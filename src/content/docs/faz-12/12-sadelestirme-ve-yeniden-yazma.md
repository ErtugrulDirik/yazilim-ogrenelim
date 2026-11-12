---
title: "12.12 Sadeleştirme ve yeniden yazma kuralları"
description: "Terim yeniden yazma: desen değişkenli kurallar (A + 0 -> A, A - A -> 0, N*A + M*A -> (N + M)*A), desen eşleştirme ve yerleştirme, aşağıdan yukarı sabit noktaya kadar uygulama; kesin sabit katlama (2^100, (1/2)^-3 = 8); değişmeli işlemlerde sıralı yeniden yazma ve kuralların da sıralı biçimde yazılması gereği (sin² + cos² örneği); sonlanma (A + B -> B + A ile 1001 adımda durdurma) ve konfluens (0/0'ın kural sırasına göre 0 ya da 1 olması); Q[x] kanonik formu ile sıfır testi; 100000 rastgele ifadede değer karşılaştırması ve double'ın işaretli sıfırının yarattığı 28 sahte fark; LLVM instcombine'ın x*2 -> x << 1 ve x*8/8 dönüşümleri."
---

Ders 12.11'deki ağaç, yazılanı olduğu gibi tutuyor: `x*1 + 0*y` beş işlemli bir ağaç. Bir CAS'ın ilk işi bunu `x`'e indirmek. Ders 12.1'de bunun genel olarak **çözülemez** olduğunu gördük (Richardson teoremi: bir ifadenin sıfır olup olmadığına karar veren genel bir algoritma yok). Yine de pratikte çok iş görebilen bir mekanizma var: **yeniden yazma kuralları**. Derleyiciler aynı mekanizmayla optimizasyon yapıyor. LLVM'in `instcombine` geçişinde binlerce kural var. Bu derste mekanizmayı yazıp iki temel sorusuna bakıyoruz: her zaman bitiyor mu (**sonlanma**) ve sonuç kural sırasına bağlı mı (**konfluens**).

---

## 1. Kurallar ve desenler

Bir kural, iki ifade: `sol -> sag`. Sol taraf bir **desen**. Büyük harfler (`A`, `B`, ...) **desen değişkeni**, her alt ağaçla eşleşiyor. `N` ve `M` yalnız sayılarla eşleşiyor. Aynı harf iki kez geçerse, iki yerdeki alt ağaçlar aynı olmalı: `A - A -> 0`, `x*y - x*y`'yi sıfıra indiriyor, `x - y`'yi indirmiyor.

Kurallar, Ders 12.11'deki ayrıştırıcıyla metinden okunuyor. Bir desen de bir ifade ağacı. Eşleştirme, iki ağacı aynı anda gezmek: desende değişken varsa onu **bağla**, değilse düğüm türleri ve değerleri aynı olmalı. Yerleştirme, sağ taraftaki değişkenlerin yerine bağlanan alt ağaçların kopyalarını koymak.

**Strateji**: önce çocukları normal forma getir, sonra kökte kuralları sırayla dene. Bir kural uygulanırsa sonuç yeniden normal forma getiriliyor (yeni bir kural uygulanabilir hale gelmiş olabilir). Hiçbiri uygulanmazsa ifade bir **normal form**.

```c
/* sadele.h: terim yeniden yazma ve sadelestirme */
#ifndef SADELE_H
#define SADELE_H
#include "ifade.h"
#include "poli.h"

/* kural: sol -> sag. Desen degiskenleri tek buyuk harf: A..Z her alt agaci, N ve M yalniz sayilari eslestirir */
typedef struct { ifade *sol, *sag; } kural;

int  kural_derle(kural *k, const char *metin);       /* "A + 0 -> A"; hata -1 */
void kural_sil(kural *k);

typedef struct {
    const kural *k; int n;      /* kurallar, sirayla denenir */
    int katla;                  /* sabitleri hesapla: 2 + 3 -> 5 */
    int sirala;                 /* degismeli islemlerde cocuklari sirala */
    long adim, sinir;           /* yapilan yeniden yazma; sinira ulasinca dur */
} sistem;

ifade *normal_form(const ifade *e, sistem *s);       /* adim > sinir ise sonlanmadi */
int    i_kars(const ifade *a, const ifade *b);       /* agaclar uzerinde tam siralama */
ifade *sadelestir(const ifade *e);                   /* temel kurallar + katlama + siralama */
extern const char *TEMEL_KURALLAR[];

/* kanonik form: x'e gore polinomsa Q[x]'e cevir (yoksa -1), ve geri */
int    ifade_poli(poli *p, const ifade *e, const char *x);
ifade *poli_ifade(const poli *p, const char *x);
#endif
```

