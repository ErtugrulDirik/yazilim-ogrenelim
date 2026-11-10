---
title: "11.10 Karıştırma ve permütasyon"
description: "Şeritleri yeniden düzenlemek: _MM_SHUFFLE makrosu ve 0xE4'ün anlamı, shuffle_ps'in iki kaynaktan okuması, unpack ve movelh/movehl, blend ve blendv ile şerit seçimi; pshufb'un bayt düzeyinde tablo arama olması ve 0x80 ile sıfırlama; bswap için tek komut; 4x4 ve 8x8 matris transpozunun adım adım unpack + shuffle + permute2f128 olması ve C ile birebir doğrulama; RGBA'dan kanal ayıklama; AVX'te 128 bit şerit sınırı ve permutevar8x32 ile aşılması."
---

SIMD aritmetiği şeritleri bağımsız işliyor. Veriler komşu şeritlere doğru sırada gelmediğinde bir şeyler yapmak gerekiyor. Gerçek SIMD kodunun büyük bölümü toplama-çarpma değil, **veriyi doğru yere taşıma**. Bu derste bu aletlerin ana ailelerini görüyoruz.

---

## 1. _MM_SHUFFLE

`_mm_shuffle_ps(a, b, imm)` 8 bitlik sabitin 2'şer bitiyle dört şerit seçer. `_MM_SHUFFLE(d, c, b, a)` bu sabiti kurar ve argümanları (yine) yüksek şeritten düşüğe alır.

```c
_MM_SHUFFLE(3, 2, 1, 0)   // 0b11100100 = 0xe4: kimlik
_MM_SHUFFLE(0, 1, 2, 3)   // 0b00011011 = 0x1b: tersine
```

Kural: sonucun **düşük iki şeridi `a`'dan**, **yüksek iki şeridi `b`'den** gelir.

```c
/* karistir.c: shuffle ailesi */
#include <stdio.h>
#include <immintrin.h>

static void yazf(const char *ad, __m128 v) {
    float f[4]; _mm_storeu_ps(f, v);
    printf("%-30s %3g %3g %3g %3g\n", ad, f[0], f[1], f[2], f[3]);
}
static void yazb(const char *ad, __m128i v) {
    unsigned char b[16]; _mm_storeu_si128((__m128i *)b, v);
    printf("%-30s", ad);
    for (int i = 0; i < 16; i++) printf(" %02x", b[i]);
    printf("\n");
}

int main(void) {
    __m128 a = _mm_setr_ps(1, 2, 3, 4), b = _mm_setr_ps(10, 20, 30, 40);
    printf("_MM_SHUFFLE(3,2,1,0) = 0x%02x\n_MM_SHUFFLE(0,1,2,3) = 0x%02x\n", _MM_SHUFFLE(3,2,1,0), _MM_SHUFFLE(0,1,2,3));
    yazf("a", a);
    yazf("b", b);
    yazf("shuffle(a,a,0,1,2,3)", _mm_shuffle_ps(a, a, _MM_SHUFFLE(0, 1, 2, 3)));
    yazf("shuffle(a,b,3,2,1,0)", _mm_shuffle_ps(a, b, _MM_SHUFFLE(3, 2, 1, 0)));
    yazf("shuffle(a,a,0,0,0,0)", _mm_shuffle_ps(a, a, _MM_SHUFFLE(0, 0, 0, 0)));
    yazf("unpacklo(a,b)", _mm_unpacklo_ps(a, b));
    yazf("unpackhi(a,b)", _mm_unpackhi_ps(a, b));
    yazf("movelh(a,b)", _mm_movelh_ps(a, b));
    yazf("movehl(a,b)", _mm_movehl_ps(a, b));
    yazf("blend(a,b,0b0101)", _mm_blend_ps(a, b, 0x5));
    yazf("blendv(a,b,a>2)", _mm_blendv_ps(a, b, _mm_cmpgt_ps(a, _mm_set1_ps(2))));

    __m128i v = _mm_setr_epi8(0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15);
    yazb("v", v);
    /* pshufb: her cikis byte'i icin hangi girdi? yuksek bit 1 ise 0 */
    __m128i t = _mm_setr_epi8(3,2,1,0, 7,6,5,4, 11,10,9,8, 15,14,13,12);
    yazb("kontrol (bswap32)", t);
    yazb("shuffle_epi8", _mm_shuffle_epi8(v, t));
    __m128i z = _mm_setr_epi8(0,(char)0x80,2,(char)0x80, 4,(char)0x80,6,(char)0x80, 8,(char)0x80,10,(char)0x80, 12,(char)0x80,14,(char)0x80);
    yazb("kontrol (0x80 ile sifirla)", z);
    yazb("shuffle_epi8", _mm_shuffle_epi8(v, z));
    return 0;
}
```

