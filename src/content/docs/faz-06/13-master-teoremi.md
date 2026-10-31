---
title: "6.13 Master teoremi"
description: "Böl-yönet algoritmalarının T(n) = aT(n/b) + f(n) bağıntısı; özyineleme ağacıyla açma ve düzey düzey maliyet; kritik üs log_b a ve üç durum (yapraklar baskın, dengeli, kök baskın); birleştirmeli sıralama, ikili arama, Karatsuba ve Strassen örnekleri; teoremin uygulanamadığı durumlar; birleştirmeli sıralamanın karşılaştırma sayısını ölçüp n log₂ n ile oranlayan ve üç durumu sayısal olarak gösteren C programı."
---

Ders 6.11'deki bağıntılar $n$'yi **birer birer** küçültüyordu: $T(n) = 2T(n-1) + 1$. Ama hızlı algoritmaların çoğu problemi **bir sabit oranda** küçültüyor: ikili arama yarıya, birleştirmeli sıralama iki yarıya. Bunlar **böl-yönet** (divide and conquer) algoritmaları ve maliyetleri farklı biçimde bir bağıntı:

$$
T(n) = a\, T\!\left(\frac{n}{b}\right) + f(n).
$$

- $a$: kaç alt problem
- $n/b$: her alt problemin büyüklüğü
- $f(n)$: bölmenin ve birleştirmenin maliyeti

Bu derste bu bağıntıyı açıp çözüyoruz, ve sonucu her böl-yönet algoritmasına tek bakışta uygulanan bir tabloya, **Master teoremine**, dönüştürüyoruz.

---

## 1. Birleştirmeli sıralama

Diziyi ikiye böl, her yarıyı özyinelemeyle sırala, iki sıralı yarıyı tek geçişte birleştir:

```c
static uint64_t cmps = 0;

static void merge_sort(int *a, int *tmp, int n) {
    if (n < 2) return;
    int h = n / 2;
    merge_sort(a, tmp, h);              // T(n/2)
    merge_sort(a + h, tmp, n - h);      // T(n/2)
    int i = 0, j = h, k = 0;            // birlestir: Theta(n)
    while (i < h && j < n) {
        cmps++;
        tmp[k++] = (a[i] <= a[j]) ? a[i++] : a[j++];
    }
    while (i < h) tmp[k++] = a[i++];
    while (j < n) tmp[k++] = a[j++];
    memcpy(a, tmp, n * sizeof *a);
}
```

Birleştirme her adımda iki yarının öndeki elemanlarından küçüğünü alıyor; en fazla $n - 1$ karşılaştırma. Bağıntı:

$$
T(n) = 2T\!\left(\frac{n}{2}\right) + \Theta(n), \qquad a = 2,\; b = 2,\; f(n) = n.
$$

---

## 2. Özyineleme ağacı

Ders 6.11'deki açmanın böl-yönet hali: her çağrıyı bir düğüm olarak çiz, düğümün yanına o çağrının **kendi** işini (alt çağrılar hariç) yaz.

```
düzey 0:                n                       toplam: n
                     /     \
düzey 1:          n/2       n/2                 toplam: n
                 /   \     /   \
düzey 2:       n/4  n/4  n/4  n/4               toplam: n
               ...                               ...
düzey k:    1  1  1  1  ...  1  1  1  (n tane)   toplam: n
```

Her düzeyde problem sayısı ikiye katlanıyor, büyüklük yarıya iniyor; çarpımları sabit kalıyor: her düzeyin toplam işi $n$. Kaç düzey? Büyüklük $n / 2^k = 1$ olunca, yani $k = \log_2 n$. Toplam:

$$
T(n) = n \cdot (\log_2 n + 1) = \Theta(n \log n).
$$

Ölçelim:

```
n=    1024 karsilastirma=     8937  n log2 n=    10240  oran=0.8728
n=   32768 karsilastirma=   449977  n log2 n=   491520  oran=0.9155
n= 1048576 karsilastirma= 19645432  n log2 n= 20971520  oran=0.9368
```

