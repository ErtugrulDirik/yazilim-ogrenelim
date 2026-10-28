---
title: "3.14 double ve hassasiyet"
description: "64 bitlik double'ın yapısı ve sınırları; komşu iki kayan nokta sayı arasındaki boşluk (ULP), en yakına yuvarlama ve diğer yuvarlama modları, uzun toplamlarda hatanın birikmesi ve yutulması, Kahan toplama algoritması ve -ffast-math'in onu nasıl bozduğu."
---

Ders 3.12'de float'ın yaklaşık 7 ondalık basamak tuttuğunu gördük. Bir fizik simülasyonu, bir harita uygulaması ya da bir banka hesabı için bu çok az. C'de eksiz yazılan her küsuratlı sabitin (`0.1`, `2.5`) `double` olması bu yüzden: C, varsayılan kayan nokta tipi olarak `double`'ı seçmiş.

Bu derste üç soru var: `double` float'tan ne kadar iyi? İki kayan nokta sayı arasında **ne kadar boşluk** var? Ve uzun hesaplarda biriken hatayı nasıl küçültürüz?

---

## 1. double: 64 bit

`double`, IEEE 754'ün **çift hassasiyetli** (double precision) biçimi. Fikir Ders 3.12'dekinin aynısı, sadece her parça daha büyük:

| | `float` | `double` |
| --- | --- | --- |
| Boyut | 32 bit | 64 bit |
| İşaret | 1 bit | 1 bit |
| Üs | 8 bit | 11 bit |
| Mantis | 23 bit (+1 gizli) | 52 bit (+1 gizli) |
| Bias | 127 | 1023 |
| En büyük | 3,4 × 10³⁸ | 1,8 × 10³⁰⁸ |
| En küçük normal | 1,2 × 10⁻³⁸ | 2,2 × 10⁻³⁰⁸ |
| En küçük denormal | 1,4 × 10⁻⁴⁵ | 4,9 × 10⁻³²⁴ |
| Epsilon (`FLT_`/`DBL_EPSILON`) | 1,2 × 10⁻⁷ | 2,2 × 10⁻¹⁶ |
| Kayıpsız ondalık basamak (`_DIG`) | 6 | 15 |
| Geri dönüş için gereken basamak | 9 | 17 |

`<float.h>`'teki sabitlerin adları da `FLT_` yerine `DBL_` ile başlıyor: `DBL_MAX`, `DBL_MIN`, `DBL_EPSILON`, `DBL_DIG`. Ders 3.13'teki özel değerler (sonsuz, NaN, ±0, denormaller) aynı şekilde var; tek fark üs alanının "hepsi 1" değerinin 255 değil 2047 olması.

Ders 3.12'deki gibi `memcpy` ile bitlere bakarsak:

| Sayı | `double` bitleri (onaltılık) |
| --- | --- |
| 1,0 | `0x3FF0000000000000` |
| 0,1 | `0x3FB999999999999A` |

1,0'ın üs alanı `0x3FF` = 1023, yani gerçek üs 0. 0,1'in mantisi `9999…`, yani ikilikte `1001 1001 1001…`: Ders 3.12'de float'ta gördüğümüz tekrar, bu sefer 52 bit boyunca. Sondaki `A` (`1010`), float'taki `D` gibi: kesilen kısım yarıdan büyük olduğu için son bit yukarı yuvarlanmış.

**Yazdırmak.** Bir `double`'ı tam olarak geri elde edebilmek için 17 anlamlı basamak gerekiyor; Ders 3.12'nin başında `%.17g` kullanmamızın sebebi bu. `%f` ve `%g`'nin varsayılan 6 basamağı, `double`'ın farklı değerlerini aynı gösterebilir: `0.1 + 0.2` `%g` ile `0.3` diye yazılır.

### Tamsayılar

Mantis 53 bit (gizli bitle). Ders 3.12'deki mantıkla, 2⁵³ = **9.007.199.254.740.992**'ye kadar her tamsayı `double`'da tam saklanır:

```c
double big = 9007199254740992.0;
printf("%.1f\n", big + 1);
printf("%.1f\n", big + 2);
```

```
9007199254740992.0
9007199254740994.0
```

2⁵³ + 1 saklanamıyor; en yakın `double` 2⁵³'ün kendisi. Bu sayı sana tanıdık gelebilir: JavaScript'te bütün sayılar `double`'dır, ve `Number.MAX_SAFE_INTEGER` tam olarak 2⁵³ − 1.

İyi haber: 32 bitlik her `int` bir `double`'a **tam olarak** sığar. Ders 3.12'deki `int` → `float` kaybı (16.777.217 → 16.777.216) `double`'da olmaz. `int64_t` için ise aynı sorun geri döner: 2⁵³'ten büyük bir `int64_t`, `double`'a çevrilince yuvarlanır.

---

## 2. ULP: komşular arasındaki boşluk

Ders 3.11'deki Q16.16'da iki komşu sayı arasındaki fark her yerde aynıydı: 1/65.536. Kayan noktada öyle değil.

1 ile 2 arasını düşün. Bu aralıktaki her `double`, 1,mantis × 2⁰ biçiminde; mantis 52 bit olduğu için aralık 2⁵² eşit parçaya bölünmüş. Komşular arasındaki fark 2⁻⁵². 2 ile 4 arasında ise sayılar 1,mantis × 2¹: yine 2⁵² parça, ama aralık iki kat geniş; fark 2⁻⁵¹. Her 2'nin kuvvetinde boşluk **ikiye katlanıyor**.

Bir sayı ile ondan büyük ilk komşusu arasındaki farka **ULP** denir (unit in the last place, son basamağın birimi): sayının mantisinin son bitinin değeri. `<math.h>`'teki `nextafter(x, y)`, `x`'ten `y`'ye doğru giderken karşılaşılan ilk `double`'ı verir; bununla ULP'yi ölçebiliriz:

```c
#include <stdio.h>
#include <math.h>

double ulp(double x) {
    return nextafter(x, INFINITY) - x;
}

int main(void) {
    double values[] = {0.1, 1.0, 2.0, 1000.0, 1e6, 1e16, 1e20};
    int count = sizeof(values) / sizeof(values[0]);
    for (int i = 0; i < count; i++) {
        printf("ulp(%g) = %g\n", values[i], ulp(values[i]));
    }
    return 0;
}
```

Aynı ölçümü `float` için `nextafterf` ile de yaptık:

| x | `double` ULP | `float` ULP |
| --- | --- | --- |
| 0,1 | 1,4 × 10⁻¹⁷ | 7,5 × 10⁻⁹ |
| 1 | 2,2 × 10⁻¹⁶ | 1,2 × 10⁻⁷ |
| 2 | 4,4 × 10⁻¹⁶ | 2,4 × 10⁻⁷ |
| 1.000 | 1,1 × 10⁻¹³ | 6,1 × 10⁻⁵ |
| 1.000.000 | 1,2 × 10⁻¹⁰ | **0,0625** |
| 16.777.216 (2²⁴) | 3,7 × 10⁻⁹ | **2** |
| 10¹⁶ | **2** | 1,1 × 10⁹ |
| 10²⁰ | **16.384** | 8,8 × 10¹² |

Tablonun söylediği:

- **ULP sayıyla birlikte büyüyor.** 10²⁰ civarında iki `double` arasında 16.384'lük bir boşluk var; Ders 3.13'te mutlak toleransın bu yüzden işe yaramadığını görmüştük.
- **Bağıl boşluk yaklaşık sabit.** ULP / x her satırda `double` için yaklaşık 10⁻¹⁶, `float` için 10⁻⁷. Kayan nokta, sayının **büyüklüğüne göre** aynı hassasiyeti verir: 15–16 basamak ya da 7 basamak, virgül nerede olursa olsun.
- 1 için ULP tam olarak `DBL_EPSILON` = 2⁻⁵². Epsilon'un tanımı bu.
- `float`'ta 1.000.000 civarında boşluk 0,0625: float, bir milyon liranın kuruşlarını tutamaz.

