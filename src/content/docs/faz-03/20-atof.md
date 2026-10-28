---
title: "3.20 Dönüşüm sıfırdan 5: atof"
description: "Ondalık bir yazıyı double'a çevirmek: basamak basamak eklemenin neden yanlış sonuç verdiği, bütün basamakları tamsayıda toplayıp tek bir bölmeyle doğru yuvarlanmış sonuca ulaşmak (Clinger'ın hızlı yolu), 10²²'nin neden sınır olduğu, üslü gösterim, strtod'un sözleşmesi ve hızlı yolun dışında kalan sayılar."
---

Ders 3.17'de `"1234"`'ü tamsayıya çevirdik; sonuç ya doğruydu ya taşmıştı, arası yoktu. Küsuratlı sayılarda iş farklı. `"0.3"` yazısının **tam** karşılığı olan bir `double` yok (Ders 3.12); yapabileceğimiz en iyi şey, 0,3'e **en yakın** `double`'ı bulmak. "En yakın" demek kolay; bu derste onu bulmanın ne kadar ince bir iş olduğunu göreceğiz.

Ders 3.19'da `double`'ı yazıya çevirmiştik. Bu ders tersini yapıyor: **atof** (ASCII to float). İkisi birlikte, bir sayıyı bir dosyaya yazıp geri okuduğunda aynı sayıyı elde etmenin temeli.

---

## 1. İlk deneme: basamak basamak

Ders 3.17'deki Horner yöntemini tam kısım için kullanalım; virgülden sonraki her basamağı da basamak değeriyle (0,1, 0,01, …) çarpıp ekleyelim. Üs kısmı (`e-3`) için de sayıyı o kadar kez 10'a bölelim ya da 10 ile çarpalım:

```c
int is_digit(char c) {
    return c >= '0' && c <= '9';
}

double atof_naive(const char text[]) {
    int i = 0;
    int negative = 0;
    if (text[i] == '+' || text[i] == '-') {
        negative = text[i] == '-';
        i++;
    }
    double value = 0.0;
    while (is_digit(text[i])) {
        value = value * 10 + (text[i] - '0');
        i++;
    }
    if (text[i] == '.') {
        i++;
        double place = 0.1;
        while (is_digit(text[i])) {
            value = value + (text[i] - '0') * place;
            place = place * 0.1;
            i++;
        }
    }
    if (text[i] == 'e' || text[i] == 'E') {
        i++;
        int exp_negative = 0;
        if (text[i] == '+' || text[i] == '-') {
            exp_negative = text[i] == '-';
            i++;
        }
        int e = 0;
        while (is_digit(text[i])) {
            e = e * 10 + (text[i] - '0');
            i++;
        }
        for (int k = 0; k < e; k++) {
            value = exp_negative ? value / 10 : value * 10;
        }
    }
    return negative ? -value : value;
}
```

`1e-3`, 1 × 10⁻³ = 0,001 demek (Ders 3.12). `strtod` (Bölüm 4) ile karşılaştıralım:

| Yazı | `strtod` | `atof_naive` | |
| --- | --- | --- | --- |
| `0.1` | 0.10000000000000001 | 0.10000000000000001 | ✓ |
| `123.456` | 123.456 | 123.456 | ✓ |
| `2.675` | 2.6749999999999998 | 2.6749999999999998 | ✓ |
| `1e-3` | 0.001 | 0.001 | ✓ |
| `0.3` | 0.29999999999999999 | **0.30000000000000004** | ✗ |
| `3.14159` | 3.1415899999999999 | **3.1415900000000003** | ✗ |
| `0.000001` | 9.9999999999999995e-07 | **1.0000000000000004e-06** | ✗ |
| `22.857142857142858` | 22.857142857142858 | **22.857142857142854** | ✗ |
| `1.7976931348623157e308` | 1.7976931348623157e+308 | **1.7976931348623145e+308** | ✗ |