```
$ clang -O2 -mssse3 -msse4.1 karistir.c -o a && ./a
_MM_SHUFFLE(3,2,1,0) = 0xe4
_MM_SHUFFLE(0,1,2,3) = 0x1b
a                                1   2   3   4
b                               10  20  30  40
shuffle(a,a,0,1,2,3)             4   3   2   1
shuffle(a,b,3,2,1,0)             1   2  30  40
shuffle(a,a,0,0,0,0)             1   1   1   1
unpacklo(a,b)                    1  10   2  20
unpackhi(a,b)                    3  30   4  40
movelh(a,b)                      1   2  10  20
movehl(a,b)                     30  40   3   4
blend(a,b,0b0101)               10   2  30   4
blendv(a,b,a>2)                  1   2  30  40
v                              00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f
kontrol (bswap32)              03 02 01 00 07 06 05 04 0b 0a 09 08 0f 0e 0d 0c
shuffle_epi8                   03 02 01 00 07 06 05 04 0b 0a 09 08 0f 0e 0d 0c
kontrol (0x80 ile sifirla)     00 80 02 80 04 80 06 80 08 80 0a 80 0c 80 0e 80
shuffle_epi8                   00 00 02 00 04 00 06 00 08 00 0a 00 0c 00 0e 00
```

Aileler:

| Komut | Ne yapar |
| --- | --- |
| `shuffle_ps` | 2 kaynaktan, sabit, dört şerit |
| `unpacklo/hi` | iki kaynağın alt/üst yarısını **dönüşümlü dizer** |
| `movelh / movehl` | alt-üst 64 bitleri birleştirir |
| `blend_ps` | sabit bit maskesiyle şerit seçer (AVX/SSE4.1) |
| `blendv_ps` | çalışma zamanı maskesiyle; her şeridin **en yüksek biti** |
| `shuffle_epi8` | byte düzeyinde, **çalışma zamanı** tablosu |

`blend` ile Ders 11.7'deki `and + andnot` üçlüsü tek komuta iniyor (SSE4.1 varsa).

---

## 2. pshufb: en güçlü komut

`_mm_shuffle_epi8(v, t)` her sonuç byte'ı için `t[i]` değerini indis olarak kullanır:

- `t[i] & 0x80` ise sonuç byte'ı 0.
- Yoksa `sonuc[i] = v[t[i] & 0x0f]`.

Bu **çalışma zamanında verilen** bir 16 girişli tablo araması. Ders 11.13'te popcount tam bu sayede 4 bitlik parçalara tablo uygulayacak. Bu derste iki uygulama:

```c
/* bayt.c: uygulamalar: bswap ve RGBA'dan kanal cikarma */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <immintrin.h>
#include "olcum.h"

__attribute__((noinline)) void bs_c(uint32_t *d, const uint32_t *k, long n) {
    for (long i = 0; i < n; i++) d[i] = __builtin_bswap32(k[i]);
}
__attribute__((noinline, target("ssse3"))) void bs_sse(uint32_t *d, const uint32_t *k, long n) {
    const __m128i t = _mm_setr_epi8(3,2,1,0, 7,6,5,4, 11,10,9,8, 15,14,13,12);
    long i = 0;
    for (; i + 4 <= n; i += 4)
        _mm_storeu_si128((__m128i *)(d + i), _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)(k + i)), t));
    for (; i < n; i++) d[i] = __builtin_bswap32(k[i]);
}
/* RGBARGBA... -> sadece R */
__attribute__((target("ssse3"))) static void kanal(uint8_t *r, const uint8_t *rgba, long piksel) {
    const __m128i t = _mm_setr_epi8(0,4,8,12, -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1);
    long i = 0;
    for (; i + 4 <= piksel; i += 4) {
        __m128i v = _mm_shuffle_epi8(_mm_loadu_si128((const __m128i *)(rgba + i * 4)), t);
        _mm_storeu_si32(r + i, v);
    }
    for (; i < piksel; i++) r[i] = rgba[i * 4];
}

int main(void) {
    long n = 4096;
    uint32_t *k = malloc(n * 4), *a = malloc(n * 4), *b = malloc(n * 4);
    for (long i = 0; i < n; i++) k[i] = (uint32_t)(i * 2654435761u);
    bs_c(a, k, n); bs_sse(b, k, n);
    printf("bswap ayni: %s\n", memcmp(a, b, n * 4) ? "HAYIR" : "evet");
    double e1 = 1e9, e2 = 1e9;
    for (int r = 0; r < 7; r++) {
        double t = simdi(); for (int j = 0; j < 20000; j++) { bs_c(a, k, n); BELLEK(); } double s = simdi() - t; if (s < e1) e1 = s;
        t = simdi(); for (int j = 0; j < 20000; j++) { bs_sse(b, k, n); BELLEK(); } s = simdi() - t; if (s < e2) e2 = s;
    }
    printf("C %.3f ns/eleman, SSSE3 %.3f ns/eleman\n", e1 * 1e9 / (20000.0 * n), e2 * 1e9 / (20000.0 * n));
    uint8_t rgba[40], r[10]; for (int i = 0; i < 40; i++) rgba[i] = (uint8_t)i;
    kanal(r, rgba, 10);
    for (int i = 0; i < 10; i++) printf("%d ", r[i]);
    puts("");
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize bayt.c -o d && ./d
bswap ayni: evet
C 0.196 ns/eleman, SSSE3 0.073 ns/eleman
0 4 8 12 16 20 24 28 32 36 
```

