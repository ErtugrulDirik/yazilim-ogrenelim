---
title: "11.9 Tamsayı SIMD"
description: "__m128i ile byte ve word şeritleri: add_epi8'in sarması, adds_epu8'in doyması, 8 bitlik karşılaştırma ve kaydırmanın olmayan sürümleri; görüntü parlaklığı dalsız ve C ile 256 değerde birebir aynı sonuç; kontrast için unpack, mullo_epi16, srli ve packus; packus'un 40000'i sıfıra çevirmesi; x>>8'in yüzde 87 yanlış olması ve 255'e bölme hilesinin 65026 değerin tamamında doğruluğu; alfa harmanlama, avg ve sad; 14 kata varan hızlanma."
---

SIMD'in en büyük kazançları görüntü, ses ve metin gibi **küçük tamsayı** verilerinde. 128 bite 4 `float` sığarken 16 `uint8_t` sığıyor. Üstelik donanım, küçük tamsayılar için C'de olmayan işlemler sunuyor. Bu ders ayrıca SIMD'in **eksik** komutlarını anlatıyor: ne yazık ki küme simetrik değil.

---

## 1. Sarma ve doyma

C'de `(uint8_t)(250 + 10)` 4 olur: 8 bitte sarar. Görüntüde bu felaket: çok parlak piksel siyah oluyor. Donanımda **doymalı** (*saturating*) toplama var.

```c
/* doyma.c: sarma ve doyma */
#include <stdio.h>
#include <immintrin.h>

static void yaz(const char *ad, __m128i v, int isaretli) {
    unsigned char b[16]; _mm_storeu_si128((__m128i *)b, v);
    printf("%-16s", ad);
    for (int i = 0; i < 6; i++) printf(" %4d", isaretli ? (int)(signed char)b[i] : (int)b[i]);
    printf("\n");
}

int main(void) {
    __m128i a = _mm_setr_epi8((char)250, (char)200, 100, 0, 5, (char)255, 0,0,0,0,0,0,0,0,0,0);
    __m128i b = _mm_setr_epi8(10, 100, 100, 5, 5, 1, 0,0,0,0,0,0,0,0,0,0);
    yaz("a (uint8)", a, 0);
    yaz("b (uint8)", b, 0);
    yaz("add_epi8", _mm_add_epi8(a, b), 0);
    yaz("adds_epu8", _mm_adds_epu8(a, b), 0);
    yaz("subs_epu8 (a-b)", _mm_subs_epu8(a, b), 0);
    yaz("avg_epu8", _mm_avg_epu8(a, b), 0);
    __m128i c = _mm_setr_epi8(120, -120, 50, -50, 127, -128, 0,0,0,0,0,0,0,0,0,0);
    __m128i d = _mm_setr_epi8(20, -20, 50, -50, 1, -1, 0,0,0,0,0,0,0,0,0,0);
    yaz("c (int8)", c, 1);
    yaz("d (int8)", d, 1);
    yaz("add_epi8", _mm_add_epi8(c, d), 1);
    yaz("adds_epi8", _mm_adds_epi8(c, d), 1);
    return 0;
}
```

```
$ cc -O2 doyma.c -o a && ./a
a (uint8)         250  200  100    0    5  255
b (uint8)          10  100  100    5    5    1
add_epi8            4   44  200    5   10    0
adds_epu8         255  255  200    5   10  255
subs_epu8 (a-b)   240  100    0    0    0  254
avg_epu8          130  150  100    3    5  128
c (int8)          120 -120   50  -50  127 -128
d (int8)           20  -20   50  -50    1   -1
add_epi8         -116  116  100 -100 -128  127
adds_epi8         127 -128  100 -100  127 -128
```

- `adds_epu8`: işaretsiz doyma, $[0, 255]$'te kırpar. `subs_epu8` alttan 0'da durur.
- `adds_epi8`: işaretli, $[-128, 127]$. Ses örneklerini toplarken doğru sürüm budur.
- `avg_epu8`: $(a + b + 1) \gg 1$, yuvarlayan ortalama; ara hesap 9 bit olsa da **taşmaz**. Birçok görüntü işlemede kullanışlı.

