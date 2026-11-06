---
title: "9.7 Doğrusal zamanlı sıralama"
description: "Karşılaştırma yapmadan sıralamak ve Ders 9.6'daki Ω(n log n) sınırının dışına çıkmak: sayma sıralaması (sayaç, önek toplamı, kararlı yerleştirme; O(n + k)), en anlamlı olmayan basamaktan başlayan (LSD) radix sıralama ve doğruluğunun kararlılığa dayanması, düzgün dağılımlı sayılar için kova sıralaması; 16 milyon uint32'de radix 0.074 s, birleştirmeli 0.85 s, qsort 1.64 s; 0–127 aralığındaki 16 milyon anahtarda sayma 1.8 ns/eleman; basamak genişliği seçimi (4, 8, 11, 16 bit) ve cache; işaretli sayılar, string'ler ve kovanın kötü dağılımda çöküşü."
---

Ders 9.6'nın alt sınırı kesindi: **karşılaştırmayla** sıralayan hiçbir algoritma en kötü durumda $\log_2 n! \approx n \log_2 n$ karşılaştırmanın altına inemez. Ama ispatın bir varsayımı vardı: algoritma anahtarlar hakkında bilgiyi **sadece** `a < b` sorusuyla alıyor. Anahtarlar tamsayıysa başka sorular da sorabiliriz: "bu anahtarın değeri kaç?" ve "bu anahtarın 3. baytı ne?" Bir değeri doğrudan bir **dizi indeksi** olarak kullanmak, tek bir adımda $\log_2 k$ bitlik bilgi almak demek ($k$ değer aralığı); bir karşılaştırma ise 1 bit veriyor. Bu derstekiler bu fikri kullanıyor ve uygun koşullarda **doğrusal** zamanda sıralıyor.

---

## 1. Kod

```c
/* Karsilastirmasiz siralama: sayma, LSD radix (8 bitlik basamaklar), kova */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct { uint32_t anahtar; char etiket; } Kayit;

/* SAYMA: anahtarlar [0, k). Kararli. O(n + k) zaman, O(n + k) bellek. */
static void sayma(const Kayit *a, Kayit *b, size_t n, uint32_t k) {
    size_t *say = calloc(k + 1, sizeof *say);
    for (size_t i = 0; i < n; i++) say[a[i].anahtar + 1]++;          /* 1) kac tane */
    for (uint32_t v = 0; v < k; v++) say[v + 1] += say[v];             /* 2) onek toplami: v'lerin baslangic yeri */
    for (size_t i = 0; i < n; i++) b[say[a[i].anahtar]++] = a[i];      /* 3) soldan saga yerlestir: kararli */
    free(say);
}

/* LSD RADIX: 32 bitlik anahtar, 4 tur, her turda bir bayt (256 kova) uzerinde sayma siralamasi */
static void radix(uint32_t *a, uint32_t *y, size_t n) {
    for (int kaydir = 0; kaydir < 32; kaydir += 8) {
        size_t say[257] = { 0 };
        for (size_t i = 0; i < n; i++) say[((a[i] >> kaydir) & 0xff) + 1]++;
        for (int v = 0; v < 256; v++) say[v + 1] += say[v];
        for (size_t i = 0; i < n; i++) y[say[(a[i] >> kaydir) & 0xff]++] = a[i];
        uint32_t *t = a; a = y; y = t;                                  /* 4 tur: sonuc yine ilk dizide */
    }
}

/* KOVA: [0, 1) araliginda duzgun dagilmis double'lar. n kova, her kovada ekleme siralamasi. */
static void kova(double *a, size_t n) {
    size_t *bas = calloc(n + 1, sizeof *bas);
    double *y = malloc(n * sizeof *y);
    for (size_t i = 0; i < n; i++) bas[(size_t)(a[i] * n) + 1]++;     /* kova = floor(x * n) */
    for (size_t k = 0; k < n; k++) bas[k + 1] += bas[k];
    size_t *yaz = malloc(n * sizeof *yaz); memcpy(yaz, bas, n * sizeof *yaz);
    for (size_t i = 0; i < n; i++) y[yaz[(size_t)(a[i] * n)]++] = a[i];
    for (size_t k = 0; k < n; k++)                                       /* her kovanin icini sirala: ortalama 1 eleman */
        for (size_t i = bas[k] + 1; i < bas[k + 1]; i++) { double x = y[i]; size_t j = i; while (j > bas[k] && y[j - 1] > x) { y[j] = y[j - 1]; j--; } y[j] = x; }
    memcpy(a, y, n * sizeof *a);
    free(bas); free(y); free(yaz);
}
```

