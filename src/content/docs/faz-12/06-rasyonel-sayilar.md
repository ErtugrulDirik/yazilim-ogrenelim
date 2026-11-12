---
title: "12.6 Rasyonel sayılar"
description: "Büyük tamsayı çiftiyle kesin kesir tipi: kanonik biçim (payda pozitif, EBOB 1, sıfır 0/1) ve her işlemden sonra Öklid ile sadeleştirme; Python Fraction'a karşı 20000 vektörde sınama; Hilbert sistemini kesin Gauss eliminasyonuyla çözmek (n = 40'ta bile çözüm tam 1, double ile hata 362'ye kadar), det(H_n)'nin kapalı formülle doğrulanması; tamsayı determinantında üç yol: bölmesiz eleme (n = 15'te 2588 limb), Bareiss (n = 80'de 21 limb) ve kesirli Gauss (aynı sonuç, 100 kat yavaş); Hadamard sınırı ve n! σ^(2n) tahmini; SymPy ile doğrulama."
---

Ders 12.1'de Python'un `Fraction`'ı ile Hilbert sistemini tam çözmüştük: `double` 15.2 hata verirken kesirler tam 1 bulmuştu. `Fraction`'ın içinde iki `int` ve bir EBOB var. Bu derste aynısını kendi büyük tamsayılarımızla kuruyor, sonra kesin lineer cebirin asıl problemine bakıyoruz: sayıların ara adımlarda ne kadar büyüdüğü.

---

## 1. Temsil ve kanonik biçim

Bir rasyonel sayı $p/q$, ama $1/2 = 2/4 = -3/{-6}$. Aynı sayının tek bir yazılışı olsun istiyoruz, çünkü eşitlik testi o zaman tamsayı karşılaştırmasına iniyor ve sayılar gereksiz büyümüyor. **Kanonik biçim**:

- $q > 0$ (işaret payda),
- $\gcd(p, q) = 1$,
- sıfır her zaman $0/1$.

```c
/* rat.h: kesin rasyonel sayi p/q. Degismez: q > 0, ebob(p, q) = 1, sifir 0/1 */
#ifndef RAT_H
#define RAT_H
#include "bn.h"

typedef struct { bn p, q; } rat;

void rat_baslat(rat *x);
void rat_sil(rat *x);
void rat_kopyala(rat *r, const rat *a);
void rat_tam(rat *r, int64_t v);                 /* r = v / 1 */
void rat_kesir(rat *r, int64_t p, int64_t q);    /* r = p / q, sadelestirilir */
void rat_topla(rat *r, const rat *a, const rat *b);
void rat_cikar(rat *r, const rat *a, const rat *b);
void rat_carp(rat *r, const rat *a, const rat *b);
void rat_bol(rat *r, const rat *a, const rat *b); /* b != 0 */
int  rat_kars(const rat *a, const rat *b);
int  rat_sifir_mi(const rat *a);
char *rat_yaz(const rat *a);                     /* "-3/4" ya da "5"; free ile birak */
int  rat_oku(rat *r, const char *s);             /* "-3/4" ya da "5" */
size_t rat_basamak(const rat *a);                /* pay ve paydanin toplam limb sayisi */
#endif
```

İşlemler okul formülleri: $\frac ab + \frac cd = \frac{ad + cb}{bd}$, $\frac ab \cdot \frac cd = \frac{ac}{bd}$. Her birinden sonra `sadelestir` çağrılıyor: EBOB'u bul (Ders 12.5'teki `bn_ebob`, Öklid), iki tarafı da ona böl.

