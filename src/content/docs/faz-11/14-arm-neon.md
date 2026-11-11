---
title: "11.14 ARM NEON"
description: "Aynı örneklerin NEON karşılığı ve bu kez gerçek donanımda ölçüm: vaddq_f32 isim şeması, lane, vaddvq ile tek komutta yatay toplam, vbslq ile seçim; vqaddq_u8 ile parlaklıkta 20 kat, vld3q ile RGB'den griye 10 kat; movemask olmayan bir kümede vshrn hilesiyle strlen ve 30862 uç durumda 0 hata, glibc ile eşit hız; vcntq_u8 popcount ve derleyicinin SWAR'ı cnt'ye çevirmesi; FMA birikimci sayısı ve 0.18 çevrim/eleman; vector_size ile taşınabilir kod ve iki mimaride uqadd/paddusb."
---

Ders 11.7–11.13 x86 içindi ve süreleri Rosetta altında ölçmek zorunda kaldık. Bu derste aynı problemleri bu bilgisayarın kendi SIMD kümesi **NEON** ile çözüyoruz. Bu yüzden buradaki bütün süreler gerçek: Apple M2, Docker'daki arm64 Linux, 3.5 GHz kalibrasyonu (Ders 11.1).

---

## 1. İsimler ve tipler

```c
#include <arm_neon.h>
```

Tip adları şeridi söyler: `float32x4_t` (4 × float, 128 bit), `uint8x16_t`, `int16x8_t`; 64 bitlik yarılar `float32x2_t`, `uint8x8_t`. Fonksiyon adı:

```
vaddq_f32
| |  | +-- tip: f32, u8, s16 ...
| |  +---- q: 128 bit (yoksa 64 bit)
| +------- islem
+--------- v: vektor
```

x86'dan farklar: AArch64'te 32 vektör register'ı var (x86-64 SSE/AVX'te 16), şerit sırası `vld1q` ile bellekteki sırayla aynı (`_mm_set_ps` tuzağı yok) ve birçok komut x86'da olmayan biçimler sunuyor.

```c
/* serit.c: NEON tipleri ve isimleri */
#include <stdio.h>
#include <arm_neon.h>

int main(void) {
    float k[4] = { 1, 2, 3, 4 }, l[4] = { 10, 20, 30, 40 }, d[4];
    float32x4_t a = vld1q_f32(k), b = vld1q_f32(l);    /* q: 128 bit */
    vst1q_f32(d, vaddq_f32(a, b));
    printf("vaddq_f32   %g %g %g %g\n", d[0], d[1], d[2], d[3]);
    printf("lane 2      %g\n", vgetq_lane_f32(a, 2));
    printf("vaddvq_f32  %g   (yatay toplam, tek komut)\n", vaddvq_f32(a));
    printf("vmaxvq_f32  %g\n", vmaxvq_f32(b));
    float32x2_t y = vget_low_f32(a);                   /* 64 bit yari */
    printf("vget_low    %g %g\n", vget_lane_f32(y, 0), vget_lane_f32(y, 1));
    /* skaler ile carpma: lane secerek */
    vst1q_f32(d, vmulq_laneq_f32(b, a, 3));
    printf("b * a[3]    %g %g %g %g\n", d[0], d[1], d[2], d[3]);
    /* karsilastirma yine maske */
    uint32x4_t m = vcgtq_f32(a, vdupq_n_f32(2.5f));
    printf("a > 2.5     %08x %08x %08x %08x\n", vgetq_lane_u32(m, 0), vgetq_lane_u32(m, 1), vgetq_lane_u32(m, 2), vgetq_lane_u32(m, 3));
    vst1q_f32(d, vbslq_f32(m, b, a));                  /* bit secimi: blend */
    printf("vbslq       %g %g %g %g\n", d[0], d[1], d[2], d[3]);
    printf("sizeof(float32x4_t)=%zu sizeof(uint8x16_t)=%zu sizeof(float32x4x3_t)=%zu\n",
           sizeof(float32x4_t), sizeof(uint8x16_t), sizeof(float32x4x3_t));
    return 0;
}
```

