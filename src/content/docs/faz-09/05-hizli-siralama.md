---
title: "9.5 Hızlı sıralama"
description: "Böl-yönet'in öbür yüzü: işi bölmede yapıp birleştirmeyi ortadan kaldırmak; Lomuto ve Hoare bölümleme şemaları ve değişmezleri; ilk eleman pivotunun sıralı girdide n²/2 karşılaştırmaya düşmesi, rastgele pivot ve beklenen 2n ln n karşılaştırmanın 'her çift en fazla bir kez karşılaştırılır' argümanıyla ispatı; küçük tarafa özyineleme ile O(log n) yığın derinliği; hep aynı ya da az farklı değerli girdide Lomuto'nun karesele çökmesi, Hoare'nin dayanması ve Dijkstra'nın üç yollu bölmesinin 4 milyon eşit elemanı 2.5 ms'de bitirmesi; introsort."
---

Ders 9.4'teki birleştirmeli sıralama işi **sonda** yapıyordu: kolay bir bölme (ortadan ikiye), zor bir birleştirme. **Hızlı sıralama** (quicksort; Tony Hoare, 1959) tersini yapıyor: işin hepsi **bölmede**, birleştirme yok. Bir **pivot** eleman seç; diziyi, pivottan küçükler solda ve büyükler sağda olacak şekilde yeniden diz. Pivot artık son yerinde. İki tarafı özyinelemeyle sırala; iş bitti, çünkü sol taraftaki her eleman sağdakilerin hepsinden küçük.

Yerinde çalışıyor (ek dizi yok), iç döngüsü çok kısa, ve pratikte genelde en hızlı karşılaştırmalı sıralama. Ama en kötü durumda $\Theta(n^2)$, ve kötü bir pivot seçimi ya da çok sayıda eşit anahtar onu oraya sürükleyebiliyor. Bu ders hem neden bu kadar hızlı olduğunu hem de bu tuzakları ölçüyor.

---

## 1. Kod

```c
/* Hizli siralama: Lomuto ve Hoare bolmeleri, pivot secimi, uc yollu bolme */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long kars, en_derin;
static uint64_t xs = 88172645463325252ull;
static uint64_t rnd(void) { xs ^= xs << 13; xs ^= xs >> 7; xs ^= xs << 17; return xs; }
static void takas(int *a, long i, long j) { int t = a[i]; a[i] = a[j]; a[j] = t; }

typedef enum { ILK, RASTGELE } Pivot;
static Pivot pivot_turu;
static long pivot_sec(long lo, long hi) { return pivot_turu == ILK ? lo : lo + (long)(rnd() % (uint64_t)(hi - lo + 1)); }

/* LOMUTO: pivot sona. DEGISMEZ: a[lo..s) < p, a[s..i) >= p. Sonunda pivot a[s]'ye. */
static long lomuto(int *a, long lo, long hi) {             /* [lo, hi] kapali */
    takas(a, pivot_sec(lo, hi), hi);
    int p = a[hi]; long s = lo;
    for (long i = lo; i < hi; i++) { kars++; if (a[i] < p) takas(a, i, s++); }
    takas(a, s, hi);
    return s;                                               /* pivotun son yeri */
}

/* HOARE: iki uctan iceri. DEGISMEZ: a[lo..i) <= p, a(j..hi] >= p. Donen j: a[lo..j] <= a[j+1..hi]. */
static long hoare(int *a, long lo, long hi) {
    takas(a, pivot_sec(lo, hi), lo);
    int p = a[lo]; long i = lo - 1, j = hi + 1;
    for (;;) {
        do { i++; kars++; } while (a[i] < p);
        do { j--; kars++; } while (a[j] > p);
        if (i >= j) return j;
        takas(a, i, j);
    }
}

static void q_lomuto(int *a, long lo, long hi, long d) {
    if (d > en_derin) en_derin = d;
    while (lo < hi) {                                       /* kucuk tarafa ozyinele, buyuk tarafta dongu: derinlik O(log n) */
        long m = lomuto(a, lo, hi);
        if (m - lo < hi - m) { q_lomuto(a, lo, m - 1, d + 1); lo = m + 1; }
        else                 { q_lomuto(a, m + 1, hi, d + 1); hi = m - 1; }
    }
}

static void q_hoare(int *a, long lo, long hi, long d) {
    if (d > en_derin) en_derin = d;
    while (lo < hi) {
        long m = hoare(a, lo, hi);
        if (m - lo < hi - m) { q_hoare(a, lo, m, d + 1); lo = m + 1; }
        else                 { q_hoare(a, m + 1, hi, d + 1); hi = m; }
    }
}

/* UC YOLLU (Dijkstra): a[lo..lt) < p, a[lt..i) == p, a(gt..hi] > p. Esitler bir kez yerlesir. */
static void q_uc(int *a, long lo, long hi, long d) {
    if (d > en_derin) en_derin = d;
    while (lo < hi) {
        takas(a, pivot_sec(lo, hi), lo);
        int p = a[lo]; long lt = lo, i = lo + 1, gt = hi;
        while (i <= gt) {
            kars++;
            if (a[i] < p) takas(a, lt++, i++);
            else if (a[i] > p) takas(a, i, gt--);
            else i++;
        }
        if (lt - lo < hi - gt) { q_uc(a, lo, lt - 1, d + 1); lo = gt + 1; }
        else                   { q_uc(a, gt + 1, hi, d + 1); hi = lt - 1; }
    }
}
```

