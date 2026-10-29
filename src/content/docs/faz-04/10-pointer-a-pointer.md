---
title: "4.10 Pointer'a pointer"
description: "Bir pointer'ın adresini tutan pointer: int ** ile iki adımlı erişim, bir fonksiyonun çağıranın pointer'ını değiştirmesi (strtol'un char **end'i), iki boyutlu array ile pointer array'i arasındaki fark ve (int **) cast'inin neden çöktüğü, main'in argc ve argv'si ile komut satırından gelen sayıları toplayan bir program."
---

Ders 4.5'te `&p`'nin tipinin `int **` olduğunu gördük ve "pointer'ı gösteren pointer" deyip geçtik. Ders 4.7'de `strtol(text, &end, 10)`'daki `&end`'in bir `char **` olduğunu söyledik. Bu derste ikisini açıyoruz.

Fikir yeni değil: bir pointer da bir değişken, bellekte bir yeri ve bir adresi var (Ders 4.5). O adresi tutan bir değişken tanımlayabiliriz. Yeni olan, bunun neden bu kadar sık gerektiği.

---

## 1. İki adım

```c
#include <stdio.h>

int main(void) {
    int x = 42;
    int *p = &x;
    int **pp = &p;

    printf("&x  = %p, x   = %d\n", (void *)&x, x);
    printf("&p  = %p, p   = %p\n", (void *)&p, (void *)p);
    printf("&pp = %p, pp  = %p\n", (void *)&pp, (void *)pp);
    printf("*pp = %p, **pp = %d\n", (void *)*pp, **pp);

    **pp = 7;
    printf("x = %d\n", x);

    int y = 99;
    *pp = &y;
    printf("p = %p, *p = %d\n", (void *)p, *p);
    return 0;
}
```

```
&x  = 0x16fa5e178, x   = 42
&p  = 0x16fa5e170, p   = 0x16fa5e178
&pp = 0x16fa5e168, pp  = 0x16fa5e170
*pp = 0x16fa5e178, **pp = 42
x = 7
p = 0x16fa5e164, *p = 99
```