```
$ clang -O2 serit.c -o s && ./s
vaddq_f32   11 22 33 44
lane 2      3
vaddvq_f32  10   (yatay toplam, tek komut)
vmaxvq_f32  40
vget_low    1 2
b * a[3]    40 80 120 160
a > 2.5     00000000 00000000 ffffffff ffffffff
vbslq       1 2 30 40
sizeof(float32x4_t)=16 sizeof(uint8x16_t)=16 sizeof(float32x4x3_t)=48
```

- `vaddvq_f32` bütün şeritleri **tek komutla** topluyor. Ders 11.11'de x86 için kurduğumuz üç aşamalı karıştırmaya burada gerek yok.
- `vmulq_laneq_f32(b, a, 3)`: bir vektörü diğerinin **bir şeridiyle** çarpıyor. Ders 11.19'daki matris çekirdeğinin temel aleti.
- Karşılaştırma yine maske üretiyor; `vbslq` (*bitwise select*) Ders 11.7'deki `and/andnot/or` üçlüsünün tek komutlu hali.

---

## 2. Görüntü: doyma ve kanal ayırma

```c
/* goruntu.c: parlaklik ve RGB'den gri, NEON ile */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arm_neon.h>
#include "olcum.h"

typedef unsigned char u8;

__attribute__((noinline)) void parlak_c(u8 *d, const u8 *k, long n, int e) {
    for (long i = 0; i < n; i++) { int v = k[i] + e; d[i] = (u8)(v > 255 ? 255 : v); }
}
__attribute__((noinline)) void parlak_neon(u8 *d, const u8 *k, long n, int e) {
    uint8x16_t ve = vdupq_n_u8((u8)e);
    long i = 0;
    for (; i + 16 <= n; i += 16) vst1q_u8(d + i, vqaddq_u8(vld1q_u8(k + i), ve));
    for (; i < n; i++) { int v = k[i] + e; d[i] = (u8)(v > 255 ? 255 : v); }
}

/* gri = (77 R + 150 G + 29 B) >> 8 */
__attribute__((noinline)) void gri_c(u8 *g, const u8 *rgb, long n) {
    for (long i = 0; i < n; i++)
        g[i] = (u8)((77 * rgb[3 * i] + 150 * rgb[3 * i + 1] + 29 * rgb[3 * i + 2]) >> 8);
}
__attribute__((noinline)) void gri_neon(u8 *g, const u8 *rgb, long n) {
    long i = 0;
    for (; i + 16 <= n; i += 16) {
        uint8x16x3_t p = vld3q_u8(rgb + 3 * i);        /* R, G, B ayri register'lara */
        uint16x8_t lo = vmull_u8(vget_low_u8(p.val[0]), vdup_n_u8(77));
        lo = vmlal_u8(lo, vget_low_u8(p.val[1]), vdup_n_u8(150));
        lo = vmlal_u8(lo, vget_low_u8(p.val[2]), vdup_n_u8(29));
        uint16x8_t hi = vmull_high_u8(p.val[0], vdupq_n_u8(77));
        hi = vmlal_high_u8(hi, p.val[1], vdupq_n_u8(150));
        hi = vmlal_high_u8(hi, p.val[2], vdupq_n_u8(29));
        vst1q_u8(g + i, vcombine_u8(vshrn_n_u16(lo, 8), vshrn_n_u16(hi, 8)));
    }
    for (; i < n; i++) g[i] = (u8)((77 * rgb[3 * i] + 150 * rgb[3 * i + 1] + 29 * rgb[3 * i + 2]) >> 8);
}

typedef void pf(u8 *, const u8 *, long, int);
typedef void gf(u8 *, const u8 *, long);

int main(void) {
    long n = 1920 * 1080;
    u8 *k = malloc((size_t)n * 3), *a = malloc((size_t)n), *b = malloc((size_t)n);
    unsigned long long s = 88172645463325252ull;
    for (long i = 0; i < 3 * n; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; k[i] = (u8)s; }
    long hata = 0;
    for (int e = 0; e < 256; e++) { parlak_c(a, k, 1000, e); parlak_neon(b, k, 1000, e); hata += memcmp(a, b, 1000) != 0; }
    gri_c(a, k, n); gri_neon(b, k, n); hata += memcmp(a, b, (size_t)n) != 0;
    printf("farkli sonuc: %ld\n", hata);
    struct { const char *ad; pf *p; gf *g; } t[] = { {"parlaklik C", parlak_c, 0}, {"parlaklik NEON", parlak_neon, 0}, {"gri C", 0, gri_c}, {"gri NEON", 0, gri_neon} };
    for (int q = 0; q < 4; q++) {
        double en = 1e9;
        for (int r = 0; r < 7; r++) {
            double b0 = simdi();
            for (int j = 0; j < 100; j++) { if (t[q].p) t[q].p(a, k, n, 40); else t[q].g(a, k, n); BELLEK(); }
            double e = simdi() - b0; if (e < en) en = e;
        }
        printf("%-15s %.3f ms/kare\n", t[q].ad, en * 1e3 / 100);
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize goruntu.c -o g && ./g
farkli sonuc: 0
parlaklik C     0.908 ms/kare
parlaklik NEON  0.044 ms/kare
gri C           1.206 ms/kare
gri NEON        0.115 ms/kare
```

