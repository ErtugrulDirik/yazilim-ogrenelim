---
title: "11.7 SSE intrinsics"
description: "Assembly yazmadan SIMD komutu kullanmak: intrinsic'in ne olduğu ve clang başlığında aslında bir vektör toplaması olması, _mm_add_ps isim şeması (ps, ss, epi32, si128); iki float dizisini kalan döngüsüyle toplama ve 0-100 uzunlukta C ile sınama; load ile loadu farkı, movaps ve hizasız adres; karşılaştırmanın maske üretmesi, and/andnot ile dalsız seçim; add_ps ve add_ss, rsqrtps yaklaşımı, -O0 ile -O2 assembly'si ve üst üste binen dizi tuzağı."
---

Ders 11.6'da derleyicinin ürettiği vektör komutlarını okuduk. Şimdi kendimiz yazıyoruz. Assembly'e inmeye gerek yok: **intrinsic**, C'den çağrılan ve genellikle tek bir makine komutuna karşılık gelen fonksiyondur.

---

## 1. İsim şeması

```c
#include <immintrin.h>     /* butun x86 SIMD basliklari */
```

İsim üç parçadan oluşur:

```
_mm_add_ps
 |   |   |
 |   |   +-- veri tipi: ps = packed single (4 x float)
 |   +------ islem
 +---------- genislik: _mm = 128 bit, _mm256 = 256, _mm512 = 512
```

| Sonek | Anlamı |
| --- | --- |
| `ps` / `pd` | paket `float` / `double` |
| `ss` / `sd` | yalnız lane 0, `float` / `double` (skaler) |
| `epi8/16/32/64` | paket işaretli tamsayı |
| `epu8/16/32/64` | paket işaretsiz tamsayı |
| `si128` / `si256` | tipi olmayan bitler (`and`, `load` gibi) |

Tipler: `__m128` (float), `__m128d` (double), `__m128i` (tamsayı). Bu tipler her zaman 16 byte hizalıdır. Tüm intrinsic'lerin listesi: Intel Intrinsics Guide.

---

## 2. İki diziyi toplamak

```c
/* topla.c: iki float dizisini toplamak */
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>
#include "olcum.h"

__attribute__((noinline))
void topla_c(float *d, const float *a, const float *b, long n) {
    for (long i = 0; i < n; i++) d[i] = a[i] + b[i];
}

__attribute__((noinline))
void topla_sse(float *d, const float *a, const float *b, long n) {
    long i = 0;
    for (; i + 4 <= n; i += 4) {               /* 4'erli govde */
        __m128 x = _mm_loadu_ps(a + i);
        __m128 y = _mm_loadu_ps(b + i);
        _mm_storeu_ps(d + i, _mm_add_ps(x, y));
    }
    for (; i < n; i++) d[i] = a[i] + b[i];     /* kalan 0-3 eleman */
}

__attribute__((noinline))
void topla_hizali(float *d, const float *a, const float *b, long n) {
    long i = 0;
    for (; i + 4 <= n; i += 4)
        _mm_store_ps(d + i, _mm_add_ps(_mm_load_ps(a + i), _mm_load_ps(b + i)));
    for (; i < n; i++) d[i] = a[i] + b[i];
}

typedef void fn(float *, const float *, const float *, long);

static double olc(fn *f, float *d, float *a, float *b, long n) {
    long tur = 200000000 / n;
    double en = 1e9;
    for (int t = 0; t < 7; t++) {
        double b0 = simdi();
        for (long r = 0; r < tur; r++) { f(d, a, b, n); BELLEK(); }
        double s = simdi() - b0;
        if (s < en) en = s;
    }
    return en * 1e9 / (tur * n);
}

int main(void) {
    long n = 4096;
    float *a = aligned_alloc(64, 4 * (size_t)n), *b = aligned_alloc(64, 4 * (size_t)n), *d = aligned_alloc(64, 4 * (size_t)n);
    for (long i = 0; i < n; i++) { a[i] = i * 0.5f; b[i] = i * 0.25f; }

    /* once dogruluk: her uzunluk icin C ile ayni mi? */
    float d2[128];
    for (long m = 0; m <= 100; m++) {
        topla_c(d2, a, b, m); topla_sse(d, a, b, m);
        for (long i = 0; i < m; i++) if (d[i] != d2[i]) { printf("FARK m=%ld i=%ld\n", m, i); return 1; }
    }
    puts("0..100 arasi her uzunlukta sonuclar ayni");

    printf("%-12s %.3f ns/eleman\n", "C", olc(topla_c, d, a, b, n));
    printf("%-12s %.3f ns/eleman\n", "SSE loadu", olc(topla_sse, d, a, b, n));
    printf("%-12s %.3f ns/eleman\n", "SSE load", olc(topla_hizali, d, a, b, n));
    return 0;
}
```