```c
/* rat.c: her islemden sonra EBOB ile sadelestirilen kesirler */
#include <stdlib.h>
#include <string.h>
#include "bn.h"
#include "bn_mod.h"
#include "rat.h"

void rat_baslat(rat *x) { bn_baslat(&x->p); bn_baslat(&x->q); bn_u64(&x->q, 1); }
void rat_sil(rat *x) { bn_sil(&x->p); bn_sil(&x->q); }
void rat_kopyala(rat *r, const rat *a) { bn_kopyala(&r->p, &a->p); bn_kopyala(&r->q, &a->q); }

static void bn_i64(bn *x, int64_t v) {
    bn_u64(x, v < 0 ? 0 - (uint64_t)v : (uint64_t)v);
    x->isaret = v < 0 && x->n;
}

/* p/q'yu kanonik yap: payda pozitif, EBOB 1 */
static void sadelestir(rat *r) {
    if (r->q.isaret) { r->q.isaret = 0; r->p.isaret = r->p.n ? !r->p.isaret : 0; }
    if (r->p.n == 0) { bn_u64(&r->q, 1); return; }
    bn g; bn_baslat(&g);
    bn_ebob(&g, &r->p, &r->q);
    if (!(g.n == 1 && g.d[0] == 1)) {
        bn_bol(&r->p, 0, &r->p, &g);
        bn_bol(&r->q, 0, &r->q, &g);
    }
    bn_sil(&g);
}

void rat_tam(rat *r, int64_t v) { bn_i64(&r->p, v); bn_u64(&r->q, 1); }
void rat_kesir(rat *r, int64_t p, int64_t q) { bn_i64(&r->p, p); bn_i64(&r->q, q); sadelestir(r); }

/* a/b + c/d = (ad + cb) / bd */
static void topla_cikar(rat *r, const rat *a, const rat *b, int cikar) {
    rat t; bn u; rat_baslat(&t); bn_baslat(&u);
    bn_carp(&t.p, &a->p, &b->q);
    bn_carp(&u, &b->p, &a->q);
    if (cikar) bn_cikar(&t.p, &t.p, &u); else bn_topla(&t.p, &t.p, &u);
    bn_carp(&t.q, &a->q, &b->q);
    sadelestir(&t);
    rat_sil(r); *r = t; bn_sil(&u);                 /* r, a ya da b olabilir */
}
void rat_topla(rat *r, const rat *a, const rat *b) { topla_cikar(r, a, b, 0); }
void rat_cikar(rat *r, const rat *a, const rat *b) { topla_cikar(r, a, b, 1); }

void rat_carp(rat *r, const rat *a, const rat *b) {
    rat t; rat_baslat(&t);
    bn_carp(&t.p, &a->p, &b->p);
    bn_carp(&t.q, &a->q, &b->q);
    sadelestir(&t);
    rat_sil(r); *r = t;
}

void rat_bol(rat *r, const rat *a, const rat *b) {
    rat t; rat_baslat(&t);
    bn_carp(&t.p, &a->p, &b->q);
    bn_carp(&t.q, &a->q, &b->p);                    /* isaret sadelestir'de paya gecer */
    sadelestir(&t);
    rat_sil(r); *r = t;
}

int rat_kars(const rat *a, const rat *b) {          /* a/b ? c/d  <=>  ad ? cb (paydalar pozitif) */
    bn x, y; bn_baslat(&x); bn_baslat(&y);
    bn_carp(&x, &a->p, &b->q); bn_carp(&y, &b->p, &a->q);
    int k = bn_kars(&x, &y);
    bn_sil(&x); bn_sil(&y);
    return k;
}

int rat_sifir_mi(const rat *a) { return a->p.n == 0; }
size_t rat_basamak(const rat *a) { return a->p.n + a->q.n; }

char *rat_yaz(const rat *a) {
    char *p = bn_ondaliga(&a->p);
    if (a->q.n == 1 && a->q.d[0] == 1) return p;
    char *q = bn_ondaliga(&a->q), *s = malloc(strlen(p) + strlen(q) + 2);
    strcpy(s, p); strcat(s, "/"); strcat(s, q);
    free(p); free(q);
    return s;
}

int rat_oku(rat *r, const char *s) {
    const char *b = strchr(s, '/');
    if (!b) { bn_u64(&r->q, 1); return bn_ondaliktan(&r->p, s); }
    char *pay = malloc(b - s + 1);
    memcpy(pay, s, b - s); pay[b - s] = 0;
    int h = bn_ondaliktan(&r->p, pay) || bn_ondaliktan(&r->q, b + 1) || r->q.n == 0;
    free(pay);
    if (!h) sadelestir(r);
    return h ? -1 : 0;
}
```

Karşılaştırma bölme istemiyor: paydalar pozitif olduğundan $\frac ab < \frac cd \iff ad < cb$.

Sadeleştirmenin bir maliyeti var: EBOB, $n$ limb'lik sayılar için $O(n^2)$ ve sabiti çarpmadan büyük (her Öklid adımı bir Algoritma D bölmesi). Daha akıllı formüller var. Henrici'nin toplaması, $g = \gcd(b, d)$'yi önce bulup daha küçük sayılarla çalışıyor; GMP'nin `mpq_add`'ı böyle. Alıştırma 2 bunun üzerine.

---

## 2. Sınama

`uret.py`'nin yeni `kesir` modu, Python'un `Fraction`'ı ile rastgele kesirler ve dört işlemin sonucunu üretiyor. Pay ve paydalar 5000 bite kadar çıkıyor, yani sonuç metinleri binlerce basamak. `uret.py`'nin başına `sys.set_int_max_str_digits(0)` ekledik (Ders 12.4).

