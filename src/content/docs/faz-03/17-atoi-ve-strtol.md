---
title: "3.17 Dönüşüm sıfırdan 2: atoi ve strtol"
description: "Yazıyı sayıya çevirmek: Horner yöntemiyle basamakları biriktirmek, atoi'nin neden yetersiz olduğu, strtol'un sözleşmesi (boşluk, işaret, taban, 0x öneki, bitiş yeri, taşma) ve bu sözleşmenin birebir kopyası; kendi fonksiyonumuzu iki milyon girdide strtol ile karşılaştırmak."
---

Ders 2.13'teki sağlık hesaplayıcısı sayıları `scanf("%9d", &value)` ile okuyordu. O `9` bir hileydi: `int`'e sığmayacak bir sayıyı `%d` ile okumak undefined behavior olduğu için, `scanf`'e en fazla 9 basamak okumasını söylemiştik. 9 basamaklı her sayı `int`'e sığar; ama 2.000.000.000 gibi geçerli bir `int` de artık okunamıyordu.

Ders 3.16'da sayıyı yazıya çevirdik. Bu derste ters yöne gidiyoruz: `"-1234"` yazısını −1234 sayısına çevirmek. Önce en basit halini yazacağız, sonra C standart kütüphanesindeki `strtol`'un davranışını **birebir** kopyalayacağız: boşluklar, işaret, tabanlar, geçersiz karakterler ve taşma dahil. Sonunda Ders 2.13'teki hileye gerek kalmayacak.

---

## 1. Basamaklardan sayıya

`"1234"` dört karakter: `'1'`, `'2'`, `'3'`, `'4'`. Ders 3.2'den biliyoruz ki `c - '0'` bir rakam karakterini sayıya çevirir. Peki basamakları nasıl birleştiririz?

Soldan sağa okurken, her yeni basamak öncekilerin hepsini bir basamak sola iter. Ondalıkta "sola itmek" 10 ile çarpmak demek:

> value = value × 10 + yeni basamak

| Karakter | Basamak | `value × 10 + basamak` |
| --- | --- | --- |
| Başta | | 0 |
| `'1'` | 1 | 0 × 10 + 1 = **1** |
| `'2'` | 2 | 1 × 10 + 2 = **12** |
| `'3'` | 3 | 12 × 10 + 3 = **123** |
| `'4'` | 4 | 123 × 10 + 4 = **1234** |

Ders 3.16'da sayıyı basamaklara ayırırken basamaklar **ters** sırayla çıkıyordu; burada sorun yok, çünkü yazının başı sayının en anlamlı basamağı. Bu yönteme **Horner yöntemi** denir: 1234 = ((1 × 10 + 2) × 10 + 3) × 10 + 4. Ders 12.7'de polinomları hesaplarken aynı fikre döneceğiz.

```c
int is_digit(char c) {
    return c >= '0' && c <= '9';
}

int simple_atoi(const char text[]) {
    int value = 0;
    int i = 0;
    while (is_digit(text[i])) {
        value = value * 10 + (text[i] - '0');
        i++;
    }
    return value;
}
```

- `const char text[]`: fonksiyonun `text`'i **değiştirmeyeceğini** söylüyor. Ders 3.16'daki `digits` tablosunda da kullanmıştık; ayrıntısı Ders 3.21'de.
- Döngü, rakam olmayan ilk karakterde duruyor. Yazının sonundaki `'\0'` (Ders 3.16) da rakam değil; döngü en geç orada biter.

`simple_atoi("1234")` 1234 verir. Ama `"-5"`, `"  42"`, `"12abc"` ya da `"99999999999"` için ne yapmalı?

---

## 2. atoi neden yetmez?

Standart kütüphanede (`<stdlib.h>`) bu işi yapan hazır bir fonksiyon var: `atoi` (ASCII to integer).

```c
printf("%d %d %d %d\n", atoi("12abc"), atoi("abc"), atoi("  -42"), atoi("0"));
```

```
12 0 -42 0
```

