---
title: "4.9 void pointer"
description: "Tipi olmayan pointer: void * her nesne pointer'ına dönüşebilir ve geri dönebilir, ama dereference edilemez ve aritmetiği yapılamaz. %p'nin neden (void *) istediği, byte byte çalışan genel bir swap ve reverse, tip bilgisini kaybetmenin bedeli ve _Static_assert ile korunan bir SWAP makrosu."
---

Ders 4.7'de `swap(int *a, int *b)` yazdık. İki `double`'ı değiştirmek istesen? Bir `swap_double` daha. İki `struct Point`? Bir `swap_point`. Her tip için aynı fonksiyonu yeniden yazmak zorundayız, çünkü Ders 4.5'e göre pointer'ın tipi, gösterdiği yerden **kaç byte** okunacağını belirliyor.

Ama bir `swap` aslında değerin **ne olduğuyla** ilgilenmiyor: iki bellek parçasının byte'larını yer değiştiriyor. Tipini bilmeden bir yeri gösterebilen bir pointer olsaydı, tek bir `swap` yeterdi. O pointer'ın adı `void *`.

---

## 1. Tipi olmayan pointer

```c
#include <stdio.h>

int main(void) {
    int x = 42;
    double d = 2.5;
    void *v = &x;
    printf("v = %p\n", v);
    v = &d;
    printf("v = %p\n", v);
    double *dp = v;
    printf("*dp = %g\n", *dp);
    return 0;
}
```

`void *`, "**bir şeyin** adresi, ama ne olduğunu söylemiyorum" demek. Kurallar:

- **Her nesne pointer'ı `void *`'a dönüşebilir**, cast gerekmeden. `v = &x` (`int *`) ve `v = &d` (`double *`) ikisi de serbest.
- **`void *` her nesne pointer'ına geri dönebilir**, yine cast gerekmeden: `double *dp = v;`. Bu, Ders 4.5'teki uyarıdan farklı: `int *`'ı `char *`'a vermek bir hataydı.

```c
char *c = &x;
```

```
error: incompatible pointer types initializing 'char *' with an expression of type 'int *' [-Wincompatible-pointer-types]
```

`void *` bu kuralın tek istisnası: her tiple iki yönde de serbest dönüşen ortak bir ara tip.

Bir koşulla: `void *`'tan geri dönerken **doğru** tipe dönmek senin sorumluluğun. `v`, `d`'yi gösterirken `int *ip = v;` yazmak da derlenir; ama `*ip` bir `double`'ın byte'larını `int` diye okur, ve Ders 4.5'teki strict aliasing kuralına göre bu undefined behavior. Compiler `void *`'ın arkasında ne olduğunu artık bilmiyor; o bilgiyi sen taşıyorsun.

### Neden `%p` `(void *)` istiyor?

Ders 4.1'den beri adresleri `printf("%p", (void *)&x)` diye yazdırıyoruz. C standardına göre `%p` bir `void *` bekliyor. `int *` ile `void *`'ın bu makinede aynı boyutta ve aynı gösterimde olması bir **garanti** değil; standart, farklı tiplerdeki pointer'ların farklı gösterimlere sahip olabileceği makinelere izin veriyor. `printf` gibi değişken sayıda argüman alan fonksiyonlarda compiler dönüşümü kendisi yapmadığı için, cast'i biz yazıyoruz. Bu makinede cast'siz de çalışırdı; ama doğrusu bu.

---

## 2. Yapamadıkları

Tip bilgisi olmayınca, tip bilgisi gerektiren iki işlem de yok.

**Dereference yok.** `*v` kaç byte okumalı? 1 mi, 4 mü, 8 mi? Compiler bilemez:

```c
printf("*v = %d\n", *v);
```

```
warning: ISO C does not allow indirection on operand of type 'void *' [-Wvoid-ptr-dereference]
error: argument type 'void' is incomplete
```

`void`, "boyutu olmayan, eksik (incomplete) bir tip". `void` tipinde bir değer olmadığı için okunamıyor.

