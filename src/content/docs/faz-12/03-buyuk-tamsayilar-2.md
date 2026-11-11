---
title: "12.3 Büyük tamsayılar 2: okul çarpması ve Karatsuba"
description: "Büyük tamsayı çarpması: okul yönteminin O(n²) çift döngüsü ve (2^32-1)² + 2(2^32-1)'in 64 bite tam sığması, iç döngünün tek umaddl komutuna derlenip elde zinciri yüzünden çarpım başına 5 çevrim sürmesi; Karatsuba'nın dört yerine üç çarpımı, dengesiz boyutlar ve özyinelemenin bn < 4'te bitmemesi hatası; 20000 vektörde dört eşik değeriyle 0 hata; 2048 limb'te eşik taraması ve 24-32'de en iyi sonuç; büyüklük arttıkça 4 kat boyutta 9.3 kat süreyle n^1.585 doğrusu; GMP ile farkın 3 kattan 42 kata büyümesi ve Toom-Cook ile FFT."
---

Ders 6.13'te Karatsuba çarpmasının bağıntısını $T(n) = 3T(n/2) + O(n)$ olarak yazıp Master teoremiyle $\Theta(n^{\log_2 3})$ bulduk. Bu derste algoritmayı limb'ler üzerinde yazıyor, doğruluğunu sınıyor ve teorideki üssü ölçerek görüyoruz.

Ölçümler macOS'ta, M2 performans çekirdeğinde.

---

## 1. Okul çarpması

İlkokulda öğrendiğimiz alt alta çarpma: $a$'nın her limb'ini $b$'nin bütün limb'leriyle çarpıp kaydırarak topla.