Bu kadarı, Ders 5.6'daki taşma kontrollerini 16 şeritte, dalsız, tek komuta indiriyor.

---

## 2. Olmayan komutlar

SIMD tamsayı kümesi eksik. Üç klasik:

```c
/* tuzak.c: 8 bit serit icin olmayan komutlar */
#include <stdio.h>
#include <immintrin.h>

static void yaz(const char *ad, __m128i v) {
    unsigned char b[16]; _mm_storeu_si128((__m128i *)b, v);
    printf("%-22s", ad);
    for (int i = 0; i < 4; i++) printf(" %3d", b[i]);
    printf("\n");
}

int main(void) {
    __m128i a = _mm_setr_epi8((char)200, 100, 7, (char)255, 0,0,0,0,0,0,0,0,0,0,0,0);
    __m128i b = _mm_set1_epi8(100);
    yaz("a", a);
    yaz("cmpgt_epi8(a,100)", _mm_cmpgt_epi8(a, b));
    __m128i isaret = _mm_set1_epi8((char)0x80);
    yaz("xor 0x80 ile", _mm_cmpgt_epi8(_mm_xor_si128(a, isaret), _mm_xor_si128(b, isaret)));
    yaz("srli_epi16(a,1)", _mm_srli_epi16(a, 1));
    yaz("srli_epi16 & 0x7f", _mm_and_si128(_mm_srli_epi16(a, 1), _mm_set1_epi8(0x7f)));
    return 0;
}
```

```
$ clang -O2 tuzak.c -o b && ./b
a                      200 100   7 255
cmpgt_epi8(a,100)        0   0   0   0
xor 0x80 ile           255   0   0 255
srli_epi16(a,1)        100  50 131 127
srli_epi16 & 0x7f      100  50   3 127
```

1. **`_mm_cmpgt_epi8` yalnız işaretli**. 200 bit deseninde -56'dır, `-56 > 100` yanlış. Çözüm: her iki tarafı `0x80` ile XOR'la (işaretsiz aralığı işaretli aralığa kaydırır). Alternatif olarak $a \ge b$ testi: `_mm_cmpeq_epi8(_mm_max_epu8(a, b), a)` (AVX-512 öncesinde işaretsiz karşılaştırma komutu yok).
2. **8 bitlik kaydırma yok**, `_mm_srli_epi16` var. 16 bitlik kaydırmada komşu byte'tan bit sızar: `7 >> 1` beklenirken 131 çıktı (`7` şeridine, üst byte 255'in düşük biti girdi). Çözüm: `0x7f` maskesi. Ders 5'in maske mantığı.
3. **8 bitlik çarpma yok**. 16'ya genişletip çarpmak gerek (bir sonraki bölüm).

---

## 3. Parlaklık

Her pikselin değerine sabit bir sayı eklemek:

```c
/* parlak.c: gri goruntu parlakligi ve kontrasti */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <immintrin.h>
#include "olcum.h"

typedef unsigned char u8;

__attribute__((noinline))
void parlak_c(u8 *d, const u8 *k, long n, int e) {
    for (long i = 0; i < n; i++) {
        int v = k[i] + e;
        if (v > 255) v = 255;
        d[i] = (u8)v;
    }
}

__attribute__((noinline))
void parlak_sse(u8 *d, const u8 *k, long n, int e) {
    __m128i ve = _mm_set1_epi8((char)e);
    long i = 0;
    for (; i + 16 <= n; i += 16)
        _mm_storeu_si128((__m128i *)(d + i),
                         _mm_adds_epu8(_mm_loadu_si128((const __m128i *)(k + i)), ve));
    for (; i < n; i++) { int v = k[i] + e; d[i] = (u8)(v > 255 ? 255 : v); }
}

/* k/16 ile carp: katsayi 16 = 1.0 */
__attribute__((noinline))
void kontrast_c(u8 *d, const u8 *k, long n, int c) {
    for (long i = 0; i < n; i++) {
        int v = (k[i] * c) >> 4;
        d[i] = (u8)(v > 255 ? 255 : v);
    }
}

__attribute__((noinline))
void kontrast_sse(u8 *d, const u8 *k, long n, int c) {
    __m128i sifir = _mm_setzero_si128(), vc = _mm_set1_epi16((short)c);
    long i = 0;
    for (; i + 16 <= n; i += 16) {
        __m128i v  = _mm_loadu_si128((const __m128i *)(k + i));
        __m128i lo = _mm_unpacklo_epi8(v, sifir);       /* 8 x uint16 */
        __m128i hi = _mm_unpackhi_epi8(v, sifir);
        lo = _mm_srli_epi16(_mm_mullo_epi16(lo, vc), 4);
        hi = _mm_srli_epi16(_mm_mullo_epi16(hi, vc), 4);
        _mm_storeu_si128((__m128i *)(d + i), _mm_packus_epi16(lo, hi));
    }
    for (; i < n; i++) { int v = (k[i] * c) >> 4; d[i] = (u8)(v > 255 ? 255 : v); }
}

typedef void fn(u8 *, const u8 *, long, int);

static double olc(fn *f, u8 *d, u8 *k, long n, int e) {
    double en = 1e9;
    for (int t = 0; t < 7; t++) {
        double b0 = simdi();
        for (int r = 0; r < 200; r++) { f(d, k, n, e); BELLEK(); }
        double s = simdi() - b0; if (s < en) en = s;
    }
    return en * 1e3 / 200;
}

int main(void) {
    long w = 1920, h = 1080, n = w * h;
    u8 *k = malloc((size_t)n), *a = malloc((size_t)n), *b = malloc((size_t)n);
    unsigned long long s = 88172645463325252ull;
    for (long i = 0; i < n; i++) { s ^= s << 13; s ^= s >> 7; s ^= s << 17; k[i] = (u8)s; }

    /* butun deger ve butun katsayilar: C ile bire bir ayni mi? */
    u8 hepsi[256 + 16], x[272], y[272];
    for (int i = 0; i < 272; i++) hepsi[i] = (u8)i;
    long bad = 0;
    for (int e = 0; e < 256; e++) {
        parlak_c(x, hepsi, 272, e); parlak_sse(y, hepsi, 272, e);
        bad += memcmp(x, y, 272) != 0;
    }
    for (int c = 0; c < 256; c++) {
        kontrast_c(x, hepsi, 272, c); kontrast_sse(y, hepsi, 272, c);
        bad += memcmp(x, y, 272) != 0;
    }
    printf("256 parlaklik + 256 kontrast katsayisi: %ld farkli sonuc\n", bad);

    printf("parlaklik C   : %.3f ms/kare\n", olc(parlak_c, a, k, n, 40));
    printf("parlaklik SSE : %.3f ms/kare\n", olc(parlak_sse, a, k, n, 40));
    printf("kontrast  C   : %.3f ms/kare\n", olc(kontrast_c, a, k, n, 22));
    printf("kontrast  SSE : %.3f ms/kare\n", olc(kontrast_sse, a, k, n, 22));
    (void)b;
    return 0;
}
```

