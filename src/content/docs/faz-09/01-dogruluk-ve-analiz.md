---
title: "9.1 Doğruluk ve analiz"
description: "Bir algoritmanın doğru olduğunu döngü değişmeziyle ispatlamak: başlangıç, koruma, sonlanma; hızlı üs almanın değişmezini assert ile çalışırken denetlemek; en iyi, ortalama ve en kötü durum ve doğrusal aramada 1, (n+1)/2 ve n karşılaştırma; ikiye katlama deneyiyle büyüme üstelini ölçmek: toplama 1.0, karesel çift sayma 2.0, qsort'un n log n'inin neden 1.0 gibi görünmesi; ölçüm tuzakları: derleyicinin işi silmesi, ısınma, tekrar ve en iyi süre."
---

Faz 8 veri yapılarını kurdu: verinin bellekte **nasıl durduğunu**. Faz 9 o veri üzerinde çalışan **algoritmalar**: sıralama, arama, graf gezinmeleri, dinamik programlama. Her algoritma için iki soru soracağız. **Doğru mu?** Her girdi için istenen çıktıyı veriyor ve bitiyor mu? **Ne kadar hızlı?** Girdi büyüdükçe süresi nasıl büyüyor?

Faz 6 bu soruların matematiğini hazırladı: tümevarım (Ders 6.4) ve döngü değişmezi, asimptotik notasyon (Ders 6.12), özyinelemeli bağıntılar ve Master teoremi (Ders 6.11, 6.13). Bu ders onları bir araya getirip bütün faz boyunca kullanacağımız yöntemi kuruyor: ispat, analiz ve **ölçüm**. Üçü birbirini tamamlıyor. İspat test etmediğimiz girdiler için de güvence veriyor; analiz büyük $n$'de ne olacağını söylüyor; ölçüm ise ispatın ve analizin kaçırdığı şeyleri (sabitler, cache, derleyici) gösteriyor.

---

## 1. Döngü değişmezi

Ders 6.4'te gördük: bir döngünün doğruluğunu ispatlamanın standart yolu bir **değişmez** (invariant) bulmak, yani döngünün her turunun başında doğru olan bir önerme. İspat üç adımlı:

1. **Başlangıç**: döngüye girmeden önce değişmez doğru.
2. **Koruma**: bir turun başında doğruysa, turun sonunda (bir sonraki turun başında) da doğru.
3. **Sonlanma**: döngü bitince, değişmez ile çıkış koşulu birlikte istenen sonucu veriyor. Ayrıca döngünün **bittiğini** de göstermek gerekiyor: her turda azalan ve sonsuza kadar azalamayacak bir nicelik.

Örnek: $a^n$'yi $O(\log n)$ çarpmayla hesaplayan **hızlı üs alma** (Ders 5.13'teki çarpma algoritmasının üs hali, Ders 6.20'deki modüler üs almanın temeli).

```c
/* Hizli us alma: dongu degismezini assert ile kontrol etmek */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>

/* Gercek a^n'yi ayri, yavas ama apacik dogru bir yolla hesapla (sadece kontrol icin) */
static uint64_t yavas_us(uint64_t a, unsigned n) { uint64_t s = 1; while (n--) s *= a; return s; }

static uint64_t us(uint64_t a, unsigned n) {
    uint64_t sonuc = 1, taban = a;
    unsigned k = n;
    /* DEGISMEZ: sonuc * taban^k == a^n  (mod 2^64) */
    while (k > 0) {
        assert(sonuc * yavas_us(taban, k) == yavas_us(a, n));
        if (k & 1) sonuc *= taban;          /* k tek: bir carpani sonuca al */
        taban *= taban;                      /* taban^k = (taban^2)^(k/2) */
        k >>= 1;
    }
    assert(sonuc == yavas_us(a, n));        /* k == 0: degismez -> sonuc == a^n */
    return sonuc;
}
```

Değişmez: $\text{sonuc} \cdot \text{taban}^k = a^n$.

