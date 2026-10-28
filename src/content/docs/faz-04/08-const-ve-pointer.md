---
title: "4.8 const ve pointer"
description: "Bir pointer'da iki şey değişebilir: gösterdiği yer ve pointer'ın kendisi. const int *, int *const ve const int *const farkları, tanımları sağdan sola okumak, int *'dan const int *'a serbest ama tersine uyarılı dönüşüm, const'u cast ile kaldırıp yazmanın undefined behavior olması, fonksiyon imzalarında const doğruluğu ve strchr ikilemi."
---

Ders 3.21'de `const`'u tanıdık: `const double PI = 3.14159;` bir daha değiştirilemiyor. Ders 3.16'dan beri parametrelerde `const char text[]` yazıyoruz; Ders 4.6'da da onun pointer hali olan `const int *a`'yı kullandık ve ayrıntısını bu derse bıraktık.

Bir pointer söz konusu olunca `const`'un iki farklı anlamı olabilir, çünkü bir pointer'da **iki şey** değişebilir (Ders 4.5): pointer'ın **gösterdiği yer** (`*p = …`) ve pointer'ın **kendisi** (`p = …`). `const` hangisini kilitliyor? Cevap, `const`'un `*`'ın hangi tarafında yazıldığına bağlı.

---

## 1. Üç tanım

```c
int x = 1;
int y = 2;

const int *p = &x;
int *const q = &x;
const int *const r = &x;
```

Her birinde iki şeyi deneyelim: gösterilen yeri değiştirmek ve pointer'ı başka bir yere yöneltmek.

```c
*p = 5;
p = &y;
*q = 5;
q = &y;
*r = 5;
r = &y;
```

```
error: read-only variable is not assignable                                (*p = 5)
error: cannot assign to variable 'q' with const-qualified type 'int *const' (q = &y)
error: read-only variable is not assignable                                (*r = 5)
error: cannot assign to variable 'r' with const-qualified type 'const int *const' (r = &y)
```

`p = &y` ve `*q = 5` derlendi; diğerleri hata.

| Tanım | `*p = …` (gösterilen yer) | `p = …` (pointer) | Okunuşu |
| --- | --- | --- | --- |
| `int *p` | serbest | serbest | int'i gösteren pointer |
| `const int *p` | **yasak** | serbest | **const int**'i gösteren pointer |
| `int *const p` | serbest | **yasak** | int'i gösteren **const pointer** |
| `const int *const p` | **yasak** | **yasak** | const int'i gösteren const pointer |

### Sağdan sola oku

Tanımları ezberlemek yerine **sağdan sola** okumak işe yarar:

- `const int *p` → "`p` bir pointer (`*`), bir `int`'e, ki o `const`." Kilitli olan `int`.
- `int *const q` → "`q` bir `const`, pointer (`*`), bir `int`'e." Kilitli olan pointer'ın kendisi.
- `const int *const r` → "`r` bir `const` pointer, bir `const int`'e." İkisi de.

Kısa kural: **`const`, `*`'ın solundaysa gösterilen şey; sağındaysa pointer'ın kendisi sabit.** `const int *p` ile `int const *p` aynı şey; ikisinde de `const` `*`'ın solunda. Bu seride ilkini yazıyoruz, çünkü C kütüphanelerinin hemen hepsi öyle yazıyor.

### Hangisi ne zaman?

- **`const int *`**: açık ara en sık kullanılanı. "Bu adresteki veriyi **okuyacağım ama değiştirmeyeceğim**." Fonksiyon parametrelerinin büyük çoğunluğu bu.
- **`int *const`**: "Bu pointer hep **aynı yeri** gösterecek." Nadiren kullanılır; Ders 4.5'teki örnekteki gibi bir pointer'ı yanlışlıkla başka yere yöneltmeyi engellemek için. Ders 4.1'de array'lere atama yapılamadığını gördük; bir array'in adı, bir anlamda bir `int *const` gibi davranıyor.
- **`const int *const`**: ikisi birden. Örneğin değişmeyecek bir tabloyu gösteren global bir pointer.

