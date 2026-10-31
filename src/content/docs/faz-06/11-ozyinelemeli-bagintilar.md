---
title: "6.11 Özyinelemeli bağıntılar"
description: "Bir dizinin kendi önceki terimleriyle tanımlanması; Hanoi kulelerinin hamle sayısı T(n) = 2T(n−1) + 1 ve tahmin-kanıt ile 2ⁿ − 1 çözümü; açma (unrolling) yöntemi; doğrusal homojen bağıntılar ve karakteristik denklem; çift kök durumu; Fibonacci'nin kapalı formu (Binet), altın oran, ve double ile hesaplanan Binet formülünün n = 71'de yanılmasını gösteren C programı."
---

Ders 2.8'de Hanoi kulelerini özyinelemeyle çözmüştük: $n$ diski taşımak için önce üstteki $n - 1$'i kenara al, en büyüğünü taşı, sonra $n - 1$'i üstüne geri koy. Kaç hamle sürüyor? Kodun yapısı cevabı da bir özyineleme olarak veriyor:

$$
T(0) = 0, \qquad T(n) = 2T(n-1) + 1.
$$

Bir diziyi kendi önceki terimleriyle tanımlayan böyle denklemlere **özyinelemeli bağıntı** (recurrence relation) denir. Özyinelemeli her algoritmanın maliyeti bir özyinelemeli bağıntı; bu derste onları kapalı formüle çevirmeyi öğreneceğiz. Ders 6.10'daki toplamlar, en basit bağıntının ($S_n = S_{n-1} + a_n$) çözümüydü.

---

## 1. Hanoi: tahmin et, kanıtla

Küçük değerleri hesaplayalım: $T(0) = 0$, $T(1) = 1$, $T(2) = 3$, $T(3) = 7$, $T(4) = 15$. Desen göze çarpıyor: $T(n) = 2^n - 1$.

**Teorem.** $T(n) = 2^n - 1$.

**Kanıt** (Ders 6.4, tümevarım). *Taban*: $T(0) = 0 = 2^0 - 1$. ✓ *Adım*: $T(k) = 2^k - 1$ ise $T(k+1) = 2(2^k - 1) + 1 = 2^{k+1} - 1$. ✓ $\blacksquare$

Programla da sayalım:

```c
static uint64_t moves = 0;
static void hanoi(int n, int from, int to, int via) {
    if (n == 0) return;
    hanoi(n - 1, from, via, to);
    moves++;                       // en buyuk diski tasi
    hanoi(n - 1, via, to, from);
}
```

```
n= 0 hamle=      0  2^n-1=      0
n= 5 hamle=     31  2^n-1=     31
n=10 hamle=   1023  2^n-1=   1023
n=15 hamle=  32767  2^n-1=  32767
n=20 hamle=1048575  2^n-1=1048575
```

Bu sayı aynı zamanda **alt sınır**: $n$ diski $2^n - 1$'den az hamleyle taşımak mümkün değil. (En büyük disk bir kez taşınmalı; o anda diğer $n - 1$ disk üçüncü çubukta olmalı, oraya gitmek en az $T(n-1)$, geri gelmek en az $T(n-1)$ hamle.) Efsanedeki 64 diskli kule saniyede bir hamleyle yaklaşık 585 milyar yıl sürüyor.

"Tahmin et, kanıtla" güçlü ama tahmini bulmak her zaman kolay değil. Daha sistematik yöntemler lazım.

---

## 2. Açma

Bağıntıyı kendi içine tekrar tekrar koy, deseni gör:

$$
\begin{aligned}
T(n) &= 2T(n-1) + 1 \\
&= 2\big(2T(n-2) + 1\big) + 1 = 4T(n-2) + 2 + 1 \\
&= 8T(n-3) + 4 + 2 + 1 \\
&\;\;\vdots \\
&= 2^n T(0) + 2^{n-1} + \dots + 2 + 1 = 2^n - 1.
\end{aligned}
$$

Son adımda Ders 6.10'daki geometrik seri. Açma (unrolling ya da iteration) yöntemi bağıntıyı bir **toplama** çeviriyor ve toplamları çözmeyi biliyoruz. Ders 6.13'te böl-yönet bağıntılarını ($T(n) = 2T(n/2) + n$ gibi) aynı yöntemle bir ağaç çizerek açacağız.

---

## 3. Doğrusal homojen bağıntılar

Fibonacci, iki önceki terime bağlı:

$$
F_0 = 0, \quad F_1 = 1, \quad F_n = F_{n-1} + F_{n-2}.
$$

Açma burada dağılıyor: her adımda terim sayısı ikiye katlanıyor. Başka bir fikir gerekiyor.

