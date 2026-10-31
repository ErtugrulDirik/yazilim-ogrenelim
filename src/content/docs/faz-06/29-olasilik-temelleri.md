---
title: "6.29 Olasılık temelleri"
description: "Örnek uzay, olay ve olasılık aksiyomları; eşit olası sonuçlarda sayma; koşullu olasılık, bağımsızlık ve Bayes teoremi (yanlış pozitif paradoksu); rastgele değişken ve beklenen değer; beklenen değerin doğrusallığı ve gösterge değişkenleri; kupon toplayıcı problemi ve n·Hₙ; zincirli hash tablosunda başarısız ve başarılı aramanın beklenen maliyeti (α ve 1 + α/2); splitmix64 üreteci, rand() % n sapması ve bütün sonuçları simülasyonla doğrulayan C programı."
---

Ders 6.15'te doğum günü paradoksunu, Ders 6.20'de Miller–Rabin'in "bileşik bir sayının geçme olasılığı en fazla $\frac14$" garantisini gördük, ve olasılık kelimesini tanımlamadan kullandık. Bu ders o boşluğu dolduruyor.

Olasılık, algoritma analizinin ikinci büyük aleti. Ders 6.12'deki $O$, en kötü durumu konuşuyordu; ama hash tabloları, quicksort, Miller–Rabin ve skip list gibi pek çok önemli algoritmanın en kötü durumu kötü, **ortalama** durumu mükemmel. "Ortalama"yı kesin konuşmanın dili beklenen değer. Faz 8'deki hash tablosu ve Faz 9'daki rastgeleleştirilmiş algoritmalar bu derse yaslanıyor.

---

## 1. Örnek uzay ve olasılık

- **Örnek uzay** $\Omega$: bir deneyin olası bütün sonuçlarının kümesi. İki zar: $\Omega = \{1..6\} \times \{1..6\}$, 36 sonuç (Ders 6.5, kartezyen çarpım).
- **Olay**: $\Omega$'nın bir alt kümesi. "Toplam 7": $\{(1,6), (2,5), \dots, (6,1)\}$, 6 sonuç.
- **Olasılık** $P$: her olaya $[0, 1]$'de bir sayı atayan fonksiyon. Üç aksiyom (Kolmogorov):
  1. $P(A) \ge 0$
  2. $P(\Omega) = 1$
  3. $A \cap B = \emptyset$ ise $P(A \cup B) = P(A) + P(B)$

Üçüncüsü Ders 6.14'teki toplama ilkesinin olasılık hali; kesişen olaylar için Ders 6.15'teki içerme–dışlama: $P(A \cup B) = P(A) + P(B) - P(A \cap B)$. Tümleyen: $P(\overline{A}) = 1 - P(A)$, doğum günü hesabında kullandığımız "hiç çakışmama"nın tersi.

Sonlu bir $\Omega$'da bütün sonuçlar **eşit olası** ise olasılık bir sayma problemi:

$$
P(A) = \frac{|A|}{|\Omega|}.
$$

$P(\text{toplam } 7) = \frac{6}{36} = \frac16$. Bütün kombinatorik (Ders 6.14–6.16) burada olasılığa dönüşüyor.

---

## 2. Koşullu olasılık ve bağımsızlık

$B$ olduğunu **bildiğimizde** $A$'nın olasılığı:

$$
P(A \mid B) = \frac{P(A \cap B)}{P(B)}, \qquad P(B) > 0.
$$

Sezgi: örnek uzayı $B$'ye daralt ve orada $A$'nın payına bak. İlk zar 3 ise toplam 7 için ikinci zar 4 olmalı: $P(\text{toplam } 7 \mid \text{ilk } 3) = \frac{1}{6}$.

$A$ ile $B$ **bağımsız**: $P(A \cap B) = P(A) P(B)$, yani $P(A \mid B) = P(A)$. $B$'yi bilmek $A$ hakkında hiçbir şey söylemiyor. Yukarıdaki örnekte "toplam 7" ile "ilk zar 3" bağımsız ($\frac16 = \frac16$); "toplam 12" ile "ilk zar 3" ise değil ($0 \ne \frac{1}{36}$).

