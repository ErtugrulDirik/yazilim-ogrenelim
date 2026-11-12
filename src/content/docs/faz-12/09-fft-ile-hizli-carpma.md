---
title: "12.9 FFT ile hızlı çarpma"
description: "Çarpmayı değerlendirme ve ara değerlemeye çevirmek: polinomu n noktada değerlendirip noktasal çarpmak; birim kökleri ve DFT; Cooley–Tukey FFT (böl ve yönet, O(n log n)), bit-ters sıralama ve kelebek; karmaşık FFT ile büyük sayı çarpımı ve 16 bitlik parçalarda 262144 limb'de yuvarlama hatasının 0.5'e ulaşıp sonucu bozması; NTT: Goldilocks cismi p = 2^64 - 2^32 + 1'de bölmesiz indirgeme ve tam sonuç; Karatsuba ile kesişmenin 512–1024 limb arasında olması, 1 milyon limb'de NTT'nin GMP'den yalnız 1.7 kat yavaş kalması."
---

Ders 12.3'te Karatsuba ile $O(n^2)$'yi $O(n^{1.58})$'e indirdik, Toom-Cook'un $O(n^{1.46})$ verdiğini söyledik. Bu derste çarpmayı neredeyse doğrusal zamana, $O(n \log n)$'ye indiren fikri yazıyoruz: **hızlı Fourier dönüşümü**. Ders 12.7'de büyük sayıyı polinoma ve polinomu büyük sayıya çevirebildiğimizi gördük. FFT ikisini de hızlandırıyor.

---

## 1. Çarpma yerine değerlendirme

Derecesi $< n$ olan bir polinom, $n$ katsayısıyla ya da **$n$ farklı noktadaki değerleriyle** tamamen belirlenir: değerlerden katsayılara giden doğrusal sistemin matrisi (Vandermonde matrisi) tersinir, sistem Ders 6.26'daki anlamda tek çözümlü. İki temsilde işlem maliyetleri çok farklı:

| | katsayılar | değerler |
| --- | --- | --- |
| toplama | $O(n)$ | $O(n)$ |
| çarpma | $O(n^2)$ | $O(n)$: $c(x_i) = a(x_i) \cdot b(x_i)$ |
| değerlendirme | $O(n)$ (Horner) | ? |

Çarpma, değerler temsilinde noktasal. Plan:

1. $a$ ve $b$'yi $2n$ noktada **değerlendir** (çarpımın derecesi $< 2n$, yani $2n$ değer gerekiyor).
2. Değerleri noktasal çarp.
3. $2n$ değerden çarpımın katsayılarını **geri bul** (ara değerleme).

Rastgele noktalarda 1. ve 3. adım $O(n^2)$, kazanç yok. Hile noktaları seçmekte.

---

## 2. Birim kökleri ve DFT

Noktalar $\omega^0, \omega^1, \dots, \omega^{n-1}$ olsun: $\omega = e^{-2\pi i / n}$, $n$. dereceden ilkel birim kökü ($\omega^n = 1$, daha küçük kuvveti 1 değil). $a$'nın bu noktalardaki değerleri **ayrık Fourier dönüşümü** (DFT):

$$A_k = \sum_{j=0}^{n-1} a_j\, \omega^{jk}$$

Neden bu noktalar? $a$'yı çift ve tek katsayılarına ayır: $a(x) = a_{\text{çift}}(x^2) + x\, a_{\text{tek}}(x^2)$. $\omega^k$'nın karesi $\omega^{2k}$, ve $(\omega^2)$ bir $n/2$. dereceden birim kökü. Yani $n$ noktada değerlendirme, iki **yarı boyutlu** değerlendirmeye iniyor:

$$A_k = E_k + \omega^k O_k, \qquad A_{k + n/2} = E_k - \omega^k O_k$$

($\omega^{n/2} = -1$ olduğundan ikinci yarı bedava.) $E$ ve $O$, $a_{\text{çift}}$ ve $a_{\text{tek}}$'in $n/2$ noktalı DFT'leri. $T(n) = 2T(n/2) + O(n)$, Master teoremiyle (Ders 6.13) $O(n \log n)$. Cooley ve Tukey (1965). Fikrin izi Gauss'un 1805 tarihli yayımlanmamış notlarına kadar gidiyor.