```c
/* sina_rat.c: dort islem ve karsilastirma, Python'un Fraction'i ile */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rat.h"

static char sat[7][40000];
static long hata;
static void kontrol(const rat *x, const char *beklenen, const char *ne) {
    char *s = rat_yaz(x);
    if (strcmp(s, beklenen)) { hata++; if (hata < 5) printf("%s: %.60s...\n", ne, beklenen); }
    free(s);
}

int main(void) {
    long satir = 0;
    rat a, b, r; rat_baslat(&a); rat_baslat(&b); rat_baslat(&r);
    while (scanf("%39999s %39999s %39999s %39999s %39999s %39999s %39999s", sat[0], sat[1], sat[2], sat[3], sat[4], sat[5], sat[6]) == 7) {
        satir++;
        rat_oku(&a, sat[0]); rat_oku(&b, sat[1]);
        rat_topla(&r, &a, &b); kontrol(&r, sat[2], "topla");
        rat_cikar(&r, &a, &b); kontrol(&r, sat[3], "cikar");
        rat_carp(&r, &a, &b);  kontrol(&r, sat[4], "carp");
        if (strcmp(sat[5], "-")) { rat_bol(&r, &a, &b); kontrol(&r, sat[5], "bol"); }
        if (rat_kars(&a, &b) != atoi(sat[6])) hata++;
        rat_topla(&a, &a, &a);                       /* takma ad: r = a */
        rat_cikar(&a, &a, &b); rat_topla(&a, &a, &b);
        rat_cikar(&a, &a, &a);
        if (!rat_sifir_mi(&a)) hata++;
    }
    printf("%ld satir, %ld hata\n", satir, hata);
    return 0;
}
```

```
$ python3 uret.py kesir 7 20000 > v_kesir.txt
$ clang -O2 -c rat.c && clang -O2 sina_rat.c bn_*.o rat.o -o sina_rat
$ ./sina_rat < v_kesir.txt
20000 satir, 0 hata
```

Karşılaştırma doğrudan **metinle** yapılıyor: `rat_yaz` ile Python'un çıktısı aynı karakter dizisi olmalı. Bu ancak iki taraf da aynı kanonik biçimi kullanıyorsa mümkün, kanonik biçimin bir faydası daha. Son dört satır takma ad (`r == a`) durumunu ve $a - a = 0$'ı sınıyor.

---

## 3. Kesin Gauss eliminasyonu

Ders 6.26'daki Gauss eliminasyonunu `double` yerine `rat` ile yazıyoruz. Kesin aritmetikte pivot seçimi doğruluk için değil, yalnız sıfıra bölmemek için gerekli: sıfır olmayan ilk eleman yetiyor. Kayan noktada en büyük elemanı seçmek (kısmi pivotlama) hatayı sınırlamak içindi; burada hata yok.

```c
/* gauss.c: Hilbert sistemi H x = b, b = H (1, 1, ..., 1): kesin ve double */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>
#include "olcum.h"
#include "rat.h"

static size_t en_buyuk;                              /* ara degerlerdeki en buyuk limb sayisi */

/* A: n x (n+1) genisletilmis matris, yerinde. Cozum A[i][n]'de. det doner. */
static void gauss_rat(rat *A, int n, rat *det) {
    rat c, t; rat_baslat(&c); rat_baslat(&t);
    rat_tam(det, 1);
    for (int k = 0; k < n; k++) {
        int p = k;                                   /* sifir olmayan ilk pivot yeter: hata yok */
        while (p < n && rat_sifir_mi(&A[p * (n + 1) + k])) p++;
        if (p == n) { rat_tam(det, 0); return; }
        if (p != k) {
            for (int j = 0; j <= n; j++) { rat s = A[k * (n + 1) + j]; A[k * (n + 1) + j] = A[p * (n + 1) + j]; A[p * (n + 1) + j] = s; }
            det->p.isaret = det->p.n ? !det->p.isaret : 0;
        }
        rat_carp(det, det, &A[k * (n + 1) + k]);
        for (int i = k + 1; i < n; i++) {            /* satir_i -= (a_ik / a_kk) satir_k */
            rat_bol(&c, &A[i * (n + 1) + k], &A[k * (n + 1) + k]);
            for (int j = k; j <= n; j++) {
                rat_carp(&t, &c, &A[k * (n + 1) + j]);
                rat_cikar(&A[i * (n + 1) + j], &A[i * (n + 1) + j], &t);
                size_t b = rat_basamak(&A[i * (n + 1) + j]);
                if (b > en_buyuk) en_buyuk = b;
            }
        }
    }
    for (int i = n - 1; i >= 0; i--) {               /* geri yerine koyma */
        for (int j = i + 1; j < n; j++) {
            rat_carp(&t, &A[i * (n + 1) + j], &A[j * (n + 1) + n]);
            rat_cikar(&A[i * (n + 1) + n], &A[i * (n + 1) + n], &t);
        }
        rat_bol(&A[i * (n + 1) + n], &A[i * (n + 1) + n], &A[i * (n + 1) + i]);
    }
    rat_sil(&c); rat_sil(&t);
}

static double gauss_double(int n) {                  /* kismi pivotlu, en buyuk hata doner */
    double *A = malloc(sizeof(double) * n * (n + 1));
    for (int i = 0; i < n; i++) {
        double s = 0;
        for (int j = 0; j < n; j++) { A[i * (n + 1) + j] = 1.0 / (i + j + 1); s += A[i * (n + 1) + j]; }
        A[i * (n + 1) + n] = s;
    }
    for (int k = 0; k < n; k++) {
        int p = k;
        for (int i = k + 1; i < n; i++) if (fabs(A[i * (n + 1) + k]) > fabs(A[p * (n + 1) + k])) p = i;
        for (int j = 0; j <= n; j++) { double s = A[k * (n + 1) + j]; A[k * (n + 1) + j] = A[p * (n + 1) + j]; A[p * (n + 1) + j] = s; }
        for (int i = k + 1; i < n; i++) {
            double c = A[i * (n + 1) + k] / A[k * (n + 1) + k];
            for (int j = k; j <= n; j++) A[i * (n + 1) + j] -= c * A[k * (n + 1) + j];
        }
    }
    double hata = 0;
    for (int i = n - 1; i >= 0; i--) {
        for (int j = i + 1; j < n; j++) A[i * (n + 1) + n] -= A[i * (n + 1) + j] * A[j * (n + 1) + n];
        A[i * (n + 1) + n] /= A[i * (n + 1) + i];
        if (fabs(A[i * (n + 1) + n] - 1) > hata) hata = fabs(A[i * (n + 1) + n] - 1);
    }
    free(A);
    return hata;
}

int main(void) {
    int ns[] = { 5, 10, 14, 20, 30, 40 };
    printf("  n   double hatasi   kesin: cozum     en buyuk ara deger   1/det basamak      sure\n");
    for (int z = 0; z < 6; z++) {
        int n = ns[z];
        rat *A = malloc(sizeof(rat) * n * (n + 1)), t, det;
        rat_baslat(&t); rat_baslat(&det);
        for (int i = 0; i < n; i++) {
            rat_tam(&A[i * (n + 1) + n], 0);
            for (int j = 0; j < n; j++) {
                rat_baslat(&A[i * (n + 1) + j]);
                rat_kesir(&A[i * (n + 1) + j], 1, i + j + 1);
                rat_topla(&A[i * (n + 1) + n], &A[i * (n + 1) + n], &A[i * (n + 1) + j]);
            }
        }
        en_buyuk = 0;
        double t0 = simdi();
        gauss_rat(A, n, &det);
        double t1 = simdi();
        int hepsi_bir = 1;
        rat_tam(&t, 1);
        for (int i = 0; i < n; i++) if (rat_kars(&A[i * (n + 1) + n], &t)) hepsi_bir = 0;
        char *ds = bn_ondaliga(&det.q);
        printf("%3d   %13.3g   %-14s %8zu limb (~%5.0f bas.) %10zu   %8.2f ms\n", n, gauss_double(n),
               hepsi_bir ? "hepsi tam 1" : "YANLIS", en_buyuk, en_buyuk * 9.63, strlen(ds), (t1 - t0) * 1e3);
        if (n == 5) { char *s = rat_yaz(&det); printf("      det(H_5) = %s\n", s); free(s); }
        free(ds);
        for (int i = 0; i < n * (n + 1); i++) rat_sil(&A[i]);
        free(A); rat_sil(&t); rat_sil(&det);
    }
    return 0;
}
```