`"0.3"` bile yanlış. Sebep: `3 * place` = 3 × 0,1. `place`, 0,1'e en yakın `double`; tam 0,1 değil. 3 ile çarpınca hata üç katına çıkıyor ve sonuç başka bir `double`'a yuvarlanıyor. Ders 3.12'deki 0,1 + 0,2 ile aynı hikaye: yanlış bir şey yapmadık, ama **her işlem bir yuvarlama**, ve yuvarlamalar birikti. Son satırda 308 kez 10 ile çarpmak, 308 yuvarlama demek.

Bu yanlışlar nadir mi? `-123.4567` gibi, en fazla 5 tam ve 10 ondalık basamaklı, bazılarının sonunda üs olan iki milyon rastgele yazıyla denedik:

```
yanlış: 837273 / 2000000 (%41,9)
```

Neredeyse **her iki sayıdan biri** yanlış. Yanlışlık en fazla bir iki ULP; ama Ders 3.19'un sonundaki söz bozuluyor: bir sayıyı `%.17g` ile yazıp bu fonksiyonla geri okursan, aynı sayıyı elde edemeyebilirsin.

---

## 2. Fikir: tek bir yuvarlama

Ders 3.14'teki sözü hatırla: IEEE 754'te her işlem, sonuç **tam** hesaplanıp **bir kez** yuvarlanmış gibi sonuç verir. Tek bir işlemin hatası en fazla yarım ULP. Sorun, birden çok işlem yapmamız.

O halde bütün işi **tek bir işleme** indirelim. `"3.14159"`'u şöyle okuyalım: virgülü yok sayarak bütün basamakları bir **tamsayıda** topla, virgülün yerini ayrıca say.

> 3.14159 = 314159 × 10⁻⁵

314.159 bir tamsayı; Ders 3.14'e göre 2⁵³'ten küçük her tamsayı `double`'da **tam** saklanır. 10⁵ = 100.000 de tam. O halde:

> `314159.0 / 100000.0`

iki **tam** sayının tek bir bölmesi. Sonucu, gerçek 3,14159'un en yakın `double`'a yuvarlanmış hali. Tanım gereği doğru cevap.

Bu fikri 1990'da William Clinger yayımladı; adı **hızlı yol** (fast path). İki koşulu var:

1. **Mantis** (bütün basamaklardan oluşan tamsayı) en fazla 2⁵³ olmalı; yaklaşık 15–16 basamak.
2. **10'un kuvveti** `double`'da tam olmalı. Bu, 10²²'ye kadar doğru.

İkinci koşul nereden geliyor? 10ⁿ = 2ⁿ × 5ⁿ. 2ⁿ kısmı sadece üsse gider (Ders 3.12), ama 5ⁿ mantise sığmalı:

| n | 5ⁿ | 2⁵³ = 9.007.199.254.740.992'ye sığar mı? |
| --- | --- | --- |
| 22 | 2.384.185.791.015.625 | sığar |
| 23 | 11.920.928.955.078.125 | **sığmaz** |

10²² `double`'daki son tam 10 kuvveti. 10²³ tam değil: Ders 3.19'un en kısa gösterim tablosunda `1e23`'ün aslında 9,9999999999999992 × 10²² olduğunu görmüştük.

---

## 3. parse_double

Ders 3.17'deki `parse_long` gibi, sonucu bir struct ile döndürelim. Bu sefer bir alan daha var: `exact`, sonucun hızlı yoldan, yani **kesinlikle doğru** olarak hesaplanıp hesaplanmadığını söylüyor.

```c
#include <stdint.h>

#define PARSE_OK 0
#define PARSE_NO_DIGITS 1

struct DoubleResult {
    int status;
    int exact;
    double value;
    int end;
};

const double powers_of_ten[] = {
    1e0, 1e1, 1e2, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9, 1e10, 1e11,
    1e12, 1e13, 1e14, 1e15, 1e16, 1e17, 1e18, 1e19, 1e20, 1e21, 1e22,
};
```

`powers_of_ten`'deki 23 sabitin hepsi `double`'da tam. Compiler onları derleme sırasında, kendi doğru `strtod`'uyla çeviriyor.

Hızlı yolun dışında kalan sayılar için, en azından makul bir sonuç veren bir yardımcı:

```c
double scale_by_ten(double value, int exponent) {
    while (exponent > 22) {
        value = value * 1e22;
        exponent -= 22;
    }
    while (exponent < -22) {
        value = value / 1e22;
        exponent += 22;
    }
    if (exponent < 0) {
        return value / powers_of_ten[-exponent];
    }
    return value * powers_of_ten[exponent];
}
```

Ve asıl fonksiyon. `is_space` ve `is_digit` Ders 3.17'deki gibi:

```c
struct DoubleResult parse_double(const char text[]) {
    struct DoubleResult result = {PARSE_NO_DIGITS, 1, 0.0, 0};
    int i = 0;
    while (is_space(text[i])) {
        i++;
    }
    int negative = 0;
    if (text[i] == '+' || text[i] == '-') {
        negative = text[i] == '-';
        i++;
    }

    uint64_t mantissa = 0;
    int digits = 0;
    int exponent = 0;
    int any_digits = 0;
    int dropped = 0;

    while (is_digit(text[i])) {
        if (digits < 19) {
            mantissa = mantissa * 10 + (uint64_t)(text[i] - '0');
            if (mantissa != 0) {
                digits++;
            }
        } else {
            exponent++;
            dropped = 1;
        }
        any_digits = 1;
        i++;
    }
    if (text[i] == '.') {
        i++;
        while (is_digit(text[i])) {
            if (digits < 19) {
                mantissa = mantissa * 10 + (uint64_t)(text[i] - '0');
                if (mantissa != 0) {
                    digits++;
                }
                exponent--;
            } else {
                dropped = 1;
            }
            any_digits = 1;
            i++;
        }
    }
    if (!any_digits) {
        return result;
    }

    if (text[i] == 'e' || text[i] == 'E') {
        int j = i + 1;
        int exp_negative = 0;
        if (text[j] == '+' || text[j] == '-') {
            exp_negative = text[j] == '-';
            j++;
        }
        if (is_digit(text[j])) {
            int e = 0;
            while (is_digit(text[j])) {
                if (e < 100000) {
                    e = e * 10 + (text[j] - '0');
                }
                j++;
            }
            exponent += exp_negative ? -e : e;
            i = j;
        }
    }

    result.status = PARSE_OK;
    result.end = i;
    double value;
    if (!dropped && mantissa <= (1ull << 53) && exponent >= -22 && exponent <= 22) {
        value = (double)mantissa;
        if (exponent < 0) {
            value = value / powers_of_ten[-exponent];
        } else {
            value = value * powers_of_ten[exponent];
        }
    } else {
        value = scale_by_ten((double)mantissa, exponent);
        result.exact = 0;
    }
    result.value = negative ? -value : value;
    return result;
}
```

Öncekilerden farklı olan parçalar:

**Mantis ve üs.** Tam kısımdaki her basamak mantise ekleniyor. Virgülden sonraki her basamak da mantise ekleniyor, ama `exponent`'i bir azaltıyor: `"3.14159"` → mantis 314.159, üs −5. Sonda yazıdaki üs (`e-1` gibi) bu sayıya ekleniyor: `"-12.5e-1"` → mantis 125, üs −1 − 1 = −2, sonuç −125 / 100 = **−1,25**.

**19 basamak sınırı.** `uint64_t` en fazla 19 basamaklı her sayıyı tutar (2⁶⁴ ≈ 1,8 × 10¹⁹). Daha fazla basamak gelirse onları mantise eklemiyoruz; tam kısımdaysa üssü artırıyoruz ki sayının büyüklüğü korunsun. Atılan basamaklar sonucu etkileyebileceği için `dropped`'ı işaretliyoruz. Baştaki sıfırları saymıyoruz (`mantissa != 0` koşulu): `0.000001`'in altı sıfırı yer kaplamasın.

**Üs kısmı isteğe bağlı.** `"1e"` ve `"1e+"`'da `e`'den sonra rakam yok; bu durumda `e` sayının parçası **değil**, bitiş yeri `e`'nin başı. Bunun için `j` adında ayrı bir indeksle ileriye bakıyoruz ve sadece rakam bulursak `i`'yi ilerletiyoruz. Ders 3.17'deki `0x` kontrolünün aynı fikri. Üs değeri 100.000'de duruyor; `"1e99999999999"` gibi bir yazı `int`'i taşırmasın (Ders 3.8). O kadar büyük bir üs zaten sonsuz ya da 0 verir.

