---
title: "11.17 Cache optimizasyonu derinlemesine"
description: "Önbelleğin dört pratik konusu ölçerek: dört iş parçacığının yan yana sayaçlarında false sharing ile 15 kat yavaşlama ve bu makinede 64 byte aralığın yetmesi; rastgele erişimde yazılımla önyüklemenin hiç kazandırmaması ve sırasız yürütmenin bellek düzeyi paralelliği; satır sınırını aşan nesnenin yalnız yüzde 2 maliyeti; 4096 float satırlı matris transpozunda bloklamanın 2'nin kuvveti çakışması yüzünden işe yaramaması, 16 float dolguyla 12 kat hızlanma ve blok boyutunun seçimi."
---

Ders 7.24–7.26'da önbellek hiyerarşisini, organizasyonunu ve önbellek dostu kodun temel kurallarını gördük. Bu ders o kuralların kenar durumlarına bakıyor. Bu konularda sezgi sık sık yanıltıyor, o yüzden hepsini ölçtük.

Ortam: M2, Docker arm64 Linux, 8 çekirdek (4 performans + 4 verimlilik). macOS'a göre satır boyu 128 byte (`hw.cachelinesize`); Linux sanal makinesi L1 için 64 byte bildiriyor (`getconf LEVEL1_DCACHE_LINESIZE`). Bu çelişki birinci bölümde önemli olacak.

---

## 1. False sharing

İki iş parçacığı **farklı** değişkenleri yazıyor, ama değişkenler aynı önbellek satırında. Önbellek tutarlılık protokolü (MESI) satırı çekirdekler arasında sürekli taşıyor; değişkenler ayrı olsa da sanki paylaşılıyormuş gibi bekliyorlar.

```c
/* paylasim.c: her is parcacigi kendi sayacini artiriyor */
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <stdatomic.h>
#include "olcum.h"

#define TUR 20000000L
static char *alan;
static long aralik;

static void *calis(void *arg) {
    long k = (long)arg;
    _Atomic long *s = (_Atomic long *)(alan + k * aralik);
    for (long i = 0; i < TUR; i++) atomic_fetch_add_explicit(s, 1, memory_order_relaxed);
    return 0;
}

int main(int argc, char **argv) {
    int t = argc > 1 ? atoi(argv[1]) : 4;
    alan = aligned_alloc(4096, 4096 * 2);
    long araliklar[] = { 8, 32, 64, 128, 256 };
    for (int a = 0; a < 5; a++) {
        aralik = araliklar[a];
        double en = 1e9;
        for (int q = 0; q < 5; q++) {
            pthread_t th[16];
            double b0 = simdi();
            for (long k = 0; k < t; k++) pthread_create(&th[k], 0, calis, (void *)k);
            for (int k = 0; k < t; k++) pthread_join(th[k], 0);
            double e = simdi() - b0; if (e < en) en = e;
        }
        printf("%d is parcacigi, sayaclar %3ld byte arayla: %6.1f ms  (%.2f ns/artirma)\n", t, aralik, en * 1e3, en * 1e9 / TUR);
    }
    return 0;
}
```

```
$ clang -O2 -pthread paylasim.c -o p && ./p 4 && ./p 2
4 is parcacigi, sayaclar   8 byte arayla:  627.0 ms  (31.35 ns/artirma)
4 is parcacigi, sayaclar  32 byte arayla:  183.8 ms  (9.19 ns/artirma)
4 is parcacigi, sayaclar  64 byte arayla:   41.3 ms  (2.07 ns/artirma)
4 is parcacigi, sayaclar 128 byte arayla:   41.2 ms  (2.06 ns/artirma)
4 is parcacigi, sayaclar 256 byte arayla:   41.1 ms  (2.06 ns/artirma)
2 is parcacigi, sayaclar   8 byte arayla:  174.7 ms  (8.74 ns/artirma)
2 is parcacigi, sayaclar  32 byte arayla:  173.3 ms  (8.66 ns/artirma)
2 is parcacigi, sayaclar  64 byte arayla:   39.7 ms  (1.99 ns/artirma)
2 is parcacigi, sayaclar 128 byte arayla:   39.9 ms  (1.99 ns/artirma)
2 is parcacigi, sayaclar 256 byte arayla:   39.7 ms  (1.98 ns/artirma)
```

