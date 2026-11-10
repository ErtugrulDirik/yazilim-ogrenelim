---
title: "11.13 SIMD ile popcount ve bit işlemleri"
description: "Dizideki toplam 1 sayısı: SWAR, popcnt komutu ve pshufb ile yarım bayt tablo araması; sad_epu8 ile yatay toplama; Harley-Seal'in taşıma kaydeden toplayıcısı; 0-2000 eleman ve tam sınama; Rosetta'da popcnt önde çıkıp SIMD arkada kalırken llvm-mca'nın Skylake için popcnt 1.01, AVX2 0.75, Harley-Seal 0.43 ve Ice Lake AVX-512 için 0.126 çevrim/kelime tahmini; vpopcntq ile maskeli yükleme ve bu makinede çalıştırılamama; bit kümesi kesişimi."
---

Ders 5.8'de bir `uint64_t`'nin bitlerini saymayı öğrendik. Şimdi problem büyüyor: bir bit kümesindeki toplam 1 sayısı, örneğin veritabanı indeksinde. SIMD kümelerinde AVX-512'ye kadar popcount komutu yok. Wojciech Muła'nın 2008'de anlattığı yöntem bu eksikliği güzelce kapatıyor: **`pshufb`'yi tablo arama aleti** olarak kullanmak.

---

## 1. Yarım byte tablosu

Ders 11.10'daki `pshufb`, 16 girişli bir tablo arıyor. Tek bir nibble'ın (4 bit) 16 olası değeri var; popcount'ları:

| Nibble | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | A | B | C | D | E | F |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Pop | 0 | 1 | 1 | 2 | 1 | 2 | 2 | 3 | 1 | 2 | 2 | 3 | 2 | 3 | 3 | 4 |

Her byte'ı iki nibble'a ayır, tabloya sor, topla:

```c
/* pop.h: bir uint64_t dizisinin toplam 1 biti */
#include <stdint.h>
#include <stddef.h>
#include <immintrin.h>

__attribute__((noinline)) static uint64_t p_swar(const uint64_t *a, size_t n) {
    uint64_t t = 0;
    for (size_t i = 0; i < n; i++) {
        uint64_t x = a[i];
        x = x - ((x >> 1) & 0x5555555555555555ull);
        x = (x & 0x3333333333333333ull) + ((x >> 2) & 0x3333333333333333ull);
        x = (x + (x >> 4)) & 0x0f0f0f0f0f0f0f0full;
        t += (x * 0x0101010101010101ull) >> 56;
    }
    return t;
}

__attribute__((noinline, target("popcnt"))) static uint64_t p_hw(const uint64_t *a, size_t n) {
    uint64_t t = 0;
    for (size_t i = 0; i < n; i++) t += (uint64_t)__builtin_popcountll(a[i]);
    return t;
}

__attribute__((noinline, target("ssse3"))) static uint64_t p_ssse3(const uint64_t *a, size_t n) {
    const __m128i tablo = _mm_setr_epi8(0,1,1,2, 1,2,2,3, 1,2,2,3, 2,3,3,4);
    const __m128i m = _mm_set1_epi8(0x0f);
    __m128i top = _mm_setzero_si128();
    size_t i = 0;
    for (; i + 2 <= n; i += 2) {
        __m128i v = _mm_loadu_si128((const __m128i *)(a + i));
        __m128i lo = _mm_and_si128(v, m), hi = _mm_and_si128(_mm_srli_epi16(v, 4), m);
        __m128i c = _mm_add_epi8(_mm_shuffle_epi8(tablo, lo), _mm_shuffle_epi8(tablo, hi));
        top = _mm_add_epi64(top, _mm_sad_epu8(c, _mm_setzero_si128()));
    }
    uint64_t t = (uint64_t)_mm_cvtsi128_si64(top) + (uint64_t)_mm_cvtsi128_si64(_mm_unpackhi_epi64(top, top));
    for (; i < n; i++) t += (uint64_t)__builtin_popcountll(a[i]);
    return t;
}

__attribute__((target("avx2"))) static inline __m256i bayt_say(__m256i v) {
    const __m256i tablo = _mm256_setr_epi8(0,1,1,2, 1,2,2,3, 1,2,2,3, 2,3,3,4, 0,1,1,2, 1,2,2,3, 1,2,2,3, 2,3,3,4);
    const __m256i m = _mm256_set1_epi8(0x0f);
    __m256i lo = _mm256_and_si256(v, m), hi = _mm256_and_si256(_mm256_srli_epi16(v, 4), m);
    return _mm256_add_epi8(_mm256_shuffle_epi8(tablo, lo), _mm256_shuffle_epi8(tablo, hi));
}

__attribute__((target("avx2"))) static inline uint64_t yatay64(__m256i v) {
    return (uint64_t)_mm256_extract_epi64(v, 0) + (uint64_t)_mm256_extract_epi64(v, 1)
         + (uint64_t)_mm256_extract_epi64(v, 2) + (uint64_t)_mm256_extract_epi64(v, 3);
}

__attribute__((noinline, target("avx2,popcnt"))) static uint64_t p_avx2(const uint64_t *a, size_t n) {
    __m256i top = _mm256_setzero_si256();
    size_t i = 0;
    for (; i + 4 <= n; i += 4)
        top = _mm256_add_epi64(top, _mm256_sad_epu8(bayt_say(_mm256_loadu_si256((const __m256i *)(a + i))), _mm256_setzero_si256()));
    uint64_t t = yatay64(top);
    for (; i < n; i++) t += (uint64_t)__builtin_popcountll(a[i]);
    return t;
}

/* Harley-Seal: tasima-kaydetme toplayicisi ile popcount cagrisini azalt */
#define CSA(h, l, a, b, c) do { __m256i u = _mm256_xor_si256(a, b); \
    h = _mm256_or_si256(_mm256_and_si256(a, b), _mm256_and_si256(u, c)); \
    l = _mm256_xor_si256(u, c); } while (0)

__attribute__((noinline, target("avx2,popcnt"))) static uint64_t p_hs(const uint64_t *a, size_t n) {
    __m256i t = _mm256_setzero_si256(), birler = t, ikiler = t, dortler = t, sekizler = t;
    __m256i ikiA, ikiB, dortA, dortB, sekizA, sekizB, onaltilar;
    const __m256i *p = (const __m256i *)a;
    size_t i = 0;
#define Y(k) _mm256_loadu_si256(p + i + (k))
    for (; (i + 16) * 4 <= n; i += 16) {
        CSA(ikiA, birler, birler, Y(0), Y(1));   CSA(ikiB, birler, birler, Y(2), Y(3));
        CSA(dortA, ikiler, ikiler, ikiA, ikiB);
        CSA(ikiA, birler, birler, Y(4), Y(5));   CSA(ikiB, birler, birler, Y(6), Y(7));
        CSA(dortB, ikiler, ikiler, ikiA, ikiB);
        CSA(sekizA, dortler, dortler, dortA, dortB);
        CSA(ikiA, birler, birler, Y(8), Y(9));   CSA(ikiB, birler, birler, Y(10), Y(11));
        CSA(dortA, ikiler, ikiler, ikiA, ikiB);
        CSA(ikiA, birler, birler, Y(12), Y(13)); CSA(ikiB, birler, birler, Y(14), Y(15));
        CSA(dortB, ikiler, ikiler, ikiA, ikiB);
        CSA(sekizB, dortler, dortler, dortA, dortB);
        CSA(onaltilar, sekizler, sekizler, sekizA, sekizB);
        t = _mm256_add_epi64(t, _mm256_sad_epu8(bayt_say(onaltilar), _mm256_setzero_si256()));
    }
#undef Y
    t = _mm256_slli_epi64(t, 4);
    #define S(x, k) _mm256_slli_epi64(_mm256_sad_epu8(bayt_say(x), _mm256_setzero_si256()), k)
    t = _mm256_add_epi64(t, S(sekizler, 3));
    t = _mm256_add_epi64(t, S(dortler, 2));
    t = _mm256_add_epi64(t, S(ikiler, 1));
    t = _mm256_add_epi64(t, S(birler, 0));
    uint64_t r = yatay64(t);
    for (size_t j = i * 4; j < n; j++) r += (uint64_t)__builtin_popcountll(a[j]);
    return r;
}
```

Adımlar:

1. `v & 0x0f`: alt nibble.
2. `_mm_srli_epi16(v, 4) & 0x0f`: üst nibble. 16 bitlik kaydırma (Ders 11.9) ve maske ile sızan bitler atılır.
3. `shuffle_epi8(tablo, ...)`: iki tablo araması, 16 şeritte.
4. `add_epi8`: her byte artık o byte'ın popcount'u (0–8).
5. `_mm_sad_epu8(c, 0)`: sıfıra uzaklık, yani **yatay toplam**, sekizli gruplar halinde iki 64 bitlik parçaya. Ders 11.9'daki SAD'in yan etkisi.

