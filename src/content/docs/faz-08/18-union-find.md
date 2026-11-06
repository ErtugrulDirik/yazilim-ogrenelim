---
title: "8.18 Union-find"
description: "Ayrık kümeler yapısı: birleştir ve bul işlemleri, her kümenin kökü temsilci olan bir ağaç, bütün yapının tek bir ebeveyn dizisi; saf sürümün zincire dönüşmesi, rank ile birleştirme (yükseklik ≤ log₂ n ispatı) ve yol sıkıştırma; dört sürümün 100 bin ve 10 milyon elemanda ölçümü (saf: işlem başına 6480 adım, ikisi birlikte: 0.90); ters Ackermann fonksiyonu α(n) ve neden pratikte 4'ü geçmediği; ızgarada süzülme simülasyonu ve 0.5927 eşiği."
---

Bazı problemler tek bir soruya iner: **bu iki şey aynı gruba mı ait?** Bir ağda iki bilgisayar birbirine (dolaylı olarak) bağlı mı? Bir resimde iki piksel aynı renkli bölgede mi? Bir derleyicinin tip çıkarımında iki tip değişkeni aynı tipe mi bağlandı? Gruplar zamanla **birleşiyor** ama hiç ayrılmıyor. Bu iki işlemi, birleştirme ve sorgulamayı, neredeyse $O(1)$'de yapan yapıya **union-find** ya da **ayrık kümeler** (disjoint sets) deniyor. Kodu 20 satır; analizi ise bilgisayar biliminin en şaşırtıcı sonuçlarından biri.

---

## 1. Problem ve fikir

Elemanlar $0, 1, \dots, n-1$. Başta her eleman kendi tek elemanlı kümesinde. İki işlem:

- `birlestir(a, b)`: `a`'nın kümesi ile `b`'nin kümesini birleştir.
- `bul(x)`: `x`'in kümesinin **temsilcisini** döndür. İki eleman aynı kümedeyse `bul` ikisi için aynı temsilciyi verir.

Ders 6.6'nın diliyle: birleştirmeler bir **denklik bağıntısı** kuruyor, ve `bul` bir elemanın denklik sınıfını söylüyor.

Fikir (Galler ve Fischer, 1964): her küme bir **ağaç**, kökü kümenin temsilcisi. Ağaçlar Ders 8.7'deki gibi yukarıdan aşağı değil, **aşağıdan yukarı** bağlı: her eleman sadece ebeveynini biliyor. Ebeveyn bağlantısı tek bir tamsayı olduğu için bütün orman tek bir dizi: `ebeveyn[x]`. Kök, kendi kendisinin ebeveyni.

- `bul(x)`: ebeveynleri izleyerek köke çık.
- `birlestir(a, b)`: iki kökü bul; birini ötekinin çocuğu yap.

```
 başta:            0  1  2  3  4  5          ebeveyn: 0 1 2 3 4 5

 birlestir(3, 4):  0  1  2  4  5             ebeveyn: 0 1 2 4 4 5
                             |
                             3

 birlestir(1, 3):  0  2  4  5                ebeveyn: 0 4 2 4 4 5
                         / \
                        3   1
```

İki elemanın aynı kümede olup olmadığı: `bul(a) == bul(b)`. Bir kümenin elemanlarını listelemek ya da kümeyi ikiye ayırmak bu yapıda yok (Alıştırma 5); karşılığında aranan iki işlem çok hızlı.

---

## 2. Kod

