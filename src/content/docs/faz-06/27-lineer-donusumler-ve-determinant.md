---
title: "6.27 Lineer dönüşümler ve determinant"
description: "Doğrusal dönüşümün tanımı (toplamayı ve skaler çarpmayı korumak); her doğrusal dönüşümün bir matris olması ve sütunların taban vektörlerinin görüntüleri olduğu; 2B'de döndürme, ölçekleme, kaydırma, yansıma ve izdüşüm; bileşkenin matris çarpımı olması; çekirdek, görüntü ve rank–sıfırlık teoremi; determinant: işaretli alan/hacim çarpanı, özellikleri ve det(AB) = det A · det B; kofaktör açılımı (O(n!)) ile eliminasyonun (O(n³)) karşılaştırıldığı C programı; tersinirlik ile det ≠ 0'ın denkliği ve değişken dönüşümü sezgisi."
---

Ders 6.25'te matris–vektör çarpımının "sütunların doğrusal birleşimi" olduğunu ve matris çarpımının tanımının "iki dönüşümün bileşkesi" olduğu için öyle göründüğünü söyledik. Bu ders o sözü açıyor: bir matris, aslında bir **fonksiyon**; uzayı döndüren, geren, büken, ezen bir dönüşüm. Bu bakış açısıyla, Ders 6.26'daki "tersinir", "rank", "tekil" kelimeleri geometrik bir anlam kazanıyor ve **determinant** adında tek bir sayı hepsini özetliyor.

Ders 6.28'de bu fikri tamsayılara taşıyacağız: bir derleyicinin döngü dönüşümleri, döngü indekslerinin uzayında birer doğrusal dönüşüm.

---

## 1. Doğrusal dönüşüm

$V$ ve $W$ aynı cisim üzerinde iki vektör uzayı (Ders 6.25). $T : V \to W$ fonksiyonu **doğrusal**dır:

$$
T(\mathbf{u} + \mathbf{v}) = T(\mathbf{u}) + T(\mathbf{v}), \qquad T(c\mathbf{v}) = c\, T(\mathbf{v}).
$$

Toplamayı ve skaler çarpmayı **koruyor**. Ders 6.21'deki izomorfizm tanımının akrabası: yapıyı koruyan fonksiyon. İkisi birlikte: $T(c_1\mathbf{v}_1 + \dots + c_k\mathbf{v}_k) = c_1 T(\mathbf{v}_1) + \dots + c_k T(\mathbf{v}_k)$. Bir sonuç: $T(\mathbf{0}) = \mathbf{0}$ (çünkü $T(0 \cdot \mathbf{v}) = 0 \cdot T(\mathbf{v})$). Orijini kaydıran bir fonksiyon (örneğin $x \mapsto x + 1$) doğrusal değil.

Örnekler:

- $\mathbb{R}^2$'de döndürme, ölçekleme, yansıma.
- Türev: $(f + g)' = f' + g'$, $(cf)' = cf'$. Polinomlar uzayında doğrusal bir dönüşüm.
- $GF(2)^n$'de: bitlerin herhangi bir permütasyonu (Ders 5.11), sabit bir maskeyle `&`, CRC (Ders 5.19, sıfır başlangıç değeriyle). `^` ile toplamayı koruyan her şey.
- Doğrusal **olmayanlar**: $x \mapsto x^2$, $x \mapsto |x|$, $GF(2)^8$'de AES S-kutusu (bu yüzden güvenli; Ders 6.24).

---

## 2. Her doğrusal dönüşüm bir matristir

**Teorem.** $T : F^n \to F^m$ doğrusalsa, $T(\mathbf{x}) = A\mathbf{x}$ olan tek bir $m \times n$ matris vardır: $A$'nın $j$'inci sütunu $T(\mathbf{e}_j)$.

**Kanıt.** $\mathbf{x} = x_1\mathbf{e}_1 + \dots + x_n\mathbf{e}_n$ (taban, Ders 6.25). Doğrusallıkla $T(\mathbf{x}) = x_1 T(\mathbf{e}_1) + \dots + x_n T(\mathbf{e}_n)$, ve bu tam olarak sütunları $T(\mathbf{e}_j)$ olan matrisin $\mathbf{x}$ ile çarpımı (sütun yorumu). $\blacksquare$