```
$ clang -O2 gauss.c bn_*.o rat.o -o gauss && ./gauss
  n   double hatasi   kesin: cozum     en buyuk ara deger   1/det basamak      sure
  5        8.24e-13   hepsi tam 1           2 limb (~   19 bas.)         12       0.12 ms
      det(H_5) = 1/266716800000
 10        0.000377   hepsi tam 1           3 limb (~   29 bas.)         53       0.96 ms
 14            15.2   hepsi tam 1           4 limb (~   39 bas.)        108       3.03 ms
 20            30.6   hepsi tam 1           5 limb (~   48 bas.)        226      10.47 ms
 30             362   hepsi tam 1           7 limb (~   67 bas.)        519      30.30 ms
 40            56.3   hepsi tam 1          10 limb (~   96 bas.)        932      56.97 ms
```

- **`double` sütunu**: Ders 12.1'deki 15.2 burada da. Kısmi pivotlama bile kurtarmıyor, çünkü sorun algoritmada değil, matriste. $H_{14}$'ün koşul sayısı $1.9 \times 10^{19}$ (mpmath ile 80 basamak hassasiyetle hesapladım), $n$ ile yaklaşık $e^{3.5n}$ hızında büyüyor. `double`'ın 16 basamaklık hassasiyeti ise çoktan aşıldı. Bu noktadan sonra çıkan sayılar anlamsız; 30'da 362, 40'ta 56 olması da rastgele.
- **Kesin sütun**: $n = 40$'ta bile çözüm tam 1. Süre 57 ms.
- **Determinant**: $\det H_n = c_n^4 / c_{2n}$, $c_n = \prod_{i=0}^{n-1} i!$ formülü bilinen bir sonuç (Hilbert matrisi bir Cauchy matrisi). Python'la formülden hesaplanan paydaların basamak sayıları: 12, 53, 108, 226, 519, 932. Tablodakiyle aynı ve $n = 5$'te $1/266716800000$.

```
$ python3 -c "
import math; from fractions import Fraction as F
c = lambda k: math.prod(math.factorial(i) for i in range(k))
for n in (5, 10, 14, 20, 30, 40): print(n, len(str(F(c(n)**4, c(2*n)).denominator)))"
5 12
10 53
...
40 932
```

