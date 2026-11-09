---
title: "11.1 Performansı ölçmek"
description: "Mikro benchmark'ın tuzakları: derleyicinin işi silmesi (bir milyar tur, 0.000 ns), volatile'ın ölçülen şeyi değiştirmesi, 41.7 ns'lik saat tanesi, ısınma, sağa çarpık dağılım; bağımlı add zinciriyle frekansı 3.5 GHz olarak kalibre etmek ve macOS'un gerçek çevrim sayaçlarıyla doğrulamak; perf donanım sayaçları, IPC ve sanal makinedeki sınır; CPE ve doğru uydurma; CS:APP'in hızlandırılmış psum2'sinin burada 2.5 kat yavaş çıkması ve store-to-load iletimi."
---

Faz 7'de işlemcinin içini (boru hattı, dal tahmini, sırasız yürütme, önbellek), Ders 9.1 ve 10.18'de ölçmenin temellerini gördük. Faz 11 bunları birleştiriyor: bir kod parçasını **donanımın sınırına kadar** hızlandırmak. Önce elle (bu fazın ilk beş dersi: gecikme, açma, dalsız kod, aliasing), sonra SIMD ile, sonra da derleyicinin aynı işi kendisinin yapıp yapamadığına bakarak. Faz 16'daki optimizasyon geçişleri bu fazda elle yaptıklarımızın otomatik hali olacak.

Bu derste ölçüm yöntemini sağlamlaştırıyoruz, çünkü bir sonraki derslerdeki farklar **çevrim kesirleri** büyüklüğünde. Ders 10.18'de `strlen` hatası 900 kat fark veriyordu ve kaba bir ölçüm yetiyordu; 1.0 ile 0.5 çevrimi ayırmak başka bir iş.

Çıktılar Faz 10'daki ortamda alındı: arm64 Linux (Ubuntu 24.04, clang 18), Apple M2 üzerinde sanal makine. Mimariye bağlı yerlerde x86-64 karşılığını da veriyoruz.

---

## 1. Süreden çevrime

Süre makineye bağlı. **Çevrim** (cycle) ise işlemcinin kendi saat vuruşu, ve "bu döngü eleman başına 1 çevrim sürüyor" cümlesi mikro mimari hakkında konuşmayı sağlıyor. Sorun, çevrimi okumanın her yerde kolay olmaması:

| Ortam | Ne okunabiliyor | Çekince |
| --- | --- | --- |
| x86-64, `rdtsc` | Sabit hızlı bir sayaç | Gerçek çekirdek çevrimi **değil**: frekans değişse de sabit hızla sayar |
| arm64, `cntvct_el0` | 24 MHz sayaç (Apple) | Çok kaba: bir tıkı 41.7 ns |
| `perf` sayaçları | Gerçek çevrim | Sanal makinede çoğu zaman yok (Bölüm 3) |

Yedek yöntem: **frekansı biz ölçelim.** Birbirine bağımlı `add` komutlarından oluşan bir zincir, her çekirdekte çevrim başına tam olarak bir `add` ilerler (bir komutun sonucu bir sonrakinin girdisi; Ders 7.23). Zincirin süresi bize çevrim süresini veriyor.

```c
/* olcum.h: bu fazin kucuk olcum kutuphanesi */
#ifndef OLCUM_H
#define OLCUM_H
#include <time.h>
static inline double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
/* derleyiciye "x kullaniliyor" der; komut uretmez */
#define KORU(x)  __asm__ volatile("" : : "r"(x) : "memory")
/* derleyiciye "bellek degisti" der; komut uretmez */
#define BELLEK() __asm__ volatile("" : : : "memory")
#endif
```

```c
/* Frekansi olcmek: birbirine bagimli add zinciri cevrim basina 1 ilerler */
#include "olcum.h"
#include <stdio.h>
#include <stdlib.h>
#if defined(__aarch64__)
#define ZINCIR(n) __asm__ volatile("mov x9, %0\n1:\n.rept 200\nadd x10, x10, #1\n.endr\nsubs x9, x9, #1\nb.ne 1b" : : "r"(n) : "x9", "x10", "cc")
#elif defined(__x86_64__)
#define ZINCIR(n) __asm__ volatile("mov %0, %%r9\n1:\n.rept 200\nadd $1, %%r10\n.endr\nsub $1, %%r9\njnz 1b" : : "r"(n) : "r9", "r10", "cc")
#endif
static int kars(const void *a, const void *b) { double x = *(const double *)a, y = *(const double *)b; return (x > y) - (x < y); }
int main(void) {
    enum { R = 400, T = 5000 };
    double o[R];
    for (int i = 0; i < R; i++) { double t0 = simdi(); ZINCIR((long)T); o[i] = (simdi() - t0) / (T * 200.0) * 1e9; }
    qsort(o, R, sizeof *o, kars);
    printf("add basina ns: en iyi %.4f, ortanca %.4f, en kotu %.4f\n", o[0], o[R / 2], o[R - 1]);
    printf("en iyi sureye gore frekans: %.2f GHz\n", 1.0 / o[0]);
    return 0;
}
```

