---
title: "11.6 SIMD kavramı"
description: "Tek komutla birden çok veri: Flynn sınıflandırması (SISD, SIMD, MISD, MIMD), vektör register'ı ve lane kavramı, aynı 128 bitin byte/short/int/long olarak okunması, _mm_set_ps'in ters sırası; MMX'ten AVX-512'ye x86, NEON, SVE ve RVV genel bakışı; aynı döngünün addss, addps ve ymm ile vaddps'e derlenmesi; M2 üzerinde ölçülen 5.3 kat kazancın büyük dizide 1.7 kata düşmesi; desteklenmeyen komutla Illegal instruction ve çalışma zamanı seçimi."
---

Ders 11.2'de "$k$ tane birikimci" fikriyle bir döngüyü 8 kat hızlandırdık ve Ders 11.3'te döngü açmanın tek başına bir şey kazandırmadığını gördük: işlemcinin kapasitesi sınırlıydı. **SIMD** o kapasiteyi çoğaltıyor: tek komut, aynı işlemi 4, 8 ya da 16 veri üzerinde birden yapıyor. Bu dersten itibaren Faz 11'in ikinci yarısı buna ayrılıyor.

:::note[Bu derslerin ölçüm ortamı]
Bu fazın derslerini Apple M2 üzerinde hazırlıyoruz. x86 kodları (SSE, AVX) Docker içinde **Rosetta 2** çevirisiyle çalışıyor, ARM kodları doğrudan donanımda. Bunun sonuçları:

- Kodun **ne ürettiği** gerçek: x86 komutları tanımlı anlamlarıyla yürütülüyor ve sonuçları sınıyoruz.
- Rosetta altındaki **süreler x86 işlemcinin süreleri değil**. Yalnızca o ortamda ölçülmüş sayılar olarak veriyoruz.
- Gerçek bir x86 çekirdeğinin ne yapacağını görmek için Ders 11.8'de `llvm-mca` ile Skylake modelinden tahmin alacağız.
:::

---

## 1. Flynn sınıflandırması

Michael Flynn 1966'da bilgisayarları iki soruyla sınıflandırdı: aynı anda kaç **komut akışı**, kaç **veri akışı** var?

| | Tek veri | Çok veri |
| --- | --- | --- |
| **Tek komut** | SISD: klasik sıralı işlemci | **SIMD**: bir komut, çok veri |
| **Çok komut** | MISD: pratikte neredeyse yok | MIMD: çok çekirdekli işlemciler (Faz 12) |

Modern bir işlemci aslında hepsinin karışımı: Ders 7'deki sırasız yürütme tek akışta paralellik buluyor, her çekirdek bir MIMD parçası, her çekirdeğin içinde SIMD birimleri var. Dikkat edilecek fark şu: SIMD'de paralellik **programcının veya derleyicinin görebileceği** yerde, komutun kendisinde.

---

## 2. Vektör register'ı ve lane

SIMD register'ı, içinde küçük sayılar taşıyan geniş bir register'dır. 128 bitlik bir `xmm` register'ını:

```
  127                                                          0
 +--------------+--------------+--------------+--------------+
 |   float [3]  |   float [2]  |   float [1]  |   float [0]  |      4 lane
 +--------------+--------------+--------------+--------------+
```

Her dilime **lane** (şerit) denir. Bir SIMD toplaması bütün şeritleri **bağımsız** toplar; bir şeritten diğerine elde geçmez:

```
  a:   1     2     3     4
  b:  10    20    30    40
      +     +     +     +
  =:  11    22    33    44        tek komut: addps
```

128 bitin nasıl bölüneceğine register karar vermez, **komut** karar verir. Aynı bitler:

```c
/* serit.c: bir vektor register'inin icinde ne var? */
#include <stdio.h>
#include <immintrin.h>

typedef union { __m128 v; float f[4]; } F4;
typedef union { __m128i v; unsigned char b[16]; short h[8]; int w[4]; long long q[2]; } I16;

int main(void) {
    F4 a = { .v = _mm_set_ps(4, 3, 2, 1) };          /* DIKKAT: yuksekten dusuge */
    printf("_mm_set_ps(4,3,2,1)  -> f[0..3] = %g %g %g %g\n", a.f[0], a.f[1], a.f[2], a.f[3]);
    F4 b = { .v = _mm_setr_ps(4, 3, 2, 1) };         /* r: reversed, bellek sirasi */
    printf("_mm_setr_ps(4,3,2,1) -> f[0..3] = %g %g %g %g\n", b.f[0], b.f[1], b.f[2], b.f[3]);

    I16 x = { .v = _mm_set_epi32(0x0d0c0b0a, 0x09080706, 0x05040302, 0x01000f0e) };
    printf("ayni 128 bit:\n  byte :");
    for (int i = 0; i < 16; i++) printf(" %02x", x.b[i]);
    printf("\n  short:");
    for (int i = 0; i < 8; i++) printf(" %04hx", x.h[i]);
    printf("\n  int  :");
    for (int i = 0; i < 4; i++) printf(" %08x", x.w[i]);
    printf("\n  long :");
    for (int i = 0; i < 2; i++) printf(" %016llx", (unsigned long long)x.q[i]);
    printf("\n");
    printf("sizeof(__m128)=%zu _Alignof=%zu  sizeof(__m256)=%zu _Alignof=%zu\n",
           sizeof(__m128), _Alignof(__m128), sizeof(__m256), _Alignof(__m256));
    return 0;
}
```

```
$ cc -O2 -msse4.2 serit.c -o serit && ./serit
_mm_set_ps(4,3,2,1)  -> f[0..3] = 1 2 3 4
_mm_setr_ps(4,3,2,1) -> f[0..3] = 4 3 2 1
ayni 128 bit:
  byte : 0e 0f 00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d
  short: 0f0e 0100 0302 0504 0706 0908 0b0a 0d0c
  int  : 01000f0e 05040302 09080706 0d0c0b0a
  long : 0504030201000f0e 0d0c0b0a09080706
sizeof(__m128)=16 _Alignof=16  sizeof(__m256)=32 _Alignof=32
```

İlk iki satır, SIMD'e yeni başlayanların ilk tuzağı: `_mm_set_ps` argümanları **yüksek lane'den düşüğe** alıyor (kağıda yazılan sayı gibi), bellekte ise lane 0 en düşük adreste. Ters sırayı istemiyorsan `_mm_setr_ps` (`r`: reversed) kullan.

Son dört satır küçük-sonluluğu (Ders 3.9) yeniden gösteriyor: en düşük adresteki byte `0e`, 32 bitlik okumada en düşük byte oluyor, sayı `01000f0e` biçiminde yazılıyor.

Kaç şerit? Basit bir bölme:

| Register | int8 | int16 | int32/float | int64/double |
| --- | --- | --- | --- | --- |
| 128 bit (`xmm`, NEON) | 16 | 8 | 4 | 2 |
| 256 bit (`ymm`) | 32 | 16 | 8 | 4 |
| 512 bit (`zmm`) | 64 | 32 | 16 | 8 |

Veri tipini küçültmek SIMD'de kazancı doğrudan katlar: `float` yerine `double` kullanan kod, aynı register'da yarı şeritle çalışır. Ders 11.9'da bunu `uint8_t` görüntü pikselleriyle göreceğiz.

---

## 3. Komut kümelerine genel bakış

