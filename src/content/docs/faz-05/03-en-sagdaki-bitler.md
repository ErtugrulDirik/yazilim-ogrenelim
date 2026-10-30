---
title: "5.3 En sağdaki bitler"
description: "x-1'in en sağdaki 1'i ve ardındaki sıfırları nasıl değiştirdiğinden çıkan üç özdeşlik: x & (x-1) en sağdaki 1'i siler (ve ikinin kuvveti testi), x & -x en sağdaki 1'i izole eder, x | (x+1) en sağdaki 0'ı set eder. Her birinin iki tümleyen üzerinden ispatı, Kernighan'ın bit sayma yöntemi ve derleyicinin bazılarını tek komuta çevirmesi."
---

Bir sayının **en sağdaki** 1'i, **en sağdaki** 0'ı — bunları bulmak ve değiştirmek, bit hilelerinin çekirdeğinde. Üç küçük formül (`x & (x-1)`, `x & -x`, `x | (x+1)`) sürekli karşına çıkacak: bit saymada (Ders 5.8), sondaki sıfırları bulmada (Ders 5.9), ikinin kuvveti testinde (Ders 5.7). Bu derste üçünü de türetip ispatlıyoruz.

Hepsinin sırrı tek bir gözlemde: **`x - 1`, en sağdaki 1'i 0 yapar ve onun sağındaki bütün 0'ları 1 yapar.** Ondalıkta 1 çıkarırken ödünç almak (borrow) gibi: `...1000 - 1 = ...0111`. Bu fazda hep işaretsiz (`unsigned`) sayılarla çalışıyoruz (Ders 5.1).

---

## 1. x & (x-1): en sağdaki 1'i sil

```
x        = 10110000
x - 1    = 10101111      <- en sagdaki 1 (bit 4) 0 oldu, sagindaki 0'lar 1 oldu
x & (x-1)= 10100000      <- en sagdaki 1 silindi
```

**İspat.** `x`'in en sağdaki 1'i `k`. bitte olsun. O zaman `x` şöyle: `[üst bitler] 1 [k tane 0]`. `x - 1`, `k`. bitteki 1'i ödünç verir: `k`. bit 0 olur, sağındaki `k` tane 0, 1 olur, üst bitler değişmez: `[üst bitler] 0 [k tane 1]`. Şimdi `x & (x-1)`:

- **Üst bitler**: ikisinde de aynı, `&` onları korur.
- **`k`. bit**: `x`'te 1, `x-1`'de 0 → `&` sonucu 0. **En sağdaki 1 silindi.**
- **Alt `k` bit**: `x`'te hepsi 0, `x-1`'de hepsi 1 → `&` sonucu 0.

Sonuç: en sağdaki 1 kaldırılmış, gerisi aynı. ∎

### Hemen bir uygulama: ikinin kuvveti testi

Bir sayının 2'nin kuvveti olması demek, **tam olarak bir** bitinin 1 olması demek (`1, 10, 100, ...`). O tek 1'i silersek 0 kalır:

```c
int is_pow2(uint32_t x) {
    return x != 0 && (x & (x - 1)) == 0;
}
```

```
1 2 4 8 16   <- 0..16 arasindaki ikinin kuvvetleri
```

`x & (x-1) == 0`, "en sağdaki 1'i silince hiç bit kalmadı" = "zaten tek bir bit vardı". `x != 0` kontrolü şart: 0'ın hiç 1'i yok, `0 & (0-1)` da 0 olur ama 0 ikinin kuvveti değil. Ders 5.1'deki öncelik tuzağı yüzünden `(x & (x-1))` parantezli. Ders 5.7'de bu testi hizalama için kullanacağız.

### Kernighan'ın bit sayma yöntemi

`x & (x-1)` her seferinde bir 1'i siliyor; o halde kaç kez silebildiğimiz, kaç 1 olduğudur:

```c
int popcount(uint32_t x) {
    int count = 0;
    while (x != 0) {
        x &= x - 1;    // en sagdaki 1'i sil
        count++;
    }
    return count;
}
```

```
popcount(0b10110100) = 4
```

Döngü, bit sayısı kadar değil, **1 sayısı** kadar dönüyor: `0b10110100`'de 4 adım. Çok 0'lı sayılarda bu, her biti tek tek kontrol etmekten hızlı. Ders 5.8'de bundan da hızlı (dalsız, paralel) yöntemleri göreceğiz, ama Kernighan'ınki en zarifi.

---

## 2. x & -x: en sağdaki 1'i izole et

```
x      = 10110000
-x     = 01010000      <- iki tumleyen: ~x + 1
x & -x = 00010000      <- sadece en sagdaki 1 kaldi
```

