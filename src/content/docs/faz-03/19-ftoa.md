---
title: "3.19 Dönüşüm sıfırdan 4: ftoa"
description: "Bir double'ı yazıya çevirmek: ölçekleyip yuvarlamanın ve basamak basamak çarpmanın neden yanlış sonuç verdiği, her double'ın tam ondalık değerinin sonlu olması, bitlerden tamsayı aritmetiğiyle doğru yuvarlanmış bir ftoa ve printf ile karşılaştırması; en kısa gösterim problemi ve Dragon4, Grisu, Ryu algoritmaları."
---

Şu satır ne yazar?

```c
printf("%.2f\n", 2.675);
```

```
2.67
```

2,675'i iki ondalığa yuvarlarsak 2,68 olmalı, değil mi? Ders 3.12'yi okuduysan cevabı tahmin edebilirsin: `2.675` sabiti `double`'da tam olarak saklanamıyor. Saklanan değer 2,67499999999999982236431605997495353221893310546875; ve bu sayıyı iki ondalığa yuvarlamak gerçekten **2,67** veriyor. `printf` haklı.

Ders 3.16'da tamsayıyı yazıya çevirdik. Bu derste aynısını `double` için yapacağız: **ftoa** (float to ASCII). Önce akla gelen iki basit yolu deneyip neden yanlış olduklarını göreceğiz, sonra `printf` ile **her basamağında aynı** sonucu veren bir sürüm yazacağız. Ders 3.18'deki kaydırma ve maskeler burada iş görecek.

---

## 1. İlk deneme: ölçekle ve yuvarla

Ders 3.11'deki fikir: iki ondalık istiyorsak sayıyı 100 ile çarp, en yakın tamsayıya yuvarla, sonra tam kısmı ve küsuratı ayrı ayrı yaz.

Önce Ders 3.16'daki basamak yazıcısını `uint64_t` için ve "en az şu kadar basamak" seçeneğiyle yeniden yazalım; küsuratın baştaki sıfırları için gerekecek (0,05'in küsuratı 5 değil `05`):

```c
#include <stdio.h>
#include <stdint.h>
#include <math.h>

void reverse(char s[], int from, int to) {
    while (from < to) {
        char tmp = s[from];
        s[from] = s[to];
        s[to] = tmp;
        from++;
        to--;
    }
}

int write_u64(uint64_t value, char out[], int start, int min_digits) {
    int length = start;
    do {
        out[length] = (char)('0' + value % 10);
        length++;
        value = value / 10;
    } while (value != 0 || length - start < min_digits);
    out[length] = '\0';
    reverse(out, start, length - 1);
    return length;
}

int ftoa_simple(double x, char out[], int decimals) {
    int length = 0;
    if (signbit(x)) {
        out[0] = '-';
        length = 1;
        x = -x;
    }
    uint64_t scale = 1;
    for (int i = 0; i < decimals; i++) {
        scale = scale * 10;
    }
    uint64_t total = (uint64_t)llround(x * (double)scale);
    length = write_u64(total / scale, out, length, 1);
    if (decimals > 0) {
        out[length] = '.';
        length++;
        length = write_u64(total % scale, out, length, decimals);
    }
    return length;
}
```

- `signbit` (Ders 3.13), −0'ı da negatif sayıyor; `printf` gibi `-0.00` yazmamızı sağlıyor.
- `llround` (Ders 3.14), en yakın tamsayıya yuvarlayıp `long long` döndürüyor.
- NaN, sonsuz ve çok büyük sayıları şimdilik düşünmüyoruz.

`printf("%.2f")` ile karşılaştıralım:

| `x` | `ftoa_simple` | `printf` |
| --- | --- | --- |
| 22,857142857142858 | 22.86 | 22.86 |
| −0,5 | -0.50 | -0.50 |
| −0,0 | -0.00 | -0.00 |
| 1,005 | 1.00 | 1.00 |
| **2,675** | **2.68** | 2.67 |
| **0,125** | **0.13** | 0.12 |
| **10¹⁵ + 0,3** | **1000000000000000.32** | 1000000000000000.25 |

Çoğu doğru, ama üçü yanlış; ve her birinin sebebi farklı.

