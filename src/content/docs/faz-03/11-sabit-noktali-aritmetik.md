---
title: "3.11 Sabit noktalı aritmetik"
description: "Küsuratlı sayıları tamsayılarla tutmak: ölçek fikri, ondalık ölçekten ikilik ölçeğe, Q16.16 biçimi; dönüştürme, toplama, çarpma ve bölmenin kuralları, aralık ve hassasiyet sınırları ve vücut kitle indeksini Q16.16 ile yeniden hesaplamak."
---

Ders 2.13'teki sağlık hesaplayıcısında küsuratlı sayı kullanamıyorduk, ama vücut kitle indeksini `22,85` diye iki ondalıkla göstermek istiyorduk. Çözümümüz basitti: sayıyı **100 ile çarpılmış** bir tamsayı olarak tutmak. 22,85 yerine 2285. Ders 3.1'de buna "elle yaptığımız bir şey" demiş ve bu derste onu düzenli bir biçime sokacağımızı söylemiştik.

Bu dersin konusu, o hilenin arkasındaki genel fikir: **sabit noktalı sayılar** (fixed-point numbers). Bilgisayarın küsuratlı sayılar için kullandığı asıl yöntemi (float) Ders 3.12'de göreceğiz; ama sabit noktalı sayılar bugün de para hesaplarında, ses işlemede, kayan nokta birimi olmayan küçük işlemcilerde ve eski oyunlarda kullanılıyor. 1993'te çıkan Doom, bütün 3B hesaplarını bu dersteki Q16.16 biçimiyle yaptı.

---

## 1. Ölçek fikri

Sabit noktalı bir sayı, bir tamsayı ve kafamızda tuttuğumuz bir **ölçekten** (scale) oluşur:

> gerçek değer = saklanan tamsayı / ölçek

Ders 2.13'te ölçek 100'dü: 2285 saklıyorduk, 2285 / 100 = 22,85 demek istiyorduk. Virgülün yeri sayının içinde değil, **ölçekte** sabit; adı da buradan geliyor.

Ölçek ne kadar büyükse virgülden sonra o kadar çok basamak tutabiliriz, ama o kadar küçük sayılar sığar:

| Ölçek | Saklanan | Gerçek değer | En küçük adım | `int32_t` ile en büyük değer |
| --- | --- | --- | --- | --- |
| 1 | 22 | 22 | 1 | 2.147.483.647 |
| 100 | 2285 | 22,85 | 0,01 | 21.474.836,47 |
| 10.000 | 228571 | 22,8571 | 0,0001 | 214.748,3647 |

32 bit sabit. Ölçeği büyütmek, bitlerin bir kısmını tam kısımdan alıp küsurata vermek demek. Ders 3.1'deki cümleyi hatırla: "22,86'yı gösterebilmek için bitlerin bir kısmını virgülden sonrasına ayırmamız gerekir."

### Ondalık ölçek: para

Ölçeğin 10'un kuvveti olması, sayıları insanların okuduğu gibi tutar. En önemli kullanım alanı **para**: 149,90 TL'yi 14990 kuruş olarak saklamak. Kuruş bir tamsayıdır; toplama, çıkarma ve karşılaştırma tam olarak doğru sonuç verir. Ders 3.12'de 0,1'in float ile tam olarak saklanamadığını göreceğiz; bu yüzden ciddi hiçbir finans yazılımı parayı float ile tutmaz.

### İkilik ölçek: Q biçimi

Ölçek 2'nin bir kuvveti olunca bitlerle düşünmek kolaylaşır. Ölçek 2¹⁶ = 65.536 olsun: 32 bitlik sayının sağdaki 16 biti virgülden sonrası, soldaki 16 biti (işaret dahil) tam kısım.

```
  tam kısım (16 bit)   küsurat (16 bit)
  00000000 00010110 , 11011011 01101101
```

Bu biçime **Q16.16** denir: 16 bit tam kısım, 16 bit küsurat. ("Q" bu gösterimin geleneksel adı; Q8.8, Q1.15 gibi başka bölüşümler de var.)

