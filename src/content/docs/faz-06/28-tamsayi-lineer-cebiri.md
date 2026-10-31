---
title: "6.28 Tamsayı lineer cebiri"
description: "Neden tamsayılar bir cisim değil ve eliminasyonun neden değişmesi gerektiği; tamsayı matrisleri ve kafes (lattice) olarak satır uzayı; unimodüler matrisler (det = ±1) ve tersinin de tamsayı olması; Bézout ile 2×2 unimodüler satır işlemi; Hermite normal formu ve onu hesaplayan C programı; doğrusal Diophantine denklemleri; döngü yuvalarını indeks uzayında nokta kümesi olarak görmek, takas ve çarpıtmanın unimodüler dönüşümler olması, bağımlılık vektörleri ve sözlük sırasında pozitiflik ile dönüşümün geçerliliğini denetleyen kod; polyhedral modele hazırlık."
---

Ders 6.26'daki eliminasyon bir **cisim** istiyordu: bir satırı pivotla bölebilmek için. Ders 6.27'yi bir gözlemle bitirdik: bir derleyicinin döngü indeksleri tamsayı; onları $\frac{1}{3}$ ile çarpamayız, $i = 2.5$ diye bir döngü turu yok. Döngü dönüşümlerini matematiksel olarak konuşabilmek için **tamsayılar üzerinde** doğrusal cebir gerekiyor.

$\mathbb{Z}$ bir halka ama cisim değil (Ders 6.23–6.24): bölme yok. Bu ders, eliminasyonu bölmesiz yapmanın yolunu (Bézout ile, Ders 6.19) ve "tamsayı ızgarasını bozmadan dönüştürmek" için doğru matris sınıfını (unimodüler) kuruyor. Faz 16'daki döngü optimizasyonları ve polyhedral model bunun üzerine oturuyor.

---

## 1. Tamsayı matrisleri ve kafesler

Tamsayı elemanlı bir $A$ matrisinin satırlarının **tamsayı** doğrusal birleşimleri bir **kafes** (lattice) oluşturur:

$$
L(A) = \{c_1 \mathbf{a}_1 + \dots + c_m \mathbf{a}_m \mid c_i \in \mathbb{Z}\}.
$$

(Ders 6.8'deki "kafes" ile isim benzerliği talihsiz bir tesadüf; ikisi farklı kavramlar. Bu ders boyunca "kafes", $\mathbb{Z}^n$'deki düzenli nokta ızgarası anlamında.)

Örnekler: $\mathbb{Z}^2$'nin kendisi, $\mathbf{e}_1, \mathbf{e}_2$ tarafından üretilen kafes. $(2, 0)$ ve $(0, 2)$ ise sadece **çift** koordinatlı noktaları üretiyor; aynı düzlemi gerçel katsayılarla geriyorlar ama tamsayılarla değil. $(2, 1)$ ve $(1, 1)$: $(2,1) - (1,1) = (1, 0)$ ve $(1,1) - (1,0) = (0, 1)$, yani bütün $\mathbb{Z}^2$.

