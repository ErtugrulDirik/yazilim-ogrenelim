---
title: "3.10 Sayı sabitleri"
description: "Koda yazılan sayıların dili: onaltılık (0x), sekizlik (0) ve ikilik (0b) sabitler, U, L ve LL ekleri, bir sabitin tipinin nasıl belirlendiği, negatif sabitlerin olmayışı ve INT_MIN'in neden (-2147483647-1) diye tanımlandığı."
---

Şu programın ne yazdıracağını tahmin et:

```c
#include <stdio.h>

int main(void) {
    int a = 10;
    int b = 010;
    int c = 0x10;
    int d = 0b10;
    printf("%d %d %d %d\n", a, b, c, d);
    return 0;
}
```

```
10 8 16 2
```

Dört sabit, dört farklı sayı. Başına konan bir `0`, `10`'u **8** yaptı.

Koda doğrudan yazdığımız sayılara **sabit** (constant ya da literal) denir: `10`, `1000000`, `'A'`. Şimdiye kadar onları hiç düşünmeden kullandık. Ama her sabitin bir **tabanı** ve bir **tipi** var, ve ikisi de Faz 3'ün tuzaklarıyla doğrudan ilgili.

---

## 1. Onaltılık sabitler: 0x

Ders 3.9'da 16.909.060 sayısının byte'larını bulmak için bölme yaptık ve sonucu "1 2 3 4" diye yazmak için 256 tabanını kullandık. Ondalık sayıların sorunu bu: byte'ların ve bitlerin sınırları ondalık basamaklarla örtüşmüyor. 16.909.060'a bakarak byte'larını göremezsin.

**Onaltılık** (hexadecimal, kısaca hex) taban, bu sorunu çözer. 16 rakam kullanır: 0–9, sonra A (10), B (11), C (12), D (13), E (14), F (15). C'de bir sayının başına `0x` yazarsan onaltılık olur.

Onaltılığın sihri şu: 16 = 2⁴, yani **bir hex rakamı tam olarak 4 bite** karşılık gelir:

| Hex | Bitler | Ondalık | | Hex | Bitler | Ondalık |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | `0000` | 0 | | 8 | `1000` | 8 |
| 1 | `0001` | 1 | | 9 | `1001` | 9 |
| 2 | `0010` | 2 | | A | `1010` | 10 |
| 3 | `0011` | 3 | | B | `1011` | 11 |
| 4 | `0100` | 4 | | C | `1100` | 12 |
| 5 | `0101` | 5 | | D | `1101` | 13 |
| 6 | `0110` | 6 | | E | `1110` | 14 |
| 7 | `0111` | 7 | | F | `1111` | 15 |

Bir byte 8 bit olduğu için **iki hex rakamıyla** yazılır: `00`'dan `FF`'ye (0–255). Böylece bitlerle hex arasında çeviri yapmak için hiç hesap gerekmez, sadece 4'erli gruplar:

```
11110000 = 1111 0000 = F0 = 240
```

Ders 3.9'daki sayı: 16.909.060 = **`0x01020304`**. Her byte iki hex rakamı: `01`, `02`, `03`, `04`. Byte'ları sayıya bakarak okuyabiliyoruz.

Faz 3'te gördüğümüz bazı sayıların hex halleri:

| Ondalık | Hex | Ne? |
| --- | --- | --- |
| 255 | `0xFF` | 8 bitin hepsi 1, `UINT8_MAX` |
| 65.535 | `0xFFFF` | `UINT16_MAX` |
| 2.147.483.647 | `0x7FFFFFFF` | `INT_MAX`: işaret biti 0, gerisi 1 |
| 2.147.483.648 | `0x80000000` | Sadece işaret biti 1: `INT_MIN`'in bitleri |
| 4.294.967.295 | `0xFFFFFFFF` | `UINT_MAX`, ya da işaretli okununca −1 |

`INT_MAX`'ın neden "2.147.483.647" gibi anlamsız bir sayı olduğunu ondalıkta göremezsin; hex'te bir bakışta görünür.