### Tek bir işlemin hatası

IEEE 754'ün en önemli sözü şu: toplama, çıkarma, çarpma, bölme ve karekök, **sanki sonsuz hassasiyetle hesaplanmış ve sonra en yakın sayıya yuvarlanmış** gibi sonuç verir. Yani tek bir işlemin hatası en fazla **yarım ULP**'dir. 0,1 + 0,2'nin 0,30000000000000004 çıkması bu sözün ihlali değil: toplama kusursuz yapıldı, ama girdiler zaten 0,1 ve 0,2 değildi (Ders 3.12).

```c
printf("%d\n", 1.0 + DBL_EPSILON / 2 == 1.0);
printf("%d\n", 1.0 + DBL_EPSILON == 1.0);
```

```
1
0
```

1'e yarım ULP eklemek 1'i değiştirmiyor; tam bir ULP eklemek değiştiriyor. Birincide sonuç iki komşunun tam ortasına düştü; hangisinin seçildiğini bir sonraki bölümde göreceğiz.

---

## 3. Yuvarlama modları

Gerçek sonuç iki komşu `double`'ın arasına düştüğünde hangisi seçilecek? IEEE 754 dört yuvarlama modu tanımlar:

| Mod | `<fenv.h>` adı | Kural |
| --- | --- | --- |
| En yakına | `FE_TONEAREST` | En yakın komşu; tam ortadaysa son biti 0 olan (**çift**) komşu |
| Yukarı | `FE_UPWARD` | Her zaman büyük olan komşu (+∞'a doğru) |
| Aşağı | `FE_DOWNWARD` | Her zaman küçük olan komşu (−∞'a doğru) |
| Sıfıra doğru | `FE_TOWARDZERO` | Mutlak değeri küçük olan komşu |

Varsayılan mod **en yakına**; şimdiye kadar gördüğümüz her sonuç bu modla hesaplandı. Modu `<fenv.h>`'teki `fesetround` ile değiştirip 1/3 ve −1/3'ü `float` ile hesapladık:

```c
#include <stdio.h>
#include <fenv.h>

#pragma STDC FENV_ACCESS ON

int main(void) {
    int modes[] = {FE_TONEAREST, FE_UPWARD, FE_DOWNWARD, FE_TOWARDZERO};
    volatile float one = 1.0f;
    volatile float three = 3.0f;
    for (int i = 0; i < 4; i++) {
        fesetround(modes[i]);
        printf("%.10f  %.10f\n", one / three, -one / three);
    }
    fesetround(FE_TONEAREST);
    return 0;
}
```

| Mod | 1/3 | −1/3 |
| --- | --- | --- |
| `FE_TONEAREST` | 0,3333333433 | −0,3333333433 |
| `FE_UPWARD` | 0,3333333433 | −0,3333333134 |
| `FE_DOWNWARD` | 0,3333333134 | −0,3333333433 |
| `FE_TOWARDZERO` | 0,3333333134 | −0,3333333134 |

İki komşu float var: 0,3333333134 ve 0,3333333433. 1/3 ikisinin arasında; her mod birini seçiyor.

- `#pragma STDC FENV_ACCESS ON`, compiler'a "bu dosyada yuvarlama modunu değiştiriyorum" der; yoksa compiler hesapları derleme sırasında varsayılan modla yapıp sonucu koda gömebilir. Ders 3.21'de göreceğimiz `volatile` de aynı amaçla: compiler'ın `1.0f / 3.0f`'ı önceden hesaplamasını engelliyor.
- Yukarı ve aşağı modlarının bilinen bir kullanımı **aralık aritmetiği**: aynı hesabı bir kez aşağı, bir kez yukarı yuvarlayarak yaparsan, gerçek sonucun kesinlikle bu iki değerin arasında olduğunu bilirsin.
- Programların neredeyse hiçbiri modu değiştirmez. Değiştirirsen işin bitince geri al; mod, programın geri kalanındaki **her** işlemi etkiler.

### Neden "çifte"?

Tam ortaya düşen sonuçlar için "her zaman yukarı" kuralı, okulda öğrendiğimiz kural: 2,5 → 3. Ama bu kural, çok sayıda yuvarlamada sonucu sistematik olarak **büyütür**: ortadaki her sayı yukarı gidiyor, hiçbiri aşağı gitmiyor. "Çifte yuvarla" kuralında ortadaki sayıların yarısı yukarı, yarısı aşağı gider ve hatalar birbirini götürür. Bankacılıkta da kullanıldığı için bu kurala **banker yuvarlaması** da denir.

`<math.h>`'te bir `double`'ı tamsayı değerine yuvarlayan birkaç fonksiyon var. Ders 3.12'de `(int)` dönüşümünün kestiğini görmüştük; işte diğer seçenekler:

| x | `(int)x` | `trunc` | `floor` | `ceil` | `round` | `rint` |
| --- | --- | --- | --- | --- | --- | --- |
| 2,7 | 2 | 2 | 2 | 3 | 3 | 3 |
| 2,5 | 2 | 2 | 2 | 3 | **3** | **2** |
| 1,5 | 1 | 1 | 1 | 2 | 2 | 2 |
| −2,5 | −2 | −2 | −3 | −2 | **−3** | **−2** |

- `trunc`: sıfıra doğru, `(int)` gibi.
- `floor` / `ceil`: aşağı / yukarı.
- `round`: en yakına; tam ortadaysa **sıfırdan uzağa** (okul kuralı).
- `rint`: o anki yuvarlama moduyla; varsayılan modda en yakına, ortadaysa **çifte**.

Bunların hepsi `double` döndürür. Sonucu doğrudan bir tamsayı olarak istiyorsan `lround` (`long` döndürür) kullan: `lround(2.7)` = 3. Bir küsuratlı sayıyı en yakın `int`'e çevirmenin doğru yolu, `(int)` değil, bu.

---

## 4. Hata birikir

Tek bir işlem en fazla yarım ULP hata yapıyor. Peki on milyon işlem? 0,1'i `n` kez toplayalım:

```c
float naive_sum(float x, int n) {
    float sum = 0.0f;
    for (int i = 0; i < n; i++) {
        sum = sum + x;
    }
    return sum;
}
```

| n | `float` toplam | `double` toplam | Doğrusu |
| --- | --- | --- | --- |
| 10 | 1,00000012 | 0,99999999999999989 | 1 |
| 1.000 | 99,9990463 | 99,999999999998593 | 100 |
| 1.000.000 | 100.958,344 | 100.000,00000133288 | 100.000 |
| 10.000.000 | 1.087.937 | 999.999,99983897537 | 1.000.000 |
| 100.000.000 | **2.097.152** | 9.999.999,9811294507 | 10.000.000 |

(`double` sütunu aynı fonksiyonun `double` hali, 0,1 ile.) `float` toplam bir milyonda %1, on milyonda %9 yanlış; yüz milyonda ise doğru cevabın **beşte biri**. Ne oldu?

### Yutulma

Toplam büyüdükçe ULP'si de büyüyor. 0,1 eklemek, toplamı **en yakın** float'a yuvarlamak demek:

- Toplam 2²⁰ = 1.048.576 ile 2²¹ arasındayken ULP 0,125. `sum + 0.1`'in en yakın komşusu `sum + 0.125`: her adımda 0,1 değil **0,125** ekleniyor. On milyonda sonucun fazla çıkması bu yüzden.
- Toplam 2²¹ = **2.097.152**'ye ulaşınca ULP 0,25 oluyor. 0,1, yarım ULP'den (0,125) küçük; `sum + 0.1`'in en yakın komşusu **`sum`'ın kendisi**. Toplam artık hiç değişmiyor.

Küçük bir sayının büyük bir sayıya eklenince kaybolmasına **yutulma** (absorption) denir. Ders 3.12'nin 5. alıştırmasında söz ettiğimiz, sonsuza kadar aynı yerde dönen döngü bu. Float ile saymak da aynı duvara çarpar: `1.0f`'ı 20 milyon kez toplayınca sonuç 16.777.216'da (2²⁴) takılıp kalıyor; orada ULP 2, ve 1 yarım ULP'ye eşit olduğu için "çifte yuvarla" kuralı toplamı yerinde bırakıyor.

`double` da aynı sorunu yaşıyor, sadece çok daha geç: yüz milyon toplamada hata 0,02. Çoğu zaman bu yeterli; ama hesap daha uzunsa ya da girdiler daha kötüyse yetmeyebilir.

---

## 5. Kahan toplama

1965'te William Kahan (Ders 3.13'te denormalleri savunan kişi) basit bir fikir yayımladı: her toplamada kaybolan küçük parçayı **ayrı bir değişkende** tut ve bir sonraki toplamada geri ekle.

```c
float kahan_sum(float x, int n) {
    float sum = 0.0f;
    float c = 0.0f;
    for (int i = 0; i < n; i++) {
        float y = x - c;
        float t = sum + y;
        c = (t - sum) - y;
        sum = t;
    }
    return sum;
}
```

- `y`: eklenecek sayı, bir önceki adımda kaybolan parçayla düzeltilmiş.
- `t`: yeni toplam, yuvarlanmış.
- `t - sum`: toplama **gerçekte** eklenen miktar. `sum` ile `t` birbirine yakın olduğu için bu çıkarma tamdır, hiç yuvarlama yapmaz.
- `c = (t - sum) - y`: gerçekte eklenen ile eklenmesi gereken arasındaki fark. Yuvarlamanın kaybettiği (ya da fazladan eklediği) parça, eksi işaretiyle.

### Tracing

Fikri görmek için, sadece **4 anlamlı basamak** tutan ondalık bir bilgisayar düşünelim. Toplam 1000; üç kez 1,234 ekliyoruz. Doğru cevap 1003,702.

Sıradan toplama: 1000 + 1,234 = 1001,234 → **1001**; 1002,234 → **1002**; 1003,234 → **1003**. Her adımda 0,234 kayboldu; hata 0,702.

Kahan:

| Adım | y = x − c | t = sum + y (4 basamak) | t − sum | c = (t − sum) − y | sum |
| --- | --- | --- | --- | --- | --- |
| Başta | | | | 0 | 1000 |
| 1 | 1,234 | 1001,234 → 1001 | 1 | −0,234 | 1001 |
| 2 | 1,468 | 1002,468 → 1002 | 1 | −0,468 | 1002 |
| 3 | 1,702 | 1003,702 → **1004** | 2 | +0,298 | 1004 |

Kaybolan parçalar `c`'de birikti ve üçüncü adımda toplamı bir basamak yukarı itecek kadar büyüdü. Sonuç **1004**: hata 0,298, yani 4 basamaklı bir bilgisayarın yapabileceği en iyi sonuç (1003,702'ye en yakın 4 basamaklı sayı). Üstelik `c` = 0,298, toplamın ne kadar **fazla** olduğunu hâlâ biliyor.