**2,675.** Saklanan değer 267,4999… / 100; yuvarlanınca 267 vermeli. Ama `x * 100` bir kayan nokta çarpması, ve sonucu da yuvarlanıyor (Ders 3.14, Bölüm 2). Gerçek çarpım 267,49999999999998224…; 267,5'in altındaki ilk `double` ise 267,49999999999994316. Gerçek sonuç 267,5'e çok daha yakın, ve çarpmanın sonucu tam olarak **267,5**'e yuvarlandı. "Yarıdan küçük" bilgisi, çarpmada kayboldu.

**0,125.** Bu sefer çarpma tam: 0,125 × 100 = 12,5, ikisi de `double`'da tam. 12,5 tam ortada; `llround` ortadaki sayıları **sıfırdan uzağa** yuvarlıyor (Ders 3.14'teki `round` gibi): 13. `printf` ise IEEE 754'ün varsayılan kuralını uyguluyor: ortadaysa **çifte**. 0,12.

**10¹⁵ + 0,3.** Saklanan değer 1.000.000.000.000.000,25 (10¹⁵ civarında ULP 0,125). × 100 = 10¹⁷ + 25, ama 10¹⁷ civarında ULP 16; çarpmanın sonucu 10¹⁷ + 32'ye yuvarlandı. Ölçekleme, 2⁵³'ün ötesine geçen her sayıyı bozar.

Bunlar nadir durumlar mı? 0 ile 100 arasında, üç ondalıklı bir milyon rastgele sayıyla (`12.345` gibi) denedik:

```
farklı: 44212 / 1000000
```

**%4,4.** Bu, Ders 2.13'teki sağlık hesaplayıcısı gibi bir programda, her yirmi beş sonuçtan birinin `printf`'ten farklı yazılması demek.

---

## 2. İkinci deneme: basamak basamak

Başka bir fikir: tam kısmı ayır, sonra küsuratı 10 ile çarpıp tam kısmını al, kalanla devam et. Elle bölme yaparken yaptığımız gibi.

```c
int ftoa_digits(double x, char out[], int decimals) {
    uint64_t whole = (uint64_t)x;
    int length = write_u64(whole, out, 0, 1);
    double frac = x - (double)whole;
    out[length] = '.';
    length++;
    for (int i = 0; i < decimals; i++) {
        frac = frac * 10;
        int digit = (int)frac;
        out[length] = (char)('0' + digit);
        length++;
        frac = frac - digit;
    }
    out[length] = '\0';
    return length;
}
```

Yuvarlama yapmıyor; sadece basamakları çıkarıyor. 0,1'in 30 basamağını isteyelim:

```
ftoa_digits: 0.100000000000000000000000000000
printf:      0.100000000000000005551115123126
```

Bizimki 0,1'in **tam olarak** 0,1 olduğunu iddia ediyor. Ders 3.12'de bunun doğru olmadığını gördük. Ne oldu?

İlk adımda `frac * 10` = 0,1000000000000000055… × 10 = 1,000000000000000055…, ve bu sonuç en yakın `double`'a, yani tam olarak **1,0**'a yuvarlandı. 1'in ULP'si 2,2 × 10⁻¹⁶ (Ders 3.14); 5,5 × 10⁻¹⁷'lik kuyruk yarım ULP'den küçük ve kayboldu. Her çarpma bir yuvarlama, ve yuvarlama tam olarak bakmaya çalıştığımız basamakları siliyor.

İki denemenin ortak sorunu aynı: **yazdırma sırasında kayan nokta aritmetiği kullanmak**. Her işlem bir yuvarlama daha ekliyor. Doğru bir `ftoa`, sayının bitlerine dokunmadan, **tam** bir aritmetikle çalışmalı.

---

## 3. Bir double'ın tam değeri

İyi haber: her `double`'ın ondalık açılımı **sonludur**. Ders 3.12'deki formülü hatırla: bir `double`, bir tamsayı ile 2'nin bir kuvvetinin çarpımı.

> x = m × 2^e   (m, gizli bitle birlikte 53 bitlik bir tamsayı; e bir tamsayı)

e negatifse x = m / 2^(−e). Ve 1/2ᵏ'nin ondalık açılımı her zaman sonlu:

> 1/2 = 0,5   1/4 = 0,25   1/8 = 0,125   1/2ᵏ = 5ᵏ / 10ᵏ

