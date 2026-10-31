---
title: "6.8 Kafes (lattice) teorisi"
description: "Üst sınır, alt sınır, en küçük üst sınır (join, ⊔) ve en büyük alt sınır (meet, ⊓); kafesin tanımı ve örnekleri (kuvvet kümesi, bölenler, zincirler, işaret kafesi); tam kafes ve ⊥, ⊤; monoton fonksiyon; sabit nokta ve Knaster–Tarski teoremi; sonlu yükseklikte ⊥'dan başlayan yinelemenin en küçük sabit noktayı bulması; programdaki erişilebilir blokları sabit nokta yinelemesiyle bulan C programı, veri akışı analizinin önizlemesi."
---

Ders 6.7'de 12'nin bölenlerinin Hasse diyagramını çizdik. Diyagramda bir şey dikkat çekiyor: hangi iki elemanı seçersen seç, ikisinin de **üstünde** olan elemanlar arasında en alttaki tek ve belli. 4 ve 6 için: ikisinin de üstünde sadece 12 var. 2 ve 3 için: 6 ve 12 var, en alttaki 6. Bu sayı EKOK. Aynı şekilde ikisinin de **altında** olanlar arasında en üstteki EBOB.

Her çift için böyle bir "en küçük üst" ve "en büyük alt" olan posetlere **kafes** (lattice) denir. Bu ders fazın derleyiciyle en doğrudan bağlantılı dersi: Faz 16'daki her veri akışı analizi (canlılık, sabit yayılımı, erişen tanımlar) bir kafes üzerinde bir sabit nokta hesaplıyor. Burada o hesabın matematiğini kurup küçük bir örneğini yazacağız.

---

## 1. Sınırlar

$(A, \preceq)$ bir poset, $S \subseteq A$ olsun.

- $u$, $S$'nin bir **üst sınırı**: $\forall s \in S\, (s \preceq u)$
- $l$, $S$'nin bir **alt sınırı**: $\forall s \in S\, (l \preceq s)$
- **En küçük üst sınır** (supremum, join): üst sınırların en küçüğü. $\bigsqcup S$ ya da iki eleman için $a \sqcup b$.
- **En büyük alt sınır** (infimum, meet): alt sınırların en büyüğü. $\bigsqcap S$ ya da $a \sqcap b$.

En küçük ve en büyük eleman, Ders 6.7'deki gibi, varsa tek. Ama var olmayabilir: $\{2, 3, 4, 5, 6, 8, 9\}$ posetinde (bölünebilirlik) $4$ ve $6$'nın hiç ortak üst sınırı yok (12 kümede değil). $2$ ile $3$'ün ortak alt sınırı da yok.

Üç örnekte join ve meet:

| Poset | $a \sqcup b$ | $a \sqcap b$ |
| --- | --- | --- |
| $(\mathbb{Z}, \le)$ | $\max(a, b)$ | $\min(a, b)$ |
| $(\mathbb{N}^+, \mid)$ | $\text{EKOK}(a, b)$ | $\text{EBOB}(a, b)$ |
| $(\mathcal{P}(S), \subseteq)$ | $a \cup b$ | $a \cap b$ |

Son satırı kanıtlayalım: $a \cup b$ hem $a$'yı hem $b$'yi içeriyor (üst sınır); ikisini de içeren her $u$, birleşimlerini de içerir (en küçük). Ders 6.5'teki bit temsilinde join `|`, meet `&`.

Ders 2.9'daki EBOB ve EKOK'un "en büyük" ve "en küçük" kelimeleri bu açıdan yanıltıcı: kastedilen sayısal büyüklük değil, **bölünebilirlik sıralamasında** en büyük ve en küçük. EBOB(4, 6) = 2 demek, "4 ve 6'yı bölen sayılar arasında, hepsine bölünen."

---

## 2. Kafes

Bir poset, **her iki elemanın** join'i ve meet'i varsa bir **kafes**tir.

Yukarıdaki üç poset de kafes. Ders 6.7'deki 12'nin bölenleri ve kuvvet kümesi küpü de. Kafes **olmayan** bir örnek:

```
    c     d
    | \ / |
    |  X  |
    | / \ |
    a     b
```

$a, b \preceq c, d$. $a$ ile $b$'nin üst sınırları $c$ ve $d$, ama ikisi karşılaştırılamıyor; **en küçük** üst sınır yok.

Kafeste join ve meet, birer **ikili işlem** gibi davranıyor ve tanıdık yasalara uyuyor:

| Yasa | Join | Meet |
| --- | --- | --- |
| Değişme | $a \sqcup b = b \sqcup a$ | $a \sqcap b = b \sqcap a$ |
| Birleşme | $(a \sqcup b) \sqcup c = a \sqcup (b \sqcup c)$ | aynı şekilde |
| Tek kuvvetlilik | $a \sqcup a = a$ | $a \sqcap a = a$ |
| Yutma | $a \sqcup (a \sqcap b) = a$ | $a \sqcap (a \sqcup b) = a$ |

Ve sıralama join'den geri okunabiliyor: $a \preceq b \iff a \sqcup b = b$. Bunlar Ders 6.5'teki küme yasalarının, Ders 6.1'deki mantık yasalarının genellemesi. `max`, `|`, EKOK hepsi aynı yasalara uyuyor; çünkü hepsi bir join.

### Bir derleyici kafesi: işaret

Bir derleyici her değişken için "bu değişkenin işareti ne?" sorusunu cevaplamak istesin. Mümkün cevaplar:

```
            ⊤        "bilinmiyor: her sey olabilir"
         /  |  \
        −   0   +
         \  |  /
            ⊥        "henuz hicbir deger gormedik"
```

Join "iki bilgiyi birleştir" demek. Bir `if`'in bir dalında `x = 5` (+), diğerinde `x = -3` (−) ise, birleşme noktasında $+ \sqcup - = \top$: "işareti bilinmiyor". İki dalda da `x = 5` ise $+ \sqcup + = +$; bilgi korunuyor. $\bot \sqcup a = a$: "hiçbir şey" ile birleştirmek bilgiyi değiştirmiyor.

Bu kafeste aşağısı "daha kesin bilgi", yukarısı "daha az kesin". Derleyicinin her analizi böyle bir kafes seçiyor.

---

## 3. Tam kafes

Kafes tanımı her **iki** elemanın join'ini istiyor; tümevarımla (Ders 6.4) her **sonlu** alt kümenin join'i de var. Bir posette **her** alt kümenin (sonsuz olanlar ve $\emptyset$ dahil) join'i ve meet'i varsa **tam kafes** (complete lattice) denir.

Tam kafesin en altı ve en üstü var:

- $\bot = \bigsqcup \emptyset = \bigsqcap A$ ("dip", bottom)
- $\top = \bigsqcap \emptyset = \bigsqcup A$ ("tepe", top)

($\bigsqcup \emptyset$, boş kümenin üst sınırlarının en küçüğü; **her** eleman boş kümenin üst sınırı (boş yere doğru), dolayısıyla en küçüğü $\bot$.)

- Her **sonlu** kafes tam kafestir.
- $(\mathcal{P}(S), \subseteq)$ her $S$ için tam: $\bot = \emptyset$, $\top = S$.
- $(\mathbb{Z}, \le)$ tam değil: $\mathbb{Z}$'nin kendisinin üst sınırı yok.

---

## 4. Monoton fonksiyon ve sabit nokta

