---
title: "12.10 Sonlu cisim üzerinde polinomlar"
description: "GF(p)[x]: katsayıların tek limb'lik mod p sayılar olduğu, elde ve şişmenin hiç olmadığı polinom aritmetiği; Fermat ile ters, uzun bölme, Öklid, polinomun kuvveti mod f; x^(p^n) - x'in derecesi n'yi bölen bütün indirgenemezlerin çarpımı olması ve Rabin'in indirgenemezlik testi; GF(2), GF(3) ve GF(5)'te bütün monik polinomları deneyip Gauss–Möbius formülüyle birebir aynı sayıyı bulmak; CRC'nin tam olarak M(x) x^32 mod G(x) olduğunu ve standart CRC-32'nin 0xCBF43926'sını polinom kalanından türetmek; derecelere göre ayırma ile CRC-8, CRC-16, CRC-32, CRC-32C ve CRC-64'ün çarpanları, CRC-32'nin indirgenemez ve ilkel olması."
---

Ders 12.8 polinom EBOB'unu katsayı şişmesiyle bitirdi ve gerçek sistemlerin bunu **mod $p$'de** hesaplayarak çözdüğünü söyledi. Ders 6.24'te $GF(2^8)$'i $GF(2)[x]$'in bir indirgenemez polinoma göre kalanları olarak kurmuştuk. Ders 5.19'da CRC'yi "bir polinom bölmesi" diye anlatmıştık. Üçü de aynı yapıyı kullanıyor: **katsayıları bir sonlu cisimde olan polinomlar**, $GF(p)[x]$. Bu derste o yapıyı yazıp üç soruyu cevaplıyoruz: bir polinom indirgenemez mi, kaç tane indirgenemez polinom var, ve CRC tam olarak neyi hesaplıyor.

---

## 1. Aritmetik

$GF(p)[x]$, Ders 12.7–12.8'deki $\mathbb{Q}[x]$ ile aynı algoritmalar. Tek fark katsayılar: `rat` yerine $[0, p)$ aralığında bir `uint64_t`. Bunun sonuçları büyük:

- **Şişme yok.** Her katsayı, ne kadar işlem yapılırsa yapılsın, tek bir makine sözcüğü. Ders 12.8'deki 1.7 milyon basamak burada olamaz.
- **Bölme her zaman mümkün.** $GF(p)$ bir cisim: $a^{-1} = a^{p-2}$ (Fermat, Ders 6.20). Polinom uzun bölmesi $\mathbb{Q}[x]$'teki gibi çalışıyor.
- **Hız.** $p < 2^{32}$ ise iki katsayının çarpımı 64 bite sığıyor, `%` ile indirgeniyor.

```c
/* gfp.h: GF(p)[x], p < 2^32 asal. c[i] in [0, p), n = derece + 1, c[n-1] != 0 */
#ifndef GFP_H
#define GFP_H
#include <stdint.h>

typedef struct { uint64_t *c; int n; } gpol;

void gp_baslat(gpol *a);
void gp_sil(gpol *a);
void gp_kopyala(gpol *r, const gpol *a);
void gp_ayarla(gpol *a, const uint64_t *c, int n, uint64_t p);  /* katsayilar mod p */
int  gp_derece(const gpol *a);
int  gp_esit(const gpol *a, const gpol *b);
void gp_cikar(gpol *r, const gpol *a, const gpol *b, uint64_t p);
void gp_carp(gpol *r, const gpol *a, const gpol *b, uint64_t p);
void gp_bol(gpol *q, gpol *r, const gpol *a, const gpol *f, uint64_t p);   /* a = q f + r */
void gp_mod(gpol *r, const gpol *a, const gpol *f, uint64_t p);   /* a mod f */
void gp_ddf(const gpol *f, uint64_t p, int *say);                /* say[k]: derece k indirgenemez carpan sayisi (f karesiz) */
void gp_ebob(gpol *g, const gpol *a, const gpol *b, uint64_t p);  /* monik */
void gp_usmod(gpol *r, const gpol *a, uint64_t e, const gpol *f, uint64_t p);   /* a^e mod f */
int  gp_indirgenemez(const gpol *f, uint64_t p);                 /* Rabin testi */
uint64_t gp_ters(uint64_t a, uint64_t p);
#endif
```

