---
title: "3.13 Özel float değerleri"
description: "Üs alanının iki ucu: sonsuz, NaN, iki ayrı sıfır ve denormal sayılar; sıfıra bölmenin float'ta neden program çökertmediği, kendine eşit olmayan sayı, kademeli alttan taşma ve iki float'ı == yerine bağıl hatayla karşılaştırmak."
---

Ders 3.8'de bir tamsayıyı sıfıra bölmenin undefined behavior olduğunu, x86'da programı çökerttiğini gördük. Aynısını float ile deneyelim:

```c
#include <stdio.h>

int main(void) {
    float zero = 0.0f;
    printf("%f\n", 1.0f / zero);
    printf("%f\n", -1.0f / zero);
    printf("%f\n", zero / zero);
    return 0;
}
```

```
inf
-inf
nan
```

Program çökmedi; üç tane tuhaf "sayı" yazdı. Ders 3.12'de üs alanının 0 ve 255 değerlerini özel durumlara ayırdığını söylemiştik. Bu derste o özel durumları açıyoruz.

---

## 1. Üssün iki ucu

32 bitlik bir float'ın üs alanı 8 bit: 0 ile 255 arası. Sıradan sayılar 1–254 aralığını kullanıyor. Kalan iki değer:

| Üs alanı | Mantis | Anlamı |
| --- | --- | --- |
| 1–254 | herhangi | Sıradan (normal) sayı: 1,mantis × 2^(üs − 127) |
| **255** | 0 | **±sonsuz** |
| **255** | 0 değil | **NaN** (not a number, sayı değil) |
| **0** | 0 | **±0** |
| **0** | 0 değil | **Denormal** sayı |

İşaret biti her satırda ayrıca var: sonsuzun da sıfırın da bir artı, bir eksi hali var. Ders 3.12'deki `show_float` ile bitlere bakalım:

```
inf          0 11111111 00000000000000000000000  üs  128  0x7F800000
-inf         1 11111111 00000000000000000000000  üs  128  0xFF800000
nan          0 11111111 10000000000000000000000  üs  128  0x7FC00000
-0           1 00000000 00000000000000000000000  üs -127  0x80000000
```

`show_float`'un "üs" sütunu burada bir şey ifade etmiyor: üs alanından 127 çıkarma kuralı sadece sıradan sayılar için geçerli. Bu satırlarda bakılması gereken, üs alanının bütün bitlerinin 1 ya da 0 olması.

Bu değerleri C'de yazmak için `<math.h>` başlığında `INFINITY` ve `NAN` sabitleri var; bir değerin ne olduğunu sormak için de `isinf`, `isnan` ve `isfinite`.

---

## 2. Sonsuz

IEEE 754'ün kuralı: sonucu en büyük float'ı aşan her işlem **sonsuz** verir. Sıfıra bölme bunun bir hali: 1 / 0, "0'a giderken 1 / x'in büyüdüğü yer". Aşma da aynı sonucu veriyor:

```c
printf("%f\n", FLT_MAX * 2.0f);
```

```
inf
```

Tamsayılarla büyük bir fark: Ders 3.8'de işaretsiz bir tamsayı taşınca **başa dönüyordu**, işaretli bir tamsayı taşınca undefined behavior oluyordu. Float taşınca ne başa döner ne de tanımsızdır: **sonsuza takılır** ve orada kalır.

Sonsuzla aritmetik, beklediğin gibi:

| İşlem | Sonuç |
| --- | --- |
| `inf + 1` | `inf` |
| `inf * 2` | `inf` |
| `1 / inf` | `0` |
| `-inf < -FLT_MAX` | doğru |

Sonsuz, hatayı **görünür** kılmanın bir yolu. Uzun bir hesabın ortasında bir taşma olursa sonuç sessizce anlamsız bir sayı olmaz, `inf` olarak sonuna kadar taşınır.

---

## 3. NaN: kendine eşit olmayan sayı

Bazı işlemlerin hiçbir anlamlı sonucu yok:

| İşlem | Sonuç |
| --- | --- |
| `0 / 0` | `nan` |
| `inf - inf` | `nan` |
| `inf * 0` | `nan` |
| `sqrtf(-1)` | `nan` |

NaN bulaşıcıdır: NaN ile yapılan her aritmetik işlem NaN verir. `nan + 1` = `nan`, `nan * 0` = `nan`. Hesabın bir yerinde NaN oluşursa, sonuca kadar yayılır.

En tuhaf özelliği karşılaştırmalarda:

```c
float n = zero / zero;
printf("%d %d %d %d\n", n == n, n != n, n < 1, n > 1);
```

```
0 1 0 0
```

**NaN, kendine bile eşit değil.** `n == n` yanlış, `n != n` doğru. NaN ile yapılan her `<`, `>`, `<=`, `>=` ve `==` karşılaştırması yanlış; sadece `!=` doğru. Mantığı şu: NaN bir sayı değil, "burada bir sayı yok" demek. "Hiçbir şey, hiçbir şeye eşit mi?" sorusunun güvenli cevabı "hayır".

Bu da bir değerin NaN olup olmadığını anlamanın en kısa yolunu veriyor:

```c
int is_nan(float x) {
    return x != x;
}
```

`<math.h>`'teki `isnan` da aynı işi yapar.

### NaN kontrolleri atlatır

NaN'ın asıl tehlikesi, aralık kontrollerinden **sessizce geçmesi**. Ders 2.13'teki gibi bir giriş kontrolü düşün:

```c
int valid_height(double h) {
    if (h < 0.5 || h > 2.5) {
        return 0;
    }
    return 1;
}
```

`h` NaN ise `h < 0.5` yanlış, `h > 2.5` de yanlış; fonksiyon **1** döndürüyor. NaN'lık bir boy, "geçerli" diye kabul edildi. Kontrolü "neyin geçersiz olduğu" yerine "neyin geçerli olduğu" üzerine kurmak bunu çözer:

```c
int valid_height(double h) {
    return h >= 0.5 && h <= 2.5;
}
```

NaN için iki karşılaştırma da yanlış, sonuç 0. Aynı mantıkla, iki sayının büyüğünü seçen `a > b ? a : b` gibi bir ifade de NaN'da **sırayla** değişen sonuçlar verir: `a` NaN ise `b`'yi, `b` NaN ise `b`'yi yani NaN'ı döndürür. Bilgisayarımızda denedik: `max(nan, 1)` 1 çıktı, `max(1, nan)` NaN.

### -ffast-math

clang ve GCC'nin `-ffast-math` ayarı, compiler'a "bu programda NaN ve sonsuz hiç olmayacak, kayan nokta kurallarını gevşetebilirsin" der. Kod biraz hızlanabilir, ama söz bozulursa sonuçlar tuhaflaşır. `-O2 -ffast-math` ile derleyince, NaN olduğu kesin bir değer için bile:

```
isnan=0 is_nan=0
```

Compiler, NaN olmayacağını varsaydığı için `isnan`'ı ve `x != x`'i "her zaman 0" diye derledi. Ders 3.8'de taşma kontrolünü silen mantığın aynısı. Bu ayarı kullanan bir projede NaN'ı kontrol etmenin güvenilir bir yolu kalmıyor.

---

## 4. İki sıfır

İşaret–büyüklük gösteriminin Ders 3.3'te söylediğimiz sorunu: **+0** (`0x00000000`) ve **−0** (`0x80000000`). IEEE 754 ikisini eşit sayar:

```c
float pz = 0.0f;
float nz = -0.0f;
printf("%d\n", pz == nz);
printf("%f %f\n", 1 / pz, 1 / nz);
```

```
1
inf -inf
```

Eşitler, ama aynı değiller: 1 / +0 = +sonsuz, 1 / −0 = −sonsuz. −0, "sıfıra negatif taraftan yaklaşmış ama oraya kadar küçülmüş" bir sayının hatırası. Örneğin çok küçük iki sayının çarpımı float'a sığmayacak kadar küçükse, sonuç işaretini koruyarak sıfıra yuvarlanır: `-1e-30f * 1e-30f` = **−0**.

Gündelik hayatta −0 en çok yazdırırken karşına çıkar:

```c
printf("%.1f\n", -0.04);
```

```
-0.0
```

−0,04 bir ondalık basamağa yuvarlanınca 0,0 oluyor, ama işaret kalıyor. Bir sıcaklık göstergesi "−0,0 °C" yazıyorsa sebebi bu. İşareti sormak için `<math.h>`'teki `signbit` var: `signbit(-0.0f)` sıfırdan farklı, `signbit(0.0f)` 0 döndürür.

---

## 5. Denormal sayılar

`FLT_MIN` en küçük pozitif **normal** float: 1,0 × 2⁻¹²⁶ ≈ 1,17549435 × 10⁻³⁸. Onu tekrar tekrar ikiye bölelim:

```c
float x = FLT_MIN;
for (int i = 0; i < 25; i++) {
    show_float(x);
    x = x / 2;
}
```

```
1.17549435e-38 0 00000001 00000000000000000000000  üs -126  0x00800000
5.87747175e-39 0 00000000 10000000000000000000000  üs -127  0x00400000
2.93873588e-39 0 00000000 01000000000000000000000  üs -127  0x00200000
1.46936794e-39 0 00000000 00100000000000000000000  üs -127  0x00100000
...
5.60519386e-45 0 00000000 00000000000000000000100  üs -127  0x00000004
2.80259693e-45 0 00000000 00000000000000000000010  üs -127  0x00000002
1.40129846e-45 0 00000000 00000000000000000000001  üs -127  0x00000001
0            0 00000000 00000000000000000000000  üs -127  0x00000000
```

`FLT_MIN`'den sonra üs alanı 0'a düştü, ama sayı hemen sıfır olmadı. Bunun yerine mantisteki 1, her bölmede bir basamak sağa kaydı. Üs alanı 0 olunca kurallar değişiyor:

$$
\text{denormal değer} = (-1)^{\text{işaret}} \times 0{,}\text{mantis}_2 \times 2^{-126}
$$

**Gizli bit yok**: başta 1 değil, 0 var. Üs de −127 değil, **−126**; `show_float`'un yazdığı −127 bu satırlarda yanlış. (Üs −127 olsaydı, `FLT_MIN`'den bir sonraki adıma geçerken sayı yarıya değil dörtte bire düşerdi.) Bu sayılara **denormal** (ya da subnormal) denir. En küçüğü, mantisin sadece son biti 1 olan sayı: 2⁻²³ × 2⁻¹²⁶ = 2⁻¹⁴⁹ ≈ **1,4 × 10⁻⁴⁵**. `<float.h>`'te adı `FLT_TRUE_MIN`. Ondan küçüğü sıfır.

Bedeli hassasiyet: denormal bir sayının anlamlı bitleri, baştaki sıfırlar yüzünden azalır. 0x00000001'in tek bir anlamlı biti var. Sayı sıfıra yaklaştıkça hassasiyet **kademeli** olarak kayboluyor; buna **kademeli alttan taşma** (gradual underflow) denir.

### Neden var?

Denormaller olmasaydı, `FLT_MIN`'in altındaki her sonuç doğrudan sıfır olurdu. O zaman şu olurdu:

```c
float a = 1.0e-38f;
float b = 1.1e-38f;
```

`a` ve `b` farklı sayılar; `a == b` yanlış. Ama `b - a` = 10⁻³⁹, `FLT_MIN`'den küçük. Denormaller olmasa bu fark **0** çıkardı: iki sayı eşit değil, ama farkları sıfır. `if (a != b) { … / (b - a) }` gibi bir kod sıfıra bölerdi. Denormallerle `b - a` = 1e-39 çıkıyor; bilgisayarımızda ölçtüğümüz sonuç bu.

IEEE 754 komitesinde denormalleri savunan kişi William Kahan'dı (Ders 3.14'teki toplama algoritmasının sahibi); bu garantiyi standarda koydurmak için uzun bir tartışma verdi.

**Hız notu.** Bazı işlemciler denormal sayılarla işlemi donanımda değil, yavaş bir yedek yolla yapar. Ses işleme ve oyun motorları gibi hızın önemli olduğu yerlerde, denormalleri sıfır sayan özel işlemci ayarları (flush-to-zero) açılır. Bu, yukarıdaki garantiyi bilerek bozmak demek.

---

## 6. İki float'ı karşılaştırmak

Ders 3.12'de `0.1 + 0.2 == 0.3`'ün yanlış çıktığını gördük. Hesaplanmış iki küsuratlı sayıyı `==` ile karşılaştırmak, yuvarlama hatalarının şansına kalmış demek. Çözüm: "eşit mi?" yerine "**yeterince yakın** mı?" diye sormak.

### Mutlak hata

İlk fikir: farkları küçük bir sayıdan küçükse eşit say.

```c
#include <math.h>

int close_abs(double a, double b) {
    return fabs(a - b) < 1e-9;
}
```

`fabs`, `<math.h>`'teki mutlak değer fonksiyonu (`double` için; `float` için `fabsf`). Linux'ta `<math.h>` fonksiyonlarını kullanan bir programı derlerken komutun sonuna `-lm` eklemen gerekebilir.

`close_abs(0.1 + 0.2, 0.3)` doğru çıkar. Ama 1e-9 sabiti, sayıların büyüklüğünden habersiz:

| `a` | `b` | `close_abs` | Gerçekte |
| --- | --- | --- | --- |
| 0,1 + 0,2 | 0,3 | 1 | Eşit sayılmalı |
| 10²⁰ | 10²⁰ + 16384 | **0** | Yan yana iki `double` |
| 10⁻¹² | 2 × 10⁻¹² | **1** | Biri diğerinin iki katı |

10²⁰ civarında iki `double` arasındaki en küçük adım 16.384 (Ders 3.14). Yan yana duran, sadece son biti farklı iki sayının farkı bile 1e-9'dan çok büyük; bu sayılar için `close_abs` asla "eşit" demez. Öte yandan 10⁻¹² civarında 1e-9 dev bir tolerans: birinin iki katı olan sayıyı bile eşit sayıyor.

### Bağıl hata

Daha iyi fikir: farkı, sayıların **büyüklüğüne göre** ölç. "İki sayı, büyük olanın milyarda biri kadar yakınsa eşittir."

> |a − b| ≤ max(|a|, |b|) × tolerans

Bu kural her ölçekte aynı şekilde çalışır; kayan noktanın kendisi gibi. Ama sıfırın yakınında çöker: bir sayıyı 0 ile karşılaştırırken max(|a|, |b|) = |a| olur ve kural "|a| ≤ |a| × tolerans" demeye döner; bu sadece a = 0 iken doğru. Ders 3.12'deki on tane 0,1'in toplamından 1 çıkarınca kalan −1,1 × 10⁻¹⁶'yı, bağıl hata hiçbir zaman 0'a "yakın" bulmaz.

### İkisi birlikte

Pratikte ikisini birleştiririz: sıfır yakını için mutlak bir taban, geri kalan her şey için bağıl tolerans.

```c
#include <math.h>

int nearly_equal(double a, double b, double rel_tol, double abs_tol) {
    double diff = fabs(a - b);
    if (diff <= abs_tol) {
        return 1;
    }
    double larger = fabs(a) > fabs(b) ? fabs(a) : fabs(b);
    return diff <= larger * rel_tol;
}
```

| Çağrı | Sonuç |
| --- | --- |
| `nearly_equal(0.1 + 0.2, 0.3, 1e-9, 0)` | 1 |
| `nearly_equal(1e20, 1e20 + 16384, 1e-9, 0)` | 1 |
| `nearly_equal(1e-12, 2e-12, 1e-9, 0)` | 0 |
| `nearly_equal(sum - 1.0, 0.0, 1e-9, 0)` | 0 |
| `nearly_equal(sum - 1.0, 0.0, 1e-9, 1e-12)` | 1 |

