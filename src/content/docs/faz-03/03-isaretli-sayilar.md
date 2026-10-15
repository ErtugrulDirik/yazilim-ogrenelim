---
title: "3.3 İşaretli sayılar: signed ve unsigned"
description: "Aynı bit deseninin iki farklı yorumu; negatif sayıları göstermenin üç yolu ve ikiler tümleyeninin neden kazandığı; çıkarmanın toplamaya dönüşmesi, aralık hesabı ve carry ile overflow farkı."
---

Ders 3.1 ve 3.2'de iki soruyu sonraya bırakmıştık:

- `INT_MIN` -2.147.483.648, `INT_MAX` ise 2.147.483.647. Negatif taraf neden **bir fazla**?
- Bilgisayar sadece 0 ve 1 tutabiliyorsa, **eksi işaretini** nereye koyuyor?

İkisinin cevabı aynı: negatif sayıların bitlerle gösterilme biçimi. Bu derste önce kağıt üstünde, sonra C ile bu biçimi kuracağız.

---

## 1. İşaretsiz sayılar: unsigned

Faz 0'da bitleri hep **pozitif** sayılar olarak okuduk. 8 bit ile 2⁸ = 256 farklı desen vardı ve bunları 0'dan 255'e kadar sayılar olarak yorumladık. C'de bu yoruma **işaretsiz** (unsigned) denir ve bir tipin önüne `unsigned` yazarak istenir:

```c
#include <stdio.h>
#include <limits.h>

int main(void) {
    printf("signed char:   %d ile %d arası\n", SCHAR_MIN, SCHAR_MAX);
    printf("unsigned char: 0 ile %d arası\n", UCHAR_MAX);
    printf("unsigned short: 0 ile %d arası\n", USHRT_MAX);
    printf("unsigned int:  0 ile %u arası\n", UINT_MAX);
    printf("unsigned long long: 0 ile %llu arası\n", ULLONG_MAX);
    return 0;
}
```

```
signed char:   -128 ile 127 arası
unsigned char: 0 ile 255 arası
unsigned short: 0 ile 65535 arası
unsigned int:  0 ile 4294967295 arası
unsigned long long: 0 ile 18446744073709551615 arası
```

- `unsigned int` ile `int` aynı boyuttadır: 4 byte. Fark sadece bitlerin **nasıl okunduğunda**. `int` yaklaşık −2,1 milyar ile +2,1 milyar arasını tutarken `unsigned int` 0 ile 4,2 milyar arasını tutar. Negatif tarafı verip pozitif tarafı iki katına çıkarmış olur.
- `unsigned` sayıları yazdırmak için `%u` kullanılır; `unsigned long long` için `%llu`.
- Ders 3.2'deki "`char` işaretli mi işaretsiz mi?" belirsizliğinin çözümü de burada: `signed char` her platformda −128 ile 127, `unsigned char` her platformda 0 ile 255 arasıdır. Sadece `char` yazarsan seçimi platform yapar.

İşaretsiz bir sayının en büyük değeri, bütün bitleri 1 olan desendir: n bit için **2ⁿ − 1**.

---

## 2. Aynı bitler, iki farklı sayı

Faz 0'dan beri tekrarladığımız cümle: **bitlerin anlamını bağlam belirler.** 11111111 desenini düşün. İşaretsiz okursan 255. Peki işaretli okursan?

Bunu görmek için bir `signed char`'ın bitlerini yazdıran küçük bir program yazalım:

```c
#include <stdio.h>

void print_bits(unsigned char b) {
    for (int w = 128; w >= 1; w = w / 2) {
        putchar(b / w % 2 ? '1' : '0');
    }
}

int main(void) {
    signed char values[] = {5, -5, 1, -1, 0, 127, -128};
    int count = sizeof(values) / sizeof(values[0]);

    for (int i = 0; i < count; i++) {
        unsigned char bits = values[i];
        printf("%4d  ", values[i]);
        print_bits(bits);
        printf("  işaretsiz okunursa: %d\n", bits);
    }
    return 0;
}
```

