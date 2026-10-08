---
title: "2.11 printf olmadan sayı yazdırma"
description: "putchar ile kendi print_int fonksiyonumuzu sıfırdan yazmak: rakamı karaktere çevirmek, recursion ile doğru sıra, negatif sayılar ve INT_MIN tuzağı."
---

Ders 2.2'den beri `printf`'i bir kara kutu olarak kullanıyoruz ve "önce kendin yaz" demiştik. Sıra geldi: bu derste ekrana bir sayı yazdıran fonksiyonu **sıfırdan** yazacağız.

Elimizde tek bir araç olacak: `putchar`. Ekrana **tek bir karakter** yazar. Hepsi bu. Bir sayıyı, örneğin 2026'yı, ekranda görmek için onu kendimiz `'2'`, `'0'`, `'2'`, `'6'` karakterlerine çevirip sırayla yazmak zorundayız.

---

## 1. Rakamı karaktere çevirmek

Faz 0'daki ASCII tablosunu hatırla: karakterler aslında sayıdır. `'0'` karakterinin sayısı 48, `'1'`'in 49, …, `'9'`'un 57. Rakam karakterleri tabloda **arka arkaya** dizilmiş durumda.

Bu yüzden 0 ile 9 arasındaki bir rakamı karaktere çevirmek tek bir toplama:

```c
#include <stdio.h>

int main(void) {
    int digit = 7;
    putchar('0' + digit);
    putchar('\n');
    return 0;
}
```

```
7
```

`'0' + 7` = 48 + 7 = 55, ve 55 tam olarak `'7'` karakterinin sayısı. `putchar('\n')` de satırı bitirir.

---

## 2. Bir sayının bütün rakamları

Bir sayının rakamlarını ayırmayı biliyoruz: `n % 10` son rakamı verir, `n / 10` son rakamı atar (Ders 1.1, 2.5). Ama rakamlar **sağdan sola** çıkıyor: 2026'dan önce 6, sonra 2, 0, 2. Ekrana ise soldan sağa yazmamız gerekiyor.

Bu sorunu Ders 2.8'de recursion ile çözmüştük: `print_in_order`, önce sayının geri kalanını yazdırıp kendi rakamını **en son** yazıyordu. Çıkarken yazdığı için sıra kendiliğinden düzeliyordu. Aynı fikir, `printf` yerine `putchar` ile:

```c
void print_int(int n) {
    if (n >= 10) {
        print_int(n / 10);
    }
    putchar('0' + n % 10);
}
```

`print_int(2026)` → önce `print_int(202)`, o da önce `print_int(20)`, o da önce `print_int(2)`. En dipteki `'2'`'yi yazar; sonra çıkarken `'0'`, `'2'`, `'6'` yazılır: **2026**.

`print_int(0)` da doğru çalışıyor: 0, 10'dan küçük olduğu için doğrudan `'0'` yazılır. Ders 1.1'deki BasamakSayısı'nın düştüğü 0 tuzağına bu fonksiyon düşmüyor.

---

## 3. Negatif sayılar

-45'i yazdırmak için akla gelen ilk yol: önce `'-'` yaz, sonra sayıyı pozitif yapıp devam et.

```c
#include <stdio.h>
#include <limits.h>

void print_int(int n) {
    if (n < 0) {
        putchar('-');
        n = -n;
    }
    if (n >= 10) {
        print_int(n / 10);
    }
    putchar('0' + n % 10);
}

int main(void) {
    print_int(2026);
    putchar('\n');
    print_int(0);
    putchar('\n');
    print_int(-45);
    putchar('\n');
    print_int(INT_MAX);
    putchar('\n');
    print_int(INT_MIN);
    putchar('\n');
    return 0;
}
```

`<limits.h>`, `int`'in alabileceği en büyük ve en küçük değeri iki isimle verir: `INT_MAX` (2.147.483.647) ve `INT_MIN` (-2.147.483.648). Programı çalıştıralım:

```
2026
0
-45
2147483647
-(
```

Son satır! `INT_MIN`'i yazdırması gerekirken `-(` yazdı. Ne oldu?

---

## 4. INT_MIN tuzağı

İki sınıra dikkatle bak:

- `INT_MAX` = **2.147.483.647**
- `INT_MIN` = **-2.147.483.648**

