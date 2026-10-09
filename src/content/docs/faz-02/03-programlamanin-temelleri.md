---
title: "2.3 Programlamanın temelleri"
description: "C'nin yazım kuralları ve her dilde bulunan temel araçlar: değişken, aritmetik, karar, döngü, fonksiyon ve struct; çarpım tablosundan kalbe kadar alıştırmalar."
---

Bu ders, C dilinin **yazım kurallarını** ve hemen her programlama dilinde bulunan **temel araçların** nasıl kullanıldığını gösterir: değişkenler, hesaplama, karar verme, döngüler, fonksiyonlar ve struct'lar.

Bunlar programlamanın alfabesidir. Python, Java, JavaScript, hangi dile geçersen geç, aynı araçları bulacaksın; sadece yazılışları biraz farklı olacak. Burada öğrendiğin şey C'den çok daha büyük: **programlamanın kendisi**.

Faz 1'de bu araçların hepsini kağıtta zaten kullandın: atama, karar, döngü… Şimdi aynı şeyleri bilgisayara yazdıracağız.

:::caution[Bu dersin kalbi alıştırmalar]
Bu ders uzun ve sonunda bol alıştırma var. **Alıştırmalar dersin en önemli kısmı.** Programlama okuyarak öğrenilmez, tıpkı bisiklet sürmenin izleyerek öğrenilmediği gibi. Her örneği kendin yaz, çalıştır, bir yerini değiştirip ne olduğuna bak. Alıştırmaları çözmeden bir sonraki derse geçme; çözümlere bakmadan önce gerçekten uğraş. Takıldığın yer, öğrendiğin yerdir.
:::

Örnekleri `faz-02` klasöründe ayrı dosyalara yaz (`variables.c`, `loops.c` gibi). `F5` ile çalıştır.

---

## 1. Bir C programının iskeleti

Her C programı aşağı yukarı aynı iskelete sahiptir:

```c
#include <stdio.h>

int main(void) {
    // Kodun buraya yazılır.
    printf("Hello!\n");
    return 0;
}
```

Bilmen gereken birkaç kural:

- **Her komutun sonunda noktalı virgül (`;`) olur.** Türkçede cümle sonuna nokta koymak gibi.
- **Süslü parantezler (`{` `}`) bir grup komutu bir arada tutar.** Faz 1'deki pseudocode'da girinti ne yapıyorsa, C'de süslü parantez onu yapar.
- **`//` ile başlayan satır yorumdur.** Bilgisayar onu okumaz; sana ve kodu okuyacak başkalarına not bırakmak içindir.
- **Büyük ve küçük harf farklıdır.** `main` ile `Main` iki ayrı şeydir.
- **Girinti zorunlu değildir ama yapmalısın.** Bilgisayar umursamaz, ama düzgün girintili kodu okumak çok daha kolaydır. Her süslü parantezin içini dört boşluk içeri al.

---

## 2. Değişkenler

**Değişken**, içine bir değer koyduğumuz, üstünde adı yazan bir kutudur. Faz 1'de `x ← 5` diye yazdığımız şeyin C'deki karşılığı:

```c
#include <stdio.h>

int main(void) {
    int age = 20;
    int height = 175;

    printf("Yaş: %d\n", age);
    printf("Boy: %d cm\n", height);

    age = age + 1;
    printf("Bir yıl sonra yaş: %d\n", age);
    return 0;
}
```

```
Yaş: 20
Boy: 175 cm
Bir yıl sonra yaş: 21
```

Satır satır:

- `int age = 20;` → "`age` adında bir kutu aç, içine 20 koy". `int`, kutunun içine **tamsayı** konacağını söyler: 20, -3, 0, 1000 gibi. Küsuratlı sayılar için başka türler var; onları Faz 3'te göreceğiz. Bu fazda hep `int` kullanacağız.
- `printf("Yaş: %d\n", age);` → Ekrana yazı yazar. Yazının içindeki `%d`'nin yerine `age`'in değeri konur. `\n` satırı bitirir.
- `age = age + 1;` → "`age`'in içindeki değere 1 ekle, sonucu yine `age`'e koy". Faz 1'deki `age ← age + 1` ile aynı. C'de atama için `=` kullanılır.

**Bir `printf` içinde birden çok değer** yazdırabilirsin; `%d`'ler sırayla doldurulur:

```c
#include <stdio.h>

int main(void) {
    int a = 7;
    int b = 5;
    printf("%d + %d = %d\n", a, b, a + b);
    return 0;
}
```

```
7 + 5 = 12
```

**İsim kuralları:**

