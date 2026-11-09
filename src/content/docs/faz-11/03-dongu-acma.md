---
title: "11.3 Döngü açma (unrolling)"
description: "Bir döngüyü açmak: kalan döngüsü, Duff'ın aleti; neden işe yaradığı ve yaramadığı: tek birikimcide kazanç yok (1.07'den 0.95'e), bellek kopyalamada CPE 1.2'den 0.52'ye; #pragma clang loop unroll_count, #pragma unroll ve -Rpass=loop-unroll; tam açma; bedeli: kod 32 bayttan 200 bayta, kısa dizilerde kalan döngüsü; n=1024'te bütün sürümlerin 1.56'ya çıkması."
---

Ders 11.2'de `2x1` çarpım döngüsünün bir kazanç getirmediğini gördük. **Döngü açma** (loop unrolling) yine de en eski ve en yaygın optimizasyonlardan biri. Bu derste ne zaman işe yaradığını, ne zaman yaramadığını ve bedelini ölçüyoruz; sonra derleyiciye yaptırıyoruz.

Fikir basit: aynı işi her turda bir kez yapıp $n$ kez dallanmak yerine, $k$ kez yapıp $n/k$ kez dallanmak.

```c
/* acilmamis */                     /* 4 acilmis */
for (i = 0; i < n; i++)             for (i = 0; i + 3 < n; i += 4) {
    d[i] = k[i] + 1;                    d[i]   = k[i]   + 1;
                                        d[i+1] = k[i+1] + 1;
                                        d[i+2] = k[i+2] + 1;
                                        d[i+3] = k[i+3] + 1;
                                    }
                                    for (; i < n; i++)         /* kalan */
                                        d[i] = k[i] + 1;
```

Kalan döngüsü şart: $n$, $k$'nin katı olmak zorunda değil.

Kazanç nereden gelmeli? Eleman başına düşen **döngü yönetimi** (sayaç artırma, karşılaştırma, dal) azalıyor. Kaç işe yaradığı ise Ders 11.2'deki iki sınıra bağlı.

---

## 1. Yaramadığı yer: tek birikimci

```c
/* Tek birikimci: acmak gecikme sinirini degistirmez */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
NO long t1(const long *a, long n) { long s = 0; 
    #pragma clang loop unroll(disable)
    for (long i = 0; i < n; i++) s += a[i]; return s; }
NO long t8(const long *a, long n) { long s = 0;
    #pragma clang loop unroll_count(8)
    for (long i = 0; i < n; i++) s += a[i]; return s; }
static long a[8192];
typedef long (*Fn)(const long *, long);
static double sure(Fn f, long n) { double en = 1e9; for (int r = 0; r < 300; r++) { double t0 = simdi(); for (int q = 0; q < 200; q++) { long v = f(a, n); KORU(v); } double t = simdi() - t0; if (t < en) en = t; } return en / 200 * 1e9 * GHZ; }
int main(void) { printf("acilmamis CPE %.2f\n", (sure(t1, 4000) - sure(t1, 2000)) / 2000); printf("8 acilmis CPE %.2f\n", (sure(t8, 4000) - sure(t8, 2000)) / 2000); return 0; }
```

```
$ ./topla
acilmamis CPE 1.07
8 acilmis CPE 0.95
```

Sekiz açılmış sürüm neredeyse aynı. `s += a[i]` her turda aynı birikimciyi kullanıyor: gecikme sınırı eleman başına 1 çevrim (`add`), ve açma bu zinciri kırmıyor. Modern çekirdekte döngü yönetiminin komutları ayrı birimlerde paralel çalışıyor; kritik yolda değiller. (Eski, dar işlemcilerde açma burada da işe yarardı, çünkü orada kapasite darboğazdı.)

---

## 2. Yaradığı yer: birim verimini doldurmak

Kritik yolu olmayan bir döngü: `d[i] = k[i] + 1`. Elemanlar birbirinden bağımsız. Burada altı sürümü karşılaştıralım. Karşılaştırmanın temiz olması için hep vektörleştirmeyi kapatıyoruz (`-fno-vectorize`); aksi takdirde derleyici NEON'a çevirirdi (Ders 11.6).