Bağımsızlık bir **varsayım** ve çoğu zaman hesabı mümkün kılan şey. Ders 6.20'deki $4^{-k}$ hesabı, Miller–Rabin turlarının bağımsız (her tur yeni bir rastgele taban) olmasına dayanıyordu.

### Bayes teoremi

$P(A \mid B)$ ile $P(B \mid A)$ farklı şeyler; aralarındaki köprü:

$$
P(A \mid B) = \frac{P(B \mid A)\, P(A)}{P(B)}.
$$

(İki tarafı $P(B)$ ile çarpınca ikisi de $P(A \cap B)$.)

**Yanlış pozitif paradoksu.** Bir hastalık 1000 kişide birde görülüyor. Test hastalarda %99 pozitif çıkıyor, sağlamlarda %5 yanlış pozitif veriyor. Testin pozitif çıktığı birinin hasta olma olasılığı?

$$
P(\text{pozitif}) = 0.99 \cdot 0.001 + 0.05 \cdot 0.999 \approx 0.0509
$$

$$
P(\text{hasta} \mid \text{pozitif}) = \frac{0.99 \cdot 0.001}{0.0509} \approx 0.019.
$$

Yüzde 2'den az. Hastalık o kadar nadir ki, pozitiflerin çoğu sağlam insanlardaki %5'lik hatadan geliyor. Programlamada aynı yapı: nadir bir hatayı arayan bir statik analiz aracı ya da bir spam filtresi, yanlış pozitif oranı küçük görünse bile uyarılarının çoğunun yanlış olmasına yol açabiliyor.

---

## 3. Rastgele değişken ve beklenen değer

**Rastgele değişken** $X$: her sonuca bir sayı atayan bir fonksiyon $X : \Omega \to \mathbb{R}$ (Ders 6.9). "İki zarın toplamı", "bir arama algoritmasının yaptığı karşılaştırma sayısı".

**Beklenen değer**: değerlerin olasılıklarıyla ağırlıklı ortalaması,

$$
E[X] = \sum_{\omega \in \Omega} X(\omega)\, P(\omega) = \sum_x x \cdot P(X = x).
$$

Bir zarın beklenen değeri $\frac{1 + 2 + \dots + 6}{6} = 3.5$; hiçbir zaman 3.5 gelmiyor ama uzun vadede ortalama oraya gidiyor (büyük sayılar yasası; simülasyonların neden çalıştığı).

### Doğrusallık

Olasılığın en güçlü ve en şaşırtıcı aleti:

$$
E[X + Y] = E[X] + E[Y], \qquad E[cX] = c\, E[X]
$$

