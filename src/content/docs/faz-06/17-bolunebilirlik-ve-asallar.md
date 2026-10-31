---
title: "6.17 Bölünebilirlik ve asallar"
description: "Bölünebilirlik bağıntısının özellikleri; bölme algoritması ve C'nin / ile % operatörlerinin negatif sayılardaki davranışı; EBOB, EKOK ve Öklid algoritmasının doğruluğu; Öklid önsavı ve aritmetiğin temel teoremi (varlık ve teklik); asal sayı teoremi; Eratosthenes eleği, neden p²'den başladığı ve O(n log log n) maliyeti; sadece tek sayıları tutan bitset ile 10⁸'e kadar asalları sayan C programı."
---

Ders 2.9'da EBOB'u, asal testini, Ders 6.3'te asalların sonsuzluğunu, Ders 6.4'te her sayının asalların çarpımı olduğunu gördük. Bu ders bu parçaları bir araya getiren **sayı teorisinin** başlangıcı. Önümüzdeki dört ders (modüler aritmetik, modüler ters, Çin kalan teoremi, Fermat) bunların üzerine kurulacak; Faz 5'teki bitset de burada en klasik uygulamasını bulacak.

---

## 1. Bölünebilirlik

Ders 6.3'teki tanım: $a \mid b \iff \exists k \in \mathbb{Z}\; (b = ak)$. Doğrudan çıkan özellikler (her biri bir satırlık kanıt):