Bir doğrusal dönüşümü bilmek için **sadece taban vektörlerinin nereye gittiğini** bilmek yetiyor; geri kalan her şey doğrusallıktan çıkıyor. $n$ boyutlu sonsuz bir uzayı $n$ vektörle tarif ediyoruz.

$\mathbb{R}^2$'de beş dönüşüm ve taban vektörlerinin görüntüleri:

```
dondurme 30  e1 -> ( 0.87, 0.50)  e2 -> (-0.50, 0.87)  det =  1.00
olcekle 2,3  e1 -> ( 2.00, 0.00)  e2 -> ( 0.00, 3.00)  det =  6.00
kaydirma     e1 -> ( 1.00, 0.00)  e2 -> ( 1.00, 1.00)  det =  1.00
yansima      e1 -> ( 1.00, 0.00)  e2 -> ( 0.00,-1.00)  det = -1.00
izdusum      e1 -> ( 1.00, 0.00)  e2 -> ( 0.00, 0.00)  det =  0.00
```

| Dönüşüm | Matris | Ne yapıyor |
| --- | --- | --- |
| $\theta$ kadar döndürme | $\begin{pmatrix} \cos\theta & -\sin\theta \\ \sin\theta & \cos\theta \end{pmatrix}$ | uzunlukları ve açıları korur |
| ölçekleme | $\begin{pmatrix} 2 & 0 \\ 0 & 3 \end{pmatrix}$ | eksenler boyunca gerer |
| kaydırma (shear) | $\begin{pmatrix} 1 & 1 \\ 0 & 1 \end{pmatrix}$ | kareyi paralelkenara yatırır |
| yansıma | $\begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix}$ | $x$ ekseninde aynalar |
| izdüşüm | $\begin{pmatrix} 1 & 0 \\ 0 & 0 \end{pmatrix}$ | düzlemi $x$ eksenine ezer |

**Bileşke = çarpım.** $S(T(\mathbf{x})) = B(A\mathbf{x}) = (BA)\mathbf{x}$ (birleşme). Önce $T$ sonra $S$ uygulamak, $BA$ matrisi; **sağdan sola** okunuyor, Ders 6.9'daki $g \circ f$ gibi. "Önce döndür sonra ölçekle" ile "önce ölçekle sonra döndür" farklı: matris çarpımının değişmeli olmamasının geometrik anlamı. Bilgisayar grafiğinde bir nesnenin bütün dönüşümleri tek bir matriste birleştirilip her köşeye bir kez uygulanıyor.

### Çekirdek ve görüntü

- **Çekirdek** (kernel): $\ker A = \{\mathbf{x} \mid A\mathbf{x} = \mathbf{0}\}$. Sıfıra ezilen vektörler.
- **Görüntü** (image): $\text{im}\, A = \{A\mathbf{x}\}$, sütunların germesi. Boyutu rank (Ders 6.26).

İzdüşümde çekirdek $y$ ekseni, görüntü $x$ ekseni.

**Teorem (rank–sıfırlık).** $A$, $m \times n$ ise $\dim \ker A + \text{rank}\, A = n$.

Ders 6.26'nın diliyle: pivot sütunları rank'ı, serbest değişkenler çekirdeğin boyutunu veriyor; ikisi birlikte bütün sütunlar. Kaybedilen boyutlar (çekirdek) ve korunan boyutlar (görüntü) toplamı başlangıç boyutu.

$A$ birebir $\iff$ $\ker A = \{\mathbf{0}\}$ (çünkü $A\mathbf{x} = A\mathbf{y} \iff A(\mathbf{x} - \mathbf{y}) = \mathbf{0}$). Kare bir matris için Ders 6.9'daki "birebir $\iff$ örten" sonucu burada da geçerli (boyutlar eşitse): **tersinir** $\iff$ çekirdek sıfır $\iff$ rank $n$.

---

## 3. Determinant

Bir dönüşüm, birim kareyi (2B) ya da birim küpü (3B) bir paralelkenara / paralelyüze götürüyor. Yeni şeklin alanı ya da hacmi, dönüşümün **determinantı**:

$$
\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc.
$$

