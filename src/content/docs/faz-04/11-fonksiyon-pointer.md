---
title: "4.11 Fonksiyon pointer'ı"
description: "Bir fonksiyonun adresini bir değişkende tutmak: int (*op)(int, int) tanımı ve okunuşu, typedef ile sadeleştirmek, count_if ve transform gibi callback alan fonksiyonlar, komut satırından çalışan ve işlem tablosuyla yönetilen bir hesap makinesi, kabuğun * karakterini genişletmesi, qsort karşılaştırıcıları ve a - b karşılaştırıcısının taşma hatası."
---

Ders 4.4'te `main`'in adresini yazdırdık ve "fonksiyonlar da bellekte duruyor; makine komutları olarak" dedik. Bir fonksiyonun adresi varsa, onu bir değişkende tutabilir, bir fonksiyona argüman olarak verebilir, bir array'e koyabiliriz. Ve en önemlisi: **o adresteki fonksiyonu çağırabiliriz**.

Bu, bir fonksiyona "ne yapacağını" bir parametre olarak vermek demek. Ders 4.9'daki `void *` bir fonksiyonu **tipten** bağımsız yaptı; fonksiyon pointer'ı onu **davranıştan** bağımsız yapacak.

---

## 1. Tanım ve çağrı

```c
#include <stdio.h>

int add(int a, int b) {
    return a + b;
}

int multiply(int a, int b) {
    return a * b;
}

int main(void) {
    int (*op)(int, int) = add;
    printf("add = %p, op = %p\n", (void *)add, (void *)op);
    printf("op(2, 3) = %d\n", op(2, 3));
    op = multiply;
    printf("op(2, 3) = %d\n", op(2, 3));
    printf("(*op)(2, 3) = %d\n", (*op)(2, 3));
    printf("sizeof op = %zu\n", sizeof op);
    return 0;
}
```

```
add = 0x100154460, op = 0x100154460
op(2, 3) = 5
op(2, 3) = 6
(*op)(2, 3) = 6
sizeof op = 8
```

`int (*op)(int, int)`'i Ders 4.8'deki gibi içeriden dışarı oku: "`op` bir pointer (`*op`), **iki `int` alıp `int` döndüren bir fonksiyona**." Fonksiyonun tipi, parametrelerinin ve dönüş tipinin tamamı. `add`'in tipi `int (int, int)`; bir array'in ilk elemanının adresine dönüştüğü gibi (Ders 4.6), bir fonksiyonun adı da **kendi adresine** dönüşüyor. Bu yüzden `= &add` yazmaya gerek yok (yazsan da aynı).

Aynı `op(2, 3)` satırı önce toplama, sonra çarpma yaptı. Hangi fonksiyonun çağrılacağı artık derleme sırasında değil, **çalışırken**, `op`'un içindeki adrese göre belirleniyor.

Çağırırken `op(2, 3)` ile `(*op)(2, 3)` aynı. İkincisi "pointer'ın gösterdiği fonksiyonu çağır" diyor ve eski C kodlarında sık görülür; ama `*op` da yine bir adrese dönüştüğü için sonuç değişmiyor. Bu seride kısasını yazacağız.

### Parantezler şart

`(*op)` parantezleri olmazsa anlam tamamen değişiyor:

```c
int *wrong(int, int) = add;
```

```
error: illegal initializer (only variables can be initialized)
```

`int *wrong(int, int)`, "iki `int` alıp **`int *` döndüren** bir fonksiyon" bildirimi; bir değişken değil. `*`, `int`'e yapıştı. Parantez, `*`'ı isme bağlıyor.

### Tipler uymalı

```c
double half(double x) { return x / 2; }
int (*op)(int, int) = half;
```

```
error: incompatible function pointer types initializing 'int (*)(int, int)' with an expression of type 'double (double)' [-Wincompatible-function-pointer-types]
```

Compiler, `op(1, 2)` çağrısında iki `int`'i nereye koyacağını ve sonucu nereden alacağını `op`'un tipine göre ayarlıyor; `half` ise bir `double` bekleyip bir `double` döndürüyor. Tipi uymayan bir fonksiyonu çağırmak undefined behavior, ve bu sefer compiler bunu hata olarak yakalıyor.

### typedef ile okunabilirlik

`int (*)(int, int)` yazmak çabuk zorlaşıyor; özellikle bir fonksiyon pointer'ı **parametre** ya da **dönüş tipi** olduğunda. Ders 3.21'deki `typedef` bunu çözüyor:

```c
typedef int (*BinaryOp)(int, int);

BinaryOp op = add;
```

`BinaryOp`, "iki `int` alıp `int` döndüren fonksiyonun pointer'ı" tipinin adı. Bu seride fonksiyon pointer'larını hep böyle bir isimle kullanacağız.

### `void *` ile fonksiyon pointer'ı

Ders 4.9'da `void *`'ın **nesne** pointer'ları için olduğunu söylemiştik. C standardı, bir fonksiyon pointer'ının bir `void *`'a çevrilebileceğini **garanti etmiyor**: bazı makinelerde kod ve veri farklı bellek alanlarında, farklı boyutta adreslerle duruyor. Yukarıdaki `(void *)add` cast'i bu makinede ve POSIX sistemlerinde (macOS, Linux) çalışıyor, çünkü POSIX bunu ayrıca garanti ediyor; yazdırmak için yeterli. Ama fonksiyon pointer'larını saklamak için `void *` değil, doğru fonksiyon pointer tipini kullan.

---

## 2. Callback: davranışı parametre olarak vermek

Ders 4.2'de bir array'de bir değeri sayan, en büyüğü bulan fonksiyonlar yazdık. "Kaç tane çift sayı var?", "kaç tane negatif var?", "kaç tane 100'den büyük var?" için her seferinde yeni bir fonksiyon mu yazacağız? Döngü hep aynı; değişen tek şey **koşul**. Koşulu bir fonksiyon olarak verelim:

```c
#include <stdbool.h>

int count_if(const int *a, int n, bool (*predicate)(int)) {
    int count = 0;
    for (int i = 0; i < n; i++) {
        if (predicate(a[i])) {
            count++;
        }
    }
    return count;
}

void transform(int *a, int n, int (*fn)(int)) {
    for (int i = 0; i < n; i++) {
        a[i] = fn(a[i]);
    }
}

bool is_even(int x) { return x % 2 == 0; }
bool is_negative(int x) { return x < 0; }
int square(int x) { return x * x; }
int negate(int x) { return -x; }
```

```c
int values[6] = {3, -4, 7, 10, -1, 0};
printf("cift: %d, negatif: %d\n",
       count_if(values, 6, is_even), count_if(values, 6, is_negative));
transform(values, 6, square);
transform(values, 6, negate);
```

```
cift: 3, negatif: 2
9 16 49 100 1 0
negatif: 5
```

`count_if`'e verilen `is_even`, `count_if`'in içinden **geri çağrılıyor**; bu yüzden böyle fonksiyonlara **callback** denir. `count_if` bir kez yazıldı, bütün koşullar için çalışıyor. (Son satırda `0`, `-0 == 0` olduğu için negatif sayılmadı.)

Ders 3.8'den hatırla: `square`, `x * x` büyük bir sayıda taşabilir. Callback'in içindeki kuralların sorumluluğu callback'i yazanda; `transform` onları bilmiyor.

---

## 3. İşlem tablosuyla bir hesap makinesi

Fonksiyon pointer'larını bir array'e koyunca bir **tablo** elde ediyoruz: "şu sembol için şu fonksiyonu çağır". Komut satırından üç argüman (Ders 4.10) alan bir hesap makinesi:

```
$ ./calc 12 + 30
42
```

Her işlem, Ders 4.7'deki kalıpla yazılmış: sonucu bir çıkış parametresine yazıyor, dönüş değeri "hesaplanabildi mi?". Toplama, çıkarma ve çarpma için Ders 3.8'deki taşma kontrolünü, bölme için sıfıra bölmeyi ve Ders 3.8'deki `LONG_MIN / -1` tuzağını kontrol ediyoruz:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <limits.h>

typedef bool (*Operation)(long a, long b, long *result);

bool op_add(long a, long b, long *result) {
    return !__builtin_add_overflow(a, b, result);
}

bool op_sub(long a, long b, long *result) {
    return !__builtin_sub_overflow(a, b, result);
}

bool op_mul(long a, long b, long *result) {
    return !__builtin_mul_overflow(a, b, result);
}

bool op_div(long a, long b, long *result) {
    if (b == 0 || (a == LONG_MIN && b == -1)) {
        return false;
    }
    *result = a / b;
    return true;
}

bool op_mod(long a, long b, long *result) {
    if (b == 0 || (a == LONG_MIN && b == -1)) {
        return false;
    }
    *result = a % b;
    return true;
}
```

Şimdi tablo. Her satırda bir sembol ve bir fonksiyon pointer'ı:

```c
struct Entry {
    const char *symbol;
    Operation fn;
};