Dört tane 32 bitlik sayının bayt sırasını **bir komut** değiştiriyor (Ders 3.9). `kanal` fonksiyonu 40 byte'lık bir RGBA dizisinden `R` kanalını (her 4. byte) çıkarıyor. Maske için `-1` yazdık (`0xFF`, en yüksek bit 1).

---

## 3. Matris transpozu

Klasik bir kullanım: 4×4 matrisin transpozu, `_MM_TRANSPOSE4_PS` makrosunun içi.

```c
/* transpoz.c: 4x4 ve 8x8 float matris transpozu */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <immintrin.h>
#include "olcum.h"

__attribute__((noinline)) void tr4_c(float *d, const float *m) {
    for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) d[j * 4 + i] = m[i * 4 + j];
}

__attribute__((noinline)) void tr4_sse(float *d, const float *m) {
    __m128 r0 = _mm_loadu_ps(m), r1 = _mm_loadu_ps(m + 4), r2 = _mm_loadu_ps(m + 8), r3 = _mm_loadu_ps(m + 12);
    __m128 t0 = _mm_unpacklo_ps(r0, r1);       /* a0 b0 a1 b1 */
    __m128 t1 = _mm_unpacklo_ps(r2, r3);       /* c0 d0 c1 d1 */
    __m128 t2 = _mm_unpackhi_ps(r0, r1);       /* a2 b2 a3 b3 */
    __m128 t3 = _mm_unpackhi_ps(r2, r3);       /* c2 d2 c3 d3 */
    _mm_storeu_ps(d,      _mm_movelh_ps(t0, t1));   /* a0 b0 c0 d0 */
    _mm_storeu_ps(d + 4,  _mm_movehl_ps(t1, t0));   /* a1 b1 c1 d1 */
    _mm_storeu_ps(d + 8,  _mm_movelh_ps(t2, t3));
    _mm_storeu_ps(d + 12, _mm_movehl_ps(t3, t2));
}

__attribute__((noinline)) void tr8_c(float *d, const float *m) {
    for (int i = 0; i < 8; i++) for (int j = 0; j < 8; j++) d[j * 8 + i] = m[i * 8 + j];
}

__attribute__((noinline, target("avx"))) void tr8_avx(float *d, const float *m) {
    __m256 r[8], t[8], s[8];
    for (int i = 0; i < 8; i++) r[i] = _mm256_loadu_ps(m + i * 8);
    for (int i = 0; i < 4; i++) {                 /* 1: 32 bit ciftler */
        t[2 * i]     = _mm256_unpacklo_ps(r[2 * i], r[2 * i + 1]);
        t[2 * i + 1] = _mm256_unpackhi_ps(r[2 * i], r[2 * i + 1]);
    }
    s[0] = _mm256_shuffle_ps(t[0], t[2], _MM_SHUFFLE(1, 0, 1, 0));   /* 2: 64 bit ciftler */
    s[1] = _mm256_shuffle_ps(t[0], t[2], _MM_SHUFFLE(3, 2, 3, 2));
    s[2] = _mm256_shuffle_ps(t[1], t[3], _MM_SHUFFLE(1, 0, 1, 0));
    s[3] = _mm256_shuffle_ps(t[1], t[3], _MM_SHUFFLE(3, 2, 3, 2));
    s[4] = _mm256_shuffle_ps(t[4], t[6], _MM_SHUFFLE(1, 0, 1, 0));
    s[5] = _mm256_shuffle_ps(t[4], t[6], _MM_SHUFFLE(3, 2, 3, 2));
    s[6] = _mm256_shuffle_ps(t[5], t[7], _MM_SHUFFLE(1, 0, 1, 0));
    s[7] = _mm256_shuffle_ps(t[5], t[7], _MM_SHUFFLE(3, 2, 3, 2));
    for (int i = 0; i < 4; i++) {                 /* 3: 128 bit yarilar */
        _mm256_storeu_ps(d + i * 8,       _mm256_permute2f128_ps(s[i], s[i + 4], 0x20));
        _mm256_storeu_ps(d + (i + 4) * 8, _mm256_permute2f128_ps(s[i], s[i + 4], 0x31));
    }
}

typedef void fn(float *, const float *);

static double olc(fn *f, float *d, const float *m) {
    double en = 1e9;
    for (int t = 0; t < 7; t++) {
        double b0 = simdi();
        for (int r = 0; r < 5000000; r++) { f(d, m); KORU(d); BELLEK(); }
        double s = simdi() - b0; if (s < en) en = s;
    }
    return en * 1e9 / 5000000;
}

int main(void) {
    float m[64], a[64], b[64];
    for (int i = 0; i < 64; i++) m[i] = (float)i;
    tr4_c(a, m); tr4_sse(b, m); printf("4x4 ayni: %s\n", memcmp(a, b, 16 * 4) ? "HAYIR" : "evet");
    tr8_c(a, m); tr8_avx(b, m); printf("8x8 ayni: %s\n", memcmp(a, b, 64 * 4) ? "HAYIR" : "evet");
    for (int i = 0; i < 2; i++) { for (int j = 0; j < 8; j++) printf("%3g", b[i * 8 + j]); puts(""); }
    printf("4x4 C   %.1f ns\n", olc(tr4_c, a, m));
    printf("4x4 SSE %.1f ns\n", olc(tr4_sse, a, m));
    printf("8x8 C   %.1f ns\n", olc(tr8_c, a, m));
    printf("8x8 AVX %.1f ns\n", olc(tr8_avx, a, m));
    return 0;
}
```