Ara değerler şaşırtıcı derecede küçük: $n = 40$'ta en büyüğü 10 limb, determinantın paydası 932 basamak olsa bile. Bu Hilbert matrisine özgü değil. Sadeleştirilmiş kesirli Gauss'ta her ara eleman, özgün matrisin iki alt determinantının (minörünün) oranı. Minörler de matrisin boyutu ve elemanlarıyla sınırlı (bir sonraki bölümde Hadamard sınırı). Sadeleştirme olmasa ne olurdu?

---

## 4. Ara değer şişmesi: üç yol

Elemanları $[-99, 99]$ aralığında rastgele tamsayılar olan bir matrisin determinantı. Kesir hiç kullanmadan da Gauss yapılabilir.

1. **Bölmesiz eleme.** $\text{satır}_i \leftarrow a_{kk} \cdot \text{satır}_i - a_{ik} \cdot \text{satır}_k$. Hep tamsayı, ama her adımda sayılar yaklaşık **iki katı** uzunluğa çıkıyor (iki tamsayının çarpımı).
2. **Bareiss** (1968). Aynı adımdan sonra bir önceki pivota bölmek. Sylvester'in determinant özdeşliği bu bölmenin **her zaman tam** olduğunu söylüyor. $k$. adımdan sonraki her eleman, özgün matrisin $(k+1) \times (k+1)$'lik bir minörü. Son pivot doğrudan determinant.
3. **Kesirli Gauss**, bizim `rat`'ımızla.

