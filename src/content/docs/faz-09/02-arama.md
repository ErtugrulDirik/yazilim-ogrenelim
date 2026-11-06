---
title: "9.2 Arama"
description: "Doğrusal arama ve sıralı dizide ikili arama; aralık değişmeziyle doğru yazılmış alt sınır (lower bound) ve yarı açık [lo, hi) aralığı; (lo + hi) / 2 taşma hatası: 2³¹ − 1 elemanlı sanal bir dizide UBSan'ın yakaladığı işaretli taşma ve -O0 ile -O2'de iki farklı sonsuz döngü; lo + (hi − lo) / 2 düzeltmesi ve Java'nın 2006'daki hatası; Apple M2'de 16 elemandan 16 milyona sorgu başına süre: doğrusal, ikili ve dalsız ikili arama, cache'ten taşınca ikili aramanın yavaşlaması."
---

Arama, en temel algoritmik soru: bir değer bir kümede var mı, varsa nerede? Faz 8'in büyük kısmı bu soruya verilmiş cevaplardı: hash tabloları (Ders 8.14–8.15), arama ağaçları (Ders 8.8–8.11), trie'ler (Ders 8.17). Bu ders en yalın iki cevaba dönüyor: düz bir dizide **doğrusal** arama ve **sıralı** bir dizide **ikili** arama. İkili arama Ders 4.2'den beri birkaç kez karşımıza çıktı. Ama Jon Bentley'nin ünlü gözlemi şu: profesyonel programcılara ikili aramayı yazdırdığında, %90'ı hatalı kod yazıyor. Bu derste hem neden zor olduğunu hem de onlarca yıl fark edilmeyen bir hatasını göreceğiz.

---

## 1. Doğrusal arama

Ders 9.1'de saydık: aranan yoksa $n$, varsa ortalama $(n+1)/2$ karşılaştırma. Sıralanmamış veri için yapılabilecek en iyi şey bu: her elemana bakmadan bir elemanın **olmadığını** bilemezsin. Avantajları: veri sıralı olmak zorunda değil, kod üç satır, ve bellek erişimi tamamen ardışık (Ders 7.24'ün en dostça erişim kalıbı).

Sıralı bir dizide doğrusal aramanın da bir anlamı var: aranandan büyük ya da eşit ilk elemana gelince durabiliriz.

```c
/* Ilk a[i] >= x olan i (yoksa n). Siralanmis dizide x'in "eklenecegi yer". */
static size_t dogrusal(const int *a, size_t n, int x) {
    size_t i = 0;
    while (i < n && a[i] < x) i++;
    return i;
}
```

Bu fonksiyonun döndürdüğü şey bir **konum**: `x`'in dizideki yeri (varsa) ya da diziyi sıralı tutarak ekleneceği yer (yoksa). C++'ta `std::lower_bound`, Python'da `bisect_left`. "Var mı?" sorusu buradan çıkıyor: `i < n && a[i] == x`. Bu tanım, "bulamazsa -1 döndür" tasarımından daha kullanışlı: ekleme yeri, aralık sorguları (Alıştırma 1) ve tekrarlı elemanlar için doğru cevap veriyor.

---

## 2. İkili arama ve değişmezi

Sıralı bir dizide ortadaki elemana bakınca dizinin yarısını eleyebiliyoruz. Her adımda kalan aralık yarıya indiği için $\lceil \log_2(n+1) \rceil$ adım. 1 milyar elemanda 30.

Zorluk ayrıntılarda: aralığın uçları kapalı mı açık mı, `orta`'nın yuvarlanması, döngünün koşulu `<` mü `<=` mü, ve güncellemede `orta` mı `orta + 1` mi. Her biri bir eleman kaydırma (off-by-one) hatası ya da sonsuz döngü fırsatı. Çözüm Ders 9.1'deki gibi: önce **değişmezi** yaz, kodu ondan türet.