const struct Entry table[] = {
    {"+", op_add},
    {"-", op_sub},
    {"x", op_mul},
    {"/", op_div},
    {"%", op_mod},
};

const int table_size = sizeof table / sizeof table[0];

Operation find_operation(const char *symbol) {
    for (int i = 0; i < table_size; i++) {
        if (strcmp(table[i].symbol, symbol) == 0) {
            return table[i].fn;
        }
    }
    return NULL;
}
```

`strcmp(a, b)`, `<string.h>`'teki bir fonksiyon: iki yazı aynıysa 0 döndürüyor (Ders 4.16'da kendimiz yazacağız). `find_operation` bulamazsa `NULL` döndürüyor; fonksiyon pointer'ları da `NULL` olabilir.

`main` sadece argümanları çeviriyor, tabloya soruyor ve bulduğu fonksiyonu çağırıyor:

```c
bool parse(const char *text, long *out) {
    char *end;
    errno = 0;
    *out = strtol(text, &end, 10);
    return end != text && *end == '\0' && errno != ERANGE;
}

int main(int argc, char **argv) {
    if (argc != 4) {
        printf("kullanim: %s sayi islem sayi\n", argv[0]);
        return 1;
    }
    long a, b;
    if (!parse(argv[1], &a) || !parse(argv[3], &b)) {
        printf("gecersiz sayi\n");
        return 1;
    }
    Operation op = find_operation(argv[2]);
    if (op == NULL) {
        printf("bilinmeyen islem: %s\n", argv[2]);
        return 1;
    }
    long result;
    if (!op(a, b, &result)) {
        printf("hesaplanamadi\n");
        return 1;
    }
    printf("%ld\n", result);
    return 0;
}
```

```
$ ./calc 12 + 30
42
$ ./calc 12 x 5
60
$ ./calc 7 / 0
hesaplanamadi
$ ./calc 17 % 5
2
$ ./calc 9223372036854775807 + 1
hesaplanamadi
$ ./calc 2 '^' 3
bilinmeyen islem: ^
```

Yeni bir işlem eklemek için `main`'e dokunmak gerekmiyor: bir fonksiyon yaz, tabloya bir satır ekle. Ders 2'deki gibi bir `if`/`else if` zinciriyle yazsaydık, her yeni işlem `main`'i büyütürdü. Bu "tabloyla yönlendirme" (dispatch table) fikri, ileride yazacağımız yorumlayıcılarda ve bir işletim sisteminin sistem çağrılarını yönetmesinde tam olarak aynı biçimde karşımıza çıkacak.

### Neden `*` değil de `x`?

Çarpma için `*` yerine `x` kullandık. `*` ile denesek?

```
$ ./calc 12 * 5
kullanim: ./calc sayi islem sayi
```

Program dört argüman beklerken daha fazlasını aldı. Neden? Ders 4.10'daki `args` programıyla bakalım:

```
$ ./args 12 * 5
argc = 7
argv[0] = "./args"
argv[1] = "12"
argv[2] = "args"
argv[3] = "args.c"
argv[4] = "calc"
argv[5] = "calc.c"
argv[6] = "5"
```

`*`, programa hiç ulaşmadı. **Kabuk**, `*`'ı "bu klasördeki bütün dosya adları" diye **genişletti** ve programa onları verdi. Programın bunu engellemesinin yolu yok; olan, program başlamadan önce oluyor. Kabuğa `*`'ı olduğu gibi geçirmesini söylemek için tırnak gerekiyor: `./calc 12 '*' 5`. Bizim tablomuzda `*` olmadığı için bu da `bilinmeyen islem: *` verir; `x`'i seçmemizin sebebi bu.

---

## 4. qsort

Standart kütüphanenin en bilinen fonksiyon pointer kullanıcısı, `<stdlib.h>`'teki `qsort`. Her tipte array'i sıralıyor:

```c
void qsort(void *base, size_t count, size_t size,
           int (*compare)(const void *, const void *));