```c
/* Dongu acma: elle ve derleyiciye yaptirarak */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
/* 1: acilmamis */
NO void g1(long *d, const long *k, long n) {
    #pragma clang loop unroll(disable)
    for (long i = 0; i < n; i++) d[i] = k[i] + 1;
}
/* 2: elle 4 acma, kalan dongusuyle */
NO void g4(long *d, const long *k, long n) {
    long i;
    for (i = 0; i + 3 < n; i += 4) {
        d[i] = k[i] + 1; d[i + 1] = k[i + 1] + 1;
        d[i + 2] = k[i + 2] + 1; d[i + 3] = k[i + 3] + 1;
    }
    #pragma clang loop unroll(disable)
    for (; i < n; i++) d[i] = k[i] + 1;
}
/* 3: elle 8 acma */
NO void g8(long *d, const long *k, long n) {
    long i;
    for (i = 0; i + 7 < n; i += 8) {
        d[i] = k[i] + 1; d[i + 1] = k[i + 1] + 1; d[i + 2] = k[i + 2] + 1; d[i + 3] = k[i + 3] + 1;
        d[i + 4] = k[i + 4] + 1; d[i + 5] = k[i + 5] + 1; d[i + 6] = k[i + 6] + 1; d[i + 7] = k[i + 7] + 1;
    }
    #pragma clang loop unroll(disable)
    for (; i < n; i++) d[i] = k[i] + 1;
}
/* 4: derleyiciye sayi soyleyerek */
NO void p4(long *d, const long *k, long n) {
    #pragma clang loop unroll_count(4)
    for (long i = 0; i < n; i++) d[i] = k[i] + 1;
}
NO void p8(long *d, const long *k, long n) {
    #pragma unroll 8
    for (long i = 0; i < n; i++) d[i] = k[i] + 1;
}
/* 5: Duff'in aleti */
NO void duff(long *d, const long *k, long n) {
    if (n <= 0) return;
    long tur = (n + 7) / 8;
    switch (n % 8) {
        case 0: do { *d++ = *k++ + 1;
        case 7:      *d++ = *k++ + 1;
        case 6:      *d++ = *k++ + 1;
        case 5:      *d++ = *k++ + 1;
        case 4:      *d++ = *k++ + 1;
        case 3:      *d++ = *k++ + 1;
        case 2:      *d++ = *k++ + 1;
        case 1:      *d++ = *k++ + 1;
                } while (--tur > 0);
    }
}
typedef void (*Fn)(long *, const long *, long);
static char alan[1 << 20] __attribute__((aligned(4096)));
static double sure(Fn f, long n) {
    long *k = (long *)alan, *d = (long *)(alan + 65536);
    int ic = 200000 / (n + 8) + 1; double en = 1e9;
    for (int r = 0; r < 200; r++) { double t0 = simdi(); for (int q = 0; q < ic; q++) { f(d, k, n); BELLEK(); } double t = simdi() - t0; if (t < en) en = t; }
    return en / ic * 1e9 * GHZ;
}
int main(void) {
    struct { const char *ad; Fn f; } s[] = { { "acilmamis", g1 }, { "elle 4", g4 }, { "elle 8", g8 }, { "pragma 4", p4 }, { "pragma 8", p8 }, { "Duff 8", duff } };
    long kisa[] = { 1, 3, 7, 16 }, uzun[] = { 64, 256, 1024, 4096 };
    printf("cagri basina cevrim:\n%-10s", ""); for (int j = 0; j < 4; j++) printf(" n=%-5ld", kisa[j]); printf("\n");
    for (int i = 0; i < 6; i++) { printf("%-10s", s[i].ad); for (int j = 0; j < 4; j++) printf(" %7.1f", sure(s[i].f, kisa[j])); printf("\n"); }
    printf("eleman basina cevrim:\n%-10s", ""); for (int j = 0; j < 4; j++) printf(" n=%-5ld", uzun[j]); printf("\n");
    for (int i = 0; i < 6; i++) { printf("%-10s", s[i].ad); for (int j = 0; j < 4; j++) printf(" %7.2f", sure(s[i].f, uzun[j]) / uzun[j]); printf("\n"); }
    return 0;
}
```

