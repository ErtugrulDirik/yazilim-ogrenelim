---
title: "12.1 Bilgisayar cebiri nedir"
description: "Sayısal ve sembolik hesaplamanın farkı: (1 - cos x)/x² ifadesinin double ile x = 1e-9'da 0 vermesi, 14×14 Hilbert sisteminde hatanın 15'e çıkması ve 21!'in unsigned long long'da sessizce taşması; aynı soruların Python'un kesin kesirleriyle tam 1 ve tam 1/2 vermesi; SymPy ile limit, seri, çarpanlara ayırma, türev, integral ve iç içe kökleri sadeleştirme, Mathematica ve Maxima karşılıkları; kesinliğin bedeli: 6×6 determinantta 720 terim, harmonik toplamda 4345 basamaklı payda; sıfıra eşitlik sorusunun karar verilemezliği (Richardson) ve bu fazın yol haritası."
---

Faz 3'te kayan noktanın neden yaklaşık olduğunu, Faz 6'da tamsayılar, kesirler, polinomlar ve cisimler gibi yapıların kurallarını öğrendik. Faz 12 ikisini birleştiriyor: **bilgisayara yaklaşık değil kesin hesap yaptırmak**. Bunu yapan programlara *bilgisayar cebir sistemi* (CAS: computer algebra system) denir: Mathematica, Maple, Maxima, SymPy. Bu fazda bunların çekirdeğini, büyük tamsayılardan sembolik türeve kadar C'de sıfırdan yazacağız.

Bu derste henüz CAS yazmıyoruz; neden gerektiğini ve neye benzediğini görüyoruz.

---

## 1. İki dünya

| | Sayısal hesap | Sembolik hesap |
| --- | --- | --- |
| Nesneler | `double`, sabit genişlikli tamsayılar | Tam sayılar, kesirler, $\sqrt{2}$, $x$, $\sin x$ |
| Sonuç | Yaklaşık bir sayı | Kesin bir ifade |
| Hız | Donanım komutu, nanosaniye | Yazılım, çoğunlukla çok daha yavaş |
| Bellek | Sabit | Sonuçla birlikte büyür |
| Hata | Yuvarlama, taşma | Yok; ama ifade patlaması ve zaman |
| Örnek | Faz 11'deki bütün kod | $\int e^{-x^2} dx = \sqrt{\pi}$ |

İkisi rakip değil, birbirini tamamlıyor. Derleyiciler de iki dünyayı birlikte kullanıyor: sabitleri katlarken kesin, kod üretirken sayısal (Faz 16). Ders 12.12'de yazacağımız ifade sadeleştirme, derleyicinin `instcombine` geçişinin doğrudan atası.

---

## 2. Kayan noktanın üç yanılgısı

```c
/* sayisal.c: kayan noktanin uc yanilgisi */
#include <stdio.h>
#include <math.h>

/* n x n Hilbert matrisi H[i][j] = 1/(i+j+1); H x = H * (1,1,...,1) coz */
static double hilbert_hata(int n) {
    double a[16][17];
    for (int i = 0; i < n; i++) {
        a[i][n] = 0;
        for (int j = 0; j < n; j++) { a[i][j] = 1.0 / (i + j + 1); a[i][n] += a[i][j]; }
    }
    for (int k = 0; k < n; k++) {                 /* kismi pivotlu Gauss (Ders 6.26) */
        int p = k;
        for (int i = k + 1; i < n; i++) if (fabs(a[i][k]) > fabs(a[p][k])) p = i;
        for (int j = 0; j <= n; j++) { double t = a[k][j]; a[k][j] = a[p][j]; a[p][j] = t; }
        for (int i = k + 1; i < n; i++) {
            double m = a[i][k] / a[k][k];
            for (int j = k; j <= n; j++) a[i][j] -= m * a[k][j];
        }
    }
    double x[16], hata = 0;
    for (int i = n - 1; i >= 0; i--) {
        double s = a[i][n];
        for (int j = i + 1; j < n; j++) s -= a[i][j] * x[j];
        x[i] = s / a[i][i];
        if (fabs(x[i] - 1) > hata) hata = fabs(x[i] - 1);
    }
    return hata;
}

int main(void) {
    printf("1) (1 - cos x) / x^2, dogru limit 0.5\n");
    for (double x = 1e-1; x > 1e-10; x /= 100)
        printf("   x = %.0e  ->  %.17g\n", x, (1 - cos(x)) / (x * x));

    printf("2) Hilbert sistemi, dogru cevap hep 1: en buyuk hata\n");
    for (int n = 4; n <= 14; n += 2) printf("   n = %2d  ->  %.3g\n", n, hilbert_hata(n));

    printf("3) n! unsigned long long ile\n");
    unsigned long long f = 1;
    for (int n = 1; n <= 22; n++) { f *= (unsigned long long)n; if (n >= 19) printf("   %d! = %llu\n", n, f); }
    return 0;
}
```

