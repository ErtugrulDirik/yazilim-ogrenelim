---
title: "7.26 Cache dostu kod"
description: "Önbellek bilgisini koda dökmek: C'de dizilerin satır öncelikli (row-major) dizilişi ve gezinme sırasının etkisi (64 MB'lık matriste sütun sırası ~10–30 kat yavaş); matris çarpımında döngü sırası (ijk, ikj, jki) ve ikj'nin 8 kat, jki'nin 40 kat farkı; bloklama (tiling) ile çalışma kümesini L1'e sığdırmak ve blok boyutunun seçimi; yapı dizisi (AoS) ve dizi yapısı (SoA); Apple M2 üzerinde ölçümler."
---

Ders 7.24'te belleğin hiyerarşik olduğunu ve yerelliğin önbelleği işe yarattığını gördük; Ders 7.25'te önbelleğin satır satır nasıl çalıştığını. Bu ders bunları **programcının elindeki** kararlara çeviriyor. Algoritma aynı kaldığı, yapılan işlem sayısı hiç değişmediği halde, sadece döngülerin sırasını ya da verinin dizilişini değiştirerek 40 kat hız farkı göreceğiz. Büyük-O analizi (Ders 6.12) bu farkı göremez: ikisi de $O(n^3)$.

Bütün ölçümler Apple M2'de (`cc -O2`), tek bir programla.

---

## 1. C dizileri bellekte: satır öncelikli

Ders 4.3'te gördüğümüz gibi `int T[R][S]` dizisi bellekte satır satır durur: `T[0][0]`, `T[0][1]`, ..., `T[0][S-1]`, sonra `T[1][0]`. `T[i][j]`'nin adresi `T + (i·S + j)·4`.

- `j`'yi artırmak 4 bayt ileri gitmek: **ardışık**, aynı önbellek satırı.
- `i`'yi artırmak $4S$ bayt ileri gitmek: $S = 4096$ ise **16 KB**, her adım yeni bir satır (ve sık sık yeni bir sayfa, Ders 7.27).