Virgülden sonra **tam olarak k basamak**. 1/3'ün tersine, ikilikte sonlu olan her kesir ondalıkta da sonlu; çünkü 10, 2'nin katı. Sonuç: küsuratı k bitle yazılan bir `double`, virgülden sonra en fazla k basamakla **tam olarak** yazılabilir.

0,1'in `double`'ı: m = 0x1999999999999A, e = −56, yani m / 2⁵⁶. m çift olduğu için kesir bir kez sadeleşiyor: (m / 2) / 2⁵⁵. Virgülden sonra tam olarak 55 basamak:

```
0.1000000000000000055511151231257827021181583404541015625
```

`printf("%.55f", 0.1)` da tam olarak bunu yazar. Bilgisayarındaki "0,1"in gerçek değeri bu.

---

## 4. Doğru bir ftoa

Plan: Ders 3.18'deki gibi bitlerden m'yi ve e'yi çıkar. x = m / 2ᵏ (k = −e) ise:

- **Tam kısım**: m'nin sağdaki k biti atılmış hali, `m >> k`.
- **Küsurat**: sağdaki k bit, `m & (2ᵏ − 1)`. Gerçek küsurat bu tamsayının 2ᵏ'ye bölümü; bölmeyi hiç yapmıyoruz, payı tutuyoruz.

Bir basamak üretmek için küsuratı 10 ile çarpıyoruz. Pay olarak: `frac * 10`. Yeni basamak bu sayının tam kısmı, yani `(frac * 10) >> k`; yeni küsurat da sağdaki k bit, `(frac * 10) & mask`. Her şey **tamsayı** aritmetiği; hiçbir yuvarlama yok.

Tamsayıların sığması için bir sınır koyalım: `frac` k bit, `frac * 10` k + 4 bit tutar; k ≤ 60 olursa 64 bite sığar. Tam kısmın 64 bite sığması için de e ≤ 11 olmalı. Yani bu fonksiyon 2⁻⁸ (≈ 0,0039) ile 2⁶⁴ (≈ 1,8 × 10¹⁹) arasındaki sayılarla, ve 0 ile çalışacak.

```c
#include <string.h>

int ftoa_exact(double x, char out[], int decimals) {
    uint64_t bits;
    memcpy(&bits, &x, sizeof(bits));
    int negative = (int)(bits >> 63);
    int exponent_field = (int)((bits >> 52) & 0x7FF);
    uint64_t mantissa = bits & 0xFFFFFFFFFFFFFull;

    if (exponent_field == 0x7FF || (exponent_field == 0 && mantissa != 0)) {
        return -1;
    }
    if (exponent_field != 0) {
        mantissa = mantissa | (1ull << 52);
    }
    int exponent = exponent_field == 0 ? 0 : exponent_field - 1075;
    if (exponent > 11 || exponent < -60 || decimals > 60) {
        return -1;
    }

    uint64_t whole;
    uint64_t frac;
    int k;
    if (exponent >= 0) {
        whole = mantissa << exponent;
        frac = 0;
        k = 1;
    } else {
        k = -exponent;
        whole = mantissa >> k;
        frac = mantissa & ((1ull << k) - 1);
    }
    uint64_t mask = (1ull << k) - 1;

    char digits[64];
    for (int i = 0; i < decimals; i++) {
        frac = frac * 10;
        digits[i] = (char)('0' + (frac >> k));
        frac = frac & mask;
    }

    uint64_t half = 1ull << (k - 1);
    int last_odd = decimals > 0 ? (digits[decimals - 1] - '0') % 2 : (int)(whole % 2);
    if (frac > half || (frac == half && last_odd)) {
        int i = decimals - 1;
        while (i >= 0 && digits[i] == '9') {
            digits[i] = '0';
            i--;
        }
        if (i >= 0) {
            digits[i]++;
        } else {
            whole++;
        }
    }

    int length = 0;
    if (negative) {
        out[0] = '-';
        length = 1;
    }
    length = write_u64(whole, out, length, 1);
    if (decimals > 0) {
        out[length] = '.';
        length++;
        for (int i = 0; i < decimals; i++) {
            out[length] = digits[i];
            length++;
        }
        out[length] = '\0';
    }
    return length;
}
```

Parça parça:

**Bitleri ayırmak.** Ders 3.18'deki `double` maskeleri: işaret `bits >> 63`, üs alanı `(bits >> 52) & 0x7FF`, mantis `bits & 0xFFFFFFFFFFFFF` (52 tane 1, onaltılıkta 13 tane `F`). Ders 3.13'teki özel değerler: üs alanı `0x7FF` (sonsuz, NaN) ve denormaller için −1 döndürüyoruz. Sıradan sayılarda gizli biti (`1ull << 52`) ekliyoruz.

**Üs.** Üs alanından bias'ı (1023) çıkarınca 1,mantis × 2^(üs − 1023) çıkıyor. Biz mantisi bir **tamsayı** olarak (52 bit sola kaymış) kullandığımız için 52 daha çıkarıyoruz: 1023 + 52 = **1075**. 0 için üs alanı 0 ve mantis 0; `exponent` 0 kabul ediliyor ve her şey sıfır çıkıyor.

**Basamaklar.** Bölümün başında anlattığımız döngü: `frac * 10`'un tam kısmı (`>> k`) bir basamak, kalanı (`& mask`) yeni küsurat. 0,1 için ilk adım: frac / 2⁵⁶ = 0,1000…0555; × 10 = 1,000…0555; tam kısmı 1, kalan 0,000…0555. Kuyruk **kaybolmadı**, `frac`'ın içinde duruyor.

**Yuvarlama.** İstenen basamaklar bittikten sonra `frac` atılan kısmı tutuyor. `half` = 2ᵏ⁻¹, yani 0,5'in payı. Atılan kısım yarıdan büyükse yukarı, küçükse aşağı; **tam yarıysa** son basamak tekse yukarı, çiftse aşağı (Ders 3.14). 0,125'in `%.2f` ile 0,12 olmasının sebebi bu kural; ve bu sefer "tam yarı" gerçekten tam yarı, çünkü hiçbir yuvarlama yapmadık.

**Elde.** Yukarı yuvarlamak son basamağa 1 eklemek; 9 ise 0 olur ve elde sola geçer. 0,996 → `99` + 1 → `00` ve elde tam kısma: **1.00**. Ders 0'daki toplama.

Karşılaştıralım:

| `x` | `ftoa_exact(x, out, 2)` | `printf("%.2f")` |
| --- | --- | --- |
| 2,675 | 2.67 | 2.67 |
| 0,125 | 0.12 | 0.12 |
| 0,375 | 0.38 | 0.38 |
| 0,996 | 1.00 | 1.00 |
| 9,995 | 9.99 | 9.99 |
| 10¹⁵ + 0,3 | 1000000000000000.25 | 1000000000000000.25 |

Ve 55 basamakla 0,1:

```
ftoa_exact: 0.1000000000000000055511151231257827021181583404541015625
printf:     0.1000000000000000055511151231257827021181583404541015625
```

Bölüm 1'deki gibi rastgele bir test yaptık; bu sefer üç tür sayıyla (üç ondalıklı sayılar, 0 ile 10⁶ arasında rastgele `double`'lar ve **rastgele bit desenleri**) ve 0 ile 19 arasında rastgele basamak sayılarıyla. Üç milyon denemenin yaklaşık bir milyonu fonksiyonun aralığı dışında kaldı (rastgele bit desenlerinin çoğu çok büyük ya da çok küçük sayılar). Kalanların hepsinde:

```
farklı: 0 / 2035119
```

Fonksiyonumuz, kendi aralığında, `printf` ile basamağı basamağına aynı.

---

## 5. Gerçek printf ne yapıyor?

Bizim sınırlarımız 64 bitlik tamsayılardan geliyordu. `double`'ın bütün aralığında aynı fikir çalışır, ama çok daha büyük sayılarla:

- `DBL_MAX` ≈ 1,8 × 10³⁰⁸: tam kısmı **309 basamaklı** bir tamsayı.
- `DBL_TRUE_MIN` ≈ 4,9 × 10⁻³²⁴ = 2⁻¹⁰⁷⁴: virgülden sonra **1074 basamak**.

Bunları hesaplamak için yüzlerce byte'lık tamsayılarla çarpma ve karşılaştırma yapan bir **büyük tamsayı** (bignum) aritmetiği gerekiyor. C kütüphanelerinin `printf`'i tam olarak bunu yapıyor. Bu yüzden `printf("%.2f")` göründüğünden çok daha karmaşık bir fonksiyon; ve bu yüzden basit `ftoa`'ların neredeyse hepsi yanlış. Büyük tamsayı aritmetiğini Faz 6 ve Faz 12'de kendimiz yazacağız.

