---
title: "3.8 Taşma"
description: "İşaretsiz tiplerde başa dönen (tanımlı) aritmetik ve işaretli tiplerde undefined behavior olan taşma; taşmayı sonradan kontrol etmenin neden işe yaramadığı, önceden kontrol eden checked_add ve checked_mul, __builtin_add_overflow, C23'teki ckd_add ve taşmayı yakalayan araçlar."
---

2014'te YouTube, Gangnam Style videosunun izlenme sayısının 2.147.483.647'yi, yani `INT_MAX`'ı geçmek üzere olduğunu duyurdu ve sayacı 64 bitlik bir tamsayıya çevirdi. Bir yıl sonra ABD Federal Havacılık İdaresi, Boeing 787 uçakları için bir uyarı yayımladı: elektrik sistemini yöneten yazılım, 248 gün kesintisiz açık kalırsa bütün jeneratörleri kapatabiliyordu. 248 gün, saniyenin yüzde biri cinsinden yaklaşık 2³¹: işaretli 32 bitlik bir sayacın sınırı.

Faz 2'den beri taşmayla birkaç kez karşılaştık: 13! (Ders 2.8), asal testindeki `d * d` (Ders 2.10), `x + 1 > x`'in `-O2` ile her zaman doğru çıkması (Ders 2.12), Ders 3.3'te 0'dan 1 çıkınca 4.294.967.295'e dönen sayaç. Ders 3.3'te bir söz vermiştik: taşmayı **olmadan önce** yakalamak. Bu dersin konusu bu.

---

## 1. İki farklı dünya

C'de taşma, tipin işaretli olup olmamasına göre iki bambaşka şeydir.

**İşaretsiz tiplerde taşma tanımlıdır.** Sonuç 2ⁿ'e göre hesaplanır, yani sayaç gibi başa döner. Ders 3.7'deki Kural 2'nin aritmetik hali. Bu bir hata değil, standardın verdiği bir **söz**; bu yüzden işe yarar şekillerde kullanılabilir. Bir örnek: zamanı milisaniye cinsinden sayan 32 bitlik bir sayaç yaklaşık 49,7 günde bir başa döner. Geçen süreyi hesaplarken bu bir sorun mu?

```c
#include <stdio.h>
#include <stdint.h>

int main(void) {
    uint32_t start = 4294967000u;
    uint32_t now = 200;
    uint32_t elapsed = now - start;
    printf("%u\n", elapsed);
    return 0;
}
```

```
496
```

Sayaç 4.294.967.000'deyken ölçüme başladık; o arada sayaç başa döndü ve şimdi 200'de. Gerçekte geçen süre: 4.294.967.296'ya kadar 296, sonra 200 daha, toplam **496**. `now - start` matematikte negatif, ama işaretsiz aritmetikte başa dönme tam olarak doğru cevabı verdi. Bu yüzden zaman ve sıra numarası sayaçları neredeyse her zaman işaretsizdir.

**İşaretli tiplerde taşma undefined behavior'dır** (Ders 2.12). Sonuç "başa dönmüş bir sayı" bile değildir; compiler taşmanın hiç olmayacağını varsayar ve kodu buna göre derler. Bunun en tehlikeli sonucunu bir sonraki bölümde göreceğiz.

Bir de Ders 3.5'teki tuzağı unutma: `int`'ten küçük işaretsiz tipler (`uint8_t`, `uint16_t`) hesaptan önce `int`'e yükseltilir. `uint16_t` ile yaptığın bir çarpma, aslında **işaretli** bir `int` çarpmasıdır ve taşarsa undefined behavior olur.

---

## 2. Sonradan kontrol etmek işe yaramaz

İşaretsiz sayılarda taşmayı toplamadan sonra yakalamak kolay: başa dönen bir toplam, toplananlardan küçük olur.

```c
uint32_t a = 4000000000u;
uint32_t b = 500000000u;
uint32_t sum = a + b;
if (sum < a) {
    printf("taşma\n");
}
```

4.500.000.000, 2³²'den büyük; `sum` 205.032.704 olur ve `sum < a` doğrudur. Bu kontrol doğru çalışır, çünkü işaretsiz taşmanın sonucu tanımlıdır.

Aynı fikri işaretli sayılara uygulayalım: iki pozitif sayının toplamı, toplananlardan küçükse taşma olmuştur.

```c
#include <stdio.h>
#include <limits.h>

int add_overflows(int a, int b) {
    return b > 0 && a + b < a;
}

int main(void) {
    printf("%d\n", add_overflows(INT_MAX, 1));
    printf("%d\n", add_overflows(5, 1));
    return 0;
}
```

