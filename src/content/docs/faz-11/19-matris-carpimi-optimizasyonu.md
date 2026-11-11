---
title: "11.19 Matris çarpımı optimizasyonu"
description: "Faz 11'in bütün araçları tek problemde: N=1024 float matris çarpımında naif sürümden 1.1 GFLOP/s ile başlayıp ikj, bloklama, 16 register'da tutulan 8x8 NEON mikro çekirdeği, GotoBLAS tarzı paketleme ve dört çekirdekle 337 GFLOP/s'e, yani 300 kata çıkmak; tek çekirdekte 97.5 GFLOP/s ile OpenBLAS'ın 105'ine ve 111'lik tepeye yaklaşmak; N=2048'de 2'nin kuvveti çakışmalarının bloklamayı bozması ve paketlemenin bunu çözmesi; verimlilik çekirdeklerinin eşit bölmede hızı düşürmesi."
---

Matris çarpımı yüksek başarımlı hesabın klasik sınavı: işlemi basit ($C \mathrel{+}= AB$), yoğunluğu büyük ($N/6$ flop/byte, Ders 11.18), ve iyi bir uygulama donanımın tepe hızına yaklaşabiliyor. Ders 7.26'da döngü sırası ve bloklamayla `double` için 16 GFLOP/s'e geldik. Bu derste `float` ile, adım adım, tepeye ne kadar yaklaşabildiğimizi görüyoruz. Yöntem, Kazushige Goto'nun GotoBLAS'ı ve onun torunu BLIS/OpenBLAS'ın yöntemi.