```c
/* sadele.c: desen eslestirme, kural uygulama (asagidan yukari, sabit noktaya kadar), sabit katlama */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sadele.h"

int kural_derle(kural *k, const char *metin) {
    const char *ok = strstr(metin, "->");
    if (!ok) return -1;
    char sol[256], h[128];
    snprintf(sol, sizeof sol, "%.*s", (int)(ok - metin), metin);
    ifade *l = i_ayristir(sol, h, sizeof h), *r = i_ayristir(ok + 2, h, sizeof h);
    if (!l || !r) { i_sil(l); i_sil(r); return -1; }
    sistem yalniz_katla = { 0, 0, 1, 0, 0, 1000 };   /* desendeki "-1", eksi sayi olsun */
    k->sol = normal_form(l, &yalniz_katla); k->sag = normal_form(r, &yalniz_katla);
    i_sil(l); i_sil(r);
    return 0;
}
void kural_sil(kural *k) { i_sil(k->sol); i_sil(k->sag); }

/* ---------- eslestirme ---------- */
static int desen_degiskeni(const ifade *d) { return d->t == DEG && d->ad[0] >= 'A' && d->ad[0] <= 'Z' && !d->ad[1]; }

static int eslestir(const ifade *d, const ifade *e, const ifade **bag) {
    if (desen_degiskeni(d)) {
        int i = d->ad[0] - 'A';
        if ((d->ad[0] == 'N' || d->ad[0] == 'M') && e->t != SAYI) return 0;
        if (bag[i]) return i_esit(bag[i], e);        /* ayni harf, ayni alt agac: A - A */
        bag[i] = e;
        return 1;
    }
    if (d->t != e->t) return 0;
    if (d->t == SAYI) return rat_kars(&d->r, &e->r) == 0;
    if ((d->t == DEG || d->t == FONK) && strcmp(d->ad, e->ad)) return 0;
    if (d->a && !eslestir(d->a, e->a, bag)) return 0;
    if (d->b && !eslestir(d->b, e->b, bag)) return 0;
    return 1;
}

static ifade *yerlestir(const ifade *d, const ifade **bag) {
    if (desen_degiskeni(d)) return i_kopya(bag[d->ad[0] - 'A']);
    ifade *k = i_kopya(d);                           /* yapraklar icin; ic dugumlerde cocuklari degistir */
    if (d->a) { i_sil(k->a); k->a = yerlestir(d->a, bag); }
    if (d->b) { i_sil(k->b); k->b = yerlestir(d->b, bag); }
    return k;
}

/* ---------- sabit katlama: cocuklar sayiysa kesin hesapla ---------- */
static int tamsayi_mi(const rat *r, long sinir, long *v) {
    if (!(r->q.n == 1 && r->q.d[0] == 1) || r->p.n > 1 || (r->p.n && r->p.d[0] > (uint32_t)sinir)) return 0;
    *v = r->p.n ? (long)r->p.d[0] : 0;
    if (r->p.isaret) *v = -*v;
    return 1;
}

static ifade *katla(const ifade *e) {
    if ((e->t == TOPLA || e->t == CIKAR) && e->b->t == SAYI && e->b->r.p.isaret) {   /* x + (-3) -> x - 3 */
        ifade *s = i_rat(&e->b->r); s->r.p.isaret = 0;
        return i_ikili(e->t == TOPLA ? CIKAR : TOPLA, i_kopya(e->a), s);
    }
    if (e->t == EKSI && e->a->t == SAYI && !e->a->r.p.isaret && e->a->r.p.n) {   /* -(3) -> -3 */
        ifade *s = i_rat(&e->a->r); s->r.p.isaret = 1; return s;
    }
    if (!e->a || !e->b || e->a->t != SAYI || e->b->t != SAYI) return 0;
    const rat *x = &e->a->r, *y = &e->b->r;
    rat r; rat_baslat(&r);
    switch (e->t) {
    case TOPLA: rat_topla(&r, x, y); break;
    case CIKAR: rat_cikar(&r, x, y); break;
    case CARP:  rat_carp(&r, x, y); break;
    case BOL:   if (rat_sifir_mi(y)) { rat_sil(&r); return 0; } rat_bol(&r, x, y); break;   /* 1/0 kalsin */
    case US: {
        long k;
        if (!tamsayi_mi(y, 10000, &k) || (k < 0 && rat_sifir_mi(x))) { rat_sil(&r); return 0; }   /* 2^(1/2) kalsin */
        rat_tam(&r, 1);
        for (long i = 0; i < (k < 0 ? -k : k); i++) rat_carp(&r, &r, x);
        if (k < 0) { rat b; rat_baslat(&b); rat_tam(&b, 1); rat_bol(&r, &b, &r); rat_sil(&b); }
        break;
    }
    default: rat_sil(&r); return 0;
    }
    ifade *s = i_rat(&r); rat_sil(&r);
    return s;
}

/* ---------- siralama: sayi < degisken < fonksiyon < us < carpim < toplam ... ---------- */
static int sira(tur t) { static const int s[] = { 0, 1, 7, 8, 5, 6, 4, 3, 2 }; return s[t]; }
int i_kars(const ifade *a, const ifade *b) {
    if (a->t != b->t) return sira(a->t) - sira(b->t);
    if (a->t == SAYI) return rat_kars(&a->r, &b->r);
    if (a->t == DEG || a->t == FONK) { int c = strcmp(a->ad, b->ad); if (c) return c; }
    if (a->a) { int c = i_kars(a->a, b->a); if (c) return c; }
    if (a->b) return i_kars(a->b, b->b);
    return 0;
}

/* ---------- normal form: once cocuklar, sonra kok; degisirse yeniden ---------- */
static ifade *normal(ifade *e, sistem *s) {
    if (s->adim > s->sinir) return e;
    if (e->a) e->a = normal(e->a, s);
    if (e->b) e->b = normal(e->b, s);
    ifade *y = 0;
    if (s->katla) y = katla(e);
    if (!y && s->sirala && (e->t == TOPLA || e->t == CARP)) {
        /* toplamda sayi sona (x + 1), carpimda basa (2*x); zincirde (a + b) + c, c'yi b ile karsilastir */
        ifade *sol = (e->a->t == e->t) ? e->a->b : e->a;
        int k = i_kars(sol, e->b);
        if (e->t == TOPLA && (sol->t == SAYI) != (e->b->t == SAYI)) k = sol->t == SAYI ? 1 : -1;
        if (k > 0) {
            if (e->a->t == e->t) y = i_ikili(e->t, i_ikili(e->t, i_kopya(e->a->a), i_kopya(e->b)), i_kopya(e->a->b));
            else y = i_ikili(e->t, i_kopya(e->b), i_kopya(e->a));
        }
    }
    for (int i = 0; !y && i < s->n; i++) {
        const ifade *bag[26] = { 0 };
        if (eslestir(s->k[i].sol, e, bag)) y = yerlestir(s->k[i].sag, bag);
    }
    if (!y) return e;
    s->adim++;
    i_sil(e);
    return normal(y, s);
}

ifade *normal_form(const ifade *e, sistem *s) { return normal(i_kopya(e), s); }

const char *TEMEL_KURALLAR[] = {
    "A + 0 -> A", "0 + A -> A", "A - 0 -> A", "0 - A -> -A", "A - A -> 0",
    "A * 1 -> A", "1 * A -> A", "A * 0 -> 0", "0 * A -> 0",
    "A / 1 -> A", "0 / A -> 0", "A / A -> 1",
    "A ^ 1 -> A", "A ^ 0 -> 1", "1 ^ A -> 1",
    "-0 -> 0", "-(-A) -> A", "A + -B -> A - B", "A - -B -> A + B", "-A * B -> -(A*B)", "A * -B -> -(A*B)",
    "A + A -> 2*A", "N*A + A -> (N + 1)*A", "A + N*A -> (N + 1)*A", "N*A + M*A -> (N + M)*A", "A + B - B -> A", "A + B - A -> B",
    "A * A -> A^2", "A^N * A -> A^(N + 1)", "A * A^N -> A^(N + 1)", "A^N * A^M -> A^(N + M)", "(A^N)^M -> A^(N*M)",
    "N * (M * A) -> (N*M)*A", "A * B / B -> A", "-1 * A -> -A",
    "A * (1/B) -> A/B", "1/B * A -> A/B", "A * (N*B) -> N*(A*B)", "N*A/(N*B) -> A/B", "(N*A)/N -> A",
    "A + N + M -> A + (N + M)", "A - N - M -> A - (N + M)", "A + N - M -> A + (N - M)", "A - N + M -> A - (N - M)",
    "ln(exp(A)) -> A", "exp(ln(A)) -> A", "ln(1) -> 0", "exp(0) -> 1", "sin(0) -> 0", "cos(0) -> 1",
    "cos(A)^2 + sin(A)^2 -> 1",                     /* siralanmis bicimde: sin + cos once siralanir */
    0
};

ifade *sadelestir(const ifade *e) {
    static kural k[64]; static int n = -1;
    if (n < 0) { n = 0; while (TEMEL_KURALLAR[n]) { kural_derle(&k[n], TEMEL_KURALLAR[n]); n++; } }
    sistem s = { k, n, 1, 1, 0, 100000 };
    return normal_form(e, &s);
}

/* ---------- kanonik form: Q[x] ---------- */
int ifade_poli(poli *p, const ifade *e, const char *x) {
    poli a, b; poli_baslat(&a); poli_baslat(&b);
    int h = 0;
    p->n = 0;
    switch (e->t) {
    case SAYI: poli_yer(p, 1); rat_kopyala(&p->c[0], &e->r); poli_duzelt(p); break;
    case DEG: if (strcmp(e->ad, x)) h = -1; else poli_ayarla(p, 1, 1, 1); break;
    case EKSI: h = ifade_poli(&a, e->a, x); if (!h) { rat m; rat_baslat(&m); rat_tam(&m, -1); poli_skaler(p, &a, &m); rat_sil(&m); } break;
    case TOPLA: case CIKAR: case CARP:
        h = ifade_poli(&a, e->a, x) || ifade_poli(&b, e->b, x) ? -1 : 0;
        if (!h) { if (e->t == TOPLA) poli_topla(p, &a, &b); else if (e->t == CIKAR) poli_cikar(p, &a, &b); else poli_carp(p, &a, &b); }
        break;
    case BOL:                                         /* yalniz sabite bolme polinom kalir */
        h = ifade_poli(&a, e->a, x) || ifade_poli(&b, e->b, x) || b.n != 1 ? -1 : 0;
        if (!h) { rat t; rat_baslat(&t); rat_tam(&t, 1); rat_bol(&t, &t, &b.c[0]); poli_skaler(p, &a, &t); rat_sil(&t); }
        break;
    case US: {                                        /* us negatif olmayan kucuk tamsayi olmali */
        long k;
        if (e->b->t != SAYI || !tamsayi_mi(&e->b->r, 1000, &k) || k < 0 || ifade_poli(&a, e->a, x)) { h = -1; break; }
        poli_ayarla(p, 0, 1, 1);
        for (long i = 0; i < k; i++) poli_carp(p, p, &a);
        break;
    }
    default: h = -1;
    }
    poli_sil(&a); poli_sil(&b);
    return h;
}

ifade *poli_ifade(const poli *p, const char *x) {   /* buyuk dereceden kucuge: c_n x^n + ... */
    ifade *e = 0;
    for (size_t i = p->n; i-- > 0;) {
        if (rat_sifir_mi(&p->c[i])) continue;
        rat m; rat_baslat(&m); rat_kopyala(&m, &p->c[i]);
        int eksi = m.p.isaret; m.p.isaret = 0;
        ifade *t = i == 0 ? 0 : i == 1 ? i_deg(x) : i_ikili(US, i_deg(x), i_sayi((int64_t)i));
        int bir = m.p.n == 1 && m.p.d[0] == 1 && m.q.n == 1 && m.q.d[0] == 1;
        if (!t) t = i_rat(&m);
        else if (!bir) t = i_ikili(CARP, i_rat(&m), t);
        rat_sil(&m);
        if (!e) e = eksi ? i_eksi(t) : t;
        else e = i_ikili(eksi ? CIKAR : TOPLA, e, t);
    }
    return e ? e : i_sayi(0);
}
```

