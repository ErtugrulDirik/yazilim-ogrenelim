---
title: "5.9 Baştaki ve sondaki sıfırlar"
description: "En soldaki ve en sağdaki 1'in yerini bulmak: sondaki sıfırları (ntz) naif döngüyle, x & -x ile izole edip popcount ile, ve de Bruijn dizisiyle sabit zamanda bir tablo bakışına indirmek; baştaki sıfırları (nlz) ikili aramayla; donanımın clz/ctz komutları ve __builtin_clz/ctz; nlz ile floor(log2 x) bağlantısı."
---

Ders 5.3'te en sağdaki 1'i izole etmeyi (`x & -x`), Ders 5.8'de 1'leri saymayı öğrendik. Bu derste 1'lerin **yerini** buluyoruz: en sağdaki 1 kaçıncı bitte (sondaki sıfırların sayısı, **ntz** = number of trailing zeros), ve en soldaki 1 kaçıncı bitte (baştaki sıfırların sayısı, **nlz** = number of leading zeros). Bu iki işlem, bir sayının `log₂`'sini bulmaktan (Ders 5.15) bellek ayırıcılara, öncelik kuyruklarına kadar her yerde. İşaretsiz (`unsigned`) sayılarla.

---

## 1. Sondaki sıfırlar (ntz): naif

En sağdaki 1'e kadar kaç tane 0 var?

```c
int ntz_naive(uint32_t x) {
    if (x == 0) return 32;
    int n = 0;
    while ((x & 1) == 0) {
        n++;
        x >>= 1;
    }
    return n;
}
```

