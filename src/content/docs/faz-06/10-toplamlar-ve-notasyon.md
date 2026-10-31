---
title: "6.10 Toplamlar ve notasyon"
description: "Σ notasyonu, sınırlar ve kukla indeks; boş toplam; Iverson parantezi ve C'deki karşılaştırmaların 0/1 olması; dağılma, birleşme ve indeks kaydırma yasaları; teleskopik toplamlar (Σ 1/(k(k+1)) ve küplerin farkından Σk²); pertürbasyon yöntemiyle geometrik seri ve Σk·2ᵏ; çift toplamlarda sıra değiştirme; harmonik sayılar ve ln n; kapalı formülleri bütün küçük n'ler için doğrulayan C programı."
---

Ders 6.4'te $1 + 2 + \dots + n = \frac{n(n+1)}{2}$'yi kanıtladık ama bir şikâyetle bitirdik: tümevarım formülü **doğruluyor**, **bulmuyor**. Formülü önceden bilmen gerekiyor. Bu ders o eksiği kapatıyor: toplamları kapalı formüle çevirmenin birkaç mekanik yöntemi.

Bu fazın ilerisinde bunlara sürekli ihtiyacımız olacak. Ders 6.12'de bir algoritmanın kaç adım attığını bulmak, iç içe döngülerin adım sayılarını toplamak demek; Ders 6.13'te böl-yönet algoritmalarının maliyeti, Ders 6.29'da beklenen değerler hep toplamlar. Önce notasyon, sonra yöntemler.

---

## 1. Σ notasyonu

$$
\sum_{k=1}^{n} a_k = a_1 + a_2 + \dots + a_n
$$

$k$: **indeks**, $1$: alt sınır, $n$: üst sınır, $a_k$: terim. Kod karşılığı Ders 4.2'deki ilk algoritma:

```c
long s = 0;
for (int k = 1; k <= n; k++) s += a(k);
```

İndeks bir **kukla değişken** (dummy variable): adının önemi yok. $\sum_{k=1}^n k^2 = \sum_{j=1}^n j^2$. Döngü değişkenini `i` yerine `j` diye adlandırmak programı değiştirmediği gibi. Kuklanın dışarıda bir anlamı da yok: $\sum_{k=1}^n k$'nın değeri $n$'e bağlı, $k$'ya değil.

**Boş toplam**: üst sınır alt sınırdan küçükse toplamda hiç terim yok ve değeri $0$. $\sum_{k=1}^{0} a_k = 0$. Kodda döngü hiç dönmüyor, `s` başlangıç değerinde kalıyor. Ders 6.2'deki boş $\forall$'ın doğru olmasıyla aynı mantık: işlemin etkisiz elemanı (toplama için 0, çarpma için 1; boş çarpım $\prod_{k=1}^0 a_k = 1$, bu yüzden $0! = 1$).

Sınırları başka biçimde de yazabiliriz: bir koşul altına.

$$
\sum_{\substack{1 \le k \le 100 \\ 3 \,\mid\, k}} k = 3 + 6 + \dots + 99
$$

"$1$ ile $100$ arasında, 3'e bölünen $k$'lar üzerinden topla." Bu yazım, sınırları ve koşulları terimden ayırıyor.

---

## 2. Iverson parantezi

*Concrete Mathematics*'in yazarlarının yaygınlaştırdığı küçük ama güçlü bir notasyon:

$$
[P] = \begin{cases} 1 & P \text{ doğruysa} \\ 0 & P \text{ yanlışsa} \end{cases}
$$

Bu, C'nin karşılaştırma operatörlerinin ta kendisi! C'de `k % 3 == 0` ifadesinin değeri tam olarak $[3 \mid k]$: 1 ya da 0 (Ders 2.3). Koşullu bir toplamı koşulsuz bir toplama çeviriyor:

$$
\sum_{\substack{1 \le k \le n \\ P(k)}} a_k = \sum_{k=1}^{n} a_k \, [P(k)]
$$

