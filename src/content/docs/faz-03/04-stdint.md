---
title: "3.4 stdint.h"
description: "Boyutu her platformda aynı olan tamsayı tipleri: int8_t'den uint64_t'ye tam genişlikli tipler, least ve fast tipleri, inttypes.h ile yazdırmak; size_t, ptrdiff_t ve intptr_t; hangi tipin ne zaman seçileceği."
---

Ders 3.2'nin sonunda rahatsız edici bir tabloyla kalmıştık: `int` Arduino'da 2 byte, bilgisayarında 4 byte; `long` Linux'ta 8 byte, Windows'ta 4 byte. Bir sayının **tam olarak** kaç bit olduğunu bilmen gereken yerler ise az değil:

- Bir dosya formatı "ilk 4 byte genişlik, sonraki 4 byte yükseklik" diyorsa.
- Bir ağ paketinin başlığında 16 bitlik bir port numarası varsa.
- Ders 3.3'teki gibi bitlerle çalışıyorsan ve en soldaki bitin hangisi olduğunu bilmen gerekiyorsa.

C99 standardı bu iş için `<stdint.h>` başlık dosyasını getirdi. İçindeki tiplerin adı, boyutlarını açıkça söyler.

---

## 1. Tam genişlikli tipler

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    int8_t temperature = -12;
    uint8_t brightness = 255;
    int32_t balance = -150000;
    uint64_t population = 8100000000;

    printf("%d %d %d\n", temperature, brightness, balance);
    printf("%zu %zu %zu %zu\n", sizeof(temperature), sizeof(brightness), sizeof(balance), sizeof(population));
    return 0;
}
```

```
-12 255 -150000
1 1 4 8
```

İsimlerin okunuşu:

| Parça | Anlamı |
| --- | --- |
| `int` / `uint` | işaretli / işaretsiz (**u**nsigned) |
| `8`, `16`, `32`, `64` | tam olarak kaç bit |
| `_t` | "type": bunun bir tip adı olduğunu hatırlatan ek |

Böylece sekiz tip elde ederiz:

| İşaretli | Aralık | İşaretsiz | Aralık |
| --- | --- | --- | --- |
| `int8_t` | −128 … 127 | `uint8_t` | 0 … 255 |
| `int16_t` | −32.768 … 32.767 | `uint16_t` | 0 … 65.535 |
| `int32_t` | yaklaşık ±2,1 milyar | `uint32_t` | 0 … yaklaşık 4,3 milyar |
| `int64_t` | yaklaşık ±9,2 × 10¹⁸ | `uint64_t` | 0 … yaklaşık 1,8 × 10¹⁹ |

Bu tiplerin iki güçlü garantisi var:

- **Tam olarak** o kadar bit. Ne fazla ne eksik. `int16_t` Arduino'da da, bilgisayarında da, Windows'ta da 16 bit.
- İşaretli olanlar **ikiler tümleyeni** kullanır (Ders 3.3). Eski standartlarda `int` için bu bile garanti değildi; `int8_t` için hep garantiydi.

Aralıkları `<limits.h>`'teki gibi isimlerle de alabilirsin: `INT8_MIN`, `INT8_MAX`, `UINT8_MAX`, … `INT64_MAX`, `UINT64_MAX`.

**Bunlar yeni tipler değil.** `<stdint.h>`, var olan tiplere yeni **isimler** verir. Senin bilgisayarında `int8_t` aslında `signed char`, `int32_t` aslında `int`'tir. Ama hangi ismin hangi tipe karşılık geldiğine her platform kendisi karar verir: Arduino'da `int32_t`, `long`'un takma adıdır, çünkü orada 32 bit olan tip `long`. Sen hep `int32_t` yazarsın, doğru tipi seçmek platformun işi olur. (Bir tipe takma ad vermeyi Ders 3.21'de `typedef` ile kendimiz de yapacağız.)

**Bir istisna.** Tam genişlikli tipler sadece platformda o boyutta bir tip **varsa** tanımlıdır. Bazı sinyal işlemcilerinde en küçük birim 16 bittir ve 8 bitlik bir tip yoktur; orada `int8_t` de yoktur. Bugünkü bilgisayarlarda ve mikrodenetleyicilerde dördü de vardır.

---

## 2. Bu tipleri yazdırmak: inttypes.h

Küçük tiplerde sorun yok: `int8_t`, `uint8_t`, `int16_t` ve `uint16_t`, `printf`'e verilirken zaten `int`'e çevrilir (nedenini Ders 3.5'te göreceğiz), yani `%d` yeterli. Peki `int64_t` için hangi biçim?

Senin bilgisayarında (macOS) `int64_t`, `long long`'un takma adıdır; doğru biçim `%lld`. Ama 64 bit Linux'ta `int64_t`, `long`'un takma adıdır ve doğru biçim `%ld`. İkisi de 8 byte, ama farklı tipler; yanlış olanı kullanırsan `-Wall` uyarır. Aynı kod iki platformda birden nasıl doğru olacak?

`<inttypes.h>`, her platform için doğru harfleri hazır verir:

```c
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

