---
title: "6.26 Doğrusal denklem sistemleri"
description: "Ax = b sistemi ve artırılmış matris; çözümü değiştirmeyen üç satır işlemi; Gauss eliminasyonu, basamak biçimi ve geriye yerine koyma; çözüm yok, tek çözüm, sonsuz çözüm durumları ve rank; kısmi pivotlamanın neden şart olduğunu 1e-17 örneğiyle gösteren C kodu; Gauss–Jordan ile ters matris; O(n³) maliyet; aynı algoritmanın GF(p) üzerinde tam aritmetikle çalışması ve üç noktadan geçen polinomu bulan interpolasyon."
---

Ders 6.25'te matrisleri ve matris–vektör çarpımını tanımladık. Bu derste ters soruyu soruyoruz: $A$ ve $\mathbf{b}$ verildiğinde, $A\mathbf{x} = \mathbf{b}$'yi sağlayan $\mathbf{x}$ nedir? İlkokuldan bilinen "iki bilinmeyenli iki denklem" probleminin genel hali, ve bilimsel hesaplamanın en çok çalıştırılan algoritması.

Algoritma 2000 yıllık (Çin, *Dokuz Bölüm*; Avrupa'da Gauss'un adıyla anılıyor), ama makinede doğru çalıştırmak için Faz 3'ün kayan nokta dersleri gerekiyor. Ve aynı algoritma, Ders 6.24'teki sonlu cisimlerde **tam** sonuç veriyor; Reed–Solomon kodlarını çözen de bu.

---

## 1. Sistem ve satır işlemleri

Üç bilinmeyenli üç denklem:

$$
\begin{aligned}
2x + y - z &= 8 \\
-3x - y + 2z &= -11 \\
-2x + y + 2z &= -3
\end{aligned}
\qquad\Longleftrightarrow\qquad
\left[\begin{array}{ccc|c}
2 & 1 & -1 & 8 \\
-3 & -1 & 2 & -11 \\
-2 & 1 & 2 & -3
\end{array}\right]
$$

Sağdaki **artırılmış matris** $[A \mid \mathbf{b}]$: katsayılar ve sağ taraf, değişken adları olmadan. Ders 6.25'in sütun yorumuyla soru: $\mathbf{b}$, $A$'nın sütunlarının hangi doğrusal birleşimi?

Çözümü değiştirmeyen üç **satır işlemi**:

1. İki satırın yerini değiştir.
2. Bir satırı sıfır olmayan bir sayıyla çarp.
3. Bir satıra başka bir satırın katını ekle.

Her biri tersine çevrilebilir (değiştir–geri değiştir, $c$ ile çarp–$\frac1c$ ile çarp, $f$ katını ekle–$f$ katını çıkar); dolayısıyla eski sistemin her çözümü yenisinin de çözümü, ve tersi. İkincisi bir **cisim** gerektiriyor ($\frac1c$ olmalı): $\mathbb{Z}$ üzerinde eliminasyon yapamamamızın sebebi bu, ve Ders 6.28'in konusu.

---

## 2. Gauss eliminasyonu

Hedef **basamak biçimi** (echelon form): her satırın ilk sıfır olmayan elemanı (**pivot**) bir öncekinin sağında, pivotların altı sıfır. Yöntem: sütun sütun ilerle; sütunda bir pivot seç, altındaki her satırdan pivot satırının uygun katını çıkar (işlem 3) ki o sütun sıfırlansın.

```c
#define N 8

// [A | b] artirilmis matrisini basamak bicimine getirir; rank'i dondurur.
// Kismi pivotlama: her sutunda mutlak degeri en buyuk elemani pivot sec.
static int gauss(double M[][N + 1], int rows, int cols) {
    int r = 0;
    for (int c = 0; c < cols && r < rows; c++) {
        int piv = r;
        for (int i = r + 1; i < rows; i++)
            if (fabs(M[i][c]) > fabs(M[piv][c])) piv = i;
        if (fabs(M[piv][c]) < 1e-12) continue;              // bu sutunda pivot yok
        for (int j = 0; j <= cols; j++) { double t = M[r][j]; M[r][j] = M[piv][j]; M[piv][j] = t; }
        for (int i = r + 1; i < rows; i++) {
            double f = M[i][c] / M[r][c];
            for (int j = c; j <= cols; j++) M[i][j] -= f * M[r][j];   // satir_i -= f * satir_r
        }
        r++;
    }
    return r;
}
```

