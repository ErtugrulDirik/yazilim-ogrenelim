---
title: "11.11 Yatay işlemler ve indirgeme"
description: "Vektörü tek sayıya indirgemek: haddps ile elle karıştırmanın assembly'si, 8 şerit için üç aşamalı toplam; dot product'ın dört sürümü ve birikimci sayısının etkisi, float toplama sırasının sonucu değiştirmesi ve bu veride 4 birikimcinin hatayı 4.6 kat azaltması; kalan elemanlar için maskload ve sayfa sonunda loadu SIGSEGV iken maskload'ın güvenli çalışması; maskeyle koşullu toplama ve en büyük elemanın yeri; movemask ile popcount."
---

SIMD'in güçlü olduğu şey dikey işlemler: şerit şerit toplamak. Ama bir toplamın sonunda elimize tek bir sayı lazım. Şeritleri kendi aralarında işlemek, yani **yatay** işlem, SIMD'in zayıf noktası. Bu ders ayrıca her gerçek döngünün en sıkıcı problemini çözüyor: sona kalan elemanlar.

---

## 1. Şeritleri toplamak

Kaynaktaki iki yol:

```c
/* yatay.c: 4 seridi tek sayiya indirmek */
#include <immintrin.h>

float hsum_hadd(__m128 v) {
    __m128 t = _mm_hadd_ps(v, v);
    t = _mm_hadd_ps(t, t);
    return _mm_cvtss_f32(t);
}

float hsum_kar(__m128 v) {
    __m128 t = _mm_movehdup_ps(v);             /* v1 v1 v3 v3 */
    __m128 s = _mm_add_ps(v, t);               /* v0+v1 . v2+v3 . */
    t = _mm_movehl_ps(t, s);                   /* v2+v3 . */
    s = _mm_add_ss(s, t);
    return _mm_cvtss_f32(s);
}
```

```
$ clang -O2 -msse3 -S yatay.c -o -
hsum_hadd:
	haddps	%xmm0, %xmm0
	haddps	%xmm0, %xmm0
	retq
hsum_kar:
	movshdup	%xmm0, %xmm1
	addps	%xmm1, %xmm0
	movaps	%xmm0, %xmm1
	unpckhpd	%xmm0, %xmm1
	addss	%xmm1, %xmm0
	retq
```

İki komutluk sürüm daha kısa görünüyor. Ama `haddps` tek bir komut gibi görünse de içinde birkaç mikro-işlem var (aşağıdaki `llvm-mca` tablosu). Akılda tutulacak ifade: **`hadd` kısa ama ucuz değil.** Rosetta burada yardımcı olmuyor, çünkü bu farkı x86 çekirdeği üzerinde ölçemiyoruz.

| Komut (Skylake modeli) | Mikro-işlem | Gecikme | Ters verim (çevrim) |
| --- | --- | --- | --- |
| `vaddps` | 1 | 4 | 0.5 |
| `vshufps` | 1 | 1 | 1 |
| `vhaddps` | 3 | 6 | 2 |
| `vdpps` | 4 | 13 | 1.5 |

İki `haddps` model üzerinde 12 çevrim gecikme, elle karıştırmalı sürüm ise bir `movshdup` + `addps` + `movhlps/unpckhpd` + `addss` zinciri olarak daha az mikro-işlem tutuyor.

8 şerit için önce iki 128 bitlik yarıyı topla:

```c
/* hsum256.c: 8 seritli toplam */
#include <stdio.h>
#include <immintrin.h>
__attribute__((target("avx"))) static float hsum256(__m256 v) {
    __m128 a = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
    a = _mm_add_ps(a, _mm_movehl_ps(a, a));
    a = _mm_add_ss(a, _mm_movehdup_ps(a));
    return _mm_cvtss_f32(a);
}
__attribute__((target("avx"))) int main(void) {
    printf("%g\n", hsum256(_mm256_setr_ps(1,2,3,4,5,6,7,8)));
    return 0;
}
```

