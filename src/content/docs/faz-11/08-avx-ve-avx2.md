---
title: "11.8 AVX ve AVX2"
description: "256 bit: __m256 ile 8 float işlemleri, VEX kodlaması ve üç operand, derleme bayrağı olmadan always_inline hatası; FMA'nın tek yuvarlaması ve a*a+c'nin iki adımda 0, fmadd ile 0x1p-24 vermesi, -ffp-contract; malloc'un yalnız yüzde 43 oranla 32 byte hizalı olması; 256 bitin iki 128 bitlik şerit olması, hadd ve unpack tuzağı; vzeroupper; gather; llvm-mca ile Skylake tahmini ve daxpy tablosu; Horner ve FMA ile sin(x): 3.6e-6 hata."
---

Ders 11.7'de 4 şeritle çalıştık. AVX register'ı iki kat geniş: 8 `float` ya da 4 `double`. AVX2 aynı genişliği tamsayılara getiriyor, FMA ise çarpma ve toplamayı tek komutta birleştiriyor. Kod neredeyse aynı kalıyor, ama birkaç tuzak yeni.

---

## 1. Bayrak ve hedef

`_mm` yerine `_mm256`, `__m128` yerine `__m256`. Bayraksız derlersen:

```
$ clang -O2 -c avxyok.c
avxyok.c:2:43: error: always_inline function '_mm256_add_ps' requires target feature 'avx', but would be inlined into function 'topla' that is compiled without support for 'avx'
    2 | __m256 topla(__m256 a, __m256 b) { return _mm256_add_ps(a, b); }
      |                                           ^
avxyok.c:2:43: error: AVX vector argument of type '__m256' (vector of 8 'float' values) without 'avx' enabled changes the ABI
```

İki çözüm: tüm dosya için `-mavx2 -mfma`, ya da tek fonksiyon için `__attribute__((target("avx2,fma")))` (Ders 11.6). Üretim kodunda ikincisi daha güvenli: aksi takdirde dosyadaki **her** fonksiyon, en sıradan olanı bile, AVX komutu içerebilir ve eski işlemcide `SIGILL` verir.

AVX'in bir başka getirisi **VEX kodlaması**: `vaddps %ymm2, %ymm1, %ymm0` üç operandlıdır, kaynaklar bozulmaz (`addps` iki operandlıydı ve hedefi eziyordu). Bu yüzden `-mavx2` ile derlenmiş kodda fazladan `movaps` kopyaları kaybolur; 128 bit işlemler de `vaddps %xmm...` olarak VEX ile yazılır.

---

## 2. FMA: birleşik çarpma ve toplama

`a * b + c` normalde **iki** yuvarlama içerir: önce çarpım, sonra toplam. FMA (*fused multiply-add*) $a \times b + c$'yi sonsuz kesinlikle hesaplayıp **bir kez** yuvarlar.

```c
/* fma.c: tek yuvarlama ile iki yuvarlama */
#include <stdio.h>
#include <immintrin.h>

int main(void) {
    volatile float a = 1.0f + 0x1p-12f;
    volatile float c = -(1.0f + 0x1p-11f);
    float iki = (float)a * (float)a;   /* once carp, yuvarla */
    iki = iki + c;                     /* sonra topla, yuvarla */
    __m128 sa = _mm_set_ss(a), sc = _mm_set_ss(c);
    float tek = _mm_cvtss_f32(_mm_fmadd_ss(sa, sa, sc));
    printf("a*a+c, iki adim : %a  (%g)\n", iki, iki);
    printf("a*a+c, fmadd    : %a  (%g)\n", tek, tek);
    printf("gercek deger    : 0x1p-24\n");
    return 0;
}
```

```
$ clang -O2 -mfma fma.c -o f && ./f
a*a+c, iki adim : 0x0p+0  (0)
a*a+c, fmadd    : 0x1p-24  (5.96046e-08)
gercek deger    : 0x1p-24
```

