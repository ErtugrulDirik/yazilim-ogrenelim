---
title: "11.20 Faz projesi: görüntü filtresi ve hızlı string fonksiyonları"
description: "Faz 11'in araçlarıyla iki proje: 4K gri görüntüde 3x3 Gauss bulanıklaştırmayı naif 16.5 ms'den ayrılabilir filtre, NEON, tek geçişli halka tampon ve dört çekirdekle 0.35 ms'e, 47 kata indirmek ve her adımda bit bit doğrulamak; dört çekirdekte bellek tavanına (48 GB/s) çarpılması ve sekiz çekirdeğin bir şey katmaması; iki mimari için tek arayüzlü hizli_strlen ve hizli_memchr, 110184 sayfa sınırı denemesinde 0 hata, glibc ile eşit strlen ve yüzde 24 geride memchr; ölçümleri çubuk grafik olarak yazan küçük bir araç."
---

Faz 11'de bir döngüyü ölçmeyi (11.1), donanımın sınırlarını (11.2–11.5), SIMD'i (11.6–11.15), veri düzenini ve önbelleği (11.16–11.17), tavanı tahmin etmeyi (11.18) gördük. Bu projede hepsini iki gerçek işte kullanıyoruz ve her adımı **ölçüp**, her adımın sonucunu ilk, en basit sürümle **bit bit karşılaştırıyoruz**.

Ortam: M2, arm64 Linux (Docker), clang 18. x86 sürümü aynı kaynaktan Rosetta altında yalnız doğruluk için sınandı.

---

## 1. Ölçüm grafiği

Her adımın sonucunu yatay çubuk olarak yazan küçük bir yardımcı:

```c
/* grafik.h: olcumleri yatay cubuk grafik olarak yaz */
#include <stdio.h>
static void grafik(const char *baslik, const char **ad, const double *deger, int n, const char *birim) {
    double en = 0;
    for (int i = 0; i < n; i++) if (deger[i] > en) en = deger[i];
    printf("%s\n", baslik);
    for (int i = 0; i < n; i++) {
        int uz = (int)(50.0 * deger[i] / en + 0.5);
        printf("  %-20s |", ad[i]);
        for (int k = 0; k < uz; k++) putchar('#');
        printf(" %.3f %s (%.1fx)\n", deger[i], birim, deger[0] / deger[i]);
    }
}
```

Çubuklar en yavaş sürüme göre ölçekleniyor, parantez içindeki sayı ilk sürüme göre hızlanma.

---

## 2. Görüntü filtresi: 3×3 Gauss

Çekirdek:

$$\frac{1}{16}\begin{pmatrix} 1 & 2 & 1 \\ 2 & 4 & 2 \\ 1 & 2 & 1 \end{pmatrix} = \frac{1}{16}\begin{pmatrix} 1 \\ 2 \\ 1 \end{pmatrix}\begin{pmatrix} 1 & 2 & 1 \end{pmatrix}$$

Matris bir **dışsal çarpım** olduğu için filtre **ayrılabilir**: önce her satıra yatay $[1\ 2\ 1]$, sonra sonuca dikey $[1\ 2\ 1]$. 9 çarpma yerine 6 işlem; üstelik tamsayıda tam aynı sonuç (yuvarlama sonda bir kez: $(s + 8) \gg 4$). Kenarlarda piksel tekrarlanıyor.

