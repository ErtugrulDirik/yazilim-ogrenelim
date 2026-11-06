---
title: "8.8 İkili arama ağacı"
description: "İkili arama ağacı değişmezi (solda küçükler, sağda büyükler) ve içek gezinmenin sıralı çıktı vermesi; arama, pointer'a pointer ile özyinelemesiz ekleme ve üç durumlu silme (yaprak, tek çocuk, iki çocukta ardılla değiştirme) adım adım çizimle; aynı 100 000 anahtarı karışık sırayla eklemek 0.028 s ve yükseklik 39, sıralı eklemek 25.8 s ve yükseklik 99 999: ağacın dejenere listeye dönmesi; ortalama derinlik 2 ln n ve dengeli ağaç ihtiyacı."
---

Ders 4.2'deki ikili arama sıralı bir dizide $O(\log n)$'de arıyordu, ama diziye eleman eklemek $O(n)$'di (her şeyi kaydırmak gerekiyor; Ders 8.1'deki sıralı küme). Ders 8.2'deki listeye eklemek $O(1)$'di ama aramak $O(n)$. **İkili arama ağacı** (BST, binary search tree) ikisinin iyi tarafını almaya çalışıyor: ikili aramanın "ortadaki elemana bak, yarısını at" fikrini, pointer'larla bağlı düğümlerin ucuz eklemesiyle birleştiriyor. Bu ders BST'nin üç işlemini yazıyor, sonra bu fikrin nerede çöktüğünü ölçüyor. O çöküş, sonraki üç dersin (AVL, kırmızı-siyah, B-ağacı) var olma sebebi.

---

## 1. Değişmez

Bir ikili ağaç (Ders 8.7), şu koşul **her düğüm için** sağlanıyorsa ikili arama ağacıdır:

> Sol alt ağaçtaki **bütün** anahtarlar düğümün anahtarından küçük, sağ alt ağaçtakilerin hepsi büyük.

```
              50
           /      \
         30        70
        /  \      /  \
      20    40  60    80
           /  \   \
         35   45   65
```

"Bütün" kelimesi önemli: 45, 30'un sağında olduğu için 30'dan büyük olmalı, ama aynı zamanda 50'nin solunda olduğu için 50'den de küçük olmalı. Sadece ebeveyn-çocuk çiftlerini kontrol etmek yetmez (Alıştırma 3).

Değişmezin iki sonucu var:

- **Arama**: kökten başla; aradığın küçükse sola, büyükse sağa git. Her adımda bir alt ağacı tamamen atıyorsun. Bir dizideki ikili aramanın "ortası" burada kök.
- **İçek gezinme sıralı verir**: önce sol (küçükler), sonra kök, sonra sağ (büyükler). Bunu tümevarımla görmek kolay: alt ağaçların içek gezinmeleri sıralıysa, "küçükler + kök + büyükler" de sıralı.

Bu ders boyunca anahtarlar tekrarsız `int`'ler (bir küme; Ders 8.1). Anahtarla birlikte bir değer saklamak (sözlük, map) düğüme bir alan eklemekten ibaret.

---

## 2. Arayüz ve arama

```c
/* bst.h: ikili arama agaci (anahtar: int) */
#ifndef BST_H
#define BST_H
#include <stdbool.h>

typedef struct Dugum {
    int anahtar;
    struct Dugum *sol, *sag;
} Dugum;

Dugum *bst_ara(Dugum *kok, int x);
bool   bst_ekle(Dugum **kok, int x);      /* zaten varsa false */
bool   bst_sil(Dugum **kok, int x);       /* yoksa false */
int    bst_yukseklik(const Dugum *kok);
void   bst_icek(const Dugum *kok);
void   bst_ciz(const Dugum *kok, int girinti);
void   bst_serbest(Dugum *kok);
#endif
```

