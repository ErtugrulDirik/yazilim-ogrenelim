---
title: "8.10 Kırmızı-siyah ağaç"
description: "Linux çekirdeğinin, C++ std::map'in ve Java TreeMap'in kullandığı dengeli ağaç: beş renk kuralı ve bunlardan çıkan h ≤ 2 log₂(n+1) sınırı; ebeveyn pointer'lı düğüm, yeni düğümü kırmızı eklemek ve tek ihlali (kırmızı-kırmızı) amca kırmızıysa yeniden boyama, değilse bir ya da iki dönmeyle düzeltmek; kırmızı düğümleri siyah ebeveyniyle birleştirince ağacın bir 2-3-4 ağacına dönüştüğünü programla göstermek; 1 milyon sıralı anahtarda yükseklik 36 ama ortalama derinlik 18.3, AVL'den daha az dönme ve daha hızlı karışık ekleme."
---

Ders 8.9'daki AVL ağacı yüksekliği sıkı tutuyordu: mükemmel ağaçtan en fazla %44 yüksek. Bunun bedeli, değişikliklerde biraz fazla iş. **Kırmızı-siyah ağaç** daha gevşek bir denge kuralına razı oluyor (mükemmelin en fazla 2 katı) ve karşılığında ekleme ve silmede daha az yeniden yapılanma istiyor: silme dahil her işlemde en fazla 3 dönme. Bu takas o kadar iyi ki pratikte en yaygın dengeli ağaç o oldu: Linux çekirdeğinde (işlem zamanlayıcı, sanal bellek alanları, dosya sistemleri), C++'ın `std::map` ve `std::set`'inde, Java'nın `TreeMap`'inde.

Kuralları ilk okuyuşta keyfi görünür. Dersin ikinci yarısı, onların aslında daha basit bir yapının, **2-3-4 ağacının**, ikili ağaç olarak kodlanması olduğunu gösteriyor. O noktadan sonra kurallar kendiliğinden anlam kazanıyor.

---

## 1. Kurallar

Her düğümün bir rengi var: kırmızı ya da siyah. `NULL` çocuklar (boş alt ağaçlar) siyah **yaprak** sayılır.

1. Her düğüm kırmızı ya da siyah.
2. Kök siyah.
3. `NULL` yapraklar siyah.
4. **Kırmızı bir düğümün iki çocuğu da siyah**: arka arkaya iki kırmızı yok.
5. **Her düğümden aşağıdaki bütün `NULL` yapraklara giden yollarda aynı sayıda siyah düğüm var.** Bu sayıya o düğümün **siyah yüksekliği** denir.

Kural 5 dengenin kendisi: siyah düğümler açısından ağaç **mükemmel** dengeli. Kural 4 de kırmızıların bu dengeyi en fazla ne kadar bozabileceğini sınırlıyor.

### Yükseklik sınırı

Kökten bir yaprağa giden en uzun yol, kırmızı ve siyahların sırayla dizildiği yol; en kısa yol, sadece siyahlardan oluşan yol. Kural 4 yüzünden bir yolun en az yarısı siyah. Kökün siyah yüksekliği $b$ ise (`NULL` sayılmadan) ağacın yüksekliği $h \le 2b$.

Öte yandan siyah yüksekliği $b$ olan bir alt ağaçta en az $2^b - 1$ düğüm var: sadece siyahları sayarsan kökten her yaprağa en az $b$ siyah var, yani siyahların oluşturduğu ağaç $b$ seviyeye kadar dolu. (Tümevarımla: iki çocuğun her birinin siyah yüksekliği en az $b - 1$, dolayısıyla en az $2 \cdot (2^{b-1} - 1) + 1 = 2^b - 1$.) O halde $n \ge 2^b - 1 \ge 2^{h/2} - 1$, buradan

$$
h \le 2 \log_2(n + 1).
$$

AVL'nin $1.44 \log_2 n$'inden gevşek, ama yine $O(\log n)$.

---

## 2. Düğüm ve dönme