---

## 6. En kısa gösterim

Şimdiye kadar "kaç basamak istediğimizi" biz söyledik. Ama bir sayıyı yazdırırken çoğu zaman asıl soru başka: **sayıyı tam olarak geri elde etmek için gereken en kısa yazı ne?**

Ders 3.14'te bir `double`'ı her zaman geri elde etmek için 17 anlamlı basamak gerektiğini söylemiştik. Ama çoğu sayı için 17 basamak fazla:

| Değer | `%.17g` | En kısa |
| --- | --- | --- |
| `0.1` | 0.10000000000000001 | **0.1** |
| `0.3` | 0.29999999999999999 | **0.3** |
| `0.1 + 0.2` | 0.30000000000000004 | 0.30000000000000004 |
| `1.0 / 3` | 0.33333333333333331 | 0.3333333333333333 |
| `22.857142857142858` | 22.857142857142858 | 22.857142857142858 |
| `1e23` | 9.9999999999999992e+22 | **1e+23** |
| `5e-324` | 4.9406564584124654e-324 | **5e-324** |

"En kısa" sütununu bulmak için 1'den 17'ye kadar her hassasiyeti denedik: `snprintf` ile o kadar anlamlı basamakla yazdırıp, yazıyı `strtod` (Ders 3.20) ile geri okuduk; geri okunan sayı aynı `double` olduğu anda durduk.

0,1 + 0,2'nin en kısa hali bile 17 basamak: 0,3'ten farklı bir `double` olduğu için, onu 0,3'ten ayıracak kadar basamak gerekiyor. Python'da `0.1 + 0.2` yazınca `0.30000000000000004` görmenin sebebi bu: Python, JavaScript ve Java sayıları **en kısa** gösterimle yazar. `0.1` yazınca `0.1` görürsün, çünkü 0,1'e en yakın `double`'ı geri veren en kısa yazı bu; sayının kendisi değil.

Bizim deneme–yanılma yöntemimiz çalışıyor ama yavaş: her sayı için 17'ye kadar `snprintf` ve `strtod` çağrısı. Bu problem için özel algoritmalar geliştirildi:

| Yıl | Algoritma | Yazarlar |
| --- | --- | --- |
| 1990 | Dragon4 | Guy Steele & Jon White |
| 2010 | Grisu | Florian Loitsch |
| 2018 | Ryu | Ulf Adams |

Dragon4 büyük tamsayılarla çalışan ilk doğru algoritma. Grisu, çoğu sayıyı sadece 64 bitlik tamsayılarla, çok hızlı çözüp kalan nadir durumlar için Dragon4'e devreden bir yöntem; JavaScript motorlarında uzun süre kullanıldı. Ryu ise her sayı için hem hızlı hem kesin; bugün C++'ın `std::to_chars`'ının birçok gerçeklemesinde ve birçok dilin standart kütüphanesinde Ryu ya da ondan türeyen algoritmalar çalışıyor. 2018'de yayımlanmış olması, "bir sayıyı yazdırmak" gibi temel görünen bir problemin ne kadar derin olduğunu gösteriyor.

---

## Alıştırmalar

**1** – Bölüm 1'deki `ftoa_simple`'ın `llround` yerine `printf`'in kuralıyla (ortadaysa çifte) yuvarlaması için ne kullanırdın? (İpucu: Ders 3.14.) Bu değişiklik üç hatadan hangisini düzeltir, hangilerini düzeltmez?

**2** – `ftoa_exact`'e NaN ve sonsuz desteği ekle: `printf` gibi `nan`, `inf` ve `-inf` yazsın. (Ders 3.13'teki bit desenlerini hatırla: üs alanı `0x7FF`; mantis 0 ise sonsuz, değilse NaN.)

**3** – Bölüm 3'teki kurala göre, bu sayıların tam ondalık açılımı virgülden sonra kaç basamak? Önce hesapla, sonra `printf("%.60f")` ile kontrol et: 0,25, 0,375, `(double)0.1f`.

**4** – `ftoa_exact(0.001, out, 3)` −1 döndürüyor. Neden? 0,001'in üssü ne? Fonksiyonun çalıştığı en küçük pozitif sayı tam olarak ne?