Kural dışında iki mekanizma daha var:

- **Sabit katlama**: iki çocuğu da sayı olan bir işlemi **kesin** hesapla: `2 + 3*4 - 1/2` → `27/2`. Ders 12.6'daki `rat` sayesinde $2^{100}$ da $\frac{1}{2^{-3}}$ da tam. Bölen sıfırsa ya da üs tamsayı değilse ($2^{1/2}$) katlama yapılmıyor: o ifade olduğu gibi kalıyor. Kural tablosundaki desenler de derlenirken katlanıyor: `-1 * A` deseni, ağaçtaki eksi bir sayıyla eşleşebilsin.
- **Sıralama**: `TOPLA` ve `CARP` değişmeli. $x + 1$ ile $1 + x$ aynı şey, ama yapısal olarak farklı ağaçlar. Her değişmeli düğümde çocukları sabit bir tam sıraya göre diziyoruz (`i_kars`): toplamda sayılar sona ($x + 5$), çarpımda başa ($6x$). `(a + b) + c` zincirinde de `c`'yi `b` ile karşılaştırıp yer değiştiriyoruz. Zincir, kabarcık sıralaması gibi adım adım sıraya giriyor.

---

## 2. Sonuçlar

```c
/* sadele_demo.c: kurallarla sadelestirme, kanonik form, sonlanmama, konfluens ve dogruluk sinamasi */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "bn_mod.h"
#include "sadele.h"

static void goster(const char *metin) {
    char h[128];
    ifade *e = i_ayristir(metin, h, sizeof h), *s = sadelestir(e);
    char *y = i_yaz(s);
    printf("  %-28s -> %-22s (%zu -> %zu dugum)\n", metin, y, i_boyut(e), i_boyut(s));
    free(y); i_sil(e); i_sil(s);
}

static void kanonik(const char *metin) {
    char h[128];
    ifade *e = i_ayristir(metin, h, sizeof h), *s = sadelestir(e);
    poli p; poli_baslat(&p);
    char *y = i_yaz(s);
    if (ifade_poli(&p, e, "x") == 0) {
        ifade *k = poli_ifade(&p, "x"); char *z = i_yaz(k);
        printf("  %-28s kurallar: %-18s kanonik: %s\n", metin, y, z);
        free(z); i_sil(k);
    } else printf("  %-28s kurallar: %-18s kanonik: (polinom degil)\n", metin, y);
    free(y); poli_sil(&p); i_sil(e); i_sil(s);
}

static uint64_t s = 21;
static ifade *rastgele(int d) {                     /* sadelestirilecek bol firsat: 0, 1, x, ayni alt agaclar */
    int r = (int)(rastgele64(&s) % 100);
    if (d == 0 || r < 30) {
        if (r % 2) return i_deg("x");
        return i_sayi((int64_t)(rastgele64(&s) % 4));
    }
    static const tur t[] = { TOPLA, CIKAR, CARP, BOL, US };
    if (r < 38) return i_eksi(rastgele(d - 1));
    if (r < 46) { static const char *f[] = { "sin", "cos", "exp", "ln" }; return i_fonk(f[rastgele64(&s) % 4], rastgele(d - 1)); }
    if (r < 56) { ifade *a = rastgele(d - 1); return i_ikili(t[rastgele64(&s) % 3], a, i_kopya(a)); }   /* A op A */
    tur k = t[rastgele64(&s) % 5];
    ifade *a = rastgele(d - 1);
    return i_ikili(k, a, k == US ? i_sayi((int64_t)(rastgele64(&s) % 4)) : rastgele(d - 1));
}

int main(void) {
    printf("Temel kurallar:\n");
    const char *ornek[] = { "x + 0", "x*1 + 0*y", "2 + 3*4 - 1/2", "x + x + x", "x*x*x", "(x^2)^3*x", "2*(3*x)",
                            "3 + x + 2", "x*3*2", "ln(exp(x + 1))", "sin(x)^2 + cos(x)^2", "cos(x)^2 + sin(x)^2",
                            "x - (y - y)", "-(-(x))*1", "x/x", "0/0", "2^100", "(1/2)^-3", 0 };
    for (int i = 0; ornek[i]; i++) goster(ornek[i]);

    printf("\nKanonik form (Q[x]):\n");
    kanonik("(x + 1)^2 - (x^2 + 2*x + 1)");
    kanonik("(x + 1)^3");
    kanonik("(x - 1)*(x + 1) - x*x");
    kanonik("x/2 + x/3");
    kanonik("sin(x) - sin(x)");

    printf("\nSonlanma: degisme kurali A + B -> B + A eklenirse\n");
    kural k[2]; kural_derle(&k[0], "A + 0 -> A"); kural_derle(&k[1], "A + B -> B + A");
    sistem sys = { k, 2, 0, 0, 0, 1000 };
    char h[128];
    ifade *e = i_ayristir("x + y", h, sizeof h), *n = normal_form(e, &sys);
    char *y = i_yaz(n);
    printf("  x + y: %ld yeniden yazmadan sonra durduruldu, son hali %s\n", sys.adim, y);
    free(y); i_sil(n); i_sil(e);

    printf("\nKonfluens: 0/0 icin iki kural\n");
    kural a[2], b[2];
    kural_derle(&a[0], "0 / A -> 0"); kural_derle(&a[1], "A / A -> 1");
    kural_derle(&b[0], "A / A -> 1"); kural_derle(&b[1], "0 / A -> 0");
    e = i_ayristir("0/0", h, sizeof h);
    sistem s1 = { a, 2, 0, 0, 0, 100 }, s2 = { b, 2, 0, 0, 0, 100 };
    ifade *n1 = normal_form(e, &s1), *n2 = normal_form(e, &s2);
    char *y1 = i_yaz(n1), *y2 = i_yaz(n2);
    printf("  sira 1: %s   sira 2: %s\n", y1, y2);
    free(y1); free(y2); i_sil(n1); i_sil(n2); i_sil(e);

    printf("\nDogruluk: 100000 rastgele ifade, x = 0.3, 1.7, -2.2'de deger karsilastirmasi\n");
    long ayni = 0, farkli = 0, genisledi = 0, kar = 0;
    size_t once = 0, sonra = 0;
    double xs[] = { 0.3, 1.7, -2.2 };
    for (int i = 0; i < 100000; i++) {
        ifade *e = rastgele(5), *t = sadelestir(e);
        once += i_boyut(e); sonra += i_boyut(t);
        for (int j = 0; j < 3; j++) {
            double u = i_degerle(e, "x", xs[j]), v = i_degerle(t, "x", xs[j]);
            if (!isfinite(u)) { if (isfinite(v)) genisledi++; continue; }
            kar++;
            if (fabs(u - v) <= 1e-9 * fmax(1, fabs(u))) ayni++;
            else { if (++farkli <= 3) { char *p = i_yaz(e), *q = i_yaz(t); printf("  FARKLI: %s -> %s (%g / %g)\n", p, q, u, v); free(p); free(q); } }
        }
        i_sil(e); i_sil(t);
    }
    printf("  ortalama dugum %.1f -> %.1f\n", (double)once / 100000, (double)sonra / 100000);
    printf("  %ld karsilastirma: %ld ayni, %ld farkli; tanimsizken tanimli hale gelen: %ld\n", kar, ayni, farkli, genisledi);
    return 0;
}
```