```c
/* bareiss.c: tamsayi matrisin determinanti uc yolla: kesirli Gauss, bolmesiz eleme, Bareiss */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "olcum.h"
#include "rat.h"
#include "bn_mod.h"

static size_t en_buyuk;
static void olc(const bn *x) { if (x->n > en_buyuk) en_buyuk = x->n; }

static int pivot_bul(bn *A, int n, int k) {         /* sifir olmayan pivot; satir degisimi sayisi doner */
    int p = k;
    while (p < n && A[p * n + k].n == 0) p++;
    if (p == n) return -1;
    if (p != k) for (int j = 0; j < n; j++) { bn s = A[k * n + j]; A[k * n + j] = A[p * n + j]; A[p * n + j] = s; }
    return p != k;
}

/* 1. bolmesiz: satir_i = a_kk satir_i - a_ik satir_k. det = pivotlarin carpimi / (pivot^(n-1-k) carpimi) */
static void bolmesiz(bn *A, int n, bn *det) {
    bn t, u, bolen; bn_baslat(&t); bn_baslat(&u); bn_baslat(&bolen);
    bn_u64(&bolen, 1);
    int isaret = 0;
    for (int k = 0; k < n - 1; k++) {
        int d = pivot_bul(A, n, k);
        if (d < 0) { bn_u64(det, 0); return; }
        isaret ^= d;
        for (int i = k + 1; i < n; i++) {
            for (int j = k + 1; j < n; j++) {
                bn_carp(&t, &A[k * n + k], &A[i * n + j]);
                bn_carp(&u, &A[i * n + k], &A[k * n + j]);
                bn_cikar(&A[i * n + j], &t, &u); olc(&A[i * n + j]);
            }
            bn_u64(&A[i * n + k], 0);
        }
        for (int i = k + 1; i < n; i++) bn_carp(&bolen, &bolen, &A[k * n + k]);       /* alttaki n-1-k satir a_kk ile carpildi */
    }
    bn_kopyala(det, &A[n * n - 1]);
    for (int k = 0; k < n - 1; k++) bn_carp(det, det, &A[k * n + k]);
    bn_bol(det, &t, det, &bolen);                    /* kalan sifir olmali */
    if (t.n) printf("bolmesiz: kalan sifir degil!\n");
    if (isaret) det->isaret = det->n ? !det->isaret : 0;
    bn_sil(&t); bn_sil(&u); bn_sil(&bolen);
}

/* 2. Bareiss: ayni adim, sonra onceki pivota TAM bol (Sylvester ozdesligi) */
static void bareiss(bn *A, int n, bn *det) {
    bn t, u, onceki, kalan; bn_baslat(&t); bn_baslat(&u); bn_baslat(&onceki); bn_baslat(&kalan);
    bn_u64(&onceki, 1);
    int isaret = 0;
    for (int k = 0; k < n - 1; k++) {
        int d = pivot_bul(A, n, k);
        if (d < 0) { bn_u64(det, 0); return; }
        isaret ^= d;
        for (int i = k + 1; i < n; i++) {
            for (int j = k + 1; j < n; j++) {
                bn_carp(&t, &A[k * n + k], &A[i * n + j]);
                bn_carp(&u, &A[i * n + k], &A[k * n + j]);
                bn_cikar(&t, &t, &u);
                bn_bol(&A[i * n + j], &kalan, &t, &onceki);
                if (kalan.n) printf("Bareiss: tam bolunmedi!\n");
                olc(&A[i * n + j]);
            }
            bn_u64(&A[i * n + k], 0);
        }
        bn_kopyala(&onceki, &A[k * n + k]);
    }
    bn_kopyala(det, &A[n * n - 1]);                  /* son pivot = det */
    if (isaret) det->isaret = det->n ? !det->isaret : 0;
    bn_sil(&t); bn_sil(&u); bn_sil(&onceki); bn_sil(&kalan);
}

/* 3. kesirli Gauss: pivotlarin carpimi */
static void kesirli(const bn *B, int n, bn *det) {
    rat *A = malloc(sizeof(rat) * n * n), c, t, d;
    rat_baslat(&c); rat_baslat(&t); rat_baslat(&d); rat_tam(&d, 1);
    for (int i = 0; i < n * n; i++) { rat_baslat(&A[i]); bn_kopyala(&A[i].p, &B[i]); }
    for (int k = 0; k < n; k++) {
        int p = k;
        while (p < n && rat_sifir_mi(&A[p * n + k])) p++;
        if (p == n) { rat_tam(&d, 0); break; }
        if (p != k) { for (int j = 0; j < n; j++) { rat s = A[k * n + j]; A[k * n + j] = A[p * n + j]; A[p * n + j] = s; } d.p.isaret ^= 1; }
        rat_carp(&d, &d, &A[k * n + k]);
        for (int i = k + 1; i < n; i++) {
            rat_bol(&c, &A[i * n + k], &A[k * n + k]);
            for (int j = k; j < n; j++) {
                rat_carp(&t, &c, &A[k * n + j]);
                rat_cikar(&A[i * n + j], &A[i * n + j], &t);
                if (rat_basamak(&A[i * n + j]) > en_buyuk) en_buyuk = rat_basamak(&A[i * n + j]);
            }
        }
    }
    bn_kopyala(det, &d.p);                           /* payda 1 olmali */
    for (int i = 0; i < n * n; i++) rat_sil(&A[i]);
    free(A); rat_sil(&c); rat_sil(&t); rat_sil(&d);
}

int main(void) {
    uint64_t s = 7;
    int ns[] = { 5, 10, 15, 20, 40, 80 };
    FILE *f = fopen("bareiss_kontrol.txt", "w");
    printf("  n  yol          en buyuk ara deger      sure    det basamak\n");
    for (int z = 0; z < 6; z++) {
        int n = ns[z];
        bn *M = malloc(sizeof(bn) * n * n), *A = malloc(sizeof(bn) * n * n), det, ref;
        bn_baslat(&det); bn_baslat(&ref);
        for (int i = 0; i < n * n; i++) {            /* [-99, 99] */
            bn_baslat(&M[i]); bn_baslat(&A[i]);
            int64_t v = (int64_t)(rastgele64(&s) % 199) - 99;
            bn_u64(&M[i], v < 0 ? -v : v); M[i].isaret = v < 0;
        }
        int sira[] = { 1, 0, 2 };                    /* once Bareiss: digerleri onunla karsilastirilir */
        for (int z2 = 0; z2 < 3; z2++) {
            int y = sira[z2];
            if (y == 0 && n > 15) continue;          /* bolmesiz yol buyuk n'de bitmez */
            for (int i = 0; i < n * n; i++) bn_kopyala(&A[i], &M[i]);
            en_buyuk = 0;
            double t0 = simdi();
            if (y == 0) bolmesiz(A, n, &det);
            if (y == 1) bareiss(A, n, &det);
            if (y == 2) kesirli(M, n, &det);
            double t1 = simdi();
            if (y == 1) bn_kopyala(&ref, &det);
            char *ds = bn_ondaliga(&det);
            printf("%3d  %-10s %10zu limb %12.2f ms   %4zu  %s\n", n, y == 0 ? "bolmesiz" : y == 1 ? "Bareiss" : "kesirli",
                   en_buyuk, (t1 - t0) * 1e3, strlen(ds) - (det.isaret ? 1 : 0), y == 1 ? "" : bn_kars(&det, &ref) ? "FARKLI" : "Bareiss ile ayni");
            if (y == 1) {                            /* SymPy kontrolu icin */
                fprintf(f, "%d %s\n", n, ds);
                for (int i = 0; i < n * n; i++) { char *e = bn_ondaliga(&M[i]); fprintf(f, "%s%c", e, i % n == n - 1 ? '\n' : ' '); free(e); }
            }
            free(ds);
        }
        for (int i = 0; i < n * n; i++) { bn_sil(&M[i]); bn_sil(&A[i]); }
        free(M); free(A); bn_sil(&det); bn_sil(&ref);
    }
    fclose(f);
    return 0;
}
```