`x == 0` özel durum: hiç 1 yok, 32 (ya da tanımsız kabul edilebilir — birazdan). Döngü en sağdaki 1 gelene kadar sağa kaydırıyor. `ntz(8) = 3` (`1000`'de üç sıfır), `ntz(0x80000000) = 31`. Basit ama en kötü durumda 31 adım.

---

## 2. İzole et ve say

Ders 5.3'ten: `x & -x` en sağdaki 1'i izole eder (tek bitli bir sayı). O bit `k`. konumdaysa, değeri `2^k`, ve `2^k - 1` tam `k` tane 1'den oluşur. Öyleyse:

```c
int ntz_isolate(uint32_t x) {
    if (x == 0) return 32;
    return __builtin_popcount((x & -x) - 1);
}
```

`x & -x` en sağdaki 1'i izole eder (örneğin `0x8` → `0x8`), `- 1` onu tam `k` tane 1'e çevirir (`0x8 - 1 = 0x7`, üç bit), `popcount` (Ders 5.8) o 1'leri sayar: `k`, yani sondaki sıfır sayısı. Ders 5.3 ve 5.8'i birleştiren zarif bir çözüm, ve popcount donanım komutuysa (Ders 5.8) hızlı.

---

## 3. de Bruijn: tek çarpma, tek tablo bakışı

En şık yöntem, sondaki sıfırları **tek bir çarpma ve bir tablo bakışıyla**, dalsız ve döngüsüz bulan **de Bruijn dizisi** numarası:

```c
static const int tbl[32] = {
    0, 1, 28, 2, 29, 14, 24, 3, 30, 22, 20, 15, 25, 17, 4, 8,
    31, 27, 13, 23, 21, 19, 16, 7, 26, 12, 18, 6, 11, 5, 10, 9
};
int ntz_debruijn(uint32_t x) {
    if (x == 0) return 32;
    return tbl[((uint32_t)((x & -x) * 0x077CB531u)) >> 27];
}
```

Fikir şu: `x & -x` en sağdaki 1'i izole eder, sonuç 32 olası değerden biri (`1, 2, 4, …, 2³¹`). Bunu sihirli bir sabitle (`0x077CB531`, bir **de Bruijn dizisi**) çarpıp en üst 5 biti (`>> 27`) alırsak, her `2^k` için **farklı** bir 0-31 arası indeks çıkar. Tablo o indeksi `k`'ya çeviriyor.

Neden işe yarıyor: bir de Bruijn dizisi, 5 bitlik bütün 32 deseni tam bir kez içeren özel bir bit dizisi. `2^k` ile çarpmak onu `k` kadar kaydırmak demek; en üst 5 bit her `k` için ayrı bir desen verir, ve tablo bu desenleri `k`'ya eşler. Tek çarpma + tek kaydırma + tek tablo bakışı — **sabit zaman**, dallanma yok. Donanımda `ctz` komutu olmayan işlemcilerde (ya da eski derleyicilerde) bu yöntem standarttı.

Üç yöntem de aynı cevabı veriyor:

```
0x00000008 ntz(naive=3 isolate=3 debruijn=3 builtin=3)
0x12340000 ntz(naive=18 isolate=18 debruijn=18 builtin=18)
0x80000000 ntz(naive=31 isolate=31 debruijn=31 builtin=31)
```

---

## 4. Baştaki sıfırlar (nlz): ikili arama

En soldaki 1'e kadar kaç 0 var? Naif yöntem 1'i sola kaydırarak arar; ama **ikili arama** daha hızlı: "üst yarı boş mu?" diye yarı yarıya daraltarak.

```c
int nlz_binary(uint32_t x) {
    if (x == 0) return 32;
    int n = 0;
    if (x <= 0x0000FFFF) { n += 16; x <<= 16; }   // ust 16 bit bos mu?
    if (x <= 0x00FFFFFF) { n += 8;  x <<= 8; }
    if (x <= 0x0FFFFFFF) { n += 4;  x <<= 4; }
    if (x <= 0x3FFFFFFF) { n += 2;  x <<= 2; }
    if (x <= 0x7FFFFFFF) { n += 1; }
    return n;
}
```

Her adım, en soldaki 1'in hangi yarıda olduğunu belirleyip o yarıya odaklanıyor: "üst 16 bit boşsa (`x <= 0xFFFF`), 16 sıfır var, `x`'i 16 sola kaydır". Sonra 8, 4, 2, 1 — ikili arama (Ders 2'deki gibi), 32 biti **5 adımda** (`log₂ 32`) tarıyor. `nlz(1) = 31` (en sağda tek bit, üstte 31 sıfır), `nlz(0x80000000) = 0`.

```
0x00000001 nlz=31    0x80000000 nlz=0    0x12340000 nlz=3    0x000000FF nlz=24
```

---

## 5. Donanım: clz ve ctz

İkisi de o kadar önemli ki donanımda komut: **clz** (count leading zeros = nlz) ve **ctz** (count trailing zeros = ntz). ARM'da `clz`/`rbit`+`clz`, x86'da `lzcnt`/`tzcnt`. Derleyici builtin'leri:

```c
__builtin_clz(x)    // nlz (baştaki sifirlar)
__builtin_ctz(x)    // ntz (sondaki sifirlar)
```

**Önemli uyarı:** bu builtin'ler `x == 0` için **tanımsız** (bazı donanımlarda sonuç çöp). 0'ı kendin kontrol etmelisin; bu yüzden yukarıdaki kodda hep `if (x == 0)` var. C23 bunu düzeltti: `<stdbit.h>`'teki `stdc_leading_zeros` ve `stdc_trailing_zeros` 0 için tanımlı (32 döner).

Yazdığımız bütün yöntemler (naif, izole, de Bruijn, ikili arama), hedef işlemcide bu komut varsa derleyicinin ürettiği şey. Biz onları nasıl çalıştıklarını anlamak için yazıyoruz.

---

## 6. nlz ile log₂

nlz'nin en sık kullanımı: bir sayının **tam sayı log₂**'si. `floor(log₂ x)`, en soldaki 1'in konumu — çünkü `x`, `2^k <= x < 2^(k+1)` ise `log₂ x` `k` ile `k+1` arasında, tabanı `k`:

```c
int floor_log2(uint32_t x) {      // x > 0
    return 31 - nlz_binary(x);
}
```

```
floor(log2(1000)) = 9     (2^9 = 512 <= 1000 < 1024 = 2^10)
```

En soldaki 1 `k`. bitteyse, üstünde `31 - k` sıfır var (`nlz`), yani `k = 31 - nlz`. Bu, Ders 5.7'deki "bir sonraki 2'nin kuvvetine yuvarlama"nın bir alternatifi (`1 << (floor_log2(x-1) + 1)`), ve Ders 5.15'te tam sayı log fonksiyonlarını yazarken temel. Bir sayının kaç bit yer kapladığını (bit uzunluğu) bulmak da `32 - nlz(x)`.

---

## Alıştırmalar

**1** – `ntz` ve `nlz`'yi `x = 0x00FF0000` için elle bul. Toplamları + popcount(x) kaç eder, ve neden 32? (İpucu: baştaki sıfırlar + 1'ler bölgesi + sondaki sıfırlar = 32... hep mi?)

**2** – `ntz_isolate`'te `(x & -x) - 1`'in neden tam `ntz` tane 1 verdiğini `x = 0x12340000` için göster (`x & -x` kaç, `- 1` kaç bit?).

**3** – `nlz` ile bir sayının **bit uzunluğunu** (en soldaki 1 dahil kaç bit) veren `bit_length(uint32_t x)` yaz. `bit_length(1) = 1`, `bit_length(255) = 8`, `bit_length(256) = 9`, `bit_length(0) = 0`. Bu Ders 3.16'daki `itoa`'da bir sayının kaç basamak olacağını tahmin etmekle nasıl ilişkili?

**4** – `__builtin_ctz(0)` neden tanımsız, ve bu neden tehlikeli? Bir döngüde `while (x) { int i = __builtin_ctz(x); ...; x &= x - 1; }` yazarsan 0 sorunu çıkar mı? (İpucu: döngü koşulu.)