**Aritmetik yok.** Ders 4.6'ya göre `p + 1`, `sizeof(*p)` byte ilerliyor. `sizeof(void)` tanımlı değil, dolayısıyla `v + 1` da tanımlı değil.

Ama burada bir sürpriz var: `v + 1` `-Wall -Wextra` ile **derleniyor**, uyarı bile yok.

```c
printf("%p %p\n", v, v + 1);
```

```
0x16ba52178 0x16ba52179
```

clang ve gcc, `void *` aritmetiğini bir **GNU uzantısı** olarak kabul edip `sizeof(void)`'i 1 sayıyor. Standart C değil; başka bir compiler'da derlenmeyebilir. `-pedantic` (standart dışı her şeyi uyar) ya da `-Wpointer-arith` ile görünür oluyor:

```
warning: arithmetic on a pointer to void is a GNU extension [-Wgnu-pointer-arith]
```

Byte byte ilerlemek istiyorsan, standart yol `void *`'ı önce `unsigned char *`'a çevirmek: `(unsigned char *)v + 1`. Ders 4.5'e göre `unsigned char *` her nesnenin byte'larına bakabilen tip; birazdan tam olarak bunu yapacağız.

---

## 3. Her tiple çalışan swap

`void *` ile "nerede" bilgisini alıyoruz; "kaç byte" bilgisini ise ayrı bir parametre olarak istememiz gerekiyor, çünkü pointer artık onu taşımıyor:

```c
#include <stddef.h>

void swap_any(void *a, void *b, size_t size) {
    unsigned char *p = a;
    unsigned char *q = b;
    for (size_t i = 0; i < size; i++) {
        unsigned char tmp = p[i];
        p[i] = q[i];
        q[i] = tmp;
    }
}
```

İçeride `void *`'ları `unsigned char *`'a çeviriyoruz (cast gerekmeden; Bölüm 1), ve `size` byte'ı tek tek yer değiştiriyoruz. Fonksiyon, değiştirdiği şeyin `int` mi `double` mı olduğunu hiç bilmiyor; bilmesine gerek de yok.

```c
struct Point {
    int x;
    int y;
};

int main(void) {
    int i1 = 1, i2 = 2;
    double d1 = 1.5, d2 = -7.25;
    struct Point p1 = {1, 2}, p2 = {30, 40};
    char s1[6] = "kedi", s2[6] = "kopek";

    swap_any(&i1, &i2, sizeof i1);
    swap_any(&d1, &d2, sizeof d1);
    swap_any(&p1, &p2, sizeof p1);
    swap_any(s1, s2, sizeof s1);

    printf("%d %d\n", i1, i2);
    printf("%g %g\n", d1, d2);
    printf("(%d,%d) (%d,%d)\n", p1.x, p1.y, p2.x, p2.y);
    printf("%s %s\n", s1, s2);
    return 0;
}
```

```
2 1
-7.25 1.5
(30,40) (1,2)
kopek kedi
```

Dört farklı tip, tek fonksiyon. Son satırda `&` yok: `s1` bir array, Ders 4.1'e göre zaten ilk elemanının adresine dönüşüyor. `sizeof s1` ise 6, array'in tamamı (Ders 4.1'deki `sizeof` hilesinin çalıştığı tek yer: array'in tanımlandığı fonksiyon).

Bu fonksiyonun standart kütüphanedeki karşılığı yok, ama aynı imza kalıbı her yerde: `memcpy(void *dest, const void *src, size_t n)`, `memset(void *s, int c, size_t n)`, `qsort(void *base, size_t count, size_t size, ...)`. **Bir `void *` ve yanında bir boyut**: C'de "her tiple çalışan" fonksiyonların ortak dili.

### Genel bir reverse

Ders 4.2'deki `reverse`'i de genelleştirebiliriz. Bu sefer bir array'in **elemanlarını** yer değiştireceğiz; her elemanın boyutunu bilmemiz, `i`. elemanın adresini hesaplamak için şart:

```c
void reverse_any(void *base, size_t count, size_t size) {
    unsigned char *bytes = base;
    if (count < 2) {
        return;
    }
    size_t i = 0;
    size_t j = count - 1;
    while (i < j) {
        swap_any(bytes + i * size, bytes + j * size, size);
        i++;
        j--;
    }
}
```

`bytes + i * size`, Ders 4.1'deki adres formülünün ta kendisi: başlangıç + indeks × eleman boyutu. Normalde compiler bu çarpımı `a + i`'de bizim için yapıyor; tip bilgisi olmadığında elle yapıyoruz.

```c
int a[5] = {1, 2, 3, 4, 5};
double b[4] = {0.5, 1.5, 2.5, 3.5};
reverse_any(a, 5, sizeof a[0]);
reverse_any(b, 4, sizeof b[0]);
```

```
5 4 3 2 1
3.5 2.5 1.5 0.5
```

`count < 2` kontrolü, Ders 4.2'deki boş array kenar durumu: `count` `size_t` olduğu için `count - 1`, `count == 0` iken Ders 3.6'daki gibi 2⁶⁴ − 1 olurdu.

---

## 4. Bedeli: compiler artık seni korumuyor

`swap(int *a, int *b)`'ye bir `double *` verirsen compiler hata veriyordu. `swap_any`'e?

```c
int i = 1;
double d = 2.5;
swap_any(&i, &d, sizeof d);
```

Hiçbir uyarı yok. İki pointer da `void *`'a sessizce dönüştü; `size` 8, ama `i` sadece 4 byte. `swap_any`, `i`'nin arkasındaki 4 byte'ı da değiştiriyor: Ders 4.1'deki sınır dışı yazma. AddressSanitizer ile:

```
==24168==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x00016f13a0a4 ...
READ of size 1 at 0x00016f13a0a4 thread T0
    #0 0x000100cc4858 in swap_any d.c:7
    #1 0x000100cc4b00 in main d.c:15
...
  This frame has 2 object(s):
    [32, 36) 'i' (line 13) <== Memory access at offset 36 overflows this variable
    [48, 56) 'd' (line 14)
```

"`i` 4 byte (32–36 arası), sen 36. byte'a dokundun." Genelliğin bedeli bu: **tip kontrolü kayboldu**. `void *` alan bir fonksiyonu çağırırken, compiler'ın normalde yaptığı kontrolleri sen yapmak zorundasın: iki pointer aynı tipte mi, boyut doğru mu?

### Kontrolü geri getirmek: bir makro

Ders 2.11'deki makrolarla bu kontrolün bir kısmını geri alabiliriz:

```c
#define SWAP(a, b) do { \
    _Static_assert(sizeof(a) == sizeof(b), "SWAP: farkli boyutlar"); \
    swap_any(&(a), &(b), sizeof(a)); \
} while (0)
```

`SWAP(i, j)` yazınca adresler ve boyut otomatik hesaplanıyor; boyutu yanlış yazma imkânı kalmıyor. `_Static_assert(koşul, mesaj)`, C11'den beri olan bir **derleme zamanı** kontrolü: koşul yanlışsa program derlenmiyor.

```c
SWAP(i, j);
SWAP(i, d);
```

```
error: static assertion failed due to requirement 'sizeof (i) == sizeof (d)': SWAP: farkli boyutlar
```

