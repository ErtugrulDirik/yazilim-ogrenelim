---
title: "3.18 Dönüşüm sıfırdan 3: print_bin ve print_hex"
description: "Bölme ve kalan yerine bit kaydırma (<<, >>) ve maske (&, |): bir sayıyı ikilik ve onaltılık tabanda yazdırmak, float'ın bitlerini maskeyle ayırmak, belleği byte byte dökmek; compiler'ın bölmeyi zaten kaydırmaya çevirdiği, işaretli sayılarda kaydırmanın tuzakları ve & ile && farkı. Faz 5'e köprü."
---

Faz 3 boyunca bitlere bakmak için hep aynı numarayı kullandık: bölme ve kalan. Ders 3.3'teki `print_bits` `b / w % 2` hesaplıyordu, Ders 3.9'daki `write_be32` `x / 16777216`, Ders 3.12'deki `show_float` `bits / 8388608 % 256`. Hepsi doğru çalıştı. Ama her seferinde 2'nin bir kuvvetini kafadan hesaplamak zorunda kaldık, ve kod ne yaptığını açıkça söylemiyordu.

C'nin bu iş için ayrı operatörleri var: bitleri **kaydırmak** ve **maskelemek**. Bütün ayrıntılarını Faz 5'te göreceğiz. Bu derste sadece dört tanesini, bitleri yazdırmaya yetecek kadarını öğreneceğiz ve Faz 3'te yazdığımız fonksiyonları onlarla yeniden yazacağız.

---

## 1. Kaydırma: << ve >>

Ondalık bir sayıyı 1000 ile çarpmak için sağına üç sıfır yazarız: 42 → 42000. 1000'e bölmek için de son üç basamağı sileriz: 42.317 → 42. Basamakları kaydırıyoruz.

İkilikte aynı şey 2'nin kuvvetleriyle olur:

| İfade | Anlamı | Örnek |
| --- | --- | --- |
| `x << n` | Bitleri `n` basamak **sola** kaydır, sağdan 0 ekle | `5u << 3` = `101` → `101000` = 40 = 5 × 2³ |
| `x >> n` | Bitleri `n` basamak **sağa** kaydır, sağdaki `n` biti at | `0xABCDu >> 4` = `0xABC` = 2748 = 43.981 / 2⁴ |

İşaretsiz sayılarda `x << n`, x × 2ⁿ ile; `x >> n` de x / 2ⁿ ile tamamen aynı. Ders 3.15'te compiler'ın 65.536 ile çarpmayı `shl rcx, 16`'ya çevirdiğini görmüştük: işte o komutun C'deki karşılığı.

Onaltılık tabanda her basamak 4 bit olduğu için (Ders 3.10), 4'ün katları kadar kaydırmak onaltılık basamakları kaydırmak demek: `0xABCD >> 4` = `0xABC`, `0xABCD >> 8` = `0xAB`. Onaltılık sayılarla bitlerle çalışmanın kolay olmasının sebebi bu.

---

## 2. Maske: & ve |

Faz 0'da mantık kapılarını görmüştük: AND, OR, NOT. C'de bunların **bit bit** çalışan halleri var. İki sayının her bitini, karşısındaki bitle işleme sokarlar:

| `a` | `b` | `a & b` (AND) | `a \| b` (OR) |
| --- | --- | --- | --- |
| 0 | 0 | 0 | 0 |
| 0 | 1 | 0 | 1 |
| 1 | 0 | 0 | 1 |
| 1 | 1 | 1 | 1 |

```
  0xF0 = 11110000          0xF0 = 11110000
& 0x3C = 00111100        | 0x0F = 00001111
       = 00110000 = 48          = 11111111 = 255
```

`&`'in asıl kullanımı **maske**: bir sayının sadece istediğin bitlerini bırakıp gerisini sıfırlamak. Maskede 1 olan bitler kalır, 0 olanlar silinir.