Hedef: tek çekirdekte 111 GFLOP/s (Ders 11.18'de ölçtük).

---

## 1. Kod

Bütün sürümler tek dosyada:

```c
/* mm.h: C += A * B, N x N float, satir oncelikli */
#include <stdlib.h>
#include <string.h>
#include <pthread.h>
#include <arm_neon.h>

/* 1. naif: i, j, k */
static void mm_ijk(float *C, const float *A, const float *B, int n) {
    for (int i = 0; i < n; i++)
        for (int j = 0; j < n; j++) {
            float s = C[i * n + j];
            for (int k = 0; k < n; k++) s += A[i * n + k] * B[k * n + j];
            C[i * n + j] = s;
        }
}

/* 2. i, k, j: ic dongu ardisik, derleyici vektorlestirir (Ders 7.26) */
static void mm_ikj(float *restrict C, const float *restrict A, const float *restrict B, int n) {
    for (int i = 0; i < n; i++)
        for (int k = 0; k < n; k++) {
            float a = A[i * n + k];
            for (int j = 0; j < n; j++) C[i * n + j] += a * B[k * n + j];
        }
}

/* 3. bloklu i, k, j */
#define BL 64
static void mm_blok(float *restrict C, const float *restrict A, const float *restrict B, int n) {
    for (int ii = 0; ii < n; ii += BL)
        for (int kk = 0; kk < n; kk += BL)
            for (int jj = 0; jj < n; jj += BL)
                for (int i = ii; i < ii + BL; i++)
                    for (int k = kk; k < kk + BL; k++) {
                        float a = A[i * n + k];
                        for (int j = jj; j < jj + BL; j++) C[i * n + j] += a * B[k * n + j];
                    }
}

/* 4. mikro cekirdek: C'nin 8x8'lik parcasi 16 register'da kalir.
   a: 8 satirin k. sutunu (adim lda), b: k. satirin 8 sutunu (adim ldb) */
static inline void cekirdek(float *C, int ldc, const float *a, long sa, long ka,
                            const float *b, long kb, int kc) {
    float32x4_t c[8][2];
    for (int r = 0; r < 8; r++) { c[r][0] = vld1q_f32(C + r * ldc); c[r][1] = vld1q_f32(C + r * ldc + 4); }
    for (int k = 0; k < kc; k++) {
        float32x4_t b0 = vld1q_f32(b + k * kb), b1 = vld1q_f32(b + k * kb + 4);
        float32x4_t a0, a1;
        if (sa == 1) { a0 = vld1q_f32(a + k * ka); a1 = vld1q_f32(a + k * ka + 4); }      /* paketli A */
        else {
            float t[8]; for (int r = 0; r < 8; r++) t[r] = a[r * sa + k * ka];
            a0 = vld1q_f32(t); a1 = vld1q_f32(t + 4);
        }
        c[0][0] = vfmaq_laneq_f32(c[0][0], b0, a0, 0); c[0][1] = vfmaq_laneq_f32(c[0][1], b1, a0, 0);
        c[1][0] = vfmaq_laneq_f32(c[1][0], b0, a0, 1); c[1][1] = vfmaq_laneq_f32(c[1][1], b1, a0, 1);
        c[2][0] = vfmaq_laneq_f32(c[2][0], b0, a0, 2); c[2][1] = vfmaq_laneq_f32(c[2][1], b1, a0, 2);
        c[3][0] = vfmaq_laneq_f32(c[3][0], b0, a0, 3); c[3][1] = vfmaq_laneq_f32(c[3][1], b1, a0, 3);
        c[4][0] = vfmaq_laneq_f32(c[4][0], b0, a1, 0); c[4][1] = vfmaq_laneq_f32(c[4][1], b1, a1, 0);
        c[5][0] = vfmaq_laneq_f32(c[5][0], b0, a1, 1); c[5][1] = vfmaq_laneq_f32(c[5][1], b1, a1, 1);
        c[6][0] = vfmaq_laneq_f32(c[6][0], b0, a1, 2); c[6][1] = vfmaq_laneq_f32(c[6][1], b1, a1, 2);
        c[7][0] = vfmaq_laneq_f32(c[7][0], b0, a1, 3); c[7][1] = vfmaq_laneq_f32(c[7][1], b1, a1, 3);
    }
    for (int r = 0; r < 8; r++) { vst1q_f32(C + r * ldc, c[r][0]); vst1q_f32(C + r * ldc + 4, c[r][1]); }
}

/* 4a. paketlemesiz: cekirdek dogrudan A ve B'den okur */
#define KC 256
static void mm_cekirdek(float *C, const float *A, const float *B, int n) {
    for (int kk = 0; kk < n; kk += KC)
        for (int i = 0; i < n; i += 8)
            for (int j = 0; j < n; j += 8)
                cekirdek(C + i * n + j, n, A + i * n + kk, n, 1, B + kk * n + j, n, KC);
}

/* 5. GotoBLAS: B'nin kc x nc dilimini, A'nin mc x kc blogunu paketle */
#define MC 128
static void paketle_A(float *pa, const float *A, int n, int i0, int k0) {   /* [i/8][k][8] */
    for (int i = 0; i < MC; i += 8)
        for (int k = 0; k < KC; k++)
            for (int r = 0; r < 8; r++) *pa++ = A[(i0 + i + r) * n + k0 + k];
}
static void paketle_B(float *pb, const float *B, int n, int k0, int j0, int nc) {   /* [j/8][k][8] */
    for (int j = 0; j < nc; j += 8)
        for (int k = 0; k < KC; k++) { memcpy(pb, B + (k0 + k) * n + j0 + j, 32); pb += 8; }
}
static void mm_goto_aralik(float *C, const float *A, const float *B, int n, int i_bas, int i_son, float *pa, float *pb) {
    int nc = n;
    for (int kk = 0; kk < n; kk += KC) {
        paketle_B(pb, B, n, kk, 0, nc);
        for (int ii = i_bas; ii < i_son; ii += MC) {
            paketle_A(pa, A, n, ii, kk);
            for (int j = 0; j < nc; j += 8)
                for (int i = 0; i < MC; i += 8)
                    cekirdek(C + (ii + i) * n + j, n, pa + i * KC, 1, 8, pb + j * KC, 8, KC);
        }
    }
}
static void mm_goto(float *C, const float *A, const float *B, int n) {
    float *pa = aligned_alloc(128, sizeof(float) * MC * KC), *pb = aligned_alloc(128, sizeof(float) * KC * n);
    mm_goto_aralik(C, A, B, n, 0, n, pa, pb);
    free(pa); free(pb);
}

/* 6. cok cekirdek: satir bloklari is parcaciklarina */
typedef struct { float *C; const float *A, *B; int n, bas, son; } Is;
static void *mm_is(void *v) {
    Is *w = v;
    float *pa = aligned_alloc(128, sizeof(float) * MC * KC), *pb = aligned_alloc(128, sizeof(float) * KC * w->n);
    mm_goto_aralik(w->C, w->A, w->B, w->n, w->bas, w->son, pa, pb);
    free(pa); free(pb);
    return 0;
}
static int IPLIK = 4;
static void mm_paralel(float *C, const float *A, const float *B, int n) {
    pthread_t th[16]; Is w[16];
    int blok = n / MC;
    for (int t = 0; t < IPLIK; t++) {
        w[t] = (Is){ C, A, B, n, blok * t / IPLIK * MC, blok * (t + 1) / IPLIK * MC };
        pthread_create(&th[t], 0, mm_is, &w[t]);
    }
    for (int t = 0; t < IPLIK; t++) pthread_join(th[t], 0);
}
```

Her sürüm sonucu `double` ile hesaplanmış bir referansla karşılaştırıyor (en büyük mutlak hata), ve OpenBLAS'ın `cblas_sgemm`'iyle yarışıyor.

---

## 2. Sonuçlar, N = 1024

```
$ clang -O3 -pthread olc.c -o o -lopenblas -lm && ./o 1024
1 naif ijk                1.894 s      1.1 GFLOP/s     1.0x  en buyuk hata 1.8e-05
2 ikj                     0.078 s     27.4 GFLOP/s    24.2x  en buyuk hata 1.8e-05
3 bloklu ikj              0.061 s     35.0 GFLOP/s    30.9x  en buyuk hata 1.8e-05
4 8x8 NEON cekirdek       0.030 s     71.1 GFLOP/s    62.7x  en buyuk hata 1.8e-05
5 + paketleme             0.022 s     97.5 GFLOP/s    86.0x  en buyuk hata 1.8e-05
6 + 4 cekirdek            0.006 s    337.0 GFLOP/s   297.2x  en buyuk hata 1.8e-05
6 + 8 cekirdek            0.006 s    338.1 GFLOP/s   298.1x  en buyuk hata 1.8e-05
OpenBLAS 1                0.020 s    105.1 GFLOP/s    92.6x  en buyuk hata 1.2e-05
OpenBLAS 4                0.006 s    367.0 GFLOP/s   323.6x  en buyuk hata 1.2e-05
OpenBLAS 8                0.018 s    121.6 GFLOP/s   107.2x  en buyuk hata 1.2e-05
```

Adım adım:

**1 → 2 (24 kat).** `ijk`'nin iç döngüsü `B`'yi sütun boyunca geziyor ve tek bir `s` birikimcisine bağlı (Ders 7.26). `ikj`'de iç döngü ardışık ve bağımsız; derleyici vektörleştiriyor (Ders 11.15).

**2 → 3 (1.3 kat).** Bloklama, `B`'nin bir parçasını önbellekte tutuyor. M2'nin 16 MB'lık L2'si 1024 için zaten çoğunu tutuyor, bu yüzden kazanç küçük.

**3 → 4 (2 kat).** Asıl sıçrama. `ikj`'nin iç döngüsü her `fmla` için `C`'den bir yükleme ve bir saklama yapıyor: 1 `fmla` başına 3 bellek erişimi. **Mikro çekirdek** $C$'nin 8×8'lik bir parçasını **register'da** tutuyor (16 `q` register'ı) ve her $k$ adımında:

```
b0, b1  = B'nin k. satirinin 8 elemani     (2 yukleme)
a0, a1  = A'nin k. sutunundan 8 eleman     (2 yukleme)
c[r]   += a[r] * b                          (16 fmla, vfmaq_laneq_f32)
```

16 `fmla` başına 4 yükleme, `C`'ye hiç dokunmadan. Ders 11.18'in dili ile, register düzeyinde aritmetik yoğunluk $16 \cdot 8 / (4 \cdot 16) = 2$ flop/byte'tan çok daha yüksek bir değere çıktı. `vfmaq_laneq_f32(c, b, a, 3)`, `b` vektörünü `a`'nın 3. şeridiyle çarpıp `c`'ye ekliyor: dışsal çarpımın tek komutu (Ders 11.14).

Ama bu sürümde `A`'nın sütunu bellekte **8 satıra dağılmış**: her `k` için 8 ayrı yükleme yapıp geçici diziye kopyalıyoruz.

**4 → 5 (1.4 kat): paketleme.** GotoBLAS'ın ana fikri: çekirdeğin okuyacağı veriyi önceden, **tam okunacağı sırayla** ardışık bir tampona kopyalamak.

```
A blogu (MC x KC = 128 x 256)  ->  pa: [8 satirlik serit][k][8]     128 KB, L2'de
B dilimi (KC x N  = 256 x 1024) ->  pb: [8 sutunluk serit][k][8]     1 MB, L2'de
```

Böylece çekirdek her iki girdiyi de **adım 1** ile, ardışık okuyor: önyükleyici için ideal, TLB için ideal, çakışma ıskası yok. Paketlemenin kendisi $O(N^2)$ kopya, çarpım $O(N^3)$: büyük $N$'de ücretsiz.