**Hızlı yol.** Bölüm 2'deki iki koşul ve hiçbir basamağın atılmamış olması. Tek bir bölme ya da çarpma; `exact` 1.

**Yavaş yol.** Koşullardan biri tutmuyorsa `scale_by_ten` ile 10²²'lik adımlarla ölçekliyoruz. Birkaç yuvarlama var; sonuç yaklaşık, ve `exact` 0.

---

## 4. strtod ile karşılaştırmak

Standart kütüphanede `atof`'un iki hali var, `atoi` ile `strtol` gibi:

- `atof(text)`: `double` döndürür; hata bildirmez. `atof("abc")` 0,0.
- `strtod(text, &end)`: değer ve Ders 3.17'deki gibi bir bitiş yeri; sonuç `double`'ın aralığına sığmıyorsa `errno` `ERANGE` olur.

`parse_double`'ı `strtod` ile karşılaştıralım. Önce kenar durumları:

| Yazı | `strtod` | Bitiş | `parse_double` | Bitiş | `exact` |
| --- | --- | --- | --- | --- | --- |
| `"0.3"` | 0.29999999999999999 | 3 | 0.29999999999999999 | 3 | 1 |
| `"3.14159"` | 3.1415899999999999 | 7 | 3.1415899999999999 | 7 | 1 |
| `"0.000001"` | 9.9999999999999995e-07 | 8 | 9.9999999999999995e-07 | 8 | 1 |
| `"-12.5e-1"` | −1.25 | 8 | −1.25 | 8 | 1 |
| `"  +3.0abc"` | 3 | 6 | 3 | 6 | 1 |
| `".5"` | 0.5 | 2 | 0.5 | 2 | 1 |
| `"5."` | 5 | 2 | 5 | 2 | 1 |
| `"1e"` | 1 | 1 | 1 | 1 | 1 |
| `"1e+"` | 1 | 1 | 1 | 1 | 1 |
| `"."` | 0 | 0 | 0 (rakam yok) | 0 | |
| `"e5"` | 0 | 0 | 0 (rakam yok) | 0 | |
| `"1e400"` | inf (`ERANGE`) | 5 | inf | 5 | 0 |
| `"1e-400"` | 0 (`ERANGE`) | 6 | 0 | 6 | 0 |
| `"22.857142857142858"` | 22.857142857142858 | 18 | 22.857142857142858 | 18 | 0 |
| `"1.7976931348623157e308"` | 1.7976931348623157e+308 | 22 | **1.7976931348623151e+308** | 22 | 0 |

- `"0.3"` artık doğru, ve `exact` 1: doğru olduğunu **biliyoruz**.
- `"22.857142857142858"` 17 anlamlı basamak; mantis 2⁵³'ü aşıyor ve yavaş yola düşüyor. Sonuç doğru çıktı, ama şans eseri.
- `"1.7976931348623157e308"`'de yavaş yol 2 ULP yanıldı. `exact` 0 olduğu için en azından bunu söyleyebiliyoruz.

Sonra Bölüm 1'deki iki milyon rastgele yazı:

```
atof_naive yanlış: 837273 / 2000000
parse_double, hızlı yol: 2000000, yanlış: 0
```

Hepsi hızlı yoldan geçti ve **hiçbiri** yanlış değil. Ölçüm, kullanıcı girişi, tablolar ve dosyalardaki sayıların büyük çoğunluğu bu biçimde; hızlı yol onları kesinlikle doğru çeviriyor.

Son olarak yavaş yolu zorlayalım: 17 basamaklı mantisler ve −300 ile 300 arasında üsler, bir milyon tane:

| `strtod`'dan farkı | Oran |
| --- | --- |
| 0 ULP (doğru) | %47,1 |
| 1 ULP | %43,6 |
| 2 ULP | %8,1 |
| 3 ULP | %1,1 |
| 4 ULP ya da daha fazla | %0,1 |

