---
title: "8.5 Kuyruk ve deque"
description: "İlk giren ilk çıkar (FIFO) ve iki uçtan ekleme/çıkarma (deque); düz dizide kuyruğun neden kaydığı ve halka tamponun (ring buffer) çözümü; kapasite 2'nin kuvveti olunca % yerine & (kapasite − 1) ile sarmalama, Apple M2'de 3.5 ns'ye karşı 0.8 ns; sarmış bir tamponu büyütmek; kuyrukla labirentte en kısa yolu bulan genişlik öncelikli arama (BFS) ve yerine yığın konunca ne olduğu; iki yığınla kuyruk ve kayan pencere maksimumu alıştırmaları."
---

Ders 8.4'teki yığın en son geleni ilk çıkarıyordu. Gerçek hayattaki sıraların çoğu tersini ister: bankadaki sıra, yazıcıya gönderilen belgeler, klavyeden gelen tuşlar, ağ kartına gelen paketler. **İlk gelen ilk çıkar**: FIFO (first in, first out). Bu yapının adı **kuyruk** (queue). Bu ders kuyruğu ve onun genelleşmiş hali **deque**'yu (double-ended queue, "dek" okunur, iki uçtan da ekleyip çıkarılabilen kuyruk) tek bir yapıyla, **halka tamponla** yazıyor. Yol üstünde Faz 5'teki bir bit hilesinin (Ders 5.7) neden bütün işletim sistemlerinin ve ses sürücülerinin içinde olduğunu göreceğiz, sonra kuyrukla bir labirentin en kısa yolunu bulacağız.

---

## 1. İşlemler ve ilk deneme

Kuyruk: **sona ekle** (enqueue), **baştan çek** (dequeue). Deque buna iki işlem daha ekler: **başa ekle**, **sondan çek**. Deque hem kuyruk hem yığın olarak kullanılabilir (yalnızca sona ekleyip sondan çekersen yığın), bu yüzden tek bir deque yazıp ikisini de ondan elde edeceğiz.

```c
/* deque.h: iki uclu kuyruk (deque). Kuyruk = sona ekle + bastan cek. */
#ifndef DEQUE_H
#define DEQUE_H

#include <stdbool.h>
#include <stddef.h>

typedef struct Deque Deque;

Deque *deque_olustur(void);
void   deque_yok_et(Deque *d);
bool   deque_sona_ekle(Deque *d, long x);
bool   deque_basa_ekle(Deque *d, long x);
bool   deque_bastan_cek(Deque *d, long *x);
bool   deque_sondan_cek(Deque *d, long *x);
bool   deque_bas(const Deque *d, long *x);
bool   deque_son(const Deque *d, long *x);
size_t deque_boyut(const Deque *d);
void   deque_ic_yazdir(const Deque *d);   /* hata ayiklama: tamponun ham hali */

#endif
```

Uygulama için ilk akla gelen, Ders 8.4'teki dizi: sona ekle, **baştan** çek. Ama baştan çekmek ya bütün diziyi bir sola kaydırmak ($O(n)$), ya da bir `bas` indeksi tutup ilerletmek. İkincisi her işlemi $O(1)$ yapıyor, ama yeni bir sorun çıkıyor:

```
ekle 1 2 3, cek, cek, ekle 4 5:

  [ . | . | 3 | 4 | 5 ]  ->  ekle 6: dizinin sonuna geldik
          ^bas        ^son
```

Kuyruk dizi içinde **sağa kayıyor**: baştaki yuvalar boşaldı ama kullanılmıyor. Toplam eleman sayısı küçük kalsa bile dizi sürekli büyümek zorunda. Çözüm: dizinin sonuna gelince **başa dön**. Diziyi uçları birleştirilmiş bir halka gibi düşün.

---

## 2. Halka tampon

**Halka tampon** (ring buffer, circular buffer): sabit boyutlu bir dizi, bir `bas` konumu ve bir `adet`. Bir sonraki boş yuva `(bas + adet) % kapasite`; sona ulaşan indeks modülo aritmetiğiyle (Ders 6.18) başa sarar.

```
kapasite 4:

  1 2 3 sona     [ 1  2  3  . ]   bas=0 adet=3
                   ^bas
  2 kez cek      [ .  .  3  . ]   bas=2 adet=1
                         ^bas
  4 5 sona       [ 5  .  3  4 ]   bas=2 adet=3     5, yer (2+2) % 4 = 0'a sardi
                         ^bas
  sira (bastan):  3, 4, 5
```

