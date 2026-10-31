---
title: "6.5 Kümeler"
description: "Küme, eleman, alt küme ve eşitlik; birleşim, kesişim, fark, tümleyen ve simetrik fark; küme cebirinin önermeler mantığıyla aynı yasaları; kartezyen çarpım; kuvvet kümesi ve |P(A)| = 2ⁿ; kümeleri uint32_t'nin bitleriyle temsil edip her işlemi tek bir bit operatörüne indirmek, bütün alt kümeleri sayarak ve (sub − 1) & A ile gezmek."
---

Ders 6.2'de "evren" dedik ve bir değişkenin alabileceği değerleri kastettik. Ders 6.4'te "her $n \ge 0$" dedik ve doğal sayıların hepsini kastettik. İkisinde de bir **topluluk** hakkında konuştuk ama topluluğun kendisini bir nesne olarak ele almadık. Matematikte bu nesnenin adı **küme** ve modern matematiğin neredeyse her şeyi (sayılar, fonksiyonlar, bağıntılar, graflar) kümelerle tanımlanıyor.

Bu derste kümelerin dilini kuracağız ve Faz 5'te zaten yaptığımız bir şeyi tanıyacağız: Ders 5.2'deki bayrak kümeleri gerçekten **küme**ydi.

---

## 1. Küme ve eleman

**Küme**, nesnelerin sırasız ve tekrarsız bir topluluğu. Nesnelere **eleman** denir.

- $x \in A$: "$x$, $A$'nın elemanıdır"
- $x \notin A$: "$x$, $A$'nın elemanı değildir"

Küme iki yolla yazılır:

- **Listeleyerek**: $A = \{1, 2, 3, 5\}$
- **Özellikle** (set-builder): $E = \{n \in \mathbb{Z} \mid n \text{ çift}\}$, "çift olan tamsayılar"

İkinci yazım Ders 6.2'nin yüklemleri: $\{x \in U \mid P(x)\}$, evrende $P$'yi sağlayan elemanların kümesi.

İki önemli kural:

- **Sıra önemsiz**: $\{1, 2, 3\} = \{3, 1, 2\}$
- **Tekrar önemsiz**: $\{1, 1, 2\} = \{1, 2\}$

Bir dizi (array) ise ikisini de önemsiyor: `{1, 2, 3}` ile `{3, 1, 2}` farklı diziler. Küme ile dizi arasındaki fark bu iki kural.

Sık kullanılan kümeler: $\mathbb{N} = \{0, 1, 2, \dots\}$ (doğal sayılar), $\mathbb{Z}$ (tamsayılar), $\mathbb{Q}$ (rasyonel sayılar), $\mathbb{R}$ (gerçel sayılar), ve $\emptyset = \{\}$ (**boş küme**, hiç elemanı yok).

Bir kümenin eleman sayısına **kardinalite** (cardinality) denir: $|\{1, 2, 3, 5\}| = 4$, $|\emptyset| = 0$.

---

## 2. Alt küme ve eşitlik

$A$'nın her elemanı $B$'de de varsa, $A$, $B$'nin **alt kümesi**dir:

$$
A \subseteq B \iff \forall x\, (x \in A \to x \in B)
$$

İki küme ancak ve ancak aynı elemanlara sahipse **eşittir**:

$$
A = B \iff A \subseteq B \land B \subseteq A
$$

Bu ikinci satır bir **kanıt kalıbı**: iki kümenin eşit olduğunu göstermek için iki yönü ayrı ayrı kanıtlarsın. "Sol taraftaki her eleman sağda; sağdaki her eleman solda."

Ders 6.2'den bir sonuç: **boş küme her kümenin alt kümesidir.** $\emptyset \subseteq A$ demek $\forall x\, (x \in \emptyset \to x \in A)$, ve $x \in \emptyset$ her zaman yanlış olduğu için koşul boş yere doğru.

$A \subseteq B$ ve $A \ne B$ ise $A$, $B$'nin **öz alt kümesi**dir: $A \subset B$.

---

## 3. İşlemler

$U$ evren olsun, $A, B \subseteq U$.

| İşlem | Simge | Tanım | Mantıktaki karşılığı |
| --- | --- | --- | --- |
| Birleşim | $A \cup B$ | $\{x \mid x \in A \lor x \in B\}$ | $\lor$ |
| Kesişim | $A \cap B$ | $\{x \mid x \in A \land x \in B\}$ | $\land$ |
| Fark | $A \setminus B$ | $\{x \mid x \in A \land x \notin B\}$ | $p \land \neg q$ |
| Tümleyen | $\overline{A}$ | $\{x \in U \mid x \notin A\}$ | $\neg$ |
| Simetrik fark | $A \mathbin{\triangle} B$ | $(A \setminus B) \cup (B \setminus A)$ | XOR |

