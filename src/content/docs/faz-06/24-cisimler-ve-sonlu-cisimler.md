---
title: "6.24 Cisimler ve sonlu cisimler"
description: "Cisim tanımı: sıfır dışındaki her elemanın tersi olan değişmeli halka; Q, R ve Z/pZ; Z/nZ'nin ancak n asalken cisim olması; karakteristik; polinom halkası F[x], polinom bölmesi ve indirgenemez polinom; GF(2ⁿ)'nin GF(2)[x]'in bir indirgenemez polinoma göre kalanları olarak kurulması; 8 bitlik bir byte'ın GF(2⁸)'in bir elemanı olması, toplamanın XOR olması; AES polinomu 0x11B ile kaydır-ve-topla çarpma, üreteç 3 ile log/exp tabloları ve ters alma; Reed–Solomon ve AES'e bağlantı."
---

Ders 6.23'te $\mathbb{Z}/256$'da her çift sayının bir sıfır bölen olduğunu, bölmenin yapılamadığını gördük. Ders 6.19'da ise $\mathbb{Z}/p$'de ($p$ asal) sıfır dışındaki her elemanın tersi vardı. Toplama, çıkarma, çarpma **ve bölmenin** hepsinin yapılabildiği yapıya **cisim** (field) denir. Rasyonel ve gerçel sayılar cisim; ama bilgisayar için asıl ilginç olanlar **sonlu** cisimler.

Bu dersin varacağı yer şaşırtıcı: 8 bitlik bir byte, 256 elemanlı bir cismin elemanı olarak düşünülebilir, ve o cisimde her sıfır olmayan byte'ın tersi var. `uint8_t`'nin olağan aritmetiğinde ($\mathbb{Z}/256$) bu imkânsız. AES şifrelemesi, QR kodlarındaki ve CD'lerdeki Reed–Solomon hata düzeltmesi ve RAID-6 bu cisimde çalışıyor.

---

## 1. Tanım

Bir **cisim** $(F, +, \cdot)$, şunları sağlayan bir değişmeli halka (Ders 6.23):

- $1 \ne 0$
- Sıfır dışındaki her $a$'nın bir çarpma tersi $a^{-1}$ var.

Yani $(F, +)$ değişmeli bir grup, $(F \setminus \{0\}, \cdot)$ da değişmeli bir grup, ve dağılma ikisini bağlıyor. Cisimde $\frac{a}{b} = a b^{-1}$ ($b \ne 0$) tanımlı; Gauss eliminasyonu (Ders 6.26), polinom bölmesi, doğrusal cebirin bütün aletleri çalışıyor.

Bir cisim her zaman bir tamlık bölgesi: $ab = 0$ ve $a \ne 0$ ise $b = a^{-1} a b = 0$. Sıfır bölen yok.

