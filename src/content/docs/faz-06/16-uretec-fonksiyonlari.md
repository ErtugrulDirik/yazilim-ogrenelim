---
title: "6.16 Üreteç fonksiyonları"
description: "Bir diziyi bir kuvvet serisinin katsayıları olarak görmek; polinom çarpımının evrişim (convolution) olması ve sayma problemlerini çarpmaya çevirmesi; bozuk para problemi; 1/(1−x), kaydırma ve türev işlemleri; Fibonacci'nin üreteç fonksiyonu x/(1−x−x²); Catalan sayıları, C(x) = 1 + x·C(x)² denklemi ve kapalı formu; bir ifadenin farklı parse ağaçlarının sayısı ve hepsini üreten C programı."
---

Ders 6.11'de Fibonacci'yi karakteristik denklemle çözdük, Ders 6.14'te $(x + y)^n$'yi açınca katsayıların $\binom{n}{k}$ olduğunu gördük. İkisinin arkasında ortak, şaşırtıcı derecede güçlü bir fikir var: bir sayı dizisini, bir polinomun (ya da sonsuz bir polinomun) **katsayıları** olarak yazmak.

$$
a_0, a_1, a_2, \dots \quad\longleftrightarrow\quad A(x) = a_0 + a_1 x + a_2 x^2 + \dots = \sum_{n \ge 0} a_n x^n
$$

$A(x)$'e dizinin **üreteç fonksiyonu** (generating function) denir. Burada $x$ bir sayı değil, sadece bir **yer tutucu**: $x^n$'nin katsayısı dizinin $n$'inci terimi. Bilgisayardaki karşılığı bir dizi: `a[n]` = $x^n$'nin katsayısı. Kazancımız, dizilerle yapılan zor işlemlerin (sayma, bağıntı çözme) polinomlarla yapılan kolay işlemlere (çarpma, bölme) dönüşmesi.

Wilf'in sözüyle: "Üreteç fonksiyonu, bir sayı dizisini asmak için bir çamaşır ipidir."

---

## 1. Çarpma sayar

İki polinomu çarp:

$$
(a_0 + a_1 x + a_2 x^2 + \dots)(b_0 + b_1 x + b_2 x^2 + \dots)
$$

$x^n$'nin katsayısı, üsleri toplamı $n$ olan bütün çiftlerden geliyor:

$$
c_n = \sum_{k=0}^{n} a_k\, b_{n-k}.
$$

Bu işleme **evrişim** (convolution) denir, ve bir sayma ilkesi: $a_k$ "ilk parçayı $k$ birimle yapmanın yolu", $b_{n-k}$ "ikinci parçayı kalan $n - k$ birimle yapmanın yolu" ise, $c_n$ "toplam $n$ birimle yapmanın yolu" (Ders 6.14'teki çarpma ilkesi her $k$ için, toplama ilkesi $k$'lar üzerinden).

```c
#define MAXD 64

// c = a * b (katsayi dizileri), derece < MAXD'de kes
static void poly_mul(uint64_t *c, const uint64_t *a, const uint64_t *b) {
    for (int n = 0; n < MAXD; n++) {
        c[n] = 0;
        for (int k = 0; k <= n; k++) c[n] += a[k] * b[n - k];   // evrisim
    }
}
```

Sonsuz seriler $x^{63}$'te kesiliyor; $n < 64$ için bütün katsayılar tam. Evrişim Faz 12'de (FFT ile hızlı polinom çarpımı) ve Faz 11'de (sinyal işleme, SIMD) tekrar karşımıza çıkacak.

### Bozuk para problemi

1, 5 ve 10 kuruşluk bozuk paralarla 25 kuruş kaç yolla ödenir?

1 kuruşlukları kullanmanın yolları: hiç, bir tane, iki tane, ... Bunların her biri $0, 1, 2, \dots$ kuruş tutuyor. Üreteç fonksiyonu:

$$
1 + x + x^2 + x^3 + \dots
$$

5'likler: $1 + x^5 + x^{10} + \dots$, 10'luklar: $1 + x^{10} + x^{20} + \dots$ Bir ödeme, her türden bir seçim; toplam tutar, tutarların toplamı. Çarpım:

$$
(1 + x + x^2 + \dots)(1 + x^5 + x^{10} + \dots)(1 + x^{10} + x^{20} + \dots)
$$

ve $x^{25}$'in katsayısı cevap:

```c
uint64_t c1[MAXD] = {0}, c5[MAXD] = {0}, c10[MAXD] = {0}, t[MAXD], r[MAXD];
for (int i = 0; i < MAXD; i += 1) c1[i] = 1;      // 1 + x + x^2 + ...
for (int i = 0; i < MAXD; i += 5) c5[i] = 1;      // 1 + x^5 + x^10 + ...
for (int i = 0; i < MAXD; i += 10) c10[i] = 1;    // 1 + x^10 + ...
poly_mul(t, c1, c5);
poly_mul(r, t, c10);
```

```
25 kurus: 12 yol, 50 kurus: 36 yol
```

Problemi çözmek için hiçbir durum analizi yapmadık; sadece "her para türü bir çarpan" dedik. Bu, Faz 9'daki dinamik programlamanın bozuk para çözümünün cebirsel hali.

---

## 2. Temel işlemler

En önemli seri, Ders 6.10'daki geometrik serinin sonsuz hali:

$$
\frac{1}{1 - x} = 1 + x + x^2 + x^3 + \dots \qquad (1, 1, 1, \dots)
$$

Doğrulamak için iki tarafı $(1 - x)$ ile çarp: $(1 - x)(1 + x + x^2 + \dots) = 1 + x + x^2 + \dots - x - x^2 - \dots = 1$. Burada yakınsaklıkla hiç ilgilenmedik: üreteç fonksiyonları **biçimsel** seriler, $x$'e değer vermiyoruz; sadece katsayıların cebiri.

Bundan türeyen dönüşümler:

| İşlem | Dizi | Üreteç fonksiyonu |
| --- | --- | --- |
| Temel | $1, 1, 1, \dots$ | $\frac{1}{1-x}$ |
| Ölçekleme | $1, c, c^2, \dots$ | $\frac{1}{1 - cx}$ |
| Sağa kaydırma | $0, a_0, a_1, \dots$ | $x A(x)$ |
| Kısmi toplamlar | $a_0, a_0 + a_1, \dots$ | $\frac{A(x)}{1-x}$ |
| Türev (indeksle çarpma) | $0, a_1, 2a_2, 3a_3, \dots$ | $x A'(x)$ |
| Binom | $\binom{n}{0}, \binom{n}{1}, \dots, \binom{n}{n}$ | $(1 + x)^n$ |

"Kısmi toplamlar" satırı, $\frac{1}{1-x}$ ile çarpmanın $(1, 1, 1, \dots)$ ile evrişim olmasından: $c_n = a_0 + \dots + a_n$. Örneğin $\frac{1}{(1-x)^2} = \sum (n+1) x^n$, çünkü $1, 1, 1, \dots$'nin kısmi toplamları $1, 2, 3, \dots$. Bir kez daha: $\frac{1}{(1-x)^3}$'ün katsayıları $1, 3, 6, 10, \dots = \binom{n+2}{2}$, Ders 6.14'teki çubuk–yıldız sayıları.

---

## 3. Bağıntı çözmek: Fibonacci

$F(x) = \sum F_n x^n$. Bağıntı $F_n = F_{n-1} + F_{n-2}$ ($n \ge 2$), $F_0 = 0$, $F_1 = 1$. Bağıntıyı seri düzeyinde yaz: $F(x)$'ten $x F(x)$ ve $x^2 F(x)$'i çıkar.

