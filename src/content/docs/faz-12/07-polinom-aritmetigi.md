---
title: "12.7 Polinom aritmetiği"
description: "Rasyonel katsayılı yoğun polinom tipi (katsayı dizisi, baştaki sıfırlar atılmış kanonik biçim); toplama, çıkarma, okul çarpması ve Python'a karşı 5000 vektörde sınama; Horner yöntemi ve (x - 1)^10'un açık halinin x = 1.0001'de double ile -2.3e-15, kesin olarak 10^-40 çıkması; seyrek temsil ((üs, katsayı) çiftleri, sırala ve birleştir), f^2'nin derece 38 milyonda bile 0.03 ms sürmesi; Kronecker yerine koyması ile polinom çarpımını tek bir büyük tamsayı çarpımına çevirmek ve Karatsuba'yı bedavaya kullanmak."
---

Büyük tamsayılar ve kesirler bitti; bir CAS'ın asıl nesnesi polinomlar. $3x^2 - x + \tfrac12$ bir sayı değil ama sayılar gibi toplanıyor, çarpılıyor, bölünüyor (Ders 6.23: $\mathbb{Q}[x]$ bir halka). Bu derste temsili ve dört işlemin üçünü yazıyoruz. Bölme ve EBOB Ders 12.8'de.

---

## 1. Yoğun temsil

Bir polinom, katsayılarının dizisi: `c[i]`, $x^i$'nin katsayısı. Büyük tamsayıdaki limb dizisinin aynısı, tek fark taban yok ve **elde yok**. $x^i$ ile $x^{i+1}$ birbirine taşmıyor, her katsayı istediği kadar büyüyebilir. Kanonik biçim de aynı fikir: baştaki sıfırları at, sıfır polinomun derecesi $-1$ (bazı kitaplarda $-\infty$).

Katsayılar `rat`: $\mathbb{Q}[x]$. $\mathbb{Z}[x]$ de içinde, paydalar 1 olur. $\mathbb{Q}$'yu seçmemizin nedeni Ders 12.8: bölme bir cisim ister, $\mathbb{Z}$'de $x^2 / 2x$ yapılamaz.

```c
/* poli.h: rasyonel katsayili yogun polinom. c[i], x^i'nin katsayisi.
   Degismez: n = derece + 1, c[n-1] != 0; sifir polinom n = 0 */
#ifndef POLI_H
#define POLI_H
#include "rat.h"

typedef struct { rat *c; size_t n, kap; } poli;

void poli_baslat(poli *p);
void poli_sil(poli *p);
void poli_kopyala(poli *r, const poli *a);
void poli_yer(poli *p, size_t n);                    /* en az n katsayi, yenileri 0 */
void poli_duzelt(poli *p);                           /* bastaki sifirlari at */
void poli_ayarla(poli *p, size_t i, int64_t pay, int64_t payda);
int  poli_derece(const poli *p);                     /* sifir polinom icin -1 */
void poli_topla(poli *r, const poli *a, const poli *b);
void poli_cikar(poli *r, const poli *a, const poli *b);
void poli_carp(poli *r, const poli *a, const poli *b);
void poli_skaler(poli *r, const poli *a, const rat *k);
void poli_horner(rat *r, const poli *p, const rat *x);
int  poli_esit(const poli *a, const poli *b);
char *poli_yaz(const poli *p, const char *x);       /* "3*x^2 - x + 1/2" */
int  poli_oku(poli *p, const char *s);               /* "c0,c1,c2,..." */

/* poli_bol.c */
void poli_bol(poli *q, poli *r, const poli *a, const poli *b);   /* b != 0; q ya da r NULL olabilir */
void poli_monik(poli *r, const poli *a);                         /* bas katsayi 1 */
void poli_ebob(poli *g, const poli *a, const poli *b);          /* Q uzerinde Oklid, monik sonuc */
void poli_icerik(rat *c, const poli *a);                         /* katsayilarin EBOB'u (Q'da: ebob(paylar)/ekok(paydalar)) */
void poli_ilkel(poli *r, const poli *a);                         /* a / icerik, bas katsayi pozitif */
void poli_prem(poli *r, const poli *a, const poli *b);          /* lc(b)^(da - db + 1) a mod b */
size_t poli_basamak(const poli *a);                              /* en buyuk katsayinin ondalik basamak sayisi (pay + payda) */
#endif
```

