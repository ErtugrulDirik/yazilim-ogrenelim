---
title: "3.5 Tamsayı yükseltme (integer promotion)"
description: "İki uint8_t'nin toplamı neden int çıkar? Integer promotion kuralı, farklı tipler bir araya gelince sonucun tipini belirleyen usual arithmetic conversions ve bunların assembly'deki karşılığı: movzx ve movsx."
---

Ders 3.4'te 0–255 arası değerler için `uint8_t` kullanmayı öğrendik. Şimdi iki tanesini toplayalım:

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint8_t a = 200;
    uint8_t b = 100;

    printf("a + b = %d\n", a + b);

    uint8_t c = a + b;
    printf("c = %d\n", c);

    printf("sizeof(a) = %zu, sizeof(a + b) = %zu\n", sizeof(a), sizeof(a + b));
    return 0;
}
```

```
a + b = 300
c = 44
sizeof(a) = 1, sizeof(a + b) = 4
```

Üç satır, üç sürpriz:

- `a + b` **300** çıktı. Ama 300 bir `uint8_t`'ye sığmaz! Faz 0'da "8 bitte 200 + 100 = 44" demiştik.
- Aynı toplamı `c`'ye koyunca **44** oldu.
- `a` 1 byte, ama `a + b` **4 byte**.

Demek ki `a + b` bir `uint8_t` değil. Bu dersin konusu: C, bir hesap yapmadan önce sayıları **hangi tipe** çevirir ve sonucun tipi nasıl belirlenir?

---

## 1. Integer promotion: int'ten küçük tiplerle hesap yapılmaz

C'nin kuralı şu: **`int`'ten küçük bir tip bir hesapta kullanıldığında, hesaptan önce `int`'e çevrilir.** Buna **integer promotion** (tamsayı yükseltme) denir.

"`int`'ten küçük" tipler: `char`, `signed char`, `unsigned char`, `short`, `unsigned short` ve onların `<stdint.h>`'teki takma adları: `int8_t`, `uint8_t`, `int16_t`, `uint16_t`.

Yani yukarıdaki program aslında şunu yaptı:

1. `a`'yı `int`'e çevir: 200. `b`'yi `int`'e çevir: 100.
2. İki `int`'i topla: 300. Sonucun tipi `int`; 300 rahatça sığar.
3. `printf` ile yazdırırken sonuç zaten `int`: **300**.
4. `uint8_t c = a + b;` satırında ise 300 bir `uint8_t`'ye **konmak** zorunda. Sığmayan bitler atılır: 300 − 256 = **44**.

Taşma toplamada değil, **atamada** oldu. Ve atama, toplamadan farklı olarak tanımlı bir davranış: işaretsiz bir tipe sığmayan değer, Ders 3.3'teki sayaç gibi başa döner. (Atamanın ve dönüşümlerin bütün kurallarını Ders 3.7'de göreceğiz.)

Kural sadece toplama için değil, **her** aritmetik işlem için geçerli. Hatta tek başına bir `+` bile yükseltmeye yeter:

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    char letter = 'A';
    short s = 1;
    printf("%zu %zu\n", sizeof(letter), sizeof(letter + 1));
    printf("%zu %zu\n", sizeof(s), sizeof(+s));
    printf("%zu\n", sizeof('A'));

    uint8_t x = 10;
    uint8_t y = 20;
    printf("x - y = %d\n", x - y);
    uint8_t z = x - y;
    printf("z = %d\n", z);
    return 0;
}
```

```
1 4
2 4
4
x - y = -10
z = 246
```

- `letter + 1` ve `+s`: ikisi de `int`.
- `sizeof('A')` **4**! C'de tek tırnak içinde yazılmış bir karakter `char` değil, doğrudan `int`'tir. (C++'ta bu kural farklı; Faz 13'te göreceğiz.)
- İki işaretsiz sayıyı çıkardık ve sonuç **negatif** çıktı: −10. Çünkü çıkarma `uint8_t` ile değil, iki `int` ile yapıldı. Sonucu `uint8_t`'ye koyunca −10 + 256 = **246** oldu.