```
$ cc -O2 -fno-vectorize -fno-slp-vectorize acma.c -o acma && ./acma
cagri basina cevrim:
           n=1     n=3     n=7     n=16   
acilmamis      3.0     8.8    13.0    21.0
elle 4         4.0    10.0    10.9    13.0
elle 8         4.0     9.8    14.0    10.0
pragma 4       4.0     9.8    11.0    13.0
pragma 8       4.0     9.8    14.0    10.0
Duff 8         5.0     5.0     7.0    11.9
eleman basina cevrim:
           n=64    n=256   n=1024  n=4096 
acilmamis     1.20    1.36    1.56    1.42
elle 4        0.59    0.61    1.56    0.97
elle 8        0.53    0.51    1.56    0.95
pragma 4      0.59    0.55    1.56    0.93
pragma 8      0.54    0.53    1.56    0.96
Duff 8        0.92    1.12    1.57    1.09
```

Alttaki tabloda `n = 64` ve `n = 256`: açılmamış döngü 1.2–1.36, 8 açılmış **0.51–0.53**. Ders 11.2'deki `str` verimi çevrimde 2: kapasite sınırı 0.5 CPE. 8 açılmış sürüm bu sınıra değiyor. Açılmamış sürüm eleman başına bir **alınan dal** içeriyor ve bu çekirdekte çevrim başına alınan dal sayısı sınırlı; açma, dalları sekizde birine indirip bu sınırı ortadan kaldırıyor.

**Elle ve pragma ile açılan aynı.** Derleyiciye bu işi bırakıp kodu sade tutmak hemen her zaman doğru karar.

Tablonun geri kalanı, mikro benchmark'ların neden tek bir `n` üzerinden yorumlanamayacağını gösteriyor. `n = 1024`'te **bütün sürümler** 1.56'ya çıkıyor, `n = 4096`'da 0.95'e dönüyor. Dizileri birbirinden farklı uzaklıklara koyarak (mod 4096 kaymaları dahil) tekrarladık, sonuç değişmedi. Bu desen yalnızca sayaçlarla ayrılabilecek bir donanım etkisi (önbellek, depo tamponu, önceden getirici); elimizdeki araçlarla nedeni söyleyemiyoruz. Önemli olan, tek bir `n`'den "açma 2.3 kat kazandırır" genellemesi yapmamak.

### Kısa dizilerde bedel

Üstteki tablo çağrı başına toplam çevrim. `n = 3`: açılmamış 8.8, 4 ya da 8 açılmış 9.8–10.0: **eleman sayısı azken açma zararlı**, çünkü önce açılmış döngünün girişi kontrol ediliyor, sonra kalan döngüsüne düşülüyor. `n = 7` için açılmamış 13.0, 8 açılmış 14.0. Dizi kısa, kod daha karmaşık ve dalların tahmini zorlaşıyor.

Karşılaştırma, `n = 16`'da değişiyor: 21.0 açılmamış, 10.0 açılmış: sekiz açılmış sürüm iki tam blok yapıp kalana hiç uğramıyor.

### Duff'ın aleti

Kalan döngüsünü ayrı yazmak yerine `switch`'in içine bir `do` geçirmek: Tom Duff'ın 1983 hilesi, C'nin en ünlü sözdizimi tuhaflığı. `switch (n % 8)` kaç elemanın önce işleneceğine karar verip döngünün **ortasına** atlıyor. Kısa dizilerde en hızlısı (5.0, 5.0, 7.0) çünkü başka döngü yok. Ama uzun dizilerde **daha yavaş** (0.92, 1.12 vs 0.53): derleyici bu kontrol akışını iyileştiremiyor (indirgenemez döngü, Faz 16). Tarihî bir merak olarak bilinmeli, üretimde yazılmamalı.

---

## 3. Derleyiciye yaptırmak

Yukarıdaki iki pragma aynı şey:

```c
#pragma clang loop unroll_count(4)
for (long i = 0; i < n; i++) d[i] = k[i] + 1;

#pragma unroll 8
for (long i = 0; i < n; i++) d[i] = k[i] + 1;
```

