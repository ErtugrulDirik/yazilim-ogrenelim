---
title: "6.7 Kısmi sıralamalar"
description: "Kısmi sıralama (yansıyan, ters simetrik, geçişli) ve poset; ≤, bölünebilirlik ve ⊆ örnekleri; karşılaştırılamayan elemanlar ve tam sıralama; örtme bağıntısı ve Hasse diyagramı (12'nin bölenleri); minimal, maksimal, en küçük ve en büyük eleman; sözlük sıralaması; topolojik sıralama ve derleme bağımlılıklarını doğru sırayla dizen, döngüyü algılayan Kahn algoritması."
---

Ders 6.6'nın tablosunda iki desen gördük. Yansıyan + simetrik + geçişli bağıntılar **denklik**ti: "bir açıdan aynı". Bu derste ötekisi: yansıyan + **ters** simetrik + geçişli. Sezgisi: "önce gelir", "küçüktür ya da eşittir", "parçasıdır", "bağlıdır".

Hayatın birçok sıralaması sayıların sıralaması kadar düzgün değil. İki sayıdan biri her zaman diğerinden küçük ya da ona eşit; ama iki görevden biri her zaman öbüründen önce yapılmak zorunda değil. Kısmi sıralama bu "bazen karşılaştırılamaz" durumu matematiğe sokuyor.

---

## 1. Tanım

$A$ üzerinde bir bağıntı $\preceq$ şu üç özelliği sağlıyorsa bir **kısmi sıralama**dır (partial order):

- **Yansıyan**: $a \preceq a$
- **Ters simetrik**: $a \preceq b \land b \preceq a \to a = b$
- **Geçişli**: $a \preceq b \land b \preceq c \to a \preceq c$

$(A, \preceq)$ ikilisine **kısmi sıralı küme**, kısaca **poset** denir. $a \preceq b$ ve $a \ne b$ ise $a \prec b$ yazarız ("kesin önce").

Üç temel örnek:

| Poset | $a \preceq b$ demek | Ders 6.6'daki denetim |
| --- | --- | --- |
| $(\mathbb{Z}, \le)$ | $a$, $b$'den küçük ya da eşit | `<=` satırı |
| $(\mathbb{N}^+, \mid)$ | $a$, $b$'yi böler | Alıştırma 1 |
| $(\mathcal{P}(S), \subseteq)$ | $a$, $b$'nin alt kümesi | Ders 6.5'teki `set_subset` |

Ters simetrinin rolü: döngüyü yasaklamak. $a \prec b \prec a$ olamaz, çünkü ters simetri bu durumda $a = b$ der. Bir sıralamada "kendi kendinden önce gelmek" saçma.

---

## 2. Karşılaştırılabilirlik

$a \preceq b$ ya da $b \preceq a$ ise $a$ ile $b$ **karşılaştırılabilir**. "Kısmi" kelimesi tam buradan geliyor: kısmi sıralamada bazı çiftler karşılaştırılamayabilir.

- $(\mathbb{N}^+, \mid)$: $2$ ile $3$ karşılaştırılamaz. Biri öbürünü bölmüyor.
- $(\mathcal{P}(S), \subseteq)$: $\{1\}$ ile $\{2\}$ karşılaştırılamaz.

Her çift karşılaştırılabiliyorsa sıralama **tam** (total, ya da doğrusal) sıralama. $\le$ tamdır; $\mid$ ve $\subseteq$ değil.

Bu ayrımın kodda karşılığı var. Ders 4.11'deki `qsort`, karşılaştırma fonksiyonunun bir **tam** sıralama vermesini bekliyor: her iki eleman için negatif, sıfır ya da pozitif bir cevap. Kısmi bir sıralamayı `qsort`'a verirsen ("böler mi? değilse 0 döndür" gibi) geçişlilik bozulur ve sonuç anlamsız olur. Bölüm 5'te kısmi sıralamaları doğru şekilde dizmeyi göreceğiz.

### Sözlük sıralaması

İki tam sıralamadan yeni bir tam sıralama kurmanın standart yolu **sözlük sıralaması** (lexicographic order):

$$
(a_1, a_2) \preceq (b_1, b_2) \iff a_1 < b_1 \lor (a_1 = b_1 \land a_2 \le b_2)
$$

Önce ilk bileşene bak; eşitse ikinciye. Ders 4.16'daki `strcmp` stringleri tam böyle karşılaştırıyor: ilk farklı karaktere kadar ilerle, orada karar ver. Tarihleri (yıl, ay, gün) karşılaştırmak da aynı.

---

## 3. Hasse diyagramı