(`sum`, on tane 0,1'in `double` toplamı.) Python'un `math.isclose` fonksiyonu da tam olarak bu iki parametreyle çalışır.

**Toleransı nasıl seçeceksin?** Tek bir doğru cevap yok; hesabın ne kadar hata biriktirdiğine bağlı. Bir başlangıç noktası `<float.h>`'teki epsilon'lar: `FLT_EPSILON` ≈ 1,2 × 10⁻⁷ ve `DBL_EPSILON` ≈ 2,2 × 10⁻¹⁶, tek bir yuvarlamanın en fazla bağıl hatasının iki katı. Birkaç işlemden geçmiş bir `double` için bunun birkaç katı, çok uzun bir hesap için çok daha fazlası gerekir. `abs_tol` ise problemin birimlerine bağlı: metre cinsinden bir boy için 10⁻⁶ (bir mikron) anlamlı bir taban.

Bir de unutma: `nearly_equal`'e NaN verirsen bütün karşılaştırmalar yanlış olur ve 0 döner. NaN, yine hiçbir şeye "yakın" değil.

---

## Alıştırmalar

**1** – Bu ifadeler ne verir? Önce tahmin et, sonra dene. (`zero`, değeri `0.0f` olan bir `float`.)

- `1 / (1 / zero)`
- `-0.0f == 0.0f`
- `(zero / zero) == (zero / zero)`
- `FLT_MAX + 1.0f == FLT_MAX`
- `sqrtf(-0.0f)`

**2** – `<math.h>` kullanmadan, sadece aritmetik ve karşılaştırmayla bir `is_finite(float x)` yaz: `x` sıradan bir sayıysa (sonsuz ya da NaN değilse) 1 döndürsün. (İpucu: `x - x`'i düşün.)

**3** – Bölüm 5'teki tabloda en büyük denormal float görünmüyor. Bit deseni ne? `FLT_MIN` ile arasındaki fark ne kadar?

**4** – Bir arkadaşın şu fonksiyonla bir oyunda iki nesnenin çarpışıp çarpışmadığına bakıyor: `nearly_equal(x1, x2, 0, 0.1)`. Konumlar 0, 0,08 ve 0,16. Hangi çiftler "eşit"? Bu sonuç `==`'nin hangi özelliğini bozuyor?

**5** – Ders 2.13'teki sağlık hesaplayıcısını `double` ile yazdığını düşün. Kullanıcıdan boy okuyan kodun `scanf("%lf", &height)` ile `nan` ya da `inf` yazısını da sayı olarak kabul ettiğini öğrendin. Bölüm 3'teki `valid_height`'in iki halinden hangisi bu girdileri reddeder? `inf` için ne olur?

<details>
<summary>Cevaplar</summary>

**1** –

- `1 / (1 / zero)` = 1 / inf = **0**.
- `-0.0f == 0.0f` = **1**. İki sıfır eşit sayılır.
- `(zero / zero) == (zero / zero)` = **0**. İki NaN birbirine eşit değil.
- `FLT_MAX + 1.0f == FLT_MAX` = **1**. 1, `FLT_MAX`'ın yanında o kadar küçük ki toplama sonucu değiştirmiyor; en yakın float yine `FLT_MAX`. Taşma için `FLT_MAX`'a onun en küçük adımının yarısı kadar eklemen gerekir (yaklaşık 10³¹). Ders 3.14'te bu "yutulma"ya döneceğiz.
- `sqrtf(-0.0f)` = **−0**. Standart böyle tanımlıyor: −0'ın karekökü −0. NaN değil.

**2** –

```c
int is_finite(float x) {
    return x - x == 0.0f;
}
```

Sıradan bir sayı için `x - x` = 0. Sonsuz için `inf - inf` = NaN, NaN için de NaN; NaN == 0 yanlış. Dört değerle denedik: 1,5 → 1; inf, −inf ve NaN → 0. (`-ffast-math` ile bu da güvenilmez olur.)

**3** – Üs alanı 0, mantisin bütün bitleri 1: `0 00000000 11111111111111111111111` = **0x007FFFFF** ≈ 1,17549421 × 10⁻³⁸. `FLT_MIN` (0x00800000) ile farkı, tamsayı olarak bir sonraki desen olduğu için tam olarak en küçük adım: 2⁻¹⁴⁹ = `FLT_TRUE_MIN` ≈ **1,4 × 10⁻⁴⁵**. Normal sayılardan denormallere geçişte hiçbir boşluk yok; bütün aralık aynı adımla, eşit aralıklarla dolu.

**4** – 0 ile 0,08 eşit (fark 0,08), 0,08 ile 0,16 eşit (fark 0,08), ama 0 ile 0,16 **eşit değil** (fark 0,16). `==`'nin **geçişlilik** özelliği bozuldu: a = b ve b = c ise a = c olmalıydı. Toleranslı karşılaştırmaların hepsinde bu sorun var; "yakın" sayıları gruplamak ya da tekrar eden yakınlık zincirlerine güvenmek hatalara yol açar.

**5** – İlk hali (`h < 0.5 || h > 2.5`) NaN'ı **kabul eder**; ikinci hali (`h >= 0.5 && h <= 2.5`) reddeder. `inf` ise iki halde de reddedilir: `inf > 2.5` doğru, `inf <= 2.5` yanlış. Sonsuz bir sayıdır ve karşılaştırmalara normal katılır; sorun sadece NaN'da.

</details>

---

## Kaynaklar

- IEEE Std 754-2019, §6: sonsuz, NaN ve sıfırın işareti.
- David Goldberg, "What Every Computer Scientist Should Know About Floating-Point Arithmetic", *ACM Computing Surveys*, 1991, §2.2: özel değerler ve denormal sayılar.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.4.2–2.4.3: normal, denormal ve özel değerler.
- Bruce Dawson, "Comparing Floating Point Numbers, 2012 Edition", randomascii.wordpress.com.
- C standardı (ISO/IEC 9899:2018), §7.12: `<math.h>`, `isnan`, `isinf`, `signbit`; Ek F: IEEE 754 ile uyumlu kayan nokta.

**Sıradaki ders:** `double` ve hassasiyet. İki komşu float arasında ne kadar boşluk var, ve on milyon sayıyı hata biriktirmeden nasıl toplarız?
