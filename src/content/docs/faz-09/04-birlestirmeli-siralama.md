---
title: "9.4 Birleştirmeli sıralama"
description: "Böl-yönet: diziyi ikiye böl, iki yarıyı özyinelemeyle sırala, sıralı iki yarıyı doğrusal zamanda birleştir; yardımcı dizi ve kararlılığın tek bir < işaretine bağlı olması; T(n) = 2T(n/2) + n bağıntısının Master teoremi ve özyineleme ağacıyla Θ(n log n) çözümü; aşağıdan yukarı, özyinelemesiz sürüm; küçük parçalarda ekleme sıralaması ve 'zaten sıralı mı' kontrolü; 16 milyon int'te 0.81 s (libc qsort 1.64 s), karşılaştırma sayısının 0.94·n log₂ n olması, sıralı girdide 0.014 s; birleştirme sırasında ters çift saymak."
---

Ders 9.3'teki sıralamaların hepsi $\Theta(n^2)$'ydi: her elemanı, kabaca, diğer her elemanla karşılaştırıyorlardı. **Böl-yönet** (divide and conquer) bu duvarı aşan ilk teknik: problemi küçük parçalara böl, parçaları özyinelemeyle çöz, çözümleri birleştir. **Birleştirmeli sıralama** (merge sort; John von Neumann, 1945) bu tekniğin en saf örneği, ve sıralama algoritmaları arasında birçok "en"in sahibi: en kötü durumda bile $O(n \log n)$, kararlı, analizi en temiz, ve bağlı listelerde ve diskteki dosyalarda (Ders 8.12'deki dış sıralama) doğal seçim.

---

## 1. Fikir

- **Böl**: diziyi ortadan ikiye ayır.
- **Yönet**: iki yarıyı ayrı ayrı (özyinelemeyle) sırala. Tek elemanlı bir dizi zaten sıralı: taban durumu.
- **Birleştir**: iki **sıralı** yarıyı tek bir sıralı dizide birleştir.

İşin hepsi üçüncü adımda, ve o adım kolay: iki sıralı dizinin en küçük elemanı, iki dizinin **ilk** elemanlarından biri. Onu al, çıkar, tekrarla. İki sıralı iskambil destesini birleştiren biri, iki destenin üstündeki kartlardan küçüğünü alıp yeni desteye koyar. Her adımda bir eleman yerleşiyor ve bir karşılaştırma yapılıyor: $n$ elemanı birleştirmek en fazla $n - 1$ karşılaştırma.

---

## 2. Kod

```c
/* Birlestirmeli siralama: yukaridan asagi (ozyinelemeli), asagidan yukari (dongu), kesme esikli */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long kars;

/* a[lo..orta) ve a[orta..hi) sirali; ikisini yardimci diziden geri a'ya birlestir */
static void birlestir(int *a, int *y, size_t lo, size_t orta, size_t hi) {
    memcpy(y + lo, a + lo, (hi - lo) * sizeof *a);
    size_t i = lo, j = orta, k = lo;
    while (i < orta && j < hi) {
        kars++;
        if (y[j] < y[i]) a[k++] = y[j++];      /* esitse SOLDAKI once: kararlilik */
        else             a[k++] = y[i++];
    }
    while (i < orta) a[k++] = y[i++];           /* kalanlar */
    while (j < hi)   a[k++] = y[j++];
}

static void yukaridan(int *a, int *y, size_t lo, size_t hi) {    /* [lo, hi) */
    if (hi - lo < 2) return;
    size_t orta = lo + (hi - lo) / 2;
    yukaridan(a, y, lo, orta);
    yukaridan(a, y, orta, hi);
    birlestir(a, y, lo, orta, hi);
}

static void asagidan(int *a, int *y, size_t n) {                 /* genislik 1, 2, 4, ... */
    for (size_t g = 1; g < n; g *= 2)
        for (size_t lo = 0; lo + g < n; lo += 2 * g)
            birlestir(a, y, lo, lo + g, lo + 2 * g < n ? lo + 2 * g : n);
}

static void ekleme(int *a, size_t lo, size_t hi) {
    for (size_t i = lo + 1; i < hi; i++) { int x = a[i]; size_t j = i; while (j > lo && x < a[j - 1]) { kars++; a[j] = a[j - 1]; j--; } if (j > lo) kars++; a[j] = x; }
}

static void esikli(int *a, int *y, size_t lo, size_t hi) {       /* kucuk parcalarda ekleme; zaten siraliysa birlestirme yok */
    if (hi - lo <= 24) { ekleme(a, lo, hi); return; }
    size_t orta = lo + (hi - lo) / 2;
    esikli(a, y, lo, orta);
    esikli(a, y, orta, hi);
    if (a[orta - 1] <= a[orta]) return;         /* iki yari zaten sirali birlesik */
    birlestir(a, y, lo, orta, hi);
}

static int kars_fn(const void *x, const void *y) { int p = *(const int *)x, q = *(const int *)y; return (p > q) - (p < q); }
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

int main(void) {
    int ornek[] = { 38, 27, 43, 3, 9, 82, 10 }, y0[7];
    size_t n0 = 7;
    yukaridan(ornek, y0, 0, n0);
    printf("ornek: "); for (size_t i = 0; i < n0; i++) printf("%d ", ornek[i]); printf("\n");

    for (size_t n = 1000000; n <= 16000000; n *= 4) {
        int *a = malloc(n * sizeof *a), *o = malloc(n * sizeof *a), *y = malloc(n * sizeof *a);
        srand(3); for (size_t i = 0; i < n; i++) o[i] = rand();
        const char *ad[] = { "yukaridan", "asagidan", "esikli", "qsort" };
        printf("n=%zu  (n log2 n = %.0f)\n", n, n * log2((double)n));
        for (int k = 0; k < 4; k++) {
            memcpy(a, o, n * sizeof *a); kars = 0;
            double t0 = simdi();
            if (k == 0) yukaridan(a, y, 0, n); else if (k == 1) asagidan(a, y, n); else if (k == 2) esikli(a, y, 0, n); else qsort(a, n, sizeof *a, kars_fn);
            double t = simdi() - t0;
            for (size_t i = 1; i < n; i++) if (a[i - 1] > a[i]) { puts("SIRASIZ"); return 1; }
            if (k < 3) printf("  %-10s %.3f s  %ld karsilastirma (%.3f n log2 n)\n", ad[k], t, kars, kars / (n * log2((double)n)));
            else       printf("  %-10s %.3f s\n", ad[k], t);
        }
        /* zaten sirali girdi */
        for (size_t i = 0; i < n; i++) a[i] = (int)i;
        kars = 0; double t0 = simdi(); esikli(a, y, 0, n);
        printf("  sirali girdi, esikli: %.4f s  %ld karsilastirma\n", simdi() - t0, kars);
        free(a); free(o); free(y);
    }
}
```

### Birleştirme

`birlestir`, iki yarıyı önce yardımcı diziye (`y`) kopyalıyor, sonra oradan geri `a`'ya birleştiriyor. Yerinde birleştirme (ek dizi olmadan) mümkün ama çok daha karmaşık ve yavaş; birleştirmeli sıralamanın bedeli $n$ elemanlık ek bellek. Değişmez: her adımda $a[lo..k)$, iki yarının **en küçük** $k - lo$ elemanını sıralı olarak içeriyor, ve bunlar tam olarak $y[lo..i)$ ile $y[orta..j)$.

**Kararlılık** tek bir karaktere bağlı: `if (y[j] < y[i])`. Eşitlikte **soldaki** (orijinalde önce gelen) eleman alınıyor. `<=` yazsaydık eşitlerin sırası tersine dönerdi; sıralama yine doğru olurdu ama kararsız (Ders 9.3, Bölüm 2).

### Özyinelemeli (yukarıdan aşağı)

`yukaridan`, yarı açık aralığı (Ders 9.2) ikiye bölüyor. Orta nokta yine `lo + (hi - lo) / 2`: Ders 9.2'deki Bloch makalesinin başlığı "Neredeyse bütün ikili aramalar **ve birleştirmeli sıralamalar** bozuk" idi; aynı `(lo + hi) / 2` hatası Java'nın birleştirmeli sıralamasında da vardı.

Yedi elemanlı bir örnekte birleştirmelerin sırası (girinti özyineleme derinliği):

```
    birlestir [27 43]
  birlestir [27 38 43]
    birlestir [3 9]
    birlestir [10 82]
  birlestir [3 9 10 82]
birlestir [3 9 10 27 38 43 82]
```

`[38 27 43 3 9 82 10]` önce `[38 27 43]` ve `[3 9 82 10]` diye ikiye ayrılıyor; sol yarı tekrar `[38]` ve `[27 43]`'e... Tek elemanlılar birleştirme gerektirmediği için listede görünmüyor. En üstte son birleştirme iki sıralı yarıyı bütün diziye çeviriyor.

Özyineleme derinliği $\lceil \log_2 n \rceil$: 16 milyon elemanda 24 çerçeve; Ders 8.6'daki yığın taşması endişesi burada yok.

---

## 3. Analiz

$T(n)$, $n$ elemanı sıralamanın maliyeti olsun. İki yarıyı sıralamak $2T(n/2)$, birleştirmek $\Theta(n)$:

$$
T(n) = 2T(n/2) + \Theta(n), \qquad T(1) = \Theta(1).
$$

**Master teoremi** (Ders 6.13): $T(n) = aT(n/b) + f(n)$ biçiminde $a = 2$, $b = 2$, $f(n) = \Theta(n)$. $n^{\log_b a} = n^{\log_2 2} = n$, ve $f(n) = \Theta(n^{\log_b a})$: ikinci durum, $T(n) = \Theta(n \log n)$.

Aynı sonucu **özyineleme ağacı** sezgisiyle de görmek kolay:

```
 seviye 0:            n                  toplam iş: n
 seviye 1:       n/2     n/2             toplam iş: n
 seviye 2:    n/4  n/4  n/4  n/4         toplam iş: n
   ...
 seviye log n:  1 1 1 ... 1 1 1           toplam iş: n
```

Her seviyede parçaların toplam boyutu $n$, ve her seviye toplam $\Theta(n)$ birleştirme işi yapıyor. $\log_2 n$ seviye: $\Theta(n \log n)$. Bu analiz **girdiden bağımsız**: en iyi, ortalama ve en kötü durum hepsi $\Theta(n \log n)$. Hızlı sıralamanın (Ders 9.5) aksine, birleştirmeli sıralamanın kötü bir girdisi yok.

Karşılaştırma sayısının kesin hali: en kötü durumda $n \lceil \log_2 n \rceil - 2^{\lceil \log_2 n \rceil} + 1$, yani $n \log_2 n$'den biraz az (Alıştırma 3). Ders 9.6'da göreceğiz: karşılaştırmayla sıralayan **hiçbir** algoritma en kötü durumda $\log_2 n! \approx n \log_2 n - 1.44 n$'den az karşılaştırma yapamaz. Birleştirmeli sıralama bu alt sınıra çok yakın.

### Aşağıdan yukarı

Özyineleme şart değil. Ağacın yapraklarından başlayıp yukarı doğru gidebiliriz: önce bütün komşu tek elemanlıları ikili olarak birleştir (genişlik 1), sonra ikilileri dörtlü (genişlik 2), dörtlüleri sekizli... `asagidan` bunu iki iç içe döngüyle yapıyor. Son parça kısa olabilir (`lo + 2 * g < n ? ... : n`). Özyineleme yok, yığın kullanımı yok; bağlı listelerde ve paralel uygulamalarda (her genişlikteki birleştirmeler birbirinden bağımsız) tercih ediliyor.

---

## 4. Ölçüm ve iyileştirmeler

İki pratik iyileştirme (`esikli`):

- **Küçük parçalarda ekleme sıralaması.** 24 elemandan küçük parçalarda özyineleme ve birleştirmenin sabit maliyeti, ekleme sıralamasının karesel maliyetinden büyük (Ders 9.3'te ekleme sıralaması küçük $n$'de hızlıydı). Ağacın son birkaç seviyesi yok oluyor.
- **Zaten sıralı mı?** İki yarı sıralandıktan sonra, sol yarının sonu sağ yarının başından küçük ya da eşitse iki yarı zaten **birleşik** sıralı; birleştirmeye gerek yok. Tek karşılaştırma. Sıralı ya da neredeyse sıralı girdide çok büyük kazanç.

Rastgele `int`'ler, libc `qsort` ile karşılaştırmalı (sanitizer'lı derleme de sıralı ve temiz):

