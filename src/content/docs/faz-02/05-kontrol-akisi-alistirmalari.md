---
title: "2.5 Kontrol akışı alıştırmaları"
description: "On klasik problem: FizzBuzz, artık yıl, ters çevirme, palindrom, asal, mükemmel ve Armstrong sayıları, Fibonacci, Collatz ve ikilik gösterim. Önce süre tutup kendin çöz, sonra çözüm ve trace table."
---

Bu derste yeni bir şey öğretmiyoruz. Ders 2.3 ve 2.4'te öğrendiğin araçlarla on problem çözeceksin. Problemler kolaydan zora sıralı.

**Nasıl çalışmalısın?**

1. Problemi oku ve yanındaki **süreyi** başlat. Telefonun saati yeter.
2. Kod yazmadan önce, Faz 1'deki gibi kağıtta düşün: girdi ne, çıktı ne, hangi döngü, hangi karar? Küçük bir örneği elle çöz.
3. Kodu yaz ve çalıştır. Verilen örneklerle karşılaştır.
4. Süre dolduysa ve takıldıysan, önce **İpucu** kutusunu aç. Çözümü değil.
5. Ancak ipucuyla da ilerleyemezsen **Çözüm**'e bak. Çözümü okuduktan sonra kapat ve kodu **kendin, bakmadan** yeniden yaz.
6. Çözdüysen de çözüme bak: başka bir yol bulmuş olabilirsin, ya da çözümdeki trace table senin kaçırdığın bir edge case'i gösterebilir.

Süreler bir yarış değil, bir pusula. Bir problemde süreyi aşmak normal; önemli olan, kendin uğraşmadan çözüme bakmamak.

:::tip[Trace table'ı kullan]
Kodun beklediğin sonucu vermiyorsa, Ders 1.3'teki gibi küçük bir girdiyle trace table çıkar. Değişkenleri her turda kağıda yaz; hata çoğu zaman ikinci ya da üçüncü satırda kendini gösterir. Her çözümde de bir trace table bulacaksın.
:::

---

## 1. FizzBuzz

**Süre: 10 dakika**

1'den 15'e kadar sayıları alt alta yazdır. Ama:

- 3'e bölünen sayılar yerine `Fizz`,
- 5'e bölünen sayılar yerine `Buzz`,
- hem 3'e hem 5'e bölünen sayılar yerine `FizzBuzz` yaz.

```
1
2
Fizz
4
Buzz
Fizz
7
8
Fizz
Buzz
11
Fizz
13
14
FizzBuzz
```

Basit görünüyor, ama iş görüşmelerinde bu soruyu çözemeyen çok sayıda aday olduğu bilinir. Tuzağı bulabilecek misin?

<details>
<summary>İpucu</summary>

Kararların **sırası** önemli. 15 hem 3'e hem 5'e bölünür. Önce "3'e bölünüyor mu?" diye sorarsan ne olur? Ders 2.3'teki "ilk doğru olan kazanır" kuralını hatırla.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int main(void) {
    for (int i = 1; i <= 15; i++) {
        if (i % 15 == 0) {
            printf("FizzBuzz\n");
        } else if (i % 3 == 0) {
            printf("Fizz\n");
        } else if (i % 5 == 0) {
            printf("Buzz\n");
        } else {
            printf("%d\n", i);
        }
    }
    return 0;
}
```

**Tuzak:** En özel durum (hem 3 hem 5) **en başta** sorulmalı. Sıra ters olsaydı 15, ilk karar olan "3'e bölünüyor mu?"ya takılır, `Fizz` yazılır ve zincir biterdi. Hem 3'e hem 5'e bölünmek, 15'e bölünmekle aynı şeydir; bu yüzden `i % 15 == 0` yeterli.

| `i` | `i % 15 == 0`? | `i % 3 == 0`? | `i % 5 == 0`? | Yazılan |
| --- | --- | --- | --- | --- |
| 3 | hayır | **evet** | — | Fizz |
| 5 | hayır | hayır | **evet** | Buzz |
| 7 | hayır | hayır | hayır | 7 |
| 15 | **evet** | — | — | FizzBuzz |

`—`: o karara hiç gelinmedi.

</details>

---

## 2. Artık yıl

**Süre: 10 dakika**

Bir yılın artık yıl olup olmadığını döndüren `int is_leap(int year)` fonksiyonunu yaz. Kural (Ders 1.1, Alıştırma 3.2):

- 4'e bölünen yıllar artık yıldır,
- ama 100'e bölünüp 400'e bölünmeyenler artık yıl **değildir**.

2024, 2023, 1900 ve 2000 için dene:

```
2024: artık yıl
2023: artık yıl değil
1900: artık yıl değil
2000: artık yıl
```

<details>
<summary>İpucu</summary>

Kuraldaki istisnalar, genel kuraldan daha özeldir. FizzBuzz'daki gibi: en özel durumu (400) en başta, en genel durumu (4) en sonda sor.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int is_leap(int year) {
    if (year % 400 == 0) {
        return 1;
    }
    if (year % 100 == 0) {
        return 0;
    }
    return year % 4 == 0;
}

int main(void) {
    int years[] = {2024, 2023, 1900, 2000};
    for (int i = 0; i < 4; i++) {
        printf("%d: %s\n", years[i], is_leap(years[i]) ? "artık yıl" : "artık yıl değil");
    }
    return 0;
}
```