Elemanların mantıksal sırası, tampondaki fiziksel sıradan farklı: `bas`'tan başla, sona gelince 0'a dön.

### `%` yerine `&`

`% kapasite` bir **bölme** komutu. Ders 5.7'deki gözlem: $m = 2^k$ ise $x \bmod m$ = $x$'in alt $k$ biti = `x & (m - 1)`. Kapasiteyi her zaman 2'nin kuvveti tutarsak bölme yerine tek bir AND yeter. Fark gerçek mi? Kapasitenin çalışma anında belli olduğu (derleyicinin sabit sanıp kendisi optimize edemeyeceği) bir döngüyle ölçelim:

```c
/* Halka indeksi: % mi & mi? Kapasite calisma aninda belli (derleyici sabit sanamaz). */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

__attribute__((noinline)) static long tur_mod(long *t, size_t kap, long n) {
    size_t bas = 0, son = 0; long s = 0;
    for (long i = 0; i < n; i++) {
        t[son] = i;            son = (son + 1) % kap;     /* ekle */
        s += t[bas];           bas = (bas + 1) % kap;     /* cek  */
    }
    return s;
}

__attribute__((noinline)) static long tur_maske(long *t, size_t kap, long n) {
    size_t bas = 0, son = 0, m = kap - 1; long s = 0;
    for (long i = 0; i < n; i++) {
        t[son] = i;            son = (son + 1) & m;
        s += t[bas];           bas = (bas + 1) & m;
    }
    return s;
}

__attribute__((noinline)) static long tur_dal(long *t, size_t kap, long n) {
    size_t bas = 0, son = 0; long s = 0;
    for (long i = 0; i < n; i++) {
        t[son] = i;            if (++son == kap) son = 0;
        s += t[bas];           if (++bas == kap) bas = 0;
    }
    return s;
}

int main(int argc, char **argv) {
    size_t kap = argc > 1 ? strtoul(argv[1], NULL, 10) : 1024;
    long *t = calloc(kap, sizeof *t), n = 200000000;
    long (*f[])(long *, size_t, long) = { tur_mod, tur_maske, tur_dal };
    const char *ad[] = { "% kap", "& (kap-1)", "if (++i == kap)" };
    for (int k = 0; k < 3; k++) {
        double t0 = simdi(); long s = f[k](t, kap, n); double sn = simdi() - t0;
        printf("%-16s toplam=%ld  %.3f s  %.2f ns/tur\n", ad[k], s, sn, sn * 1e9 / n);
    }
    free(t);
}
```

(Bu döngüde kuyruk hep tek elemanlı, çünkü her turda bir ekleyip bir çekiyoruz; ölçülen sadece **indeks aritmetiğinin** maliyeti.)

```
$ cc -std=c11 -O2 -Wall maske.c -o maske && ./maske 1024
% kap            toplam=19999999900000000  0.733 s  3.66 ns/tur
& (kap-1)        toplam=19999999900000000  0.158 s  0.79 ns/tur
if (++i == kap)  toplam=19999999900000000  0.209 s  1.05 ns/tur
```

Apple M2'de `%` sürümü **4.6 kat** yavaş. Derleyicinin ürettiği koda bakınca sebep açık: her `%` bir `udiv` (tamsayı bölme) ve bir `msub` (bölüm × kapasite'yi çıkar) oluyor, ve tamsayı bölme modern işlemcilerde bile 10 döngü civarı gecikmeli bir komut (toplamanın 1 döngüsüne karşı; Ders 7.23). Üstelik `son`'un yeni değeri bir sonraki turda gerekiyor: bölmeler bir bağımlılık zinciri oluşturuyor. `&` tek döngülük bir komut. Üçüncü yol, "sona gelince sıfırla" dalı, kapasite 2'nin kuvveti olmasa da çalışır ve neredeyse maske kadar hızlı: dal 1024 turda bir alınıyor ve tahminci onu kolayca öğreniyor (Ders 7.22).

`%`'in tek kurtuluşu derleyicinin kapasiteyi bildiği durum: `% 1024` sabitse derleyici onu kendisi `& 1023`'e çevirir (Ders 5.14). Kapasite değişken olduğu anda bu kaybolur. Bu yüzden Linux çekirdeğinin `kfifo`'su, ses ve ağ sürücülerinin tamponları, ve işlemcinin kendi içindeki kuyruklar (Ders 7.23'teki ROB tam bir halka tampon) kapasitelerini 2'nin kuvveti seçer.

