---
title: "8.13 Hash fonksiyonları"
description: "Anahtarı bir kova numarasına çeviren fonksiyon ve neden O(1) aramanın anahtarı olduğu; bölme yöntemi ve 2'nin kuvveti modülün kalıplı anahtarlarda (64·i, 1024·i + 7) çöküşü, asal modül; Knuth'un çarpma yöntemi ve neden üst bitlerin alınması gerektiği; string hash'leri (toplam, K&R 31, djb2, FNV-1a) 235 976 kelimelik sözlükte; çığ etkisi testi: tek bit değişince Knuth 8.8, FNV-1a 12.8, MurmurHash3 fmix32 16.0 bit değiştiriyor; Aa/BB ile 1024 çakışan dizgi ve hash taşkını saldırısı."
---

Ders 8.8–8.12'deki yapılar anahtarları **karşılaştırarak** çalışıyordu: küçükse sola, büyükse sağa. Bu yolla $n$ anahtar arasında arama en az $\log_2 n$ karşılaştırma ister (Ders 9.6'daki alt sınır). **Hash tablosu** bu sınırı karşılaştırmayı bırakarak aşıyor. Anahtarı bir sayıya, bir dizi indeksine çeviriyor ve doğrudan o yuvaya bakıyor: ortalamada $O(1)$. Bunu yapan fonksiyona **hash fonksiyonu** deniyor. Tablonun kendisi Ders 8.14 ve 8.15'te; bu ders sadece fonksiyonu, çünkü tablonun bütün performansı ona bağlı. İyi bir hash fonksiyonuyla tablo $O(1)$, kötüsüyle $O(n)$, yani bir bağlı liste.

---

## 1. Ne istiyoruz

