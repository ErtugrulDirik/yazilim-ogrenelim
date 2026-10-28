---
title: "3.12 IEEE 754 float"
description: "Bilgisayarın küsuratlı sayıları tutma biçimi: ikilik bilimsel gösterim, işaret–üs–mantis, bias ve gizli bit; 32 bitlik bir float'ı bit bit çözümlemek, 0,1'in neden tam saklanamadığı, 0,1 + 0,2'nin neden 0,3 etmediği ve tamsayılarla karışık hesapların kuralları."
---

Şu programın ne yazdıracağını tahmin et:

```c
#include <stdio.h>

int main(void) {
    double sum = 0.1 + 0.2;
    printf("%d\n", sum == 0.3);
    printf("%.17g\n", sum);
    return 0;
}
```

```
0
0.30000000000000004
```

0,1 + 0,2, 0,3 **değil**. Bu bir C hatası da değil: Python'da, JavaScript'te, Java'da, Excel'de aynı sonucu alırsın. Hepsi küsuratlı sayıları aynı standartla tutuyor: **IEEE 754**. Ders 3.1'de "0,1 + 0,2 neden 0,3 etmiyor?" diye sormuş, Ders 3.11'de de sabit noktalı sayıların her sayı için aynı ölçeği kullanmak zorunda olduğunu görmüştük. Bu derste ikisinin de cevabını alıyoruz.

---

## 1. Virgülü kaydırmak

Ders 3.11'deki Q16.16'nın sorunu, virgülün **sabit** olmasıydı: 16 bit tam kısım, 16 bit küsurat. 0,00001 için de 30.000 için de aynı bölüşüm. Fizikçiler bu sorunu çok önce **bilimsel gösterimle** çözdü:

| Sayı | Bilimsel gösterim |
| --- | --- |
| 602.200.000.000.000.000.000.000 | 6,022 × 10²³ |
| 0,000 000 000 000 000 000 160 2 | 1,602 × 10⁻¹⁹ |
| 22,857 | 2,2857 × 10¹ |

Her sayı iki parçadan oluşuyor: **anlamlı basamaklar** (6,022) ve virgülün nereye kayacağını söyleyen bir **üs** (23). Virgülün yeri her sayı için ayrı ayrı belirleniyor; adı da buradan: **kayan nokta** (floating point). Ders 3.11'in sonunda söz ettiğimiz "kararı her sayı için ayrı ayrı vermek" tam olarak bu.

Bilgisayar aynı şeyi ikilik tabanda yapar. Faz 0'da küsuratlı sayıları ikiliğe çevirmiştik; 5,75'i deneyelim:

> 5,75 = 4 + 1 + 0,5 + 0,25 = 101,11₂

Virgülü, solunda tek bir 1 kalacak şekilde kaydıralım. İki basamak sola kaydırmak, 2² ile çarpılmış bir sayı yazmak demek:

> 101,11₂ = 1,0111₂ × 2²

Ondalık bilimsel gösterimde ilk basamak 1 ile 9 arasında herhangi bir şey olabilir. İkilikte ise sıfır olmayan bir sayının ilk basamağı **her zaman 1'dir**; başka rakam yok. Bunu birazdan bedava bir bit kazanmak için kullanacağız.

---

## 2. 32 bitin üç parçası

C'de `float` tipi 4 byte, yani 32 bittir ve neredeyse her platformda IEEE 754'ün **tek hassasiyetli** (single precision) biçimini kullanır. 32 bit üç parçaya ayrılır:

```
  işaret   üs (8 bit)   mantis (23 bit)
    0      10000001     01110000000000000000000
```

| Parça | Bit | Ne tutar? |
| --- | --- | --- |
| İşaret (sign) | 1 | 0 ise pozitif, 1 ise negatif |
| Üs (exponent) | 8 | 2'nin kuvveti, **127 eklenmiş** olarak |
| Mantis (mantissa, significand) | 23 | Virgülden sonraki basamaklar |

Formül:

$$
\text{değer} = (-1)^{\text{işaret}} \times 1{,}\text{mantis}_2 \times 2^{\,\text{üs} - 127}
$$

Üç parçanın da kendine göre bir hikayesi var.

**İşaret.** Ders 3.3'teki üç fikirden ilki geri döndü: **işaret ve büyüklük**. Negatif bir float, pozitif halinin sadece en soldaki biti değişmiş halidir; ikiler tümleyeni yok. Ders 3.3'te bu fikrin iki sorunu vardı: iki tane sıfır ve bozuk toplama. Toplama burada zaten özel bir devreyle yapılıyor, ama iki sıfır sorunu duruyor: +0 ve −0 diye iki ayrı float var. Ders 3.13'te ona döneceğiz.

**Üs ve bias.** Üs negatif de olabilir: 0,5 = 1,0 × 2⁻¹. 8 bitlik üs alanı ikiler tümleyeni kullanmaz; onun yerine gerçek üse sabit bir sayı, **127**, eklenip saklanır. Bu sabite **bias** denir.

| Gerçek üs | Saklanan (üs + 127) | Bitler |
| --- | --- | --- |
| −1 | 126 | `01111110` |
| 0 | 127 | `01111111` |
| 1 | 128 | `10000000` |
| 2 | 129 | `10000001` |

Neden ikiler tümleyeni değil? Çünkü bu sayede iki pozitif float'ın bitlerini **işaretsiz tamsayı** gibi karşılaştırınca, büyük olan float'ın bitleri de büyük çıkar: üs soldaki bitlerde, ve büyük üs büyük tamsayı demek. İşlemci float'ları sıralarken tamsayı karşılaştırmasından yararlanabilir. (3. alıştırma.)

Saklanan üs 0 ile 255 arasında olabilir, ama iki uç değer özel durumlara ayrılmış: 0 sıfır ve çok küçük sayılar için, 255 sonsuz ve "sayı değil" için (Ders 3.13). Sıradan sayılar için kalan 1–254 aralığı, gerçek üs olarak **−126 ile 127** arası demek.

**Mantis ve gizli bit.** İlk basamağın her zaman 1 olduğunu söylemiştik. Her zaman 1 olan bir şeyi saklamaya gerek yok: mantis alanı sadece virgülden **sonraki** 23 biti tutar, baştaki 1 yazılmaz. Bu "görünmez" basamağa **gizli bit** (hidden bit) denir. Sonuç: 23 bitlik bir alanla **24 bitlik** hassasiyet.

---

## 3. Elle çözümleme

### Sayıdan bitlere: 5,75

1. İkiliğe çevir: 5,75 = 101,11₂.
2. Normalleştir: 1,0111₂ × 2².
3. İşaret: pozitif, **0**.
4. Üs: 2 + 127 = 129 = **10000001**.
5. Mantis: baştaki `1,`'i at, kalan `0111`'i 23 bite sağdan sıfırla tamamla: **01110000000000000000000**.

```
0 10000001 01110000000000000000000
```