```
$ clang -O2 -c sadele.c && clang -O2 sadele_demo.c bn_*.o rat.o poli.o poli_bol.o ifade.o sadele.o -o sadele_demo
$ ./sadele_demo
Temel kurallar:
  x + 0                        -> x                      (3 -> 1 dugum)
  x*1 + 0*y                    -> x                      (7 -> 1 dugum)
  2 + 3*4 - 1/2                -> 27/2                   (9 -> 1 dugum)
  x + x + x                    -> 3*x                    (5 -> 3 dugum)
  x*x*x                        -> x^3                    (5 -> 3 dugum)
  (x^2)^3*x                    -> x^7                    (7 -> 3 dugum)
  2*(3*x)                      -> 6*x                    (5 -> 3 dugum)
  3 + x + 2                    -> x + 5                  (5 -> 3 dugum)
  x*3*2                        -> 6*x                    (5 -> 3 dugum)
  ln(exp(x + 1))               -> x + 1                  (5 -> 3 dugum)
  sin(x)^2 + cos(x)^2          -> 1                      (9 -> 1 dugum)
  cos(x)^2 + sin(x)^2          -> 1                      (9 -> 1 dugum)
  x - (y - y)                  -> x                      (5 -> 1 dugum)
  -(-(x))*1                    -> x                      (5 -> 1 dugum)
  x/x                          -> 1                      (3 -> 1 dugum)
  0/0                          -> 0                      (3 -> 1 dugum)
  2^100                        -> 1267650600228229401496703205376 (3 -> 1 dugum)
  (1/2)^-3                     -> 8                      (6 -> 1 dugum)
```

