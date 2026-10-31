---
title: "6.12 Asimptotik notasyon"
description: "Neden adım sayısının tamamı değil büyüme hızı önemli; O, Ω ve Θ'nın niceleyicilerle kesin tanımları; tanımdan c ve n₀ bularak ispat; limit ile ispat ve büyüme hiyerarşisi (log n < √n < n < n log n < n² < 2ⁿ < n!); toplama ve çarpma kuralları; döngü desenlerinden (iç içe, yarıya inen, harmonik) karmaşıklık çıkarma; adım sayılarını sayıp n², log₂ n ve n ln n ile oranlayan C programı ve O notasyonunun yaygın kötüye kullanımları."
---

Ders 6.10'un alıştırmasında bir döngünün `count++` satırının tam olarak $\frac{n(n+1)(n+2)}{6}$ kez çalıştığını bulduk. Ders 6.11'de Fibonacci'nin $\frac{\varphi^n - \psi^n}{\sqrt 5}$ olduğunu. Kesin cevaplar güzel ama çoğu zaman gereğinden fazla: iki algoritmayı karşılaştırırken $\frac{n^3}{6} + \frac{n^2}{2} + \frac{n}{3}$ yerine "$n^3$ gibi büyüyor" demek yeterli, hatta daha açıklayıcı.

Üstelik kesin adım sayısı zaten tanımsız: "bir adım" bir C satırı mı, bir makine komutu mu, bir saat çevrimi mi? Derleyiciye, işlemciye, cache'e göre değişiyor (Faz 7, 11). Değişmeyen tek şey **büyüme hızı**: girdi on kat büyüyünce süre on kat mı, yüz kat mı, bin kat mı artıyor? Asimptotik notasyon bunun dili.

---

## 1. Neden sabitler önemsiz

İki algoritma: A, $100n$ adım; B, $n^2$ adım. Küçük $n$'de B daha hızlı ($n = 10$: A 1000, B 100). Ama $n = 100$'de eşitler ve sonrasında B hiç yetişemiyor: $n = 10^6$'da A $10^8$, B $10^{12}$ adım. Saniyede $10^9$ adımlık bir makinede A 0.1 saniye, B 17 dakika.

Sabit (100) A'yı başta yavaşlattı ama büyüme hızı (doğrusal) sonunda kazandı. Makineyi 100 kat hızlandırmak sabitleri değiştirir, büyüme hızını değiştirmez. Asimptotik notasyonun iki kuralı buradan:

- **Sabit çarpanları at**: $100n$ ile $n$ aynı sınıfta.
- **Küçük terimleri at**: $n^2 + 1000n$ ile $n^2$ aynı sınıfta, çünkü büyük $n$'de $n^2$ baskın.

---

## 2. Tanımlar

$f, g : \mathbb{N} \to \mathbb{R}_{\ge 0}$ olsun (adım sayıları, bellek miktarları: hep negatif olmayan).

$$
f(n) = O(g(n)) \iff \exists c > 0\; \exists n_0\; \forall n \ge n_0:\; f(n) \le c \cdot g(n)
$$

"$f$, $g$'den **hızlı büyümüyor**": yeterince büyük $n$'ler için, $g$'nin bir sabit katı $f$'i yukarıdan sınırlıyor. **Üst sınır.**

$$
f(n) = \Omega(g(n)) \iff \exists c > 0\; \exists n_0\; \forall n \ge n_0:\; f(n) \ge c \cdot g(n)
$$

"$f$, $g$'den **yavaş büyümüyor**." **Alt sınır.**

$$
f(n) = \Theta(g(n)) \iff f(n) = O(g(n)) \land f(n) = \Omega(g(n))
$$

"$f$ ile $g$ **aynı hızda büyüyor**." **Sıkı sınır.**