```
$ clang -O2 bareiss.c bn_*.o rat.o -o bareiss && ./bareiss
  n  yol          en buyuk ara deger      sure    det basamak
  5  Bareiss             1 limb         0.02 ms      9
  5  bolmesiz            3 limb         0.02 ms      9  Bareiss ile ayni
  5  kesirli             2 limb         0.15 ms      9  Bareiss ile ayni
 10  Bareiss             3 limb         0.10 ms     22
 10  bolmesiz          105 limb         0.25 ms     22  Bareiss ile ayni
 10  kesirli             5 limb         2.29 ms     22  Bareiss ile ayni
 15  Bareiss             4 limb         0.40 ms     32
 15  bolmesiz         2588 limb        27.61 ms     32  Bareiss ile ayni
 15  kesirli             8 limb         7.07 ms     32  Bareiss ile ayni
 20  Bareiss             5 limb         0.70 ms     44
 20  kesirli            10 limb        22.76 ms     44  Bareiss ile ayni
 40  Bareiss            10 limb         5.57 ms     94
 40  kesirli            20 limb       295.56 ms     94  Bareiss ile ayni
 80  Bareiss            21 limb        60.23 ms    199
 80  kesirli            42 limb      5975.26 ms    199  Bareiss ile ayni
```

- **Bölmesiz**: 10'dan 15'e çıkınca ara değerler 105'ten 2588 limb'e çıkıyor. Üstel büyüme: $n = 20$'de birkaç yüz bin limb, $n = 40$'ta evrendeki atomlardan fazla bit. Sonuç (32 basamak) küçük olsa bile ara adımlar devleşiyor.
- **Bareiss**: ara değerler determinant boyutunda kalıyor ve en hızlısı.
- **Kesirli**: Bareiss'in iki katı limb (pay ve payda), ama **100 kat** yavaş. Ara değerler küçük ama her işlemde bir EBOB, yani her işlemde bir Öklid döngüsü var. Kesin aritmetiğin asıl maliyeti genelde aritmetik değil, sadeleştirme.