Bir posetin bütün ikililerini çizmek karmaşık: geçişlilik ve yansıma bir sürü gereksiz ok ekliyor. **Hasse diyagramı** sadece özü çiziyor.

$b$, $a$'yı **örter** (covers): $a \prec b$ ve arada başka eleman yok, yani $a \prec c \prec b$ olan bir $c$ yok. Hasse diyagramında:

- Sadece örtme ilişkileri çizilir (yansıma halkaları ve geçişlilikten gelen oklar atlanır)
- Ok yerine çizgi, ve **büyük eleman yukarıda**

12'nin bölenleri, bölünebilirliğe göre. Örtme ilişkilerini bir programla bulalım: $a \mid b$ ve arada $a \mid c \mid b$ olan bir $c$ yok.

```
1 covers: 2 3
2 covers: 4 6
3 covers: 6
4 covers: 12
6 covers: 12
```

```
        12
       /  \
      4    6
      |  /  |
      2     3
       \   /
         1
```

$1 \mid 12$ var ama çizilmiyor: $1 - 2 - 4 - 12$ yolundan geçişlilikle çıkıyor. Diyagramdan bütün sıralamayı geri okuyabilirsin: $a \preceq b \iff$ $a$'dan $b$'ye **yukarı doğru** bir yol var. Ders 6.6'nın dilinde: sıralama, örtme bağıntısının **yansıyan geçişli kapanışı**.

$\mathcal{P}(\{x, y, z\})$'in Hasse diyagramı bir küp:

```
          {x,y,z}
         /   |   \
     {x,y} {x,z} {y,z}
       | \ /   \ /  |
       |  X     X   |
       | / \   / \  |
      {x}   {y}   {z}
         \   |   /
            { }
```

Her kenar tek bir eleman ekliyor. Ders 6.5'teki bit temsilinde: tek bir biti 1 yapmak. Küpün köşeleri 3 bitlik sayılar, kenarları ise tek bit farklı olan sayılar arası (Ders 5.16'daki Gray kodu bu küpün kenarlarında yürüyor).

---

## 4. Özel elemanlar

$(A, \preceq)$ bir poset olsun.

| Ad | Tanım | Sezgisi |
| --- | --- | --- |
| **Minimal** | $\neg\exists x\, (x \prec a)$ | altında kimse yok |
| **Maksimal** | $\neg\exists x\, (a \prec x)$ | üstünde kimse yok |
| **En küçük** (least) | $\forall x\, (a \preceq x)$ | herkesin altında |
| **En büyük** (greatest) | $\forall x\, (x \preceq a)$ | herkesin üstünde |