```c
/* Union-find (ayrik kumeler): her kume bir agac, koku kumenin temsilcisi. Dizi uzerinde ebeveyn pointer'lari. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct {
    int *ebeveyn;
    unsigned char *rank;          /* agac yuksekliginin ust siniri; log2(n)'den buyuk olamaz: 1 bayt yeter */
    int n, kume_sayisi;
    bool rank_kullan, sikistir;
    long adim;                    /* istatistik: find'da izlenen ebeveyn baglantisi */
} UF;

UF *uf_olustur(int n, bool rank_kullan, bool sikistir) {
    UF *u = malloc(sizeof *u);
    u->ebeveyn = malloc(n * sizeof *u->ebeveyn);
    u->rank = calloc(n, 1);
    for (int i = 0; i < n; i++) u->ebeveyn[i] = i;     /* herkes kendi kumesinin koku */
    u->n = u->kume_sayisi = n;
    u->rank_kullan = rank_kullan; u->sikistir = sikistir; u->adim = 0;
    return u;
}

int uf_bul(UF *u, int x) {
    int k = x;
    while (u->ebeveyn[k] != k) { k = u->ebeveyn[k]; u->adim++; }     /* koke cik */
    if (u->sikistir)
        while (u->ebeveyn[x] != k) { int s = u->ebeveyn[x]; u->ebeveyn[x] = k; x = s; }   /* yoldakileri koke bagla */
    return k;
}

bool uf_birlestir(UF *u, int a, int b) {
    a = uf_bul(u, a); b = uf_bul(u, b);
    if (a == b) return false;                          /* zaten ayni kumede */
    if (u->rank_kullan) {
        if (u->rank[a] < u->rank[b]) { int t = a; a = b; b = t; }   /* a: rank'i buyuk olan */
        u->ebeveyn[b] = a;                             /* kisa agac uzun agacin altina */
        if (u->rank[a] == u->rank[b]) u->rank[a]++;
    } else {
        u->ebeveyn[a] = b;                             /* saf: ilkinin kokunu ikinciye bagla */
    }
    u->kume_sayisi--;
    return true;
}

void uf_yok_et(UF *u) { free(u->ebeveyn); free(u->rank); free(u); }
```

(`malloc` hata kontrolleri kısalık için yok.) İki iyileştirme, iki bayrakla açılıp kapatılabiliyor ki dört sürümü karşılaştırabilelim. Önce ikisi de açıkken:

```c
int main(void) {
    UF *u = uf_olustur(10, true, true);
    int ciftler[][2] = { {4, 3}, {3, 8}, {6, 5}, {9, 4}, {2, 1}, {8, 9}, {5, 0}, {7, 2}, {6, 1} };
    for (int i = 0; i < 9; i++) {
        bool b = uf_birlestir(u, ciftler[i][0], ciftler[i][1]);
        printf("birlestir(%d, %d)%s  kume=%d  ebeveyn:", ciftler[i][0], ciftler[i][1], b ? "" : " zaten bagli", u->kume_sayisi);
        for (int j = 0; j < 10; j++) printf(" %d", u->ebeveyn[j]);
        printf("\n");
    }
    ...
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined uf.c -o uf && ./uf
birlestir(4, 3)  kume=9  ebeveyn: 0 1 2 4 4 5 6 7 8 9
birlestir(3, 8)  kume=8  ebeveyn: 0 1 2 4 4 5 6 7 4 9
birlestir(6, 5)  kume=7  ebeveyn: 0 1 2 4 4 6 6 7 4 9
birlestir(9, 4)  kume=6  ebeveyn: 0 1 2 4 4 6 6 7 4 4
birlestir(2, 1)  kume=5  ebeveyn: 0 2 2 4 4 6 6 7 4 4
birlestir(8, 9) zaten bagli  kume=5  ebeveyn: 0 2 2 4 4 6 6 7 4 4
birlestir(5, 0)  kume=4  ebeveyn: 6 2 2 4 4 6 6 2 4 4
birlestir(7, 2)  kume=3  ebeveyn: 6 2 2 4 4 6 6 2 4 4
birlestir(6, 1)  kume=2  ebeveyn: 6 2 6 4 4 6 6 2 4 4
bul(8)==bul(9)? evet   bul(0)==bul(7)? evet   bul(0)==bul(3)? hayir
```

Sonunda iki küme kaldı: kökü 4 olan `{3, 4, 8, 9}` ve kökü 6 olan geri kalanlar. `birlestir(8, 9)` "zaten bağlı" dedi: 8 ve 9 o anda zaten 4 üzerinden aynı kümedeydi. Bu, union-find'ın en önemli kullanımlarından biri: bir kenarın bir **döngü** kapatıp kapatmadığını anlamak (Alıştırma 3).

---

## 3. İki iyileştirme

### Saf sürüm neden kötü

Saf sürümde `birlestir`, ilk kökü ikinciye bağlıyor. Ağaçların şekli tamamen işlem sırasına bağlı ve Ders 8.8'deki BST gibi bir **zincire** dönüşebiliyor: `birlestir(0, 1)`, `birlestir(1, 2)`, ..., `birlestir(n-2, n-1)` dizisi $0 \to 1 \to 2 \to \dots \to n-1$ zincirini kuruyor ve `bul(0)` $n - 1$ adım sürüyor.

