---
title: "7.22 Dal tahmini"
description: "Boru hattının dalın sonucunu beklememek için tahmin yürütmesi: statik tahmin (hep alınır, geri dallar alınır), dinamik tahmin, 1 bitlik ve 2 bitlik doyumlu sayaç, dal geçmişi ve korelasyonlu tahminciler; farklı dal desenlerinde isabeti ölçen bir simülatör; aynı verinin sıralı ve karışık hallerinde aynı döngünün ~10 kat hız farkı (Apple M2); dalsız koda (csel/cmov) çevirmenin tahmin hatasını nasıl ortadan kaldırdığı."
---

Ders 7.21'in sonunda kontrol tehlikesini gördük: dalın sonucu boru hattının derinlerinde belli oluyor, ama IF her döngüde **bir şey** getirmek zorunda. Modern işlemcinin cevabı: **tahmin et**, tahmine göre getirmeye ve hatta çalıştırmaya devam et, yanlış çıkarsa yapılan işi çöpe at. Bu dersin sonunda, tek bir C satırının sadece **verinin sırası** değişince 10 kat yavaşladığı bir deney yapacağız; sebebi tamamen bu tahmin mekanizması.

---

## 1. Neden tahmin şart?

Ders 7.21'in 4. alıştırmasında hesapladık: dalların %20 olduğu bir programda yanlış tahmin cezası 15 döngüyse ve tahmincinin isabeti %40 ise CPI 2.8'e çıkıyor. Modern bir çekirdekte ceza 15–20 döngü, ve işlemci her döngüde 4–8 komut başlatabiliyor (Ders 7.23): bir yanlış tahmin **yüzlerce komutluk** bir fırsat kaybı. Bu yüzden tahmin isabeti %95'in üstünde olmak zorunda, ve gerçekten öyle: tipik programlarda modern tahminciler %97–99 isabetle çalışır. Kalan %1–3 bile ölçülebilir bir yavaşlama.

Tahminin iki parçası var:

- **Yön:** dal alınacak mı? (Bu ders.)
- **Hedef:** alınırsa nereye? Koşullu dallarda hedef komutta yazılı (`PC + imm`), ama IF komutu çözmeden bunu bilmiyor. İşlemci **dal hedef tamponu** (BTB, branch target buffer) adlı küçük bir önbellekte "bu adresteki dal en son şuraya gitmişti" bilgisini tutar. `ret` için ayrı bir dönüş adresi yığını (return stack buffer) var.

---

## 2. Statik tahmin

Hiçbir geçmiş tutmadan, sadece koda bakarak tahmin:

- **Hep alınmaz:** en basit, `PC + 4`'ten devam et. Ders 7.21'deki "tahmin et ve iptal et" stratejisi.
- **Hep alınır.**
- **Geri dallar alınır, ileri dallar alınmaz** (BTFNT, backward taken forward not taken): geri giden dal (hedef < PC) genelde bir döngünün sonudur ve döngüler çok tekrarlanır; ileri dal genelde bir `if`'tir ve çoğu zaman "hata durumu" gibi nadir bir yola gider.

Derleyiciler bunu bilir ve kodu buna göre yerleştirir. Ders 7.5'te gördüğümüz döngü düzeni (koşul kontrolü döngü **sonunda**, geri dal) tam bu yüzden. C'de `__builtin_expect(kosul, 0)` (Linux çekirdeğindeki `unlikely()` makrosu) derleyiciye "bu dal nadiren alınır" der; derleyici nadir yolu fonksiyonun sonuna taşır ki sık yol düz bir çizgi olsun.

---

## 3. Dinamik tahmin: sayaçlar

**1 bitlik tahminci:** her dal için bir bit, "en son ne olduysa yine o olur". Sorunu bir döngüde görülür: 10 turluk bir iç döngünün dalı 9 kez alınır, 1 kez alınmaz. Çıkışta "alınmaz" öğrenilir; döngüye bir daha girildiğinde ilk turda yanlış tahmin, sonra yine "alınır" öğrenilir. Her döngü çalışmasında **iki** hata.

**2 bitlik doyumlu sayaç:** dört durum, 0–3.

```
  alinir          alinir          alinir
 ------->        ------->        ------->
0 (guclu D)     1 (zayif D)     2 (zayif A)     3 (guclu A)
 <-------        <-------        <-------
 alinmaz         alinmaz         alinmaz

tahmin: 0, 1 -> alinmaz (D);  2, 3 -> alinir (A)
```

