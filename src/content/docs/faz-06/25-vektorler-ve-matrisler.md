---
title: "6.25 Vektörler ve matrisler"
description: "Bir cisim üzerinde vektör uzayı aksiyomları; Rⁿ, GF(2)ⁿ bit desenleri ve polinomlar örnekleri; doğrusal birleşim, germe, doğrusal bağımsızlık, taban ve boyut; iç çarpım; matris, matris–vektör ve matris–matris çarpımının tanımı ve 'satır çarpı sütun' yorumu; çarpmanın birleşmeli ama değişmeli olmaması, birim matris; satır öncelikli bellek düzeniyle C'de küçük bir matris kütüphanesi; döngü sırasının (i-j-p ve i-p-j) cache'e etkisi; Fibonacci'yi 2×2 matris kuvvetiyle O(log n) ve tam hesaplamak."
---

Ders 6.24'ü bir sözle bitirdik: bir cisim üzerinde, $k$ dereceli bir polinom $k + 1$ değerle tek türlü belirleniyor ve bunu "doğrusal bir sistem olarak" kanıtlayacağız. Ders 6.11'de iki çözümün doğrusal birleşiminin yine çözüm olduğunu, Ders 6.13'te Strassen'in matris çarpımını gördük. Hepsinin dili **doğrusal cebir**.

Doğrusal cebir derleyici mühendisliğinin en az beklenen yerlerinde çıkıyor: döngü dönüşümleri (Faz 16, ve Ders 6.28'deki tamsayı matrisleri), komut zamanlama, register tahsisi grafının analizi, ve elbette bilimsel hesaplamanın kendisi (Faz 11'deki SIMD, matris çarpımını hızlandırmak için var). Bu ders tanımları ve küçük bir C kütüphanesini kuruyor; sonraki üç ders onu kullanacak.

---

## 1. Vektör uzayı

$F$ bir cisim (Ders 6.24) olsun; elemanlarına **skaler** diyoruz. $F$ üzerinde bir **vektör uzayı** $V$:

- $(V, +)$ değişmeli bir grup (Ders 6.21): vektörleri toplayabiliyoruz, birim $\mathbf{0}$, ters $-\mathbf{v}$.
- Bir **skaler çarpma** $F \times V \to V$, $(c, \mathbf{v}) \mapsto c\mathbf{v}$, şu kurallarla: $c(\mathbf{u} + \mathbf{v}) = c\mathbf{u} + c\mathbf{v}$, $(c + d)\mathbf{v} = c\mathbf{v} + d\mathbf{v}$, $(cd)\mathbf{v} = c(d\mathbf{v})$, $1\mathbf{v} = \mathbf{v}$.

Örnekler:

| Uzay | Vektörler | Skalerler | Not |
| --- | --- | --- | --- |
| $\mathbb{R}^n$ | $n$ gerçel sayının dizisi | $\mathbb{R}$ | geometrik okların uzayı |
| $GF(2)^n$ | $n$ bitlik desenler | $\{0, 1\}$ | toplama XOR; Ders 5.19'daki Hamming kodu bu uzayda |
| $F[x]_{<n}$ | derecesi $n$'den küçük polinomlar | $F$ | katsayılar bir vektör |
| $\{f : \{1..n\} \to F\}$ | fonksiyonlar | $F$ | aslında $F^n$; dizi = fonksiyon (Ders 6.9) |

Hepsi aynı aksiyomlara uyuyor; dolayısıyla bu derste kanıtladığımız her şey bit desenleri için de, polinomlar için de geçerli. Ders 6.21'deki "bir arayüz, çok uygulama" fikri.

---

## 2. Taban ve boyut

$\mathbf{v}_1, \dots, \mathbf{v}_k$ vektörlerinin bir **doğrusal birleşimi**: $c_1\mathbf{v}_1 + \dots + c_k\mathbf{v}_k$. Bütün doğrusal birleşimlerin kümesi bu vektörlerin **germesi** (span).

Vektörler **doğrusal bağımsız**: tek doğrusal birleşimleri sıfır olan, bütün katsayıları sıfır olan.

$$
c_1\mathbf{v}_1 + \dots + c_k\mathbf{v}_k = \mathbf{0} \;\Rightarrow\; c_1 = \dots = c_k = 0
$$

Bağımsız değillerse biri ötekilerin birleşimi olarak yazılabilir: **fazlalık** var.

