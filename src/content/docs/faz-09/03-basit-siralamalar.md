---
title: "9.3 Basit sıralamalar"
description: "Seçme, ekleme ve kabarcık sıralaması: her birinin döngü değişmezi ve beş elemanlı bir dizide tur tur iz tablosu; kararlılık: eşit anahtarlı elemanların sırasını seçme sıralamasının bozduğu, ekleme ve kabarcığın koruduğu; 2000 elemanda rastgele, sıralı, ters ve neredeyse sıralı girdilerde karşılaştırma ve yazma sayıları, ekleme sıralamasının ters çiftleri saydığı; aynı Θ(n²) sınıfında kabarcığın ekleme sıralamasından 7 kat yavaş olması; Shell sıralamasına bir bakış."
---

Sıralama, algoritmalar dersinin klasik başlangıç noktası, ve sebebi var: problem herkesin anlayacağı kadar basit, ama çözümleri neredeyse her algoritma tasarım tekniğini (artımlı, böl-yönet, rastgeleleştirme, veri yapısı kullanma) ve her analiz yöntemini (en kötü durum, ortalama durum, alt sınır) sergiliyor. Bu derste $\Theta(n^2)$'lik üç basit sıralamayı yazıyoruz. Büyük diziler için yavaşlar, ama küçük dizilerde ve neredeyse sıralı verilerde hâlâ en hızlı seçenekler; Ders 9.4–9.5'teki hızlı algoritmalar da küçük parçalarda bunlara devrediyor (Ders 8.23'teki hızlı sıralama 16 elemanın altında ekleme sıralamasına geçiyordu).

Bütün dersler boyunca sıralama, bir diziyi **artan** sıraya dizmek: $a[0] \le a[1] \le \dots \le a[n-1]$. Elemanlar bir anahtar taşıyor; bu derste ayrıca bir **etiket**, ki eşit anahtarlı elemanların sırasını izleyebilelim.

---

## 1. Kod

```c
/* Uc basit siralama: secme, ekleme, kabarcik. Iz tablosu, sayaclar, kararlilik. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct { int anahtar; char etiket; } Oge;     /* etiket: kararlilik icin */
static long kars, yazma;                               /* karsilastirma ve dizi yazma sayilari */
static int iz;                                         /* 1: her dis turdan sonra diziyi yaz */

static void yaz(const char *bas, const Oge *a, int n) {
    printf("  %-14s", bas);
    for (int i = 0; i < n; i++) printf(" %d%c", a[i].anahtar, a[i].etiket);
    printf("\n");
}
static int kucuk(Oge x, Oge y) { kars++; return x.anahtar < y.anahtar; }
static void takas(Oge *a, int i, int j) { Oge t = a[i]; a[i] = a[j]; a[j] = t; yazma += 2; }

/* SECME: DEGISMEZ: a[0..i) dizinin en kucuk i elemani, sirali. Kalanin en kucugunu i'ye getir. */
static void secme(Oge *a, int n) {
    for (int i = 0; i < n - 1; i++) {
        int m = i;
        for (int j = i + 1; j < n; j++) if (kucuk(a[j], a[m])) m = j;
        if (m != i) takas(a, i, m);
        if (iz) { char b[16]; snprintf(b, sizeof b, "i=%d", i); yaz(b, a, n); }
    }
}

/* EKLEME: DEGISMEZ: a[0..i) sirali (ama henuz yerlesmemis olabilir). a[i]'yi soldaki yerine kaydir. */
static void ekleme(Oge *a, int n) {
    for (int i = 1; i < n; i++) {
        Oge x = a[i]; int j = i;
        while (j > 0 && kucuk(x, a[j - 1])) { a[j] = a[j - 1]; yazma++; j--; }   /* buyukleri saga kaydir */
        a[j] = x; yazma++;
        if (iz) { char b[16]; snprintf(b, sizeof b, "i=%d", i); yaz(b, a, n); }
    }
}

/* KABARCIK: DEGISMEZ: a[n-i..n) dizinin en buyuk i elemani, sirali. Hic takas olmazsa erken bit. */
static void kabarcik(Oge *a, int n) {
    for (int i = 0; i < n - 1; i++) {
        int takas_oldu = 0;
        for (int j = 0; j + 1 < n - i; j++)
            if (kucuk(a[j + 1], a[j])) { takas(a, j, j + 1); takas_oldu = 1; }
        if (iz) { char b[16]; snprintf(b, sizeof b, "tur %d", i); yaz(b, a, n); }
        if (!takas_oldu) break;
    }
}

typedef void (*Sirala)(Oge *, int);

int main(void) {
    Oge ornek[] = { {3,'a'}, {3,'b'}, {1,'c'}, {2,'d'}, {2,'e'} };
    const char *ad[] = { "secme", "ekleme", "kabarcik" };
    Sirala f[] = { secme, ekleme, kabarcik };
    for (int k = 0; k < 3; k++) {
        Oge a[5]; memcpy(a, ornek, sizeof a);
        printf("%s:\n", ad[k]); iz = 1; yaz("baslangic", a, 5); f[k](a, 5); iz = 0;
    }
    /* sayaclar: n = 2000, dort girdi turu */
    int n = 2000;
    Oge *a = malloc(n * sizeof *a), *b = malloc(n * sizeof *b);
    const char *tur[] = { "rastgele", "sirali", "ters", "neredeyse" };
    printf("\nn=%d  karsilastirma / dizi yazma\n%-10s", n, "");
    for (int g = 0; g < 4; g++) printf(" %22s", tur[g]);
    printf("\n");
    for (int k = 0; k < 3; k++) {
        printf("%-10s", ad[k]);
        for (int g = 0; g < 4; g++) {
            srand(1);
            for (int i = 0; i < n; i++) b[i].anahtar = g == 0 ? rand() : g == 1 ? i : g == 2 ? n - i : i, b[i].etiket = 'x';
            if (g == 3) for (int t = 0; t < 20; t++) { int i = rand() % n, j = rand() % n; Oge x = b[i]; b[i] = b[j]; b[j] = x; }
            memcpy(a, b, n * sizeof *a); kars = yazma = 0; f[k](a, n);
            for (int i = 1; i < n; i++) if (a[i].anahtar < a[i - 1].anahtar) { puts("SIRASIZ"); return 1; }
            printf(" %10ld /%10ld", kars, yazma);
        }
        printf("\n");
    }
    /* sure: rastgele girdi, n ikiye katlanarak */
    printf("\nsure (rastgele, -O2):\n");
    for (int m = 10000; m <= 40000; m *= 2) {
        Oge *c = malloc(m * sizeof *c), *d = malloc(m * sizeof *d);
        srand(2); for (int i = 0; i < m; i++) { d[i].anahtar = rand(); d[i].etiket = 'x'; }
        printf("  n=%6d", m);
        for (int k = 0; k < 3; k++) {
            memcpy(c, d, m * sizeof *c);
            struct timespec t0, t1; clock_gettime(CLOCK_MONOTONIC, &t0); f[k](c, m); clock_gettime(CLOCK_MONOTONIC, &t1);
            printf("  %s %.3f s", ad[k], (t1.tv_sec - t0.tv_sec) + (t1.tv_nsec - t0.tv_nsec) * 1e-9);
        }
        printf("\n"); free(c); free(d);
    }
    free(a); free(b);
}
```

`kucuk` her karşılaştırmayı, `takas` ve kaydırmalar her dizi yazmasını sayıyor. `iz` açıkken her dış turdan sonra dizi yazdırılıyor.

### Seçme sıralaması

Her turda kalan kısmın **en küçüğünü** bul ve başa getir. Değişmez: $a[0..i)$, dizinin en küçük $i$ elemanını sıralı olarak içeriyor. Bir sonraki tur $a[i..n)$'nin en küçüğünü $a[i]$'ye takaslıyor; o eleman kalanların hepsinden küçük ya da eşit, dolayısıyla $a[0..i]$ yine en küçük $i+1$ eleman, sıralı.

Karşılaştırma sayısı girdiden **bağımsız**: $(n-1) + (n-2) + \dots + 1 = n(n-1)/2$. Ama takas sayısı en fazla $n - 1$: bu üçünün içinde en az **yazan** algoritma. Yazmanın pahalı olduğu yerlerde (flash belleğin aşınması, büyük kayıtlar) bir avantaj.

### Ekleme sıralaması

Kart oyuncusunun elindeki kartları dizmesi: her yeni kartı, solundaki zaten sıralı kartların arasında doğru yerine kaydır. Değişmez: $a[0..i)$ sıralı (ama bunlar dizinin en küçük $i$ elemanı değil, sadece ilk $i$ elemanı). Tur, $a[i]$'yi alıp kendisinden büyük olanları birer sağa kaydırıyor ve boşluğa yerleştiriyor.

Kaydırma `takas` değil, tek yazma: eleman `x`'te tutuluyor ve sadece en sonda yazılıyor (Ders 8.12'deki "delik" tekniği).

