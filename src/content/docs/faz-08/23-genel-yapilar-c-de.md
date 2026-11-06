---
title: "8.23 Genel (generic) yapılar C'de"
description: "Aynı veri yapısını her tip için yeniden yazmamanın üç yolu: void* ve eleman boyutu ile çalışma anında genellik (qsort tarzı), makrolarla her tip için ayrı kod üreten derleme anında şablonlar, ve verinin değil bağlantının genel olduğu intrusive yapılar; aynı hızlı sıralamanın iki hali 10 milyon int'te 1.21 s'ye karşı 0.60 s, libc qsort 1.00 s, bayt bayt takasın bedeli; bir nesneyi aynı anda iki ağaçta tutan, malloc'suz intrusive ağaç ve Linux'un 'aramayı kullanıcı yazar' tasarımı; C11 _Generic; tip güvenliği, kod şişmesi, hata mesajları ve hata ayıklama açısından karşılaştırma."
---

Bu fazda yazdığımız her yapı tek bir tipe bağlıydı. Ders 8.4'teki yığın `long` tutuyordu, Ders 8.8'deki BST `int`, Ders 8.14'teki hash tablosu string'den `long`'a. Gerçek bir programda aynı yapıya onlarca farklı tiple ihtiyaç var: bir derleyicide token'ların dinamik dizisi, AST düğümlerinin dinamik dizisi, sembollerin dinamik dizisi... Her biri için `token_dizi_ekle`, `dugum_dizi_ekle`, `sembol_dizi_ekle` yazmak hem zahmetli hem hata kaynağı: bir hatayı birinde düzeltip ötekilerde unutmak.

C++'ın şablonları (`std::vector<T>`), Rust'ın ve Java'nın generic'leri bu sorunu dil düzeyinde çözüyor. C'de böyle bir mekanizma yok. Ama üç yerleşik araç var ve her biri farklı bir takas sunuyor: **`void *`**, **makrolar** ve **intrusive yapılar**. Bu ders üçünü aynı problem üzerinde karşılaştırıyor; Ders 8.24'teki faz projesinde hangisini nerede kullanacağımıza burada karar veriyoruz.

---

## 1. `void *`: çalışma anında genellik

Ders 4.9'da `void *`'ı "herhangi bir şeyin adresi" olarak tanıdık, Ders 4.11'de `qsort`'un karşılaştırma fonksiyonunu gördük. Standart kütüphanenin genel algoritmaları (`qsort`, `bsearch`) bu yolu izliyor: veri bir `void *` ve bir **eleman boyutu**; tipe özgü işlemler (karşılaştırma) bir **fonksiyon pointer'ı**.

