---
title: "6.4 Tümevarım"
description: "Domino sezgisi, zayıf tümevarımın iki adımı (taban ve tümevarım adımı), Σi = n(n+1)/2 ve 1 + 2 + 4 + … + 2ⁿ = 2ⁿ⁺¹ − 1 kanıtları, 2ⁿ > n eşitsizliği, güçlü tümevarım ile her sayının asal çarpanlara ayrılması, Faz 1'deki döngü değişmezinin tümevarım olduğu, özyinelemenin doğruluğu ve 'bütün atlar aynı renktir' yanlış kanıtı."
---

Ders 1.3'te bir döngünün **her $n$ için** doğru olduğunu üç adımda göstermiştik: değişmez başta doğru, her tur onu koruyor, çıkışta istediğimizi veriyor. O zaman "bu bir kanıttır" dedik ama nedenini söylemedik. Ders 6.3'te de "her $n > 1$'in bir asal böleni var" iddiasını bu derse bırakmıştık.

İkisinin de arkasında aynı fikir var: **tümevarım** (mathematical induction). Doğal sayılarla ilgili sonsuz bir $\forall$'ı sonlu sayıda adımla kanıtlamanın yolu.

---

## 1. Domino

Sonsuz uzunlukta bir domino dizisi düşün. Hepsinin devrileceğinden emin olmak için iki şey yeter:

1. **İlk taş devrilir.**
2. **Herhangi bir taş devrilirse, bir sonraki de devrilir.**

Birinci taş devrilir; ikinci kurala göre ikinci de; yine ikinci kurala göre üçüncü de... Hiçbir taş ayakta kalamaz. Tümevarım, bu sezginin kesin hali:

$$
\Big(P(0) \land \forall k\, \big(P(k) \to P(k+1)\big)\Big) \to \forall n\, P(n)
$$

İki adım:

- **Taban** (base case): $P(0)$'ı kanıtla. (Bazen $P(1)$ ya da başka bir başlangıç.)
- **Tümevarım adımı** (inductive step): keyfi bir $k$ için $P(k)$'yı **varsay** ve $P(k+1)$'i kanıtla. Varsaydığımız $P(k)$'ya **tümevarım hipotezi** denir.

Dikkat: adımda $P(k)$'yı kanıtlamıyoruz, **varsayıyoruz**. Bu döngüsel değil; bir koşul kanıtlıyoruz: "$P(k)$ doğruysa $P(k+1)$ de doğru." Ders 6.3'teki doğrudan kanıt kalıbı.

---

## 2. İlk örnek: 1'den n'e toplam

**Teorem.** Her $n \ge 0$ için $0 + 1 + 2 + \dots + n = \dfrac{n(n+1)}{2}$.

**Kanıt.** $P(n)$ bu eşitlik olsun.

*Taban*: $n = 0$. Sol taraf $0$, sağ taraf $\frac{0 \cdot 1}{2} = 0$. ✓

*Adım*: $P(k)$'yı varsayalım: $1 + \dots + k = \frac{k(k+1)}{2}$. $P(k+1)$'i göstermek istiyoruz. Sol tarafın son terimini ayırıp hipotezi kullanıyoruz:

$$
\underbrace{1 + \dots + k}_{\text{hipotez}} + (k+1) = \frac{k(k+1)}{2} + (k+1) = \frac{k(k+1) + 2(k+1)}{2} = \frac{(k+1)(k+2)}{2}.
$$

Bu, $P(k+1)$'in sağ tarafı: $n = k+1$ koyunca $\frac{(k+1)(k+2)}{2}$. ✓ $\blacksquare$

Bu kanıtın kalıbı hemen her toplam kanıtında aynı: **$k+1$'inci terimi ayır, kalanına hipotezi uygula, cebirle hedef biçime getir.**

Bir uyarı: tümevarım formülü **bulmaz**, sadece doğrular. $\frac{n(n+1)}{2}$'nin nereden geldiğini başka bir yolla bulmak gerekiyor (Gauss'un hikâyesi: toplamı bir de tersten yazıp alt alta topla, $n$ tane $n+1$ çıkar). Formül bulma teknikleri Ders 6.10'un konusu.

### İkinin kuvvetleri

**Teorem.** Her $n \ge 0$ için $1 + 2 + 4 + \dots + 2^n = 2^{n+1} - 1$.

