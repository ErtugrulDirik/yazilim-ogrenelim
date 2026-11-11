---
title: "12.4 Büyük tamsayılar 3: bölme, onluk taban ve 1000!"
description: "Büyük tamsayı bölmesi: tek limb'e bölmenin 64/32 bitlik adımı; Knuth'un Algoritma D'si, normalleştirme, iki limb'den bölüm tahmini ve en fazla iki düzeltme, nadir geri ekleme adımı; rastgele 20000 bölmede bir kez bile tetiklenmeyip özel olarak seçilmiş 194400 girdinin 5993'ünde tetiklenmesi ve a = 2^96, b = 2^64 + 1 örneği; C kuralıyla işaretli bölüm ve kalan; 10^9'a bölerek onluğa çevirme; 1000!'in 2568 basamağı, 249 sondaki sıfırı ve GMP ile birebir aynı sonuç; dönüşümün O(n²) olması, 100000!'de 3.5 s sürmesi ve Python'un 4300 basamak sınırının bu yüzden var olması."
---

Toplama, çıkarma ve çarpma tamam. Bölme en zor dört işlem: okulda da öyleydi. Her adımda bir sonraki bölüm basamağını **tahmin** ediyor, tahmin fazlaysa düzeltiyorduk. Knuth'un Algoritma D'si bu tahmini, limb'lerle ve kanıtlanmış bir hata sınırıyla yapıyor. Bölme olunca onluk tabana çevirme de gelecek ve böylece 1000!'i yazdırabileceğiz.

---

## 1. Tek limb'e bölme

Bölen tek limb ise okul bölmesi doğrudan çalışıyor: soldan sağa, her adımda önceki kalanı bir limb sola kaydırıp sıradaki limb'i ekle ve böl.

```c
uint64_t t = (r << 32) | a[i];      /* r < b, yani t / b < 2^32 */
q[i] = (uint32_t)(t / b);
r = t % b;
```

$r < b$ olduğundan $t < b \cdot 2^{32}$ ve bölüm bir limb'e sığıyor. Donanım 64/64 bitlik bölmeyi tek komutla yapıyor. Bu fonksiyon onluk dönüşümün de çekirdeği olacak.

---

## 2. Algoritma D

$a$ ($m + n$ limb) bölü $b$ ($n \ge 2$ limb). Okul bölmesinde olduğu gibi bölümü en üst limb'den başlayarak tek tek buluyoruz. Zor kısım her adımın **tahmini**: kalanın ilk iki limb'ini bölenin ilk limb'ine bölmek.

$$\hat q = \left\lfloor \frac{u_{j+n} B + u_{j+n-1}}{v_{n-1}} \right\rfloor$$

Knuth'un teoremi (TAOCP 4.3.1, Teorem B): bölenin en üst limb'i $v_{n-1} \ge B/2$ ise, yani en üst biti 1 ise, tahmin gerçek $q$'dan **en fazla 2 fazla**. Algoritma bu yüzden:

- **D1. Normalleştir.** $a$ ve $b$'yi aynı $s$ bit sola kaydır ki $b$'nin en üst biti 1 olsun. Bölüm değişmez, kalan $2^s$ ile çarpılır (sonda geri kaydırılır).
- **D3. Tahmin et ve inceltilmiş testle düzelt.** $\hat q v_{n-2} > (\hat r B + u_{j+n-2})$ olduğu sürece $\hat q$'yu azalt. Bu üç limb'lik test, iki fazla durumunu neredeyse her zaman yakalıyor.
- **D4. Çarp ve çıkar.** $u_{j..j+n} \mathrel{-}= \hat q \cdot v$.
- **D5–D6. Geri ekle.** Sonuç eksiye düştüyse $\hat q$ hâlâ bir fazlaymış: $v$'yi geri ekle, $\hat q$'yu bir azalt. Knuth bu adımın olasılığını yaklaşık $2/B$ olarak veriyor.
- **D8. Kalanı geri kaydır.**

