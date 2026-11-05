---
title: "7.24 Bellek hiyerarşisi"
description: "İşlemci ile bellek arasındaki hız uçurumu; register, L1, L2, L3, RAM, SSD ve disk gecikmeleri ve boyutları; zamansal ve uzamsal yerellik ilkesi; önbelleğin neden işe yaradığı; ortalama bellek erişim süresi (AMAT) formülü; Apple M2 üzerinde rastgele işaretçi kovalama ile çalışma kümesi büyüdükçe gecikmenin 1 ns'den 100 ns'ye merdiven gibi çıkışının ölçülmesi."
---

Ders 7.23'ün bir alıştırmasında, önbellekte olmayan tek bir `lw`'nun sırasız bir çekirdeği bile yüzlerce döngü durdurabildiğini hesapladık. Bu ders o sayının nereden geldiğini anlatıyor. Bir işlemci 0.3 ns'de bir toplama yapabiliyor, ama RAM'den bir sayı okumak 100 ns sürüyor: arada **300 kat** fark var. Bilgisayar mimarisinin son 40 yılının büyük kısmı bu uçurumu kapatmaya çalışan tek bir fikir etrafında döndü: **bellek hiyerarşisi**.

---

## 1. Hız uçurumu

1980'de işlemci ve DRAM aşağı yukarı aynı hızdaydı: bir bellek erişimi bir iki döngü. Sonraki yıllarda işlemciler yılda ~%50 hızlandı, DRAM gecikmesi ise yılda ~%7. Bugün DRAM'in **gecikmesi** 1990'lardakinden pek farklı değil (~50–100 ns); değişen kapasite ve bant genişliği oldu. İşlemci tarafında ise saat 100 kat, döngü başına komut birkaç kat arttı.

Fizik basit: büyük bellek yavaş, hızlı bellek küçük ve pahalı. SRAM (önbellekler, 6 transistör/bit) hızlı ama yer kaplıyor; DRAM (ana bellek, 1 transistör + 1 kapasitör/bit) yoğun ama yavaş ve ayrı bir yongada. Işık bile 1 ns'de sadece 30 cm gidiyor; işlemciden uzakta duran şey yavaş olmak zorunda.

---

## 2. Hiyerarşi

Çözüm, küçük-hızlı ve büyük-yavaş belleklerin katmanlarını üst üste koymak:

| Seviye | Tipik boyut | Tipik gecikme | Döngü (~3.5 GHz) |
| --- | --- | --- | --- |
| Register | ~1 KB (32 × 8 B, + fiziksel register'lar) | 0 | 0 |
| L1 önbellek | 32–192 KB (çekirdek başına) | ~1 ns | 3–5 |
| L2 önbellek | 1–16 MB | 3–5 ns | 10–20 |
| L3 / SLC | 8–64 MB (paylaşımlı) | 10–20 ns | 40–70 |
| RAM (DRAM) | 8–512 GB | 60–120 ns | 200–400 |
| SSD | 0.5–8 TB | ~20–100 µs | ~10⁵ |
| Sabit disk | 1–20 TB | ~5–10 ms | ~10⁷ |

Her seviye bir öncekinden ~10 kat büyük ve ~3–10 kat yavaş. Disk ile RAM arasındaki fark ise **bin kat**: diske gitmek, işlemci için bir "duraklama" değil bir çağ.

Bu sayıları insan ölçeğine çevirmek yardımcı: bir L1 erişimini 1 saniye sayarsak RAM ~1.5 dakika, SSD ~1 gün, sabit disk ~3 ay sürer.

Hiyerarşinin iki kenarı farklı yönetiliyor:

- **Register'lar**: derleyici yönetir (register tahsisi, Faz 16).
- **Önbellekler**: donanım yönetir, programa görünmez. Kod `lw` der; verinin L1'den mi RAM'den mi geldiğini bilmez (sadece süreden anlar).
- **RAM ve disk arası**: işletim sistemi yönetir, sanal bellek ile (Ders 7.27).

---

## 3. Yerellik ilkesi

Küçük bir önbellek büyük bir belleğin hızını nasıl taklit edebiliyor? Çünkü programlar belleğe rastgele erişmez. **Yerellik ilkesi** (principle of locality):

- **Zamansal yerellik** (temporal locality): az önce erişilen bir adrese yakında yine erişilir. Döngü sayaçları, sık çağrılan fonksiyonların kodu, yığının tepesi.
- **Uzamsal yerellik** (spatial locality): bir adrese erişildiyse yakınındaki adreslere de yakında erişilir. Dizileri sırayla gezmek, ardışık komutlar, bir `struct`'ın alanları.

Önbellek ikisini de kullanır:

- Bir veri getirildiğinde **bir süre tutulur** (zamansal).
- Tek bir bayt değil, etrafındaki bütün bir **önbellek satırı** (cache line, tipik 64 bayt; Apple M serisinde 128) getirilir (uzamsal). Bir `int` dizisinin `a[0]`'ı okununca `a[0]`–`a[15]` birlikte gelir; sonraki 15 erişim bedava.

Tipik programlarda L1 isabet oranı %95–99. Bu yüzden ortalama erişim RAM'in değil L1'in hızına yakın. Satır, eşleme ve yer değiştirme ayrıntıları bir sonraki dersin konusu.

---

## 4. AMAT: ortalama bellek erişim süresi

Bir seviyenin etkisini tek bir formülle ölçeriz:

$$
\text{AMAT} = \text{isabet süresi} + \text{ıska oranı} \times \text{ıska cezası}
$$

Iska cezası, bir alt seviyenin AMAT'ı: formül özyinelemeli. Örnek: L1 1 ns, ıska oranı %5; L2 4 ns, L2'ye gelenlerin %20'si ıska; RAM 100 ns.

$$
\text{AMAT}_{L2} = 4 + 0.20 \times 100 = 24 \text{ ns}
$$
$$
\text{AMAT} = 1 + 0.05 \times 24 = 2.2 \text{ ns}
$$

RAM 100 ns olmasına rağmen ortalama erişim 2.2 ns. Ama hassas: L1 ıska oranı %5'ten %10'a çıkarsa AMAT $1 + 0.10 \times 24 = 3.4$ ns, %55 kötüleşme. Ders 7.26'daki "önbellek dostu kod" tamamen bu ıska oranını düşürmekle ilgili.

---

## 5. Deney: hiyerarşiyi ölçmek

Hiyerarşiyi doğrudan görmek için **işaretçi kovalama** (pointer chasing): bir dizide her eleman bir sonraki elemanın indisini tutuyor, ve sıra **rastgele** bir döngü. Her okuma bir öncekinin sonucuna bağlı (Ders 7.23'teki bağlı liste alıştırması): sırasız yürütme hiçbir şeyi paralel yapamaz, önceden getirme (prefetch) bir sonraki adresi tahmin edemez. Ölçülen, saf **gecikme**. Dizinin boyutunu (çalışma kümesi) büyüttükçe veri önce L1'e, sonra L2'ye sığmaz hale gelir.

```c
/* Bellek gecikmesi: rastgele isaretci kovalama, calisma kumesi buyudukce */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double simdi(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

/* Her eleman bir sonraki elemanin indisini tutar; sira rastgele bir dongu.
   Bir sonraki adres, bir onceki okuma bitmeden bilinemez: saf gecikme olcumu. */
static double olc(size_t bayt) {
    size_t n = bayt / sizeof(size_t);
    size_t *zincir = malloc(n * sizeof *zincir);
    size_t *sira = malloc(n * sizeof *sira);
    for (size_t i = 0; i < n; i++) sira[i] = i;
    for (size_t i = n - 1; i > 0; i--) {                 /* Fisher-Yates karistirma */
        size_t j = (size_t)rand() % (i + 1);
        size_t t = sira[i]; sira[i] = sira[j]; sira[j] = t;
    }
    for (size_t i = 0; i < n; i++) zincir[sira[i]] = sira[(i + 1) % n];

    long adim = 20000000;
    size_t p = 0;
    for (long i = 0; i < n; i++) p = zincir[p];          /* isinma */
    double t0 = simdi();
    for (long i = 0; i < adim; i++) p = zincir[p];
    double t = simdi() - t0;
    free(zincir); free(sira);
    if (p == (size_t)-1) puts("");                       /* p'yi "kullan" */
    return t * 1e9 / adim;
}

int main(void) {
    srand(1);
    olc(1 << 20);                                        /* CPU frekansi otursun diye bos tur */
    for (size_t kb = 4; kb <= 512 * 1024; kb *= 4) {
        double ns = olc(kb * 1024);
        if (kb < 1024) printf("%8zu KB  %7.2f ns\n", kb, ns);
        else           printf("%8zu MB  %7.2f ns\n", kb / 1024, ns);
    }
    return 0;
}
```

`zincir[sira[i]] = sira[i+1]`: karıştırılmış sırada her eleman bir sonrakini gösteriyor, sonuncusu ilkini; tek, bütün elemanları dolaşan bir döngü (Fisher–Yates karıştırma: her permütasyon eşit olasılıklı, Ders 6.29'daki olasılık temelleriyle). Baştaki boş tur, işlemcinin düşük güç modundan çıkıp tam frekansa ulaşması için: ilk denemede onsuz 4 KB'ın ölçümü yanlışlıkla 2.2 ns çıktı.

Apple M2, 16 GB RAM (döngü 256 MB'ta bitiyor; sistem bilgisi `sysctl hw.perflevel0.l1dcachesize` = 128 KB, `hw.perflevel0.l2cachesize` = 16 MB, `hw.cachelinesize` = 128):

```
$ cc -O2 -Wall gecikme.c -o gecikme && ./gecikme
       4 KB     1.15 ns
      16 KB     1.15 ns
      64 KB     1.16 ns
     256 KB     3.51 ns
       1 MB     5.09 ns
       4 MB     5.45 ns
      16 MB     9.86 ns
      64 MB    76.54 ns
     256 MB   101.04 ns
```

Bir merdiven:

- **4–64 KB: 1.15 ns.** Her şey L1'de (128 KB). 1.15 ns ≈ 4 döngü: M2'nin L1 yükleme gecikmesi. Daha hızlı olamaz.
- **256 KB – 4 MB: 3.5–5.5 ns.** L1'e sığmıyor, L2'ye (16 MB) sığıyor. ~15–19 döngü.
- **16 MB: ~10 ns.** L2'nin sınırında; bir kısmı L2'de, bir kısmı M2'nin paylaşımlı sistem önbelleğinde (SLC, 8 MB, L3 benzeri).
- **64 MB ve üstü: 75–100 ns.** Çoğu erişim RAM'e gidiyor. ~350 döngü: L1'in **90 katı**. 256 MB'ta ayrıca adres çevirisi önbelleği (TLB, Ders 7.27) de taşıyor ve her erişime bir sayfa tablosu yürüyüşü ekleniyor.

Aynı programın, aynı kodun, aynı sayıda adımın süresi sadece veri boyutu yüzünden 90 kat değişti. Tablodaki sayıları bir kez kendi makinende ölçmek, ezberlemekten daha kalıcı.

---

## 6. Gecikme ve bant genişliği

Bu deney en kötü durumu ölçtü: her erişim bir öncekini bekledi. Gerçek programlar çoğu zaman bundan iyi: bir diziyi sırayla gezerken işlemci bir sonraki adresi önceden bilir, birçok satırı **aynı anda** ister ve donanım **önceden getirici** (prefetcher) "sıralı erişim" desenini fark edip satırları istenmeden getirir. Bu durumda sınır gecikme değil **bant genişliği** (bayt/saniye) olur: M2'de ~100 GB/s, yani bir 64 MB'lık dizi birkaç milisaniyede okunabilir (Ders 7.26'daki ilk deney). Rastgele erişimde aynı 64 MB'ın her 8 baytı 76 ns sürseydi okumak 600 ms'yi bulurdu.

Özet olarak üç tür erişim, üç farklı hız: L1'de duran veri (~1 ns), sırayla akan veri (bant genişliği sınırlı, eleman başına onda bir ns mertebesi), rastgele ve RAM'de duran veri (~100 ns). Veri yapılarını seçerken (Faz 8) bu üçlü, büyük-O kadar önemli.

---

## Alıştırmalar

**1** – L1 isabet süresi 1 ns, ıska oranı %3; L2 isabet süresi 5 ns, yerel ıska oranı %25; RAM 80 ns. AMAT'ı hesapla. L2'yi tamamen kaldırırsak (L1 ıskaları doğrudan RAM'e) AMAT ne olur?

**2** – Bölüm 5'teki tabloda 64 KB'dan 256 KB'a geçişte gecikme 3 kat arttı. M2'nin L1'i 128 KB. Deneye 128 KB ve 192 KB noktaları eklesen ne beklersin? Neden geçiş keskin bir basamak değil de yumuşak olabilir?

**3** – Bir programın döngüsü saniyede 10⁹ yükleme yapıyor ve yüklemelerin %1'i RAM'e gidiyor (100 ns). Sırasız yürütmenin hiçbir şeyi gizleyemediğini varsayarak, bu ıskalar saniyede ne kadar zaman harcar? Mümkün mü? Sonuç ne söylüyor?

**4** – 4 baytlık `int`'lerden oluşan bir diziyi sırayla gezerken, 64 baytlık satırlı bir önbellekte ıska oranı en fazla ne olur? Diziyi 16'şar atlayarak (`a[0]`, `a[16]`, `a[32]`...) gezerken? Hangi yerelliği kaybettin?

**5** – Bölüm 5'teki programda `zincir`'i karıştırmadan, `zincir[i] = i + 1` yapsaydık hangi ölçümü yapmış olurduk? Kendi makinende dene. (Uyarı: bazı işlemcilerde sonuç beklenmedik çıkabilir; cevaplara bak.)

<details>
<summary>Cevaplar</summary>

**1** – $\text{AMAT}_{L2} = 5 + 0.25 \times 80 = 25$ ns. $\text{AMAT} = 1 + 0.03 \times 25 = 1.75$ ns. L2 olmadan: $1 + 0.03 \times 80 = 3.4$ ns, neredeyse iki katı. L2'nin %75'lik isabeti, L1 ıskalarının bedelini 80 ns'den 25 ns'ye indiriyor.

**2** – 128 KB'ta dizi L1'e tam sığıyor gibi görünüyor ama sığmaz: L1'de başka şeyler de var (yığın, `sira` dizisi değil ama programın diğer verisi), ve önbellek küme-ilişkili olduğu için (Ders 7.25) rastgele adreslerin bazı kümelerde çakışması kapasite dolmadan ıskaya yol açar. Bu yüzden ~96–128 KB civarında gecikme yavaş yavaş artmaya başlar, 192 KB'ta çoğu erişim L2'dendir. Gerçek ölçümlerde basamaklar her zaman biraz yuvarlak.

**3** – Saniyede $10^9 \times 0.01 = 10^7$ ıska × 100 ns = **1 saniye**. Yani bütün süre ıskalarla geçer, ve hesap tutmaz: o hızda 10⁹ yükleme yapılamaz. Gerçekte bu program ya çok daha yavaş çalışır (saniyede çok daha az yükleme), ya da ıskalar paralel olduğu için (sırasız yürütme ve önceden getirme sayesinde) bedelleri örtüşür. Sonuç: %1'lik bir RAM ıska oranı bile performansa hâkim olabilir. Yerellik, kodun ne yaptığından çok, verinin nasıl dizildiğiyle ilgili.

**4** – Sıralı: satır başına 16 `int`, ilk erişim ıska, sonraki 15'i isabet: ıska oranı **1/16 ≈ %6** (önceden getirici varsa daha da az). 16'şar atlayarak: her erişim yeni bir satıra düşer, ıska oranı **%100** (önceden getirici sabit adımlı deseni yine tanıyabilir). Kaybedilen uzamsal yerellik: satırın getirilen 64 baytının sadece 4'ü kullanılıyor.

**5** – Sıralı bir zincir: her adım bir sonraki satırdaki ya da aynı satırdaki elemana gidiyor. Klasik beklenti: önceden getirici sıralı deseni yakalar, RAM ölçeğindeki dizilerde bile gecikme L1–L2 düzeyine iner; ama zincir hâlâ bağımlı olduğu için L1 gecikmesinin (~1.15 ns) altına inmemesi gerekir. M2'de denediğimizde küçük boyutlarda 1.13 ns (beklendiği gibi), büyük boyutlarda ise **0.33 ns** ölçtük: L1 gecikmesinden bile hızlı. Bu, bağımlılık zincirinin bir şekilde kırıldığını gösteriyor; olası açıklama, işlemcinin sabit adımla ilerleyen yüklemelerin **değerini ya da adresini** tahmin edip, sonucu beklemeden bir sonraki yüklemeyi spekülatif olarak başlatması (Ders 7.22'deki spekülasyonun veriye uygulanması). Ders: mikro ölçümler, ölçtüğünü sandığın şeyi ölçmeyebilir; rastgele karıştırma, bu deneyin "saf gecikme" ölçmesinin tek garantisi.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 6: bellek hiyerarşisi, yerellik, "bellek dağı" (memory mountain) ölçümü.
- Ulrich Drepper, "What Every Programmer Should Know About Memory" (2007): DRAM'den önbelleğe ayrıntılı anlatım ve işaretçi kovalama ölçümleri.
- Jeff Dean, "Latency Numbers Every Programmer Should Know" (Peter Norvig'in "Teach Yourself Programming in Ten Years" yazısındaki tablodan).
- John Hennessy & David Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Bölüm 2 ve Ek B.

**Sıradaki ders:** Cache organizasyonu. Doğrudan eşlemeli, küme-ilişkili, satır boyutu, tag/index/offset hesabı.