**Kanıt.** *Taban*: $n = 0$: $1 = 2^1 - 1$. ✓ *Adım*: $1 + \dots + 2^k = 2^{k+1} - 1$ varsayalım. O zaman $1 + \dots + 2^k + 2^{k+1} = 2^{k+1} - 1 + 2^{k+1} = 2 \cdot 2^{k+1} - 1 = 2^{k+2} - 1$. ✓ $\blacksquare$

Bu teoremi Faz 3'ten beri kullanıyoruz: $n+1$ bitin hepsi 1 olan sayı $2^{n+1} - 1$. `~0u` $= 2^{32} - 1$, `0xFF` $= 2^8 - 1$; Ders 4.24'teki dinamik dizinin $1 + 2 + 4 + \dots < n$ kopyalama maliyeti de bu toplamdan.

### Bir eşitsizlik

**Teorem.** Her $n \ge 0$ için $n < 2^n$.

**Kanıt.** *Taban*: $0 < 1$. ✓ *Adım*: $k < 2^k$ varsayalım. $k + 1 < 2^k + 1 \le 2^k + 2^k = 2^{k+1}$. ($1 \le 2^k$ her $k \ge 0$ için doğru.) ✓ $\blacksquare$

Bu teorem neden önemli? $n$ bitle $2^n$ farklı değer temsil edilebiliyor ve bu her zaman $n$'den büyük; $n$ elemanlı bir kümenin bütün alt kümelerini (Ders 6.5) bir `unsigned`'ın bitleriyle numaralandırabiliyoruz.

---

## 3. Güçlü tümevarım

Bazen $P(k+1)$'i kanıtlamak için sadece $P(k)$ yetmez, daha önceki değerler de lazım. **Güçlü tümevarım** (strong induction), adımda **bütün** önceki değerleri varsaymamıza izin veriyor:

$$
\Big(\forall k\, \big(P(0) \land \dots \land P(k) \to P(k+1)\big)\Big) \to \forall n\, P(n)
$$

Domino benzetmesinde: "önceki taşların **hepsi** devrildiyse bu taş da devrilir." Zayıf tümevarımla aynı güçte (biri öbürünü kanıtlar) ama kullanımı çok daha rahat.

**Teorem.** Her $n \ge 2$ tamsayısı asalların çarpımı olarak yazılabilir. (Tek asal da "bir asalın çarpımı" sayılıyor.)

