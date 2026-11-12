---
title: "12.5 Modüler aritmetik hızlandırma"
description: "Büyük sayılarla a^e mod m: kare al ve çarp; her adımda Algoritma D ile kalan almak; Barrett indirgemesi (bölmeyi önceden hesaplanmış μ ile iki çarpmaya çevirmek, en fazla iki düzeltme, 1 075 152 indirgemede 58 655 düzeltme); Montgomery çarpması (R = B^n, REDC, 13 modunda elle örnek, CIOS ile limb limb iç içe indirgeme, Newton ile -m^-1 mod 2^32); 32 ve 64 bit limb'le Montgomery'nin karşılaştırması ve GMP ile ölçüm; EBOB, genişletilmiş Öklid ile modüler ters, Miller–Rabin; 2048 bitlik oyuncak RSA, ÇKT ile 1.10 ms'de şifre çözme ve SymPy ile bağımsız doğrulama."
---

Ders 6.22'de RSA'yı oyuncak sayılarla ($N = 3233$) kurmuştuk; gerçek RSA 2048 bit ister ve elimizde artık o boyutta sayılar var. RSA'nın bütün işi tek bir işlem: $a^e \bmod m$, $e$ ve $m$ 2048 bitlik. Bu ders o işlemi üç kez yazıyor: önce bildiğimiz parçalarla, sonra bölmeyi ortadan kaldıran iki klasik hileyle, Barrett ve Montgomery.

---

## 1. Kare al ve çarp

$e$'nin bitlerini soldan sağa gez: her bitte sonucun karesini al, bit 1 ise tabanla da çarp. 2048 bitlik bir üs yaklaşık 2048 kare ve 1024 çarpma, toplam yaklaşık 3000 modüler çarpma demek. Her çarpmadan sonra mod almazsak ara sonuç milyonlarca bit olur. Mod alırsak her şey $m$ boyutunda kalır (Ders 6.18: her adımda mod almak serbest).

En doğrudan yol: `bn_carp` ve ardından `bn_bol` ile kalan.

```c
/* bn_mod.h: modular aritmetik */
#ifndef BN_MOD_H
#define BN_MOD_H
#include "bn.h"

void bn_mod(bn *r, const bn *a, const bn *m);
void bn_usmod_duz(bn *r, const bn *a, const bn *e, const bn *m);

typedef struct { bn m, mu; size_t k; } barrett;
void barrett_kur(barrett *c, const bn *m);
void barrett_sil(barrett *c);
void barrett_indir(bn *r, const bn *x, const barrett *c);
void bn_usmod_barrett(bn *r, const bn *a, const bn *e, const barrett *c);
extern long BARRETT_DUZELTME, BARRETT_CAGRI;

typedef struct { size_t n; uint32_t *m, *r2, minv; } mont;
void mont_kur(mont *c, const bn *m);
void mont_sil(mont *c);
void mont_carp(uint32_t *r, const uint32_t *a, const uint32_t *b, const mont *c);
void bn_usmod_mont(bn *r, const bn *a, const bn *e, const mont *c);

typedef struct { size_t n; uint64_t *m, *r2, minv; } mont64;
void mont64_kur(mont64 *c, const bn *m);
void mont64_sil(mont64 *c);
void mont64_carp(uint64_t *r, const uint64_t *a, const uint64_t *b, const mont64 *c);
void bn_usmod_mont64(bn *r, const bn *a, const bn *e, const mont64 *c);

void bn_ebob(bn *g, const bn *a, const bn *b);
int  bn_ters(bn *r, const bn *a, const bn *m);
uint64_t rastgele64(uint64_t *s);
void bn_rastgele(bn *x, size_t bit, uint64_t *s);
int  bn_asal_mi(const bn *n, int tur, uint64_t *s);
#endif
```

Çarpma $O(n^2)$ (bu boyutta Karatsuba), bölme $O(n^2)$. Bölme iki kat değil, daha pahalı: Algoritma D her limb için bir tahmin, bir çarp-çıkar ve olası düzeltmeler yapıyor, ayrıca normalleştirme ve bellek ayırma var. Hızlandırmanın iki yolu da aynı fikre dayanıyor: **mod hep aynı $m$**. Bir kez önceden hesap yapıp her bölmeyi ucuzlatabiliriz.

---

## 2. Barrett indirgemesi

Ders 5.14'te derleyicinin $x / 7$'yi sihirli bir sayıyla çarpıp kaydırmaya çevirdiğini görmüştük. Barrett (1986) aynı fikrin büyük sayı hali: $\mu = \lfloor B^{2k} / m \rfloor$'yu bir kez hesapla ($k$, $m$'nin limb sayısı). Sonra her $x < m^2$ için

$$q = \left\lfloor \frac{\lfloor x / B^{k-1} \rfloor \cdot \mu}{B^{k+1}} \right\rfloor, \qquad r = x - q m$$

$B^{k-1}$ ve $B^{k+1}$'e bölmek limb atmaktır, bedava. Geriye iki çarpma kalıyor. $q$, gerçek bölümden **en fazla 2 eksik**: iki tabanda aşağı yuvarlama hatası birikiyor. Sonda en fazla iki kez $m$ çıkarıyoruz. Onluk küçük bir örnek: $m = 97$, $B = 10$, $k = 2$, $\mu = \lfloor 10^4 / 97 \rfloor = 103$. $x = 8000$ için $\lfloor 800 \cdot 103 / 1000 \rfloor = 82$: gerçek bölüm de 82, kalan 46.