| Özellik | Q16.16 (`int32_t` içinde) |
| --- | --- |
| Ölçek | 2¹⁶ = 65.536 |
| En küçük adım | 1 / 65.536 ≈ 0,0000153 |
| En büyük değer | 32.767,99998… (`INT32_MAX` / 65.536) |
| En küçük değer | −32.768 (`INT32_MIN` / 65.536) |
| 1,0 | 65.536 |
| 0,5 | 32.768 |
| 1,5 | 98.304 |

Hassasiyet çok iyi: virgülden sonra yaklaşık 4–5 ondalık basamak. Bedeli **aralık**: 32.768'den büyük bir sayı tutamazsın. Bunu aklında tut; Bölüm 5'te bize sorun çıkaracak.

---

## 2. Dönüştürmek

Bütün fonksiyonları bir yere toplayalım. Ölçeği bir sabite koyuyoruz:

```c
#include <stdio.h>
#include <stdint.h>

#define FX_ONE 65536

int32_t fx_from_int(int n) {
    return n * FX_ONE;
}

int32_t fx_from_ratio(int num, int den) {
    return (int32_t)((int64_t)num * FX_ONE / den);
}

int fx_to_int(int32_t x) {
    return x / FX_ONE;
}
```

- `fx_from_int`: tamsayıyı ölçekle çarp. 3 → 196.608. `n`'in −32.768 ile 32.767 arasında olması gerekir; yoksa çarpma taşar (Ders 3.8).
- `fx_from_ratio`: küsuratlı bir sabiti iki tamsayının oranı olarak veriyoruz: 1,75 = `fx_from_ratio(175, 100)`, 1,5 = `fx_from_ratio(3, 2)`. Çarpma `int64_t` ile yapılıyor, çünkü `num * 65536` kolayca `int`'i aşar (Ders 3.5).
- `fx_to_int`: ölçeğe bölüp küsuratı atıyor. Dikkat: C'de bölme **sıfıra doğru** yuvarlar; `fx_to_int` −1,5 için −1 verir, −2 değil.

Yazdırmak için tam kısmı ve küsuratı ayırıp, küsuratı 4 ondalık basamağa çeviriyoruz:

```c
void fx_print(int32_t x) {
    if (x < 0) {
        putchar('-');
        x = -x;
    }
    int whole = x / FX_ONE;
    int frac = x % FX_ONE;
    int digits = (int)((int64_t)frac * 10000 / FX_ONE);
    printf("%d,%04d", whole, digits);
}
```

`frac` 0 ile 65.535 arasında; bunu 0–9.999 arasına ölçekliyoruz: `frac * 10000 / 65536`. `%04d`, Ders 2.13'teki `%02d` gibi başa sıfır koyar: 0,05 `0,0500` olarak görünür, `0,500` değil. Negatif sayılar için önce işareti yazıp sayıyı pozitife çeviriyoruz; yoksa −0,5'in tam kısmı 0 çıkar ve eksi işareti kaybolur. (`x = -x` için bir istisna var; 4. alıştırmada.)

---

## 3. Toplama ve çıkarma

İki sayının ölçeği aynıysa, toplamanın ölçeği de aynıdır:

> a / ölçek + b / ölçek = (a + b) / ölçek

Yani **hiçbir şey yapmana gerek yok**: saklanan tamsayıları topla.

```c
int32_t a = fx_from_ratio(3, 2);
int32_t b = fx_from_ratio(9, 4);
fx_print(a + b);
fx_print(a - b);
```

```
3,7500
-0,7500
```

1,5 + 2,25 = 3,75: 98.304 + 147.456 = 245.760 = 3,75 × 65.536. Sabit noktalı toplama, işlemci için sıradan bir tamsayı toplaması; bu yüzden çok hızlı. Taşma kuralları da tamsayılarla aynı (Ders 3.8).

Bir sabit noktalı sayıyla bir tamsayıyı toplamak istiyorsan önce tamsayıyı dönüştür: `a + fx_from_int(2)`. `a + 2` yazmak, 1,5'e 2 değil 2 / 65.536 ekler.

---

## 4. Çarpma ve bölme

Çarpmada ölçekler **çarpılır**:

> (a / ölçek) × (b / ölçek) = (a × b) / ölçek²

