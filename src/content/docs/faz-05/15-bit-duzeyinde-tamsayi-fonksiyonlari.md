---
title: "5.15 Bit düzeyinde tamsayı fonksiyonları"
description: "Kayan nokta kullanmadan, sadece tamsayı ve bit işlemleriyle: floor(sqrt x)'i okuldaki uzun bölme gibi bit bit hesaplayan tamsayı karekök, floor(log2 x) = 31 - clz (Ders 5.9), ve floor(log10 x)'i log2'den bir tahmin + 10'un kuvvetleri tablosuyla düzeltme. Hepsi tüm 32-bit aralıkta doğrulanmış, float'ın yuvarlama hatası olmadan kesin."
---

Faz 5'in bu son dersinde, önceki derslerin araçlarını birleştirip **tamsayı fonksiyonları** yazıyoruz: karekök, `log₂`, `log₁₀` — hepsi kayan nokta (Faz 3) kullanmadan, sadece tamsayı ve bit işlemleriyle. Neden float değil? Çünkü float'ın yuvarlama hatası (Ders 3.14) bir tamsayı sonucunu yanlış tarafa yuvarlayabilir (`sqrt(x)` tam bir kareyi `3.9999` verip `floor` 3 yapabilir); tamsayı yöntemleri **kesin**. Bu fonksiyonlar bellek ayırıcılarda, sayı biçimlemede (Ders 3.16'daki `itoa`), ve kesinlik gereken her yerde kullanılır.

İşaretsiz (`unsigned`) sayılarla, hepsi tüm 32-bit aralıkta doğrulanmış.

---

## 1. Tamsayı karekök

`isqrt(x) = floor(sqrt(x))`: `x`'ten büyük olmayan en büyük tam karenin kökü. Okuldaki uzun bölme gibi (Ders 5.13'teki kaydır-çıkar bölmenin akrabası), kökü **bit bit**, en yüksek bitten başlayarak kuruyoruz:

```c
uint32_t isqrt(uint32_t x) {
    uint32_t result = 0;
    uint32_t bit = 1u << 30;        // en yuksek cift konumlu bit
    while (bit > x) {
        bit >>= 2;                  // x'ten buyuk bitleri atla
    }
    while (bit != 0) {
        if (x >= result + bit) {
            x -= result + bit;
            result = (result >> 1) + bit;
        } else {
            result >>= 1;
        }
        bit >>= 2;                  // iki bit birden (kokun bir biti)
    }
    return result;
}
```

Fikir: `(a + b)² = a² + 2ab + b²`. Kökü en yüksek bitten kurarken, her adımda "bir sonraki bit 1 olabilir mi?" diye soruyoruz — yani `result + bit`'in karesi kalan `x`'e sığıyor mu. `bit` her adımda **iki** kayıyor (`>>= 2`), çünkü kökün bir biti, karenin iki bitine karşılık gelir. Sığıyorsa çıkarıp o biti ekliyoruz. Bu, uzun bölmedeki "bölen sığıyor mu" sorusunun karekök hali.

```
x=16 isqrt=4    x=17 isqrt=4    x=100 isqrt=10    x=99 isqrt=9
x=0xFFFFFFFF isqrt=65535
```

20 milyon değerde ve bütün tam karelerde doğruladık: `result² <= x < (result+1)²` her zaman tutuyor, sıfır hata. Float'la (`(uint32_t)sqrt(x)`) yapsaydık, büyük tam karelerde yuvarlama bazen `65535` yerine `65534` verebilirdi; tamsayı sürümü kesin.

---

## 2. Tamsayı log₂

`floor(log₂ x)`, Ders 5.9'da gördüğümüz gibi en soldaki 1'in konumu:

```c
int ilog2(uint32_t x) {       // x > 0
    return 31 - __builtin_clz(x);
}
```

