---
title: "2.9 Sayı teorisi fonksiyonları"
description: "EBOB, EKOK, asal testi ve hızlı üs alma; aynı sonucu veren yöntemlerin adım sayılarını ölçüp karşılaştırmak."
---

Bu derste sayılarla ilgili dört klasik fonksiyon yazacağız: EBOB, EKOK, asal testi ve üs alma. Hepsini daha önce bir yerde gördün. Bu dersin asıl konusu ise fonksiyonların kendisi değil, şu soru: **aynı doğru sonucu veren iki yöntem arasında ne fark var?**

Her fonksiyonun hem "akla ilk gelen" halini hem de akıllıca halini yazacağız. Sonra ikisinin kaç adımda bittiğini **ölçeceğiz**. Bunun için fonksiyonlara bir sayaç ekledik: döngünün ya da çarpmanın her tekrarında bir artıyor. Tablolardaki bütün sayılar bu ölçümlerden geliyor.

---

## 1. EBOB: en büyük ortak bölen

**Akla ilk gelen yol:** İki sayının küçüğünden başlayıp aşağı doğru say; ikisini de bölen ilk sayı EBOB'dur.

```c
int gcd_naive(int a, int b) {
    int d = a < b ? a : b;
    while (a % d != 0 || b % d != 0) {
        d--;
    }
    return d;
}
```