`a * b`'nin ölçeği 65.536² olur. Sonucu tekrar Q16.16'ya getirmek için bir kez ölçeğe bölmemiz gerekir:

```c
int32_t fx_mul(int32_t a, int32_t b) {
    return (int32_t)((int64_t)a * b / FX_ONE);
}
```

`(int64_t)` olmadan ne olur? 1,5 × 2,25 için `a * b` = 98.304 × 147.456 ≈ 14,5 milyar; `int32_t`'ye sığmaz. `-fsanitize=undefined` ile denedik:

```
runtime error: signed integer overflow: 98304 * 147456 cannot be represented in type 'int32_t' (aka 'int')
```

Sonuç olarak 3,375 yerine anlamsız bir sayı çıktı. Q16.16'da 1'den büyük herhangi iki sayının çarpımı 32 bite sığmaz; ara sonuç **her zaman** 64 bitle hesaplanmalı. Ders 3.8'deki `checked_mul`'un "daha geniş bir tiple hesapla" fikrinin aynısı. Sonda bölünce sonuç yeniden 32 bite sığar (sığmazsa, Bölüm 5).

Bölmede ise ölçekler **sadeleşir**:

> (a / ölçek) / (b / ölçek) = a / b

`a / b` ölçeksiz bir sayı, yani tamsayı kısmı kalır ve küsurat kaybolur. Bu yüzden bölmeden **önce** payı ölçekle çarparız:

```c
int32_t fx_div(int32_t a, int32_t b) {
    return (int32_t)((int64_t)a * FX_ONE / b);
}
```

Önce çarpıp sonra bölmek, Ders 2.13'teki `daily_calories`'te ara sonucun büyüklüğüne dikkat etmemizle aynı tür bir karar: burada önce bölseydik küsuratı kaybederdik.

```c
fx_print(fx_mul(a, b));
fx_print(fx_div(a, b));
```

```
3,3750
0,6666
```

1,5 × 2,25 = 3,375, **tam olarak**. 1,5 / 2,25 = 0,6666…; sonsuz bir ondalık olduğu için kesiliyor.

| İşlem | Kural |
| --- | --- |
| `a + b`, `a - b` | Olduğu gibi |
| `a * b` | 64 bitle çarp, ölçeğe böl |
| `a / b` | 64 bitle ölçekle çarp, `b`'ye böl |
| `a * n` (`n` tamsayı) | Olduğu gibi: ölçek bir kez var |
| `a / n` (`n` tamsayı) | Olduğu gibi |

Son iki satır kullanışlı: bir sabit noktalı sayıyı bir tamsayıyla çarpmak ya da bölmek için dönüşüm gerekmez. `a * 3` doğrudan 3 × 1,5 = 4,5 verir.

---

## 5. Sınırlar

### Hassasiyet

0,1'i Q16.16'da saklayalım ve on kez toplayalım:

```c
int32_t tenth = fx_from_ratio(1, 10);
int32_t sum = 0;
for (int i = 0; i < 10; i++) {
    sum = sum + tenth;
}
```

```
tenth = 6553, sum = 65530 → 0,9999
```

0,1 × 65.536 = 6.553,6. Tamsayı olmadığı için 6.553'e kesildi; her toplamada 0,6 / 65.536 kadar hata birikti. On toplamadan sonra 1 değil, 0,9999. Sebep, 0,1'in ikilik tabanda sonsuz bir kesir olması (Faz 0); 65.536'nın bir katı olarak tam yazılamaz. Ölçek 10'un kuvveti olsaydı 0,1 tam olurdu, ama 1/3 olmazdı:

```
1/3 = 21845 → 0,3333; 3 ile çarpınca 0,9999
```

**Her ölçek bazı sayıları tam, bazılarını yaklaşık tutar.** 1,5 ve 2,25 gibi paydası 2'nin kuvveti olan sayılar Q16.16'da tamdır. Ders 3.12'deki float da bu sorundan kurtulamayacak.

Kesme yerine **yuvarlamak** hatayı yarıya indirir: 6.553,6'yı 6.554'e yuvarlarsak 0,1'in hatası 0,6 adımdan 0,4 adıma düşer. 2. alıştırmada bunu yapacaksın.

### Aralık