```c
/* bn_bol.c: tek limb'e bolme, Knuth Algoritma D, onluk taban */
#include <stdlib.h>
#include <string.h>
#include "bn.h"

long GERI_EKLEME = 0;

/* q = a / b, kalan doner; q'da an limb yer olmali (q == a olabilir) */
uint32_t mag_bol_limb(uint32_t *q, const uint32_t *a, size_t an, uint32_t b) {
    uint64_t r = 0;
    for (size_t i = an; i-- > 0;) {
        uint64_t t = (r << 32) | a[i];         /* r < b oldugu icin t / b < 2^32 */
        q[i] = (uint32_t)(t / b);
        r = t % b;
    }
    return (uint32_t)r;
}

/* Knuth, TAOCP Cilt 2, 4.3.1, Algoritma D.
   a: an limb, b: bn_ limb (bn_ >= 2, b[bn_-1] != 0, an >= bn_).
   q: an - bn_ + 1 limb, r: bn_ limb (r NULL olabilir). */
void mag_bol(uint32_t *q, uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_) {
    const uint64_t B = 1ull << 32;
    int s = __builtin_clz(b[bn_ - 1]);         /* D1: normalize et, b'nin en ust biti 1 olsun */
    uint32_t *v = malloc(bn_ * 4), *u = malloc((an + 1) * 4);
    for (size_t i = bn_ - 1; i > 0; i--) v[i] = (b[i] << s) | (s ? (uint32_t)((uint64_t)b[i - 1] >> (32 - s)) : 0);
    v[0] = b[0] << s;
    u[an] = s ? (uint32_t)((uint64_t)a[an - 1] >> (32 - s)) : 0;
    for (size_t i = an - 1; i > 0; i--) u[i] = (a[i] << s) | (s ? (uint32_t)((uint64_t)a[i - 1] >> (32 - s)) : 0);
    u[0] = a[0] << s;

    for (size_t j = an - bn_ + 1; j-- > 0;) {  /* D2-D7: her bolum limb'i */
        /* D3: ust iki limb'den tahmin, en fazla 2 fazla */
        uint64_t ust = ((uint64_t)u[j + bn_] << 32) | u[j + bn_ - 1];
        uint64_t qh = ust / v[bn_ - 1], rh = ust % v[bn_ - 1];
        while (qh >= B || qh * v[bn_ - 2] > ((rh << 32) | u[j + bn_ - 2])) {
            qh--; rh += v[bn_ - 1];
            if (rh >= B) break;
        }
        /* D4: u[j..j+bn_] -= qh * v */
        uint64_t elde = 0; int64_t t = 0;
        for (size_t i = 0; i < bn_; i++) {
            uint64_t p = qh * v[i] + elde;
            elde = p >> 32;
            t = (int64_t)u[i + j] - (int64_t)(uint32_t)p - (t < 0);
            u[i + j] = (uint32_t)t;
        }
        t = (int64_t)u[j + bn_] - (int64_t)elde - (t < 0);
        u[j + bn_] = (uint32_t)t;
        /* D5-D6: eksiye dustuyse qh bir fazlaymis: geri ekle */
        if (t < 0) {
            GERI_EKLEME++;
            qh--;
            uint64_t c = 0;
            for (size_t i = 0; i < bn_; i++) {
                uint64_t z = (uint64_t)u[i + j] + v[i] + c;
                u[i + j] = (uint32_t)z; c = z >> 32;
            }
            u[j + bn_] += (uint32_t)c;
        }
        q[j] = (uint32_t)qh;
    }
    if (r) {                                   /* D8: kalani geri kaydir */
        for (size_t i = 0; i < bn_ - 1; i++) r[i] = (u[i] >> s) | (s ? (uint32_t)((uint64_t)u[i + 1] << (32 - s)) : 0);
        r[bn_ - 1] = u[bn_ - 1] >> s;
    }
    free(u); free(v);
}

/* C kurali: bolum sifira dogru yuvarlanir, kalanin isareti a'nin isareti */
void bn_bol(bn *q, bn *r, const bn *a, const bn *b) {
    bn tq, tr; bn_baslat(&tq); bn_baslat(&tr);
    if (mag_kars(a->d, a->n, b->d, b->n) < 0) {      /* |a| < |b|: q = 0, r = a */
        bn_kopyala(&tr, a);
    } else if (b->n == 1) {
        bn_yer(&tq, a->n); bn_yer(&tr, 1);
        tr.d[0] = mag_bol_limb(tq.d, a->d, a->n, b->d[0]);
        tq.n = a->n; tr.n = 1;
    } else {
        bn_yer(&tq, a->n - b->n + 1); bn_yer(&tr, b->n);
        mag_bol(tq.d, tr.d, a->d, a->n, b->d, b->n);
        tq.n = a->n - b->n + 1; tr.n = b->n;
    }
    tq.isaret = a->isaret ^ b->isaret; tr.isaret = a->isaret;
    bn_duzelt(&tq); bn_duzelt(&tr);
    if (q) { bn_sil(q); *q = tq; } else bn_sil(&tq);
    if (r) { bn_sil(r); *r = tr; } else bn_sil(&tr);
}

/* onluk: 10^9'a tekrar tekrar bol, 9'ar basamak */
char *bn_ondaliga(const bn *x) {
    if (x->n == 0) { char *s = malloc(2); strcpy(s, "0"); return s; }
    size_t n = x->n, parca = 0;
    uint32_t *t = malloc(n * 4), *p = malloc((n * 32 / 29 + 2) * 4);   /* 2^29 < 10^9 */
    memcpy(t, x->d, n * 4);
    while (n) {
        p[parca++] = mag_bol_limb(t, t, n, 1000000000u);
        while (n && t[n - 1] == 0) n--;
    }
    char *s = malloc(parca * 9 + 2), *c = s;
    if (x->isaret) *c++ = '-';
    char tmp[10]; int k = 0;
    for (uint32_t v = p[parca - 1]; v; v /= 10) tmp[k++] = (char)('0' + v % 10);   /* en ust parca: bastaki sifir yok */
    while (k) *c++ = tmp[--k];
    for (size_t i = parca - 1; i-- > 0;) {                                       /* digerleri: tam 9 basamak */
        uint32_t v = p[i];
        for (int j = 8; j >= 0; j--) { c[j] = (char)('0' + v % 10); v /= 10; }
        c += 9;
    }
    *c = 0;
    free(t); free(p);
    return s;
}

/* x = x * m + e (m, e tek limb) */
static void carp_ekle_limb(bn *x, uint32_t m, uint32_t e) {
    bn_yer(x, x->n + 1);
    uint64_t c = e;
    for (size_t i = 0; i < x->n; i++) { uint64_t t = (uint64_t)x->d[i] * m + c; x->d[i] = (uint32_t)t; c = t >> 32; }
    if (c) x->d[x->n++] = (uint32_t)c;
}

int bn_ondaliktan(bn *x, const char *s) {
    int eksi = 0;
    if (*s == '-') { eksi = 1; s++; }
    size_t uz = strlen(s), ilk = uz % 9 ? uz % 9 : 9;
    x->n = 0; x->isaret = 0;
    for (size_t i = 0; i < uz;) {
        size_t k = i == 0 ? ilk : 9;
        uint32_t v = 0, m = 1;
        for (size_t j = 0; j < k; j++, i++) {
            if (s[i] < '0' || s[i] > '9') return -1;
            v = v * 10 + (uint32_t)(s[i] - '0'); m *= 10;
        }
        carp_ekle_limb(x, m, v);
    }
    x->isaret = eksi;
    bn_duzelt(x);
    return 0;
}
```