$a = 1 + 2^{-12}$ için $a^2 = 1 + 2^{-11} + 2^{-24}$. Son terim `float`'ın 24 bitlik mantisine sığmıyor; iki adımda kayboluyor, sonuç **0**. FMA ise doğru sonucu veriyor. Hata analizi yapan kodlarda (Ders 3.14'teki yuvarlama hatası) bu kritik.

Kritik soru: derleyici `a * b + c` yazınca FMA kullanır mı?

```c
float bir(float a, float b, float c) { return a * b + c; }
float iki(float a, float b, float c) { float t = a * b; return t + c; }
```

```
$ clang -O2 -mfma -S birlesme.c -o -
bir:
	vfmadd213ss	%xmm2, %xmm1, %xmm0
iki:
	vmulss	%xmm1, %xmm0, %xmm0
	vaddss	%xmm2, %xmm0, %xmm0

$ clang -O2 -mfma -ffp-contract=off -S birlesme.c -o -       # ikisi de mul + add

$ clang -O2 -mfma -ffp-contract=fast -S birlesme.c -o -      # ikisi de vfmadd
```

clang'in varsayılanı (`on`) yalnız **aynı ifade** içinde birleştirir: `bir` birleşti, `iki` ayrı ifadeler olduğu için birleşmedi. Yani bayrak değişince **sayısal sonuç değişir**. Tekrarlanabilir kayan nokta gerekiyorsa (`-ffp-contract=off`) bilinçli bir karar vermek lazım.

Komut adındaki `213` operandların sırasını söyler (`132`, `213`, `231`), derleyiciye register seçme esnekliği verir. Bizim intrinsic'te `_mm256_fmadd_ps(a, b, c)` her zaman $a \times b + c$.

---

## 3. Hizalama artık 32

`_mm256_load_ps` 32'ye hizalı adres ister. `malloc` buna söz vermez:

```c
/* hiza.c: malloc 32'ye hizali degil */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
int main(void) {
    int h16 = 0, h32 = 0, n = 100000;
    void *p[100000];
    for (int i = 0; i < n; i++) {
        p[i] = malloc(32 + (size_t)(i % 7) * 16);
        h16 += ((uintptr_t)p[i] % 16) == 0;
        h32 += ((uintptr_t)p[i] % 32) == 0;
    }
    printf("malloc: 16'ya hizali %d/%d, 32'ye hizali %d/%d\n", h16, n, h32, n);
    return 0;
}
```

```
$ clang -O2 hiza.c -o h && ./h
malloc: 16'ya hizali 100000/100000, 32'ye hizali 42858/100000
```

İşaretçi her zaman 16'nın katı, ama 32'nin katı olması tesadüf. `_mm256_load_ps` ile yazılmış bir kod `malloc`'la **bazen** çalışır, ki bu en kötü hata türüdür. Bellek için `aligned_alloc(32, ...)` kullan; `struct` içinde `__m256` varsa ve `malloc`'layacaksan `aligned_alloc` şart.

---

## 4. 256 bit aslında iki 128 bit

AVX'in en sinsi tasarım kararı: çoğu komut 256 bitlik register'ı **iki bağımsız 128 bitlik şerit** gibi işler.

```c
/* serit.c: 256 bit, aslinda iki tane 128 bit */
#include <stdio.h>
#include <immintrin.h>

static void yaz(const char *ad, __m256 v) {
    float f[8]; _mm256_storeu_ps(f, v);
    printf("%-14s", ad);
    for (int i = 0; i < 8; i++) printf(" %5g", f[i]);
    printf("\n");
}

int main(void) {
    __m256 a = _mm256_setr_ps(1, 2, 3, 4, 5, 6, 7, 8);
    __m256 b = _mm256_setr_ps(10, 20, 30, 40, 50, 60, 70, 80);
    yaz("a", a);
    yaz("b", b);
    yaz("hadd(a,b)", _mm256_hadd_ps(a, b));
    yaz("unpacklo(a,b)", _mm256_unpacklo_ps(a, b));
    yaz("permute2f128", _mm256_permute2f128_ps(a, b, 0x21));
    __m128 alt = _mm256_castps256_ps128(a), ust = _mm256_extractf128_ps(a, 1);
    float f[4];
    _mm_storeu_ps(f, alt); printf("alt yari       %g %g %g %g\n", f[0], f[1], f[2], f[3]);
    _mm_storeu_ps(f, ust); printf("ust yari       %g %g %g %g\n", f[0], f[1], f[2], f[3]);

    /* gather: daginik indislerden yukle */
    float tablo[10] = { 0, 1.5f, 2.5f, 3.5f, 4.5f, 5.5f, 6.5f, 7.5f, 8.5f, 9.5f };
    __m256i idx = _mm256_setr_epi32(9, 0, 3, 3, 1, 7, 2, 5);
    yaz("gather", _mm256_i32gather_ps(tablo, idx, 4));
    return 0;
}
```

