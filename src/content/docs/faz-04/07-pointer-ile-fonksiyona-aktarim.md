---
title: "4.7 Pointer ile fonksiyona aktarım"
description: "Değer ile aktarımda swap'ın neden çalışmadığı ve pointer ile nasıl çalıştığı, scanf'in ve __builtin_add_overflow'un & ile ne yaptığı, bir fonksiyondan birden fazla sonuç döndürmek (çıkış parametreleri ve struct), NULL ile isteğe bağlı parametreler, aynı yeri gösteren iki pointer (aliasing) ve yerel bir değişkenin adresini döndürmenin tehlikesi."
---

Ders 2.3'ten beri bir kuralla yaşıyoruz: **fonksiyon, kendisine verilen değerin kopyasıyla çalışır.** Bu kural programları öngörülebilir kılıyor: bir fonksiyonu çağırınca değişkenlerin değişmeyeceğini biliyorsun. Ama bazen tam olarak değişmelerini istiyoruz. `scanf`'in işi `value`'nun içine yazmak; Ders 4.2'deki `reverse` iki elemanın yerini değiştiriyordu, ve "bunu Ders 4.7'de bir `swap` fonksiyonuna taşıyacağız" demiştik.

Ders 4.4'te bunun yolunu tarif ettik: değişkenin kendisini değil, **adresini** vermek. Ders 4.5'te adresi tutan değişkeni, pointer'ı öğrendik. Şimdi ikisini birleştiriyoruz.

---

## 1. swap neden çalışmıyor?

İki değişkenin değerlerini değiştiren bir fonksiyon:

```c
#include <stdio.h>

void swap_value(int a, int b) {
    int tmp = a;
    a = b;
    b = tmp;
    printf("içeride a = %d, b = %d, &a = %p\n", a, b, (void *)&a);
}

int main(void) {
    int x = 1;
    int y = 2;
    printf("main &x = %p\n", (void *)&x);
    swap_value(x, y);
    printf("x = %d, y = %d\n", x, y);
    return 0;
}
```

```
main &x = 0x16f1b2158
içeride a = 2, b = 1, &a = 0x16f1b20ec
x = 1, y = 2
```

Fonksiyonun içinde yer değiştirme **oldu**: `a` 2, `b` 1. Ama `main`'deki `x` ve `y` aynı kaldı. Adreslere bak: `a`, `x`'ten farklı bir yerde, `swap_value`'nun kendi frame'inde (Ders 4.4). Çağrı anında `x`'in değeri **kopyalandı** ve `a` adında yeni bir değişkene kondu; yer değiştirme o kopyalarda yapıldı, ve fonksiyon bitince kopyalar yok oldu.

```
main'in frame'i          swap_value'nun frame'i
┌──────────┐             ┌──────────┐
│ x │  1   │ ──kopya──►  │ a │ 1→2  │
│ y │  2   │ ──kopya──►  │ b │ 2→1  │
└──────────┘             └──────────┘
```

Bu davranışa **değer ile aktarım** (pass by value) denir. C'de parametreler **her zaman** değer ile aktarılır; istisnası yok.

---

## 2. Pointer ile swap

İstisna yoksa nasıl yapacağız? Değer ile aktarmaya devam ederek; ama aktardığımız değer bir **adres** olsun.

```c
void swap(int *a, int *b) {
    int tmp = *a;
    *a = *b;
    *b = tmp;
}

int main(void) {
    int x = 1;
    int y = 2;
    swap(&x, &y);
    printf("x = %d, y = %d\n", x, y);
    return 0;
}
```

```
x = 2, y = 1
```

- `swap(&x, &y)`: `x`'in ve `y`'nin **adresleri** veriliyor.
- `int *a`: `a` bir pointer; içinde `x`'in adresinin bir **kopyası** var. Kopya da olsa, aynı yeri gösteriyor.
- `*a = *b`: Ders 4.5'teki gibi, `a`'nın gösterdiği yere, yani `x`'in kendisine yazıyor.

