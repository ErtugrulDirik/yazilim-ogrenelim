---
title: "8.1 Soyut veri tipi (ADT)"
description: "Bir veri yapısını 'ne yapar' (arayüz) ve 'nasıl yapar' (uygulama) diye ikiye ayırmak; C'de bunu sağlayan araçlar: başlık dosyası, tamamlanmamış tip (incomplete type) ile opak pointer, dosya düzeyinde static; derleyicinin içeriye erişimi engellemesi; aynı arayüzün iki uygulaması (sırasız dizi ve sıralı dizi + ikili arama) ve kullanan koda dokunmadan ~9 kat hızlanma; değişmezler (invariant), oluşturma/yok etme sözleşmesi ve geri çağırma ile gezinme."
---

Faz 8 veri yapıları fazı: bağlı listeler, yığınlar, kuyruklar, ağaçlar, hash tabloları. Hepsine geçmeden önce bütün fazda kullanacağımız **tasarım biçimini** kuruyoruz. Bir veri yapısının iki yüzü var:

- **Ne yapar?** "Bir küme: eleman ekleyebilir, silebilir, bir elemanın içinde olup olmadığını sorabilirsin." Bu, yapının **arayüzü** (interface).
- **Nasıl yapar?** "Elemanları sıralı bir dizide tutup ikili aramayla buluyor." Bu, yapının **uygulaması** (implementation).

**Soyut veri tipi** (ADT, abstract data type), bir tipi sadece birinci yüzüyle, yani üzerinde yapılabilen işlemlerle ve bu işlemlerin davranışıyla tanımlamak demek. Kullanan kod sadece arayüzü bilir; uygulama değişebilir, kullanan kod değişmez. Bu derste C'nin buna izin veren araçlarını (Ders 2.11'deki başlık dosyalarının bir adım ötesi) öğrenip bir küme ADT'si yazacağız, sonra uygulamasını tamamen değiştirip kullanan kodun **tek satırına dokunmadan** ~9 kat hızlandıracağız.

---

## 1. Sorun: her şeyi bilen kullanıcı

Ders 2.11'deki kesir modülünü hatırla. `fraction.h` şöyleydi:

```c
struct Fraction {
    int num;
    int den;
};
```

`struct`'ın tanımı başlık dosyasındaydı, yani onu `#include` eden **her** dosya alanları görüyor ve değiştirebiliyordu:

```c
struct Fraction f = fraction_make(1, 2);
f.den = 0;          /* derleyici itiraz etmez */
```

Bunun iki bedeli var:

1. **Değişmezler korunamaz.** Kesir modülü "payda asla 0 değildir ve kesir hep sadeleştirilmiş haldedir" diye bir kural koymak istiyorsa, bu kuralı sadece kendi fonksiyonlarında uygulayabilir. Dışarıdaki kod alanlara doğrudan yazabildiği sürece kural her an çiğnenebilir.
2. **Uygulama değiştirilemez.** Bir gün kesri `long` ile tutmaya karar verirsen, `f.num`'a doğrudan dokunan her dosya (belki başkalarının yazdığı yüzlerce dosya) etkilenir. `sizeof(struct Fraction)` değiştiği için hepsinin yeniden derlenmesi gerekir.

İstediğimiz: kullanıcının yapının **içini hiç görmemesi**.

---

## 2. Opak pointer

C'de bir `struct`'ı **tanımlamadan bildirebilirsin**:

```c
typedef struct Kume Kume;      /* "Kume diye bir struct var." Icinde ne oldugu yazmiyor. */
```

Bu bir **tamamlanmamış tip** (incomplete type). Derleyici böyle bir tip hakkında sadece bir şey biliyor: var. Boyutunu bilmiyor, alanlarını bilmiyor. Ama yine de ona bir **pointer** tanımlanabilir, çünkü bütün struct pointer'ları aynı boyutta (Ders 4.5): `Kume *k` geçerli. Kullanıcı elinde bir pointer tutar, onu fonksiyonlara geçirir, ama işaret ettiği şeyin içine bakamaz. Buna **opak pointer** (opaque pointer) denir: içi görünmeyen bir tutamak (handle).

