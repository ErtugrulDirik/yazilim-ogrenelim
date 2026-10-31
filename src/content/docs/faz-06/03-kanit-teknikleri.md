---
title: "6.3 Kanıt teknikleri"
description: "Tanım, teorem ve kanıt; doğrudan kanıt (iki tek sayının toplamı çifttir), karşıt ters ile kanıt (n² çiftse n çifttir), çelişki ile kanıt (√2 irrasyoneldir, asallar sonsuzdur), durumlara ayırma, varlık kanıtı ve karşı örnekle çürütme; denemenin kanıt olmadığını gösteren n² + n + 41 örneği ve karşı örnek arayan C programı."
---

Ders 6.2'nin sonunda bir duvara çarptık: `assert` bir koşulun **bu girdide** doğru olduğunu söylüyor, ama "her girdide doğru" demek sonsuz bir $\forall$ ve sonsuz sayıda girdiyi deneyemeyiz. Matematik bu sorunu iki bin yıldır **kanıt** ile çözüyor: herkesin kabul ettiği küçük adımlarla, bir iddianın **zorunlu olarak** doğru olduğunu göstermek.

Bu derste en sık kullanılan dört kanıt kalıbını göreceğiz. Her biri Ders 6.1'deki bir totolojiye dayanıyor.

---

## 1. Önce tanımlar

Bir şeyi kanıtlamak için önce ne dediğimizi kesinleştirmemiz gerekiyor. Bu ders boyunca evren tamsayılar ve şu tanımları kullanacağız:

- $n$ **çifttir** $\iff$ $\exists k\, (n = 2k)$
- $n$ **tektir** $\iff$ $\exists k\, (n = 2k + 1)$
- $a$, $b$'yi **böler** ($a \mid b$) $\iff$ $\exists k\, (b = ak)$
- $p$ **asaldır** $\iff$ $p > 1$ ve $p$'nin pozitif bölenleri sadece $1$ ve $p$