(Ders 8.1'in opak tipini burada bilerek kullanmıyoruz: alıştırmalarda düğümlere doğrudan bakmak istiyoruz.)

```c
/* bst.c: ozyinelemesiz ekleme/silme, pointer'a pointer ile (Ders 8.2) */
#include "bst.h"
#include <stdio.h>
#include <stdlib.h>

Dugum *bst_ara(Dugum *n, int x) {
    while (n && n->anahtar != x)
        n = x < n->anahtar ? n->sol : n->sag;
    return n;
}
```

Arama kuyruk özyinelemeli bir tanım, o yüzden doğrudan döngü yazdık (Ders 8.6). Maliyeti, kökten bulunan düğüme (ya da düştüğümüz `NULL`'a) kadar olan yolun uzunluğu: en kötü durumda ağacın **yüksekliği** $h$. Bütün mesele $h$'nin ne kadar olduğu.

---

## 3. Ekleme

Yeni anahtar her zaman bir **yaprak** olarak eklenir: arama yap, düştüğün `NULL`'ın yerine yeni düğümü koy. "`NULL`'ın yeri" kök pointer'ı, bir düğümün `sol`'u ya da `sag`'ı olabilir; Ders 8.2'deki pointer'a pointer tekniği bu üçünü tek bir durum yapıyor:

```c
bool bst_ekle(Dugum **p, int x) {
    while (*p) {                                  /* p: "bu dugumu gosteren pointer"in adresi */
        if (x == (*p)->anahtar) return false;
        p = x < (*p)->anahtar ? &(*p)->sol : &(*p)->sag;
    }
    Dugum *n = malloc(sizeof *n);
    if (!n) return false;
    n->anahtar = x; n->sol = n->sag = NULL;
    *p = n;                                       /* bos yere as: kok, sol ya da sag, fark etmez */
    return true;
}
```

Döngü bittiğinde `p`, değeri `NULL` olan bir pointer'ın adresi. Ona yazmak yeni düğümü ağaca bağlıyor. Boş ağaçta `p`, çağıranın `kok` değişkeninin adresi; ilk eklemede `kok` güncelleniyor. Bunun için `bst_ekle(&kok, x)` çağrısında `&` var.

---

## 4. Silme

Silme, BST'nin tek zor işlemi. Silinecek düğüm `n` olsun; üç durum var:

1. **Yaprak**: onu gösteren pointer'ı `NULL` yap.
2. **Tek çocuk**: onu gösteren pointer'ı çocuğuna yönlendir. Çocuğun alt ağacı bütünüyle bir seviye yukarı çıkıyor; değişmez korunuyor, çünkü o alt ağaç zaten `n`'nin ebeveynine göre doğru taraftaydı.
3. **İki çocuk**: `n`'yi doğrudan çıkaramayız; iki alt ağacı tek bir pointer'a bağlayamayız. Bunun yerine `n`'nin yerine konabilecek bir anahtar bulunur: `n`'den büyük **en küçük** anahtar, yani **ardıl** (successor). Ardıl, sağ alt ağacın en solundaki düğüm. Onun anahtarı `n`'ye kopyalanır, sonra ardıl düğüm silinir. Ardılın sol çocuğu olamaz (olsaydı o daha küçük olurdu), bu yüzden onu silmek durum 1 ya da 2.

Ardıl neden doğru seçim? `n`'nin yerine geçecek anahtar, soldakilerin hepsinden büyük ve sağdakilerin hepsinden küçük olmalı. Ardıl sağ alt ağaçtan geldiği için soldakilerin hepsinden büyük; sağ alt ağacın en küçüğü olduğu için de sağdakilerin geri kalanından küçük. (Simetrik olarak **öncül**, yani sol alt ağacın en büyüğü de olur.)

```c
bool bst_sil(Dugum **p, int x) {
    while (*p && (*p)->anahtar != x)
        p = x < (*p)->anahtar ? &(*p)->sol : &(*p)->sag;
    Dugum *n = *p;
    if (!n) return false;
    if (n->sol && n->sag) {                       /* iki cocuk: ardili (sag alt agacin en kucugu) bul */
        Dugum **q = &n->sag;
        while ((*q)->sol) q = &(*q)->sol;
        Dugum *ardil = *q;
        n->anahtar = ardil->anahtar;              /* ardilin anahtarini buraya tasi... */
        *q = ardil->sag;                          /* ...ardili yerinden sok (sol cocugu yok) */
        free(ardil);
    } else {                                      /* 0 ya da 1 cocuk: tek cocugu yerine koy */
        *p = n->sol ? n->sol : n->sag;
        free(n);
    }
    return true;
}
```

Durum 1 ve 2 tek satır: `*p = n->sol ? n->sol : n->sag`. Yaprakta ikisi de `NULL`, sonuç `NULL`. Ardılı bulmak için de pointer'a pointer (`q`) kullanıyoruz, çünkü ardılı yerinden "sökerken" onu gösteren pointer'ı değiştirmemiz gerekiyor.

Adım adım:

```c
int main(void) {
    Dugum *kok = NULL;
    int girdi[] = { 50, 30, 70, 20, 40, 60, 80, 35, 45, 65 };
    for (int i = 0; i < 10; i++) bst_ekle(&kok, girdi[i]);
    printf("icek:"); bst_icek(kok); printf("\n");
    bst_ciz(kok, 2);
    printf("ara 45: %s, ara 55: %s\n", bst_ara(kok, 45) ? "var" : "yok", bst_ara(kok, 55) ? "var" : "yok");

    bst_sil(&kok, 35);  printf("\nsil 35 (yaprak):\n");        bst_ciz(kok, 2);
    bst_sil(&kok, 60);  printf("\nsil 60 (tek cocuk):\n");     bst_ciz(kok, 2);
    bst_sil(&kok, 30);  printf("\nsil 30 (iki cocuk):\n");     bst_ciz(kok, 2);
    bst_sil(&kok, 50);  printf("\nsil 50 (kok):\n");           bst_ciz(kok, 2);
    printf("icek:"); bst_icek(kok); printf("\n");
    bst_serbest(kok);
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c bst.c -o deneme && ./deneme
icek: 20 30 35 40 45 50 60 65 70 80
          80
      70
              65
          60
  50
              45
          40
              35
      30
          20
ara 45: var, ara 55: yok

sil 35 (yaprak):
          80
      70
              65
          60
  50
              45
          40
      30
          20

sil 60 (tek cocuk):
          80
      70
          65
  50
              45
          40
      30
          20

sil 30 (iki cocuk):
          80
      70
          65
  50
          45
      40
          20

sil 50 (kok):
          80
      70
  65
          45
      40
          20
icek: 20 40 45 65 70 80
```

(Çizim yana yatık, Ders 8.7: kök solda, sağ alt ağaç üstte.)

- `sil 60`: 60'ın tek çocuğu 65 bir seviye yukarı çıkıp 70'in sol çocuğu oldu.
- `sil 30`: iki çocuklu. Ardıl, sağ alt ağacın (40, 45) en solu: 40. 30'un yerine 40 yazıldı, eski 40 düğümü sökülüp yerine sağ çocuğu 45 kondu.
- `sil 50`: kökün ardılı 65 (sağ alt ağacın en solu). Kök değişti ama `kok` değişkenine dokunmadık: düğüm aynı, içindeki anahtar değişti.

Her silmeden sonra içek gezinme hâlâ sıralı. Üç işlemin üçü de kökten bir yol boyunca iniyor: $O(h)$.

---

## 5. Yükseklik her şey

$O(h)$ ne demek? Ders 8.7'nin Alıştırma 3'ü: $n$ düğümlü bir ikili ağacın yüksekliği en az $\lfloor \log_2 n \rfloor$. En fazla ise $n - 1$: her düğümün tek çocuğu olduğunda ağaç bir **listedir**. BST'nin şekli tamamen **ekleme sırasına** bağlı. Aynı 0..n−1 anahtarlarını iki sırayla ekleyelim: sıralı ve karışık (Fisher–Yates, Ders 6.29).

```c
/* Ayni anahtarlar, iki ekleme sirasi: karisik ve sirali */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "bst.h"

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

static long derinlik_toplami(const Dugum *n, long d) {
    return n ? d + derinlik_toplami(n->sol, d + 1) + derinlik_toplami(n->sag, d + 1) : 0;
}

static void dene(const char *ad, const int *a, int n) {
    Dugum *kok = NULL;
    double t0 = simdi();
    for (int i = 0; i < n; i++) bst_ekle(&kok, a[i]);
    for (int i = 0; i < n; i++) if (!bst_ara(kok, a[i])) abort();
    double sn = simdi() - t0;
    int h = bst_yukseklik(kok);
    printf("  %-8s n=%6d  yukseklik=%6d  ort. derinlik=%8.1f  %.3f s\n",
           ad, n, h, (double)derinlik_toplami(kok, 0) / n, sn);
    bst_serbest(kok);
}

int main(void) {
    for (int n = 1000; n <= 100000; n *= 10) {
        int *a = malloc(n * sizeof *a);
        for (int i = 0; i < n; i++) a[i] = i;
        dene("sirali", a, n);
        srand(42);
        for (int i = n - 1; i > 0; i--) { int j = rand() % (i + 1), t = a[i]; a[i] = a[j]; a[j] = t; }
        dene("karisik", a, n);
        printf("  log2(n)=%.1f  2 ln n=%.1f\n", log2(n), 2 * log(n));
        free(a);
    }
    return 0;
}
```

```
$ cc -std=c11 -O2 -Wall dejenere.c bst.c -o dejenere && ./dejenere
  sirali   n=  1000  yukseklik=   999  ort. derinlik=   499.5  0.004 s
  karisik  n=  1000  yukseklik=    21  ort. derinlik=    11.0  0.000 s
  log2(n)=10.0  2 ln n=13.8
  sirali   n= 10000  yukseklik=  9999  ort. derinlik=  4999.5  0.310 s
  karisik  n= 10000  yukseklik=    32  ort. derinlik=    15.1  0.001 s
  log2(n)=13.3  2 ln n=18.4
  sirali   n=100000  yukseklik= 99999  ort. derinlik= 49999.5  25.759 s
  karisik  n=100000  yukseklik=    39  ort. derinlik=    20.2  0.028 s
  log2(n)=16.6  2 ln n=23.0
```

100 000 anahtarda fark **900 kat**: 0.028 s'ye karşı 25.8 s. Sıralı eklemede her yeni anahtar hepsinden büyük, hep en sağa gidiyor; ağaç sağa doğru uzanan bir liste ve $i$. ekleme $i$ adım sürüyor. Toplam $\sum i = n(n-1)/2$ adım: $O(n^2)$. $n$ 10 katına çıkınca süre 80–100 kat artıyor, karesel büyümenin imzası. Bu sefer liste kötü yerleşimli de: her adım bir pointer takibi ve düğümler belleğe dağılmış (Ders 8.2'nin ölçümü).

Karışık sırada yükseklik $\log_2 n$'nin yaklaşık 2.3 katı, ortalama derinlik ise $2 \ln n$'ye yakın. Bu bir tesadüf değil: rastgele sırayla kurulan bir BST'de bir düğümün beklenen derinliği yaklaşık $2 \ln n \approx 1.39 \log_2 n$. Sebebi Ders 9.5'teki hızlı sıralamayla aynı: kök, rastgele bir **pivot**; ağacı iki parçaya bölüyor, ve rastgele bir pivot ortalamada "yeterince iyi" bölüyor. (Kesin formül $2(1 + 1/n)H_n - 4 \approx 2 \ln n - 2.85$; $n = 10^5$ için 20.2, ölçümle aynı.)

Ama gerçek veri rastgele değil. Sıralı ya da neredeyse sıralı veri çok sık: artan kimlik numaraları, zaman damgaları, alfabetik isim listeleri, zaten sıralı bir dosyanın yeniden yüklenmesi. Ve bir saldırgan girdiyi kendisi seçebiliyorsa en kötü durumu bilerek üretir. Bu yüzden düz BST pratikte nadiren kullanılır. Çözüm, her ekleme ve silmeden sonra ağacı **yeniden dengeleyip** yüksekliği $O(\log n)$'de tutmak:

| Yapı | Ders | Garanti | Fikir |
| --- | --- | --- | --- |
| AVL ağacı | 8.9 | $h \le 1.44 \log_2 n$ | Her düğümde iki alt ağacın yükseklik farkı en fazla 1; bozulunca **dönme** |
| Kırmızı-siyah ağaç | 8.10 | $h \le 2 \log_2 (n+1)$ | Daha gevşek kural, daha az dönme |
| B-ağacı | 8.11 | $h \approx \log_B n$ | Düğüm başına çok anahtar; disk ve cache için |
| Skip list | 8.20 | Beklenen $O(\log n)$ | Ağaç değil, rastgelelikle dengelenen liste |

---

## Alıştırmalar

**1** – `taban(kok, x)`: `x`'ten küçük ya da eşit **en büyük** anahtarı döndür (yoksa `NULL`). Bölüm 4'teki ilk ağaçta (10 anahtar) `taban(55)`, `taban(50)`, `taban(19)`, `taban(100)` ne olmalı? Neden tek bir kök-yaprak yolunda bulunabilir?

**2** – `[a, b]` aralığındaki anahtarları sayan bir fonksiyon yaz; aralığın tamamen dışında kalan alt ağaçlara hiç inmesin. Aynı ağaçta `[35, 65]` için sonuç?

**3** – Bir ağacın BST olup olmadığını denetleyen şu fonksiyon yanlış. Neden? Doğrusunu yaz ve iki fonksiyonu, Bölüm 4'teki ağaçta 45'i 55 yaparak bozduğun bir ağaçta karşılaştır.

```c
static bool gecerli_yanlis(const Dugum *n) {
    if (!n) return true;
    if (n->sol && n->sol->anahtar >= n->anahtar) return false;
    if (n->sag && n->sag->anahtar <= n->anahtar) return false;
    return gecerli_yanlis(n->sol) && gecerli_yanlis(n->sag);
}
```

**4** – 1, 2, 3 anahtarlarının 6 farklı ekleme sırası var. Kaç farklı ağaç şekli çıkıyor, ve hangileri dengeli? Genel olarak $n$ anahtarla kaç farklı BST şekli kurulabilir?

**5** – Elinde **sıralı** bir dizi var ve ondan BST kurmak istiyorsun. Sıralı eklemenin dejenere ağaç ürettiğini gördük. Diziyi karıştırmadan, en düşük yükseklikli ağacı $O(n)$'de kuran bir fonksiyon yaz. 100 000 eleman için yükseklik ne çıkar?

<details>
<summary>Cevaplar</summary>

**1** –

```c
static const Dugum *taban(const Dugum *n, int x) {   /* x'ten kucuk ya da esit en buyuk */
    const Dugum *aday = NULL;
    while (n) { if (n->anahtar == x) return n;
        if (n->anahtar < x) { aday = n; n = n->sag; } else n = n->sol; }
    return aday;
}
```

```
taban(55) = 50
taban(50) = 50
taban(19) = yok
taban(100) = 80
```

Bir düğümün anahtarı `x`'ten küçükse o bir **aday**; ama sağ alt ağacında `x`'e daha yakın bir anahtar olabilir, o yüzden sağa devam. Büyükse o ve sağ alt ağacının tamamı elenir, sola git. Her adımda bir alt ağaç atılıyor, bu yüzden tek bir yol yeterli: $O(h)$. Simetrik `tavan` (`x`'ten büyük ya da eşit en küçük) aynı şekilde yazılır. Sıralı bir dizide bunu yapan, Ders 9.2'deki "alt sınır" ikili araması; bir hash tablosunda (Ders 8.14) bu işlem **yok**. "Sıralı" yapıların hash'e üstünlüğü bu tür sorgular.

**2** –

```c
static int aralik(const Dugum *n, int a, int b) {
    if (!n) return 0;
    if (n->anahtar < a) return aralik(n->sag, a, b);
    if (n->anahtar > b) return aralik(n->sol, a, b);
    return 1 + aralik(n->sol, a, b) + aralik(n->sag, a, b);
}
```

```
[35, 65] araliginda 6 anahtar
```

(35, 40, 45, 50, 60, 65.) Anahtar `a`'dan küçükse sol alt ağaç tamamen aralık dışı, sadece sağa bakılıyor; `b`'den büyükse tersi. Maliyet $O(h + k)$; $k$, aralıktaki anahtar sayısı. Veritabanlarındaki `WHERE fiyat BETWEEN 35 AND 65` sorgusu, bir B-ağacı (Ders 8.11) üzerinde aynı şeyi yapıyor.

**3** – Yanlış fonksiyon sadece **ebeveyn-çocuk** çiftlerine bakıyor. 45'i 55 yapınca 55, ebeveyni 40'ın sağında olduğu için o kontrolü geçiyor; ama 50'nin **sol** alt ağacında ve 50'den büyük. Arama 55'i asla bulamaz (50'de sağa gider). Doğru fonksiyon, her alt ağaca anahtarlarının içinde olması gereken **aralığı** taşır:

```c
static bool gecerli(const Dugum *n, long alt, long ust) {  /* butun anahtarlar (alt, ust) araliginda */
    if (!n) return true;
    if (n->anahtar <= alt || n->anahtar >= ust) return false;
    return gecerli(n->sol, alt, n->anahtar) && gecerli(n->sag, n->anahtar, ust);
}
```

```
gecerli: 1 1
bozuk agac: yanlis=1 dogru=0
```

İlk çağrı `gecerli(kok, LONG_MIN, LONG_MAX)`. Sınırları `long` almak, `int`'in en küçük ve en büyük değerlerinin de anahtar olabilmesi için. Başka bir doğru yol: içek gezinme yapıp her anahtarın bir öncekinden büyük olduğunu kontrol etmek (Bölüm 1'deki "içek sıralı verir" özelliğinin tersi de doğru).

