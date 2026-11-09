---
title: "11.4 Dalsız programlama ve cmov"
description: "Bir dal ıskasının maliyeti: yüzde 50 rastgele veride CPE 1'den 10.3'e, yaklaşık 18 çevrim ceza; cmov ve csel: koşula göre seçim; dalsız kodun sabit 2 CPE'si ve add sxtw'nin 2 çevrim gecikmesi; kırılma noktası; dal tahmincisinin 4 KB'lık diziyi ezberlemesi; Faz 5'teki min hilelerinin ölçümü ve derleyicinin xor hilesini csel'e çevirmesi; __builtin_expect, __builtin_unpredictable; ikili aramada dalsız sürümün 5 kat hızlanması."
---

Ders 5.5'te dalsız hileler yazdık, Ders 7.22'de dal tahminini öğrendik. Bu ders ikisini ölçüyor: bir dal ne kadar pahalı, dalsız kod ne zaman kazanıyor, ve Faz 5'teki hileler bugün hâlâ gerekli mi?

Hatırlatma: işlemci dalın sonucunu beklemeden tahmin ediyor. Tahmin doğruysa bedeli sıfıra yakın; yanlışsa o noktadan sonra yürütülen her şey atılıyor ve boru hattı yeniden doluyor.

---

## 1. Dal ıskasının maliyeti

Görev: bir dizideki eşik altındaki elemanları toplamak. Üç sürüm:

```c
/* Dal tahmini ve dalsiz kod: esigin altindaki elemanlari topla */
#include "olcum.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
NO long dalli(const int *a, long n, int t) {
    long s = 0;
    for (long i = 0; i < n; i++) if (a[i] < t) { s += a[i]; __asm__ volatile(""); }   /* asm: if donusturmeyi engeller */
    return s;
}
NO long dalsiz(const int *a, long n, int t) {
    long s = 0;
    for (long i = 0; i < n; i++) s += a[i] < t ? a[i] : 0;
    return s;
}
NO long maskeli(const int *a, long n, int t) {
    long s = 0;
    for (long i = 0; i < n; i++) s += a[i] & -(long)(a[i] < t);
    return s;
}
enum { N = 1 << 20 };
static int *a; static uint32_t rs = 2463534242u;
static uint32_t rnd(void) { rs ^= rs << 13; rs ^= rs >> 17; rs ^= rs << 5; return rs; }
static int kars(const void *x, const void *y) { return (*(const int *)x > *(const int *)y) - (*(const int *)x < *(const int *)y); }
typedef long (*Fn)(const int *, long, int);
static double cpe(Fn f, long n, int t) {
    double en = 1e9;
    for (int r = 0; r < 11; r++) { double t0 = simdi(); long v = f(a, n, t); KORU(v); double s = simdi() - t0; if (s < en) en = s; }
    return en * 1e9 * GHZ / n;
}
static void satir(const char *ad, int t) { printf("%-18s %8.2f %8.2f %8.2f\n", ad, cpe(dalli, N, t), cpe(dalsiz, N, t), cpe(maskeli, N, t)); }
int main(void) {
    a = malloc(N * sizeof *a);
    for (long i = 0; i < N; i++) a[i] = rnd() % 1000;
    printf("%-18s %8s %8s %8s\n", "CPE", "dalli", "dalsiz", "maskeli");
    satir("alinan %0", 0); satir("alinan %1", 10); satir("alinan %10", 100); satir("alinan %30", 300); satir("alinan %50", 500); satir("alinan %90", 900); satir("alinan %100", 1000);
    /* ayni kucuk diziyi tekrar tekrar calistirmak: tahminci ezberler */
    printf("\nkucuk dizi, %%50, tekrar tekrar:\n");
    for (long n = 256; n <= (1 << 20); n <<= 2) {
        int t = 500; double en = 1e9;
        int ic = (int)((1 << 24) / n);
        for (int r = 0; r < 5; r++) { double t0 = simdi(); for (int q = 0; q < ic; q++) { long v = dalli(a, n, t); KORU(v); } double s = simdi() - t0; if (s < en) en = s; }
        printf("  n=%8ld: %6.2f CPE\n", n, en * 1e9 * GHZ / (ic * n));
    }
    qsort(a, N, sizeof *a, kars);
    printf("\nsirali dizi, %%50:  dalli %.2f, dalsiz %.2f\n", cpe(dalli, N, 500), cpe(dalsiz, N, 500));
    return 0;
}
```

