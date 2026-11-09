---
title: "11.5 Aliasing ve restrict"
description: "Derleyicinin en büyük engeli: iki pointer aynı yeri gösterebilir mi? *a += *b iki kez yazıldığında fazladan yükleme; restrict ile assembly farkı; s == &a[2] durumunda sonucun değişmesi; derleyicinin çalışma zamanı kontrolü ile döngüyü sürümlendirmesi ve kod boyutunun iki katına çıkması; restrict sözünü bozunca O2'de farklı sonuç; strict aliasing kuralı, int* ile float* arasında f()'in 1 döndürmesi; char* istisnası ve v->n döngüsünde 10 kat yavaşlama; memcpy ile doğru tip dönüşümü."
---

Ders 11.2–11.4'te işlemcinin sınırlarını zorladık. Bu derste derleyicinin kendi sınırına geliyoruz: **derleyici, bir pointer'ın neyi gösterdiğini bilmiyorsa çok az şey yapabilir.** İki pointer'ın aynı belleği gösterme ihtimaline **aliasing** denir ve optimizasyon derleyicilerinin en büyük problemlerinden biri budur (Faz 16'daki alias analizi geçişi tam bunun için).

---

## 1. Problem

```c
void kotu(long *a, const long *b) { *a += *b; *a += *b; }
void iyi(long *restrict a, const long *restrict b) { *a += *b; *a += *b; }
```

Sanki `*a += 2 * *b` yazılabilir. `a` ve `b` aynı adresi gösteriyorsa ama: `a == b` için `kotu`, `x` değerini `2x` ve sonra `4x` yapar; `2 * *b` eklemek `3x` verir. Derleyici bu olasılık yüzünden kısaltamıyor:

```
$ cc -O2 -S iki.c -o -
kotu:
	ldr	x8, [x1]
	ldr	x9, [x0]
	add	x8, x9, x8
	str	x8, [x0]
	ldr	x9, [x1]          ; *b yeniden okunuyor: a == b olabilir
	add	x8, x9, x8
	str	x8, [x0]
	ret
iyi:
	ldr	x8, [x1]
	ldr	x9, [x0]
	add	x8, x9, x8, lsl #1
	str	x8, [x0]
	ret
```

`restrict`, C99'un derleyiciye verdiği söz: "bu pointer'ın gösterdiği belleğe, bu fonksiyon çalışırken, başka bir yoldan erişilmeyecek." `iyi`'de `*b` tek bir kez okundu, `*a` tek bir kez yazıldı ve iki toplama bir kaydırmaya indi.

### Daha gerçekçi bir örnek

```c
/* Bellek uzerinden biriktirme: derleyici *s'yi neden register'a alamiyor */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
NO void kotu(const long *a, long n, long *s) { *s = 0; for (long i = 0; i < n; i++) *s += a[i]; }
NO void iyi(const long *a, long n, long *s) { long t = 0; for (long i = 0; i < n; i++) t += a[i]; *s = t; }
NO void sinirli(const long *restrict a, long n, long *restrict s) { *s = 0; for (long i = 0; i < n; i++) *s += a[i]; }
static long a[8192]; static long z;
typedef void (*Fn)(const long *, long, long *);
static double sure(Fn f, long n) { double en = 1e9; for (int r = 0; r < 300; r++) { double t0 = simdi(); for (int q = 0; q < 200; q++) { f(a, n, &z); BELLEK(); } double t = simdi() - t0; if (t < en) en = t; } return en / 200 * 1e9 * GHZ; }
#define CPE(f) ((sure(f, 4000) - sure(f, 2000)) / 2000)
int main(void) {
    for (int i = 0; i < 8192; i++) a[i] = i * 3;
    printf("kotu    (*s += ...)   CPE %.2f\n", CPE(kotu));
    printf("restrict              CPE %.2f\n", CPE(sinirli));
    printf("yerel degisken        CPE %.2f\n", CPE(iyi));
    /* farkli sonuc: s dizinin icindeyse */
    long b[3] = { 1, 2, 4 }; long c[3] = { 1, 2, 4 };
    kotu(b, 3, &b[2]); iyi(c, 3, &c[2]);
    printf("s == &a[2]: kotu -> %ld, yerel -> %ld\n", b[2], c[2]);
    return 0;
}
```