Q16.16'nın en büyük değeri 32.767,99998. 200 × 200'ü hesaplayalım:

```c
int32_t big = fx_from_int(200);
fx_print(fx_mul(big, big));
```

```
-25536,0000
```

40.000 aralığın dışında. `fx_mul`'daki ara sonuç 64 bit olduğu için çarpma taşmadı; ama sonucu `int32_t`'ye geri koyarken Ders 3.7'deki Kural 3 uygulandı ve bitler kırpıldı: 40.000 − 65.536 = −25.536. Ders 3.7'deki `-fsanitize=implicit-conversion` bunu yakalardı; sessizce yanlış bir sonuç almak yerine `fx_mul`'a Ders 3.8'deki gibi bir sınır kontrolü eklemek de mümkün.

Sabit noktalı bir biçim seçmek, **hangi sayıların** hesaplanacağını önceden bilmek demek. Q16.16 bir 3B oyunun koordinatları için yeterliydi; bir ülkenin nüfusu ya da bir banka hesabının bakiyesi için değil. Float'ın (Ders 3.12) büyük avantajı, bu kararı her sayı için ayrı ayrı, kendiliğinden vermesi olacak.

---

## 6. Vücut kitle indeksi, Q16.16 ile

Bütün parçaları birleştirelim. 70 kg, 175 cm:

```c
int32_t height = fx_from_ratio(175, 100);
int32_t height_squared = fx_mul(height, height);
int32_t bmi = fx_div(fx_from_int(70), height_squared);
fx_print(bmi);
```

```
22,8571
```

| Yöntem | Ders | Sonuç |
| --- | --- | --- |
| Tamsayı | 2.3 | 22 |
| 100 ile ölçeklenmiş tamsayı | 2.13 | 22,85 |
| Q16.16 | 3.11 | 22,8571 |
| Gerçek değer | | 22,857142… |

Her adım bir öncekinden daha yakın. Ara değerlere bakmak öğretici: `height` = 114.688 = 1,75 × 65.536, **tam**. `height_squared` = 3,0625, o da tam: 1,75 = 7/4, paydası 2'nin kuvveti. Hata sadece son bölmede, 70 / 3,0625'in sonsuz bir kesir olmasından geliyor.

182 cm'yi deneyince durum değişiyor: 1,82 × 65.536 = 119.275,52, tam değil; 119.275'e kesiliyor. Sonuç **21,1329**, gerçek değer 21,1327. Boyu saklarken yaptığımız küçük kesme, sonuçta son basamağı değiştirdi. Hata payını küçültmenin yolu yuvarlamak ya da daha geniş bir küsurat kullanmak (örneğin `int64_t` içinde Q32.32).

Aralığı da kontrol edelim: Ders 2.13'teki sınırlar içinde en büyük kilo 300 ve en kısa boy 1 m; vücut kitle indeksi en fazla 300 olur, 32.768'in çok altında. `fx_div`'deki ara sonuç 300 × 65.536 × 65.536 ≈ 1,3 × 10¹², `int64_t`'ye rahatça sığar. Ders 3.15'te aynı hesabı dört farklı yolla yapıp sonuçları ve makine kodlarını karşılaştıracağız.

---

## Alıştırmalar

**1** – Bu sayıların Q16.16 karşılığı (saklanan tamsayı) ne? Hangileri tam olarak saklanabilir? 2, 0,25, −1,5, 0,2, 1/3.

**2** – `fx_from_ratio`'yu **yuvarlayan** bir `fx_from_ratio_round` yaz: sonuç en yakın tamsayıya yuvarlansın. (İpucu: Bir pozitif tamsayı bölmesinde `(a + b / 2) / b` en yakına yuvarlar. Şimdilik sadece pozitif sayıları düşün.) 0,1'i on kez toplayınca ne çıkıyor?

**3** – Q16.16'da bir sayıyı kendisiyle çarpınca sonucun aralıkta kalması için o sayı en fazla ne olabilir? `fx_mul(fx_from_int(181), fx_from_int(181))` ve `fx_mul(fx_from_int(182), fx_from_int(182))` ne verir? Bu sınır sana Faz 3'te nereden tanıdık geliyor?