- **Başlangıç**: $\text{sonuc} = 1$, $\text{taban} = a$, $k = n$: $1 \cdot a^n = a^n$. ✓
- **Koruma**: $k$ çiftse, $\text{taban}^k = (\text{taban}^2)^{k/2}$; taban karesine, $k$ yarısına gidiyor, çarpım aynı. $k$ tekse, $\text{taban}^k = \text{taban} \cdot (\text{taban}^2)^{(k-1)/2}$; fazladan $\text{taban}$ sonuca katılıyor, gerisi çift durum gibi. `k >>= 1`, tek $k$ için $(k-1)/2$. ✓
- **Sonlanma**: döngü $k = 0$'da bitiyor; değişmez $\text{sonuc} \cdot \text{taban}^0 = \text{sonuc} = a^n$ diyor. ✓ Döngü biter, çünkü $k$ her turda en az yarıya iniyor ve negatif olamaz: $\lfloor \log_2 n \rfloor + 1$ tur.

İspat **bütün** $a$ ve $n$ değerleri için geçerli; test sadece denediklerimiz için. Ama ispat da hata yapabilir: değişmezi yanlış yazmak, bir durumu atlamak. Bu yüzden değişmezi bir `assert` olarak **koda** da yazmak iyi bir alışkanlık. Hata ayıklama derlemesinde her turda kontrol ediliyor, `-DNDEBUG` ile derlenince tamamen kayboluyor. Burada kontrol için ayrı, yavaş ama apaçık doğru bir `yavas_us` kullandık: değişmezi kontrol eden kod, kontrol ettiği koddan **bağımsız** olmalı.

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined us.c -o us && ./us
3^13 = 1594323
2^40 = 1099511627776
7^0  = 1
n = 1000000 icin dongu 20 tur doner
```

(Bütün aritmetik modülo $2^{64}$, `uint64_t`'nin işaretsiz taşma kuralıyla; Ders 3.8. Değişmez de modülo $2^{64}$ geçerli, çünkü modüler çarpma birleşmeli ve değişmeli.)

Değişmez bulmak bir sanat ama bir ipucu var: değişmez genelde **istenen sonucun genelleştirilmiş hali**. "sonuc = $a^n$" döngü bitince doğru olacak; döngünün ortasında "sonuc, $a^n$'nin şu ana kadar hesaplanmış kısmı, geri kalanı taban$^k$" diyoruz. Bu fazdaki her algoritmanın doğruluğunu böyle bir cümleyle ifade edeceğiz: ekleme sıralamasında "ilk $i$ eleman sıralı" (Ders 9.3), ikili aramada "aranan varsa $[lo, hi)$ aralığında" (Ders 9.2), Dijkstra'da "işlenmiş düğümlerin uzaklıkları kesin" (Ders 9.17).

---

## 2. En iyi, ortalama, en kötü

Bir algoritmanın süresi sadece girdinin **boyutuna** değil, girdinin **kendisine** de bağlı. Doğrusal arama:

```c
/* Dogrusal aramada en iyi, ortalama ve en kotu durum: karsilastirma sayilari */
#include <stdio.h>
#include <stdlib.h>
static long karsilastirma;
static long ara(const int *a, long n, int x) {
    for (long i = 0; i < n; i++) { karsilastirma++; if (a[i] == x) return i; }
    return -1;
}
int main(void) {
    long n = 1000; int *a = malloc(n * sizeof *a);
    for (long i = 0; i < n; i++) a[i] = (int)(i * 7 + 3);
    karsilastirma = 0; ara(a, n, a[0]);            printf("en iyi (ilk eleman): %ld\n", karsilastirma);
    karsilastirma = 0; ara(a, n, -1);              printf("en kotu (yok)      : %ld\n", karsilastirma);
    srand(1); long top = 0, T = 100000;
    for (long t = 0; t < T; t++) { karsilastirma = 0; ara(a, n, a[rand() % n]); top += karsilastirma; }
    printf("ortalama (var, rastgele yer): %.1f   (n+1)/2 = %.1f\n", (double)top / T, (n + 1) / 2.0);
    free(a);
}
```

```
$ cc -std=c11 -O2 -Wall dogrusal.c -o dogrusal && ./dogrusal
en iyi (ilk eleman): 1
en kotu (yok)      : 1000
ortalama (var, rastgele yer): 498.6   (n+1)/2 = 500.5
```

- **En kötü durum**: bütün $n$ boyutlu girdiler arasında en uzun süre. Aranan yoksa $n$ karşılaştırma. Bir **garanti**: algoritma hiçbir zaman bundan yavaş değil.
- **En iyi durum**: en kısa süre; aranan baştaysa 1. Nadiren işe yarar bilgi; neredeyse her algoritma bir girdide şanslıdır.
- **Ortalama durum**: girdiler üzerinde bir **olasılık dağılımı** varsayıp beklenen süre (Ders 6.29). Aranan var ve her konumda eşit olasılıklıysa beklenen karşılaştırma $\sum_{i=1}^{n} i \cdot \frac{1}{n} = \frac{n+1}{2}$. Ölçüm (100 000 rastgele arama) 498.6.

Ortalama durumun zayıf noktası varsayımı: "her konum eşit olasılıklı" gerçek veri için doğru olmayabilir. Ders 8.8'deki BST'nin ortalama derinliği $2 \ln n$'di ama gerçek veri sıralı gelince en kötü duruma düştü. Bu yüzden iki tür "ortalama"yı ayırmak gerekiyor:

- **Girdi üzerinde ortalama**: girdinin rastgele olduğunu varsayar. Varsayım yanlışsa analiz değersiz, ve bir saldırgan kötü girdiyi seçebilir (Ders 8.13'teki hash taşkını).
- **Algoritmanın kendi rastgeleliği üzerinde beklenti**: algoritma yazı-tura atıyor (Ders 8.20'deki skip list, Ders 9.5'teki rastgele pivotlu hızlı sıralama). Girdi ne olursa olsun geçerli; kötü girdi yok, sadece kötü şans.

Bir de **amortize** analiz var (Ders 4.24, 8.14): bir işlem dizisinin toplam maliyetinin işlem sayısına bölümü. Tek tek işlemlerden biri pahalı olabilir ama dizi boyunca ortalama ucuz, ve bu bir olasılık değil, **garanti**.

---

## 3. Ölçmek: ikiye katlama deneyi

Asimptotik analiz $T(n) = \Theta(n^2)$ diyor. Gerçek program böyle mi davranıyor? Basit bir deney: $n$'yi her seferinde **ikiye katla** ve sürelerin **oranına** bak. $T(n) \approx c \cdot n^b$ ise

$$
\frac{T(2n)}{T(n)} \approx \frac{c (2n)^b}{c n^b} = 2^b, \qquad b \approx \log_2 \frac{T(2n)}{T(n)}.
$$

Sabit $c$ (makinenin hızı, derleyici, dil) oranda **sadeleşiyor**. Bu, Sedgewick'in "doubling test"i: bir programın büyüme üstelini, kodunu okumadan ölçmenin yolu.

```c
/* Ikiye katlama deneyi: n'yi ikiye katla, surenin oranindan usteli tahmin et (T ~ c n^b => b ~ log2 oran) */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

