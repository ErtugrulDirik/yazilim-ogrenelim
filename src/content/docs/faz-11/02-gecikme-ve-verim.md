---
title: "11.2 Gecikme ve verim"
description: "Bir komutun iki sayısı: gecikme ve karşılıklı verim; Agner Fog tablolarını okumak (Skylake örneği); Apple M2 için kendi komut tablomuzu ölçmek: add 1, mul 3, fadd 3, fmul 4, fdiv 10, ldr 3 çevrim; gecikme sınırı ve kapasite sınırı; kritik yol; 2x1 açmanın işe yaramaması, birleşme sırasını değiştirmek ve k x k çoklu akümülatör: double çarpımında CPE 4'ten 0.51'e."
---

Ders 11.1'in sonunda iki sürpriz bıraktık: bir `add` zinciri 1.0 çevrim sürerken aynı sayıda `add` dört register'a dağılınca IPC 3.23 oluyor; `psum` döngüsü ise 3 CPE'nin altına inmiyor. İkisini de tek bir fikir açıklıyor: **bir komutun iki ayrı maliyeti var.**

---

## 1. Gecikme ve verim

- **Gecikme** (latency): bir komutun sonucunun, ona bağımlı bir sonraki komuta hazır olması için geçen çevrim sayısı.
- **Verim** (throughput): işlemcinin o komut türünden çevrim başına kaç tane **başlatabildiği**. Tablolarda çoğunlukla tersi yazılır: **karşılıklı verim** (reciprocal throughput), yani iki komutun başlaması arasındaki çevrim sayısı.

İşlem birimleri boru hatlıdır (Ders 7.20). Gecikmesi 4 ama verimi 1/çevrim olan bir çarpıcı, her çevrim yeni bir çarpma kabul eder; bir çarpma 4 çevrimde biter, ama aynı anda 4 tanesi hatta olabilir. Bu yüzden **birbirine bağımlı** komutlar gecikme hızında, **bağımsız** komutlar verim hızında ilerler.

### Komut tablosu okumak

Agner Fog'un *Instruction Tables* belgesi x86 için standart kaynak. Skylake'ten birkaç satır:

| Komut | µop | Portlar | Gecikme | Karşılıklı verim |
| --- | --- | --- | --- | --- |
| `ADD r,r` | 1 | p0156 | 1 | 0.25 |
| `IMUL r64,r64` | 1 | p1 | 3 | 1 |
| `DIV r64` | 36 | | 35–88 | 21–83 |
| `MOV r,m` | 1 | p23 | 2 | 0.5 |
| `ADDSD x,x` | 1 | p01 | 4 | 0.5 |
| `MULSD x,x` | 1 | p01 | 4 | 0.5 |
| `DIVSD x,x` | 1 | p0 | 13–14 | 4 |

