---
title: "6.20 Çin kalan teoremi ve Fermat/Euler"
description: "Çin kalan teoremi: aralarında asal modüllerdeki kalanların tek bir mod M sınıfı belirlemesi, yapıcı kanıt ve C fonksiyonu; büyük sayıları küçük modlarda temsil etme fikri; Fermat'ın küçük teoremi ve kanıtı; Euler teoremi a^φ(n) ≡ 1; Fermat asallık testi ve onu kandıran Carmichael sayıları (561); Miller–Rabin testi, neden çalıştığı, 12 sabit tabanla 64 bitlik her sayı için kesin sonuç veren C uygulaması."
---

Ders 6.18'de $3^6 \equiv 1 \pmod 7$ ve $3^{200} \equiv 1 \pmod{1000}$ çıktı ve "tesadüf değil" dedik. Ders 6.19'da modüler tersi hesaplamayı öğrendik. Bu ders iki büyük teoremle sayı teorisi bölümünü tamamlıyor: biri **birden çok modu birleştirmeyi** (Çin kalan teoremi), öbürü **üslerin mod $n$'deki periyodunu** (Fermat ve Euler) anlatıyor. İkisinden de pratik bir algoritma çıkıyor: Miller–Rabin asallık testi, ve Ders 6.22'de RSA.

---

## 1. Çin kalan teoremi

MS 3.–5. yüzyıl Çin'inden (Sunzi Suanjing) bir problem: "Bir sayı var. 3'e bölünce 2, 5'e bölünce 3, 7'ye bölünce 2 kalıyor. Sayı nedir?"

$$
x \equiv 2 \pmod 3, \qquad x \equiv 3 \pmod 5, \qquad x \equiv 2 \pmod 7.
$$

**Teorem (Çin kalan teoremi, ÇKT).** $m_1, \dots, m_k$ ikişer ikişer aralarında asal ve $M = m_1 \cdots m_k$ ise, her $r_1, \dots, r_k$ için

$$
x \equiv r_i \pmod{m_i} \quad (i = 1, \dots, k)
$$

sisteminin mod $M$'de **tek** bir çözümü vardır.

**Kanıt** (iki modül; fazlası tümevarımla). *Varlık*: Bézout ile $m_1 u + m_2 v = 1$. Şu sayıya bak:

$$
x = r_1\, m_2 v + r_2\, m_1 u.
$$

Mod $m_1$'de $m_1 u \equiv 0$ ve $m_2 v = 1 - m_1 u \equiv 1$; kalan $x \equiv r_1$. Mod $m_2$'de simetrik olarak $x \equiv r_2$. ✓ *Teklik*: $x$ ve $x'$ iki çözümse $m_1 \mid x - x'$ ve $m_2 \mid x - x'$. Aralarında asal oldukları için $m_1 m_2 \mid x - x'$ (Öklid önsavının genellemesi). $\blacksquare$

Kanıttaki $m_2 v$, "mod $m_1$'de 1, mod $m_2$'de 0" olan sayı; $m_1 u$ tersi. Her kalanı kendi "seçici" sayısıyla çarpıp topluyoruz. Kod:

```c
// x = r1 (mod m1), x = r2 (mod m2), ebob(m1, m2) = 1  ->  x mod m1*m2
static int64_t crt2(int64_t r1, int64_t m1, int64_t r2, int64_t m2) {
    int64_t u, v;
    ext_gcd(m1, m2, &u, &v);                 // m1*u + m2*v = 1
    __int128 M = (__int128)m1 * m2;
    __int128 x = (__int128)r1 * m2 % M * v % M + (__int128)r2 * m1 % M * u % M;
    x %= M; if (x < 0) x += M;
    return (int64_t)x;
}
```

`ext_gcd` Ders 6.19'dan. Ara çarpımlar $M^2$ büyüklüğüne çıkabildiği için `__int128`. Üç denklemi ikişer ikişer birleştiriyoruz:

```c
int64_t x = crt2(2, 3, 3, 5);   // 8   (mod 15)
x = crt2(x, 15, 2, 7);          // 23  (mod 105)
```

Sunzi'nin cevabı 23: $23 = 7 \cdot 3 + 2 = 4 \cdot 5 + 3 = 3 \cdot 7 + 2$. ✓ Ve her $23 + 105k$.

### Neden önemli: bir sayıyı parçalara bölmek

ÇKT'nin derin anlamı bir **birebir örten eşleme** (Ders 6.9):

$$
\mathbb{Z}/M\mathbb{Z} \;\longleftrightarrow\; \mathbb{Z}/m_1\mathbb{Z} \times \dots \times \mathbb{Z}/m_k\mathbb{Z}, \qquad x \mapsto (x \bmod m_1, \dots, x \bmod m_k).
$$