| Yapı | Cisim mi |
| --- | --- |
| $\mathbb{Q}$, $\mathbb{R}$, $\mathbb{C}$ | evet (sonsuz) |
| $\mathbb{Z}$ | hayır (2'nin tersi yok) |
| $\mathbb{Z}/p\mathbb{Z}$, $p$ asal | evet, $p$ elemanlı; $GF(p)$ ya da $\mathbb{F}_p$ |
| $\mathbb{Z}/n\mathbb{Z}$, $n$ bileşik | hayır (sıfır bölenler) |
| `double` | hayır (halka bile değil, Ders 6.23) |

**Teorem.** $\mathbb{Z}/n\mathbb{Z}$ bir cisimdir $\iff$ $n$ asaldır.

**Kanıt.** $n$ asalsa $1, \dots, n-1$'in hepsi $n$ ile aralarında asal, hepsinin tersi var (Ders 6.19). $n = ab$ bileşikse ($1 < a, b < n$) $a \cdot b \equiv 0$; $a$ sıfır bölen, cisimde olamaz. $\blacksquare$

Demek 256 elemanlı bir cisim istiyorsak $\mathbb{Z}/256$ işe yaramıyor. Başka bir yapı lazım.

### Karakteristik

Bir cisimde $1 + 1 + \dots + 1$'i toplamaya devam et. Sonlu bir cisimde bir yerde 0'a ulaşırsın (güvercin yuvası). $p$ tane 1'in toplamı 0 olan en küçük $p$'ye **karakteristik** denir. Karakteristik her zaman **asal**: $p = ab$ olsaydı $(a \cdot 1)(b \cdot 1) = 0$ ve cisimde sıfır bölen olmaz. $GF(p)$'nin karakteristiği $p$; bu dersin cisimlerinin karakteristiği **2**: $1 + 1 = 0$, yani $a + a = 0$ ve **çıkarma = toplama**.

---

## 2. Polinomlar ve indirgenemezlik

$F$ bir cisimse $F[x]$, katsayıları $F$'den olan polinomlar. Ders 6.23'teki gibi bir değişmeli halka. Tamsayılara çok benziyor:

- **Bölme algoritması** var (Ders 6.17'nin polinom hali): $f = q \cdot g + r$, $\deg r < \deg g$. Cisim olması şart: bölerken önde gelen katsayıya bölüyorsun.
- **EBOB** ve **Öklid algoritması** var (Faz 12'de yazacağız).
- **İndirgenemez** polinomlar asalların karşılığı: daha küçük dereceli iki polinomun çarpımı olarak yazılamayan polinom.

Bu derste $F = GF(2) = \{0, 1\}$: katsayılar bitler, toplama XOR, çarpma AND. $GF(2)[x]$'te bir polinomu **bitleriyle** yazabiliyoruz:

$$
x^8 + x^4 + x^3 + x + 1 \;\longleftrightarrow\; \texttt{1 0001 1011} = \texttt{0x11B}
$$

Bit $i$, $x^i$'nin katsayısı. Toplama katsayı katsayı XOR: $(x^2 + x) + (x + 1) = x^2 + 1$, yani `0b110 ^ 0b011 = 0b101`. Elde yok! Polinom toplamasında $x + x = 2x = 0$, taşma diye bir şey olmuyor. Ders 5.19'daki CRC tam olarak bu aritmetikte bir polinom bölmesinin kalanıydı.

**İndirgenemezlik örnekleri** ($GF(2)$ üzerinde): $x^2 + x + 1$ indirgenemez (kökü yok: $0^2 + 0 + 1 = 1$, $1 + 1 + 1 = 1$; ikinci dereceden bir polinom ancak doğrusal çarpanı varsa indirgenebilir). $x^2 + 1 = (x + 1)^2$ indirgenebilir (çünkü $x^2 + 2x + 1 = x^2 + 1$, $2 = 0$). $x^8 + x^4 + x^3 + x + 1$ indirgenemez; AES standardı bunu seçti.

---

## 3. $GF(2^n)$'nin kurulumu

Ders 6.18'de $\mathbb{Z}/p$'yi kurmak için tamsayıları bir **asala göre kalanlarla** değiştirdik. Aynı fikri polinomlara uygula: $GF(2)[x]$'i bir **indirgenemez** $m(x)$ polinomuna göre kalanlarla değiştir.

$$
GF(2^n) = GF(2)[x] / (m(x)), \qquad \deg m = n.
$$

- **Elemanlar**: derecesi $n$'den küçük polinomlar, yani $n$ bitlik desenler. $2^n$ tane.
- **Toplama**: polinom toplaması, yani **XOR**.
- **Çarpma**: polinomları çarp, sonra $m(x)$'e böl, kalanı al.

**Teorem.** $m$ indirgenemezse bu bir cisimdir.

**Kanıt fikri.** Sıfır olmayan her $a(x)$ için, $m$ indirgenemez olduğundan $\text{EBOB}(a, m) = 1$. Polinomlar için Bézout (Ders 6.19, aynı kanıt): $a u + m v = 1$. Mod $m$'de $a u \equiv 1$. Ters var. $\blacksquare$

Tamsayılarla birebir paralel: asal ↔ indirgenemez, $\mathbb{Z}/p$ ↔ $GF(2)[x]/(m)$. Ve bir derin teorem (Galois): her asal kuvveti $p^n$ için **tam olarak bir** (izomorfizm altında) $p^n$ elemanlı cisim var, başka mertebeden sonlu cisim yok. Hangi indirgenemez $m$'yi seçersen seç, aynı cismi farklı adlarla kuruyorsun.

### Çarpmayı bitlerle yapmak

$GF(2^8)$'de $a \cdot x$: polinomu bir derece kaydır, yani `a << 1`. Eğer $x^7$ katsayısı 1 idiyse sonuçta $x^8$ çıkar ve onu $m(x)$ ile azaltmak gerekir: $x^8 \equiv x^4 + x^3 + x + 1$ (çünkü $m(x) \equiv 0$ ve $-1 = 1$). Yani `0x1B`'yi XOR'la. AES standardında bu işlemin adı `xtime`:

```c
// GF(2^8), AES polinomu: x^8 + x^4 + x^3 + x + 1 = 0x11B
static uint8_t xtime(uint8_t a) {                 // a * x
    return (uint8_t)((a << 1) ^ ((a & 0x80) ? 0x1B : 0));
}
```

Genel çarpma, Ders 5.13'teki kaydır-ve-topla çarpmanın aynısı, ama iki farkla: toplama `+` değil `^`, ve kaydırma `xtime` (taşan biti indirgiyor):

```c
static uint8_t gf_mul(uint8_t a, uint8_t b) {     // kaydir-ve-topla, toplama = XOR
    uint8_t r = 0;
    while (b) {
        if (b & 1) r ^= a;
        a = xtime(a);
        b >>= 1;
    }
    return r;
}
```

AES standardındaki (FIPS-197) örneklerle doğrulayalım:

```
{57} * {83} = {c1}
{57} * {13} = {fe}
```

Standarttaki değerlerle aynı. Elde zinciri yok, her bit bağımsız; bu yüzden donanımda $GF(2^n)$ çarpması tamsayı çarpmasından ucuz, ve modern işlemcilerde tek komut (`pclmulqdq`, "carry-less multiply").

---

## 4. Log tabloları ve ters

$(GF(2^8) \setminus \{0\}, \cdot)$, 255 elemanlı bir grup ve Ders 6.22'deki teoreme göre **devirli** (sonlu bir cismin çarpma grubu her zaman devirli). Bir üreteç $g$ bulursak her sıfır olmayan eleman $g^i$ olarak yazılır ve

$$
a \cdot b = g^{\log a + \log b}, \qquad a^{-1} = g^{255 - \log a}.
$$

Ders 6.21'deki izomorfizm: çarpma grubu $\cong$ $\mathbb{Z}/255$ toplaması. AES polinomunda $x$ (yani 2) üreteç **değil**:

```
2'nin mertebesi: 51
```

51, 255'i bölüyor (Lagrange; $255 = 3 \cdot 5 \cdot 17$) ama eşit değil. $x + 1$ (yani 3) bir üreteç:

```c
static uint8_t exp_t[512], log_t[256];

static void build_tables(void) {
    uint8_t x = 1;
    for (int i = 0; i < 255; i++) {
        exp_t[i] = exp_t[i + 255] = x;             // 3^i
        log_t[x] = (uint8_t)i;
        x = gf_mul(x, 3);                           // 3 bir uretec
    }
}

static uint8_t gf_mul_log(uint8_t a, uint8_t b) {
    if (a == 0 || b == 0) return 0;
    return exp_t[log_t[a] + log_t[b]];             // carpma = uslerin toplami
}

static uint8_t gf_inv(uint8_t a) {                 // a != 0
    return exp_t[255 - log_t[a]];
}
```

`exp_t`'nin iki kat uzun olması bir hile: $\log a + \log b$ en fazla 508, ve mod 255 almak yerine tabloyu tekrarlıyoruz; dal ve bölme yok.

```
log tablosu = kaydir-topla: 1, tersi olan eleman: 255
{53}^-1 = {ca}, kontrol {53}*{ca} = {01}
dagilma: 1
Z/256'da 2*b = 1 cozumu: 0
```

- İki çarpma yöntemi 65536 çiftin hepsinde aynı.
- 255 sıfır olmayan elemanın **hepsinin** tersi var: bir cisim. `uint8_t`'nin olağan çarpmasında ($\mathbb{Z}/256$) 2'nin tersi yok; $GF(2^8)$'de var.
- Dağılma $a(b \oplus c) = ab \oplus ac$, $2^{24}$ üçlünün hepsinde.
- $\{53\}^{-1} = \{\text{ca}\}$, FIPS-197'deki örnek. AES'in S-kutusu, her byte'ı $GF(2^8)$'deki tersine (0'ı 0'a) gönderip üstüne sabit bir bit dönüşümü uyguluyor. Ters alma, doğrusal olmadığı için şifreye "karışıklık" veriyor.

Aynı 256 bit deseni, iki farklı halka yapısı: $\mathbb{Z}/256$ (`+`, `*`: sayılar için) ve $GF(2^8)$ (`^`, `gf_mul`: kodlama ve kriptografi için). Hangi işlemleri seçtiğin, verinin hangi cebire ait olduğunu belirliyor.

### Neden işe yarıyor: Reed–Solomon

Bir cisim üzerinde, $k$ dereceli bir polinom $k + 1$ noktadaki değerleriyle **tek türlü** belirleniyor (Ders 6.26'da doğrusal sistem olarak kanıtlayacağız). Reed–Solomon kodu, $k$ byte'lık veriyi bir polinomun katsayıları olarak görüp polinomu $n > k$ noktada değerlendiriyor ve $n$ byte gönderiyor. Herhangi $k$ byte sağlam ulaşırsa polinom ve veri geri kurulabiliyor; $n - k$ byte'a kadar kayıp tolere ediliyor. Bütün hesap $GF(2^8)$'de, çünkü bölme (interpolasyon için) gerekli ve her sembol tam bir byte. QR kodlar, CD/DVD'ler, Voyager'ın görüntüleri ve RAID-6 bu yöntemi kullanıyor.

---

## Alıştırmalar

**1** – $GF(4) = GF(2)[x]/(x^2 + x + 1)$'in 4 elemanını ($0, 1, x, x + 1$) 2 bitlik desenlerle yaz, toplama ve çarpma tablolarını elle doldur. Ders 6.21'deki `is_group` ile çarpma tablosunun (sıfırsız) grup olduğunu denetle. $\mathbb{Z}/4$ ile farkı ne?

**2** – $GF(2)$ üzerinde 3. dereceden bütün polinomları (8 tane) dene ve indirgenemezleri bul. (3. dereceden bir polinom ancak bir kökü varsa indirgenebilir; 0 ve 1'i dene.)

**3** – $GF(2^8)$'de bütün **üreteçleri** say. Kaç tane? Ders 6.15'teki $\varphi(255)$ ile karşılaştır. (Devirli bir $n$ elemanlı grubun $\varphi(n)$ üreteci var.)

**4** – `gf_mul`'u dalsız yaz (Ders 5.5): `if (b & 1)` yerine bir maske, `(a & 0x80) ? 0x1B : 0` yerine bir maske. Kriptografide bunun neden önemli olduğunu açıkla (zamanlama saldırıları).

**5** – $GF(2^8)$'de $a^{255} = 1$ ve dolayısıyla $a^{-1} = a^{254}$ ($a \ne 0$). Bunu `gf_mul` ile kareleme–çarpma kullanarak hesapla ve `gf_inv` ile karşılaştır. Hangi teorem bunu garanti ediyor?

<details>
<summary>Cevaplar</summary>

**1** – $x^2 = x + 1$ (çünkü $x^2 + x + 1 = 0$ ve $-1 = 1$). Elemanlar: $0 = 00$, $1 = 01$, $x = 10$, $x + 1 = 11$. Toplama XOR. Çarpma:

| $\cdot$ | 1 | $x$ | $x+1$ |
| --- | --- | --- | --- |
| **1** | 1 | $x$ | $x+1$ |
| **$x$** | $x$ | $x+1$ | 1 |
| **$x+1$** | $x+1$ | 1 | $x$ |

($x(x+1) = x^2 + x = 1$; $(x+1)^2 = x^2 + 1 = x$.) Sıfırsız 3 eleman bir grup, $\mathbb{Z}/3$ ile izomorf ($x$ üreteç). $\mathbb{Z}/4$'te $2 \cdot 2 = 0$, cisim değil; $GF(4)$'te sıfır bölen yok. İkisi de 4 elemanlı ama farklı halkalar; toplama grupları bile farklı ($GF(4)$: her eleman kendi tersi; $\mathbb{Z}/4$: $1 + 1 \ne 0$).

**2** – $x^3 + ax^2 + bx + c$: $c = 0$ ise $x$ çarpan, indirgenebilir. $c = 1$ olanlar: $x^3 + 1$ (kök 1: $1 + 1 = 0$), $x^3 + x + 1$ (kök yok: $0 \to 1$, $1 \to 1$), $x^3 + x^2 + 1$ (kök yok), $x^3 + x^2 + x + 1$ (kök 1). İndirgenemezler: $x^3 + x + 1$ (`0xB`) ve $x^3 + x^2 + 1$ (`0xD`). İkisi de $GF(8)$'i kuruyor; ve iki cisim izomorf.

**3** –

```c
int gens = 0;
for (int g = 1; g < 256; g++) {
    int ord = 1; uint8_t y = g;
    while (y != 1) { y = gf_mul(y, g); ord++; }
    gens += (ord == 255);
}
// gens = 128
```

$\varphi(255) = 255 \cdot \frac23 \cdot \frac45 \cdot \frac{16}{17} = 128$. Devirli bir grupta $g^k$'nın üreteç olması $\text{EBOB}(k, n) = 1$ demek; ve bu $k$'lar $\varphi(n)$ tane.

**4** –

```c
static uint8_t gf_mul_ct(uint8_t a, uint8_t b) {
    uint8_t r = 0;
    for (int i = 0; i < 8; i++) {
        r ^= a & (uint8_t)-(b & 1);                         // b'nin alt biti 1 ise a, degilse 0
        a = (uint8_t)((a << 1) ^ (0x1B & (uint8_t)-(a >> 7)));
        b >>= 1;
    }
    return r;
}
```

`(uint8_t)-(b & 1)`: bit 1 ise `0xFF`, 0 ise `0x00`. Döngü her zaman 8 tur (`while (b)` erken bitirirdi). Dallı sürümde süre, gizli anahtarın bitlerine bağlı; bir saldırgan yeterince ölçüm yaparak anahtarı çıkarabiliyor. Log tablosu da tehlikeli: tablo erişimleri cache'te farklı süreler alıyor ve hangi indekse erişildiğini sızdırıyor (2005'te AES'e karşı gerçek saldırılar). Bu yüzden modern AES uygulamaları ya dalsız bit işlemleri ya da donanım komutları (AES-NI) kullanıyor.

**5** – $a^{254} = a^{128} a^{64} a^{32} a^{16} a^8 a^4 a^2$ (254 = `11111110`): 7 kareleme, 6 çarpma. 255 sıfır olmayan elemanın hepsinde `gf_inv` ile aynı. Garanti: Lagrange (Ders 6.22), 255 elemanlı grupta $a^{255} = 1$; bu, Fermat'ın $GF(2^8)$ hali. Tablo yöntemi iki bellek okuması, üs yöntemi 13 `gf_mul`; ama üs yöntemi dalsız `gf_mul_ct` ile sabit zamanlı.

</details>

---

## Kaynaklar

- Charles Pinter, *A Book of Abstract Algebra* (2. baskı), Bölüm 24–27 ve 33: polinom halkaları, indirgenemezlik, sonlu cisimler.
- NIST, *FIPS-197: Advanced Encryption Standard* (2001), §4: $GF(2^8)$ aritmetiği, `xtime` ve örnekler.
- Rudolf Lidl & Harald Niederreiter, *Introduction to Finite Fields and Their Applications*.
- James Plank, "A Tutorial on Reed–Solomon Coding for Fault-Tolerance in RAID-like Systems", *Software: Practice and Experience* 27(9), 1997.

**Sıradaki ders:** Vektörler ve matrisler. Vektör uzayı, matris çarpımı, ve C'de küçük bir matris kütüphanesi.
