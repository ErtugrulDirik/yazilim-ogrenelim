---
title: "2.12 scanf olmadan sayı okuma"
description: "getchar ile kendi read_int fonksiyonumuzu sıfırdan yazmak: karakteri rakama çevirmek, rakamlardan sayı kurmak, boşluk ve eksi işareti, hatalı girişi bildirmek ve overflow'dan korunmak."
---

Ders 2.11'de bir sayıyı karakterlere çevirip ekrana yazdık. Bu derste tersini yapacağız: klavyeden gelen karakterleri okuyup **sayıya** çevireceğiz. C'de bu işi normalde `scanf` yapar; biz onu kullanmadan, sadece `getchar` ile yazacağız.

Klavyeden okumak, ekrana yazmaktan daha zordur. Çünkü ekrana ne yazacağımızı biz biliriz, ama kullanıcının ne yazacağını bilemeyiz. Sayı yerine harf yazabilir, başına boşluk koyabilir, `int`'e sığmayacak kadar büyük bir sayı girebilir. İyi bir okuma fonksiyonu bunların hepsine hazırlıklı olmalıdır.

---

## 1. getchar'ı hatırla

Ders 2.4'teki labirent oyununda kullandık: `getchar()` klavyeden **bir karakter** okur ve onu bir sayı olarak (ASCII kodu) döndürür. Girdi bittiğinde ise özel bir değer döndürür: `EOF`.

Kullanıcı `2026` yazıp Enter'a bastığında, `getchar` art arda çağrıldıkça şu karakterleri verir: `'2'`, `'0'`, `'2'`, `'6'`, `'\n'`. İşimiz bu karakter dizisinden 2026 sayısını kurmak.

---

## 2. Karakteri rakama çevirmek

Ders 2.11'de rakamı karaktere çevirmek için `'0'` ekliyorduk. Tersi için çıkarırız:

| Karakter | ASCII | `c - '0'` |
| --- | --- | --- |
| `'0'` | 48 | 0 |
| `'2'` | 50 | 2 |
| `'6'` | 54 | 6 |
| `'9'` | 57 | 9 |

Bir karakterin rakam olup olmadığını da aynı sıralamadan anlarız: `'0'` ile `'9'` arasındaysa rakamdır.

```c
int is_digit(int c) {
    return c >= '0' && c <= '9';
}
```

---

## 3. Rakamlardan sayı kurmak

Rakamlar soldan sağa geliyor. Her yeni rakam geldiğinde, elimizdeki sayıyı bir basamak **sola kaydırıp** (10 ile çarpıp) yeni rakamı ekleriz. Ders 2.5'teki sayıyı ters çevirme probleminin aynı fikri:

```c
int value = 0;
int c = getchar();
while (is_digit(c)) {
    value = value * 10 + (c - '0');
    c = getchar();
}
```

`2026` için trace table:

| Okunan `c` | `c - '0'` | `value` |
| --- | --- | --- |
| — | — | 0 |
| `'2'` | 2 | 0 × 10 + 2 = 2 |
| `'0'` | 0 | 2 × 10 + 0 = 20 |
| `'2'` | 2 | 20 × 10 + 2 = 202 |
| `'6'` | 6 | 202 × 10 + 6 = 2026 |
| `'\n'` | — | rakam değil, dur |

---

## 4. Gerçek dünyaya hazırlık

Bu çekirdek fikir çalışıyor, ama gerçek bir kullanıcının girdisine dayanmaz. Üç şey eklememiz gerekiyor.

**Baştaki boşlukları atla.** Kullanıcı `   42` yazabilir; bir önceki satırdan kalan `'\n'` da okunmayı bekliyor olabilir. Rakamlara gelmeden önce boşlukları, tab'ları ve satır sonlarını geç.

**Eksi işaretini oku.** `-17` için önce `'-'` gelir. Onu görürsek not alırız ve sonucun işaretini en sonda çeviririz.

**Hatalı girişi bildir.** Kullanıcı `abc` yazarsa ne döndürmeliyiz? 0 döndürsek, gerçekten 0 yazan kullanıcıdan ayırt edemeyiz. -1 döndürsek, -1 yazan kullanıcıdan ayırt edemeyiz. **Hiçbir `int` değeri "okuyamadım" anlamına gelemez**, çünkü her `int` geçerli bir giriş olabilir.

Çözüm: iki değer döndürmek. Bir fonksiyon tek bir şey döndürebilir, ama o şey bir **struct** olabilir (Ders 2.3):

```c
struct ReadResult {
    int ok;
    int value;
};
```

`ok` 1 ise okuma başarılıdır ve sonuç `value`'dadır. `ok` 0 ise okuma başarısızdır ve `value`'ya bakmanın bir anlamı yoktur.

**State machine olarak.** Ders 1.3'teki son state machine alıştırmasını hatırla: metnin geçerli bir tamsayı olup olmadığına karar veren Başla, İşaret, Sayı ve Hata durumları. Şimdi yazacağımız fonksiyon tam olarak o makine:

- **Başla:** Boşlukları atla. `'-'` gelirse İşaret'e, rakam gelirse Sayı'ya, başka bir şey gelirse Hata'ya geç.
- **İşaret:** Rakam gelirse Sayı'ya, gelmezse Hata'ya geç.
- **Sayı:** Rakam geldikçe burada kal ve sayıyı kur. Rakam olmayan bir karakter gelince dur.

Kağıtta çizdiğin makine, şimdi gerçek bir programın parçası oluyor.

---

## 5. Overflow'dan korunmak

Kullanıcı `99999999999` yazarsa ne olur? `value * 10 + digit` bir noktada `INT_MAX`'ı aşar ve overflow olur. Ders 2.10'da gördüğümüz gibi sonuç belirsizdir; ama okuma fonksiyonu için en kötüsü, sessizce **yanlış** bir sayı döndürmesidir.

Çözüm: çarpmadan **önce** sonucun sığıp sığmayacağını sormak. Bilmek istediğimiz:

**value × 10 + digit ≤ INT_MAX**

Bu soruyu olduğu gibi sorarsak sol taraf hesaplanırken overflow olur. Ders 2.10'daki hileyi kullanalım ve soruyu bölmeyle soralım. Her iki taraftan `digit`'i çıkarıp 10'a bölünce:

**value ≤ (INT_MAX − digit) / 10**

Bu hesapta hiçbir şey taşmaz. Bu koşul sağlanmıyorsa, sayı `int`'e sığmayacak demektir; okuma başarısız olur.

---

## 6. read_int

Hepsi bir arada:

```c
#include <stdio.h>
#include <limits.h>

struct ReadResult {
    int ok;
    int value;
};

int is_space(int c) {
    return c == ' ' || c == '\t' || c == '\n';
}

int is_digit(int c) {
    return c >= '0' && c <= '9';
}

struct ReadResult read_int(void) {
    struct ReadResult result = {0, 0};
    int c = getchar();

    while (is_space(c)) {
        c = getchar();
    }

    int negative = 0;
    if (c == '-') {
        negative = 1;
        c = getchar();
    }

    if (!is_digit(c)) {
        return result;
    }

    int value = 0;
    while (is_digit(c)) {
        int digit = c - '0';
        if (value > (INT_MAX - digit) / 10) {
            return result;
        }
        value = value * 10 + digit;
        c = getchar();
    }

    result.ok = 1;
    result.value = negative ? -value : value;
    return result;
}

int main(void) {
    while (1) {
        struct ReadResult r = read_int();
        if (!r.ok) {
            printf("Okunamadı.\n");
            break;
        }
        printf("Okundu: %d\n", r.value);
    }
    return 0;
}
```

`main`, okunamayan bir şeyle karşılaşana kadar sayı okuyup yazıyor. Farklı girdilerle denedik:

| Girdi | Ekrana yazılan |
| --- | --- |
| `42` | Okundu: 42 |
| `  -17` sonra `305` | Okundu: -17, Okundu: 305 |
| `12 34 56` | Okundu: 12, Okundu: 34, Okundu: 56 |
| `2147483647` | Okundu: 2147483647 |
| `2147483648` | Okunamadı. |
| `abc` | Okunamadı. |
| `-` | Okunamadı. |

Her girdinin sonunda bir "Okunamadı." daha görürsün: girdi bitince `getchar` `EOF` döndürür, o da rakam değildir.

Aynı satırdaki birden fazla sayı da tek tek okunuyor: `12`'yi bitiren boşluk, bir sonraki çağrıda baştaki boşluk olarak atlanıyor.