Bir **taban** (basis): uzayı geren, bağımsız bir vektör kümesi. Her vektör taban vektörlerinin doğrusal birleşimi olarak **tek** türlü yazılır (iki yazılış olsaydı farkları sıfırın sıfır olmayan bir birleşimi olurdu). Katsayılar vektörün **koordinatları**.

**Teorem.** Bir vektör uzayının bütün tabanları aynı sayıda vektör içerir.

Bu sayıya uzayın **boyutu** denir. Kanıt Ders 6.26'daki eliminasyonla kolaylaşıyor; şimdilik kabul edelim.

- $\mathbb{R}^3$'ün olağan tabanı $\mathbf{e}_1 = (1, 0, 0)$, $\mathbf{e}_2$, $\mathbf{e}_3$: boyut 3.
- $GF(2)^{32}$'nin olağan tabanı $1, 2, 4, \dots, 2^{31}$ (tek bitli desenler): boyut 32. Her `uint32_t`, bu taban vektörlerinin XOR'u; koordinatlar bitleri.
- $F[x]_{<n}$'nin tabanı $1, x, x^2, \dots, x^{n-1}$: boyut $n$.

Sonlu bir cisim üzerinde $n$ boyutlu bir uzayda **tam** $|F|^n$ vektör var: her koordinat için $|F|$ seçenek (Ders 6.14, çarpma ilkesi). $GF(2)^{32}$'de $2^{32}$.

### İç çarpım

$\mathbb{R}^n$'de iki vektörün **iç çarpımı** (dot product):

$$
\mathbf{u} \cdot \mathbf{v} = \sum_{i=1}^{n} u_i v_i
$$

$\mathbf{u} \cdot \mathbf{v} = 0$ ise vektörler **dik** (ortogonal). $\mathbf{v} \cdot \mathbf{v} = \|\mathbf{v}\|^2$, uzunluğun karesi. $GF(2)^n$'de iç çarpım `popcount(u & v) & 1` (Ders 5.8'deki parite): Hamming kodunun parite denetimleri tam olarak iç çarpımlar.

---

## 3. Matrisler

$m \times n$ bir **matris** $A$: $m$ satır, $n$ sütun, $a_{ij}$ $i$'inci satır $j$'inci sütundaki eleman. Ders 4.3'teki iki boyutlu dizi.

**Matris–vektör çarpımı**: $A$ ($m \times n$) ve $\mathbf{x} \in F^n$ için $A\mathbf{x} \in F^m$,

$$
(A\mathbf{x})_i = \sum_{j=1}^{n} a_{ij} x_j.
$$

İki yorum, ikisi de önemli:

- **Satır yorumu**: $(A\mathbf{x})_i$, $A$'nın $i$'inci satırı ile $\mathbf{x}$'in iç çarpımı.
- **Sütun yorumu**: $A\mathbf{x} = x_1 \mathbf{a}_1 + \dots + x_n \mathbf{a}_n$, $A$'nın **sütunlarının** doğrusal birleşimi, katsayılar $\mathbf{x}$'ten.

Sütun yorumu Ders 6.27'nin anahtarı: matris, taban vektörlerinin nereye gittiğini söylüyor ($A\mathbf{e}_j = \mathbf{a}_j$).

**Matris–matris çarpımı**: $A$ ($m \times k$), $B$ ($k \times n$) için $C = AB$ ($m \times n$),

$$
c_{ij} = \sum_{p=1}^{k} a_{ip}\, b_{pj}.
$$

$A$'nın satırı ile $B$'nin sütunu: iç boyutlar ($k$) eşleşmeli. Sütun yorumuyla: $C$'nin $j$'inci sütunu $A \mathbf{b}_j$. Matris çarpımı, Ders 6.27'de göreceğimiz gibi, iki dönüşümün **bileşkesi**; tanımın neden bu kadar garip göründüğünün sebebi bu.