**5** – Bir arkadaşın `double`'ları bir dosyaya `%.15g` ile yazıp sonra geri okuyor: "15 basamak, `DBL_DIG` kadar; kayıp olmaz." Haklı mı? Bölüm 6'daki tablodan bir karşı örnek bul. Hangi biçim her zaman güvenli?

<details>
<summary>Cevaplar</summary>

**1** – `rint` (Ders 3.14): varsayılan yuvarlama modunda ortadaki sayıları çifte yuvarlar. `(uint64_t)rint(x * (double)scale)` ile **0,125** düzelir: 12,5 → 12. Diğer ikisi düzelmez, çünkü onlarda sorun yuvarlama kuralı değil, **çarpmanın kendisi**: 2,675 × 100 zaten tam olarak 267,5'e yuvarlandı ve `rint` onu 268'e yuvarlar (268 çift); 10¹⁵ + 0,3'te de bilgi çarpmada kayboldu.

**2** – `exponent_field == 0x7FF` kontrolünü ikiye ayır:

```c
if (exponent_field == 0x7FF) {
    int length = 0;
    if (mantissa != 0) {
        strcpy(out, "nan");
        return 3;
    }
    if (negative) {
        out[0] = '-';
        length = 1;
    }
    out[length] = 'i';
    out[length + 1] = 'n';
    out[length + 2] = 'f';
    out[length + 3] = '\0';
    return length + 3;
}
```

`strcpy`, `<string.h>`'teki bir fonksiyon: ikinci yazıyı `'\0'` dahil birincinin üzerine kopyalar (Ders 4.14'te kendimiz yazacağız). Sonsuz için karakterleri elle yazdık; NaN'ın işaretini, macOS'taki `printf` gibi yok saydık. (Linux'taki glibc, işaret biti 1 olan bir NaN için `-nan` yazar. Standart bunu serbest bırakıyor.)

**3** –

- 0,25 = 1/2²: **2** basamak, `0.25`.
- 0,375 = 3/2³: **3** basamak, `0.375`.
- `(double)0.1f` = 13.421.773 / 2²⁷: **27** basamak, `0.100000001490116119384765625`. Ders 3.12'de float'ın 0,1'i olarak gördüğümüz sayı.

Kural: sadeleştirilmiş halinde payda 2ᵏ olan bir kesir, virgülden sonra tam olarak k basamaktır.

**4** – 0,001 = 1,024 × 2⁻¹⁰: `double`'da 1,mantis × 2⁻¹⁰, tamsayı mantisle m × 2⁻⁶². k = 62 > 60; `frac * 10` 66 bit gerektirir ve `uint64_t`'ye sığmaz. Fonksiyonun çalıştığı en küçük üs −60: m'nin en küçük değeri 2⁵² olduğu için en küçük sayı 2⁵² × 2⁻⁶⁰ = 2⁻⁸ = **0,00390625**. (Daha küçük sayıları da yazdırmak istersen 128 bitlik ara sonuçlar ya da Bölüm 5'teki büyük tamsayılar gerekir.)

**5** – Haklı değil. `DBL_DIG` = 15, "15 basamaklı her **ondalık** sayı `double`'a gidip geri gelince aynı kalır" demek; tersi yönde, her `double`'ı geri elde etmek için **17** basamak gerekiyor (Ders 3.14). Karşı örnek: `0.1 + 0.2`. `%.15g` ile `0.3` yazılır, geri okununca 0,3'e en yakın `double` olur; bu, 0,1 + 0,2'nin sonucu olan `double` değil. Her zaman güvenli olan `%.17g`; ya da Bölüm 6'daki en kısa gösterim.

</details>

---

## Kaynaklar

- Guy Steele & Jon White, "How to Print Floating-Point Numbers Accurately", *PLDI*, 1990.
- Florian Loitsch, "Printing Floating-Point Numbers Quickly and Accurately with Integers", *PLDI*, 2010.
- Ulf Adams, "Ryū: Fast Float-to-String Conversion", *PLDI*, 2018.
- C standardı (ISO/IEC 9899:2018), §7.21.6.1: `printf`'in `%f`, `%e`, `%g` biçimleri ve doğru yuvarlama önerisi; §5.2.4.2.2: `DECIMAL_DIG` ve `DBL_DIG`.

**Sıradaki ders:** Dönüşüm sıfırdan 5: `atof`. Ters yön: `"0.3"` yazısından 0,3'e en yakın `double`'a.