Ve bu eşleme toplamayı ve çarpmayı **koruyor** (Ders 6.18: her adımda mod almak serbest). Büyük bir modda tek bir hesap yerine, küçük modlarda **bağımsız** ve paralel hesaplar yapıp sonda ÇKT ile birleştirebilirsin. Faz 12'de büyük sayıları ve polinomları birkaç 64 bitlik asal mod altında çarpıp (NTT) birleştireceğiz; RSA da şifre çözmeyi $p$ ve $q$ modlarında ayrı yapıp ÇKT ile birleştirerek yaklaşık 4 kat hızlanıyor.

---

## 2. Fermat'ın küçük teoremi

**Teorem (Fermat, 1640).** $p$ asal ve $p \nmid a$ ise

$$
a^{p-1} \equiv 1 \pmod p.
$$

**Kanıt.** $\{a, 2a, 3a, \dots, (p-1)a\}$ sayılarına mod $p$'de bak. $a$'nın mod $p$ tersi var (Ders 6.19), dolayısıyla $a$ ile çarpma **birebir**: $ia \equiv ja$ ise $a^{-1}$ ile çarpınca $i \equiv j$. Hiçbiri 0 değil ($p \nmid i$, $p \nmid a$, Öklid önsavı). Demek bu $p - 1$ sayı, $\{1, 2, \dots, p-1\}$'in bir **permütasyonu** (Ders 6.9'daki sonlu kümede birebir = örten). Hepsini çarp:

$$
a \cdot 2a \cdots (p-1)a \equiv 1 \cdot 2 \cdots (p-1) \pmod p
\quad\Rightarrow\quad a^{p-1}(p-1)! \equiv (p-1)!.
$$

$(p-1)!$, $p$ ile aralarında asal; tersiyle çarp: $a^{p-1} \equiv 1$. $\blacksquare$

Sonuçlar:

- **Ters**: $a^{-1} \equiv a^{p-2} \pmod p$. Genişletilmiş Öklid'e alternatif; Ders 6.18'deki `powmod` ile bir satır.
- **Üsleri küçültmek**: $a^e \equiv a^{e \bmod (p-1)}$. Ders 6.18'in 1. alıştırmasında $3^{100} \bmod 7$'yi $3^{100 \bmod 6} = 3^4$'e indirmiştik.

### Euler teoremi

Fermat sadece asal modlar için. Euler genelleştirdi:

**Teorem (Euler).** $\text{EBOB}(a, n) = 1$ ise $a^{\varphi(n)} \equiv 1 \pmod n$.

Kanıt aynı: $\{1, \dots, n\}$ yerine $n$ ile aralarında asal $\varphi(n)$ sayıyı (Ders 6.15) $a$ ile çarp; yine bir permütasyon. $p$ asalken $\varphi(p) = p - 1$, Fermat çıkıyor.

$3^{200} \bmod 1000$: $\varphi(1000) = 1000 \cdot \frac12 \cdot \frac45 = 400$, demek $3^{400} \equiv 1$. Bizim bulduğumuz $3^{200} \equiv 1$ daha güçlü; Euler bir **üst sınır** veriyor, gerçek periyot onun bir **böleni** olabilir. Neden hep bir bölen olduğunu Ders 6.22'de Lagrange teoremiyle göreceğiz.

İkinin kuvvetlerinde: $\varphi(2^{32}) = 2^{31}$, dolayısıyla her tek `uint32_t` $a$ için $a^{2^{31}} \equiv 1$. (Gerçek periyot en fazla $2^{30}$.)

---

## 3. Fermat testi ve Carmichael sayıları

Fermat'ın karşıt tersi (Ders 6.3): $a^{n-1} \not\equiv 1 \pmod n$ ise $n$ **kesinlikle bileşik**. Bu, çarpanlarını hiç bulmadan bir sayının bileşik olduğunu kanıtlamanın yolu:

```c
static bool fermat(uint64_t n, uint64_t a) { return powmod(a, n - 1, n) == 1; }
```

$n = 91 = 7 \cdot 13$: $2^{90} \bmod 91 = 64 \ne 1$; bileşik. Ama ters yön doğru değil: $a^{n-1} \equiv 1$ olması $n$'nin asal olduğunu kanıtlamıyor (Ders 6.1: koşulun karşıtı denk değil). Daha kötüsü:

```
561 = 3*11*17; fermat taban 2: 1
561 ile aralarinda asal tabanlardan Fermat'i gecemeyen: 0
```