Basamak biçiminde son denklem tek bilinmeyenli; çöz, bir üstteki denkleme yerine koy, yukarı doğru devam et (**geriye yerine koyma**):

```c
// ust ucgen sistemi geriye dogru coz (rank == n varsayimi)
static void back_sub(double M[][N + 1], int n, double *x) {
    for (int i = n - 1; i >= 0; i--) {
        double s = M[i][n];
        for (int j = i + 1; j < n; j++) s -= M[i][j] * x[j];
        x[i] = s / M[i][i];
    }
}
```

```
rank = 3, basamak bicimi:
  [  -3.000  -1.000   2.000 | -11.000 ]
  [  -0.000   1.667   0.667 |   4.333 ]
  [   0.000   0.000   0.200 |  -0.200 ]
x = (2, 3, -1)
```

Son satır $0.2z = -0.2$, $z = -1$. Yukarı: $1.667y + 0.667 \cdot (-1) = 4.333$, $y = 3$. En üst: $x = 2$. Kontrol: $2 \cdot 2 + 3 - (-1) = 8$. ✓ (`-0.000`, Ders 3.13'teki negatif sıfır: $0 \cdot$ negatif bir sayıdan çıkan.)

### Maliyet

$c$'inci sütunu sıfırlamak, $(n - c)$ satırın her birinde $(n - c)$ eleman güncellemek. Toplam $\sum_c (n - c)^2 \approx \frac{n^3}{3}$ (Ders 6.10'daki kareler toplamı). $\Theta(n^3)$; geriye yerine koyma ise $\Theta(n^2)$. 1000 bilinmeyen için kabaca $3 \cdot 10^8$ işlem, bir saniyenin altında.

---

## 3. Rank ve çözüm sayısı

Eliminasyondan sonra pivot sayısı, matrisin **rank**'ı: doğrusal bağımsız satır (ve sütun) sayısı, Ders 6.25'teki "germe"nin boyutu.

Ders 6.25'in 1. alıştırmasındaki vektörler, bir sistem olarak:

```
tekil sistem rank = 2
  [   7.000   8.000   9.000 |  24.000 ]
  [   0.000   0.857   1.714 |   2.571 ]
  [   0.000   0.000  -0.000 |   0.000 ]
```

Üçüncü satır tamamen sıfır: $0 = 0$. Bir denklem fazlaymış (diğer ikisinin birleşimi). Üç durum:

| Durum | Basamak biçiminde | Çözüm |
| --- | --- | --- |
| rank = bilinmeyen sayısı | her sütunda pivot | **tek** çözüm |
| bir satır $[0 \cdots 0 \mid c]$, $c \ne 0$ | $0 = c$ çelişkisi | **yok** |
| rank < bilinmeyen sayısı, çelişki yok | pivotsuz sütunlar var | **sonsuz** (gerçel sayılarda) |

Son durumda pivotsuz sütunların değişkenleri **serbest**: istediğin değeri ver, pivot değişkenleri onlara göre belirlenir. Yukarıdaki örnekte $z = t$ serbest, $y = 3 - 2t$, $x = t$; her $t$ bir çözüm. $GF(p)$ gibi sonlu bir cisimde "sonsuz" yerine $p^{\text{serbest}}$ çözüm.

Kare bir $A$ ($n \times n$) için rank $n$ ise $A$ **tersinir** (tekil olmayan): her $\mathbf{b}$ için tek çözüm. Ders 6.27'de bunun determinantın sıfır olmamasına denk olduğunu göreceğiz.