```c
/* DEGISMEZ: a[0..lo) < x  ve  a[hi..n) >= x. Aralik [lo, hi) bos kalinca lo cevap. */
static size_t alt_sinir(const int *a, size_t n, int x) {
    size_t lo = 0, hi = n;
    while (lo < hi) {
        size_t orta = lo + (hi - lo) / 2;
        if (a[orta] < x) lo = orta + 1; else hi = orta;
    }
    return lo;
}
```

Değişmez: $a[0..lo)$'daki her eleman $x$'ten **küçük**, $a[hi..n)$'deki her eleman $x$'ten **büyük ya da eşit**. Arasındaki $[lo, hi)$ henüz bilinmeyen bölge.

```
  0          lo              hi           n
  [  < x  ...  |  bilinmiyor  |  >= x  ...  ]
```

- **Başlangıç**: $lo = 0$, $hi = n$: iki bilinen bölge de boş, değişmez kendiliğinden doğru.
- **Koruma**: $lo \le orta < hi$. $a[orta] < x$ ise dizi sıralı olduğu için $a[0..orta]$'nın hepsi $< x$: `lo = orta + 1` değişmezi koruyor. Değilse $a[orta] \ge x$ ve $a[orta..n)$'nin hepsi $\ge x$: `hi = orta` koruyor.
- **Sonlanma**: bilinmeyen bölgenin uzunluğu $hi - lo$ her turda kesin azalıyor (`orta + 1 > lo` ve `orta < hi`) ve en az yarıya iniyor. Döngü $lo = hi$'de bitiyor; değişmez, $a[lo]$'nun $x$'ten büyük ya da eşit **ilk** eleman olduğunu söylüyor (ya da $lo = n$ ise hiçbiri).