Bu sefer düğümde **ebeveyn pointer'ı** da var. Ders 8.9'da dengelemeyi özyinelemenin dönüşünde yapmıştık; burada ekleme döngüyle yapılıyor ve düzeltme yukarı doğru yürüyor. Ebeveyn pointer'ı bu yukarı yürüyüşü ve Ders 8.7'de sözünü ettiğimiz yığınsız yineleyiciyi mümkün kılıyor: bir düğümün ardılı, sağ alt ağacı varsa onun en solu; yoksa, sol çocuğu olduğumuz ilk ataya kadar yukarı çıkmak. Bedeli düğüm başına bir pointer daha ve her bağlantı değişikliğinde onu da güncellemek.

```c
/* Kirmizi-siyah agac: ekleme (CLRS 13.3), ebeveyn pointer'li */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum { KIRMIZI, SIYAH } Renk;

typedef struct Dugum {
    int anahtar;
    Renk renk;
    struct Dugum *sol, *sag, *ebeveyn;
} Dugum;

typedef struct { Dugum *kok; long donme, boyama; } Agac;

static bool kirmizi(const Dugum *n) { return n && n->renk == KIRMIZI; }   /* NULL yapraklar siyah */

/* x'in yerine y'yi koy: x'i gosteren pointer'i (kok, ebeveynin solu ya da sagi) y'ye cevir */
static void yerine_koy(Agac *t, Dugum *x, Dugum *y) {
    if (!x->ebeveyn)                 t->kok = y;
    else if (x == x->ebeveyn->sol)   x->ebeveyn->sol = y;
    else                             x->ebeveyn->sag = y;
    if (y) y->ebeveyn = x->ebeveyn;
}

static void sola_don(Agac *t, Dugum *x) {
    Dugum *y = x->sag;
    x->sag = y->sol;
    if (y->sol) y->sol->ebeveyn = x;
    yerine_koy(t, x, y);
    y->sol = x;
    x->ebeveyn = y;
    t->donme++;
}

static void saga_don(Agac *t, Dugum *y) {
    Dugum *x = y->sol;
    y->sol = x->sag;
    if (x->sag) x->sag->ebeveyn = y;
    yerine_koy(t, y, x);
    x->sag = y;
    y->ebeveyn = x;
    t->donme++;
}
```

Dönmenin kendisi Ders 8.9'dakiyle aynı (Bölüm 2'deki çizim); farklı olan, üç ebeveyn pointer'ını da düzeltmek ve yeni alt ağaç kökünü döndürmek yerine onu doğrudan ebeveyne bağlamak (`yerine_koy`). `kirmizi(NULL) == false` kuralı her yerde `NULL` kontrolünden kurtarıyor; CLRS aynı işi bütün `NULL`'ların yerine tek bir siyah **gözcü** düğüm koyarak yapıyor (Ders 8.3).

---

## 3. Ekleme

Yeni anahtarı Ders 8.8'deki gibi bir yaprak olarak ekle ve **kırmızı** boya. Neden kırmızı? Siyah eklesek o yoldaki siyah sayısı bir artar ve kural 5 **her yerde** bozulur; düzeltmesi zor. Kırmızı eklemek kural 5'i hiç bozmuyor. Bozulabilecek tek kural 4: ebeveyn de kırmızıysa iki kırmızı arka arkaya geliyor. (Ya da ağaç boştu ve kırmızı bir kök oluştu; kökü siyaha boyamak yeter.)

```c
bool rb_ekle(Agac *t, int x) {
    Dugum **p = &t->kok, *ebeveyn = NULL;
    while (*p) {
        if (x == (*p)->anahtar) return false;
        ebeveyn = *p;
        p = x < (*p)->anahtar ? &(*p)->sol : &(*p)->sag;
    }
    Dugum *z = malloc(sizeof *z);
    z->anahtar = x; z->renk = KIRMIZI; z->sol = z->sag = NULL; z->ebeveyn = ebeveyn;
    *p = z;
    ekleme_duzelt(t, z);
    return true;
}
```

### Düzeltme

