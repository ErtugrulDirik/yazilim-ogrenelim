---
title: "4.29 Kendi allocator'ımız 2: serbest liste"
description: "Gerçek bir malloc/free: her bloğun önünde boyut ve 'boş mu' tutan bir başlık, blokların bir liste oluşturması, malloc'un ilk yeten boş bloğu bulup gerekirse bölmesi, free'nin bloğu boş işaretleyip verinin önündeki başlığı bulması, ardışık boş blokları birleştirmek (coalescing) ve parçalanma. K&R §8.7'nin basitleştirilmiş hali."
---

Ders 4.28'de arena allocator'ı yazdık: hızlı ama tek tek serbest bırakma yok. Bu derste **gerçek** bir `malloc`/`free` yazıyoruz — herhangi bir bloğu, herhangi bir sırada serbest bırakabilen. Ders 4.22'de kullandığımız `malloc`'un, Ders 4.23'teki hataların, Ders 4.28'deki hız farkının altında yatan mekanizma bu. K&R'ın §8.7'deki ünlü allocator'ının basitleştirilmiş bir hali.

Arena'dan farkı: serbest bırakılan bloğu **tekrar kullanabilmek** gerekiyor. Bunun için her bloğun ne kadar büyük olduğunu ve boş olup olmadığını bir yerde saklamalıyız.

---

## 1. Başlık: her bloğun önünde gizli bilgi

Her bloğun **önüne** küçük bir başlık koyuyoruz:

```c
typedef struct Block {
    size_t size;          // yararli veri boyutu (baslik haric)
    int free;             // bos mu?
    struct Block *next;   // bir sonraki blok
} Block;
```

Bellek şöyle görünüyor: `[başlık][kullanıcı verisi][başlık][kullanıcı verisi]...`. `my_malloc`, kullanıcıya başlıktan **sonrasını** verir; `my_free`, verilen adresin hemen önündeki başlığı okur. Bu, `malloc`'un gerçekten yaptığı şey: Ders 4.23'te "sınır dışı yazma `malloc`'un yönetim bilgisini bozabilir" dediğimizde, bozulan tam bu başlıklardı. Ders 4.28'de "arena pointer'ını `free` etmek çöker" dediğimizde, `free`'nin verinin önünde bir başlık araması buydu.

Bütün belleğimiz tek bir sabit dizi (gerçek `malloc` işletim sisteminden ister; biz basitlik için statik bir dizi kullanıyoruz):

```c
#define ALIGN 8
static size_t align_up(size_t n) { return (n + ALIGN - 1) & ~((size_t)ALIGN - 1); }

static unsigned char heap[4096];
static Block *head;

void my_init(void) {
    head = (Block *)heap;
    head->size = sizeof(heap) - sizeof(Block);
    head->free = 1;
    head->next = NULL;
}
```