**Ters DFT** aynı formül, $\omega$ yerine $\omega^{-1}$ ve sonda $1/n$ ile çarparak. Ara değerleme de $O(n \log n)$.

Özyinelemeyi yerinde ve döngüyle yazmanın standart yolu: önce diziyi **bit-ters** sıraya diz ($a[6] = a[110_2] \leftrightarrow a[011_2] = a[3]$), sonra $m = 2, 4, 8, \dots, n$ boyunda gruplar halinde **kelebek** işlemini uygula: $(u, t) \to (u + wt, u - wt)$.

```c
/* fft.h: karmasik FFT ve sayi-teorik donusum (NTT), buyuk sayi carpimina uygulama */
#ifndef FFT_H
#define FFT_H
#include <complex.h>
#include "bn.h"

void fft(double complex *a, size_t n, int ters);     /* n 2'nin kuvveti; ters: 1/n dahil */
void ntt(uint64_t *a, size_t n, int ters);           /* mod p = 2^64 - 2^32 + 1 */
uint64_t gl_carp(uint64_t a, uint64_t b);            /* a b mod p */
double bn_carp_fft(bn *r, const bn *a, const bn *b, int bit);  /* bit: parca genisligi; en buyuk yuvarlama hatasi doner */
void bn_carp_ntt(bn *r, const bn *a, const bn *b);
#endif
```

