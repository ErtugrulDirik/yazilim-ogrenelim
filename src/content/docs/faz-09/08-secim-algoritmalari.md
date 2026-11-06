---
title: "9.8 Seçim algoritmaları"
description: "Bir dizinin k. en küçük elemanını (medyanı, yüzdelikleri) sıralamadan bulmak: hızlı sıralamanın sadece bir tarafa inen hali quickselect ve beklenen 2(1 + ln 2)n ≈ 3.39n karşılaştırma; 50 denemede 1.65n ile 6.24n arası dağılım; en kötü durumda da O(n) garanti eden medyanların medyanı (BFPRT, 1973), beşli gruplar ve T(n) ≤ T(n/5) + T(7n/10) + O(n) bağıntısı; 16 milyon elemanda medyan: qsort 1.63 s, quickselect 0.16 s, medyanların medyanı 0.33 s; neden 3'lü gruplar yetmiyor; introselect."
---

Bir dizinin **medyanını** (ortancasını) bulmak istiyorsun. Ya da en büyük %1'i, ya da 90. yüzdeliği. En kolay yol diziyi sıralayıp $k$. elemana bakmak: $O(n \log n)$. Ama sıralama, sorulmayan bir sürü soruyu da cevaplıyor: **her** elemanın yerini. Sadece $k$. elemanı istiyorsak daha azı yetmeli. Bu ders, $k$. en küçüğü **doğrusal** zamanda bulan iki algoritmayı yazıyor: biri beklenen $O(n)$ ve pratikte çok hızlı, öbürü en kötü durumda bile $O(n)$ ve teorik olarak çok önemli.

Medyan, istatistikte ortalamaya göre aykırı değerlere çok daha dayanıklı (bir maaş listesine tek bir milyarder eklenince ortalama uçar, medyan neredeyse kıpırdamaz). Ders 9.5'teki hızlı sıralamanın ideal pivotu da medyandı. Ve en büyük $k$ elemanı bulmak (Ders 8.12'nin Alıştırma 1'i) arama motorlarından öneri sistemlerine her yerde.

---

## 1. Kod

```c
/* k. en kucugu bulmak: siralayip bak, quickselect (rastgele pivot), medyanlarin medyani (deterministik) */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long kars;
static uint64_t xs = 88172645463325252ull;
static uint64_t rnd(void) { xs ^= xs << 13; xs ^= xs >> 7; xs ^= xs << 17; return xs; }
static void takas(int *a, long i, long j) { int t = a[i]; a[i] = a[j]; a[j] = t; }

/* Uc yollu bolme (Ders 9.5): a[lo..lt) < p, a[lt..gt] == p, a(gt..hi] > p */
static void bol(int *a, long lo, long hi, int p, long *lt_, long *gt_) {
    long lt = lo, i = lo, gt = hi;
    while (i <= gt) {
        kars++;
        if (a[i] < p) takas(a, lt++, i++);
        else if (a[i] > p) takas(a, i, gt--);
        else i++;
    }
    *lt_ = lt; *gt_ = gt;
}

/* QUICKSELECT: sadece k'nin oldugu tarafa in. Beklenen O(n). */
static int quickselect(int *a, long n, long k) {          /* k: 0 tabanli sira */
    long lo = 0, hi = n - 1;
    for (;;) {
        int p = a[lo + (long)(rnd() % (uint64_t)(hi - lo + 1))];
        long lt, gt; bol(a, lo, hi, p, &lt, &gt);
        if (k < lt) hi = lt - 1;
        else if (k > gt) lo = gt + 1;
        else return p;                                     /* k esitler blogunda */
    }
}

/* MEDYANLARIN MEDYANI (Blum, Floyd, Pratt, Rivest, Tarjan 1973): en kotu durumda O(n) */
static int bms(int *a, long lo, long hi, long k);
static long besli_medyan(int *a, long lo, long hi) {       /* en fazla 5 eleman: ekleme siralamasi, ortadakinin konumu */
    for (long i = lo + 1; i <= hi; i++) { int x = a[i]; long j = i; while (j > lo && (kars++, a[j - 1] > x)) { a[j] = a[j - 1]; j--; } a[j] = x; }
    return lo + (hi - lo) / 2;
}
static int pivot_bul(int *a, long lo, long hi) {
    if (hi - lo < 5) return a[besli_medyan(a, lo, hi)];
    long m = lo;                                           /* her 5'li grubun medyanini dizinin basina topla */
    for (long i = lo; i <= hi; i += 5) {
        long son = i + 4 < hi ? i + 4 : hi;
        takas(a, m++, besli_medyan(a, i, son));
    }
    return bms(a, lo, m - 1, lo + (m - 1 - lo) / 2);       /* medyanlarin medyanini ozyinelemeyle bul */
}
static int bms(int *a, long lo, long hi, long k) {
    for (;;) {
        if (lo == hi) return a[lo];
        int p = pivot_bul(a, lo, hi);
        long lt, gt; bol(a, lo, hi, p, &lt, &gt);
        if (k < lt) hi = lt - 1;
        else if (k > gt) lo = gt + 1;
        else return p;
    }
}
```

