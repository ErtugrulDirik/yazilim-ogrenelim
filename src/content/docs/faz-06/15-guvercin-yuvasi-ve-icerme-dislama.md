---
title: "6.15 Güvercin yuvası ve içerme–dışlama"
description: "Güvercin yuvası ilkesi ve genelleştirilmiş hali; hash çakışmasının, kayıpsız sıkıştırmanın sınırının ve sonlu durumlu bir döngünün tekrarının kaçınılmazlığı; doğum günü paradoksu ve √m kuralı; 16 bitlik bir hash'te ilk çakışmayı ölçen C programı; içerme–dışlama ilkesi; Euler'in φ fonksiyonu ve φ(n) = n ∏(1 − 1/p) formülünün içerme–dışlamayla türetilmesi ve kodu."
---

Ders 6.9'da şunu gördük: $|A| > |B|$ ise $A$'dan $B$'ye birebir bir fonksiyon **olamaz**. Bu cümlenin halk arasındaki adı **güvercin yuvası ilkesi**: 10 güvercin 9 yuvaya girerse, en az bir yuvada iki güvercin var. Bu kadar açık bir şeyin bir adı olması tuhaf görünebilir; ama şaşırtıcı derecede güçlü sonuçları var ve bilgisayar biliminde birkaç "imkânsızlık" teoremi doğrudan buradan çıkıyor.

Dersin ikinci yarısı, toplama ilkesinin (Ders 6.14) kümeler **kesiştiğinde** ne olacağını söyleyen genellemesi: **içerme–dışlama**.

---

## 1. İlke

**Teorem (güvercin yuvası).** $n + 1$ nesne $n$ kutuya konursa, en az bir kutuda en az iki nesne vardır.

**Kanıt** (çelişki). Her kutuda en fazla bir nesne olsaydı, toplam nesne sayısı en fazla $n$ olurdu. $\blacksquare$

**Genelleştirilmiş hali.** $N$ nesne $k$ kutuya konursa, en az bir kutuda en az $\lceil N / k \rceil$ nesne vardır. (Her kutuda en fazla $\lceil N/k \rceil - 1$ olsaydı toplam $k(\lceil N/k \rceil - 1) < N$ olurdu.)

Kanıt varlıkçı (Ders 6.3): **hangi** kutunun dolu olduğunu söylemiyor, sadece birinin dolu olduğunu.

Basit örnekler:

- 367 kişiden ikisinin doğum günü aynı (366 olası gün).
- Çorap çekmecesinde siyah ve beyaz çoraplar var; karanlıkta 3 çorap çekersen bir çift garanti.
- İstanbul'da (15 milyondan fazla kişi) saç teli sayısı aynı olan iki kişi var (bir insanda en fazla birkaç yüz bin saç teli).

---

## 2. Bilgisayar biliminde üç imkânsızlık

**Hash çakışması kaçınılmaz.** 32 bitlik bir hash fonksiyonu, $2^{32}$ kutuya yerleştiriyor. $2^{32} + 1$ farklı string varsa (8 karakterlik küçük harf stringleri bile $26^8 \approx 2 \cdot 10^{11}$), en az ikisi aynı hash'i alıyor. Hiçbir hash fonksiyonu, ne kadar iyi tasarlanırsa tasarlansın, sınırsız girdiye birebir olamaz. Faz 8'deki hash tablosu bu yüzden çakışmaları **çözmek** zorunda; çakışmaları önlemek imkânsız.

**Kayıpsız sıkıştırma her şeyi küçültemez.** "Her dosyayı en az bir bit küçülten" bir sıkıştırma programı olsaydı: $n$ bitlik $2^n$ dosya, en fazla $n - 1$ bitlik dosyalara gidiyor; bunların sayısı $2^0 + 2^1 + \dots + 2^{n-1} = 2^n - 1$ (Ders 6.4). Bir kutu eksik, iki dosya aynı çıktıya gidiyor, geri açarken hangisinin olduğunu bilemezsin. Her sıkıştırıcı bazı dosyaları **büyütüyor**; iyi sıkıştırıcılar sadece insanların gerçekten kullandığı dosyaları küçültüyor.