Aynı kafesi birçok farklı taban üretiyor. Tamsayı doğrusal cebirinin ana sorusu: iki taban aynı kafesi ne zaman üretir, ve bir kafesin **kanonik** (tek) bir tabanı var mı? (Ders 6.5'teki kanonik temsil fikri.)

---

## 2. Unimodüler matrisler

Kare bir tamsayı matrisi $U$, $\det U = \pm 1$ ise **unimodüler**dir.

**Teorem.** Kare bir tamsayı matrisinin tersi de tamsayı matrisidir $\iff$ matris unimodülerdir.

**Kanıt.** ($\Rightarrow$) $U$ ve $U^{-1}$ tamsayıysa determinantları tamsayı (determinant tamsayıların çarpım ve toplamı, Ders 6.27) ve $\det U \cdot \det U^{-1} = \det I = 1$. İki tamsayının çarpımı 1 ise ikisi de $\pm 1$. ($\Leftarrow$) Tersin formülü $U^{-1} = \frac{1}{\det U} \text{adj}(U)$, ve ek matris (adjugate) kofaktörlerden oluşuyor, tamsayı. $\det U = \pm 1$ ile bölmek tamsayı veriyor. $\blacksquare$

Unimodüler matrisler, $\mathbb{Z}$ üzerindeki matris halkasının **birimleri** (Ders 6.23): tamsayı dünyasında tersinir olan dönüşümler. Ve Ders 6.27'nin sonundaki sezgi: $|\det| = 1$ hacmi koruyor, dolayısıyla bir unimodüler dönüşüm $\mathbb{Z}^n$'yi **kendisine birebir örten** eşliyor. Hiçbir tamsayı noktası kaybolmuyor, hiçbiri eklenmiyor.

Aynı kafesi üreten iki taban arasındaki geçiş hep unimodüler: $L(A) = L(B) \iff B = UA$, $U$ unimodüler.

### Bölmesiz satır işlemleri

Ders 6.26'daki üç satır işleminin tamsayı karşılıkları:

1. İki satırın yerini değiştir ($\det = -1$).
2. Bir satırı $-1$ ile çarp ($\det = -1$). (2 ile çarpmak yasak: tersi $\frac12$.)
3. Bir satıra başka bir satırın **tamsayı** katını ekle ($\det = 1$).

Bu işlemlerle bir sütunu nasıl sıfırlarız? İki satırın o sütundaki elemanları $a$ ve $b$ olsun. Bézout (Ders 6.19): $xa + yb = g = \text{EBOB}(a, b)$. Şu $2 \times 2$ matrisi iki satıra uygula:

$$
\begin{pmatrix} x & y \\ -b/g & a/g \end{pmatrix} \begin{pmatrix} a \\ b \end{pmatrix} = \begin{pmatrix} g \\ 0 \end{pmatrix}, \qquad \det = \frac{xa + yb}{g} = 1.
$$

Unimodüler, ve sütunu $(g, 0)$'a indiriyor. Bu, Öklid algoritmasının satırlara uygulanmış hali: pivota bölmek yerine iki satırı EBOB'larına "sıkıştırmak".

---

## 3. Hermite normal formu

Bir tamsayı matrisinin **satır Hermite normal formu** (HNF) $H = UA$ ($U$ unimodüler) şu biçimde:

- Basamak biçiminde (Ders 6.26), pivotlar **pozitif**.
- Her pivotun **üstündeki** elemanlar $[0, \text{pivot})$ aralığında.
- Sıfır satırlar en altta.

**Teorem.** Her tamsayı matrisinin HNF'si vardır ve **tektir**.

Teklik önemli: $L(A) = L(B) \iff \text{HNF}(A) = \text{HNF}(B)$. HNF, bir kafesin kanonik adı. İki farklı tabanın aynı kafesi üretip üretmediğini anlamak için ikisinin HNF'sini karşılaştır (Ders 6.21'deki izomorfizm sorununun kafesler için çözümü).

```c
#define R 3
#define C 4

// satir Hermite normal formu: sadece unimodular satir islemleri
//  - iki satiri, determinanti 1 olan 2x2 bir tamsayi matrisle birlestir
//  - pivotu pozitif yap, pivotun ustundekileri [0, pivot) araligina indir
static void hnf(int64_t A[R][C]) {
    int r = 0;
    for (int c = 0; c < C && r < R; c++) {
        for (int i = r + 1; i < R; i++) {
            if (A[i][c] == 0) continue;
            int64_t a = A[r][c], b = A[i][c], x, y;
            int64_t g = ext_gcd(a, b, &x, &y);       // x*a + y*b = g
            int64_t u = a / g, v = b / g;              // [[x, y], [-v, u]], det = x*u + y*v = 1
            for (int j = 0; j < C; j++) {
                int64_t p = A[r][j], q = A[i][j];
                A[r][j] = x * p + y * q;
                A[i][j] = -v * p + u * q;
            }
        }
        if (A[r][c] == 0) continue;                    // bu sutunda pivot yok
        if (A[r][c] < 0) for (int j = 0; j < C; j++) A[r][j] = -A[r][j];
        for (int i = 0; i < r; i++) {                  // ustteki elemanlari indir
            int64_t q = floordiv(A[i][c], A[r][c]);
            for (int j = 0; j < C; j++) A[i][j] -= q * A[r][j];
        }
        r++;
    }
}
```

`ext_gcd` Ders 6.19'dan. `floordiv`, aşağı yuvarlayan tamsayı bölmesi: C'nin `/`'ı sıfıra doğru yuvarlıyor (Ders 6.17) ve negatif elemanlarda $[0, \text{pivot})$ aralığını tutturamıyor.

```
A =
  [    2    3    6    2 ]
  [    5    6    1    6 ]
  [    8    3    1    1 ]
HNF(A) =
  [    1    0   50  -11 ]
  [    0    3   28   -2 ]
  [    0    0   61  -13 ]
```