256 parlaklık değeri için bütün sonuçlar ve bütün kare için gri tonlama C ile bire bir aynı. Parlaklık **20 kat**, gri tonlama **10 kat** hızlandı (1920×1080).

`vld3q_u8`, NEON'un x86'da karşılığı olmayan komutlarından biri: 48 byte'lık `RGBRGB...` verisini okuyup üç register'a **ayırıyor** (`p.val[0]` = 16 R değeri). Ders 11.10'da x86'da bunun için `pshufb` maskeleri kurmuştuk. `vmull_u8` / `vmlal_u8` genişleten çarpma ve çarpma-toplama yapıyor (8 bit × 8 bit → 16 bit); `vshrn_n_u16` kaydırıp daraltıyor. Ders 11.9'daki `unpack + mullo + packus` zinciri burada üç komuta iniyor.

Vektörleştirmeyi açınca ne oluyor?

```
$ clang -O2 goruntu.c -o g2 && ./g2
parlaklik C     0.123 ms/kare
parlaklik NEON  0.045 ms/kare
gri C           0.110 ms/kare
gri NEON        0.116 ms/kare
```

Gri tonlamada derleyici elle yazdığımız kadar iyi: `3 * i` adımlı erişimi tanıyıp kendisi `ld3` üretiyor. Parlaklıkta ise hâlâ 2.7 kat geride. Hangi döngünün nasıl vektörleştiği Ders 11.15'in konusu.

---

## 3. movemask olmadan strlen