**Sonlu durumlu bir sistem sonunda tekrar eder.** Ders 1.3'teki durum makinesinin $k$ durumu varsa, $k + 1$ adımda en az bir durum iki kez görülüyor; girdi yoksa o andan sonra her şey döngüye giriyor. Rastgele sayı üreteçlerinin bir **periyodu** olması, `uint32_t` durumlu bir üretecin en fazla $2^{32}$ adımda tekrar etmesi bu yüzden. Ders 14'te sonlu otomatların neden parantez dengesini tanıyamadığının kanıtı (pompalama önsavı) da bir güvercin yuvası kanıtı.

---

## 3. Doğum günü paradoksu

Güvercin yuvası, $m + 1$ nesnede çakışmayı **garanti** ediyor. Ama çakışma çok daha önce, **büyük olasılıkla** oluyor.

23 kişilik bir sınıfta iki kişinin doğum gününün aynı olma olasılığı %50'den fazla. Hiç çakışma olmama olasılığı:

$$
\frac{365}{365} \cdot \frac{364}{365} \cdots \frac{365 - 22}{365} \approx 0.493.
$$

Sezgiye aykırı çünkü insanlar "benim doğum günümü paylaşan biri var mı?" diye düşünüyor (22 kişi, küçük olasılık); oysa soru **herhangi** bir çift hakkında ve $\binom{23}{2} = 253$ çift var (Ders 6.14).

Genel kural: $m$ kutuya rastgele yerleştirmede ilk çakışma ortalama $\sqrt{\pi m / 2} \approx 1.25\sqrt{m}$ nesnede oluyor. 16 bitlik bir hash'i ölçelim:

```c
#include <stdio.h>
#include <stdint.h>

// FNV-1a, 16 bite kirpilmis: 65536 kova
static uint16_t hash16(const char *s) {
    uint32_t h = 2166136261u;
    while (*s) { h ^= (unsigned char)*s++; h *= 16777619u; }
    return (uint16_t)(h ^ (h >> 16));
}

// "t<deneme>_<i>" anahtarlarinda ilk cakismanin kacinci anahtarda oldugu
static int first_collision(int trial) {
    static int stamp[65536];          // stamp[h] == trial + 1 ise h bu denemede goruldu
    char buf[32];
    for (int i = 0; ; i++) {
        snprintf(buf, sizeof buf, "t%d_%d", trial, i);
        uint16_t h = hash16(buf);
        if (stamp[h] == trial + 1) return i + 1;
        stamp[h] = trial + 1;
    }
}

int main(void) {
    const int trials = 10000;
    long total = 0; int lo = 1 << 30, hi = 0;
    for (int t = 0; t < trials; t++) {
        int k = first_collision(t);
        total += k;
        if (k < lo) lo = k;
        if (k > hi) hi = k;
    }
    printf("ortalama %.1f, en az %d, en cok %d (%d deneme)\n", (double)total / trials, lo, hi, trials);
    return 0;
}
```

```
ortalama 343.5, en az 12, en cok 1066 (10000 deneme)
```

65536 kutu, ama ilk çakışma ortalama **343**'üncü anahtarda; teorik tahmin $1.25 \cdot 256 \approx 321$. Güvercin yuvasının garantisi 65537'ydi; gerçekte iki yüz kat erken. `stamp` dizisi, her denemede bütün tabloyu sıfırlamamak için bir hile: "bu denemede görüldü" bilgisini deneme numarasıyla işaretliyoruz.

Bunun güvenlik açısından ağır bir sonucu var: $n$ bitlik bir hash'te çakışma bulmak için $2^n$ değil, kabaca $2^{n/2}$ deneme yetiyor (**doğum günü saldırısı**). Bu yüzden kriptografik hash'ler 256 bit: $2^{128}$ deneme hâlâ imkânsız.

---

## 4. İçerme–dışlama

Ders 6.14'teki toplama ilkesi kümelerin **ayrık** olmasını istiyordu. Kesişiyorlarsa ortak elemanları iki kez sayarız; düzeltmek için bir kez çıkarırız:

$$
|A \cup B| = |A| + |B| - |A \cap B|.
$$