`1e-12` eşiği bir uyarı: kayan noktada "tam sıfır" diye bir şey yok. Tekil bir matrisin eliminasyonu yuvarlama yüzünden $10^{-16}$ gibi küçük pivotlar üretebilir; onlara bölmek anlamsız dev sayılar verir. Hangi eşiğin doğru olduğu matrise bağlı ve sayısal doğrusal cebirin başlı başına bir konusu (koşul sayısı).

---

## 4. Pivotlama

`gauss` her sütunda mutlak değeri **en büyük** elemanı pivot seçiyor (**kısmi pivotlama**). Neden? Matematikte sıfır olmayan herhangi bir pivot yeter. Makinede yetmiyor:

$$
\begin{aligned}
10^{-17} x + y &= 1 \\
x + y &= 2
\end{aligned}
$$

Gerçek çözüm $x \approx 1$, $y \approx 1$. Pivotsuz (ilk satırı olduğu gibi kullanarak):

```
pivotsuz: x=0 y=1
pivotlu:  x=1 y=1
```

Pivotsuz yolda $f = 1 / 10^{-17} = 10^{17}$; ikinci satır $1 - 10^{17} \to -10^{17}$ olur (1, `double`'ın 53 bitlik hassasiyetinde kaybolur, Ders 3.14). $y = 1$ doğru çıkıyor ama $x = (1 - y) / 10^{-17} = 0$: tamamen yanlış. Pivotlu yolda satırlar yer değiştiriyor, $f = 10^{-17}$, hiçbir bilgi kaybolmuyor.

Kural: küçük bir pivota bölmek çarpanı büyütüyor, büyük çarpan da yuvarlama hatalarını büyütüyor. Kısmi pivotlama çarpanları $|f| \le 1$'de tutuyor. Bu, `double` ile yazılan her eliminasyonun yapması gereken asgari önlem; LAPACK gibi kütüphaneler de varsayılan olarak bunu yapıyor.

---

## 5. Ters matris

$A$ tersinirse $A^{-1}$, $AA^{-1} = I$ olan matris. $A^{-1}$'in $j$'inci sütunu $A\mathbf{x} = \mathbf{e}_j$'nin çözümü (Ders 6.25'in sütun yorumu). $n$ sistemi birden çözmek için $[A \mid I]$'yı eliminasyona sok ve **Gauss–Jordan** ile devam et: pivotların altını değil üstünü de sıfırla, pivotları 1 yap. Sol taraf $I$ olduğunda sağ taraf $A^{-1}$:

$$
[A \mid I] \;\longrightarrow\; [I \mid A^{-1}].
$$

Neden? Her satır işlemi soldan bir matrisle çarpmak; hepsinin çarpımı $E$ ise $EA = I$, yani $E = A^{-1}$, ve sağ taraf $EI = A^{-1}$.

Pratik bir uyarı: $A\mathbf{x} = \mathbf{b}$'yi çözmek için $A^{-1}$'i hesaplayıp $\mathbf{b}$ ile çarpma. Hem üç kat pahalı hem sayısal olarak daha kötü. Tersi açıkça istendiğinde hesapla; sistem çözmek için eliminasyon (ya da onun yeniden kullanılabilir hali, LU ayrışımı) kullan.

---

## 6. Sonlu cisimde eliminasyon

Algoritmanın tek ihtiyacı cisim işlemleri: toplama, çarpma, sıfır olmayan bir elemana bölme. $GF(p)$ bir cisim (Ders 6.24), dolayısıyla eliminasyon orada da çalışıyor; üstelik **tam**: yuvarlama yok, pivotlama sadece sıfır olmayan bir eleman bulmak için.

Ders 6.24'teki iddia: bir cisim üzerinde, $k$ dereceli bir polinom $k + 1$ noktadaki değerleriyle tek türlü belirleniyor. $(1, 6), (2, 17), (3, 34)$ noktalarından geçen $c_0 + c_1 x + c_2 x^2$'yi arıyoruz. Her nokta bir doğrusal denklem:

$$
\begin{pmatrix} 1 & 1 & 1 \\ 1 & 2 & 4 \\ 1 & 3 & 9 \end{pmatrix} \begin{pmatrix} c_0 \\ c_1 \\ c_2 \end{pmatrix} = \begin{pmatrix} 6 \\ 17 \\ 34 \end{pmatrix}
$$