(`a < b ? a : b`, Ders 2.3'teki kısa `if-else`: "`a` küçükse `a`, değilse `b`".)

**Öklid algoritması:** Ders 1.3'te kağıtta çalıştırdığın algoritma. EBOB(a, b) = EBOB(b, a mod b) olduğunu, b sıfır olunca da cevabın a olduğunu görmüştük.

```c
int gcd(int a, int b) {
    while (b != 0) {
        int r = a % b;
        a = b;
        b = r;
    }
    return a;
}
```

Ders 2.8'deki recursion ile, matematiksel tanımın kelimesi kelimesine çevirisi olarak da yazılabilir:

```c
int gcd_recursive(int a, int b) {
    if (b == 0) {
        return a;
    }
    return gcd_recursive(b, a % b);
}
```

**Ölçüm:**

| a | b | EBOB | Deneme (adım) | Öklid (adım) |
| --- | --- | --- | --- | --- |
| 48 | 18 | 6 | 13 | 3 |
| 1071 | 462 | 21 | 442 | 3 |
| 1.000.000 | 999.999 | 1 | 999.999 | 2 |
| 832.040 | 514.229 | 1 | 514.229 | 28 |

Deneme yöntemi sayılar büyüdükçe sayılarla birlikte büyüyor; bir milyonluk sayılarda bir milyon adım. Öklid ise birkaç adımda bitiyor.

Son satıra dikkat: 832.040 ve 514.229 ardışık iki **Fibonacci** sayısı. Öklid algoritmasının en yavaş çalıştığı durum tam olarak budur, çünkü her adımda bölüm 1 çıkar ve sayılar olabildiğince yavaş küçülür. Bu 19. yüzyılda Gabriel Lamé tarafından ispatlandı. Ama en kötü durumda bile 28 adım! Öklid'in adım sayısı sayının kendisiyle değil, **basamak sayısıyla** orantılı büyür.

---

## 2. EKOK: en küçük ortak kat

İki sayının **en küçük ortak katı**, ikisine de tam bölünen en küçük pozitif sayıdır. Örnek: bir otobüs 12 dakikada bir, öbürü 18 dakikada bir kalkıyor. İkisi aynı anda kalktıktan sonra tekrar ne zaman birlikte kalkarlar? EKOK(12, 18) = 36 dakika sonra.

EBOB'u bilince EKOK bedava gelir:

**a × b = EBOB(a, b) × EKOK(a, b)**

Neden? a ve b'nin ortak çarpanları EBOB'da toplanır. a × b'de bu ortak çarpanlar iki kez sayılır; EBOB'a bölünce bir kez sayılmış olur, geriye ikisinin de katı olan en küçük sayı kalır.

```c
int lcm(int a, int b) {
    return a / gcd(a, b) * b;
}
```

EKOK(12, 18) = 12 / 6 × 18 = 36.

**Neden `a * b / gcd(a, b)` değil de `a / gcd(a, b) * b`?** Matematikte ikisi aynı. Ama bilgisayarda `a * b` ara sonucu, sonuç sığsa bile `int`'e sığmayabilir. Ders 2.8'deki 13! overflow'unu hatırla. Önce bölmek ara sonucu küçük tutar. Ayrıca `a`, EBOB'a her zaman tam bölündüğü için bölmede küsurat da kaybolmaz.

---

## 3. Asal testi

Ders 1.3'te, Ders 2.3'te ve Ders 2.5'te asal sayı testini gördün. Şimdi üç sürümünü yan yana koyup ölçelim:

1. **Deneme:** 2'den `n - 1`'e kadar her sayıyı dene.
2. **Kareköke kadar:** `d * d <= n` olduğu sürece dene (Ders 1.3'te neden yeterli olduğunu gördük).
3. **Kareköke kadar, sadece tek sayılar:** 2'yi ayrıca kontrol et; 2'ye bölünmeyen bir sayı 4'e, 6'ya, 8'e de bölünmez. Sadece 3, 5, 7, 9, … dene.

```c
int is_prime(int n) {
    if (n < 2) {
        return 0;
    }
    if (n % 2 == 0) {
        return n == 2;
    }
    for (int d = 3; d * d <= n; d += 2) {
        if (n % d == 0) {
            return 0;
        }
    }
    return 1;
}
```

`return n == 2;`: Çift bir sayı sadece 2 ise asaldır. Karşılaştırmanın sonucu doğruysa 1, yanlışsa 0 döner.

**Ölçüm (kaç bölme yapıldı):**

| `n` | Asal mı? | Deneme | Kareköke kadar | Sadece tekler |
| --- | --- | --- | --- | --- |
| 97 | evet | 95 | 8 | 4 |
| 1.009 | evet | 1.007 | 30 | 15 |
| 999.983 | evet | 999.981 | 998 | 499 |
| 1.000.001 | hayır (101 × 9.901) | 100 | 100 | 50 |

Kareköke kadar aramak, büyük sayılarda **binlerce kat** fark yaratıyor: 999.983 için yaklaşık bir milyon bölme yerine bin. Sadece tek sayıları denemek bunu bir kez daha yarıya indiriyor. İlk iyileştirme problemin **yapısını** anlamaktan geliyor; ikincisi küçük ama bedava bir ek kazanç.

Son satıra bak: asal olmayan bir sayıda üç yöntem de ilk böleni (101) bulduğu anda duruyor. Fark, sayı asal olduğunda ortaya çıkıyor; çünkü o zaman bütün adayları tek tek denemek zorundasın.

---

## 4. Hızlı üs alma

3¹³'ü hesaplamanın akla gelen yolu 3'ü kendisiyle 13 kez çarpmak:

```c
int power_naive(int base, int exp) {
    int result = 1;
    for (int i = 0; i < exp; i++) {
        result *= base;
    }
    return result;
}
```

Daha akıllı bir yol var. Şuna dikkat et:

- 3¹² = (3⁶)²: 3⁶'yı bulup kendisiyle çarpmak yeterli.
- 3¹³ = (3⁶)² × 3: üs tekse, fazladan bir kez taban ile çarp.

Yani üssü her adımda **yarıya** indirebiliriz. Bu tam bir recursion (Ders 2.8): problemi kendisinin yarı büyüklüğündeki haline indirgiyoruz. Base case: her sayının 0. kuvveti 1'dir.

```c
int power(int base, int exp) {
    if (exp == 0) {
        return 1;
    }
    int half = power(base, exp / 2);
    int result = half * half;
    if (exp % 2 == 1) {
        result *= base;
    }
    return result;
}
```

Bu yönteme **kare al–çarp** (square-and-multiply) denir. `half`'i bir kez hesaplayıp kendisiyle çarptığımıza dikkat et; `power(base, exp / 2) * power(base, exp / 2)` yazsaydık her şeyi iki kez hesaplardık. Ders 2.8'deki Fibonacci'nin düştüğü tuzak.

**İz: `power(3, 13)`.** İniş 13 → 6 → 3 → 1 → 0. Çıkarken:

| `exp` | `half` | `half * half` | Tek mi? | Sonuç |
| --- | --- | --- | --- | --- |
| 0 | — | — | — | 1 |
| 1 | 1 | 1 | evet, × 3 | 3 |
| 3 | 3 | 9 | evet, × 3 | 27 |
| 6 | 27 | 729 | hayır | 729 |
| 13 | 729 | 531.441 | evet, × 3 | **1.594.323** |

Faz 0'dan bir bağlantı: 13'ün ikilik gösterimi **1101**. Tablodaki "evet, × 3" ve "hayır" sütununu aşağıdan yukarı oku: evet, hayır, evet, evet → 1, 0, 1, 1. Bu, 13'ün bitlerinin sağdan sola sırası. Hızlı üs alma, aslında üssün bitleri üzerinde yürüyor.

**Ölçüm (kaç çarpma yapıldı):**

| Üs | Düz çarpma | Kare al–çarp |
| --- | --- | --- |
| 10 | 10 | 6 |
| 13 | 13 | 7 |
| 30 | 30 | 9 |
| 1.000 | 1.000 | 16 |

Üs 1.000 olunca bin çarpma yerine 16. Üssü her adımda yarıya indirdiğimiz için adım sayısı, üssün **bit sayısıyla** orantılı. Ders 1.1'deki tahmin oyununu hatırla: 1.000.000'a kadar bir sayıyı 20 soruda buluyorduk, çünkü her soru ihtimalleri yarıya indiriyordu. Aynı fikir.

(Üs 1.000 olunca sonuç tabii ki `int`'e sığmaz; sayaçları tabanı 1 alarak ölçtük. Asıl kullanım yerini Alıştırma 3'te göreceksin.)

---

## 5. Ne öğrendik?

Bu dersteki dört örneğin hepsinde aynı şey oldu: **doğru** çalışan iki yöntemden biri, sayı büyüdükçe diğerinden binlerce, milyonlarca kat daha hızlı hale geldi. Fark bilgisayarın hızında değil, **yöntemde**.

| | Yavaş yöntem neyle büyüyor? | Hızlı yöntem neyle büyüyor? |
| --- | --- | --- |
| EBOB | Sayının kendisiyle | Sayının basamak sayısıyla |
| Asal testi | Sayının kendisiyle | Sayının kareköküyle |
| Üs alma | Üssün kendisiyle | Üssün bit sayısıyla |

Bir yöntemin girdisi büyüdükçe ne kadar yavaşladığını incelemeye **algoritma analizi** denir. Faz 9'da bunu matematiksel bir dille (O(n), O(log n), …) ayrıntısıyla göreceğiz. Bu dersten akılda kalması gereken: **doğru çalışması bir yöntemin iyi olduğu anlamına gelmez; önemli olan girdi büyüyünce ne olduğu.**

---

## Alıştırmalar

**1. 1'den 10'a kadar EKOK.** 1, 2, …, 10 sayılarının hepsine tam bölünen en küçük sayıyı bul. (İpucu: EKOK(a, b, c) = EKOK(EKOK(a, b), c).) Beklenen: 2520.

**2. Aralarında asal.** EBOB'ları 1 olan iki sayıya **aralarında asal** denir (Ders 1.3). 1 ile 30 arasında, 30 ile aralarında asal olan sayıları yazdır ve kaç tane olduklarını say.

**3. Son basamak.** 7²²²'nin son basamağı nedir? Bu sayı yaklaşık 190 basamaklı; `int`'e sığması imkânsız. Ama son basamak, sayının 10'a bölümünden kalandır. Ve kalanın şu güzel özelliği var: **(a × b) mod m = ((a mod m) × (b mod m)) mod m**. Yani her çarpmadan sonra `% 10` alırsan sayılar hiçbir zaman büyümez. `power` fonksiyonunu bu fikirle `int mod_power(int base, int exp, int mod)` haline getir.

**4. Mükemmel sayılar, hızlı.** Ders 2.5'teki mükemmel sayı programı, bölenleri bulmak için 1'den `n - 1`'e kadar her sayıyı deniyordu; 10.000'e kadar toplam yaklaşık 50 milyon deneme. Bölenleri **kareköke kadar** arayarak hızlandır. (İpucu: `d`, `n`'nin böleniyse `n / d` de bir bölendir. 28 için: 2 bulunca 14'ü, 4 bulunca 7'yi de bulmuş olursun.)

<details>
<summary>Cevaplar</summary>

**1.**
```c
int result = 1;
for (int i = 1; i <= 10; i++) {
    result = lcm(result, i);
}
printf("EKOK(1..10) = %d\n", result);
```
Her adımda o ana kadarki EKOK'u bir sonraki sayıyla birleştiriyoruz: 1, 2, 6, 12, 60, 60, 420, 840, 2520, 2520.

**2.**
```c
int count = 0;
for (int i = 1; i <= 30; i++) {
    if (gcd(i, 30) == 1) {
        printf("%d ", i);
        count++;
    }
}
printf("-> %d\n", count);
```
```
1 7 11 13 17 19 23 29 -> 8
```
30 = 2 × 3 × 5. 2'ye, 3'e ya da 5'e bölünen hiçbir sayı 30 ile aralarında asal olamaz. Bu sayımın matematikte bir adı var (Euler'in φ fonksiyonu); Faz 6'da göreceğiz.

**3.**
```c
int mod_power(int base, int exp, int mod) {
    if (exp == 0) {
        return 1 % mod;
    }
    int half = mod_power(base, exp / 2, mod);
    int result = half * half % mod;
    if (exp % 2 == 1) {
        result = result * (base % mod) % mod;
    }
    return result;
}
```
`mod_power(7, 222, 10)` → **9**. Her ara sonuç 0 ile 9 arasında kaldığı için hiçbir çarpma taşmıyor. `1 % mod`: `mod` 1 ise her sayının kalanı 0'dır; bu küçük edge case'i de doğru ele alıyor.

Bu fonksiyon, internette her gün kullandığın şifrelemenin (RSA) kalbinde duruyor: orada üsler ve modüller yüzlerce basamaklı sayılardır ve kare al–çarp olmadan hesaplanmaları imkânsız olurdu. Faz 6'da tekrar karşılaşacağız.

**4.**
```c
int divisor_sum(int n) {
    if (n == 1) {
        return 0;
    }
    int sum = 1;
    for (int d = 2; d * d <= n; d++) {
        if (n % d == 0) {
            sum += d;
            if (d != n / d) {
                sum += n / d;
            }
        }
    }
    return sum;
}
```
1 her sayının bölenidir, bu yüzden `sum` 1'den başlıyor. `d != n / d` kontrolü tam kareler için: 36'da 6 bulunduğunda `n / d` de 6'dır; onu iki kez eklememeliyiz. Bu sürüm 10.000'e kadar toplam **651.750** deneme yapıyor; eskisinin yaklaşık 50 milyonuna karşı **70 kattan fazla** daha az.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 2 (3. baskı), §4.5.2–4.5.3: EBOB, Öklid algoritmasının analizi ve Lamé teoremi; §4.6.3: üs alma.
- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), Bölüm 4: sayı teorisi.

**Sıradaki ders:** Tamsayı karekök. Karekökü sadece tamsayılarla bulmanın üç yolu: tek tek denemek, binary search ve Newton yöntemi.