Negatif taraf bir fazla! (Bunun neden böyle olduğunu Faz 3'te, negatif sayıların bellekte nasıl tutulduğunu görünce anlayacağız.) Bu yüzden `-INT_MIN`, yani +2.147.483.648, bir `int`'e **sığmaz**. `n = -n;` satırı overflow olur.

Ders 2.10'da overflow'un sonucunun belirsiz olduğunu görmüştük; burada sonuç saçma bir sayı oldu ve `'0' + n % 10` ekrana `(` karakterini bastı. clang'in sanitizer'ı hatayı tam yerinde yakalıyor:

```sh
clang -std=c17 -fsanitize=undefined print.c -o print
```

```
print.c:7:13: runtime error: negation of -2147483648 cannot be represented in type 'int'
```

"-2147483648'in negatifi `int` ile gösterilemez."

**Çözüm: ters taraftan çalışmak.** Sorun, negatif sayıyı pozitife çevirmeye çalışmaktı. Pozitif tarafta yer yok ama negatif tarafta her zaman var: her pozitif `int`'in negatifi bir `int`'tir. O halde tersini yapalım ve **her sayıyı negatif tarafta** işleyelim:

```c
#include <stdio.h>
#include <limits.h>

void print_negative(int n) {
    if (n <= -10) {
        print_negative(n / 10);
    }
    putchar('0' - n % 10);
}

void print_int(int n) {
    if (n < 0) {
        putchar('-');
        print_negative(n);
    } else {
        print_negative(-n);
    }
}
```

```
2026
0
-45
2147483647
-2147483648
```

Bu sefer bütün sayılar doğru.

`print_negative` neden çalışıyor? C'de negatif bir sayıyı bölünce sonuç **sıfıra doğru** yuvarlanır ve kalan da negatif çıkar:

| İşlem | Sonuç |
| --- | --- |
| `-2026 / 10` | -202 |
| `-2026 % 10` | -6 |

Kalan -6 olduğu için rakamı `'0' - (-6)` = `'0' + 6` = `'6'` ile buluyoruz. `'0' + ...` yerine `'0' - ...` yazmamızın sebebi bu. Durma koşulu da ters döndü: `n >= 10` yerine `n <= -10`.

`print_int` artık sadece bir yönlendirici: negatif sayının önüne `'-'` koyup olduğu gibi gönderiyor, pozitif sayıyı ise negatife çevirip gönderiyor. Pozitiften negatife çevirmek her zaman güvenli.

Bu küçük tuzak, gerçek kütüphanelerde yıllarca fark edilmeden kalmış hatalara yol açmıştır. Ders 1.3'ten beri söylediğimiz şeyin bir örneği daha: **edge case'leri ayrıca dene.** `INT_MIN`, bir `int` fonksiyonunun her zaman denenmesi gereken edge case'idir.

---

## 5. printf'e göre ne kazandık?

`printf` çok daha fazlasını yapabiliyor: ondalıklı sayılar, hizalama, onaltılık gösterim… Ama artık `printf`'in içinde, bir sayıyı yazdırırken neler olduğunu biliyorsun: rakamlara ayırmak, sırayı düzeltmek, işaret ve edge case'lerle uğraşmak. Bir sonraki derste aynı işin tersini yapacağız: klavyeden gelen karakterleri sayıya çevirmek.

`print_int`'i bu fazın geri kalanında kendi araç kutumuz olarak kullanacağız. Ders 2.13'te onu ayrı bir dosyaya taşıyacak, Ders 2.15'teki faz projesinde de `printf`'in sayı yazdırma işini tamamen ona bırakacağız.

---

## Alıştırmalar

**1. Döngüyle.** `print_int`'i recursion kullanmadan, bir **array** yardımıyla yaz. (İpucu: rakamları sağdan sola bir array'e doldur, sonra array'i tersten yazdır. Bir `int` en fazla kaç basamaklı olabilir?)

**2. Binlik ayırıcı.** Sayıyı Türkçede alışık olduğumuz gibi binlik noktalarla yazdıran `print_with_dots(int n)` fonksiyonunu yaz: 1234567 → `1.234.567`, 999 → `999`, 1000 → `1.000`. Negatif sayıları düşünmene gerek yok.

**3. Genişlik.** `printf("%4d", n)` sayıyı 4 karakterlik bir alana sağa yaslayarak yazar (Ders 2.3, çarpım tablosu). Aynı işi yapan `print_padded(int n, int width)` fonksiyonunu yaz. `print_padded(42, 5)` → `   42`. (İpucu: önce sayının kaç karakter tuttuğunu bul.)

<details>
<summary>Cevaplar</summary>

**1.**
```c
void print_int(int n) {
    int digits[10];
    int count = 0;

    if (n < 0) {
        putchar('-');
    } else {
        n = -n;
    }
    do {
        digits[count] = -(n % 10);
        count++;
        n = n / 10;
    } while (n != 0);

    for (int i = count - 1; i >= 0; i--) {
        putchar('0' + digits[i]);
    }
}
```
Bir `int` en fazla 10 basamaklıdır (2.147.483.648), bu yüzden 10 elemanlı bir array yeter. Sayıyı yine negatif tarafta işliyoruz; `-(n % 10)` her zaman 0 ile 9 arasında. `do-while`, 0 sayısında da bir rakam yazılmasını sağlıyor (Ders 1.1'deki BasamakSayısı'nı hatırla). Recursion'ın stack'te bizim için yaptığını, burada array ile elle yaptık.

**2.**
```c
void print_with_dots(int n) {
    if (n < 1000) {
        print_int(n);
        return;
    }
    print_with_dots(n / 1000);
    putchar('.');
    int group = n % 1000;
    if (group < 100) {
        putchar('0');
    }
    if (group < 10) {
        putchar('0');
    }
    print_int(group);
}
```
`print_int` ile aynı fikir, ama rakam rakam değil **üçer üçer** ilerliyoruz. İnce nokta: 1.005.000'deki ortadaki grup 5'tir, ama `005` diye yazılmalı. Bu yüzden 100'den ve 10'dan küçük gruplara baştan sıfır ekliyoruz. En soldaki grup ise sıfırsız yazılır; o da durma koşulunda `print_int(n)` ile oluyor.

**3.**
```c
int count_chars(int n) {
    int count = 1;
    if (n < 0) {
        count++;
    }
    while (n <= -10 || n >= 10) {
        n = n / 10;
        count++;
    }
    return count;
}

void print_padded(int n, int width) {
    for (int i = count_chars(n); i < width; i++) {
        putchar(' ');
    }
    print_int(n);
}
```
Eksi işareti de bir karakter tutar. `n = n / 10` hem pozitif hem negatif sayılarda sıfıra yaklaştırdığı için, burada `INT_MIN` ile bile bir sorun yok.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §3.6 (`itoa`) ve §4.10 (`printd`): sayıyı karaktere çevirmenin döngülü ve recursive halleri. Alıştırma 3-4 aynı `INT_MIN` sorununu sorar.

**Sıradaki ders:** `scanf` olmadan sayı okuma. Klavyeden gelen karakterleri sayıya çevireceğiz.