- Harf, rakam ve alt çizgi (`_`) kullanılabilir: `total`, `item2`, `student_count`.
- Rakamla başlayamaz: `2item` olmaz.
- **İsimleri İngilizce ver.** Yazılım dünyasının ortak dili İngilizcedir: kütüphaneler, belgeler, hata mesajları ve dünyanın her yerindeki programcıların kodları İngilizce isimlerle yazılır. Bu kitapta da öyle yapacağız: `yas` değil `age`, `toplam` değil `total`. (Ekrana yazdırdığın mesajlar elbette Türkçe olabilir.)
- İsim, kutunun içinde ne olduğunu anlatsın. `x` yerine `student_count` yazmak, kodunu okuyacak herkese (yarınki sana da) iyilik yapmaktır.

**Değer vermeden kullanma.** `int number;` yazıp içine bir şey koymadan `number`'ı yazdırırsan, ekrana ne çıkacağı belli değildir; kutunun içinde rastgele bir değer olabilir. Değişkeni açtığın anda bir değer vermeyi alışkanlık edin.

---

## 3. Hesaplama

| İşlem | C'de | Örnek | Sonuç |
| --- | --- | --- | --- |
| Toplama | `+` | `7 + 2` | 9 |
| Çıkarma | `-` | `7 - 2` | 5 |
| Çarpma | `*` | `7 * 2` | 14 |
| Bölme | `/` | `7 / 2` | **3** |
| Bölümden kalan | `%` | `7 % 2` | 1 |

**Dikkat: tamsayı bölmesi.** `7 / 2` sonucu 3,5 değil **3**'tür. İki tamsayı bölündüğünde küsurat atılır. Faz 1'deki `÷` işleminin aynısı. Kalan lazımsa `%` kullanılır; Faz 1'deki `mod`'un aynısı.

**İşlem önceliği** matematikteki gibidir: önce çarpma ve bölme, sonra toplama ve çıkarma. `2 + 3 * 4` sonucu 14'tür. Önce toplamayı yaptırmak istersen parantez kullan: `(2 + 3) * 4` sonucu 20'dir.

**Örnek: saniyeyi saate çevirmek.**

```c
#include <stdio.h>

int main(void) {
    int total = 3725;

    int hours = total / 3600;
    int minutes = (total % 3600) / 60;
    int seconds = total % 60;

    printf("%d saniye = %d saat %d dakika %d saniye\n", total, hours, minutes, seconds);
    return 0;
}
```

```
3725 saniye = 1 saat 2 dakika 5 saniye
```

**Örnek: vücut kitle indeksi.** Boyu santimetre olarak alırsak, metreye çevirmek için 10.000 ile çarpmamız gerekir:

```c
#include <stdio.h>

int main(void) {
    int weight = 70;
    int height = 175;

    int bmi = weight * 10000 / (height * height);
    printf("Vücut kitle indeksi: %d\n", bmi);
    return 0;
}
```

```
Vücut kitle indeksi: 22
```

Gerçek değer 22,86'ydı (Ders 1.2). Küsurat, tamsayı bölmesinde kayboldu. Bu fazda bununla yaşayacağız; Faz 3'te küsuratlı sayılarla düzelteceğiz.

**Kısaltmalar.** Bazı işlemler o kadar sık yapılır ki kısa yazılışları vardır:

| Uzun hali | Kısa hali |
| --- | --- |
| `x = x + 5;` | `x += 5;` |
| `x = x - 5;` | `x -= 5;` |
| `x = x * 5;` | `x *= 5;` |
| `x = x + 1;` | `x++;` |
| `x = x - 1;` | `x--;` |

---

## 4. Karşılaştırma ve mantık

Karar verebilmek için soru sormamız gerekir. Bu soruların cevabı **doğru** ya da **yanlış**tır.

| Soru | C'de | Örnek |
| --- | --- | --- |
| Eşit mi? | `==` | `a == b` |
| Eşit değil mi? | `!=` | `a != b` |
| Küçük mü? | `<` | `a < b` |
| Büyük mü? | `>` | `a > b` |
| Küçük ya da eşit mi? | `<=` | `a <= b` |
| Büyük ya da eşit mi? | `>=` | `a >= b` |

**`=` ile `==` farklıdır.** `=` atamadır ("şunu kutuya koy"), `==` sorudur ("bunlar eşit mi?"). Yeni başlayanların en sık yaptığı hata, soru sormak isterken `=` yazmaktır. Neyse ki `-Wall` ayarı açık olduğu için compiler seni uyarır.

Soruları birleştirmek için:

| Anlamı | C'de | Örnek |
| --- | --- | --- |
| AND: ikisi de doğru mu? | `&&` | `age >= 18 && age <= 65` |
| OR: en az biri doğru mu? | `\|\|` | `day == 6 \|\| day == 7` |
| NOT: tersi | `!` | `!(a == b)` |

