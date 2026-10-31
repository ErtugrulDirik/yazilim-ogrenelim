---
title: "6.9 Fonksiyonlar"
description: "Fonksiyonu özel bir bağıntı olarak tanımlamak; tanım kümesi, değer kümesi ve görüntü; birebir, örten ve birebir örten fonksiyonlar ve C'de denetlenmeleri; tek sayıyla çarpmanın mod 256'da birebir örten olması ve tersi; bileşke ve ters fonksiyon; kardinaliteyi eşlemeyle karşılaştırmak, ℕ × ℕ'nin sayılabilir olduğunu gösteren Cantor eşleme fonksiyonu, Cantor köşegen yöntemiyle sayılamazlık ve hesaplanamayan fonksiyonların varlığı."
---

Ders 2.7'den beri "fonksiyon" kelimesini kullanıyoruz: girdi alan, çıktı veren bir kod parçası. Matematikteki fonksiyon daha basit ve daha genel: kodu yok, sadece **hangi girdinin hangi çıktıya gittiği**. Ders 6.6'nın diliyle, özel bir bağıntı.

Bu derste fonksiyonların üç önemli özelliğini (birebir, örten, ikisi birden) göreceğiz ve sonra bunları beklenmedik bir yerde kullanacağız: sonsuz kümeleri karşılaştırmakta. Varacağımız yer, bilgisayarların **hesaplayamayacağı** fonksiyonların var olduğu.

---

## 1. Tanım

$A$'dan $B$'ye bir **fonksiyon** $f : A \to B$, her $a \in A$'yı **tam olarak bir** $b \in B$ ile ilişkilendiren bir bağıntıdır:

$$
\forall a \in A\; \exists!\, b \in B\; (a, b) \in f
$$

($\exists!$: "tam olarak bir tane var".) Bu $b$'yi $f(a)$ diye yazıyoruz.

- $A$: **tanım kümesi** (domain)
- $B$: **değer kümesi** (codomain)
- $f(A) = \{f(a) \mid a \in A\}$: **görüntü** (image, range). Gerçekten ulaşılan değerler; $B$'nin bir alt kümesi.

Tanımda iki şart var ve ikisi de önemli:

- **Her** $a$'nın bir çıktısı var. Bazı girdilerde tanımsız olan "fonksiyonlara" **kısmi fonksiyon** denir: $\sqrt{x}$ gerçel sayılarda $x < 0$ için, `1 / x` ise $x = 0$ için tanımsız. C'de sonsuz döngüye giren ya da undefined behavior'a düşen her fonksiyon matematiksel olarak kısmi.
- Her $a$'nın **tek** çıktısı var. Aynı girdiye bazen 3, bazen 5 veren şey fonksiyon değil. C'de `rand()` ya da global bir değişkeni okuyan bir fonksiyon, matematiksel anlamda parametrelerinin fonksiyonu değil; gizli bir girdisi (durum) var.

Sonlu bir tanım kümesinde bir fonksiyon en kolay bir **dizi** ile temsil ediliyor: `f[x]`. Ders 5'teki arama tabloları (lookup table) tam bu; Ders 5.8'deki 256 elemanlı popcount tablosu bir $\{0, \dots, 255\} \to \{0, \dots, 8\}$ fonksiyonuydu.

```c
#define M 256   // tanim ve deger kumesi: {0, ..., 255}

typedef uint8_t fn8[M];   // f[x] = f(x)
```

---

## 2. Birebir, örten, birebir örten

| Özellik | Tanım | Sezgisi |
| --- | --- | --- |
| **Birebir** (injective) | $f(a_1) = f(a_2) \to a_1 = a_2$ | farklı girdiler farklı çıktılara gider; bilgi kaybolmaz |
| **Örten** (surjective) | $\forall b \in B\; \exists a \in A\; f(a) = b$ | $B$'nin her elemanına ulaşılır; görüntü $= B$ |
| **Birebir örten** (bijective) | ikisi birden | $A$ ve $B$ arasında kusursuz bir eşleme |