---

## 3. Deque'nin tamamı

```c
/* deque.c: halka tampon (ring buffer). Kapasite hep 2'nin kuvveti. */
#include "deque.h"
#include <stdio.h>
#include <stdlib.h>

struct Deque {
    long  *tampon;
    size_t kapasite;   /* 2'nin kuvveti */
    size_t bas;        /* ilk elemanin konumu (0..kapasite-1) */
    size_t adet;
};

/* i. elemanin (bastan sayarak) tampondaki yeri. kapasite 2^k oldugu icin
   "% kapasite" yerine "& (kapasite - 1)": bolme yok, tek AND. */
static size_t yer(const Deque *d, size_t i) { return (d->bas + i) & (d->kapasite - 1); }

Deque *deque_olustur(void) {
    Deque *d = malloc(sizeof *d);
    if (!d) return NULL;
    d->kapasite = 4;
    d->tampon = malloc(d->kapasite * sizeof *d->tampon);
    if (!d->tampon) { free(d); return NULL; }
    d->bas = d->adet = 0;
    return d;
}

void deque_yok_et(Deque *d) { if (d) { free(d->tampon); free(d); } }

/* Dolunca kapasiteyi ikiye katla. Elemanlari sirayla yeni tamponun basina tasi:
   realloc yetmez, cunku eleman dizisi tamponun sonundan basina "sarmis" olabilir. */
static bool buyut(Deque *d) {
    size_t yeni_kap = 2 * d->kapasite;
    long *yeni = malloc(yeni_kap * sizeof *yeni);
    if (!yeni) return false;
    for (size_t i = 0; i < d->adet; i++) yeni[i] = d->tampon[yer(d, i)];
    free(d->tampon);
    d->tampon = yeni;
    d->kapasite = yeni_kap;
    d->bas = 0;
    return true;
}

bool deque_sona_ekle(Deque *d, long x) {
    if (d->adet == d->kapasite && !buyut(d)) return false;
    d->tampon[yer(d, d->adet)] = x;
    d->adet++;
    return true;
}

bool deque_basa_ekle(Deque *d, long x) {
    if (d->adet == d->kapasite && !buyut(d)) return false;
    d->bas = (d->bas - 1) & (d->kapasite - 1);      /* 0 - 1 sarar: size_t'de tanimli (Ders 3.8) */
    d->tampon[d->bas] = x;
    d->adet++;
    return true;
}

bool deque_bastan_cek(Deque *d, long *x) {
    if (d->adet == 0) return false;
    *x = d->tampon[d->bas];
    d->bas = (d->bas + 1) & (d->kapasite - 1);
    d->adet--;
    return true;
}

bool deque_sondan_cek(Deque *d, long *x) {
    if (d->adet == 0) return false;
    *x = d->tampon[yer(d, d->adet - 1)];
    d->adet--;
    return true;
}

bool deque_bas(const Deque *d, long *x) {
    if (d->adet == 0) return false;
    *x = d->tampon[d->bas];
    return true;
}

bool deque_son(const Deque *d, long *x) {
    if (d->adet == 0) return false;
    *x = d->tampon[yer(d, d->adet - 1)];
    return true;
}

size_t deque_boyut(const Deque *d) { return d->adet; }

void deque_ic_yazdir(const Deque *d) {
    printf("kap=%zu bas=%zu adet=%zu  tampon: [", d->kapasite, d->bas, d->adet);
    for (size_t k = 0; k < d->kapasite; k++) {
        size_t i = (k - d->bas) & (d->kapasite - 1);    /* bu yuva bastan kacinci? */
        if (i < d->adet) printf(k ? " %2ld" : "%2ld", d->tampon[k]);
        else             printf(k ? "  ." : " .");
    }
    printf("]\n");
}
```

Birkaç ince nokta:

- **Başa ekleme** `bas`'ı bir **geri** alıyor: `(bas - 1) & (kapasite - 1)`. `bas = 0` iken `0 - 1`, `size_t`'de en büyük değere sarar (`0xFFFF...FF`; işaretsiz taşma tanımlı, Ders 3.8), ve `& (kapasite - 1)` onu `kapasite - 1`'e indirir: dizinin son yuvası. Doğru sonuç, tek ifade.
- **Büyütme** `realloc` ile yapılamıyor. Sarmış bir tamponda (`[5 . 3 4]` gibi) elemanlar dizinin iki ucuna dağılmış; diziyi uzatmak araya boşluk sokar ve sırayı bozar. `buyut` elemanları **mantıksal sırayla** yeni dizinin başına kopyalıyor ve `bas`'ı 0 yapıyor. Kapasite ikiye katlandığı için hâlâ 2'nin kuvveti, ve Ders 4.24'teki analiz aynen geçerli: ekleme amortize $O(1)$.
- **Boş ve dolu** ayrımı `adet` ile. Sadece `bas` ve `son` tutan tasarımlarda `bas == son` hem "boş" hem "dolu" anlamına gelebilir; ya bir yuva bilerek boş bırakılır ya da ayrı bir sayaç tutulur (Alıştırma 4).

Çalışırken tamponun ham hali:

```c
#include <stdio.h>
#include "deque.h"

int main(void) {
    Deque *q = deque_olustur();
    long x;
    for (long i = 1; i <= 3; i++) deque_sona_ekle(q, i);
    printf("1 2 3 sona     "); deque_ic_yazdir(q);
    deque_bastan_cek(q, &x); deque_bastan_cek(q, &x);
    printf("2 kez bastan   "); deque_ic_yazdir(q);
    deque_sona_ekle(q, 4); deque_sona_ekle(q, 5);
    printf("4 5 sona       "); deque_ic_yazdir(q);           /* 5 tamponun basina sardi */
    deque_basa_ekle(q, 0);
    printf("0 basa         "); deque_ic_yazdir(q);           /* dolu */
    deque_sona_ekle(q, 6);
    printf("6 sona (buyur) "); deque_ic_yazdir(q);
    printf("bastan:");
    while (deque_bastan_cek(q, &x)) printf(" %ld", x);
    printf("\n");
    deque_yok_et(q);
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c deque.c -o deneme && ./deneme
1 2 3 sona     kap=4 bas=0 adet=3  tampon: [ 1  2  3  .]
2 kez bastan   kap=4 bas=2 adet=1  tampon: [ .  .  3  .]
4 5 sona       kap=4 bas=2 adet=3  tampon: [ 5  .  3  4]
0 basa         kap=4 bas=1 adet=4  tampon: [ 5  0  3  4]
6 sona (buyur) kap=8 bas=0 adet=5  tampon: [ 0  3  4  5  6  .  .  .]
bastan: 0 3 4 5 6
```

- `4 5 sona`: 5 dizinin sonundan başa **sardı** (yuva 0).
- `0 basa`: `bas` 2'den 1'e geriledi; tampon artık dolu ve mantıksal sıra `0 3 4 5`, fiziksel olarak `[5 0 3 4]`.
- `6 sona`: dolu tampona ekleme, büyütme. Elemanlar mantıksal sırayla yeni tamponun başına dizildi.

| İşlem | Halka tampon deque | Çift yönlü liste (8.3) |
| --- | --- | --- |
| Başa / sona ekleme | $O(1)$ amortize | $O(1)$ |
| Baştan / sondan çekme | $O(1)$ | $O(1)$ |
| `i`. elemana erişim | $O(1)$: `tampon[yer(d, i)]` | $O(i)$ |
| Ortaya ekleme | $O(n)$ | $O(1)$ (düğüm elindeyse) |
| Bellek | Tek blok, yan yana | Düğüm başına `malloc` + 2 pointer |

C++'ın `std::deque`'i ve Rust'ın `VecDeque`'i bu tasarımın varyantları; Python'un `collections.deque`'i ise blokların çift yönlü listesi (ikisinin karışımı).

---

## 4. Uygulama: labirentte en kısa yol

Ders 2.4'te bir labirent oyunu yazmıştık; oyuncu yolu kendisi buluyordu. Şimdi bilgisayar bulsun, ve **en kısasını** bulsun.