Hata, program çalışmadan önce yakalandı. (Aynı boyuttaki bir `int` ile bir `float`'ı yine de sessizce değiştirir; makro bir yardım, tam bir tip kontrolü değil.)

`do { ... } while (0)` tuhaf görünüyor ama C makrolarının bilinen bir kalıbı: birden fazla satırlık bir makroyu **tek bir komut** gibi davrandırıyor. Böylece `if (x) SWAP(a, b); else ...` yazıldığında, Ders 2.11'deki `SQUARE` tuzağına benzer bir sürpriz olmuyor; makro, sonundaki `;` ile birlikte tam bir komut oluşturuyor.

---

## 5. Nerelerde göreceğiz

`void *` bu fazın geri kalanında sık sık karşımıza çıkacak:

- **`qsort`** (Ders 4.11): her tipteki array'i sıralayan standart fonksiyon. `void *base`, eleman sayısı ve eleman boyutu alıyor; elemanları nasıl karşılaştıracağını ise ona bir fonksiyon vererek söylüyoruz.
- **`memcpy`, `memmove`, `memset`, `memcmp`** (Ders 4.18): byte'larla çalışan, tipten bağımsız fonksiyonlar. `swap_any` gibi içeride `unsigned char *` kullanacağız.
- **`malloc`** (Ders 4.22): istenen kadar byte ayırıp `void *` döndürüyor; ne için kullanacağını bilmiyor. `int *a = malloc(10 * sizeof(int));` cast gerektirmiyor, Bölüm 1'deki dönüşüm sayesinde.

Son bir not: C++'ta `void *`'tan başka bir pointer'a dönüşüm **cast gerektirir**. C++ kodunda `int *a = (int *)malloc(...)` görmenin sebebi bu. C'de bu cast gereksiz, hatta zararlı sayılır: `<stdlib.h>`'yi eklemeyi unutursan, eski C'de cast hatayı gizleyebiliyordu.

Bir de fonksiyonlar: `void *` **nesne** pointer'ları için. Bir fonksiyonun adresini (Ders 4.4'te `main`'in adresini yazdırmıştık) `void *`'a çevirmek standart C'de garanti değil; fonksiyon pointer'larının kendi kuralları var, Ders 4.11'de göreceğiz.

---

## Alıştırmalar

**1** – Bu satırlardan hangileri derlenir, hangileri uyarı ya da hata verir? (`-Wall -Wextra -std=c17`)

```c
int x = 5;
double d = 1.0;
void *v = &x;
int *ip = v;
double *dp = &x;
double *dq = v;
v = &d;
printf("%d\n", *(int *)v);
printf("%d\n", *v);
```

Derlenenlerden hangisi çalışırken sorun çıkarır?

**2** – `void *` alan, bir array'deki her elemanı sıfırlayan `void zero_all(void *base, size_t count, size_t size)` yazıp bir `int` ve bir `double` array'iyle dene. (Bir `double`'ın bütün byte'ları 0 olunca değeri ne olur? Ders 3.12.)

**3** – Ders 4.2'deki `rotate_left`'i, Ders 4.2'deki üç ters çevirme fikriyle genelleştir: `void rotate_left_any(void *base, size_t count, size_t size, size_t k)`. Bir `struct Point` array'iyle test et.

**4** – `swap_any`, `a` ve `b` aynı adres olduğunda (`swap_any(&x, &x, sizeof x)`) doğru çalışır mı? Ders 4.7'deki `swap_arith`'le karşılaştır. İki bölge **kısmen** çakışırsa (`swap_any(arr, arr + 1, 2 * sizeof arr[0])`) ne olur?

**5** – Byte byte değiştirmek yerine, `memcpy` ve bir geçici tamponla çalışan bir `swap_any` yaz. Tamponun boyutu ne olmalı? Her `size` için çalışması gerekiyorsa ne yapardın?

<details>
<summary>Cevaplar</summary>

**1** –

| Satır | Sonuç |
| --- | --- |
| `void *v = &x;` | ✓ |
| `int *ip = v;` | ✓ |
| `double *dp = &x;` | ✗ hata: `int *` ile `double *` uyumsuz |
| `double *dq = v;` | ✓ derlenir. `v` o anda `x`'i (bir `int`'i) gösteriyor; `*dq` okunursa 4 byte'lık bir `int`'ten 8 byte okunur, sınır dışı ve undefined behavior. |
| `v = &d;` | ✓ |
| `*(int *)v` | ✓ derlenir, ama bir `double`'ın ilk 4 byte'ını `int` diye okuyor: strict aliasing ihlali, undefined behavior. |
| `*v` | ✗ hata: `void` eksik bir tip |