**Kanıt.** *Taban*: $n = 2$ asal. ✓ *Adım*: $2, 3, \dots, k$'nın hepsinin asalların çarpımı olduğunu varsayalım; $k+1$'e bakalım. İki durum var (Ders 6.3'teki durumlara ayırma):

- $k+1$ asalsa, kendisi bir asalın çarpımı. ✓
- Asal değilse $k+1 = ab$, $2 \le a, b \le k$. Hipoteze göre $a$ ve $b$ asalların çarpımı; ikisini çarpınca $k+1$ de asalların çarpımı. ✓ $\blacksquare$

Zayıf tümevarım burada işe yaramazdı: $k+1 = ab$ olduğunda $a$ ve $b$, $k$ değil, ondan çok daha küçük sayılar. Hipotezin **hepsini** kullanmamız gerekiyor. Ders 6.3'teki Öklid kanıtının eksik parçası ("$N > 1$'in bir asal böleni var") böylece tamamlandı.

Kanıt, bir algoritmayı da anlatıyor. Kodda hali şöyle:

```c
// n >= 2 icin n'in asal carpanlarini yazar (guclu tumevarimin kod hali)
static void factor(long n) {
    for (long d = 2; d * d <= n; d++) {
        if (n % d == 0) {          // n = d * (n/d), ikisi de n'den kucuk
            factor(d);
            factor(n / d);
            return;
        }
    }
    printf("%ld ", n);             // boleni yok: n asal
}
```

```
factor(360)   -> 2 2 2 3 3 5
factor(30031) -> 59 509
factor(97)    -> 97
```

Özyinelemeli çağrıların ikisi de daha küçük sayılarla yapılıyor; kanıttaki "hipotezi $a$ ve $b$'ye uygula" adımı tam olarak bu.

---

## 4. Döngü değişmezi bir tümevarımdır

Ders 1.3'e dönelim. Toplam döngüsünün değişmezi: "her turun başında $s = 1 + \dots + (i - 1)$." Üç adımı tekrar yazalım, bu sefer tümevarımın diliyle. $P(t)$: "$t$'inci turun başında değişmez doğru."

| Ders 1.3 | Tümevarım |
| --- | --- |
| Başlangıçta doğru | Taban: $P(0)$ |
| Her tur onu korur | Adım: $P(t) \to P(t+1)$ |
| Çıkışta istediğimizi verir | Sonuç: $P$ son turda da doğru, ve çıkış koşuluyla birleşince istenen sonuç |

Değişmezi kanıtlamak, **tur sayısı üzerinde tümevarım** yapmak. Döngüde kaç tur olursa olsun değişmez bozulamaz; aynı domino.

Kodda değişmezi `assert` ile yazabiliriz. Ders 6.2'deki gibi bu bir kanıt değil, bir **denetim**; ama değişmezi kâğıtta kanıtladıktan sonra kodda da yazmak, kodun kâğıttaki algoritmayla aynı olduğunu kontrol ediyor:

```c
#include <assert.h>

static long sum_to(long n) {
    long s = 0;
    long i = 1;
    while (i <= n) {
        assert(s == (i - 1) * i / 2);   // degismez: s = 1 + ... + (i-1)
        s += i;
        i++;
    }
    assert(s == n * (n + 1) / 2);       // cikista: s = 1 + ... + n
    return s;
}
```

`sum_to(100)` 5050 döndürüyor ve hiçbir `assert` patlamıyor. Bir hata yapsak (örneğin `i = 0` ile başlasak ya da `s += i`'yi `i++`'dan sonra yazsak) ilk turda değişmez bozulur ve program hangi satırda bozulduğunu söyler.

### Özyinelemenin doğruluğu

Ders 2.8'deki özyinelemeli fonksiyonlar da tümevarımla kanıtlanıyor; yapı bire bir aynı:

```c
long fact(int n) {
    if (n == 0) return 1;          // taban
    return n * fact(n - 1);        // adim: fact(n-1) dogru ise fact(n) dogru
}
```

"`fact(n - 1)` doğru sonucu veriyorsa `fact(n)` de veriyor" demek, tümevarım hipotezini kullanmak. Özyinelemeli bir fonksiyonu yazarken "küçük çağrı zaten çalışıyor, ben sadece bir adımı yapayım" diye düşünmek, bilinçsizce bir tümevarım kanıtı yazmak. Base case'i unutmak (Ders 2.8, Bölüm 3) tabanı unutmak; tabanı olmayan tümevarım hiçbir şey kanıtlamaz.

---

## 5. Yanlış bir kanıt

**"Teorem."** Bütün atlar aynı renktir.

**"Kanıt."** $P(n)$: "$n$ atlık her grupta bütün atlar aynı renk." *Taban*: $n = 1$, tek atlık grupta atlar elbette aynı renk. *Adım*: $P(k)$'yı varsayalım ve $k+1$ atlık bir grup alalım. İlk $k$ atı al: hipoteze göre aynı renk. Son $k$ atı al: bunlar da aynı renk. İki grup ortak atlar içerdiği için, $k+1$ atın hepsi aynı renk. $\blacksquare$

Hata nerede? Taban doğru. Adım $k \ge 2$ için de doğru. Ama $k = 1$'den $k + 1 = 2$'ye geçerken: "ilk 1 at" ve "son 1 at" iki farklı at, **ortak at yok**. Adım tam bu geçişte bozuluyor; domino zincirinde ilk iki taş arasında boşluk var.

Ders: tümevarım adımı **her** $k$ için çalışmalı, özellikle tabanın hemen yanındaki küçük değerler için. Bir kanıtı kontrol ederken adımı $k = 0$, $k = 1$ için elle dene; bu, kodda sınır durumlarını (boş dizi, tek elemanlı dizi) test etmenin aynısı.

---

## Alıştırmalar

**1** – Tümevarımla kanıtla: $1 + 3 + 5 + \dots + (2n - 1) = n^2$, her $n \ge 1$ için. Bu formülü bir kare çizerek nasıl görürsün?

**2** – Tümevarımla kanıtla: her $n \ge 0$ için $n^3 - n$, 3'e bölünür.

**3** – Fibonacci sayıları $F_0 = 0$, $F_1 = 1$, $F_{n} = F_{n-1} + F_{n-2}$. Güçlü tümevarımla kanıtla: her $n \ge 0$ için $F_n < 2^n$. Taban için neden **iki** değer gerekiyor?

**4** – Ders 1.3'teki faktöriyel döngüsünün değişmezini ($f = (i - 1)!$) `assert` ile koda yaz. Faktöriyeli ayrı hesaplayan bir fonksiyon olmadan bunu nasıl denetlersin?

**5** – Şu kanıttaki hatayı bul. "Teorem: her $n \ge 0$ için $2n = 0$. Kanıt (güçlü tümevarım): taban $2 \cdot 0 = 0$. Adım: $k+1 = a + b$ olacak şekilde $a, b \le k$ seç. Hipoteze göre $2a = 0$ ve $2b = 0$, o halde $2(k+1) = 2a + 2b = 0$."

<details>
<summary>Cevaplar</summary>

**1** – *Taban*: $n = 1$: $1 = 1^2$. ✓ *Adım*: $1 + \dots + (2k - 1) = k^2$ varsayalım. Bir sonraki tek sayı $2(k+1) - 1 = 2k + 1$. $k^2 + 2k + 1 = (k+1)^2$. ✓ $\blacksquare$ Geometrik olarak: $k \times k$ bir kareyi $(k+1) \times (k+1)$'e büyütmek için sağına ve altına bir "L" eklersin; L'de $k + k + 1 = 2k + 1$ kare var.

**2** – *Taban*: $0^3 - 0 = 0$, 3'e bölünür. ✓ *Adım*: $3 \mid k^3 - k$ varsayalım.

$$
(k+1)^3 - (k+1) = k^3 + 3k^2 + 3k + 1 - k - 1 = (k^3 - k) + 3(k^2 + k).
$$

İlk parça hipoteze göre 3'e bölünür, ikinci parça açıkça 3'ün katı. Toplamları 3'e bölünür. ✓ $\blacksquare$ (Doğrudan yol: $n^3 - n = (n-1)n(n+1)$, ardışık üç sayının biri 3'e bölünür.)

