---
title: "5.18 Float bit hileleri"
description: "Bir float'ın bitlerini tamsayı gibi kullanmak: pozitif float'ların bit deseni sıralamasının değer sıralamasıyla aynı olması (ve negatifleri de kapsayan monoton anahtar dönüşümü), ve ünlü hızlı ters karekök — 0x5f3759df sihirli sayısıyla bir ilk tahmin üretip bir Newton-Raphson adımıyla düzeltmek, neden çalıştığı (log yaklaşımı) ve ölçülen %0.17 hata."
---

Ders 3.12'de bir float'ın bitlerini (işaret, üs, kesir) incelemiş, Ders 4.27'de union ile bu bitlere bakmıştık. Bu derste bir adım ileri gidip float'ın bitlerini **tamsayı gibi kullanıyoruz** — ne için tasarlandığından farklı amaçlarla. İki klasik: float'ları tamsayı karşılaştırmasıyla sıralamak, ve bir sayının ters karekökünü (`1/√x`) neredeyse bedavaya hesaplayan ünlü **hızlı ters karekök**. Bitleri bir tipten alıp başka tip gibi okumak için Ders 3.9/4.5'teki `memcpy` yöntemini kullanacağız (union da olurdu; Ders 4.27).

---

## 1. Float'ları tamsayı gibi karşılaştırmak

IEEE 754 (Ders 3.12) bilerek öyle tasarlanmış ki, bir float'ın bit deseni (işaret + üs + kesir, bu sırayla) **pozitif** sayılar için, değerle aynı sırada artıyor. Yani iki pozitif float'ı, bitlerini `uint32_t` olarak karşılaştırarak sıralayabilirsin:

```c
uint32_t bits(float f) {
    uint32_t i;
    memcpy(&i, &f, 4);
    return i;
}
// pozitif a, b icin: a < b  <=>  bits(a) < bits(b)
```

Bütün pozitif float aralığında (denormal + normal) doğruladık: bit deseni sıralaması değer sıralamasıyla **birebir** aynı, sıfır hata. Neden: üs, kesirden daha yüksek bitlerde durduğu için (Ders 3.12'deki `1 + 8 + 23` düzeni), daha büyük bir float her zaman daha büyük bir bit desenine sahip — üs büyükse sayı da büyük, üs eşitse kesir belirliyor.

Ama **negatiflerde bozulur**: işaret biti (en üst bit) 1 olunca, bit deseni olarak en büyük görünürler, oysa değerce en küçüktürler. `-2.0` bit deseni, `-1.0`'ınkinden büyük (daha büyük mutlak değer), ama `-2.0 < -1.0`. Hem pozitif hem negatifi doğru sıralayan bir **monoton anahtar** dönüşümü:

```c
uint32_t mono_key(float f) {
    uint32_t i;
    memcpy(&i, &f, 4);
    return (i & 0x80000000u) ? ~i : (i | 0x80000000u);
}
```

- **Negatifse** (işaret biti 1): bütün bitleri ters çevir (`~i`). Bu, negatiflerin kendi aralarındaki ters sırasını düzeltir ve onları pozitiflerin altına taşır.
- **Pozitifse**: sadece işaret bitini 1 yap (`i | 0x80000000`). Pozitifleri negatiflerin üstüne taşır.

```
   -100 -> 0x3d37ffff
     -2 -> 0x3fffffff
     -1 -> 0x407fffff
      0 -> 0x80000000
    0.5 -> 0xbf000000
      1 -> 0xbf800000
    100 -> 0xc2c80000
```

Artık `mono_key(a) < mono_key(b)` bütün float'lar için `a < b` ile aynı — tam aralıkta doğruladık, sıfır hata. Bu dönüşüm, float'ları **radix sort** (Faz 9) gibi tamsayı sıralama algoritmalarıyla sıralamayı mümkün kılar: float'ları `mono_key` ile tamsayıya çevir, tamsayı sırala, geri çevir. Float karşılaştırmasının yavaş olduğu ya da olmadığı donanımlarda da işe yarar.

---

## 2. Hızlı ters karekök

Bilgisayar grafiklerinin en ünlü kod parçası. `1/√x`, 3B grafikte bir vektörü normalize etmek için sürekli gerekir (ışık hesapları), ve karekök + bölme pahalıdır (Ders 5.13). Quake III'ün kaynak kodunda bulunan bu fonksiyon, float bitlerini kullanarak `1/√x`'i çok hızlı, kabul edilebilir bir hatayla hesaplıyor:

```c
float fast_rsqrt(float x) {
    float xhalf = 0.5f * x;
    uint32_t i;
    memcpy(&i, &x, sizeof i);          // float bitlerini int gibi oku
    i = 0x5f3759df - (i >> 1);          // sihirli sayi: ilk tahmin
    memcpy(&x, &i, sizeof x);
    x = x * (1.5f - xhalf * x * x);     // bir Newton-Raphson adimi
    return x;
}
```

```
x        fast_rsqrt     1/sqrt(x)      hata%
1        0.99830717     1.00000000     0.1693
4        0.49915358     0.50000000     0.1693
0.25     1.99661434     2.00000000     0.1693
2        0.70693004     0.70710677     0.0250
100      0.09984488     0.10000000     0.1551
```

Tek bir çarpma, bir kaydırma, bir çıkarma ile başlayıp bir Newton adımıyla düzeltiyor; sonuç **%0.17**'den az hatayla `1/√x`. İki parçası var.

### Sihirli sayı: log yaklaşımı

`i = 0x5f3759df - (i >> 1)` satırı neden işe yarıyor? Ders 3.12'den: bir float'ın bit deseni, kabaca sayının **log₂**'siyle orantılı (üs bitleri doğrudan `log₂`'nin tam kısmı, kesir bitleri kesirli kısmına yakın). Yani float bitlerini tamsayı olarak okumak, kabaca `log₂ x`'i (ölçeklenmiş) vermek demek.