Bir hash fonksiyonu $h$, anahtar evrenini (bütün olası `int`'ler, bütün olası stringler) $\{0, 1, \dots, m - 1\}$ kovalarına eşliyor. Evren kovalardan çok çok büyük olduğu için Ders 6.15'teki güvercin yuvası ilkesi gereği **çakışma** (collision) kaçınılmaz: farklı anahtarlar aynı kovaya düşecek. Tablo çakışmaları çözer; fonksiyonun işi onları **az ve eşit dağılmış** tutmak.

İstenen özellikler:

1. **Deterministik**: aynı anahtar her zaman aynı kova. (Rastgele bir tohum kullanılabilir, ama tablonun ömrü boyunca sabit kalmalı.)
2. **Düzgün dağılım**: gerçek anahtar kümelerinde, kovalar rastgele seçilmiş gibi dolsun. "Gerçek" burada kilit kelime: anahtarlar nadiren rastgele. Ardışık kimlik numaraları, 8'in katı olan adresler, ortak önekli dosya adları.
3. **Hızlı**: her arama ve eklemede çalışıyor. Bir dengeli ağaçtaki 20 karşılaştırmadan daha yavaş bir hash fonksiyonu amacı boşa çıkarır.

Ölçüt olarak şunu kullanacağız: rastgele seçilmiş bir anahtarın kovasında (kendisi dahil) ortalama kaç anahtar var. Zincirlemeli bir tabloda (Ders 8.14) bu, başarılı bir aramanın beklenen maliyeti. Kova doluluklarının $b_j$ ise ölçüt $\sum_j b_j^2 / n$. Anahtarlar kovalara gerçekten rastgele dağılsaydı bu değer yaklaşık $\alpha + 1$ olurdu; $\alpha = n/m$ **yük faktörü**. (Bir anahtarın kovasında kendisi + diğer $n - 1$ anahtarın her biri $1/m$ olasılıkla.)

---

## 2. Tamsayılar: bölme ve çarpma

### Bölme yöntemi

$$h(k) = k \bmod m$$

En basit ve en tehlikeli yöntem. Tehlike $m$'nin seçiminde: Ders 8.5'te `%` yerine `&` kullanmak için kapasiteyi 2'nin kuvveti seçmiştik. $m = 2^r$ ise $k \bmod m$, $k$'nin **sadece alt $r$ biti**. Anahtarların üst bitlerindeki bütün bilgi atılıyor. Anahtarların alt bitleri bir kalıp taşıyorsa (ve gerçek veride çok sık taşır: hizalanmış adresler 8'in, 16'nın, 64'ün katı; Ders 4.26) bütün anahtarlar birkaç kovaya yığılıyor.

### Çarpma yöntemi (Knuth)

$$h(k) = \left\lfloor \frac{(A \cdot k) \bmod 2^{w}}{2^{w - r}} \right\rfloor$$

$w = 32$ bitlik bir sözcükte $k$'yi sabit bir $A$ ile çarp (taşma serbest: işaretsiz aritmetik modülo $2^{32}$, Ders 3.8), sonucun **üst** $r$ bitini al. C'de tek satır: `(k * A) >> (32 - r)`. Knuth'un önerisi $A \approx 2^{32} / \varphi = 2\,654\,435\,769$, yani altın oranın tersi. Bu seçimle ardışık anahtarlar kovalara mümkün olan en düzgün şekilde serpiliyor (Fibonacci hashing; Alıştırma 2'de neden üst bitlerin alındığını göreceğiz).

Çarpma, alt bitlerin üst bitlere **taşınmasını** sağlıyor: çarpımın üst bitleri, $k$'nin bütün bitlerine bağlı. Bölme komutu yok, sadece bir çarpma ve bir kaydırma.

### Ölçüm

8192 anahtarı 1024 kovaya (yük faktörü 8) dört farklı kalıpla yerleştirelim:

```c
/* Tamsayi anahtarlar, 1024 kova: bolme ve carpma yontemleri kalipli anahtarlarla */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define M 1024                                    /* kova sayisi = 2^10 */

static uint32_t mod_1024(uint32_t k)  { return k % 1024; }        /* = k & 1023: sadece alt 10 bit */
static uint32_t mod_1021(uint32_t k)  { return k % 1021; }        /* asal: butun bitler etkiler */
static uint32_t knuth(uint32_t k)     { return (k * 2654435769u) >> (32 - 10); }   /* ust 10 bit */

static void dagilim(const char *ad, uint32_t (*h)(uint32_t), const uint32_t *anahtar, int n, int m) {
    int kova[M] = { 0 }, bos = 0, en = 0;
    for (int i = 0; i < n; i++) kova[h(anahtar[i])]++;
    double kare = 0;
    for (int j = 0; j < m; j++) { if (!kova[j]) bos++; if (kova[j] > en) en = kova[j]; kare += (double)kova[j] * kova[j]; }
    /* ortalama arama maliyeti (zincirleme): rastgele bir anahtarin kovasindaki eleman sayisi */
    printf("    %-10s bos kova %4d/%d   en dolu %4d   anahtar basina kova doluluğu %.2f\n", ad, bos, m, en, kare / n);
}
```

(`main`, dört kalıbı üretip her biri için üç fonksiyonu deniyor; rastgele anahtarlar xorshift32 ile.)

```
$ cc -std=c11 -O2 -Wall tamsayi.c -o tamsayi -lm && ./tamsayi
ardisik  i:
    % 1024     bos kova    0/1024   en dolu    8   anahtar basina kova doluluğu 8.00
    % 1021     bos kova    0/1021   en dolu    9   anahtar basina kova doluluğu 8.03
    Knuth      bos kova    0/1024   en dolu    9   anahtar basina kova doluluğu 8.06
64 * i:
    % 1024     bos kova 1008/1024   en dolu  512   anahtar basina kova doluluğu 512.00
    % 1021     bos kova    0/1021   en dolu    9   anahtar basina kova doluluğu 8.03
    Knuth      bos kova    0/1024   en dolu   12   anahtar basina kova doluluğu 8.68
1024 * i + 7:
    % 1024     bos kova 1023/1024   en dolu 8192   anahtar basina kova doluluğu 8192.00
    % 1021     bos kova    0/1021   en dolu    9   anahtar basina kova doluluğu 8.03
    Knuth      bos kova    0/1024   en dolu    9   anahtar basina kova doluluğu 8.09
rastgele:
    % 1024     bos kova    0/1024   en dolu   18   anahtar basina kova doluluğu 8.99
    % 1021     bos kova    0/1021   en dolu   17   anahtar basina kova doluluğu 9.01
    Knuth      bos kova    0/1024   en dolu   19   anahtar basina kova doluluğu 9.06
(ideal rastgele: bos kova ~0.3, doluluk ~9.00)
```

- `64 * i`'de `% 1024` sadece 16 kova kullanıyor: 64'ün katlarının alt 6 biti hep 0, kalan 4 bit 16 farklı değer alıyor. Arama 64 kat yavaşlıyor. `1024 * i + 7`'de bütün anahtarlar **tek** kovada: alt 10 bit hep `0000000111`. Hash tablosu bir bağlı listeye dönüştü.
- **Asal** modül her kalıpta iyi. Bir asalın, anahtarlardaki kalıbın adımıyla (64, 1024) ortak böleni yok; Ders 6.18'de gördüğümüz gibi $\gcd(d, p) = 1$ ise $d \cdot i \bmod p$, $i = 0, \dots, p - 1$ için bütün kalanları dolaşıyor.
- Knuth'un çarpması da her kalıpta iyi ve bölme yok.
- Kalıplı anahtarlarda iyi fonksiyonlar rastgeleden bile **iyi** sonuç veriyor (8.03 < 9.00): ardışık anahtarları kovalara sırayla, eşit dağıtıyorlar. Rastgele anahtarlarda üç fonksiyon da teorik değerde.

Pratik kural: kova sayısı 2'nin kuvvetiyse (ki `&` ile hızlı indeksleme için genelde öyle), hash fonksiyonu **bütün** bitleri karıştırmak zorunda. Kova sayısı asalsa basit `%` iş görür ama her erişimde bir bölme ödenir (Ders 8.5'teki ölçüm: 3.66 ns'ye karşı 0.79 ns).

---

## 3. Stringler

String bir bayt dizisi; hash fonksiyonu her baytı bir duruma katıp karıştırıyor.

```c
static uint32_t toplam(const char *s) { uint32_t h = 0; while (*s) h += (unsigned char)*s++; return h; }
static uint32_t kr(const char *s)     { uint32_t h = 0; while (*s) h = h * 31 + (unsigned char)*s++; return h; }
static uint32_t djb2(const char *s)   { uint32_t h = 5381; while (*s) h = h * 33 + (unsigned char)*s++; return h; }
static uint32_t fnv1a(const char *s) {
    uint32_t h = 2166136261u;                     /* FNV offset basis */
    while (*s) { h ^= (unsigned char)*s++; h *= 16777619u; }   /* FNV prime: once XOR, sonra carp */
    return h;
}
```

- **toplam**: karakter kodlarını topla. Sıra bilgisi kayboluyor (`"dog"` ile `"god"` aynı) ve sonuç küçük: 10 harfli bir kelimenin toplamı en fazla birkaç bin. 65 536 kovanın çoğuna hiç ulaşamıyor.
- **K&R** (*The C Programming Language*, §6.6): $h = 31h + c$. Dizgiyi 31 tabanında bir sayı gibi okuyor; Ders 3.17'deki `atoi`'nin $h = 10h + c$ döngüsünün aynısı. Java'nın `String.hashCode()`'u da tam bu.
- **djb2** (Daniel J. Bernstein): $h = 33h + c$, başlangıç 5381. `h * 33` derleyicide `(h << 5) + h`.
- **FNV-1a** (Fowler–Noll–Vo): önce baytı XOR'la, sonra özel seçilmiş bir asalla çarp. Basit, hızlı ve dağılımı iyi; Ders 8.14'te kullanacağımız fonksiyon.

macOS'ta (ve çoğu Linux dağıtımında) `/usr/share/dict/words` İngilizce bir kelime listesi. 235 976 kelimeyi $2^{16} = 65\,536$ kovaya, hash'in **alt** 16 bitiyle dağıtalım:

```
$ cc -std=c11 -O2 -Wall string.c -o string -lm && ./string
235976 kelime, 65536 kova, yuk 3.60 (ideal: bos ~1789, doluluk ~4.60)
  toplam   alt bit  bos kova 63406   en dolu   623   doluluk  297.98
  K&R 31   alt bit  bos kova  1788   en dolu    14   doluluk    4.60
  djb2     alt bit  bos kova  1795   en dolu    14   doluluk    4.59
  FNV-1a   alt bit  bos kova  1741   en dolu    14   doluluk    4.59
  toplam("dog")=314 toplam("god")=314   kr("Aa")=2112 kr("BB")=2112
```

`toplam` felaket: kovaların %97'si boş, arama ideal durumdan 65 kat yavaş. Diğer üçü bu gerçek veride ideal rastgele dağılımdan ayırt edilemiyor; boş kova sayısı bile Poisson tahminiyle ($m e^{-\alpha} \approx 1789$) aynı. Doğal veride basit bir çarpımsal hash genelde yeterli. Farklar ortaya çıkıyor ama başka yerlerde: anahtarlar bir kalıp taşıdığında, kovalar başka bitlerden seçildiğinde, ve biri bilerek kötü anahtarlar ürettiğinde.

---

## 4. Çığ etkisi

İyi bir hash fonksiyonunda girdinin **tek bir bitini** değiştirmek, çıktının her bitini $1/2$ olasılıkla değiştirmeli. Buna **çığ etkisi** (avalanche) denir. Ortalama olarak 32 bitten 16'sı değişmeli, ve hiçbir girdi biti ile çıktı biti çifti arasında $1/2$'den sapan bir ilişki olmamalı. Bu, çıktının **herhangi bir** bit alt kümesinin (alt bitler, üst bitler, ortadakiler) kova numarası olarak kullanılabileceğinin garantisi.

32 bitlik tamsayı anahtarlar için üç fonksiyonu deneyelim: Knuth'un çarpması (kaydırma olmadan, tam 32 bit çıktı), 4 bayt üzerinde FNV-1a ve MurmurHash3'ün son karıştırma adımı `fmix32`:

```c
/* Cig etkisi (avalanche): girdinin tek bir bitini cevirince ciktinin kac biti degisiyor? Ideal: 16/32. */
#include <stdint.h>
#include <stdio.h>

static uint32_t knuth(uint32_t k) { return k * 2654435769u; }
static uint32_t fnv1a(uint32_t k) {
    uint32_t h = 2166136261u;
    for (int i = 0; i < 4; i++) { h ^= (k >> (8 * i)) & 0xff; h *= 16777619u; }
    return h;
}
static uint32_t fmix32(uint32_t h) {              /* MurmurHash3'un son karistirma adimi */
    h ^= h >> 16; h *= 0x85ebca6bu;
    h ^= h >> 13; h *= 0xc2b2ae35u;
    h ^= h >> 16;
    return h;
}

static void test(const char *ad, uint32_t (*h)(uint32_t)) {
    static long say[32][32];                      /* say[giris biti][cikis biti]: kac kez degisti */
    for (int i = 0; i < 32; i++) for (int j = 0; j < 32; j++) say[i][j] = 0;
    int N = 100000; uint32_t x = 2463534242u; long toplam = 0;
    for (int t = 0; t < N; t++) {
        x ^= x << 13; x ^= x >> 17; x ^= x << 5;
        uint32_t a = h(x);
        for (int i = 0; i < 32; i++) {
            uint32_t fark = a ^ h(x ^ (1u << i));
            toplam += __builtin_popcount(fark);
            for (int j = 0; j < 32; j++) say[i][j] += (fark >> j) & 1;
        }
    }
    double en_kotu = 0; int ei = 0, ej = 0;
    for (int i = 0; i < 32; i++) for (int j = 0; j < 32; j++) {
        double p = (double)say[i][j] / N, s = p > 0.5 ? p - 0.5 : 0.5 - p;
        if (s > en_kotu) { en_kotu = s; ei = i; ej = j; }
    }
    printf("  %-7s ortalama %5.2f bit degisiyor   en kotu cift: giris %2d -> cikis %2d, olasilik %.3f\n",
           ad, (double)toplam / (32.0 * N), ei, ej, (double)say[ei][ej] / N);
    printf("          giris biti 31 cevrilince cikis bitleri 0..7 degisme olasiligi:");
    for (int j = 0; j < 8; j++) printf(" %.2f", (double)say[31][j] / N);
    printf("\n");
}

int main(void) { test("Knuth", knuth); test("FNV-1a", fnv1a); test("fmix32", fmix32); }
```

(`__builtin_popcount`, Ders 5.8.)

```
$ cc -std=c11 -O2 -Wall cig.c -o cig && ./cig
  Knuth   ortalama  8.77 bit degisiyor   en kotu cift: giris  0 -> cikis  0, olasilik 1.000
          giris biti 31 cevrilince cikis bitleri 0..7 degisme olasiligi: 0.00 0.00 0.00 0.00 0.00 0.00 0.00 0.00
  FNV-1a  ortalama 12.77 bit degisiyor   en kotu cift: giris  0 -> cikis  0, olasilik 1.000
          giris biti 31 cevrilince cikis bitleri 0..7 degisme olasiligi: 0.00 0.00 0.00 0.00 0.00 0.00 0.00 1.00
  fmix32  ortalama 16.00 bit degisiyor   en kotu cift: giris 24 -> cikis 29, olasilik 0.506
          giris biti 31 cevrilince cikis bitleri 0..7 degisme olasiligi: 0.50 0.50 0.50 0.50 0.50 0.50 0.50 0.50
```

- **Knuth**: çarpma sadece **yukarı** doğru taşıma yapıyor. Girdinin $i$. biti çıktının $i$'nci ve üstündeki bitlerini etkiliyor, altındakileri asla. Bit 31'i çevirmek çıktının sadece bit 31'ini değiştiriyor; bit 0'ı çevirmek çıktının bit 0'ını **her zaman** değiştiriyor ($A$ tek sayı). Çıktının alt bitleri girdinin sadece alt bitlerine bağlı. Bu yüzden Knuth yönteminde **üst** bitler alınıyor (`>> (32 - r)`): üst bitler bütün girdi bitlerine bağlı. `& (m - 1)` ile alt bitleri almak, `k % 1024`'ün bütün kusurlarını geri getirir (Alıştırma 2).
- **FNV-1a**: daha iyi ama mükemmel değil. Girdinin son baytı (bit 24–31) sadece **bir** çarpmadan geçiyor. Bit 31'i çevirmek çıktının alt 7 bitini hiç değiştirmiyor, bit 7'sini her zaman değiştiriyor. Uzun stringlerde bu son birkaç baytla sınırlı bir sorun, ama kısa anahtarlarda ve alt bitlerle seçilen kovalarda etkili.
- **fmix32**: ideal. Ortalama tam 16 bit; en kötü girdi-çıktı çifti bile $0.506$. Kaydırma-XOR (`h ^= h >> 16`) üst bitleri **aşağı** taşıyor, çarpma alt bitleri **yukarı** taşıyor; ikisini sırayla iki kez uygulamak her biti her bite yayıyor.

`fmix32` gibi bir "son karıştırıcı" (finalizer), zayıf ama hızlı bir hash'in çıktısına uygulanıp onu güçlendirmek için kullanılabilir. Modern hash fonksiyonları (MurmurHash3, xxHash, wyhash) aynı ilkeyle, bir seferde 8 ya da 16 bayt işleyerek çalışıyor; uzun anahtarlarda bayt bayt ilerleyen FNV'den birkaç kat hızlılar.

---

## 5. Hash taşkını

K&R hash'inde `"Aa"` ve `"BB"` aynı değeri veriyor: $31 \cdot 65 + 97 = 31 \cdot 66 + 66 = 2112$. Bu iki ikiliden yapılmış **her** dizgi de aynı değeri veriyor, çünkü $h$ doğrusal: aynı uzunluktaki iki bloğun katkısı aynıysa, onlarla kurulan dizgilerin hash'i de aynı. $k$ blokla $2^k$ çakışan dizgi:

```
  AaAaAaAaAaAaAaAaAaAa -> 3041952384
  BBAaAaAaAaAaAaAaAaAa -> 3041952384
  AaBBAaAaAaAaAaAaAaAa -> 3041952384
1024 dizginin 1024 tanesi ayni K&R hash'ine sahip
```

Bir web sunucusu, gelen bir isteğin form alanlarını bir hash tablosuna koyuyorsa ve hash fonksiyonu biliniyorsa, saldırgan aynı kovaya düşen on binlerce alan adı gönderebilir. Tablo listeye döner, her ekleme $O(n)$, toplam $O(n^2)$: tek bir istek sunucunun işlemcisini dakikalarca meşgul eder. 2011'de bu saldırı (hash flooding) PHP, Java, Python, Ruby ve ASP.NET'te aynı anda gösterildi.

Çözüm, hash fonksiyonunu saldırganın **bilemeyeceği** hale getirmek: program başlarken rastgele seçilen gizli bir **tohum** (seed) ile çalışan, anahtarlı bir fonksiyon. Bunun için tasarlanmış SipHash (Aumasson ve Bernstein, 2012) bugün Python'un, Rust'ın ve Linux çekirdeğinin ağ kodunun varsayılan string hash'i. Python'da aynı programı iki kez çalıştırınca `hash("abc")`'nin farklı çıkmasının sebebi bu.

| Fonksiyon | Hız | Dağılım | Saldırıya dayanıklılık | Ne zaman |
| --- | --- | --- | --- | --- |
| `k % p` (asal) | Bölme | İyi | Yok | Basit, kova sayısı asal |
| Knuth çarpması | Çok hızlı | İyi (üst bitler) | Yok | Tamsayı anahtarlar, $2^r$ kova |
| FNV-1a | Hızlı (kısa anahtar) | İyi | Yok | Kısa stringler, iç veri |
| xxHash, wyhash | Çok hızlı | Mükemmel | Zayıf | Büyük veri, sağlama toplamı |
| SipHash | Orta | Mükemmel | Var (gizli tohumla) | Dışarıdan gelen anahtarlar |
| SHA-256 | Yavaş | Mükemmel | Kriptografik | Tablo için değil: bütünlük, imza (Faz 12) |

Son satır önemli bir ayrım: **kriptografik** hash fonksiyonları (SHA-256) çakışma bulmayı hesaplama açısından imkânsız kılmak için tasarlanmış ve bunun için çok yavaşlar. Hash tablosu için gereken çok daha zayıf bir özellik; o yüzden tablo hash'leri ondan onlarca kat hızlı.

---

## Alıştırmalar

**1** – Bir programcı kova sayısını $m = 1000$ seçiyor ("yuvarlak sayı"). Anahtarlar 10'un katı olan fiyatlar (kuruş cinsinden: 10, 20, 30, ...). Kaç kova kullanılır? $m = 997$ olsa?

**2** – Knuth'un çarpmasında kova numarasını üst bitler yerine alt bitlerle alırsan, yani `(k * 2654435769u) & 1023`, `1024 * i + 7` anahtarları kaç kovaya düşer? Neden? Çığ testi sonucunu kullanarak açıkla.

**3** – K&R hash'inde `"Aa"` ve `"BB"`'nin çakıştığını gördük. `"Ab"` ile çakışan iki harfli bir dizgi bul. Bu çakışma sınıfı neden sadece K&R'a özgü değil? FNV-1a'da da çakışma bulmak mümkün mü, ve SipHash'i farklı kılan nedir?

**4** – **FNV-1** (FNV-1a'nın eski hali) işlemlerin sırasını değiştiriyor: önce çarp, sonra XOR'la. `"kedi"`, `"kedj"`, `"kedk"` için iki fonksiyonun çıktılarını karşılaştır. FNV-1'in hangi zayıflığı görülüyor ve bunun alt bitleri kova numarası olarak kullanan bir tabloya etkisi ne?

**5** – Bir `struct Nokta { int x, y; }` için hash yazmak istiyorsun. `h = 31 * x + y` neden kötü olabilir? İki alanın hash'lerini birleştirmenin daha iyi bir yolunu öner.

<details>
<summary>Cevaplar</summary>

**1** – $10i \bmod 1000$ sadece 10'un katlarını alabilir: 0, 10, ..., 990. **100** kova kullanılıyor, kovaların %90'ı boş, aramalar 10 kat yavaş. $\gcd(10, 1000) = 10$; genel olarak adımı $d$ olan anahtarlar $m / \gcd(d, m)$ kovaya düşer. $m = 997$ asal: $\gcd(10, 997) = 1$, bütün kovalar kullanılıyor (Ders 6.18). Asal modül, anahtarlarda hangi aritmetik kalıp olursa olsun (adım, asalın katı olmadıkça) bu sorunu önlüyor. "Yuvarlak" sayılar (10'un, 2'nin kuvvetleri) en kötü seçim, çünkü insanların ürettiği veride en sık rastlanan kalıplar onlarla aynı çarpanları taşıyor.

**2** – **Tek** kovaya. Çarpımın alt 10 biti, $k$'nin sadece alt 10 bitine bağlı (çarpmada taşıma sadece yukarı gidiyor): $(A \cdot k) \bmod 2^{10} = (A \bmod 2^{10}) \cdot (k \bmod 2^{10}) \bmod 2^{10}$. Bütün anahtarların alt 10 biti 7 olduğu için hepsi aynı kovaya, $(A \cdot 7) \bmod 1024$'e düşüyor. Çığ testinde gördüğümüz bu: Knuth'ta bit 31'i çevirmek çıktının bit 0–7'sini değiştirme olasılığı **0**. Alt bitler bilgi taşımıyor; Knuth yöntemi ancak üst bitlerle doğru.

**3** – $31 \cdot c_1 + c_2$ sabit kalmalı: $c_1$'i bir azaltıp $c_2$'yi 31 artırmak. `'A' = 65`, `'b' = 98`: $c_1 = 64$ (`'@'`), $c_2 = 129$ (ASCII dışı) olur; ya da tersine $c_1 = 66$ (`'B'`), $c_2 = 67$ (`'C'`): `"BC"`. Kontrol: $31 \cdot 65 + 98 = 2113 = 31 \cdot 66 + 67$. Hash değeri anahtardan küçük bir uzaya eşlendiği sürece çakışmalar her zaman var (güvercin yuvası); soru onları **bulmanın** ne kadar kolay olduğu. FNV-1a gibi gizli tohumsuz her fonksiyon için çakışma üretmek, fonksiyonu bilen biri için mümkün; doğrusal K&R'da kâğıt kalemle, FNV'de biraz arama ile. SipHash'te çıktı gizli bir 128 bitlik anahtara bağlı; o anahtarı bilmeyen saldırgan hangi girdilerin çakışacağını hesaplayamıyor. Çakışmalar hâlâ var, ama saldırgan onları seçemiyor.

**4** –

```
  kedi  FNV-1 a1156424   FNV-1a fb7de756
  kedj  FNV-1 a1156427   FNV-1a fa7de5c3
  kedk  FNV-1 a1156426   FNV-1a f97de430
```

FNV-1'de son karakter çarpmadan **sonra** XOR'lanıyor, yani son karakter hash'in sadece alt 8 bitini değiştiriyor: üç kelimenin FNV-1 değerleri sadece son hex rakamda farklı. Son karakterleri farklı ama geri kalanı aynı anahtarlar (`kayit1`, `kayit2`, ...) üst bitleri tamamen aynı hash'ler alıyor. Kovaları **üst** bitlerle seçen bir tablo bu anahtarları aynı kovaya yığar. Alt bitlerle seçen bir tabloda bu anahtarlar farklı kovalara gider; zayıflık üst bitlerde. FNV-1a'da her karakter en az bir çarpmadan geçiyor ve değişiklik üst bitlere taşınıyor.

**5** – $31x + y$'de $(x, y)$ ve $(x - 1, y + 31)$ çakışıyor: küçük koordinatlı ızgaralarda bu çok sık (`(0, 31)` ve `(1, 0)`). Üstelik doğrusal: bir saldırgan kolayca çakışma üretir. Daha iyisi, alanları **karıştırarak** birleştirmek: `h = fmix32(x); h = fmix32(h ^ y);` ya da Boost'un `hash_combine` kalıbı, `h ^= hy + 0x9e3779b9 + (h << 6) + (h >> 2)` (`0x9e3779b9` Knuth'un $2^{32}/\varphi$ sabiti). İki 32 bitlik alan varsa en basit güçlü yol: onları tek bir 64 bitlik sayıda birleştirip (`((uint64_t)x << 32) | (uint32_t)y`) 64 bitlik bir son karıştırıcıdan geçirmek. Struct'ı `memcpy` ile bayt dizisi olarak hash'lemek ise tehlikeli: dolgu baytlarının değeri belirsiz (Ders 4.26), aynı iki nokta farklı hash alabilir.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.4: hashing; bölme ve çarpma yöntemleri, altın oranla çarpma.
- Brian Kernighan ve Dennis Ritchie, *The C Programming Language* (2. baskı), §6.6: `hash` fonksiyonu ve tablo araması.
- Glenn Fowler, Landon Curt Noll ve Kiem-Phong Vo, "FNV Hash", IETF taslağı `draft-eastlake-fnv`.
- Austin Appleby, *SMHasher* ve MurmurHash3: çığ testi ve `fmix32`.
- Jean-Philippe Aumasson ve Daniel J. Bernstein, "SipHash: a fast short-input PRF", *INDOCRYPT* 2012.
- Alexander Klink ve Julian Wälde, "Efficient Denial of Service Attacks on Web Application Platforms", 28C3, 2011.

**Sıradaki ders:** Hash tablosu: zincirleme. Yük faktörü ve yeniden boyutlandırma.