```c
/* poli.c: yogun polinom aritmetigi, Q[x] */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "poli.h"

void poli_baslat(poli *p) { p->c = 0; p->n = p->kap = 0; }
void poli_sil(poli *p) {
    for (size_t i = 0; i < p->kap; i++) rat_sil(&p->c[i]);
    free(p->c); poli_baslat(p);
}
void poli_yer(poli *p, size_t n) {
    if (n > p->kap) {
        p->c = realloc(p->c, n * sizeof(rat));
        for (size_t i = p->kap; i < n; i++) rat_baslat(&p->c[i]);
        p->kap = n;
    }
    for (size_t i = p->n; i < n; i++) rat_tam(&p->c[i], 0);
    if (n > p->n) p->n = n;
}
void poli_duzelt(poli *p) { while (p->n && rat_sifir_mi(&p->c[p->n - 1])) p->n--; }
int  poli_derece(const poli *p) { return (int)p->n - 1; }

void poli_kopyala(poli *r, const poli *a) {
    if (r == a) return;
    r->n = 0; poli_yer(r, a->n);
    for (size_t i = 0; i < a->n; i++) rat_kopyala(&r->c[i], &a->c[i]);
}

void poli_ayarla(poli *p, size_t i, int64_t pay, int64_t payda) {
    if (i >= p->n) poli_yer(p, i + 1);
    rat_kesir(&p->c[i], pay, payda);
    poli_duzelt(p);
}

static void topla_cikar(poli *r, const poli *a, const poli *b, int cikar) {
    poli t; poli_baslat(&t);
    poli_yer(&t, a->n > b->n ? a->n : b->n);
    for (size_t i = 0; i < t.n; i++) {
        if (i < a->n) rat_kopyala(&t.c[i], &a->c[i]);
        if (i < b->n) { if (cikar) rat_cikar(&t.c[i], &t.c[i], &b->c[i]); else rat_topla(&t.c[i], &t.c[i], &b->c[i]); }
    }
    poli_duzelt(&t);
    poli_sil(r); *r = t;                             /* r, a ya da b olabilir */
}
void poli_topla(poli *r, const poli *a, const poli *b) { topla_cikar(r, a, b, 0); }
void poli_cikar(poli *r, const poli *a, const poli *b) { topla_cikar(r, a, b, 1); }

/* okul carpmasi: (sum a_i x^i)(sum b_j x^j) = sum_k (sum_{i+j=k} a_i b_j) x^k */
void poli_carp(poli *r, const poli *a, const poli *b) {
    poli t; poli_baslat(&t);
    if (a->n && b->n) {
        rat u; rat_baslat(&u);
        poli_yer(&t, a->n + b->n - 1);
        for (size_t i = 0; i < a->n; i++) {
            if (rat_sifir_mi(&a->c[i])) continue;
            for (size_t j = 0; j < b->n; j++) {
                rat_carp(&u, &a->c[i], &b->c[j]);
                rat_topla(&t.c[i + j], &t.c[i + j], &u);
            }
        }
        rat_sil(&u);
        poli_duzelt(&t);                             /* Q'da sifir bolen yok: gerek yok, ama zarari yok */
    }
    poli_sil(r); *r = t;
}

void poli_skaler(poli *r, const poli *a, const rat *k) {
    poli_kopyala(r, a);
    for (size_t i = 0; i < r->n; i++) rat_carp(&r->c[i], &r->c[i], k);
    poli_duzelt(r);
}

/* Horner: p(x) = c0 + x (c1 + x (c2 + ... )): n - 1 carpma, n - 1 toplama */
void poli_horner(rat *r, const poli *p, const rat *x) {
    rat t; rat_baslat(&t);
    for (size_t i = p->n; i-- > 0;) { rat_carp(&t, &t, x); rat_topla(&t, &t, &p->c[i]); }
    rat_sil(r); *r = t;
}

int poli_esit(const poli *a, const poli *b) {
    if (a->n != b->n) return 0;
    for (size_t i = 0; i < a->n; i++) if (rat_kars(&a->c[i], &b->c[i])) return 0;
    return 1;
}

/* buyuk dereceden kucuge; katsayi 1 ise yazilmaz, eksiler " - " ile */
char *poli_yaz(const poli *p, const char *x) {
    if (p->n == 0) { char *s = malloc(2); strcpy(s, "0"); return s; }
    size_t kap = 64, uz = 0;
    char *s = malloc(kap);
    s[0] = 0;
    for (size_t i = p->n; i-- > 0;) {
        const rat *c = &p->c[i];
        if (rat_sifir_mi(c)) continue;
        int eksi = c->p.isaret;
        rat m; rat_baslat(&m); rat_kopyala(&m, c); m.p.isaret = 0;
        char *k = rat_yaz(&m);
        int bir = strcmp(k, "1") == 0;
        char us[32] = "";
        if (i == 1) snprintf(us, sizeof us, "%s", x);
        else if (i > 1) snprintf(us, sizeof us, "%s^%zu", x, i);
        size_t gerek = uz + strlen(k) + strlen(us) + 8;
        if (gerek > kap) { while (kap < gerek) kap *= 2; s = realloc(s, kap); }
        const char *on = uz == 0 ? (eksi ? "-" : "") : (eksi ? " - " : " + ");
        if (i == 0) uz += snprintf(s + uz, kap - uz, "%s%s", on, k);
        else if (bir) uz += snprintf(s + uz, kap - uz, "%s%s", on, us);
        else uz += snprintf(s + uz, kap - uz, "%s%s*%s", on, k, us);
        free(k); rat_sil(&m);
    }
    return s;
}

int poli_oku(poli *p, const char *s) {
    p->n = 0;
    size_t i = 0;
    char buf[65536];
    while (*s) {
        const char *v = strchr(s, ',');
        size_t uz = v ? (size_t)(v - s) : strlen(s);
        if (uz >= sizeof buf) return -1;
        memcpy(buf, s, uz); buf[uz] = 0;
        poli_yer(p, i + 1);
        if (rat_oku(&p->c[i], buf)) return -1;
        i++;
        s += uz + (v ? 1 : 0);
    }
    poli_duzelt(p);
    return 0;
}
```