`z` kırmızı ve ebeveyni `e` de kırmızı. `e` kırmızı olduğu için kök olamaz (kök siyah), yani bir büyük ebeveyn `b` var ve `b` siyah (kural 4 eklemeden önce sağlanıyordu). Belirleyici olan, `e`'nin kardeşi, yani `z`'nin **amcası**. (Aşağıda `e`, `b`'nin sol çocuğu; sağ çocuğuysa her şeyin aynası.)

**Durum 1: amca kırmızı.** Dönme yok, sadece boya: `e` ve amcayı siyah, `b`'yi kırmızı yap.

```
        b(S)                  b(K)   ← şimdi b ile onun ebeveyni çakışabilir
       /    \                /    \
    e(K)    a(K)    ──►   e(S)    a(S)
     |                     |
    z(K)                  z(K)
```

`b`'nin altındaki her yolda siyah sayısı değişmedi (bir siyah aşağı indi, `b`'den kırmızıya döndü, her yolda bir siyah var). Ama `b` artık kırmızı ve ebeveyni de kırmızıysa aynı sorun **iki seviye yukarıda** tekrar ortaya çıktı. `z = b` yapıp döngüye devam. Köke ulaşırsa kökü siyaha boyamak bitiriyor.

**Durum 2 ve 3: amca siyah.** Boyamak işe yaramaz (amcayı siyah yapamayız, zaten siyah). Dönme gerekiyor; AVL'deki gibi, `z`'nin ebeveynine ve büyük ebeveynine göre konumu bir **çizgi** ya da **üçgen** oluşturuyor:

```
 Durum 3 (çizgi): b'de sağa dön, e'yi siyah, b'yi kırmızı boya

          b(S)                 e(S)
         /    \               /    \
      e(K)    a(S)   ──►    z(K)   b(K)
      /                               \
    z(K)                              a(S)

 Durum 2 (üçgen): z sağda; önce e'de sola dön, durum 3'e dönüşür
```

Durum 3'ten sonra alt ağacın kökü siyah (`e`), yani yukarıyla çakışma yok: **düzeltme biter**. Durum 2'de `e`'de bir dönme `z` ile `e`'nin rollerini değiştirip çizgi oluşturuyor; sonra durum 3. Ekleme başına en fazla 2 dönme.

```c
/* Yeni dugum kirmizi eklenir; tek olasi ihlal "kirmizi ebeveynin kirmizi cocugu". */
static void ekleme_duzelt(Agac *t, Dugum *z) {
    while (kirmizi(z->ebeveyn)) {
        Dugum *e = z->ebeveyn, *b = e->ebeveyn;           /* ebeveyn kirmizi => kok degil => buyukbaba var */
        bool solda = (e == b->sol);
        Dugum *amca = solda ? b->sag : b->sol;
        if (kirmizi(amca)) {                              /* durum 1: amca kirmizi -> yeniden boya, yukari cik */
            e->renk = amca->renk = SIYAH;
            b->renk = KIRMIZI;
            t->boyama++;
            z = b;
            continue;
        }
        if (z == (solda ? e->sag : e->sol)) {             /* durum 2: ucgen -> ebeveynde don, durum 3'e cevir */
            z = e;
            if (solda) sola_don(t, z); else saga_don(t, z);
            e = z->ebeveyn;
        }
        e->renk = SIYAH;                                  /* durum 3: cizgi -> buyukbabada don, boya */
        b->renk = KIRMIZI;
        if (solda) saga_don(t, b); else sola_don(t, b);
        break;
    }
    t->kok->renk = SIYAH;
}
```

`solda` bayrağı, ayna durumları ayrı ayrı yazmak yerine tek kodda topluyor. Durum 1 döngüde $O(\log n)$ kez tekrarlanabilir, ama sadece renk değiştiriyor ve her tekrarda iki seviye yukarı çıkıyor.

### Denetleyici

Ders 8.9'daki gibi, kod yazmadan önce denetleyici:

```c
/* Denetci: kok siyah, kirmizi-kirmizi yok, her yolda ayni sayida siyah. Siyah yuksekligi dondurur. */
static int denetle(const Dugum *n, long alt, long ust) {
    if (!n) return 1;                                     /* NULL yaprak: siyah, 1 sayilir */
    if (n->anahtar <= alt || n->anahtar >= ust) { puts("sira bozuk"); abort(); }
    if (n->sol && n->sol->ebeveyn != n) { puts("ebeveyn bozuk"); abort(); }
    if (n->sag && n->sag->ebeveyn != n) { puts("ebeveyn bozuk"); abort(); }
    if (kirmizi(n) && (kirmizi(n->sol) || kirmizi(n->sag))) { puts("kirmizi-kirmizi"); abort(); }
    int a = denetle(n->sol, alt, n->anahtar), b = denetle(n->sag, n->anahtar, ust);
    if (a != b) { puts("siyah yukseklik farkli"); abort(); }
    return a + (n->renk == SIYAH);
}
int rb_denetle(const Agac *t) {
    if (kirmizi(t->kok)) { puts("kok kirmizi"); abort(); }
    return denetle(t->kok, -2147483649L, 2147483648L);
}
```

(Döndürülen sayı kökten aşağı bir yoldaki siyah düğüm sayısı, `NULL` yaprak dahil.)

### İz sürme

```c
int main(void) {
    Agac t = { 0 };
    int g[] = { 10, 20, 30, 15, 25, 5, 1, 27, 28 };
    for (int i = 0; i < 9; i++) {
        long d = t.donme, b = t.boyama;
        rb_ekle(&t, g[i]);
        printf("ekle %d: %ld yeniden boyama, %ld donme, siyah yukseklik %d\n", g[i], t.boyama - b, t.donme - d, rb_denetle(&t));
    }
    rb_ciz(t.kok, 2);
    printf("2-3-4 gorunumu:\n"); rb_234(t.kok);
    rb_serbest(t.kok);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c rb.c -o deneme && ./deneme
ekle 10: 0 yeniden boyama, 0 donme, siyah yukseklik 2
ekle 20: 0 yeniden boyama, 0 donme, siyah yukseklik 2
ekle 30: 0 yeniden boyama, 1 donme, siyah yukseklik 2
ekle 15: 1 yeniden boyama, 0 donme, siyah yukseklik 3
ekle 25: 0 yeniden boyama, 0 donme, siyah yukseklik 3
ekle 5: 0 yeniden boyama, 0 donme, siyah yukseklik 3
ekle 1: 1 yeniden boyama, 0 donme, siyah yukseklik 3
ekle 27: 0 yeniden boyama, 2 donme, siyah yukseklik 3
ekle 28: 1 yeniden boyama, 0 donme, siyah yukseklik 3
            30
                 28(K)
       27(K)
            25
  20
            15
       10(K)
            5
                 1(K)
2-3-4 gorunumu:
  [10 20 27] 
  [1 5] [15] [25] [28 30]
```

(Çizim yana yatık, kök solda; `(K)` kırmızı, işaretsizler siyah.)

- `ekle 30`: 10 → 20 → 30 çizgisi, amca yok (`NULL`, siyah): durum 3, tek dönme. 20 kök oldu.
- `ekle 15`: 15 kırmızı, ebeveyni 10 kırmızı, amca 30 kırmızı: durum 1. 10 ve 30 siyah, 20 kırmızı oldu, sonra kök siyaha boyandı. Siyah yükseklik 2'den 3'e çıktı. **Ağacın siyah yüksekliği sadece böyle artıyor**: durum 1 köke kadar ulaştığında.
- `ekle 27`: o anda 30 siyah ve sol çocuğu 25 kırmızı. 27, 25'in **sağına** ekleniyor: `z = 27` ve `e = 25` kırmızı, `b = 30`, amca 30'un sağı yani `NULL` (siyah). `z` sağda, `e` solda: üçgen, durum 2. 25'te sola, 30'da sağa dönme; 27 siyah olup bu küçük alt ağacın köküne çıkıyor, 25 ve 30 onun kırmızı çocukları.
- `ekle 28`: 30'un soluna. Ebeveyn 30 kırmızı, amca 25 kırmızı: durum 1. 25 ve 30 siyaha, 27 kırmızıya boyandı; 27'nin ebeveyni 20 siyah olduğu için orada duruyor.