static long toplam(const int *a, long n) { long s = 0; for (long i = 0; i < n; i++) s += a[i]; return s; }
static int kars(const void *x, const void *y) { int p = *(const int *)x, q = *(const int *)y; return (p > q) - (p < q); }
static long sirala(int *a, long n) { qsort(a, n, sizeof *a, kars); return a[n / 2]; }
static long cift_say(const int *a, long n) {              /* toplami 0 olan cift sayisi, saf O(n^2) */
    long c = 0;
    for (long i = 0; i < n; i++) for (long j = i + 1; j < n; j++) c += (a[i] + a[j] == 0);
    return c;
}

typedef long (*Fn)(int *, long);
static long t_toplam(int *a, long n) { return toplam(a, n); }
static long t_cift(int *a, long n) { return cift_say(a, n); }

static void deney(const char *ad, Fn f, long n0, int adim, int tekrar) {
    printf("%s\n", ad);
    double onceki = 0;
    for (long n = n0, k = 0; k < adim; k++, n *= 2) {
        int *a = malloc(n * sizeof *a);
        double en_iyi = 1e9; volatile long sonuc = 0;
        for (int r = 0; r < tekrar; r++) {
            srand(7); for (long i = 0; i < n; i++) a[i] = rand() % 2000001 - 1000000;
            double t0 = simdi(); sonuc += f(a, n); double t = simdi() - t0;
            if (t < en_iyi) en_iyi = t;                    /* en iyi tekrar: gurultuyu azaltir */
        }
        if (onceki > 0) printf("  n=%9ld  %9.4f s  oran %5.2f  b ~ %4.2f\n", n, en_iyi, en_iyi / onceki, log2(en_iyi / onceki));
        else            printf("  n=%9ld  %9.4f s\n", n, en_iyi);
        onceki = en_iyi;
        free(a);
    }
}