- $a \mid b$ ve $b \mid c$ ise $a \mid c$ (geçişlilik; Ders 6.7'de bölünebilirlik bir kısmi sıralamaydı)
- $a \mid b$ ve $a \mid c$ ise her $x, y$ için $a \mid bx + cy$ (**doğrusal birleşim**)
- $a \mid b$ ve $b \ne 0$ ise $|a| \le |b|$
- Her $a$ için $a \mid 0$ ve $1 \mid a$

İkinci özellik bu dersin ve bir sonrakilerin ana aleti. Kanıt: $b = ak$, $c = al$ ise $bx + cy = a(kx + ly)$.

---

## 2. Bölme algoritması

**Teorem.** $a$ bir tamsayı, $b > 0$ ise, $a = qb + r$ ve $0 \le r < b$ olacak şekilde **tek** bir $(q, r)$ çifti vardır.

**Kanıt** (varlık). $\{a - qb \mid q \in \mathbb{Z}\} \cap \mathbb{N}$ kümesi boş değil ($q$'yu çok negatif seç). En küçük elemanı $r = a - qb \ge 0$ olsun (her boş olmayan doğal sayı kümesinin en küçük elemanı var; Ders 6.7'deki teoremin $\mathbb{N}$ hali, tümevarıma denk). $r \ge b$ olsaydı $r - b = a - (q+1)b$ daha küçük bir eleman olurdu. Demek $r < b$. *Teklik*: iki çift olsa $(q - q')b = r' - r$ ve $|r' - r| < b$; $b$'nin bir katı ancak 0 ise $b$'den küçük olabilir. $\blacksquare$

$q$ **bölüm**, $r$ **kalan**. Matematikte $r$ her zaman negatif değil. C'de **değil**:

```c
-7 / 2   // -3   (C99'dan beri sifira dogru yuvarlanir)
-7 % 2   // -1   (a == (a / b) * b + a % b her zaman dogru)
```

C, bölümü sıfıra doğru kesiyor ve kalanı buna uyduruyor; negatif $a$'da kalan negatif çıkıyor. Matematiğin $-7 = -4 \cdot 2 + 1$'ini istiyorsan düzeltmen gerekiyor:

```c
static int mod(int a, int b) {     // b > 0, sonuc [0, b)
    int r = a % b;
    return r < 0 ? r + b : r;
}
```

Bu fark, Ders 6.18'deki modüler aritmetiği yazarken sürekli karşımıza çıkacak. (Ders 5.1'de `-1 >> 1`'in `-1`, `-1 / 2`'nin `0` olmasının sebebi de bu: kaydırma aşağı, bölme sıfıra doğru yuvarlıyor.)

---

## 3. EBOB ve Öklid algoritması

$\text{EBOB}(a, b)$: $a$ ve $b$'nin ikisini de bölen en büyük sayı. Ders 6.8'de bunun bölünebilirlik kafesinde $a \sqcap b$ olduğunu gördük: ortak bölenlerin hepsi EBOB'u bölüyor.

Ders 1.3'teki Öklid algoritması:

```c
static uint64_t gcd(uint64_t a, uint64_t b) {
    while (b) { uint64_t t = a % b; a = b; b = t; }
    return a;
}
```

**Teorem.** $\text{EBOB}(a, b) = \text{EBOB}(b, a \bmod b)$.

**Kanıt.** $r = a - qb$. $d$, $a$ ve $b$'yi bölüyorsa doğrusal birleşimleri $r$'yi de böler; $d$, $b$ ve $r$'yi bölüyorsa $a = qb + r$'yi de böler. İki çiftin ortak bölenleri **aynı küme**; en büyükleri de aynı. $\blacksquare$

Ders 1.3'teki döngü değişmezi ("EBOB değişmiyor") böylece kanıtlandı. Algoritma sonlanıyor çünkü $b$ her turda kesin küçülüyor ve negatif olamıyor; Ders 6.11'deki Lamé teoremine göre en fazla $\approx 2.08 \ln b$ tur.

$\text{EKOK}(a, b) = \frac{ab}{\text{EBOB}(a, b)}$. Kodda `a / gcd(a, b) * b` yaz, `a * b / gcd(a, b)` değil; ilki taşmayı geciktiriyor (Ders 6.14'teki "önce sadeleştir" ilkesi).

---

## 4. Aritmetiğin temel teoremi

Ders 6.4'te güçlü tümevarımla her $n \ge 2$'nin asalların çarpımı olduğunu kanıtladık (**varlık**). Asıl önemli kısım **teklik**: $360 = 2^3 \cdot 3^2 \cdot 5$ yazılışı, sıra dışında tek. Bunun için bir önsav gerekiyor.

**Önsav (Öklid).** $p$ asal ve $p \mid ab$ ise $p \mid a$ ya da $p \mid b$.

Kanıtı Ders 6.19'daki Bézout özdeşliğiyle iki satır olacak; şimdilik kabul edelim. Asallığın şart olduğuna dikkat: $6 \mid 4 \cdot 9$ ama $6 \nmid 4$ ve $6 \nmid 9$.

**Teorem (aritmetiğin temel teoremi).** Her $n \ge 2$ asalların çarpımı olarak yazılır ve bu yazılış, çarpanların sırası dışında tektir.

**Kanıt** (teklik, çelişki). İki farklı çarpanlaraya ayırması olan en küçük $n$'yi al: $n = p_1 p_2 \cdots p_r = q_1 q_2 \cdots q_s$. $p_1 \mid q_1 \cdots q_s$; Öklid önsavını tekrar tekrar uygula: $p_1$, bir $q_j$'yi bölüyor, ve $q_j$ asal olduğu için $p_1 = q_j$. İki taraftan sadeleştir: $n / p_1$'in de iki farklı ayrışması var ve $n / p_1 < n$. En küçüklükle çelişiyor. $\blacksquare$

Teklik bize sayıları **asal üslerinin vektörü** olarak görme hakkı veriyor:

$$
n = \prod_p p^{e_p} \quad\longleftrightarrow\quad (e_2, e_3, e_5, e_7, \dots)
$$

Bu temsilde çarpma üslerin toplamı, bölünebilirlik "her üs küçük ya da eşit", EBOB üslerin **minimumu**, EKOK **maksimumu**. Ders 6.7'deki 30'un bölenleri bir küptü, çünkü $30 = 2^1 3^1 5^1$ ve bölenler $\{0,1\}^3$'teki vektörler.

---

## 5. Asalların yoğunluğu

Ders 6.3'te asalların sonsuz olduğunu gördük. Ne sıklıkta?

**Asal sayı teoremi** (1896, Hadamard ve de la Vallée Poussin). $\pi(n)$, $n$'ye kadar olan asal sayısı olmak üzere

$$
\pi(n) \sim \frac{n}{\ln n}, \qquad \text{yani} \quad \lim_{n \to \infty} \frac{\pi(n)}{n / \ln n} = 1.
$$

Kabaca: $n$ civarında rastgele bir sayının asal olma olasılığı $\frac{1}{\ln n}$. 100 basamaklı bir sayı için bu yaklaşık $\frac{1}{230}$; Ders 6.20'de RSA için büyük asal ararken bunu kullanacağız (rastgele tek sayılar dene, ortalama 115 denemede bir asal bulunur). Kanıtı karmaşık analiz istiyor ve bu serinin kapsamı dışında; ama aşağıda programla görebiliriz.

---

## 6. Eratosthenes eleği

$n$'ye kadar **bütün** asalları bulmak için her sayıyı ayrı ayrı test etmek (Ders 2.9) $\Theta(n\sqrt n)$. Eratosthenes'in fikri tersinden gitmek: asalları aramak yerine **bileşikleri işaretle**.

1. 2'den $n$'ye bütün sayıları yaz.
2. İşaretlenmemiş en küçük sayı $p$ asal. Bütün katlarını işaretle.
3. Bir sonraki işaretlenmemiş sayıya geç, tekrarla.

İki iyileştirme:

- **$p^2$'den başla.** $p$'nin $p^2$'den küçük katları $kp$, $k < p$; $k$'nın bir asal çarpanı $p$'den küçük ve o asal işlenirken $kp$ zaten işaretlendi.
- **$p \le \sqrt n$ yeter.** Bileşik her $m \le n$'nin $\sqrt n$'den büyük olmayan bir asal böleni var (iki büyük asalın çarpımı $n$'yi aşar).

Bellek: her sayı için bir bit yeter (asal mı, değil mi), Ders 5.20'deki bitset. Daha da azaltabiliriz: 2 dışındaki çift sayılar asal olamaz, sadece **tek** sayıları tut. Bit $i$, $2i + 1$ sayısını temsil ediyor; $n = 10^8$ için $5 \cdot 10^7$ bit, yaklaşık 6 MB.

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <time.h>

// sadece tek sayilar: bit i, 2i+1 sayisini temsil eder; 1 = bilesik
typedef struct { uint64_t *w; uint64_t nbits; } oddset;

static int  is_set(const oddset *s, uint64_t i) { return (s->w[i / 64] >> (i % 64)) & 1; }
static void set(oddset *s, uint64_t i)          { s->w[i / 64] |= 1ull << (i % 64); }

static oddset sieve(uint64_t n) {                     // n >= 1
    oddset s = { NULL, (n + 1) / 2 };                 // 1, 3, 5, ..., <= n
    s.w = calloc((s.nbits + 63) / 64, sizeof *s.w);
    set(&s, 0);                                       // 1 asal degil
    for (uint64_t p = 3; p * p <= n; p += 2) {
        if (is_set(&s, p / 2)) continue;              // p bilesik: katlari zaten isaretli
        for (uint64_t m = p * p; m <= n; m += 2 * p)  // p^2'den basla, sadece tek katlar
            set(&s, m / 2);
    }
    return s;
}

static uint64_t count_primes(const oddset *s) {
    uint64_t cnt = 1;                                 // 2
    uint64_t nw = (s->nbits + 63) / 64;
    for (uint64_t i = 0; i < nw; i++) {
        uint64_t x = ~s->w[i];                        // 0 bitler asal
        if (i == nw - 1 && s->nbits % 64) x &= (1ull << (s->nbits % 64)) - 1;
        cnt += __builtin_popcountll(x);
    }
    return cnt;
}

int main(void) {
    for (uint64_t n = 10; n <= 100000000; n *= 10) {
        clock_t t0 = clock();
        oddset s = sieve(n);
        uint64_t pi = count_primes(&s);
        double ms = 1000.0 * (clock() - t0) / CLOCKS_PER_SEC;
        double est = n / log((double)n);
        printf("n=%10llu  pi(n)=%8llu  n/ln n=%9.0f  oran=%.4f  %6.1f ms\n",
               (unsigned long long)n, (unsigned long long)pi, est, pi / est, ms);
        free(s.w);
    }
    return 0;
}
```

```
n=        10  pi(n)=       4  n/ln n=        4  oran=0.9210     0.0 ms
n=       100  pi(n)=      25  n/ln n=       22  oran=1.1513     0.0 ms
n=      1000  pi(n)=     168  n/ln n=      145  oran=1.1605     0.0 ms
n=     10000  pi(n)=    1229  n/ln n=     1086  oran=1.1320     0.0 ms
n=    100000  pi(n)=    9592  n/ln n=     8686  oran=1.1043     0.2 ms
n=   1000000  pi(n)=   78498  n/ln n=    72382  oran=1.0845     1.7 ms
n=  10000000  pi(n)=  664579  n/ln n=   620421  oran=1.0712    21.6 ms
n= 100000000  pi(n)= 5761455  n/ln n=  5428681  oran=1.0613   146.3 ms
```

(Süreler `-O2` ile bir dizüstü bilgisayarda; senin makinende farklı olacak.)

- $10^8$'e kadar 5.761.455 asal, saniyenin yedide birinde.
- Oran, asal sayı teoreminin söylediği gibi 1'e yaklaşıyor, ama **yavaşça** ($\frac{1}{\ln n}$ hızında). Daha iyi bir yaklaşım $\frac{n}{\ln n - 1}$.
- Asalları sayarken Ders 5.8'deki `popcount` 64 sayıyı birden sayıyor. Son kelimedeki fazla bitleri maskelemek, Ders 6.5'teki "tümleyende evren dışındaki bitleri temizle" uyarısının aynısı.
- $10^7$'den $10^8$'e süre 10 katın üstünde artıyor. Algoritma neredeyse doğrusal, ama 6 MB'lık dizi cache'e sığmıyor ve her $p$ için bütün diziyi baştan sona geziyoruz. Faz 11'de diziyi cache'e sığan parçalara bölerek (**parçalı elek**) bunu düzelteceğiz.

**Maliyet.** $p$ için iç döngü yaklaşık $\frac{n}{p}$ adım; toplam $\sum_{p \le \sqrt n} \frac{n}{p}$, asallar üzerinden bir harmonik toplam. Ders 6.12'deki harmonik desen bütün sayılar üzerinden $n \ln n$ veriyordu; sadece asallar üzerinden toplam çok daha yavaş büyüyor: $\sum_{p \le x} \frac{1}{p} \approx \ln \ln x$ (Mertens). Elek $\Theta(n \log \log n)$; $\log \log 10^8 \approx 2.9$, pratikte doğrusal.

---

## Alıştırmalar

**1** – C'de `a % b`'nin $b < 0$ iken ne verdiğini dene (`7 % -2`, `-7 % -2`). `mod` fonksiyonunu negatif $b$ için de matematiksel kalanı (her zaman $[0, |b|)$) verecek şekilde genelleştir.

**2** – $\text{EBOB}(a, b) \cdot \text{EKOK}(a, b) = ab$ olduğunu asal üs vektörleri ile kanıtla. (İpucu: $\min(x, y) + \max(x, y) = x + y$.)

**3** – Elek programını değiştirip $n$'ye kadar olan asalları bir diziye topla. $10^6$'ya kadar **ikiz asalları** ($p$ ve $p + 2$ ikisi de asal) say. Asallar arasındaki en büyük boşluk ne?

**4** – Faktörleri bulan bir **en küçük asal bölen eleği** yaz: `spf[m]` = $m$'nin en küçük asal böleni. Bununla her $m \le n$'yi $O(\log m)$ adımda çarpanlarına ayır. `spf` dizisi bitset'ten neden çok daha fazla bellek istiyor?

**5** – $2, 3, 5$'in hiçbirine bölünmeyen sayılar, 30'un her bloğunda tam 8 tane (Ders 6.15'teki $\varphi(30) = 8$). Bu sayılar mod 30'da $\{1, 7, 11, 13, 17, 19, 23, 29\}$. Bir byte'ın 8 biti bir 30'luk bloğu temsil ederse, $10^8$'e kadar elek kaç byte tutar? Tek sayı bitset'iyle karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – C'de kalanın işareti **bölünenin** işaretini izliyor: `7 % -2 == 1`, `-7 % -2 == -1` (çünkü `7 / -2 == -3` ve `-7 / -2 == 3`, sıfıra doğru). Genel hali:

```c
static long mod(long a, long b) {     // b != 0, sonuc [0, |b|)
    long r = a % b;
    if (r < 0) r += (b < 0) ? -b : b;
    return r;
}
```

(`LONG_MIN % -1` undefined behavior; bölüm `-LONG_MIN` taşıyor, Ders 3.8. Sınır durumları kalanlarda bile peşimizi bırakmıyor.)

**2** – $a = \prod p^{x_p}$, $b = \prod p^{y_p}$. $\text{EBOB} = \prod p^{\min(x_p, y_p)}$, $\text{EKOK} = \prod p^{\max(x_p, y_p)}$. Çarpımları $\prod p^{\min + \max} = \prod p^{x_p + y_p} = ab$. $\blacksquare$ Teklik olmadan bu kanıt çalışmazdı: üsleri "okuyabilmemiz" ayrışmanın tek olmasına bağlı.

**3** – $10^6$'ya kadar 8169 ikiz asal çifti. En büyük boşluk 114 ($492113$ ile $492227$ arası). Ortalama boşluk $\ln n \approx 14$; ama boşluklar çok düzensiz. İkiz asalların sonsuz olup olmadığı hâlâ bilinmiyor (ikiz asal sanısı).

**4** –

```c
uint32_t *spf = calloc(n + 1, sizeof *spf);
for (uint32_t p = 2; p <= n; p++) {
    if (spf[p]) continue;                     // bilesik
    for (uint64_t m = p; m <= n; m += p)
        if (!spf[m]) spf[m] = p;              // ilk isaretleyen en kucuk asal
}
// ayristirma:
while (m > 1) { printf("%u ", spf[m]); m /= spf[m]; }
```

Her bölme $m$'yi en az yarıya indiriyor: en fazla $\log_2 m$ adım. Bellek: her sayı için bir bit değil bir `uint32_t` (32 bit), yani 64 kat (tek sayı bitset'ine göre). $10^8$ için 400 MB. Bilgi miktarı belirliyor: "asal mı" 1 bit, "en küçük asal böleni ne" $\log_2 n$ bit.

**5** – $10^8 / 30 \approx 3.33 \cdot 10^6$ blok, blok başına 1 byte: yaklaşık 3.3 MB. Tek sayı bitset'i $5 \cdot 10^7$ bit = 6.25 MB. Kazanç $\frac{8/30}{1/2} = \frac{8}{15}$: bellek yarıya yakın iniyor. Bu **tekerlek** (wheel) yöntemi; 7'yi de eklersen ($\varphi(210) = 48$) kazanç azalarak sürüyor. Bitlerin konum hesabı karmaşıklaşıyor (mod 30'daki 8 kalandan hangisi), ama hız ve cache için değiyor.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Elementary Number Theory and Its Applications* (6. baskı), Bölüm 1–3: bölünebilirlik, asallar, aritmetiğin temel teoremi.
- G. H. Hardy & E. M. Wright, *An Introduction to the Theory of Numbers* (6. baskı), Bölüm 1–2 ve 22: asalların dağılımı.
- Richard Crandall & Carl Pomerance, *Prime Numbers: A Computational Perspective* (2. baskı), §3.2: elek yöntemleri ve tekerlekler.

**Sıradaki ders:** Modüler aritmetik. Denklik, mod $n$ halkası, ve Faz 3'teki ikiye tümleyenin aslında mod $2^n$ aritmetiği olduğu.