### Rank ile birleştirme

Her kök, ağacının yüksekliği için bir üst sınır saklıyor: **rank**. Birleştirirken rank'i **küçük** olan ağaç büyüğün altına konuyor. Eşitse herhangi biri, ve yeni kökün rank'i bir artıyor. Ağaç sadece iki eşit ağaç birleşince uzuyor.

> **Önerme**: rank'i $r$ olan bir kökün ağacında en az $2^r$ eleman var.

Tümevarım: rank 0, tek eleman, $2^0 = 1$. Bir kökün rank'i $r$'den $r + 1$'e sadece rank'i $r$ olan iki ağaç birleşince çıkıyor; ikisinde de en az $2^r$ eleman, toplam en az $2^{r+1}$. Rank'i değişmeyen birleştirmeler eleman sayısını sadece artırıyor. Buradan rank (ve dolayısıyla yükseklik) hiçbir zaman $\log_2 n$'yi geçmiyor: $n$ elemanlı bir yapıda bir ağacın $2^r \le n$ elemanı olabilir. Her `bul` $O(\log n)$. Rank'in neden bir bayta sığdığı da buradan: $\log_2 n \le 31$.

(Alternatif: rank yerine **boyut**, yani eleman sayısı saklayıp küçük ağacı büyüğün altına koymak. Aynı $\log_2 n$ sınırını veriyor, ve boyut başka amaçlar için de kullanılabiliyor.)

### Yol sıkıştırma

`bul(x)` kökü bulduktan sonra yoldan **ikinci kez** geçip her düğümü doğrudan köke bağlıyor. Bir sonraki `bul` aynı düğümlerden geçerse tek adımda bitiyor.

```
 bul(a) öncesi:          sonrası:

        k                    k
        |                  / | \
        c                 a  b  c
        |
        b
        |
        a
```

Sıkıştırma ağacı **yassılaştırıyor** ama rank'leri güncellemiyor; rank artık kesin yükseklik değil, sadece bir üst sınır. Bu sorun değil, çünkü rank'in görevi birleştirmede karar vermek ve bunun için üst sınır yeterli.

---

## 4. Ölçüm

Dört sürüm, iki iş yükü. Rastgele: $n$ eleman, $2n$ rastgele çift üzerinde `birlestir`, sonra $n$ rastgele `bul`. Kötü niyetli: Bölüm 3'teki zincir, sonra 1000 kez `bul(0)`. "Adım" bir ebeveyn bağlantısı izlemek; `birlestir`'in kendi iki `bul`'u da sayılıyor.

```
$ cc -std=c11 -O2 -Wall olcum.c -o olcum && ./olcum 100000
rastgele: n=100000, 200000 birlestir + 100000 bul
  saf              islem basina 6479.56 adim   14.906 s  kume=1865  en derin agac=16783
  rank             islem basina   1.60 adim    0.006 s  kume=1865  en derin agac=7
  sikistirma       islem basina   2.57 adim    0.006 s  kume=1865  en derin agac=4
  rank+sikistirma  islem basina   0.90 adim    0.003 s  kume=1865  en derin agac=3
zincir: n=100000, birlestir(i, i+1), sonra 1000 kez bul(0)
  saf              yapim sonrasi en derin= 99999   bul(0) basina  99999.00 adim  0.0404 s
  rank             yapim sonrasi en derin=     1   bul(0) basina      0.00 adim  0.0000 s
  sikistirma       yapim sonrasi en derin= 99999   bul(0) basina    101.00 adim  0.0001 s
  rank+sikistirma  yapim sonrasi en derin=     1   bul(0) basina      0.00 adim  0.0000 s
```

