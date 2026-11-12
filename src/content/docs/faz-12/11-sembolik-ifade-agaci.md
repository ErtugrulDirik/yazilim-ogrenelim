---
title: "12.11 Sembolik ifade ağacı"
description: "Sembolik ifadeyi ağaç olarak temsil etmek: sayı (kesin rat), değişken, ikili işlem, tekli eksi ve fonksiyon düğümleri; dilbilgisi ile öncelik ve birleşme yönü (2^3^2 = 2^(3^2), -x^2 = -(x^2), a - b - c = (a - b) - c); özyinelemeli inişle ayrıştırma ve konumlu hata mesajları; en az parantezle yazdırma kuralları ve 100000 rastgele ağaçta yaz-ayrıştır döngüsünün aynı ağacı vermesi; Python'un kendi ayrıştırıcısıyla 72864 ifadede aynı sayısal sonuç; Clang'ın AST dökümüyle karşılaştırma."
---

Şimdiye kadar sayıları ve polinomları temsil ettik. $\sin(x) \cdot e^x + \frac{3}{1-x}$ ise ne sayı ne polinom. Bir CAS bunu **ağaç** olarak tutuyor: her iç düğüm bir işlem, her yaprak bir sayı ya da değişken. Derleyiciler de kaynak kodu aynı şekilde tutuyor (Ders 8.7'deki ifade ağacı, Faz 15'teki AST). Bu derste metinden ağaca (ayrıştırma) ve ağaçtan metne (yazdırma) giden iki yönü yazıyoruz. Sonraki üç ders bu ağacın üzerinde çalışacak.

---

## 1. Düğümler

```c
/* ifade.h: sembolik ifade agaci. Sayilar kesin (rat), degiskenler ve fonksiyonlar adla */
#ifndef IFADE_H
#define IFADE_H
#include "rat.h"

typedef enum { SAYI, DEG, TOPLA, CIKAR, CARP, BOL, US, EKSI, FONK } tur;

typedef struct ifade {
    tur t;
    rat r;                    /* SAYI */
    char ad[8];               /* DEG ve FONK: "x", "sin" */
    struct ifade *a, *b;      /* cocuklar: ikili islemde ikisi, EKSI ve FONK'ta yalniz a */
} ifade;

/* kurucular: cocuklarin sahipligini alir */
ifade *i_sayi(int64_t v);
ifade *i_rat(const rat *r);
ifade *i_deg(const char *ad);
ifade *i_ikili(tur t, ifade *a, ifade *b);
ifade *i_eksi(ifade *a);
ifade *i_fonk(const char *ad, ifade *a);
ifade *i_kopya(const ifade *e);
void   i_sil(ifade *e);

int    i_esit(const ifade *a, const ifade *b);     /* yapisal esitlik */
size_t i_boyut(const ifade *e);                    /* dugum sayisi */
ifade *i_ayristir(const char *s, char *hata, size_t hata_boy);   /* hata varsa NULL */
char  *i_yaz(const ifade *e);                      /* en az parantezle; free ile birak */
void   i_agac(const ifade *e, int girinti);        /* agaci alt alta yazdir */
double i_degerle(const ifade *e, const char *ad, double x);
#endif
```

Dokuz düğüm türü:

- **Yapraklar**: `SAYI` (kesin bir `rat`: $\frac{5}{4}$ ve $10^{100}$ da bir yaprak) ve `DEG` (değişken adı).
- **İkili işlemler**: `TOPLA`, `CIKAR`, `CARP`, `BOL`, `US`.
- **Tekliler**: `EKSI` ve `FONK` (`sin`, `cos`, `tan`, `exp`, `ln`, `sqrt`).

`CIKAR` ve `BOL` ayrı düğümler. $a - b$'yi $a + (-1) \cdot b$ olarak tutmak sadeleştirme için daha düzenli bir biçim (Ders 12.12'de kanonik formda yapacağımız gibi), ama girdiyi olduğu gibi tutmak, yazdırmayı ve hata mesajlarını kullanıcının yazdığına yakın tutuyor. Derleyicilerin ön yüzü de böyle: AST kaynağa sadık, sadeleştirme sonraki aşamalarda.

Bellek modeli basit: her fonksiyon **yeni** bir ağaç döndürüyor, girdisine dokunmuyor. Kurucular çocuklarının sahipliğini alıyor. Her düğüm ayrı bir `calloc`, her ağaç `i_sil` ile özyinelemeli siliniyor. Ders 8.21'deki arena, yüz binlerce küçük düğüm için çok daha hızlı olurdu. Burada açıklık için atlıyoruz.

---

## 2. Dilbilgisi

$2 + 3 \cdot 4$'ün $2 + (3 \cdot 4)$ olduğunu bir ayrıştırıcıya nasıl söyleriz? Her öncelik düzeyine bir kural:

```
ifade := terim (('+' | '-') terim)*
terim := birli (('*' | '/') birli)*
birli := '-' birli | us
us    := atom ('^' birli)?
atom  := sayi | ad | ad '(' ifade ')' | '(' ifade ')'
```

- Düşük öncelikli işlem üstteki kuralda: `ifade` önce bütün `terim`leri topluyor, her `terim` de kendi çarpımlarını. $2 + 3 \cdot 4$'te `3 * 4` bir `terim` olarak birlikte okunuyor.
- `*` ile tekrarlanan kurallar **sol birleşimli**: döngü her turda ağacı sola doğru büyütüyor, $a - b - c = (a - b) - c$.
- `us`, `birli`'ye geri dönen sağ tarafıyla **sağ birleşimli**: $2^{3^2} = 2^9 = 512$, $(2^3)^2 = 64$ değil. Matematik ve Python (`**`) böyle.
- `birli`, `us`'un **üstünde**: $-x^2 = -(x^2)$. Üssün sağı yine `birli`: $x^{-1}$ yazılabiliyor.

Bu dilbilgisi doğrudan koda çevriliyor: her kural bir fonksiyon, her fonksiyon gerektiğinde alt kuralı çağırıyor. **Özyinelemeli iniş** (*recursive descent*). Ders 8.4'teki postfix hesaplayıcıdan farklı olarak yığını biz tutmuyoruz, C'nin çağrı yığını tutuyor (Ders 8.6). GCC ve Clang'ın C ve C++ ayrıştırıcıları da elle yazılmış özyinelemeli iniş ayrıştırıcıları.