### Sonuçlar

| n | `float` sıradan | `float` Kahan | `double` sıradan |
| --- | --- | --- | --- |
| 1.000 | 99,9990463 | **100** | 99,999999999998593 |
| 1.000.000 | 100.958,344 | **100.000** | 100.000,00000133288 |
| 10.000.000 | 1.087.937 | **1.000.000** | 999.999,99983897537 |
| 100.000.000 | 2.097.152 | **10.000.000** | 9.999.999,9811294507 |

Kahan toplaması `float` ile, sıradan `double` toplamadan **daha iyi** sonuç verdi. Bedeli, her adımda bir yerine dört işlem. (Kahan'ın sonuçları, 0,1'e değil `0.1f`'e, yani 0,100000001490116'ya göre en iyi sonuç; bu kadar büyük toplamlarda o fark float'ın ULP'sinin altında kalıyor.)

### -ffast-math Kahan'ı siler

Ders 3.13'te `-ffast-math`'in NaN kontrollerini sildiğini görmüştük. Bu ayar compiler'a, kayan nokta işlemlerini **matematikteki** gibi düzenleme izni de verir. Matematikte:

> c = (t − sum) − y = ((sum + y) − sum) − y = 0

Compiler da tam olarak bunu yapıyor. Aynı programı `-O2 -ffast-math` ile derleyince:

| n | `float` sıradan | `float` Kahan |
| --- | --- | --- |
| 10.000.000 | 1.005.958,56 | 1.005.958,56 |
| 100.000.000 | 9.906.993 | 9.906.993 |

Kahan ile sıradan toplama artık **aynı** sonucu veriyor; ürettiği assembly'de `c`'nin hesabından hiçbir iz yok. (Sıradan toplamanın sonucu da değişti: compiler toplamayı dört ayrı ara toplama bölüp aynı anda yürüttü, bu da yuvarlamaların sırasını değiştirdi. Faz 11'de bu tekniğe, SIMD'ye ayrıntılı bakacağız.)

Kayan nokta aritmetiğinde **işlem sırası önemlidir**: (a + b) + c ile a + (b + c) farklı sonuç verebilir. Kahan algoritması tam olarak bu farka dayanıyor. Hassas hesaplar yapan bir kodu `-ffast-math` ile derleme.

### Daha basit yollar

- **Daha geniş bir toplayıcı.** Girdiler `float` ise toplamı `double` ile tutmak, çoğu durumda Kahan kadar iyi sonuç verir ve tek satır değişiklik. 0,1f'i yüz milyon kez `double` bir toplama ekleyince 10.000.000,149 çıkıyor: `0.1f`'in gerçek değerinin tam yüz milyon katı.
- **Sıralı toplama.** Küçük sayıları önce toplamak, yutulmayı azaltır (4. alıştırma).
- **İkili toplama** (pairwise summation): sayıları ikişer ikişer toplayıp, sonuçları yine ikişer ikişer toplamak. Hata, toplanan sayı sayısıyla çok yavaş büyür; Python'un NumPy kütüphanesi bunu kullanır. Özyinelemeli yazmak kolay (Ders 2.8), ama sayıları bir array'de tutmayı gerektiriyor.