Maliyet girdiye çok bağlı. Her kaydırma, $a[j] > x$ olan bir $(j, i)$ çiftini düzeltiyor; böyle bir çifte **ters çift** (inversion) denir. Ekleme sıralaması tam olarak ters çift sayısı kadar kaydırma yapıyor (Alıştırma 1): sıralı girdide 0, ters sıralıda $n(n-1)/2$, rastgele girdide ortalama $n(n-1)/4$.

### Kabarcık sıralaması

Komşu çiftleri karşılaştır, yanlış sıradaysa takasla; büyük elemanlar her turda sağa "kabarıyor". Değişmez: $i$ turdan sonra $a[n-i..n)$ dizinin en büyük $i$ elemanını sıralı olarak içeriyor (her tur o anki en büyüğü sona taşıyor). Bir turda hiç takas olmazsa dizi sıralıdır ve erken bitiliyor.

---

## 2. İz tablosu

Beş eleman, iki tane 3 (`a` ve `b`) ve iki tane 2 (`d` ve `e`):

```
$ cc -std=c11 -O2 -Wall -Wextra -fsanitize=address,undefined basit.c -o basit && ./basit
secme:
  baslangic      3a 3b 1c 2d 2e
  i=0            1c 3b 3a 2d 2e
  i=1            1c 2d 3a 3b 2e
  i=2            1c 2d 2e 3b 3a
  i=3            1c 2d 2e 3b 3a
ekleme:
  baslangic      3a 3b 1c 2d 2e
  i=1            3a 3b 1c 2d 2e
  i=2            1c 3a 3b 2d 2e
  i=3            1c 2d 3a 3b 2e
  i=4            1c 2d 2e 3a 3b
kabarcik:
  baslangic      3a 3b 1c 2d 2e
  tur 0          3a 1c 2d 2e 3b
  tur 1          1c 2d 2e 3a 3b
  tur 2          1c 2d 2e 3a 3b
```

