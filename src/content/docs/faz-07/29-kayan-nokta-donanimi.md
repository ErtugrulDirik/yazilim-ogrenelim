---
title: "7.29 Kayan nokta donanımı"
description: "x86'da kayan noktanın iki dünyası: 8 register'lık yığın tabanlı x87 (80 bit) ve register tabanlı SSE (xmm0–xmm15); x86-64'te float/double'ın SSE ile, long double'ın hâlâ x87 ile derlenmesi; addsd, mulss, cvtsi2sd, cvttsd2si, ucomisd, sqrtsd gibi skaler komutlar; System V ABI'de float argümanların xmm register'larında taşınması; x87'nin geniş ara hassasiyetinin aynı ifadeye farklı sonuç verdirmesi (1e308·10/10); NaN karşılaştırmaları ve seta; -fno-math-errno; aynı xmm register'larında paketlenmiş (SIMD) komutlara ilk bakış."
gereksinimler: [gcc]
---

Ders 3.12–3.14'te IEEE 754 sayılarının **bit düzeyinde** nasıl göründüğünü, Ders 5.18'de bu bitlerle hileler yapmayı gördük. Ama bu fazda baktığımız bütün assembly tamsayıydı: `add`, `imul`, `cmp`. Bu ders kayan noktanın donanım tarafını açıyor: işlemcinin `double` toplarken hangi register'ları ve komutları kullandığı, ve x86'nın neden bunun için **iki ayrı** sisteme sahip olduğu. Sonunda aynı register'ların aynı anda dört sayıyla çalışabildiğini görüp Faz 11'deki SIMD'ye kapıyı aralıyoruz.

Assembly çıktıları x86-64 Linux'ta (clang 18 ve gcc 13), karşılaştırma için bir yerde Apple M2'de.

---

## 1. Kısa tarih: x87

İlk x86 işlemcilerinde kayan nokta yoktu; ayrı bir yardımcı işlemci (8087, 1980) takılıyordu. **x87** denen bu birimin tasarımı sıra dışıydı:

- 8 tane **80 bitlik** register (`st(0)`–`st(7)`), ama adresle değil **yığın** olarak kullanılıyorlar (Ders 7.2'deki yığın makinesine benzer): `fld` yığına bir sayı iter, `fadd` tepedeki iki sayıyı toplar, `fstp` tepeyi belleğe yazıp çıkarır.
- Her hesap içeride **80 bit genişletilmiş hassasiyetle** (64 bit mantis, 15 bit üs) yapılıyor; `double`'a (53 bit mantis) ancak belleğe yazılırken yuvarlanıyor.

Yığın modeli derleyiciler için zahmetliydi (register tahsisi yerine yığın derinliği takibi), ve geniş hassasiyet bir **tutarsızlık** kaynağıydı: aynı ifade, ara değerin register'da mı yoksa bellekte mi tutulduğuna göre farklı sonuç verebiliyordu (Bölüm 4). 

1999'da Intel **SSE** (Streaming SIMD Extensions) ile yeni register'lar (`xmm0`–`xmm7`, her biri 128 bit) ve sıradan, register tabanlı kayan nokta komutları getirdi. SSE2 (2001) `double` desteği ekledi. AMD 64 bite geçerken (2003) bütün x86-64 işlemcilerinde SSE2'nin olmasını **zorunlu** kıldı; böylece x86-64 ABI'si kayan nokta için SSE'yi seçti ve x87 neredeyse emekliye ayrıldı.

---

## 2. SSE ile skaler kayan nokta

```c
double hipot2(double x, double y) { return x * x + y * y; }
float  karisik(float a, int n)    { return a * n + 0.5f; }
int    buyuk_mu(double a, double b) { return a > b; }
```

```
$ clang -O2 -S fp.c
hipot2:
        mulsd   %xmm1, %xmm1
        mulsd   %xmm0, %xmm0
        addsd   %xmm1, %xmm0
        retq

.LCPI1_0:
        .long   0x3f000000                      # float 0.5
karisik:
        cvtsi2ss  %edi, %xmm1
        mulss   %xmm1, %xmm0
        addss   .LCPI1_0(%rip), %xmm0
        retq

buyuk_mu:
        xorl    %eax, %eax
        ucomisd %xmm1, %xmm0
        seta    %al
        retq
```

Okumak için üç kural:

**İsimlendirme.** `mul` + `s` + `d`: **s**kaler (tek bir sayı), **d**ouble. `ss` = scalar single (`float`). `addsd`, `subsd`, `mulsd`, `divsd`, `sqrtsd`; ve `float` için `addss`, `mulss`, ... Bölüm 6'da göreceğimiz paketlenmiş sürümler `pd`/`ps` (packed double/single).

**ABI** (Ders 7.10'un kayan nokta kısmı). İlk 8 kayan nokta argümanı `xmm0`–`xmm7`'de, dönüş değeri `xmm0`'da. Tamsayı argümanlar kendi sıralarında (`rdi`, `rsi`, ...) ilerler, ikisi birbirini etkilemez: `karisik(float a, int n)`'de `a` → `xmm0`, `n` → `edi`. Bütün `xmm` register'ları çağıran-kaydeder (caller-saved); bir fonksiyon çağırınca hepsi bozulabilir.

**Sabitler.** x86'da kayan nokta için "anında değer" (immediate) yok; `0.5f` bellekte bir sabit olarak duruyor (`.LCPI1_0`, değeri `0x3f000000`: Ders 3.12'deki IEEE 754 kodlaması, işaret 0, üs 126, mantis 0) ve `%rip`'e göre adresleniyor (Ders 7.17).

**Dönüşüm** komutları: `cvtsi2ss` (signed integer → scalar single), `cvtss2sd` (float → double), `cvttsd2si` (double → int, **t**runcate: sıfıra doğru keserek, C'nin `(int)x` kuralı, Ders 3.7):

```c
int kes(double x) { return (int)x; }
double topla3(float a, double b, int c) { return a + b + c; }
```

```
kes:
        cvttsd2si %xmm0, %eax
        retq
topla3:
        cvtss2sd  %xmm0, %xmm2          # a: float -> double (C'nin aritmetik donusumu)
        addsd     %xmm1, %xmm2          # a + b
        xorps     %xmm0, %xmm0          # (bagimliligi kirmak icin sifirla, Ders 7.23)
        cvtsi2sd  %edi, %xmm0           # c: int -> double
        addsd     %xmm2, %xmm0          # (a + b) + c
        retq
```

`topla3` Ders 3.5–3.7'deki "olağan aritmetik dönüşümleri" komut komut gösteriyor: her işlemden önce iki taraf da ortak tipe (`double`) çevriliyor. `cvtsi2sd` hedef register'ın sadece alt 64 bitini yazıyor; üst kısım eski değerde kalıyor, bu da sahte bir bağımlılık (Ders 7.23'teki isim bağımlılığının bir türü) yaratıyor. Derleyici önce `xorps` ile register'ı sıfırlayarak işlemciye "eski değere bağlı değilim" diyor.

---

## 3. Karşılaştırma ve NaN

`buyuk_mu`'daki `ucomisd` (unordered compare scalar double) sonucu tamsayı karşılaştırmasındaki gibi bayraklara yazıyor, ama **işaretsiz** karşılaştırma bayraklarına: `CF` ve `ZF` (Ders 7.8). Bu yüzden `a > b` için `setg` değil `seta` ("above", işaretsiz büyük) kullanılıyor.

Neden "unordered"? Ders 3.13'teki NaN yüzünden: NaN hiçbir şeyle (kendisiyle bile) karşılaştırılamaz. `ucomisd` iki taraftan biri NaN ise `ZF = PF = CF = 1` yapar: "eşit ve küçük" gibi bir saçmalık, ve **PF** (parity) "sıralanamaz" işareti. `seta` `CF = 0` ve `ZF = 0` ister; NaN'de ikisi de 1, sonuç 0. Yani `NaN > 1` yanlış, doğru olan bu:

```c
volatile double n = NAN;
printf("%d %d %d\n", buyuk_mu(n, 1), buyuk_mu(1, n), n == n);
```

```
0 0 0
```

Derleyici `a < b`'yi de `seta` ile yapar, operandların yerini değiştirerek:

```
kucuk_mu:                       # return a < b;
        xorl    %eax, %eax
        ucomisd %xmm0, %xmm1    # b ile a'yi karsilastir (ters sira)
        seta    %al             # b > a
        retq
```

`setb` ("below") kullansaydı NaN'de `CF = 1` olduğu için `NaN < 1` **doğru** çıkardı. Ters çevirme hilesi NaN'i bedavaya doğru işliyor. (`==` için derleyici NaN'i ayrıca hesaba katmak zorunda; Alıştırma 3.)

### `sqrt` ve `errno`

```c
#include <math.h>
double kok(double x) { return sqrt(x); }
```

```
kok:                                   # clang -O2
        xorpd   %xmm1, %xmm1
        ucomisd %xmm1, %xmm0           # x < 0 mi?
        jb      sqrt@PLT               # evet: libm'deki sqrt'yi cagir (errno = EDOM)
        sqrtsd  %xmm0, %xmm0           # hayir: tek komut
        retq

kok:                                   # clang -O2 -fno-math-errno
        sqrtsd  %xmm0, %xmm0
        retq
```

Donanımın `sqrtsd` komutu var ve negatif sayıda NaN döndürüyor. Ama C standardı `sqrt(-1)`'in ayrıca `errno`'yu `EDOM`'a ayarlamasını istiyor, ve bir komut `errno` yazamaz. Derleyici bu yüzden negatif durumu kütüphaneye yönlendiriyor. `-fno-math-errno` ("errno'ya bakmıyorum") bu yükü kaldırıyor. Matematik ağırlıklı kodda sık kullanılan, `-ffast-math`'ın (Ders 7.23) güvenli bir alt kümesi.

---

## 4. x87 hâlâ burada: `long double`

x87 tamamen gitmedi: x86-64 Linux'ta `long double` 80 bitlik x87 sayısı olarak kaldı.

```c
long double uzun(long double x, long double y) { return x * y + x; }
```

```
uzun:
        fldt    24(%rsp)            # y'yi x87 yiginina it  (st0 = y)
        fldt    8(%rsp)             # x'i it                (st0 = x, st1 = y)
        fmul    %st, %st(1)         # st1 = x * y
        faddp   %st, %st(1)         # st1 = x*y + x, yigindan cikar -> st0
        retq                        # sonuc st0'da
```

Yığın makinesi açıkça görünüyor: register adı yok, `st(0)` hep tepe. ABI de farklı: `long double` argümanlar **yığında** (16 baytlık yuvalarda, `8(%rsp)` ve `24(%rsp)`) geliyor, sonuç x87 yığınının tepesinde dönüyor.

Hassasiyet farkını görelim:

```c
#include <stdio.h>
#include <float.h>

int main(void) {
    volatile double d = 1e308;
    volatile long double ld = 1e308L;
    printf("double:      1e308 * 10 / 10 = %g\n", d * 10 / 10);
    printf("long double: 1e308 * 10 / 10 = %Lg\n", ld * 10 / 10);
    printf("sizeof: float %zu, double %zu, long double %zu\n",
           sizeof(float), sizeof(double), sizeof(long double));
    printf("mantis bitleri: float %d, double %d, long double %d\n",
           FLT_MANT_DIG, DBL_MANT_DIG, LDBL_MANT_DIG);
    volatile double a = 0.1, b = 0.2;
    printf("0.1 + 0.2 = %.17g\n", a + b);
    return 0;
}
```

```
=== x86-64 Linux
double:      1e308 * 10 / 10 = inf
long double: 1e308 * 10 / 10 = 1e+308
sizeof: float 4, double 8, long double 16
mantis bitleri: float 24, double 53, long double 64
0.1 + 0.2 = 0.30000000000000004

=== arm64 macOS (Apple M2)
double:      1e308 * 10 / 10 = inf
long double: 1e308 * 10 / 10 = inf
sizeof: float 4, double 8, long double 8
mantis bitleri: float 24, double 53, long double 53
0.1 + 0.2 = 0.30000000000000004
```

- `double`'da `1e309` temsil edilemez (en büyük ~1.8e308, Ders 3.13), `inf` oluyor ve `inf / 10` hâlâ `inf`.
- x87'nin `long double`'ında üs 15 bit, en büyük değer ~1.2e4932: `1e309` sığıyor, bölünce `1e308`'e dönüyor.
- `sizeof(long double)` 16 ama mantis 64 bit: 80 bitlik sayı, hizalama için 16 bayta dolguyla (Ders 4.26).
- arm64 macOS'ta `long double` sadece `double`'ın başka bir adı. Taşınabilir kod `long double`'ın daha hassas olduğuna güvenemez.

32 bitlik eski x86 kodunda `double` hesaplar da x87 ile yapılıyordu. O zaman `d * 10 / 10` ara sonuç register'da kaldığı sürece `1e308`, belleğe yazılırsa `inf` verebiliyordu: aynı kod, optimizasyon seviyesine göre farklı sonuç. SSE'ye geçişin asıl kazancı bu **öngörülebilirlik**: her `double` işlemi tam 64 bitle yuvarlanıyor, sonuç her derlemede aynı (ve IEEE 754'ün istediği). `0.1 + 0.2`'nin iki makinede de aynı 17 basamağı vermesi bunun küçük bir kanıtı.

---

## 5. SIMD'ye köprü: paketlenmiş komutlar

`xmm` register'ları 128 bit, ama skaler komutlar sadece alt 32 ya da 64 bitini kullanıyor. Geri kalanı boşa mı? Hayır: **paketlenmiş** (packed) komutlar aynı register'daki 4 `float`'ı (ya da 2 `double`'ı) **tek komutla** işler. SSE'nin adındaki "SIMD" (single instruction, multiple data) bu.

```c
void olcekle(float *restrict a, int n, float k) { for (int i = 0; i < n; i++) a[i] *= k; }
```

`-O2` ile clang döngüyü **vektörleştirir** (otomatik vektörleştirme):

```
        shufps  $0, %xmm0, %xmm1          # k'yi xmm1'in 4 yuvasina da kopyala: [k,k,k,k]
        ...
        movups  (%rdi,%rsi), %xmm2        # a[i..i+3]: 4 float birden yukle
        movups  16(%rdi,%rsi), %xmm3      # a[i+4..i+7]
        mulps   %xmm1, %xmm2              # 4 carpma, tek komut
        mulps   %xmm1, %xmm3              # 4 carpma daha
        movups  %xmm2, (%rdi,%rsi)        # 4 float birden sakla
        movups  %xmm3, 16(%rdi,%rsi)
        ...
        mulss   %xmm0, %xmm1              # dongu sonu: 8'e bolunmeyen kalanlar tek tek
```

Vektörleştirme kapalıyken (`-fno-vectorize -fno-slp-vectorize -fno-unroll-loops`) sadece skaler `mulss` kalıyor. Bir `mulps` dört `mulss`'in işini yapıyor; döngü başına iki `mulps` ile her turda 8 eleman.

İki ayrıntı:

- **`restrict`** (Ders 7.21'deki aliasing): derleyicinin `a[i]`'ye yazmanın `k`'yi ya da başka bir `a[j]`'yi etkilemediğinden emin olması gerekiyor. Burada `k` değerle geçtiği için sorun yok, ama genel durumda `restrict` vektörleştirmeyi mümkün kılan bilgi.
- **Kalan döngü**: `n` 8'in katı değilse son elemanlar skaler komutlarla. Vektörleştirilmiş her döngünün bir "ana gövde + kuyruk" yapısı var.

Bugünkü x86-64 işlemcilerinde `xmm` register'ları 256 bitlik `ymm` (AVX) ve 512 bitlik `zmm` (AVX-512) register'larının alt yarısı: bir komutla 8 ya da 16 `float`. arm64'teki karşılığı NEON (`v0`–`v31`, 128 bit), Ders 7.23'teki `fadd.2d v0, ...` komutları. Faz 11'de bunları elle (intrinsic'lerle) kullanacak, ve Ders 7.26'daki matris çarpımını bu komutlarla yeniden yazacağız.

---

## Alıştırmalar

**1** – `double ortalama(double a, double b, double c) { return (a + b + c) / 3; }` için `-O2` assembly'sini tahmin et: hangi register'lar, hangi komutlar, `3` nerede duruyor? `/ 3` neden `* (1.0/3)`'e çevrilmiyor?

**2** – `float f(float x) { return x * 2.0; }` (sabitte `f` soneki yok) ile `float g(float x) { return x * 2.0f; }`'nin assembly'si farklı mı? Ders 3.7'deki dönüşüm kurallarıyla açıkla.

**3** – `int esit_mi(double a, double b) { return a == b; }`'yi gcc ile derle: `ucomisd`'den sonra tek bir `sete` değil, `setnp` ve bir `cmovne` görürsün. Neden tek bir `sete` yetmiyor? clang ise `ucomisd` hiç kullanmıyor; ne yapıyor?

**4** – x86-64'te `printf("%f", x)` gibi değişken argümanlı bir fonksiyona `double` geçerken, çağıran `%al` register'ına bir sayı yazar (Ders 7.17'deki `main`'de `__printf_chk` çağrısından önceki `mov $0x0,%eax`'i hatırla). Bu sayı ne?

**5** – Bölüm 5'teki `olcekle` fonksiyonunda `restrict`'i kaldırıp `void olcekle(float *a, int n, float *k)` (k artık işaretçi, döngüde `a[i] *= *k`) yapsan derleyici neden vektörleştirmekte zorlanır?

<details>
<summary>Cevaplar</summary>

**1** – `a`, `b`, `c` `xmm0`–`xmm2`'de; iki `addsd`, sonra `divsd` ile bellekteki `3.0` sabitine (`.LCPI0_0`, `%rip`'e göre) bölme; sonuç `xmm0`'da. `/ 3` ile `* (1.0/3)` aynı değil: `1.0/3` tam temsil edilemez (Ders 3.14), çarpma bir yuvarlama daha ekler ve son bit farklı çıkabilir. Derleyici sonucu değiştiren dönüşümleri `-ffast-math` (`-freciprocal-math`) olmadan yapmaz. 2'nin kuvvetlerine bölme ise (`/ 4` → `* 0.25`) tam olduğu için her zaman yapılır.

**2** – Farklı olabilir. `2.0` bir `double` sabiti; `x * 2.0` C kurallarına göre `x`'i `double`'a çevirip çarpar ve sonucu tekrar `float`'a yuvarlar: `cvtss2sd`, `mulsd`, `cvtsd2ss`. `2.0f` ile tek `mulss` (ya da derleyici `x + x`'e çevirir: `addss`). Ama burada derleyici akıllıdır: 2 ile çarpma tam olduğu için iki sürüm de aynı sonucu verir, ve clang ikisini de `addss %xmm0, %xmm0`'a indirir. `* 0.1` gibi tam olmayan bir sabitle fark gerçekten görünür.

**3** – `ucomisd` NaN'de `ZF = 1` yapar (Bölüm 3): sadece `sete` olsaydı `NaN == NaN` doğru çıkardı. "Eşit" demek için iki koşul gerekiyor: `ZF = 1` **ve** `PF = 0` (sıralanabilir). gcc 13:

```
        xorl    %eax, %eax
        ucomisd %xmm1, %xmm0
        movl    $0, %edx
        setnp   %al             # al = (PF == 0): ikisi de NaN degil
        cmovne  %edx, %eax      # ZF == 0 ise (esit degil) sonuc 0
```

clang 18 başka bir yol seçiyor: `cmpeqsd %xmm1, %xmm0` SSE'nin **maske** üreten karşılaştırması; eşitse `xmm0`'ın alt 64 bitini tamamen 1, değilse (NaN dahil) 0 yapar. Sonra `movq %xmm0, %rax; andl $1, %eax` ile maskeden 0/1 çıkarıyor. Bu maske biçimi Bölüm 5'teki paketlenmiş komutların karşılaştırma yöntemi: dört karşılaştırma, dört maske, sonra Ders 5.5'teki gibi dalsız seçim.

**4** – `%al`, `xmm` register'larında geçen kayan nokta argümanlarının **sayısı** (en fazla 8). Değişken argümanlı fonksiyon (`printf`) prologunda hangi argümanların nerede olduğunu bilmez; `al` 0 ise `xmm` register'larını kaydetmeyi atlayabilir. Bir `double` geçerken clang `movb $1, %al` yazıyor (`void yaz(double x) { printf("%f\n", x); }` derleyince). Ders 7.17'deki `printf` çağrısında `mov $0x0,%eax` vardı çünkü hiç kayan nokta argüman yoktu.

**5** – Artık `k` bellekte, `a` ile aynı bellekte olabilir: `olcekle(dizi, n, &dizi[5])` çağrısında `a[5] *= *k` yazması `*k`'yi değiştirir ve sonraki elemanlar **yeni** `k` ile çarpılmalıdır. Dört elemanı birden yükleyip aynı `k` ile çarpan vektör kod bu durumda yanlış olur. Derleyici ya vektörleştirmez, ya da çalışma anında "`k`, `a[0..n)` aralığında mı?" kontrolü ekleyip iki sürüm (vektör ve skaler) üretir. `float *restrict a, ..., const float *restrict k` bu belirsizliği kaldırır.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.11: kayan nokta kodu, SSE/AVX, ABI.
- Intel 64 and IA-32 Architectures Software Developer's Manual, Cilt 1, Bölüm 8 (x87) ve 10–11 (SSE/SSE2).
- David Monniaux, "The pitfalls of verifying floating-point computations" (ACM TOPLAS, 2008): x87'nin geniş ara hassasiyetinin yarattığı tutarsızlıklar.
- System V AMD64 ABI, Bölüm 3.2.3: `xmm` ve x87 ile parametre geçirme, değişken argümanlı fonksiyonlarda `%al`.

**Sıradaki ders:** Faz projesi: RISC-V emülatörü. C ile RV32I emülatörü yazma; kendi derlediğimiz programı içinde çalıştırma.