`kotu` CS:APP'in klasik "bellek birikimcisi", her turda `*s`'yi güncelliyor. `iyi` bir yerel değişken kullanıyor. Peki aynı şeyi mi yapıyorlar?

```
$ cc -O2 birikim.c -o birikim && ./birikim
kotu    (*s += ...)   CPE 0.50
restrict              CPE 0.50
yerel degisken        CPE 0.50
s == &a[2]: kotu -> 6, yerel -> 7

kotu    (*s += ...)   CPE 1.18
restrict              CPE 1.29
yerel degisken        CPE 1.25
```

(Üst bölüm `-O2`, ikinci bölüm `-O2 -fno-vectorize`.)

İlk ders: **`s == &a[2]` iken sonuçlar farklı.** `kotu`'da `*s = 0` hemen `a[2]`'yi sıfırlıyor ve döngü o sıfırlanmış değerleri okuyor (1, 3, 6); `iyi`'de `a[2]` döngü bitene kadar 4 kalıyor (7). Yani derleyicinin "yerel değişkene al" dönüşümünü **yapmaması** gerekiyor. `kotu`'nun yavaş olması bir derleyici hatası değil, **programın anlamı** bunu gerektiriyor.

İkinci ders, CPE'lerde: üçü de aynı. Klasik ders kitabı anlatımı `kotu`'nun çok yavaş olacağını söyler. Bugünkü derleyici çözümü: **çalışma zamanında sor**.

---

## 2. Döngü sürümlendirme

```
kotu:
	cmp	x1, #1
	str	xzr, [x2]
	b.lt	.LBB0_7
	cmp	x1, #8
	b.lo	.LBB0_4
	add	x8, x0, x1, lsl #3    ; a + n
	cmp	x8, x2                ; a + n <= s ise cakismiyor
	b.ls	.LBB0_8
	add	x8, x2, #8            ; s + 1
	cmp	x8, x0                ; s + 1 <= a ise cakismiyor
	b.ls	.LBB0_8
	...                           ; cakisiyor: yavas, skaler yol
```

Derleyici iki sürüm üretiyor: **çakışmıyorsa** vektörlü hızlı yol (`.LBB0_8`), **çakışıyorsa** her turda yazan yavaş yol. Yukarıda hızlı yola her zaman düştüğümüz için CPE 0.50. Vektörleştirme kapatılınca bu sürümlendirme ortadan kalktığı için üç sürüm de 1.2 civarı oluyor: kazanç zaten vektörleştirmeden geliyormuş (Ders 11.15).

Kontrolün bedelini iki dizi üzerinde ölçelim:

```c
/* Iki dizi: restrict'in vektorlestirmeye etkisi */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
NO void ak(float *d, const float *x, const float *y, long n) { for (long i = 0; i < n; i++) d[i] = x[i] + y[i]; }
NO void ar(float *restrict d, const float *restrict x, const float *restrict y, long n) { for (long i = 0; i < n; i++) d[i] = x[i] + y[i]; }
typedef void (*Fn)(float *, const float *, const float *, long);
static float d[8192], x[8192], y[8192];
static double sure(Fn f, float *dd, const float *xx, long n) { int ic = n < 64 ? 4000 : 200; double en = 1e9; for (int r = 0; r < 300; r++) { double t0 = simdi(); for (int q = 0; q < ic; q++) { f(dd, xx, y, n); BELLEK(); } double t = simdi() - t0; if (t < en) en = t; } return en / ic * 1e9 * GHZ; }
int main(void) {
    long ns[] = { 2, 4, 8, 16, 64, 1000 };
    printf("%-22s", "n"); for (int j = 0; j < 6; j++) printf(" %8ld", ns[j]); printf("  (cevrim/cagri)\n");
    printf("%-22s", "restrict yok"); for (int j = 0; j < 6; j++) printf(" %8.1f", sure(ak, d, x, ns[j])); printf("\n");
    printf("%-22s", "restrict"); for (int j = 0; j < 6; j++) printf(" %8.1f", sure(ar, d, x, ns[j])); printf("\n");
    printf("%-22s", "restrict yok, cakisik"); for (int j = 0; j < 6; j++) printf(" %8.1f", sure(ak, d + 1, d, ns[j])); printf("  (d = x + 1)\n");
    return 0;
}
```