Minimal ile en küçük farklı! $\{2, 3, 4, 6\}$ bölünebilirliğe göre: $2$ ve $3$ **minimal** (hiçbiri bu kümede başka bir sayıyla bölünmüyor), ama **en küçük** eleman yok (2, 3'ü bölmüyor). Minimal "yerel", en küçük "küresel" bir özellik. Tam sıralamada ikisi çakışıyor.

En küçük eleman varsa tektir (iki tane olsa, $a \preceq b$ ve $b \preceq a$, ters simetriyle $a = b$). Hasse diyagramında en küçük eleman en altta tek başına duran nokta: 12'nin bölenlerinde $1$, kuvvet kümesinde $\emptyset$. Bu elemanlar bir sonraki derste $\bot$ ("dip") adını alacak.

**Teorem.** Sonlu ve boş olmayan her posetin en az bir minimal elemanı vardır.

**Kanıt.** Herhangi bir $a_0$ ile başla. Minimalse bitti. Değilse $a_1 \prec a_0$ olan bir $a_1$ var. Minimalse bitti; değilse $a_2 \prec a_1$... Zincir $a_0 \succ a_1 \succ a_2 \succ \dots$ hep farklı elemanlardan oluşuyor (tekrar etse $a_i \prec \dots \prec a_i$, ters simetri ve geçişlilikle çelişir). Küme sonlu, sonsuza kadar süremez; bir minimal elemanda duruyor. $\blacksquare$

Sonsuz kümede doğru değil: $(\mathbb{Z}, \le)$'de minimal eleman yok. Bu teorem bir sonraki bölümün algoritmasını mümkün kılıyor.

---

## 5. Topolojik sıralama

Bir projede dosyalar birbirine bağlı. Derleme sırası nasıl olmalı?

```
util.h  <- util.c, parse.c, main.c
parse.h <- parse.c, main.c
util.c, parse.c, main.c <- prog
```

"$u$, $v$'den önce hazır olmalı" bağıntısının geçişli kapanışı bir kısmi sıralama (döngü olmadığı sürece). İstediğimiz, bu kısmi sıralamaya **uyan** bir tam sıralama: her $u \prec v$ için $u$ listede $v$'den önce gelsin. Buna **topolojik sıralama** denir.

Bölüm 4'teki teorem bir algoritma veriyor: **minimal bir eleman seç, listeye ekle, kümeden çıkar, tekrarla.** Minimal eleman, bağımlılıklarının hepsi zaten listede olan eleman. Kalan küme hâlâ bir poset ve boş değilse yine minimal elemanı var. Bu, **Kahn algoritması**.

Bağımlılıkları Ders 6.6'daki gibi satır başına bir küme olarak tutuyoruz. "Bütün bağımlılıkları bitti mi?" sorusu Ders 6.5'teki alt küme testi:

```c
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

#define N 6

static const char *name[N] = {"util.h", "util.c", "parse.h", "parse.c", "main.c", "prog"};

// need[v]: v'den ONCE hazir olmasi gerekenler (v, bunlara bagli)
static uint32_t need[N];

static void depends(int v, int u) { need[v] |= (uint32_t)1 << u; }

// Kahn: bagimliliklari biten bir dugumu sec, cikar, tekrarla
static bool topo_sort(int *order) {
    uint32_t done = 0;
    for (int i = 0; i < N; i++) {
        int pick = -1;
        for (int v = 0; v < N; v++) {
            bool ready = !((done >> v) & 1) && (need[v] & ~done) == 0;
            if (ready) { pick = v; break; }
        }
        if (pick < 0) return false;   // hazir dugum yok: dongu var
        order[i] = pick;
        done |= (uint32_t)1 << pick;
    }
    return true;
}

int main(void) {
    depends(1, 0);              // util.c   <- util.h
    depends(3, 2);              // parse.c  <- parse.h
    depends(3, 0);              // parse.c  <- util.h
    depends(4, 0);              // main.c   <- util.h
    depends(4, 2);              // main.c   <- parse.h
    depends(5, 1);              // prog     <- util.c
    depends(5, 3);              // prog     <- parse.c
    depends(5, 4);              // prog     <- main.c

    int order[N];
    if (topo_sort(order)) {
        for (int i = 0; i < N; i++) printf("%s%s", name[order[i]], i + 1 < N ? " -> " : "\n");
    }
    depends(0, 5);              // util.h <- prog: dongu
    if (!topo_sort(order)) printf("dongu var, siralama yok\n");
    return 0;
}
```

```
util.h -> util.c -> parse.h -> parse.c -> main.c -> prog
dongu var, siralama yok
```

`(need[v] & ~done) == 0`: "$v$'nin bağımlılıklarından bitmemiş olan yok", yani $\text{need}[v] \subseteq \text{done}$. Ve hazır bir düğüm bulunamazsa, kalan düğümlerin hiçbiri minimal değil demek; Bölüm 4'teki teoreme göre bu ancak sıralama bir poset değilse, yani **döngü** varsa olabilir. Algoritma hem sıralıyor hem döngüyü algılıyor.

Topolojik sıralama **tek değil**: `util.h -> parse.h -> util.c -> ...` de geçerli bir sıra. Her adımda birden çok minimal eleman olabilir ve hangisini seçtiğin önemsiz. Make bu serbestliği `make -j` ile kullanıyor: aynı anda hazır olan dosyaları paralel derliyor.

Bu algoritma her turda bütün düğümleri gezdiği için $N^2$ adım; Faz 9'da her düğüme bekleyen bağımlılık sayısını tutarak bunu düğüm + kenar sayısına indireceğiz. Topolojik sıralama derleyicide de sürekli karşımıza çıkacak: Faz 16'da temel blokları, Faz 17'de modülleri, komut zamanlamada (Ders 7.21) birbirine bağımlı komutları sıralamak için.

---

## Alıştırmalar

**1** – 30'un bölenleri $\{1, 2, 3, 5, 6, 10, 15, 30\}$ için Hasse diyagramını çiz. Hangi tanıdık şekle benziyor? Neden? (İpucu: $30 = 2 \cdot 3 \cdot 5$.)

**2** – $\{2, 3, 4, 5, 6, 8, 9\}$ kümesi bölünebilirliğe göre. Minimal elemanları, maksimal elemanları, varsa en küçük ve en büyük elemanı bul.

**3** – `bool is_partial_order(const rel R)`'yi Ders 6.6'daki fonksiyonlarla yaz. $(\{0, \dots, 5\}, \le)$ ve $(\{1, \dots, 6\}, \mid)$ için dene (ikinci için elemanları $x - 1$ olarak kaydır).

**4** – Bir posetin **bütün** topolojik sıralamalarını yazdıran bir program yaz (her adımda her hazır düğümü dene, özyinelemeyle). Bölüm 5'teki örnekte kaç tane var?

**5** – Kahn algoritmasının döngüyü algılaması, Bölüm 4'teki teoremin karşıt tersi. Bunu açıkça yaz: "sonlu, boş olmayan ve döngüsüz ise minimal eleman var" teoreminin karşıt tersi ne söylüyor?

<details>
<summary>Cevaplar</summary>

**1** –

```
          30
        / |  \
      6  10   15
      | X  X  |
      2   3   5
        \ | /
          1
```

$6 = 2 \cdot 3$, $10 = 2 \cdot 5$, $15 = 3 \cdot 5$; her kenar bir asal çarpan ekliyor. Bu, Bölüm 3'teki **küp**, $\mathcal{P}(\{2, 3, 5\})$'in Hasse diyagramıyla aynı: her bölen, hangi asalları içerdiğiyle bir alt kümeye karşılık geliyor ($6 \leftrightarrow \{2, 3\}$), ve bölmek alt küme olmak. İki poset arasındaki bu birebir eşleşmeye **izomorfizm** denir; Ders 6.21'de gruplar için de göreceğiz.

**2** – Minimal: $2, 3, 5$ (kümede onları bölen başka eleman yok). Maksimal: $5, 6, 8, 9$ (kümede onlara bölünen başka eleman yok; $5$ hem minimal hem maksimal, kimseyle karşılaştırılamıyor). En küçük yok (2, 3'ü bölmüyor). En büyük yok (8, 9'u bölmüyor).

**3** –

```c
bool is_partial_order(const rel R) {
    return reflexive(R) && antisymmetric(R) && transitive(R);
}

static bool divides(int a, int b) { return (b + 1) % (a + 1) == 0; }   // eleman x, x+1'i temsil ediyor
```

İkisi için de `1` dönüyor. Bölünebilirlikte ters simetri pozitif tamsayılarda doğru; tamsayılarda ($-2 \mid 2$ ve $2 \mid -2$) bozulurdu.

**4** –

```c
static int order[N];

static int all_topo(uint32_t done, int depth) {
    if (depth == N) {
        for (int i = 0; i < N; i++) printf("%s ", name[order[i]]);
        printf("\n");
        return 1;
    }
    int count = 0;
    for (int v = 0; v < N; v++) {
        if (!((done >> v) & 1) && (need[v] & ~done) == 0) {
            order[depth] = v;
            count += all_topo(done | (uint32_t)1 << v, depth + 1);
        }
    }
    return count;
}
// all_topo(0, 0)
```

Örnekte 14 sıralama var. Elle sayalım; `prog` hep en sonda, dolayısıyla ilk beş yere bakıyoruz. İlk dosya bir başlık olmalı. *`util.h` ilkse*: kalan dört dosyada tek kısıt `parse.h`'ın `parse.c` ve `main.c`'den önce gelmesi; dört dosyanın $4! = 24$ dizilişinin, `parse.h`'ın bu üçlünün başında olduğu üçte biri: 8. *`parse.h` ilkse*: `util.c`, `parse.c` ve `main.c`'nin üçü de `util.h`'ı beklediği için ikinci dosya `util.h` olmak zorunda, kalan üçü serbest: $3! = 6$. Toplam $8 + 6 = 14$.

**5** – Teorem: "döngüsüz $\land$ sonlu $\land$ boş değil $\to$ minimal eleman var". Karşıt tersi: "minimal eleman yok $\to$ (döngü var $\lor$ sonsuz $\lor$ boş)". Kahn'da kalan küme sonlu ve (henüz bitmediği için) boş değil; geriye tek seçenek kalıyor: döngü var. Algoritmanın `return false` satırı, bu karşıt tersin koddaki hali.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §9.6: kısmi sıralamalar, Hasse diyagramı, topolojik sıralama.
- Brian Davey & Hilary Priestley, *Introduction to Lattices and Order* (2. baskı), Bölüm 1: sıralı kümeler.
- Arthur Kahn, "Topological sorting of large networks", *Communications of the ACM* 5(11), 1962.

**Sıradaki ders:** Kafes teorisi. Her iki elemanın bir "en küçük üstü" ve "en büyük altı" olduğu posetler, ve derleyicinin veri akışı analizinin dayandığı sabit nokta teoremi.