```

İlk üç parametre Ders 4.9'daki `reverse_any`'nin aynısı: nerede, kaç eleman, her biri kaç byte. Ama sıralamak için iki elemandan hangisinin önce geleceğini bilmek gerekiyor; `qsort` bunu bilmiyor, çünkü elemanların ne olduğunu bilmiyor. Bu yüzden bir **karşılaştırıcı** istiyor: iki elemanın adresini alıp

- birincisi önce gelecekse **negatif**,
- eşitlerse **0**,
- ikincisi önce gelecekse **pozitif**

döndüren bir fonksiyon.

### int'ler

```c
int compare_ints(const void *a, const void *b) {
    int x = *(const int *)a;
    int y = *(const int *)b;
    if (x < y) {
        return -1;
    }
    if (x > y) {
        return 1;
    }
    return 0;
}

int compare_ints_desc(const void *a, const void *b) {
    return compare_ints(b, a);
}
```

```c
int a[7] = {42, -7, 15, 0, 15, 100, -3};
qsort(a, 7, sizeof a[0], compare_ints);
qsort(a, 7, sizeof a[0], compare_ints_desc);
```

```
-7 -3 0 15 15 42 100
100 42 15 15 0 -3 -7
```

Karşılaştırıcının parametreleri `const void *`: `qsort` her tiple çalışmak için elemanların adresini `void *` olarak veriyor (Ders 4.9), ve karşılaştırıcının onları değiştirmemesini istiyor (Ders 4.8). İçeride doğru tipe çevirmek bizim işimiz. Ters sıralama için yeni bir mantık gerekmiyor: argümanların yerini değiştirmek yeterli.

### `a - b` tuzağı

İnternette sık görülen kısa bir karşılaştırıcı:

```c
int compare_ints_bad(const void *a, const void *b) {
    return *(const int *)a - *(const int *)b;
}
```

`x - y`, `x < y` iken negatif, eşitken 0, büyükken pozitif. Çoğu zaman çalışıyor. Ama:

```c
int b[3] = {INT_MIN, 1, INT_MAX};
qsort(b, 3, sizeof b[0], compare_ints_bad);
```

```
1 2147483647 -2147483648
```

Sıralama yanlış: `INT_MIN` sona gitti. `INT_MIN - 1` bir `int`'e sığmıyor (Ders 3.8); bu makinede sarıp **pozitif** büyük bir sayı oldu, ve `qsort` "`INT_MIN`, `1`'den büyük" sandı. `-fsanitize=undefined` ile:

```
runtime error: signed integer overflow: -2147483648 - 1 cannot be represented in type 'int'
```

`compare_ints` ise hiç çıkarma yapmadığı için doğru: `-2147483648 1 2147483647`. Kısa bir doğru yazılış da var: `return (x > y) - (x < y);`. İki karşılaştırma da 0 ya da 1 veriyor (Ders 3.21), farkları −1, 0 ya da 1.

### Yazılar

Ders 4.10'daki pointer array'ini sıralayalım:

```c
int compare_strings(const void *a, const void *b) {
    const char *x = *(const char *const *)a;
    const char *y = *(const char *const *)b;
    return strcmp(x, y);
}

const char *words[5] = {"elma", "Zeytin", "armut", "incir", "Ayva"};
qsort(words, 5, sizeof words[0], compare_strings);
```

```
Ayva Zeytin armut elma incir
```

Dikkat edilecek iki şey:

**Karşılaştırıcıya yazılar değil, elemanların adresleri geliyor.** Elemanlar `const char *`; adresleri `const char **` (Ders 4.10). Bu yüzden önce `const char *const *`'a çevirip **bir kez** dereference ediyoruz. (Ortadaki `const`: `qsort` elemanı değiştirmememizi istiyor, eleman da bir pointer.) Bunu atlayıp `strcmp((const char *)a, (const char *)b)` yazmak çok yaygın bir hata: derleniyor, ama pointer'ların **byte'larını** yazı sanıp karşılaştırıyor. Bu makinede sonuç `incir Ayva elma Zeytin armut`: hiçbir sıraya uymuyor.

**Büyük harfler önce geldi.** `strcmp` karakterleri sayısal değerlerine göre karşılaştırıyor; Faz 0'daki ASCII tablosunda bütün büyük harfler (65–90) küçüklerden (97–122) önce. "Sözlük sırası" istiyorsan karşılaştırıcı daha akıllı olmalı (5. alıştırma).

### Struct'lar ve birden fazla anahtar

Puana göre büyükten küçüğe, puanlar eşitse isme göre:

```c
struct Student {
    const char *name;
    int score;
};

int by_score_then_name(const void *a, const void *b) {
    const struct Student *x = a;
    const struct Student *y = b;
    if (x->score != y->score) {
        return x->score > y->score ? -1 : 1;
    }
    return strcmp(x->name, y->name);
}