---

## 2. Sayma sıralaması

Anahtarlar küçük bir aralıktaysa ($[0, k)$: yaşlar, notlar, ASCII karakterler, durum kodları) her değerden **kaç tane** olduğunu say, ve buradan her elemanın son yerini hesapla.

1. **Say**: `say[v + 1]`, değeri `v` olan eleman sayısı (bir kaydırılmış olarak, ki ikinci adım doğrudan başlangıçları versin).
2. **Önek toplamı** (Ders 8.19'daki CSR kurulumu ve Ders 6.10'daki kısmi toplamlar): `say[v]`, değeri `v`'den küçük elemanların sayısı, yani `v` değerli elemanların sıralı dizideki **başlangıç** konumu.
3. **Yerleştir**: girdiyi soldan sağa tara, her elemanı kendi değerinin bölgesindeki sıradaki boş yere koy.

$O(n + k)$ zaman, $O(n + k)$ ek bellek. Hiç karşılaştırma yok.

Sıralanan şey sadece anahtarlar değil, **kayıtlar** (burada bir anahtar ve bir etiket). Sadece tamsayıları sıralasaydık sayaçlardan diziyi doğrudan yeniden üretebilirdik ("üç tane 0, iki tane 1..."); ama gerçek hayatta anahtarın yanında taşınan veri var ve onu doğru yere götürmek gerekiyor.

```
sayma: 0d 1b 1e 2f 3a 3c 
```

Girdi `3a 1b 3c 0d 1e 2f`. Sonuçta `1b` `1e`'den, `3a` `3c`'den önce: **kararlı**. Üçüncü adım girdiyi soldan sağa taradığı ve her değerin bölgesini soldan sağa doldurduğu için, eşit anahtarlı elemanlar orijinal sıralarıyla yerleşiyor. Bu özellik bir sonraki algoritmanın temeli.

Sınır: $k$ büyükse sayaç dizisi devasa olur. 32 bitlik anahtarlar için $k = 2^{32}$, 32 GB'lık bir sayaç dizisi. Sayma sıralaması ancak $k = O(n)$ iken doğrusal.

---

## 3. Radix sıralaması

32 bitlik anahtarlar için çözüm, anahtarı **basamaklarına** ayırıp her basamağa ayrı ayrı sayma sıralaması uygulamak. Bu kodda basamak bir bayt (256 değer): 4 tur.

Hangi basamaktan başlamalı? Sezgi en anlamlıdan (en soldaki) başlamayı söyler, ama sihir tersinde: **en anlamsız basamaktan** (LSD, least significant digit) başla, ve her turda **kararlı** bir sıralama kullan.

```
 girdi      1. tur (birler)   2. tur (onlar)   3. tur (yüzler)
  329           720              720              329
  457           355              329              355
  657           436              436              436
  839    ──►    457      ──►     839      ──►     457
  436           657              355              657
  720           329              457              720
  355           839              657              839
```

