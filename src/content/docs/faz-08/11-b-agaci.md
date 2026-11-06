---
title: "8.11 B-ağacı"
description: "Düğüm başına çok anahtarlı, bütün yaprakları aynı derinlikte, mükemmel dengeli arama ağacı; minimum derece T, düğüm bölme ve ortanca anahtarın yukarı çıkması, ağacın yukarıdan büyümesi; inerken önceden bölen tek geçişli ekleme ve T = 2'de çıkan ağacın Ders 8.10'daki 2-3-4 görünümüyle aynı olması; Apple M2'de 1 milyon anahtarda düğüm boyutu değişince arama süresi (T = 2'de 313 ns, T = 32'de 73 ns, kırmızı-siyah 136 ns, sıralı dizi 43 ns); düğüm içinde doğrusal mı ikili arama mı; diskte sayfa boyutlu düğümler, veritabanları ve dosya sistemleri, B+ ağacı."
---

Ders 8.8–8.10'daki ağaçların hepsi ikili: her düğümde bir anahtar, iki çocuk. Bir milyon anahtarda kökten yaprağa yaklaşık 20 adım, her adım bir pointer takibi. Ders 7.24'ün ölçümüne göre, düğüm cache'te değilse her takip 100 ns civarı. Veri diskteyse durum çok daha kötü: bir SSD okuması 10–100 µs, dönen bir diskte 5–10 ms. 20 disk okumasıyla tek bir arama 100 ms sürer.

**B-ağacı** (Rudolf Bayer ve Edward McCreight, 1970) bunu düğümü **büyüterek** çözüyor. Bir düğüm, tek bir okumayla gelen bir bloğun (bir disk sayfası ya da birkaç cache satırı) tamamını dolduruyor ve onlarca, yüzlerce anahtar tutuyor. Ağaç o kadar sığlaşıyor ki 1 milyon anahtar 3–4 seviyeye, 1 milyar anahtar 5 seviyeye sığıyor. Bugün neredeyse bütün veritabanları (SQLite, PostgreSQL, MySQL/InnoDB) ve dosya sistemleri (APFS, NTFS, btrfs, ext4'ün dizin indeksleri) bir B-ağacı türü kullanıyor.

---

## 1. Tanım

**Minimum derecesi** $T \ge 2$ olan bir B-ağacında:

1. Her düğümde en fazla $2T - 1$ anahtar var. Kök dışındaki her düğümde en az $T - 1$ anahtar var.
2. Bir düğümdeki anahtarlar sıralı: $k_0 < k_1 < \dots < k_{n-1}$.
3. $n$ anahtarlı bir iç düğümün $n + 1$ çocuğu var. `cocuk[i]`'deki bütün anahtarlar $k_{i-1}$ ile $k_i$ arasında (Ders 8.8'deki BST değişmezinin çok yollu hali).
4. **Bütün yapraklar aynı derinlikte.**

```
                        [ 30   60 ]
                  /         |          \
       [10 20]         [40 45 50]        [70 80]
       <30 olanlar     30 ile 60 arası   >60 olanlar
```

Kural 4 mükemmel denge; kural 1'deki alt sınır her düğümün en az yarı dolu olmasını sağlıyor. $T = 2$ için düğümlerde 1–3 anahtar, 2–4 çocuk var: Ders 8.10'daki **2-3-4 ağacı**. Kırmızı-siyah ağaç, aslında $T = 2$ bir B-ağacının ikili kodlamasıydı.

### Yükseklik

Yüksekliği $h$ (kökten yaprağa kenar sayısı) olan bir B-ağacında en az kaç anahtar var? Kökte en az 1 anahtar ve 2 çocuk; ondan sonra her düğümün en az $T$ çocuğu var. Derinlik $d \ge 1$'de en az $2T^{d-1}$ düğüm, her birinde en az $T - 1$ anahtar:

$$
n \;\ge\; 1 + (T - 1)\sum_{d=1}^{h} 2T^{d-1} \;=\; 1 + 2(T-1)\cdot\frac{T^h - 1}{T - 1} \;=\; 2T^h - 1,
$$

yani

$$
h \le \log_T \frac{n+1}{2}.
$$

(Geometrik toplam, Ders 6.10.) $T = 32$ ve $n = 10^6$ için $\log_{32} 500\,000 \approx 3.79$: yükseklik en fazla 3. İkili bir ağaçta bunun karşılığı 20.