`atoi` baştaki boşlukları atlıyor, işareti anlıyor ve rakam olmayan ilk karakterde duruyor. Sorun ikinci ve dördüncü sonuçta: `"abc"` ile `"0"` **aynı** sonucu veriyor. Kullanıcı 0 mı yazdı, yoksa bir şey yanlış mı gitti, bilmenin yolu yok. Daha kötüsü, sonuç `int`'e sığmıyorsa `atoi`'nin davranışı **undefined**. Ders 2.13'teki `scanf("%d")` ile aynı sorun.

Standart, bu yüzden daha ayrıntılı bir fonksiyon da sunar: `strtol` (string to long).

```c
#include <stdlib.h>
#include <errno.h>

char *end;
errno = 0;
long value = strtol(text, &end, 10);
```

Üç şey döndürüyor:

1. **Değer**: `long` olarak.
2. **Bitiş yeri**: `end`, yazıda okumanın durduğu yeri gösteriyor. `char *` bir **pointer** tipi; Faz 4'te göreceğiz. Şimdilik "`text`'in kaçıncı karakterinde durduğunu söyleyen bir işaret" diye düşün; `end - text` bu sayıyı verir. `&` işareti Ders 2.13'teki `scanf`'teki gibi: `strtol`'un sonucu `end`'in içine yazabilmesi için.
3. **Hata**: sonuç `long`'a sığmıyorsa `<errno.h>`'teki `errno` adlı global değişkene (Ders 2.7) `ERANGE` yazılır. `errno`'yu çağırmadan önce 0 yapmak bizim işimiz; `strtol` başarılı olduğunda ona dokunmaz.

---

## 3. strtol'un sözleşmesi

`strtol`'un ne yaptığını bir tabloyla ölçelim. Her satırda girdi, taban, dönen değer, okumanın kaçıncı karakterde durduğu (`end - text`) ve `errno` var. Bilgisayarımızda `long` 8 byte: `LONG_MAX` = 9.223.372.036.854.775.807.

| Girdi | Taban | Değer | Bitiş | `errno` |
| --- | --- | --- | --- | --- |
| `"1234"` | 10 | 1234 | 4 | |
| `"  42"` | 10 | 42 | 4 | |
| `"+15"` | 10 | 15 | 3 | |
| `"12abc"` | 10 | 12 | **2** | |
| `"1e5"` | 10 | 1 | 1 | |
| `"abc"` | 10 | 0 | **0** | |
| `"-"` | 10 | 0 | **0** | |
| `"+ 5"` | 10 | 0 | **0** | |
| `"9223372036854775807"` | 10 | 9223372036854775807 | 19 | |
| `"9223372036854775808"` | 10 | 9223372036854775807 | 19 | **`ERANGE`** |
| `"-9223372036854775808"` | 10 | −9223372036854775808 | 20 | |
| `"99999999999999999999abc"` | 10 | 9223372036854775807 | **20** | **`ERANGE`** |
| `"1A"` | 16 | 26 | 2 | |
| `"0x1A"` | 16 | 26 | 4 | |
| `"0x1A"` | 0 | 26 | 4 | |
| `"077"` | 0 | 63 | 3 | |
| `"09"` | 0 | 0 | 1 | |
| `"0x"` | 16 | 0 | **1** | |
| `"zz"` | 36 | 1295 | 2 | |
| `"789"` | 8 | 7 | 1 | |

Bu tablodan `strtol`'un kurallarını çıkaralım:

1. Baştaki **boşluk** karakterleri atlanır: boşluk, `'\t'`, `'\n'`, `'\v'`, `'\f'`, `'\r'`.
2. İsteğe bağlı bir **`+`** ya da **`-`** gelir. İşaretten sonra boşluk olamaz (`"+ 5"`).
3. **Taban 0** ise taban yazıdan anlaşılır, Ders 3.10'daki sabitler gibi: `0x` ile başlıyorsa 16, `0` ile başlıyorsa 8, değilse 10. `"09"`'un 0 vermesi bu yüzden: sekizlik bir sayı, ve 9 sekizlikte bir rakam değil.
4. **Taban 16** ise baştaki `0x` ya da `0X` atlanabilir. Ama `0x`'ten sonra onaltılık bir rakam yoksa, `x` sayının parçası sayılmaz: `"0x"`, "0 ve arkasında bir `x`" olarak okunur.
5. Rakamlar: `0`–`9` ve tabana göre `a`–`z` (büyük ya da küçük harf). Değeri tabandan küçük olmayan ilk karakterde okuma durur.
6. **Hiç rakam yoksa** değer 0'dır ve bitiş yeri yazının **başıdır**; boşluklar ve işaret de okunmamış sayılır. `"abc"` ile `"0"`'ı ayıran bilgi bu: `"0"` için bitiş 1, `"abc"` için 0.
7. **Taşma** olursa değer `LONG_MAX` ya da `LONG_MIN` olur ve `errno` `ERANGE` olur. Rakamların hepsi yine okunur: `"99999999999999999999abc"` için bitiş 20, yani `abc`'nin başı.
8. Taban 0 değilse ve 2–36 arasında değilse sonuç 0'dır.