### Hex yazdırmak

`printf`'in hex için kendi biçimleri var:

```c
printf("%x %X %#x %08x\n", 16909060, 3054, 255, 255);
```

```
1020304 BEE 0xff 000000ff
```

- `%x`: küçük harfle hex. `%X`: büyük harfle.
- `%#x`: başına `0x` ekler.
- `%08x`: en az 8 rakam, gerekirse başına sıfır. Ders 2.13'teki `%02d`'nin aynısı. 32 bitlik bir sayının bütün byte'larını görmek için ideal.

`%x` bir `unsigned int` bekler. `uint8_t` ve `uint16_t` `int`'e yükseltildiği için onlarla da kullanılabilir. `uint32_t` için Ders 3.4'teki `PRIx32`, `uint64_t` için `PRIx64` kullan.

---

## 2. Sekizlik sabitler: 0

Başı `0` ile başlayan bir sayı **sekizlik** (octal) tabandadır: rakamlar 0–7, her rakam 3 bit. Girişteki `010` bu yüzden 8 × 1 + 0 = **8** oldu.

Bu, C'nin en eski tuzaklarından biri. Sayıları hizalamak için başlarına sıfır koymak çok doğal görünür:

```c
int codes[] = {120, 045, 300};
```

`045` 45 değil, 4 × 8 + 5 = **37**. Compiler hiçbir uyarı vermez; `045` tamamen geçerli bir sabit. Sekizlikte olmayan bir rakam yazarsan ise hata alırsın:

```
error: invalid digit '9' in octal constant
    1 | int x = 09;
```

Sekizlik bugün neredeyse tek bir yerde kullanılıyor: Unix'te dosya izinleri. `0755` gibi izinleri Faz 10'da göreceğiz. Onun dışında **sayıların başına sıfır koyma**.

(Bir ilginç ayrıntı: `0` sabiti de teknik olarak sekizliktir. Ama değeri her tabanda aynı olduğu için fark etmez.)

`printf`'te sekizlik için `%o`, başına `0` ekleyerek `%#o`: `printf("%#o", 493)` → `0755`.

---

## 3. İkilik sabitler: 0b

`0b` ile başlayan sayılar **ikilik** (binary) tabandadır: `0b11110000` = 240. Bitlerle çalışırken en okunaklı yol bu.

İkilik sabitler uzun süre standart C'nin parçası değildi; clang ve GCC ek bir özellik olarak destekliyordu. **C23** ile standarda girdi. `-std=c17 -pedantic` ile derlersen clang bunu söyler:

```
warning: binary integer literals are a C23 extension [-Wc23-extensions]
```

C23 bir kolaylık daha getirdi: uzun sayıların rakamlarını **tek tırnakla** ayırabilirsin:

```c
int million = 1'000'000;
int mask = 0b1111'0000;
```

Tırnaklar sayının değerini değiştirmez; sadece okumayı kolaylaştırır. clang'de `-std=c23` ile çalışır.

C23 `printf`'e ikilik için `%b` biçimini de ekledi, ama standart kütüphaneler buna yavaş yetişiyor: macOS'ta `printf("%b", 240)` denedik, ekrana sadece `b` yazdı. Bitleri görmek için şimdilik Ders 3.7'deki `print_bits`'i kullanmaya devam edeceğiz.

---

## 4. Ekler: U, L, LL

Bir sabitin sonuna harf ekleyerek tipini etkileyebilirsin:

| Ek | Anlamı | Örnek |
| --- | --- | --- |
| `U` | işaretsiz | `10U` → `unsigned int` |
| `L` | en az `long` | `10L` → `long` |
| `LL` | en az `long long` | `10LL` → `long long` |
| `UL`, `ULL` | işaretsiz ve en az `long` / `long long` | `10ULL` → `unsigned long long` |

Ekler büyük ya da küçük harfle yazılabilir (`10u`, `10l`), ama küçük `l`'den kaçın: `10l`, `101` ile kolayca karışır. `L`'yi her zaman büyük yaz.