Alınınca bir artır (3'te dur), alınmayınca bir azalt (0'da dur). Tahmin değiştirmek için **üst üste iki** ters sonuç gerekir. Döngü çıkışındaki tek "alınmaz" sayacı 3'ten 2'ye indirir, tahmin hâlâ "alınır": döngü başına tek hata.

Bunları farklı dal desenlerinde ölçen bir simülatör:

```c
/* Dal tahmincileri: statik, 1 bitlik ve 2 bitlik sayac; farkli dal desenlerinde isabet */
#include <stdio.h>
#include <stdlib.h>

#define N 100000

/* 2 bitlik doyumlu sayac: 0,1 = "alinmaz" tahmini; 2,3 = "alinir" */
static int iki_bit(const int *dal, int n) {
    int sayac = 2, dogru = 0;
    for (int i = 0; i < n; i++) {
        int tahmin = sayac >= 2;
        dogru += (tahmin == dal[i]);
        if (dal[i]) { if (sayac < 3) sayac++; }
        else        { if (sayac > 0) sayac--; }
    }
    return dogru;
}

static int bir_bit(const int *dal, int n) {          /* son sonucu tekrar et */
    int son = 1, dogru = 0;
    for (int i = 0; i < n; i++) { dogru += (son == dal[i]); son = dal[i]; }
    return dogru;
}

static int statik(const int *dal, int n) {           /* hep "alinir" de */
    int dogru = 0;
    for (int i = 0; i < n; i++) dogru += (dal[i] == 1);
    return dogru;
}

static void dene(const char *ad, const int *dal) {
    printf("%-26s statik %5.1f%%   1-bit %5.1f%%   2-bit %5.1f%%\n", ad,
           100.0 * statik(dal, N) / N, 100.0 * bir_bit(dal, N) / N,
           100.0 * iki_bit(dal, N) / N);
}

int main(void) {
    static int dal[N];
    for (int i = 0; i < N; i++) dal[i] = 1;
    dene("hep alinir", dal);
    for (int i = 0; i < N; i++) dal[i] = (i % 10) != 9;     /* 10 turluk ic dongu */
    dene("dongu (9 alinir, 1 cikis)", dal);
    for (int i = 0; i < N; i++) dal[i] = i % 2;
    dene("donusumlu (0,1,0,1...)", dal);
    srand(42);
    int v[N];
    for (int i = 0; i < N; i++) v[i] = rand() % 256;
    for (int i = 0; i < N; i++) dal[i] = v[i] >= 128;
    dene("rastgele veri >= 128", dal);
    for (int i = 0; i < N; i++) dal[i] = i >= N / 2;        /* sirali verinin deseni */
    dene("sirali veri >= 128", dal);
    return 0;
}
```

```
$ cc -O1 -Wall tahmin.c -o tahmin && ./tahmin
hep alinir                 statik 100.0%   1-bit 100.0%   2-bit 100.0%
dongu (9 alinir, 1 cikis)  statik  90.0%   1-bit  80.0%   2-bit  90.0%
donusumlu (0,1,0,1...)     statik  50.0%   1-bit   0.0%   2-bit   0.0%
rastgele veri >= 128       statik  49.9%   1-bit  49.9%   2-bit  49.7%
sirali veri >= 128         statik  50.0%   1-bit 100.0%   2-bit 100.0%
```

Satır satır:

- **Döngü:** 1 bit 10 turda 2 hata (%80), 2 bit 1 hata (%90). Bölüm 3'teki analiz.
- **Dönüşümlü:** sayaçların en kötü durumu. 1 bit her seferinde bir önceki sonucu tahmin ediyor ve desen her seferinde değişiyor: %0. 2 bit sayaç 2 ile 1 arasında gidip geliyor, yine her seferinde yanlış. Hiçbir sayaç bunu öğrenemez, çünkü sayaç sadece "ne sıklıkta" sorusunu cevaplıyor, "hangi sırayla"yı değil.
- **Rastgele:** **hiçbir** tahminci yazı-turayı %50'den iyi tahmin edemez. Desen yok, öğrenilecek bir şey yok.
- **Sıralı:** aynı veri sıralanınca dal önce 50 000 kez alınmaz, sonra 50 000 kez alınır. Dinamik tahminciler geçişte bir iki hata yapıp gerisini bilir: %100 (yuvarlanmış; gerçekte 100 000'de 1–2 hata).

### Geçmişe bakan tahminciler

Dönüşümlü deseni çözmek için tahminci "bu dal en son ne yaptı?" sorusunu da sormalı: son sonuç 0'sa sıradaki 1, 1'se sıradaki 0. **İki seviyeli** tahminciler bunu yapar: son $h$ dal sonucunu bir **geçmiş register'ında** tutar ve her geçmiş deseni için ayrı bir 2 bit sayaç kullanır. 1 bitlik geçmişle dönüşümlü desen %100 olur (Alıştırma 3). Gerçek tahminciler (gshare, TAGE, ve son yıllarda küçük sinir ağları: perceptron tahmincileri) onlarca dalın geçmişini, dalın adresiyle karıştırıp binlerce sayaçlık tablolara bakıyor. Bu yüzden 10 turluk bir döngünün çıkışını bile tahmin edebiliyorlar: son 9 sonuç "alındı" ise sıradaki "alınmaz".

Ama rastgele veriyi hiçbiri tahmin edemez. Bunu gerçek bir işlemcide görelim.

---

## 4. Deney: sıralı ve karışık dizi

Bir milyon rastgele sayı (0–255), ve 128'den büyük olanları toplayan bir döngü. Aynı veriyi önce karışık, sonra sıralanmış halde topluyoruz. Toplam iki durumda da **aynı**; değişen sadece dalın deseni.

```c
/* Dal tahmini deneyi: ayni veri, sirali ve karisik; ayni toplam, farkli sure */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

#define N 1000000
#define TEKRAR 50

static int karsilastir(const void *a, const void *b) {
    return *(const int *)a - *(const int *)b;
}

static double simdi(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

/* Dalli surum. Bos asm, derleyicinin dali "csel/cmov" ile dalsiz koda
   cevirmesini engeller: deneyi gormek icin dalin gercekten kalmasi gerekiyor. */
__attribute__((noinline))
static long topla_dalli(const int *d, int n) {
    long s = 0;
    for (int i = 0; i < n; i++)
        if (d[i] >= 128) {        /* veri rastgeleyse bu dal %50 tahmin edilemez */
            s += d[i];
            __asm__ volatile("");
        }
    return s;
}

/* Dalsiz surum: derleyici normalde zaten bunu uretir (csel/cmov) */
__attribute__((noinline))
static long topla_dalsiz(const int *d, int n) {
    long s = 0;
    for (int i = 0; i < n; i++) {
        long maske = -(long)(d[i] >= 128);   /* kosul dogruysa ...1111, degilse 0 */
        s += d[i] & maske;
        __asm__ volatile("");
    }
    return s;
}

static void olc(const char *ad, long (*f)(const int *, int), const int *d) {
    double t0 = simdi();
    long s = 0;
    for (int r = 0; r < TEKRAR; r++) s += f(d, N);
    double t = simdi() - t0;
    printf("%-16s toplam=%ld  sure=%.3f s  (%.2f ns/eleman)\n",
           ad, s, t, t * 1e9 / ((double)N * TEKRAR));
}

int main(void) {
    int *d = malloc(N * sizeof *d);
    srand(42);
    for (int i = 0; i < N; i++) d[i] = rand() % 256;
    olc("dalli, karisik", topla_dalli, d);
    olc("dalsiz, karisik", topla_dalsiz, d);
    qsort(d, N, sizeof *d, karsilastir);
    olc("dalli, sirali", topla_dalli, d);
    olc("dalsiz, sirali", topla_dalsiz, d);
    free(d);
    return 0;
}
```

Bir tuzak: derleyici akıllı. Bu kadar basit bir `if`'i kendiliğinden **dalsız** koda çevirir (Ders 5.5'teki teknik, makine düzeyinde: arm64'te `csel`, x86-64'te `cmov`, Ders 7.9). O zaman ölçecek dal kalmaz. `if` gövdesindeki boş `__asm__ volatile("")` derleyiciye "burada görünmeyen bir şey oluyor, bu kodu koşullu tut" der ve dalı korur. `topla_dalsiz`'daki asm da derleyicinin 50 tekrarı "aynı sonuç" diye tek bir çağrıya indirmesini engelliyor.

Sonuçlar (Apple M2, macOS, `cc -O2`; üç çalıştırmadan biri, diğerleri ±%15 içinde):

```
$ cc -O2 -Wall dal.c -o dal && ./dal
dalli, karisik   toplam=4783441000  sure=0.148 s  (2.97 ns/eleman)
dalsiz, karisik  toplam=4783441000  sure=0.029 s  (0.58 ns/eleman)
dalli, sirali    toplam=4783441000  sure=0.015 s  (0.30 ns/eleman)
dalsiz, sirali   toplam=4783441000  sure=0.029 s  (0.58 ns/eleman)
```