İskelet her SIMD döngüsünde aynı: **gövde** (4'erli) ve **kalan** (0–3 eleman). Bir SIMD fonksiyonuna asla güvenmeden önce kalan döngüsünü sınamak gerekir; hata çoğunlukla oradadır.

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize topla.c -o t && ./t
0..100 arasi her uzunlukta sonuclar ayni
C            0.297 ns/eleman
SSE loadu    0.084 ns/eleman
SSE load     0.085 ns/eleman
```

(Süreler Rosetta altında; x86 işlemcinin süresi değildir.) 3.5 kat kazanç ve `load` ile `loadu` arasında fark yok. C sürümünü `-fno-vectorize` ile derledik, aksi halde derleyici onu da SSE'ye çeviriyordu; karşılaştırmanın anlamı kalmazdı.

---

## 3. Bir intrinsic aslında nedir?

clang'in başlığına bakalım:

```
$ grep -A3 '^_mm_add_ps' /usr/lib/llvm-18/lib/clang/18/include/xmmintrin.h
_mm_add_ps(__m128 __a, __m128 __b)
{
  return (__m128)((__v4sf)__a + (__v4sf)__b);
}
```

Sıradan bir vektör toplaması. Derleyici bunu normal bir işlem gibi görüyor, yani optimize ediyor. Üç küçük fonksiyon:

```c
#include <immintrin.h>
__m128 topla(__m128 a, __m128 b) { return _mm_add_ps(a, b); }
__m128 ikikat(__m128 a) { return _mm_add_ps(_mm_add_ps(a, a), _mm_setzero_ps()); }
void kopya(float *d, const float *k) { _mm_storeu_ps(d, _mm_loadu_ps(k)); }
```

```
$ clang -O2 -S uzak.c -o -
topla:
	addps	%xmm1, %xmm0
	retq
ikikat:
	addps	%xmm0, %xmm0
	xorps	%xmm1, %xmm1
	addps	%xmm1, %xmm0
	retq
kopya:
	movups	(%rsi), %xmm0
	movups	%xmm0, (%rdi)
	retq
```

`ikikat`'taki `+ 0` kalkmadı, çünkü IEEE 754'te $-0 + 0 = +0$: "sıfır eklemek hiçbir şey yapmaz" kuralı kayan noktada yanlıştır (Ders 3.14). Derleyici intrinsic'in içini de bildiği için bu kuralları uyguluyor.

`-O0` ile aynı `topla` ise eğitici derecede kötü:

```
$ clang -O0 -S uzak.c -o -
topla:
	pushq	%rbp
	movq	%rsp, %rbp
	movaps	%xmm0, -48(%rbp)
	movaps	%xmm1, -64(%rbp)
	movaps	-48(%rbp), %xmm1
	movaps	-64(%rbp), %xmm0
	movaps	%xmm1, -16(%rbp)
	movaps	%xmm0, -32(%rbp)
	movaps	-16(%rbp), %xmm0
	addps	-32(%rbp), %xmm0
	popq	%rbp
	retq
```

Intrinsic'ler `-O0`'da satır içi fonksiyon olarak yığına yazılıp okunuyor. **`-O0` ile SIMD ölçme**, sonuç hiçbir şey ifade etmez (Ders 11.1).

---

## 4. Hizalı ve hizasız

`_mm_load_ps(p)` `movaps` üretir ve `p`'nin 16'ya hizalı olmasını **şart koşar**. `_mm_loadu_ps(p)` `movups` üretir, her adresi kabul eder.

```c
/* hiza.c: hizali yukleme, hizasiz adres */
#include <stdio.h>
#include <stdalign.h>
#include <immintrin.h>

alignas(16) float dizi[8] = { 1, 2, 3, 4, 5, 6, 7, 8 };

__attribute__((noinline)) void ilk(float *d, const float *p) {
    _mm_storeu_ps(d, _mm_load_ps(p));          /* movaps ister */
}
__attribute__((noinline)) void ilku(float *d, const float *p) {
    _mm_storeu_ps(d, _mm_loadu_ps(p));         /* movups */
}

int main(void) {
    float d[4];
    ilku(d, dizi + 1);  printf("hizasiz loadu: %g\n", d[0]);
    ilk(d, dizi);       printf("hizali load  : %g\n", d[0]);
    fflush(stdout);
    ilk(d, dizi + 1);   printf("hizasiz load : %g\n", d[0]);
    return 0;
}
```

```
$ clang -O2 -g hiza.c -o h && objdump -d --no-show-raw-insn h | grep -A3 '<ilk>:'
0000000000001150 <ilk>:
    1150:	movaps (%rsi),%xmm0
    1153:	movups %xmm0,(%rdi)
    1156:	ret
$ ./h; echo "cikis: $?"
hizasiz loadu: 2
hizali load  : 1
hizasiz load : 2
cikis: 0
```

Beklediğimiz `SIGSEGV` **gelmedi**. Intel kılavuzuna göre hizasız adresle `movaps` genel koruma hatası (`#GP`) üretir; Linux'ta bu `SIGSEGV` demektir. Bizim ortamda çeviriyi yapan Rosetta bu kontrolü yapmıyor. Yani **bu makinedeki sonuç gerçek bir x86 davranışı değil**. Yalnızca `movaps` ürettiğimizi doğruladık; hatanın kendisini sana kendi x86 makinende göstermek düşüyor (Alıştırma 4).

İki pratik gerçek:

- `load` yazmak `movaps` üretileceğini garanti etmez. Bu örneğin ilk sürümünde `_mm_cvtss_f32(_mm_load_ps(p))` yazmıştım ve derleyici yalnız 4 byte okuyan `movss` üretti (hizalama gerektirmez). Bu yüzden `ilk`, vektörün tamamını geri yazıyor.
- Modern işlemcilerde hizalı adrese yapılan `movups` ile `movaps` arasında pratik hız farkı yok. Hizasız yükleme bir önbellek satırını veya sayfayı aşarsa bedel ödenir. Yukarıda ölçülen sonuç (0.084 ve 0.085) bu mikro testte fark olmadığını söylüyor ama Rosetta altında, kesin kanıt değil.

**Ne zaman hangisi:** bilmiyorsan `loadu`. Hizayı garanti ettiysen `load` bir hata yakalama aracı olarak işe yarar (yanlış adres anında patlar), hız için değil.

Hizalı bellek almak için: `aligned_alloc(16, boyut)` (boyut hizanın katı olmalı), `alignas(16)` ile statik dizi. `malloc` x86-64 glibc'de 16 byte hizalıdır, 32 değil (Ders 11.8).

---

## 5. Karşılaştırma bir maskedir

```c
/* maske.c: karsilastirma sonucu bir maskedir */
#include <stdio.h>
#include <string.h>
#include <immintrin.h>

static void yaz(const char *ad, __m128 v) {
    float f[4]; unsigned u[4];
    _mm_storeu_ps(f, v); memcpy(u, f, 16);
    printf("%-10s %08x %08x %08x %08x\n", ad, u[0], u[1], u[2], u[3]);
}
static void yazf(const char *ad, __m128 v) {
    float f[4]; _mm_storeu_ps(f, v);
    printf("%-10s %g %g %g %g\n", ad, f[0], f[1], f[2], f[3]);
}

int main(void) {
    __m128 a = _mm_setr_ps(1, 5, -2, 9);
    __m128 esik = _mm_set1_ps(4);
    __m128 m = _mm_cmpgt_ps(a, esik);
    yazf("a", a);
    yaz("a > 4", m);
    printf("movemask   %d\n", _mm_movemask_ps(m));

    /* a[i] > 4 ise 4, degilse a[i]: dalsiz secim (Ders 11.4) */
    __m128 sonuc = _mm_or_ps(_mm_and_ps(m, esik), _mm_andnot_ps(m, a));
    yazf("kirpilmis", sonuc);
    yazf("min_ps", _mm_min_ps(a, esik));

    /* _ss sadece serit 0'a dokunur */
    __m128 x = _mm_setr_ps(1, 2, 3, 4), y = _mm_setr_ps(10, 20, 30, 40);
    yazf("add_ps", _mm_add_ps(x, y));
    yazf("add_ss", _mm_add_ss(x, y));

    /* yaklasik ters karekok ve dogrusu */
    __m128 v = _mm_setr_ps(2, 3, 100, 12345);
    yazf("1/sqrt", _mm_div_ps(_mm_set1_ps(1), _mm_sqrt_ps(v)));
    yazf("rsqrtps", _mm_rsqrt_ps(v));
    return 0;
}
```

```
$ clang -O2 maske.c -o m && ./m
a          1 5 -2 9
a > 4      00000000 ffffffff 00000000 ffffffff
movemask   10
kirpilmis  1 4 -2 4
min_ps     1 4 -2 4
add_ps     11 22 33 44
add_ss     11 2 3 4
1/sqrt     0.707107 0.57735 0.1 0.00900025
rsqrtps    0.707098 0.577347 0.0999997 0.00900025
```

Karşılaştırma `true`/`false` döndürmüyor: her şerit için **tüm bitleri 1 ya da 0** olan bir maske üretiyor. Bu Ders 5.5'teki dalsız kodun dört şeritli hali:

$$\text{sonuç} = (m \land x) \lor (\lnot m \land y)$$

- `_mm_and_ps(m, esik)`: koşul doğruysa `esik`, değilse 0.
- `_mm_andnot_ps(m, a)`: `(~m) & a` (dikkat: **ilk** argüman değilleniyor).
- `_mm_movemask_ps`: her şeridin en yüksek bitini 4 bitlik bir tamsayıya toplar. `10 = 0b1010`: lane 1 ve 3 eşleşti. C'ye dönüş kapısıdır; Ders 11.12'nin temel aleti.

`add_ss` yalnız lane 0'ı topluyor, diğer şeritleri **ilk argümandan** kopyalıyor (`11 2 3 4`).

`_mm_rsqrt_ps` $1/\sqrt{x}$'in hızlı **yaklaşığı**: tablodan okunuyor, hatası Intel'in belgesine göre en fazla $1.5 \times 2^{-12}$. Ders 5.18'in "hızlı ters karekök"ünün donanıma inmiş hali. Tablo uygulamaya bağlı, yani farklı işlemcide son basamaklar değişebilir: burada gördüğün değerler Rosetta'nınki.

---

## 6. Üst üste binen diziler

Ders 11.5'te derleyiciye `restrict` sözü vermenin önemini gördük. Intrinsic yazarken aynı sorumluluk sende. `d = a + 1` ile:

```c
for (int i = 0; i < 8; i++) c[i + 1] = c[i] + b[i];       /* skaler */
for (int i = 0; i + 4 <= 8; i += 4)
    _mm_storeu_ps(a + 1 + i, _mm_add_ps(_mm_loadu_ps(a + i), _mm_loadu_ps(b + i)));
```

Başlangıçta her şey 1 ise:

```
$ ./u
1 2 3 4 5 6 7 8 9
1 2 2 2 2 3 2 2 2
```

İlk satır skaler sürüm: her eleman bir öncekini kullanıyor. İkincisi SSE: sürüm dört elemanı **aynı anda** okuyor, yani önceki turda yazılan değeri görmüyor. Derleyici bu farkı kontrol ederdi (Ders 11.5); elle yazılmış intrinsic'te o kontrol yok.

---

## Alıştırmalar

**1** – `_mm_add_ss(x, y)` ile `_mm_add_ps(x, y)` arasındaki farkı `x = (1,2,3,4)`, `y = (10,20,30,40)` için el ile yaz.

**2** – Her şeridin mutlak değerini alan tek satırı yaz. (İpucu: IEEE 754'te işaret biti nerede, `-0.0f`'in bit deseni ne?)

**3** – `n = 4k + 3` için kalan döngüsü en fazla kaç tur döner? Yerine `_mm_loadu_ps` ile son 4 elemanı üst üste bindirerek işlemek neden yalnız idempotent işlerde güvenli? (Ders 11.3)

**4** – Elinde gerçek bir x86 makinesi varsa `hiza.c`'yi çalıştır. Hangi satırda, hangi sinyalle ölüyor? `gdb` ile komut adresine bak.

**5** – `_mm_load_ps` ile yazılan döngüde clang `addps (%rdx,%r8,4), %xmm0` gibi bellek operandlı komut üretebiliyor, `loadu`'da üretmiyor (SSE'de). Neden? AVX'in VEX kodlaması bunu nasıl değiştiriyor?