Dörderli gruplarsak `0100 0000 1011 1000 0000 …` = **0x40B80000** (Ders 3.10'daki onaltılık sabitler).

−5,75 için sadece işaret biti değişir: `1 10000001 0111…` = **0xC0B80000**.

### Bitlerden sayıya: 0x3F800000

```
0011 1111 1000 0000 0000 0000 0000 0000
0 01111111 00000000000000000000000
```

- İşaret 0: pozitif.
- Üs `01111111` = 127; gerçek üs 127 − 127 = 0.
- Mantis 0; gizli bitle birlikte 1,0.

Sonuç: 1,0 × 2⁰ = **1**. Bitlerin hepsi neredeyse 1 olsa da sayı 1; bir float'ın bitlerine tamsayı gözüyle bakmak işe yaramaz.

---

## 4. C ile bitlere bakmak

Bir float'ın bitlerini görmek için Ders 3.9'daki `memcpy`'yi kullanabiliriz: float'ın 4 byte'ını hiç yorumlamadan bir `uint32_t`'ye kopyalarız. Parçaları ayırmak için bit kaydırmayı Faz 5'te göreceğiz; şimdilik Ders 3.9'daki gibi bölme ve kalanla yapalım:

- **İşaret**: en soldaki bit, yani 2³¹'in basamağı: `bits / 2147483648u`.
- **Üs**: sağdan 23 bit atla, kalan 8 biti al: `bits / 8388608 % 256` (2²³ = 8.388.608).
- **Mantis**: sağdaki 23 bit: `bits % 8388608`.

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>

void print_bits(uint32_t x, int width) {
    uint32_t w = 1;
    for (int i = 1; i < width; i++) {
        w = w * 2;
    }
    for (int i = width; i >= 1; i--) {
        putchar(x / w % 2 ? '1' : '0');
        w = w / 2;
    }
}

void show_float(float f) {
    uint32_t bits;
    memcpy(&bits, &f, sizeof(bits));
    uint32_t sign = bits / 2147483648u;
    uint32_t exponent = bits / 8388608 % 256;
    uint32_t mantissa = bits % 8388608;

    printf("%-12.9g ", f);
    print_bits(sign, 1);
    putchar(' ');
    print_bits(exponent, 8);
    putchar(' ');
    print_bits(mantissa, 23);
    printf("  üs %4d  0x%08X\n", (int)exponent - 127, bits);
}

int main(void) {
    float values[] = {1.0f, 2.0f, 3.0f, 0.5f, 5.75f, -5.75f, 22.857142f};
    int count = sizeof(values) / sizeof(values[0]);
    for (int i = 0; i < count; i++) {
        show_float(values[i]);
    }
    return 0;
}
```

```
1            0 01111111 00000000000000000000000  üs    0  0x3F800000
2            0 10000000 00000000000000000000000  üs    1  0x40000000
3            0 10000000 10000000000000000000000  üs    1  0x40400000
0.5          0 01111110 00000000000000000000000  üs   -1  0x3F000000
5.75         0 10000001 01110000000000000000000  üs    2  0x40B80000
-5.75        1 10000001 01110000000000000000000  üs    2  0xC0B80000
22.8571415   0 10000011 01101101101101101101101  üs    4  0x41B6DB6D
```

- `print_bits`, Ders 3.7'dekinin aynısı; bu sefer satır sonu ve 8'li gruplar olmadan.
- `f` sayısının sonundaki **`f`** eki, sabitin `float` olduğunu söylüyor (Ders 3.10'daki `U` ve `L` gibi). Eksiz `1.0` bir `double`'dır; birazdan göreceğiz.
- `%g`, sayıyı gereksiz sıfırlar olmadan yazar; `%.9g` en fazla 9 anlamlı basamak demek. Neden 9 olduğunu Bölüm 6'da göreceğiz.

Tabloyu oku:

- **1 ve 2** sadece üste farklı: 2 = 1,0 × 2¹. Bir float'ı 2 ile çarpmak, mantise hiç dokunmadan üse 1 eklemek demek.
- **3** = 1,1₂ × 2¹; mantisin ilk biti 1, yani 0,5. 1,5 × 2 = 3.
- **0,5**'in üssü −1, saklanan 126.
- **22,857142**: Ders 3.11'deki vücut kitle indeksi. 10110,110110110…₂ = 1,0110110110…₂ × 2⁴. Mantisteki `110` tekrarı, 22,857142… = 160/7'nin ikilikteki sonsuz açılımından geliyor. 23 bit dolunca kesiliyor ve float 22,857142 yerine **22,8571415** saklıyor.

---

## 5. 0,1 neden tam değil?

Faz 0'da 0,1'i ikiliğe çevirmiştik: sonsuza kadar tekrar eden bir kesir.

> 0,1 = 0,0001100110011001100…₂ = 1,100110011001100…₂ × 2⁻⁴

Mantise 23 bit sığıyor; 24. bitten sonrası atılmak zorunda. IEEE 754, atılan kısma bakıp sonucu **en yakın** float'a yuvarlar:

```
tam açılım:  1,10011001100110011001100 1100…
             ↑ gizli    23 bit         ↑ atılan kısım yarıdan büyük
saklanan:    1,10011001100110011001101
```

Atılan kısım (`1100…`) yarıdan büyük olduğu için son bit yukarı yuvarlandı. `show_float(0.1f)`:

```
0.100000001  0 01111011 10011001100110011001101  üs   -4  0x3DCCCCCD
```

Saklanan sayı **tam olarak** şu:

> 0,100000001490116119384765625

0,1'e en yakın float bu; ama 0,1 değil. Ders 3.11'de söylediğimiz gibi: **her ölçek bazı sayıları tam, bazılarını yaklaşık tutar.** Float'ın ölçeği her zaman 2'nin bir kuvveti olduğu için paydası 2'nin kuvveti olmayan hiçbir kesir (0,1 = 1/10, 0,2 = 1/5, 1/3…) tam saklanamaz. 0,5, 0,25, 5,75 ve 0,375 ise tamdır.

### 0,1 + 0,2

Dersin başındaki program `double` kullanıyordu; `double`, aynı fikrin 64 bitlik hali (Ders 3.14). Üç sabitin `double`'da saklanan gerçek değerleri:

| Sabit | Saklanan değer |
| --- | --- |
| `0.1` | 0,1000000000000000055511151231257827… |
| `0.2` | 0,2000000000000000111022302462515654… |
| `0.3` | 0,2999999999999999888977697537484345… |
| `0.1 + 0.2` | 0,3000000000000000444089209850062616… |

0,1 ve 0,2 gerçek değerlerinden biraz **büyük** saklanıyor; toplamları da 0,3'ten biraz büyük çıkıyor ve en yakın `double`'a yuvarlanıyor. 0,3 sabiti ise 0,3'ten biraz **küçük** olan komşuya yuvarlanmış. Sonuç: aynı sayıya en yakın olmaya çalışan iki **farklı** `double`. Aralarındaki fark, 0,3 civarında iki `double` arasındaki en küçük adım kadar; ve `==` ile karşılaştırınca 0 çıkıyor.

Aynı şeyi `float` ile deneyelim:

```c
printf("%d\n", 0.1f + 0.2f == 0.3f);
```

```
1
```

Bu sefer **eşit**. Float'ta yuvarlama hataları tesadüfen birbirini götürdü. Bundan "float daha doğru" sonucu çıkmaz; asıl ders şu: hesaplanmış iki küsuratlı sayının `==` ile eşit çıkıp çıkmayacağı, yuvarlamaların nereye düştüğüne bağlı bir şans meselesi. Karşılaştırmanın doğru yolunu Ders 3.13'te göreceğiz.

Ders 3.11'deki deneyi tekrarlayalım, 0,1'i on kez toplayalım:

| Biçim | Sonuç |
| --- | --- |
| Q16.16 (Ders 3.11) | 0,9999 |
| `float` | 1,00000012 |
| `double` | 0,99999999999999989 |

Üçü de 1 değil. Float'ın kurtarıcı olmadığını, sadece **çok daha geniş bir aralıkta** çalıştığını gösteriyor.

---

## 6. C'de kayan nokta tipleri

C'de üç kayan nokta tipi var. Standart, Ders 3.2'deki tamsayılarda olduğu gibi boyutları kesin olarak belirlemiyor; sadece `float`'ın `double`'dan, `double`'ın da `long double`'dan daha hassas olamayacağını söylüyor. Ölçtük:

| Platform | `float` | `double` | `long double` |
| --- | --- | --- | --- |
| macOS (Apple Silicon) | 4 | 8 | 8 |
| Linux, x86-64 | 4 | 8 | 16 |
| Windows, x86-64 | 4 | 8 | 8 |
| **Arduino Uno** | 4 | **4** | 4 |

- `float` her yerde 32 bitlik IEEE 754.
- `long double` en az güvenilir olanı: Apple Silicon'da ve Windows'ta `double`'ın aynısı, x86-64 Linux'ta 80 bitlik eski bir Intel biçimi (16 byte'a dolgu ile).
- Arduino'da `double` da 4 byte; yani aslında bir `float`. Ders 3.15'te bunun bir sonucunu daha göreceğiz.

**Sabitler.** Ders 3.10'daki ekler burada da var:

| Yazım | Tip |
| --- | --- |
| `0.1`, `2.0`, `1e-3` | `double` |
| `0.1f`, `2.0f`, `1e-3f` | `float` |
| `0.1L` | `long double` |

`1e-3`, 1 × 10⁻³ = 0,001 demek; `6.022e23` de 6,022 × 10²³. Ek yazmazsan sabit **`double`**'dır; `float x = 0.1;` yazınca önce `double` bir 0,1 oluşur, sonra `float`'a dönüştürülür. Bu yüzden `float` ile çalışırken sabitlere `f` ekle.

**Yazdırmak.**

| Biçim | `22.857142f` için | |
| --- | --- | --- |
| `%f` | `22.857141` | Virgülden sonra 6 basamak |
| `%.2f` | `22.86` | Virgülden sonra 2 basamak |
| `%e` | `2.285714e+01` | Bilimsel gösterim |
| `%g` | `22.8571` | 6 anlamlı basamak, gereksiz sıfırlar yok |
| `%.9g` | `22.8571415` | 9 anlamlı basamak |

`printf`'e bir `float` verdiğinde, `printf` gibi değişken sayıda parametre alan fonksiyonlar onu önce `double`'a çevirir (Ders 3.5'teki yükseltmenin kayan nokta hali). Bu yüzden `%f` hem `float` hem `double` için çalışır. `scanf`'te ise iş farklı: `float` için `%f`, `double` için `%lf` yazmak zorundasın.

**Sınırlar** `<float.h>` başlığında:

| Sabit | Değer | Anlamı |
| --- | --- | --- |
| `FLT_MAX` | 3,40282347 × 10³⁸ | En büyük float |
| `FLT_MIN` | 1,17549435 × 10⁻³⁸ | En küçük pozitif (normal) float |
| `FLT_EPSILON` | 1,19209 × 10⁻⁷ | 1 ile ondan büyük ilk float arasındaki fark: 2⁻²³ |
| `FLT_DIG` | 6 | Kayıpsız saklanabilen ondalık basamak sayısı |

Q16.16'nın aralığı yaklaşık ±32.768'di; float'ınki 10³⁸. Bedeli hassasiyet: 24 bitlik mantis yaklaşık **7 ondalık basamak** demek. 22,857142'yi yazdırırken 9 basamak istediğimizde son basamakların "uydurma" çıkması bu yüzden. `FLT_DIG`'in 6 olması "her 6 basamaklı ondalık sayı float'a gidip geri döndüğünde aynı kalır" demek; tersi yönde, bir float'ı tam olarak geri elde edebilmek için 9 basamak yazmak gerekir. Bölüm 4'te `%.9g` bu yüzden.

---

## 7. Tamsayılarla karışınca

Ders 3.5'te usual arithmetic conversions kurallarını görürken "bir taraf küsuratlı bir sayıysa bunlardan önce başka bir kural gelir" demiştik. İşte o kural. Bir işlemin iki tarafının tipi farklıysa, sırayla:

1. Biri `long double` ise, diğeri `long double`'a çevrilir.
2. Değilse, biri `double` ise, diğeri `double`'a çevrilir.
3. Değilse, biri `float` ise, diğeri `float`'a çevrilir.
4. Hiçbiri kayan nokta değilse, Ders 3.5'teki tamsayı kuralları uygulanır.

Yani bir tarafta kayan nokta varsa, tamsayı her zaman kayan noktaya çevrilir; büyüklüğü ne olursa olsun.

```c
printf("%d\n", 7 / 2);
printf("%g\n", 7 / 2.0);
printf("%.1f\n", 1 / 2 * 3.0);
printf("%.1f\n", 3.0 * 1 / 2);
```

```
3
3.5
0.0
1.5
```

Son iki satır aynı sayılarla aynı işlemler, ama farklı sonuç. İşlemler soldan sağa yapılır: `1 / 2 * 3.0` önce `1 / 2`'yi hesaplar, iki `int`, sonuç 0; sonra 0 × 3,0 = 0,0. Kural, işlemin **tamamına** değil, her işlemin **kendi iki tarafına** uygulanıyor. `3.0 * 1 / 2`'de ise ilk işlem `3.0 * 1` = 3,0 olur ve bölme de kayan noktayla yapılır.

### Tamsayıdan float'a

Float'ın mantisi 24 bit. 2²⁴ = 16.777.216'ya kadar her tamsayı tam saklanır; ötesinde mantis yetmez ve tamsayılar da yuvarlanmaya başlar:

```c
int a = 16777217;
float f = a;
printf("%.1f\n", f);
printf("%d\n", f == a);
```

```
16777216.0
1
```

16.777.217, float'a çevrilince 16.777.216 olmuş: değer **değişti**. Ama ikinci satır "eşit" diyor. Neden? `f == a` karşılaştırmasında kural 3 uygulanıyor: `a` da float'a çevriliyor, o da 16.777.216 oluyor. Değişmiş değeri, aynı şekilde değişmiş haliyle karşılaştırdık. Ders 3.6'daki işaretli–işaretsiz karşılaştırma tuzağının kayan nokta kardeşi.

123.456.789 da float'ta 123.456.792 olur. 32 bitlik bir `int`'in her değeri bir `float`'a sığmaz; ikisi de 4 byte, ama float'ın bitlerinin 8'i üse gidiyor. clang bunun için uyarı verebilir:

```
warning: implicit conversion from 'int' to 'float' may lose precision [-Wimplicit-int-float-conversion]
```

Bu uyarı Ders 3.7'deki `-Wconversion` ile açılıyor.

### Float'tan tamsayıya

Ters yönde küsurat **atılır**, sıfıra doğru: `(int)3.99f` = 3, `(int)-3.99f` = −3. Yuvarlama değil, kesme; Ders 3.11'deki `fx_to_int` gibi. En yakına yuvarlamanın yollarını Ders 3.14'te göreceğiz.

Sayı hedef tipe sığmıyorsa, örneğin 3 milyarı `int`'e çevirmek: **undefined behavior**. Ders 3.7'deki işaretli dönüşümde sonuç "platforma bağlı"ydı; burada ondan da kötü. `-fsanitize=undefined` yakalıyor:

```
runtime error: 3e+09 is outside the range of representable values of type 'int'
```

Ve platformlar gerçekten farklı davranıyor: bilgisayarımızda (ARM) sonuç **2.147.483.647** çıktı, işlemci en yakın `int`'e doyurdu. Aynı programı x86-64 için derleyip çalıştırınca **−2.147.483.648** çıktı; x86'nın dönüşüm komutu, sığmayan her sayı için bu "geçersiz" değeri üretiyor.

---

## Alıştırmalar

**1** – Şu sayıları elle float'a çevir: işaret, üs ve mantis bitlerini ve onaltılık değerini bul. Sonra `show_float` ile kontrol et. −2,5, 0,75, 10.

**2** – Bu bit desenleri hangi sayılar? `0x41C80000`, `0xBF400000`.

**3** – Bölüm 2'de, pozitif float'ların bitlerini işaretsiz tamsayı olarak karşılaştırmanın sıralamayı koruduğunu söyledik. 1,5 ile 2,0 için kontrol et. Peki negatif sayılarda da doğru mu? −1,5 ile −2,0'yi düşün.

**4** – Bölüm 7'deki tuzağa düşmeden, `float`'a çevrilip geri `int`'e çevrildiğinde **değişen** ilk pozitif tamsayıyı bulan bir döngü yaz. Neden `(float)i == i` koşulu bu iş için işe yaramaz?

**5** – Bu döngü kaç kez döner?

```c
int count = 0;
for (float x = 0.0f; x != 1.0f; x = x + 0.1f) {
    count++;
}
```

Döngüyü, 0'dan 1'e 0,1'lik adımlarla on kez dönecek şekilde düzelt.

<details>
<summary>Cevaplar</summary>

**1** –

- −2,5 = −10,1₂ = −1,01₂ × 2¹. İşaret 1, üs 1 + 127 = 128 = `10000000`, mantis `0100…`. `1 10000000 01000000000000000000000` = **0xC0200000**.
- 0,75 = 0,11₂ = 1,1₂ × 2⁻¹. İşaret 0, üs 126 = `01111110`, mantis `1000…`. **0x3F400000**.
- 10 = 1010₂ = 1,010₂ × 2³. İşaret 0, üs 130 = `10000010`, mantis `0100…`. **0x41200000**.

**2** –

- `0x41C80000` = `0 10000011 10010000000000000000000`. Üs 131 − 127 = 4, mantis 1,1001₂ = 1 + 0,5 + 0,0625 = 1,5625. 1,5625 × 16 = **25**.
- `0xBF400000` = `1 01111110 10000000000000000000000`. Negatif, üs −1, mantis 1,1₂ = 1,5. −1,5 × 0,5 = **−0,75**.

**3** – 1,5 = `0x3FC00000`, 2,0 = `0x40000000`; tamsayı olarak da 1,5'inki küçük. Doğru. Negatiflerde **ters**: −1,5 = `0xBFC00000`, −2,0 = `0xC0000000`. Tamsayı olarak −2,0'ın bitleri daha büyük, ama −2,0 daha küçük bir sayı. Sebep işaret–büyüklük gösterimi: işaret bitinden sonrası **büyüklüğü** tutuyor, ve büyüklüğü fazla olan negatif sayı daha küçük. İkiler tümleyeninde böyle bir sorun yoktu (Ders 3.3). İşlemciler float karşılaştırmasını bu yüzden ayrı bir komutla yapar.

**4** –

```c
for (int i = 1; i > 0; i++) {
    float f = (float)i;
    if ((int)f != i) {
        printf("%d\n", i);
        break;
    }
}
```

**16.777.217** (2²⁴ + 1) yazar. `(float)i == i` koşulunda sağdaki `i` de float'a çevrilir (kural 3); iki taraf **her zaman** aynı şekilde yuvarlanır ve koşul her zaman doğru çıkar. Karşılaştırmayı `int` dünyasında yapmak gerekiyor. `(int)f` dönüşümü burada güvenli: 16.777.216 `int`'e rahatça sığıyor.

**5** – Hiç bitmez. On toplamadan sonra `x` 1,0 değil, 1,00000012 (Bölüm 5'teki tablo). `x != 1.0f` doğru kalıyor ve döngü 1,1, 1,2… diye devam ediyor; bir daha da tam olarak 1,0'a denk gelmiyor. (Ders 3.14'te göreceğimiz gibi, sayı büyüyünce bir noktada `x + 0.1f` artık `x`'i hiç değiştirmiyor; döngü sonsuza kadar aynı yerde dönüyor.) Düzeltmek için sayacı tamsayı yap ve küsuratlı değeri ondan hesapla:

```c
for (int i = 0; i < 10; i++) {
    float x = i / 10.0f;
    count++;
}
```

Kural: **döngü sayacı olarak kayan nokta kullanma**, ve kayan nokta sayıları `==` ya da `!=` ile karşılaştırmadan önce iki kez düşün.

</details>

---

## Kaynaklar

- IEEE Std 754-2019, *IEEE Standard for Floating-Point Arithmetic*.
- David Goldberg, "What Every Computer Scientist Should Know About Floating-Point Arithmetic", *ACM Computing Surveys*, 1991.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.4: kayan nokta.
- C standardı (ISO/IEC 9899:2018), §5.2.4.2.2: `<float.h>`; §6.3.1.4: kayan nokta ile tamsayı arasında dönüşüm; §6.3.1.8: usual arithmetic conversions.

**Sıradaki ders:** Özel float değerleri. Sıfıra bölünce ne oluyor, kendine eşit olmayan sayı hangisi, ve iki float nasıl karşılaştırılır?