`poli_carp` iki iç içe döngü: $a_i b_j$, $x^{i+j}$'ye ekleniyor. Bu, Ders 12.3'teki okul çarpmasıyla aynı iskelet, elde satırı eksik. $O(nm)$ katsayı çarpması, her biri bir `rat_carp` ve bir `rat_topla`, yani EBOB'lar. Dış döngüdeki `continue`, sıfır katsayıları atlıyor: seyrek polinomlarda önemli olacak.

---

## 2. Sınama

`uret.py`'ye `poli` modu: katsayı listeleri Python'un `Fraction`'larıyla. Bazı katsayılar sıfır, bazıları 300 bitlik, bazıları küçük kesir. Python tarafında polinom çarpması iki satırlık bir döngü; değerlendirme `sum(c * x**i)`. Horner'dan bağımsız bir yöntem.

```c
/* sina_poli.c: toplama, cikarma, carpma ve Horner, Python'un Fraction listeleri ile */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "poli.h"

static char sat[7][200000];

int main(void) {
    long satir = 0, hata = 0;
    poli a, b, r, beklenen; poli_baslat(&a); poli_baslat(&b); poli_baslat(&r); poli_baslat(&beklenen);
    rat x, d, e; rat_baslat(&x); rat_baslat(&d); rat_baslat(&e);
    while (scanf("%199999s %199999s %199999s %199999s %199999s %199999s %199999s", sat[0], sat[1], sat[2], sat[3], sat[4], sat[5], sat[6]) == 7) {
        satir++;
        poli_oku(&a, sat[0]); poli_oku(&b, sat[1]);
        poli_topla(&r, &a, &b); poli_oku(&beklenen, sat[2]); if (!poli_esit(&r, &beklenen)) hata++;
        poli_cikar(&r, &a, &b); poli_oku(&beklenen, sat[3]); if (!poli_esit(&r, &beklenen)) hata++;
        poli_carp(&r, &a, &b);  poli_oku(&beklenen, sat[4]); if (!poli_esit(&r, &beklenen)) hata++;
        rat_oku(&x, sat[5]); rat_oku(&e, sat[6]);
        poli_horner(&d, &a, &x); if (rat_kars(&d, &e)) hata++;
        poli_carp(&a, &a, &a);                           /* takma ad */
    }
    printf("%ld satir, %ld hata\n", satir, hata);
    poli_oku(&a, "1/2,-1,0,3");
    char *s = poli_yaz(&a, "x"); printf("ornek: %s\n", s); free(s);
    return 0;
}
```

```
$ python3 uret.py poli 8 5000 > v_poli.txt
$ clang -O2 -c poli.c && clang -O2 sina_poli.c bn_*.o rat.o poli.o -o sina_poli
$ ./sina_poli < v_poli.txt
5000 satir, 0 hata
ornek: 3*x^3 - x + 1/2
```

---

## 3. Horner yöntemi

$p(x) = c_0 + c_1 x + \dots + c_n x^n$'yi doğrudan hesaplamak $x$'in kuvvetlerini ister: her terim için bir çarpma daha, toplam $2n$ çarpma. Horner iç içe yazıyor:

$$p(x) = c_0 + x\,(c_1 + x\,(c_2 + \dots + x\,(c_{n-1} + x\, c_n)))$$

