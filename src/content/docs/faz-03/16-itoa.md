---
title: "3.16 Dönüşüm sıfırdan 1: itoa"
description: "Bir tamsayıyı 2 ile 36 arasındaki herhangi bir tabanda yazıya çevirmek: kalanla basamak ayırma, rakamı karaktere çevirme, sonunda '\\0' olan char array'ler, ters çevirme adımı, negatif sayılar ve INT_MIN tuzağı, tampon boyutunun hesabı ve tampon taşması."
---

Faz 2'den beri `printf("%d", x)` yazıyoruz ve sayı ekranda beliriyor. Ama bilgisayarın belleğinde duran şey bir sayı: 1234, `int` içinde 32 bitlik bir desen (Ders 3.3). Ekrana yazılan ise dört **karakter**: `'1'`, `'2'`, `'3'`, `'4'`. Arada bir dönüşüm var ve `printf` onu bizden saklıyor.

Bu derste o dönüşümü sıfırdan yazacağız: **itoa** (integer to ASCII). Üstelik `printf`'ten daha fazlasını yapacak: Ders 3.10'da `%b`'nin henüz desteklenmediğini görmüştük; bizim fonksiyonumuz ikilikte, onaltılıkta ve 36'ya kadar her tabanda yazacak. Ders 3.17'de de tersini yazacağız: yazıyı sayıya çevirmek.

(`itoa` adı yaygın, ama standart C'de böyle bir fonksiyon yok. Bazı compiler'lar kendi kütüphanelerinde sunuyor; hepsinin parametreleri farklı.)

---

## 1. Basamakları ayırmak

Ders 2.8'deki basamak toplamını hatırla: `n % 10` son basamağı verir, `n / 10` son basamağı atar. 1234'e uygulayalım:

| Adım | `value` | `value % 10` | `value / 10` |
| --- | --- | --- | --- |
| 1 | 1234 | **4** | 123 |
| 2 | 123 | **3** | 12 |
| 3 | 12 | **2** | 1 |
| 4 | 1 | **1** | 0 |

`value` 0 olunca duruyoruz. Basamaklar çıktı, ama **ters sırayla**: 4, 3, 2, 1. Sayının en anlamsız basamağı en kolay ulaşılanı; Ders 3.9'daki byte'larda da böyleydi.

10 yerine herhangi bir taban `b` yazarsak aynı şey çalışır: `value % b`, o tabandaki son basamak. 1234'ü 16'lık tabana çevirelim:

| Adım | `value` | `value % 16` | `value / 16` |
| --- | --- | --- | --- |
| 1 | 1234 | 2 | 77 |
| 2 | 77 | **13** | 4 |
| 3 | 4 | 4 | 0 |

Ters sırayla 4, 13, 2. 13 onaltılıkta `d`: **`4d2`**. Ders 3.10'da `%x` ile gördüğümüz sonuç.

---

## 2. Rakamı karaktere çevirmek

Elimizde 4 sayısı var; yazmak istediğimiz ise `'4'` karakteri. Faz 0'daki ASCII tablosuna göre ikisi farklı: `'4'` karakterinin değeri 52. Ders 3.2'de `'7' - '0'` = 7 olduğunu görmüştük; rakam karakterleri ASCII'de art arda dizili. Tersi de geçerli:

```c
char c = '0' + 4;   // '4'
```

10'dan büyük tabanlarda 10, 11, 12… için harf gerekiyor: `a`, `b`, `c`… En kısa yol bir **tablo**:

```c
const char digits[] = "0123456789abcdefghijklmnopqrstuvwxyz";
```

`digits[4]` `'4'`, `digits[13]` `'d'`, `digits[35]` `'z'`. Tek bir array erişimi, hiç `if` yok. 10 rakam ve 26 harf, toplam 36 sembol: bu yüzden fonksiyonumuz en fazla **36'lık tabanı** destekleyecek. 36'lık taban gerçekten kullanılıyor: kısa bağlantı servisleri ve bazı sipariş numaraları, büyük sayıları kısa yazmak için onu kullanır.

---

## 3. Yazıyı tutmak: char array ve '\0'

Basamakları bir yere yazmamız gerekiyor. C'de bir yazı (string), **sonunda değeri 0 olan bir karakter bulunan bir `char` array'idir**. O son karaktere **null karakter** denir ve `'\0'` diye yazılır:

```c
char text[4] = {'4', 'd', '2', '\0'};
printf("%s\n", text);
```

```
4d2
```