```c
/* gfp.c: sonlu cisim uzerinde polinomlar. Katsayi aritmetigi tek limb: elde yok, sisme yok */
#include <stdlib.h>
#include <string.h>
#include "gfp.h"

void gp_baslat(gpol *a) { a->c = 0; a->n = 0; }
void gp_sil(gpol *a) { free(a->c); gp_baslat(a); }
static void duzelt(gpol *a) { while (a->n && a->c[a->n - 1] == 0) a->n--; }
static void yer(gpol *a, int n) { a->c = realloc(a->c, (n ? n : 1) * 8); memset(a->c, 0, (n ? n : 1) * 8); a->n = n; }
int gp_derece(const gpol *a) { return a->n - 1; }

void gp_kopyala(gpol *r, const gpol *a) {
    if (r == a) return;
    yer(r, a->n); memcpy(r->c, a->c, a->n * 8);
}
void gp_ayarla(gpol *a, const uint64_t *c, int n, uint64_t p) {
    yer(a, n);
    for (int i = 0; i < n; i++) a->c[i] = c[i] % p;
    duzelt(a);
}
int gp_esit(const gpol *a, const gpol *b) { return a->n == b->n && !memcmp(a->c, b->c, a->n * 8); }

/* Fermat: a^(p-2) = a^-1 (Ders 6.20) */
uint64_t gp_ters(uint64_t a, uint64_t p) {
    uint64_t r = 1, e = p - 2;
    for (; e; e >>= 1, a = a * a % p) if (e & 1) r = r * a % p;
    return r;
}

void gp_cikar(gpol *r, const gpol *a, const gpol *b, uint64_t p) {
    gpol t; gp_baslat(&t);
    yer(&t, a->n > b->n ? a->n : b->n);
    for (int i = 0; i < t.n; i++) {
        uint64_t x = i < a->n ? a->c[i] : 0, y = i < b->n ? b->c[i] : 0;
        t.c[i] = x >= y ? x - y : x + p - y;
    }
    duzelt(&t);
    gp_sil(r); *r = t;
}

void gp_carp(gpol *r, const gpol *a, const gpol *b, uint64_t p) {
    gpol t; gp_baslat(&t);
    if (a->n && b->n) {
        yer(&t, a->n + b->n - 1);
        for (int i = 0; i < a->n; i++)
            for (int j = 0; j < b->n; j++) t.c[i + j] = (t.c[i + j] + a->c[i] * b->c[j]) % p;   /* < 2^64: p < 2^32 */
        duzelt(&t);
    }
    gp_sil(r); *r = t;
}

/* a = q f + r; q NULL olabilir */
void gp_bol(gpol *q, gpol *r, const gpol *a, const gpol *f, uint64_t p) {
    gpol t, tq; gp_baslat(&t); gp_baslat(&tq); gp_kopyala(&t, a);
    yer(&tq, a->n >= f->n ? a->n - f->n + 1 : 0);
    uint64_t ters = gp_ters(f->c[f->n - 1], p);
    while (t.n >= f->n) {                            /* bas terimi yok et */
        uint64_t k = t.c[t.n - 1] * ters % p;
        int s = t.n - f->n;
        tq.c[s] = k;
        for (int i = 0; i < f->n; i++) t.c[i + s] = (t.c[i + s] + (p - f->c[i]) * k) % p;
        duzelt(&t);
    }
    duzelt(&tq);
    if (q) { gp_sil(q); *q = tq; } else gp_sil(&tq);
    gp_sil(r); *r = t;
}
void gp_mod(gpol *r, const gpol *a, const gpol *f, uint64_t p) { gp_bol(0, r, a, f, p); }

void gp_ebob(gpol *g, const gpol *a, const gpol *b, uint64_t p) {
    gpol x, y, r; gp_baslat(&x); gp_baslat(&y); gp_baslat(&r);
    gp_kopyala(&x, a); gp_kopyala(&y, b);
    while (y.n) { gp_mod(&r, &x, &y, p); gp_sil(&x); x = y; y = r; gp_baslat(&r); }
    if (x.n) { uint64_t t = gp_ters(x.c[x.n - 1], p); for (int i = 0; i < x.n; i++) x.c[i] = x.c[i] * t % p; }
    gp_sil(g); *g = x; gp_sil(&y);
}

/* kare al ve carp, her adimda mod f: derece hep < der f */
void gp_usmod(gpol *r, const gpol *a, uint64_t e, const gpol *f, uint64_t p) {
    gpol x, b; gp_baslat(&x); gp_baslat(&b);
    uint64_t bir = 1;
    gp_ayarla(&x, &bir, 1, p);
    gp_mod(&b, a, f, p);
    for (; e; e >>= 1) {
        if (e & 1) { gp_carp(&x, &x, &b, p); gp_mod(&x, &x, f, p); }
        gp_carp(&b, &b, &b, p); gp_mod(&b, &b, f, p);
    }
    gp_sil(r); *r = x; gp_sil(&b);
}

/* x^(p^k) mod f: k kez p. kuvvet (p^k 64 bite sigmayabilir) */
static void x_p_k(gpol *r, int k, const gpol *f, uint64_t p) {
    uint64_t xc[2] = { 0, 1 };
    gp_ayarla(r, xc, 2, p);
    for (int i = 0; i < k; i++) gp_usmod(r, r, p, f, p);
}

/* Rabin (1980): der f = n icin f indirgenemez <=>
   x^(p^n) = x (mod f) ve n'nin her asal boleni q icin ebob(x^(p^(n/q)) - x, f) = 1 */
int gp_indirgenemez(const gpol *f, uint64_t p) {
    int n = gp_derece(f);
    if (n < 1) return 0;
    gpol t, x, g; gp_baslat(&t); gp_baslat(&x); gp_baslat(&g);
    uint64_t xc[2] = { 0, 1 };
    gp_ayarla(&x, xc, 2, p);
    int sonuc = 1;
    for (int q = 2, m = n; m > 1 && sonuc; q++) {    /* n'nin asal bolenleri */
        if (m % q) continue;
        while (m % q == 0) m /= q;
        x_p_k(&t, n / q, f, p);
        gp_cikar(&t, &t, &x, p);
        gp_ebob(&g, &t, f, p);
        if (g.n != 1) sonuc = 0;                     /* ortak carpan: n/q dereceyi bolen bir carpan var */
    }
    if (sonuc) {
        x_p_k(&t, n, f, p);
        gpol xm; gp_baslat(&xm); gp_mod(&xm, &x, f, p);
        sonuc = gp_esit(&t, &xm);
        gp_sil(&xm);
    }
    gp_sil(&t); gp_sil(&x); gp_sil(&g);
    return sonuc;
}

/* derecelere gore ayirma (distinct-degree factorization): x^(p^k) - x, derecesi k'yi bolen
   butun monik indirgenemezlerin carpimi. ebob(x^(p^k) - x, f), f'nin derece k carpanlarini toplar */
void gp_ddf(const gpol *f, uint64_t p, int *say) {
    gpol g, h, x, t, kalan; gp_baslat(&g); gp_baslat(&h); gp_baslat(&x); gp_baslat(&t); gp_baslat(&kalan);
    uint64_t xc[2] = { 0, 1 };
    gp_ayarla(&x, xc, 2, p);
    gp_kopyala(&kalan, f);
    gp_mod(&h, &x, &kalan, p);                       /* h = x^(p^k) mod kalan */
    for (int k = 1; 2 * k <= gp_derece(&kalan); k++) {
        gp_usmod(&h, &h, p, &kalan, p);
        gp_cikar(&t, &h, &x, p);
        gp_ebob(&g, &t, &kalan, p);
        if (g.n > 1) {
            say[k] = gp_derece(&g) / k;
            gp_bol(&kalan, &t, &kalan, &g, p);
            gp_mod(&h, &h, &kalan, p);
        }
    }
    if (gp_derece(&kalan) > 0) say[gp_derece(&kalan)]++;   /* geriye kalan tek bir indirgenemez */
    gp_sil(&g); gp_sil(&h); gp_sil(&x); gp_sil(&t); gp_sil(&kalan);
}
```