Blok boyutları önbelleklere göre seçiliyor:

| Parça | Boyut | Nerede kalmalı |
| --- | --- | --- |
| C mikro bloğu | 8 × 8 | register (16 tane) |
| B mikro şeridi | KC × 8 = 8 KB | L1 |
| A bloğu | MC × KC = 128 KB | L2 |
| B dilimi | KC × N = 1 MB | L2 (paylaşılan) |

Tek çekirdekte **97.5 GFLOP/s**: tepenin yüzde 88'i, OpenBLAS'ın yüzde 93'ü. OpenBLAS'ın elle yazılmış assembly çekirdeği yazmadığımız birkaç şey yapıyor: daha büyük bir mikro blok (register'ların hepsini kullanan), yazılımla önyükleme ve döngü açma.

**5 → 6: çekirdekler.** `C`'nin satır bantlarını iş parçacıklarına böldük: her biri kendi `A` paketini ve `B` paketini tutuyor (B'yi her iş parçacığının yeniden paketlemesi basit ama israf). Dört performans çekirdeğinde **337 GFLOP/s** (3.5 kat), OpenBLAS 367.

**8 çekirdek** ise kazandırmıyor: biz 338, OpenBLAS **122**'ye düşüyor. Dört verimlilik çekirdeği performans çekirdeklerinin hızının çok altında; işi eşit bölünce bütün program en yavaş iş parçacığını bekliyor. Bizim kodda bant sayısı (8) 8 iş parçacığına eşit dağıldı ve P çekirdekleri işlerini bitirip bekledi; OpenBLAS'ın bölme şekli bu makinede daha kötü sonuç verdi. Heterojen çekirdekli işlemcilerde **iş çalma** ya da çekirdek türüne göre bölüştürme gerekiyor.

Hata sütunu: her sürüm `float` sonucunu `double` referansla karşılaştırıyor. $1.8 \times 10^{-5}$ hepsinde aynı, OpenBLAS biraz daha iyi ($1.2 \times 10^{-5}$; toplama sırası farklı, Ders 11.11).

---

## 3. N = 2048: 2'nin kuvveti geri döndü

```
$ ./o 2048
1 naif ijk               62.520 s      0.3 GFLOP/s     1.0x  en buyuk hata 3.7e-05
2 ikj                     0.633 s     27.2 GFLOP/s    98.8x  en buyuk hata 3.7e-05
3 bloklu ikj              0.720 s     23.9 GFLOP/s    86.9x  en buyuk hata 3.7e-05
4 8x8 NEON cekirdek       0.360 s     47.8 GFLOP/s   173.9x  en buyuk hata 3.7e-05
5 + paketleme             0.201 s     85.5 GFLOP/s   311.1x  en buyuk hata 3.7e-05
6 + 4 cekirdek            0.059 s    290.3 GFLOP/s  1056.6x  en buyuk hata 3.7e-05
6 + 8 cekirdek            0.053 s    324.3 GFLOP/s  1180.1x  en buyuk hata 3.7e-05
OpenBLAS 1                0.164 s    105.0 GFLOP/s   382.0x  en buyuk hata 1.5e-05
OpenBLAS 4                0.047 s    365.1 GFLOP/s  1328.6x  en buyuk hata 1.5e-05
OpenBLAS 8                0.070 s    245.7 GFLOP/s   894.1x  en buyuk hata 1.5e-05
```

- Naif sürüm 1.1'den **0.3** GFLOP/s'e düştü: `B`'nin sütununda ardışık elemanlar 8 KB arayla, hepsi aynı önbellek kümesinde (Ders 11.17).
- **Bloklama** `ikj`'den **yavaş** oldu: Ders 11.17'deki transpozun aynısı. 64'lük blokta `B`'nin satırları yine 8 KB arayla ve aynı kümelere düşüyor.
- Paketlemesiz NEON çekirdeği 71'den 48'e indi; aynı neden.
- **Paketleme** sorunu kendiliğinden çözüyor (85.5): kopyalanan tampon ardışık, `N`'nin değeri artık önemsiz. GotoBLAS'ın paketlemesinin ikinci büyük getirisi bu.

---

## 4. Ne kaldı?

Tek çekirdekte bizim 97.5 / 85.5 ile OpenBLAS'ın 105 arası:

1. **Mikro blok büyüklüğü.** 8×8 için 16 birikimci; 32 register'ın yarısı. 8×12 (24 birikimci) her `k` adımında 24 `fmla` için 5 yükleme yapar: daha iyi oran.
2. **Kenarlar.** Kodumuz `N`'nin 128'in ve 256'nın katı olduğunu varsayıyor. Gerçek kütüphane kenar parçalarını sıfırla doldurulmuş paketlerle ya da küçük çekirdeklerle işliyor.
3. **B'yi bir kez paketlemek** ve iş parçacıkları arasında paylaşmak.
4. **Assembly.** Derleyicinin register ayırması ve komut sırası çoğunlukla iyi, ama en iç döngüyü elle zamanlamak son yüzde 5–10'u kazandırıyor.

Faz 11'in özeti tek tabloda:

| Adım | Ders | Kazanç (N=1024) |
| --- | --- | --- |
| Ardışık erişim | 7.26 | 24× |
| Bloklama | 7.26, 11.17 | 1.3× |
| Register bloklama + SIMD | 11.2, 11.14 | 2.0× |
| Paketleme | 11.16, 11.17 | 1.4× |
| Çok çekirdek | Faz 10 | 3.5× |
| **Toplam** | | **~300×** |

---

## Alıştırmalar

**1** – Mikro çekirdekte her `k` adımında kaç flop, kaç byte yükleme var? Yükleme kapasitesi (çevrimde ~3) ve `fmla` kapasitesi (çevrimde 4) göz önüne alındığında sınır hangisi?

**2** – `KC`'yi 128 ve 512 yapıp ölç. Tablodaki önbellek hesabıyla açıkla.

**3** – Mikro çekirdeği 8×12'ye genişlet (24 birikimci). Kaç register gerekir? 32'ye sığar mı?

**4** – `mm_paralel`'de B paketlemesini paylaşmak için ne gerekir? Hangi senkronizasyon?

**5** – `N = 1000` için kod neden çalışmaz? En basit düzeltme nedir?

<details>
<summary>Cevaplar</summary>

**1** – 16 `fmla` × 8 flop = 128 flop; 4 yükleme × 16 byte = 64 byte. 16 `fmla` 4 çevrim, 4 yükleme ~1.3 çevrim: sınır `fmla` (hesap), olması gerektiği gibi.

**2** – Kendi ölçümün. `KC = 128`: B mikro şeridi 4 KB, A bloğu 64 KB; çekirdek her çağrıda daha kısa çalışır, `C` 8×8 bloğunun yükleme/saklama maliyeti daha sık ödenir. `KC = 512`: B şeridi 16 KB (L1'e hâlâ sığar), A bloğu 256 KB.

**3** – 24 birikimci + 3 `b` vektörü (12 sütun) + 2 `a` vektörü = 29 register. 32'ye sığar, ama sınırda: derleyici geçici değerler için yer bulamazsa register taşırır (spill). Assembly'de `str q.., [sp]` olup olmadığına bak.

**4** – Her `kk` turunda B bir kez paketlenmeli, ardından bütün iş parçacıkları o paketi kullanmalı, sonra bir sonraki `kk`'ya geçilmeli: her `kk` turunun başında ve sonunda bir **bariyer** (`pthread_barrier_wait`). Paketlemenin kendisi de iş parçacıkları arasında bölünebilir.

**5** – 1000, 8'in katı değil, 128'in hiç değil: mikro çekirdek dizinin sonunu okur ve yazar. En basit düzeltme, matrisleri 1024'e (128'in katına) sıfırla doldurmak; doğru sonuç verir ama yüzde 7 boşa iş yapar. Daha iyisi paketlerken kenarları sıfırla doldurup yazarken yalnız geçerli kısmı yazmak.

</details>

---

## Kaynaklar

- Kazushige Goto ve Robert van de Geijn, "Anatomy of High-Performance Matrix Multiplication", *ACM TOMS*, 34(3), 2008.
- Field G. Van Zee ve Robert van de Geijn, "BLIS: A Framework for Rapidly Instantiating BLAS Functionality", *ACM TOMS*, 41(3), 2015.
- Tze Meng Low ve ark., "Analytical Modeling Is Enough for High-Performance BLIS", *ACM TOMS*, 43(2), 2016 (blok boyutlarının seçimi).
- OpenBLAS (github.com/OpenMathLib/OpenBLAS), `kernel/arm64/`.

**Sıradaki ders:** Faz projesi. SIMD ile hızlandırılmış görüntü filtresi ve hızlı `strlen`/`memchr`, her adımda ölçüm grafiği.
