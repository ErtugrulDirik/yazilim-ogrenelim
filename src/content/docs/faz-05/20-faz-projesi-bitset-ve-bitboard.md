---
title: "5.20 Faz projesi: bitset ve bitboard"
description: "Faz 5'in bitiş projesi: bu fazın tekniklerini birleştiren iki yapı. Bir bitset kütüphanesi — kelime dizisiyle keyfi boyutlu bit kümeleri, set/clear/test (5.2), popcount ile sayma (5.8), ctz + x&(x-1) ile set bitler üzerinde gezinme (5.3/5.9). Ve bir satranç bitboard'u — 64 kareyi bir uint64_t'de tutup at hamlelerini tek bir dalsız kaydırma-maske ifadesiyle 64 kareye birden üretmek, tüm karelerde doğrulanmış."
---

Faz 5'in sonuna geldin. Bu fazda bitlerle hesabın bütün araçlarını topladık. Bu projede ikisini bir araya getiren iki gerçek yapı kuruyoruz: genel amaçlı bir **bitset kütüphanesi** ve bir satranç **bitboard'u**. İkisi de "bir sayı, bir bit kümesidir" (Ders 5.2) fikrinin doğal sonucu, ve bu fazdaki her tekniği — maskeler, popcount, ctz, dalsız kod — pratikte kullanıyor.

:::tip[Önce kendin yaz]
Bu bir proje dersi. Yapıları ve işlemleri okuduktan sonra **kendi çözümünü yaz**. Bizim çözümümüz aşağıda, kapalı kutularda. Takıldığın yerde ilgili fonksiyona bak.
:::

---

## 1. Bitset: keyfi boyutlu bit kümesi

Ders 5.2'de bir `uint32_t`'de 32 bayrak tuttuk; bir `uint64_t`'de 64. Ya 1000 bayrak gerekiyorsa? Bir **kelime dizisi** (array of words): her `uint64_t` 64 bit, `n` bit için `⌈n/64⌉` kelime (Ders 5.7'deki yukarı yuvarlama).

```c
#define BITS_PER_WORD 64
typedef struct {
    uint64_t *words;
    size_t nbits;
    size_t nwords;
} Bitset;

void bs_init(Bitset *b, size_t nbits) {
    b->nbits = nbits;
    b->nwords = (nbits + BITS_PER_WORD - 1) / BITS_PER_WORD;   // Ders 5.7
    b->words = calloc(b->nwords, sizeof(uint64_t));            // sifirla (Ders 4.22)
}
```

`i`. bit, `words[i / 64]` kelimesinin `i % 64`. bitinde. Ders 5.7'den: 64 bir 2'nin kuvveti, `i / 64 == i >> 6`, `i % 64 == i & 63` — derleyici bunları kaydırma ve maskeye çevirir. Temel işlemler Ders 5.2'nin kelime dizisine taşınmış hali:

```c
void bs_set(Bitset *b, size_t i)   { b->words[i/64] |= (uint64_t)1 << (i%64); }
void bs_clear(Bitset *b, size_t i) { b->words[i/64] &= ~((uint64_t)1 << (i%64)); }
int  bs_test(const Bitset *b, size_t i) { return (b->words[i/64] >> (i%64)) & 1; }
```

### Saymak ve gezmek

Kaç bit set? Her kelimenin popcount'unu topla (Ders 5.8):

```c
size_t bs_count(const Bitset *b) {
    size_t c = 0;
    for (size_t w = 0; w < b->nwords; w++) {
        c += __builtin_popcountll(b->words[w]);
    }
    return c;
}
```

Set bitlerin **üzerinde gezmek** (hepsini ziyaret etmek) ise Ders 5.3 ve 5.9'un güzel birleşimi: her kelimede, en sağdaki 1'i `ctz` ile bul, işle, sonra `x & (x-1)` ile sil, tekrarla:

```c
void bs_foreach(const Bitset *b, void (*fn)(size_t)) {
    for (size_t w = 0; w < b->nwords; w++) {
        uint64_t x = b->words[w];
        while (x) {
            int i = __builtin_ctzll(x);   // en sagdaki 1'in konumu (Ders 5.9)
            fn(w * 64 + i);                // o biti isle
            x &= x - 1;                    // en sagdaki 1'i sil (Ders 5.3)
        }
    }
}
```

Bu döngü **set bit sayısı** kadar döner (bit sayısı kadar değil; Ders 5.3'teki Kernighan) — seyrek bir bitset'te çok hızlı. `while (x)` koşulu, `ctz(0)`'ın tanımsızlığından (Ders 5.9) korur: `x` sıfırsa hiç girilmez. Çalışırken:

```
count=4  set bitler: 3 64 100 199
```

4 bit set edildi (3, 64, 100, 199), `bs_foreach` hepsini sırayla ziyaret etti — fonksiyon pointer'ı (Ders 4.11) ile her birine `print_idx` uygulandı.

<details>
<summary>bitset.c (tam)</summary>

```c
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#define BITS_PER_WORD 64
typedef struct { uint64_t *words; size_t nbits; size_t nwords; } Bitset;

void bs_init(Bitset *b, size_t nbits) {
    b->nbits = nbits;
    b->nwords = (nbits + BITS_PER_WORD - 1) / BITS_PER_WORD;
    b->words = calloc(b->nwords, sizeof(uint64_t));
}
void bs_free(Bitset *b) { free(b->words); b->words = NULL; }
void bs_set(Bitset *b, size_t i)   { b->words[i/64] |= (uint64_t)1 << (i%64); }
void bs_clear(Bitset *b, size_t i) { b->words[i/64] &= ~((uint64_t)1 << (i%64)); }
int  bs_test(const Bitset *b, size_t i) { return (b->words[i/64] >> (i%64)) & 1; }
size_t bs_count(const Bitset *b) {
    size_t c = 0;
    for (size_t w = 0; w < b->nwords; w++) c += __builtin_popcountll(b->words[w]);
    return c;
}
void bs_foreach(const Bitset *b, void (*fn)(size_t)) {
    for (size_t w = 0; w < b->nwords; w++) {
        uint64_t x = b->words[w];
        while (x) {
            int i = __builtin_ctzll(x);
            fn(w * 64 + i);
            x &= x - 1;
        }
    }
}
```

Küme işlemleri (birleşim, kesişim, fark) kelime kelime `|`, `&`, `& ~` ile eklenebilir (1. alıştırma) — Ders 5.2'deki bayrak işlemlerinin dizi hali.

</details>

---

## 2. Bitboard: satranç tahtası bir uint64_t

Satranç tahtası 8×8 = 64 kare. Tam bir `uint64_t`'nin bit sayısı. **Bitboard**, her kareyi bir bit yapar: `a1 = 0`, `b1 = 1`, …, `h8 = 63`. Bir taşın konumu, bir satır taşın yeri, saldırılan kareler — hepsi birer 64-bit sayı, ve işlemler bit işlemleri. Modern satranç motorlarının (Stockfish) temeli bu.

En güzel örnek **at hamleleri**. Bir atın gidebileceği 8 kareyi, her kare için ayrı ayrı hesaplamak yerine, **tek bir dalsız ifadeyle** üretiyoruz — hem de aynı anda tahtadaki **bütün** atlar için. Atın 8 hamlesi, konumdan belirli kaydırmalarla elde edilir; kenar taşmalarını maskelerle (Ders 5.2) engelleriz:

```c
#define FILE_A 0x0101010101010101ull   // a sutunu
#define FILE_B 0x0202020202020202ull
#define FILE_G 0x4040404040404040ull
#define FILE_H 0x8080808080808080ull

uint64_t knight_attacks(uint64_t knights) {
    uint64_t l1 = (knights >> 1) & ~FILE_H;          // 1 sol
    uint64_t l2 = (knights >> 2) & ~(FILE_G | FILE_H); // 2 sol
    uint64_t r1 = (knights << 1) & ~FILE_A;          // 1 sag
    uint64_t r2 = (knights << 2) & ~(FILE_A | FILE_B); // 2 sag
    uint64_t h1 = l1 | r1;
    uint64_t h2 = l2 | r2;
    return (h1 << 16) | (h1 >> 16) | (h2 << 8) | (h2 >> 8);
}
```

At L şeklinde gider: iki yatay bir dikey, ya da bir yatay iki dikey. `<< 1`/`>> 1` bir kare yana, `<< 8`/`>> 8` bir kare yukarı/aşağı (bir satır = 8 bit), `<< 16`/`>> 16` iki satır. `h1` (bir yatay) iki satır (`<< 16`, `>> 16`) ile, `h2` (iki yatay) bir satır (`<< 8`, `>> 8`) ile birleşince 8 hamle çıkar. Maskeler (`~FILE_H` vb.) atın tahtanın kenarından "sarıp" diğer taraftan çıkmasını engeller (Ders 5.2; kaydırma bitleri komşu satıra taşıyabilir).

At d4'te (kare 27):

```
Gidebilecegi kareler (8 tane):
. . # . # . . .
. # . . . # . .
. . . . . . . .
. # . . . # . .
. . # . # . . .
```

Klasik at deseni — 8 kare, hiç dal (`if`) yok, hiç döngü yok. Köşedeki bir at (a1) 2, kenardaki 3-4, merkezdeki 8 hamleye sahip; bütün 64 kareyi bir referansla doğruladık:

```
64 kare dogrulama: 0 hata, toplam hamle=336
```

336, bir atın bir satranç tahtasındaki toplam hamle sayısının bilinen değeri. `knight_attacks`'in gücü: tek bir atı değil, bir `uint64_t`'deki **bütün** atları aynı anda işler — tahtadaki her at için hamle üretmek yine tek bir fonksiyon çağrısı. SWAR'ın (Ders 5.8) satranca uygulanmış hali: 64 kareyi paralel işlemek.

<details>
<summary>Neden bitboard?</summary>

Bir satranç motorunun saniyede milyonlarca pozisyon değerlendirmesi gerekir. Bitboard'la:
- **Hamle üretimi** dalsız, paralel (yukarıdaki gibi).
- **"Kaç taş var?"** = `popcount` (Ders 5.8), tek komut.
- **"Hangi karelerde?"** = `ctz` ile gezinme (Bölüm 1'deki `bs_foreach`), set bit sayısı kadar adım.
- **"İki taş aynı karede mi?"**, **"bu kare saldırı altında mı?"** = `&`, `|` ile tek işlem.

8×8'lik bir diziyle (Ders 4.3) her sorgu bir döngü olurdu; bitboard'la çoğu sorgu tek bir 64-bit işlem. Fil/kale/vezir hamleleri daha karmaşık (engelleyen taşlar; "magic bitboards" denen, Ders 5.14'teki sihirli sayıların akrabası bir teknikle), ama at ve şah hamleleri tam da buradaki gibi saf kaydırma-maske.

</details>

---

## Faz 5 bitti

Bu fazda bitlerle hesabın sanatını öğrendik: operatörlerden (5.1) maskelere (5.2), en sağdaki bit formüllerinden (5.3) aritmetik–mantık köprüsüne (5.4), dalsız koddan (5.5) taşma ve döndürmeye (5.6), 2'nin kuvvetlerinden (5.7) popcount ve pariteye (5.8), sıfır saymadan (5.9) word-at-a-time'a (5.10), bit yeniden düzenlemeden (5.11) compress/expand'e (5.12), çarpma/bölme algoritmalarından (5.13) sabite bölmeye (5.14), tamsayı fonksiyonlarından (5.15) Gray kodu ve alışılmadık tabanlara (5.16), uzay doldurma eğrilerinden (5.17) float bit hilelerine (5.18), CRC ve Hamming'den (5.19) bu projeye (5.20).

İki tema boyunca tekrarlandı. Biri: **bir sayı, yorumuna göre farklı şeydir** — bir tamsayı, bir bit kümesi, bir float'ın bitleri, bir koordinat çifti, bir satranç tahtası. Diğeri: **derleyici bu hilelerin çoğunu zaten biliyor** — popcount `popcnt`'e, rotate `ror`'a, `/3` çarpmaya, `max` `csel`'e dönüşür; biz hileleri *neden* işe yaradıklarını anlamak için, derleyici *hız* için kullanıyor. Bu iki kavrayış, Faz 7'de assembly'ye, Faz 11'de SIMD'e geçtiğimizde temel olacak.

Bir sonraki faz **matematik temelleri, sayı teorisi ve soyut cebir**: bu fazdaki GF(2) (CRC), modüler aritmetik (sabite bölme) ve Boole cebiri (bit işlemleri) sezgilerinin üzerine, ispatlı bir matematik kurulacak.

---

## Alıştırmalar

**1** – Bitset'e küme işlemleri ekle: `bs_or` (birleşim), `bs_and` (kesişim), `bs_andnot` (fark). Her biri kelime kelime hangi operatörü kullanır (Ders 5.2)? İki bitset'in **aynı boyutta** olduğunu nasıl garanti edersin?

**2** – `bs_foreach`'i bir fonksiyon pointer'ı yerine, "bir sonraki set biti" döndüren bir **yineleyici** (`bs_next(b, from)`) olarak yeniden tasarla. `ctz` (Ders 5.9) ile nasıl yazarsın? Hangisi daha esnek — callback mi iterator mu?

**3** – Satrançta **şah** hamlelerini (8 komşu kare) üreten `king_attacks(uint64_t kings)` yaz. At'a göre daha basit; hangi kaydırmalar (`<< 1`, `<< 7`, `<< 8`, `<< 9` ve tersleri) ve hangi dosya maskeleri gerekir?

**4** – `knight_attacks`'teki maskelerin (`~FILE_H` vb.) ne engellediğini göster: maskesiz, a-dosyasındaki bir atı `>> 1` ile kaydırırsan taş nereye "sarar"? `d4` atı yerine `a1` atını maskesiz işleyip bozuk çıktıyı gözle.

**5** – Bitset ve bitboard'ı Ders 4.3'teki 8×8 dizi (`int board[8][8]`) yaklaşımıyla karşılaştır. "Kaç taş var", "bütün taşların karelerini listele", "bu kare dolu mu" sorguları için her biri ne kadar iş yapar (bellek, işlem sayısı)? Bitboard ne zaman kazanır, dizi ne zaman daha okunur?

<details>
<summary>Cevaplar</summary>

**1** –

```c
void bs_or(Bitset *dst, const Bitset *a, const Bitset *b) {
    for (size_t w = 0; w < dst->nwords; w++) dst->words[w] = a->words[w] | b->words[w];
}
void bs_and(Bitset *dst, const Bitset *a, const Bitset *b) {
    for (size_t w = 0; w < dst->nwords; w++) dst->words[w] = a->words[w] & b->words[w];
}
void bs_andnot(Bitset *dst, const Bitset *a, const Bitset *b) {
    for (size_t w = 0; w < dst->nwords; w++) dst->words[w] = a->words[w] & ~b->words[w];
}
```

Birleşim `|`, kesişim `&`, fark `& ~` — Ders 5.2'deki bayrak işlemlerinin kelime kelime hali (`bs_set` = `|`, `bs_clear` = `& ~`'in toplu versiyonu). Aynı boyut garantisi: ya `assert(a->nbits == b->nbits)` ile kontrol, ya da en küçük `nwords`'e kadar işleyip gerisini ele almak. Farklı boyutlarda `dst->words[w]` sınır dışına çıkabilir (Ders 4.1); boyut eşitliği şart.

**2** –

```c
// from'dan itibaren bir sonraki set biti dondur; yoksa nbits
size_t bs_next(const Bitset *b, size_t from) {
    size_t w = from / 64;
    if (w >= b->nwords) return b->nbits;
    uint64_t x = b->words[w] & (~0ull << (from % 64));   // from'dan oncesini maskele
    while (1) {
        if (x) return w * 64 + __builtin_ctzll(x);
        if (++w >= b->nwords) return b->nbits;
        x = b->words[w];
    }
}
```

`from % 64`'ten önceki bitleri `~0ull << (from % 64)` ile maskeleyip, kalan kelimede `ctz` ile bir sonraki 1'i buluyoruz; kelimede yoksa sonraki kelimelere geçiyoruz. Kullanım: `for (size_t i = bs_next(b, 0); i < b->nbits; i = bs_next(b, i+1))`. **Iterator daha esnek**: döngüyü erken durdurabilir, `break` edebilir, iki bitset'i paralel gezebilirsin; callback (`bs_foreach`) her biti işlemek zorunda, akışı dışarıdan kontrol edemezsin. Callback daha kısa, iterator daha güçlü.

**3** –

```c
uint64_t king_attacks(uint64_t kings) {
    uint64_t l = (kings >> 1) & ~FILE_H;   // sol
    uint64_t r = (kings << 1) & ~FILE_A;   // sag
    uint64_t lr = kings | l | r;           // sutun yayilimi
    return l | r | (lr << 8) | (lr >> 8);  // bir yukari, bir asagi
}
```

Şah 8 komşuya gider: yatay (`l`, `r`), ve bu üçlünün (kendisi + sol + sağ) bir yukarı (`<< 8`) ve bir aşağı (`>> 8`) kaydırılmışı. At'tan basit, çünkü hep bir kare (iki değil); sadece `~FILE_A` ve `~FILE_H` maskeleri gerekir (yatay taşmayı önlemek için), dikey taşma `<< 8`/`>> 8`'de 64-bit sınırında kendiliğinden kaybolur.

**4** – Maskesiz `a1` atını (kare 0) `>> 1` ile kaydırırsak, bit 0'ın altında bit yok, kaybolur — bu durumda sorun değil. Ama `a2` (kare 8) atını `>> 1` ile kaydırırsak bit 7'ye (h1) düşer: at a-dosyasından h-dosyasına "sardı" — tahtanın solundan çıkıp sağından girdi, geçersiz. `~FILE_H` maskesi tam bunu keser: `>> 1` sonrası h-dosyasına düşen bitleri siler. Maskesiz `a1` atını işlersen bazı hamleler h-dosyasında yanlış karelere düşer; `print_board` ile tahtanın sağ kenarında olmaması gereken `#`'ler görünür.

**5** – **"Kaç taş var"**: bitboard `popcount` (tek komut); dizi 64 hücreyi gezen bir döngü (64 adım). **"Karelerini listele"**: bitboard `ctz` + `x&(x-1)` ile taş sayısı kadar adım; dizi 64 hücre taraması. **"Bu kare dolu mu"**: bitboard `(bb >> sq) & 1` (bir işlem); dizi `board[r][c]` (bir erişim) — burada eşit. Bitboard **toplu** sorgularda kazanır (say, listele, saldırı maskesi — 64 kareyi paralel), ve bellekte 8 byte (dizi 64+ byte). Dizi **okunabilirlik**te kazanır: `board[r][c] = KNIGHT` bir satranç kodunu okuyan için açıktır, `1ull << (r*8+c)` değil. Pratikte motorlar bitboard kullanır (hız kritik), öğretici/basit kodlar dizi. Ders 4.3'teki "veri düzeni erişim desenine uymalı" ilkesi: toplu bit sorguları için bitboard, tek tek kare erişimi için dizi.

</details>

---

## Kaynaklar

- Chess Programming Wiki, "Knight Pattern" ve "Bitboards": bitboard teknikleri ve dalsız hamle üretimi.
- Donald Knuth, *TAOCP* Cilt 4A, §7.1.3: bitset işlemleri ve "broadword" programlama.
- Henry Warren, *Hacker's Delight* (2. baskı): bu fazın bütün tekniklerinin kaynağı.
- Ders 5.2 (maskeler), 5.3 (en sağdaki bit), 5.8 (popcount), 5.9 (ctz): bu projenin yapı taşları.

**Sıradaki faz:** Matematik temelleri, sayı teorisi ve soyut cebir. Bu fazdaki Boole cebiri, GF(2) ve modüler aritmetik sezgilerinin ispatlı hali.
