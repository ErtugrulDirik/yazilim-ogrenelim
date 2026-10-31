---
title: "6.6 Bağıntılar"
description: "Bağıntıyı A × B'nin bir alt kümesi olarak tanımlamak; matris, graf ve satır başına bir bitmask ile temsil; yansıma, simetri, ters simetri ve geçişlilik özellikleri ve C'de denetlenmeleri; denklik bağıntısı, denklik sınıfları ve bölüntü (mod n örneği); geçişli kapanış ve Warshall algoritmasının bitlerle yazılışı."
---

"Eşittir", "küçüktür", "böler", "aynı kalanı verir", "bu dosya şu dosyaya bağlı", "bu fonksiyon şu fonksiyonu çağırıyor"... Hepsi iki şey arasındaki bir **ilişki**. Matematikte bu ilişkilerin ortak adı **bağıntı** (relation), ve Ders 6.5'teki kartezyen çarpım sayesinde tanımı tek satır.

Bu ders fazın ikinci yarısının temeli: Ders 6.7'deki sıralamalar, 6.8'deki kafesler, 6.9'daki fonksiyonlar ve 6.30'daki graflar hep özel bağıntılar.

---

## 1. Tanım

$A$'dan $B$'ye bir **bağıntı**, $A \times B$'nin herhangi bir alt kümesidir:

$$
R \subseteq A \times B
$$

$(a, b) \in R$ ise "$a$, $b$ ile $R$ bağıntısında" deriz ve $a \mathrel{R} b$ yazarız. $A = B$ ise "$A$ üzerinde bir bağıntı" deriz.

Örnek: $A = \{0, 1, 2, 3\}$ üzerinde "küçüktür" bağıntısı

$$
{<} = \{(0,1), (0,2), (0,3), (1,2), (1,3), (2,3)\}.
$$

Bu tanımın gücü şu: bir bağıntı **sadece** hangi ikililerin ilişkili olduğundan ibaret. "Küçüktür"ün anlamı, nasıl hesaplandığı, bir formülü olup olmadığı önemsiz. İstediğin herhangi bir ikili kümesi bir bağıntı; $\emptyset$ bile (hiçbir şey hiçbir şeyle ilişkili değil).

Ders 6.2'deki iki değişkenli yüklemler, $Q(x, y)$, bağıntılarla aynı şey: $R = \{(x, y) \mid Q(x, y)\}$. C'de iki parametreli `bool` döndüren bir fonksiyon.

---

## 2. Üç temsil

Sonlu bir küme üzerindeki bağıntıyı üç şekilde görebiliriz. $A = \{0, 1, 2\}$ üzerinde $R = \{(0, 0), (0, 1), (1, 2), (2, 2)\}$:

**Matris**: $M_{ab} = 1 \iff a \mathrel{R} b$.

| | 0 | 1 | 2 |
| --- | --- | --- | --- |
| **0** | 1 | 1 | 0 |
| **1** | 0 | 0 | 1 |
| **2** | 0 | 0 | 1 |

**Yönlü graf**: her eleman bir düğüm, her $(a, b)$ ikilisi $a$'dan $b$'ye bir ok. $(0, 0)$ gibi bir eleman kendine dönen bir halka.

```
  ↻                     ↻
  0 ───────▶ 1 ───────▶ 2
```

**Satır başına bir küme**: matrisin her satırı, Ders 6.5'teki gibi bir bitmask. $R[a]$, $a$'nın ilişkili olduğu elemanların kümesi.

```c
#include <stdint.h>
#include <stdbool.h>

#define N 6   // kume: {0, 1, ..., 5}

// R[a] bir kume: a ile iliskili olan b'ler. b, R[a]'da ise a R b.
typedef uint32_t rel[N];

static bool related(const rel R, int a, int b) { return (R[a] >> b) & 1; }
```

Üçüncü temsil iki öncekinin birleşimi: matrisin kompaktlığı, bir de satırları kümeler olarak işleyebilme. Bu dersin kodunda bunu kullanacağız. Bir yüklemden bağıntı kurmak için:

```c
static void build(rel R, bool (*p)(int, int)) {
    for (int a = 0; a < N; a++) {
        R[a] = 0;
        for (int b = 0; b < N; b++)
            if (p(a, b)) R[a] |= (uint32_t)1 << b;
    }
}
```

---

## 3. Dört özellik

$A$ üzerindeki bir $R$ bağıntısı:

| Özellik | Tanım | Matriste | Grafta |
| --- | --- | --- | --- |
| **Yansıyan** (reflexive) | $\forall a\, (a \mathrel{R} a)$ | köşegen hep 1 | her düğümde halka |
| **Simetrik** | $\forall a, b\, (a \mathrel{R} b \to b \mathrel{R} a)$ | $M = M^T$ | her okun tersi de var |
| **Ters simetrik** (antisymmetric) | $\forall a, b\, (a \mathrel{R} b \land b \mathrel{R} a \to a = b)$ | köşegen dışında $M_{ab}$, $M_{ba}$ ikisi birden 1 değil | iki düğüm arasında karşılıklı ok yok |
| **Geçişli** (transitive) | $\forall a, b, c\, (a \mathrel{R} b \land b \mathrel{R} c \to a \mathrel{R} c)$ | — | iki adımda gidebiliyorsan bir adımda da |

Ters simetrik "simetrik değil" demek **değil**. $=$ bağıntısı hem simetrik hem ters simetrik; "simetrik olmayan" bir bağıntı ters simetrik olmak zorunda değil. Bunlar bağımsız özellikler.

Her tanım bir $\forall$; Ders 6.2'nin dersini uygulayıp her birini iç içe döngülere çeviriyoruz:

```c
static bool reflexive(const rel R) {
    for (int a = 0; a < N; a++)
        if (!related(R, a, a)) return false;
    return true;
}

static bool symmetric(const rel R) {
    for (int a = 0; a < N; a++)
        for (int b = 0; b < N; b++)
            if (related(R, a, b) && !related(R, b, a)) return false;
    return true;
}

static bool antisymmetric(const rel R) {
    for (int a = 0; a < N; a++)
        for (int b = 0; b < N; b++)
            if (a != b && related(R, a, b) && related(R, b, a)) return false;
    return true;
}

static bool transitive(const rel R) {
    for (int a = 0; a < N; a++)
        for (int b = 0; b < N; b++)
            if (related(R, a, b) && (R[b] & ~R[a]) != 0) return false;   // R[b], R[a]'nin alt kumesi olmali
    return true;
}
```

`transitive` üç değişkenli $\forall$'ı iki döngüye indirdi. "$a \mathrel{R} b$ ise, $b$'nin ilişkili olduğu her $c$ ile $a$ da ilişkili" demek, "$R[b] \subseteq R[a]$" demek; Ders 6.5'teki alt küme testi tek bir `&`.

Dört bağıntıyı deneyelim, $\{0, \dots, 5\}$ üzerinde:

```c
static bool same_mod3(int a, int b) { return a % 3 == b % 3; }
static bool less_eq(int a, int b)   { return a <= b; }
static bool less(int a, int b)      { return a < b; }
static bool successor(int a, int b) { return b == a + 1; }
```

```
mod 3    yans=1 sim=1 tersim=0 gec=1
<=       yans=1 sim=0 tersim=1 gec=1
<        yans=0 sim=0 tersim=1 gec=1
b=a+1    yans=0 sim=0 tersim=1 gec=0
```

İlk iki satırdaki desenler özel isimler alıyor. **Yansıyan + simetrik + geçişli**: denklik bağıntısı (bu dersin geri kalanı). **Yansıyan + ters simetrik + geçişli**: kısmi sıralama (Ders 6.7).

---

## 4. Denklik bağıntısı

Yansıyan, simetrik ve geçişli bir bağıntıya **denklik bağıntısı** (equivalence relation) denir. Sezgisi: "bir açıdan aynı". Eşitliğin gevşetilmiş hali, eşitliğin üç temel özelliğini koruyor.

- $a \equiv b \pmod{n}$: "$n$'e bölünce aynı kalanı verir"
- "Aynı uzunlukta stringler"
- "Aynı değeri hesaplayan iki ifade" (derleyicinin ortak alt ifade elemesi bunu arıyor)
- Ders 6.1'deki mantıksal denklik $\equiv$: aynı doğruluk tablosuna sahip formüller