- Dört sayaç 8 byte arayla (hepsi aynı satırda): **15 kat** yavaş.
- 32 byte arayla dördü iki çift halinde iki satıra düşüyor: hâlâ 4.5 kat yavaş.
- **64 byte** yetiyor: bu makinede tutarlılık birimi 64 byte gibi davranıyor, macOS'un bildirdiği 128 değil. 128 byte'a hizalamak her ikisini de kapsar ve güvenli seçim.

Çözüm, sıcak değişkenleri satır sınırına hizalamak:

```c
struct sayac { _Alignas(128) _Atomic long n; };   /* her biri ayri satirda */
```

C++17'de bunun için `std::hardware_destructive_interference_size` sabiti var; C'de yok, değeri kendin seçiyorsun. Ders 10.12'deki atomik sayaçlarda ve kilitsiz yapılarda bu ayrıntı belirleyici.

`relaxed` sıralamalı atomik kullandık (Ders 10.12–10.13): sıradan bir `long`'u derleyici döngünün dışında tek bir toplamaya indirirdi, ki bu da Ders 11.1'deki ölü kod tuzağı.

---

## 2. Yazılımla önyükleme

`__builtin_prefetch(p)` işlemciye "bu adresi yakında okuyacağım, şimdi getirmeye başla" der (AArch64'te `prfm`, x86'da `prefetcht0`). Rastgele indisli bir toplama, tablo 256 MB:

```c
/* onyukle.c: rastgele indisli toplama ve yazilimla onyukleme */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"

__attribute__((noinline)) long topla(const int *a, const unsigned *idx, long n, int D) {
    long s = 0;
    if (D == 0) { for (long i = 0; i < n; i++) s += a[idx[i]]; return s; }
    for (long i = 0; i < n; i++) {
        __builtin_prefetch(&a[idx[i + D]], 0, 0);   /* D eleman ilerisi */
        s += a[idx[i]];
    }
    return s;
}

int main(void) {
    long m = 64L * 1024 * 1024, n = 8L * 1024 * 1024;   /* 256 MB tablo */
    int *a = malloc(4 * m);
    unsigned *idx = malloc(4 * (n + 1024));
    for (long i = 0; i < m; i++) a[i] = (int)(i & 7);
    unsigned long long x = 88172645463325252ull;
    for (long i = 0; i < n + 1024; i++) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; idx[i] = (unsigned)(x % (unsigned long long)m); }
    KORU(a); KORU(idx);
    int ds[] = { 0, 1, 4, 16, 64, 256, 1024 };
    long ref = topla(a, idx, n, 0);
    for (int k = 0; k < 7; k++) {
        double en = 1e9; long s = 0;
        for (int q = 0; q < 5; q++) { double b0 = simdi(); s = topla(a, idx, n, ds[k]); double e = simdi() - b0; if (e < en) en = e; }
        printf("D=%5d  %.2f ns/eleman  %s\n", ds[k], en * 1e9 / n, s == ref ? "" : "FARKLI");
    }
    /* ayni sey, sirali indisle: donanim onyukleyicisi */
    for (long i = 0; i < n; i++) idx[i] = (unsigned)(i * 8);
    double en = 1e9;
    for (int q = 0; q < 5; q++) { double b0 = simdi(); KORU(topla(a, idx, n, 0)); double e = simdi() - b0; if (e < en) en = e; }
    printf("sirali (32 byte adim), D=0: %.2f ns/eleman\n", en * 1e9 / n);
    return 0;
}
```

```
$ clang -O2 onyukle.c -o o && ./o
D=    0  5.53 ns/eleman  
D=    1  6.16 ns/eleman  
D=    4  5.94 ns/eleman  
D=   16  5.61 ns/eleman  
D=   64  5.52 ns/eleman  
D=  256  5.76 ns/eleman  
D= 1024  6.46 ns/eleman  
sirali (32 byte adim), D=0: 0.63 ns/eleman
```

**Hiçbir mesafede kazanç yok**; uzak mesafeler biraz zarar veriyor. Neden?

Her eleman ~5.5 ns alıyor, ama tek bir DRAM erişimi Ders 7.24'te ölçtüğümüz gibi 100 ns civarı. Yani işlemci **aynı anda yaklaşık 18 ıskayı** bekliyor. `idx[i]`'ler önceden biliniyor ve birbirinden bağımsız, sırasız yürütme birimi (Ders 7.23) döngünün ilerisindeki yüklemeleri kendisi başlatıyor. Buna **bellek düzeyi paralellik** (MLP) denir. Önyükleme komutunun yapacağı işi donanım zaten yapıyor; bizim komutlarımız yalnızca ek yük.

