---
title: "11.18 Roofline modeli"
description: "Bir çekirdeğin kaç GFLOP/s'e ulaşabileceğini iki sayıyla tahmin etmek: tepe hesap hızı ve bellek bant genişliği; M2'de zincir sayısıyla ölçülen 111 GFLOP/s (çevrimde 4 fmla) tavanı ve ilk denemedeki gizli mov'ların hızı yarıya indirmesi; okuma bant genişliğinin veri boyutuna göre 78'den 56 GB/s'e düşmesi; aritmetik yoğunluğu 0.25'ten 32'ye değişen bir çekirdekle ölçülmüş roofline grafiği; çok çekirdekte hesap tavanının 330'a çıkıp bellek tavanının 47 GB/s'te kalması ve dönüm noktasının kayması."
---

Bir döngüyü hızlandırmaya başlamadan önce sorulacak soru: **bu döngü en fazla ne kadar hızlı olabilir?** Ders 11.2'de tek komut düzeyinde bu soruyu gecikme ve kapasiteyle yanıtladık. *Roofline modeli* (Williams, Waterman ve Patterson, 2009) aynı soruyu bütün bir çekirdek için iki sayıyla yanıtlıyor.

---

## 1. Model

Bir çekirdek (kernel) için:

- $F$: yaptığı kayan nokta işlemi (flop).
- $Q$: bellekle taşıdığı byte.
- **Aritmetik yoğunluk** $I = F / Q$ (flop/byte).

Makine için:

- $P$: tepe hesap hızı (GFLOP/s).
- $\beta$: bellek bant genişliği (GB/s).

Ulaşılabilir hız:

$$\text{GFLOP/s} \le \min(P,\; \beta \cdot I)$$

Log-log eksende bu bir **çatı**: önce eğik (bellek sınırlı), sonra yatay (hesap sınırlı). İkisinin kesiştiği yer **dönüm noktası** (*ridge point*) $I^* = P / \beta$. Yoğunluğu bundan küçük kodu hızlandırmanın yolu daha az byte taşımaktır, büyük kodu ise daha iyi hesap.

Örnekler (float, 4 byte):

| Çekirdek | flop / eleman | byte / eleman | $I$ |
| --- | --- | --- | --- |
| `d[i] = a[i] + b[i]` | 1 | 12 | 0.083 |
| `y[i] = a*x[i] + y[i]` | 2 | 12 | 0.17 |
| dot product | 2 | 8 | 0.25 |
| $N \times N$ matris çarpımı | $2N^3$ toplam | en az $3 \cdot 4N^2$ | $N/6$ |

Matris çarpımı $N$ ile büyüyen tek satır: bu yüzden doğru yazıldığında hesap sınırlı (Ders 11.19).

---

## 2. Tavanı ölçmek: P

M2 performans çekirdeğinde dört SIMD/FP biriminin her biri çevrimde bir 128 bitlik `fmla` yapabiliyor: $4 \times 4 \text{ şerit} \times 2 \text{ flop} \times 3.5 \text{ GHz} = 112$ GFLOP/s (float). Bunu görmek için yeterli bağımsız zincir gerekiyor: gecikme 4 × kapasite 4 = 16 (Ders 11.2).