Önemli bir ayrıntı: `const int *p = &x;` yazmak `x`'i **sabit yapmıyor**. `x` hâlâ sıradan bir `int`; `x = 5` yazabilirsin. `const`, sadece **bu pointer üzerinden** yazmayı yasaklıyor. Bir değişkeni gösteren iki pointer olabilir; biri `const`, diğeri değil (Ders 4.7'deki aliasing). `*p`'nin değeri, `p`'ye hiç dokunmadan değişebilir.

---

## 2. Dönüşümler: bir yönde serbest

Bir `int *`'ı bir `const int *`'a vermek her zaman serbest:

```c
int x = 1;
int *plain = &x;
const int *view = plain;
```

Sorun yok: `view`, `plain`'in izin verdiğinden **daha az** şey yapabiliyor. Bir değişkene "değiştirmeyeceğim" sözüyle bakmak her zaman güvenli.

Ters yönde ise compiler uyarıyor:

```c
const int limit = 10;
int *w = &limit;

const int *ok = &x;
int *back = ok;
```

```
warning: initializing 'int *' with an expression of type 'const int *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
warning: initializing 'int *' with an expression of type 'const int *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
```

"Discards qualifiers": `const` niteleyicisi **atılıyor**. `w` üzerinden, değişmemesi gereken `limit`'e yazılabilir hale geldi. Ders 3.21'deki `modify(word)` uyarısı da bu: `const char[]` bir `char *` parametresine verilince `const` atılıyordu.

C'de bu bir uyarı; C++'ta ise **hata**. C programlarını `-Werror` ile (Ders 2.13) derlemek, bu uyarıyı da hataya çevirir.

---

## 3. const'u cast ile kaldırmak

Uyarıyı bir cast ile susturabilirsin: `int *w = (int *)&limit;`. Compiler artık bir şey demiyor. Ama `w` üzerinden yazmak?

```c
#include <stdio.h>

const int global_limit = 100;

int main(void) {
    const int local_limit = 10;
    int *lp = (int *)&local_limit;
    *lp = 20;
    printf("local_limit = %d, *lp = %d\n", local_limit, *lp);

    int *gp = (int *)&global_limit;
    *gp = 200;
    printf("global_limit = %d\n", global_limit);
    return 0;
}
```

`-O0` ile:

```
local_limit = 10, *lp = 20
zsh: bus error  ./c2
```

İki tuhaflık var.

**Aynı yer, iki farklı değer.** `lp`, `local_limit`'in adresini gösteriyor ve `*lp` 20 diyor; ama `local_limit` 10 yazıyor. Compiler `local_limit`'in `const` olduğunu bildiği için, onu her kullandığı yerde bellekten okumak yerine doğrudan 10 yazdı. `*lp = 20` belleği değiştirdi ama compiler'ın "biliyorum, bu 10" kararını değiştiremedi.

**Global olan programı çökertti.** `global_limit`, Ders 4.4'teki haritada **salt okunur veri** bölgesindeydi. İşletim sistemi o sayfayı yazmaya kapalı işaretlemişti; yazma girişimi programı durdurdu (bu sefer adı **bus error**, segmentation fault'un bir kardeşi).

`-O2` ile aynı program çökmedi bile; `global_limit = 100` yazıp normal bitti, çünkü compiler yazmanın sonucunu hiç kullanmadı. Ders 2.12'nin bildik tablosu: **gerçekten `const` tanımlanmış bir nesneyi değiştirmeye çalışmak undefined behavior**, ve sonuç her şey olabilir.

Ama dikkat: cast'in kendisi yasak değil. `const int *` olarak **aldığın** bir pointer, aslında `const` olmayan bir değişkeni gösteriyorsa, `const`'u cast ile kaldırıp yazmak tanımlı. Sorun, gösterilen nesnenin **kendisinin** `const` olması. Fonksiyonun bunu bilmesinin yolu olmadığı için kural basit: **`const`'u cast ile atma.** Bir fonksiyon bir şeyi değiştirmek istiyorsa, parametresi `const` olmamalı.

Ders 4.12'de bir string sabitini (`"merhaba"`) değiştirmeye çalışınca aynı şeyin olduğunu göreceğiz: o da salt okunur bölgede.

---

## 4. Fonksiyon imzalarında const

Ders 3.21'deki **const doğruluğu** kuralının pointer'lı hali: bir fonksiyon bir pointer'ın gösterdiği yeri değiştirmiyorsa, parametre `const T *` olmalı.

