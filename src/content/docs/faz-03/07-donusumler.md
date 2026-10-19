---
title: "3.7 Dönüşümler (cast)"
description: "Bir değer başka bir tamsayı tipine konduğunda ne olur? Örtük ve açık dönüşüm, cast'in önceliği, sıfırla ve işaretle genişletme, kırpma, işaret değiştirme; standardın kuralları, bit düzeyinde gösterim ve -Wconversion ile -fsanitize=implicit-conversion."
---

Önceki derslerde bir değeri başka bir tipe koyduğumuz her seferinde "kurallarını Ders 3.7'de göreceğiz" dedik:

- Ders 3.3: `signed char` −1, `unsigned char`'a konunca **255** oldu.
- Ders 3.4: 8.100.000.000, `uint32_t`'ye konunca **3.805.032.704** oldu.
- Ders 3.5: `uint8_t c = a + b;` satırında 300, **44** oldu; `short`'a konan 60.000 ise **−5.536**.
- Ders 3.6: −30, `size_t`'ye çevrilip bölündükten sonra `int`'e dönünce **1.431.655.755** oldu.

Bu derste hepsini tek bir kural setine bağlayacağız. Önce tek bir programda bütün durumlara bakalım:

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    int8_t  s = -1;
    uint8_t u = 255;
    int32_t from_s = s;
    int32_t from_u = u;
    uint32_t s_to_u32 = s;
    printf("%d %d %u\n", from_s, from_u, s_to_u32);

    int big = 300;
    uint8_t  t1 = big;
    int8_t   t2 = big;
    int8_t   t3 = 200;
    uint16_t t4 = 70000;
    int16_t  t5 = 40000;
    printf("%d %d %d %d %d\n", t1, t2, t3, t4, t5);

    unsigned int x = 3000000000u;
    int y = x;
    printf("%d\n", y);
    int neg = -1;
    unsigned int z = neg;
    printf("%u\n", z);
    uint8_t w = -1;
    printf("%d\n", w);
    return 0;
}
```

```
-1 255 4294967295
44 44 -56 4464 -25536
-1294967296
4294967295
255
```

`s` ile `u`'nun bitleri aynı (`11111111`), ama `int32_t`'ye konunca biri −1, öbürü 255 oluyor. `s`, `uint32_t`'ye konunca 4.294.967.295 oluyor. 300 hem `uint8_t`'de hem `int8_t`'de 44. Bütün bunların arkasında üç basit kural var.

---

## 1. Örtük ve açık dönüşüm

Bir değerin tipi iki şekilde değişebilir.

**Örtük dönüşüm** (implicit conversion): Sen bir şey yazmadan C'nin kendisinin yaptığı dönüşüm. Dört yerde olur:

- **Atama:** `uint8_t t1 = big;` sağ taraf sol tarafın tipine çevrilir.
- **Fonksiyon argümanı:** `uint8_t` parametresi olan bir fonksiyona `int` verirsen, argüman parametrenin tipine çevrilir (Ders 2.7'deki prototip bunu mümkün kılar).
- **`return`:** Döndürülen değer, fonksiyonun dönüş tipine çevrilir. Ders 3.6'daki `average` böyleydi.
- **Hesap ve karşılaştırma:** Ders 3.5'teki integer promotion ve usual arithmetic conversions.

**Açık dönüşüm** (explicit conversion), yani **cast**: Dönüşümü sen yazarsın. Parantez içinde bir tip adı, ardından değer:

```c
int big = 300;
uint8_t small = (uint8_t)big;
```

Cast iki şey söyler. Compiler'a: "bu dönüşümü bilerek yapıyorum." Kodu okuyan kişiye: "burada bir değer değişebilir, dikkat." Değişkenin kendisini değiştirmez; `big` hâlâ 300. Cast sadece **yeni bir değer** üretir.

### Cast'in önceliği

Cast, `*` ve `/`'dan **önce** uygulanır. Bu yüzden nereye yazdığın önemlidir. Ders 3.5'teki örneği hatırla:

```c
#include <stdio.h>