$$
\begin{aligned}
F(x) &= F_0 + F_1 x + F_2 x^2 + F_3 x^3 + \dots \\
x F(x) &= \phantom{F_0 + {}} F_0 x + F_1 x^2 + F_2 x^3 + \dots \\
x^2 F(x) &= \phantom{F_0 + F_1 x + {}} F_0 x^2 + F_1 x^3 + \dots
\end{aligned}
$$

$F - xF - x^2 F$'de $x^2$ ve üstündeki her katsayı $F_n - F_{n-1} - F_{n-2} = 0$. Geriye sadece $F_0 + (F_1 - F_0)x = x$ kalıyor:

$$
F(x)(1 - x - x^2) = x \quad\Rightarrow\quad F(x) = \frac{x}{1 - x - x^2}.
$$

Bütün sonsuz dizi tek bir kesirde. Paydanın kökleri $\frac{1}{\varphi}$ ve $\frac{1}{\psi}$; kesri basit kesirlere ayırıp her birini $\frac{1}{1 - cx}$ olarak açınca Ders 6.11'deki Binet formülü çıkıyor. Karakteristik denklem yöntemi aslında bu hesabın kısayolu: paydanın $1 - x - x^2$, karakteristik denklemin $r^2 - r - 1$ olması, katsayıların ters sırası.

---

## 4. Catalan sayıları ve parse ağaçları

Bir derleyici `a - b - c - d` ifadesini ayrıştırırken, öncelik ve birleşme kuralları olmasaydı kaç farklı ağaç kurabilirdi? Her ağaç bir parantezleme:

```c
// lo..hi harflerinin butun parantezlemelerini out'a yazar, sayisini dondurur
static int trees(char lo, char hi, char out[][LEN]) {
    if (lo == hi) { out[0][0] = lo; out[0][1] = '\0'; return 1; }
    int n = 0;
    for (char m = lo; m < hi; m++) {          // kok: m ile m+1 arasindaki operator
        char L[MAXT][LEN], R[MAXT][LEN];
        int nl = trees(lo, m, L), nr = trees(m + 1, hi, R);
        for (int i = 0; i < nl; i++)
            for (int j = 0; j < nr; j++)
                snprintf(out[n++], LEN, "(%s-%s)", L[i], R[j]);
    }
    return n;
}
```

```
(a-(b-(c-d)))
(a-((b-c)-d))
((a-b)-(c-d))
((a-(b-c))-d)
(((a-b)-c)-d)
5 agac
```

Beş ağaç, ve çıkarma birleşmeli olmadığı için hepsi farklı değer veriyor ($a = 8, b = 4, c = 2, d = 1$ için ilki $5$, sonuncusu $1$). C'nin "çıkarma soldan birleşir" kuralı, beşinden **sonuncusunu** seçiyor. Ders 14.8'de bu seçimi gramere kodlayacağız; şimdi soru: $n$ operatörlü bir ifadenin kaç ağacı var?

Kodun yapısı bağıntıyı veriyor. $C_n$ = $n$ operatörlü (yani $n + 1$ yapraklı) ikili ağaç sayısı. Kök operatör, solunda $k$ operatör ve sağında $n - 1 - k$ operatör bırakıyor:

$$
C_0 = 1, \qquad C_{n} = \sum_{k=0}^{n-1} C_k\, C_{n-1-k}.
$$

Bu bir evrişim! Üreteç fonksiyonu $C(x) = \sum C_n x^n$ için, sağ taraf $C(x)^2$'nin $x^{n-1}$ katsayısı:

$$
C(x) = 1 + x\, C(x)^2.
$$

"Bir ağaç ya tek yapraktır (1), ya da bir kök ($x$) ve iki alt ağaçtır ($C^2$)." Ağacın **tanımı**, doğrudan bir denklem. İkinci dereceden denklemi $C(x)$ için çöz:

$$
C(x) = \frac{1 - \sqrt{1 - 4x}}{2x}
$$

