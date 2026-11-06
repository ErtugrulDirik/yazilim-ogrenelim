---
title: "8.9 AVL ağacı"
description: "Kendini dengeleyen ilk ağaç: her düğümde iki alt ağacın yükseklik farkı (denge faktörü) en fazla 1; sağa ve sola dönmenin içek sırayı koruduğu, dört dengesizlik durumu (sol-sol, sağ-sağ, sol-sağ, sağ-sol) ve çift dönme; ekleme ve silmede dönüş yolunda dengeleme; en az düğümlü AVL ağaçlarının Fibonacci bağıntısıyla h ≤ 1.44 log₂ n ispatı; 1 milyon sıralı anahtarda yükseklik 19 ve 0.14 s (düz BST'de yükseklik n − 1), denetleyiciyle 2 milyon rastgele işlem testi."
---

Ders 8.8'in sonunda gördük: ikili arama ağacının bütün işlemleri $O(h)$, ve $h$ ekleme sırasına göre $\log_2 n$ ile $n - 1$ arasında herhangi bir şey olabilir. Sıralı 100 000 anahtar 25 saniye sürdü. Bu derste ağacın yüksekliğini **her zaman** $O(\log n)$'de tutan ilk yapıyı yazıyoruz. 1962'de Georgy Adelson-Velsky ve Evgenii Landis tarafından yayımlandı; adı ikisinin baş harfleri. Fikir basit: ağaç bozulmaya başladığı anda, yerel ve $O(1)$ bir hamleyle düzelt.

---

## 1. Kural

> **AVL koşulu**: her düğümde, sol ve sağ alt ağaçların yükseklik farkı en fazla 1.

Bu farka **denge faktörü** denir: `denge(n) = yükseklik(sol) − yükseklik(sağ)`, ve her düğümde $-1$, $0$ ya da $+1$ olmalı. Kural "mükemmel dengeli" demiyor (bu çok pahalı olurdu); her düğümde **biraz** dengesizliğe izin veriyor. Bu gevşekliğin yine de $O(\log n)$ yükseklik garanti ettiğini Bölüm 5'te ispatlayacağız.

Denge faktörünü her seferinde hesaplamak $O(n)$ olurdu. Bunun yerine her düğüm kendi alt ağacının yüksekliğini saklıyor ve değişikliklerden sonra güncelliyor:

```c
/* AVL agaci: her dugumde yukseklik; ekleme ve silmeden sonra donmelerle denge */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

typedef struct Dugum {
    int anahtar;
    int yuk;                       /* bu dugumun alt agacinin yuksekligi; yaprak = 0 */
    struct Dugum *sol, *sag;
} Dugum;

static int  yuk(const Dugum *n) { return n ? n->yuk : -1; }
static int  maks(int a, int b) { return a > b ? a : b; }
static void guncelle(Dugum *n) { n->yuk = 1 + maks(yuk(n->sol), yuk(n->sag)); }
static int  denge(const Dugum *n) { return yuk(n->sol) - yuk(n->sag); }   /* +: sol agir */
```

`yuk(NULL) = -1` kuralı Ders 8.7'deki tercihle aynı, ve `guncelle` bu sayede yaprak için özel durum istemiyor.

---

## 2. Dönme

Dengeyi düzelten tek araç **dönme** (rotation): bir düğümü çocuğunun yerine indirip çocuğunu onun yerine çıkarmak.

```
        y                    x
       / \                  / \
      x   C     sağa       A   y
     / \       ─────►         / \
    A   B      ◄─────        B   C
               sola
```

$A$, $B$, $C$ alt ağaç (boş olabilir). Sağa dönmede $x$ yukarı çıkıyor, $y$ onun sağ çocuğu oluyor, ve $x$'in eski sağ alt ağacı $B$ el değiştirip $y$'nin sol alt ağacı oluyor.

Bu neden geçerli bir BST hamlesi? Soldaki ağaçta içek sıra $A, x, B, y, C$. Sağdakinde de $A, x, B, y, C$. $B$'deki anahtarlar $x$'ten büyük ve $y$'den küçük; iki ağaçta da tam o konumda duruyor. **Dönme içek sırayı korur**, yani BST değişmezini bozmaz. Sadece şekli değiştirir: $A$ bir seviye yukarı, $C$ bir seviye aşağı iniyor.