Yavaş yol sonuçların yarısından fazlasında yanılıyor.

### Gerçek strtod ne yapıyor?

Bütün girdiler için doğru sonuç vermek, Ders 3.19'daki gibi **büyük tamsayılar** gerektiriyor: `"1.7976931348623157e308"`'in tam değerini 309 basamaklı bir tamsayı olarak hesaplayıp, iki komşu `double`'dan hangisine daha yakın olduğuna bakmak. David Gay'in 1990'da yazdığı `dtoa.c`, onlarca yıl birçok C kütüphanesinin ve programlama dilinin `strtod`'u oldu. 2020'de Daniel Lemire ve Michael Eisel, büyük tamsayıları neredeyse hiç gerektirmeyen çok daha hızlı bir yöntem buldu (Eisel–Lemire algoritması); bugün GCC'nin C++ kütüphanesi, Go ve Rust bunu kullanıyor. Yine 2018'deki Ryu (Ders 3.19) gibi: bir sayıyı okumak da yazmak kadar yeni bir araştırma konusu.

`strtod`'un bizim desteklemediğimiz birkaç özelliği daha var:

| Yazı | `strtod` |
| --- | --- |
| `"inf"`, `"-Infinity"` | sonsuz |
| `"nan"` | NaN |
| `"0x1.8p3"` | 12: onaltılık kayan nokta, 1,5 × 2³ |
| `"0x10"` | 16 |

Son satır şaşırtıcı: `strtod("0x10")` 16 verir, bizim `parse_double`'ımız 0 (bitiş 1). C99'dan beri `double` sabitleri de onaltılık yazılabiliyor; `0x1.8p3`'teki `p`, "2 üzeri" demek. Onaltılık gösterimin büyük avantajı, her `double`'ı **hiçbir yuvarlama olmadan** yazabilmesi: mantis zaten ikilik, ve her 4 bit bir onaltılık basamak. `printf`'in `%a` biçimi sayıları bu şekilde yazar: `printf("%a", 0.1)` → `0x1.999999999999ap-4`.

---

## Alıştırmalar

**1** – `parse_double("-0.0025e3")`'ün `mantissa`, `digits` ve `exponent` değerlerini adım adım takip et. Hızlı yoldan mı geçer? Sonuç ne?

**2** – Çalıştırmadan söyle: `"1e"`, `"."`, `"5."`, `"-.5e1"` ve `"1.5e+2x"` için `parse_double` hangi değeri ve bitiş yerini döndürür?

**3** – `"123e25"`, Bölüm 2'deki koşullara göre hızlı yoldan geçemez: üs 25. Ama 123 × 10²⁵ = 123.000 × 10²²; ve 123.000 de 2⁵³'ten küçük. Hızlı yolu, mantis yeterince küçükse büyük üsleri mantise taşıyacak şekilde genişlet. `"123e25"`, `"1e30"` ve `"9e37"` artık doğru mu?

**4** – Hızlı yolda `mantissa / 10ⁿ` yerine `mantissa * (1.0 / 10ⁿ)` yazsaydık ne olurdu? Neden?

**5** – Bir veri dosyasında sayılar `%.17g` ile yazılmış. Bu dosyayı `parse_double` ile okursan sayıları tam olarak geri elde eder misin? Hangi sayılar sorun çıkarır? `%.15g` ile yazılmış olsaydı?

<details>
<summary>Cevaplar</summary>

**1** –

| Karakter | `mantissa` | `digits` | `exponent` |
| --- | --- | --- | --- |
| `0` | 0 | 0 | 0 |
| `.` | 0 | 0 | 0 |
| `0` | 0 | 0 | −1 |
| `0` | 0 | 0 | −2 |
| `2` | 2 | 1 | −3 |
| `5` | 25 | 2 | −4 |
| `e3` | 25 | 2 | −4 + 3 = −1 |

Baştaki sıfırlar `digits`'i artırmadı ama virgülden sonra oldukları için üssü azalttı. Hızlı yoldan geçer: 25 / 10 = **−2,5** (eksi işaretiyle).

**2** –