`%s`, Ders 2.3'ten beri kullandığımız biçim; array'in başından başlar ve `'\0'`'ı görene kadar her karakteri yazar. `'\0'` olmasaydı `printf` array bittiğinde durması gerektiğini bilemezdi ve bellekte ne bulursa yazmaya devam ederdi.

`"0123…z"` gibi çift tırnaklı bir yazı da aynı şeyin kısa yolu: compiler sonuna `'\0'`'ı kendisi ekler. `sizeof(digits)` bu yüzden 36 değil **37**. Stringlerin bütün ayrıntısını (ve neden bu kadar tehlikeli olduklarını) Ders 4.12'de göreceğiz; bu ders için bu kadarı yeterli.

Fonksiyonumuz sonucu döndüremez, çünkü C'de bir fonksiyon array döndüremez. Onun yerine çağıran, bir array hazırlayıp fonksiyona verecek. Ders 2.4'teki kuralı hatırla: array'ler kopyalanmaz, fonksiyon **asıl array'i** değiştirir. Burada tam olarak istediğimiz bu.

---

## 4. Ters çevirmek

Basamaklar ters sırayla çıkıyor. En basit çözüm: önce olduğu gibi yaz, sonra array'i ters çevir. İki uçtan başlayıp ortaya doğru yer değiştir:

```c
void reverse(char s[], int from, int to) {
    while (from < to) {
        char tmp = s[from];
        s[from] = s[to];
        s[to] = tmp;
        from++;
        to--;
    }
}
```

`from` ve `to` parametreleri, array'in sadece bir **parçasını** ters çevirmemizi sağlıyor; eksi işaretini işin dışında bırakmak için birazdan lazım olacak. `"4321"` için `reverse(s, 0, 3)`:

| Adım | `from` | `to` | `s` |
| --- | --- | --- | --- |
| Başta | 0 | 3 | `4321` |
| 1 | 0 | 3 | `1324` |
| 2 | 1 | 2 | `1234` |
| Bitti | 2 | 1 | `1234` |

Uzunluk tek olsaydı ortadaki karakter yerinde kalırdı; `from < to` koşulu onu kendisiyle değiştirmeye çalışmaz.

---

## 5. İşaretsiz sayılar: utoa

Önce işaretsiz sayılarla başlayalım; negatif sayıların tuzağı yok.

```c
int write_digits(unsigned int value, char out[], int start, int base) {
    const char digits[] = "0123456789abcdefghijklmnopqrstuvwxyz";
    int length = start;
    do {
        out[length] = digits[value % base];
        length++;
        value = value / base;
    } while (value != 0);
    out[length] = '\0';
    reverse(out, start, length - 1);
    return length;
}

int utoa(unsigned int value, char out[], int base) {
    if (base < 2 || base > 36) {
        out[0] = '\0';
        return 0;
    }
    return write_digits(value, out, 0, base);
}
```

- **`do`–`while`**, `while` değil. Ders 2.3'teki basamak sayma örneğindeki sebep: 0 da bir basamak. `while (value != 0)` ile başlasaydık 0 için hiçbir basamak yazılmaz ve sonuç boş bir yazı olurdu.
- `write_digits`, basamakları `out`'un `start` numaralı yerinden itibaren yazar. Şimdilik `start` 0; bir sonraki bölümde eksi işaretine yer açmak için kullanacağız.
- Basamakların arkasına `'\0'` koyuyoruz, sonra **sadece basamakları** ters çeviriyoruz.
- Fonksiyonlar yazının uzunluğunu (`'\0'` hariç) döndürüyor. Çağıran için kullanışlı bir bilgi, ve Ders 4.13'teki `strlen`'i çağırmaya gerek bırakmıyor.
- Geçersiz bir tabanda boş bir yazı üretip 0 döndürüyoruz. `base` 0 olsaydı `value % base` sıfıra bölme olurdu (Ders 3.8), 1 olsaydı döngü hiç bitmezdi; bu kontrol ikisini de engelliyor.

```c
char text[33];
utoa(4294967295u, text, 2);
printf("%s\n", text);
utoa(4294967295u, text, 36);
printf("%s\n", text);
```

```
11111111111111111111111111111111
1z141z3
```

`UINT_MAX`'ın 32 tane 1'i, ve 36'lık tabanda sadece 7 karakter.

---

## 6. Negatif sayılar: itoa

İlk akla gelen: sayı negatifse bir `'-'` yaz, sayıyı pozitife çevir, gerisi aynı.

```c
if (value < 0) {
    out[0] = '-';
    value = -value;   // tehlikeli
}
```

