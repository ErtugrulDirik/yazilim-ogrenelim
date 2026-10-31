---
title: "6.1 Önermeler mantığı"
description: "Önerme, beş bağlaç (¬ ∧ ∨ → ↔), doğruluk tablosu, totoloji, çelişki ve olumsallık, mantıksal denklik ve temel yasalar (De Morgan, dağılma, p → q ≡ ¬p ∨ q), koşulun karşıtı ve karşıt tersi, ve n değişkenli bir formülün doğruluk tablosunu bitlerle üretip sınıflandıran C programı."
---

Faz 0'da AND, OR ve NOT'u kapılar olarak, Ders 2.3'te `&&`, `||` ve `!` olarak, Faz 5'te de 32 biti birden işleyen bit operatörleri olarak gördük. Hep aynı şeyi kullandık ama adını koymadık: **mantık**. Bu fazda derleyici mühendisliğinin dayandığı matematiği kuracağız ve ilk adım, matematiğin kendi dilini öğrenmek. Her kanıt, her tanım, her "her zaman doğru" iddiası bu dille yazılır.

Bu dersin sorusu basit: bir cümlenin doğru olup olmadığını **biçimine bakarak** nasıl anlarız?

---

## 1. Önerme

**Önerme** (proposition), doğru ya da yanlış olan, ikisi birden olmayan bir cümledir.

- "7 bir asal sayıdır." → önerme (doğru)
- "2 + 2 = 5" → önerme (yanlış)
- "x > 3" → önerme **değil**: `x`'e bağlı, kendi başına doğru ya da yanlış değil (bir sonraki dersin konusu)
- "Bu programı çalıştır." → önerme değil: emir cümlesi, doğru ya da yanlış olmaz

Önermeleri küçük harflerle gösteriyoruz: $p$, $q$, $r$. Bir önermenin değeri **D** (doğru) ya da **Y** (yanlış); biz C ile uyumlu olsun diye **1** ve **0** yazacağız.

Önermeler mantığı, önermelerin **içine** bakmaz. "7 asal" ile "2 + 2 = 5" arasındaki fark, mantık için sadece biri 1, öbürü 0. Bizi ilgilendiren, önermeleri **bağlaçlarla** birleştirince ortaya çıkan yeni önermenin değeri.

---

## 2. Beş bağlaç

| Bağlaç | Simge | Okunuşu | C'de |
| --- | --- | --- | --- |
| Olumsuzlama | $\neg p$ | değil p | `!p` |
| Ve (conjunction) | $p \land q$ | p ve q | `p && q` |
| Veya (disjunction) | $p \lor q$ | p veya q | `p \|\| q` |
| Koşul (implication) | $p \to q$ | p ise q | `!p \|\| q` |
| İki yönlü koşul | $p \leftrightarrow q$ | p ancak ve ancak q | `p == q` |

Doğruluk tabloları:

| $p$ | $q$ | $\neg p$ | $p \land q$ | $p \lor q$ | $p \to q$ | $p \leftrightarrow q$ |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0 | 1 | 0 | 0 | **1** | 1 |
| 0 | 1 | 1 | 0 | 1 | **1** | 0 |
| 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| 1 | 1 | 0 | 1 | 1 | 1 | 1 |

İlk üçü tanıdık. Dikkat isteyen **koşul**.

**$p \to q$ ne zaman yanlış?** Sadece $p$ doğru ve $q$ yanlışken. "Yağmur yağarsa yerler ıslanır" sözü, ancak yağmur yağıp yerler kuru kalırsa yalan çıkar. Yağmur hiç yağmadıysa söz bozulmamıştır; yerler ister ıslak ister kuru olsun. Bu yüzden **$p$ yanlışken $p \to q$ her zaman doğru** (tablodaki kalın iki satır). Buna "boş yere doğru" (vacuously true) denir ve ileride sık karşımıza çıkacak: "boş dizinin bütün elemanları pozitiftir" doğru bir cümle.

`p == q` iki yönlü koşul için doğru çalışıyor ama bir şartla: `p` ve `q` gerçekten 0 ya da 1 olmalı. C'de `2` de "doğru" sayılır, ama `2 == 1` yanlış. Bu yüzden ya `bool` tipini kullanıyoruz (Ders 3.21; `bool`'a atanan her sıfırdan farklı değer 1 olur) ya da `!!p == !!q` yazıyoruz.

---