| İfade | Ne verir? | Bölme–kalan karşılığı |
| --- | --- | --- |
| `x & 1` | En sağdaki bit | `x % 2` |
| `x & 0xF` | En sağdaki 4 bit (son onaltılık basamak) | `x % 16` |
| `x & 0xFF` | En sağdaki byte | `x % 256` |
| `x & 0x7FFFFF` | En sağdaki 23 bit | `x % 8388608` |

Kaydırma ile maske birlikte, bir sayının **ortasındaki** bitleri çıkarır: önce istediğin bitleri en sağa kaydır, sonra maskele.

> `(x >> n) & 1` → `n` numaralı bit (sağdan, 0'dan başlayarak)
>
> `(x >> 4) & 0xF` → sağdan ikinci onaltılık basamak

`0xABCD` için: `(0xABCD >> 8) & 0xFF` = `0xAB` = 171.

`|` ise parçaları **birleştirmek** için: `0xAB << 8 | 0xCD` = `0xABCD`. Bölüm 5'te byte'ları bir araya getirirken kullanacağız.

---

## 3. print_bin ve print_hex

Ders 3.7'deki `print_bits`, en soldaki bitin basamak değerini (2^(width − 1)) bir döngüyle hesaplayıp her adımda ikiye bölüyordu. Kaydırma ile:

```c
#include <stdio.h>
#include <stdint.h>

void print_bin(uint32_t x, int width) {
    for (int i = width - 1; i >= 0; i--) {
        putchar((x >> i) & 1 ? '1' : '0');
        if (i % 8 == 0 && i > 0) {
            putchar(' ');
        }
    }
}
```

Her adımda `i` numaralı biti sağa kaydırıp maskeyle alıyoruz; en soldaki bitten (`width - 1`) en sağdakine (0) doğru. 8 bitte bir boşluk bırakıyoruz.

Onaltılık için aynı fikir, 4 bitlik gruplarla, ve Ders 3.16'daki rakam tablosuyla:

```c
void print_hex(uint64_t x, int digits) {
    const char hex[] = "0123456789abcdef";
    for (int i = digits - 1; i >= 0; i--) {
        putchar(hex[(x >> (4 * i)) & 0xF]);
    }
}
```

`i` numaralı onaltılık basamak, `4 * i` bit sağda duruyor. Parametreyi `uint64_t` yaptık ki `double`'ın 64 bitini de yazdırabilelim; `uint32_t` bir değer verince Ders 3.7'deki Kural 1 gereği değeri değişmeden genişler.

Ders 3.16'daki `itoa`'dan farkı: basamak sayısını çağıran veriyor, ve fonksiyon **baştaki sıfırları da** yazıyor. Bitlere bakarken istediğimiz bu: `print_hex(255, 8)` `000000ff` yazar, bir `uint32_t`'nin bütün 32 bitini gösterir.

```c
int main(void) {
    print_bin(16909060, 32);
    putchar('\n');
    print_hex(16909060, 8);
    putchar('\n');
    print_hex(48879, 4);
    putchar('\n');
    return 0;
}
```

```
00000001 00000010 00000011 00000100
01020304
beef
```

Ders 3.9'daki 16.909.060: dört byte'ı 1, 2, 3, 4. İkilikteki her 8'li grup, onaltılıktaki 2 basamağa karşılık geliyor.

`itoa` ile karşılaştır: `itoa` herhangi bir tabanda çalışıyordu ama her basamak için bir bölme yapıyordu. `print_bin` ve `print_hex` sadece 2'nin kuvveti olan tabanlarda çalışıyor; karşılığında hiç bölme yok, ve hangi bitin nereye gittiği kodda açıkça görünüyor.

---

## 4. Compiler zaten biliyordu

Peki eski `print_bits` gerçekten daha mı yavaştı? Ders 3.5'teki gibi godbolt'a soralım (**x86-64 clang**, **`-O2`**):

```c
#include <stdint.h>

uint32_t nibble_div(uint32_t x) {
    return x / 16 % 16;
}

uint32_t nibble_shift(uint32_t x) {
    return (x >> 4) & 0xF;
}
```

```asm
nibble_div:
        mov     eax, edi
        shr     eax, 4
        and     eax, 15
        ret

nibble_shift:
        mov     eax, edi
        shr     eax, 4
        and     eax, 15
        ret
```

**Birebir aynı.** Compiler, işaretsiz bir sayıyı 16'ya bölmenin 4 bit sağa kaydırmak, 16'ya göre kalanın da son 4 biti maskelemek olduğunu biliyor. Ders 3.12'deki `show_float` da `-O2` ile derlendiğinde aslında kaydırma ve maskeyle çalışıyordu.

O halde neden yeni operatörler? Çünkü kod **ne demek istediğini** söylemeli. `bits / 8388608 % 256` bir okuyucuya hiçbir şey anlatmaz; `(bits >> 23) & 0xFF` "23 bit sağa kaydır, 8 bit al" der. Bitlerle çalışırken bitlerin dilini konuş.

### İşaretli sayılarda fark

Aynı karşılaştırmayı `int32_t` ile yapalım:

```c
int32_t sdiv16(int32_t x) {
    return x / 16;
}

int32_t sshr4(int32_t x) {
    return x >> 4;
}
```

```asm
sdiv16:
        lea     eax, [rdi + 15]
        test    edi, edi
        cmovns  eax, edi
        sar     eax, 4
        ret

sshr4:
        mov     eax, edi
        sar     eax, 4
        ret
```

Bu sefer farklılar. Sebebi negatif sayılar:

| `x` | `x / 4` | `x >> 2` |
| --- | --- | --- |
| −16 | −4 | −4 |
| −15 | **−3** | **−4** |

C'de bölme **sıfıra doğru** yuvarlar (Ders 3.11'deki `fx_to_int`): −15 / 4 = −3,75 → −3. Sağa kaydırma ise ikiler tümleyeninde **aşağı doğru** yuvarlar: −3,75 → −4. Compiler `x / 16`'yı kaydırmaya çevirirken, negatif sayılar için önce 15 ekleyerek (`lea eax, [rdi + 15]`; `cmovns` bunu sadece negatif sayılar için seçiyor) sonucu düzeltmek zorunda kalıyor.