```
   5  00000101  işaretsiz okunursa: 5
  -5  11111011  işaretsiz okunursa: 251
   1  00000001  işaretsiz okunursa: 1
  -1  11111111  işaretsiz okunursa: 255
   0  00000000  işaretsiz okunursa: 0
 127  01111111  işaretsiz okunursa: 127
-128  10000000  işaretsiz okunursa: 128
```

- `print_bits`, Ders 2.8'deki rakam ayırma fikrinin ikilik hali: 128, 64, 32… diye basamak değerlerinde ilerliyor; `b / w % 2` o basamaktaki biti veriyor.
- `unsigned char bits = values[i];` → İşaretli değeri işaretsiz bir kutuya koyuyoruz. Bitler **aynen** kopyalanır, sadece okunuşları değişir. (Farklı tipler arası atamanın bütün kurallarını Ders 3.7'de göreceğiz.)

Çıktıdaki tuhaflıklara bak: −1, `11111111`. −5, `11111011`. −128, `10000000`. Negatif sayıların hepsi 1 ile başlıyor, ama −5'in deseni 5'in deseninin başına bir 1 konmuş hali değil. Bu desenler nereden geliyor?

---

## 3. Negatif sayıları göstermenin üç yolu

Hesapları kısa tutmak için **4 bit** ile çalışalım; 4 bit ile 2⁴ = 16 desen var. Tarih boyunca bilgisayarlar bu desenleri negatif sayılara üç farklı şekilde dağıttı.

### Fikir 1: İşaret ve büyüklük

En doğal fikir: en soldaki bit **işaret** olsun (0 artı, 1 eksi), kalan bitler sayının **büyüklüğü**. Kağıtta yazdığımız gibi.

- +5 = `0101`
- −5 = `1101`

İki sorunu var:

- **İki tane sıfır var:** `0000` (+0) ve `1000` (−0). Bir desen boşa gidiyor ve "bu sayı sıfır mı?" sorusu iki karşılaştırma gerektiriyor.
- **Toplama bozuluyor.** Faz 0'daki toplama kuralıyla 5 + (−5) yapalım: `0101` + `1101` = `1 0010`. 4 bite sığmayan 1 atılır, sonuç `0010` = **+2**. Doğrusu 0'dı. Bu gösterimde toplama yapmak için işaretlere bakıp "aynıysa topla, farklıysa büyükten küçüğü çıkar" diyen ayrı bir devre gerekir.

### Fikir 2: Birler tümleyeni (ones' complement)

Negatif sayıyı, pozitif sayının **bütün bitlerini ters çevirerek** elde edelim (Faz 0'daki NOT işlemi):

- +5 = `0101`
- −5 = NOT `0101` = `1010`

5 + (−5) = `0101` + `1010` = `1111`. Bu gösterimde `1111`, −0 demektir. Sonuç doğru, ama **iki sıfır** sorunu hâlâ duruyor: `0000` ve `1111`. Üstelik bazı toplamalarda sonuç bir eksik çıkar ve dışarı taşan biti tekrar sağa eklemek gerekir: 3 + (−1) = `0011` + `1110` = `1 0001` → `0001` = 1. Doğrusu 2.

### Fikir 3: İkiler tümleyeni (two's complement)

Bitleri ters çevir ve **1 ekle**:

> −x = NOT x + 1

- +5 = `0101`
- NOT `0101` = `1010`, 1 ekle: −5 = `1011`

5 + (−5) = `0101` + `1011` = `1 0000`. 4 bite sığmayan 1 atılır: `0000`. **Sıfır.** Hiçbir özel kural gerekmedi.

Bu fikrin arkasında Faz 0'daki kilometre sayacı var. 4 bitlik bir sayaç `0000`'dan geriye doğru bir adım sayarsa `1111`'e döner. Sıfırdan bir önceki sayı −1 olduğuna göre, `1111` = **−1** demek mantıklı. Bir adım daha geri: `1110` = −2. Ve böyle devam eder.

Bütün desenleri yan yana koyalım:

| Bitler | İşaretsiz | İşaret-büyüklük | Birler tümleyeni | **İkiler tümleyeni** |
| --- | --- | --- | --- | --- |
| `0000` | 0 | +0 | +0 | **0** |
| `0001` | 1 | 1 | 1 | **1** |
| `0010` | 2 | 2 | 2 | **2** |
| `0011` | 3 | 3 | 3 | **3** |
| `0100` | 4 | 4 | 4 | **4** |
| `0101` | 5 | 5 | 5 | **5** |
| `0110` | 6 | 6 | 6 | **6** |
| `0111` | 7 | 7 | 7 | **7** |
| `1000` | 8 | −0 | −7 | **−8** |
| `1001` | 9 | −1 | −6 | **−7** |
| `1010` | 10 | −2 | −5 | **−6** |
| `1011` | 11 | −3 | −4 | **−5** |
| `1100` | 12 | −4 | −3 | **−4** |
| `1101` | 13 | −5 | −2 | **−3** |
| `1110` | 14 | −6 | −1 | **−2** |
| `1111` | 15 | −7 | −0 | **−1** |

Pozitif sayılar dört gösterimde de aynı; fark sadece en soldaki bit 1 olduğunda ortaya çıkıyor.

**İkiler tümleyenini okumanın kısa yolu.** En soldaki bitin değeri artı değil **eksi** sayılır. 4 bitte basamak değerleri 8, 4, 2, 1 yerine **−8**, 4, 2, 1 olur:

- `1011` = −8 + 2 + 1 = **−5**
- `1111` = −8 + 4 + 2 + 1 = **−1**
- `1000` = **−8**

Bölüm 2'deki çıktıyla karşılaştır: 8 bitte en soldaki bitin değeri −128. `11111011` = −128 + 64 + 32 + 16 + 8 + 2 + 1 = **−5**. Bugünkü bilgisayarların hepsi bu gösterimi kullanıyor.

---

## 4. Neden ikiler tümleyeni kazandı?

**Tek sıfır.** 16 desenin hiçbiri boşa gitmiyor ve "sıfır mı?" sorusu tek bir karşılaştırma.

**Çıkarma, toplamaya dönüşür.** a − b = a + (−b) = a + (NOT b + 1). İşlemcinin ayrı bir çıkarma devresine ihtiyacı yok: b'nin bitlerini ters çevirip toplama devresine verir ve elde girişine 1 koyar. 4 bitte 7 − 3:

```
   0111   (7)
 + 1101   (−3 = NOT 0011 + 1)
 ------
 1 0100   → dışarı taşan 1 atılır: 0100 = 4
```

**Aynı devre, iki tip.** Tablodaki "İşaretsiz" ve "İkiler tümleyeni" sütunlarına tekrar bak. `1011` + `0001` = `1100`. İşaretsiz okursan 11 + 1 = 12; ikiler tümleyeniyle okursan −5 + 1 = −4. **İkisi de doğru.** Toplama devresi bitlerin ne anlama geldiğini bilmek zorunda değil; `int` ile `unsigned int` için aynı toplama komutu kullanılır. Yorumu yapan sensin.

Bu üstünlükler yüzünden 1970'lerden sonra üretilen işlemcilerin neredeyse hepsi ikiler tümleyenini kullandı. Ders 3.2'de standardın neden −128 yerine −127'yi garanti ettiğini merak etmiştik: eski standart, işaret-büyüklük ve birler tümleyeni kullanan makinelere de yer bırakıyordu; o gösterimlerde 8 bitin en küçük değeri −127'dir. Bu makineler artık müzelerde olduğu için **C23** standardı ikiler tümleyenini zorunlu hale getirdi.

---

## 5. Aralık hesabı ve INT_MIN'in sırrı

n bitlik bir sayıda:

| | En küçük | En büyük |
| --- | --- | --- |
| İşaretsiz | 0 | 2ⁿ − 1 |
| İşaretli (ikiler tümleyeni) | −2ⁿ⁻¹ | 2ⁿ⁻¹ − 1 |

| Bit | İşaretsiz | İşaretli |
| --- | --- | --- |
| 8 | 0 … 255 | −128 … 127 |
| 16 | 0 … 65.535 | −32.768 … 32.767 |
| 32 | 0 … 4.294.967.295 | −2.147.483.648 … 2.147.483.647 |
| 64 | 0 … 18.446.744.073.709.551.615 | yaklaşık ±9,2 × 10¹⁸ |

İşaretli sayılarda en soldaki biti 0 olan desenler (yarısı) sıfır ve pozitif sayılara, 1 olanlar (diğer yarısı) negatiflere gidiyor. Negatif tarafta 2ⁿ⁻¹ sayı var. Pozitif tarafta da 2ⁿ⁻¹ desen var ama bunlardan biri **sıfır**. Asimetrinin sebebi bu: 4 bitte −8'e kadar inebiliyoruz ama +7'de duruyoruz.

Şimdi `INT_MIN`'in negatifini bitlerle görelim. 4 bitte en küçük sayı −8 = `1000`. Negatifini alalım:

```
NOT 1000 = 0111
    0111 + 1 = 1000
```

**−(−8) = −8.** +8'i gösterecek desen yok; işlem kendi üstüne döndü. `-INT_MIN` de tam olarak bu yüzden `int`'e sığmaz. C'de bu işaretli bir overflow olduğu için undefined behavior'dır (Ders 2.12).

---

## 6. Carry ve overflow

Faz 0'da "8 bitte 255 + 1 = 0" demiştik ve buna overflow demiştik. Artık daha dikkatli olabiliriz, çünkü aynı toplama iki farklı şekilde yanlış gidebilir. 4 bitle iki örnek:

**Örnek A:** `0111` + `0001` = `1000`

- İşaretsiz: 7 + 1 = 8. **Doğru.**
- İşaretli: 7 + 1 = −8. **Yanlış!** İki pozitif sayının toplamı negatif çıktı.

**Örnek B:** `1111` + `0001` = `1 0000` → `0000`

- İşaretsiz: 15 + 1 = 0. **Yanlış!** Dışarı bir bit taştı.
- İşaretli: −1 + 1 = 0. **Doğru.**

İki ayrı durum var ve ikisinin ayrı adı var:

- **Carry (elde taşması):** En soldaki bitten dışarı bir elde çıktı. **İşaretsiz** sonuç yanlıştır.
- **Overflow (taşma):** Aynı işaretli iki sayı toplandı ve sonucun işareti farklı çıktı (iki pozitifin toplamı negatif ya da iki negatifin toplamı pozitif). **İşaretli** sonuç yanlıştır.

Farklı işaretli iki sayının toplamı asla overflow olmaz; sonuç her zaman ikisinin arasında bir yerdedir. İşlemci her toplamadan sonra iki durumu da ayrı ayrı not eder; Faz 7'de assembly yazarken bunları işlemcinin **bayrakları** olarak göreceğiz.

**C'de ikisi çok farklı karşılanır.** İşaretsiz tiplerde dışarı taşan bit sessizce atılır ve bu **tanımlı** bir davranıştır: sonuç sayaç gibi başa döner.

```c
#include <stdio.h>

int main(void) {
    unsigned int count = 0;
    count = count - 1;
    printf("%u\n", count);
    return 0;
}
```

```
4294967295
```

0'dan 1 çıkınca sayaç geriye dönüp en büyük değere, 2³² − 1'e geldi. Sanitizer bile şikayet etmez; standart bu davranışı garanti eder. İşaretli tiplerde ise overflow, Ders 2.12'de gördüğümüz gibi **undefined behavior**'dır. Taşmayı önceden yakalamayı Ders 3.8'de göreceğiz.

---

## Alıştırmalar

**1** – 8 bit ikiler tümleyeniyle −20'nin bit desenini bul. Sonra desenin işaretsiz değerini hesapla ve 256'dan çıkar. Ne fark ettin?

**2** – `10110110` deseni işaretsiz okunursa kaç, ikiler tümleyeniyle okunursa kaçtır? İkinciyi hem "en soldaki bit eksi" yoluyla hem de "NOT ve 1 ekle" yoluyla bul.

**3** – 4 bit ikiler tümleyeniyle aşağıdaki toplamaları yap. Her biri için carry ve overflow oldu mu, işaretsiz ve işaretli sonuçlar doğru mu?

- a) 6 + 3
- b) −6 + (−3)
- c) 5 + (−2)

