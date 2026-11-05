---
title: "8.3 Çift yönlü ve dairesel liste"
description: "Her düğümün öncekini de bilmesi; dairesel yapı ve gözcü (sentinel) düğüm sayesinde bütün NULL ve baş/son özel durumlarının ortadan kalkması; tek bir araya_ekle ile başa ve sona O(1) ekleme, elindeki düğümü O(1) çıkarma; Linux çekirdeğindeki gömülü (intrusive) liste: list_head, offsetof ve container_of ile bir alanın adresinden onu içeren struct'a geri dönmek, bir nesnenin aynı anda iki listede bulunması; Josephus problemi ve LRU önbelleği alıştırmaları."
---

Ders 8.2'nin son alıştırmasında tek yönlü listenin bir sınırına çarptık: bir düğümü silmek için ondan **önceki** düğüme ihtiyaç var, ve oraya ancak baştan yürüyerek gidilebiliyor. Kuyruk pointer'ı eklemek sona eklemeyi hızlandırdı ama sondan silmeyi hızlandırmadı, üstüne de her fonksiyonda güncellenmesi gereken bir pointer daha getirdi.

Bu ders iki fikri birleştiriyor: her düğüme bir **geri** ok eklemek (çift yönlü liste), ve listeyi bir **halka** yapıp ortasına değer taşımayan bir **gözcü** düğüm koymak. Sonuç şaşırtıcı derecede basit: dört satırlık tek bir ekleme fonksiyonu, hiç `if`'siz. Sonra aynı yapının Linux çekirdeğinde nasıl kullanıldığını göreceğiz: listenin düğümü verinin **içinde**.

---

## 1. Çift yönlü düğüm ve dairesellik

```c
typedef struct Dugum {
    int deger;
    struct Dugum *onceki, *sonraki;
} Dugum;
```

Her düğüm hem sonrakini hem öncekini biliyor: liste iki yönde de gezilebilir, ve elinde bir düğüm varsa komşularına $O(1)$'de ulaşırsın. Bedeli düğüm başına bir pointer daha (8 bayt) ve her işlemde güncellenecek iki kat ok.

Tek yönlü listede `NULL` iki uçta da "burada bitiyor" anlamına geliyordu, ve her fonksiyon onu ayrıca kontrol etmek zorundaydı: baş boş mu, son düğümde miyiz? **Dairesel** listede son düğümün `sonraki`'si ilk düğümü, ilk düğümün `onceki`'si son düğümü gösterir; hiç `NULL` yok. Ama boş liste hâlâ bir özel durum (hiç düğüm yok, kim kimi gösterecek?).

## 2. Gözcü düğüm

Çözüm: listeye **her zaman** bir düğüm koymak, değer taşımayan bir **gözcü** (sentinel, ya da "kukla", dummy). Gözcü halkanın bir parçası; hem "başın öncesi" hem "sonun sonrası". 

```
bos liste:                    dolu liste (0 1 2 3):

  +--------+                  +------------------------------------------------+
  |  +---+ |                  |  +---+     +---+     +---+     +---+     +---+ |
  +->| G |-+                  +->| G |<--->| 0 |<--->| 1 |<--->| 2 |<--->| 3 |-+
     +---+                       +---+     +---+     +---+     +---+     +---+
  G.onceki = G.sonraki = G       G.sonraki = ilk (0),  G.onceki = son (3)
```

Artık her düğümün, gözcü dahil, **her zaman** bir öncekisi ve bir sonrakisi var. Boş liste "gözcü kendini gösteriyor" demek. Bu tek değişmez bütün özel durumları siliyor:

```c
/* Cift yonlu, dairesel, gozcu dugumlu liste */
#include <stdio.h>
#include <stdlib.h>

typedef struct Dugum {
    int deger;
    struct Dugum *onceki, *sonraki;
} Dugum;

/* Gozcu (sentinel): deger tasimayan, listenin hem basi hem sonu olan dugum.
   Bos liste: gozcu kendini gosterir. */
static void liste_kur(Dugum *g) { g->onceki = g->sonraki = g; }

/* x'i a ile b'nin arasina koy (a->sonraki == b). Bos/dolu, bas/son ayrimi YOK. */
static void araya_ekle(Dugum *x, Dugum *a, Dugum *b) {
    x->onceki = a;
    x->sonraki = b;
    a->sonraki = x;
    b->onceki = x;
}

static void basa_ekle(Dugum *g, Dugum *x) { araya_ekle(x, g, g->sonraki); }
static void sona_ekle(Dugum *g, Dugum *x) { araya_ekle(x, g->onceki, g); }   /* O(1)! */

/* Elinde dugum varsa listeyi bilmeden O(1) cikar */
static void cikar(Dugum *x) {
    x->onceki->sonraki = x->sonraki;
    x->sonraki->onceki = x->onceki;
    x->onceki = x->sonraki = x;           /* kendine baglanmis: "hicbir listede degil" */
}

static Dugum *yeni(int v) { Dugum *d = malloc(sizeof *d); d->deger = v; liste_kur(d); return d; }

static void yaz(const char *ad, const Dugum *g) {
    printf("%-12s ileri:", ad);
    for (const Dugum *d = g->sonraki; d != g; d = d->sonraki) printf(" %d", d->deger);
    printf("   geri:");
    for (const Dugum *d = g->onceki; d != g; d = d->onceki) printf(" %d", d->deger);
    printf("\n");
}

int main(void) {
    Dugum g;                               /* gozcu yiginda, veri dugumleri heap'te */
    liste_kur(&g);
    yaz("bos", &g);
    for (int i = 1; i <= 3; i++) sona_ekle(&g, yeni(i));
    basa_ekle(&g, yeni(0));
    yaz("0 1 2 3", &g);
    Dugum *iki = g.sonraki->sonraki->sonraki;   /* deger 2 */
    cikar(iki);  free(iki);
    yaz("2 cikti", &g);
    Dugum *bas = g.sonraki;
    cikar(bas);  free(bas);
    yaz("bas cikti", &g);
    while (g.sonraki != &g) { Dugum *d = g.sonraki; cikar(d); free(d); }
    yaz("bosaltildi", &g);
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined cift.c -o cift && ./cift
bos          ileri:   geri:
0 1 2 3      ileri: 0 1 2 3   geri: 3 2 1 0
2 cikti      ileri: 0 1 3   geri: 3 1 0
bas cikti    ileri: 1 3   geri: 3 1
bosaltildi   ileri:   geri:
```

Bütün yapının kalbi `araya_ekle`: `x`'i `a` ile `b`'nin arasına koyan dört atama. **Hiç `if` yok.** Çünkü:

- Başa eklemek "gözcü ile ilk düğümün arasına" eklemek: `araya_ekle(x, g, g->sonraki)`.
- Sona eklemek "son düğüm ile gözcünün arasına": `araya_ekle(x, g->onceki, g)`. Son düğüme `g->onceki` ile $O(1)$'de ulaşılıyor; kuyruk pointer'ına gerek yok, çünkü **gözcünün geri oku zaten kuyruk pointer'ı**.
- Liste boşsa `g->sonraki` ve `g->onceki` gözcünün kendisi: `araya_ekle(x, g, g)`, ve dört atama yine doğru sonucu veriyor (`x` gözcüyle iki yönde bağlı, iki düğümlü bir halka).

`cikar` da aynı: `x`'in iki komşusunu birbirine bağla. `x` ilk mi, son mu, tek mi? Fark etmiyor; komşulardan biri ya da ikisi gözcüyse onlar da güncelleniyor. Ve en önemlisi, `cikar` **listeyi** (gözcüyü) almıyor bile: elinde bir düğüm pointer'ı varsa, hangi listede olduğunu bilmeden $O(1)$'de çıkarabilirsin. Çıkarılan düğümü kendine bağlamak (`x->onceki = x->sonraki = x`) onu "hiçbir listede değil" durumuna getiriyor; aynı düğümü yanlışlıkla iki kez çıkarmak zararsız oluyor.

Gezinme de özel durumsuz: `for (d = g->sonraki; d != g; d = d->sonraki)`, "gözcüye dönene kadar". Geri yönde `onceki` ile aynı.