Üstelik negatif bir sayıyı sağa kaydırmanın sonucu C standardında **platforma bağlı** (implementation-defined). Bugünkü bütün compiler'lar işaret bitini kopyalayarak kaydırıyor (`sar`, **s**hift **a**rithmetic **r**ight), ama standart bunu söz vermiyor.

---

## 5. Tuzaklar

### Kural: bitlerle işaretsiz çalış

Kaydırmanın tanımsız ya da platforma bağlı olduğu durumlar, neredeyse hep işaretli sayılarda. `-fsanitize=undefined` ile denedik:

```c
int n = 31;
printf("%d\n", 1 << n);
```

```
runtime error: left shift of 1 by 31 places cannot be represented in type 'int'
```

`1` bir `int` sabiti (Ders 3.10). Onu 31 bit sola kaydırmak, 1'i işaret bitine taşımak demek; sonuç 2³¹, `int`'e sığmaz: undefined behavior. `1u << 31` ise 2.147.483.648, tamamen tanımlı. Bitlerle çalışırken sabitlere `u` ekle, değişkenleri `uint32_t` gibi işaretsiz tiplerden seç.

### Tipin genişliğinden fazla kaydırmak

```c
uint32_t x = 1;
int s = 32;
printf("%u\n", x << s);
```

```
runtime error: shift exponent 32 is too large for 32-bit type 'uint32_t' (aka 'unsigned int')
```

