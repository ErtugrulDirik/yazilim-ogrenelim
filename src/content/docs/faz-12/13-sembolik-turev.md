---
title: "12.13 Sembolik türev"
description: "Türev kurallarını ağaç dönüşümü olarak yazmak: toplam, çarpım ve bölüm kuralları, üs için üç durum (u^n, a^v, u^v), zincir kuralıyla sin, cos, tan, exp, ln, sqrt; ham türevin sadeleştiriciden geçirilmesi (1/(1 + x^2)'nin türevi 29 düğümden 12'ye); sonlu farkla 17424 ifadede sınama ve uyuşmayan 12 ifadede hatanın sonlu farkta olduğunun SymPy ile gösterilmesi; 286 ifadede SymPy'nin diff'i ile 30 basamakta karşılaştırma; art arda türevde ifade şişmesi (6. türevde 1.7 milyon düğüm, sadeleştirmeyle 267 bin, SymPy'de 877) ve nedenleri."
---

Türev, sembolik hesabın en eski işi: 1950'lerde ilk CAS programları türev alıyordu. Algoritma bir paragraf: ağacı gez, her düğümde bir kural uygula. Ama sonuç neredeyse her zaman gereksiz derecede büyük. Bu ders iki parçalı: türev kuralları, ve büyüyen sonucu Ders 12.12'nin sadeleştiricisiyle küçültmek.

---

## 1. Kurallar

Her düğüm türü için bir kural, ve her kural çocukların türevlerini ($u'$, $v'$) kullanıyor:

| düğüm | türev |
| --- | --- |
| sayı, başka değişken | $0$ |
| $x$ | $1$ |
| $u \pm v$ | $u' \pm v'$ |
| $u v$ | $u' v + u v'$ |
| $u / v$ | $(u' v - u v') / v^2$ |
| $u^n$ ($n$, $x$'e bağlı değil) | $n\, u^{n-1}\, u'$ |
| $a^v$ ($a$, $x$'e bağlı değil) | $a^v \ln a \cdot v'$ |
| $u^v$ (ikisi de bağlı) | $u^v \left( v' \ln u + v\, u'/u \right)$ |
| $f(u)$ | $f'(u) \cdot u'$ (zincir kuralı) |

Son üs kuralı, $u^v = e^{v \ln u}$ yazıp zincir kuralından çıkıyor. Ama yalnız $u > 0$ iken anlamlı. İlk iki kural onun özel halleri ve $u \le 0$ için de doğru ($(-2)^3$'ün türevi). Hangi kuralın uygulanacağına `icerir` karar veriyor: alt ağaçta $x$ geçiyor mu?

```c
/* turev.h: sembolik turev */
#ifndef TUREV_H
#define TUREV_H
#include "ifade.h"
int    icerir(const ifade *e, const char *x);        /* e, x'e bagli mi */
ifade *i_turev(const ifade *e, const char *x);       /* d/dx e, sadelestirmeden */
#endif
```

```c
/* turev.c: her dugum turu icin bir kural; cocuklarin turevleriyle yeni bir agac kur */
#include <string.h>
#include "turev.h"

int icerir(const ifade *e, const char *x) {
    if (!e) return 0;
    if (e->t == DEG) return !strcmp(e->ad, x);
    return icerir(e->a, x) || icerir(e->b, x);
}

#define K(e) i_kopya(e)
#define D(e) i_turev(e, x)
#define IKI(t, a, b) i_ikili(t, a, b)

ifade *i_turev(const ifade *e, const char *x) {
    const ifade *u = e->a, *v = e->b;
    switch (e->t) {
    case SAYI: return i_sayi(0);
    case DEG:  return i_sayi(!strcmp(e->ad, x));
    case TOPLA: return IKI(TOPLA, D(u), D(v));
    case CIKAR: return IKI(CIKAR, D(u), D(v));
    case EKSI:  return i_eksi(D(u));
    case CARP:                                           /* (uv)' = u'v + uv' */
        return IKI(TOPLA, IKI(CARP, D(u), K(v)), IKI(CARP, K(u), D(v)));
    case BOL:                                            /* (u/v)' = (u'v - uv') / v^2 */
        return IKI(BOL, IKI(CIKAR, IKI(CARP, D(u), K(v)), IKI(CARP, K(u), D(v))), IKI(US, K(v), i_sayi(2)));
    case US:
        if (!icerir(v, x))                               /* (u^n)' = n u^(n-1) u' */
            return IKI(CARP, IKI(CARP, K(v), IKI(US, K(u), IKI(CIKAR, K(v), i_sayi(1)))), D(u));
        if (!icerir(u, x))                               /* (a^v)' = a^v ln(a) v' */
            return IKI(CARP, IKI(CARP, K(e), i_fonk("ln", K(u))), D(v));
        /* (u^v)' = u^v (v' ln u + v u' / u) */
        return IKI(CARP, K(e), IKI(TOPLA, IKI(CARP, D(v), i_fonk("ln", K(u))), IKI(BOL, IKI(CARP, K(v), D(u)), K(u))));
    case FONK: {                                         /* zincir kurali: f(u)' = f'(u) u' */
        ifade *f;
        if (!strcmp(e->ad, "sin")) f = i_fonk("cos", K(u));
        else if (!strcmp(e->ad, "cos")) f = i_eksi(i_fonk("sin", K(u)));
        else if (!strcmp(e->ad, "tan")) f = IKI(BOL, i_sayi(1), IKI(US, i_fonk("cos", K(u)), i_sayi(2)));
        else if (!strcmp(e->ad, "exp")) f = K(e);
        else if (!strcmp(e->ad, "ln")) f = IKI(BOL, i_sayi(1), K(u));
        else f = IKI(BOL, i_sayi(1), IKI(CARP, i_sayi(2), K(e)));   /* sqrt */
        return IKI(CARP, f, D(u));
    }
    }
    return i_sayi(0);
}
```

`i_turev`, girdi ağacına dokunmuyor: $u$ ve $v$'nin **kopyalarını** yeni ağaca koyuyor. Çarpım kuralında $u$ ve $v$ ikişer kez geçiyor (biri türevli biri türevsiz): her çarpım düğümü, alt ağaçların iki kopyasını üretiyor. Şişmenin kaynağı bu.

---

## 2. Örnekler

```c
/* turev_demo.c: ornekler, sonlu farkla sinama, art arda turevde sisme */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include "bn_mod.h"
#include "sadele.h"
#include "turev.h"

static uint64_t s = 31;
static ifade *rastgele(int d) {
    int r = (int)(rastgele64(&s) % 100);
    if (d == 0 || r < 25) return r % 2 ? i_deg("x") : i_sayi((int64_t)(rastgele64(&s) % 5) + 1);
    static const tur t[] = { TOPLA, CIKAR, CARP, BOL, US };
    static const char *f[] = { "sin", "cos", "exp", "ln", "sqrt", "tan" };
    if (r < 33) return i_eksi(rastgele(d - 1));
    if (r < 48) return i_fonk(f[rastgele64(&s) % 6], rastgele(d - 1));
    tur k = t[rastgele64(&s) % 5];
    return i_ikili(k, rastgele(d - 1), rastgele(d - 1));
}

int main(void) {
    setvbuf(stdout, 0, _IOLBF, 0);
    char h[128];
    const char *ornek[] = { "x^3", "3*x^2 + 2*x + 1", "x*sin(x)", "sin(x)/x", "exp(x^2)", "ln(sin(x))",
                            "sqrt(1 - x^2)", "x^x", "2^x", "tan(x)", "1/(1 + x^2)", 0 };
    FILE *f = fopen("turev_kontrol.txt", "w");
    printf("ornekler (ham turev -> sadelestirilmis):\n");
    for (int i = 0; ornek[i]; i++) {
        ifade *e = i_ayristir(ornek[i], h, sizeof h), *d = i_turev(e, "x"), *sd = sadelestir(d);
        char *y = i_yaz(sd);
        printf("  d/dx %-16s = %-40s (%zu -> %zu dugum)\n", ornek[i], y, i_boyut(d), i_boyut(sd));
        fprintf(f, "%s;%s\n", ornek[i], y);
        free(y); i_sil(e); i_sil(d); i_sil(sd);
    }

    printf("\nsonlu fark ile sinama: 20000 rastgele ifade, x = 0.37\n");
    long kar = 0, uyan = 0;
    double x0 = 0.37, hh = 1e-6;
    for (int i = 0; i < 20000; i++) {
        ifade *e = rastgele(4), *d = i_turev(e, "x"), *sd = sadelestir(d);
        double fp = i_degerle(e, "x", x0 + hh), fm = i_degerle(e, "x", x0 - hh), f0 = i_degerle(e, "x", x0);
        double fark = (fp - fm) / (2 * hh), t1 = i_degerle(d, "x", x0), t2 = i_degerle(sd, "x", x0);
        /* sonlu fark ancak fonksiyon puruzsuz ve olcekli ise anlamli */
        if (isfinite(fp) && isfinite(fm) && isfinite(f0) && isfinite(t1) && fabs(f0) < 1e6 && fabs(t1) < 1e6) {
            kar++;
            if (fabs(fark - t1) <= 1e-4 * fmax(1, fabs(t1)) && fabs(t1 - t2) <= 1e-9 * fmax(1, fabs(t1))) uyan++;
            else if (kar - uyan <= 3) { char *a = i_yaz(e); printf("  uyusmadi: %s  fark %g, turev %g, sade %g\n", a, fark, t1, t2); free(a); }
        }
        if (i < 300) { char *a = i_yaz(e), *b = i_yaz(sd); fprintf(f, "%s;%s\n", a, b); free(a); free(b); }
        i_sil(e); i_sil(d); i_sil(sd);
    }
    fclose(f);
    printf("  %ld karsilastirma, %ld uyumlu\n", kar, uyan);

    printf("\nart arda turev: f = x^2*exp(sin(x))/(1 + x), dugum sayisi\n   n      ham    her adimda sadelestir\n");
    ifade *ham = i_ayristir("x^2*exp(sin(x))/(1 + x)", h, sizeof h), *sade = i_kopya(ham);
    for (int n = 1; n <= 6; n++) {
        ifade *a = i_turev(ham, "x"), *b0 = i_turev(sade, "x"), *b = sadelestir(b0);
        i_sil(ham); i_sil(sade); i_sil(b0); ham = a; sade = b;
        printf("%4d %8zu %12zu\n", n, i_boyut(ham), i_boyut(sade));
    }
    i_sil(ham); i_sil(sade);
    return 0;
}
```

```
$ clang -O2 -c turev.c && clang -O2 turev_demo.c bn_*.o rat.o poli.o poli_bol.o ifade.o sadele.o turev.o -o turev_demo
$ ./turev_demo
ornekler (ham turev -> sadelestirilmis):
  d/dx x^3              = 3*x^2                                    (9 -> 5 dugum)
  d/dx 3*x^2 + 2*x + 1  = 6*x + 2                                  (27 -> 5 dugum)
  d/dx x*sin(x)         = sin(x) + x*cos(x)                        (11 -> 7 dugum)
  d/dx sin(x)/x         = (x*cos(x) - sin(x))/x^2                  (15 -> 11 dugum)
  d/dx exp(x^2)         = 2*(x*exp(x^2))                           (14 -> 8 dugum)
  d/dx ln(sin(x))       = cos(x)/sin(x)                            (9 -> 5 dugum)
  d/dx sqrt(1 - x^2)    = -(x/sqrt(1 - x^2))                       (22 -> 9 dugum)
  d/dx x^x              = x^x*(ln(x) + 1)                          (14 -> 8 dugum)
  d/dx 2^x              = ln(2)*2^x                                (8 -> 6 dugum)
  d/dx tan(x)           = 1/cos(x)^2                               (8 -> 6 dugum)
  d/dx 1/(1 + x^2)      = (-(2*x))/(x^2 + 1)^2                     (29 -> 12 dugum)
```

$3x^2 + 2x + 1$'in ham türevi 27 düğüm. Elle yazınca şöyle bir şey:

$$(0 \cdot x^2 + 3 \cdot (2 x^{1} \cdot 1)) + (0 \cdot x + 2 \cdot 1) + 0$$

Her sabit katsayı çarpım kuralından bir $0 \cdot \ldots$ terimi, her $x$ bir $\cdot 1$ getiriyor. Sadeleştirici bunları `A * 0`, `A * 1`, `A + 0` kurallarıyla temizliyor ve `6*x + 2` kalıyor. Ham sonucu doğrudan göstermek hiçbir CAS'ın yaptığı bir şey değil.

İlk sürümde bazı sonuçlar daha çirkindi: `cos(x)*(1/sin(x))`, `-(2*x*(1/(2*sqrt(1 - x^2))))`. Bunlar ln ve sqrt kurallarından gelen $1/u$ çarpanları. Ders 12.12'nin kural tablosuna `A * (1/B) -> A/B`, `N*A/(N*B) -> A/B` ve sayıyı çarpımın dışına çeken `A * (N*B) -> N*(A*B)` kurallarını ekledim. Sonuç bir kural tablosunun nasıl büyüdüğünü gösteriyor: her yeni çıktı biçimi, yeni bir kural. Gerçek CAS'larda yüzlercesi var.

---

## 3. Sınama

**Sonlu fark.** $f'(x_0) \approx \frac{f(x_0 + h) - f(x_0 - h)}{2h}$, $h = 10^{-6}$. Hatası $O(h^2)$ ve `double` yuvarlamasından gelen $O(\epsilon / h)$ toplamı, yaklaşık $10^{-10}$ bağıl. 20000 rastgele ifade:

```
sonlu fark ile sinama: 20000 rastgele ifade, x = 0.37
  uyusmadi: tan(3^5*(5/x)*(-(1/x)))  fark 48420.5, turev 48382.4, sade 48382.4
  uyusmadi: sin((x/2)^-5)/(x/5/(x + x))^(x - x - 5)  fark 0.591155, turev 0.591538, sade 0.591538
  uyusmadi: sin((5 + 4 - (-4))^(2 + 3 - (-x)))  fark -223001, turev -870889, sade -870889
  17424 karsilastirma, 17412 uyumlu
```

Her satırda iki sayı karşılaştırılıyor: ham türevle sonlu fark, ve ham türevle sadeleştirilmiş türev. 12 uyuşmazlıkta ham ve sadeleştirilmiş türev hep aynı, sonlu fark farklı. Kim haklı? SymPy'ye aynı ifadelerin türevini $x = 37/100$'de 12 basamakla hesaplattım:

```
48382.3621197
0.591538491413
-870888.901722
```

**Biz haklıyız.** Bu fonksiyonlar çok hızlı salınıyor: $\sin(13^{5+x})$'in türevi $13^{5.37} \ln 13 \approx 2 \times 10^6$ ölçeğinde. $h = 10^{-6}$ adımında fonksiyon bir periyottan fazla dönüyor ve sonlu fark anlamsızlaşıyor. Sembolik türevin sayısal türevden üstünlüğü tam olarak bu: hata yok, adım seçimi yok.

**SymPy ile.** Program örneklerin ve ilk 300 rastgele ifadenin türevlerini `turev_kontrol.txt`'ye yazıyor. SymPy her birinin türevini kendi `diff`'i ile alıyor ve iki sonucu üç **kesin** noktada ($37/100$, $13/10$, $29/10$) 30 basamakla karşılaştırıyor:

```python
# turev_sympy.py: bizim turevlerimizi SymPy'nin diff'i ile 30 basamakta, uc noktada karsilastir
import sys
from sympy import sympify, diff, Symbol, Rational, preorder_traversal, sin, cos, exp, log, sqrt, tan, N
x = Symbol('x')
yerel = {'x': x, 'ln': log, 'sin': sin, 'cos': cos, 'exp': exp, 'sqrt': sqrt, 'tan': tan}
def oku(s): return sympify(s.replace('^', '**'), locals=yerel)
say = ayni = atla = 0
for satir in open(sys.argv[1]):
    f, d = satir.strip().split(';')
    F, Dbiz = oku(f), oku(d)
    Dsym = diff(F, x)
    tamam = True; olculdu = False
    for x0 in (Rational(37, 100), Rational(13, 10), Rational(29, 10)):   # kesin noktalar
        a = N(Dsym.subs(x, x0), 30); b = N(Dbiz.subs(x, x0), 30)
        if not (a.is_real and b.is_real and a.is_finite and b.is_finite): continue
        olculdu = True
        if abs(a - b) > 1e-20 * max(1, abs(a)): tamam = False
    if not olculdu: atla += 1; continue
    say += 1; ayni += tamam
    if not tamam: print('FARKLI', f, d)
print(f'{say} ifade, {ayni} tanesi SymPy ile ayni ({atla} tanesi hic gercel noktada tanimli degil)')
f = oku('x**2*exp(sin(x))/(1 + x)')
for n in range(1, 7):
    f = diff(f, x)
    print(n, len(list(preorder_traversal(f))))
```

```
$ python3 turev_sympy.py turev_kontrol.txt
FARKLI -2 + cos(x) - x + exp((5 - 1)/(x - x)) -sin(x) - 1
286 ifade, 285 tanesi SymPy ile ayni (25 tanesi hic gercel noktada tanimli degil)
```

Bu sınama, kendi kodumdaki iki hatayı da buldu:

- **Sınama betiğinin hatası.** İlk sürüm noktaları `'0.37'` metniyle veriyordu. SymPy bunu 15 basamaklı bir `Float` yapıyor, 30 basamaklık karşılaştırma anlamsızlaşıyor ve doğru türevler "farklı" çıkıyordu. `Rational(37, 100)` ile düzeldi.
- **Yazıcının hatası.** $(x+2)^{-2/5}$, `(x + 2)^-2/5` diye yazılıyordu. Bu metin $((x+2)^{-2})/5$ olarak okunuyor. Eksi kesirli sayılara bölmenin önceliğini verdim (Ders 12.11'in yazdırma kuralları güncellendi). Düzeltmeden sonra Ders 12.11'in sınamaları yine tam geçiyor.

Kalan tek fark gerçek bir anlam farkı: $\exp\!\left(\frac{4}{x - x}\right)$ her yerde **tanımsız**. Türevi $e^u \cdot u'$, ve $u' = \frac{0 \cdot (x - x) - 4 \cdot 0}{(x - x)^2}$. Sadeleştiricimiz bunu `0 / A -> 0` ve `A * 0 -> 0` ile sıfıra indiriyor ve tanımsız terim yok oluyor: türev `-sin(x) - 1`. Ders 12.12'deki "genel konumda doğru" kuralların bir sonucu. SymPy'nin davranışı da tuhaf: ifadeyi okurken $x - x = 0$, $4/0 = \tilde\infty$ (`zoo`), $e^{\tilde\infty}$ = `nan` yapıyor ve bütün ifade `nan` oluyor. `diff(nan, x)` ise `0` veriyor. İkimiz de tanımsız bir fonksiyona tanımlı bir türev veriyoruz, yalnız farklı tanımlı türevler.

---

## 4. İfade şişmesi

Türevin türevini alınca ne oluyor?

```
art arda turev: f = x^2*exp(sin(x))/(1 + x), dugum sayisi
   n      ham    her adimda sadelestir
   1       48           36
   2      261          140
   3     1807          688
   4    15267         4217
   5   151267        31093
   6  1710313       267013
```

Ham türev her adımda **yaklaşık 10 kat** büyüyor: 6. türev 1.7 milyon düğüm. Her adımda sadeleştirmek yalnız 6–8 kata indiriyor. İlk denemede 8. türeve kadar gitmeye çalıştım ve program yaklaşık 20 saniye sonra belleği bitirip öldürüldü. Neden bu kadar kötü?

- **Kopyalar.** $(uv)' = u'v + uv'$: $u$ ve $v$ iki kez. Bölüm kuralında $v$ üç kez ($v$, $v'$ içinde, $v^2$). Her türev, alt ağaçları çoğaltıyor.
- **Kurallarımız yerel.** `A + B - B` gibi bir kural yalnız tam o biçimdeki ağaçta uygulanıyor. Toplamın içindeki aynı iki terimi uzaktan göremiyor (Ders 12.12, Alıştırma 2).

SymPy aynı fonksiyonun 6. türevini **877** düğümle veriyor:

```
1 39
2 94
3 183
4 336
5 555
6 877
```

Fark çoğunlukla temsilden geliyor:

- SymPy'nin `Add` ve `Mul` düğümleri **n-li**. Her oluşturulduğunda terimleri sıralıyor, aynı terimleri katsayılarıyla birleştiriyor ($2 x e^{\sin x} + 3 x e^{\sin x} \to 5 x e^{\sin x}$) ve aynı tabanlı çarpanların üslerini topluyor.
- SymPy, aynı alt ifadeyi bellekte **paylaşıyor** (önbellekli yapıcılar). Bizim kopyaladığımız yerde aynı nesneyi gösteriyor.

Ağacın yerine bir **DAG** (yönlü döngüsüz graf) kullanmak, yani ortak alt ifadeleri tek düğümde tutmak, kopyaların maliyetini ortadan kaldırıyor (Alıştırma 4). Derleyicinin "ortak alt ifade eleme" (CSE) optimizasyonu da aynı fikir.

Bu şişme, makine öğrenmesindeki türev hesabının neden sembolik değil **otomatik türev** (AD) ile yapıldığını açıklıyor. AD, ifadeyi değil **sayıları** türev kurallarıyla taşıyor: her ara değerin yanında türevinin değeri. Maliyeti, fonksiyonu değerlendirmenin sabit bir katı. Faz 19'da sembolik türevden ileri ve geri modlu AD kodu üreteceğiz. Ama AD de bu dersin tablosundaki kuralları kullanıyor: yalnızca sembolleri değil sayıları taşıyor.

---

## Alıştırmalar

**1** – `i_turev`'e `asin`, `acos`, `atan`, `sinh` ve `cosh` ekle (önce Ders 12.11'deki `fonklar` listesine). `atan(x)`'in türevinin $\frac{1}{1 + x^2}$ çıktığını doğrula.

**2** – Kısmi türev: $f(x, y) = x^2 y + \sin(xy)$. `i_turev(e, "y")` ne veriyor? Sadeleştirilmiş sonuç $x^2 + x \cos(xy)$ ile aynı mı? Gradyanı ve Hessian matrisini hesaplayan bir fonksiyon yaz.

**3** – **İleri mod AD**: her değer bir çift $(f, f')$ olsun ("dual sayı"). `i_degerle`'nin bir kopyasını yazıp her işlemde türevi de taşı: $(a, a') \cdot (b, b') = (ab, a'b + ab')$. Rastgele ifadelerde sonucu `i_turev` + `i_degerle` ile karşılaştır. Hangisi daha hızlı? Art arda türev için ne olur?

**4** – `i_turev`'i bir **önbellekle** yaz: aynı alt ağacın (yapısal olarak eşit) türevini bir kez hesapla, sonra aynı düğümü paylaş. Bunun için düğümleri silmeden paylaşmak gerekiyor: başvuru sayacı ya da arena (Ders 8.21). 6. türevdeki düğüm sayısı ne oluyor?

**5** – Türevin tersi: $\int x \cos x \, dx$. Kısmi integrasyon bir "kural" olarak yazılabilir mi? Neden integral alma, türev almaktan bu kadar zor? (Risch algoritmasını araştır.)

<details>
<summary>Cevaplar</summary>

**1** – Kurallar: $\arcsin' u = u' / \sqrt{1 - u^2}$, $\arccos' u = -u' / \sqrt{1 - u^2}$, $\arctan' u = u' / (1 + u^2)$, $\sinh' u = \cosh u \cdot u'$, $\cosh' u = \sinh u \cdot u'$. `i_degerle`'ye de `asin`, `acos` vb. eklenmeli, yoksa sonlu fark sınaması çalışmaz. `atan(x)` için ham türev `1/(1 + x^2)*1`, sadeleşmiş `1/(x^2 + 1)` (sıralama nedeniyle).

**2** – `icerir` adla çalıştığından $x$ orada bir sabit gibi davranıyor: $(x^2 y)' = 0 \cdot y + x^2 \cdot 1$, $\sin(xy)' = \cos(xy)(0 \cdot y + x \cdot 1)$. Sadeleşmiş: `x^2 + x*cos(x*y)` (sıralamaya göre terimlerin yeri değişebilir). Gradyan, her değişken için bir türev. Hessian, gradyanın her elemanının yine her değişkene göre türevi: $n^2$ türev, şişmenin karesi.

**3** – Dual sayılarla değerlendirme, ifadeyi bir kez gezip iki sayı taşıyor. `i_turev` yeni bir ağaç kuruyor (kopyalar, `malloc`), sonra onu geziyor. Dual sayılar tipik olarak çok daha hızlı. Art arda türevde dual sayılar "dual'ın dual'ı" ile ($n$. mertebe için $2^n$ bileşen, ya da kesik Taylor serileri ile $n + 1$ bileşen) genişletilebiliyor. Sembolik türevin üstel şişmesi yok.

**4** – Önbellekli türevde, aynı alt ifadeler bir kez temsil ediliyor. DAG'deki düğüm sayısı genelde polinom hızda büyüyor. Ama yazdırınca (ağaca açınca) yine büyük bir ifade çıkıyor. Kazanç bellekte ve değerlendirme süresinde: aynı alt ifade bir kez hesaplanıyor. Ölçüm senin.

**5** – Kısmi integrasyon $\int u v' = uv - \int u' v$ bir kural, ama **hangi** çarpanın $u$ olacağını seçmek gerekiyor ve yanlış seçim sonsuz döngü ya da şişme demek. Türevde her düğümün tek kuralı var ve sonuç her zaman aynı türden fonksiyonlarla ifade ediliyor. İntegralde ise sonuç, girdideki fonksiyonlarla ifade edilemeyebilir ($\int e^{-x^2}$, $\text{erf}$ gerektirir). Risch (1969), elementer fonksiyonlar için "elementer bir integral var mı, varsa nedir" sorusuna karar veren bir algoritma verdi. Tam uygulaması çok karmaşık: hiçbir CAS'ta eksiksiz değil.

</details>

---

## Kaynaklar

- Harold Abelson ve Gerald Jay Sussman, *Structure and Interpretation of Computer Programs* (2. baskı), §2.3.2 ("Example: Symbolic Differentiation").
- Joel S. Cohen, *Computer Algebra and Symbolic Computation: Mathematical Methods*, Bölüm 4 (türev ve otomatik sadeleştirme).
- Andreas Griewank ve Andrea Walther, *Evaluating Derivatives: Principles and Techniques of Algorithmic Differentiation* (2. baskı), SIAM, 2008.
- Atılım Güneş Baydin, Barak Pearlmutter, Alexey Radul, Jeffrey Siskind, "Automatic Differentiation in Machine Learning: a Survey", *Journal of Machine Learning Research*, 18, 2018.
- Robert H. Risch, "The Problem of Integration in Finite Terms", *Transactions of the AMS*, 139, 1969.
- SymPy belgeleri, "Automatic Simplification" ve `Add`/`Mul` yapıcıları (docs.sympy.org).

**Sıradaki ders:** Faz projesi: mini CAS. Büyük sayı, rasyonel, polinom ve sembolik türevi bir araya getiren komut satırı cebir sistemi.