```
$ ./topla
n                             2        4        8       16       64     1000  (cevrim/cagri)
restrict yok                4.0      9.9      5.9      7.0     18.2    288.8
restrict                    5.1     11.0      5.9      5.9     18.2    294.6
restrict yok, cakisik       4.1     10.2     23.2     61.0    471.0  11690.0  (d = x + 1)
```

Uzun dizilerde `restrict` hiçbir kazanç getirmiyor: kontrol maliyeti birkaç çevrimlik bir başlangıç maliyeti. Üstteki iki satırda farklar küçük (çoğu yerde 1 çevrim civarı, `n = 1000`'de yüzde 2) ve yön de tutarsız: ölçüm gürültüsü. Üçüncü satır, kontrolün neden kurtarıcı olduğunu gösteriyor: `d = x + 1` ise derleyici skaler yola düşmek **zorunda**; aksi takdirde sonuç yanlış olur. Bu durumda yazılan her eleman bir sonraki turda okunuyor (Ders 11.1'deki store-to-load iletimi): 11.7 CPE.

Kontrol kod boyutunu büyütüyor:

```
$ nm -S topla | grep -E ' a[kr]$'
0000000000000858 00000000000000a8 T ak
0000000000000900 000000000000008c T ar
```

168 ve 140 bayt, burada küçük bir fark. Pointer sayısı artınca **çiftler** büyüyor: $p$ pointer için $O(p^2)$ kontrol:

```c
/* Cok pointer: calisma zamani kontrolu kac cifte cikar? */
void kotu(float *a, float *b, float *c, float *d, const float *e, const float *f, const float *g, const float *h, long n) {
    for (long i = 0; i < n; i++) { a[i] = e[i] + 1; b[i] = f[i] + 2; c[i] = g[i] + 3; d[i] = h[i] + 4; }
}
void iyi(float *restrict a, float *restrict b, float *restrict c, float *restrict d, const float *restrict e, const float *restrict f, const float *restrict g, const float *restrict h, long n) {
    for (long i = 0; i < n; i++) { a[i] = e[i] + 1; b[i] = f[i] + 2; c[i] = g[i] + 3; d[i] = h[i] + 4; }
}
```

```
$ cc -O2 -c cok.c && nm -S cok.o
0000000000000220 0000000000000114 T iyi
0000000000000000 0000000000000220 T kotu
```

Sekiz pointer'lı döngüde `restrict` olmadan kod **iki katına** (544 bayt, 276 baytın yanında) çıkıyor. Modern derleyici iş görüyor ama çok büyük döngülerde ya da çok pointer'lı işlevlerde kontrol maliyeti eşiği aşınca vektörleştirmeyi bırakır. Yani `restrict` bugün çoğunlukla: (1) kod boyutu, (2) kısa dizilerde başlangıç maliyeti ve (3) kontrol yapılamayan (bir döngünün yineleme sayısı önceden belli olmayan) durumlarda vektörleştirmeyi sağlıyor.

---

## 3. restrict bir sözdür

`restrict` derleyiciye verilmiş bir söz, kontrol edilmiyor. Bozarsan davranış tanımsız:

```c
/* restrict sozunu bozmak */
#include <stdio.h>
__attribute__((noinline)) void kaydir(int *restrict d, const int *restrict k, int n) { for (int i = 0; i < n; i++) d[i] = k[i]; }
__attribute__((noinline)) void kaydir_guvenli(int *d, const int *k, int n) { for (int i = 0; i < n; i++) d[i] = k[i]; }
int main(void) {
    int a[12], b[12];
    for (int i = 0; i < 12; i++) a[i] = b[i] = i;
    kaydir(a + 1, a, 11); kaydir_guvenli(b + 1, b, 11);
    printf("restrict: "); for (int i = 0; i < 12; i++) printf("%d ", a[i]);
    printf("\nnormal  : "); for (int i = 0; i < 12; i++) printf("%d ", b[i]);
    printf("\n");
    return 0;
}
```

```
$ cc -O0 ihlal.c -o i0 && ./i0
restrict: 0 0 0 0 0 0 0 0 0 0 0 0 
normal  : 0 0 0 0 0 0 0 0 0 0 0 0 
$ cc -O2 ihlal.c -o i2 && ./i2
restrict: 0 0 1 2 3 4 5 6 7 8 9 10 
normal  : 0 0 0 0 0 0 0 0 0 0 0 0 
```