Ders 3.8'in 3. alıştırmasını ve Ders 3.11'in 4. alıştırmasını hatırla: `value` `INT_MIN` ise `-value` `int`'e **sığmaz**; undefined behavior. Çözüm de oradakinin aynısı: mutlak değeri `unsigned int` olarak hesaplamak. Her `int`'in mutlak değeri `unsigned int`'e sığar.

```c
int itoa(int value, char out[], int base) {
    if (base < 2 || base > 36) {
        out[0] = '\0';
        return 0;
    }
    unsigned int magnitude = (unsigned int)value;
    int start = 0;
    if (value < 0) {
        out[0] = '-';
        start = 1;
        magnitude = 0u - magnitude;
    }
    return write_digits(magnitude, out, start, base);
}
```

- `(unsigned int)value`: Ders 3.7'deki Kural 2. −1234, 4.294.966.062 olur.
- `0u - magnitude`: işaretsiz aritmetikte 2³² − 4.294.966.062 = **1234**. Hiçbir işlem işaretli değil, hiçbiri taşmıyor. `INT_MIN` için de: 2.147.483.648 → 2.147.483.648.
- Eksi işareti 0 numaralı yerde; basamaklar 1'den başlıyor ve `reverse` işarete dokunmuyor. `write_digits`'e `start` parametresini bu yüzden koyduk.

Deneyelim:

```c
#include <stdio.h>
#include <limits.h>

#define ITOA_BUFFER_SIZE 34

// reverse, write_digits, utoa, itoa

int main(void) {
    char text[ITOA_BUFFER_SIZE];
    int values[] = {0, 7, 1234, -1234, 255, INT_MAX, INT_MIN};
    int count = sizeof(values) / sizeof(values[0]);
    for (int i = 0; i < count; i++) {
        printf("%11d:", values[i]);
        itoa(values[i], text, 10);
        printf(" %s", text);
        itoa(values[i], text, 2);
        printf(" %s", text);
        itoa(values[i], text, 16);
        printf(" %s", text);
        itoa(values[i], text, 36);
        printf(" %s\n", text);
    }
    return 0;
}
```

```
          0: 0 0 0 0
          7: 7 111 7 7
       1234: 1234 10011010010 4d2 ya
      -1234: -1234 -10011010010 -4d2 -ya
        255: 255 11111111 ff 73
 2147483647: 2147483647 1111111111111111111111111111111 7fffffff zik0zj
-2147483648: -2147483648 -10000000000000000000000000000000 -80000000 -zik0zk
```

`-fsanitize=undefined,address` ile çalıştırdık; hiçbir rapor yok.

Bir fark var: bizim fonksiyonumuz −255'i onaltılıkta **`-ff`** diye yazıyor, `printf("%x", -255)` ise **`ffffff01`**. İkisi de doğru, ama farklı soruları cevaplıyor. `%x` işaretsiz bir sayı bekler; −255'in **bitlerini** (ikiler tümleyeni, Ders 3.3) yazar. Bizim `itoa`'mız **değeri** yazar: eksi, ve 255'in onaltılık hali. Bitleri görmek istediğinde `utoa((unsigned int)x, text, 16)` aynı sonucu verir.

---

## 7. Tampon ne kadar büyük olmalı?

`text` array'ine **tampon** (buffer) diyoruz: sonucun yazılacağı, çağıranın hazırladığı alan. Ne kadar büyük olmalı? En uzun sonuç, en küçük tabanda ve en büyük mutlak değerde çıkar: `INT_MIN`, ikilik tabanda.

| Parça | Karakter |
| --- | --- |
| Eksi işareti | 1 |
| 2³¹'in ikilikte basamakları | 32 |
| `'\0'` | 1 |
| **Toplam** | **34** |

`ITOA_BUFFER_SIZE`'ın 34 olmasının sebebi bu. Sadece onluk tabanda yazacaksan 12 yeterli: eksi, 10 basamak ve `'\0'`.

Tampon küçük olursa ne olur? `char text[12]` ile −1234'ü ikilikte yazmayı deneyelim. Sonuç `-10011010010`: 12 karakter, ve `'\0'` için 13. byte gerekiyor. `-fsanitize=address` ile:

```
==50638==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x00016f45e0cc ...
WRITE of size 1 at 0x00016f45e0cc thread T0
    #0 0x0001009a13d8 in write_digits itoa.c:24
    #1 0x0001009a1780 in itoa itoa.c:49
    #2 0x0001009a18c0 in main itoa.c:54
...
  This frame has 1 object(s):
    [32, 44) 'text' (line 53) <== Memory access at offset 44 overflows this variable
```

