---
title: "9.6 Heapsort ve sıralama alt sınırı"
description: "Ders 8.12'deki heap'i dizinin kendi içinde kurup sıralamak: O(n) heap kurulumu, kökü sona alıp kalanı düzeltmek, ek bellek yok ve en kötü durumda O(n log n); 16 milyon int'te heapsort 2.05 s, birleştirme 0.85 s, hızlı sıralama 1.18 s, ve sebebi cache; 100 bin elemanda ise en hızlısı; karar ağacı modeli ve karşılaştırmayla sıralayan her algoritmanın en kötü durumda en az ⌈log₂ n!⌉ ≈ n log₂ n − 1.44n karşılaştırma yapması gerektiğinin ispatı; Stirling, küçük n için tablo ve birleştirmeli sıralamayla fark; ortalama durum için de aynı sınır."
---

Şimdiye kadar iki $O(n \log n)$ sıralama gördük, ve ikisinin de bir eksiği vardı. Birleştirmeli sıralama (Ders 9.4) en kötü durumda $O(n \log n)$ ama $n$ elemanlık ek bellek istiyor. Hızlı sıralama (Ders 9.5) yerinde ama en kötü durumda $\Theta(n^2)$. **Heapsort** (J. W. J. Williams, 1964) ikisini birden veriyor: **yerinde** ve **en kötü durumda** $O(n \log n)$. Ders 9.5'teki introsort'un yedek planı bu yüzden heapsort.

Dersin ikinci yarısı tersine bir soru soruyor: $O(n \log n)$'den daha iyisi mümkün mü? Cevap, karşılaştırmayla çalışan algoritmalar için **hayır**, ve ispatı bilgisayar biliminin en zarif alt sınır argümanlarından biri.

---

## 1. Heapsort

Ders 8.12'de bir **min**-heap'i dizi üzerinde kurduk ve art arda en küçüğü çekmenin elemanları sıralı verdiğini gördük. Ama orada çekilen elemanlar ayrı bir yere yazılıyordu. Heapsort aynı işi tek dizide yapıyor; hile **max**-heap kullanmak:

1. Diziyi yerinde bir max-heap'e çevir (Ders 8.12'deki Floyd yöntemi, $O(n)$).
2. Kök, en büyük eleman. Onu dizinin **son** elemanıyla takasla; artık en büyük eleman son yerinde. Heap bir eleman küçüldü, ve köke gelen eleman heap özelliğini bozuyor: aşağı indir.
3. Heap tek elemana inene kadar tekrarla.

Dizinin sağ tarafı, sıralı en büyükler bölgesi olarak büyüyor; sol tarafı küçülen bir heap.

```c
/* Yerinde heapsort: once max-heap kur (Floyd, O(n)), sonra kokteki en buyugu sona al, kalan heap'i duzelt */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long kars;

/* a[0..n) bir max-heap; i'deki eleman asagi inerek yerine otursun (Ders 8.12'nin max hali, delik teknigi) */
static void asagi_in(int *a, size_t n, size_t i) {
    int x = a[i];
    for (;;) {
        size_t c = 2 * i + 1;
        if (c >= n) break;
        if (c + 1 < n) { kars++; if (a[c + 1] > a[c]) c++; }     /* buyuk cocuk */
        kars++;
        if (a[c] <= x) break;
        a[i] = a[c]; i = c;                                        /* cocugu yukari al, delik asagi */
    }
    a[i] = x;
}

static void heap_sirala(int *a, size_t n) {
    for (size_t i = n / 2; i-- > 0; ) asagi_in(a, n, i);          /* 1) heap kur: O(n) */
    for (size_t son = n; son > 1; son--) {                        /* 2) DEGISMEZ: a[0..son) heap, a[son..n) en buyukler, sirali */
        int t = a[0]; a[0] = a[son - 1]; a[son - 1] = t;          /* en buyugu sona */
        asagi_in(a, son - 1, 0);
    }
}
```