`gp_usmod`, Ders 12.5'teki kare al ve çarp, ama tabanı bir polinom ve modu $f$. Ara sonuçların derecesi hep $< \deg f$, işlem sayısı $O(\log e)$ polinom çarpması.

---

## 2. İndirgenemezlik: $x^{p^n} - x$

Sonlu cisimlerin temel teoremi (Ders 6.24'te $GF(2^n)$ için kurduğumuz yapının genel hali):

$$x^{p^n} - x = \prod \{\, f \text{ monik, indirgenemez, } \deg f \mid n \,\}$$

Yani $x^{p^n} - x$, derecesi $n$'yi bölen **bütün** monik indirgenemez polinomların çarpımı ve her biri bir kez. Neden: $GF(p^n)$'nin $p^n$ elemanının hepsi $y^{p^n} = y$'yi sağlıyor (Lagrange, Ders 6.22), yani hepsi bu polinomun kökü. Derecesi $d$ olan bir indirgenemez $f$'nin kökleri $GF(p^d)$'de, o da $GF(p^n)$'nin içinde, ancak ve ancak $d \mid n$.

Buradan iki algoritma çıkıyor:

**Rabin testi** (1980). $\deg f = n$ olsun. $f$ indirgenemezse $x^{p^n} \equiv x \pmod f$. Bu tek başına yetmiyor: $f$, derecesi $n$'yi bölen birkaç indirgenemezin çarpımı da olabilir. Bunu ayırmak için $n$'nin her asal böleni $q$ için $\gcd(x^{p^{n/q}} - x, f) = 1$ olmalı. $f$'nin derecesi $n$'nin bir özbölenini bölen bir çarpanı varsa, o çarpan bu EBOB'lardan birinde görünür. `gp_indirgenemez` tam olarak bu. Maliyet: $x^{p^k} \bmod f$'yi hesaplamak, $k$ kez $p$. kuvvet almak, yani $O(k \log p)$ polinom çarpması.

**Derecelere göre ayırma** (*distinct-degree factorization*, DDF). $k = 1, 2, \dots$ için $g_k = \gcd(x^{p^k} - x, f)$: $f$'nin derece $k$'lı indirgenemez çarpanlarının çarpımı (küçük derecelileri önceden bölüp attıysak). $\deg g_k / k$, derece $k$'lı çarpan sayısı. `gp_ddf` bunu yapıyor. Tek şartı, $f$'nin **karesiz** olması: aynı çarpan iki kez varsa, EBOB onu bir kez sayıyor. Bunu bölüm 4'te bizzat yaşayacağız.

---

## 3. Kaç tane indirgenemez polinom var?

Bütün derece $n$ monik polinomları deneyip Rabin testiyle sayalım ve Gauss'un formülüyle karşılaştıralım. $x^{p^n} - x$'in derecesine bakınca $p^n = \sum_{d \mid n} d \cdot N_p(d)$ çıkıyor ($N_p(d)$: derece $d$ monik indirgenemez sayısı). Möbius tersine çevirmesiyle:

$$N_p(n) = \frac{1}{n} \sum_{d \mid n} \mu(d)\, p^{n/d}$$

($\mu$, Möbius fonksiyonu: $d$ karesizse $(-1)^{\text{asal çarpan sayısı}}$, değilse 0. Ders 6.15'teki içerme-dışlamanın sayı teorisi hali.)

```c
/* sayim.c: GF(p) uzerinde n. dereceden monik indirgenemez polinomlarin sayisi: hepsini dene, formulle karsilastir */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"
#include "gfp.h"

static int mobius(int n) {
    int k = 0;
    for (int q = 2; q <= n; q++) if (n % q == 0) { n /= q; if (n % q == 0) return 0; k++; }
    return k % 2 ? -1 : 1;
}

int main(void) {
    int ps[] = { 2, 3, 5 }, enfazla[] = { 14, 8, 6 };
    for (int z = 0; z < 3; z++) {
        uint64_t p = ps[z];
        printf("p = %llu\n   n   deneme   indirgenemez   Gauss formulu   oran x n      sure\n", (unsigned long long)p);
        for (int n = 1; n <= enfazla[z]; n++) {
            uint64_t top = 1; for (int i = 0; i < n; i++) top *= p;   /* p^n monik polinom */
            uint64_t *c = calloc(n + 1, 8);
            gpol f; gp_baslat(&f);
            long say = 0;
            double t0 = simdi();
            for (uint64_t k = 0; k < top; k++) {
                uint64_t v = k;
                for (int i = 0; i < n; i++) { c[i] = v % p; v /= p; }
                c[n] = 1;
                gp_ayarla(&f, c, n + 1, p);
                say += gp_indirgenemez(&f, p);
            }
            double t1 = simdi();
            long formul = 0;                              /* (1/n) sum_{d | n} mu(d) p^(n/d) */
            for (int d = 1; d <= n; d++) if (n % d == 0) { long pk = 1; for (int i = 0; i < n / d; i++) pk *= p; formul += mobius(d) * pk; }
            formul /= n;
            printf("%4d %8llu %14ld %15ld %10.3f %9.1f ms %s\n", n, (unsigned long long)top, say, formul, (double)say * n / top, (t1 - t0) * 1e3, say == formul ? "" : "FARKLI");
            free(c); gp_sil(&f);
        }
    }
    return 0;
}
```

```
$ clang -O2 -c gfp.c && clang -O2 sayim.c gfp.o -o sayim && ./sayim
p = 2
   n   deneme   indirgenemez   Gauss formulu   oran x n      sure
   1        2              2               2      1.000       0.0 ms
   2        4              1               1      0.500       0.0 ms
   3        8              2               2      0.750       0.0 ms
   4       16              3               3      0.750       0.1 ms
   5       32              6               6      0.938       0.1 ms
   6       64              9               9      0.844       0.3 ms
   7      128             18              18      0.984       0.4 ms
   8      256             30              30      0.938       1.6 ms
   9      512             56              56      0.984       3.3 ms
  10     1024             99              99      0.967      10.6 ms
  11     2048            186             186      0.999      11.0 ms
  12     4096            335             335      0.981      31.5 ms
  13     8192            630             630      1.000      27.0 ms
  14    16384           1161            1161      0.992     111.3 ms
p = 3
   n   deneme   indirgenemez   Gauss formulu   oran x n      sure
   ...
   8     6561            810             810      0.988      25.1 ms
p = 5
   ...
   6    15625           2580            2580      0.991      57.5 ms
```

Her satırda birebir aynı. Ders 6.24'teki "$GF(2)$ üzerinde derece 8 indirgenemez polinomlar" sorusunun cevabı 30. AES'in seçtiği `0x11B` bunlardan biri.

"oran × n" sütunu yaklaşık 1: rastgele bir derece $n$ monik polinomun indirgenemez olma olasılığı yaklaşık $1/n$. Tamsayılardaki asal sayı teoreminin ($1/\ln N$, Ders 6.17) polinom karşılığı. Burada $N = p^n$, $\ln N \propto n$. Pratik sonucu: derece $n$ bir indirgenemez polinom gerekiyorsa (Ders 6.24'teki gibi bir cisim kurmak için), rastgele dene. Ortalama $n$ denemede biri çıkar ve her denemeyi Rabin testi hızla eliyor.

---

## 4. CRC: bir polinom kalanı

Ders 5.19'da CRC-32'yi bit bit hesapladık ve "kontrol değeri `0xCBF43926`" ile doğruladık. Bu değerin gerçekten bir polinom kalanı olduğunu, kendi $GF(2)[x]$ kütüphanemizle hiç CRC kodu kullanmadan elde edelim.

```c
/* crc.c: CRC = mesaj polinomunun GF(2)[x]'te kalani; CRC polinomlarinin carpanlari */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "gfp.h"

/* Ders 5.19'daki bit bit dongu, yansitmasiz (en anlamli bit once), baslangic 0, son XOR yok */
static uint32_t crc_duz(const uint8_t *m, size_t n, uint32_t poli) {
    uint32_t c = 0;
    for (size_t i = 0; i < n; i++)
        for (int b = 7; b >= 0; b--) {
            uint32_t ust = (c >> 31) ^ ((m[i] >> b) & 1);
            c <<= 1;
            if (ust) c ^= poli;
        }
    return c;
}

static void poli_kur(gpol *g, uint64_t bitler, int derece) {   /* bitler: x^i katsayisi i. bit */
    uint64_t c[65];
    for (int i = 0; i <= derece; i++) c[i] = (bitler >> i) & 1;
    gp_ayarla(g, c, derece + 1, 2);
}

static void turev(gpol *r, const gpol *f) {          /* GF(2)'de (x^i)' = i x^(i-1): tek i'ler kalir */
    uint64_t c[65] = { 0 };
    for (int i = 1; i < f->n; i++) c[i - 1] = (uint64_t)i * f->c[i];
    gp_ayarla(r, c, f->n > 1 ? f->n - 1 : 1, 2);
}

/* x'in mertebesi 2^d - 1 mi (ilkel polinom)? d = 32: 2^32 - 1 = 3 5 17 257 65537 */
static int ilkel32(const gpol *f) {
    static const uint64_t q[] = { 3, 5, 17, 257, 65537 };
    uint64_t N = 0xffffffffull, xc[2] = { 0, 1 };
    gpol x, t; gp_baslat(&x); gp_baslat(&t);
    gp_ayarla(&x, xc, 2, 2);
    int ilkel = 1;
    for (int i = 0; i < 5; i++) { gp_usmod(&t, &x, N / q[i], f, 2); if (t.n == 1 && t.c[0] == 1) ilkel = 0; }
    gp_sil(&x); gp_sil(&t);
    return ilkel;
}

static uint32_t kalan_bitleri(const gpol *r) { uint32_t v = 0; for (int i = 0; i < r->n; i++) v |= (uint32_t)r->c[i] << i; return v; }

int main(void) {
    const char *mesaj = "123456789";
    size_t n = strlen(mesaj), bit = 8 * n;
    gpol M, G, R; gp_baslat(&M); gp_baslat(&G); gp_baslat(&R);
    poli_kur(&G, 0x104C11DB7ull, 32);                /* CRC-32: x^32 + x^26 + ... + 1 */

    /* 1. duz CRC: M(x) x^32 mod G(x). Mesajin ilk biti en yuksek derece */
    uint64_t *c = calloc(bit + 32, 8);
    for (size_t i = 0; i < bit; i++) c[32 + bit - 1 - i] = (mesaj[i / 8] >> (7 - i % 8)) & 1;
    gp_ayarla(&M, c, bit + 32, 2);
    gp_mod(&R, &M, &G, 2);
    printf("duz CRC: bit dongusu %08x, polinom kalani %08x\n", crc_duz((const uint8_t *)mesaj, n, 0x04C11DB7), kalan_bitleri(&R));

    /* 2. standart CRC-32: byte'larin bitleri ters (en dusuk bit once), baslangic 0xFFFFFFFF
       (= ilk 32 biti tumle), sonda 32 biti ters cevir ve 0xFFFFFFFF ile XOR */
    memset(c, 0, (bit + 32) * 8);
    for (size_t i = 0; i < bit; i++) c[32 + bit - 1 - i] = ((mesaj[i / 8] >> (i % 8)) & 1) ^ (i < 32);
    gp_ayarla(&M, c, bit + 32, 2);
    gp_mod(&R, &M, &G, 2);
    uint32_t k = kalan_bitleri(&R), ters = 0;
    for (int i = 0; i < 32; i++) ters |= ((k >> i) & 1u) << (31 - i);
    printf("standart CRC-32(\"%s\") = %08x (beklenen cbf43926)\n\n", mesaj, ters ^ 0xFFFFFFFFu);

    /* 3. carpanlar */
    struct { const char *ad; uint64_t p; int d; } crc[] = {
        { "CRC-8 (ATM)", 0x107, 8 }, { "CRC-16-IBM", 0x18005, 16 }, { "CRC-16-CCITT", 0x11021, 16 },
        { "CRC-32 (IEEE)", 0x104C11DB7ull, 32 }, { "CRC-32C (Castagnoli)", 0x11EDC6F41ull, 32 },
        { "CRC-64-ECMA", 0, 64 },
    };
    for (int z = 0; z < 6; z++) {
        if (crc[z].d == 64) {                         /* x^64 + 0x42F0E1EBA9EA3693 */
            uint64_t cc[65]; uint64_t v = 0x42F0E1EBA9EA3693ull;
            for (int i = 0; i < 64; i++) cc[i] = (v >> i) & 1;
            cc[64] = 1; gp_ayarla(&G, cc, 65, 2);
        } else poli_kur(&G, crc[z].p, crc[z].d);
        int say[65] = { 0 };
        gpol d, g, h; gp_baslat(&d); gp_baslat(&g); gp_baslat(&h);
        turev(&d, &G); gp_ebob(&g, &G, &d, 2);        /* DDF karesiz polinom ister */
        gp_bol(&h, &d, &G, &g, 2);                    /* h = G / ebob(G, G'): karesiz kisim */
        gp_ddf(&h, 2, say);
        if (gp_derece(&g) > 0) gp_ddf(&g, 2, say);    /* tekrarlanan kisim; burada (x+1)^2. Genelde Yun gerekir */
        printf("%-22s derece %2d: ", crc[z].ad, crc[z].d);
        for (int i = 1; i <= 64; i++) if (say[i]) printf("%d x derece %d  ", say[i], i);
        if (gp_derece(&g) > 0) printf("[ebob(f, f') derece %d: tekrarlanan carpan] ", gp_derece(&g));
        if (gp_indirgenemez(&G, 2)) printf("(indirgenemez%s)", crc[z].d == 32 && ilkel32(&G) ? ", ilkel" : "");
        printf("\n");
        gp_sil(&d); gp_sil(&g); gp_sil(&h);
    }
    free(c); gp_sil(&M); gp_sil(&G); gp_sil(&R);
    return 0;
}
```

```
$ clang -O2 crc.c gfp.o -o crc && ./crc
duz CRC: bit dongusu 89a1897f, polinom kalani 89a1897f
standart CRC-32("123456789") = cbf43926 (beklenen cbf43926)
```

İlk satır tanım: mesajı bir polinom $M(x)$ olarak yaz (ilk bit en yüksek derece), $x^{32}$ ile çarp, $G(x)$'e böl, kalanı al. Bit döngüsü, bu uzun bölmenin sırayla yapılmış hali: her adımda "en üst bit 1 ise $G$'yi çıkar (XOR)". İkisi aynı.

İkinci satır, standart CRC-32'nin üç ek kuralı. Hepsi polinom diline çevrilebiliyor:

- **Yansıtma**: byte'ların bitleri ters sırada okunuyor (en düşük bit önce). Ders 5.19'daki `0xEDB88320`, `0x04C11DB7`'nin bit-ters hali; aynı polinom, ters yazılmış.
- **Başlangıç `0xFFFFFFFF`**: mesajın ilk 32 bitini tümlemekle aynı. Bu yüzden mesajın başındaki sıfır byte'lar CRC'yi değiştiriyor; düz CRC'de $0 \cdot x^k$ kalanı etkilemezdi.
- **Son XOR ve son yansıtma**: kalanın 32 bitini ters çevir ve tümle.

Kodda bu üçünü polinomu kurarken uygulayıp `gp_mod`'u çağırdık. `0xCBF43926` çıktı.

---

## 5. CRC polinomlarının çarpanları

Bir CRC polinomunun çarpanları, hangi hataları yakaladığını belirliyor (Ders 5.19'da sonuçları gördük, burada nedenleri):

- $G$, $(x + 1)$ ile bölünüyorsa, **tek sayıda bit hatasının hepsini** yakalıyor: hata polinomu $E(x)$'in $x = 1$'deki değeri, hatalı bit sayısının paritesi. $E(1) = 1$ ise $G \nmid E$.
- $G$ derece $d$ ve **ilkel** (indirgenemez ve $x$'in mertebesi $2^d - 1$) ise, $2^d - 1$ bitten kısa her mesajda **iki bitlik hataların hepsini** yakalıyor: $x^i + x^j = x^j (x^{i-j} + 1)$, ve $G \mid x^k + 1$ ancak $k$, $x$'in mertebesinin katıysa.
- Derece $d$ olan ve sabit terimi 1 olan her $G$, uzunluğu en fazla $d$ bit olan **bütün ardışık hata patlamalarını** yakalıyor.

Derecelere göre ayırma ile çarpanları bulalım:

```
CRC-8 (ATM)            derece  8: 1 x derece 1  1 x derece 7
CRC-16-IBM             derece 16: 1 x derece 1  1 x derece 15
CRC-16-CCITT           derece 16: 1 x derece 1  1 x derece 15
CRC-32 (IEEE)          derece 32: 1 x derece 32  (indirgenemez, ilkel)
CRC-32C (Castagnoli)   derece 32: 1 x derece 1  1 x derece 31
CRC-64-ECMA            derece 64: 2 x derece 1  3 x derece 15  1 x derece 17  [ebob(f, f') derece 2: tekrarlanan carpan]
```

SymPy ile karşılaştırma:

```
$ python3 -c "
from sympy import Poly, symbols; x = symbols('x')
def P(v, d): return Poly([(v >> i) & 1 for i in range(d, -1, -1)], x, modulus=2)
for ad, v, d in [('crc32', 0x104C11DB7, 32), ('crc32c', 0x11EDC6F41, 32), ('crc64', (1 << 64) | 0x42F0E1EBA9EA3693, 64)]:
    print(ad, [(g.degree(), e) for g, e in P(v, d).factor_list()[1]])"
crc32 [(32, 1)]
crc32c [(1, 1), (31, 1)]
crc64 [(1, 2), (15, 1), (15, 1), (15, 1), (17, 1)]
```

CRC-64'te $(x + 1)^2$ var: kare çarpan. `gp_ddf`'nin ilk sürümü bunu "1 × derece 1" diye saymıştı. DDF karesiz girdi ister, ve aynı çarpanı iki kez içeren bir polinomda EBOB onu bir kez görür. SymPy'nin `(1, 2)`'si bu hatayı gösterdi. Düzeltme: önce $\gcd(f, f')$'yi ayır. Tekrarlanan bir çarpan türevde de kalıyor (Ders 12.8, Alıştırma 2). Karesiz kısım $f / \gcd(f, f')$. Genel çözüm Yun'un karesiz ayrıştırması ($GF(p)$'de $f' = 0$ olabildiği için küçük bir ek gerekiyor). Ders 12.4'teki "nadir dal" dersinin bir benzeri: bağımsız bir doğrulama, kendi testinin göremediği bir varsayımı yakaladı.

CRC-32 (IEEE) **indirgenemez ve ilkel**: $x$'in mertebesi tam $2^{32} - 1$. $2^{32} - 1 = 3 \cdot 5 \cdot 17 \cdot 257 \cdot 65537$'nin her asal böleni $q$ için $x^{(2^{32}-1)/q} \not\equiv 1$ (`ilkel32`). Yani $2^{32} - 1$ bitten (yaklaşık 512 MB) kısa her mesajda iki bitlik hataların hepsini yakalıyor. Ama $(x + 1)$ çarpanı yok: tek sayıda hata garantisi de yok. CRC-32C, Castagnoli ve arkadaşlarının (1993) sistematik aramasının sonucu. $(x + 1)$ çarpanı ve derece 31 bir indirgenemez içeriyor. $2^{31} - 1$ asal olduğundan derece 31 her indirgenemez polinom ilkel. Ethernet CRC-32'yi kullanıyor; iSCSI, ext4 ve SSE4.2'nin `crc32` komutu CRC-32C'yi.

---

## Alıştırmalar

**1** – $GF(2)$ üzerinde derece 4 olan 3 monik indirgenemez polinomu elle bul. $x^{16} - x$'in çarpanlarına ayrılışını yaz: içinde hangi dereceler, kaçar tane?

**2** – Ders 6.24'teki AES polinomu `0x11B` için Rabin testini `gp_indirgenemez` ile çalıştır. İlkel mi? AES neden üreteç olarak $x$ (2) değil $x + 1$ (3) kullanıyor?

**3** – Rastgele derece $n$ polinomları üreterek ilk indirgenemezi bulana kadar kaç deneme yaptığını ölç ($p = 2^{31} - 1$, $n = 64$). Ortalamanın $n$'ye yakın olduğunu doğrula.

**4** – `crc.c`'deki bit döngüsünü 4 bitlik bir tablo ile hızlandır (16 girişli tablo, Ders 5.19'daki 256'lık tablonun küçüğü). Tablonun $i$. girişi, polinom dilinde neye karşılık geliyor?

**5** – Bir mesajın CRC'si $R(x) = M(x)\, x^{32} \bmod G(x)$. İki mesajın XOR'u için $R(M_1 + M_2) = R(M_1) + R(M_2)$ (düz CRC). Neden? Standart CRC-32'de (başlangıç ve son XOR'la) bu eşitlik nasıl değişiyor?

<details>
<summary>Cevaplar</summary>

**1** – $x^4 + x + 1$, $x^4 + x^3 + 1$, $x^4 + x^3 + x^2 + x + 1$. $x^{16} - x$ = derecesi 4'ü bölen bütün monik indirgenemezlerin çarpımı: derece 1 (iki tane: $x$, $x + 1$), derece 2 (bir tane: $x^2 + x + 1$), derece 4 (üç tane). Derece toplamı $2 + 2 + 12 = 16$. ✓ (Tablodaki 2, 1, 3.)

**2** – İndirgenemez, ama ilkel **değil**: $x$'in mertebesi 51 (255'i bölüyor, 255 değil). Bu yüzden $x$'in kuvvetleri $GF(2^8)$'in 255 sıfır olmayan elemanının yalnız 51'ini geziyor ve log tablosu kurulamıyor. $x + 1$'in mertebesi 255; bunu küçük bir döngüyle hesapladım. Ders 6.24'teki log/exp tabloları bu yüzden 3 ile kurulmuştu.

**3** – $p = 2^{31} - 1$'de katsayı çarpımı $< 2^{62}$: `gp_carp` güvenli. Beklenen deneme yaklaşık $n = 64$ (geometrik dağılım, sapması da yaklaşık 64). Her Rabin testi: $n = 64 = 2^6$'nın tek asal böleni 2, yani bir $x^{p^{32}}$ ve bir $x^{p^{64}}$. 64 kez $p$. kuvvet, her biri yaklaşık 31 kare alma ve derece 64 polinom çarpması. Testlerin çoğu daha ucuz bir ön elemeyle (küçük dereceli çarpanlar için DDF'nin ilk birkaç adımı) erken bitirilebilir.

**4** – Bir defada 4 bit işlenir. Tablonun $i$. girişi, $i(x) \cdot x^{32} \bmod G(x)$: $i$'nin 4 bitini derece 32–35'e koyup $G$'ye bölmenin kalanı. Döngü: `c = (c << 4) ^ T[(c >> 28) ^ dort_bit]`. 256'lık tablo aynı fikir 8 bitle. Doğrusallık (Alıştırma 5) her girişin bağımsız hesaplanabilmesini sağlıyor.

**5** – Polinom çarpması ve kalan almak **doğrusal**: $(M_1 + M_2) x^{32} \bmod G = M_1 x^{32} \bmod G + M_2 x^{32} \bmod G$. $GF(2)$'de toplama XOR. Standart CRC'de başlangıç değeri ve son XOR **sabit** bir terim ekliyor: $\text{CRC}(M) = R(M) + C_{\text{uz}}$, $C$ yalnız mesaj uzunluğuna bağlı. Eşit uzunluklu üç mesaj için $\text{CRC}(M_1 \oplus M_2 \oplus M_3) = \text{CRC}(M_1) \oplus \text{CRC}(M_2) \oplus \text{CRC}(M_3)$. Bu doğrusallık yüzden CRC **kriptografik bir özet değil**: istenen CRC'yi veren bir mesajı kurmak, bir doğrusal denklem çözmek kadar kolay.

</details>

---

## Kaynaklar

- Michael O. Rabin, "Probabilistic Algorithms in Finite Fields", *SIAM Journal on Computing*, 9(2), 1980.
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra*, Bölüm 14 (sonlu cisimlerde çarpanlara ayırma: karesiz ayrıştırma, DDF, Cantor–Zassenhaus).
- Rudolf Lidl ve Harald Niederreiter, *Introduction to Finite Fields and Their Applications*, Bölüm 3 (indirgenemez polinomların sayısı, ilkel polinomlar).
- Guy Castagnoli, Stefan Bräuer, Martin Herrmann, "Optimization of Cyclic Redundancy-Check Codes with 24 and 32 Parity Bits", *IEEE Transactions on Communications*, 41(6), 1993.
- Philip Koopman, "32-Bit Cyclic Redundancy Codes for Internet Applications", *DSN 2002*; ve CRC polinom tabloları (users.ece.cmu.edu/~koopman/crc).
- Ross Williams, "A Painless Guide to CRC Error Detection Algorithms", 1993 (yansıtma, başlangıç değeri, son XOR kuralları).

**Sıradaki ders:** Sembolik ifade ağacı. İfadeyi ağaç olarak temsil, ayrıştırıp yazdırma, derleyici ön yüzünün mini sürümü.