```
$ clang -O2 sayisal.c -o sayisal && ./sayisal
1) (1 - cos x) / x^2, dogru limit 0.5
   x = 1e-01  ->  0.49958347219741783
   x = 1e-03  ->  0.49999995832550326
   x = 1e-05  ->  0.50000004137018539
   x = 1e-07  ->  0.49960036108132039
   x = 1e-09  ->  0
2) Hilbert sistemi, dogru cevap hep 1: en buyuk hata
   n =  4  ->  5.27e-13
   n =  6  ->  3.71e-10
   n =  8  ->  6.88e-07
   n = 10  ->  0.000377
   n = 12  ->  0.0252
   n = 14  ->  15.2
3) n! unsigned long long ile
   19! = 121645100408832000
   20! = 2432902008176640000
   21! = 14197454024290336768
   22! = 17196083355034583040
```

1. **Yok edici çıkarma** (Ders 3.14). $x = 10^{-9}$'da $\cos x$, `double`'da tam 1'e yuvarlanıyor ve pay 0 oluyor. $x$ küçüldükçe sonuç önce iyileşiyor, sonra bozuluyor: $x = 10^{-5}$'te bile yalnız 7 basamak doğru.
2. **Kötü koşullu sistem** (Ders 6.26). Hilbert matrisinin girişleri $1/(i+j+1)$. Kısmi pivotlu Gauss, $n = 14$'te doğru cevabı (hepsi 1) **15'lik hatayla** buluyor: sonuç tamamen anlamsız. Algoritmada bir hata yok; `double`'ın 16 basamağı bu matris için yetmiyor.
3. **Sessiz taşma** (Ders 3.8). $21! = 51\,090\,942\,171\,709\,440\,000$ olmalı; 64 bite sığmıyor ve program hiçbir uyarı vermeden yanlış sayı yazıyor.

---

## 3. Kesin aritmetik

Aynı sorular Python'da, `int` (sınırsız büyüklükte) ve `fractions.Fraction` (kesin kesir) ile:

```python
# kesin.py: ayni sorular kesin aritmetikle (Python'un Fraction'i ve buyuk tamsayilari)
from fractions import Fraction
import math, time, sys
sys.set_int_max_str_digits(0)          # 4300 basamak sinirini kaldir (12.4)

def hilbert_kesin(n):
    a = [[Fraction(1, i + j + 1) for j in range(n)] for i in range(n)]
    for i in range(n): a[i].append(sum(a[i]))
    for k in range(n):                       # pivot gerekmez: kesin aritmetikte yuvarlama yok
        for i in range(k + 1, n):
            m = a[i][k] / a[k][k]
            for j in range(k, n + 1): a[i][j] -= m * a[k][j]
    x = [0] * n
    for i in reversed(range(n)):
        x[i] = (a[i][n] - sum(a[i][j] * x[j] for j in range(i + 1, n))) / a[i][i]
    pay = max(len(str(abs(v.denominator))) for r in a for v in r)
    return x, pay

for n in (4, 8, 14):
    t = time.perf_counter(); x, pay = hilbert_kesin(n); t = time.perf_counter() - t
    print(f"Hilbert n={n:2d}: x = {set(x)}, ara degerlerde en uzun payda {pay} basamak, {t*1e3:.1f} ms")

print("22! =", math.factorial(22))
h = sum(Fraction(1, k) for k in range(1, 101))
print("1 + 1/2 + ... + 1/100 =", f"{h.numerator}/{h.denominator}"[:60] + "...")
print("  pay", len(str(h.numerator)), "basamak, payda", len(str(h.denominator)), "basamak, float hali", float(h))
t = time.perf_counter(); s = sum(1.0 / k for k in range(1, 100001)); tf = time.perf_counter() - t
t = time.perf_counter(); h = sum(Fraction(1, k) for k in range(1, 10001)); tk = time.perf_counter() - t
print(f"float ile 100000 terim {tf*1e3:.1f} ms; kesin ile 10000 terim {tk*1e3:.0f} ms, payda {len(str(h.denominator))} basamak")
```