Tablodaki değerler: döndürme alanı korur ($\det = 1$), ölçekleme $2 \times 3 = 6$ kat büyütür, kaydırma kareyi yatırır ama alanını korur (paralelkenarın tabanı ve yüksekliği aynı), yansıma alanı korur ama **yönü** ters çevirir ($\det = -1$; işaret, saat yönünün değişip değişmediği), izdüşüm her şeyi bir doğruya ezer ($\det = 0$).

Determinantı tanımlayan üç özellik (her biri alan sezgisinden):

1. $\det I = 1$ (birim kare).
2. İki satırın yerini değiştirmek işareti çeviriyor (yön).
3. Her satıra göre doğrusal: bir satırı $c$ ile çarpmak $\det$'i $c$ ile çarpıyor; bir satır iki vektörün toplamıysa $\det$ de toplanıyor.

Bu üç özellik determinantı **tek** türlü belirliyor, ve gerisi onlardan çıkıyor:

- İki satır eşitse $\det = 0$ (yer değiştirince hem aynı kalıyor hem işaret değiştiriyor).
- Bir satıra başka bir satırın katını eklemek $\det$'i **değiştirmiyor** (Ders 6.26'daki 3. satır işlemi; kaydırma gibi).
- Üçgen bir matrisin determinantı köşegeninin çarpımı.
- $\det A = 0 \iff$ satırlar doğrusal bağımlı $\iff$ $A$ tekil.
- $\det(AB) = \det A \cdot \det B$ (alan çarpanları arka arkaya çarpılıyor).
- $\det(A^{-1}) = 1 / \det A$, $\det(A^T) = \det A$.

Programla dördüncüyü deneyelim: $A = \begin{pmatrix} 2 & 1 \\ 1 & 3 \end{pmatrix}$, $B$ 90° döndürme.

```
det A = 5, det B = 1, det AB = 5
```

---

## 4. Determinantı hesaplamak

**Kofaktör açılımı** (Laplace): ilk satıra göre aç; her eleman için o satırı ve sütunu silip kalan $(n-1) \times (n-1)$ matrisin determinantını işaretle çarp.

$$
\det A = \sum_{j=1}^{n} (-1)^{1+j} a_{1j} \det A_{1j}
$$

```c
// kofaktor acilimi: ilk satira gore, O(n!)
static double det_cofactor(double a[][MAXN], int n) {
    if (n == 1) return a[0][0];
    double sub[MAXN][MAXN], d = 0;
    for (int col = 0; col < n; col++) {
        for (int i = 1; i < n; i++)                 // 0. satiri ve col. sutunu sil
            for (int j = 0, k = 0; j < n; j++)
                if (j != col) sub[i - 1][k++] = a[i][j];
        double sign = (col % 2 == 0) ? 1 : -1;
        d += sign * a[0][col] * det_cofactor(sub, n - 1);
    }
    return d;
}
```

Güzel, kısa, özyinelemeli (Ders 2.8). Ve felaket: $T(n) = n \cdot T(n-1) + O(n^2)$, yani $\Theta(n!)$ (Ders 6.14).

**Eliminasyonla**: satır işlemleriyle üst üçgene getir. 3. tip işlemler determinantı değiştirmiyor, her satır değişimi işaretini çeviriyor; sonuç köşegenin (pivotların) çarpımı.

```c
// eliminasyon: pivotlarin carpimi, her satir degisimi isareti cevirir. O(n^3)
static double det_gauss(double a0[][MAXN], int n) {
    double a[MAXN][MAXN]; memcpy(a, a0, sizeof a);
    double d = 1;
    for (int c = 0; c < n; c++) {
        int p = c;
        for (int i = c + 1; i < n; i++) if (fabs(a[i][c]) > fabs(a[p][c])) p = i;
        if (a[p][c] == 0) return 0;
        if (p != c) { for (int j = 0; j < n; j++) { double t = a[c][j]; a[c][j] = a[p][j]; a[p][j] = t; } d = -d; }
        d *= a[c][c];
        for (int i = c + 1; i < n; i++) {
            double f = a[i][c] / a[c][c];
            for (int j = c; j < n; j++) a[i][j] -= f * a[c][j];
        }
    }
    return d;
}
```

Elemanları $-9..9$ arasında rastgele tamsayı matrislerle (`srand(7)`, `rand() % 19 - 9`):