Gözcü fikri sadece listelere özgü değil: Ders 4.13'teki `strlen` dizinin sonundaki `'\0'`'a, bir tür gözcüye güveniyor. Ders 8.10'daki kırmızı-siyah ağaçta da bütün `NULL` yaprakları tek bir gözcü düğümle değiştirmek kodu ciddi biçimde sadeleştiriyor.

| İşlem | Tek yönlü (8.2) | Çift yönlü + gözcü |
| --- | --- | --- |
| Başa ekleme | $O(1)$ | $O(1)$ |
| Sona ekleme | $O(n)$ | $O(1)$ |
| Baştan çıkarma | $O(1)$ | $O(1)$ |
| Sondan çıkarma | $O(n)$ | $O(1)$ |
| Elindeki düğümü çıkarma | $O(n)$ (öncekini bul) | $O(1)$ |
| Elindeki düğümden önceye ekleme | $O(n)$ | $O(1)$ |
| Düğüm başına pointer | 1 | 2 |

---

## 3. Gömülü liste: Linux'un `list_head`'i

Şimdiye kadar düğüm **veriyi içeriyordu**: `Dugum` içinde `int deger`. Gerçek programlarda veri bir `int` değil, büyük bir `struct`: bir süreç, bir dosya, bir ağ bağlantısı. Onu bir listeye koymak için ya düğüme bir pointer koyarsın (`void *veri`; her düğüm ayrı bir `malloc`, veriye ulaşmak iki pointer kovalamak), ya da tam tersini yaparsın: **düğümü verinin içine koy**.

Linux çekirdeği ikincisini yapar. Bağlantı yapısı veri hakkında hiçbir şey bilmez:

```c
typedef struct ListeBasi {
    struct ListeBasi *onceki, *sonraki;
} ListeBasi;
```

(Çekirdekte adı `struct list_head`, alanları `prev`, `next`.) Listeye girecek her `struct` bu yapıdan bir **alan** taşır. Liste fonksiyonları sadece `ListeBasi`'larla çalışır, Bölüm 2'dekilerin aynısı ama `deger`'siz. Bu tür listeye **gömülü** (intrusive) liste denir: bağlantı bilgisi nesnenin içine gömülü.

Peki listede gezerken elimize bir `ListeBasi *` geçiyor; bize lazım olan onu içeren `struct`. Geri dönüş yolu **`container_of`**:

```c
#define container_of(ptr, tip, alan) ((tip *)((char *)(ptr) - offsetof(tip, alan)))
```

`offsetof(tip, alan)` (`<stddef.h>`) bir alanın struct'ın başından kaç bayt ötede olduğunu derleme anında verir (Ders 4.25–4.26'daki yerleşim). Alanın adresinden bu ofseti çıkarırsan struct'ın başlangıç adresini bulursun. `char *`'a çevirme şart: pointer aritmetiği bayt cinsinden yapılsın diye (Ders 4.6).

Asıl güç şurada: bir nesne birden fazla `ListeBasi` alanı taşıyıp **aynı anda birden fazla listede** olabilir, ve bunun için tek bir ek `malloc` gerekmez:

```c
/* Linux cekirdegi tarzi gomulu (intrusive) liste: list_head + container_of */
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>

typedef struct ListeBasi {
    struct ListeBasi *onceki, *sonraki;
} ListeBasi;

static void liste_kur(ListeBasi *g) { g->onceki = g->sonraki = g; }
static void araya_ekle(ListeBasi *x, ListeBasi *a, ListeBasi *b) {
    x->onceki = a; x->sonraki = b; a->sonraki = x; b->onceki = x;
}
static void sona_ekle(ListeBasi *g, ListeBasi *x) { araya_ekle(x, g->onceki, g); }
static void cikar(ListeBasi *x) {
    x->onceki->sonraki = x->sonraki;
    x->sonraki->onceki = x->onceki;
    liste_kur(x);
}
static int bos_mu(const ListeBasi *g) { return g->sonraki == g; }

/* Bir alanin adresinden, onu iceren struct'in adresini bul */
#define container_of(ptr, tip, alan) ((tip *)((char *)(ptr) - offsetof(tip, alan)))

/* Listedeki her struct'i gez. (Cekirdekteki list_for_each_entry'nin tip parametreli hali) */
#define liste_her(pos, gozcu, tip, alan)                          \
    for (tip *pos = container_of((gozcu)->sonraki, tip, alan);    \
         &pos->alan != (gozcu);                                   \
         pos = container_of(pos->alan.sonraki, tip, alan))

/* Ayni anda IKI listede olan bir nesne: hic ek malloc yok */
typedef struct Gorev {
    int no;
    const char *ad;
    ListeBasi tum;      /* butun gorevler listesindeki baglanti */
    ListeBasi hazir;    /* calismaya hazir gorevler listesindeki baglanti */
} Gorev;

int main(void) {
    ListeBasi tum_gorevler, hazir_kuyruk;
    liste_kur(&tum_gorevler);
    liste_kur(&hazir_kuyruk);

    const char *adlar[] = { "derle", "test", "paketle", "yukle" };
    Gorev *g[4];
    for (int i = 0; i < 4; i++) {
        g[i] = malloc(sizeof *g[i]);
        g[i]->no = i + 1;
        g[i]->ad = adlar[i];
        liste_kur(&g[i]->hazir);
        sona_ekle(&tum_gorevler, &g[i]->tum);
    }
    sona_ekle(&hazir_kuyruk, &g[0]->hazir);    /* sadece 1 ve 3 hazir */
    sona_ekle(&hazir_kuyruk, &g[2]->hazir);

    printf("offsetof(Gorev, tum) = %zu, offsetof(Gorev, hazir) = %zu, sizeof(Gorev) = %zu\n",
           offsetof(Gorev, tum), offsetof(Gorev, hazir), sizeof(Gorev));
    printf("g[2] = %p, &g[2]->hazir = %p, container_of geri = %p\n",
           (void *)g[2], (void *)&g[2]->hazir, (void *)container_of(&g[2]->hazir, Gorev, hazir));

    printf("tum:  ");  liste_her(p, &tum_gorevler, Gorev, tum)  printf(" %d:%s", p->no, p->ad);
    printf("\nhazir:");  liste_her(p, &hazir_kuyruk, Gorev, hazir) printf(" %d:%s", p->no, p->ad);
    printf("\n");

    cikar(&g[0]->hazir);                      /* 1 calisti, kuyruktan cikti; tum listesinde duruyor */
    sona_ekle(&hazir_kuyruk, &g[3]->hazir);
    printf("sonra hazir:");  liste_her(p, &hazir_kuyruk, Gorev, hazir) printf(" %d:%s", p->no, p->ad);
    printf("\n");

    while (!bos_mu(&tum_gorevler)) {
        Gorev *x = container_of(tum_gorevler.sonraki, Gorev, tum);
        cikar(&x->tum);
        cikar(&x->hazir);                     /* kendine bagliysa zararsiz */
        free(x);
    }
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined gomulu.c -o gomulu && ./gomulu
offsetof(Gorev, tum) = 16, offsetof(Gorev, hazir) = 32, sizeof(Gorev) = 48
g[2] = 0x604000000490, &g[2]->hazir = 0x6040000004b0, container_of geri = 0x604000000490
tum:   1:derle 2:test 3:paketle 4:yukle
hazir: 1:derle 3:paketle
sonra hazir: 3:paketle 4:yukle
```

Yerleşim: `no` (4 bayt) + dolgu (4) + `ad` (8) = 16, sonra `tum` (16 bayt), sonra `hazir` (16 bayt): toplam 48 (Ders 4.26). `&g[2]->hazir` struct'ın başından `0x4b0 − 0x490 = 0x20 = 32` bayt ötede; `container_of` 32 çıkarıp tam struct'ın başını buldu.

`Gorev`'ler hem "tüm görevler" hem "hazır kuyruk" listesinde. 1. görev çalışıp hazır kuyruktan çıkınca (`cikar(&g[0]->hazir)`), "tüm" listesindeki yeri etkilenmedi; hiçbir şey ayrılmadı, kopyalanmadı. Linux'ta bir süreç (`task_struct`) bu şekilde onlarca listede birden durur: bütün süreçler, ebeveyninin çocukları, bir bekleme kuyruğu, ...