Faz 0'daki AND, OR ve NOT'u hatırla: aynı mantık.

---

## 5. Karar: if ve else

`if`, Faz 1'deki karar sembolünün C'deki karşılığıdır.

**Örnek: çift mi, tek mi?**

```c
#include <stdio.h>

int main(void) {
    int number = 7;

    if (number % 2 == 0) {
        printf("%d çift\n", number);
    } else {
        printf("%d tek\n", number);
    }
    return 0;
}
```

```
7 tek
```

Okunuşu: "**Eğer** sayının 2'ye bölümünden kalan 0 ise 'çift' yaz, **değilse** 'tek' yaz." Parantezin içindeki soru doğruysa ilk süslü parantez, yanlışsa `else`'in süslü parantezi çalışır.

**Örnek: harf notu.** Birden fazla seçenek varsa `else if` ile zincir kurulur. Ders 1.2'deki zincir kararları hatırla:

```c
#include <stdio.h>

int main(void) {
    int score = 78;

    if (score >= 85) {
        printf("AA\n");
    } else if (score >= 70) {
        printf("BB\n");
    } else if (score >= 50) {
        printf("CC\n");
    } else {
        printf("FF\n");
    }
    return 0;
}
```

```
BB
```

Kontrol yukarıdan aşağıya yapılır ve **ilk doğru olan** çalışır, gerisine bakılmaz. 78, 85'ten büyük değil; 70'ten büyük, o yüzden "BB" yazılır ve zincir biter.

**Örnek: AND ile aralık kontrolü.**

```c
#include <stdio.h>

int main(void) {
    int temperature = 24;

    if (temperature >= 18 && temperature <= 26) {
        printf("Hava güzel.\n");
    } else {
        printf("Hava ya soğuk ya sıcak.\n");
    }
    return 0;
}
```

```
Hava güzel.
```

**Örnek: iç içe karar.** Bir `if`'in içine başka bir `if` yazılabilir:

```c
#include <stdio.h>

int main(void) {
    int age = 20;
    int has_license = 1;   // 1: var, 0: yok

    if (age >= 18) {
        if (has_license == 1) {
            printf("Araba kullanabilirsin.\n");
        } else {
            printf("Önce ehliyet almalısın.\n");
        }
    } else {
        printf("Yaşın tutmuyor.\n");
    }
    return 0;
}
```

```
Araba kullanabilirsin.
```

---

## 6. Çok seçenekli karar: switch

Bir değişkenin **belirli değerlerine** göre farklı işler yapılacaksa, uzun bir `else if` zinciri yerine `switch` daha okunaklıdır:

```c
#include <stdio.h>

int main(void) {
    int day = 3;

    switch (day) {
        case 1: printf("Pazartesi\n"); break;
        case 2: printf("Salı\n"); break;
        case 3: printf("Çarşamba\n"); break;
        case 4: printf("Perşembe\n"); break;
        case 5: printf("Cuma\n"); break;
        case 6:
        case 7: printf("Hafta sonu\n"); break;
        default: printf("Böyle bir gün yok\n");
    }
    return 0;
}
```

```
Çarşamba
```

- `case 3:` → "değer 3 ise buradan başla".
- `break;` → "`switch`'ten çık". **Unutursan**, program bir sonraki `case`'in komutlarını da çalıştırmaya devam eder.
- `case 6:` ile `case 7:` arka arkaya yazıldı: ikisi de aynı işi yapsın diye. Burada `break`'in olmaması bilerek yapıldı.
- `default:` → hiçbir `case` tutmazsa burası çalışır. `else`'e benzer.

---

## 7. Döngüler

Faz 1'de okun yukarı dönmesine döngü demiştik. C'de üç döngü var.

### while: koşul doğru oldukça tekrarla

Ders 1.2'deki "1'den n'e kadar toplam" diyagramının C hali:

```c
#include <stdio.h>

int main(void) {
    int n = 10;
    int total = 0;
    int i = 1;

    while (i <= n) {
        total += i;
        i++;
    }

    printf("Toplam: %d\n", total);
    return 0;
}
```

```
Toplam: 55
```

Diyagramla yan yana koy: `while (i <= n)` karar kutusu, süslü parantezin içi döngünün gövdesi, kapanan parantez ise yukarı dönen ok.

### for: sayarak tekrarla

Yukarıdaki döngüde üç şey vardı: sayacı başlatmak (`i = 1`), koşulu sormak (`i <= n`), sayacı ilerletmek (`i++`). Bu kalıp o kadar sık kullanılır ki bunun için ayrı bir döngü var:

```c
#include <stdio.h>

int main(void) {
    int n = 10;
    int total = 0;

    for (int i = 1; i <= n; i++) {
        total += i;
    }

    printf("Toplam: %d\n", total);
    return 0;
}
```