Oran bir sabite yaklaşıyor (rastgele girdilerde 1'in biraz altında; birleştirme çoğu zaman bir yarı bitince erken duruyor). Ders 6.12'nin limit testi: $\Theta(n \log n)$.

### Genel ağaç

$T(n) = aT(n/b) + f(n)$ için aynı çizim:

- Düzey $i$'de $a^i$ düğüm, her biri $n / b^i$ büyüklüğünde, toplam iş $a^i f(n / b^i)$.
- Düzey sayısı $\log_b n$.
- En alttaki **yaprak** sayısı $a^{\log_b n} = n^{\log_b a}$.

(Son eşitlik: $a^{\log_b n} = b^{\log_b a \cdot \log_b n} = n^{\log_b a}$.) Toplam:

$$
T(n) = \underbrace{\Theta\!\left(n^{\log_b a}\right)}_{\text{yapraklar}} + \sum_{i=0}^{\log_b n - 1} a^i f\!\left(\frac{n}{b^i}\right).
$$

Sonuç, iki kuvvetin yarışına bağlı: ağaç aşağı indikçe düğüm sayısı ($a^i$) artıyor, düğüm başına iş ($f(n/b^i)$) azalıyor. Hangisi kazanırsa toplamı o belirliyor.

---

## 3. Master teoremi

**Kritik üs** $c^* = \log_b a$. Yaprak sayısı $n^{c^*}$; $f(n)$'yi bununla karşılaştır.

**Teorem (Master).** $a \ge 1$, $b > 1$ sabitler ve $T(n) = aT(n/b) + f(n)$ olsun.

| Durum | Koşul | Sonuç | Sezgisi |
| --- | --- | --- | --- |
| 1 | $f(n) = O(n^{c^* - \epsilon})$, bir $\epsilon > 0$ için | $T(n) = \Theta(n^{c^*})$ | **yapraklar** baskın |
| 2 | $f(n) = \Theta(n^{c^*})$ | $T(n) = \Theta(n^{c^*} \log n)$ | her düzey eşit, $\log n$ düzey |
| 3 | $f(n) = \Omega(n^{c^* + \epsilon})$, ve $a f(n/b) \le k f(n)$ bir $k < 1$ için | $T(n) = \Theta(f(n))$ | **kök** baskın |

Durum 3'teki ek koşul (düzenlilik koşulu) iş miktarının aşağı indikçe gerçekten **azalmasını** garanti ediyor; $f$ bir polinomsa kendiliğinden sağlanıyor.

**Kanıt fikri.** $f(n) = n^d$ olsun. Düzey $i$'nin işi $a^i (n/b^i)^d = n^d \left(\frac{a}{b^d}\right)^i$: bir **geometrik seri**, oranı $r = \frac{a}{b^d}$ (Ders 6.10).

- $r > 1$ ($d < c^*$): seri artıyor, son terim baskın: yapraklar, $\Theta(n^{c^*})$.
- $r = 1$ ($d = c^*$): bütün terimler eşit, $\log_b n$ terim: $\Theta(n^d \log n)$.
- $r < 1$ ($d > c^*$): seri azalıyor, ilk terim baskın (geometrik serinin toplamı ilk terimin sabit katı): kök, $\Theta(n^d)$. $\blacksquare$

Bütün teorem, ağacın düzeylerinin bir geometrik seri olmasından ibaret. Programla üç durumu da görelim; $T(n) = aT(n/b) + n^d$'yi doğrudan özyinelemeyle hesaplayıp tahmin edilen fonksiyona oranlıyoruz:

```c
// T(n) = a T(n/b) + n^d, T(1) = 1 ; tamsayi bolme ile
static double T(int a, int b, double d, uint64_t n) {
    if (n <= 1) return 1;
    return a * T(a, b, d, n / b) + pow((double)n, d);
}
```

```
         n  8T(n/2)+n^2    2T(n/2)+n     T(n/2)+n
       256       1.9961       1.1250       1.9961
      4096       1.9998       1.0833       1.9998
     65536       2.0000       1.0625       2.0000
```

- $8T(n/2) + n^2$: $c^* = \log_2 8 = 3 > 2$. Durum 1, $\Theta(n^3)$. Oran ($T / n^3$) 2'ye yaklaşıyor.
- $2T(n/2) + n$: $c^* = 1 = d$. Durum 2, $\Theta(n \log n)$. Oran ($T / n\log_2 n$) 1'e iniyor (yavaşça; fark $\frac{1}{\log_2 n}$).
- $T(n/2) + n$: $c^* = 0 < 1$. Durum 3, $\Theta(n)$. Oran ($T / n$) 2'ye yaklaşıyor: $n + n/2 + n/4 + \dots = 2n$.

---

## 4. Örnekler

| Algoritma | Bağıntı | $c^*$ | Durum | Sonuç |
| --- | --- | --- | --- | --- |
| İkili arama (Ders 2.10) | $T(n/2) + 1$ | 0 | 2 | $\Theta(\log n)$ |
| Hızlı üs alma (Ders 2.9) | $T(n/2) + 1$ | 0 | 2 | $\Theta(\log n)$ |
| Birleştirmeli sıralama | $2T(n/2) + n$ | 1 | 2 | $\Theta(n \log n)$ |
| Okul çarpması, böl-yönet | $4T(n/2) + n$ | 2 | 1 | $\Theta(n^2)$ |
| Karatsuba çarpması | $3T(n/2) + n$ | $\log_2 3 \approx 1.585$ | 1 | $\Theta(n^{1.585})$ |
| Matris çarpımı, böl-yönet | $8T(n/2) + n^2$ | 3 | 1 | $\Theta(n^3)$ |
| Strassen | $7T(n/2) + n^2$ | $\log_2 7 \approx 2.807$ | 1 | $\Theta(n^{2.807})$ |
| Ortanca bulma (median of medians) | yaklaşık $T(n/5) + T(7n/10) + n$ | — | — | $\Theta(n)$ |

Karatsuba ve Strassen satırları teoremin en güzel dersi: **alt problem sayısını bir azaltmak** ($4 \to 3$, $8 \to 7$) kritik üssü düşürüyor ve büyük $n$'de dev bir kazanç sağlıyor. Ek toplamalar ($f(n)$) kritik üssün altında kaldığı sürece önemsiz. Karatsuba'yı Ders 12.3'te büyük tamsayılar için yazacağız: 1000 basamaklı iki sayıyı okul yöntemiyle çarpmak $10^6$, Karatsuba ile kabaca $5.7 \cdot 10^4$ basamak çarpması.

---

## 5. Teoremin sınırları

Master teoremi her böl-yönet bağıntısını çözmüyor:

- **Alt problemler eşit değilse**: $T(n) = T(n/3) + T(2n/3) + n$. Ağaç dengesiz; teorem $aT(n/b)$ biçimini istiyor. Ağaç yöntemi hâlâ çalışıyor: her düzeyin toplamı en fazla $n$, en uzun yol $\log_{3/2} n$ düzey; $\Theta(n \log n)$. Daha genel araç: Akra–Bazzi teoremi.
- **Durumlar arasında boşluk**: $T(n) = 2T(n/2) + n \log n$. $f(n) = n \log n$, $n^1$'den büyük ama hiçbir $\epsilon$ için $n^{1+\epsilon}$ kadar değil; ne durum 2 ne durum 3. Ağaçla: düzey $i$'nin işi $n \log(n / 2^i) = n(\log n - i)$, toplam $\Theta(n \log^2 n)$. (Teoremin genişletilmiş hali, $f(n) = \Theta(n^{c^*} \log^k n)$ için $\Theta(n^{c^*} \log^{k+1} n)$ diyor.)
- **$n$ bir sabit kadar küçülüyorsa**: $T(n) = 2T(n-1) + 1$. Böl-yönet değil; Ders 6.11'in yöntemleri.

Tamsayı bölmesi ($\lfloor n/2 \rfloor$ ve $\lceil n/2 \rceil$) sonucu değiştirmiyor: Bölüm 3'teki program tamsayı bölmesi kullandı ve oranlar yine beklenen sabitlere yaklaştı.

---

## Alıştırmalar

**1** – Master teoremiyle çöz: (a) $T(n) = 9T(n/3) + n$ (b) $T(n) = T(2n/3) + 1$ (c) $T(n) = 3T(n/4) + n \log n$ (d) $T(n) = 2T(n/4) + \sqrt{n}$

**2** – $T(n) = 2T(\sqrt n) + \log n$'yi değişken değiştirerek çöz: $m = \log_2 n$ ve $S(m) = T(2^m)$ dersen $S$ için bağıntı ne olur?

**3** – Birleştirmeli sıralamanın sıralı bir dizide kaç karşılaştırma yaptığını ölç. Ters sıralı dizide? Sonuçları $\frac{n}{2}\log_2 n$ ile karşılaştır. En kötü ve en iyi durum aynı $\Theta$ sınıfında mı?

**4** – Diziyi ikiye değil **üçe** bölen bir birleştirmeli sıralamanın bağıntısını yaz. Asimptotik olarak daha mı hızlı? Bölümleri $k$'ya çıkarmak neden sınırsız kazanç sağlamıyor?

**5** – Hızlı üs alma (Ders 2.9) $x^n$'yi $T(n) = T(n/2) + O(1)$ çarpmayla hesaplıyor. Sayılar büyüdükçe (Faz 12'deki büyük tamsayılar) çarpmanın maliyeti sabit değil. $x$ tek basamaklıysa $x^n$ yaklaşık $n$ basamaklı; okul çarpmasıyla ($\Theta(m^2)$, $m$ basamak) toplam maliyet ne olur?