**4** – `fx_print`, `INT32_MIN` için doğru çalışır mı? `x = -x` satırında ne olur? (Ders 3.8, 3. alıştırma.) Fonksiyonu nasıl düzeltirsin?

**5** – Ders 2.13'teki kalori formülünde hareket katsayıları 1,2, 1,375, 1,55, 1,725 ve 1,9 idi ve onları 1000 ile ölçeklemiştik. Bu katsayıları Q16.16 ile `fx_from_ratio` kullanarak yaz. Hangisi tam olarak saklanır? BMH'si 1648 kcal olan biri için 1,55 katsayısıyla sonucu `fx_mul` ve `fx_to_int` ile hesapla.

<details>
<summary>Cevaplar</summary>

**1** –

- 2 → **131.072**, tam.
- 0,25 → **16.384**, tam (1/4).
- −1,5 → **−98.304**, tam.
- 0,2 → 13.107,2 → **13.107**, tam değil (gerçekte 0,19999…).
- 1/3 → 21.845,33… → **21.845**, tam değil.

Paydası (sadeleştirilmiş haliyle) 2'nin bir kuvveti olan ve 2¹⁶'yı geçmeyen sayılar tam saklanır.

**2** –

```c
int32_t fx_from_ratio_round(int num, int den) {
    return (int32_t)(((int64_t)num * FX_ONE + den / 2) / den);
}
```

0,1 artık 6.554. On kez toplayınca 65.540, yani **1,0000** gibi görünür (4 basamakta 1,00006 kesilip 1,0000 olarak yazılır), ama gerçekte 1'den biraz büyük. Hata yön değiştirdi ve yarıya indi; yok olmadı.

**3** – Sonuç 32.767,99998'i geçmemeli; √32.768 ≈ 181,02. 181 × 181 = **32.761,0000**, sığıyor. 182 × 182 = 33.124 sığmıyor ve bitler kırpılınca **−32.412,0000** çıkıyor (33.124 − 65.536). Tanıdık sınır: Ders 3.1'deki 4. alıştırmada, 2 byte'lık `int`'i olan Arduino'da `height_cm * height_cm` da tam olarak 182 cm'de taşıyordu. Q16.16'nın tam kısmı da 16 bit; aynı sınır, aynı sebep.

**4** – Hayır. `INT32_MIN` −2.147.483.648; negatifi `int32_t`'ye sığmaz, `x = -x` undefined behavior olur. Bir çözüm, işaretli sayıyı Ders 3.8'deki gibi işaretsiz olarak çevirmek:

```c
void fx_print(int32_t x) {
    uint32_t magnitude = (uint32_t)x;
    if (x < 0) {
        putchar('-');
        magnitude = 0u - magnitude;
    }
    uint32_t whole = magnitude / FX_ONE;
    uint32_t frac = magnitude % FX_ONE;
    uint32_t digits = (uint32_t)((uint64_t)frac * 10000 / FX_ONE);
    printf("%u,%04u", whole, digits);
}
```

`INT32_MIN` için `-32768,0000` yazar.

**5** –

```c
int32_t factors[] = {
    fx_from_ratio(12, 10),
    fx_from_ratio(1375, 1000),
    fx_from_ratio(155, 100),
    fx_from_ratio(1725, 1000),
    fx_from_ratio(19, 10),
};
```

Sadece **1,375** tam saklanır: 1,375 = 11/8. Diğerlerinin paydası 5'in kuvvetlerini içeriyor. Hesap:

```c
int calories = fx_to_int(fx_mul(fx_from_int(1648), factors[2]));
```

1648 × 1,55 = 2554,4 → **2554** kcal, Ders 2.13'teki sonucun aynısı. 1648 × 65.536 ≈ 108 milyon, Q16.16'ya sığıyor (1648 < 32.768).

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.4.1: kesirli ikilik sayılar.
- Fabien Sanglard, *Game Engine Black Book: DOOM* (2018): Doom'un 16.16 sabit noktalı sayıları (`fixed_t`).

**Sıradaki ders:** IEEE 754 float. Bilgisayar küsuratlı sayıları nasıl tutuyor, ve 0,1 + 0,2 neden 0,3 etmiyor?