`for`'un parantezinde, noktalı virgülle ayrılmış üç parça var:

1. `int i = 1` → **başlangıç**: döngüden önce bir kez çalışır.
2. `i <= n` → **koşul**: her turdan önce sorulur; yanlışsa döngü biter.
3. `i++` → **adım**: her turun sonunda çalışır.

Kaç kez döneceği belli olan döngüler için `for`, belli olmayanlar için `while` kullanmak okunaklı bir alışkanlıktır.

### do-while: önce yap, sonra sor

Ders 1.1'deki BasamakSayısı algoritmasını hatırla: 0 sayısında hata vermemesi için önce bölmeyi yapıp sonra soruyu sormuştuk. İşte o döngü:

```c
#include <stdio.h>

int main(void) {
    int n = 2026;
    int count = 0;

    do {
        n = n / 10;
        count++;
    } while (n != 0);

    printf("Basamak sayısı: %d\n", count);
    return 0;
}
```

```
Basamak sayısı: 4
```

`n`'yi 0 yapıp dene: sonuç 1 olur. Doğru.

### break ve continue

- `break;` → döngüden **hemen çık**.
- `continue;` → bu turun geri kalanını atla, **bir sonraki tura geç**.

```c
#include <stdio.h>

int main(void) {
    // 50'den sonraki, 7'ye bölünen ilk sayı
    for (int i = 50; i <= 100; i++) {
        if (i % 7 == 0) {
            printf("Bulundu: %d\n", i);
            break;
        }
    }

    // 1'den 10'a kadar tek sayılar
    for (int i = 1; i <= 10; i++) {
        if (i % 2 == 0) {
            continue;
        }
        printf("%d ", i);
    }
    printf("\n");
    return 0;
}
```

```
Bulundu: 56
1 3 5 7 9 
```

### İç içe döngüler

Bir döngünün içine başka bir döngü yazılabilir. Dıştaki döngünün **her bir turunda**, içteki döngü baştan sona çalışır. Alıştırmalardaki bütün şekiller bu fikirle çizilecek, o yüzden iyi anla:

```c
#include <stdio.h>

int main(void) {
    for (int row = 1; row <= 3; row++) {
        for (int col = 1; col <= 4; col++) {
            printf("(%d,%d) ", row, col);
        }
        printf("\n");
    }
    return 0;
}
```

```
(1,1) (1,2) (1,3) (1,4) 
(2,1) (2,2) (2,3) (2,4) 
(3,1) (3,2) (3,3) (3,4) 
```

Dış döngü satırları, iç döngü o satırdaki sütunları sayıyor. Her satırın sonunda `printf("\n")` bir alt satıra geçiyor.