561, kendisiyle aralarında asal **her** taban için Fermat testini geçiyor. Bu tür sayılara **Carmichael sayıları** denir; 561 en küçüğü, ve sonsuz sayıda var (1994'te kanıtlandı). Fermat testi tek başına güvenilmez.

---

## 4. Miller–Rabin

Daha güçlü bir test için bir gözlem: $p$ asalsa, $x^2 \equiv 1 \pmod p$'nin **sadece** iki çözümü var: $x \equiv \pm 1$. (Çünkü $p \mid (x-1)(x+1)$, Öklid önsavıyla $p$ birini böler.) Bileşik modlarda daha fazla "1'in karekökü" olabilir: mod 8'de $1, 3, 5, 7$'nin hepsinin karesi 1.

$n - 1 = 2^s d$, $d$ tek. $a^{n-1}$'i şöyle hesapla: önce $a^d$, sonra $s$ kez karele.

$$
a^d, \; a^{2d}, \; a^{4d}, \; \dots, \; a^{2^s d} = a^{n-1}.
$$

$n$ asalsa son terim 1 (Fermat). Ve 1'e ilk ulaşılan noktada bir önceki terimin karesi 1, dolayısıyla o terim $\pm 1$ olmalı. Yani asal bir $n$ için dizi ya **1 ile başlıyor**, ya da bir yerde **$n - 1$ görünüyor**. İkisi de olmuyorsa $n$ kesinlikle bileşik, ve $a$ bunun **tanığı**.

```c
// a tabaninda Miller-Rabin: true = "muhtemelen asal", false = kesin bilesik
static bool mr_round(uint64_t n, uint64_t a, uint64_t d, int s) {
    uint64_t x = powmod(a, d, n);
    if (x == 1 || x == n - 1) return true;
    for (int i = 1; i < s; i++) {
        x = mulmod(x, x, n);
        if (x == n - 1) return true;
    }
    return false;
}
```

561 için: $560 = 2^4 \cdot 35$. $2^{35} \equiv 263$, $263^2 \equiv 166$, $166^2 \equiv 67$, $67^2 \equiv 1$. Dizi $263, 166, 67, 1$: 1'e $-1$ görmeden ulaştı. 67, mod 561'de 1'in **önemsiz olmayan** bir karekökü; 561 bileşik. Fermat'ın kaçırdığını yakaladı.

```
MR taban 2: 0
```

**Teorem (Rabin, 1980).** Bileşik bir $n$ için, $\{1, \dots, n-1\}$'deki tabanların en fazla $\frac14$'ü testi geçer.

Rastgele $k$ taban denersek bileşik bir sayının geçme olasılığı $4^{-k}$'dan küçük: 20 tabanda $10^{-12}$. Olasılıksal algoritmaların (Ders 6.29) ilk büyük başarısı.

### 64 bitte kesin test

64 bitlik sayılar için şans bile gerekmiyor: ilk 12 asal ($2, 3, \dots, 37$) taban olarak kullanılınca, $2^{64}$'e kadar testi geçen **hiçbir** bileşik sayı olmadığı bilgisayarla doğrulanmış.

```c
static bool is_prime(uint64_t n) {
    if (n < 2) return false;
    static const uint64_t small[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (int i = 0; i < 12; i++) {
        if (n == small[i]) return true;
        if (n % small[i] == 0) return false;
    }
    uint64_t d = n - 1; int s = 0;
    while ((d & 1) == 0) { d >>= 1; s++; }     // n - 1 = 2^s * d
    for (int i = 0; i < 12; i++)
        if (!mr_round(n, small[i], d, s)) return false;
    return true;                                // bu 12 taban 2^64'e kadar yeterli
}
```

`while ((d & 1) == 0)`: $n - 1$'in sondaki sıfırlarını saymak, Ders 5.9'daki `ctz`. Doğrulayalım:

```
10^6'ya kadar MR ile: 78498 asal
2305843009213693951: 1
18446744073709551557: 1
18446744073709551615: 0
3215031751: 0
```

78498, Ders 6.17'deki elekle aynı. $2^{61} - 1$ bir Mersenne asalı. $2^{64} - 59$, 64 bite sığan en büyük asal. $2^{64} - 1 = 3 \cdot 5 \cdot 17 \cdots$ bileşik. $3215031751 = 151 \cdot 751 \cdot 28351$, 2, 3, 5 ve 7 tabanlarının hepsini kandıran en küçük sayı; 11 tabanı yakalıyor.

Maliyet: 12 `powmod`, her biri en fazla 64 karelemeli; deneme bölmesinin (Ders 2.9) $\sqrt n \approx 4 \cdot 10^9$ bölmesine karşı birkaç bin çarpma. Ders 6.17'deki asal sayı teoremiyle birlikte büyük asal bulmak artık kolay: rastgele bir tek sayı seç, test et, olmazsa 2 ekle.

---

## Alıştırmalar

**1** – $x \equiv 1 \pmod 4$, $x \equiv 2 \pmod 9$, $x \equiv 3 \pmod{25}$ sistemini elle ve `crt2` ile çöz.

**2** – Modüller aralarında asal değilse ÇKT ne olur? $x \equiv 1 \pmod 6$ ve $x \equiv 3 \pmod{10}$ sisteminin çözümü var mı? $x \equiv 1 \pmod 6$ ve $x \equiv 4 \pmod{10}$? Genel koşulu bul.

**3** – Fermat ile $a^{-1} \equiv a^{p-2}$'yi kullanan bir `mod_inverse_fermat` yaz. $p = 10^9 + 7$ için Ders 6.19'daki `mod_inverse` ile 1 milyon rastgele $a$'da karşılaştır: sonuç ve süre.

**4** – $10^6$'ya kadar olan Carmichael sayılarını bul. (Bir sayının Carmichael olması için Korselt kriteri: bileşik, karesiz, ve her asal böleni $p$ için $p - 1 \mid n - 1$. Ders 6.17'deki `spf` eleğini kullan.) Kaç tane var?

