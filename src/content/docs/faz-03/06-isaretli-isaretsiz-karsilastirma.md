---
title: "3.6 İşaretli–işaretsiz karşılaştırma tuzağı"
description: "C'de -1 < 1u neden yanlış? Karşılaştırmalarda usual arithmetic conversions, -Wsign-compare'in neyi yakalayıp neyi kaçırdığı, size_t ile count - 1 ve uzunluk farkı hataları, işaretli ile işaretsiz sayıyı güvenle karşılaştırmak."
---

Ders 3.5'i bir uyarıyla bitirmiştik: C'de `-1 < 1u` **yanlıştır**. Kendin gör:

```c
#include <stdio.h>

int main(void) {
    int i = -1;
    unsigned int u = 1;

    printf("-1 < 1u      : %d\n", -1 < 1u);
    printf("i < u        : %d\n", i < u);
    printf("i == 4294967295u : %d\n", i == 4294967295u);

    int scores[] = {70, 85, 60};
    if (-1 < sizeof(scores)) {
        printf("-1, 12'den küçük\n");
    } else {
        printf("-1, 12'den büyük?!\n");
    }
    return 0;
}
```

```
-1 < 1u      : 0
i < u        : 0
i == 4294967295u : 1
-1, 12'den büyük?!
```

C'de bir karşılaştırma doğruysa 1, yanlışsa 0 verir. Yani:

- −1, 1'den küçük **değil**.
- −1, 4.294.967.295'e **eşit**.
- −1, `sizeof(scores)`'tan, yani 12'den **büyük**.

Matematik bozulmadı. Bu dersin konusu, bu üç satırın neden C'nin kurallarına göre tamamen doğru olduğu ve bu tuzağın gerçek programlarda nasıl ortaya çıktığı.

---

## 1. Karşılaştırma da bir hesaptır

`<`, `>`, `<=`, `>=`, `==` ve `!=` da `+` ve `*` gibi iki taraflı işlemlerdir. İşlemci iki sayıyı ancak **aynı tipteyse** karşılaştırabilir. Bu yüzden Ders 3.5'teki **usual arithmetic conversions** kuralları karşılaştırmalarda da aynen uygulanır.

`i < u` satırında `i` bir `int`, `u` bir `unsigned int`. Aynı rütbedeler ve biri işaretsiz: **kural 4** uyar ve `i`, `unsigned int`'e çevrilir. Ders 3.3'te gördüğümüz gibi bitler aynı kalır, sadece okunuşları değişir:

| | Bitler | `int` olarak | `unsigned int` olarak |
| --- | --- | --- | --- |
| −1 | `11111111 11111111 11111111 11111111` | −1 | 4.294.967.295 |

Karşılaştırma aslında `4294967295 < 1` oldu. Sonuç: yanlış.

`sizeof` satırı da aynı şey. `sizeof`'un sonucu Ders 3.4'teki `size_t` tipindedir ve 64 bitlik bilgisayarında `size_t` 8 byte'lık bir işaretsiz tiptir. −1 de `size_t`'ye çevrilir: 2⁶⁴ − 1 = 18.446.744.073.709.551.615. Bu sayı 12'den büyük.

### Hangi tiplerde olur?

Tuzak sadece işaretsiz taraf **en az `int` kadar büyükse** ortaya çıkar. `int`'ten küçük tipler önce `int`'e yükseltilir (Ders 3.5, integer promotion) ve karşılaştırma iki `int` arasında yapılır. clang ile ölçtük; `n` her satırda `-1` olan bir `int`:

| İfade | İşaretsiz taraf neye dönüşüyor? | Sonuç |
| --- | --- | --- |
| `n < (uint8_t)1` | `int`'e yükseltiliyor | 1 (doğru) |
| `n < (uint16_t)1` | `int`'e yükseltiliyor | 1 (doğru) |
| `n < (uint32_t)1` | `n`, `unsigned int`'e çevriliyor | **0 (yanlış)** |
| `n < (uint64_t)1` | `n`, `uint64_t`'ye çevriliyor | **0 (yanlış)** |
| `(int64_t)-1 < (uint32_t)1` | `uint32_t`, `int64_t`'ye çevriliyor (kural 5) | 1 (doğru) |

Son satır bir çıkış yolu gösteriyor: işaretli taraf, işaretsiz tarafın **bütün değerlerini** tutabilecek kadar büyükse çevrilen işaretsiz taraf olur ve sonuç doğru çıkar. Bunu Bölüm 4'te kullanacağız.