| Ayar | `add_overflows(INT_MAX, 1)` | `add_overflows(5, 1)` |
| --- | --- | --- |
| `-O0` | 1 | 0 |
| `-O2` | **0** | 0 |

`-O2` ile taşmayı **yakalayamadı**. Compiler'ın ürettiği kod (x86-64):

```asm
add_overflows:
        xor     eax, eax
        ret
```

`xor eax, eax`, `eax`'i sıfırlar. Fonksiyon, parametrelerine hiç bakmadan **0 döndürüyor**. Compiler'ın mantığı Ders 2.12'deki ile aynı: "`b > 0` ise `a + b`, taşma olmadığı sürece `a`'dan büyüktür. Taşma undefined behavior'dır, doğru bir programda olmaz. O halde `a + b < a` hiçbir zaman doğru değildir." Ve kontrolü sildi.

Burada bir ders var: taşmayı kontrol etmek için yazdığın kod da taşmaya dayanıyorsa, compiler o kontrolü yok sayabilir. İşaretli sayılarda taşmayı **olduktan sonra** değil, **olmadan önce** yakalamak zorundayız.

(`-fwrapv` ayarı compiler'a "işaretli taşmayı da başa dönen, tanımlı bir işlem say" der; o zaman bu fonksiyon `-O2` ile de doğru çalışır. Ama bu, kodunun sadece bu ayarla doğru olması demek. Ayarı bilmeyen biri kodunu derlediğinde hata geri döner.)

---

## 3. Önceden kontrol etmek

Fikir: işlemi yapmadan, sonucun sığıp sığmayacağını **sığdığı bilinen** sayılarla hesaplamak.

### Toplama

`a + b > INT_MAX` kontrolü yazamayız, çünkü `a + b` zaten taşar. Ama eşitsizliğin iki tarafından `b`'yi çıkarırsak:

> `b` pozitifse: `a + b > INT_MAX` ⟺ `a > INT_MAX − b`

`b` pozitif olduğu için `INT_MAX − b` hiçbir zaman taşmaz. Negatif `b` için aynı şeyi alt sınırla yaparız:

> `b` negatifse: `a + b < INT_MIN` ⟺ `a < INT_MIN − b`

`b` negatif olduğu için `INT_MIN − b`, `INT_MIN`'den büyük bir sayıdır ve taşmaz.

Sonucu ve taşma olup olmadığını birlikte döndürmek için Ders 2.13'teki `ReadResult` gibi bir struct kullanalım:

```c
#include <stdio.h>
#include <limits.h>

struct CheckedInt {
    int ok;
    int value;
};

struct CheckedInt checked_add(int a, int b) {
    struct CheckedInt result = {0, 0};
    if (b > 0 && a > INT_MAX - b) {
        return result;
    }
    if (b < 0 && a < INT_MIN - b) {
        return result;
    }
    result.ok = 1;
    result.value = a + b;
    return result;
}

void show(struct CheckedInt r) {
    if (r.ok) {
        printf("%d\n", r.value);
    } else {
        printf("taşma\n");
    }
}

int main(void) {
    show(checked_add(2000000000, 100000000));
    show(checked_add(2000000000, 200000000));
    show(checked_add(-2000000000, -200000000));
    show(checked_add(INT_MIN, -1));
    show(checked_add(INT_MAX, INT_MIN));
    return 0;
}
```

```
2100000000
taşma
taşma
taşma
-1
```

`-fsanitize=undefined` ile çalıştırdık; hiçbir rapor yok, çünkü taşacak hiçbir işlem yapılmadı. Son satır, Ders 3.3'teki kuralı hatırlatıyor: farklı işaretli iki sayının toplamı asla taşmaz. `b` 0 ise de iki koşul da yanlıştır ve toplama yapılır.

### Çarpma

Çarpmada iki yol var.

**Daha geniş bir tiple hesaplamak.** İki 32 bitlik sayının çarpımı her zaman 64 bite sığar (en büyüğü yaklaşık 2⁶²). Önce `int64_t` ile çarp, sonra sonucun `int`'e sığıp sığmadığına bak:

```c
#include <stdint.h>

struct CheckedInt checked_mul(int a, int b) {
    struct CheckedInt result = {0, 0};
    int64_t wide = (int64_t)a * b;
    if (wide > INT_MAX || wide < INT_MIN) {
        return result;
    }
    result.ok = 1;
    result.value = (int)wide;
    return result;
}
```

| Çağrı | Sonuç |
| --- | --- |
| `checked_mul(46340, 46340)` | 2147395600 |
| `checked_mul(46341, 46341)` | taşma |
| `checked_mul(-65536, 32768)` | −2147483648 |

Ders 2.10'daki `d * d`: 46.341², `INT_MAX`'ı geçen ilk kare. Son satırdaki sonuç tam olarak `INT_MIN`; sığıyor. `(int64_t)a * b` yazarken Ders 3.7'deki öncelik kuralını kullandık: cast çarpmadan önce uygulanıyor. Sondaki `(int)wide` cast'i de sınırları kontrol ettikten sonra yapılıyor; değeri değiştirmeyeceğini biliyoruz.

Bu yol, 64 bitlik sayılar için işe yaramaz: `int64_t`'den büyük standart bir tip yok. O zaman toplamadaki gibi bölmeyle kontrol etmek gerekir (`a > INT64_MAX / b` gibi). İşaret kombinasyonlarıyla birlikte dört ayrı durum çıkar; 5. alıştırmada deneyeceksin.

### Bölme

Bölme sonucu küçültür, ama iki tuzağı var:

- **Sıfıra bölme**: undefined behavior.
- **`INT_MIN / -1`**: Sonuç +2.147.483.648 olmalı; bu `int`'e sığmaz. Ders 3.3'teki asimetri yine karşımızda: `-INT_MIN` sığmıyordu, bu da onun kardeşi.

İkincisinin sonucu, makineye göre değişir. Bilgisayarımızda (ARM) sanitizer bir rapor verip −2.147.483.648 yazdırdı. Aynı programı x86-64 için derleyip çalıştırdığımızda ise program **çöktü**: x86'nın bölme komutu sonucun sığmadığını görünce işlemciyi durduruyor ve işletim sistemi programı bitiriyor (`floating point exception`; adına rağmen bir tamsayı hatası).

```c
struct CheckedInt checked_div(int a, int b) {
    struct CheckedInt result = {0, 0};
    if (b == 0 || (a == INT_MIN && b == -1)) {
        return result;
    }
    result.ok = 1;
    result.value = a / b;
    return result;
}
```

---

## 4. Compiler'ın yardımı: __builtin_add_overflow

Bu kontrolleri her seferinde elle yazmak yorucu ve hata yapmaya açık. clang ve GCC bu iş için hazır fonksiyonlar sunar:

```c
int sum;
if (__builtin_add_overflow(a, b, &sum)) {
    // taşma oldu; sum'daki değere güvenme
}
```

- `__builtin_add_overflow`, `__builtin_sub_overflow`, `__builtin_mul_overflow`: toplama, çıkarma, çarpma.
- Sonuç üçüncü parametreye yazılır. Ders 2.13'teki `scanf` gibi, değişkenin önündeki `&` işareti fonksiyonun sonucu **değişkenin içine** yazabilmesi için gerekiyor; ne anlama geldiğini Faz 4'te göreceğiz.
- Taşma olursa 1, olmazsa 0 döndürür. Sonucun tipini üçüncü parametrenin tipi belirler; `a` ve `b`'nin tipleri farklı olabilir.

Ders 2.8'deki faktöriyeli düşün. 13!'in sığmadığını, onu hesaplamadan söyleyebiliriz:

```c
#include <stdio.h>

int main(void) {
    int result = 1;
    for (int n = 1; n <= 20; n++) {
        int next;
        if (__builtin_mul_overflow(result, n, &next)) {
            printf("%d! int'e sığmıyor\n", n);
            break;
        }
        result = next;
        printf("%d! = %d\n", n, result);
    }
    return 0;
}
```

```
...
11! = 39916800
12! = 479001600
13! int'e sığmıyor
```

### Makinede ne oluyor?

Ders 3.3'te işlemcinin her toplamadan sonra overflow'u ayrı bir **bayrakta** not ettiğini söylemiştik. Builtin, tam olarak o bayrağı kullanır. Şu fonksiyonu `-O2` ile derleyelim:

```c
int add_or_zero(int a, int b) {
    int sum;
    if (__builtin_add_overflow(a, b, &sum)) {
        return 0;
    }
    return sum;
}
```

x86-64:

```asm
add_or_zero:
        xor     eax, eax
        add     edi, esi
        cmovno  eax, edi
        ret
```

ARM64:

```asm
add_or_zero:
        adds    w8, w0, w1
        csel    w0, wzr, w8, vs
        ret
```

- x86: `add` toplar ve bayrakları ayarlar. `cmovno` (conditional move if **n**o **o**verflow), overflow bayrağı kapalıysa toplamı sonuca taşır; açıksa sonuç 0 kalır.
- ARM: `adds`'teki `s`, "bayrakları ayarla" demek. `csel ... vs`, overflow bayrağı (**v**) açıksa (**s**et) 0'ı, değilse toplamı seçer.

Elle yazdığımız `checked_add` iki karşılaştırma yapıyordu; burada toplama ve bir bayrak kontrolü var, o kadar. Taşmayı yakalamanın neredeyse bedava olduğu ortada.

### C23: ckd_add

C23 standardı aynı fikri `<stdckdint.h>` başlığıyla standartlaştırdı:

```c
#include <stdckdint.h>

int r;
if (ckd_add(&r, a, b)) {
    // taşma
}
```

`ckd_add`, `ckd_sub`, `ckd_mul`. Tek fark parametre sırası: sonuç **başta**. clang bunu destekliyor; derlerken `-std=c23` kullanabilirsin. Taşınabilir kod yazarken builtin yerine bunu tercih et.

---

## 5. Taşmayı bulmak

| Araç | Ne yapar? |
| --- | --- |
| `-fsanitize=undefined` | İşaretli taşmayı, `INT_MIN / -1`'i ve sıfıra bölmeyi çalışma sırasında raporlar (Ders 2.12). |
| `-fsanitize=unsigned-integer-overflow` | İşaretsiz taşmayı da raporlar. Tanımlı bir davranış olduğu için `undefined`'a dahil değil; bilerek başa dönen kodda (Bölüm 1'deki sayaç gibi) yanlış alarm verir. clang'e özel. |
| `-fsanitize=implicit-conversion` | Taşmanın atamada olduğu durumları yakalar (Ders 3.7). |
| `-fwrapv` | İşaretli taşmayı başa dönen, tanımlı bir işlem yapar. Hatayı bulmaz, sadece compiler'ın onu kullanmasını engeller. |

