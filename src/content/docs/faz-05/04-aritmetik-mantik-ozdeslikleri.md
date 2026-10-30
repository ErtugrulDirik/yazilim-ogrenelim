---
title: "5.4 Aritmetik–mantık özdeşlikleri"
description: "Aritmetiği bit işlemleriyle bağlayan özdeşlikler: toplamanın elde'siz kısmı XOR, elde ise (x & y) << 1, buradan x + y = (x ^ y) + 2(x & y); iki sayının ortalamasını toplamları taşsa bile doğru veren (x & y) + ((x ^ y) >> 1) formülü; De Morgan yasalarının 32 bite genellenmesi ve x - y = x + ~y + 1."
---

Şimdiye kadar bitleri ayrı ayrı yönettik (Ders 5.2, 5.3). Bu derste bitlerle **aritmetiği** birbirine bağlıyoruz: toplama, çıkarma ve ortalama almanın bit işlemleriyle yazılan halleri. Bu özdeşlikler hem güzel (aritmetiğin neden "böyle" çalıştığını gösteriyorlar) hem de pratik: bir toplamın taşacağı yerde bile doğru ortalama almak gibi gerçek sorunları çözüyorlar.

İşaretsiz (`unsigned`) sayılarla çalışıyoruz (Ders 5.1).

---

## 1. Toplamanın iki parçası: XOR ve elde

