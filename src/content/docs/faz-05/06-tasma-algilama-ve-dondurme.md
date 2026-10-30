---
title: "5.6 Taşma algılama ve döndürme"
description: "İşaretsiz toplamanın taşmasını (a+b)<a ile, çarpmanın taşmasını 64 bite genişleterek bit düzeyinde bulmak; bit döndürme (rotate): (x<<n)|(x>>(32-n)), n=0'da x>>32'nin undefined behavior olması ve n&31 ile güvenli hale getirmek, derleyicinin bu kalıbı tanıyıp tek bir ror/rol komutuna çevirmesi."
---

Ders 3.8'de taşmayı derleyicinin `__builtin_add_overflow` gibi yardımcılarıyla yakalamıştık. Bu derste taşmayı **bit düzeyinde kendimiz** buluyoruz — hem nasıl çalıştığını anlamak için, hem de bu yardımcıların altında ne olduğunu görmek için. Sonra yeni bir işlem ekliyoruz: bit **döndürme** (rotate), kaydırmanın dışarı taşan bitleri diğer uçtan geri getiren hali. İkisi de işaretsiz (`unsigned`) sayılarla.

---

## 1. İşaretsiz toplamada taşma

İki işaretsiz sayı toplanırken sonuç 32 bite sığmazsa, mod 2³² sarılır (Ders 3.8). Taşma olduğunu nasıl anlarız? Basit bir gözlem: **taşma olduysa, toplam toplananlardan küçük olur.**

```c
int add_overflows(uint32_t a, uint32_t b) {
    return (a + b) < a;
}
```

```
0xFFFFFFFF + 1 tasti mi? 1
100 + 200 tasti mi? 0
```

Neden çalışıyor? `a + b` taşmazsa sonuç en az `a` kadardır (`b >= 0`). Taşarsa, mod 2³² yüzünden sonuç `a + b - 2³²` olur; `b < 2³²` olduğu için bu `a`'dan **küçük**. Yani `(a + b) < a` tam olarak taşma koşulu. `< b` ile de test edilebilir (simetrik). Bu, işaretsiz toplamanın "sarması" özelliğinin — Ders 3.8'de tanımlı davranış olduğunu söylemiştik — pratik bir kullanımı.

Dikkat: bu sadece **işaretsizde** çalışır. İşaretli taşma undefined behavior olduğu için (Ders 3.8), `(a + b) < a` numarası işaretli sayılarda geçerli değil; orada `__builtin_add_overflow` ya da Ders 3.8'deki ön kontroller gerekir.

---

## 2. Çarpmada taşma: genişleterek

Çarpmada "sonuç küçükse taştı" numarası işe yaramıyor (çarpım tahmin edilemez şekilde sarar). En temiz yol, çarpımı **daha geniş** bir tipte yapıp sonuca bakmak:

```c
int umul_overflows(uint32_t a, uint32_t b, uint32_t *result) {
    uint64_t wide = (uint64_t)a * b;
    *result = (uint32_t)wide;
    return wide > 0xFFFFFFFFu;
}
```

```
0x10000 * 0x10000 tasti mi? 1 (r=0x0)
1000 * 1000 tasti mi? 0 (r=1000000)
```

İki 32 bitlik sayının çarpımı en fazla 64 bit olabilir, o yüzden `uint64_t` her zaman yeter. `(uint64_t)a * b`: `a`'yı önce 64 bite çevirince çarpma 64 bitte yapılır (Ders 3.5'teki tip yükseltme), taşma olmaz. Sonuç 2³²'den büyükse, 32 bite sığmayacağı için taşma var demektir. `*result`, çıkış parametresiyle (Ders 4.7) 32 bitlik alt kısmı da veriyor.