- **Saf sürüm rastgele girdide bile felaket**: 100 bin elemanda işlem başına 6480 adım, 15 saniye; 16 783 derinliğinde bir ağaç. Sebebi, rastgele birleştirmelerin hızla tek bir **dev küme** oluşturması (rastgele graflarda **dev bileşen** olgusu; Erdős ve Rényi, 1960): her yeni birleştirme o dev ağacın kökünü küçük bir ağacın altına bağlıyor ve ağaç her seferinde bir seviye uzuyor. Aynı ölçüm 1 milyon elemanla çalıştırıldığında saf sürüm işlem başına 65 438 adım attı ve **32 dakika** sürdü (en derin ağaç 168 295); eleman sayısı 10 katına çıkınca işlem başına maliyet de 10 katına çıkıyor, yani işlem başına $O(n)$. Rank ve sıkıştırmalı sürüm aynı girdide 0.032 s.
- **Rank tek başına** her şeyi düzeltiyor: işlem başına 1.6 adım, en derin ağaç 7 ($\log_2 10^5 = 16.6$ sınırının çok altında). Zincir girdisinde derinlik 1: her yeni eleman tek elemanlı (rank 0) bir ağaç olarak büyük ağacın köküne bağlanıyor.
- **Sıkıştırma tek başına** zinciri kurmayı engellemiyor (derinlik 99 999) ama ilk `bul(0)` 99 999 adım sürüp bütün zinciri yassılaştırıyor, sonraki 999'u 1'er adım: ortalama 101. Pahalı bir işlemin sonraki işlemleri ucuzlattığı **amortize** analiz (Ders 4.24).
- **İkisi birlikte** en iyisi: işlem başına 0.90 adım. 1'den az, çünkü çoğu `bul` doğrudan bir köke ya da kökün çocuğuna denk geliyor.

Saf sürüm olmadan 10 milyon eleman:

```
$ ./olcum 10000000 atla
rastgele: n=10000000, 20000000 birlestir + 10000000 bul
  rank             islem basina   1.65 adim    1.363 s  kume=187364  en derin agac=9
  sikistirma       islem basina   3.33 adim    1.970 s  kume=187364  en derin agac=5
  rank+sikistirma  islem basina   0.90 adim    0.741 s  kume=187364  en derin agac=3
```

Eleman sayısı 100 kat arttı, işlem başına adım **değişmedi**: 0.90. Süre işlem başına 25 ns, ve bunun neredeyse tamamı 40 MB'lık diziye rastgele erişimlerin cache kaçırmaları (Ders 7.24). Sanitizer'lı derleme temiz.

---

## 5. Ters Ackermann

Rank ve yol sıkıştırma birlikte kullanıldığında $m$ işlemin toplam maliyeti $O(m \, \alpha(n))$ (Robert Tarjan, 1975). Buradaki $\alpha$, **Ackermann fonksiyonunun tersi**.

Ackermann fonksiyonu akıl almaz hızla büyüyen bir fonksiyon. Bir sürümü:

$$
A_0(x) = x + 1, \qquad A_{k+1}(x) = A_k^{(x+1)}(x) \quad (A_k\text{'yı } x+1 \text{ kez uygula}).
$$

$A_1(x) = 2x + 1$; $A_2(x) \approx 2^x \cdot x$; $A_3(x)$ bir 2'nin kuvvetleri kulesi ($2^{2^{2^{\cdots}}}$, yüksekliği $x$ civarı); $A_4(1)$ ise o kadar büyük ki ondalık yazımı, gözlemlenebilir evrendeki atom sayısından ($\approx 10^{80}$) çok daha fazla basamak ister. $\alpha(n)$, $A_k(1) \ge n$ olan en küçük $k$:

| $n$ | $\alpha(n)$ |
| --- | --- |
| 0–2 | 0 |
| 3 | 1 |
| 4–7 | 2 |
| 8–2047 | 3 |
| 2048 – $A_4(1)$ | 4 |

$A_4(1)$, $2^{2^{2^{\cdots}}}$ biçiminde 2048 katlı bir kule civarında. Evrende yazılabilecek her $n$ için $\alpha(n) \le 4$. Pratikte sabit; ama teoride sabit **değil**, çok çok yavaş da olsa büyüyor. Tarjan, 1979'da, bu yapının bir genelleştirilmiş modelde $\Omega(m \, \alpha(n))$'den daha hızlı olamayacağını da gösterdi: ters Ackermann gerçekten problemin doğasında. İnce bir analiz, ama sonucu basit: her işlem pratikte $O(1)$.

Ölçümün söylediği de bu: 100 bin ve 10 milyon elemanda işlem başına 0.90 adım.

---

## 6. Uygulama: süzülme

Bir $N \times N$ ızgaradaki hücreler kapalı başlıyor ve rastgele sırayla **açılıyor**. Açık bir hücre, açık komşularıyla (yukarı, aşağı, sol, sağ) bağlı. Ne zaman üst kenardan alt kenara açık hücrelerle giden bir yol oluşur? Fizikte **süzülme** (percolation) problemi: suyun gözenekli bir kayadan sızması, bir ormanda yangının yayılması, bir malzemenin iletken hale gelmesi. Açık hücre oranı belirli bir **eşiği** geçince bağlantı bir anda ortaya çıkıyor, ve bu eşiğin kesin değeri bilinmiyor; sadece simülasyonla tahmin ediliyor.

Union-find ile: her hücre bir eleman, artı iki sanal eleman, `UST` ve `ALT`. Üst satırdaki her açık hücre `UST`'a, alt satırdakiler `ALT`'a bağlı. Hücre açıldıkça açık komşularıyla birleştiriliyor; `bul(UST) == bul(ALT)` olduğu anda süzülme var.

```c
/* Suzulme (percolation): N x N izgarada hucreler rastgele aciliyor; ust kenar alt kenara ne zaman baglaniyor? */
#define KUTUPHANE
#include "uf.c"
#include <math.h>
#include <string.h>

static uint32_t xs = 2024u;
static uint32_t rnd(void) { xs ^= xs << 13; xs ^= xs >> 17; xs ^= xs << 5; return xs; }

/* Bir deneme: acik hucre orani (suzulme aninda). Iki sanal dugum: UST = N*N, ALT = N*N + 1. */
static double deneme(int N, int ciz) {
    int toplam = N * N, UST = toplam, ALT = toplam + 1;
    UF *u = uf_olustur(toplam + 2, true, true);
    bool *acik = calloc(toplam, 1);
    int *sira = malloc(toplam * sizeof *sira);
    for (int i = 0; i < toplam; i++) sira[i] = i;
    for (int i = toplam - 1; i > 0; i--) { int j = rnd() % (i + 1), t = sira[i]; sira[i] = sira[j]; sira[j] = t; }   /* Fisher-Yates */
    int acilan = 0;
    while (uf_bul(u, UST) != uf_bul(u, ALT)) {
        int h = sira[acilan++], s = h / N, g = h % N;
        acik[h] = true;
        if (s == 0) uf_birlestir(u, h, UST);
        if (s == N - 1) uf_birlestir(u, h, ALT);
        int ds[] = { -1, 1, 0, 0 }, dg[] = { 0, 0, -1, 1 };
        for (int k = 0; k < 4; k++) {
            int ys = s + ds[k], yg = g + dg[k];
            if (ys >= 0 && ys < N && yg >= 0 && yg < N && acik[ys * N + yg]) uf_birlestir(u, h, ys * N + yg);
        }
    }
    if (ciz) {
        int kok = uf_bul(u, UST);
        for (int s = 0; s < N; s++) {
            printf("  ");
            for (int g = 0; g < N; g++) { int h = s * N + g; putchar(!acik[h] ? '#' : uf_bul(u, h) == kok ? 'o' : '.'); }
            printf("\n");
        }
    }
    double oran = (double)acilan / toplam;
    free(acik); free(sira); uf_yok_et(u);
    return oran;
}

int main(void) {
    printf("20 x 20, bir deneme ('o': ustten ulasilabilen acik, '.': diger acik, '#': kapali):\n");
    printf("  acik oran: %.3f\n", deneme(20, 1));
    int boyutlar[] = { 20, 100, 500, 1000 };
    for (int b = 0; b < 4; b++) {
        int N = boyutlar[b], T = N <= 100 ? 1000 : 50;
        double top = 0, kare = 0;
        for (int t = 0; t < T; t++) { double p = deneme(N, 0); top += p; kare += p * p; }
        double ort = top / T, sap = sqrt((kare / T - ort * ort));
        printf("N=%4d, %4d deneme: ortalama esik %.4f, standart sapma %.4f\n", N, T, ort, sap);
    }
}
```

(`calloc`/`malloc` hata kontrolleri kısalık için yok.)

```
$ cc -std=c11 -O2 -Wall -Wextra suzulme.c -o suzulme -lm && time ./suzulme
20 x 20, bir deneme ('o': ustten ulasilabilen acik, '.': diger acik, '#': kapali):
  ##oooo###o#oo#o#oooo
  o####ooo###ooo##o###
  ooo#o#o##ooo##oooo#.
  o#oooo#o#o#o#ooo##..
  o#ooooooo#ooooo#....
  ####oo#o##ooo##.#..#
  .#ooo#oooo#o##o#o#.#
  #oo#oo#ooo#oo#oooo#.
  #oooo##oo#oooo#oo#..
  .##oo###oooo#ooo#...
  ##.#ooo#ooooo###..#.
  o##ooooo#ooo###.....
  oo#oo##o####..#.#...
  oooooo##oooo#..#o#.#
  ooo##ooooo#oo##ooo#o
  ###ooooo#ooo#ooooo#o
  o##o#oo##oooo#oooo#o
  oooooooo##o#o#o#oooo
  ##ooooo#.##o#oooooo#
  oooo#ooo#o#ooooo#ooo
  acik oran: 0.652
N=  20, 1000 deneme: ortalama esik 0.5935, standart sapma 0.0489
N= 100, 1000 deneme: ortalama esik 0.5929, standart sapma 0.0164
N= 500,   50 deneme: ortalama esik 0.5934, standart sapma 0.0052
N=1000,   50 deneme: ortalama esik 0.5927, standart sapma 0.0031
./suzulme  1.43s user 0.01s system 77% cpu 1.866 total
```

Bu tek denemede eşik 0.652'de aşıldı (ortalamadan yüksek, ama $N = 20$'de sapma büyük). Ortalama eşik bütün boyutlarda yaklaşık **0.593**; ızgara büyüdükçe denemeler arası sapma küçülüyor ve eşik keskinleşiyor. Literatürdeki değer $p_c \approx 0.592746$. 1000 × 1000'lik 50 deneme (her biri yaklaşık 600 bin hücre açıp 2.4 milyon birleştirme yapan) toplam bir saniyenin altında. Saf union-find ile tek bir deneme saatler sürerdi.

Bunu BFS (Ders 8.5) ile de yapabilirdik: her hücre açıldıktan sonra üst kenardan bir arama. Ama her arama $O(N^2)$ ve hücre başına bir arama $O(N^4)$; union-find her hücreyi açarken sabit iş yapıyor.

---

## Alıştırmalar

**1** – Bölüm 3'teki önermenin ispatında "rank'i değişmeyen birleştirmeler eleman sayısını sadece artırıyor" dedik. Yol sıkıştırma, bir ağaçtaki eleman sayısını ya da kökün rank'ini değiştirir mi? Önerme sıkıştırmayla birlikte de geçerli mi?

**2** – **Yol yarılama** (path halving): `bul` yolda ilerlerken her düğümü **büyük ebeveynine** bağlıyor: `ebeveyn[x] = ebeveyn[ebeveyn[x]]; x = ebeveyn[x];`. Kodu yaz. Tam yol sıkıştırmaya göre avantajı ne? Aynı $O(\alpha(n))$ sınırı bunun için de geçerli.

**3** – Bir graf kenar kenar veriliyor: (0,1), (1,2), (3,4), (2,0), (2,3), (4,1). Union-find ile hangi kenarların bir **döngü** kapattığını bul. Bu, Ders 9'daki Kruskal en küçük kapsayan ağaç algoritmasının çekirdeği; nasıl?

**4** – Bölüm 4'teki "en derin ağaç" değeri rank sürümünde 10 milyon elemanda 9 çıktı, sınır $\log_2 10^7 \approx 23$. Sınır neden bu kadar gevşek? Hangi işlem dizisi sınıra ulaşan bir ağaç üretir?

**5** – Union-find kümeleri **ayıramıyor**: `ayir(a, b)` yok. Neden bu yapıyla verimli bir ayırma yapılamıyor? Kenarları zamanla hem eklenen hem silinen bir grafta bağlantı sorgusu için ne yapılabilir?

<details>
<summary>Cevaplar</summary>

**1** – Değiştirmez. Sıkıştırma sadece **aynı ağacın içinde** düğümlerin ebeveynlerini değiştiriyor; hiçbir düğüm ağaçtan çıkmıyor ya da ağaca girmiyor, ve kök aynı kalıyor. Rank sadece köklerde anlamlı ve sadece `birlestir`'de değişiyor. Önermedeki "rank $r$ olan kökün ağacında en az $2^r$ eleman" iddiası eleman sayısı ve rank hakkında, ağacın şekli hakkında değil; sıkıştırma ikisine de dokunmadığı için önerme geçerli. Değişen tek şey, rank'in artık yüksekliğin kendisi değil sadece bir üst sınırı olması.

**2** –

```c
int uf_bul_yari(UF *u, int x) {
    while (u->ebeveyn[x] != x) {
        u->ebeveyn[x] = u->ebeveyn[u->ebeveyn[x]];    /* buyuk ebeveyne atla */
        x = u->ebeveyn[x];
    }
    return x;
}
```

Yolu **tek geçişte** kısaltıyor: ikinci bir döngü, ya da kökü bulana kadar düğümleri hatırlamak (özyineleme ya da yığın) gerekmiyor. Her adımda yolun uzunluğu yaklaşık yarıya iniyor. Döngü daha basit ve dal tahmini için daha dostça; birçok kütüphane bu sürümü kullanıyor. Tarjan ve van Leeuwen (1984) yol yarılama ve yol bölmenin (path splitting) de rank ile birlikte $O(m\,\alpha(n))$ verdiğini gösterdi.

**3** – Her kenar `(a, b)` için `birlestir(a, b)`; `false` dönerse (a ve b zaten aynı kümedeydi) bu kenar bir döngü kapatıyor. Sırayla: (0,1) birleştir, (1,2) birleştir, (3,4) birleştir, **(2,0)**: 2 ve 0 zaten bağlı (0–1–2 üzerinden), döngü. (2,3) iki kümeyi birleştirir, **(4,1)**: 4 ve 1 artık bağlı (4–3–2–1), döngü. Kruskal: kenarları ağırlıklarına göre sırala, sırayla ekle, döngü kapatanları atla. Eklenenler en küçük kapsayan ağacı oluşturuyor. Sıralama $O(E \log E)$, union-find işlemleri $O(E\,\alpha(V))$; algoritmanın darboğazı sıralama.

**4** – Sınır en kötü durum için: yükseklik ancak **eşit rank'li** iki ağaç birleşince artıyor. Sınıra ulaşmak için $n = 2^k$ elemanı bir turnuva ağacı gibi birleştirmek gerekiyor: önce $(0,1), (2,3), \dots$ çiftleri (rank 1), sonra o çiftleri ikişer ikişer (rank 2), ... $k$ turda tek bir ağaç ve yükseklik $k = \log_2 n$. Rastgele birleştirmelerde ağaçların rank'leri nadiren eşit oluyor: dev küme hızla büyüyor ve küçük ağaçlar onun altına bir seviyede ekleniyor. Bu yüzden 10 milyon elemanda en derin ağaç 9. (Sıkıştırma olmadan bile.)

**5** – Bir birleştirme iki kökü bağlıyor, ama sonraki birleştirmeler ve yol sıkıştırma, hangi elemanın hangi birleştirme yüzünden kümede olduğu bilgisini siliyor. `ayir(a, b)` için o bilgi gerekirdi: "a ile b'yi bağlayan" kenar kaldırılınca hangi elemanların hangi tarafta kaldığı. Union-find sadece **sonucu** (kim kiminle aynı kümede) tutuyor, **sebebi** (hangi kenarlar) tutmuyor. Tamamen dinamik bağlantı (kenar ekleme ve silme) için çok daha karmaşık yapılar var: Holm, de Lichtenberg ve Thorup'un algoritması işlem başına $O(\log^2 n)$ amortize; link-cut ağaçları ormanlar için $O(\log n)$. Eğer bütün işlemler önceden biliniyorsa (çevrimdışı), silmeleri ters sırada eklemelere çevirip union-find kullanmak mümkün, ya da zaman ekseninde böl-yönet ile geri alınabilir bir union-find (yol sıkıştırmasız, sadece rank'li; her birleştirme bir yığına yazılıp geri alınabiliyor).

</details>

---

## Kaynaklar

- Bernard Galler ve Michael Fischer, "An Improved Equivalence Algorithm", *Communications of the ACM* 7(5), 1964.
- Robert Tarjan, "Efficiency of a Good But Not Linear Set Union Algorithm", *Journal of the ACM* 22(2), 1975.
- Robert Tarjan ve Jan van Leeuwen, "Worst-Case Analysis of Set Union Algorithms", *Journal of the ACM* 31(2), 1984.
- Robert Sedgewick ve Kevin Wayne, *Algorithms* (4. baskı), Bölüm 1.5: union-find ve süzülme örneği.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 21.
- Mark Newman ve Robert Ziff, "Efficient Monte Carlo algorithm and high-precision results for percolation", *Physical Review Letters* 85, 2000: $p_c = 0.59274621$.

**Sıradaki ders:** Graf gösterimleri. Komşuluk matrisi ve listesi, CSR formatı.