Son sütuna bak: her küme işlemi bir mantık bağlacı. Bu tesadüf değil, **tanım** öyle: "$x \in A \cup B$" ifadesi, "$x \in A$" ve "$x \in B$" önermelerinin $\lor$'u. Dolayısıyla Ders 6.1'deki bütün denklik yasaları kümelerde de geçerli:

| Yasa | Mantıkta | Kümelerde |
| --- | --- | --- |
| De Morgan | $\neg(p \land q) \equiv \neg p \lor \neg q$ | $\overline{A \cap B} = \overline{A} \cup \overline{B}$ |
| Dağılma | $p \land (q \lor r) \equiv (p \land q) \lor (p \land r)$ | $A \cap (B \cup C) = (A \cap B) \cup (A \cap C)$ |
| Yutma | $p \lor (p \land q) \equiv p$ | $A \cup (A \cap B) = A$ |
| Çift tümleyen | $\neg\neg p \equiv p$ | $\overline{\overline{A}} = A$ |

**Teorem.** $\overline{A \cap B} = \overline{A} \cup \overline{B}$.

**Kanıt.** Her $x \in U$ için:

$$
x \in \overline{A \cap B} \iff \neg(x \in A \land x \in B) \iff x \notin A \lor x \notin B \iff x \in \overline{A} \cup \overline{B}.
$$

Ortadaki adım önermelerin De Morgan'ı. İki yön birden gösterildi ($\iff$), kümeler eşit. $\blacksquare$

Bir yapı ($\cup$, $\cap$, tümleyen, $\emptyset$, $U$) ile başka bir yapının ($\lor$, $\land$, $\neg$, 0, 1) aynı yasalara uyması matematikte önemli bir fikir; ikisi de bir **Boole cebiri**. Ders 6.8'de bu yapıyı kafes olarak yeniden göreceğiz.

### Kartezyen çarpım

Kümeler sırasız; ama bazen sıra lazım. **Sıralı ikili** $(a, b)$'de $(1, 2) \ne (2, 1)$. İki kümenin **kartezyen çarpımı**, bütün sıralı ikililerin kümesi:

$$
A \times B = \{(a, b) \mid a \in A \land b \in B\}
$$

$\{1, 2\} \times \{x, y, z\} = \{(1, x), (1, y), (1, z), (2, x), (2, y), (2, z)\}$, ve $|A \times B| = |A| \cdot |B|$. Ders 4.3'teki iki boyutlu dizi `int m[2][3]`'ün indeksleri tam olarak $\{0, 1\} \times \{0, 1, 2\}$. Bir sonraki ders bağıntıları $A \times B$'nin alt kümeleri olarak tanımlayacak.

---

## 4. Kuvvet kümesi

Bir kümenin **bütün** alt kümelerinin kümesine **kuvvet kümesi** denir:

$$
\mathcal{P}(\{0, 1, 2\}) = \{\emptyset, \{0\}, \{1\}, \{0, 1\}, \{2\}, \{0, 2\}, \{1, 2\}, \{0, 1, 2\}\}
$$

Sekiz eleman. Genel olarak:

**Teorem.** $|A| = n$ ise $|\mathcal{P}(A)| = 2^n$.

