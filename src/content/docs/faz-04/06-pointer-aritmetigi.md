---
title: "4.6 Pointer aritmetiği"
description: "p + 1'in bir byte değil bir eleman ilerlemesi, a[i]'nin aslında *(a + i) olması ve bu yüzden i[a]'nın da çalışması, array'i pointer ile gezmek, iki pointer'ın farkı ve ptrdiff_t, array'in bir sonrasını gösteren pointer, *p++ ile (*p)++ farkı, ve array ile pointer'ın gerçekte nerede ayrıldığı."
---

Ders 4.5'te bir `unsigned char *` ile bir sayının byte'larını `bytes[0]`, `bytes[1]` diye okuduk; pointer'ı bir array gibi kullandık ve "sebebini Ders 4.6'da göreceğiz" dedik. Ders 3.17'de de `strtol`'un bitiş yerini `end - text` diye bulmuştuk: iki adresi birbirinden çıkarmıştık. Bu derste adreslerle yapılan aritmetiğe bakıyoruz; ve C'deki array erişiminin aslında tamamen bu aritmetikten ibaret olduğunu göreceğiz.

---

## 1. p + 1

Bir pointer'a 1 eklemek ne yapar? Adresi bir byte ilerletmesini bekleyebilirsin; öyle değil:

```c
char c[4] = "abc";
int n[4] = {10, 20, 30, 40};
double d[4] = {0.5, 1.5, 2.5, 3.5};

char *cp = c;
int *ip = n;
double *dp = d;
printf("cp %p, cp + 1 %p\n", (void *)cp, (void *)(cp + 1));
printf("ip %p, ip + 1 %p, ip + 3 %p\n", (void *)ip, (void *)(ip + 1), (void *)(ip + 3));
printf("dp %p, dp + 1 %p\n", (void *)dp, (void *)(dp + 1));
```

```
cp 0x16d672124, cp + 1 0x16d672125
ip 0x16d672160, ip + 1 0x16d672164, ip + 3 0x16d67216c
dp 0x16d672140, dp + 1 0x16d672148
```

`char *`'a 1 eklemek adresi 1 byte, `int *`'a eklemek **4 byte**, `double *`'a eklemek **8 byte** ilerletiyor. `ip + 3`, 12 byte sonrası. Kural:

> `p + k`, `p`'nin gösterdiği tipten `k` **eleman** sonrasının adresi: adres olarak p + k × sizeof(*p).

Ders 4.1'deki adres formülünün aynısı. `p + 1`, "bir sonraki byte" değil, "bir sonraki **eleman**". Ders 4.5'te pointer'ın tipinin `*p`'nin kaç byte okuyacağını belirlediğini görmüştük; aritmetikte kaç byte atlanacağını da o belirliyor. Ve bu sayede, pointer aritmetiği yazarken eleman boyutlarını hiç düşünmek zorunda kalmıyoruz.

Ders 4.4'teki bir soruyu da cevaplıyor: `&scores` ile `&scores[0]` aynı adres ama farklı tip. `&scores[0] + 1` 4 byte sonrası; `&scores + 1` ise, `&scores` "5 elemanlı bir array'in adresi" olduğu için, **20 byte** sonrası: bütün array'in arkası. Ölçtük; ikisi de öyle.

---

## 2. a[i] aslında *(a + i)

Ders 4.1'de bir array'in adının ilk elemanının adresine dönüştüğünü gördük. Bölüm 1'deki kurala göre `n + 2`, ilk elemandan iki eleman sonrasının, yani `n[2]`'nin adresi. O halde `*(n + 2)`, `n[2]`'nin kendisi.

Bu bir benzerlik değil, **tanım**. C standardı köşeli parantezi böyle tanımlıyor:

> `a[i]`, `*(a + i)` demektir.

```c
printf("%d %d %d %d\n", n[2], *(n + 2), *(2 + n), 2[n]);
```

```
30 30 30 30
```

Dördü de aynı. Toplama değişmeli olduğu için `*(n + 2)` ile `*(2 + n)` aynı; ve tanım gereği `*(2 + n)`, `2[n]` demek. `2[n]` derlenip çalışıyor! `1["abc"]` da `'b'`. Bunlar gerçek kodda hiç kullanılmaz; ama C'deki `[]`'nin "array'e erişmek" değil "bir adrese eklemek ve oraya gitmek" olduğunu çok açık gösteriyor.

Bu tanımdan üç sonuç çıkıyor:

- **Pointer'lar `[]` ile kullanılabilir.** Ders 4.5'teki `bytes[i]`, `*(bytes + i)` demek. Ders 4.1'deki fonksiyon parametresi `int numbers[]` da aslında `int *numbers`; `numbers[i]` aynı hesabı yapıyor.
- **İndeksler 0'dan başlıyor**, çünkü ilk eleman `a + 0`'da.
- **C sınırı kontrol edemiyor**, çünkü `a[i]` sadece bir toplama ve bir bellek erişimi; toplamada array'in boyutu hiç yok.

---

## 3. Array'i pointer ile gezmek

Ders 4.2'deki `sum`'ı indeks yerine bir pointer ile yazalım:

```c
int sum_pointer(const int *a, int n) {
    int total = 0;
    for (const int *p = a; p < a + n; p++) {
        total += *p;
    }
    return total;
}
```

- `const int *a`: "değiştirmeyeceğim `int`'leri gösteren pointer". `const int a[]` ile aynı anlam; ayrıntısı Ders 4.8'de.
- `p` başta ilk elemanı gösteriyor; her turda `p++` ile bir **eleman** ilerliyor.
- `a + n`: son elemanın **bir sonrası**. Döngü, `p` oraya ulaşınca bitiyor.

`p++`'nın `p = p + 1` olduğunu Ders 2.3'ten biliyoruz; burada "bir sonraki elemana geç" demek.

### Hangisi daha hızlı?

Eski C kitaplarında pointer'lı döngünün daha hızlı olduğu yazar: her turda `a + i × 4` hesaplamak yerine `p`'ye 4 eklemek. Ders 4.2'deki indeksli `sum` ile karşılaştıralım; godbolt, **armv8-a clang**, `-O1`. İki fonksiyonun döngü gövdeleri:

```asm
sum_index:                          sum_pointer:
        ...                                 ...
.LBB0_2:                            .LBB1_2:
        ldr     w10, [x8], #4               ldr     w10, [x0], #4
        subs    x9, x9, #1                  cmp     x0, x9
        add     w0, w10, w0                 add     w8, w10, w8
        b.ne    .LBB0_2                     b.lo    .LBB1_2
```

**Aynı.** `ldr w10, [x8], #4`, "x8'deki adresten 4 byte oku, sonra x8'e 4 ekle"; yani `*p++`. Compiler, indeksli döngüyü de kendisi pointer'lı hale getirmiş. 1970'lerin compiler'larında bu fark önemliydi; bugün değil. Hangisi daha okunaklıysa onu yaz: çoğu zaman indeks.

---

## 4. İki pointer'ın farkı

Bir pointer'a bir tamsayı eklenebiliyorsa, aynı array'in içindeki iki pointer'ın farkı da alınabilir; sonuç **aralarındaki eleman sayısı**:

```c
#include <stddef.h>

ptrdiff_t diff = &n[3] - &n[0];
printf("%td\n", diff);
printf("%td\n", &n[0] - &n[3]);
```

```
3
-3
```

Adresler 12 byte uzakta, ama fark 12 değil **3**: pointer aritmetiği her zaman eleman cinsinden. İkisini byte cinsinden görmek istersen önce `char *`'a çevir: `(char *)&n[3] - (char *)&n[0]` 12.

Sonucun tipi Ders 3.4'te tanıştığımız **`ptrdiff_t`**: işaretli, çünkü fark negatif olabilir. Yazdırmak için `%td`. Ders 3.17'de `strtol`'un `end`'inin, yazının kaçıncı karakterinde durduğunu `end - text` ile bulmuştuk: iki `char *`'ın farkı, yani aradaki karakter sayısı.

Bu bize pointer'larla array işlemenin ikinci yaygın kalıbını veriyor: bir **başlangıç** ve bir **bitiş** pointer'ı. Ders 4.2'deki `find`'ı, bulduğu elemanın **adresini** döndürecek şekilde yazalım:

```c
const int *find_pointer(const int *begin, const int *end, int value) {
    for (const int *p = begin; p < end; p++) {
        if (*p == value) {
            return p;
        }
    }
    return NULL;
}
```

Bulunamazsa −1 yerine Ders 4.5'teki `NULL`. Bulunduysa, indeks istiyorsan `result - begin`. Ders 4.17'deki `strchr` ve C++'ın standart kütüphanesindeki bütün algoritmalar bu biçimde çalışır.

---

## 5. Kurallar