`dalli`'deki boş `__asm__ volatile("")`, derleyicinin bu `if`'i otomatik olarak dalsıza çevirmesini engelliyor; aksi takdirde karşılaştırma yapamazdık. Dizi bir milyon elemanlı ve rastgele; önbelleğe sığıyor ama dal tahminci için büyük.

```
$ cc -O2 -fno-vectorize -fno-slp-vectorize dal.c -o dal && ./dal
CPE                   dalli   dalsiz  maskeli
alinan %0              1.02     2.01     2.01
alinan %1              1.35     2.01     2.01
alinan %10             3.15     2.01     2.01
alinan %30             6.79     2.01     2.01
alinan %50            10.29     2.01     2.01
alinan %90             3.06     2.01     2.01
alinan %100            1.04     2.01     2.01
```

Dal sütunu dramatik: öngörülebilir veride 1 çevrim, tamamen rastgele veride 10.3 çevrim. `%50`'de dalların yarısı yanlış tahmin ediliyorsa, eleman başına ek maliyet $0.5 \times \text{ceza}$:

$$
\text{ceza} \approx \frac{10.29 - 1.03}{0.5} \approx 18.5 \text{ çevrim}.
$$

Sütunun şekli de bir tablo okuma alıştırması: `%10` ile `%90` birbirine çok yakın (3.15 ve 3.06). Doğal: tahminci "hep alınır" ya da "hiç alınmaz" diyor ve her iki durumda da hata oranı %10.

Dalsız sütun ise **veriden tamamen bağımsız**: 2.01. Süresi veriye bağlı olmayan kod, Ders 5.5'te bahsettiğimiz öngörülebilirliğin ötesinde kriptografik kod için de kritik: bir dal, gizli verinin zamanlama yoluyla sızmasına neden olabilir.

### Neden dalsız 2 CPE?

```
dalsiz:
	...
	ldr	w9, [x0], #4
	cmp	w9, w2
	csel	w9, w9, wzr, lt
	subs	x1, x1, #1
	add	x8, x8, w9, sxtw
	b.ne	.LBB1_2
```

Birikimci zinciri `add x8, x8, w9, sxtw`. Ders 11.2'deki tablodaki satır burada ortaya çıkıyor: uzatmalı `add` **2 çevrim**. Tek birikimci, gecikme 2: CPE 2. `int` dizinin `long` toplama aktarılması bu `sxtw`'yi gerektiriyor. Aynı testi `long` dizilerle yaparsak:

```
long dizi
alinan %0              1.03     1.52     1.52
alinan %50            10.31     1.52     1.52
alinan %100            1.05     1.52     1.52
```

1.52'ye düştü. Dalsızlık bedava değil ama çok ucuz; bu fark çoğu programda önemsiz, ancak yine de `1.03` öngörülebilir dal hâlâ en hızlısı.

**Kırılma noktası**: `int` için `%1` ile `%10` arası. Yani hata oranı yüzde birkaçı geçtiğinde dalsız kazanır.

---

## 2. cmov ve csel

Dalsız kodun donanım temeli **koşullu taşıma**: bayraklara bakıp iki değerden birini seçen tek komut. x86-64'te `cmovcc`, arm64'te `csel` (ve türevleri `csinc`, `csneg`, `csinv`).