`liste_her` makrosu çekirdeğin `list_for_each_entry`'sinin karşılığı. Çekirdeğinki tipi `typeof` (GCC uzantısı, C23'te standart) ile kendisi bulur; biz C11'de kaldığımız için tipi parametre olarak verdik. Döngü, gözcünün kendisine de `container_of` uyguluyor: gözcü bir `Gorev` içinde olmadığı için çıkan adres anlamsız, ama hiç **erişilmiyor**, sadece `&pos->alan != gozcu` karşılaştırmasında kullanılıp döngü bitiyor. Bu, C standardının katı okumasına göre gri bir bölge (nesnenin dışına pointer aritmetiği); çekirdek ve bütün büyük derleyiciler buna güveniyor.

### Gömülü listenin artıları ve eksileri

- **Artı:** düğüm başına ayrı `malloc` yok, veriye ulaşmak için ikinci bir pointer kovalanmıyor (Ders 8.2'deki 80 ns'lik adımların yarısı), bir nesne birçok listede olabiliyor, liste kodu tek bir kez yazılıp her tip için kullanılıyor (Ders 8.23).
- **Eksi:** nesnenin tipi, hangi listelerde olabileceğini **önceden** bilmeli (her liste için bir alan). Nesnenin ömrü listenin değil senin sorumluluğun: listede duran bir nesneyi `free` edersen komşuları serbest bırakılmış belleği gösterir.

---

## Alıştırmalar

**1** – **Josephus problemi:** $n$ kişi bir çember oluşturuyor; 1'den başlayarak saymaya başla ve her $k$'ıncı kişiyi ele, çember tek kişi kalana dek. Dairesel liste ve gözcüyle $n = 7$, $k = 3$ için eleme sırasını ve son kalanı bul. Gözcüyü sayarken atlamayı unutma.

**2** – Bölüm 2'deki listeye `void ters_cevir(Dugum *g)` ekle. Çift yönlü dairesel listede ters çevirmek, Ders 8.2'dekinden çok daha basit: her düğümün (gözcü dahil) iki pointer'ını **takas** etmek yeter. Neden?

**3** – **LRU önbelleği** (least recently used, Ders 7.25): kapasitesi 3 olan bir önbellek; erişilen anahtar varsa listenin başına taşınır (isabet), yoksa başa eklenir ve önbellek doluysa **sondaki** (en uzun süredir kullanılmayan) atılır (ıska). `1, 2, 3, 1, 4, 2, 5` erişim dizisini çift yönlü listeyle simüle et. Hangi işlemler $O(1)$, hangisi değil ve onu nasıl $O(1)$ yaparsın?

**4** – `cikar`'dan sonra düğümü kendine bağlamak yerine `onceki` ve `sonraki`'yi `NULL` yapsaydık, aynı düğümü yanlışlıkla iki kez `cikar` etmek ne yapardı? Linux çekirdeği `list_del`'de bu pointer'lara özel "zehirli" (poison) değerler (`0xdead000000000100` gibi) yazar. Neden `NULL` değil?

**5** – `container_of(&x->hazir, Gorev, tum)` gibi yanlış alan adıyla çağırırsan ne olur? Derleyici bunu yakalar mı?

<details>
<summary>Cevaplar</summary>

**1** –

```c
static int josephus(int n, int k) {
    Dugum g; kur(&g);
    for (int i = 1; i <= n; i++) { Dugum *d = malloc(sizeof *d); d->deger = i; sona(&g, d); }
    Dugum *p = &g;
    printf("elenen:");
    while (g.sonraki->sonraki != &g) {             /* birden fazla kisi var */
        for (int s = 0; s < k; s++) { p = p->sonraki; if (p == &g) p = p->sonraki; }
        Dugum *ol = p; p = p->onceki;
        printf(" %d", ol->deger);
        cikar(ol); free(ol);
    }
    int kalan = g.sonraki->deger; free(g.sonraki);
    printf("\n");
    return kalan;
}
```

```
elenen: 3 6 2 7 5 1
son kalan: 4
```

Elenen düğümü çıkarmadan önce `p`'yi bir geriye almak önemli: sayma bir sonraki kişiden devam etmeli. Gözcü sayılmamalı (`if (p == &g) p = p->sonraki`). Her eleme $O(k)$, toplam $O(nk)$. (Josephus'un kapalı bir özyinelemeli formülü de var: $J(1) = 0$, $J(n) = (J(n-1) + k) \bmod n$, 0 tabanlı; $J(7) = 3$, yani 4. kişi.)