Bölüm 1'deki sayaç programını `-fsanitize=unsigned-integer-overflow` ile çalıştırınca:

```
uns.c:6:28: runtime error: unsigned integer overflow: 200 - 4294967000 cannot be represented in type 'uint32_t' (aka 'unsigned int')
```

Program yine 496 yazdırır. Rapor doğru: başa dönme oldu. Ama bu sefer bilerek yaptık.

**Kurallar:**

1. Bir hesabın taşıp taşamayacağını, Ders 2.13'teki vücut kitle indeksinde yaptığımız gibi **en uç değerlerle** önceden düşün.
2. Taşabiliyorsa daha geniş bir tip kullan (Ders 3.4), ya da işlemi önceden kontrol et: `ckd_add` / `__builtin_add_overflow`.
3. İşaretli bir taşmayı sonradan kontrol etmeye çalışma.
4. Testleri `-fsanitize=undefined` ile çalıştır.

---

## Alıştırmalar

**1** – `checked_sub(int a, int b)`'yi yaz: `a - b` taşacaksa `ok` 0 olsun. `checked_sub(0, INT_MIN)` ne döndürmeli?

**2** – Ders 2.10'daki ikili aramada orta noktayı `mid = (low + high) / 2` diye hesaplamak klasik bir hatadır. `low` = 2.000.000.000 ve `high` = 2.100.000.000 için ne olur? Taşmayan bir formül yaz.