$n$ çarpma ve $n$ toplama, ve kanıtlanmış en az: genel bir polinom için daha azı yapılamaz (Ostrowski 1954, Pan 1966). Ders 3.17'deki `atoi` aynı döngüydü: `n = n * 10 + basamak`, $x = 10$ için Horner.

Kesin aritmetikte Horner sadece hız. Kayan noktada ise başka bir şey ortaya çıkıyor:

```c
/* horner.c: (x - 1)^10'un acik hali, x = 1.0001'de: double ve kesin */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "poli.h"

int main(void) {
    poli p, x1; poli_baslat(&p); poli_baslat(&x1);
    poli_ayarla(&p, 0, 1, 1);
    poli_ayarla(&x1, 0, -1, 1); poli_ayarla(&x1, 1, 1, 1);         /* x - 1 */
    for (int i = 0; i < 10; i++) poli_carp(&p, &p, &x1);
    char *s = poli_yaz(&p, "x"); printf("p(x) = %s\n", s); free(s);

    double xd = 1.0001, horner = 0, duz = 0;
    for (size_t i = p.n; i-- > 0;) {
        char *t = bn_ondaliga(&p.c[i].p);              /* katsayilar tamsayi */
        double c = atof(t); free(t);
        horner = horner * xd + c;
        duz += c * pow(xd, (double)i);
    }
    rat x, r; rat_baslat(&x); rat_baslat(&r);
    rat_kesir(&x, 10001, 10000);
    poli_horner(&r, &p, &x);
    char *k = rat_yaz(&r);
    printf("double, Horner      : %.6e\n", horner);
    printf("double, duz toplam  : %.6e\n", duz);
    printf("double, (x - 1)^10  : %.6e\n", pow(xd - 1, 10));
    printf("kesin               : %s\n", k);
    free(k); rat_sil(&x); rat_sil(&r); poli_sil(&p); poli_sil(&x1);
    return 0;
}
```

```
$ ./horner
p(x) = x^10 - 10*x^9 + 45*x^8 - 120*x^7 + 210*x^6 - 252*x^5 + 210*x^4 - 120*x^3 + 45*x^2 - 10*x + 1
double, Horner      : -2.304080e-15
double, duz toplam  : 1.376677e-14
double, (x - 1)^10  : 1.000000e-40
kesin               : 1/10000000000000000000000000000000000000000
```

Gerçek değer $10^{-40}$. İki `double` sonucu bunun $10^{25}$ katı ve biri **eksi**: anlamsız. Katsayılar 252'ye kadar çıkıyor, terimler birbirini götürüyor ve `double`'ın $10^{-16}$'lık bağıl hatası, $252 \times 10^{-16}$ civarında mutlak gürültü bırakıyor. Aynı polinom, **çarpanlı biçimde** yazılınca `double` ile de doğru çıkıyor.

Bu da Ders 12.1'in temasının bir örneği: aynı nesnenin farklı temsilleri (açık hal, çarpanlı hal) sayısal olarak hiç eşit değil. Bir CAS'ın `expand` ve `factor` ayrımı sadece okunabilirlik meselesi değil.

---

## 4. Seyrek temsil

$x^{1000000} + 1$ için yoğun temsil bir milyon katsayı tutuyor, ikisi dışında hepsi sıfır. **Seyrek** temsil yalnız sıfır olmayan terimleri tutuyor: (üs, katsayı) çiftleri, üse göre sıralı.

```c
/* seyrek.h: seyrek polinom: (us, katsayi) ciftleri, us'e gore artan, katsayilar sifir degil */
#ifndef SEYREK_H
#define SEYREK_H
#include "bn.h"

typedef struct { uint64_t us; bn k; } terim;
typedef struct { terim *t; size_t n; } seyrek;

void seyrek_baslat(seyrek *p);
void seyrek_sil(seyrek *p);
void seyrek_ekle(seyrek *p, uint64_t us, int64_t k);  /* sona ekler: us artan sirada verilmeli */
void seyrek_carp(seyrek *r, const seyrek *a, const seyrek *b);
#endif
```

Çarpma: bütün terim çiftlerini üret, üslerine göre sırala, aynı üsleri topla. $|a| |b|$ çarpım ve bir sıralama: maliyet terim sayısına bağlı, dereceye değil.