Küme ADT'sinin bütün arayüzü:

```c
/* kume.h: tamsayi kumesi ADT'si. Kullanici sadece bunu gorur. */
#ifndef KUME_H
#define KUME_H

#include <stdbool.h>
#include <stddef.h>

typedef struct Kume Kume;          /* opak tip: icerigi burada YOK */

Kume  *kume_olustur(void);
void   kume_yok_et(Kume *k);
bool   kume_ekle(Kume *k, int x);  /* yeni eklendiyse true, zaten varsa false */
bool   kume_icerir(const Kume *k, int x);
bool   kume_sil(Kume *k, int x);
size_t kume_boyut(const Kume *k);
void   kume_yazdir(const Kume *k);

#endif
```

Dikkat: bu dosyada `struct Kume`'ın alanları **yok**. Kullanıcının bilmesi gereken her şey burada: hangi işlemler var, ne alıyorlar, ne döndürüyorlar. `const Kume *` alan fonksiyonlar (`kume_icerir`, `kume_boyut`) kümeyi değiştirmeyeceğine söz veriyor (Ders 4.8).

Kullanıcı içine girmeye çalışırsa derleyici durduruyor:

```c
#include "kume.h"
int main(void) {
    Kume *k = kume_olustur();
    k->adet = 100;              /* icini kurcalamaya calis */
    Kume yigindaki;             /* ya da yiginda bir tane olustur */
    return (int)sizeof(Kume);
}
```

```
$ cc -std=c11 -c hile.c
hile.c:4:6: error: incomplete definition of type 'Kume' (aka 'struct Kume')
hile.c:5:10: error: variable has incomplete type 'Kume' (aka 'struct Kume')
hile.c:6:17: error: invalid application of 'sizeof' to an incomplete type 'Kume' (aka 'struct Kume')
```

Üç hata, üç ayrı koruma: alanlara erişilemiyor, tipten değişken tanımlanamıyor (boyutu bilinmiyor), `sizeof` alınamıyor. Bunun bir sonucu: kullanıcı bir `Kume`'ı **kendisi oluşturamaz**, yığında da heap'te de. Nesneyi sadece modül oluşturabilir (`kume_olustur`), ve sadece modül yok edebilir (`kume_yok_et`). Bu yüzden opak tipler hemen her zaman `malloc` ile ayrılır.

Standart kütüphanede bunun bir örneğini Faz 2'den beri kullanıyorsun: `FILE *`. `fopen` bir `FILE *` döndürür, `fprintf` ve `fclose` onu alır; `FILE`'ın içinde ne olduğunu (tampon, dosya tanımlayıcı, konum) hiç bilmedin ve bilmen gerekmedi.

---

## 3. Uygulama 1: sırasız dizi

Uygulama ayrı bir `.c` dosyasında. `struct`'ın tanımı **sadece burada**:

```c
/* kume_dizi.c: uygulama 1, sirasiz dinamik dizi (Ders 4.24). */
#include "kume.h"
#include <stdio.h>
#include <stdlib.h>

struct Kume {                      /* tanim sadece bu dosyada */
    int *veri;
    size_t adet, kapasite;
};

Kume *kume_olustur(void) {
    Kume *k = malloc(sizeof *k);
    if (k) { k->veri = NULL; k->adet = 0; k->kapasite = 0; }
    return k;
}

void kume_yok_et(Kume *k) {
    if (!k) return;
    free(k->veri);
    free(k);
}

static size_t bul(const Kume *k, int x) {     /* static: disaridan gorunmez */
    for (size_t i = 0; i < k->adet; i++)
        if (k->veri[i] == x) return i;
    return k->adet;                            /* yok */
}

bool kume_icerir(const Kume *k, int x) { return bul(k, x) < k->adet; }

bool kume_ekle(Kume *k, int x) {
    if (kume_icerir(k, x)) return false;
    if (k->adet == k->kapasite) {
        size_t yeni = k->kapasite ? 2 * k->kapasite : 4;
        int *p = realloc(k->veri, yeni * sizeof *p);
        if (!p) return false;
        k->veri = p; k->kapasite = yeni;
    }
    k->veri[k->adet++] = x;
    return true;
}

bool kume_sil(Kume *k, int x) {
    size_t i = bul(k, x);
    if (i == k->adet) return false;
    k->veri[i] = k->veri[--k->adet];           /* sira onemsiz: sonuncuyu buraya tasi */
    return true;
}

size_t kume_boyut(const Kume *k) { return k->adet; }

void kume_yazdir(const Kume *k) {
    printf("{");
    for (size_t i = 0; i < k->adet; i++) printf(i ? ", %d" : "%d", k->veri[i]);
    printf("}\n");
}
```

Ders 4.24'teki dinamik dizi, bir kural eklenmiş haliyle: **aynı sayı iki kez bulunmaz**. Bu kuralın adı **değişmez** (invariant): her fonksiyon çağrısından önce ve sonra doğru olan bir özellik. `kume_ekle` önce `kume_icerir` ile kontrol ederek kuralı koruyor. Opak tip sayesinde kuralı bozabilecek başka kod **yok**: `veri` dizisine dokunabilen tek yer bu dosya.

`bul` fonksiyonu `static` (Ders 2.11): dosyaya özel, arayüzün parçası değil. Kullanıcı onu çağıramaz, hatta varlığından haberi yok; uygulama değişince silinebilir.

`kume_sil`'deki hile: sıra önemli olmadığı için silinen elemanın yerine **sonuncuyu** koyup diziyi bir kısaltıyoruz, kaydırma yok: $O(1)$ (bulmak hariç). Sırayı korumak zorunda olan bir yapı bunu yapamaz; "küme" soyutlamasının "sıra yok" demesi, uygulamaya bu serbestliği veriyor.

Kullanan kod:

```c
/* ana.c: kumeyi KULLANAN kod. Sadece kume.h'yi biliyor. */
#include <stdio.h>
#include <time.h>
#include "kume.h"

int main(void) {
    Kume *k = kume_olustur();
    int sayilar[] = { 5, 3, 8, 3, 1, 8, 9 };
    for (int i = 0; i < 7; i++)
        printf("ekle %d -> %s\n", sayilar[i], kume_ekle(k, sayilar[i]) ? "eklendi" : "zaten var");
    kume_yazdir(k);
    printf("boyut=%zu, 8 var mi? %d, 4 var mi? %d\n", kume_boyut(k), kume_icerir(k, 8), kume_icerir(k, 4));
    kume_sil(k, 3);
    kume_yazdir(k);
    kume_yok_et(k);

    /* Ayni kod, buyuk veri: hangi uygulama baglandiysa onun hizinda calisir */
    k = kume_olustur();
    clock_t t0 = clock();
    for (int i = 0; i < 20000; i++) kume_ekle(k, (i * 7919) % 20011);
    long bulunan = 0;
    for (int i = 0; i < 20000; i++) bulunan += kume_icerir(k, i);
    double sn = (double)(clock() - t0) / CLOCKS_PER_SEC;
    printf("20000 ekleme + 20000 arama: boyut=%zu bulunan=%ld, %.3f s\n", kume_boyut(k), bulunan, sn);
    kume_yok_et(k);
    return 0;
}
```

```
$ cc -std=c11 -O2 -Wall -Wextra ana.c kume_dizi.c -o k_dizi && ./k_dizi
ekle 5 -> eklendi
ekle 3 -> eklendi
ekle 8 -> eklendi
ekle 3 -> zaten var
ekle 1 -> eklendi
ekle 8 -> zaten var
ekle 9 -> eklendi
{5, 3, 8, 1, 9}
boyut=5, 8 var mi? 1, 4 var mi? 0
{5, 9, 8, 1}
20000 ekleme + 20000 arama: boyut=20000 bulunan=19989, 0.149 s
```