4×4 için iki aşama: `unpack` ile komşu satırları ikişer dizmek, sonra `movelh/movehl` ile sütunları birleştirmek.

```
r0: a0 a1 a2 a3         t0 = unpacklo(r0, r1): a0 b0 a1 b1
r1: b0 b1 b2 b3         t1 = unpacklo(r2, r3): c0 d0 c1 d1
r2: c0 c1 c2 c3         movelh(t0, t1):        a0 b0 c0 d0
r3: d0 d1 d2 d3         movehl(t1, t0):        a1 b1 c1 d1
```

8×8 AVX sürümü üç aşama: `unpack` (32 bit çiftler), `shuffle` (64 bit), `permute2f128` (128 bit). $\log_2 8 = 3$ aşama; 2'nin kuvveti boyutlarda bu kalıp genelleşiyor.

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize transpoz.c -o c && ./c
4x4 ayni: evet
8x8 ayni: evet
  0  8 16 24 32 40 48 56
  1  9 17 25 33 41 49 57
4x4 C   3.2 ns
4x4 SSE 1.9 ns
8x8 C   14.0 ns
8x8 AVX 5.9 ns
```

:::caution[Yine ölü kod]
Bu testin ilk sürümü dört satırın hepsinde **0.7 ns** gösterdi. Derleyici `a` ve `b` dizilerinin döngüden sonra kullanılmadığını anlayıp çağrıyı atmıştı (`noinline` olsa bile); `BELLEK()` yetmedi, çünkü yerel dizinin adresi kaçmıyordu. Her turda `KORU(d)` eklemek çözdü. Ders 11.1'in tuzağı, SIMD'de de aynı.
:::

(Rosetta altında.) 8×8'de 2.4 kat kazanç var.

---

## 4. Şerit sınırı

AVX'in 128 bitlik şeritleri (Ders 11.8) burada da geçerli:

```c
/* avxper.c: 256 bit karistirma ve serit siniri */
#include <stdio.h>
#include <immintrin.h>