```
n= 3 kofaktor 130 (0.000 s)  gauss 130 (0.000001 s)
n= 7 kofaktor -3.74023e+06 (0.000 s)  gauss -3.74023e+06 (0.000002 s)
n=11 kofaktor 3.96311e+11 (0.582 s)  gauss 3.96311e+11 (0.000002 s)
```

Aynı sonuç, $n = 11$'de yarım milyon kat fark. $n = 20$'de kofaktör açılımı $20! \approx 2.4 \cdot 10^{18}$ işlem, yıllarca; eliminasyon mikrosaniyeler. Ders 6.12'nin büyüme hiyerarşisinin canlı bir örneği: tanımın doğrudan çevirisi her zaman iyi algoritma değil.

(`a[p][c] == 0` testi tam sıfır arıyor; kayan noktada Ders 6.26'daki eşik uyarısı geçerli. Tamsayı matrislerin determinantını **tam** hesaplamak için ya rasyonel sayılar ya da Bareiss algoritması gerekiyor: Ders 6.28'in 4. alıştırması.)

---

## 5. Değişken dönüşümü sezgisi

Determinantın "hacim çarpanı" olması analizde de karşımıza çıkıyor. Bir bölgeyi doğrusal bir dönüşümle başka bir bölgeye taşıdığında, her küçük karecik $|\det A|$ katı alana sahip bir paralelkenara gidiyor. Bir integral değişken değiştirdiğinde $dx\,dy$ yerine $|\det A|\, du\,dv$ geliyor. Doğrusal olmayan dönüşümlerde (kutupsal koordinatlar gibi) her noktada dönüşüm **yerel olarak** doğrusala yakın, ve o yerel matrisin determinantı (Jakobiyen) çarpan: kutupsal koordinatlarda $r$, dolayısıyla $dx\,dy = r\,dr\,d\theta$.

Ders 6.28 için daha önemli bir okuma: tamsayı ızgarasındaki noktaları sayarken. Bir döngü yuvası $(i, j)$ noktalarının bir ızgarasını geziyor. Bir doğrusal dönüşümle yeni indeksler $(i', j') = A(i, j)$ seçersek, $|\det A| = 1$ ise ızgaranın her noktası tam bir noktaya gidiyor ve **hiç nokta kaybolmuyor ya da eklenmiyor**: döngü dönüşümü aynı işi farklı sırada yapıyor. Determinantı $\pm 1$ olan tamsayı matrislerine **unimodüler** denir; bir sonraki dersin konusu.

---

## Alıştırmalar

**1** – $\mathbb{R}^2$'de "önce 90° döndür, sonra $x$ ekseninde aynala" dönüşümünün matrisini iki yoldan bul: (a) taban vektörlerini izleyerek, (b) iki matrisi doğru sırada çarparak. Sonuç hangi doğruya göre bir yansıma?

**2** – $GF(2)^8$'de bir byte'ın bitlerini ters çeviren dönüşüm (Ders 5.11, `reverse`) doğrusal mı? Matrisini yaz. Bir byte'ı **sola döndürmek** (`rotl`)? `x + 1` (mod 256 toplama)?