32 bitlik bir sayıyı 32 ya da daha fazla bit kaydırmak, işaretsiz de olsa **undefined behavior**. "Bütün bitler dışarı çıkar, sonuç 0 olur" diye düşünmek doğal, ama donanım böyle çalışmıyor: x86 ve ARM, 32 bitlik kaydırmada kaydırma miktarının sadece son 5 bitine bakar. Bilgisayarımızda sonuç 0 değil **1** çıktı: 32 kaydırma, 0 kaydırma gibi davrandı. Negatif bir miktar kadar kaydırmak da tanımsız.

### & ile && aynı şey değil

```c
unsigned a = 6;
unsigned b = 1;
printf("%u %d\n", a & b, a && b);
```

```
0 1
```

`&&` (Ders 2.3) **mantıksal** VE: iki taraf da sıfırdan farklı mı? 6 ve 1, ikisi de "doğru"; sonuç 1. `&` ise **bit bit** VE: `110 & 001` = `000`. Birini ötekinin yerine yazmak sessiz bir hata; aynısı `|` ile `||` için de geçerli.

### Öncelik

16'nın 16'ya bölünüp bölünmediğine bakalım:

```c
unsigned x = 16;
if (x & 0xF == 0) {
    printf("bölünür\n");
} else {
    printf("bölünmez\n");
}
```

```
bölünmez
```

`&`'in önceliği `==`'den **düşük**. Bu satır `x & (0xF == 0)` diye okunuyor; `0xF == 0` yanlış, yani 0; `16 & 0` = 0; koşul yanlış. C'nin tarihinden kalan bir garip kural: `&` eskiden `&&`'in işini de görüyordu ve önceliği ona göre seçilmişti. Neyse ki clang bunu `-Wall` ile yakalıyor:

```
warning: & has lower precedence than ==; == will be evaluated first [-Wparentheses]
```

Kural: bit operatörlerini karşılaştırmalarla birlikte kullanırken **her zaman parantez** koy: `(x & 0xF) == 0`.

---

## 6. Eski fonksiyonlar, yeni operatörler

### show_float

Ders 3.12'deki `show_float`'un parçaları ayıran üç satırı:

```c
uint32_t sign = bits / 2147483648u;
uint32_t exponent = bits / 8388608 % 256;
uint32_t mantissa = bits % 8388608;
```

Aynı şey, float'ın düzenini doğrudan anlatarak:

```c
uint32_t sign = bits >> 31;
uint32_t exponent = (bits >> 23) & 0xFF;
uint32_t mantissa = bits & 0x7FFFFF;
```

- İşaret en soldaki bit: 31 bit kaydırınca o kalıyor.
- Üs, sağdan 23 bit sonra başlayan 8 bit: kaydır, `0xFF` ile maskele.
- Mantis, sağdaki 23 bit: `0x7FFFFF`, 23 tane 1.

```
5.75         0 10000001 01110000000000000000000  0x40b80000
-0.100000001 1 01111011 10011001100110011001101  0xbdcccccd
```

`double` için sadece sayılar değişiyor: işaret `bits >> 63`, üs `(bits >> 52) & 0x7FF`, mantis `bits & 0xFFFFFFFFFFFFF` (52 bit). `print_hex` ile 0,1'in `double` bitleri: `3fb999999999999a`, Ders 3.14'teki değer. Ders 3.19'da bu üç satırı bir `double`'ı doğru yazdırmak için kullanacağız.

### Bellek dökümü

Ders 3.9'da `memcpy` ile bir sayının byte'larını bellekteki sırayla bir array'e kopyalamıştık. `print_hex` ile her byte'ı iki onaltılık basamak olarak yazdıralım:

```c
#include <string.h>

int main(void) {
    int32_t n = 16909060;
    uint8_t bytes[4];
    memcpy(bytes, &n, sizeof(n));
    for (int i = 0; i < 4; i++) {
        print_hex(bytes[i], 2);
        putchar(' ');
    }
    putchar('\n');

    double d = 0.1;
    uint8_t dbytes[8];
    memcpy(dbytes, &d, sizeof(d));
    for (int i = 0; i < 8; i++) {
        print_hex(dbytes[i], 2);
        putchar(' ');
    }
    putchar('\n');
    return 0;
}
```