Eklerin asıl işi, bir hesabın **hangi tiple** yapılacağını belirlemek. Ders 3.5'teki örneği hatırla: `big * 2` iki `int`'in çarpımıydı ve taştı. `2` yerine `2LL` yazsaydık:

```c
long long right = big * 2LL;
```

`2LL` bir `long long`; usual arithmetic conversions ile `big` de `long long`'a çevrilir ve çarpma 64 bitle yapılır. `(long long)big * 2` ile aynı sonuç, daha kısa yazımla.

`<stdint.h>`'teki tipler için hazır makrolar var: `INT64_C(5)` sabiti `int64_t` yapar, `UINT32_C(5)` `uint32_t` yapar. Boyutu platforma bağlı `L` yerine bunları kullanmak niyeti daha açık söyler.

---

## 5. Bir sabitin tipi nasıl belirlenir?

Eksiz bir sabitin bile bir tipi var. Kural şu: C, bir listedeki tipleri sırayla dener ve sabitin **sığdığı ilk tipi** seçer. Liste, sabitin tabanına göre farklı:

| Sabit | Denenen tipler (sırayla) |
| --- | --- |
| Ondalık, eksiz | `int`, `long`, `long long` |
| Hex, sekizlik ya da ikilik, eksiz | `int`, `unsigned int`, `long`, `unsigned long`, `long long`, `unsigned long long` |
| `U` ekli | `unsigned int`, `unsigned long`, `unsigned long long` |
| `L` ekli (ondalık) | `long`, `long long` |
| `LL` ekli (ondalık) | `long long` |

İnce ama önemli bir fark var: **eksiz bir ondalık sabit asla işaretsiz olmaz**. Hex sabitler ise `int`'e sığmadıklarında önce `unsigned int`'i dener.

Bunu görmek için bir sabitin tipinin adını yazdıran küçük bir makro kullanalım. Makronun içindeki `_Generic`, bir ifadenin tipine göre seçim yapan bir C11 özelliği. Nasıl çalıştığını bilmen gerekmiyor; sadece "bu ifadenin tipi ne?" sorusuna cevap veren bir araç olarak kullanacağız:

```c
#include <stdio.h>

#define TYPE_NAME(x) _Generic((x), \
    int: "int", unsigned int: "unsigned int", \
    long: "long", unsigned long: "unsigned long", \
    long long: "long long", unsigned long long: "unsigned long long")

int main(void) {
    printf("%s\n", TYPE_NAME(2147483647));
    printf("%s\n", TYPE_NAME(2147483648));
    printf("%s\n", TYPE_NAME(0x7FFFFFFF));
    printf("%s\n", TYPE_NAME(0x80000000));
    printf("%s\n", TYPE_NAME(0xFFFFFFFF));
    printf("%s\n", TYPE_NAME(0x100000000));
    printf("%s\n", TYPE_NAME(5000000000U));
    printf("%s\n", TYPE_NAME('A'));
    return 0;
}
```

Bilgisayarımızda (macOS, `long` 8 byte):

| Sabit | Tip | Neden? |
| --- | --- | --- |
| `2147483647` | `int` | `INT_MAX`, `int`'e sığar |
| `2147483648` | `long` | `int`'e sığmaz; ondalık listede sıradaki `long` |
| `0x7FFFFFFF` | `int` | Aynı değer, `int`'e sığar |
| `0x80000000` | **`unsigned int`** | `int`'e sığmaz; hex listesinde sıradaki `unsigned int` |
| `0xFFFFFFFF` | **`unsigned int`** | Aynı sebep |
| `0x100000000` | `long` | 32 bite sığmaz |
| `5000000000U` | `unsigned long` | `unsigned int`'e sığmaz |
| `'A'` | `int` | Karakter sabitleri `int`'tir (Ders 3.5) |

`2147483648` ile `0x80000000` **aynı sayı**, ama tipleri farklı. Ders 3.6'dan hemen bir tuzak çıkıyor:

```c
printf("%d %d\n", -1 < 2147483648, -1 < 0x80000000);
```

```
1 0
```

