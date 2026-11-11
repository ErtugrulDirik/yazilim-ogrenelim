---
title: "12.2 Büyük tamsayılar 1: temsil, toplama, çıkarma"
description: "Sınırsız büyüklükte tamsayıyı C'de kurmak: 2^32 tabanında uint32_t limb dizisi, işaret ve büyüklük, normal biçim ve -0'ın yasaklanması; elde zincirli toplama ve ödünç zincirli çıkarmanın Ders 0.1'deki bit toplamasının genellemesi olması; işaretli toplamanın büyüklük karşılaştırmasına indirgenmesi; Python'un ürettiği 20000 test vektöründe 0 hata; clang'in elde bayrağını döngü boyunca taşıyamaması, __builtin_addc ile 3 kat ve GMP'nin assembly'si ile 6 kat hızlı toplama."
---

Ders 0.1'de iki ikilik sayıyı bit bit topladık ve elde, sağdan sola bir bitten ötekine geçti. Donanım bunu 64 bitte bir komutla yapıyor. Daha büyük sayılar için aynı işlemi **yazılımda**, 64 bitten daha büyük "basamaklarla" yapacağız.

Bu dersin kütüphanesi Faz 12 boyunca büyüyecek: bugün temsil, toplama, çıkarma; Ders 12.3'te çarpma, Ders 12.4'te bölme ve onluk taban.

---

## 1. Temsil

Bir sayıyı $B = 2^{32}$ tabanında yazalım:

$$x = \pm \sum_{i=0}^{n-1} d_i B^i, \qquad 0 \le d_i < B$$