Bu formül, en sağdaki 1'i **yalnız başına** çıkarıyor (gerisini sıfırlıyor). İşaretsiz `-x`, Ders 3.3'teki iki tümleyen: `-x = ~x + 1`, ve işaretsizde `-x` her zaman tanımlı (mod 2ⁿ).

**İspat.** Yine en sağdaki 1 `k`. bitte: `x = [A] 1 [k tane 0]`, burada `[A]` üst bitler. İki tümleyeni iki adımda:

- `~x` = `[~A] 0 [k tane 1]` (her bit ters).
- `-x = ~x + 1`: alttaki `k` tane 1'e 1 eklenince hepsi 0 olur ve `k`. bite taşınır (`0 → 1`): `-x = [~A] 1 [k tane 0]`.

Şimdi `x & -x`:

- **`k`. bit**: ikisinde de 1 → sonuç **1**.
- **Alt `k` bit**: ikisinde de 0 → sonuç 0.
- **Üst bitler (`A` ve `~A`)**: her konumda biri 1'se diğeri 0 (biri diğerinin tersi) → `&` sonucu her zaman 0.

Geriye yalnızca `k`. bitteki 1 kalır: en sağdaki 1 izole edildi. ∎

Bu değere "en düşük set bit" (lowest set bit) denir ve hem bir 2'nin kuvvetidir (tek bitli) hem de en sağdaki 1'in **değerini** verir (burada 16). Ders 5.9'da sondaki sıfırları saymak için, Faz 8'deki bazı veri yapılarında (Fenwick ağacı) doğrudan bu formül kullanılır.

---

## 3. x | (x+1): en sağdaki 0'ı set et

Simetrik olarak, `x + 1` en sağdaki 0'ı 1 yapıp ardındaki 1'leri 0 yapar (toplamada elde taşıma). `x | (x+1)` ise en sağdaki 0'ı 1'ler:

```
x        = 10110000
x + 1    = 10110001      <- en sagdaki 0 (bit 0) 1 oldu
x | (x+1)= 10110001      <- en sagdaki 0 set edildi
```

```
x        = 00101000
x + 1    = 00101001
x | (x+1)= 00101001
```

**İspat.** `x`'in en sağdaki 0'ı `k`. bitte olsun: `x = [B] 0 [k tane 1]`. `x + 1`, alttaki `k` tane 1'e 1 ekler, hepsi 0 olur ve `k`. bite taşınır: `x + 1 = [B] 1 [k tane 0]`. `x | (x+1)`:

- **`k`. bit**: `x`'te 0, `x+1`'de 1 → `|` sonucu **1**. En sağdaki 0 set edildi.
- **Alt `k` bit**: `x`'te 1, `x+1`'de 0 → `|` sonucu 1 (korundu).
- **Üst bitler**: aynı, `|` korur.

Sonuç: en sağdaki 0, 1 olmuş, gerisi aynı. ∎

Bu üç formül bir aile: `x - 1` ve `-x`, en sağdaki **1** ile; `x + 1`, en sağdaki **0** ile oynuyor. Bir kez `x ± 1`'in taşıma/ödünç yoluyla alt bitleri nasıl değiştirdiğini gördükten sonra, hepsi aynı mantıktan çıkıyor.

---

## 4. Derleyici bunları tanıyor mu?

Bu formüller o kadar temel ki, bazıları doğrudan bir işlemci komutuna karşılık geliyor ve derleyici onları tanıyor. `x & -x` (en düşük set bit), x86'da `blsi` komutu; `x & (x-1)` (en düşük set biti sıfırla) `blsr`. Kernighan'ın `popcount`'u ise, hedef işlemcide `popcnt` komutu varsa (Ders 5.8) derleyici tarafından **tek bir komuta** çevrilebilir — döngümüz, aslında donanımın bir seferde yaptığı işi tarif ediyor.

Bu, bu fazın tekrar eden temasını önceden gösteriyor: bir bit hilesini yazdıktan sonra, derleyicinin (godbolt ile) onu zaten bir komuta çevirip çevirmediğine bakmak. Çoğu zaman çeviriyor — biz hileyi neden işe yaradığını anlamak için, derleyici hızı için yazıyor.

---

## Alıştırmalar

**1** – `x = 0b11011100` için `x & (x-1)`, `x & -x`, `x | (x+1)`'i elle hesapla (önce `x-1`, `-x`, `x+1`'i bul). Sonuçları ikilik yaz.

**2** – `x & (x-1)`'i **iki kez** uygulamak ne yapar? `n` kez uygulamak? Bir sayının en sağdaki `k` tane 1'ini silen bir döngü yaz.

