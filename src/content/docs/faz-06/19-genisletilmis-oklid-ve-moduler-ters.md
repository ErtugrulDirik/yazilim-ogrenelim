---
title: "6.19 Genişletilmiş Öklid ve modüler ters"
description: "Bézout özdeşliği (EBOB, a ile b'nin doğrusal birleşimidir) ve kanıtı; Öklid önsavının Bézout ile kanıtı; genişletilmiş Öklid algoritması, iz tablosu ve döngü değişmezi; modüler tersin ancak ve ancak EBOB(a, n) = 1 iken var olması; doğrusal denkliklerin (ax ≡ b mod n) çözümü; mod tersini hesaplayan C fonksiyonu, mod 2³² ters için Newton yinelemesi, ve C(n, k) mod p'yi faktöriyel tersleriyle hesaplamak."
---

Ders 6.18'i iki açık soruyla bitirdik: mod $n$'de "bölme" ne zaman mümkün, ve nasıl yapılır? Ders 6.9'da 5'in mod 256 tersini (205) tabloyu ters çevirerek, Ders 6.17'de Öklid önsavını kanıtsız bıraktık. Hepsinin cevabı, Ders 1.3'ten beri kullandığımız Öklid algoritmasının küçük bir genişlemesinde.

---

## 1. Bézout özdeşliği

**Teorem (Bézout).** $a, b$ tamsayıları (ikisi birden 0 değil) için

$$
\text{EBOB}(a, b) = ax + by
$$

olacak şekilde $x, y$ tamsayıları vardır. Dahası, EBOB bu biçimde yazılabilen **en küçük pozitif** sayıdır.

**Kanıt.** $S = \{ax + by \mid x, y \in \mathbb{Z}\} \cap \mathbb{Z}^+$ boş değil ($a^2 + b^2 > 0$). En küçük elemanı $d = ax_0 + by_0$ olsun. *$d \mid a$*: bölme algoritmasıyla $a = qd + r$, $0 \le r < d$. $r = a - q(ax_0 + by_0) = a(1 - qx_0) + b(-qy_0)$, yani $r$ de bir doğrusal birleşim. $r > 0$ olsaydı $S$'de $d$'den küçük olurdu; demek $r = 0$. Aynı şekilde $d \mid b$. Demek $d$ ortak bölen. *En büyük*: $c$, $a$ ve $b$'nin ortak böleniyse doğrusal birleşimlerini de böler (Ders 6.17), dolayısıyla $c \mid d$ ve $c \le d$. $\blacksquare$

