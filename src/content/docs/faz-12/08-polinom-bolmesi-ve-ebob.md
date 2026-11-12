---
title: "12.8 Polinom bölmesi ve EBOB"
description: "Q[x]'te polinom uzun bölmesi (her adımda baş terimi yok etmek); Öklid algoritmasının polinomlara taşınması ve monik EBOB; içerik ve ilkel kısım, Gauss lemması; sözde bölme (prem) ile kesirsiz kalan; Knuth'un klasik örneğinde dört kalan dizisi: Q'da Öklid (19 basamaklı kesir), Öklid PRS (35 basamak), ilkel PRS ve alt-sonuç PRS (260708, SymPy ile birebir aynı); derece 20'de Öklid PRS'nin her adımda 1 + √2 kat büyüyüp 1.68 milyon basamağa çıkması; içine EBOB gizlenmiş derece 40'lık polinomlarda dört yolun karşılaştırması."
---

Tamsayılarda Öklid algoritması (Ders 1.3 ve 6.19) en eski algoritmalardan biri: $\gcd(a, b) = \gcd(b, a \bmod b)$. Polinomlar da bir halka ve bölme ile kalanları var. Öyleyse aynı algoritma polinomlarda da çalışmalı. Çalışıyor, ama Ders 12.6'daki ara değer şişmesinin en ünlü örneğini de beraberinde getiriyor. Bu derste o şişmeyi ölçüp onu yenen iki yöntemi yazacağız.