`write_digits`, `out[length] = '\0'` satırında `text`'in hemen arkasındaki byte'a yazdı. Bu bir **tampon taşması** (buffer overflow). Sanitizer olmadan program büyük ihtimalle sessizce çalışmaya devam ederdi; ama bellekte `text`'in arkasında başka bir değişken varsa, onun bir byte'ı değişmiş olurdu. Tampon taşmaları, yazılım tarihinin en çok istismar edilen güvenlik açıklarından; Ders 4.14'te ayrıntılı göreceğiz.

Fonksiyonumuz tamponun boyutunu bilmiyor; doğru boyutu vermek çağıranın sorumluluğu. Daha güvenli yol, boyutu da parametre olarak almak (3. alıştırma). Standart kütüphanedeki `snprintf` tam olarak böyle çalışır:

```c
char text[12];
snprintf(text, sizeof(text), "%d", -1234);
```

`snprintf`, tampona en fazla `sizeof(text)` byte yazar; sonuç sığmazsa keser ama asla taşmaz. Ama sadece `printf`'in tabanlarını bilir: 8, 10 ve 16.

---

## 8. Makine kodunda % ve /

Döngüdeki her adımda hem `value % base` hem `value / base` hesaplanıyor: iki bölme mi? `write_digits`'i godbolt'ta **x86-64 clang**, **`-O2`** ile derleyince döngüde tek bir bölme komutu var:

```asm
.LBB1_1:
        mov     eax, r9d
        xor     edx, edx
        div     ecx
        movzx   edx, byte ptr [rdx + rbx]
        mov     byte ptr [rsi + r11 + 1], dl
        ...
```

x86'nın `div` komutu bölümü `eax`'e, kalanı `edx`'e **aynı anda** yazar. Compiler, `%` ve `/`'nin aynı iki sayıyla yapıldığını görüp ikisini tek bir `div`'e birleştirdi. Hemen arkasındaki `movzx edx, byte ptr [rdx + rbx]`, kalanı `digits` tablosunda indeks olarak kullanıyor: `digits[value % base]`. (`xor edx, edx`, Ders 3.15'teki `cdq`'nun işaretsiz hali: bölmeden önce `edx`'i sıfırlıyor.)

ARM64'te kalan komutu yok; compiler bölümü `udiv` ile bulup kalanı `msub` (multiply-subtract) ile hesaplıyor: `value - bölüm × base`.

Taban sabit olsaydı, örneğin sadece 10 olsaydı, Ders 3.15'teki 100'e bölme gibi bölme hiç kalmazdı; yerine bir sihirli sayıyla çarpma gelirdi. `printf("%d")`'nin hızlı olmasının bir sebebi bu.

---

## Alıştırmalar

**1** – `utoa(2026, text, 36)`'nın tracing tablosunu çiz (`value`, `value % 36`, karakter, `value / 36`). Sonuç ne? Kontrol için `utoa`'yı çalıştır.

**2** – Ters çevirmeden yazmanın bir yolu: önce sayının kaç basamaklı olduğunu bul, sonra basamakları **sondan başa** doğru doğrudan doğru yerlerine yaz. Önce `int count_digits(unsigned int value, int base)`'i, sonra onu kullanan `utoa_backward`'ı yaz. 0 için doğru çalışıyor mu?

**3** – Tampon boyutunu da alan `int itoa_n(int value, char out[], int size, int base)` yaz. Sonuç (`'\0'` dahil) `size` byte'a sığmıyorsa hiçbir şey yazmadan (`out[0] = '\0'` hariç) −1 döndürsün. `char small[5]` ile 1234, −1234 ve 12345'i dene.