**Genişlik öncelikli arama** (BFS, breadth-first search): başlangıçtan uzaklığı 0 olan hücreler, sonra 1 olanlar, sonra 2 olanlar... diye katman katman ilerle. Bunu sağlayan şey kuyruk: bir hücrenin komşularını kuyruğun **sonuna** ekliyoruz, sıradaki hücreyi **baştan** alıyoruz. Böylece $d$ uzaklıktaki bütün hücreler, $d+1$ uzaklıktakilerin hepsinden önce işleniyor. Bir hücre ilk kez görüldüğünde ona verilen uzaklık, **en kısa** uzaklık (Faz 9'da ispatlayacağız).

```c
/* Labirentte en kisa yol: genislik oncelikli arama (BFS) bir kuyrukla */
#include <stdio.h>
#include <string.h>
#include "deque.h"

#define S 7
#define G 11
static char harita[S][G + 1] = {
    "###########",
    "#B..#.....#",
    "#.#.#.###.#",
    "#.#...#...#",
    "#.#####.#.#",
    "#.......#C#",
    "###########",
};

int main(void) {
    int uzaklik[S][G];
    memset(uzaklik, -1, sizeof uzaklik);            /* -1: henuz gorulmedi */
    int bs = 1, bg = 1;                               /* B'nin yeri */
    Deque *q = deque_olustur();
    uzaklik[bs][bg] = 0;
    deque_sona_ekle(q, bs * G + bg);                  /* (satir, sutun) tek sayi olarak */
    long kod, en_cok = 0;
    int cs = -1, cg = -1;
    while (deque_bastan_cek(q, &kod)) {
        int s = (int)(kod / G), g = (int)(kod % G);
        if (harita[s][g] == 'C') { cs = s; cg = g; break; }
        int ds[] = { -1, 1, 0, 0 }, dg[] = { 0, 0, -1, 1 };
        for (int k = 0; k < 4; k++) {
            int ys = s + ds[k], yg = g + dg[k];
            if (harita[ys][yg] != '#' && uzaklik[ys][yg] < 0) {
                uzaklik[ys][yg] = uzaklik[s][g] + 1;  /* ilk gorulen = en kisa */
                deque_sona_ekle(q, ys * G + yg);
            }
        }
        if ((long)deque_boyut(q) > en_cok) en_cok = (long)deque_boyut(q);
    }
    printf("cikisa en kisa yol: %d adim (kuyruk en fazla %ld eleman)\n", uzaklik[cs][cg], en_cok);
    /* yolu geri izle: her adimda uzakligi bir az olan komsuya git */
    int s = cs, g = cg;
    while (uzaklik[s][g] > 0) {
        int ds[] = { -1, 1, 0, 0 }, dg[] = { 0, 0, -1, 1 };
        for (int k = 0; k < 4; k++) {
            int ys = s + ds[k], yg = g + dg[k];
            if (uzaklik[ys][yg] == uzaklik[s][g] - 1) { s = ys; g = yg; break; }
        }
        if (harita[s][g] == '.') harita[s][g] = '*';
    }
    for (int i = 0; i < S; i++) printf("  %s\n", harita[i]);
    deque_yok_et(q);
    return 0;
}
```

Hücreyi kuyrukta tek bir `long` olarak tutuyoruz: `satir * G + sutun` (Ders 4.3'teki iki boyutlu indeksin tek boyuta açılması), çekince `/` ve `%` ile geri açıyoruz.

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined bfs.c deque.c -o bfs && ./bfs
cikisa en kisa yol: 16 adim (kuyruk en fazla 2 eleman)
  ###########
  #B**#*****#
  #.#*#*###*#
  #.#***#..*#
  #.#####.#*#
  #.......#C#
  ###########
```

16 adım. Bu labirentte aynı uzunlukta ikinci bir yol da var (sol sütundan aşağı, alt koridordan sağa); BFS komşuları "yukarı, aşağı, sol, sağ" sırasıyla eklediği ve geri izleme ilk uygun komşuyu seçtiği için bunu buldu. Yolu bulmak için ayrı bir şey saklamadık: `uzaklik` dizisi yeterli. Çıkıştan geriye, her adımda uzaklığı bir eksik olan bir komşuya giderek başlangıca dönülüyor.

Her hücre kuyruğa en fazla bir kez giriyor (ilk görüldüğünde `uzaklik` dolduruluyor ve bir daha eklenmiyor): $O(\text{hücre sayısı})$. Bu, Faz 9'daki graf algoritmalarının ilki; hücreler düğüm, komşuluklar kenar.

---

## Alıştırmalar

**1** – `bfs.c`'de `deque_bastan_cek`'i `deque_sondan_cek` yap: kuyruk yığına döndü (Ders 8.4). Önce Bölüm 4'teki labirentte, sonra içi boş bir odada (B `(1,1)`'de, C `(3,3)`'te, duvarsız 5 × 9'luk bir alan) dene. Bulunan "en kısa yol" hâlâ en kısa mı? Neden?

**2** – Sadece iki **yığınla** bir kuyruk yap: `ekle` birinci yığına iter; `cek`, ikinci yığın boşsa birincidekilerin hepsini ikinciye aktarır, sonra ikinciden çeker. `ekle 1, 2, 3; cek; ekle 4; cek, cek, cek` ne verir? Bir `cek` $O(n)$ sürebiliyorken neden her işlem **amortize** $O(1)$?

**3** – **Kayan pencere maksimumu**: bir dizide, uzunluğu $k$ olan her pencerenin en büyük elemanını $O(n)$ toplam zamanda bul. İpucu: deque'de **indeksleri**, karşılık gelen değerler azalan sırada olacak şekilde tut; yeni eleman gelince ondan küçük ya da eşit olanları **sondan** at, pencereden çıkanı **baştan** at. `[1, 3, -1, -3, 5, 3, 6, 7]`, $k = 3$ için çıktı ne?

**4** – Bazı halka tamponlar `adet` yerine hiç sıfırlanmayan iki sayaç tutar: `okunan` ve `yazilan` (`size_t`). Eleman sayısı `yazilan - okunan`, yuva `yazilan & (kap - 1)`. Sayaçlar $2^{64}$'te sararsa ne olur? Bu tasarımın Linux'un tek üreticili/tek tüketicili `kfifo`'sunda neden tercih edildiğini düşün (iki iş parçacığı, Faz 10).

**5** – Kapasite 6 olsaydı `& (kap - 1)` ne yapardı? `yer(d, i)` için `bas = 4`, `i = 0..5` değerlerini `% 6` ve `& 5` ile hesapla.

<details>
<summary>Cevaplar</summary>

**1** – Bölüm 4'teki labirentte yine 16 çıkıyor: koridorlar o kadar dar ki hemen her hücreye tek bir yoldan ulaşılıyor, sıra fark etmiyor. Boş odada fark ortaya çıkıyor:

```
== kuyruk (BFS)                          == yigin
cikisa en kisa yol: 4 adim               cikisa en kisa yol: 16 adim
  ###########                              ###########
  #B**......#                              #B********#
  #..*......#                              #........*#
  #..C......#                              #..C******#
  #.........#                              #.........#
  #.........#                              #.........#
  ###########                              ###########
```

Yığınla arama **derinlik öncelikli** (DFS) oluyor: en son eklenen komşuya, yani hep aynı yönde, gidebildiği yere kadar gidiyor ve odayı dolanıp C'ye 16 adımda varıyor. Bir hücreye "ilk ulaşma" artık en kısa yoldan değil, ilk keşfedilen yoldan; ve `uzaklik` bir kez yazılınca değişmediği için 16 yanlışlıkla "en kısa" diye raporlanıyor. BFS'in en kısa yolu bulmasının tek sebebi kuyruğun FIFO olması. DFS'in de yerleri var (bir yolun **var olup olmadığını** az bellekle bulmak, Faz 9'daki topolojik sıralama), ama en kısa yol için yanlış araç.

**2** – Deque'nin bir ucunu yığın olarak kullanarak:

```c
typedef struct { Deque *gelen, *giden; } IkiYigin;
static void ky_ekle(IkiYigin *q, long x) { deque_sona_ekle(q->gelen, x); }
static int ky_cek(IkiYigin *q, long *x) {
    if (deque_boyut(q->giden) == 0) { long t; while (deque_sondan_cek(q->gelen, &t)) deque_sona_ekle(q->giden, t); }
    return deque_sondan_cek(q->giden, x);
}
```

Çıktı `cek 1`, sonra `cek 2`, `cek 3`, `cek 4`: FIFO sırası korunuyor. Aktarma birinci yığını **ters çevirerek** ikinciye koyuyor (yığından yığına aktarma ters çevirir), ve ters çevrilmiş yığının tepesi en eski eleman. Amortize analiz: her eleman en fazla **bir kez** `gelen`'e itilir, bir kez oradan çekilir, bir kez `giden`'e itilir, bir kez oradan çekilir. $n$ işlemde toplam iş $O(n)$, işlem başına $O(1)$ (Ders 4.24'teki ikiye katlamanın aynı türden bir argümanı). Bu yapı, sadece yığınları olan (değişmez listeli) fonksiyonel dillerde kuyruğun standart uygulaması (Ders 8.22).

**3** –

```c
static void pencere_max(const long *a, int n, int k) {
    Deque *d = deque_olustur(); long i_son, i_bas;
    for (int i = 0; i < n; i++) {
        while (deque_son(d, &i_son) && a[i_son] <= a[i]) deque_sondan_cek(d, &i_son);
        deque_sona_ekle(d, i);
        deque_bas(d, &i_bas);
        if (i_bas <= i - k) deque_bastan_cek(d, &i_bas);
        if (i >= k - 1) { deque_bas(d, &i_bas); printf(" %ld", a[i_bas]); }
    }
    printf("\n");
    deque_yok_et(d);
}
```

```
pencere max (k=3): 3 3 5 5 6 7
```

Değişmez: deque'deki indekslerin değerleri baştan sona **azalan**, ve hepsi şu anki pencerenin içinde. O halde pencerenin maksimumu her zaman baştaki. Yeni gelen $a_i$'den küçük bir eleman bir daha asla maksimum olamaz ($a_i$ ondan büyük ve pencerede ondan daha uzun kalacak), bu yüzden sondan atılıyor. Her indeks deque'ye bir kez girip en fazla bir kez çıktığı için toplam $O(n)$; her pencere için $k$ elemana bakan saf yöntem $O(nk)$. Hem baştan hem sondan çıkarma gerektiği için yığın da kuyruk da yetmiyor: tam bir deque problemi.

**4** – Sararlar ve hiçbir şey bozulmaz. `yazilan - okunan` işaretsiz çıkarma, modülo $2^{64}$ (Ders 3.8): `yazilan` sarıp küçük bir sayıya döndüğünde bile fark doğru eleman sayısını verir (yeter ki gerçek fark $2^{64}$'ten küçük olsun, ki her zaman öyle). Yuva hesabı da doğru, çünkü $2^{64}$, kapasitenin ($2^k$) katı: `yazilan & (kap - 1)` sarmadan etkilenmez. Faydası: "boş" (`yazilan == okunan`) ve "dolu" (`yazilan - okunan == kap`) hiç karışmıyor, ve **üretici sadece `yazilan`'ı, tüketici sadece `okunan`'ı değiştiriyor**. İki iş parçacığı aynı değişkene yazmadığı için kilit gerekmiyor, sadece doğru bellek sıralaması (Faz 10'daki bellek bariyerleri). Bizim `bas`/`adet` tasarımımızda iki taraf da `adet`'i değiştiriyor; aynı şey kilitsiz yapılamaz.

**5** – Kapasite 6 = `110`, `kap - 1` = 5 = `101`. `bas + i` = 4, 5, 6, 7, 8, 9:

| `bas + i` | `% 6` | `& 5` |
| --- | --- | --- |
| 4 | 4 | 4 |
| 5 | 5 | 5 |
| 6 | 0 | 4 |
| 7 | 1 | 5 |
| 8 | 2 | 0 |
| 9 | 3 | 1 |

`& 5` sadece 0, 1, 4, 5 yuvalarını kullanıyor (bit 1 her zaman siliniyor) ve 6 ile 4'ü aynı yuvaya eşliyor: elemanlar birbirinin üstüne yazılır. Maske hilesi **sadece** $2^k$ için doğru, çünkü sadece o zaman $m - 1$'in bütün alt bitleri 1 (Ders 5.7). Bu yüzden `deque_olustur` 4'ten başlayıp her seferinde ikiye katlıyor; kullanıcının istediği bir kapasiteyi kabul eden bir arayüz onu bir sonraki 2'nin kuvvetine yuvarlamalı (Ders 5.9'daki `clz` ile).

</details>

---

## Kaynaklar

- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 4.6: FIFO kuyrukları, dizi ile halka uygulama.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 2.2.2: ardışık yerleşimde kuyruk ve deque.
- Linux çekirdeği, `include/linux/kfifo.h` ve `lib/kfifo.c`: 2'nin kuvveti boyutlu, kilitsiz tek üretici/tek tüketici halka tamponu.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 10.1 (kuyruklar) ve 22.2 (BFS).

**Sıradaki ders:** Özyineleme ve yığın ilişkisi. Özyinelemeli fonksiyonu açık yığınla döngüye çevirme.