```c
/* fft.c: Cooley-Tukey, yerinde, bit-ters sirali; karmasik ve mod p */
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "fft.h"

static void bit_ters(void *v, size_t n, size_t boy) {   /* a[i] <-> a[ters(i)] */
    char *a = v, tmp[16];
    for (size_t i = 1, j = 0; i < n; i++) {
        size_t bit = n >> 1;
        for (; j & bit; bit >>= 1) j ^= bit;
        j ^= bit;
        if (i < j) { memcpy(tmp, a + i * boy, boy); memcpy(a + i * boy, a + j * boy, boy); memcpy(a + j * boy, tmp, boy); }
    }
}

/* ---------- karmasik FFT ---------- */
void fft(double complex *a, size_t n, int ters) {
    double complex *w = malloc(n / 2 * sizeof *w);       /* w[k] = e^(-+2 pi i k / n): her biri dogrudan, hata birikmesin */
    for (size_t k = 0; k < n / 2; k++) w[k] = cexp((ters ? 2 : -2) * M_PI * I * k / n);
    bit_ters(a, n, sizeof *a);
    for (size_t m = 2; m <= n; m *= 2) {                /* m: kelebek grubu boyu, kokler w[k n/m] */
        size_t adim = n / m;
        for (size_t j = 0; j < n; j += m)
            for (size_t k = 0; k < m / 2; k++) {
                double complex u = a[j + k], t = w[k * adim] * a[j + k + m / 2];
                a[j + k] = u + t; a[j + k + m / 2] = u - t;
            }
    }
    free(w);
    if (ters) for (size_t i = 0; i < n; i++) a[i] /= n;
}

/* ---------- Goldilocks cismi: p = 2^64 - 2^32 + 1 ---------- */
#define P 0xffffffff00000001ull
typedef unsigned __int128 u128;

/* 2^64 = 2^32 - 1 ve 2^96 = -1 (mod p): 128 bitlik sayiyi bolmesiz indirge */
static inline uint64_t indir(u128 x) {
    uint64_t lo = (uint64_t)x, hi = (uint64_t)(x >> 64);
    uint64_t hh = hi >> 32, hl = hi & 0xffffffff;
    uint64_t t = lo - hh;                                /* lo - hh 2^96 */
    if (lo < hh) t -= 0xffffffff;                        /* odunc: -2^64 = -(2^32 - 1) */
    uint64_t u = hl * 0xffffffff;                        /* hl 2^64 = hl (2^32 - 1) */
    uint64_t r = t + u;
    if (r < u) r += 0xffffffff;                          /* tasma: 2^64 = 2^32 - 1 */
    if (r >= P) r -= P;
    return r;
}
uint64_t gl_carp(uint64_t a, uint64_t b) { return indir((u128)a * b); }
static inline uint64_t gl_topla(uint64_t a, uint64_t b) { uint64_t r = a + b; if (r < a || r >= P) r -= P; return r; }
static inline uint64_t gl_cikar(uint64_t a, uint64_t b) { return a >= b ? a - b : a + (P - b); }
static uint64_t gl_us(uint64_t a, uint64_t e) { uint64_t r = 1; for (; e; e >>= 1, a = gl_carp(a, a)) if (e & 1) r = gl_carp(r, a); return r; }

/* 7, cismin carpimsal grubunu uretir; p - 1 = 2^32 (2^32 - 1), yani 2^32. dereceden birim kokleri var */
void ntt(uint64_t *a, size_t n, int ters) {
    bit_ters(a, n, sizeof *a);
    for (size_t m = 2; m <= n; m *= 2) {
        uint64_t wm = gl_us(7, (P - 1) / m);             /* ilkel m. birim koku */
        if (ters) wm = gl_us(wm, P - 2);                 /* tersi (Fermat) */
        uint64_t *w = malloc(m / 2 * 8);
        w[0] = 1;
        for (size_t k = 1; k < m / 2; k++) w[k] = gl_carp(w[k - 1], wm);   /* kesin: hata birikmez */
        for (size_t j = 0; j < n; j += m)
            for (size_t k = 0; k < m / 2; k++) {
                uint64_t u = a[j + k], t = gl_carp(w[k], a[j + k + m / 2]);
                a[j + k] = gl_topla(u, t); a[j + k + m / 2] = gl_cikar(u, t);
            }
        free(w);
    }
    if (ters) { uint64_t nt = gl_us(n, P - 2); for (size_t i = 0; i < n; i++) a[i] = gl_carp(a[i], nt); }
}

/* ---------- buyuk sayi carpimi: limb'leri parcalara bol, evrisim, elde yay ---------- */
static size_t ust2(size_t n) { size_t k = 1; while (k < n) k *= 2; return k; }

static uint32_t parca(const bn *x, size_t i, int bit) {  /* x'in i. "bit" bitlik parcasi */
    size_t b = i * bit;
    uint64_t v = x->d[b / 32];
    if (b / 32 + 1 < x->n) v |= (uint64_t)x->d[b / 32 + 1] << 32;
    return (uint32_t)(v >> (b % 32)) & ((1u << bit) - 1);
}

/* c[i] (her biri < 2^64) * 2^(bit i) toplamini r'ye yaz */
static void elde_yay(bn *r, const uint64_t *c, size_t m, int bit) {
    size_t limb = (m * bit) / 32 + 4;
    bn_yer(r, limb); memset(r->d, 0, limb * 4);
    u128 elde = 0;
    size_t yazilan = 0;                                  /* r'nin kac biti kesinlesti */
    uint64_t tampon = 0; int tb = 0;
    for (size_t i = 0; i < m || elde; i++) {
        if (i < m) elde += c[i];
        tampon |= (uint64_t)(elde & ((1u << bit) - 1)) << tb;   /* en dusuk "bit" biti bu yuvanin */
        tb += bit; elde >>= bit;
        while (tb >= 32) { r->d[yazilan++] = (uint32_t)tampon; tampon >>= 32; tb -= 32; }
    }
    if (tb) r->d[yazilan++] = (uint32_t)tampon;
    r->n = yazilan; r->isaret = 0; bn_duzelt(r);
}

double bn_carp_fft(bn *r, const bn *a, const bn *b, int bit) {
    size_t na = (a->n * 32 + bit - 1) / bit, nb = (b->n * 32 + bit - 1) / bit, n = ust2(na + nb);
    double complex *x = calloc(n, sizeof *x), *y = calloc(n, sizeof *y);
    for (size_t i = 0; i < na; i++) x[i] = parca(a, i, bit);
    for (size_t i = 0; i < nb; i++) y[i] = parca(b, i, bit);
    fft(x, n, 0); fft(y, n, 0);
    for (size_t i = 0; i < n; i++) x[i] *= y[i];         /* evrisim teoremi: carpim noktasal */
    fft(x, n, 1);
    uint64_t *c = malloc(n * 8);
    double hata = 0;
    for (size_t i = 0; i < n; i++) {
        double v = creal(x[i]), yuv = round(v);
        if (fabs(v - yuv) > hata) hata = fabs(v - yuv);
        c[i] = yuv < 0 ? 0 : (uint64_t)yuv;
    }
    int isaret = a->isaret ^ b->isaret;
    elde_yay(r, c, n, bit);
    r->isaret = r->n ? isaret : 0;
    free(x); free(y); free(c);
    return hata;
}

void bn_carp_ntt(bn *r, const bn *a, const bn *b) {
    const int bit = 16;                                  /* evrisim degeri < n 2^32 < p: tek asal yeter */
    size_t na = a->n * 2, nb = b->n * 2, n = ust2(na + nb);
    uint64_t *x = calloc(n, 8), *y = calloc(n, 8);
    for (size_t i = 0; i < na; i++) x[i] = parca(a, i, bit);
    for (size_t i = 0; i < nb; i++) y[i] = parca(b, i, bit);
    ntt(x, n, 0); ntt(y, n, 0);
    for (size_t i = 0; i < n; i++) x[i] = gl_carp(x[i], y[i]);
    ntt(x, n, 1);
    int isaret = a->isaret ^ b->isaret;
    elde_yay(r, x, n, bit);
    r->isaret = r->n ? isaret : 0;
    free(x); free(y);
}
```