int main(void) {
    int big = 2000000000;
    long long a = (long long)big * 2;
    long long b = (long long)(big * 2);
    printf("%lld\n%lld\n", a, b);
    return 0;
}
```

`-fsanitize=undefined` ile:

```
prec.c:6:35: runtime error: signed integer overflow: 2000000000 * 2 cannot be represented in type 'int'
4000000000
-294967296
```

- `(long long)big * 2`: Önce `big`, `long long`'a çevrilir; sonra çarpma 64 bitle yapılır. Doğru.
- `(long long)(big * 2)`: Önce parantezin içi, yani **iki `int`'in** çarpımı hesaplanır. Taşma burada olur. Ardından zaten bozulmuş sonuç `long long`'a çevrilir. Cast işe yaramaz.

**Kural:** Cast, hesaptan **önce** genişletmek istediğin değerin hemen önüne yazılır, sonucun önüne değil.

---

## 2. Kural 1: Değer sığıyorsa korunur

Standardın ilk kuralı en basiti: **Değer yeni tipe sığıyorsa, değişmez.** `int8_t` −1, `int32_t`'ye konunca yine −1; `uint8_t` 255, `int32_t`'ye konunca yine 255. Dönüşümlerin büyük çoğunluğu bu kurala girer ve hiçbir sürpriz yaratmaz.

Peki bitlere ne oluyor? Küçük bir tipi büyük bir tipe çevirmek, **genişletmek** demektir: yeni tipte daha fazla bit var ve soldaki yeni bitlerin bir şeyle doldurulması gerekiyor. Ders 3.5'teki `movzx` ve `movsx`'i hatırla. Görmek için Ders 3.3'teki `print_bits`'i 32 bite genişletelim:

```c
#include <stdio.h>
#include <stdint.h>

void print_bits(uint32_t x, int width) {
    uint32_t w = 1;
    for (int i = 1; i < width; i++) {
        w = w * 2;
    }
    for (int i = width; i >= 1; i--) {
        putchar(x / w % 2 ? '1' : '0');
        if (i % 8 == 1 && i > 1) {
            putchar(' ');
        }
        w = w / 2;
    }
    putchar('\n');
}