```c
/* bn_carp.c: okul carpmasi ve Karatsuba */
#include <stdlib.h>
#include <string.h>
#include "bn.h"

size_t KARATSUBA_ESIK = 32;

/* r = a * b; r'de an + bn limb yer olmali, onceden sifirlanmis olmasi gerekmez */
void mag_carp_okul(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_) {
    memset(r, 0, (an + bn_) * sizeof(uint32_t));
    for (size_t i = 0; i < an; i++) {
        uint64_t elde = 0, ai = a[i];
        for (size_t j = 0; j < bn_; j++) {
            /* en fazla (2^32-1)^2 + 2 (2^32-1) = 2^64 - 1: tasmaz */
            uint64_t t = ai * b[j] + r[i + j] + elde;
            r[i + j] = (uint32_t)t;
            elde = t >> 32;
        }
        r[i + bn_] = (uint32_t)elde;
    }
}

static size_t uzunluk(const uint32_t *a, size_t n) { while (n && a[n - 1] == 0) n--; return n; }

/* r[0..rn) += x[0..xn); rn >= xn olmali, tasma olmamali */
static void ekle(uint32_t *r, size_t rn, const uint32_t *x, size_t xn) {
    xn = uzunluk(x, xn);
    if (xn) mag_topla(r, r, rn, x, xn);
}

void mag_carp(uint32_t *r, const uint32_t *a, size_t an, const uint32_t *b, size_t bn_) {
    if (an < bn_) { const uint32_t *t = a; a = b; b = t; size_t k = an; an = bn_; bn_ = k; }
    /* bn_ < 4 iken toplamlar kuculmez ve ozyineleme bitmez */
    if (bn_ < KARATSUBA_ESIK || bn_ < 4) { mag_carp_okul(r, a, an, b, bn_); return; }

    if (an >= 2 * bn_) {                       /* dengesiz: a'yi bn_'lik parcalara bol */
        memset(r, 0, (an + bn_) * sizeof(uint32_t));
        uint32_t *t = malloc(2 * bn_ * sizeof(uint32_t));
        for (size_t i = 0; i < an; i += bn_) {
            size_t k = an - i < bn_ ? an - i : bn_;
            mag_carp(t, a + i, k, b, bn_);
            ekle(r + i, an + bn_ - i, t, k + bn_);
        }
        free(t);
        return;
    }

    /* a = a1 B^m + a0,  b = b1 B^m + b0,  bn_ > m */
    size_t m = an / 2;
    const uint32_t *a0 = a, *a1 = a + m, *b0 = b, *b1 = b + m;
    size_t a1n = an - m, b1n = bn_ - m;

    size_t san = a1n + 1, sbn = (b1n > m ? b1n : m) + 1;
    uint32_t *sa = calloc(san, 4), *sb = calloc(sbn, 4);
    sa[a1n] = mag_topla(sa, a1, a1n, a0, m);                       /* a0 + a1 */
    if (b1n >= m) sb[b1n] = mag_topla(sb, b1, b1n, b0, m);         /* b0 + b1 */
    else          sb[m]   = mag_topla(sb, b0, m, b1, b1n);

    uint32_t *z0 = malloc(2 * m * 4), *z2 = malloc((a1n + b1n) * 4), *z1 = malloc((san + sbn) * 4);
    mag_carp(z0, a0, m, b0, m);                                    /* a0 b0 */
    mag_carp(z2, a1, a1n, b1, b1n);                                /* a1 b1 */
    mag_carp(z1, sa, san, sb, sbn);                                /* (a0+a1)(b0+b1) */
    mag_cikar(z1, z1, san + sbn, z0, 2 * m);                       /* - a0 b0 */
    mag_cikar(z1, z1, san + sbn, z2, a1n + b1n);                   /* - a1 b1 = a0 b1 + a1 b0 */

    /* r = z0 + z1 B^m + z2 B^2m */
    memcpy(r, z0, 2 * m * 4);
    memcpy(r + 2 * m, z2, (a1n + b1n) * 4);
    ekle(r + m, an + bn_ - m, z1, san + sbn);
    free(sa); free(sb); free(z0); free(z1); free(z2);
}

void bn_carp(bn *r, const bn *a, const bn *b) {
    if (a->n == 0 || b->n == 0) { bn_sil(r); return; }
    bn t; bn_baslat(&t);
    bn_yer(&t, a->n + b->n);
    mag_carp(t.d, a->d, a->n, b->d, b->n);
    t.n = a->n + b->n; t.isaret = a->isaret ^ b->isaret;
    bn_duzelt(&t);
    bn_sil(r); *r = t;
}
```

`mag_carp_okul`'un iç döngüsü:

```c
uint64_t t = ai * b[j] + r[i + j] + elde;
```

Bu 64 bite sığar mı? En kötü durumda:

$$(2^{32} - 1)^2 + (2^{32} - 1) + (2^{32} - 1) = 2^{64} - 2^{33} + 1 + 2^{33} - 2 = 2^{64} - 1$$

Tam sınırda: bir limb çarpımı ve **iki** 32 bitlik toplama tam olarak 64 bite sığıyor. Bu, 32 bitlik limb seçiminin (Ders 12.2) asıl nedeni.

Derlenmiş hali:

```
$ clang -O2 -S bn_carp.c -o -
LBB0_6:
	ldr	w15, [x13], #4
	ldr	w16, [x12]
	add	x10, x10, x16
	umaddl	x10, w15, w11, x10     ; 32 x 32 + 64 -> 64, tek komut
	str	w10, [x12], #4
	lsr	x10, x10, #32
	subs	x14, x14, #1
	b.ne	LBB0_6
```

`umaddl` çarpmayı ve toplamayı birleştiriyor. Yine de her tur bir öncekinin eldesini bekliyor: `add` → `umaddl` → `lsr` zinciri. Ölçtüğümüz 1024 limb'lik çarpım 1477 µs, yani limb çarpımı başına $1477 \text{ µs} / 1024^2 \approx 1.41$ ns ≈ **5 çevrim**. Bu, zincirin gecikmesi (Ders 11.2'deki tabloya göre `add` 1, `umaddl` 3, `lsr` 1 çevrim). Kapasite değil gecikme sınırlı.

