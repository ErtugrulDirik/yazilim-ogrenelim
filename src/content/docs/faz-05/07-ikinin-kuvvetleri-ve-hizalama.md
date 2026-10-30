---
title: "5.7 2'nin kuvvetleri ve hizalama"
description: "2'nin kuvvetleriyle bit işlemleri: x & (x-1) == 0 ile kuvvet testi, bit yayma (x |= x>>1; …) ile bir sonraki kuvvete yuvarlama, işaretsiz 2'nin kuvvetiyle bölme ve mod'un kaydırma ve maskeye dönüşmesi (x/8 → x>>3, x%8 → x&7), ve Ders 4.26/4.28'deki hizalama formüllerinin (align_up, align_down, is_aligned) neden tam bu bit işlemleri olduğu."
---

2'nin kuvvetleri (1, 2, 4, 8, 16, …) bitlerle hesabın kalbinde: her biri **tek bir bit** (`1, 10, 100, …`). Bu yüzden onlarla çarpma, bölme, mod ve hizalama işlemleri sıradan aritmetik yerine ucuz bit işlemlerine dönüşüyor. Ders 4.26 ve 4.28'de hizalama formüllerini kullandık; bu derste neden işe yaradıklarını topluyoruz. İşaretsiz (`unsigned`) sayılarla.

---

## 1. İkinin kuvveti testi

Ders 5.3'ten: bir sayı 2'nin kuvvetiyse tam bir biti 1'dir, ve `x & (x-1)` o biti siler:

```c
int is_pow2(uint32_t x) {
    return x && !(x & (x - 1));
}
```

```
x=3 pow2=0   x=16 pow2=1   x=17 pow2=0   x=65536 pow2=1
```

`x && ...` ile 0'ı eliyoruz (Ders 5.3'teki tuzak: 0, `x & (x-1)` testini yanlışlıkla geçer). `!(x & (x-1))`, "en sağdaki 1'i silince hiç bit kalmadı". Bu tek satır, bir hizalama değerinin ya da bir tampon boyutunun 2'nin kuvveti olup olmadığını kontrol etmenin standart yolu.

---

## 2. Bir sonraki 2'nin kuvvetine yuvarlama

`x`'ten büyük veya eşit en küçük 2'nin kuvvetini bulmak (Ders 4.24'teki dinamik dizi kapasitesi, hash tablosu boyutu gibi yerlerde gerekir):

```c
uint32_t round_up_pow2(uint32_t x) {
    if (x <= 1) return 1;
    x--;
    x |= x >> 1;
    x |= x >> 2;
    x |= x >> 4;
    x |= x >> 8;
    x |= x >> 16;
    return x + 1;
}
```

```
x=3 round_up=4   x=5 round_up=8   x=17 round_up=32   x=1000 round_up=1024   x=65536 round_up=65536
```

Bu "bit yayma" (bit smearing) hilesi şöyle çalışıyor: en üstteki 1'den sonraki bütün bitleri 1 yapıp sonra 1 eklemek. `x |= x >> 1`, en üstteki 1'i bir sağdaki bite de kopyalar; `>> 2` iki bite; `>> 4`, `>> 8`, `>> 16` ile en üstteki 1'in altındaki **bütün** bitler 1 olur (`1000...` → `1111...`). Sonra `+ 1` bir üst kuvvete taşır (`0111 + 1 = 1000`). Başta `x--`: `x` zaten 2'nin kuvvetiyse olduğu gibi kalsın diye (yoksa bir fazlasına çıkardı).

Beş kaydırma (`1, 2, 4, 8, 16`) 32 biti kapsıyor: her adım yayılan bit sayısını iki katına çıkarıyor, `1+2+4+8+16 = 31` bitlik bir boşluğu doldurmaya yeter. 64 bit için bir `>> 32` daha eklenir. C23'te bu iş için `stdc_bit_ceil` var; ama hile, derleyicinin yoksa ürettiği şeyin ta kendisi.

---

## 3. 2'nin kuvvetiyle bölme ve mod

İşaretsiz bir sayıyı 2'nin kuvvetine bölmek bir sağa kaydırma, mod almak bir maske:

$$x / 2^k = x \gg k \qquad x \bmod 2^k = x \mathbin{\&} (2^k - 1)$$

```c
1000 / 8   ==  1000 >> 3    // 125
1000 % 8   ==  1000 & 7     // 0
1003 % 8   ==  1003 & 7     // 3
```

**Bölme neden kaydırma?** Ders 3.18'den: sağa kaydırmak 2'nin kuvvetine bölmek. **Mod neden maske?** `x mod 2^k`, `x`'in alt `k` biti — çünkü üst bitler 2^k'nın katlarını temsil eder, mod'da yok olurlar; kalan tam olarak alt `k` bit, yani `x & (2^k - 1)` (Ders 5.2'deki alt-k-bit maskesi).

