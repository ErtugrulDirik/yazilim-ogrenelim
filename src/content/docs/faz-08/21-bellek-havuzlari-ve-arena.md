---
title: "8.21 Bellek havuzları ve arena ile veri yapıları"
description: "Ders 4.28'deki arenanın blok zincirli, büyüyen hali: eski pointer'lar geçerli kalarak yeni blok açmak, işaret ve geri sarma ile geçici bellek, ASan'ın bellek zehirleme arayüzüyle arena içinde kullanım-sonrası hataları yakalamak; 10 milyon düğümlü bir ifade ağacını (AST) malloc yerine arenadan kurmak: kurma 1.9 kat hızlı, serbest bırakma 0.17 s'den sıfıra; tek tek serbest bırakma gerekirse arena üstünde sabit boyutlu havuz ve serbest liste: macOS'ta malloc/free çiftine 130 ns'ye karşı 3.7 ns; nesne ömürleri ve derleyicide arena kullanımı."
---

Bu fazdaki her veri yapısı düğümlerini tek tek `malloc` ile ayırıp tek tek `free` ile bıraktı. Ders 8.7'deki ifade ağacının `serbest` fonksiyonu, Ders 8.9'daki AVL'nin `avl_serbest`'i, Ders 8.14'teki tablonun `tablo_yok_et`'i: hepsi yapının bütün düğümlerini gezip her biri için `free` çağırıyor. Bu hem yavaş hem de hata kaynağı: bir düğümü unutmak sızıntı, iki kez bırakmak çökme (Ders 4.23).

Ders 4.28'deki **arena** başka bir model önermişti: bütün nesneleri tek bir büyük bloktan sırayla ayır, hepsini **tek seferde** bırak. Tek tek `free` yok. Bu ders o fikri gerçek veri yapılarına uyguluyor. Bir derleyicinin bütün AST'si, bir HTTP isteğini işlerken yaratılan her şey, bir oyunun tek bir karesinde hesaplanan her şey aynı anda doğup aynı anda ölüyor. Bu ortak ömür, arenayı neredeyse bedava yapıyor.

---

## 1. Büyüyen arena

Ders 4.28'deki arena sabit kapasiteliydi ve dolunca `NULL` dönüyordu. Alıştırma 5'te sorduğumuz soru: dolunca ne yapmalı? Bloğu `realloc` ile büyütmek, daha önce verilmiş bütün pointer'ları geçersiz kılabilir. Çözüm, orada da önerdiğimiz gibi, blokları **zincirlemek**: yer yetmeyince yeni bir blok aç, eskisini olduğu yerde bırak.

```c
/* arena.h: blok zincirli arena (Ders 4.28'in buyuyen hali). Pointer'lar arena_bosalt/yok_et'e kadar gecerli. */
#ifndef ARENA_H
#define ARENA_H
#include <stddef.h>

typedef struct Blok Blok;
typedef struct {
    Blok *simdiki;            /* ayirmalarin yapildigi blok (zincirin basi) */
    size_t blok_boyutu;       /* yeni bloklarin varsayilan boyutu */
    size_t toplam;            /* istatistik: dagitilan bayt */
} Arena;

typedef struct { Blok *blok; size_t dolu; } ArenaIsaret;    /* geri sarma noktasi */

void   arena_baslat(Arena *a, size_t blok_boyutu);
void  *arena_ayir(Arena *a, size_t boyut, size_t hiza);
char  *arena_strdup(Arena *a, const char *s);
ArenaIsaret arena_isaret(const Arena *a);
void   arena_geri_sar(Arena *a, ArenaIsaret i);   /* isaretten sonra ayrilanlarin hepsini birakir */
void   arena_yok_et(Arena *a);

#define ARENA_YENI(a, T) ((T *)arena_ayir((a), sizeof(T), _Alignof(T)))
#endif
```