int main(void) {
    printf("int32_t:  %zu byte, %" PRId32 " ile %" PRId32 " arası\n", sizeof(int32_t), INT32_MIN, INT32_MAX);
    printf("uint32_t: %zu byte, 0 ile %" PRIu32 " arası\n", sizeof(uint32_t), UINT32_MAX);
    printf("int64_t:  %zu byte, %" PRId64 " ile %" PRId64 " arası\n", sizeof(int64_t), INT64_MIN, INT64_MAX);
    printf("uint64_t: %zu byte, 0 ile %" PRIu64 " arası\n", sizeof(uint64_t), UINT64_MAX);
    return 0;
}
```

```
int32_t:  4 byte, -2147483648 ile 2147483647 arası
uint32_t: 4 byte, 0 ile 4294967295 arası
int64_t:  8 byte, -9223372036854775808 ile 9223372036854775807 arası
uint64_t: 8 byte, 0 ile 18446744073709551615 arası
```

İlk bakışta tuhaf görünüyor; parçalara ayıralım:

- `PRId64` → "**PR**int**f**'te bir **i**nt64_t'yi **d** ile yazdırmak için gereken harfler." macOS'ta bu `"lld"`, Linux'ta `"ld"` yazısıdır. `PRIu64` aynı şeyin **u**nsigned hali.
- `"%" PRId64 " arası"` → C, yan yana yazılmış yazıları tek bir yazı olarak birleştirir. macOS'ta bu ifade `"%lld arası"` olur, Linux'ta `"%ld arası"`.

Biraz çirkin, ama platformdan bağımsız doğru olan yol bu. Ders 2.8'deki faktöriyeli `uint64_t` ile yazalım:

```c
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>

uint64_t factorial(int n) {
    uint64_t result = 1;
    for (int i = 2; i <= n; i++) {
        result = result * i;
    }
    return result;
}

int main(void) {
    for (int n = 19; n <= 22; n++) {
        printf("%d! = %" PRIu64 "\n", n, factorial(n));
    }
    return 0;
}
```

```
19! = 121645100408832000
20! = 2432902008176640000
21! = 14197454024290336768
22! = 17196083355034583040
```

İşaretsiz olduğu için Ders 3.2'deki gibi negatif bir sayı çıkmadı; ama 21! ve 22! yine **yanlış**. 21! = 51.090.942.171.709.440.000, 2⁶⁴'ü aşıyor. Ders 3.3'te gördüğümüz gibi işaretsiz tiplerde taşan bitler sessizce atılır. Sanitizer da susar, çünkü bu tanımlı bir davranış. İşaretsiz olmak overflow'u engellemez, sadece **görünmez** yapar.

---

## 3. least ve fast tipleri

`<stdint.h>`'te iki aile daha var. İkisi de "**en az** N bit" der; tam genişlikli tiplerden farkları budur.

- **`int_leastN_t`**: En az N bit olan tiplerin **en küçüğü**. Tam genişlikli tipler olmayabilir ama bunlar her platformda vardır. 8 bitlik tipi olmayan bir sinyal işlemcisinde `int_least8_t` 16 bit olur.
- **`int_fastN_t`**: En az N bit olan tiplerin **en hızlısı**. Hangisinin en hızlı olduğuna platform karar verir.

İkisinin de `uint_` ile başlayan işaretsiz halleri var. Platforma göre neler seçildiğine bakalım:

| Tip | macOS (Apple Silicon) | Linux, 64 bit (glibc) |
| --- | --- | --- |
| `int_least16_t` | 2 byte | 2 byte |
| `int_fast8_t` | 1 byte | 1 byte |
| `int_fast16_t` | 2 byte | **8 byte** |
| `int_fast32_t` | 4 byte | **8 byte** |

Linux'taki C kütüphanesi, 64 bit işlemcinin 64 bitlik sayılarla en rahat çalıştığına karar vermiş ve 16 bit "hızlı" bir sayıya 8 byte ayırmış. Apple farklı karar vermiş. Hangisinin gerçekten daha hızlı olduğu duruma göre değişir; Faz 11'de performansı ölçerken bu tür kararların ne kadar ince olduğunu göreceğiz.

Pratikte bu iki aileyi nadiren göreceksin. Çok farklı donanımlarda çalışması gereken kütüphanelerde ve gömülü sistemlerde işe yararlar.

---

## 4. size_t: boyutların tipi

Ders 3.1'de `sizeof`'u `%zu` ile yazdırmıştık ve nedenini bu derse bırakmıştık. `sizeof`'un sonucu `int` değil, **`size_t`** tipindedir.

`size_t`, bellekteki **herhangi bir nesnenin boyutunu** tutabilecek kadar büyük, **işaretsiz** bir tamsayı tipidir. Bir boyut negatif olamayacağı için işaretsiz; bellekteki en büyük nesne kadar sayabilmesi gerektiği için de boyutu platforma göre değişir:

| Platform | `sizeof(size_t)` |
| --- | --- |
| 64 bit (macOS, Linux, Windows) | 8 byte |
| 32 bit | 4 byte |
| Arduino Uno | 2 byte |

`%zu`'daki `z`, "size_t boyutunda", `u` da "unsigned" demektir.

Bir şeyin **boyutunu**, **eleman sayısını** ya da **indeksini** tutarken doğal tip `size_t`'dir. Standart kütüphane de bu kuralı izler: Faz 4'te yazacağımız `strlen`, bir yazının uzunluğunu `size_t` olarak döndürür.

```c
#include <stdio.h>