int main(void) {
    deney("toplam (dogrusal)", t_toplam, 4000000, 5, 5);
    deney("qsort (n log n)", sirala, 1000000, 5, 3);
    deney("cift sayma (karesel)", t_cift, 4000, 5, 3);
}
```

```
$ cc -std=c11 -O2 -Wall ikiye.c -o ikiye -lm && ./ikiye
toplam (dogrusal)
  n=  4000000     0.0003 s
  n=  8000000     0.0006 s  oran  2.03  b ~ 1.02
  n= 16000000     0.0011 s  oran  1.90  b ~ 0.93
  n= 32000000     0.0023 s  oran  2.01  b ~ 1.01
  n= 64000000     0.0043 s  oran  1.88  b ~ 0.91
qsort (n log n)
  n=  1000000     0.0817 s
  n=  2000000     0.1714 s  oran  2.10  b ~ 1.07
  n=  4000000     0.3461 s  oran  2.02  b ~ 1.01
  n=  8000000     0.6859 s  oran  1.98  b ~ 0.99
  n= 16000000     1.3580 s  oran  1.98  b ~ 0.99
cift sayma (karesel)
  n=     4000     0.0013 s
  n=     8000     0.0051 s  oran  3.94  b ~ 1.98
  n=    16000     0.0201 s  oran  3.98  b ~ 1.99
  n=    32000     0.0801 s  oran  3.98  b ~ 1.99
  n=    64000     0.3203 s  oran  4.00  b ~ 2.00