```
$ cc -O2 frekans.c -o frekans && ./frekans
add basina ns: en iyi 0.2853, ortanca 0.3011, en kotu 1.3768
en iyi sureye gore frekans: 3.51 GHz
```

Bir `add` en iyi durumda 0.2853 ns: **3.5 GHz**, M2'nin performans çekirdeğinin bilinen frekansı. Ortanca ile en kötü değer arasındaki fark, sanal makinedeki sürecin bazen başka işlerle kesildiğini ya da verimlilik çekirdeğine düştüğünü gösteriyor. Bu derslerde **en iyi süreyi** alıp `çevrim = ns × 3.5` çeviriyoruz.

Bu varsayımı doğrulayabiliyoruz. macOS'ta bir süreç kendi gerçek çevrim ve komut sayılarını `proc_pid_rusage` ile okuyabiliyor (sanal makineye gerek yok, ayrıcalık da gerekmiyor):

```c
/* macOS: proc_pid_rusage ile gercek cevrim ve komut sayilari */
#include "olcum.h"
#include <libproc.h>
#include <stdio.h>
#include <unistd.h>
#define ZINCIR(n) __asm__ volatile("mov x9, %0\n1:\n.rept 200\nadd x10, x10, #1\n.endr\nsubs x9, x9, #1\nb.ne 1b" : : "r"(n) : "x9", "x10", "cc")
#define GENIS(n) __asm__ volatile("mov x9, %0\n1:\n.rept 200\nadd x10, x10, #1\nadd x11, x11, #1\nadd x12, x12, #1\nadd x13, x13, #1\n.endr\nsubs x9, x9, #1\nb.ne 1b" : : "r"(n) : "x9", "x10", "x11", "x12", "x13", "cc")
typedef struct { unsigned long long c, i; double t; } An;
static An al(void) { struct rusage_info_v4 r; proc_pid_rusage(getpid(), RUSAGE_INFO_V4, (rusage_info_t *)&r); An a = { r.ri_cycles, r.ri_instructions, simdi() }; return a; }
static void rapor(const char *ad, An a, An b, double ops) {
    double c = (double)(b.c - a.c), i = (double)(b.i - a.i), t = b.t - a.t;
    printf("%-14s cevrim %12.0f, komut %12.0f, IPC %5.2f, op basina %.3f cevrim, %.2f GHz\n", ad, c, i, i / c, c / ops, c / t / 1e9);
}
int main(void) {
    long n = 2000000;
    for (int r = 0; r < 3; r++) {
        An a = al(); ZINCIR(n); An b = al(); GENIS(n); An d = al();
        rapor("bagimli add", a, b, n * 200.0);
        rapor("4 ayri zincir", b, d, n * 800.0);
    }
    return 0;
}
```

```
$ cc -O2 mac_sayac.c -o mac_sayac && ./mac_sayac       # macOS'ta dogrudan
bagimli add    cevrim    400767053, komut    404396544, IPC  1.01, op basina 1.002 cevrim, 2.99 GHz
4 ayri zincir  cevrim    497038565, komut   1604239356, IPC  3.23, op basina 0.311 cevrim, 3.48 GHz
bagimli add    cevrim    400229785, komut    404183933, IPC  1.01, op basina 1.001 cevrim, 3.47 GHz
4 ayri zincir  cevrim    497100143, komut   1605390872, IPC  3.23, op basina 0.311 cevrim, 3.38 GHz
bagimli add    cevrim    400225792, komut    404175405, IPC  1.01, op basina 1.001 cevrim, 3.47 GHz
4 ayri zincir  cevrim    497214606, komut   1604217109, IPC  3.23, op basina 0.311 cevrim, 3.48 GHz
```