```c
/* tepe2.c: zincir sayisina gore NEON fmla verimi */
#include <stdio.h>
#include <arm_neon.h>
#include "olcum.h"
#define TEPE(ad, K) \
__attribute__((noinline)) float32x4_t ad(long tur, float32x4_t a, float32x4_t b) { \
    float32x4_t s[K]; \
    for (int k = 0; k < K; k++) s[k] = vaddq_f32(b, vdupq_n_f32((float)k)); \
    for (long t = 0; t < tur; t++) { \
        for (int k = 0; k < K; k++) s[k] = vfmaq_f32(s[k], b, a); \
        __asm__ volatile("" ::: "memory"); \
    } \
    for (int k = 1; k < K; k++) s[0] = vaddq_f32(s[0], s[k]); \
    return s[0]; \
}
TEPE(t4, 4) TEPE(t8, 8) TEPE(t12, 12) TEPE(t16, 16) TEPE(t24, 24)
typedef float32x4_t tf(long, float32x4_t, float32x4_t);
int main(int argc, char **argv) {
    (void)argv;
    float32x4_t a = vdupq_n_f32(0.999f * (float)argc), b = vdupq_n_f32(0.001f);
    struct { int k; tf *f; } t[] = { {4, t4}, {8, t8}, {12, t12}, {16, t16}, {24, t24} };
    for (int q = 0; q < 5; q++) {
        long tur = 50000000; double en = 1e9;
        for (int r = 0; r < 5; r++) { double b0 = simdi(); float32x4_t s = t[q].f(tur, a, b); KORU(vaddvq_f32(s)); double e = simdi() - b0; if (e < en) en = e; }
        double g = 8.0 * t[q].k * tur / en / 1e9;
        printf("%2d zincir: %6.1f GFLOP/s  %5.2f fmla/cevrim\n", t[q].k, g, g / 3.5 / 8);
    }
    return 0;
}
```

İlk sürümde döngü gövdesi `s[k] = vfmaq_f32(b, s[k], a)` idi ve 16 zincirde **36 GFLOP/s** ölçtüm. Assembly'ye bakınca:

```
	mov	v18.16b, v1.16b
	mov	v21.16b, v1.16b
	...
	fmla	v18.4s, v0.4s, v16.4s
	fmla	v21.4s, v0.4s, v3.4s
```

`fmla` sonucu **birikimci register'ına** yazıyor (`Vd = Vd + Vn * Vm`). `vfmaq_f32(b, s, a)` = $b + s \cdot a$ ise birikimci `b`, yani her adımda `b`'nin bir kopyası (`mov`) gerekiyor. Gövdeyi $s \leftarrow s + b \cdot a$ yapınca (`vfmaq_f32(s[k], b, a)`) `mov`'lar kayboldu:

```
$ clang -O2 tepe2.c -o t2 && ./t2
 4 zincir:   27.8 GFLOP/s   0.99 fmla/cevrim
 8 zincir:   55.0 GFLOP/s   1.96 fmla/cevrim
12 zincir:   80.7 GFLOP/s   2.88 fmla/cevrim
16 zincir:  108.2 GFLOP/s   3.86 fmla/cevrim
24 zincir:  111.3 GFLOP/s   3.97 fmla/cevrim
```

