---
title: "2.11 Çok dosyalı program ve Make"
description: "Kodu header (.h) ve kaynak (.c) dosyalarına bölmek, linker hataları, include guard, dosya düzeyinde static, extern, macro tuzakları ve Makefile ile sadece değişeni yeniden derlemek."
---

Ders 2.9'da `gcd` ve `lcm`, Ders 2.10'da `isqrt` gibi kullanışlı fonksiyonlar yazdık. Şimdi onları kullanmak istediğimiz her programa **kopyalamamız** gerekiyor. Bir hatayı düzeltirsek, kopyaladığımız her yerde ayrı ayrı düzeltmemiz gerekecek. Bir yeri unutursak, aynı fonksiyonun iki farklı sürümü dolaşmaya başlar.

Gerçek programlar tek bir dosyada yazılmaz. Bir tarayıcı, bir işletim sistemi, bir oyun binlerce dosyadan oluşur. Bu derste bir programı birden fazla dosyaya bölmeyi ve bu dosyaları her seferinde elle derlemek yerine **Make** adlı bir araca derletmeyi öğreneceğiz.

---

## 1. Header ve kaynak dosyası

Örnek olarak kesirlerle çalışan küçük bir modül yazalım: bir kesri bir `struct` ile tutacağız (Ders 2.3), iki kesri toplayıp sonucu sadeleştireceğiz. Fonksiyonları iki dosyaya ayıracağız:

- **`fraction.h`**, bir **header file** (başlık dosyası): Fonksiyonların **prototiplerini** (Ders 2.7) ve ortak tanımları içerir. "Bu dosyada neler var?" sorusunun cevabıdır; bir tür içindekiler sayfası.
- **`fraction.c`**, kaynak dosyası: Fonksiyonların **gövdelerini** içerir. "Bunlar nasıl yapılıyor?" sorusunun cevabı.

`faz-02` klasöründe `fraction-app` adında yeni bir klasör aç ve içine üç dosya koy.

`fraction.h`:

```c
#ifndef FRACTION_H
#define FRACTION_H

struct Fraction {
    int num;
    int den;
};

struct Fraction add_fractions(struct Fraction a, struct Fraction b);
void print_fraction(struct Fraction f);

#endif
```