---

## 4. 2-3-4 ağacı

Kurallarla tek tek uğraşmak yerine bir adım geri çekilelim. Her siyah düğümü, kırmızı çocuklarıyla birlikte **tek bir büyük düğüm** gibi düşün:

```
     siyah + 0 kırmızı çocuk  →  1 anahtarlı, 2 çocuklu düğüm   [b]
     siyah + 1 kırmızı çocuk  →  2 anahtarlı, 3 çocuklu düğüm   [a b]
     siyah + 2 kırmızı çocuk  →  3 anahtarlı, 4 çocuklu düğüm   [a b c]
```

Kural 4 (iki kırmızı arka arkaya yok) bir büyük düğümün en fazla 3 anahtarlı olmasını garanti ediyor. Kural 5 (her yolda aynı sayıda siyah) bütün büyük düğüm yapraklarının **aynı derinlikte** olması demek. Bu iki özellik birlikte bir **2-3-4 ağacını** tanımlıyor: her düğümde 1, 2 ya da 3 anahtar (2, 3 ya da 4 çocuk) ve bütün yapraklar aynı seviyede. Mükemmel dengeli, çok yollu bir arama ağacı.

Bu görünümü yazdıran fonksiyon, siyah düğümleri seviye seviye geziyor ve kırmızı çocukları ebeveynleriyle aynı köşeli paranteze koyuyor:

```c
/* 2-3-4 gorunumu: siyah dugum + kirmizi cocuklari = tek bir "buyuk dugum" */
static void dugum234(const Dugum *n) {
    printf("[");
    if (kirmizi(n->sol)) printf("%d ", n->sol->anahtar);
    printf("%d", n->anahtar);
    if (kirmizi(n->sag)) printf(" %d", n->sag->anahtar);
    printf("]");
}
void rb_234(const Dugum *kok) {       /* seviye seviye: her seviyede siyah dugumler */
    const Dugum *seviye[64], *sonraki[64]; int n = 0, m;
    if (kok) seviye[n++] = kok;
    while (n) {
        printf("  ");
        m = 0;
        for (int i = 0; i < n; i++) {
            dugum234(seviye[i]); printf(" ");
            const Dugum *liste[4]; int k = 0;   /* kirmizi cocugun cocuklari bir alt seviyede */
            if (kirmizi(seviye[i]->sol)) { liste[k++] = seviye[i]->sol->sol; liste[k++] = seviye[i]->sol->sag; }
            else liste[k++] = seviye[i]->sol;
            if (kirmizi(seviye[i]->sag)) { liste[k++] = seviye[i]->sag->sol; liste[k++] = seviye[i]->sag->sag; }
            else liste[k++] = seviye[i]->sag;
            for (int j = 0; j < k; j++) if (liste[j]) sonraki[m++] = liste[j];
        }
        printf("\n");
        for (int i = 0; i < m; i++) seviye[i] = sonraki[i];
        n = m;
    }
}
```

Yukarıdaki çıktıda kırmızı-siyah ağaç (yükseklik 3, dört seviye) bir 2-3-4 ağacı olarak iki seviye: kök `[10 20 27]` ve dört yaprak `[1 5] [15] [25] [28 30]`. Her yaprak aynı derinlikte.

Şimdi ekleme durumları kendiliğinden anlaşılıyor. 2-3-4 ağacına ekleme her zaman bir yaprağa:

- Yaprakta yer varsa (1 ya da 2 anahtar) anahtar oraya girer. Kırmızı-siyahta bu, kırmızı bir düğümü siyah bir ebeveyne asmak (düzeltme yok) ya da durum 2/3'teki dönmeler: aynı büyük düğümün içindeki üç anahtarı "ortadaki siyah, kenarlar kırmızı" olacak şekilde yeniden dizmek.
- Yaprak **doluysa** (3 anahtar), 4 anahtara çıkar ve **bölünür**: ortadaki anahtar ebeveyne çıkar, kalanlar iki ayrı düğüm olur. Kırmızı-siyahta bu tam olarak **durum 1**: iki kırmızı çocuk siyaha, siyah ebeveyn kırmızıya döner. Kırmızıya dönen `b`, yukarıdaki büyük düğüme katılan anahtar. Orada da yer yoksa bölünme yukarı yayılıyor: durum 1'in yukarı doğru tekrarlanması.
- Bölünme köke kadar ulaşırsa yeni bir kök oluşuyor ve ağaç **yukarıdan** bir seviye büyüyor. Bütün yapraklar aynı anda bir seviye derine iniyor; denge hiç bozulmuyor. Kırmızı-siyahta: durum 1 köke ulaşıp kök siyaha boyanınca siyah yükseklik bir artıyor.