Bu tablonun ilk hali daha kötüydü, ve nedenleri öğretici:

- **`x + x + x` → `x + 2*x`** çıkıyordu. İçteki `x + x` → `2*x`, sonra sıralama `2*x + x`'i `x + 2*x` yaptı ($x$, çarpımdan "küçük"). `N*A + A` kuralı ise yalnız öbür sırayla eşleşiyordu. `A + N*A` kuralını ekledim. `x*x*x` için `A * A^N` aynı şekilde.
- **`sin(x)^2 + cos(x)^2` sadeleşmiyordu.** Kural `sin(A)^2 + cos(A)^2 -> 1` diye yazılmıştı, ama sıralama girdiyi önce `cos(x)^2 + sin(x)^2`'ye çeviriyordu: kural hiç eşleşmiyordu. Doğrusu, kuralı **sıralanmış biçimde** yazmak. Şimdi iki girdi sırası da 1 veriyor. Genel ders: sıralı yeniden yazmada kuralların sol tarafları da normal formda olmalı. Yoksa hiç eşleşmeyecek kurallar yazmış olursun.
- **`x/x` → `1`** ve **`0/0` → `0`**: ikisi de matematik açısından sorunlu. Bölüm 4'te.

---

## 3. Kanonik form

Kural tabanlı sadeleştirici, kuralını bilmediği eşitliği göremez: $(x + 1)^2 - (x^2 + 2x + 1)$ sıfır, ama hiçbir kural bunu açmıyor. Polinomlar için daha güçlü bir yol var: ifadeyi Ders 12.7'deki $\mathbb{Q}[x]$ tipine **çevir**. $\mathbb{Q}[x]$'te her elemanın tek bir yazılışı var (katsayı dizisi, baştaki sıfırlar atılmış). İki polinom ancak ve ancak katsayıları aynıysa eşit. **Sıfır testi kesin ve hızlı.**