```
$ python3 kesin.py
Hilbert n= 4: x = {Fraction(1, 1)}, ara degerlerde en uzun payda 4 basamak, 0.1 ms
Hilbert n= 8: x = {Fraction(1, 1)}, ara degerlerde en uzun payda 9 basamak, 0.4 ms
Hilbert n=14: x = {Fraction(1, 1)}, ara degerlerde en uzun payda 16 basamak, 1.7 ms
22! = 1124000727777607680000
1 + 1/2 + ... + 1/100 = 14466636279520351160221518043104131447711/278881500918849908...
  pay 41 basamak, payda 40 basamak, float hali 5.187377517639621
float ile 100000 terim 4.3 ms; kesin ile 10000 terim 51 ms, payda 4345 basamak
```

- Hilbert sistemi her boyutta **tam olarak** $x = (1, \dots, 1)$. Pivot seçmeye bile gerek yok: yuvarlama olmadığı için hangi elemanın büyük olduğu önemsiz.
- $22!$ doğru.
- Bedeli son satırlarda. 100 terimlik harmonik toplamın paydası 40 basamak; 10 000 terimde 4345. Float ile terim başına 43 ns, kesin hesapta 5100 ns ve terim eklendikçe artıyor, çünkü her toplama paydaları daha da büyütüyor.

Python bunu nasıl yapıyor? `int` aslında bir **limb dizisi**: Ders 12.2–12.4'te kendimiz yazacağız. `Fraction` ise bir çift `int` ve her işlemden sonra EBOB ile sadeleştirme (Ders 12.6).

---

## 4. Sembolik hesap

Kesin sayıların ötesine geçip **değişkenlerle** hesap yapmak için bir CAS lazım. Açık kaynaklı, Python ile yazılmış SymPy:

```
$ python3 -m venv ortam && ortam/bin/pip install sympy
```

```python
# sembolik.py: SymPy ile birkac klasik islem
from sympy import (symbols, cos, sin, exp, sqrt, limit, series, expand, factor, diff, integrate,
                   solve, simplify, Matrix, Rational, oo, nsimplify, pi, sqrtdenest, det, Symbol, latex)
x = symbols('x')
print("limit((1-cos x)/x^2, x->0) =", limit((1 - cos(x)) / x**2, x, 0))
print("seri:", series((1 - cos(x)) / x**2, x, 0, 6))
print("expand((x+1)^5) =", expand((x + 1)**5))
print("factor(x^4 - 1) =", factor(x**4 - 1))
print("diff(sin(x) e^x) =", diff(sin(x) * exp(x), x))
print("integrate(1/(x^2+1)) =", integrate(1 / (x**2 + 1), x))
print("integrate(e^(-x^2), -oo..oo) =", integrate(exp(-x**2), (x, -oo, oo)))
print("solve(x^2 - 2) =", solve(x**2 - 2, x))
print("sqrt(8) =", sqrt(8), "  sqrt(2)^2 =", sqrt(2)**2, "  sqrt(2)^2 == 2:", sqrt(2)**2 == 2)
print("simplify(sin^2 + cos^2) =", simplify(sin(x)**2 + cos(x)**2))
e = sqrt(5 + 2 * sqrt(6)) - sqrt(2) - sqrt(3)
print("sqrt(5+2 sqrt6) - sqrt2 - sqrt3: simplify ->", simplify(e), "  sqrtdenest ->", sqrtdenest(e))
print("Hilbert 4x4 tersi, ilk satir:", Matrix(4, 4, lambda i, j: Rational(1, i + j + 1)).inv().row(0))
a = symbols('a0:16'); M = Matrix(4, 4, a)
print("genel 4x4 determinant:", len(det(M).as_ordered_terms()), "terim")
a = symbols('a0:36'); M = Matrix(6, 6, a)
print("genel 6x6 determinant:", len(M.det(method='berkowitz').expand().as_ordered_terms()), "terim")
print("nsimplify(0.333333333333333) =", nsimplify(0.333333333333333), "  nsimplify(3.14159265358979) =", nsimplify(3.14159265358979, [pi]))
```

```
$ ortam/bin/python sembolik.py
limit((1-cos x)/x^2, x->0) = 1/2
seri: 1/2 - x**2/24 + x**4/720 + O(x**6)
expand((x+1)^5) = x**5 + 5*x**4 + 10*x**3 + 10*x**2 + 5*x + 1
factor(x^4 - 1) = (x - 1)*(x + 1)*(x**2 + 1)
diff(sin(x) e^x) = exp(x)*sin(x) + exp(x)*cos(x)
integrate(1/(x^2+1)) = atan(x)
integrate(e^(-x^2), -oo..oo) = sqrt(pi)
solve(x^2 - 2) = [-sqrt(2), sqrt(2)]
sqrt(8) = 2*sqrt(2)   sqrt(2)^2 = 2   sqrt(2)^2 == 2: True
simplify(sin^2 + cos^2) = 1
sqrt(5+2 sqrt6) - sqrt2 - sqrt3: simplify -> 0   sqrtdenest -> 0
Hilbert 4x4 tersi, ilk satir: Matrix([[16, -120, 240, -140]])
genel 4x4 determinant: 24 terim
genel 6x6 determinant: 720 terim
nsimplify(0.333333333333333) = 1/3   nsimplify(3.14159265358979) = pi
```