`ARENA_YENI`, Ders 4.28'deki `ARENA_NEW` makrosu: tipin boyutunu ve hizalamasını (`_Alignof`) kendisi buluyor.

```c
/* arena.c: yer yetmeyince yeni blok; eski bloklar yerinde kalir, eski pointer'lar gecerli kalir. */
#include "arena.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#if defined(__has_feature)
#  if __has_feature(address_sanitizer)
#    include <sanitizer/asan_interface.h>
#    define ZEHIRLE(p, n)   ASAN_POISON_MEMORY_REGION((p), (n))
#    define TEMIZLE(p, n)   ASAN_UNPOISON_MEMORY_REGION((p), (n))
#  endif
#endif
#ifndef ZEHIRLE
#  define ZEHIRLE(p, n)   ((void)(p), (void)(n))
#  define TEMIZLE(p, n)   ((void)(p), (void)(n))
#endif

struct Blok {
    Blok *onceki;             /* zincirde bir onceki (daha eski) blok */
    size_t kapasite, dolu;
    _Alignas(max_align_t) unsigned char veri[];
};

static Blok *blok_yeni(size_t kapasite, Blok *onceki) {
    Blok *b = malloc(sizeof *b + kapasite);
    if (!b) return NULL;
    b->onceki = onceki; b->kapasite = kapasite; b->dolu = 0;
    ZEHIRLE(b->veri, kapasite);                 /* henuz dagitilmamis: dokunan ASan'a yakalanir */
    return b;
}

void arena_baslat(Arena *a, size_t blok_boyutu) { a->simdiki = NULL; a->blok_boyutu = blok_boyutu; a->toplam = 0; }

static size_t yukari_hizala(size_t n, size_t hiza) { return (n + hiza - 1) & ~(hiza - 1); }   /* Ders 4.28 */

void *arena_ayir(Arena *a, size_t boyut, size_t hiza) {
    Blok *b = a->simdiki;
    size_t ofset = b ? yukari_hizala(b->dolu, hiza) : 0;
    if (!b || ofset > b->kapasite || boyut > b->kapasite - ofset) {     /* tasmasiz kontrol (Ders 4.28 Al. 2) */
        size_t kap = boyut > a->blok_boyutu ? boyut : a->blok_boyutu;   /* buyuk istek: kendine ozel blok */
        b = blok_yeni(kap, a->simdiki);
        if (!b) return NULL;
        a->simdiki = b;
        ofset = 0;
    }
    void *p = b->veri + ofset;
    b->dolu = ofset + boyut;
    a->toplam += boyut;
    TEMIZLE(p, boyut);
    return p;
}
```

Üç ayrıntı:

- `veri` esnek dizi üyesi (Ders 8.14) ve `_Alignas(max_align_t)` ile en katı hizalamada başlıyor; bloğun başı hangi tipe verilirse verilsin doğru hizalı.
- Blok boyutundan büyük bir istek kendi boyunda özel bir blok alıyor. Bu, o anki bloğun geri kalanını boşa harcıyor; bir iyileştirme, büyük blokları zincirin **arkasına** takıp mevcut bloğu kullanmaya devam etmek.
- `ZEHIRLE` ve `TEMIZLE`: aşağıda.

### İşaret ve geri sarma

Arenanın tek seferde bırakmasının bir ara yolu: bir **işaret** al, geçici bir iş yap, sonra işarete **geri sar**. İşaretten sonra ayrılan her şey bırakılıyor, öncesi duruyor.

```c
ArenaIsaret arena_isaret(const Arena *a) { return (ArenaIsaret){ a->simdiki, a->simdiki ? a->simdiki->dolu : 0 }; }

void arena_geri_sar(Arena *a, ArenaIsaret i) {
    while (a->simdiki != i.blok) {               /* isaretten sonra acilan bloklari birak */
        Blok *b = a->simdiki;
        a->simdiki = b->onceki;
        free(b);
    }
    if (a->simdiki) {
        ZEHIRLE(a->simdiki->veri + i.dolu, a->simdiki->dolu - i.dolu);   /* geri alinan kisim artik yasak */
        a->simdiki->dolu = i.dolu;
    }
}

void arena_yok_et(Arena *a) { arena_geri_sar(a, (ArenaIsaret){ NULL, 0 }); a->toplam = 0; }
```