Yazılımla önyükleme şu durumlarda işe yarar:

- **Pointer kovalamada** sonraki adres ancak şimdiki yüklendikten sonra biliniyor (bağlı liste, ağaç). Burada da önceden bir adres bilinmeli: örneğin ağaçta iki çocuğu birden, ya da hash tablosunda **bir grup** anahtarın kovalarını önceden istemek.
- İş döngüsü uzunsa ve sırasız pencereyi (yüzlerce komut) dolduruyorsa.
- Donanım önyükleyicisinin tanımadığı desenlerde (çok büyük adımlar, sayfa sınırları).

Son satır neden önyüklemeye uğraştığımızı gösteriyor: aynı döngü **sıralı** erişimde 9 kat hızlı, çünkü donanım önyükleyicisi deseni tanıyor.

---

## 3. Satır sınırını aşmak

64 byte'lık bir nesne 128 byte'lık satırın içinde nerede durursa dursun ya bir ya iki satıra düşer. Rastgele erişim, 256 MB:

```c
/* hiza.c: 64 byte'lik nesneler, satir sinirina gore konumu */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "olcum.h"

typedef struct { float v[16]; } Nesne;   /* 64 byte */

__attribute__((noinline)) float oku(const char *taban, long ofset, const unsigned *idx, long n) {
    float s = 0;
    for (long i = 0; i < n; i++) {
        const Nesne *o = (const Nesne *)(taban + ofset + (long)idx[i] * 128);
        for (int j = 0; j < 16; j++) s += o->v[j];
    }
    return s;
}

int main(void) {
    long m = 2L * 1024 * 1024, n = 4L * 1024 * 1024;     /* 2M yuva x 128 byte = 256 MB */
    char *taban = aligned_alloc(4096, m * 128 + 4096);
    memset(taban, 0, m * 128 + 4096);
    unsigned *idx = malloc(4 * n);
    unsigned long long x = 88172645463325252ull;
    for (long i = 0; i < n; i++) { x ^= x << 13; x ^= x >> 7; x ^= x << 17; idx[i] = (unsigned)(x % (unsigned long long)m); }
    KORU(taban); KORU(idx);
    long ofsetler[] = { 0, 32, 64, 96 };
    for (int k = 0; k < 4; k++) {
        double en = 1e9; volatile float r;
        for (int q = 0; q < 5; q++) { double b0 = simdi(); r = oku(taban, ofsetler[k], idx, n); double e = simdi() - b0; if (e < en) en = e; }
        (void)r;
        printf("nesne 128 byte satirin %3ld. byte'inda: %s, %.2f ns/nesne\n", ofsetler[k],
               ofsetler[k] + 64 > 128 ? "iki satir" : "tek satir", en * 1e9 / n);
    }
    return 0;
}
```

```
$ clang -O2 -ffast-math -fno-vectorize -fno-slp-vectorize hiza.c -o h && ./h
nesne 128 byte satirin   0. byte'inda: tek satir, 25.94 ns/nesne
nesne 128 byte satirin  32. byte'inda: tek satir, 26.08 ns/nesne
nesne 128 byte satirin  64. byte'inda: tek satir, 25.91 ns/nesne
nesne 128 byte satirin  96. byte'inda: iki satir, 26.47 ns/nesne
```

İki satıra bölünen nesne yalnız **yüzde 2** daha pahalı. İkinci satırın ıskası birinciyle paralel başlıyor (yine MLP) ve DRAM komşu satırları birlikte veriyor. Hizalama, false sharing'de (1. bölüm) ve SIMD yüklemelerinde (Ders 11.7) kritik; tek başına bir okuma hızı kazancı olarak beklentiyi düşük tut.

---

## 4. Tiling parametresini seçmek

Ders 7.26'nın Alıştırma 2'si: matris transpozunda döngü sırası tek başına yardım etmez, bloklama eder. 4096 × 4096 `float`:

```c
/* transpoz.c: blok boyutu ve satir uzunlugu (dolgu) */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"

__attribute__((noinline)) void tr(float *restrict d, const float *restrict k, long n, long ld, long b) {
    for (long ii = 0; ii < n; ii += b)
        for (long jj = 0; jj < n; jj += b)
            for (long i = ii; i < ii + b && i < n; i++)
                for (long j = jj; j < jj + b && j < n; j++)
                    d[j * ld + i] = k[i * ld + j];
}

int main(void) {
    long n = 4096;
    long lds[] = { 4096, 4096 + 16 };
    for (int l = 0; l < 2; l++) {
        long ld = lds[l];
        float *k = aligned_alloc(128, 4 * ld * n), *d = aligned_alloc(128, 4 * ld * n);
        for (long i = 0; i < ld * n; i++) { k[i] = (float)i; d[i] = 0; }
        KORU(k); KORU(d);
        printf("satir uzunlugu %ld float:\n", ld);
        long bs[] = { 1, 4, 8, 16, 32, 64, 128, 256 };
        for (int q = 0; q < 8; q++) {
            double en = 1e9;
            for (int r = 0; r < 3; r++) { double b0 = simdi(); tr(d, k, n, ld, bs[q] == 1 ? n : bs[q]); BELLEK(); double e = simdi() - b0; if (e < en) en = e; }
            printf("  blok %4ld%s: %6.1f ms  %.2f ns/eleman\n", bs[q], bs[q] == 1 ? " (yok)" : "      ", en * 1e3, en * 1e9 / (n * n));
        }
        int dogru = 1;
        for (long i = 0; i < n; i += 37) for (long j = 0; j < n; j += 41) if (d[j * ld + i] != k[i * ld + j]) dogru = 0;
        printf("  dogru: %s\n", dogru ? "evet" : "HAYIR");
        free(k); free(d);
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize transpoz.c -o t && ./t
satir uzunlugu 4096 float:
  blok    1 (yok):  156.6 ms  9.34 ns/eleman
  blok    4      :   50.4 ms  3.01 ns/eleman
  blok    8      :   68.7 ms  4.09 ns/eleman
  blok   16      :  136.0 ms  8.11 ns/eleman
  blok   32      :  137.5 ms  8.20 ns/eleman
  blok   64      :  145.5 ms  8.67 ns/eleman
  blok  128      :  136.4 ms  8.13 ns/eleman
  blok  256      :  139.4 ms  8.31 ns/eleman
  dogru: evet
satir uzunlugu 4112 float:
  blok    1 (yok):  139.7 ms  8.33 ns/eleman
  blok    4      :   38.0 ms  2.26 ns/eleman
  blok    8      :   31.9 ms  1.90 ns/eleman
  blok   16      :   22.6 ms  1.35 ns/eleman
  blok   32      :   14.6 ms  0.87 ns/eleman
  blok   64      :   13.2 ms  0.78 ns/eleman
  blok  128      :   13.1 ms  0.78 ns/eleman
  blok  256      :   13.8 ms  0.82 ns/eleman
  dogru: evet
```

Satır uzunluğu 4096 float (16 KB) iken bloklama **büyüdükçe kötüleşiyor**: 16'dan büyük her blok neredeyse bloklamasız kadar yavaş. Yazılan `d[j * ld + i]` sütun boyunca gidiyor ve ardışık elemanlar 16 KB arayla. 16 KB 2'nin kuvveti olduğundan bu adresler önbellekte **aynı kümeye** düşüyor (Ders 7.25, çakışma ıskaları): kümenin yolu kadar satırdan fazlası aynı anda tutulamıyor ve blok ne kadar büyük olursa olsun önbellekte kalmıyor.

Satırı **16 float uzatınca** (`ld = 4112`, satırlar arası 16 KB + 64 byte) adresler farklı kümelere dağılıyor ve bloklama beklenen işi yapıyor: **12 kat** hızlanma. Bu bir dolgu (*padding*); BLAS kütüphanelerinin "leading dimension" parametresinin bir nedeni de bu.

Blok boyutu seçimi için kaba hesap: transpozda bir blok iki $b \times b$ parça kullanıyor (okunan ve yazılan), $2 \cdot b^2 \cdot 4$ byte.

| $b$ | Çalışma kümesi | Sonuç (dolgulu) |
| --- | --- | --- |
| 16 | 2 KB | iç döngü kısa, 1.35 ns |
| 32 | 8 KB | 0.87 |
| 64 | 32 KB | **0.78** |
| 128 | 128 KB | **0.78**, L1 sınırında |
| 256 | 512 KB | 0.82, L2'de |