static void yaz(const char *ad, __m256 v) {
    float f[8]; _mm256_storeu_ps(f, v);
    printf("%-26s", ad);
    for (int i = 0; i < 8; i++) printf(" %3g", f[i]);
    printf("\n");
}

int main(void) {
    __m256 a = _mm256_setr_ps(0, 1, 2, 3, 4, 5, 6, 7);
    yaz("a", a);
    yaz("permute_ps(0,1,2,3)", _mm256_permute_ps(a, _MM_SHUFFLE(0, 1, 2, 3)));
    __m256i ters = _mm256_setr_epi32(7, 6, 5, 4, 3, 2, 1, 0);
    yaz("permutevar8x32 (ters)", _mm256_permutevar8x32_ps(a, ters));
    yaz("permute2f128(a,a,0x01)", _mm256_permute2f128_ps(a, a, 0x01));
    return 0;
}
```

```
$ clang -O2 -mavx2 avxper.c -o b && ./b
a                            0   1   2   3   4   5   6   7
permute_ps(0,1,2,3)          3   2   1   0   7   6   5   4
permutevar8x32 (ters)        7   6   5   4   3   2   1   0
permute2f128(a,a,0x01)       4   5   6   7   0   1   2   3
```

`_mm256_permute_ps` **her şeritte ayrı** çalışır; 8 elemanı tümden çevirmek için `permutevar8x32` (çapraz şerit, AVX2, indisler bir vektörden gelir) gerekir. `pshufb`'nin 256 bitlik sürümü `_mm256_shuffle_epi8` de şerit içi: 32 byte'ı tersine çevirmek isteyen, önce her yarıyı `pshufb` ile çevirip sonra `permute2x128` ile yarıları takas etmelidir. `llvm-mca`'nın Skylake modelinde çapraz şerit `vpermps` ve `vperm2f128` 3 çevrim, şerit içi `vpshufb` ve `vpermilps` 1 çevrim gecikmeli. Bu yüzden derleyiciler şerit içi yolları tercih eder.

---

## Alıştırmalar

**1** – `_MM_SHUFFLE(2, 3, 0, 1)` kaçtır? `a = (1, 2, 3, 4)` için `_mm_shuffle_ps(a, a, ...)` ne verir?

**2** – RGB dizisini BGR'ye çeviren (`R G B R G B ...`) `pshufb` kontrol maskesini yaz. 16 byte'ta en son eleman nereye düşer?

**3** – 16 bitlik her sayının bayt sırasını çeviren `pshufb` kontrolü ne olur?

**4** – 32 byte'lık register'daki byte'ları tersine çeviren AVX2 kod parçasını yaz.

**5** – `blend_ps` ile `blendv_ps` arasında derleme zamanı açısından hangi fark var? `mask` bir `__m128` olduğunda hangisini kullanırsın?

<details>
<summary>Cevaplar</summary>

**1** – `0xb1`. Sonuç `2 1 4 3`. (Denedik.)

**2** – `_mm_setr_epi8(2,1,0, 5,4,3, 8,7,6, 11,10,9, 14,13,12, 15)`. Son byte (`15`) tam bir piksel oluşturmadığı için yerinde kalır. `(1,...,16)` üzerinde: `3 2 1 6 5 4 9 8 7 12 11 10 15 14 13 16`.

**3** – `_mm_setr_epi8(1,0, 3,2, 5,4, 7,6, 9,8, 11,10, 13,12, 15,14)`.

**4** –
```c
const __m256i t = _mm256_setr_epi8(15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0,
                                   15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0);
__m256i y = _mm256_shuffle_epi8(x, t);          /* her yari kendi icinde */
y = _mm256_permute2x128_si256(y, y, 1);         /* yarilari takas */
```
`x = 0..31` ile çalıştırdık: `31 30 ... 1 0`.

**5** – `blend_ps`'in maskesi derleme zamanı sabiti (`imm8`); `blendv_ps` çalışma zamanı register'ını okur, her şeridin en yüksek bitine bakar. Karşılaştırma sonucundan gelen bir `__m128` için `blendv_ps`.

</details>

---

## Kaynaklar

- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 2: `SHUFPS`, `PSHUFB`, `BLENDVPS`, `VPERMPS`.
- LLVM, `llvm-mca` Skylake zamanlama modeli (`-instruction-info`).
- Intel, *Intel 64 and IA-32 Architectures Optimization Reference Manual*, karıştırma ve transpoz örnekleri.

**Sıradaki ders:** Yatay işlemler ve indirgeme. Vektör içi toplama, dot product, maskeleme ile kalan elemanları işleme.