İki not: hiçbir `if` yok, ve doğruluğu **bütün** 256 piksel değeri ve **bütün** 256 parlaklık/kontrast katsayısı için sınıyoruz. 8 bitte tam tarama ucuz:

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize parlak.c -o c && ./c
256 parlaklik + 256 kontrast katsayisi: 0 farkli sonuc
parlaklik C   : 0.645 ms/kare
parlaklik SSE : 0.046 ms/kare
kontrast  C   : 0.733 ms/kare
kontrast  SSE : 0.080 ms/kare
```

(1920×1080 tek kanal, Rosetta altında.) Parlaklık **14 kat**, kontrast **9 kat** hızlandı. 16 şeritlik register'dan beklenen büyüklükte. C sürümünü vektörleştirmeyi açarak derlediğimizde parlaklık 0.361 ms'e iniyor, kontrastta ise (0.803 ms) kazanç yok: derleyici elle yazılan `adds_epu8` ve `packus` düzeyine ulaşamıyor.

Kontrast işlemi 8 bitlik çarpmanın eksikliğini gösteriyor. Adımlar:

```
 v      : 16 x uint8
 lo, hi : unpack -> 8 x uint16 (ust byte 0)
 *c     : mullo_epi16
 >> 4   : k / 16 sabit noktasi
 pack   : packus_epi16 -> 16 x uint8, doyar
```

`_mm_packus_epi16` işaretli 16 bit girdileri işaretsiz 8 bite **doyurur**: büyükse 255, negatifse 0. "Bu doyma neden işe yarıyor?" sorusunun yanıtı: `v * c >> 4` en fazla $255 \times 255 / 16 \approx 4064$, 16 bit işaretliye sığıyor, yani 255'e doğru kırpılıyor. Sınıra dikkat: `packus` girdisini **işaretli** kabul eder. 40000 girersen (işaretli olarak negatif) sonuç **0** olur, 255 değil. Denedik: `_mm_packus_epi16` ile 40000 → 0, 300 → 255.

---

## 4. 255'e bölme

Alfa karıştırma $\text{sonuç} = (k \cdot a + g \cdot (255 - a)) / 255$. SIMD'de tamsayı bölme yok, Ders 5.14'teki sabite bölme devreye giriyor. Sık yapılan hata `x >> 8` ile yaklaşık bölmek:

```c
/* alfa.c: 255'e bolme hilesi, butun girdilerde */
#include <stdio.h>
#include <immintrin.h>

int main(void) {
    long yanlis_shift = 0, yanlis_hile = 0;
    for (int x = 0; x <= 65025; x++) {
        int dogru = (x * 2 + 255) / 510;               /* round(x / 255) */
        if (x >> 8 != dogru) yanlis_shift++;
        int t = x + 128;
        if ((t + (t >> 8)) >> 8 != dogru) yanlis_hile++;
    }
    printf("x>>8 yanlis: %ld / 65026\n(x+128 + (x+128)>>8) >> 8 yanlis: %ld / 65026\n", yanlis_shift, yanlis_hile);

    /* SSE ile: 8 piksel, alfa karistirma */
    __m128i a = _mm_setr_epi16(255, 0, 128, 77, 200, 13, 90, 255);
    __m128i k = _mm_setr_epi16(10, 20, 30, 40, 50, 60, 70, 80);
    __m128i g = _mm_setr_epi16(200, 200, 200, 200, 200, 200, 200, 200);
    __m128i x = _mm_add_epi16(_mm_mullo_epi16(k, a), _mm_mullo_epi16(g, _mm_sub_epi16(_mm_set1_epi16(255), a)));
    __m128i t = _mm_add_epi16(x, _mm_set1_epi16(128));
    __m128i s = _mm_srli_epi16(_mm_add_epi16(t, _mm_srli_epi16(t, 8)), 8);
    short o[8]; _mm_storeu_si128((__m128i *)o, s);
    for (int i = 0; i < 8; i++) printf("%d ", o[i]);
    puts("");
    return 0;
}
```

```
$ clang -O2 alfa.c -o d && ./d
x>>8 yanlis: 56770 / 65026
(x+128 + (x+128)>>8) >> 8 yanlis: 0 / 65026
10 200 115 152 82 193 154 80 
```

$0 \le x \le 65025$ ($255^2$) aralığındaki **her** değerde sınadık. Basit kaydırma yüzde 87 oranında yanlış sonuç veriyor; ikinci formül sıfır hatalı. Son satır sekiz pikseli bu formülle harmanlıyor. Formül **doğru yuvarlanmış** bölme verir: $\mathrm{round}(x/255)$.

---

## 5. Bir daha fazlası: SAD

`_mm_sad_epu8` iki 16 byte'lık bloğun mutlak fark toplamını iki 64 bitlik parça olarak üretir. Tek komut, video kodlamadaki hareket arama çekirdeğinin ta kendisi:

```c
/* sad.c: iki 16 byte'lik blok arasindaki fark */
#include <stdio.h>
#include <stdlib.h>
#include <immintrin.h>