```c
/* ifade.c: kurucular, ozyinelemeli inisle ayristirma, en az parantezle yazdirma, sayisal deger */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <math.h>
#include "ifade.h"

static ifade *yeni(tur t) { ifade *e = calloc(1, sizeof *e); e->t = t; return e; }
ifade *i_sayi(int64_t v) { ifade *e = yeni(SAYI); rat_baslat(&e->r); rat_tam(&e->r, v); return e; }
ifade *i_rat(const rat *r) { ifade *e = yeni(SAYI); rat_baslat(&e->r); rat_kopyala(&e->r, r); return e; }
ifade *i_deg(const char *ad) { ifade *e = yeni(DEG); snprintf(e->ad, sizeof e->ad, "%s", ad); return e; }
ifade *i_ikili(tur t, ifade *a, ifade *b) { ifade *e = yeni(t); e->a = a; e->b = b; return e; }
ifade *i_eksi(ifade *a) { ifade *e = yeni(EKSI); e->a = a; return e; }
ifade *i_fonk(const char *ad, ifade *a) { ifade *e = yeni(FONK); snprintf(e->ad, sizeof e->ad, "%s", ad); e->a = a; return e; }

ifade *i_kopya(const ifade *e) {
    if (!e) return 0;
    ifade *k = yeni(e->t);
    memcpy(k->ad, e->ad, sizeof k->ad);
    if (e->t == SAYI) { rat_baslat(&k->r); rat_kopyala(&k->r, &e->r); }
    k->a = i_kopya(e->a); k->b = i_kopya(e->b);
    return k;
}
void i_sil(ifade *e) {
    if (!e) return;
    if (e->t == SAYI) rat_sil(&e->r);
    i_sil(e->a); i_sil(e->b); free(e);
}
int i_esit(const ifade *a, const ifade *b) {
    if (!a || !b) return a == b;
    if (a->t != b->t) return 0;
    if (a->t == SAYI) return rat_kars(&a->r, &b->r) == 0;
    if ((a->t == DEG || a->t == FONK) && strcmp(a->ad, b->ad)) return 0;
    return i_esit(a->a, b->a) && i_esit(a->b, b->b);
}
size_t i_boyut(const ifade *e) { return e ? 1 + i_boyut(e->a) + i_boyut(e->b) : 0; }

/* ---------- ayristirma ----------
   ifade := terim (('+' | '-') terim)*
   terim := birli (('*' | '/') birli)*
   birli := '-' birli | us
   us    := atom ('^' birli)?          sag birlesimli: 2^3^2 = 2^(3^2), -x^2 = -(x^2)
   atom  := sayi | ad | ad '(' ifade ')' | '(' ifade ')'                                 */
typedef struct { const char *bas, *p; char *hata; size_t hb; } ayr;

static void bosluk(ayr *a) { while (isspace((unsigned char)*a->p)) a->p++; }
static ifade *hata(ayr *a, const char *m) {
    if (!a->hata[0]) snprintf(a->hata, a->hb, "%d. karakterde %s", (int)(a->p - a->bas) + 1, m);
    return 0;
}
static ifade *ifade_(ayr *a);
static ifade *birli(ayr *a);

static const char *fonklar[] = { "sin", "cos", "tan", "exp", "ln", "sqrt", 0 };

static ifade *atom(ayr *a) {
    bosluk(a);
    char c = *a->p;
    if (isdigit((unsigned char)c)) {                 /* 12 ya da 1.25 = 5/4: ondalik da kesin */
        char buf[256]; size_t n = 0, kesir = 0; int nokta = 0;
        while ((isdigit((unsigned char)*a->p) || (*a->p == '.' && !nokta)) && n < 250) {
            if (*a->p == '.') nokta = 1; else { buf[n++] = *a->p; if (nokta) kesir++; }
            a->p++;
        }
        buf[n] = 0;
        ifade *e = yeni(SAYI); rat_baslat(&e->r);
        rat_oku(&e->r, buf);
        if (kesir) {
            rat on; rat_baslat(&on); rat_tam(&on, 1);
            rat t; rat_baslat(&t); rat_tam(&t, 10);
            for (size_t i = 0; i < kesir; i++) rat_carp(&on, &on, &t);
            rat_bol(&e->r, &e->r, &on);
            rat_sil(&on); rat_sil(&t);
        }
        return e;
    }
    if (isalpha((unsigned char)c)) {
        char ad[8]; size_t n = 0;
        while (isalnum((unsigned char)*a->p)) { if (n < 7) ad[n++] = *a->p; a->p++; }
        ad[n] = 0;
        bosluk(a);
        if (*a->p == '(') {
            int bilinen = 0;
            for (int i = 0; fonklar[i]; i++) if (!strcmp(fonklar[i], ad)) bilinen = 1;
            if (!bilinen) return hata(a, "bilinmeyen fonksiyon");
            a->p++;
            ifade *ic = ifade_(a);
            if (!ic) return 0;
            bosluk(a);
            if (*a->p != ')') { i_sil(ic); return hata(a, "')' bekleniyordu"); }
            a->p++;
            return i_fonk(ad, ic);
        }
        return i_deg(ad);
    }
    if (c == '(') {
        a->p++;
        ifade *e = ifade_(a);
        if (!e) return 0;
        bosluk(a);
        if (*a->p != ')') { i_sil(e); return hata(a, "')' bekleniyordu"); }
        a->p++;
        return e;
    }
    return hata(a, c ? "beklenmeyen karakter" : "ifade erken bitti");
}

static ifade *us(ayr *a) {
    ifade *e = atom(a);
    if (!e) return 0;
    bosluk(a);
    if (*a->p == '^') {
        a->p++;
        ifade *s = birli(a);                         /* x^-1 ve 2^3^2 */
        if (!s) { i_sil(e); return 0; }
        e = i_ikili(US, e, s);
    }
    return e;
}

static ifade *birli(ayr *a) {
    bosluk(a);
    if (*a->p == '-') { a->p++; ifade *e = birli(a); return e ? i_eksi(e) : 0; }
    return us(a);
}

static ifade *terim(ayr *a) {
    ifade *e = birli(a);
    while (e) {
        bosluk(a);
        char c = *a->p;
        if (c != '*' && c != '/') break;
        a->p++;
        ifade *s = birli(a);
        if (!s) { i_sil(e); return 0; }
        e = i_ikili(c == '*' ? CARP : BOL, e, s);   /* sol birlesimli: a/b/c = (a/b)/c */
    }
    return e;
}

static ifade *ifade_(ayr *a) {
    ifade *e = terim(a);
    while (e) {
        bosluk(a);
        char c = *a->p;
        if (c != '+' && c != '-') break;
        a->p++;
        ifade *s = terim(a);
        if (!s) { i_sil(e); return 0; }
        e = i_ikili(c == '+' ? TOPLA : CIKAR, e, s);
    }
    return e;
}

ifade *i_ayristir(const char *s, char *h, size_t hb) {
    ayr a = { s, s, h, hb };
    h[0] = 0;
    ifade *e = ifade_(&a);
    bosluk(&a);
    if (e && *a.p) { i_sil(e); e = 0; hata(&a, "fazladan karakter"); }
    return e;
}

/* ---------- yazdirma ---------- */
typedef struct { char *s; size_t n, kap; } tampon;
static void ekle(tampon *t, const char *s) {
    size_t k = strlen(s);
    if (t->n + k + 1 > t->kap) { while (t->n + k + 1 > t->kap) t->kap = t->kap ? 2 * t->kap : 64; t->s = realloc(t->s, t->kap); }
    memcpy(t->s + t->n, s, k + 1); t->n += k;
}

/* 1: + -, 2: * /, 3: tekli eksi, 4: ^, 5: atom. Eksi tamsayi tekli eksi gibi, kesir (eksi de olsa) bolme gibi */
static int oncelik(const ifade *e) {
    switch (e->t) {
    case TOPLA: case CIKAR: return 1;
    case CARP: case BOL: return 2;
    case EKSI: return 3;
    case US: return 4;
    case SAYI: return !(e->r.q.n == 1 && e->r.q.d[0] == 1) ? 2 : e->r.p.isaret ? 3 : 5;   /* kesir: eksi de olsa bolme gibi */
    default: return 5;
    }
}

static void yaz(tampon *t, const ifade *e);
/* cocuk, ebeveynin solunda mi saginda mi: parantez gerekir mi */
static void cocuk(tampon *t, const ifade *c, const ifade *ebeveyn, int sag) {
    int cp = oncelik(c), pp = oncelik(ebeveyn), gerek;
    if (cp == 3)                                     /* "a + -b" ve "x^-1" parantezsiz okunuyor; baska yerde degil */
        gerek = !(((ebeveyn->t == TOPLA || ebeveyn->t == CIKAR) && !sag) || (ebeveyn->t == US && sag));
    else if (ebeveyn->t == EKSI) gerek = cp <= 3;
    else if (ebeveyn->t == US) gerek = sag ? cp <= 2 : cp <= 4;    /* sag birlesimli: x^y^z = x^(y^z) */
    else gerek = cp < pp || (cp == pp && sag);                      /* sol birlesimli */
    if (gerek) ekle(t, "(");
    yaz(t, c);
    if (gerek) ekle(t, ")");
}

static void yaz(tampon *t, const ifade *e) {
    static const char *op[] = { 0, 0, " + ", " - ", "*", "/", "^" };
    switch (e->t) {
    case SAYI: { char *s = rat_yaz(&e->r); ekle(t, s); free(s); break; }
    case DEG: ekle(t, e->ad); break;
    case FONK: ekle(t, e->ad); ekle(t, "("); yaz(t, e->a); ekle(t, ")"); break;
    case EKSI: ekle(t, "-"); cocuk(t, e->a, e, 0); break;
    default: cocuk(t, e->a, e, 0); ekle(t, op[e->t]); cocuk(t, e->b, e, 1); break;
    }
}

char *i_yaz(const ifade *e) { tampon t = { 0, 0, 0 }; ekle(&t, ""); yaz(&t, e); return t.s; }

void i_agac(const ifade *e, int g) {
    static const char *ad[] = { "SAYI", "DEG", "TOPLA", "CIKAR", "CARP", "BOL", "US", "EKSI", "FONK" };
    printf("%*s%s", 2 * g, "", ad[e->t]);
    if (e->t == SAYI) { char *s = rat_yaz(&e->r); printf(" %s", s); free(s); }
    if (e->t == DEG || e->t == FONK) printf(" %s", e->ad);
    printf("\n");
    if (e->a) i_agac(e->a, g + 1);
    if (e->b) i_agac(e->b, g + 1);
}

/* ---------- sayisal deger ---------- */
static double bn_double(const bn *x) {
    double v = 0;
    for (size_t i = x->n; i-- > 0;) v = v * 4294967296.0 + x->d[i];
    return x->isaret ? -v : v;
}

double i_degerle(const ifade *e, const char *ad, double x) {
    switch (e->t) {
    case SAYI: return bn_double(&e->r.p) / bn_double(&e->r.q);
    case DEG: return strcmp(e->ad, ad) ? NAN : x;
    case TOPLA: return i_degerle(e->a, ad, x) + i_degerle(e->b, ad, x);
    case CIKAR: return i_degerle(e->a, ad, x) - i_degerle(e->b, ad, x);
    case CARP: return i_degerle(e->a, ad, x) * i_degerle(e->b, ad, x);
    case BOL: return i_degerle(e->a, ad, x) / i_degerle(e->b, ad, x);
    case US: return pow(i_degerle(e->a, ad, x), i_degerle(e->b, ad, x));
    case EKSI: return -i_degerle(e->a, ad, x);
    case FONK: {
        double v = i_degerle(e->a, ad, x);
        if (!strcmp(e->ad, "sin")) return sin(v);
        if (!strcmp(e->ad, "cos")) return cos(v);
        if (!strcmp(e->ad, "tan")) return tan(v);
        if (!strcmp(e->ad, "exp")) return exp(v);
        if (!strcmp(e->ad, "ln")) return log(v);
        return sqrt(v);
    }
    }
    return NAN;
}
```