struct Student s[4] = {{"Ece", 85}, {"Can", 92}, {"Ali", 85}, {"Deniz", 70}};
qsort(s, 4, sizeof s[0], by_score_then_name);
```

```
Can:92 Ali:85 Ece:85 Deniz:70
```

`x->score`, `(*x).score`'un kısa yazılışı: "`x`'in gösterdiği struct'ın `score` alanı". Ders 4.25'te ayrıntısıyla göreceğiz.

Eşit puanlı `Ali` ve `Ece`'nin sırasını ikinci anahtar belirledi. İkinci anahtar olmasaydı? `qsort`'un **kararlı** (stable) olduğu garanti edilmiyor: eşit elemanların başlangıçtaki sırasını korumayabilir. Sıra önemliyse, eşitliği kendin bozmalısın.

### Kaç karşılaştırma?

Karşılaştırıcıyı her çağrıldığında bir sayaç artıracak şekilde yazıp rastgele sayılarla (`<stdlib.h>`'teki `rand()`) dolu array'leri sıralayalım:

```
n =    1000  karsilastirma =     10200  n*log2(n) =      9966
n =   10000  karsilastirma =    135423  n*log2(n) =    132877
n =  100000  karsilastirma =   1702583  n*log2(n) =   1660964
n = 1000000  karsilastirma =  20912210  n*log2(n) =  19931569
```

Karşılaştırma sayısı, $n \log_2 n$'e çok yakın büyüyor: eleman sayısı 10 katına çıkınca karşılaştırma 13 kat civarında artıyor. Her karşılaştırma bir fonksiyon pointer'ı üzerinden bir çağrı; `qsort` her tiple çalışmanın bedelini burada ödüyor, çünkü compiler çağrılacak fonksiyonu bilmediği için onu `qsort`'un içine yerleştiremiyor. (Sıralama algoritmalarını ve bu sayının neden $n \log n$ olduğunu Faz 9'da göreceğiz.)

---

## Alıştırmalar

**1** – Şu tanımları sağdan sola, içeriden dışarı oku:

```c
int (*f)(void);
int *g(void);
void (*h[4])(int);
int (*(*k)(int))(int);
```

Sonuncusu için önce bir `typedef` yazıp tanımı sadeleştir.

**2** – `int fold(const int *a, int n, int start, int (*combine)(int, int))` yaz: `start`'tan başlayıp her elemanı `combine` ile birleştirsin. `add` ile toplamı, `multiply` ile çarpımı, `max` ile en büyüğü hesapla. Boş array için ne döner?

**3** – Hesap makinesine `^` (üs alma) işlemini ekle. Ders 3.8'deki gibi taşmayı kontrol etmeli; negatif üs için `false` dönmeli. `main`'de hangi satırları değiştirmen gerekti?

**4** – `bsearch`, sıralı bir array'de ikili arama yapan standart bir fonksiyon:

```c
void *bsearch(const void *key, const void *base, size_t count, size_t size,
              int (*compare)(const void *, const void *));