**3** – En sağdaki 1'i izole etmenin (`x & -x`) tersine, en sağdaki 1'i **0'a kadar bütün** bitlerle (kendisi dahil) veren `x ^ (x-1)` ifadesini `x = 0b10110000` için hesapla. Bu neden `0b00011111` verir? (İpucu: `x-1`'in alt bitleri.)

**4** – `is_pow2`'de `x != 0` kontrolünü kaldırırsan hangi `x` için yanlış "evet" döner? Neden 0 bu testi yanlışlıkla geçiyor? `x & -x == x` ifadesi ikinin kuvvetini test etmenin başka bir yolu mu — 0 için ne verir?

**5** – Kernighan `popcount`'unu, `0xFFFFFFFF` (32 bit 1) ve `0x80000000` (tek bit) için kaç adım döndüğünü sayarak çalıştır. Her biti tek tek kontrol eden naif sürüm (`for i in 0..32: count += (x>>i)&1`) bu ikisinde kaç adım döner? Kernighan ne zaman kazanır, ne zaman kaybeder?

<details>
<summary>Cevaplar</summary>

**1** – `x = 11011100`. `x - 1 = 11011011`, `x & (x-1) = 11011000` (en sağdaki 1, bit 2, silindi). `-x = ~x + 1 = 00100011 + 1 = 00100100`, `x & -x = 00000100` (en sağdaki 1, bit 2, izole). `x + 1 = 11011101`, `x | (x+1) = 11011101` (en sağdaki 0, bit 0, set edildi).

**2** – `x & (x-1)` iki kez: en sağdaki **iki** 1'i siler. `n` kez: en sağdaki `n` tane 1'i siler (sayıda `n`'den az 1 varsa 0'a iner).

```c
uint32_t clear_lowest_k(uint32_t x, int k) {
    for (int i = 0; i < k && x != 0; i++) {
        x &= x - 1;
    }
    return x;
}
```

`x != 0` kontrolü, 1'ler bitince durmak için (yoksa `x=0` iken `x & (x-1)` = `0 & 0xFFFFFFFF` = 0, zararsız ama gereksiz).

**3** – `x = 10110000`, `x - 1 = 10101111`, `x ^ (x-1) = 00011111`. En sağdaki 1 (`x`'te bit 4) ve onun sağındaki her şey 1 oluyor. Çünkü `x` ile `x-1`, en sağdaki 1'in **konumundan aşağısında** tamamen farklı (biri `1000...`, diğeri `0111...`), yukarısında ise aynı. XOR, farklı olan bitleri 1 yapar: tam olarak en sağdaki 1'den aşağısı. Bu, en sağdaki 1'in konumunu bulmanın (mask üretmenin) bir yolu; Ders 5.9'da işe yarayacak.

**4** – `x = 0` yanlışlıkla "evet" döner: `0 & (0-1)` = `0 & 0xFFFFFFFF` = 0, yani test geçer ama 0 ikinin kuvveti değil. 0'ın hiç 1 biti yok; "en sağdaki 1'i silince 0 kalır" mantığı 0'da boşuna doğru çıkıyor. `x & -x == x` da benzer: ikinin kuvvetinde en sağdaki 1 zaten tek bit olduğu için `x & -x == x`; ama `x = 0` için `0 & 0 = 0 == 0`, yine yanlış geçer. İki test de `x != 0` ile korunmalı. (Ayrıca `==`'nin önceliği `&`'den yüksek olduğu için `x & -x == x`, `x & (-x == x)` diye okunur — parantez şart: `(x & -x) == x`; Ders 5.1.)

**5** – `0xFFFFFFFF`: Kernighan **32 adım** (her adımda bir 1 siler, 32 tane var). `0x80000000`: Kernighan **1 adım** (tek 1). Naif sürüm her ikisinde de **32 adım** (hep bütün bitleri gezer). Kernighan, 1 sayısı azsa kazanır (`0x80000000`'da 32'ye karşı 1); 1 sayısı çoksa naifle eşitlenir (`0xFFFFFFFF`'te ikisi de 32). Yani Kernighan "1 sayısı kadar" çalışır, naif "bit sayısı kadar"; az 1'li sayılarda büyük fark, dolu sayılarda fark yok. Ders 5.8'deki paralel yöntem her ikisinde de sabit (az) adımda biter.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §2.1: `x & (x-1)`, `x & -x` ve türevleri.
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: en sağdaki bit işlemleri.
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), Alıştırma 2-9: `x & (x-1)` ile bit sayma.
- Sean Anderson, "Bit Twiddling Hacks": lowest set bit, power-of-two testi.

**Sıradaki ders:** Aritmetik–mantık özdeşlikleri. `x + y = (x ^ y) + 2(x & y)`, ortalamayı taşmadan almak ve De Morgan genellemeleri.
