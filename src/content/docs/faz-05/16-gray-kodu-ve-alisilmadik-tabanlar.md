---
title: "5.16 Gray kodu ve alışılmadık tabanlar"
description: "Ardışık değerleri tam bir bit farkla kodlayan Gray kodu: ikilikten Gray'e x ^ (x>>1), geri dönüşü XOR katlamayla (Ders 5.8'deki parite deseni), neden ardışık kodların tek bit farklı olduğu ve dönme enkoderlerindeki kullanımı; ve negatif sayıları işaret biti olmadan temsil eden taban −2 (negabinary), hem bölme-kalan algoritmasıyla hem Schroeppel'in (n + 0xAAAAAAAA) ^ 0xAAAAAAAA bit hilesiyle."
---

Bu derste bitleri **alışılmadık** biçimlerde yorumluyoruz: önce **Gray kodu**, ardışık sayıları tam bir bit farkla kodlayan bir düzen; sonra **taban −2** (negabinary), negatif sayıları işaret biti olmadan temsil eden bir sayı sistemi. İkisi de "ikilik tek doğru yorum değil" fikrini gösteriyor — aynı bitler farklı kurallarla farklı sayıları ifade edebilir.

İşaretsiz (`unsigned`) bit desenleriyle, ama taban −2'de işaretli değerler temsil edeceğiz.

---

## 1. Gray kodu: tek bitlik adımlar

Sıradan ikilikte ardışık sayılar birden çok bitte farklı olabilir: `3 = 011`, `4 = 100` — üç bit birden değişti. **Gray kodu**, sayıları öyle bir sıraya dizer ki **ardışık** iki kod **tam bir bit** farklı olur:

```
n  ikilik  gray
0  000     000
1  001     001
2  010     011
3  011     010
4  100     110
5  101     111
6  110     101
7  111     100
```

`2 → 3`: Gray `011 → 010`, tek bit. `3 → 4`: `010 → 110`, tek bit. Sıradan ikilikte `3 → 4` üç bit değişirken, Gray'de hep bir bit.

İkilikten Gray'e dönüşüm şaşırtıcı derecede basit:

```c
uint32_t to_gray(uint32_t x) {
    return x ^ (x >> 1);
}
```

Her biti, bir solundaki bitle XOR'lamak. Neden tek bitlik adım sağlıyor: `n`'den `n+1`'e geçerken ikilikte en sağdaki 1 bloğu değişir (Ders 5.3'teki `x+1` davranışı); `x ^ (x>>1)` bu değişimi tek bir bite indirger. (Tam ispat Knuth §7.2.1.1'de; sezgi: komşu bitlerin XOR'u, çok bitlik taşımayı tek bite "yumuşatır".)