**5** – Miller–Rabin'i sadece 2 tabanıyla çalıştırınca $10^6$'ya kadar kaç bileşik sayı "asal" çıkıyor? (Bunlar 2 tabanında **güçlü yalancı asallar**.) Fermat testiyle (2 tabanı) kaç tane? Karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – $4, 9, 25$ ikişer ikişer aralarında asal, $M = 900$. Önce $x \equiv 1 \ (4)$, $x \equiv 2 \ (9)$: $x = 29$ (mod 36; $29 = 7 \cdot 4 + 1 = 3 \cdot 9 + 2$). Sonra $x \equiv 29 \ (36)$, $x \equiv 3 \ (25)$: $x = 353$ (mod 900). Kontrol: $353 = 88 \cdot 4 + 1 = 39 \cdot 9 + 2 = 14 \cdot 25 + 3$. ✓

**2** – $x \equiv 1 \ (6)$ $x$'in tek olmasını, $x \equiv 3 \ (10)$ da tek olmasını istiyor; mod 2'de uyumlular. Çözüm var: $x \equiv 13 \pmod{30}$ ($\text{EKOK}(6, 10) = 30$). İkincisinde $x \equiv 4 \ (10)$ çift, $x \equiv 1 \ (6)$ tek istiyor: çelişki, çözüm yok. Genel koşul: $r_1 \equiv r_2 \pmod{\text{EBOB}(m_1, m_2)}$; varsa çözüm mod $\text{EKOK}(m_1, m_2)$'de tek.

**3** –

```c
static uint64_t mod_inverse_fermat(uint64_t a, uint64_t p) {   // p asal, p ∤ a
    return powmod(a, p - 2, p);
}
```

Sonuçlar aynı (tersin tekliği). Süre: Fermat yaklaşık 30 karele + 15 çarpma (her biri `__int128` mod), genişletilmiş Öklid ortalama ~20 bölme; ölçünce genişletilmiş Öklid birkaç kat hızlı çıkıyor. Fermat sürümünün avantajı **sabit zamanlı** yazılabilmesi (üs gizli olmadığı için dallar girdiden bağımsız), kriptografide önemli.

**4** – $10^6$'ya kadar 43 Carmichael sayısı: 561, 1105, 1729, 2465, 2821, 6601, ... (1729, Ramanujan'ın taksi sayısı.) Korselt ile kontrol: $561 = 3 \cdot 11 \cdot 17$, karesiz, $2, 10, 16$ hepsi $560$'ı bölüyor. ✓

**5** – Fermat (taban 2): $10^6$'ya kadar 245 bileşik testi geçiyor (2 tabanında Fermat yalancı asalları; en küçüğü 341 = 11 · 31). Miller–Rabin (taban 2): 46 tane (en küçüğü 2047 = 23 · 89, Ders 6.3'teki Mersenne karşı örneği). Tek tabanda bile Miller–Rabin yalancıların çoğunu eliyor; birkaç taban sonra hiçbiri kalmıyor.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Elementary Number Theory and Its Applications* (6. baskı), §4.3 (ÇKT), §6.1–6.3 (Fermat, Euler, yalancı asallar).
- Michael Rabin, "Probabilistic Algorithm for Testing Primality", *Journal of Number Theory* 12(1), 1980.
- W. R. Alford, Andrew Granville & Carl Pomerance, "There are infinitely many Carmichael numbers", *Annals of Mathematics* 139, 1994.
- Jim Sinclair ve Feitsma–Galway tabloları: 64 bitlik deterministik Miller–Rabin tabanları.

**Sıradaki ders:** Gruplar. Toplama, çarpma, permütasyon ve bit desenleri üzerindeki XOR'un ortak yapısı; soyut cebirin ilk adımı.