```
main'in frame'i               swap'ın frame'i
┌──────────────┐              ┌───────────────┐
│ x │  1 → 2   │ ◄─────────── │ a │ &x        │
│ y │  2 → 1   │ ◄─────────── │ b │ &y        │
└──────────────┘              │ tmp │ 1       │
                              └───────────────┘
```

Tracing:

| Satır | `*a` (yani `x`) | `*b` (yani `y`) | `tmp` |
| --- | --- | --- | --- |
| Başta | 1 | 2 | |
| `int tmp = *a;` | 1 | 2 | 1 |
| `*a = *b;` | **2** | 2 | 1 |
| `*b = tmp;` | 2 | **1** | 1 |

Bu, C'de "bir fonksiyonun çağıranın değişkenini değiştirmesi"nin **tek** yolu. C++ ve diğer dillerdeki "referans ile aktarım" da arka planda tam olarak bunu yapar; C sadece bunu gizlemiyor.

Ders 4.2'deki `reverse` artık şöyle yazılabilir:

```c
void reverse(int a[], int n) {
    for (int i = 0, j = n - 1; i < j; i++, j--) {
        swap(&a[i], &a[j]);
    }
}
```

`&a[i]`, Ders 4.6'ya göre `a + i`; `swap(a + i, a + j)` yazmak da aynı. `for`'un ilk kısmındaki `int i = 0, j = n - 1` iki değişken tanımlıyor; son kısımdaki virgül de (`i++, j--`) iki işlemi sırayla yapıyor. İki uçtan ilerleyen döngülerde yaygın bir kalıp.

---

## 3. scanf ve arkadaşları

Artık Ders 2.13'ten beri kara kutu olarak kullandığımız çağrıları tam olarak okuyabiliriz:

| Çağrı | Fonksiyon adresle ne yapıyor? |
| --- | --- |
| `scanf("%d", &value)` | Okuduğu sayıyı `value`'nun adresine yazıyor. |
| `__builtin_add_overflow(a, b, &sum)` (Ders 3.8) | Toplamı `sum`'ın adresine yazıyor; dönüş değeri sadece taşma bilgisi. |
| `ckd_add(&r, a, b)` (Ders 3.8) | Aynısı, sonuç başta. |
| `memcpy(bytes, &x, sizeof(x))` (Ders 3.9) | `x`'in adresinden başlayarak byte'ları **okuyor**, `bytes`'a yazıyor. |
| `strtol(text, &end, 10)` (Ders 3.17) | Bitiş yerini `end`'in adresine yazıyor. |

`strtol`'unkini biraz açalım. `end` bir `char *`; `&end` onun adresi, tipi `char **` (Ders 4.5'teki "pointer'ı gösteren pointer"). `strtol`, `end`'in **içine**, yani pointer'ın kendisine, yazının neresinde durduğunu yazıyor. Değiştirilmesi gereken değişken bir pointer olunca, onun da adresini vermek gerekiyor. Ders 4.10'da bu kalıba döneceğiz.

`scanf("%d", value)` diye `&`'i unutsaydın ne olurdu? `scanf`, `value`'nun içindeki **sayıyı** bir adres sanıp oraya yazmaya çalışırdı; Ders 4.5'teki başlatılmamış pointer'ın aynısı. Neyse ki clang bunu `-Wall` ile yakalıyor: `format specifies type 'int *' but the argument has type 'int' [-Wformat]`. clang, `%d`'nin `scanf`'te bir `int` değil bir `int *` beklediğini biliyor.

---

## 4. Birden fazla sonuç döndürmek

Bir fonksiyonun `return` ile tek bir değer döndürebildiğini biliyoruz. Bölüm ile kalanı **birlikte** döndüren bir fonksiyon:

```c
void divmod(int a, int b, int *quotient, int *remainder) {
    *quotient = a / b;
    *remainder = a % b;
}

int q;
int r;
divmod(17, 5, &q, &r);
```

`q` = 3, `r` = 2. Sonuçları alacak değişkenleri çağıran hazırlıyor, fonksiyon adreslerine yazıyor. Bu tür parametrelere **çıkış parametresi** (output parameter) denir.

Daha kullanışlı bir örnek: Ders 4.2'nin 4. alıştırmasında en küçük ve en büyük elemanı bir struct ile döndürmüştük. Çıkış parametreleriyle:

```c
#include <stdbool.h>

bool min_max(const int a[], int n, int *min, int *max) {
    if (n <= 0) {
        return false;
    }
    *min = a[0];
    *max = a[0];
    for (int i = 1; i < n; i++) {
        if (a[i] < *min) {
            *min = a[i];
        }
        if (a[i] > *max) {
            *max = a[i];
        }
    }
    return true;
}
```

```c
int values[5] = {4, -2, 9, 0, 3};
int lo;
int hi;
if (min_max(values, 5, &lo, &hi)) {
    printf("%d %d\n", lo, hi);
}
```

```
-2 9
```

Bu, C kütüphanelerindeki en yaygın kalıp: **dönüş değeri başarıyı ya da hatayı söylüyor, sonuçlar çıkış parametrelerine yazılıyor.** `scanf` de böyle: kaç değer okuduğunu döndürüyor, değerleri adreslere yazıyor. Boş bir array'de `min_max` `false` döndürüyor ve `lo` ile `hi`'ye **dokunmuyor**; çağıran, dönüş değerine bakmadan onları kullanmamalı.

### Struct mı, çıkış parametresi mi?

Ders 3.17'de `parse_long`'un sonucunu bir struct ile döndürmüştük, çünkü henüz pointer'ları bilmiyorduk. İkisini karşılaştıralım:

| | Struct döndürmek | Çıkış parametresi |
| --- | --- | --- |
| Örnek | `struct ParseResult r = parse_long(text, 10);` | `long v; int end; int status = parse_long2(text, 10, &v, &end);` |
| Okunuş | Sonuçlar bir arada, adlarıyla | Sonuçlar ayrı değişkenlerde |
| Yeni tip | Her fonksiyon için bir struct | Gerekmiyor |
| İsteğe bağlı sonuç | Hepsi her zaman hesaplanıyor | `NULL` verilebiliyor (aşağıda) |
| Standart kütüphane | Nadiren (`div`) | Neredeyse her yerde |

İkisi de doğru. Birbirine ait birkaç değer için struct daha okunaklı; dönüş değeri bir hata kodu olacaksa ve bazı sonuçlar isteğe bağlıysa çıkış parametreleri.

### NULL: "bu sonuca ihtiyacım yok"

Ders 4.5'te `strtol`'a `end` yerine `NULL` verilebileceğini söylemiştik. Kendi fonksiyonlarımızda aynısını yapmak için, yazmadan önce pointer'ın `NULL` olmadığına bakmak yeter:

```c
void divmod(int a, int b, int *quotient, int *remainder) {
    if (quotient != NULL) {
        *quotient = a / b;
    }
    if (remainder != NULL) {
        *remainder = a % b;
    }
}

int r;
divmod(17, 5, NULL, &r);
```

Sadece kalan isteniyor. Bir fonksiyonun dokümantasyonu, hangi pointer parametrelerinin `NULL` olabileceğini her zaman söylemeli; `swap(NULL, &y)` Ders 4.5'teki gibi çöker.

---

## 5. Aynı yeri gösteren iki pointer

`swap(&x, &x)` ne yapar? Bir değişkeni kendisiyle değiştirmek; değişmemeli.

```c
swap(&x, &x);
```

`x` aynı kalıyor: `tmp = x; x = x; x = tmp;`. Ama bazen geçici değişken kullanmadan yer değiştirmenin "akıllıca" bir yolu önerilir:

```c
void swap_arith(int *a, int *b) {
    *a = *a + *b;
    *b = *a - *b;
    *a = *a - *b;
}
```

Farklı iki değişkenle doğru çalışıyor (taşma olmadığı sürece; Ders 3.8). Aynı değişkenle:

```c
int x = 2;
swap_arith(&x, &x);
```

```
swap_arith(&x, &x): x = 0
```

`x` **sıfır oldu**. `a` ve `b` aynı yeri gösterdiği için ilk satır `x`'i 4 yapıyor, ikinci satır `*b = *a - *b` yani `x = 4 - 4` = 0, ve üçüncüsü 0 − 0. Fonksiyon, `*a`'ya yazmanın `*b`'yi değiştirmeyeceğini varsayıyordu.