<details>
<summary>Cevaplar</summary>

**1** – (a) $c^* = \log_3 9 = 2$, $f = n = O(n^{2-1})$: durum 1, $\Theta(n^2)$. (b) $a = 1$, $b = 3/2$, $c^* = 0$, $f = 1 = \Theta(n^0)$: durum 2, $\Theta(\log n)$. (c) $c^* = \log_4 3 \approx 0.79$, $f = n \log n = \Omega(n^{0.79 + 0.2})$; düzenlilik: $3 \cdot \frac{n}{4}\log\frac{n}{4} \le \frac{3}{4} n \log n$ ✓. Durum 3, $\Theta(n \log n)$. (d) $c^* = \log_4 2 = \frac{1}{2}$, $f = \sqrt n = \Theta(n^{1/2})$: durum 2, $\Theta(\sqrt n \log n)$.

**2** – $T(2^m) = 2T(2^{m/2}) + m$, yani $S(m) = 2S(m/2) + m$: birleştirmeli sıralamanın bağıntısı, $S(m) = \Theta(m \log m)$. Geri dönünce $T(n) = \Theta(\log n \cdot \log\log n)$. Değişken değiştirmek, Master teoreminin biçimine uymayan bir bağıntıyı uyan bir bağıntıya çeviriyor.