**Teorem.** $n \ge 1$ için "mod $n$ denk" bir denklik bağıntısıdır. ($a \equiv b \pmod n \iff n \mid a - b$.)

**Kanıt.** *Yansıyan*: $a - a = 0 = n \cdot 0$. ✓ *Simetrik*: $a - b = nk$ ise $b - a = n(-k)$. ✓ *Geçişli*: $a - b = nk$ ve $b - c = nj$ ise $a - c = (a - b) + (b - c) = n(k + j)$. ✓ $\blacksquare$

### Denklik sınıfları

Bir denklik bağıntısı kümeyi **parçalara** ayırıyor. $a$'nın **denklik sınıfı**, $a$ ile denk olan her şey:

$$
[a] = \{x \in A \mid x \mathrel{R} a\}
$$

Mod 3 için $\{0, \dots, 5\}$ üzerinde: $[0] = \{0, 3\}$, $[1] = \{1, 4\}$, $[2] = \{2, 5\}$. Ve $[3] = [0]$: aynı sınıfın farklı **temsilcileri**.

Satır-küme temsilinde denklik sınıfı hazır duruyor: `R[a]` ta kendisi (simetri sayesinde $x \mathrel{R} a \iff a \mathrel{R} x$). Sınıfları tekrarsız yazmak için görülen elemanları bir kümede biriktiriyoruz:

```c
uint32_t seen = 0;
for (int a = 0; a < N; a++) {
    if ((seen >> a) & 1) continue;   // a zaten bir sinifta
    print_set(R[a]);
    seen |= R[a];
}
```

```
mod 3 denklik siniflari: {0, 3} {1, 4} {2, 5}
```

Sınıflar üç özelliğe sahip: hiçbiri boş değil, ikisi ya **tamamen aynı** ya **hiç kesişmiyor**, ve birleşimleri bütün küme. Bu üç özelliğe sahip bir parça ailesine **bölüntü** (partition) denir.

**Teorem.** Bir denklik bağıntısının sınıfları bir bölüntü oluşturur; ve tersine, her bölüntü "aynı parçada olmak" diye bir denklik bağıntısı tanımlar.