Pointer aritmetiği güçlü, ama standart onu sadece belirli durumlarda tanımlıyor.

**Bir sonrası serbest, ötesi değil.** Bir pointer, bir array'in elemanlarından birini ya da **son elemanın bir sonrasını** gösterebilir. `a + n` geçerli bir adres; Bölüm 3'teki döngü onu karşılaştırmada kullanıyor. Ama `*(a + n)` geçersiz: orada bir eleman yok (Ders 4.1). `a + n + 1` ya da `a - 1`'i **hesaplamak** bile, hiç kullanmasan da, undefined behavior. `-fsanitize=undefined` bunu yakalayabiliyor:

```c
int a[4] = {1, 2, 3, 4};
int *q = a - 1;
```

```
runtime error: index -1 out of bounds for type 'int[4]'
```

Neden hesaplamak bile yasak? Bazı eski ve bazı gömülü sistemlerde bellek parçalara bölünmüş ve bir parçanın ötesini gösteren bir adres donanımda **var olamıyor**; standart bu sistemlerde de çalışabilmek istiyor. Döngüleri `p >= a` diye geriye doğru yazarken bu kurala dikkat (2. alıştırma).

**Fark ve karşılaştırma aynı array'de.** `p - q` ya da `p < q`, ikisi aynı array'i (ya da onun bir sonrasını) gösteriyorsa anlamlı. Farklı array'lerin adreslerini karşılaştırmak undefined behavior; Ders 4.4'te iki ayrı değişkenin bellekteki sırasının garanti olmadığını görmüştük.

**İki pointer toplanamaz.** `p + q` bir hata; bir adresi bir adresle toplamanın anlamı yok. Bir tamsayı eklenebilir, iki pointer birbirinden çıkarılabilir; o kadar.

### *p++, (*p)++, *++p

`++` ile `*`'ı birlikte kullanınca öncelik önemli. `int n[4] = {10, 20, 30, 40}` ve `int *p = n` için:

| İfade | Ne yapar? | Sonuç |
| --- | --- | --- |
| `v = *p++` | `*p`'yi oku, sonra **`p`'yi** ilerlet | `v` = 10, `p` artık `n[1]`'i gösteriyor, `n` değişmedi |
| `(*p)++` | **`*p`'yi** bir artır | `n[0]` = 11, `p` değişmedi |
| `w = *++p` | Önce `p`'yi ilerlet, sonra oku | `w` = 20 |

`*p++`, "oku ve bir sonrakine geç" demek; C'nin en çok kullanılan deyimlerinden biri. Ders 4.13'te `strlen`'i, Ders 4.14'te `strcpy`'yi bu deyimle yazacağız. Gösterilen değeri artırmak istiyorsan parantez şart.

---

## 6. Array ve pointer aynı şey mi?

Bu kadar benzerlikten sonra "array, aslında bir pointer" demek cazip. Değil. Ders 4.1'deki istisnalarda ayrılıyorlar:

| | `int a[5]` | `int *p = a` |
| --- | --- | --- |
| `sizeof` | 20: bütün array | 8: bir adres |
| `&` | `&a`: "5 elemanlı array'in adresi" | `&p`: "pointer'ın kendi adresi" (`int **`) |
| Atama | `a = …` hata (Ders 4.1) | `p = …` serbest, başka yeri gösterebilir |
| Bellekte | 5 `int`'lik yer | 8 byte'lık bir adres; elemanlar başka yerde |

Bir array, belleğin bir **parçası**; bir pointer, o parçanın **nerede** olduğunu tutan ayrı bir değişken. Bir ifadenin içinde array hemen ilk elemanının adresine dönüştüğü için çoğu zaman aynı şekilde kullanılıyorlar. Ders 4.12'de string'lerle `char s[] = "abc"` ile `char *s = "abc"`'in neden çok farklı şeyler olduğunu gördüğümüzde bu ayrım önem kazanacak.

---

## Alıştırmalar

**1** – `short s[10]`, `s` `0x2000`'de başlıyor. `s + 4`, `&s[9] - &s[2]`, `(char *)&s[9] - (char *)&s[2]` ve `&s + 1`'in değerleri ne?

**2** – Bu, bir array'i tersten yazdırmaya çalışan bir döngü:

```c
for (int *p = a + n - 1; p >= a; p--) {
    printf("%d ", *p);
}
```

Çalışıyor gibi görünüyor. Bölüm 5'teki kurala göre neden yanlış? Kuralı bozmayan bir hali yaz.