```c
/* bn_mod.c: modular indirgeme ve us alma: duz yol ve Barrett */
#include <stdlib.h>
#include <string.h>
#include "bn.h"
#include "bn_mod.h"

/* r = a mod m, 0 <= r < m (a eksi olabilir, m > 0) */
void bn_mod(bn *r, const bn *a, const bn *m) {
    bn_bol(0, r, a, m);
    if (r->isaret) bn_topla(r, r, m);
}

/* 1. yol: her carpmadan sonra Algoritma D ile kalan al */
void bn_usmod_duz(bn *r, const bn *a, const bn *e, const bn *m) {
    bn x, t; bn_baslat(&x); bn_baslat(&t);
    bn_u64(&x, 1);
    bn_mod(&t, a, m);
    for (size_t i = e->n * 32; i-- > 0;) {        /* soldan saga kare al ve carp */
        bn_carp(&x, &x, &x); bn_bol(0, &x, &x, m);
        if ((e->d[i / 32] >> (i % 32)) & 1) { bn_carp(&x, &x, &t); bn_bol(0, &x, &x, m); }
    }
    bn_sil(r); *r = x; bn_sil(&t);
}

/* ---------- Barrett: mu = floor(B^(2k) / m), bolme yerine iki carpma ---------- */
void barrett_kur(barrett *c, const bn *m) {
    bn_baslat(&c->m); bn_baslat(&c->mu);
    bn_kopyala(&c->m, m);
    c->k = m->n;
    bn b2k; bn_baslat(&b2k);
    bn_yer(&b2k, 2 * c->k + 1);
    memset(b2k.d, 0, (2 * c->k + 1) * 4);
    b2k.d[2 * c->k] = 1; b2k.n = 2 * c->k + 1;
    bn_bol(&c->mu, 0, &b2k, m);
    bn_sil(&b2k);
}
void barrett_sil(barrett *c) { bn_sil(&c->m); bn_sil(&c->mu); }

/* x'in ilk s limb'ini at (x / B^s) */
static void limb_sag(bn *r, const bn *x, size_t s) {
    if (x->n <= s) { r->n = 0; r->isaret = 0; return; }
    bn_yer(r, x->n - s);
    memmove(r->d, x->d + s, (x->n - s) * 4);
    r->n = x->n - s; r->isaret = 0;
}
/* x mod B^s */
static void limb_kes(bn *x, size_t s) { if (x->n > s) { x->n = s; bn_duzelt(x); } }

long BARRETT_DUZELTME = 0, BARRETT_CAGRI = 0;

/* r = x mod m, 0 <= x < m^2 */
void barrett_indir(bn *r, const bn *x, const barrett *c) {
    size_t k = c->k;
    BARRETT_CAGRI++;
    bn q, t; bn_baslat(&q); bn_baslat(&t);
    limb_sag(&q, x, k - 1);                       /* q1 = x / B^(k-1) */
    bn_carp(&q, &q, &c->mu);                      /* q2 = q1 mu */
    limb_sag(&q, &q, k + 1);                      /* q3 = q2 / B^(k+1), gercek bolumden en fazla 2 eksik */
    bn_carp(&t, &q, &c->m);
    bn_kopyala(r, x);
    limb_kes(r, k + 1); limb_kes(&t, k + 1);      /* mod B^(k+1) yeterli */
    bn_cikar(r, r, &t);
    if (r->isaret) {                              /* B^(k+1) ekle */
        bn b; bn_baslat(&b); bn_yer(&b, k + 2);
        memset(b.d, 0, (k + 2) * 4); b.d[k + 1] = 1; b.n = k + 2;
        bn_topla(r, r, &b); bn_sil(&b);
    }
    while (bn_kars(r, &c->m) >= 0) { bn_cikar(r, r, &c->m); BARRETT_DUZELTME++; }
    bn_sil(&q); bn_sil(&t);
}

void bn_usmod_barrett(bn *r, const bn *a, const bn *e, const barrett *c) {
    bn x, t; bn_baslat(&x); bn_baslat(&t);
    bn_u64(&x, 1);
    bn_mod(&t, a, &c->m);
    for (size_t i = e->n * 32; i-- > 0;) {
        bn_carp(&x, &x, &x); barrett_indir(&x, &x, c);
        if ((e->d[i / 32] >> (i % 32)) & 1) { bn_carp(&x, &x, &t); barrett_indir(&x, &x, c); }
    }
    bn_sil(r); *r = x; bn_sil(&t);
}
```

Bir incelik: $r = x - qm$'yi tam hesaplamaya gerek yok. $r < 3m < B^{k+1}$ olduğundan iki tarafı da mod $B^{k+1}$ almak yeterli (`limb_kes`). Eksi çıkarsa $B^{k+1}$ ekleniyor.

---

## 3. Montgomery çarpması

Montgomery (1985) daha radikal: modu değiştirmiyor, **sayıların temsilini** değiştiriyor. $R = B^n > m$ seç ($m$ tek olmalı ki $\gcd(R, m) = 1$ olsun). Her $a$'yı $\tilde a = aR \bmod m$ olarak tut. İki temsili çarpınca $\tilde a \tilde b = abR^2$ çıkıyor, bize $abR$ lazım: **$R$'ye bölmek** gerekiyor. $R$ 2'nin kuvveti, dolayısıyla $R$'ye bölme kaydırmadan ibaret. Ama bu bir bölme değil, mod $m$'de $R^{-1}$ ile çarpma, ve $T$ genelde $R$'ye tam bölünmüyor.

Hile (REDC): $T$'ye $m$'nin öyle bir katını ekle ki toplam $R$'ye tam bölünsün. $m' = -m^{-1} \bmod R$ ise $q = T m' \bmod R$ için $T + qm \equiv T - T \equiv 0 \pmod R$. Mod $m$'de $qm$ eklemek değeri değiştirmiyor.