Üç kümede: tekli kesişimleri ekle, ikili kesişimleri çıkar, ama üçlü kesişim bu sefer üç kez eklenip üç kez çıkarıldı, bir kez geri ekle:

$$
|A \cup B \cup C| = |A| + |B| + |C| - |A \cap B| - |A \cap C| - |B \cap C| + |A \cap B \cap C|.
$$

**Teorem (içerme–dışlama).** Sonlu $A_1, \dots, A_n$ kümeleri için

$$
\left|\bigcup_{i=1}^n A_i\right| = \sum_{\emptyset \ne S \subseteq \{1,\dots,n\}} (-1)^{|S|+1} \left|\bigcap_{i \in S} A_i\right|.
$$

**Kanıt.** Birleşimdeki bir $x$ elemanı tam $m \ge 1$ kümede olsun. Sağ tarafta $x$, $S$ bu $m$ kümenin boş olmayan bir alt kümesi olduğunda sayılıyor. $k$ elemanlı $\binom{m}{k}$ alt küme var, her biri $(-1)^{k+1}$ katkı veriyor. Toplam katkı

$$
\sum_{k=1}^{m} (-1)^{k+1}\binom{m}{k} = 1 - \sum_{k=0}^{m} (-1)^k \binom{m}{k} = 1 - 0 = 1.
$$

(Ders 6.14'teki $\sum (-1)^k \binom{m}{k} = 0$ özdeşliği.) Her eleman tam bir kez sayılıyor. $\blacksquare$

**Örnek.** 1 ile 1000 arasında 2, 3 ya da 5'e bölünen kaç sayı var? $A_p$ = $p$'ye bölünenler, $|A_p| = \lfloor 1000/p \rfloor$; $A_p \cap A_q$ = $pq$'ya bölünenler.

$$
500 + 333 + 200 - 166 - 100 - 66 + 33 = 734.
$$

Bölünmeyenler $1000 - 734 = 266$. Program, sayarak: `266`. ✓

Pratikte bir kalıp: "**hiçbir** özelliği sağlamayanları say" sorusu, tümleyenden içerme–dışlamayla çözülüyor:

$$
\left|\overline{A_1} \cap \dots \cap \overline{A_n}\right| = |U| - \left|\bigcup A_i\right| = \sum_{S \subseteq \{1,\dots,n\}} (-1)^{|S|} \left|\bigcap_{i \in S} A_i\right|
$$

($S = \emptyset$ terimi $|U|$.)

Terim sayısı $2^n$; alt kümeleri Ders 6.5'teki gibi bitmask ile gezebilirsin (Alıştırma 4).

---

## 5. Euler'in φ fonksiyonu

$\varphi(n)$: $1 \le k \le n$ olup $n$ ile **aralarında asal** ($\text{EBOB}(k, n) = 1$) olan $k$'ların sayısı.

$\varphi(12) = 4$: $\{1, 5, 7, 11\}$. $p$ asalsa $\varphi(p) = p - 1$: $p$'den küçük her sayı aralarında asal. Bu fonksiyon Ders 6.20'deki Euler teoreminin ve Ders 6.22'deki RSA'nın kalbinde.

Tanımdan doğrudan saymak $n$ kez EBOB hesaplamak. İçerme–dışlama çok daha hızlı bir formül veriyor. $n$'nin farklı asal bölenleri $p_1, \dots, p_r$ olsun. $k$, $n$ ile aralarında asal $\iff$ $k$ hiçbir $p_i$'ye bölünmüyor. $A_i$ = $p_i$'ye bölünenler, $|A_i| = n / p_i$, kesişimler $n / (p_i p_j \cdots)$. Bölüm 4'teki "hiçbirinde değil" formülü:

$$
\varphi(n) = n - \sum_i \frac{n}{p_i} + \sum_{i<j} \frac{n}{p_i p_j} - \dots = n \prod_{i=1}^{r} \left(1 - \frac{1}{p_i}\right).
$$

Son eşitlik: çarpımı açınca tam olarak içerme–dışlamanın terimleri çıkıyor (her alt kümeden bir terim, işareti $(-1)^{|S|}$). $\varphi(12) = 12 \cdot \frac{1}{2} \cdot \frac{2}{3} = 4$. ✓

Kodda: $n$'yi asal çarpanlarına ayırırken (Ders 6.4'teki `factor`) her yeni asal için $r \leftarrow r \cdot (1 - 1/p) = r - r/p$. Bölme her zaman tam, çünkü $p$, $r$'yi hâlâ bölüyor:

```c
// icerme-dislama: n * prod (1 - 1/p), p n'in asal bolenleri
static uint64_t phi(uint64_t n) {
    uint64_t r = n;
    for (uint64_t p = 2; p * p <= n; p++) {
        if (n % p == 0) {
            while (n % p == 0) n /= p;
            r -= r / p;               // r = r * (1 - 1/p)
        }
    }
    if (n > 1) r -= r / n;            // kalan tek buyuk asal
    return r;
}
```

```
phi(12) = 4 (sayarak 4)
phi(36) = 12 (sayarak 12)
phi(97) = 96 (sayarak 96)
phi(100) = 40 (sayarak 40)
phi(1000000) = 400000 (sayarak 400000)
```

"Sayarak" sütunu, Ders 2.9'daki EBOB ile $n$ sayıyı tek tek deneyen kaba kuvvet. Formül $\Theta(\sqrt n)$, kaba kuvvet $\Theta(n \log n)$. Döngü sonundaki `if (n > 1)`: $\sqrt n$'ye kadar bütün küçük asal bölenleri çıkardıktan sonra geriye 1'den büyük bir sayı kaldıysa o bir asal (iki tane $\sqrt n$'den büyük asal böleni olamaz; çarpımları $n$'yi aşar).

---

## Alıştırmalar

**1** – $\{1, 2, \dots, 2n\}$'den $n + 1$ sayı seçilirse, ikisinin ardışık olduğunu kanıtla. (Kutular: $\{1, 2\}, \{3, 4\}, \dots$) İkisinden birinin diğerini böldüğünü de kanıtla. (Kutular: her sayıyı $2^a \cdot m$, $m$ tek, olarak yaz; $m$'ye göre kutula.)

**2** – Bir dizide $n^2 + 1$ farklı sayı varsa, ya $n + 1$ uzunluğunda artan ya da $n + 1$ uzunluğunda azalan bir alt dizi var (Erdős–Szekeres). Her eleman için "orada biten en uzun artan alt dizinin uzunluğu"nu etiket olarak kullanıp güvercin yuvasıyla kanıtla.

**3** – Bölüm 3'teki programda hash'i 8 bite (256 kutu) indir. Ortalama ilk çakışma ne olur? $1.25\sqrt{256} = 20$ ile karşılaştır. 24 bitte?

**4** – $n$ asal ve $N$ verildiğinde, $1..N$ arasında bu asalların **hiçbirine** bölünmeyen sayıları içerme–dışlamayla sayan `uint64_t count_coprime(uint64_t N, const uint64_t *p, int r)` yaz. Alt kümeleri bitmask ile gez; işaret `popcount`'un paritesine bağlı (Ders 5.8).

**5** – $\varphi(n)$ çarpımsal: $\text{EBOB}(m, n) = 1$ ise $\varphi(mn) = \varphi(m)\varphi(n)$. Formülden neden çıktığını açıkla. $\varphi(2^k)$ nedir? `uint32_t`'nin tek sayılarının sayısıyla ilişkisi ne? (İpucu: Ders 6.9'da tek sayıyla çarpma birebir örtendi.)

<details>
<summary>Cevaplar</summary>

**1** – Ardışık: $n$ kutu $\{1,2\}, \{3,4\}, \dots, \{2n-1, 2n\}$; $n+1$ sayı, bir kutuda iki sayı, ve bir kutudaki iki sayı ardışık. Bölme: her sayı $2^a m$, $m$ tek ve $1 \le m \le 2n - 1$; $n$ farklı tek sayı var, $n$ kutu. İki sayı aynı $m$'ye sahip: $2^a m$ ve $2^b m$, $a < b$ ise ilki ikinciyi böler. $\blacksquare$ Kanıtın zekâsı kutuları seçmekte; güvercin yuvası kanıtlarının hepsinde öyle.