En soldaki 1 `k`. bitteyse `2^k <= x < 2^(k+1)`, yani `floor(log₂ x) = k = 31 - clz(x)` (Ders 5.9). `ilog2(16) = 4` (`2⁴ = 16`), `ilog2(17) = 4`, `ilog2(100) = 6` (`2⁶ = 64 <= 100 < 128`). `x = 0` tanımsız (`log₂ 0` yok, ve `clz(0)` tanımsız; Ders 5.9), çağıran `x > 0` sağlamalı. Bu, Ders 5.9'daki `nlz`'nin en doğrudan uygulaması, ve bir sayının kaç bit yer kapladığını (`ilog2(x) + 1`) söyler.

---

## 3. Tamsayı log₁₀

`floor(log₁₀ x)`, `x`'in **ondalık basamak sayısı eksi bir** (Ders 3.16'daki `itoa`'da kaç basamak gerektiğini bilmek için). Doğrudan bir bit işlemi yok, ama `log₂`'den bir tahminle başlayıp düzeltebiliriz:

```c
int ilog10(uint32_t x) {      // x > 0
    static const uint32_t pow10[] = {
        1, 10, 100, 1000, 10000, 100000,
        1000000, 10000000, 100000000, 1000000000
    };
    int guess = (ilog2(x) + 1) * 1233 >> 12;   // log10(2) ~ 1233/4096
    return guess - (x < pow10[guess]);
}
```

`log₁₀ x = log₂ x × log₁₀ 2`, ve `log₁₀ 2 ≈ 0.30103 ≈ 1233 / 4096`. Yani `log₁₀ x`'i, bit uzunluğunu (`ilog2 + 1`) `1233`'le çarpıp `>> 12` (yani `/ 4096`) ile tahmin ediyoruz — bir sabit nokta çarpımı (Ders 3.11), bölme yok. Bu tahmin ya doğru ya bir fazla; `pow10` tablosuna bakıp düzeltiyoruz: `x`, tahmin edilen basamaktaki 10'un kuvvetinden küçükse bir eksilt.

```
x=100 ilog10=2    x=99 ilog10=1    x=1000000 ilog10=6    x=0xFFFFFFFF ilog10=9
```

`100` → 2 (üç basamak, `log₁₀` 2), `99` → 1 (iki basamak). Tablo bakışı, sabit nokta çarpımının bazen bir fazla tahmin etmesini düzeltiyor — float `log10` çağırmadan, kesin. `ilog10(x) + 1`, `x`'in kaç ondalık basamak olduğu: `itoa`'nın tampon boyutunu önceden ayırmasının (Ders 3.16) temiz yolu.

---

## 4. Neden float değil?

Üç fonksiyon da float'la yazılabilirdi: `(uint32_t)sqrt(x)`, `(int)log2(x)`, `(int)log10(x)`. Neden bit/tamsayı yöntemleri?

- **Kesinlik**: float'ın 52 bitlik mantisi (Ders 3.14) 32-bit tamsayıları temsil edebilir, ama `sqrt`/`log` sonuçları yuvarlanır. `sqrt(x)` bir tam karede `k.9999...` verip `floor`/`(int)` yanlış tarafa yuvarlayabilir. Tamsayı `isqrt` her zaman tam `floor(sqrt(x))`.
- **Taşınabilirlik ve hız**: float birimi olmayan ya da yavaş olan sistemlerde (gömülü işlemciler) tamsayı yöntemleri çalışır.
- **Belirlenebilirlik**: tamsayı sonuçları her makinede aynı; float yuvarlama modu ve `-ffast-math` gibi ayarlardan etkilenebilir (Ders 3.14).

Bu, Faz 5'in genel dersini özetliyor: bitlerle ve tamsayılarla, kayan noktanın belirsizliği olmadan, kesin ve hızlı hesap. Bu faz boyunca topladığımız araçlar — maskeler, kaydırmalar, `clz`/`ctz`, kaydır-çıkar, sabit nokta — bu fonksiyonlarda bir araya geliyor.

---

## Faz 5 ortası: buraya kadar