```c
int donme_sayisi;

/*      y                x
       / \              / \
      x   C    -->     A   y
     / \                  / \
    A   B                B   C        saga donme: x yukari, y asagi; B el degistirir */
static Dugum *saga_don(Dugum *y) {
    Dugum *x = y->sol;
    y->sol = x->sag;
    x->sag = y;
    guncelle(y); guncelle(x);          /* once asagidaki (y), sonra yukaridaki (x) */
    donme_sayisi++;
    return x;
}

static Dugum *sola_don(Dugum *x) {     /* saga_don'un aynasi */
    Dugum *y = x->sag;
    x->sag = y->sol;
    y->sol = x;
    guncelle(x); guncelle(y);
    donme_sayisi++;
    return y;
}
```

Üç pointer ataması, iki yükseklik güncellemesi: $O(1)$. Fonksiyon alt ağacın **yeni kökünü** döndürüyor; çağıran onu, eski kökü gösteren pointer'a yazmalı. Güncellemelerin sırası önemli: `x`'in yüksekliği `y`'ninkine bağlı, o yüzden önce `y`.

---

## 3. Dört durum

Bir ekleme ya da silmeden sonra bir düğümün denge faktörü $+2$ ya da $-2$ olabilir (daha fazlası olamaz, çünkü tek bir işlem bir alt ağacın yüksekliğini en fazla 1 değiştirir). Sol ağır ($+2$) durumu iki alt duruma ayrılıyor; fark, fazla yüksekliğin sol çocuğun **hangi tarafında** olduğu:

```
 sol-sol (LL): z'de tek sağa dönme

       z               y
      /               / \
     y      ──►      x   z
    /
   x

 sol-sağ (LR): önce y'de sola, sonra z'de sağa

     z              z              x
    /              /              / \
   y      ──►     x      ──►     y   z
    \            /
     x          y
```

- **Sol-sol**: fazlalık sol çocuğun da solunda. $z$'de tek bir sağa dönme yeter: $y$ yukarı çıkar.
- **Sol-sağ**: fazlalık sol çocuğun **sağında**. $z$'de sağa dönmek işe yaramaz (fazlalık $B$ alt ağacındaydı ve $B$ sadece el değiştirir, yükselmez; sol-sağ ağacı sağ-sol ağacına dönüşür). Önce sol çocukta **sola** dönüp durumu sol-sole çevir, sonra $z$'de sağa dön. Buna **çift dönme** denir; sonunda en derindeki $x$ (üçünün ortancası) köke çıkıyor.

Sağ ağır ($-2$) durumlar bunların aynası: sağ-sağ (tek sola dönme) ve sağ-sol (önce sağ çocukta sağa, sonra sola). Hangi alt durumda olduğumuzu çocuğun denge faktörü söylüyor: sol ağır bir düğümün sol çocuğu **sağa** yatıksa (`denge < 0`) sol-sağ durumu.

```c
/* n'nin cocuklari AVL; n'nin kendisi en fazla 2 dengesiz olabilir. Dengele, yeni koku dondur. */
static Dugum *dengele(Dugum *n) {
    guncelle(n);
    int b = denge(n);
    if (b > 1) {                                   /* sol agir */
        if (denge(n->sol) < 0) n->sol = sola_don(n->sol);   /* sol-sag durumu: once cocugu cevir */
        return saga_don(n);
    }
    if (b < -1) {                                  /* sag agir */
        if (denge(n->sag) > 0) n->sag = saga_don(n->sag);   /* sag-sol durumu */
        return sola_don(n);
    }
    return n;
}
```

Bütün AVL mantığı bu 15 satırda. Ekleme ve silme, Ders 8.8'deki işlemlerin aynısı; tek fark, dönüş yolunda her düğümde `dengele` çağırmak.

---

## 4. Ekleme ve silme