**her zaman**, $X$ ile $Y$ bağımsız olsun olmasın. (Kanıt: tanımdaki toplamı ikiye ayır; Ders 6.10'daki birleşme yasası.) Rastgele değişkenler bir vektör uzayı ve $E$ onun üzerinde doğrusal bir fonksiyon (Ders 6.27).

### Gösterge değişkenleri

Bir olay için **gösterge**: $I_A = 1$ eğer $A$ olduysa, değilse $0$. Ders 6.10'daki Iverson parantezi $[A]$'nın olasılık hali, ve $E[I_A] = P(A)$.

Karmaşık bir şeyi **saymak** istiyorsan, onu göstergelerin toplamı olarak yaz ve doğrusallığı kullan. Örnek: $n$ kişilik bir grupta doğum günü aynı olan **çiftlerin** beklenen sayısı? Her çift için bir gösterge, $P = \frac{1}{365}$; $\binom{n}{2}$ çift. $E = \binom{n}{2} / 365$. 28 kişide 1'i geçiyor. Hiçbir bağımsızlık hesabı yapmadık; çiftler bağımsız bile değil.

---

## 4. Kupon toplayıcı

Her gofret paketinden $n$ farklı kartın biri eşit olasılıkla çıkıyor. Hepsini toplamak için beklenen paket sayısı?

$X_i$: $i - 1$ farklı kart topladıktan sonra $i$'ncisini bulana kadar açılan paket sayısı. Yeni bir kart gelme olasılığı $p_i = \frac{n - i + 1}{n}$; her paket bağımsız. Başarı olasılığı $p$ olan bir denemeyi başarıya kadar tekrarlamanın beklenen sayısı $\frac1p$ (geometrik dağılım). Doğrusallıkla:

$$
E[X] = \sum_{i=1}^{n} \frac{n}{n - i + 1} = n \left(\frac1n + \frac{1}{n-1} + \dots + 1\right) = n H_n \approx n \ln n.
$$

Ders 6.10'daki harmonik sayılar. Son kartlar pahalı: son kartı bulmak tek başına ortalama $n$ paket.

Simülasyon için bir rastgele sayı üreteci gerekiyor. C'nin `rand()`'ı hem kalitesiz hem yavaş olabiliyor; küçük ve iyi dağılımlı bir 64 bitlik üreteç:

```c
static uint64_t state = 0x9E3779B97F4A7C15ull;
static uint64_t splitmix64(void) {                 // kucuk, hizli, iyi dagilimli bir uretec
    uint64_t z = (state += 0x9E3779B97F4A7C15ull);
    z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ull;
    z = (z ^ (z >> 27)) * 0x94D049BB133111EBull;
    return z ^ (z >> 31);
}
static uint64_t below(uint64_t m) { return splitmix64() % m; }   // m << 2^64 iken sapma ihmal edilebilir
```

Bir sayacı sabit bir tek sayıyla artırıp (Ders 6.9: tek sayıyla toplama mod $2^{64}$'de bütün değerleri gezer) bitleri XOR–kaydırma–çarpma ile karıştırıyor; Ders 5'in aletlerinden yapılma. Kriptografik değil, ama simülasyon için mükemmel.

```
P(toplam=7) = 0.1665 (1/6 = 0.1667), P(toplam=7 | ilk=3) = 0.1671
kupon (n=50): ortalama 225.3 deneme, n*H_n = 225.0
```

On milyon zar atışı ve 20 bin kupon koleksiyonu; teoriyle üç basamak uyuşuyor.

**`% n` sapması hakkında bir uyarı.** `below(m)`, $2^{64}$ değeri $m$ kovaya bölüyor; $m$, $2^{64}$'ü tam bölmüyorsa bazı kovalar bir fazla değer alıyor. Küçük bir örnekle büyütelim: 0–9 arası 10 eşit olası değeri `% 6` ile 6 kovaya dağıtınca `2 2 2 2 1 1`: 0–3, 4–5'ten iki kat olası. 64 bitte fark $m / 2^{64}$ civarı, ihmal edilebilir; ama `RAND_MAX` = 32767 olan platformlarda `rand() % 10000` belirgin biçimde sapıyor. (Doğru yöntem: sapma yaratan son kısmı reddedip yeniden çekmek; Alıştırma 5.)

---

## 5. Hash tablosunun beklenen maliyeti

Faz 8'de yazacağımız **zincirli** hash tablosu: $m$ kova, her kova bir bağlı liste. $k$ anahtar ekleniyor. **Yük faktörü** $\alpha = k / m$. Varsayım (basit düzgün hashleme): her anahtar, diğerlerinden bağımsız olarak, her kovaya $\frac1m$ olasılıkla gidiyor.

**Başarısız arama** (aranan anahtar yok): hash'i hesapla, bir kovanın bütün zincirini gez. Kova $b$'nin uzunluğu $L_b = \sum_{\text{anahtar } x} [h(x) = b]$; doğrusallıkla $E[L_b] = k \cdot \frac1m = \alpha$. Maliyet $\Theta(1 + \alpha)$ (1, hash hesabı).

**Başarılı arama** (tablodaki rastgele bir anahtar): anahtar zincirin başına ekleniyorsa, $x$'i bulmak için $x$'ten **sonra** aynı kovaya eklenen anahtarları ve $x$'i kendisini geçiyoruz. $i$'nci eklenen anahtar için, sonra eklenen $k - i$ anahtarın her biri $\frac1m$ olasılıkla aynı kovada. Ortalama:

$$
\frac{1}{k}\sum_{i=1}^{k}\left(1 + \frac{k - i}{m}\right) = 1 + \frac{k - 1}{2m} \approx 1 + \frac{\alpha}{2}.
$$

(Ders 6.10'daki Gauss toplamı.) Simülasyon, $m = 1000$:

```c
for (int i = 0; i < k; i++) len[below(m)]++;
double unsucc = 0, succ = 0;                 // basarisiz: rastgele bir kovanin uzunlugu
for (int b = 0; b < m; b++) { unsucc += len[b]; succ += (double)len[b] * (len[b] + 1) / 2; }
unsucc /= m; succ /= k;                      // basarili: anahtarin zincirdeki ortalama sirasi
```

```
alpha=0.5  basarisiz 0.500 (alpha 0.500)  basarili 1.222 (1+alpha/2 1.250)  en uzun 4
alpha=1.0  basarisiz 1.000 (alpha 1.000)  basarili 1.492 (1+alpha/2 1.500)  en uzun 5
alpha=2.0  basarisiz 2.000 (alpha 2.000)  basarili 1.976 (1+alpha/2 2.000)  en uzun 10
alpha=4.0  basarisiz 4.000 (alpha 4.000)  basarili 2.987 (1+alpha/2 3.000)  en uzun 13
```

Bir kovadaki $\ell$ anahtar, sıralarına göre $1, 2, \dots, \ell$ karşılaştırmada bulunuyor; toplamı $\frac{\ell(\ell+1)}{2}$. (Başarısız sütun her seferinde tam $\alpha$: bütün kovaların ortalama uzunluğu tanım gereği $k/m$. Asıl rastgele olan, hangi kovaya düşeceğin.) Başarılı sütun $1 + \frac{\alpha}{2}$'ye çok yakın; küçük fark formüldeki $-\frac{1}{2m}$ terimi ve simülasyonun gürültüsü.

Sonuç: $\alpha$ sabit tutulursa (tablo dolunca büyütülürse, Ders 4.24'teki dinamik dizi gibi) her işlem **beklenen** $O(1)$. Ama "en uzun" sütununa bak: en kötü kova ortalamanın çok üstünde. $\alpha = 1$'de beklenen en uzun zincir $\Theta(\frac{\log m}{\log \log m})$; ve kötü niyetli biri hash fonksiyonunu biliyorsa bütün anahtarları **aynı** kovaya düşürüp her aramayı $\Theta(k)$ yapabiliyor (HashDoS saldırıları, 2011). Beklenen değer analizi, varsayımlarının (düzgün ve bağımsız hash) gerçekleştiği kadar geçerli. Rastgele seçilen bir hash fonksiyonu (evrensel hashleme, Faz 8) bu varsayımı saldırgana karşı da korumanın yolu.

---

## Alıştırmalar

**1** – İki zarda: (a) en az bir 6 gelme olasılığı (b) toplamın çift olması ile ilk zarın çift olması bağımsız mı? (c) ikisinin de çift olduğu bilindiğinde toplamın 8 olma olasılığı. Simülasyonla doğrula.

**2** – Bir dizinin rastgele bir permütasyonunda (Ders 6.21) **sabit nokta** ($a[i] = i$) sayısının beklenen değeri nedir? Gösterge değişkenleriyle hesapla ve Fisher–Yates karıştırmasıyla (`for i = n-1..1: swap(a[i], a[below(i+1)])`) simüle et.

**3** – Ders 6.2'deki `find`'ı (doğrusal arama) düşün. Aranan anahtar dizide **var** ve her konumda eşit olasılıklı ise beklenen karşılaştırma sayısı ne? Yoksa? Anahtarın dizide olma olasılığı $q$ ise?

**4** – Bölüm 5'teki simülasyonu **açık adresleme** ile tekrarla (doğrusal sondalama: kova doluysa bir sonrakine bak). $\alpha = 0.5, 0.7, 0.9$ için başarısız aramanın ortalama sonda sayısını ölç. Knuth'un formülü $\frac12\left(1 + \frac{1}{(1 - \alpha)^2}\right)$ ile karşılaştır. $\alpha \to 1$'de ne oluyor?

**5** – Sapmasız `below(m)` yaz: $2^{64} \bmod m$ kadar değeri reddet. Beklenen yeniden çekme sayısı nedir? (İpucu: reddedilme olasılığı $< \frac12$; geometrik dağılım.)

<details>
<summary>Cevaplar</summary>

**1** – (a) Tümleyen: hiç 6 gelmemesi $\left(\frac56\right)^2 = \frac{25}{36}$; cevap $\frac{11}{36} \approx 0.306$. (b) $P(\text{toplam çift}) = \frac12$, $P(\text{ilk çift}) = \frac12$, $P(\text{ikisi}) = P(\text{ikisi de çift}) = \frac14 = \frac12 \cdot \frac12$: bağımsız. Sezgiye aykırı görünebilir ama ilk zarı bilmek toplamın paritesini değiştirmiyor; ikinci zar onu yarı yarıya belirliyor. (c) İkisi de çift: 9 sonuç; toplam 8: $(2,6), (4,4), (6,2)$; $\frac39 = \frac13$.

**2** – $I_i = [a[i] = i]$, $P = \frac1n$ (rastgele permütasyonda $i$ her konuma eşit olasılıkla gidiyor). $E = n \cdot \frac1n = 1$, $n$'den bağımsız! Simülasyonda $n = 10$ ve $n = 1000$ için ikisi de $\approx 1$. (Hiç sabit noktası olmama olasılığı ise $\approx \frac1e \approx 0.368$; içerme–dışlamayla, Ders 6.15.)

**3** – Var ve konum $i$ ($1..n$) eşit olasılıklı: $i$ karşılaştırma, $E = \frac{n+1}{2}$. Yok: hep $n$. Olma olasılığı $q$: koşullu beklenti ile $E = q \frac{n+1}{2} + (1 - q) n$ (toplam beklenti yasası, Bayes'in beklenen değer hali). $q = 1$'de yarı yol, $q = 0$'da hepsi.

**4** – $m = 2^{20}$ kovalı bir tabloda 200 bin rastgele başarısız aramayla ölçüm: $\alpha = 0.5$: 2.49, $\alpha = 0.7$: 6.11, $\alpha = 0.9$: 48.0; formül $2.5$, $6.06$, $50.5$. $\alpha \to 1$'de $\frac{1}{(1-\alpha)^2}$ patlıyor: doğrusal sondalamada dolu kümeler birbirine yapışıyor (birincil kümelenme). Zincirlemede maliyet $\alpha$ ile doğrusal artıyordu; açık adreslemede tablo dolmadan büyütmek şart (pratikte $\alpha \le 0.7$). Ama açık adresleme cache dostu (ardışık bellek, Ders 6.25), ve düşük $\alpha$'da genellikle daha hızlı.

**5** –

```c
static uint64_t below_unbiased(uint64_t m) {   // m > 0
    uint64_t limit = -m % m;                    // = 2^64 mod m (unsigned: -m = 2^64 - m)
    uint64_t x;
    do { x = splitmix64(); } while (x < limit); // ilk 'limit' degeri reddet
    return x % m;
}
```

Kalan $2^{64} - \text{limit}$ değer, $m$'nin tam katı; her kova eşit sayıda değer alıyor. `-m % m`, Ders 6.18'deki modüler aritmetiğin bir hilesi: `unsigned`'da $-m \equiv 2^{64} - m$, ve $(2^{64} - m) \bmod m = 2^{64} \bmod m$. Reddedilme olasılığı $\frac{\text{limit}}{2^{64}} < \frac{m}{2^{64}}$; beklenen çekme sayısı $\frac{1}{1 - \text{red}} \approx 1$. Daha hızlı yöntemler (Lemire, 2019) bölmeyi de 128 bitlik çarpmayla değiştiriyor.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), Bölüm 7: ayrık olasılık, Bayes, beklenen değer.
- Thomas Cormen ve diğ., *Introduction to Algorithms* (4. baskı), Bölüm 5 (olasılıksal analiz, gösterge değişkenleri) ve §11.2 (zincirli hashlemenin analizi).
- Michael Mitzenmacher & Eli Upfal, *Probability and Computing* (2. baskı), Bölüm 1–2: rastgele algoritmalar için olasılık.
- Sebastiano Vigna, "splitmix64" ve xoshiro üreteçleri (prng.di.unimi.it); Daniel Lemire, "Fast Random Integer Generation in an Interval", *ACM TOMACS* 29(1), 2019.

**Sıradaki ders:** Graf teorisi temelleri. Düğümler ve kenarlar, yönlü graflar, ağaçlar, DAG'ler, ve register tahsisinin bir graf renklendirme problemi olması.