Niceleyicilerin sırasına dikkat (Ders 6.2): $\exists c\, \exists n_0\, \forall n$. Önce **bir** sabit ve **bir** başlangıç noktası seçiyorsun, sonra o noktadan sonraki **her** $n$ için eşitsizlik tutmalı. Sırayı $\forall n\, \exists c$'ye çevirirsen tanım anlamsızlaşır: her $n$ için $c = f(n) / g(n)$ seçebilirsin ve her fonksiyon her fonksiyonun $O$'su olur.

$n_0$ "sonlu sayıda istisna"ya izin veriyor: küçük $n$'lerde ne olduğu önemsiz.

---

## 3. Tanımdan ispat

**Teorem.** $3n^2 + 10n + 5 = \Theta(n^2)$.

**Kanıt.** *$O$ yönü*: $n \ge 1$ için $10n \le 10n^2$ ve $5 \le 5n^2$. O halde $3n^2 + 10n + 5 \le 18n^2$. $c = 18$, $n_0 = 1$. ✓ *$\Omega$ yönü*: her $n$ için $3n^2 + 10n + 5 \ge 3n^2$. $c = 3$, $n_0 = 0$. ✓ $\blacksquare$

Kalıp: $O$ için küçük terimleri büyük terime **yukarı yuvarla**, $\Omega$ için küçük terimleri **at**. $c$'nin en iyi değeri önemli değil; var olması yeterli.

**Teorem.** $n^2 \ne O(n)$.

**Kanıt** (çelişki, Ders 6.3). $n^2 \le cn$ her $n \ge n_0$ için doğru olsun. $n > 0$ için ikiye böl: $n \le c$. Ama $n = \max(n_0, \lceil c \rceil + 1)$ seçince $n > c$. Çelişki. $\blacksquare$

Bir şeyin $O$ **olmadığını** göstermek, tanımın olumsuzlamasını göstermek: $\forall c\, \forall n_0\, \exists n \ge n_0:\; f(n) > c\, g(n)$. Her sabit için bir karşı örnek.

---

## 4. Limit ile ispat

Tanımla çalışmak bazen zahmetli. Analizden bir kısayol: oranın limitine bak.

$$
L = \lim_{n \to \infty} \frac{f(n)}{g(n)}
$$

| $L$ | Sonuç |
| --- | --- |
| $0$ | $f = O(g)$, ama $f \ne \Theta(g)$ ($f$ kesinlikle yavaş) |
| $0 < L < \infty$ | $f = \Theta(g)$ |
| $\infty$ | $f = \Omega(g)$, ama $f \ne \Theta(g)$ ($f$ kesinlikle hızlı) |

(Limit yoksa, örneğin oran salınıyorsa, bu test bir şey söylemiyor; tanıma dön.)