Her satır, sayısal hesabın yapamadığı bir şey:

- Sayısal olarak bozulan limit, **kesin** olarak $1/2$; seri açılımı da hatanın nereden geldiğini gösteriyor: $1/2 - x^2/24 + \dots$
- `factor`, `diff`, `integrate`, `solve`: sonuçlar sayı değil **ifade**.
- $\sqrt{2}^2 = 2$ kesin olarak doğru. `double`'da `sqrt(2) * sqrt(2) == 2` yanlış (Ders 3.14).
- $\sqrt{5 + 2\sqrt{6}} = \sqrt{2} + \sqrt{3}$ gibi iç içe kökleri tanımak için özel algoritmalar gerekiyor (`sqrtdenest`).
- Hilbert matrisinin tersi **tamsayı** girişli. Sayısal hesapta bu bilgi kaybolur.
- `nsimplify` tersini yapıyor: bir ondalık sayıdan "bu büyük olasılıkla $\pi$" diye tahmin. Bu bir sezgi, kanıt değil.

Aynı işlemler diğer sistemlerde (bu sistemleri burada çalıştırmadık, söz dizimleri belgelerinden):

| İşlem | SymPy | Mathematica | Maxima |
| --- | --- | --- | --- |
| Açma | `expand((x+1)**5)` | `Expand[(x+1)^5]` | `expand((x+1)^5);` |
| Çarpanlar | `factor(x**4-1)` | `Factor[x^4-1]` | `factor(x^4-1);` |
| Türev | `diff(sin(x)*exp(x), x)` | `D[Sin[x] Exp[x], x]` | `diff(sin(x)*exp(x), x);` |
| İntegral | `integrate(1/(x**2+1), x)` | `Integrate[1/(x^2+1), x]` | `integrate(1/(x^2+1), x);` |
| Denklem | `solve(x**2-2, x)` | `Solve[x^2 == 2, x]` | `solve(x^2 = 2, x);` |
| Limit | `limit((1-cos(x))/x**2, x, 0)` | `Limit[(1-Cos[x])/x^2, x -> 0]` | `limit((1-cos(x))/x^2, x, 0);` |

---

## 5. Kesinliğin bedeli: ifade patlaması

Genel bir $n \times n$ matrisin determinantı $n!$ terimli: $4 \times 4$'te 24, $6 \times 6$'da 720, $10 \times 10$'da 3.6 milyon. Sayısal Gauss eliminasyonu $O(n^3)$ işlemle **bir sayı** buluyor; sembolik determinant ise $n!$ terimli **bir ifade**. Harmonik toplamın paydası da aynı olgunun sayılardaki yüzü.

Bu, sembolik hesabın temel gerilimi: kesin sonuç ara adımlarda devleşebilir, son sonuç küçük olsa bile (Hilbert tersinin girişleri küçük tamsayılar, ara kesirler değil). Ders 12.8'de polinom EBOB'unda bunun en ünlü örneği olan **katsayı şişmesini** göreceğiz.

---

## 6. Sıfır mı?

Bir CAS'ın en temel sorusu: verilen ifade sıfır mı? $\sqrt{5 + 2\sqrt 6} - \sqrt 2 - \sqrt 3$ için SymPy evet dedi. Genel durumda ne olur?

Daniel Richardson 1968'de gösterdi: $x$, $\pi$, $\ln 2$, toplama, çarpma, $\sin$, $e^x$ ve mutlak değerden kurulan ifadeler için "bu ifade her $x$ için sıfır mı?" sorusuna cevap veren **bir algoritma olamaz**. Karar verilemez; Faz 14'te durma problemiyle aynı aileden olduğunu göreceğiz.

Pratik sonuç: her CAS'ın `simplify` fonksiyonu sezgisel. Bazen sıfır olan bir ifadeyi sadeleştiremez; bu bir hata değil, teoremin gereği. Bu yüzden CAS'lar **kanonik biçimleri** olan alt dünyalarda (polinomlar, kesirler, cebirsel sayılar) çalışmayı tercih eder: orada iki ifade eşitse yazılışları da aynıdır ve sıfır testi kolay (Ders 12.12).