Bağımlı zincirde `add` başına **1.001 çevrim**: varsayım doğrulandı. Aynı sayıda `add`'i dört ayrı register'a dağıtınca IPC 1'den 3.23'e çıkıyor: Ders 7.23'teki sırasız yürütmenin canlı görüntüsü ve bir sonraki dersin konusu.

---

## 2. Mikro benchmark tuzakları

### Tuzak 1: derleyici işi siliyor

```c
/* Mikro benchmark tuzagi: derleyici olculen isi silebilir */
#include "olcum.h"
#include <stdio.h>
enum { N = 1000000000 };
__attribute__((noinline)) static double a_kullanilmiyor(void) {
    double t0 = simdi(); long s = 0;
    for (long i = 0; i < N; i++) s += i;
    return simdi() - t0;
}
__attribute__((noinline)) static double b_kapali_form(long *cikti) {
    double t0 = simdi(); long s = 0;
    for (long i = 0; i < N; i++) s += i;
    *cikti = s;
    return simdi() - t0;
}
__attribute__((noinline)) static double c_volatile(void) {
    double t0 = simdi(); volatile long s = 0;
    for (long i = 0; i < N; i++) s += i;
    return simdi() - t0;
}
__attribute__((noinline)) static double d_koru(void) {
    double t0 = simdi(); long s = 0;
    for (long i = 0; i < N; i++) { s += i; KORU(s); }
    return simdi() - t0;
}
int main(void) {
    long c;
    double a = a_kullanilmiyor(), b = b_kapali_form(&c), v = c_volatile(), d = d_koru();
    printf("sonuc kullanilmiyor : %8.3f ns/tur\n", a / N * 1e9);
    printf("sonuc yaziliyor     : %8.3f ns/tur (s = %ld)\n", b / N * 1e9, c);
    printf("volatile degisken   : %8.3f ns/tur\n", v / N * 1e9);
    printf("KORU ile            : %8.3f ns/tur\n", d / N * 1e9);
    return 0;
}
```

```
$ cc -O2 -fno-vectorize tuzak.c -o tuzak && ./tuzak
sonuc kullanilmiyor :    0.000 ns/tur
sonuc yaziliyor     :    0.000 ns/tur (s = 499999999500000000)
volatile degisken   :    1.492 ns/tur
KORU ile            :    0.288 ns/tur
```

Bir milyar tur, sıfır süre. Birinci fonksiyonda `s` kullanılmıyor: döngü **ölü kod** (Ders 7.15). İkincisinde kullanılıyor ama derleyici yine döngü yazmıyor, $\sum i$'nin **kapalı formülüne** çeviriyor (Ders 8.6'da gördüğümüz dönüşüm):

```
$ cc -O2 -S kucuk.c -o -        # long topla(long n) { ...s += i... }
topla:
	subs	x8, x0, #1
	b.lt	.LBB0_2
	sub	x9, x0, #2
	mul	x10, x8, x9
	umulh	x9, x8, x9
	extr	x9, x9, x10, #1
	add	x0, x8, x9
	ret
```

Üçüncüsü başka bir hata. `volatile` işi korudu ama **ölçülen şeyi değiştirdi**: her turda bellekten okuma ve belleğe yazma var (1.49 ns). Kimse gerçek kodunda sayaca `volatile` yazmaz; bu değer döngünün değil, belleğe gidip gelmenin maliyeti.

Doğrusu dördüncüsü. `olcum.h`'deki `KORU(s)` boş bir satır içi assembly: derleyiciye "`s` register'da olmalı, onu biri okuyor" diyor ama **hiç komut üretmiyor**. 0.288 ns = 1 çevrim, beklediğimiz değer. `BELLEK()` de aynı şekilde "bellek değişmiş olabilir" diyor. (Google Benchmark'ın `DoNotOptimize` ve `ClobberMemory` fonksiyonları tam olarak bunlar.)

:::tip[Kural]
0.000 ya da inanılmayacak kadar iyi bir sonuç görürsen önce assembly'ye bak (`-S`). Ölçülen şey orada mı?
:::

### Tuzak 2: saat tanesi

Ders 10.18'de `CLOCK_MONOTONIC`'in görülen en küçük adımı 41 ns çıkmıştı. Bu sanal makinede saatin altındaki sayaç 24 MHz, yani bir tık 41.67 ns. Kısa işleri tek tek ölçünce sonuç bu tanelere yapışıyor:

```c
/* Saat tanesi: cok kisa isler olculemez */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
static long a[4096];
__attribute__((noinline)) static long topla(const long *p, long n) { long s = 0; for (long i = 0; i < n; i++) { s += p[i]; KORU(s); } return s; }
static double olc(long n, int ic) {
    double en = 1e9;
    for (int r = 0; r < 2000; r++) { double t0 = simdi(); for (int q = 0; q < ic; q++) { long v = topla(a, n); KORU(v); } double t = simdi() - t0; if (t < en) en = t; }
    return en / ic;
}
int main(void) {
    for (int ic = 1; ic <= 256; ic *= 16) {
        printf("ic tekrar %3d: ", ic);
        for (long n = 1000; n <= 1004; n++) printf("%8.1f", olc(n, ic) * 1e9);
        printf("   ns (n=1000..1004)\n");
    }
    return 0;
}
```

```
$ ./tane
ic tekrar   1:    291.0   291.0   291.0   291.0   291.0   ns (n=1000..1004)
ic tekrar  16:    304.7   291.6   291.6   291.6   291.6   ns (n=1000..1004)
ic tekrar 256:    293.1   293.5   293.6   293.9   294.3   ns (n=1000..1004)
```

Tek ölçümle `n = 1000` ile `n = 1004` arasında fark **yok**; bütün değerler 7 tık. 256 kez tekrarlayıp bölünce her eleman için beklenen ~0.29 ns'lik artış görünüyor. Bu tuzağa düştük: 11.2'deki ilk ölçümümüzde bütün CPE'ler 0.146'nın katı çıkmıştı ($41.67 \text{ ns} \times 3.5 / 1000$). Bu yüzden bu fazdaki ölçümler her zaman bir **iç tekrar** döngüsü kullanıyor ve her ölçüm saat tanesinin en az birkaç yüz katı sürüyor.

### Tuzak 3: ısınma

```c
/* Ilk calistirma ile sonrakiler: taze bellek, sayfa hatalari */
#include "olcum.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
static long hata(void) { struct rusage r; getrusage(RUSAGE_SELF, &r); return r.ru_minflt; }
int main(void) {
    size_t n = 64u << 20;
    char *a = malloc(n);
    for (int t = 1; t <= 6; t++) {
        long h0 = hata(); double t0 = simdi();
        memset(a, t, n); KORU(a);
        double s = simdi() - t0;
        printf("tur %d: %8.2f ms, %6ld sayfa hatasi\n", t, s * 1e3, hata() - h0);
    }
    free(a);
    return 0;
}
```

```
$ ./isinma
tur 1:    14.56 ms,     34 sayfa hatasi
tur 2:     1.80 ms,      0 sayfa hatasi
tur 3:     1.84 ms,      0 sayfa hatasi
tur 4:     1.82 ms,      0 sayfa hatasi
tur 5:     1.80 ms,      0 sayfa hatasi
tur 6:     1.88 ms,      0 sayfa hatasi
```

İlk tur 8 kat yavaş: fiziksel sayfaları çekirdek o an veriyor (34 hata çünkü burada büyük sayfalar devrede; Ders 10.7). Önbellek ve dal tahmincisi de boş başlıyor. İlk turu at ya da en iyi süreyi al.

### Tuzak 4: dağılım simetrik değil

```c
/* Ayni is, 200000 olcum: dagilim simetrik degil */
#include "olcum.h"
#include <stdio.h>
#include <stdlib.h>
static int kars(const void *a, const void *b) { double x = *(const double *)a, y = *(const double *)b; return (x > y) - (x < y); }
__attribute__((noinline)) static long is(void) { long s = 0; for (long i = 0; i < 2000; i++) { s += i; KORU(s); } return s; }
int main(void) {
    enum { M = 200000 };
    double *o = malloc(M * sizeof *o), top = 0;
    for (int i = 0; i < M; i++) { double t0 = simdi(); is(); o[i] = (simdi() - t0) * 1e9; top += o[i]; }
    qsort(o, M, sizeof *o, kars);
    printf("en iyi  %8.0f ns\n", o[0]);
    printf("ortanca %8.0f ns\n", o[M / 2]);
    printf("ortalama%8.0f ns\n", top / M);
    printf("p99     %8.0f ns\n", o[M * 99 / 100]);
    printf("p99.9   %8.0f ns\n", o[M * 999 / 1000]);
    printf("en kotu %8.0f ns\n", o[M - 1]);
    double b = 0; for (int i = 0; i < 20000; i++) { double t0 = simdi(); double t1 = simdi(); b += t1 - t0; }
    printf("iki ardisik saat okumasi arasi: %.1f ns\n", b / 20000 * 1e9);
    return 0;
}
```