Özellikler (kare matrisler için, Ders 6.23'ün dilinde: $n \times n$ matrisler bir halka):

- **Birleşmeli**: $(AB)C = A(BC)$. (Bileşke birleşmeli, Ders 6.9.)
- **Dağılmalı**: $A(B + C) = AB + AC$.
- **Birim**: $I$, köşegeninde 1, gerisi 0. $AI = IA = A$.
- **Değişmeli değil**: genellikle $AB \ne BA$.
- **Sıfır bölenler var**: $\begin{pmatrix} 0 & 1 \\ 0 & 0 \end{pmatrix}^2 = 0$.

**Devrik** (transpose) $A^T$: $(A^T)_{ij} = a_{ji}$, satırlar sütun olur. $(AB)^T = B^T A^T$ (ters sıra, Ders 6.21'deki çorap–ayakkabı).

---

## 4. Küçük bir matris kütüphanesi

Ders 4.3'te iki boyutlu dizileri satır öncelikli düzende gördük. Boyutu çalışma zamanında belli olan matrisler için tek bir `double` dizisi ve elle indeks hesabı:

```c
typedef struct { int rows, cols; double *a; } mat;    // satir oncelikli: a[i*cols + j]

static mat mat_new(int r, int c) { mat m = { r, c, calloc((size_t)r * c, sizeof(double)) }; return m; }
static void mat_free(mat *m) { free(m->a); m->a = NULL; }
static double *at(const mat *m, int i, int j) { return &m->a[(size_t)i * m->cols + j]; }

static mat mat_identity(int n) {
    mat m = mat_new(n, n);
    for (int i = 0; i < n; i++) *at(&m, i, i) = 1;
    return m;
}
```

`at` bir pointer döndürüyor; hem okumak (`*at(&m, i, j)`) hem yazmak (`*at(&m, i, j) = 5`) için. `(size_t)` dönüşümü, büyük matrislerde `i * cols` çarpımının `int`'te taşmasını önlüyor (Ders 3.8). `calloc` sıfırlanmış bellek veriyor, sıfır matris hazır.

Çarpma, tanımın doğrudan çevirisi; ama döngüleri **bilinçli** bir sırada yazıyoruz:

```c
// C = A B ; A: n x k, B: k x m
static mat mat_mul(const mat *A, const mat *B) {
    mat C = mat_new(A->rows, B->cols);
    for (int i = 0; i < A->rows; i++)
        for (int p = 0; p < A->cols; p++) {          // i-p-j sirasi: B'nin satirini sirayla gez
            double aip = *at(A, i, p);
            for (int j = 0; j < B->cols; j++)
                *at(&C, i, j) += aip * *at(B, p, j);
        }
    return C;
}
```

(Bir gerçek kütüphane `A->cols == B->rows` ön koşulunu `assert` ile denetlemeli; Ders 6.2.)

Değişmeli olmadığını görelim; $A = \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}$, $B = \begin{pmatrix} 0 & 1 \\ 1 & 0 \end{pmatrix}$:

```
AB =
  [   2.00   1.00 ]
  [   4.00   3.00 ]
BA =
  [   3.00   4.00 ]
  [   1.00   2.00 ]
AI =
  [   1.00   2.00 ]
  [   3.00   4.00 ]
```

$B$ bir permütasyon matrisi: sağdan çarpınca ($AB$) $A$'nın **sütunlarını**, soldan çarpınca ($BA$) **satırlarını** değiştiriyor. Ders 6.21'deki $S_n$, permütasyon matrisleri olarak da temsil edilebiliyor.

### Döngü sırası

Matematikte $c_{ij} = \sum_p a_{ip} b_{pj}$ toplamının hangi sırayla hesaplandığı önemsiz (sonlu toplam, Ders 6.10; `double`'da yuvarlama farkları dışında). Makinede çok önemli. Ders kitabı sırası (`i-j-p`, iç döngü $p$ üzerinde) $B$'yi **sütun sütun** geziyor: her adımda bellekte `cols` kadar ileri atlıyor. `i-p-j` sırası ise $B$'nin bir **satırını** baştan sona okuyor; ardışık bellek.

```
n=512: i-j-p 0.170 s, i-p-j 0.019 s, ayni sonuc: 1
```

(`-O2`, bir dizüstü bilgisayarda; senin makinende sayılar farklı ama oran benzer olmalı.) Aynı $\Theta(n^3)$ algoritma, aynı sonuç, yaklaşık **9 kat** fark. Sebep Faz 7'deki cache: ardışık erişim her cache satırındaki 8 `double`'ın hepsini kullanıyor; atlamalı erişim her seferinde yeni bir satır getiriyor. Ayrıca `i-p-j`'nin iç döngüsü (`C[i][j] += a * B[p][j]`) derleyicinin SIMD ile vektörleştirebileceği biçimde. Ders 6.12'nin uyarısı: asimptotik notasyon sabitleri atıyor, makine atmıyor. Faz 11'de bloklama (tiling) ile bir kat daha hızlanacağız.

---

## 5. Matris kuvveti ile Fibonacci

Ders 6.11'de Binet formülünün `double`'da $n = 71$'de yanıldığını gördük ve "tam sonuç için matris kuvveti" demiştik. Fibonacci bağıntısını bir matris–vektör çarpımı olarak yaz:

$$
\begin{pmatrix} F_{n+1} \\ F_n \end{pmatrix} = \begin{pmatrix} 1 & 1 \\ 1 & 0 \end{pmatrix} \begin{pmatrix} F_n \\ F_{n-1} \end{pmatrix}.
$$

Bir adım, bir çarpma. $n$ adım: $Q^n$, $Q = \begin{pmatrix} 1 & 1 \\ 1 & 0 \end{pmatrix}$. Tümevarımla (Ders 6.4) kanıtlanıyor:

$$
Q^n = \begin{pmatrix} F_{n+1} & F_n \\ F_n & F_{n-1} \end{pmatrix}.
$$

Matris çarpımı birleşmeli olduğu için Ders 2.9'daki hızlı üs alma **matrislere de** uygulanıyor: $\Theta(\log n)$ matris çarpımı. Hızlı üssün tek ihtiyacı birleşmeydi; çarpmanın değişmeli olması gerekmiyor.

```c
// 2x2 tamsayi matris, Fibonacci icin
typedef struct { uint64_t a, b, c, d; } m22;
static m22 m22_mul(m22 x, m22 y) {
    m22 r = { x.a * y.a + x.b * y.c, x.a * y.b + x.b * y.d,
              x.c * y.a + x.d * y.c, x.c * y.b + x.d * y.d };
    return r;
}
static uint64_t fib(unsigned n) {                     // [[1,1],[1,0]]^n = [[F(n+1),F(n)],[F(n),F(n-1)]]
    m22 r = {1, 0, 0, 1}, q = {1, 1, 1, 0};
    while (n) { if (n & 1) r = m22_mul(r, q); q = m22_mul(q, q); n >>= 1; }
    return r.b;
}
```

```
fib(71) = 308061521170129, fib(93) = 12200160415121876738
```

$F_{71}$ bu sefer doğru (Ders 6.11'de Binet `...130` vermişti). $F_{93}$, `uint64_t`'ye sığan son Fibonacci. Tamsayı matrisleriyle, yuvarlama yok, ve $\log_2 93 \approx 7$ kareleme. (Son karelemede `q`'nun elemanları $F_{129}$ civarına çıkıp sarıyor, ama o değer kullanılmıyor; `unsigned` sarmanın undefined behavior olmaması burada işe yarıyor.) Mod $p$'de aynı kod $F_{10^{18}} \bmod p$'yi 60 adımda hesaplıyor.

Bu, genel bir yöntem: $k$'ıncı dereceden **her** doğrusal bağıntı (Ders 6.11) bir $k \times k$ matrisin kuvvetine dönüşüyor, ve $n$'inci terim $O(k^3 \log n)$'de.

---

## Alıştırmalar

**1** – $\mathbb{R}^3$'te $(1, 2, 3)$, $(4, 5, 6)$, $(7, 8, 9)$ doğrusal bağımsız mı? Bağımsız değilse bir bağıntı bul. (İpucu: ardışık farklara bak.)

**2** – $GF(2)^3$'te kaç tane farklı taban var? (İlk vektör sıfır olmamalı: 7 seçenek. İkinci, ilkinin germesinde olmamalı. Üçüncü, ilk ikisinin germesinde olmamalı.) Sıralı tabanları say, sonra sırasızları.

**3** – `mat_transpose` ve `mat_add` yaz. $(AB)^T = B^T A^T$'yi rastgele $3 \times 4$ ve $4 \times 2$ matrislerle doğrula. `double` karşılaştırmasında neden tam eşitlik bu durumda çalışıyor? (İpucu: aynı çarpımlar aynı sırada toplanıyor mu?)

**4** – `mat_mul`'un döngü sırasının altı permütasyonunu da yaz ve $n = 512$ için ölç. En hızlı ve en yavaş hangileri? Bellek erişim desenleriyle açıkla.

**5** – Tribonacci: $T_n = T_{n-1} + T_{n-2} + T_{n-3}$, $T_0 = 0$, $T_1 = 0$, $T_2 = 1$. 3×3 bir matris kur ve $T_n \bmod (10^9 + 7)$'yi $n = 10^{18}$ için hesapla. Doğrulamak için küçük $n$'lerde döngüyle karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – Bağımlı: $(4, 5, 6) - (1, 2, 3) = (3, 3, 3) = (7, 8, 9) - (4, 5, 6)$. Yani $(1,2,3) - 2(4,5,6) + (7,8,9) = \mathbf{0}$, sıfır olmayan katsayılarla. Üç vektör bir **düzlem** geriyor (boyut 2), $\mathbb{R}^3$'ün tamamını değil. Ders 6.26'da eliminasyon bunu mekanik olarak bulacak (rank 2).

**2** – İlk vektör: $2^3 - 1 = 7$. İkinci: ilkinin germesi $\{0, \mathbf{v}_1\}$ (2 eleman), $8 - 2 = 6$ seçenek. Üçüncü: ilk ikisinin germesi 4 eleman, $8 - 4 = 4$. Sıralı tabanlar $7 \cdot 6 \cdot 4 = 168$. Her sırasız taban $3! = 6$ sırada: $168 / 6 = 28$. (168, $3 \times 3$ tersinir $GF(2)$ matrislerinin sayısı: her sıralı taban bir matrisin sütunları. Bu grup Ders 6.21'deki anlamda bir grup ve 168 elemanlı.)

**3** –

```c
static mat mat_transpose(const mat *A) {
    mat T = mat_new(A->cols, A->rows);
    for (int i = 0; i < A->rows; i++)
        for (int j = 0; j < A->cols; j++)
            *at(&T, j, i) = *at(A, i, j);
    return T;
}
```

$(AB)^T_{ij} = (AB)_{ji} = \sum_p a_{jp} b_{pi}$ ve $(B^T A^T)_{ij} = \sum_p (B^T)_{ip} (A^T)_{pj} = \sum_p b_{pi} a_{jp}$. Aynı çarpımlar ($a_{jp} b_{pi} = b_{pi} a_{jp}$, `double` çarpması değişmeli), aynı $p$ sırasıyla toplanıyor; dolayısıyla bit bit aynı sonuç. Toplama sırası farklı olsaydı (örneğin farklı döngü sıralı iki `mat_mul`) son birkaç bitte fark görebilirdin; Bölüm 4'teki ölçümde "aynı sonuç: 1" çıkması, `i-j-p` ve `i-p-j`'nin her $c_{ij}$ için $p$'yi aynı sırayla toplamasından.

**4** – Altı sıra: `ijp`, `ipj`, `jip`, `jpi`, `pij`, `pji`. En hızlılar `ipj` ve `pij`: iç döngü $j$, hem $B$'nin hem $C$'nin bir satırını ardışık geziyor. En yavaşlar `jpi` ve `pji`: iç döngü $i$, hem $A$'yı hem $C$'yi sütun boyunca, `n` atlamalarla geziyor. `ijp` ve `jip` ortada: biri ardışık ($A$'nın satırı), biri atlamalı ($B$'nin sütunu). Kural: iç döngünün değişkeni, erişilen dizilerin **son** indeksi olmalı (satır öncelikli düzende).

**5** –

$$
\begin{pmatrix} T_{n+1} \\ T_n \\ T_{n-1} \end{pmatrix} = \begin{pmatrix} 1 & 1 & 1 \\ 1 & 0 & 0 \\ 0 & 1 & 0 \end{pmatrix} \begin{pmatrix} T_n \\ T_{n-1} \\ T_{n-2} \end{pmatrix}
$$

$M^{n-2}$'yi hızlı üsle (mod $p$'de, her çarpımdan sonra `% P`; elemanlar $< p$ olduğu için çarpımlar $p^2 < 2^{63}$) hesapla ve $(T_2, T_1, T_0) = (1, 0, 0)$'a uygula; ilk bileşen $T_n$. Küçük $n$'lerde döngüyle aynı: $0, 0, 1, 1, 2, 4, 7, 13, 24, \dots$

</details>

---

## Kaynaklar

- Gilbert Strang, *Introduction to Linear Algebra* (5. baskı), Bölüm 1–2: vektörler, matrisler, çarpımın satır ve sütun yorumları.
- Sheldon Axler, *Linear Algebra Done Right* (4. baskı, ücretsiz), Bölüm 1–2: vektör uzayları, taban, boyut.
- Ulrich Drepper, "What Every Programmer Should Know About Memory" (2007), §6.2: matris çarpımında döngü sırası ve cache.

**Sıradaki ders:** Doğrusal denklem sistemleri. Gauss eliminasyonu, rank, ters matris, ve C'de bir çözücü.