### Lomuto bölmesi

Pivot dizinin sonuna konuyor. Soldan sağa tek bir tarama; pivottan küçük her eleman, "küçükler bölgesinin" sonuna takaslanıyor. Değişmez: $a[lo..s)$ pivottan küçük, $a[s..i)$ büyük ya da eşit, $a[i..hi)$ henüz bakılmamış.

```
  lo          s           i            hi
  [   < p    |   >= p    |  bakılmadı  | p ]
```

Tarama bitince pivot $a[s]$ ile takaslanıp iki bölgenin arasına oturuyor ve son yeri $s$ dönüyor. Basit ve anlaşılır; Ders 8.23'te kullandığımız şema buydu.

### Hoare bölmesi

Hoare'nin orijinal şeması iki uçtan içeri doğru yürüyor: soldan, pivottan büyük ya da eşit bir eleman bulana kadar; sağdan, pivottan küçük ya da eşit bir eleman bulana kadar; ikisini takasla, devam et. İki gösterge karşılaşınca dur. Değişmez: $a[lo..i)$ pivottan küçük ya da eşit, $a(j..hi]$ büyük ya da eşit. Dönen $j$, pivotun son yeri **değil**: sadece $a[lo..j]$'nin hepsinin $a[j+1..hi]$'nin hepsinden küçük ya da eşit olduğu bir bölme noktası. Bu yüzden özyineleme $[lo, j]$ ve $[j+1, hi]$ üzerinde (Lomuto'daki gibi pivotu dışarıda bırakarak değil).