Derleyici bunu **zaten** yapıyor. `x % 8u`'in `-O2` çıktısı (ARM):

```
and	w0, w0, #0x7       <- % 8 yerine & 7
```

`x / 8u` ise `lsr w0, w0, #3` (sağa kaydırma). Yani `/` ve `%` yazmak yeterli; derleyici sabit 2'nin kuvvetlerinde onları bit işlemine çevirir — **işaretsizde**. İşaretli sayılarda bu dönüşüm daha karmaşık (negatif sayıda `/` sıfıra doğru yuvarlar, kaydırma değil; Ders 5.13), o yüzden işaretli `x % 8` daha uzun koda derlenir. Bölme ve mod için işaretsiz tip hem doğru hem hızlı.

---

## 4. Hizalama: hepsi tek bir maske

Ders 4.26'da donanımın her tipi kendi hizasında (2'nin kuvveti) istediğini, Ders 4.28'de arena allocator'da `align_up` yazdığımızı gördük. Şimdi o formüllerin neden böyle olduğunu görüyoruz. `a` bir 2'nin kuvveti olsun; `a - 1`, alt bitleri 1 olan maske (Ders 5.2):

```c
size_t align_down(size_t n, size_t a) { return n & ~(a - 1); }
size_t align_up(size_t n, size_t a)   { return (n + a - 1) & ~(a - 1); }
int    is_aligned(size_t n, size_t a) { return (n & (a - 1)) == 0; }
```

```
align_up(100, 16) = 112    align_down(100, 16) = 96    is_aligned(96, 16) = 1
```

- **`align_down`**: `~(a-1)`, alt bitleri 0, üstü 1 olan maske; `n & ~(a-1)` `n`'nin alt bitlerini siler, yani `a`'nın katına **aşağı** yuvarlar. Bölüm 3'teki `n & (a-1)` (mod) ile ilişki: `align_down(n,a) = n - (n % a)`.
- **`align_up`**: önce `n + a - 1` ile bir sonraki katı geçecek kadar artır, sonra `align_down`. Ders 4.28'de kullandığımız formül.
- **`is_aligned`**: `n & (a-1)`, `n`'nin `a`'ya bölümünden kalan (mod); 0 ise hizalı.

Üçü de 2'nin kuvveti olan `a` için **sadece** çalışıyor — `a - 1`'in temiz bir maske olması buna bağlı. Bir adresin hizalı olup olmadığını `n % a == 0` ile de test edebilirdin, ama `n & (a-1)` aynı şey ve daha hızlı (Bölüm 3). Hizalamanın donanımdaki ve allocator'lardaki her kullanımı (Ders 4.26, 4.28; Faz 10'daki sayfalar) bu üç formülün üzerine kurulu.

---

## Alıştırmalar

**1** – `round_up_pow2`'yi `x = 1`, `x = 2`, `x = 0` için adım adım izle. `x = 0` neden `1` döndürüyor (ipucu: `if (x <= 1)`)? `x = 0x80000001` (en üst bit + alt bit) için ne döner, ve neden bu bir sorun olabilir?

**2** – `x & (x-1)` ikinin kuvvetini test ediyor. Peki `x`'in **tam üç** biti 1 mi (ne eksik ne fazla) diye test eden bir ifade yaz. (İpucu: `x & (x-1)` ile en sağdaki 1'i sil, üç kez; Ders 5.3.)

**3** – `align_up(n, a) = n - (n % a) + (n % a == 0 ? 0 : a)` ile bit formülü `(n + a - 1) & ~(a - 1)`'in aynı sonucu verdiğini `n = 16, 17, 32`, `a = 16` için doğrula. Bit formülü neden `n` zaten hizalıyken `n` döndürüyor (bir üst kata çıkmıyor)?

**4** – `x % 8` ile `x & 7`'nin **işaretli** `x` için farklı sonuç verdiğini `x = -1` ile göster. `-1 % 8` kaç (C'de), `-1 & 7` kaç? Derleyici neden işaretli `% 8`'i basit bir `& 7`'ye çeviremiyor?

**5** – Bir sayıyı `a`'nın (2'nin kuvveti) en yakın katına (aşağı değil, en yakın) yuvarlayan `round_nearest(size_t n, size_t a)` yaz. (İpucu: `align_up(n + a/2, a)`? ya da `align_down(n + a/2, a)` — hangisi doğru, dene.)