---

## 2. Düğüm ve arama

```c
/* B-agaci (CLRS 18): minimum derece T. Her dugumde T-1..2T-1 anahtar (kok haric), 2T'ye kadar cocuk. */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#ifndef T
#define T 2                          /* T = 2: 2-3-4 agaci (Ders 8.10) */
#endif
#define MAKS (2 * T - 1)

typedef struct BDugum {
    int n;                           /* anahtar sayisi */
    bool yaprak;
    int anahtar[MAKS];
    struct BDugum *cocuk[MAKS + 1];  /* cocuk[i]: anahtar[i]'den kucukler; cocuk[n]: en buyuklerden sonrasi */
} BDugum;

static BDugum *yeni_dugum(bool yaprak) {
    BDugum *d = calloc(1, sizeof *d);
    d->yaprak = yaprak;
    return d;
}
```

$T$ derleme zamanında bir makro, böylece aynı kodu farklı düğüm boyutlarıyla derleyip ölçebileceğiz (`-DT=32`). Anahtarlar ve çocuk pointer'ları düğümün **içinde**, sabit boyutlu dizilerde. Bir düğüm tek bir bellek bloğu ve onu okumak art arda gelen cache satırlarını okumak demek; işlemcinin önden getiricisi (prefetcher) bunu çok iyi yapıyor (Ders 7.24).

Arama, Ders 8.8'deki BST araması; tek fark, her düğümde "sola mı sağa mı" yerine "$n + 1$ çocuktan hangisine" sorusu. Cevabı düğümün sıralı anahtar dizisinde bir ikili arama veriyor (Ders 4.2):

```c
/* Dugumde x'ten kucuk olmayan ilk anahtarin yeri (ikili arama) */
static int yer_bul(const BDugum *d, int x) {
    int lo = 0, hi = d->n;
    while (lo < hi) {
        int orta = (lo + hi) / 2;
        if (d->anahtar[orta] < x) lo = orta + 1; else hi = orta;
    }
    return lo;
}

long ziyaret;                        /* arama basina kac dugume girildi (disk okumasi) */

bool b_ara(const BDugum *d, int x) {
    while (d) {
        ziyaret++;
        int i = yer_bul(d, x);
        if (i < d->n && d->anahtar[i] == x) return true;
        d = d->yaprak ? NULL : d->cocuk[i];
    }
    return false;
}
```

`yer_bul`, `x`'ten küçük olmayan ilk anahtarın konumunu veriyor. O anahtar `x` ise bulduk; değilse `x` varsa `cocuk[i]`'dedir, çünkü `anahtar[i-1] < x < anahtar[i]`.

---

## 3. Ekleme ve bölme

AVL ve kırmızı-siyah ağaçlar yeni anahtarı bir yaprak olarak ekleyip sonra dönmelerle dengeyi düzeltiyordu. B-ağacı **asla dönmüyor**. Yeni anahtar her zaman mevcut bir yaprak düğüme giriyor. Yaprak doluysa (zaten $2T - 1$ anahtar varsa) **bölünüyor**:

```
 T = 3, dolu düğüm (5 anahtar), ebeveynde yer var:

      [ 20       60 ]                     [ 20   40   60 ]
          |                    ──►             /    \
   [30 35 40 45 50]                   [30 35]      [45 50]
```

Ortanca anahtar (40) ebeveyne çıkıyor, solundakiler bir düğümde kalıyor, sağındakiler yeni bir düğüme taşınıyor. İki yarının her birinde $T - 1$ anahtar var, yani ikisi de kural 1'i sağlıyor.