Ders 11.12'deki `strlen` `pmovmskb`'ye dayanıyordu: 16 byte'lık maskeyi 16 bitlik sayıya sıkıştırmak. NEON'da bu komut yok. Yaygın çözüm (Danila Kutenin'in Arm için anlattığı yöntem): karşılaştırma maskesini 16 bitlik şeritler olarak görüp **4 bit sağa kaydırarak daraltmak**. Her byte'tan 4 bit kalır, 16 byte 64 bitlik bir sayıya sığar:

```c
static inline uint64_t maske(uint8x16_t eq) {
    uint8x8_t n = vshrn_n_u16(vreinterpretq_u16_u8(eq), 4);
    return vget_lane_u64(vreinterpret_u64_u8(n), 0);
}
```

Bulunan yer `ctz(m) >> 2` (her byte 4 bit). Geri kalan her şey Ders 11.12 ile aynı: aşağı hizala, baştaki byte'ları kaydırıp at.

```c
/* dizgi.h: NEON strlen ve memchr */
#include <stddef.h>
#include <stdint.h>
#include <arm_neon.h>

/* NEON'da movemask yok: her byte'tan 4 bit, 64 bitlik maske */
static inline uint64_t maske(uint8x16_t eq) {
    uint8x8_t n = vshrn_n_u16(vreinterpretq_u16_u8(eq), 4);
    return vget_lane_u64(vreinterpret_u64_u8(n), 0);
}

__attribute__((noinline)) static size_t sl_bayt(const char *s) {
    const char *p = s;
    while (*p) p++;
    return (size_t)(p - s);
}

#define ONES  0x0101010101010101ull
#define HIGHS 0x8080808080808080ull
__attribute__((noinline)) static size_t sl_word(const char *s) {
    const char *p = s;
    while ((uintptr_t)p % 8) { if (!*p) return (size_t)(p - s); p++; }
    for (;;) {
        uint64_t v = *(const uint64_t *)p, z = (v - ONES) & ~v & HIGHS;
        if (z) return (size_t)(p - s) + ((size_t)__builtin_ctzll(z) >> 3);
        p += 8;
    }
}

__attribute__((noinline)) static size_t sl_neon(const char *s) {
    const uint8_t *p = (const uint8_t *)((uintptr_t)s & ~(uintptr_t)15);
    unsigned bas = (unsigned)((uintptr_t)s & 15);
    uint64_t m = maske(vceqzq_u8(vld1q_u8(p))) >> (4 * bas);
    if (m) return (size_t)__builtin_ctzll(m) >> 2;
    for (;;) {
        p += 16;
        m = maske(vceqzq_u8(vld1q_u8(p)));
        if (m) return (size_t)(p - (const uint8_t *)s) + ((size_t)__builtin_ctzll(m) >> 2);
    }
}

/* dort vektor, tek dal: umaxv yerine minv ile "sifir var mi" */
__attribute__((noinline)) static size_t sl_neon4(const char *s) {
    const uint8_t *p = (const uint8_t *)((uintptr_t)s & ~(uintptr_t)15);
    uint64_t m = maske(vceqzq_u8(vld1q_u8(p))) >> (4 * ((uintptr_t)s & 15));
    if (m) return (size_t)__builtin_ctzll(m) >> 2;
    for (p += 16; (uintptr_t)p & 63; p += 16) {
        m = maske(vceqzq_u8(vld1q_u8(p)));
        if (m) return (size_t)(p - (const uint8_t *)s) + ((size_t)__builtin_ctzll(m) >> 2);
    }
    for (;; p += 64) {
        uint8x16x4_t v = vld1q_u8_x4(p);
        uint8x16_t k = vminq_u8(vminq_u8(v.val[0], v.val[1]), vminq_u8(v.val[2], v.val[3]));
        if (vminvq_u8(k) == 0) break;
    }
    for (;; p += 16) {
        m = maske(vceqzq_u8(vld1q_u8(p)));
        if (m) return (size_t)(p - (const uint8_t *)s) + ((size_t)__builtin_ctzll(m) >> 2);
    }
}

__attribute__((noinline)) static const void *mc_neon(const void *v, int c, size_t n) {
    if (n == 0) return 0;
    const uint8_t *s = v, *son = s + n;
    const uint8x16_t ara = vdupq_n_u8((uint8_t)c);
    const uint8_t *p = (const uint8_t *)((uintptr_t)s & ~(uintptr_t)15);
    uint64_t m = maske(vceqq_u8(vld1q_u8(p), ara)) & (~0ull << (4 * ((uintptr_t)s & 15)));
    for (;;) {
        if (m) { const uint8_t *r = p + (__builtin_ctzll(m) >> 2); return r < son ? r : 0; }
        p += 16;
        if (p >= son) return 0;
        m = maske(vceqq_u8(vld1q_u8(p), ara));
    }
}
```

Sayfa sınırı testini aynen tekrarlıyoruz:

```
$ clang -O1 -fno-builtin sina.c -o t && ./t
30862 deneme, 0 hata
$ clang -O2 -fno-vectorize -fno-slp-vectorize hiz.c -o h && ./h
   uzunluk      bayt      word      neon   neon x4      libc   (ns/cagri)
         4       3.2       2.0       0.9       0.9       1.7
        61      19.3       4.3       3.2       2.6       2.6
      1021     303.7      61.8      20.8      11.2      12.0
     65533   18857.5    3557.1    1602.9     597.1     606.7
   1048573  301577.4   56814.1   25613.7   11075.7   11374.9
memchr 64 KB: neon 1219 ns, libc 980 ns
```

Bu kez gerçek donanımda Ders 11.12'nin sonucu doğrulanıyor: tek vektörlü döngü glibc'nin yarı hızında; **dört vektörü tek dalla** tarayan `neon x4` glibc'ye eşit. 1 MB'ta bayt döngüsünden **27 kat** hızlı: 1 MB / 11 µs ≈ 95 GB/s, yani L2'den okuma hızı.

`neon x4` "sıfır var mı" sorusunu `vminvq_u8` ile soruyor: dört vektörün minimumunun **yatay minimumu** sıfırsa bloğun içinde bir sıfır var. Yatay işlemlerin tek komut olması NEON'da bu tür kodları sadeleştiriyor.

---

## 4. popcount: NEON'da komut var

```c
/* pop.c: NEON'un popcount komutu var: cnt */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <arm_neon.h>
#include "olcum.h"

__attribute__((noinline)) uint64_t p_swar(const uint64_t *a, size_t n) {
    uint64_t t = 0;
    for (size_t i = 0; i < n; i++) {
        uint64_t x = a[i];
        x = x - ((x >> 1) & 0x5555555555555555ull);
        x = (x & 0x3333333333333333ull) + ((x >> 2) & 0x3333333333333333ull);
        x = (x + (x >> 4)) & 0x0f0f0f0f0f0f0f0full;
        t += (x * 0x0101010101010101ull) >> 56;
    }
    return t;
}
__attribute__((noinline)) uint64_t p_builtin(const uint64_t *a, size_t n) {
    uint64_t t = 0;
    for (size_t i = 0; i < n; i++) t += (uint64_t)__builtin_popcountll(a[i]);
    return t;
}
__attribute__((noinline)) uint64_t p_neon(const uint64_t *a, size_t n) {
    uint64x2_t top = vdupq_n_u64(0);
    size_t i = 0;
    for (; i + 8 <= n; i += 8) {                     /* 64 byte / tur */
        uint8x16x4_t v = vld1q_u8_x4((const uint8_t *)(a + i));
        uint8x16_t c = vaddq_u8(vaddq_u8(vcntq_u8(v.val[0]), vcntq_u8(v.val[1])),
                                vaddq_u8(vcntq_u8(v.val[2]), vcntq_u8(v.val[3])));   /* <= 32 */
        top = vpadalq_u32(top, vpaddlq_u16(vpaddlq_u8(c)));   /* genislet ve biriktir */
    }
    uint64_t t = vaddvq_u64(top);
    for (; i < n; i++) t += (uint64_t)__builtin_popcountll(a[i]);
    return t;
}
typedef uint64_t pf(const uint64_t *, size_t);
int main(void) {
    uint64_t *a = aligned_alloc(64, 8 * 8192), s = 88172645463325252ull;
    for (int i = 0; i < 8192; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; a[i] = s; }
    long hata = 0;
    for (size_t n = 0; n <= 2000; n++) if (p_neon(a, n) != p_swar(a, n) || p_builtin(a, n) != p_swar(a, n)) hata++;
    printf("0..2000 eleman: %ld hata\n", hata);
    struct { const char *ad; pf *f; } t[] = { {"SWAR", p_swar}, {"builtin", p_builtin}, {"NEON cnt", p_neon} };
    for (int k = 0; k < 3; k++) {
        size_t n = 4096; long tur = 50000; double en = 1e9; uint64_t r = 0;
        for (int q = 0; q < 7; q++) {
            double b0 = simdi();
            for (long j = 0; j < tur; j++) { r += t[k].f(a, n); BELLEK(); }
            double e = simdi() - b0; if (e < en) en = e;
        }
        KORU(r);
        double ns = en * 1e9 / ((double)tur * n);
        printf("%-9s %.3f ns/kelime  %.2f cevrim/kelime\n", t[k].ad, ns, ns * 3.5);
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize pop.c -o p && ./p
0..2000 eleman: 0 hata
SWAR      0.405 ns/kelime  1.42 cevrim/kelime
builtin   0.405 ns/kelime  1.42 cevrim/kelime
NEON cnt  0.112 ns/kelime  0.39 cevrim/kelime
```

`vcntq_u8` her byte'ın popcount'unu veriyor: Ders 11.13'teki `pshufb` tablosuna gerek yok. Toplama için `vpaddlq` (*pairwise add long*: komşuları toplayıp genişlet) ve `vpadalq` (aynısı, birikimciye ekle). 64 byte'ı tek turda işleyen sürüm `__builtin_popcountll`'dan 3.6 kat hızlı.

Asıl ilginç satır SWAR = builtin. Derleyicinin SWAR fonksiyonu için ürettiği koda bakalım:

```
$ clang -O2 -fno-vectorize -S pop.c -o -
p_swar:
	ldr	d0, [x0], #8
	subs	x1, x1, #1
	cnt	v0.8b, v0.8b
	uaddlv	h0, v0.8b
	fmov	w9, s0
	add	x8, x9, x8
	b.ne	.LBB0_1
```

Ders 5.8'in dört adımlık SWAR'ı **tanınıp** `cnt` komutuna çevrilmiş. Clang popcount kalıbını tanıyor; bu yüzden "SWAR mı builtin mi" sorusu bu derleyicide anlamsız. AArch64 skaler register'da `popcount` komutu olmadığı için builtin de vektör register'ına (`d0`) gidip `cnt` kullanıyor.

---

## 5. FMA ve birikimciler

```c
/* nokta.c: dot product, NEON FMA */
#include <stdio.h>
#include <stdlib.h>
#include <arm_neon.h>
#include "olcum.h"
__attribute__((noinline)) float n_c(const float *a, const float *b, long n) {
    float s = 0; for (long i = 0; i < n; i++) s += a[i] * b[i]; return s;
}
__attribute__((noinline)) float n_1(const float *a, const float *b, long n) {
    float32x4_t s = vdupq_n_f32(0);
    for (long i = 0; i + 4 <= n; i += 4) s = vfmaq_f32(s, vld1q_f32(a + i), vld1q_f32(b + i));
    return vaddvq_f32(s);
}
__attribute__((noinline)) float n_k(const float *a, const float *b, long n) {
    float32x4_t s[8];
    for (int k = 0; k < 8; k++) s[k] = vdupq_n_f32(0);
    for (long i = 0; i + 32 <= n; i += 32)
        for (int k = 0; k < 8; k++) s[k] = vfmaq_f32(s[k], vld1q_f32(a + i + 4 * k), vld1q_f32(b + i + 4 * k));
    for (int k = 1; k < 8; k++) s[0] = vaddq_f32(s[0], s[k]);
    return vaddvq_f32(s[0]);
}
typedef float fn(const float *, const float *, long);
int main(void) {
    long n = 4096;
    float *a = aligned_alloc(64, 4 * n), *b = aligned_alloc(64, 4 * n);
    for (long i = 0; i < n; i++) { a[i] = (float)(i % 7) * 0.25f; b[i] = (float)(i % 5) * 0.5f; }
    KORU(a); KORU(b);                     /* diziler kacsin: aksi halde cagri donguden cikar */
    struct { const char *ad; fn *f; } t[] = { {"C", n_c}, {"NEON 1 birikimci", n_1}, {"NEON 8 birikimci", n_k} };
    for (int k = 0; k < 3; k++) {
        double en = 1e9; volatile float r = 0;
        for (int q = 0; q < 7; q++) {
            double b0 = simdi();
            for (int j = 0; j < 50000; j++) { r = t[k].f(a, b, n); BELLEK(); }
            double e = simdi() - b0; if (e < en) en = e;
        }
        double ns = en * 1e9 / (50000.0 * n);
        printf("%-17s sonuc=%.1f  %.3f ns/eleman  %.3f cevrim/eleman\n", t[k].ad, r, ns, ns * 3.5);
    }
    return 0;
}
```

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize nokta.c -o n && ./n
C                 sonuc=3071.2  1.133 ns/eleman  3.966 cevrim/eleman
NEON 1 birikimci  sonuc=3071.2  0.270 ns/eleman  0.944 cevrim/eleman
NEON 8 birikimci  sonuc=3071.2  0.051 ns/eleman  0.178 cevrim/eleman
```

Ders 11.2'nin hesabı gerçek donanımda:

- C: her eleman bir `fmadd` zincirinde, gecikme 4 çevrim → **3.97**.
- 1 birikimci: yine zincir, ama her halkada 4 eleman → $4/4 =$ **0.94**.
- 8 birikimci: zincir kırıldı. Her `fmla` için iki yükleme gerekiyor; M2 çevrimde yaklaşık 3 yükleme yapıyor (Ders 11.2'de ölçtüğümüz `ldr` kapasitesi 2.83). 16 yükleme / 3 ≈ 5.3 çevrim / 32 eleman = 0.167; ölçüm **0.178**. Sınır artık **yüklemeler**.

C sürümüne göre 22 kat. Bu sonucun ilk denemesinde üç satırda da 0.000 ölçmüştüm: diziler hiçbir yere "kaçmadığı" için derleyici çağrının sonucunun her turda aynı olduğunu anlayıp döngünün dışına almıştı. Döngüden önce `KORU(a); KORU(b);` yazmak bunu engelledi (Ders 11.1).

---

## 6. Taşınabilir SIMD

Her mimari için ayrı intrinsic yazmak pahalı. Seçenekler:

| Yol | Nasıl | Bedeli |
| --- | --- | --- |
| Derleyiciye bırak | Ders 11.15 | Vektörleşmeyebilir |
| Vektör uzantısı | `__attribute__((vector_size(16)))` (GCC ve Clang) | Karıştırma ve özel komutlar sınırlı |
| Sarmalayıcı kütüphane | Google Highway, SIMDe, xsimd | Ek bağımlılık |
| Dil desteği | C++26 `std::simd` | C'de yok |

Vektör uzantısıyla:

```c
/* tasinabilir.c: derleyicinin vektor uzantisi, iki mimaride ayni kaynak */
#include <stdint.h>
#include <string.h>
typedef float    f32x4 __attribute__((vector_size(16)));
typedef uint8_t  u8x16 __attribute__((vector_size(16)));

void topla(float *d, const float *a, const float *b, long n) {
    for (long i = 0; i + 4 <= n; i += 4) {
        f32x4 x, y;
        memcpy(&x, a + i, 16); memcpy(&y, b + i, 16);   /* hizasiz yukleme */
        x = x + y;
        memcpy(d + i, &x, 16);
    }
}

u8x16 kirp(u8x16 v, u8x16 e) {
    u8x16 t = v + e;                     /* sarar */
    return t | (u8x16)(t < v);           /* tasma olan seritte maske 0xFF: doymali toplama */
}
```

`t < v` karşılaştırması her şeritte 0 ya da -1 (tüm bitler 1) veriyor, `|` ile taşan şeritler 255 oluyor. İlk denememde `t < v ? 255 : t` yazmıştım: C'de clang vektörler üzerinde `?:` kabul etmiyor (C++'ta ediyor), derleme hatası verdi.

İki mimaride aynı kaynak:

```
$ clang -O2 -S tasinabilir.c -o -        # arm64
kirp:
	uqadd	v0.16b, v0.16b, v1.16b
	ret

$ clang -O2 -S tasinabilir.c -o -        # x86-64
kirp:
	paddusb	%xmm1, %xmm0
	retq
```

Derleyici "topla, taştıysa 255 yap" kalıbını iki mimaride de **tek doymalı toplama komutuna** çeviriyor. 65536 girdi çiftinin hepsinde doğru sonuç veriyor (iki mimaride de denedik). `topla` arm64'te `ldr q / fadd v.4s`, x86'da `movups / addps` oluyor. Hizasız okuma için `memcpy` kullandık: vektör tipine pointer çevirmek hizalama ve aliasing kurallarını (Ders 11.5) çiğner, `memcpy` tek bir yükleme komutuna derlenir.

---

## Alıştırmalar

**1** – `vaddq_f32`, `vadd_f32` ve `vaddvq_f32` arasındaki farkı yaz. Her biri kaç şerit üzerinde çalışır, ne döndürür?

**2** – NEON `maske` hilesinde `vshrn_n_u16(..., 4)` yerine `vshrn_n_u16(..., 8)` kullansaydık ne olurdu?

**3** – `pop.c`'deki `vaddq_u8` toplamında dört `vcntq_u8` sonucu toplanıyor. Bir byte'ta en fazla kaç olur? 8 vektörü toplasaydık taşma olur muydu?

**4** – `nokta.c`'de 12 ve 16 birikimci dene. 8'den iyi olur mu? Sınırın yüklemelerde olduğunu nasıl doğrularsın? (İpucu: bir dizinin yerine sabit bir vektör kullan.)

**5** – `tasinabilir.c`'deki `kirp` işaretli `int8_t` için yazılsaydı (`vector_size(16)` ile `int8_t`) aynı kalıp doymalı toplamayı verir mi? Taşma koşulu nasıl değişir?

<details>
<summary>Cevaplar</summary>

**1** – `vaddq_f32`: 4 şerit, vektör döndürür. `vadd_f32`: 2 şerit (64 bit), vektör döndürür. `vaddvq_f32`: 4 şeridi toplar, tek bir `float` döndürür.

**2** – 16 bitlik her şeridin üst byte'ı kalırdı: her iki byte'tan yalnızca biri (tek indisli olanı) maskeye girerdi. Çift indisli byte'lardaki sıfırlar görünmez olurdu. 4 bit kaydırma, her byte'tan yarım byte alarak ikisini de korur.

**3** – Bir byte'ın popcount'u en fazla 8, dört tanesi 32. Sekiz vektörle 64 olur, bu da 255'ten küçük: taşmaz. 31 vektöre kadar (248) güvenli.

**4** – Yükleme sınırlı olduğu için birikimci eklemek kazandırmaz (beklenen). Doğrulamak için `b` yerine sabit bir vektör kullan: yükleme sayısı yarıya iner. Süre de yaklaşık yarıya inerse sınır yüklemelerdir.

**5** – Hayır. İşaretli taşma koşulu farklıdır: iki pozitifin toplamı negatif ya da iki negatifin toplamı pozitif çıkar. Ayrıca sonuç alt sınırda $-128$'e de kırpılmalıdır. Bunu ifade eden kalıp daha uzun; derleyicinin `sqadd`'e çevirip çevirmediğini assembly'den kontrol etmek gerekir.

</details>

---

## Kaynaklar

- Arm, *Arm Neon Intrinsics Reference* (developer.arm.com/architectures/instruction-sets/intrinsics).
- Arm, *Arm Architecture Reference Manual for A-profile*, SIMD&FP bölümleri: `LD3`, `UQADD`, `CNT`, `SHRN`, `FMLA`.
- Danila Kutenin, "Porting x86 vector bitmask optimizations to Arm NEON", Arm Community blogu, 2022.
- GCC belgeleri, "Using Vector Instructions through Built-in Functions" (`vector_size`).
- Google Highway (github.com/google/highway); SIMDe (github.com/simd-everywhere/simde).

**Sıradaki ders:** Otomatik vektörleştirme. `-O3 -fopt-info-vec`, `-Rpass=loop-vectorize`; vektörleşen ve vektörleşmeyen döngüler ve nedenleri.