**4** – 16 bitlik işaretsiz ve işaretli bir sayının aralığını hesapla. Ders 3.1'deki Arduino `int`'iyle karşılaştır.

**5** – Bir x sayısı ile NOT x'i toplarsan her bit 1 + 0 ya da 0 + 1 olur; sonuç hep `1111...1` çıkar. Bunu ve `1111...1` = −1 bilgisini kullanarak **−x = NOT x + 1** kuralını kendin türet.

**6** – Bölüm 2'deki programın `values` array'ine 64, −64, −127 ve 100 ekle. Çıktıyı çalıştırmadan önce tahmin et.

<details>
<summary>Cevaplar</summary>

**1** – 20 = `00010100`. NOT: `11101011`. 1 ekle: `11101100`. İşaretsiz değeri 236; 256 − 236 = 20. Genel kural: n bitte −x'in deseni, işaretsiz okunduğunda **2ⁿ − x**'tir. "İkiler tümleyeni" adı da buradan gelir: x'i 2ⁿ'e tamamlayan sayı.

**2** – İşaretsiz: 128 + 32 + 16 + 4 + 2 = **182**. İşaretli: −128 + 32 + 16 + 4 + 2 = **−74**. Diğer yol: NOT `10110110` = `01001001` = 73; 1 ekle: 74. Yani desen −74'tür. Kontrol: 182 − 256 = −74.