Elle izlemenin tablosu bu: her satır bir dış turun sonu, ve değişmez her satırda görülebiliyor. Seçmede sol kısım (`1c`, `1c 2d`, ...) her zaman bitmiş; eklemede sol kısım sıralı ama sonradan araya eleman girebiliyor (`i=2`'de `1c` en başa geçti); kabarcıkta sağ kısım (`3b`, `3a 3b`) bitmiş. Kabarcık 3. turda hiç takas yapmadı ve durdu.

### Kararlılık

Bir sıralama, eşit anahtarlı elemanların **orijinal sırasını** koruyorsa **kararlı** (stable). Sonuçlara bak:

- **Seçme**: `3b 3a`. Orijinalde `a` önceydi; sıralama **bozdu**. Sebep `i=0`'daki uzun takas: `1c`'yi öne getirirken `3a`'yı `3b`'nin arkasına attı. Seçme sıralaması kararlı değil.
- **Ekleme**: `3a 3b`, `2d 2e`: korundu. Bir eleman sadece kendisinden **kesin büyük** elemanların üzerinden atlıyor (`kucuk(x, a[j-1])`, `<`); eşitin önüne geçmiyor.
- **Kabarcık**: korundu. Sadece komşular, sadece kesin sırasızsa takaslanıyor.

Kararlılık neden önemli? Birden çok anahtarla sıralarken: bir tabloyu önce **isme**, sonra kararlı bir sıralamayla **şehre** göre sıralarsan, her şehrin içinde isimler sıralı kalır. Elektronik tablolarda sütun başlığına art arda tıklamak bunu yapıyor. Ders 9.7'deki radix sıralama tamamen bu ilkeye dayanıyor. Ekleme sıralamasında koşulu `<=` yapmak, onu sessizce kararsız yapar.

---

## 3. Sayılar

2000 eleman, dört girdi türü: rastgele, zaten sıralı, ters sıralı ve "neredeyse sıralı" (sıralı diziye 20 rastgele takas):

```
n=2000  karsilastirma / dizi yazma
                         rastgele                 sirali                   ters              neredeyse
secme         1999000 /      3984    1999000 /         0    1999000 /      2000    1999000 /        40
ekleme         988385 /    988385       1999 /      1999    1999000 /   2000999      26053 /     26053
kabarcik      1997404 /   1972772       1999 /         0    1999000 /   3998000    1913509 /     48108
```

| | En iyi | Ortalama | En kötü | Yazma | Kararlı | Uyarlanır |
| --- | --- | --- | --- | --- | --- | --- |
| Seçme | $n^2/2$ | $n^2/2$ | $n^2/2$ | $O(n)$ | Hayır | Hayır |
| Ekleme | $n$ | $n^2/4$ | $n^2/2$ | ters çift kadar | Evet | Evet |
| Kabarcık | $n$ | $n^2/2$ | $n^2/2$ | 2 × ters çift | Evet | Kısmen |

- **Seçme** her girdide tam $n(n-1)/2 = 1\,999\,000$ karşılaştırma yapıyor, sıralı dizide bile. Ama yazma 4000'in altında.
- **Ekleme** girdiye **uyarlanıyor** (adaptive): sıralı dizide $n - 1$ karşılaştırma, neredeyse sıralıda 26 bin (rastgelenin 40'ta biri). Rastgele girdide 988 385 ≈ $n^2/4$. Ters sıralıda en kötü.
- **Kabarcık**, sıralı dizide erken bitiyor ama bir tek yanlış yerleşmiş küçük eleman yetiyor: neredeyse sıralı girdide 1.9 milyon karşılaştırma. Küçük bir eleman sondaysa her turda sadece bir adım sola gidebiliyor ("kaplumbağa" problemi). Yazma sayısı eklemenin tam iki katı: her ters çift için bir takas, yani iki yazma.

Ve süre (rastgele girdi, `-O2`):

```
sure (rastgele, -O2):
  n= 10000  secme 0.064 s  ekleme 0.015 s  kabarcik 0.092 s
  n= 20000  secme 0.204 s  ekleme 0.061 s  kabarcik 0.418 s
  n= 40000  secme 0.639 s  ekleme 0.240 s  kabarcik 1.790 s
```

Üçü de $n$ ikiye katlanınca 3–4 kat yavaşlıyor (Ders 9.1'in ikiye katlama deneyi): karesel. Ama aynı sınıfın içinde **7 kat** fark var. Ekleme sıralaması, seçmenin yarısı kadar karşılaştırma yapıyor ve iç döngüsü kısa; kabarcık hem en çok karşılaştırmayı hem en çok yazmayı yapıyor ve iç döngüsündeki "takasla mı?" dalı rastgele girdide yarı yarıya yanlış tahmin ediliyor (Ders 7.22). Seçmenin iç döngüsündeki "yeni en küçük mü?" dalı ise çoğunlukla "hayır" dediği için iyi tahmin ediliyor.

Ortadaki ders: **kabarcık sıralamasını kullanmak için neredeyse hiçbir sebep yok.** Basitliği ekleme sıralamasından fazla değil, ve her ölçüde daha kötü. Donald Knuth: "Kabarcık sıralamasının akılda kalıcı bir isim ve bazı ilginç teorik problemler dışında önerecek hiçbir şeyi yok."

---

## 4. Karesellikten çıkış: Shell sıralaması

Ekleme sıralamasının sorunu, bir elemanı her seferinde sadece **bir** konum kaydırması: uzağa gitmesi gereken bir eleman çok adım atıyor. Donald Shell'in fikri (1959): önce birbirinden $g$ uzaklıktaki elemanlar arasında ekleme sıralaması yap ($g$-sıralama), sonra daha küçük bir $g$ ile, ..., en son $g = 1$ ile (düz ekleme sıralaması). Büyük $g$'ler elemanları kaba yerlerine hızla taşıyor; son tur, neredeyse sıralı bir dizide çalıştığı için ucuz.

Karmaşıklık boşluk dizisine bağlı ve tam analizi bilinmiyor; Ciura'nın deneysel dizisi (1, 4, 10, 23, 57, 132, 301, 701, 1750, sonra 2.25 ile çarparak) pratikte en iyilerden. Aynı makinede 40 000 eleman 0.003 s (ekleme sıralamasının 0.240 s'sine karşı **85 kat**), 4 milyon eleman 0.48 s (Alıştırma 5). Ders 9.4–9.6'daki $O(n \log n)$ algoritmalarına yakın, ve kodu ekleme sıralamasından üç satır uzun.

---

## Alıştırmalar

**1** – Ekleme sıralamasının kaydırma sayısının, dizideki ters çift ($i < j$ ve $a[i] > a[j]$) sayısına **eşit** olduğunu göster. Rastgele bir permütasyonda beklenen ters çift sayısı neden $n(n-1)/4$?

**2** – Seçme sıralamasını kararlı yap: en küçüğü takasla öne getirmek yerine, aradaki elemanları birer sağa kaydırıp en küçüğü boşluğa koy. Kaç yazma yapar? Seçme sıralamasının hangi avantajı kayboldu?

**3** – **İkili ekleme sıralaması**: eklenecek yeri doğrusal yerine ikili aramayla (Ders 9.2) bul. Karşılaştırma sayısı ne olur? Yazma sayısı? Ne zaman gerçekten daha hızlıdır? Kararlı kalması için ikili arama hangi sınırı aramalı?

**4** – Kabarcık sıralamasında yazma sayısı neden tam olarak ekleme sıralamasının iki katı çıktı (rastgele girdide 1 972 772'ye karşı 988 385; ekleme sayısında son yerleştirmeler de var)?

**5** – Shell sıralamasını Ciura'nın boşluklarıyla yaz ve 40 000, 400 000 ve 4 000 000 rastgele `int`'te ölç. Büyüme $n^2$'ye mi $n \log n$'e mi yakın? Shell sıralaması kararlı mı?

<details>
<summary>Cevaplar</summary>

**1** – $i$. turda $x = a[i]$, solundaki sıralı kısımda kendisinden büyük her elemanın üzerinden bir kaydırmayla geçiyor. Solundaki ve kendisinden büyük elemanlar, $x$'in sağ ucu olduğu ters çiftlerin tam listesi (sıralı kısım orijinal $a[0..i)$'nin bir permütasyonu, yani aynı elemanlar). Her ters çift tam bir kez, büyük elemanın sağa kaydığı anda düzeltiliyor; başka bir kaydırma yok. Toplam = ters çift sayısı. Rastgele bir permütasyonda her $(i, j)$ çifti $1/2$ olasılıkla ters (simetri: çiftteki iki değerin hangisinin önde olduğu eşit olası); beklenen sayı $\binom{n}{2} \cdot \frac12 = n(n-1)/4$, olasılığın doğrusallığıyla (Ders 6.29). $n = 2000$ için 999 500; ölçülen kaydırma sayısı 986 386 (yazma sayısı 988 385'ten son yerleştirmelerin $n - 1$ yazması çıkınca).

**2** – `m` bulunduktan sonra `x = a[m]; for (j = m; j > i; j--) a[j] = a[j-1]; a[i] = x;`. Kaydırma eşit elemanların göreli sırasını değiştirmiyor (hepsi bir sağa kayıyor), ve en küçüklerin ilki seçiliyor (`<`): kararlı. Yazma sayısı her turda $m - i + 1$; toplam $O(n^2)$, rastgele girdide ortalama $n^2/4$ civarı. Seçme sıralamasının tek gerçek avantajı (en fazla $n$ takas, $O(n)$ yazma) kayboldu; karşılaştırması da hâlâ her girdide $n^2/2$. Bu sürüm, ekleme sıralamasından her açıdan kötü.

**3** – Her eleman için $\lceil \log_2 (i + 1) \rceil$ karşılaştırma, toplam $O(n \log n)$. Ama boşluk açmak için yine aradaki bütün elemanlar kaydırılıyor: yazma hâlâ $O(n^2)$ (ters çift sayısı). Karşılaştırma pahalı, yazma ucuzsa (uzun string anahtarlar, `memmove` ile toplu kaydırma; Ders 4.18) daha hızlı. Kararlılık için `ust_sinir` (Ders 9.2, Alıştırma 1) kullanılmalı: eşitlerin **sonuna** eklemek. `alt_sinir`, yeni elemanı eşitlerin önüne koyar ve kararlılığı bozar.

**4** – Kabarcık her ters çifti bir komşu takasıyla düzeltiyor ve her takas tam olarak bir ters çifti ortadan kaldırıyor (komşu iki elemanı değiştirmek sadece onların arasındaki çifti etkiler). Takas sayısı = ters çift sayısı, ve her takas 2 yazma. Ekleme sıralaması aynı ters çiftleri bir kaydırmayla (1 yazma) düzeltiyor, artı her tur sonunda bir yerleştirme yazması ($n - 1$ tane). Rastgele girdide: ters çift $T$, ekleme $T + (n-1)$ yazma (988 385 → $T$ = 986 386), kabarcık $2T$ = 1 972 772. Tam olarak öyle.

**5** – Shell sıralaması (`for` her boşluk `g`: `for (i = g; i < n; i++) { x = a[i]; j = i; while (j >= g && a[j-g] > x) { a[j] = a[j-g]; j -= g; } a[j] = x; }`):

```
shell n=40000 0.0028 s
shell n=400000 0.0377 s
shell n=4000000 0.4773 s
```

$n$ 10 katına çıkınca 13 kat: $n^2$ olsaydı 100 kat olurdu. Bu aralıkta $n \log n$'in (10 kattan biraz fazla) ya da $n^{1.1}$'in davranışına yakın. Shell sıralaması **kararlı değil**: $g$-sıralama, aralarında $g$ mesafe olmayan eşit elemanları birbirinin üzerinden atlatabiliyor.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 5.2.1 (ekleme ve Shell), 5.2.2 (kabarcık), 5.2.3 (seçme); ters çiftler 5.1.1.
- Robert Sedgewick ve Kevin Wayne, *Algorithms* (4. baskı), Bölüm 2.1: basit sıralamalar ve Shell sıralaması.
- Marcin Ciura, "Best Increments for the Average Case of Shellsort", *FCT* 2001.
- Owen Astrachan, "Bubble Sort: An Archaeological Algorithmic Analysis", *SIGCSE* 2003.

**Sıradaki ders:** Birleştirmeli sıralama. Böl-yönet, Master teoremi ile analiz ve aşağıdan yukarı sürüm.