## 3. Bileşik önermeler ve öncelik

Bağlaçlar iç içe girince bileşik önerme oluşur: $(p \to q) \land \neg r$. Parantezleri azaltmak için öncelik sırası var: $\neg$ en güçlü, sonra $\land$, sonra $\lor$, en son $\to$ ve $\leftrightarrow$. C'de de `!` > `&&` > `||`, aynı sıra.

$n$ değişkenli bir formülün doğruluk tablosunda $2^n$ satır var: her değişken 0 ya da 1. Üç değişken 8 satır, on değişken 1024 satır. Satırları yazmanın en düzenli yolu Faz 5'ten tanıdık: **satır numarasının bitleri değişkenlerin değerleri**. 0'dan $2^n - 1$'e sayarsan bütün kombinasyonları tam bir kez gezersin.

| satır | ikilik | $p$ | $q$ | $r$ |
| --- | --- | --- | --- | --- |
| 0 | 000 | 0 | 0 | 0 |
| 1 | 001 | 0 | 0 | 1 |
| 5 | 101 | 1 | 0 | 1 |
| 7 | 111 | 1 | 1 | 1 |

---

## 4. Totoloji, çelişki, olumsallık

Bir formülün doğruluk tablosunun son sütununa bakarak onu üç sınıftan birine koyarız:

- **Totoloji**: her satırda 1. Örnek: $p \lor \neg p$ (bir şey ya doğrudur ya değildir).
- **Çelişki**: her satırda 0. Örnek: $p \land \neg p$.
- **Olumsal** (contingent): bazı satırlarda 1, bazılarında 0. Örnek: $p \to q$.

Totolojiler önemli, çünkü **biçimleri yüzünden** doğrular; içlerine hangi önermeyi koyarsan koy doğru kalırlar. Kanıtlarda kullandığımız akıl yürütme kuralları aslında totolojiler. En ünlüsü **modus ponens**: $((p \to q) \land p) \to q$. "p ise q; p doğru; o halde q doğru."

İki formül her satırda aynı değeri veriyorsa **mantıksal olarak denk**tir: $A \equiv B$. Bu, $A \leftrightarrow B$'nin totoloji olması demek.

---

## 5. Denklik yasaları

Sık kullanacağımız denklikler (hepsini doğruluk tablosuyla kontrol edebilirsin, birazdan programla edeceğiz):

| Ad | Denklik |
| --- | --- |
| Çift olumsuzlama | $\neg\neg p \equiv p$ |
| De Morgan | $\neg(p \land q) \equiv \neg p \lor \neg q$, $\quad \neg(p \lor q) \equiv \neg p \land \neg q$ |
| Değişme | $p \land q \equiv q \land p$, $\quad p \lor q \equiv q \lor p$ |
| Dağılma | $p \land (q \lor r) \equiv (p \land q) \lor (p \land r)$ |
| Dağılma | $p \lor (q \land r) \equiv (p \lor q) \land (p \lor r)$ |
| Yutma | $p \land (p \lor q) \equiv p$, $\quad p \lor (p \land q) \equiv p$ |
| Koşulun açılımı | $p \to q \equiv \neg p \lor q$ |
| Karşıt ters | $p \to q \equiv \neg q \to \neg p$ |

De Morgan'ı Faz 0'da kapılarla görmüştük; Ders 5.4'teki `~(a & b) == ~a | ~b` de aynı yasanın 32 bitlik hali. Bu yasalar kodda da işe yarıyor:

```c
if (!(x >= 0 && x < n))   // "aralikta degil"
if (x < 0 || x >= n)      // De Morgan: ayni kosul, daha okunur
```

### Karşıt ve karşıt ters

Bir koşuldan türeyen üç önerme var ve sık karıştırılıyor:

| Ad | Biçim | $p \to q$ ile denk mi? |
| --- | --- | --- |
| Koşulun kendisi | $p \to q$ | — |
| Karşıtı (converse) | $q \to p$ | **hayır** |
| Tersi (inverse) | $\neg p \to \neg q$ | **hayır** |
| Karşıt tersi (contrapositive) | $\neg q \to \neg p$ | **evet** |

"Sayı 4'e bölünüyorsa çifttir" doğru. Karşıtı "çiftse 4'e bölünür" yanlış (6). Karşıt tersi "çift değilse 4'e bölünmez" doğru. Karşıt tersin koşulla denk olması, Ders 6.3'teki kanıt tekniklerinden birinin temeli olacak.