```
$ ./dagilim
en iyi       500 ns
ortanca      584 ns
ortalama     611 ns
p99          792 ns
p99.9        958 ns
en kotu    22625 ns
iki ardisik saat okumasi arasi: 16.3 ns
```

Aynı iş, yine de dağılım sağa çarpık: gerçek süre bir **alt sınır** ve her şey (kesme, TLB ıskası, başka bir sürecin yolu kesmesi) onu yalnızca artırır. En kötü ölçüm en iyinin 45 katı. Ortalama bu aykırı değerlere duyarlı.

- Mekanizmayı, çevrim sayısını anlamak istiyorsan **en iyi** süreye bak: "işlemcinin rahatsız edilmeden yaptığı".
- Bir sistemin kullanıcıya hissettirdiğini ölçüyorsan **ortanca ve p99**. Sunucu gecikmesinde en iyi değer anlamsızdır.

### Tuzak 5: ölçüm düzeneği

Mytkowicz ve arkadaşları (2009), bağlama sırası ve ortam değişkenlerinin boyutu gibi "alakasız" şeylerin bile performansı %10'u aşan oranda değiştirebildiğini gösterdi: kod ve yığının hizası değişiyor. Bunu kendi makinemizde deneyelim:

```c
/* Kod hizasi: dongunun bellekteki yeri sureyi degistirir mi? */
#include "olcum.h"
#include <stdio.h>
#define DON(ad, nop) __attribute__((noinline, aligned(4096))) static double ad(void) { \
    double t0 = simdi(); long x = 0; long n = 100000000; \
    __asm__ volatile(".rept " #nop "\n nop\n .endr\n 1: add %0, %0, #1\n add %0, %0, #1\n subs %1, %1, #1\n b.ne 1b" : "+r"(x), "+r"(n) : : "cc"); \
    return simdi() - t0; }
DON(h0, 0) DON(h3, 3) DON(h5, 5) DON(h7, 7) DON(h9, 9) DON(h13, 13) DON(h15, 15) DON(h31, 31)
static double en(double (*f)(void)) { double m = 1e9; for (int i = 0; i < 12; i++) { double t = f(); if (t < m) m = t; } return m / 1e8 * 1e9; }
int main(void) {
    printf("nop 0: %.3f\nnop 3: %.3f\nnop 5: %.3f\nnop 7: %.3f\nnop 9: %.3f\nnop13: %.3f\nnop15: %.3f\nnop31: %.3f ns/tur\n", en(h0), en(h3), en(h5), en(h7), en(h9), en(h13), en(h15), en(h31));
    return 0;
}
```

```
$ ./hiza
nop 0: 0.580
nop 3: 0.580
nop 5: 0.580
nop 7: 0.580
nop 9: 0.580
nop13: 0.580
nop15: 0.580
nop31: 0.580 ns/tur
```

