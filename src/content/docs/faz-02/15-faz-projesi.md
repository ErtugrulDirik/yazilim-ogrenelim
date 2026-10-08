---
title: "2.15 Faz projesi: sağlık hesaplayıcı"
description: "Faz 2'nin bitiş projesi: sadece int ve kendi print_int/read_int fonksiyonlarımızla, çok dosyalı, Makefile'lı, menülü bir sağlık hesaplayıcı."
---

Faz 2'nin sonuna geldin. Bu fazda bir programlama dilinin temel araçlarını, kendi giriş-çıkış fonksiyonlarını, programı dosyalara bölmeyi ve hataları yakalamayı öğrendin. Şimdi hepsini tek bir programda bir araya getireceksin: **menülü bir sağlık hesaplayıcı**.

Ders 0.1'den beri bizimle olan vücut kitle indeksi burada son halini alıyor. Faz 1'de kağıtta akış diyagramını çizmiştin, Ders 2.3'te ilk C halini yazmıştın. Şimdi gerçek bir programın parçası olacak.

:::tip[Önce kendin yaz]
Bu bir proje dersi. Gereksinimleri ve formülleri okuduktan sonra **kendi çözümünü yaz**. Bizim çözümümüz aşağıda, kapalı kutularda duruyor. Takıldığın yerde sadece ilgili dosyaya bak, hepsine birden değil. Bitirdikten sonra kendi çözümünü bizimkiyle karşılaştır; farklı ama doğru bir yol bulmuş olman çok olası.
:::

---

## 1. Gereksinimler

Program açıldığında bir menü gösterir:

```
=== Sağlık Hesaplayıcı ===

1) Vücut kitle indeksi
2) İdeal kilo
3) Günlük kalori ihtiyacı
0) Çıkış
Seçimin:
```

- **1:** Boy ve kilo sorar; vücut kitle indeksini **iki ondalık basamakla** (`22,85` gibi) ve hangi gruba girdiğini yazar.
- **2:** Boy ve cinsiyet sorar; ideal kiloyu yazar.
- **3:** Kilo, boy, yaş, cinsiyet ve hareket düzeyi sorar; günlük kalori ihtiyacını yazar.
- **0:** Programı bitirir.

Her hesaptan sonra menü tekrar gösterilir.

**Kurallar:**

