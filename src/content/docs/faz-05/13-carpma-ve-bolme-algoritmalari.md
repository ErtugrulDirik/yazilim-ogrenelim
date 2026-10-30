---
title: "5.13 Çarpma ve bölme algoritmaları"
description: "Çarpma ve bölmeyi bit işlemleriyle kurmak: kaydır-topla çarpma (ikilik uzun çarpma), kaydır-çıkar bölme (ikilik uzun bölme) bölüm ve kalanla, çarpımın yüksek yarısını 64 bite genişleterek bulmak ve neden gerektiği, ve iki 32-bit yarıyla 64-bit toplama yaparak çok kelimeli aritmetikte elde taşımayı görmek."
---

Ders 5.4'te toplamayı XOR ve eldeye ayırmıştık. Bu derste çarpma ve bölmeyi de temel işlemlere indiriyoruz: **kaydır-topla** ile çarpma, **kaydır-çıkar** ile bölme. Bunlar işlemcinin (ve Faz 7'de yazacağımız bir donanımın) bu işlemleri nasıl yaptığının ta kendisi. Sonra iki pratik konu: bir çarpımın **yüksek yarısı** ve **çok kelimeli** aritmetikte elde taşıma. İşaretsiz (`unsigned`) sayılarla.

---

## 1. Kaydır-topla çarpma

Okulda öğrendiğimiz uzun çarpmanın ikilik hali. Ondalıkta her basamak için çarpıp kaydırıp toplarız; ikilikte her basamak 0 ya da 1, yani her adım ya **hiçbir şey ekleme** ya da **kaydırılmış çarpanı ekle**:

```c
uint32_t mul_shiftadd(uint32_t a, uint32_t b) {
    uint32_t result = 0;
    while (b) {
        if (b & 1) {          // b'nin su anki biti 1 ise
            result += a;      // kaydirilmis a'yi ekle
        }
        a <<= 1;              // a'yi iki katina (bir basamak sola)
        b >>= 1;              // b'nin bir sonraki bitine gec
    }
    return result;
}
```

```
13 * 11 = 143
255 * 255 = 65025
```

`13 = 1101₂`, `11 = 1011₂`. `b = 11`'in bitlerini gez: bit 0 = 1 → `result += 13`; bit 1 = 1 → `result += 26` (13<<1); bit 2 = 0 → atla; bit 3 = 1 → `result += 104` (13<<3). Toplam `13 + 26 + 104 = 143`. Her adımda `a` ikiye katlanıyor (`<< 1`), `b`'nin biti 1 olan konumlarda o değer toplanıyor. Bu, çarpmanın "kaydır ve topla" tanımı — Ders 5.8'deki popcount SWAR'ının son adımında (`x * 0x01010101`) bu toplama özelliğini kullanmıştık.

Ders 3.18'de "derleyici 2'nin kuvvetiyle çarpmayı kaydırmaya çeviriyor" demiştik; bu algoritma onun genel hali: her çarpma, kaydırmaların toplamı.

---

## 2. Kaydır-çıkar bölme

Uzun bölmenin ikilik hali. Bölüneni basamak basamak "indirip", bölen sığıyorsa çıkarıp bölüme 1 yazıyoruz:

```c
uint32_t div_shiftsub(uint32_t n, uint32_t d, uint32_t *rem) {
    uint32_t q = 0, r = 0;
    for (int i = 31; i >= 0; i--) {
        r = (r << 1) | ((n >> i) & 1);   // kalana bir sonraki basamagi indir
        if (r >= d) {
            r -= d;                      // bolen sigiyorsa cikar
            q |= (1u << i);              // bolume 1 yaz
        }
    }
    if (rem) *rem = r;
    return q;
}
```

```
1000 / 7 = 142, kalan 6
0xFFFFFFFF / 3 = 1431655765, kalan 0
```