Okuması: `ADD` dört porttan (0, 1, 5, 6) birinde çalışır, çevrimde 4 tane başlar. `IMUL` sadece port 1'de: çevrimde 1, 3 çevrim gecikmeli. `ADDSD`'nin gecikmesi 4 ama iki portta çalışıyor: çevrimde 2. `DIV`'in aralığı değerlere bağlı olduğunu söylüyor, 64 bit tamsayı bölmesi `ADD`'den yüz kat pahalı (Ders 5.14'teki sabite bölme optimizasyonunun nedeni). `MOV r,m` için 2 çevrim L1 vuruşunun **en iyi** gecikmesi.

Daha rahat bir kaynak uops.info: aynı veriyi otomatik ölçümlerle, işlemci başına veriyor. Bu sayılar **çekirdeğe özeldir**: Skylake'in tablosunu Zen 4'e uygulayamazsın. Tahmini `llvm-mca` aracıyla da yapabilirsin: LLVM'in zamanlama modellerini kullanarak bir assembly parçasını simüle eder.

---

## 2. Kendi tablomuzu ölçmek

Apple, M serisi için tablo yayımlamıyor (Dougall Johnson'ın bağımsız "Apple Microarchitecture Research" ölçümleri en iyi kaynak). Ama ölçmek kolay:

- **Gecikme**: komutun sonucunu tekrar girdi yapan bir zincir. Süre = adet × gecikme.
- **Verim**: aynı komutu çok sayıda **bağımsız** register'a dağıt; süre artık kapasite ile belirleniyor.

```c
/* Komut tablosunu kendimiz olcelim: gecikme (bagimli zincir) ve verim (bagimsiz zincirler) */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
#define TUR 200
static void *hedef[2048];                 /* L1'e sigan rastgele sirali halka */
#define OLC(ad, kur, op) __attribute__((noinline)) static void ad(long n) { \
    __asm__ volatile(kur "\n mov x17, %0\n 1:\n .rept 200\n" op "\n .endr\n subs x17, x17, #1\n b.ne 1b" \
    : : "r"(n), "r"(hedef) \
    : "x0","x1","x2","x3","x4","x5","x6","x7","x9","x10","x11","x12","x13","x14","x15","x16","x17", \
      "v0","v1","v2","v3","v4","v5","v6","v7","v16","v17","v18","v19","v20","v21","v22","v23","v24","v25","v26","v27","cc","memory"); }

#define KUR_T "mov x1, #3\n mov x9, #5\n mov x10, #5\n mov x11, #5\n mov x12, #5\n mov x13, #5\n mov x14, #5\n mov x15, #5\n mov x16, #5\n"
#define KUR_F "fmov d31, #1.0\n"
/* gecikme */
OLC(l_add,  KUR_T, "add x10, x10, #1")
OLC(l_eor,  KUR_T, "eor x10, x10, x1")
OLC(l_addx, KUR_T, "add x10, x10, w1, sxtw")
OLC(l_adds, KUR_T, "add x10, x10, x1, lsl #2")
OLC(l_csel, KUR_T "cmp x1, #0\n", "csel x10, x10, x1, ne")
OLC(l_lsl,  KUR_T, "lsl x10, x10, #1")
OLC(l_mul,  KUR_T, "mul x10, x10, x1")
OLC(l_madd, KUR_T, "madd x10, x10, x1, x1")
OLC(l_sdiv, "mov x11, #1\n lsl x11, x11, #60\n mov x10, #1\n lsl x10, x10, #30\n", "sdiv x10, x11, x10")
OLC(l_fadd, "fmov d0, #1.0\n fmov d1, #1.0\n", "fadd d0, d0, d1")
OLC(l_fmul, "fmov d0, #1.0\n fmov d1, #1.0\n", "fmul d0, d0, d1")
OLC(l_fmadd,"fmov d0, #1.0\n fmov d1, #1.0\n fmov d2, #1.0\n", "fmadd d0, d0, d1, d2")
OLC(l_fdiv, "fmov d0, #1.5\n fmov d1, #2.0\n", "fdiv d0, d1, d0")
OLC(l_ldr,  "mov x10, %1\n", "ldr x10, [x10]")
/* verim: 8 ya da 16 ayri zincir, blok basina op sayisi asagida */
#define I8(o) o " x9, x9, " Y "\n" o " x10, x10, " Y "\n" o " x11, x11, " Y "\n" o " x12, x12, " Y "\n" o " x13, x13, " Y "\n" o " x14, x14, " Y "\n" o " x15, x15, " Y "\n" o " x16, x16, " Y
#define Y "#1"
OLC(t_add, KUR_T, I8("add"))
#undef Y
#define Y "x1"
OLC(t_mul, KUR_T, I8("mul"))
#define F16(o) o " d0,d0,d31\n" o " d1,d1,d31\n" o " d2,d2,d31\n" o " d3,d3,d31\n" o " d4,d4,d31\n" o " d5,d5,d31\n" o " d6,d6,d31\n" o " d7,d7,d31\n" \
               o " d16,d16,d31\n" o " d17,d17,d31\n" o " d18,d18,d31\n" o " d19,d19,d31\n" o " d20,d20,d31\n" o " d21,d21,d31\n" o " d22,d22,d31\n" o " d23,d23,d31"
OLC(t_fadd, KUR_F "fmov d0,#1.0\n fmov d1,#1.0\n fmov d2,#1.0\n fmov d3,#1.0\n fmov d4,#1.0\n fmov d5,#1.0\n fmov d6,#1.0\n fmov d7,#1.0\n fmov d16,#1.0\n fmov d17,#1.0\n fmov d18,#1.0\n fmov d19,#1.0\n fmov d20,#1.0\n fmov d21,#1.0\n fmov d22,#1.0\n fmov d23,#1.0\n", F16("fadd"))
OLC(t_fmul, KUR_F "fmov d0,#1.0\n fmov d1,#1.0\n fmov d2,#1.0\n fmov d3,#1.0\n fmov d4,#1.0\n fmov d5,#1.0\n fmov d6,#1.0\n fmov d7,#1.0\n fmov d16,#1.0\n fmov d17,#1.0\n fmov d18,#1.0\n fmov d19,#1.0\n fmov d20,#1.0\n fmov d21,#1.0\n fmov d22,#1.0\n fmov d23,#1.0\n", F16("fmul"))
OLC(t_ldr, "mov x0, %1\n", "ldr x9, [x0]\n ldr x10, [x0,#8]\n ldr x11, [x0,#16]\n ldr x12, [x0,#24]\n ldr x13, [x0,#32]\n ldr x14, [x0,#40]\n ldr x15, [x0,#48]\n ldr x16, [x0,#56]")
OLC(t_str, "mov x0, %1\n", "str x1, [x0]\n str x1, [x0,#8]\n str x1, [x0,#16]\n str x1, [x0,#24]\n str x1, [x0,#32]\n str x1, [x0,#40]\n str x1, [x0,#48]\n str x1, [x0,#56]")
OLC(t_sdiv, "mov x1, #1\n lsl x1, x1, #60\n mov x9, #1\n lsl x9, x9, #30\n mov x10, x9\n mov x11, x9\n mov x12, x9\n", "sdiv x9, x1, x9\n sdiv x10, x1, x10\n sdiv x11, x1, x11\n sdiv x12, x1, x12")

static double cevrim(void (*f)(long), double op) {
    double en = 1e9;
    for (int r = 0; r < 60; r++) { double t0 = simdi(); f(TUR); double t = simdi() - t0; if (t < en) en = t; }
    return en * 1e9 * GHZ / (TUR * 200.0 * op);
}
int main(void) {
    int sira[2048]; unsigned r = 12345;
    for (int i = 0; i < 2048; i++) sira[i] = i;
    for (int i = 2047; i > 0; i--) { r = r * 1103515245 + 12345; int j = (r >> 8) % (i + 1); int t = sira[i]; sira[i] = sira[j]; sira[j] = t; }
    for (int i = 0; i < 2048; i++) hedef[sira[i]] = &hedef[sira[(i + 1) % 2048]];
    printf("%-10s %8s\n", "komut", "gecikme");
#define G(ad, f) printf("%-10s %8.2f\n", ad, cevrim(f, 1))
    G("add", l_add); G("eor", l_eor); G("add sxtw", l_addx); G("add lsl#2", l_adds); G("csel", l_csel); G("lsl", l_lsl); G("mul", l_mul); G("madd", l_madd); G("sdiv", l_sdiv);
    G("fadd", l_fadd); G("fmul", l_fmul); G("fmadd", l_fmadd); G("fdiv", l_fdiv); G("ldr (L1)", l_ldr);
    printf("%-10s %10s %14s\n", "komut", "op/cevrim", "cevrim/op");
#define V(ad, f, op) { double c = cevrim(f, op); printf("%-10s %10.2f %14.3f\n", ad, 1 / c, c); }
    V("add", t_add, 8); V("mul", t_mul, 8); V("fadd", t_fadd, 16); V("fmul", t_fmul, 16); V("ldr", t_ldr, 8); V("str", t_str, 8); V("sdiv", t_sdiv, 4);
    return 0;
}
```

```
$ cc -O2 -fno-vectorize tablo.c -o tablo && ./tablo
komut       gecikme
add            1.00
eor            1.00
add sxtw       2.00
add lsl#2      1.99
csel           1.00
lsl            1.00
mul            2.99
madd           3.19
sdiv           6.99
fadd           2.99
fmul           3.99
fmadd          3.99
fdiv           9.99
ldr (L1)       2.99
komut       op/cevrim      cevrim/op
add              4.79          0.209
mul              2.00          0.501
fadd             4.01          0.250
fmul             4.01          0.250
ldr              2.83          0.353
str              2.00          0.499
sdiv             0.50          1.997
```

Tablodan okunanlar:

- Gecikmeler neredeyse tam sayı: `add` 1, `mul` 3, `fadd` 3, `fmul` 4, `sdiv` 7, `fdiv` 10, L1 `ldr` 3. Yöntem çalışıyor.
- **Uzatmalı `add`** (`add x, x, w, sxtw`) ve kaydırmalı `add` (`lsl #2`) **2 çevrim**: düz `add`'in iki katı. Assembly'de tek komut gibi görünüyorlar ama bir aşama daha var. Ders 11.4'te bunun bir CPE sonucunu açıkladığını göreceğiz.
- `csel` 1 çevrim: dallanmadan seçim yapmak ucuz (Ders 11.4).
- Verim: `mul` çevrimde 2, `fadd` ve `fmul` çevrimde 4, `str` 2, `ldr` 2.83, `sdiv` 0.5.
- `add` için 4.79. Bağımsız ölçümler bu çekirdekte altı tamsayı birimi veriyor, biz 8 zincirle 4.8'de kaldık. Yani darboğaz birim sayısı değil, başka bir aşama; elimizdeki araçlarla bunu ayıramıyoruz.

:::caution[Bir ölçüm tuzağı daha]
`ldr` gecikmesini ilk ölçüşümüzde bir yere kendini gösteren tek işaretçi kullandık (`ldr x10, [x10]`, `x10` hep aynı adres). Bazı çalıştırmalar 3.0, bazıları **1.14** çevrim verdi. M serisi çekirdeklerde adres tahmini var (SLAP makalesi, 2024): aynı adresten aynı yükleme tekrarlanınca işlemci sonucu tahmin edebiliyor, bağımlılık zinciri kırılıyor. Bellek gecikmesi ölçmek için işaretçi **rastgele sıralı bir halkada** gezmeli; yukarıdaki kod bunu yapıyor ve hep 2.99 veriyor.
:::

---

## 3. İki sınır

Bir döngünün CPE'si için iki alt sınır var:

$$
\text{gecikme sınırı} = \frac{\text{kritik yol gecikmesi}}{\text{eleman sayısı}}, \qquad \text{kapasite sınırı} = \frac{\text{komut sayısı}}{\text{birim sayısı}}
$$

**Kritik yol**: döngü boyunca birbirine bağımlı komutların en uzun zinciri. Çarpım döngüsüne bakalım:

```c
for (long i = 0; i < n; i++) r = r * a[i];
```

```
.LBB19_2:
	ldr	d1, [x8], #8
	subs	x0, x0, #1
	fmul	d0, d0, d1
	b.ne	.LBB19_2
```

Her `fmul` bir öncekinin sonucunu (`d0`) kullanıyor: uzun bir bağımlılık zinciri.

```
tur:      1          2          3
d0 ───▶ fmul ───▶ fmul ───▶ fmul ───▶      her fmul: 4 çevrim
         ▲          ▲          ▲
        ldr        ldr        ldr          bağımsız: paralel
```

Eleman başına bir `fmul`, gecikme 4: gecikme sınırı **4 CPE**. Oysa kapasite sınırı 1/4 = 0.25 CPE. İşlemci her çevrim dört çarpma başlatabilir, ama aynı zincirdeki bir çarpma bir öncekinin bitmesini bekliyor: dört birimin üçü boşta. Hızlanmak için **zinciri kırmak** gerekiyor.

---

## 4. Zinciri kırmak

CS:APP'in `combine` ailesi. `k×j`: tur başına $k$ eleman, $j$ tane birikimci.

- `1x1`: düz döngü.
- `2x1`: iki eleman, tek birikimci: `r = (r * a[i]) * a[i+1]`. Hâlâ tek zincir.
- `2x1a`: **birleşme sırasını değiştir**: `r = r * (a[i] * a[i+1])`. Zincirdeki adım sayısı yarıya iniyor: iki elemanı çarpmak bağımsız yapılabiliyor.
- `2x2`: iki bağımsız birikimci: `r0 *= a[i]; r1 *= a[i+1];`.
- `4x4`, `8x8`: aynı fikir daha geniş.

```c
/* Coklu akumulator: k x j acma (CS:APP combine) */
#include "olcum.h"
#include <stdio.h>
#define GHZ 3.5
#define URET(sonek, T, OP, BIRIM) \
__attribute__((noinline)) static T c1x1_##sonek(const T *a, long n) { T r = BIRIM; for (long i = 0; i < n; i++) r = r OP a[i]; return r; } \
__attribute__((noinline)) static T c2x1_##sonek(const T *a, long n) { T r = BIRIM; long i; for (i = 0; i + 1 < n; i += 2) r = (r OP a[i]) OP a[i + 1]; for (; i < n; i++) r = r OP a[i]; return r; } \
__attribute__((noinline)) static T c2x1a_##sonek(const T *a, long n) { T r = BIRIM; long i; for (i = 0; i + 1 < n; i += 2) r = r OP (a[i] OP a[i + 1]); for (; i < n; i++) r = r OP a[i]; return r; } \
__attribute__((noinline)) static T c2x2_##sonek(const T *a, long n) { T r0 = BIRIM, r1 = BIRIM; long i; for (i = 0; i + 1 < n; i += 2) { r0 = r0 OP a[i]; r1 = r1 OP a[i + 1]; } for (; i < n; i++) r0 = r0 OP a[i]; return r0 OP r1; } \
__attribute__((noinline)) static T c4x4_##sonek(const T *a, long n) { T r0 = BIRIM, r1 = BIRIM, r2 = BIRIM, r3 = BIRIM; long i; for (i = 0; i + 3 < n; i += 4) { r0 = r0 OP a[i]; r1 = r1 OP a[i + 1]; r2 = r2 OP a[i + 2]; r3 = r3 OP a[i + 3]; } for (; i < n; i++) r0 = r0 OP a[i]; return (r0 OP r1) OP (r2 OP r3); } \
__attribute__((noinline)) static T c8x8_##sonek(const T *a, long n) { T r[8]; for (int k = 0; k < 8; k++) r[k] = BIRIM; T r0=r[0],r1=r[1],r2=r[2],r3=r[3],r4=r[4],r5=r[5],r6=r[6],r7=r[7]; long i; for (i = 0; i + 7 < n; i += 8) { r0 = r0 OP a[i]; r1 = r1 OP a[i + 1]; r2 = r2 OP a[i + 2]; r3 = r3 OP a[i + 3]; r4 = r4 OP a[i + 4]; r5 = r5 OP a[i + 5]; r6 = r6 OP a[i + 6]; r7 = r7 OP a[i + 7]; } for (; i < n; i++) r0 = r0 OP a[i]; return ((r0 OP r1) OP (r2 OP r3)) OP ((r4 OP r5) OP (r6 OP r7)); }
URET(lt, long, +, 0)
URET(lc, long, *, 1)
URET(dt, double, +, 0.0)
URET(dc, double, *, 1.0)
static long la[4096]; static double da[4096];
#define EGIM(fn, dizi, T) ({ double y[2]; long ns[2] = { 1000, 2000 }; \
    for (int k = 0; k < 2; k++) { double en = 1e9; for (int r = 0; r < 200; r++) { double t0 = simdi(); for (int q = 0; q < 200; q++) { T v = fn(dizi, ns[k]); KORU(v); } double t = simdi() - t0; if (t < en) en = t; } y[k] = en / 200; } \
    (y[1] - y[0]) * 1e9 * GHZ / 1000; })
#define SATIR(ad, sn, dizi, T) printf("%-12s %6.2f %6.2f %6.2f %6.2f %6.2f %6.2f\n", ad, EGIM(c1x1_##sn, dizi, T), EGIM(c2x1_##sn, dizi, T), EGIM(c2x1a_##sn, dizi, T), EGIM(c2x2_##sn, dizi, T), EGIM(c4x4_##sn, dizi, T), EGIM(c8x8_##sn, dizi, T))
int main(void) {
    for (int i = 0; i < 4096; i++) { la[i] = 2 * i + 3; da[i] = 1.0 + (i % 7 - 3) * 1e-6; }
    printf("%-12s %6s %6s %6s %6s %6s %6s\n", "CPE", "1x1", "2x1", "2x1a", "2x2", "4x4", "8x8");
    SATIR("long +", lt, la, long); SATIR("long *", lc, la, long); SATIR("double +", dt, da, double); SATIR("double *", dc, da, double);
    return 0;
}
```

```
$ cc -O2 -fno-vectorize -fno-slp-vectorize birlestir.c -o birlestir && ./birlestir
CPE             1x1    2x1   2x1a    2x2    4x4    8x8
long +         1.25   1.08   1.09   1.02   0.55   0.33
long *         3.00   3.00   3.00   1.50   0.81   0.53
double +       3.00   2.99   1.50   1.50   0.75   0.39
double *       4.00   3.99   2.00   2.00   1.00   0.51
```

Satır satır, Bölüm 2'deki tablo ile:

| | Gecikme | $L$ / $k$ tahmini (1, 2, 4, 8 birikimci) | Kapasite sınırı |
| --- | --- | --- | --- |
| `double *` | 4 | 4, 2, 1, 0.5 | 0.25 (ve yükleme: 0.35) |
| `double +` | 3 | 3, 1.5, 0.75, 0.375 | 0.25 (ve yükleme: 0.35) |
| `long *` | 3 | 3, 1.5, 0.75, 0.375 | 0.5 |
| `long +` | 1 | 1, 0.5, 0.25, 0.125 | yükleme: 0.35 |

- `double` satırları neredeyse **tam** teoriyi veriyor: çarpımda $4 \to 2 \to 1 \to 0.51$, toplamada $3 \to 1.5 \to 0.75 \to 0.39$. $L/k$ formülü ölçümle örtüşüyor.
- `2x1` hiçbir kazanç getirmedi: 4.00'dan 3.99'a. Sırf açmak zinciri kırmıyor. Bu Ders 11.1'deki `psum`'un da sonucu: açmak gecikme sınırını değiştirmez.
- `2x1a` iki katı hız: yalnızca parantezlerin yeri değişti.
- `long *`, `8x8`'de 0.53'te duruyor: `mul` çevrimde en fazla 2 (kapasite sınırı 0.5).
- `long +` için 8x8'de 0.33 yükleme sınırına yakın (0.35). Eleman başına bir yükleme var ve çevrimde 2.83'ten fazla yapılamıyor.
- `long +` satırı en az temiz olan: 2x2 için beklediğimiz 0.5 yerine 1.02 ölçtük. Üretilen kod iki ayrı birikimci içeriyor (assembly'de `add x9, x14, x9` ve `add x8, x13, x8`); sayaçsız bir ortamda nedeni kesin olarak söyleyemiyoruz.

### Tamsayı ile kayan nokta farkı

Tamsayı toplama ve çarpma **birleşmeli**: `2x1a` ve `2x2` sonucu değiştirmez. Derleyici bunu kendisi yapabilir. Kayan noktada ise `(a * b) * c` ile `a * (b * c)` yuvarlama nedeniyle farklı çıkabilir (Ders 3.14). Standart bu yüzden derleyicinin yer değiştirmesine izin vermiyor: `double` için kod `2x1`'den `2x1a`'ya elle çevrilmek zorunda, ya da `-ffast-math` (`-fassociative-math`) ile bu serbestlik verilmeli. Yani yukarıdaki yeniden yazım **sonucu değiştiriyor**: bir `double` çarpımı için genellikle kabul edilebilir, finansal bir toplam için asla.

Bu teknik Faz 11'in omurgası: SIMD (Ders 11.6) tam olarak "$k$ tane birikimci"yi tek register'a koymak demek. Faz 16'da derleyicinin yeniden birleştirme (reassociation) geçişini yazarken aynı dönüşümü otomatikleştireceğiz.

---

## Alıştırmalar

**1** – Bir `combine` döngüsünde her turda `fadd`, `fmul` sırayla bir birikimciye uygulanıyor: `r = (r + a[i]) * b[i]`. M2 için gecikme sınırı nedir?

**2** – `tablo.c`'ye `fsqrt d0, d1, d0`'ın gecikmesini ve 4 bağımsız zincirli verimini ekle. Girdi seçimi önemli mi?

**3** – Skylake'te `IMUL r64,r64` için döngüde `r = r * a[i]`. 1x1 için CPE ne olur? 4x4 için? Kapasite sınırı hangisini engeller?

**4** – `2x1a` döngüsünde `(a[i] * a[i+1])` çarpımları birbirinden bağımsız. Teorik CPE hesabını yaz. Neden `(r * a[i]) * a[i+1]` ile `r * (a[i] * a[i+1])` farklı kritik yollara sahip?

**5** – Bir matris döngüsünde `a[i][j] = a[i-1][j] + a[i][j-1]`. Burada hangi bağımlılıklar kırılamaz? Çoklu akümülatör işe yarar mı?

<details>
<summary>Cevaplar</summary>

**1** – Kritik yol: `r` → `fadd` (3) → `fmul` (4) → `r`. Eleman başına 7 çevrim. Bu iki işlem tek zincirde birbirine bağımlı; `r`'yi bölmeden kısaltılamaz.

**2** – `fsqrt`, `fdiv` gibi uzun ve bazı işlemcilerde girdiye bağlı. Zincirde değer değişimi ve özel değerler önemli: `d0 = sqrt(d0)` 1.0'a yaklaşır ve çoğu zaman en hızlı duruma düşer, bu yüzden Bölüm 2'deki `fdiv` gibi ters çevrilebilir, değer değişimini önleyen bir kurulum kullan. Verim için farklı register'lara dağıtıp aynı yöntemi uygula.

**3** – 1x1: gecikme sınırı 3 CPE (tek zincir). 4x4: $3/4 = 0.75$ olurdu, ama `IMUL` yalnızca port 1'de, çevrimde 1 tane: kapasite sınırı **1 CPE**. Dolayısıyla 4x4 CPE ≈ 1, gecikme değil kapasite belirliyor. M2 çevrimde 2 tane yaptığı için aynı durumda 0.75'e kadar iniyor.

**4** – İki elemanı çarpan fmul'ler bağımsız, zincirdeki tek bağımlı işlem turda bir `fmul`: `r`. Tur başına 4 çevrim, tur başına 2 eleman: 2 CPE. Sol tarafta `r` iki kez arka arkaya çarpılıyor, yani zincir tur başına 2 fmul (8 çevrim): 4 CPE. Sağ tarafta `r` tur başına bir kez.

**5** – `a[i][j]` hem üstündekine hem solundakine bağlı: bir hücrenin önündeki bütün hücreler bitmeden başlanamaz. Satır içinde akümülatör bölmek geçersiz, çünkü her eleman bir öncekinin **sonucuna** ihtiyaç duyuyor (toplama birleşmeli olsa bile ara sonuçların kendisi isteniyor). Paralellik ancak farklı bir sırayla (çapraz dalgalar) mümkün; Faz 16'daki döngü dönüşümlerinin konusu.

</details>

---

## Kaynaklar

- Agner Fog, *Instruction Tables: Lists of Instruction Latencies, Throughputs and Micro-Operation Breakdowns* (agner.org/optimize).
- Andreas Abel ve Jan Reineke, "uops.info: Characterizing Latency, Throughput, and Port Usage of Instructions on Intel Microarchitectures", *ASPLOS 2019*.
- Dougall Johnson, "Apple Microarchitecture Research" (dougallj.github.io/applecpu/firestorm.html): Firestorm için ölçülmüş tablo.
- Randal Bryant ve David O'Hallaron, *CS:APP* (3. baskı), Bölüm 5.7–5.9: gecikme, kapasite sınırı ve `combine` deneyleri.
- Jason Kim ve ark., "SLAP: Data Speculation Attacks via Load Address Prediction on Apple Silicon", 2024.
- `man llvm-mca`.

**Sıradaki ders:** Döngü açma. Elle açma, derleyicinin açması, `#pragma unroll`.