Ders 8.8'de pointer'a pointer ile özyinelemesiz yazmıştık. Burada **özyinelemeli** yazıyoruz, çünkü dengeleme yaprağa inen yolun **tersinde**, aşağıdan yukarı yapılıyor; özyinelemenin dönüşü bu yolu bizim için hazır tutuyor (Ders 8.6'daki çağrı yığını). Derinlik $O(\log n)$ olduğu için yığın taşması riski yok: 1 milyar anahtarda bile 45 çerçeve.

```c
Dugum *avl_ekle(Dugum *n, int x) {
    if (!n) {
        n = malloc(sizeof *n);
        n->anahtar = x; n->yuk = 0; n->sol = n->sag = NULL;
        return n;
    }
    if (x < n->anahtar)      n->sol = avl_ekle(n->sol, x);
    else if (x > n->anahtar) n->sag = avl_ekle(n->sag, x);
    else return n;                                 /* zaten var */
    return dengele(n);                             /* donuste, yol boyunca asagidan yukari */
}

Dugum *avl_sil(Dugum *n, int x) {
    if (!n) return NULL;
    if (x < n->anahtar)      n->sol = avl_sil(n->sol, x);
    else if (x > n->anahtar) n->sag = avl_sil(n->sag, x);
    else {
        if (!n->sol || !n->sag) {                  /* 0 ya da 1 cocuk */
            Dugum *c = n->sol ? n->sol : n->sag;
            free(n);
            return c;
        }
        Dugum *a = n->sag;                         /* iki cocuk: ardil */
        while (a->sol) a = a->sol;
        n->anahtar = a->anahtar;
        n->sag = avl_sil(n->sag, a->anahtar);
    }
    return dengele(n);
}
```

`n->sol = avl_ekle(n->sol, x)` kalıbı: her çağrı alt ağacın (belki dönmeyle değişmiş) yeni kökünü döndürüyor, çağıran onu yerine yazıyor. Kullanım: `kok = avl_ekle(kok, x)`. (Ders 8.8'deki `bst_ekle(&kok, x)` ile aynı işi farklı yoldan yapıyor.) `malloc` hata kontrolü kısalık için yok; Ders 8.24'teki kütüphanede olacak.

Sıralı ekleme, düz BST'yi listeye çeviren girdi. AVL'de:

```c
int main(void) {
    Dugum *kok = NULL;
    for (int i = 1; i <= 7; i++) {
        int once = donme_sayisi;
        kok = avl_ekle(kok, i);
        printf("ekle %d (%d donme):\n", i, donme_sayisi - once);
        avl_ciz(kok, 2);
    }
    ...
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c avl.c -o deneme && ./deneme
ekle 1 (0 donme):
  1
ekle 2 (0 donme):
      2
  1
ekle 3 (1 donme):
      3
  2
      1
ekle 4 (0 donme):
          4
      3
  2
      1
ekle 5 (1 donme):
          5
      4
          3
  2
      1
ekle 6 (1 donme):
          6
      5
  4
          3
      2
          1
ekle 7 (1 donme):
          7
      6
          5
  4
          3
      2
          1
...
3 1 2 ekle (2 donme):
      3
  2
      1
```

(Çizim yana yatık, Ders 8.7: kök solda.) `ekle 3`: 1'in denge faktörü $-2$, sağ-sağ durumu, 1'de sola dönme ve 2 köke çıkıyor. `ekle 6`: dengesizlik **kökte** (2'nin sağ alt ağacı yükseklik 2, solu 0); kökte sola dönme, 4 köke çıkıyor, 3 el değiştirip 2'nin sağ çocuğu oluyor. 7 eklemeden sonra ağaç **mükemmel**: yükseklik 2, her seviye dolu. Son satır sol-sağ durumu: 3, 1, 2 sırası iki dönme gerektiriyor ve ortanca anahtar 2 köke çıkıyor.

Eklemede şu da doğru: bir dönme (ya da çift dönme) dengesiz alt ağacın yüksekliğini **ekleme öncesindeki** değerine geri getirir. Bu yüzden ekleme başına en fazla bir (tek ya da çift) dönme gerekiyor; ondan yukarıdaki düğümlerin yüksekliği değişmiyor. Silmede bu garanti yok (Alıştırma 4).

---

## 5. Yükseklik ispatı

İddia: $n$ düğümlü bir AVL ağacının yüksekliği $h < 1.4405 \log_2(n + 2)$.

Soruyu ters çeviriyoruz: yüksekliği $h$ olan bir AVL ağacında **en az** kaç düğüm olabilir? Buna $N(h)$ diyelim. En az düğümlü ağacı kurmak için kökün bir alt ağacı yükseklik $h - 1$ olmalı (ağacın yüksekliği $h$ olsun diye), öteki de AVL koşulunun izin verdiği en kısa yükseklik, yani $h - 2$. İkisi de kendi yüksekliklerinde en az düğümlü olmalı:

$$
N(h) = 1 + N(h-1) + N(h-2), \qquad N(0) = 1,\; N(1) = 2.
$$

| $h$ | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| $N(h)$ | 1 | 2 | 4 | 7 | 12 | 20 | 33 | 54 |

Fibonacci'ye benziyor. Gerçekten de $N(h) + 1$ dizisi (2, 3, 5, 8, 13, 21, ...) Fibonacci bağıntısını sağlıyor: $N(h) + 1 = (N(h-1) + 1) + (N(h-2) + 1)$. Başlangıç değerleri $F_3 = 2$ ve $F_4 = 3$ olduğu için

$$
N(h) = F_{h+3} - 1.
$$

Ders 6.11'deki kapalı formdan $F_k \approx \varphi^k / \sqrt{5}$, $\varphi = (1+\sqrt5)/2 \approx 1.618$. Yüksekliği $h$ olan bir ağaçta $n \ge N(h) = F_{h+3} - 1$ düğüm var:

$$
n + 1 \ge F_{h+3} > \frac{\varphi^{h+3}}{\sqrt5} - 1
\;\Longrightarrow\;
h < \log_\varphi\big(\sqrt5\,(n+2)\big) - 3
\approx \frac{\log_2 (n+2)}{\log_2 \varphi} - 1.33
= 1.4405 \log_2(n+2) - 1.33.
$$

AVL ağacı, mükemmel dengeli ağaçtan en fazla **%44** daha yüksek. Bu en az düğümlü ağaçlara **Fibonacci ağaçları** denir: her düğümde sol alt ağaç bir Fibonacci ağacı, sağ alt ağaç bir küçüğü. AVL'nin en kötü durumu onlar ve onlar bile logaritmik.

1 milyon anahtar için bu sınır 28.7. Kesin sayı tablodan: $N(27) = 832\,039 \le 10^6 < N(28) = 1\,346\,268$, yani 1 milyon düğümlü bir AVL ağacının yüksekliği **en fazla 27** (Alıştırma 3).

---

## 6. Ölçüm ve denetleyici

Dengeli ağaç kodunda hata yapmak kolay, ve hatalar sessizdir: yanlış dönen bir ağaç hâlâ çalışır, sadece dengesizdir ya da (daha kötüsü) bir alt ağacı kaybeder. Her değişmezi kontrol eden bir **denetleyici** yazmak bu yüzden şart:

```c
/* Denetci: BST sirasi, saklanan yukseklikler ve |denge| <= 1. Gercek yuksekligi dondurur. */
int avl_denetle(const Dugum *n, long alt, long ust) {
    if (!n) return -1;
    if (n->anahtar <= alt || n->anahtar >= ust) { printf("sira bozuk\n"); abort(); }
    int a = avl_denetle(n->sol, alt, n->anahtar), b = avl_denetle(n->sag, n->anahtar, ust);
    if (n->yuk != 1 + maks(a, b)) { printf("yukseklik bozuk\n"); abort(); }
    if (a - b > 1 || b - a > 1)    { printf("denge bozuk\n"); abort(); }
    return n->yuk;
}
```

(Sıra denetimi Ders 8.8, Alıştırma 3'teki aralık yöntemi.) Ölçüm programı 1 milyon anahtarı sıralı ve karışık ekleyip hepsini arıyor; sonra 20 000 anahtar aralığında 2 milyon rastgele ekleme/silme yapıp her 1000 işlemde bir ağacı denetliyor:

```c
    for (int i = 0; i < 2000000; i++) {
        int x = rand() % 20000;
        if (rand() % 2) kok = avl_ekle(kok, x); else kok = avl_sil(kok, x);
        if (i % 1000 == 0) avl_denetle(kok, LONG_MIN, LONG_MAX);
    }
```

```
$ cc -std=c11 -O2 -Wall olcum.c avl.c -o olcum && ./olcum
n=1000000  log2(n)=19.93  1.44 log2(n)=28.70
  sirali   yukseklik=19  donme/ekleme=1.000  ekleme 0.137 s  arama 0.071 s
  karisik  yukseklik=23  donme/ekleme=0.700  ekleme 0.251 s  arama 0.097 s
  2M rastgele ekle/sil: 9896 anahtar, yukseklik=15, denetim gecti
```

Aynı program `-fsanitize=address,undefined` ile de temiz geçiyor.

- **Sıralı**: Ders 8.8'de 100 000 anahtar 25.8 s sürmüştü; burada 10 kat fazla anahtar 0.14 s. Yükseklik 19 = $\lfloor \log_2 10^6 \rfloor$: sıralı ekleme AVL'de **mükemmel** ağaç üretiyor. Ekleme başına tam bir dönme yapılıyor.
- **Karışık**: yükseklik 23, mükemmel ağacın 4 üstünde ve 28.7 sınırının çok altında. Ekleme başına 0.7 dönme (çift dönme 2 sayıldı).
- Sıralı ekleme karışıktan **hızlı**, çünkü art arda eklemeler hep ağacın aynı (en sağ) yolunu geziyor ve o yol cache'te kalıyor (Ders 7.24). Karışık eklemede her ekleme ağacın başka bir köşesine iniyor.

| | Düz BST (8.8) | AVL |
| --- | --- | --- |
| Arama, ekleme, silme | $O(h)$, en kötü $O(n)$ | $O(\log n)$ garanti |
| Düğüm başına ek alan | — | Yükseklik (`int`; 2 bit de yeter, Alıştırma 5) |
| Ekleme başına dönme | — | En fazla 1 (tek ya da çift) |
| Silme başına dönme | — | $O(\log n)$'e kadar |

AVL çok sıkı dengelenmiş bir ağaç: arama yükü ağır, değişikliği az olan iş yüklerinde (bir kere kurulup çok sorgulanan sözlükler) ideal. Sık ekleme ve silmede dengeyi korumak için yapılan iş göreli olarak artıyor; Ders 8.10'daki kırmızı-siyah ağaç biraz daha yüksek bir ağaca razı olup daha az dönme yapıyor.

---

## Alıştırmalar

**1** – Dönmenin içek sırayı koruduğunu Bölüm 2'deki çizim üzerinden gösterdik. $A$, $B$, $C$ boş değilken, dönmeden önce ve sonra $A$'daki bir düğümün, $B$'deki bir düğümün ve $C$'deki bir düğümün **derinliği** nasıl değişiyor? Bu, dönmenin neden dengeyi düzeltebildiğini nasıl açıklıyor?

**2** – Boş bir AVL ağacına 50, 20, 70, 10, 30, 25 sırasıyla ekle. Hangi eklemede dönme oluyor, hangi düğümde, ve hangi durum (LL, RR, LR, RL)? Son ağacı çiz.

**3** – $N(h)$ tablosunu kullanarak 1 milyon düğümlü bir AVL ağacının en fazla kaç yüksekliğe sahip olabileceğini bul. Ölçümde karışık eklemenin yüksekliği 23 çıktı. Bu sınıra ulaşan bir ağaç nasıl görünür?

**4** – Eklemede en fazla bir dönme yetiyor. Silmede neden yetmeyebilir? Bir Fibonacci ağacından (Bölüm 5) bir yaprak silindiğinde ne olduğunu düşün.

**5** – Düğüm `int yuk` saklıyor. Bunun yerine yalnızca denge faktörü ($-1$, $0$, $+1$) saklansa yeter mi? Kaç bit eder? Düğüm yapısını düşününce gerçekte bir bellek kazancı olur mu (Ders 4.26)?

<details>
<summary>Cevaplar</summary>

**1** – Sağa dönmede $x$ kökün yerine çıkıyor. $A$'daki her düğüm bir seviye **yukarı** çıkıyor (derinlik $-1$), $B$'dekiler **aynı** derinlikte kalıyor (önceden $y \to x \to B$, sonra $x \to y \to B$; iki adım), $C$'dekiler bir seviye **aşağı** iniyor ($+1$). Sol-sol durumunda fazlalık $A$'daydı; dönme onu yukarı alıp $C$'yi aşağı itiyor ve iki tarafı eşitliyor. Sol-sağ durumunda fazlalık $B$'deydi ve tek dönme $B$'nin derinliğini değiştirmiyor, bu yüzden işe yaramıyor; çift dönmenin ilk adımı fazlalığı $B$'den çıkarıp sol-sol konumuna getiriyor.

**2** – Programla izlendiğinde:

```
ekle 25: 2 donme
          70
      50
  30
          25
      20
          10
```

İlk beş eklemede dönme yok: 50 kök, 20 ve 70 çocukları, 10 ve 30 da 20'nin çocukları. 25, 30'un sol çocuğu olarak eklenince 20'nin denge faktörü $-1$ (sağı yükseklik 1, solu 0), 50'ninki $+2$ (solu yükseklik 2, sağı 0). Dengesiz düğüm 50; sol çocuğu 20 **sağa** yatık: sol-sağ (LR) durumu. Önce 20'de sola dönme (30 yukarı çıkar, 25 el değiştirip 20'nin sağ çocuğu olur), sonra 50'de sağa dönme (30 köke çıkar). Son ağaç: kök 30; solunda 20 (çocukları 10, 25), sağında 50 (sağ çocuğu 70).

**3** – $N(27) = 832\,039 \le 10^6 < N(28) = 1\,346\,268$: en fazla 27 (ölçen program aynı sonucu veriyor). Formül 28.7 diyordu, tamsayı sınır 27. Bu sınıra ulaşan bir ağaç, yüksekliği 27 olan bir Fibonacci ağacından başlayıp yüksekliği artırmadan düğüm eklenerek elde edilir: hemen her düğümde iki alt ağacın yükseklikleri bir farklı. Rastgele ekleme böyle aşırı yatık şekiller üretmiyor; ölçülen 23, mükemmel ağacın (19) sadece 4 üstünde. AVL'nin 1.44 çarpanı en kötü durum sınırı, tipik durum değil.

**4** – Eklemede dönme, alt ağacın yüksekliğini eski haline döndürüp yukarıyı etkilemiyordu. Silmede ise bir dönme alt ağacın yüksekliğini bir **azaltabilir** (eklemenin tersi: alt ağaç zaten kısalmıştı, dönme onu dengeleyip bir kısalttı daha). O zaman ebeveynin denge faktörü değişiyor ve o da dengesiz olabiliyor; bu yukarı doğru köke kadar sürebilir. Fibonacci ağacında her düğüm sınırda olduğu için, en kısa taraftaki en derin yaprağı silmek her seviyede bir dönme tetikleyebilir: $O(\log n)$ dönme. Toplam maliyet yine $O(\log n)$, sadece sabit büyüyor.

**5** – Yeter. Ekleme ve silme sırasında yükseklik yerine denge faktörünü güncellemek mümkün (her durumdaki yeni faktörler sabit bir tablo), ama kod daha karışık: `guncelle`'nin tek satırı yerine her dönme durumu için ayrı kurallar. Üç değer için **2 bit** yeter. Ama `Dugum`'da `int` (4 bayt) + iki pointer (16 bayt) = 20 bayt, hizalamayla 24 bayt (Ders 4.26). `int yuk` yerine `signed char denge` koymak yapıyı 24 bayttan aşağı indirmiyor; dolgu boşluğu artıyor sadece. Bit saklamak ancak denge bitleri pointer'ların kullanılmayan alt bitlerine gizlenirse (pointer'lar 8'e hizalı, alt 3 bitleri hep 0; Ders 5.7) bir şey kazandırır. Linux çekirdeğinin kırmızı-siyah ağacı rengi tam olarak böyle saklıyor (Ders 8.10).

</details>

---

## Kaynaklar

- Georgy Adelson-Velsky ve Evgenii Landis, "An algorithm for the organization of information", *Doklady Akademii Nauk SSSR* 146, 1962.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.2.3: dengeli ağaçlar; yükseklik sınırının ispatı ve Fibonacci ağaçları.
- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 13.
- Ben Pfaff, "An Introduction to Binary Search Trees and Balanced Trees" (*libavl* kılavuzu): AVL ve kırmızı-siyah ağaçların C'de ayrıntılı, test edilmiş uygulamaları.

**Sıradaki ders:** Kırmızı-siyah ağaç. Kurallar, ekleme durumları ve 2-3-4 ağacı ile ilişkisi.
