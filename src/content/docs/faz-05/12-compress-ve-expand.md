---
title: "5.12 Compress ve expand"
description: "Bir maskeye göre bitleri toplamak ve dağıtmak: compress (pext) maskede 1 olan bitleri seçip sağa sıkıştırır, expand (pdep) bir sayının alt bitlerini maskedeki konumlara yayar; ikisinin birbirinin tersi olması, naif uygulamaları ve dağınık bit alanlarını toplamada kullanımı, x86'nın pext/pdep komutları ve ARM'da donanım karşılığının olmaması."
---

Ders 5.11'de bitleri yeniden **düzenledik** (ters çevirme, karıştırma). Bu derste bitleri bir **maskeye göre** topluyoruz ve dağıtıyoruz: iki işlem, **compress** (maskede seçili bitleri bir araya sıkıştır) ve **expand** (bir araya gelmiş bitleri maskedeki yerlere yay). Birbirinin tersi olan bu ikili, dağınık bit alanlarını toplamada, veri sıkıştırmada ve Ders 5.17'deki uzay doldurma eğrilerinde işe yarıyor. x86'da bunlar tek birer komut (`pext`/`pdep`); nasıl çalıştıklarını önce yazılımda görüyoruz.

İşaretsiz (`unsigned`) sayılarla.

---

## 1. Compress (pext): maskeli bitleri topla

**Compress**, `mask`'te 1 olan konumlardaki `x` bitlerini seçip, aralarındaki boşlukları atarak **sağa** dizer:

```c
uint32_t compress_naive(uint32_t x, uint32_t mask) {
    uint32_t r = 0;
    int out = 0;
    for (int i = 0; i < 32; i++) {
        if (mask & (1u << i)) {         // maskede bu bit secili mi?
            if (x & (1u << i)) {        // x'te bu bit 1 mi?
                r |= (1u << out);       // sonucun bir sonraki bosluguna koy
            }
            out++;
        }
    }
    return r;
}
```

```
x        = 10110100
mask     = 11001100
compress = 00001001    (maskeli bitler saga dizildi)
```

`mask = 11001100`, bit 2, 3, 6, 7'yi seçiyor. `x`'in bu konumlardaki bitleri (düşükten yükseğe): bit 2 = 1, bit 3 = 0, bit 6 = 0, bit 7 = 1. Bunları aralarındaki seçilmemiş bitleri atarak yan yana dizince: `1001` = sonucun alt 4 biti. Dağınık bitler bir araya toplandı.

Pratik kullanımı: bir sayıya dağılmış bir bit alanını (örneğin bir donanım register'ında araya başka bitler girmiş bir sayacı) tek bir bütün sayı olarak çıkarmak. Ya da bir filtreden geçen elemanları yan yana toplamak.

---

## 2. Expand (pdep): bitleri maskeye yay

**Expand**, compress'in tersi: bir sayının alt bitlerini alıp `mask`'te 1 olan konumlara **dağıtır**:

```c
uint32_t expand_naive(uint32_t x, uint32_t mask) {
    uint32_t r = 0;
    int in = 0;
    for (int i = 0; i < 32; i++) {
        if (mask & (1u << i)) {         // maskede bu bit secili mi?
            if (x & (1u << in)) {       // x'in siradaki alt biti 1 mi?
                r |= (1u << i);         // maskedeki bu konuma koy
            }
            in++;
        }
    }
    return r;
}
```

`x`'in alt bitlerini sırayla alıp maskenin 1 olduğu konumlara serpiştiriyor. Compress yan yana getiriyordu, expand araları açıyor.

### Birbirinin tersi

İkisi bir maskeye göre birbirini geri alıyor:

```c
expand(compress(x, mask), mask)  ==  x & mask
```

```
x & mask         = 10000100
expand(compress) = 10000100
```

`compress`, `x`'in maskeli bitlerini topladı; `expand` onları aynı maskeye geri yaydı; sonuç `x`'in maske bitleri (maskesiz bitler sıfır). Compress bilgi kaybeder mi? Sadece **maskesiz** bitleri atar; maskeli bitler korunur ve expand ile geri konur. Bu tersinirlik, ikisinin bir çift olmasının sebebi.

---

## 3. Donanım: pext ve pdep

Bu iki işlem o kadar kullanışlı ki x86 (BMI2 uzantısı) bunlar için tek birer komut sunuyor:

- **`pext`** (parallel bits extract) = compress.
- **`pdep`** (parallel bits deposit) = expand.

Intel/AMD işlemcilerde, naif döngümüzün 32 adımda yaptığını **tek komutta** yapıyorlar. GCC/Clang'de `<immintrin.h>` ile `_pext_u32` / `_pdep_u32` olarak erişilir (sadece x86'da).