`#pragma unroll N`, GCC'de `#pragma GCC unroll N`. Diğer biçimler: `#pragma clang loop unroll(full)`, `unroll(enable)`, `unroll(disable)`. Derleyici kararını sormak için Ders 7.15'teki `-Rpass`:

```
$ cc -O2 -fno-vectorize -Rpass=loop-unroll -c acma.c
acma.c:34:5: remark: unrolled loop by a factor of 4 with run-time trip count [-Rpass=loop-unroll]
acma.c:38:5: remark: unrolled loop by a factor of 8 with run-time trip count [-Rpass=loop-unroll]
acma.c:67:48: remark: completely unrolled loop with 4 iterations [-Rpass=loop-unroll]
acma.c:69:49: remark: completely unrolled loop with 4 iterations [-Rpass=loop-unroll]
```

"With run-time trip count": yineleme sayısı derleme anında belli değil, kalan döngüsü üretilecek. Son iki satır ilginç: `main`'in içindeki `for (j < 4)` döngülerini derleyici **tamamen** açtı: 4 tur bilindiği için dal hiç kalmadı. Üretilen kod da elle yazdığımızla aynı kalıp:

```
p4:
	...
	ldur	x13, [x11, #-16]
	sub	x9, x9, #4
	cmp	x10, x9
	add	x13, x13, #1
	stur	x13, [x12, #-16]
	ldur	x13, [x11, #-8]
	add	x13, x13, #1
	stur	x13, [x12, #-8]
	ldr	x13, [x11]
	add	x13, x13, #1
	str	x13, [x12]
	ldr	x13, [x11, #8]
	add	x11, x11, #32
	add	x13, x13, #1
	str	x13, [x12, #8]
	add	x12, x12, #32
	b.ne	.LBB3_3
```

Dört `ldr/add/str` üçlüsü, tek bir dal ve tek bir sayaç güncellemesi. Tam açma küçük sabit döngülerde her zaman yapılır ve ardından SLP vektörleştirici devreye girebilir:

```c
long dort(const long *a) { long s = 0; for (int i = 0; i < 4; i++) s += a[i] * 3; return s; }
```

```
dort:
	ldp	q1, q0, [x0]
	add	v0.2d, v1.2d, v0.2d
	addp	d0, v0.2d
	fmov	x8, d0
	add	x0, x8, x8, lsl #1
	ret
```

Döngü kayboldu; dört eleman iki vektör olarak yüklendi (Ders 11.6). Çarpma da `lsl #1` ile `add`'e dönüştü.

`-funroll-loops` bayrağı derleyiciye "döngüleri açabilirsin" diyor, ama karar yine maliyet modelinin. `s += a[i]` döngüsü bu bayrakla `-O2` ve `-O3`'te de, `-mcpu=apple-m1` ile de açılmadı (hiçbir `-Rpass` satırı üretilmedi), ki Bölüm 1'deki ölçüm bunu doğruluyor.

Burada vektörleştirmeyi kapattık. Açıkken döngüler doğrudan vektörleştiriliyor ve açma da bunun bir parçası oluyor (`-Rpass=loop-vectorize` çıktısındaki "interleaved count"; Ders 11.15).

---

## 4. Bedeli

```
$ nm -S --size-sort acma | grep -E ' (g1|g4|g8|p4|p8|duff)$'
0000000000000918 0000000000000020 T g1
0000000000000938 0000000000000098 T g4
0000000000000a98 0000000000000098 T p4
0000000000000bf8 00000000000000c4 T duff
00000000000009d0 00000000000000c8 T g8
0000000000000b30 00000000000000c8 T p8
```

Açılmamış 32 bayt, 4 açılmış 152 bayt, 8 açılmış 200 bayt: **6 kat** fark. Bir döngüyü her yerde açmak komut önbelleğini doldurur (Ders 7.24) ve soğuk yollar için boşa gider. Kural olarak:

- **Kısa ve sık çalışan** döngüler için, ve kritik yolu olmayan ya da birden çok birikimci içeren döngülerde mantıklı.
- Gövdesi büyük döngülerde kazanç yok, kod maliyeti büyük.
- Dizi uzunluğu küçükse maliyet kalan döngüsüne gider.
- **Önce ölç**, sonra derleyiciye `#pragma` ile söyle. Elle açılmış kod okunmaz, bakımı zor; aynı optimizasyonu derleyici yapıyor.

Faz 16'da döngü açma geçişini yazarken "tekrar sayısı derleme anında bilinen", "kalan döngüsü" ve "koşulun ters çevrilmesi" tam olarak bu ders olacak.

---

## Alıştırmalar

**1** – `n`'in 8 ile tam bölünmediği bir `g8` çağrısında kalan döngüsü en fazla kaç tur döner? Bu en kötü durumda toplam kaç dal çalışır?

**2** – Kalan döngüsünü ortadan kaldırmak için ne yapabilirsin? Örneğin `n`'i 8'in katına yuvarlamak geçerli mi, hangi durumda?

**3** – `d[i] = k[i] + 1` döngüsünü `-fno-vectorize` olmadan derle ve `-Rpass=loop-vectorize` ile derleyicinin ne dediğine bak. Elle açtığın `g8`'den hızlı mı?

**4** – Yukarıdaki `acma` tablosunda `n = 7` için `elle 8` neden `elle 4`'ten yavaş? Kod yolunu takip et.

**5** – `Duff 8`, `n = 1` için 5.0 çevrim, `acilmamis` 3.0. Duff'ın aleti kısa dizilerde neden avantajlı diye bir iddiayı bu sayılarla değerlendir.

<details>
<summary>Cevaplar</summary>

**1** – En fazla 7 tur. Toplamda `n / 8` açılmış dal, artı en fazla 7 kalan dalı, artı döngü giriş kontrolleri.

**2** – Veri boyutu seçilebiliyorsa (matris, tampon) evet: `n`'i 8'in katı yapmak veya sonuna dolgu eklemek kalan döngüsünü tümüyle kaldırır. Diğer yöntem SIMD'de kullanılan maskeli kalan işleme ya da son bloğu ters yönden üst üste bindirerek çalıştırmak (memcpy'lerin kullandığı hile; işlem idempotent olmalıdır).

**3** – Derleyici döngüyü NEON ile vektörleştirir (`vectorized loop (vectorization width: 2, interleaved count: ...)`). Kapasite bir çevrimde birden çok elemanı işleyecek biçimde değiştiği için `g8`'den daha hızlıdır: açmanın başka bir hali. `interleaved count`, vektörleştirilmiş döngünün **ayrıca** kaç kere açıldığı.

**4** – `n = 7`: `elle 8`'in ana döngüsü hiç çalışmıyor (ilk koşul başarısız), 7 elemanın hepsi kalan döngüsünde teker teker işleniyor: toplam 14.0. `elle 4` ise bir tam blok (4 eleman, verimli) + 3 kalan yapıyor: 10.9.

**5** – 5.0 çevrim, `n = 1` için açılmamış sürümden bile yavaş (ek `switch` ve bölüm hesabı); tabloda `n = 3` ve `7`'de ise Duff önde (5.0 ve 7.0'a karşı 8.8 ve 13.0). Yani "kısa dizilerde avantajlı" 1 hariç tutuyor; asıl sonuç, tek bir `n`'e değil dizi uzunluğu dağılımına bakılması gerektiği. Uzun dizilerde (`n = 256`) açılmış döngülere 2 kat kaybediyor (1.12 vs 0.53).

</details>

---

## Kaynaklar

- Randal Bryant ve David O'Hallaron, *CS:APP* (3. baskı), Bölüm 5.8: döngü açma.
- Tom Duff, net.lang.c iletisi, 1984: Duff's device.
- Clang belgeleri: "Loop Unrolling" ve `#pragma clang loop`.
- LLVM `LoopUnrollPass` kaynak kodu ve "Loop Terminology" belgesi.
- Agner Fog, *Optimizing Software in C++*, Bölüm 7: döngüler.

**Sıradaki ders:** Dalsız programlama ve `cmov`. Faz 5'teki dalsız hilelerin gerçek performans etkisi.