---

## 3. Karmaşık FFT ve yuvarlama

Büyük sayıyı **16 bitlik parçalara** böl: bir polinom, $x = 2^{16}$'da değerlendirilmiş hali. İki polinomu FFT ile çarp, katsayıları en yakın tamsayıya yuvarla, eldeyi yay (`elde_yay`): Ders 12.7'deki Kronecker'in tersi. Çarpım katsayısı en fazla $n \cdot (2^{16})^2 = n \cdot 2^{32}$. `double`'ın 53 bitine sığdığı sürece yuvarlama doğru katsayıyı veriyor.

Ama FFT tam değil: $\cos$, $\sin$ ve her kelebek bir yuvarlama hatası ekliyor. `bn_carp_fft` bu yüzden en büyük yuvarlama hatasını da döndürüyor: $|v - \text{round}(v)|$. 0.5'e yaklaşınca sonuç yanlış olabilir.

---

## 4. NTT: hatasız FFT

FFT'nin ihtiyacı **karmaşık sayılar değil, birim kökleri**. $n$. dereceden ilkel bir birim kökü olan herhangi bir halkada aynı algoritma çalışıyor. Sonlu cisim $\mathbb{Z}_p$'de (Ders 6.24) çarpımsal grup $p - 1$ elemanlı ve devirli (Ders 6.22). $n \mid p - 1$ ise $n$. dereceden kökler var. Bu **sayı-teorik dönüşüm** (NTT) ve hiç yuvarlama yok: her şey tamsayı.

Asal seçimi önemli. $p = 2^{64} - 2^{32} + 1$ (kriptografi topluluğunda "Goldilocks" asalı diye biliniyor):

- $p - 1 = 2^{32} (2^{32} - 1)$: $2^{32}$'ye kadar her 2'nin kuvveti boyunda dönüşüm var.
- 64 bite sığıyor, çarpım `__uint128_t`.
- **Bölmesiz indirgeme**: $2^{64} \equiv 2^{32} - 1$ ve $2^{96} \equiv -1 \pmod p$. 128 bitlik $x = x_0 + 2^{64} x_1 + 2^{96} x_2$ ($x_1$, $x_2$ 32'şer bit), yani $x \equiv x_0 + (2^{32} - 1) x_1 - x_2$: bir çıkarma, bir 32×32 çarpma, bir toplama ve en fazla iki düzeltme. Ders 12.5'teki Montgomery'ye bile gerek yok, çünkü asal özel biçimli.
- 16 bitlik parçalarla çarpım katsayısı $< n \cdot 2^{32} < p$, $n < 2^{31}$ olduğu sürece: tek asal, ÇKT yok.

Kökü bulmak için cismin bir **üreteci** lazım: 7. O zaman $\omega_m = 7^{(p-1)/m}$, $m$. dereceden ilkel kök. 7'nin üreteç olduğunu Python ile kontrol ettim: $p - 1 = 2^{32} \cdot 3 \cdot 5 \cdot 17 \cdot 257 \cdot 65537$ ve her asal çarpan $q$ için `pow(7, (p-1)//q, p) != 1` (Ders 6.22: mertebe $p-1$'in her özbölenini aşıyor). `sina_fft` de dolaylı bir sınama: kök yanlış olsaydı ters NTT çarpımı geri vermezdi.