**Programı denemek için** `F5` ile çalıştırıp alttaki terminale sayılar yazabilirsin. Bitirmek için `Ctrl+D` ile girdiyi kapat (Windows'ta WSL içinde de `Ctrl+D`). Girdiyi elle yazmak yerine terminalden hazır da verebilirsin:

```sh
printf '12 34 56\n' | ./build/faz-02/read
```

`|` işareti, soldaki komutun çıktısını sağdaki programın girdisine bağlar: program bu metni klavyeden yazılmış gibi okur. Aynı programı farklı girdilerle hızlıca denemenin pratik bir yolu.

---

## 7. Sayıyı bitiren karakter

Bir inceliğe dikkat: `7x` girersek ne olur?

Fonksiyon `'7'`'yi okur, sonra `'x'`'i okur. `'x'` rakam olmadığı için döngü biter ve 7 döndürülür. Ama `'x'` **okundu ve gitti**; bir sonraki `read_int` çağrısı onu göremez. Sayıyı bitiren karakter her zaman tüketilir.

Çoğu zaman bu bir sorun değil: sayıyı bitiren karakter genelde bir boşluk ya da satır sonudur. Ama sayıdan hemen sonra gelen karaktere ihtiyacın varsa sorun olur. Alıştırma 3'te bununla karşılaşacaksın.

---

## Alıştırmalar

**1. Toplama.** Kullanıcı 0 girene kadar sayı okuyup hepsinin toplamını yazdıran bir program yaz. Geçersiz bir giriş olursa "Geçersiz giriş" yazıp dursun.

**2. INT_MIN.** Yukarıdaki `read_int`, `-2147483648`'i okuyamıyor. Neden? Bunu da okuyabilen bir sürüm yaz. (İpucu: Ders 2.11'deki `print_int`'in çözümünü hatırla.)

**3. Hesap makinesi.** `12 + 30` gibi bir satırı okuyup sonucu yazdıran bir program yaz. İşlemler `+`, `-`, `*` ve `/` olsun. Sıfıra bölmeyi kontrol et. Programı `7*6` gibi boşluksuz bir girdiyle dene. Ne oluyor?

<details>
<summary>Cevaplar</summary>

**1.**
```c
int main(void) {
    int total = 0;
    while (1) {
        struct ReadResult r = read_int();
        if (!r.ok) {
            printf("Geçersiz giriş\n");
            return 1;
        }
        if (r.value == 0) {
            break;
        }
        total += r.value;
    }
    printf("Toplam: %d\n", total);
    return 0;
}
```

**2.** Fonksiyon sayıyı önce pozitif olarak kurup en sonda işaretini çeviriyor. Ama 2.147.483.648 bir `int`'e sığmaz; overflow kontrolü bu yüzden onu reddediyor. Ders 2.11'deki gibi çözüm: sayıyı **negatif tarafta** kurmak.

```c
struct ReadResult read_int(void) {
    struct ReadResult result = {0, 0};
    int c = getchar();
    while (is_space(c)) {
        c = getchar();
    }

    int negative = 0;
    if (c == '-') {
        negative = 1;
        c = getchar();
    }
    if (!is_digit(c)) {
        return result;
    }

    int value = 0;
    while (is_digit(c)) {
        int digit = c - '0';
        if (value < (INT_MIN + digit) / 10) {
            return result;
        }
        value = value * 10 - digit;
        c = getchar();
    }

    if (!negative) {
        if (value == INT_MIN) {
            return result;
        }
        value = -value;
    }
    result.ok = 1;
    result.value = value;
    return result;
}
```

Rakamları eklemek yerine **çıkarıyoruz**; `value` hep 0 ya da negatif. Overflow kontrolü de ters döndü: value × 10 − digit ≥ INT_MIN olmalı. Sonda, sayı pozitifse işaretini çeviriyoruz. Tek bir istisna var: değer tam `INT_MIN` ise ve eksi işareti yoksa, kullanıcı 2147483648 yazmış demektir ve bu sığmaz. Denedik: `-2147483648` okunuyor, `2147483648` ve `-2147483649` reddediliyor.

**3.**
```c
int read_operator(void) {
    int c = getchar();
    while (is_space(c)) {
        c = getchar();
    }
    return c;
}

int main(void) {
    struct ReadResult a = read_int();
    int op = read_operator();
    struct ReadResult b = read_int();
    if (!a.ok || !b.ok) {
        printf("Geçersiz sayı.\n");
        return 1;
    }
    switch (op) {
        case '+': printf("%d\n", a.value + b.value); break;
        case '-': printf("%d\n", a.value - b.value); break;
        case '*': printf("%d\n", a.value * b.value); break;
        case '/':
            if (b.value == 0) {
                printf("Sıfıra bölünemez.\n");
            } else {
                printf("%d\n", a.value / b.value);
            }
            break;
        default: printf("Bilinmeyen işlem.\n"); break;
    }
    return 0;
}
```

`12 + 30` → 42. Ama `7*6` → "Geçersiz sayı."! Bölüm 7'deki incelik: `read_int`, 7'yi bitiren `*` karakterini okuyup tüketti. `read_operator` çağrıldığında `*` artık yok; sıradaki karakter `6`. Operatör olarak `'6'` okunuyor, ardından ikinci sayı için hiçbir şey kalmıyor.

Çözüm: C'nin `getchar`'ın tersi olan bir fonksiyonu var: `ungetc`. Okuduğun karakteri girdiye **geri koyar**; bir sonraki `getchar` onu tekrar verir. `read_int`'te döngüden çıktıktan sonra şu satırı ekle:

```c
    ungetc(c, stdin);
```

Artık sayıyı bitiren karakter kaybolmuyor ve `7*6` → 42. (`stdin`, "standart girdi", yani klavye demektir.)

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.7 (`atoi`) ve §5.2 (`getint`): sayı okumanın kitaptaki halleri; `getint`, `ungetc`'nin kardeşi olan `ungetch`'i kullanır.

**Sıradaki ders:** Çok dosyalı program ve Make. `print_int` ve `read_int`'i her programa kopyalamak yerine ayrı bir dosyaya taşıyacağız.