---

## Alıştırmalar

**1** – 1.000.000.000 (bir milyar) civarında `double`'ın ve `float`'ın ULP'si ne? (İpucu: 2²⁹ = 536.870.912 < 10⁹ < 2³⁰.) `float` ile 1.000.000.001 saklanabilir mi?

**2** – Para tutarlarını `float` ile kuruş hassasiyetinde tutmak istiyorsun. Hangi tutardan itibaren komşu iki float arasındaki fark 1 kuruştan (0,01) büyük olur? `double` için?

**3** – 0,5, 1,5, 2,5 ve 3,5'i önce `round`, sonra `rint` ile yuvarlayıp topla. Gerçek toplam 8. Hangisi daha yakın? Neden?

**4** – 1/1² + 1/2² + 1/3² + … serisi π²/6 ≈ 1,644934067'ye yakınsar. İlk on milyon terimi `float` ile iki sırada topla: büyükten küçüğe (`i` = 1'den N'e) ve küçükten büyüğe (`i` = N'den 1'e). Hangisi daha doğru? Neden?

**5** – `kahan_sum`'ın `double` halini yaz ve 0,1'i yüz milyon kez topla. Sonucu sıradan `double` toplamla karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – 10⁹, [2²⁹, 2³⁰) aralığında.

- `double`: ULP = 2²⁹ × 2⁻⁵² = 2⁻²³ ≈ **1,2 × 10⁻⁷**.
- `float`: ULP = 2²⁹ × 2⁻²³ = 2⁶ = **64**.