```
Kanonik form (Q[x]):
  (x + 1)^2 - (x^2 + 2*x + 1)  kurallar: (x + 1)^2 - (x^2 + 2*x + 1) kanonik: 0
  (x + 1)^3                    kurallar: (x + 1)^3          kanonik: x^3 + 3*x^2 + 3*x + 1
  (x - 1)*(x + 1) - x*x        kurallar: (x + 1)*(x - 1) - x^2 kanonik: -1
  x/2 + x/3                    kurallar: x/2 + x/3          kanonik: 5/6*x
  sin(x) - sin(x)              kurallar: 0                  kanonik: (polinom degil)
```

`ifade_poli`, ağacı aşağıdan yukarı gezip her düğümü bir polinom işlemine çeviriyor. `sin(x)` gibi polinom olmayan bir parça varsa vazgeçiyor (orada kurallar daha başarılı: `A - A`). Ders 12.1'de "CAS'lar kanonik biçimi olan alt dünyalarda çalışmayı tercih eder" demiştik. Bu, o alt dünyalardan biri. Kesirli fonksiyonlar ($\mathbb{Q}(x)$: pay ve paydası polinom, EBOB'u 1, Ders 12.8) bir sonraki. SymPy'nin `expand`, `cancel`, `together` fonksiyonları bu kanonik formlara çeviriyor. `simplify` ise bir dizi sezgiseli deneyip en kısa sonucu seçiyor.

Kanonik formun bedeli: $(x + 1)^{100}$'ü 101 terimli bir polinoma açmak. Kısa ve okunur bir ifade, uzun ve kanonik bir ifadeye dönüşüyor. "Sadeleştirme" tek bir hedef değil.

---

## 4. Sonlanma ve konfluens

```
Sonlanma: degisme kurali A + B -> B + A eklenirse
  x + y: 1001 yeniden yazmadan sonra durduruldu, son hali y + x

Konfluens: 0/0 icin iki kural
  sira 1: 0   sira 2: 1
```

**Sonlanma.** $A + B \to B + A$ doğru bir eşitlik, ama bir **kural** olarak sonsuz döngü: `x + y` → `y + x` → `x + y` → ... `sistem.sinir` 1000 adımda durduruyor. Bu yüzden değişmeliliği kural olarak değil, **sıralı yeniden yazma** olarak uyguladık: yalnız sıra düzeliyorsa yer değiştir. Sıra kesin olarak azaldığından döngü olamaz. Genel yöntem: her kuralın ifadeyi bir iyi-sıralı ölçüye göre küçülttüğünü göstermek (düğüm sayısı, ya da *yol sıralaması* gibi daha ince ölçüler). Bizim kuralların çoğu düğüm sayısını azaltıyor. Azaltmayanlar (`A + -B -> A - B`, sıralama) başka bir ölçüyü azaltıyor.

**Konfluens.** `0/0`'a iki kural uyuyor: `0 / A -> 0` ve `A / A -> 1`. Hangisi önce denenirse o kazanıyor: sonuç kural **sırasına** bağlı. Bir sistem, her ifadenin **tek** bir normal formu varsa *konfluent*. Knuth ve Bendix (1970) bunun sınanabilir olduğunu gösterdi: iki kuralın sol tarafları üst üste binebiliyorsa (burada `0/0`, iki desenin ortak örneği: bir **kritik çift**) ve her kritik çiftin iki sonucu aynı normal forma iniyorsa, sistem konfluent. Değilse, **Knuth–Bendix tamamlama** eksik kuralı ekler (burada `0 -> 1`, açıkça saçma). Asıl sorun, iki kuralın da yalnız $A \neq 0$ iken doğru olması. Doğru sistem, bu kuralları **koşullu** yazmak.

---

## 5. Doğruluk

Her kural bir matematik iddiası. Yanlış bir kural, sessizce yanlış sonuç demek. Sınama: 100000 rastgele ifadeyi sadeleştir ve üç noktada eski ve yeni değerleri karşılaştır.