**3** – *Taban*: $F_0 = 0 < 1$, $F_1 = 1 < 2$. ✓ *Adım* ($k + 1 \ge 2$): $F_{k+1} = F_k + F_{k-1} < 2^k + 2^{k-1} < 2^k + 2^k = 2^{k+1}$. ✓ $\blacksquare$ Adım iki önceki değeri ($F_k$ ve $F_{k-1}$) kullanıyor. Sadece $F_0$'ı taban alsaydık, $F_1$ için adım $F_0 + F_{-1}$'i isterdi ve $F_{-1}$ tanımlı değil. Kural: adım geriye kaç değer bakıyorsa, o kadar taban gerekiyor. Ders 2.8'deki özyinelemeli `fib`'in iki base case'i olması da bu yüzden.

**4** – Faktöriyeli ayrı hesaplamadan denetlemenin yolu, değişmezin **tümevarım adımını** denetlemek: bir önceki turun değerini saklayıp yeni değerle ilişkisine bakmak.

```c
long fact_loop(int n) {
    long f = 1;
    for (int i = 1; i <= n; i++) {
        long prev = f;              // prev = (i-1)!
        f *= i;
        assert(f / i == prev);      // f = i * (i-1)! = i!
    }
    return f;
}
```

Bu, tabanı (`f = 1 = 0!`) ve her adımı denetliyor; tümevarıma göre değişmez her turda doğru. Bonus: `f / i == prev` taşmayı da yakalıyor. `long`'da `21!` taşıyor (Ders 3.8) ve taşmadan sonra `f / i` artık `prev`'e eşit olmuyor. (Taşma işaretli tipte undefined behavior olduğu için tam güvenilir denetim `-fsanitize=undefined` ile yapılır.)

**5** – Adım $k + 1 = 1$ için bozuluyor. $k = 0$ iken $1 = a + b$ ve $a, b \le 0$ olmalı; ama doğal sayılarda $a + b = 1$ ise biri 1 olmalı, yani $k = 0$'dan büyük. Hipotez sadece $0, \dots, k$ için geçerli, 1 için değil. Gerçekten $2 \cdot 1 = 2 \ne 0$. Atlar örneği gibi: adım tabanın hemen yanında çöküyor, sonrası (tümü yanlış olsa da) "doğru" görünüyor.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), Bölüm 5: tümevarım, güçlü tümevarım, özyinelemeli tanımlar ve program doğruluğu.
- Daniel Velleman, *How to Prove It* (3. baskı), Bölüm 6: tümevarım.
- Thomas Cormen ve diğ., *Introduction to Algorithms* (4. baskı), §2.1: döngü değişmezi ile ekleme sıralamasının doğruluğu.

**Sıradaki ders:** Kümeler. Matematiğin temel veri yapısı, ve onu bir `unsigned`'ın bitleriyle temsil etmek.