`num` pay (numerator), `den` payda (denominator). (`#ifndef`, `#define` ve `#endif` satırlarını Bölüm 4'te açıklayacağız.)

`fraction.c`:

```c
#include <stdio.h>
#include "fraction.h"

static int gcd(int a, int b) {
    while (b != 0) {
        int r = a % b;
        a = b;
        b = r;
    }
    return a;
}

static struct Fraction simplify(struct Fraction f) {
    int g = gcd(f.num, f.den);
    struct Fraction result = {f.num / g, f.den / g};
    return result;
}

struct Fraction add_fractions(struct Fraction a, struct Fraction b) {
    struct Fraction sum = {a.num * b.den + b.num * a.den, a.den * b.den};
    return simplify(sum);
}

void print_fraction(struct Fraction f) {
    printf("%d/%d", f.num, f.den);
}
```

`gcd`, Ders 2.9'daki Öklid algoritması. Paydaları çarpıp topluyoruz, sonra pay ve paydayı EBOB'a bölerek sadeleştiriyoruz. Kesirlerin pozitif olduğunu varsayıyoruz. (`static` kelimesini Bölüm 5'te açıklayacağız.)

`main.c`:

```c
#include <stdio.h>
#include "fraction.h"

int main(void) {
    struct Fraction a = {1, 6};
    struct Fraction b = {3, 4};
    print_fraction(a);
    printf(" + ");
    print_fraction(b);
    printf(" = ");
    print_fraction(add_fractions(a, b));
    printf("\n");
    return 0;
}
```

**`#include "fraction.h"` ile `#include <stdio.h>` arasındaki fark:** Açılı parantez `< >` "sistemin kendi kütüphanelerinde ara" demektir. Tırnak `" "` ise "önce benim klasörümde ara" demektir. Kendi header'larımızı hep tırnakla ekleriz.

Ders 2.2'deki preprocessor'ı hatırla: `#include` satırı, dosyanın içeriğini olduğu gibi oraya yapıştırır. Yani `main.c` derlenirken `fraction.h`'daki struct tanımı ve prototipler `main.c`'nin en üstüne kopyalanmış olur. Compiler `struct Fraction`'ın neye benzediğini, `add_fractions` ve `print_fraction`'ın var olduğunu ve nasıl çağrılacaklarını buradan öğrenir. Gövdelerini ise görmez; onlar başka bir dosyada.

---

## 2. Derlemek ve linker hataları

VS Code'daki `Ctrl+Shift+B` sadece **açık olan** dosyayı derler; bu yüzden çok dosyalı programlarda işe yaramaz. Terminali aç ve `fraction-app` klasörüne geç:

```sh
cd faz-02/fraction-app
mkdir -p ../../build/faz-02/fraction-app
clang -std=c17 -Wall -Wextra main.c fraction.c -o ../../build/faz-02/fraction-app/fractions
```

İki `.c` dosyasını birlikte verdik. Peki `fraction.c`'yi unutsaydık?

```sh
clang -std=c17 main.c -o fractions
```

```
Undefined symbols for architecture arm64:
  "_add_fractions", referenced from:
      _main in main-0852d8.o
  "_print_fraction", referenced from:
      _main in main-0852d8.o
```

(Linux'ta aynı hata `undefined reference to 'add_fractions'` diye görünür.)

Bu bir **compiler** hatası değil, bir **linker** hatası. Ders 2.2'deki derleme hattını hatırla:

1. Compiler her `.c` dosyasını **ayrı ayrı** derleyip bir object file (`.o`) üretir. `main.c`'yi derlerken `fraction.h` sayesinde `add_fractions`'ın var olduğunu bilir ve hiç şikâyet etmez: "Bu fonksiyon bir yerlerde var, linker bulur."
2. Linker bütün object file'ları birleştirir ve her çağrının gerçekten bir gövdesi olup olmadığına bakar. `add_fractions`'ın gövdesi hiçbir yerde yok: hata.

Hatanın **hangi adımda** çıktığını anlamak, onu çözmenin yarısıdır. "undefined symbol" ya da "undefined reference" gördüğünde, aklına ilk gelmesi gereken soru şu: "Bu fonksiyonun gövdesi olan dosyayı derlemeye ekledim mi?"

---

## 3. Her dosyayı ayrı derlemek

Derleme hattını adım adım yürütüp her dosyayı ayrı derleyebiliriz:

```sh
clang -std=c17 -Wall -Wextra -c main.c -o ../../build/faz-02/fraction-app/main.o
clang -std=c17 -Wall -Wextra -c fraction.c -o ../../build/faz-02/fraction-app/fraction.o
clang ../../build/faz-02/fraction-app/main.o ../../build/faz-02/fraction-app/fraction.o -o ../../build/faz-02/fraction-app/fractions
```

`-c` "sadece derle, bağlama" demektir (Ders 2.2). Önce iki object file ürettik, sonra linker'a birleştirttik.

Neden bu kadar zahmet? Çünkü artık `main.c`'yi değiştirdiğimizde `fraction.c`'yi **yeniden derlememize gerek yok**: sadece `main.c`'yi derleyip tekrar bağlarız. İki dosyada fark hissedilmez. Ama binlerce dosyalı bir projede her küçük değişiklikte her şeyi baştan derlemek dakikalar, hatta saatler sürer. Sadece değişeni derlemek saniyeler.

Bunu elle takip etmek zor: hangi dosya değişti, hangi `.o` eskidi? Bu işi bizim yerimize yapan araç **Make**. Bölüm 7'de ona geçeceğiz; önce header dosyalarının üç önemli inceliğini görelim.

---

## 4. Include guard

`fraction.h`'ın başındaki ve sonundaki üç satırın neden orada olduğunu görmek için onları kaldırınca ne olduğuna bakalım. İki header düşün: `point.h` bir struct tanımlıyor, `shapes.h` de onu kullandığı için `point.h`'ı ekliyor:

```c
// point.h
struct Point {
    int x;
    int y;
};
```

```c
// shapes.h
#include "point.h"

int distance_squared(struct Point a, struct Point b);
```

`main.c` ikisini de ekliyor:

```c
#include "point.h"
#include "shapes.h"
```

```
./point.h:1:8: error: redefinition of 'Point'
main.c:1:10: note: './point.h' included multiple times, additional include site here
```

`point.h` iki kez eklendi: bir kez doğrudan, bir kez `shapes.h`'ın içinden. Preprocessor içeriğini iki kez yapıştırdı ve `struct Point` iki kez tanımlanmış oldu. C buna izin vermez.

Büyük projelerde header'lar birbirini ekler ve aynı header'ın dolaylı yollardan birden fazla kez eklenmesi kaçınılmazdır. Çözüm **include guard**:

```c
#ifndef POINT_H
#define POINT_H

struct Point {
    int x;
    int y;
};

#endif
```

Preprocessor için:

- `#ifndef POINT_H`: "`POINT_H` diye bir isim **tanımlanmamışsa** devam et; tanımlanmışsa `#endif`'e kadar her şeyi atla."
- `#define POINT_H`: "`POINT_H`'ı tanımla."

İlk eklemede `POINT_H` tanımlı değildir; içerik yapıştırılır ve `POINT_H` tanımlanır. İkinci eklemede `POINT_H` artık tanımlıdır ve içeriğin tamamı atlanır. Header kaç kez eklenirse eklensin, içeriği bir kez görünür.

**Kural:** Yazdığın her header dosyası include guard ile başlasın. İsim olarak dosya adının büyük harfli halini kullan: `fraction.h` → `FRACTION_H`.

(Pek çok compiler, aynı işi tek satırda yapan `#pragma once`'ı da tanır. Standart C'nin parçası değildir ama yaygındır.)

---

## 5. Dosya düzeyinde static

`fraction.c`'de iki fonksiyonun başında `static` var: `gcd` ve `simplify`. Ders 2.7'de "`static` kelimesinin bir anlamı daha var" demiştik; işte o anlam.

Bir fonksiyonun başına `static` yazıldığında, o fonksiyon **sadece kendi dosyasından** görünür. Başka bir dosya onu çağıramaz:

```c
// s.c
static int helper(void) {
    return 7;
}

int api(void) {
    return helper();
}
```

```c
// m.c
int helper(void);

int main(void) {
    return helper();
}
```

```
Undefined symbols for architecture arm64:
  "_helper", referenced from:
      _main in m-c45c4d.o
```

`m.c` prototipi yazsa bile linker `helper`'ı bulamıyor; çünkü `helper` `s.c`'nin dışına hiç açılmamış.

**Neden işe yarar?** `gcd` ve `simplify`, `add_fractions`'ın iç işinin bir parçası. `main.c`'nin onu bilmesine gerek yok; bilirse yanlışlıkla çağırabilir. Bir dosyanın dışarıya sadece **gerekeni** göstermesi, Ders 2.7'deki "değişkeni olabildiğince dar bir scope'ta tanımla" kuralının dosyalar düzeyindeki karşılığı. Header dosyası dışarıya açık olanların listesidir; `static` fonksiyonlar o listede yer almaz.

---

## 6. extern: dosyalar arası global değişken

Ders 2.7'de global değişkenlerden uzak durmayı önermiştik. Ama birden fazla dosyanın gerçekten aynı değişkeni paylaşması gerekiyorsa? Örneğin `add_fractions`'ın kaç kez çağrıldığını programın her yerinden görmek isteyelim.

Değişken **bir** `.c` dosyasında tanımlanır, header'da ise `extern` ile duyurulur:

```c
// counter.h
#ifndef COUNTER_H
#define COUNTER_H

extern int add_count;
void count_add(void);

#endif
```

```c
// counter.c
#include "counter.h"

int add_count = 0;

void count_add(void) {
    add_count++;
}
```

`extern int add_count;` şunu söyler: "`add_count` adında bir `int` var, ama burada değil, başka bir dosyada." Bu bir **tanıtım**dır, yer ayırmaz. Değişkenin kendisi `counter.c`'deki `int add_count = 0;` satırıdır. Prototipin değişkenler için olan karşılığı gibi düşün.

Ders 2.7'deki uyarı burada iki katına çıkar: artık değişkeni bozabilecek fonksiyonlar sadece bir dosyada değil, programın **her yerinde** olabilir. `extern`'ü gerçekten gerekmedikçe kullanma.

---

## 7. #define ve macro tuzakları

`#define`'ı Ders 2.4'ten beri sabitler için kullanıyoruz: `#define SIZE 5`. Preprocessor kodda `SIZE` gördüğü her yere `5` yazar. Ama `#define` parametre de alabilir; buna **macro** denir:

```c
#define SQUARE(x) x * x
```

Bir fonksiyon gibi görünüyor, ama **değil**. Preprocessor sadece metni değiştirir. Sonuçlara bakalım:

```c
#include <stdio.h>

#define SQUARE(x) x * x
#define SQUARE_OK(x) ((x) * (x))

int main(void) {
    printf("%d\n", SQUARE(3));
    printf("%d\n", SQUARE(1 + 2));
    printf("%d\n", SQUARE_OK(1 + 2));
    printf("%d\n", 100 / SQUARE(5));
    printf("%d\n", 100 / SQUARE_OK(5));
    return 0;
}
```

```
9
5
9
100
4
```

`SQUARE(1 + 2)` 9 değil **5**, `100 / SQUARE(5)` 4 değil **100**! Neden? `clang -E` ile preprocessor'ın çıktısına bakalım (Ders 2.2):

```c
printf("%d\n", 3 * 3);
printf("%d\n", 1 + 2 * 1 + 2);
printf("%d\n", ((1 + 2) * (1 + 2)));
printf("%d\n", 100 / 5 * 5);
```

Macro, `x`'in yerine `1 + 2`'yi **olduğu gibi** yapıştırdı: `1 + 2 * 1 + 2`. İşlem önceliği yüzünden önce çarpma yapıldı ve sonuç 5 oldu. `100 / 5 * 5` de soldan sağa hesaplandı: (100 / 5) × 5 = 100.

**Kural 1:** Macro'da her parametreyi **ve** bütün ifadeyi paranteze al: `((x) * (x))`.

Ama paranteze almak bile her şeyi çözmez:

```c
#define MAX(a, b) ((a) > (b) ? (a) : (b))

int x = 5;
int y = 3;
int m = MAX(x++, y);
```

```
MAX: 6, x: 7
```

5 ile 3'ün büyüğü 5 olmalıydı. Ama macro açıldığında `x++` **iki kez** yazılmış olur: `((x++) > (y) ? (x++) : (y))`. `x` iki kez artırıldı ve sonuç 6 çıktı. Aynı işi bir fonksiyonla yapsaydık `x++` sadece bir kez çalışırdı ve sonuç 5 olurdu.

**Kural 2:** Hesap yapan bir macro yazmak istiyorsan, onun yerine **fonksiyon** yaz. Macro'ları sabitler ve include guard gibi preprocessor'ın asıl işleri için sakla.

---

## 8. Make

Şimdi Bölüm 3'teki "sadece değişeni derle" fikrini bir araca bırakalım. **Make**, 1976'dan beri kullanılan bir derleme aracıdır. Ne yapacağını, proje klasöründeki `Makefile` adlı bir dosyadan okur. [clang ve LLDB](/kurulum/llvm/) kurulumunda make de kuruldu; `make --version` bir sürüm göstermiyorsa o sayfaya dön.

`fraction-app` klasörüne `Makefile` adında (uzantısız) bir dosya oluştur:

```makefile
CC = clang
CFLAGS = -std=c17 -Wall -Wextra -g
BUILD = ../../build/faz-02/fraction-app

$(BUILD)/fractions: $(BUILD)/main.o $(BUILD)/fraction.o
	$(CC) $(CFLAGS) $(BUILD)/main.o $(BUILD)/fraction.o -o $(BUILD)/fractions

$(BUILD)/main.o: main.c fraction.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c main.c -o $(BUILD)/main.o

$(BUILD)/fraction.o: fraction.c fraction.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c fraction.c -o $(BUILD)/fraction.o

run: $(BUILD)/fractions
	$(BUILD)/fractions

clean:
	rm -rf $(BUILD)

.PHONY: run clean
```

**İlk dört satır değişken:** `$(CC)` yazılan her yere `clang`, `$(CFLAGS)` yazılan her yere derleme ayarları gelir. Derleme çıktıları, Ders 2.2'deki düzene uygun olarak çalışma alanının `build` klasörüne gidiyor.

**Geri kalanı kurallar.** Her kural şu şekildedir:

```makefile
hedef: bağımlılıklar
	komut
```

- **Hedef** (target): Üretilecek dosya. Örneğin `$(BUILD)/main.o`.
- **Bağımlılıklar** (prerequisites): Hedef hangi dosyalardan üretiliyor? `main.o`, `main.c`'den ve onun eklediği `fraction.h`'dan üretiliyor.
- **Komut** (recipe): Hedefi üretmek için ne çalıştırılacak? **Dikkat:** komut satırları boşlukla değil, **Tab** karakteriyle başlamak zorunda. Boşlukla başlarsa Make `missing separator` hatası verir. VS Code `Makefile`'larda Tab'ı kendiliğinden kullanır.

**Make nasıl karar verir?** Bir hedefi üretmeden önce bağımlılıklarına bakar. Bağımlılıklardan herhangi biri hedeften **daha yeniyse**, yani hedef üretildikten sonra değiştirildiyse, komutu çalıştırır. Değilse hiçbir şey yapmaz. Bunu her dosyanın son değiştirilme zamanına bakarak yapar.

İlk çalıştırma:

```sh
make
```

```
mkdir -p ../../build/faz-02/fraction-app
clang -std=c17 -Wall -Wextra -g -c main.c -o ../../build/faz-02/fraction-app/main.o
mkdir -p ../../build/faz-02/fraction-app
clang -std=c17 -Wall -Wextra -g -c fraction.c -o ../../build/faz-02/fraction-app/fraction.o
clang -std=c17 -Wall -Wextra -g ../../build/faz-02/fraction-app/main.o ../../build/faz-02/fraction-app/fraction.o -o ../../build/faz-02/fraction-app/fractions
```

Make ilk kuralı (`fractions`) hedef aldı. Onun için `main.o` ve `fraction.o` gerekiyordu; ikisi de yoktu, önce onları üretti, sonra bağladı. Hiçbir şeyi değiştirmeden tekrar çalıştır:

```
make: `../../build/faz-02/fraction-app/fractions' is up to date.
```

"Güncel." Hiçbir şey derlenmedi. Şimdi sadece `fraction.c`'yi değiştir (bir boşluk ekleyip kaydetmek yeter) ve tekrar `make`:

```
mkdir -p ../../build/faz-02/fraction-app
clang -std=c17 -Wall -Wextra -g -c fraction.c -o ../../build/faz-02/fraction-app/fraction.o
clang -std=c17 -Wall -Wextra -g ../../build/faz-02/fraction-app/main.o ../../build/faz-02/fraction-app/fraction.o -o ../../build/faz-02/fraction-app/fractions
```

Sadece `fraction.o` yeniden derlendi; `main.o`'ya dokunulmadı. Son olarak `fraction.h`'ı değiştir:

```
mkdir -p ../../build/faz-02/fraction-app
clang -std=c17 -Wall -Wextra -g -c main.c -o ../../build/faz-02/fraction-app/main.o
mkdir -p ../../build/faz-02/fraction-app
clang -std=c17 -Wall -Wextra -g -c fraction.c -o ../../build/faz-02/fraction-app/fraction.o
clang -std=c17 -Wall -Wextra -g ../../build/faz-02/fraction-app/main.o ../../build/faz-02/fraction-app/fraction.o -o ../../build/faz-02/fraction-app/fractions
```

`fraction.h` iki `.o`'nun da bağımlılığı olduğu için ikisi de yeniden derlendi. Header'ı bağımlılıklara yazmamızın sebebi bu: `Fraction` struct'ını değiştirirsek, onu kullanan her dosya yeniden derlenmeli.

**`run` ve `clean`.** Bunlar dosya üretmeyen, kolaylık için konmuş hedefler. `make run` programı derleyip çalıştırır; `make clean` derleme çıktılarını siler. `.PHONY` satırı Make'e "bunlar dosya adı değil, sadece komut isimleri" der.

```sh
make run
```

```
../../build/faz-02/fraction-app/fractions
1/6 + 3/4 = 11/12
```

İlk satırda Make, çalıştırdığı komutu yazıyor; ardından programın kendisi geliyor.

**Hata ayıklamak için:** `F5`, VS Code'daki ayara göre açık dosyayı tek başına derler; çok dosyalı bir programda bu linker hatası verir. Çok dosyalı programlarda önce `make` ile derle, sonra terminalden LLDB'yi kullan: `lldb ../../build/faz-02/fraction-app/fractions` (Ders 2.6). `CFLAGS`'teki `-g` bu yüzden orada.

Make, bu fazın sonuna kadar ihtiyacımızı karşılayacak. Projeler büyüdükçe Makefile'ları elle yazmak zorlaşır; kitabın ilerleyen bölümlerinde daha güçlü derleme sistemlerine geçeceğiz. Ama hepsinin altında aynı fikir yatar: **hedef, bağımlılıklar, komut; sadece değişeni yeniden üret.**

---

## Alıştırmalar

**1. Kendi kütüphanen.** Ders 2.10'daki `isqrt` ve Ders 2.9'daki `gcd`, `lcm`, `is_prime` fonksiyonlarını `numbers.h` ve `numbers.c` dosyalarına taşı. Bunları kullanan bir `main.c` yaz: 1'den 50'ye kadar asal sayıları ve 36'nın karekökünü yazdırsın. Bir `Makefile` hazırla.

**2. Eksik bağımlılık.** Bölüm 8'deki `Makefile`'da `main.o` kuralındaki bağımlılıklardan `fraction.h`'ı sildiğini düşün. Sonra `fraction.h`'daki `struct Fraction`'ın iki alanının sırasını değiştirdin (`den` önce, `num` sonra) ve `make` yazdın. Ne olur? Neden tehlikeli?

**3. Macro mu, fonksiyon mu?** Bir sayının mutlak değerini veren `ABS(x)` macro'sunu Bölüm 7'deki kurallara uyarak yaz. Sonra `ABS(x--)` ifadesinde ne olacağını tahmin et. Bunun yerine ne yazmalısın?

<details>
<summary>Cevaplar</summary>

**1.** `numbers.h`:

```c
#ifndef NUMBERS_H
#define NUMBERS_H

int gcd(int a, int b);
int lcm(int a, int b);
int isqrt(int n);
int is_prime(int n);

#endif
```

`numbers.c` bu dört fonksiyonun gövdelerini içerir ve en başta `#include "numbers.h"` yapar. `is_prime`, Ders 2.10'daki düzeltilmiş haliyle `isqrt`'yi kullanabilir; ikisi aynı dosyada olduğu için sorun yok. `Makefile`, Bölüm 8'dekinin aynısı; `fraction` yerine `numbers` yaz ve `BUILD` klasörünün adını değiştir.

Kendi header'ını kendi `.c` dosyasının başında eklemek iyi bir alışkanlıktır: prototiple gövde arasında bir uyumsuzluk varsa (örneğin parametre sayısı farklıysa) compiler bunu hemen yakalar.

**2.** `make`, `fraction.o`'yu yeniden derler (çünkü `fraction.c`'nin kuralında `fraction.h` hâlâ var), ama `main.o`'yu derlemez: `main.c` değişmedi ve `fraction.h` artık onun bağımlılığı değil. Sonuçta iki object file, `Fraction`'ın **iki farklı halini** varsayıyor: `main.o`'da `num` önce, `fraction.o`'da `den` önce. Program hiçbir hata vermeden derlenir ve çalışır, ama yanlış sonuç verir. Biz denedik:

```
6/1 + 4/3 = 22/3
```

`main`, `{1, 6}` yazarken 1'i paya koyduğunu sanıyor; `fraction.o` ise ilk alanı payda olarak okuyor. 1/6, 6/1 oldu. Bu, bulunması çok zor bir hatadır; derleme temiz geçtiği için kimse aklına getirmez. Header'ları bağımlılıklara eksiksiz yazmak bu yüzden önemli. Emin olamadığında `make clean` ve ardından `make`: her şeyi baştan derler.

**3.**
```c
#define ABS(x) ((x) < 0 ? -(x) : (x))
```
`ABS(x--)` açıldığında `((x--) < 0 ? -(x--) : (x--))` olur: `x` iki kez azalır ve sonuç da beklediğin değer olmaz. `MAX` örneğindeki tuzağın aynısı. Çözüm bir fonksiyon:

```c
int absolute(int x) {
    return x < 0 ? -x : x;
}
```

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §4.4–4.5: dış değişkenler ve header dosyaları; §4.6: `static`; §4.11: preprocessor, macro'lar ve koşullu ekleme.
- [GNU Make kılavuzu](https://www.gnu.org/software/make/manual/make.html), Bölüm 2: "An Introduction to Makefiles".

**Sıradaki ders:** Uyarılar ve undefined behavior. Derleyicinin uyarılarını ciddiye almayı ve C'nin en tehlikeli kavramını öğreneceğiz.
