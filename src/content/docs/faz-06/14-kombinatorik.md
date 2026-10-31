---
title: "6.14 Kombinatorik"
description: "Toplama ve çarpma ilkeleri; permütasyon (n!, P(n,k)) ve kombinasyon (C(n,k)); tekrarlı seçimler ve çubuk-yıldız yöntemi; Pascal üçgeni ve C(n,k) = C(n−1,k−1) + C(n−1,k) özdeşliğinin sayma kanıtı; binom teoremi ve 2ⁿ toplamı; C(n,k)'yı faktöriyelle, çarpımsal formülle, EBOB ile sadeleştirerek ve Pascal üçgeniyle hesaplayan dört C fonksiyonu ve hangisinin hangi n'de sessizce taştığı."
---

Ders 6.5'te $n$ elemanlı bir kümenin $2^n$ alt kümesi olduğunu, alıştırmasında da $\{0, \dots, 4\}$'ün 2 elemanlı alt kümelerinin 10 tane olduğunu **saydık**. Ders 6.10'da üç iç içe döngünün $\frac{n(n+1)(n+2)}{6}$ kez döndüğünü bulduk ve bunun "3 eleman seçmek" olduğunu söyledik. Bu ders, saymayı listelemeden yapmanın dili: **kombinatorik**.

Algoritma analizinde (kaç durum var?), olasılıkta (Ders 6.29: kaç olası sonuç var?) ve kod üretiminde (kaç farklı komut sırası var?) sürekli lazım.

---

## 1. İki ilke

**Toplama ilkesi.** Bir iş ya $A$ yoluyla ya $B$ yoluyla yapılıyorsa ve yollar ortak değilse, toplam $|A| + |B|$ yol var. Kümelerle: $A \cap B = \emptyset$ ise $|A \cup B| = |A| + |B|$.

**Çarpma ilkesi.** Bir iş iki aşamalıysa, ilk aşama $m$ yolla, ikinci aşama (ilkinden bağımsız olarak) $n$ yolla yapılıyorsa, toplam $m \cdot n$ yol var. Kümelerle: $|A \times B| = |A| \cdot |B|$ (Ders 6.5).

Örnekler:

- 8 bitlik bir byte: her bit 2 seçenek, $2^8 = 256$ değer (çarpma).
- C'de bir değişken adı: ilk karakter harf ya da `_` (53 seçenek), sonraki her karakter harf, rakam ya da `_` (63). 3 karakterlik adlar: $53 \cdot 63^2 = 210357$.
- 1 ile 3 karakter arası adlar: $53 + 53 \cdot 63 + 53 \cdot 63^2$ (toplama; uzunluklar ortak değil).

Bütün kombinatorik bu iki ilkenin dikkatli kullanımı. Zorluk, "ortak değil" ve "bağımsız" şartlarının gerçekten sağlanıp sağlanmadığını görmekte.

---

## 2. Permütasyon

$n$ farklı nesneyi **sıraya** dizmenin yolları: ilk yere $n$, ikinciye $n - 1$, ..., sonuncuya 1 seçenek.

$$
n! = n \cdot (n-1) \cdots 2 \cdot 1
$$

$n$ nesneden **$k$ tanesini** sıraya dizmek ($k$-permütasyon):

$$
P(n, k) = n (n-1) \cdots (n - k + 1) = \frac{n!}{(n-k)!}
$$