**Kanıt** (ilk yönün kritik kısmı). $[a] \cap [b] \ne \emptyset$ ise $[a] = [b]$ olduğunu gösterelim. Ortak bir $c$ olsun: $c \mathrel{R} a$ ve $c \mathrel{R} b$. Simetriyle $a \mathrel{R} c$, geçişlilikle $a \mathrel{R} b$. Şimdi $x \in [a]$ ise $x \mathrel{R} a$ ve $a \mathrel{R} b$, geçişlilikle $x \mathrel{R} b$, yani $x \in [b]$. Demek $[a] \subseteq [b]$; simetrik akıl yürütmeyle $[b] \subseteq [a]$. (Ders 6.5'teki "iki yönlü alt küme" kalıbı.) $\blacksquare$

Denklik sınıfları ileride çok çıkacak. Ders 6.18'de $\mathbb{Z}/n\mathbb{Z}$, mod $n$ sınıflarının kümesi olacak ve bilgisayarın `uint32_t` aritmetiği $\mathbb{Z}/2^{32}\mathbb{Z}$. Ders 14.5'teki DFA küçültme, "aynı davranan durumlar" denkliğinin sınıflarını buluyor. Faz 8'deki union-find, sınıfları birleştirip "bu iki eleman aynı sınıfta mı?" sorusunu neredeyse sabit zamanda cevaplayan veri yapısı.

---

## 5. Geçişli kapanış

$b = a + 1$ bağıntısı geçişli değil: $0 \to 1$ ve $1 \to 2$ var ama $0 \to 2$ yok. Onu geçişli yapmak için gereken **en az** ikiliyi eklersek ne elde ederiz? Bu, bağıntının **geçişli kapanışı**: $a \mathrel{R^+} b \iff$ $a$'dan $b$'ye **bir ya da daha fazla** adımla gidilebiliyor.

Grafta: "$a$'dan $b$'ye bir yol var mı?" Programlarda sürekli soruluyor. "Bu fonksiyon dolaylı yoldan kendini çağırıyor mu?" (özyineleme algılama), "Bu `.c` dosyası dolaylı olarak hangi başlıklara bağlı?" (Ders 2.11'deki make'in bilmesi gereken şey).

**Warshall algoritması** bunu üç iç içe döngüyle hesaplıyor. Fikir: ara düğümleri birer birer "izinli" yap. $k$'yı izinli yaptığında, $a \to k$ ve $k \to b$ olan her çift için $a \to b$ ekle. Satır-küme temsilinde iç döngü tek bir `|`:

```c
// Warshall: R'yi gecisli kapanisina cevirir
static void transitive_closure(rel R) {
    for (int k = 0; k < N; k++)
        for (int a = 0; a < N; a++)
            if (related(R, a, k)) R[a] |= R[k];   // a -> k ve k -> b ise a -> b
}
```

```
b=a+1+   yans=0 sim=0 tersim=1 gec=1
kapanis == <: 1
```

"Bir sonraki" bağıntısının geçişli kapanışı tam olarak "küçüktür". Mantıklı: $a < b$ demek, $a$'dan $b$'ye birer birer artarak ulaşılabilir demek.

Döngülerin sırası önemli: $k$ **en dışta** olmalı. Bunun neden doğru olduğunun kanıtı $k$ üzerinde bir tümevarım (Ders 6.4): "$k$'ıncı turdan sonra, ara düğümleri sadece $\{0, \dots, k\}$'dan olan bütün yollar eklenmiş." Faz 9'da aynı yapının en kısa yolları bulan hali olan Floyd–Warshall'u göreceğiz.

---

## Alıştırmalar

**1** – $\{0, \dots, 5\}$ üzerinde şu bağıntıların dört özelliğini önce elle bul, sonra programa ekleyip doğrula: (a) $a \mid b$ ($a$, $b$'yi böler; $0 \mid b$ sadece $b = 0$ iken), (b) $a \ne b$, (c) $|a - b| \le 1$.

**2** – Simetrik ve geçişli olan her bağıntı yansıyan mıdır? Şu "kanıt"ı değerlendir: "$a \mathrel{R} b$ ise simetriyle $b \mathrel{R} a$, geçişlilikle $a \mathrel{R} a$." (İpucu: $\emptyset$'ı düşün.)

**3** – $\{0, 1, 2\}$ üzerinde kaç tane bağıntı var? Kaç tanesi yansıyan? Bütün bağıntıları bitlerle gezip denklik bağıntılarını sayan bir program yaz. Sonuç, 3 elemanlı kümenin bölüntü sayısına eşit olmalı; elle say.

**4** – Stringler üzerinde "aynı harflerin aynı sayıda geçmesi" (anagram olmak) bir denklik bağıntısı mı? Denklik sınıfının bir temsilcisini nasıl seçersin? (İpucu: kanonik temsil, Ders 6.5'in 4. alıştırması.)

**5** – Warshall'da döngüleri `for a / for k` sırasına çevirirsen hangi girdide yanlış sonuç alırsın? Küçük bir örnek bul.

<details>
<summary>Cevaplar</summary>

**1** – (a) Bölünebilirlik: yansıyan ($a \mid a$; $0 \mid 0$ da doğru), simetrik değil ($1 \mid 2$ ama $2 \nmid 1$), ters simetrik (doğal sayılarda $a \mid b$ ve $b \mid a$ ise $a = b$), geçişli ($b = ak$, $c = bj$ ise $c = a(kj)$). Kısmi sıralama, Ders 6.7'de baş örneğimiz olacak. (b) $\ne$: yansıyan değil, simetrik, ters simetrik değil, geçişli değil ($0 \ne 1$, $1 \ne 0$ ama $0 = 0$). (c) $|a - b| \le 1$: yansıyan, simetrik, ters simetrik değil, geçişli değil ($0, 1$ ve $1, 2$ var, $0, 2$ yok). "Yakın olmak" sezgisel olarak bir denklik gibi görünse de geçişli değil; küçük farklar birikiyor. Faz 3'teki `fabs(a - b) < eps` ile float karşılaştırmanın asıl sorunu da bu.

**2** – Hayır. Kanıt, "her $a$ için bir $b$ var ki $a \mathrel{R} b$" varsayımını gizlice yapıyor. $R = \emptyset$ boş yere simetrik ve geçişli ama yansıyan değil (boş olmayan bir kümede). Daha az uç bir örnek: $\{0, 1\}$ üzerinde $R = \{(0, 0)\}$; simetrik, geçişli, ama $(1, 1)$ yok. Kanıt sadece "en az bir şeyle ilişkili olan" elemanlar için çalışıyor. Ders 6.2'deki dersin tekrarı: $\forall a$ ile $\exists b$'nin sırasını ve varlığını dikkatle yaz.

**3** – $|A \times A| = 9$, her ikili var ya da yok: $2^9 = 512$ bağıntı. Yansıyan olanlarda köşegendeki 3 ikili zorunlu, kalan 6 serbest: $2^6 = 64$.

```c
// 3x3 matrisin 9 biti: bit (3*a + b) -> a R b
int count = 0;
for (unsigned m = 0; m < 512; m++) {
    rel R = {0};
    for (int a = 0; a < 3; a++)
        R[a] = (m >> (3 * a)) & 7;        // satir a
    // N yerine 3 kullanan reflexive/symmetric/transitive ile
    if (reflexive3(R) && symmetric3(R) && transitive3(R)) count++;
}
// count = 5
```

3 elemanlı kümenin bölüntüleri: $\{\{0,1,2\}\}$; $\{\{0\},\{1,2\}\}$, $\{\{1\},\{0,2\}\}$, $\{\{2\},\{0,1\}\}$; $\{\{0\},\{1\},\{2\}\}$. Beş tane, programla aynı. (Bu sayılar Bell sayıları: 1, 1, 2, 5, 15, 52, ...)

**4** – Evet: bir string kendisinin anagramı (yansıyan); $s$, $t$'nin anagramıysa tersi de (simetrik); harf sayıları eşitlik olduğu için geçişli. Temsilci olarak harfleri **sıralanmış** string seçilebilir: "elma", "emla", "male" hepsinin temsilcisi "aelm". İki string anagramsa temsilcileri aynı; temsilcileri karşılaştırmak denkliği kontrol etmek. Bu, bir denklik sınıfını kanonik bir elemanla göstermenin genel fikri.

**5** – $N = 4$, $R = \{(0, 2), (2, 1), (1, 3)\}$: $0 \to 2 \to 1 \to 3$ zinciri, ama düğümler numara sırasında değil. `for a / for k` sırasında $a = 0$ işlenirken $k = 1$'de $R[0]$'da 1 henüz yok, atlanıyor; $k = 2$'de $R[2] = \{1\}$ ekleniyor ve $R[0] = \{1, 2\}$ oluyor. Ama $k = 1$ çoktan geçti; $R[1] = \{3\}$ hiç eklenmiyor. Sonuç $R[0] = \{1, 2\}$ (`0x6`), doğrusu $\{1, 2, 3\}$ (`0xe`). $k$ dışta olunca $k = 1$ turunda $R[2]$'ye 3 eklenir, $k = 2$ turunda da $R[0]$'a $R[2] = \{1, 3\}$ eklenir; doğru sonuç. Ders: döngü sırası, kanıttaki tümevarımın hangi değişken üzerinde yapıldığını yansıtıyor; sırayı değiştirmek kanıtı bozuyor.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), Bölüm 9: bağıntılar, özellikleri, kapanışlar, Warshall algoritması, denklik bağıntıları.
- Daniel Velleman, *How to Prove It* (3. baskı), Bölüm 4: bağıntılar ve denklik bağıntıları.
- Stephen Warshall, "A Theorem on Boolean Matrices", *Journal of the ACM* 9(1), 1962.

**Sıradaki ders:** Kısmi sıralamalar. Yansıyan, ters simetrik, geçişli: "önce gelir" ilişkisinin matematiği, ve bağımlılıkları doğru sırayla işleyen topolojik sıralama.