Kontroller: pivotlar $1, 3, 61$, üstlerindeki elemanlar ($0$; $50, 28$) aralıkta. Pivotların çarpımı $183 = |\det(A\text{'nın ilk 3 sütunu})|$; unimodüler işlemler determinantın mutlak değerini korur. Satırların $\mathbb{Z}$-birleşimleri değişmedi: aynı kafes, kanonik taban.

Bir uyarı: tamsayı eliminasyonunda ara değerler **şişebilir**. Burada küçük kaldılar, ama büyük matrislerde Bézout katsayıları ve satır birleşimleri hızla büyüyor; `int64_t` taşabiliyor. Gerçek uygulamalar ya büyük tamsayılar (Faz 12) ya da ara sonuçları bir determinant katına göre mod alan algoritmalar kullanıyor.

### Doğrusal Diophantine denklemleri

Gerçel sayılarda $A\mathbf{x} = \mathbf{b}$'nin çözümü var mı sorusunu rank cevaplıyordu. Tamsayılarda daha incelikli: $2x + 4y = 3$'ün gerçel çözümü bol, tamsayı çözümü yok (sol taraf hep çift). Tek denklemde cevap Bézout: $a_1 x_1 + \dots + a_n x_n = b$ tamsayı çözümlüdür $\iff$ $\text{EBOB}(a_1, \dots, a_n) \mid b$. Sistemler için HNF (ya da onun daha güçlü kardeşi **Smith normal formu**) aynı soruyu cevaplıyor. Derleyicinin "bu iki dizi erişimi aynı bellek hücresine düşebilir mi?" sorusu (bağımlılık analizi) tam olarak böyle bir tamsayı denklemi: `a[2*i]` ile `a[2*j + 1]` asla çakışmaz, çünkü $2i = 2j + 1$'in tamsayı çözümü yok (**EBOB testi**).

---

## 4. Döngü yuvaları indeks uzayında

İki iç içe döngü:

```c
for (int i = 0; i < n; i++)
    for (int j = 0; j < m; j++)
        S(i, j);
```

$S$'nin her çalışması $\mathbb{Z}^2$'de bir nokta $(i, j)$; döngü yuvası bir dikdörtgendeki tamsayı noktalarını **sözlük sırasıyla** (Ders 6.7) geziyor: önce $i$'ye, eşitse $j$'ye göre.

Bir **döngü dönüşümü**, yeni indeksler seçmek: $(i', j') = T(i, j)$, ve yeni noktaları sözlük sırasıyla gezmek. $T$ unimodülerse her $(i, j)$ tam bir $(i', j')$'ye gidiyor: **aynı işler, farklı sıra**. İki temel dönüşüm:

| Dönüşüm | $T$ | Yeni indeksler |
| --- | --- | --- |
| **Takas** (interchange) | $\begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$ | $(j, i)$: döngüleri yer değiştir |
| **Çarpıtma** (skewing) | $\begin{pmatrix} 1 & 0 \\ 1 & 1 \end{pmatrix}$ | $(i, i + j)$ |

Çarpıtılmış döngü, sınırları yeniden hesaplanarak:

```c
for (int t = 0; t < n; t++)                        // t = i
    for (int s = t; s < t + m; s++) {              // s = i + j
        int i = t, j = s - t;
        S(i, j);
    }
```

```
carpitilmis dongu 12 nokta, her biri bir kez: 1
```

($n = 4$, $m = 3$.) Her $(i, j)$ tam bir kez; $\det T = 1$'in sonucu. Yeni sınırları bulmak, dikdörtgenin $T$ altındaki görüntüsünün (bir paralelkenar) eşitsizliklerini yazmak. Genel durumda bu, Fourier–Motzkin eliminasyonu ile yapılıyor ve **polyhedral model**in özü.

### Ne zaman geçerli?

Sırayı değiştirmek her zaman güvenli değil. Döngünün gövdesi şöyle olsun:

```c
a[i][j] = a[i - 1][j + 1] + a[i][j - 1];
```

$(i, j)$ turu, $(i-1, j+1)$ turunun **yazdığını** okuyor; o tur önce çalışmalı. Fark vektörü $(i, j) - (i - 1, j + 1) = (1, -1)$: bir **bağımlılık vektörü**. Aynı şekilde $a[i][j-1]$'den $(0, 1)$.

Orijinal sırada her bağımlılık vektörü **sözlük sırasında pozitif** (ilk sıfır olmayan bileşeni pozitif): kaynak, hedeften önce çalışıyor. Dönüşüm $T$ geçerli $\iff$ $T\mathbf{d}$ her bağımlılık vektörü $\mathbf{d}$ için hâlâ sözlük sırasında pozitif. (Doğrusallık sayesinde nokta çiftlerinin farkını dönüştürmek yeterli: $T(\mathbf{p}) - T(\mathbf{q}) = T(\mathbf{p} - \mathbf{q})$, Ders 6.27.)

```c
int dep[2][2] = { {1, -1}, {0, 1} };
// her T icin: T*d sozluk sirasinda pozitif mi?
```

```
takas                gecerli: 0
carpitma (i, i+j)    gecerli: 1
(i+j, j)             gecerli: 0
```

Takas $(1, -1)$'i $(-1, 1)$'e götürüyor: bağımlılık **geriye** dönüyor, yanlış sonuç. Çarpıtma $(1, -1) \to (1, 0)$ ve $(0, 1) \to (0, 1)$: ikisi de pozitif, geçerli. Derleyici bir dönüşümü ancak bu denetimden geçerse uyguluyor.

Neden bu kadar uğraş? Doğru seçilmiş bir unimodüler $T$, iç döngünün bütün turlarını **birbirinden bağımsız** yapabiliyor (Alıştırma 4): o döngü SIMD ile vektörleştirilebilir ya da çekirdeklere dağıtılabilir (Faz 10–11). Ya da cache dostu bir sıra elde ediliyor (Ders 6.25'teki döngü sırası, artık bir matris seçimi). Faz 16'da bu fikri bir derleyici geçişi olarak yazacağız.

---

## Alıştırmalar

**1** – $\begin{pmatrix} 2 & 1 \\ 7 & 4 \end{pmatrix}$ unimodüler mi? Tersini bul ve tamsayı olduğunu doğrula. $\begin{pmatrix} 2 & 0 \\ 0 & 1 \end{pmatrix}$'nin tersi neden tamsayı değil, ve $\mathbb{Z}^2$'yi kendisine eşlerken hangi noktalar "kayboluyor"?

**2** – $(4, 6)$ ve $(6, 9)$ vektörlerinin ürettiği kafesin HNF'sini programla bul. Bu kafes, $(2, 3)$'ün tamsayı katlarından ibaret mi? (İpucu: rank.)

**3** – Şu dizi erişim çiftlerinden hangileri aynı hücreye düşebilir? EBOB testiyle karar ver. (a) `a[4*i + 2]` ve `a[6*j + 5]` (b) `a[3*i + 1]` ve `a[6*j + 4]` (c) `a[i + 2*j]` ve `a[2*k + 1]`

**4** – Bölüm 4'teki gövde için $T = \begin{pmatrix} 2 & 1 \\ 1 & 0 \end{pmatrix}$ (**dalga cephesi**: dış döngü $t = 2i + j$) unimodüler ve geçerli mi? Dönüştürülmüş bağımlılıkların ilk bileşenine bak: iç döngünün turları neden birbirinden bağımsız?

**5** – Tamsayı matrisinin determinantını **tam** hesaplamak için Bareiss algoritması: $M^{(k+1)}_{ij} = (M^{(k)}_{kk} M^{(k)}_{ij} - M^{(k)}_{ik} M^{(k)}_{kj}) / M^{(k-1)}_{k-1,k-1}$, ve bölme her zaman tam. Yaz, Ders 6.27'deki rastgele $11 \times 11$ matrislerde `det_gauss` ile karşılaştır. (Pivot sıfırsa satır değiştirmeyi unutma.)

<details>
<summary>Cevaplar</summary>

**1** – $\det = 8 - 7 = 1$, unimodüler. Ters: $\begin{pmatrix} 4 & -1 \\ -7 & 2 \end{pmatrix}$ (2×2 formülü: köşegeni değiştir, diğerlerinin işaretini çevir, $\det$'e böl). Çarpım $I$. ✓ $\begin{pmatrix} 2 & 0 \\ 0 & 1 \end{pmatrix}$'nin tersi $\begin{pmatrix} 1/2 & 0 \\ 0 & 1 \end{pmatrix}$; $\det = 2$. $\mathbb{Z}^2$'yi kendisine eşlerken görüntü sadece ilk koordinatı çift olan noktalar: yarısı "kayıp". Bu dönüşümü bir döngüye uygulasaydın turların yarısına hiç karşılık gelmeyen boş indeksler oluşurdu.

**2** – $(6, 9) - (4, 6) = (2, 3)$, ve $(4, 6) = 2 \cdot (2, 3)$. HNF: $\begin{pmatrix} 2 & 3 \\ 0 & 0 \end{pmatrix}$. Rank 1; kafes $(2, 3)$'ün tamsayı katları. İki vektör aynı doğru üzerinde; HNF'deki sıfır satır bunu gösteriyor.

**3** – (a) $4i + 2 = 6j + 5 \iff 4i - 6j = 3$. $\text{EBOB}(4, 6) = 2 \nmid 3$: **asla** çakışmaz (bir taraf hep çift, öbürü hep tek). (b) $3i - 6j = 3$, $\text{EBOB} = 3 \mid 3$: tamsayı çözümü var ($i = 1$, $j = 0$: `a[4]` ve `a[4]`), çakışabilir. (c) $i + 2j - 2k = 1$, $\text{EBOB}(1, 2, 2) = 1$: çözüm var ($i = 1$, $j = k$). EBOB testi sınırları (döngü aralıklarını) hesaba katmıyor; "çözüm var" deyince gerçekte çakışma olduğu kesin değil, sadece mümkün. Daha kesin testler (Omega testi) tamsayı doğrusal programlama gerektiriyor.

**4** – $\det = 0 \cdot 2 - 1 \cdot 1 = -1$, unimodüler. $T(1, -1) = (2 - 1, 1) = (1, 1)$, $T(0, 1) = (1, 0)$: ikisi sözlük sırasında pozitif, **geçerli**. İki dönüştürülmüş bağımlılığın ilk bileşeni de 1 (kesin pozitif): her bağımlılık bir dış turdan **sonraki** dış tura gidiyor. Aynı $t$ değerindeki (aynı dalga cephesindeki) noktalar arasında hiç bağımlılık yok; iç döngü paralel çalıştırılabilir. Gauss–Seidel ve dinamik programlama tablolarını paralelleştirmenin klasik yolu.

**5** –

```c
// tam determinant, Bareiss; a degistirilir
static int64_t det_bareiss(int64_t a[][MAXN], int n) {
    int64_t prev = 1; int sign = 1;
    for (int k = 0; k < n - 1; k++) {
        if (a[k][k] == 0) {
            int p = k + 1; while (p < n && a[p][k] == 0) p++;
            if (p == n) return 0;
            for (int j = 0; j < n; j++) { int64_t t = a[k][j]; a[k][j] = a[p][j]; a[p][j] = t; }
            sign = -sign;
        }
        for (int i = k + 1; i < n; i++)
            for (int j = k + 1; j < n; j++)
                a[i][j] = (int64_t)(((__int128)a[k][k] * a[i][j]
                                     - (__int128)a[i][k] * a[k][j]) / prev);   // tam bolunur
        prev = a[k][k];
    }
    return sign * a[n - 1][n - 1];
}
```

Her ara değer bir alt determinant, dolayısıyla sonuçtan çok büyümüyor; ama $a_{kk} a_{ij}$ çarpımı geçici olarak iki katı bit istiyor. `int64_t` ile yazınca $11 \times 11$'de bile `-fsanitize=undefined` işaretli taşma yakalıyor; çarpımları `__int128`'de yapınca düzeliyor. Ders 6.27'deki matrisler için sonuçlar $130$, $-3740232$ ve $396311285069$; `det_gauss`'un `double` sonuçları ($-3.74023 \cdot 10^6$, $3.96311 \cdot 10^{11}$) bunların yuvarlanmış hali. Kesin sayımda (Ders 6.14'teki gibi) yuvarlama kabul edilemez; Bareiss bölmeyi tamsayıda tutarak bunu sağlıyor.

</details>

---

## Kaynaklar

- Alexander Schrijver, *Theory of Linear and Integer Programming*, Bölüm 4–5: Hermite ve Smith normal formları, doğrusal Diophantine denklemleri.
- Utpal Banerjee, *Loop Transformations for Restructuring Compilers: The Foundations*: unimodüler dönüşümler ve bağımlılık analizi.
- Michael Wolf & Monica Lam, "A Loop Transformation Theory and an Algorithm to Maximize Parallelism", *IEEE TPDS* 2(4), 1991: unimodüler döngü dönüşümleri çerçevesi.
- Erwin Bareiss, "Sylvester's Identity and Multistep Integer-Preserving Gaussian Elimination", *Mathematics of Computation* 22, 1968.

**Sıradaki ders:** Olasılık temelleri. Koşullu olasılık, beklenen değer, ve rastgele algoritmaların analizi: hash tablosunun beklenen maliyeti.