```
$ clang -O2 -mavx2 serit.c -o s && ./s
a                  1     2     3     4     5     6     7     8
b                 10    20    30    40    50    60    70    80
hadd(a,b)          3     7    30    70    11    15   110   150
unpacklo(a,b)      1    10     2    20     5    50     6    60
permute2f128       5     6     7     8    10    20    30    40
alt yari       1 2 3 4
ust yari       5 6 7 8
gather           9.5     0   3.5   3.5   1.5   7.5   2.5   5.5
```

`hadd` satırına bak. Yatay toplama sonucunun `3 7 11 15 30 70 110 150` olmasını beklersin, ama çıktı `3 7 30 70 | 11 15 110 150`: alt yarı `a` ve `b`'nin alt yarılarından, üst yarı üst yarılarından. `unpacklo` aynı: `1 10 2 20 | 5 50 6 60`. 128 bitlik sınırın üstünden veri geçirmek için özel komutlar lazım: `_mm256_permute2f128_ps` ve (Ders 11.10) `_mm256_permutevar8x32_ps`.

`extract` ve `cast` iki yarıya ulaşmanı sağlar: `_mm256_castps256_ps128` komut üretmez (yalnızca tip dönüşümü), `_mm256_extractf128_ps` üretir.

`_mm256_i32gather_ps` (AVX2) **gather**: dizinin dağınık indislerini yükler; tablo aramaları için. Yine de sekiz ayrı bellek okuması yapıyor, sihir değil.

---

## 5. vzeroupper

Fonksiyonu bir kez `ymm` kullanacak şekilde derleyelim:

```
$ clang -O2 -mavx2 -S vz.c -o -
	vmovups	(%rsi), %ymm0
	vaddps	%ymm0, %ymm0, %ymm0
	vmovups	%ymm0, (%rdi)
	vzeroupper
	retq
```