```
$ cc -std=c11 -O2 -Wall -Wextra birlestir.c -o birlestir -lm && ./birlestir
ornek: 3 9 10 27 38 43 82 
n=1000000  (n log2 n = 19931569)
  yukaridan  0.050 s  18674444 karsilastirma (0.937 n log2 n)
  asagidan   0.050 s  18716236 karsilastirma (0.939 n log2 n)
  esikli     0.042 s  20223304 karsilastirma (1.015 n log2 n)
  qsort      0.086 s
  sirali girdi, esikli: 0.0009 s  934464 karsilastirma
n=4000000  (n log2 n = 87726274)
  yukaridan  0.216 s  82695763 karsilastirma (0.943 n log2 n)
  asagidan   0.216 s  82863400 karsilastirma (0.945 n log2 n)
  esikli     0.186 s  88887002 karsilastirma (1.013 n log2 n)
  qsort      0.377 s
  sirali girdi, esikli: 0.0036 s  3737856 karsilastirma
n=16000000  (n log2 n = 382905097)
  yukaridan  0.942 s  362787150 karsilastirma (0.947 n log2 n)
  asagidan   0.935 s  363454331 karsilastirma (0.949 n log2 n)
  esikli     0.814 s  387579264 karsilastirma (1.012 n log2 n)
  qsort      1.636 s
  sirali girdi, esikli: 0.0143 s  14951424 karsilastirma
```