```c
/* bulanik.h: 3x3 Gauss bulaniklastirma, [1 2 1; 2 4 2; 1 2 1] / 16, kenarlar tekrarlanir */
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <pthread.h>
#include <arm_neon.h>
typedef uint8_t u8;

static inline int kis(int v, int ust) { return v < 0 ? 0 : v > ust ? ust : v; }

/* 1. dogrudan tanim: 9 komsu, her pikselde kenar kontrolu */
static void b_naif(u8 *d, const u8 *k, int w, int h) {
    static const int c[3][3] = { {1, 2, 1}, {2, 4, 2}, {1, 2, 1} };
    for (int y = 0; y < h; y++)
        for (int x = 0; x < w; x++) {
            int s = 0;
            for (int dy = -1; dy <= 1; dy++)
                for (int dx = -1; dx <= 1; dx++)
                    s += c[dy + 1][dx + 1] * k[kis(y + dy, h - 1) * w + kis(x + dx, w - 1)];
            d[y * w + x] = (u8)((s + 8) >> 4);
        }
}

/* 2. ayrilabilir: once yatay [1 2 1], sonra dikey [1 2 1]; ara sonuc uint16 */
static void yatay_c(uint16_t *t, const u8 *s, int w) {
    t[0] = (uint16_t)(3 * s[0] + s[1]);
    for (int x = 1; x < w - 1; x++) t[x] = (uint16_t)(s[x - 1] + 2 * s[x] + s[x + 1]);
    t[w - 1] = (uint16_t)(s[w - 2] + 3 * s[w - 1]);
}
static void dikey_c(u8 *d, const uint16_t *a, const uint16_t *b, const uint16_t *c, int w) {
    for (int x = 0; x < w; x++) d[x] = (u8)((a[x] + 2 * b[x] + c[x] + 8) >> 4);
}
static void b_ayrik(u8 *d, const u8 *k, int w, int h) {
    uint16_t *t = malloc(sizeof(uint16_t) * (size_t)w * h);
    for (int y = 0; y < h; y++) yatay_c(t + (size_t)y * w, k + (size_t)y * w, w);
    for (int y = 0; y < h; y++)
        dikey_c(d + (size_t)y * w, t + (size_t)kis(y - 1, h - 1) * w, t + (size_t)y * w, t + (size_t)kis(y + 1, h - 1) * w, w);
    free(t);
}

/* 3. NEON: 16 piksel birden; komsular vextq ile */
static void yatay_neon(uint16_t *t, const u8 *s, int w) {
    int x = 1;
    t[0] = (uint16_t)(3 * s[0] + s[1]);
    for (; x + 16 <= w - 1; x += 16) {
        uint8x16_t sol = vld1q_u8(s + x - 1), orta = vld1q_u8(s + x), sag = vld1q_u8(s + x + 1);
        uint16x8_t lo = vaddl_u8(vget_low_u8(sol), vget_low_u8(sag));
        uint16x8_t hi = vaddl_high_u8(sol, sag);
        lo = vmlal_u8(lo, vget_low_u8(orta), vdup_n_u8(2));
        hi = vmlal_high_u8(hi, orta, vdupq_n_u8(2));
        vst1q_u16(t + x, lo); vst1q_u16(t + x + 8, hi);
    }
    for (; x < w - 1; x++) t[x] = (uint16_t)(s[x - 1] + 2 * s[x] + s[x + 1]);
    t[w - 1] = (uint16_t)(s[w - 2] + 3 * s[w - 1]);
}
static void dikey_neon(u8 *d, const uint16_t *a, const uint16_t *b, const uint16_t *c, int w) {
    int x = 0;
    for (; x + 16 <= w; x += 16) {
        uint16x8_t l = vaddq_u16(vaddq_u16(vld1q_u16(a + x), vld1q_u16(c + x)), vshlq_n_u16(vld1q_u16(b + x), 1));
        uint16x8_t r = vaddq_u16(vaddq_u16(vld1q_u16(a + x + 8), vld1q_u16(c + x + 8)), vshlq_n_u16(vld1q_u16(b + x + 8), 1));
        vst1q_u8(d + x, vcombine_u8(vrshrn_n_u16(l, 4), vrshrn_n_u16(r, 4)));   /* (v + 8) >> 4 */
    }
    for (; x < w; x++) d[x] = (u8)((a[x] + 2 * b[x] + c[x] + 8) >> 4);
}
static void b_neon(u8 *d, const u8 *k, int w, int h) {
    uint16_t *t = malloc(sizeof(uint16_t) * (size_t)w * h);
    for (int y = 0; y < h; y++) yatay_neon(t + (size_t)y * w, k + (size_t)y * w, w);
    for (int y = 0; y < h; y++)
        dikey_neon(d + (size_t)y * w, t + (size_t)kis(y - 1, h - 1) * w, t + (size_t)y * w, t + (size_t)kis(y + 1, h - 1) * w, w);
    free(t);
}

/* 4. tek gecis: yalnizca 3 satirlik halka tampon, ara goruntu onbellekte kalir */
static void b_halka_aralik(u8 *d, const u8 *k, int w, int h, int y0, int y1, uint16_t *hal) {
    uint16_t *r[3] = { hal, hal + w, hal + 2 * w };
    yatay_neon(r[0], k + (size_t)kis(y0 - 1, h - 1) * w, w);
    yatay_neon(r[1], k + (size_t)y0 * w, w);
    for (int y = y0; y < y1; y++) {
        yatay_neon(r[2], k + (size_t)kis(y + 1, h - 1) * w, w);
        dikey_neon(d + (size_t)y * w, r[0], r[1], r[2], w);
        uint16_t *t = r[0]; r[0] = r[1]; r[1] = r[2]; r[2] = t;
    }
}
static void b_halka(u8 *d, const u8 *k, int w, int h) {
    uint16_t *hal = malloc(sizeof(uint16_t) * 3 * (size_t)w);
    b_halka_aralik(d, k, w, h, 0, h, hal);
    free(hal);
}

/* 5. is parcaciklari: her biri bir satir bandi */
typedef struct { u8 *d; const u8 *k; int w, h, y0, y1; } Bant;
static void *bant_calis(void *v) {
    Bant *b = v;
    uint16_t *hal = malloc(sizeof(uint16_t) * 3 * (size_t)b->w);
    b_halka_aralik(b->d, b->k, b->w, b->h, b->y0, b->y1, hal);
    free(hal);
    return 0;
}
static int BANT = 4;
static void b_paralel(u8 *d, const u8 *k, int w, int h) {
    pthread_t th[16]; Bant b[16];
    for (int t = 0; t < BANT; t++) {
        b[t] = (Bant){ d, k, w, h, h * t / BANT, h * (t + 1) / BANT };
        pthread_create(&th[t], 0, bant_calis, &b[t]);
    }
    for (int t = 0; t < BANT; t++) pthread_join(th[t], 0);
}
```

