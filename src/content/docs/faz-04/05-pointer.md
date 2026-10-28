---
title: "4.5 Pointer"
description: "Bir adresi tutan değişken: pointer'ı tanımlamak, * ile gösterdiği yeri okumak ve yazmak, pointer'ın da bir adresi olması, pointer tipinin neden önemli olduğu (unsigned char * ile bir sayının byte'larını okumak), başlatılmamış ve NULL pointer'lar, ve tanımlamadaki int *a, b tuzağı."
---

Ders 4.4'te adresleri yazdırdık, aralarındaki farkları hesapladık, bir bellek haritası çizdik. Ama bir adresi bir **değişkende tutmadık**, ve en önemlisi, bir adresi kullanarak o adresteki değeri **okumadık ya da değiştirmedik**. `scanf`'in `&value`'yu alıp `value`'nun içine yazabilmesi tam olarak bunu gerektiriyor.

Bir adresi tutan değişkene **pointer** denir (Türkçesiyle "gösterici"; bir yeri gösterir). C'nin en güçlü, en çok korkulan ve aslında en basit fikri.

---

## 1. Tanımlamak ve kullanmak

```c
#include <stdio.h>

int main(void) {
    int x = 42;
    int *p = &x;

    printf("x = %d, &x = %p\n", x, (void *)&x);
    printf("p = %p, *p = %d\n", (void *)p, *p);

    *p = 100;
    printf("x = %d\n", x);
    return 0;
}
```

```
x = 42, &x = 0x16d7b6178
p = 0x16d7b6178, *p = 42
x = 100
```

Satır satır:

- `int *p = &x;` → "`p` adında, **bir `int`'in adresini** tutan bir değişken aç; içine `x`'in adresini koy." `int *`, "int'i gösteren pointer" diye okunur. Ders 4.4'te `&x`'in tipinin `int *` olduğunu söylemiştik: `p`'nin tipi tam olarak bu.
- `p`'nin değeri, `x`'in adresi: ikisi aynı sayı.
- `*p` → "`p`'nin gösterdiği yerdeki değer". `p`'deki adrese git, oradaki `int`'i oku: 42. Bu işleme **dereference** (pointer'ın gösterdiği yere gitmek) denir.
- `*p = 100;` → "`p`'nin gösterdiği yere 100 yaz." `x`'e hiç dokunmadık, ama `x` artık 100: çünkü `p`'nin gösterdiği yer, `x`'in kendisi.

`*`, Ders 4.4'teki `&`'in **tersi**:

| İfade | Anlamı | Değer |
| --- | --- | --- |
| `x` | `x`'teki değer | 42 |
| `&x` | `x`'in adresi | `0x16d7b6178` |
| `p` | `p`'deki değer, yani bir adres | `0x16d7b6178` |
| `*p` | `p`'nin gösterdiği yerdeki değer | 42 |
| `*&x` | `x`'in adresindeki değer | 42, `x`'in kendisi |

Bir uyarı: `*` işareti C'de üç farklı yerde üç farklı anlamda kullanılıyor. `a * b`'de çarpma; `int *p` tanımında "bu bir pointer"; `*p` ifadesinde "gösterdiği yere git". Compiler hangisi olduğunu bağlamdan anlıyor; Ders 3.18'deki `&` gibi.

`*p`, kullanıldığı her yerde `x` gibi davranıyor: okunabilir, değiştirilebilir, bir hesabın içinde kullanılabilir. Pointer'ı başka bir değişkene de yöneltebiliriz:

```c
int y = 7;
p = &y;
*p = *p + 1;
printf("x = %d, y = %d\n", x, y);
```

```
x = 100, y = 8
```

`p = &y` pointer'ın **kendisini** değiştiriyor: artık `y`'yi gösteriyor. `*p = *p + 1` ise **gösterdiği yeri**: `y` 8 oldu, `x`'e dokunulmadı. Pointer'larla çalışırken her satırda kendine sor: pointer'ı mı değiştiriyorum, gösterdiği yeri mi?

---

## 2. Bir kutu ve bir ok

Pointer'ları çizmenin geleneksel yolu: her değişken bir kutu, ve pointer'ın kutusundan gösterdiği kutuya bir ok.

```
       p                         x
  ┌────────────┐            ┌────────┐
  │ 0x…6178  ──┼──────────► │   42   │
  └────────────┘            └────────┘
   adres 0x…6170             adres 0x…6178
```

`p` de bir değişken; onun da bellekte bir yeri ve **kendi adresi** var. LLDB ile bakalım (Ders 4.1'deki gibi, `-g` ile derleyip `*p = 100;` satırında durarak):

```
(lldb) p p
(int *) 0x000000016fdfdf58
(lldb) p *p
(int) 42
(lldb) p &p
(int **) 0x000000016fdfdf50
(lldb) memory read --size 8 --format x --count 1 &p
0x16fdfdf50: 0x000000016fdfdf58
```

- `p`'nin değeri `x`'in adresi (`…df58`), ve LLDB tipini `int *` olarak gösteriyor.
- `p`'nin kendi adresi `…df50`: `x`'ten 8 byte aşağıda, stack'te (Ders 4.4).
- `&p`'nin tipi `int **`: "bir `int *`'in adresi", pointer'ı gösteren pointer. Ders 4.10'da göreceğiz.
- `memory read` ile `p`'nin 8 byte'ını okuyunca, içinde tam olarak `x`'in adresi yazıyor. Bir pointer'ın bellekteki hali bu: 8 byte'lık sıradan bir sayı. Onu özel yapan şey, compiler'ın bu sayıyı bir **adres** olarak kullanmasına izin vermemiz.

---

## 3. Pointer'ın tipi neden önemli?

Bütün adresler 8 byte (Ders 4.4). O halde neden `int *`, `double *`, `char *` diye farklı pointer tipleri var? Tek bir "adres" tipi yetmez mi?

Yetmez, çünkü adres sadece **nereden başlanacağını** söylüyor. `*p` yazınca o adresten **kaç byte** okunacağını ve o byte'ların **nasıl yorumlanacağını** pointer'ın tipi söylüyor:

```c
int x = 42;
double d = 1.0;
unsigned char c = 'a';
int *p = &x;
double *dp = &d;
unsigned char *cp = &c;
printf("%zu %zu %zu\n", sizeof(p), sizeof(dp), sizeof(cp));
printf("%zu %zu %zu\n", sizeof(*p), sizeof(*dp), sizeof(*cp));
```

```
8 8 8
4 8 1
```

Pointer'ların üçü de 8 byte; gösterdikleri şeyler 4, 8 ve 1 byte. `*dp`, adresten başlayarak 8 byte okuyup onları Ders 3.14'teki `double` biçimiyle yorumlar; `*p`, 4 byte okuyup ikiler tümleyeniyle (Ders 3.3). Faz 0'dan beri tekrarladığımız cümle: **bitlerin anlamını bağlam belirler**. Pointer'ın tipi, o bağlam.

Bu yüzden compiler, tipleri uymayan pointer'ları karıştırmana izin vermiyor:

```c
double d = 1.0;
int *p = &d;
```

```
error: incompatible pointer types initializing 'int *' with an expression of type 'double *' [-Wincompatible-pointer-types]
```

Bu atamaya izin verseydi, `*p` bir `double`'ın ilk 4 byte'ını bir `int` gibi okurdu.

### Byte byte okumak

Ama bazen tam olarak bunu **istiyoruz**. Ders 3.9'da bir sayının byte'larını görmek için `memcpy` ile bir `uint8_t` array'ine kopyalamıştık, ve "Faz 4'te bir pointer ile byte byte okuyacağız" demiştik. İşte o pointer:

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    int32_t n = 16909060;
    unsigned char *bytes = (unsigned char *)&n;
    printf("%d %d %d %d\n", bytes[0], bytes[1], bytes[2], bytes[3]);
    return 0;
}
```

```
4 3 2 1
```

- `(unsigned char *)&n`: `n`'in adresini, "bir `unsigned char`'ın adresi" olarak görmek istediğimizi açıkça söylüyoruz. Bu cast olmadan compiler, yukarıdaki gibi tip uyuşmazlığı hatası verirdi.
- Pointer'ın tipi artık 1 byte'lık bir şeyi gösteriyor; `bytes[i]`, `n`'in `i`. byte'ı. Bir pointer'ı array gibi `[]` ile kullanabilmemizin sebebini Ders 4.6'da göreceğiz; şimdilik `bytes[0]`'ın `*bytes` ile aynı şey olduğunu söylemek yeter.
- Sonuç Ders 3.9'daki little endian düzen: en anlamsız byte (4) en düşük adreste.

Bu sefer hiçbir şey kopyalamadık: `bytes[0]` ile `n`'in ilk byte'ının **kendisine** bakıyoruz. `bytes[0] = 5;` yazsaydık `n` değişirdi.

**Hangi pointer tipiyle her şeye bakılabilir?** C standardı bu iş için `char`, `signed char` ve `unsigned char` pointer'larına özel bir izin veriyor: herhangi bir nesnenin byte'larını onlarla okuyabilirsin. Başka tiplerde bu izin yok: bir `float`'ın bitlerini görmek için `int *` ile `float`'ı göstermek **undefined behavior**; compiler, farklı tipteki pointer'ların aynı yeri göstermeyeceğini varsayarak kodu düzenleyebilir. Ders 3.12'de `show_float`'ta `memcpy` kullanmamızın sebebi bu. Bu kurala **strict aliasing** denir; Ders 4.27'de union'larla birlikte döneceğiz.

---

## 4. Hiçbir yeri göstermeyen pointer

### Başlatılmamış pointer

Yerel bir değişkene ilk değer vermezsen içinde ne olduğu belirsiz (Ders 2.12). Pointer'lar için bu çok daha tehlikeli:

```c
int *q;
printf("%d\n", *q);
```

```
warning: variable 'q' is uninitialized when used here [-Wuninitialized]
```

Uyarıya rağmen derleyip çalıştırınca bilgisayarımızda `-291602240` yazdı. `q`'nun içinde rastgele bir sayı vardı; `*q` o sayıyı bir adres kabul edip oradaki byte'ları okudu. Bu sefer program çökmedi, çünkü rastgele sayı tesadüfen programın erişebildiği bir yeri gösteriyordu. `*q = 5` yazsaydık, o rastgele yerdeki **bir şeyi** bozacaktık; Ders 4.1'deki sınır dışına yazmanın daha kötü bir hali. **Her pointer'a tanımlarken bir değer ver.**

### NULL

Bazen bir pointer'ın henüz hiçbir şeyi göstermediğini söylemek isteriz. Bunun için özel bir değer var: **`NULL`** (`<stddef.h>`, `<stdio.h>` ve `<stdlib.h>`'te tanımlı). Bütün sistemlerde pratikte 0 adresi.

```c
#include <stdio.h>

int main(void) {
    int *p = NULL;
    printf("%p\n", (void *)p);
    printf("%d\n", *p);
    return 0;
}
```

```
0x0
zsh: segmentation fault  ./p4
```

`NULL`'u dereference etmek undefined behavior; pratikte işletim sistemi 0 adresinin çevresini **hiçbir programa** açmadığı için program hemen durduruluyor. Bu iyi bir şey: hata sessizce bir şeyi bozmak yerine anında ortaya çıkıyor. ASan da nedenini açıkça söylüyor:

```
==3347==ERROR: AddressSanitizer: SEGV on unknown address 0x000000000000 ...
==3347==The signal is caused by a READ memory access.
==3347==HINT: address points to the zero page.
    #0 0x00010402c844 in main p4.c:3
```

`NULL`'un asıl kullanımı bir **işaret** olmak: "burada bir şey yok". Ders 3.17'de `strtol(text, &end, 10)` çağırmıştık; `end`'e ihtiyacın yoksa yerine `NULL` verebilirsin, ve `strtol` bunu görünce bitiş yerini hiçbir yere yazmaz. Bir pointer'ı kullanmadan önce `NULL` olup olmadığına bakmak C'de çok yaygın bir kalıp:

```c
if (p != NULL) {
    printf("%d\n", *p);
}
```

`NULL` pointer'ın mucidi Tony Hoare, 2009'daki bir konuşmasında onu "milyar dolarlık hatam" diye anmıştı: o zamandan bu yana sayısız programın çökmesine sebep oldu. C23, `NULL`'un yanına türü daha belirgin olan `nullptr`'ı ekledi; ikisi de aynı işi görüyor.

---

## 5. Tanımlama tuzağı

`int *p` yazarken `*` hangi tarafa ait? Boşluğun yeri compiler için fark etmez; şu üçü aynı:

```c
int *p;
int* p;
int * p;
```

Ama `int* p` yazmak, `*`'ın tipin bir parçası olduğunu düşündürüyor; ve bu düşünce bir tuzağa düşürüyor:

```c
int* a, b;
```

Bu satır **iki pointer tanımlamıyor**. `a` bir `int *`, ama `b` düz bir `int`. C'de `*` tipe değil, **değişkenin adına** bağlanır; satır `int *a, b;` diye okunur. Bu yüzden bu seride `int *p` yazıyoruz. İki pointer için:

```c
int *a, *b;
```

Ya da daha açık olanı: her satırda tek bir tanım.

---

## Alıştırmalar

**1** – Bu programın çıktısını, çalıştırmadan, bir kutu-ok çizimiyle tahmin et:

```c
int a = 1;
int b = 2;
int *p = &a;
int *q = &b;
*p = *q;
p = q;
*p = 10;
printf("%d %d %d %d\n", a, b, *p, *q);
```

**2** – Ders 3.12'deki `show_float`'un `memcpy` satırını, Bölüm 3'teki gibi bir `unsigned char *` ile değiştir: float'ın 4 byte'ını onaltılık yazdır. `5.75f` için ne çıkıyor? Byte'ların sırası Ders 3.12'deki `0x40B80000` ile nasıl ilişkili?

**3** – `double d = 1.0;` için `unsigned char *` ile 8 byte'ı yazdır. Ders 3.14'teki `0x3FF0000000000000` ile karşılaştır.

**4** – Bu satırların her biri ne tanımlıyor? `int *a, b, *c;` `int **d;` `int e[3], *f = e;`

**5** – Bir arkadaşın şöyle yazmış:

```c
int *p;
*p = 5;
```

"`p` bir pointer, `5`'i gösterdiği yere yazıyorum." Ne yanlış? `int *p = 5;` yazsaydı ne olurdu? Doğrusu ne?

<details>
<summary>Cevaplar</summary>

**1** –

| Satır | `a` | `b` | `p` gösteriyor | `q` gösteriyor |
| --- | --- | --- | --- | --- |
| Başta | 1 | 2 | `a` | `b` |
| `*p = *q;` | **2** | 2 | `a` | `b` |
| `p = q;` | 2 | 2 | **`b`** | `b` |
| `*p = 10;` | 2 | **10** | `b` | `b` |

Çıktı: `2 10 10 10`. İkinci satır `a`'yı değiştirdi (gösterilen yer), üçüncüsü `p`'yi (pointer'ın kendisi). Sonunda iki pointer da `b`'yi gösteriyor.

**2** –

```c
float f = 5.75f;
unsigned char *bytes = (unsigned char *)&f;
for (int i = 0; i < 4; i++) {
    printf("%02x ", bytes[i]);
}
```

`00 00 b8 40`. `0x40B80000`'ın byte'ları, little endian sırayla: en anlamsız byte (`00`) başta, en anlamlı (`40`, işaret ve üssün ilk bitleri) sonda. `%02x`, Ders 3.10'daki gibi iki basamaklı onaltılık.

**3** – `00 00 00 00 00 00 f0 3f`. Yine little endian: `0x3FF0000000000000`'ın byte'ları tersten.

**4** –

- `int *a, b, *c;` → `a` ve `c` `int *`, `b` `int`.
- `int **d;` → `d`, bir `int *`'i gösteren pointer (Bölüm 2'deki `&p`'nin tipi).
- `int e[3], *f = e;` → `e` 3 elemanlı bir `int` array'i; `f` bir `int *`, ve Ders 4.1'deki kural gereği `e`'nin ilk elemanını gösteriyor.

**5** – `p`'ye hiç değer verilmemiş; Bölüm 4'teki başlatılmamış pointer. `*p = 5` rastgele bir adrese 5 yazar. `int *p = 5;` ise 5 sayısını bir **adres** olarak `p`'ye koymaya çalışır; clang bunu `incompatible integer to pointer conversion` ile reddeder (ve yapabilseydi, `*p` 5 numaralı byte'a giderdi; Bölüm 4'teki `NULL` gibi çöken bir adres). Doğrusu, önce pointer'ın gösterebileceği bir yer yaratmak:

```c
int value;
int *p = &value;
*p = 5;
```

Bir pointer'ın kendisi bir şey tutmaz; sadece bir şeyin **nerede** olduğunu tutar. Gösterecek bir şey olmadan pointer'ın bir anlamı yok.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.1: pointer'lar ve adresler.
- C standardı (ISO/IEC 9899:2018), §6.5.3.2: `&` ve `*`; §6.3.2.3: `NULL` ve pointer dönüşümleri; §6.5¶7: bir nesneye hangi tiplerle erişilebileceği (strict aliasing ve `char` istisnası).
- Kenneth Reek, *Pointers on C* (1997), Bölüm 6.
- Tony Hoare, "Null References: The Billion Dollar Mistake", QCon London, 2009.

**Sıradaki ders:** Pointer aritmetiği. `p + 1` neden bir sonraki byte'ı değil bir sonraki **elemanı** gösteriyor, ve `a[i]` aslında ne demek?
