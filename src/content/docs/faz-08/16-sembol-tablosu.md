---
title: "8.16 Sembol tablosu"
description: "Derleyicinin isimleri tanımlarına bağladığı yapı: iç içe kapsamlar, gölgeleme, tanımsız ve tekrar tanımlanmış isim hataları; string interning ile her ismin tek kopyası ve strcmp yerine pointer eşitliği; tek bir hash tablosunda her kovanın bir yığın olduğu, kapsam kapanınca sembollerin kova tepesinden O(1)'de söküldüğü tasarım; küçük bir dilin isim çözümlemesi; kapsam başına ayrı tablo ile karşılaştırma: 200 kapsam derinlikte 125 ns'ye karşı 1.2 ns."
---

`x = y + 1;` satırını derleyen bir derleyici, `x` ve `y`'nin **ne** olduğunu bilmek zorunda: hangi tanıma işaret ediyorlar, tipleri ne, bellekte nerede duruyorlar? Bu soruyu cevaplayan yapı **sembol tablosu**. Derleyicinin her aşaması ona başvuruyor: ayrıştırıcı (bir ismin tip adı mı değişken mi olduğu C'de ayrıştırmayı etkiler), tip denetleyici, kod üretici. Faz 15–16'daki derleyicinin merkezinde bu dersteki yapı olacak.

Sembol tablosu bir sözlük (Ders 8.14): isimden bilgiye. Ama iki özelliği onu düz bir hash tablosundan ayırıyor. Birincisi **kapsamlar**: aynı isim iç içe bloklarda farklı şeyler ifade edebiliyor, ve bir blok kapanınca onun isimleri bir anda kaybolmalı. İkincisi **hız**: bir kaynak dosyadaki her isim tokeni (binlerce, milyonlarca) tabloya en az bir kez soruluyor.

---

## 1. Kapsam kuralları

C'de bir isim, onu içeren en içteki `{ }` bloğunda tanımlıysa o tanıma bağlanıyor; değilse bir dıştaki bloğa bakılıyor, ve en dışta global kapsam var. Bu derste kullanacağımız küçük dil, C'nin bu kuralının çıplak hali: `int AD;` bir tanım, `{` ve `}` kapsam açıp kapatıyor, diğer her isim bir kullanım.

```
 1  int x;
 2  int y;
 3  {
 4    int x;            ← dıştaki x'i gölgeliyor
 5    x = y;            ← x: satır 4, y: satır 2
 6    {
 7      int z; int y;   ← y'yi gölgeliyor
 8      z = x + y;      ← z: 7, x: 4, y: 7
 9    }
10    z = 1;            ← hata: z bu kapsamda yok (satır 9'da öldü)
11    int x;            ← hata: x bu kapsamda zaten tanımlı
12  }
13  x = y;              ← x: 1, y: 2
```

Sembol tablosundan istenenler:

| İşlem | Anlamı |
| --- | --- |
| `kapsam_ac()` | Yeni, boş bir iç kapsam |
| `kapsam_kapat()` | En içteki kapsamın **bütün** isimlerini unut |
| `sembol_tanimla(ad)` | Şu anki kapsama ekle; **aynı** kapsamda zaten varsa hata |
| `sembol_bul(ad)` | En içteki görünür tanımı döndür |

Kapsamlar bir **yığın** (Ders 8.4): açılan son kapsam ilk kapanıyor. Bu, tasarımın anahtarı olacak.

---

## 2. String interning

Bir kaynak dosyada aynı isim defalarca geçiyor. Ders 8.14'teki tabloyu kullanırsak her `sembol_bul` önce ismin hash'ini hesaplıyor (ismin bütün baytları), sonra zincirde `strcmp` yapıyor (yine bütün baytlar). Bunun yerine, isimleri **bir kez**, sözcüksel çözümleyici (lexer) onları okurken kanonik bir kopyaya çevirirsek: her farklı string için bellekte tek bir kopya, ve aynı içerikli iki string her zaman **aynı pointer**. Buna **interning** denir.

```c
/* intern.h: her farkli string icin tek bir kopya; esit stringler = esit pointer'lar */
#ifndef INTERN_H
#define INTERN_H
#include <stddef.h>
const char *intern(const char *s, size_t uzunluk);    /* s[0..uzunluk) icin kanonik kopya */
size_t intern_sayisi(void);
void intern_temizle(void);
#endif
```