**Kanıt** (tümevarımla, Ders 6.4). *Taban*: $n = 0$, $A = \emptyset$, tek alt kümesi $\emptyset$; $2^0 = 1$. ✓ *Adım*: $n = k$ için doğru olsun; $|A| = k + 1$ ve $a \in A$ bir eleman olsun. $A$'nın alt kümeleri iki gruba ayrılıyor: $a$'yı **içermeyenler** ($A \setminus \{a\}$'nın alt kümeleri, hipoteze göre $2^k$ tane) ve $a$'yı **içerenler** (her biri, içermeyen bir kümeye $a$ eklenerek elde ediliyor, yine $2^k$ tane). Toplam $2^k + 2^k = 2^{k+1}$. ✓ $\blacksquare$

Kanıtın sezgisi daha basit: her eleman için iki seçenek var, "kümede" ya da "kümede değil". $n$ eleman, $2^n$ seçim. Bu da bir sonraki bölümün temeli.

---

## 5. Kümeyi bitlerle temsil etmek

Evren küçük ve sabitse, diyelim $U = \{0, 1, \dots, 31\}$, bir alt küme **32 bitlik bir sayıyla** temsil edilebilir: **$i$'inci bit 1 ise $i$ kümede.** Bu, Ders 5.2'deki bayrak kümesinin ta kendisi.

$$
A = \{1, 2, 3, 5\} \quad\longleftrightarrow\quad \texttt{0b101110} = \texttt{0x2E}
$$

Ve 3. bölümdeki tablonun son sütunu kodun kendisi oluyor:

```c
#include <stdint.h>
#include <stdbool.h>

typedef uint32_t set32;   // evren {0, 1, ..., 31}; bit i 1 ise i kumede

static set32 set_of(int x)             { return (set32)1 << x; }
static bool  set_has(set32 a, int x)   { return (a >> x) & 1; }
static set32 set_union(set32 a, set32 b)  { return a | b; }
static set32 set_inter(set32 a, set32 b)  { return a & b; }
static set32 set_diff(set32 a, set32 b)   { return a & ~b; }
static set32 set_symdiff(set32 a, set32 b){ return a ^ b; }
static bool  set_subset(set32 a, set32 b) { return (a & ~b) == 0; }   // a, b'nin alt kumesi mi
static int   set_size(set32 a)            { return __builtin_popcount(a); }
```

Her işlem **tek bir komut**: 32 elemanın hepsi için $\land$, $\lor$, $\neg$ aynı anda hesaplanıyor. Kardinalite Ders 5.8'deki `popcount`. Alt küme testi ilginç: $A \subseteq B \iff A \setminus B = \emptyset$, yani "$A$'da olup $B$'de olmayan eleman yok". Ders 6.2'deki $\forall$ döngüsü 32 elemanı tek tek gezerdi; bitlerle tek bir `&` ve karşılaştırma.

Yazdırmak için bitleri geziyoruz:

```c
static void set_print(set32 a) {
    printf("{");
    bool first = true;
    for (int x = 0; x < 32; x++) {
        if (set_has(a, x)) {
            printf(first ? "%d" : ", %d", x);
            first = false;
        }
    }
    printf("}\n");
}
```

```c
set32 A = set_of(1) | set_of(2) | set_of(3) | set_of(5);
set32 B = set_of(2) | set_of(3) | set_of(7);
```

```
A       = {1, 2, 3, 5}
B       = {2, 3, 7}
A u B   = {1, 2, 3, 5, 7}
A n B   = {2, 3}
A - B   = {1, 5}
A ^ B   = {1, 5, 7}
|A| = 4, A n B alt kume A: 1, A alt kume B: 0
```

Tümleyen için dikkat: `~a` evren $\{0, \dots, 31\}$ ise doğru. Evren daha küçükse, diyelim $\{0, \dots, n-1\}$, fazla bitleri temizlemek gerekiyor: `~a & ((1u << n) - 1)`. Yoksa tümleyen evrende olmayan elemanları da içerir.

### Bütün alt kümeleri gezmek

Kuvvet kümesi kanıtının sezgisi koda dönüşüyor: $\{0, \dots, n-1\}$'in alt kümeleri, $0$'dan $2^n - 1$'e kadar **sayılar**. Her sayının bitleri bir seçim.

```c
int n = 3;
for (set32 s = 0; s < (1u << n); s++) set_print(s);
```

```
{}
{0}
{1}
{0, 1}
{2}
{0, 2}
{1, 2}
{0, 1, 2}
```

Ders 6.1'deki doğruluk tablosu programı da tam olarak bunu yapıyordu: her satır, "doğru olan değişkenlerin kümesi".

Bazen evrenin değil, **belirli bir kümenin** alt kümelerini gezmek istersin. $A = \{1, 2, 3, 5\}$'in 16 alt kümesi $0$ ile $2^{32}$ arasındaki sayılar içinde dağınık; hepsini sayıp filtrelemek israf. Faz 5'ten bir hile:

```c
set32 sub = A;
while (1) {
    // sub'i isle
    if (sub == 0) break;
    sub = (sub - 1) & A;
}
```

```
{1, 2, 3, 5}
{2, 3, 5}
{1, 3, 5}
{3, 5}
...      (toplam 16 tane, sonuncusu {})
```

`sub - 1`, Ders 5.3'te gördüğümüz gibi en sağdaki 1'i 0 yapıp altındaki bitleri 1'e çeviriyor; `& A` ise $A$'da olmayan bitleri atıyor. Sonuç: $A$'nın alt kümelerini **büyükten küçüğe** tam $2^{|A|}$ adımda geziyor. Bu döngü dinamik programlamada (Faz 9) "alt maske gezme" adıyla sık geçer.

Bitlerle temsilin sınırı açık: evren 32 (ya da `uint64_t` ile 64) elemanı geçemez. Daha büyük evrenler için kelime dizisi kullanılır; Ders 5.20'deki bitset tam olarak buydu. Evren hiç sabit değilse (örneğin rastgele tamsayılar), kümeler Faz 8'deki hash tablosu ya da arama ağacıyla temsil edilir.

---

## Alıştırmalar

**1** – $U = \{0, \dots, 9\}$, $A = \{0, 2, 4, 6, 8\}$, $B = \{0, 3, 6, 9\}$. $A \cup B$, $A \cap B$, $A \setminus B$, $\overline{A}$, $A \mathbin{\triangle} B$'yi elle yaz; sonra her birini bit deseni (onaltılık) olarak hesapla.

**2** – Kanıtla: $A \setminus B = A \cap \overline{B}$. Bu eşitlik `set_diff`'in neden `a & ~b` olduğunu açıklıyor.

**3** – $A \mathbin{\triangle} B = (A \cup B) \setminus (A \cap B)$ olduğunu kanıtla, ve bunun bitlerde `a ^ b == (a | b) & ~(a & b)` olduğunu göster.

**4** – `bool set_equal(set32 a, set32 b)`'yi sadece `set_subset` kullanarak yaz. Bit düzeyinde daha kısa yolu ne?

**5** – $\{0, \dots, n-1\}$'in **tam $k$ elemanlı** alt kümelerini yazdıran bir fonksiyon yaz (bütün alt kümeleri gezip `popcount` ile filtreleyebilirsin). $n = 5$, $k = 2$ için kaç tane çıkıyor? Bu sayıyı Ders 6.14'te formülle hesaplayacağız.

<details>
<summary>Cevaplar</summary>

**1** – $A = \{0, 2, 4, 6, 8\}$ = `0x155`, $B = \{0, 3, 6, 9\}$ = `0x249`.

- $A \cup B = \{0, 2, 3, 4, 6, 8, 9\}$ = `0x155 | 0x249` = `0x35D`
- $A \cap B = \{0, 6\}$ = `0x041`
- $A \setminus B = \{2, 4, 8\}$ = `0x114`
- $\overline{A} = \{1, 3, 5, 7, 9\}$ = `~0x155 & 0x3FF` = `0x2AA` (evren 10 bit, maske `(1u << 10) - 1` = `0x3FF`)
- $A \mathbin{\triangle} B = \{2, 3, 4, 8, 9\}$ = `0x31C`

**2** – Her $x$ için: $x \in A \setminus B \iff x \in A \land x \notin B \iff x \in A \land x \in \overline{B} \iff x \in A \cap \overline{B}$. $\blacksquare$ Bitlerde $\overline{B}$ = `~b`, $\cap$ = `&`. Evrenin dışındaki bitler `a`'da zaten 0 olduğu için burada `~b`'yi maskelemeye gerek yok.

**3** – $x \in A \mathbin{\triangle} B$ demek, $x$ tam olarak birinde: ($x \in A \land x \notin B$) $\lor$ ($x \in B \land x \notin A$). $x \in (A \cup B) \setminus (A \cap B)$ demek, en az birinde ama ikisinde birden değil. Durumlara ayıralım: $x$ ikisinde de varsa ikisi de yanlış; hiçbirinde yoksa ikisi de yanlış; tam birinde varsa ikisi de doğru. Dört durumda aynı, kümeler eşit. $\blacksquare$ Bitlerde aynı dört durum, aynı doğruluk tablosu: XOR, "en az biri ama ikisi değil".

**4** –

```c
bool set_equal(set32 a, set32 b) {
    return set_subset(a, b) && set_subset(b, a);
}
```

Bit temsilinde eşitlik doğrudan `a == b`, çünkü temsil **tek** (kanonik): her kümenin tek bir bit deseni var. Dizi temsilinde bu doğru değildi: `{1, 2}` ve `{2, 1}` farklı diziler ama aynı küme. Kanonik temsil karşılaştırmayı ucuzlatıyor; Faz 12'de sembolik ifadeler için aynı sorunu yaşayacağız.

**5** –

```c
void subsets_of_size(int n, int k) {
    int count = 0;
    for (set32 s = 0; s < (1u << n); s++) {
        if (set_size(s) == k) { set_print(s); count++; }
    }
    printf("%d tane\n", count);
}
```

$n = 5$, $k = 2$ için 10 tane: $\{0,1\}, \{0,2\}, \{1,2\}, \{0,3\}, \dots, \{3,4\}$. Bu sayı $\binom{5}{2} = 10$.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §2.1–2.2: kümeler ve küme işlemleri; bit dizisiyle temsil.
- Paul Halmos, *Naive Set Theory*: kümeler kuramına kısa ve klasik bir giriş.
- Henry Warren, *Hacker's Delight* (2. baskı), §2-1: en sağdaki bitlerle oynamak, alt maske gezme.

**Sıradaki ders:** Bağıntılar. $A \times B$'nin alt kümeleri, ve "eşittir", "küçüktür", "aynı kalanı verir" gibi ilişkilerin ortak yapısı.