1. **Sadece `int`.** Küsuratlı sayı yok (onları Faz 3'te göreceğiz).
2. **Sayıları kendi fonksiyonlarınla oku ve yaz:** Ders 2.11'deki `print_int` ve Ders 2.12'deki `read_int`. `printf`'i sadece sabit yazılar için kullan (`printf("Boyun (cm): ");` gibi); `%d` yok.
3. **Hatalı girişe dayanıklı ol.** Kullanıcı harf yazarsa ya da izin verilen aralığın dışında bir sayı girerse, program çökmeden aynı soruyu tekrar sorsun. İzin verilen aralıklar:
   - Boy: 100–250 cm
   - Kilo: 20–300 kg
   - Yaş: 10–100
   - Cinsiyet: 1 (erkek) ya da 2 (kadın)
   - Hareket düzeyi: 1–5
4. **Girdi kapanırsa düzgünce bit.** Kullanıcı herhangi bir soruda `Ctrl+D` ile girdiyi kapatırsa program sonsuz döngüye girmeden çıksın.
5. **Çok dosyalı ol** (Ders 2.13): giriş-çıkış fonksiyonları, hesaplama fonksiyonları ve menü ayrı dosyalarda dursun.
6. **`Makefile` ile derlensin**, `-Wall -Wextra -Werror` ile hiç uyarı vermesin ve sanitizer'larla (Ders 2.14) çalıştırıldığında hiçbir hata raporlamasın.

---

## 2. Formüller

**Vücut kitle indeksi** = kilo / boy², boy metre cinsinden. Sonucu iki ondalık basamakla göstermek istiyoruz, ama küsuratlı sayı kullanamıyoruz. Çözüm: sonucu **100 ile çarpılmış** bir tamsayı olarak tutmak. 22,85 yerine 2285. Boy santimetre olarak geldiği için:

vki × 100 = kilo × 1.000.000 / (boy × boy)

70 kg ve 175 cm için: 70.000.000 / 30.625 = **2285**. Yazdırırken `2285 / 100` = 22'yi, bir virgülü ve `2285 % 100` = 85'i yazarsın. Bu yönteme **sabit noktalı sayı** (fixed-point) denir: virgülün yeri sayının içinde değil, kafamızda sabittir. Ders 2.3'teki vücut kitle indeksi 22 çıkıyordu; artık 22,85.

Gruplar da 100 ile çarpılmış sınırlarla: 1850'nin altı zayıf; 2500'ün altı normal; 3000'in altı fazla kilolu; 3000 ve üstü obez.

**Overflow kontrolü:** En büyük kilo 300; 300 × 1.000.000 = 300.000.000. `INT_MAX` yaklaşık 2,1 milyar; sığıyor. Bu hesabı yapmadan büyük sayılarla çarpma yapma alışkanlığı edinme (Ders 2.14).

**İdeal kilo (Broca formülü):** Erkekler için (boy − 100) × %90, kadınlar için (boy − 100) × %85. 175 cm bir erkek için: 75 × 90 / 100 = **67** kg.

**Günlük kalori ihtiyacı (Mifflin-St Jeor formülü):** Önce bazal metabolizma hızı (BMH), yani vücudun hiçbir şey yapmadan harcadığı enerji:

- Erkek: 10 × kilo + 6,25 × boy − 5 × yaş + 5
- Kadın: 10 × kilo + 6,25 × boy − 5 × yaş − 161

6,25 küsuratlı. Yine 100 ile çarpılmış haliyle hesapla: 1000 × kilo + 625 × boy − 500 × yaş + 500, sonra 100'e böl.

Sonra BMH'yi hareket düzeyine göre bir katsayıyla çarp:

| Hareket düzeyi | Katsayı | × 1000 |
| --- | --- | --- |
| 1: çok az (masa başı) | 1,2 | 1200 |
| 2: az (haftada 1–3 gün spor) | 1,375 | 1375 |
| 3: orta (haftada 3–5 gün) | 1,55 | 1550 |
| 4: yüksek (haftada 6–7 gün) | 1,725 | 1725 |
| 5: çok yüksek (ağır iş ya da günde iki antrenman) | 1,9 | 1900 |

70 kg, 175 cm, 30 yaşında, orta hareketli bir erkek için: BMH = (70.000 + 109.375 − 15.000 + 500) / 100 = 1648; × 1550 / 1000 = **2554** kcal.

(Bu formüller genel bir tahmin verir; tıbbi bir değerlendirmenin yerini tutmaz.)

---

## 3. Tasarım

Kod yazmadan önce, Ders 2.4'teki labirentte yaptığımız gibi, programı parçalarına ayıralım:

| Dosya | Sorumluluğu | İçindekiler |
| --- | --- | --- |
| `io.h`, `io.c` | Sayı okumak ve yazmak | `print_int`, `print_fixed2`, `read_int` |
| `health.h`, `health.c` | Hesaplamalar | `bmi_x100`, `ideal_weight`, `daily_calories` |
| `main.c` | Kullanıcıyla konuşmak | menü, soruları sorma, sonuçları yazma |
| `Makefile` | Derleme | |

Neden bu ayrım? `health.c` hiçbir şey okumaz, hiçbir şey yazmaz; sadece hesap yapar. Formüllerden birinde hata varsa nereye bakacağın belli. `io.c` hiçbir sağlık bilgisi bilmez; başka bir projede olduğu gibi kullanılabilir. Her dosyanın **tek bir işi** var.

**`read_int`'i geliştirmek.** Ders 2.12'deki `read_int` iki şeyi ayırt edemiyor: kullanıcının yanlış bir şey yazması ile girdinin **bitmesi**. İkisinde de `ok` 0 oluyor. Ama bu projede ikisine farklı davranmamız gerekiyor: yanlış girişte soruyu tekrar sormalı, girdi bitince programdan çıkmalıyız. Yoksa girdi kapandığında program "lütfen geçerli bir sayı gir" diye sonsuza kadar sorar. Bu yüzden `ok` alanını üç değer alabilen bir `status` alanına çeviriyoruz: `READ_OK`, `READ_INVALID` ve `READ_EOF`.

İkinci bir geliştirme: kullanıcı `175abc` yazarsa, Ders 2.12'deki sürüm 175'i kabul edip `abc`'yi bir sonraki soruya bırakırdı. Bu projede **satırın tamamına** bakıyoruz: sayıdan sonra satır sonuna kadar boşluktan başka bir şey varsa giriş geçersizdir ve satırın geri kalanı atlanır.

İşte gerçek bir projede olan bu: dünkü kodun bugünkü ihtiyaca yetmez ve onu geliştirirsin. Ders 2.4'teki labirentte gördüğümüz çalışma biçimi.

**Soru sormak.** Her soru aynı kalıpta: bir sayı oku, aralıktaysa kabul et, değilse uyarıp tekrar sor, girdi bittiyse vazgeç. Bunu her soru için tekrar yazmak yerine bir fonksiyona koy: `int ask(int min, int max)`. Girdi biterse -1 döndürsün; bütün aralıklar 0 ya da daha büyük olduğu için -1 hiçbir zaman geçerli bir cevapla karışmaz.

---

## 4. Bizim çözümümüz

Proje klasörü `faz-02/health`. Her dosya ayrı bir kutuda.

<details>
<summary>io.h</summary>

```c
#ifndef IO_H
#define IO_H

#define READ_OK 1
#define READ_INVALID 0
#define READ_EOF -1

struct ReadResult {
    int status;
    int value;
};

void print_int(int n);
void print_fixed2(int value_x100);
struct ReadResult read_int(void);

#endif
```

</details>

<details>
<summary>io.c</summary>

```c
#include <stdio.h>
#include <limits.h>
#include "io.h"

static void print_negative(int n) {
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

void print_fixed2(int value_x100) {
    print_int(value_x100 / 100);
    putchar(',');
    int cents = value_x100 % 100;
    if (cents < 10) {
        putchar('0');
    }
    print_int(cents);
}

static int is_space(int c) {
    return c == ' ' || c == '\t';
}

static int is_digit(int c) {
    return c >= '0' && c <= '9';
}

static void skip_line(void) {
    int c = getchar();
    while (c != '\n' && c != EOF) {
        c = getchar();
    }
}

struct ReadResult read_int(void) {
    struct ReadResult result = {READ_INVALID, 0};
    int c = getchar();
    while (is_space(c)) {
        c = getchar();
    }
    if (c == EOF) {
        result.status = READ_EOF;
        return result;
    }
    int negative = 0;
    if (c == '-') {
        negative = 1;
        c = getchar();
    }
    int value = 0;
    int digits = 0;
    while (is_digit(c)) {
        int digit = c - '0';
        if (value > (INT_MAX - digit) / 10) {
            skip_line();
            return result;
        }
        value = value * 10 + digit;
        digits++;
        c = getchar();
    }
    while (is_space(c)) {
        c = getchar();
    }
    if (c != '\n' && c != EOF) {
        skip_line();
        return result;
    }
    if (digits == 0) {
        return result;
    }
    result.status = READ_OK;
    result.value = negative ? -value : value;
    return result;
}
```

`print_fixed2`, 2285'i `22,85` diye yazar. `cents < 10` kontrolü 2205'in `22,5` değil `22,05` diye yazılması için. `skip_line` ve karakter testleri `static`: dışarıya açılması gerekmeyen yardımcılar (Ders 2.13).

</details>

<details>
<summary>health.h</summary>

```c
#ifndef HEALTH_H
#define HEALTH_H

#define MALE 1
#define FEMALE 2

int bmi_x100(int weight_kg, int height_cm);
int ideal_weight(int height_cm, int sex);
int daily_calories(int weight_kg, int height_cm, int age, int sex, int activity);

#endif
```

</details>

<details>
<summary>health.c</summary>

```c
#include "health.h"

int bmi_x100(int weight_kg, int height_cm) {
    return weight_kg * 1000000 / (height_cm * height_cm);
}

int ideal_weight(int height_cm, int sex) {
    int base = height_cm - 100;
    if (sex == MALE) {
        return base * 90 / 100;
    }
    return base * 85 / 100;
}

int daily_calories(int weight_kg, int height_cm, int age, int sex, int activity) {
    int bmr_x100 = 1000 * weight_kg + 625 * height_cm - 500 * age;
    if (sex == MALE) {
        bmr_x100 += 500;
    } else {
        bmr_x100 -= 16100;
    }
    int factor_x1000;
    switch (activity) {
        case 1: factor_x1000 = 1200; break;
        case 2: factor_x1000 = 1375; break;
        case 3: factor_x1000 = 1550; break;
        case 4: factor_x1000 = 1725; break;
        default: factor_x1000 = 1900; break;
    }
    return bmr_x100 / 100 * factor_x1000 / 1000;
}
```

`daily_calories`'de önce 100'e bölüp sonra katsayıyla çarpıyoruz. Tersi de olurdu, ama ara sonucu küçük tutmak overflow riskini azaltır (Ders 2.9'daki EKOK'u hatırla).

</details>

<details>
<summary>main.c</summary>

```c
#include <stdio.h>
#include "io.h"
#include "health.h"

static int ask(int min, int max) {
    while (1) {
        struct ReadResult r = read_int();
        if (r.status == READ_EOF) {
            return -1;
        }
        if (r.status == READ_OK && r.value >= min && r.value <= max) {
            return r.value;
        }
        printf("Lütfen ");
        print_int(min);
        printf(" ile ");
        print_int(max);
        printf(" arasında bir sayı gir: ");
    }
}

static int show_bmi(void) {
    printf("Boyun (cm): ");
    int height = ask(100, 250);
    if (height < 0) {
        return 0;
    }
    printf("Kilon (kg): ");
    int weight = ask(20, 300);
    if (weight < 0) {
        return 0;
    }

    int bmi = bmi_x100(weight, height);
    printf("Vücut kitle indeksin: ");
    print_fixed2(bmi);
    if (bmi < 1850) {
        printf(" (zayıf)\n");
    } else if (bmi < 2500) {
        printf(" (normal)\n");
    } else if (bmi < 3000) {
        printf(" (fazla kilolu)\n");
    } else {
        printf(" (obez)\n");
    }
    return 1;
}

static int show_ideal_weight(void) {
    printf("Boyun (cm): ");
    int height = ask(100, 250);
    if (height < 0) {
        return 0;
    }
    printf("Cinsiyetin (1: erkek, 2: kadın): ");
    int sex = ask(MALE, FEMALE);
    if (sex < 0) {
        return 0;
    }

    printf("İdeal kilon: yaklaşık ");
    print_int(ideal_weight(height, sex));
    printf(" kg\n");
    return 1;
}

static int show_calories(void) {
    printf("Kilon (kg): ");
    int weight = ask(20, 300);
    if (weight < 0) {
        return 0;
    }
    printf("Boyun (cm): ");
    int height = ask(100, 250);
    if (height < 0) {
        return 0;
    }
    printf("Yaşın: ");
    int age = ask(10, 100);
    if (age < 0) {
        return 0;
    }
    printf("Cinsiyetin (1: erkek, 2: kadın): ");
    int sex = ask(MALE, FEMALE);
    if (sex < 0) {
        return 0;
    }
    printf("Hareket düzeyin (1: çok az, 2: az, 3: orta, 4: yüksek, 5: çok yüksek): ");
    int activity = ask(1, 5);
    if (activity < 0) {
        return 0;
    }

    printf("Günlük kalori ihtiyacın: yaklaşık ");
    print_int(daily_calories(weight, height, age, sex, activity));
    printf(" kcal\n");
    return 1;
}

int main(void) {
    printf("=== Sağlık Hesaplayıcı ===\n");
    int running = 1;
    while (running) {
        printf("\n1) Vücut kitle indeksi\n");
        printf("2) İdeal kilo\n");
        printf("3) Günlük kalori ihtiyacı\n");
        printf("0) Çıkış\n");
        printf("Seçimin: ");

        switch (ask(0, 3)) {
            case 1: running = show_bmi(); break;
            case 2: running = show_ideal_weight(); break;
            case 3: running = show_calories(); break;
            default: running = 0; break;
        }
    }
    printf("Görüşmek üzere!\n");
    return 0;
}
```

Her `show_...` fonksiyonu, girdi biterse 0, hesabı bitirirse 1 döndürüyor. `main` bu değeri `running`'e yazıyor; böylece girdinin bir sorunun ortasında kapanması da programı düzgünce bitiriyor. `ask(0, 3)` -1 döndürürse `switch`'in `default` dalına düşüyor ve program yine çıkıyor.

</details>

<details>
<summary>Makefile</summary>

```makefile
CC = clang
CFLAGS = -std=c17 -Wall -Wextra -Werror -g
BUILD = ../../build/faz-02/health
OBJS = $(BUILD)/main.o $(BUILD)/io.o $(BUILD)/health.o

$(BUILD)/health: $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $(BUILD)/health

$(BUILD)/main.o: main.c io.h health.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c main.c -o $(BUILD)/main.o

$(BUILD)/io.o: io.c io.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c io.c -o $(BUILD)/io.o

$(BUILD)/health.o: health.c health.h
	mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -c health.c -o $(BUILD)/health.o

run: $(BUILD)/health
	$(BUILD)/health

clean:
	rm -rf $(BUILD)

.PHONY: run clean
```

Ders 2.13'teki `Makefile`'ın aynısı, üç dosya için. `CFLAGS`'te bu sefer `-Werror` da var.

</details>

---

## 5. Çalıştırmak ve test etmek

```sh
cd faz-02/health
make run
```

Bir oturum (kalın yazılar kullanıcının yazdıkları):

<pre><code>=== Sağlık Hesaplayıcı ===

1) Vücut kitle indeksi
2) İdeal kilo
3) Günlük kalori ihtiyacı
0) Çıkış
Seçimin: <b>1</b>
Boyun (cm): <b>175</b>
Kilon (kg): <b>70</b>
Vücut kitle indeksin: 22,85 (normal)