**4** – Büyük sayıları okumak zor: 1234567 yerine **1.234.567** yazan `int format_thousands(int value, char out[])` yaz. (Türkçede binlik ayırıcı nokta.) −1.234.567, 999, 1.000 ve `INT_MIN` için doğru çalışsın. (İpucu: önce `itoa` ile ayırıcısız yaz, sonra karakterleri başka bir array'e kopyalarken arka arkaya kalan basamak sayısına bak.)

**5** – `itoa`'nın `long long` sürümünü yazacak olsaydın neleri değiştirmen gerekirdi? Tamponun boyutu kaç olmalı?

<details>
<summary>Cevaplar</summary>

**1** –

| Adım | `value` | `value % 36` | Karakter | `value / 36` |
| --- | --- | --- | --- | --- |
| 1 | 2026 | 10 | `a` | 56 |
| 2 | 56 | 20 | `k` | 1 |
| 3 | 1 | 1 | `1` | 0 |

Ters çevirince **`1ka`**. Kontrol: 1 × 36² + 20 × 36 + 10 = 1296 + 720 + 10 = 2026.

**2** –

```c
int count_digits(unsigned int value, int base) {
    int count = 0;
    do {
        count++;
        value = value / base;
    } while (value != 0);
    return count;
}

int utoa_backward(unsigned int value, char out[], int base) {
    const char digits[] = "0123456789abcdefghijklmnopqrstuvwxyz";
    int length = count_digits(value, base);
    out[length] = '\0';
    for (int i = length - 1; i >= 0; i--) {
        out[i] = digits[value % base];
        value = value / base;
    }
    return length;
}
```

`do`–`while` sayesinde `count_digits(0, 10)` 1 döndürür ve `utoa_backward` 0 için `"0"` yazar. Bu yolun bedeli, bölmeleri iki kez yapmak: bir kez saymak, bir kez yazmak. `reverse`'ün bedeli ise yer değiştirmeler. Bölme pahalı bir işlem olduğu için çoğu gerçek kütüphane ya ters çevirir ya da sonucu önce yeterince büyük geçici bir tamponun **sonuna** yazıp sonra kopyalar.

**3** –

```c
int itoa_n(int value, char out[], int size, int base) {
    if (base < 2 || base > 36 || size < 1) {
        return -1;
    }
    unsigned int magnitude = (unsigned int)value;
    int sign = value < 0;
    if (sign) {
        magnitude = 0u - magnitude;
    }
    int needed = sign + count_digits(magnitude, base) + 1;
    if (needed > size) {
        out[0] = '\0';
        return -1;
    }
    if (sign) {
        out[0] = '-';
    }
    return write_digits(magnitude, out, sign, base);
}
```

`char small[5]` ile: 1234 → **4** ve `"1234"` (4 basamak + `'\0'` = 5, tam sığıyor). −1234 → **−1** (6 byte gerekiyor). 12345 → **−1**. Hiçbiri taşmıyor; sanitizer temiz. `sign`, `value < 0` karşılaştırmasının sonucu, yani 0 ya da 1; hem eksi işaretinin kapladığı yer hem de basamakların başlangıç yeri olarak kullanılabiliyor.

**4** –

```c
int format_thousands(int value, char out[]) {
    char plain[ITOA_BUFFER_SIZE];
    int length = itoa(value, plain, 10);
    int start = value < 0 ? 1 : 0;
    int j = 0;
    if (start) {
        out[j] = '-';
        j++;
    }
    for (int i = start; i < length; i++) {
        out[j] = plain[i];
        j++;
        int remaining = length - i - 1;
        if (remaining > 0 && remaining % 3 == 0) {
            out[j] = '.';
            j++;
        }
    }
    out[j] = '\0';
    return j;
}
```

Bir basamaktan sonra 3'ün katı kadar basamak kalıyorsa (ve hiç kalmıyor değilse) arkasına nokta koyuyoruz. Sonuçlar: `1.234.567`, `-1.234.567`, `999`, `1.000`, `-2.147.483.648`. `out` için en uzun durum `INT_MIN`: 11 karakter + 3 nokta + `'\0'` = 15 byte.

**5** – Üç şey:

- Parametre `long long`, mutlak değer `unsigned long long`: `magnitude = 0ull - magnitude`. `LLONG_MIN` için de aynı hile çalışır.
- `write_digits`'in `value` parametresi `unsigned long long` olmalı; `% base` ve `/ base` işlemleri o zaman 64 bitle yapılır (Ders 3.5: `base` `int` olsa da `unsigned long long`'a çevrilir).
- Tampon: eksi + 64 basamak + `'\0'` = **66** byte.

`digits` tablosu, `reverse` ve taban kontrolü hiç değişmiyor. Bu tekrarı azaltmanın bir yolu, sadece `unsigned long long` alan tek bir `write_digits` yazıp bütün tipleri ona çevirmek: her işaretsiz tip ona kayıpsız sığar.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §3.6: `itoa` ve `reverse`; ve 3-4. alıştırmadaki en küçük negatif sayı sorusu.
- C standardı (ISO/IEC 9899:2018), §7.21.6.5: `snprintf`; §6.4.5: string sabitleri ve sondaki null karakter.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §3.10.3: tampon taşması.

**Sıradaki ders:** Dönüşüm sıfırdan 2: `atoi` ve `strtol`. Bu sefer yön ters: `"-1234"` yazısını sayıya çevirmek, geçersiz karakterleri ve taşmayı yakalamak.