**4** –

```
123 -> (.(.(..))) (yukseklik 2)
132 -> (.((..).)) (yukseklik 2)
213 -> ((..)(..)) (yukseklik 1)
231 -> ((..)(..)) (yukseklik 1)
312 -> ((.(..)).) (yukseklik 2)
321 -> (((..).).) (yukseklik 2)
```

(Gösterim: `(sol sağ)`, `.` boş ağaç.) 5 farklı şekil; sadece 2 ile başlayan iki sıra dengeli ağacı veriyor, çünkü kök her zaman ilk eklenen anahtar. Genel sayı **Catalan sayısı** $C_n = \frac{1}{n+1}\binom{2n}{n}$: 1, 1, 2, 5, 14, 42... Kökü $k$. anahtar seçince sol alt ağaçta $k - 1$, sağda $n - k$ anahtar kalıyor, buradan $C_n = \sum_{k=1}^{n} C_{k-1} C_{n-k}$ (Ders 6.16'da üreteç fonksiyonuyla çözdüğümüz bağıntı). Şekillerin hepsi eşit olasılıklı değil: $n!$ sıranın 2'si dengeli ağaca, ama 4'ü dört ayrı "zincir" şekline gidiyor.

**5** – Sıralı dizinin **ortasını** kök yap, sol yarıdan sol alt ağacı, sağ yarıdan sağ alt ağacı özyinelemeyle kur:

```c
static Dugum *diziden(const int *a, int lo, int hi) {      /* [lo, hi) */
    if (lo >= hi) return NULL;
    int orta = lo + (hi - lo) / 2;
    Dugum *n = malloc(sizeof *n);
    n->anahtar = a[orta];
    n->sol = diziden(a, lo, orta);
    n->sag = diziden(a, orta + 1, hi);
    return n;
}
```

```
n=100000 yukseklik=16
```

$\lfloor \log_2 100\,000 \rfloor = 16$: mümkün olan en düşük yükseklik. Her eleman bir kez işleniyor, $O(n)$; özyineleme derinliği $\log_2 n$, yığın için güvenli (Ders 8.6). Bu kurulan ağaç, ikili aramanın her adımda baktığı "orta" elemanların ağacı: ikili arama ile BST'nin aynı şey olduğunun en net gösterimi. Ama bu dengeyi **sonraki** eklemeler yine bozar; bu yüzden dinamik veri için Ders 8.9'daki kendini dengeleyen ağaçlar gerekiyor.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 12: ikili arama ağaçları; 12.4 rastgele kurulan ağacın beklenen yüksekliği.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.2.2: ağaç araması, ortalama yol uzunluğu analizi ve silme.
- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 12.5–12.9.
- Thomas Hibbard, "Some Combinatorial Properties of Certain Trees With Applications to Searching and Sorting", *Journal of the ACM* 9(1), 1962: ardılla silme yönteminin ilk analizi.

**Sıradaki ders:** AVL ağacı. Dönmeler, denge faktörü ve yüksekliğin $O(\log n)$ olduğunun ispatı.
