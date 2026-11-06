---
title: "8.24 Faz projesi: mini konteyner kütüphanesi"
description: "Faz 8'in parçalarından tek bir kütüphane: blok zincirli arena, makro şablonlu tipli dinamik dizi VEC(T) ve anahtar/değer boyutları çalışma anında verilen, açık adreslemeli genel hash tablosu HTablo (ayrı kontrol baytları, mezar taşları, aynı boyutta temizlik); tek başlık dosyası, Makefile; ASan ve UBSan altında referansa karşı 2 milyon rastgele işlemle test, kümeler ve arenadaki stringlerle kelime sayma, sıralamayla bağımsız doğrulama; 4 milyon anahtarda benchmark: genel tablo, tipe özel yalın tablo ve zincirleme; genelliğin bedeli (bulma 28 ns'ye karşı 12 ns) ve ayrı kontrol baytlarının başarısız aramada kazandırdığı."
---

Faz 8 boyunca veri yapılarını tek tek yazdık, her birini kendi dersinde ölçtük. Bu proje onları bir araya getiriyor: başka programların (Faz 9'daki algoritmaların, Faz 15–16'daki derleyicinin) gerçekten `#include` edip kullanacağı küçük bir **konteyner kütüphanesi**. Üç parça:

- **Arena** (Ders 8.21): ömür grubu belleği.
- **`VEC(T)`** (Ders 4.24, 8.23): makro şablonlu, tipli dinamik dizi.
- **`HTablo`** (Ders 8.13–8.15, 8.23): genel hash tablosu; anahtar ve değer herhangi bir sabit boyutlu tip.

Bir kütüphane, bir dersteki örnek programdan farklı standartlarda yazılmalı: her `malloc` hatası ele alınıyor, arayüz belgeleniyor, ve en önemlisi **testleri** var. Bu derste kodun yarısı test. Ders 8.23'teki karar kuralını izliyoruz: değerle tutulan, sıkça gezilen dizi için makro; hash tablosu için `void *` tabanlı genellik (ve bunun bedelini, aynı algoritmanın tipe özel hali ile ölçerek); bellek için arena.

```
kap/
├── kap.h        arayüz (tek başlık)
├── arena.c      Ders 8.21'deki arena
├── vec.c        VEC büyütme fonksiyonu
├── htablo.c     genel hash tablosu
├── test.c       testler
├── bench.c      ölçümler
└── Makefile
```

---

## 1. Arayüz

```c
/* kap.h: mini konteyner kutuphanesi. Arena + makro dinamik dizi + genel hash tablosu. */
#ifndef KAP_H
#define KAP_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

/* ---------- Arena (Ders 8.21) ---------- */
typedef struct Blok Blok;
typedef struct { Blok *simdiki; size_t blok_boyutu; size_t toplam; } Arena;
typedef struct { Blok *blok; size_t dolu; } ArenaIsaret;

void   arena_baslat(Arena *a, size_t blok_boyutu);
void  *arena_ayir(Arena *a, size_t boyut, size_t hiza);
char  *arena_strdup(Arena *a, const char *s);
ArenaIsaret arena_isaret(const Arena *a);
void   arena_geri_sar(Arena *a, ArenaIsaret i);
void   arena_yok_et(Arena *a);
#define ARENA_YENI(a, T) ((T *)arena_ayir((a), sizeof(T), _Alignof(T)))

/* ---------- VEC(T): makro sablon dinamik dizi (Ders 4.24, 8.23) ----------
   Kullanim:  VEC(int) v = {0};  vec_ekle(&v, 42);  v.veri[0];  vec_yok_et(&v);
   Basarisizlikta (bellek yok) vec_ekle false doner ve dizi degismez. */
#define VEC(T) struct { T *veri; size_t adet, kap; }

bool vec__buyut(void **veri, size_t *kap, size_t eleman_boyutu, size_t gereken);

#define vec_ekle(v, x)                                                                        \
    ((v)->adet < (v)->kap ||                                                                  \
     vec__buyut((void **)&(v)->veri, &(v)->kap, sizeof *(v)->veri, (v)->adet + 1)             \
        ? ((v)->veri[(v)->adet++] = (x), true) : false)
#define vec_son(v)     ((v)->veri[(v)->adet - 1])
#define vec_cek(v)     ((v)->veri[--(v)->adet])
#define vec_temizle(v) ((v)->adet = 0)
#define vec_yok_et(v)  (free((v)->veri), (v)->veri = NULL, (v)->adet = (v)->kap = 0)

/* ---------- HTablo: genel hash tablosu (acik adresleme, dogrusal sondalama; Ders 8.15) ----------
   Anahtar ve deger, boyutlari olusturmada verilen duz bayt bloklari olarak yuvalarin ICINDE saklanir.
   Pointer anahtarlar icin (ornegin stringler) anahtar boyutu sizeof(char *) ve uygun hash/esit fonksiyonlari. */
typedef uint64_t (*HashFn)(const void *anahtar);
typedef bool     (*EsitFn)(const void *a, const void *b);

typedef struct HTablo HTablo;

HTablo *ht_olustur(size_t anahtar_boyutu, size_t deger_boyutu, HashFn h, EsitFn e);
void    ht_yok_et(HTablo *t);
void   *ht_bul(const HTablo *t, const void *anahtar);                /* degerin adresi ya da NULL */
void   *ht_koy(HTablo *t, const void *anahtar, const void *deger);   /* varsa gunceller; degerin adresi ya da NULL (bellek yok) */
bool    ht_sil(HTablo *t, const void *anahtar);
size_t  ht_boyut(const HTablo *t);

/* Gezinme: for (size_t i = 0; ht_sonraki(t, &i, &a, &d); ) { ... }  (sira tanimsiz) */
bool    ht_sonraki(const HTablo *t, size_t *konum, const void **anahtar, void **deger);

/* Hazir hash/esitlik fonksiyonlari */
uint64_t ht_hash_u64(const void *anahtar);       /* anahtar: uint64_t */
bool     ht_esit_u64(const void *a, const void *b);
uint64_t ht_hash_str(const void *anahtar);       /* anahtar: const char * (pointer'in kendisi saklanir) */
bool     ht_esit_str(const void *a, const void *b);
#endif
```