Geri dönüş (Gray'den ikiliğe) biraz daha çok iş — her biti, kendisinden üstteki **bütün** bitlerin XOR'u yapmak gerekiyor, ve bu Ders 5.8'deki parite katlamasının aynısı:

```c
uint32_t from_gray(uint32_t g) {
    g ^= g >> 16;
    g ^= g >> 8;
    g ^= g >> 4;
    g ^= g >> 2;
    g ^= g >> 1;
    return g;
}
```

Doğruladık: ardışık Gray kodları 16 milyon değerde hep tam 1 bit farklı, ve `from_gray(to_gray(n)) == n` her zaman.

**Nerede kullanılır:** en klasik yeri **dönme enkoderleri** ve pozisyon sensörleri. Bir milin açısını ikilik okusaydık, `011 → 100` geçişinde üç bit **aynı anda** değişmek zorunda; sensör bunları tam eşzamanlı okuyamazsa aradaki bir anda `111` ya da `000` gibi bir çöp değer görünür. Gray kodda hep tek bit değiştiği için böyle bir ara çöp değer olmaz — en kötü ihtimalle bir komşu değer okunur. Aynı sebeple Karnaugh haritalarında (Faz 6'daki Boole sadeleştirme) ve bazı hata düzeltme şemalarında kullanılır.

---

## 2. Taban −2: işaret biti olmadan negatif sayılar

İkilikte negatif sayılar için iki tümleyen (Ders 3.3) ya da bir işaret biti kullandık. Ama tabanın kendisi **negatif** olursa, negatif sayılar hiçbir özel kurala gerek kalmadan, sıradan basamaklarla temsil edilir. **Taban −2** (negabinary): basamak değerleri `1, -2, 4, -8, 16, …` yani `(-2)^k`.

```
 -3 = 1101   (-8 + 4 + 0 + 1 = -3)
 -2 = 10     (-2)
 -1 = 11     (-2 + 1 = -1)
  0 = 0
  1 = 1
  2 = 110    (4 - 2 + 0 = 2)
  3 = 111    (4 - 2 + 1 = 3)
```

Hepsi aynı 0/1 basamaklarıyla, ama konumların değeri değişerek işareti alternatifliyor. İşaret biti yok; `-1` ile `1`'in gösterimi (`11` ve `1`) farklı uzunlukta ama ikisi de sıradan basamaklar. Dönüşüm, Ders 5.13'teki bölme-kalan algoritmasının negatif bölenli hali:

```c
void negabinary(int n, char *out) {
    char tmp[40]; int k = 0;
    if (n == 0) { out[0] = '0'; out[1] = '\0'; return; }
    while (n != 0) {
        int r = n % (-2);
        n = n / (-2);
        if (r < 0) { r += 2; n += 1; }   // kalani 0/1'e duzelt
        tmp[k++] = '0' + r;
    }
    int i = 0;
    for (int j = k - 1; j >= 0; j--) out[i++] = tmp[j];
    out[i] = '\0';
}
```

Her adımda `-2`'ye bölüp kalanı alıyoruz; kalan negatif çıkarsa (C'nin `%`'si bölünenin işaretini alır, Ders 5.7) onu 0/1'e düzeltip bölüme bir ekliyoruz. −1'den 1'e kadar bütün değerleri doğru çevirip geri okuyor.

### Schroeppel'in bit hilesi

Daha da güzeli: bir iki-tümleyen tamsayıyı negabinary bit desenine çeviren tek satırlık bir **bit hilesi** var:

```c
uint32_t to_negabinary_bits(int32_t n) {
    const uint32_t MASK = 0xAAAAAAAAu;   // 1010...1010
    return (uint32_t)((n + MASK) ^ MASK);
}
```

`0xAAAAAAAA`, tek konumlardaki (negatif değerli basamaklar: `-2, -8, -32, …`) bitler. `n`'ye bu maskeyi ekleyip sonra XOR'lamak, iki-tümleyen gösterimini negabinary bit desenine çeviriyor. −1 milyon ile +1 milyon arası bütün değerlerde doğruladık: sıfır hata. Neden çalıştığı Ders 5.4'teki aritmetik–mantık özdeşliklerine dayanıyor (maskeli toplama ve XOR'un etkileşimi); türetimi Knuth §7.1.3'te. Bölme-kalan döngüsünün yaptığını tek bir toplama ve XOR'a indiriyor.

Taban −2 pratikte nadir, ama fikir önemli: **negatiflik, sayı sisteminin tabanına gömülebilir**, ayrı bir işaret biti ya da iki tümleyen gerekmez. Benzer şekilde taban −1+i (karmaşık sayılar için) ya da dengeli üçlü (balanced ternary, basamaklar −1/0/1) sistemleri vardır; hepsi "ikilik ve iki tümleyen tek yol değil" temasının çeşitleri.

---

## Alıştırmalar

**1** – `to_gray(x) = x ^ (x >> 1)` ile `n = 0..7`'nin Gray kodlarını üret ve ardışık olanların tam bir bit farklı olduğunu elle kontrol et. `7 → 0`'a dönüşte (dairesel) kaç bit farklı?

**2** – `from_gray`'in neden XOR katlama (Ders 5.8'deki parite gibi) olduğunu açıkla: Gray'in `i`. biti, ikiliğin `i`. ve üstündeki bitlerinin XOR'u mu? Bir baytlık (`uint8_t`) `from_gray8` yaz — kaç katlama adımı yeter?

**3** – Taban −2'de `10101` kaç eder? (Basamak değerleri `1, -2, 4, -8, 16`.) Taban −2'de hangi sayılar "pozitif görünümlü" (en üst basamağı pozitif konumda)?

**4** – Schroeppel hilesini (`(n + 0xAAAAAAAA) ^ 0xAAAAAAAA`) `n = 2` ve `n = -2` için elle hesapla, sonucu `eval_bits` ile (basamak değerleri `(-2)^k`) doğrula.

**5** – Gray kodunun bir uygulaması: bir sayaç her adımda tek bir bit değiştirsin istiyorsun (düşük güç tüketimi için, bit değişimi enerji harcar). `n`'i artırmak yerine Gray koduyla saymak bunu nasıl sağlar? Bir "Gray sayaç"ın bir sonraki değerini (`gray_next`) doğrudan, ikiliğe çevirmeden üretebilir misin? (İpucu: pariteye bak.)

<details>
<summary>Cevaplar</summary>