---

## 2. Harley-Seal

Bitleri tek tek sayma, **önce taşıma kaydeden toplayıcıyla** (CSA) sıkıştır. Bir CSA üç sayıyı iki sayıya indirir, Ders 7.2'deki tam toplayıcının kelime genişliğinde hali:

$$h = (a \land b) \lor ((a \oplus b) \land c), \quad l = a \oplus b \oplus c$$

Bu, $a + b + c = 2h + l$ özdeşliğinin bit bit karşılığı. 16 vektörü CSA ağacından geçirince yalnız bir `onaltilar` çıktısı kalıyor; onun popcount'unu alıp 16 ile çarpıyoruz. Yani 16 vektör başına yalnız **bir** tablo arama. Kalan ara birikimcilerin popcount'u döngü sonunda bir kez alınıyor.

`CSA` makrosu ve `p_hs` yukarıdaki dosyada. Doğruluk testi:

```c
/* sina.c: hepsi ayni sonucu veriyor mu, kac eleman icin? */
#include <stdio.h>
#include <stdlib.h>
#include "pop.h"
int main(void) {
    uint64_t a[2000], s = 88172645463325252ull;
    for (int i = 0; i < 2000; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; a[i] = s; }
    long hata = 0;
    for (size_t n = 0; n <= 2000; n++) {
        uint64_t r = p_swar(a, n);
        if (p_hw(a, n) != r || p_ssse3(a, n) != r || p_avx2(a, n) != r || p_hs(a, n) != r) hata++;
    }
    for (int i = 0; i < 2000; i++) a[i] = ~0ull;
    if (p_hs(a, 2000) != 128000 || p_avx2(a, 2000) != 128000 || p_ssse3(a, 2000) != 128000) hata++;
    printf("0..2000 eleman, ayrica hepsi 1: %ld hata\n", hata);
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize sina.c -o s && ./s
0..2000 eleman, ayrica hepsi 1: 0 hata
```

Her uzunlukta, ayrıca tüm bitler 1 durumunda (en ağır yük: 64 × 2000 = 128000 ile karşılaştırıyoruz) hata yok.

---

## 3. Sonuçlar: iki farklı hikâye

```c
/* hiz.c: popcount hizi */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"
#include "pop.h"
typedef uint64_t pf(const uint64_t *, size_t);
int main(void) {
    size_t ns[] = { 8, 64, 4096 };
    struct { const char *ad; pf *f; } t[] = { {"SWAR", p_swar}, {"popcnt", p_hw}, {"SSSE3 pshufb", p_ssse3}, {"AVX2 pshufb", p_avx2}, {"AVX2 Harley-Seal", p_hs} };
    uint64_t *a = aligned_alloc(64, 8 * 8192), s = 88172645463325252ull;
    for (int i = 0; i < 8192; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; a[i] = s; }
    printf("%-18s", "kelime sayisi:");
    for (int u = 0; u < 3; u++) printf(" %9zu", ns[u]);
    puts("   (ns/kelime)");
    for (int k = 0; k < 5; k++) {
        printf("%-18s", t[k].ad);
        for (int u = 0; u < 3; u++) {
            size_t n = ns[u]; long tur = 200000000 / (long)n; double en = 1e9; uint64_t r = 0;
            for (int q = 0; q < 7; q++) {
                double b0 = simdi();
                for (long j = 0; j < tur; j++) { r += t[k].f(a, n); BELLEK(); }
                double e = simdi() - b0; if (e < en) en = e;
            }
            KORU(r);
            printf(" %9.3f", en * 1e9 / ((double)tur * (double)n));
        }
        puts("");
    }
    return 0;
}
```