```c
/* intern.c: zincirlemeli hash tablosu (Ders 8.14), yalnizca anahtar. Program boyunca yasar. */
#include "intern.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

typedef struct Ip { struct Ip *sonraki; uint32_t hash; size_t uz; char s[]; } Ip;

static Ip **kova;
static size_t kova_sayisi, adet;

static uint32_t fnv1a(const char *s, size_t n) {
    uint32_t h = 2166136261u;
    for (size_t i = 0; i < n; i++) { h ^= (unsigned char)s[i]; h *= 16777619u; }
    return h;
}

static void buyut(void) {
    size_t yeni = kova_sayisi ? 2 * kova_sayisi : 256;
    Ip **k = calloc(yeni, sizeof *k);
    for (size_t i = 0; i < kova_sayisi; i++)
        for (Ip *p = kova[i], *s; p; p = s) { s = p->sonraki; Ip **h = &k[p->hash & (yeni - 1)]; p->sonraki = *h; *h = p; }
    free(kova);
    kova = k; kova_sayisi = yeni;
}

const char *intern(const char *s, size_t n) {
    if (adet + 1 > kova_sayisi) buyut();
    uint32_t h = fnv1a(s, n);
    Ip **p = &kova[h & (kova_sayisi - 1)];
    for (Ip *q = *p; q; q = q->sonraki)
        if (q->hash == h && q->uz == n && memcmp(q->s, s, n) == 0) return q->s;   /* zaten var: ayni pointer */
    Ip *y = malloc(sizeof *y + n + 1);
    memcpy(y->s, s, n); y->s[n] = 0;
    y->hash = h; y->uz = n;
    y->sonraki = *p; *p = y;
    adet++;
    return y->s;
}
```