Bu M2'de 64–128 arası düz bir tepe var; geniş bir tepe, iyi bir tasarım kararıdır, çünkü başka işlemcide de fena olmaz. Genel kurallar:

1. Çalışma kümesini hedef önbelleğin yarısı ile üçte ikisi arasında tut (gerisi başka veriye, TLB'ye ve çakışmalara kalsın).
2. Satır uzunluğu 2'nin kuvvetiyse dolgu ekle.
3. Seçimi bir boyut taramasıyla doğrula; teorik değer başlangıç noktası, sonuç değil.
4. Taşınabilirlik gerekiyorsa çalışma zamanında ayarlayan bir kütüphane (ATLAS'ın yaklaşımı) ya da birkaç değer arasında seçim.

---

## Alıştırmalar

**1** – `paylasim.c`'de sayaçları atomik yerine sıradan `volatile long` yap. Sonuçlar nasıl değişir? Neden doğruluk açısından da bir sorun yok (her iş parçacığı kendi sayacını yazıyor)?

**2** – Bir bağlı listeyi gezen döngüde `__builtin_prefetch(p->next->next)` eklemek neden işe yaramayabilir?

**3** – `transpoz.c`'de `ld = 4096 + 1` (bir float dolgu) dene. 16 float dolguyla aynı kazancı beklemeli misin? (İpucu: satırlar arası adım kaç satır kümesi atlıyor ve SIMD yüklemesi hizalı kalıyor mu?)

**4** – 1. bölümde 2 iş parçacığı için 8 ve 32 byte aralık aynı süreyi verdi. Neden?

**5** – Bir sunucu programında her istek için bir `struct istatistik { long sayac; long bayt; }` dizisinin `[cekirdek_no]` elemanı güncelleniyor. Ne öneririsin?

<details>
<summary>Cevaplar</summary>

**1** – `volatile` her artırmada yükleme ve saklama zorunlu kılar, ama atomik değil. Paylaşım olmadığı için sonuç doğru. False sharing yine olur, çünkü satır her yazmada el değiştirir; atomik `ldadd` yerine `ldr/add/str` olacağından mutlak süreler değişebilir, ama aralığa göre desen aynı kalmalı.

**2** – `p->next->next` adresini hesaplamak için `p->next`'i okumak gerekiyor: o okuma zaten ıskalıyorsa önyüklemeden önce bekleniyor. Önyükleme ancak adres önceden bilindiğinde yardımcı olur; listeyi bir diziye (ya da havuza) taşımak daha iyi bir çözüm.

**3** – Bir float (4 byte) dolgu da kümeleri dağıtır: ardışık satırlar farklı kümelere düşer. Ama satırlar 16 byte'a hizalı olmaktan çıkar, SIMD hizalı yüklemeler bozulur ve bir satırın başı önbellek satırının ortasına düşer. 16 float (64 byte) dolgu iki sorunu birden çözer.

**4** – İki iş parçacığında sayaçlar 0 ve 8 (ya da 0 ve 32) byte'ta; her iki durumda da aynı 64 byte'lık birimde. Aynı satırda iki yazar, ikisinde de aynı tutarlılık trafiği.

**5** – Her elemanı 128 byte'a hizala ve doldur (`_Alignas(128)`), ya da iş parçacığına yerel (`_Thread_local`) sayaç tutup periyodik olarak birleştir. İkincisi aynı zamanda yazma trafiğini de azaltır.

</details>

---

## Kaynaklar

- Ulrich Drepper, *What Every Programmer Should Know About Memory*, 2007, Bölüm 3.3, 6.3, 6.4.
- Monica Lam, Edward Rothberg, Michael Wolf, "The Cache Performance and Optimizations of Blocked Algorithms", *ASPLOS 1991*.
- R. Clint Whaley ve Jack Dongarra, "Automatically Tuned Linear Algebra Software", *SC 1998* (ATLAS).
- Arm, *Arm Architecture Reference Manual*: `PRFM`.
- C++17, `std::hardware_destructive_interference_size`.

**Sıradaki ders:** Roofline modeli. Aritmetik yoğunluk, bellek sınırlı ve hesap sınırlı kod.