**Örnek.** $\log n$ ile $n$: $\lim \frac{\ln n}{n} = \lim \frac{1/n}{1} = 0$ (L'Hôpital). $\log n = O(n)$, ve kesinlikle yavaş.

**Örnek.** $n^{100}$ ile $2^n$: L'Hôpital'i 100 kez uygula, pay sabite iner, payda hâlâ $(\ln 2)^{100} 2^n$; limit 0. Her polinom her üstelden yavaş.

Bu tür limitlerden **büyüme hiyerarşisi** çıkıyor; her biri bir sonrakinin $O$'su ama $\Theta$'sı değil:

$$
1 \;<\; \log n \;<\; \sqrt{n} \;<\; n \;<\; n \log n \;<\; n^2 \;<\; n^3 \;<\; 2^n \;<\; n! \;<\; n^n
$$

| $n$ | $\log_2 n$ | $n \log_2 n$ | $n^2$ | $2^n$ |
| --- | --- | --- | --- | --- |
| 10 | 3.3 | 33 | 100 | 1024 |
| 100 | 6.6 | 664 | $10^4$ | $1.3 \cdot 10^{30}$ |
| $10^6$ | 20 | $2 \cdot 10^7$ | $10^{12}$ | (evrendeki atomlardan fazla) |

Logaritmanın tabanı önemsiz: $\log_2 n = \frac{\ln n}{\ln 2}$, aradaki fark sabit bir çarpan. Bu yüzden $O(\log n)$ yazıp tabanı belirtmiyoruz.

---

## 5. Kurallar

Tanımdan kolayca kanıtlanan kurallar (hepsi küçük alıştırmalar):

- **Toplama**: $f_1 = O(g_1)$ ve $f_2 = O(g_2)$ ise $f_1 + f_2 = O(\max(g_1, g_2))$. Ardışık iki döngü: büyüğü kazanır.
- **Çarpma**: $f_1 = O(g_1)$ ve $f_2 = O(g_2)$ ise $f_1 \cdot f_2 = O(g_1 \cdot g_2)$. İç içe iki döngü: çarpılır.
- **Geçişlilik**: $f = O(g)$ ve $g = O(h)$ ise $f = O(h)$. $O$ bir kısmi sıralama gibi davranıyor (Ders 6.7); $\Theta$ ise bir denklik bağıntısı (Ders 6.6), ve "$\Theta(n^2)$" aslında bir denklik sınıfının adı.
- **Polinom**: $a_d n^d + \dots + a_0 = \Theta(n^d)$ ($a_d > 0$).

---

## 6. Döngülerden karmaşıklık çıkarmak

Üç tipik desen; adımları sayıp tahminimizi kontrol edelim.

```c
#include <stdio.h>
#include <stdint.h>
#include <math.h>

static uint64_t pairs(uint64_t n) {          // i < j ciftleri
    uint64_t c = 0;
    for (uint64_t i = 0; i < n; i++)
        for (uint64_t j = i + 1; j < n; j++) c++;
    return c;
}

static uint64_t halving(uint64_t n) {        // her turda yariya indir
    uint64_t c = 0;
    for (uint64_t m = n; m > 1; m /= 2) c++;
    return c;
}

static uint64_t multiples(uint64_t n) {      // her i icin i'nin katlari
    uint64_t c = 0;
    for (uint64_t i = 1; i <= n; i++)
        for (uint64_t j = i; j <= n; j += i) c++;
    return c;
}

int main(void) {
    printf("%7s | %11s %7s | %4s %6s | %8s %7s\n",
           "n", "pairs", "/n^2", "halv", "log2 n", "mult", "/n ln n");
    for (uint64_t n = 10; n <= 100000; n *= 10) {
        uint64_t p = pairs(n), h = halving(n), m = multiples(n);
        double dn = (double)n;
        printf("%7llu | %11llu %7.4f | %4llu %6.2f | %8llu %7.4f\n",
               (unsigned long long)n, (unsigned long long)p, p / (dn * dn),
               (unsigned long long)h, log2(dn),
               (unsigned long long)m, m / (dn * log(dn)));
    }
    return 0;
}
```

```
      n |       pairs    /n^2 | halv log2 n |     mult /n ln n
     10 |          45  0.4500 |    3   3.32 |       27  1.1726
    100 |        4950  0.4950 |    6   6.64 |      482  1.0466
   1000 |      499500  0.4995 |    9   9.97 |     7069  1.0233
  10000 |    49995000  0.5000 |   13  13.29 |    93668  1.0170
 100000 |  4999950000  0.5000 |   16  16.61 |  1166750  1.0134
```

**İç içe, bağımlı sınır** (`pairs`): Ders 6.10'daki çift toplam, $\frac{n(n-1)}{2} = \Theta(n^2)$. Oran $\frac{1}{2}$'ye yaklaşıyor; limit testindeki $0 < L < \infty$ durumu. İç döngünün her seferinde kısalması sabiti yarıya indirdi, büyüme hızını değiştirmedi.

**Yarıya inen** (`halving`): $m$, $n, n/2, n/4, \dots$ diye gidiyor ve 1'e ulaşınca duruyor. $k$ tur sonra $m = n / 2^k$; $2^k \ge n$ olunca bitiyor, yani $k = \lfloor \log_2 n \rfloor$. $\Theta(\log n)$. Ders 2.10'daki ikili arama, Ders 2.9'daki hızlı üs alma, Ders 5.9'daki ikili arama ile `clz` hep bu desen. Tablodaki `halv` sütunu tam $\lfloor \log_2 n \rfloor$.

**Harmonik** (`multiples`): $i$ için iç döngü $\lfloor n / i \rfloor$ kez dönüyor. Toplam $\sum_{i=1}^{n} \lfloor n/i \rfloor \approx n \sum \frac{1}{i} = n H_n$, ve Ders 6.10'dan $H_n \approx \ln n$. $\Theta(n \log n)$. Oran yavaşça 1'e iniyor (fark $\frac{\gamma}{\ln n}$ kadar). Bu desen Ders 6.17'deki Eratosthenes eleğinde karşımıza çıkacak.

Dikkat: üç fonksiyonun ikisi iç içe döngü ama karmaşıklıkları farklı ($n^2$ ve $n \log n$). "İç içe iki döngü $n^2$'dir" bir kural değil; iç döngünün **gerçekte** kaç kez döndüğünü toplamak gerekiyor.

---

## 7. Yaygın hatalar

**"$=$" bir eşitlik değil.** $n = O(n^2)$ ve $n^2 = O(n^2)$, ama $n \ne n^2$. $f = O(g)$ aslında "$f \in O(g)$" demek; $O(g)$, $g$'den hızlı büyümeyen fonksiyonların **kümesi**. Gelenek "$=$" yazmak, ama sadece soldan sağa okunuyor.

**$O$ "en kötü durum" demek değil.** $O$ bir fonksiyon hakkında üst sınır; hangi fonksiyondan bahsettiğin ayrı bir konu. "Ekleme sıralamasının en kötü durumu $\Theta(n^2)$, en iyi durumu $\Theta(n)$" iki farklı fonksiyon hakkında iki ayrı iddia. Ortalama durum (Ders 6.29) üçüncü bir fonksiyon.

**$O$ sıkı değil.** "İkili arama $O(n^2)$" **doğru** bir cümle (üst sınır, ve gevşek). Bilgi verici olanı $\Theta(\log n)$. Pratikte insanlar $O$ deyip $\Theta$'yı kastediyor; kesin konuşmak istediğinde $\Theta$ yaz.

**Sabitler gerçekte önemli olabilir.** $10^6 n$ bir algoritma $n^2$'den ancak $n > 10^6$'da hızlı. Faz 11'de cache etkisiyle $\Theta(n \log n)$ bir algoritmanın $\Theta(n^2)$'lik bir algoritmadan küçük girdilerde yavaş olduğunu ölçeceğiz; standart kütüphanelerin sıralama fonksiyonları da küçük parçalarda ekleme sıralamasına geçiyor.

---

## Alıştırmalar

**1** – Tanımdan $c$ ve $n_0$ bularak kanıtla: (a) $5n + 3 = O(n)$ (b) $n^2 - 10n = \Omega(n^2)$ (c) $2^{n+1} = \Theta(2^n)$. Sonra şunun yanlış olduğunu kanıtla: (d) $2^{2n} = O(2^n)$.

**2** – Şu fonksiyonları büyüme hızına göre sırala: $n \log n$, $\sqrt{n}$, $n^{1.5}$, $(\log n)^2$, $2^{\log_2 n}$, $n!$, $1.01^n$, $n^{100}$.

**3** – Şu kodların karmaşıklığını $\Theta$ ile bul:

```c
// (a)
for (int i = 1; i < n; i *= 2)
    for (int j = 0; j < i; j++) c++;
// (b)
for (int i = 0; i < n; i++)
    for (int j = 1; j < n; j *= 2) c++;
// (c)
for (int i = 0; i * i < n; i++) c++;
```

**4** – $f = O(g)$ ise $g = \Omega(f)$ olduğunu kanıtla. $\Theta$'nın bir denklik bağıntısı olduğunu kanıtla (Ders 6.6'nın üç özelliği).