```

- **Toplam**: oran 2, $b \approx 1$. Doğrusal.
- **Çift sayma**: oran 4, $b = 2.00$. İkinci ondalığa kadar karesel. (64 000 elemanda 2 milyar çift 0.32 s'de: eleman çifti başına 0.16 ns. Derleyici iç döngüyü SIMD komutlarıyla vektörleştirmiş; Faz 11. Karmaşıklık değişmiyor, sabit küçülüyor.)
- **qsort**: oran yaklaşık 2, $b \approx 1$. Ama qsort $\Theta(n \log n)$; $n^1$ değil! İkiye katlama $\log n$ çarpanını neredeyse **göremiyor**: $\frac{2n \log(2n)}{n \log n} = 2 \cdot \frac{\log n + 1}{\log n}$, ve $n = 10^6$'da bu $2 \cdot 21/20 = 2.1$; $n$ büyüdükçe 2'ye yaklaşıyor. Ölçülen 2.10, 2.02, 1.98, 1.98: ilk oran tahminle aynı, sonrakiler gürültü içinde. Doğrusal ile $n \log n$'i ayırmak için çok daha geniş bir $n$ aralığı ya da $T(n)/(n \log n)$'in sabit kaldığını göstermek gerekiyor (Alıştırma 5).

### Ölçme tuzakları

Bu fazdaki her ölçümde dikkat ettiğimiz şeyler:

- **Derleyici işi silebilir.** Sonucu hiç kullanılmayan bir hesap `-O2`'de tamamen kaldırılabilir (Ders 7.15). Yukarıda sonuçlar bir `volatile` değişkene toplanıyor. Ders 8.6'da clang bir özyinelemeli toplamı kapalı formüle çevirmişti; Ders 8.16'da döngüde değişmeyen bir arama döngünün dışına çıkarılmış ve ilk ölçüm 0.0 ns çıkmıştı.
- **Çok kısa süreler ölçülemez.** Saatin çözünürlüğü ve `clock_gettime`'ın kendi maliyeti var; yukarıdaki toplamın ilk satırı (0.3 ms) gürültüye yakın. Ölçülen iş en az birkaç milisaniye sürmeli, gerekirse tekrar edilmeli.
- **İlk çalıştırma farklı.** Belleğe ilk dokunuş sayfa hatası (Ders 7.27), cache boş, dal tahmincisi eğitilmemiş. Birkaç tekrar yapıp **en iyisini** (ya da ortancayı) almak, ortalamadan daha kararlı: ortalama bir kez araya giren bir işletim sistemi kesintisinden etkilenir.
- **Girdi önemli.** Aynı tohumla üretilen aynı girdi, karşılaştırmaları adil yapıyor. Sıralama algoritmalarını sıralı, ters sıralı, çok tekrarlı ve rastgele girdilerde ayrı ayrı ölçeceğiz (Ders 9.3–9.5).
- **Ölçüm makineye ait.** Bu fazdaki süreler bir Apple M2'de ölçüldü. Oranlar ve üstel başka makinelerde de geçerli; mutlak süreler değil.

---

## Alıştırmalar

**1** – Öklid algoritması (Ders 2.9, 6.17): `while (b != 0) { t = a % b; a = b; b = t; } return a;`. Bir döngü değişmezi yaz ve üç adımlı ispatı yap. Döngünün bittiğini hangi nicelik garanti ediyor?

**2** – Bir diziyi yerinde ters çeviren döngü: `for (i = 0, j = n - 1; i < j; i++, j--) takas(a[i], a[j]);`. Değişmezi orijinal dizi $b$ cinsinden yaz. Döngü bitince neden dizi tamamen ters çevrilmiş oluyor; $n$ tek ise ortadaki eleman ne oluyor?

**3** – Şu fonksiyon dizinin en büyük elemanını bulmak için yazılmış. Değişmezi kurmaya çalışarak hatayı bul:

```c
int en_buyuk(const int *a, int n) {   /* n >= 1 */
    int m = 0;
    for (int i = 0; i < n; i++) if (a[i] > m) m = a[i];
    return m;
}
```

**4** – Doğrusal aramada aranan eleman $q$ olasılıkla dizide **yok**, $1 - q$ olasılıkla var ve her konumda eşit olasılıklı. Beklenen karşılaştırma sayısı nedir? $q = 0$, $q = 1$ ve $q = 1/2$ için kontrol et.

**5** – İkiye katlama deneyinde qsort'un oranı 2'ye çok yakındı. $T(n) = c \cdot n \log_2 n$ ise $n = 10^6, 10^7, 10^9$ için $T(2n)/T(n)$'i hesapla. $n \log n$'i doğrusal büyümeden deneysel olarak ayırt etmek için hangi büyüklüğü tabloya eklerdin?

<details>
<summary>Cevaplar</summary>

**1** – Değişmez: $\gcd(a, b) = \gcd(a_0, b_0)$ ($a_0, b_0$ başlangıç değerleri). Başlangıç: $a = a_0$, $b = b_0$, apaçık. Koruma: Ders 6.17'deki temel özdeşlik $\gcd(a, b) = \gcd(b, a \bmod b)$; yeni $(a, b)$ çifti eskisinin $(b, a \bmod b)$'si. Sonlanma: döngü $b = 0$'da bitiyor, $\gcd(a, 0) = a$, yani dönen $a$ = $\gcd(a_0, b_0)$. Bitiş garantisi: $b \ge 0$ ve her turda kesin azalıyor ($a \bmod b < b$); negatif olmayan bir tamsayı sonsuza kadar azalamaz. Daha güçlü bir sınır: iki turda bir $b$ en az yarıya iniyor, yani $O(\log \min(a, b))$ tur (Lamé teoremi, Fibonacci sayıları en kötü durum; Ders 6.17).

**2** – Değişmez: her turun başında $a[0..i)$ = $b$'nin son $i$ elemanının tersi ($a[k] = b[n-1-k]$, $k < i$), $a(j..n-1]$ = $b$'nin ilk $n-1-j$ elemanının tersi, ve $a[i..j]$ hâlâ $b[i..j]$ (dokunulmamış), ayrıca $i + j = n - 1$. Takas, $a[i]$ ve $a[j]$'yi doğru yerlerine koyup iki ucu birer içeri alıyor. Döngü $i \ge j$ olunca bitiyor: $n$ çiftse $i = j + 1$ ve dokunulmamış bölge boş; $n$ tekse $i = j$ ve dokunulmamış bölge tek eleman, ortadaki eleman: $b[(n-1)/2]$, ve tersi kendisi. Her iki durumda dizi tamamen ters.

**3** – Değişmez "$m$, $a[0..i)$'nin en büyüğü" olmalı. Başlangıçta $i = 0$ ve $a[0..0)$ boş; boş kümenin en büyüğü tanımsız, ama `m = 0` sanki 0 bir elemanmış gibi davranıyor. Bütün elemanlar negatifse fonksiyon 0 döndürüyor, ki dizide yok. Doğrusu `int m = a[0];` ve döngüyü `i = 1`'den başlatmak: başlangıçta değişmez "$m$, $a[0..1)$'in en büyüğü" ve gerçekten doğru. Değişmezi başlangıçta doğrulamaya çalışmak hatayı hemen gösteriyor; test etmek ise sadece negatif sayılarla denersen gösteriyor.

**4** – $E = q \cdot n + (1 - q) \cdot \frac{n+1}{2}$. $q = 0$: $\frac{n+1}{2}$ (Bölüm 2'deki ölçüm). $q = 1$: $n$ (en kötü durum). $q = 1/2$: $\frac{n}{2} + \frac{n+1}{4} = \frac{3n + 1}{4}$. Her durumda $\Theta(n)$; olasılık sadece sabiti değiştiriyor.

**5** – $\frac{T(2n)}{T(n)} = 2 \cdot \frac{\log_2 n + 1}{\log_2 n}$. $n = 10^6$: $\log_2 n \approx 19.93$, oran $2.100$. $n = 10^7$: $23.25$, oran $2.086$. $n = 10^9$: $29.9$, oran $2.067$. Ölçüm gürültüsü yüzde birkaç iken bu farklar (2'den %3–5) neredeyse görünmez. Daha iyisi, $T(n) / (n \log_2 n)$ sütununu eklemek: $n \log n$ büyümede bu sabit kalır, doğrusal büyümede yavaşça azalır. Ya da çok geniş bir aralıkta ($n = 10^3$'ten $10^8$'e) $T(n)/n$'e bakmak: doğrusal büyümede sabit, $n \log n$'de $\log n$ gibi artar (aralıkta yaklaşık 2.7 kat). Ama dikkat: büyük $n$'de veri cache'ten taşınca (Ders 7.24) sabit de değişir ve bu etki $\log n$ çarpanından büyük olabilir.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 2.1–2.2: döngü değişmezleri, en kötü ve ortalama durum.
- Robert Sedgewick ve Kevin Wayne, *Algorithms* (4. baskı), Bölüm 1.4: algoritma analizi ve ikiye katlama deneyi.
- David Gries, *The Science of Programming*, Springer, 1981: değişmezlerle program türetme.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 1.2.1: matematiksel tümevarım ve algoritma doğruluğu.
- Jon Bentley, *Programming Pearls* (2. baskı), Bölüm 4: doğru program yazmak ve ikili arama.

**Sıradaki ders:** Arama. Doğrusal ve ikili arama, ikili aramanın `(lo + hi) / 2` taşma hatası.