Tabloda göstermediğimiz bir ayrıntı: macOS'taki `strtol`, hiç rakam bulamadığında `errno`'ya bir de `EINVAL` yazıyor. Standart bunu istemiyor ve her sistem yapmıyor; taşınabilir kod, "rakam var mı?" sorusunu bitiş yerine bakarak cevaplar. (Bir not daha: C23, taban 0 ve 2 için `0b` önekini de ekledi; macOS'taki kütüphane bunu henüz desteklemiyor. `"0b101"` için 0 verdi.)

---

## 4. Kendi strtol'umuz

Pointer'ları henüz görmediğimiz için `end`'i ayrı bir parametreyle değil, Ders 3.8'deki `CheckedInt` gibi bir struct ile döndürelim: değer, bitiş yeri ve ne olduğu.

```c
#include <limits.h>

#define PARSE_OK 0
#define PARSE_NO_DIGITS 1
#define PARSE_OVERFLOW 2
#define PARSE_BAD_BASE 3

struct ParseResult {
    int status;
    long value;
    int end;
};
```

İki yardımcı fonksiyon:

```c
int is_space(char c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\v' || c == '\f' || c == '\r';
}

int digit_value(char c) {
    if (c >= '0' && c <= '9') {
        return c - '0';
    }
    if (c >= 'a' && c <= 'z') {
        return c - 'a' + 10;
    }
    if (c >= 'A' && c <= 'Z') {
        return c - 'A' + 10;
    }
    return 36;
}
```

`digit_value`, bir karakterin **herhangi bir tabandaki** değerini veriyor: `'7'` → 7, `'d'` → 13, `'Z'` → 35. Rakam ya da harf olmayan karakterler için 36 döndürüyor: hiçbir tabanda (en büyüğü 36) geçerli bir rakam olamayacak bir değer. Böylece "bu karakter bu tabanda bir rakam mı?" sorusu tek bir karşılaştırmaya iniyor: `digit_value(c) < base`. `'9'`, onluk tabanda geçerli (9 < 10), sekizlikte değil (9 < 8 yanlış); `"789"`'un 8'lik tabanda 7 vermesi bu.

Ve asıl fonksiyon:

```c
struct ParseResult parse_long(const char text[], int base) {
    struct ParseResult result = {PARSE_NO_DIGITS, 0, 0};
    if (base != 0 && (base < 2 || base > 36)) {
        result.status = PARSE_BAD_BASE;
        return result;
    }

    int i = 0;
    while (is_space(text[i])) {
        i++;
    }

    int negative = 0;
    if (text[i] == '+' || text[i] == '-') {
        negative = text[i] == '-';
        i++;
    }

    if ((base == 0 || base == 16) && text[i] == '0'
            && (text[i + 1] == 'x' || text[i + 1] == 'X')
            && digit_value(text[i + 2]) < 16) {
        i += 2;
        base = 16;
    } else if (base == 0) {
        base = text[i] == '0' ? 8 : 10;
    }

    unsigned long limit = negative ? (unsigned long)LONG_MAX + 1 : (unsigned long)LONG_MAX;
    unsigned long magnitude = 0;
    int any_digits = 0;
    int overflow = 0;

    while (digit_value(text[i]) < base) {
        unsigned long d = (unsigned long)digit_value(text[i]);
        if (magnitude > (limit - d) / (unsigned long)base) {
            overflow = 1;
        } else {
            magnitude = magnitude * (unsigned long)base + d;
        }
        any_digits = 1;
        i++;
    }

    if (!any_digits) {
        return result;
    }
    result.end = i;
    if (overflow) {
        result.status = PARSE_OVERFLOW;
        result.value = negative ? LONG_MIN : LONG_MAX;
        return result;
    }
    result.status = PARSE_OK;
    if (!negative) {
        result.value = (long)magnitude;
    } else if (magnitude == limit) {
        result.value = LONG_MIN;
    } else {
        result.value = -(long)magnitude;
    }
    return result;
}
```

Bölüm 3'teki kuralların her biri kodda bir yere karşılık geliyor. En ilginç dört parça:

**`0x` kontrolü.** `text[i + 2]`'nin onaltılık bir rakam olmasını da istiyoruz (kural 4). `"0x"` için `text[i + 2]` yazının sonundaki `'\0'`; `digit_value('\0')` 36, ve önek atlanmıyor. Sonra `"0"` okunuyor, `x`'te duruluyor; bitiş 1. `text[i + 1]` ve `text[i + 2]`'ye bakmak güvenli mi? `text[i]` `'0'` olduğu için `text[i + 1]` en kötü ihtimalle `'\0'`'dır. `&&` soldan sağa çalışır ve sol taraf yanlışsa sağ tarafa **hiç bakmaz** (buna kısa devre denir); `text[i + 1]` `'x'` değilse `text[i + 2]` okunmuyor. Okunduğunda da en kötü ihtimalle `'x'`'ten sonraki `'\0'`'dır.

**Taşmayı önceden yakalamak.** Ders 3.8'deki `checked_add`'in fikri: işlemi yapmadan, sonucun sığıp sığmayacağına **sığdığı bilinen** sayılarla bakmak.

> magnitude × base + d > limit ⟺ magnitude > (limit − d) / base

`limit − d` taşmaz (d en fazla 35, limit çok büyük), bölme de taşmaz. Bölme kesirli kısmı attığı için iki taraf tamsayı eşitsizliği olarak birebir aynı.

**`LONG_MIN`'in asimetrisi.** Ders 3.3'ten beri tanıdık sorun: `LONG_MIN`'in mutlak değeri `LONG_MAX`'tan bir fazla. Negatif bir sayı için izin verilen en büyük mutlak değer `LONG_MAX + 1`; bunu `long`'da hesaplayamayız ama `unsigned long`'da hesaplayabiliriz (Ders 3.7, Kural 2). Mutlak değeri biriktirirken de işaretsiz kalıyoruz. Sonunda `-(long)magnitude` yazmak `LONG_MIN` için işe yaramaz: `(long)magnitude` 2⁶³'ü `long`'a çevirmeye çalışır, sığmaz (Ders 3.7, Kural 3). Bu yüzden o tek durumu ayrıca ele alıyoruz.

**Taşmadan sonra devam etmek.** Taşma olunca döngüden çıkmıyoruz; `strtol` gibi rakamları okumaya devam ediyoruz, sadece biriktirmeyi bırakıyoruz. Bitiş yeri böylece sayının sonunu gösteriyor (kural 7).

---

## 5. strtol ile karşılaştırmak

Kopyamızın birebir aynı davrandığından nasıl emin olacağız? İkisini aynı girdiyle çağırıp sonuçları karşılaştıran bir fonksiyon yazalım:

```c
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

int check(const char text[], int base) {
    char *end;
    errno = 0;
    long expected = strtol(text, &end, base);
    int overflowed = errno == ERANGE;

    struct ParseResult r = parse_long(text, base);
    int same = r.value == expected
            && r.end == (int)(end - text)
            && overflowed == (r.status == PARSE_OVERFLOW);
    if (!same) {
        printf("FARKLI: '%s' taban %d\n", text, base);
    }
    return same;
}
```

Bu fonksiyonu iki şekilde kullandık:

- Bölüm 3'teki tablonun bütün girdileri ve `"  +0x"`, `"-00x1"`, `"0x0x1"`, `"0x8000000000000000"` gibi aklımıza gelen kenar durumları, altı tabanda (0, 2, 8, 10, 16, 36).
- Boşluk, `+`, `-`, rakamlar, `a`, `b`, `c`, `x`, `X`, `z` ve `Z`'den rastgele seçilmiş, 0–24 karakter uzunluğunda **iki milyon** yazı. Rastgele sayıları `<stdlib.h>`'teki `rand()` üretiyor: her çağrıda 0 ile `RAND_MAX` arasında yeni bir sayı. `alphabet[rand() % count]` ile rastgele bir karakter seçtik.

```
2000252 / 2000252 aynı
```

`-fsanitize=undefined` ile çalıştırdık; rapor yok. Kenar durumları elle bulmaya çalışmak yerine bilgisayara rastgele girdilerle denetmek, **fuzzing** denen test tekniğinin en basit hali. Ne kadar dikkatli olursak olalım aklımıza gelmeyecek girdileri (`"-00x1"` gibi) bulmanın en ucuz yolu bu.

---

## 6. Ders 2.13'e dönüş

`int` okumak için `parse_long`'un sonucunu `int`'in aralığıyla karşılaştırmak yeter:

```c
struct ParseResult parse_int(const char text[]) {
    struct ParseResult r = parse_long(text, 10);
    if (r.status == PARSE_OK && (r.value > INT_MAX || r.value < INT_MIN)) {
        r.status = PARSE_OVERFLOW;
    }
    return r;
}
```

`parse_int("2000000000")` artık `PARSE_OK` döndürür; `%9d` hilesinin reddettiği bir sayı. `parse_int("3000000000")` `PARSE_OVERFLOW` döndürür; undefined behavior yok.

Bir uyarı: Windows'ta `long` 4 byte (Ders 3.2), yani orada `parse_long`'un sınırı `LONG_MAX` = 2.147.483.647. Kodumuz `LONG_MAX` ve `LONG_MIN` kullandığı için orada da doğru çalışır; sadece daha küçük bir aralıkla. Her platformda 64 bitlik bir okuma istiyorsan aynı fonksiyonu `long long` ve `LLONG_MAX` ile yazmak gerekir; standart kütüphanedeki karşılığı `strtoll`.

Ders 2.13'teki `read_int`'in bir kuralı daha vardı: `175abc` gibi, sayıdan sonra boşluktan başka bir şey olan girişler geçersizdi. `end` bu kuralı da çok kolaylaştırıyor (4. alıştırma). Satırı bir array'e okuyup `parse_int` ile çevirmek, Ders 4.12'de string'leri gördükten sonra bütün `scanf` kullanımlarımızın yerini alacak.

---

## Alıştırmalar

**1** – `parse_long("  -0x1A", 0)`'ın tracing tablosunu çiz: her adımda `i`, `text[i]`, `base`, `negative` ve `magnitude`. Sonuç ve bitiş yeri ne?

**2** – Çalıştırmadan söyle: bu çağrılar hangi `value`, `end` ve `status`'u döndürür?

- `parse_long("0x", 0)`
- `parse_long("09", 0)`
- `parse_long("- 5", 10)`
- `parse_long("ZZ", 36)`
- `parse_long("10", 1)`

**3** – `parse_long`'daki taşma kontrolünü `magnitude * base + d > limit` diye yazsaydık ne olurdu? `magnitude` ve `limit` işaretsiz; undefined behavior olur mu?

**4** – Ders 2.13'teki kuralı uygulayan `struct ParseResult parse_whole_int(const char text[])` yaz: sayıdan sonra yazının sonuna kadar sadece boşluk karakterleri olabilir; başka bir şey varsa `status` `PARSE_NO_DIGITS` olsun. `"175"`, `" 175  "`, `"175abc"`, `"175 1"` ve `""` için dene.

**5** – `digit_value`'da harfleri `c - 'a' + 10` diye çeviriyoruz. Bu, `'a'` ile `'z'` arasındaki harflerin art arda dizildiğini varsayıyor. C standardı bunu garanti eder mi? Rakamlar için?

<details>
<summary>Cevaplar</summary>

**1** –

| Adım | `i` | `text[i]` | `base` | `negative` | `magnitude` |
| --- | --- | --- | --- | --- | --- |
| Boşlukları atla | 0 → 2 | `' '` → `'-'` | 0 | 0 | 0 |
| İşaret | 2 → 3 | `'-'` | 0 | 1 | 0 |
| `0x` öneki (`text[5]` = `'1'`, 16'dan küçük) | 3 → 5 | `'0'` | 16 | 1 | 0 |
| Rakam `'1'` | 5 → 6 | `'1'` | 16 | 1 | 1 |
| Rakam `'A'` | 6 → 7 | `'A'` | 16 | 1 | 1 × 16 + 10 = 26 |
| `'\0'`: dur | 7 | `'\0'` | 16 | 1 | 26 |

Sonuç **−26**, bitiş **7**, `PARSE_OK`. `strtol` da aynısını veriyor.

**2** –

- `"0x"`, taban 0: **0**, bitiş **1**, `PARSE_OK`. `0x`'ten sonra rakam yok; `0` okunuyor, taban 8 oluyor (`0` ile başladığı için), `x`'te duruluyor.
- `"09"`, taban 0: **0**, bitiş **1**, `PARSE_OK`. Sekizlik sayı `0`; `9` sekizlikte rakam değil.
- `"- 5"`: **0**, bitiş **0**, `PARSE_NO_DIGITS`. İşaretten sonra boşluk olamaz.
- `"ZZ"`, taban 36: **1295** (35 × 36 + 35), bitiş **2**, `PARSE_OK`.
- `"10"`, taban 1: **0**, bitiş **0**, `PARSE_BAD_BASE`.

**3** – Undefined behavior olmaz: `magnitude * base` işaretsiz, taşarsa başa döner (Ders 3.8). Ama kontrol **yanlış** olur: taşıp başa dönmüş, küçük görünen bir sonuç `limit`'ten küçük çıkar ve taşma fark edilmez. Ders 3.8'deki `sum < a` kontrolünü hatırla; o, toplamada başa dönmenin **tek** bir kez olabileceğini bildiğimiz için çalışıyordu. Çarpmada sonuç birçok kez başa dönebilir ve hiçbir basit karşılaştırma bunu yakalayamaz. Önceden kontrol etmek tek güvenli yol.

**4** –

```c
struct ParseResult parse_whole_int(const char text[]) {
    struct ParseResult r = parse_int(text);
    if (r.status != PARSE_OK) {
        return r;
    }
    int i = r.end;
    while (is_space(text[i])) {
        i++;
    }
    if (text[i] != '\0') {
        r.status = PARSE_NO_DIGITS;
    }
    return r;
}
```

`"175"` ve `" 175  "` → `PARSE_OK`, 175. `"175abc"` ve `"175 1"` → `PARSE_NO_DIGITS`. `""` → `PARSE_NO_DIGITS` (zaten `parse_int`'ten öyle geliyor). Satır sonundaki `'\n'` da bir boşluk karakteri olduğu için, bir satırı olduğu gibi verirsen de çalışır. `PARSE_NO_DIGITS` yerine `PARSE_TRAILING` gibi yeni bir durum eklemek, hatayı kullanıcıya daha iyi açıklamanı sağlar.

**5** – Harfler için **hayır**. Standart sadece `'0'`–`'9'` rakamlarının art arda olmasını garanti eder (§5.2.1); `c - '0'` bu yüzden her sistemde doğru. Harfler ASCII'de art arda, ama IBM ana bilgisayarlarında hâlâ kullanılan EBCDIC karakter kümesinde `'i'` ile `'j'` arasında boşluk var: orada `'j' - 'a'` 9 değil 16. Tamamen taşınabilir bir `digit_value`, Ders 3.16'daki `digits` tablosunda harfi arayarak yazılabilir. Bugün karşılaşacağın her sistem ASCII uyumlu olduğu için `strtol`'un kendi gerçeklemeleri de çoğunlukla bizim yaptığımızı yapar.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §7.22.1.4: `strtol`, `strtoll`, `strtoul`, `strtoull`; §7.22.1.2: `atoi`; §5.2.1: rakam karakterlerinin art arda olması.
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.7 ve §3.5: `atoi`.
- SEI CERT C Coding Standard, ERR34-C: metni sayıya çevirirken hataları yakalamak (`atoi` yerine `strtol`).

**Sıradaki ders:** Dönüşüm sıfırdan 3: `print_bin` ve `print_hex`. Bölme ve kalan yerine bit kaydırma ve maske.