(Diğer kök $x \to 0$'da sonsuza gidiyor; $C(0) = 1$ olmalı.) $\sqrt{1 - 4x}$'i genelleştirilmiş binom teoremiyle açınca, birkaç satır cebirden sonra:

$$
C_n = \frac{1}{n+1}\binom{2n}{n}.
$$

İkisini programla karşılaştıralım; bağıntıyla:

```c
uint64_t C[MAXD] = {1};
for (int n = 0; n + 1 < 36; n++) {
    C[n + 1] = 0;
    for (int k = 0; k <= n; k++) C[n + 1] += C[k] * C[n - k];
}
```

```
1 1 2 5 14 42 132 429 1430 4862 16796
C_35 = 3116285494907301262
```

$C_3 = 5$, programın saydığı ağaç sayısı. $C_{35} = \frac{1}{36}\binom{70}{35}$ ile aynı. Catalan sayıları bilgisayar biliminin her yerinde: $n$ çift dengeli parantez dizisi (Ders 6.7'deki yığın), $n$ düğümlü ikili ağaç (Faz 8), bir matris çarpım zincirini parantezlemenin yolları (Faz 9'daki dinamik programlama), bir çokgeni üçgenlemenin yolları. Hepsi aynı $C = 1 + xC^2$ yapısına sahip.

Büyüme hızı: Stirling ile $C_n \approx \frac{4^n}{n^{3/2}\sqrt{\pi}}$. Belirsiz bir gramerde (Ders 14.8) uzun bir ifadenin parse ağacı sayısı üstel büyüyor; bu yüzden parser'lar belirsizliği kurallarla gideriyor, bütün ağaçları denemek yerine.

---

## Alıştırmalar

**1** – 1, 2 ve 5 liralık bozuk paralarla 20 lira kaç yolla ödenir? Programla hesapla. Her türden **en fazla 3** para kullanılabilseydi hangi çarpanlar değişirdi?

**2** – $\frac{1}{(1 - x)(1 - 2x)}$'in katsayılarını bul. (İpucu: kısmi toplamlar kuralı, ya da basit kesirlere ayır.) Hangi tanıdık diziyi buldun?

**3** – Ders 6.11'deki $a_n = 5a_{n-1} - 6a_{n-2}$, $a_0 = 1$, $a_1 = 4$ bağıntısını üreteç fonksiyonuyla çöz. Payda ile karakteristik denklem arasındaki ilişkiyi göster.

**4** – $n$ çift parantezden oluşan dengeli dizileri (`(())()` gibi) üreten bir program yaz ve sayılarının $C_n$ olduğunu doğrula. Bir parantez dizisi ile bir ikili ağaç arasında birebir örten bir eşleme tarif et.

**5** – Bölüm 4'teki `C[n]` hesabını `uint64_t`'de kaçıncı $n$'ye kadar sürdürebilirsin? $C_n \approx 4^n / (n^{3/2}\sqrt\pi)$ yaklaşımıyla tahmin et, sonra Ders 6.14'teki taşma testiyle doğrula. Evrişimdeki **ara** çarpımlar sonuçtan küçük mü?

<details>
<summary>Cevaplar</summary>

**1** – $(1 + x + x^2 + \dots)(1 + x^2 + x^4 + \dots)(1 + x^5 + x^{10} + \dots)$, $x^{20}$ katsayısı: **29**. En fazla 3 para: her çarpan sonlu bir polinom olur, örneğin 2'likler için $1 + x^2 + x^4 + x^6$. Üreteç fonksiyonlarının esnekliği: kısıt, sadece ilgili çarpanı değiştiriyor.

**2** – $\frac{1}{1-2x} = \sum 2^n x^n$, $\frac{1}{1-x}$ ile çarpmak kısmi toplam alıyor: $c_n = 1 + 2 + \dots + 2^n = 2^{n+1} - 1$. Hanoi dizisinin bir kaydırılmışı (Ders 6.11): $T(n+1)$. Basit kesirlerle: $\frac{1}{(1-x)(1-2x)} = \frac{2}{1-2x} - \frac{1}{1-x}$, katsayılar $2 \cdot 2^n - 1$. Aynı sonuç.

**3** – $A - 5xA + 6x^2 A = a_0 + (a_1 - 5a_0)x = 1 - x$. $A(x) = \frac{1 - x}{1 - 5x + 6x^2} = \frac{1 - x}{(1 - 2x)(1 - 3x)}$. Basit kesirler: $\frac{1-x}{(1-2x)(1-3x)} = \frac{\alpha}{1-2x} + \frac{\beta}{1-3x}$; $x = \frac12$ koyarak $\alpha = \frac{1/2}{-1/2} = -1$, $x = \frac13$ koyarak $\beta = \frac{2/3}{1/3} = 2$. $a_n = -2^n + 2 \cdot 3^n$. ✓ Payda $1 - 5x + 6x^2$; karakteristik denklem $r^2 - 5r + 6$. Biri öbürünün katsayılarını ters sırada yazıyor; $x = 1/r$ koyup $r^2$ ile çarpınca birbirine dönüşüyorlar. Paydanın kökleri ($\frac12$, $\frac13$), karakteristik köklerin ($2$, $3$) tersleri.

**4** –

```c
static int gen(char *buf, int pos, int open, int close, int n) {
    if (pos == 2 * n) { buf[pos] = '\0'; printf("%s\n", buf); return 1; }
    int c = 0;
    if (open < n)     { buf[pos] = '('; c += gen(buf, pos + 1, open + 1, close, n); }
    if (close < open) { buf[pos] = ')'; c += gen(buf, pos + 1, open, close + 1, n); }
    return c;
}
// char buf[64]; gen(buf, 0, 0, 0, 4) -> 14 = C_4
```

Eşleme: boş dizi ↔ tek yaprak. Boş olmayan her dengeli dizi tek bir biçimde `(` $L$ `)` $R$ olarak yazılabilir ($L$ ve $R$ dengeli; ilk parantezin eşini bul). Bunu kökü olan, sol alt ağacı $L$'ye, sağ alt ağacı $R$'ye karşılık gelen bir ağaca eşle. Ayrıştırma tek türlü olduğu için birebir örten; ve $C = 1 + xC^2$ denkleminin her iki yorumu da tam bu ayrıştırmayı anlatıyor.

**5** – $4^n / (n^{1.5} \sqrt\pi) \approx 2^{64}$ için $2n - 1.5 \log_2 n - 0.83 \approx 64$, $n \approx 36$. Gerçekte $C_{35} \approx 3.1 \cdot 10^{18}$ sığıyor, $C_{36} \approx 1.1 \cdot 10^{19}$ hâlâ $2^{64} \approx 1.8 \cdot 10^{19}$'dan küçük, $C_{37} \approx 4.2 \cdot 10^{19}$ sığmıyor. Evrişimdeki her $C_k C_{n-1-k}$ çarpımı sonuçtan **küçük** (sonuç bu çarpımların toplamı); dolayısıyla sonuç sığıyorsa ara değerler de sığıyor. Ders 6.14'teki çarpımsal formülün tersine güvenli bir hesap. Sadece toplamın kendisi taşabilir; `C[n+1] < C[n]` kontrolü (sarma) bunu yakalar.

</details>

---

## Kaynaklar

- Herbert Wilf, *generatingfunctionology* (3. baskı, yazarın sitesinde ücretsiz): üreteç fonksiyonlarının klasik kitabı.
- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), Bölüm 7: üreteç fonksiyonları; §7.5 Catalan sayıları.
- Richard Stanley, *Catalan Numbers* (2015): Catalan sayılarının 200'den fazla yorumu.

**Sıradaki ders:** Bölünebilirlik ve asallar. Aritmetiğin temel teoremi ve Eratosthenes eleği, Faz 5'teki bitset ile.