`float` ile 1.000.000.001 saklanamaz: 10⁹ civarındaki float'lar 64'er 64'er artıyor. `nextafterf` ile ölçtük: 64.

**2** – `float`'ta ULP, [2ᵉ, 2ᵉ⁺¹) aralığında 2ᵉ⁻²³. 2ᵉ⁻²³ > 0,01 olması için e ≥ 17 gerekir: 2¹⁷ = **131.072 TL**. Bu tutarın üstünde ULP 0,015625; `131072.01f` aslında 131.072,0156 olarak saklanıyor. (131.072'nin altında ULP 0,0078; kuruşlar yaklaşık olarak ayırt edilebiliyor ama yine de tam değil, çünkü 0,01 ikilikte tam değil.) `double` için 2ᵉ⁻⁵² > 0,01 → e ≥ 46: 2⁴⁶ ≈ **70 trilyon TL**. Yine de: para için Ders 3.11'deki gibi kuruş cinsinden bir tamsayı kullan.

**3** – `round`: 1 + 2 + 3 + 4 = **10**. `rint`: 0 + 2 + 2 + 4 = **8**. `rint` tam doğru çıktı. `round` ortadaki her sayıyı yukarı (sıfırdan uzağa) yuvarladı ve her biri 0,5 hata ekledi; `rint`'te iki sayı yukarı, iki sayı aşağı gitti ve hatalar birbirini götürdü.

**4** –

```c
float forward = 0.0f;
for (int i = 1; i <= N; i++) {
    forward = forward + 1.0f / ((float)i * i);
}
float backward = 0.0f;
for (int i = N; i >= 1; i--) {
    backward = backward + 1.0f / ((float)i * i);
}
```

Ölçtük: büyükten küçüğe **1,64472532**, küçükten büyüğe **1,64493394**. Gerçek değer (ilk on milyon terim için) yaklaşık 1,6449339; küçükten büyüğe toplam neredeyse tam. Büyükten küçüğe toplarken toplam hızla 1,6'ya ulaşıyor; oradaki ULP 1,2 × 10⁻⁷ ve 1/i², i yaklaşık 4.096'yı geçince bunun yarısının altına düşüyor. Ondan sonraki milyonlarca terim **yutuluyor**. Küçükten başlayınca küçük terimler önce birbirleriyle toplanıp anlamlı bir büyüklüğe ulaşıyor. (`(float)i * i` yazdık, çünkü `i * i` `int` olarak 46.341'den sonra taşar; Ders 3.8.)

**5** –

```c
double kahan_sum_d(double x, int n) {
    double sum = 0.0;
    double c = 0.0;
    for (int i = 0; i < n; i++) {
        double y = x - c;
        double t = sum + y;
        c = (t - sum) - y;
        sum = t;
    }
    return sum;
}
```

Kahan: **10000000.0000000000**. Sıradan: 9999999.9811294507. Kahan'ın hatası `%.10f` ile görünmeyecek kadar küçük.

</details>

---

## Kaynaklar

- David Goldberg, "What Every Computer Scientist Should Know About Floating-Point Arithmetic", *ACM Computing Surveys*, 1991: ULP, yuvarlama ve Kahan toplama.
- William Kahan, "Further Remarks on Reducing Truncation Errors", *Communications of the ACM*, 8(1), 1965.
- Nicholas Higham, *Accuracy and Stability of Numerical Algorithms* (2. baskı), Bölüm 4: toplama.
- C standardı (ISO/IEC 9899:2018), §7.6: `<fenv.h>` ve yuvarlama modları; §7.12.9: `round`, `rint`, `trunc`, `floor`, `ceil`.

**Sıradaki ders:** Vücut kitle indeksi dört yolla. `int`, ölçekli `int`, Q16.16 ve `double`: sonuçları ve makine kodları yan yana.