```c
int m_uclu(int x, int y) { return x < y ? x : y; }
int m_hile(int x, int y) { return y ^ ((x ^ y) & -(x < y)); }
int m_cikar(int x, int y) { int f = x - y; return y + (f & (f >> 31)); }
long say(long s, int a, int t) { if (a < t) s += a; return s; }
int ongorulemez(int a, int b, int c) { if (__builtin_unpredictable(a < b)) return c + 1; return c * 3; }
int beklenen(int a, int b, int c) { if (__builtin_expect(a < b, 0)) return c + 1; return c * 3; }
```

```
$ cc -O2 -S minasm.c -o -                        # arm64
m_uclu:
	cmp	w0, w1
	csel	w0, w0, w1, lt
	ret
m_hile:
	cmp	w0, w1
	csel	w0, w0, w1, lt
	ret
m_cikar:
	sub	w8, w0, w1
	and	w8, w8, w8, asr #31
	add	w0, w8, w1
	ret
say:
	cmp	w1, w2
	csel	w8, w1, wzr, lt
	add	x0, x0, w8, sxtw
	ret
$ cc --target=x86_64-linux-gnu -O2 -S minasm.c -o -        # x86-64
m_uclu:
	movl	%esi, %eax
	cmpl	%esi, %edi
	cmovll	%edi, %eax
	retq
m_hile:
	movl	%esi, %eax
	cmpl	%esi, %edi
	cmovll	%edi, %eax
	retq
```

Dikkat edilecek nokta `m_hile`: Ders 5.5'teki `y ^ ((x ^ y) & -(x < y))`. Derleyici bunu **tanıdı** ve `?:` ile aynı koda çevirdi. Faz 5'teki bit hilesi burada anlaşılır kodla aynı hızda ve aslında aynı makine kodu.

`m_cikar` farklı kalıyor: `x - y` taşarsa yanlış sonuç veriyor, bu yüzden derleyici onu `min`'e eşdeğer sayamıyor. Hile sadece hızlı olmak için değil, tanımlı bir aralıkta olmak için de düşünülmeli.

### Derleyiciye ipucu

```c
int ongorulemez(int a, int b, int c) { if (__builtin_unpredictable(a < b)) return c + 1; return c * 3; }
int beklenen(int a, int b, int c) { if (__builtin_expect(a < b, 0)) return c + 1; return c * 3; }
```

`-O2` ile `arm64`'te ikisi aynı: `csinc`. x86-64'te ise farklı:

```
ongorulemez:                                 beklenen:
	leal	1(%rdx), %ecx                	movl	%edx, %eax
	cmpl	%esi, %edi                   	cmpl	%esi, %edi
	leal	(%rdx,%rdx,2), %eax          	jl	.LBB5_1
	cmovll	%ecx, %eax                   	leal	(%rax,%rax,2), %eax
	retq                                 	retq
```

