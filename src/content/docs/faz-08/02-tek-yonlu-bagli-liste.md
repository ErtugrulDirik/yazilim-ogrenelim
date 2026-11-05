---
title: "8.2 Tek yönlü bağlı liste"
description: "Kendine pointer tutan struct ile düğüm; kutu-ok diyagramları; başa ekleme O(1), sona ekleme O(n); arama; pointer'a pointer ile özel durumsuz silme ve ekleme; yerinde ters çevirme (üç pointer); düğümleri serbest bırakırken use-after-free tuzağı ve ASan çıktısı; dizi ile karmaşıklık karşılaştırması; aynı 4 milyon düğümü ayrıldıkları sırayla ve karışık bağlayınca toplamanın 0.45 ns'den 80 ns'ye çıkması (Apple M2)."
---

Ders 4.24'teki dinamik dizi elemanları belleğe **yan yana** koyuyordu: `a[i]`'nin adresi `a + i`. Bunun güzel sonuçları vardı (her elemana $O(1)$'de erişim, önbellek dostu gezinme; Ders 7.24–7.26), ama bir bedeli de: ortaya bir eleman eklemek ya da silmek, arkasındaki her şeyi kaydırmak demek (Ders 8.1'deki sıralı kümede `memmove`).

**Bağlı liste** tersini seçiyor: her eleman kendi küçük bellek parçasında, istediği yerde duruyor, ve bir sonraki elemanın **adresini** yanında taşıyor. Yan yana olmak zorunda değiller; sıra pointer'larla kuruluyor. Bu ders tek yönlü listeyi (her düğüm sadece **sonrakini** biliyor) sıfırdan yazıyor ve bu fazın en çok kullanacağımız pointer tekniğini, **pointer'a pointer** ile özel durumsuz kodu öğretiyor (Ders 4.10'un uygulaması).

---

## 1. Düğüm

```c
typedef struct Dugum {
    int deger;
    struct Dugum *sonraki;      /* struct kendi tipine pointer tutabilir */
} Dugum;
```

Bir `struct` kendi tipinden bir **alan** içeremez (sonsuz boyutlu olurdu), ama kendi tipine bir **pointer** içerebilir: pointer'ın boyutu sabit (8 bayt). `typedef` henüz tamamlanmadığı için içeride `struct Dugum *` yazmak zorundayız.

Bütün liste tek bir pointer: ilk düğümün adresi, **baş** (head). Boş liste `NULL`. Son düğümün `sonraki`'si `NULL`: "liste burada bitiyor".

Liste algoritmalarını anlamanın en iyi yolu **çizmek**. Her düğüm iki bölmeli bir kutu, sol bölmede değer, sağ bölmede bir ok:

```
 bas
  |
  v
+---+---+    +---+---+    +---+---+
| 1 | *-+--->| 3 | *-+--->| 4 | / |
+---+---+    +---+---+    +---+---+
                                  ^ NULL
```

Programımız bunu tek satırda çizecek: `bas -> [1|*]-->[3|*]-->[4|/]`. Bir liste fonksiyonu yazarken önce kağıtta, değişecek her oku çizerek düşün; kodu sonra yaz.

---

## 2. Bütün program

```c
/* Tek yonlu bagli liste: temel islemler */
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

typedef struct Dugum {
    int deger;
    struct Dugum *sonraki;      /* struct kendi tipine pointer tutabilir */
} Dugum;

static Dugum *dugum_yeni(int deger, Dugum *sonraki) {
    Dugum *d = malloc(sizeof *d);
    if (!d) { perror("malloc"); exit(1); }
    d->deger = deger;
    d->sonraki = sonraki;
    return d;
}

/* Kutu-ok diyagrami: [deger|*]--> ... [deger|/] */
static void ciz(const char *ad, const Dugum *bas) {
    printf("%-8s ", ad);
    if (!bas) { printf("bas -> NULL\n"); return; }
    printf("bas -> ");
    for (const Dugum *d = bas; d; d = d->sonraki)
        printf(d->sonraki ? "[%d|*]-->" : "[%d|/]", d->deger);
    printf("\n");
}

/* O(1): yeni dugum eski basin onune gecer */
static void basa_ekle(Dugum **bas, int deger) {
    *bas = dugum_yeni(deger, *bas);
}

/* O(n): sona kadar yuru. Pointer'a pointer ile bos liste ozel durum degil. */
static void sona_ekle(Dugum **bas, int deger) {
    Dugum **p = bas;
    while (*p) p = &(*p)->sonraki;
    *p = dugum_yeni(deger, NULL);
}

static Dugum *bul(Dugum *bas, int deger) {
    for (Dugum *d = bas; d; d = d->sonraki)
        if (d->deger == deger) return d;
    return NULL;
}

/* Ilk esleseni sil. p, "bu dugumu gosteren pointer"in adresi. */
static bool sil(Dugum **bas, int deger) {
    for (Dugum **p = bas; *p; p = &(*p)->sonraki) {
        if ((*p)->deger == deger) {
            Dugum *silinecek = *p;
            *p = silinecek->sonraki;      /* oku atla */
            free(silinecek);
            return true;
        }
    }
    return false;
}

/* Yerinde ters cevir: her okun yonunu degistir. O(n) zaman, O(1) ek bellek. */
static Dugum *ters_cevir(Dugum *bas) {
    Dugum *onceki = NULL;
    while (bas) {
        Dugum *sonraki = bas->sonraki;    /* 1. devami kaybetme */
        bas->sonraki = onceki;            /* 2. oku geri cevir  */
        onceki = bas;                     /* 3. bir adim ilerle */
        bas = sonraki;
    }
    return onceki;
}

static size_t uzunluk(const Dugum *bas) {
    size_t n = 0;
    for (; bas; bas = bas->sonraki) n++;
    return n;
}

static void serbest_birak(Dugum *bas) {
    while (bas) {
        Dugum *sonraki = bas->sonraki;    /* free'den ONCE oku */
        free(bas);
        bas = sonraki;
    }
}

int main(void) {
    Dugum *liste = NULL;
    ciz("bos:", liste);
    basa_ekle(&liste, 3);
    basa_ekle(&liste, 1);
    ciz("basa:", liste);
    sona_ekle(&liste, 4);
    sona_ekle(&liste, 1);
    sona_ekle(&liste, 5);
    ciz("sona:", liste);
    printf("uzunluk=%zu, 4 bulundu mu? %s, 9 bulundu mu? %s\n", uzunluk(liste),
           bul(liste, 4) ? "evet" : "hayir", bul(liste, 9) ? "evet" : "hayir");
    sil(&liste, 1);  ciz("sil 1:", liste);    /* bastaki 1 */
    sil(&liste, 5);  ciz("sil 5:", liste);    /* sondaki */
    sil(&liste, 9);  ciz("sil 9:", liste);    /* yok: degisiklik yok */
    liste = ters_cevir(liste);
    ciz("ters:", liste);
    serbest_birak(liste);
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -g -fsanitize=address,undefined liste.c -o liste && ./liste
bos:     bas -> NULL
basa:    bas -> [1|*]-->[3|/]
sona:    bas -> [1|*]-->[3|*]-->[4|*]-->[1|*]-->[5|/]
uzunluk=5, 4 bulundu mu? evet, 9 bulundu mu? hayir
sil 1:   bas -> [3|*]-->[4|*]-->[1|*]-->[5|/]
sil 5:   bas -> [3|*]-->[4|*]-->[1|/]
sil 9:   bas -> [3|*]-->[4|*]-->[1|/]
ters:    bas -> [1|*]-->[4|*]-->[3|/]
```

ASan ve UBSan açıkken temiz bitti: sızıntı yok, geçersiz erişim yok. Şimdi fonksiyonları tek tek açalım.

---

## 3. Başa ekleme: $O(1)$

```c
static void basa_ekle(Dugum **bas, int deger) {
    *bas = dugum_yeni(deger, *bas);
}
```

Yeni düğüm oluşturulur, `sonraki`'si **eski baş** olur, sonra baş yeni düğüme çevrilir. İki ok değişiyor:

```
once:   bas --> [3|/]

        yeni: [1|*]--+
                     v
sonra:  bas --> [1|*]-->[3|/]
```

Listenin uzunluğundan bağımsız, sabit iş: $O(1)$. Boş listede de çalışıyor (`*bas` = `NULL`, yeni düğümün `sonraki`'si `NULL`).

Fonksiyon neden `Dugum *bas` değil `Dugum **bas` alıyor? Çünkü **başın kendisini** değiştiriyor. C'de argümanlar değerle geçer (Ders 4.7): `Dugum *bas` alsaydı yerel bir kopyayı değiştirir, `main`'deki `liste` değişkeni eski düğümü göstermeye devam ederdi. `&liste` geçmek, "liste değişkeninin kendisini değiştirebilirsin" demek.

---

## 4. Pointer'a pointer: özel durumsuz kod

Sona ekleme ve silme, "**bir düğümü gösteren oku** değiştirmek" işleri. Sorun şu: o ok bazen bir düğümün `sonraki` alanı, bazen de (listenin başındaysak) `bas` değişkeninin kendisi. Önce klasik, özel durumlu yazıma bakalım:

```c
/* Ozel durumlu silme: bas dugum ayri ele aliniyor */
static bool sil_naif(Dugum **bas, int deger) {
    if (*bas == NULL) return false;
    if ((*bas)->deger == deger) {              /* ozel durum: ilk dugum */
        Dugum *s = *bas;
        *bas = s->sonraki;
        free(s);
        return true;
    }
    for (Dugum *onceki = *bas; onceki->sonraki; onceki = onceki->sonraki) {
        if (onceki->sonraki->deger == deger) {
            Dugum *s = onceki->sonraki;
            onceki->sonraki = s->sonraki;
            free(s);
            return true;
        }
    }
    return false;
}
```

Çalışıyor (1–5 listesinden 1, 3, 5, 9 silinince `2 4` kalıyor, ASan temiz), ama aynı işi iki kez yazdık: bir kez baş için, bir kez geri kalanlar için. İki kopya, iki hata fırsatı.

Gözlem: `bas` da, `onceki->sonraki` de aynı tipte, `Dugum *`. İkisini **adresleriyle** tutarsak (`Dugum **`) farkları kalmaz:

```c
static bool sil(Dugum **bas, int deger) {
    for (Dugum **p = bas; *p; p = &(*p)->sonraki) {
        if ((*p)->deger == deger) {
            Dugum *silinecek = *p;
            *p = silinecek->sonraki;      /* oku atla */
            free(silinecek);
            return true;
        }
    }
    return false;
}
```

`p` her zaman "**şu anki düğümü gösteren pointer'ın adresi**":

- Başlangıçta `p = bas`, yani `&liste`: ilk düğümü gösteren pointer, `liste` değişkeni.
- `p = &(*p)->sonraki`: bir sonraki adımda, şu anki düğümün `sonraki` alanının adresi.

Silme tek satır: `*p = silinecek->sonraki`, "beni gösteren ok, artık benim sonrakimi göstersin". `p` `&liste` ise baş değişir, bir düğümün `sonraki`'sinin adresiyse o düğümün oku değişir. Kod ikisini ayırt etmiyor, etmesi de gerekmiyor:

```
p --> [bas] --> [1|*]-->[3|*]-->[4|/]      sil 3, p su an 1'in "sonraki" alanini gosteriyor:

                 +-------------+
                 |             v
      [bas] --> [1|*]  [3|*]-->[4|/]       *p = 3->sonraki;  free(3)
```

Linus Torvalds bu örneği "iyi zevk" (good taste) üzerine bir konuşmasında kullanmış: özel durumu ortadan kaldıran bir bakış açısı, özel durumu doğru ele alan koddan daha iyi. `sona_ekle` aynı fikirle:

```c
static void sona_ekle(Dugum **bas, int deger) {
    Dugum **p = bas;
    while (*p) p = &(*p)->sonraki;   /* NULL olan pointer'i bul: ya bas ya son dugumun sonraki'si */
    *p = dugum_yeni(deger, NULL);
}
```

Boş listede `*p` baştan `NULL`, `p` = `&liste`, yeni düğüm baş olur. Dolu listede `p` son düğümün `sonraki` alanında durur. Tek kod yolu. Ama dikkat: sona ekleme listenin **sonuna kadar yürümek** zorunda: $O(n)$ (Alıştırma 5).

---

## 5. Ters çevirme

Her okun yönünü değiştirmek. Üç pointer:

```c
static Dugum *ters_cevir(Dugum *bas) {
    Dugum *onceki = NULL;
    while (bas) {
        Dugum *sonraki = bas->sonraki;    /* 1. devami kaybetme */
        bas->sonraki = onceki;            /* 2. oku geri cevir  */
        onceki = bas;                     /* 3. bir adim ilerle */
        bas = sonraki;
    }
    return onceki;
}
```

İlk iki adımı çizelim (`[3]→[4]→[1]`):

```
baslangic:  onceki=NULL   bas=[3]-->[4]-->[1]-->NULL

tur 1:      sonraki=[4]
            [3]->sonraki = NULL         NULL<--[3]    [4]-->[1]-->NULL
            onceki=[3], bas=[4]

tur 2:      sonraki=[1]
            [4]->sonraki = [3]          NULL<--[3]<--[4]    [1]-->NULL
            onceki=[4], bas=[1]

tur 3:      ...                         NULL<--[3]<--[4]<--[1]
            onceki=[1], bas=NULL  ->  return [1]
```

1. adımın sırası kritik: `bas->sonraki`'yi değiştirmeden önce kaydetmezsek listenin geri kalanına giden tek yolu kaybederiz (geri kalan düğümler sızıntı olur). Yeni bellek ayrılmıyor: $O(n)$ zaman, $O(1)$ ek bellek. Döngü değişmezi (Ders 6.4'teki tümevarımla ispatlanabilir): her turun başında `onceki` işlenen kısmın **ters çevrilmiş** halinin başı, `bas` işlenmemiş kısmın başı.

---

## 6. Serbest bırakma ve klasik hata

Her düğüm ayrı bir `malloc`, yani ayrı bir `free` gerekiyor. Ders 4.23'teki hataların en sık görüleni burada:

```c
for (Dugum *d = bas; d; d = d->sonraki)   /* YANLIS: free'den sonra d->sonraki okunuyor */
    free(d);
```

Döngünün artırma kısmı `d->sonraki`'yi `free(d)`'den **sonra** okuyor. Çoğu zaman "çalışır" (bellek henüz başkasına verilmedi), ama UB. ASan hemen yakalıyor:

```
==6837==ERROR: AddressSanitizer: heap-use-after-free on address 0x602000000118 ...
READ of size 8 at 0x602000000118 thread T0
    #0 0x0001022486d4 in main hata.c:6
freed by thread T0 here:
    #0 0x000102b1d368 in free+0x7c ...
```

"8 baytlık okuma, serbest bırakılmış bir bölgeden": `sonraki` pointer'ı. Doğrusu `serbest_birak`'taki gibi: önce `sonraki`'yi bir değişkene al, sonra `free`. Liste koduyla çalışırken ASan'ı (`-fsanitize=address`) her zaman açık tut.

---

## 7. Dizi mi, liste mi?

| İşlem | Dinamik dizi (4.24) | Tek yönlü liste |
| --- | --- | --- |
| `i`. elemana erişim | $O(1)$ | $O(i)$ |
| Başa ekleme | $O(n)$ (kaydırma) | $O(1)$ |
| Sona ekleme | $O(1)$ amortize | $O(n)$ (kuyruk pointer'ıyla $O(1)$) |
| Elinde pointer'ı olan düğümden sonra ekleme/silme | $O(n)$ | $O(1)$ |
| Arama | $O(n)$ (sıralıysa $O(\log n)$) | $O(n)$ (sıralı olsa bile) |
| Eleman başına ek bellek | ~0–1 eleman (kapasite boşluğu) | 1 pointer (8 bayt) + `malloc` yükü |

Kağıt üzerinde liste ortada ekleme/silmede kazanıyor. Ama Ders 7.24'ü hatırla: listeyi gezmek **işaretçi kovalamak**. Aynı 4 milyon sayıyı bir dizide ve bir listede toplayalım; liste düğümlerini önce ayrıldıkları sırayla, sonra karışık sırayla bağlayarak (çok sayıda ekleme/silmeden sonra gerçek bir listenin hali):

```c
/* Liste mi dizi mi? Ayni 4 milyon sayiyi toplamak */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <stddef.h>

typedef struct Dugum { long deger; struct Dugum *sonraki; } Dugum;
#define N 4000000

static double simdi(void) {
    struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

static long liste_topla(const Dugum *d) { long s = 0; for (; d; d = d->sonraki) s += d->deger; return s; }

int main(void) {
    long *dizi = malloc(N * sizeof *dizi);
    Dugum **d = malloc(N * sizeof *d);            /* dugumlerin adresleri */
    for (long i = 0; i < N; i++) {
        dizi[i] = i;
        d[i] = malloc(sizeof **d);                /* her dugum ayri malloc */
        d[i]->deger = i;
    }
    /* 1) Dugumleri ayrildiklari sirayla bagla */
    for (long i = 0; i < N; i++) d[i]->sonraki = (i + 1 < N) ? d[i + 1] : NULL;
    double t0 = simdi(); long s1 = 0;
    for (long i = 0; i < N; i++) s1 += dizi[i];
    double t_dizi = simdi() - t0;
    t0 = simdi(); long s2 = liste_topla(d[0]); double t_sirali = simdi() - t0;

    ptrdiff_t fark = (char *)d[1] - (char *)d[0];

    /* 2) Ayni dugumleri rastgele sirayla bagla (cok ekleme/silmeden sonraki hal) */
    srand(1);
    for (long i = N - 1; i > 0; i--) { long j = rand() % (i + 1); Dugum *t = d[i]; d[i] = d[j]; d[j] = t; }
    for (long i = 0; i < N; i++) d[i]->sonraki = (i + 1 < N) ? d[i + 1] : NULL;
    t0 = simdi(); long s3 = liste_topla(d[0]); double t_karisik = simdi() - t0;

    printf("dizi:            toplam=%ld  %6.1f ms  %5.2f ns/eleman\n", s1, t_dizi * 1e3, t_dizi * 1e9 / N);
    printf("liste (sirali):  toplam=%ld  %6.1f ms  %5.2f ns/eleman\n", s2, t_sirali * 1e3, t_sirali * 1e9 / N);
    printf("liste (karisik): toplam=%ld  %6.1f ms  %5.2f ns/eleman\n", s3, t_karisik * 1e3, t_karisik * 1e9 / N);
    printf("dugum boyutu %zu bayt, art arda ayrilan iki dugumun adres farki %td bayt\n",
           sizeof(Dugum), fark);
    for (long i = 0; i < N; i++) free(d[i]);
    free(d); free(dizi);
    return 0;
}
```

```
$ cc -std=c11 -O2 -Wall hiz.c -o hiz && ./hiz
dizi:            toplam=7999998000000     1.1 ms   0.27 ns/eleman
liste (sirali):  toplam=7999998000000     1.8 ms   0.45 ns/eleman
liste (karisik): toplam=7999998000000   319.9 ms  79.98 ns/eleman
dugum boyutu 16 bayt, art arda ayrilan iki dugumun adres farki 16 bayt
```

(Apple M2; ikinci çalıştırma neredeyse aynı.)

- **Sıralı liste neredeyse dizi kadar hızlı.** `malloc` art arda istenen 16 baytlık düğümleri bellekte **yan yana** verdi (adres farkı 16 bayt). Düğümler fiilen bir diziye dönüşmüş; önceden getirici ve Ders 7.24 Alıştırma 5'teki "sıralı kovalama" etkisi devrede.
- **Karışık liste 180 kat yavaş.** Aynı düğümler, aynı değerler, aynı toplam; sadece okların sırası rastgele. Her adım muhtemelen yeni bir önbellek satırı ve RAM'e bir yolculuk (~80 ns, Ders 7.24'teki merdivenin tepesi).

Ders: büyük-O tablosu listenin gerçek maliyetini göstermiyor. Uzun ömürlü, çok değişen bir listenin düğümleri zamanla belleğe dağılır. Gerçek programlarda "liste mi dizi mi?" sorusunun cevabı çoğu zaman, ortadan ekleme/silme gerçekten baskın değilse, **dizi**. Bağlı listelerin parladığı yerler: düğümün başka bir yapının parçası olduğu durumlar (Ders 8.3'teki gömülü listeler), elinde düğüm pointer'ı olduğu için $O(1)$ silmenin kritik olduğu durumlar (Ders 8.3'teki LRU önbelleği), ve bellek ayırıcıların serbest listeleri (Ders 4.29). Düğümleri bir arenadan (Ders 4.28) ayırmak da yerelliği korumanın bir yolu (Ders 8.21).

---

## Alıştırmalar

**1** – `ters_cevir`'i **özyinelemeli** yaz: geri kalan listeyi ters çevir, sonra şu anki düğümü sona ekle. Kaç ek bellek kullanır (yığın çerçeveleri, Ders 7.11)? 10 milyon düğümlü bir listede ne olur?

**2** – Listeyi **tek geçişte** gezerek ortadaki düğümü bul (uzunluğu önceden bilmeden). İpucu: iki pointer, biri bir, diğeri iki adım atsın. 5 ve 6 elemanlı listelerde sonuç ne?

**3** – Bir hata sonucu son düğümün `sonraki`'si listenin ortasındaki bir düğümü gösterirse liste **döngülü** olur ve `uzunluk` sonsuza dek döner. Sabit ek bellekle döngü olup olmadığını nasıl anlarsın?

**4** – `sirali_ekle(Dugum **bas, int deger)` yaz: liste hep artan sırada kalsın. Pointer'a pointer tekniğiyle, özel durumsuz. `4, 1, 3, 5, 2, 3` sırasıyla ekleyince ne çıkar?

**5** – `sona_ekle`'yi $O(1)$ yapmak için listeye bir `son` (kuyruk) pointer'ı eklemek istiyoruz: `typedef struct { Dugum *bas, *son; } Liste;`. Hangi fonksiyonlar `son`'u güncellemek zorunda? `sil` ile **son** düğümü silmek neden yine $O(n)$?

<details>
<summary>Cevaplar</summary>

**1** –

```c
static Dugum *ters_ozy(Dugum *bas) {
    if (!bas || !bas->sonraki) return bas;      /* 0 ya da 1 dugum: zaten ters */
    Dugum *yeni_bas = ters_ozy(bas->sonraki);   /* geri kalani cevir */
    bas->sonraki->sonraki = bas;                /* eski sonrakim artik beni gostersin */
    bas->sonraki = NULL;                        /* ben sona gectim */
    return yeni_bas;
}
```

`1 2 3 4 5` → `5 4 3 2 1` (ASan temiz). Püf noktası `bas->sonraki->sonraki = bas`: özyineleme döndüğünde `bas->sonraki` hâlâ eski sonraki düğümü gösteriyor, ve o düğüm artık ters listenin **sonu**. Her düğüm için bir yığın çerçevesi: $O(n)$ ek bellek. 10 milyon düğümde onlarca bayt × 10⁷ yüzlerce MB eder; varsayılan 8 MB'lık yığın taşar ve program çöker (Ders 8.6'nın konusu: özyinelemeyi açık yığınla döngüye çevirmek). Döngülü sürüm $O(1)$ ve her zaman tercih edilmeli.

**2** –

```c
static Dugum *orta(Dugum *bas) {
    Dugum *yavas = bas, *hizli = bas;
    while (hizli && hizli->sonraki) { yavas = yavas->sonraki; hizli = hizli->sonraki->sonraki; }
    return yavas;
}
```

`hizli` sona vardığında `yavas` yolun yarısında. 5 elemanda (`5 4 3 2 1`) ortadaki 3; 6 elemanda (`1..6`) **4**, yani iki ortadan ikincisi. İlkini istersen döngü koşulunu `hizli->sonraki && hizli->sonraki->sonraki` yap.

**3** – Aynı iki pointer fikri (Floyd'un "kaplumbağa ve tavşan" algoritması): `yavas` bir, `hizli` iki adım. Döngü yoksa `hizli` `NULL`'a ulaşır. Döngü varsa ikisi de döngüye girer, ve döngünün içinde `hizli` `yavas`'a her turda bir adım yaklaştığı için bir noktada **aynı düğümde** buluşurlar:

```c
static bool dongu_var(const Dugum *bas) {
    const Dugum *yavas = bas, *hizli = bas;
    while (hizli && hizli->sonraki) {
        yavas = yavas->sonraki; hizli = hizli->sonraki->sonraki;
        if (yavas == hizli) return true;
    }
    return false;
}
```

`1..6` listesinde 0; son düğümü 3'e bağlayınca 1. $O(n)$ zaman, $O(1)$ bellek. Alternatif (ziyaret edilen adresleri bir kümede tutmak, Ders 8.1) $O(n)$ bellek ister.

**4** –

```c
static void sirali_ekle(Dugum **bas, int v) {
    Dugum **p = bas;
    while (*p && (*p)->deger < v) p = &(*p)->sonraki;   /* ilk >= v olan dugumu gosteren ok */
    *p = dugum_yeni(v, *p);                              /* araya gir */
}
```

Sonuç `1 2 3 3 4 5`. Başa, ortaya ve sona ekleme aynı satırla: `p` hangi oku gösteriyorsa yeni düğüm o okun ucuna konuyor, eski uç yeni düğümün `sonraki`'si oluyor. Eşit değerde (`3`) yeni düğüm eskisinin **önüne** girer; `<` yerine `<=` yazsan arkasına girerdi (sıralamada "kararlılık", Faz 9).

**5** – `son`'u güncellemesi gerekenler: `sona_ekle` (her zaman: `son` yeni düğüm), `basa_ekle` (liste boşken: yeni düğüm hem baş hem son), `sil` (silinen son düğümse), `ters_cevir` (baş ve son yer değiştirir), `serbest_birak` (ikisi de `NULL`). Unutulan tek bir güncelleme, `son`'un serbest bırakılmış bir düğümü göstermesine yol açar: bir sonraki `sona_ekle`'de use-after-free. Son düğümü silmek yine $O(n)$, çünkü silindikten sonra `son`'un yeni değeri **sondan bir önceki** düğüm, ve tek yönlü listede bir düğümden öncekine gitmenin yolu baştan yürümek. Bu, Ders 8.3'teki çift yönlü listenin varlık sebebi.

</details>

---

## Kaynaklar

- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 3.3–3.4: bağlı listeler, temel işlemler.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 2.2.3: bağlı yerleşim.
- Linus Torvalds, TED 2016 röportajı ("The mind behind Linux"): pointer'a pointer ile silme ve "good taste" örneği.
- Robert Floyd'un döngü bulma algoritması: Knuth, *TAOCP* Cilt 2, Bölüm 3.1, Alıştırma 6.

**Sıradaki ders:** Çift yönlü ve dairesel liste. Gözcü (sentinel) düğüm, Linux çekirdeğindeki `list_head` ve `container_of`.