`bn_bol`, C'nin kuralını izliyor (Ders 2.3'teki `/` ve `%`): bölüm sıfıra doğru yuvarlanıyor, kalanın işareti bölünenin işareti. Python'un `//`'si ise aşağı yuvarlıyor; test vektörleri bu yüzden `uret.py` içinde C kuralıyla hesaplanıyor (`bol_c`).

---

## 3. Sınama ve nadir adım

```c
/* sina_bolme.c: bolum, kalan ve onluk donusum */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bn.h"

int main(void) {
    static char sa[20000], sb[20000], sq[20000], sr[20000], sd[30000];
    long satir = 0, hata = 0;
    bn a, b, q, r, d; bn_baslat(&a); bn_baslat(&b); bn_baslat(&q); bn_baslat(&r); bn_baslat(&d);
    while (scanf("%s %s %s %s %s", sa, sb, sq, sr, sd) == 5) {
        satir++;
        bn_hexten(&a, sa); bn_hexten(&b, sb);
        bn_bol(&q, &r, &a, &b);
        char *t = bn_hexe(&q); if (strcmp(t, sq)) hata++; free(t);
        t = bn_hexe(&r); if (strcmp(t, sr)) hata++; free(t);
        t = bn_ondaliga(&a); if (strcmp(t, sd)) hata++; free(t);
        bn_ondaliktan(&d, sd); if (bn_kars(&d, &a)) hata++;
    }
    printf("%ld satir, %ld hata, geri ekleme %ld kez\n", satir, hata, GERI_EKLEME);
    return 0;
}
```