Ebeveyn de doluysa ne olur? Ortanca anahtar oraya sığmaz. Bölünme yukarı yayılabilir (Ders 8.10'daki durum 1'in köke kadar tekrarlanması). Bunu yönetmenin iki yolu var: aşağı inip sonra gerekirse yukarı doğru bölmek (ebeveyn pointer'ları ya da bir yol yığını gerekir), ya da **inerken** yoldaki her dolu düğümü **önceden** bölmek. İkinci yolda, bir düğüme indiğimizde ebeveyninde her zaman yer olduğu garanti; bölünme hiçbir zaman yukarı yayılmıyor ve ekleme tek bir geçişte bitiyor. CLRS'nin yöntemi bu:

```c
/* ebeveyn->cocuk[i] dolu (2T-1 anahtar). Ortanca anahtar ebeveyne cikar, sag yari yeni dugum olur. */
static void bol(BDugum *ebeveyn, int i) {
    BDugum *sol = ebeveyn->cocuk[i];
    BDugum *sag = yeni_dugum(sol->yaprak);
    sag->n = T - 1;
    for (int j = 0; j < T - 1; j++) sag->anahtar[j] = sol->anahtar[j + T];
    if (!sol->yaprak)
        for (int j = 0; j < T; j++) sag->cocuk[j] = sol->cocuk[j + T];
    sol->n = T - 1;
    for (int j = ebeveyn->n; j > i; j--) ebeveyn->cocuk[j + 1] = ebeveyn->cocuk[j];   /* ebeveynde yer ac */
    ebeveyn->cocuk[i + 1] = sag;
    for (int j = ebeveyn->n - 1; j >= i; j--) ebeveyn->anahtar[j + 1] = ebeveyn->anahtar[j];
    ebeveyn->anahtar[i] = sol->anahtar[T - 1];                                        /* ortanca yukari */
    ebeveyn->n++;
}

/* Inerken dolu dugumleri onceden bol: boylece yapraga varildiginda yer garanti. */
bool b_ekle(BDugum **kok, int x) {
    if (b_ara(*kok, x)) return false;
    BDugum *r = *kok;
    if (r->n == MAKS) {                              /* kok doluysa: yeni kok, agac YUKARIDAN buyur */
        BDugum *s = yeni_dugum(false);
        s->cocuk[0] = r;
        bol(s, 0);
        *kok = r = s;
    }
    while (!r->yaprak) {
        int i = yer_bul(r, x);
        if (r->cocuk[i]->n == MAKS) {
            bol(r, i);
            if (x > r->anahtar[i]) i++;              /* ortanca yukari cikti; x hangi yarida? */
        }
        r = r->cocuk[i];
    }
    int i = r->n;
    while (i > 0 && r->anahtar[i - 1] > x) { r->anahtar[i] = r->anahtar[i - 1]; i--; }
    r->anahtar[i] = x;
    r->n++;
    return true;
}
```

(Kısalık için başta bir `b_ara` var, tekrarlı anahtarları reddetmek için; gerçek kodda bu kontrol inişle birleştirilir. `calloc` hata kontrolü de yok.)

Yaprağa ekleme, Ders 4.2'deki sıralı diziye eklemenin aynısı: büyükleri bir sağa kaydır, boşluğa yaz. $O(T)$, ama $T$ en fazla birkaç yüz ve kaydırılan veri tek bir bloğun içinde.

**Kök bölünmesi** B-ağacının yükseklik kazanmasının tek yolu: yeni ve boş bir kök açılıyor, eski kök onun tek çocuğu oluyor ve bölünüyor. Ağaç **yukarıdan** büyüyor. Bütün yapraklar aynı anda bir seviye derine iniyor, bu yüzden kural 4 hiçbir zaman bozulmuyor. İkili ağaçlarda dengeyi korumak için gereken dönmelerin hiçbiri burada yok; denge yapının kendisinden geliyor.

### Denetleyici ve iz

```c
/* Denetci: siralama, anahtar sayilari, butun yapraklar ayni derinlikte. Yapragin derinligini dondurur. */
int b_denetle(const BDugum *d, long alt, long ust, bool kok) {
    if (!kok && (d->n < T - 1 || d->n > MAKS)) { printf("anahtar sayisi bozuk: %d\n", d->n); abort(); }
    for (int i = 0; i < d->n; i++) {
        long a = i ? d->anahtar[i - 1] : alt;
        if (d->anahtar[i] <= a || d->anahtar[i] >= ust) { puts("sira bozuk"); abort(); }
    }
    if (d->yaprak) return 0;
    int derin = -1;
    for (int i = 0; i <= d->n; i++) {
        long a = i ? d->anahtar[i - 1] : alt, b = i < d->n ? d->anahtar[i] : ust;
        int k = b_denetle(d->cocuk[i], a, b, false);
        if (derin >= 0 && k != derin) { puts("yapraklar farkli derinlikte"); abort(); }
        derin = k;
    }
    return derin + 1;
}
```

$T = 2$ ile 1'den 10'a kadar ekleyip her adımda ağacı seviye seviye yazdıralım ve denetleyelim:

```c
int main(void) {
    BDugum *kok = yeni_dugum(true);
    printf("T=%d (dugum basina %d-%d anahtar)\n", T, T - 1, MAKS);
    for (int x = 1; x <= 10; x++) {
        b_ekle(&kok, x);
        printf("ekle %d:\n", x); b_yazdir(kok);
        b_denetle(kok, LONG_MIN, LONG_MAX, true);
    }
    b_serbest(kok);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme_main.c -o deneme && ./deneme
T=2 (dugum basina 1-3 anahtar)
ekle 1:
  [1] 
ekle 2:
  [1 2] 
ekle 3:
  [1 2 3] 
ekle 4:
  [2] 
  [1] [3 4] 
ekle 5:
  [2] 
  [1] [3 4 5] 
ekle 6:
  [2 4] 
  [1] [3] [5 6] 
ekle 7:
  [2 4] 
  [1] [3] [5 6 7] 
ekle 8:
  [2 4 6] 
  [1] [3] [5] [7 8] 
ekle 9:
  [4] 
  [2] [6] 
  [1] [3] [5] [7 8 9] 
ekle 10:
  [4] 
  [2] [6 8] 
  [1] [3] [5] [7] [9 10]
```

- `ekle 4`: kök `[1 2 3]` dolu. Önce bölünüyor (2 yeni köke çıkıyor), sonra 4 sağ yarıya giriyor.
- `ekle 7` sonrası `[2 4] / [1] [3] [5 6 7]`: Ders 8.10'da kırmızı-siyah ağaca 1..7 ekleyince 2-3-4 görünümünde **aynısı** çıkmıştı. İki kod tamamen farklı ama aynı soyut yapıyı kuruyor.
- `ekle 9`: 9'un gideceği yaprak `[7 8]`'de yer var, ama inerken geçilen kök `[2 4 6]` dolu ve **önceden** bölünüyor. Ağaç gerekmediği halde bir seviye büyüdü. Önceden bölmenin bedeli bu: biraz daha erken büyüme (Alıştırma 3).

---

## 4. Düğüm boyutu ve cache

B-ağacı disk için tasarlandı, ama aynı mantık bellek hiyerarşisinin her seviyesinde geçerli. RAM, L1 cache'e göre "yavaş bir disk" (Ders 7.24). Ölçelim: 1 milyon anahtar karışık sırayla ekleniyor, sonra 1 milyon arama başka bir karışık sırayla yapılıyor (5 tekrarın ortalaması). $T$'yi derlemede değiştiriyoruz:

```c
/* Dugum boyutu (T) degisince B-agaci aramasi: yukseklik, ziyaret edilen dugum, sure */
#include "btree.c"
#include <limits.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void) {
    int n = 1000000;
    int *a = malloc(n * sizeof *a), *q = malloc(n * sizeof *q);
    for (int i = 0; i < n; i++) a[i] = q[i] = 2 * i;          /* cift sayilar */
    srand(1);
    for (int i = n - 1; i > 0; i--) { int j = rand() % (i + 1), t = a[i]; a[i] = a[j]; a[j] = t; }
    for (int i = n - 1; i > 0; i--) { int j = rand() % (i + 1), t = q[i]; q[i] = q[j]; q[j] = t; }
    BDugum *kok = yeni_dugum(true);
    for (int i = 0; i < n; i++) b_ekle(&kok, a[i]);
    int h = b_denetle(kok, LONG_MIN, LONG_MAX, true);
    ziyaret = 0;
    double t0 = simdi(); long bulunan = 0;
    for (int tekrar = 0; tekrar < 5; tekrar++)
        for (int i = 0; i < n; i++) bulunan += b_ara(kok, q[i]);
    double sn = (simdi() - t0) / 5;
    printf("T=%4d  dugum=%5zu bayt  yukseklik=%d  ziyaret/arama=%.2f  arama %.0f ns\n",
           T, sizeof(BDugum), h, (double)ziyaret / (5.0 * n), sn * 1e9 / n);
    b_serbest(kok);
    if (bulunan != 5L * n) abort();
}
```

```
$ for t in 2 4 8 16 32 64 128 256; do cc -std=c11 -O2 -Wall -DT=$t olcum.c -o olcum_$t && ./olcum_$t; done
T=   2  dugum=   56 bayt  yukseklik=15  ziyaret/arama=15.43  arama 313 ns
T=   4  dugum=  104 bayt  yukseklik=8  ziyaret/arama=8.78  arama 175 ns
T=   8  dugum=  200 bayt  yukseklik=5  ziyaret/arama=5.90  arama 131 ns
T=  16  dugum=  392 bayt  yukseklik=4  ziyaret/arama=4.95  arama 87 ns
T=  32  dugum=  776 bayt  yukseklik=3  ziyaret/arama=3.98  arama 73 ns
T=  64  dugum= 1544 bayt  yukseklik=3  ziyaret/arama=3.99  arama 79 ns
T= 128  dugum= 3080 bayt  yukseklik=2  ziyaret/arama=2.99  arama 77 ns
T= 256  dugum= 6152 bayt  yukseklik=2  ziyaret/arama=3.00  arama 62 ns
```

Aynı sorgularla iki karşılaştırma noktası (Ders 8.10'daki kırmızı-siyah ağaç ve sıralı bir dizide düz ikili arama):

```
kirmizi-siyah         arama 136 ns
sirali dizi, ikili ara arama 43 ns
```

| Yapı | Arama (ns) | Düğüm ziyareti |
| --- | --- | --- |
| B-ağacı, $T = 2$ | 313 | 15.4 |
| Kırmızı-siyah | 136 | ~19 |
| B-ağacı, $T = 8$ | 131 | 5.9 |
| B-ağacı, $T = 32$ | 73 | 4.0 |
| Sıralı dizi | 43 | (dizi, pointer yok) |

Okunacaklar:

- **Yükseklik** $T$ ile hızla düşüyor: $T = 32$'de 3, Bölüm 1'deki sınırla aynı. Ziyaret edilen düğüm sayısı yükseklik + 1'e yakın (anahtarlar çoğunlukla yapraklarda, çünkü yaprak sayısı iç düğüm sayısının yaklaşık $T$ katı).
- **$T = 32$ kırmızı-siyahtan 1.9 kat hızlı.** Karşılaştırma sayısı aşağı yukarı aynı ($\log_2 n \approx 20$; her düğümdeki ikili arama $\log_2 63 \approx 6$ karşılaştırma), ama cache kaçırma sayısı çok farklı. Kırmızı-siyah ağaçta her adım rastgele bir adrese atlıyor. B-ağacında bir düğümün içindeki adımlar aynı 776 baytlık blokta ve sadece 4 kez başka bir bloğa atlanıyor.
- **$T = 2$ en yavaşı**, kırmızı-siyahtan bile yavaş: 2-3-4 ağacı ile aynı yapı, ama her düğümde döngü ve dallanma maliyeti var ve düğüm (56 bayt) bir ikili düğümden büyük. Küçük $T$, B-ağacının bütün avantajını kaybettiriyor.
- $T = 32$'den sonra kazanç yok: düğüm birkaç cache satırını aşınca düğüm içindeki ikili aramanın kendisi cache kaçırmaya başlıyor. Bu makinede tatlı nokta yüzlerce bayt ile birkaç kilobayt arası. Diskte ise tatlı nokta sayfa boyutu (4 KB ya da 16 KB), yani $T$ yüzler mertebesinde.
- **Sıralı dizi** hepsinden hızlı, ama ekleme $O(n)$. B-ağacı, "sıralı diziyi bloklara bölüp blokları bir ağaçla bağlamak" olarak da düşünülebilir: sıralı dizinin yerelliğini ağacın ucuz eklemesiyle birleştiriyor.

### Düğüm içinde doğrusal arama

63 anahtarlık bir dizide ikili arama mı, baştan sona doğrusal tarama mı? Ders 7.22'nin dersi: ikili aramanın her adımı tahmin edilemeyen bir dal. Doğrusal taramanın dalı ise neredeyse hep aynı yöne gidiyor ve bellek erişimi tamamen ardışık. `yer_bul`'u tek satırlık doğrusal taramayla değiştirip ölçelim:

```c
static int yer_bul(const BDugum *d, int x) { int i = 0; while (i < d->n && d->anahtar[i] < x) i++; return i; }
```

| $T$ | İkili (ns) | Doğrusal (ns) |
| --- | --- | --- |
| 4 | 175 | 134 |
| 8 | 131 | 89 |
| 16 | 87 | 83 |
| 32 | 73 | 78 |
| 64 | 79 | 88 |
| 128 | 77 | 113 |

Küçük düğümlerde doğrusal tarama **daha hızlı**; ancak 30–60 anahtardan sonra ikili arama öne geçiyor. Gerçek B-ağacı kütüphaneleri ikisini karıştırıyor: önce ikili aramayla aralığı daraltıp sonra kısa bir doğrusal (ya da SIMD, Faz 11) tarama yapıyorlar.

---

## 5. Diskte B-ağacı

Bir veritabanı tablosundaki satırları birincil anahtara göre indeksleyen yapı neredeyse her zaman bir B-ağacı. Düğüm tam olarak bir **sayfa**: SQLite'ta varsayılan 4 KB, PostgreSQL'de 8 KB, InnoDB'de 16 KB. Pointer'lar bellek adresi değil, dosyadaki **sayfa numarası**. 8 baytlık anahtar ve 8 baytlık sayfa numarasıyla 16 KB'lık bir düğüm yaklaşık 1000 çocuk tutar:

| Seviye | Ulaşılan anahtar |
| --- | --- |
| 1 (kök) | ~1 000 |
| 2 | ~1 000 000 |
| 3 | ~1 000 000 000 |

Kök ve ikinci seviye zaten bellekte tutulur (birkaç megabayt), bu yüzden bir milyar satırlı bir tabloda arama **tek** disk okumasıyla biter.

Pratikte kullanılan çoğunlukla **B+ ağacı**:

- Değerler (satırlar ya da onlara pointer'lar) sadece **yapraklarda**. İç düğümler sadece yön gösteren anahtarlar tutuyor, bu yüzden bir sayfaya daha fazla anahtar sığıyor ve ağaç daha da sığlaşıyor.
- Yapraklar birbirine bağlı bir liste (Ders 8.2). `WHERE fiyat BETWEEN 35 AND 65` gibi bir aralık sorgusu, ilk yaprağı bir aramayla bulup sonra yaprak listesinde ilerliyor; ağaçta geri çıkmak gerekmiyor (Ders 8.8, Alıştırma 2'nin disk hali).

Silme bu derste yok; ekleme gibi tek geçişte yapılabiliyor. Bir düğüme inmeden önce onun en az $T$ anahtarı olduğu garanti ediliyor: kardeşinden bir anahtar ödünç alınıyor ya da kardeşiyle birleştiriliyor (bölmenin tersi). Kök boşalırsa ağaç yukarıdan bir seviye kısalıyor. Ayrıntılı durumlar CLRS 18.3'te.

---

## Alıştırmalar

**1** – $T = 128$ ile 1 milyar ($10^9$) anahtarlık bir B-ağacının yüksekliği en fazla ne olur? Aynı anahtarlarla bir kırmızı-siyah ağacın yüksekliği en fazla?

**2** – Bölüm 3'teki izde `ekle 8` adımında ne oluyor? Önce hangi düğüm bölünüyor, 8 nereye giriyor? Ders 8.10'daki kırmızı-siyah ağaçta buna hangi durum karşılık geliyor?

**3** – Önceden bölme, `ekle 9` adımında gerekmeyen bir bölünmeye yol açtı. Bu neden bir sorun değil? Tek geçişli eklemenin, aşağıdan yukarı bölmeye göre ne avantajı var (ipucu: ebeveyn pointer'ları ve aynı ağaca aynı anda erişen birden çok iş parçacığı)?

**4** – Bölüm 1'deki tanımda bir düğüm neden en az $T - 1$ anahtar tutmalı? Alt sınır hiç olmasaydı (düğümler 1 ile $2T-1$ arası anahtar tutabilseydi), ağacın yüksekliği ve bellek kullanımı hakkında ne söylenebilirdi?

**5** – $T = 32$ bir B-ağacının düğümü 776 bayt. Bunun ne kadarı anahtar, ne kadarı pointer? Yaprak düğümlerde `cocuk` dizisi hiç kullanılmıyor. Yaprakların sayısını düşünerek bellekte ne kadar israf olduğunu kabaca hesapla ve bir çözüm öner.

<details>
<summary>Cevaplar</summary>

**1** – $h \le \log_{128} \frac{10^9 + 1}{2} = \frac{\log_2(5 \cdot 10^8)}{7} \approx \frac{28.9}{7} \approx 4.13$, yani en fazla **4** (5 seviye). Kırmızı-siyah ağaçta $h \le 2\log_2(10^9 + 1) \approx 59.8$, en fazla 59. Diskte bu, 5 okumaya karşı 60 okuma demek; üstelik B-ağacının üst iki seviyesi bellekte tutulursa 3 okuma.

**2** – 8'in gideceği yer, kökün en sağ çocuğu `[5 6 7]`. İnerken kök `[2 4]` dolu değil, ama çocuk `[5 6 7]` dolu: bölünüyor, ortanca 6 köke çıkıyor ve kök `[2 4 6]` oluyor. 8, sağ yarıya (`[7]`) girip `[7 8]` oluyor. Kırmızı-siyah ağaçta bu **durum 1**: dolu bir 2-3-4 düğümü siyah bir düğüm ve iki kırmızı çocuğu demek; bölünme, iki kırmızı çocuğu siyaha ve siyah ebeveyni kırmızıya boyamak. Kırmızıya dönen 6, yukarıdaki düğüme katılmış oldu.

**3** – Gereksiz bölünme sadece kökü bir süre erken büyütüyor ve bazı düğümleri yarı dolu bırakıyor. Kurallar bozulmuyor, ve yükseklik sınırı (Bölüm 1) hâlâ geçerli; en fazla bir seviye ve bir miktar boş yer kaybı. Avantajı ise büyük: bölünmeler hiçbir zaman yukarı yayılmadığı için ebeveyn pointer'ı ya da inilen yolun bir yığında saklanması gerekmiyor. Disk tabanlı bir ağaçta yukarı dönmek, daha önce okunmuş sayfaları tekrar okumak ya da kilitli tutmak demek. Eş zamanlı erişimde, bir iş parçacığı bir düğüme inince onun ebeveyninin bir daha değişmeyeceği garanti olduğu için ebeveynin kilidi hemen bırakılabiliyor ("kilit kuplajı", lock coupling). Faz 10'daki eş zamanlı veri yapılarının temel bir tekniği.

**4** – Alt sınır olmadan ağaç seyrekleşebilir: bir sürü silmeden sonra, her düğümde tek anahtar kalabilir ve ağaç ikili bir ağaca döner. Kural 4 (yapraklar aynı derinlikte) hâlâ yükseklik için $\log_2 n$ sınırı verir, ama B-ağacının asıl kazancı olan $\log_T n$ kaybolur. Her düğüm yine de tam bir sayfa yer kapladığı için bellek kullanımı $2T - 1$ kata kadar kötüleşebilir. Alt sınır, düğümlerin en az **yarı dolu** olmasını, dolayısıyla hem kısa yolları hem de en az %50 doluluk oranını garanti ediyor. Ekleme sırasında bölünen düğümlerin iki yarısının tam $T - 1$ anahtarla başlaması, bu alt sınırla uyumlu olsun diye.

**5** – `n` ve `yaprak` için 8 bayt (hizalamayla), 63 anahtar × 4 = 252 bayt, 64 pointer × 8 = 512 bayt; toplam 772, hizalamayla 776. Düğümün üçte ikisi pointer. Bir B-ağacında düğümlerin büyük çoğunluğu yaprak (iç düğüm sayısının yaklaşık $T$ katı; $T = 32$ için %95'ten fazlası), ve yapraklarda bu 512 bayt tamamen boş. Bellek kullanımı gerekenin yaklaşık 3 katı. Çözüm, iki ayrı düğüm tipi: `cocuk` dizisi olmayan bir yaprak yapısı ve onu içeren bir iç düğüm yapısı (Ders 8.1'deki opak tip ya da ortak başlıklı iki struct, Ders 4.27). B+ ağacında aynı fikir daha da ileri gidiyor: yapraklar anahtar + değer, iç düğümler anahtar + çocuk tutuyor.

</details>

---

## Kaynaklar

- Rudolf Bayer ve Edward McCreight, "Organization and Maintenance of Large Ordered Indexes", *Acta Informatica* 1(3), 1972.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 18: B-ağaçları; tek geçişli ekleme (18.2) ve silme (18.3).
- Douglas Comer, "The Ubiquitous B-Tree", *ACM Computing Surveys* 11(2), 1979.
- SQLite belgeleri, "Database File Format": sayfa yapısı ve B-ağacı sayfaları.
- Goetz Graefe, "Modern B-Tree Techniques", *Foundations and Trends in Databases* 3(4), 2011.

**Sıradaki ders:** Heap ve öncelik kuyruğu. İkili heap, heapify, dizi üzerinde ağaç ve olay simülasyonu.