Birebirliğin karşıt tersi (Ders 6.3) daha sezgisel: $a_1 \ne a_2 \to f(a_1) \ne f(a_2)$.

Kontrol etmek için Ders 6.2'deki gibi $\forall$'ları döngülere çeviriyoruz. Birebirlik için çiftleri karşılaştırmak yerine görülen çıktıları işaretlemek daha hızlı: ikinci kez görülen bir çıktı, iki girdinin çarpıştığı anlamına geliyor.

```c
static bool injective(const fn8 f) {
    bool seen[M] = {false};
    for (int x = 0; x < M; x++) {
        if (seen[f[x]]) return false;   // iki girdi ayni ciktiya gitti
        seen[f[x]] = true;
    }
    return true;
}

static bool surjective(const fn8 f) {
    bool hit[M] = {false};
    for (int x = 0; x < M; x++) hit[f[x]] = true;
    for (int y = 0; y < M; y++)
        if (!hit[y]) return false;      // y'ye hicbir girdi gitmiyor
    return true;
}
```

`uint8_t` aritmetiğindeki bazı fonksiyonları deneyelim (`uint8_t` sonucu mod 256 alıyor, Ders 3.8):

```c
static void build_mul(fn8 f, unsigned k) {
    for (int x = 0; x < M; x++) f[x] = (uint8_t)(x * k);
}
```

```
x*2 mod 256: birebir=0 orten=0
x*3 mod 256: birebir=1 orten=1
x*4 mod 256: birebir=0 orten=0
x*5 mod 256: birebir=1 orten=1
x>>1:        birebir=0 orten=0
```

İlginç bir desen: **tek** sayıyla çarpmak birebir örten, **çift** sayıyla çarpmak ikisi de değil. Çift sayıyla çarpınca en üst bit kayboluyor: $x \cdot 2$, $x$ ile $x + 128$'i aynı yere götürüyor ($2 \cdot 128 = 256 \equiv 0$). Tek sayıyla çarpmada hiçbir bilgi kaybolmuyor; nedenini Ders 6.19'da kanıtlayacağız (tek sayılar 256 ile aralarında asal). `x >> 1` ise hem en alt biti kaybediyor (birebir değil) hem de 127'den büyük sonuç veremiyor (örten değil).

**Teorem.** $A$ ve $B$ sonlu ve $|A| = |B|$ ise, $f : A \to B$ için birebir $\iff$ örten.

**Kanıt** (birebir $\to$ örten). $f$ birebirse $|A|$ farklı girdi $|A|$ farklı çıktı veriyor, yani $|f(A)| = |A| = |B|$. $f(A) \subseteq B$ ve aynı büyüklükte; sonlu kümelerde bu $f(A) = B$ demek. Diğer yön benzer. $\blacksquare$

Yukarıdaki tablo bunu doğruluyor: her satırda iki sütun aynı. Ve bir sonuç: $|A| > |B|$ ise $f$ birebir **olamaz**; en az iki girdi aynı çıktıya gitmek zorunda. Bu, Ders 6.15'teki **güvercin yuvası ilkesi**: 32 bitlik bir hash fonksiyonu, $2^{32}$'den fazla farklı stringi birebir eşleyemez, çakışma kaçınılmaz.

---

## 3. Bileşke ve ters

İki fonksiyon arka arkaya: $f : A \to B$ ve $g : B \to C$ ise **bileşke** $g \circ f : A \to C$,

$$
(g \circ f)(x) = g(f(x)).
$$

Okuma yönüne dikkat: $g \circ f$'de **önce $f$**, sonra $g$ uygulanıyor. Kodda `g(f(x))`, ya da sonlu fonksiyonlarda `g[f[x]]`.

$f : A \to B$ birebir örtense, her $b$'nin tam olarak bir ön görüntüsü var ve **ters fonksiyon** $f^{-1} : B \to A$ tanımlı:

$$
f^{-1}(b) = a \iff f(a) = b, \qquad f^{-1} \circ f = \text{id}_A, \qquad f \circ f^{-1} = \text{id}_B
$$

$\text{id}_A(x) = x$, **birim fonksiyon**. Birebir değilse ters tanımlanamaz (hangi $a$'ya geri döneceğini bilemezsin); örten değilse bazı $b$'lerin geri gideceği yer yok.

```c
static void compose(fn8 r, const fn8 g, const fn8 f) {   // r = g o f
    for (int x = 0; x < M; x++) r[x] = g[f[x]];
}

static void inverse(fn8 r, const fn8 f) {                // f birebir orten olmali
    for (int x = 0; x < M; x++) r[f[x]] = (uint8_t)x;
}
```

`inverse`, tabloyu ters çeviriyor: $f(x) = y$ ise $r[y] = x$. Birebir örten olmasaydı bazı `r[y]`'ler iki kez yazılır, bazıları hiç yazılmazdı.

```c
build_mul(f, 5);
inverse(g, f);
compose(h, g, f);   // h = g o f, birim olmali
```

```
5'in tersi: g(1) = 205, 5*205 mod 256 = 1
g o f = birim: 1
```

$5 \cdot 205 = 1025 = 4 \cdot 256 + 1$. Yani mod 256'da $205$, $5$'in **çarpımsal tersi**: 5 ile çarpmayı 205 ile çarpmak geri alıyor. Ders 5.14'te sabite bölmeyi çarpmaya çevirmiştik; tam bölünen sayılarda $x / 5$, $x \cdot 205 \bmod 256$ (ya da 32 bitte $x \cdot \text{0xCCCCCCCD}$) ile **tam** hesaplanabiliyor, çünkü $x = 5q$ ise $5q \cdot 205 \equiv q$. Bu tersi tabloyu çevirmeden, doğrudan hesaplamayı Ders 6.19'daki genişletilmiş Öklid algoritmasıyla öğreneceğiz.

**Teorem.** İki birebir örten fonksiyonun bileşkesi birebir örtendir, ve $(g \circ f)^{-1} = f^{-1} \circ g^{-1}$.

Ters sıraya dikkat: önce çorap sonra ayakkabı giyiyorsan, çıkarırken önce ayakkabı sonra çorap. Ders 6.21'de gruplar bu yasa üzerine kuruluyor.

---

## 4. Sonsuzluğu saymak

İki sonlu kümenin aynı büyüklükte olduğunu saymadan da gösterebiliriz: aralarında **birebir örten bir fonksiyon** kurarak. Sınıfta oturan öğrencilerle sandalyeler: her öğrenci bir sandalyede, her sandalyede bir öğrenci varsa, saymadan sayıların eşit olduğunu biliyoruz.

Cantor'un fikri: bu tanımı **sonsuz** kümelere de uygulamak. $A$ ile $B$ arasında birebir örten bir fonksiyon varsa $|A| = |B|$.

$\mathbb{N}$ ile aynı büyüklükteki kümelere **sayılabilir sonsuz** (countably infinite) denir: elemanlarını $0, 1, 2, \dots$ diye bir listeye dizebiliyorsun. Sonuçlar sezgiye ters:

**Çift sayılar** $\mathbb{N}$ kadar: $f(n) = 2n$ birebir örten. Bir parça, bütün kadar büyük.

**Tamsayılar** $\mathbb{N}$ kadar: $0, -1, 1, -2, 2, -3, \dots$ diye listele. Fonksiyon olarak: $n$ çiftse $n / 2$, tekse $-(n+1)/2$. (Protobuf ve benzeri formatların "zigzag" kodlaması tam bu eşlemeyi kullanıyor: küçük negatif sayıları küçük pozitif sayılara çevirip az byte ile yazıyor.)

**$\mathbb{N} \times \mathbb{N}$** de $\mathbb{N}$ kadar! İkilileri bir tabloya yerleştir ve **köşegenler boyunca** say:

```
      b=0  b=1  b=2  b=3
a=0     0    2    5    9
a=1     1    4    8   13
a=2     3    7   12   18
a=3     6   11   17   24
```

$a + b = d$ olan ikililer $d$'inci köşegende; ondan önceki köşegenlerde toplam $1 + 2 + \dots + d = \frac{d(d+1)}{2}$ ikili var (Ders 6.4). Bu, **Cantor eşleme fonksiyonu**:

$$
\pi(a, b) = \frac{(a + b)(a + b + 1)}{2} + b
$$

```c
static uint64_t pair(uint64_t a, uint64_t b) { return (a + b) * (a + b + 1) / 2 + b; }

static void unpair(uint64_t z, uint64_t *a, uint64_t *b) {
    uint64_t d = 0;
    while ((d + 1) * (d + 2) / 2 <= z) d++;   // d = a + b: z'nin dustugu kosegen
    *b = z - d * (d + 1) / 2;
    *a = d - *b;
}
```

`unpair(17)` $(3, 2)$ veriyor; tabloda 17, $a = 3$, $b = 2$ hücresinde. İlk yüz bin sayı için `pair(unpair(z)) == z` doğru. İki sayıyı tek sayıya, kayıpsız ve geri döndürülebilir biçimde paketledik.

Aynı yöntemle $\mathbb{Q}$ (her kesir bir $(p, q)$ ikilisi), bütün sonlu stringler, bütün sonlu sayı listeleri, ve **bütün C programları** (her program sonlu bir byte dizisi) sayılabilir. Program metinlerini önce uzunluğa, sonra sözlük sırasına (Ders 6.7) göre dizersen hepsini $0, 1, 2, \dots$ diye numaralandırabilirsin.

---

## 5. Cantor köşegen yöntemi

Peki **her** sonsuz küme sayılabilir mi? Hayır, ve kanıtı matematiğin en güzel kanıtlarından biri.

**Teorem (Cantor).** $\mathbb{N}$'den $\{0, 1\}$'e bütün fonksiyonların kümesi (yani sonsuz bit dizileri) sayılabilir değildir.

**Kanıt** (çelişkiyle). Sayılabilir olduğunu varsayalım: bütün sonsuz bit dizilerini bir listeye dizebiliyoruz, $s_0, s_1, s_2, \dots$ $s_i(j)$, $i$'inci dizinin $j$'inci biti.

```
s_0:  [0]  1   0   1   1  ...
s_1:   1  [1]  0   0   1  ...
s_2:   0   0  [1]  1   0  ...
s_3:   1   0   1  [0]  0  ...
s_4:   0   1   1   1  [1] ...
...
```

Köşegeni oku ve her biti **ters çevir**: $d(j) = 1 - s_j(j)$. Örnekte köşegen $0, 1, 1, 0, 1, \dots$, ters çevrilmiş hali $d = 1, 0, 0, 1, 0, \dots$

$d$ de bir sonsuz bit dizisi, dolayısıyla listede bir yerde olmalı: $d = s_k$. Ama $d$ ile $s_k$, $k$'ıncı bitte farklı: $d(k) = 1 - s_k(k) \ne s_k(k)$. Çelişki. Liste eksiksiz olamaz. $\blacksquare$

Hangi listeyi yaparsan yap, köşegen sana listede olmayan bir dizi veriyor. Sonsuz bit dizileri $\mathbb{N}$'den **kesinlikle büyük** bir sonsuzluk. Aynı kanıt, ikili açılımlar üzerinden, gerçel sayıların ($\mathbb{R}$) sayılamaz olduğunu gösteriyor.

### Hesaplanamayan fonksiyonlar

Şimdi iki sonucu yan yana koy:

- Bütün C programları **sayılabilir** (Bölüm 4).
- $\mathbb{N} \to \{0, 1\}$ fonksiyonları **sayılamaz** (Bölüm 5).

Her program en fazla bir fonksiyon hesaplıyor. Programlar fonksiyonlardan az; demek ki **hiçbir programın hesaplayamadığı** $\mathbb{N} \to \{0, 1\}$ fonksiyonları var. Hem de "çoğu" fonksiyon böyle: hesaplanabilenler sayılabilir bir azınlık.

Bu bir varlık kanıtı (Ders 6.3): hesaplanamayan bir fonksiyon **gösterilmedi**, sadece var olduğu kanıtlandı. Ders 14.11'de aynı köşegen fikrini programların kendisine uygulayıp somut bir örnek bulacağız: **durma problemi**, "bu program bu girdide durur mu?" sorusunu her program için doğru cevaplayan bir program yazılamaz. Ve Rice teoremi bunu genelleştirerek, derleyicinin statik analizinin neden her zaman **yaklaşık** olmak zorunda olduğunu gösterecek: Ders 6.8'deki "erişilebilir bloklar" analizi, gerçekte asla çalışmayacak bir bloğu bazen "erişilebilir" sayıyor, ve bunu kusursuz yapan bir analiz var olamaz.

---

## Alıştırmalar

**1** – $\mathbb{Z} \to \mathbb{Z}$ şu fonksiyonlar birebir mi, örten mi? (a) $f(x) = 2x + 1$ (b) $f(x) = x^2$ (c) $f(x) = -x$ (d) $f(x) = \lfloor x / 2 \rfloor$

**2** – Bölüm 2'deki programla $k = 0, \dots, 255$ için `x * k mod 256`'nın kaç tanesinin birebir örten olduğunu say. Sonra aynı soruyu $x \mapsto x \oplus k$ (XOR) için sor. Sonuçları açıkla.

**3** – `uint32_t` üzerinde $f(x) = x \cdot 5$'in tersini bul: $5 \cdot g \equiv 1 \pmod{2^{32}}$. (İpucu: Ders 5.14'teki `0xCCCCCCCD`'yi dene.) `unsigned` çarpmanın taşma davranışı (Ders 3.8) bu hesabı neden mümkün kılıyor?

**4** – Zigzag kodlamayı yaz: `uint32_t zigzag(int32_t n)` ve tersini `int32_t unzigzag(uint32_t z)`. $0, -1, 1, -2, 2$ sırasıyla $0, 1, 2, 3, 4$'e gitmeli. (İpucu: $(n \ll 1) \oplus (n \gg 31)$; aritmetik sağa kaydırmayı hatırla, Ders 5.1.)

**5** – Köşegen kanıtını şu iddiaya uygula: "$A$ herhangi bir küme ise, $A$'dan $\mathcal{P}(A)$'ya örten bir fonksiyon yoktur." (İpucu: $f : A \to \mathcal{P}(A)$ verilsin; $D = \{a \in A \mid a \notin f(a)\}$ kümesine bak.) Bu, Ders 6.5'teki $|\mathcal{P}(A)| = 2^n > n$ sonucunu sonsuz kümelere nasıl genelleştiriyor?

<details>
<summary>Cevaplar</summary>

**1** – (a) Birebir ($2x_1 + 1 = 2x_2 + 1 \to x_1 = x_2$), örten değil (çift sayılara ulaşılmıyor). (b) Birebir değil ($f(2) = f(-2)$), örten değil (negatiflere ve 2'ye ulaşılmıyor). (c) Birebir örten, kendi kendinin tersi: $f \circ f = \text{id}$. (d) Birebir değil ($f(0) = f(1) = 0$), örten ($f(2y) = y$). Sonsuz kümelerde Bölüm 2'deki "birebir $\iff$ örten" teoremi **geçerli değil**: (a) birebir ama örten değil, (d) örten ama birebir değil. O teorem sonluluğu kullanıyordu.

**2** –

```c
int count = 0;
for (unsigned k = 0; k < 256; k++) {
    build_mul(f, k);
    if (injective(f)) count++;
}
// count = 128
```

128 tane: tam olarak tek $k$'lar. Çift $k$ bir biti kaybettiriyor. XOR için 256'nın hepsi birebir örten: $x \oplus k$'nın tersi yine $x \oplus k$ (Ders 5.1'deki tersinirlik, $(x \oplus k) \oplus k = x$). XOR hiçbir zaman bilgi kaybetmiyor; bu yüzden şifreleme ve hata düzeltmede bu kadar çok kullanılıyor.

**3** – `5u * 0xCCCCCCCDu` $= 0x400000001$, mod $2^{32}$'de `0x00000001`. Yani $g = $ `0xCCCCCCCD`. `unsigned` çarpma, taşan bitleri atarak tam olarak mod $2^{32}$ hesaplıyor; matematikteki $\mathbb{Z}/2^{32}\mathbb{Z}$ halkasının çarpması (Ders 6.23). İşaretli `int` olsaydı taşma undefined behavior olurdu ve bu eşitliğe güvenemezdin. Kontrol: `(x * 5u) * 0xCCCCCCCDu == x` her `uint32_t x` için doğru.

**4** –

```c
uint32_t zigzag(int32_t n) {
    return ((uint32_t)n << 1) ^ (uint32_t)(n >> 31);
}

int32_t unzigzag(uint32_t z) {
    return (int32_t)((z >> 1) ^ (0u - (z & 1)));
}
```

`n >> 31` aritmetik kaydırmayla negatif sayılarda bütün bitleri 1 (`-1`), pozitiflerde 0 yapıyor (Ders 5.1; uygulamaya bağlı ama yaygın). Negatif $n$ için sonuç $\sim(2n) = -2n - 1$: $-1 \to 1$, $-2 \to 3$. Pozitif için $2n$. Tersinde `0u - (z & 1)` en alt bit 1 ise bütün bitleri 1, değilse 0 yapan maske (Ders 5.5'teki dalsız seçim). `n << 1`'i `uint32_t` üzerinde yaptık, çünkü işaretli sola kaydırma negatif sayıda undefined behavior.

**5** – $f : A \to \mathcal{P}(A)$ örten olsun. $D = \{a \in A \mid a \notin f(a)\}$, $A$'nın bir alt kümesi, yani $D \in \mathcal{P}(A)$. Örtenlikle $f(d) = D$ olan bir $d$ var. $d \in D$ mi? $d \in D \iff d \notin f(d) \iff d \notin D$. Çelişki. $\blacksquare$ Köşegenle bağlantı: $f(a)$'yı bir bit dizisi gibi düşün ("$x$, $f(a)$'da mı?"); $D$, köşegenin ($a \in f(a)$?) ters çevrilmişi. Sonuç: her küme, kuvvet kümesinden **kesinlikle** küçük. Sonlu kümelerde bu $n < 2^n$ (Ders 6.4); sonsuzda da geçerli. $\mathbb{N} < \mathcal{P}(\mathbb{N}) < \mathcal{P}(\mathcal{P}(\mathbb{N})) < \dots$, sonu olmayan bir sonsuzluklar merdiveni.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §2.3 ve §2.5: fonksiyonlar ve kümelerin kardinalitesi.
- Daniel Velleman, *How to Prove It* (3. baskı), Bölüm 5 ve 8: fonksiyonlar, eşlemeler ve sayılabilirlik.
- Georg Cantor, "Über eine elementare Frage der Mannigfaltigkeitslehre" (1891): köşegen kanıtının ilk yayımı.
- Michael Sipser, *Introduction to the Theory of Computation* (3. baskı), §4.2: köşegen yöntemi ve tanınamayan diller.

**Sıradaki ders:** Toplamlar ve notasyon. $\Sigma$'yı bir cebir aleti olarak kullanmak, ve toplamları kapalı formüle çevirmenin yöntemleri.