**ARM'da (bu makine, Apple M2) bu komutlar yok.** ARM'ın `pext`/`pdep` karşılığı yok; orada ya naif döngü, ya da Ders 5.11'deki kelebek desenine benzer, `log₂ 32 = 5` adımlık daha hızlı bir yazılım uygulaması (Hacker's Delight'taki) kullanılır. Bu, bir bit işleminin **donanıma bağlı** olduğu nadir durumlardan biri: popcount (Ders 5.8) ve clz/ctz (Ders 5.9) çoğu mimaride komutken, pext/pdep uzun süre sadece x86'daydı (ve ilk AMD uygulamaları yavaştı). Taşınabilir kod yazarken yazılım sürümünü bulundurmak gerekir.

Yani bu derste yazdığımız naif sürümler, x86'da `pext`/`pdep`'e, ARM'da bir yazılım rutinine karşılık geliyor — aynı mantık, farklı maliyet.

---

## 4. Nerede kullanılır

- **Dağınık bit alanları**: bir protokol ya da donanım register'ında araya başka bitler girmiş bir alanı tek sayı olarak okumak (compress) ya da yazmak (expand).
- **Morton kodu / Z-order** (Ders 5.17): iki koordinatın bitlerini `0101...` ve `1010...` maskeleriyle expand edip OR'layarak tek bir sayıya "örmek"; perfect shuffle'ın (Ders 5.11) bir alternatifi.
- **Satranç bitboard'ları** (Ders 5.20): tahtadaki belirli karelere karşılık gelen bitleri toplamak.
- **Veri sıkıştırma ve filtreleme**: bir maskeye göre seçili elemanları yan yana toplamak (SIMD'de `compress` işlemleri bunun vektör hali).

Compress/expand, "bitler bir küme" (Ders 5.2) görüşünün doğal uzantısı: bir alt kümeyi (maske) seçip onun elemanlarını (bitleri) ayrı bir yere taşımak.

---

## Alıştırmalar

**1** – `compress_naive(0b11110000, 0b10101010)`'ı elle hesapla. Maske hangi bitleri seçiyor, `x`'in o bitleri ne, sonuç ne?

**2** – `expand(x, mask)`'te `mask`'te `k` tane 1 varsa, `x`'in kaç biti kullanılır? `x`'in `k`'dan fazla biti 1 ise (üst bitler) ne olur — kaybolur mu? `compress` için `mask`'teki 1 sayısı sonucun kaç bitini belirler?

**3** – `compress(x, mask)` ile `(x & mask)` farkı ne? İkisi de maskesiz bitleri atar; `compress` ek olarak ne yapar? `x & mask`'in sonucunda bitler nerede, `compress`'te nerede?

**4** – Bir `uint32_t`'de tek konumlardaki (bit 1, 3, 5, …) bitleri toplayan bir ifade yaz: `compress(x, 0xAAAAAAAA)`. Sonuç 16 bitlik mi? Bu, Ders 5.11'deki unshuffle'ın yarısı mı? (İpucu: shuffle iki yarıyı geçiriyordu; compress onları ayırıyor.)

**5** – `pext`/`pdep`'in x86'da olup ARM'da olmaması, "taşınabilir bit kodu" yazarken ne demek? Bir fonksiyonu hem x86 (`_pext_u32`) hem ARM (naif/butterfly) için nasıl yazarsın — `#ifdef` ile mi, yoksa derleyicinin seçmesine mi bırakırsın? (popcount'u karşılaştır, Ders 5.8.)