**3** –

- a) `0110` + `0011` = `1001`. Carry yok, işaretsiz 9 doğru. İki pozitifin toplamı negatif (−7) çıktı: **overflow**, işaretli sonuç yanlış. 9, 4 bitlik işaretli aralığın (−8 … 7) dışında.
- b) `1010` + `1101` = `1 0111`. **Carry** var: işaretsiz 10 + 13 = 23 sığmadı, 7 çıktı. İki negatifin toplamı pozitif (7) çıktı: **overflow**. İkisi de yanlış; −9 da aralığın dışında.
- c) `0101` + `1110` = `1 0011` = 3. Carry var: işaretsiz 5 + 14 = 19 sığmadı. İşaretler farklı olduğu için overflow olamaz; işaretli sonuç 3, **doğru**. Carry olması işaretli sonucun yanlış olduğu anlamına gelmez.

**4** – İşaretsiz 0 … 2¹⁶ − 1 = **0 … 65.535**. İşaretli −2¹⁵ … 2¹⁵ − 1 = **−32.768 … 32.767**. Arduino'daki `INT_MIN` ve `INT_MAX` tam olarak bunlar.

**5** – x + NOT x = `1111...1` = −1. İki taraftan NOT x'i yalnız bırakalım: NOT x = −1 − x. İki tarafa 1 ekleyelim: NOT x + 1 = −x.

**6** –

```
  64  01000000  işaretsiz okunursa: 64
 -64  11000000  işaretsiz okunursa: 192
-127  10000001  işaretsiz okunursa: 129
 100  01100100  işaretsiz okunursa: 100
```

−64 = −128 + 64. −127 = −128 + 1. Her negatif değerin işaretsiz okunuşu 256 fazlası: 192 = −64 + 256.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.2: işaretli ve işaretsiz gösterimler; §2.3.1–2.3.2: toplama ve overflow.
- Charles Petzold, *Code* (2. baskı), "But What About Subtraction?" bölümü: ikiler tümleyeninin bir toplama devresiyle çıkarma yapmayı nasıl mümkün kıldığı.
- C standardı taslağı N3096 (C23), §6.2.6.2: işaretli tamsayıların ikiler tümleyeniyle gösterilmesi.

**Sıradaki ders:** `<stdint.h>`. Boyutu her platformda aynı olan tipler: `int8_t`, `uint32_t`, `int64_t` ve `size_t`.
