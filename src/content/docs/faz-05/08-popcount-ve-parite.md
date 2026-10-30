---
title: "5.8 Popcount ve parite"
description: "Bir sayıda kaç bitin 1 olduğunu saymak: her biti tek tek gezen naif yöntem, Ders 5.3'teki x & (x-1) ile Kernighan yöntemi (1 sayısı kadar adım), ve bitleri 2'li-4'li-8'li gruplar halinde paralel toplayan SWAR yöntemi adım adım; parite (1'lerin tek/çift olması) XOR katlamayla; __builtin_popcount ve popcnt/cnt donanım komutu, ölçülen hız farkları."
---

**Popcount** (population count): bir sayıda kaç bitin 1 olduğunu saymak. Basit görünen bu işlem, hata düzeltme kodlarından (Ders 5.19) veri yapılarına, satranç motorlarından (Ders 5.20) makine öğrenmesine kadar her yerde, ve o kadar önemli ki işlemciler için **tek bir komut** haline gelmiş. Bu derste onu üç farklı yoldan yazıp, naiften donanım hızına nasıl çıkıldığını göreceğiz. **Parite** (1'lerin sayısının tek mi çift mi olduğu) da yakın akrabası.

---

## 1. Naif: her biti gez

```c
int popcount_naive(uint32_t x) {
    int count = 0;
    for (int i = 0; i < 32; i++) {
        count += (x >> i) & 1;
    }
    return count;
}
```

Her biti sağa kaydırıp `& 1` ile oku, topla (Ders 5.2'deki test). Doğru, ama `x` ne olursa olsun **her zaman 32 adım**. Çok 0'lı sayılarda bu israf.

---

## 2. Kernighan: 1 sayısı kadar adım

Ders 5.3'teki `x & (x - 1)` en sağdaki 1'i siliyordu. Kaç kez silebildiğimiz, kaç 1 olduğudur:

```c
int popcount_kernighan(uint32_t x) {
    int count = 0;
    while (x != 0) {
        x &= x - 1;    // en sagdaki 1'i sil
        count++;
    }
    return count;
}
```

Döngü **1 sayısı** kadar dönüyor (Ders 5.3): `0x80000000` için 1 adım, `0xFF` için 8. Az 1'li sayılarda naiften çok hızlı; dolu sayılarda (`0xFFFFFFFF`) ikisi de 32. Ortalama rastgele veride ~16 adım.

---

## 3. SWAR: paralel sayma

En hızlı taşınabilir yöntem, saymayı **paralel** yapmak: bitleri gruplara ayırıp her grubun 1'lerini aynı anda toplamak. Buna **SWAR** denir (SIMD Within A Register — bir register içinde paralel işlem). Fikir, "böl ve topla": önce komşu bit çiftlerinin toplamını her çiftin yerine yaz, sonra çiftleri dörtlü yap, dörtlüleri sekizli…

```c
int popcount_swar(uint32_t x) {
    x = x - ((x >> 1) & 0x55555555);                   // 1: 2'li gruplarin sayimi
    x = (x & 0x33333333) + ((x >> 2) & 0x33333333);    // 2: 4'lu gruplar
    x = (x + (x >> 4)) & 0x0F0F0F0F;                    // 3: 8'li gruplar
    x = (x * 0x01010101) >> 24;                         // 4: 4 byte'i topla
    return (int)x;
}
```

Adım adım, maskelerin anlamı (Ders 5.2):

- **`0x55555555`** = `0101...0101`: her çiftin alt biti. **Adım 1** zekice: her 2-bitlik grupta 1 sayısını, o grubun yerine yazıyor. `x - ((x >> 1) & 0x55)` özdeşliği, her çift için "üst bit + alt bit"i hesaplıyor (2-bitlik bir grupta 1 sayısı 0, 1 ya da 2, hepsi 2 bite sığar).
- **`0x33333333`** = `0011...0011`: her 4'lünün alt yarısı. **Adım 2**, komşu iki 2-bitlik sayımı toplayıp 4-bitlik gruplara koyuyor (en fazla 4, 4 bite sığar).
- **`0x0F0F0F0F`**: her byte'ın alt yarısı. **Adım 3**, komşu iki 4-bitlik sayımı toplayıp byte başına koyuyor (en fazla 8).
- **Adım 4**: artık her byte, o byte'taki 1 sayısını tutuyor (0-8). `x * 0x01010101` çarpımı, dört byte'ı en üst byte'ta **toplar** (çarpmanın kaydır-topla doğası; Ders 5.13), `>> 24` o toplamı en alta getirir. Toplam en fazla 32, tek byte'a sığar.

32 bit, **sabit 4 adımda** sayıldı — `x`'in içeriğinden bağımsız, dalsız (Ders 5.5), döngüsüz. Bütün popcount yöntemleri aynı cevabı veriyor:

```
0x12345678  naive=13 kern=13 swar=13 builtin=13   OK
0xFFFFFFFF  naive=32 kern=32 swar=32 builtin=32   OK
0xAAAAAAAA  naive=16 kern=16 swar=16 builtin=16   OK
```

---

## 4. Donanım: popcnt

Popcount o kadar sık gerekiyor ki, modern işlemcilerde **tek bir komut**: x86'da `popcnt`, ARM'da `cnt`. C'de doğrudan bir operatör yok, ama derleyici builtin'i var:

```c
__builtin_popcount(x)     // int icin
__builtin_popcountll(x)   // long long icin
```

`__builtin_popcount`'un `-O2` çıktısı (bu makine, ARM):

```
cnt.8b  v0, v0      <- her byte'in 1'lerini say (NEON)
...                 <- byte'lari topla
```

Tek bir donanım komutuyla (artı byte'ları toplayan birkaç komut). C23 bunu standartlaştırdı: `<stdbit.h>`'teki `stdc_count_ones`. Rastgele 1M sayıda ölçtük:

```
naive     0.467 s
kernighan 0.093 s
swar      0.093 s
builtin   0.094 s
```

Naif 5 kat yavaş; Kernighan, SWAR ve builtin neredeyse eşit (derleyici SWAR'ı ve Kernighan'ı da iyi optimize ediyor, builtin ise donanım komutunu kullanıyor). Pratik kural: **popcount gerektiğinde `__builtin_popcount` (ya da C23'te `stdc_count_ones`) kullan**; SWAR'ı, donanım komutu olmayan bir hedefte ya da nasıl çalıştığını anlamak için bil.

---

## 5. Parite: tek mi çift mi

Parite, "1'lerin sayısı tek mi?" sorusu — yani `popcount(x) & 1`. Ama tek tek saymadan, XOR ile daha hızlı hesaplanır. XOR'un özelliği (Ders 5.1): iki biti XOR'lamak, "1 sayısı tek mi" demek. Bütün bitleri birbiriyle XOR'lamak için **katlama** (folding):

```c
int parity(uint32_t x) {
    x ^= x >> 16;    // ust yari ile alt yariyi XOR'la
    x ^= x >> 8;
    x ^= x >> 4;
    x ^= x >> 2;
    x ^= x >> 1;
    return x & 1;
}
```

Her adım sayıyı ikiye katlayıp iki yarıyı XOR'luyor: 32 bit → 16 → 8 → 4 → 2 → 1. Sonunda en alttaki bit, bütün bitlerin XOR'u = pariteyi verir. 5 adım, dalsız.

```
0xFF parity=0        (8 bir, cift)
0x12345678 parity=1  (13 bir, tek)
0xFFFFFFFF parity=0  (32 bir, cift)
```

Parite, en basit **hata algılama** yöntemi: bir veriye bir "parite biti" eklenir ki toplam 1 sayısı hep çift olsun; tek bir bit bozulursa parite değişir ve hata yakalanır (ama düzeltilemez). Ders 5.19'da bunun üzerine kurulu Hamming kodunu göreceğiz. `__builtin_parity` da var, donanımda genelde `popcount & 1` olarak yapılır.

---

## Alıştırmalar

**1** – SWAR'ın ilk adımını (`x - ((x >> 1) & 0x55555555)`) `x = 0b1110` için elle hesapla. Sonuç neden her 2-bitlik grupta o grubun 1 sayısını verir? (İpucu: `0b11` grubu → 2, `0b10` grubu → 1.)

**2** – `popcount(x) == 1` (tam bir bit, yani 2'nin kuvveti; Ders 5.7) ile `x && !(x & (x-1))` aynı testi mi yapıyor? Hangisi daha okunur, hangisi 0 için doğru davranır?

**3** – İki sayının kaç bitte **farklı** olduğunu (Hamming mesafesi) veren `int hamming(uint32_t a, uint32_t b)` yaz. (İpucu: Ders 5.1'deki XOR farkı bulur, sonra popcount.)

**4** – `parity`'yi Kernighan tarzı yaz: `x & (x-1)` döngüsüyle 1'leri say, sonucun son bitini al. Kaç adım döner? XOR katlama sürümü kaç adım? Hangisi dalsız?

**5** – SWAR popcount'un son adımı `(x * 0x01010101) >> 24`. Bu çarpma neden dört byte'ı toplar? `0x01010101` ile çarpmak, `x`'in dört byte'ının her birini bir pozisyona kaydırıp toplamak demek — elle `b0 + b1 + b2 + b3`'ü kaydırmalarla yazıp çarpmayla aynı olduğunu göster. (Ders 5.13'e köprü.)

<details>
<summary>Cevaplar</summary>

**1** – `x = 0b1110`. `x >> 1 = 0b0111`, `& 0x5 (0b0101) = 0b0101`. `x - 0b0101 = 0b1110 - 0b0101 = 0b1001`. Gruplara bakalım (sağdan 2'şer): `x`'in grupları `11`, `10`; sonuç `10`, `01` yani 2 ve 1. `11` grubunda 2 bir var → sonuç `10` (2); `10` grubunda 1 bir → `01` (1). Doğru. Formül her 2-bitlik grup için `üst + alt`'ı hesaplıyor: bir 2-bitlik sayıda 1 sayısı = `bit1 + bit0`, ve `x - (x>>1 & 0x55)` tam bunu her grup için paralel yapıyor.

**2** – İkisi de 2'nin kuvveti (tam bir bit) testi. `popcount(x) == 1` daha **okunur** (niyeti açık: "tam bir bit"). `x && !(x & (x-1))` daha eski/düşük seviye. 0 için: `popcount(0) == 1` → `0 == 1` → yanlış (doğru, 0 kuvvet değil); `0 && ...` → yanlış (doğru). İkisi de 0'ı doğru reddediyor. `popcount == 1` okunurluğu için tercih edilir, ve `__builtin_popcount` donanım komutuysa aynı hızda.

**3** –

```c
int hamming(uint32_t a, uint32_t b) {
    return __builtin_popcount(a ^ b);
}
```

`a ^ b`, `a` ve `b`'nin **farklı** olduğu bitlerde 1 (Ders 5.1: XOR farkı bulur). Onların sayısı, kaç bitte farklı olduklarıdır — Hamming mesafesi. Hata düzeltme kodlarının (Ders 5.19) ve benzerlik ölçümlerinin temeli. `0b1100 ^ 0b1010 = 0b0110`, popcount 2: iki bitte farklılar.

**4** –

```c
int parity_kern(uint32_t x) {
    int p = 0;
    while (x) { x &= x - 1; p ^= 1; }
    return p;
}
```

Kernighan tarzı **1 sayısı kadar** adım döner (`0xFFFFFFFF` için 32, `0x1` için 1). XOR katlama **her zaman 5 adım** (sabit). Katlama **dalsız**; Kernighan döngülü (dallı). Parite için XOR katlama hem sabit hem dalsız olduğu için tercih edilir; ama `__builtin_parity` en iyisi.

**5** – `x = b3 b2 b1 b0` (dört byte, her biri o byte'taki 1 sayısı, 0-8). `x * 0x01010101`:

`0x01010101 = (1<<24) + (1<<16) + (1<<8) + 1`, yani çarpım `x<<24 + x<<16 + x<<8 + x`. En üst byte'a (bit 24-31) bakarsak, oraya `b3 + b2 + b1 + b0` toplamı düşer (her kaydırma bir byte'ı üst byte'a hizalar; alt byte'lardan taşma olmaz çünkü her `bi <= 8`, toplam <= 32, tek byte'a sığar). `>> 24` o toplamı en alta indirir. Elle: `(x>>24) + (x>>16 & 0xFF) + (x>>8 & 0xFF) + (x & 0xFF)` da aynı toplamı verir — çarpma, bu dört kaydırma-toplamayı tek işlemde yapıyor. Çarpmanın "kaydır ve topla" doğası (Ders 5.13) burada bir sayma hilesine dönüşüyor.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §5.1: popcount'un bütün yöntemleri, SWAR türetimi.
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: "sideways addition" (popcount).
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), Alıştırma 2-9.
- C23 `<stdbit.h>`: `stdc_count_ones`. GCC/Clang: `__builtin_popcount`, `__builtin_parity`.

**Sıradaki ders:** Baştaki ve sondaki sıfırlar. `nlz`, `ntz`, ikili arama ve de Bruijn dizisiyle; `lzcnt`/`tzcnt`.