İki pointer'ın aynı belleği göstermesine **aliasing** denir. Ders 4.3'ün 5. alıştırmasındaki `mat_mul(a, a, a)` da aynı sorundu: sonuca yazmak girdiyi bozuyordu. Pointer alan her fonksiyonu yazarken sor: "Bu pointer'lar aynı yeri gösterirse ne olur?" Ya fonksiyon bu durumda da doğru çalışmalı (geçici değişkenli `swap` gibi), ya da dokümantasyonu bunu yasaklamalı. Ders 4.18'de `memcpy` ile `memmove` arasındaki farkın tamamen bu soru olduğunu, ve C'nin `restrict` anahtar kelimesiyle compiler'a "bu pointer'lar aynı yeri göstermeyecek" demeyi göreceğiz.

---

## 6. Yerel bir değişkenin adresini döndürmek

Ters yönde de bir tuzak var. Bir fonksiyon, kendi yerel değişkeninin adresini **döndürürse**:

```c
int *make_value(void) {
    int local = 5;
    return &local;
}
```

clang hemen uyarıyor:

```
warning: address of stack memory associated with local variable 'local' returned [-Wreturn-stack-address]
```

Uyarıya rağmen deneyelim:

```c
int other(void) {
    int junk = 12345;
    return junk * 2;
}

int main(void) {
    int *p = make_value();
    printf("%d\n", *p);
    other();
    printf("%d\n", *p);
    return 0;
}
```

```
5
12345
```

`p`'ye hiç dokunmadık, ama gösterdiği değer **değişti**. `make_value` bitince frame'i ortadan kalktı (Ders 2.7); `local`'ın yeri artık kimsenin değil. `other` çağrılınca frame'i **aynı yere** kuruldu ve `junk` tam `local`'ın eski yerine yazıldı. `p`, artık var olmayan bir değişkeni gösteriyor; böyle pointer'lara **sallanan pointer** (dangling pointer) denir. İlk `printf`'in 5 yazması, hatanın en kötü yanı: program bir süre doğru çalışıyor gibi görünüyor.

ASan bunu yakalayabiliyor, ama özel bir ayarla: `ASAN_OPTIONS=detect_stack_use_after_return=1 ./program`:

```
==3559==ERROR: AddressSanitizer: stack-use-after-return on address 0x000102260060 ...
READ of size 4 at 0x000102260060 thread T0
```