Aşama sayısı $\log_2 k$. Bu yüzden indirgemenin çok sayıda elemana karşı maliyeti önemsiz, ama küçük döngülerde başlangıç maliyeti olarak görünür (Ders 11.1'deki CPE doğrusu).

---

## 2. Dot product: bütün dersin özeti

```c
/* nokta.c: dot product: bes surum */
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>
#include "olcum.h"

__attribute__((target("avx,fma"))) static inline float hs(__m256 v) {
    __m128 a = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
    a = _mm_add_ps(a, _mm_movehl_ps(a, a));
    a = _mm_add_ss(a, _mm_movehdup_ps(a));
    return _mm_cvtss_f32(a);
}

__attribute__((noinline)) float nokta_c(const float *a, const float *b, long n) {
    float s = 0;
    for (long i = 0; i < n; i++) s += a[i] * b[i];
    return s;
}

__attribute__((noinline, target("sse4.1"))) float nokta_dp(const float *a, const float *b, long n) {
    __m128 s = _mm_setzero_ps();
    long i = 0;
    for (; i + 4 <= n; i += 4)
        s = _mm_add_ss(s, _mm_dp_ps(_mm_loadu_ps(a + i), _mm_loadu_ps(b + i), 0xF1));
    float r = _mm_cvtss_f32(s);
    for (; i < n; i++) r += a[i] * b[i];
    return r;
}

__attribute__((noinline, target("avx,fma"))) float nokta_1(const float *a, const float *b, long n) {
    __m256 s = _mm256_setzero_ps();
    long i = 0;
    for (; i + 8 <= n; i += 8)
        s = _mm256_fmadd_ps(_mm256_loadu_ps(a + i), _mm256_loadu_ps(b + i), s);
    float r = hs(s);
    for (; i < n; i++) r += a[i] * b[i];
    return r;
}

__attribute__((noinline, target("avx,fma"))) float nokta_4(const float *a, const float *b, long n) {
    __m256 s0 = _mm256_setzero_ps(), s1 = s0, s2 = s0, s3 = s0;
    long i = 0;
    for (; i + 32 <= n; i += 32) {
        s0 = _mm256_fmadd_ps(_mm256_loadu_ps(a + i),      _mm256_loadu_ps(b + i),      s0);
        s1 = _mm256_fmadd_ps(_mm256_loadu_ps(a + i + 8),  _mm256_loadu_ps(b + i + 8),  s1);
        s2 = _mm256_fmadd_ps(_mm256_loadu_ps(a + i + 16), _mm256_loadu_ps(b + i + 16), s2);
        s3 = _mm256_fmadd_ps(_mm256_loadu_ps(a + i + 24), _mm256_loadu_ps(b + i + 24), s3);
    }
    s0 = _mm256_add_ps(_mm256_add_ps(s0, s1), _mm256_add_ps(s2, s3));
    float r = hs(s0);
    for (; i < n; i++) r += a[i] * b[i];
    return r;
}

typedef float fn(const float *, const float *, long);

int main(void) {
    long n = 4096;
    float *a = aligned_alloc(64, 4 * (size_t)n), *b = aligned_alloc(64, 4 * (size_t)n);
    unsigned s = 12345;
    for (long i = 0; i < n; i++) {
        s = s * 1664525u + 1013904223u; a[i] = (float)(s >> 8) / 16777216.0f;
        s = s * 1664525u + 1013904223u; b[i] = (float)(s >> 8) / 16777216.0f;
    }
    double dogru = 0; for (long i = 0; i < n; i++) dogru += (double)a[i] * (double)b[i];
    printf("double ile dogru deger: %.6f\n", dogru);
    struct { const char *ad; fn *f; } t[] = { {"C", nokta_c}, {"SSE4.1 dpps", nokta_dp}, {"AVX FMA, 1 birikimci", nokta_1}, {"AVX FMA, 4 birikimci", nokta_4} };
    for (int k = 0; k < 4; k++) {
        double en = 1e9; volatile float r = 0;
        for (int q = 0; q < 7; q++) {
            double b0 = simdi();
            for (int j = 0; j < 20000; j++) { r = t[k].f(a, b, n); BELLEK(); }
            double e = simdi() - b0; if (e < en) en = e;
        }
        printf("%-22s sonuc=%.6f  hata=%+.2e  %.3f ns/eleman\n", t[k].ad, r, r - dogru, en * 1e9 / (20000.0 * n));
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize nokta.c -o n && ./n
double ile dogru deger: 1010.155606
C                      sonuc=1010.155762  hata=+1.56e-04  0.872 ns/eleman
SSE4.1 dpps            sonuc=1010.155334  hata=-2.72e-04  0.292 ns/eleman
AVX FMA, 1 birikimci   sonuc=1010.155823  hata=+2.17e-04  0.429 ns/eleman
AVX FMA, 4 birikimci   sonuc=1010.155640  hata=+3.37e-05  0.153 ns/eleman
```

Burada iki şey gözüküyor:

- **Hız:** 4 birikimcili sürüm tek birikimciliden 2.8 kat hızlı (Rosetta altında). Ders 11.2'deki gecikme sınırı. Ders 11.8'deki `llvm-mca` da Skylake için `dot` tek birikimciyle 0.50, 4 birikimciyle 0.125 çevrim/eleman öngörmüştü.
- **Sonuç:** her sürüm **farklı bir sayı** veriyor. Doğru değer `double` ile hesaplanan 1010.155606. `float` toplamı sıralı olduğundan sonraki toplananların hatası birikir; SIMD ise toplamaları farklı sırada yapıyor. Bu veride 4 birikimcili sürümün hatası C sürümünden 4.6 kat küçük çıktı; ara toplamlar küçük kaldığı için yuvarlama hatası da küçülüyor. Bu tek bir ölçüm, bir garanti değil.

Yani kayan nokta toplaması birleşmeli olmadığı için (Ders 3.14) **SIMD'e geçmek sonucu değiştirir**. Çoğu uygulamada sorun yok, ama "SIMD sürümü C ile bit bit aynı olmalı" testi kayan noktada yanlıştır. Bunun için derleyici yalnız `-ffast-math` ile benzer yeniden sıralamaya izin verir (Ders 11.15).

`_mm_dp_ps(a, b, 0xF1)`'de `0xF`: hangi şeritler çarpılacak, `1`: sonuç hangi şeride yazılacak. `dpps` esnek ama pahalı bir komut (yukarıdaki tablo), uzun döngülerde `fmadd` tercih edilir.

---

## 3. Kalan elemanlar

Beş yol, en iyiden kötüye değil, duruma göre:

| Yol | Nasıl | Uygun olduğu yer |
| --- | --- | --- |
| Skaler döngü | Ders 11.7'deki gibi | Kısa, her yerde çalışır; kalan pahalıysa `n` küçükken yavaş |
| Üst üste son blok | `loadu(a + n - 8)` ile bir kez daha | İdempotent işlem, en az 8 eleman |
| Doldurma | Diziyi 8'in katına uzat | Veri boyutu sende |
| Maskeli yükleme | `maskload` (AVX), `maskz_loadu` (AVX-512) | Dallanma yok, sayfa güvenli |
| Hiçbiri | `aligned` + bilinçli taşma | `strlen` tipi, Ders 11.12 |

Maskeli yüklemenin en büyük getirisi: **maskelenmiş şeritler için bellek hatası oluşmaz.** Bunu sayfa sonunda deneyelim:

```c
/* kalan.c: dongunun sonundaki 0-7 eleman, sayfa sinirinda */
#include <stdio.h>
#include <signal.h>
#include <setjmp.h>
#include <sys/mman.h>
#include <unistd.h>
#include <immintrin.h>

static sigjmp_buf j;
static void yakala(int s) { siglongjmp(j, s); }

__attribute__((target("avx"))) static float topla_mask(const float *p, int m) {
    static const int tablo[16] = { -1,-1,-1,-1,-1,-1,-1,-1, 0,0,0,0,0,0,0,0 };
    __m256i maske = _mm256_loadu_si256((const __m256i *)(tablo + 8 - m));
    __m256 v = _mm256_maskload_ps(p, maske);
    __m128 a = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
    a = _mm_add_ps(a, _mm_movehl_ps(a, a));
    a = _mm_add_ss(a, _mm_movehdup_ps(a));
    return _mm_cvtss_f32(a);
}

__attribute__((target("avx"))) static float topla_duz(const float *p) {
    __m256 v = _mm256_loadu_ps(p);
    __m128 a = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
    a = _mm_add_ps(a, _mm_movehl_ps(a, a));
    a = _mm_add_ss(a, _mm_movehdup_ps(a));
    return _mm_cvtss_f32(a);
}

int main(void) {
    long sayfa = sysconf(_SC_PAGESIZE);
    char *m = mmap(0, 2 * sayfa, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    mprotect(m + sayfa, sayfa, PROT_NONE);
    float *son = (float *)(m + sayfa) - 3;       /* sadece 3 float bizim */
    son[0] = 1; son[1] = 2; son[2] = 3;
    signal(SIGSEGV, yakala);
    printf("sayfa boyutu %ld\n", sayfa);
    int s = sigsetjmp(j, 1);
    if (s == 0) printf("maskload, 3 eleman: %g\n", topla_mask(son, 3));
    else printf("maskload: sinyal %d\n", s);
    s = sigsetjmp(j, 1);
    if (s == 0) printf("loadu, 8 eleman: %g\n", topla_duz(son));
    else printf("loadu: sinyal %d (SIGSEGV)\n", s);
    return 0;
}
```

```
$ clang -O2 kalan.c -o k && ./k
sayfa boyutu 4096
maskload, 3 eleman: 6
loadu, 8 eleman: sinyal 11 (SIGSEGV)
```

Bir sonraki sayfa `PROT_NONE`. 3 elemanlı `maskload` sadece kendi 12 byte'ını okuyor, normal `loadu` sayfanın sonunu aşıyor ve program ölüyor. Bu özellik Ders 11.13'te AVX-512'nin çok daha temiz sürümünde tekrar çıkacak (`_mm512_maskz_loadu_epi64`).

`tablo + 8 - m` numarası: 16 elemanlı `-1 ... 0` dizisinden, `m` tane `-1` ile başlayan 8 elemanlı kesit alır, böylece her uzunluk için tek bir tablo yeter.

---

## 4. Koşullu indirgeme

"Pozitifleri topla ve say" Ders 5.5'in vektörlenmiş hali:

```c
/* kosul.c: kosullu toplama, sayma, en buyuk ve yeri */
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>

__attribute__((target("avx"))) static float hs(__m256 v) {
    __m128 a = _mm_add_ps(_mm256_castps256_ps128(v), _mm256_extractf128_ps(v, 1));
    a = _mm_add_ps(a, _mm_movehl_ps(a, a));
    a = _mm_add_ss(a, _mm_movehdup_ps(a));
    return _mm_cvtss_f32(a);
}

__attribute__((target("avx,popcnt"))) int main(void) {
    float a[16];
    for (int i = 0; i < 16; i++) a[i] = (float)((i * 7) % 16) - 5;
    for (int i = 0; i < 16; i++) printf("%g ", a[i]);
    puts("");
    __m256 s = _mm256_setzero_ps(), sifir = _mm256_setzero_ps();
    int adet = 0;
    for (int i = 0; i + 8 <= 16; i += 8) {
        __m256 v = _mm256_loadu_ps(a + i);
        __m256 m = _mm256_cmp_ps(v, sifir, _CMP_GT_OQ);
        s = _mm256_add_ps(s, _mm256_and_ps(v, m));
        adet += __builtin_popcount((unsigned)_mm256_movemask_ps(m));
    }
    printf("pozitiflerin toplami %g, adedi %d\n", hs(s), adet);
    float kt = 0; int ka = 0; for (int i = 0; i < 16; i++) if (a[i] > 0) { kt += a[i]; ka++; }
    printf("C ile: %g, %d\n", kt, ka);

    /* en buyuk elemanin yeri: maks yay, esit olan seridi bul */
    __m256 v = _mm256_loadu_ps(a);
    __m256 t = _mm256_max_ps(v, _mm256_permute_ps(v, _MM_SHUFFLE(2, 3, 0, 1)));
    t = _mm256_max_ps(t, _mm256_permute_ps(t, _MM_SHUFFLE(1, 0, 3, 2)));
    t = _mm256_max_ps(t, _mm256_permute2f128_ps(t, t, 1));
    int yer = __builtin_ctz((unsigned)_mm256_movemask_ps(_mm256_cmp_ps(v, t, _CMP_EQ_OQ)));
    printf("ilk 8 icinde en buyuk %g, yeri %d\n", _mm256_cvtss_f32(t), yer);
    return 0;
}
```

```
$ clang -O2 kosul.c -o s && ./s
-5 2 9 0 7 -2 5 -4 3 10 1 8 -1 6 -3 4 
pozitiflerin toplami 55, adedi 10
C ile: 55, 10
ilk 8 icinde en buyuk 9, yeri 2
```

- `cmp` her şerit için maske üretir.
- `and` ile koşulu sağlamayanlar 0 olur (`+0` etkisi yok).
- `movemask` + `popcount`: kaç şerit eşleşti (Ders 5.8).

En büyüğün **yerini** bulmak yine yatay bir iş: `max`'i şeritler arasında yaymak (`permute` ile bir kaydırma, sonra bir daha), sonra yayılmış maksimumun orijinal vektörde nerede olduğunu `cmp` + `movemask` + `ctz` ile bulmak.

Bu kalıp (`cmp → movemask → ctz`) bir sonraki dersin temeli: `strlen` tam olarak budur, ama byte'larda.

---

## Alıştırmalar

**1** – `hsum256`'daki `_mm256_castps256_ps128` makine komutu üretir mi? `_mm256_extractf128_ps(v, 1)` üretir mi? Neden farklı?

**2** – `dpps`'in `0xF1` argümanındaki bitleri açıkla. `0x71` olsa ne değişir? `(1,2,3,4)` ve `(5,6,7,8)` için `0xF1` sonucu?

**3** – `nokta.c`'de 8 birikimci dene. Yuvarlama hatasının azalması sürüyor mu? Eleman sayısı arttıkça hata yaklaşık nasıl büyür?

**4** – Maskeli yükleme yerine, kalan elemanları yerel bir `float t[8] = {0}`'a kopyalayıp normal yükleme nasıl yapılır? Maliyetini tartış.

**5** – `kosul.c`'deki "en büyüğün yeri" kodu 8 elemanda eşit iki maksimum varsa hangisini döndürür? `NaN` içeren bir dizide ne olur?

<details>
<summary>Cevaplar</summary>

**1** – `cast` üretmez: `ymm0`'ın alt yarısı zaten `xmm0`, yalnızca tip değişiyor. `extractf128` üretir (`vextractf128`), çünkü üst yarıyı başka register'a taşıması gerekir.

**2** – Üst 4 bit: hangi şeritler çarpılıp toplanacak (`F` = hepsi). Alt 4 bit: sonuç hangi şeride yazılacak (`1` = lane 0). `0x71`: lane 3 hariç, yalnız `1*5 + 2*6 + 3*7 = 38`. `0xF1`: $1 \cdot 5 + 2 \cdot 6 + 3 \cdot 7 + 4 \cdot 8 = 70$. (Çalıştırdık: 70, ikinci lane 0.)

**3** – Elde edilen sonuç veriye bağlı. Beklenen: birikimci sayısı arttıkça her birinin aldığı toplamlar küçüldüğünden hata azalma eğiliminde, ama her ek birikimci yeni bir bitiş-toplama adımı da ekler. Rasgele yuvarlamada hata kabaca $\sqrt{n}$ gibi büyür.

**4** – `memcpy(t, p, m * sizeof(float))` ile kopyala, normal yükle. Basit ve taşınabilir, ama `memcpy` çağrısı, dal veya tablo ek maliyet getirir. Toplam birkaç nanosaniye, küçük döngülerde kayda değer.

**5** – `ctz` en düşük bitli eşleşeni, yani ilk geçeni verir. `_mm256_max_ps(a, b)`'nin NaN davranışı: bir operand NaN ise ikinci operandı döndürür; sonuç argüman sırasına bağlı olur, sessizce NaN'ı kaybedebilir. Hata yapmamak için NaN'ları önceden ele almak gerekir.

</details>

---

## Kaynaklar

- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 2: `HADDPS`, `DPPS`, `VMASKMOVPS`, `CMPPS`.
- Agner Fog, *Optimizing subroutines in assembly language*, yatay işlemler.
- Nicholas J. Higham, *Accuracy and Stability of Numerical Algorithms* (2. baskı), Bölüm 4: toplama sıralaması ve hata.

**Sıradaki ders:** SIMD ile string işlemleri. `pcmpeqb` ve `pmovmskb` ile `strlen` ve `memchr`; Faz 4 ve Faz 5'teki sürümlerle hız karşılaştırması.