**2** – $a_i$ için $L_i$ = $a_i$'de biten en uzun artan alt dizinin uzunluğu. Hiçbir artan alt dizi $n+1$ uzunlukta değilse $L_i \in \{1, \dots, n\}$: $n$ kutu, $n^2 + 1$ eleman. Genelleştirilmiş ilkeyle bir kutuda en az $\lceil (n^2+1)/n \rceil = n + 1$ eleman. Aynı etiketli $i < j$ için $a_i > a_j$ olmalı (yoksa $a_j$, $a_i$'nin dizisini uzatır ve $L_j > L_i$ olurdu). Aynı etiketli $n + 1$ eleman, sırayla azalan bir alt dizi. $\blacksquare$

**3** – Hash'i `& 0xFF` ile 8 bite indirip `stamp`'i 256 elemanlı yapınca 10000 denemede ortalama yaklaşık **28** çıkıyor; teorik tahmin 20–21. 24 bitte (`& 0xFFFFFF`, $2^{24}$ elemanlı statik `stamp`) birkaç yüz denemede yaklaşık **7000**; tahmin $1.25 \cdot 4096 \approx 5100$. Kabaca her 8 bit çakışmayı 16 kat ($\sqrt{256}$) geciktiriyor. Ölçümün teoriden biraz sapması da bir şey söylüyor: tahmin hash değerlerinin **tam rastgele** dağıldığını varsayıyor; bu kadar benzer anahtarlarda (`t0_1`, `t0_2`, ...) FNV-1a'nın kırpılmış bitleri kusursuz düzgün değil. Bir hash fonksiyonunu böyle ölçmek, kalitesini sınamanın basit bir yolu.

**4** –

```c
uint64_t count_coprime(uint64_t N, const uint64_t *p, int r) {
    int64_t total = 0;
    for (uint32_t S = 0; S < (1u << r); S++) {
        uint64_t prod = 1;
        for (int i = 0; i < r; i++)
            if ((S >> i) & 1) prod *= p[i];
        int64_t term = (int64_t)(N / prod);
        total += (__builtin_popcount(S) & 1) ? -term : term;   // (-1)^|S|
    }
    return (uint64_t)total;
}
// count_coprime(1000, (uint64_t[]){2, 3, 5}, 3) == 266
```

$S = 0$ (boş küme) terimi $N$; tek elemanlı alt kümeler eksi, iki elemanlılar artı. `prod` çok sayıda büyük asalda taşabilir; $\text{prod} > N$ olunca terim zaten 0, orada durmak hem taşmayı hem işi önler.

**5** – $\text{EBOB}(m, n) = 1$ ise $m$ ile $n$'nin asal bölenleri ortak değil; $mn$'nin asal bölenleri ikisininkilerin ayrık birleşimi. $\varphi(mn) = mn \prod_{p \mid m}(1 - \frac1p) \prod_{p \mid n}(1 - \frac1p) = \varphi(m)\varphi(n)$. Ortak asal varsa $(1 - \frac1p)$ çarpanı iki kez sayılırdı; bu yüzden şart gerekli ($\varphi(4) = 2 \ne \varphi(2)^2 = 1$). $\varphi(2^k) = 2^k \cdot \frac12 = 2^{k-1}$: $2^k$ ile aralarında asal olanlar tam olarak tek sayılar. `uint32_t`'de $2^{31}$ tek sayı var ve Ders 6.9'da gördük ki tam olarak bunlar mod $2^{32}$'de tersi olan sayılar. Ders 6.19'da bunu genelleştireceğiz: $a$'nın mod $n$'de tersi var $\iff$ $\text{EBOB}(a, n) = 1$; ve tersi olanların sayısı $\varphi(n)$.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §6.2 (güvercin yuvası) ve §8.5–8.6 (içerme–dışlama ve uygulamaları).
- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), §4.9: φ fonksiyonu.
- Thomas Cormen ve diğ., *Introduction to Algorithms* (4. baskı), §5.4: doğum günü paradoksu ve olasılıksal analiz.

**Sıradaki ders:** Üreteç fonksiyonları. Bir diziyi bir polinomun katsayıları olarak görmek, ve Catalan sayıları: bir ifadenin kaç farklı parse ağacı olabileceği.