**3** – Mutlak değer fonksiyonu:

```c
int absolute(int x) {
    return x < 0 ? -x : x;
}
```

Bu fonksiyonun taştığı tek bir girdi var. Hangisi? `-fsanitize=undefined` ne diyor? Fonksiyonun dönüş tipini değiştirerek bu sorunu nasıl çözersin?

**4** – Bölüm 1'deki milisaniye sayacı: ölçüme başlarken sayaç 4.294.967.000'deydi. Şimdi 1.000'de. Ama arada sayaç bir tur **daha** döndü (yaklaşık 50 gün geçti). `now - start` kaç verir? Bu yöntem hangi koşulda doğru çalışır?

**5** – `checked_mul`'u `int64_t` için yaz. Daha büyük bir tip olmadığı için bölmeyle kontrol etmen gerekecek. (İpucu: `a` ile `b`'nin işaretlerine göre dört durum var; `a` ya da `b` 0 ise taşma olmaz.) Ya da `__builtin_mul_overflow` ile tek satırda yaz.

<details>
<summary>Cevaplar</summary>

**1** –

```c
struct CheckedInt checked_sub(int a, int b) {
    struct CheckedInt result = {0, 0};
    if (b < 0 && a > INT_MAX + b) {
        return result;
    }
    if (b > 0 && a < INT_MIN + b) {
        return result;
    }
    result.ok = 1;
    result.value = a - b;
    return result;
}
```