int main(void) {
    uint8_t u = 240;
    int8_t  s = -16;
    printf("uint8_t  240: ");
    print_bits(u, 8);
    printf("uint32_t 240: ");
    print_bits((uint32_t)u, 32);
    printf("int8_t   -16: ");
    print_bits((uint8_t)s, 8);
    printf("int32_t  -16: ");
    print_bits((uint32_t)(int32_t)s, 32);
    return 0;
}
```

```
uint8_t  240: 11110000
uint32_t 240: 00000000 00000000 00000000 11110000
int8_t   -16: 11110000
int32_t  -16: 11111111 11111111 11111111 11110000
```

`print_bits`, en soldaki bitin basamak değerini (`width` bit için 2^(width − 1)) bulup Ders 3.3'teki gibi sağa doğru ilerliyor; her 8 bitte bir boşluk bırakıyor. Bitleri görmek istediğimiz değeri önce cast'lerle `uint32_t`'ye çeviriyoruz. Bu cast'lerin neden bitleri değiştirmediğini birazdan göreceğiz.

İki genişletme şekli:

- **Sıfırla genişletme** (zero extension): Kaynak tip **işaretsizse** soldaki yeni bitler 0 olur. 240, 240 olarak kalır.
- **İşaretle genişletme** (sign extension): Kaynak tip **işaretliyse** soldaki yeni bitler, en soldaki bitin (işaret bitinin) kopyasıyla dolar. Ders 3.3'teki ikiler tümleyeninde 8 bitlik −16 `11110000`, 32 bitlik −16 de `11111111 11111111 11111111 11110000`. Değer korunur.

`11110000` deseni iki satırda da aynı, ama genişletilmiş halleri farklı. Hangisinin uygulanacağını hedef tip değil, **kaynak tip** belirler.

---

## 3. Kural 2: İşaretsiz tipe sığmazsa, başa döner

Değer sığmıyorsa ve hedef tip **işaretsizse** standart sonucu kesin olarak tanımlar: Değer, hedef tipe sığana kadar ona **2ⁿ eklenir ya da 2ⁿ çıkarılır** (n, hedef tipin bit sayısı). Bu, Ders 3.3'teki sayacın ta kendisi: 255'ten sonra 0, 0'dan önce 255.

| Değer | Hedef | Hesap | Sonuç |
| --- | --- | --- | --- |
| 300 | `uint8_t` | 300 − 256 | **44** |
| 70.000 | `uint16_t` | 70.000 − 65.536 | **4.464** |
| −1 | `uint8_t` | −1 + 256 | **255** |
| −1 | `unsigned int` | −1 + 2³² | **4.294.967.295** |
| −1 (`int8_t`) | `uint32_t` | −1 + 2³² | **4.294.967.295** |

Bu tanım matematik diliyle yazılmış, ama ikiler tümleyeni kullanan bir makinede çok basit bir şeye karşılık gelir:

- **Büyük tipten küçüğe** (daraltma): Sadece **sağdaki n bit** tutulur, gerisi atılır. Buna **kırpma** (truncation) denir.
- **Küçük işaretli tipten büyük işaretsiz tipe:** Önce işaretle genişletilir, sonra bitler işaretsiz okunur.
- **Aynı boyutta işaretliden işaretsize:** Bitlere **hiç dokunulmaz**, sadece okunuşları değişir.

300'ün kırpılması:

```
int      300: 00000000 00000000 00000001 00101100
uint8_t   44: 00101100
```

Soldaki üç byte atıldı; kalan `00101100` = 32 + 8 + 4 = 44. "300 − 256" hesabıyla aynı sonuç. Atılan bitlerde sadece 256'nın biti vardı.

`print_bits`'teki cast'ler bu yüzden güvenli: `(uint8_t)s` −16'nın bitlerine dokunmuyor, `(uint32_t)(int32_t)s` de önce işaretle genişletiyor, sonra bitleri olduğu gibi işaretsiz okuyor.

---

## 4. Kural 3: İşaretli tipe sığmazsa, platforma bağlı

Değer sığmıyorsa ve hedef tip **işaretliyse** standart sonucu **tanımlamaz**: sonuç **implementation-defined**, yani platforma bırakılmıştır. Bu, Ders 2.12'deki undefined behavior'dan farklıdır. Program bozulmaz, ama sonucun ne olacağını standart değil compiler belirler ve compiler bunu belgelemek zorundadır.

Pratikte bugünkü bütün compiler'lar aynı şeyi yapar: Kural 2'deki gibi **bitleri kırpar** ve sonucu ikiler tümleyeniyle okur. clang ile:

| Değer | Hedef | Sağdaki bitler | Sonuç |
| --- | --- | --- | --- |
| 300 | `int8_t` | `00101100` | **44** |
| 200 | `int8_t` | `11001000` | **−56** |
| 40.000 | `int16_t` | `10011100 01000000` | **−25.536** |
| 3.000.000.000 (`unsigned int`) | `int` | aynı 32 bit | **−1.294.967.296** |

Ders 3.5'teki `short sum = h + h;` satırının −5.536 vermesinin sebebi buydu. Ders 3.6'daki 1.431.655.755 de aynı kuralın sonucu: 6.148.914.691.236.517.195'in sağdaki 32 biti.

**Bir ayrıma dikkat:** `int8_t t2 = 300;` platforma bağlı ama **tanımlı**; `INT_MAX + 1` ise undefined behavior. Fark, dönüşüm ile aritmetik arasında: işaretli bir **hesabın** taşması UB'dir, işaretli bir tipe **dönüşüm** ise değildir.

### char'ın işareti

Ders 3.2'de `char`'ın bazı platformlarda işaretli, bazılarında işaretsiz olduğunu görmüştük. Kural 1 ve 3 burada birleşir:

```c
char c = (char)200;
int as_int = c;
```

- macOS ve x86 Linux'ta `char` işaretli: 200, Kural 3 ile −56 olur; `int`'e işaretle genişletilir: **−56**.
- ARM Linux'ta `char` işaretsiz: 200 sığar; `int`'e sıfırla genişletilir: **200**.

clang'in iki platform için ürettiği assembly'de de bu var: x86-64 Linux için fonksiyon −56, ARM Linux için 200 döndürüyor. Byte'larla çalışırken `char` değil, `uint8_t` kullanmamızın bir sebebi daha (Ders 3.4).

---

## 5. Kuralların özeti

| Durum | Standardın kuralı | Bitlere ne olur? |
| --- | --- | --- |
| Değer sığıyor | Değer korunur | İşaretsiz kaynak: sıfırla genişletme. İşaretli kaynak: işaretle genişletme. |
| Sığmıyor, hedef işaretsiz | 2ⁿ ekle ya da çıkar (tanımlı) | Kırpma, ya da aynı bitleri işaretsiz okuma |
| Sığmıyor, hedef işaretli | Platforma bağlı (implementation-defined) | Pratikte: kırpma ve ikiler tümleyeniyle okuma |

Sıranın önemli olduğu bir örnekle bitirelim. Aynı byte, iki farklı yoldan `uint32_t`'ye gidiyor:

```c
int8_t sbyte = -16;
uint32_t b = sbyte;
uint32_t c = (uint8_t)sbyte;
```

- `b`: `int8_t` → `uint32_t`. İşaretle genişletilir: **4.294.967.280**.
- `c`: önce `int8_t` → `uint8_t` (bitler aynı, 240), sonra `uint8_t` → `uint32_t`. Sıfırla genişletilir: **240**.

Bir byte'ı "0–255 arası bir sayı" olarak büyük bir tipe taşımak istiyorsan, önce `uint8_t`'ye çevir. Faz 5'te bitlerle çalışırken bu kalıbı çok kullanacağız.

---

## 6. Dönüşümleri yakalamak

Programın başındaki koda `-Wall -Wextra` ile sadece **üç** uyarı geldi:

```
warning: implicit conversion from 'int' to 'int8_t' (aka 'signed char') changes value from 200 to -56 [-Wconstant-conversion]
warning: implicit conversion from 'int' to 'uint16_t' (aka 'unsigned short') changes value from 70000 to 4464 [-Wconstant-conversion]
warning: implicit conversion from 'int' to 'int16_t' (aka 'short') changes value from 40000 to -25536 [-Wconstant-conversion]
```

Üçü de **sabit** sayılar için. `uint8_t t1 = big;` gibi bir değişkenden gelen kırpılmalar ve `uint8_t w = -1;` için hiçbir şey yok. Ders 3.6'daki `-Wsign-compare`'in tersi: bu sefer compiler sabitleri yakalıyor, değişkenleri değil.

### -Wconversion

`-Wconversion`, `-Wall` ve `-Wextra`'ya dahil olmayan bir uyarı grubu. Değer kaybedebilecek **her** örtük dönüşümü raporlar:

```sh
clang -std=c17 -Wall -Wextra -Wconversion conv.c -o conv
```

Aynı programa dokuz uyarı geldi; bazıları:

```
implicit conversion loses integer precision: 'int' to 'uint8_t' (aka 'unsigned char') [-Wimplicit-int-conversion]
implicit conversion changes signedness: 'int8_t' (aka 'signed char') to 'uint32_t' (aka 'unsigned int') [-Wsign-conversion]
implicit conversion changes signedness: 'int' to 'unsigned int' [-Wsign-conversion]
```

İki çeşit var: "precision" uyarısı büyük tipten küçüğe (kırpma), "signedness" uyarısı işaretliden işaretsize ya da tersine. Uyarıyı susturmanın doğru yolu, dönüşümü düşünüp **cast ile açıkça yazmaktır**: `uint8_t t1 = (uint8_t)big;`. Bu, "evet, kırpılabileceğini biliyorum" demek. Değer kaybetmemesi gerekiyorsa da uyarı sana bir hatayı göstermiş demektir.

`-Wconversion` çok gürültülü olabilir; bu yüzden `-Wall`'a dahil değil. Ama küçük tiplerle (`uint8_t`, `int16_t`…) çalışan bir kodda açmaya değer.

### -fsanitize=implicit-conversion

Uyarılar derleme sırasında çalışır; değerleri bilemez. clang'in bir sanitizer'ı dönüşümleri **çalışma sırasında** izler ve değer gerçekten değiştiğinde haber verir:

```c
#include <stdio.h>
#include <stdint.h>