---

## 2. Karatsuba

$a = a_1 B^m + a_0$ ve $b = b_1 B^m + b_0$ olarak ikiye böl:

$$ab = a_1 b_1 B^{2m} + (a_1 b_0 + a_0 b_1) B^m + a_0 b_0$$

Dört çarpım. Karatsuba'nın 1960'taki gözlemi: ortadaki terim, iki çarpımdan **zaten bildiğimiz** sonuçlarla elde edilebilir:

$$a_1 b_0 + a_0 b_1 = (a_0 + a_1)(b_0 + b_1) - a_0 b_0 - a_1 b_1$$

Üç çarpım ve birkaç $O(n)$ toplama-çıkarma. Özyinelemeyle uygulanınca:

$$T(n) = 3\,T(n/2) + O(n) \;\Rightarrow\; T(n) = \Theta(n^{\log_2 3}) = \Theta(n^{1.585})$$

Koddaki üç ayrıntı:

1. **Toplamlar bir limb uzar.** $a_0 + a_1$, $m + 1$ limb olabilir. Bu yüzden `sa`, `sb` bir limb fazla ayrılıyor.
2. **Dengesiz boyutlar.** $a$, $b$'nin iki katından uzunsa ikiye bölmek işe yaramaz ($b_1$ boş olur); $a$'yı $b$ boyunda parçalara bölüp her parçayı ayrı çarpıyoruz.
3. **Eşik.** Küçük sayılarda okul çarpması daha hızlı, çünkü Karatsuba'nın ek toplamaları ve bellek ayırmaları var. Belirli bir boyutun altında okul yöntemine geçiyoruz.

İlk sürümde üçüncü maddede bir hata vardı. Eşiği 2 limb'e indirip test edince program **çöktü** (`SIGSEGV`, yığın taşması). $n = 2$ için $m = 1$; toplamlar $m + 1 = 2$ limb, yani özyinelemeli çarpım yine $2 \times 2$: problem küçülmüyor, özyineleme bitmiyor. $n = 3$ için de aynı. Problem ancak $n \ge 4$ iken küçülüyor: bu yüzden `bn_ < 4` koşulu eşikten bağımsız eklendi.

---

## 3. Sınama

```c
/* sina_carpma.c: Python vektorleri, iki esik degeriyle */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "bn.h"

int main(int argc, char **argv) {
    KARATSUBA_ESIK = argc > 1 ? (size_t)atol(argv[1]) : 32;
    static char sa[20000], sb[20000], sc[40000];
    long satir = 0, hata = 0;
    bn a, b, r; bn_baslat(&a); bn_baslat(&b); bn_baslat(&r);
    while (scanf("%s %s %s", sa, sb, sc) == 3) {
        satir++;
        bn_hexten(&a, sa); bn_hexten(&b, sb);
        bn_carp(&r, &a, &b);
        char *t = bn_hexe(&r); if (strcmp(t, sc)) hata++; free(t);
    }
    printf("esik %zu: %ld satir, %ld hata\n", KARATSUBA_ESIK, satir, hata);
    return 0;
}
```

```
$ python3 uret.py carpma 2 20000 > v_carpma.txt
$ for e in 2 4 8 32; do ./sina_carpma $e < v_carpma.txt; done
esik 2: 20000 satir, 0 hata
esik 4: 20000 satir, 0 hata
esik 8: 20000 satir, 0 hata
esik 32: 20000 satir, 0 hata
```

Aynı vektörleri birkaç eşik değeriyle çalıştırmak önemli: eşik 32 iken test sayılarının çoğu (5000 bitlik sayı 157 limb) Karatsuba'ya ancak bir iki düzey giriyor. Eşik 4'te özyineleme derin ve bütün dallar (dengesiz parçalama, `b1n < m` durumu, toplamın taşması) deneniyor.

---

## 4. Eşiği seçmek