Bu bir **yığın** disiplini (Ders 8.4): işaretler iç içe olabilir ama sırayla, en son alınandan geri sarılmalı. Bir döngünün her turunda bir işaret alıp turun sonunda geri sarmak, turun geçici belleğini sıfır maliyetle temizliyor. `arena_yok_et` en baştaki işarete geri sarmak.

### ASan ile arena hataları

Ders 4.28'in Alıştırma 4'ü: arena içinde kullanım-sonrası hataları ASan yakalayamaz, çünkü bellek hâlâ `malloc`'un verdiği bir bloğun içinde. ASan'ın bunun için bir arayüzü var: `ASAN_POISON_MEMORY_REGION` bir bölgeyi "dokunulmaz" işaretliyor, `ASAN_UNPOISON_MEMORY_REGION` tekrar açıyor. Arena, henüz dağıtılmamış ve geri sarılmış bölgeleri zehirliyor, dağıttığı parçaları temizliyor. ASan'sız derlemede iki makro hiçbir şey yapmıyor.

```c
#include <stdio.h>
#include "arena.h"
typedef struct { double x, y; } Nokta;
int main(void) {
    Arena a; arena_baslat(&a, 64);                     /* kucuk bloklar: zincirlenmeyi gormek icin */
    Nokta *p[10];
    for (int i = 0; i < 10; i++) { p[i] = ARENA_YENI(&a, Nokta); p[i]->x = i; p[i]->y = i * i; }
    printf("10 nokta (her biri 16 bayt, blok 64 bayt): ");
    for (int i = 0; i < 10; i++) printf("%.0f ", p[i]->y);
    printf("\nadres farklari:");
    for (int i = 1; i < 10; i++) printf(" %td", (char *)p[i] - (char *)p[i - 1]);
    printf("\n");
    ArenaIsaret is = arena_isaret(&a);
    char *gecici = arena_strdup(&a, "gecici");
    printf("gecici: %s\n", gecici);
    arena_geri_sar(&a, is);
    printf("geri sarildi; p[9]->y hala %.0f\n", p[9]->y);
#ifdef HATA
    printf("geri sarilmis bellegi oku: %c\n", gecici[0]);
#endif
    arena_yok_et(&a);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c arena.c -o deneme && ./deneme
10 nokta (her biri 16 bayt, blok 64 bayt): 0 1 4 9 16 25 36 49 64 81 
adres farklari: 16 16 16 80 16 16 16 80 16
gecici: gecici
geri sarildi; p[9]->y hala 81
```

64 baytlık bloğa dört nokta sığıyor; her dört noktada bir yeni blok açılıyor ve adres sıçrıyor (80: yeni bloğun başlığı ve `malloc`'un yerleşimi). Bloklar zincirlendiği için eski noktalar yerinde: `p[0]`'dan `p[9]`'a hepsi geçerli. `-DHATA` ile geri sarılmış belleği okuyan satır açılınca:

```
$ cc -std=c11 -g -DHATA -fsanitize=address deneme.c arena.c -o hata && ./hata
==25664==ERROR: AddressSanitizer: use-after-poison on address 0x608000000258 at pc 0x000100158ddc bp 0x00016fca5e90 sp 0x00016fca5e88
READ of size 1 at 0x608000000258 thread T0
    #0 0x000100158dd8 in main deneme.c:19
    ...
SUMMARY: AddressSanitizer: use-after-poison deneme.c:19 in main
```

`use-after-poison`: arena içindeki bir kullanım-sonrası hatası, satır numarasıyla. Kendi allocator'ını yazınca kaybettiğimiz korumayı geri kazandık.

---

## 2. AST'yi arenadan kurmak

Ders 8.7'deki ifade ağacı, büyük ölçekte: 5 milyon işlem ve 5 milyon + 1 sayı düğümü, toplam 10 milyon düğüm. Ağacın şekli rastgele (her iç düğümde sol alt ağacın boyutu düzgün dağılımlı; Ders 8.8'deki rastgele BST şekli, yükseklik $O(\log n)$ ve özyineleme güvenli). Aynı ağaç iki kez kuruluyor: `malloc` ile ve arena ile.