**Sonsuz döngüye dikkat.** Koşul hiç yanlış olmazsa döngü bitmez (Ders 1.3'ü hatırla). Programın donup kaldıysa terminalde `Ctrl+C` ile durdurabilirsin.

---

## 8. Fonksiyonlar

Bir işi birden fazla yerde yapacaksan, onu her seferinde baştan yazmak yerine bir kez **fonksiyon** olarak yazar ve adıyla çağırırsın. `main` de bir fonksiyondur; `printf` de.

```c
#include <stdio.h>

int square(int x) {
    return x * x;
}

int main(void) {
    printf("%d\n", square(5));
    printf("%d\n", square(12));
    return 0;
}
```

```
25
144
```

Fonksiyonun parçaları: `int square(int x)`

- `int` → fonksiyonun **geri verdiği** değerin türü.
- `square` → fonksiyonun **adı**.
- `int x` → fonksiyonun **aldığı** değer (parametre). `square(5)` çağrıldığında, fonksiyonun içinde `x` 5 olur.
- `return x * x;` → sonucu **geri ver** ve fonksiyondan çık.

**Birden fazla parametre** alabilir:

```c
int larger(int a, int b) {
    if (a >= b) {
        return a;
    }
    return b;
}
```

**Hiçbir şey geri vermeyebilir.** O zaman türü `void` yazılır. Böyle fonksiyonlar bir iş yapar ama sonuç döndürmez:

```c
void draw_line(int length) {
    for (int i = 0; i < length; i++) {
        printf("-");
    }
    printf("\n");
}
```

**Örnek: hepsi bir arada.** Ders 1.3'teki asal sayı algoritması da bir fonksiyon oluyor. C'de "doğru" için 1, "yanlış" için 0 kullanılır:

```c
#include <stdio.h>

int larger(int a, int b) {
    if (a >= b) {
        return a;
    }
    return b;
}

void draw_line(int length) {
    for (int i = 0; i < length; i++) {
        printf("-");
    }
    printf("\n");
}

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
    printf("Büyük olan: %d\n", larger(17, 42));

    draw_line(20);
    printf("30'a kadar asallar: ");
    for (int i = 1; i <= 30; i++) {
        if (is_prime(i)) {
            printf("%d ", i);
        }
    }
    printf("\n");
    draw_line(20);
    return 0;
}
```

```
Büyük olan: 42
--------------------
30'a kadar asallar: 2 3 5 7 11 13 17 19 23 29 
--------------------
```

`if (is_prime(i))` → fonksiyon 1 döndürürse koşul doğru, 0 döndürürse yanlış sayılır.

**Fonksiyon, kendisine verilen değerin kopyasıyla çalışır.** Fonksiyonun içinde parametreyi değiştirmek, dışarıdaki değişkeni değiştirmez:

```c
#include <stdio.h>

void increment(int x) {
    x = x + 1;
    printf("Fonksiyonun içinde: %d\n", x);
}

int main(void) {
    int a = 5;
    increment(a);
    printf("Dışarıda: %d\n", a);
    return 0;
}
```

```
Fonksiyonun içinde: 6
Dışarıda: 5
```

`increment`'e `a`'nın kendisi değil, değerinin bir kopyası (5) gitti. Fonksiyon kendi kopyasını 6 yaptı; `a` 5 olarak kaldı. Fonksiyonun içindeki değişkenler de sadece o fonksiyona aittir; dışarıdan görülmez. Fonksiyondan bir sonuç almak istiyorsan `return` ile geri verirsin.

**Sıra önemli.** C, dosyayı yukarıdan aşağıya okur. Bir fonksiyonu çağırmadan **önce** onu tanımış olmalıdır. Bu yüzden fonksiyonlarını `main`'in üstüne yaz.

---

## 9. Struct'lar

Bazen birkaç değer birlikte anlam taşır. Bir noktanın x ve y'si, bir dikdörtgenin eni ve boyu, bir öğrencinin numarası ve notları. Bunları ayrı ayrı değişkenlerde tutmak yerine tek bir pakette toplayabiliriz: **struct** (yapı).

### Örnek 1: nokta

```c
#include <stdio.h>

struct Point {
    int x;
    int y;
};

int main(void) {
    struct Point a = {3, 4};

    printf("a = (%d, %d)\n", a.x, a.y);

    a.x = 10;
    printf("a = (%d, %d)\n", a.x, a.y);
    return 0;
}
```

```
a = (3, 4)
a = (10, 4)
```

- `struct Point { int x; int y; };` → "Point adında yeni bir **tür** tanımla; içinde `x` ve `y` adında iki tamsayı olsun." Bu bir kalıptır; henüz kutu açılmadı.
- `struct Point a = {3, 4};` → "Bu kalıptan `a` adında bir kutu aç; `x`'e 3, `y`'ye 4 koy."
- `a.x` → "`a`'nın içindeki `x`." Nokta işareti, paketin içindeki parçaya ulaşmak için kullanılır.

### Örnek 2: dikdörtgen ve fonksiyonlar

Struct'lar fonksiyonlara verilebilir:

```c
#include <stdio.h>

struct Rectangle {
    int width;
    int height;
};

int area(struct Rectangle d) {
    return d.width * d.height;
}

int perimeter(struct Rectangle d) {
    return 2 * (d.width + d.height);
}

int is_square(struct Rectangle d) {
    return d.width == d.height;
}

int main(void) {
    struct Rectangle room = {4, 5};
    struct Rectangle tile = {3, 3};

    printf("Oda: alan %d, çevre %d\n", area(room), perimeter(room));
    printf("Karo: alan %d, çevre %d\n", area(tile), perimeter(tile));

    if (is_square(tile)) {
        printf("Karo bir kare.\n");
    }
    return 0;
}
```

```
Oda: alan 20, çevre 18
Karo: alan 9, çevre 12
Karo bir kare.
```

`return d.width == d.height;` → Karşılaştırmanın sonucu doğruysa 1, yanlışsa 0 döner.

### Örnek 3: öğrenci notu

```c
#include <stdio.h>

struct Student {
    int id;
    int midterm;
    int final;
};

int average(struct Student st) {
    return (st.midterm * 40 + st.final * 60) / 100;
}

int main(void) {
    struct Student student1 = {101, 60, 75};
    struct Student student2 = {102, 40, 45};

    int avg1 = average(student1);
    int avg2 = average(student2);

    printf("%d numaralı öğrenci: %d, %s\n", student1.id, avg1, avg1 >= 50 ? "geçti" : "kaldı");
    printf("%d numaralı öğrenci: %d, %s\n", student2.id, avg2, avg2 >= 50 ? "geçti" : "kaldı");
    return 0;
}
```

```
101 numaralı öğrenci: 69, geçti
102 numaralı öğrenci: 43, kaldı
```

Vizenin %40'ı, finalin %60'ı alınıyor. İki küçük yenilik var:

- `%s` → `%d` sayı yazar, `%s` ise bir yazı yazar.
- `koşul ? a : b` → "koşul doğruysa `a`, değilse `b`". Kısa bir `if-else` gibi düşün.

### Örnek 4: tarih ve fonksiyondan struct döndürmek

Fonksiyonlar struct **döndürebilir** de:

```c
#include <stdio.h>

struct Date {
    int day;
    int month;
    int year;
};

void print_date(struct Date date) {
    printf("%02d.%02d.%d\n", date.day, date.month, date.year);
}

int is_before(struct Date a, struct Date b) {
    if (a.year != b.year) {
        return a.year < b.year;
    }
    if (a.month != b.month) {
        return a.month < b.month;
    }
    return a.day < b.day;
}

struct Date add_years(struct Date date, int years) {
    date.year = date.year + years;
    return date;
}

int main(void) {
    struct Date birthday = {5, 3, 2001};
    struct Date today = {7, 10, 2026};

    print_date(birthday);
    print_date(today);

    if (is_before(birthday, today)) {
        printf("Doğum tarihi daha önce.\n");
    }

    struct Date ten_years_later = add_years(today, 10);
    print_date(ten_years_later);
    return 0;
}
```

```
05.03.2001
07.10.2026
Doğum tarihi daha önce.
07.10.2036
```

- `%02d` → sayıyı en az 2 basamakla yaz, eksikse başına 0 koy: 5 → `05`.
- `is_before` önce yıllara bakar; yıllar eşitse aylara, onlar da eşitse günlere. Ders 1.2'deki zincir kararların bir başka hali.
- `add_years` kendisine gelen tarihin **kopyasını** değiştirip geri veriyor. `today` değişmedi; yeni tarih `ten_years_later`'a kondu.

---

## 10. Alıştırmalar

Bu bölüm dersin en önemli kısmı. Her alıştırmayı **önce kendin** yaz. Takılırsan Faz 1'deki gibi önce kağıtta düşün: şekil alıştırmalarında her satır için "kaç boşluk, kaç yıldız?" diye küçük bir tablo çiz. Çözüme ancak gerçekten uğraştıktan sonra bak. Çözdükten sonra da bakıp kendi kodunla karşılaştır.

Şekil alıştırmalarının çoğunda bu iki yardımcı fonksiyon işini kolaylaştıracak. Dosyanın başına koy ve kullan:

```c
void spaces(int count) {
    for (int i = 0; i < count; i++) {
        printf(" ");
    }
}

void stars(int count) {
    for (int i = 0; i < count; i++) {
        printf("*");
    }
}
```

### Isınma

**10.1** – Bir sayının mutlak değerini döndüren `int absolute(int x)` fonksiyonunu yaz. `absolute(-7)` 7, `absolute(3)` 3 döndürmeli.

**10.2** – Üç sayının en büyüğünü bulan `int largest(int a, int b, int c)` fonksiyonunu yaz. (İpucu: Bölüm 8'deki `larger` fonksiyonunu kullanabilirsin.)

**10.3** – Bir saati tutan `struct Time { int hours; int minutes; };` yapısını tanımla. Bir saate dakika ekleyen `struct Time add_minutes(struct Time s, int mins)` fonksiyonunu yaz. 23:50'ye 25 dakika eklenince 00:15 olmalı.

<details>
<summary>Cevaplar</summary>

**10.1**
```c
int absolute(int x) {
    if (x < 0) {
        return -x;
    }
    return x;
}
```

**10.2**
```c
int largest(int a, int b, int c) {
    return larger(larger(a, b), c);
}
```
Önce `a` ile `b`'nin büyüğü bulunuyor, sonra o sonuçla `c` karşılaştırılıyor.

**10.3**
```c
struct Time {
    int hours;
    int minutes;
};

struct Time add_minutes(struct Time s, int mins) {
    int total = s.hours * 60 + s.minutes + mins;
    total = total % (24 * 60);
    s.hours = total / 60;
    s.minutes = total % 60;
    return s;
}
```
Fikir: önce her şeyi dakikaya çevir, ekle, bir günü (1440 dakika) aşarsa `%` ile başa sar, sonra tekrar saat ve dakikaya ayır. Bölüm 3'teki saniye çevirme örneğinin aynısı. Yazdırırken `printf("%02d:%02d\n", s.hours, s.minutes);` kullan.

</details>

### Çarpım tablosu

**10.4** – 1'den 10'a kadar çarpım tablosunu yazdır. Her sayı 4 karakterlik bir alana yazılsın ki sütunlar hizalı dursun. (İpucu: `%4d`, sayıyı 4 karakterlik bir alana sağa yaslayarak yazar.)

```
   1   2   3   4   5   6   7   8   9  10
   2   4   6   8  10  12  14  16  18  20
   3   6   9  12  15  18  21  24  27  30
 ...
  10  20  30  40  50  60  70  80  90 100
```

<details>
<summary>Cevap</summary>

```c
#include <stdio.h>

int main(void) {
    for (int row = 1; row <= 10; row++) {
        for (int col = 1; col <= 10; col++) {
            printf("%4d", row * col);
        }
        printf("\n");
    }
    return 0;
}
```

Bölüm 7'deki iç içe döngü örneğinin aynısı; sadece `(satır,sütun)` yerine `satır × sütun` yazıyoruz.

</details>

### Şekiller

Bütün şekillerde `int n = 5;` ile başla. Kodun doğruysa `n`'yi değiştirdiğinde şekil de büyüyüp küçülmeli.

**10.5 Kare.** n × n yıldızdan oluşan bir kare çiz.

```
*****
*****
*****
*****
*****
```

**10.6 Dik üçgen.** 1. satırda 1, 2. satırda 2, …, n. satırda n yıldız.

```
*
**
***
****
*****
```

**10.7 Ters dik üçgen.** 1. satırda n, 2. satırda n − 1, …, son satırda 1 yıldız.

```
*****
****
***
**
*
```

**10.8 Üçgen.** Ortalanmış bir üçgen (piramit).

```
    *
   ***
  *****
 *******
*********
```

<details>
<summary>Cevaplar: kare, dik üçgen, ters dik üçgen</summary>

Üçünde de dış döngü satırları sayıyor; değişen tek şey, her satırda kaç yıldız yazılacağı.

| Şekil | Satır `i`'de (1'den n'e) yıldız sayısı |
| --- | --- |
| Kare | `n` |
| Dik üçgen | `i` |
| Ters dik üçgen | `n - i + 1` |

```c
#include <stdio.h>

void stars(int count) {
    for (int i = 0; i < count; i++) {
        printf("*");
    }
}

int main(void) {
    int n = 5;

    // Kare
    for (int i = 1; i <= n; i++) {
        stars(n);
        printf("\n");
    }
    printf("\n");

    // Dik üçgen
    for (int i = 1; i <= n; i++) {
        stars(i);
        printf("\n");
    }
    printf("\n");

    // Ters dik üçgen
    for (int i = 1; i <= n; i++) {
        stars(n - i + 1);
        printf("\n");
    }
    return 0;
}
```

</details>

<details>
<summary>Cevap: üçgen</summary>

Önce kağıtta n = 5 için tabloyu çıkar:

| Satır `i` | Boşluk | Yıldız |
| --- | --- | --- |
| 1 | 4 | 1 |
| 2 | 3 | 3 |
| 3 | 2 | 5 |
| 4 | 1 | 7 |
| 5 | 0 | 9 |

Boşluk her satırda bir azalıyor: `n - i`. Yıldız her satırda iki artıyor: `2 * i - 1`.

```c
#include <stdio.h>

void spaces(int count) {
    for (int i = 0; i < count; i++) {
        printf(" ");
    }
}

void stars(int count) {
    for (int i = 0; i < count; i++) {
        printf("*");
    }
}

int main(void) {
    int n = 5;

    for (int i = 1; i <= n; i++) {
        spaces(n - i);
        stars(2 * i - 1);
        printf("\n");
    }
    return 0;
}
```

Şekil alıştırmalarının sırrı bu tablodur: **önce sayıları bul, sonra kodu yaz.** Ders 1.3'teki trace table'ın bir başka kullanımı.

</details>

### Kalp

Son alıştırma, bu dersteki her şeyi bir araya getiriyor. Bir kerede çözmeye çalışma; **aşama aşama** ilerle. Her aşama bir öncekinin üzerine kurulu. Hepsinde `int k = 3;` kullan.

Hedefimiz bu:

```
  ***     ***
 *****   *****
******* *******
***************
 *************
  ***********
   *********
    *******
     *****
      ***
       *
```

Dikkatli bak: bu şekil iki parçadan oluşuyor. Üstte **yan yana iki tepecik**, altta **ters bir üçgen**.

**10.9 Aşama 1: tek tepecik.** Üstü düz bir piramit çiz: k satır; ilk satırda k yıldız, her satırda 2 yıldız fazlası. Ortalanmış olsun.

```
  ***
 *****
*******
```

**10.10 Aşama 2: iki tepecik.** Aynı tepeciği yan yana iki kez çiz. Aralarındaki boşluk aşağı indikçe daralsın, son satırda tek boşluk kalsın.

```
  ***     ***
 *****   *****
******* *******
```

**10.11 Aşama 3: ters üçgen.** İlk satırı 15 yıldız (`6 * k - 3`) olan, her satırda iki yanından birer yıldız eksilen, en sonda tek yıldıza inen bir ters üçgen çiz.

```
***************
 *************
  ***********
   *********
    *******
     *****
      ***
       *
```

**10.12 Aşama 4: kalp.** İki tepeciğin hemen altına ters üçgeni ekle. Sonra `k`'yi 4 ya da 5 yapıp kalbin büyüdüğünü gör.

<details>
<summary>Cevap: aşama 1, tek tepecik</summary>

Tablo (k = 3, satırlar 0'dan başlıyor):

| Satır `i` | Boşluk | Yıldız |
| --- | --- | --- |
| 0 | 2 | 3 |
| 1 | 1 | 5 |
| 2 | 0 | 7 |

Boşluk: `k - 1 - i`. Yıldız: `k + 2 * i`.

```c
for (int i = 0; i < k; i++) {
    spaces(k - 1 - i);
    stars(k + 2 * i);
    printf("\n");
}
```

</details>

<details>
<summary>Cevap: aşama 2, iki tepecik</summary>

İkinci tepeciği aynı satıra yazmadan önce aradaki boşluğu basmamız gerekiyor. Tabloya bir sütun ekleyelim:

| Satır `i` | Sol boşluk | Yıldız | Ara boşluk | Yıldız |
| --- | --- | --- | --- | --- |
| 0 | 2 | 3 | 5 | 3 |
| 1 | 1 | 5 | 3 | 5 |
| 2 | 0 | 7 | 1 | 7 |

Ara boşluk her satırda iki azalıyor ve 1'de bitiyor: `2 * (k - 1 - i) + 1`.

```c
for (int i = 0; i < k; i++) {
    spaces(k - 1 - i);
    stars(k + 2 * i);
    spaces(2 * (k - 1 - i) + 1);
    stars(k + 2 * i);
    printf("\n");
}
```

</details>

<details>
<summary>Cevap: aşama 3, ters üçgen</summary>

İki tepeciğin son satırı 7 + 1 + 7 = 15 karakter. Ters üçgen de tam bu genişlikte başlamalı ki iki parça birbirine otursun: `6 * k - 3`.

| Satır `j` | Boşluk | Yıldız |
| --- | --- | --- |
| 0 | 0 | 15 |
| 1 | 1 | 13 |
| … | … | … |
| 7 | 7 | 1 |

Boşluk: `j`. Yıldız: `width - 2 * j`. Yıldız sayısı 1'e inince dur; bu da `3 * k - 1` satır eder.

```c
int width = 6 * k - 3;
for (int j = 0; j < 3 * k - 1; j++) {
    spaces(j);
    stars(width - 2 * j);
    printf("\n");
}
```

</details>

<details>
<summary>Cevap: aşama 4, kalp</summary>

İki parçayı arka arkaya koymak yeterli:

```c
#include <stdio.h>

void spaces(int count) {
    for (int i = 0; i < count; i++) {
        printf(" ");
    }
}

void stars(int count) {
    for (int i = 0; i < count; i++) {
        printf("*");
    }
}

int main(void) {
    int k = 3;

    // Üst: iki tepecik
    for (int i = 0; i < k; i++) {
        spaces(k - 1 - i);
        stars(k + 2 * i);
        spaces(2 * (k - 1 - i) + 1);
        stars(k + 2 * i);
        printf("\n");
    }

    // Alt: ters üçgen
    int width = 6 * k - 3;
    for (int j = 0; j < 3 * k - 1; j++) {
        spaces(j);
        stars(width - 2 * j);
        printf("\n");
    }
    return 0;
}
```

k = 4 ile:

```
   ****       ****
  ******     ******
 ********   ********
********** **********
*********************
 *******************
  *****************
   ***************
    *************
     ***********
      *********
       *******
        *****
         ***
          *
```

Büyük bir şekli küçük parçalara bölmek, her parçayı ayrı ayrı çözmek, sonra birleştirmek: bu sadece kalp çizmenin değil, **her büyük programın** yazılış biçimidir. Bu fikri bu kitap boyunca defalarca kullanacağız.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), Bölüm 1–3: değişkenler, kontrol akışı, fonksiyonlar; Bölüm 6.1–6.2: struct'lar.
- K. N. King, *C Programming: A Modern Approach* (2. baskı), Bölüm 2–9: aynı konuların bol örnekli anlatımı.

**Sıradaki ders:** Array'ler. Aynı türden çok sayıda değeri tek bir isim altında tutmayı öğrenip ilk oyunumuzu yazacağız: bir labirent.