İki biti topladığını düşün (Ders 0.2'deki ikilik toplama): `0+0=0`, `0+1=1`, `1+0=1`, `1+1=10`. İlk üçü tam XOR'un tablosu. Dördüncüde (`1+1`) sonuç biti 0, ama bir **elde** (carry) var. Yani:

- **Elde'siz toplam** (her bit kendi başına): `x ^ y`. XOR, "1+1=0" diyerek eldeyi yok sayıyor.
- **Elde**: sadece iki bitin de 1 olduğu yerde doğar (`x & y`), ve bir **sola** taşınır (bir üst basamağa): `(x & y) << 1`.

Gerçek toplam ikisinin toplamı:

$$x + y = (x \oplus y) + 2(x \mathbin{\&} y)$$

($2 \times$, bir sola kaydırma; Ders 3.18.) Ölçelim:

```c
uint32_t carryless = x ^ y;        // elde'siz
uint32_t carry = (x & y) << 1;     // elde, bir sola
carryless + carry                   // == x + y
```

```
x+y=66676  (x^y)+2(x&y)=66676
x+y=133342 (x^y)+2(x&y)=133342
```

Her zaman tutuyor. Bu, toplamanın tanımını ikiye ayırıyor: XOR "bitleri topla", AND<<1 "eldeleri taşı". Dikkat: sağ taraftaki `+` hâlâ bir toplama — özdeşlik toplamayı yok etmiyor, onu **açıklıyor**. Ama eldeyi tekrar tekrar bu formülle işlersek toplamayı tamamen bit işlemleriyle kurabiliriz; Ders 5.13'te kaydır-topla çarpmada ve bir donanımın toplayıcıyı nasıl kurduğunu anlatırken bunu kullanacağız.

---

## 2. Taşmadan ortalama almak

İki sayının ortalaması `(x + y) / 2`. Ama `x + y` **taşarsa** (Ders 3.8), bu formül yanlış cevap verir — ortalama ikisinden de küçük çıkar:

```c
uint32_t a = 0xFFFFFFF0u, b = 0xFFFFFFF0u;   // ikisi de buyuk
(a + b) / 2       // 2147483632 (YANLIS: a+b 32 bitte tasti)
```

İki büyük sayının ortalaması yine o büyüklükte olmalı (burada `0xFFFFFFF0`), ama `a + b` 33 bit gerektirdiği için 32 bitte sarıp küçük bir sayı verdi, bölünce de yanlış. Bu, gerçek bir hata kaynağı: ikili aramada `mid = (low + high) / 2` (Faz 8'de göreceğiz) tam bu yüzden büyük dizilerde yıllarca gizli kalmış ünlü bir bug'a yol açtı.

Bölüm 1'deki özdeşlik çözümü veriyor. $x + y = (x \oplus y) + 2(x \& y)$'yi 2'ye bölersek:

$$\frac{x + y}{2} = (x \mathbin{\&} y) + \frac{x \oplus y}{2}$$

Yani:

```c
uint32_t avg = (a & b) + ((a ^ b) >> 1);
```

```
bit: (a&b)+((a^b)>>1) = 4294967280   = 0xFFFFFFF0  (DOGRU)
```

Neden taşmıyor? `a & b`, iki sayının **ortak** bitleri — ikisinden de küçük ya da eşit, taşmaz. `(a ^ b) >> 1` de farkın yarısı, zaten küçük. İkisinin toplamı ortalama, ve ara adımların hiçbiri 32 biti aşmıyor. Bu formül **aşağı yuvarlar** (floor); `x` ve `y`'nin ikisi de tekse ortalama `.5` çıkar ve aşağı iner.

(Bir alternatif, `a + (b - a) / 2`: `b - a` taşmaz çünkü fark küçük. Ama `b < a` ise işaretsizde `b - a` sarar; o yüzden `a <= b` gerektirir. Bit formülü sıra gözetmez, her zaman çalışır.)

---

## 3. De Morgan: 32 bit birden

Mantıktan De Morgan yasalarını biliyoruz (Faz 1'deki akış koşulları): "ne p ne q" = "p değil ve q değil". Bit işlemlerinde aynı yasa, 32 bitin **hepsi** için aynı anda:

$$\sim(x \mathbin{\&} y) = \sim x \mathbin{|} \sim y \qquad \sim(x \mathbin{|} y) = \sim x \mathbin{\&} \sim y$$

```c
uint32_t p = 0xCC, q = 0xAA;
~(p & q)   ==  (~p) | (~q)     // ikisi de 0x...77
~(p | q)   ==  (~p) & (~q)     // ikisi de 0x...11
```

Her bit konumunda sıradan mantık De Morgan'ı geçerli; `&`, `|`, `~` 32 biti paralel işlediği için yasa 32 bite olduğu gibi taşınıyor. Pratik faydası: bir bit ifadesini sadeleştirmek ya da `&`'yi `|`'ye çevirmek (bazen bir maskeyi tersten kurmak daha kolay). Örneğin "şu bitlerin **hiçbiri** set değil" = `(x & mask) == 0` = `(~x & mask) == mask` — De Morgan'ın bir sonucu.

De Morgan'ın bir genellemesi, `&`, `|`, `^`, `~` ile kurulu **her** bit ifadesinin tersinin, operatörleri çevirip (`&`↔`|`) ve değişkenleri tümleyerek bulunabilmesidir. Ders 5.1'deki `x ^ 0xFF == ~x & 0xFF` de bu ailede: XOR ile tümlemek arasındaki bağ.

---

## 4. Çıkarma: x - y = x + ~y + 1

Ders 3.3'teki iki tümleyenden: `-y = ~y + 1`. O halde çıkarma bir toplama:

$$x - y = x + (\sim y + 1)$$

```c
uint32_t x = 100, y = 30;
x + ~y + 1    // 70, tipki x - y gibi
```

Bu neden önemli? Donanımda **ayrı bir çıkarıcı devre yok**: işlemci çıkarmayı, `y`'yi tümleyip 1 ekleyerek, aynı toplayıcıyla yapıyor. İki tümleyenin bütün amacı buydu (Ders 3.3): çıkarmayı toplamaya indirgemek. Bu özdeşlik, Ders 5.3'teki `-x = ~x + 1` ile birlikte, aritmetiğin neden bit işlemleriyle kurulabildiğinin temeli.

Bu özdeşliklerin hepsi bir aileyi gösteriyor: **aritmetik ve mantık ayrı dünyalar değil.** Toplama XOR + taşıma, çıkarma tümleme + toplama, ortalama ortak bitler + farkın yarısı. Bir sonraki derste (dalsız kod) bu bağı kullanıp `if` olmadan dallanma yapacağız.

---

## Alıştırmalar

**1** – `x = 0b1100`, `y = 0b1010` için `x ^ y`, `(x & y) << 1` ve toplamlarını hesapla. `x + y` ile aynı mı? Eldeli tek bit hangisi?

**2** – İki sayının ortalamasını **yukarı** yuvarlayan (ceil) formül: `(x | y) - ((x ^ y) >> 1)`. `x = 5, y = 8` için hem floor (`(x&y)+((x^y)>>1)`) hem ceil formülünü hesapla; gerçek ortalama 6.5, hangisi 6 hangisi 7 verir?

**3** – `x + y = (x ^ y) + 2(x & y)` özdeşliğini kullanarak, `x & y == 0` (yani hiç ortak bit yok) olduğunda `x + y == x | y == x ^ y` olduğunu göster. Bu ne zaman işe yarar? (İpucu: ayrık bitli bayrakları birleştirmek, Ders 5.2.)

**4** – De Morgan ile `(x & mask) == 0` ("mask'teki hiçbir bit set değil") ifadesini `~` kullanan eşdeğer bir ifadeye çevir. Sonra "mask'teki **bütün** bitler set" (`(x & mask) == mask`) için benzer bir dönüşüm yaz.

**5** – `x - y = x + ~y + 1` özdeşliğini `x = 50, y = 50` için doğrula (`~y + 1` kaç, `x + o` kaç?). İşaretsizde `x - y` `y > x` iken ne verir, ve bu özdeşlikle nasıl tutarlı? (İpucu: mod 2³².)

<details>
<summary>Cevaplar</summary>

**1** – `x = 1100`, `y = 1010`. `x ^ y = 0110` (elde'siz toplam), `x & y = 1000`, `(x & y) << 1 = 10000` (elde, bir sola). Toplam: `0110 + 10000 = 10110` = 22. `x + y = 12 + 10 = 22`. Aynı. Eldeli tek bit: ikisinde de 1 olan bit 3 (`1000`); o yüzden elde oradan bir üste (bit 4) taşındı.

**2** – `x = 5 = 0101`, `y = 8 = 1000`. Floor: `(x & y) + ((x ^ y) >> 1)` = `0000 + (1101 >> 1)` = `0 + 0110` = 6. Ceil: `(x | y) - ((x ^ y) >> 1)` = `1101 - 0110` = `13 - 6` = 7. Gerçek ortalama 6.5; floor **6**, ceil **7** verir. İkisi `x + y` tek olduğunda 1 farklıdır; `x + y` çiftse eşittirler.

**3** – `x & y == 0` ise özdeşlik `x + y = (x ^ y) + 2·0 = x ^ y`. Ayrıca ortak bit olmadığında `x | y` de `x ^ y`'ye eşittir (OR ile XOR sadece ortak bitlerde farklıdır, ortak bit yoksa aynı). Yani `x + y == x | y == x ^ y`. İşe yararlığı: ayrık (çakışmayan) bitli bayrakları birleştirirken `|` ile `+` aynı sonucu verir — Ders 5.2'de `PERM_READ | PERM_WRITE` ile `PERM_READ + PERM_WRITE` aynı, çünkü bayraklar farklı bitlerde. Bu yüzden bazı eski kodlar bayrakları `+` ile birleştirir (ama bir bayrak yanlışlıkla iki kez eklenirse `+` taşırır, `|` taşmaz — `|` daha güvenli).

**4** – `(x & mask) == 0` ↔ "mask bitlerinin hepsi x'te 0" ↔ `(~x & mask) == mask` (x'in tersinde mask bitlerinin hepsi 1). "Bütün bitler set" (`(x & mask) == mask`) ↔ "x'in tersinde mask bitlerinin hiçbiri set değil" ↔ `(~x & mask) == 0`. İkisi birbirinin De Morgan yansıması: "hepsi 1" ile "hiçbiri 1 değil (tersinde)" aynı şey.

**5** – `x = 50, y = 50`. `~y = ~50 = 0xFFFFFFCD`, `~y + 1 = 0xFFFFFFCE` = `(uint32_t)(-50)`. `x + (~y + 1) = 50 + 4294967246 = 4294967296` = 2³², ki 32 bitte 0'a sarar → `x - y = 0`. Doğru. `y > x` iken (örneğin `x=30, y=50`): `x - y` işaretsizde `30 - 50` = `-20` mod 2³² = `4294967276` — negatif değil, büyük bir pozitif. Özdeşlikle tutarlı: `x + ~y + 1` de aynı mod 2³² sonucunu verir. İşaretsiz çıkarma hiçbir zaman "hata" vermez, sadece mod 2³² çalışır; iki tümleyenin tutarlılığı bu.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §2.2 (toplama/çıkarma özdeşlikleri), §2.5 (ortalama).
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: Boole ve aritmetik işlemlerin birleşimi.
- Joshua Bloch, "Extra, Extra — Read All About It: Nearly All Binary Searches and Mergesorts are Broken" (2006): `(low + high) / 2` taşma hatası.
- Jörg Arndt, *Matters Computational*, Bölüm 1: bit aritmetiği özdeşlikleri.

**Sıradaki ders:** Dalsız (branchless) kod. abs, sign, min/max ve koşullu atamayı `if` olmadan yazmak, dal tahmininin neden önemli olduğu.