Ayrıştırıcının küçük ayrıntıları:

- `1.25`, `5/4` olarak **kesin** okunuyor: 125'i 100'e bölüyoruz, `double`'a hiç uğramıyoruz.
- Bir ad `(` ile devam ediyorsa fonksiyon, değilse değişken. Bilinmeyen fonksiyon hata.
- Her hata, konumuyla birlikte ilk hatayı saklıyor ve `NULL` yukarı kadar taşınıyor. Kısmi ağaçlar siliniyor.

---

## 3. En az parantezle yazdırma

Her alt ifadeyi paranteze almak kolay ama okunmaz: $((x^2) \cdot \sin(x)) + (3/(1 - x))$. İstediğimiz, **yeniden ayrıştırıldığında aynı ağacı veren en kısa metin**. Kural, dilbilgisinin tersi:

- Çocuk ebeveyninden **düşük** öncelikliyse parantez: $(a + b) \cdot c$.
- **Eşit** öncelikte, sol birleşimli bir işlemin **sağ** çocuğu parantez ister: $a - (b - c)$. Ama $(a - b) - c$, $a - b - c$ olarak yazılıyor.
- `US` sağ birleşimli: tersine, **sol** çocuk parantez istiyor. $(2^3)^2$ ama $2^{3^2}$.
- Tekli eksi yalnız iki yerde parantezsiz okunabiliyor: toplama veya çıkarmanın solunda ($-a + b$) ve üssün sağında ($x^{-1}$). Başka her yerde parantez: $2 \cdot (-x)$. Neden: `2*-x/y` metnini ayrıştırıcımız $(2 \cdot (-x)) / y$ olarak okuyor. Ama $2 \cdot (-(x / y))$ ağacını parantezsiz yazsaydık o da `2*-x/y` olurdu. İki farklı ağaç aynı metne düşer ve geri dönüş bozulurdu.
- Eksi tamsayılar tekli eksi gibi davranıyor. Kesirli sayılar ($\frac{5}{4}$, $-\frac{2}{5}$) ise, eksi olsalar da, bölme gibi: $x^{(5/4)}$, $x^{(-2/5)}$. Bu ayrımı ilk başta yapmamıştım. Ders 12.13'te SymPy ile karşılaştırırken $(x+2)^{-2/5}$'in `(x + 2)^-2/5` diye yazıldığını ve $((x+2)^{-2})/5$ olarak okunduğunu gördüm. Yaz-ayrıştır sınaması bunu yakalayamazdı: oradaki rastgele ağaçlarda eksi kesirli sayı yok, onlar ancak sadeleştirmeden sonra ortaya çıkıyor.