Bu, Ders 3.8'deki `__builtin_mul_overflow`'un 32 bit için tam olarak yaptığı şey. Peki 64 bitlik sayıların çarpımında taşmayı nasıl buluruz — 128 bitlik tip her yerde yok? O zaman çarpımın **yüksek yarısına** bakmak gerekir; bunu Ders 5.13'te (çok kelimeli aritmetik) göreceğiz. Derleyicinin builtin'leri bu yüksek yarı komutunu (ARM'da `umulh`) kullanıyor.

---

## 3. Döndürme (rotate)

Kaydırmada (`<<`, `>>`) dışarı taşan bitler kaybolur. **Döndürmede** (rotate) ise diğer uçtan geri gelirler — bitler bir çember gibi dönüyor. `rotl` (sola döndür):

```c
uint32_t rotl(uint32_t x, int n) {
    return (x << n) | (x >> (32 - n));
}
```

`x << n` bitleri `n` sola iter (üstten taşanlar kaybolur), `x >> (32 - n)` o taşan üst bitleri alttan geri getirir; `|` ikisini birleştirir.

```c
uint32_t x = 0x12345678;
rotl(x, 8)   // 0x34567812  (ust byte alta dondu)
rotl(x, 4)   // 0x23456781
```

`rotl(0x12345678, 8)` = `0x34567812`: en üstteki `0x12` byte'ı en alta döndü. Döndürme, kriptografide (hash fonksiyonları, şifreler — SHA, ChaCha), karma (hash) hesaplamada ve bit desenlerini kaydırmadan "çevirmekte" sürekli kullanılır.

### n = 0 tuzağı

Yukarıdaki `rotl`'de gizli bir hata var: `n = 0` olursa `x >> (32 - 0)` = `x >> 32`, ve Ders 5.1'den biliyoruz ki 32 bitlik bir tipi 32 kaydırmak **undefined behavior**. Güvenli hali:

```c
uint32_t rotl_safe(uint32_t x, int n) {
    n &= 31;                      // n'yi 0-31 araligina indir
    return n ? (x << n) | (x >> (32 - n)) : x;
}
```

`n &= 31`, `n`'yi 0-31 arasına kısıtlar (döndürme zaten 32'de başa sarar, `rotl(x, 32) == rotl(x, 0)`). `n ? ... : x`, `n = 0` durumunu ayırıp `x >> 32`'den kaçınır. Bu, döndürmeyi her `n` için tanımlı yapar.

### Derleyici rotate'i tanıyor

C'de ayrı bir döndürme operatörü yok (çoğu işlemcide bir **komut** olmasına rağmen). Ama derleyici `(x << n) | (x >> (32 - n))` kalıbını **tanıyor** ve tek bir komuta çeviriyor. `rotl`'ün `-O2` çıktısı (bu makine, ARM):

```
_rotl:
	ror	w0, w0, w8
	ret
```

Tek komut: `ror` (rotate right — ARM'da sola döndürme, 32−n sağa döndürme olarak yapılır; x86'da bu `rol` olurdu). Yani C'de operatör olmasa da, deyimi doğru yazarsak derleyici donanımın tek komutunu kullanıyor. C23 bu yüzden `<stdbit.h>`'e `stdc_rotate_left`/`stdc_rotate_right` ekledi — ama deyim zaten çalıştığı için çoğu kod onu kullanıyor.

Bu, bu fazın tekrar eden dersi: bit hilesini **neden** işe yaradığını anlamak için yazıyoruz; derleyici onu hız için zaten tanıyor.

---

## Alıştırmalar

**1** – `add_overflows(a, b)` için `(a + b) < a` yerine `(a + b) < b` yazmak da doğru mu? İkisi her `a`, `b` için aynı sonucu mu verir? `a = 0` durumunu düşün.

**2** – İşaretsiz **çıkarmada** taşma (aslında "alttan taşma", underflow): `a - b`'nin saramaması için koşul nedir? `sub_underflows(uint32_t a, uint32_t b)` yaz. (İpucu: `a < b` ise sonuç sarar.)

**3** – `rotr` (sağa döndür) fonksiyonunu `rotl` cinsinden yaz: `rotr(x, n) == rotl(x, ?)`. Bir sayıyı önce `rotl(x, 8)` sonra `rotr(x, 8)` döndürünce `x`'e geri döner mi? Neden döndürme tersinir?