<details>
<summary>Cevaplar</summary>

**1** – `add_ps`: `11 22 33 44`. `add_ss`: `11 2 3 4`.

**2** – `_mm_andnot_ps(_mm_set1_ps(-0.0f), v)`. `-0.0f` yalnız işaret biti 1 olan sayıdır; `andnot` o biti temizler. Denedik: `(-1, 2, -3, 0)` için `1 2 3 0`.

**3** – En fazla 3 tur. Son 4'lüyü üst üste bindirmek bazı elemanları iki kez işler; `a[i] = b[i] + c[i]` gibi bir atama için sonuç aynı (`idempotent`), `s += a[i]` gibi bir toplamada iki kez eklenir, yanlış olur.

**4** – Kendi makinende çalıştırmalısın; biz Rosetta altında hatayı üretemedik. Intel SDM'ye göre `movaps` hizasız adreste `#GP` üretir, Linux `SIGSEGV` gönderir.

**5** – Eski SSE kodlamasında bellek operandı olan aritmetik komutlar 16 byte hizalamayı şart koşar; `loadu` hizasız olabildiğinden derleyici onu `addps`'in içine katamaz, ayrı bir `movups` kullanır. VEX (Ders 11.8) ile kodlanan `vaddps` bellek operandını hizasız da kabul eder, bu yüzden AVX modunda kaynaştırma serbestleşir; Ders 11.6'daki AVX çıktısında `vaddps (%rdx,%r8,4), %ymm0, %ymm0` görmüştük.

</details>

---

## Kaynaklar

- Intel, *Intel Intrinsics Guide* (intel.com/content/www/us/en/docs/intrinsics-guide).
- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 2: `MOVAPS`, `RSQRTPS`, `CMPPS`.
- Agner Fog, *Optimizing subroutines in assembly language*, Bölüm 13 (vektör programlama).
- Clang kaynak kodu: `lib/Headers/xmmintrin.h`.

**Sıradaki ders:** AVX ve AVX2. `__m256`, 8'li float işlemleri, FMA, hizalı ve hizasız yükleme.