Hoare daha az takas yapıyor (yanlış tarafta olan iki elemanı bir takasla düzeltiyor; Lomuto küçük her elemanı takaslıyor), ve göreceğimiz gibi eşit elemanlarla çok daha iyi başa çıkıyor. Bedeli, değişmezinin ve sınır durumlarının daha ince olması: Hoare şemasını "biraz değiştirip" sonsuz döngü ya da dizi dışı erişim üretmek kolay. (Burada `do-while` ile önce ilerleyip sonra karşılaştırmak, ve pivotun `lo`'da durması, göstergelerin dizi dışına çıkmamasını garanti ediyor: pivot ilk taramada bir durak, ilk takastan sonra da takaslanan elemanlar.)

### Küçük tarafa özyineleme

`q_lomuto` ve diğerleri iki taraftan **küçük** olanına özyinelemeyle iniyor, büyük olanı aynı fonksiyonun döngüsünde işliyor (kuyruk özyinelemesini elle döngüye çevirmek; Ders 8.6). Küçük taraf en fazla yarı boyutta olduğu için özyineleme derinliği en fazla $\log_2 n$, **en kötü durumda bile**. Bunu yapmasaydık, en kötü durumda derinlik $n$ olurdu ve 1 milyon elemanlık sıralı bir dizi yığını taşırırdı (Ders 8.6'nın 174 bin çerçevelik sınırı). `derinlik` sütunu bunu ölçüyor.

---

## 2. Pivot seçimi

İdeal pivot **ortanca** (medyan): diziyi tam ikiye böler, $T(n) = 2T(n/2) + \Theta(n) = \Theta(n \log n)$, Ders 9.4 ile aynı. En kötü pivot en küçük ya da en büyük eleman: bir taraf boş, öteki $n - 1$ elemanlı, $T(n) = T(n-1) + \Theta(n) = \Theta(n^2)$.

En basit seçim, dizinin **ilk** elemanı. Rastgele bir dizide bu rastgele bir eleman kadar iyi. Ama dizi **zaten sıralıysa** ilk eleman her seferinde en küçük eleman, ve her bölme en kötü bölme. Sıralı girdi gerçek hayatta çok yaygın (Ders 8.8'deki BST'nin dejenere olduğu durumun aynısı; aslında rastgele pivotlu hızlı sıralama ile rastgele sırayla kurulmuş BST matematiksel olarak aynı yapı).

Çözüm: pivotu **rastgele** seç (`pivot_sec`). Artık girdinin sırası hiçbir şeyi değiştirmiyor; kötü bölmeler sadece kötü şansla geliyor ve onların olasılığı çok küçük.

### Beklenen karşılaştırma sayısı

Elemanları sıralı hallerine göre $z_1 < z_2 < \dots < z_n$ diye adlandıralım. İki gözlem:

- Bir karşılaştırma her zaman pivotla yapılıyor, ve bir eleman pivot olduktan sonra bir daha karşılaştırılmıyor. Dolayısıyla her $(z_i, z_j)$ çifti **en fazla bir kez** karşılaştırılıyor.
- $z_i$ ile $z_j$ ($i < j$), ancak $\{z_i, z_{i+1}, \dots, z_j\}$ kümesinden **ilk** pivot seçilen eleman $z_i$ ya da $z_j$ ise karşılaştırılıyor. Aradaki bir $z_k$ önce seçilirse, $z_i$ ve $z_j$ onun farklı taraflarına düşüyor ve bir daha karşılaşmıyorlar.

Pivotlar rastgele olduğu için o kümeden ilk seçilenin $z_i$ ya da $z_j$ olma olasılığı $\frac{2}{j - i + 1}$. Olasılığın doğrusallığıyla (Ders 6.29) beklenen karşılaştırma sayısı:

$$
E[C] = \sum_{i=1}^{n-1} \sum_{j=i+1}^{n} \frac{2}{j - i + 1} \;\le\; 2n \sum_{k=2}^{n} \frac{1}{k} \;<\; 2n H_n \approx 2 n \ln n \approx 1.39\, n \log_2 n.
$$

($H_n$ harmonik sayı, Ders 6.10.) Kesin değer $2(n+1)H_n - 4n$. $n = 4 \cdot 10^6$'da $H_n \approx 15.78$: yaklaşık 110 milyon karşılaştırma. Ders 9.4'teki birleştirmeli sıralamanın $0.94\, n \log_2 n \approx 82$ milyonundan **%35 fazla**, ama yine de genelde daha hızlı (aşağıda).

---

## 3. Ölçüm

Dört sürüm, dört girdi: rastgele, sıralı, **hep aynı** değer ve sadece **10 farklı** değer. Önce 20 000 eleman (karesel durumların da ölçülebilmesi için), sonra 4 milyon (karesel olanlar atlandı):

```
$ cc -std=c11 -O2 -Wall -Wextra hizli.c -o hizli -lm && ./hizli
n=20000  (2 n ln n = 396140)
  rastgele:
    Lomuto, ilk pivot      0.0009 s       350295 karsilastirma  derinlik 9
    Lomuto, rastgele       0.0010 s       335532 karsilastirma  derinlik 9
    Hoare, rastgele        0.0012 s       414144 karsilastirma  derinlik 10
    uc yollu, rastgele     0.0011 s       341072 karsilastirma  derinlik 9
  sirali:
    Lomuto, ilk pivot      0.0632 s    199990000 karsilastirma  derinlik 1
    Lomuto, rastgele       0.0004 s       332162 karsilastirma  derinlik 10
    Hoare, rastgele        0.0006 s       429831 karsilastirma  derinlik 10
    uc yollu, rastgele     0.0006 s       335313 karsilastirma  derinlik 9
  hep ayni:
    Lomuto, ilk pivot      0.0633 s    199990000 karsilastirma  derinlik 1
    Lomuto, rastgele       0.0633 s    199990000 karsilastirma  derinlik 1
    Hoare, rastgele        0.0003 s       318430 karsilastirma  derinlik 14
    uc yollu, rastgele     0.0000 s        19999 karsilastirma  derinlik 1
  10 farkli deger:
    Lomuto, ilk pivot      0.0069 s     20065386 karsilastirma  derinlik 4
    Lomuto, rastgele       0.0070 s     20075124 karsilastirma  derinlik 3
    Hoare, rastgele        0.0005 s       327838 karsilastirma  derinlik 13
    uc yollu, rastgele     0.0002 s        65924 karsilastirma  derinlik 3
n=4000000  (2 n ln n = 121614439)
  rastgele:
    Lomuto, ilk pivot    (atlandi: karesel)
    Lomuto, rastgele       0.2737 s    106630105 karsilastirma  derinlik 14
    Hoare, rastgele        0.3370 s    120691174 karsilastirma  derinlik 15
    uc yollu, rastgele     0.3266 s    107662029 karsilastirma  derinlik 14
  sirali:
    Lomuto, ilk pivot    (atlandi: karesel)
    Lomuto, rastgele       0.0969 s    110535655 karsilastirma  derinlik 14
    Hoare, rastgele        0.1286 s    126205033 karsilastirma  derinlik 14
    uc yollu, rastgele     0.1638 s    107079217 karsilastirma  derinlik 14
  hep ayni:
    Lomuto, ilk pivot    (atlandi: karesel)
    Lomuto, rastgele     (atlandi: karesel)
    Hoare, rastgele        0.0723 s     95079934 karsilastirma  derinlik 21
    uc yollu, rastgele     0.0025 s      3999999 karsilastirma  derinlik 1
  10 farkli deger:
    Lomuto, ilk pivot    (atlandi: karesel)
    Lomuto, rastgele     (atlandi: karesel)
    Hoare, rastgele        0.1117 s     99037966 karsilastirma  derinlik 20
    uc yollu, rastgele     0.0388 s     13201115 karsilastirma  derinlik 3
```

(Her sıralamadan sonra dizinin sıralı olduğu kontrol ediliyor; aynı program ASan ve UBSan altında da temiz.)

**Pivot**: ilk eleman pivotu sıralı 20 000 elemanda tam $n(n-1)/2 = 199\,990\,000$ karşılaştırma, rastgele pivottan **600 kat** fazla. 4 milyonda bu 8 trilyon karşılaştırma, saatler. Rastgele pivotla sıralı girdi rastgele girdiden bile hızlı (dal tahmini, Ders 7.22: bölmenin "küçük mü" dalı sıralı veride düzenli).

**Beklenen sayı**: 4 milyon rastgele elemanda Lomuto 106.6 milyon karşılaştırma; Bölüm 2'deki kesin formül 110 milyon diyordu (Lomuto her bölmede pivotla karşılaştırmayı bir eksik sayıyor). Hoare her göstergenin son "durma" karşılaştırmasını da saydığı için biraz fazla.

**Derinlik** en kötü durumda bile küçük: ilk-pivot-sıralı-girdi durumunda derinlik 1, çünkü küçük taraf hep boş ve büyük taraf döngüde işleniyor. Aynı kod iki tarafa da özyinelemeyle inseydi derinlik 20 000 olurdu.

**Tekrarlı anahtarlar** asıl sürpriz. **Hep aynı** değer: rastgele pivotlu Lomuto da karesel! Pivota eşit elemanların hepsi "büyük ya da eşit" tarafına gidiyor; bölme tamamen dengesiz ve pivot seçimi hiçbir şeyi değiştirmiyor. Sadece 10 farklı değer olduğunda da aynı: her değerden 2000 kopyası olan bir dizide Lomuto 20 milyon karşılaştırma. Gerçek veride tekrarlar çok yaygın (yaşlar, şehirler, durum kodları), ve bu bir zayıflık değil, bir **açık**.

- **Hoare** eşit elemanlarda dayanıyor: iki gösterge de pivota eşit elemanlarda **duruyor** ve onları takaslıyor; eşitler iki tarafa yarı yarıya dağılıyor ve bölme dengeli kalıyor. Gereksiz takaslar yapıyor ama $O(n \log n)$.
- **Üç yollu bölme** (Dijkstra'nın "Hollanda bayrağı" problemi): diziyi üç bölgeye ayır, pivottan küçükler, **eşitler**, büyükler. Eşitler tek seferde son yerlerine yerleşiyor ve bir daha hiç dokunulmuyor. Hep aynı değerde tek bir bölme, $n - 1$ karşılaştırma: 4 milyon elemanda **2.5 ms**. 10 farklı değerde derinlik 3 ve Hoare'den 3 kat hızlı. $k$ farklı değer varsa beklenen maliyet $O(n \log k)$; $k = n$'de normal hızlı sıralama.

Rastgele ve farklı değerli girdide üç yollu bölme Lomuto'dan %20 yavaş (fazladan karşılaştırma ve takas); C++'ın `std::sort`'u ve Go'nun `sort`'u gibi modern uygulamalar bu yüzden ikisini birleştiriyor: normalde iki yollu, çok sayıda eşit pivot görünce üç yollu bölme.

### Neden hızlı

Ders 9.4'teki birleştirmeli sıralama 4 milyon elemanı 0.19–0.22 s'de, hızlı sıralama 0.27–0.34 s'de sıraladı: bu ölçümde birleştirmeli sıralama kazanıyor. Hızlı sıralamanın bilinen hızı bu temel sürümlerde değil, iyileştirilmiş hallerinde: küçük parçalarda ekleme sıralaması (Ders 9.4'teki gibi), üçün ortancası (median of 3) pivot, ve dalsız bölme. Hızlı sıralamanın gerçek avantajları başka: **yerinde** (birleştirmeli sıralamanın $n$ elemanlık ek dizisi yok) ve **cache dostu** (her bölme ardışık bir tarama; parçalar küçüldükçe cache'e sığıyor ve oradan hiç çıkmıyor).

---

## 4. En kötü durumu garanti etmek

Rastgele pivotla karesel durumun olasılığı ihmal edilebilir, ama sıfır değil; ve rastgele sayı üreteci tahmin edilebilirse bir saldırgan onu üretebilir (Ders 8.20, Alıştırma 5). Pivotu deterministik bir kuralla seçen sürümler (üçün ortancası) ise bilinen bir girdiyle karesele zorlanabiliyor: Doug McIlroy'un 1999 tarihli "A Killer Adversary for Quicksort" makalesi, karşılaştırma fonksiyonu sırasında girdiyi uyduran bir programla neredeyse her `qsort`'u karesel yaptı.

**Introsort** (David Musser, 1997) bunu kesin olarak çözüyor: hızlı sıralama gibi başla, özyineleme derinliğini say; derinlik $2 \log_2 n$'i aşarsa (bu, bölmelerin sistematik olarak kötü gittiğinin işareti) o parçayı **heapsort** ile sırala (Ders 9.6). Heapsort en kötü durumda $O(n \log n)$. Sonuç: normalde hızlı sıralamanın hızı, en kötü durumda heapsort'un garantisi. C++'ın `std::sort`'u introsort.

---

## Alıştırmalar

**1** – Bölüm 2'deki toplamı kesin olarak hesapla: $\sum_{i<j} \frac{2}{j-i+1} = 2(n+1)H_n - 4n$ olduğunu göster (iç toplamı $k = j - i + 1$ üzerinden yaz ve her $k$'nin kaç kez geçtiğini say). $n = 20\,000$ için sonuç, ölçülen 335 532 ile uyumlu mu?

**2** – **Üçün ortancası**: pivotu $a[lo]$, $a[(lo+hi)/2]$, $a[hi]$'nin ortancası olarak seç. Sıralı girdide ne olur? Ters sıralıda? Bu yöntem rastgele pivotun yerini tamamen tutar mı?

**3** – `q_lomuto`'yu "küçük tarafa özyinele" yerine her iki tarafa da özyinelemeyle inen haliyle yaz (`q(lo, m-1); q(m+1, hi);`). İlk eleman pivotuyla 1 milyon elemanlık sıralı bir dizide `-O0`'da ne olur (Ders 8.6)? `-O2`'de?

**4** – Hoare bölmesinde `do { i++; } while (a[i] < p);` yerine `while (a[i] < p) i++;` yazmak (önce karşılaştır, sonra ilerle) neden sonsuz döngüye yol açabilir? Hangi girdide?

**5** – Bir `int` dizisinin **en sık geçen** değerini bulmak istiyorsun. Üç yollu hızlı sıralama bunun için neden uygun? Sıralamadan, $O(n)$ beklenen zamanda başka nasıl bulunur (Faz 8)?

<details>
<summary>Cevaplar</summary>

**1** – $k = j - i + 1$ ($2 \le k \le n$) için, aradaki fark $k - 1$ olan $(i, j)$ çifti sayısı $n - k + 1$. Toplam $\sum_{k=2}^{n} \frac{2(n - k + 1)}{k} = 2(n+1)\sum_{k=2}^{n} \frac1k - 2(n-1) = 2(n+1)(H_n - 1) - 2(n - 1) = 2(n+1)H_n - 4n$. $n = 20\,000$: $H_n \approx \ln 20\,000 + 0.5772 = 10.481$; $2 \cdot 20\,001 \cdot 10.481 - 80\,000 \approx 339\,260$. Ölçülen 335 532 (Lomuto, rastgele pivot), %1 içinde; fark, Lomuto'nun her bölmede pivotun kendisiyle karşılaştırmayı yapmaması.

**2** – Sıralı girdide ortadaki eleman tam ortanca: mükemmel bölmeler, rastgele pivottan bile iyi. Ters sıralıda da. Ortancanın beklenen konumu daha merkezde olduğu için rastgele girdide de karşılaştırma sayısı azalıyor (yaklaşık $1.19\, n \log_2 n$). Ama yöntem **deterministik**: kötü bir girdi kurulabilir ("organ borusu" dizileri `1 2 3 ... n ... 3 2 1` ve McIlroy'un düşmanı). Rastgeleliğin "her girdi için" garantisini vermiyor. Pratik kütüphaneler ikisini birleştiriyor: üçün ortancası (ya da büyük dizilerde dokuzun ortancası, "ninther") ve en kötü durum için introsort.

**3** – İki tarafa da özyinelemeyle inince sıralı dizide her çağrı bir boş, bir de $n - 1$ elemanlı taraf üretiyor; özyineleme derinliği $n$. `-O0`'da 1 milyon çerçeve, Ders 8.6'daki ~174 binlik sınırın çok üstünde: segmentation fault (ASan'la `stack-overflow`). `-O2`'de clang ikinci çağrıyı kuyruk çağrısı olarak döngüye çevirebilir (Ders 8.6, Bölüm 4) ve büyük taraf sağdaysa program şans eseri çalışır; ama hata ayıklama derlemesi çöker, ve ters sıralı dizide büyük taraf solda kalıp yine çöker. Hem karesel süre hem yığın taşması; elle küçük tarafa özyinelemek yığın sorununu her durumda çözüyor.

**4** – `while (a[i] < p) i++;` biçiminde, iki gösterge de pivota eşit elemanlarda duruyor; takastan sonra **ilerlemeden** tekrar aynı elemanlara bakıyorlar. İkisi de pivota eşitse (`a[i] == a[j] == p`), takas onları değiştirmiyor, döngü tekrar aynı noktalarda duruyor, ve `i < j` olduğu sürece sonsuza kadar takaslıyor. Hep aynı değerlerden oluşan bir dizi bunu hemen tetikliyor. `do-while` ile her turda önce bir adım ilerlemek, göstergelerin her takastan sonra en az bir adım hareket etmesini garanti ediyor.

**5** – Üç yollu bölme, pivota eşit bütün elemanları tek bir blok halinde topluyor; sıralama sonunda eşit değerler ardışık bloklarda, ve tek bir tarama en uzun bloğu buluyor. Az farklı değer varsa ($k \ll n$) üç yollu sıralama $O(n \log k)$, yani hızlı. Sıralamadan: Ders 8.14–8.15'teki hash tablosuyla değer → sayaç sözlüğü kurup en büyük sayacı bulmak, $O(n)$ beklenen. Değerler küçük bir aralıktaysa düz bir sayaç dizisi (Ders 9.7'deki sayma sıralamasının ilk adımı), $O(n + \text{aralık})$ ve kesin.

</details>

---

## Kaynaklar

- C. A. R. Hoare, "Quicksort", *The Computer Journal* 5(1), 1962.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 7: Lomuto bölmesi, rastgele pivot ve beklenen analiz; Problem 7-1: Hoare bölmesi.
- Robert Sedgewick ve Kevin Wayne, *Algorithms* (4. baskı), Bölüm 2.3: üç yollu bölme ve tekrarlı anahtarlar.
- Jon Bentley ve M. Douglas McIlroy, "Engineering a Sort Function", *Software: Practice and Experience* 23(11), 1993.
- M. Douglas McIlroy, "A Killer Adversary for Quicksort", *Software: Practice and Experience* 29(4), 1999.
- David Musser, "Introspective Sorting and Selection Algorithms", *Software: Practice and Experience* 27(8), 1997.

**Sıradaki ders:** Heapsort ve sıralama alt sınırı. Karşılaştırma tabanlı sıralamanın Ω(n log n) ispatı (karar ağacı).