(Ders 8.14'teki tablonun sadeleşmiş hali; değer yok, silme yok. `malloc` hata kontrolleri kısalık için yok.) Arayüz uzunluk alıyor: lexer kaynak metnin **içinden** bir dilimi, `'\0'` ile bitmeyen bir parçayı intern edebiliyor, ayrı bir kopya yapmadan.

Interning'in getirdikleri:

- **Karşılaştırma $O(1)$**: `ad1 == ad2`. Uzun isimler (`kapsam_kapat`, `MAX_BUFFER_SIZE`) için `strcmp` uzunluk kadar sürer.
- **Hash $O(1)$**: sembol tablosu artık string'i değil **pointer'ı** hash'leyebilir. Pointer bir tamsayı.
- **Bellek**: her isim bir kez saklanıyor. Ders 8.14'teki `tablo.c`, yorumlar dahil 559 isim tokeni içeriyor ama sadece 139 farklı isim (Alıştırma 3).
- **Anahtar kelimeler**: lexer başlarken `int`, `while`, `return`'ü intern edip pointer'larını saklarsa, bir ismin anahtar kelime olup olmadığını pointer karşılaştırmasıyla anlıyor.

Bedeli: intern edilmiş stringler program boyunca yaşıyor (ya da derleme birimi bitene kadar). Derleyici için bu sorun değil, hatta ideal: Ders 8.21'deki arena allocator'la intern tablosunun bütün belleği tek seferde serbest bırakılıyor. Lisp'in **sembolleri**, Java'nın `String.intern()`'ü, Python'un tanımlayıcıları, Ruby'nin `:sembol`'leri aynı fikir.

---

## 3. Tasarım: kovalar yığın, kapsamlar liste

İlk akla gelen tasarım, her kapsam için ayrı bir hash tablosu ve onların bir yığını. Arama içten dışa her tabloya bakıyor. Basit, ama global bir ismi (bir fonksiyon adını, `printf`'i) derin bir kapsamdan aramak, aradaki her kapsamın tablosuna bakmak demek: maliyet derinlikle doğrusal.

Daha iyi tasarım (Aho ve arkadaşlarının *Compilers* kitabında ve pek çok gerçek derleyicide), **tek** bir hash tablosu kullanıyor:

- Her kovanın zinciri bir **yığın**: yeni tanım zincirin **başına** ekleniyor. Aynı ismin dış kapsamdaki tanımı onun arkasında kalıyor; arama zincirde ilk eşleşmeyi bulunca en içteki tanımı bulmuş oluyor. Gölgeleme kendiliğinden.
- Ayrıca her kapsam, kendi tanımladığı sembollerin bir **listesini** tutuyor (ikinci bir `sonraki` pointer'ı). Kapsam kapanınca bu liste gezilip her sembol kovasından sökülüyor.

```
 satır 8'deki durum (seviye 2):

  kova("x") → [x, sv 1, satır 4] → [x, sv 0, satır 1] → /
  kova("y") → [y, sv 2, satır 7] → [y, sv 0, satır 2] → /
  kova("z") → [z, sv 2, satır 7] → /

  kapsamlar[2] → z(7) ← y(7)        kapsamlar[1] → x(4)        kapsamlar[0] → y(2) ← x(1)
  (her listede en son tanımlanan önde)
```

```c
/* sembol.h: ic ice kapsamli sembol tablosu. Isimler intern edilmis olmali. */
#ifndef SEMBOL_H
#define SEMBOL_H
#include <stdbool.h>

typedef struct Sembol {
    const char *isim;            /* intern edilmis: karsilastirma pointer esitligi */
    int seviye;                  /* tanimlandigi kapsam derinligi (0 = global) */
    int satir;                   /* tanimlandigi satir */
    struct Sembol *golge;        /* ayni kovada sonraki: dis kapsamdaki ayni isim de burada */
    struct Sembol *kapsam_sonraki;  /* ayni kapsamda tanimlanan bir onceki sembol */
} Sembol;

void    sembol_baslat(void);
void    kapsam_ac(void);
void    kapsam_kapat(void);
int     kapsam_seviyesi(void);
Sembol *sembol_tanimla(const char *isim, int satir);  /* ayni kapsamda zaten varsa NULL */
Sembol *sembol_bul(const char *isim);                 /* en ic kapsamdaki tanim */
void    sembol_bitir(void);
#endif
```

Gerçek bir derleyicide `Sembol`'de tip, depolama sınıfı, yığın çerçevesindeki konum gibi alanlar da olur. Bir sembol aynı anda iki **intrusive** listenin (Ders 8.3) üyesi: kova zinciri ve kapsam listesi.

```c
/* sembol.c: tek hash tablosu + kapsam yigini. Her kova bir yigin: en ic tanim en ustte.
   Kapsam kapaninca o kapsamin sembolleri kovalarinin TEPESINDEN cikariliyor: O(1)/sembol. */
#include "sembol.h"
#include <stdint.h>
#include <stdlib.h>

#define KOVA (1u << 12)
static Sembol *kova[KOVA];
static Sembol *kapsamlar[256];          /* her seviyenin tanimladigi sembollerin listesi */
static int seviye;

static uint32_t kova_no(const char *isim) {           /* intern pointer'inin kendisini hash'le */
    uintptr_t p = (uintptr_t)isim;
    uint32_t h = (uint32_t)(p ^ (p >> 32));
    h ^= h >> 16; h *= 0x85ebca6bu; h ^= h >> 13;      /* fmix32'nin yarisi yeter */
    return h & (KOVA - 1);
}

void sembol_baslat(void) { seviye = 0; kapsamlar[0] = NULL; }
int  kapsam_seviyesi(void) { return seviye; }

void kapsam_ac(void) { kapsamlar[++seviye] = NULL; }

void kapsam_kapat(void) {
    for (Sembol *s = kapsamlar[seviye], *k; s; s = k) {
        k = s->kapsam_sonraki;
        Sembol **p = &kova[kova_no(s->isim)];
        while (*p != s) p = &(*p)->golge;           /* neredeyse her zaman ilk adimda: s en ustte */
        *p = s->golge;                                /* dis kapsamdaki tanim yeniden gorunur */
        free(s);
    }
    seviye--;
}

Sembol *sembol_bul(const char *isim) {
    for (Sembol *s = kova[kova_no(isim)]; s; s = s->golge)
        if (s->isim == isim) return s;               /* strcmp yok: intern sayesinde == yeter */
    return NULL;
}

Sembol *sembol_tanimla(const char *isim, int satir) {
    Sembol *o = sembol_bul(isim);
    if (o && o->seviye == seviye) return NULL;      /* ayni kapsamda iki tanim */
    Sembol *s = malloc(sizeof *s);
    s->isim = isim; s->seviye = seviye; s->satir = satir;
    Sembol **k = &kova[kova_no(isim)];
    s->golge = *k; *k = s;                            /* kovanin tepesine: dis tanimi golgeler */
    s->kapsam_sonraki = kapsamlar[seviye]; kapsamlar[seviye] = s;
    return s;
}

void sembol_bitir(void) { while (seviye > 0) kapsam_kapat(); kapsam_kapat(); seviye = 0; }
```

Pointer'ın hash'i: intern pointer'ları `malloc`'tan geldiği için alt 4 biti hep 0 (16 bayt hizalı, Ders 4.22) ve ardışık ayrılan pointer'lar birbirine yakın. Doğrudan `p & (KOVA - 1)` kullanılsa alt 4 bit hep 0 olduğu için kovaların sadece 16'da biri kullanılırdı; birkaç kaydırma-XOR-çarpma bitleri karıştırıyor (Ders 8.13).

Tablo, kova sayısı ve en fazla 255 iç içe kapsamla sabit; `kapsamlar` dizisinin sınırı denetlenmiyor (gerçek kodda büyüyen bir dizi; C standardı derleyicilerden en az 127 iç içe blok seviyesini desteklemelerini istiyor). Kovalar sabit, çünkü bir derleme biriminde aynı anda görünür isim sayısı tahmin edilebilir; büyütme Ders 8.14'teki gibi eklenebilir.

---

## 4. İsim çözümleme

Bölüm 1'deki programı karakter karakter tarayan küçük bir çözümleyici:

```c
/* Kucuk bir dilin isim cozumlemesi: "int x;" tanimlar, { } kapsam acar/kapatir, diger isimler kullanimdir. */
#include <ctype.h>
#include <stdio.h>
#include <string.h>
#include "intern.h"
#include "sembol.h"

static const char *program =
    "int x;\n"                     /* 1 */
    "int y;\n"                     /* 2 */
    "{\n"                          /* 3 */
    "  int x;\n"                   /* 4  golgeler */
    "  x = y;\n"                   /* 5 */
    "  {\n"                        /* 6 */
    "    int z; int y;\n"          /* 7 */
    "    z = x + y;\n"             /* 8 */
    "  }\n"                        /* 9 */
    "  z = 1;\n"                   /* 10 tanimsiz */
    "  int x;\n"                   /* 11 ayni kapsamda tekrar */
    "}\n"                          /* 12 */
    "x = y;\n";                    /* 13 */

int main(void) {
    const char *INT = intern("int", 3);
    sembol_baslat();
    int satir = 1, tanim_bekleniyor = 0;
    for (const char *p = program; *p; ) {
        if (*p == '\n') { satir++; p++; continue; }
        if (*p == '{') { kapsam_ac(); p++; continue; }
        if (*p == '}') { kapsam_kapat(); p++; continue; }
        if (isalpha((unsigned char)*p)) {
            const char *bas = p;
            while (isalnum((unsigned char)*p)) p++;
            const char *ad = intern(bas, (size_t)(p - bas));
            if (ad == INT) { tanim_bekleniyor = 1; continue; }        /* anahtar kelime: pointer karsilastirmasi */
            if (tanim_bekleniyor) {
                Sembol *onceki = sembol_bul(ad);
                if (!sembol_tanimla(ad, satir))
                    printf("satir %2d: hata: '%s' bu kapsamda zaten tanimli (ilk tanim: satir %d)\n", satir, ad, onceki->satir);
                else if (onceki)
                    printf("satir %2d: uyari: '%s' distaki tanimi golgeliyor (satir %d)\n", satir, ad, onceki->satir);
                tanim_bekleniyor = 0;
            } else {
                Sembol *s = sembol_bul(ad);
                if (s) printf("satir %2d: %s -> tanim satir %d, seviye %d\n", satir, ad, s->satir, s->seviye);
                else   printf("satir %2d: hata: '%s' tanimlanmamis\n", satir, ad);
            }
            continue;
        }
        p++;
    }
    printf("%zu farkli isim intern edildi\n", intern_sayisi());
    sembol_bitir();
    intern_temizle();
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined cozumle.c sembol.c intern.c -o cozumle && ./cozumle
satir  4: uyari: 'x' distaki tanimi golgeliyor (satir 1)
satir  5: x -> tanim satir 4, seviye 1
satir  5: y -> tanim satir 2, seviye 0
satir  7: uyari: 'y' distaki tanimi golgeliyor (satir 2)
satir  8: z -> tanim satir 7, seviye 2
satir  8: x -> tanim satir 4, seviye 1
satir  8: y -> tanim satir 7, seviye 2
satir 10: hata: 'z' tanimlanmamis
satir 11: hata: 'x' bu kapsamda zaten tanimli (ilk tanim: satir 4)
satir 13: x -> tanim satir 1, seviye 0
satir 13: y -> tanim satir 2, seviye 0
4 farkli isim intern edildi
```

Bölüm 1'deki beklentilerin hepsi. Satır 9'daki `}` z'yi ve içteki y'yi söktü: satır 10'da z bulunamıyor. Satır 12'deki `}` içteki x'i söktü: satır 13'te x yine satır 1'deki tanım. 13 satırda 20 isim tokeni geçiyor ama sadece 4 farklı isim var (`int`, `x`, `y`, `z`). Gölgeleme uyarısı clang'in `-Wshadow`'unun yaptığı şey.

Gerçek bir derleyicide çözümleme ayrıştırmadan sonra, AST üzerinde bir gezinme olarak yapılıyor (Ders 8.7): her blok düğümüne girerken `kapsam_ac`, çıkarken `kapsam_kapat`, her tanım düğümünde `sembol_tanimla`, her isim düğümünde `sembol_bul` ve bulunan `Sembol *` düğüme yazılıyor. Sonraki aşamalar ismi bir daha aramıyor, doğrudan pointer'ı kullanıyor.

---

## 5. Ölçüm

İki tasarımı karşılaştıralım: kapsam başına ayrı bir tablo (string anahtarlı, aramada içten dışa gezen) ve tek tablo. $D$ iç içe kapsam açılıyor, her birinde 8 yerel isim; global kapsamda tanımlı `sayac` 2 milyon kez aranıyor. Tek tabloda iki ölçüm: isim önceden intern edilmişken (derleyicide normal durum, lexer zaten intern etti) ve intern etmenin maliyeti de dahil.

```c
/* Yontem A: kapsam basina kucuk bir hash tablosu, string anahtarli; aramada icten disa her tabloya bak */
typedef struct G { const char *isim; struct G *s; } G;
typedef struct { G *k[64]; } KTablo;
static uint32_t fnv(const char *s) { uint32_t h = 2166136261u; while (*s) { h ^= (unsigned char)*s++; h *= 16777619u; } return h; }
static KTablo yigin_[512]; static int derin_;
static void a_tanimla(const char *ad) { G *g = malloc(sizeof *g); g->isim = ad; G **k = &yigin_[derin_].k[fnv(ad) & 63]; g->s = *k; *k = g; }
__attribute__((noinline)) static const char *a_bul(const char *ad) {
    uint32_t h = fnv(ad) & 63;
    for (int d = derin_; d >= 0; d--)
        for (G *g = yigin_[d].k[h]; g; g = g->s) if (strcmp(g->isim, ad) == 0) return g->isim;
    return NULL;
}
```

(`noinline` ve iki ayrı sorgu kopyası, derleyicinin döngüde hiç değişmeyen bir aramayı döngünün dışına çıkarıp ölçümü sıfırlamasını önlemek için; ilk denemede tam olarak bu oldu ve 0.0 ns ölçüldü. Ders 7.15.)

```
$ cc -std=c11 -O2 -Wall olcum.c sembol.c intern.c -o olcum && ./olcum
derinlik   1:  kapsam basina tablo    6.0 ns   tek tablo (intern hazir)  1.2 ns   tek tablo + intern  7.2 ns
derinlik  10:  kapsam basina tablo   14.8 ns   tek tablo (intern hazir)  1.2 ns   tek tablo + intern  7.6 ns
derinlik 100:  kapsam basina tablo   69.9 ns   tek tablo (intern hazir)  1.2 ns   tek tablo + intern  7.3 ns
derinlik 200:  kapsam basina tablo  125.0 ns   tek tablo (intern hazir)  1.2 ns   tek tablo + intern  7.2 ns
```

- Kapsam başına tabloda maliyet derinlikle doğrusal: kapsam başına yaklaşık 0.6 ns (her kapsamda bir boş kova kontrolü).
- Tek tabloda derinlikten **bağımsız**: 1.2 ns, bir pointer hash'i, bir dizi okuması, bir pointer karşılaştırması.
- Intern etmenin kendisi yaklaşık 6 ns (string'in hash'i ve bir `memcmp`). Bu, lexer'da her token için **bir kez** ödeniyor; sonraki her arama, karşılaştırma ve tablo erişimi 1.2 ns'lik yoldan.

200 iç içe kapsam gerçekçi değil; tipik C kodunda derinlik 3–6. Ama tasarım farkı başka bir yerden de geliyor: kapsam başına tablo her `kapsam_ac`'ta bir tablo ayırıyor ve sıfırlıyor (burada 64 kova, 512 bayt), çoğu kapsam ise sadece birkaç isim tanımlıyor. Tek tabloda kapsam açmak bir sayaç artırımı.

---

## Alıştırmalar

**1** – `kapsam_kapat`'taki `while (*p != s)` döngüsü kaç kez döner? Bir sembol, kapsamı kapanırken her zaman kovasının **tepesinde** mi? İspatla ya da karşı örnek ver.

**2** – C'de aynı isim aynı anda bir değişken, bir `struct` etiketi ve bir `goto` etiketi olabilir: `struct x { int x; } x; x: ;` geçerli C. Bu ayrı **isim alanlarını** (namespaces) sembol tablosunda nasıl desteklersin? İki yol öner.

**3** – Bir C dosyasındaki isim tokenlarını sayan ve hepsini intern eden bir program yaz. Ders 8.14'teki `tablo.c` için kaç token, kaç farklı isim çıkıyor? Interning olmasaydı derleyici isim stringleri için ne kadar fazla bellek tutardı?

**4** – C'de bir isim **kullanılmadan önce** tanımlanmalı. Java'da bir sınıfın metodu, aynı sınıfta daha **aşağıda** tanımlanan bir alanı ya da metodu kullanabilir. Bu, isim çözümlemeyi nasıl değiştirir? Bu dersteki tek geçişli çözümleyici yeterli mi?

**5** – Tek tablo tasarımında arama derinlikten bağımsız, kapsam kapatma ise o kapsamın sembol sayısıyla orantılı. Ama bir hata ayıklayıcı (LLDB, Ders 2.6) programın herhangi bir noktasındaki görünür değişkenleri sormak istiyor; derleme bittikten sonra. Kapsamlar kapanınca semboller silindiği için bu tasarım bunu desteklemiyor. Derleyiciler bu bilgiyi nasıl saklıyor?

<details>
<summary>Cevaplar</summary>

**1** – **Hiç** dönmez; her zaman ilk adımda `*p == s`. İspat: `s`, seviye $L$'de tanımlandı ve kovasının tepesine kondu. Ondan sonra aynı kovanın tepesine konan her sembol ya (a) seviye $L$'de `s`'ten **sonra** tanımlandı, ya da (b) daha derin bir seviyede tanımlandı. (b) türündekiler, $L$ kapanmadan önce kapanan kapsamlara ait, yani `s`'in kapsamı kapanırken zaten sökülmüşler. (a) türündekiler `kapsamlar[L]` listesinde `s`'ten **önce** geliyor (liste en son tanımlanandan başlıyor), yani `s`'ten önce sökülüyorlar. Dolayısıyla `s` söküleceği anda kovasının tepesinde. Döngü bir güvenlik ağı; `kova[...] = s->golge` tek satırı yeterli. Bu, kapsamların **yığın** gibi açılıp kapanmasının (LIFO) doğrudan sonucu; aynı argüman kova zincirlerinin de birer yığın olduğunu söylüyor.

**2** – Birinci yol: her isim alanı için ayrı bir tablo (değişkenler/fonksiyonlar/typedef'ler bir tabloda, etiketler bir tabloda, `struct`/`union`/`enum` etiketleri bir tabloda). İkinci yol: tek tablo, ama `Sembol`'e bir `alan` alanı ekleyip aramayı `(isim, alan)` çiftiyle yapmak: `if (s->isim == isim && s->alan == alan)`. İkincisinde aynı ismin farklı alanlardaki tanımları aynı kovada, ama hiçbiri ötekini gölgelemiyor. C'de `goto` etiketlerinin kapsamı da farklı: blok değil, bütün **fonksiyon**. Bu yüzden etiketler için ayrı, fonksiyon başına açılıp kapanan bir tablo daha doğal.

**3** –

```
../zincir/tablo.c: 559 isim tokeni (2289 bayt), 139 farkli isim
```

(Sayaç basit: harf ya da `_` ile başlayan dizileri sayıyor, yorumlardaki kelimeler de dahil.) Interning olmadan her token için ayrı bir string kopyası tutulsaydı 2289 bayt (`'\0'`'lar ve `malloc` başlıkları hariç), intern edilince 139 farklı ismin toplam uzunluğu, birkaç yüz bayt. Daha önemlisi, sonraki her karşılaştırma `strcmp` yerine `==`. Gerçek bir projede başlık dosyaları eklenince (`#include <stdio.h>` yüzlerce isim getirir) oran çok daha büyür: aynı isimler (`size_t`, `NULL`, `printf`) her dosyada binlerce kez geçer.

**4** – Tek geçiş yetmez: bir isim kullanıldığında tanımı henüz tabloda olmayabilir. Çözüm **iki geçiş**: önce sınıf gövdesindeki bütün tanımları (alanlar, metot imzaları) toplayıp tabloya koy, sonra metot gövdelerini çözümle. Derleyiciler bunu AST üzerinde iki gezinmeyle yapıyor (Ders 8.7'deki AST burada işe yarıyor: kaynak metni iki kez ayrıştırmak gerekmiyor). C bu kısıtı biraz da tek geçişli derleyiciler (1970'lerin bellek sınırları) için koymuştu; fonksiyonlar için bile ileri bildirim (prototype) istemesi bu yüzden. C'de de bir istisna var: `goto` etiketleri fonksiyonun aşağısında tanımlanabilir, bu yüzden derleyici çözümlenmemiş etiketleri fonksiyon sonuna kadar bir listede tutup orada denetliyor.

**5** – Kapsamlar kapanırken semboller silinmiyor, **saklanıyor**: her kapsam bir ağaç düğümü oluyor (ebeveyni dış kapsam, çocukları iç kapsamlar) ve kendi sembol listesini tutuyor. Derleme sırasındaki hızlı arama yine tek tablodan yapılıyor; kapsam kapanınca semboller tablodan sökülüyor ama `free` edilmiyor, kapsam ağacında kalıyor. Derleyici sonunda bu ağacı, her kapsamın hangi **kod adresi aralığına** karşılık geldiğiyle birlikte, nesne dosyasına hata ayıklama bilgisi olarak yazıyor: DWARF formatındaki `DW_TAG_lexical_block` girdileri (Ders 7.16'daki ELF bölümlerinden `.debug_info`). LLDB bir duraklama noktasında program sayacını (`pc`) alıp hangi blokların içinde olduğunu bu ağaçtan buluyor ve görünür değişkenleri o blokların listelerinden topluyor.

</details>

---

## Kaynaklar

- Alfred Aho, Monica Lam, Ravi Sethi ve Jeffrey Ullman, *Compilers: Principles, Techniques, and Tools* (2. baskı), Bölüm 2.7: sembol tabloları ve kapsamlar.
- Keith Cooper ve Linda Torczon, *Engineering a Compiler* (2. baskı), Bölüm 5.5: sembol tabloları, iç içe kapsamlar için tek tablo tasarımı.
- Andrew Appel, *Modern Compiler Implementation in C*, Bölüm 5: sembol tabloları, "destructive update" ve geri alma yığını.
- David Hanson ve Christopher Fraser, *A Retargetable C Compiler: Design and Implementation* (lcc): `string.c` (interning) ve `sym.c` (kapsamlı sembol tablosu).
- ISO/IEC 9899:2011 (C11), §6.2.1 (kapsamlar), §6.2.3 (isim alanları), §5.2.4.1 (çeviri sınırları).

**Sıradaki ders:** Trie ve radix ağacı. Anahtar kelime tanıma ve önek arama.
