---
title: "5.11 Bitleri yeniden düzenleme"
description: "Bitlerin yerini değiştirmek: bir sayının bitlerini ters çevirmek (bit reverse) naif döngüyle ve kelebek (butterfly) deseniyle paralel olarak — komşu bitleri, sonra 2'li, 4'lü, 8'li, 16'lı grupları değiştirmek; perfect shuffle; ve 8 byte'ı 8×8 bit matrisi görüp transpozunu almak. Hepsinin ortak 'böl ve yer değiştir' deseni."
---

Ders 5.8 ve 5.9'da bitleri **saydık** ve yerlerini bulduk; bu derste bitleri **yeniden düzenliyoruz**: ters çevirmek, karıştırmak, bir matris gibi devirmek. Bu işlemler sinyal işlemede (FFT'nin bit-reversal adımı), kriptografide, grafik ve veri sıkıştırmada karşına çıkar. Hepsinin altında aynı güzel desen var: **böl ve yer değiştir** (kelebek/butterfly) — Ders 5.8'deki SWAR'ın akrabası.

İşaretsiz (`unsigned`) sayılarla.

---

## 1. Bit reverse: naif

Bir sayının bitlerini tersine çevirmek: en düşük bit en yükseğe, en yüksek en düşüğe.

```c
uint32_t reverse_naive(uint32_t x) {
    uint32_t r = 0;
    for (int i = 0; i < 32; i++) {
        r = (r << 1) | (x & 1);   // x'in en dusuk bitini r'nin en dusugune al
        x >>= 1;
    }
    return r;
}
```

```
reverse(1) = 0x80000000      (en dusuk bit en yuksege)
reverse(0x12345678) = 0x1e6a2c48
reverse(0xAAAAAAAA) = 0x55555555
```

Her adımda `x`'ten bir bit alıp `r`'ye ters sırada diziyoruz. 32 adım, doğru ama yavaş.

---

## 2. Bit reverse: kelebek deseni

Ters çevirmeyi **paralel** yapabiliriz. Fikir: önce komşu **bit çiftlerini** değiştir, sonra komşu **2'li grupları**, sonra 4'lü, 8'li, 16'lı. Her adım grup boyutunu iki katına çıkarıyor; 5 adımda (`log₂ 32`) bütün bitler tersine döner.

```c
uint32_t reverse_parallel(uint32_t x) {
    x = ((x & 0x55555555) << 1)  | ((x >> 1) & 0x55555555);   // komsu bitler
    x = ((x & 0x33333333) << 2)  | ((x >> 2) & 0x33333333);   // 2'li gruplar
    x = ((x & 0x0F0F0F0F) << 4)  | ((x >> 4) & 0x0F0F0F0F);   // 4'lu (nibble)
    x = ((x & 0x00FF00FF) << 8)  | ((x >> 8) & 0x00FF00FF);   // byte'lar
    x = (x << 16) | (x >> 16);                                 // yarilar
    return x;
}
```

Her satır bir "kelebek" adımı. İlkine bakalım (`0x55555555` = `0101...`, her çiftin alt biti; Ders 5.8):

- `(x & 0x55555555) << 1`: her çiftin **alt** bitini al, bir sola taşı (üst konuma).
- `(x >> 1) & 0x55555555`: her çiftin **üst** bitini al, bir sağa taşı (alt konuma).
- `|`: ikisini birleştir → her çiftin iki biti yer değiştirdi.

Sonraki satırlar aynı şeyi gittikçe büyüyen gruplara uyguluyor: 2'li grupları (`0x33`), 4'lü nibble'ları (`0x0F`), byte'ları (`0x00FF`), son olarak iki 16-bitlik yarıyı. Her adım yerel takaslar yapıyor; beşi birlikte bitleri tam tersine çeviriyor:

```
0x12345678 -> naive 0x1e6a2c48  parallel 0x1e6a2c48  OK
```

Naif ve paralel aynı sonucu veriyor. Paralel sürüm 5 işlem (döngüsüz, dalsız). Bazı işlemcilerde tek komut (`rbit`, ARM); C'de operatör yok ama kelebek deseni derleyicinin onu tanımasına izin verir.