`kaydir` çakışan bölgelerle çağrılıyor: `a + 1`'e `a`'dan kopyala. `-O0`'da bir sıra ile (her eleman bir öncekinin **yeni** değerini okuyor) hepsi 0 oluyor. `-O2`'de ise derleyici vektörleştiriyor ve `0 0 1 2 3 ...`; ne `-O0` ne `normal` ile aynı.

Bu standart kütüphanede somut bir sözleşme: `memcpy(void *restrict d, const void *restrict k, size_t n)`: kaynak ve hedef çakışamaz. `memmove`'un `restrict`'i yok: çakışmayı kontrol edip doğru yönde kopyalar (Ders 4.18). Çakışan `memcpy` hatası uzun süre fark edilmeyip kütüphane güncellenince patlayan klasik bir hatadır.

Kullanım kuralı: `restrict` yazmadan önce çağıranlardan hiçbirinin çakışan pointer geçmediğinden emin ol, ve yalnızca ölçüm kazanç gösteriyorsa kullan.

---

## 4. Strict aliasing

Derleyicinin `restrict` olmadan bile bir kısayolu var: C standardının **etkin tip kuralı** (§6.5/7, "strict aliasing"). Kabaca: bir nesneye ancak **kendi tipinden** (ya da uyumlu bir tipten, `signed`/`unsigned` karşılığından, ya da `char` türlerinden) bir lvalue ile erişilebilir. Buna göre `int *` ve `float *` aynı belleği göstermiyor varsayılabilir.

```c
/* Strict aliasing: farkli tipler ayni bellegi gostermez varsayimi */
#include <stdio.h>
__attribute__((noinline)) int f(int *i, float *g) { *i = 1; *g = 0.0f; return *i; }
__attribute__((noinline)) int f2(int *i, char *g) { *i = 1; *g = 0; return *i; }
__attribute__((noinline)) int f3(int *i, unsigned *g) { *i = 1; *g = 0; return *i; }
int main(void) {
    int x = 7; printf("f  (int*, float*)    -> %d\n", f(&x, (float *)&x));
    x = 7; printf("f2 (int*, char*)     -> %d\n", f2(&x, (char *)&x));
    x = 7; printf("f3 (int*, unsigned*) -> %d\n", f3(&x, (unsigned *)&x));
    return 0;
}
```

```
$ cc -O0 katisi.c -o k0 && ./k0
f  (int*, float*)    -> 0
f2 (int*, char*)     -> 0
f3 (int*, unsigned*) -> 0
$ cc -O2 katisi.c -o k2 && ./k2
f  (int*, float*)    -> 1
f2 (int*, char*)     -> 0
f3 (int*, unsigned*) -> 0
$ cc -O2 -fno-strict-aliasing katisi.c -o k3 && ./k3
f  (int*, float*)    -> 0
f2 (int*, char*)     -> 0
f3 (int*, unsigned*) -> 0
```

`f`'in `-O2`'de 1 dönmesi "optimizasyon hatası" gibi görünür, değildir: program tanımsız, derleyici haklı. Üretilen kod:

```
f:
	mov	w8, #1
	str	wzr, [x1]
	str	w8, [x0]
	mov	w0, #1            ; *i'yi okumadan 1 dondur
	ret
f2:
	mov	w8, #1
	str	w8, [x0]
	strb	wzr, [x1]
	ldr	w0, [x0]          ; char olabilir: yeniden oku
	ret
```

`f`'te iki yazma yer bile değiştirdi. `char` istisnası `f2`'de işliyor: `char*` her nesneyi gösterebilir, derleyici `ldr` yapmak zorunda. Bilgiyi tip tabanlı alias analizi (TBAA) taşıyor; LLVM IR'da açıkça görülüyor:

```
$ cc -O2 -S -emit-llvm katisi.c -o -
  store i32 1, ptr %0, align 4, !tbaa !6
  store float 0.000000e+00, ptr %1, align 4, !tbaa !10
  store i32 1, ptr %0, align 4, !tbaa !6
  store i8 0, ptr %1, align 1, !tbaa !12
```

Her belleğe erişimin üzerinde "tip etiketi" var (Faz 16).