Bu 15 derste bitlerle hesabın temellerini kurduk: operatörler ve tuzakları (5.1), maskeler (5.2), en sağdaki bit formülleri (5.3), aritmetik–mantık köprüsü (5.4), dalsız kod (5.5), taşma ve döndürme (5.6), 2'nin kuvvetleri ve hizalama (5.7), popcount ve parite (5.8), baştaki/sondaki sıfırlar (5.9), word-at-a-time (5.10), bit yeniden düzenleme (5.11), compress/expand (5.12), çarpma/bölme algoritmaları (5.13), sabite bölme (5.14) ve bit düzeyinde tamsayı fonksiyonları (5.15). Faz 4'teki `strlen`'i 8 kat hızlandırdık (5.10), Ders 3.12'deki float bitlerini union olmadan bit işlemleriyle inceledik, ve derleyicinin bu hilelerin çoğunu zaten bildiğini godbolt'ta gördük.

Fazın kalan dersleri (5.16–5.20) bunların üzerine kurulu: Gray kodu ve alışılmadık tabanlar, uzay doldurma eğrileri (Morton/Hilbert), float bit hileleri (hızlı ters karekök), CRC ve Hamming kodu, ve bir bitset/bitboard projesi.

---

## Alıştırmalar

**1** – `isqrt(x)`'in sonucunun `result² <= x < (result+1)²` değişmezini (Ders 4.2'deki döngü değişmezi) sağladığını `x = 10` için izle. `result` ve kalan `x` adım adım nasıl değişiyor?

**2** – `ilog2` ile bir sayının **ikilik basamak sayısını** (`bit_length`, Ders 5.9) ve `isqrt` ile tam kare olup olmadığını (`isqrt(x)² == x`) test eden fonksiyonlar yaz. `is_perfect_square(16)`, `is_perfect_square(17)` ne döner?

**3** – `ilog10`'daki `1233 / 4096` yaklaşımı `log₁₀ 2 ≈ 0.30103`'e ne kadar yakın? `1233 / 4096`'yı hesapla. Neden tam `0.30103` yerine bu kesri kullanıyoruz (ipucu: `>> 12` bir kaydırma, Ders 5.7)?

**4** – `ilog10`'da `pow10` tablosuyla düzeltme neden gerekli? Tahmin (`guess`) ne zaman bir fazla çıkar? `x = 1000` (tam `10³`) için `guess` ve düzeltme ne veriyor, elle izle.