**4** – `rotl(x, 8)` bir `uint32_t`'de byte sırasını nasıl değiştirir? `rotl` ile 4 byte'ın tamamını ters çeviren (endian swap, Ders 3.9) bir fonksiyon yazılabilir mi, yoksa başka bir şey mi gerekir? (İpucu: döndürme bitleri döndürür, byte'ları yeniden sıralamaz.)

**5** – `umul_overflows`'u `uint64_t` yerine, Ders 5.1'deki gibi iki `uint32_t`'nin çarpımının 32 bite sığması için `a == 0 || b <= 0xFFFFFFFF / a` ön koşuluyla yaz (bölme ile, genişletmeden). İki yöntemden hangisi daha açık, hangisi 64 bit tip olmayan bir makinede gerekli?

<details>
<summary>Cevaplar</summary>

**1** – `(a + b) < b` de doğru, ve her `a`, `b` için `(a + b) < a` ile **aynı** sonucu verir: taşma olduysa toplam hem `a`'dan hem `b`'den küçüktür, olmadıysa her ikisinden de büyük/eşittir. Simetri toplamanın değişmeliğinden. `a = 0`: `(0 + b) < 0` → `b < 0`, işaretsizde her zaman yanlış (taşma yok, doğru — 0 + b taşmaz). `(0 + b) < b` → `b < b`, yine yanlış. İkisi de "taşma yok" diyor, tutarlı.

**2** –

```c
int sub_underflows(uint32_t a, uint32_t b) {
    return a < b;
}
```

İşaretsiz `a - b`, `b > a` iken sarar (Ders 5.4'te `30 - 50`'nin büyük bir pozitif verdiğini görmüştük). Koşul tam olarak `a < b`. Toplamadaki "sonuca bak" numarasına gerek yok; çıkarmada taşma, girdilere bakarak doğrudan bellidir. (Toplamada da `a > UINT_MAX - b` ile önceden bakılabilir; iki yaklaşım da geçerli.)

**3** – `rotr(x, n) == rotl(x, 32 - n)` (`n`'yi `&31` sonrası). Sağa `n` döndürmek, sola `32 - n` döndürmekle aynı — çember 32 adımlık. `rotl(x, 8)` sonra `rotr(x, 8)`: ilki bitleri 8 sola, ikincisi 8 sağa döndürür, net etki sıfır, `x`'e döner. Döndürme tersinir çünkü hiç bit kaybolmaz (kaydırmanın aksine); her bit sadece yer değiştirir, ters yönde döndürünce eski yerine gelir. Matematiksel olarak `rotl(·, n)` ve `rotl(·, 32-n)` birbirinin tersi.

**4** – `rotl(x, 8)` byte'ları **döndürür** ama ters çevirmez: `0x12345678` → `0x34567812` (her byte 8 bit, bir pozisyon ileri döndü, en üstteki en alta geçti). Endian swap (`0x12345678` → `0x78563412`) byte'ların **sırasını tersine çevirmek** demek, bu döndürmeyle olmaz — döndürme dairesel bir kaydırma, sıra ters çevirme değil. Endian swap için ya byte byte maskeleme (`((x & 0xFF) << 24) | ...`) ya da `__builtin_bswap32` gerekir. Döndürme bir rotasyon, ters çevirme bir yansıma; farklı işlemler.

**5** –

```c
int umul_overflows_div(uint32_t a, uint32_t b) {
    return a != 0 && b > 0xFFFFFFFFu / a;
}
```

`a * b > UINT_MAX` koşulunu, taşmadan, `b > UINT_MAX / a` diye yazıyoruz (bölme taşmaz; `a != 0` sıfıra bölmeyi engeller). **Açıklık**: 64 bitlik genişletme (`(uint64_t)a * b`) daha açık ve doğrudan — "geniş çarp, sığıyor mu bak". **Gereklilik**: bölme yöntemi, 32 bitten geniş bir tip **olmayan** bir makinede (ya da 64 bit çarpımın taşmasını kontrol ederken, 128 bit tip yoksa) gerekli — orada genişletecek tip olmadığı için bölmeyle önceden kontrol tek yol. Pratikte: mümkünse genişlet (açık ve hızlı); genişletecek tip yoksa bölme ön koşulu.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §2.12 (taşma algılama), §2.15 (rotate).
- C standardı (ISO/IEC 9899:2018), §6.2.5¶9 (işaretsiz sarma), §6.5.7 (kaydırma UB). C23: `<stdbit.h>` döndürme fonksiyonları.
- Sean Anderson, "Bit Twiddling Hacks": merge/rotate kalıpları.
- SEI CERT C Coding Standard, INT30-C (işaretsiz taşmayı kontrol etmek).

**Sıradaki ders:** 2'nin kuvvetleri ve hizalama. İkinin kuvveti testi, bir sonraki kuvvete yuvarlama ve adres hizalaması.
