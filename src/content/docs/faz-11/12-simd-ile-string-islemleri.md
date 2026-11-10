---
title: "11.12 SIMD ile string işlemleri"
description: "pcmpeqb ve pmovmskb ile strlen ve memchr yazmak: Ders 4.13'ün bayt döngüsü ve Ders 5.10'un word sürümüyle yarış; adresi aşağı hizalayarak sayfa sınırını geçmeme garantisi, hizasız safça sürümün SIGSEGV vermesi ve ASan'in bu okumayı yakalaması; 30862 uç durum denemesi, sayfa sonunda sıfır hata; 1 MB'ta 342 µs'den 13 µs'e; glibc'nin farkının dört vektörü tek dalla taramak olduğunu kendi sürümümüzle doğrulama."
---

Ders 4.13'te `strlen`'i byte byte yazdık, standart sürüm 15 kat hızlı çıktı. Ders 5.10'da sekizer byte tarayarak farkın bir kısmını kapattık ve "16 byte'lık parçalarla nasıl okunuyor?" sorusunu buraya bıraktık. Bu ders hem o sorunun yanıtı, hem de önceki derslerin birleştiği yer.

---

## 1. Tek adım

İki komut, üç satır:

```c
__m128i v = _mm_load_si128((const __m128i *)p);
__m128i e = _mm_cmpeq_epi8(v, _mm_setzero_si128());    /* 16 maske byte'i */
unsigned m = _mm_movemask_epi8(e);                     /* 16 bit tamsayi */
```

- `_mm_cmpeq_epi8` (`pcmpeqb`): her byte 0 ise `0xFF`, değilse `0x00`.
- `_mm_movemask_epi8` (`pmovmskb`): her byte'ın en yüksek bitini 16 bitlik sayıya toplar.

Sonuç: `m == 0` ise bu 16 byte'ta sıfır yok. Varsa, ilkinin yeri `__builtin_ctz(m)` (Ders 5.9). Ders 11.11'deki `cmp → movemask → ctz` kalıbı.

---

## 2. Hizalama neden kritik

16 byte'lık okuma, dizinin sonunu aşabilir. Safça sürüm:

```c
/* saf.c: hizalamadan okuyan safca surum */
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <immintrin.h>
static size_t sl_saf(const char *s) {
    const __m128i sifir = _mm_setzero_si128();
    for (size_t i = 0;; i += 16) {
        unsigned m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_loadu_si128((const __m128i *)(s + i)), sifir));
        if (m) return i + (size_t)__builtin_ctz(m);
    }
}
int main(void) {
    long sayfa = sysconf(_SC_PAGESIZE);
    char *m = mmap(0, 2 * sayfa, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    mprotect(m + sayfa, sayfa, PROT_NONE);
    char *s = m + sayfa - 4;
    strcpy(s, "abc");
    printf("%zu\n", sl_saf(m));                  /* sayfanin basi: bos */
    fflush(stdout);
    printf("%zu\n", sl_saf(s));
    return 0;
}
```

```
$ clang -O1 saf.c -o f && ./f; echo "cikis: $?"
0
Segmentation fault
cikis: 139
```

