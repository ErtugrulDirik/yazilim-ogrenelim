---
title: "3.1 int neden yetmedi?"
description: "Faz 2'de int ile karşılaştığımız sınırlar; sizeof ile bir tipin kaç byte tuttuğunu ölçmek; byte sayısından değer aralığına; aynı programın farklı platformlarda farklı davranması."
---

Faz 2'yi baştan sona tek bir tiple yazdık: `int`. Değişkenler, array'ler, struct'lar, sağlık hesaplayıcısı… Hepsi `int`. Ve yol boyunca `int`'in sınırlarına defalarca çarptık:

- **Ders 2.3:** Vücut kitle indeksi 22,86 olmalıydı; program **22** dedi. Küsurat kayboldu.
- **Ders 2.8:** 13! = 6.227.020.800 olmalıydı; program **1.932.053.504** dedi. Sayı sığmadı, overflow oldu.
- **Ders 2.10:** Asal testi, 2.147.483.647'nin asal olmadığını söyledi; çünkü `d * d` sığmadı.
- **Ders 2.11:** `INT_MAX` 2.147.483.647 ama `INT_MIN` -2.147.483.648: negatif taraf neden bir fazla?
- **Ders 2.15:** 22,85'i yazdırabilmek için sayıyı 100 ile çarpıp virgülü kafamızda tutmak zorunda kaldık.
- **Faz 0:** 0,1'in ikilikte sonsuz olduğunu görmüştük. Bilgisayar 0,1'i nasıl saklıyor?

Faz 3'ün işi bu soruların hepsini cevaplamak. İlk adım, en temel soru: **bir `int` aslında nedir?**

---

## 1. Değişken = sabit sayıda byte

Faz 0'da belleği numaralandırılmış kutulardan oluşan bir raf olarak düşünmüştük. Her kutu bir **byte**, yani 8 bit. Bir değişken, bu raftaki **yan yana birkaç kutudur**. Kaç kutu olacağını değişkenin **tipi** belirler.

Bir tipin ya da değişkenin kaç byte tuttuğunu C'ye sorabiliriz. Bunun için `sizeof` kullanılır:

```c
#include <stdio.h>

struct Point {
    int x;
    int y;
};

int main(void) {
    int age = 20;
    int scores[5] = {70, 85, 60, 90, 75};
    struct Point p = {3, 4};

    printf("int: %zu byte\n", sizeof(int));
    printf("age: %zu byte\n", sizeof(age));
    printf("scores: %zu byte\n", sizeof(scores));
    printf("p: %zu byte\n", sizeof(p));
    printf("eleman sayısı: %zu\n", sizeof(scores) / sizeof(scores[0]));
    return 0;
}
```

```
int: 4 byte
age: 4 byte
scores: 20 byte
p: 8 byte
eleman sayısı: 5
```

(`%zu`, `sizeof`'un sonucunu yazdırmak için kullanılan biçim. Bunun neden `%d` olmadığını Ders 3.4'te göreceğiz.)

- Bir `int` **4 byte** tutuyor.
- 5 `int`'lik bir array 5 × 4 = **20 byte**. Ders 2.4'te "array, yan yana kutular" demiştik; işte o kutular.
- İki `int`'lik bir struct 2 × 4 = **8 byte**.

Son satırdaki hile kullanışlı: array'in toplam boyutunu bir elemanın boyutuna bölünce **eleman sayısı** çıkıyor. Böylece array'in boyutunu `#define` ile ayrıca yazmadan bulabilirsin. (Bir uyarı: bu hile, Ders 2.4'te fonksiyona verdiğimiz array'lerde **çalışmaz**. Nedenini Faz 4'te, array'lerin fonksiyona nasıl verildiğini görünce anlayacağız.)

`sizeof` bir fonksiyon gibi görünse de değildir: bir **operatör**dür ve cevabı program çalışmadan önce, derleme sırasında bilinir. Compiler her değişkenin tipini bildiği için boyutunu da bilir.

---

## 2. Byte sayısından değer aralığına

4 byte = 32 bit. Faz 0'daki kuralı hatırla: **n bit ile 2ⁿ farklı değer** gösterilebilir.

2³² = 4.294.967.296 farklı değer. Bunların yarısı negatif, yarısı sıfır ve pozitif sayılar için kullanılır:

| | Değer |
| --- | --- |
| Toplam farklı değer | 2³² = 4.294.967.296 |
| En küçük | −2³¹ = **−2.147.483.648** (`INT_MIN`) |
| En büyük | 2³¹ − 1 = **2.147.483.647** (`INT_MAX`) |

Ders 2.11'deki asimetri buradan geliyor: 0 da pozitif taraftaki yerlerden birini kullanıyor. Negatif tarafta 2³¹ sayı var, sıfır ve pozitif tarafta da 2³¹; ama bunlardan biri 0 olduğu için en büyük pozitif sayı 2³¹ − 1. Negatif sayıların bitlerle tam olarak nasıl gösterildiğini Ders 3.3'te göreceğiz.

**Overflow'un sebebi de bu.** 13! = 6.227.020.800 sayısını 32 bitle göstermenin yolu yok. Ne kadar akıllı bir program yazarsan yaz, 4 byte'lık kutuya 4 byte'tan büyük bir sayı sığmaz. Daha büyük sayılar için daha büyük kutulara, yani **başka tiplere** ihtiyacımız var. Ders 3.2'nin konusu bu.

**Küsurat kaybının sebebi de bu.** 32 bitin her birini tamsayıları göstermek için kullandık; küsurata ayrılmış tek bir bit yok. 22,86'yı gösterebilmek için bitlerin bir kısmını virgülden sonrasına ayırmamız gerekir. Ders 2.15'te bunu elle yaptık: sayıyı 100 ile çarpıp tuttuk. Ders 3.11'de bu fikri düzenli bir biçime sokacağız, Ders 3.12'de de bilgisayarın küsuratlı sayılar için kullandığı asıl yöntemi göreceğiz.

---

## 3. Aynı program, farklı platform

Şimdi rahatsız edici bir gerçek: **C standardı, bir `int`'in 4 byte olacağını söylemez.**

Standart sadece bir alt sınır koyar: bir `int` en az 16 bit, yani en az 2 byte olmalıdır. Gerisi platforma kalmıştır. Bugünkü bilgisayarların neredeyse hepsinde `int` 4 byte; ama her yerde değil.

Bunu kendi gözümüzle görebiliriz. clang sadece kendi bilgisayarın için değil, **başka platformlar için de** derleme yapabilir; buna **cross-compilation** denir. Aynı küçük dosyayı birkaç farklı platform için derleyip `sizeof(int)`'in kaç çıktığına baktık:

| Platform | `sizeof(int)` | `INT_MAX` |
| --- | --- | --- |
| macOS (Apple Silicon) | 4 | 2.147.483.647 |
| Linux, 64 bit | 4 | 2.147.483.647 |
| Windows, 64 bit | 4 | 2.147.483.647 |
| **Arduino Uno** (AVR işlemci) | **2** | **32.767** |

Arduino Uno, dünyada en çok kullanılan mikrodenetleyici kartlarından biri: elektronik projelerinde, okullarda, robotlarda. Ve orada `int` sadece 2 byte.

Ders 2.3'teki vücut kitle indeksi satırını hatırla:

```c
int bmi = weight * 10000 / (height * height);
```

70 kg ve 175 cm için önce `weight * 10000` = 700.000 hesaplanır. Bilgisayarında sorun yok. Ama Arduino'da `int`'in alabileceği en büyük değer 32.767; 700.000 sığmaz ve **overflow** olur. Bilgisayarında mükemmel çalışan program, Arduino'da saçma bir sonuç verir. Hiçbir satırı değiştirmeden.

Hatta `height * height` = 30.625 bile sınırın kıl payı altında; 182 cm'lik biri için 33.124 olur ve o da sığmaz.

Bu bir istisna değil. Ders 3.2'de göreceğimiz gibi `long` tipinin boyutu Linux ile Windows arasında bile farklı. C'nin "her makineye uyum sağlayan" tasarımının bedeli bu: **tiplerin boyutunu varsaymak yerine bilmek zorundasın.**

---

## 4. Faz 3'te neler var?

Bu fazda tiplerin perde arkasına bakacağız:

- **Hangi tamsayı tipleri var**, hangisi ne kadar büyük, hangisi neyi garanti ediyor? (3.2–3.4)
- **Negatif sayılar** bitlerle nasıl gösteriliyor, `INT_MIN` neden bir fazla? (3.3)
- Farklı tipler bir araya gelince **neler oluyor**, hangi tuzaklar var? (3.5–3.8)
- Çok byte'lık bir sayı **bellekte hangi sırayla** duruyor? (3.9)
- **Küsuratlı sayılar** nasıl tutuluyor, 0,1 + 0,2 neden 0,3 etmiyor? (3.11–3.14)
- Sayıları metne, metni sayıya çeviren fonksiyonları **sıfırdan** yazmak. (3.16–3.20)
- Ve fazın sonunda, bunların hepsini kullanan kendi **`printf`**'imiz. (3.22)

Faz 2'de "neden 22, neden 13! yanlış" diye sorduğun her şeyin cevabı bu fazda.

---

## Alıştırmalar

**1** – Kendi bilgisayarında `sizeof(int)`'in ve 10 elemanlı bir `int` array'inin boyutunu yazdır. Sonuçlar bu dersteki tabloyla uyuşuyor mu?

**2** – Ders 2.4'teki labirent haritası (`int map[7][11]`) bellekte kaç byte tutar? Önce hesapla, sonra `sizeof` ile kontrol et. Harita `int` yerine her kutusu 1 byte olan bir tiple tutulsaydı kaç byte olurdu?

**3** – `int`'in **2 byte** olduğu bir platformda en küçük ve en büyük `int` değerleri ne olur? Hesapla.

**4** – Ders 2.15'teki sağlık hesaplayıcısının `bmi_x100` fonksiyonu `weight_kg * 1000000` hesaplıyordu. Bu program Arduino Uno'da doğru çalışır mı? Hangi değerlerde sorun çıkar? Programın geri kalanına da bak.

<details>
<summary>Cevaplar</summary>

**1** – Bugünkü bilgisayarların neredeyse hepsinde `sizeof(int)` 4 ve 10 elemanlı array 40 byte çıkar.

**2** – 7 × 11 = 77 kutu, her biri 4 byte: **308 byte**. `sizeof(map)` de 308 der. Her kutu 1 byte olsaydı 77 byte olurdu; dört kat daha az. Haritadaki değerler sadece 0, 1 ve 2 olduğu için 4 byte'lık bir `int` aslında çok fazla. Ders 3.2'de 1 byte'lık bir tip göreceğiz.

**3** – 2 byte = 16 bit, 2¹⁶ = 65.536 farklı değer. En küçük: −2¹⁵ = **−32.768**, en büyük: 2¹⁵ − 1 = **32.767**. Arduino'daki `INT_MAX` tam olarak bu.

**4** – Kısmen; ve sonuç seni şaşırtabilir.

Önce iyi haber: `1000000` gibi bir sabit, 2 byte'lık `int`'e sığmadığı için C onu otomatik olarak daha büyük bir tip olan `long` kabul eder (Arduino'da 4 byte; ayrıntısı Ders 3.10'da). Bu yüzden `weight_kg * 1000000` aslında `long` ile hesaplanır ve 300 kg için bile sığar.

Kötü haber paydada: `height_cm * height_cm` iki `int`'in çarpımı. 181 cm için 32.761 eder ve kıl payı sığar; **182 cm**'den itibaren (33.124) overflow olur. Yani boyu 1,82 m ve üstü olan herkes için vücut kitle indeksi yanlış çıkar.

Kalori hesabı daha da kötü: `625 * height_cm`, en kısa boy olan 100 cm için bile 62.500 eder ve sığmaz. Kalori sonucu **her** girdide yanlış olur.

Bütün bunları Arduino için derlerken compiler hiçbir uyarı vermez. Bilgisayarında `-Werror` ve sanitizer'larla tertemiz çalışan bir program, sadece platform değişti diye işe yaramaz hale geliyor. Tiplerin boyutunu **varsaymak** yerine **bilmek** bu yüzden şart.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.1: bilgiyi bit olarak saklamak, tiplerin boyutları.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 3: aritmetik tipler.

**Sıradaki ders:** `char`, `short`, `int`, `long`, `long long`. C'nin tamsayı tipleri, standardın neyi garanti ettiği ve neyi platforma bıraktığı.
