---
title: "8.12 Heap ve öncelik kuyruğu"
description: "Öncelik kuyruğu soyut tipi ve ikili heap: pointer'sız, dizi üzerinde tam ikili ağaç (çocuklar 2i+1, 2i+2); heap özelliği, yukarı çıkarma ile ekleme ve aşağı indirme ile en küçüğü çekme, ikisi de O(log n); n elemanı tek tek eklemek yerine aşağıdan yukarı heapify ile O(n)'de heap kurmak, ispatı ve 10 milyon elemanda ölçümü (eleman başına 1.88 karşılaştırma); olay güdümlü simülasyon: bankada gişe kuyruğu, kuyruk teorisinin tahminleriyle karşılaştırma; en büyük k eleman ve akan veride medyan alıştırmaları."
---

Ders 8.4'teki yığın en son ekleneni, Ders 8.5'teki kuyruk en eski ekleneni veriyordu. Çoğu zaman ikisi de istenen şey değil. İşletim sisteminin zamanlayıcısı **en yüksek öncelikli** işi çalıştırmak ister; bir yol bulma algoritması **en yakın** düğümü işlemek ister (Dijkstra, Faz 9); bir simülasyon **en erken** olayı işlemek ister. Bu soyut tipin adı **öncelik kuyruğu** (priority queue):

| İşlem | Anlamı |
| --- | --- |
| `ekle(x)` | `x`'i kuyruğa koy |
| `en_kucuk()` | En küçük (en öncelikli) elemanı göster |
| `cek()` | En küçüğü çıkar ve döndür |

Ders 8.9–8.10'daki dengeli ağaçlar bunu $O(\log n)$'de yapabilir, ama gereğinden fazlasını yapıyorlar: her elemanın tam sırasını tutuyorlar. Öncelik kuyruğu sadece **en küçüğü** bilmek istiyor. Bu zayıf gereksinim çok daha basit ve hızlı bir yapıya izin veriyor: **ikili heap**. Pointer'ı yok, düğüm ayırma yok, tek bir dizi.

---

## 1. Dizi üzerinde ağaç

Bir **tam ikili ağaç** (complete binary tree), son seviyesi hariç her seviyesi dolu ve son seviyesi soldan sağa doldurulmuş ağaç. Böyle bir ağacın şekli sadece düğüm sayısına bağlı; o yüzden onu pointer'sız, seviye sırasıyla (Ders 8.7) bir diziye yazabiliriz:

```
             a[0]
          /        \
       a[1]        a[2]
      /    \      /    \
   a[3]   a[4]  a[5]   a[6]
   / \
a[7] a[8] ...
```

Pointer'ların yerini aritmetik alıyor:

$$
\text{sol}(i) = 2i + 1, \qquad \text{sağ}(i) = 2i + 2, \qquad \text{ebeveyn}(i) = \lfloor (i-1)/2 \rfloor.
$$

(Diziyi 1'den başlatanlar $2i$, $2i+1$, $\lfloor i/2 \rfloor$ yazar; bu kitapların çoğundaki gösterim. C'de 0'dan başlamak daha doğal.) $n$ elemanlı bir tam ağacın yüksekliği $\lfloor \log_2 n \rfloor$: Ders 8.7, Alıştırma 3'teki alt sınıra eşit, yani **olabilecek en kısa ağaç**. Ders 8.8–8.10'daki dengeleme sorunları burada hiç yok, çünkü şekil hiçbir zaman değişmiyor; sadece eleman sayısı değişiyor.

**Heap özelliği** (min-heap): her düğüm, çocuklarından küçük ya da eşit. Buradan kök, bütün elemanların en küçüğü. Ama başka bir sıra garantisi yok: kardeşler arasında ya da farklı dallar arasında bir ilişki yok. BST'deki "solda küçükler" kuralına göre çok daha gevşek. (Max-heap'te tersi: her düğüm çocuklarından büyük ya da eşit.)

---

## 2. İki temel işlem

Her değişiklik heap özelliğini en fazla **bir yerde** bozar ve onu düzeltmenin iki yönü var:

- **Yukarı çıkarma** (sift-up): bir eleman ebeveyninden küçükse yer değiştir, tekrarla.
- **Aşağı indirme** (sift-down): bir eleman çocuklarından birinden büyükse **küçük olan** çocukla yer değiştir, tekrarla.