- **Karşılaştırma sayısı** $0.94\, n \log_2 n$ civarında: rastgele girdide birleştirmeler bir yarı tükenince erken bitiyor ve en kötü durumdan biraz az karşılaştırma yapılıyor. $n$ 4 katına çıkınca süre 4.3 kat: $n \log n$'in ikiye katlama tablosundaki imzası (Ders 9.1, Alıştırma 5).
- **Yukarıdan ve aşağıdan** sürümler aynı hızda: özyinelemenin maliyeti, işin yanında ihmal edilebilir.
- **Eşikli sürüm** %13–15 hızlı, ama **daha fazla** karşılaştırma yapıyor ($1.01\, n \log_2 n$): küçük parçalardaki ekleme sıralaması karşılaştırmada daha savurgan ama bellek yazması ve fonksiyon çağrısı olarak çok daha ucuz. Karşılaştırma sayısı her zaman süreyi belirlemiyor.
- **libc `qsort`'tan 2 kat hızlı**: Ders 8.23'te gördüğümüz gibi `qsort` her karşılaştırma için bir fonksiyon çağırıyor; buradaki kod `int`'e özel ve karşılaştırma inline.
- **Sıralı girdide** eşikli sürüm 16 milyon elemanı 0.014 s'de "sıralıyor": her birleştirme tek karşılaştırmayla atlanıyor, kalan iş sadece en alttaki ekleme sıralamaları ($n$ karşılaştırma civarı).