Rosetta altında:

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize hiz.c -o h && ./h
kelime sayisi:             8        64      4096   (ns/kelime)
SWAR                   1.088     0.948     0.853
popcnt                 0.586     0.380     0.352
SSSE3 pshufb           0.905     0.666     0.630
AVX2 pshufb            1.128     0.695     0.630
AVX2 Harley-Seal       2.103     1.178     1.031
```

Buradan "SIMD faydasız, Harley-Seal kötü" sonucu çıkarırsan **yanılırsın**. Rosetta altında `popcnt`, ARM'in `cnt`'ine çevriliyor olabilir; 256 bitlik register'lar da büyük ihtimalle bölünüyor (AVX2 = SSSE3 satırı bunu düşündürüyor). Harley-Seal'in onlarca xor'u Rosetta'nın gerçekleştirmesinde pahalı.

`llvm-mca` ile Skylake ve Ice Lake modeli:

| Yöntem | Kelime/tur | Skylake (çevrim/kelime) | Ice Lake (çevrim/kelime) |
| --- | --- | --- | --- |
| SWAR | 1 | 4.02 | 4.02 |
| `popcnt` | 1 | **1.01** | 1.01 |
| SSSE3 `pshufb` | 2 | 1.84 | 1.84 |
| AVX2 `pshufb` | 4 | 0.75 | 0.67 |
| AVX2 Harley-Seal | 64 | **0.43** | 0.43 |
| AVX-512 `vpopcntq` | 8 | yok | **0.126** |

Bu tablo gerçek x86 için beklenen sıralamayı veriyor: `popcnt` 1 çevrim, onu geçmek için 256 bit gerekiyor (SSSE3 yeterli değil); Harley-Seal yaklaşık 2.3 kat önde; AVX-512'nin gerçek donanım komutu **8 kat**. Bu sonuç Muła, Kurz ve Lemire'in 2018 makalesindeki gerçek donanım ölçümleriyle aynı yönde. (Sayılar model tahminidir, ölçüm değil.)

Kısa dizilerde Harley-Seal kötü: 64 elemandan az için döngüsü hiç girmeyip ara birikimcileri ve kalanı işlemeye bakıyor (8 kelimede 2.1 ns).

---

## 4. AVX-512'nin yaptığı

```c
t = _mm512_add_epi64(t, _mm512_popcnt_epi64(_mm512_loadu_si512(a + i)));
```

Tek komut. Bu makinede çalıştıramıyoruz (Ders 11.6: `SIGILL`); yalnız derleyip assembly'sini okuyabiliyoruz:

```c
#include <immintrin.h>
#include <stdint.h>
#include <stddef.h>
uint64_t p512(const uint64_t *a, size_t n) {
    __m512i t = _mm512_setzero_si512();
    size_t i = 0;
    for (; i + 8 <= n; i += 8)
        t = _mm512_add_epi64(t, _mm512_popcnt_epi64(_mm512_loadu_si512(a + i)));
    /* maskeli yukleme: kalan 0-7 eleman, dongu yok */
    __mmask8 m = (__mmask8)((1u << (n - i)) - 1);
    t = _mm512_add_epi64(t, _mm512_popcnt_epi64(_mm512_maskz_loadu_epi64(m, a + i)));
    return (uint64_t)_mm512_reduce_add_epi64(t);
}
```

```
$ clang -O2 -mavx512f -mavx512vpopcntdq -S vp.c -o -
	vpopcntq	(%rdi,%rax,8), %zmm1
	vpopcntq	64(%rdi,%rax,8), %zmm2
	...
	kmovw	%edx, %k1
	vmovdqu64	(%rdi,%rax,8), %zmm1 {%k1} {z}
	vpopcntq	%zmm1, %zmm1
	vpaddq	%zmm0, %zmm1, %zmm0
```

İki önemli şey. `k1` **maske register'ı**: `{%k1} {z}`, maske biti 0 olan şeritleri sıfırla ve onlar için bellek okumasını yapma. Ders 11.11'deki `maskload`'ın temiz, her tipte, her komutta çalışan hali: **kalan elemanlar için ayrı döngü yok**. Bu, AVX-512'nin (ve SVE, RVV'nin) gerçek yeniliği, 512 bitten daha önemlisi.

---

## 5. Bit kümesi kesişimi

Bit düzeyinde işlemlerin kendisi zaten şerit bağımsızdır, en kolay SIMD:

```c
/* kume.c: iki bit kumesinin kesisimi (Ders 5.20) */
#include <stdio.h>
#include <stdlib.h>
#include "pop.h"
__attribute__((target("avx2,popcnt"))) int main(void) {
    enum { N = 1024 };
    static uint64_t a[N], b[N], s = 88172645463325252ull;
    for (int i = 0; i < N; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; a[i] = s; s ^= s << 13; s ^= s >> 7; s ^= s << 17; b[i] = s; }
    uint64_t c = 0; for (int i = 0; i < N; i++) c += (uint64_t)__builtin_popcountll(a[i] & b[i]);
    __m256i t = _mm256_setzero_si256();
    for (int i = 0; i + 4 <= N; i += 4) {
        __m256i x = _mm256_and_si256(_mm256_loadu_si256((const __m256i *)(a + i)), _mm256_loadu_si256((const __m256i *)(b + i)));
        t = _mm256_add_epi64(t, _mm256_sad_epu8(bayt_say(x), _mm256_setzero_si256()));
    }
    printf("C %llu  AVX2 %llu  (N*64=%d bit)\n", (unsigned long long)c, (unsigned long long)yatay64(t), N * 64);
    return 0;
}
```

```
$ clang -O2 kume.c -o k && ./k
C 16547  AVX2 16547  (N*64=65536 bit)
```

İki bit kümesi `and`, kesişim boyutu popcount. Ders 5.20'nin bitboard'unda kullandığımız aynı işlem, 256'şar bit birden.

Derleyici bayrağı yoksa `__builtin_popcountl` SWAR'a dönüşür (komutun gelmesini garanti etmez):

```
$ clang -O2 -S yanlis.c -o -
	movq	%rdi, %rax
	shrq	%rax
	movabsq	$6148914691236517205, %rcx      # imm = 0x5555555555555555
	...
	imulq	%rdx, %rax
	shrq	$56, %rax