---

## 7. Bu fazın yol haritası

Bir CAS katmanlardan oluşuyor; her katman bir alttakini kullanıyor:

```
  sembolik ifadeler, sadelestirme, turev        12.11 - 12.13
  sonlu cisimler, GF(p)[x]                      12.10
  polinomlar: carpma, bolme, EBOB, FFT          12.7 - 12.9
  kesirler                                      12.6
  modüler aritmetik                             12.5
  buyuk tamsayilar                              12.2 - 12.4
```

En alttan başlıyoruz: hiçbir sınırı olmayan tamsayılar. Ders 12.14'teki mini CAS hepsini bir araya getirecek.

---

## Alıştırmalar

**1** – `sayisal.c`'deki $(1 - \cos x)/x^2$ ifadesini, $1 - \cos x = 2\sin^2(x/2)$ özdeşliğiyle yeniden yaz. $x = 10^{-9}$'da ne verir? Sembolik dönüşüm burada nasıl yardım etti?

**2** – $20!$ 64 bite sığıyor, $21!$ sığmıyor. $n!$'in bit sayısı yaklaşık $\log_2 n!$. Stirling yaklaşımıyla 1000! kaç bittir, kaç 32 bitlik limb gerekir?

**3** – $\sqrt{2}^2 = 2$ sembolik olarak kolay. $\sqrt{2} + \sqrt{3} = \sqrt{5 + 2\sqrt 6}$ eşitliğini elle doğrula.

**4** – Bir CAS'ta `x/x` her zaman `1` olarak sadeleştirilmeli mi? $x = 0$'da ne olur?

**5** – `nsimplify(3.14159265358979, [pi])` neden kanıt değil? Ona `3.14159265358979` yerine `3.1415926535897932385` versen sonuç farklı olabilir mi?

<details>
<summary>Cevaplar</summary>

**1** – $(1 - \cos x)/x^2 = 2\sin^2(x/2)/x^2$. $x = 10^{-9}$'da $\sin(x/2) \approx 5 \times 10^{-10}$, kare $2.5 \times 10^{-19}$, $\times 2 / 10^{-18} = 0.5$: çıkarma kalmadığı için tam doğru sonuç. Sembolik dönüşüm, sayısal olarak tehlikeli bir ifadeyi aynı fonksiyonun güvenli bir yazılışına çevirdi; derleyicilerin `-ffast-math` olmadan yapmadığı türden bir dönüşüm.

**2** – $\log_2 n! \approx n \log_2 n - n \log_2 e + \tfrac12 \log_2(2\pi n) \approx 9966 - 1443 + 6 = 8529$ bit. $8529 / 32 \approx 267$ limb. Ders 12.4'te hesapladığımızda tam olarak 267 limb çıkıyor.

**3** – $(\sqrt 2 + \sqrt 3)^2 = 2 + 2\sqrt 6 + 3 = 5 + 2\sqrt 6$, iki taraf da pozitif olduğundan kökleri eşit.

**4** – $x \neq 0$ için doğru, $x = 0$'da sol taraf tanımsız. Çoğu CAS (SymPy dahil) `x/x`'i `1` yapar ve bu koşulu sessizce düşer: genelde istenen davranış, ama bazen yanlış sonuç kaynağı. Bu "genel konumda doğru" sadeleştirmeler Ders 12.12'nin konusu.

**5** – `nsimplify`, verilen ondalığa yeterince yakın "basit" bir ifade arıyor; 15 basamak, $\pi$'ye yakın ama $\pi$ olmayan sonsuz sayıyla da uyumlu. Daha çok basamak verince aday kümesi daralıyor, ama sonlu sayıda basamak hiçbir zaman eşitliği kanıtlamaz.

</details>

---

## Kaynaklar

- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra* (3. baskı), Cambridge, 2013, Bölüm 1.
- Keith Geddes, Stephen Czapor, George Labahn, *Algorithms for Computer Algebra*, Kluwer, 1992, Bölüm 1–3.
- Daniel Richardson, "Some Undecidable Problems Involving Elementary Functions of a Real Variable", *Journal of Symbolic Logic*, 33(4), 1968.
- Aaron Meurer ve ark., "SymPy: symbolic computing in Python", *PeerJ Computer Science*, 2017.
- David Goldberg, "What Every Computer Scientist Should Know About Floating-Point Arithmetic", *ACM Computing Surveys*, 1991.

**Sıradaki ders:** Büyük tamsayılar 1. `uint32_t` limb dizisi ile temsil, toplama ve çıkarma.