```c
// 1..100 arasinda 3'e ya da 5'e bolunenlerin sayisi
int c = 0;
for (int k = 1; k <= 100; k++) c += (k % 3 == 0) || (k % 5 == 0);
// c = 47
```

`if` yok; Iverson parantezi doğrudan toplanıyor. Bu, Ders 5.5'teki dalsız kodun matematiksel adı. Iverson parantezinin bir yararı da sınırları serbest bırakması: "$1 \le k \le n$" koşulunu da parantezin içine alırsak toplamı **bütün** tamsayılar üzerinden yazabiliriz, $\sum_k a_k [1 \le k \le n]$, ve sınırların hesabı sıradan mantık işlemine dönüşüyor ($[P][Q] = [P \land Q]$).

---

## 3. Üç temel yasa

$K$ sonlu bir indeks kümesi, $c$ bir sabit olsun.

| Yasa | Biçim | Kodda |
| --- | --- | --- |
| **Dağılma** | $\sum_{k} c\, a_k = c \sum_{k} a_k$ | sabiti döngü dışına çıkar |
| **Birleşme** | $\sum_{k} (a_k + b_k) = \sum_{k} a_k + \sum_{k} b_k$ | iki toplamı ayır ya da birleştir |
| **İndeks değiştirme** | $\sum_{k \in K} a_k = \sum_{p(k) \in K} a_{p(k)}$ | döngü değişkenini kaydır ya da ters çevir |

Son yasada $p$, $K$ üzerinde bir **birebir örten** fonksiyon olmalı (Ders 6.9): toplamın terimlerini yeniden sıralıyoruz, hiçbirini atlamadan ya da tekrarlamadan.

Gauss'un hilesi bu üç yasayla bir satırlık bir türetme oluyor. $S = \sum_{k=0}^{n} k$. İndeksi $k \to n - k$ ile ters çevir (birebir örten: $0 \leftrightarrow n$, $1 \leftrightarrow n-1$, ...):

$$
S = \sum_{k=0}^{n} (n - k).
$$

İki ifadeyi topla (birleşme):

$$
2S = \sum_{k=0}^{n} \big(k + (n - k)\big) = \sum_{k=0}^{n} n = (n + 1)\, n.
$$

$S = \frac{n(n+1)}{2}$. Formülü **bulduk**, sadece doğrulamadık.

Bir uyarı: bu yasalar **sonlu** toplamlarda koşulsuz geçerli. Sonsuz toplamlarda terimleri yeniden sıralamak bazen sonucu değiştiriyor; bu dersin sınırları dışında.

---

## 4. Teleskopik toplam

Terimler bir **farkın** biçimindeyse, toplam neredeyse tamamen sadeleşiyor:

$$
\sum_{k=0}^{n-1} (b_{k+1} - b_k) = (b_1 - b_0) + (b_2 - b_1) + \dots + (b_n - b_{n-1}) = b_n - b_0.
$$

Her $b_k$ bir kez $+$, bir kez $-$ olarak geçiyor; sadece uçlar kalıyor. Adını iç içe geçip kısalan bir dürbünden alıyor.

**Örnek.** $\sum_{k=1}^{n} \frac{1}{k(k+1)}$. Terimi bir fark olarak yaz: $\frac{1}{k(k+1)} = \frac{1}{k} - \frac{1}{k+1}$ (sağ tarafı ortak paydada birleştirip kontrol et). O halde

$$
\sum_{k=1}^{n} \left(\frac{1}{k} - \frac{1}{k+1}\right) = 1 - \frac{1}{n+1} = \frac{n}{n+1}.
$$

$n = 10$ için $\frac{10}{11}$. Kesirleri Ders 2.9'daki EBOB ile sadeleştirerek tam (kayan nokta kullanmadan) toplayan bir program da `10/11` veriyor.