### Aynı satır, iki platform

Ders 3.5'teki tablodan hatırla: `long` ile `unsigned int` buluştuğunda sonucun tipi platforma göre değişiyordu. Karşılaştırmanın **sonucu** da değişir:

```c
int f(void) {
    return -1L < 1u;
}
```

`1L`'deki `L`, sayının `long` olduğunu söyler (Ders 3.10). clang ile iki platform için derleyip assembly'ye baktık:

| Platform | `long` | Kural | `-1L < 1u` |
| --- | --- | --- | --- |
| Linux, macOS (64 bit) | 8 byte | 5: `1u`, `long`'a çevrilir | 1 (doğru) |
| Windows (64 bit) | 4 byte | 6: ikisi de `unsigned long`'a çevrilir | **0 (yanlış)** |

Aynı kod, aynı compiler, farklı cevap.

---

## 2. Compiler neyi yakalar?

Başlangıçtaki programı `-Wall -Wextra` ile derlediğimizde clang şunu söyledi:

```
cmp.c:8:37: warning: comparison of integers of different signs: 'int' and 'unsigned int' [-Wsign-compare]
    8 |     printf("i < u        : %d\n", i < u);
      |                                   ~ ^ ~
cmp.c:9:41: warning: comparison of integers of different signs: 'int' and 'unsigned int' [-Wsign-compare]
    9 |     printf("i == 4294967295u : %d\n", i == 4294967295u);
      |                                       ~ ^  ~~~~~~~~~~~
```

Uyarının adı **`-Wsign-compare`**: "farklı işaretli tamsayıları karşılaştırıyorsun." `-Wextra` bunu açar; sadece `-Wall` ile gelmez. Ders 2.12'deki "her zaman `-Wall -Wextra`" kuralının bir sebebi daha.

Ama sayılara dikkat et: dört tuzaklı karşılaştırmadan sadece **ikisi** için uyarı geldi. `-1 < 1u` ve `-1 < sizeof(scores)` için hiçbir şey yok. clang, işaretli tarafı bir **sabit** olan karşılaştırmalarda bu uyarıyı vermiyor. Yani compiler'ın sessiz olması kodun doğru olduğu anlamına gelmiyor.

Tersi de doğru: her `-Wsign-compare` uyarısı bir hata değildir. Ders 3.4'te `size_t` ile yazdığımız döngüyü `int` ile yazalım:

```c
int scores[] = {70, 85, 60};
for (int i = 0; i < sizeof(scores) / sizeof(scores[0]); i++) {
    printf("%d\n", scores[i]);
}
```

```
warning: comparison of integers of different signs: 'int' and '__size_t' (aka 'unsigned long') [-Wsign-compare]
```

Bu döngü doğru çalışır: `i` hiçbir zaman negatif olmuyor, çevrildiğinde de değeri değişmiyor. Ama uyarıyı görmezden gelmek yerine `i`'yi `size_t` yap. Uyarısız kod yazma alışkanlığın, gerçek uyarıları gürültünün içinde kaybetmeni engeller.

---

## 3. size_t ile çıkarma

İşaretsiz sayılarla en tehlikeli işlem çıkarmadır, çünkü sonuç **sıfırın altına inemez**: Ders 3.3'teki sayaç gibi en büyük değere döner. Bir de `size_t` boyutların ve eleman sayılarının tipi olduğu için bu tuzak en çok array'lerle çalışırken ortaya çıkar.

### count − 1

Bir array'in küçükten büyüğe sıralı olup olmadığına bakan bir fonksiyon. Her elemanı bir sonrakiyle karşılaştırıyor; son elemanın bir sonrakisi olmadığı için döngü `count - 1`'de duruyor:

```c
#include <stdio.h>

int is_sorted(int values[], size_t count) {
    for (size_t i = 0; i < count - 1; i++) {
        if (values[i] > values[i + 1]) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    int scores[] = {60, 70, 85};
    printf("%d\n", is_sorted(scores, 3));
    printf("%d\n", is_sorted(scores, 0));
    return 0;
}
```

Boş bir array sıralı sayılır; ikinci çağrının 1 döndürmesi gerekir. `-fsanitize=address` ile çalıştıralım (Ders 2.12):