En yüksek bitten başlayıp bölüneni bit bit `r`'ye (kalan) indiriyoruz. Her adımda `r`, bölen `d`'den büyük/eşitse: `d`'yi çıkar, o konumun bölüm bitini 1 yap. Bu, elle yaptığımız uzun bölmenin aynısı — "bölen bu kısma sığıyor mu?" sorusu, ikilikte "evet/hayır" (bölüm biti 1/0). 32 adımda hem bölüm (`q`) hem kalan (`r`) çıkıyor; bölme ve mod'u tek geçişte veriyor (Ders 2'deki `/` ve `%`). Bölme, işlemcilerin en yavaş aritmetik işlemi olmasının sebebi bu 32 adımlık döngü; çarpma çok daha hızlıdır, bu yüzden Ders 5.14'te bölmeyi çarpmaya çevireceğiz.

---

## 3. Çarpımın yüksek yarısı

İki 32-bit sayının çarpımı 64 bit olabilir. Sıradan `a * b` (32-bit) sadece **alt** 32 biti verir (üst yarı kaybolur; Ders 3.8'deki taşma). Üst yarıya nasıl ulaşırız? 64 bite genişleterek (Ders 5.6):

```c
uint32_t a = 0xFFFFFFFF, b = 0xFFFFFFFF;
uint64_t wide = (uint64_t)a * b;
uint32_t high = (uint32_t)(wide >> 32);   // yuksek yari
uint32_t low  = (uint32_t)wide;           // alt yari
```

```
0xFFFFFFFF * 0xFFFFFFFF = high 0xFFFFFFFE, low 0x00000001
```

`(uint64_t)a * b`, çarpmayı 64 bitte yapar (Ders 5.6'daki taşma tespiti); `>> 32` üst yarıyı verir. Donanımda bu, ayrı bir komut: ARM'da `umulh` (unsigned multiply high), x86'da `mul`'un üst register'ı. Neden gerekir? Sabite bölme hilesinde (Ders 5.14) ve çok kelimeli çarpmada (64-bit sayıları 32-bit parçalarla çarparken) ara çarpımların üst yarısı lazım. 64-bit × 64-bit çarpımın üst yarısı için ise, 128-bit tip yoksa, bu `umulh`'a doğrudan ihtiyaç var (Ders 5.6'daki "64-bit taşma" sorusunun cevabı).

---

## 4. Çok kelimeli aritmetik: elde taşıma

Bir makine 32-bit (ya da 64-bit) sayılarla çalışıyor ama daha büyük sayılara ihtiyacımız varsa (kriptografi, büyük sayı kütüphaneleri), sayıları birden çok "kelime"ye (word) bölüp parça parça işleriz — **çok kelimeli** (multiword) aritmetik. İşin püf noktası, Ders 5.6'daki elde taşıma. İki 64-bit sayıyı, iki 32-bit yarım halinde toplayalım:

```c
void add128(uint32_t a_hi, uint32_t a_lo, uint32_t b_hi, uint32_t b_lo,
            uint32_t *r_hi, uint32_t *r_lo) {
    uint32_t lo = a_lo + b_lo;
    uint32_t carry = (lo < a_lo);        // alt yari tasti mi? (Ders 5.6)
    *r_lo = lo;
    *r_hi = a_hi + b_hi + carry;         // elde'yi ust yariya tasi
}
```

```
0x00000001_FFFFFFFF + 0x00000000_00000001 = 0x00000002_00000000
```

Alt yarıları topla; taştıysa (`lo < a_lo`, Ders 5.6'daki işaretsiz taşma tespiti) bir **elde** doğar; o eldeyi üst yarının toplamına ekle. Tam olarak Ders 0.2'deki ve okuldaki toplamadaki "elde bir sonraki basamağa" — ama basamak yerine 32-bit kelimeler. Çıkarma, çarpma ve bölme de aynı mantıkla kelime kelime kurulur (çarpmada Bölüm 3'teki yüksek yarı, ara çarpımların eldesini taşır).

Bu, keyfi büyüklükte tamsayılarla (bignum) çalışan kütüphanelerin temeli; RSA gibi kriptografi 2048-bit sayılarla bu şekilde hesaplar. Donanımın "carry flag"i (elde bayrağı) tam bu taşımayı destekler; C'de `__builtin_add_overflow` (Ders 3.8) ya da `lo < a_lo` kontrolüyle yaparız.

---

## Alıştırmalar

**1** – `mul_shiftadd(6, 5)`'i adım adım izle (`6 = 110₂`, `5 = 101₂`). Hangi adımlarda `result += a` çalışıyor, her adımda `a` kaç? Toplam 30 mu?

**2** – `div_shiftsub`'da `d = 0` (sıfıra bölme) ne olur? Döngü çöker mi, yoksa yanlış sonuç mu verir? Gerçek donanımda sıfıra bölme ne yapar (Ders 3.8'deki `LONG_MIN / -1` tuzağını hatırla)?

**3** – `mul_shiftadd` 32-bit sonucun **taşan** kısmını (üst 32 bit) atıyor. Onu da tutan, `uint64_t` sonuç döndüren bir sürüm yaz. Bölüm 3'teki `(uint64_t)a * b` ile aynı sonucu mu veriyor?

**4** – Kaydır-çıkar bölmede her adım bir `<<`, bir karşılaştırma, belki bir çıkarma: 32 adım. Kaydır-topla çarpma da ~32 adım. İkisi de $O(w)$ ($w$ = bit sayısı). Peki neden donanımda çarpma bölmeden çok daha hızlı (çarpma birkaç çevrim, bölme onlarca)? (İpucu: çarpmanın adımları paralelleştirilebilir, bölmeninki birbirine bağlı.)

**5** – `add128`'i kullanarak, 64-bit bir sayıyı iki 32-bit yarıyla temsil edip 1 ekleyen `inc128` yaz. `a_lo = 0xFFFFFFFF` iken 1 eklemek `a_hi`'yi nasıl etkiler? Bu, çok kelimeli aritmetikte en sık elde taşıma durumu.

<details>
<summary>Cevaplar</summary>

**1** – `a = 6`, `b = 5 = 101₂`. Adım 0: `b & 1 = 1` → `result += 6` (result=6); `a = 12`, `b = 10₂ = 2`. Adım 1: `b & 1 = 0` → atla; `a = 24`, `b = 1`. Adım 2: `b & 1 = 1` → `result += 24` (result=30); `a = 48`, `b = 0`, döngü biter. `result += a` adım 0 (`a=6`) ve adım 2'de (`a=24`) çalıştı; `6 + 24 = 30 = 6 × 5`. Doğru. `b`'nin 1 olan bitleri (bit 0 ve bit 2), `a`'nın o kadar kaydırılmış halini topladı.

**2** – `d = 0`: döngüde `r >= d` her zaman doğru (`r >= 0`), her adımda `r -= 0` (değişmez) ve `q`'nun her biti 1 olur → `q = 0xFFFFFFFF`, `r = n`'in bir kalıntısı. Çökmez ama **anlamsız** sonuç verir (matematikte sıfıra bölme tanımsız). Gerçek donanımda tamsayı sıfıra bölme bir **istisna/trap** üretir (x86'da `#DE`, program çöker) — Ders 3.8'deki `LONG_MIN / -1` gibi tanımsız, ama bu sefer donanım yakalıyor. Bizim yazılım bölmemiz bunu kendisi kontrol etmeli (`if (d == 0) return ...`).

**3** –

```c
uint64_t mul_wide(uint32_t a, uint32_t b) {
    uint64_t result = 0;
    uint64_t aa = a;
    while (b) {
        if (b & 1) result += aa;
        aa <<= 1;
        b >>= 1;
    }
    return result;
}
```

`a`'yı `uint64_t`'ye (`aa`) alıp 64 bitte topluyoruz; `aa <<= 1` artık 32 biti aşabilir ve kaybolmaz. `mul_wide(0xFFFFFFFF, 0xFFFFFFFF)` = `(uint64_t)a * b` ile aynı: `0xFFFFFFFE00000001`. Donanım çarpması tam bunu tek komutta yapar; biz 32 adımda, ama aynı 64-bit sonucu.

**4** – İkisi de $O(w)$ adım, ama **bağımlılık yapısı** farklı. Çarpmada, `b`'nin her biti için "kaydırılmış `a`" birbirinden **bağımsız** hesaplanabilir; donanım hepsini aynı anda üretip bir ağaç toplayıcıyla (Wallace tree) birkaç çevrimde toplar — paralel. Bölmede ise her adımın kalanı, bir önceki adımın sonucuna **bağlı** (`r = (r << 1) | ...`, sonra `r -= d`); bir sonraki basamağı bulmak için bu basamağı bitirmen gerekir — paralelleştirilemez, adım adım. Bu yüzden donanım çarpması birkaç çevrim, bölmesi onlarca. Ders 5.14'te bölmeyi (sabit bölenlerde) çarpmaya çevirerek bu maliyetten kaçacağız.

**5** –

```c
void inc128(uint32_t *hi, uint32_t *lo) {
    uint32_t new_lo = *lo + 1;
    if (new_lo < *lo) {      // alt yari tasti (0xFFFFFFFF -> 0)
        (*hi)++;             // elde ust yariya
    }
    *lo = new_lo;
}
```

`a_lo = 0xFFFFFFFF` iken 1 eklemek `new_lo = 0` yapar ve `0 < 0xFFFFFFFF` olduğu için taşma algılanır, `*hi` bir artar — tam Ders 5.6'daki elde. Yani `0x00000000_FFFFFFFF + 1 = 0x00000001_00000000`: alt yarı sıfırlandı, elde üst yarıya taşındı. Bu, çok kelimeli sayaçlarda (ve 64-bit olmayan makinelerde 64-bit zaman damgalarında) en sık görülen elde taşıma; kelime sayısı arttıkça (128, 256 bit) aynı taşıma zinciri uzar.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §8 (çarpma), §9 (bölme), çok kelimeli aritmetik.
- Donald Knuth, *TAOCP* Cilt 2, §4.3.1: çok kelimeli (classical) aritmetik algoritmaları.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.3: çarpma ve bölmenin makine düzeyi.
- ARM `umulh`, x86 `mul`/`div`: donanım komutları.

**Sıradaki ders:** Sabite bölme. Sihirli sayıyla çarpma, `x / 7`'nin godbolt'ta çarpmaya dönüşmesi ve sihirli sayıyı hesaplayan programı yazmak.