Bu son iyileştirmenin genelleştirilmiş hali **Timsort** (Tim Peters, 2002; Python'un ve Java'nın nesne sıralaması): dizide zaten sıralı olan ardışık parçaları ("koşuları", runs) bulup onları birleştiriyor. Gerçek veride sıklıkla bulunan kısmen sıralı yapıları kullanarak birçok durumda $O(n)$'e yaklaşıyor.

---

## Alıştırmalar

**1** – Birleştirme sırasında dizideki **ters çiftleri** (Ders 9.3, Alıştırma 1) say. Sağ yarıdan bir eleman alındığında, kaç ters çift tespit edilmiş olur? `[38 27 43 3 9 82 10]` için sonuç ne? Bu yöntemin karmaşıklığı ne, ve saf yöntemle ($O(n^2)$) karşılaştır.

**2** – Birleştirmeli sıralamayı **bağlı liste** (Ders 8.2) için yaz. Listenin ortasını nasıl bulursun (Ders 8.2, Alıştırma 2)? Neden ek bellek gerekmiyor? Aşağıdan yukarı sürüm bağlı listede neden daha da doğal?

**3** – En kötü durumda karşılaştırma sayısı $C(n) = C(\lfloor n/2 \rfloor) + C(\lceil n/2 \rceil) + n - 1$, $C(1) = 0$. $n = 2^k$ için kapalı formu bul. $n = 16\,000\,000$'da bu sayı kaç, ve ölçülen 362 787 150 ile karşılaştır.

**4** – Birleştirmeli sıralamanın $n$ elemanlık yardımcı dizisini **yarıya** indirebilir misin? İpucu: birleştirmede sadece **sol** yarıyı yardımcı diziye kopyala.

**5** – 16 milyon elemanlık bir diziyi 8 çekirdekte paralel sıralamak istiyorsun. Birleştirmeli sıralamanın hangi kısmı kolayca paralelleşiyor, hangi kısmı darboğaz oluyor? Aşağıdan yukarı sürümde her genişlikte kaç bağımsız birleştirme var?

<details>
<summary>Cevaplar</summary>

**1** – Sağ yarıdan $y[j]$ alındığında, sol yarıda henüz alınmamış her eleman ($y[i..orta)$, yani `orta - i` tane) ondan büyük ve onunla bir ters çift oluşturuyor; sol yarıdan alınan elemanlar ters çift oluşturmuyor. `if (y[j] < y[i]) { ters += orta - i; ... }`:

```
ters cift: 11
```