```
04 03 02 01
9a 99 99 99 99 99 b9 3f
```

Ders 3.9'daki little endian düzen: en anlamsız byte başta. `double` da istisna değil: `3fb999999999999a`'nın byte'ları bellekte tersten duruyor. Bellekteki byte'ları böyle onaltılık yazdıran araçlara **hex dump** denir; debugger'lar, dosya formatı incelemeleri ve ağ analizi hep bu görünümü kullanır. LLDB'de (Ders 2.6) `memory read` komutu aynı şeyi yapar.

### write_be32 ve read_be32

Ders 3.9'da bu fonksiyonları bölmeyle yazmış ve "Faz 5'te çok daha kısa yazacağız" demiştik:

```c
void write_be32(uint8_t out[], uint32_t x) {
    out[0] = (uint8_t)(x >> 24);
    out[1] = (uint8_t)(x >> 16);
    out[2] = (uint8_t)(x >> 8);
    out[3] = (uint8_t)x;
}

uint32_t read_be32(const uint8_t in[]) {
    return (uint32_t)in[0] << 24 | (uint32_t)in[1] << 16
         | (uint32_t)in[2] << 8 | in[3];
}
```

- `write_be32`'de maske bile gerekmiyor: `(uint8_t)` cast'i, Ders 3.7'deki Kural 2 gereği sadece en sağdaki 8 biti bırakıyor.
- `read_be32`, byte'ları yerlerine kaydırıp `|` ile birleştiriyor. Bit grupları çakışmadığı için `|` ile `+` aynı sonucu verir; `|` "parçaları birleştiriyorum" niyetini daha açık söyler.
- `(uint32_t)` cast'leri hâlâ şart: `in[0] << 24`, cast olmadan Ders 3.5 gereği `int` ile hesaplanırdı ve `in[0]` 128 ya da daha büyükse 1'i işaret bitine taşırdı. Bölüm 5'teki ilk tuzak.
- `<<`'nin önceliği `|`'den yüksek; burada parantez gerekmiyor.

---

## Alıştırmalar

**1** – Çalıştırmadan hesapla: `0xABCDu >> 4`, `0xABCDu & 0xF`, `(0xABCDu >> 8) & 0xFF`, `5u << 3`, `0xF0u | 0x0Fu`. Sonuçları onluk ve onaltılık tabanda yaz.

**2** – Bir `uint32_t`'nin kaç bitinin 1 olduğunu sayan `int count_ones(uint32_t x)` fonksiyonunu yaz: en sağdaki biti `& 1` ile oku, sonra sayıyı 1 bit sağa kaydır. 255, `0xF0F0`, `UINT32_MAX` ve 0 için dene. Döngü neden her zaman biter?

**3** – `print_hex`'in, baştaki sıfırları yazmayan bir halini yaz: `print_hex_short(255)` `ff`, `print_hex_short(0x1000)` `1000` yazsın. 0 için ne yazmalı?

**4** – Bir sayının 8'in katı olup olmadığını `%` kullanmadan, `&` ile kontrol et. Neden çalışıyor? Aynı yöntem 10'un katları için çalışır mı?

**5** – Ders 3.4'teki `uint8_t` ile bir RGB rengi tutmak istiyorsun: kırmızı, yeşil ve mavi, her biri 0–255. Üçünü tek bir `uint32_t`'de `0x00RRGGBB` biçiminde birleştiren `pack_rgb(uint8_t r, uint8_t g, uint8_t b)` ve tersini yapan üç fonksiyonu (`red`, `green`, `blue`) yaz. Turuncu (255, 165, 0) hangi sayıya dönüşür? `print_hex` ile yazdır.

<details>
<summary>Cevaplar</summary>

**1** –