$ clang -O2 -mpopcnt -S yanlis.c -o -
	popcntq	%rdi, %rax
	retq
```

Ders 5.8'in SWAR'ının 20 komutu ve tek `popcnt` komutu. Bayrak olmadan x86-64 taban hedefi `popcnt` içermiyor.

---

## Alıştırmalar

**1** – Nibble tablosunda 0xF için değer ne? Neden `add_epi8`'in taşma riski yok? Toplamda bir byte'ın popcount'u en fazla kaç?

**2** – `sad_epu8` olmadan her turda `add_epi8` ile biriktirmeye çalışsaydın, kaç tur sonra taşma olurdu?

**3** – Harley-Seal'de CSA'nın $a + b + c = 2h + l$ özdeşliğini iki tek bit için tablo yap.

**4** – AVX2 popcount'u `pshufb`'siz, Ders 5.8'in SWAR'ıyla yazıp `llvm-mca` ile karşılaştır. Hangisi hızlı, neden?

**5** – `vp.c`'de `_mm512_maskz_loadu_epi64` satırı. `n - i == 0` için `(1u << 0) - 1 = 0`: sıfır maske, güvenli mi? `n - i == 8`'de bu kod döngüden çıkmış olur mu?

<details>
<summary>Cevaplar</summary>

**1** – 0xF = 1111, popcount 4. Tek byte'ın popcount'u en fazla 8, iki nibble'dan 4 + 4, `add_epi8`'de 8 < 255: taşmaz.

**2** – Bir byte en fazla 8 biriktirir; $\lfloor 255 / 8 \rfloor = 31$ tur güvenli, 32. turda (256) taşabilir. Bu yüzden her tur (veya en geç 31 turda bir) `sad` ile 64 bite taşımak gerekir.

**3** – $a, b, c$ için: `0,0,0 → h=0,l=0`, `1,0,0 → h=0,l=1`, `1,1,0 → h=1,l=0`, `1,1,1 → h=1,l=1`. Her durumda $a + b + c = 2h + l$.

**4** – Kendi deneyin. Beklenti: SWAR adımlarında bol komut, `pshufb` iki tablo aramasıyla gidiyor; `pshufb` önde olmalı. Skylake modeli SWAR için kelime başına 4 çevrim, `pshufb` için 0.75 veriyor.

**5** – Sıfır maske tüm şeritleri maskeliyor; hiçbir okuma yapılmaz, dolayısıyla güvenli. Yani kalan yoksa da ek komut yalnız bir `kmov + vmovdqu64`. Döngü `i + 8 <= n` iken döner; `n - i == 8` olamaz, çünkü o zaman döngü bir tur daha yapardı.

</details>

---

## Kaynaklar

- Wojciech Muła, Nathan Kurz, Daniel Lemire, "Faster Population Counts Using AVX2 Instructions", *The Computer Journal*, 61(1), 2018.
- Henry S. Warren, *Hacker's Delight* (2. baskı), Bölüm 5.
- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 2: `PSHUFB`, `PSADBW`, `VPOPCNTD/Q`.
- LLVM, `llvm-mca`.

**Sıradaki ders:** ARM NEON. Aynı örneklerin NEON karşılığı, taşınabilir SIMD (`<arm_neon.h>`).