Bu "böl ve yer değiştir" deseni Ders 5.8'deki popcount SWAR'ıyla aynı aile: ikisi de 32 biti `log₂ 32 = 5` adımda, grup boyutunu iki katlayarak işliyor. Endian byte-swap (Ders 3.9'daki `__builtin_bswap32`) da bunun son üç satırı (byte düzeyinde takas, bit düzeyinde değil).

---

## 3. Perfect shuffle

**Perfect shuffle** (mükemmel karma), bir deste kâğıdı tam ortadan ikiye bölüp bir birinden bir diğerinden alarak harmanlamak gibi: üst yarının bitleriyle alt yarının bitlerini birbirine **geçirmek**. 16 bitlik `abcd...` ve `ABCD...` iki yarısı `aAbBcC...` olur. Kelebek deseninin bir çeşidi:

```c
uint32_t shuffle(uint32_t x) {
    uint32_t t;
    t = (x ^ (x >> 8)) & 0x0000FF00; x = x ^ t ^ (t << 8);
    t = (x ^ (x >> 4)) & 0x00F000F0; x = x ^ t ^ (t << 4);
    t = (x ^ (x >> 2)) & 0x0C0C0C0C; x = x ^ t ^ (t << 2);
    t = (x ^ (x >> 1)) & 0x22222222; x = x ^ t ^ (t << 1);
    return x;
}
```

Perfect shuffle ve tersi (unshuffle), Morton kodu (Ders 5.17'deki uzay doldurma eğrileri) ve bazı FFT uygulamalarında, iki boyutlu bir koordinatın bitlerini tek bir sayıya "örmek" için kullanılır. Ayrıntısı Ders 5.17'de; burada sadece "bitleri geçirme" fikrini tanıyoruz.

---

## 4. 8×8 bit matrisi transpozu

En görsel örnek. 8 byte'ı, her byte bir **satır** olan bir 8×8 bit matrisi olarak düşün. Transpoz: satırlarla sütunları değiştir (Ders 4.3'teki matris transpozu, ama elemanlar tek bit). Naif hali her biti tek tek taşıyor:

```c
void transpose8(const uint8_t in[8], uint8_t out[8]) {
    for (int i = 0; i < 8; i++) out[i] = 0;
    for (int r = 0; r < 8; r++)
        for (int c = 0; c < 8; c++)
            if (in[r] & (1u << c))
                out[c] |= (1u << r);     // (r,c) biti (c,r)'ye
}
```

Alt üçgen bir matris verelim; transpoz onu üst üçgene çevirmeli:

```
girdi:            transpoz:
#.......          ########
##......          .#######
###.....          ..######
####....          ...#####
#####...          ....####
######..          .....###
#######.          ......##
########          .......#
```

`(r, c)` konumundaki bit `(c, r)`'ye gitti: satırlarla sütunlar yer değiştirdi. Naif sürüm 64 bit kontrolü yapıyor; Warren'ın *Hacker's Delight*'taki hızlı sürümü, Bölüm 2'deki kelebek desenini 64 bite uygulayıp bütün transpozu birkaç kaydırma-maske adımında yapıyor (4. alıştırma).

Bit matris transpozu, bir görüntüyü 90° döndürmede, bir bit matrisini satır-öncelikli ile sütun-öncelikli arasında çevirmede (Ders 4.3'teki döngü sırası sorunuyla bağlantılı), ve bazı veritabanı/sıkıştırma algoritmalarında kullanılır. "Byte'ları matris gör, bitlerle oyna" fikri, bitlerin tek sayılar değil, **düzenlenebilir bir ızgara** olduğunu gösteriyor.

---

## Alıştırmalar

**1** – `reverse_parallel`'ın ilk satırını (`((x & 0x55555555) << 1) | ((x >> 1) & 0x55555555)`) `x = 0b1101` için izle. Komşu çiftler nasıl yer değiştiriyor? Sonuç `0b1110` mu?

**2** – Bir byte'ın (8 bit) bitlerini ters çeviren `reverse8(uint8_t x)` yaz: kelebek deseninin kaç satırı yeter (`log₂ 8`)? Hangi maskeler (`0x55`, `0x33`, `0x0F` gibi ama 8 bitlik)?

**3** – `reverse_parallel`'ın son satırı `(x << 16) | (x >> 16)` — bu neden Ders 5.6'daki `rotl(x, 16)` ile aynı sonucu veriyor (bu özel durumda)? Genel bir `reverse` için neden döndürme değil, iki yarıyı **takas** gerekiyor?

**4** – 8×8 transpozun `(r,c) → (c,r)` eşlemesini kullanarak, bir karakterin (8×8 piksel font) 90° döndürülmüş halini üreten bir fikir yaz. Transpoz + satır ters çevirme (Bölüm 1) 90° döndürmeyi nasıl verir? (Ders 4.3'teki matris döndürme.)

**5** – Bit reverse tersinir mi — `reverse(reverse(x)) == x`? Perfect shuffle için tersi (unshuffle) var mı? Bir işlemin "bitleri yeniden düzenlemesi" ile "bilgi kaybetmesi" arasındaki fark ne (ipucu: reverse vs Ders 5.8'deki popcount)?

<details>
<summary>Cevaplar</summary>

**1** – `x = 0b1101` (4 bit, çiftler: `11` ve `01`). `(x & 0x5) << 1`: `0b0101 & 0b1101 = 0b0101`, `<< 1 = 0b1010` (alt bitler üste). `(x >> 1) & 0x5`: `0b0110 & 0b0101 = 0b0100` (üst bitler alta). `|`: `0b1010 | 0b0100 = 0b1110`. Evet, `0b1110`. Her çift içinde iki bit yer değiştirdi: `11`→`11` (simetrik, değişmedi), `01`→`10`. Sonuç çift-içi takaslar; tam reverse için sonraki satırlar grupları da takaslar.

**2** –

```c
uint8_t reverse8(uint8_t x) {
    x = ((x & 0x55) << 1) | ((x >> 1) & 0x55);   // komsu bitler
    x = ((x & 0x33) << 2) | ((x >> 2) & 0x33);   // 2'li gruplar
    x = ((x & 0x0F) << 4) | ((x >> 4) & 0x0F);   // 4'lu yarilar
    return x;
}
```

8 bit için `log₂ 8 = 3` satır yeter. Maskeler 8-bitlik halleri: `0x55` (`01010101`), `0x33` (`00110011`), `0x0F` (`00001111`). Her satır grup boyutunu iki katlar: 1→2→4; üç adımda byte tamamen tersine döner.

**3** – `(x << 16) | (x >> 16)`, bir `uint32_t`'nin iki 16-bitlik yarısını takas eder; `rotl(x, 16)` da (Ders 5.6) tam olarak bunu yapar — 16 döndürmek, 32-bitlik bir sayıda iki yarıyı değiştirmekle **aynı** (dışarı taşan üst 16 bit alttan geri gelir, net etki takas). Bu özel durumda eşitler. Ama genel reverse'in diğer satırları döndürme **değil**: onlar yarıları değil, grupları (çiftleri, nibble'ları) çaprazlamalı takas ediyor — `& maske` ile seçip farklı yönlere kaydırıp birleştiriyor; basit bir döndürme bunu yapamaz. Sadece en büyük grup (yarılar) için takas = döndürme.

**4** – 90° saat yönünde döndürme = transpoz + her satırı ters çevirme (ya da sütunları ters, yöne göre). Transpoz `(r,c)→(c,r)` yapar (satır/sütun değişir, bir köşegen yansıma); sonra her satırı yatay ters çevirmek (reverse8) bu yansımayı gerçek bir rotasyona dönüştürür. 8×8 bir font karakteri için: byte'ları transpoze et, sonra her byte'ı `reverse8` ile ters çevir → karakter 90° dönmüş olur. Bu, Ders 4.3'teki matris döndürmenin bit düzeyindeki hali; bitmap fontları döndürmede kullanılır.

**5** – Bit reverse **tersinir**: `reverse(reverse(x)) == x` — bitleri iki kez ters çevirmek başa döndürür, hiç bilgi kaybolmaz (her bit sadece yer değiştirir). Perfect shuffle de tersinir; tersi "unshuffle" (iç içe geçmiş bitleri ayırma), var ve benzer kelebek adımlarıyla yazılır. Fark: reverse, shuffle, transpoz **permütasyonlar** — bitleri yeniden düzenler ama hiçbirini yok etmez, bu yüzden tersi vardır (bijektif). Popcount (Ders 5.8) ise bilgi **kaybeder**: 32 bitten tek bir sayı (0-32) üretir, farklı girdiler aynı çıktıyı verebilir (`0b11` ve `0b101` ikisi de 2), bu yüzden tersi yoktur. "Yeniden düzenleme" tersinir, "özetleme/sayma" değil.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §7.1 (bit reverse), §7.3 (8×8 bit matris transpozu), §7.2 (shuffle).
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: bit permütasyonları.
- Jörg Arndt, *Matters Computational*, Bölüm 1: bit düzeyinde permütasyonlar, perfect shuffle.
- ARM `rbit` komutu: donanımda bit reverse.

**Sıradaki ders:** Compress ve expand. Maskeye göre bitleri toplamak ve x86 `pext`/`pdep` komutları.