uint8_t brighten(uint8_t level, int amount) {
    return level + amount;
}

int main(void) {
    printf("%d\n", brighten(100, 50));
    printf("%d\n", brighten(200, 100));
    return 0;
}
```

```sh
clang -std=c17 -Wall -Wextra -g -fsanitize=implicit-conversion san.c -o san
```

```
san.c:5:12: runtime error: implicit conversion from type 'int' of value 300 (32-bit, signed) to type 'uint8_t' (aka 'unsigned char') changed the value to 44 (8-bit, unsigned)
150
44
```

İlk çağrıda 150 sığdığı için rapor yok; ikincisinde 300, 44'e dönüştüğü anda sanitizer satırı ve değerleri gösteriyor. Bu bir undefined behavior değil, bu yüzden `-fsanitize=undefined` buna bakmaz; ayrıca istemen gerekir. (Bu sanitizer GCC'de yok; clang'e özel.)

---

## Alıştırmalar

**1** – Çalıştırmadan her değişkenin değerini bul. Sonra bir programla kontrol et.

```c
uint8_t  a = 513;
int8_t   b = 128;
uint16_t c = -2;
int32_t  d = (int8_t)200;
uint32_t e = (int8_t)-2;
int      f = (uint8_t)-2;
```

**2** – Aşağıdaki iki satırdan hangisi doğru sonucu verir? `a` ve `b` 100.000 değerinde iki `int`.

```c
int64_t p = (int64_t)(a * b);
int64_t q = (int64_t)a * b;
```

**3** – Bölüm 6'daki `brighten` fonksiyonunu, sonuç 255'i geçerse 255, 0'ın altına inerse 0 döndürecek şekilde yeniden yaz. (Bu davranışa **doyma**, saturation, denir: resim işlemede bir pikseli parlatırken beyazı geçemezsin.) Hiç örtük daraltma kalmasın; `-Wconversion` ile uyarısız derlensin.

**4** – Ders 3.5'teki 5. alıştırmanın `average` fonksiyonunu `-Wall -Wextra -Wconversion` ile derle:

```c
uint8_t average(uint8_t values[], int count) {
    uint8_t total = 0;
    for (int i = 0; i < count; i++) {
        total = total + values[i];
    }
    return total / count;
}
```

Hangi satırlar için uyarı geliyor? Asıl hata hangi satırdaydı? Bu sana ne söylüyor?

**5** – Bir sensör, sıcaklığı tek bir byte olarak gönderiyor: değer ikiler tümleyeniyle yazılmış, −128 ile 127 °C arasında bir sayı. Byte'ı `uint8_t raw` olarak aldın; değeri 231. Sıcaklık kaç derece? Bunu bir `int`'e doğru olarak nasıl çevirirsin?

<details>
<summary>Cevaplar</summary>

**1** –

- `a` = **1**. 513 − 2 × 256. Sağdaki 8 bit: 513 = `10 00000001`.
- `b` = **−128**. 128 `int8_t`'ye sığmaz; bitleri `10000000`, ikiler tümleyeninde −128. (Kural 3, platforma bağlı.)
- `c` = **65.534**. −2 + 65.536.
- `d` = **−56**. Önce 200 → `int8_t`: −56. Sonra `int32_t`'ye: sığıyor, korunur.
- `e` = **4.294.967.294**. −2 bir `int8_t`; `uint32_t`'ye işaretle genişletilip işaretsiz okunur: −2 + 2³².
- `f` = **254**. −2 → `uint8_t`: 254. Sonra `int`'e: sığıyor, korunur.

**2** – **`q`**. `p`'de cast parantezin dışında: `a * b` iki `int` ile hesaplanır, 10.000.000.000 `int`'e sığmaz ve undefined behavior olur. `q`'da `a` önce `int64_t`'ye çevrilir, `b` de usual arithmetic conversions ile `int64_t` olur ve çarpma 64 bitle yapılır.

**3** –

```c
uint8_t brighten(uint8_t level, int amount) {
    int result = level + amount;
    if (result > 255) {
        return 255;
    }
    if (result < 0) {
        return 0;
    }
    return (uint8_t)result;
}
```

Hesap `int` ile yapılıyor; sonuç `uint8_t`'ye ancak sınırları kontrol ettikten sonra konuyor. Son satırdaki cast'in değeri değiştirmeyeceğini artık biliyoruz; cast bunu okuyana ve compiler'a söylüyor. (`level + amount` da `int` ile `int`'in toplamı olduğu için taşma riski var mı? `amount` çok büyükse evet. Gerçek bir kütüphanede `amount`'un aralığı da kontrol edilir.)

**4** – clang sadece `return total / count;` için uyarır:

```
warning: implicit conversion changes signedness: 'int' to 'uint8_t' (aka 'unsigned char') [-Wsign-conversion]
```

Asıl hata ise döngüdeki `total = total + values[i];` satırındaydı: 255'i geçen toplam her adımda kırpılıyordu. clang, `total + values[i]` gibi iki tarafı da hedefle aynı küçük tipte olan ifadeler için bu uyarıyı bilerek vermiyor; bu kalıp çok yaygın ve çoğu zaman bilerek yazılıyor. Ders: **`-Wconversion` da her şeyi yakalamaz.** Uyarılar, sanitizer'lar ve testler birbirinin kör noktasını kapatır (Ders 2.12'deki iki sanitizer gibi). Bu hatayı çalışma sırasında `-fsanitize=implicit-conversion` yakalardı.

**5** – **−25 °C.** 231, `int8_t`'ye sığmaz; bitleri `11100111`, ikiler tümleyeninde 231 − 256 = −25. Çevirmek için:

```c
int temperature = (int8_t)raw;
```

Önce `int8_t`'ye çeviriyoruz (bitler aynı kalır, artık işaretli okunuyor: −25), sonra `int`'e (işaretle genişletilir, −25 korunur). `int temperature = raw;` yazsaydık sıfırla genişletilir ve 231 °C olurdu. Bu cast Kural 3'e, yani platforma bağlı davranışa dayanıyor; bugünkü bütün compiler'larda doğru çalışır. Tamamen taşınabilir bir yol: `int temperature = raw < 128 ? raw : raw - 256;`

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §6.3.1.3: işaretli ve işaretsiz tamsayılar arasındaki dönüşümler (üç kural); §6.5.4: cast operatörü.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.2.4–2.2.7: işaretli ve işaretsiz arasında dönüşüm, genişletme ve kırpma.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 3: dönüşümler.
- [Clang UndefinedBehaviorSanitizer belgesi](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html): `-fsanitize=implicit-conversion`.

**Sıradaki ders:** Taşma. İşaretsiz tiplerde tanımlı, işaretlilerde undefined behavior; taşmayı olmadan önce yakalamak.