Her `return` fonksiyondan çıktığı için `else` yazmaya gerek kalmadı: ilk karar tutmazsa zaten ikinciye geçilir.

| `year` | `% 400 == 0`? | `% 100 == 0`? | `% 4 == 0`? | Sonuç |
| --- | --- | --- | --- | --- |
| 2024 | hayır | hayır | evet | artık yıl |
| 2023 | hayır | hayır | hayır | değil |
| 1900 | hayır | **evet** | — | değil |
| 2000 | **evet** | — | — | artık yıl |

1900 ve 2000 bu problemin edge case'leri: sadece "4'e bölünüyor mu?" diye soran bir program ikisine de "artık yıl" der ve 1900'de yanılır.

</details>

---

## 3. Sayıyı ters çevirme

**Süre: 15 dakika**

Bir sayının basamaklarını ters çeviren `int reverse(int n)` fonksiyonunu yaz.

```
reverse(1234) → 4321
reverse(1200) → 21
reverse(7)    → 7
```

<details>
<summary>İpucu</summary>

İki şeyi biliyorsun: `n % 10` sayının **son** basamağını verir, `n / 10` son basamağı atar (Ders 1.1'deki BasamakSayısı). Yeni sayıyı nasıl kurarsın? 43'ün sonuna 2 eklemek için: 43 × 10 + 2 = 432.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int reverse(int n) {
    int result = 0;
    while (n > 0) {
        int digit = n % 10;
        result = result * 10 + digit;
        n = n / 10;
    }
    return result;
}

int main(void) {
    printf("%d\n", reverse(1234));
    printf("%d\n", reverse(1200));
    printf("%d\n", reverse(7));
    return 0;
}
```

Her turda `n`'nin son basamağını kopar, `result`'ın sonuna ekle.

| Tur | `n` | `digit` | `result` | yeni `n` |
| --- | --- | --- | --- | --- |
| 1. | 1234 | 4 | 4 | 123 |
| 2. | 123 | 3 | 43 | 12 |
| 3. | 12 | 2 | 432 | 1 |
| 4. | 1 | 1 | 4321 | 0 |

**Edge case:** 1200'ün tersi 0021 olmalı, ama bir tamsayının başında sıfır olmaz: sonuç 21. Bu bir hata değil, sayıların doğası. Sıfırları korumak gerekseydi sayıyı rakam rakam yazdırmamız gerekirdi.

</details>

---

## 4. Palindrom sayı

**Süre: 10 dakika**

Tersten okunuşu kendisiyle aynı olan sayılara **palindrom** denir: 12321, 1221, 7. Bir sayının palindrom olup olmadığını döndüren `int is_palindrome(int n)` fonksiyonunu yaz.

```
12321: palindrom
1221: palindrom
1234: palindrom değil
7: palindrom
```

<details>
<summary>İpucu</summary>

Bir önceki problemde yazdığın fonksiyonu kullanabilir misin?

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int reverse(int n) {
    int result = 0;
    while (n > 0) {
        result = result * 10 + n % 10;
        n = n / 10;
    }
    return result;
}

int is_palindrome(int n) {
    return n == reverse(n);
}

int main(void) {
    int numbers[] = {12321, 1221, 1234, 7};
    for (int i = 0; i < 4; i++) {
        printf("%d: %s\n", numbers[i], is_palindrome(numbers[i]) ? "palindrom" : "palindrom değil");
    }
    return 0;
}
```

Bütün iş tek satır: bir sayı, tersine eşitse palindromdur. Bir önceki problemde yazdığın fonksiyon burada hazır bir yapı taşı oldu. Fonksiyon yazmanın asıl kazancı bu: bir kez çöz, her yerde kullan.

| `n` | `reverse(n)` | Eşit mi? |
| --- | --- | --- |
| 12321 | 12321 | evet |
| 1234 | 4321 | hayır |

Problem 3'teki edge case burada işe yarıyor: 10'un tersi 1'dir, 10 ≠ 1, yani 10 palindrom değil. Doğru.

</details>

---

## 5. Asal sayılar

**Süre: 15 dakika**

1'den 100'e kadar olan asal sayıları yazdır ve kaç tane olduğunu söyle.

```
2 3 5 7 11 13 17 19 23 29 31 37 41 43 47 53 59 61 67 71 73 79 83 89 97 
Toplam: 25 asal
```

<details>
<summary>İpucu</summary>

Bir sayının asal olup olmadığını bulmayı Ders 1.3'te tasarladın, Ders 2.3'te de fonksiyon olarak yazdın. Önce o fonksiyonu yaz, sonra 1'den 100'e kadar her sayı için çağır.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int is_prime(int n) {
    if (n < 2) {
        return 0;
    }
    for (int d = 2; d * d <= n; d++) {
        if (n % d == 0) {
            return 0;
        }
    }
    return 1;
}

int main(void) {
    int count = 0;
    for (int i = 1; i <= 100; i++) {
        if (is_prime(i)) {
            printf("%d ", i);
            count++;
        }
    }
    printf("\nToplam: %d asal\n", count);
    return 0;
}
```

`is_prime(15)` için iz:

| Adım | `d` | `d * d <= 15`? | `15 % d` | Sonuç |
| --- | --- | --- | --- | --- |
| 1. | 2 | 4, evet | 1 | devam |
| 2. | 3 | 9, evet | **0** | asal değil |

Neden `d * d <= n`? Ders 1.3'te gördük: bir sayının bir böleni varsa, karekökünden küçük ya da ona eşit bir böleni mutlaka vardır. 97'yi test etmek için 95 değil, sadece 8 sayı denememiz yetiyor.

**Edge case:** 1 asal değildir; fonksiyonun başındaki `n < 2` kontrolü bu yüzden var. Onu silersen döngü 1 için hiç çalışmaz ve fonksiyon 1'e "asal" der.

</details>

---

## 6. Mükemmel sayılar

**Süre: 20 dakika**

Kendisi hariç bütün bölenlerinin toplamı kendisine eşit olan sayılara **mükemmel sayı** denir. 6'nın bölenleri 1, 2 ve 3'tür; 1 + 2 + 3 = 6. 10.000'e kadar olan mükemmel sayıları bul.

```
6
28
496
8128
```

Sadece dört tane! Mükemmel sayılar o kadar seyrektir ki bugüne kadar bilinenlerin sayısı elliyi biraz geçer.

<details>
<summary>İpucu</summary>

Problemi ikiye böl. Önce bir sayının kendisi hariç bölenlerinin toplamını veren `int divisor_sum(int n)` fonksiyonunu yaz ve 6 ile 28 için dene. Sonra 2'den 10.000'e kadar her sayı için bu fonksiyonu çağır.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int divisor_sum(int n) {
    int sum = 0;
    for (int d = 1; d < n; d++) {
        if (n % d == 0) {
            sum += d;
        }
    }
    return sum;
}

int main(void) {
    for (int n = 2; n <= 10000; n++) {
        if (divisor_sum(n) == n) {
            printf("%d\n", n);
        }
    }
    return 0;
}
```

`divisor_sum(28)` için yalnızca bölen olan `d` değerleri:

| `d` | `28 % d` | `sum` |
| --- | --- | --- |
| 1 | 0 | 1 |
| 2 | 0 | 3 |
| 4 | 0 | 7 |
| 7 | 0 | 14 |
| 14 | 0 | 28 |

`d < n`: sayının kendisi toplama katılmıyor; `<=` yazsaydın her sayının toplamı kendisinden büyük çıkar ve hiç mükemmel sayı bulamazdın.

Program biraz bekletebilir: 10.000 sayının her biri için neredeyse kendisi kadar bölme yapılıyor, toplamda yaklaşık 50 milyon işlem. Bölenleri bulmayı Problem 5'teki gibi kareköke kadar sınırlamak mümkün; ama önce **doğru** çalışan programı yaz, hızlandırmayı sonra düşün. Ders 2.4'teki labirentte de böyle yapmıştık.

</details>

---

## 7. Armstrong sayıları

**Süre: 20 dakika**

Üç basamaklı bir sayı, basamaklarının küplerinin toplamına eşitse ona **Armstrong sayısı** denir:

153 = 1³ + 5³ + 3³ = 1 + 125 + 27

100 ile 999 arasındaki bütün Armstrong sayılarını bul.

```
153
370
371
407
```

<details>
<summary>İpucu</summary>

Üç basamaklı bir sayıyı basamaklarına ayırmayı Ders 2.3'teki saniye çevirme örneğinde gördün. 153 için: yüzler basamağı 153 / 100 = 1, birler basamağı 153 % 10 = 3. Onlar basamağı?

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int main(void) {
    for (int n = 100; n <= 999; n++) {
        int hundreds = n / 100;
        int tens = (n / 10) % 10;
        int ones = n % 10;
        int sum = hundreds * hundreds * hundreds
                + tens * tens * tens
                + ones * ones * ones;
        if (sum == n) {
            printf("%d\n", n);
        }
    }
    return 0;
}
```

Onlar basamağı için önce birler basamağını at (`n / 10`, 153 → 15), sonra kalanın son basamağını al (`% 10`, 15 → 5).

| `n` | `hundreds` | `tens` | `ones` | `sum` | Eşit mi? |
| --- | --- | --- | --- | --- | --- |
| 152 | 1 | 5 | 2 | 1 + 125 + 8 = 134 | hayır |
| 153 | 1 | 5 | 3 | 1 + 125 + 27 = 153 | **evet** |
| 370 | 3 | 7 | 0 | 27 + 343 + 0 = 370 | **evet** |

Uzun bir ifadeyi birkaç satıra bölmek serbesttir: C, ifadenin noktalı virgüle kadar sürdüğünü bilir. `sum` satırı okunaklı olsun diye üçe bölündü.

</details>

---

## 8. Fibonacci

**Süre: 15 dakika**

Fibonacci dizisinde her sayı, kendisinden önceki iki sayının toplamıdır: 1, 1, 2, 3, 5, 8, 13… Dizinin ilk 15 terimini yazdır.

```
1 1 2 3 5 8 13 21 34 55 89 144 233 377 610 
```

<details>
<summary>İpucu</summary>

Her adımda sadece **son iki** terimi bilmen yeterli. İki değişken tut: `previous` ve `current`. Bir sonraki terimi hesapladıktan sonra ikisini de bir adım kaydırman gerekiyor. Hangi sırayla güncellemelisin? Bir değeri ezmeden önce ona ihtiyacın var mı?

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int main(void) {
    int count = 15;
    int previous = 0;
    int current = 1;

    for (int i = 1; i <= count; i++) {
        printf("%d ", current);
        int next = previous + current;
        previous = current;
        current = next;
    }
    printf("\n");
    return 0;
}
```

| `i` | Yazılan | `next` | yeni `previous` | yeni `current` |
| --- | --- | --- | --- | --- |
| 1 | 1 | 0 + 1 = 1 | 1 | 1 |
| 2 | 1 | 1 + 1 = 2 | 1 | 2 |
| 3 | 2 | 1 + 2 = 3 | 2 | 3 |
| 4 | 3 | 2 + 3 = 5 | 3 | 5 |

**Sıra tuzağı:** `next`'i hesaplamadan `previous = current;` yazsaydın, eski `previous` değeri kaybolurdu ve toplam yanlış çıkardı. Ders 2.4'teki yer değiştirme alıştırmasındaki `temp` gibi, burada da `next` bir değeri ezmeden önce saklamaya yarıyor.

</details>

---

## 9. Collatz dizisi

**Süre: 20 dakika**

Bir sayıdan başla:

- Çiftse 2'ye böl,
- tekse 3 ile çarpıp 1 ekle.

1'e ulaşana kadar devam et. 6'dan başlayan diziyi yazdır; kaç adımda 1'e ulaştığını ve yol boyunca ulaşılan en yüksek sayıyı söyle.

```
6 -> 3 -> 10 -> 5 -> 16 -> 8 -> 4 -> 2 -> 1
Adım: 8, en yüksek: 16
```

Bu kuralın **her** pozitif tamsayı için sonunda 1'e ulaşıp ulaşmadığı bilinmiyor. 1937'de Lothar Collatz tarafından ortaya atılan bu soru, matematiğin en ünlü çözülmemiş problemlerinden biri. Bilgisayarlar çok büyük sayılara kadar denedi; hepsi 1'e ulaştı, ama kimse bunun her sayı için doğru olduğunu ispatlayamadı.

<details>
<summary>İpucu</summary>

Kaç adım süreceğini bilmiyorsun; bu bir `for` değil, `while` problemi (Ders 2.3). Koşul: `n` 1 olmadığı sürece. En yüksek değeri bulmak, Ders 2.4'teki "en yüksek not"un aynısı.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

int main(void) {
    int n = 6;
    int steps = 0;
    int highest = n;

    printf("%d", n);
    while (n != 1) {
        if (n % 2 == 0) {
            n = n / 2;
        } else {
            n = 3 * n + 1;
        }
        printf(" -> %d", n);
        steps++;
        if (n > highest) {
            highest = n;
        }
    }
    printf("\nAdım: %d, en yüksek: %d\n", steps, highest);
    return 0;
}
```

| Adım | `n` | Çift mi? | yeni `n` | `highest` |
| --- | --- | --- | --- | --- |
| 1. | 6 | evet | 3 | 6 |
| 2. | 3 | hayır | 10 | 10 |
| 3. | 10 | evet | 5 | 10 |
| 4. | 5 | hayır | 16 | 16 |
| 5. | 16 | evet | 8 | 16 |
| 6. | 8 | evet | 4 | 16 |
| 7. | 4 | evet | 2 | 16 |
| 8. | 2 | evet | 1 | 16 |

`n`'yi 27 yap ve dene: 27 gibi küçük bir sayı **111 adım** sürüyor ve yolda **9232**'ye kadar çıkıyor. Bu dizinin bu kadar şaşırtıcı olmasının sebebi bu.

Ders 1.1'deki **sonluluk** özelliğini hatırla: bir algoritma mutlaka bitmelidir. Bu döngü her sayı için bitiyor mu? Kimse bilmiyor. Bir döngünün biteceğinden emin olmanın her zaman kolay olmadığının güzel bir örneği.

</details>

---

## 10. Onluktan ikiliğe

**Süre: 25 dakika**

Bir sayının ikilik gösterimini yazdıran `void print_binary(int n)` fonksiyonunu yaz. **Array kullanma.**

```
print_binary(13)  → 1101
print_binary(156) → 10011100
print_binary(0)   → 0
print_binary(1)   → 1
```

Faz 0'daki bölme–kalan yöntemi bitleri **sağdan sola** üretiyordu: önce son bit, en sonda ilk bit. Ama ekrana soldan sağa yazmak zorundayız. Array kullanmadan bu sorunu nasıl çözersin?

<details>
<summary>İpucu</summary>

Faz 0'daki **ikinci** yöntemi hatırla: 156 = 128 + 16 + 8 + 4. Önce sayıdan küçük ya da ona eşit olan en büyük 2'nin kuvvetini bul (156 için 128). Sonra bu kuvvetten başlayıp her adımda yarıya inerek "bu kuvvet sayıya sığıyor mu?" diye sor. Sığıyorsa `1` yaz ve sayıdan çıkar; sığmıyorsa `0` yaz. Bu yöntem bitleri soldan sağa üretir.

</details>

<details>
<summary>Çözüm</summary>

```c
#include <stdio.h>

void print_binary(int n) {
    if (n == 0) {
        printf("0\n");
        return;
    }
    int power = 1;
    while (power * 2 <= n) {
        power = power * 2;
    }
    while (power > 0) {
        if (n >= power) {
            printf("1");
            n = n - power;
        } else {
            printf("0");
        }
        power = power / 2;
    }
    printf("\n");
}

int main(void) {
    print_binary(13);
    print_binary(156);
    print_binary(0);
    print_binary(1);
    return 0;
}
```

İki döngü var: ilki doğru 2'nin kuvvetini **bulur**, ikincisi o kuvvetten aşağı doğru bitleri **yazar**.

`print_binary(13)`: ilk döngü `power`'ı 1 → 2 → 4 → 8 yapar (16 > 13 olduğu için durur). İkinci döngü:

| Adım | `power` | `n >= power`? | Yazılan | yeni `n` |
| --- | --- | --- | --- | --- |
| 1. | 8 | 13 ≥ 8 evet | 1 | 5 |
| 2. | 4 | 5 ≥ 4 evet | 1 | 1 |
| 3. | 2 | 1 ≥ 2 hayır | 0 | 1 |
| 4. | 1 | 1 ≥ 1 evet | 1 | 0 |

Sonuç: **1101**. `power` 1'den sonra 1 / 2 = 0 olur ve döngü biter.

**Edge case:** 0 için ilk döngü hiç çalışmaz, `power` 1 kalır, ikinci döngü 0 ≥ 1 sorusuna "hayır" deyip `0` yazar. Bu durumda zaten doğru çalışıyor, ama fonksiyonun başında 0'ı ayrıca ele aldık: okuyan kişinin "0 için ne oluyor?" diye düşünmesine gerek kalmasın diye. Edge case'i açıkça yazmak, onu kodun içinde saklamaktan iyidir.

</details>

---

## Kendini değerlendir

On problemin kaçını ipucuna bakmadan çözdün?

- **8–10:** Kontrol akışı artık senin için doğal. Bir sonraki derse rahatça geçebilirsin.
- **5–7:** İyi gidiyorsun. Çözemediklerini birkaç gün sonra, çözüme bakmadan tekrar dene.
- **0–4:** Endişelenme; bu fazın en önemli dersi buydu ve tekrar gerektirir. Ders 2.3'ün alıştırmalarına dön, sonra bu problemleri baştan çöz. Ders 1.2'deki moral yazısını hatırla: herkes bu yoldan geçti.

## Kaynaklar

- K. N. King, *C Programming: A Modern Approach* (2. baskı), Bölüm 5–6: seçim ve döngü yapıları, programlama projeleri.
- Jeff Atwood, *Why Can't Programmers.. Program?* (2007): FizzBuzz'ın ünlü olma hikâyesi.
- Jeffrey Lagarias (ed.), *The Ultimate Challenge: The 3x+1 Problem* (2010): Collatz probleminin matematiği.

**Sıradaki ders:** LLDB ile hata ayıklama. Elle tuttuğun trace table'ı bilgisayara tutturmayı öğreneceğiz.