SymPy ile bağımsız kontrol (program matrisleri ve Bareiss determinantını `bareiss_kontrol.txt`'ye yazıyor):

```
$ python3 -c "
from sympy import Matrix
L = open('bareiss_kontrol.txt').read().split('\n'); i = 0
while i < len(L) and L[i]:
    n, d = L[i].split(); n = int(n)
    M = Matrix([[int(x) for x in L[i + 1 + r].split()] for r in range(n)])
    print(n, M.det(method='berkowitz' if n <= 40 else 'bareiss') == int(d)); i += n + 1"
5 True
10 True
15 True
20 True
40 True
80 True
```

($n \le 40$ için SymPy'nin Berkowitz yöntemi, bambaşka bir algoritma, aynı sonucu buluyor.)

**Determinant ne kadar büyük olabilir?** Hadamard eşitsizliği: $|\det A| \le \prod_i \lVert a_i \rVert$, satır normlarının çarpımı. Elemanlar en fazla 99 ise $\lVert a_i \rVert \le 99\sqrt n$; $n = 80$ için $\log_{10}(99 \sqrt{80})^{80} \approx 236$ basamak. Bu en kötü durum. Rastgele matrisler için $E[\det^2] = n! \, \sigma^{2n}$ ($\sigma^2$ elemanların varyansı, $[-99, 99]$ düzgün dağılımında $\sigma \approx 57.4$). Bu da $\log_{10} \sqrt{80!} + 80 \log_{10} 57.4 \approx 59.4 + 140.7 = 200$ basamak veriyor. Ölçtüğümüz: 199.

---

## 5. Ne öğrendik

Kesin hesabın üç kuralı, bu fazın geri kalanında da geçerli:

1. **Kanonik biçim** olmadan eşitlik testi bile zor. Biçim ne kadar "sıkı" olursa (EBOB = 1), sayılar o kadar küçük kalıyor.
2. **Ara değer şişmesi** son sonucun boyutuyla ilgisiz olabilir. Bölmesiz eleme 32 basamaklık bir determinant için 25000 basamaklık sayılar üretti.
3. **Tam bölmeyi bilmek** (Bareiss), hem kesirlerden hem şişmeden kurtarıyor. Ders 12.8'de polinom EBOB'unda aynı üç yolu göreceğiz: kesirli Öklid, bölmesiz (*pseudo*-bölme) ve alt-sonuç dizisi. Orada da kazanan, Bareiss'in fikrini taşıyan yol.

---

## Alıştırmalar

**1** – `rat_kars`'ın yaptığı iki çarpma pahalı. Önce işaretlere, sonra $\lfloor p/q \rfloor$'lara bakan bir hızlı yol ekle. Hangi durumlarda yine çarpma gerekir?

**2** – Henrici toplaması: $g = \gcd(b, d)$, $b' = b/g$, $d' = d/g$. $t = a d' + c b'$, $g_2 = \gcd(t, g)$. Sonuç $\frac{t / g_2}{b' d' (g / g_2)}$. Bunun neden zaten sadeleşmiş olduğunu göster ve `rat_topla`'yı böyle yaz. Hangi EBOB'lar küçük sayılarla yapılıyor?

**3** – Harmonik toplam $H_{1000} = \sum_{k=1}^{1000} 1/k$'yi `rat` ile hesapla. Paydanın basamak sayısını Python'la karşılaştır. Payda, $\text{EKOK}(1, \dots, 1000)$'e eşit mi?

**4** – Bölmesiz elemede adım $k$'den sonra elemanların kabaca kaç bitlik olacağını özyinelemeli yaz: $b_{k+1} \approx 2 b_k$. $b_0 = 7$ bitle $n = 10$ ve $n = 15$ için tahmini, tablodaki 105 ve 2588 limb ile karşılaştır.

**5** – Bareiss'in son pivotunun determinant olduğu bilgisini kullanarak, Ders 12.1'deki genel $6 \times 6$ determinantın 720 terimli olduğunu hatırla. Bareiss kaç tamsayı çarpması yapar? $n!$ terimin hepsini açmaktan neden bu kadar ucuz?

<details>
<summary>Cevaplar</summary>

**1** – İşaretler farklıysa sonuç hemen belli. Aynıysa tam kısımları ($\lfloor p/q \rfloor$, bir bölme) karşılaştır. Farklıysalar bitti. Eşitse kalanlarla devam etmek gerekiyor: $r_1/q_1$ ile $r_2/q_2$, bu da yine çapraz çarpma ya da sürekli kesir açılımıyla adım adım karşılaştırma. Pratikte önce bit uzunluğu tahmini ($\log_2 |p| - \log_2 q$) çoğu durumu tek bakışta ayırıyor; çarpma yalnız değerler çok yakınsa gerekiyor.

**2** – $\gcd(t, b'd') = 1$: $t \equiv a d' \pmod {b'}$ ve $\gcd(a, b) = 1$, $\gcd(d', b') = 1$ olduğundan $t$, $b'$ ile aralarında asal; aynısı $d'$ için. Kalan tek ortak çarpan $g$'den gelebilir, onu da $g_2$ alıyor. EBOB'lar $b, d$ (girdi boyutu) ve $t, g$ ($g$ çoğu zaman küçük) arasında. Sonucun tamamı ile bir EBOB hiç yok. Rastgele kesirlerde $g$ genelde 1 ya da küçük olduğundan ikinci EBOB neredeyse bedava.

**3** – Python: `sum(Fraction(1, k) for k in range(1, 1001)).denominator` 433 basamak ve $n = 1000$ için $\text{EKOK}(1, \dots, 1000)$'e **eşit**. Ama her $n$ için değil: $H_6 = 49/20$, oysa $\text{EKOK}(1..6) = 60$. Payın 3'e bölünmesi paydadaki bir 3'ü götürüyor. $n \le 1000$ arasında bu tür sadeleşmenin olduğu 855 değer var, yani eşitlik kural değil istisna (ilkleri: 6, 7, 8, 18, 19, 20). Kendi `rat` sonucunu Python'unkiyle karakter karakter karşılaştır.

**4** – $b_k \approx 2^k b_0$ (her adımda iki $b_k$ bitlik sayının çarpımı ve küçük bir toplama). $n = 10$: $n - 1 = 9$ adım, $2^9 \times 7 \approx 3600$ bit $\approx 112$ limb. $n = 15$: $2^{14} \times 7 \approx 115000$ bit $\approx 3600$ limb. Ölçülen 105 ve 2588; tahmin üst sınır, çünkü $a_{kk} a_{ij} - a_{ik} a_{kj}$'de baştaki bitler kısmen birbirini götürüyor.

**5** – Adım $k$'de $(n-1-k)^2$ eleman, her biri iki çarpma ve bir bölme: toplam yaklaşık $\frac{2}{3} n^3$ çarpma. $n = 6$ için yaklaşık 110 çarpma (ve 55 tam bölme), oysa açılım $720 \times 5 = 3600$ çarpma. Determinant, $n!$ terimin toplamı olarak tanımlansa da, satır işlemleri ara sonuçları paylaştırarak her minörü bir kez hesaplıyor: dinamik programlama (Ders 9.11) ile aynı ilke.

</details>

---

## Kaynaklar

- Erwin H. Bareiss, "Sylvester's Identity and Multistep Integer-Preserving Gaussian Elimination", *Mathematics of Computation*, 22(103), 1968.
- Donald Knuth, *TAOCP*, Cilt 2, §4.5.1 (kesirler, Henrici'nin formülleri) ve §4.5.2 (Öklid algoritması).
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra* (3. baskı), Bölüm 5 (modüler algoritmalar ve kesin lineer cebir).
- Man-Duen Choi, "Tricks or Treats with the Hilbert Matrix", *The American Mathematical Monthly*, 90(5), 1983.
- GMP belgeleri, "Rational Number Functions" ve "Rational Internals" bölümleri (gmplib.org/manual).

**Sıradaki ders:** Polinom aritmetiği. Yoğun ve seyrek temsil, toplama, çarpma, Horner yöntemi ile değerlendirme.