```c
void print_array(const int *a, int n) {
    for (int i = 0; i < n; i++) {
        printf("%d ", a[i]);
    }
    printf("\n");
}

void fill(int *a, int n, int value) {
    for (int i = 0; i < n; i++) {
        a[i] = value;
    }
}
```

Sadece imzalara bakarak `print_array`'in array'i okuduğunu, `fill`'in değiştirdiğini anlıyorsun. Ve `print_array`, Bölüm 2'deki serbest dönüşüm sayesinde hem sıradan hem `const` array'lerle çağrılabiliyor; `fill` ise `const` bir array'le çağrılırsa compiler uyarıyor. Standart kütüphanenin imzaları da hep böyle:

```c
size_t strlen(const char *s);
void *memcpy(void *dest, const void *src, size_t n);
int strcmp(const char *a, const char *b);
```

`memcpy`'nin imzası iki pointer'dan hangisinin okunduğunu, hangisinin yazıldığını tek başına söylüyor. Ders 4.13'ten itibaren bu fonksiyonları kendimiz yazarken imzaları birebir kopyalayacağız.

### Parametrenin kendisi const olunca

Peki `void f(int *const p)`? Bu, `p`'nin fonksiyonun **içinde** başka bir yere yöneltilemeyeceğini söylüyor. Çağıran için hiçbir anlamı yok: Ders 4.7'ye göre `p` zaten bir kopya, ve fonksiyon onu değiştirse bile çağıranın pointer'ı etkilenmez. Bu yüzden fonksiyon **bildirimlerinde** (header dosyalarında; Ders 2.11) böyle bir `const` yazılmaz. Önemli olan her zaman `*`'ın **solundaki** `const`.

### strchr ikilemi

Ders 4.6'daki `find_pointer`, `const int *` alıp `const int *` döndürüyordu. Bu bir sorun yaratıyor: array'in kendisi `const` değilse ve bulduğun elemanı **değiştirmek** istiyorsan?

```c
int values[5] = {4, 8, 15, 16, 23};
const int *found = find_pointer(values, values + 5, 15);
*found = 0;
```

```
error: read-only variable is not assignable
```

`values` değiştirilebilir bir array, ama `find_pointer`'ın dönüş tipi bunu "unutturdu". İki çözüm var: biri `int *` alıp döndüren, diğeri `const int *` alıp döndüren **iki ayrı** fonksiyon yazmak (C++'ın yaptığı); ya da `const int *` alıp `int *` döndürmek. C standart kütüphanesi, yazı içinde bir karakter arayan `strchr` için ikincisini seçmiş:

```c
char *strchr(const char *s, int c);
```

`const` bir yazı alıyor, `const` olmayan bir pointer döndürüyor; yani içeride `const`'u cast ile atıyor. Bu, `const` bir yazıda arama yapıp dönen pointer üzerinden yazmana compiler'ın **izin vermesi** demek; Bölüm 3'teki undefined behavior'a açık bir kapı. C23 bu kapıyı kapattı: `strchr`'e `const char *` verirsen artık `const char *` döner. Ders 4.17'de `strchr`'i yazarken bu kararı biz de vereceğiz.

---

## Alıştırmalar

**1** – Her satır için derlenip derlenmeyeceğini söyle:

```c
int a = 1;
int b = 2;
const int *p1 = &a;
int *const p2 = &a;
const int *const p3 = &a;

p1 = &b;
*p1 = 3;
p2 = &b;
*p2 = 3;
a = 4;
int *p4 = p2;
int *p5 = p1;
```

**2** – Bu tanımları sağdan sola okuyarak Türkçe yaz: `char const *s;` `const char *const t;` `int **u;` `const int **v;` `int *const *w;`

**3** – Ders 4.2'deki fonksiyonların (`sum`, `index_of_max`, `average`, `reverse`, `rotate_left`, `is_sorted`, `find`, `unique`) imzalarını pointer parametreleriyle yeniden yaz. Hangilerinin parametresi `const` olmalı?

**4** – Bölüm 1'deki `const int *p = &x;`'ten sonra `x = 5;` yazıp `*p`'yi yazdır. Ne çıkar? Bu, `const`'un neyi garanti ettiği hakkında ne söylüyor?