Örnek: $\text{EBOB}(240, 46) = 2 = 240 \cdot (-9) + 46 \cdot 47$. Katsayılardan biri negatif; her zaman öyle (ikisi de pozitifse toplam $a$ ya da $b$'den büyük olurdu).

Bézout katsayıları tek değil: $(x + \frac{b}{d}k,\; y - \frac{a}{d}k)$ da çalışıyor. Ama **bir** tane bulmak yetiyor.

### Öklid önsavının kanıtı

Ders 6.17'de aritmetiğin temel teoreminin tekliği buna dayanıyordu.

**Önsav.** $p$ asal ve $p \mid ab$ ise $p \mid a$ ya da $p \mid b$.

**Kanıt.** $p \nmid a$ olsun. $p$ asal, tek bölenleri 1 ve $p$; demek $\text{EBOB}(p, a) = 1$. Bézout: $1 = px + ay$. $b$ ile çarp: $b = pbx + aby$. $p$ ilk terimi açıkça, ikinci terimi varsayımla ($p \mid ab$) bölüyor; dolayısıyla $p \mid b$. $\blacksquare$

Böylece Ders 6.17'deki zincir tamamlandı: Bézout → Öklid önsavı → çarpanlara ayırmanın tekliği.

---

## 2. Genişletilmiş Öklid algoritması

Bézout kanıtı varlıkçıydı; katsayıları **hesaplamak** için Öklid algoritmasını takip ediyoruz. Fikir: algoritmanın her adımındaki her sayıyı, başlangıçtaki $a$ ve $b$'nin doğrusal birleşimi olarak tutmak.

Başta $a = 1 \cdot a + 0 \cdot b$ ve $b = 0 \cdot a + 1 \cdot b$. Öklid her adımda $r = a - qb$ yapıyor. İki sayının katsayıları biliniyorsa, $r$'nin katsayıları aynı işlemle bulunuyor: $(x_a - q\, x_b,\; y_a - q\, y_b)$.

$a = 240$, $b = 46$ iz tablosu (Ders 1.3'teki gibi):

| $q$ | $r$ | $x$ | $y$ | kontrol: $240x + 46y$ |
| --- | --- | --- | --- | --- |
| | 240 | 1 | 0 | 240 |
| | 46 | 0 | 1 | 46 |
| 5 | 10 | 1 | −5 | 10 |
| 4 | 6 | −4 | 21 | 6 |
| 1 | 4 | 5 | −26 | 4 |
| 1 | 2 | −9 | 47 | 2 |
| 2 | 0 | 23 | −120 | 0 |

Her satır bir öncekinin iki satırından: $r$, $x$, $y$ sütunlarının üçü de "iki önceki $- q \cdot$ bir önceki" kuralıyla hesaplanıyor. Son sıfırdan önceki satır EBOB ve Bézout katsayıları: $2 = 240 \cdot (-9) + 46 \cdot 47$.

**Döngü değişmezi**: her satırda $r = 240x + 46y$. Başta doğru, her adım koruyor (doğrusal işlem doğrusal birleşimi koruyor), sonda istediğimizi veriyor. Ders 6.4'ün üç adımı.

```c
// d = ebob(a, b) ve a*x + b*y = d olacak x, y
static int64_t ext_gcd(int64_t a, int64_t b, int64_t *x, int64_t *y) {
    int64_t x0 = 1, y0 = 0;     // a = 1*a + 0*b
    int64_t x1 = 0, y1 = 1;     // b = 0*a + 1*b
    while (b != 0) {
        int64_t q = a / b, t;
        t = a - q * b;   a = b;   b = t;      // Oklid adimi
        t = x0 - q * x1; x0 = x1; x1 = t;     // ayni adim katsayilara
        t = y0 - q * y1; y0 = y1; y1 = t;
    }
    *x = x0; *y = y0;
    return a;
}
```

```
ebob(240, 46) = 2 = 240*(-9) + 46*(47)
```

Katsayılar en fazla $|b/d|$ ve $|a/d|$ büyüklüğünde kalıyor; `int64_t` girdilerle taşma yok. Adım sayısı Öklid'inkiyle aynı, $O(\log \min(a, b))$.

---

## 3. Modüler ters

$a$'nın mod $n$'deki **tersi**, $a x \equiv 1 \pmod n$ sağlayan $x$; $a^{-1}$ diye yazıyoruz.

**Teorem.** $a$'nın mod $n$'de tersi vardır $\iff$ $\text{EBOB}(a, n) = 1$.

**Kanıt.** ($\Leftarrow$) Bézout: $1 = ax + ny$. Mod $n$'de $ny \equiv 0$, kalan $ax \equiv 1$. Ters $x$. ($\Rightarrow$) $ax \equiv 1$ ise $ax - 1 = kn$, yani $1 = ax - kn$; 1, $a$ ve $n$'nin doğrusal birleşimi. Ortak her bölen 1'i böler, dolayısıyla $\text{EBOB} = 1$. $\blacksquare$

Kanıt bir algoritma da veriyor: genişletilmiş Öklid'i $a$ ve $n$'ye uygula, $x$'i al.

```c
// a'nin mod m tersi; yoksa false
static bool mod_inverse(int64_t a, int64_t m, int64_t *inv) {
    int64_t x, y;
    int64_t d = ext_gcd(((a % m) + m) % m, m, &x, &y);
    if (d != 1) return false;
    *inv = ((x % m) + m) % m;
    return true;
}
```

`((x % m) + m) % m`, Ders 6.17'deki C kalan düzeltmesi: $x$ negatif olabilir, ama ters $[0, m)$'de istiyoruz.

```
3^-1 mod 26 = 9
5^-1 mod 26 = 21
6'nin mod 26 tersi yok
10'nin mod 26 tersi yok
2^-1 mod p = 500000004
```

$3 \cdot 9 = 27 \equiv 1$, $5 \cdot 21 = 105 = 4 \cdot 26 + 1$. ✓ 6 ve 10, 26 ile ortak böleni 2 olduğu için tersiz. $p = 10^9 + 7$ asal olduğu için 1 ile $p - 1$ arasındaki **her** sayının tersi var; $2^{-1} = \frac{p + 1}{2}$.

Sonuçlar:

- $n = p$ asalsa sıfır dışındaki her sınıfın tersi var. $\mathbb{Z}/p\mathbb{Z}$'de toplama, çıkarma, çarpma **ve bölme** yapılabiliyor: Ders 6.24'te buna **cisim** diyeceğiz.
- Mod $n$'de tersi olan sınıfların sayısı, $n$ ile aralarında asal olanların sayısı: Ders 6.15'teki $\varphi(n)$.
- Mod $2^{32}$'de tersi olanlar tam olarak **tek** sayılar ($\text{EBOB}(a, 2^{32}) = 1 \iff a$ tek). Ders 6.9'da gözlemlediğimiz "tek sayıyla çarpma birebir örten" sonucunun kanıtı.

### Mod $2^k$'da hızlı ters

İkinin kuvvetlerinde daha da hızlı bir yol var, ve bölme bile gerektirmiyor. $x$, $a$'nın tersine $k$ bitte doğru bir yaklaşım olsun: $ax \equiv 1 \pmod{2^k}$. O zaman

$$
x' = x(2 - ax) \quad\Rightarrow\quad ax' \equiv 1 \pmod{2^{2k}}.
$$

(Kanıt: $ax = 1 + t\,2^k$ ise $ax' = (1 + t 2^k)(1 - t 2^k) = 1 - t^2 2^{2k}$.) Her adımda doğru bit sayısı **ikiye katlanıyor**. Başlangıç için bir hile: tek her $a$ için $a \cdot a \equiv 1 \pmod 8$, yani $x = a$ zaten 3 bit doğru.

```c
// tek a icin mod 2^32 ters: Newton, her adimda dogru bit sayisi ikiye katlanir
static uint32_t inverse_pow2(uint32_t a) {
    uint32_t x = a;               // a*a = 1 mod 8: 3 bit dogru
    for (int i = 0; i < 4; i++) x *= 2 - a * x;   // 3 -> 6 -> 12 -> 24 -> 48 bit
    return x;
}
```

```
inverse_pow2(5) = 0xCCCCCCCD, inverse_pow2(3) = 0xAAAAAAAB
ilk milyon tek sayi: 1
```

Dört çarpma-çıkarma adımı, hiç dal ve bölme yok. Ders 6.18'in 5. alıştırmasındaki sihirli sayılar böyle hesaplanıyor; derleyiciler tam bölme için sabitleri bu formülle üretiyor. Formül, analizdeki Newton yönteminin ($x' = x - f(x)/f'(x)$, $f(x) = 1/x - a$) modüler hali.

---

## 4. Doğrusal denklikler

$ax \equiv b \pmod n$ denklemini çöz.

- $\text{EBOB}(a, n) = 1$ ise tek çözüm (mod $n$): $x \equiv a^{-1} b$.
- Genel olarak $d = \text{EBOB}(a, n)$. Çözüm var $\iff$ $d \mid b$. Varsa $\frac{a}{d}x \equiv \frac{b}{d} \pmod{\frac{n}{d}}$'ye sadeleştir ve çöz; mod $n$'de $d$ tane çözüm çıkıyor.

Ders 6.18'deki örnek: $2x \equiv 2 \pmod{256}$. $d = 2 \mid 2$, sadeleştirince $x \equiv 1 \pmod{128}$; mod 256'da iki çözüm: 1 ve 129. "Bölme belirsiz" demiştik; işte tam olarak ne kadar belirsiz olduğu.

### $\binom{n}{k} \bmod p$

Ders 6.14'te Pascal üçgenini mod $p$'de kurmuştuk ($n^2$ işlem) çünkü çarpımsal formüldeki bölmeyi mod $p$'de yapamıyorduk. Artık yapabiliyoruz: $k! \bmod p$'nin tersiyle çarp.

$$
\binom{n}{k} \equiv n! \cdot (k!)^{-1} \cdot ((n-k)!)^{-1} \pmod p \qquad (n < p)
$$

```c
const int64_t P = 1000000007;
int64_t f[1001]; f[0] = 1;
for (int i = 1; i <= 1000; i++) f[i] = f[i - 1] * i % P;
int64_t ik, ink;
mod_inverse(f[500], P, &ik); mod_inverse(f[500], P, &ink);
printf("C(1000,500) mod p = %lld\n", (long long)(f[1000] * ik % P * ink % P));
```

```
C(1000,500) mod p = 159835829
```

Ders 6.14'teki Pascal sonucuyla aynı, ama $n^2$ yerine $O(n + \log p)$ işlemde. Çarpımlar $p^2 < 2^{63}$ olduğu için `int64_t`'ye sığıyor. ($n \ge p$ ise $n!$ mod $p$ sıfır olur ve bu yöntem çalışmaz; Lucas teoremi gerekiyor.)

---

## Alıştırmalar

**1** – $\text{EBOB}(1071, 462)$ için genişletilmiş Öklid iz tablosunu elle doldur, Bézout katsayılarını bul. Programla doğrula.

**2** – $17x \equiv 5 \pmod{43}$ ve $6x \equiv 4 \pmod{10}$ denklemlerini çöz. İkincisinin kaç çözümü var?

**3** – Affine şifre: bir harf $m \in \{0, \dots, 25\}$, $c = (am + b) \bmod 26$ olarak şifreleniyor. Hangi $a$ değerleri kullanılabilir (şifre çözülebilir olmalı)? Kaç anahtar $(a, b)$ var? $a = 5$, $b = 8$ için çözme formülünü yaz.

**4** – `inverse_pow2`'yi `uint64_t` için yaz. Kaç Newton adımı gerekiyor? Bir tek sayı için sonucu genişletilmiş Öklid ile (mod $2^{64}$'ü `__int128` ile temsil ederek) karşılaştır.

**5** – $1, \dots, n$'nin hepsinin mod $p$ terslerini $O(n)$'de hesaplayan bir formül var: $i^{-1} \equiv -\lfloor p / i \rfloor \cdot (p \bmod i)^{-1} \pmod p$. Neden doğru? (İpucu: $p = \lfloor p/i \rfloor \cdot i + (p \bmod i)$'yi mod $p$'de yaz.) Kodla ve `mod_inverse` ile karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – $1071 = 2 \cdot 462 + 147$; $462 = 3 \cdot 147 + 21$; $147 = 7 \cdot 21 + 0$. EBOB = 21.

| $q$ | $r$ | $x$ | $y$ |
| --- | --- | --- | --- |
| | 1071 | 1 | 0 |
| | 462 | 0 | 1 |
| 2 | 147 | 1 | −2 |
| 3 | 21 | −3 | 7 |
| 7 | 0 | 22 | −51 |

$21 = 1071 \cdot (-3) + 462 \cdot 7 = -3213 + 3234$. ✓

**2** – $17^{-1} \bmod 43$: $43 = 2 \cdot 17 + 9$, $17 = 9 + 8$, $9 = 8 + 1$; geri yerine koyunca $1 = 9 - 8 = 9 - (17 - 9) = 2 \cdot 9 - 17 = 2(43 - 2 \cdot 17) - 17 = 2 \cdot 43 - 5 \cdot 17$. Ters $-5 \equiv 38$. $x \equiv 38 \cdot 5 = 190 \equiv 190 - 172 = 18$. Kontrol: $17 \cdot 18 = 306 = 7 \cdot 43 + 5$. ✓ İkincisi: $d = \text{EBOB}(6, 10) = 2 \mid 4$. $3x \equiv 2 \pmod 5$, $3^{-1} = 2$, $x \equiv 4 \pmod 5$. Mod 10'da **iki** çözüm: 4 ve 9. ($6 \cdot 4 = 24 \equiv 4$, $6 \cdot 9 = 54 \equiv 4$ ✓)

**3** – Çözülebilmesi için $am$ mod 26'da birebir olmalı: $\text{EBOB}(a, 26) = 1$, yani $a$ tek ve 13 değil. $\varphi(26) = 12$ değer: $\{1, 3, 5, 7, 9, 11, 15, 17, 19, 21, 23, 25\}$. Anahtar sayısı $12 \cdot 26 = 312$ (kaba kuvvetle anında kırılır). $a = 5$: $5^{-1} = 21$ (yukarıda). Çözme: $m \equiv 21(c - 8) \pmod{26}$.

**4** – `uint64_t` için 3 → 6 → 12 → 24 → 48 → 96 bit: **5** adım (dördüncüsünden sonra 48 bit, yetmiyor).

```c
uint64_t inverse_pow2_64(uint64_t a) {
    uint64_t x = a;
    for (int i = 0; i < 5; i++) x *= 2 - a * x;
    return x;
}
```

Genişletilmiş Öklid ile: `ext_gcd`'yi `__int128` üzerinden $a$ ve $2^{64}$ için çalıştır, $x$'i mod $2^{64}$'e indir. İkisi aynı sonucu veriyor (ters tek olduğu için); Newton beş çarpma, Öklid yaklaşık 40 bölme.

**5** – $p = qi + r$, $q = \lfloor p/i \rfloor$, $r = p \bmod i$. Mod $p$'de $0 \equiv qi + r$, yani $qi \equiv -r$. İki tarafı $i^{-1} r^{-1}$ ile çarp: $q r^{-1} \equiv -i^{-1}$, yani $i^{-1} \equiv -q\, r^{-1}$. $r < i$ olduğu için $r^{-1}$ zaten hesaplanmış.

```c
int64_t inv[1001]; inv[1] = 1;
for (int i = 2; i <= 1000; i++)
    inv[i] = (P - (P / i) * inv[P % i] % P) % P;
```

Her $i$ için $i \cdot \text{inv}[i] \equiv 1$ kontrolü ve `mod_inverse` ile aynı sonuç. Her ters tek bir çarpma; $n$ ters $O(n)$'de. (Dinamik programlama: büyük problemin cevabını küçüklerden kurmak, Faz 9.)

</details>

---

## Kaynaklar

- Donald Knuth, *TAOCP* Cilt 2, §4.5.2: genişletilmiş Öklid algoritması ve analizi.
- Kenneth Rosen, *Elementary Number Theory and Its Applications* (6. baskı), §3.4 ve §4.2: Bézout, doğrusal denklikler.
- Henry Warren, *Hacker's Delight* (2. baskı), §10-16: Newton yöntemiyle mod 2ⁿ ters.
- Thomas Cormen ve diğ., *Introduction to Algorithms* (4. baskı), §31.2–31.4.

**Sıradaki ders:** Çin kalan teoremi ve Fermat/Euler. Birden çok modda verilen bilgiyi birleştirmek, $a^{p-1} \equiv 1$, ve büyük sayıların asallığını olasılıksal olarak test eden Miller–Rabin.