İki algoritma da Ders 9.5'teki **üç yollu bölmeyi** kullanıyor: pivota eşitler ortada bir blokta toplanıyor, ve aranan sıra o bloğun içindeyse cevap pivot. Tekrarlı değerler bu sayede sorun olmuyor (Ders 9.5'teki Lomuto'nun "hep aynı değerde karesel" tuzağı).

---

## 2. Quickselect

Hoare'nin (1961) gözlemi: hızlı sıralama bölmeden sonra **iki** tarafa iniyor, ama $k$. eleman sadece **bir** tarafta. Bölmeden sonra $k$ hangi bölgedeyse sadece oraya in.

- $k < lt$: aranan, pivottan küçükler arasında. Sol tarafa in.
- $k > gt$: büyükler arasında. Sağ tarafa in.
- Aksi halde $k$. eleman pivota eşit: bitti.

Özyineleme tek dallı olduğu için doğrudan bir döngü (Ders 8.6'daki kuyruk özyinelemesi). Değişmez: aranan $k$. eleman her zaman $a[lo..hi]$ içinde; ve $a[0..lo)$'nun hepsi ondan küçük ya da eşit, $a(hi..n)$'nin hepsi büyük ya da eşit.

### Beklenen maliyet

Rastgele pivot iyi bir pivotsa (diyelim, dizinin ortadaki yarısından, yani sıralı halde $[n/4, 3n/4]$ arasından geliyorsa; olasılık $1/2$) kalan parça en fazla $3n/4$. Ortalamada iki denemede bir iyi pivot geliyor; her bölme $O(n)$. Kabaca:

$$
T(n) \le 2 \cdot cn + T(3n/4) \;\Longrightarrow\; T(n) \le 2cn \left(1 + \tfrac34 + (\tfrac34)^2 + \dots\right) = 8cn = O(n).
$$

(Geometrik toplam, Ders 6.10.) Hızlı sıralamanın $O(n \log n)$'inden farkı: her seviyede **toplam** iş sabit kalmıyor, geometrik olarak küçülüyor, çünkü parçalardan sadece biri işleniyor.

Kesin analiz (Ders 9.5'teki "her çift en fazla bir kez karşılaştırılır" argümanıyla aynı türden) medyan için beklenen karşılaştırma sayısının $2(1 + \ln 2)\,n \approx 3.39\,n$ olduğunu veriyor. En kötü durumda (her pivot en kötüsü) yine $\Theta(n^2)$, ama rastgele pivotla olasılığı ihmal edilebilir.

---

## 3. Medyanların medyanı

Rastgelelik olmadan, **en kötü durumda** $O(n)$ mümkün mü? 1973'te Blum, Floyd, Pratt, Rivest ve Tarjan (BFPRT) "evet" dedi, ve yöntemleri iyi bir pivotu **deterministik** olarak buluyor:

1. Diziyi 5'li gruplara böl (son grup daha küçük olabilir).
2. Her grubun medyanını bul (5 elemanı ekleme sıralamasıyla sıralamak; sabit iş).
3. Bu $\lceil n/5 \rceil$ medyanın **medyanını**, aynı algoritmayla **özyinelemeyle** bul. Pivot bu.
4. Pivotla böl ve Quickselect gibi tek tarafa in.

Neden iyi bir pivot? Medyanların yarısı pivottan küçük ya da eşit; her birinin grubunda medyanın kendisi ve ondan küçük iki eleman daha var. Yani en az $3 \cdot \lceil \frac12 \lceil n/5 \rceil \rceil - O(1) \approx 3n/10$ eleman pivottan küçük ya da eşit; simetrik olarak en az $3n/10$ eleman büyük ya da eşit. Dolayısıyla bölmeden sonra her iki taraf da en fazla $7n/10$ elemanlı.

```
  Her sütun bir 5'li grup, içinde yukarıdan aşağı küçükten büyüğe sıralı.
  Sütunlar, medyanlarına (orta satır) göre soldan sağa sıralı.

     ≤  ≤  ≤  ≤  .  .  .
     ≤  ≤  ≤  ≤  .  .  .
     ≤  ≤  ≤ [P] ≥  ≥  ≥      ← medyanlar satırı; P medyanların medyanı
     .  .  .  ≥  ≥  ≥  ≥
     .  .  .  ≥  ≥  ≥  ≥

  ≤ ile işaretli sol üst blok P'den küçük ya da eşit, ≥ ile işaretli sağ alt blok
  büyük ya da eşit; ikisi de yaklaşık 3n/10 eleman.
```

Maliyet bağıntısı:

$$
T(n) \le T(n/5) + T(7n/10) + cn.
$$

$T(n/5)$ medyanların medyanını bulmak, $T(7n/10)$ en kötü taraf, $cn$ gruplama ve bölme. $\frac15 + \frac{7}{10} = \frac{9}{10} < 1$: iki özyinelemeli çağrının toplam boyutu $n$'den **küçük**. Özyineleme ağacının her seviyesi bir öncekinin en fazla $9/10$'u kadar iş yapıyor ve toplam $cn(1 + 0.9 + 0.81 + \dots) = 10cn = O(n)$. (Ders 6.13'teki Master teoremi iki farklı boyutlu alt problemi doğrudan ele almıyor; Akra–Bazzi teoremi ya da bu özyineleme ağacı argümanı gerekiyor.)

---

## 4. Ölçüm

Rastgele tamsayılarda medyan; karşılaştırma için `qsort` ile sıralayıp bakmak:

```
$ cc -std=c11 -O2 -Wall -Wextra secim.c -o secim && ./secim
n= 1000000 medyan=500622783  qsort 0.087 s | quickselect 500622783  0.0073 s  2.55 n kars | medyanlarin medyani 500622783  0.0210 s  8.46 n kars
n= 4000000 medyan=499649446  qsort 0.374 s | quickselect 499649446  0.0213 s  1.91 n kars | medyanlarin medyani 499649446  0.0835 s  8.52 n kars
n=16000000 medyan=499992679  qsort 1.628 s | quickselect 499992679  0.1607 s  4.97 n kars | medyanlarin medyani 499992679  0.3300 s  8.55 n kars
sirali, en buyuk: quickselect 3999999 1.98 n kars
sirali, en buyuk: medyanlarin medyani 3999999 7.10 n kars
```

(Üç yöntem her boyutta aynı medyanı buluyor; sanitizer'lı derleme temiz.)

- **Quickselect** 16 milyon elemanda `qsort`'tan **10 kat**, 4 milyonda 17 kat hızlı. Karşılaştırma sayısı ise denemeden denemeye çok oynuyor: $1.91n$, $2.55n$, $4.97n$. Aynı 4 milyonluk dizide 50 farklı rastgele pivot dizisiyle:

```
50 deneme: ortalama 3.32 n, en az 1.65 n, en cok 6.24 n
```

Ortalama $3.32n$, teorik $3.39n$'e çok yakın. Ama tek bir çalıştırma, ilk birkaç pivotun şansına göre beklentinin yarısı ya da iki katı olabiliyor: beklenen $O(n)$ bir **ortalama**, her çalıştırmanın garantisi değil.
- **Medyanların medyanı** her çalıştırmada aynı: $8.5n$ karşılaştırma, deterministik. Quickselect'in ortalamasından 2.5 kat fazla ve süresi 2–4 kat uzun; garantinin bedeli, pivotu bulmak için yapılan özyinelemeli iş.
- Sıralı dizide en büyük eleman: rastgele pivotlu quickselect için sıralı girdi özel değil ($1.98n$). İlk eleman pivotuyla (Ders 9.5) bu karesel olurdu.

Bu yüzden pratikte **introselect** (Musser, 1997; Ders 9.5'teki introsort'un kardeşi) kullanılıyor: quickselect gibi başla, ilerleme beklenenden yavaşsa (parça yeterince küçülmüyorsa) medyanların medyanına geç. C++'ın `std::nth_element`'i böyle.

---

## Alıştırmalar

**1** – Bir dizinin **en küçük $k$** elemanını (sırasız) bulmanın üç yolu: sıralayıp ilk $k$'yı almak, Ders 8.12'deki boyutu $k$ olan heap, ve quickselect ile $k$. elemanı bulup bölme sonrası sol tarafı almak. Her birinin karmaşıklığı ne? $n = 10^7$, $k = 10$ ve $k = 10^6$ için hangisini seçerdin?

**2** – Medyanların medyanında grupları 5 yerine **3**'lü yaparsan bağıntı ne olur? Neden doğrusal olmaz? **7**'li gruplar?

**3** – Hızlı sıralamada pivotu medyanların medyanıyla seçersek (her bölmede tam ortanca garantili) en kötü durum ne olur? Bu pratikte neden kullanılmıyor?

**4** – Quickselect'in en kötü durumu $\Theta(n^2)$. Pivotlar rastgele olduğu halde, $n = 10^6$'da karşılaştırma sayısının $20n$'yi aşma olasılığı hakkında ne söylenebilir? (Markov eşitsizliğini kullan; daha güçlü sınırlar da var.)

**5** – Akan veride (Ders 8.12, Alıştırma 4) medyanı iki heap ile $O(\log n)$'de güncelliyorduk. Bütün veri hazırken quickselect $O(n)$. 1 milyar sayı var ve belleğe sığmıyor; sadece **yaklaşık** medyan istiyorsun (gerçek medyandan en fazla %1 sıra uzaklıkta). Ne yaparsın?

<details>
<summary>Cevaplar</summary>

**1** – Sıralama: $O(n \log n)$, $k$'dan bağımsız. Heap: $O(n \log k)$ zaman, $O(k)$ bellek; ama elemanlar bir akış gibi bir kez okunabiliyor. Quickselect: beklenen $O(n)$, $k$'dan bağımsız, ve sonunda $a[0..k)$ en küçük $k$ eleman (sırasız). $k = 10$: heap, $n \log 10 \approx 3.3n$ ama karşılaştırmaların çoğu "kökten büyük mü?" testinde hemen bitiyor (Ders 8.12'de 1 milyon elemanda 5 en büyük için çok az iş); veriyi tek geçişte ve sabit bellekle okuması büyük avantaj. $k = 10^6$: quickselect, $n \log k = 20n$'e karşı $3.4n$ beklenen. İstenirse ilk $k$'yı sonra sıralamak $O(k \log k)$ ekliyor: C++'ın `std::partial_sort`'u heap, `std::nth_element` + `sort` quickselect yolu.

**2** – 3'lü gruplarda pivot, her tarafta en az $2 \cdot \frac12 \cdot \frac{n}{3} = n/3$ eleman bırakıyor; en kötü taraf $2n/3$. Bağıntı $T(n) \le T(n/3) + T(2n/3) + cn$. $\frac13 + \frac23 = 1$: alt problemlerin toplam boyutu $n$, her seviye yine $cn$ iş yapıyor ve $\log n$ seviye var: $T(n) = \Theta(n \log n)$, doğrusal değil. 7'li gruplar: her tarafta en az $4 \cdot \frac12 \cdot \frac{n}{7} = 2n/7$, en kötü taraf $5n/7$; $\frac17 + \frac57 = \frac67 < 1$, doğrusal. 5, işe yarayan en küçük tek grup boyutu. Büyük gruplar özyinelemeyi küçültüyor ama grup medyanlarını bulmak pahalılaşıyor; pratikte 5 ya da 7.

**3** – Her bölme diziyi tam ikiye böldüğü için $T(n) = 2T(n/2) + O(n) = O(n \log n)$, **en kötü durumda**. Ama medyanı bulmanın sabiti büyük (bu derste $8.5n$ karşılaştırma, bölmenin $n$'ine ek olarak): her seviyede yaklaşık 9–10 kat fazla iş. Toplam, rastgele pivotlu hızlı sıralamanın $1.39\, n \log_2 n$'inden birkaç kat yavaş. Introsort (Ders 9.5) aynı garantiyi, sadece işler kötüye gidince heapsort'a geçerek çok daha ucuza veriyor.

**4** – Karşılaştırma sayısı $C$ negatif olmayan bir rastgele değişken ve $E[C] \approx 3.39n$. Markov: $P(C \ge 20n) \le \frac{E[C]}{20n} \approx 0.17$. Bu çok zayıf bir sınır; gerçek olasılık çok daha küçük. Daha iyi bir argüman: $C \ge 20n$ olması için çok sayıda kötü pivotun arka arkaya gelmesi gerekiyor; her pivot $1/2$ olasılıkla iyi (kalan $\le 3n/4$) ve iyi pivotların sayısı Chernoff sınırlarıyla yoğunlaşıyor; olasılık $n$ ile üstel olarak küçülüyor. 50 denemede en kötüsü $6.24n$'di.

**5** – **Örneklem al**: veriden rastgele (ve tek geçişte, rezervuar örneklemesiyle) $m$ eleman seç, örneklemin medyanını quickselect ile bul. Örneklem medyanının gerçek sırası, $m$ büyüdükçe $n/2$'nin etrafında yoğunlaşıyor: sıra hatası yaklaşık $n/\sqrt{m}$ mertebesinde. %1 hata için $m$ birkaç on bin yeterli (sabit bellek). Daha güçlü garantili akış algoritmaları (Greenwald–Khanna, t-digest, KLL sketch) belirli bir hata sınırıyla bütün yüzdelikleri küçük bir bellekle tutuyor; veritabanlarının ve izleme sistemlerinin (`p99` gecikme ölçümleri) kullandığı yöntemler bunlar.

</details>

---

## Kaynaklar

- C. A. R. Hoare, "Algorithm 65: Find", *Communications of the ACM* 4(7), 1961: quickselect.
- Manuel Blum, Robert Floyd, Vaughan Pratt, Ronald Rivest ve Robert Tarjan, "Time Bounds for Selection", *Journal of Computer and System Sciences* 7(4), 1973.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 9: beklenen doğrusal zamanlı seçim ve en kötü durumda doğrusal seçim.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 5.3.3: minimum karşılaştırmalı seçim; quickselect'in $2(1 + \ln 2)n$ analizi.
- David Musser, "Introspective Sorting and Selection Algorithms", *Software: Practice and Experience* 27(8), 1997.

**Sıradaki ders:** String eşleme. KMP, Boyer–Moore ve Rabin–Karp; Faz 4'teki `strstr`'i yeniden yazma.