```
$ python3 uret.py bolme 3 20000 > v_bolme.txt
$ ./sina_bolme < v_bolme.txt
20000 satir, 0 hata, geri ekleme 0 kez
```

Bölüm, kalan, onluğa çevirme ve onluktan geri okuma: dördü de doğru. Ama son sayı kötü haber: **geri ekleme adımı hiç çalışmadı.** $2/B = 2/2^{32} \approx 5 \times 10^{-10}$: rastgele sayılarla bu satıra ulaşmak için milyarlarca bölme gerekir. O satırın hatalı olup olmadığını bu test bize hiç söylemiyor.

Rastgele değil, **uç değerlerden** kurulmuş girdiler deneyelim: her limb $\{0, 1, 2^{31} - 1, 2^{31}, 2^{32} - 2, 2^{32} - 1\}$ değerlerinden biri, 4 limb'lik $a$ ve 3 limb'lik $b$'nin bütün birleşimleri. Doğruluğu Python'a sormadan, tanımla kontrol ediyoruz: $qb + r = a$ ve $0 \le r < b$.

```c
/* geri.c: Algoritma D'nin geri ekleme adimini tetikleyen girdileri ara */
#include <stdio.h>
#include <stdlib.h>
#include "bn.h"

int main(void) {
    const uint32_t deger[] = { 0, 1, 0x7fffffffu, 0x80000000u, 0xfffffffeu, 0xffffffffu };
    long deneme = 0, tutarsiz = 0, bulunan = 0;
    uint32_t a[4], b[3], q[2], r[3], qb[5], k[5];
    int yazdi = 0;
    for (int i0 = 0; i0 < 6; i0++) for (int i1 = 0; i1 < 6; i1++) for (int i2 = 0; i2 < 6; i2++) for (int i3 = 1; i3 < 6; i3++)
    for (int j0 = 0; j0 < 6; j0++) for (int j1 = 0; j1 < 6; j1++) for (int j2 = 1; j2 < 6; j2++) {
        a[0] = deger[i0]; a[1] = deger[i1]; a[2] = deger[i2]; a[3] = deger[i3];
        b[0] = deger[j0]; b[1] = deger[j1]; b[2] = deger[j2];
        if (mag_kars(a, 4, b, 3) < 0) continue;
        long once = GERI_EKLEME;
        mag_bol(q, r, a, 4, b, 3);
        deneme++;
        /* dogrula: q b + r == a ve r < b */
        mag_carp_okul(qb, q, 2, b, 3);
        uint32_t c = mag_topla(k, qb, 5, r, 3);
        if (c || mag_kars(k, 4, a, 4) || k[4] || mag_kars(r, 3, b, 3) >= 0) tutarsiz++;
        if (GERI_EKLEME > once) {
            bulunan++;
            if (!yazdi) {
                yazdi = 1;
                printf("ornek: a = %08x %08x %08x %08x\n       b =          %08x %08x %08x\n       q = %08x %08x, r = %08x %08x %08x\n",
                       a[3], a[2], a[1], a[0], b[2], b[1], b[0], q[1], q[0], r[2], r[1], r[0]);
            }
        }
    }
    printf("%ld bolme, %ld tutarsiz, %ld tanesinde geri ekleme\n", deneme, tutarsiz, bulunan);
    return 0;
}
```