| İfade | Onaltılık | Onluk |
| --- | --- | --- |
| `0xABCDu >> 4` | `0xABC` | 2748 |
| `0xABCDu & 0xF` | `0xD` | 13 |
| `(0xABCDu >> 8) & 0xFF` | `0xAB` | 171 |
| `5u << 3` | `0x28` | 40 |
| `0xF0u \| 0x0Fu` | `0xFF` | 255 |

**2** –

```c
int count_ones(uint32_t x) {
    int count = 0;
    while (x != 0) {
        count = count + (x & 1);
        x = x >> 1;
    }
    return count;
}
```

Sonuçlar: **8**, **8**, **32**, **0**. Her adımda en soldaki 1 bit, bir basamak sağa kayıyor; en fazla 32 adımda bütün bitler dışarı çıkar ve `x` 0 olur. `x` işaretli olsaydı ve negatif olsaydı, `>>` işaret bitini kopyalayabileceği için (Bölüm 4) `x` hiçbir zaman 0 olmayabilirdi: −1 >> 1, −1. İşaretsiz çalışmanın bir sebebi daha. Bu işlemin adı **popcount**; Faz 5'te çok daha hızlı yollarını ve işlemcinin bunu tek komutla yaptığını göreceğiz.

**3** –

```c
void print_hex_short(uint32_t x) {
    const char hex[] = "0123456789abcdef";
    int i = 7;
    while (i > 0 && ((x >> (4 * i)) & 0xF) == 0) {
        i--;
    }
    for (; i >= 0; i--) {
        putchar(hex[(x >> (4 * i)) & 0xF]);
    }
}
```

En soldaki sıfır olmayan basamağı bulup oradan başlıyor. 0 için **`0`** yazmalı: `i > 0` koşulu en sağdaki basamağı her zaman yazdırıyor; Ders 3.16'daki `do`–`while` ile aynı sebep. `((x >> (4 * i)) & 0xF) == 0`'daki parantezler Bölüm 5'teki öncelik tuzağı yüzünden şart.

**4** – `(x & 7) == 0`. 8 = 2³; bir sayı 8'in katıysa, ikilikte son üç biti 0'dır (ondalıkta 1000'in katlarının son üç basamağının 0 olması gibi). 7 = `111`, son üç biti seçen maske. 10'un katları için **çalışmaz**: 10 2'nin kuvveti değil, ve "10'a bölünebilmek" ikilik basamaklarda düzenli bir desene karşılık gelmiyor. Genel kural: `x % 2ⁿ` = `x & (2ⁿ − 1)`, sadece işaretsiz sayılar için.

**5** –

```c
uint32_t pack_rgb(uint8_t r, uint8_t g, uint8_t b) {
    return (uint32_t)r << 16 | (uint32_t)g << 8 | b;
}

uint8_t red(uint32_t c) {
    return (uint8_t)(c >> 16);
}

uint8_t green(uint32_t c) {
    return (uint8_t)(c >> 8);
}

uint8_t blue(uint32_t c) {
    return (uint8_t)c;
}
```

Turuncu: 255 << 16 = `0xFF0000`, 165 << 8 = `0xA500`, `0x00`; birleşince **`0x00ffa500`** = 16.753.920. Web sayfalarındaki `#ffa500` renk kodu tam olarak bu.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.9: bit operatörleri.
- C standardı (ISO/IEC 9899:2018), §6.5.7: kaydırma operatörleri (taşan sola kaydırma ve tip genişliğinden fazla kaydırma undefined, negatif sayıyı sağa kaydırma implementation-defined); §6.5.10–6.5.12: `&`, `^`, `|`.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.1.7–2.1.9: bit düzeyinde işlemler, maskeler ve kaydırmalar.

**Sıradaki ders:** Dönüşüm sıfırdan 4: `ftoa`. Bir `double`'ı yazıya çevirmek, ve `printf("%.2f")`'nin neden göründüğünden çok daha zor bir iş yaptığı.