Başlangıçta tek bir büyük boş blok: 4096 − `sizeof(Block)` = 4072 byte kullanılabilir (`sizeof(Block)` bu makinede 24; Ders 4.26'daki dolguyla).

```
baslangic:
  blok0: size=4072 BOS
```

---

## 2. my_malloc: ilk yeten bloğu bul, gerekirse böl

```c
void *my_malloc(size_t size) {
    size = align_up(size);
    for (Block *b = head; b != NULL; b = b->next) {
        if (b->free && b->size >= size) {
            if (b->size >= size + sizeof(Block) + ALIGN) {
                Block *rest = (Block *)((unsigned char *)(b + 1) + size);
                rest->size = b->size - size - sizeof(Block);
                rest->free = 1;
                rest->next = b->next;
                b->size = size;
                b->next = rest;
            }
            b->free = 0;
            return b + 1;
        }
    }
    return NULL;
}
```

İki adım:

**İlk yeten bloğu bul** (first-fit): listeyi baştan gez, boş ve yeterince büyük ilk bloğu seç. (Başka stratejiler de var: best-fit, en küçük yeten blok; first-fit en basiti ve K&R'ın seçimi.)

**Gerekirse böl** (split): bulunan blok istenenden çok büyükse, kalanını **yeni bir boş blok** yap. Yoksa 100 byte isteyip 4072 byte'lık bloğu verseydik, 3972 byte boşa giderdi. Bölme koşulu `b->size >= size + sizeof(Block) + ALIGN`: kalanda en az bir başlık + biraz veri sığacaksa böl; sığmayacaksa bütün bloğu ver (küçük bir iç parçalanma). `b + 1`, başlığın hemen sonrası — Ders 4.6'daki pointer aritmetiği (`Block *` üzerinde `+1`, bir `Block` ileri = başlığı atla).

Üç ayırma yapalım:

```c
int *a = my_malloc(10 * sizeof(int));   // 40 byte
char *b = my_malloc(100);               // 104'e yuvarlanir
double *c = my_malloc(5 * sizeof(double)); // 40 byte
```

```
3 ayirma sonrasi:
  blok0: size=40 dolu
  blok1: size=104 dolu
  blok2: size=40 dolu
  blok3: size=3816 BOS
```

İlk büyük blok üç kez bölündü; her ayırma başından bir parça aldı, kalan sona itildi. `100` istenince `104`'e yuvarlandı (align 8). Hizalamayı kontrol edelim:

```
hizalar: a%8=0 b%8=0 c%8=0
```

Üçü de 8 hizalı. `sizeof(Block)` 24 (8'in katı) ve `heap` 8 hizalı başladığı için, her `b + 1` otomatik olarak 8 hizalı — Ders 4.28'deki hizalama sorununu başlığın boyutunu 8'in katı tutarak çözdük.

---

## 3. my_free: bloğu boşalt ve birleştir

```c
void my_free(void *ptr) {
    if (ptr == NULL) {
        return;          // free(NULL) guvenli (Ders 4.23)
    }
    Block *b = (Block *)ptr - 1;   // baslik, verinin hemen onunde
    b->free = 1;
    // Birlestirme (coalescing)
    for (Block *c = head; c != NULL; c = c->next) {
        while (c->free && c->next != NULL && c->next->free) {
            c->size += sizeof(Block) + c->next->size;
            c->next = c->next->next;
        }
    }
}
```

İki adım:

**Bloğu boş işaretle.** `(Block *)ptr - 1`, kullanıcının verisinin hemen önündeki başlığı buluyor (Ders 4.6; `my_malloc`'un `b + 1` döndürmesinin tersi). `free = 1` yapmak yeterli — veri hâlâ orada, ama blok artık tekrar kullanılabilir.

**Birleştir** (coalescing). Sadece boş işaretlemek yetmez: yan yana iki boş blok kalırsa, aralarında yapay bir sınır olur ve büyük bir istek, ikisinin toplamı yetse bile reddedilir. Birleştirme, **ardışık** boş blokları tek bir büyük boş bloğa çeviriyor. Bir bloğu serbest bırakalım, sonra komşusunu:

```c
my_free(b);
```
```
b serbest:
  blok0: size=40 dolu
  blok1: size=104 BOS
  blok2: size=40 dolu
  blok3: size=3816 BOS
```

`b` boş oldu ama komşuları dolu, birleşme yok. Şimdi `a`'yı da bırakalım:

```c
my_free(a);
```
```
a serbest (a ile b birlesmeli):
  blok0: size=168 BOS
  blok1: size=40 dolu
  blok2: size=3816 BOS
```

`a` (40) ve `b` (104) artık ardışık ve ikisi de boş; birleştiler: 40 + 24 (aradaki başlık artık veri) + 104 = **168**. İki blok tek oldu. Son olarak `c`'yi bırakınca her şey tek bloğa döner:

```
hepsi serbest (tek blok):
  blok0: size=4072 BOS
```

Başlangıçtaki 4072'ye geri döndük. Birleştirme olmasaydı, hepsini serbest bıraksak bile bellek küçük parçalara bölünmüş kalır ve büyük bir istek başarısız olurdu.

---

## 4. Parçalanma

Birleştirmeye rağmen bir sorun kalıyor: **parçalanma** (fragmentation). Toplam boş bellek yeterli olsa bile, **ardışık** boş bellek yetmeyebilir. Örneğin 40, 40, 40 byte'lık üç blok ayırıp ortadakini serbest bırakırsak, 40 byte boşumuz var ama 80 byte'lık bir istek, o 40 iki dolu bloğun arasında sıkıştığı için başarısız olur. Birleştirme sadece **ardışık** boşları toplayabilir; arada dolu bir blok varsa yapacak bir şey yok.

Bu, `malloc` tabanlı her sistemin temel sorunu. Çözümler kısmi: farklı boyutlar için farklı listeler (segregated free lists), blokları taşıyıp sıkıştırmak (compaction — ama C'de pointer'lar sabit olduğu için zor), ya da Ders 4.28'deki arena gibi hiç tek tek serbest bırakmamak. Gerçek `malloc` uygulamaları (glibc'nin ptmalloc'u, jemalloc, mimalloc) bu stratejilerin karmaşık karışımları; ama hepsinin çekirdeğinde bu derste yazdığımız fikir var: **başlıklı bloklar, boş liste, bölme ve birleştirme.**

Bizim sürümümüz basit ve yavaş (her `malloc` listeyi baştan gezer — $O(n)$; her `free` birleştirme için tüm listeyi gezer). Ama Ders 4.22'deki `malloc`'un ne yaptığını, Ders 4.23'teki hataların neden bellek bozulmasına yol açtığını, Ders 4.28'deki arena'nın neden daha hızlı olabildiğini artık içeriden biliyoruz.

---

## Alıştırmalar

**1** – `my_malloc`'taki bölme koşulu `b->size >= size + sizeof(Block) + ALIGN`. `+ ALIGN` olmasaydı (sadece `size + sizeof(Block)`), kalan blok 0 byte veri taşıyan bir başlık olabilirdi. Neden sıfır byte'lık bir boş blok işe yaramaz, hatta zararlı? (İpucu: bir sonraki `my_malloc` onu "bulur" ama kullanamaz.)

**2** – `my_free`'de başlığı `(Block *)ptr - 1` ile buluyoruz. Kullanıcı `my_malloc`'un döndürdüğü pointer'ı değil de, onun **içinde** bir adresi (`a + 2`) `my_free`'e verirse ne olur? Gerçek `malloc` neden bunu da (Ders 4.23'teki gibi) yakalayamaz?

**3** – first-fit yerine **best-fit** (en küçük yeten boş blok) uygula: listeyi sonuna kadar gez, en küçük uygun bloğu seç. Parçalanma açısından avantajı/dezavantajı ne? Hız açısından?

**4** – Bölme sonrası iki blok oluyor ama birleştirme tüm listeyi gezen bir döngü. Birleştirmeyi daha verimli yapmak için başlığa bir `struct Block *prev` (çift yönlü liste) eklersen, serbest bırakılan bloğun **soldaki** komşusuyla birleşmesi nasıl kolaylaşır? (Şu an sadece sağdakiyle kolay birleşiyor.)

**5** – Bu allocator'ı Ders 4.22'deki sızıntı testine tabi tut: 100 kez `my_malloc` yapıp hiç `my_free` etme, sonra `dump` ile boş blok kaldı mı bak. Sonra hepsini `my_free` et ve tek bloğa döndüğünü doğrula. valgrind bu sızıntıyı neden **yakalayamaz** (ipucu: bellek tek bir statik diziden geliyor, `malloc`'tan değil)?

<details>
<summary>Cevaplar</summary>

**1** – `+ ALIGN` olmasaydı, kalan blok `size=0` olabilir: sadece bir başlık, hiç veri. Bir sonraki `my_malloc`, bu bloğu listede görür (`b->free && b->size >= size` kontrolünde `size=0` hiçbir isteğe yetmez, atlanır) ama hiçbir işe yaramaz — listeyi uzatır, her gezişte zaman kaybettirir, ve `free = 1` olduğu için birleştirmeye kadar orada kalır. Daha kötüsü, `size + sizeof(Block)` tam sığarsa `size=0`'lık bir blok oluşur ama birleşemez (komşusu dolu olabilir). `+ ALIGN`, "kalanda en az bir anlamlı ayırma yapılabilecekse böl, yoksa bütün bloğu ver" diyor; küçük bir iç parçalanmayı (bütün bloğu vermek) kabul edip işe yaramaz blok üretmekten kaçınıyor.

**2** – `my_free(a + 2)` çağrılırsa, `(Block *)(a + 2) - 1` yanlış bir adresi başlık sanar: `a`'nın verisinin ortasındaki byte'ları `size`, `free`, `next` olarak okur — çöp değerler. `b->free = 1` rastgele bir yere yazar, sonraki birleştirme döngüsü çöp `next` pointer'ını takip edip çöker ya da belleği bozar. Gerçek `malloc` da bunu güvenilir biçimde yakalayamaz, çünkü Ders 4.22'deki pointer sözleşmesi: `free`, **yalnızca** `malloc`'un döndürdüğü pointer'ı kabul eder; başka bir şey vermek undefined behavior. Başlığı bulmak için pointer'dan sabit bir ofset geri gitmek, verilen pointer'ın gerçekten bir blok başlangıcı olduğuna **güvenir** — kontrol etmenin ucuz bir yolu yok.

**3** –

```c
void *my_malloc_bestfit(size_t size) {
    size = align_up(size);
    Block *best = NULL;
    for (Block *b = head; b != NULL; b = b->next) {
        if (b->free && b->size >= size) {
            if (best == NULL || b->size < best->size) {
                best = b;
            }
        }
    }
    if (best == NULL) return NULL;
    // ... bolme ve isaretleme (first-fit'teki gibi) ...
}
```

Best-fit **parçalanmayı azaltabilir**: en küçük yeten bloğu seçtiği için büyük boş blokları büyük istekler için saklar, küçük istekleri küçük boşluklara yerleştirir. Dezavantajı: çok küçük, kullanılamayacak kadar ufak artıklar (slivers) bırakabilir, ve **daha yavaş** — her ayırma listenin **tamamını** gezmek zorunda (first-fit ilk uygunu bulunca durur). Pratikte first-fit ve best-fit'in parçalanma farkı çoğu iş yükünde küçüktür; bu yüzden basit ve hızlı olan first-fit (ya da onun bir çeşidi next-fit) yaygındır.

**4** – Şu an birleştirme listeyi baştan gezip her boş bloğun **sağındaki** (`next`) boş komşusuyla birleşiyor; bir bloğu serbest bırakınca onun **solundaki** komşuyla birleşmek için listeyi baştan taramak gerekiyor. `prev` eklersek (çift yönlü liste), serbest bırakılan `b` için doğrudan `b->prev`'e bakıp "soldaki komşum boş mu?" diye sorabiliriz — listeyi gezmeden, $O(1)$. Böylece `my_free`, hem `b->next` hem `b->prev` ile yerinde birleşir, tüm listeyi gezen döngüye gerek kalmaz. K&R'ın allocator'ı adresa göre sıralı dairesel bir liste kullanarak benzer bir kolaylık sağlar. (Daha da hızlısı: her bloğun **sonuna** da bir boyut etiketi — "boundary tag" — koyup soldaki komşunun başlığını bulmak; Knuth'un yöntemi.)

**5** – 100 `my_malloc` sonrası `dump`, dolu blokları ve (varsa) kalan boş bloğu gösterir — sızıntı burada "boş'a dönmeyen dolu bloklar" olarak görünür. Hepsini `my_free` edince birleştirme tek bloğa (4072) döndürür. valgrind bu sızıntıyı **yakalayamaz**, çünkü valgrind gerçek `malloc`/`free` çağrılarını izler (Ders 4.22); bizim belleğimiz `static unsigned char heap[4096]` adlı bir **global diziden** geliyor (Ders 4.21'deki bss), hiç `malloc` çağrılmıyor. valgrind için ortada ayrılmış bellek yok, sadece bir global dizi var; onun içindeki mantıksal sızıntıyı göremez. Kendi allocator'ını yazınca, Ders 4.28'deki gibi, araçların `malloc` için verdiği denetimi kaybedersin — kendi `dump`'ını yazıp kendin kontrol etmen gerekir.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §8.7: "A Storage Allocator" — başlıklı bloklar ve serbest liste.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, §2.5: ayırma stratejileri (first-fit, best-fit, boundary tags, birleştirme).
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §9.9: örtük ve açık serbest listeler, parçalanma.
- Doug Lea, "A Memory Allocator" (dlmalloc): gerçek bir `malloc`'un tasarımı.

**Sıradaki ders:** Faz projesi — libmystr. Kendi string kütüphanemiz, test programı, statik kütüphane (`ar`) ve Makefile.