Bu döngü bu çekirdekte **hiç etkilenmedi** (x86'da dönen kod önbelleği ve 32 baytlık sınırlar nedeniyle etkilenebiliyor). İki `add` zinciri 0.58 ns ≈ 2 çevrim, yani kod yeri fark etmeksizin beklenen. Ders şu: bir etkinin yokluğu da bir ölçüm sonucu ve başka makineye taşınmaz.

---

## 3. perf sayaçları

Modern işlemciler olayları donanımda sayar: çevrimler, biten komutlar, dal ıskaları, önbellek ıskaları, TLB ıskaları. `perf stat` (Ders 10.18) bunları okur. En kullanışlı türetilmiş ölçüt **IPC**:

$$
\text{IPC} = \frac{\text{biten komut sayısı}}{\text{çevrim}}
$$

Düşük IPC, işlemcinin bir şey beklediğini söyler: bellek, dal düzeltmesi ya da uzun komutlar. Çekirdek sayaçlara `perf_event_open` sistem çağrısıyla erişiyor, program içinden de kullanılabilir:

```c
/* perf_event_open: program icinden donanim sayaci okumak */
#define _GNU_SOURCE
#include <errno.h>
#include <linux/perf_event.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/syscall.h>
#include <unistd.h>
static int ac(uint32_t tur, uint64_t olay) {
    struct perf_event_attr a; memset(&a, 0, sizeof a);
    a.size = sizeof a; a.type = tur; a.config = olay; a.disabled = 1; a.exclude_kernel = 1; a.exclude_hv = 1;
    return (int)syscall(SYS_perf_event_open, &a, 0, -1, -1, 0);
}
int main(void) {
    struct { const char *ad; uint32_t t; uint64_t o; } s[] = {
        { "cycles", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CPU_CYCLES },
        { "instructions", PERF_TYPE_HARDWARE, PERF_COUNT_HW_INSTRUCTIONS },
        { "branch-misses", PERF_TYPE_HARDWARE, PERF_COUNT_HW_BRANCH_MISSES },
        { "cache-misses", PERF_TYPE_HARDWARE, PERF_COUNT_HW_CACHE_MISSES },
        { "task-clock", PERF_TYPE_SOFTWARE, PERF_COUNT_SW_TASK_CLOCK },
        { "page-faults", PERF_TYPE_SOFTWARE, PERF_COUNT_SW_PAGE_FAULTS },
    };
    for (size_t i = 0; i < sizeof s / sizeof *s; i++) {
        int f = ac(s[i].t, s[i].o);
        if (f < 0) { printf("%-14s yok: %s\n", s[i].ad, strerror(errno)); continue; }
        ioctl(f, PERF_EVENT_IOC_RESET, 0); ioctl(f, PERF_EVENT_IOC_ENABLE, 0);
        volatile long x = 0; for (long k = 0; k < 10000000; k++) x += k;
        ioctl(f, PERF_EVENT_IOC_DISABLE, 0);
        long long v = 0; read(f, &v, sizeof v); close(f);
        printf("%-14s %lld\n", s[i].ad, v);
    }
    return 0;
}
```

```
$ ./olay
cycles         yok: No such file or directory
instructions   yok: No such file or directory
branch-misses  yok: No such file or directory
cache-misses   yok: No such file or directory
task-clock     16199834
page-faults    0
```

Ders 10.18'deki gibi: bu sanal makinenin hipervizörü donanım sayaçlarını konuğa sunmuyor (`ENOENT`), yazılım sayaçları çalışıyor. **Çıplak donanım Linux'ta** aynı program gerçek sayıları verir ve `perf stat -e cycles,instructions,branch-misses,cache-misses ./program` kullanılabilir. WSL2 ve bulut makinelerinde durum değişkendir; bu programı çalıştırarak öğrenebilirsin. Biz bu fazda yukarıdaki iki yedek yolu (frekans kalibrasyonu ve macOS sayacı) kullanacağız; dal ıskası ve önbellek ıskası sayılarını doğrudan ölçemiyoruz, davranıştan çıkaracağız (Ders 11.4).

---

## 4. CPE

Kısa bir döngünün performansını ifade etmenin en iyi yolu **eleman başına çevrim** (cycles per element, CPE; *CS:APP* Bölüm 5). Bir döngünün süresi $n$'e doğrusal bağlı:

$$
T(n) = c + \text{CPE} \cdot n
$$

$c$, başlangıç maliyeti (fonksiyon çağrısı, kontrol, kalan döngüsü). Toplam süreyi $n$'e bölersek ikisi karışır; farklı $n$ değerlerinde ölçüp **doğru uydurursak** (en küçük kareler) ayrılırlar. Klasik örnek, önek toplamı:

```c
/* CPE: T(n) = sabit + CPE * n dogrusunun egimi (CS:APP Bolum 5) */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5                   /* frekans.c ile olculdu */
__attribute__((noinline)) static void psum1(const float *a, float *p, long n) {
    p[0] = a[0];
    for (long i = 1; i < n; i++) p[i] = p[i - 1] + a[i];
}
__attribute__((noinline)) static void psum2(const float *a, float *p, long n) {
    long i; p[0] = a[0];
    for (i = 1; i < n - 1; i += 2) { float m = p[i - 1] + a[i]; p[i] = m; p[i + 1] = m + a[i + 1]; }
    if (i < n) p[i] = p[i - 1] + a[i];
}
typedef void (*Fn)(const float *, float *, long);
static float a[4096], p[4096];
static double olc(Fn f, long n) {
    double en = 1e9;
    for (int r = 0; r < 200; r++) { double t0 = simdi(); for (int q = 0; q < 100; q++) { f(a, p, n); BELLEK(); } double t = simdi() - t0; if (t < en) en = t; }
    return en / 100 * 1e9 * GHZ;       /* cevrim */
}
static void uydur(const char *ad, Fn f) {
    double sx = 0, sy = 0, sxx = 0, sxy = 0; int m = 0;
    printf("%s\n", ad);
    for (long n = 200; n <= 2000; n += 200) {
        double y = olc(f, n);
        if (n % 600 == 200) printf("  n=%4ld: %8.0f cevrim, %.2f cevrim/eleman\n", n, y, y / n);
        sx += n; sy += y; sxx += (double)n * n; sxy += n * y; m++;
    }
    double b = (m * sxy - sx * sy) / (m * sxx - sx * sx), c = (sy - b * sx) / m;
    printf("  dogru: %.1f + %.3f * n  -> CPE = %.3f\n", c, b, b);
}
int main(void) {
    for (int i = 0; i < 4096; i++) a[i] = (float)(i % 17) * 0.25f;
    uydur("psum1", psum1);
    uydur("psum2", psum2);
    return 0;
}
```

`psum2` döngüyü iki adımda bir açıyor; ders kitabında daha hızlı olan sürüm bu. Bu makinede:

```
$ cc -O2 -fno-vectorize -fno-slp-vectorize cpe.c -o cpe && ./cpe
psum1
  n= 200:      502 cevrim, 2.51 cevrim/eleman
  n= 800:     2272 cevrim, 2.84 cevrim/eleman
  n=1400:     4070 cevrim, 2.91 cevrim/eleman
  n=2000:     5868 cevrim, 2.93 cevrim/eleman
  dogru: -94.9 + 2.977 * n  -> CPE = 2.977
psum2
  n= 200:     1256 cevrim, 6.28 cevrim/eleman
  n= 800:     5750 cevrim, 7.19 cevrim/eleman
  n=1400:    10245 cevrim, 7.32 cevrim/eleman
  n=2000:    14739 cevrim, 7.37 cevrim/eleman
  dogru: -242.8 + 7.491 * n  -> CPE = 7.491
```

Doğru uydurmanın değeri: `cevrim/eleman` sütunu `n` ile değişiyor (2.51, 2.84, ...), oysa eğim 2.98 net. (Burada $c$ negatif çıkıyor; küçük $n$'de ilk elemanlar daha hızlı işleniyor, gerçek bir "başlangıç maliyeti" değil. Uydurmayı ölçüm aralığının dışına taşıma.)

Ama asıl sürpriz: "hızlandırılmış" `psum2` **2.5 kat yavaş**. Nedenini assembly söylüyor:

```
psum1:  ...                                  psum2:  ...
	ldr	s1, [x9], #4                     	ldur	s0, [x10, #-4]      ; p[i-1]
	subs	x8, x8, #1                       	ldur	s1, [x11, #-4]
	fadd	s0, s0, s1                       	add	x8, x8, #2
	str	s0, [x1], #4                     	cmp	x8, x9
	b.ne	.LBB2_2                          	fadd	s0, s0, s1
                                                 	str	s0, [x10]
                                                 	ldr	s1, [x11], #8
                                                 	fadd	s0, s0, s1
                                                 	str	s0, [x10, #4]
                                                 	add	x10, x10, #8
                                                 	b.lt	.LBB3_2
```

`psum1`'de derleyici bir önceki sonucu `s0`'da tutuyor: bellekten geri okumuyor. `psum2`'de ise döngü başında `p[i-1]`, **bir önceki turda yeni yazılmış** bellekten okunuyor. Yazma henüz depo tamponundayken okuma oradan iletilmek zorunda (**store-to-load forwarding**) ve bu, gecikme zincirine ekleniyor. Tur başına 15 çevrim: 2 `fadd` için 6, geriye kalan yaklaşık 9 çevrim iletimin. Doğrulama: aynı açmayı sonucu bir yerel değişkende tutarak yazalım.

```c
__attribute__((noinline)) static void psum3(const float *a, float *p, long n) {
    long i; float son = p[0] = a[0];
    for (i = 1; i < n - 1; i += 2) { float m = son + a[i]; son = m + a[i + 1]; p[i] = m; p[i + 1] = son; }
    if (i < n) p[i] = son + a[i];
}
```

```
p - a uzakligi   psum1   psum2   psum3 (CPE)
     65536      3.00    7.49    3.11
     65568      3.00    7.49    3.12
     65600      3.00    7.49    3.11
     66560      3.00    7.49    3.11
     67584      3.00    7.49    3.11
     68536      3.00    7.49    3.11
```

`psum3` 3.11: `psum1` ile aynı. (Dizilerin birbirine göre konumunu da değiştirdik, sonuç oynamadı; yani bu, adres çakışması değil.) `fadd` gecikmesi 3 çevrim (Ders 11.2) ve eleman başına bir `fadd` zinciri olduğu için **3 CPE'nin altına inilemez**. Açmanın işe yaramamasının sebebi de bu: Ders 11.3'ün konusu.

---

## Alıştırmalar

**1** – `tuzak.c`'deki `a_kullanilmiyor` fonksiyonuna, döngüden sonra `KORU(s);` ekle. Süre ne olur? Neden hâlâ gerçek bir döngü ölçmüyorsun? Döngünün içine aldığında ne değişiyor?

**2** – `frekans.c`'deki `add` zincirini, bir önceki sonucu kullanmayan iki ayrı register'a dağıtılmış hale getir ve aynı "frekansı" hesapla. Neden 7 GHz gibi anlamsız bir değer çıkıyor?

**3** – 5 ms süren bir işi ölçüyorsun, saatin çözünürlüğü 1 ms. Bağıl belirsizlik ne kadar? 41.67 ns'lik saatte %1 hassasiyet için tek ölçüm en az kaç ns sürmeli?

**4** – `T(n) = 100 + 2n` olan bir döngü ile `T(n) = 20 + 3n` olan bir döngü veriliyor. Hangi $n$'de eşitlenirler? Çoğunlukla 8 elemanlı vektörler işleyen bir program için hangisi daha iyi?

**5** – Bir programda IPC 0.4 ölçtün. Tek başına bu bilgiyle ne söyleyebilirsin, ne söyleyemezsin? Aynı programı bir sonraki adımda hangi sayaçlarla incelersin?

<details>
<summary>Cevaplar</summary>

**1** – Hâlâ 0 ns'ye yakın: `KORU(s)` döngüden sonra olunca derleyici `s`'i kapalı formülle üretebiliyor, yalnızca sonucun var olmasını istemiş oluyoruz. Döngünün içinde olunca her turda `s` register'da gerçekten bulunmak zorunda ve döngü kapalı forma çevrilemiyor (bir ara değer bile "kullanılıyor").

**2** – İki bağımsız zincir her çevrimde iki `add` tamamlıyor: bir `add` süresi yarıya iniyor ve "frekans" iki katına çıkıyor. `add` başına çevrim, **bağımlılık** olduğunda 1'dir; yalnızca o zaman bir saat ölçer olarak kullanılabilir (macOS çıktısındaki 0.311 çevrim/op bunu gösteriyor).

**3** – Yaklaşık $\pm 1 / 5 = \%20$ (iki uçta da yarım tane kabulüyle $\pm 10\%$). $41.67 / 0.01 = 4167$ ns, yani en az 4.2 µs, güvenli olmak için birkaç katı.

**4** – $100 + 2n = 20 + 3n \Rightarrow n = 80$. $n = 8$ için ilki $116$, ikincisi $44$ çevrim: ikinci çok daha iyi. CPE'si iyi olan sürüm uzun dizilerde kazanır, başlangıç maliyeti düşük olan kısa dizilerde. Ders 11.3'teki açma, Ders 11.15'teki vektörleştirme hep bu değiş tokuşu yapar.

**5** – Söylenebilen: çevrimlerin büyük kısmında işlemci komut bitirmiyor; bir şeyi bekliyor. Söylenemeyen: **neyi** beklediği (önbellek ıskası, dal ıskası, uzun gecikmeli komut, bellek bant genişliği) ve hızlandırmanın mümkün olup olmadığı. Sonraki adım `cache-misses`, `branch-misses`, `LLC-load-misses` ve `dTLB-load-misses` sayaçları, ya da `perf stat -d` ve `perf stat --topdown` ile üst düzey ayrıştırma.

</details>

---

## Kaynaklar

- Randal Bryant ve David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 5: CPE ve program optimizasyonu.
- Todd Mytkowicz ve ark., "Producing Wrong Data Without Doing Anything Obviously Wrong!", *ASPLOS 2009*.
- Agner Fog, *Optimizing Software in C++* ve *Optimizing Subroutines in Assembly Language* (agner.org/optimize).
- Google Benchmark belgeleri: `DoNotOptimize` ve `ClobberMemory`.
- Charlie Curtsinger ve Emery Berger, "STABILIZER: Statistically Sound Performance Evaluation", *ASPLOS 2013*.
- `man 2 perf_event_open`, `man 1 perf-stat`.

**Sıradaki ders:** Gecikme ve verim. Komut tablolarını okumak, bağımlılık zinciri ve çoklu akümülatör tekniği.