$n!$ çok hızlı büyüyor: $10! = 3628800$, $20! \approx 2.4 \cdot 10^{18}$ (`uint64_t`'ye sığan son faktöriyel), $21!$ taşıyor. **Stirling formülü** büyüme hızını veriyor:

$$
n! \approx \sqrt{2\pi n} \left(\frac{n}{e}\right)^n
$$

Bu yüzden Ders 6.12'nin hiyerarşisinde $n!$, $2^n$'den sonra geliyor. Bütün permütasyonları deneyen bir algoritma (örneğin gezgin satıcı problemini kaba kuvvetle çözmek) $n = 20$'de bile umutsuz.

---

## 3. Kombinasyon

$n$ farklı nesneden **sırasız** $k$ tanesini seçmek, yani $k$ elemanlı alt küme sayısı:

$$
\binom{n}{k} = \frac{n!}{k!\,(n-k)!}
$$

Neden? $k$-permütasyonları say: $P(n, k)$. Her $k$ elemanlı alt küme, $k!$ farklı sırada yazılabildiği için $k!$ kez sayıldı. Böl: $\frac{P(n,k)}{k!}$. Bu "fazla say, sonra böl" kalıbı Ders 6.6'daki denklik sınıflarının sayma hali: aynı alt kümeyi veren permütasyonlar bir denklik sınıfı, her sınıfta $k!$ eleman.

Simetri: $\binom{n}{k} = \binom{n}{n-k}$. $k$ elemanı seçmek, geride bırakılacak $n - k$ elemanı seçmekle aynı.

Örnekler:

- 52'lik desteden 5 kart: $\binom{52}{5} = 2598960$.
- Ders 6.2'deki `all_distinct`'in karşılaştırma sayısı: $\binom{n}{2} = \frac{n(n-1)}{2}$, her çift bir kez.
- Ders 6.10'daki üç iç içe döngü: $\binom{n+2}{3}$.
- Ders 6.5'teki $n = 5$, $k = 2$: $\binom{5}{2} = 10$. ✓

### Tekrarlı seçim: çubuklar ve yıldızlar

$k$ özdeş topu $n$ farklı kutuya kaç yolla dağıtırız? (Ya da $x_1 + \dots + x_n = k$ denkleminin negatif olmayan tamsayı çözümleri.) Topları yıldız, kutu sınırlarını çubuk olarak yaz: $k$ yıldız ve $n - 1$ çubuk.

```
**|*||***     ->  x1 = 2, x2 = 1, x3 = 0, x4 = 3   (k = 6, n = 4)
```

Her dağıtım, $k + n - 1$ konumdan hangilerinin çubuk olacağını seçmek:

$$
\binom{k + n - 1}{n - 1}
$$

Ders 6.10'daki döngü $0 \le i \le k \le j < n$ biçiminde üç indeksi sıralı seçiyordu; tekrarlı seçimin bir örneği.

---

## 4. Pascal üçgeni

**Teorem.** $1 \le k \le n - 1$ için

$$
\binom{n}{k} = \binom{n-1}{k-1} + \binom{n-1}{k}.
$$

**Kanıt** (sayarak). $\{1, \dots, n\}$'nin $k$ elemanlı alt kümelerini iki gruba ayır: $n$'yi **içerenler** ve **içermeyenler** (toplama ilkesi; gruplar ortak değil). İçerenler: geri kalan $k - 1$ elemanı $n - 1$ elemandan seç, $\binom{n-1}{k-1}$. İçermeyenler: $k$ elemanın hepsini $n - 1$ elemandan seç, $\binom{n-1}{k}$. $\blacksquare$

Bu, Ders 6.5'teki kuvvet kümesi kanıtıyla aynı fikir (bir elemanı seç, onu içerenler ve içermeyenler). Cebirsel kanıt da var ama sayma kanıtı **neden** doğru olduğunu söylüyor.

Özdeşlik, bir tablo kurmanın tarifini veriyor: her sayı, üstündeki iki sayının toplamı.

```
n=0:          1
n=1:         1 1
n=2:        1 2 1
n=3:       1 3 3 1
n=4:      1 4 6 4 1
n=5:     1 5 10 10 5 1
```

### Binom teoremi

$$
(x + y)^n = \sum_{k=0}^{n} \binom{n}{k} x^k y^{n-k}
$$

$(x + y)^n$'yi açınca her terim, $n$ parantezin her birinden ya $x$ ya $y$ seçerek oluşuyor; $x^k y^{n-k}$ terimi, $x$'in hangi $k$ parantezden geldiğini seçme sayısı kadar, $\binom{n}{k}$ kez çıkıyor. Bu yüzden $\binom{n}{k}$'lara **binom katsayıları** deniyor.

$x = y = 1$ koyunca:

$$
\sum_{k=0}^{n} \binom{n}{k} = 2^n
$$

Bütün alt kümeleri büyüklüklerine göre gruplayıp saymak, Ders 6.5'teki $|\mathcal{P}(A)| = 2^n$. $x = -1$, $y = 1$ koyunca $\sum (-1)^k \binom{n}{k} = 0$: çift elemanlı alt kümeler tek elemanlılar kadar. Bu ikinci özdeşlik Ders 6.15'teki içerme–dışlamanın temeli.

---

## 5. $\binom{n}{k}$'yı hesaplamak

Formül basit; ama makinede dört farklı yol dört farklı sonuç veriyor.

**Faktöriyelle.** Formülün kendisi:

```c
static uint64_t binom_fact(int n, int k) {
    uint64_t f[64]; f[0] = 1;
    for (int i = 1; i <= n; i++) f[i] = f[i - 1] * i;   // 21!'den sonra tasar
    return f[n] / (f[k] * f[n - k]);
}
```

```
C(20,10): fact=184756
C(25,12): fact=2
```

$\binom{25}{12} = 5200300$ küçük bir sayı, ama ara değer $25!$ `uint64_t`'yi çoktan aşıyor. İşaretsiz taşma undefined behavior değil (mod $2^{64}$, Ders 3.8), dolayısıyla hiçbir uyarı yok: sadece **yanlış** bir sayı, 2. Sonucun küçük olması ara değerlerin küçük olduğu anlamına gelmiyor.

**Çarpımsal formül.** $\binom{n}{k}$'yı adım adım kur: $\binom{n-k+i}{i} = \binom{n-k+i-1}{i-1} \cdot \frac{n-k+i}{i}$. Her adımda sonuç bir binom katsayısı, dolayısıyla bölme **tam**:

```c
static uint64_t binom_mul(int n, int k) {
    if (k > n - k) k = n - k;
    uint64_t c = 1;
    for (int i = 1; i <= k; i++) c = c * (n - k + i) / i;   // c * (n-k+i) tasabilir
    return c;
}
```

`k > n - k` ise simetriyle küçük olanı kullanıyoruz (Bölüm 3). Çarpmanın bölmeden **önce** yapılması şart: $c \cdot \frac{n-k+i}{i}$'yi önce bölüp sonra çarpsaydık bölme tam olmayabilirdi. Ama bu sefer de $c \cdot (n - k + i)$ ara çarpımı, sonuçtan $n$ kat kadar büyük ve taşabilir.

**EBOB ile sadeleştirerek.** Çarpmadan önce kesri sadeleştir (Ders 2.9). $\frac{c \cdot \text{num}}{\text{den}}$'de, $\text{den}$'i önce $c$ ile, sonra $\text{num}$ ile ortak bölenlerinden arındır; sonuç tam olduğu için $\text{den}$ 1'e iniyor. Geriye kalan çarpma, **gerçek** sonucun bir parçası; taşacaksa gerçekten sığmıyor demek ve bunu çarpmadan önce kontrol edebiliriz:

```c
static bool binom_safe(int n, int k, uint64_t *out) {
    if (k > n - k) k = n - k;
    uint64_t c = 1;
    for (int i = 1; i <= k; i++) {
        uint64_t num = n - k + i, den = i;
        uint64_t g = gcd(c, den); c /= g; den /= g;      // c/den'in paydasi
        g = gcd(num, den); num /= g; den /= g;            // artik den == 1
        if (c > UINT64_MAX / num) return false;           // gercek sonuc sigmiyor
        c *= num;
    }
    *out = c;
    return true;
}
```

`c > UINT64_MAX / num` testi, Ders 3.8'deki taşmayı çarpmadan önce algılama kalıbı.

**Pascal üçgeniyle.** Sadece toplama; ara değerler hiç sonuçtan büyük olmuyor:

```c
static uint64_t P[70][70];
for (int n = 0; n < 70; n++) {
    P[n][0] = P[n][n] = 1;
    for (int k = 1; k < n; k++) P[n][k] = P[n - 1][k - 1] + P[n - 1][k];
}
```

Dördünü karşılaştıralım:

```
C(62,31): mul=465428353255261088 safe=465428353255261088
C(66,33): mul=350360427585442349 safe=7219428434016265740
C(67,33): mul=23341572944240599  safe=14226520737620288370
C(68,34): mul=46683145888481198  safe=sigmiyor
Pascal C(66,33)=7219428434016265740 C(67,33)=14226520737620288370 C(68,34)=10006297401531025124
```

Doğru değerler: $\binom{66}{33} = 7219428434016265740$, $\binom{67}{33} = 14226520737620288370$, $\binom{68}{34} \approx 2.8 \cdot 10^{19} > 2^{64}$.

- `binom_mul` $\binom{66}{33}$'te sessizce yanlış: ara çarpım taştı, sonuç sığdığı halde.
- `binom_safe` sığan her değeri doğru veriyor, sığmayanı **söylüyor**.
- Pascal sığan her değeri doğru veriyor ama $\binom{68}{34}$'te sessizce sarıyor; ayrıca $n^2$ bellek ve zaman istiyor.

Ders: "formül doğru" ile "kod doğru" arasında Faz 3'ün bütün dersleri duruyor. Kombinatorik sayılar, taşmayı test etmenin en iyi yollarından biri: küçük görünen sonuçlar dev ara değerlerden geçiyor. Sonuç da sığmıyorsa Faz 12'deki büyük tamsayılar gerekiyor.

---

## Alıştırmalar

**1** – Bir parola 8 karakter; her karakter küçük harf (26), büyük harf (26) ya da rakam (10). (a) Kaç parola var? (b) En az bir rakam içerenler kaç tane? (İpucu: hiç rakam içermeyenleri çıkar.) (c) Saniyede $10^{10}$ deneme yapan bir saldırgan (a)'daki bütün parolaları ne kadar sürede dener?

**2** – `MISSISSIPPI` kelimesinin harfleriyle kaç farklı dizilim yazılabilir? (Fazla say, böl: aynı harflerin kendi aralarındaki yer değiştirmeleri ayırt edilemez.)

**3** – Sayma kanıtıyla göster: $\sum_{k=0}^{n} \binom{n}{k}^2 = \binom{2n}{n}$. (İpucu: $2n$ kişilik bir gruptan $n$ kişi seç; grubu $n$ erkek ve $n$ kadın olarak ayır.)

**4** – Ders 6.5'teki alt küme gezmeyi kullanarak $\{0, \dots, n-1\}$'in $k$ elemanlı alt kümelerini **sırayla** üreten bir fonksiyon yaz, ama $2^n$ alt kümenin hepsini gezmeden. (İpucu: Gosper'ın hilesi. $x$'in en sağdaki 1'leri grubunu bir sola kaydırıp kalanları en sağa yığ: `c = x & -x; r = x + c; x = (((r ^ x) >> 2) / c) | r;`) Ürettiğin sayıyı $\binom{n}{k}$ ile karşılaştır.

**5** – $\binom{n}{k}$ mod $p$ ($p$ asal) için ara değerlerin taşmadığı bir yöntem: Pascal üçgenini mod $p$'de kur. $\binom{1000}{500} \bmod (10^9 + 7)$'yi hesapla. Neden `binom_mul`'u mod $p$'de çalıştıramıyoruz? (İpucu: mod $p$'de bölme; Ders 6.19.)

<details>
<summary>Cevaplar</summary>

**1** – (a) $62^8 \approx 2.18 \cdot 10^{14}$. (b) Hiç rakamsız: $52^8 \approx 5.35 \cdot 10^{13}$. En az bir rakamlı: $62^8 - 52^8 \approx 1.65 \cdot 10^{14}$. "En az bir" sayılarında tümleyeni saymak neredeyse her zaman kolay (Ders 6.2'deki $\neg \forall \equiv \exists \neg$'nin sayma hali). (c) $2.18 \cdot 10^{14} / 10^{10} \approx 21800$ saniye, 6 saatten biraz fazla. 12 karakterde $62^{12} \approx 3.2 \cdot 10^{21}$: 10 bin yıl. Uzunluk, karakter çeşitliliğinden daha etkili (üstte).

**2** – 11 harf: M bir, I dört, S dört, P iki. $\frac{11!}{1!\,4!\,4!\,2!} = \frac{39916800}{1152} = 34650$. Bu, **çok terimli katsayı**; $\binom{n}{k}$, iki çeşit nesneli özel hali.

**3** – $2n$ kişiden $n$ kişi seçmenin $\binom{2n}{n}$ yolu var. Başka sayalım: seçilenlerden $k$ tanesi erkek, $n - k$ tanesi kadın olsun. Erkekleri $\binom{n}{k}$, kadınları $\binom{n}{n-k} = \binom{n}{k}$ yolla seçeriz (çarpma). $k$'ya göre topla (toplama): $\sum_k \binom{n}{k}^2$. Aynı şeyi iki yolla saydık, iki sonuç eşit. $\blacksquare$ Bu teknik (**çift sayma**) kombinatoriğin en güçlü kanıt yöntemi.

**4** –

```c
void subsets_k(int n, int k) {
    if (k == 0) { /* tek alt kume: bos */ return; }
    uint32_t x = (1u << k) - 1;                    // en kucuk: alt k bit
    int count = 0;
    while (x < (1u << n)) {
        count++;                                   // x'i isle
        uint32_t c = x & -x;                       // en sagdaki 1 (Ders 5.3)
        uint32_t r = x + c;                        // en sagdaki 1 grubunu bir sola tasi
        x = (((r ^ x) >> 2) / c) | r;              // kalan 1'leri en saga yigi
    }
    printf("%d\n", count);                         // C(n, k)
}
```

$n = 10$, $k = 3$ için 120 $= \binom{10}{3}$. Sayılar artan sırada geliyor ve tam $\binom{n}{k}$ adım. ($n = 32$'de `1u << n` undefined behavior; o durumda döngü koşulunu taşmaya göre değiştirmek gerekir.)

**5** –

```c
#define MOD 1000000007u
static uint32_t P[1001][1001];
for (int n = 0; n <= 1000; n++) {
    P[n][0] = P[n][n] = 1;
    for (int k = 1; k < n; k++) P[n][k] = (P[n - 1][k - 1] + P[n - 1][k]) % MOD;
}
// P[1000][500] = 159835829
```

İki sayı $10^9 + 7$'den küçük, toplamları $2^{32}$'den küçük; taşma yok. `binom_mul`'daki `/ i` mod $p$'de çalışmaz: $\frac{a \bmod p}{i}$ genellikle tam değil, çünkü $a$'nın kendisi $i$'ye bölünse bile kalanı bölünmeyebilir. Mod $p$'de "$i$'ye bölmek", $i$'nin **modüler tersiyle** çarpmak demek; Ders 6.19'da bunu hesaplayıp $\binom{n}{k} \bmod p$'yi $O(n)$'de bulacağız.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), Bölüm 6: sayma ilkeleri, permütasyon, kombinasyon, binom katsayıları.
- Ronald Graham, Donald Knuth & Oren Patashnik, *Concrete Mathematics* (2. baskı), Bölüm 5: binom katsayıları.
- Donald Knuth, *TAOCP* Cilt 4A, §7.2.1.3: kombinasyonları üretmek (Gosper'ın hilesi dahil).

**Sıradaki ders:** Güvercin yuvası ilkesi ve içerme–dışlama. Hash çakışmalarının neden kaçınılmaz olduğu, ve Euler'in $\varphi$ fonksiyonu.