**3** – $\det \begin{pmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \\ 7 & 8 & 10 \end{pmatrix}$'yi kofaktörle elle, sonra eliminasyonla hesapla. Son elemanı 9 yapınca ne olur, ve bu Ders 6.25'in 1. alıştırmasıyla nasıl bağlantılı?

**4** – $\det(AB) = \det A \det B$'yi rastgele $5 \times 5$ matrislerde programla doğrula. $\det(A + B) = \det A + \det B$ doğru mu?

**5** – Bir üçgenin köşeleri $(x_1, y_1)$, $(x_2, y_2)$, $(x_3, y_3)$. Alanı $\frac12 \left| \det \begin{pmatrix} x_2 - x_1 & x_3 - x_1 \\ y_2 - y_1 & y_3 - y_1 \end{pmatrix} \right|$. Neden? İşaret neyi söylüyor? Bunu kullanarak "$P$ noktası $AB$ doğrusunun solunda mı?" sorusunu tek bir determinantla cevaplayan bir C fonksiyonu yaz (hesaplamalı geometrinin temel testi).

<details>
<summary>Cevaplar</summary>

**1** – (a) 90° döndürme: $\mathbf{e}_1 \to (0, 1)$, $\mathbf{e}_2 \to (-1, 0)$. Sonra aynalama ($y \to -y$): $(0, 1) \to (0, -1)$, $(-1, 0) \to (-1, 0)$. Sütunlar: $\begin{pmatrix} 0 & -1 \\ -1 & 0 \end{pmatrix}$. (b) Aynalama $\cdot$ döndürme $= \begin{pmatrix} 1 & 0 \\ 0 & -1 \end{pmatrix} \begin{pmatrix} 0 & -1 \\ 1 & 0 \end{pmatrix} = \begin{pmatrix} 0 & -1 \\ -1 & 0 \end{pmatrix}$. ✓ Önce uygulanan sağda. Bu, $y = -x$ doğrusuna göre yansıma ($(1, -1)$ sabit kalıyor; $\det = -1$).

**2** – Bit ters çevirme: doğrusal (bitlerin permütasyonu; XOR'u koruyor). Matris, ters köşegeninde 1'ler olan $8 \times 8$ permütasyon matrisi. `rotl`: o da bir permütasyon, doğrusal; matrisi, birimin sütunlarının kaydırılmışı. `x + 1` doğrusal **değil**: $T(0) = 1 \ne 0$; üstelik elde zinciri bitleri birbirine bağlıyor, `+` XOR değil. Ders 6.24'ün dersi tekrar: aynı byte'lar, hangi toplamayı kullandığına göre farklı bir uzay.

**3** – Kofaktör: $1(50 - 48) - 2(40 - 42) + 3(32 - 35) = 2 + 4 - 9 = -3$. Eliminasyon: satırlar $(1, 2, 3)$, $(0, -3, -6)$, $(0, -6, -11)$; sonra $(0, 0, 1)$; köşegen $1 \cdot (-3) \cdot 1 = -3$. ✓ Son eleman 9 olunca satırlar $(1,2,3), (4,5,6), (7,8,9)$: Ders 6.25'teki bağımlı vektörler; $\det = 0$, matris tekil, uzayı bir düzleme eziyor.

**4** – $\det(AB)$ ile $\det A \cdot \det B$ arasındaki fark $10^{-12}$ civarı göreli hata (yuvarlama); eşitlik tutuyor. $\det(A + B) \ne \det A + \det B$ genellikle: determinant her satıra göre doğrusal ama matrisin bütününe göre doğrusal değil. Örnek: $\det(I + I) = \det(2I) = 2^n$, oysa $\det I + \det I = 2$.

**5** – Kenar vektörleri $\mathbf{u} = B - A$, $\mathbf{v} = C - A$; determinant bunların gerdiği paralelkenarın işaretli alanı, üçgen onun yarısı. İşaret, $A \to B \to C$'nin saat yönünün **tersine** mi (pozitif) yoksa saat yönünde mi (negatif) döndüğünü söylüyor.

```c
// > 0: P, A->B'nin solunda; < 0: saginda; 0: dogru uzerinde
static long orient(long ax, long ay, long bx, long by, long px, long py) {
    return (bx - ax) * (py - ay) - (by - ay) * (px - ax);
}
```

Tamsayı koordinatlarla **tam**: bölme yok, sadece çarpma ve çıkarma. Kayan noktada sıfıra yakın değerler yanlış işaret verebilir ve geometri algoritmalarını (dışbükey zarf, üçgenleme) bozar; bu yüzden sağlam geometri kütüphaneleri bu testi tam aritmetikle yapıyor.

</details>

---

## Kaynaklar

- Gilbert Strang, *Introduction to Linear Algebra* (5. baskı), Bölüm 5 (determinantlar) ve 8 (doğrusal dönüşümler).
- Sheldon Axler, *Linear Algebra Done Right* (4. baskı), Bölüm 3: doğrusal dönüşümler, çekirdek, görüntü, rank–sıfırlık.
- 3Blue1Brown, "Essence of Linear Algebra" (video serisi): dönüşüm ve determinantın geometrik sezgisi.
- Jonathan Shewchuk, "Adaptive Precision Floating-Point Arithmetic and Fast Robust Geometric Predicates" (1997): yön testinin sağlam hesaplanması.

**Sıradaki ders:** Tamsayı lineer cebiri. Tamsayı matrisleri, unimodüler dönüşümler, Hermite normal formu, ve derleyicinin döngü dönüşümlerine hazırlık.