Adımlar:

1. **Naif**: tanımın doğrudan yazılışı; her pikselde 9 komşu ve kenar kontrolü.
2. **Ayrılabilir**: iki geçiş, `uint16_t` ara görüntü. Yatay toplam en fazla $4 \times 255 = 1020$, dikey en fazla $4 \times 1020 = 4080$: 16 bite sığıyor (Ders 11.9'daki taşma analizi). Derleyici iki iç döngüyü de vektörleştiriyor (`-Rpass`: genişlik 16).
3. **NEON**: komşular üç kaydırılmış yükleme, `vaddl_u8` / `vmlal_u8` ile genişleten toplama; `vrshrn_n_u16(v, 4)` tek komutta $(v + 8) \gg 4$ ve daraltma.
4. **Tek geçiş**: ara görüntü 16.6 MB, iki geçiş arasında önbellekten düşüyor. Dikey geçiş için yalnız **üç satır** gerekiyor; üç satırlık bir halka tamponda (3 × 7.5 KB, L1'de) yatay sonucu üretip hemen dikeyi uyguluyoruz. Ara görüntü belleğe hiç gitmiyor.
5. **Çok çekirdek**: satır bantları; her bant kendi halka tamponuyla, sınır satırlarını kaynaktan okuyarak bağımsız.

Doğrulama: her sürüm naif sürümle 3840×2160'ta ve 1–100 piksellik garip boyutlarda (1×1 hariç) karşılaştırılıyor.

```
$ clang -O2 -pthread filtre.c -o f && ./f
kucuk boyutlar: 0 farkli
3840x2160, butun adimlar naif surumle bit bit ayni
Gauss 3x3 bulaniklastirma (ms/kare, kisa cubuk iyi)
  1 naif               |################################################## 16.543 ms (1.0x)
  2 ayrilabilir        |#### 1.433 ms (11.5x)
  3 NEON               |### 1.043 ms (15.9x)
  4 tek gecis          |## 0.806 ms (20.5x)
  5 4 cekirdek         |# 0.348 ms (47.5x)
  6 8 cekirdek         |# 0.366 ms (45.2x)
```

Okuma:

- **Algoritma ilk sırada** (11.5 kat). Ayrılabilirlik iş miktarını azalttı, kenar kontrolünü iç döngüden çıkardı ve döngüleri vektörleşebilir yaptı. Elle yazılmış SIMD'den önce **matematiğe** bak.
- **Elle NEON** derleyicinin vektörleştirmesinden 1.4 kat iyi: `vrshrn` ve genişleten çarpma-toplama gibi komutları derleyici her zaman seçemiyor (Ders 11.15).
- **Tek geçiş** 1.3 kat: ara görüntünün bellek trafiği (16.6 MB yazma + okuma) gitti.
- **4 çekirdek** 2.3 kat, **8 çekirdek** daha kötü. Roofline sorusu (Ders 11.18): her kare 8.3 MB okuma + 8.3 MB yazma, 0.348 ms'de: $16.6 / 0.348 \approx 48$ GB/s. Bu makinenin bellek tavanı. Filtre artık **bellek sınırlı**; çekirdek eklemek bir şey kazandırmıyor.

Bu noktadan daha hızlı olmanın tek yolu daha az byte taşımak: örneğin bulanıklaştırmayı bir sonraki işlemle (kenar bulma, ölçekleme) **birleştirip** görüntüyü bir kez okumak.

---

## 3. Hızlı strlen ve memchr

Ders 4.13'te byte byte yazdık, 5.10'da word word, 11.12'de SSE2, 11.14'te NEON ile. Şimdi bunları tek bir başlıkta, iki mimarili bir kütüphane olarak topluyoruz: derleme hedefine göre NEON, SSE2 ya da standart kütüphane.

```c
/* hizli.h: strlen ve memchr, iki mimari, tek arayuz */
#include <stddef.h>
#include <stdint.h>

#if defined(__aarch64__)
#include <arm_neon.h>
static inline uint64_t h_maske(uint8x16_t eq) {           /* Ders 11.14 */
    return vget_lane_u64(vreinterpret_u64_u8(vshrn_n_u16(vreinterpretq_u16_u8(eq), 4)), 0);
}
static inline size_t hizli_strlen(const char *s) {
    const uint8_t *p = (const uint8_t *)((uintptr_t)s & ~(uintptr_t)15);
    uint64_t m = h_maske(vceqzq_u8(vld1q_u8(p))) >> (4 * ((uintptr_t)s & 15));
    if (m) return (size_t)__builtin_ctzll(m) >> 2;
    for (p += 16; (uintptr_t)p & 63; p += 16)
        if ((m = h_maske(vceqzq_u8(vld1q_u8(p))))) return (size_t)(p - (const uint8_t *)s) + ((size_t)__builtin_ctzll(m) >> 2);
    for (;; p += 64) {                                        /* 64 byte, tek dal */
        uint8x16x4_t v = vld1q_u8_x4(p);
        if (vminvq_u8(vminq_u8(vminq_u8(v.val[0], v.val[1]), vminq_u8(v.val[2], v.val[3]))) == 0) break;
    }
    for (;; p += 16)
        if ((m = h_maske(vceqzq_u8(vld1q_u8(p))))) return (size_t)(p - (const uint8_t *)s) + ((size_t)__builtin_ctzll(m) >> 2);
}
static inline const void *hizli_memchr(const void *v, int c, size_t n) {
    if (n == 0) return 0;
    const uint8_t *s = v, *son = s + n;
    const uint8x16_t ara = vdupq_n_u8((uint8_t)c);
    const uint8_t *p = (const uint8_t *)((uintptr_t)s & ~(uintptr_t)15);
    uint64_t m = h_maske(vceqq_u8(vld1q_u8(p), ara)) & (~0ull << (4 * ((uintptr_t)s & 15)));
    for (;;) {
        if (m) { const uint8_t *r = p + (__builtin_ctzll(m) >> 2); return r < son ? r : 0; }
        p += 16;
        if (p >= son) return 0;
        if (((uintptr_t)p & 63) == 0 && son - p >= 64) {          /* 64 byte, tek dal: maksimum eslesme */
            uint8x16x4_t q = vld1q_u8_x4(p);
            uint8x16_t e = vorrq_u8(vorrq_u8(vceqq_u8(q.val[0], ara), vceqq_u8(q.val[1], ara)),
                                    vorrq_u8(vceqq_u8(q.val[2], ara), vceqq_u8(q.val[3], ara)));
            if (vmaxvq_u8(e) == 0) { p += 48; m = 0; continue; }
        }
        m = h_maske(vceqq_u8(vld1q_u8(p), ara));
    }
}
#elif defined(__x86_64__)
#include <immintrin.h>
static inline size_t hizli_strlen(const char *s) {                /* Ders 11.12, SSE2 */
    const char *p = (const char *)((uintptr_t)s & ~(uintptr_t)15);
    const __m128i z = _mm_setzero_si128();
    unsigned m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), z)) >> ((uintptr_t)s & 15);
    if (m) return (size_t)__builtin_ctz(m);
    for (;;) {
        p += 16;
        if ((m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), z)))) return (size_t)(p - s) + (size_t)__builtin_ctz(m);
    }
}
static inline const void *hizli_memchr(const void *v, int c, size_t n) {
    if (n == 0) return 0;
    const unsigned char *s = v, *son = s + n;
    const __m128i ara = _mm_set1_epi8((char)c);
    const unsigned char *p = (const unsigned char *)((uintptr_t)s & ~(uintptr_t)15);
    unsigned m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), ara)) & (0xFFFFu << ((uintptr_t)s & 15));
    for (;;) {
        if (m) { const unsigned char *r = p + __builtin_ctz(m); return r < son ? r : 0; }
        p += 16;
        if (p >= son) return 0;
        m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), ara));
    }
}
#else
#include <string.h>
static inline size_t hizli_strlen(const char *s) { return strlen(s); }
static inline const void *hizli_memchr(const void *v, int c, size_t n) { return memchr(v, c, n); }
#endif
```

`hizli_memchr`'a NEON'da dört vektörlü bir yol ekledik: 64 byte'ın dört eşleşme maskesini `vorrq` ile birleştirip `vmaxvq_u8` ile "hiç eşleşme var mı" diye soruyoruz (Ders 11.12, Alıştırma 5).

Sınama, Ders 11.12'deki gibi iki yanı korumalı sayfalarla, daha geniş: 600'e kadar uzunluk, 64 başlangıç hizası, `memchr` için `n`'in hemen ötesinde eşleşme ve sayfanın ortası/sonu.

```
$ clang -O2 -fno-builtin-strlen -fno-builtin-memchr dizgi.c -o d && ./d       # arm64
aarch64 NEON: 110184 deneme, 0 hata
strlen, 1 MB (mikrosaniye, kisa cubuk iyi)
  bayt (Ders 4.13)     |################################################## 304.332 us (1.0x)
  word (Ders 5.10)     |######### 56.941 us (5.3x)
  hizli_strlen         |## 11.154 us (27.3x)
  glibc strlen         |## 11.161 us (27.3x)
memchr, 1 MB, bulunamayan byte (mikrosaniye)
  bayt                 |################################################## 393.662 us (1.0x)
  hizli_memchr         |## 18.829 us (20.9x)
  glibc memchr         |## 15.239 us (25.8x)

$ ./d | head -1                                                              # x86-64, Rosetta
x86-64 SSE2: 110184 deneme, 0 hata
```

`hizli_strlen` glibc ile **eşit**. `hizli_memchr` yüzde 24 geride: döngümüz her 16 byte'ta bir hizalama ve kalan uzunluk kontrolü yapıyor, glibc'ninki 64 byte'lık döngüye bir kez girip orada kalıyor. Alıştırma 3 bunu düzeltmek.

:::caution[Projede de ölü kod]
İlk ölçümde `glibc memchr` satırı **0.000 µs** gösterdi. Fonksiyonu saran `mc_libc`, derleyicinin gözünde yan etkisiz ve sonucu yalnız döngüden sonra kullanılıyor; çağrılar silinmişti (assembly'de `bl memchr` yoktu). Her turda `KORU(r0)` eklemek düzeltti. Faz 11 boyunca bu tuzağa altı kez düştük: ölçüm sonucu fazla iyiyse önce bundan şüphelen.
:::

---

## 4. Değerlendirme

| Proje | Başlangıç | Son | Sınır |
| --- | --- | --- | --- |
| Gauss 3×3, 4K | 16.5 ms | 0.35 ms (47×) | Bellek bant genişliği |
| `strlen`, 1 MB | 304 µs | 11 µs (27×) | L2 okuma hızı, glibc'ye eşit |
| `memchr`, 1 MB | 394 µs | 19 µs (21×) | glibc'den yüzde 24 yavaş |

Faz boyunca tekrar eden dersler:

1. **Önce ölç, sonra doğrula, sonra yine ölç.** Her optimizasyon bir hata kaynağı; bit bit karşılaştırma ucuz.
2. **Algoritma > bellek düzeni > SIMD > iş parçacığı.** Kazançlar bu sırayla büyük.
3. **Tavanı bil.** Roofline bellek sınırına geldiğini söylüyorsa çekirdek eklemek boşa.
4. **Derleyiciye bak.** Bazen elle yazdığından iyi (gri tonlama, popcount), bazen 8 kat kötü (koşullu atama).
5. **Kenarlar.** Kalan elemanlar, sayfa sınırları, 2'nin kuvveti boyutlar: hataların ve yavaşlıkların çoğu orada.

---

## Alıştırmalar

**1** – Filtreyi 5×5 Gauss'a ($[1\ 4\ 6\ 4\ 1]$) genişlet. Ara değer 16 bite sığar mı? NEON sürümünde komşuları nasıl yüklersin?

**2** – Bulanıklaştırma ve ardından bir eşikleme (`v > 128 ? 255 : 0`) yapan iki geçişi tek geçişe birleştir. Bellek sınırlı olduğu için ne kadar kazanç beklersin? Ölç.

**3** – `hizli_memchr`'ı glibc'ye yaklaştır: başta 64'e hizalanana kadar 16'lık adımlar, sonra kontrolsüz 64 byte'lık döngü, en sonda kalan parçalar. Sayfa sınırı testini yeniden çalıştır.

**4** – `hizli.h`'e AVX2 dalı ekle (Ders 11.12'deki `sl_avx2x4`) ve çalışma zamanında `__builtin_cpu_supports("avx2")` ile seç. Neden `#if defined(__AVX2__)` yeterli değil?

**5** – `b_paralel`'de bantları performans çekirdekleri için büyük, verimlilik çekirdekleri için küçük yapmak 8 iş parçacığını işe yarar hale getirir mi? (İpucu: Ders 11.18'deki sınır.)

<details>
<summary>Cevaplar</summary>

**1** – Yatay ağırlık toplamı 16: $16 \times 255 = 4080$; dikey: $16 \times 4080 = 65280 < 65536$, `uint16_t`'ye **tam sığıyor** (işaretsiz). İşaretli 16 bit kullanılırsa taşar. Yuvarlama: $(s + 128) \gg 8$, `vrshrn_n_u16(v, 8)`. Komşular: `s + x - 2 ... s + x + 2` beş yükleme (ya da `vextq_u8` ile ikisinden türetme).

**2** – Eşiklemeyi `dikey_neon`'un sonuna ekleyip (`vcgtq_u8` + doğrudan maskeyi yazmak) ikinci geçişi kaldırırsın. Ayrı geçişlerde ikinci geçiş 8.3 MB okuyup 8.3 MB yazıyor; birleşik hali bunu sıfırlar. Bellek sınırlı olduğu için toplam süre yaklaşık yarıya iner (16.6 + 16.6 MB yerine 16.6 MB). Ölçmedim.

**3** – Kendi çözümün; sınama programı (`dizgi.c`) değişmeden kullanılabilir. Dikkat: 64 byte'lık döngü `n`'in ötesini okumamalı; ancak `son - p >= 64` iken girilmeli.

**4** – `__AVX2__` derleme zamanı makrosu, programın **derlendiği** bayrakları söyler, **çalıştığı** işlemciyi değil. AVX2 ile derlenmiş ikili, AVX2'siz makinede `SIGILL` verir (Ders 11.6). Çalışma zamanı seçimi `target("avx2")` ile derlenmiş ayrı bir fonksiyon ve `__builtin_cpu_supports` gerektirir.

**5** – Hayır. 4 çekirdekte zaten bellek tavanındayız (48 GB/s); bant genişliği çekirdek sayısıyla artmıyor (Ders 11.18). Dengesiz bölme ancak **hesap** sınırlı işlerde (Ders 11.19'daki matris çarpımı) işe yarar.

</details>

---

## Kaynaklar

- Rafael C. Gonzalez ve Richard E. Woods, *Digital Image Processing* (4. baskı), Bölüm 3.5 (uzamsal filtreleme, ayrılabilir çekirdekler).
- Jonathan Ragan-Kelley ve ark., "Halide: A Language and Compiler for Optimizing Parallelism, Locality, and Recomputation in Image Processing Pipelines", *PLDI 2013* (birleştirme ve tek geçiş).
- glibc kaynak kodu: `sysdeps/aarch64/strlen.S`, `sysdeps/aarch64/memchr.S`.
- Samuel Williams ve ark., "Roofline", *CACM*, 2009.

**Sıradaki ders:** Faz 12 başlıyor: bilgisayar cebiri nedir? Sayısal ve sembolik hesaplama farkı, kesin aritmetik.