**3** – Sıralı dizide her birleştirmede sol yarı önce bitiyor: tam $\frac{n}{2}$ karşılaştırma, toplam $\frac{n}{2}\log_2 n$. Ters sıralıda da aynı (bu sefer sağ yarı önce bitiyor). Rastgele dizide $n \log_2 n$'ye daha yakın (Bölüm 2'deki oran ~0.94). En kötü durum $n \log_2 n - n + 1$ civarında. Hepsi $\Theta(n \log n)$; birleştirmeli sıralamanın en iyi ve en kötü durumu aynı sınıfta. Ekleme sıralamasında öyle değil ($\Theta(n)$ ile $\Theta(n^2)$).

**4** – $T(n) = 3T(n/3) + cn$: $c^* = 1$, durum 2, yine $\Theta(n \log n)$. Düzey sayısı $\log_3 n$'ye iniyor ($\log_2 n$'nin $0.63$ katı) ama her düzeyde üç sıralı dizinin en küçüğünü bulmak için iki karşılaştırma gerekiyor; sabit değişiyor, sınıf değişmiyor. $k$ parçaya bölünce düzey sayısı $\log_k n$ ama birleştirmenin maliyeti $k$ ile artıyor ($k$ elemanın en küçüğünü bulmak). Ders 6.12'deki ilke: bölümler sabit faktör kazandırıyor. Karşılaştırmayla sıralamanın $\Omega(n \log n)$'den hızlı olamayacağını Faz 9'da kanıtlayacağız.

**5** – Adım $i$'de sayılar yaklaşık $n / 2^i$ basamaklı (sondan geriye: son karelemede $n/2$ basamaklı iki sayı). Karesini almanın maliyeti $(n/2^i)^2$. $T(n) = T(n/2) + \Theta(n^2)$: $c^* = 0$, durum 3, $\Theta(n^2)$. Son çarpma bütün maliyete hâkim; önceki bütün karelemeler toplamda onun sabit katı. Karatsuba ile $\Theta(n^{1.585})$. Ders: Master teoremi "bir adım" ne demek olduğunu sormuyor; $f(n)$'ye doğru maliyeti koymak sana kalmış.

</details>

---

## Kaynaklar

- Thomas Cormen ve diğ., *Introduction to Algorithms* (4. baskı), Bölüm 4: böl-yönet, özyineleme ağacı ve Master teoremi.
- Jon Bentley, Dorothea Haken & James Saxe, "A General Method for Solving Divide-and-Conquer Recurrences", *SIGACT News* 12(3), 1980: teoremin ilk biçimi.
- Anatolii Karatsuba & Yuri Ofman, "Multiplication of Multidigit Numbers on Automata", 1962.

**Sıradaki ders:** Kombinatorik. Permütasyon, kombinasyon, Pascal üçgeni, ve $\binom{n}{k}$'yı taşmadan hesaplamak.