```
==8921==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x00016d03a0ac ...
READ of size 4 at 0x00016d03a0ac thread T0
    #0 0x000102dc48cc in is_sorted sorted.c:5
    #1 0x000102dc4aac in main sorted.c:15
...
    [32, 44) 'scores' (line 13) <== Memory access at offset 44 overflows this variable
```

`count` 0 iken `count - 1` −1 değil, 18.446.744.073.709.551.615. Döngü durmuyor ve array'in dışını okuyor. Bu sefer hiçbir uyarı da yok: karşılaştırmanın iki tarafı da `size_t`, işaretler aynı.

Düzeltmesi: çıkarmayı karşılaştırmanın öbür tarafına **toplama** olarak taşı.

```c
for (size_t i = 0; i + 1 < count; i++) {
```

Matematikte `i < count − 1` ile `i + 1 < count` aynı şeydir. Bilgisayarda değil: `i + 1` hiçbir zaman sıfırın altına inmez. `count` 0 iken `0 + 1 < 0` yanlıştır ve döngü hiç çalışmaz.

### Uzunlukların farkı

İki uzunluğu karşılaştırırken çıkarma yapmak çok doğal görünür:

```c
#include <stdio.h>

int main(void) {
    size_t first_len = 3;
    size_t second_len = 5;
    if (first_len - second_len > 0) {
        printf("Birinci daha uzun\n");
    } else {
        printf("İkinci daha uzun\n");
    }
    printf("%zu\n", first_len - second_len);
    return 0;
}
```

```
Birinci daha uzun
18446744073709551614
```

3 − 5, −2 değil 2⁶⁴ − 2. Bu sayı 0'dan büyük olduğu için koşul, uzunluklar eşit olmadığı sürece **her zaman** doğru. Faz 4'te yazacağımız `strlen` de bir yazının uzunluğunu `size_t` olarak döndürür; `strlen(a) - strlen(b) > 0` C programlarında sık görülen bir hatadır.

Düzeltmesi: işaretsiz sayıları çıkarma, doğrudan karşılaştır.

```c
if (first_len > second_len) {
```

Ders 3.4'teki geriye sayan döngü de aynı ailenin üyesi: `i >= 0`, `size_t` için her zaman doğrudur.

---

## 4. Güvenli karşılaştırma

Kurallar şöyle:

**1. Karıştırma.** Bir değişkenin negatif olamayacağını biliyorsan (boyut, eleman sayısı, indeks), onu karşılaştırdığın şeyle aynı tipte tut. Döngü değişkeni `size_t` olan bir sınırla karşılaştırılıyorsa o da `size_t` olsun.

**2. İşaretsiz sayılarla çıkarma yapmadan önce düşün.** `a - b` ifadesinde `b`, `a`'dan büyük olabilir mi? Olabiliyorsa çıkarmayı karşılaştırmanın öbür tarafına toplama olarak taşı ya da doğrudan `a < b` diye karşılaştır.

**3. Karıştırmak zorundaysan negatifliği önce sen kontrol et.** Negatif bir sayı, her işaretsiz sayıdan küçüktür; bunu C'ye bırakma:

```c
int less_than(int a, unsigned int b) {
    if (a < 0) {
        return 1;
    }
    return (unsigned int)a < b;
}
```

`a` negatifse cevap belli. Değilse `a`'nın değeri `unsigned int`'e sorunsuz sığar ve karşılaştırma doğru olur. `(unsigned int)a`, Ders 3.5'te gördüğümüz **cast**: dönüşümü açıkça yazıyoruz. Davranış aynı, ama okuyan kişi (ve compiler) bunun bilerek yapıldığını görüyor. `-Wsign-compare` de susuyor. Cast'leri Ders 3.7'de ayrıntılı göreceğiz.

**4. Ya da ikisini birden tutabilen bir tipe çevir.** Bölüm 1'deki tablonun son satırı: `int64_t`, hem `int`'in hem `uint32_t`'nin bütün değerlerini tutabilir.

```c
int less_than(int a, uint32_t b) {
    return (int64_t)a < (int64_t)b;
}
```

Bu yol 64 bitlik işaretsiz sayılarda işe yaramaz; `uint64_t`'nin bütün değerlerini tutan daha büyük bir standart tip yok. Orada 3. kural kalır.