- `"1e"` → **1**, bitiş **1**. `e`'den sonra rakam yok.
- `"."` → rakam yok, `PARSE_NO_DIGITS`, bitiş **0**.
- `"5."` → **5**, bitiş **2**. Noktadan sonra rakam olmaması sorun değil; noktadan önce var.
- `"-.5e1"` → **−5**, bitiş **5**.
- `"1.5e+2x"` → **150**, bitiş **6** (`x`'in başı).

`strtod` da aynılarını veriyor.

**3** – Hızlı yol koşulundan hemen önce:

```c
while (!dropped && exponent > 22 && mantissa <= (1ull << 53) / 10) {
    mantissa = mantissa * 10;
    exponent--;
}
```

`mantissa * 10`, mantis 2⁵³ / 10'dan küçük olduğu sürece 2⁵³'ü geçmez ve tam kalır. `"123e25"` → 123.000 × 10²²: **1,23 × 10²⁷**, `strtod` ile aynı. Bilgisayarımızda `"1e30"` ve `"9e37"` (9 × 10¹⁵ × 10²²; 9 × 10¹⁵ < 2⁵³) de doğru çıktı. 0–99.999 arası mantisler ve 0–39 arası üslerle bir milyon rastgele yazı denedik; hızlı yoldan geçen 850.488'inin hepsi doğru. Clinger'ın makalesindeki genişletme de bu.

**4** – Sonuç bazen yanlış olur. `1.0 / 10ⁿ`, n ≥ 1 için tam değil (0,1, 0,01… ikilikte sonsuz; Ders 3.12). Bir yuvarlama bölmede, bir yuvarlama çarpmada: iki işlem, iki yuvarlama, ve "tek yuvarlama" garantisi kayboldu. `0.3`'ü deneyebilirsin: 3 × (1 / 10) aslında Bölüm 1'deki `3 * place`, ve sonuç 0,30000000000000004. Bölme çarpmadan yavaş olsa da, burada doğruluk için şart. (Ders 3.15'te compiler'ın `/ 100.0`'ı `* 0.01`'e çevirmemesinin sebebi de buydu.)

**5** – `%.17g` 17 anlamlı basamak yazar; 17 basamaklı bir mantis 2⁵³'ü (yaklaşık 9 × 10¹⁵, 16 basamak) çoğu zaman aşar ve **yavaş yola** düşer. Bölüm 4'teki ölçüme göre sonuçların yarısından fazlası 1 ULP ya da daha fazla farklı çıkabilir; `exact` 0 olacağı için en azından bilirsin. Sorunsuz olanlar, `%.17g`'nin sonda sıfırları atıp kısa yazdığı sayılar (`0.5`, `100` gibi). `%.15g` ile yazılmış bir dosyada mantis en fazla 15 basamak, yani her zaman 2⁵³'ün altında: üs ±22 içinde kaldığı sürece `parse_double` dosyadaki **yazıları** kesinlikle doğru okur. Ama Ders 3.19'un 5. alıştırmasındaki sorun bu sefer yazarken ortaya çıkar: `%.15g`, `double`'ları geri elde edilebilecek kadar basamakla yazmaz. Doğru çözüm, en kısa gösterimle yazmak ve tam bir `strtod` ile okumak.

</details>

---

## Kaynaklar

- William Clinger, "How to Read Floating Point Numbers Accurately", *PLDI*, 1990.
- David Gay, "Correctly Rounded Binary-Decimal and Decimal-Binary Conversions", AT&T Bell Laboratories, Numerical Analysis Manuscript 90-10, 1990.
- Daniel Lemire, "Number Parsing at a Gigabyte per Second", *Software: Practice and Experience*, 51(8), 2021.
- C standardı (ISO/IEC 9899:2018), §7.22.1.3: `strtod`, `strtof`, `strtold`; §7.22.1.2: `atof`; §6.4.4.2: onaltılık kayan nokta sabitleri.

**Sıradaki ders:** `bool`, `enum`, `typedef`, `const` ve `volatile`. Faz 3'ün son dersi: compiler'a "bu değişken hakkında şunu bil" demenin beş yolu.