`2147483648` bir `long`; `-1 < 2147483648` iki işaretli sayının karşılaştırması ve doğru. `0x80000000` bir `unsigned int`; −1 `unsigned int`'e çevrilir ve 4.294.967.295 olur. Aynı sayı, iki yazım, iki farklı sonuç; ve `-Wall -Wextra` ikisi için de sessiz.

### Platforma göre değişir

Listedeki tipler sabit, ama hangisine sığacağı tiplerin boyutuna bağlı. Ders 3.2'deki veri modelleri burada da karşımıza çıkıyor. clang ile üç platform için ölçtük:

| Sabit | macOS / Linux | Windows | Arduino |
| --- | --- | --- | --- |
| `30000` | `int` | `int` | `int` |
| `40000` | `int` | `int` | **`long`** |
| `0xFFFF` | `int` | `int` | **`unsigned int`** |
| `1000000` | `int` | `int` | `long` |
| `2147483648` | `long` | **`long long`** | `long long` |

- **Arduino'da `int` 2 byte**: 40.000 ona sığmaz ve ondalık olduğu için `long` olur. `0xFFFF` ise hex olduğu için önce `unsigned int`'i dener ve 2 byte'lık `unsigned int`'e sığar. Arduino'da `0xFFFF > -1` **yanlıştır**, `40000 > -1` doğrudur.
- **Windows'ta `long` 4 byte**: 2.147.483.648 ona sığmaz ve `long long` olur.

Ders 3.1'deki 4. alıştırmada "`1000000` Arduino'da `long` olur, ayrıntısı Ders 3.10'da" demiştik. Ayrıntısı bu tablo: ondalık bir sabit `int`'e sığmazsa C onu sessizce büyütür. O alıştırmada vücut kitle indeksinin payını kurtaran da buydu.

Bir sabit listedeki **hiçbir** tipe sığmıyorsa (örneğin `9223372036854775808`, 2⁶³) program yanlış olur. clang bir uyarı verip onu işaretsiz sayar:

```
warning: integer literal is too large to be represented in a signed integer type, interpreting as unsigned [-Wimplicitly-unsigned-literal]
```

---

## 6. Negatif sabit yoktur

Bir sürpriz daha: C'de **negatif sabit diye bir şey yok**. `-5` yazdığında bu iki parçadır: `5` sabiti ve önündeki eksi işlemi. Önce sabitin tipi belirlenir, sonra eksi uygulanır.

Çoğu zaman bunun hiçbir önemi yok. Ama `INT_MIN`'i yazmaya çalışınca önemli hale gelir:

```c
printf("%zu\n", sizeof(-2147483648));
```

```
8
```

−2.147.483.648 bir `int`'e tam sığar, ama ifadenin boyutu 8 byte! Çünkü önce `2147483648` sabitinin tipi belirleniyor: `int`'e sığmaz (`INT_MAX`'tan bir fazla), bu yüzden `long` oluyor. Eksi işareti de `long` bir sayıya uygulanıyor. Sonuç: değeri `INT_MIN` olan ama tipi `long` olan bir ifade.

`<limits.h>` bu yüzden `INT_MIN`'i şöyle tanımlar (macOS'taki başlık dosyasından):

```c
#define INT_MAX         2147483647      /* max value for an int */
#define INT_MIN         (-2147483647-1) /* min value for an int */
```

`2147483647` bir `int`; negatifi de bir `int`; bir çıkarınca −2.147.483.648 olur ve tip `int` olarak kalır. Ders 3.3'teki asimetri, en temel başlık dosyasının içine kadar uzanıyor.

---

## Alıştırmalar

**1** – Bu sayıları hex'e çevir (önce ikiliğe çevirip 4'erli gruplamak işini kolaylaştırır): 10, 100, 1.000, 65.536.

**2** – Bu hex sabitlerin ondalık değeri ne? `0x2A`, `0x100`, `0xBEEF`, `0x7F`.