Ders 11.2'nin doğrusu kusursuz: zincir başına çevrimde 1/4 `fmla`, 16'da doyma, **111 GFLOP/s** (teorinin yüzde 99'u). Aynı tuzak Horner yöntemindeki $p \leftarrow d + p \cdot x$ ifadesinde de var: sabit `d` her adımda kopyalanmak zorunda.

---

## 3. Bant genişliğini ölçmek: β

```c
/* bant.c: okuma bant genisligi, veri boyutuna gore */
#include <stdio.h>
#include <stdlib.h>
#include <arm_neon.h>
#include "olcum.h"

__attribute__((noinline)) float oku(const float *a, long n) {
    float32x4_t s0 = vdupq_n_f32(0), s1 = s0, s2 = s0, s3 = s0;
    for (long i = 0; i < n; i += 16) {
        s0 = vaddq_f32(s0, vld1q_f32(a + i));      s1 = vaddq_f32(s1, vld1q_f32(a + i + 4));
        s2 = vaddq_f32(s2, vld1q_f32(a + i + 8));  s3 = vaddq_f32(s3, vld1q_f32(a + i + 12));
    }
    return vaddvq_f32(vaddq_f32(vaddq_f32(s0, s1), vaddq_f32(s2, s3)));
}

int main(void) {
    long bs[] = { 32L << 10, 96L << 10, 1L << 20, 3L << 20, 12L << 20, 64L << 20, 512L << 20 };
    float *a = aligned_alloc(128, 512L << 20);
    for (long i = 0; i < (512L << 20) / 4; i++) a[i] = 1;
    KORU(a);
    for (int k = 0; k < 7; k++) {
        long n = bs[k] / 4, tur = (4L << 30) / bs[k]; if (tur < 3) tur = 3;
        double en = 1e9;
        for (int q = 0; q < 5; q++) {
            double b0 = simdi();
            for (long t = 0; t < tur; t++) { KORU(oku(a, n)); }
            double e = simdi() - b0; if (e < en) en = e;
        }
        printf("%8ld KB: %6.1f GB/s\n", bs[k] >> 10, (double)bs[k] * tur / en / 1e9);
    }
    return 0;
}
```

```
$ clang -O2 bant.c -o b && ./b
      32 KB:   77.8 GB/s
      96 KB:   74.9 GB/s
    1024 KB:   73.7 GB/s
    3072 KB:   71.7 GB/s
   12288 KB:   70.7 GB/s
   65536 KB:   62.9 GB/s
  524288 KB:   56.2 GB/s
```

Bu döngü salt okuyor ve şaşırtıcı biçimde L1'den bile ancak 78 GB/s: çevrimde 22 byte, yani 1.4 vektör yükleme. Döngüdeki `fadd` zinciri (4 birikimci, gecikme 3) sınır oluşturuyor; L1 bant genişliğinin kendisi daha yüksek olmalı. Tek bir çekirdeğin DRAM'den okuma hızı 56 GB/s. Bu bir **salt okuma** sayısı; okuma ve yazmayı karıştıran çekirdeklerde aşağıda 40–48 GB/s göreceğiz.

---

## 4. Ölçülmüş roofline

Yoğunluğu ayarlanabilen bir çekirdek: her elemanı okuyup $k$ kez $p \leftarrow p + p \cdot x$ uygulayıp yazmak. $2k$ flop, 8 byte (4 okuma + 4 yazma), $I = k/4$.

```c
/* nokta.c: aritmetik yogunluk degisken: her elemana k derece polinom */
#include <stdio.h>
#include <stdlib.h>
#include <arm_neon.h>
#include <pthread.h>
#include "olcum.h"

/* her elemana k adim p <- p + p * x: 2k flop, 8 byte (4 oku + 4 yaz).
   Z bagimsiz zincir: Z = 4 az, Z = 12 yeterli paralellik (Ders 11.2) */
#define POLI(ad, Z) \
__attribute__((noinline)) void ad(float *restrict y, const float *restrict x, long n, int k) { \
    const float32x4_t c = vdupq_n_f32(0.5f), d = vdupq_n_f32(0.25f); \
    for (long i = 0; i < n; i += 4 * Z) { \
        float32x4_t v[Z], p[Z]; \
        for (int z = 0; z < Z; z++) { v[z] = vld1q_f32(x + i + 4 * z); p[z] = c; } \
        for (int j = 0; j < k; j++) \
            for (int z = 0; z < Z; z++) p[z] = vfmaq_f32(p[z], p[z], v[z]); \
        for (int z = 0; z < Z; z++) vst1q_f32(y + i + 4 * z, p[z]); \
    } \
}
POLI(poli4, 4)
POLI(poli12, 12)

typedef struct { float *y, *x; long n; int k, tur, z; } Is;
static void *calis(void *v) {
    Is *w = v;
    for (int t = 0; t < w->tur; t++) { if (w->z == 4) poli4(w->y, w->x, w->n, w->k); else poli12(w->y, w->x, w->n, w->k); BELLEK(); }
    return 0;
}

int main(int argc, char **argv) {
    int T = argc > 1 ? atoi(argv[1]) : 1, Z = argc > 2 ? atoi(argv[2]) : 12;
    long boy[] = { 16L << 10, 256L << 20 };    /* eleman: L1'de ve bellekte (toplam 2 dizi) */
    int ks[] = { 1, 2, 4, 8, 16, 32, 64, 128 };
    for (int b = 0; b < 2; b++) {
        long n = boy[b] / 8 / T / 192 * 192;                          /* her is parcacigina */
        Is w[16];
        for (int t = 0; t < T; t++) {
            w[t].x = aligned_alloc(128, 4 * n); w[t].y = aligned_alloc(128, 4 * n); w[t].n = n;
            for (long i = 0; i < n; i++) { w[t].x[i] = 0.001f; w[t].y[i] = 0; }
        }
        printf("%s, %d is parcacigi, %d zincir\n", b == 0 ? "L1'e sigan (16 KB)" : "bellekte (256 MB)", T, Z);
        for (int q = 0; q < 8; q++) {
            int k = ks[q], tur = (int)(2000000000L / (n * T * (k + 4)));
            if (tur < 2) tur = 2;
            double en = 1e9;
            for (int r = 0; r < 3; r++) {
                pthread_t th[16];
                for (int t = 0; t < T; t++) { w[t].k = k; w[t].tur = tur; w[t].z = Z; }
                double b0 = simdi();
                for (int t = 0; t < T; t++) pthread_create(&th[t], 0, calis, &w[t]);
                for (int t = 0; t < T; t++) pthread_join(th[t], 0);
                double e = simdi() - b0; if (e < en) en = e;
            }
            double flop = 2.0 * k * n * T * tur, bayt = 8.0 * n * T * tur;
            printf("  k=%3d  AI=%6.2f flop/byte  %6.1f GFLOP/s  %6.1f GB/s\n", k, flop / bayt, flop / en / 1e9, bayt / en / 1e9);
        }
        for (int t = 0; t < T; t++) { free(w[t].x); free(w[t].y); }
    }
    return 0;
}
```

Tek çekirdek, 12 bağımsız zincir:

```
$ clang -O2 -pthread nokta.c -o n && ./n 1 12
L1'e sigan (16 KB), 1 is parcacigi, 12 zincir
  k=  1  AI=  0.25 flop/byte    40.8 GFLOP/s   163.0 GB/s
  k=  2  AI=  0.50 flop/byte    62.7 GFLOP/s   125.5 GB/s
  k=  4  AI=  1.00 flop/byte    80.3 GFLOP/s    80.3 GB/s
  k=  8  AI=  2.00 flop/byte    90.8 GFLOP/s    45.4 GB/s
  k= 16  AI=  4.00 flop/byte    92.1 GFLOP/s    23.0 GB/s
  k= 32  AI=  8.00 flop/byte    87.4 GFLOP/s    10.9 GB/s
  k= 64  AI= 16.00 flop/byte    83.3 GFLOP/s     5.2 GB/s
  k=128  AI= 32.00 flop/byte    81.1 GFLOP/s     2.5 GB/s
bellekte (256 MB), 1 is parcacigi, 12 zincir
  k=  1  AI=  0.25 flop/byte    10.2 GFLOP/s    40.7 GB/s
  k=  2  AI=  0.50 flop/byte    19.6 GFLOP/s    39.3 GB/s
  k=  4  AI=  1.00 flop/byte    40.4 GFLOP/s    40.4 GB/s
  k=  8  AI=  2.00 flop/byte    72.9 GFLOP/s    36.5 GB/s
  k= 16  AI=  4.00 flop/byte    85.4 GFLOP/s    21.3 GB/s
  k= 32  AI=  8.00 flop/byte    74.8 GFLOP/s     9.4 GB/s
  k= 64  AI= 16.00 flop/byte    82.3 GFLOP/s     5.1 GB/s
  k=128  AI= 32.00 flop/byte    80.9 GFLOP/s     2.5 GB/s
```

Grafik (log-log; `.` = $\min(111, 41 \cdot I)$ çatısı, `o` = L1'de, `*` = bellekte):

```
GFLOP/s
160 |
    |
    |                             ...................................
    |                     o     .o.     *      o      *      *
 64 |              o          ...*             *
    |                       ...
    |       o             *..
    |                  ...
    |                ...
    |              ...
    |            ..*
 16 |          ...
    |       ...
    |     ..*
    |   ...
    | ...
    |..
  4 |
    +----------------------------------------------------------------
     1/8           1/2           2             8             32        flop/byte
```

- **Bellekte, $I \le 1$**: noktalar tam eğik çizginin üstünde; GB/s sütunu sabit 40 civarı. Burada hesap birimini hızlandırmak hiçbir şey kazandırmaz.
- **$I \ge 4$**: bellek sınırı kalkıyor; iki boyutta da 80–90 GFLOP/s. Tepe 111'in yaklaşık yüzde 80'i: 12 zincir (16 değil) ve döngü yükü.
- **L1'de**, $I$ küçükken: L1'in çatısı çok daha yukarıda (163 GB/s'e kadar ölçtük); burada sınır hesap ve yükleme/saklama komutları.
- Tek çekirdek için dönüm noktası $I^* \approx 111/41 \approx 2.7$ flop/byte.

4 zincirli sürümü de çalıştırdım: bellekte $k = 16$'da 81 GFLOP/s'e çıkıyor, $k = 128$'de 32.5'e düşüyor. Büyük $k$'da her elemanın zinciri uzuyor ve 4 zincir gecikmeyi kapatamıyor (Ders 11.2'nin tavanı: $4/16 \times 111 \approx 28$). Bu, roofline'ın altında kalan bir **iç tavan** (*ceiling*): ILP, SIMD ya da FMA olmadan ulaşılabilecek düşük çatılar. Williams ve arkadaşları bunları grafiğe ek yatay çizgiler olarak koyar.

---

## 5. Çok çekirdek

```
$ ./n 4 12        (secilmis satirlar)
L1'e sigan:  k= 16  330.3 GFLOP/s       bellekte: k=  1   11.8 GFLOP/s   47.0 GB/s
             k= 32  307.3                         k= 32  274.3           34.3
                                                  k=128  294.6            9.2
$ ./n 8 12
L1'e sigan:  k= 16  348.2 GFLOP/s       bellekte: k=  1   11.7 GFLOP/s   47.0 GB/s
                                                  k=128  341.3           10.7
```

- Hesap tavanı 4 çekirdekte yaklaşık **330** (4 × 83), 8 çekirdekte ancak 348: dört verimlilik çekirdeği hesapta zayıf.
- Bellek tavanı çekirdek sayısıyla **değişmiyor**: 1, 4, 8 iş parçacığında $k = 1$'de hep 47 GB/s civarı. Bu sanal makinenin bellek yolu tek çekirdekle neredeyse doyuyor.
- Dönüm noktası $330/47 \approx 7$ flop/byte'a kayıyor: çekirdek ekledikçe daha fazla kod **bellek sınırlı** sınıfına geçiyor. $k = 8$ ($I = 2$) tek çekirdekte hesap sınırına yakındı; 4 çekirdekte bellek sınırlı (89.7 GFLOP/s, 44.8 GB/s).

Bunun pratik sonucu: bellek sınırlı bir döngüyü paralel yapmak bu makinede **kazandırmaz**. Ders 11.20'de bir görüntü filtresinde bunu doğrudan göreceğiz.

---

## 6. Önceki derslere geri dönmek

Ders 11.6'daki `topla`, 384 MB'ta 0.232 ns/eleman: $1 / 0.232 = 4.3$ GFLOP/s. $I = 1/12$, çatı $41 \times 0.083 = 3.4$. Ölçüm çatının biraz **üstünde**: tahmin ettiğimiz 12 byte'ı değil, daha azını taşımış olamaz, demek ki bu çekirdekte bant genişliği 41'den biraz yüksek (okuma ağırlıklı karışım: iki okuma, bir yazma; salt okumada 56 ölçmüştük). Model doğru büyüklüğü veriyor ve bu döngünün **SIMD'in önemsiz olduğu** bölgede olduğunu söylüyor: Ders 11.6'da büyük dizide kazancın 1.7 kata düşmesinin nedeni bu.

Roofline'ın sınırları:

- $Q$'yu doğru saymak zor: önbellek isabetleri, write-allocate (Ders 11.16, Alıştırma 3), önyükleme.
- Tek bir $\beta$ yok: her önbellek seviyesinin kendi çatısı var (*hierarchical roofline*).
- Gecikme sınırlı kod (pointer kovalama) modelin dışında.

Yine de bir optimizasyona başlamadan "hangi duvara çarpıyorum?" sorusunu yanıtlamanın en ucuz yolu.

---

## Alıştırmalar

**1** – 2 GB/s'lik bir disk okuyan, her byte için 10 flop yapan bir program hangi sınıfta? Bu makinenin tek çekirdeği için ulaşılabilir hız nedir?

**2** – Dot product ($I = 0.25$) bu makinede tek çekirdekte en fazla kaç GFLOP/s yapabilir? Ders 11.14'te önbellekte ölçtüğümüz 0.178 çevrim/eleman kaç GFLOP/s?

**3** – Matris çarpımında $N = 1024$ için en iyi durum yoğunluğu $N/6$'dır. Bloklamasız `ikj` (Ders 7.26) neden bu yoğunluğa ulaşamaz? Gerçek yoğunluk ne olur?

**4** – 2. bölümdeki `mov` sorunu Horner yönteminde neden kaçınılmaz? Estrin yöntemi bunu çözer mi?

**5** – Bellek bant genişliği 47 GB/s, 8 çekirdekli hesap tavanı 348 GFLOP/s. Bu makinede hangi yoğunluğun altındaki kodu paralel yapmak anlamsızdır?

<details>
<summary>Cevaplar</summary>

**1** – $I = 10$ flop/byte ama bant genişliği 2 GB/s: çatı $2 \times 10 = 20$ GFLOP/s, hesap tavanı (111) çok yukarıda. Disk sınırlı.

**2** – $0.25 \times 41 \approx 10$ GFLOP/s (bellekte). Önbellekte 0.178 çevrim/eleman = $2 \text{ flop} / (0.178/3.5 \text{ ns}) \approx 39$ GFLOP/s: L1 bant genişliğinin çatısında, yüklemelerle sınırlı (Ders 11.14).

**3** – `ikj` her `i` için `B`'nin tamamını (4 MB) okuyor; `B` L1/L2'de kalmazsa her turda bellekten gelir. Byte sayısı $\approx N \cdot 4N^2 = 4N^3$, flop $2N^3$: $I \approx 0.5$. Bloklama, her bloğu birçok kez kullanarak yoğunluğu $b/\text{sabit}$'e çıkarır.

**4** – Horner $p = p \cdot x + c_k$: her adımda farklı bir sabit `c_k` eklenir, birikimci `c_k` olur, `fmla` `c_k`'nın kopyasını gerektirir. Pratikte derleyici bu `mov`'u çoğunlukla gizler (M2'de `mov`'lar ucuz ama ücretsiz değil). Estrin yöntemi terimleri ikişerli gruplar ($c_0 + c_1 x$) olarak hesaplar; bağımlılık zinciri kısalır ve daha fazla bağımsız `fmla` oluşur. `mov` sayısı aynı kalabilir, ama ILP artar.

**5** – Bellek tavanı çekirdek sayısıyla değişmediği için $I < 1$ civarında (tek çekirdekte bile bellek sınırlı olan) her şey. Tam söylemek gerekirse tek çekirdeğin dönüm noktası (~2.7) altındaki kodda kazanç küçüktür; 5. bölümde $I = 2$'de 4 çekirdek ancak 1.2 kat getirdi (72.9'dan 89.7'ye).

</details>

---

## Kaynaklar

- Samuel Williams, Andrew Waterman, David Patterson, "Roofline: An Insightful Visual Performance Model for Multicore Architectures", *Communications of the ACM*, 52(4), 2009.
- John McCalpin, "STREAM: Sustainable Memory Bandwidth in High Performance Computers" (cs.virginia.edu/stream).
- Aleksandar Ilic, Frederico Pratas, Leonel Sousa, "Cache-aware Roofline model", *IEEE Computer Architecture Letters*, 2014.
- Georg Hager ve Gerhard Wellein, *Introduction to High Performance Computing for Scientists and Engineers*, CRC Press, 2010.

**Sıradaki ders:** Matris çarpımı optimizasyonu. Naif sürümden blocking + SIMD + çok çekirdekli sürüme adım adım hızlandırma (GotoBLAS yaklaşımı).