```
$ ./geri
ornek: a = 00000001 00000000 00000000 00000000
       b =          00000001 00000000 00000001
       q = 00000000 ffffffff, r = 00000000 ffffffff 00000001
194400 bolme, 0 tutarsiz, 5993 tanesinde geri ekleme
```

Uç değerlerde geri ekleme yüzde 3 oranında çalışıyor ve sonuçların hepsi tutarlı. İlk örnek: $a = 2^{96}$, $b = 2^{64} + 1$. Python ile:

```
>>> hex(2**96 // (2**64 + 1)), hex(2**96 % (2**64 + 1))
('0xffffffff', '0xffffffff00000001')
```

Ders: **nadir dallar rastgele testle sınanmaz.** Kenar değerlerini sistematik olarak üreten bir test, ya da Hacker's Delight'taki gibi elle seçilmiş örnekler gerekir.

---

## 4. Onluk taban

İkilik limb'lerden onluk basamaklara geçmenin en basit yolu: sayıyı tekrar tekrar 10'a böl, kalanları topla. Her bölme $O(n)$, $O(n)$ basamak için $O(n^2)$. 10 yerine $10^9$'a bölmek (32 bite sığan en büyük 10 kuvveti) her bölmede 9 basamak üretiyor ve 9 kat hızlı. Ters yön, `bn_ondaliktan`, 9'ar basamak okuyup $x \leftarrow x \cdot 10^9 + \text{parça}$ yapıyor.

---

## 5. 1000!

```c
/* fakt.c: 1000! ve 10000!: hesap, onluga cevirme, GMP ile karsilastirma */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gmp.h>
#include "olcum.h"
#include "bn.h"

static void fakt(bn *x, uint32_t n) {
    bn_u64(x, 1);
    for (uint32_t i = 2; i <= n; i++) {          /* x *= i: tek limb'lik carpma */
        uint64_t c = 0;
        for (size_t j = 0; j < x->n; j++) { uint64_t t = (uint64_t)x->d[j] * i + c; x->d[j] = (uint32_t)t; c = t >> 32; }
        if (c) { bn_yer(x, x->n + 1); x->d[x->n++] = (uint32_t)c; }
    }
}

int main(void) {
    uint32_t ns[] = { 1000, 10000, 100000 };
    for (int k = 0; k < 3; k++) {
        uint32_t n = ns[k];
        bn x; bn_baslat(&x);
        double t0 = simdi(); fakt(&x, n); double t1 = simdi();
        char *s = bn_ondaliga(&x); double t2 = simdi();
        mpz_t g; mpz_init(g);
        double g0 = simdi(); mpz_fac_ui(g, n); double g1 = simdi();
        char *gs = mpz_get_str(0, 10, g); double g2 = simdi();
        size_t uz = strlen(s), sifir = 0; long top = 0;
        for (size_t i = uz; i-- > 0 && s[i] == '0';) sifir++;
        for (size_t i = 0; i < uz; i++) top += s[i] - '0';
        printf("%u!: %zu basamak, %zu limb, sondaki sifir %zu, basamak toplami %ld, GMP ile %s\n",
               n, uz, x.n, sifir, top, strcmp(s, gs) ? "FARKLI" : "ayni");
        if (n == 1000) printf("  ilk 40 basamak: %.40s...\n  son 10 sifirsiz: ...%.10s\n", s, s + uz - sifir - 10);
        printf("  bizim: hesap %.2f ms, onluga %.2f ms   GMP: hesap %.2f ms, onluga %.2f ms\n",
               (t1 - t0) * 1e3, (t2 - t1) * 1e3, (g1 - g0) * 1e3, (g2 - g1) * 1e3);
        free(s); free(gs); mpz_clear(g); bn_sil(&x);
    }
    return 0;
}
```