Bir $f : A \to A$ fonksiyonu (Ders 6.9'da fonksiyonları ayrıntılı göreceğiz; şimdilik "her elemana bir eleman atayan kural"):

- **Monoton**: $a \preceq b \to f(a) \preceq f(b)$. Sırayı koruyor; daha büyük girdi, daha büyük (ya da eşit) çıktı.
- $x$, $f$'in bir **sabit noktası**: $f(x) = x$.

Örnekler $(\mathbb{Z}, \le)$'de: $f(x) = x + 1$ monoton, sabit noktası yok. $f(x) = \lfloor x / 2 \rfloor$ monoton, sabit noktaları $0$ ve $-1$. $f(x) = -x$ monoton değil.

**Teorem (Knaster–Tarski).** $(L, \preceq)$ bir tam kafes ve $f : L \to L$ monoton ise, $f$'in sabit noktalarının kümesi de bir tam kafestir. Özellikle $f$'in bir **en küçük sabit noktası** vardır:

$$
\text{lfp}(f) = \bigsqcap \{x \in L \mid f(x) \preceq x\}.
$$

**Kanıt.** $D = \{x \mid f(x) \preceq x\}$ ve $m = \bigsqcap D$ olsun ($L$ tam kafes, bu meet var). Her $x \in D$ için $m \preceq x$; monotonlukla $f(m) \preceq f(x) \preceq x$. Demek $f(m)$, $D$'nin bir alt sınırı, ve $m$ en büyük alt sınır olduğu için $f(m) \preceq m$. (1)

(1)'e monotonluğu uygula: $f(f(m)) \preceq f(m)$. Yani $f(m) \in D$, ve $m$, $D$'nin alt sınırı olduğu için $m \preceq f(m)$. (2)

(1) ve (2) ile ters simetri: $f(m) = m$. Sabit nokta. Her sabit nokta $D$'de olduğu için $m$ hepsinden küçük ya da eşit; en küçük sabit nokta. $\blacksquare$

Teoremin ikinci hali (en büyük sabit nokta $\bigsqcup \{x \mid x \preceq f(x)\}$) simetrik.

Bu teoremin gücü **varlık** garantisi: tam kafes ve monoton fonksiyon varsa, sabit nokta **kesinlikle** var. Ama nasıl bulacağımızı söylemiyor.

### Sabit noktayı hesaplamak

Kafesin **yüksekliği** sonluysa (en uzun $\bot \prec a_1 \prec a_2 \prec \dots$ zinciri sonlu, örneğin sonlu bir kafes) bulmak kolay: **$\bot$'dan başla ve $f$'i uygulamaya devam et.**

$$
\bot \preceq f(\bot) \preceq f(f(\bot)) \preceq \dots
$$

**Teorem (Kleene yinelemesi, sonlu yükseklik).** Bu zincir artar, sonlu adımda durur ve durduğu yer $\text{lfp}(f)$'tir.

**Kanıt.** *Artar*: $\bot \preceq f(\bot)$ çünkü $\bot$ her şeyden küçük. $f^k(\bot) \preceq f^{k+1}(\bot)$ ise monotonlukla $f^{k+1}(\bot) \preceq f^{k+2}(\bot)$ (tümevarım). *Durur*: kesin artan bir zincir yükseklikten uzun olamaz; bir yerde $f^{k+1}(\bot) = f^k(\bot)$, sabit nokta. *En küçük*: $p$ herhangi bir sabit nokta olsun. $\bot \preceq p$; $f^k(\bot) \preceq p$ ise $f^{k+1}(\bot) \preceq f(p) = p$ (tümevarım). Demek bulunan sabit nokta her sabit noktanın altında. $\blacksquare$

Bu, Faz 16'daki **worklist algoritmasının** matematiği: başlangıçta "hiçbir şey bilmiyoruz" ($\bot$), her turda bilgiyi bir adım yay, bilgi değişmeyince dur.

---

## 5. Örnek: erişilebilir bloklar

Bir programın kontrol akış grafı (Faz 16'da kuracağız; şimdilik Faz 1'deki akış diyagramı gibi düşün): bloklar ve bloklardan bloklara geçişler. Hangi bloklar programın başından (blok 0) **erişilebilir**? Erişilemeyen bloklar ölü kod; derleyici onları silebilir.

```
    ┌───────────┐
    ↓           │
0 → 1 → 2 → 4 ──┘
    │       ↑
    └─→ 3 ──┘   4 → 5 ← 6
```

Kenarlar: $0 \to 1$, $1 \to 2$, $1 \to 3$, $2 \to 4$, $3 \to 4$, $4 \to 1$ (bir döngü), $4 \to 5$, $6 \to 5$.

Kafes: $(\mathcal{P}(\{0, \dots, 6\}), \subseteq)$, tam kafes, $\bot = \emptyset$. Fonksiyon:

$$
f(S) = \{0\} \cup \{v \mid \exists u \in S\, (u \to v)\}
$$

"Giriş bloğu, artı $S$'deki blokların ardılları." Monoton: $S$ büyürse ardılları da büyür. Erişilebilir bloklar kümesi $R$ için $f(R) = R$ olmalı (giriş erişilebilir, erişilebilir bir bloğun ardılı erişilebilir), ve $R$ bunu sağlayan **en küçük** küme. Yani $R = \text{lfp}(f)$.

```c
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define N 7
typedef uint32_t set32;

// succ[v]: v'den tek adimda gidilen bloklar
static set32 succ[N];
static void edge(int u, int v) { succ[u] |= (set32)1 << v; }

// f(S) = {0} u (S'deki bloklarin ardillari)
static set32 f(set32 S) {
    set32 r = (set32)1 << 0;
    for (int v = 0; v < N; v++)
        if ((S >> v) & 1) r |= succ[v];
    return r;
}

int main(void) {
    edge(0, 1); edge(1, 2); edge(1, 3); edge(2, 4); edge(3, 4); edge(4, 1); edge(4, 5);
    edge(6, 5);                       // 6'ya hicbir yerden gelinmiyor: olu kod

    set32 S = 0;                      // alt eleman: bos kume
    for (int i = 0; ; i++) {
        printf("adim %d: ", i); set_print(S); printf("\n");
        set32 next = f(S);
        if (next == S) break;         // sabit nokta
        S = next;
    }
    printf("erisilemeyen: "); set_print(~S & ((1u << N) - 1)); printf("\n");
    return 0;
}
```

(`set_print`, Ders 6.5'teki fonksiyon; döngüdeki sınır `N`.)

```
adim 0: {}
adim 1: {0}
adim 2: {0, 1}
adim 3: {0, 1, 2, 3}
adim 4: {0, 1, 2, 3, 4}
adim 5: {0, 1, 2, 3, 4, 5}
erisilemeyen: {6}
```

Zincir Kleene teoremindeki gibi artıyor: $\emptyset \subseteq \{0\} \subseteq \{0, 1\} \subseteq \dots$ Her adım bilgiyi bir blok daha ileri yayıyor. Döngü ($4 \to 1$) sorun çıkarmıyor: 1 zaten kümede, tekrar eklemek bir şey değiştirmiyor (join tek kuvvetli). 6. adımda küme değişmiyor; sabit nokta. Blok 6 ölü kod.

Neden **en küçük** sabit nokta? $\{0, \dots, 6\}$ de $f(S) \subseteq S$'yi sağlıyor ama "6 erişilebilir" yanlış bir iddia. En küçük sabit nokta sadece **kanıtlanabilen** gerçekleri içeriyor: $\bot$'dan başlayıp yalnızca kuralların gerektirdiğini ekliyoruz. Bu, Ders 6.4'teki tümevarımın kafes dilindeki hali; $R$, "0 içinde olan ve ardıllara kapalı" en küçük küme, tıpkı $\mathbb{N}$'nin "0'ı içeren ve $+1$'e kapalı" en küçük küme olması gibi.

Kod, bu dersin bütün kavramlarını kullanıyor: kafes ($\mathcal{P}$, bitmask), join (`|`), $\bot$ (`0`), monoton fonksiyon (`f`), sabit nokta testi (`next == S`). Faz 16'da kafesler değişecek (işaret kafesi, sabit değerler kafesi, canlı değişkenler kümesi) ve fonksiyonlar her bloğun komutlarına göre kurulacak; ama döngü aynı.

---

## Alıştırmalar

**1** – $(\{1, 2, 3, 4, 6, 12\}, \mid)$'de $4 \sqcup 6$, $4 \sqcap 6$, $2 \sqcup 3$, $3 \sqcap 4$'ü bul. Bu kafeste $\bot$ ve $\top$ ne?

**2** – İşaret kafesinde toplama için bir "soyut toplama" tablosu yaz: iki işaret verildiğinde toplamın işareti. ($+$ ile $+$ toplamı $+$; $+$ ile $-$ toplamı ne?) Satır ve sütunlara $\bot$, $-$, $0$, $+$, $\top$ koy. Bu işlem monoton mu?

**3** – Bölüm 5'teki programa `edge(6, 6)` ekle. En küçük sabit nokta değişiyor mu? Şimdi $\top$'dan (bütün bloklar) başlayıp $f$'i uygula; nereye varıyorsun? İki sabit nokta arasındaki fark ne anlatıyor?

**4** – $\mathcal{P}(\{0, 1\})$ üzerinde $f(S) = \overline{S}$ (tümleyen) monoton mu? Sabit noktası var mı? Bu, Knaster–Tarski'nin monotonluk şartı hakkında ne söylüyor?

**5** – Kleene teoreminin kanıtında "sonlu yükseklik" nerede kullanıldı? $(\mathbb{N} \cup \{\infty\}, \le)$ tam kafes, ve $f(n) = n + 1$, $f(\infty) = \infty$. $\bot = 0$'dan yineleme ne yapıyor? Sabit nokta var mı?

<details>
<summary>Cevaplar</summary>

**1** – $4 \sqcup 6 = \text{EKOK} = 12$, $4 \sqcap 6 = \text{EBOB} = 2$, $2 \sqcup 3 = 6$, $3 \sqcap 4 = 1$. $\bot = 1$ (her sayıyı böler), $\top = 12$ (her sayıya bölünür).

**2** –

| $+$ | $\bot$ | $-$ | $0$ | $+$ | $\top$ |
| --- | --- | --- | --- | --- | --- |
| $\bot$ | $\bot$ | $\bot$ | $\bot$ | $\bot$ | $\bot$ |
| $-$ | $\bot$ | $-$ | $-$ | $\top$ | $\top$ |
| $0$ | $\bot$ | $-$ | $0$ | $+$ | $\top$ |
| $+$ | $\bot$ | $\top$ | $+$ | $+$ | $\top$ |
| $\top$ | $\bot$ | $\top$ | $\top$ | $\top$ | $\top$ |

$+$ ile $-$'nin toplamı $\top$: $5 + (-3) > 0$ ama $3 + (-5) < 0$; işaret bilinemez. $\bot$ satırı: hiç değer yoksa toplam da yok. Monoton: bir girdiyi yukarı taşımak (örneğin $+$'yı $\top$'a) sonucu aşağı indirmiyor; tabloda her satır ve sütun boyunca sağa/aşağı gidince değerler hiç "inmiyor". Derleyicinin soyut işlemlerinin monoton olması, Knaster–Tarski'yi kullanabilmenin şartı.

**3** – En küçük sabit nokta değişmiyor: $\{0, \dots, 5\}$. Blok 6 kendine dönüyor ama oraya **girilemiyor**. $\top$'dan başlayınca: $f(\{0, \dots, 6\}) = \{0\} \cup \{1, 2, 3, 4, 5, 6\} = \{0, \dots, 6\}$, hemen sabit nokta. İkisi farklı: en büyük sabit nokta 6'yı da içeriyor, çünkü "6 erişilebilir **varsayılırsa**, kendi kendini doğruluyor" (6'nın ardılı 6). En küçük sabit nokta kanıtlanabilen gerçekleri, en büyük ise çürütülemeyen varsayımları veriyor. Erişilebilirlik için doğru olan en küçük; bazı analizler (örneğin "bu döngü sonsuza kadar sürebilir mi?") en büyüğü istiyor.

**4** – Monoton değil: $\emptyset \subseteq \{0\}$ ama $f(\emptyset) = \{0, 1\} \not\subseteq \{1\} = f(\{0\})$. Küme büyüyünce tümleyeni küçülüyor; sırayı **ters çeviriyor**. Sabit noktası da yok: $S = \overline{S}$ olsaydı her eleman hem $S$'de hem $S$'nin dışında olurdu. Kafes tam, ama fonksiyon monoton olmadığı için teorem hiçbir şey garanti etmiyor ve gerçekten de sabit nokta yok. Yinelemeyle de görülüyor: $\emptyset \to \{0, 1\} \to \emptyset \to \dots$, sonsuza kadar salınıyor. Derleyicide monoton olmayan bir transfer fonksiyonu yazmak, analizin hiç bitmemesine yol açar.

**5** – Kanıtın "durur" adımında: kesin artan zincirin uzunluğu yükseklikle sınırlı olmalı. Burada $0, 1, 2, 3, \dots$ zinciri sonsuza kadar artıyor, yineleme hiç durmuyor. Sabit nokta var ($\infty$), Knaster–Tarski bunu garanti ediyor, ama $\bot$'dan sonlu adımla ona ulaşılamıyor. Derleyiciler bu yüzden ya sonlu yükseklikli kafes seçiyor, ya da sonsuz kafeslerde (örneğin "bu değişkenin değer aralığı") yinelemeyi zorla durduran **genişletme** (widening) operatörü kullanıyor: "üç turdur artıyorsa, $\infty$ de". Faz 16'da göreceğiz.

</details>

---

## Kaynaklar

- Brian Davey & Hilary Priestley, *Introduction to Lattices and Order* (2. baskı), Bölüm 2 ve 8: kafesler, tam kafesler, sabit nokta teoremleri.
- Alfred Tarski, "A lattice-theoretical fixpoint theorem and its applications", *Pacific Journal of Mathematics* 5(2), 1955.
- Flemming Nielson, Hanne Riis Nielson & Chris Hankin, *Principles of Program Analysis*, Bölüm 1–2 ve Ek A: kafesler ve veri akışı analizi.
- Anders Møller & Michael Schwartzbach, *Static Program Analysis* (ders notları, ücretsiz), Bölüm 4–5: kafes teorisi ve monoton çerçeve.

**Sıradaki ders:** Fonksiyonlar. Birebir, örten, bileşke, ters; ve sonsuzlukların da büyüklükleri olduğu: Cantor'un köşegen yöntemi.