Polinom EBOB'u bir CAS'ın her yerinde: kesirli ifadeleri sadeleştirmek ($\frac{x^2 - 1}{x^2 + 2x + 1} = \frac{x - 1}{x + 1}$), katlı kökleri bulmak ($\gcd(p, p')$), çarpanlara ayırmanın ilk adımı.

---

## 1. Uzun bölme

$a = qb + r$, $\deg r < \deg b$. Okulda sayılar için yaptığımızın aynısı ama daha basit, çünkü **tahmin yok**: her adımda $a$'nın baş terimini $b$'nin baş terimine böl, bu bölümün bir terimi. $b$ ile çarpıp çıkar, baş terim sıfırlanır. Algoritma D'nin (Ders 12.4) tahmin ve düzeltme adımları burada yok, çünkü katsayılar arasında elde yok.

Tek şart: $b$'nin baş katsayısına **bölebilmek**. $\mathbb{Q}$'da her sıfır olmayan sayıya bölünebiliyor. $\mathbb{Z}$'de $x^2 \div 2x$ yapılamıyor. Katsayıların $\mathbb{Q}$ olmasını bu yüzden seçmiştik.

```c
/* poli_bol.c: polinom uzun bolmesi, Oklid, icerik ve ilkel kisim, sozde bolme */
#include <stdlib.h>
#include <string.h>
#include "bn_mod.h"
#include "poli.h"

/* a = q b + r, der r < der b. Okul bolmesi: her adimda bas terimi yok et */
void poli_bol(poli *q, poli *r, const poli *a, const poli *b) {
    poli tq, tr; poli_baslat(&tq); poli_baslat(&tr);
    poli_kopyala(&tr, a);
    int db = poli_derece(b);
    if (poli_derece(a) >= db) poli_yer(&tq, a->n - b->n + 1);
    rat c, t; rat_baslat(&c); rat_baslat(&t);
    while (poli_derece(&tr) >= db) {
        size_t k = tr.n - b->n;                          /* bolumun bu terimi: c x^k */
        rat_bol(&c, &tr.c[tr.n - 1], &b->c[b->n - 1]);
        rat_kopyala(&tq.c[k], &c);
        for (size_t i = 0; i < b->n; i++) {              /* tr -= c x^k b */
            rat_carp(&t, &c, &b->c[i]);
            rat_cikar(&tr.c[i + k], &tr.c[i + k], &t);
        }
        poli_duzelt(&tr);                                /* bas katsayi tam sifir oldu */
    }
    rat_sil(&c); rat_sil(&t);
    poli_duzelt(&tq);
    if (q) { poli_sil(q); *q = tq; } else poli_sil(&tq);
    if (r) { poli_sil(r); *r = tr; } else poli_sil(&tr);
}

void poli_monik(poli *r, const poli *a) {
    poli_kopyala(r, a);
    if (!r->n) return;
    rat k; rat_baslat(&k); rat_kopyala(&k, &r->c[r->n - 1]);
    for (size_t i = 0; i < r->n; i++) rat_bol(&r->c[i], &r->c[i], &k);
    rat_sil(&k);
}

/* Oklid: (a, b) -> (b, a mod b), son sifir olmayan kalan */
void poli_ebob(poli *g, const poli *a, const poli *b) {
    poli x, y, r; poli_baslat(&x); poli_baslat(&y); poli_baslat(&r);
    poli_kopyala(&x, a); poli_kopyala(&y, b);
    while (y.n) { poli_bol(0, &r, &x, &y); poli_sil(&x); x = y; y = r; poli_baslat(&r); }
    poli_monik(g, &x);
    poli_sil(&x); poli_sil(&y);
}

void poli_icerik(rat *c, const poli *a) {
    bn g, l, t; bn_baslat(&g); bn_baslat(&l); bn_baslat(&t);
    bn_u64(&l, 1);
    for (size_t i = 0; i < a->n; i++) {
        bn_ebob(&g, &g, &a->c[i].p);                     /* ebob(0, x) = |x| */
        bn_ebob(&t, &l, &a->c[i].q);                     /* ekok(l, q) = l q / ebob(l, q) */
        bn_carp(&l, &l, &a->c[i].q); bn_bol(&l, 0, &l, &t);
    }
    rat_sil(c); rat_baslat(c);
    if (g.n) { bn_kopyala(&c->p, &g); bn_kopyala(&c->q, &l); }  /* ebob(g, l) = 1 zaten */
    bn_sil(&g); bn_sil(&l); bn_sil(&t);
}

void poli_ilkel(poli *r, const poli *a) {
    rat c; rat_baslat(&c);
    poli_icerik(&c, a);
    if (a->n && a->c[a->n - 1].p.isaret) c.p.isaret = 1;  /* bas katsayi pozitif olsun */
    poli_kopyala(r, a);
    for (size_t i = 0; i < r->n; i++) rat_bol(&r->c[i], &r->c[i], &c);
    rat_sil(&c);
}

/* sozde kalan: Z[x]'te kesirsiz kalan. lc(b)^(da-db+1) a, b'ye Q'da bolunur ve kalan tamsayi katsayili */
void poli_prem(poli *r, const poli *a, const poli *b) {
    poli t; poli_baslat(&t);
    poli_kopyala(&t, a);
    int k = poli_derece(a) - poli_derece(b) + 1;
    for (int i = 0; i < k; i++) poli_skaler(&t, &t, &b->c[b->n - 1]);
    poli_bol(0, r, &t, b);
    poli_sil(&t);
}

size_t poli_basamak(const poli *a) {
    size_t en = 0;
    for (size_t i = 0; i < a->n; i++) {
        char *p = bn_ondaliga(&a->c[i].p), *q = bn_ondaliga(&a->c[i].q);
        size_t b = strlen(p) - (p[0] == '-') + (strcmp(q, "1") ? strlen(q) : 0);
        if (b > en) en = b;
        free(p); free(q);
    }
    return en;
}
```

Dosyadaki öteki fonksiyonlar:

- **`poli_ebob`**: Öklid'in aynısı. Sonucu **monik** yapıyor (baş katsayı 1). EBOB yalnızca bir sabit çarpana kadar tek: $x - 1$ ile $2x - 2$ ikisi de ortak bölen. Monik olan kanonik seçim.
- **`poli_icerik` ve `poli_ilkel`**: Bir $\mathbb{Z}[x]$ polinomunun **içeriği** katsayılarının EBOB'u. **İlkel kısmı** polinom bölü içeriği. $6x^2 + 4 = 2 \cdot (3x^2 + 2)$. Gauss lemması: iki ilkel polinomun çarpımı da ilkel. Bu yüzden $\gcd(a, b) = \gcd(\text{içerik}(a), \text{içerik}(b)) \cdot \gcd(\text{ilkel}(a), \text{ilkel}(b))$ ve iki problem ayrılıyor.
- **`poli_prem`**: **Sözde kalan**. $a$'yı önce $\text{lc}(b)^{\deg a - \deg b + 1}$ ile çarparsan, uzun bölmenin bütün adımları $\mathbb{Z}$'de kalıyor: her adımdaki bölmenin paydası $\text{lc}(b)$ ve onu önceden çarpmış oluyoruz. Kesirsiz bir kalan, ama gereksiz bir çarpanla.

---

## 2. Knuth'un örneği

TAOCP §4.6.1'in ünlü çifti:

$$A = x^8 + x^6 - 3x^4 - 3x^3 + 8x^2 + 2x - 5, \qquad B = 3x^6 + 5x^4 - 4x^2 - 9x + 21$$

Bu ikisi aralarında asal: EBOB 1. Ama bunu bulmak için hangi kalanlar geçiyor? Dört yol deniyoruz:

1. **$\mathbb{Q}$'da Öklid**: kalanlar olduğu gibi, kesirli.
2. **Öklid PRS** (*polynomial remainder sequence*): her adımda `poli_prem`, hiç sadeleştirme yok.
3. **İlkel PRS**: her sözde kalanı ilkel kısmına indir. Her adımda bir içerik EBOB'u.
4. **Alt-sonuç PRS** (Collins 1967, Brown 1971): sözde kalanı, önceden **bilinen** bir $\beta_i$ çarpanına böl. Bölme her zaman tam ve EBOB gerekmiyor. Bareiss'in (Ders 12.6) polinom karşılığı. $\beta$ ve $\psi$ formülleri aşağıdaki kodda.

```c
/* prs.c: dort kalan dizisi: Q'da Oklid, Oklid PRS, ilkel PRS, alt-sonuc PRS.
   Once Knuth'un ornegi, sonra icine EBOB gizlenmis rastgele polinomlar */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "olcum.h"
#include "bn_mod.h"
#include "poli.h"

static const char *ad[] = { "Q", "Oklid", "ilkel", "altsonuc" };

static void satir(const char *yol, int i, const poli *r) {
    char *s = poli_yaz(r, "x");
    printf("  %-8s r%d  der %d  %3zu bas.  %.60s%s\n", yol, i, poli_derece(r), poli_basamak(r), s, strlen(s) > 60 ? "..." : "");
    free(s);
}

static void rat_us(rat *r, const rat *x, int k) {       /* r = x^k, k eksi olabilir */
    rat t; rat_baslat(&t); rat_tam(&t, 1);
    for (int i = 0; i < (k < 0 ? -k : k); i++) rat_carp(&t, &t, x);
    if (k < 0) { rat bir; rat_baslat(&bir); rat_tam(&bir, 1); rat_bol(&t, &bir, &t); rat_sil(&bir); }
    rat_sil(r); *r = t;
}

/* tur 0: Q'da Oklid, 1: Oklid PRS (sozde kalan), 2: ilkel PRS, 3: alt-sonuc PRS (Collins, Brown) */
static size_t dizi(int tur, const poli *A, const poli *B, FILE *f, int yaz, poli *son) {
    size_t en = 0;
    poli r0, r1, r2; poli_baslat(&r0); poli_baslat(&r1); poli_baslat(&r2);
    poli_kopyala(&r0, A); poli_kopyala(&r1, B);
    rat beta, psi, t, a; rat_baslat(&beta); rat_baslat(&psi); rat_baslat(&t); rat_baslat(&a);
    int d = poli_derece(&r0) - poli_derece(&r1);
    rat_tam(&beta, d % 2 ? 1 : -1);                      /* beta_1 = (-1)^(d+1) */
    rat_tam(&psi, -1);                                   /* psi_1 = -1 */
    for (int i = 2; r1.n; i++) {
        if (tur == 0) poli_bol(0, &r2, &r0, &r1);
        else poli_prem(&r2, &r0, &r1);
        if (tur == 2) poli_ilkel(&r2, &r2);
        if (tur == 3) { rat_tam(&t, 1); rat_bol(&t, &t, &beta); poli_skaler(&r2, &r2, &t); }   /* r_{i+1} = prem / beta_i */
        if (yaz) satir(ad[tur], i, &r2);
        if (poli_basamak(&r2) > en) en = poli_basamak(&r2);
        if (f && tur == 3) { for (size_t k = r2.n; k-- > 0;) { char *c = rat_yaz(&r2.c[k]); fprintf(f, "%s%c", c, k ? ',' : '\n'); free(c); } }
        if (tur == 3 && r2.n) {                          /* psi ve beta'yi bir sonraki adim icin guncelle */
            rat_kopyala(&a, &r1.c[r1.n - 1]);            /* a_i = lc(r_i) */
            rat_tam(&t, -1); rat_carp(&a, &a, &t);       /* -a_i */
            int dyeni = poli_derece(&r1) - poli_derece(&r2);
            rat_us(&t, &a, d);                           /* psi = (-a_i)^d_i psi^(1 - d_i) */
            rat_us(&psi, &psi, 1 - d);
            rat_carp(&psi, &psi, &t);
            rat_us(&t, &psi, dyeni);                     /* beta = -a_i psi^d_{i+1} */
            rat_carp(&beta, &a, &t);
            d = dyeni;
        }
        poli_sil(&r0); r0 = r1; r1 = r2; poli_baslat(&r2);
    }
    rat_sil(&beta); rat_sil(&psi); rat_sil(&t); rat_sil(&a);
    if (son) poli_kopyala(son, &r0);                     /* son sifir olmayan kalan */
    poli_sil(&r0); poli_sil(&r1);
    return en;
}

int main(void) {
    poli A, B; poli_baslat(&A); poli_baslat(&B);
    poli_oku(&A, "-5,2,8,-3,-3,0,1,0,1");                /* x^8 + x^6 - 3x^4 - 3x^3 + 8x^2 + 2x - 5 */
    poli_oku(&B, "21,-9,-4,0,5,0,3");                    /* 3x^6 + 5x^4 - 4x^2 - 9x + 21 */
    char *a = poli_yaz(&A, "x"), *b = poli_yaz(&B, "x");
    printf("A = %s\nB = %s\n", a, b);
    FILE *f = fopen("prs_kontrol.txt", "w");
    for (int tur = 0; tur < 4; tur++) { dizi(tur, &A, &B, f, 1, 0); printf("\n"); }
    fclose(f);

    /* gizli EBOB: A = g u, B = g v, g derece 4; katsayilar [-9, 9] */
    printf("  der(A)   yol        en buyuk ara katsayi       sure    EBOB = g ?\n");
    uint64_t s = 5;
    for (int n = 10; n <= 40; n += 10) {
        poli g, u, v, son, m1, m2; poli_baslat(&g); poli_baslat(&u); poli_baslat(&v); poli_baslat(&son); poli_baslat(&m1); poli_baslat(&m2);
        for (int i = 0; i <= 4; i++) poli_ayarla(&g, i, (int64_t)(rastgele64(&s) % 19) - 9 + (i == 4 ? 10 : 0), 1);
        for (int i = 0; i <= n - 4; i++) { poli_ayarla(&u, i, (int64_t)(rastgele64(&s) % 19) - 9, 1); poli_ayarla(&v, i, (int64_t)(rastgele64(&s) % 19) - 9, 1); }
        poli_ayarla(&u, n - 4, 1, 1); poli_ayarla(&v, n - 4, 2, 1);
        poli_carp(&A, &g, &u); poli_carp(&B, &g, &v);
        poli_monik(&m1, &g);
        for (int tur = 0; tur < 4; tur++) {
            if (tur == 1 && n > 10) { printf("%7d   %-9s %13s\n", n, "Oklid", "(atlandi)"); continue; }   /* dakikalarca surer */
            double t0 = simdi();
            size_t en = dizi(tur, &A, &B, 0, 0, &son);
            double t1 = simdi();
            poli_monik(&m2, &son);
            printf("%7d   %-9s %13zu basamak %10.2f ms   %s\n", n, ad[tur], en, (t1 - t0) * 1e3, poli_esit(&m1, &m2) ? "evet" : "HAYIR");
        }
        if (n == 40) {                                       /* SymPy kontrolu */
            FILE *k = fopen("prs_ebob.txt", "w");
            char *a = poli_yaz(&A, "x"), *b = poli_yaz(&B, "x"), *e = poli_yaz(&m1, "x");
            fprintf(k, "%s\n%s\n%s\n", a, b, e); fclose(k); free(a); free(b); free(e);
        }
        poli_sil(&g); poli_sil(&u); poli_sil(&v); poli_sil(&son); poli_sil(&m1); poli_sil(&m2);
    }
    return 0;
}
```

```
$ clang -O2 -c poli_bol.c && clang -O2 prs.c bn_*.o rat.o poli.o poli_bol.o -o prs
$ ./prs
A = x^8 + x^6 - 3*x^4 - 3*x^3 + 8*x^2 + 2*x - 5
B = 3*x^6 + 5*x^4 - 4*x^2 - 9*x + 21
  Q        r2  der 4    2 bas.  -5/9*x^4 + 1/9*x^2 - 1/3
  Q        r3  der 2    5 bas.  -117/25*x^2 - 9*x + 441/25
  Q        r4  der 1   11 bas.  233150/19773*x - 102500/6591
  Q        r5  der 0   19 bas.  -1288744821/543589225
  Q        r6  der -1    0 bas.  0

  Oklid    r2  der 4    2 bas.  -15*x^4 + 3*x^2 - 9
  Oklid    r3  der 2    5 bas.  15795*x^2 + 30375*x - 59535
  Oklid    r4  der 1   16 bas.  1254542875143750*x - 1654608338437500
  Oklid    r5  der 0   35 bas.  12593338795500743100931141992187500
  Oklid    r6  der -1    0 bas.  0

  ilkel    r2  der 4    1 bas.  5*x^4 - x^2 + 3
  ilkel    r3  der 2    2 bas.  13*x^2 + 25*x - 49
  ilkel    r4  der 1    4 bas.  4663*x - 6150
  ilkel    r5  der 0    1 bas.  1
  ilkel    r6  der -1    0 bas.  0

  altsonuc r2  der 4    2 bas.  15*x^4 - 3*x^2 + 9
  altsonuc r3  der 2    3 bas.  65*x^2 + 125*x - 245
  altsonuc r4  der 1    5 bas.  9326*x - 12300
  altsonuc r5  der 0    6 bas.  260708
  altsonuc r6  der -1    0 bas.  0
```

Dört yol da aynı sonucu buluyor: son sıfır olmayan kalan bir **sabit**, EBOB 1. Ama ara kalanların boyutları çok farklı:

- **$\mathbb{Q}$**'da kesirler büyüyor: $-1288744821/543589225$, sadece 1 olduğunu söylemek için.
- **Öklid PRS** 35 basamağa çıkıyor. Kesir yok ama gereksiz çarpanlar birikiyor: her `prem` bir önceki adımın baş katsayısının kuvvetini taşıyor.
- **İlkel PRS** en küçük katsayıları veriyor, ama her adımda katsayıların EBOB'unu hesaplıyor.
- **Alt-sonuç PRS** EBOB hesaplamadan ilkel PRS'ye yakın kalıyor. Kalanları SymPy'nin `subresultants` fonksiyonuyla birebir aynı:

```
$ python3 -c "
from sympy import *
x = symbols('x'); A = x**8+x**6-3*x**4-3*x**3+8*x**2+2*x-5; B = 3*x**6+5*x**4-4*x**2-9*x+21
for p in subresultants(A, B, x)[2:]: print(Poly(p, x).all_coeffs())"
[15, 0, -3, 0, 9]
[65, 125, -245]
[9326, -12300]
[260708]
```

260708 da tesadüf değil: SymPy'ye `resultant(A, B, x)` dersen tam olarak 260708 diyor. $A$ ile $B$'nin **sonuç**u (*resultant*), Sylvester matrisinin determinantı. Alt-sonuç PRS'nin her elemanı, Sylvester matrisinin bir alt determinantı. Bareiss'te ara değerlerin minör olması gibi, bu da boyutları sınırlıyor.

---

## 3. Şişme ne kadar hızlı?

Knuth'un örneği küçük. Derece 20'de, içine derece 4'lük bir ortak bölen gizlenmiş iki polinomda Öklid PRS'yi SymPy ile (Python'un kendi tamsayılarıyla) çalıştırıp her adımda en büyük katsayının basamak sayısını yazdırdım:

```
der  basamak    sure
 19        4     0.0 s
 18        9
 17       19
 16       44
 15      104
 14      251
 13      605
 12     1460
 11     3524
 10     8507
  9    20533     0.1 s
  8    49571     0.2 s
  7   119674     0.6 s
  6   288917     1.5 s
  5   697508     4.7 s
  4  1683931    15.1 s
 -1        -    45.5 s   (sifir: EBOB derece 4)
```

Her adımda yaklaşık **2.414 kat**. Bu sayı $1 + \sqrt 2$: dereceler birer birer düştüğünde `prem`, önceki iki kalanın boyutlarını $d_{k+1} \approx 2 d_k + d_{k-1}$ olarak birleştiriyor ($2 \cdot 605 + 251 = 1461$, ölçülen 1460). Bu bağıntının çözümü $(1 + \sqrt 2)^k$ (Ders 6.11'deki karakteristik denklem $r^2 = 2r + 1$). 16 adımda 1.7 milyon basamak, 4 basamaklı katsayılardan başlayıp. Bizim $O(n^2)$ kütüphanemiz bunu dakikalarca hesaplıyor; tabloda bu yüzden atlandı.

---

## 4. Gizli EBOB'lu polinomlar

$A = g u$, $B = g v$: $g$ derece 4, $u$ ve $v$ rastgele, katsayılar $[-9, 9]$. EBOB'un $g$ çıkması gerekiyor (rastgele $u$, $v$ neredeyse kesin aralarında asal). Her yolun bulduğu son kalanı monik yapıp $g$'nin monik haliyle karşılaştırıyoruz:

```
  der(A)   yol        en buyuk ara katsayi       sure    EBOB = g ?
     10   Q                    50 basamak       0.93 ms   evet
     10   Oklid               248 basamak       0.37 ms   evet
     10   ilkel                 9 basamak       0.30 ms   evet
     10   altsonuc             21 basamak       0.30 ms   evet
     20   Q                   519 basamak      31.90 ms   evet
     20   Oklid         (atlandi)
     20   ilkel                36 basamak       0.85 ms   evet
     20   altsonuc             57 basamak       0.97 ms   evet
     30   Q                  1464 basamak     188.87 ms   evet
     30   Oklid         (atlandi)
     30   ilkel                60 basamak       1.54 ms   evet
     30   altsonuc             77 basamak       1.32 ms   evet
     40   Q                  3058 basamak    1060.88 ms   evet
     40   Oklid         (atlandi)
     40   ilkel                87 basamak       3.26 ms   evet
     40   altsonuc            178 basamak       3.56 ms   evet
```

Derece 40'ta SymPy'nin `gcd`'si de aynı $g$'yi buluyor (program polinomları `prs_ebob.txt`'ye yazıyor):

```
$ python3 -c "
from sympy import *
x = symbols('x'); L = open('prs_ebob.txt').read().split('\n')
A, B, g = [sympify(l.replace('^', '**')) for l in L[:3]]
print('SymPy gcd monik == g:', expand(Poly(gcd(A, B), x).monic().as_expr() - g) == 0, '  g =', g)"
SymPy gcd monik == g: True   g = x**4 + x**3/6 - x**2/9 + 7*x/18 - 1/2
```

- **$\mathbb{Q}$'da Öklid** üstel değil, polinom zamanlı büyüyor (kesirler her adımda sadeleşiyor). Yine de ilkel PRS'den 300 kat yavaş: kesirli kalanlar sayı olarak alt-sonuçların oranları ve her işlemde bir EBOB.
- **İlkel ve alt-sonuç PRS** bu boyutta başa baş. İlkel daha küçük sayılar tutuyor ama her adımda $n$ katsayının EBOB'unu hesaplıyor. Alt-sonuç biraz daha büyük sayılar tutuyor, EBOB hesaplamıyor.

**Gerçek sistemler hiçbirini kullanmıyor.** Hem ilkel hem alt-sonuç PRS, ara katsayıları sınırlı tutsa da büyük sayılarla çalışıyor. Brown'un **modüler EBOB algoritması** (1971) EBOB'u birkaç küçük asal $p$ için $\mathbb{Z}_p[x]$'te hesaplıyor. Orada katsayılar hep 64 bite sığıyor ve şişme yok. Sonra sonuçlar Çin kalan teoremiyle (Ders 6.20) $\mathbb{Z}$'ye taşınıyor. Bir asal "şanssız" çıkabilir ($p$, sonuçu bölüyorsa EBOB'un derecesi yanlış çıkar), bu da derecesi büyük çıkan asalı atarak anlaşılıyor. $\mathbb{Z}_p[x]$ aritmetiğini Ders 12.10'da yazacağız. Modüler EBOB Alıştırma 5'te.

---

## Alıştırmalar

**1** – $\gcd(x^4 - 1, x^6 - 1)$'i elle Öklid ile bul. Genel olarak $\gcd(x^a - 1, x^b - 1)$ nedir? (İpucu: Ders 6.17'deki $\gcd(a, b)$.)

**2** – $p = (x - 1)^3 (x + 2)$ için $\gcd(p, p')$'yi `poli_ebob` ile hesapla. Sonuç neden $(x-1)^2$? **Karesiz çarpanlara ayırma**: $p / \gcd(p, p')$ neyi verir?

**3** – `poli_ebob`'da her kalanı **monik** yaparak ilerle (her adımda baş katsayıya böl). Derece 40'taki 3058 basamak ve 1 saniye nasıl değişiyor?

**4** – $\text{res}(A, B)$, Sylvester matrisinin determinantı. Knuth'un $A$ ve $B$'si için $14 \times 14$'lük Sylvester matrisini kur ve Ders 12.6'daki Bareiss ile determinantını hesapla. 260708 ile ilişkisini bul.

**5** – Modüler EBOB'un en basit hali: büyük bir asal $p$ seç (örneğin $2^{31} - 1$), $A$ ve $B$'nin katsayılarını mod $p$ al, $\mathbb{Z}_p[x]$'te Öklid uygula, sonucu monik yap. Derecesi, gerçek EBOB'unkine eşit mi? Hangi $p$'ler için olmaz?

<details>
<summary>Cevaplar</summary>

**1** – $x^6 - 1 = x^2 (x^4 - 1) + (x^2 - 1)$, sonra $x^4 - 1 = (x^2 + 1)(x^2 - 1) + 0$. EBOB $x^2 - 1$. Genelde $\gcd(x^a - 1, x^b - 1) = x^{\gcd(a, b)} - 1$. Polinom Öklid'inin adımları, üslerde $\gcd(a, b)$'nin Öklid adımlarını izliyor: $x^a - 1 \bmod x^b - 1 = x^{a \bmod b} - 1$.

**2** – $p' = (x-1)^2 [3(x+2) + (x-1)] = (x-1)^2 (4x + 5)$. Ortak kısım $(x - 1)^2$: $k$ katlı bir kök türevde $k - 1$ katlı kalıyor. $p / \gcd(p, p') = (x - 1)(x + 2)$: her kök bir kez. Yani **karesiz kısım**. Yun'un algoritması bunu tekrarlayarak her katlılığı ayrı ayrı çıkarıyor; çarpanlara ayırmanın ilk adımı.

**3** – Aynı rastgele polinomlarla ölçtüm: derece 40'ta en büyük katsayı 3058 basamaktan **173 basamağa**, süre 1061 ms'den **62 ms**'ye iniyor (10: 17 basamak, 20: 71, 30: 119). Monik kalan, kalanın $\mathbb{Q}$'daki kanonik temsili ve baş katsayının taşıdığı fazlalığı her adımda atıyor. Yine de kesirli: her işlemde EBOB var, bu yüzden ilkel PRS'den hâlâ 20 kat yavaş.

**4** – Sylvester matrisi: $B$'nin katsayılarından 8 satır ve $A$'nın katsayılarından 6 satır, kaydırılarak. $\det = \text{res}(A, B)$. Alt-sonuç PRS'nin son elemanı, sabit kalan durumunda $\pm \text{res}(A, B)$. SymPy'nin `resultant` fonksiyonu 260708 veriyor; Bareiss de satırlar standart sırada ($A$'nın 6 satırı önce) kurulursa aynısını vermeli. Satır sırası değişirse işaret değişebilir.

**5** – Çoğu $p$ için evet: EBOB'un derecesi, $p$ ne $A$ ve $B$'nin baş katsayılarını ne de $\text{res}(A/g, B/g)$'yi bölmüyorsa korunuyor. Bölüyorsa mod $p$ EBOB'un derecesi **büyük** çıkıyor ("şanssız asal"). Rastgele büyük bir $p$ için olasılık çok küçük. Gerçek algoritma birkaç asal deniyor, en küçük dereceliyi tutuyor ve ÇKT ile katsayıları yeniden kuruyor. Son adımda bulunan $g$'nin $A$ ve $B$'yi gerçekten böldüğü kontrol ediliyor.

</details>

---

## Kaynaklar

- Donald Knuth, *TAOCP*, Cilt 2, §4.6.1 (polinom bölmesi, Öklid, alt-sonuç algoritması; buradaki $A$, $B$ örneği).
- George E. Collins, "Subresultants and Reduced Polynomial Remainder Sequences", *Journal of the ACM*, 14(1), 1967.
- W. S. Brown, "On Euclid's Algorithm and the Computation of Polynomial Greatest Common Divisors", *Journal of the ACM*, 18(4), 1971.
- Keith Geddes, Stephen Czapor, George Labahn, *Algorithms for Computer Algebra*, Bölüm 7 (PRS'ler) ve Bölüm 7.4 (modüler EBOB).
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra*, Bölüm 6 (sonuç ve alt-sonuçlar) ve Bölüm 14 (karesiz çarpanlara ayırma).

**Sıradaki ders:** FFT ile hızlı çarpma. Karmaşık köklerle FFT, NTT (sayı-teorik dönüşüm), polinom ve büyük sayı çarpımına uygulama.