| Küme | Yıl | Genişlik | Eklenenler |
| --- | --- | --- | --- |
| MMX | 1997 | 64 | Tamsayı; x87 ile register paylaşımı yüzünden artık kullanılmıyor |
| SSE | 1999 | 128 | `float` 4'lü işlemler, `xmm0–7` |
| SSE2 | 2001 | 128 | `double`, 128 bit tamsayı. x86-64 için **zorunlu temel**, `xmm0–15` |
| SSE3 / SSSE3 | 2004 / 2006 | 128 | Yatay toplama, `pshufb` |
| SSE4.1 / 4.2 | 2007 / 2008 | 128 | `blend`, `dpps`, string komutları, `popcnt` |
| AVX | 2011 | 256 | `float`/`double` için `ymm`, 3 operandlı VEX kodlaması |
| AVX2 + FMA | 2013 | 256 | 256 bit tamsayı, `gather`, birleşik çarpma-toplama |
| AVX-512 | 2016 | 512 | `zmm0–31`, `k0–7` maske register'ları |
| AVX10 | 2023 duyurusu | 256/512 | AVX-512'yi sürümleyip birleştirme girişimi |
| NEON | 2005 (ARMv7) | 128 | AArch64'te 32 register; Apple M serisinde var (Ders 11.14) |
| SVE / SVE2 | 2016 | 128–2048 | Genişliği donanım belirler; aynı ikili her genişlikte çalışır |
| RVV 1.0 | 2021 | değişken | RISC-V vektör uzantısı; genişlik yine donanımın |

İki felsefe var. **Sabit genişlik** (SSE, AVX, NEON): kod, şerit sayısını bilerek yazılır ve daha geniş bir küme için yeniden yazılır. **Genişlikten bağımsız** (SVE, RVV): kod "kaç şeridin varsa o kadar işle" diye yazılır. Bu ders dizisi sabit genişlikli kodu öğretiyor; hem öğrenmesi daha somut hem bugünkü kodun çoğu böyle.

---

## 4. Aynı döngü, üç hedef

```c
void topla(float *restrict d, const float *restrict a, const float *restrict b, long n) {
    for (long i = 0; i < n; i++) d[i] = a[i] + b[i];
}
```

Derleyici vektörleştirmesi kapalıyken, varsayılan SSE2 ile ve AVX2 ile x86-64 çıktısı (`clang -S`, çekirdek döngüler):

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize -S topla.c -o -
	movss	(%rsi,%r8,4), %xmm0
	addss	(%rdx,%r8,4), %xmm0       ; ss: scalar single, bir float
	movss	%xmm0, (%rdi,%r8,4)

$ clang -O2 -S topla.c -o -
	movups	(%rsi,%r8,4), %xmm0
	movups	16(%rsi,%r8,4), %xmm1
	movups	(%rdx,%r8,4), %xmm2
	addps	%xmm0, %xmm2              ; ps: packed single, dort float
	movups	16(%rdx,%r8,4), %xmm0
	addps	%xmm1, %xmm0
	movups	%xmm2, (%rdi,%r8,4)
	movups	%xmm0, 16(%rdi,%r8,4)

$ clang -O2 -mavx2 -S topla.c -o -
	vmovups	(%rsi,%r8,4), %ymm0
	vaddps	(%rdx,%r8,4), %ymm0, %ymm0  ; ymm: sekiz float
	vmovups	%ymm0, (%rdi,%r8,4)
	...
```

Komut adlarını okumayı öğrendin: `ss` tek değer, `ps` paket, başta `v` varsa VEX kodlaması. `-O2`'de clang 18 x86'da vektörleştiriyor; ayrıca bayrak vermeden yalnızca SSE2 kullanıyor, çünkü x86-64 temeli o. AVX için bayrak gerek. Derleyicinin bunu nasıl yaptığı Ders 11.15'in konusu; önümüzdeki beş ders elle yazacağız.

---

## 5. Kazancın sınırı: bellek

Asıl soru: 4 şerit 4 kat hızlandırır mı? M2 üzerinde gerçek donanımda, NEON ile (derleyicinin vektörleştirmesi; `-fno-vectorize` karşılaştırma için):

```c
/* boyut.c: SIMD kazanci dizi boyutuna bagli (derleyici vektorlestirir) */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"

__attribute__((noinline))
void topla(float *restrict d, const float *restrict a, const float *restrict b, long n) {
    for (long i = 0; i < n; i++) d[i] = a[i] + b[i];
}