**1** – Gray kodları: 000, 001, 011, 010, 110, 111, 101, 100. Ardışık farklar: 000→001 (bit 0), 001→011 (bit 1), 011→010 (bit 0), 010→110 (bit 2), 110→111 (bit 0), 111→101 (bit 1), 101→100 (bit 0) — hepsi tek bit. `7 → 0` dairesel: `100 → 000`, tek bit (bit 2). Gray kodu **dairesel** olarak da tek bitlik: son değerden ilk değere dönüş de bir bit — bu yüzden "cyclic Gray code", dönen bir mile tam uyar.

**2** – Evet: Gray'den ikiliğe dönüşte, ikiliğin `i`. biti = Gray'in `i`. ve **üstündeki** bütün bitlerinin XOR'u. Bu bir "önek XOR'u" (prefix XOR), ve onu paralel hesaplamanın yolu Ders 5.8'deki parite katlamasının aynısı (her bit, üstündekilerin XOR'unu toplar).

```c
uint8_t from_gray8(uint8_t g) {
    g ^= g >> 4;
    g ^= g >> 2;
    g ^= g >> 1;
    return g;
}
```

8 bit için `log₂ 8 = 3` katlama adımı (`>>4, >>2, >>1`) yeter — tıpkı Ders 5.8'deki 8-bit parite ve Ders 5.11'deki 8-bit reverse gibi.

**3** – `10101` taban −2: konumlar (sağdan) `1, -2, 4, -8, 16`. Set bitler: konum 0 (`1`), konum 2 (`4`), konum 4 (`16`). Toplam `1 + 4 + 16 = 21`. "Pozitif görünümlü": en üst (en soldaki) 1 **çift** konumdaysa (pozitif basamak: `1, 4, 16, …`) sayı pozitif, **tek** konumdaysa (negatif basamak: `-2, -8, …`) negatif. `10101`'in en üst 1'i konum 4 (çift, +16), o yüzden pozitif. Taban −2'de bir sayının işaretini en üst 1'in konumunun çift/tekliği belirler — işaret biti yerine konum paritesi.

**4** – `MASK = 0xAAAAAAAA`. `n = 2`: `2 + 0xAAAAAAAA = 0xAAAAAAAC`, `^ 0xAAAAAAAA = 0x00000006` = `110`. `eval`: konum 1 (`-2`) + konum 2 (`4`) = `-2 + 4 = 2`. Doğru. `n = -2`: `-2 + 0xAAAAAAAA = 0xAAAAAAA8`, `^ 0xAAAAAAAA = 0x00000002` = `10`. `eval`: konum 1 (`-2`) = `-2`. Doğru. Hile, iki-tümleyen `n`'yi negabinary bit desenine çeviriyor, bölme döngüsü olmadan.

**5** – Gray koduyla saymak, her adımda tam bir bit değiştirir (Bölüm 1); ikilik sayaçta ise `0111 → 1000` gibi geçişler dört bit birden değiştirir, dört kez enerji harcar. Gray sayaç her artışta sadece bir bit değiştirdiği için düşük güçlü sayaçlarda ve asenkron devrelerde tercih edilir. Bir sonrakini doğrudan üretmek: Gray kodunda, çift pariteli (Ders 5.8) bir değerde en sağdaki biti çevir, tek pariteli bir değerde en sağdaki 1'in solundaki biti çevir.

```c
uint32_t gray_next(uint32_t g) {
    if (__builtin_parity(g) == 0) {
        return g ^ 1;                       // en sagdaki biti cevir
    } else {
        uint32_t lowest = g & (~g + 1);     // en sagdaki 1 (Ders 5.3: g & -g)
        return g ^ (lowest << 1);           // onun solundaki biti cevir
    }
}
```

İkiliğe hiç çevirmeden, sadece parite ve en sağdaki 1'e bakarak bir sonraki Gray değerini üretir — Ders 5.3 ve 5.8'in birleşimi.

</details>

---

## Kaynaklar

- Donald Knuth, *TAOCP* Cilt 4A, §7.2.1.1 (Gray kodu), §7.1.3 (negabinary ve bit hileleri).
- Henry Warren, *Hacker's Delight* (2. baskı), §13.1 (Gray kodu), §2.17 (taban −2).
- Frank Gray, "Pulse Code Communication" (1953 patenti): Gray kodunun kökeni.
- Ders 5.8 (parite katlaması) ve Ders 5.3 (en sağdaki bit): bu dersin araçları.

**Sıradaki ders:** Uzay doldurma eğrileri. Morton (Z-order) ve Hilbert eğrileri, cache dostu veri düzenine bağlantı.