Üç değişken, stack'te 8'er byte arayla (Ders 4.4'teki gibi aşağı doğru):

```
   pp                    p                     x
┌──────────────┐      ┌──────────────┐      ┌──────┐
│ 0x16fa5e170 ─┼────▶ │ 0x16fa5e178 ─┼────▶ │  42  │
└──────────────┘      └──────────────┘      └──────┘
 0x16fa5e168           0x16fa5e170           0x16fa5e178
```

- `pp` → `p`'nin adresi.
- `*pp` → `pp`'nin gösterdiği yer, yani `p`'nin **kendisi**. Tipi `int *`, değeri `x`'in adresi.
- `**pp` → `*pp`'nin gösterdiği yer, yani `x`. Tipi `int`.

Okları bir kez takip etmek bir `*`, iki kez takip etmek iki `*`. `**pp = 7` iki ok takip edip `x`'e yazıyor. `*pp = &y` ise **bir** ok takip edip `p`'ye yazıyor: `p` artık `y`'yi gösteriyor, ve bunu `p`'nin adını hiç kullanmadan yaptık.

Bu son satır dersin asıl fikri: `int **`, bir `int *` değişkenini **uzaktan değiştirebilmenin** yolu.

Sıra `int ***`'e de gidebilir, ama pratikte nadiren iki yıldızdan öteye geçilir. Ders 4.8'deki gibi sağdan sola oku: `int **pp` → "`pp` bir pointer, bir pointer'a, bir `int`'e".

---

## 2. Bir fonksiyonun çağıranın pointer'ını değiştirmesi

Ders 4.7'deki kural: bir fonksiyonun çağıranın bir değişkenini değiştirebilmesi için o değişkenin **adresini** alması gerekiyor. `int` değiştirmek için `int *`. Değiştirilecek değişken bir **pointer** ise? Aynı kural: onun adresi, yani `int **`.

Bir array'de ilk negatif sayıyı bulan, bulduğunu bir **pointer** olarak geri veren ve dönüş değerini "bulundu mu?" için kullanan bir fonksiyon:

```c
#include <stdbool.h>
#include <stddef.h>

bool find_first_negative(int *a, int n, int **out) {
    for (int i = 0; i < n; i++) {
        if (a[i] < 0) {
            *out = &a[i];
            return true;
        }
    }
    *out = NULL;
    return false;
}
```

```c
int values[6] = {4, 8, -15, 16, -23, 42};
int *neg;
if (find_first_negative(values, 6, &neg)) {
    printf("bulundu: %d, indeks %td\n", *neg, neg - values);
    *neg = 0;
}
printf("values[2] = %d\n", values[2]);
```

```
bulundu: -15, indeks 2
values[2] = 0
```

`*out = &a[i]` → "`out`'un gösterdiği pointer'a (`main`'deki `neg`'e) `a[i]`'nin adresini yaz." Sonra `main`, `neg` üzerinden array'deki elemanı değiştirebiliyor.

`int **` yerine `int *` yazsaydık?

```c
void find_bad(int *a, int n, int *out) {
    for (int i = 0; i < n; i++) {
        if (a[i] < 0) {
            out = &a[i];
            return;
        }
    }
}

int *q = NULL;
find_bad(values, 6, q);
printf("q = %p\n", (void *)q);
```

```
warning: parameter 'out' set but not used [-Wunused-but-set-parameter]
q = 0x0
```

Ders 4.7'deki `swap_value`'nun aynısı: `out`, `q`'nun bir **kopyası**. Fonksiyon kopyayı değiştirdi; `q` hâlâ `NULL`. Compiler da durumu fark etti: "`out`'a bir değer yazdın ama hiç kullanmadın."

### strtol'un `char **end`'i

Artık `strtol`'un imzasını tam okuyabiliyoruz:

```c
long strtol(const char *text, char **end, int base);
```

`strtol`, `text`'te okumayı bıraktığı yeri **bir pointer olarak** çağırana vermek istiyor. Çağıranın `char *end` değişkenini değiştirmesi gerekiyor; o yüzden onun adresini, bir `char **`, alıyor. İçeride bir yerde `*end = (char *)current;` gibi bir satır var. (Buradaki cast, Ders 4.8'deki `strchr` ikileminin aynısı: `const char *` bir yazının içini `const` olmayan bir pointer'la veriyor.)

Ders 3.17'de `parse_long`'u `int end` (bir **indeks**) döndüren bir struct ile yazmıştık. Standart kütüphane aynı bilgiyi **pointer** olarak veriyor; ikisi arasında `end_pointer - text == end_index` ilişkisi var (Ders 4.6).

---

## 3. İki boyutlu array ile pointer array'i

`int **`'ın en çok karıştırıldığı yer burası. İki tanım:

```c
char grid[4][10] = {"pazartesi", "sali", "carsamba", "cuma"};
const char *list[4] = {"pazartesi", "sali", "carsamba", "cuma"};
```

İkisinde de `grid[i]` ve `list[i]` bir yazı, `grid[i][j]` ve `list[i][j]` bir karakter. Ama bellekte hiç benzemiyorlar:

```c
printf("sizeof grid = %zu, sizeof list = %zu\n", sizeof grid, sizeof list);
for (int i = 0; i < 4; i++) {
    printf("grid[%d] = %p  list[%d] = %p  %s\n",
           i, (void *)grid[i], i, (void *)list[i], list[i]);
}
printf("&list[0] = %p &list[1] = %p\n", (void *)&list[0], (void *)&list[1]);
```

```
sizeof grid = 40, sizeof list = 32
grid[0] = 0x16f156140  list[0] = 0x100ca8808  pazartesi
grid[1] = 0x16f15614a  list[1] = 0x100ca8812  sali
grid[2] = 0x16f156154  list[2] = 0x100ca8817  carsamba
grid[3] = 0x16f15615e  list[3] = 0x100ca8820  cuma
&list[0] = 0x16f156120 &list[1] = 0x16f156128
```

**`grid`**, Ders 4.3'teki gibi tek bir blok: 4 satır × 10 byte = 40 byte, stack'te. Satırlar tam 10 byte arayla (`0x...140`, `0x...14a`, `0x...154`). Her satır, yazı ne kadar kısa olursa olsun 10 byte yer kaplıyor; `"sali"` için 5 byte kullanılıyor, 5'i boş.

**`list`**, 4 tane **pointer**: 4 × 8 = 32 byte, stack'te (`&list[0]` ile `&list[1]` arası 8). Yazıların kendisi bu 32 byte'ın **içinde değil**; `0x100ca...` adreslerinde, Ders 4.4'teki haritanın en altında, salt okunur sabitler bölgesinde. Orada uç uca duruyorlar: `"pazartesi"` 10 byte (`0x808`'den `0x812`'ye), `"sali"` 5 byte (`0x812`'den `0x817`'ye). Boşluk yok.

```
grid (40 byte, stack)                      list (32 byte, stack)       salt okunur bölge
┌──────────────────────────────┐          ┌──────────┐
│p a z a r t e s i \0          │          │ ─────────┼──▶ "pazartesi\0"
│s a l i \0 · · · · ·          │          │ ─────────┼──▶ "sali\0"
│c a r s a m b a \0 ·          │          │ ─────────┼──▶ "carsamba\0"
│c u m a \0 · · · · ·          │          │ ─────────┼──▶ "cuma\0"
└──────────────────────────────┘          └──────────┘
```

| | `char grid[4][10]` | `const char *list[4]` |
| --- | --- | --- |
| Ne tutuyor? | 40 karakter | 4 adres |
| Yazılar nerede? | array'in içinde | başka bir yerde |
| Satır uzunlukları | hepsi aynı (10) | her biri farklı olabilir |
| Bir yazıyı değiştirmek | `grid[1][0] = 'S'` serbest | salt okunur bölgeye yazmak (Ders 4.12) |
| `grid[i][j]` nasıl hesaplanıyor? | `grid + i*10 + j`, tek adım | önce `list[i]`'yi oku, sonra `+ j`: iki adım |

Son satır önemli. `grid[i][j]` ile `list[i][j]` aynı görünüyor, ama compiler ikisi için tamamen farklı kod üretiyor. `grid` için Ders 4.3'teki adres formülü; `list` için önce bellekten bir pointer okuyup sonra ona `j` ekleme.

### Düzensiz satırlar

Pointer array'inin asıl gücü, satırların **farklı uzunlukta** olabilmesi:

```c
int r0[3] = {1, 2, 3};
int r1[1] = {4};
int r2[5] = {5, 6, 7, 8, 9};
int *rows[3] = {r0, r1, r2};
int lengths[3] = {3, 1, 5};

for (int i = 0; i < 3; i++) {
    for (int j = 0; j < lengths[i]; j++) {
        printf("%d ", rows[i][j]);
    }
    printf("\n");
}
```

```
1 2 3
4
5 6 7 8 9
```

`int m[3][5]` yazsaydık 15 `int` ayırırdık; burada sadece 9 tane var. Bir array'in bir `int *`'a dönüştüğü gibi (Ders 4.6), bir **pointer array'i** de ilk elemanının adresine, yani bir `int **`'a dönüşüyor:

```c
int **rp = rows;
printf("rp[2][4] = %d, *(*(rp + 2) + 4) = %d\n", rp[2][4], *(*(rp + 2) + 4));
```

```
rp[2][4] = 9, *(*(rp + 2) + 4) = 9
```

`*(rp + 2)`, `rows[2]`'yi, yani `r2`'nin adresini okuyor; `+ 4` ve `*` ise `r2[4]`'ü.

### `int **` ile `int [][N]` aynı şey değil

Ders 4.3'te `int m[3][4]`'ü `int (*)[3]` bekleyen bir fonksiyona verince hata almıştık. `int **` bekleyen bir fonksiyona?

```c
int sum_rows(int **rows, int nrows, int ncols);

int m[2][3] = {{1, 2, 3}, {4, 5, 6}};
sum_rows(m, 2, 3);
```

```
error: incompatible pointer types passing 'int[2][3]' to parameter of type 'int **' [-Wincompatible-pointer-types]
```

Hata, ve haklı. Bir an "cast'le susturayım" diye düşünebilirsin: `sum_rows((int **)m, 2, 3)`. Program derleniyor ve çalıştırınca:

```
zsh: segmentation fault  ./d
```

Neden? `sum_rows`, `rows[0]`'ı bir **pointer** diye okuyor. Ama `m`'nin başında pointer yok; `1, 2, 3, ...` sayıları var. İlk 8 byte'ı bir adres olarak okursak:

```c
int **bad = (int **)m;
printf("bad[0] = %p\n", (void *)bad[0]);
```

```
bad[0] = 0x200000001
```

`m[0][0] = 1` ve `m[0][1] = 2`'nin byte'ları (Ders 3.9'daki little-endian sırayla) yan yana, ve `0x200000001` diye bir adres oluşturuyorlar. `rows[0][0]` o "adrese" gitmeye çalışınca program çöküyor.

**`int **`, pointer'larla dolu bir yer bekliyor; iki boyutlu bir array'de pointer yok, sadece sayılar var.** Aradaki tek ortak şey `[i][j]` yazılışı.

---

## 4. `argc` ve `argv`

Şimdiye kadar her programa `int main(void)` yazdık: "`main` hiçbir şey almıyor". Ama `main`'in ikinci bir standart imzası var:

```c
#include <stdio.h>

int main(int argc, char *argv[]) {
    printf("argc = %d\n", argc);
    for (int i = 0; i < argc; i++) {
        printf("argv[%d] = \"%s\"  (%p)\n", i, argv[i], (void *)argv[i]);
    }
    printf("argv[%d] = %p\n", argc, (void *)argv[argc]);
    printf("argv = %p\n", (void *)argv);
    return 0;
}
```

```
$ ./args merhaba "iki kelime" 42
argc = 4
argv[0] = "./args"  (0x16ee16ac0)
argv[1] = "merhaba"  (0x16ee16ac7)
argv[2] = "iki kelime"  (0x16ee16acf)
argv[3] = "42"  (0x16ee16ada)
argv[4] = 0x0
argv = 0x16ee167c8
```

Programı çalıştırırken adının arkasına yazdığın kelimeler **komut satırı argümanları**. `clang -Wall -o args args.c` yazarken clang'e verdiğin `-Wall`, `-o`, `args`, `args.c` tam olarak bunlar; clang'in `main`'i onları böyle alıyor.

- **`argc`** (argument count): kaç argüman var. Programın kendi adı da sayılıyor; bu yüzden 3 değil 4.
- **`argv`** (argument vector): bir **pointer array'i**, Bölüm 3'teki `list` gibi. Her eleman bir yazıyı gösteriyor. `argv[0]` programın adı.
- Kabuk (zsh) argümanları **boşluklardan** ayırıyor; tırnak içindeki `"iki kelime"` tek bir argüman.
- **`argv[argc]` her zaman `NULL`**. Standart bunu garanti ediyor; `argc`'yi hiç kullanmadan, `NULL`'a kadar ilerleyerek de bütün argümanları gezebilirsin.
- Bütün argümanlar **yazı**. `42` bir sayı değil, `'4'`, `'2'`, `'\0'`. Sayı olarak kullanmak için Ders 3.17'deki `strtol` gerekiyor.

Yazıların adreslerine bak: `0x16ee16ac0`, `0x...ac7` (`"./args"` 6 karakter + `'\0'` = 7 byte sonra), `0x...acf`… Uç uca, ve `argv`'nin kendisinin (`0x16ee167c8`) biraz üstünde. İkisi de stack bölgesinde, `main`'in kendi değişkenlerinin de üstünde: işletim sistemi programı başlatırken argümanları stack'in en tepesine yerleştirip `main`'e bunların adresini veriyor. Ders 4.21'de programın bellek düzenini bütünüyle gördüğümüzde bu bölgeye döneceğiz.

### Parametrede `char *argv[]` = `char **argv`

Ders 4.1'e göre bir parametrede `int a[]` ile `int *a` aynı şey. Aynı kural burada: `char *argv[]` ("char pointer'larından oluşan bir array") parametre olarak `char **argv`'nin aynısı. İkisi de yaygın.

### Komut satırından gelen sayıları toplamak

`argv`'yi bir `char **` ile `NULL`'a kadar gezen, her argümanı Ders 3.17'deki kurallarla sayıya çeviren bir program:

```c
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>

int main(int argc, char **argv) {
    if (argc < 2) {
        printf("kullanim: %s sayi...\n", argv[0]);
        return 1;
    }
    long total = 0;
    for (char **arg = argv + 1; *arg != NULL; arg++) {
        char *end;
        errno = 0;
        long value = strtol(*arg, &end, 10);
        if (end == *arg || *end != '\0' || errno == ERANGE) {
            printf("gecersiz sayi: %s\n", *arg);
            return 1;
        }
        total += value;
    }
    printf("%ld\n", total);
    return 0;
}
```

```
$ ./sum 10 20 -5
25
$ ./sum
kullanim: ./sum sayi...
$ ./sum 3 4x
gecersiz sayi: 4x
$ ./sum 99999999999999999999
gecersiz sayi: 99999999999999999999
```

İki seviyeli pointer'ların hepsi tek programda:

- `arg` bir `char **`: `argv` array'inde bir **eleman**ı gösteriyor. `arg++` bir sonraki elemana (8 byte ileri; Ders 4.6).
- `*arg` bir `char *`: o elemanın gösterdiği **yazı**.
- `&end` bir `char **`: `strtol`, `end`'in içine yazının neresinde durduğunu yazıyor.
- `*end` bir `char`: durduğu yerdeki karakter. `'\0'` değilse, sayının arkasında başka bir şey var (`4x`'teki `x`).

`main`'in dönüş değeri de burada ilk kez anlam kazanıyor: `return 1`, programı çalıştıran kabuğa "bir sorun oldu" diyor. zsh'ta son programın dönüş değerini `echo $?` ile görebilirsin: geçerli girişte 0, diğerlerinde 1. Ders 2.11'deki `make`, bir komut 0'dan farklı dönerse durur; bütün Unix araçları bu sözleşmeyle konuşur.

---

## Alıştırmalar

**1** – Bölüm 1'deki programda `pp`, `*pp`, `**pp`, `&pp` ve `&*pp` ifadelerinin her birinin tipini ve değerini yaz. (`&*pp`'ye dikkat: `&` ve `*` birbirini götürür mü?)

**2** – Bir `int *`'ı `NULL`'a çeken ve aynı zamanda gösterdiği yeri sıfırlayan `void clear_and_null(int **pp)` yaz. `*pp` zaten `NULL`'sa ne yapmalı? Neden `int *` parametre yeterli olmuyor?

**3** – `argv`'deki argümanları **ters sırada**, `argc`'yi hiç kullanmadan yazdıran bir program yaz. (İpucu: önce `NULL`'a kadar ilerle.)

**4** – Bir yazı array'inde en uzun yazıyı bulan `const char *longest(const char **words, int n)` yaz. Bölüm 3'teki `list`'i ve bir `char grid[4][10]`'u bu fonksiyona vermeyi dene. Hangisi derlenir? Diğerini nasıl uyumlu hale getirirsin?

**5** – Ders 4.7'deki `min_max`'ı, en küçük ve en büyük elemanın **değerlerini** değil **adreslerini** döndürecek şekilde yaz: `bool min_max_ptr(int *a, int n, int **min, int **max)`. Döndürülen pointer'larla `*min` ile `*max`'ı yer değiştirip array'i yazdır.

<details>
<summary>Cevaplar</summary>

**1** –

| İfade | Tip | Değer |
| --- | --- | --- |
| `pp` | `int **` | `0x16fa5e170` (`p`'nin adresi) |
| `*pp` | `int *` | `0x16fa5e178` (`p`'nin değeri, `x`'in adresi) |
| `**pp` | `int` | `42` |
| `&pp` | `int ***` | `0x16fa5e168` |
| `&*pp` | `int **` | `0x16fa5e170`, `pp`'nin kendisi |

`*pp` "`pp`'nin gösterdiği yer" (bir lvalue; Ders 4.4), `&` da onun adresi; ikisi birbirini götürüyor. Standart bunu açıkça söylüyor: `&*E`, `E` ile aynı.

**2** –

```c
void clear_and_null(int **pp) {
    if (*pp != NULL) {
        **pp = 0;
        *pp = NULL;
    }
}
```

`*pp` `NULL`'sa `**pp` bir NULL dereference olurdu (Ders 4.5); kontrol şart. `int *p` parametresi olsaydı, `*p = 0` çalışırdı ama `p = NULL` sadece kopyayı değiştirirdi (Bölüm 2'deki `find_bad`). Ders 4.22'de `free`'den sonra pointer'ı `NULL`'a çekmek için tam olarak bu kalıbı kullanacağız.

**3** –

```c
int main(int argc, char **argv) {
    (void)argc;
    char **last = argv;
    while (*last != NULL) {
        last++;
    }
    while (last != argv) {
        last--;
        printf("%s\n", *last);
    }
    return 0;
}
```

`last` sonunda `argv[argc]`'yi, yani `NULL`'u gösteriyor; Ders 4.6'daki "bir sonrasını gösteren pointer" gibi. Geri giderken önce azaltıp sonra okuyoruz. `(void)argc;`, "bu parametreyi bilerek kullanmıyorum" demenin yolu; `-Wunused-parameter` uyarısını susturur.

**4** –

```c
const char *longest(const char **words, int n) {
    if (n == 0) {
        return NULL;
    }
    const char *best = words[0];
    size_t best_length = strlen(best);
    for (int i = 1; i < n; i++) {
        size_t length = strlen(words[i]);
        if (length > best_length) {
            best = words[i];
            best_length = length;
        }
    }
    return best;
}
```

`longest(list, 4)` derlenir (`"pazartesi"`). `longest(grid, 4)` derlenmez: `char [4][10]`, `char (*)[10]`'a dönüşüyor, `const char **`'a değil (Bölüm 3'teki `int **` hatasının aynısı). Uyumlu hale getirmek için bir pointer array'i kurmak gerekiyor: `const char *view[4] = {grid[0], grid[1], grid[2], grid[3]};` ve `longest(view, 4)`. `grid[i]` bir `char [10]`, `char *`'a dönüşüyor; Ders 4.8'e göre `const char *`'a serbestçe çevrilebiliyor. (`strlen`'in kendisini Ders 4.13'te yazacağız.)

**5** –

```c
bool min_max_ptr(int *a, int n, int **min, int **max) {
    if (n == 0) {
        return false;
    }
    *min = &a[0];
    *max = &a[0];
    for (int i = 1; i < n; i++) {
        if (a[i] < **min) {
            *min = &a[i];
        }
        if (a[i] > **max) {
            *max = &a[i];
        }
    }
    return true;
}
```

`int values[5] = {3, 9, -2, 7, 5};` için `swap(min, max)` (Ders 4.7) sonrası array `{3, -2, 9, 7, 5}` olur. Karşılaştırmalarda `**min`: `min` bir `int **`, `*min` çağıranın pointer'ı, `**min` onun gösterdiği sayı.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.6 (pointer array'leri), §5.7 ve §5.9 (çok boyutlu array'ler ve pointer array'leri), §5.10 (komut satırı argümanları).
- Peter van der Linden, *Expert C Programming*, Bölüm 9–10: array ile pointer'ın ne zaman aynı, ne zaman farklı olduğu; düzensiz (ragged) array'ler.
- C standardı (ISO/IEC 9899:2018), §5.1.2.2.1: `main`'in iki imzası ve `argv[argc]`'nin `NULL` olması; §6.5.3.2¶3: `&*E`'nin `E`'ye eşit olması.

**Sıradaki ders:** Fonksiyon pointer'ı. Bir fonksiyonun adresini bir değişkende tutmak, callback'ler, işlem tablosuyla bir hesap makinesi ve `qsort`'un karşılaştırıcısı.