### char ile sürpriz

`char*` istisnası hızlı kodda sessizce can yakıyor:

```c
/* char aliasing: char* her seyi gosterebilir */
#include "olcum.h"
#include <stdint.h>
#include <stdio.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
typedef struct { char *p; long n; } TB;
typedef struct { uint16_t *p; long n; } TS;
NO void c_doldur(TB *v) { for (long i = 0; i < v->n; i++) v->p[i] = 1; }
NO void s_doldur(TS *v) { for (long i = 0; i < v->n; i++) v->p[i] = 1; }
NO void c_yerel(TB *v) { char *p = v->p; long n = v->n; for (long i = 0; i < n; i++) p[i] = 1; }
static char b[8192]; static uint16_t h[8192];
int main(void) {
    TB t = { b, 8000 }; TS u = { h, 8000 }; double e1 = 1e9, e2 = 1e9, e3 = 1e9;
    for (int r = 0; r < 2000; r++) {
        double t0 = simdi(); c_doldur(&t); BELLEK(); double a = simdi() - t0; if (a < e1) e1 = a;
        t0 = simdi(); s_doldur(&u); BELLEK(); a = simdi() - t0; if (a < e2) e2 = a;
        t0 = simdi(); c_yerel(&t); BELLEK(); a = simdi() - t0; if (a < e3) e3 = a;
    }
    printf("char*, v->n dongude : %.2f cevrim/eleman\nuint16_t*          : %.2f cevrim/eleman\nchar*, yerel kopya  : %.2f cevrim/eleman\n", e1 * 1e9 * GHZ / 8000, e2 * 1e9 * GHZ / 8000, e3 * 1e9 * GHZ / 8000);
    return 0;
}
```

```
$ cc -O2 doldur.c -o doldur && ./doldur
char*, v->n dongude : 0.97 cevrim/eleman
uint16_t*          : 0.09 cevrim/eleman
char*, yerel kopya  : 0.02 cevrim/eleman
```

`char *p` üzerinden yazmak, `v->n`'i (long) bile değiştirebilir. Her turda `v->n` ve `v->p` yeniden yükleniyor:

```
c_doldur:
	ldr	x8, [x0, #8]
	...
	ldr	x10, [x0]         ; v->p yeniden
	strb	w9, [x10, x8]
	add	x8, x8, #1
	ldr	x10, [x0, #8]     ; v->n yeniden
	cmp	x8, x10
	b.lt	.LBB0_2
```

`uint16_t` sürümünde yazma, `long`'a takma olamaz: derleyici `n`'i dışarı aldı ve vektörleştirdi: **10 kat** hızlı. Yerel kopya yapılan `c_yerel`'de ise `memset` bile çıkıyor (0.02). Pratik kural: bir yapının alanını döngüde kullanacaksan önce yerel değişkene al; özellikle işaretçi `char` ise. Bu Ders 4.13'teki `strlen` tuzağının kuzeni.

---

## 5. Bitleri doğru okumak

Bir `float`'un bitlerine bakmak (Ders 5.18) doğru yollarla yapılmalı:

```c
/* float'un bitlerini okumanin dogru ve yanlis yollari */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
uint32_t yanlis(float f) { return *(uint32_t *)&f; }
uint32_t dogru(float f) { uint32_t u; memcpy(&u, &f, sizeof u); return u; }
uint32_t birlik(float f) { union { float f; uint32_t u; } b; b.f = f; return b.u; }
int main(void) { printf("%08x %08x %08x\n", yanlis(1.5f), dogru(1.5f), birlik(1.5f)); return 0; }
```

```
$ ./bitler
3fc00000 3fc00000 3fc00000
```

Üçü de bu derlemede aynı sonucu verdi, ama `yanlis` tanımsız davranış; bir gün değişik bağlamda `f` örneği gibi farklı kod üretebilir. `memcpy` hem doğru hem ücretsiz: derleyici onu tanıyıp tek komuta indiriyor.

```
dogru:
	fmov	w0, s0
	ret
```

Bu nedenle Ders 5.18'de hep `memcpy` kullandık. `union` C'de geçerli (Ders 4.27), C++'ta değil (`std::bit_cast`; Faz 13).