**3** – Ders 4.2'deki `reverse`'ü iki pointer ile yaz: `void reverse_pointer(int *begin, int *end)`; `begin` ilk elemanı, `end` son elemanın bir sonrasını göstersin.

**4** – Bölüm 4'teki `find_pointer`'ı kullanarak bir array'de bir değerin **kaç kez** geçtiğini sayan bir döngü yaz. (İpucu: her bulduğunda, bir sonraki aramaya bulduğun yerin bir sonrasından başla.)

**5** – `int a[3][4]` iki boyutlu bir array. `a + 1` ile `&a[0][0] + 1` aynı adres mi? Kaç byte farklı? (Ders 4.3'teki "array'lerin array'i" fikrini kullan.)

<details>
<summary>Cevaplar</summary>

**1** – `short` 2 byte.

- `s + 4` = `0x2000 + 4 × 2` = **`0x2008`**.
- `&s[9] - &s[2]` = **7** (eleman cinsinden, `ptrdiff_t`).
- `(char *)&s[9] - (char *)&s[2]` = **14** (byte cinsinden).
- `&s + 1` = `0x2000 + sizeof(s)` = `0x2000 + 20` = **`0x2014`**: bütün array'in arkası.

**2** – Son turda `p`, `a`'yı gösteriyor ve `p--` onu `a - 1` yapıyor; sonra `p >= a` karşılaştırması bu geçersiz pointer'la yapılıyor. `a - 1`'i hesaplamak bile undefined behavior. Pratikte çoğu makinede çalışır, ama compiler bu hesabın hiç yapılmayacağını varsayıp döngüyü değiştirmekte serbest. Kuralı bozmayan hali, pointer'ı **önce** azaltmak:

```c
for (int *p = a + n; p > a; ) {
    p--;
    printf("%d ", *p);
}
```

`p` hiçbir zaman `a`'nın altına inmiyor; en düşük değeri `a`. Ders 4.1'deki 5. alıştırmanın işaretsiz döngüsüyle aynı fikir: azaltmadan önce karşılaştır.

**3** –

```c
void reverse_pointer(int *begin, int *end) {
    while (begin < end) {
        end--;
        int tmp = *begin;
        *begin = *end;
        *end = tmp;
        begin++;
    }
}
```

`end` başta bir sonrasını gösterdiği için önce azaltılıyor. Çağrı: `reverse_pointer(a, a + n)`. Boş array için `begin == end` ve döngü hiç dönmüyor. `end--`, `end` `begin`'den büyükken yapıldığı için hiçbir zaman array'in başının altına inmiyor.

**4** –

```c
int count = 0;
const int *p = find_pointer(a, a + n, value);
while (p != NULL) {
    count++;
    p = find_pointer(p + 1, a + n, value);
}
```

`p + 1` en kötü ihtimalle `a + n`, yani bir sonrası; geçerli, ve `find_pointer` o durumda hiç dönmeden `NULL` döndürüyor.

**5** – Aynı adres değil. `a`, her elemanı `int[4]` olan bir array; ilk elemanının adresine dönüşünce tipi "4 elemanlı bir `int` array'inin adresi" oluyor. `a + 1` bir **satır** atlıyor: 4 × 4 = **16 byte**, yani `&a[1][0]`. `&a[0][0]` ise bir `int *`; `+ 1` sadece **4 byte**: `&a[0][1]`. Fark 12 byte. Ders 4.3'teki adres formülü, iki boyutlu bir array'de `a[i][j]`'nin `*(*(a + i) + j)` demek olmasından geliyor: önce `i` satır, sonra `j` eleman.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.3–5.4: pointer'lar ve array'ler, adres aritmetiği.
- C standardı (ISO/IEC 9899:2018), §6.5.2.1: `E1[E2]`'nin `(*((E1)+(E2)))` olarak tanımı; §6.5.6¶8–9: pointer'a tamsayı eklemek, bir sonrasını gösteren pointer ve iki pointer'ın farkı; §6.5.8¶5: pointer karşılaştırması.
- Peter van der Linden, *Expert C Programming: Deep C Secrets* (1994), Bölüm 4: "The Shocking Truth: C Arrays and Pointers Are NOT the Same!"

**Sıradaki ders:** Pointer ile fonksiyona aktarım. İki değişkenin yerini değiştiren `swap`, ve bir fonksiyondan birden fazla sonuç döndürmek.