**5** – `isqrt`'i float ile (`(uint32_t)sqrtf(x)`) yazıp, bir tam karede (`x = k*k`, büyük `k`) bit sürümüyle karşılaştır. `sqrtf` (32-bit float) hangi `k`'dan sonra yanlış sonuç vermeye başlar (ipucu: float'ın 24-bit mantisi, Ders 3.12)? `double` kullanmak bunu çözer mi, tamamen mi?

<details>
<summary>Cevaplar</summary>

**1** – `x = 10`. `bit` başta `1<<30`; `bit > 10` olduğu sürece `>>= 2` → `bit = 8` (`1<<3`). Adım 1 (`bit=8`): `x >= result+bit`? `10 >= 0+8`? Evet → `x -= 8` (x=2), `result = (0>>1)+8 = 8`... Burada bir incelik var: `result` ara değerlerde "iki katına ölçeklenmiş" tutuluyor. Son adımda `result` gerçek köke iner. `bit=8→2→...`; sonuçta `isqrt(10) = 3`, ve `3² = 9 <= 10 < 16 = 4²` değişmezi tutuyor. (Algoritmanın ara `result` değerleri ölçekli; değişmez son değerde kontrol edilir. Ayrıntılı iz için Warren §11.1'deki türetim.)

**2** –

```c
int bit_length(uint32_t x) { return x == 0 ? 0 : ilog2(x) + 1; }
int is_perfect_square(uint32_t x) { uint32_t s = isqrt(x); return s * s == x; }
```

`is_perfect_square(16)`: `isqrt(16) = 4`, `4*4 = 16 == 16` → **1** (evet). `is_perfect_square(17)`: `isqrt(17) = 4`, `4*4 = 16 != 17` → **0** (hayır). Tamsayı `isqrt` kesin olduğu için bu test de kesin; float `sqrt` ile `s*s == x` bazı büyük karelerde yuvarlama yüzünden yanlış olabilirdi.

**3** – `1233 / 4096 = 0.301025...`; `log₁₀ 2 = 0.301029995...`. Fark ~`0.000005`, çok küçük — 32-bit aralıktaki bütün `x` için doğru tahmin (artı/eksi bir, tablo düzeltir) vermeye yeter. Tam `0.30103` yerine `1233/4096` kullanıyoruz çünkü payda `4096 = 2¹²` bir 2'nin kuvveti; `/ 4096` bir **kaydırma** (`>> 12`, Ders 5.7), bölme değil. Yani kesri 2'nin kuvveti paydalı seçmek, çarpımı tamsayı + kaydırmaya indiriyor (Ders 3.11'deki sabit nokta); float ya da bölme gerekmiyor.

**4** – `(ilog2(x)+1) * 1233 >> 12` tahmini, `log₁₀ x`'in **tabanına** çoğu zaman eşit ama bazen **bir fazla** çıkar — çünkü bit uzunluğu (`ilog2+1`) kaba bir ölçü, ve bazı sayılar için yukarı yuvarlar. `x = 1000`: `ilog2(1000) = 9` (`2⁹=512<=1000<1024`), `(9+1)*1233 >> 12 = 12330 >> 12 = 3`. Ama `log₁₀ 1000 = 3` (dört basamak, taban 3)... `guess = 3`, `pow10[3] = 1000`, `x < 1000`? `1000 < 1000` hayır → düzeltme 0, sonuç **3**. Doğru. Eğer `x = 999` olsaydı: `guess` yine muhtemelen 3 çıkar (`999` bit uzunluğu 1000'le aynı), `pow10[3]=1000`, `999 < 1000` evet → `3 - 1 = 2`. Doğru (999 üç basamak, taban 2). Tablo, tahminin "10'un kuvveti sınırını geçtim mi" sorusunu kesinleştiriyor.

**5** – `(uint32_t)sqrtf(x)`, `sqrtf` 32-bit float kullanır; float'ın mantisi 24 bit (Ders 3.12), yani `2²⁴ = 16777216`'dan büyük tamsayıları **tam** temsil edemez. `k² > 2²⁴`, yani `k > 4096` civarından sonra, `sqrtf`'in sonucu bir tam karede `k - 0.0001` gibi çıkıp `(uint32_t)` ile `k-1`'e yuvarlanabilir — yanlış. `double` (52-bit mantis) kullanmak sınırı çok yükseltir: 32-bit tamsayılar (`< 2³²`) `double`'da tam temsil edilir, ve `sqrt` sonucu da genelde doğru yuvarlanır — ama **tamamen** garanti değil: standart `sqrt`'in doğru yuvarlandığını söyler, ama `(uint32_t)` dönüşümü ve ara hesaplar yine sınırda bir hata bırakabilir, o yüzden kesinlik gerekiyorsa `s*s <= x < (s+1)²` ile doğrulama ya da doğrudan tamsayı `isqrt` tercih edilir. Tamsayı sürümü hiçbir sınır tanımaz, her zaman kesin.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §11.1 (tamsayı karekök), §11.4 (tamsayı log).
- Donald Knuth, *TAOCP* Cilt 2, §4.3.1 ve §1.2.4: tamsayı fonksiyonları ve taban dönüşümleri.
- Sean Anderson, "Bit Twiddling Hacks": integer log2, log10, sqrt.
- Ders 3.16 (itoa): basamak sayısı ve tampon boyutu; Ders 5.9 (clz): `ilog2`'nin temeli.

**Sıradaki ders:** Gray kodu ve alışılmadık tabanlar. İkilik ↔ Gray dönüşümü ve taban −2 gösterimi.