```c
/* Ifade agaci (Ders 8.7) 10 milyon dugum: malloc/free mi, arena mi? */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "arena.h"
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

typedef struct Ifade { char op; long sayi; struct Ifade *sol, *sag; } Ifade;   /* op == 0: sayi */

static uint64_t xs;
static uint32_t rnd(void) { xs ^= xs << 13; xs ^= xs >> 7; xs ^= xs << 17; return (uint32_t)(xs >> 32); }

static Arena *arena;                  /* NULL ise malloc */

static Ifade *yeni(void) { return arena ? ARENA_YENI(arena, Ifade) : malloc(sizeof(Ifade)); }

/* n ic dugumlu rastgele agac: kok bolmesi duzgun dagilimli (rastgele BST sekli, yukseklik O(log n)) */
static Ifade *kur(long n) {
    Ifade *e = yeni();
    if (n == 0) { e->op = 0; e->sayi = rnd() % 10; e->sol = e->sag = NULL; return e; }
    long k = (long)(rnd() % (uint32_t)n);
    e->op = "+-*"[rnd() % 3];
    e->sol = kur(k); e->sag = kur(n - 1 - k);
    return e;
}

static long hesapla(const Ifade *e) {             /* sonek gezinme; tasma serbest olsun diye unsigned */
    if (!e->op) return e->sayi;
    unsigned long a = (unsigned long)hesapla(e->sol), b = (unsigned long)hesapla(e->sag);
    return (long)(e->op == '+' ? a + b : e->op == '-' ? a - b : a * b);
}

static void serbest(Ifade *e) { if (!e) return; serbest(e->sol); serbest(e->sag); free(e); }

int main(void) {
    long n = 5000000;                               /* 5M ic + 5M+1 yaprak = 10M dugum */
    for (int tekrar = 0; tekrar < 2; tekrar++) {
        for (int yontem = 0; yontem < 2; yontem++) {
            Arena a; arena_baslat(&a, 1 << 20);
            arena = yontem ? &a : NULL;
            xs = 0x9E3779B97F4A7C15ull;
            double t0 = simdi();
            Ifade *kok = kur(n);
            double t1 = simdi();
            long s = hesapla(kok);
            double t2 = simdi();
            if (yontem) arena_yok_et(&a); else serbest(kok);
            double t3 = simdi();
            printf("%-6s  kur %.3f s  hesapla %.3f s  birak %.3f s  (sonuc %ld)\n", yontem ? "arena" : "malloc",
                   t1 - t0, t2 - t1, t3 - t2, s);
        }
    }
}
```