1) Vücut kitle indeksi
2) İdeal kilo
3) Günlük kalori ihtiyacı
0) Çıkış
Seçimin: <b>2</b>
Boyun (cm): <b>175</b>
Cinsiyetin (1: erkek, 2: kadın): <b>1</b>
İdeal kilon: yaklaşık 67 kg

1) Vücut kitle indeksi
2) İdeal kilo
3) Günlük kalori ihtiyacı
0) Çıkış
Seçimin: <b>3</b>
Kilon (kg): <b>70</b>
Boyun (cm): <b>175</b>
Yaşın: <b>30</b>
Cinsiyetin (1: erkek, 2: kadın): <b>1</b>
Hareket düzeyin (1: çok az, 2: az, 3: orta, 4: yüksek, 5: çok yüksek): <b>3</b>
Günlük kalori ihtiyacın: yaklaşık 2554 kcal

1) Vücut kitle indeksi
2) İdeal kilo
3) Günlük kalori ihtiyacı
0) Çıkış
Seçimin: <b>5</b>
Lütfen 0 ile 3 arasında bir sayı gir: <b>abc</b>
Lütfen 0 ile 3 arasında bir sayı gir: <b>0</b>
Görüşmek üzere!
</code></pre>

**Hızlı test.** Her seferinde elle yazmak yerine girdiyi hazır ver (Ders 2.12):