Aynı hızlı sıralamayı (Lomuto bölmesi, küçük parçalarda ekleme sıralaması; Ders 9.5'te ayrıntılı) bu yolla yazalım:

```c
/* 1) void* surumu: eleman boyutu ve karsilastirma calisma aninda */
static void takas_bayt(char *a, char *b, size_t boyut) {
    while (boyut--) { char t = *a; *a++ = *b; *b++ = t; }
}
static void vsirala(void *taban, size_t n, size_t boyut, int (*kars)(const void *, const void *)) {
    char *a = taban;
    while (n > 16) {
        char *pivot = a + (n / 2) * boyut;
        takas_bayt(pivot, a + (n - 1) * boyut, boyut);           /* pivotu sona al */
        pivot = a + (n - 1) * boyut;
        size_t s = 0;
        for (size_t i = 0; i + 1 < n; i++)
            if (kars(a + i * boyut, pivot) < 0) takas_bayt(a + i * boyut, a + s++ * boyut, boyut);
        takas_bayt(a + s * boyut, pivot, boyut);                  /* Lomuto bolmesi (Ders 9.5) */
        vsirala(a, s, boyut, kars);                               /* sol tarafa ozyinele... */
        a += (s + 1) * boyut; n -= s + 1;                         /* ...sag tarafta dongude devam */
    }
    for (size_t i = 1; i < n; i++)                                 /* kucuk parcalar: ekleme siralamasi */
        for (size_t j = i; j > 0 && kars(a + (j - 1) * boyut, a + j * boyut) > 0; j--)
            takas_bayt(a + (j - 1) * boyut, a + j * boyut, boyut);
}
```

Eleman adresleri elle hesaplanıyor (`a + i * boyut`; `void *` üzerinde aritmetik yapılamadığı için `char *`, Ders 4.9), ve iki elemanın yerini değiştirmek bir bayt döngüsü, çünkü elemanın tipi bilinmiyor. Kullanmak için tipe özgü bir karşılaştırma fonksiyonu:

```c
static int int_kars(const void *x, const void *y) { int a = *(const int *)x, b = *(const int *)y; return (a > b) - (a < b); }
```

(`return a - b;` yazmak taşma yüzünden yanlış: `INT_MIN - 1`. `(a > b) - (a < b)` her zaman -1, 0 ya da 1; Ders 3.8.)

**Artıları**: kod bir kez derleniyor, bir kez yer kaplıyor; tip yeni bir modülde, kütüphane yeniden derlenmeden kullanılabiliyor (`qsort` libc'de hazır); sıralanacak tip çalışma anında bile seçilebiliyor.

**Eksileri**: her karşılaştırma bir **dolaylı fonksiyon çağrısı**; derleyici karşılaştırmayı sıralama döngüsünün içine yerleştiremiyor (inline). Takas tipin boyutunu derleme anında bilmiyor. Ve **tip güvenliği yok**: `vsirala(int_dizisi, n, sizeof(int), kisi_kars)` derleniyor ve sessizce yanlış çalışıyor (Alıştırma 3).

---

## 2. Makrolar: derleme anında şablon

İkinci yol, aynı kodu her tip için **önişlemciye yazdırmak** (Ders 2.11'deki `#define`, burada çok satırlı halde). Bir makro, tipi ve karşılaştırmayı parametre alıp tam, tipli bir fonksiyon üretiyor:

```c
/* 2) Makro surumu: her tip icin ayri, tipli bir fonksiyon uretiliyor */
#define SIRALA_TANIMLA(T, AD, KUCUK)                                              \
    static void AD(T *a, size_t n) {                                               \
        while (n > 16) {                                                           \
            T t = a[n / 2]; a[n / 2] = a[n - 1]; a[n - 1] = t;                     \
            T pivot = a[n - 1]; size_t s = 0;                                      \
            for (size_t i = 0; i + 1 < n; i++)                                     \
                if (KUCUK(a[i], pivot)) { t = a[i]; a[i] = a[s]; a[s++] = t; }     \
            a[n - 1] = a[s]; a[s] = pivot;                                         \
            AD(a, s);                                                              \
            a += s + 1; n -= s + 1;                                                \
        }                                                                          \
        for (size_t i = 1; i < n; i++)                                             \
            for (size_t j = i; j > 0 && KUCUK(a[j], a[j - 1]); j--) {              \
                T t = a[j]; a[j] = a[j - 1]; a[j - 1] = t; }                       \
    }

#define INT_KUCUK(x, y) ((x) < (y))
SIRALA_TANIMLA(int, sirala_int, INT_KUCUK)

typedef struct { char ad[12]; int yas; } Kisi;
#define KISI_KUCUK(x, y) ((x).yas < (y).yas)
SIRALA_TANIMLA(Kisi, sirala_kisi, KISI_KUCUK)
```

`SIRALA_TANIMLA(int, sirala_int, INT_KUCUK)` satırı önişlemciden sonra `static void sirala_int(int *a, size_t n) { ... }` oluyor: bütün `T`'ler `int`, bütün `KUCUK(x, y)`'ler `((x) < (y))`. Takas düz bir atama, karşılaştırma tek bir komut. `sirala_kisi(k, 4)` de ayrı bir fonksiyon:

```
Can(19) Mehmet(25) Ayse(31) Zeynep(42) 
```

Bu, C++ şablonlarının yaptığı şeyin elle yapılmış hali. stb_ds, klib (`khash.h`, `kvec.h`) ve BSD'nin `sys/tree.h`'si gibi yaygın C kütüphaneleri bu teknikle yazılmış.

**Artıları**: tam hız (her şey inline); tip güvenliği (`sirala_int`'e bir `Kisi *` verirsen derleme hatası).

**Eksileri**: her tip için ayrı bir kopya (**kod şişmesi**); hata mesajları makronun açıldığı satırı gösteriyor ve okunması zor; hata ayıklayıcıda makro içine adım adım girilemiyor (bütün fonksiyon tek bir kaynak satırı); makro parametreleri birden fazla kez değerlendirilebiliyor ve isim çakışmaları olabiliyor (Alıştırma 2).

### Ölçüm

10 milyon rastgele `int` ve 2 milyon `Kisi` (16 bayt), üç sıralamayla (aynı girdi, her seferinde yeniden kopyalanıyor; sonuçların sıralı olduğu kontrol ediliyor):

```
$ cc -std=c11 -O2 -Wall -Wextra siralama.c -o siralama && ./siralama
Can(19) Mehmet(25) Ayse(31) Zeynep(42) 
int  void*+fonksiyon  1.206 s
int  makro            0.596 s
int  libc qsort       0.997 s
Kisi void*+fonksiyon  0.294 s
Kisi makro            0.101 s
Kisi libc qsort       0.138 s
```

İkinci çalıştırma neredeyse aynı (1.224, 0.599, 1.000; 0.283, 0.101, 0.138); sanitizer'lı derleme temiz.

- **Aynı algoritma, iki genellik yöntemi**: makro sürümü `int`'te **2 kat**, `Kisi`'de **2.9 kat** hızlı. Fark tamamen genelliğin bedeli: dolaylı karşılaştırma çağrısı ve bayt bayt takas.
- **libc `qsort`** bizim `void *` sürümümüzden hızlı, ama makronun yine gerisinde. `qsort` da her karşılaştırma için bizim fonksiyonumuzu çağırmak zorunda; ama takası akıllıca yapıyor (Alıştırma 1).
- C++'ın `std::sort`'u, `qsort`'tan genelde 2–3 kat hızlı olmasıyla bilinir: tam bu farkın kaynağı, şablonların karşılaştırmayı inline etmesi.

---

## 3. Intrusive: bağlantı genel, veri değil

Ders 8.3'teki Linux `list_head`'i üçüncü bir yol gösteriyordu. Ne veriyi `void *`'a çeviriyoruz ne de her tip için kod üretiyoruz: kütüphane sadece **bağlantıyı** (iki pointer'lık küçük bir struct) biliyor, ve bu bağlantı kullanıcının kendi struct'ının **içinde** duruyor. Bağlantıdan nesneye `container_of` ile dönülüyor.

Bir ağaç için:

```c
/* Intrusive: kutuphane sadece baglanti dugumunu bilir; veri kullanicinin struct'inda, baglanti onun icinde. */
#include <stddef.h>
#include <stdio.h>

/* --- kutuphane: tip bilmeyen ikili agac baglantisi --- */
typedef struct Bag { struct Bag *sol, *sag; } Bag;
#define container_of(p, T, alan) ((T *)((char *)(p) - offsetof(T, alan)))   /* Ders 8.3 */

/* Kutuphane karsilastirmayi bilmiyor. Linux rbtree'deki gibi: aramayi KULLANICI yazar,
   kutuphane sadece "bu yere bagla" der. (Burada denge yok; rb_insert_color'in yeri.) */
static void bag_as(Bag *yeni, Bag **yer) { yeni->sol = yeni->sag = NULL; *yer = yeni; }

static void bag_icek(const Bag *b, void (*f)(const Bag *)) { if (!b) return; bag_icek(b->sol, f); f(b); bag_icek(b->sag, f); }

/* --- kullanici --- */
typedef struct {
    char ad[12];
    int yas;
    Bag yas_agaci;            /* yasa gore agacta bu baglanti */
    Bag ad_agaci;             /* ada gore BASKA bir agacta bu baglanti: ayni nesne iki yapida */
} Kisi;

static int ad_kars(const char *a, const char *b) { while (*a && *a == *b) { a++; b++; } return (unsigned char)*a - (unsigned char)*b; }

static void yasa_gore_ekle(Bag **kok, Kisi *k) {
    Bag **p = kok;
    while (*p) p = k->yas < container_of(*p, Kisi, yas_agaci)->yas ? &(*p)->sol : &(*p)->sag;   /* tipli karsilastirma: inline */
    bag_as(&k->yas_agaci, p);
}
static void ada_gore_ekle(Bag **kok, Kisi *k) {
    Bag **p = kok;
    while (*p) p = ad_kars(k->ad, container_of(*p, Kisi, ad_agaci)->ad) < 0 ? &(*p)->sol : &(*p)->sag;
    bag_as(&k->ad_agaci, p);
}
static void yaz_yas(const Bag *b) { const Kisi *k = container_of(b, Kisi, yas_agaci); printf(" %s(%d)", k->ad, k->yas); }
static void yaz_ad(const Bag *b)  { const Kisi *k = container_of(b, Kisi, ad_agaci);  printf(" %s(%d)", k->ad, k->yas); }

int main(void) {
    Kisi kisiler[] = { { .ad = "Ayse", .yas = 31 }, { .ad = "Mehmet", .yas = 25 }, { .ad = "Zeynep", .yas = 42 },
                       { .ad = "Can", .yas = 19 }, { .ad = "Deniz", .yas = 31 } };    /* malloc yok: nesneler dizide */
    Bag *yas_kok = NULL, *ad_kok = NULL;
    for (int i = 0; i < 5; i++) { yasa_gore_ekle(&yas_kok, &kisiler[i]); ada_gore_ekle(&ad_kok, &kisiler[i]); }
    printf("yasa gore:"); bag_icek(yas_kok, yaz_yas); printf("\n");
    printf("ada gore: "); bag_icek(ad_kok, yaz_ad); printf("\n");
    printf("sizeof(Kisi) = %zu, offsetof yas_agaci = %zu, ad_agaci = %zu\n", sizeof(Kisi), offsetof(Kisi, yas_agaci), offsetof(Kisi, ad_agaci));
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined intrusive.c -o intrusive && ./intrusive
yasa gore: Can(19) Mehmet(25) Ayse(31) Deniz(31) Zeynep(42)
ada gore:  Ayse(31) Can(19) Deniz(31) Mehmet(25) Zeynep(42)
sizeof(Kisi) = 48, offsetof yas_agaci = 16, ad_agaci = 32
```

Beş kişi, iki ağaç, sıfır `malloc`. Her `Kisi` iki bağlantı taşıyor ve **aynı anda** iki ağaçta, iki farklı sırayla. `void *` yaklaşımında bir nesneyi iki yapıya koymak için ya nesneyi kopyalamak ya da her yapıda nesneye bir pointer tutan ayrı bir düğüm ayırmak gerekirdi.

Karşılaştırma sorununu Linux'un kırmızı-siyah ağacı (`include/linux/rbtree.h`) ilginç bir şekilde çözüyor: kütüphane karşılaştırmayı hiç bilmiyor. **Arama döngüsünü kullanıcı yazıyor** (yukarıdaki `yasa_gore_ekle`'nin `while`'ı), kütüphane sadece "bu düğümü bu yere bağla" (`rb_link_node`) ve "şimdi dengele" (`rb_insert_color`; Ders 8.10'daki `ekleme_duzelt`) fonksiyonlarını veriyor. Karşılaştırma kullanıcının kodunda, tipli ve inline; dengeleme kütüphanede, bir kez. Hem makronun hızını hem `void *`'ın tek kopya kodunu alıyor.

**Artıları**: nesne başına ek `malloc` yok; bir nesne birden çok yapıda; yapı nesnenin ömrünü yönetmiyor (nesneler bir dizide, bir arenada ya da yığında olabilir); hız.

**Eksileri**: nesnenin tipi, hangi yapılarda olacağını **önceden** bilmeli (bağlantı alanları struct'ta); `container_of` yanlış alan adıyla kullanılırsa derleyici uyarmıyor ve sonuç çöp (Ders 8.3, Alıştırma 5); nesneyi serbest bırakmadan önce bütün yapılardan çıkarmak kullanıcının işi.

---

## 4. `_Generic`

C11'in `_Generic` ifadesi, bir ifadenin **tipine göre** derleme anında bir seçim yapıyor:

```c
/* C11 _Generic: derleme aninda tipe gore fonksiyon secmek */
#include <stdio.h>
static void yaz_int(int x) { printf("int %d\n", x); }
static void yaz_double(double x) { printf("double %g\n", x); }
static void yaz_str(const char *s) { printf("string \"%s\"\n", s); }
#define YAZ(x) _Generic((x), int: yaz_int, double: yaz_double, char *: yaz_str, const char *: yaz_str)(x)
int main(void) { YAZ(42); YAZ(3.5); YAZ("merhaba"); }
```

```
int 42
double 3.5
string "merhaba"
```

Bu bir genel veri yapısı mekanizması değil, bir **aşırı yükleme** (overloading) mekanizması: önceden yazılmış fonksiyonlar arasında tipe göre seçim. `<tgmath.h>`'nin `sqrt`'u `float`, `double` ve `long double` için böyle seçiliyor. Makro şablonlarla birlikte kullanılınca işe yarıyor: `VEC_EKLE(v, x)` yazınca `v`'nin tipine göre doğru `vec_int_ekle` ya da `vec_kisi_ekle` çağrılabiliyor. Ama her tip için hâlâ bir satır yazmak gerekiyor; listede olmayan bir tip derleme hatası.

---

## 5. Karşılaştırma

| | `void *` + fonksiyon | Makro şablon | Intrusive |
| --- | --- | --- | --- |
| Hız | Dolaylı çağrı, inline yok | En hızlı | Hızlı (arama kullanıcıda, tipli) |
| Tip güvenliği | Yok | Var | Kısmen (`container_of` denetlenmiyor) |
| Kod boyutu | Tek kopya | Tip başına kopya | Tek kopya (bağlantı işlemleri) |
| Hata mesajı, hata ayıklama | İyi | Kötü (makro açılımı) | İyi |
| Nesne başına `malloc` | Genelde var (düğüm) | Yapıya bağlı | Yok |
| Nesne birden çok yapıda | Pointer'larla, ek düğümle | Pointer'larla | Doğrudan |
| Örnekler | `qsort`, `bsearch`, GLib | stb_ds, klib, BSD `tree.h` | Linux `list.h`, `rbtree.h` |

Pratik kural:

- **Kapsayıcı dizi ve hash tablosu** gibi elemanları **değerle** tutan yapılar için makro (ya da sık kullanılan birkaç tip için elle yazılmış sürümler): elemanlar yan yana durmalı ve eleman boyutu derleme anında bilinmeli ki dizi indeksleme hızlı olsun.
- **Bağlı yapılar** (listeler, ağaçlar) için intrusive: düğüm ayırmayı ortadan kaldırıyor ve nesnenin birden çok yapıda olmasına izin veriyor.
- **Seyrek kullanılan, hızın kritik olmadığı** genel algoritmalar için `void *`: `qsort`'u bir yapılandırma dosyasındaki 50 satırı sıralamak için kullanmak sorun değil.

Ders 8.24'teki kütüphane bu kuralı izleyecek: dinamik dizi bir makro şablon, hash tablosu genel ama anahtar ve değer boyutları çalışma anında verilen bir `void *` tasarımı (bu kez bilerek, ölçüp karşılaştırmak için), bellek bir arenadan.

---

## Alıştırmalar

**1** – `vsirala`'nın `takas_bayt`'ı her takası bayt bayt yapıyor. Eleman boyutu 4 ise tek bir 32 bitlik, 8'in katıysa 64 bitlik parçalarla takas eden bir sürüm yaz (`memcpy` ile, hizalama varsayımı yapmadan). Süre ne kadar değişir? Takası `char t[64]; memcpy(t, a, boyut); ...` ile yapmak neden **daha yavaş** olabilir?

**2** – `SIRALA_TANIMLA` makrosunda iki gizli tuzak var. (a) `KUCUK` makrosuna yan etkili bir ifade verilirse ne olur? (b) Makronun içinde `t` diye bir değişken var; kullanıcının `KUCUK` makrosu da `t` adında bir şeye başvuruyorsa ne olur? Her birinin çaresi ne?

**3** – `vsirala(int_dizisi, n, sizeof(int), kisi_kars)` derleniyor mu? Çalıştırınca ne olur? Aynı hatayı makro sürümünde yapmak (`sirala_kisi(int_dizisi, n)`) mümkün mü?

**4** – Bölüm 3'teki intrusive ağaçlarda, `kisiler[2]` (Zeynep) programın ortasında silinecekse ne yapmak gerekir? `kisiler` dizisi yığında; `main` dönünce iki ağacın kökleri ne gösterir? Bunu, bir `void *` tabanlı ağaçla karşılaştır.

**5** – Bir derleyicide şu yapılar gerekiyor: tokenların dinamik dizisi (milyonlarca, sırayla eklenip sırayla okunuyor), her fonksiyonun AST düğümleri arasında ebeveyn-çocuk listeleri, isimden sembole bir hash tablosu, ve bir temel bloktan ardıllarına kenarlar. Her biri için hangi genellik yaklaşımını seçerdin, neden?

<details>
<summary>Cevaplar</summary>

**1** –

```c
static void takas_bayt(char *a, char *b, size_t boyut) {
    if (boyut == 4) { uint32_t t; memcpy(&t, a, 4); memcpy(a, b, 4); memcpy(b, &t, 4); return; }   /* sabit boyut: tek yukleme */
    if (boyut % 8 == 0) { for (size_t i = 0; i < boyut; i += 8) { uint64_t t; memcpy(&t, a + i, 8); memcpy(a + i, b + i, 8); memcpy(b + i, &t, 8); } return; }
    while (boyut--) { char t = *a; *a++ = *b; *b++ = t; }
}
```

```
int  void*+fonksiyon  1.011 s
Kisi void*+fonksiyon  0.174 s
```

`int`'te 1.21 s'den 1.01 s'ye (libc `qsort` ile aynı), 16 baytlık `Kisi`'de 0.29 s'den 0.17 s'ye. Sabit boyutlu `memcpy` (4 ya da 8) derleyici tarafından tek bir yükleme ve tek bir saklama komutuna çevriliyor (Ders 4.18); hizalama varsayımı yapmadığı için güvenli. Makro sürümüyle (0.60 s, 0.10 s) aradaki kalan fark artık sadece dolaylı karşılaştırma çağrısı. `char t[64]` ile değişken boyutlu `memcpy` ise bu makinede **daha yavaş** ölçüldü (`int` için 2.69 s): boyut derleme anında bilinmediği için derleyici gerçek bir `memcpy` fonksiyon çağrısı üretiyor ve her takas üç fonksiyon çağrısı oluyor. libc `qsort`'u da benzer şekilde, eleman boyutuna göre sözcük sözcük takas yapan özel yollar içeriyor.

**2** – (a) `KUCUK(a[i++], pivot)` gibi bir ifade, makronun içinde `KUCUK(x, y)`'nin `x`'i kaç kez kullandığına göre birden çok kez değerlendirilir; burada `KUCUK` bir kez açılıyor ama kullanıcının makrosu `((x) < (y) || (x) == ...)` gibi `x`'i iki kez kullanırsa `i` iki kez artar. Çare: şablon parametresini bir **fonksiyon** yapmak (`static inline bool kisi_kucuk(Kisi a, Kisi b)`): derleyici onu yine inline eder, ama argümanlar bir kez değerlendirilir. (b) Kullanıcının `KUCUK` makrosu `t`'ye başvuruyorsa, açıldığı yerde makronun yerel `t`'si onu **gölgeler** (Ders 8.16) ve yanlış değişkeni kullanır. Çare: makro içindeki yerel adlara çakışması zor önekler vermek (`sirala__t`) ya da `AD`'yi ön ek olarak kullanmak (`AD##_t`, `##` önişlemci yapıştırma işleci). Bu, Faz 18'deki **hijyenik makro** probleminin C'deki hali.

**3** – Derleniyor: `vsirala`'nın imzası `int (*)(const void *, const void *)` istiyor ve `kisi_kars`'ın tipi tam olarak bu. Çalışınca `kisi_kars`, iki `int`'in adresini `Kisi *` sanıp `->yas` alanını (ofset 12) okuyor: dizinin 12 bayt ötesindeki rastgele `int`'ler karşılaştırılıyor, sonuç sıralı değil, ve dizinin sonunda dizi sınırının dışı okunuyor; ASan bunu `heap-buffer-overflow` olarak yakalıyor. Makro sürümünde `sirala_kisi(int_dizisi, n)` derleme hatası verir: `sirala_kisi`'nin parametresi `Kisi *` ve `int *` ondan farklı bir tip. Tip güvenliği bu.

**4** – Zeynep'i silmek için onu **iki** ağaçtan da çıkarmak gerekir: yaş ağacından ve ad ağacından, her birinde Ders 8.8'deki silme ile (intrusive bir ağaçta bu, düğümün `Bag` alanının adresini kullanarak). Birinden çıkarıp ötekinde bırakmak, dizinin o elemanı yeniden kullanılınca ötekinde bozuk bir düğüm demek. `main` dönünce `kisiler` dizisi yok oluyor ve kökler artık **geçersiz** yığın adreslerini gösteriyor; ağaçlar `main`'in yerel değişkenleri olduğu için sorun yok, ama kökler global olsaydı sallanan pointer olurdu. Ağaç nesnelerin ömrünü **yönetmiyor**; intrusive tasarımın hem gücü hem tehlikesi. `void *` tabanlı bir ağaç ise kendi düğümlerini `malloc` edip nesnelere pointer tutuyor: silme sadece ağacın düğümünü bırakıyor, nesne yaşamaya devam ediyor; nesneyi önce `free` edip ağaçtan çıkarmayı unutursan ağaç sallanan bir `void *` tutuyor. Sorun ortadan kalkmıyor, sadece yer değiştiriyor.

**5** – **Tokenlar**: değerle tutulan, çok sayıda, sıralı erişilen elemanlar; makro şablon dinamik dizi (`VEC(Token)`): yan yana, tipli, hızlı. **AST ebeveyn-çocuk listeleri**: düğümler zaten arenada (Ders 8.21) ve her düğüm birden çok listede olabilir (çocuklar listesi, bir kapsamdaki tanımlar listesi); intrusive liste. **Sembol tablosu**: anahtar intern edilmiş pointer, değer `Sembol *` (Ders 8.16); tek tip, elle yazılmış ya da makro üretilmiş bir hash tablosu; çalışma anında genellik gereksiz. **Temel blok kenarları**: blok başına küçük, değişen listeler; blok struct'ının içinde makro şablon dinamik diziler (`VEC(Blok *) ardillar, onculler;`). LLVM'in seçimleri de benzer: `SmallVector<T, N>` (şablon dizi), intrusive `ilist` (komutlar ve bloklar), `DenseMap` (şablon hash tablosu).

</details>

---

## Kaynaklar

- ISO/IEC 9899:2011 (C11), §6.5.1.1: `_Generic` seçimi; §7.25: `<tgmath.h>`.
- Linux çekirdeği, `include/linux/rbtree.h` ve `Documentation/core-api/rbtree.rst`: "aramayı kullanıcı yazar" tasarımı.
- Sean Barrett, *stb_ds.h*: makro tabanlı dinamik dizi ve hash tablosu.
- Attractive Chaos, *klib* (`khash.h`, `kvec.h`, `ksort.h`): makro şablonlu C kütüphanesi ve `qsort` karşılaştırmaları.
- OpenBSD, `sys/sys/tree.h`: makrolarla üretilen kırmızı-siyah ve splay ağaçları.
- Jon Bentley ve M. Douglas McIlroy, "Engineering a Sort Function", *Software: Practice and Experience* 23(11), 1993: `qsort`'un takas ve pivot iyileştirmeleri.

**Sıradaki ders:** Faz projesi. Genel hash tablosu, dinamik dizi ve arena içeren mini konteyner kütüphanesi; testler ve benchmark.