İkisi de en fazla ağacın yüksekliği kadar adım: $O(\log n)$.

```c
/* Ikili min-heap: dizi uzerinde tam ikili agac. Kok a[0]; i'nin cocuklari 2i+1, 2i+2; ebeveyni (i-1)/2. */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct { long *a; size_t n, kap; long karsilastirma; } Heap;

static bool kucuk(Heap *h, size_t i, size_t j) { h->karsilastirma++; return h->a[i] < h->a[j]; }
static void takas(Heap *h, size_t i, size_t j) { long t = h->a[i]; h->a[i] = h->a[j]; h->a[j] = t; }

static void yukari_cik(Heap *h, size_t i) {           /* sift-up: ebeveyninden kucuk oldukca yer degistir */
    while (i > 0) {
        size_t e = (i - 1) / 2;
        if (!kucuk(h, i, e)) break;
        takas(h, i, e);
        i = e;
    }
}

static void asagi_in(Heap *h, size_t i) {             /* sift-down: kucuk cocuktan buyuk oldukca yer degistir */
    for (;;) {
        size_t s = 2 * i + 1, en = i;
        if (s < h->n && kucuk(h, s, en)) en = s;
        if (s + 1 < h->n && kucuk(h, s + 1, en)) en = s + 1;
        if (en == i) break;
        takas(h, i, en);
        i = en;
    }
}
```

`asagi_in`'de **küçük** çocukla yer değiştirmek şart: büyük çocukla değiştirsek, yukarı çıkan büyük çocuk öteki çocuktan büyük olur ve özellik bozulur. `karsilastirma` sayacı Bölüm 3'teki ölçüm için.

**Ekleme**: yeni elemanı dizinin **sonuna** koy (ağacın son seviyesindeki ilk boş yer; şekil tam kalıyor), sonra yukarı çıkar. **Çekme**: kökü al; **son** elemanı köke taşı (şekil yine tam), sonra aşağı indir.

```c
bool heap_ekle(Heap *h, long x) {
    if (h->n == h->kap) {
        size_t yk = h->kap ? 2 * h->kap : 16;
        long *y = realloc(h->a, yk * sizeof *y);
        if (!y) return false;
        h->a = y; h->kap = yk;
    }
    h->a[h->n++] = x;                                  /* en sona koy (agacin son seviyesi) */
    yukari_cik(h, h->n - 1);
    return true;
}

bool heap_cek(Heap *h, long *x) {                     /* en kucugu cikar */
    if (h->n == 0) return false;
    *x = h->a[0];
    h->a[0] = h->a[--h->n];                            /* son elemani koke tasi */
    asagi_in(h, 0);
    return true;
}
```

Büyüme Ders 4.24'teki dinamik dizi; ekleme amortize $O(\log n)$.

```c
int main(void) {
    Heap h = { 0 };
    long g[] = { 5, 3, 8, 1, 9, 2, 7 };
    for (int i = 0; i < 7; i++) heap_ekle(&h, g[i]);
    printf("dizi:"); for (size_t i = 0; i < h.n; i++) printf(" %ld", h.a[i]); printf("\nagac:\n"); yaz(&h);
    long x; printf("cek:");
    while (heap_cek(&h, &x)) printf(" %ld", x);
    printf("\n");
    free(h.a);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c -o deneme && ./deneme
dizi: 1 3 2 5 9 8 7
agac:
  1 
  3 2 
  5 9 8 7 
cek: 1 2 3 5 7 8 9
```

(`yaz`, diziyi seviye seviye bölüp yazdıran küçük bir yardımcı.) Dizi sıralı değil (`3` ile `2`, `9` ile `8` "ters"), ama her düğüm çocuklarından küçük. Art arda çekmek elemanları **sıralı** veriyor: heap'e $n$ eleman koyup $n$ kez çekmek bir sıralama algoritması, **heapsort**, $O(n \log n)$ (Ders 9.6'da yerinde, ek dizi kullanmadan yazacağız).

---

## 3. Heap'i $O(n)$'de kurmak

Elimizde $n$ elemanlı bir dizi varsa onu heap'e çevirmenin bariz yolu $n$ kez `heap_ekle`: $O(n \log n)$. Daha iyisi var. Diziyi zaten bir tam ağaç olarak düşün; heap özelliği sadece bozuk. Yaprakların (dizinin ikinci yarısı, `n/2`'den sonrası) çocuğu yok, onlar kendi başlarına geçerli birer heap. Son iç düğümden başlayıp köke doğru her düğümü **aşağı indirirsek**, her adımda iki çocuğu zaten heap olan bir düğümü düzeltmiş oluyoruz:

```c
/* Dizinin tamamini heap'e cevir: yapraklar zaten heap; son ic dugumden koke dogru asagi_in. O(n). */
void heap_kur(Heap *h, long *a, size_t n) {
    h->a = a; h->n = h->kap = n; h->karsilastirma = 0;
    for (size_t i = n / 2; i-- > 0; ) asagi_in(h, i);
}
```

(`for (i = n/2; i-- > 0; )`, işaretsiz `i` ile geriye sayarken `i >= 0` koşulunun her zaman doğru olması tuzağından kaçmanın kalıbı; Ders 3.6.)

Neden $O(n)$? Bir düğümü aşağı indirmenin maliyeti, onun **altındaki** yükseklik kadar. Düğümlerin yarısı yaprak (0 adım), dörtte biri yaprakların bir üstü (en fazla 1 adım), sekizde biri 2 adım... Toplam:

$$
\sum_{k \ge 1} \frac{n}{2^{k+1}} \cdot k \;=\; \frac{n}{2} \sum_{k \ge 1} \frac{k}{2^k} \;=\; \frac{n}{2} \cdot 2 \;=\; n.
$$

($\sum k x^k = x/(1-x)^2$, $x = 1/2$'de 2; Ders 6.16.) Pahalı işlemler (köke yakın, uzun yollar) az sayıda düğümde; ucuz işlemler çok sayıda düğümde. `heap_ekle` ile tek tek kurmada ise tam tersi: elemanların yarısı son seviyeye ekleniyor ve en kötü durumda **köke kadar** çıkıyor.

Ölçüm (rastgele `long`'lar ve azalan sıralı dizi; azalan, min-heap'e ekleme için en kötü durum, çünkü her yeni eleman köke kadar çıkıyor):

```c
        Heap h1 = { 0 };
        double t0 = simdi();
        for (size_t i = 0; i < n; i++) heap_ekle(&h1, a[i]);
        double t1 = simdi();
        Heap h2;
        heap_kur(&h2, b, n);
        double t2 = simdi();
```

```
$ cc -std=c11 -O2 -Wall kur.c -o kur && ./kur
n= 1000000  tek tek ekle:  2.28 karsilastirma/eleman 0.009 s   heap_kur: 1.88 karsilastirma/eleman 0.004 s  gecerli=11
          azalan girdi:  tek tek 17.95   heap_kur 2.00  karsilastirma/eleman
n=10000000  tek tek ekle:  2.28 karsilastirma/eleman 0.084 s   heap_kur: 1.88 karsilastirma/eleman 0.047 s  gecerli=11
          azalan girdi:  tek tek 21.32   heap_kur 2.00  karsilastirma/eleman
```

- Azalan girdide tek tek ekleme eleman başına $\log_2 n$ civarında karşılaştırma yapıyor (17.95 ≈ $\log_2 10^6 - 2$, 21.32 ≈ $\log_2 10^7 - 2$): $n$ ile **büyüyor**. `heap_kur` 2.00'de sabit. $O(n \log n)$'e karşı $O(n)$ farkı tam olarak bu.
- Rastgele girdide tek tek ekleme de sabit görünüyor (2.28). Rastgele bir eleman ortalamada sadece birkaç seviye yukarı çıkıyor, çünkü ağacın yarısı yapraklarda ve yeni elemanın onların ebeveyninden küçük olma olasılığı düşük. Ortalama durum iyi, en kötü durum $O(\log n)$. `heap_kur`'un garantisi en kötü durum için.
- Süre olarak `heap_kur` iki kat hızlı. `gecerli=11`: iki heap de özelliği sağlıyor (bütün `i` için `a[i] >= a[(i-1)/2]` denetimi).

---

## 4. Olay güdümlü simülasyon

Gerçek bir sistemi saniye saniye simüle etmek israf: çoğu saniyede bir şey olmuyor. **Olay güdümlü simülasyon** (discrete-event simulation) zamanı atlıyor: bekleyen bütün olaylar (müşteri gelişi, hizmetin bitişi, bir paketin varışı) bir öncelik kuyruğunda **zamana göre** tutuluyor; döngü her seferinde **en erken** olayı çekip işliyor. Bir olayı işlemek yeni olaylar doğurabilir (bir müşteri hizmete girince onun bitiş olayı kuyruğa ekleniyor). Ağ simülatörlerinin, oyun motorlarındaki zamanlayıcıların ve donanım simülatörlerinin çekirdeği bu döngü.

Örnek: bir banka. Müşteriler ortalama dakikada bir geliyor; gişe sayısı ve hizmet süresi değişiyor. Gelişler arası süre ve hizmet süresi **üstel dağılımlı** (bağımsız rastgele olayların arasındaki sürenin doğal modeli; Ders 6.29'daki düzgün dağılımdan ters fonksiyon yöntemiyle: $-\text{ort} \cdot \ln(1 - U)$).

```c
/* Olay simulasyonu: bankada gise kuyrugu. Bekleyen olaylar zamana gore bir min-heap'te. */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum { GELIS, BITIS } Tur;
typedef struct { double zaman; Tur tur; int musteri; } Olay;

typedef struct { Olay *a; int n, kap; } OlayHeap;

static void ekle(OlayHeap *h, Olay o) {
    if (h->n == h->kap) { h->kap = h->kap ? 2 * h->kap : 64; h->a = realloc(h->a, h->kap * sizeof *h->a); }
    int i = h->n++;
    while (i > 0 && o.zaman < h->a[(i - 1) / 2].zaman) { h->a[i] = h->a[(i - 1) / 2]; i = (i - 1) / 2; }
    h->a[i] = o;                                   /* takas yerine "delik" kaydirma: yari kadar yazma */
}

static Olay cek(OlayHeap *h) {
    Olay kok = h->a[0], son = h->a[--h->n];
    int i = 0;
    for (;;) {
        int c = 2 * i + 1;
        if (c >= h->n) break;
        if (c + 1 < h->n && h->a[c + 1].zaman < h->a[c].zaman) c++;
        if (son.zaman <= h->a[c].zaman) break;
        h->a[i] = h->a[c]; i = c;
    }
    if (h->n) h->a[i] = son;
    return kok;
}
```

Bu heap elemanları struct ve ilk heap'ten bir şekilde farklı: **takas yapmıyor**. Yukarı çıkarken yeni elemanı her adımda yazmak yerine ebeveynleri bir aşağı kaydırıp bir "delik" taşıyor ve elemanı sadece en sonda, bir kez yazıyor (Ders 9.3'teki ekleme sıralamasının aynı hilesi). 24 baytlık struct'larda yazma sayısını yarıya indiriyor. (`realloc` hata kontrolü kısalık için yok. Elemanı `long` değil `Olay` olan ikinci bir heap yazmak zorunda kaldık; Ders 8.23 bunun genel çözümleri hakkında.)

```c
static double ustel(double ort) { return -ort * log(1.0 - rand() / (RAND_MAX + 1.0)); }  /* ortalama ort */

static void simule(int gise, double hizmet, int musteri_sayisi, int iz) {
    srand(2024);
    OlayHeap h = { 0 };
    double *gelis = malloc(musteri_sayisi * sizeof *gelis);
    int *sira = malloc(musteri_sayisi * sizeof *sira), bas = 0, son = 0;   /* bekleyenler: FIFO (Ders 8.5) */
    int bos = gise;
    double t = 0, toplam_bekleme = 0, en_cok = 0;
    for (int m = 0; m < musteri_sayisi; m++) {      /* gelisleri onceden uret: ortalama 1 dk arayla */
        t += ustel(1.0);
        ekle(&h, (Olay){ t, GELIS, m });
    }
    while (h.n) {
        Olay o = cek(&h);                           /* her zaman EN ERKEN olay */
        if (iz) printf("  t=%6.2f  %-5s musteri %d\n", o.zaman, o.tur == GELIS ? "gelis" : "bitis", o.musteri);
        if (o.tur == GELIS) { gelis[o.musteri] = o.zaman; sira[son++] = o.musteri; }
        else bos++;
        while (bos > 0 && bas < son) {              /* bos gise ve bekleyen varsa hizmete al */
            int m = sira[bas++];
            double bekleme = o.zaman - gelis[m];
            toplam_bekleme += bekleme;
            if (bekleme > en_cok) en_cok = bekleme;
            bos--;
            ekle(&h, (Olay){ o.zaman + ustel(hizmet), BITIS, m });  /* hizmet suresi */
        }
    }
    printf("%d gise, hizmet ort. %.1f dk: %6d musteri, ortalama bekleme %5.2f dk, en uzun %5.2f dk\n",
           gise, hizmet, musteri_sayisi, toplam_bekleme / musteri_sayisi, en_cok);
    free(h.a); free(gelis); free(sira);
}

int main(void) {
    simule(1, 0.9, 4, 1);
    simule(1, 0.9, 100000, 0);
    simule(2, 1.8, 100000, 0);
    simule(2, 0.9, 100000, 0);
    simule(1, 0.5, 100000, 0);
    return 0;
}
```

İki kuyruk var ve ikisi farklı iş görüyor: olaylar **zamana göre** bir öncelik kuyruğunda, gişe bekleyen müşteriler **geliş sırasına göre** düz bir FIFO kuyrukta (bankada kimse sırayı atlamıyor).

```
$ cc -std=c11 -O2 -Wall -Wextra -fsanitize=address,undefined sim.c -o sim -lm && ./sim
  t=  0.02  gelis musteri 0
  t=  0.28  gelis musteri 1
  t=  0.36  bitis musteri 0
  t=  0.54  bitis musteri 1
  t=  0.70  gelis musteri 2
  t=  0.93  bitis musteri 2
  t=  1.07  gelis musteri 3
  t=  1.09  bitis musteri 3
1 gise, hizmet ort. 0.9 dk:      4 musteri, ortalama bekleme  0.02 dk, en uzun  0.08 dk
1 gise, hizmet ort. 0.9 dk: 100000 musteri, ortalama bekleme  7.47 dk, en uzun 53.54 dk
2 gise, hizmet ort. 1.8 dk: 100000 musteri, ortalama bekleme  7.04 dk, en uzun 53.61 dk
2 gise, hizmet ort. 0.9 dk: 100000 musteri, ortalama bekleme  0.22 dk, en uzun  6.99 dk
1 gise, hizmet ort. 0.5 dk: 100000 musteri, ortalama bekleme  0.49 dk, en uzun  8.39 dk
```

İz satırlarında olaylar **zaman sırasıyla** çıkıyor, ama kuyruğa bu sırayla girmediler: bütün gelişler başta eklendi, bitişler sonradan, işlendikçe. Heap onları doğru sıraya koyuyor.

Kuyruk teorisi bu sistemler için kapalı formüller veriyor (M/M/1 ve M/M/c modelleri). Gişe başına doluluk oranı $\rho = \lambda / (c\mu)$ ($\lambda$: geliş hızı, $\mu$: bir gişenin hizmet hızı, $c$: gişe sayısı); tek gişede ortalama kuyruk bekleme süresi $\rho / (\mu - \lambda)$:

| Senaryo | $\rho$ | Teori (dk) | Simülasyon (dk) |
| --- | --- | --- | --- |
| 1 gişe, 0.9 dk | 0.90 | 8.10 | 7.47 |
| 2 gişe, 1.8 dk | 0.90 | 7.67 | 7.04 |
| 2 gişe, 0.9 dk | 0.45 | 0.23 | 0.22 |
| 1 gişe, 0.5 dk | 0.50 | 0.50 | 0.49 |

(İki gişeli değerler Erlang C formülünden.) Düşük dolulukta simülasyon teoriyle neredeyse aynı. $\rho = 0.9$'da sapma büyük, çünkü yoğun sistemde ardışık beklemeler birbirine çok bağlı ve 100 000 müşteri bile ortalamayı tam oturtmaya yetmiyor. Asıl ders tablonun kendisinde: doluluk %45'ten %90'a çıkınca bekleme **35 kat** artıyor. $\rho \to 1$'de bekleme sonsuza gidiyor. Sunucular, ağ bağlantıları ve CPU zamanlayıcıları için de aynı: kapasitenin %90'ında çalışan bir sistem "%10 boşta" değil, kuyruk patlamasının eşiğinde.

---

## 5. Diğer öncelik kuyrukları

| Yapı | `ekle` | `cek` | `azalt` (öncelik değiştir) | Not |
| --- | --- | --- | --- | --- |
| Sırasız dizi | $O(1)$ | $O(n)$ | $O(1)$ | Çok küçük $n$ |
| Sıralı dizi | $O(n)$ | $O(1)$ | $O(n)$ | |
| Dengeli BST (8.9) | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | Sıralı gezinme de var |
| İkili heap | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | Tek dizi, en hızlısı |
| $d$-li heap | $O(\log_d n)$ | $O(d \log_d n)$ | $O(\log_d n)$ | Alıştırma 5 |
| Fibonacci heap | $O(1)$ amortize | $O(\log n)$ amortize | $O(1)$ amortize | Teoride Dijkstra için ideal, pratikte yavaş |

`azalt` işlemi (bir elemanın önceliğini artırmak), Dijkstra'nın en kısa yol algoritmasında gerekiyor (Faz 9). İkili heap'te bunun için elemanın dizideki **yerini** bilmek gerekiyor; her eleman için konumunu tutan ikinci bir dizi ve her takasta onu güncellemek. Alternatif: eski kaydı bırakıp yenisini eklemek ve çekerken eskiyi atlamak (Ders 8.15'teki mezar taşlarına benzer bir fikir).

---

## Alıştırmalar

**1** – 1 milyon sayılık bir akıştan **en büyük** 5 sayıyı, akışın tamamını saklamadan bul. Boyutu 5 olan bir **min**-heap kullan: neden max değil de min? $a_i = (7919\,i) \bmod 1\,000\,003$, $i = 0, \dots, 999\,999$ için sonucu `qsort` ile doğrula. Maliyet ne?

**2** – Bölüm 3'teki $O(n)$ sınırının toplamını, heap'in tam ikili ağaç olduğunu varsayarak tekrar yap. `heap_kur` en kötü durumda kaç takas yapar? Ölçülen "eleman başına 2.00 karşılaştırma" bu sınırla uyumlu mu?

**3** – $k$ tane sıralı liste var, toplam $N$ eleman. Hepsini tek bir sıralı listeye $O(N \log k)$'de birleştir. Heap'te ne saklarsın?

**4** – Akan bir sayı dizisinde, her sayı geldiğinde o ana kadarki **medyanı** yazdır. İki heap kullan: alt yarı için bir max-heap, üst yarı için bir min-heap. (Elindeki min-heap'i max-heap olarak kullanmak için sayıları eksi işaretiyle sakla.) `5 15 1 3 8 7 9 10` için çıktı?

**5** – **$d$-li heap**: her düğümün $d$ çocuğu var ($dk + 1, \dots, dk + d$). Yüksekliği ne? `ekle` ve `cek` kaç karşılaştırma yapar? Ekleme ve `azalt`'ın çok, `cek`'in az olduğu bir iş yükünde (Dijkstra) neden $d = 4$ ya da $d = 8$ tercih edilir? Cache açısından ne değişir?

<details>
<summary>Cevaplar</summary>

**1** – Heap, o ana kadarki en büyük 5 sayıyı tutuyor; bunların **en küçüğü** kökte. Yeni sayı kökten küçükse en büyük 5'e giremez, atılır; büyükse kökü (5'in en küçüğünü) atıp yerine yenisini koyup aşağı indiriyoruz. Max-heap kullansaydık atılması gereken elemana (5'in en küçüğüne) hızlıca erişemezdik.

```c
    for (size_t i = 0; i < n; i++) {
        if (h.n < k) heap_ekle(&h, v[i]);
        else if (v[i] > h.a[0]) { h.a[0] = v[i]; asagi_in(&h, 0); }   /* en kucugu at, yenisini koy */
    }
```

```
en buyuk 5 (heap): 1000002 1000001 1000000 999999 999998
en buyuk 5 (qsort): 1000002 1000001 1000000 999999 999998
```

($7919 i \bmod 1\,000\,003$, $p = 1\,000\,003$ asal olduğu için $i$'nin farklı değerlerine farklı sonuç veriyor; Ders 6.18.) Maliyet $O(n \log k)$, bellek $O(k)$. $k = 5$'te bu pratikte $O(n)$: çoğu sayı kökle tek bir karşılaştırmada eleniyor. Sıralamak $O(n \log n)$ ve bütün veriyi bellekte tutmayı gerektirirdi. Unix'teki `sort | head` yerine bir arama motorunun "en alakalı 10 sonuç"u bu yöntemle buluyor.

**2** – Yüksekliği $H = \lfloor \log_2 n \rfloor$ olan bir tam ağaçta, kendi altındaki yüksekliği $k$ olan en fazla $\lceil n / 2^{k+1} \rceil$ düğüm var. Her biri en fazla $k$ takas yapıyor: toplam $\sum_{k=0}^{H} \lceil n/2^{k+1} \rceil \, k \le n \sum_{k \ge 0} k/2^{k+1} = n$. Yani en fazla yaklaşık $n$ takas. Her takas adımı 2 karşılaştırma yapıyor (iki çocuk), artı her düğüm için durmaya karar veren son karşılaştırmalar; toplam en fazla yaklaşık $2n$ karşılaştırma. Azalan girdide ölçülen tam 2.00, rastgele girdide 1.88: sınırla uyumlu, ve sınır neredeyse sıkı.

**3** – Heap'te her listenin **şu anki** ilk elemanını, hangi listeden geldiği bilgisiyle sakla (`{deger, liste_no}`; Bölüm 4'teki `Olay` gibi bir struct). En küçüğü çek, çıktıya yaz, aynı listenin bir sonraki elemanını ekle. Heap hiçbir zaman $k$'dan büyük değil, her eleman bir kez ekleniyor ve bir kez çekiliyor: $O(N \log k)$. Bu, belleğe sığmayan veriyi sıralayan **dış sıralamanın** (external sort) ikinci aşaması: veri belleğe sığan parçalara bölünüp her biri sıralanıyor ve diske yazılıyor, sonra $k$ parça bu yöntemle birleştiriliyor (Ders 9.4).

**4** –

```c
        if (alt.n == 0 || y <= -alt.a[0]) heap_ekle(&alt, -y); else heap_ekle(&ust, y);
        if (alt.n > ust.n + 1) { heap_cek(&alt, &x); heap_ekle(&ust, -x); }
        else if (ust.n > alt.n) { heap_cek(&ust, &x); heap_ekle(&alt, -x); }
        if (alt.n > ust.n) printf(" %ld", -alt.a[0]);
        else printf(" %.1f", (-alt.a[0] + ust.a[0]) / 2.0);
```

```
medyanlar: 5 10.0 5 4.0 5 6.0 7 7.5
```

Değişmez: alt yarının bütün elemanları üst yarınınkilerden küçük ya da eşit, ve alt yarı ya üst yarıyla eşit ya da bir fazla elemanlı. O zaman medyan ya alt yarının en büyüğü (kökü) ya da iki kökün ortalaması. Her sayı için $O(\log n)$. (Eksi işareti hilesi `LONG_MIN`'de taşar; Ders 3.8. Gerçek kodda karşılaştırma fonksiyonu alan bir heap yazılır.)

**5** – Yükseklik $\log_d n$. `ekle` (yukarı çıkarma) seviye başına bir karşılaştırma: $\log_d n$. `cek` (aşağı indirme) seviye başına $d$ çocuğun en küçüğünü bulmak için $d$ karşılaştırma: $d \log_d n$. $d$ büyüdükçe ekleme ve `azalt` ucuzlıyor, çekme pahalılaşıyor. Dijkstra'da `azalt` sayısı kenar sayısı ($E$), `cek` sayısı düğüm sayısı ($V$); yoğun graflarda $E \gg V$ olduğu için büyük $d$ kazandırıyor. Cache açısından: $d$ çocuk dizide **yan yana** (`dk + 1 .. dk + d`); $d = 8$ ve 8 baytlık elemanlarla bir düğümün çocukları tam bir 64 baytlık cache satırı. Aşağı inerken her seviye tek bir cache satırı okuyor ve seviye sayısı ikili heap'in üçte biri. Ders 8.11'deki B-ağacının mantığının heap'e uygulanması.

</details>

---

## Kaynaklar

- J. W. J. Williams, "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), 1964: ikili heap ve heapsort.
- Robert Floyd, "Algorithm 245: Treesort 3", *Communications of the ACM* 7(12), 1964: $O(n)$ heap kurma.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 6: heap'ler ve öncelik kuyrukları.
- Leonard Kleinrock, *Queueing Systems, Volume 1: Theory*, 1975: M/M/1 ve M/M/c modelleri.
- Linux çekirdeği, `include/linux/min_heap.h`: genel amaçlı dizi tabanlı min-heap.

**Sıradaki ders:** Hash fonksiyonları. Bölme, çarpma (Knuth), FNV-1a ve iyi bir hash'in özellikleri.