- **Dallı, karışık: 2.97 ns.** Dal yarı yarıya rastgele; tahminci %50 yanılıyor. Eleman başına ~10 döngü (M2 ~3.5 GHz'de 2.97 ns). Sıralı sürümle fark 2.67 ns, ve bu fark elemanların yarısındaki yanlış tahminden geliyor: yanlış tahmin başına ~5.3 ns, yani **~18 döngü** kayıp.
- **Dallı, sıralı: 0.30 ns, 10 kat hızlı.** Aynı kod, aynı veri, aynı toplam. Tahminci neredeyse hiç yanılmıyor.
- **Dalsız: her iki durumda 0.58 ns.** Dal yok, tahmin edilecek bir şey yok, verinin sırası önemsiz. Karışık veride dallı sürümden 5 kat hızlı; sıralı veride ise dallı sürümün yarı hızında, çünkü dalsız kod **her** elemanda karşılaştırma + seçme yapıyor, doğru tahmin edilen dal ise alınmayan yolda toplamayı tamamen atlıyor.

Dallı döngünün çekirdeği (`objdump`, arm64):

```
1000007e4:  ldr   w10, [x0], #0x4        ; d[i]
1000007e8:  cmp   w10, #0x80
1000007ec:  b.lt  0x1000007dc            ; < 128 ise toplamayi atla  <-- tahmin edilen dal
1000007f0:  add   x8, x8, x10
```

Dalsız sürümü derleyici, bizim maske ifademizi tanıyıp yine tek bir seçme komutuna çevirmiş:

```
100000814:  ldr   w10, [x0], #0x4
100000818:  cmp   w10, #0x7f
10000081c:  csel  w10, w10, wzr, gt      ; > 127 ise d[i], degilse 0  (dal yok)
100000820:  add   x8, x8, w10, sxtw
```

(x86-64'te gcc aynı yeri `cmovle` ile derliyor.) Ders: **dalsız kod tahmin edilemeyen dallarda kazanır, tahmin edilebilir dallarda kaybedebilir.** Derleyici hangisinin olduğunu bilemez (veriyi görmüyor); bu yüzden profil güdümlü optimizasyon (PGO, Faz 11) var: program gerçek veriyle bir kez çalıştırılır, dal istatistikleri toplanır, derleyici ikinci derlemede bu bilgiyi kullanır.

Bir de güvenlik notu: işlemci tahmin ettiği yolu **gerçekten çalıştırır** (spekülatif yürütme) ve yanlışsa sonuçları atar. Ama atılan komutlar önbellekte iz bırakabiliyor; 2018'de bulunan Spectre açıkları bu izi ölçerek veri sızdırmanın mümkün olduğunu gösterdi. Bugün işletim sistemleri ve derleyiciler buna karşı önlemler içeriyor (örneğin `-mspeculative-load-hardening`).

---

## Alıştırmalar

**1** – 2 bitlik sayaç 2'den (zayıf alınır) başlıyor. Dal deseni A, A, D, A, D, D, A (A = alınır, D = alınmaz). Her adımda sayacın değerini, tahmini ve doğru/yanlış olduğunu yaz. Kaç isabet?

**2** – Bir dalın 1000 çalıştırmasında desen: 100 kez A, 100 kez D, tekrar (5 blok A, 5 blok D). 1 bit ve 2 bit tahmincinin hata sayısını hesapla.

**3** – Simülatöre 1 bitlik geçmişli bir tahminci ekle: iki ayrı 2 bit sayaç, "son sonuç 0 ise sayaç 0'ı, 1 ise sayaç 1'i kullan". Dönüşümlü desende ve 10 turluk döngü deseninde isabeti ölç. Döngü deseni için kaç bitlik geçmiş gerekir?

**4** – Bölüm 4'teki deneyde `rand() % 256` yerine `rand() % 256 < 250 ? 0 : 255` kullansan (değerlerin %98'i 0) dallı ve dalsız sürümlerin karışık veride hızları nasıl değişir? Tahmin et, sonra ölç.

**5** – `topla_dalli`'daki `__asm__ volatile("")` satırını sil ve `-O2` ile derle. `objdump -d` ile döngüye bak: hangi komutu görüyorsun? Bu durumda sıralı/karışık farkı ne olur?

<details>
<summary>Cevaplar</summary>

**1** –

| Adım | Sayaç (önce) | Tahmin | Gerçek | Sonuç | Sayaç (sonra) |
| --- | --- | --- | --- | --- | --- |
| 1 | 2 | A | A | ✓ | 3 |
| 2 | 3 | A | A | ✓ | 3 |
| 3 | 3 | A | D | ✗ | 2 |
| 4 | 2 | A | A | ✓ | 3 |
| 5 | 3 | A | D | ✗ | 2 |
| 6 | 2 | A | D | ✗ | 1 |
| 7 | 1 | D | A | ✗ | 2 |

7'de 3 isabet. Tek tük D'ler 2 bitlik sayacı devirmiyor (adım 3, 5), ama arka arkaya iki D (5, 6) deviriyor ve hemen ardından gelen A yanlış tahmin ediliyor.

**2** – Her blok geçişinde (A→D ya da D→A): 1 bit tahminci geçişin ilk elemanında 1 hata yapar (sonra yeni yönü bilir). 9 geçiş (10 blok arasında) → **9 hata** (başlangıç tahmini doğruysa). 2 bit: güçlü bir durumdan (3) karşı yöne geçmek için iki ters sonuç gerekir, her geçişte **2 hata** → 18 hata (ilk geçişte sayaç 3'teyse). Uzun bloklarda 1 bit daha iyi; 2 bit, nadir istisnaların olduğu desende (döngü) daha iyi. Hangi tahmincinin iyi olduğu iş yüküne bağlı.

**3** – Dönüşümlü desende **%100** (ilk birkaç adımdan sonra): son sonuç 0'ken sayaç 0 hep "1 gelecek"i, son sonuç 1'ken sayaç 1 hep "0 gelecek"i öğrenir. Döngü deseninde ise yine **%90**: son sonuç 1'ken sıradaki 9 kez 1, 1 kez 0; tek bit geçmiş çıkışı önceden göremez. Döngü çıkışını kesin tahmin etmek için son **9** sonucu görmek gerekir (9 tane A görülünce sıradaki D): 9 bitlik geçmiş. Gerçek tahmincilerin uzun geçmiş tutmasının sebebi bu.

**4** – `rand() % 256 < 250` olasılığı 250/256, değerlerin ~%97.7'si 0: dal neredeyse hep "alınmaz", tahminci ~%98 isabetle çalışır. Ölçüm (M2, ilk soğuk çalıştırmadan sonraki iki çalıştırma): dallı karışık **0.48–0.52 ns**, dalsız karışık **0.58 ns**, dallı sıralı 0.30 ns. Dallı sürüm artık dalsızdan hızlı, ama sıralı veri kadar değil: kalan ~%2.3 yanlış tahmin (eleman başına 0.023 × ~18 döngü ≈ 0.4 döngü ≈ 0.12 ns) hâlâ görünüyor, ve sayılar bu hesapla uyumlu ($0.30 + 0.12 \approx 0.42$, ölçülen 0.48–0.52). "Dalsız her zaman iyi" kuralı yok, verinin dağılımı karar verir. (İlk çalıştırmada değerler daha yüksek çıktı; işlemcinin frekansı daha oturmamıştı. Ölçümü tekrarlamanın sebebi bu.)

**5** – Derleyici `if`'i `csel` (arm64) ya da `cmov` (x86-64) ile dalsız yapar, yani `topla_dalsiz`'ın aynısı olur; sıralı/karışık farkı kaybolur. Ayrıca asm olmadan derleyici fonksiyonun saf olduğunu görüp `olc`'deki 50 çağrıyı tek çağrıya indirebilir, süre anlamsız derecede kısa çıkar (bu ölçüm hatasını ilk denemede biz de yaşadık). Mikro ölçümlerde her zaman üretilen koda bak (Faz 11).

</details>

---

## Kaynaklar

- John Hennessy & David Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Bölüm 3.3: dal tahmini, korelasyonlu ve turnuva tahmincileri.
- Scott McFarling, "Combining Branch Predictors" (DEC WRL Technical Note TN-36, 1993): gshare.
- André Seznec, "A new case for the TAGE branch predictor" (MICRO 2011).
- Daniel Jiménez & Calvin Lin, "Dynamic Branch Prediction with Perceptrons" (HPCA 2001).
- Stack Overflow, "Why is processing a sorted array faster than processing an unsorted array?" (2012): bu deneyin en çok okunan anlatımı.
- Paul Kocher ve ark., "Spectre Attacks: Exploiting Speculative Execution" (IEEE S&P 2019).

**Sıradaki ders:** Sırasız yürütme (out-of-order). Register yeniden adlandırma, ROB, superscalar, ILP.