```c
/* seyrek.c: butun terim ciftlerini uret, us'e gore sirala, ayni usleri birlestir */
#include <stdlib.h>
#include "seyrek.h"

void seyrek_baslat(seyrek *p) { p->t = 0; p->n = 0; }
void seyrek_sil(seyrek *p) { for (size_t i = 0; i < p->n; i++) bn_sil(&p->t[i].k); free(p->t); seyrek_baslat(p); }

void seyrek_ekle(seyrek *p, uint64_t us, int64_t k) {
    p->t = realloc(p->t, (p->n + 1) * sizeof(terim));
    bn_baslat(&p->t[p->n].k);
    bn_u64(&p->t[p->n].k, k < 0 ? -(uint64_t)k : (uint64_t)k);
    p->t[p->n].k.isaret = k < 0;
    p->t[p->n++].us = us;
}

static int us_kars(const void *x, const void *y) {
    uint64_t a = ((const terim *)x)->us, b = ((const terim *)y)->us;
    return (a > b) - (a < b);
}

/* |a| |b| carpim, O(|a| |b| log(|a| |b|)); derece hic onemli degil */
void seyrek_carp(seyrek *r, const seyrek *a, const seyrek *b) {
    size_t m = a->n * b->n, k = 0;
    terim *t = malloc((m ? m : 1) * sizeof(terim));
    for (size_t i = 0; i < a->n; i++)
        for (size_t j = 0; j < b->n; j++) {
            bn_baslat(&t[k].k);
            bn_carp(&t[k].k, &a->t[i].k, &b->t[j].k);
            t[k++].us = a->t[i].us + b->t[j].us;
        }
    qsort(t, m, sizeof(terim), us_kars);
    size_t w = 0;                                     /* ayni usleri topla, sifirlari at */
    for (size_t i = 0; i < m;) {
        size_t j = i + 1;
        while (j < m && t[j].us == t[i].us) { bn_topla(&t[i].k, &t[i].k, &t[j].k); bn_sil(&t[j].k); j++; }
        if (t[i].k.n) t[w++] = t[i]; else bn_sil(&t[i].k);
        i = j;
    }
    seyrek_sil(r);
    r->t = t; r->n = w;
}
```

```c
/* seyrek_hiz.c: f = sum_{i<20} (i+1) x^(i k), f^2: yogun ve seyrek */
#include <stdio.h>
#include "olcum.h"
#include "poli.h"
#include "seyrek.h"

int main(void) {
    printf("      k   derece(f^2)   yogun: katsayi    sure     seyrek: terim    sure\n");
    for (uint64_t k = 1; k <= 1000000; k *= 10) {
        seyrek s, s2; seyrek_baslat(&s); seyrek_baslat(&s2);
        for (int i = 0; i < 20; i++) seyrek_ekle(&s, i * k, i + 1);
        double t0 = simdi(); seyrek_carp(&s2, &s, &s); double t1 = simdi();
        double yt = -1; size_t yn = 0;
        if (k <= 10000) {                             /* yogun: derece 38k'ya kadar her katsayi */
            poli p, p2; poli_baslat(&p); poli_baslat(&p2);
            for (int i = 0; i < 20; i++) poli_ayarla(&p, i * k, i + 1, 1);
            double u0 = simdi(); poli_carp(&p2, &p, &p); double u1 = simdi();
            yt = (u1 - u0) * 1e3; yn = p2.n;
            for (size_t i = 0, j = 0; i < p2.n; i++)  /* iki sonuc ayni mi */
                if (!rat_sifir_mi(&p2.c[i])) {
                    if (j >= s2.n || s2.t[j].us != i || bn_kars(&s2.t[j].k, &p2.c[i].p)) printf("FARKLI\n");
                    j++;
                }
            poli_sil(&p); poli_sil(&p2);
        }
        if (yt >= 0) printf("%7llu %12llu %15zu %9.2f ms %14zu %8.3f ms\n", (unsigned long long)k, (unsigned long long)(38 * k), yn, yt, s2.n, (t1 - t0) * 1e3);
        else         printf("%7llu %12llu %15s %12s %14zu %8.3f ms\n", (unsigned long long)k, (unsigned long long)(38 * k), "-", "-", s2.n, (t1 - t0) * 1e3);
        seyrek_sil(&s); seyrek_sil(&s2);
    }
    return 0;
}
```

```
$ clang -O2 -c seyrek.c && clang -O2 seyrek_hiz.c bn_*.o rat.o poli.o seyrek.o -o seyrek_hiz
$ ./seyrek_hiz
      k   derece(f^2)   yogun: katsayi    sure     seyrek: terim    sure
      1           38              39      0.43 ms             39    0.087 ms
     10          380             381      1.68 ms             39    0.060 ms
    100         3800            3801     16.62 ms             39    0.059 ms
   1000        38000           38001     72.87 ms             39    0.067 ms
  10000       380000          380001    546.03 ms             39    0.030 ms
 100000      3800000               -            -             39    0.035 ms
1000000     38000000               -            -             39    0.026 ms
```