(Satırları $1, x_i, x_i^2$ olan bu matrise **Vandermonde matrisi** denir; $x_i$'ler farklıysa tersinir.) Gauss–Jordan'ı mod $p$'de, bölme yerine Fermat tersiyle (Ders 6.20):

```c
for (int c = 0; c < 3; c++) {
    int piv = c; while (A[piv][c] == 0) piv++;
    for (int j = 0; j < 4; j++) { int64_t t = A[c][j]; A[c][j] = A[piv][j]; A[piv][j] = t; }
    int64_t inv = pw(A[c][c], p - 2, p);
    for (int j = 0; j < 4; j++) A[c][j] = A[c][j] * inv % p;          // pivotu 1 yap
    for (int i = 0; i < 3; i++) if (i != c && A[i][c]) {
        int64_t fct = A[i][c];
        for (int j = 0; j < 4; j++) A[i][j] = ((A[i][j] - fct * A[c][j]) % p + p) % p;
    }
}
```

```
katsayilar mod p: 1 + 2 x + 3 x^2
```

$3x^2 + 2x + 1$: $x = 1 \to 6$, $x = 2 \to 17$, $x = 3 \to 34$. ✓ Reed–Solomon'un kod çözmesi bu hesabın, $GF(2^8)$'de ve hata konumlarını bulan ek adımlarla yapılan hali. Faz 12'de polinom interpolasyonunu eliminasyonsuz, Lagrange formülüyle $O(k^2)$'de yapacağız.

$GF(2)$'de eliminasyon daha da basit: her satır bir bit deseni, satır işlemi tek bir XOR. 64 bilinmeyenli bir sistemin her satırı bir `uint64_t`; Ders 5.20'deki bitset'in en temiz uygulamalarından biri (Alıştırma 5).

---

## Alıştırmalar

**1** – Elle çöz ve programla doğrula: $x + 2y + z = 4$, $2x + 4y + 3z = 9$, $3x + 6y + 5z = 14$. Rank kaç? Çözüm kümesini serbest değişkenle yaz.

**2** – `gauss`'a Gauss–Jordan adımını ekleyerek `bool mat_inverse(const mat *A, mat *inv)` yaz (Ders 6.25'teki `mat`). $A A^{-1}$'in $I$'ya ne kadar yakın olduğunu, en büyük $|(AA^{-1} - I)_{ij}|$ ile ölç. $10 \times 10$ **Hilbert matrisi** ($h_{ij} = \frac{1}{i + j + 1}$) için ne çıkıyor?

**3** – `gauss`'u pivotlamasız bir sürümle karşılaştır: rastgele $100 \times 100$ sistemlerde (bilinen bir $\mathbf{x}$ seçip $\mathbf{b} = A\mathbf{x}$ hesapla) iki yöntemin hatası nedir? Köşegeni küçük ($10^{-10}$) bir matriste?

**4** – $n = 200, 400, 800$ için eliminasyonun süresini ölç. $\Theta(n^3)$ ile uyuşuyor mu? (Her ikiye katlamada süre ~8 kat.)