```c
/* sina_fft.c: Goldilocks indirgemesi, NTT ve FFT carpimi, Karatsuba (bn_carp) ile */
#include <stdio.h>
#include "bn.h"
#include "bn_mod.h"
#include "fft.h"

int main(void) {
    uint64_t s = 99, P = 0xffffffff00000001ull;
    long hata = 0;
    for (int i = 0; i < 10000000; i++) {                 /* indirgeme: u128 % p ile */
        uint64_t a = rastgele64(&s), b = rastgele64(&s);
        if (i % 3 == 0) a = P - 1 - (a & 15);            /* sinira yakin degerler */
        if (i % 5 == 0) b = P - 1 - (b & 15);
        a %= P; b %= P;
        if (gl_carp(a, b) != (uint64_t)((unsigned __int128)a * b % P)) hata++;
    }
    printf("gl_carp: 10^7 carpim, %ld hata\n", hata);
    hata = 0;
    int deneme = 0;
    for (size_t n = 1; n <= 3000; n = n * 3 / 2 + 1)
        for (int k = 0; k < 5; k++) {
            bn a, b, r1, r2, r3; bn_baslat(&a); bn_baslat(&b); bn_baslat(&r1); bn_baslat(&r2); bn_baslat(&r3);
            bn_rastgele(&a, 32 * n - (k * 7) % 31, &s);
            bn_rastgele(&b, 32 * (n / (k + 1) + 1), &s);
            if (k == 4) for (size_t i = 0; i < a.n; i++) a.d[i] = 0xffffffff;   /* hep 1: en buyuk evrisim */
            if (k == 3) b.isaret = 1;
            bn_carp(&r1, &a, &b); bn_carp_ntt(&r2, &a, &b); bn_carp_fft(&r3, &a, &b, 16);
            if (bn_kars(&r1, &r2)) hata++;
            if (bn_kars(&r1, &r3)) hata++;
            deneme++;
            bn_sil(&a); bn_sil(&b); bn_sil(&r1); bn_sil(&r2); bn_sil(&r3);
        }
    printf("NTT ve FFT(16 bit): %d carpim, %ld hata\n", deneme, hata);
    return 0;
}
```

```
$ clang -O2 -c fft.c && clang -O2 sina_fft.c bn_*.o fft.o -o sina_fft && ./sina_fft
gl_carp: 10^7 carpim, 0 hata
NTT ve FFT(16 bit): 90 carpim, 0 hata
```

İndirgeme, $p$'ye yakın ve rastgele 10 milyon çarpımda `__uint128_t % p` ile aynı. Çarpımlar, 1 limb'den 3000 limb'e kadar, işaretli ve "hep 1" (en büyük evrişim değeri) girdilerle Karatsuba ile aynı.

---

## 5. Hız ve doğruluk

```c
/* hiz_fft.c: n limb x n limb: Karatsuba, NTT, karmasik FFT, GMP (uc olcumun en kucugu);
   FFT'nin yuvarlama hatasi rastgele ve "hep 1" girdide */
#include <stdio.h>
#include <gmp.h>
#include "olcum.h"
#include "bn.h"
#include "bn_mod.h"
#include "fft.h"

#define OLC(sonuc, ifade) do { sonuc = 1e9; for (int t_ = 0; t_ < 3; t_++) { double a_ = simdi(); ifade; double b_ = simdi() - a_; if (b_ < sonuc) sonuc = b_; } } while (0)

int main(void) {
    uint64_t s = 1;
    printf("   limb   Karatsuba        NTT   FFT 16 bit  hata(rastgele/hep 1)        GMP   GMP ile karsilastirma\n");
    for (size_t n = 1024; n <= (1u << 20); n *= 4) {
        bn a, b, r1, r2, r3, r4, h, g; bn_baslat(&a); bn_baslat(&b); bn_baslat(&r1); bn_baslat(&r2); bn_baslat(&r3); bn_baslat(&r4); bn_baslat(&h); bn_baslat(&g);
        bn_rastgele(&a, 32 * n, &s); bn_rastgele(&b, 32 * n, &s);
        double tk = -1, tn, tf, tg, e1 = 0, e2;
        if (n <= 65536) OLC(tk, bn_carp(&r1, &a, &b));
        OLC(tn, bn_carp_ntt(&r2, &a, &b));
        OLC(tf, e1 = bn_carp_fft(&r3, &a, &b, 16));
        bn_kopyala(&h, &a); for (size_t i = 0; i < h.n; i++) h.d[i] = 0xffffffff;
        e2 = bn_carp_fft(&r4, &h, &h, 16);
        mpz_t ga, gb, gr; mpz_inits(ga, gb, gr, NULL);
        mpz_import(ga, a.n, -1, 4, 0, 0, a.d); mpz_import(gb, b.n, -1, 4, 0, 0, b.d);
        OLC(tg, mpz_mul(gr, ga, gb));
        bn_yer(&g, 2 * n + 1); size_t k; mpz_export(g.d, &k, -1, 4, 0, 0, gr); g.n = k; bn_duzelt(&g);
        if (tk >= 0) printf("%7zu %9.1f ms", n, tk * 1e3); else printf("%7zu %12s", n, "-");
        printf(" %8.1f ms %9.1f ms   %.1e / %.1e %9.2f ms   %s%s %s\n", tn * 1e3, tf * 1e3, e1, e2, tg * 1e3,
               tk < 0 || !bn_kars(&r1, &g) ? "" : "Karatsuba:YANLIS ", bn_kars(&r2, &g) ? "NTT:YANLIS" : "NTT:dogru", bn_kars(&r3, &g) ? "FFT:YANLIS" : "FFT:dogru");
        bn_sil(&a); bn_sil(&b); bn_sil(&r1); bn_sil(&r2); bn_sil(&r3); bn_sil(&r4); bn_sil(&h); bn_sil(&g);
        mpz_clears(ga, gb, gr, NULL);
    }
    return 0;
}
```