```

Bölüm 4'teki sıralanmış `words` array'inde `"elma"`'yı `bsearch` ile ara. Karşılaştırıcının ilk argümanı (`key`) neyi göstermeli: bir yazıyı mı, bir `const char *`'ı mı?

**5** – `"Zeytin"`'in `"armut"`'tan sonra gelmesi için, büyük-küçük harf farkını yok sayan bir karşılaştırıcı yaz. (İpucu: ASCII tablosunda `'A'` ile `'a'` arasında sabit bir fark var. Ders 4.19'da bunu `tolower` ile yapacağız.)

<details>
<summary>Cevaplar</summary>

**1** –

- `int (*f)(void)` → `f` bir pointer, parametre almayan ve `int` döndüren bir fonksiyona.
- `int *g(void)` → `g` bir **fonksiyon**, parametre almıyor ve `int *` döndürüyor.
- `void (*h[4])(int)` → `h` 4 elemanlı bir array; her elemanı bir pointer, `int` alıp hiçbir şey döndürmeyen bir fonksiyona. (Bölüm 3'teki tablonun struct'sız hali.)
- `int (*(*k)(int))(int)` → `k` bir pointer, `int` alıp **bir fonksiyon pointer'ı döndüren** bir fonksiyona; döndürülen pointer, `int` alıp `int` döndüren bir fonksiyonu gösteriyor.

```c
typedef int (*IntFn)(int);
IntFn (*k)(int);
```

`typedef`'le "`k`, `int` alıp `IntFn` döndüren bir fonksiyonun pointer'ı" diye okunuyor.

**2** –

```c
int fold(const int *a, int n, int start, int (*combine)(int, int)) {
    int result = start;
    for (int i = 0; i < n; i++) {
        result = combine(result, a[i]);
    }
    return result;
}
```

Toplam için `fold(a, n, 0, add)`, çarpım için `fold(a, n, 1, multiply)`, en büyük için `fold(a, n, INT_MIN, max)`. Boş array için `start` döner: toplamın 0, çarpımın 1 olması matematikteki "boş toplam" ve "boş çarpım" tanımlarıyla aynı. `start`, işlemin **etkisiz elemanı** olmalı.

**3** –

```c
bool op_pow(long base, long exp, long *result) {
    if (exp < 0) {
        return false;
    }
    long r = 1;
    for (long i = 0; i < exp; i++) {
        if (__builtin_mul_overflow(r, base, &r)) {
            return false;
        }
    }
    *result = r;
    return true;
}
```

Tabloya `{"^", op_pow},` satırını eklemek yeterli; `main`'de hiçbir satır değişmedi. (Bu döngü `exp` kez çarpıyor; Ders 2.9'daki hızlı üs alma ile $\log_2 \text{exp}$ adımda yapılabilir. Ama taşma kontrolü varken `exp` en fazla 63 olabilir, yani fark küçük. `base` 0, 1 ya da −1 iken büyük bir `exp` uzun sürer; bunlar için ayrı bir kısa yol eklenebilir.) `^` kabukta özel bir karakter olmadığı için zsh'ta tırnağa gerek yok, ama tırnak koymak zarar vermez.

**4** –

```c
const char *key = "elma";
const char **found = bsearch(&key, words, 5, sizeof words[0], compare_strings);
if (found != NULL) {
    printf("%td. sirada\n", found - words);
}
```

`3. sirada` yazar. `bsearch`, `key`'i karşılaştırıcıya ilk argüman olarak, array elemanlarıyla **aynı biçimde** veriyor. Karşılaştırıcı her iki argümanı da `const char *`'ın adresi sanıyor; bu yüzden `"elma"`'nın kendisini değil, onu gösteren `key`'in adresini veriyoruz. Dönen değer de bir elemanın adresi, yani bir `const char **`.

**5** –

```c
int lower(int c) {
    if (c >= 'A' && c <= 'Z') {
        return c + ('a' - 'A');
    }
    return c;
}

int compare_strings_nocase(const void *a, const void *b) {
    const unsigned char *x = *(const unsigned char *const *)a;
    const unsigned char *y = *(const unsigned char *const *)b;
    while (*x != '\0' && lower(*x) == lower(*y)) {
        x++;
        y++;
    }
    return lower(*x) - lower(*y);
}
```

Sonuç: `armut Ayva elma incir Zeytin`. `x` biterse `*x == '\0'` olduğu için döngü durur; `y` önce biterse `lower(*y) == 0`, `lower(*x)`'ten farklı olduğu için yine durur. Karakterleri `unsigned char` olarak okumanın sebebini Ders 4.16'da göreceğiz. Burada çıkarma güvenli: iki değer de 0–255 arasında, farkları bir `int`'e her zaman sığar. Bu karşılaştırıcı Türkçe harfleri (`ç`, `ş`, `İ`) bilmiyor; onlar UTF-8'de birden fazla byte'la yazılıyor (Ders 4.12).

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.11 (fonksiyon pointer'ları; genel bir sıralama fonksiyonu), §5.12 (karmaşık tanımları okumak), §B5 (`qsort`, `bsearch`).
- Peter van der Linden, *Expert C Programming*, Bölüm 3: C tanımlarını çözümlemek.
- C standardı (ISO/IEC 9899:2018), §6.3.2.1¶4: fonksiyon adının adresine dönüşmesi; §6.5.2.2¶9: uyumsuz tipte bir fonksiyon pointer'ı üzerinden çağrının undefined behavior olması; §7.22.5.2: `qsort` ve kararlılığın garanti edilmemesi.
- POSIX.1-2017, `dlsym`: fonksiyon pointer'ının `void *`'a çevrilebilmesi gereksinimi.

**Sıradaki ders:** C stringleri. `'\0'` ile biten yazılar, `char s[]` ile `char *s`'nin farkı ve bir string sabitini değiştirmeye çalışınca neden çöktüğümüz.