Genel biçim: $k$'ıncı dereceden **doğrusal homojen** bağıntı, sabit katsayılarla

$$
a_n = c_1 a_{n-1} + c_2 a_{n-2} + \dots + c_k a_{n-k}.
$$

"Doğrusal": terimler sadece sabitlerle çarpılıp toplanıyor ($a_{n-1}^2$ yok). "Homojen": sabit bir terim yok (Hanoi'deki $+1$ gibi). Böyle bir bağıntıyı ve ilk $k$ değeri bilirsen dizi tek türlü belirleniyor (tümevarım).

**Fikir:** $a_n = r^n$ biçiminde bir çözüm ara. İkinci dereceden durumda, $a_n = c_1 a_{n-1} + c_2 a_{n-2}$'ye koyunca

$$
r^n = c_1 r^{n-1} + c_2 r^{n-2} \quad\Rightarrow\quad r^2 = c_1 r + c_2 \quad (r \ne 0 \text{ için } r^{n-2}\text{'ye böl}).
$$

Bu, bağıntının **karakteristik denklemi**: $r^2 - c_1 r - c_2 = 0$. Kökleri $r_1$, $r_2$ ise $r_1^n$ ve $r_2^n$ ikisi de çözüm. Ve bağıntı doğrusal olduğu için çözümlerin her doğrusal birleşimi de çözüm:

$$
a_n = \alpha\, r_1^n + \beta\, r_2^n.
$$

$\alpha$ ve $\beta$'yı ilk iki değerden buluyoruz.

**Teorem.** $r^2 - c_1 r - c_2 = 0$'ın iki farklı kökü $r_1 \ne r_2$ varsa, bağıntının **her** çözümü $\alpha r_1^n + \beta r_2^n$ biçimindedir.

**Kanıt (ana fikir).** Verilen $a_0$, $a_1$ için $\alpha + \beta = a_0$ ve $\alpha r_1 + \beta r_2 = a_1$ sisteminin tek çözümü var (çünkü $r_1 \ne r_2$; Ders 6.26'daki determinant sıfır değil). Bu $\alpha$, $\beta$ ile kurulan dizi ilk iki terimde $a$ ile çakışıyor ve aynı bağıntıyı sağlıyor; dolayısıyla güçlü tümevarımla her terimde çakışıyor. $\blacksquare$

**Örnek.** $a_0 = 1$, $a_1 = 4$, $a_n = 5a_{n-1} - 6a_{n-2}$. Karakteristik denklem $r^2 - 5r + 6 = 0$, kökler $2$ ve $3$. $a_n = \alpha 2^n + \beta 3^n$. İlk değerler: $\alpha + \beta = 1$, $2\alpha + 3\beta = 4$, buradan $\beta = 2$, $\alpha = -1$. Sonuç:

$$
a_n = 2 \cdot 3^n - 2^n.
$$

Doğrulama: $a_2 = 5 \cdot 4 - 6 \cdot 1 = 14$, formül $18 - 4 = 14$. ✓ (Programla $n = 30$'a kadar denedik, hepsi tutuyor.)

### Çift kök

Karakteristik denklemin tek (çift katlı) bir kökü varsa, $r_1 = r_2 = r$, iki bağımsız çözüm $r^n$ ve $n\, r^n$:

$$
a_n = (\alpha + \beta n)\, r^n.
$$

Örnek: $a_n = 4a_{n-1} - 4a_{n-2}$, $r^2 - 4r + 4 = (r - 2)^2$. Çözümler $2^n$ ve $n 2^n$. Bu, Ders 6.10'daki $\sum k\, 2^k$ toplamında gördüğümüz $n 2^n$ deseninin kaynağı.

### Homojen olmayan

Hanoi'deki $+1$ gibi sabit bir terim varsa bir hile: bağıntıyı sabiti yok edecek biçimde değiştir. $T(n) = 2T(n-1) + 1$ ve $T(n-1) = 2T(n-2) + 1$; çıkar:

$$
T(n) - T(n-1) = 2T(n-1) - 2T(n-2) \quad\Rightarrow\quad T(n) = 3T(n-1) - 2T(n-2).
$$

Karakteristik denklem $r^2 - 3r + 2 = (r - 1)(r - 2)$, $T(n) = \alpha + \beta 2^n$. $T(0) = 0$, $T(1) = 1$'den $\alpha = -1$, $\beta = 1$. Yine $2^n - 1$, ama bu sefer tahmin etmeden.

---

## 4. Fibonacci'nin kapalı formu

$F_n = F_{n-1} + F_{n-2}$: karakteristik denklem $r^2 - r - 1 = 0$, kökler

$$
\varphi = \frac{1 + \sqrt{5}}{2} \approx 1.618, \qquad \psi = \frac{1 - \sqrt{5}}{2} \approx -0.618.
$$

$\varphi$, **altın oran**. $F_0 = 0$'dan $\alpha + \beta = 0$, $F_1 = 1$'den $\alpha \varphi + \beta \psi = 1$; buradan $\alpha = \frac{1}{\sqrt 5}$, $\beta = -\frac{1}{\sqrt 5}$:

$$
F_n = \frac{\varphi^n - \psi^n}{\sqrt{5}} \qquad \text{(Binet formülü)}.
$$

Kökler irrasyonel, ama her $n$ için sonuç bir **tamsayı**. Üstelik $|\psi| < 1$ olduğu için $\psi^n$ hızla sıfıra gidiyor ve $\left|\frac{\psi^n}{\sqrt 5}\right| < \frac{1}{2}$; dolayısıyla

$$
F_n = \text{round}\!\left(\frac{\varphi^n}{\sqrt{5}}\right).
$$

İki önemli sonuç:

- **Büyüme hızı**: $F_n \approx \frac{\varphi^n}{\sqrt 5}$, üstel. Ders 2.8'deki saf özyinelemeli `fib`'in çağrı sayısı da $F_n$ ile orantılı, dolayısıyla $\varphi^n$ gibi büyüyor. Ders 6.4'teki $F_n < 2^n$ sınırı doğru ama gevşekti; gerçek taban $1.618$.
- **Öklid algoritması**: Ders 1.3'teki EBOB algoritmasının en kötü girdisi ardışık Fibonacci sayıları, ve adım sayısı $\log_\varphi$ ile orantılı (Lamé teoremi).

### Kayan noktada kapalı form

Formül elimizde; o zaman `fib(n)` için döngüye gerek yok mu? Deneyelim:

```c
const double phi = (1 + sqrt(5.0)) / 2;
uint64_t a = 0, b = 1;         // F(0), F(1)
for (int n = 0; n <= 93; n++) {
    uint64_t binet = (uint64_t)llround(pow(phi, n) / sqrt(5.0));
    if (binet != a) {
        printf("Binet ilk kez n=%d'de yanilir: %llu != %llu\n", n,
               (unsigned long long)binet, (unsigned long long)a);
        break;
    }
    uint64_t t = a + b; a = b; b = t;
}
```

```
Binet ilk kez n=71'de yanilir: 308061521170130 != 308061521170129
```

Matematikte kusursuz formül, `double`'da $n = 71$'de bir birim yanlış. Sebep Ders 3.14: `double`'ın 53 bitlik anlamlı kısmı yaklaşık 16 ondalık basamak taşıyor; $\varphi$'deki küçücük yuvarlama hatası $\varphi^{71}$'de $10^{14}$ katına büyüyor ve tam sayıyı bozuyor. **Kapalı form, doğru hesaplama yöntemi demek değil.** Tam sonuç isteyen kod ya döngüyle ($n$ adım) ya da Ders 6.25'teki matris kuvvetiyle ($\log n$ adım, tamsayılarla) hesaplıyor.

Kapalı formun asıl değeri **analizde**: bir algoritmanın $\varphi^n$ mi $2^n$ mi $n^2$ mi büyüdüğünü söylemesinde. Bir sonraki dersin konusu.

---

## Alıştırmalar

**1** – $a_0 = 2$, $a_1 = 5$, $a_n = a_{n-1} + 6a_{n-2}$ bağıntısını karakteristik denklemle çöz. İlk birkaç değeri hem bağıntıyla hem formülle hesaplayıp karşılaştır.

**2** – Hanoi'nin bir varyantında diskler sadece **komşu** çubuklar arasında taşınabiliyor (1'den 3'e doğrudan geçiş yok). Hamle sayısı $T(n) = 3T(n-1) + 2$. Çöz.

**3** – $n$ basamaklı, ardışık iki 1 içermeyen ikilik dizgilerin sayısı $s_n$ olsun ($s_1 = 2$: `0`, `1`; $s_2 = 3$: `00`, `01`, `10`). Bir bağıntı kur ve Fibonacci ile ilişkisini bul. Bütün dizgileri bitlerle sayan bir programla $n = 20$'ye kadar doğrula. (İpucu: `x & (x >> 1)`.)

**4** – $a_n = 6a_{n-1} - 9a_{n-2}$, $a_0 = 1$, $a_1 = 6$. Çift kök durumu; çöz.

**5** – Binet formülünü `long double` ile dene. Kaçıncı $n$'de yanılıyor? Sonucu `long double`'ın anlamlı bit sayısıyla açıkla (`LDBL_MANT_DIG`). macOS'ta ARM işlemcide `long double` ile `double` aynı olabilir; neden?

<details>
<summary>Cevaplar</summary>

**1** – $r^2 - r - 6 = (r - 3)(r + 2)$. $a_n = \alpha 3^n + \beta (-2)^n$. $\alpha + \beta = 2$ ve $3\alpha - 2\beta = 5$. İlkinden $\beta = 2 - \alpha$; ikincisine koyunca $5\alpha - 4 = 5$, yani $\alpha = \frac{9}{5}$, $\beta = \frac{1}{5}$. $a_n = \frac{9 \cdot 3^n + (-2)^n}{5}$. Bağıntı: $a_2 = 5 + 12 = 17$, formül $\frac{81 + 4}{5} = 17$. ✓ $a_3 = 17 + 30 = 47$, formül $\frac{243 - 8}{5} = 47$. ✓ Katsayılar kesir çıksa da her terim tamsayı.

**2** – Sabiti yok etmek için ardışık iki denklemi çıkar: $T(n) - T(n-1) = 3T(n-1) - 3T(n-2)$, yani $T(n) = 4T(n-1) - 3T(n-2)$. $r^2 - 4r + 3 = (r - 1)(r - 3)$, $T(n) = \alpha + \beta 3^n$. $T(0) = 0$, $T(1) = 2$ (bir disk: 1'den 2'ye, 2'den 3'e): $\alpha + \beta = 0$, $\alpha + 3\beta = 2$, $\beta = 1$, $\alpha = -1$. $T(n) = 3^n - 1$. Daha kısa yol: $T(n) + 1 = 3(T(n-1) + 1)$, yani $T(n) + 1$ geometrik bir dizi.

**3** – Son basamağa bak. `0` ile bitiyorsa öncesi geçerli herhangi bir $n-1$ basamaklı dizgi: $s_{n-1}$. `1` ile bitiyorsa ondan önceki `0` olmalı, öncesi $n-2$ basamaklı geçerli dizgi: $s_{n-2}$. $s_n = s_{n-1} + s_{n-2}$, $s_1 = 2$, $s_2 = 3$: $s_n = F_{n+2}$.

```c
for (int n = 1; n <= 20; n++) {
    int count = 0;
    for (uint32_t x = 0; x < (1u << n); x++)
        if ((x & (x >> 1)) == 0) count++;   // komsu iki 1 yok
    printf("%d: %d\n", n, count);           // 2, 3, 5, 8, 13, ...
}
```

`x & (x >> 1)`, Ders 5.2'deki kaydırılmış maske: bir bit ve solundaki komşusu ikisi de 1 ise sonuçta 1 oluşuyor.

**4** – $r^2 - 6r + 9 = (r - 3)^2$, $a_n = (\alpha + \beta n) 3^n$. $a_0 = \alpha = 1$; $a_1 = (1 + \beta) \cdot 3 = 6$, $\beta = 1$. $a_n = (n + 1) 3^n$. Kontrol: $a_2 = 36 - 9 = 27$, formül $3 \cdot 9 = 27$. ✓

**5** – x86-64 Linux'ta `long double` 80 bitlik x87 formatı, `LDBL_MANT_DIG` = 64. Yaklaşık 11 bit daha fazla hassasiyet, kabaca $\log_\varphi(2^{11}) \approx 16$ adım daha: yanılma noktası 15 kadar adım ileri kayıyor (tam değeri programla bul). Apple Silicon (ARM64) macOS'ta `long double` ile `double` aynı tip (`LDBL_MANT_DIG` = 53); ARM'ın 80 bitlik bir kayan nokta birimi yok ve Apple'ın ABI'si `long double`'ı `double` olarak tanımlıyor. Orada sonuç değişmiyor: yine $n = 71$. Bir tipin boyutunun platforma göre değişmesi, Ders 3.2'deki `long`'un hikâyesinin kayan nokta hali.

</details>

---

## Kaynaklar

- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), Bölüm 1 (Hanoi, özyinelemeli problemler) ve §6.6 (Fibonacci sayıları).
- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §8.1–8.2: özyinelemeli bağıntıların modellenmesi ve doğrusal bağıntıların çözümü.
- Donald Knuth, *TAOCP* Cilt 1, §1.2.8: Fibonacci sayıları.

**Sıradaki ders:** Asimptotik notasyon. $O$, $\Omega$, $\Theta$: sabitleri ve küçük terimleri atıp büyüme hızını konuşmak.