```
$ clang -O2 hiz_fft.c bn_*.o fft.o -I/opt/homebrew/include -L/opt/homebrew/lib -lgmp -o hiz_fft
$ ./hiz_fft
   limb   Karatsuba        NTT   FFT 16 bit  hata(rastgele/hep 1)        GMP   GMP ile karsilastirma
   1024       0.3 ms      0.2 ms       0.3 ms   7.3e-04 / 2.9e-03      0.03 ms   NTT:dogru FFT:dogru
   4096       3.0 ms      0.9 ms       1.1 ms   3.9e-03 / 1.4e-02      0.21 ms   NTT:dogru FFT:dogru
  16384      22.4 ms      3.4 ms       4.2 ms   2.1e-02 / 6.2e-02      0.89 ms   NTT:dogru FFT:dogru
  65536     203.6 ms     15.8 ms      19.0 ms   1.1e-01 / 2.8e-01      4.69 ms   NTT:dogru FFT:dogru
 262144            -     69.7 ms      89.3 ms   5.0e-01 / 5.0e-01     26.39 ms   NTT:dogru FFT:YANLIS
1048576            -    307.5 ms     553.1 ms   5.0e-01 / 5.0e-01    184.91 ms   NTT:dogru FFT:YANLIS
```

- **Karmaşık FFT, 262144 limb'de yanlış sonuç veriyor.** Hata her 4 katta 3–5 kat büyüyor ve 65536'da zaten 0.28. 262144 limb, 524288 parça ve $2^{20}$ noktalık dönüşüm: katsayılar $2^{19} \cdot 2^{32} = 2^{51}$'e kadar çıkıyor, `double`'ın 53 bitinin sınırında. Çare: daha küçük parça (8 bit iki kat uzun dönüşüm demek) ya da FFT'yi bölüp hata analizine göre parça genişliğini seçmek. Percival (2003), güvenli parça genişliği için kanıtlanmış bir sınır veriyor.
- **NTT her boyutta doğru** ve karmaşık FFT'den hızlı: karmaşık çarpma 4 kayan nokta çarpımı ve 2 toplama, bizim `gl_carp` bir 64×64 çarpma ve birkaç tamsayı işlemi.
- **Boyut 4 katına çıktığında süre**: NTT 4.4–4.6 kat ($n \log n$: $4 \cdot \frac{\log 4n}{\log n} \approx 4.5$), Karatsuba 7–9 kat ($4^{1.58} \approx 9$).
- **GMP** 1024 limb'de 7 kat önde, 1 milyon limb'de yalnız **1.7 kat**. GMP de bu boyutta FFT tabanlı (Schönhage–Strassen) çarpmaya geçiyor ve fark algoritmadan değil, uygulama ayrıntısından geliyor.