(Elle: 38 dört elemandan (27, 3, 9, 10), 27 üçten, 43 üçten, 82 birden büyük ve onlardan önce: $4 + 3 + 3 + 1 = 11$.) Her ters çift tam bir kez, iki elemanın farklı yarılarda olduğu en küçük özyineleme seviyesinde sayılıyor. Maliyet birleştirmeli sıralamanın kendisi: $O(n \log n)$. İki sıralamanın (iki kişinin film tercihleri gibi) ne kadar benzediğini ölçen Kendall tau uzaklığı tam olarak bu sayı.

**2** – Ortayı yavaş/hızlı pointer'larla bul (Ders 8.2), listeyi orada ikiye kes, iki yarıyı özyinelemeyle sırala, sonra birleştir. Birleştirme düğümleri **yeniden bağlıyor**, kopyalamıyor: yeni listenin sonuna sıradaki küçük düğümü `sonraki` pointer'ıyla ekle. Ek bellek yok (özyineleme yığını dışında). Aşağıdan yukarı sürümde orta bulmaya da gerek yok: listeyi başından tarayıp uzunluğu 1, 2, 4... olan parçaları sırayla birleştirmek yeterli; sabit ek bellekle $O(n \log n)$. Linux çekirdeğinin `list_sort`'u (`lib/list_sort.c`) intrusive listeler (Ders 8.3) için tam bunu yapıyor.

**3** – $n = 2^k$ için $C(n) = 2C(n/2) + n - 1$. Açarak: $C(n) = \sum_{i=0}^{k-1} 2^i (n/2^i - 1) = kn - (2^k - 1) = n \log_2 n - n + 1$. Genel $n$ için Knuth'un formülü $n \lceil \log_2 n \rceil - 2^{\lceil \log_2 n \rceil} + 1$. $n = 16\,000\,000$: $\lceil \log_2 n \rceil = 24$, $2^{24} = 16\,777\,216$; $C = 384\,000\,000 - 16\,777\,216 + 1 = 367\,222\,785$. Ölçülen 362 787 150, en kötü durumun %1.2 altında: rastgele girdide birleştirmelerin çoğu son birkaç elemana kadar karşılaştırma yapıyor.

**4** – Evet. Birleştirmeden önce sadece sol yarıyı ($orta - lo$ eleman) yardımcı diziye kopyala; sağ yarı `a`'da yerinde kalsın. Birleştirme `a[k]`'ya yazarken $k$ hiçbir zaman sağ yarının okunmamış kısmını geçemiyor: $k = lo + (i - lo) + (j - orta) \le j$, çünkü $i \le orta$. Yani sağ yarının henüz okunmamış elemanlarının üzerine hiç yazılmıyor. Sol yarı bitince sağ yarının kalanı zaten yerinde, kopyalamaya gerek yok. Ek bellek $n/2$, ve kopyalama yarıya iniyor. Bu, Timsort'un yaptığı (daha kısa olan koşuyu kopyalıyor).

**5** – **Yönet** adımı paralelleşiyor: iki yarı birbirinden bağımsız, 8 çekirdeğe 8 parça dağıtıp her birini ayrı sıralamak kolay (Faz 10'daki iş parçacıkları). Darboğaz **son birleştirmeler**: en üstteki birleştirme $n$ elemanı tek bir çekirdekte işliyor, bir öncekinde 2 birleştirme var, 2 çekirdek çalışıyor... Aşağıdan yukarı sürümde genişlik $g$'de $n / (2g)$ bağımsız birleştirme var: başta milyonlarca, sonda bir tane. Çözüm, birleştirmenin kendisini paralelleştirmek: büyük birleştirmeyi, sol yarının ortancasını sağ yarıda ikili aramayla (Ders 9.2) bulup iki bağımsız küçük birleştirmeye bölmek. Bu, paralel birleştirmeli sıralamayı $O(\log^2 n)$ derinliğe indiriyor.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 2.3: böl-yönet ve birleştirmeli sıralama; Bölüm 4: özyineleme ağacı ve Master teoremi.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 5.2.4: birleştirmeyle sıralama ve kesin karşılaştırma sayısı.
- Robert Sedgewick ve Kevin Wayne, *Algorithms* (4. baskı), Bölüm 2.2: yukarıdan aşağı, aşağıdan yukarı ve iyileştirmeler.
- Tim Peters, "listsort.txt" (CPython kaynak kodu, `Objects/listsort.txt`), 2002: Timsort'un tasarımı.
- Linux çekirdeği, `lib/list_sort.c`: bağlı listelerde aşağıdan yukarı birleştirmeli sıralama.

**Sıradaki ders:** Hızlı sıralama. Bölümleme şemaları (Lomuto, Hoare), pivot seçimi ve beklenen analiz.