Aynı toplamı iki sırayla hesaplayalım (64 MB'lık bir `int` matrisi: hiçbir önbelleğe sığmaz):

```c
    /* 1) Ayni toplam, iki gezinme sirasi */
    double t0 = simdi(); long s1 = 0;
    for (int i = 0; i < T_N; i++) for (int j = 0; j < T_N; j++) s1 += T[i][j];   /* ardisik */
    double t1 = simdi() - t0;
    t0 = simdi(); long s2 = 0;
    for (int j = 0; j < T_N; j++) for (int i = 0; i < T_N; i++) s2 += T[i][j];   /* 16 KB adim */
    double t2 = simdi() - t0;
```

```
satir sirasi:  toplam=125829120  2.1 ms
sutun sirasi:  toplam=125829120  57.6 ms  (27.5x yavas)
```

Satır sırası 64 MB'ı 2.1 ms'de okuyor (~30 GB/s: bant genişliği sınırı, Ders 7.24 Bölüm 6). Sütun sırasında her erişim farklı bir satıra düşüyor ve 128 baytlık M2 satırının sadece 4 baytı kullanılıyor; satırın geri kalanı, `j` bir artıp aynı yere dönülene kadar (4096 erişim sonra) önbellekten çoktan atılmış oluyor. Çalıştırmalar arasında oran 10 ile 30 arasında değişti (ilk çalıştırmada satır sırası 7.8 ms ölçüldü: bellek sayfaları ilk kez dokunuluyordu), ama yön hiç değişmedi.

**Kural: en içteki döngü, en sağdaki indisi gezmeli.** Fortran ve MATLAB sütun öncelikli (column-major): orada kural tersi. NumPy her ikisini de destekler (`order='C'` / `'F'`).

---

## 2. Matris çarpımı: döngü sırası

$C = A \cdot B$, $N \times N$ `double` matrisler, $N = 1024$ (her biri 8 MB). Klasik formül $C_{ij} = \sum_k A_{ik} B_{kj}$ üç iç içe döngü ister, ve döngülerin sırası **altı** şekilde seçilebilir; hepsi aynı $2N^3 \approx 2.1 \times 10^9$ kayan nokta işlemi yapar.

```c
__attribute__((noinline)) static void ijk(void) {     /* ic dongu Bm'yi sutun sutun gezer */
    for (int i = 0; i < N; i++)
        for (int j = 0; j < N; j++) {
            double s = 0;
            for (int k = 0; k < N; k++) s += A[i][k] * Bm[k][j];
            C[i][j] = s;
        }
}

__attribute__((noinline)) static void ikj(void) {     /* ic dongu satir satir: ardisik bellek */
    for (int i = 0; i < N; i++)
        for (int k = 0; k < N; k++) {
            double a = A[i][k];
            for (int j = 0; j < N; j++) C[i][j] += a * Bm[k][j];
        }
}
```

İç döngüye bakarak tahmin yürütebiliriz:

| Sıra | İç döngü | `A` | `B` | `C` |
| --- | --- | --- | --- | --- |
| `ijk` | `k` | satır boyunca (ardışık) | **sütun boyunca** (8 KB adım) | sabit |
| `ikj` | `j` | sabit | satır boyunca | satır boyunca |
| `jki` | `i` | **sütun boyunca** | sabit | **sütun boyunca** |

```
ijk (naif)   iz=24227483  1.190 s  1.80 GFLOP/s
ikj          iz=24227483  0.154 s  13.96 GFLOP/s
```

`iz` (köşegen toplamı) üç sürümün de aynı sonucu bulduğunu doğruluyor. `ikj` **8 kat** hızlı. Sebep yalnızca önbellek değil: `ikj`'nin iç döngüsü `C[i][j] += a * B[k][j]` ardışık ve bağımsız olduğu için derleyici onu SIMD komutlarıyla vektörleştiriyor (Ders 7.29) ve işlemci birçok yüklemeyi paralel başlatıyor; `ijk`'nin iç döngüsü ise tek bir `s` akümülatörüne bağımlılık zinciri (Ders 7.23) **ve** sütun gezinmesi. Önbellek dostu kod çoğu zaman vektörleştirmeye de dost.

---

## 3. Bloklama (tiling)

`ikj` iyi, ama $N$ büyüdükçe bir sorun var: `i`'nin her değerinde `B`'nin **tamamı** (8 MB) baştan sona okunuyor. `B` L1'e (128 KB) sığmadığı için her `i` turunda yeniden L2'den (ya da RAM'den) geliyor.

**Bloklama** fikri: matrisleri $b \times b$'lik bloklara bölüp çarpımı blok blok yapmak. Bir blok çarpımı sırasında kullanılan veri: üç blok, $3 \cdot b^2 \cdot 8$ bayt. $b = 64$ için $3 \cdot 64^2 \cdot 8 = 96$ KB, L1'e sığıyor. Blok önbelleğe bir kez gelir ve $b$ kez kullanılır.

```c
#define B 64                         /* blok boyutu: 3 blok * 64*64*8 B = 96 KB */

__attribute__((noinline)) static void bloklu(void) {  /* B x B bloklar cache'te kalir */
    for (int ii = 0; ii < N; ii += B)
        for (int kk = 0; kk < N; kk += B)
            for (int jj = 0; jj < N; jj += B)
                for (int i = ii; i < ii + B; i++)
                    for (int k = kk; k < kk + B; k++) {
                        double a = A[i][k];
                        for (int j = jj; j < jj + B; j++) C[i][j] += a * Bm[k][j];
                    }
}
```

İç üç döngü, Bölüm 2'deki `ikj`'nin tek bir blok üzerinde çalışan hali; dış üç döngü bloklar üzerinde aynı `ikj` sırasını izliyor. İşlem sayısı yine tam $2N^3$.

```
ikj          iz=24227483  0.154 s  13.96 GFLOP/s
bloklu ikj   iz=24227483  0.135 s  15.86 GFLOP/s
```

$N = 1024$'te kazanç sadece ~%13. M2'nin 16 MB'lık L2'si üç matrisin (24 MB) önemli bir kısmını tutuyor ve önceden getirici `ikj`'nin ardışık erişimlerini iyi besliyor. $N = 2048$'de (her matris 32 MB):

```
ikj          iz=97020915  1.261 s  13.62 GFLOP/s
bloklu ikj   iz=97020915  1.078 s  15.94 GFLOP/s
```

~%17. Daha eski ya da daha küçük önbellekli işlemcilerde fark çok daha büyük olur. Önemli olan şu: bloklu sürüm $N$ büyüdükçe performansını **korur**, çünkü çalışma kümesi $N$'den bağımsız (her zaman üç blok). Gerçek matris kütüphaneleri (OpenBLAS, Apple Accelerate, Intel MKL) bloklamayı her önbellek seviyesi için ayrı ayrı yapar, SIMD ve elle zamanlanmış assembly çekirdeklerle birleştirir ve M2'de yüzlerce GFLOP/s'e ulaşır. Faz 11'de bu sayıya yaklaşmaya çalışacağız.

Blok boyutunun seçimi (Alıştırma 3): çok küçük bloklarda döngü yükü artar, çok büyüklerde bloklar L1'e sığmaz.

---

## 4. Veri yerleşimi: AoS ve SoA

Önbellek dostu olmak sadece döngü sırası değil, **verinin nasıl dizildiği** de. Bir parçacık simülasyonu düşün:

```c
/* Yapi dizisi (Array of Structs, AoS) */
struct Parcacik { double x, y, z, vx, vy, vz, kutle; int tur; };   /* 64 bayt */
struct Parcacik p[1000000];

/* Dizi yapisi (Struct of Arrays, SoA) */
struct Parcaciklar { double x[1000000], y[1000000], z[1000000], /* ... */ ; };
```

Sadece `x` koordinatlarını toplayan bir döngü:

- **AoS**: her parçacık 64 bayt; `p[i].x` her satırdan sadece 8 bayt kullanıyor. Önbelleğe getirilen verinin 7/8'i boşa.
- **SoA**: `x[]` dizisi ardışık; her satırın tamamı kullanılıyor, ve SIMD ile 2–8 `x` aynı anda işlenebiliyor.

Bütün alanların birlikte kullanıldığı işlerde (bir parçacığı tam güncellemek) AoS daha doğal ve aynı derecede iyi olabilir. Karar erişim desenine bakarak verilir. Oyun motorlarındaki "veri odaklı tasarım" (data-oriented design) ve sütun tabanlı veritabanları bu fikrin uygulamaları.

Ders 4.26'daki hizalama ve dolgu da buraya bağlanıyor: bir `struct`'ın alanlarını büyükten küçüğe dizmek dolguyu azaltır, daha fazla nesne aynı önbellek satırına sığar.

---

## 5. Kontrol listesi

1. **En içteki döngü ardışık belleği gezsin.** C'de en sağdaki indis.
2. **Veriyi bir kez getirip çok kullan.** Bloklama, döngü birleştirme (aynı dizi üzerindeki iki döngüyü tek döngüye indirmek).
3. **Sadece gereken veriyi getir.** SoA, sıkıştırılmış veri tipleri (`double` yerine `float`, `int64_t` yerine `int32_t` yetiyorsa).
4. **İşaretçi kovalamadan kaçın.** Bağlı listeler, ağaçlar, düğüm başına `malloc` (Ders 7.24'teki 100 ns'lik merdiven); mümkünse diziler, havuz ayırıcıları (Ders 4.28'deki arena).
5. **2'nin kuvveti adımlara dikkat.** Ders 7.25'teki çakışma ıskaları; gerekirse dolgu.
6. **Ölç.** Önbellek davranışı tahmin etmesi zor bir şey; Faz 11'de donanım sayaçlarıyla (`perf stat -e cache-misses`, macOS'ta Instruments) doğrudan ıska sayacağız.

---

## Alıştırmalar

**1** – `jki` sırasını yaz (iç döngü `i`) ve ölç. Bölüm 2'deki tabloya bakarak `ijk`'den hızlı mı yavaş mı olacağını önce tahmin et.

**2** – Bir matrisin devriğini (transpose) alan `B[j][i] = A[i][j]` döngüsünde hem satır hem sütun gezinmesi var; döngü sırasını değiştirmek sorunu çözmez. Neden? Bloklama burada nasıl yardım eder?

**3** – Bloklu çarpımı $b$ = 16, 32, 64, 128, 256 ile ölç. En iyi $b$ hangisi? $3b^2 \cdot 8$ baytı her $b$ için hesapla ve L1 (128 KB) ile karşılaştır.

**4** – Sadece `x` alanını toplayan bir döngüde AoS (64 baytlık `struct`) ile SoA arasında bellekten okunan bayt miktarı kaç kat fark eder? M2'nin 128 baytlık satırını kullan.

**5** – Bölüm 1'deki sütun sırası döngüsünü, `T`'yi değiştirmeden hızlandırmanın bir yolu var mı? (İpucu: dış döngüde aynı anda birkaç `j` sütunu.)

<details>
<summary>Cevaplar</summary>

**1** – `jki`'nin iç döngüsü hem `A`'yı hem `C`'yi **sütun** boyunca geziyor: tablodaki en kötü satır. Ölçüm (M2, $N = 1024$): **6.1 s, 0.35 GFLOP/s**. `ijk`'den 5 kat, `ikj`'den **40 kat** yavaş. Aynı formül, aynı işlem sayısı, aynı sonuç (`iz` aynı).

**2** – Okunan `A` satır boyunca gezilirse yazılan `B` sütun boyunca gezilir, ya da tersi: ikisinden biri her zaman 8 KB'lık adımlarla gidiyor. Bloklama: matrisi örneğin 32 × 32'lik bloklara böl; bir bloğun devriği alınırken okunan blok (8 KB) ve yazılan blok (8 KB) L1'e sığar. Sütun boyunca gidilse bile 32 satırın hepsi önbellekte durur, her satırın tamamı kullanılır.

**3** – Ölçümler ($N = 1024$):

| $b$ | $3b^2 \cdot 8$ | Süre | GFLOP/s |
| --- | --- | --- | --- |
| 16 | 6 KB | 0.157 s | 13.6 |
| 32 | 24 KB | 0.143 s | 15.0 |
| 64 | 96 KB | 0.140 s | 15.4 |
| 128 | 384 KB | 0.205 s | 10.5 |
| 256 | 1.5 MB | 0.195 s | 11.0 |

En iyi $b = 64$: üç blok L1'e (128 KB) sığan en büyük boyut. $b = 128$'de bloklar L1'den taşıyor ve performans `ikj`'nin bile altına düşüyor. $b = 16$'da veri sığıyor ama iç döngü sadece 16 tur, döngü yükü ve vektörleştirme verimi düşüyor.

**4** – AoS: her parçacık 64 bayt, bir 128 baytlık satırda 2 parçacık, satır başına 2 `x` (16 bayt kullanışlı veri). SoA: bir satırda 16 `x`. 1 milyon `x` için AoS 64 MB, SoA 8 MB okur: **8 kat** fark. Bellek bant genişliğiyle sınırlı bir döngüde bu doğrudan ~8 kat süre farkı demek.

**5** – Evet: dış döngüyü birkaç `j`'yi birlikte işleyecek şekilde açmak. Örneğin `for (j = 0; j < S; j += 32) for (i = 0; i < R; i++) for (jj = j; jj < j + 32; jj++) s += T[i][jj];`. Her satıra gelindiğinde 32 ardışık `int` (128 bayt, tam bir M2 satırı) okunur. Bu, Bölüm 3'teki bloklamanın tek boyutlu hali; toplamın sırası değişse de tamsayı toplama birleşmeli olduğu için sonuç aynı.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 6.5–6.6: önbellek dostu kod yazmak, matris çarpımı döngü sıraları (bu dersteki `ijk`/`ikj`/`jki` karşılaştırması oradan).
- Monica Lam, Edward Rothberg & Michael Wolf, "The Cache Performance and Optimizations of Blocked Algorithms" (ASPLOS 1991).
- Kazushige Goto & Robert van de Geijn, "Anatomy of High-Performance Matrix Multiplication" (ACM TOMS, 2008): BLAS kütüphanelerinin çok seviyeli bloklaması.
- Richard Fabian, *Data-Oriented Design* (2018).

**Sıradaki ders:** Sanal bellek. Sayfalama, sayfa tablosu, TLB, adres çevirisi adım adım.