**5** – Bölüm 6'daki programa (a), (b), (c) kodlarını ekle ve tahmin ettiğin fonksiyona oranlarını yazdır. Oranlar bir sabite yaklaşıyor mu?

<details>
<summary>Cevaplar</summary>

**1** – (a) $n \ge 1$ için $5n + 3 \le 5n + 3n = 8n$: $c = 8$, $n_0 = 1$. (b) $n \ge 20$ için $10n \le \frac{n^2}{2}$, yani $n^2 - 10n \ge \frac{n^2}{2}$: $c = \frac{1}{2}$, $n_0 = 20$. (c) $2^{n+1} = 2 \cdot 2^n$; $c = 2$ ile $O$, $c = 1$ ile $\Omega$. (d) $2^{2n} = 4^n \le c\, 2^n$ olsaydı, $2^n \le c$ olurdu, her $n \ge n_0$ için; ama $2^n$ sınırsız büyüyor. Çelişki. Üsteki sabit çarpan ($2n$) tabanı değiştiriyor ($4^n$), sabit bir çarpan değil.

**2** – $(\log n)^2 < \sqrt{n} < n \log n < n^{1.5} < n^{100} < 1.01^n < n!$, ve $2^{\log_2 n} = n$, $\sqrt n$ ile $n \log n$ arasına giriyor. $(\log n)^k$ her $k$ için her $n^\epsilon$'dan yavaş; $1.01^n$, ne kadar yavaş görünse de, sonunda $n^{100}$'ü geçiyor (çok büyük bir $n$'de, ama geçiyor).

**3** – (a) İç döngü $i = 1, 2, 4, \dots$ değerleri için $i$ kez: $1 + 2 + 4 + \dots < 2n$ (Ders 6.4'teki ikinin kuvvetleri). $\Theta(n)$. İç içe olmasına rağmen doğrusal! Ders 4.24'teki dinamik dizinin büyütme maliyeti de bu toplam. (b) Dış döngü $n$, iç döngü $\lceil \log_2 n \rceil$: $\Theta(n \log n)$. (c) $i^2 < n$ iken, yani $i < \sqrt n$: $\Theta(\sqrt n)$. Ders 2.9'daki asal testi döngüsü (`d * d <= n`) bu.

**4** – $f(n) \le c\, g(n)$ ise $g(n) \ge \frac{1}{c} f(n)$; $\Omega$ tanımı $\frac{1}{c}$ sabitiyle sağlanıyor. $\Theta$ için: *yansıyan*, $f \le 1 \cdot f$ ve $f \ge 1 \cdot f$. *Simetrik*, $f = \Theta(g)$ ise ilk kısımla $g = \Omega(f)$ ve $g = O(f)$. *Geçişli*, $f \le c_1 g$ ve $g \le c_2 h$ ise $f \le c_1 c_2 h$ ($n_0$ olarak ikisinin büyüğü); $\Omega$ yönü aynı. Denklik sınıfları büyüme hızları: $[n^2]$, $3n^2 + 1$, $\frac{n^2}{2}$, $n^2 + n \log n$ hepsini içeriyor.

**5** – (a)'nın $n$'ye oranı, $n$ 2'nin kuvveti değilse 1 ile 2 arasında salınıyor (limit yok ama sınırlı; $\Theta$ yine doğru, Bölüm 4'teki uyarı). (b)'nin $n \log_2 n$'ye oranı 1'e yaklaşıyor. (c)'nin $\sqrt n$'ye oranı 1'e yaklaşıyor. Salınan oran ilginç: limit testinin işe yaramadığı ama tanımın hâlâ çalıştığı bir örnek.

</details>

---

## Kaynaklar

- Thomas Cormen ve diğ., *Introduction to Algorithms* (4. baskı), Bölüm 3: asimptotik notasyon.
- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), Bölüm 9: asimptotikler.
- Donald Knuth, "Big Omicron and Big Omega and Big Theta", *SIGACT News* 8(2), 1976: notasyonun bugünkü tanımlarının kaynağı.

**Sıradaki ders:** Master teoremi. $T(n) = aT(n/b) + f(n)$ biçimindeki böl-yönet bağıntılarını tek bir tabloyla çözmek.