```
Dogruluk: 100000 rastgele ifade, x = 0.3, 1.7, -2.2'de deger karsilastirmasi
  FARKLI: exp(x/(0^3*(-x)))*x -> x*exp(x/0) (0 / inf)
  FARKLI: exp(x/(0^3*(-x)))*x -> x*exp(x/0) (0 / inf)
  FARKLI: exp(x - x/(0/x*2)) -> exp(x - x/0) (0 / inf)
  ortalama dugum 9.4 -> 3.8
  271993 karsilastirma: 271965 ayni, 28 farkli; tanimsizken tanimli hale gelen: 5852
```

- **28 fark**. Hepsini tek tek yazdırıp inceledim, hepsinde **özgün ifade sıfıra bölüyor**. Ama `double` bunu göremiyor:
  - $0^3 \cdot (-x)$, `double`'da **eksi sıfır** ($-0.0$). $x/(-0) = -\infty$, $e^{-\infty} = 0$: özgün ifade sonlu bir sayı veriyor.
  - Başka bir örnek, `x - 3 + 3 - x`: `double`'da $1.1 \times 10^{-16}$, tam sıfır değil.

  Kesin sadeleştirici bu paydaların sıfır olduğunu biliyor. Bu farklar sadeleştiricinin değil, kayan noktanın hataları. (Fark sayısı, `-0 -> 0` kuralını ekleyince 12'den 28'e çıktı. Kural, sadeleşmiş ifadedeki `-(0)`'ları `0` yapıyor. Özgün ifade ise `double`'da hâlâ $-0$'a bölüyor ve $e^{-\infty} = 0$ gibi sonlu bir sonuç veriyor. Yeni farkların hepsi yine sıfıra bölen ifadeler.)
- **5852 kez tanım kümesi genişledi**: özgün ifade tanımsızken (NaN) sadeleşmiş hali tanımlı. Bunlar bilinçli seçimler:
  - `A * 0 -> 0`, $A$ tanımsız olsa bile ($\ln(-2) \cdot 0$).
  - `A / A -> 1`, $A = 0$'da.
  - `exp(ln(A)) -> A`, $A < 0$'da.

  Ders 12.1'in Alıştırma 4'ünde değindiğimiz "genel konumda doğru" kurallar. SymPy de `x/x`'i 1 yapıyor. Ama `sqrt(x**2)`'yi `x` yapmıyor, çünkü bu yalnız $x \ge 0$ iken doğru. SymPy'de `x = Symbol('x', positive=True)` dersen yapıyor. Doğru bir CAS, kuralları bu tür **varsayımlarla** koşullu uyguluyor.

---

## 6. Derleyicinin kuralları

LLVM'in `instcombine` geçişi, IR üzerinde çalışan bir yeniden yazma sistemi:

```
$ cat ic.c
int f(int x) { return (x * 2 + 0) * 1; }
int g(int x) { return x * 8 / 8; }
unsigned h(unsigned x) { return x * 8 / 8; }
int k(int x) { return x - x + (x ^ x); }
$ clang -O0 -Xclang -disable-O0-optnone -S -emit-llvm ic.c -o ic.ll
$ opt -passes=mem2reg -S ic.ll -o ic2.ll        # yigin degiskenlerini register'a tasi
$ opt -passes=instcombine -S ic2.ll
```

| fonksiyon | `instcombine` öncesi | sonrası |
| --- | --- | --- |
| `f` | `mul nsw %0, 2`, `add nsw %2, 0`, `mul nsw %3, 1` | `shl nsw %0, 1` |
| `g` | `mul nsw %0, 8`, `sdiv %2, 8` | `ret i32 %0` |
| `h` | `mul %0, 8`, `udiv %2, 8` | `and %0, 536870911` |
| `k` | `sub nsw %0, %0`, `xor %0, %0`, `add` | `ret i32 0` |

(Homebrew LLVM 23.1.2.) Bizim kurallarımızın aynıları: `A + 0`, `A * 1`, `A - A`, ve yol haritasındaki `x * 2 → x << 1` (`shl`).

`g` ile `h`'nin farkı bu dersin en önemli satırı:

- **İşaretli** tamsayıda $x \cdot 8 / 8 = x$, çünkü `nsw` (*no signed wrap*) bayrağı "bu çarpma taşmaz" diyor. C'de işaretli taşma tanımsız davranış (Ders 3.8), derleyici olmayacağını varsayabiliyor.
- **İşaretsiz** tamsayıda taşma tanımlı (mod $2^{32}$). $x \cdot 8$ üst 3 biti atıyor, $/8$ onları geri getirmiyor. Doğru sonuç `x & 0x1FFFFFFF`.

Aynı **kural**, farklı **varsayımlarla** farklı. Bizim `A * B / B -> A` kuralımızın derleyicideki karşılığı yalnız `nsw` varken geçerli. CAS'ta $B \neq 0$ varsayımına, derleyicide taşmama varsayımına dayanıyor.

LLVM bu kuralların doğruluğunu bir SMT çözücüyle (Alive2) **kanıtlayarak** sınıyor. Yanlış optimizasyon kuralları gerçek derleyici hatalarının bilinen bir kaynağı. Alive2 makalesi, LLVM'de bu yolla bulunmuş onlarca hatayı anlatıyor (Lopes ve diğerleri, 2021). Faz 16'da `instcombine` benzeri yerel optimizasyonları kendi derleyicimize, Faz 19'da yeniden yazma sistemlerinin biçimsel teorisini ve eşitlik doyurmayı (e-graph) yazacağız.

---

## Alıştırmalar

**1** – `A * (B + C) -> A*B + A*C` (dağılma) kuralını ekle. Sonlanıyor mu? `(A + B) * C` de gerekir mi? Kanonik formla ilişkisi ne?

**2** – `A + B - B -> A` kuralı, `x + y - x`'i sadeleştiriyor mu? Neden? Hangi ek kural ya da sıralama bunu çözer?

**3** – Koşullu kural: `A / A -> 1 [A != 0]`. `sistem`'e "bu alt ağaç kesinlikle sıfır değil" diyen basit bir analiz ekle (sıfır olmayan sayılar, `exp(...)`, `x^2 + 1` gibi). `0/0` artık nasıl sadeleşiyor?

**4** – İki kural: `f(f(A)) -> A` ve `f(f(f(A))) -> f(A)`. Kritik çiftleri bul. Sistem konfluent mi?

**5** – `instcombine`'ın `h` için ürettiği `and`'in sabiti neden `536870911`? Aynı dönüşümü `x * 6 / 6` için dene: derleyici ne yapıyor, neden?

<details>
<summary>Cevaplar</summary>

**1** – Sonlanıyor: her uygulama bir çarpma düğümünü toplamın altına itiyor ve bu, "çarpımların toplamlarının içindeki derinliği" ölçüsünü azaltıyor. Ama ifade büyüyebiliyor: $(a + b)(c + d)(e + f)$ 8 terime açılıyor. Sağdan da dağılma için `(A + B) * C` gerekli. İkisi ve sıralama, toplamlar ve çarpımlardan oluşan ifadeleri polinomun açık hali olan kanonik forma götürüyor: `ifade_poli`'nin yaptığını kurallarla yapmak, ama çok daha yavaş.

**2** – Hayır: ağaç `(x + y) - x`, desen `(A + B) - B`. $B$ hem `y` hem `x` olamıyor. Çözüm ya `A + B - A -> B` kuralı ya da daha genel bir yol: toplamları düz bir listeye (n-li toplam) çevirip terimleri sıralamak ve aynı terimleri katsayılarıyla birleştirmek. Gerçek CAS'lar böyle (SymPy'de `Add` n-li bir düğüm).