(Onluk basamaklarla, CLRS'nin örneği.) **Neden doğru?** Değişmez: $d$ turdan sonra dizi, anahtarların son $d$ basamağına göre sıralı. Tur $d + 1$, basamak $d + 1$'e göre sıralıyor. Bu basamakları farklı iki anahtar doğru sıraya giriyor. Bu basamakları **eşit** olan iki anahtar ise, sıralama kararlı olduğu için önceki göreli sıralarını, yani son $d$ basamağa göre sıralarını koruyor. Böylece son $d + 1$ basamağa göre sıralılar. Kararlılık olmasaydı her tur bir önceki turun işini bozardı. (Ders 9.3'teki "önce isme, sonra kararlı sıralamayla şehre göre sırala" ilkesi.)

Maliyet: $b$ bitlik anahtarlar ve $r$ bitlik basamaklarla $\lceil b/r \rceil$ tur, her biri $O(n + 2^r)$. 32 bit ve 8 bitlik basamaklarla 4 tur, $O(4(n + 256)) = O(n)$. Ek bellek, $n$ elemanlık bir yardımcı dizi (her tur iki dizi arasında gidip geliyor; çift sayıda tur olduğu için sonuç baştaki dizide).

**MSD** (en anlamlı basamaktan) radix sıralama da var: en soldaki basamağa göre kovalara ayır, sonra her kovayı **ayrı ayrı** özyinelemeyle bir sonraki basamağa göre sırala. Kararlılık gerekmiyor ama özyineleme ve çok sayıda küçük kova var; değişken uzunluklu anahtarlar (stringler) için doğal seçim (Alıştırma 4).

---

## 4. Kova sıralaması

Anahtarlar $[0, 1)$ aralığında **düzgün dağılmış** gerçel sayılarsa: aralığı $n$ eşit kovaya böl, her elemanı $\lfloor x \cdot n \rfloor$ numaralı kovaya koy, her kovanın içini ekleme sıralamasıyla (Ders 9.3) sırala, kovaları sırayla birleştir. Burada kovalar ayrı listeler değil, sayma sıralamasının aynı önek toplamı yöntemiyle tek bir dizinin bölgeleri.

Düzgün dağılımda bir kovaya düşen beklenen eleman sayısı 1, ve kova içi ekleme sıralamasının beklenen toplam maliyeti $O(n)$ (CLRS 8.4: $\sum E[n_i^2] = 2n - 1$). Toplam beklenen $O(n)$. Ama bu bir **girdi üzerinde ortalama** (Ders 9.1): dağılım düzgün değilse, örneğin bütün sayılar $[0, 0.001)$ içindeyse, hepsi tek bir kovaya düşüyor ve ekleme sıralaması $O(n^2)$ (Alıştırma 5).

---

## 5. Ölçüm

Rastgele 32 bitlik tamsayılar; karşılaştırma için Ders 9.4'ün eşikli birleştirmeli sıralaması ve libc `qsort`. Ayrıca $[0, 128)$ aralığında anahtarlı kayıtlarla sayma sıralaması, ve $[0, 1)$'de düzgün `double`'larla kova sıralaması:

```
$ cc -std=c11 -O2 -Wall -Wextra dogrusal.c -o dogrusal && ./dogrusal
sayma: 0d 1b 1e 2f 3a 3c 
n=1000000, rastgele uint32:
  radix       0.004 s  (3.71 ns/eleman)
  birlestirme 0.044 s  (43.69 ns/eleman)
  qsort       0.084 s  (84.04 ns/eleman)
  sayma [0,128) 0.001 s  (1.46 ns/eleman)
  kova [0,1)  0.011 s  (10.83 ns/eleman)
  qsort double 0.099 s
n=4000000, rastgele uint32:
  radix       0.018 s  (4.51 ns/eleman)
  birlestirme 0.192 s  (48.01 ns/eleman)
  qsort       0.371 s  (92.80 ns/eleman)
  sayma [0,128) 0.006 s  (1.50 ns/eleman)
  kova [0,1)  0.070 s  (17.42 ns/eleman)
  qsort double 0.425 s
n=16000000, rastgele uint32:
  radix       0.074 s  (4.62 ns/eleman)
  birlestirme 0.853 s  (53.31 ns/eleman)
  qsort       1.639 s  (102.46 ns/eleman)
  sayma [0,128) 0.029 s  (1.79 ns/eleman)
  kova [0,1)  0.420 s  (26.26 ns/eleman)
  qsort double 2.173 s
```

(Her sonuç sıralılık için kontrol ediliyor; sanitizer'lı derleme temiz.)

- **Radix sıralama 16 milyon elemanda 0.074 s: birleştirmeli sıralamadan 11.5 kat, `qsort`'tan 22 kat hızlı.** Eleman başına süre neredeyse sabit (3.7 → 4.6 ns): doğrusal. Karşılaştırmalı sıralamaların eleman başına süresi ise $\log n$ ile artıyor (43.7 → 53.3 ns).
- **Sayma** 128 kovayla eleman başına 1.5–1.8 ns: tek bir tur, ve 128 sayaç L1 cache'e sığıyor.
- **Kova** sıralaması küçük $n$'de hızlı, ama eleman başına süresi $n$ ile artıyor (10.8 → 26.3 ns). Algoritma doğrusal; artış bellekten: $n$ kovaya rastgele dağıtmak, her eleman için rastgele bir konuma yazmak demek, ve $n$ büyüyünce bu yazmaların hepsi cache kaçırması (Ders 7.24). Radix'in 256 kovası ise cache'te kalıyor: 256 yazma "akışı", her biri ardışık.

### Basamak genişliği

Basamak genişliği $r$, tur sayısı ($32/r$) ile kova sayısı ($2^r$) arasında bir takas. Aynı 16 milyon eleman:

```
   4 bit (8 tur): 0.161 s 
   8 bit (4 tur): 0.082 s 
  11 bit (3 tur): 0.061 s 
  16 bit (2 tur): 0.076 s
```

11 bit (2048 kova, 3 tur) en hızlısı. 16 bitte tur sayısı yarıya iniyor ama 65 536 sayaç (512 KB) ve 65 536 ayrı yazma noktası artık cache'e sığmıyor. Teori "$r = \log_2 n$ seç" der (CLRS Lemma 8.4: $\Theta(bn / \log n)$); pratikte doğru seçim cache boyutuna bağlı. Kütüphanelerdeki radix sıralamalar genelde 8 ya da 11 bit kullanıyor.

### Ne zaman

Radix sıralama her zaman kazanmıyor. Gereksinimleri: anahtarlar sabit uzunlukta, bitleri anlamlı bir sırada (tamsayılar; ve dönüşümle işaretli tamsayılar ve IEEE `float`'lar, Alıştırma 1 ve Ders 5.18); ve $n$, tur başına sabit maliyeti ($2^r$ sayacı sıfırlamak, gezmek) karşılayacak kadar büyük. Karşılaştırma fonksiyonuyla tanımlanan karmaşık sıralar (isme sonra yaşa göre, Türkçe alfabeyle) için karşılaştırmalı sıralama gerekiyor. Ders 8.23'ün kütüphane sorusu burada tersine: radix sıralama genel bir `void *` arayüzüne uymuyor, çünkü anahtarın **bitlerini** bilmesi gerekiyor.

---

## Alıştırmalar

**1** – Radix sıralamayı **işaretli** `int32_t`'ler için uyarla. İkiye tümleyende negatif sayıların bit desenleri işaretsiz olarak pozitiflerden büyük. Tek bir XOR ile nasıl düzeltirsin? IEEE `float`'lar için ne gerekir (Ders 3.12, 5.18)?

**2** – Sayma sıralamasının 3. adımı girdiyi soldan sağa tarıyordu. Sağdan sola tarayıp her bölgeyi sağdan sola doldursak (CLRS'nin sürümü) yine kararlı mı? Soldan sağa tarayıp bölgeleri **sağdan** sola doldursak?

**3** – $n$ tane, $[0, n^2)$ aralığında tamsayı var. Bunları $O(n)$'de nasıl sıralarsın? (İpucu: radix, taban $n$.) Aralık $[0, n^{10})$ olsaydı?

**4** – $n$ tane küçük harfli İngilizce kelimeyi (değişken uzunlukta) sözlük sırasına dizmek için LSD radix neden uygun değil? MSD radix nasıl çalışır, ve kısa kelimeler (`a`, `an`) nasıl ele alınır?

**5** – Kova sıralamasına bütün sayıların $[0, 0.001)$ içinde olduğu 1 milyon `double` verilirse ne olur? Kovaları verinin gerçek **en küçük** ve **en büyük** değerine göre (sabit $[0, 1)$ yerine) kurmak sorunu tamamen çözer mi?

<details>
<summary>Cevaplar</summary>

**1** – İşaret bitini ters çevir: `u = (uint32_t)x ^ 0x80000000u`. $-2^{31}$ (`0x80000000`) `0x00000000`'a, $-1$ (`0xFFFFFFFF`) `0x7FFFFFFF`'e, $0$ `0x80000000`'a, $2^{31}-1$ `0xFFFFFFFF`'e gidiyor: işaretsiz sıra, işaretli sırayla aynı. Bu dönüşümle sırala (ya da son turda en anlamlı baytın kovalarını ters yorumla), sonra geri çevir. `float`'lar için: pozitif `float`'ların bit desenleri işaretsiz tamsayı olarak zaten doğru sırada (üs önce, sonra mantis; Ders 3.12). Negatiflerde işaret biti 1 ve büyüklük **ters** sırada. Dönüşüm: işaret biti 0 ise sadece işaret bitini çevir, 1 ise **bütün** bitleri çevir: `u ^ ((u >> 31) ? 0xFFFFFFFF : 0x80000000)`. Ders 5.18'deki float bit hilelerinden biri.

**2** – Sağdan sola tarayıp her bölgeyi sağdan sola doldurmak (sayaçları **bitiş** konumları olarak kullanıp her yerleştirmede azaltmak) kararlı: bir değerin en sağdaki elemanı bölgenin en sağına gidiyor, yani orijinal göreli sıra yine korunuyor. CLRS'nin sürümü bu. Ama soldan sağa tarayıp bölgeleri sağdan sola doldurmak eşit elemanların sırasını **tersine** çeviriyor: kararsız. Radix sıralamada bu her turda bir önceki turu bozar ve sonuç yanlış olur. Tarama yönü ile doldurma yönü aynı olmalı.

**3** – Her sayıyı taban $n$'de iki basamaklı olarak yaz: $x = q \cdot n + r$, $0 \le q, r < n$. İki tur LSD radix: önce $r = x \bmod n$'ye göre, sonra $q = x / n$'ye göre, her biri $n$ kovalı sayma sıralaması, $O(n + n) = O(n)$. Aralık $[0, n^{10})$ ise 10 basamak, 10 tur, yine $O(n)$ (sabit 10). Genel olarak $[0, n^c)$ aralığı $O(cn)$. Bu, "sıralama $\Omega(n \log n)$" sözünün neden sadece karşılaştırma modelinde geçerli olduğunun bir örneği: kelime boyutu $O(\log n)$ bit olan tamsayılar doğrusal zamanda sıralanabiliyor.

**4** – LSD en sağ basamaktan başlıyor; ama değişken uzunlukta kelimelerde "en sağ basamak" kelimeden kelimeye farklı bir konum. Kelimeleri en uzun kelimenin uzunluğuna boşluk karakteriyle doldurmak (boşluk harflerden küçük) işe yarıyor ama kısa kelimeler için gereksiz turlar yapıyor. MSD: ilk harfe göre 27 kovaya ayır (26 harf + "kelime bitti" kovası, ki en küçük kova: `a`, `an`'den önce gelir), sonra her kovayı ikinci harfe göre özyinelemeyle sırala. Ortak öneki olmayan kelimeler birkaç harfte ayrılıyor; maliyet, kelimeleri birbirinden ayırt etmek için gereken toplam harf sayısıyla orantılı. Küçük kovalar için ekleme sıralamasına geçmek şart, yoksa her küçük kovada 27 sayaçlık sabit maliyet baskın olur. Ders 8.17'deki trie, bu özyinelemenin veri yapısı hali; MSD radix sıralama bir trie'yi kurup önek gezinmeyle (Ders 8.7) okumakla aynı sırayı veriyor.

**5** – $\lfloor x \cdot n \rfloor$ bütün $x < 0.001$ için $< 1000$; 1 milyon eleman ilk 1000 kovaya düşüyor, kova başına 1000 eleman ve kova içi ekleme sıralaması kova başına yaklaşık $1000^2/4$ işlem: toplam $250$ milyon, doğrusalın 250 katı. Bütün sayılar aynıysa tek kova, $O(n^2)$. Kovaları gerçek $[\min, \max]$ aralığına göre kurmak bu örneği düzeltir (veri $[0, 0.001)$'e yayılır), ama tamamen çözmez: aralığın içinde dağılım düzgün değilse (örneğin değerlerin %99'u bir uçta kümelenmiş, birkaç aykırı değer öbür uçta) kovalar yine dengesiz olur. Kova sıralamasının garantisi dağılım varsayımına bağlı. Sağlam bir uygulama, büyük kovaları özyinelemeyle tekrar kovalara ayırıyor ya da kova içinde ekleme yerine $O(m \log m)$ bir sıralama kullanıyor; o zaman en kötü durum $O(n \log n)$'e iniyor.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 8.2–8.4: sayma, radix ve kova sıralaması.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 5.2 (dağıtarak sıralama) ve 5.2.5 (radix sıralama).
- Robert Sedgewick ve Kevin Wayne, *Algorithms* (4. baskı), Bölüm 5.1: string sıralama, LSD ve MSD radix.
- Michael Herf, "Radix Tricks", 2001: 11 bitlik basamaklar ve `float`'ları radix ile sıralamak.
- Peter McIlroy, Keith Bostic ve M. Douglas McIlroy, "Engineering Radix Sort", *Computing Systems* 6(1), 1993.

**Sıradaki ders:** Seçim algoritmaları. Quickselect ve medyanların medyanı.