Bu kalıptaki iki seçim değişmezden doğrudan çıkıyor: **yarı açık** aralık $[lo, hi)$ (Dijkstra'nın önerisi; boş aralık $lo = hi$ ile, uzunluk $hi - lo$ ile ifade ediliyor), ve **sadece iki dal**: eşitlik durumu ayrıca kontrol edilmiyor, `>=` dalına dahil. Üç dallı sürüm (`<`, `>`, `==` ise dön) tekrarlı elemanlardan rastgele birini bulur; iki dallı sürüm her zaman **ilkini**.

`size_t` kullandık: dizi indeksleri negatif değil, ve 64 bitlik `size_t` herhangi bir dizinin boyutunu tutabiliyor.

---

## 3. `(lo + hi) / 2` hatası

Yukarıdaki kodda `orta = lo + (hi - lo) / 2` yazdık. Matematiksel olarak `(lo + hi) / 2` ile aynı. Neden daha karmaşık halini seçtik?

1986'da Bentley'nin *Programming Pearls*'ü ikili aramayı `int` indekslerle ve `(lo + hi) / 2` ile yazdı; Java'nın `Arrays.binarySearch`'ü bu kodu temel aldı. 2006'da Joshua Bloch, Google'da `Arrays.binarySearch`'ün **çöktüğünü** bildirdi: $2^{30}$'dan fazla elemanlı bir dizide `lo + hi`, `int`'in en büyük değeri $2^{31} - 1$'i aşıyordu. Hata 20 yıl boyunca, ders kitaplarında ve kütüphanelerde fark edilmemişti; çünkü 1986'da bir milyar elemanlı dizi yoktu.

C'de işaretli taşma Java'daki gibi negatif bir sayıya sarmakla kalmıyor, **tanımsız davranış** (Ders 2.12, 3.8). Göstermek için 2 milyar elemanlı bir dizi ayırmamıza gerek yok; sıralı bir "sanal dizi" yeter: `f(i) = i`.

```c
/* (lo + hi) / 2 tasmasi. Dizi yerine "sanal dizi": f(i) = i, i in [0, n). Bellek gerekmiyor. */
#include <limits.h>
#include <stdio.h>

static int f(int i) { return i; }                  /* sirali, dev bir dizi gibi */

static int ara_hatali(int n, int x) {               /* [lo, hi] kapali aralik */
    int lo = 0, hi = n - 1, tur = 0;
    while (lo <= hi) {
        if (++tur > 100) { printf("  100 turda bitmedi: lo=%d hi=%d\n", lo, hi); return -2; }
        int orta = (lo + hi) / 2;                   /* lo + hi > INT_MAX olabilir! */
        if (tur > 30) printf("  tur %d: lo=%d hi=%d orta=%d\n", tur, lo, hi, orta);
        if (f(orta) < x) lo = orta + 1; else if (f(orta) > x) hi = orta - 1; else return orta;
    }
    return -1;
}

static int ara_dogru(int n, int x) {
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int orta = lo + (hi - lo) / 2;              /* hi - lo hic tasmaz */
        if (f(orta) < x) lo = orta + 1; else if (f(orta) > x) hi = orta - 1; else return orta;
    }
    return -1;
}

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);
    int n = INT_MAX;                                /* 2^31 - 1 elemanli sanal dizi */
    printf("dogru : ara(%d) = %d\n", 2000000000, ara_dogru(n, 2000000000));
    printf("hatali: ara(%d) = %d\n", 2000000000, ara_hatali(n, 2000000000));
    return 0;
}
```

(İki sürüm de Bentley'nin klasik, kapalı aralıklı ve üç dallı biçiminde. Hatalı sürüme 100 turluk bir emniyet sınırı ve 30. turdan sonra iz satırları ekledik; doğru bir ikili arama $2^{31}$ elemanda en fazla 31 tur döner. `setvbuf` çıktıyı tamponsuz yapıyor ki program takılsa bile yazdıkları görünsün.)

```
$ cc -std=c11 -O0 -g -Wall -fsanitize=undefined tasma.c -o tasma && ./tasma
dogru : ara(2000000000) = 2000000000
tasma.c:11:24: runtime error: signed integer overflow: 1073741824 + 2147483646 cannot be represented in type 'int'
SUMMARY: UndefinedBehaviorSanitizer: undefined-behavior tasma.c:11:24 
  tur 31: lo=-715827882 hi=2147483646 orta=715827882
  tur 32: lo=715827883 hi=2147483646 orta=-715827883
  tur 33: lo=-715827882 hi=2147483646 orta=715827882
  ...
  100 turda bitmedi: lo=-715827882 hi=2147483646
hatali: ara(2000000000) = -2
```

İlk turda $lo = 0$, $hi = 2^{31} - 2$, toplam sığıyor. İkinci turda $lo = 2^{30}$ ve `lo + hi` $= 3 \cdot 2^{30} - 2$, sığmıyor: UBSan tam o satırı ve değerleri gösteriyor. `-O0`'da toplam negatif bir sayıya sarıyor, `orta` negatif oluyor, `lo` negatif oluyor, ve döngü iki durum arasında sonsuza kadar gidip geliyor.

Aynı program `-O2` ile ve sanitizer'sız:

```
$ cc -std=c11 -O2 -Wall tasma.c -o tasma2 && ./tasma2
dogru : ara(2000000000) = 2000000000
  tur 31: lo=1073741824 hi=2147483646 orta=1073741823
  tur 32: lo=1073741824 hi=2147483646 orta=1073741823
  ...
  100 turda bitmedi: lo=1073741824 hi=2147483646
hatali: ara(2000000000) = -2
```

**Farklı** bir sonsuz döngü: `orta`, `lo`'dan küçük bir pozitif sayı ve `lo` hiç ilerlemiyor. Derleyici, işaretli taşmanın olamayacağını varsayıp `(lo + hi) / 2`'yi farklı bir komut dizisine çevirmiş; ikisi de standarda uygun, çünkü taşma olduğu anda programın hiçbir davranışı garanti değil. Ders 2.12'deki "tanımsız davranış her şey olabilir"in somut hali: aynı kaynak, iki derleme, iki farklı yanlış sonuç.

Düzeltmeler:

- `lo + (hi - lo) / 2`: $0 \le lo \le hi$ olduğu sürece `hi - lo` hiç taşmaz. Bu dersin seçimi.
- `size_t` (64 bit) indeksler: $2^{63}$ elemana kadar `lo + hi` taşmaz. Ama `size_t` ile kapalı aralık kullanırken `hi = orta - 1` ifadesi `orta = 0`'da $2^{64} - 1$'e sarar; yarı açık aralık bu sorunu da ortadan kaldırıyor.
- Java'nın düzeltmesi: `(lo + hi) >>> 1`, işaretsiz sağa kaydırma. C'de karşılığı `((unsigned)lo + (unsigned)hi) >> 1`.

---

## 4. Ölçüm

Üç arama, $n$ = 16'dan 16 milyona: doğrusal (sıralı dizide erken duran), ikili (`alt_sinir`) ve **dalsız** ikili:

```c
/* Dalsiz: aralik uzunlugu her adimda yariya iner; karsilastirma sonucu sadece bir toplamada kullanilir */
static size_t alt_sinir_dalsiz(const int *a, size_t n, int x) {
    const int *taban = a;
    while (n > 1) {
        size_t yari = n / 2;
        taban = (taban[yari - 1] < x) ? taban + yari : taban;   /* derleyici csel uretir (Ders 7.22) */
        n -= yari;
    }
    return (size_t)(taban - a) + (n == 1 && *taban < x);
}
```

Dalsız sürüm, kalan aralığın uzunluğunu karşılaştırma sonucundan bağımsız olarak her adımda yarıya indiriyor; karşılaştırma sadece aralığın **başlangıcını** seçiyor. Döngü her girdi için aynı sayıda dönüyor, ve `?:` bir dal yerine koşullu seçme komutuna (`csel`, Ders 7.22) dönüşüyor. Rastgele bir sorguda ikili aramanın her dalı %50 olasılıkla yanlış tahmin ediliyor; dalsız sürümde tahmin edilecek dal yok.

Dizi çift sayılar ($a[i] = 2i$), sorgular $[0, 2n]$'de rastgele (yarısı dizide var), sorgu başına süre; üç yöntemin aynı cevabı verdiği her $n$ için 1000 sorguda kontrol ediliyor:

```
$ cc -std=c11 -O2 -Wall -Wextra arama.c -o arama && ./arama
         n     dogrusal        ikili       dalsiz   (ns/sorgu)
        16          9.3          3.9          3.1
        64         17.8          5.2          5.2
       256         56.0          7.2          6.9
      1024        176.8         10.3          9.8
      4096        663.2         13.5         11.7
     16384       2663.5         17.1         14.7
     65536            -         33.7         24.9
    262144            -         51.8         37.1
   1048576            -         64.2         49.1
   4194304            -        130.2        115.4
  16777216            -        372.5        254.3
```

(Sanitizer'lı derleme temiz.)

- **Doğrusal arama** her $n$ 4 katına çıkınca 4 kat yavaşlıyor: $O(n)$. Bu makinede 16 elemanda bile ikili aramadan yavaş; dizinin ortasındaki çıkış noktası her sorguda farklı olduğu için döngünün çıkış dalı her seferinde yanlış tahmin ediliyor. Çok küçük dizilerde doğrusal aramanın daha hızlı olduğu söylenir; SIMD ile birkaç elemanı birden karşılaştıran bir doğrusal arama (Faz 11) için bu doğru, bu basit döngü için değil.
- **İkili arama**, $n$ 4 katına çıkınca 2 karşılaştırma daha yapıyor; dizi cache'e sığdığı sürece ($n \le 16384$, 64 KB) her adım 2–3 ns ekliyor. Dizi büyüyüp önce L2'den sonra RAM'e taşınca adım başına maliyet artıyor: 16 milyon elemanda (64 MB) 372 ns. Son adımlardaki her erişim farklı bir cache satırına, büyük ihtimalle RAM'e gidiyor (Ders 7.24'teki 100 ns'lik gecikme) ve her biri bir öncekinin sonucuna bağlı.
- **Dalsız sürüm** her boyutta biraz daha hızlı, büyük dizilerde %30'a kadar. Dal yanlış tahminlerinin her biri 10–15 döngü; dalsız sürümde onlar yok.

$O(\log n)$ olan bir algoritmanın 16 elemandan 16 milyona sorgu başına süresi 100 kat arttı, $\log$ ise sadece 6 kat. Kalan fark bellek hiyerarşisi. Büyük sıralı dizilerde ikili aramayı hızlandırmanın yolu veriyi yeniden düzenlemek: Ders 8.11'deki B-ağacı gibi bloklar, ya da dizinin "ağaç sırasına" (Eytzinger düzeni; ilk seviyeler dizinin başında, sık erişilenler aynı cache satırlarında) dizilmesi.

---

## Alıştırmalar

**1** – `ust_sinir(a, n, x)`: $a[i] > x$ olan ilk $i$. `alt_sinir`'dan tek bir karakteri değiştirerek yaz ve değişmezini söyle. Sıralı bir dizide $x$'in kaç kez geçtiğini bu iki fonksiyonla $O(\log n)$'de nasıl bulursun?

**2** – İkili arama sadece dizilerde değil, herhangi bir **monoton** yüklemde çalışıyor: $p(i)$, bir $i_0$'dan önce yanlış, sonra doğruysa ilk doğru noktayı bulmak. Bunu kullanarak bir `uint32_t` için $\lfloor \sqrt{x} \rfloor$'u hesapla (Ders 2.10'u hatırla). Yüklem ne, aralık ne, ve çarpma taşabilir mi?

**3** – **Üstel arama** (exponential/galloping search): sonu bilinmeyen (ya da çok büyük) sıralı bir dizide, aranan başa yakınsa, önce $1, 2, 4, 8, \dots$ konumlarına bakıp aralığı bul, sonra o aralıkta ikili ara. Aranan $i$. konumdaysa kaç karşılaştırma yapar? Nerede kullanılıyor?

**4** – Bölüm 3'teki hatanın 20 yıl fark edilmemesinin sebebi neydi? Bu tür bir hatayı **test** ile yakalamak için ne gerekirdi? UBSan'lı bir test ne değiştirirdi?

**5** – **İnterpolasyon araması**: ortaya değil, değerin aralıktaki **orantılı** konumuna bak: `orta = lo + (x - a[lo]) * (hi - lo) / (a[hi] - a[lo])`. Değerler düzgün dağılmışsa beklenen adım sayısı $O(\log \log n)$. 1 milyar düzgün dağılmış elemanda bu yaklaşık kaç adım? En kötü durumu ne, ve hangi girdi onu üretir? Formülde hangi taşma tehlikeleri var?

<details>
<summary>Cevaplar</summary>

**1** – Koşulu `a[orta] < x`'ten `a[orta] <= x`'e çevir. Değişmez: $a[0..lo)$'daki her eleman $\le x$, $a[hi..n)$'deki her eleman $> x$. Döngü sonunda $lo$, $x$'ten büyük ilk elemanın konumu. $x$'in tekrar sayısı `ust_sinir(a, n, x) - alt_sinir(a, n, x)`: iki ikili arama, $O(\log n)$, kaç tekrar olursa olsun. `alt_sinir` ile `ust_sinir` arasındaki yarı açık aralık tam olarak $x$'e eşit elemanlar: Ders 8.8'deki aralık sorgusunun dizi hali.

**2** – Yüklem $p(r) = (r + 1)^2 > x$: $r$ büyüdükçe yanlıştan doğruya geçiyor ve ilk doğru olduğu $r$, $\lfloor \sqrt{x} \rfloor$. Ya da eşdeğer olarak "$r^2 \le x$ olan en büyük $r$". Aralık $[0, 65536)$ yeter, çünkü $\sqrt{2^{32} - 1} < 65536$. Çarpma taşabilir: $r = 65535$'te $r^2$ `uint32_t`'ye sığıyor ama $(r+1)^2 = 2^{32}$ sığmıyor; karşılaştırmayı `uint64_t`'de yapmak (`(uint64_t)r * r <= x`) ya da `r <= x / r` biçiminde yazmak gerekiyor. Ders 2.10'daki tamsayı karekök Newton yöntemiyle daha az adımda yakınsıyordu; ikili arama daha yavaş (16 adım) ama doğruluğu değişmezle apaçık.

**3** – $2^k > i$ olan ilk $k$ için $\lceil \log_2(i + 1) \rceil$ karşılaştırma aralığı buluyor, sonra boyutu $2^{k-1}$ olan aralıkta ikili arama, bir o kadar daha: toplam yaklaşık $2 \log_2 i$, dizinin boyutundan **bağımsız**. Aranan başa yakınsa ikili aramadan çok daha hızlı; sonu bilinmeyen akışlarda tek seçenek. Kullanım: Timsort'un (Python ve Java'nın sıralaması) birleştirme adımı, bir dizinin diğerinden ne kadar elemanı "galloping" ile atlayabileceğini bu yöntemle buluyor; sıralı listelerin kesişimini hesaplayan arama motoru algoritmaları da öyle.

**4** – Hata sadece $n > 2^{30}$'da tetikleniyordu; 1986'da bu kadar büyük bir dizi ne belleğe sığıyordu ne de 32 bitlik makinelerde adreslenebiliyordu. Kod "doğru" kabul edildi çünkü test edilebilen her girdide doğruydu. Testle yakalamak için tam sınırda, $2^{30}$'dan büyük bir dizi gerekirdi; ya da bu dersteki gibi indeksleri dizi erişiminden ayırıp sanal bir diziyle denemek. UBSan'lı bir test, taşmayı sonucun yanlış olmasını beklemeden, **olduğu anda** raporluyor: Bölüm 3'te ilk taşmada satır numarasıyla. Ama yine de o girdinin denenmesi gerekiyor. Ders 9.1'in dersi: ispat (burada, "`lo + hi` hiç taşar mı?" sorusunu sormak) test edilmeyen girdileri de kapsıyor.

**5** – $\log_2 \log_2 10^9 \approx \log_2 29.9 \approx 4.9$: yaklaşık 5 adım, ikili aramanın 30'una karşı. En kötü durum $O(n)$: değerler çok dengesiz dağılmışsa, örneğin $a = [1, 2, 3, \dots, 999, 10^{18}]$ ve aranan 998: tahmin her seferinde aralığın başına düşüyor ve aralık her adımda sadece bir eleman küçülüyor. Taşma: `(x - a[lo]) * (hi - lo)` çarpımı kolayca taşıyor (64 bitlik değerler ve büyük indekslerde); `x - a[lo]` işaretli çıkarmada da taşabilir; `a[hi] - a[lo] = 0` ise sıfıra bölme. Pratik sürümler hesabı `double`'da yapıyor ya da birkaç interpolasyon adımından sonra ikili aramaya geçiyor.

</details>

---

## Kaynaklar

- Jon Bentley, *Programming Pearls* (2. baskı), Bölüm 4 ve 9: ikili aramanın doğruluğu ve hızlandırılması.
- Joshua Bloch, "Extra, Extra – Read All About It: Nearly All Binary Searches and Mergesorts are Broken", Google Research Blog, 2006.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.2.1: sıralı tabloda arama, ikili arama ve interpolasyon.
- Edsger Dijkstra, "Why numbering should start at zero", EWD831, 1982: yarı açık aralıklar.
- Paul-Virak Khuong ve Pat Morin, "Array Layouts for Comparison-Based Searching", *ACM Journal of Experimental Algorithmics* 22, 2017: dalsız ikili arama ve Eytzinger düzeni.

**Sıradaki ders:** Basit sıralamalar. Seçme, ekleme ve kabarcık sıralaması; iz sürme tablosuyla adım adım, kararlılık.