(Fonksiyonun adı `heapsort` değil `heap_sirala`, çünkü macOS'un `stdlib.h`'sinde BSD libc'nin `int heapsort(void *, size_t, size_t, int (*)(const void *, const void *))` fonksiyonu zaten bildirilmiş ve aynı adla bir `static` fonksiyon derleme hatası veriyor. Standart C'de olmayan bir isim, ama sistem başlıklarında var: kendi fonksiyonlarına kütüphanelerinkine benzeyen isimler verirken dikkatli olmanın bir sebebi daha.)

Değişmez: her turun başında $a[0..son)$ bir max-heap ve $a[son..n)$ dizinin en büyük $n - son$ elemanını sıralı tutuyor. Takas, heap'in en büyüğünü (sağ bölgedeki her şeyden küçük ya da eşit, çünkü onlar daha önce çıkarılan en büyüklerdi) sağ bölgenin başına koyuyor.

Maliyet: heap kurma $O(n)$, sonra $n - 1$ kez aşağı indirme, her biri $O(\log n)$. Toplam $O(n \log n)$, **her** girdide; heap'in şekli her zaman tam bir ağaç ve yüksekliği her zaman $\lfloor \log_2 n \rfloor$ (Ders 8.12). Kötü girdi yok.

Kararlı değil: kökü sona takaslamak, eşit elemanları uzak mesafeden yer değiştiriyor (Ders 9.3'teki seçme sıralaması gibi; heapsort aslında en büyüğü bulmak için heap kullanan bir seçme sıralaması).

### Ölçüm

```
$ cc -std=c11 -O2 -Wall -Wextra heap.c -o heap -lm && ./heap
ornek: 1 3 4 5 7 8 10 
n=100000  log2(n!) = 1516704  (n log2 n = 1660964)
  heapsort    0.003 s  3019404 karsilastirma (1.99 x log2 n!)
  birlestirme 0.004 s
  hizli       0.005 s
n=16000000  log2(n!) = 359821990  (n log2 n = 382905097)
  heapsort    2.049 s  716698243 karsilastirma (1.99 x log2 n!)
  birlestirme 0.852 s
  hizli       1.176 s
```

(Birleştirme, Ders 9.4'ün eşikli sürümü; hızlı, Ders 9.5'in rastgele pivotlu Lomuto'su. Sanitizer'lı derleme temiz.)

- **Karşılaştırma**: heapsort, alt sınırın (Bölüm 2) yaklaşık **2 katı** karşılaştırma yapıyor: aşağı indirmenin her adımında iki karşılaştırma (iki çocuktan büyüğü, sonra o çocuk ile inen eleman). Birleştirmeli sıralama $0.94\, n \log_2 n$ civarındaydı.
- **100 bin elemanda** (400 KB, cache'e sığıyor) heapsort üçünün en hızlısı.
- **16 milyonda** (64 MB) heapsort birleştirmeden 2.4 kat yavaş. Sebebi bellek erişimi: aşağı indirme kökten başlayıp her adımda indeksi **ikiye katlıyor**; `i`'den `2i + 1`'e atlamak, büyük bir heap'te her seviyede farklı bir cache satırına, alt seviyelerde farklı bir sayfaya gitmek demek. Birleştirmeli ve hızlı sıralama ise diziyi ardışık tarıyor (Ders 7.24). Heapsort'un asimptotik garantisi, büyük dizilerde cache dostu olmamasıyla ödeniyor; bu yüzden pratikte "sigorta" olarak (introsort) ya da bellek kısıtlı gömülü sistemlerde (Linux çekirdeğinin `lib/sort.c`'si heapsort) kullanılıyor.

---

## 2. Alt sınır: karar ağacı

Ders 9.3–9.6'daki bütün sıralamalar elemanlar hakkında bilgiyi tek bir yoldan alıyor: iki elemanı **karşılaştırarak** (`a[i] < a[j]` mi?). Elemanların değerlerine başka hiçbir şekilde bakmıyorlar: onları toplamıyor, bitlerine bakmıyor, indeks olarak kullanmıyorlar. Böyle algoritmalara **karşılaştırma tabanlı** sıralama denir.

Karşılaştırma tabanlı bir algoritmanın $n$ elemanlık bir girdi üzerindeki bütün olası çalışmaları bir **karar ağacı** olarak çizilebilir: her iç düğüm bir karşılaştırma, iki çocuğu iki olası sonuç, her yaprak bir **cevap** (girdinin hangi permütasyonunun sıralı olduğu). Üç eleman için (ekleme sıralamasının ağacı):

```
                         a < b ?
                    evet /      \ hayır
                 b < c ?          a < c ?
               /       \         /       \
          [a b c]    a < c ?   [b a c]   b < c ?
                    /     \              /     \
               [a c b]  [c a b]     [b c a]  [c b a]
```

Algoritma bir girdi üzerinde çalışırken kökten bir yaprağa bir yol izliyor; yaptığı karşılaştırma sayısı o yolun uzunluğu. **En kötü durum**, ağacın **yüksekliği**.

**Teorem**: $n$ elemanı sıralayan her karşılaştırma tabanlı algoritma, en kötü durumda en az $\lceil \log_2 n! \rceil$ karşılaştırma yapar.

**İspat**: $n$ farklı elemanın $n!$ farklı sırası var, ve her biri farklı bir çıktı gerektiriyor (farklı bir permütasyon uygulanmalı). Dolayısıyla karar ağacının en az $n!$ **farklı yaprağı** olmalı; aksi halde iki farklı girdi aynı yaprağa düşer, algoritma ikisine aynı permütasyonu uygular ve en az birini yanlış sıralar. Yüksekliği $h$ olan bir ikili ağacın en fazla $2^h$ yaprağı var (Ders 8.7, Alıştırma 3). O halde $2^h \ge n!$, yani $h \ge \log_2 n!$. $\blacksquare$

$\log_2 n!$'nin büyüklüğü Stirling yaklaşımından ($n! \approx \sqrt{2\pi n}\,(n/e)^n$):

$$
\log_2 n! = n \log_2 n - n \log_2 e + O(\log n) \approx n \log_2 n - 1.443\, n.
$$

Yani $\Omega(n \log n)$. Birleştirmeli sıralama ve heapsort **asimptotik olarak optimal**: karşılaştırma tabanlı hiçbir algoritma onlardan asimptotik olarak daha hızlı olamaz. Sabitlerde fark var: 16 milyon eleman için alt sınır 359.8 milyon karşılaştırma; birleştirmeli sıralama 362.8 milyon yaptı (Ders 9.4), sınırın sadece %0.8 üstünde; heapsort iki katı.

Küçük $n$ için:

| $n$ | $n!$ | $\lceil \log_2 n! \rceil$ | Birleştirmeli sıralama, en kötü |
| --- | --- | --- | --- |
| 3 | 6 | 3 | 3 |
| 4 | 24 | 5 | 5 |
| 5 | 120 | 7 | 8 |
| 6 | 720 | 10 | 11 |
| 8 | 40 320 | 16 | 17 |
| 10 | 3 628 800 | 22 | 25 |
| 12 | 479 001 600 | 29 | 33 |

$n = 5$'te 7 karşılaştırmayla sıralamak mümkün mü? Evet: Ford ve Johnson'un **birleştirmeli ekleme** (merge insertion) algoritması $n \le 11$ için tam alt sınıra ulaşıyor. $n = 12$'de alt sınır 29, ama 1965'te bilgisayarla yapılan kapsamlı bir aramayla 30'un gerçekten gerekli olduğu gösterildi: alt sınır her zaman ulaşılabilir değil. Hangi $n$ için tam optimumun ne olduğu hâlâ kısmen açık bir problem.

### Ortalama durum

Sınır ortalama durum için de geçerli: $n!$ yapraklı bir ikili ağaçta yaprakların **ortalama** derinliği de en az $\log_2 n!$ (en dengeli ağaçta bile; Alıştırma 3). Yani rastgele girdide bile, hiçbir karşılaştırma tabanlı algoritma ortalamada $\log_2 n! \approx n \log_2 n - 1.44 n$'den az karşılaştırma yapamaz. Rastgele pivotlu hızlı sıralamanın $1.39\, n \log_2 n$'i bu sınırın %39 üstünde.

### Sınırın dışına çıkmak

İspat sadece **karşılaştırma** yapan algoritmalar için. Elemanların değerlerini başka bir şekilde kullanan algoritmalar bu sınıra tabi değil. Tamsayıları dizi indeksi olarak kullanan sayma sıralaması ya da bitlerine bakan radix sıralama, belirli koşullarda $O(n)$'de sıralıyor: Ders 9.7. Bu bir çelişki değil; sadece farklı bir hesaplama modeli. Benzer şekilde Ders 8.14'teki hash tablosu, karşılaştırma tabanlı aramanın $\Omega(\log n)$ sınırını (aynı karar ağacı argümanı: $n + 1$ olası cevap) hash'leyerek aşıyordu.

---

## Alıştırmalar

**1** – `[4 10 3 5 1 8 7]` dizisinde Floyd yöntemiyle max-heap kurulduktan sonra dizi ne olur? İlk iki "kökü sona al" adımından sonra?

**2** – Heapsort'un aşağı indirmesinde iki karşılaştırma yapılıyordu. **Aşağıdan yukarı heapsort** (Wegener, 1993): kökteki deliği, hiç inen elemanla karşılaştırmadan büyük çocuklar yolu boyunca **yaprağa kadar** indir (her seviyede tek karşılaştırma), sonra inen elemanı o yaprağa koyup yukarı çıkar. Neden karşılaştırma sayısı yaklaşık yarıya iner?

**3** – Karar ağacı argümanının ortalama durum hali: $L$ yapraklı bir ikili ağaçta yaprakların ortalama derinliği en az $\log_2 L$. İpucu: en küçük toplam derinlik dengeli ağaçta; ya da Kraft eşitsizliği $\sum 2^{-d_i} \le 1$ ve Jensen.

**4** – Sıralı bir dizide ikili aramanın (Ders 9.2) en kötü durumda en az $\lceil \log_2(n+1) \rceil$ karşılaştırma gerektirdiğini karar ağacıyla göster. Hash tablosu bu sınırı nasıl aşıyor?

**5** – $n$ elemanın **en büyüğünü** bulmak için en az kaç karşılaştırma gerekir? Karar ağacı argümanı burada neden zayıf bir sınır veriyor ($\log_2 n$), ve doğru sınır ($n - 1$) hangi argümanla ispatlanıyor?

<details>
<summary>Cevaplar</summary>

**1** – Floyd yöntemi son iç düğümden ($i = 2$) köke doğru aşağı indiriyor. $i = 2$: 3'ün çocukları 8, 7; 8 büyük, yer değiştir: `[4 10 8 5 1 3 7]`. $i = 1$: 10'un çocukları 5, 1; 10 büyük, değişiklik yok. $i = 0$: 4'ün çocukları 10, 8; 10 yukarı, 4 indeks 1'e; çocukları 5, 1; 5 büyük, 5 yukarı, 4 indeks 3'e: `[10 5 8 4 1 3 7]`. Max-heap. Birinci adım: 10 ile son eleman 7 takas, `[7 5 8 4 1 3 | 10]`; 7 aşağı: çocukları 5, 8; 8 yukarı: `[8 5 7 4 1 3 | 10]`. İkinci adım: 8 ile 3 takas, `[3 5 7 4 1 | 8 10]`; 3 aşağı: 7 yukarı (çocuğu yok): `[7 5 3 4 1 | 8 10]`. Sağ bölge en büyükleri sıralı biriktiriyor.

**2** – Köke takaslanan eleman dizinin **son** elemanıydı, yani heap'in en altından geliyor ve büyük ihtimalle küçük: sonunda yine en alta yakın bir yere inecek. Standart aşağı indirme her seviyede "inen eleman bu çocuktan büyük mü?" diye soruyor ve cevap neredeyse her zaman "hayır". Aşağıdan yukarı sürüm bu soruyu sormadan, sadece iki çocuğu karşılaştırarak yaprağa kadar iniyor (seviye başına 1 karşılaştırma, toplam $\log_2 n$), sonra elemanın gerçek yerini yapraktan yukarı doğru arıyor; bu genelde 1–2 adım. Toplam yaklaşık $\log_2 n + O(1)$ yerine $2 \log_2 n$: heapsort'u $n \log_2 n + O(n)$ karşılaştırmaya, yani alt sınıra yakın bir yere indiriyor. Cache sorunu ise aynı kalıyor.

**3** – Derinlikleri $d_1, \dots, d_L$ olan yapraklar için Kraft eşitsizliği $\sum_i 2^{-d_i} \le 1$ (bir ikili ağaçta bir yaprak, köke giden yol üzerindeki seçimlerin bir "kodu"; Ders 9.10'daki Huffman kodlarıyla aynı yapı). Ortalama derinlik $\bar d = \frac1L \sum d_i$. $2^{-x}$ dışbükey olduğu için Jensen: $2^{-\bar d} \le \frac1L \sum 2^{-d_i} \le \frac1L$, yani $\bar d \ge \log_2 L$. $L = n!$ için ortalama karşılaştırma sayısı en az $\log_2 n!$.

**4** – $n$ elemanlık sıralı bir dizide arama $n + 1$ farklı cevaptan birini vermeli: $x$ elemanlardan birine eşit ($n$ cevap) ya da yok, ve "yok" durumunda ekleme yeri $n + 1$ aralıktan biri. Sadece "eklenecek yer" sorusu için bile $n + 1$ yaprak gerekiyor, dolayısıyla yükseklik $\ge \lceil \log_2(n+1) \rceil$. İkili arama tam bu sayıyı yapıyor: optimal. Hash tablosu karşılaştırma yapmıyor: anahtarın kendisinden bir **adres** hesaplıyor ve oraya gidiyor. Bu, bir karşılaştırmanın verdiği 1 bitlik bilgi yerine tek adımda $\log_2 m$ bitlik bilgi (kova numarası) kullanmak demek. Bedeli, sıralı sorguları (önceki, sonraki, aralık) kaybetmek.

**5** – Karar ağacı argümanı: $n$ olası cevap (hangi eleman en büyük), yükseklik $\ge \log_2 n$. Ama gerçek cevap $n - 1$, çok daha büyük. Doğru argüman bir **düşman** (adversary) argümanı: en büyük olmayan her eleman, en az bir karşılaştırmayı **kaybetmiş** olmalı (aksi halde algoritma onun en büyük olmadığını bilemez). Her karşılaştırma en fazla bir kaybeden üretiyor, ve $n - 1$ eleman kaybetmeli: en az $n - 1$ karşılaştırma. Karar ağacı argümanı sadece cevap sayısını sayıyor; ama farklı yolların aynı yaprağa çıkabildiği durumlarda (en büyüğü bulmak için çok sayıda farklı karşılaştırma sırası aynı cevabı veriyor) sınır gevşek kalıyor. Sıralama için ise iki argüman aynı sınıra varıyor.

</details>

---

## Kaynaklar

- J. W. J. Williams, "Algorithm 232: Heapsort", *Communications of the ACM* 7(6), 1964.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 6 (heapsort) ve 8.1 (karşılaştırmalı sıralamanın alt sınırı).
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 5.3.1: minimum karşılaştırmalı sıralama, Ford–Johnson algoritması ve $n = 12$ için 30.
- Lester Ford ve Selmer Johnson, "A Tournament Problem", *The American Mathematical Monthly* 66(5), 1959.
- Ingo Wegener, "Bottom-up-heapsort, a new variant of heapsort beating, on an average, quicksort (if n is not very small)", *Theoretical Computer Science* 118(1), 1993.

**Sıradaki ders:** Doğrusal zamanlı sıralama. Sayma, radix ve kova (bucket) sıralaması.