(`(i * 7919) % 20011` 20 000 farklı sayı üretir, çünkü 20011 asal ve 7919 onun katı değil, yani $i \mapsto 7919 i \bmod 20011$ birebir (Ders 6.18); bunların 0–19 999 arasında olanları 19 989 tane. `-fsanitize=address,undefined` ile de çalıştırdık, hata yok.)

3'ü silince 9 onun yerine geçti: `{5, 9, 8, 1}`. Küme açısından doğru; sıra zaten tanımsızdı.

---

## 4. Uygulama 2: sıralı dizi ve ikili arama

İlk uygulamada her `kume_icerir` bütün diziye bakıyor: $O(n)$. 20 000 ekleme ve 20 000 arama, her biri ortalama 10 000 karşılaştırma: ~4 × 10⁸ işlem. Diziyi **sıralı** tutarsak arama ikili arama ile $O(\log n)$ olur (Ders 2.10).

```c
/* kume_sirali.c: uygulama 2, sirali dizi + ikili arama. Ayni arayuz. */
#include "kume.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct Kume {
    int *veri;
    size_t adet, kapasite;
};

Kume *kume_olustur(void) {
    Kume *k = calloc(1, sizeof *k);
    return k;
}

void kume_yok_et(Kume *k) {
    if (!k) return;
    free(k->veri);
    free(k);
}

/* x'in olmasi gereken konum: ilk veri[i] >= x olan i (Ders 4.2'deki ikili arama) */
static size_t konum(const Kume *k, int x) {
    size_t lo = 0, hi = k->adet;
    while (lo < hi) {
        size_t orta = lo + (hi - lo) / 2;
        if (k->veri[orta] < x) lo = orta + 1; else hi = orta;
    }
    return lo;
}

bool kume_icerir(const Kume *k, int x) {
    size_t i = konum(k, x);
    return i < k->adet && k->veri[i] == x;
}

bool kume_ekle(Kume *k, int x) {
    size_t i = konum(k, x);
    if (i < k->adet && k->veri[i] == x) return false;
    if (k->adet == k->kapasite) {
        size_t yeni = k->kapasite ? 2 * k->kapasite : 4;
        int *p = realloc(k->veri, yeni * sizeof *p);
        if (!p) return false;
        k->veri = p; k->kapasite = yeni;
    }
    memmove(&k->veri[i + 1], &k->veri[i], (k->adet - i) * sizeof *k->veri);  /* Ders 4.18 */
    k->veri[i] = x;
    k->adet++;
    return true;
}

bool kume_sil(Kume *k, int x) {
    size_t i = konum(k, x);
    if (i == k->adet || k->veri[i] != x) return false;
    memmove(&k->veri[i], &k->veri[i + 1], (k->adet - i - 1) * sizeof *k->veri);
    k->adet--;
    return true;
}

size_t kume_boyut(const Kume *k) { return k->adet; }

void kume_yazdir(const Kume *k) {
    printf("{");
    for (size_t i = 0; i < k->adet; i++) printf(i ? ", %d" : "%d", k->veri[i]);
    printf("}\n");
}
```

Değişmez artık bir kural daha içeriyor: **dizi kesin artan sırada**. `kume_ekle` doğru konumu bulup elemanları bir sağa kaydırıyor (`memmove`, çünkü kaynak ve hedef örtüşüyor, Ders 4.18); `kume_sil` sola kaydırıyor. Ekleme ve silme hâlâ $O(n)$ (kaydırma yüzünden) ama arama $O(\log n)$.

**`ana.c`'ye hiç dokunmadan**, sadece bağlanan dosyayı değiştiriyoruz:

```
$ cc -std=c11 -O2 -Wall -Wextra ana.c kume_sirali.c -o k_sirali && ./k_sirali
ekle 5 -> eklendi
ekle 3 -> eklendi
ekle 8 -> eklendi
ekle 3 -> zaten var
ekle 1 -> eklendi
ekle 8 -> zaten var
ekle 9 -> eklendi
{1, 3, 5, 8, 9}
boyut=5, 8 var mi? 1, 4 var mi? 0
{1, 5, 8, 9}
20000 ekleme + 20000 arama: boyut=20000 bulunan=19989, 0.016 s
```

Aynı sonuçlar (yazdırma sırası dışında, ki o zaten küme için anlamsızdı), **9 kat** daha hızlı (Apple M2). `ana.c` yeniden derlenmek zorunda bile değil: `ana.o`'yu bir kez üretip iki farklı `kume_*.o` ile bağlamak yeter (Ders 7.17). Çünkü `ana.c`'nin derlenmiş kodu `struct Kume`'ın boyutuna ya da alanlarına hiç bağlı değil: sadece pointer'ları taşıyor ve fonksiyon çağırıyor.

Bu fazda aynı oyunu defalarca oynayacağız: "küme" arayüzünün arkasına sırayla ikili arama ağacı (8.8), dengeli ağaçlar (8.9, 8.10), hash tablosu (8.14, 8.15) koyulabilir. Her biri farklı bir maliyet tablosu:

| Uygulama | `icerir` | `ekle` | `sil` | Sıralı gezinme |
| --- | --- | --- | --- | --- |
| Sırasız dizi | $O(n)$ | $O(n)$ (kontrol yüzünden) | $O(n)$ | Yok |
| Sıralı dizi | $O(\log n)$ | $O(n)$ | $O(n)$ | Var, bedava |
| Dengeli ağaç (8.9) | $O(\log n)$ | $O(\log n)$ | $O(\log n)$ | Var |
| Hash tablosu (8.14) | $O(1)$ beklenen | $O(1)$ beklenen | $O(1)$ beklenen | Yok |

Hangisinin "en iyi" olduğu sorusu, kullanıcının hangi işlemleri ne sıklıkla yaptığına bağlı. ADT tasarımı, bu kararı **sonraya bırakmayı** ve ölçüme göre değiştirmeyi mümkün kılıyor.

---

## 5. Arayüz tasarımının kuralları

Küçük ama bütün faz boyunca uyacağımız birkaç karar:

- **İsim öneki.** C'de isim alanı (namespace) yok; her fonksiyon `kume_` ile başlıyor ki başka bir modülün `ekle`'siyle çakışmasın (Ders 7.17'deki "multiple definition").
- **Sahiplik açık.** `kume_olustur` bir nesne verir, onu `kume_yok_et` ile geri vermek **çağıranın** görevi. Her `_olustur`'un bir `_yok_et`'i var. `kume_yok_et(NULL)` güvenli, `free(NULL)` gibi.
- **Hata nasıl bildirilir?** `kume_ekle` `bool` döndürüyor; `false` "zaten vardı" ya da "bellek yetmedi" demek. İkisini ayırmak isteyen bir arayüz bir `enum` döndürürdü. Bu bir tasarım kararı; önemli olan belgelenmiş olması.
- **Gezinme sorunu.** Kullanıcı elemanları gezmek isterse ne olacak? Diziyi döndürmek içini açığa çıkarır. `kume_yazdir` bir geçici çözüm; doğru çözüm ya bir **geri çağırma** (callback, Ders 4.11) ya da bir **yineleyici** (iterator) nesnesi. Alıştırma 3.

### Opak olmanın bedeli

Her şeyin bir bedeli var. Opak tipte:

- Her nesne heap'te, her oluşturma bir `malloc` (Ders 4.22): yığında hızlıca bir tane oluşturamazsın.
- Her erişim bir fonksiyon çağrısı. Derleyici `kume_boyut`'u başka bir `.c` dosyasında olduğu için inline edemez (bağlama zamanı optimizasyonu, `-flto`, edebilir).

Bu yüzden küçük, sık kullanılan, değişmesi beklenmeyen tipler (bir 2B nokta, bir kesir) çoğu zaman **şeffaf** bırakılır, büyük ve karmaşık yapılar (bir dosya, bir hash tablosu, bir veritabanı bağlantısı) opak yapılır. C++'ta (Faz 13) `private` alanlar bu ikisinin arasında bir yol sunuyor: alanlar derleyiciye görünür (boyut bilinir, inline mümkün) ama kullanıcı koduna kapalı.

---

## Alıştırmalar

**1** – `kume_sirali.c`'ye bir `static bool degismez_tamam(const Kume *k)` fonksiyonu ekle: dizi kesin artan sırada mı ve `adet <= kapasite` mi? Her değiştiren fonksiyonun sonunda `assert(degismez_tamam(k))` çağır. Bu kontroller neden `kume_dizi.c`'de farklı olur?

**2** – `kume_birlesim(const Kume *a, const Kume *b)` yeni bir küme döndürsün. Sıralı uygulamada bunu $O(|a| + |b|)$ zamanda nasıl yaparsın? Sırasız uygulamada en iyi ne yapabilirsin?

**3** – Kullanıcının elemanları gezebilmesi için `void kume_her(const Kume *k, void (*f)(int x, void *ctx), void *ctx);` ekle. Bunu kullanarak 1'den 10'a kadar sayıların karelerinden oluşan bir kümenin elemanlarının toplamını hesapla. `ctx` parametresi ne işe yarıyor?

**4** – `kume.h`'yi değiştirmeden, `kume_boyut` çağrısını `kume_dizi.c` ve `kume_sirali.c`'de ayrı ayrı `printf` ile "çağrıldım" yazdıracak şekilde değiştirip `ana.o`'yu yeniden derlemeden iki uygulamayla bağla. Bu, Bölüm 4'teki "yeniden derlemeye gerek yok" iddiasını nasıl doğrular?

**5** – Bir arkadaşın "`kume.h`'ye `struct Kume { int *veri; size_t adet, kapasite; };` koyalım, kullanıcı `k->adet`'i doğrudan okusun, fonksiyon çağrısı maliyeti olmasın" diyor. Hangi durumlarda haklı? Hangi riskleri kabul etmiş olursunuz?

<details>
<summary>Cevaplar</summary>

**1** –

```c
#include <assert.h>
static bool degismez_tamam(const Kume *k) {
    if (k->adet > k->kapasite) return false;
    for (size_t i = 1; i < k->adet; i++)
        if (k->veri[i - 1] >= k->veri[i]) return false;   /* kesin artan: tekrar da yok */
    return true;
}
```

`kume_ekle` ve `kume_sil`'in her `return true`'sundan önce `assert(degismez_tamam(k));`. Kontrol $O(n)$, yani her işlemi $O(n)$ yapar; sadece test sırasında (`-DNDEBUG` olmadan) istenir. Sırasız uygulamada "artan" şartı yok; "tekrar yok" kontrolü ise sıralı dizideki gibi komşulara bakarak yapılamaz, her çifti karşılaştırmak gerekir: $O(n^2)$. Aynı değişmez, farklı uygulamada farklı maliyetle kontrol ediliyor; değişmezi sıralı uygulamada **ucuza kontrol edilebilir** kılan da sıralılık.

**2** – Sıralı: iki sıralı diziyi **birleştirme** (merge, Faz 9'daki merge sort'un kalbi). İki indeks `i`, `j`; küçük olanı sonuca ekle ve indeksini ilerlet, eşitse bir kez ekle ve ikisini ilerlet. Her eleman bir kez işleniyor: $O(|a| + |b|)$, ve sonuç zaten sıralı (ekleme fonksiyonuna gerek yok, doğrudan diziye yazılabilir; bu fonksiyon modülün içinde olduğu için `struct`'a erişebilir). Sırasız: `b`'nin her elemanı için `a`'da arama, $O(|a| \cdot |b|)$; ya da önce ikisini sıralamak, $O(n \log n)$. Bazı işlemlerin verimli yazılması iç yapıyı bilmeyi gerektiriyor; bu yüzden onlar ADT'nin **içinde** tanımlanır, dışarıda değil.

**3** – `kume_sirali.c`'ye:

```c
void kume_her(const Kume *k, void (*f)(int x, void *ctx), void *ctx) {
    for (size_t i = 0; i < k->adet; i++) f(k->veri[i], ctx);
}
```

Kullanım:

```c
static void topla(int x, void *ctx) { *(long *)ctx += x; }
/* ... */
for (int i = 1; i <= 10; i++) kume_ekle(k, i * i);
long s = 0;
kume_her(k, topla, &s);
printf("kareler toplami = %ld\n", s);
```

```
kareler toplami = 385
```

($1 + 4 + \dots + 100 = \frac{10 \cdot 11 \cdot 21}{6} = 385$, Ders 6.10.) `ctx` (bağlam) geri çağırma fonksiyonuna **kendi verisini** iletmenin yolu: `topla`'nın toplamı nereye yazacağını bilmesi gerekiyor, ama `kume_her` toplamdan habersiz. `void *` (Ders 4.9) sayesinde `kume_her` her türlü bağlamı taşıyabiliyor: bir sayaç, bir dosya, başka bir küme. Global değişken kullanmaktan çok daha temiz.

**4** – `cc -c ana.c` ile `ana.o`'yu bir kez üret. Sonra `cc ana.o kume_dizi.c` ve `cc ana.o kume_sirali.c`: iki program farklı mesajlar basar, ikisi de doğru çalışır, `ana.o` hiç değişmedi. Bunun mümkün olması `ana.o`'nun içinde `struct Kume` hakkında **hiçbir** bilgi (boyut, alan ofseti) olmamasından: sadece `kume_*` sembollerine çağrılar var, onlar da bağlamada çözülüyor (Ders 7.17). Paylaşımlı kütüphaneler (`.so`) bu özellik sayesinde, onları kullanan programları yeniden derlemeden güncellenebiliyor; buna **ABI uyumluluğu** denir.

**5** – Haklı olduğu durum: `kume_boyut` çok sık çağrılıyor, ölçümler (Faz 11) bunun gerçekten bir darboğaz olduğunu gösteriyor ve yapının uygulaması değişmeyecek. Kabul edilen riskler: (1) kullanıcı `k->adet = 0` yazarak değişmezi bozabilir (eleman dizide kaldı ama "yok" sayılıyor, ya da tersi); (2) uygulama ağaca ya da hash tablosuna geçerse `adet` alanı olmayabilir veya anlamı değişebilir, ve ona dokunan her kod kırılır; (3) `sizeof(Kume)` değişince her kullanıcının yeniden derlenmesi gerekir (Alıştırma 4'ün tersi). Orta yol: `static inline` erişim fonksiyonlarını başlıkta tanımlamak, ya da bağlama zamanı optimizasyonuyla (`-flto`) çağrı maliyetini kaldırmak.

</details>

---

## Kaynaklar

- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 4: soyut veri tipleri, istemci–arayüz–uygulama ayrımı.
- David Hanson, *C Interfaces and Implementations* (1996): C'de opak tiplerle arayüz tasarımının en kapsamlı kitabı; bu dersteki `_olustur`/`_yok_et` ve önek düzeni oradaki stile yakın.
- Barbara Liskov & Stephen Zilles, "Programming with Abstract Data Types" (ACM SIGPLAN Notices, 1974): ADT kavramının ilk tanımı.
- David Parnas, "On the Criteria To Be Used in Decomposing Systems into Modules" (CACM, 1972): bilgi gizleme (information hiding).

**Sıradaki ders:** Tek yönlü bağlı liste. Ekleme, silme, arama, ters çevirme; düğümleri kutu-ok diyagramıyla çizme.