Linux çekirdeği gibi çok fazla tip dönüşümü yapan kod `-fno-strict-aliasing` ile derlenir; bu güvenli ama performans bedeli olan bir seçenek. Yeni kod için doğrusu kurallara uymak ve `-fsanitize=undefined` gibi araçların yakalayamadığı bu tür hataları kod incelemesiyle önlemek.

---

## Alıştırmalar

**1** – `kotu(a, a)` ve `iyi(a, a)`'nın ikisini de `*a = 1` için elle izle. `restrict` sözü bozulunca `iyi` ne döndürür?

**2** – `void f(int *a, long *b) { for (i...) a[i] = *b; }`. Strict aliasing, `*b`'yi dışarı almaya izin verir mi? Tipleri `int *a, int *b` yapınca ne değişir?

**3** – `doldur.c`'de `char` yerine `signed char`, sonra `int8_t` yap. Sonuç ne olur? Neden?

**4** – Yerinde bir normalizasyon fonksiyonu `void norm(float *a, float *toplam, long n)`: `*toplam` ile her elemanı böler. Aliasing tuzağı nerede? Düzelt.

**5** – Ders 11.15'te göreceğimiz vektörleştirici için, `for (i) a[i] = b[i - 1] + 1` ile `for (i) a[i] = b[i + 1] + 1` döngülerinde `a == b` olursa hangisi vektörleştirilemez? Nedenini yazma sırasıyla açıkla.

<details>
<summary>Cevaplar</summary>

**1** – `kotu(a, a)`: `*a = 1`: birinci toplama 2, ikinci 4 (her seferinde `*b` yeniden okunuyor). `iyi(a, a)`: `*a + 2 * *b` hesaplıyor: 3. `restrict` sözü bozulduğu için davranış **tanımsız**; aslında derlenen kodun verdiği sonuç 3 olsa da buna güvenilemez.

**2** – Evet: `int` ve `long` farklı tipler, `a[i] = ...` `*b`'yi etkileyemez varsayılır; `*b` bir kez okunup dışarı alınabilir. `int *a, int *b` yapınca aynı tipte oldukları için alias olabilirler: `*b` her turda okunmak zorunda ya da derleyici çalışma zamanı kontrolü ekler.

**3** – `signed char` da karakter tipi olduğundan istisnaya dahildir: aynı yavaş sonuç. `int8_t` genellikle `signed char`'ın takma adı olduğu için aynı. `uint16_t` gibi bir tip hızlı kalır. Yani "byte" türü alias için hep karakter tipidir.

**4** – Kod: `for (i) a[i] /= *toplam;`. Derleyici `*toplam`'ı dışarı alamaz, çünkü `toplam == &a[3]` olabilir ve `a[3]` değiştiğinde bölen de değişir. Çözüm: `float t = *toplam;` ile döngüden önce kopyala (ya da `restrict`). Kopyalamak anlamı da netleştirir: "bölen sabit".

**5** – `a[i] = b[i - 1] + 1` ile `a == b`: her eleman bir önceki turda **yazılan** değeri okuyor; sıralı bağımlılık, vektörlenince sonuç yanlış olur (eski değerler okunur). Vektörleştirilemez. `a[i] = b[i + 1] + 1` ile `a == b`: her eleman henüz yazılmamış (ileriki) değeri okuyor; vektörlü halde de aynı eski değerler okunduğu için güvenli, vektörleştirilebilir.

</details>

---

## Kaynaklar

- ISO/IEC 9899:2011 (C11), §6.5/7 (etkin tip kuralı), §6.7.3.1 (`restrict`).
- Randal Bryant ve David O'Hallaron, *CS:APP* (3. baskı), Bölüm 5.1: bellek aliasing'i ve optimizasyon engelleri.
- Mike Acton, "Understanding Strict Aliasing", 2006 (cellperformance.beyond3d.com).
- John Regehr, "A Guide to Undefined Behavior in C and C++", 2010 (blog.regehr.org).
- LLVM belgeleri: "Alias Analysis Infrastructure" ve TBAA metadata.
- Pascal Cuoq ve ark., "Detecting Strict Aliasing Violations in the Wild", *VMCAI 2017*.

**Sıradaki ders:** SIMD kavramı. Flynn sınıflandırması, vektör register'ı, lane, SSE/AVX/AVX-512/NEON/RVV genel bakış.