**3** – Ders 3.9'daki `write_be32` fonksiyonunu düşün. 4.278.190.335 sayısının byte'larını big endian düzende yazdırır. Hangi dört byte'ı yazdırır? Sayıyı hex'e çevirince cevap neden apaçık oluyor?

**4** – Tipleri neler? (macOS ya da Linux'ta) `100`, `100U`, `3000000000`, `0xC0000000`, `0x7F`, `-1`.

**5** – Bir arkadaşın bir sensörden gelen 16 bitlik değerin çok yüksek olup olmadığını şöyle kontrol ediyor:

```c
int value = read_sensor();
if (value > 60000) {
    printf("Uyarı: değer çok yüksek\n");
}
```

`read_sensor` 0–65.535 arası bir değeri `unsigned int` olarak döndürüyor. Bu kod bilgisayarında doğru çalışıyor. Arduino'da da doğru çalışır mı? (İpucu: Arduino'da `int` 2 byte. `read_sensor` 65.535 döndürünce `value`'ya ne konur? `60000` sabitinin Arduino'daki tipi ne?)

<details>
<summary>Cevaplar</summary>

**1** –

- 10 = `1010` = **`0xA`**
- 100 = `0110 0100` = **`0x64`**
- 1.000 = `0011 1110 1000` = **`0x3E8`**
- 65.536 = 2¹⁶ = `1 0000 0000 0000 0000` = **`0x10000`**

**2** – `0x2A` = 2 × 16 + 10 = **42**. `0x100` = 16² = **256**. `0xBEEF` = 11 × 4096 + 14 × 256 + 14 × 16 + 15 = **48.879**. `0x7F` = **127**, `INT8_MAX`.

**3** – 4.278.190.335 = **`0xFF0000FF`**. Byte'lar: `FF 00 00 FF`, yani **255 0 0 255**. Kontrol: 255 × 16.777.216 + 0 + 0 + 255 = 4.278.190.335. Ondalık sayıya bakarak bunu görmek imkansız; hex'te her byte iki rakam olarak orada duruyor.

**4** – `100`: `int`. `100U`: `unsigned int`. `3000000000`: `long` (ondalık, `int`'e sığmaz, asla `unsigned int` olmaz). `0xC0000000`: **`unsigned int`** (hex, `int`'e sığmaz, `unsigned int`'e sığar). `0x7F`: `int`. `-1`: `int`; `1` sabitinin tipi `int`, eksi de `int` olarak kalıyor.

**5** – **Hayır.** Arduino'da 65.535, 2 byte'lık `int`'e sığmaz; `value`'ya konunca (Ders 3.7, Kural 3) **−1** olur. 60.001 ile 65.535 arasındaki bütün değerler de negatif sayılara dönüşür. `60000` ise Arduino'da `int`'e sığmadığı için bir `long`. Karşılaştırmada `value` `long`'a çevrilir ve değeri korunur: −1 > 60.000 **yanlış**. Uyarı hiçbir zaman çıkmaz.

clang ile Arduino için derlediğimizde fonksiyon karşılaştırmayı hiç yapmadan 0 döndürdü ve compiler bunu bir uyarıyla söyledi:

```
warning: result of comparison of constant 60000 with expression of type 'int' is always false [-Wtautological-constant-out-of-range-compare]
```

2 byte'lık bir `int`, 32.767'den büyük olamaz. Asıl sorun `value`'nun tipi: 16 bitlik işaretsiz bir değer için `int` değil **`uint16_t`** kullanılmalı (Ders 3.4). O zaman her platformda `value` 65.535 olur ve karşılaştırma doğru çalışır; Arduino için derlediğimizde de öyle oldu.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §6.4.4.1: tamsayı sabitleri ve tiplerini belirleyen tablo; §6.4.4.4: karakter sabitleri. C23 (ISO/IEC 9899:2024): ikilik sabitler ve rakam ayırıcı.
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.3: sabitler.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 3: tamsayı sabitleri.

**Sıradaki ders:** Sabit noktalı aritmetik. Ders 2.13'teki "100 ile çarp" hilesini düzenli bir sayı biçimine dönüştürüyoruz.