Her tamsayının ya çift ya tek olduğunu (ikisi birden değil) kabul ediyoruz; bölme algoritmasının (Ders 2.3'teki `%`) sonucu bu.

Tanımlar kanıtların hammaddesi. "Çift" kelimesini görünce zihninde "$2k$ biçiminde yazılabilir" diye açılmalı; çoğu kanıt tanımları açıp cebirle kapatmaktan ibaret.

Birkaç kelime: **teorem** kanıtlanmış önemli bir iddia; **önsav** (lemma) bir teoremi kanıtlamak için kullanılan yardımcı teorem; **sonuç** (corollary) bir teoremden hemen çıkan iddia; **sanı** (conjecture) doğru olduğu düşünülen ama kanıtlanmamış iddia.

---

## 2. Doğrudan kanıt

$p \to q$ biçimindeki bir iddiayı kanıtlamanın en doğal yolu: **$p$'yi varsay, adım adım $q$'ya ulaş.**

**Teorem.** İki tek sayının toplamı çifttir.

**Kanıt.** $a$ ve $b$ tek olsun. Tanım gereği $a = 2j + 1$ ve $b = 2k + 1$ olacak şekilde $j$, $k$ tamsayıları var. O halde

$$
a + b = 2j + 1 + 2k + 1 = 2(j + k + 1).
$$

$j + k + 1$ bir tamsayı, dolayısıyla $a + b$ çift. $\blacksquare$

Kalıba dikkat: "tek" tanımını açtık, cebir yaptık, sonucu "çift" tanımına uyacak biçime soktuk. $\blacksquare$ (ya da "QED") kanıtın bittiğini gösteriyor.

Önemli bir ayrıntı: $a$ ve $b$ için **farklı** harfler ($j$, $k$) kullandık. İkisine de $2k + 1$ deseydik, sessizce $a = b$ varsaymış olurduk ve sadece $a + a$'nın çift olduğunu kanıtlardık.

Aynı kalıpla bit düzeyindeki bir gerçeği de kanıtlayabiliriz:

**Teorem.** $n$ tekse $n^2$ de tektir.

**Kanıt.** $n = 2k + 1$ ise $n^2 = 4k^2 + 4k + 1 = 2(2k^2 + 2k) + 1$, tek. $\blacksquare$

Faz 5'in dilinde: bir sayının en düşük biti, karesinin en düşük biti. `(n * n) & 1 == n & 1` bütün `unsigned` sayılar için doğru, çünkü bu kanıt mod $2^{32}$'de de geçerli.

---

## 3. Karşıt ters ile kanıt

Bazen $p$'den $q$'ya doğrudan gitmek zor. Ders 6.1'deki denkliği hatırla: $p \to q \equiv \neg q \to \neg p$. O halde **$\neg q$'yu varsayıp $\neg p$'ye ulaşmak** da aynı iddiayı kanıtlar.

**Teorem.** $n^2$ çiftse $n$ çifttir.

Doğrudan denesek: $n^2 = 2k$ ise $n = \sqrt{2k}$... Bu bir yere götürmüyor. Karşıt tersi: "$n$ çift değilse, $n^2$ çift değildir", yani "$n$ tekse, $n^2$ tektir."

**Kanıt.** Karşıt tersini kanıtlayacağız. $n$ tek olsun. Bir önceki bölümde $n^2$'nin tek olduğunu gösterdik. Dolayısıyla $n^2$ çiftse $n$ tek olamaz, çift olmalı. $\blacksquare$

Karşıt ters, "olumsuz" bir varsayımı "olumlu" bir varsayıma çeviriyor: "$n^2$ çift" bilgisi $n$ hakkında doğrudan bir şey söylemiyordu, "$n$ tek" ise $n = 2k + 1$ diye elle tutulur bir biçim veriyor.

---

## 4. Çelişki ile kanıt

En güçlü kalıp: **iddianın yanlış olduğunu varsay, bir çelişkiye ulaş.** Mantıksal temeli: $\neg p \to (q \land \neg q)$ doğruysa $p$ doğru olmalı, çünkü hiçbir şey hem doğru hem yanlış olamaz.

**Teorem.** $\sqrt{2}$ irrasyoneldir: $a, b$ tamsayı olmak üzere $\frac{a}{b}$ biçiminde yazılamaz.

**Kanıt.** Tersini varsayalım: $\sqrt{2} = \frac{a}{b}$, ve kesir **sadeleşmiş** olsun (ortak böleni 1, Ders 2.9'daki EBOB ile her kesri böyle yazabiliriz). Kare alınca

$$
2 = \frac{a^2}{b^2} \quad\Rightarrow\quad a^2 = 2b^2.
$$

Demek $a^2$ çift. Bir önceki teoreme göre $a$ çift: $a = 2c$. Yerine koyunca $4c^2 = 2b^2$, yani $b^2 = 2c^2$. Demek $b^2$ çift, dolayısıyla $b$ de çift. Ama $a$ ve $b$ ikisi de çiftse ortak bölenleri en az 2; kesir sadeleşmiş değil. Varsayımla çelişiyor. $\blacksquare$

Bu kanıtın Faz 3 için bir sonucu var: $\sqrt{2}$ hiçbir sonlu kesirle **tam** yazılamıyor, dolayısıyla hiçbir `double` (ki her `double` bir kesir: tamsayı bölü 2'nin kuvveti, Ders 3.12) $\sqrt{2}$'ye eşit olamaz. `sqrt(2.0)` her zaman bir yaklaşıklık.

**Teorem (Öklid).** Sonsuz sayıda asal vardır.

**Kanıt.** Tersini varsayalım: asallar sonlu, $p_1, p_2, \dots, p_k$. Şu sayıya bakalım:

$$
N = p_1 p_2 \cdots p_k + 1.
$$

$N > 1$, dolayısıyla bir asal böleni var (bunu Ders 6.4'te güçlü tümevarımla kanıtlayacağız). Bu asal listede olmalı, diyelim $p_i$. $p_i$, $p_1 \cdots p_k$'yı böler; $N$'yi de bölüyorsa farklarını, yani $1$'i de bölmeli. Ama hiçbir asal 1'i bölmez. Çelişki. $\blacksquare$

Sık yapılan bir hata: "$N$ asaldır" demek. Değil! $2 \cdot 3 \cdot 5 \cdot 7 \cdot 11 \cdot 13 + 1 = 30031 = 59 \cdot 509$. Kanıt sadece $N$'nin listede **olmayan** bir asal böleni olduğunu söylüyor.

---

## 5. Durumlara ayırma ve varlık

**Durumlara ayırma** (proof by cases): iddiayı, bütün olasılıkları kapsayan birkaç duruma bölüp her birini ayrı kanıtlamak. Temeli: $(p \lor q) \land (p \to r) \land (q \to r) \to r$.

**Teorem.** Her $n$ için $n^2 + n$ çifttir.

**Kanıt.** $n$ çift ya da tek. *Durum 1*: $n = 2k$ ise $n^2 + n = 4k^2 + 2k = 2(2k^2 + k)$. *Durum 2*: $n = 2k + 1$ ise $n^2 + n = (2k+1)(2k+2) = 2(2k+1)(k+1)$. Her iki durumda çift. $\blacksquare$

(Daha kısa yol: $n^2 + n = n(n+1)$, ardışık iki sayıdan biri mutlaka çift. Bir teoremin birden çok kanıtı olabilir; kısa olan genellikle daha çok şey anlatır.)

Ders 2.3'teki `switch` ve `if-else` zincirleri programlardaki durumlara ayırma. Bir durumu unutmak, kanıtta da kodda da aynı türden hata.

**Varlık kanıtı**: $\exists x\, P(x)$'i kanıtlamak için bir **tanık** göstermek yeter. "Üç ardışık sayının toplamı 99 olabilir mi?" — $32 + 33 + 34 = 99$. Bitti.

**Karşı örnekle çürütme**: $\forall x\, P(x)$'in **yanlış** olduğunu göstermek için tek bir karşı örnek yeter, çünkü $\neg \forall x\, P(x) \equiv \exists x\, \neg P(x)$. Ders 6.1'deki asimetri burada: "her" demek kanıt ister, "her değil" demek tek bir örnek.

---

## 6. Denemek kanıt değildir

Euler'in ünlü polinomuna bakalım: $n^2 + n + 41$. $n = 0$ için 41, $n = 1$ için 43, $n = 2$ için 47, $n = 3$ için 53... Hepsi asal. Kırk değer deneyip hepsinin asal çıktığını görünce "her $n$ için asal" demek çok cazip. Bilgisayara soralım:

```c
#include <stdio.h>
#include <stdbool.h>

static bool is_prime(long n) {
    if (n < 2) return false;
    for (long d = 2; d * d <= n; d++) {
        if (n % d == 0) return false;
    }
    return true;
}

int main(void) {
    for (long n = 0; n < 100; n++) {
        long v = n * n + n + 41;
        if (!is_prime(v)) {
            printf("karsi ornek: n = %ld, n^2 + n + 41 = %ld = 41 * %ld\n", n, v, v / 41);
            break;
        }
    }
    return 0;
}
```

```
karsi ornek: n = 40, n^2 + n + 41 = 1681 = 41 * 41
```

Kırk değer doğru, kırk birincisi yanlış. Üstelik kanıtı programdan bile kolay: $n = 41$ için $41^2 + 41 + 41 = 41 \cdot 43$, $41$'e bölünüyor; bunu görmek için hiçbir şey denemeye gerek yok.

Daha kötü örnekler de var. Pólya sanısı yüzlerce milyon sayıya kadar doğru çıktı, ilk karşı örneği yaklaşık 906 milyonda. Asalların dağılımıyla ilgili bir başka sanının ($\pi(x) < \mathrm{li}(x)$) ilk karşı örneği ise $10^{316}$ civarında; hiçbir bilgisayar oraya kadar sayamaz, karşı örneğin varlığı da kanıtla bulundu.

Program yazarken de durum aynı. Testler bir hatanın **varlığını** gösterebilir, **yokluğunu** gösteremez (Dijkstra). Bir fonksiyonu yüz girdiyle test etmek yüz $P(a_i)$ kontrol etmek; $\forall$ değil. Bu yüzden derleyicinin optimizasyonları test edilerek değil, kanıtlanarak doğru kabul ediliyor: `x * 2`'yi `x << 1`'e çevirmenin her `unsigned x` için güvenli olduğunu biliyoruz, çünkü kanıtı var (Ders 5.13). Faz 19'da bu kanıtları bilgisayara yaptıracağız.

Yine de bilgisayarla denemenin iki meşru kullanımı var: **karşı örnek aramak** (bulursan iddia çürüdü, kanıt bitti) ve **sanı üretmek** (bir desen görürsen, kanıtlamaya değecek bir şey bulmuş olabilirsin).

---

## Alıştırmalar

**1** – Doğrudan kanıtla: bir çift sayı ile bir tek sayının çarpımı çifttir.

**2** – Karşıt tersle kanıtla: $a + b \ge 100$ ise $a \ge 50$ veya $b \ge 50$.

**3** – Çelişkiyle kanıtla: en büyük tamsayı yoktur.

**4** – "Her asal $n$ için $2^n - 1$ asaldır" iddiasını çürütmek için karşı örnek arayan bir program yaz. İlk karşı örnek ne? (Bu sayılar Mersenne sayıları; GIMPS projesinin bulduğu dev asalların hepsi bu biçimde.)

**5** – Şu "kanıt"taki hatayı bul: "Teorem: $n$ çiftse $n^2$ çifttir. Kanıt: $n^2$ çift olsun, $n^2 = 2k$. O zaman $n \cdot n = 2k$, demek $n$ çift." Teorem doğru mu? Kanıt neyi kanıtlamaya çalıştı?

<details>
<summary>Cevaplar</summary>

**1** – $a$ çift, $b$ tek olsun: $a = 2j$, $b = 2k + 1$. $ab = 2j(2k + 1) = 2(j(2k+1))$, çift. $\blacksquare$ (Aslında $b$'nin tek olmasını hiç kullanmadık: çift bir sayı **herhangi** bir tamsayıyla çarpılınca çift. Kanıt, iddiadan daha güçlü bir şey gösterdi. Bu sık olur ve iyidir; bir varsayımı kullanmadığını fark etmek, teoremi genelleştirebileceğini söyler.)

**2** – Karşıt ters: "$a < 50$ ve $b < 50$ ise $a + b < 100$." (Olumsuzlama: $\neg(a \ge 50 \lor b \ge 50) \equiv a < 50 \land b < 50$, De Morgan.) Kanıt: tamsayılarda $a \le 49$ ve $b \le 49$, toplayınca $a + b \le 98 < 100$. $\blacksquare$ Doğrudan kanıt "$a + b \ge 100$"den hangi değişkenin büyük olduğunu bulmaya çalışıp takılırdı; karşıt ters ise iki eşitsizliği toplamaktan ibaret.

**3** – Tersini varsayalım: en büyük tamsayı $M$ olsun. $M + 1$ de bir tamsayı ve $M + 1 > M$. $M$'nin en büyük olmasıyla çelişiyor. $\blacksquare$ (Matematikte doğru; C'nin `int`'inde `INT_MAX` en büyük tamsayı, çünkü `INT_MAX + 1` bir `int` değil. Kanıt, "tamsayılar toplamaya göre kapalı" varsayımını kullandı ve makine tamsayılarında bu varsayım yanlış.)

**4** –

```c
for (long n = 2; n < 40; n++) {
    if (!is_prime(n)) continue;
    long m = (1L << n) - 1;
    if (!is_prime(m)) { printf("n = %ld: 2^n - 1 = %ld asal degil\n", n, m); break; }
}
```

```
n = 11: 2^n - 1 = 2047 asal degil
```

$2047 = 23 \cdot 89$. $n = 2, 3, 5, 7$ için $3, 7, 31, 127$ asal; desen beşinci asalda bozuluyor. Tersi ise doğru ve kanıtlanabilir: $2^n - 1$ asalsa $n$ asaldır (karşıt tersiyle: $n = ab$ ise $2^a - 1$, $2^n - 1$'i böler).

**5** – Kanıt, teoremin **karşıtını** ("$n^2$ çiftse $n$ çift") kanıtlamaya çalıştı, kendisini değil: $p$ = "$n$ çift", $q$ = "$n^2$ çift" iken $q$'yu varsayıp $p$'ye ulaşmaya çalışıyor. Üstelik son adım ("$n \cdot n = 2k$, demek $n$ çift") gerekçesiz; tam da Bölüm 3'te karşıt tersle kanıtladığımız şey. Teorem doğru, doğru kanıtı: $n = 2k$ ise $n^2 = 4k^2 = 2(2k^2)$. Ders 6.1'deki uyarı: koşul ile karşıtı denk değil; birini kanıtlamak öbürünü kanıtlamaz.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §1.7–1.8: kanıt yöntemleri ve stratejileri.
- Daniel Velleman, *How to Prove It* (3. baskı), Bölüm 3: kanıt kalıpları, adım adım.
- Richard Hammack, *Book of Proof* (3. baskı), Bölüm 4–7: doğrudan, karşıt ters ve çelişki ile kanıt; yazarın sitesinde ücretsiz.
- Edsger Dijkstra, "The Humble Programmer" (1972): testlerin hataların yokluğunu gösteremeyeceği üzerine.

**Sıradaki ders:** Tümevarım. Sonsuz bir $\forall$'ı iki adımda kanıtlamak, ve Faz 1'deki döngü değişmezinin gerçek adı.