`ekle 15`'teki siyah yükseklik artışı buydu: kök `[10 20 30]` doluydu, 15 gelince bölündü, 20 yeni kök oldu.

Kırmızı-siyah ağaç, 2-3-4 ağacını **ikili ağaç düğümleriyle** temsil etmenin bir yolu. Neden doğrudan 2-3-4 ağacı yazmıyoruz? Değişken sayıda anahtarlı düğümler kodda can sıkıcı (her düğümde 3 anahtar ve 4 pointer'lık yer ayırıp çoğunu boş bırakmak) ve her düğümde küçük bir doğrusal arama gerekiyor. İkili gösterim her düğümü aynı boyutta tutuyor ve arama kodu Ders 8.8'deki düz BST aramasının **aynısı**: renkleri hiç okumuyor. Ders 8.11'deki B-ağacı ise tam tersini yapıyor: düğümleri büyük tutup bunu bir avantaja çeviriyor.

---

## 5. Ölçüm

AVL ile aynı deney (1 milyon anahtar, sıralı ve karışık):

```
$ cc -std=c11 -O2 -Wall olcum.c rb.c -o olcum -lm && ./olcum
n=1000000  2 log2(n+1)=39.9
  sirali   yukseklik=36  siyah yuk.=20  ort. derinlik=18.33  donme/ekleme=1.000  boyama/ekleme=1.000  ekleme 0.198 s  arama 0.079 s
  karisik  yukseklik=23  siyah yuk.=13  ort. derinlik=18.38  donme/ekleme=0.582  boyama/ekleme=0.514  ekleme 0.136 s  arama 0.131 s
```

Sanitizer'lı derleme de denetleyiciden temiz geçiyor. Aynı girdilerde AVL'nin ortalama derinlikleri 17.95 (sıralı) ve 18.30 (karışık).

| 1 milyon anahtar | AVL (8.9) | Kırmızı-siyah |
| --- | --- | --- |
| Yükseklik, sıralı | 19 | 36 |
| Yükseklik, karışık | 23 | 23 |
| Ortalama derinlik, karışık | 18.30 | 18.38 |
| Dönme / ekleme, karışık | 0.70 | 0.58 |
| Ekleme süresi, karışık | 0.251 s | 0.136 s |
| Düğüm boyutu | 24 bayt | 32 bayt (ebeveyn pointer'ı) |

- **Sıralı girdide** kırmızı-siyahın yüksekliği 36, AVL'nin neredeyse iki katı, ve $2 \log_2(n+1) = 39.9$ sınırına yakın. Ama **ortalama** derinlik sadece 18.3: ağacın en sol yolu 18 kenar ve tamamen siyah, en sağ yolu 36 kenar ve kırmızı-siyah sırayla (Alıştırma 5'teki programla ölçüldü). Sınır en kötü yol için; tipik arama çok daha kısa.
- **Karışık girdide** iki ağaç neredeyse aynı şekilde. Kırmızı-siyah daha az dönüyor ve ekleme **1.8 kat** daha hızlı. Farkın bir kısmı dönme sayısından, büyük kısmı ise döngüyle yazılmış eklemeden geliyor: AVL'de yoldaki **her** düğümde `dengele` (yükseklik güncellemesi) çalışıyor, kırmızı-siyahta düzeltme çoğu zaman ilk adımda bitiyor (ekleme başına ortalama 0.51 yeniden boyama).
- Arama süreleri benzer: arama ikisinde de renk ya da yüksekliğe bakmayan düz BST araması.

Ders 8.9'daki karar kuralı burada netleşiyor: okuma ağırlıklıysa AVL'nin sıkı dengesi biraz daha kısa yollar verir; yazma ağırlıklıysa (ya da genel amaçlı bir kütüphane yazıyorsan) kırmızı-siyah. Standart kütüphanelerin seçimi ikincisi.

**Silme** bu derste yok. Mantığı aynı (2-3-4 ağacında bir anahtar çıkarınca düğüm boşalırsa kardeşten ödünç almak ya da kardeşle birleşmek), ama kırmızı-siyah kodlaması dört simetrik durum çifti ve "çift siyah" adı verilen geçici bir ihlal içeriyor. CLRS Bölüm 13.4 ve Linux'un `lib/rbtree.c` dosyası iyi kaynaklar; ikincisi her durumu 2-3-4 ağacı çizimleriyle açıklayan yorumlarla dolu.

---

## Alıştırmalar

**1** – Bölüm 1'deki ispatta "siyah yüksekliği $b$ olan bir alt ağaçta en az $2^b - 1$ iç düğüm var" iddiasını tümevarımla tam olarak yaz. Kırmızı bir kökün çocuklarının siyah yüksekliği neden $b - 1$ değil de $b$?

**2** – 1'den 7'ye kadar anahtarları sırayla ekle. Kırmızı-siyah ağacı ve 2-3-4 görünümünü elle çiz, sonra programla karşılaştır. Aynı girdi AVL'de mükemmel bir ağaç vermişti (Ders 8.9); burada da mı?

**3** – Yeni düğümü kırmızı değil **siyah** eklesek hangi kural bozulur, ve onu düzeltmek neden daha zor?

**4** – Ders 8.9'daki AVL'de ekleme sonrası en fazla bir (tek ya da çift) dönme gerekiyordu, burada en fazla iki dönme. Ama durum 1 $O(\log n)$ kez tekrarlanabiliyor. Bir eklemenin **amortize** yeniden boyama sayısının $O(1)$ olduğu biliniyor; ölçüm (`boyama/ekleme`) bununla uyumlu mu?

**5** – Sıralı 1 milyon anahtarla kurulan ağaçta en soldaki ve en sağdaki yolun uzunluğunu ve en sağ yoldaki kırmızı düğüm sayısını ölç. Kurallar açısından açıkla.

<details>
<summary>Cevaplar</summary>

**1** – Siyah yüksekliği burada şöyle tanımlayalım: $b(x)$, `x`'ten aşağı herhangi bir `NULL`'a giden yolda, `x`'in **kendisi hariç**, `NULL` hariç siyah düğüm sayısı (kural 5 yüzünden her yolda aynı). İddia: `x` köklü alt ağaçta en az $2^{b(x)} - 1$ düğüm var. Temel: `x` bir yaprağın üstündeki `NULL` ise alt ağaç boş ve $b = 0$, $2^0 - 1 = 0$. Adım: `x`'in her çocuğu `c` için, `c` kırmızıysa $b(c) = b(x)$, siyahsa $b(c) = b(x) - 1$ (kendisi sayılmadığı için `x`'ten bakınca bir siyah eksiliyor); her iki durumda $b(c) \ge b(x) - 1$. Çocuk alt ağaçları daha kısa olduğu için tümevarım hipotezi uygulanıyor: her birinde en az $2^{b(x)-1} - 1$ düğüm. Toplam en az $2(2^{b(x)-1} - 1) + 1 = 2^{b(x)} - 1$. Kırmızı bir çocuğun siyah yüksekliği ebeveyninkiyle **aynı**, çünkü siyah yükseklik aşağıdaki siyahları sayıyor ve kırmızı düğüm yola siyah eklemiyor. (Güçlü tümevarım yükseklik üzerinde, Ders 6.4.) Bölüm 1'deki $b$, kökün bu tanımla siyah yüksekliği artı 1 (kök siyah); sınır değişmiyor.

**2** –

```
                 7(K)
            6
                 5(K)
       4(K)
            3
  2
       1
  [2 4] 
  [1] [3] [5 6 7] 
```

Mükemmel değil: yükseklik 3 (AVL'de 2). Ama 2-3-4 ağacı olarak mükemmel dengeli: iki seviye, bütün yapraklar aynı derinlikte. Sıralı ekleme her seferinde en sağdaki yaprağa ekliyor; o yaprak dolunca bölünüyor ve ortanca yukarı çıkıyor. Sonuçta sol taraf seyrek (`[1]`, `[3]`), sağ taraf dolu (`[5 6 7]`). Kırmızı-siyah ağaç bu 2-3-4 ağacının birebir kodlaması; dengesizlik görünüşte.

**3** – Kural 5: o yaprağa giden yolda siyah sayısı bir artar, ağacın geri kalanında artmaz. Bu, düğümün **bütün** atalarında siyah yüksekliği bozar ve düzeltmek için ağacın başka yerlerindeki yolları da değiştirmek gerekir. Kırmızı eklemenin bozabileceği tek kural 4, ve onun ihlali **yerel**: sadece yeni düğüm ile ebeveyni arasında. Yerel bir ihlali yerel hamlelerle (boyama, dönme) yukarı doğru itmek mümkün. 2-3-4 diliyle: yeni anahtar her zaman mevcut bir yaprak düğüme katılır (kırmızı); yeni bir seviye (siyah) sadece kökte, bölünmeyle oluşur.

**4** – Uyumlu: karışık girdide ekleme başına 0.51, sıralı girdide 1.00 yeniden boyama. Sıralı girdide bile sabit kalıyor; $n$'yle büyümüyor. Bunun nedeni 2-3-4 görünümünde bölünmelerin seyrekliği: bir düğüm bölündükten sonra iki yarısı da yarı dolu (birer anahtar) ve tekrar dolmaları için en az iki ekleme gerekiyor. Ders 4.24'teki dinamik dizi ikiye katlamasıyla aynı türden bir potansiyel argümanıyla, $n$ eklemede toplam bölünme (yani durum 1) sayısı $O(n)$.

**5** –

```c
static int sol_yol(const Dugum *n) { int d = -1; for (; n; n = n->sol) d++; return d; }
static int sag_yol(const Dugum *n) { int d = -1; for (; n; n = n->sag) d++; return d; }
static int sag_kirmizi(const Dugum *n) { int k = 0; for (; n; n = n->sag) k += n->renk == KIRMIZI; return k; }
```

```
sirali 1e6: en sol yol 18, en sag yol 36 (kirmizi 18), siyah yuk 20
```

En sol yol 19 düğüm (18 kenar), hepsi siyah. En sağ yol 37 düğüm: 19 siyah, 18 kırmızı, sırayla. İkisinde de `NULL` dahil 20 siyah var (kural 5). Kural 4'ün izin verdiği en uzun yol, kırmızı ve siyahın sırayla dizildiği yol; sıralı ekleme her seferinde en sağa eklediği için tam bu yolu üretiyor. Bölüm 1'deki $h \le 2b$ eşitsizliği burada neredeyse eşitlik. Sıralı girdi, kırmızı-siyah ağacın en kötü **şekli**; ama çoğu düğüm sol tarafta ve sığ, ortalama derinlik bu yüzden 18.3.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 13: kırmızı-siyah ağaçlar; ekleme (13.3) ve silme (13.4).
- Leonidas Guibas ve Robert Sedgewick, "A Dichromatic Framework for Balanced Trees", *FOCS* 1978: kırmızı-siyah ağaçların tanıtıldığı makale ve 2-3-4 ağaçlarıyla ilişki.
- Robert Sedgewick, "Left-leaning Red-Black Trees", 2008: 2-3 ağacına karşılık gelen, çok daha kısa bir varyant.
- Linux çekirdeği, `include/linux/rbtree.h` ve `lib/rbtree.c`: intrusive (Ders 8.3) kırmızı-siyah ağaç; rengi ebeveyn pointer'ının alt bitinde saklıyor.

**Sıradaki ders:** B-ağacı. Disk ve cache dostu ağaç, düğüm bölme.