**5** – $GF(2)$ üzerinde eliminasyon: her denklemi bir `uint64_t` (bit $j$ = $x_j$'nin katsayısı) ve bir sağ taraf biti olarak tut. Satır çıkarma = XOR. Bir **ışıkları kapat** (Lights Out) bulmacasını (5×5 ızgara, bir lambaya basınca kendisi ve komşuları değişir) 25 bilinmeyenli bir sistem olarak kur ve çöz.

<details>
<summary>Cevaplar</summary>

**1** – İkinci satırdan $2 \times$ birinci, üçüncüden $3 \times$ birinci: $z = 1$ ve $2z = 2$. Üçüncüden $2 \times$ ikinci: $0 = 0$. Rank 2, $y$ sütununda pivot yok: $y = t$ serbest. $z = 1$, $x = 4 - 2t - 1 = 3 - 2t$. Çözüm kümesi $\{(3 - 2t, t, 1)\}$, bir doğru. (Programdaki kısmi pivotlama farklı satır sırası seçebilir ama aynı rank'ı ve aynı çözüm kümesini verir.)

**2** – Rastgele iyi koşullu matrislerde hata $10^{-15}$ civarı. Hilbert matrisinde $10 \times 10$ için hata $10^{-4}$ ile $10^{-3}$ arası: koşul sayısı yaklaşık $1.6 \cdot 10^{13}$ ve `double`'ın 16 basamağının 13'ünü yutuyor. Hilbert matrisi tersinir (rank 10) ama "neredeyse tekil"; sayısal doğrusal cebirin klasik zor örneği. Faz 12'deki rasyonel sayılarla (EBOB ile sadeleştirilmiş kesirler) aynı ters **tam** hesaplanabiliyor; tersin elemanları büyük tamsayılar çıkıyor.

**3** – Elemanları $[0, 1]$'de rastgele bir $100 \times 100$ matris, $\mathbf{x} = (1, \dots, 1)$ ile bir ölçüm: pivotsuz sürümün en büyük hatası yaklaşık $3 \cdot 10^{-9}$, pivotlu $7 \cdot 10^{-13}$. Köşegeni $10^{-10}$ yapınca pivotsuz $2 \cdot 10^{-4}$'e çıkıyor, pivotlu yine $3 \cdot 10^{-13}$. Rastgele matrislerde bile pivotsuz yöntem dört basamak kaybediyor; küçük pivotlarda dokuz basamak. Bölüm 4'ün dersi büyük ölçekte.

**4** – $n$ ikiye katlanınca süre 7–9 kat artıyor. Büyük $n$'de 8'in biraz üstüne çıkabiliyor: matris cache'ten taşınca her satır güncellemesi belleği bekliyor (Ders 6.25'teki döngü sırası etkisi). Bloklu (LAPACK tarzı) eliminasyon bu sabiti düşürüyor, $\Theta(n^3)$'ü değil.

**5** – Bilinmeyen $x_k \in \{0, 1\}$: $k$ lambasına basılıyor mu. Lamba $i$'nin son durumu, başlangıç durumu XOR (kendisi ve komşularından basılanların sayısının paritesi). "Hepsini kapat": her $i$ için $\bigoplus_{k \in N(i)} x_k = s_i$. 25 denklem, 25 bilinmeyen.

```c
uint32_t row[25]; uint8_t rhs[25];   // row[i] bit k: k'ya basmak i'yi degistirir mi
// eliminasyon:
int r = 0;
for (int c = 0; c < 25 && r < 25; c++) {
    int piv = -1;
    for (int i = r; i < 25; i++) if ((row[i] >> c) & 1) { piv = i; break; }
    if (piv < 0) continue;
    swap(row[r], row[piv]); swap(rhs[r], rhs[piv]);
    for (int i = 0; i < 25; i++)
        if (i != r && ((row[i] >> c) & 1)) { row[i] ^= row[r]; rhs[i] ^= rhs[r]; }   // tek XOR
    r++;
}
```

5×5'te rank 23: iki serbest değişken var, her çözülebilir durumun 4 çözümü var ve bütün başlangıç durumlarının sadece dörtte biri çözülebilir. Bir satır işlemi 25 bilinmeyeni tek bir XOR ile güncelliyor: Faz 5'in "kelime düzeyinde paralellik" fikri.

</details>

---

## Kaynaklar

- Gilbert Strang, *Introduction to Linear Algebra* (5. baskı), Bölüm 2–3: eliminasyon, ters matris, rank ve çözüm uzayları.
- Lloyd Trefethen & David Bau, *Numerical Linear Algebra*, Ders 20–22: Gauss eliminasyonu, pivotlama ve kararlılık.
- William Press ve diğ., *Numerical Recipes* (3. baskı), §2.1–2.3: Gauss–Jordan ve LU ayrışımı.

**Sıradaki ders:** Doğrusal dönüşümler ve determinant. Bir matrisi uzayı büken bir fonksiyon olarak görmek, ve determinantın hacmi nasıl ölçtüğü.