Dize sayfanın son byte'larında bitiyor; sonraki sayfa `PROT_NONE`. 16 byte'lık hizasız okuma sayfa sınırını geçiyor. İlk çağrı (`m`, sayfanın başı, `strcpy`'den önce sıfırla dolu) çalıştı, ikincisi öldü.

Çözüm Ders 5.10'daki argümanla aynı, sadece 16'lık:

**Bir bellek sayfası 4096 byte ve 4096, 16'nın katı. 16'ya hizalı bir adresten 16 byte okumak sayfa sınırını asla geçmez.** Dizinin içindeki bir byte'ın bulunduğu 16'lık blok, o byte ile aynı sayfadadır; o sayfa da okunabilir.

Yani önce adresi aşağı yuvarla, ilk blokta `s`'ten önceki byte'ları görmezden gel:

```c
/* dizgi.h: strlen ve memchr surumleri */
#include <stddef.h>
#include <stdint.h>
#include <immintrin.h>

__attribute__((noinline)) static size_t sl_bayt(const char *s) {
    const char *p = s;
    while (*p) p++;
    return (size_t)(p - s);
}

/* Ders 5.10 */
#define ONES  0x0101010101010101ull
#define HIGHS 0x8080808080808080ull
__attribute__((noinline)) static size_t sl_word(const char *s) {
    const char *p = s;
    while ((uintptr_t)p % 8) { if (!*p) return (size_t)(p - s); p++; }
    for (;;) {
        uint64_t v = *(const uint64_t *)p;
        uint64_t z = (v - ONES) & ~v & HIGHS;
        if (z) return (size_t)(p - s) + ((size_t)__builtin_ctzll(z) >> 3);
        p += 8;
    }
}

__attribute__((noinline)) static size_t sl_sse(const char *s) {
    const __m128i sifir = _mm_setzero_si128();
    const char *p = (const char *)((uintptr_t)s & ~(uintptr_t)15);       /* asagi hizala */
    unsigned bas = (unsigned)((uintptr_t)s & 15);
    unsigned m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), sifir));
    m >>= bas;                                       /* s'den onceki byte'lar sayilmaz */
    if (m) return (size_t)__builtin_ctz(m);
    for (;;) {
        p += 16;
        m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), sifir));
        if (m) return (size_t)(p - s) + (size_t)__builtin_ctz(m);
    }
}

__attribute__((noinline, target("avx2"))) static size_t sl_avx2(const char *s) {
    const __m256i sifir = _mm256_setzero_si256();
    const char *p = (const char *)((uintptr_t)s & ~(uintptr_t)31);
    unsigned bas = (unsigned)((uintptr_t)s & 31);
    unsigned m = (unsigned)_mm256_movemask_epi8(_mm256_cmpeq_epi8(_mm256_load_si256((const __m256i *)p), sifir));
    m >>= bas;
    if (m) return (size_t)__builtin_ctz(m);
    for (;;) {
        p += 32;
        m = (unsigned)_mm256_movemask_epi8(_mm256_cmpeq_epi8(_mm256_load_si256((const __m256i *)p), sifir));
        if (m) return (size_t)(p - s) + (size_t)__builtin_ctz(m);
    }
}

/* glibc'nin yaptigi gibi: 4 vektoru tek dalla tara */
__attribute__((noinline, target("avx2"))) static size_t sl_avx2x4(const char *s) {
    const __m256i sifir = _mm256_setzero_si256();
    const char *p = (const char *)((uintptr_t)s & ~(uintptr_t)31);
    unsigned m = (unsigned)_mm256_movemask_epi8(_mm256_cmpeq_epi8(_mm256_load_si256((const __m256i *)p), sifir));
    m >>= ((uintptr_t)s & 31);
    if (m) return (size_t)__builtin_ctz(m);
    for (p += 32; (uintptr_t)p & 127; p += 32) {      /* 128'e kadar tek tek */
        m = (unsigned)_mm256_movemask_epi8(_mm256_cmpeq_epi8(_mm256_load_si256((const __m256i *)p), sifir));
        if (m) return (size_t)(p - s) + (size_t)__builtin_ctz(m);
    }
    for (;; p += 128) {
        __m256i a = _mm256_load_si256((const __m256i *)p), b = _mm256_load_si256((const __m256i *)(p + 32));
        __m256i c = _mm256_load_si256((const __m256i *)(p + 64)), d = _mm256_load_si256((const __m256i *)(p + 96));
        __m256i k = _mm256_min_epu8(_mm256_min_epu8(a, b), _mm256_min_epu8(c, d));   /* sifir varsa min sifir */
        if (_mm256_movemask_epi8(_mm256_cmpeq_epi8(k, sifir))) break;
    }
    for (;; p += 32) {                                /* hangi vektorde? */
        m = (unsigned)_mm256_movemask_epi8(_mm256_cmpeq_epi8(_mm256_load_si256((const __m256i *)p), sifir));
        if (m) return (size_t)(p - s) + (size_t)__builtin_ctz(m);
    }
}

__attribute__((noinline)) static const void *mc_bayt(const void *v, int c, size_t n) {
    const unsigned char *p = v;
    for (size_t i = 0; i < n; i++) if (p[i] == (unsigned char)c) return p + i;
    return 0;
}

__attribute__((noinline)) static const void *mc_sse(const void *v, int c, size_t n) {
    if (n == 0) return 0;
    const unsigned char *s = v, *son = s + n;
    const __m128i ara = _mm_set1_epi8((char)c);
    const unsigned char *p = (const unsigned char *)((uintptr_t)s & ~(uintptr_t)15);
    unsigned m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), ara));
    m &= 0xFFFFu << ((uintptr_t)s & 15);             /* s'den oncesini ele */
    for (;;) {
        if (m) {
            const unsigned char *r = p + __builtin_ctz(m);
            return r < son ? r : 0;                  /* n'in otesinde bulunduysa yok say */
        }
        p += 16;
        if (p >= son) return 0;
        m = (unsigned)_mm_movemask_epi8(_mm_cmpeq_epi8(_mm_load_si128((const __m128i *)p), ara));
    }
}
```

`m >>= bas` işleminin amacı: hizaya indirdiğimiz için blokta `s`'ten önceki byte'lar da var; onlardaki sıfırları görmemeliyiz.

---

## 3. Doğrulama

Bu kod tam olarak sınır durumlarda hata verir. Tek bir örnek yeterli değil:

```c
/* sina.c: butun hizalar ve uzunluklar, sayfa sinirinda */
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include "dizgi.h"

int main(void) {
    long sayfa = sysconf(_SC_PAGESIZE);
    char *m = mmap(0, 3 * sayfa, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    mprotect(m, sayfa, PROT_NONE); mprotect(m + 2 * sayfa, sayfa, PROT_NONE);
    char *orta = m + sayfa, *bitis = m + 2 * sayfa;
    long deneme = 0, hata = 0;
    for (long len = 0; len < 400; len++) {
        char *s = bitis - len - 1;                   /* '\0' sayfanin son byte'i */
        memset(orta, 'x', sayfa); s[len] = 0;
        for (long i = 0; i < 1; i++) {
            size_t a = sl_bayt(s), b = sl_word(s), c = sl_sse(s), d = sl_avx2(s), e = sl_avx2x4(s);
            deneme++; if (a != (size_t)len || b != a || c != a || d != a || e != a) hata++;
        }
        for (long h = 0; h < 64 && h <= len; h++) {  /* sayfa basina yakin hizalar */
            char *t = orta + h;
            memset(orta, 'x', sayfa); t[len - h] = 0;
            size_t a = sl_bayt(t), c = sl_sse(t), d = sl_avx2(t), e = sl_avx2x4(t);
            deneme++; if (a != (size_t)(len - h) || c != a || d != a || e != a) hata++;
        }
    }
    for (long len = 0; len < 300; len++)
        for (long hedef = -1; hedef < len; hedef += 7) {
            char *s = bitis - len;
            memset(orta, 'x', sayfa);
            if (hedef >= 0) s[hedef] = 'Q';
            const void *a = memchr(s, 'Q', (size_t)len), *b = mc_bayt(s, 'Q', (size_t)len), *c = mc_sse(s, 'Q', (size_t)len);
            deneme++; if (a != b || a != c) hata++;
            /* n'in hemen otesinde eslesme olsa da bulmamali */
            if (len > 0 && hedef == -1) { s = bitis - len - 1; s[len] = 'Q'; deneme++; if (mc_sse(s, 'Q', (size_t)len)) hata++; s[len] = 'x'; }
        }
    printf("%ld deneme, %ld hata\n", deneme, hata);
    return 0;
}
```

```
$ clang -O1 -fno-builtin -g sina.c -o s && ./s
30862 deneme, 0 hata
```

Her iki yanı `PROT_NONE` korumalı sayfanın **tam sonunda** biten dizeler, bütün hizalar, `memchr`'de `n` sınırının hemen ötesinde eşleşme durumu da sınandı. Bir byte fazla okuyan kod anında `SIGSEGV` verirdi. Hepsi referans `strlen`/`memchr` ile aynı.

---

## 4. Hız

```
$ clang -O2 -fno-vectorize -fno-slp-vectorize hiz.c -o h && ./h
   uzunluk      bayt      word      sse2      avx2    avx2x4      libc   (ns/cagri)
         4       3.9       2.7       2.4       3.3       3.3       4.2
        61      20.4       5.7       5.3       5.4       5.6       6.1
      1021     339.1      71.5      52.1      47.0      21.3      22.3
     65533   19528.2    4093.6    2932.2    2633.5     850.9     834.0
   1048573  341627.8   56176.2   47817.7   42259.6   13608.5   13419.6
memchr 64 KB: bayt 32324 ns, sse2 3613 ns, libc 902 ns
```

(Rosetta altında.) 1 MB'lık dizede bayt döngüsüne göre word 6 kat, SSE2 7 kat, `avx2x4` ve glibc **25 kat** hızlı. Kısa dizelerde hepsi birkaç nanosaniye; bu aralıkta çağrı ve başlangıç maliyeti, vektörün boyundan önemli.

Çok ilginç: SSE2 ile AVX2 arasındaki fark küçük, ama glibc üç kat önde. Niye? Bunu "glibc sihirli" diye geçmedim, deneyle test ettim. glibc'nin AVX2 döngüsü **dört vektörü aynı anda** okuyor, `vpminub` ile tek bir vektörde birleştiriyor ve yalnız bir dal kullanıyor:

```c
__m256i k = _mm256_min_epu8(_mm256_min_epu8(a, b), _mm256_min_epu8(c, d));
if (_mm256_movemask_epi8(_mm256_cmpeq_epi8(k, sifir))) break;
```

Sıfır varsa minimum da sıfırdır. `avx2x4` sütunu bu fikri kendimiz yazıyoruz: 13.6 µs, glibc 13.4 µs. **Farkın kaynağı buydu.**

`llvm-mca` Skylake için ne diyor (çevrim/byte, dal cezası hariç):

| Döngü | Tur | Byte | Çevrim/byte |
| --- | --- | --- | --- |
| `word` | 1.01 | 8 | 0.126 |
| `sse2` | 1.01 | 16 | 0.063 |
| `avx2` | 1.01 | 32 | 0.032 |
| `avx2x4` | 2.51 | 128 | 0.020 |

Model `avx2x4`'ün `avx2`'ye üstünlüğünü 1.6 kat görüyor, Rosetta'da 3.1 kat ölçtük. Hangisinin x86 donanıma daha yakın olduğunu burada söyleyemeyiz.

`strlen` gibi fonksiyonlarda glibc'yi yenmeye çalışmaya değmez; bu derste amaç nasıl yazıldığını anlamaktı.

---

## 5. ASan bunu neden şikayet eder?

Hizalanmış okuma standart C açısından yine "dizinin dışını okumak" demektir:

```
$ clang -O1 -g -fsanitize=address asan.c -o a && ./a
==24==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x502000000010 ...
READ of size 16 at 0x502000000010 thread T0
0x502000000015 is located 0 bytes after 5-byte region [0x502000000010,0x502000000015)
```

ASan haklı: 5 byte'lık bir ayırmadan 16 byte okuduk. Bu, donanım garantisine (Ders 5.10) dayanan ve dil standardının tanımlamadığı bir şey. glibc'nin sürümünde bu rapor çıkmaz, çünkü ASan `strlen` çağrılarını kendi denetimli sürümüyle yakalar (interceptor). Kendi kodunda:

```c
__attribute__((no_sanitize("address"))) size_t sl_sse(const char *s) { ... }
```

Bu öznitelikle derlendiğinde ASan rapor vermedi, doğru sonuç (4) yazıldı. Kullanırken dikkat: sadece **kanıtlayabildiğin** taşmalar için, kör susturma için değil.

---

## 6. memchr: bir sınır daha

`memchr`, `strlen`'den farklı olarak bir `n` alıyor. Vektör bulursa, bulduğu yer `n`'in ötesinde olabilir; `r < son` kontrolü bu yüzden. Üstelik döngü `p >= son` olduğunda durmalı, sonrasını okumamalı. `sina.c` bunu `n`'in hemen ötesindeki eşleşmeyle sınıyor.

`m &= 0xFFFFu << ofset` satırı `strlen`'deki `m >>= bas`'in karşılığı: `s`'ten önceki eşleşmeleri ayıklar. Bir kerelik maliyet.

---

## Alıştırmalar

**1** – Neden 16'ya hizalı 16 byte'lık okuma sayfa sınırını geçemez? Yazılı kanıtla.

**2** – `sl_sse`'de `m >>= bas` satırını sil. Hangi girdide yanlış sonuç verir? Küçük bir örnek kur.

**3** – Üç satırlık bir `strcmp` iskeleti tasarla: `_mm_cmpeq_epi8(a, b)` ve "sıfır var mı" kontrolü. Ne zaman durmalı?

**4** – AVX2'de 32'ye aşağı hizalamak hâlâ güvenli mi? Sayfa boyutu 4096 değil 2 MB olsaydı kanıt değişir mi?

**5** – `memchr` için `avx2x4` tarzı dört vektörlü döngüyü (`min` yerine hangi işlem?) tasarla. Sıfır byte aramadığımız için `min` hilesi neden çalışmaz?

<details>
<summary>Cevaplar</summary>

**1** – Sayfa $P = 4096 = 16 \times 256$. Adres $16k$ ve $16k + 15$ aynı $\lfloor \cdot / P \rfloor$ değerine sahip, çünkü $16k \bmod P$, 16'nın katı olduğundan en fazla $P - 16$, $16k+15 \bmod P \le P - 1$. Bloğun tamamı aynı sayfada. Bir byte dizinin içindeyse (ve o sayfa okunabilirse) bloğun tamamı okunabilir.

**2** – `s` hizalı değilse ve aynı blokta `s`'ten önce bir sıfır varsa yanlış. Örnek: `alignas(16) char t[32] = "a\0bcde";`, `sl_sse(t + 3)` doğru cevap 3 (`cde`) iken 1 döndürür; `ctz(m)`, `t[1]`'deki sıfırı buluyor.

**3** – `a = load(p1); b = load(p2); e = cmpeq(a, b); z = cmpeq(a, 0);`. Durum: `m = movemask(e)` bütün bitler 1 değilse fark var, veya `movemask(z) != 0` ise dize bitti. Yerini `ctz(~m | z)` ile bul. Dikkat: iki dizenin hizası farklıysa ikisi birlikte hizalanamaz, bu yüzden `strcmp` hizalama için daha karmaşıktır.

**4** – Evet, 32 de 4096'yı böler, aynı argüman geçerli. Büyük sayfa kanıtı değiştirmez: 2 MB da 32'nin katı.

**5** – Eşleşme için önce `cmpeq(v, ara)` ile dört maskeyi üret (`e1..e4`), sonra **`or`** ile birleştir: `_mm256_or_si256`. `min` hilesi "değer sıfırsa min de sıfır" kuralına dayanıyordu; aranan `c` için bir eşleşmenin kendisi 0 değildir. Alternatifi: `xor` ile `c`'yi 0'a çevirip `min`'e girmek (Ders 5.10).

</details>

---

## Kaynaklar

- Intel, *Intel 64 and IA-32 Architectures SDM*, Cilt 2: `PCMPEQB`, `PMOVMSKB`.
- glibc kaynak kodu: `sysdeps/x86_64/multiarch/strlen-avx2.S`, `memchr-avx2.S`.
- Agner Fog, *Optimizing subroutines in assembly language*, Bölüm 13.
- Wojciech Muła, "SIMD-friendly algorithms for substring searching" (0x80.pl).

**Sıradaki ders:** SIMD ile popcount ve bit işlemleri. Tablo arama (`pshufb`) ile popcount, AVX-512 `vpopcnt`.