$f$'nin 20 terimi var, $f^2$'nin 39. Seyrek çarpma hep 400 terim çarpımı yapıyor ve dereceden bağımsız. Yoğun çarpma, `continue` sayesinde $O(n^2)$ değil $O(20 \cdot n)$. Yine de sıfırları tutmanın ve toplamanın bedelini ödüyor: $k = 10000$'de yarım saniye. Sıfırları atlamasak 380000² / 2 iç adım olurdu, saatler.

Hangisi ne zaman? Tek değişkenli ve "dolu" polinomlarda (her derecede katsayı var) yoğun temsil daha hızlı: dizi, sıralama yok, cache dostu (Ders 7.26). Çok değişkenli polinomlarda neredeyse her zaman seyrek: $(x + y + z + 1)^{20}$'nin yoğun bir $21^3$'lük tablosunun çoğu boş. Gerçek sistemler ikisini birden tutuyor. SymPy'nin `Poly`'sinde yoğun tek değişkenli (`DUP`) ve seyrek çok değişkenli gösterimler var. Maple'ın polinom çekirdeği, Monagan ve Pearce'ın yığın (heap) tabanlı seyrek çarpmasını kullanıyor. Bizim "hepsini üret, sonra sırala" yöntemimiz $|a||b|$ terimi bellekte tutuyor. Yığın yöntemi ise terimleri üs sırasıyla teker teker üretiyor ve yalnız $|a|$ boyutunda bir yığın tutuyor.

---

## 5. Kronecker yerine koyması

Yoğun $\mathbb{Z}[x]$ çarpmasında bir hile var. Katsayıları negatif olmayan ve 20 bitten küçük iki polinom düşün. $x = 2^{b}$ koyarsak polinom tek bir büyük tamsayı oluyor:

$$a(2^b) = \sum a_i 2^{bi}$$

Katsayılar $b$ bitlik "yuvalara" oturuyor. Çarpım katsayıları da $b$ bitten küçükse, $a(2^b) \cdot b(2^b) = (ab)(2^b)$'nin yuvaları birbirine taşmıyor ve çarpımın katsayıları doğrudan okunuyor. Çarpım katsayısı en fazla $n \cdot 2^{20} \cdot 2^{20}$: $b = 41 + \log_2 n$ yeter.

Elimizde hızlı bir büyük tamsayı çarpması (Karatsuba) olduğundan, polinom çarpması onu **bedavaya** kullanıyor.

```c
/* kronecker.c: tamsayi katsayili polinom carpimini tek bir buyuk sayi carpimina cevirmek */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "olcum.h"
#include "bn.h"
#include "bn_mod.h"
#include "poli.h"

/* katsayilari b bitlik yuvalara koy: P = sum c_i 2^(b i) (c_i >= 0, c_i < 2^b) */
static void paketle(bn *P, const uint32_t *c, size_t n, unsigned b) {
    size_t limb = (n * b + 31) / 32 + 1;
    bn_yer(P, limb); memset(P->d, 0, limb * 4);
    for (size_t i = 0; i < n; i++) {
        size_t bit = i * b;
        uint64_t v = (uint64_t)c[i] << (bit % 32);    /* c_i < 2^32: en fazla iki limb'e yayilir */
        P->d[bit / 32] |= (uint32_t)v;
        P->d[bit / 32 + 1] |= (uint32_t)(v >> 32);
    }
    P->n = limb; P->isaret = 0; bn_duzelt(P);
}

/* b bitlik yuvalari geri oku (b <= 64) */
static void ac(uint64_t *c, size_t n, const bn *P, unsigned b) {
    for (size_t i = 0; i < n; i++) {
        size_t bit = i * b;
        unsigned __int128 v = 0;
        for (int k = 0; k < 4; k++) {
            size_t l = bit / 32 + k;
            if (l < P->n) v |= (unsigned __int128)P->d[l] << (32 * k);
        }
        v >>= bit % 32;
        c[i] = b == 64 ? (uint64_t)v : (uint64_t)v & ((1ull << b) - 1);
    }
}

int main(void) {
    uint64_t s = 3;
    printf("  derece   Kronecker (bn_carp)   poli_carp (rat)   uint64 okul   ayni mi\n");
    for (size_t n = 100; n <= 100000; n *= 10) {
        uint32_t *a = malloc(n * 4), *b = malloc(n * 4);
        for (size_t i = 0; i < n; i++) { a[i] = rastgele64(&s) & 0xfffff; b[i] = rastgele64(&s) & 0xfffff; }   /* 20 bit */
        /* carpim katsayisi < n 2^40: 40 + log2(n) + 1 bit yeter */
        unsigned yuva = 41 + (unsigned)(64 - __builtin_clzll(n));
        bn A, B, C; bn_baslat(&A); bn_baslat(&B); bn_baslat(&C);
        uint64_t *kr = malloc((2 * n - 1) * 8), *okul = calloc(2 * n - 1, 8);
        double t0 = simdi();
        paketle(&A, a, n, yuva); paketle(&B, b, n, yuva);
        bn_carp(&C, &A, &B);
        ac(kr, 2 * n - 1, &C, yuva);
        double t1 = simdi();
        for (size_t i = 0; i < n; i++)                    /* karsilastirma: makine tamsayilariyla okul */
            for (size_t j = 0; j < n; j++) okul[i + j] += (uint64_t)a[i] * b[j];
        double t2 = simdi();
        double pt = -1;
        if (n <= 1000) {
            poli p, q, r; poli_baslat(&p); poli_baslat(&q); poli_baslat(&r);
            for (size_t i = 0; i < n; i++) { poli_ayarla(&p, i, a[i], 1); poli_ayarla(&q, i, b[i], 1); }
            double u0 = simdi(); poli_carp(&r, &p, &q); pt = (simdi() - u0) * 1e3;
            poli_sil(&p); poli_sil(&q); poli_sil(&r);
        }
        int ayni = memcmp(kr, okul, (2 * n - 1) * 8) == 0;
        if (pt >= 0) printf("%8zu %14.3f ms %15.2f ms %11.3f ms   %s (yuva %u bit)\n", n - 1, (t1 - t0) * 1e3, pt, (t2 - t1) * 1e3, ayni ? "evet" : "HAYIR", yuva);
        else         printf("%8zu %14.3f ms %18s %11.3f ms   %s (yuva %u bit)\n", n - 1, (t1 - t0) * 1e3, "-", (t2 - t1) * 1e3, ayni ? "evet" : "HAYIR", yuva);
        free(a); free(b); free(kr); free(okul); bn_sil(&A); bn_sil(&B); bn_sil(&C);
    }
    return 0;
}
```