```c
/* esik.c: Karatsuba esigini secmek: 2048 limb carpimi */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"
#include "bn.h"
int main(void) {
    size_t n = 2048;
    uint32_t *a = malloc(n * 4), *b = malloc(n * 4), *r = malloc(2 * n * 4);
    for (size_t i = 0; i < n; i++) { a[i] = (uint32_t)(i * 2654435761u); b[i] = (uint32_t)(i * 40503u + 7); }
    size_t es[] = { 2, 4, 8, 16, 24, 32, 48, 64, 128, 256, 4096 };
    for (int k = 0; k < 11; k++) {
        KARATSUBA_ESIK = es[k];
        double en = 1e9;
        for (int q = 0; q < 5; q++) { double b0 = simdi(); for (int t = 0; t < 20; t++) { mag_carp(r, a, n, b, n); BELLEK(); } double e = (simdi() - b0) / 20; if (e < en) en = e; }
        printf("esik %4zu%s: %7.1f us\n", es[k], es[k] == 4096 ? " (yalniz okul)" : "", en * 1e6);
    }
    return 0;
}
```

```
$ ./esik
esik    2:  7026.6 us
esik    4:  6997.5 us
esik    8:  2151.0 us
esik   16:  1135.5 us
esik   24:   785.9 us
esik   32:   782.7 us
esik   48:   915.3 us
esik   64:   924.3 us
esik  128:  1155.0 us
esik  256:  1714.1 us
esik 4096 (yalniz okul):  6007.0 us
```