Kararlar:

- **`VEC(T)` isimsiz bir struct tipi.** `VEC(int) v = {0};` her kullanımda yeni bir tip tanımlıyor; iki ayrı `VEC(int)` değişkeni C'nin kurallarına göre **farklı** tipler ve birbirine atanamaz. Bir fonksiyona `VEC(int)` geçirmek için önce `typedef VEC(int) IntVec;` yazmak gerekiyor. stb_ds'in çözümü dizileri düz `T *` olarak tutup başlığı pointer'ın **önüne** saklamak; bizimki daha basit ve hata ayıklayıcıda okunaklı.
- **`vec_ekle` başarısızlığı bildiriyor.** `realloc` başarısız olursa dizi değişmeden kalıyor ve makro `false` döndürüyor; kullanıcı devam edip etmeyeceğine karar veriyor. Makro `x`'i bir kez, `v`'yi birkaç kez değerlendiriyor: `vec_ekle(&dizi[i++], ...)` yazılmamalı (Ders 8.23, Alıştırma 2).
- **`HTablo` opak** (Ders 8.1), anahtarı ve değeri kendi içine **kopyalıyor**. String anahtarlar için tabloda `char *` (pointer'ın kendisi) saklanıyor ve string'in belleği kullanıcının; tipik olarak bir arena (Bölüm 4'teki kelime sayma testi).
- **`ht_bul` ve `ht_koy` değerin adresini** döndürüyor (Ders 8.14'teki gibi): sayaç gibi değerler yerinde güncellenebiliyor. Bu adres bir sonraki `ht_koy`'a kadar geçerli; büyütme her şeyi taşıyor (Ders 8.15'in son tablosu).
- **Değer boyutu 0 olabilir**: tablo bir küme oluyor.

---

## 2. Arena ve VEC

`arena.c`, Ders 8.21'deki dosyanın aynısı; tek fark ilk satırın `#include "kap.h"` olması. ASan altında dağıtılmamış ve geri sarılmış bölgeleri zehirlemeye devam ediyor.

`VEC`'in tipten bağımsız tek parçası, büyütme:

```c
/* vec.c: VEC(T) makrolarinin tek tip-bagimsiz parcasi: buyutme */
#include "kap.h"
#include <stdint.h>

bool vec__buyut(void **veri, size_t *kap, size_t eleman_boyutu, size_t gereken) {
    size_t yeni = *kap ? *kap : 8;
    while (yeni < gereken) {
        if (yeni > SIZE_MAX / 2) return false;
        yeni *= 2;                                          /* ikiye katla: amortize O(1) (Ders 4.24) */
    }
    if (yeni > SIZE_MAX / eleman_boyutu) return false;      /* carpim tasmasi (Ders 3.8) */
    void *p = realloc(*veri, yeni * eleman_boyutu);
    if (!p) return false;                                   /* eski blok gecerli kaliyor */
    *veri = p; *kap = yeni;
    return true;
}
```

Ders 4.24'teki dinamik diziden iki farkı var: çarpımın taşmasını kontrol ediyor (`yeni * eleman_boyutu`; Ders 3.8, ve Ders 4.28 Alıştırma 2'deki aynı kalıp), ve `realloc` başarısız olunca eski bloğu kaybetmiyor (`*veri`'yi ancak başarıdan sonra güncelliyor; Ders 4.22'deki klasik `p = realloc(p, ...)` sızıntısı). Makro, fonksiyonu sadece dizi doluyken çağırıyor; yaygın durum (yer var) tek bir karşılaştırma ve bir atama.

---

## 3. Genel hash tablosu

```c
/* htablo.c: genel acik adresleme. Yuva duzeni: [kontrol baytlari][anahtarlar][degerler] ayri diziler. */
#include "kap.h"
#include <string.h>

enum { BOS = 0, DOLU = 1, MEZAR = 2 };

struct HTablo {
    unsigned char *kontrol;     /* yuva durumu; kap bayt */
    unsigned char *anahtar;     /* kap * anahtar_boyutu bayt */
    unsigned char *deger;       /* kap * deger_boyutu bayt */
    size_t kap, adet, mezar;    /* kap: 2'nin kuvveti */
    size_t ab, db;              /* anahtar ve deger boyutu */
    HashFn hash; EsitFn esit;
};

#define ANAHTAR(t, i) ((t)->anahtar + (i) * (t)->ab)
#define DEGER(t, i)   ((t)->deger + (i) * (t)->db)

static bool diziler_ayir(HTablo *t, size_t kap) {
    unsigned char *k = calloc(kap, 1), *a = malloc(kap * t->ab), *d = malloc(kap * (t->db ? t->db : 1));
    if (!k || !a || !d) { free(k); free(a); free(d); return false; }
    t->kontrol = k; t->anahtar = a; t->deger = d; t->kap = kap; t->adet = t->mezar = 0;
    return true;
}

HTablo *ht_olustur(size_t ab, size_t db, HashFn h, EsitFn e) {
    HTablo *t = malloc(sizeof *t);
    if (!t) return NULL;
    t->ab = ab; t->db = db; t->hash = h; t->esit = e;
    if (!diziler_ayir(t, 16)) { free(t); return NULL; }
    return t;
}

void ht_yok_et(HTablo *t) { if (!t) return; free(t->kontrol); free(t->anahtar); free(t->deger); free(t); }
size_t ht_boyut(const HTablo *t) { return t->adet; }

/* Anahtarin yuvasi; yoksa SIZE_MAX. */
static size_t ara(const HTablo *t, const void *anahtar, uint64_t h) {
    size_t m = t->kap - 1;
    for (size_t i = h & m; ; i = (i + 1) & m) {
        if (t->kontrol[i] == BOS) return SIZE_MAX;
        if (t->kontrol[i] == DOLU && t->esit(ANAHTAR(t, i), anahtar)) return i;
    }
}

void *ht_bul(const HTablo *t, const void *anahtar) {
    size_t i = ara(t, anahtar, t->hash(anahtar));
    return i == SIZE_MAX ? NULL : DEGER(t, i);
}

static bool yeniden_kur(HTablo *t, size_t yeni_kap) {
    HTablo eski = *t;
    if (!diziler_ayir(t, yeni_kap)) { *t = eski; return false; }
    for (size_t i = 0; i < eski.kap; i++)
        if (eski.kontrol[i] == DOLU) {
            size_t m = t->kap - 1, j = t->hash(eski.anahtar + i * t->ab) & m;
            while (t->kontrol[j] != BOS) j = (j + 1) & m;      /* yeni tabloda mezar yok, esitlik yok */
            t->kontrol[j] = DOLU;
            memcpy(ANAHTAR(t, j), eski.anahtar + i * t->ab, t->ab);
            memcpy(DEGER(t, j), eski.deger + i * t->db, t->db);
            t->adet++;
        }
    free(eski.kontrol); free(eski.anahtar); free(eski.deger);
    return true;
}

void *ht_koy(HTablo *t, const void *anahtar, const void *deger) {
    uint64_t h = t->hash(anahtar);
    size_t i = ara(t, anahtar, h);
    if (i != SIZE_MAX) { memcpy(DEGER(t, i), deger, t->db); return DEGER(t, i); }
    if ((t->adet + t->mezar + 1) * 4 > t->kap * 3) {           /* yuk + mezar > 0.75 */
        size_t yeni = (t->adet + 1) * 4 > t->kap * 2 ? t->kap * 2 : t->kap;   /* cogu mezarsa ayni boyutta temizle */
        if (!yeniden_kur(t, yeni)) return NULL;
    }
    size_t m = t->kap - 1;
    for (i = h & m; t->kontrol[i] == DOLU; i = (i + 1) & m) { }   /* ilk BOS ya da MEZAR */
    if (t->kontrol[i] == MEZAR) t->mezar--;
    t->kontrol[i] = DOLU;
    memcpy(ANAHTAR(t, i), anahtar, t->ab);
    memcpy(DEGER(t, i), deger, t->db);
    t->adet++;
    return DEGER(t, i);
}

bool ht_sil(HTablo *t, const void *anahtar) {
    size_t i = ara(t, anahtar, t->hash(anahtar));
    if (i == SIZE_MAX) return false;
    t->kontrol[i] = MEZAR;
    t->adet--; t->mezar++;
    return true;
}

bool ht_sonraki(const HTablo *t, size_t *konum, const void **anahtar, void **deger) {
    for (size_t i = *konum; i < t->kap; i++)
        if (t->kontrol[i] == DOLU) {
            *anahtar = ANAHTAR(t, i); *deger = DEGER(t, i); *konum = i + 1;
            return true;
        }
    *konum = t->kap;
    return false;
}

uint64_t ht_hash_u64(const void *p) {                     /* splitmix64 son karistiricisi (fmix64 benzeri, Ders 8.13) */
    uint64_t x; memcpy(&x, p, 8);
    x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ull;
    x ^= x >> 27; x *= 0x94d049bb133111ebull;
    return x ^ (x >> 31);
}
bool ht_esit_u64(const void *a, const void *b) { return memcmp(a, b, 8) == 0; }

uint64_t ht_hash_str(const void *p) {                     /* FNV-1a 64 bit + son karistirma */
    const char *s; memcpy(&s, p, sizeof s);
    uint64_t h = 1469598103934665603ull;
    while (*s) { h ^= (unsigned char)*s++; h *= 1099511628211ull; }
    return ht_hash_u64(&h);
}
bool ht_esit_str(const void *a, const void *b) {
    const char *x, *y; memcpy(&x, a, sizeof x); memcpy(&y, b, sizeof y);
    return strcmp(x, y) == 0;
}
```

Ders 8.15'teki doğrusal sondalama, üç yenilikle:

- **Ayrı diziler.** Yuva durumu (`BOS`, `DOLU`, `MEZAR`) ayrı bir **kontrol bayt dizisinde**, anahtarlar ve değerler ayrı dizilerde. Sondalama önce sadece 1 baytlık kontrol dizisini tarıyor: bir cache satırında 64 yuvanın durumu. Bir anahtar ancak yuvası `DOLU` ise karşılaştırılıyor. Google'ın Swiss Table'ının fikri; onun bir adımı daha var (Alıştırma 1).
- **Genel anahtar ve değer.** Yuvanın içindekiler düz bayt blokları; `ANAHTAR(t, i)` ve `DEGER(t, i)` makroları `i`. yuvanın adresini eleman boyutuyla hesaplıyor. Tipe özgü işlemler (hash ve eşitlik) Ders 8.23'teki gibi fonksiyon pointer'ları.
- **Büyütme ve temizlik tek fonksiyonda.** Doluluk (canlı + mezar) %75'i geçince tablo yeniden kuruluyor. Canlı girdiler kapasitenin yarısından fazlaysa kapasite ikiye katlanıyor; değilse doluluğun çoğu mezar demektir ve aynı kapasitede yeniden kurmak mezarları temizlemeye yetiyor (Ders 8.15'in Bölüm 4'ündeki birikme). Yeniden kurulan tabloda mezar yok ve bütün anahtarlar farklı, o yüzden yeniden ekleme döngüsü eşitlik karşılaştırması yapmadan ilk boş yuvayı arıyor.

Hazır hash fonksiyonları: `uint64_t` için splitmix64'ün son karıştırıcısı (Ders 8.13'teki `fmix32`'nin 64 bitlik akrabası; tam 64 bitlik çığ etkisi), stringler için 64 bitlik FNV-1a ve ardından aynı karıştırıcı (Ders 8.13'te gördüğümüz, FNV'nin son karakterleri zayıf karıştırması sorununu kapatıyor). Anahtarlar `memcpy` ile okunuyor; anahtar dizisi `malloc`'tan geldiği için hizalı olurdu ama eleman boyutu 8'in katı değilse olmayabilir, ve `memcpy` bunu dert etmiyor.

---

## 4. Testler

```c
/* test.c: kap kutuphanesi testleri. make test: ASan + UBSan ile derlenip calistirilir. */
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include "kap.h"

static int basarisiz, toplam;
#define KONTROL(kosul) do { toplam++; if (!(kosul)) { basarisiz++; \
    printf("  BASARISIZ %s:%d: %s\n", __FILE__, __LINE__, #kosul); } } while (0)

static uint64_t xs = 88172645463325252ull;
static uint64_t rnd(void) { xs ^= xs << 13; xs ^= xs >> 7; xs ^= xs << 17; return xs; }

static void test_arena(void) {
    Arena a; arena_baslat(&a, 256);
    char *c = arena_ayir(&a, 1, 1);
    double *d = ARENA_YENI(&a, double);
    long double *ld = ARENA_YENI(&a, long double);
    KONTROL(c && d && ld);
    KONTROL((uintptr_t)d % _Alignof(double) == 0);
    KONTROL((uintptr_t)ld % _Alignof(long double) == 0);
    char *buyuk = arena_ayir(&a, 10000, 1);              /* blok boyutundan buyuk */
    KONTROL(buyuk != NULL);
    memset(buyuk, 'x', 10000);
    *d = 3.5;
    ArenaIsaret is = arena_isaret(&a);
    for (int i = 0; i < 1000; i++) arena_strdup(&a, "gecici");
    arena_geri_sar(&a, is);
    KONTROL(*d == 3.5 && buyuk[9999] == 'x');           /* isaretten oncekiler saglam */
    KONTROL(strcmp(arena_strdup(&a, "merhaba"), "merhaba") == 0);
    arena_yok_et(&a);
}

typedef struct { int x; double y; } Cift;

static void test_vec(void) {
    VEC(int) v = { 0 };
    bool eklendi = true;
    for (int i = 0; i < 1000000; i++) eklendi &= vec_ekle(&v, i * 3);
    KONTROL(eklendi && v.adet == 1000000 && v.kap >= v.adet);
    int dogru = 1;
    for (int i = 0; i < 1000000; i++) if (v.veri[i] != i * 3) dogru = 0;
    KONTROL(dogru);
    KONTROL(vec_son(&v) == 2999997);
    KONTROL(vec_cek(&v) == 2999997 && v.adet == 999999);
    vec_yok_et(&v);
    KONTROL(v.veri == NULL && v.adet == 0);

    VEC(Cift) c = { 0 };
    vec_ekle(&c, ((Cift){ 1, 2.5 }));                    /* virgullu bilesik sabit: parantez sart */
    vec_ekle(&c, ((Cift){ 2, 5.0 }));
    KONTROL(c.adet == 2 && c.veri[1].x == 2 && c.veri[1].y == 5.0);
    vec_yok_et(&c);
}

/* Rastgele islemler; referans: kucuk bir aralikta duz dizi */
static void test_ht_rastgele(void) {
    enum { ARALIK = 50000 };
    static bool var[ARALIK]; static uint64_t refdeger[ARALIK];
    memset(var, 0, sizeof var);
    HTablo *t = ht_olustur(sizeof(uint64_t), sizeof(uint64_t), ht_hash_u64, ht_esit_u64);
    long hata = 0;
    for (int k = 0; k < 2000000; k++) {
        uint64_t x = rnd() % ARALIK, d = rnd();
        int op = (int)(rnd() % 4);
        if (op <= 1) { ht_koy(t, &x, &d); var[x] = true; refdeger[x] = d; }
        else if (op == 2) { if (ht_sil(t, &x) != var[x]) hata++; var[x] = false; }
        else { uint64_t *p = ht_bul(t, &x); if ((p != NULL) != var[x] || (p && *p != refdeger[x])) hata++; }
    }
    KONTROL(hata == 0);
    size_t say = 0, beklenen = 0;
    for (int x = 0; x < ARALIK; x++) beklenen += var[x];
    KONTROL(ht_boyut(t) == beklenen);
    const void *a; void *d;
    for (size_t i = 0; ht_sonraki(t, &i, &a, &d); ) { uint64_t x; memcpy(&x, a, 8); if (x < ARALIK && var[x]) say++; }
    KONTROL(say == beklenen);                            /* gezinme her anahtari tam bir kez veriyor */
    ht_yok_et(t);
}

static void test_ht_kume(void) {                         /* deger boyutu 0: kume */
    HTablo *t = ht_olustur(sizeof(uint64_t), 0, ht_hash_u64, ht_esit_u64);
    for (uint64_t i = 0; i < 100000; i += 2) ht_koy(t, &i, NULL);
    size_t bulunan = 0;
    for (uint64_t i = 0; i < 100000; i++) bulunan += ht_bul(t, &i) != NULL;
    KONTROL(bulunan == 50000 && ht_boyut(t) == 50000);
    ht_yok_et(t);
}

static int str_kars(const void *a, const void *b) { return strcmp(*(char *const *)a, *(char *const *)b); }

/* Kelime sayma: anahtarlar arenadaki stringler. Sonucu, siralayip sayarak bagimsiz dogrula. */
static void test_ht_kelime(void) {
    FILE *f = fopen("/usr/share/dict/words", "r");
    KONTROL(f != NULL);
    if (!f) return;
    Arena a; arena_baslat(&a, 1 << 16);
    HTablo *t = ht_olustur(sizeof(char *), sizeof(long), ht_hash_str, ht_esit_str);
    VEC(char *) tum = { 0 };
    char satir[128];
    while (fgets(satir, sizeof satir, f)) {
        satir[strcspn(satir, "\n")] = 0;
        for (char *p = satir; *p; p++) *p = (char)tolower((unsigned char)*p);
        if (strlen(satir) > 3) satir[3] = 0;             /* ilk 3 harf: cok tekrar uretmek icin */
        char *s = satir;
        long *n = ht_bul(t, &s);
        if (n) (*n)++;
        else { char *kopya = arena_strdup(&a, satir); long bir = 1; ht_koy(t, &kopya, &bir); }
        vec_ekle(&tum, arena_strdup(&a, satir));
    }
    fclose(f);
    qsort(tum.veri, tum.adet, sizeof(char *), str_kars);
    size_t farkli = 0; long hata = 0;
    for (size_t i = 0; i < tum.adet; ) {
        size_t j = i; while (j < tum.adet && strcmp(tum.veri[j], tum.veri[i]) == 0) j++;
        long *n = ht_bul(t, &tum.veri[i]);
        if (!n || *n != (long)(j - i)) hata++;
        farkli++; i = j;
    }
    KONTROL(hata == 0 && farkli == ht_boyut(t));
    const char *kel = "pre"; long *n = ht_bul(t, &kel);
    printf("  %zu kelime, %zu farkli 3-harfli onek; \"pre\" ile baslayan %ld kelime\n", tum.adet, farkli, n ? *n : 0);
    vec_yok_et(&tum); ht_yok_et(t); arena_yok_et(&a);
}

int main(void) {
    printf("arena\n");      test_arena();
    printf("vec\n");        test_vec();
    printf("ht rastgele\n"); test_ht_rastgele();
    printf("ht kume\n");     test_ht_kume();
    printf("ht kelime\n");   test_ht_kelime();
    printf("%d/%d kontrol gecti\n", toplam - basarisiz, toplam);
    return basarisiz != 0;
}
```

Test stratejisi:

- **`KONTROL` makrosu**: başarısız olunca dosya, satır ve koşulun metnini (`#kosul`, önişlemcinin string'e çevirme işleci) yazıyor, programı durdurmuyor. Sonda kaç kontrolün geçtiği raporlanıyor; çıkış kodu başarısızlıkta 1, ki `make` ve sürekli entegrasyon sistemleri bunu görsün.
- **Referansla karşılaştırma** (`test_ht_rastgele`): tablo, aynı işlemleri uygulanan ve doğruluğu apaçık olan düz bir diziyle karşılaştırılıyor. 50 000'lik küçük bir anahtar aralığı, aynı anahtarların sık sık eklenip silinmesini, yani mezarların birikip temizliğin tetiklenmesini garanti ediyor. Ders 8.9'dan beri kullandığımız yöntem.
- **Bağımsız doğrulama** (`test_ht_kelime`): kelime sayıları tabloyla hesaplanıyor, sonra bütün kelimeler **sıralanıp** ardışık eşitler sayılarak ikinci kez, tablodan tamamen bağımsız bir yolla hesaplanıp karşılaştırılıyor. Testin kendi hatası iki yöntemde aynı şekilde ortaya çıkmaz.
- **Kenar durumlar**: büyük hizalama (`long double`), blok boyutundan büyük istek, geri sarmadan sonra eski verinin sağlamlığı, değer boyutu 0.

```
$ make test
cc -std=c11 -Wall -Wextra -Wpedantic -g -O1 -fsanitize=address,undefined test.c arena.c vec.c htablo.c -o test
./test
arena
vec
ht rastgele
ht kume
ht kelime
  235976 kelime, 4051 farkli 3-harfli onek; "pre" ile baslayan 3032 kelime
18/18 kontrol gecti
```

Bütün testler ASan ve UBSan altında, `-Wpedantic` uyarısız. Kelime testinde her sözlük kelimesi ilk üç harfine kısaltılıyor (üç harften kısa kelimeler olduğu gibi kalıyor), böylece aynı anahtar çok kez geliyor ve sayaç gerçekten sınanıyor: 235 976 kelime 4051 farklı anahtara düşüyor.

---

## 5. Ölçüm

```c
/* Tipe ozel yalin dogrusal sondalama (Ders 8.15): anahtar 0 = bos, ayni hash, ayni yuk siniri */
typedef struct { uint64_t a, d; } Yuva;
typedef struct { Yuva *y; size_t kap, adet; } Yalin;
static uint64_t mix(uint64_t x) { x ^= x >> 30; x *= 0xbf58476d1ce4e5b9ull; x ^= x >> 27; x *= 0x94d049bb133111ebull; return x ^ (x >> 31); }
static void yalin_koy(Yalin *t, uint64_t a, uint64_t d);
static void yalin_buyut(Yalin *t) {
    Yalin e = *t; t->kap = e.kap ? 2 * e.kap : 16; t->y = calloc(t->kap, sizeof(Yuva)); t->adet = 0;
    for (size_t i = 0; i < e.kap; i++) if (e.y[i].a) yalin_koy(t, e.y[i].a, e.y[i].d);
    free(e.y);
}
static void yalin_koy(Yalin *t, uint64_t a, uint64_t d) {
    if ((t->adet + 1) * 4 > t->kap * 3) yalin_buyut(t);
    size_t m = t->kap - 1, i = mix(a) & m;
    while (t->y[i].a && t->y[i].a != a) i = (i + 1) & m;
    if (!t->y[i].a) t->adet++;
    t->y[i].a = a; t->y[i].d = d;
}
static uint64_t *yalin_bul(Yalin *t, uint64_t a) {
    size_t m = t->kap - 1, i = mix(a) & m;
    while (t->y[i].a) { if (t->y[i].a == a) return &t->y[i].d; i = (i + 1) & m; }
    return NULL;
}

/* ... zincirleme tablo ve main'in geri kalani ... */

    HTablo *h = ht_olustur(8, 8, ht_hash_u64, ht_esit_u64);
    t0 = simdi(); for (size_t i = 0; i < n; i++) ht_koy(h, &a[i], &a[i]);
    t1 = simdi(); for (size_t i = 0; i < n; i++) s += *(uint64_t *)ht_bul(h, &q[i]);
    t2 = simdi(); for (size_t i = 0; i < n; i++) { uint64_t x = rnd() & ~1ull; s += ht_bul(h, &x) != NULL; }
    t3 = simdi();
    printf("u64, %zu anahtar   genel HTablo : koy %5.1f ns  bul %5.1f ns  bulma(yok) %5.1f ns\n", n, (t1 - t0) * 1e9 / n, (t2 - t1) * 1e9 / n, (t3 - t2) * 1e9 / n);
    ht_yok_et(h);
```

`bench.c` aynı 4 milyon rastgele 64 bitlik anahtarı üç tabloya ekleyip karışık sırayla arıyor: genel `HTablo`, aynı algoritmanın (aynı hash, aynı %75 sınırı, ikiye katlama) tipe özel, yalın hali (Ders 8.15'teki gibi 16 baytlık `{anahtar, değer}` yuvaları, anahtar 0 "boş"), ve düğümleri arenadan gelen bir zincirleme tablo (Ders 8.14). Ardından `VEC` ile 100 milyon `int` ekleme, önceden ayrılmış bir diziye yazmayla karşılaştırılıyor. Üç çalıştırma:

```
$ make bench
u64, 4000000 anahtar   genel HTablo : koy  63.8 ns  bul  27.1 ns  bulma(yok)  25.2 ns
                    tipe ozel    : koy  59.4 ns  bul  12.3 ns  bulma(yok)  36.1 ns
                    zincirleme   : koy  73.4 ns  bul  28.5 ns  bulma(yok)  34.1 ns
VEC, 100000000 int     vec_ekle 2.68 ns/eleman   duz dizi 0.68 ns/eleman   (0)
$ ./bench
u64, 4000000 anahtar   genel HTablo : koy  60.0 ns  bul  28.1 ns  bulma(yok)  26.7 ns
                    tipe ozel    : koy  63.0 ns  bul  12.3 ns  bulma(yok)  37.5 ns
                    zincirleme   : koy  54.2 ns  bul  22.7 ns  bulma(yok)  26.7 ns
VEC, 100000000 int     vec_ekle 2.24 ns/eleman   duz dizi 0.34 ns/eleman   (0)
$ ./bench
u64, 4000000 anahtar   genel HTablo : koy  63.3 ns  bul  30.3 ns  bulma(yok)  31.5 ns
                    tipe ozel    : koy  62.8 ns  bul  12.9 ns  bulma(yok)  37.0 ns
                    zincirleme   : koy  68.8 ns  bul  27.2 ns  bulma(yok)  30.6 ns
VEC, 100000000 int     vec_ekle 2.54 ns/eleman   duz dizi 0.93 ns/eleman   (0)
```

(Çalıştırmalar arası %10–20 oynama var; yorumlar tutarlı olan farklar üzerine.)

- **Genelliğin bedeli, başarılı aramada 2.2 kat**: genel tablo 27–30 ns, tipe özel 12–13 ns. Üç sebep: hash ve eşitlik dolaylı fonksiyon çağrıları (inline yok); bir arama üç ayrı diziye dokunuyor (kontrol, anahtar, değer), yani rastgele bir anahtar için üç cache kaçırması, tipe özel tabloda ise anahtar ve değer aynı 16 baytta, tek kaçırma; ve `memcpy` ile genel anahtar karşılaştırması. Ders 8.23'teki sıralama ölçümünün (2 kat) hash tablosundaki karşılığı.
- **Başarısız aramada genel tablo daha hızlı**: 25–31 ns'ye karşı 36–37 ns. Ayrı kontrol baytlarının kazancı: boş bir yuvaya ulaşana kadar taranan kısım yoğun bir bayt dizisi (64 yuva bir cache satırında); tipe özel tabloda aynı tarama 16 baytlık yuvalar üzerinden, 4 yuva bir satırda. Swiss Table'ın tasarımının özü bu.
- **Ekleme** üçünde de benzer (55–73 ns): baskın maliyet büyütmeler sırasında 4 milyon anahtarı defalarca yeniden dağıtmak ve yeni sayfalara ilk kez dokunmak.
- **Zincirleme** bu ölçümde genel tablo kadar iyi: düğümler arenadan, art arda ayrıldığı için Ders 8.14'teki `malloc`'lu sürümden daha iyi yerleşimli; ve başarısız arama kısa bir zincir.
- **`vec_ekle` eleman başına 2.2–2.7 ns**, önceden ayrılmış diziye yazmak 0.3–0.9 ns. Büyütmelerin kopyalaması (toplam yaklaşık $n$ eleman taşıma; Ders 4.24) bu farkın küçük bir kısmı: kapasiteyi baştan ayırmak `vec_ekle`'yi sadece 2.1–2.4 ns'ye indiriyor (Alıştırma 3). Asıl fark döngünün kendisi: düz dizi döngüsünü derleyici vektörleştirip bir komutta dört `int` yazıyor (Faz 11), `vec_ekle`'nin her elemandaki "yer var mı" dalı ve `adet` güncellemesi bunu engelliyor. Düz dizinin süresi de sayfalara ilk kez dokunmanın (Ders 7.27) maliyetine göre oynuyor.

Kararın sonucu: bu kütüphane genel amaçlı bir varsayılan olarak yeterince iyi (her ölçümde zincirlemeyle aynı sınıfta), ama bir programın sıcak noktasındaki bir tabloda, tipe özel bir sürüm başarılı aramaları iki kat hızlandırabiliyor. Ölçmeden hangisinin gerektiğini bilmek mümkün değil.

---

## 6. Faz 8'e dönüp bakış

| Yapı | Ders | Ne zaman |
| --- | --- | --- |
| Dinamik dizi | 4.24, 8.24 | Varsayılan konteyner; çoğu zaman en hızlısı |
| Bağlı liste | 8.2–8.3 | Ortadan $O(1)$ ekleme/silme, nesne birden çok listede (intrusive) |
| Yığın, kuyruk, deque | 8.4–8.5 | Gezinmeler, tamponlar; halka tampon |
| Dengeli ağaçlar (AVL, kırmızı-siyah) | 8.9–8.10 | Sıralı sözlük, aralık sorguları, en kötü durum garantisi |
| B-ağacı | 8.11 | Disk ve cache; veritabanları, dosya sistemleri |
| Heap | 8.12 | Öncelik kuyruğu, en iyi $k$, olay simülasyonu |
| Hash tablosu | 8.13–8.15, 8.24 | Sırasız sözlük, en hızlı tam eşleşme |
| Sembol tablosu | 8.16 | Kapsamlı isim çözümleme |
| Trie, radix | 8.17 | Önek sorguları, en uzun eşleşme, anahtar kelimeler |
| Union-find | 8.18 | Bağlantı, denklik sınıfları |
| CSR graf | 8.19 | Değişmeyen büyük graflar |
| Skip list | 8.20 | Eş zamanlı sıralı sözlük |
| Arena, havuz | 8.21 | Ömür grupları, sabit boyutlu nesneler |
| Kalıcı yapılar | 8.22 | Sürüm geçmişi, kilitsiz okuma, kapsamlar |

Fazın tekrar eden dersi iki parçalı. Asimptotik karmaşıklık neyin **mümkün** olduğunu söylüyor: bir hash tablosu sıralı gezinme veremez, bir bağlı liste $O(1)$ indeksleme veremez. Ama aynı karmaşıklık sınıfındaki yapılar arasındaki seçim neredeyse her zaman **bellek erişimine** bağlı: Ders 8.2'de aynı listenin bellekte sırayla ve karışık dizilmesi arasındaki 180 katlık fark, Ders 8.11'de B-ağacının kırmızı-siyahı 1.9 kat geçmesi, Ders 8.19'da CSR'nin bağlı listeyi 13 kat geçmesi, bu derste ayrı kontrol baytlarının başarısız aramayı hızlandırması. Ölçmek, tasarımın bir parçası.

---

## Alıştırmalar

**1** – Swiss Table'ın ikinci fikri: kontrol baytında sadece `DOLU` değil, anahtarın hash'inin 7 bitini de sakla (`0x80 | (h >> 57)` gibi; üst bit doluluk). Sondalama sırasında anahtar karşılaştırması sadece bu 7 bit eşleşince yapılıyor. String anahtarlı bir tabloda bu ne kazandırır? `uint64_t` anahtarlarda?

**2** – Kelime sayma testinde her kelime için önce `ht_bul`, yoksa `ht_koy` çağrılıyor: yeni bir kelime için hash iki kez hesaplanıyor ve tablo iki kez aranıyor. `void *ht_bul_ya_da_ekle(HTablo *t, const void *anahtar, bool *yeni)` fonksiyonunu tasarla: anahtar varsa değerinin adresini, yoksa yeni bir yuva açıp onun (henüz doldurulmamış) değer adresini döndürsün. Bu arayüzün bir tehlikesi var mı?

**3** – `VEC` için `vec_ayir(v, n)` makrosu ekle: kapasiteyi en az `n` yap (eleman ekleme). 100 milyon elemanı bununla önceden ayırıp sonra `vec_ekle` ile doldurmak ne kadar sürer? Dalın maliyeti tamamen kaybolur mu?

**4** – `ht_sonraki` ile tabloyu gezerken `ht_koy` çağırmak neden tehlikeli? Hata ayıklama derlemelerinde bunu yakalayan bir mekanizma tasarla (ipucu: tabloda bir "değişiklik sayacı").

**5** – Kütüphaneye Ders 8.22'deki gibi kalıcı bir sözlük ya da Ders 8.10'daki gibi sıralı bir sözlük eklemek istesen, Ders 8.23'teki üç yaklaşımdan hangisini seçerdin? Bu kütüphanenin arenasıyla nasıl birlikte çalışır?

<details>
<summary>Cevaplar</summary>

**1** – Kontrol baytı `BOS`, `MEZAR` ya da `DOLU + 7 bit hash` olur. Aranan anahtarın 7 bitlik parçasıyla eşleşmeyen dolu yuvalar **karşılaştırılmadan** geçiliyor; rastgele bir dolu yuvanın yanlışlıkla eşleşme olasılığı $1/128$. String anahtarlarda kazanç büyük: her gereksiz `strcmp` (bir fonksiyon çağrısı ve stringin belleğine bir erişim, muhtemelen bir cache kaçırması) neredeyse tamamen ortadan kalkıyor. Ders 8.14'teki "saklanan hash ile önce ucuz karşılaştırma" fikrinin bayt düzeyinde hali. `uint64_t` anahtarlarda kazanç küçük: eşitlik zaten tek bir karşılaştırma, ama `esit` fonksiyon çağrısı ve anahtar dizisine erişim yine de kalkıyor. Swiss Table bir adım daha atıyor: 16 kontrol baytını tek bir SIMD komutuyla aranan 7 bitle karşılaştırıp eşleşenlerin bit maskesini çıkarıyor (Faz 11).

**2** – `ht_koy`'un içi zaten bunu yapıyor: `ara` ile bak, yoksa büyütmeyi kontrol et, ilk boş yuvayı bul. Fark, değeri kopyalamak yerine yuvanın değer adresini döndürmek ve `*yeni = true` demek; çağıran değeri kendisi yazıyor (`if (yeni) *n = 0; (*n)++;`). Hash bir kez hesaplanıyor. Tehlike: yeni bir yuvanın değeri **başlatılmamış**; çağıran yazmayı unutursa tabloda çöp bir değer kalıyor. Bir de, döndürülen adres bir sonraki `ht_koy`'a kadar geçerli; bir kelime için adres alınıp, değer yazılmadan başka bir kelime eklenirse büyütme ilk adresi geçersiz kılabilir. C++'ın `std::unordered_map::operator[]`'ı ve Rust'ın `entry` API'si bu desenin güvenli halleri.

**3** – `#define vec_ayir(v, n) ((n) <= (v)->kap || vec__buyut((void **)&(v)->veri, &(v)->kap, sizeof *(v)->veri, (n)))`. Üç çalıştırmada ölçüm (aynı program içinde, ns/eleman):

```
vec_ekle 2.36  vec_ayir+vec_ekle 2.40  duz dizi 0.92 ns/eleman
vec_ekle 2.47  vec_ayir+vec_ekle 2.16  duz dizi 0.08 ns/eleman
vec_ekle 2.47  vec_ayir+vec_ekle 2.08  duz dizi 0.06 ns/eleman
```

Önceden ayırmak neredeyse hiçbir şey kazandırmıyor: büyütmeler zaten amortize $O(1)$ ve ucuz. Dal her zaman aynı yöne gittiği için tahminci onu mükemmel tahmin ediyor (Ders 7.22), ama döngü yine eleman başına bir karşılaştırma, bir saklama ve `adet`'in güncellenmesi; derleyici bu döngüyü vektörleştiremiyor. Düz dizinin ilk turdaki 0.92 ns'si sayfa hataları: 400 MB'lık yeni bir blokta her 16 KB'lık sayfaya ilk dokunuş (Ders 7.27); sonraki turlarda `malloc` serbest bırakılmış aynı sayfaları geri verdiği için 0.06–0.08 ns, yani saf vektörleştirilmiş yazma. Tam hız için `vec_ayir`'dan sonra diziyi doğrudan doldurup (`v.veri[i] = ...`) `v.adet`'i sonda tek seferde ayarlamak gerekiyor.

**4** – `ht_koy` büyütme tetiklerse bütün yuvalar yeni dizilere taşınıyor; `ht_sonraki`'nin `konum`'u artık bambaşka bir dizinin indeksi: bazı girdiler iki kez, bazıları hiç görülmüyor; ve gezinme sırasında alınmış `anahtar`/`deger` pointer'ları serbest bırakılmış belleği gösteriyor (ASan `heap-use-after-free` yakalar). Büyütme olmasa bile yeni girdi gezilmiş bir bölgeye ya da gezilecek bir bölgeye düşebilir. Mekanizma: `HTablo`'ya bir `degisiklik` sayacı ekle, her `ht_koy` ve `ht_sil` onu artırsın. Gezinme başlarken sayacı bir yerde sakla (konum değişkenine gömmek ya da ayrı bir `HtGezgin` struct'ı ile), her `ht_sonraki` çağrısında karşılaştır; farklıysa `assert` ile dur. Java'nın koleksiyonlarındaki `ConcurrentModificationException` bu mekanizma.

**5** – Sıralı sözlük (kırmızı-siyah ağaç) için **intrusive** yaklaşım (Ders 8.23, Linux `rbtree`): düğüm bağlantısı kullanıcının struct'ında, düğümler kullanıcının arenasından ya da Ders 8.21'deki havuzdan geliyor, arama döngüsü tipli ve inline. Kütüphane dengeleme kodunu bir kez içeriyor. Kalıcı sözlük için düğümleri kütüphanenin kendisinin ayırması gerekiyor (yol kopyalama yeni düğümler yaratıyor), dolayısıyla `void *` ya da makro şablon; ve bellek kullanıcının verdiği bir **arenadan**: `KalSozluk *ks_olustur(Arena *a, ...)`. Bütün sürümler arenanın ömrü boyunca yaşıyor, arena yok edilince hepsi gidiyor (Ders 8.22, Bölüm 4). Arenayı parametre olarak almak, kütüphanenin bellek politikasını kullanıcıya bırakmanın genel yolu; Zig'in standart kütüphanesi bunu bütün konteynerlerde zorunlu kılıyor.

</details>

---

## Kaynaklar

- Matt Kulukundis, "Designing a Fast, Efficient, Cache-friendly Hash Table, Step by Step", CppCon 2017; Abseil `flat_hash_map` belgeleri.
- Sean Barrett, *stb_ds.h*: tek başlıklı C konteyner kütüphanesi.
- Brian Kernighan ve Rob Pike, *The Practice of Programming*, Bölüm 4 (arayüzler) ve Bölüm 6 (test).
- Sebastiano Vigna, "splitmix64" (`xorshift.di.unimi.it`): 64 bitlik son karıştırıcı.
- David Hanson, *C Interfaces and Implementations*, Addison-Wesley, 1996: C'de arayüz tasarımı, arena (`Arena`), tablo (`Table`) ve dinamik dizi (`Seq`) modülleri.

**Sıradaki ders:** Faz 9'a geçiyoruz: doğruluk ve analiz. Döngü değişmezi ile ispat, en iyi, ortalama ve en kötü durum, deneysel ölçüm.