```
$ clang -O2 kronecker.c bn_*.o rat.o poli.o -o kronecker && ./kronecker
  derece   Kronecker (bn_carp)   poli_carp (rat)   uint64 okul   ayni mi
      99          0.052 ms           10.84 ms       0.003 ms   evet (yuva 48 bit)
     999          1.148 ms          443.78 ms       0.269 ms   evet (yuva 51 bit)
    9999         22.607 ms                  -      13.630 ms   evet (yuva 55 bit)
   99999        969.997 ms                  -    1911.928 ms   evet (yuva 58 bit)
```

- **`poli_carp` 400 kat yavaş.** Katsayı başına bir `rat` çarpması ve toplaması, ikisi de EBOB'lu. Kesir genelliğinin bedeli; Ders 12.6'daki "kesirli Gauss ile Bareiss" farkının aynısı. Katsayıların tamsayı olduğu bilindiğinde $\mathbb{Z}[x]$'e özel bir yol hep daha hızlı.
- **Makine tamsayısıyla okul çarpması** küçük derecede rakipsiz: tek bir `madd` ve derleyici döngüyü vektörleştiriyor (Ders 11.15). Ama $O(n^2)$: derece 10 kat artınca süre 100 kat artıyor. Kronecker, Karatsuba sayesinde 10 kat dereceye 20–40 kat süre harcıyor ve derece 100000'de **2 kat önde**.
- Kesişme noktası 10000 ile 100000 arasında. Ders 12.9'da FFT ile bu noktayı çok daha aşağı çekeceğiz.

Negatif katsayılar için yuvalar "dengeli" okunuyor (yuvanın üst yarısı eksi sayıları temsil ediyor ve bir sonraki yuvadan ödünç alınıyor). Çok değişkenli polinomlar için her değişkene ayrı bir yuva genişliği veriliyor. FLINT kütüphanesi $\mathbb{Z}[x]$ çarpmasının önemli bir kısmında Kronecker yerine koymasını kullanıyor; Harvey (2009) yöntemi dört farklı nokta seçerek iyileştirdi.

---

## Alıştırmalar

**1** – `poli_carp`'ı Karatsuba ile yaz (Ders 12.3'teki `mag_carp`'ın iskeleti). Katsayılar arasında elde olmadığından hangi adımlar sadeleşiyor? `rat` katsayılarla gerçekten hızlanır mı?

**2** – $p(x)$ ve $p'(x)$'i aynı anda hesaplayan bir Horner yaz: bir döngüde iki birikimci. Newton yönteminde neden işe yarar?

**3** – `seyrek_carp`'ın belleği $|a| \cdot |b|$ terim. $|a| = |b| = 10^4$ terimli iki polinom için kaç terim, kaç bayt? Monagan–Pearce yığın yönteminin bellek kullanımı ne olurdu?