**5** – de Bruijn tablosunu kendin **üret**: `0x077CB531`'i `0`'dan `31`'e kadar her `k` için `(0x077CB531u << k) >> 27` hesaplayıp, çıkan indeksi `k`'ya eşleyen tabloyu kur. Yukarıdaki `tbl` ile aynı mı çıkıyor? (Bu, sihirli sabitin neden işe yaradığını gösterir.)

<details>
<summary>Cevaplar</summary>

**1** – `x = 0x00FF0000` = `00000000 11111111 00000000 00000000`. `nlz` = 8 (baştaki sekiz 0), `ntz` = 16 (sondaki on altı 0), `popcount` = 8 (ortadaki sekiz 1). Toplam: 8 + 8 + 16 = 32. Bu **her zaman** 32 olur **ancak** 1'ler **bitişikse** (tek bir blok); `nlz + popcount + ntz = 32` sadece 1'lerin arasında 0 yoksa geçerli. `0x01010101` gibi dağınık 1'lerde ortadaki 0'lar ne nlz'ye ne ntz'ye girer, toplam 32'yi tutmaz. Bitişik tek blok için tutar.

**2** – `x = 0x12340000`. `x & -x`: en sağdaki 1'i izole eder. `0x12340000`'in en sağdaki 1'i bit 18'de (`0x40000` = `2^18`). `x & -x = 0x40000`. `0x40000 - 1 = 0x3FFFF` = 18 tane 1 (bit 0-17). `popcount(0x3FFFF) = 18 = ntz`. İzole edilen bit `2^18` olduğu için, bir eksiği tam 18 bitlik bir 1 bloğu; onları saymak sondaki sıfır sayısını verir.

**3** –

```c
int bit_length(uint32_t x) {
    return x == 0 ? 0 : 32 - nlz_binary(x);
}
```

`32 - nlz` = en soldaki 1'in konumu + 1 = bit uzunluğu. `bit_length(255) = 32 - 24 = 8`, `bit_length(256) = 32 - 23 = 9`, `bit_length(0) = 0`. Ders 3.16'daki `itoa` ile ilişki: bir sayının ikilik basamak sayısı tam `bit_length`; onluk basamak sayısı ise yaklaşık `bit_length / log₂(10) ≈ bit_length × 0.301` (Ders 5.15'te tam sayı log₁₀). `itoa` tamponu ayırırken bu, en fazla kaç basamak gerekeceğini önceden bilmeye yarar.

**4** – `__builtin_ctz(0)` tanımsız çünkü "en sağdaki 1" diye bir şey yok (hiç 1 yok); donanım komutu (`tzcnt`/`rbit+clz`) 0 girdisinde çöp ya da 32 döndürebilir, garanti yok. Tehlikeli, çünkü `ctz(0)` sessizce yanlış bir indeks verir ve program fark etmeden yanlış bite dokunur. `while (x) { int i = __builtin_ctz(x); ...; x &= x - 1; }` kalıbında **sorun çıkmaz**: döngü koşulu `while (x)`, yani `x` 0 olduğunda döngüye hiç girilmez, `ctz` asla 0 ile çağrılmaz. Bu, "set bitlerin üzerinde gezinme"nin güvenli standart kalıbı (Ders 5.3'teki `x &= x-1` ile birlikte); her 1'in konumunu sırayla verir.

**5** –

```c
int gen[32];
for (int k = 0; k < 32; k++) {
    gen[((0x077CB531u << k) >> 27)] = k;
}
```

Her `k` için `(0x077CB531 << k) >> 27` (en üst 5 bit) **farklı** bir 0-31 indeksi verir (de Bruijn dizisinin özelliği: 5-bitlik pencereler hep farklı), ve o indekse `k`'yı yazarız. Çıkan `gen` tablosu, metindeki `tbl` ile **aynı**. Bu, sihrin sırrı: sabit, 32 olası `2^k`'yı 32 ayrı tablo konumuna dağıtacak şekilde seçilmiş; çarpma `<< k`'yı, `>> 27` pencereyi yapıyor, tablo ters çeviriyor. Kendi de Bruijn sabitini üretmek bir arama problemi (Knuth §7.1.3).

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §5.3 (nlz), §5.4 (ntz), de Bruijn yöntemi.
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: de Bruijn dizileri ve bit tarama.
- Leiserson, Prokop & Randall, "Using de Bruijn Sequences to Index a 1 in a Computer Word" (1998).
- C23 `<stdbit.h>`: `stdc_leading_zeros`, `stdc_trailing_zeros`. GCC/Clang: `__builtin_clz`, `__builtin_ctz`.

**Sıradaki ders:** Word-at-a-time. İlk sıfır byte'ı bulma formülü ve Faz 4'teki `strlen`'i word word okuyarak hızlandırma.