**5** – Bir `const` array'in en büyük elemanını sıfırlamak istiyorsun:

```c
const int scores[4] = {70, 85, 60, 90};
int *best = (int *)find_pointer(scores, scores + 4, 90);
*best = 0;
```

Derlenir mi? Çalışır mı? `scores`, `const` olmayan bir array olsaydı?

<details>
<summary>Cevaplar</summary>

**1** –

| Satır | Sonuç |
| --- | --- |
| `p1 = &b;` | ✓ pointer serbest |
| `*p1 = 3;` | ✗ gösterilen yer `const` |
| `p2 = &b;` | ✗ pointer `const` |
| `*p2 = 3;` | ✓ gösterilen yer serbest |
| `a = 4;` | ✓ `a`'nın kendisi `const` değil |
| `int *p4 = p2;` | ✓ `p2`'nin kopyası; kopya `const` olmak zorunda değil, ve gösterilen yer zaten serbest |
| `int *p5 = p1;` | ⚠ uyarı: `const` atılıyor (discards qualifiers) |

**2** –

- `char const *s` → `s` bir pointer, bir `const char`'a. (`const char *s` ile aynı.)
- `const char *const t` → `t` bir `const` pointer, bir `const char`'a.
- `int **u` → `u` bir pointer, bir pointer'a, bir `int`'e.
- `const int **v` → `v` bir pointer, bir pointer'a, bir `const int`'e.
- `int *const *w` → `w` bir pointer, bir `const` pointer'a, bir `int`'e.

**3** –

```c
long long sum(const int *a, int n);
int index_of_max(const int *a, int n);
double average(const int *a, int n);
void reverse(int *a, int n);
void rotate_left(int *a, int n, int k);
bool is_sorted(const int *a, int n);
int find(const int *a, int n, int value);
int unique(int *a, int n);
```

Sadece okuyanlar `const`; array'i değiştiren `reverse`, `rotate_left` ve `unique` değil. Ders 4.1'e göre `const int a[]` ile `const int *a` parametrede aynı şey; hangisini yazacağın bir tercih. Bu seride, bir array beklendiğini vurgulamak istediğimizde `[]`, pointer aritmetiği yapacağımızda `*` yazıyoruz.

**4** – `5` çıkar. `x` `const` değil; `p` üzerinden yazılamıyor, ama `x`'in kendisi değişebiliyor ve `p` hâlâ onu gösteriyor. `const int *`, "bu veri değişmeyecek" demiyor; "**ben** bu veriyi değiştirmeyeceğim" diyor. Bir fonksiyon `const int *` aldığında, verinin çağrı sırasında başka bir yoldan değişmeyeceğinden emin olamaz.

**5** – Derlenir: cast uyarıyı susturuyor. Ama `scores` gerçekten `const` tanımlanmış bir array; Bölüm 3'e göre ona yazmak **undefined behavior**. Yerel bir array olduğu için çökmeyebilir; global olsaydı Bölüm 3'teki `global_limit` gibi büyük ihtimalle çökerdi. `scores` `const` olmasaydı (`int scores[4]`), aynı cast **tanımlı** ve doğru olurdu: pointer, aslında değiştirilebilir bir nesneyi gösteriyor. İkisinin farkını kodun bu satırından görmenin yolu yok; `const`'u atmamanın sebebi bu. Doğrusu, değiştirilebilir array için `const` olmayan bir `find_pointer` hali yazmak.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §A8.2: tip niteleyicileri.
- C standardı (ISO/IEC 9899:2018), §6.7.3¶6: `const` tanımlanmış bir nesneyi `const` olmayan bir lvalue üzerinden değiştirmenin undefined behavior olması; §6.3.2.3¶2: niteleyici ekleyen pointer dönüşümleri. C23 (ISO/IEC 9899:2024), §7.26.5: niteleyiciyi koruyan `strchr` ve benzerleri.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 2: `const` niteleyicisi.
- SEI CERT C Coding Standard, EXP40-C: sabit bir nesneyi değiştirmemek.

**Sıradaki ders:** `void` pointer. Herhangi bir tipi gösterebilen pointer, ve her tiple çalışan bir `swap`.