---

## 4. Sınama

İki bağımsız sınama:

1. **Yaz-ayrıştır döngüsü.** Rastgele ağaç üret, yazdır, yazdırılan metni ayrıştır: aynı ağaç çıkmalı. Parantez kuralındaki her hata, bir ağacın farklı bir ağaca dönüşmesiyle görünüyor.
2. **Python ile.** Yazdırdığımız metni Python'un **kendi ayrıştırıcısına** ver (`^` yerine `**`) ve $x = 0.7$'de değerlendir. Bizim `i_degerle` ile aynı sayıyı vermeli. Bu, öncelik kurallarımızın matematikteki (ve Python'daki) kurallarla aynı olduğunu sınıyor. Kendi ayrıştırıcımızla sınamak bunu yakalayamazdı: ayrıştırıcı ile yazıcı aynı yanlışı paylaşabilirdi.

```c
/* sina_ifade.c: rastgele agac -> yaz -> ayristir -> ayni agac mi; Python icin dosya; hata mesajlari */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "bn_mod.h"
#include "ifade.h"

static uint64_t s = 11;
static ifade *rastgele(int derinlik) {
    int r = (int)(rastgele64(&s) % 100);
    if (derinlik == 0 || r < 25) {
        if (r % 3 == 0) return i_deg("x");
        return i_sayi((int64_t)(rastgele64(&s) % 10));
    }
    static const tur ikili[] = { TOPLA, CIKAR, CARP, BOL, US };
    static const char *f[] = { "sin", "cos", "exp", "ln", "sqrt" };
    if (r < 35) return i_eksi(rastgele(derinlik - 1));
    if (r < 45) return i_fonk(f[rastgele64(&s) % 5], rastgele(derinlik - 1));
    tur t = ikili[rastgele64(&s) % 5];
    ifade *a = rastgele(derinlik - 1), *b = rastgele(derinlik - 1);
    return i_ikili(t, a, b);
}

int main(void) {
    char h[128];
    long ayni = 0, n = 100000;
    size_t dugum = 0;
    FILE *f = fopen("ifade_kontrol.txt", "w");
    for (long i = 0; i < n; i++) {
        ifade *e = rastgele(6);
        char *y = i_yaz(e);
        ifade *e2 = i_ayristir(y, h, sizeof h);
        if (e2 && i_esit(e, e2)) ayni++;
        else if (n - ayni < 5) printf("FARKLI: %s (%s)\n", y, h);
        dugum += i_boyut(e);
        double v = i_degerle(e, "x", 0.7);
        if (isfinite(v)) fprintf(f, "%.17g %s\n", v, y);
        free(y); i_sil(e); i_sil(e2);
    }
    fclose(f);
    printf("%ld agac (ortalama %.1f dugum): yaz + ayristir %ld tanesinde ayni agaci verdi\n", n, (double)dugum / n, ayni);

    const char *ornek = "x^2*sin(x) + 3/(1 - x)";
    ifade *e = i_ayristir(ornek, h, sizeof h);
    char *y = i_yaz(e);
    printf("\n%s\n  -> %s\n", ornek, y);
    i_agac(e, 1);
    free(y); i_sil(e);

    const char *ikili[] = { "2^3^2", "-x^2", "a - b - c", "a - (b - c)", "(a*b)/(c*d)", "2*-x", "1.25*x" };
    for (int i = 0; i < 7; i++) {
        e = i_ayristir(ikili[i], h, sizeof h); y = i_yaz(e);
        printf("%-14s -> %s\n", ikili[i], y);
        free(y); i_sil(e);
    }
    const char *bozuk[] = { "x + ", "sin x", "foo(x)", "(x + 1", "x + 1)", "2 $ 3" };
    for (int i = 0; i < 6; i++) {
        e = i_ayristir(bozuk[i], h, sizeof h);
        printf("%-10s: %s\n", bozuk[i], e ? "kabul edildi?" : h);
        i_sil(e);
    }
    return 0;
}
```

```python
# ifade_python.py: C'nin yazdigi ifadeleri Python'un kendi ayristiricisi ile hesapla
import math, re, sys
ad = {'sin': math.sin, 'cos': math.cos, 'exp': math.exp, 'ln': math.log, 'sqrt': math.sqrt, 'x': 0.7}
say = uyan = atla = 0
for satir in open(sys.argv[1]):
    c, metin = satir.split(' ', 1)
    try:
        v = eval(re.sub(r'(\d+)', r'\1.0', metin).replace('^', '**'),   # 9^9^9 tamsayi olarak hesaplanmasin
                  {'__builtins__': {}}, ad)
    except (ValueError, ZeroDivisionError, OverflowError, TypeError):   # TypeError: ara deger karmasik
        atla += 1; continue
    if isinstance(v, complex) or not math.isfinite(v): atla += 1; continue
    say += 1
    c = float(c)
    if abs(v - c) <= 1e-9 * max(1, abs(v)): uyan += 1
    elif say - uyan < 4: print('FARKLI', c, v, metin.strip())
print(f'{say} ifade karsilastirildi, {uyan} ayni ({atla} tanesi Python\'da tanimsiz)')
```

```
$ clang -O2 -c ifade.c && clang -O2 sina_ifade.c bn_*.o rat.o ifade.o -o sina_ifade && ./sina_ifade
100000 agac (ortalama 17.6 dugum): yaz + ayristir 100000 tanesinde ayni agaci verdi

x^2*sin(x) + 3/(1 - x)
  -> x^2*sin(x) + 3/(1 - x)
  TOPLA
    CARP
      US
        DEG x
        SAYI 2
      FONK sin
        DEG x
    BOL
      SAYI 3
      CIKAR
        SAYI 1
        DEG x
2^3^2          -> 2^3^2
-x^2           -> -x^2
a - b - c      -> a - b - c
a - (b - c)    -> a - (b - c)
(a*b)/(c*d)    -> a*b/(c*d)
2*-x           -> 2*(-x)
1.25*x         -> 5/4*x
x +       : 5. karakterde ifade erken bitti
sin x     : 5. karakterde fazladan karakter
foo(x)    : 4. karakterde bilinmeyen fonksiyon
(x + 1    : 7. karakterde ')' bekleniyordu
x + 1)    : 6. karakterde fazladan karakter
2 $ 3     : 3. karakterde fazladan karakter
$ python3 ifade_python.py ifade_kontrol.txt
72864 ifade karsilastirildi, 72864 ayni (3234 tanesi Python'da tanimsiz)
```

- `(a*b)/(c*d)`'nin ilk parantezi gereksizmiş: `a*b/(c*d)` aynı ağaç.
- `sin x` hatası: `sin`'i değişken sandı ve sonra fazladan bir `x` buldu. Mesaj teknik olarak doğru ama yardımcı değil. Gerçek derleyicilerin hata mesajı kalitesine bu kadar emek vermesinin nedeni bu. Alıştırma 4.
- **Yazıcının ilk taslağında bir hata vardı**: üssün sağındaki toplamı parantezsiz yazıyordu ($x^{(a + b)}$, `x^a + b` oluyordu). Kural "sağ birleşimli, sağ çocuk parantez istemez" diye yazılmıştı. Bu yalnız eşit ve daha yüksek öncelikli çocuklar için doğru. Hatayı testi çalıştırmadan, kodu gözden geçirirken fark ettim. Sonradan eski kuralı geri koyup testi çalıştırdım: 100000 ağacın yalnız 69274'ü aynı ağacı veriyor. Yani yaz-ayrıştır döngüsü bu hatayı hemen yakalardı.
- **Python sınamasının da iki dersi oldu.** İlk sürüm takıldı: `9^9^9`'u Python **tam sayı** olarak hesaplamaya çalışıyordu, 370 milyon basamaklı bir sayı. Sayıları `9.0` yaparak kayan noktaya zorladım. Sonra bir `TypeError`: C'de `pow(-2, 0.5)` NaN veriyor ve `pow(NaN, 0) = 1` ile NaN kayboluyor. Python'da ise $(-2)^{0.5}$ bir karmaşık sayı ve `sin` onu kabul etmiyor. 3234 "tanımsız" ifadenin bir kısmı bunlar.

---

## 5. Derleyicinin ağacı

Clang'a aynı ifadeyi C olarak verip AST'sini döktüm (adresleri ve kaynak konumlarını sildim):

```
$ cat ast.c
double sin(double);
double f(double x) { return x * x * sin(x) + 3 / (1 - x); }
$ clang -fsyntax-only -Xclang -ast-dump -Xclang -ast-dump-filter=f ast.c
FunctionDecl f 'double (double)' external-linkage
|-ParmVarDecl used x 'double'
`-CompoundStmt
  `-ReturnStmt
    `-BinaryOperator 'double' '+'
      |-BinaryOperator 'double' '*'
      | |-BinaryOperator 'double' '*'
      | | |-ImplicitCastExpr 'double'
      | | | `-DeclRefExpr 'double' lvalue ParmVar 'x' 'double'
      | | `-ImplicitCastExpr 'double'
      | |   `-DeclRefExpr 'double' lvalue ParmVar 'x' 'double'
      | `-CallExpr 'double'
      |   |-ImplicitCastExpr 'double (*)(double)'
      |   | `-DeclRefExpr 'double (double)' Function 'sin' 'double (double)'
      |   `-ImplicitCastExpr 'double'
      |     `-DeclRefExpr 'double' lvalue ParmVar 'x' 'double'
      `-BinaryOperator 'double' '/'
        |-ImplicitCastExpr 'double'
        | `-IntegerLiteral 'int' 3
        `-ParenExpr 'double'
          `-BinaryOperator 'double' '-'
            |-ImplicitCastExpr 'double'
            | `-IntegerLiteral 'int' 1
            `-ImplicitCastExpr 'double'
              `-DeclRefExpr 'double' lvalue ParmVar 'x' 'double'
```

Şekil bizimkinin aynısı: kökte `+`, solda çarpım, sağda bölme. Farklar derleyicinin ek işleri:

- **Türler**: her düğümün bir türü var (`'double'`) ve dönüşümler açıkça birer düğüm (`ImplicitCastExpr`: `3`, `int`'ten `double`'a). Ders 3.5'teki tamsayı yükseltme kuralları bu düğümleri üretiyor.
- **`ParenExpr`**: Clang parantezleri de saklıyor. Uyarılar için (`if (a = b)` ile `if ((a = b))` arasındaki fark) ve kaynağı birebir geri üretmek için.
- **Değerler ve yerler**: `lvalue` bir değişkenin **yeri**, `ImplicitCastExpr` (LValueToRValue) onu değere çeviriyor. CAS'ımızda atama olmadığı için bu ayrım yok.
- `x^2` yerine `x * x`: C'de üs işleci yok. `^` C'de XOR (Ders 5.1), bu yüzden C kodunda `pow` yazmak gerekiyor.

---

## Alıştırmalar

**1** – Dilbilgisine örtük çarpma ekle: `2x`, `3sin(x)`, `(x+1)(x-1)`. Hangi durumlarda belirsizlik çıkıyor? (`sin x` ve `xy` düşün.)

**2** – `i_yaz`'ın, `TOPLA`'nın sağ çocuğu eksi olduğunda `a + (-b)` yerine `a - b` yazmasını isteyelim. Yaz-ayrıştır döngüsü neden bozulur? Döngüyü korumak için ne yapılabilir?

**3** – Ayrıştırıcıyı **Pratt** (öncelik tırmanma) yöntemiyle yeniden yaz: her işlecin sol ve sağ bağlanma gücü (`+`: 1/2, `*`: 3/4, `^`: 6/5) ve tek bir döngü. Yeni bir işleç eklemek iki yöntemde nasıl farklı?

**4** – `sin x` için daha iyi bir hata mesajı üret: bilinen bir fonksiyon adının ardından `(` gelmezse "sin'den sonra '(' bekleniyordu" desin. Ama `sinx` bir değişken mi olmalı?

**5** – `i_degerle`'yi aynı ifadeyi milyonlarca kez değerlendirmek için hızlandır: ağacı bir kez **postfix** komut dizisine derle (Ders 8.4), sonra bir yığın makinesiyle çalıştır. Ağaçla karşılaştırınca ne kadar hızlanıyor? Ders 10.8'deki JIT bir adım daha ileri gider: makine kodu.

<details>
<summary>Cevaplar</summary>

**1** – `birli` ile `terim` arasına bir kural: `terim := carpan (('*' | '/') carpan | carpan)*`. İkinci seçenek, bir sonraki karakter rakam, harf ya da `(` ise uygulanıyor. Belirsizlikler: `xy`, `x*y` mi yoksa `xy` adlı bir değişken mi? (Mathematica: `xy` değişken, `x y` çarpım. SymPy'nin `parse_expr`'i dönüşüm seçenekleriyle karar veriyor.) `2^3x`: $2^{3x}$ mi, $2^3 \cdot x$ mi? Örtük çarpmanın önceliği tartışmalı (`1/2x`, $\frac{1}{2x}$ mi $\frac{x}{2}$ mi?). Çoğu sistem açık `*`'yi tercih ediyor.

**2** – `a - b`, ayrıştırıldığında `CIKAR(a, b)` veriyor, `TOPLA(a, EKSI(b))` değil: farklı ağaç. Ya bu iki ağacı **eşdeğer** sayan bir eşitlik kullanırsın (yapısal değil değer eşitliği, Ders 12.12'nin kanonik formu), ya da ağaçta `CIKAR`'ı hiç tutmazsın (ayrıştırıcı `a - b`'yi doğrudan `TOPLA(a, EKSI(b))` yapar). İkincisi kanonik formun ilk adımı.

**3** – Pratt: `ifade(min_guc)`: bir `birli` oku, sonra döngü: sıradaki işlecin sol gücü `min_guc`'tan küçükse dur. Değilse işleci tüket, sağ tarafı `ifade(sag_guc)` ile oku. Sol birleşimli işleçte sağ güç soldan büyük, sağ birleşimlide küçük. Yeni bir işleç (örneğin `%`) eklemek Pratt'ta bir tablo satırı. Özyinelemeli inişte yeni bir öncelik düzeyiyse yeni bir fonksiyon ve çağrı zincirinde bir değişiklik. Pratt, işleç sayısı çok olan dillerde (C'nin 15 düzeyi) tercih ediliyor.

**4** – `atom`'da ad okunduktan sonra, ad `fonklar` listesindeyse ve sıradaki karakter `(` değilse: "'sin' fonksiyonundan sonra '(' bekleniyordu". `sinx`: bizim ayrıştırıcımız harf ve rakamları birlikte okuduğu için `sinx` tek bir ad ve bir değişken. Mesaj yalnız ad tam olarak bir fonksiyon adıysa çıkmalı.

**5** – Postfix dizi örneği: `x x 2 ^ ...` gibi; komutlar `{ITLE_SAYI v, ITLE_X, TOPLA, CARP, ..., SIN}`. Ağaç gezintisindeki işaretçi takibi (cache kaçırma, Ders 7.26), özyineleme çağrıları ve `switch` yerine düz bir diziyi okuyan bir döngü kalıyor. Tipik kazanç 2–5 kat; ölçüm senin. JIT ile her komut bir veya birkaç makine komutuna dönüşüyor ve döngü ile `switch` tamamen kalkıyor.

</details>

---

## Kaynaklar

- Alfred Aho, Monica Lam, Ravi Sethi, Jeffrey Ullman, *Compilers: Principles, Techniques, and Tools* (2. baskı), Bölüm 2.4 ve 4.4 (özyinelemeli iniş, öncelik ve birleşme yönü).
- Vaughan Pratt, "Top Down Operator Precedence", *POPL 1973*.
- Robert Nystrom, *Crafting Interpreters*, Bölüm 6 ("Parsing Expressions") ve 17 (Pratt ayrıştırıcı); craftinginterpreters.com.
- Keith Geddes, Stephen Czapor, George Labahn, *Algorithms for Computer Algebra*, Bölüm 3 (ifadelerin temsili).
- Clang belgeleri, "Introduction to the Clang AST" (clang.llvm.org/docs/IntroductionToTheClangAST.html).

**Sıradaki ders:** Sadeleştirme ve yeniden yazma kuralları. Kanonik form, `x + 0 → x`, `x * 2 → x << 1` gibi kurallar, terim yeniden yazma sistemi, sonlanma ve konfluens.