**Kesişme noktası:**

```c
/* kesisme.c: NTT hangi boyutta Karatsuba'yi geciyor (1000 tekrarin ortalamasi, mikrosaniye) */
#include <stdio.h>
#include "olcum.h"
#include "bn.h"
#include "bn_mod.h"
#include "fft.h"
int main(void) {
    uint64_t s = 4;
    printf("  limb   Karatsuba      NTT\n");
    for (size_t n = 32; n <= 4096; n *= 2) {
        bn a, b, r; bn_baslat(&a); bn_baslat(&b); bn_baslat(&r);
        bn_rastgele(&a, 32 * n, &s); bn_rastgele(&b, 32 * n, &s);
        int T = (int)(200000 / n);
        double t0 = simdi(); for (int i = 0; i < T; i++) bn_carp(&r, &a, &b);
        double t1 = simdi(); for (int i = 0; i < T; i++) bn_carp_ntt(&r, &a, &b);
        double t2 = simdi();
        printf("%6zu %9.1f us %8.1f us\n", n, (t1 - t0) / T * 1e6, (t2 - t1) / T * 1e6);
        bn_sil(&a); bn_sil(&b); bn_sil(&r);
    }
}
```

```
$ clang -O2 kesisme.c bn_*.o fft.o -o kesisme && ./kesisme
  limb   Karatsuba      NTT
    32       0.8 us     12.5 us
    64       2.8 us     18.3 us
   128       9.2 us     29.4 us
   256      28.7 us     51.2 us
   512      88.0 us     97.5 us
  1024     276.6 us    211.7 us
  2048     820.7 us    383.3 us
  4096    2444.9 us    821.9 us
```

NTT, 512 ile 1024 limb arasında (yaklaşık 20000–30000 bit, 6000–10000 ondalık basamak) Karatsuba'yı geçiyor. Küçük boyutta NTT'yi sabit giderleri yeniyor: her çağrıda `malloc` ve kök tabloları, 2'nin kuvvetine yuvarlama (en kötü durumda yarı boş bir dönüşüm), 16 bitlik parça yüzünden iki kat uzun dizi. Gerçek kütüphaneler bu yüzden boyuta göre katman katman algoritma seçiyor: okul → Karatsuba → Toom-3 → Toom-4 → ... → FFT.

Tarih notu: $O(n \log n)$ çarpmanın büyük sayılar için **mümkün** olduğu 2019'a kadar bilinmiyordu. Schönhage–Strassen (1971) $O(n \log n \log \log n)$ veriyordu. Harvey ve van der Hoeven (2019) $O(n \log n)$'yi kanıtladı, ama sabiti o kadar büyük ki pratikte kullanılmıyor. Bizim NTT'miz $n < 2^{31}$ parça için çalışıyor. "Her $n$ için" çalışan bir algoritma, sonsuza uzanan bir asallar zinciri ya da Schönhage–Strassen'in özyinelemeli halkaları gerektiriyor.

---

## Alıştırmalar

**1** – $(1 + 2x + 3x^2)(4 + 5x)$'i elle 4 noktalık DFT ile hesapla: $\omega = -i$, noktalar $1, -i, -1, i$. İki polinomu değerlendir, noktasal çarp, ters DFT uygula. Sonucu doğrudan çarpımla karşılaştır.

**2** – `fft.c`'de iki ileri dönüşüm var. Girdiler gerçel olduğundan ikisi **tek** bir karmaşık FFT ile yapılabilir: $z = x + iy$ dönüştür, $X_k = (Z_k + \overline{Z_{n-k}})/2$, $Y_k = (Z_k - \overline{Z_{n-k}})/(2i)$. Bu formülü kanıtla ve uygula. Kazanç ne?

**3** – Kare alma için ($a = b$) NTT'de kaç dönüşüm gerekir? `bn_carp_ntt`'ye bir `a == b` dalı ekle. Ders 12.4'teki 100000!'i binary splitting ile hesaplayıp (eşit büyüklükteki sayıları çarparak) NTT ile ne kadar hızlandığını ölç.

**4** – $p = 998244353 = 119 \cdot 2^{23} + 1$ yarışma programcılarının sevdiği NTT asalı (üreteci 3). Bu asalla, 32 bitlik aritmetikle hangi parça genişliği ve en fazla kaç parça kullanılabilir? Neden çoğu zaman üç asal ve ÇKT gerekiyor?