**5. `-Wall -Wextra` ile derle ve `-Wsign-compare` uyarılarını düzelt.** Bölüm 2'de gördüğümüz gibi her durumu yakalamaz, ama çoğunu yakalar.

(C++ bu sorunu dilin içinde çözmüş: `std::cmp_less(a, b)` işaretleri farklı olsa bile matematikteki gibi karşılaştırır. Faz 13'te göreceğiz.)

---

## Alıştırmalar

**1** – Çalıştırmadan her ifadenin sonucunu (0 ya da 1) bul. (`uint8_t x = 200;`, `int64_t m = -1;`, `uint32_t one = 1;` olsun; `UINT_MAX`, `<limits.h>`'teki en büyük `unsigned int`.)

- a) `-1 > 0u`
- b) `x > -1`
- c) `-5 < 3u`
- d) `m < one`
- e) `-1 == UINT_MAX`

**2** – Aşağıdaki fonksiyon bir array'in ortalamasını hesaplıyor. `values` = {−10, −20, 0} için ne döndürür? Neden?

```c
int average(int values[], size_t count) {
    int total = 0;
    for (size_t i = 0; i < count; i++) {
        total = total + values[i];
    }
    return total / count;
}
```

**3** – İki uzunluğu karşılaştıran `int compare_lengths(size_t a, size_t b)` fonksiyonunu yaz: `a` küçükse −1, eşitse 0, büyükse 1 döndürsün. Çıkarma kullanma.

**4** – Bölüm 4'teki ilk `less_than`'ı `int` ve `size_t` için yaz: `int less_than_size(int a, size_t b)`. Sonra `less_than_size(-1, 0)`, `less_than_size(5, 3)` ve `less_than_size(2, 3000000000)` ile dene.

<details>
<summary>Cevaplar</summary>

**1** –

- a) **1.** −1, `unsigned int`'e çevrilir: 4.294.967.295 > 0.
- b) **1.** `x` bir `uint8_t`; `int`'e yükseltilir: 200 > −1. clang burada "bu karşılaştırma her zaman doğru" diye uyarır (`-Wtautological-constant-out-of-range-compare`), çünkü bir `uint8_t` asla −1'den küçük ya da ona eşit olamaz.
- c) **0.** −5, 4.294.967.291 olur.
- d) **1.** `int64_t`, `uint32_t`'nin bütün değerlerini tutabilir; `one` `int64_t`'ye çevrilir (kural 5).
- e) **1.** −1'in bitleri `unsigned int` olarak okununca tam olarak `UINT_MAX`.

**2** – **1431655755** döndürür. Ortalama −10 olmalıydı. `total` −30, ama `total / count` bir `int` ile bir `size_t` arasında: `total`, `size_t`'ye çevrilir ve 2⁶⁴ − 30 olur. Bölümün sonucu 6.148.914.691.236.517.195. Bu sayı `int`'e sığmaz; `return` sırasında `int`'e çevrilirken kırpılır (kuralını Ders 3.7'de göreceğiz) ve geriye 1.431.655.755 kalır. `-Wall -Wextra` uyarmaz. Düzeltme: bölmeden önce `count`'u işaretli bir tipe çevirmek: `return total / (int)count;`. (`count`'un `int`'e sığacak kadar küçük olduğunu varsayıyoruz.)

**3** –

```c
int compare_lengths(size_t a, size_t b) {
    if (a < b) {
        return -1;
    }
    if (a > b) {
        return 1;
    }
    return 0;
}
```

`return a - b;` yazmak cazip görünür, ama hem işaretsiz çıkarma sıfırın altına inemez hem de `size_t`'den `int`'e dönüşte büyük farklar kırpılır.

**4** –

```c
int less_than_size(int a, size_t b) {
    if (a < 0) {
        return 1;
    }
    return (size_t)a < b;
}
```

Sonuçlar: 1, 0, 1. Negatif olmayan bir `int`'in değeri `size_t`'ye her zaman sığar.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §6.5.8: ilişki operatörleri (karşılaştırmada da usual arithmetic conversions uygulanır); §6.3.1.8: usual arithmetic conversions.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 3 ve 4: işaretli ve işaretsiz tamsayıların karşılaştırılması.
- [Clang uyarı listesi](https://clang.llvm.org/docs/DiagnosticsReference.html#wsign-compare): `-Wsign-compare`.

**Sıradaki ders:** Dönüşümler. Bir değer başka bir tipe konduğunda bitlerine ne olur?