---

## 6. Doğruluk tablosu üreten program

Şimdi bütün bunları makineye yaptıralım. Formülü bir fonksiyon olarak yazıyoruz; fonksiyon, değişkenlerin değerlerini bir `bool` dizisinden okuyor. Doğruluk tablosu fonksiyonu formülü Ders 4.11'deki gibi bir **fonksiyon pointer'ı** olarak alıyor:

```c
#include <stdio.h>
#include <stdbool.h>

typedef bool (*formula_fn)(const bool *v);

static bool implies(bool p, bool q) { return !p || q; }
static bool iff(bool p, bool q) { return p == q; }

static bool de_morgan(const bool *v) {          // !(p && q) <-> (!p || !q)
    return iff(!(v[0] && v[1]), !v[0] || !v[1]);
}
static bool converse(const bool *v) {           // (p -> q) <-> (q -> p)
    return iff(implies(v[0], v[1]), implies(v[1], v[0]));
}
static bool modus_ponens(const bool *v) {       // ((p -> q) && p) -> q
    return implies(implies(v[0], v[1]) && v[0], v[1]);
}
static bool contradiction(const bool *v) {      // p && !p
    return v[0] && !v[0];
}

// n degiskenli formulun dogruluk tablosunu yazar, dogru satir sayisini dondurur
static int truth_table(const char *name, formula_fn f, int n) {
    bool v[8];
    int count = 0;
    printf("%s\n", name);
    for (unsigned row = 0; row < (1u << n); row++) {
        for (int i = 0; i < n; i++) {
            v[i] = (row >> (n - 1 - i)) & 1;   // en soldaki degisken en yuksek bit
            printf("%d ", v[i]);
        }
        bool r = f(v);
        count += r;
        printf("| %d\n", r);
    }
    return count;
}

static void classify(const char *name, formula_fn f, int n) {
    int count = truth_table(name, f, n);
    int rows = 1 << n;
    if (count == rows)   printf("=> totoloji\n\n");
    else if (count == 0) printf("=> celiski\n\n");
    else                 printf("=> olumsal (%d/%d)\n\n", count, rows);
}

int main(void) {
    classify("De Morgan", de_morgan, 2);
    classify("Karsit (converse)", converse, 2);
    classify("Modus ponens", modus_ponens, 2);
    classify("p && !p", contradiction, 1);
    return 0;
}
```

```
De Morgan
0 0 | 1
0 1 | 1
1 0 | 1
1 1 | 1
=> totoloji

Karsit (converse)
0 0 | 1
0 1 | 0
1 0 | 0
1 1 | 1
=> olumsal (2/4)

Modus ponens
0 0 | 1
0 1 | 1
1 0 | 1
1 1 | 1
=> totoloji

p && !p
0 | 0
1 | 0
=> celiski
```

Program, De Morgan'ın bir yasa olduğunu, koşulla karşıtının denk **olmadığını** (iki satırda ayrılıyorlar) ve modus ponens'in totoloji olduğunu doğruladı. `(row >> (n - 1 - i)) & 1`, Ders 5.2'deki tek bit okuma: satır numarasının $i$'inci değişkene karşılık gelen bitini alıyor.

Bu yöntemin bir sınırı var: $2^n$ satır. 20 değişkende bir milyon satır hâlâ hızlı, 60 değişkende evrenin ömrü yetmez. Bir formülün **sağlanabilir** olup olmadığını (en az bir satırda 1 veren bir atama var mı?) bulmak ünlü **SAT** problemi; bilinen hiçbir algoritma her durumda bunu üstel zamandan hızlı çözemiyor. Faz 19'daki SMT çözücüler bu problemi akıllıca budayarak pratikte binlerce değişkenle çözüyor.

---

## Alıştırmalar

**1** – $p \to (q \to r)$ ile $(p \land q) \to r$ denk mi? Önce elle doğruluk tablosu yaz, sonra programa yeni bir formül fonksiyonu ekleyip doğrula.

**2** – $p \to q$ ile $q \to p$'nin hangi satırlarda farklı olduğunu programın çıktısından oku. "Sayı 4'e bölünüyorsa çifttir" örneğinde bu satırlar hangi sayılara karşılık geliyor?