**4** – Kronecker'i **negatif** katsayılar için genişlet. İpucu: yuvayı $[-2^{b-1}, 2^{b-1})$ olarak oku; bir yuva eksi çıkarsa $2^b$ ekle ve bir sonraki yuvadan 1 çıkar.

**5** – $(x - 1)^{10}$'u `double` ile $x = 1.0001$'de Horner ile hesaplarken hatanın büyüklüğünü kabaca tahmin et: katsayıların mutlak değerlerinin toplamı $\sum |c_i| = 2^{10}$ ve bağıl hassasiyet $2^{-53}$. Ölçtüğümüz $10^{-15}$–$10^{-14}$ ile uyumlu mu?

<details>
<summary>Cevaplar</summary>

**1** – $a = a_1 x^m + a_0$, $b = b_1 x^m + b_0$ ve üç çarpım $a_0 b_0$, $a_1 b_1$, $(a_0 + a_1)(b_0 + b_1)$. Sayılardaki gibi toplamlarda taşma limb'i (`sa[a1n]`) ve sonda `ekle` ile elde yayılımı yok, katsayılar doğrudan toplanıyor. Ama `rat` ile her toplama da EBOB'lu bir işlem: Karatsuba çarpma sayısını $n^{1.58}$'e indiriyor, toplama sayısını ise artırıyor. Kesir katsayılarda kazanç ancak çok büyük derecede görünür. Pratikte önce ortak paydayı dışarı çekip $\mathbb{Z}[x]$'te çarpmak çok daha iyi.

**2** – `q = 0, p = 0; for i in n..0: q = q*x + p; p = p*x + c[i]`. Döngü bitince `p` $= p(x)$, `q` $= p'(x)$. Newton adımı $x \leftarrow x - p(x)/p'(x)$ ikisini de ister. Tek geçiş, $2n$ çarpma, türevi ayrıca hesaplamaya gerek yok.

**3** – $10^8$ terim. Her terim 8 bayt üs + 24 bayt `bn` başlığı + katsayının limb'leri (en az 16 bayt, `bn_yer`'in başlangıç kapasitesi): $10^8 \times 48 \approx 4.8$ GB. Yığın yöntemi aynı anda $|a| = 10^4$ aday tutuyor (her $a_i$ için "sıradaki $b_j$"), yani birkaç yüz KB, ve sonucu sırayla doğrudan yazıyor.

**4** – Paketlerken eksi katsayıyı yuvasına $2^b + c_i$ olarak yaz, bir üst yuvadan 1 çıkar (ya da $a(2^b)$'yi işaretli bir büyük sayı olarak toplamla kur: `bn_topla` ödüncü kendisi halleder). Açarken her yuvayı oku, $\ge 2^{b-1}$ ise $2^b$ çıkar ve bir sonraki yuvaya 1 ekle. Yuva genişliğini de bir bit artır: çarpım katsayısı artık $[-n 2^{40}, n 2^{40}]$.

**5** – Horner'ın hata sınırı kabaca $2n \cdot u \cdot \sum |c_i| |x|^i$, $u = 2^{-53} \approx 1.1 \times 10^{-16}$. $\sum |c_i| \cdot 1.0001^i \approx 2^{10} \approx 1024$, $2n = 20$: $20 \times 1.1 \times 10^{-16} \times 1024 \approx 2.3 \times 10^{-12}$. Ölçtüğümüz $2.3 \times 10^{-15}$ bu sınırın çok altında: sınır en kötü durum, hatalar birbirini kısmen götürüyor. Sonuç yine de gerçek değerden ($10^{-40}$) 25 basamak büyük.

</details>

---

## Kaynaklar

- Donald Knuth, *TAOCP*, Cilt 2, §4.6 (polinom aritmetiği) ve §4.6.4 (polinom değerlendirme, Horner'ın en iyiliği).
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra*, Bölüm 2 (temel aritmetik) ve §8.4 (Kronecker yerine koyması).
- Michael Monagan ve Roman Pearce, "Sparse Polynomial Division Using a Heap", *Journal of Symbolic Computation*, 46(7), 2011.
- David Harvey, "Faster Polynomial Multiplication via Multipoint Kronecker Substitution", *Journal of Symbolic Computation*, 44(10), 2009.
- Nicholas Higham, *Accuracy and Stability of Numerical Algorithms* (2. baskı), Bölüm 5 (Horner yönteminin hata analizi).

**Sıradaki ders:** Polinom bölmesi ve EBOB. Polinom uzun bölmesi, polinomlar üzerinde Öklid algoritması, katsayı şişmesi problemi.