<details>
<summary>Cevaplar</summary>

**1** – `x = 1`: `if (1 <= 1)` → `return 1`. `x = 2`: `x-- → 1`, `1 | 0 | ... = 1`, `return 1 + 1 = 2`. `x = 0`: `if (0 <= 1)` → `return 1` (0'dan büyük/eşit en küçük 2'nin kuvveti 1 kabul ediliyor — tanım gereği, 0 bir kuvvet değil). `x = 0x80000001`: `x-- → 0x80000000`, bit yayma `0xFFFFFFFF` yapar, `+ 1` → `0x100000000` ama bu 32 bite sığmaz, `0`'a sarar. **Sorun**: 2³¹'den büyük girdilerde sonuç (2³²) `uint32_t`'ye sığmaz ve 0 olur. Gerçek kodda bu uç durum kontrol edilmeli (ya da 64 bit kullanılmalı).

**2** – "Tam üç bit 1":

```c
int exactly_three_bits(uint32_t x) {
    if (x == 0) return 0;
    uint32_t y = x & (x - 1);      // 1 bit sil
    y &= y - 1;                    // 2. biti sil
    uint32_t z = y & (y - 1);      // 3. biti sil
    return y != 0 && z == 0;       // 2. silmeden sonra hala bit vardi, 3.ten sonra yok
}
```

En sağdaki 1'i iki kez silince hâlâ bit kalmalı (`y != 0`: en az 3 bit vardı), üçüncü silmeden sonra hiç kalmamalı (`z == 0`: tam 3 bit). Ya da Ders 5.8'deki `popcount(x) == 3` — daha okunur.

**3** – `n = 16, a = 16`: `n % a = 0`, aritmetik formül `16 - 0 + 0 = 16`; bit `(16 + 15) & ~15 = 31 & ~15 = 16`. `n = 17`: aritmetik `17 - 1 + 16 = 32`; bit `(17+15) & ~15 = 32 & ~15 = 32`. `n = 32`: ikisi de 32. Bit formülü hizalıyken `n` döndürür, çünkü `n` zaten `a`'nın katıysa alt bitleri 0'dır; `n + a - 1` eklemek onu bir sonraki katın hemen **altına** taşır (`a-1` kadar), `& ~(a-1)` geri aynı kata iner — bir üste çıkmaz. `a - 1` tam da "tam katta kalma, bir fazlasında çık" sınırını veriyor.

**4** – C'de `-1 % 8 = -1` (mod işleminin sonucu bölünenin işaretini alır; Ders 2'deki `%`). `-1 & 7 = 7` (`-1` tüm bitler 1, alt 3 bit `111` = 7). Farklılar: `-1` vs `7`. Derleyici işaretli `% 8`'i basit `& 7`'ye çeviremez, çünkü negatif sayıda sonuç farklı olurdu; işaretli mod için önce işareti ayıran daha uzun kod üretir. İşaretsizde `x % 8` her zaman `x & 7`'ye eşit olduğu için çevirebilir. Bu, 2'nin kuvvetiyle mod/bölme için işaretsiz tip kullanmanın bir sebebi daha.

**5** –

```c
size_t round_nearest(size_t n, size_t a) {
    return align_down(n + a / 2, a);
}
```

`align_down(n + a/2, a)` doğru: ortaya `a/2` ekleyip aşağı yuvarlamak, en yakın kata yuvarlar. `n = 20, a = 16`: `20 + 8 = 28`, `align_down(28,16) = 16` (20, 16'ya 24'ten yakın). `n = 25, a = 16`: `25 + 8 = 33`, `align_down(33,16) = 32` (25, 32'ye yakın). `align_up(n + a/2, a)` ise yanlış — bir fazla kata çıkabilir (tam ortadaki değerler için). Sınırda (tam `a/2` uzaklık) bu formül yukarı yuvarlar; "yarıyı yukarı" kuralı. `a` 2'nin kuvveti olduğu için `a/2` de kaydırma (`a >> 1`).

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §3.1 (2'nin kuvvetine yuvarlama), §3.2 (hizalama).
- Sean Anderson, "Bit Twiddling Hacks": round up to power of 2, power-of-2 testi.
- C standardı (ISO/IEC 9899:2018), §6.5.5 (bölme ve mod'un işaretli davranışı). C23: `<stdbit.h>` `stdc_bit_ceil`.
- Ders 4.26 (hizalama ve dolgu) ve Ders 4.28 (arena allocator): bu formüllerin kullanıldığı yerler.

**Sıradaki ders:** Popcount ve parite. Kernighan yöntemi, paralel (SWAR) bit toplama adım adım ve `popcnt` komutu.