int main(void) {
    int scores[] = {70, 85, 60, 90, 75};
    size_t count = sizeof(scores) / sizeof(scores[0]);

    for (size_t i = 0; i < count; i++) {
        printf("scores[%zu] = %d\n", i, scores[i]);
    }
    return 0;
}
```

```
scores[0] = 70
scores[1] = 85
scores[2] = 60
scores[3] = 90
scores[4] = 75
```

`size_t` için `<stdint.h>` gerekmez; `<stdio.h>` ya da `<stddef.h>` getirir.

**Bir uyarı.** İşaretsiz olduğu için `size_t` asla negatif olmaz. Bu, geriye doğru sayan bir döngüde tuzağa dönüşür: `for (size_t i = count - 1; i >= 0; i--)` döngüsü **hiç bitmez**, çünkü `i >= 0` her zaman doğrudur; `i` 0'dan sonra Ders 3.3'teki gibi en büyük değere döner. Bu tuzağı ve işaretli ile işaretsiz sayıların karşılaştırılmasını Ders 3.6'da ayrıntılı göreceğiz.

---

## 5. ptrdiff_t ve intptr_t

İki tip daha var ve ikisi de Faz 4'teki **pointer**'larla, yani bellek adresleriyle ilgili. Şimdilik sadece tanış:

- **`ptrdiff_t`** (`<stddef.h>`): Bellekteki iki konum arasındaki **farkı** tutan **işaretli** tip. Fark negatif olabileceği için işaretli. Yazdırmak için `%td`.
- **`intptr_t`** ve **`uintptr_t`** (`<stdint.h>`): Bir bellek adresini bir **tamsayı olarak** tutabilecek kadar büyük tipler. Adresler üzerinde aritmetik yapmak ya da bir adresin bitlerine bakmak için kullanılır.

64 bitlik bir bilgisayarda üçü de 8 byte.

---

## 6. Hangisi ne zaman?

| Durum | Tip |
| --- | --- |
| Genel amaçlı sayılar, sayaçlar | `int` |
| Bir boyut, eleman sayısı ya da array indeksi | `size_t` |
| ±2 milyarı aşabilecek sayılar | `int64_t` |
| Dosya formatları, ağ paketleri, donanım | tam genişlikli tipler: `uint8_t`, `uint16_t`, `uint32_t`… |
| Bitlerle çalışmak (Faz 5) | işaretsiz tam genişlikli tipler: `uint32_t`, `uint64_t` |
| Bellekte çok sayıda küçük değer | `uint8_t`, `int16_t` |
| Bir byte, bir ham veri birimi | `uint8_t` |

Ders 3.2'deki "2 milyarı aşan sayılar için `long long`" önerisi hâlâ doğru, ama `int64_t` niyetini daha açık söyler: "bu sayı tam olarak 64 bit". Bu kitapta bundan sonra büyük sayılar için `int64_t` kullanacağız.

`int`'i bırakmak için bir sebep yok. Normal hesaplarda `int` hâlâ en doğal seçim; `<stdint.h>`'teki tipler, **boyutun önemli olduğu** yerler için.

---

## Alıştırmalar

**1** – Aşağıdakiler için hangi tipi seçerdin?

- a) Bir rengin kırmızı, yeşil ve mavi bileşenlerinin her biri (0–255)
- b) 1 Ocak 1970'ten bu yana geçen saniye sayısı
- c) Bir dosyanın byte cinsinden boyutu
- d) −40 °C ile 125 °C arasını ölçen bir sıcaklık sensörünün değeri
- e) Ders 2.4'teki labirent haritasının bir kutusu

**2** – Bölüm 1'deki programda `population`'ı `uint32_t` yapıp çalıştır. Ne oldu? Neden? Compiler bir şey söyledi mi?

**3** – Ders 3.2'deki faktöriyel programını `int64_t` ve `PRId64` ile yeniden yaz. 21! için çıktıyı Ders 3.2'deki `long long` sürümüyle karşılaştır.

**4** – Bir arkadaşın `int64_t` bir değişkeni `%lld` ile yazdırıyor ve "benim bilgisayarımda çalışıyor, uyarı da yok" diyor. Haklı mı? Kodu hangi platformda derlersek sorun çıkar?

**5** – Aşağıdaki döngü ne yazdırır? Çalıştırmadan önce düşün, sonra dene. (Sonsuz döngüden çıkmak için `Ctrl+C`.)

```c
for (size_t i = 3; i >= 0; i--) {
    printf("%zu\n", i);
}
```

Döngüyü, aynı sırayla 3, 2, 1, 0 yazdıracak ve yine `size_t` kullanacak şekilde düzelt.

<details>
<summary>Cevaplar</summary>

**1** –

- a) **`uint8_t`.** Tam olarak 0–255. Bir resimde milyonlarca piksel ve her pikselde üç bileşen olduğu için 1 byte'lık tip bellekte büyük fark yaratır.
- b) **`int64_t`.** Ders 3.2'deki 2038 problemi tam olarak bu sayının 32 bite sığmamasından doğuyor. İşaretli seçilir, çünkü 1970'ten önceki tarihler negatif sayılarla gösterilir.
- c) **`size_t`** düşünülebilir. (Standart kütüphanenin dosya fonksiyonlarının kendi tipleri var; Faz 10'da göreceğiz.)
- d) **`int8_t`.** −40 ile 125 arası, −128 ile 127'ye sığar.
- e) **`uint8_t`.** Sadece 0, 1 ve 2 değerleri var. Ders 3.2'deki `char` önerisinden daha iyi, çünkü `uint8_t` "bu bir harf değil, küçük bir sayı" diyor ve işareti platforma bırakmıyor.

**2** – 8.100.000.000, 2³² = 4.294.967.296'dan büyük ve 32 bite sığmaz. Atama sırasında taşan bitler atılır ve değişkene 8.100.000.000 − 4.294.967.296 = **3.805.032.704** konur; `sizeof(population)` da 4 olur. Bu örnekte clang uyarır:

```
warning: implicit conversion from 'long' to 'uint32_t' (aka 'unsigned int') changes value from 8100000000 to 3805032704 [-Wconstant-conversion]
```

`-Werror` ile derliyorsan program hiç derlenmez. Ama compiler bunu sadece **sabit** bir sayıyı gördüğü için yakalayabildi. Değer çalışma sırasında hesaplansaydı (örneğin kullanıcıdan okunsaydı) aynı kırpılma sessizce olurdu. Dönüşümlerin kurallarını Ders 3.7'de göreceğiz.

**3** – 20!'e kadar aynı sonuçlar çıkar; 21!'de işaretli overflow olur ve `-fsanitize=undefined` bunu yakalar. Ders 3.2'deki sonucun aynısını görürsün: `-4249290049419214848`. Bunun nedeni bilgisayarında `int64_t` ile `long long`'un zaten aynı tip olması.

**4** – **Hayır.** macOS'ta `int64_t` = `long long` olduğu için `%lld` doğru ve uyarı çıkmıyor. 64 bit Linux'ta `int64_t` = `long` olur ve `-Wall` "format `%lld` expects `long long`, but the argument has type `long`" diye uyarır. İkisi de 8 byte olduğu için program muhtemelen yine doğru yazdırır; ama standarda göre yanlış tipte bir değer vermek **undefined behavior**'dır. `PRId64` kullanan kod her iki platformda da doğrudur.

**5** – 3, 2, 1, 0 yazdırır ve sonra durmaz: 0'dan sonra `i--`, `i`'yi 18.446.744.073.709.551.615'e (2⁶⁴ − 1) götürür ve `i >= 0` hâlâ doğrudur. `-Wall -Wextra` bile uyarmaz. Bir düzeltme, karşılaştırmayı azaltmadan önce yapmak:

```c
for (size_t i = 4; i > 0; i--) {
    printf("%zu\n", i - 1);
}
```

`i`, 4'ten 1'e kadar iner; yazdırılan `i - 1` ise 3'ten 0'a. `i` hiçbir zaman 0'ın altına inmeye çalışmaz.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §7.20: `<stdint.h>`; §7.8: `<inttypes.h>`; §7.19: `<stddef.h>`.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 3: tamsayı tipleri ve `<stdint.h>`.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.2.3 ve oradaki sabit boyutlu tamsayı tipleri notu.

**Sıradaki ders:** Tamsayı yükseltme (integer promotion). İki `uint8_t`'yi toplayınca sonuç neden `uint8_t` değil?