(`malloc` hata kontrolleri kısalık için yok. Hesaplama `unsigned long` üzerinden, çünkü 10 milyon düğümlük çarpımlar `long`'u taşırır ve işaretli taşma tanımsız davranış; Ders 3.8.)

```
$ cc -std=c11 -O2 -Wall ast.c arena.c -o ast && ./ast
malloc  kur 0.166 s  hesapla 0.044 s  birak 0.167 s  (sonuc 1484802093190831560)
arena   kur 0.085 s  hesapla 0.056 s  birak 0.000 s  (sonuc 1484802093190831560)
malloc  kur 0.161 s  hesapla 0.037 s  birak 0.170 s  (sonuc 1484802093190831560)
arena   kur 0.087 s  hesapla 0.037 s  birak 0.000 s  (sonuc 1484802093190831560)
```

- **Kurma 1.9 kat hızlı**: arenada bir ayırma bir hizalama, bir karşılaştırma ve bir toplama (Ders 4.28'in ölçümü), `malloc`'ta bir fonksiyon çağrısı ve allocator'ın iç veri yapılarının güncellenmesi.
- **Serbest bırakma 0.17 s'den sıfıra**: 10 milyon `free` yerine yaklaşık 300 `free`: 32 baytlık 10 milyon düğüm 320 MB, yani 1 MB'lık 300 küsur blok. Ağacı gezmeye bile gerek yok.
- **Hesaplama aynı**: bu programda `malloc` da 32 baytlık nesneleri art arda ayırdığı için düğümler zaten neredeyse ardışık. Gerçek bir programda (bir derleyici AST düğümlerinin arasına stringler, tablolar, listeler ayırırken) `malloc`'tan gelen düğümler dağılıyor; arenada aynı türden nesneleri ayrı arenalardan ayırarak yerleşim kontrol edilebiliyor.
- Sanitizer'lı derlemede de sonuç aynı ve rapor yok.

Bellek de az: macOS'ta `malloc(24)` gerçekte 32 bayt kullanıyor (`malloc_size`), çünkü allocator her bloğu 16 baytın katına yuvarlıyor; arenada 24 baytlık bir nesne 24 bayt (artı hizalama boşluğu).

---

## 3. Tek tek bırakmak gerekirse: havuz

Arena her şeyin aynı anda öldüğü durumlar için. Ama bir AVL ağacında ya da bir hash tablosunda düğümler **tek tek** silinip ekleniyor; silinen düğümün belleği yeni eklenecek düğüm için tekrar kullanılmalı, yoksa arena sınırsız büyür.

Bütün nesneler **aynı boyuttaysa** (bir yapının bütün düğümleri gibi) çözüm basit: **sabit boyutlu havuz** (pool, slab). Bırakılan yuvaları bir **serbest listede** tut (Ders 4.29'daki serbest listenin tek boyutlu hali; boyut tek olduğu için arama, bölme, birleştirme yok). Yeni bir yuva istendiğinde önce listeden al, liste boşsa arenadan yeni yuva kes.

```c
/* Sabit boyutlu havuz: arenadan yer al, birakilanlari bir serbest listede tut (Ders 4.29'un tek boyutlu hali) */
typedef struct Bos { struct Bos *sonraki; } Bos;      /* birakilmis bir yuvanin ilk 8 bayti */
typedef struct { Arena arena; size_t boyut, hiza; Bos *serbest; } Havuz;

static void havuz_baslat(Havuz *h, size_t boyut, size_t hiza) {
    arena_baslat(&h->arena, 1 << 20);
    h->boyut = boyut < sizeof(Bos) ? sizeof(Bos) : boyut;      /* yuva en az bir pointer tutabilmeli */
    h->hiza = hiza < _Alignof(Bos) ? _Alignof(Bos) : hiza;
    h->serbest = NULL;
}
static void *havuz_al(Havuz *h) {
    if (h->serbest) { Bos *b = h->serbest; h->serbest = b->sonraki; return b; }   /* once geri donusum */
    return arena_ayir(&h->arena, h->boyut, h->hiza);
}
static void havuz_birak(Havuz *h, void *p) { Bos *b = p; b->sonraki = h->serbest; h->serbest = b; }   /* yigina it: O(1) */
static void havuz_yok_et(Havuz *h) { arena_yok_et(&h->arena); }
```

Serbest liste **intrusive** (Ders 8.3): `sonraki` pointer'ı bırakılmış yuvanın kendi içinde, ek bellek yok. Bırakılmış bir yuvanın içeriği zaten artık anlamsız. Liste bir yığın: en son bırakılan ilk verilir, ve o yuva muhtemelen hâlâ cache'te.

Ölçüm: 1 milyon canlı düğüm (24 bayt), sonra 20 milyon kez rastgele birini bırakıp yerine yenisini almak. Bir dengeli ağacın ya da bir hash tablosunun sürekli ekleme-silme altındaki davranışı:

```
$ cc -std=c11 -O2 -Wall havuz.c arena.c -o havuz && ./havuz
malloc/free: 2.584 s  (129.2 ns/cift)
havuz      : 0.075 s  (3.7 ns/cift), arenadan 24000000 bayt = dugum basina 24.0 bayt
```

İkinci çalıştırmada 139.9 ns ve 3.7 ns; sanitizer'lı derleme temiz. Bu makinede (macOS'un allocator'ı, Apple M2) havuz **35 kat** hızlı. Farkın büyüklüğü allocator'a bağlı ve bu ölçüm macOS'unkine ait; Linux'taki glibc'nin iş parçacığı başına önbelleği (tcache) gibi mekanizmalar aynı boyutlu küçük blokların geri dönüşümünü hızlandırıyor ve farkı küçültüyor. Ama yön hep aynı: genel amaçlı bir allocator her boyutu, her sırayı ve her iş parçacığını desteklemek zorunda; havuz sadece bir boyutu ve tek bir iş parçacığını.

Linux çekirdeğinin **slab allocator**'ı (`kmem_cache_create`) aynı fikrin çekirdek düzeyindeki hali: süreç tanımlayıcıları, dosya düğümleri, ağ paketleri gibi her sık nesne türü için ayrı bir havuz.

---

## 4. Ömür düşünmek

Arena ve havuz, bellek yönetimini **nesne başına** düşünmekten **ömür grubu başına** düşünmeye çeviriyor. Her nesne için "kim bunu ne zaman bırakacak" sorusu yerine, "bu nesne hangi grupla birlikte ölüyor" sorusu.

Faz 15–16'daki derleyicide ömür grupları:

| Nesneler | Ömür | Yer |
| --- | --- | --- |
| Tokenlar | Ayrıştırma bitene kadar | Geçici arena; ayrıştırmadan sonra geri sar |
| İntern edilmiş isimler (8.16) | Bütün derleme | Kalıcı arena |
| AST düğümleri | Bir fonksiyonun derlenmesi | Fonksiyon başına arena |
| Sembol tablosu girdileri | Kapsam açıkken | Havuz (kapsam kapanınca tek tek bırakılıyor) |
| Ara temsil, kod üretimi | Bir fonksiyon | Fonksiyon başına arena |

Clang'in `ASTContext`'i bütün AST düğümlerini bir `BumpPtrAllocator`'dan (bir arena) ayırıyor ve düğümleri hiç tek tek silmiyor. GCC'nin `obstack`'leri, Apache ve nginx'in istek başına havuzları, oyun motorlarının kare başına arenaları aynı tasarım.

Bedeli de var:

- **Arena pointer'ı dışarı kaçarsa**: bir arenadan ayrılmış nesneye, arenadan uzun yaşayan bir yerden (global bir değişken, başka bir arenadaki bir yapı) pointer verilirse, arena bırakıldığında o pointer sallanır. Kural: kısa ömürlü bir arenadaki nesne, uzun ömürlü bir arenadakini gösterebilir; tersi olamaz.
- **Kaynaklar**: arena belleği bırakıyor ama dosyaları kapatmıyor, kilitleri bırakmıyor. Bir arena nesnesi bir `FILE *` ya da ayrıca `malloc` edilmiş bir tampon tutuyorsa, onlar sızıyor (Alıştırma 4).
- **İçeride büyüyen nesneler**: Ders 4.24'teki dinamik dizi arenada büyütülemez (`realloc` yok); her büyütme yeni yer ayırır ve eskisi arenada boşa kalır. Ders 8.24'te bunu nasıl yöneteceğimizi göreceğiz.

---

## Alıştırmalar

**1** – Bir program bir dosyayı satır satır okuyor; her satır için birkaç geçici string ve küçük bir dizi ayırıp satırı işliyor, sonra satırın sonuçlarından sadece birkaç sayıyı saklıyor. Arena ve işaret/geri sarma ile bunu nasıl yaparsın? İşaretleri neden ters sırada geri sarmak gerekiyor; sırayı bozarsan ne olur?

**2** – Ders 8.16'daki `intern` her ismi ayrı bir `malloc` ile ayırıyordu ve `intern_temizle` hepsini tek tek bırakıyordu. Arenayla yeniden yaz. Kova dizisi de arenadan ayrılabilir mi? (İpucu: kova dizisi büyüyor.)

**3** – Havuza ASan desteği ekle: `havuz_birak` yuvayı zehirlesin ki bırakılmış bir düğüme erişim yakalansın. Ama serbest liste `sonraki` pointer'ını yuvanın içinde tutuyor; zehirli bir yuvadan nasıl okuyacaksın?

**4** – Arenadan ayrılmış bir nesne, ayrıca `fopen` ile açılmış bir dosya tutuyor. `arena_yok_et` dosyayı kapatmaz. Arenaya, yok edilirken çağrılacak **temizleme fonksiyonları** kaydedebilme özelliği ekle. Bu kayıtları nerede saklarsın, ve hangi sırayla çağırmalısın?

**5** – Bölüm 2'deki ağaçta, `malloc` sürümünün `serbest` fonksiyonu özyinelemeli. 10 milyon düğümlü ama **dengesiz** (her iç düğümün sol çocuğu yaprak olan) bir ağaçta ne olur (Ders 8.6)? Arena sürümünde bu sorun var mı?

<details>
<summary>Cevaplar</summary>

**1** – Satırlardan uzun yaşayacak sonuçlar ayrı (kalıcı) bir arenada ya da düz değişkenlerde; geçici her şey bir **kazıma** (scratch) arenasında:

```c
Arena gecici; arena_baslat(&gecici, 1 << 16);
while (fgets(satir, sizeof satir, f)) {
    ArenaIsaret is = arena_isaret(&gecici);
    /* ... arena_strdup(&gecici, ...), ARENA_YENI(&gecici, ...) ... */
    toplam += sonuc;                 /* saklanacak tek sey: bir sayi */
    arena_geri_sar(&gecici, is);     /* bu satirin butun gecici bellegi gitti */
}
arena_yok_et(&gecici);
```

İlk satırdan sonra arena bloğu bir kere açılmış oluyor ve her satır aynı bloğu baştan kullanıyor: döngüde hiç `malloc` yok. İşaretler bir yığın: `a`'yı aldıktan sonra `b`'yi alıp önce `a`'ya geri sararsan, `b`'den sonra ayrılanlar da gidiyor (doğru), ama sonra `b`'ye geri sarmak, `b.dolu` değerini **artık geçersiz** olan bir ofsete geri koyuyor: `a` ile `b` arasındaki bellek dağıtılmış sanılıyor, ve `b.blok` serbest bırakılmış bir blok olabilir. Bizim kodumuz bunu denetlemiyor; gerçek kütüphaneler hata ayıklama derlemesinde işaretlerin sırasını kontrol ediyor.

**2** – `Ip` girdileri `arena_ayir(&a, sizeof(Ip) + n + 1, _Alignof(Ip))` ile ayrılır, `intern_temizle` sadece `arena_yok_et` olur. Kova dizisi büyürken eski dizi atılıyor; arenadan ayrılırsa her büyütmede eski dizi arenada boşa kalır. Toplam boşa giden: $256 + 512 + \dots + m/2 < m$ pointer, yani en fazla son dizinin boyutu kadar; geometrik büyümede kabul edilebilir bir kayıp (Ders 4.24). Alternatif: kova dizisini `malloc` ile tutup sadece stringleri arenadan ayırmak. Bu, Bölüm 4'teki "içeride büyüyen nesneler" sorununun tipik çözümü: büyüyen omurga `malloc`'ta, değişmeyen yükler arenada.

**3** – `havuz_birak` önce `b->sonraki`'yi yazar, sonra yuvanın **tamamını** zehirler. `havuz_al`, listeden bir yuva alırken önce o yuvayı temizler (`TEMIZLE(b, h->boyut)`), sonra `b->sonraki`'yi okur. Kodun kendisi zehirli bölgeye sadece temizledikten sonra dokunuyor; kullanıcı kodu bırakılmış bir düğüme dokunursa ASan `use-after-poison` raporlar. (Daha ince bir yol: yuvanın ilk 8 baytını açık bırakıp sadece geri kalanını zehirlemek; ama o zaman bırakılmış düğümün ilk alanına yazan bir hata yakalanmaz.) Bir de çift bırakma: `havuz_birak` aynı yuvayı iki kez listeye koyarsa liste döngüye girer; yuva zehirliyken ikinci `havuz_birak`'ın `b->sonraki = ...` yazması ASan'a yakalanır.

**4** – Arenada bir temizleme listesi: `struct Temizleme { void (*f)(void *); void *veri; struct Temizleme *sonraki; }`, girdiler arenanın kendisinden ayrılıyor. `arena_temizlik_ekle(a, fclose_sarmal, dosya)`. `arena_yok_et` önce listeyi gezip fonksiyonları çağırıyor, sonra blokları bırakıyor. Sıra **ters** (en son eklenen ilk), çünkü sonra oluşturulan nesneler öncekilere bağımlı olabilir: önce bir tampon açılıp sonra onu kullanan bir sıkıştırıcı oluşturulduysa, önce sıkıştırıcı kapatılmalı. Liste başa ekleme yaptığı için doğal sırası zaten ters. Geri sarma da işaretten sonra eklenen temizlemeleri çağırmalı. Apache'nin APR havuzlarındaki `apr_pool_cleanup_register` tam bu.

**5** – Sol çocukları yaprak olan bir ağaçta sağ omurga 5 milyon düğüm uzunluğunda. `serbest`'in özyineleme derinliği 5 milyon, ve Ders 8.6'da ölçtüğümüz 8 MB'lık yığın birkaç yüz bin çerçevede bitiyor: program **çöker**. (`kur` ve `hesapla` da aynı ağaçta çöker.) Arena sürümünde serbest bırakma ağacı hiç gezmiyor: 10 bloğu bırakmak, ağacın şeklinden bağımsız. Arena, "veri yapısının şekli ne olursa olsun bırakma $O(\text{blok sayısı})$" garantisi veriyor; bu, büyük ve şekli öngörülemeyen yapılar (derleyicilerdeki uzun `else if` zincirlerinin AST'si tam böyle bir sağa yatık ağaç) için önemli bir sağlamlık.

</details>

---

## Kaynaklar

- David Hanson, "Fast Allocation and Deallocation of Memory Based on Object Lifetimes", *Software: Practice and Experience* 20(1), 1990: arenalar ve lcc'deki kullanımı.
- Jeff Bonwick, "The Slab Allocator: An Object-Caching Kernel Memory Allocator", *USENIX Summer* 1994.
- Ryan Fleury, "Untangling Lifetimes: The Arena Allocator", 2022: arena merkezli C programlama.
- LLVM, `llvm/Support/Allocator.h`: `BumpPtrAllocator`; Clang'de `ASTContext`'in AST düğümlerini ayırması.
- AddressSanitizer belgeleri, "ManualPoisoning": `ASAN_POISON_MEMORY_REGION` ve `ASAN_UNPOISON_MEMORY_REGION`.

**Sıradaki ders:** Kalıcı (persistent) yapılar. Yol kopyalama, değişmez (immutable) liste ve ağaç.