(2048 limb × 2048 limb, yani 65 536 bit.) Eşik 2–4'te Karatsuba **okul yönteminden yavaş**: her özyinelemede beş `malloc` var ve küçük çarpımlarda onların maliyeti çarpımın kendisini aşıyor. 24–32 limb (768–1024 bit) en iyi; yalnız okul yöntemine göre 7.7 kat. GMP'nin bu makinedeki eşiği farklı (64 bitlik limb ve assembly yüzünden), ama değer aynı yöntemle, bir tarama ile seçiliyor (GMP'de `tune` programı).

---

## 5. Üssü ölçmek

```c
/* hiz_carpma.c: okul, Karatsuba ve GMP, buyukluge gore */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <gmp.h>
#include "olcum.h"
#include "bn.h"

static double olc_bizim(const uint32_t *a, const uint32_t *b, size_t n, uint32_t *r, int okul) {
    double en = 1e9; long tur = 1;
    for (;;) {
        double b0 = simdi();
        for (long t = 0; t < tur; t++) { if (okul) mag_carp_okul(r, a, n, b, n); else mag_carp(r, a, n, b, n); BELLEK(); }
        double e = simdi() - b0;
        if (e > 0.05) { en = e / tur; break; }
        tur *= 2;
    }
    for (int q = 0; q < 2; q++) {
        double b0 = simdi();
        for (long t = 0; t < tur; t++) { if (okul) mag_carp_okul(r, a, n, b, n); else mag_carp(r, a, n, b, n); BELLEK(); }
        double e = (simdi() - b0) / tur; if (e < en) en = e;
    }
    return en;
}

int main(void) {
    size_t ns[] = { 8, 16, 32, 64, 128, 256, 1024, 4096, 16384, 65536 };
    printf("%8s %8s %12s %12s %12s %8s\n", "limb", "bit", "okul", "karatsuba", "GMP", "oran");
    for (int k = 0; k < 10; k++) {
        size_t n = ns[k];
        uint32_t *a = malloc(n * 4), *b = malloc(n * 4), *r = malloc(2 * n * 4), *r2 = malloc(2 * n * 4);
        unsigned long long s = 88172645463325252ull + n;
        for (size_t i = 0; i < n; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; a[i] = (uint32_t)s; b[i] = (uint32_t)(s >> 32); }
        double to = n <= 16384 ? olc_bizim(a, b, n, r, 1) : 0;
        double tk = olc_bizim(a, b, n, r2, 0);
        if (n <= 16384 && memcmp(r, r2, 2 * n * 4)) printf("FARK n=%zu\n", n);
        mpz_t x, y, z; mpz_init(x); mpz_init(y); mpz_init(z);
        mpz_import(x, n, -1, 4, 0, 0, a); mpz_import(y, n, -1, 4, 0, 0, b);
        long tur = 1; double tg;
        for (;;) { double b0 = simdi(); for (long t = 0; t < tur; t++) mpz_mul(z, x, y); tg = simdi() - b0; if (tg > 0.05) break; tur *= 2; }
        tg /= tur;
        uint32_t *r3 = calloc(2 * n, 4); size_t cnt; mpz_export(r3, &cnt, -1, 4, 0, 0, z);
        if (memcmp(r3, r2, 2 * n * 4)) printf("GMP FARK n=%zu\n", n);
        char okul[32]; if (to > 0) snprintf(okul, 32, "%10.2f us", to * 1e6); else snprintf(okul, 32, "%13s", "-");
        printf("%8zu %8zu %s %9.2f us %9.2f us %7.1fx\n", n, n * 32, okul, tk * 1e6, tg * 1e6, tk / tg);
        free(a); free(b); free(r); free(r2); free(r3); mpz_clear(x); mpz_clear(y); mpz_clear(z);
    }
    return 0;
}
```

```
$ ./hiz_carpma
    limb      bit         okul    karatsuba          GMP     oran
       8      256       0.05 us      0.05 us      0.01 us     3.3x
      16      512       0.17 us      0.17 us      0.03 us     5.9x
      32     1024       0.85 us      0.74 us      0.10 us     7.5x
      64     2048       4.09 us      2.68 us      0.33 us     8.2x
     128     4096      19.96 us      9.43 us      1.09 us     8.7x
     256     8192      94.85 us     29.46 us      3.54 us     8.3x
    1024    32768    1476.66 us    261.32 us     24.68 us    10.6x
    4096   131072   24217.50 us   2433.62 us    198.38 us    12.3x
   16384   524288  386625.00 us  21779.25 us    931.94 us    23.4x
   65536  2097152             - 197904.00 us   4683.06 us    42.3x
```

("oran": bizim Karatsuba / GMP. GMP sütunu isteğe bağlı; GMP kurulu değilse o kısmı silip derleyebilirsin.) Büyüklük 4 kat artınca:

| Geçiş | Okul | Karatsuba | Teori |
| --- | --- | --- | --- |
| 1024 → 4096 | 16.4 kat | 9.3 kat | $4^2 = 16$, $4^{1.585} = 9.0$ |
| 4096 → 16384 | 16.0 kat | 8.9 kat | aynı |
| 16384 → 65536 | — | 9.1 kat | aynı |

Ölçüm teorinin üssünü neredeyse tam veriyor. 16 384 limb'te (yarım milyon bit) Karatsuba okul yönteminden **18 kat** hızlı ve fark büyümeye devam ediyor.

GMP ile oran ise küçük sayılarda 3 kattan büyük sayılarda **42 kata** çıkıyor. İki ayrı neden var:

- **Sabit çarpan** (her boyutta 3–8 kat): 64 bitlik limb'ler (dört kat az limb çarpımı), assembly ve bellek ayırmayan özyineleme.
- **Daha iyi üs** (büyük boyutta artan fark): GMP büyüdükçe daha hızlı algoritmalara geçiyor. Toom-Cook-3, sayıyı üçe bölüp 9 yerine 5 çarpım yapıyor: $O(n^{\log_3 5}) = O(n^{1.465})$. Daha büyük sayılarda Toom-4, 6, 8 ve en sonunda FFT tabanlı Schönhage–Strassen çarpması geliyor: $O(n \log n \log \log n)$. FFT ile çarpmayı Ders 12.9'da yazacağız.

---

## Alıştırmalar

**1** – Karatsuba'yı çıkarma ile yaz: ortadaki terim $(a_1 - a_0)(b_0 - b_1) + a_0 b_0 + a_1 b_1$. Bu yazılışın avantajı ne? Dezavantajı ne? (İpucu: toplamların uzunluğu ve işaret.)

**2** – Karatsuba'nın bir sayıyı **kendisiyle** çarptığı durum (kare alma) için ne sadeleşir? Okul yönteminde kare almanın neden yaklaşık iki kat hızlı yapılabileceğini göster.

**3** – $n = 2^k$ limb için Karatsuba kaç tane tek limb çarpımı yapar (eşik 1 kabul et)? $k = 10$ için okul yöntemiyle karşılaştır.

**4** – `mag_carp`'taki `malloc`'ları kaldırmak için çağırana önceden ayrılmış bir **çalışma alanı** verilebilir. Toplam ne kadar alan gerekir? (İpucu: her düzeyde ne kadar, kaç düzey.)

**5** – Toom-3'ün $O(n^{1.465})$'i neden Karatsuba'dan ancak büyük $n$'de hızlıdır?

<details>
<summary>Cevaplar</summary>

**1** – $a_1 - a_0$ ve $b_0 - b_1$ farkları $m$ limb'e sığar (toplam ise $m+1$ olabilir), bu yüzden özyinelemeli çarpım boyu büyümez ve bu yazılış GMP'nin tercihi. Bedeli, farkların işaretli olması: büyüklükleri çarpıp işaret çarpımına göre sonucu eklemek ya da çıkarmak gerekir.

**2** – Kare alırken üç çarpımın üçü de kare olur: $a_0^2$, $a_1^2$, $(a_0 - a_1)^2$. Okul yönteminde $a_i a_j$ ve $a_j a_i$ aynı: yalnız $i < j$ için çarpıp ikiyle çarpmak ve sonra köşegeni ($a_i^2$) eklemek $n^2$ yerine yaklaşık $n^2/2$ çarpım.

**3** – $3^k$ çarpım: $k = 10$ için $59\,049$; okul yöntemi $4^{10} = 1\,048\,576$. 17.8 kat az; 5. bölümdeki 18 kat ölçümüyle tutarlı (ölçümde eşik 32 ve toplama maliyetleri de var).

**4** – Bir düzeyde $O(n)$ alan (üç ara çarpım ve iki toplam, yaklaşık $4n$ limb); bir alt düzey bunun yarısını kullanıyor. Toplam $4n + 2n + n + \dots \le 8n$ limb: tek bir $8n$ limb'lik tampon yeter. GMP'nin `mpn_mul` iç fonksiyonları bu şekilde bir çalışma alanı alıyor.

**5** – Üs farkı küçük ($1.585 - 1.465 = 0.12$), ama Toom-3'ün sabit çarpanı daha büyük: beş noktada değerlendirme ve **interpolasyon** (bir küçük bölme dahil) gerekiyor. $n^{0.12}$ kazancı ancak $n$ birkaç yüz limb'i geçince sabit maliyeti aşıyor.

</details>

---

## Kaynaklar

- Anatolii Karatsuba ve Yuri Ofman, "Multiplication of Multidigit Numbers on Automata", *Soviet Physics Doklady*, 7, 1963.
- Donald Knuth, *TAOCP*, Cilt 2, §4.3.1 (Algoritma M) ve §4.3.3 (hızlı çarpma).
- Andrei Toom, "The complexity of a scheme of functional elements realizing the multiplication of integers", 1963; Stephen Cook, doktora tezi, Harvard, 1966.
- Richard Brent ve Paul Zimmermann, *Modern Computer Arithmetic*, Bölüm 1.3.
- GMP kılavuzu, "Multiplication Algorithms" (Karatsuba, Toom, FFT eşikleri).

**Sıradaki ders:** Büyük tamsayılar 3. Uzun bölme (Knuth Algoritma D), onluk tabana çevirip yazdırma, 1000! hesaplama.