<details>
<summary>Cevaplar</summary>

**1** – `x = 0b11110000`, `mask = 0b10101010` (bit 1, 3, 5, 7 seçili). `x`'in o bitleri (düşükten): bit 1 = 0, bit 3 = 0, bit 5 = 1, bit 7 = 1. Yan yana (düşük maske biti sonucun en düşük bitine): `1100` = `0b00001100`. Maske 4 bit seçtiği için sonuç 4 bitlik, değeri `0b1100` = 12.

**2** – `expand`'te `mask`'te `k` tane 1 varsa, `x`'in alt `k` biti kullanılır (her maske biti için bir tane). `x`'in `k`'dan fazla biti 1 ise (üst bitler), o üst bitler **kullanılmaz** — expand sadece alt `k` biti okur, gerisi yok sayılır (kaybolur). `compress` için: `mask`'teki 1 sayısı `k`, sonucun **alt `k` biti**ni belirler; `compress` en fazla `k` bit üretir, üst `32 - k` bit 0.

**3** – `x & mask`, maskesiz bitleri sıfırlar ama maskeli bitleri **yerinde** bırakır (aralarında boşluklar kalır). `compress(x, mask)` ek olarak o maskeli bitleri **sağa sıkıştırır** (boşlukları atıp yan yana dizer). Yani `x & mask`'te bitler orijinal konumlarında, dağınık; `compress`'te hepsi en sağda, bitişik. `expand(compress(x,m), m) == x & m` ilişkisi tam bunu söylüyor: sıkıştır, sonra geri yay → `x & mask`.

**4** – `compress(x, 0xAAAAAAAA)` tek konumlardaki 16 biti toplar; sonuç **16 bitlik** (maskede 16 tane 1 var). Bu, unshuffle'ın yarısı: `shuffle` (Ders 5.11) iki 16-bitlik yarıyı `aAbBcC...` diye geçiriyordu; unshuffle onları ayırır. `compress(x, 0xAAAAAAAA)` tek konumları (bir yarı), `compress(x, 0x55555555)` çift konumları (diğer yarı) toplar — ikisi birlikte unshuffle. Yani compress, perfect shuffle'ı tersine çevirmenin bir yolu.

**5** – "Taşınabilir bit kodu", bir işlemin her hedefte **çalışması** ama hızının donanıma bağlı olabileceği demek. `pext`/`pdep` için iki yol: (a) `#ifdef __BMI2__` ile x86'da `_pext_u32`, başka yerde yazılım sürümü — açık ama elle bakım gerektirir; (b) her zaman yazılım sürümünü yaz ve derleyicinin tanımasını um — ama popcount'un aksine (Ders 5.8, derleyici SWAR'ı `popcnt`'e çevirebiliyor), derleyiciler compress/expand deyimlerini genellikle `pext`/`pdep`'e **çeviremez** (desen çok karmaşık). Bu yüzden pext/pdep, `#ifdef` ya da bir soyutlama katmanı gerektiren, "derleyici otomatik yapar"a güvenemediğin nadir durumlardan. popcount taşınabilir (builtin her yerde iyi), pext/pdep değil.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §7.4: compress (pext), §7.5: expand, kelebek tabanlı hızlı uygulamalar.
- Intel 64 and IA-32 Architectures Software Developer's Manual: `PEXT`, `PDEP` (BMI2).
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: bit compress/expand.
- Ders 5.11 (bitleri yeniden düzenleme) ve Ders 5.17 (uzay doldurma eğrileri): ilgili kullanımlar.

**Sıradaki ders:** Çarpma ve bölme algoritmaları. Kaydır-topla çarpma, kaydır-çıkar bölme, yüksek yarı ve çok kelimeli aritmetik.