```
$ clang -O2 fakt.c bn_temel.o bn_carp.o bn_bol.o -I/opt/homebrew/include -L/opt/homebrew/lib -lgmp -o fakt
$ ./fakt
1000!: 2568 basamak, 267 limb, sondaki sifir 249, basamak toplami 10539, GMP ile ayni
  ilk 40 basamak: 4023872600770937735437024339230039857193...
  son 10 sifirsiz: ...0027753472
  bizim: hesap 0.41 ms, onluga 0.23 ms   GMP: hesap 0.07 ms, onluga 0.06 ms
10000!: 35660 basamak, 3702 limb, sondaki sifir 2499, basamak toplami 149346, GMP ile ayni
  bizim: hesap 39.68 ms, onluga 29.65 ms   GMP: hesap 0.20 ms, onluga 0.62 ms
100000!: 456574 basamak, 47398 limb, sondaki sifir 24999, basamak toplami 1938780, GMP ile ayni
  bizim: hesap 2778.73 ms, onluga 3495.98 ms   GMP: hesap 4.23 ms, onluga 16.28 ms
```

GMP yalnız karşılaştırma için; olmadan da `mpz_*` satırlarını silip çalıştırabilirsin. Python ile bağımsız kontrol:

```
$ python3 -c "import math; s = str(math.factorial(1000)); print(len(s), sum(map(int, s)), len(s) - len(s.rstrip('0')))"
2568 10539 249
```

- **Sondaki sıfırlar**: $\lfloor 1000/5 \rfloor + \lfloor 1000/25 \rfloor + \lfloor 1000/125 \rfloor + \lfloor 1000/625 \rfloor = 200 + 40 + 8 + 1 = 249$ (Legendre formülü). Her 10 çarpanı bir 2 ve bir 5 ister ve 5'ler daha az.
- **267 limb**: Ders 12.1'in Alıştırma 2'sinde Stirling ile tahmin ettiğimiz sayı.
- **Zaman**: bizim iki işlemimiz de $O(n^2)$. 10 kat büyük faktöriyel yaklaşık 100 kat zaman: hesap 0.41 → 39.7 → 2779 ms. Faktöriyeli bir küçük sayıyla tek tek çarparak kuruyoruz, $n$ adımın her biri $O(\text{boyut})$.

GMP 100000!'i **650 kat** hızlı hesaplıyor ve **215 kat** hızlı yazdırıyor. Nedeni yine algoritma. Faktöriyel için *binary splitting*: çarpımı bir ağaç gibi, eşit büyüklükteki sayıları çarparak kurmak; böylece Karatsuba/Toom/FFT devreye giriyor. Dönüşüm için böl ve yönet: sayıyı $10^{k}$'ya bölüp iki yarıyı ayrı ayrı çevirmek, bölmeyi de hızlı çarpma üzerinden yapmak.

---

## 6. Python'un 4300 basamak sınırı

Ders 12.1'deki ilk denememizde Python şu hatayı vermişti:

```
ValueError: Exceeds the limit (4300 digits) for integer string conversion;
use sys.set_int_max_str_digits() to increase the limit
```

Bu sınır Python 3.11 ile, bir güvenlik açığı (CVE-2020-10735) yüzünden geldi. Onluk dönüşüm bizimki gibi $O(n^2)$ olduğundan, bir web servisine gönderilen 1 MB'lık bir sayı metni sunucuyu saniyelerce meşgul edebiliyordu: bir hizmet engelleme saldırısı. Sınır bunu kesiyor. Bizim 100000! dönüşümümüz 3.5 saniye sürdü: aynı sorun.

(Python 3.14 burada 100000!'i 83 ms'de çevirdi: yeni sürümler bazı durumlarda böl ve yönet dönüşüm kullanıyor. Ama sınır hâlâ varsayılan olarak açık.)