`__builtin_unpredictable` "iki yöne eşit, dalsız yap"; `__builtin_expect(x, 0)` "neredeyse hiç olmaz, dal kullanıp sık yolu düz bırak": beklenmeyen `incl` kodu ayrı bir yere itildi. Veriyi tanıyorsan bu ipuçları derleyiciye hakikat sağlar (C++'taki `[[likely]]` de aynı mekanizma; Faz 13). Ama **yanlış ipucu zararlıdır**.

---

## 3. Dal tahmincisi ezberler

Yukarıdaki deneyin çok önemli bir ön koşulu vardı: dizi bir milyon elemanlı. Aynı küçük diziyi tekrar tekrar çalıştırsak:

```
kucuk dizi, %50, tekrar tekrar:
  n=     256:   2.13 CPE
  n=    1024:   2.05 CPE
  n=    4096:   2.86 CPE
  n=   16384:   8.18 CPE
  n=   65536:   9.94 CPE
  n=  262144:  10.23 CPE
  n= 1048576:  10.34 CPE
```

`n = 256`'da **%50 rastgele** veri, neredeyse hiçbir ıska vermiyor (2.13). Tahminci geçmişe dayalı olduğu için (Ders 7.22) dal sonuçlarının tekrar eden dizisini tümüyle ezberliyor. Ancak dizi 4–16 bin elemanı geçince yetişemiyor. Bu, mikro benchmark'ların en sinsi hatası: küçük bir rastgele diziyi 1000 kere ölçünce "dal maliyeti yok" sonucu çıkar, oysa gerçek veri her seferinde farklıdır. Ya çok büyük bir dizi kullan ya da her turda veriyi değiştir.

Sıralı dizi de tahmincinin en sevdiği şey: `dalli` 1.03 CPE (bir kere değişen dal). Ünlü "sıralı diziyi işlemek neden daha hızlı" sorusunun cevabı bu.

```
sirali dizi, %50:  dalli 1.03, dalsiz 2.00
```

---

## 4. Faz 5'teki hileler: kazandıran hangisi?

```c
/* Faz 5'teki dalsiz min hilesi: gercekten kazandiriyor mu? */
#include "olcum.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
NO int m_dal(int x, int y) { if (x < y) { __asm__ volatile(""); return x; } return y; }
NO int m_uclu(int x, int y) { return x < y ? x : y; }
NO int m_hile(int x, int y) { return y ^ ((x ^ y) & -(x < y)); }
NO int m_cikar(int x, int y) { int f = x - y; return y + (f & (f >> 31)); }
enum { N = 1 << 16 };
static int a[N], b[N];
typedef int (*Fn)(int, int);
static double olc(Fn f) { double en = 1e9; for (int r = 0; r < 40; r++) { double t0 = simdi(); long s = 0; for (long i = 0; i < N; i++) s += f(a[i], b[i]); KORU(s); double t = simdi() - t0; if (t < en) en = t; } return en * 1e9 * GHZ / N; }
int main(void) {
    uint32_t r = 7;
    for (int i = 0; i < N; i++) { r = r * 2654435761u + 1; a[i] = (int)((r >> 8) % 100000); r = r * 2654435761u + 1; b[i] = (int)((r >> 8) % 100000); }
    printf("rastgele x, y   dal %.2f, ?: %.2f, xor hilesi %.2f, cikarma hilesi %.2f cevrim/cagri\n", olc(m_dal), olc(m_uclu), olc(m_hile), olc(m_cikar));
    for (int i = 0; i < N; i++) { a[i] = i; b[i] = i + 5; }
    printf("hep x < y       dal %.2f, ?: %.2f, xor hilesi %.2f, cikarma hilesi %.2f cevrim/cagri\n", olc(m_dal), olc(m_uclu), olc(m_hile), olc(m_cikar));
    return 0;
}
```

```
$ ./min
rastgele x, y   dal 14.20, ?: 3.00, xor hilesi 3.00, cikarma hilesi 3.00 cevrim/cagri
hep x < y       dal 3.00, ?: 3.00, xor hilesi 3.00, cikarma hilesi 3.00 cevrim/cagri
```

Sonuçlar kesin:

- Rastgele veride **gerçek bir dal** 14.2 çevrim, her üç dalsız sürüm 3.00.
- Öngörülebilir veride hepsi 3.00: fonksiyon çağrısının maliyeti burada baskın.
- `?:` yazmak yeterli: derleyici en iyi kodu üretiyor. **Bugün `min`'i elle bit hilesiyle yazmak için bir sebep yok**, okunabilirlik kaybı karşılığında hiçbir şey kazanmıyorsun.

Faz 5'teki hilelerin yararı artık başka yerde: derleyicinin üretebileceğini anlamak, SIMD'de (`pcmpgt` ve maskeler aynı mantık; Ders 11.11) ve sabit zamanlı kodda (derleyicinin dal geri getirmemesi için `volatile`/özel araçlarla).

---

## 5. Daha büyük bir kazanç: ikili arama

Dalsız kod, algoritmanın dallarını kaldırdığında büyük fark yaratıyor. İkili aramada her karşılaştırma tahmin edilemez (%50 alınıyor):

```c
/* Ikili arama: dalli ve dalsiz, dizi buyudukce */
#include "olcum.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#define GHZ 3.5
#define NO __attribute__((noinline))
NO long dalli(const int *a, long n, int x) {
    long lo = 0, hi = n;
    while (lo < hi) { long m = lo + (hi - lo) / 2; if (a[m] < x) { lo = m + 1; __asm__ volatile(""); } else hi = m; }
    return lo;
}
NO long dalsiz(const int *a, long n, int x) {
    const int *b = a;
    while (n > 1) { long y = n / 2; b = b[y - 1] < x ? b + y : b; n -= y; }
    return (b - a) + (*b < x);
}
int main(void) {
    uint32_t rs = 88172645;
    int *q = malloc(1 << 18 << 2);
    printf("%12s %10s %10s  cevrim/arama\n", "boyut", "dalli", "dalsiz");
    for (long n = 1 << 8; n <= 1L << 26; n <<= 3) {
        int *a = malloc(n * sizeof *a);
        for (long i = 0; i < n; i++) a[i] = (int)(i * 2 + 1);
        for (int i = 0; i < 1 << 18; i++) { rs ^= rs << 13; rs ^= rs >> 17; rs ^= rs << 5; q[i] = (int)(rs % (uint32_t)(2 * n)); }
        double e1 = 1e9, e2 = 1e9;
        for (int r = 0; r < 5; r++) {
            double t0 = simdi(); long s = 0; for (int i = 0; i < 1 << 18; i++) s += dalli(a, n, q[i]); KORU(s); double t = simdi() - t0; if (t < e1) e1 = t;
            t0 = simdi(); s = 0; for (int i = 0; i < 1 << 18; i++) s += dalsiz(a, n, q[i]); KORU(s); t = simdi() - t0; if (t < e2) e2 = t;
        }
        printf("%12ld %10.1f %10.1f\n", n, e1 * 1e9 * GHZ / (1 << 18), e2 * 1e9 * GHZ / (1 << 18));
        free(a);
    }
    return 0;
}
```

```
$ ./ikili
       boyut      dalli     dalsiz  cevrim/arama
         256      118.2       22.1
        2048      167.6       33.6
       16384      217.6       46.7
      131072      336.8      218.0
     1048576      427.5      359.0
     8388608      943.1      878.5
    67108864     2463.1     2158.3
```

Küçük dizilerde **5 kat** fark. Çünkü `dalli` arama başına $\log_2 n$ tane %50'lik dal yapıyor, her ıska ~18 çevrim. Ama dizi büyüdükçe fark kapanıyor: 131 072 elemanda 1.5 kat, 67 milyon elemanda 1.14 kat. Sebep Ders 7.24: büyük dizide süreyi önbellek ıskaları belirliyor (2000 çevrim!) ve ıskaları iki sürüm eşit sayıda yapıyor.

`csel`'in bir bedeli var: bir sonraki yüklemenin adresi önceki karşılaştırmanın sonucuna bağlı, işlemci spekülasyon yapamıyor. Dallı sürüm ise tahmin ettiği yönde yüklemeyi önden başlatıyor. Bazı işlemcilerde ve boyutlarda bu sayede dallı sürümün öne geçtiği bildirilmiştir; bu çekirdekte ölçtüğümüz bütün boyutlarda dalsız önde kaldı. Karar kendi çekirdeğinde ölçülerek verilmeli.

---

## Alıştırmalar

**1** – Ders 7.22'deki dal tahmincisi 2 bitlik sayaç olsaydı, `%50` rastgele verilerde beklenen ıska oranı nedir? `dal.c`'nin çıktısı gerçek tahmincinin bundan iyi olup olmadığını söyler mi?

**2** – `dal.c`'de `int` dizi yerine `long` dizi kullanan `dalli` ile `dalsiz`'in kırılma noktası (hangi yüzdede eşit)? `alinan %1` ile `%10` arasında birkaç değer ekleyip ölç.

**3** – Bir döngüde koşul `if (x > 0) yavas_fonksiyon(x);`. Bu kod dalsız yazılabilir mi? `csel` hangi koşulda uygulanamaz?

**4** – `abs(x)`'i Ders 5.5'teki `(x ^ m) - m` ile ve `x < 0 ? -x : x` ile yazıp `-S` çıktılarını karşılaştır. `INT_MIN` için hangisi ne yapar?

**5** – Ders 8.5'teki halka kuyruk `(i + 1) % n` yazıyor. Bunu `i + 1 == n ? 0 : i + 1` ile ve `(i + 1) & (n - 1)` ile karşılaştır. Hangisi hangi koşulda en iyisi? Ders 11.2'deki `sdiv` gecikmesi ne der?

<details>
<summary>Cevaplar</summary>

**1** – Rastgele bağımsız veride her tahminci için en iyi beklenti %50 ıskadır: bilgi yok. 2 bitlik sayaç da %50 civarında kalır. Tablodaki büyük dizi (10.3 CPE) buna tam uyuyor: tahminci yetişemiyor. Küçük tekrar eden dizide ise tahmin %50'den çok iyi (2.13 CPE): bu, gerçek tahmincinin 2 bitlik sayaçtan çok ötesini yapabildiğini kanıtlıyor; 2 bitlik sayaç tekrarı ezberleyemezdi.

**2** – `long` dizide `dalsiz` 1.52: `dalli`'nin $1.03 + p \times 18.5 = 1.52$ olduğu $p \approx \%2.7$. Yani hata oranı %3'ü geçince dalsız kazanır; ölçümle bu civarda doğrulanabilir. `int` için bu sınır `2.01`'e göre yaklaşık %5.

**3** – Yazılamaz. `csel` iki **değer** arasında seçim yapar; ikisi de önceden hesaplanmış olmalıdır. Yan etkili bir çağrı (ya da bellek okuması: `p ? *p : 0`, NULL okuyabilir) koşula bağlı yürütülmelidir. Pahalı bir hesap iki yolda da yapılırsa kazanç olmaz.

**4** – İkisi çoğu zaman aynı koda (`cneg`/`cmov`) iner: `cmp w0, #0` ve `cneg w0, w0, mi`. `INT_MIN` için ikisi de taşar: `x < 0 ? -x : x` tanımsız davranış (`-INT_MIN`, Ders 3.8), `(x ^ m) - m` de `x - (-1)` gibi aritmetikte aynı taşmayı yaşar. Tanımlı sonuç için `unsigned` hesap yap.

**5** – `% n` bölme: 64 bit `sdiv` 7 çevrim, ve her turda. Karşılaştırmalı `?:`: `csel` ile 1 çevrim, her zaman çalışır, `n` için sınır yok. `& (n - 1)`: 1 çevrim, ama `n` 2'nin kuvveti olmak zorunda (Ders 5.7). Sabit `n` varsa derleyici `%`'yi ucuzlatır (Ders 5.14), o zaman fark azalır. En iyisi: `n` 2'nin kuvvetiyse `&`, değilse `?:`.

</details>

---

## Kaynaklar

- Randal Bryant ve David O'Hallaron, *CS:APP* (3. baskı), Bölüm 5.11–5.12: dal cezası, dalsız stil.
- Henry Warren, *Hacker's Delight* (2. baskı), Bölüm 2: dalsız kod.
- Daniel Lemire, branchless programlama yazıları (lemire.me/blog).
- Paul-Virak Khuong ve Pat Morin, "Array Layouts for Comparison-Based Searching", *JEA*, 2017: dallı ve dalsız ikili arama.
- GCC ve Clang belgeleri: `__builtin_expect`, `__builtin_unpredictable`.

**Sıradaki ders:** Aliasing ve `restrict`. Derleyicinin neden optimizasyon yapamadığı, `restrict` ile assembly farkı, strict aliasing kuralı.
