---
title: "4.28 Kendi allocator'ımız 1: arena"
description: "En basit allocator: büyük bir bloğu bir kez malloc edip içinden sırayla pay dağıtan bump/arena allocator. used işaretçisini ileri itmek, her ayırmayı hizaya yuvarlamak (align_up ve ikinin kuvveti bit hilesi), tek tek free yerine hepsini bir kerede sıfırlamak (reset), malloc'tan neden kat kat hızlı olduğu ve ne zaman doğru araç olduğu."
---

Ders 4.22'de `malloc` ve `free`'yi kullandık; nasıl çalıştıklarına hiç bakmadık. Bu derste ve sonrakinde kendi bellek ayırıcımızı (allocator) sıfırdan yazıyoruz. Bu derste en basiti: **arena** (ya da **bump**) allocator. Fikir o kadar basit ki tek bir toplama işlemi; ama belirli durumlarda `malloc`'tan kat kat hızlı, ve Ders 4.26'daki hizalamayı kendi elimizle uygulamamızı gerektiriyor.

Temel fikir: işletim sisteminden **bir kez** büyük bir blok al (Ders 4.22'deki `malloc`), sonra her istek geldiğinde o bloğun içinden sırayla bir parça ver, bir işaretçiyi (`used`) ileri **it** (bump). Serbest bırakma yok; iş bitince bütün bloğu tek seferde at.

---

## 1. Yapı ve ilk ayırma

```c
typedef struct {
    unsigned char *buffer;   // tek buyuk blok
    size_t capacity;         // toplam boyut
    size_t used;             // su ana kadar dagitilan
} Arena;

void arena_init(Arena *a, size_t capacity) {
    a->buffer = malloc(capacity);
    a->capacity = capacity;
    a->used = 0;
}
```

`buffer`, `malloc`'la alınan büyük blok (Ders 4.22); `used`, o bloğun ne kadarının dağıtıldığı. Her ayırma, `used`'dan itibaren bir parça verip `used`'ı ileri itiyor:

```c
void *arena_alloc(Arena *a, size_t size, size_t align) {
    size_t offset = align_up(a->used, align);
    if (offset + size > a->capacity) {
        return NULL;   // arena doldu
    }
    void *ptr = a->buffer + offset;
    a->used = offset + size;
    return ptr;
}
```

`align_up`'ı birazdan yazacağız. Gövdenin özü üç satır: ofseti bul, oradan `size` byte ayır, `used`'ı ileri it. Bu kadar — bir arama, bir liste, bir birleştirme yok. `malloc`'un karmaşıklığının (Ders 4.29'da göreceğiz) yanında neredeyse hiçbir şey.

`buffer`'ı `unsigned char *` seçtik, `void *` değil: Ders 4.9'dan, `void *` üzerinde aritmetik yapılamaz; `buffer + offset` için byte-byte ilerleyen bir tip gerekli.

---

## 2. Hizalama: align_up

Ders 4.26'dan: her tip kendi hizasında durmalı (`int` 4'ün katı, `double` 8'in katı). `malloc` bunu bizim için yapıyordu (en katı hizayı garanti ediyordu; Ders 4.26). Kendi allocator'ımızda bunu **biz** yapmak zorundayız: verdiğimiz her adres, istenen hizanın katı olmalı. Yoksa arena'dan aldığımız bir `double`, 8'in katı olmayan bir adrese düşebilir ve Ders 4.26'daki hizasız erişim sorununu yaratır.

`used`'ı bir sonraki hiza katına **yukarı yuvarlayan** fonksiyon:

```c
static size_t align_up(size_t n, size_t align) {
    return (n + align - 1) & ~(align - 1);
}
```

Bu bit hilesi (Ders 3.18) sadece `align` **ikinin kuvveti** olduğunda çalışıyor — ki bütün temel tiplerin hizası öyle (1, 2, 4, 8, 16). Nasıl çalıştığı:

- `align - 1`, alt bitleri 1 olan bir maske. `align = 4` için `3` = `...00011`.
- `n + align - 1`, `n`'yi bir sonraki katı **geçecek** kadar artırır.
- `& ~(align - 1)`, alt bitleri **sıfırlar**, yani kata **aşağı** yuvarlar. İkisi birlikte "yukarı yuvarla".

```
align_up(0,4)=0  align_up(1,4)=4  align_up(2,4)=4  align_up(3,4)=4
align_up(4,4)=4  align_up(5,4)=8  align_up(8,4)=8  align_up(9,4)=12
```

4'ün katı olanlar aynı kalıyor, aradakiler bir sonraki 4 katına çıkıyor. Örneğin bir `char` (1 byte, ofset 0'a) sonra bir `int` (hiza 4) ayırırsak:

```c
char *c = arena_alloc(&a, 1, 1);    // ofset 0
int *x = arena_alloc(&a, 4, 4);     // used=1, align_up(1,4)=4: ofset 4
```

```
c ofset=0
x ofset=4   (1 degil 4: hizalama bosluğu)
```

`char`'tan sonra `used` 1'di; `int` için `align_up(1, 4)` = 4, yani 1–3 arası 3 byte **boşa** gitti (Ders 4.26'daki dolgunun aynısı, bu sefer biz yapıyoruz). Bu, hizalamanın bedeli; karşılığında her değer doğru hizada.

Tip güvenli bir sarmalayıcı, Ders 4.27'deki `_Alignof` ile (hizayı elle yazmaya gerek kalmaz):

```c
#define ARENA_NEW(a, type) ((type *)arena_alloc((a), sizeof(type), _Alignof(type)))

int *x = ARENA_NEW(&a, int);
double *d = ARENA_NEW(&a, double);
```

Ölçtüğümüzde `x` 4'ün, `d` 8'in katı bir adreste çıkıyor: hizalama doğru.

---

## 3. Serbest bırakma: hepsi bir kerede

Arena'nın en radikal tarafı: **tek tek `free` yok.** Bir `arena_free` fonksiyonu yok; onun yerine ya hepsini birden sıfırla, ya da bütün bloğu at:

```c
void arena_reset(Arena *a) {
    a->used = 0;        // her seyi "serbest birak": sadece used'i sifirla
}

void arena_destroy(Arena *a) {
    free(a->buffer);    // tum blogu isletim sistemine geri ver
    a->buffer = NULL;
    a->capacity = a->used = 0;
}
```

`arena_reset`, `used`'ı 0 yapıyor — o kadar. Bir sonraki ayırma yine baştan başlar, eski veriyi üzerine yazar. Binlerce ayırma, tek bir `used = 0` ile "serbest" bırakılıyor. Ders 4.22'de her `malloc`'un bir `free`'si olmalı demiştik; arena bu kuralı **topluca** yerine getiriyor: tek tek değil, hepsi birden.

Bu, arena'nın hem gücü hem sınırı. Güç: serbest bırakma neredeyse bedava, ve bir bloğu unutup sızdırmak (Ders 4.22) imkânsız — ya hepsi yaşar ya hiçbiri. Sınır: **tek bir nesneyi** serbest bırakamazsın; arena'daki her şey aynı anda ölür. Bu yüzden arena, "bir işi yap, bitince hepsini at" kalıbına uyan durumlar için: bir web isteğini işlerken ayrılan geçici veriler (istek bitince `reset`), bir oyunun tek karesinde kullanılan geçici bellek (kare bitince `reset`), bir derleyicinin bir dosyayı ayrıştırırken kurduğu AST (Faz 8).

---

## 4. Ne kadar hızlı?

Beş milyon küçük ayırmayı `malloc`/`free` ile ve arena ile ölçtük:

```
malloc/free: 0.0110 s
arena:       0.0042 s  (2.6x)
```

Arena ~2,6 kat hızlı — ve bu sadece ayırma; `malloc` tarafında ayrıca her `free`'nin maliyeti de var, arena tarafında hiç `free` yok. Fark neden? `malloc`, hangi bloğun boş olduğunu bulmak için bir veri yapısında arama yapıyor, bloğu işaretliyor, `free`'de geri veriyor (Ders 4.29'da bunu yazacağız). Arena sadece bir toplama ve bir karşılaştırma yapıyor. Bu, "özel durum için özel araç" ilkesinin bir örneği: `malloc` **her** deseni (her boyut, her ömür, karışık `free` sırası) desteklemek zorunda; arena sadece "sırayla ayır, topluca at" desenini destekliyor ve o yüzden çok daha hızlı olabiliyor.

Bedeli: esneklik. Arena genel amaçlı değil. Ama uyduğu yerde hem hızlı hem güvenli (sızıntı yok, `free` sırası hatası yok, double free yok — Ders 4.23'teki hataların çoğu arena'da imkânsız). Pek çok yüksek performanslı program (oyun motorları, derleyiciler, veritabanları) `malloc`'u az kullanıp arena benzeri allocator'lara dayanır.

---

## Alıştırmalar

**1** – `align_up(n, 8)`'i `n` = 0, 1, 7, 8, 9, 16 için elle hesapla (`align - 1 = 7` maskesiyle). Sonra `align_up(n, 1)`'in her zaman `n` döndürdüğünü göster — 1 hizalı (yani her yere konabilen) tipler için neden boşluk olmuyor?

**2** – `arena_alloc`'ta `offset + size > a->capacity` kontrolünde, `offset + size` bir `size_t` toplaması. `size` çok büyükse (örneğin `(size_t)-1`) bu toplam taşıp küçük bir sayı olabilir ve kontrol yanlışlıkla geçebilir (Ders 3.8). Kontrolü taşmaya karşı güvenli hale getir (ipucu: `size > a->capacity - offset`).

**3** – Arena'dan ayrılmış bir pointer'ı `free` etmeye çalışırsan (`free(x)` — `x` `ARENA_NEW`'den geldi) ne olur? Neden undefined behavior? (İpucu: `free` sadece `malloc`'un döndürdüğü pointer'ları kabul eder; Ders 4.22.)

**4** – `arena_reset`'ten sonra eski pointer'lar (reset'ten önce `arena_alloc`'tan alınanlar) hâlâ geçerli mi? Reset'ten sonra onları kullanmak hangi Ders 4.23 hatasına benzer? Neden arena'da bu hatayı AddressSanitizer yakalayamaz (ipucu: bellek hâlâ `malloc`'un verdiği blok içinde)?

**5** – Bir `Arena`'nın kapasitesi dolduğunda `NULL` dönmek yerine **büyümesini** sağla: `arena_alloc` içinde yer yetmezse yeni, daha büyük bir blok `malloc` edip eskisini kopyala (`realloc` da olur). Bu neden tehlikeli — daha önce `arena_alloc`'tan dönen pointer'lara ne olur? (Ders 4.22'deki `realloc` taşınması.)

<details>
<summary>Cevaplar</summary>

**1** – `align_up(n, 8)`, maske `7`: `n=0`→0, `n=1`→`(1+7)&~7 = 8&~7 = 8`, `n=7`→`14&~7=8`, `n=8`→`15&~7=8`, `n=9`→`16&~7=16`, `n=16`→`23&~7=16`. Yani 8'in katları aynı, aradakiler bir sonraki 8 katına. `align_up(n, 1)`: `align - 1 = 0`, maske `~0` (bütün bitler 1), `(n + 0) & ~0 = n`. Her zaman `n`. 1 hizalı tipler (`char`) her adreste durabildiği için yuvarlamaya gerek yok, boşluk olmaz — bu yüzden `char` dizilerinde (string'ler) hiç hizalama kaybı yaşanmaz.

**2** –

```c
void *arena_alloc(Arena *a, size_t size, size_t align) {
    size_t offset = align_up(a->used, align);
    if (offset > a->capacity || size > a->capacity - offset) {
        return NULL;
    }
    void *ptr = a->buffer + offset;
    a->used = offset + size;
    return ptr;
}
```

`offset + size > capacity` yerine `size > capacity - offset` yazdık: artık toplama yok, dolayısıyla taşma yok. Ama `capacity - offset` da taşmasın diye önce `offset > capacity` kontrolü (align_up, `used`'ı `capacity`'nin üstüne çıkarmış olabilir). İki kontrol birlikte her durumda güvenli. Ders 3.8'deki "farkı değil, çıkarmayı kullan" kalıbı.

**3** – Undefined behavior, büyük ihtimalle çökme (double-free benzeri bir bozulma). `free`, sadece `malloc`/`calloc`/`realloc`'un döndürdüğü bir pointer'ı kabul eder (Ders 4.22). `x`, arena'nın `buffer`'ının **ortasında** bir adres; `malloc` ona hiç böyle bir blok vermedi. `free(x)`, `malloc`'un o adresin hemen öncesinde tuttuğunu sandığı yönetim bilgisini (Ders 4.29) çöp olarak okur ve iç yapısını bozar. Arena'dan ayrılan hiçbir şey `free` edilmez; sadece `arena_destroy` tek bir `free(buffer)` yapar.

**4** – Reset'ten sonra eski pointer'lar teknik olarak hâlâ aynı belleği gösterir, ama **mantıken geçersiz**: bir sonraki `arena_alloc` aynı yeri başka bir şeye verip üzerine yazacak. Onları kullanmak Ders 4.23'teki **use-after-free**'ye benzer (ömrü bitmiş belleği kullanmak). AddressSanitizer bunu yakalayamaz, çünkü bellek hâlâ `malloc`'un verdiği `buffer` bloğunun **içinde** ve o blok hâlâ geçerli — ASan "bu adres ayrılmış bir blokta mı?" diye bakar, "bu adres arena'nın mantığına göre hâlâ canlı mı?" diye bakamaz. Kendi allocator'ını yazmanın bedeli bu: ASan'ın `malloc` için verdiği korumayı kaybedersin; arena'nın kendi kurallarını kendin uygulamak zorundasın.

**5** – Arena'yı büyütmek için yeni bir blok ayırıp eskisini taşırsan, daha önce `arena_alloc`'tan dönen **bütün** pointer'lar geçersizleşir — eski `buffer` taşındıysa (Ders 4.22'deki `realloc` taşınması) hepsi sallanan pointer olur. Bu, arena'nın temel sözünü bozar: "verdiğim pointer'lar `reset`/`destroy`'a kadar geçerli". Çözüm, tek bir bloğu büyütmek yerine **blokları zincirlemek**: yer yetmeyince yeni bir blok `malloc` edip eskisini korumak, yeni ayırmaları yeni bloktan vermek. Böylece eski pointer'lar eski blokta geçerli kalır. Çoğu gerçek arena uygulaması (ve Faz 8'deki kullanımımız) bu "blok listesi" yaklaşımını kullanır; `reset`/`destroy` bütün blokları dolaşır.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §8.7: bir `malloc` uygulaması (sonraki derste).
- Per-Åke Larson ve ark.; ayrıca Ryan Fleury, "Untangling Lifetimes: The Arena Allocator": arena deseni ve ömür yönetimi.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §9.9: ayırıcı tasarımı.
- C standardı (ISO/IEC 9899:2018), §6.5.3.4 (`_Alignof`), §7.22.3 (`malloc` ailesinin pointer sözleşmesi).

**Sıradaki ders:** Kendi allocator'ımız 2. Serbest liste ile `malloc`/`free`, K&R §8.7 ve birleştirme (coalescing).