Kural: **bir fonksiyon, kendi yerel değişkenlerinin adresini dışarı veremez.** Adresin işe yarayabilmesi için gösterdiği şeyin fonksiyondan **uzun** yaşaması gerekiyor: çağıranın değişkeni (çıkış parametresi), bir global ya da `static` değişken (Ders 4.4'teki veri bölgesi), ya da Ders 4.22'de göreceğimiz `malloc` ile ayrılmış bellek.

---

## Alıştırmalar

**1** – Üç `int`'in değerlerini sola döndüren `rotate3(int *a, int *b, int *c)` yaz: `b`'deki değer `a`'ya, `c`'deki `b`'ye, `a`'daki `c`'ye geçsin. (1, 2, 3) → (2, 3, 1). Sadece `swap`'ı kullanarak yazabilir misin?

**2** – Ders 4.2'deki `average`'ı, boş array'de NaN döndürmek yerine başarıyı `bool` olarak döndürüp ortalamayı bir çıkış parametresine yazacak şekilde değiştir: `bool average(const int a[], int n, double *result)`.

**3** – Saniye cinsinden bir süreyi saat, dakika ve saniyeye çeviren `void split_time(int total, int *hours, int *minutes, int *seconds)` yaz. Üç çıkış parametresinden her biri `NULL` olabilsin. 3725 saniye kaç saat, kaç dakika, kaç saniye?

**4** – Bu fonksiyon iki sayının büyüğünü küçüğün yerine yazmak istiyor. `clamp_to_max(&x, &x)` için ne olur? Ya `clamp_to_max(&x, &y)` için?

```c
void clamp_to_max(int *small, int *big) {
    if (*small > *big) {
        int tmp = *small;
        *small = *big;
        *big = tmp;
    }
    *small = *big;
}
```

**5** – Bir arkadaşın, Ders 3.16'daki `itoa` için tampon hazırlamaktan sıkılmış ve şunu yazmış:

```c
char *to_text(int value) {
    char buffer[12];
    itoa(value, buffer, 10);
    return buffer;
}
```

Ne yanlış? clang ne der? Bölüm 6'daki seçeneklerle üç farklı düzeltme öner. Her birinin bir dezavantajı ne?

<details>
<summary>Cevaplar</summary>

**1** –

```c
void rotate3(int *a, int *b, int *c) {
    int tmp = *a;
    *a = *b;
    *b = *c;
    *c = tmp;
}
```

Sadece `swap` ile: `swap(a, b); swap(b, c);`. (1, 2, 3) → ilk `swap`'tan sonra (2, 1, 3) → ikinciden sonra (2, 3, 1). Ders 4.2'deki döndürmenin üç elemanlık hali.

**2** –

```c
bool average(const int a[], int n, double *result) {
    if (n <= 0) {
        return false;
    }
    *result = (double)sum(a, n) / n;
    return true;
}
```

Çağıran artık `isnan` yerine dönüş değerine bakıyor: `if (average(a, n, &avg)) { … }`.

**3** –

```c
void split_time(int total, int *hours, int *minutes, int *seconds) {
    if (hours != NULL) {
        *hours = total / 3600;
    }
    if (minutes != NULL) {
        *minutes = total % 3600 / 60;
    }
    if (seconds != NULL) {
        *seconds = total % 60;
    }
}
```

3725 = 1 saat (3600) + 2 dakika (120) + 5 saniye.

**4** – `clamp_to_max(&x, &y)` doğru çalışır: sonunda ikisi de büyük olanın değerini taşır. `clamp_to_max(&x, &x)`'te `*small > *big` hiçbir zaman doğru değil (bir sayı kendisinden büyük olamaz) ve `*small = *big` yani `x = x`; `x` değişmez. Bu fonksiyon aliasing'e karşı güvenli: iki pointer aynı yeri gösterse de sonuç anlamlı. Aliasing her zaman hata yaratmaz; sadece fonksiyonun bu durumu düşünüp düşünmediği önemli.

**5** – `buffer` yerel bir array; Ders 4.1'e göre `return buffer;` onun ilk elemanının adresini döndürüyor ve fonksiyon bitince o bellek artık kimsenin değil. clang: `address of stack memory associated with local variable 'buffer' returned [-Wreturn-stack-address]`. Düzeltmeler:

- **Tamponu çağırana hazırlat** (çıkış parametresi): `void to_text(int value, char out[])`. Bu, Ders 3.16'daki `itoa`'nın kendisi. Dezavantajı: çağıran tamponun boyutunu bilmek zorunda.
- **`static char buffer[12];`**: tampon artık veri bölgesinde (Ders 4.4) ve fonksiyondan uzun yaşıyor. Dezavantajı: her çağrı **aynı** tamponu kullanıyor. `printf("%s %s", to_text(1), to_text(2))` iki kez aynı adresi alır ve iki sayıdan biri kaybolur. Ders 4.20'deki `strtok` bu tasarımın sorunlarını gösterecek.
- **`malloc` ile bellek ayırmak** (Ders 4.22): her çağrıya yeni bir tampon. Dezavantajı: çağıran, işi bitince belleği `free` ile geri vermek zorunda; unutursa bellek sızar.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.2: pointer'lar ve fonksiyon argümanları (`swap`).
- C standardı (ISO/IEC 9899:2018), §6.5.2.2¶4: argümanların değer ile aktarılması; §6.2.4¶2: bir nesnenin ömrü bittikten sonra ona işaret eden pointer'ın değerinin belirsizleşmesi.
- SEI CERT C Coding Standard, DCL30-C: nesneleri doğru ömürle tanımlamak (yerel değişkenin adresini döndürmemek).

**Sıradaki ders:** `const` ve pointer. `const int *`, `int *const` ve `const int *const`: neyin değişmeyeceğini söylemenin üç yolu.