**5** – Goldilocks indirgemesinde `if (lo < hh) t -= 0xffffffff;` satırının neden ikinci bir ödünce yol açmadığını göster.

<details>
<summary>Cevaplar</summary>

**1** – $a = (1, 2, 3, 0)$: $a(1) = 6$, $a(-i) = 1 - 2i - 3 = -2 - 2i$, $a(-1) = 2$, $a(i) = -2 + 2i$. $b = (4, 5, 0, 0)$: $9$, $4 - 5i$, $-1$, $4 + 5i$. Çarpımlar: $54$, $(-2 - 2i)(4 - 5i) = -18 + 2i$, $-2$, $-18 - 2i$. Ters DFT ($\omega^{-1} = i$, $1/4$ ile): $c_0 = (54 - 18 + 2i - 2 - 18 - 2i)/4 = 4$, $c_1 = 13$, $c_2 = 22$, $c_3 = 15$. Doğrudan çarpım: $4 + 13x + 22x^2 + 15x^3$. ✓

**2** – DFT doğrusal: $Z = X + iY$. Gerçel bir dizinin DFT'si eşlenik simetrik: $X_{n-k} = \overline{X_k}$. Buradan $\overline{Z_{n-k}} = X_k - iY_k$ ve iki denklemden $X_k$, $Y_k$ çıkıyor. Üç dönüşüm yerine iki (bir ileri, bir ters): yaklaşık yüzde 33 kazanç. Benzer bir hileyle gerçel uzunluk-$n$ FFT, uzunluk-$n/2$ karmaşık FFT'ye indiriliyor.

**3** – İki: bir ileri (iki yerine), bir ters. Yaklaşık yüzde 33 daha hızlı. Binary splitting: $\prod_{i=1}^{n} i = \left(\prod_{i \le n/2}\right) \cdot \left(\prod_{i > n/2}\right)$, özyinelemeli. Üst seviyelerdeki çarpımlar 20000 limb civarında, orada NTT Karatsuba'dan 7 kat hızlı. Ders 12.4'teki 2.78 saniyelik süre, birkaç yüz milisaniyeye inmeli. Ölçüm senin.

**4** – $p < 2^{30}$. Parçalar $b$ bit, $n$ parça için çarpım katsayısı $< n 2^{2b} < p \approx 2^{29.9}$. $b = 8$ ile $n < 2^{13}$; $b = 4$ ile $n < 2^{21}$. İkisi de büyük sayılar için çok küçük ve verimsiz. Üç asalla ($\approx 2^{90}$) ve ÇKT ile $b = 32$ ve milyonlarca parça mümkün. 64 bitlik Goldilocks'un bu kadar kullanışlı olması bundan.

**5** – Ödünç oluştuysa $t = lo - hh + 2^{64}$ ve $hh < 2^{32}$ olduğundan $t > 2^{64} - 2^{32}$. $2^{32} - 1$ çıkarınca $t > 2^{64} - 2^{33} + 1 > 0$: yeni bir ödünç yok. Toplama tarafındaki taşma da benzer: taşma olduysa $r < u \le (2^{32}-1)^2$ ve $r + 2^{32} - 1$ yine 64 bite sığıyor.

</details>

---

## Kaynaklar

- James W. Cooley ve John W. Tukey, "An Algorithm for the Machine Calculation of Complex Fourier Series", *Mathematics of Computation*, 19(90), 1965.
- Arnold Schönhage ve Volker Strassen, "Schnelle Multiplikation großer Zahlen", *Computing*, 7, 1971.
- David Harvey ve Joris van der Hoeven, "Integer Multiplication in Time O(n log n)", *Annals of Mathematics*, 193(2), 2021.
- Colin Percival, "Rapid Multiplication Modulo the Sum and Difference of Highly Composite Numbers", *Mathematics of Computation*, 72(241), 2003 (FFT yuvarlama hatası sınırları).
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra*, Bölüm 8 (FFT, NTT, Schönhage–Strassen).
- Richard Brent ve Paul Zimmermann, *Modern Computer Arithmetic*, §1.3.

**Sıradaki ders:** Sonlu cisim üzerinde polinomlar. GF(p)[x] aritmetiği, indirgenemezlik testi, Faz 5'teki CRC'ye bağlantı.