**2** – Çift yönlü dairesel listede "ters çevirmek", her okun anlamını değiştirmek demek: eskiden "sonraki" olan artık "önceki". Her düğümde iki pointer'ı takas edersen (gözcü dahil, böylece `g->sonraki` eski son düğüm olur), yapının değişmezi korunur ve ileri gezinme eski geri gezinmeyi verir:

```c
static void ters_cevir(Dugum *g) {
    Dugum *d = g;
    do {
        Dugum *t = d->sonraki; d->sonraki = d->onceki; d->onceki = t;
        d = d->onceki;            /* takastan sonra "eski sonraki" artik onceki'de */
    } while (d != g);
}
```

Ders 8.2'deki gibi "devamı kaybetme" sorunu yok, çünkü her düğüm devamını iki yönde de tutuyor.

**3** – Simülasyon:

```
1: iska  [1]
2: iska  [2 1]
3: iska  [3 2 1]
1: isabet  [1 3 2]
4: iska, 2 atildi  [4 1 3]
2: iska, 3 atildi  [2 4 1]
5: iska, 1 atildi  [5 2 4]
```

`1`'e tekrar erişilince başa taşındı; bu yüzden `4` geldiğinde atılan `1` değil, en eski `2` oldu. Başa taşıma (`cikar` + `basa_ekle`) ve sondan atma (`g->onceki`) **$O(1)$**: çift yönlü liste olmadan sondakini atmak ve ortadakini taşımak $O(n)$ olurdu. $O(n)$ kalan tek iş, anahtarın listede **aranması**. Gerçek LRU önbellekleri bir hash tablosu (Ders 8.14) ile "anahtar → düğüm pointer'ı" eşlemesini de tutar: arama $O(1)$, ve bütün işlem $O(1)$. Hash tablosu + çift yönlü liste, LRU'nun klasik uygulaması.

**4** – `NULL` olsaydı ikinci `cikar`, `x->onceki->sonraki`'de `NULL`'dan alan okumaya çalışıp çökerdi (sayfa 0, Ders 7.28): hata hemen görünür, ama hata mesajı "NULL pointer" der ve gerçek sebebi (çift çıkarma) gizler. Linux'un zehirli değerleri bilerek **tanınabilir** ve **eşlenmemiş** adresler: erişim yine sayfa hatası verir, ama çökme raporunda `0xdead000000000100` gören bir geliştirici hemen "silinmiş bir liste düğümüne erişildi" der. Bizim "kendine bağla" yaklaşımımız ise ikinci `cikar`'ı zararsız yapıyor; hangisinin seçileceği, hatayı **gizlemek mi yakalamak mı** istediğine bağlı.

**5** – Derleyici yakalamaz: `container_of` sadece bir pointer aritmetiği, ve `offsetof(Gorev, tum)` geçerli bir alan. `&x->hazir`'den `tum`'un ofseti (16) çıkarılır, sonuç struct'ın başından 16 bayt **ötede** bir adres, `Gorev *` gibi kullanılınca alanlar kaymış okunur: `no` yerine `tum`'un içindeki pointer'ın baytları. Sessiz bellek bozulması. Linux'un `container_of`'u bu yüzden `typeof` ile bir tip kontrolü de yapar (`ptr`'nin tipinin `tip`'in `alan` alanının tipiyle aynı olmasını ister), ama iki alan aynı tipteyse (burada ikisi de `ListeBasi`) o kontrol de yakalayamaz. Gömülü listelerin bedeli: tip güvenliği programcının disiplininde.

</details>

---

## Kaynaklar

- Linux çekirdeği, `include/linux/list.h`: `list_head`, `list_add`, `list_del`, `list_for_each_entry`, `container_of` (bu dersteki kodun modeli).
- Robert Love, *Linux Kernel Development* (3. baskı), Bölüm 6: çekirdek veri yapıları, bağlı liste.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 10.2: bağlı listeler ve gözcüler.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 2.2.4–2.2.5: dairesel ve çift bağlı listeler.

**Sıradaki ders:** Yığın (stack). Dizi ve liste ile, parantez denetleyici, postfix ifade hesaplayıcı.