Algoritma karmaşıklığı bir güvenlik özelliği olabilir: dışarıdan gelen veriyle $O(n^2)$ çalışan her kod potansiyel bir saldırı yüzeyi.

---

## Alıştırmalar

**1** – `mag_bol_limb`'de neden `t / b < 2^32` garanti? $r$'nin önceki adımdan $r < b$ olduğunu kullan.

**2** – Normalleştirme olmadan (s = 0) `mag_bol`'u çalıştır. Hangi girdide $\hat q$ gerçek bölümden 2'den fazla büyük çıkabilir? Bir örnek bulmaya çalış.

**3** – $2^{10000}$'in onluk gösteriminin kaç basamak olduğunu hesapla ($\log_{10} 2 \approx 0.30103$). Kütüphanenle doğrula.

**4** – `bn_ondaliga`'yı böl ve yönet ile yaz: $x = h \cdot 10^{9k} + l$ böl, iki yarıyı özyinelemeli çevir. Bizim $O(n^2)$ bölme algoritmamızla ne kazanırsın? Ne zaman gerçekten hızlanır?

**5** – 1000! içinde kaç tane 2 çarpanı var? Sonucun ikilik gösteriminde kaç tane sondaki sıfır olduğunu kütüphaneyle doğrula.

<details>
<summary>Cevaplar</summary>

**1** – $t = r \cdot 2^{32} + a_i \le (b - 1) \cdot 2^{32} + 2^{32} - 1 = b \cdot 2^{32} - 1$, bölü $b$: $< 2^{32}$.

**2** – Normalleştirmesiz $v_{n-1}$ küçük olabilir; örneğin $v_{n-1} = 1$ iken tahmin çok kaba olur ve sınır yalnız $\hat q - q \le 2$ yerine çok daha büyüktür. Bizim `while` döngüsü inceltilmiş testle birkaç kez azaltmayı dener ama `rh >= B` olunca durur ve D4–D6 yalnız bir kez geri ekler: sonuç yanlış olabilir. Normalleştirme bu yüzden doğruluğun **şartı**, bir hız ayarı değil.

**3** – $\lfloor 10000 \times 0.30103 \rfloor + 1 = 3011$ basamak.

**4** – Bir $10^{9k}$ bölmesi yine $O(n^2)$ (bizim Algoritma D'miz), ama iki yarıya bölünen her alt problem dörtte bir maliyetli: toplam $O(n^2)$, sabit çarpan daha kötü. Kazanç ancak bölme alt-ikinci dereceden olduğunda (Newton yöntemiyle bölme, hızlı çarpma üzerine) gelir: $O(M(n) \log n)$.

**5** – Legendre: $\lfloor 1000/2 \rfloor + \lfloor 1000/4 \rfloor + \dots = 500 + 250 + 125 + 62 + 31 + 15 + 7 + 3 + 1 = 994$. İkilik gösterimin en düşük 994 biti sıfır: `d[0]`'dan başlayan 31 tam sıfır limb ve 32. limb'de 2 sıfır bit ($31 \times 32 + 2 = 994$).

</details>

---

## Kaynaklar

- Donald Knuth, *TAOCP*, Cilt 2 (3. baskı), §4.3.1: Algoritma D, Teorem A ve B; Alıştırma 21–22 (geri ekleme olasılığı).
- Henry S. Warren, *Hacker's Delight* (2. baskı), §9.2: `divmnu` ve test örnekleri.
- Per Brinch Hansen, "Multiple-length Division Revisited: A Tour of the Minefield", *Software: Practice and Experience*, 24(6), 1994.
- Richard Brent ve Paul Zimmermann, *Modern Computer Arithmetic*, Bölüm 1.4 (bölme) ve 1.7 (taban dönüşümü).
- Python, CVE-2020-10735 ve `sys.set_int_max_str_digits` belgeleri (docs.python.org/3/library/stdtypes.html#int-max-str-digits).

**Sıradaki ders:** Modüler aritmetik hızlandırma. Montgomery çarpması, Barrett indirgemesi, büyük sayıyla RSA oyuncağı.