**Örnek: kareler toplamı.** $\sum_{k=0}^n k^2$ için Gauss'un hilesi işe yaramıyor. Teleskopla dolaylı yoldan gidelim: küplerin farkı

$$
(k+1)^3 - k^3 = 3k^2 + 3k + 1.
$$

İki tarafı $k = 0$'dan $n$'e topla. Sol taraf teleskopik: $(n+1)^3 - 0^3$. Sağ taraf, birleşme ve dağılmayla:

$$
(n+1)^3 = 3\sum_{k=0}^{n} k^2 + 3 \cdot \frac{n(n+1)}{2} + (n + 1).
$$

Aradığımız toplamı yalnız bırak:

$$
\sum_{k=0}^{n} k^2 = \frac{(n+1)^3 - \frac{3n(n+1)}{2} - (n+1)}{3} = \frac{n(n+1)(2n+1)}{6}.
$$

(Son adım cebir: $(n+1)$'i ortak paranteze al.) Yöntem genel: $\sum k^m$'yi bulmak için $(k+1)^{m+1} - k^{m+1}$'i teleskopla ve bir önceki toplamları kullan.

Teleskop, Ders 6.4'teki döngü değişmezinin de arkasında: her turda $s$'nin değişimi $a_i$ ise, toplam değişim $s_\text{son} - s_\text{ilk}$.

---

## 5. Pertürbasyon yöntemi

*Concrete Mathematics*'in en sevdiği teknik: toplamı $S_n$ diye adlandır, son terimi **iki farklı yolla** ayır, çıkan denklemi $S_n$ için çöz.

$$
S_{n+1} = S_n + a_{n+1} \qquad \text{ve} \qquad S_{n+1} = a_0 + \sum_{k=0}^{n} a_{k+1}
$$

İlki son terimi, ikincisi ilk terimi ayırıyor. Eğer $\sum a_{k+1}$, $S_n$ cinsinden yazılabiliyorsa, elde bir denklem var.

**Geometrik seri.** $S_n = \sum_{k=0}^{n} x^k$. İkinci yolda $a_{k+1} = x^{k+1} = x \cdot x^k$, yani $\sum_{k=0}^n a_{k+1} = x S_n$:

$$
S_n + x^{n+1} = 1 + x S_n \quad\Rightarrow\quad S_n = \frac{1 - x^{n+1}}{1 - x} \qquad (x \ne 1).
$$

$x = 2$ için $2^{n+1} - 1$, Ders 6.4'teki ikinin kuvvetleri teoremi. $x = \frac{1}{2}$ için $2 - \frac{1}{2^n}$: hiç 2'ye ulaşmayan ama ona yaklaşan bir toplam.

**$\sum k \cdot 2^k$.** $S_n = \sum_{k=0}^{n} k\, 2^k$. İkinci yol:

$$
\sum_{k=0}^{n} (k+1) 2^{k+1} = 2\sum_{k=0}^{n} k\, 2^k + 2\sum_{k=0}^{n} 2^k = 2 S_n + 2(2^{n+1} - 1).
$$

İki yolu eşitle ($a_0 = 0$):

$$
S_n + (n+1)2^{n+1} = 2 S_n + 2^{n+2} - 2 \quad\Rightarrow\quad S_n = (n - 1)\, 2^{n+1} + 2.
$$

Bu toplam algoritma analizinde sık çıkıyor: Faz 8'deki yığın (heap) kurma algoritmasının maliyeti bu biçimde bir toplam ve sonucu şaşırtıcı biçimde $O(n)$.

---

## 6. Çift toplamlar

İç içe iki döngü, iki indeksli bir toplam:

$$
\sum_{i=1}^{n} \sum_{j=1}^{m} a_{ij}
$$

Sonlu toplamlarda **sıra değiştirilebilir**: $\sum_i \sum_j a_{ij} = \sum_j \sum_i a_{ij}$. Bir matrisi önce satır satır, ya da önce sütun sütun toplamak aynı sonucu veriyor (Ders 4.3'te ikisinin hızı farklıydı, sonucu değil).

Sınırlar birbirine bağlıysa dikkat gerekiyor. $\sum_{1 \le i < j \le n}$ yazımı "bütün $i < j$ çiftleri üzerinden" demek; Iverson ile $\sum_{i, j} a_{ij} [1 \le i < j \le n]$. Sırayı değiştirirken koşulu iki biçimde de yazabilirsin:

$$
\sum_{j=1}^{n} \sum_{i=1}^{j-1} a_{ij} = \sum_{i=1}^{n} \sum_{j=i+1}^{n} a_{ij}.
$$

**Örnek.** Ders 6.2'deki `all_distinct` kaç karşılaştırma yapıyor? Her $i < j$ çifti için bir:

$$
\sum_{1 \le i < j \le n} 1 = \sum_{j=1}^{n} (j - 1) = \sum_{k=0}^{n-1} k = \frac{n(n-1)}{2}.
$$

İç toplam ($i$ üzerinden, $1$'den $j-1$'e) $j - 1$ tane 1; sonra indeks kaydırma ($k = j - 1$) ve Gauss.

---

## 7. Harmonik sayılar

Her toplamın kapalı formülü yok. En ünlüsü **harmonik sayılar**:

$$
H_n = \sum_{k=1}^{n} \frac{1}{k} = 1 + \frac{1}{2} + \frac{1}{3} + \dots + \frac{1}{n}
$$

$H_n$ için $\frac{n(n+1)}{2}$ gibi bir formül yok; ama ne kadar büyüdüğünü biliyoruz. $\frac{1}{k}$'yı $\int \frac{dx}{x}$ ile karşılaştırınca $H_n \approx \ln n$, ve fark bir sabite yaklaşıyor:

```
H = 14.392727 ln n = 13.815511 fark = 0.577216
```

($n = 10^6$.) Bu sabit $\gamma \approx 0.5772$, Euler–Mascheroni sabiti. Harmonik toplam **sonsuza** gidiyor (ama çok yavaş: $H_n > 100$ için $n \approx 1.5 \cdot 10^{43}$ gerekiyor) ve $\ln n$ hızıyla büyüyor. Faz 9'daki quicksort'un ortalama karşılaştırma sayısı, $2n H_n \approx 1.39\, n \log_2 n$, buradan geliyor.

Kayan noktayla bir uyarı: toplamı $k = 1$'den yukarı toplamak, büyük $H$'ye küçük terimler eklediği için hassasiyet kaybediyor (Ders 3.14). Küçükten büyüğe, yani $k = n$'den aşağı toplamak daha doğru sonuç veriyor.

---

## 8. Formülü programla denetlemek

Ders 6.3'ün dersi: denemek kanıt değildir. Ama bir formülü türettikten sonra küçük $n$'ler için denemek, **cebir hatalarını** yakalamanın en ucuz yolu. Bir işaret hatası ya da yanlış sınır ilk birkaç $n$'de hemen ortaya çıkıyor.

```c
#include <stdio.h>
#include <stdint.h>
#include <stdbool.h>

typedef int64_t (*term_fn)(int64_t k);
typedef int64_t (*closed_fn)(int64_t n);

static int64_t sq(int64_t k)       { return k * k; }
static int64_t sq_closed(int64_t n){ return n * (n + 1) * (2 * n + 1) / 6; }
static int64_t k2k(int64_t k)      { return k << k; }
static int64_t k2k_closed(int64_t n){ return (n - 1) * ((int64_t)1 << (n + 1)) + 2; }

// sum_{k=0}^{n} term(k) == closed(n), her n in [0, max] icin
static bool check(const char *name, term_fn term, closed_fn closed, int64_t max) {
    int64_t s = 0;
    for (int64_t n = 0; n <= max; n++) {
        s += term(n);                      // s = term(0) + ... + term(n)
        if (s != closed(n)) {
            printf("%s: n = %lld icin toplam %lld, formul %lld\n",
                   name, (long long)n, (long long)s, (long long)closed(n));
            return false;
        }
    }
    printf("%s: n = 0..%lld dogru\n", name, (long long)max);
    return true;
}

int main(void) {
    check("k^2", sq, sq_closed, 1000);
    check("k*2^k", k2k, k2k_closed, 50);
    return 0;
}
```

```
k^2: n = 0..1000 dogru
k*2^k: n = 0..50 dogru
```

`check`, toplamı her $n$ için baştan hesaplamıyor: bir önceki toplama yeni terimi ekliyor (pertürbasyondaki $S_{n+1} = S_n + a_{n+1}$). Ders 6.4'teki `sum_to`'nun `assert`'lü döngüsünün genel hali.

Sınırlara dikkat: `k << k`'yı $n = 50$'de durdurduk. $n \cdot 2^{n+1}$, $n = 57$'de 63 biti aşıyor ve işaretli taşma undefined behavior (Ders 3.8). `-fsanitize=undefined` ile derleyince bu sınırı aşan bir denemede UBSan hemen uyarıyor. Bir formül matematikte her $n$ için doğru olsa da kodda ancak tipin sığdığı aralıkta doğru.

---

## Alıştırmalar

**1** – $\sum_{k=1}^{n} (2k - 1)$'i Bölüm 3'teki yasalarla hesapla (tümevarım kullanmadan). Ders 6.4'ün 1. alıştırmasıyla karşılaştır.

**2** – Teleskopla hesapla: $\sum_{k=1}^{n} \frac{1}{(2k-1)(2k+1)}$. (İpucu: $\frac{1}{(2k-1)(2k+1)} = \frac{1}{2}\left(\frac{1}{2k-1} - \frac{1}{2k+1}\right)$.) Sonucu tam kesirle hesaplayan bir programla $n = 10$ için doğrula.

**3** – $\sum_{k=0}^{n} k^3$'ü Bölüm 4'teki küp yöntemini bir derece yükselterek ($(k+1)^4 - k^4$) bul. Sonuç $\left(\frac{n(n+1)}{2}\right)^2$ çıkmalı; programla doğrula.

**4** – Şu iç içe döngünün `count++` satırı kaç kez çalışıyor? Önce çift toplam olarak yaz, sonra kapalı forma getir.

```c
for (int i = 0; i < n; i++)
    for (int j = i; j < n; j++)
        for (int k = i; k <= j; k++)
            count++;
```

**5** – Biri $\sum_{k=0}^{n} k^2$ için $\frac{n(n+1)(2n+1)}{6}$ yerine $\frac{n^3}{3} + \frac{n^2}{2}$ yazmış. `check`'e bu formülü ver. Hangi $n$'de yanlış çıkıyor? Doğru formülle farkı ne?

<details>
<summary>Cevaplar</summary>

**1** – Birleşme ve dağılma: $\sum_{k=1}^n (2k - 1) = 2\sum_{k=1}^n k - \sum_{k=1}^n 1 = 2 \cdot \frac{n(n+1)}{2} - n = n^2 + n - n = n^2$. Ders 6.4'te aynı sonucu tümevarımla doğrulamıştık; burada formülü önceden bilmeden **türettik**.

**2** – Terim bir fark: $\frac{1}{2}(b_k - b_{k+1})$, $b_k = \frac{1}{2k-1}$. Teleskop: $\frac{1}{2}\left(b_1 - b_{n+1}\right) = \frac{1}{2}\left(1 - \frac{1}{2n+1}\right) = \frac{n}{2n+1}$. $n = 10$ için $\frac{10}{21}$.

```c
uint64_t p = 0, q = 1;                     // p/q = 0
for (uint64_t k = 1; k <= 10; k++) {
    uint64_t d = (2 * k - 1) * (2 * k + 1);
    p = p * d + q; q = q * d;              // p/q + 1/d
    uint64_t g = gcd(p, q); p /= g; q /= g;
}
// p/q = 10/21
```

Her adımda EBOB ile sadeleştirmek önemli; yoksa payda hızla büyüyüp `uint64_t`'yi taşırır. Faz 12'de keyfi büyüklükte tamsayılarla bu sınırı kaldıracağız.

**3** – $(k+1)^4 - k^4 = 4k^3 + 6k^2 + 4k + 1$. $0$'dan $n$'e topla: $(n+1)^4 = 4\sum k^3 + 6 \cdot \frac{n(n+1)(2n+1)}{6} + 4 \cdot \frac{n(n+1)}{2} + (n+1)$. Yalnız bırakıp sadeleştirince: $\sum_{k=0}^{n} k^3 = \frac{n^2(n+1)^2}{4} = \left(\frac{n(n+1)}{2}\right)^2$. Yani küplerin toplamı, sayıların toplamının karesi: $1^3 + 2^3 + 3^3 = 36 = (1 + 2 + 3)^2$.

```c
static int64_t cube(int64_t k)        { return k * k * k; }
static int64_t cube_closed(int64_t n) { return (n * (n + 1) / 2) * (n * (n + 1) / 2); }
// check("k^3", cube, cube_closed, 1000);  ->  dogru
```

**4** – En içteki döngü $j - i + 1$ kez dönüyor. Toplam:

$$
\sum_{i=0}^{n-1} \sum_{j=i}^{n-1} (j - i + 1).
$$

İç toplamda $m = j - i + 1$ dersek (indeks kaydırma) $m$, $1$'den $n - i$'ye gidiyor: $\sum_{m=1}^{n-i} m = \frac{(n-i)(n-i+1)}{2}$. Dış toplamda $t = n - i$ ($t$, $1$'den $n$'e; ters çevirme):

$$
\sum_{t=1}^{n} \frac{t(t+1)}{2} = \frac{1}{2}\left(\sum t^2 + \sum t\right) = \frac{1}{2}\left(\frac{n(n+1)(2n+1)}{6} + \frac{n(n+1)}{2}\right) = \frac{n(n+1)(n+2)}{6}.
$$

$n = 10$ için $220$. Bu, $\binom{n+2}{3}$; üç iç içe döngü, $\{0, \dots, n+1\}$'den 3 eleman seçmenin yollarını sayıyor (Ders 6.14).

**5** – $n = 1$'de: toplam $1$, yanlış formül $\frac{1}{3} + \frac{1}{2}$. Tamsayı aritmetiğinde `n*n*n/3 + n*n/2` $= 0 + 0 = 0$, `check` hemen `n = 1 icin toplam 1, formul 0` diyor. Doğru formülü açınca $\frac{n(n+1)(2n+1)}{6} = \frac{n^3}{3} + \frac{n^2}{2} + \frac{n}{6}$; yanlış formül son terimi ($\frac{n}{6}$) unutmuş. Büyük $n$'de bu terim önemsiz görünür (Ders 6.12'de $\Theta(n^3)$ açısından ikisi aynı), ama tam bir sayım için yanlış. Program, kâğıttaki bir cebir hatasını ilk denemede yakaladı.

</details>

---

## Kaynaklar

- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), Bölüm 2: toplamlar, Iverson parantezi, pertürbasyon, çift toplamlar, harmonik sayılar.
- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §2.4: diziler ve toplamlar.
- Kenneth Iverson, *A Programming Language* (1962): $[P]$ notasyonunun kaynağı.
- Donald Knuth, "Two Notes on Notation", *American Mathematical Monthly* 99(5), 1992: Iverson parantezinin savunusu.

**Sıradaki ders:** Özyinelemeli bağıntılar. Hanoi kuleleri, karakteristik denklem, ve Fibonacci sayılarının kapalı formülü.