**2** –

```c
void zero_all(void *base, size_t count, size_t size) {
    unsigned char *bytes = base;
    for (size_t i = 0; i < count * size; i++) {
        bytes[i] = 0;
    }
}
```

Elemanları ayrı ayrı düşünmeye gerek yok: array'in toplam `count * size` byte'ını sıfırlamak yeterli. Bütün bitleri 0 olan bir `double`, Ders 3.12'deki IEEE 754 düzenine göre işaret 0, üs 0, kesir 0: tam olarak `+0.0`. (Bu, IEEE 754'ün bir özelliği; C standardı her makine için bunu garanti etmiyor, ama bu serinin bütün makinelerinde doğru.) Ders 4.18'deki `memset` tam olarak bu işi yapıyor.

**3** –

```c
void reverse_range_any(void *base, size_t from, size_t to, size_t size) {
    unsigned char *bytes = base;
    while (from + 1 < to) {
        to--;
        swap_any(bytes + from * size, bytes + to * size, size);
        from++;
    }
}

void rotate_left_any(void *base, size_t count, size_t size, size_t k) {
    if (count == 0) {
        return;
    }
    k %= count;
    reverse_range_any(base, 0, k, size);
    reverse_range_any(base, k, count, size);
    reverse_range_any(base, 0, count, size);
}
```

`to` dahil olmayan sınır (`[from, to)`); `from + 1 < to` koşulu, `to - 1`'i `size_t`'de eksiye düşürmeden "en az iki eleman kaldı mı?" diye soruyor.

**4** – Aynı adreste doğru çalışır: her byte kendisiyle yer değiştiriyor, `tmp` değeri koruyor, sonuç değişmiyor. `swap_arith` ise sıfırlıyordu, çünkü değeri geçici bir değişkende saklamadan aynı yere iki kez yazıyordu. Kısmi çakışmada ise yanlış: `arr = {1, 2, 3}` için ilk 4 byte'ı (`arr[0]`) `arr[1]`'le değiştirdikten sonra, ikinci 4 byte artık `arr[1]`'in **yeni** değerini taşıyor; sonuç `{2, 3, 1}` olur, `{2, 3}` ile `{1, 2}`'nin yer değiştirmesi değil. Kısmen çakışan bölgeler sorusu, Ders 4.18'deki `memmove`'un ta kendisi.

**5** –

```c
void swap_any(void *a, void *b, size_t size) {
    unsigned char tmp[64];
    unsigned char *p = a;
    unsigned char *q = b;
    while (size > 0) {
        size_t chunk = size < sizeof tmp ? size : sizeof tmp;
        memcpy(tmp, p, chunk);
        memcpy(p, q, chunk);
        memcpy(q, tmp, chunk);
        p += chunk;
        q += chunk;
        size -= chunk;
    }
}
```

`size` kadar bir tampon, `size` çalışırken belli olduğu için sabit bir array olarak yazılamıyor (Ders 4.22'ye kadar). Sabit boyutlu bir tamponla parça parça değiştirmek her `size` için çalışıyor. `memcpy`, byte byte döngüden daha hızlı olabilir, çünkü Ders 4.18'de göreceğimiz gibi birden fazla byte'ı aynı anda kopyalıyor.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.11 ve §A6.8: `void *` dönüşümleri.
- C standardı (ISO/IEC 9899:2018), §6.3.2.3¶1: her nesne pointer'ının `void *`'a ve geri dönüşümü; §6.2.5¶19: `void`'in eksik bir tip olması; §7.21.6.1¶8: `%p`'nin `void *` beklemesi; §6.7.10: `_Static_assert`.
- Kenneth Reek, *Pointers on C*, Bölüm 6.
- GCC belgeleri, "Arithmetic on void- and Function-Pointers": `sizeof(void) == 1` uzantısı.

**Sıradaki ders:** Pointer'a pointer. `int **`, iki boyutlu array ile pointer array'i arasındaki fark, ve `main`'in `argv`'si.