**Neden böyle bir kural var?** Ders 3.2'de `int`'in "işlemcinin en rahat çalıştığı doğal boyut" olarak seçildiğini söylemiştik. İşlemcinin hesap yaptığı kutular (**register**'lar) bugün 32 ya da 64 bittir; 8 bitlik bir toplama komutu çoğu işlemcide ya yoktur ya da daha yavaştır. C de "küçük tipleri hesaptan önce `int`'e çevir" diyerek işlemcinin doğal boyutunda çalışmayı kural haline getirmiş. Ders 3.2'deki "`short`'u aritmetik için kullanmak çoğu zaman bir şey kazandırmaz" önerisinin sebebi buydu.

**Küçük bir ayrıntı.** Kural aslında şöyle: küçük tipin bütün değerleri `int`'e sığıyorsa `int`'e, sığmıyorsa `unsigned int`'e çevrilir. Bilgisayarında her küçük tip `int`'e sığar. Ama `int`'in 2 byte olduğu Arduino'da `uint16_t`'nin en büyük değeri 65.535, `int`'e sığmaz; orada `uint16_t` **`unsigned int`**'e yükseltilir. Aynı kod, farklı platformda farklı tiple hesaplanır.

---

## 2. Farklı tipler buluşunca: usual arithmetic conversions

Integer promotion'dan sonra iki tarafın tipi hâlâ farklı olabilir: `int` + `long long`, `int` + `unsigned int` gibi. İşlemci sadece **aynı** tipteki iki sayıyı toplayabilir, bu yüzden C birini diğerinin tipine çevirir. Hangisinin çevrileceğini belirleyen kurallara **usual arithmetic conversions** (alışılmış aritmetik dönüşümler) denir.

Kuralları anlatmadan önce bir kavram: her tamsayı tipinin bir **rütbesi** (rank) vardır ve rütbe boyutla birlikte artar:

> `char` < `short` < `int` < `long` < `long long`

Bir tipin `unsigned` hali, kendisiyle aynı rütbededir. Kurallar sırayla uygulanır; ilk uyan kural kazanır:

1. **Önce iki taraf da integer promotion'dan geçer.** Artık her iki taraf da en az `int`.
2. **Tipler aynıysa** iş bitti.
3. **İkisi de işaretli ya da ikisi de işaretsizse**, rütbesi küçük olan büyüğe çevrilir. `int` + `long long` → `long long`.
4. **İşaretsiz olanın rütbesi büyük ya da eşitse**, işaretli olan işaretsize çevrilir. `int` + `unsigned int` → **`unsigned int`**.
5. **İşaretli olan, işaretsizin bütün değerlerini tutabiliyorsa**, işaretsiz olan işaretliye çevrilir. `unsigned int` + `long long` → `long long`.
6. **Hiçbiri değilse**, ikisi de işaretli tipin işaretsiz haline çevrilir.

(Bir taraf küsuratlı bir sayıysa bunlardan önce başka bir kural gelir; onu Ders 3.12'de göreceğiz.)

Örneklerle, clang ile ölçerek:

| İfade | macOS / Linux | Windows | Arduino |
| --- | --- | --- | --- |
| `short` + `char` | `int` | `int` | `int` |
| `int` + `long long` | `long long` | `long long` | `long long` |
| `int` + `unsigned int` | `unsigned int` | `unsigned int` | `unsigned int` |
| `unsigned int` + `long long` | `long long` | `long long` | `long long` |
| `unsigned int` + `long` | `long` | **`unsigned long`** | `long` |
| `unsigned short` + `int` | `int` | `int` | **`unsigned int`** |
| `long long` + `unsigned long long` | `unsigned long long` | `unsigned long long` | `unsigned long long` |

Kalın satırlara bak. `unsigned int` + `long`: Linux'ta `long` 8 byte ve `unsigned int`'in bütün değerlerini tutabildiği için kural 5 uyar ve sonuç `long` olur. Windows'ta ikisi de 4 byte; `long`, `unsigned int`'in büyük değerlerini tutamaz, kural 6 uyar ve sonuç **`unsigned long`** olur. Arduino satırı ise Bölüm 1'deki "küçük ayrıntı". Ders 3.2'deki veri modelleri, hesapların **sonucunun tipini** de değiştiriyor.

### Kural 4'ün tuzağı

Kural 4, bu dersteki en tehlikeli kural: işaretli bir sayı, işaretsiz bir sayıyla buluştuğunda **işaretsize** çevrilir.

```c
#include <stdio.h>

int main(void) {
    unsigned int u = 10;
    int i = -20;
    printf("%u\n", u + i);
    return 0;
}
```

```
4294967286
```

10 + (−20) = −10 olmalıydı. Ama −20 `unsigned int`'e çevrildi; Ders 3.3'teki gibi bitleri aynı kaldı ve işaretsiz okundu: 2³² − 20. Toplamın sonucu da 2³² − 10 = 4.294.967.286. Hiçbir uyarı yok, sanitizer da sessiz: işaretsiz aritmetik tanımlı bir davranış.

Bu tuzağın en sinsi hali karşılaştırmalarda ortaya çıkar: C'de `-1 < 1u` **yanlıştır**. Ders 3.6'nın konusu bu.

### Sonucun tipi, değişkenin tipine bakmaz

Bir hesabın tipine sadece **işlemin iki tarafı** karar verir. Sonucun konacağı değişkenin tipinin hiçbir etkisi yoktur:

```c
#include <stdio.h>

int main(void) {
    int big = 2000000000;
    long long wrong = big * 2;
    long long right = (long long)big * 2;
    printf("%lld\n%lld\n", wrong, right);
    return 0;
}
```

`-fsanitize=undefined` ile:

```
runtime error: signed integer overflow: 2000000000 * 2 cannot be represented in type 'int'
-294967296
4000000000
```

`wrong`, 8 byte'lık bir `long long`; 4 milyar oraya rahatça sığar. Ama `big * 2` iki `int`'in çarpımı, yani bir `int` hesabı. Taşma, sonuç `wrong`'a konmadan **önce** oldu.

`right` satırında `(long long)big` yazdık. Parantez içinde bir tip adı, "bu değeri bu tipe çevir" demektir; buna **cast** denir (Ders 3.7'de ayrıntılı). Artık çarpmanın bir tarafı `long long` olduğu için kural 3 uyar, 2 de `long long`'a çevrilir ve hesap 64 bitle yapılır.

Ders 3.1'deki Arduino sorununun asıl sebebi de buydu: `weight * 10000`, sonuç nereye konursa konsun **iki `int` ile** hesaplanıyordu.

### Bir tuzak daha: uint16_t × uint16_t

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint16_t a = 65535;
    uint16_t b = 65535;
    uint32_t product = a * b;
    printf("%u\n", product);
    return 0;
}
```

```
runtime error: signed integer overflow: 65535 * 65535 cannot be represented in type 'int'
4294836225
```

Kodda tek bir işaretli değişken yok! Ama `a` ve `b` önce `int`'e yükseltilir ve çarpma iki **işaretli** `int` ile yapılır. 65.535 × 65.535 = 4.294.836.225, `INT_MAX`'ı aşar: **undefined behavior**. Sonuç doğru görünse de sanitizer haklı. Düzeltmesi: çarpmadan önce bir tarafı `uint32_t`'ye çevirmek, `(uint32_t)a * b`. O zaman iki taraf da `unsigned int` olur ve taşma olmaz.

İşin ironisi: bu kod Arduino'da **tanımlı** çalışır, çünkü orada `uint16_t`, `unsigned int`'e yükseltilir.

---

## 3. Assembly'de yükseltme: movzx ve movsx

Compiler'ın küçük tipleri gerçekten `int`'e çevirdiğini görmek için ürettiği makine koduna bakalım. Bunun için **Compiler Explorer** adlı siteyi kullanacağız: [godbolt.org](https://godbolt.org). Sol tarafa C kodu yazarsın, sağ tarafta compiler'ın ürettiği **assembly** belirir. Assembly, işlemcinin anladığı komutların insanların okuyabileceği hali; Faz 7'de ayrıntılı göreceğiz. Şimdilik birkaç komutu okumak yeterli.

Sitede dili **C** seç, sağ taraftaki compiler'ı **x86-64 clang**, seçenekleri **`-O2`** yap ve şu kodu yaz:

```c
#include <stdint.h>

int sum_u8(uint8_t values[]) {
    return values[0] + values[1];
}

int sum_i8(int8_t values[]) {
    return values[0] + values[1];
}
```

Çıkan assembly (x86-64, Intel yazımı):

```asm
sum_u8:
        movzx   ecx, byte ptr [rdi]
        movzx   eax, byte ptr [rdi + 1]
        add     eax, ecx
        ret

sum_i8:
        movsx   ecx, byte ptr [rdi]
        movsx   eax, byte ptr [rdi + 1]
        add     eax, ecx
        ret
```

Satır satır, `sum_u8`:

- `rdi` → array'in bellekte başladığı yer. `[rdi]` array'in 0. elemanı, `[rdi + 1]` 1. elemanı.
- `byte ptr` → "oradan **1 byte** oku".
- `movzx ecx, ...` → okunan byte'ı 32 bitlik `ecx` register'ına koy, kalan 24 biti **0** ile doldur. **movzx**: move with **z**ero e**x**tend, sıfırla genişleterek taşı.
- `add eax, ecx` → **32 bitlik** toplama. 8 bitlik toplama yok!
- `ret` → fonksiyondan dön; sonuç `eax`'te.

`sum_i8` tek bir harfle farklı: `movsx`, move with **s**ign e**x**tend, **işaretle** genişleterek taşı. Fark neden gerekli? `11111111` byte'ını düşün:

| | Byte | 32 bite genişletilmiş hali | Değer |
| --- | --- | --- | --- |
| `uint8_t` olarak (`movzx`) | `11111111` | `00000000 00000000 00000000 11111111` | 255 |
| `int8_t` olarak (`movsx`) | `11111111` | `11111111 11111111 11111111 11111111` | −1 |

İşaretsiz bir sayıyı genişletirken sol taraf 0 ile dolar ve değer korunur. İşaretli bir sayıda ise sol taraf **en soldaki bitin kopyasıyla** doldurulmalıdır. Ders 3.3'teki ikiler tümleyeninde 8 bitlik −1 `11111111`, 32 bitlik −1 de `11111111 ... 11111111`'dir. Sol tarafı 0 ile doldursaydık −1, 255 olurdu.

Integer promotion'ın makinedeki karşılığı tam olarak bu iki komut. `uint8_t` ile `int8_t` arasındaki tek fark, hangisinin kullanılacağı.

**Apple Silicon kullanıyorsan** bilgisayarın x86-64 değil **ARM** işlemcili. Compiler Explorer'da **armv8-a clang** seçersen aynı fikri farklı isimlerle görürsün:

```asm
sum_u8:
        ldrb    w8, [x0]
        ldrb    w9, [x0, #1]
        add     w0, w9, w8
        ret

sum_i8:
        ldrsb   w8, [x0]
        ldrsb   w9, [x0, #1]
        add     w0, w9, w8
        ret
```

`ldrb` (load register byte) sıfırla, `ldrsb` (load register **signed** byte) işaretle genişletir. Toplama yine 32 bitlik `w` register'larında.

Compiler Explorer yerine kendi bilgisayarında da bakabilirsin:

```sh
clang -std=c17 -O2 -S -masm=intel --target=x86_64-linux-gnu sum.c -o -
```

`-S` "makine kodu yerine assembly üret", `-o -` "dosyaya değil ekrana yaz" demek. `--target` kısmını silersen kendi işlemcinin assembly'sini görürsün; ARM'da `-masm=intel`'i de silmen gerekir.

---

## Alıştırmalar

**1** – Her ifade için sonucun tipini ve değerini bul. (`uint8_t u = 255;`, `int8_t s = -1;`, `short h = 30000;` olsun.)

- a) `u + 1`
- b) `s + u`
- c) `h + h`
- d) `u * u`
- e) `'a' + 1`

**2** – Çalıştırmadan, ne yazdıracağını tahmin et:

```c
uint8_t u = 255;
u = u + 1;
printf("%d\n", u);

short h = 30000;
short sum = h + h;
printf("%d\n", sum);
```

**3** – Ders 3.1'deki vücut kitle indeksi satırı Arduino'da overflow oluyordu:

```c
int bmi = weight * 10000 / (height * height);
```

`weight` ve `height`'ın tipini değiştirmeden, Bölüm 2'deki cast ile bu satırı Arduino'da da doğru çalışacak hale getir. Hangi çarpmalara dokunman gerekti?

**4** – Bölüm 3'teki iki fonksiyonu `uint16_t` ve `int16_t` ile yeniden yaz ve Compiler Explorer'da assembly'ye bak. `byte ptr` yerine ne yazıyor?

**5** – Aşağıdaki fonksiyon, bir `uint8_t` array'indeki sayıların ortalamasını hesaplıyor. Bir hata var mı? 200 tane 255 değerli eleman için ne olur?

```c
uint8_t average(uint8_t values[], int count) {
    uint8_t total = 0;
    for (int i = 0; i < count; i++) {
        total = total + values[i];
    }
    return total / count;
}
```

<details>
<summary>Cevaplar</summary>

**1** –

- a) `int`, **256**. `u` önce `int`'e yükseltilir; 256 `int`'e rahatça sığar.
- b) `int`, **254**. `s` −1, `u` 255 olarak `int`'e çevrilir: −1 + 255.
- c) `int`, **60.000**. `short`'a sığmazdı, ama hesap `int` ile yapılıyor.
- d) `int`, **65.025**. 255 × 255.
- e) `int`, **98**. `'a'` zaten bir `int`: 97.

**2** –

```
0
-5536
```

`u + 1` = 256 bir `int`; `u`'ya konunca 256 − 256 = 0 olur. `h + h` = 60.000 bir `int`; `short`'a sığmadığı için 60.000 − 65.536 = −5.536 olur. İşaretsiz bir tipe sığmayan değerin başa dönmesi standartta tanımlıdır; işaretli bir tipe sığmayan değerin ne olacağını ise standart platforma bırakır (Ders 3.7). Bugünkü bilgisayarların hepsi bitleri kırpar ve −5.536 verir.

**3** –

```c
int bmi = (long)weight * 10000 / ((long)height * height);
```

İki çarpmaya da dokunmak gerekti: `weight * 10000` (700.000) ve `height * height` (182 cm için 33.124). Arduino'da `long` 4 byte, 2 milyara kadar tutar. Bölümün sonucu (yaklaşık 22) `int`'e sığdığı için atama sorunsuz. `(long)` yerine `(int32_t)` yazmak niyetini daha açık söyler: "bu hesap 32 bitle yapılsın".

**4** – `word ptr` yazar: 2 byte (bir **word**, Intel'in eski 16 bitlik işlemcilerinden kalma bir isim). Komutlar yine `movzx` ve `movsx`; toplama yine 32 bitlik `add`.

**5** – Evet. Hata `total`'ın tipinde. `total + values[i]` bir `int` hesabı ve doğru; ama sonuç her adımda `uint8_t` olan `total`'a konuyor ve 255'i geçtiği anda başa dönüyor. 200 × 255 = 51.000 olmalıydı; `total` her seferinde 256'nın kalanını tutar: 51.000 − 199 × 256 = **56**. Ortalama 56 / 200 = **0** çıkar; doğrusu 255. Düzeltme: `total`'ı yeterince büyük bir tip yapmak, örneğin `uint32_t total = 0;`. Kural: küçük tipler **saklamak** için, toplamlar ve ara sonuçlar ise geniş tiplerde.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §6.3.1.1: tamsayı rütbesi ve integer promotion; §6.3.1.8: usual arithmetic conversions.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.2.6: bir sayının bit sayısını genişletmek (zero extension ve sign extension).
- Robert Seacord, *Effective C* (2. baskı), Bölüm 3: integer promotion ve dönüşüm kuralları.
- [Compiler Explorer](https://godbolt.org): C kodunun assembly karşılığını anında görmek için.

**Sıradaki ders:** İşaretli–işaretsiz karşılaştırma tuzağı. `-1 < 0u` neden yanlış?