`1/√x`'in logaritması: `log₂(1/√x) = -½ log₂ x`. Bit düzeyinde bu, "bit desenini ikiye böl (`>> 1`), negatifle, bir sabit ekle" demek — tam olarak `0x5f3759df - (i >> 1)`. Sabit `0x5f3759df`, hem üssün kaydırılmasını (`-½` ve bias düzeltmesi) hem de log yaklaşımındaki hatayı en aza indirecek şekilde seçilmiş (bu "en iyi" sabit üzerine makaleler yazıldı; `0x5f375a86` biraz daha iyi). Sonuç, `1/√x`'in **ilk tahmini** — %3-4 hatayla kaba ama bedava.

### Newton adımı

İlk tahmin kaba; bir **Newton-Raphson** adımı onu hassaslaştırıyor. `y = 1/√x` denklemini çözmek, `f(y) = 1/y² - x = 0`'ın kökünü bulmak. Newton'ın formülü bu denklem için `y' = y(1.5 - 0.5·x·y²)`'e sadeleşir — kodun son satırı. Bir adım, %3-4 hatayı %0.17'ye indiriyor; iki adım %0.0005'e (4. alıştırma). Newton-Raphson'ı Faz 6'da ayrıntısıyla göreceğiz; burada bir adımın tahmini kaç kat iyileştirdiğini görüyoruz.

Bugün çoğu işlemcide `rsqrt` için özel bir komut var (SSE'de `rsqrtss`, ARM'da `frsqrte`), bu yüzden bu numara artık hız için **gerekmiyor** — donanım daha hızlı ve hassas. Ama fikir — "float bitlerini tamsayı gibi yorumlayıp log aritmetiği yapmak" — hâlâ öğretici, ve bu fazın temasının zirvesi: **bitlerin anlamı, onlara hangi gözle baktığına bağlı**.

---

## 3. memcpy, union, ve strict aliasing

İki örnekte de float bitlerini `uint32_t` olarak okumak için `memcpy` kullandık. Neden doğrudan `*(uint32_t*)&x` değil? Ders 4.5'teki **strict aliasing**: bir `float`'a `uint32_t *` ile bakmak undefined behavior. İki tanımlı yol var:

- **`memcpy`** (Ders 3.9): her derleyicide, her dilde tanımlı; derleyici zaten tek bir komuta optimize eder (kopya olmaz). En taşınabilir.
- **union** (Ders 4.27): C'de tanımlı (C++'ta değil). `union { float f; uint32_t i; }`.

Quake III'ün orijinal kodu `*(long*)&x` kullanıyordu — teknik olarak UB, ve modern derleyicilerde `-O2` ile bozulabilir. Doğrusu `memcpy` ya da union. Bu, Ders 4.5 ve 4.27'deki tip punning kurallarının gerçek bir sonucu: ünlü bir kod bile, dilin kurallarına göre yanlış yazılmış olabilir.

---

## Alıştırmalar

**1** – `bits(1.0f)`, `bits(2.0f)`, `bits(0.5f)`'i hesapla (Ders 3.12'deki IEEE 754). Bit desenleri değerlerle aynı sırada mı (`0.5 < 1.0 < 2.0`)? Üs bitlerinin kesir bitlerinden yüksek konumda olması bunu nasıl sağlıyor?

**2** – `mono_key`'in tersini (`mono_key_inverse`) yaz: bir anahtarı geri float'a çevir. Negatif ve pozitif durumları nasıl ayırıyorsun (ipucu: dönüşümden sonra en üst bit)? Round-trip'i doğrula.

**3** – `fast_rsqrt`'teki Newton adımını (`x = x * (1.5f - xhalf * x * x)`) kaldırıp sadece sihirli sayı tahminini döndür. Hata ne kadar (yaklaşık %3-4)? Bir adım ekleyince neden %0.17'ye iniyor?