**3** – Sadece `!` ve `&&` kullanarak `||`, `->` ve `<->`'yi yaz. (İpucu: De Morgan.) Bu, iki bağlacın bütün mantığı ifade etmeye yettiğini gösteriyor. Tek bir bağlaç yeter mi? NAND ($\neg(p \land q)$) ile $\neg p$ ve $p \land q$'yu kur.

**4** – `if (!(a > 0) || !(b > 0))` koşulunu De Morgan ile tek `!` içeren hale, sonra hiç `!` içermeyen hale getir.

**5** – `classify`'ı değiştirip olumsal formüllerde **doğru olan satırları** ayrıca listele. Bu satırlar formülün **sağlayan atamaları**. Bir formülün sağlanabilir olduğunu söylemek için kaç tanesini bulman yeter?

<details>
<summary>Cevaplar</summary>

**1** – Denk. Tek yanlış satır ikisinde de $p = 1, q = 1, r = 0$: sol tarafta $q \to r$ yanlış olur, $p$ doğru olduğu için bütün koşul yanlış; sağ tarafta $p \land q$ doğru, $r$ yanlış, koşul yanlış. Diğer yedi satırda ikisi de doğru. Programda:

```c
static bool curry(const bool *v) {   // (p -> (q -> r)) <-> ((p && q) -> r)
    return iff(implies(v[0], implies(v[1], v[2])), implies(v[0] && v[1], v[2]));
}
// classify("Curry", curry, 3);  =>  totoloji
```

Bu denklik, "iki koşul arka arkaya" ile "iki koşul birlikte" aynı şey demek; programlama dillerinde iki parametreli bir fonksiyonu tek parametreli fonksiyon döndüren fonksiyona çevirmenin (currying) mantıktaki karşılığı.

**2** – Satır `0 1` ($p = 0, q = 1$): koşul doğru, karşıt yanlış. Satır `1 0` ($p = 1, q = 0$): koşul yanlış, karşıt doğru. $p$ = "4'e bölünür", $q$ = "çift" dersek, `0 1` satırı 4'e bölünmeyen ama çift sayılar: 2, 6, 10. Bu sayılar karşıtı ("çiftse 4'e bölünür") çürüten karşı örnekler. `1 0` satırına (4'e bölünüp tek olan) hiçbir sayı düşmüyor; koşulun kendisi bu yüzden doğru.

**3** –

```c
bool or_(bool p, bool q)      { return !(!p && !q); }        // De Morgan
bool implies_(bool p, bool q) { return !(p && !q); }         // p -> q = !(p && !q)
bool iff_(bool p, bool q)     { return implies_(p, q) && implies_(q, p); }
```

NAND tek başına yeter: `nand(p, p)` = $\neg p$; `nand(nand(p, q), nand(p, q))` = $\neg\neg(p \land q)$ = $p \land q$. $\neg$ ve $\land$ elde edilince, yukarıdaki gibi her şey elde edilir. Bu yüzden bir işlemcinin bütün mantık devreleri ilke olarak sadece NAND kapılarından kurulabilir; Faz 7'deki Nand2Tetris tam olarak bunu yapıyor.

**4** – `!(a > 0) || !(b > 0)` = `!(a > 0 && b > 0)` (De Morgan, tek `!`). `!` olmadan: `a <= 0 || b <= 0`, çünkü $\neg(a > 0)$ tamsayılarda $a \le 0$ demek.

**5** –

```c
// truth_table icinde, r hesaplandiktan sonra:
if (r) printf("   <- saglayan atama\n");
```

Sağlanabilir olduğunu göstermek için **bir** sağlayan atama yeter; bu bir **tanık** (witness). Buna karşılık bir formülün sağlanamaz (çelişki) olduğunu göstermek için **bütün** satırlara bakmak gerekiyor. "Var" demek bir örnekle, "yok" demek her şeyi kontrol ederek: bu asimetri bir sonraki dersteki $\exists$ ve $\forall$'ın da asimetrisi.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §1.1–1.3: önermeler, bağlaçlar, mantıksal denklik.
- Daniel Velleman, *How to Prove It* (3. baskı), Bölüm 1: önermeler mantığı ve doğruluk tabloları.
- Noam Nisan & Shimon Schocken, *The Elements of Computing Systems*, Bölüm 1: her şeyi NAND'dan kurmak.

**Sıradaki ders:** Yüklemler mantığı. "Her" ve "bazı" kelimelerinin matematiksel karşılığı: $\forall$ ve $\exists$.