int main(void) {
    long ns[] = { 1000, 8000, 100000, 1000000, 8000000, 32000000 };
    for (int k = 0; k < 6; k++) {
        long n = ns[k];
        float *a = aligned_alloc(64, (size_t)n * 4), *b = aligned_alloc(64, (size_t)n * 4), *d = aligned_alloc(64, (size_t)n * 4);
        for (long i = 0; i < n; i++) { a[i] = i; b[i] = 2 * i; d[i] = 0; }
        long tur = 400000000 / n; if (tur < 4) tur = 4;
        double en = 1e9;
        for (int t = 0; t < 7; t++) {
            double b0 = simdi();
            for (long r = 0; r < tur; r++) { topla(d, a, b, n); BELLEK(); }
            double s = simdi() - b0; if (s < en) en = s;
        }
        printf("n=%9ld  bellek=%8.1f MB  %.3f ns/eleman  CPE=%.2f\n", n, 3.0 * n * 4 / 1e6, en * 1e9 / (tur * n), en * 1e9 / (tur * n) * 3.5);
        free(a); free(b); free(d);
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize boyut.c -o a && ./a    # skaler
n=     1000  bellek=     0.0 MB  0.345 ns/eleman  CPE=1.21
n=     8000  bellek=     0.1 MB  0.352 ns/eleman  CPE=1.23
n=   100000  bellek=     1.2 MB  0.338 ns/eleman  CPE=1.18
n=  1000000  bellek=    12.0 MB  0.397 ns/eleman  CPE=1.39
n=  8000000  bellek=    96.0 MB  0.408 ns/eleman  CPE=1.43
n= 32000000  bellek=   384.0 MB  0.400 ns/eleman  CPE=1.40

$ clang -O2 boyut.c -o b && ./b                                      # NEON
n=     1000  bellek=     0.0 MB  0.066 ns/eleman  CPE=0.23
n=     8000  bellek=     0.1 MB  0.061 ns/eleman  CPE=0.21
n=   100000  bellek=     1.2 MB  0.126 ns/eleman  CPE=0.44
n=  1000000  bellek=    12.0 MB  0.137 ns/eleman  CPE=0.48
n=  8000000  bellek=    96.0 MB  0.230 ns/eleman  CPE=0.80
n= 32000000  bellek=   384.0 MB  0.232 ns/eleman  CPE=0.81
```

Tablo olarak:

| Dizi | Skaler CPE | NEON CPE | Kazanç |
| --- | --- | --- | --- |
| 12 KB | 1.21 | 0.23 | **5.3 kat** |
| 96 KB | 1.23 | 0.21 | 5.9 kat |
| 1.2 MB | 1.18 | 0.44 | 2.7 kat |
| 12 MB | 1.39 | 0.48 | 2.9 kat |
| 96 MB | 1.43 | 0.80 | 1.8 kat |
| 384 MB | 1.40 | 0.81 | **1.7 kat** |

4 şeritten 5–6 kat kazanç şaşırtıcı görünmesin: vektörleştirici döngüyü aynı zamanda açıyor ve skaler sürüm daha çok bellek komutu çalıştırıyor (skaler kod dört eleman için 12 ayrı bellek erişimi yapıyor, NEON üç). Yine de 4 katın üstündeki kısmı burada tek tek ayırmadık. Asıl ders son satırda: **dizi önbelleğe sığmayınca hesap değil bellek sınır oluyor** ve SIMD'in kazancı eriyor. Ders 11.18'de buna *Roofline modeli* ile sayı vereceğiz, Ders 11.17'de önbellek tarafını ele alacağız.

Bu nedenle bir SIMD optimizasyonuna başlamadan iki şeyi ölç: kodun hesap mı bellek mi sınırlı olduğunu, ve vektörleşebilen kısmın toplam sürenin ne kadarı olduğunu. İkincisi Amdahl yasası (Ders 10.18): vektörleşebilen oran $p$, şerit sayısı $k$ ise kazanç

$$S = \frac{1}{(1 - p) + p/k}$$

---

## 6. Desteklenmeyen komut

Bir program komutunu çalıştıran işlemcide o komut yoksa ne olur? Bu makinenin (Rosetta altındaki) x86 özellikleri:

```c
/* destek.c: bu islemci neyi destekliyor? */
#include <stdio.h>
int main(void) {
    __builtin_cpu_init();
#define G(x) printf("%-12s %s\n", x, __builtin_cpu_supports(x) ? "var" : "yok")
    G("sse2"); G("ssse3"); G("sse4.2"); G("popcnt"); G("avx"); G("avx2"); G("fma");
    G("avx512f"); G("avx512bw"); G("avx512vpopcntdq");
    return 0;
}
```

```
$ cc -O2 destek.c -o d && ./d
sse2         var
ssse3        var
sse4.2       var
popcnt       var
avx          var
avx2         var
fma          var
avx512f      yok
avx512bw     yok
avx512vpopcntdq yok
```

Bu makinede AVX-512 yok. Yine de derlemeyi kimse engellemiyor:

```c
/* ill.c: desteklenmeyen komut */
#include <stdio.h>
#include <immintrin.h>
__attribute__((noinline)) void iki_kat(int *d, const int *k) {
    __m512i a = _mm512_loadu_si512(k);
    _mm512_storeu_si512(d, _mm512_add_epi32(a, a));
}
int main(void) {
    int k[16] = { 1, 2, 3 }, d[16];
    iki_kat(d, k);
    printf("%d %d %d\n", d[0], d[1], d[2]);
    return 0;
}
```

```
$ clang -O2 -mavx512f ill.c -o i
$ objdump -d --no-show-raw-insn i | grep -A3 '<iki_kat>:'
0000000000001140 <iki_kat>:
    1140:	vmovdqu64 (%rsi),%zmm0
    1146:	vpaddd %zmm0,%zmm0,%zmm0
    114c:	vmovdqu64 %zmm0,(%rdi)
$ ./i
Illegal instruction
$ echo $?
132
```

`SIGILL` (sinyal 4, 128 + 4 = 132). Bayrak derleyiciye "bu işlemcide çalıştıracağım" sözü vermek demek, sözü tutmak sana kalıyor.

:::caution[Ölü kod tuzağı burada da var]
Bu örneğin ilk sürümünde `iki_kat` yoktu; `main`'in içinde `_mm512_set1_epi32(argc)` ile vektörü kurup toplayıp `reduce` çağırmıştım. Program AVX-512 olmayan bu makinede **sorunsuz çalıştı ve 32 yazdı**: LLVM bütün vektör işini bir skaler çarpmaya sadeleştirmişti. Intrinsic yazmak o komutun üretileceğini garanti etmez (Ders 11.7). `noinline` bir fonksiyon ve bellekten okuma gerçek komutu zorladı.
:::

Dağıtılan yazılımda çözüm **çalışma zamanı seçimi**: birkaç sürüm derle, işlemciye sor:

```c
/* secim.c: calisma zamaninda en iyi surumu sec */
#include <stdio.h>
#include <immintrin.h>

static long say_sse(void) { return 4; }
__attribute__((target("avx2"))) static long say_avx2(void) {
    __m256i a = _mm256_set1_epi32(1);
    a = _mm256_add_epi32(a, a);
    return _mm256_extract_epi32(a, 0) * 4;
}

int main(void) {
    __builtin_cpu_init();
    long (*f)(void) = __builtin_cpu_supports("avx2") ? say_avx2 : say_sse;
    printf("secilen: %s -> %ld\n", f == say_avx2 ? "avx2" : "sse", f());
    return 0;
}
```

```
$ cc -O2 secim.c -o y && ./y
secilen: avx2 -> 8
```

`target("avx2")` özniteliği, dosyayı `-mavx2` ile derlemeden tek fonksiyonda o komutları açıyor. glibc'nin `strlen`'i de böyle çalışır: yükleyici `IFUNC` ile en iyi sürümü bir kez seçer (Ders 11.12'de bu sürümle yarışacağız). Clang ve GCC, aynı işi tek satıra indiren `__attribute__((target_clones("avx2", "default")))` özniteliğini de sunuyor.

Bir başka gerçek: geniş vektörler bazı işlemcilerde saat frekansını düşürür. Özellikle AVX-512 ile eski Intel sunucu çekirdekleri (Skylake-SP) yoğun kullanımda frekansı belirgin biçimde indirir. Bu yüzden "vektör ne kadar genişse o kadar iyi" kuralı her zaman doğru değil; kısa aralıklarda birkaç AVX-512 komutu çevredeki bütün skaler kodu yavaşlatabilir. Daha yeni çekirdeklerde bu etki azaldı, ama ölçmeden bilinmez.

---

## Alıştırmalar

**1** – Programın zamanının yüzde 80'i vektörleşebilen bir döngüde. 8 şeritle en iyi kazanç nedir? Şerit sayısı sonsuz olsa?

**2** – `_mm_set_ps(1, 2, 3, 4)` yazıldıktan sonra `f[0]` kaçtır? `_mm_setr_ps(1, 2, 3, 4)` için?

**3** – 512 bitlik register'a kaç `int8_t`, `int32_t` ve `double` sığar?

**4** – `boyut.c`'yi kendi makinende çalıştır ve kazancın düştüğü yeri bul. Önbellek boyutlarınla (`lscpu`) karşılaştır.

**5** – Bir fonksiyona `__attribute__((target_clones("avx2", "default")))` ekleyip gövdesinde `#ifdef __AVX2__` ile farklı değer döndürmeye çalış. Sonuç ne olur, neden? (İpucu: önişlemci ne zaman çalışır?)

<details>
<summary>Cevaplar</summary>

**1** – $S = 1/(0.2 + 0.8/8) = 1/0.3 = 3.33$. Şerit sonsuzsa $S = 1/0.2 = 5$: skaler kalan yüzde 20 kazancı beşe kilitliyor.

**2** – `_mm_set_ps(1,2,3,4)`: `f[0] = 4` (son argüman en düşük lane). `_mm_setr_ps(1,2,3,4)`: `f[0] = 1`.

**3** – 64 `int8_t`, 16 `int32_t`, 8 `double`.

**4** – Makineye göre değişir. Beklenen desen: L2'ye kadar yüksek kazanç, son seviye önbelleği aşılınca düşüş. Bu derste düşüş 96 MB civarında (toplam üç dizi) belirginleşti.

**5** – `#ifdef` her iki klonda da AVX2'siz sonucu veriyor; bunu denedik, `f()` 0 döndürdü. Önişlemci derlemeden önce çalışıp bir tek metin üretiyor; `target_clones` ise aynı metni iki ayrı hedef için derliyor, `__AVX2__` makrosunu değiştirmiyor. Hedefe göre davranış değişikliği, yalnızca derleyicinin ürettiği kodda oluyor.

</details>

---

## Kaynaklar

- Michael J. Flynn, "Very High-Speed Computing Systems", *Proceedings of the IEEE*, 54(12), 1966.
- Michael J. Flynn, "Some Computer Organizations and Their Effectiveness", *IEEE Transactions on Computers*, C-21(9), 1972.
- Intel, *Intel 64 and IA-32 Architectures Software Developer's Manual*, Cilt 1, Bölüm 9–15 (MMX, SSE, AVX).
- Arm, *Arm Architecture Reference Manual for A-profile*; SVE ve NEON bölümleri.
- RISC-V International, *RISC-V "V" Vector Extension*, sürüm 1.0, 2021.
- Hennessy ve Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Bölüm 4.

**Sıradaki ders:** SSE intrinsics. `__m128`, `_mm_load_ps`, `_mm_add_ps`, `_mm_store_ps`; iki diziyi toplama.