`a - b > INT_MAX` ⟺ `a > INT_MAX + b` (`b` negatifken `INT_MAX + b` taşmaz). Aynı şekilde `b` pozitifken `INT_MIN + b` taşmaz. `checked_sub(0, INT_MIN)` taşma döndürmeli: 0 − (−2.147.483.648) = 2.147.483.648, `INT_MAX`'tan bir fazla. `checked_add(a, -b)` yazmak cazip ama yanlış: `b` `INT_MIN` ise `-b` zaten taşar.

**2** – `low + high` = 4.100.000.000, `INT_MAX`'ı geçer: undefined behavior. Bilgisayarımızda `-fsanitize=undefined` taşmayı raporladı ve `mid` olarak **−97.483.648** çıktı; negatif bir indeks. Doğrusu:

```c
int mid = low + (high - low) / 2;
```

`low <= high` olduğu sürece `high - low` negatif olmaz ve taşmaz; `low`'a eklenen değer de `high - low`'dan küçük olduğu için sonuç `high`'ı geçmez. Sonuç **2.050.000.000**. (Bu hata, Java'nın standart kütüphanesindeki ikili aramada yaklaşık dokuz yıl fark edilmeden kaldı; 2006'da düzeltildi.)

**3** – `INT_MIN`. `-INT_MIN` sığmaz. Sanitizer: `negation of -2147483648 cannot be represented in type 'int'; cast to an unsigned type to negate this value to itself`. Sonucu `unsigned int` olarak döndürmek sorunu çözer, çünkü her `int`'in mutlak değeri `unsigned int`'e sığar:

```c
unsigned int absolute(int x) {
    if (x < 0) {
        return 0u - (unsigned int)x;
    }
    return (unsigned int)x;
}
```

`(unsigned int)x`, `INT_MIN` için 2.147.483.648 olur (Ders 3.7, Kural 2); `0u - 2147483648u` da işaretsiz aritmetikte yine 2.147.483.648. Bütün işlemler işaretsiz, hiçbiri undefined değil.

**4** – **1.296.** Gerçekte geçen süre bundan 2³² ms (≈ 49,7 gün) fazla, ama `uint32_t`'nin bunu bilmesinin yolu yok: tam bir turu göremez. Yöntem, iki ölçüm arasındaki süre sayacın bir turundan **kısa** olduğu sürece doğrudur. Daha uzun süreleri ölçmen gerekiyorsa daha geniş bir sayaç (`uint64_t`) kullan.

**5** – Builtin ile:

```c
int64_t result;
int overflow = __builtin_mul_overflow(a, b, &result);
```

Elle (`a` ve `b` `int64_t`, `<stdint.h>`'teki `INT64_MAX` ve `INT64_MIN` ile):

```c
int mul_overflows(int64_t a, int64_t b) {
    if (a == 0 || b == 0) {
        return 0;
    }
    if (a > 0) {
        if (b > 0) {
            return a > INT64_MAX / b;
        }
        return b < INT64_MIN / a;
    }
    if (b > 0) {
        return a < INT64_MIN / b;
    }
    return a < INT64_MAX / b;
}
```

Dört durumda da bölme taşmaz: bölen hiçbir zaman −1 ile birlikte `INT64_MIN` olmuyor. Örneğin iki negatif sayıda `INT64_MAX / b` hesaplanıyor; `INT64_MAX` pozitif olduğu için sorun yok. Builtin'in değeri burada çok açık: tek satır ve hata yapacak yer yok.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §6.2.5¶9: işaretsiz aritmetik taşmaz, 2ⁿ'e göre hesaplanır; §6.5¶5: sonucu tipine sığmayan işlem undefined behavior'dır. C23 (ISO/IEC 9899:2024), §7.20: `<stdckdint.h>`.
- SEI CERT C Coding Standard, INT30-C ve INT32-C: işaretsiz ve işaretli taşmayı önlemek.
- [Clang belgesi: Checked Arithmetic Builtins](https://clang.llvm.org/docs/LanguageExtensions.html#checked-arithmetic-builtins).
- Joshua Bloch, "Extra, Extra – Read All About It: Nearly All Binary Searches and Mergesorts are Broken", Google Research Blog, 2006.
- FAA, Airworthiness Directive 2015-09-07 (Boeing 787 elektrik sistemi).

**Sıradaki ders:** Endianness. Çok byte'lık bir sayının byte'ları bellekte hangi sırayla duruyor?