int main(void) {
    unsigned char a[16], b[16];
    long ctoplam = 0;
    for (int i = 0; i < 16; i++) { a[i] = (unsigned char)(i * 17); b[i] = (unsigned char)(255 - i * 9); ctoplam += labs((long)a[i] - b[i]); }
    __m128i s = _mm_sad_epu8(_mm_loadu_si128((__m128i *)a), _mm_loadu_si128((__m128i *)b));
    long hi = _mm_cvtsi128_si64(_mm_unpackhi_epi64(s, s)), lo = _mm_cvtsi128_si64(s);
    printf("C: %ld  SSE: %ld + %ld = %ld\n", ctoplam, lo, hi, lo + hi);
    return 0;
}
```

```
$ ./e
C: 1800  SSE: 1312 + 488 = 1800
```

Bu komut Ders 11.13'te yan etkisiyle karşımıza çıkacak: `v` sıfırla SAD yaparsan **yatay toplama** yapıyorsun.

---

## Alıştırmalar

**1** – `_mm_adds_epi8` 100 + 100, `_mm_adds_epu8` 100 + 200, `_mm_subs_epu8` 3 − 5 kaç verir?

**2** – `a >= b` testini işaretsiz 8 bit için yaz (komut yoksa nasıl?). `a = (200, 100, 7, 255)`, `b = 100` için çıktı?

**3** – Her byte'ı 2 sola kaydıran `_mm_slli_epi16` tabanlı fonksiyon yaz. `(200, 100, 7, 255)` sonucunu tahmin et.

**4** – `kontrast_sse`'de `c = 300` ve `>> 4` yerine `>> 0` yapsaydık hangi aşamada ne bozulur?

**5** – 32 bitlik RGBA pikseli için 16 bitlik `mullo` yeterli, ama `_mm_mullo_epi32`'nin SSE4.1 gerektirdiğini Intrinsics Guide'dan bul. `_mm_madd_epi16` ne yapıyor, gri tonlama hesabı için nasıl kullanılır?

<details>
<summary>Cevaplar</summary>

**1** – 127, 255, 0.

**2** – `_mm_cmpeq_epi8(_mm_max_epu8(a, b), a)`. Çıktı: `255 255 0 255`. (Denedik.)

**3** – `_mm_and_si128(_mm_slli_epi16(a, 2), _mm_set1_epi8(0xFC))`. Çıktı: `32 144 28 252` (200 << 2 = 800, 8 bit tutunca 32).

**4** – `255 * 300 = 76500`, 16 bite sığmaz. `mullo_epi16` düşük 16 biti tutar: taşma ilk orada, sessizce. `>> 0` olursa değer 32767'yi aşabildiğinden `packus` onu negatif görür ve **0'a** kırpar: parlak pikseller siyah olur.

**5** – `_mm_madd_epi16`: işaretli 16 bitleri çarpar, komşu 32 bitlik çarpımları toplar. Bir pikselin R ve G değerlerini tek şeritte `(r * kr + g * kg)` olarak hesaplar; gri tonlamanın iki yarım toplamını bu tek komut verir.

</details>

---

## Kaynaklar

- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 2: `PADDUSB`, `PACKUSWB`, `PSADBW`, `PMADDWD`.
- Jim Blinn, "Three Wrongs Make a Right", *IEEE Computer Graphics and Applications*, 1995 (255'e bölme).

**Sıradaki ders:** Karıştırma ve permütasyon. `shuffle`, `blend`, `permute`; SIMD ile matris transpozu.