```sh
printf '1\n175\n70\n0\n' | ../../build/faz-02/health/health
```

Kendi çözümünü en azından şu durumlarla dene:

- Bölüm 2'deki örnek değerler: 22,85, 67 kg ve 2554 kcal çıkmalı.
- Aralık dışı ve harfli girişler: `5`, `abc`, `175abc`. Program çökmemeli, aynı soruyu tekrar sormalı.
- Bir sorunun ortasında `Ctrl+D`: program "Görüşmek üzere!" deyip çıkmalı.
- En uç değerler: 300 kg ve 100 cm; 20 kg ve 250 cm. Sonuçlar mantıklı olmalı ve hiçbir hesap overflow olmamalı.

**Sanitizer'larla.** Son olarak programı sanitizer'larla derleyip aynı testleri tekrarla:

```sh
clang -std=c17 -Wall -Wextra -Werror -fsanitize=undefined,address main.c io.c health.c -o ../../build/faz-02/health/health-san
```

Bizim çözümümüzü en uç değerler dahil bu şekilde denedik; hiçbir sanitizer raporu çıkmadı.

---

## 6. Geliştirme önerileri

Proje çalışıyor. Bitmiş mi? Gerçek yazılımlar hiç bitmez. Kendini denemek istersen:

1. **Hedef kilo.** Vücut kitle indeksi "fazla kilolu" ya da "obez" çıkarsa, normal gruba girmek için en fazla kaç kilo olunması gerektiğini de yazdır. (İpucu: vki × 100 = 2499 olacak şekilde kiloyu bul; formülü kilo için tersine çevir.)
2. **Su ihtiyacı.** Menüye dördüncü bir seçenek ekle: günlük su ihtiyacı, kilo başına 35 ml. Sonucu litre cinsinden, `print_fixed2` ile iki ondalıkla yaz (70 kg → 2,45 litre). Hangi dosyalara dokunman gerekti?
3. **Son sonuçlar.** Program, o oturumda hesaplanan son 5 vücut kitle indeksini bir array'de tutsun ve menüye "geçmişi göster" seçeneği eklensin. Array dolunca en eskisi silinsin.

---

## Faz 2 bitti

Bu fazın başında bilgisayarın sana `Hello, world!` yazmasını sağlamıştın. Şimdi:

- değişkenler, kararlar, döngüler, fonksiyonlar, struct'lar ve array'lerle program yazabiliyorsun,
- `printf` ve `scanf`'in yaptığı işi kendin yapabiliyorsun,
- programını dosyalara bölüp Make ile derleyebiliyorsun,
- hataları debugger, uyarılar ve sanitizer'larla avlayabiliyorsun.

Ve bunların hepsini **sadece `int`** ile yaptın. Vücut kitle indeksindeki o virgülden sonraki iki rakamı göstermek için bile sabit noktalı sayı hilesine başvurmak zorunda kaldın. Bilgisayar küsuratlı sayıları nasıl tutuyor? `int`'in sınırları nereden geliyor, `INT_MIN` neden `INT_MAX`'tan bir fazla? 0,1 neden tam olarak saklanamıyor?

**Sıradaki faz:** Veri tipleri. Bu soruların hepsinin cevabı orada.