$$\text{REDC}(T) = \frac{T + (T m' \bmod R)\, m}{R} \equiv T R^{-1} \pmod m$$

$T < m^2$ ise sonuç $< 2m$: en fazla bir çıkarma. Elle bir örnek: $m = 13$, $R = 16$, $m' = -13^{-1} \bmod 16 = 11$. $a = 7$, $b = 9$:

- $\tilde a = 7 \cdot 16 \bmod 13 = 8$, $\tilde b = 9 \cdot 16 \bmod 13 = 1$
- $T = 8 \cdot 1 = 8$, $q = 8 \cdot 11 \bmod 16 = 8$, $(8 + 8 \cdot 13)/16 = 112/16 = 7$
- 7, $63 \cdot 16 \bmod 13$ ile aynı: $\widetilde{ab}$. Çıkış için bir REDC daha: $\text{REDC}(7) = 11 = 63 \bmod 13$. ✓

Her şey Montgomery temsilinde kalıyor: girişte bir kez $\tilde a = \text{REDC}(a \cdot (R^2 \bmod m))$, çıkışta bir kez $\text{REDC}(\tilde x)$. $R^2 \bmod m$ bir kez Algoritma D ile hesaplanıyor; 3000 çarpmanın içinde hiç bölme yok.

**CIOS.** Gerçek kodda $T$'nin tamamını hesaplayıp sonra indirgemek yerine, her limb çarpımından hemen sonra **tek limb'lik** bir indirgeme yapılıyor: $q_i = t_0 m' \bmod 2^{32}$ ve $t \leftarrow (t + q_i m)/2^{32}$. Böylece ara sonuç $n + 2$ limb'de kalıyor ve $m'$ yalnız $m$'nin en düşük limb'inin tersi oluyor. Koç, Acar ve Kaliski (1996) bunun beş farklı sıralamasını karşılaştırmış; *Coarsely Integrated Operand Scanning* en çok kullanılanı.

$m'$'yi Newton yöntemiyle buluyoruz: $m$ tekse $x = m$ zaten mod 8'de doğru bir ters ($m^2 \equiv 1 \pmod 8$), ve $x \leftarrow x(2 - mx)$ her adımda doğru bit sayısını ikiye katlıyor: $3 \to 6 \to 12 \to 24 \to 48$. 32 bit için 4 adım, 64 bit için 5.

```c
/* bn_mont.c: Montgomery carpmasi, 32 ve 64 bit limb ile */
#include <stdlib.h>
#include <string.h>
#include "bn.h"
#include "bn_mod.h"

/* ---------- Montgomery: R = B^n, a -> aR mod m, carp(aR, bR) = abR ---------- */
void mont_kur(mont *c, const bn *m) {                 /* m tek olmali */
    c->n = m->n;
    c->m = malloc(c->n * 4); memcpy(c->m, m->d, c->n * 4);
    uint32_t m0 = m->d[0], inv = m0;                  /* m0 * inv = 1 mod 2^3 (m0 tek) */
    for (int i = 0; i < 4; i++) inv *= 2 - m0 * inv;  /* Newton: her adimda dogru bit sayisi ikiye katlanir */
    c->minv = (uint32_t)0 - inv;                      /* -m^-1 mod 2^32 */
    bn r2, b; bn_baslat(&r2); bn_baslat(&b);          /* R^2 mod m: bir kez, Algoritma D ile */
    bn_yer(&b, 2 * c->n + 1); memset(b.d, 0, (2 * c->n + 1) * 4);
    b.d[2 * c->n] = 1; b.n = 2 * c->n + 1;
    bn_bol(0, &r2, &b, m);
    c->r2 = calloc(c->n, 4); memcpy(c->r2, r2.d, r2.n * 4);
    bn_sil(&r2); bn_sil(&b);
}
void mont_sil(mont *c) { free(c->m); free(c->r2); }

/* r = a b R^-1 mod m (CIOS: carp ve indirgemeyi limb limb ic ice yap).
   a, b < m, n limb; r n limb (r, a ya da b olabilir) */
void mont_carp(uint32_t *r, const uint32_t *a, const uint32_t *b, const mont *c) {
    size_t n = c->n;
    uint32_t t[n + 2];
    memset(t, 0, sizeof t);
    for (size_t i = 0; i < n; i++) {
        uint64_t C = 0, bi = b[i];
        for (size_t j = 0; j < n; j++) {              /* t += a * b[i] */
            uint64_t s = t[j] + a[j] * bi + C;
            t[j] = (uint32_t)s; C = s >> 32;
        }
        uint64_t s = (uint64_t)t[n] + C;
        t[n] = (uint32_t)s; t[n + 1] = (uint32_t)(s >> 32);
        uint64_t q = (uint32_t)(t[0] * c->minv);      /* t + q m, 2^32'ye tam bolunsun */
        C = (t[0] + q * c->m[0]) >> 32;               /* en dusuk limb sifir olur: at */
        for (size_t j = 1; j < n; j++) {              /* t = (t + q m) / 2^32 */
            uint64_t s2 = t[j] + q * c->m[j] + C;
            t[j - 1] = (uint32_t)s2; C = s2 >> 32;
        }
        s = (uint64_t)t[n] + C;
        t[n - 1] = (uint32_t)s;
        t[n] = t[n + 1] + (uint32_t)(s >> 32);
    }
    /* t < 2m: gerekirse bir kez m cikar */
    if (t[n] || mag_kars(t, n, c->m, n) >= 0) mag_cikar(t, t, n + 1, c->m, n);
    memcpy(r, t, n * 4);
}

void bn_usmod_mont(bn *r, const bn *a, const bn *e, const mont *c) {
    size_t n = c->n;
    uint32_t x[n], t[n], bir[n];
    bn am; bn_baslat(&am);
    bn mm = { c->m, n, n, 0 };
    bn_mod(&am, a, &mm);
    memset(t, 0, sizeof t); memcpy(t, am.d, am.n * 4);
    mont_carp(t, t, c->r2, c);                        /* t = a R mod m */
    memset(bir, 0, sizeof bir); bir[0] = 1;
    mont_carp(x, bir, c->r2, c);                      /* x = 1 R mod m */
    for (size_t i = e->n * 32; i-- > 0;) {
        mont_carp(x, x, x, c);
        if ((e->d[i / 32] >> (i % 32)) & 1) mont_carp(x, x, t, c);
    }
    mont_carp(x, x, bir, c);                          /* Montgomery'den cik: x R^-1 */
    bn_yer(r, n); memcpy(r->d, x, n * 4); r->n = n; r->isaret = 0;
    bn_duzelt(r);
    bn_sil(&am);
}

/* ---------- Montgomery, 64 bit limb: ayni algoritma, __uint128_t ile ---------- */
typedef unsigned __int128 u128;

void mont64_kur(mont64 *c, const bn *m) {
    c->n = (m->n + 1) / 2;
    c->m = calloc(c->n, 8); memcpy(c->m, m->d, m->n * 4);   /* little-endian: iki 32'lik = bir 64'luk */
    uint64_t m0 = c->m[0], inv = m0;
    for (int i = 0; i < 5; i++) inv *= 2 - m0 * inv;
    c->minv = 0 - inv;
    bn r2, b; bn_baslat(&r2); bn_baslat(&b);
    size_t k = 4 * c->n + 1;                                /* R^2 = 2^(128 n) */
    bn_yer(&b, k); memset(b.d, 0, k * 4); b.d[k - 1] = 1; b.n = k;
    bn_bol(0, &r2, &b, m);
    c->r2 = calloc(c->n, 8); memcpy(c->r2, r2.d, r2.n * 4);
    bn_sil(&r2); bn_sil(&b);
}
void mont64_sil(mont64 *c) { free(c->m); free(c->r2); }

void mont64_carp(uint64_t *r, const uint64_t *a, const uint64_t *b, const mont64 *c) {
    size_t n = c->n;
    uint64_t t[n + 2];
    memset(t, 0, sizeof t);
    for (size_t i = 0; i < n; i++) {
        u128 C = 0;
        for (size_t j = 0; j < n; j++) {
            u128 s = (u128)a[j] * b[i] + t[j] + (uint64_t)C;
            t[j] = (uint64_t)s; C = s >> 64;
        }
        u128 s = (u128)t[n] + (uint64_t)C;
        t[n] = (uint64_t)s; t[n + 1] = (uint64_t)(s >> 64);
        uint64_t q = t[0] * c->minv;
        C = ((u128)q * c->m[0] + t[0]) >> 64;
        for (size_t j = 1; j < n; j++) {
            u128 s2 = (u128)q * c->m[j] + t[j] + (uint64_t)C;
            t[j - 1] = (uint64_t)s2; C = s2 >> 64;
        }
        s = (u128)t[n] + (uint64_t)C;
        t[n - 1] = (uint64_t)s;
        t[n] = t[n + 1] + (uint64_t)(s >> 64);
    }
    int buyuk = t[n] != 0;
    if (!buyuk) {
        buyuk = 1;                                          /* esitse de cikar */
        for (size_t j = n; j-- > 0;) if (t[j] != c->m[j]) { buyuk = t[j] > c->m[j]; break; }
    }
    if (buyuk) {
        uint64_t odunc = 0;
        for (size_t j = 0; j < n; j++) {
            u128 d = (u128)t[j] - c->m[j] - odunc;
            t[j] = (uint64_t)d; odunc = (uint64_t)(d >> 64) & 1;
        }
    }
    memcpy(r, t, n * 8);
}

void bn_usmod_mont64(bn *r, const bn *a, const bn *e, const mont64 *c) {
    size_t n = c->n;
    uint64_t x[n], t[n], bir[n];
    bn am, mm; bn_baslat(&am); bn_baslat(&mm);
    bn_yer(&mm, 2 * n); memcpy(mm.d, c->m, n * 8); mm.n = 2 * n; bn_duzelt(&mm);
    bn_mod(&am, a, &mm);
    memset(t, 0, sizeof t); memcpy(t, am.d, am.n * 4);
    mont64_carp(t, t, c->r2, c);
    memset(bir, 0, sizeof bir); bir[0] = 1;
    mont64_carp(x, bir, c->r2, c);
    for (size_t i = e->n * 32; i-- > 0;) {
        mont64_carp(x, x, x, c);
        if ((e->d[i / 32] >> (i % 32)) & 1) mont64_carp(x, x, t, c);
    }
    mont64_carp(x, x, bir, c);
    bn_yer(r, 2 * n); memcpy(r->d, x, n * 8); r->n = 2 * n; r->isaret = 0;
    bn_duzelt(r);
    bn_sil(&am); bn_sil(&mm);
}
```

`mont64`, aynı algoritma ama limb 64 bit. Çarpım 128 bit oluyor: C'de `unsigned __int128` (GCC ve Clang uzantısı). ARM64'te `mul` ve `umulh`, x86-64'te tek `mul` komutuna derleniyor. Limb dizimiz little-endian olduğu için iki 32 bitlik limb bellekte tam bir 64 bitlik limb: dönüşüm `memcpy`.

---

## 4. Sınama

EBOB, modüler ters ve Miller–Rabin asallık testi: Ders 6.19 ve 6.20'deki algoritmaların büyük sayı halleri.

```c
/* bn_asal.c: EBOB, modular ters, rastgele sayi, Miller-Rabin */
#include <stdlib.h>
#include <string.h>
#include "bn.h"
#include "bn_mod.h"

/* ---------- EBOB, modular ters, asallik ---------- */
void bn_ebob(bn *g, const bn *a, const bn *b) {      /* Oklid, sonuc >= 0 */
    bn x, y, r; bn_baslat(&x); bn_baslat(&y); bn_baslat(&r);
    bn_kopyala(&x, a); x.isaret = 0;
    bn_kopyala(&y, b); y.isaret = 0;
    while (y.n) { bn_bol(0, &r, &x, &y); bn_sil(&x); x = y; y = r; bn_baslat(&r); }
    bn_sil(g); *g = x; bn_sil(&y);
}

/* r = a^-1 mod m; yoksa -1 doner (genisletilmis Oklid, Ders 6.19) */
int bn_ters(bn *r, const bn *a, const bn *m) {
    bn r0, r1, s0, s1, q, t; bn_baslat(&r0); bn_baslat(&r1); bn_baslat(&s0); bn_baslat(&s1); bn_baslat(&q); bn_baslat(&t);
    bn_mod(&r0, a, m); bn_kopyala(&r1, m);
    bn_u64(&s0, 1);                                   /* s0 a = r0, s1 a = r1 (mod m) */
    while (r1.n) {
        bn_bol(&q, &t, &r0, &r1);
        bn_sil(&r0); r0 = r1; r1 = t; bn_baslat(&t);
        bn_carp(&t, &q, &s1); bn_cikar(&t, &s0, &t);
        bn_sil(&s0); s0 = s1; s1 = t; bn_baslat(&t);
    }
    int ok = r0.n == 1 && r0.d[0] == 1;
    if (ok) bn_mod(r, &s0, m);
    bn_sil(&r0); bn_sil(&r1); bn_sil(&s0); bn_sil(&s1); bn_sil(&q); bn_sil(&t);
    return ok ? 0 : -1;
}

/* xorshift64*: tekrarlanabilir rastgelelik (kriptografik DEGIL) */
uint64_t rastgele64(uint64_t *s) { *s ^= *s >> 12; *s ^= *s << 25; *s ^= *s >> 27; return *s * 0x2545F4914F6CDD1Dull; }

void bn_rastgele(bn *x, size_t bit, uint64_t *s) {   /* tam bit bitlik: en ust bit 1 */
    size_t n = (bit + 31) / 32;
    bn_yer(x, n);
    for (size_t i = 0; i < n; i++) x->d[i] = (uint32_t)rastgele64(s);
    size_t ust = bit - 32 * (n - 1);                  /* son limb'deki bit sayisi */
    if (ust < 32) x->d[n - 1] &= (1u << ust) - 1;
    x->d[n - 1] |= 1u << (ust - 1);
    x->n = n; x->isaret = 0;
}

/* Miller-Rabin (Ders 6.20), Montgomery ile; n tek ve > 3 */
int bn_asal_mi(const bn *n, int tur, uint64_t *s) {
    static const uint32_t kucuk[] = { 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47 };
    for (int i = 0; i < 14; i++) {                    /* ucuz on eleme */
        uint32_t tmp[n->n];
        if (mag_bol_limb(tmp, n->d, n->n, kucuk[i]) == 0) return n->n == 1 && n->d[0] == kucuk[i];
    }
    mont c; mont_kur(&c, n);
    bn d, bir, n1, a, x; bn_baslat(&d); bn_baslat(&bir); bn_baslat(&n1); bn_baslat(&a); bn_baslat(&x);
    bn_u64(&bir, 1); bn_cikar(&n1, n, &bir);          /* n - 1 = 2^k d, d tek */
    bn_kopyala(&d, &n1);
    int k = 0;
    while (!(d.d[0] & 1)) {                           /* d >>= 1 */
        for (size_t i = 0; i < d.n; i++) d.d[i] = (d.d[i] >> 1) | (i + 1 < d.n ? d.d[i + 1] << 31 : 0);
        bn_duzelt(&d); k++;
    }
    int asal = 1;
    for (int t = 0; t < tur && asal; t++) {
        bn_rastgele(&a, 32 * n->n - 2, s);            /* a < n */
        bn_mod(&a, &a, n);
        if (a.n == 0 || bn_kars(&a, &bir) == 0) continue;
        bn_usmod_mont(&x, &a, &d, &c);
        if (bn_kars(&x, &bir) == 0 || bn_kars(&x, &n1) == 0) continue;
        int tanik = 1;
        for (int i = 1; i < k; i++) {
            bn_carp(&x, &x, &x); bn_mod(&x, &x, n);
            if (bn_kars(&x, &n1) == 0) { tanik = 0; break; }
        }
        if (tanik) asal = 0;                          /* a, n'nin bilesik oldugunun tanigi */
    }
    mont_sil(&c);
    bn_sil(&d); bn_sil(&bir); bn_sil(&n1); bn_sil(&a); bn_sil(&x);
    return asal;
}
```

`uret.py`'ye iki mod ekledik: `usmod` Python'un `pow(a, e, m)`'si ile, `ebob` de `math.gcd` ve `pow(a, -1, m)` ile vektör üretiyor.

```c
/* sina_mod.c: uc usmod yolu Python'un pow'u ile ayni mi */
#include <stdio.h>
#include <string.h>
#include "bn.h"
#include "bn_mod.h"

int main(void) {
    char a_[3000], e_[3000], m_[3000], s_[3000];
    long satir = 0, hata = 0;
    bn a, e, m, s, r; bn_baslat(&a); bn_baslat(&e); bn_baslat(&m); bn_baslat(&s); bn_baslat(&r);
    while (scanf("%2999s %2999s %2999s %2999s", a_, e_, m_, s_) == 4) {
        bn_hexten(&a, a_); bn_hexten(&e, e_); bn_hexten(&m, m_); bn_hexten(&s, s_);
        satir++;
        bn_usmod_duz(&r, &a, &e, &m);
        if (bn_kars(&r, &s)) { hata++; printf("duz: %s^%s mod %s\n", a_, e_, m_); }
        barrett b; barrett_kur(&b, &m);
        bn_usmod_barrett(&r, &a, &e, &b);
        if (bn_kars(&r, &s)) { hata++; printf("barrett: %s^%s mod %s\n", a_, e_, m_); }
        barrett_sil(&b);
        mont c; mont_kur(&c, &m);
        bn_usmod_mont(&r, &a, &e, &c);
        if (bn_kars(&r, &s)) { hata++; printf("mont: %s^%s mod %s\n", a_, e_, m_); }
        mont_sil(&c);
        mont64 c6; mont64_kur(&c6, &m);
        bn_usmod_mont64(&r, &a, &e, &c6);
        if (bn_kars(&r, &s)) { hata++; printf("mont64: %s^%s mod %s\n", a_, e_, m_); }
        mont64_sil(&c6);
    }
    printf("%ld satir, 4 yol, %ld hata, Barrett: %ld indirgeme, %ld duzeltme\n", satir, hata, BARRETT_CAGRI, BARRETT_DUZELTME);
    return 0;
}
```

```
$ clang -O2 -c bn_temel.c bn_carp.c bn_bol.c bn_mod.c bn_mont.c bn_asal.c
$ python3 uret.py usmod 5 3000 > v_usmod.txt
$ clang -O2 sina_mod.c bn_*.o -o sina_mod && ./sina_mod < v_usmod.txt
3000 satir, 4 yol, 0 hata, Barrett: 1075152 indirgeme, 58655 duzeltme
$ python3 uret.py ebob 6 20000 > v_ebob.txt
$ clang -O2 sina_ebob.c bn_*.o -o sina_ebob && ./sina_ebob < v_ebob.txt
20000 satir, 424 ters, 0 hata
```

Barrett'ın tahmini indirgemelerin yüzde 94.5'inde zaten doğru; düzeltme yüzde 5.5 oranında çalışıyor. Bu kez nadir dal rastgele testte de tetikleniyor (Ders 12.4'ün geri ekleme adımının tersine).

---

## 5. Hız

```c
/* hiz_mod.c: a^e mod m, e ve m ayni boyutta: duz, Barrett, Montgomery, GMP */
#include <stdio.h>
#include <stdlib.h>
#include <gmp.h>
#include "olcum.h"
#include "bn.h"
#include "bn_mod.h"

static void gmp_al(mpz_t z, const bn *x) { mpz_import(z, x->n, -1, 4, 0, 0, x->d); }

int main(void) {
    uint64_t s = 12;
    printf("  bit     duz   Barrett   Mont32   Mont64      GMP   (ms, bir us alma)\n");
    for (size_t bit = 256; bit <= 4096; bit *= 2) {
        bn a, e, m, r; bn_baslat(&a); bn_baslat(&e); bn_baslat(&m); bn_baslat(&r);
        bn_rastgele(&m, bit, &s); m.d[0] |= 1;
        bn_rastgele(&e, bit, &s);
        bn_rastgele(&a, bit - 1, &s);
        int tekrar = bit <= 1024 ? 20 : 3;
        double t0 = simdi();
        for (int i = 0; i < tekrar; i++) bn_usmod_duz(&r, &a, &e, &m);
        double t1 = simdi();
        barrett b; barrett_kur(&b, &m);
        for (int i = 0; i < tekrar; i++) bn_usmod_barrett(&r, &a, &e, &b);
        double t2 = simdi();
        mont c; mont_kur(&c, &m);
        for (int i = 0; i < tekrar; i++) bn_usmod_mont(&r, &a, &e, &c);
        double t3 = simdi();
        mont64 c6; mont64_kur(&c6, &m);
        for (int i = 0; i < tekrar; i++) bn_usmod_mont64(&r, &a, &e, &c6);
        double t35 = simdi();
        mpz_t ga, ge, gm, gr; mpz_inits(ga, ge, gm, gr, NULL);
        gmp_al(ga, &a); gmp_al(ge, &e); gmp_al(gm, &m);
        for (int i = 0; i < tekrar; i++) mpz_powm(gr, ga, ge, gm);
        double t4 = simdi();
        bn kontrol; bn_baslat(&kontrol);
        bn_yer(&kontrol, m.n); size_t say = 0;
        mpz_export(kontrol.d, &say, -1, 4, 0, 0, gr); kontrol.n = say; bn_duzelt(&kontrol);
        printf("%5zu %8.2f %8.2f %8.2f %8.2f %8.3f   %s\n", bit,
               (t1 - t0) * 1e3 / tekrar, (t2 - t1) * 1e3 / tekrar, (t3 - t2) * 1e3 / tekrar, (t35 - t3) * 1e3 / tekrar, (t4 - t35) * 1e3 / tekrar,
               bn_kars(&kontrol, &r) ? "FARKLI" : "GMP ile ayni");
        barrett_sil(&b); mont_sil(&c); mont64_sil(&c6);
        bn_sil(&a); bn_sil(&e); bn_sil(&m); bn_sil(&r); bn_sil(&kontrol);
        mpz_clears(ga, ge, gm, gr, NULL);
    }
    return 0;
}
```

```
$ clang -O2 hiz_mod.c bn_*.o -I/opt/homebrew/include -L/opt/homebrew/lib -lgmp -o hiz_mod
$ ./hiz_mod
  bit     duz   Barrett   Mont32   Mont64      GMP   (ms, bir us alma)
  256     0.28     0.34     0.10     0.04    0.030   GMP ile ayni
  512     1.26     0.88     0.31     0.10    0.048   GMP ile ayni
 1024     3.85     3.94     3.49     0.54    0.231   GMP ile ayni
 2048    25.83    26.29    25.33     4.90    1.606   GMP ile ayni
 4096   182.75   168.44   252.55    45.09   11.956   GMP ile ayni
```

Beklediğimiz tablo bu değildi:

- **Küçük boyutta** (256–512 bit) Montgomery 32, düz yoldan 3–4 kat hızlı. Burada maliyetin çoğu `bn_bol`'un sabit giderleri: normalleştirme, iki `malloc`, kopyalar. Montgomery ise yığında, ayırmasız çalışıyor.
- **Büyük boyutta** üç 32 bitlik yol aşağı yukarı eşit. Barrett iki çarpma yapıyor, Algoritma D de limb başına bir çarp-çıkar: ikisi de $O(n^2)$ ve limb başına maliyetleri benzer. Montgomery de $2n^2$ limb çarpımı yapıyor. Hepsini aynı şey sınırlıyor: Ders 12.3'te gördüğümüz, limb başına birkaç döngülük elde zinciri.
- **Montgomery 64**, Montgomery 32'den **5 kat** hızlı. Limb sayısı yarıya inince limb çarpımı sayısı dörtte bire iniyor ve ARM64 64×64 → 128 çarpımı neredeyse 32×32 kadar ucuza yapıyor. Asıl ders burada: **limb genişliği, algoritma seçiminden daha büyük bir etken.** Bütün kütüphaneyi 64 bit limb'le yazmak da doğal bir seçenek olurdu. Ders 12.2'de okunabilirlik için 32 biti seçmiştik.
- **Barrett'ın üstünlüğü** donanımda bölmenin çok pahalı olduğu yerde (mikrodenetleyiciler, bölme komutu olmayan çipler) ve indirgenen sayının sabit olduğu kriptografik bağlamlarda ortaya çıkıyor. Ayrıca $m$'nin tek olmasını istemiyor; Montgomery istiyor.
- **GMP**, 2048 bitte Mont64'ten 3 kat hızlı: assembly ile yazılmış çarpma çekirdeği ve karesi alınan sayı için ayrı bir kare alma rutini ($a^2$'de $a_i a_j$ ve $a_j a_i$ aynı: yarı çarpım). Bir de *pencereli* üs alma: bitleri tek tek değil 4–6'lık gruplar halinde işleyerek çarpma sayısını 1024'ten yaklaşık 400'e indiriyor.

---

## 6. 2048 bitlik oyuncak RSA

:::caution
Bu kod eğitim amaçlı. Gerçek RSA'da *padding* (OAEP), kriptografik rastgelelik ve sabit zamanlı kod şart. Bizim `rastgele64` tahmin edilebilir; üs alma süresi de $d$'nin bitlerine göre değişiyor (zamanlama saldırısı, Kocher 1996). Gerçek işte OpenSSL, libsodium ya da işletim sisteminin kütüphanesini kullan.
:::

```c
/* rsa.c: 2048 bitlik oyuncak RSA (ders amacli: padding yok, rastgelelik kriptografik degil) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gmp.h>
#include "olcum.h"
#include "bn.h"
#include "bn_mod.h"

static int deneme;
static void asal_uret(bn *p, size_t bit, uint64_t *s) {
    deneme = 0;
    do {
        bn_rastgele(p, bit, s);
        p->d[0] |= 1;                                   /* tek */
        p->d[p->n - 1] |= 1u << ((bit - 1) % 32 - 1);   /* en ust iki bit 1: p q tam 2 bit sayisi */
        deneme++;
    } while (!bn_asal_mi(p, 40, s));
}

static void gmp_al(mpz_t z, const bn *x) { mpz_import(z, x->n, -1, 4, 0, 0, x->d); }

int main(void) {
    uint64_t s = 2026;
    bn p, q, n, phi, e, d, bir, t, m, c, r;
    bn_baslat(&p); bn_baslat(&q); bn_baslat(&n); bn_baslat(&phi); bn_baslat(&e); bn_baslat(&d);
    bn_baslat(&bir); bn_baslat(&t); bn_baslat(&m); bn_baslat(&c); bn_baslat(&r);

    double t0 = simdi();
    asal_uret(&p, 1024, &s); int dp = deneme;
    asal_uret(&q, 1024, &s); int dq = deneme;
    double t1 = simdi();
    printf("p: %d aday, q: %d aday, toplam %.0f ms\n", dp, dq, (t1 - t0) * 1e3);

    bn_carp(&n, &p, &q);
    bn_u64(&bir, 1); bn_u64(&e, 65537);
    bn_cikar(&t, &p, &bir); bn_cikar(&phi, &q, &bir); bn_carp(&phi, &phi, &t);
    if (bn_ters(&d, &e, &phi)) { printf("e, phi ile aralarinda asal degil\n"); return 1; }
    printf("n: %zu bit, d: %zu bit\n", n.n * 32 - __builtin_clz(n.d[n.n - 1]), d.n * 32 - __builtin_clz(d.d[d.n - 1]));

    const char *mesaj = "Merhaba, Faz 12!";
    size_t uz = strlen(mesaj);                          /* byte'lar buyuk sayi: ilk byte en anlamli */
    bn_u64(&m, 0);
    for (size_t i = 0; i < uz; i++) { bn_u64(&t, 256); bn_carp(&m, &m, &t); bn_u64(&t, (uint8_t)mesaj[i]); bn_topla(&m, &m, &t); }

    mont mn; mont_kur(&mn, &n);
    bn_usmod_mont(&c, &m, &e, &mn);                     /* sifrele: c = m^e mod n */
    char *ch = bn_hexe(&c);
    printf("sifreli: %.32s... (%zu hex basamak)\n", ch, strlen(ch));

    barrett br; barrett_kur(&br, &n);
    mont64 m6; mont64_kur(&m6, &n);
    mpz_t gc, gd, gn, gr; mpz_inits(gc, gd, gn, gr, NULL); gmp_al(gc, &c); gmp_al(gd, &d); gmp_al(gn, &n);

    /* CKT ile cozme (Ders 6.22): yari boyutta iki us */
    bn dp_, dq_, qinv, mp, mq, p1, q1; bn_baslat(&dp_); bn_baslat(&dq_); bn_baslat(&qinv); bn_baslat(&mp); bn_baslat(&mq); bn_baslat(&p1); bn_baslat(&q1);
    bn_cikar(&p1, &p, &bir); bn_cikar(&q1, &q, &bir);
    bn_mod(&dp_, &d, &p1); bn_mod(&dq_, &d, &q1); bn_ters(&qinv, &q, &p);
    mont64 mp6, mq6; mont64_kur(&mp6, &p); mont64_kur(&mq6, &q);

    const char *ad[] = { "duz (Algoritma D)", "Barrett", "Montgomery 32", "Montgomery 64", "Montgomery 64 + CKT", "GMP mpz_powm" };
    for (int y = 0; y < 6; y++) {
        int tekrar = 10;
        double a0 = simdi();
        for (int i = 0; i < tekrar; i++) {
            if (y == 0) bn_usmod_duz(&r, &c, &d, &n);
            if (y == 1) bn_usmod_barrett(&r, &c, &d, &br);
            if (y == 2) bn_usmod_mont(&r, &c, &d, &mn);
            if (y == 3) bn_usmod_mont64(&r, &c, &d, &m6);
            if (y == 4) {                               /* m = mq + q ((mp - mq) qinv mod p) */
                bn_usmod_mont64(&mp, &c, &dp_, &mp6);
                bn_usmod_mont64(&mq, &c, &dq_, &mq6);
                bn_cikar(&t, &mp, &mq); bn_carp(&t, &t, &qinv); bn_mod(&t, &t, &p);
                bn_carp(&t, &t, &q); bn_topla(&r, &t, &mq);
            }
            if (y == 5) mpz_powm(gr, gc, gd, gn);
        }
        double a1 = simdi();
        if (y == 5) { size_t k; bn_yer(&r, n.n); mpz_export(r.d, &k, -1, 4, 0, 0, gr); r.n = k; r.isaret = 0; bn_duzelt(&r); }
        char cozum[64]; size_t k = 0;                   /* sayiyi byte'lara geri cevir */
        bn_kopyala(&t, &r);
        uint8_t ters[64];
        while (t.n && k < 64) { ters[k++] = (uint8_t)mag_bol_limb(t.d, t.d, t.n, 256); bn_duzelt(&t); }
        for (size_t i = 0; i < k; i++) cozum[i] = (char)ters[k - 1 - i];
        cozum[k] = 0;
        printf("  %-20s %7.2f ms  \"%s\"\n", ad[y], (a1 - a0) * 1e3 / tekrar, cozum);
    }

    FILE *f = fopen("rsa_kontrol.txt", "w");            /* Python ile bagimsiz kontrol icin */
    char *hp = bn_hexe(&p), *hq = bn_hexe(&q), *hd = bn_hexe(&d);
    fprintf(f, "%s\n%s\n%s\n%s\n", hp, hq, hd, ch);
    fclose(f);
    return 0;
}
```

```
$ clang -O2 rsa.c bn_*.o -I/opt/homebrew/include -L/opt/homebrew/lib -lgmp -o rsa
$ ./rsa
p: 663 aday, q: 130 aday, toplam 1046 ms
n: 2048 bit, d: 2048 bit
sifreli: c53fcd47febd6d23c0795cf562014199... (512 hex basamak)
  duz (Algoritma D)      25.87 ms  "Merhaba, Faz 12!"
  Barrett                28.10 ms  "Merhaba, Faz 12!"
  Montgomery 32          25.24 ms  "Merhaba, Faz 12!"
  Montgomery 64           4.91 ms  "Merhaba, Faz 12!"
  Montgomery 64 + CKT     1.10 ms  "Merhaba, Faz 12!"
  GMP mpz_powm            1.64 ms  "Merhaba, Faz 12!"
```

- **Asal arama**: Ders 6.17'deki asal sayı teoremine göre 1024 bit civarında rastgele bir sayının asal olma olasılığı $1/\ln 2^{1024} \approx 1/710$; yalnız tek sayılara baktığımız için ortalama 355 aday. 663 ve 130, beklenen dağılımla uyumlu (geometrik dağılım: sapma, ortalama kadar büyük). Adayların çoğunu küçük asallara bölme eliyor; Miller–Rabin'in tam üs alması yalnız ilk elemeyi geçenlerde çalışıyor.
- **ÇKT**: Ders 6.22'deki Garner formülü. İki 1024 bitlik üs, bir 2048 bitlik üsten 4.5 kat hızlı: çarpma maliyeti 4'te 1, üs uzunluğu yarı, ama iki üs. Teorik kazanç 4 kat; ek kazanç, 1024 bitlik sayıların L1 cache'te daha rahat durmasından olabilir. Böylece **GMP'nin düz `powm`'unu geçtik**: algoritma (ÇKT) uygulamayı (assembly) yendi. GMP'ye de ÇKT uygulansa yine 3 kat önde olurdu.

Python ve SymPy ile bağımsız kontrol: program $p$, $q$, $d$ ve şifreli metni `rsa_kontrol.txt`'ye yazıyor.

```
$ python3 -c "
from sympy import isprime
p, q, d, c = [int(l, 16) for l in open('rsa_kontrol.txt')]
n = p * q; e = 65537
print('p asal:', isprime(p), ' q asal:', isprime(q), ' n bit:', n.bit_length())
print('e d mod phi =', (e * d) % ((p - 1) * (q - 1)))
m = pow(c, d, n); print(m.to_bytes((m.bit_length() + 7) // 8, 'big'))"
p asal: True  q asal: True  n bit: 2048
e d mod phi = 1
b'Merhaba, Faz 12!'
```

---

## Alıştırmalar

**1** – Montgomery, $m$ çift olunca neden çalışmaz? $m = 12$, $R = 16$ için $m'$'yi bulmaya çalış.

**2** – `mont_carp`'ın sonunda neden **en fazla bir** çıkarma yetiyor? $a, b < m$ ve $m < R$ varsayımlarıyla sonucun $2m$'den küçük olduğunu göster.

**3** – Kare al ve çarp, $e$'nin bit sayısı $k$ ve 1 bit sayısı $w$ ise kaç modüler çarpma yapar? 65537 için kaç? Şifrelemenin şifre çözmeden neden yüzlerce kat hızlı olduğunu buradan açıkla.

**4** – 4 bitlik **sabit pencere**: $a^0, \dots, a^{15}$'i önceden hesapla, sonra üssü 4'er bit gez: 4 kare ve 1 çarpma. 2048 bitlik bir üs için çarpma sayısını kare al ve çarp ile karşılaştır. `bn_usmod_mont64`'e ekleyip ölç.

**5** – `rastgele64`'ün yerine `/dev/urandom`'dan (Ders 10.2'deki `open` ve `read`) okuyan bir `bn_rastgele` yaz. Neden bu da tek başına "güvenli RSA" için yetmez?

<details>
<summary>Cevaplar</summary>

**1** – $m' = -m^{-1} \bmod R$ var olmalı, yani $\gcd(m, R) = 1$. $R$ 2'nin kuvveti olduğundan $m$ tek olmalı. $m = 12$ için $12x \equiv 1 \pmod{16}$'nın çözümü yok: sol taraf hep çift. RSA'da $n = pq$ tek, sorun yok. Çift modlarda Barrett ya da düz yol kullanılır.

**2** – $T = ab < m^2$, $q < R$ ve $(T + qm)/R < (m^2 + Rm)/R = m(m/R + 1) < 2m$, çünkü $m < R$. CIOS'ta da aynı sınır her adımda tutuyor: ara $t$ hep $< 2m$ ve $n + 2$ limb'e sığıyor.

**3** – $k - 1$ kare ve $w - 1$ çarpma (ilk 1 bitte kare almaya gerek yok, ama bizim kodumuz $x = 1$'den başlayıp gereksiz kareler de alıyor). $65537 = 2^{16} + 1$: 16 kare, 1 çarpma. 2048 bitlik $d$ için yaklaşık 2047 kare ve 1024 çarpma, toplam yaklaşık 3070: 180 kat fazla. Bu yüzden $e$ küçük seçiliyor ve şifreleme ile imza doğrulama ucuz.

**4** – Kare al ve çarp: 2048 kare + ortalama 1024 çarpma. Pencere: 2048 kare + $2048/4 = 512$ çarpma + 14 ön hesap. Yaklaşık yüzde 16 tasarruf. Kayan (sliding) pencere ve daha geniş pencerelerle çarpma sayısı 400'ün altına iniyor; karelerin sayısı ise değişmiyor, oradaki kazanç ancak hızlı kare alma rutiniyle geliyor.

**5** – Rastgelelik tek sorun değil: padding olmadan küçük mesajlar ve aynı mesajın tekrarı saldırıya açık ($m^e < n$ ise $c$'nin $e$. kökü düz tamsayı kökü olur). Üs alma süresi $d$'nin bitlerine bağlı (zamanlama ve güç tüketimi yan kanalları), ve bellekte kalan $d$ silinmiyor. Kriptografi yazmak, doğru matematikten çok daha fazlası.

</details>

---

## Kaynaklar

- Peter L. Montgomery, "Modular Multiplication Without Trial Division", *Mathematics of Computation*, 44(170), 1985.
- Paul Barrett, "Implementing the Rivest Shamir and Adleman Public Key Encryption Algorithm on a Standard Digital Signal Processor", *CRYPTO '86*.
- Çetin Kaya Koç, Tolga Acar, Burton S. Kaliski Jr., "Analyzing and Comparing Montgomery Multiplication Algorithms", *IEEE Micro*, 16(3), 1996.
- Alfred Menezes, Paul van Oorschot, Scott Vanstone, *Handbook of Applied Cryptography*, Bölüm 14 (ücretsiz PDF: cacr.uwaterloo.ca/hac).
- Richard Brent ve Paul Zimmermann, *Modern Computer Arithmetic*, §2.4 (Barrett, Montgomery, REDC).
- Paul Kocher, "Timing Attacks on Implementations of Diffie-Hellman, RSA, DSS, and Other Systems", *CRYPTO '96*.

**Sıradaki ders:** Rasyonel sayılar. EBOB ile sadeleştirilmiş kesir tipi ve kesin Gauss eliminasyonu.