Kaynakta yazmadığımız `vzeroupper` geldi. Üst yarısı kirli `ymm` varken VEX olmayan eski SSE komutları çalışırsa bazı Intel çekirdeklerinde ağır geçiş cezası oluşur (Agner Fog'un mikromimari kılavuzu bunu ayrıntılı anlatır). Derleyici bunu ABI sınırında temizliyor. `-mno-vzeroupper` ile çıktıdaki sayısı sıfıra iniyor. Intrinsic'lerle `-mavx2` bayrağıyla derlediğin sürece sorun yok; **SSE ve AVX'i bayraksız elle karıştırmak** gerçek sorundur, çünkü orada VEX'siz `addps` üretilir.

---

## 6. Gerçek x86 için tahmin: llvm-mca

Rosetta altında AVX zamanları:

```c
/* daxpy.c: y[i] = a * x[i] + y[i], dort surum */
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>
#include "olcum.h"

__attribute__((noinline))
void c_s(float *y, const float *x, float a, long n) {
    for (long i = 0; i < n; i++) y[i] = a * x[i] + y[i];
}

__attribute__((noinline))
void sse_s(float *y, const float *x, float a, long n) {
    __m128 va = _mm_set1_ps(a);
    long i = 0;
    for (; i + 4 <= n; i += 4)
        _mm_storeu_ps(y + i, _mm_add_ps(_mm_mul_ps(va, _mm_loadu_ps(x + i)), _mm_loadu_ps(y + i)));
    for (; i < n; i++) y[i] = a * x[i] + y[i];
}

__attribute__((noinline, target("avx2")))
void avx_s(float *y, const float *x, float a, long n) {
    __m256 va = _mm256_set1_ps(a);
    long i = 0;
    for (; i + 8 <= n; i += 8)
        _mm256_storeu_ps(y + i, _mm256_add_ps(_mm256_mul_ps(va, _mm256_loadu_ps(x + i)), _mm256_loadu_ps(y + i)));
    for (; i < n; i++) y[i] = a * x[i] + y[i];
}

__attribute__((noinline, target("avx2,fma")))
void fma_s(float *y, const float *x, float a, long n) {
    __m256 va = _mm256_set1_ps(a);
    long i = 0;
    for (; i + 8 <= n; i += 8)
        _mm256_storeu_ps(y + i, _mm256_fmadd_ps(va, _mm256_loadu_ps(x + i), _mm256_loadu_ps(y + i)));
    for (; i < n; i++) y[i] = a * x[i] + y[i];
}

typedef void fn(float *, const float *, float, long);

int main(void) {
    long n = 4096;
    float *x = aligned_alloc(64, 4 * (size_t)n), *y = aligned_alloc(64, 4 * (size_t)n);
    for (long i = 0; i < n; i++) x[i] = (float)i;
    struct { const char *ad; fn *f; } t[] = { {"C", c_s}, {"SSE", sse_s}, {"AVX", avx_s}, {"AVX+FMA", fma_s} };
    for (int k = 0; k < 4; k++) {
        long tur = 100000000 / n; double en = 1e9;
        for (int r = 0; r < 7; r++) {
            for (long i = 0; i < n; i++) y[i] = 0;
            double b0 = simdi();
            for (long j = 0; j < tur; j++) { t[k].f(y, x, 1e-9f, n); BELLEK(); }
            double s = simdi() - b0; if (s < en) en = s;
        }
        printf("%-8s %.3f ns/eleman\n", t[k].ad, en * 1e9 / (tur * n));
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize -mfma daxpy.c -o d -lm && ./d
C        0.629 ns/eleman
SSE      0.108 ns/eleman
AVX      0.086 ns/eleman
AVX+FMA  0.153 ns/eleman
```

AVX, SSE'nin ancak **1.25 katı** hızlı ve FMA daha **yavaş**. Bu, AVX'in kendisi hakkında bir şey söylemiyor: bu ortamda altta çalışan işlemci 128 bit NEON ve Rosetta'nın FMA'yı nasıl çevirdiğini bilmiyoruz. **Buradan x86 sonucu çıkaramayız.** Bu dersin en dürüst cümlesi bu.

Çözüm: LLVM'in mikromimari modeliyle statik analiz yapan **llvm-mca**. Komut sırasını Skylake'in zamanlama modelinde çalıştırıp çevrim tahmin ediyor. Döngü gövdesini iki yorumla işaretliyoruz:

```c
#define B(ad) __asm__ volatile("# LLVM-MCA-BEGIN " #ad)
#define E(ad) __asm__ volatile("# LLVM-MCA-END " #ad)
for (long i = 0; i + 8 <= n; i += 8) { B(daxpy_avx);
    _mm256_storeu_ps(y + i, _mm256_add_ps(_mm256_mul_ps(va, _mm256_loadu_ps(x + i)), _mm256_loadu_ps(y + i)));
    E(daxpy_avx); }
```

```
$ clang -O2 -msse4.1 -mtune=skylake -S mca.c -o a.s
$ llvm-mca -mcpu=skylake -iterations=1000 a.s
```

Sonuçlar (çevrim/eleman; önbellek ıskaları ve döngü sayacının komutları dahil değil):

| Döngü | Tur başına çevrim | Eleman | Çevrim/eleman |
| --- | --- | --- | --- |
| `topla`, C | 1.01 | 1 | 1.012 |
| `topla`, SSE | 1.01 | 4 | 0.253 |
| `topla`, AVX | 1.01 | 8 | 0.127 |
| `daxpy`, C | 1.02 | 1 | 1.017 |
| `daxpy`, SSE | 1.02 | 4 | 0.254 |
| `daxpy`, AVX | 1.02 | 8 | 0.127 |
| `daxpy`, AVX+FMA | 1.01 | 8 | 0.127 |
| `dot`, 1 birikimci | 4.01 | 8 | 0.501 |
| `dot`, 4 birikimci | 4.01 | 32 | 0.125 |

Modele göre **Skylake'te tüm bu döngüler turda 1 çevrim** alıyor: hepsinde tek `store` var ve Skylake çevrimde bir `store` yapabiliyor. Kazanç doğrudan şerit sayısından geliyor; AVX, SSE'nin tam 2 katı. FMA bu örnekte hız katmıyor (`daxpy`'de sınır store, hesap değil), üç komutu ikiye düşürüp güç tasarrufu ve doğruluk getiriyor.

`dot` satırları Ders 11.2'nin tekrarı: tek birikimci varken bağımlılık zinciri FMA gecikmesine (4 çevrim) kilitleniyor, 4 birikimciyle 4 kat kazanç.

llvm-mca bir **model**: ıskaları, dal hatalarını, frekans düşüşünü bilmez. Yine de "bu döngü nerede tıkanıyor" sorusuna Rosetta'dan çok daha doğru cevap verir.

---

## 7. Küçük bir uygulama: sin(x)

Polinom yaklaşımı, FMA'nın tam alanıdır. Taylor dizisi, Horner biçiminde:

```c
/* yaksin.c: 8 serit polinom ile sin(x) */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <immintrin.h>
#include "olcum.h"

/* Taylor katsayilari, -pi/2..pi/2 */
__attribute__((noinline, target("avx2,fma")))
void sin8(float *d, const float *x, long n) {
    const __m256 c3 = _mm256_set1_ps(-1.0f / 6), c5 = _mm256_set1_ps(1.0f / 120),
                 c7 = _mm256_set1_ps(-1.0f / 5040), c9 = _mm256_set1_ps(1.0f / 362880);
    for (long i = 0; i + 8 <= n; i += 8) {
        __m256 v = _mm256_loadu_ps(x + i), k = _mm256_mul_ps(v, v);
        __m256 p = _mm256_fmadd_ps(c9, k, c7);       /* Horner */
        p = _mm256_fmadd_ps(p, k, c5);
        p = _mm256_fmadd_ps(p, k, c3);
        p = _mm256_fmadd_ps(p, k, _mm256_set1_ps(1));
        _mm256_storeu_ps(d + i, _mm256_mul_ps(p, v));
    }
}

__attribute__((noinline)) void sin_c(float *d, const float *x, long n) {
    for (long i = 0; i < n; i++) d[i] = sinf(x[i]);
}

int main(void) {
    long n = 4096;
    float *x = aligned_alloc(32, 4 * (size_t)n), *a = aligned_alloc(32, 4 * (size_t)n), *b = aligned_alloc(32, 4 * (size_t)n);
    for (long i = 0; i < n; i++) x[i] = -1.5707963f + 3.1415926f * (float)i / (float)(n - 1);
    sin8(a, x, n); sin_c(b, x, n);
    double enb = 0; for (long i = 0; i < n; i++) { double h = fabs((double)a[i] - sin((double)x[i])); if (h > enb) enb = h; }
    printf("en buyuk mutlak hata: %.2e\n", enb);
    double e1 = 1e9, e2 = 1e9;
    for (int r = 0; r < 7; r++) {
        double t = simdi(); for (int j = 0; j < 2000; j++) { sin8(a, x, n); BELLEK(); } double s = simdi() - t; if (s < e1) e1 = s;
        t = simdi(); for (int j = 0; j < 2000; j++) { sin_c(b, x, n); BELLEK(); } s = simdi() - t; if (s < e2) e2 = s;
    }
    printf("AVX2+FMA polinom: %.2f ns/eleman\nsinf (glibc)    : %.2f ns/eleman\n", e1 * 1e9 / (2000.0 * n), e2 * 1e9 / (2000.0 * n));
    return 0;
}
```

```
$ clang -O2 yaksin.c -o y -lm && ./y
en buyuk mutlak hata: 3.56e-06
AVX2+FMA polinom: 0.65 ns/eleman
sinf (glibc)    : 5.84 ns/eleman
```

Aralık $[-\pi/2, \pi/2]$ ile sınırlı ve hata `float` çözünürlüğünün üzerinde: gerçek bir `sinf` tam aralığa indirgeme yapar, son bit doğruluğu için çok daha iyi katsayılar kullanır. Bu 9 kat hızlı sayıyı bu yüzden `sinf` ile tam eşit görme. Grafik motorları ve DSP kodu bu değiş tokuşu bilerek yapar.

---

## Alıştırmalar

**1** – `dot` tablosunda 4 birikimcili sürüm neden 8 birikimci kullansaydık bile modelde 4 çevrimden aşağı inmeyebilir? (İpucu: 4 `fmadd` komutu toplam kaç yükleme yapıyor, Skylake çevrimde kaç yükleme yapar?)

**2** – `_mm256_hadd_ps(a, a)` için `a = 1,2,...,8` sonucunu tahmin et. 4 yatay toplamın düzgün sırada çıkması için hangi `permute` eklenmeli?

**3** – Aynı kaynak `-ffp-contract=off` ile `fast` arasında farklı sonuç verebilir. Bir kayan nokta testin hangi derleyici bayrağı değişiminde bozulur?

**4** – `yaksin.c`'de `c9` terimini sil ve hatayı ölç. Her terim hatayı yaklaşık kaç kat düşürüyor?

**5** – `llvm-mca` çıktısında `-timeline` bayrağını dene. Bağımlılık zincirini görebiliyor musun?

<details>
<summary>Cevaplar</summary>

**1** – Her `fmadd` iki bellek operandı alıyor (`a` ve `b`), yani 4 `fmadd` = 8 yükleme; Skylake çevrimde 2 yükleme yapar, bu 4 çevrim eder. Sınır yüklemeler; birikimci sayısını artırmak bir işe yaramaz.

**2** – Denedik: `3 7 3 7 11 15 11 15`. Her yarı kendi içinde çift olarak yazılıyor. Sıralı istiyorsan `_mm256_permutevar8x32_ps` ile `(0,1,4,5,...)` düzeltmesi gerek.

**3** – Tam karşılaştırma yapan birim testler (`==`) ve kaydedilmiş sayısal dosyalarla yapılan regresyon testleri. Aynı nedenle farklı makineler arasında farklı sonuç alınabilir; kayan nokta kodunu bir tolerans ile test et.

**4** – Denedik: `c9` olmadan hata `1.57e-04`, yani 44 kat daha büyük. Bu aralıkta sonraki terimin büyüklüğü $(\pi/2)^9/9! \approx 1.6 \times 10^{-4}$ ile tutarlı.

**5** – `-timeline` her komutun dağıtım, yürütme, emekliliğini (D, E, R) çevrim çizgisinde gösterir. Tek birikimcili `dot`'ta her fmadd önceki bitmeden başlayamaz; çizgide 4'er çevrim kayma görünür.

</details>

---

## Kaynaklar

- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 1, Bölüm 14 (AVX, FMA), Cilt 2: `VFMADD*`, `VZEROUPPER`.
- Agner Fog, *The microarchitecture of Intel, AMD and VIA CPUs* (AVX geçiş cezaları).
- LLVM, *llvm-mca: LLVM Machine Code Analyzer* belgeleri.
- Clang, "Controlling Floating Point Behavior": `-ffp-contract`.

**Sıradaki ders:** Tamsayı SIMD. `__m128i`, `int8_t` ve `int16_t` şeritleri, doymalı aritmetik, görüntü parlaklığı.