**3** – Örneğin `sifir_degil(e)`: `SAYI` ve sıfır değilse, `exp(...)`, `A^2 + N` ($N > 0$) için 1 döndürsün, bilinmiyorsa 0. Kural ancak `sifir_degil(A)` ise uygulanıyor. `0/0` artık hiçbir kurala uymuyor ve olduğu gibi kalıyor: doğru davranış (tanımsız). `x/x` de artık 1 olmuyor. Kullanıcı $x \neq 0$ varsayımını açıkça vermeli.

**4** – $f(f(f(A)))$: ilk kural içteki $f(f(A))$'yı $A$ yaparak $f(A)$ veriyor, ikinci kural da doğrudan $f(A)$. $f(f(f(f(A))))$: ilk kural dıştan uygulanırsa $f(f(A))$ → $A$. İkinci kural dış üçlüye uygulanırsa $f(f(A))$ → $A$. Hepsi aynı normal forma iniyor. İkinci kural ilkinin bir sonucu, gereksiz. Sistem konfluent.

**5** – $536870911 = 2^{29} - 1$: $x \cdot 8$ en üst 3 biti atıyor ($32 - 3 = 29$ bit kalıyor), bölme kaydırarak geri getiriyor. Kalan, $x$'in alt 29 biti. $x \cdot 6 / 6$ için böyle bir maske yok: 6 ikinin kuvveti değil, taşma bitleri karışıyor. Denedim: işaretli `x * 6 / 6` yine `ret i32 %0` oluyor (`nsw` sayesinde). İşaretsizde `instcombine` `mul` ve `udiv`'i olduğu gibi bırakıyor. Bölme ancak daha sonra, kod üretiminde Ders 5.14'teki sihirli sayılı çarpmaya dönüşüyor.

</details>

---

## Kaynaklar

- Franz Baader ve Tobias Nipkow, *Term Rewriting and All That*, Cambridge University Press, 1998 (sonlanma, konfluens, kritik çiftler, Knuth–Bendix).
- Donald Knuth ve Peter Bendix, "Simple Word Problems in Universal Algebras", *Computational Problems in Abstract Algebra*, 1970.
- Daniel Richardson, "Some Undecidable Problems Involving Elementary Functions of a Real Variable", *Journal of Symbolic Logic*, 33(4), 1968.
- Joel S. Cohen, *Computer Algebra and Symbolic Computation: Elementary Algorithms*, Bölüm 3 (otomatik sadeleştirme ve sıralama).
- Nuno Lopes, Juneyoung Lee, Chung-Kil Hur, Zhengyang Liu, John Regehr, "Alive2: Bounded Translation Validation for LLVM", *PLDI 2021*.
- LLVM kaynak kodu, `llvm/lib/Transforms/InstCombine/` (kuralların her biri bir C++ fonksiyonu).

**Sıradaki ders:** Sembolik türev. Türev kurallarının ağaç dönüşümü olarak uygulanması, sonuç sadeleştirme.