**4** – `fast_rsqrt`'e **ikinci** bir Newton adımı ekle (aynı satırı tekrar et). Hata ne oluyor (yaklaşık %0.0005)? Her Newton adımı hatayı neden kabaca kareliyor (hassas basamak sayısını ikiye katlıyor)?

**5** – `0x5f3759df` yerine `0x5f400000` (daha basit, sadece üs kaydırma) kullan. Hata artar mı? Sihirli sayının alt bitleri (`0x...3759df`) log yaklaşımının hatasını düzeltiyor; bunları atmak neden tahmini kötüleştirir ama Newton adımı yine de çoğunu telafi eder?

<details>
<summary>Cevaplar</summary>

**1** – `bits(0.5f) = 0x3F000000`, `bits(1.0f) = 0x3F800000`, `bits(2.0f) = 0x40000000` (Ders 3.12). Sıra: `0x3F000000 < 0x3F800000 < 0x40000000`, yani `0.5 < 1.0 < 2.0` — değerle aynı. Üs bitleri (bit 23-30) kesir bitlerinden (bit 0-22) **yüksek** konumda olduğu için, daha büyük üslü (daha büyük) bir sayı her zaman daha büyük bir bit desenine sahip; üs eşitse kesir belirler. IEEE 754'ün bu düzeni (işaret, sonra üs, sonra kesir) bilerek, pozitiflerin tamsayı olarak sıralanabilmesi için seçilmiş.

**2** –

```c
float mono_key_inverse(uint32_t key) {
    uint32_t i = (key & 0x80000000u) ? (key & 0x7FFFFFFFu) : ~key;
    float f; memcpy(&f, &i, 4); return f;
}
```

`mono_key` pozitifleri `| 0x80000000` (en üst bit 1) yapmıştı, negatifleri `~i` (en üst bit 0). Yani dönüşümden sonra: anahtarın en üst biti 1 ise orijinal **pozitifti** (işaret bitini geri 0 yap: `& 0x7FFFFFFF`), en üst biti 0 ise **negatifti** (`~key` ile geri al). Round-trip: `mono_key_inverse(mono_key(f)) == f`. Dönüşüm bijektif olduğu için tersi var.

**3** – Sadece sihirli sayı tahmini (Newton'suz) ~%3-4 hata verir — kaba ama bir bölme/karekök hiç yapmadan. Newton adımı (`x * (1.5 - 0.5·x·y²)`), `f(y) = 1/y² - x`'in köküne bir adım yaklaşır; Newton-Raphson, iyi bir ilk tahminden başlayınca hatayı hızla düşürür. Bir adım %3-4'ü %0.17'ye indirir — çünkü ilk tahmin zaten köke yakın, Newton'ın karesel yakınsaması devreye girer.

**4** – İkinci Newton adımı hatayı ~%0.0005'e indirir. Newton-Raphson **karesel yakınsar**: her adım, doğru basamak sayısını kabaca ikiye katlar (hatayı kareler). İlk tahmin ~%4 (hata 0.04); bir adım → ~0.04² mertebesi ~%0.17; ikinci adım → ~0.0017² mertebesi ~%0.0005. Bu yüzden iki adım çoğu grafik uygulaması için fazlasıyla hassas; Quake III bir adımla yetinmişti (hız/hassasiyet dengesi).

**5** – `0x5f400000` (sadece üs kısmı, alt bitler sıfır) kullanmak ilk tahmini **kötüleştirir** (hata ~%6-7'ye çıkar), çünkü `0x...3759df`'nin alt bitleri, bit desenini `log₂`'ye bağlayan yaklaşımın sistematik hatasını (Ders 2'deki log eğrisinin düz çizgiyle yaklaşımı) telafi edecek şekilde ince ayarlanmış; onları atmak yaklaşımı kabalaştırır. Ama Newton adımı güçlü olduğu için, kötü bir ilk tahminden bile (%6-7) sonra ~%0.4 civarına iner — yani Newton çoğunu kurtarır, ama iyi bir sihirli sayıyla başlamak (tek adımda %0.17) daha az adımla daha iyi sonuç verir. Sihirli sayının zarafeti, Newton'ın işini kolaylaştırmasında.

</details>

---

## Kaynaklar

- "Fast inverse square root" ve `0x5f3759df`: Quake III Arena kaynak kodu (id Software); Chris Lomont, "Fast Inverse Square Root" (2003) — sabitin analizi.
- Henry Warren, *Hacker's Delight* (2. baskı), §17: float'ları tamsayı olarak karşılaştırma.
- C standardı (ISO/IEC 9899:2018), §6.5¶7 (strict aliasing); Ders 4.5 ve 4.27 (tip punning).
- Ders 3.12 (IEEE 754) ve Faz 6 (Newton-Raphson): bu dersin temelleri.

**Sıradaki ders:** CRC ve Hamming kodu. Polinom bölmesi olarak CRC-32 ve tek bit hatası düzelten Hamming kodu.