Her $d_i$ bir **limb** (GMP'nin terimi: "kol", basamağın büyük hali). Kararlar:

- **Taban $2^{32}$**: iki limb'in çarpımı ($< 2^{64}$) `uint64_t`'ye sığıyor, böylece Ders 12.3'teki çarpma taşınabilir C ile yazılabiliyor. $2^{64}$ taban daha hızlı olur ama çarpım için `__int128` ya da derleyiciye özgü bir yol gerekir (GMP öyle yapıyor).
- **Küçük-sonlu sıra** (Ders 3.9): `d[0]` en düşük anlamlı. Toplama ve çarpma sağdan sola ilerlediği için dizinin başından başlıyor.
- **İşaret ve büyüklük** (Ders 3.3): ikiler tümleyeni değil. Büyük sayıda ikiler tümleyeni sonsuz sayıda 1 bit demek; işaretin ayrı tutulması çarpma ve bölmeyi çok sadeleştiriyor.
- **Normal biçim**: en üstteki limb sıfır olamaz, sıfır `n = 0` ile gösterilir ve `-0` yoktur. Böylece her sayının **tek** bir gösterimi var ve karşılaştırma önce uzunluğa bakabilir.

```c
/* bn.h: buyuk tamsayi. Deger = (-1)^isaret * sum d[i] * 2^(32 i) */
#ifndef BN_H
#define BN_H
#include <stdint.h>
#include <stddef.h>

typedef struct {
    uint32_t *d;     /* limb'ler, en dusuk anlamli once (little-endian) */
    size_t n;        /* kullanilan limb sayisi; d[n-1] != 0, sifir icin n = 0 */
    size_t kap;      /* ayrilmis limb sayisi */
    int isaret;      /* 0: pozitif ya da sifir, 1: negatif */
} bn;

/* buyukluk (mag) duzeyi: isaretsiz limb dizileri */
uint32_t mag_topla(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_);
uint32_t mag_cikar(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_);
int      mag_kars(const uint32_t *a, size_t an, const uint32_t *b, size_t bn_);
void     mag_carp_okul(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_);
void     mag_carp(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_);
uint32_t mag_bol_limb(uint32_t *q, const uint32_t *a, size_t an, uint32_t b);
void     mag_bol(uint32_t *q, uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_);

/* bn duzeyi */
void bn_baslat(bn *x);
void bn_sil(bn *x);
void bn_u64(bn *x, uint64_t v);
void bn_kopyala(bn *r, const bn *a);
int  bn_kars(const bn *a, const bn *b);
void bn_topla(bn *r, const bn *a, const bn *b);
void bn_cikar(bn *r, const bn *a, const bn *b);
void bn_carp(bn *r, const bn *a, const bn *b);
void bn_bol(bn *q, bn *r, const bn *a, const bn *b);   /* C gibi: bolum sifira dogru */
int  bn_hexten(bn *x, const char *s);
char *bn_hexe(const bn *x);                            /* free ile birak */
int  bn_ondaliktan(bn *x, const char *s);
char *bn_ondaliga(const bn *x);

/* ic yardimcilar */
void bn_yer(bn *x, size_t n);
void bn_duzelt(bn *x);
extern size_t KARATSUBA_ESIK;
extern long   GERI_EKLEME;      /* Algoritma D'nin nadir adimi kac kez calisti */
#endif
```

İki katman var: `mag_*` fonksiyonları **büyüklüklerle** (işaretsiz limb dizileri) çalışıyor ve bellek ayırmıyor; `bn_*` fonksiyonları işareti, belleği ve normal biçimi yönetiyor. GMP'de bu iki katmanın karşılığı `mpn_*` ve `mpz_*`.

---

## 2. Toplama ve çıkarma

```c
/* bn_temel.c: temsil, toplama, cikarma, karsilastirma, hex */
#include <stdlib.h>
#include <string.h>
#include "bn.h"

void bn_baslat(bn *x) { x->d = 0; x->n = x->kap = 0; x->isaret = 0; }
void bn_sil(bn *x) { free(x->d); bn_baslat(x); }

void bn_yer(bn *x, size_t n) {                 /* en az n limb'lik yer */
    if (n <= x->kap) return;
    size_t k = x->kap ? x->kap : 4;
    while (k < n) k *= 2;
    x->d = realloc(x->d, k * sizeof(uint32_t));
    x->kap = k;
}

void bn_duzelt(bn *x) {                        /* bastaki sifir limb'leri at */
    while (x->n > 0 && x->d[x->n - 1] == 0) x->n--;
    if (x->n == 0) x->isaret = 0;              /* -0 yok */
}

void bn_u64(bn *x, uint64_t v) {
    bn_yer(x, 2);
    x->d[0] = (uint32_t)v; x->d[1] = (uint32_t)(v >> 32);
    x->n = 2; x->isaret = 0;
    bn_duzelt(x);
}

void bn_kopyala(bn *r, const bn *a) {
    if (r == a) return;
    bn_yer(r, a->n);
    if (a->n) memcpy(r->d, a->d, a->n * sizeof(uint32_t));
    r->n = a->n; r->isaret = a->isaret;
}

/* r = a + b, an >= bn_; r'de an limb yer olmali; elde doner */
uint32_t mag_topla(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_) {
    uint64_t elde = 0;
    size_t i = 0;
    for (; i < bn_; i++) {
        uint64_t t = (uint64_t)a[i] + b[i] + elde;
        r[i] = (uint32_t)t;
        elde = t >> 32;
    }
    for (; i < an; i++) {
        uint64_t t = (uint64_t)a[i] + elde;
        r[i] = (uint32_t)t;
        elde = t >> 32;
    }
    return (uint32_t)elde;
}

/* r = a - b, a >= b ve an >= bn_; odunc doner (dogru kullanimda 0) */
uint32_t mag_cikar(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_) {
    uint32_t odunc = 0;
    size_t i = 0;
    for (; i < bn_; i++) {
        uint64_t t = (uint64_t)a[i] - b[i] - odunc;
        r[i] = (uint32_t)t;
        odunc = (uint32_t)(t >> 63);           /* eksiye dustuyse en ust bit 1 */
    }
    for (; i < an; i++) {
        uint64_t t = (uint64_t)a[i] - odunc;
        r[i] = (uint32_t)t;
        odunc = (uint32_t)(t >> 63);
    }
    return odunc;
}

int mag_kars(const uint32_t *a, size_t an, const uint32_t *b, size_t bn_) {
    if (an != bn_) return an < bn_ ? -1 : 1;
    for (size_t i = an; i-- > 0;)
        if (a[i] != b[i]) return a[i] < b[i] ? -1 : 1;
    return 0;
}

int bn_kars(const bn *a, const bn *b) {
    if (a->isaret != b->isaret) return a->isaret ? -1 : 1;
    int k = mag_kars(a->d, a->n, b->d, b->n);
    return a->isaret ? -k : k;
}

/* isaretli toplama: buyuklukleri topla ya da buyukten kucugu cikar */
static void topla_isaretli(bn *r, const bn *a, const bn *b, int b_isaret) {
    bn t; bn_baslat(&t);
    if (a->isaret == b_isaret) {
        const bn *x = a->n >= b->n ? a : b, *y = a->n >= b->n ? b : a;
        bn_yer(&t, x->n + 1);
        t.d[x->n] = mag_topla(t.d, x->d, x->n, y->d, y->n);
        t.n = x->n + 1; t.isaret = a->isaret;
    } else {
        int k = mag_kars(a->d, a->n, b->d, b->n);
        if (k == 0) { bn_sil(r); return; }
        const bn *x = k > 0 ? a : b, *y = k > 0 ? b : a;
        bn_yer(&t, x->n);
        mag_cikar(t.d, x->d, x->n, y->d, y->n);
        t.n = x->n; t.isaret = k > 0 ? a->isaret : b_isaret;
    }
    bn_duzelt(&t);
    bn_sil(r); *r = t;                         /* r, a ya da b olabilir */
}

void bn_topla(bn *r, const bn *a, const bn *b) { topla_isaretli(r, a, b, b->isaret); }
void bn_cikar(bn *r, const bn *a, const bn *b) { topla_isaretli(r, a, b, b->n ? !b->isaret : 0); }

/* "-1f" gibi: istege bagli eksi, sonra 16'lik basamaklar */
int bn_hexten(bn *x, const char *s) {
    int eksi = 0;
    if (*s == '-') { eksi = 1; s++; }
    size_t uz = strlen(s);
    if (uz == 0) return -1;
    bn_yer(x, uz / 8 + 1);
    memset(x->d, 0, (uz / 8 + 1) * sizeof(uint32_t));
    for (size_t i = 0; i < uz; i++) {          /* sagdan i. basamak */
        char c = s[uz - 1 - i];
        int v = c >= '0' && c <= '9' ? c - '0' : c >= 'a' && c <= 'f' ? c - 'a' + 10 : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1;
        if (v < 0) return -1;
        x->d[i / 8] |= (uint32_t)v << (4 * (i % 8));
    }
    x->n = uz / 8 + 1; x->isaret = eksi;
    bn_duzelt(x);
    return 0;
}

char *bn_hexe(const bn *x) {
    char *s = malloc(x->n * 8 + 3), *p = s;
    if (x->n == 0) { strcpy(s, "0"); return s; }
    if (x->isaret) *p++ = '-';
    static const char h[] = "0123456789abcdef";
    int bas = 1;
    for (size_t i = x->n; i-- > 0;)
        for (int k = 7; k >= 0; k--) {
            int v = (x->d[i] >> (4 * k)) & 15;
            if (bas && v == 0) continue;       /* bastaki sifirlari yazma */
            bas = 0; *p++ = h[v];
        }
    *p = 0;
    return s;
}
```

**Toplama.** Okul toplamasının aynısı, basamak 10 yerine $2^{32}$:

```
t     = a[i] + b[i] + elde     (64 bit; en fazla 2^33 - 1)
r[i]  = t'nin alt 32 biti
elde  = t'nin ust 32 biti      (0 ya da 1)
```

**Çıkarma.** Aynı şey, ödünçle. $a[i] - b[i] - \text{odunc}$ 64 bitte hesaplanınca, sonuç eksiyse işaretsiz aritmetikte $2^{64}$ civarına sarar ve en üst biti 1 olur: `t >> 63` ödünç. `mag_cikar` $a \ge b$ şartıyla çağrılıyor, bu yüzden en sonda ödünç kalmıyor.

**İşaretli toplama.** $a + b$'nin dört durumu, büyüklükler üzerinden iki duruma iniyor:

| İşaretler | İşlem |
| --- | --- |
| Aynı | $\lvert a \rvert + \lvert b \rvert$, işaret ortak |
| Farklı | Büyük büyüklükten küçüğü çıkar, işaret büyüğün |

Çıkarma, $b$'nin işaretini çevirip toplamak. Sonucu önce geçici bir değişkene yazıp en sonda `r`'ye koyuyoruz: böylece `bn_topla(&a, &a, &b)` gibi **takma ad** çağrıları doğru çalışıyor.

`bn_hexten` ve `bn_hexe` 16'lık tabanda okuyup yazıyor: her limb tam 8 onaltılık basamak, dönüşüm yalnız kaydırma. Onluk taban bölme gerektiriyor ve Ders 12.4'e kaldı.

---

## 3. Sınama: Python'la karşılaştırma

Büyük tamsayı kodunun hataları neredeyse her zaman **kenarlarda**: elde zincirinin bütün sayı boyunca ilerlemesi, eşit büyüklükler, sıfır, farklı uzunluklar. Elle test yazmak yerine, kesin olduğunu bildiğimiz bir uygulamayla, Python'un `int`'iyle binlerce rastgele örnek üretiyoruz:

```python
# uret.py: rastgele test vektorleri, Python'un buyuk tamsayilari ile
import random, sys
random.seed(int(sys.argv[2]) if len(sys.argv) > 2 else 1)
ne = sys.argv[1]
def h(x): return ('-' if x < 0 else '') + format(abs(x), 'x')
def sayi():
    t = random.random()
    bit = random.choice([0, 1, 31, 32, 33, 63, 64, 65, 100, 500, 2000, 5000])
    if t < 0.15: v = (1 << bit) - 1                       # hep 1: elde zinciri
    elif t < 0.25: v = 1 << bit                           # tek 1 bit: odunc zinciri
    else: v = random.getrandbits(bit) if bit else 0
    return -v if random.random() < 0.4 else v
def bol_c(a, b):                                          # C gibi: sifira dogru
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0): q = -q
    return q, a - q * b
for _ in range(int(sys.argv[3]) if len(sys.argv) > 3 else 20000):
    a, b = sayi(), sayi()
    if random.random() < 0.1: b = a                       # esitlik ve a - a
    if random.random() < 0.05: b = -a
    if ne == 'toplama':
        print(h(a), h(b), h(a + b), h(a - b), (a > b) - (a < b))
    elif ne == 'carpma':
        print(h(a), h(b), h(a * b))
    elif ne == 'bolme':
        if b == 0: b = 1
        q, r = bol_c(a, b)
        print(h(a), h(b), h(q), h(r), str(a))
```

Örneklerin yüzde 15'i "hepsi 1" ($2^k - 1$, eklenince elde baştan sona taşınıyor), yüzde 10'u "tek bit" ($2^k$, çıkarınca ödünç baştan sona gidiyor), bit sayıları limb sınırlarında (31, 32, 33, 63, 64, 65) yoğun, yüzde 10'unda $a = b$ ve yüzde 5'inde $a = -b$.

```c
/* sina_toplama.c: Python'un urettigi vektorlerle toplama, cikarma, karsilastirma */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bn.h"

int main(void) {
    static char sa[20000], sb[20000], st[20000], sf[20000];
    int k; long satir = 0, hata = 0;
    bn a, b, r; bn_baslat(&a); bn_baslat(&b); bn_baslat(&r);
    while (scanf("%s %s %s %s %d", sa, sb, st, sf, &k) == 5) {
        satir++;
        bn_hexten(&a, sa); bn_hexten(&b, sb);
        bn_topla(&r, &a, &b);
        char *t = bn_hexe(&r); if (strcmp(t, st)) hata++; free(t);
        bn_cikar(&r, &a, &b);
        t = bn_hexe(&r); if (strcmp(t, sf)) hata++; free(t);
        if (bn_kars(&a, &b) != k) hata++;
        bn_topla(&a, &a, &b);                  /* takma ad: r == a */
        t = bn_hexe(&a); if (strcmp(t, st)) hata++; free(t);
    }
    printf("%ld satir, %ld hata\n", satir, hata);
    return 0;
}
```

```
$ clang -O2 -c bn_temel.c && clang -O2 sina_toplama.c bn_temel.o -o sina_toplama
$ python3 uret.py toplama 1 20000 > v_toplama.txt
$ ./sina_toplama < v_toplama.txt
20000 satir, 0 hata
```

Her satırda dört kontrol: toplam, fark, karşılaştırma ve takma adlı toplama. 80 000 kontrolün hepsi doğru.

---

## 4. Elde bayrağı

İşlemcinin toplama komutu eldeyi zaten bir **bayrakta** üretiyor ve "elde ile topla" komutu var: x86'da `adc`, AArch64'te `adcs`. 64 bitlik limb'lerle bir toplama, limb başına tek komut olabilir. Bizim C kodumuz ne oluyor?

```
$ clang -O2 -S bn_temel.c -o -          # arm64, ilk dongu
LBB6_2:
	ldr	w12, [x9], #4
	ldr	w13, [x3], #4
	add	x12, x0, x12
	add	x12, x12, x13
	str	w12, [x10], #4
	lsr	x0, x12, #32           ; elde: ust 32 bit
	subs	x11, x11, #1
	b.ne	LBB6_2
```

Beklenen kod: 64 bitte topla, üst yarıyı elde olarak al. Elde bayrağı yok. Clang'in `__builtin_addcll`'ı ile 64 bitlik limb'ler:

```c
/* adc.c: derleyiciye "elde ile topla" komutunu soyletmek */
#include <stdint.h>
#include <stddef.h>
uint64_t topla64(uint64_t *r, const uint64_t *a, const uint64_t *b, size_t n) {
    unsigned long long elde = 0;
    for (size_t i = 0; i < n; i++) r[i] = __builtin_addcll(a[i], b[i], elde, &elde);
    return elde;
}
```

```
$ clang -O2 -S adc.c -o -               # arm64
LBB0_1:
	ldr	x9, [x1], #8
	ldr	x10, [x2], #8
	adds	x9, x9, x10
	cset	w10, hs                ; elde -> register
	adds	x9, x9, x8
	csinc	w8, w10, wzr, lo       ; iki eldeyi birlestir
	str	x9, [x0], #8
	subs	x3, x3, #1             ; dongu sayaci bayraklari ezer
	b.ne	LBB0_1
```

Derleyici yine `adcs` zinciri kurmuyor: döngü sayacının `subs`'u bayrakları eziyor, bu yüzden elde her turda bir register'a alınıp geri konuyor. x86-64 çıktısında aynı tablo: bir `adcq` var, ama yanında `setb`, `addb $-1` ile eldeyi bayrağa geri yükleme.

Hız (macOS, M2 performans çekirdeği, 1024 × 64 bit = 64 Kbit; çevrim Ders 11.1'deki 3.5 GHz kalibrasyonuyla):

```c
/* hiz_toplama.c: 64 bitlik kelime basina toplama suresi */
#include <stdio.h>
#include <stdlib.h>
#include <gmp.h>
#include "olcum.h"
#include "bn.h"
uint64_t topla64(uint64_t *r, const uint64_t *a, const uint64_t *b, size_t n);
int main(void) {
    size_t n = 1024;                                 /* 64 bitlik kelime: 64 Kbit */
    uint64_t *a = malloc(8 * n), *b = malloc(8 * n), *r = malloc(8 * n);
    for (size_t i = 0; i < n; i++) { a[i] = i * 0x9e3779b97f4a7c15ull; b[i] = ~a[i] + (i & 1); }
    double e1 = 1e9, e2 = 1e9, e3 = 1e9;
    for (int q = 0; q < 7; q++) {
        double t = simdi(); for (int k = 0; k < 100000; k++) { mag_topla((uint32_t *)r, (uint32_t *)a, 2 * n, (uint32_t *)b, 2 * n); BELLEK(); } double e = simdi() - t; if (e < e1) e1 = e;
        t = simdi(); for (int k = 0; k < 100000; k++) { topla64(r, a, b, n); BELLEK(); } e = simdi() - t; if (e < e2) e2 = e;
        t = simdi(); for (int k = 0; k < 100000; k++) { mpn_add_n((mp_limb_t *)r, (mp_limb_t *)a, (mp_limb_t *)b, (mp_size_t)n); BELLEK(); } e = simdi() - t; if (e < e3) e3 = e;
    }
    double c = 1e9 / (100000.0 * n);
    printf("32 bit limb, C        : %.3f ns / 64 bit  (%.2f cevrim)\n", e1 * c, e1 * c * 3.5);
    printf("64 bit, __builtin_addc: %.3f ns / 64 bit  (%.2f cevrim)\n", e2 * c, e2 * c * 3.5);
    printf("GMP mpn_add_n         : %.3f ns / 64 bit  (%.2f cevrim)\n", e3 * c, e3 * c * 3.5);
    return 0;
}
```

```
$ clang -O2 hiz_toplama.c adc.c bn_temel.o -I/opt/homebrew/include -L/opt/homebrew/lib -lgmp -o hiz_toplama
$ ./hiz_toplama
32 bit limb, C        : 1.716 ns / 64 bit  (6.01 cevrim)
64 bit, __builtin_addc: 0.594 ns / 64 bit  (2.08 cevrim)
GMP mpn_add_n         : 0.292 ns / 64 bit  (1.02 cevrim)
```

- Taşınabilir C sürümümüz 64 bit başına 6 çevrim (32 bitlik limb başına 3: `add`, `add`, `lsr` bağımlılık zinciri, Ders 11.2).
- 64 bitlik limb ve builtin: 3 kat hızlı.
- GMP'nin elle yazılmış assembly'si: **çevrimde bir limb**, bizim C kodumuzdan 6 kat hızlı. GMP'nin `mpn/arm64/` dizinindeki çekirdekler döngüyü açıp sayaç komutlarını elde zincirini bozmayacak yerlere koyuyor; ayrıntısını kaynağından okuyabilirsin.

Büyük tamsayı kütüphaneleri bu yüzden en iç döngüleri hâlâ assembly ile yazar: C'nin bayraklara erişimi yok. GMP kurulu değilse (`brew install gmp`, `apt install libgmp-dev`) bu karşılaştırmayı atlayabilirsin; dersin geri kalanı GMP gerektirmiyor.

Bu fazda okunabilirliği tercih edip 32 bitlik limb ve düz C ile devam ediyoruz.

---

## Alıştırmalar

**1** – `mag_topla`'da `t` en fazla kaçtır? Bu değer neden 33 bite sığar?

**2** – İkiler tümleyeni gösterimiyle büyük tamsayı tutsaydık $-1$ nasıl görünürdü? Hangi işlemler kolaylaşır, hangileri zorlaşır?

**3** – `bn_duzelt`'i çağırmayı unutursak hangi fonksiyon yanlış sonuç verir? Bir örnek kur.

**4** – `bn_kars` yazılırken önce limb sayısına bakmak neden doğru? Normal biçim olmasaydı ne olurdu?

**5** – `uret.py`'den "hepsi 1" örneklerini çıkar ve `mag_topla`'nın ikinci döngüsünü (yalnız `a`'nın kalan limb'leri) bilerek boz (örneğin eldeyi eklemeyi unut). Rastgele sayılarla hata kaç satırda yakalanıyor?

<details>
<summary>Cevaplar</summary>

**1** – $(2^{32} - 1) + (2^{32} - 1) + 1 = 2^{33} - 1$: 33 bit. Elde bu yüzden her zaman 0 ya da 1.

**2** – $-1$ sonsuz sayıda 1 bit; pratikte "en üst limb'in ötesi hep işaret biti" kuralıyla `0xffffffff` tek limb. Toplama ve çıkarma işaret düşünmeden aynı döngü olur (işlemcideki gibi), bit işlemleri (`&`, `|`, `~`) doğal. Çarpma, bölme ve karşılaştırma ise işaret durumlarını ele almak zorunda kalır; GMP işaret-büyüklüğü bu yüzden seçiyor (bit işlemlerinde ikiler tümleyenini taklit ediyor).

**3** – `bn_kars` ve `bn_hexe`. Örnek: $x - x$ sonucu `n = 1, d[0] = 0` bırakırsa `bn_kars(r, 0)` limb sayılarına bakıp "büyük" der; ayrıca `-0` ile `0` farklı karşılaştırılır.

**4** – Normal biçimde daha çok limb'li sayı daha büyüktür (en üst limb sıfır değil). Normal biçim olmasaydı, baştaki sıfırları atlayarak gerçek uzunlukları bulmak gerekirdi.

**5** – Kendi deneyin. Beklenti: rastgele sayılarda kısa sayının bittiği noktada elde 1 olma olasılığı yarı yarıya, ama hata yalnız eldenin **kalan** limb'lere de taşınması gereken (`0xffffffff`'lerle devam eden) durumda görünür. Bu yüzden "hepsi 1" örnekleri olmadan hata nadiren yakalanır: test vektörlerinin kenarları kasıtlı olarak zorlaması bu yüzden.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 2 (3. baskı), §4.3.1: klasik algoritmalar (Algoritma A ve S).
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra*, Bölüm 2.
- GMP kılavuzu, "Low-level Functions" (`mpn_add_n`) ve "Integer Internals" (gmplib.org/manual).
- Richard Brent ve Paul Zimmermann, *Modern Computer Arithmetic*, Cambridge, 2010, Bölüm 1.1–1.2.

**Sıradaki ders:** Büyük tamsayılar 2. Okul çarpması, Karatsuba çarpması ve karmaşıklık analizi.
