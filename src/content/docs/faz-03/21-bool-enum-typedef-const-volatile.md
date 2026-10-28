---
title: "3.21 bool, enum, typedef, const, volatile"
description: "Yeni sayı türü yaratmayan ama compiler'a bir değer hakkında bilgi veren beş araç: her sıfır olmayan değeri 1 yapan bool, adlandırılmış sabitler için enum, tiplere yeni ad veren typedef, salt okunur değişkenler ve const doğruluğu, ve compiler'ın bellek erişimlerini silmesini engelleyen volatile. Faz 3'ün kapanışı."
---

Faz 3 boyunca tipleri öğrendik: kaç byte tuttuklarını, bitlerinin nasıl okunduğunu, birbirlerine nasıl dönüştüklerini. Bu dersteki beş anahtar kelime yeni bir sayı biçimi getirmiyor. Hepsi, compiler'a bir değer hakkında **bir şey söylemenin** yolu:

| Anahtar kelime | Compiler'a ne söylüyor? |
| --- | --- |
| `bool` | "Bu değer sadece doğru ya da yanlış." |
| `enum` | "Bu değerler, adları olan küçük bir kümeden." |
| `typedef` | "Bu tipe şu adla seslen." |
| `const` | "Bunu değiştirmeyeceğim." |
| `volatile` | "Bu değer senin bilmediğin bir şekilde değişebilir." |

Söylediklerimiz, compiler'ın hataları yakalamasını, okuyucunun kodu anlamasını, ve son ikisinde makine kodunun kendisini değiştiriyor.

---

## 1. bool

Faz 2'de doğru ve yanlışı hep `int` ile tuttuk. Ders 2.13'teki `running` değişkeni 0 ya da 1'di; Ders 3.17'deki `is_digit` bir `int` döndürüyordu. Çalışıyor, ama `int running` yazınca okuyucu bunun bir sayaç mı yoksa bir bayrak mı olduğunu bilemiyor.

C99, sadece iki değer alan bir tip ekledi: `_Bool`. `<stdbool.h>` başlığı ona daha okunaklı adlar verir: `bool`, `true` (1) ve `false` (0). C23'te bu üçü artık başlık gerektirmeyen anahtar kelimeler (Ders 2.1'deki tablo).

```c
#include <stdbool.h>

bool is_digit(char c) {
    return c >= '0' && c <= '9';
}
```

`bool`'u özel yapan şey, dönüşüm kuralı. Ders 3.7'deki tamsayı dönüşümlerinde değer sığmazsa bitler kırpılıyordu. `bool`'a dönüşümde ise kural tek: **sıfıra eşitse 0, değilse 1.**

| İfade | Sonuç | Karşılaştır |
| --- | --- | --- |
| `(bool)256` | **1** | `(uint8_t)256` = 0 |
| `(bool)0.1` | **1** | `(int)0.1` = 0 |
| `(bool)-0.0` | **0** | −0,0 == 0 (Ders 3.13) |
| `(bool)NAN` | **1** | NaN != 0 (Ders 3.13) |

İlk satır, Ders 3.18'deki maskelerle birlikte gerçek bir hataya dönüşebilir:

```c
uint32_t flags = 0x100;
bool b = flags & 0x100;
uint8_t u = flags & 0x100;
printf("%d %d\n", b, u);
```

```
1 0
```

`flags & 0x100` = 256: 8 numaralı bit açık. `bool`'a konunca 1, yani "açık". `uint8_t`'ye konunca ise Ders 3.7'deki Kural 2 gereği son 8 bit kalıyor ve sonuç **0**: "kapalı". Bir bayrağı tutmak için küçük bir tamsayı tipi seçmek, sessizce yanlış cevap verebiliyor. `bool`'un var olma sebebi bu.

Birkaç ayrıntı:

- `sizeof(bool)` 1. Bir bit yeterli olsa da, bellekteki en küçük adreslenebilir birim bir byte.
- Aritmetikte `bool`, Ders 3.5'teki gibi `int`'e yükseltilir: `true + true` = 2.
- C'de karşılaştırmaların sonucu hâlâ `int`: `sizeof(1 < 2)` 4. (C++'ta `bool`.) `bool` bir değişkene konunca anlam kazanıyor.

---

## 2. enum

Ders 2.13'te `read_int`'in sonucunu üç sabitle anlatmıştık:

```c
#define READ_OK 1
#define READ_INVALID 0
#define READ_EOF -1
```

Ders 3.17'de `PARSE_OK`, `PARSE_NO_DIGITS`… için aynısını yaptık. Bunlar birbirine ait değerler, ama compiler bunu bilmiyor: üç ayrı `#define`, üç ayrı sayı. `enum` (enumeration, sayım) bir değer **kümesi** tanımlar:

```c
enum ReadStatus {
    READ_EOF = -1,
    READ_INVALID,
    READ_OK,
};
```

- Her ad bir `int` sabiti. Değer verilmezse bir öncekinin bir fazlası alınır; ilkinin değeri verilmezse 0. Burada `READ_EOF` −1, `READ_INVALID` 0, `READ_OK` 1: `#define`'ların aynısı.
- `enum ReadStatus` bir tip: `enum ReadStatus status = READ_OK;`. Ders 2.13'teki struct'ın `int status` alanı `enum ReadStatus status` olabilir.

`#define`'dan üç farkı var.

**Debugger adları biliyor.** Ders 2.6'daki LLDB ile bir `enum` değişkenine bakınca:

```
(lldb) p status
(ReadStatus) READ_OK
(lldb) p code
(int) 1
```

`#define`'lar compiler'a ulaşmadan önce silinir (Ders 2.11); debugger `1` görür, `READ_OK` değil.

**Eksik durumları compiler yakalıyor.** Bir `enum`'u `switch` ile işleyen bir fonksiyon:

```c
enum Color { RED, GREEN, BLUE };

const char *name(enum Color c) {
    switch (c) {
        case RED: return "kırmızı";
        case GREEN: return "yeşil";
    }
    return "?";
}
```

`-Wall` ile:

```
warning: enumeration value 'BLUE' not handled in switch [-Wswitch]
```

`BLUE`'yu unuttuk ve compiler fark etti. Bir `enum`'a sonradan yeni bir değer eklediğinde, onu işlemesi gereken her `switch` bu uyarıyla ortaya çıkar. `#define`'larla bunun bir yolu yok. (`switch`'e `default:` eklersen uyarı kaybolur; bu yüzden `enum`'lu `switch`'lerde `default` kullanmamak çoğu zaman daha iyi.)

**Ama tam bir koruma değil.** C'de bir `enum`, kılık değiştirmiş bir `int`:

```c
enum Color x = 7;
printf("%d %s\n", x, name(x));
```

```
7 ?
```

Uyarı bile yok. `sizeof(enum Color)` 4. Compiler, bir `enum` değişkenine kümenin dışından bir değer koymanı engellemiyor; C++'taki `enum class` bunu yapar. C23 ise bir `enum`'un hangi tamsayı tipinde tutulacağını seçmeyi ekledi: `enum Small : uint8_t { A, B };` 1 byte.

**Ne zaman `enum`, ne zaman `#define`?** Birbirine ait, birbirinden farklı durumlar (renkler, hata kodları, menü seçenekleri, Ders 2.13'teki `MALE` ve `FEMALE`) için `enum`. Tek başına bir sabit (`FX_ONE`, `ITOA_BUFFER_SIZE`) için `#define` ya da Bölüm 4'te göreceğimiz yollar.

---

## 3. typedef

`typedef`, var olan bir tipe **yeni bir ad** verir:

```c
typedef int32_t fixed_t;
```

Ders 3.4'te `<stdint.h>`'teki tiplerin "yeni tipler değil, var olan tiplere yeni isimler" olduğunu söylemiştik. O isimler tam olarak böyle tanımlanır; bilgisayarındaki sistem başlıklarında `typedef int int32_t;` gibi satırlar var. `size_t` de bir `typedef`.

`fixed_t`, Ders 3.11'deki Doom'un tipinin adı. Q16.16 fonksiyonlarımızı onunla yazalım:

```c
typedef int32_t fixed_t;

fixed_t fx_mul(fixed_t a, fixed_t b) {
    return (fixed_t)((int64_t)a * b / FX_ONE);
}
```

`int32_t fx_mul(int32_t a, int32_t b)` ile makine için **hiçbir fark yok**. Fark okuyucu için: `fixed_t` "bu bir sabit noktalı sayı" diyor; `int32_t` sadece "32 bit". Bir gün Q16.16 yerine Q32.32'ye (`int64_t`) geçmek istersen, tek satırı değiştirirsin.

Dikkat: `typedef` yeni bir tip **yaratmaz**, sadece bir takma ad verir. `fx_mul(3, 4)` yazmak (tamsayıları sabit noktalı sayı gibi vermek; Ders 3.11'deki `a + 2` hatası) hiçbir uyarı üretmez, çünkü compiler için `fixed_t` ve `int` aynı şey.

### struct'larla

Ders 2.3'ten beri struct tiplerini `struct` kelimesiyle birlikte yazıyoruz: `struct ReadResult r`. `typedef` bunu kısaltır:

```c
typedef struct {
    int status;
    long value;
    int end;
} ParseResult;

ParseResult r = parse_long(text, 10);
```

İki yazım da yaygın; Linux çekirdeği gibi bazı projeler `struct`'ı her zaman açıkça yazmayı tercih eder ki tipin bir struct olduğu görünsün. Bir ad kuralı: `_t` ile biten adlar POSIX tarafından sistem kütüphanelerine ayrılmış; kendi tiplerine bu eki vermek, ileride bir sistem tipiyle çakışma riski taşır. Doom'un `fixed_t`'si bu kural yaygınlaşmadan önce yazıldı.

---

## 4. const

`const`, bir değişkenin ilk değerinden sonra **değiştirilemeyeceğini** söyler:

```c
const double PI = 3.14159;
PI = 3;
```

```
error: cannot assign to variable 'PI' with const-qualified type 'const double'
```

Bu bir uyarı değil, **hata**: program derlenmez. Değişmemesi gereken bir değeri yanlışlıkla değiştirmek artık mümkün değil.

### const parametreler

Ders 3.16'dan beri `const char text[]` yazıyoruz. Fonksiyonun, kendisine verilen array'i **okuyacağını ama değiştirmeyeceğini** söylüyor. Ders 2.4'te gördüğümüz gibi array'ler kopyalanmadan verildiği için, bir fonksiyon çağıranın array'ini değiştirebilir; `const` bu kapıyı kapatır:

```c
void f(const int values[]) {
    values[0] = 1;
}
```

```
error: read-only variable is not assignable
```

Tersi yönde de çalışıyor. `const` bir array'i, `const` sözü vermeyen bir fonksiyona verirsen:

```c
void modify(char text[]) {
    text[0] = 'x';
}

const char word[] = "abc";
modify(word);
```

```
warning: passing 'const char[4]' to parameter of type 'char *' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
```

(`char *` Faz 4'teki pointer gösterimi; şimdilik `char text[]` ile aynı şey.) `modify` bu sözü vermediği için compiler uyarıyor; ve `word` gerçekten değiştirilirse sonuç undefined behavior.

**const doğruluğu** (const correctness): bir fonksiyon bir parametreyi değiştirmiyorsa, onu `const` olarak tanımla. Böylece fonksiyon hem `const` hem de sıradan array'lerle çağrılabilir, ve fonksiyonun imzası ne yapıp ne yapmadığını anlatır. `strlen`'in standart kütüphanedeki tanımı `size_t strlen(const char *s)`: bir yazının uzunluğunu ölçmek, yazıyı değiştirmeyi gerektirmez. Faz 4'te string kütüphanesini sıfırdan yazarken bu kuralı her fonksiyonda uygulayacağız.

### const bir sabit değil

Şaşırtıcı bir ayrıntı: C'de `const` bir değişken, compiler'ın derleme sırasında bildiği bir **sabit** sayılmaz; sadece salt okunur bir değişkendir.

```c
const int SIZE = 10;
int table[SIZE];
```

Fonksiyonların dışında bu, C standardına göre hatalı: global bir array'in boyutu bir sabit ifade olmalı. clang bunu bir eklenti olarak kabul edip uyarıyor:

```
warning: variable length array folded to constant array as an extension [-Wgnu-folding-constant]
```

Array boyutları için hâlâ `#define` (ya da `enum { SIZE = 10 };`) kullanılmasının sebebi bu. C23, bu eksiği gerçek derleme zamanı sabitleri için `constexpr` ile kapattı: `constexpr int SIZE = 10;` uyarısız derleniyor. (C++'ta `const int` zaten sabit sayılır; iki dilin en bilinen farklarından biri.)

---

## 5. volatile

Son anahtar kelime, compiler'ın en güçlü silahlarından birini, kod **silmeyi**, durdurur.

Bir global değişken (Ders 2.7) ve onu okuyan üç küçük fonksiyon yazalım. `ready_v` aynı değişkenin `volatile` hali:

```c
int ready;
volatile int ready_v;

int twice_plain(void) {
    return ready + ready;
}

int twice_volatile(void) {
    return ready_v + ready_v;
}

void store_plain(void) {
    ready = 1;
    ready = 2;
}

void store_volatile(void) {
    ready_v = 1;
    ready_v = 2;
}
```

godbolt, **x86-64 clang**, **`-O2`**:

```asm
twice_plain:
        mov     eax, dword ptr [rip + ready]
        add     eax, eax
        ret

twice_volatile:
        mov     eax, dword ptr [rip + ready_v]
        add     eax, dword ptr [rip + ready_v]
        ret

store_plain:
        mov     dword ptr [rip + ready], 2
        ret

store_volatile:
        mov     dword ptr [rip + ready_v], 1
        mov     dword ptr [rip + ready_v], 2
        ret
```

- `twice_plain`: `ready` bellekten **bir kez** okunuyor ve kendisiyle toplanıyor. Compiler'ın mantığı: iki okuma arasında `ready`'yi kimse değiştirmedi, aynı değeri iki kez okumaya gerek yok.
- `store_plain`: `ready = 1` satırı **yok**. 1 yazıp hemen üzerine 2 yazmak, sadece 2 yazmakla aynı sonucu veriyor.
- `volatile` hallerinde her okuma ve her yazma, koddaki gibi **ayrı ayrı** yapılıyor.

Normal bir programda compiler'ın yaptığı tamamen doğru ve programı hızlandırıyor. Ama ya `ready` değişkeni bellekte değil de bir **donanım** parçasındaysa?

### Donanım register'ları

Ders 3.15'teki Arduino'yu düşün. Bir LED'i yakmak için, işlemcinin belirli bir adresindeki bir byte'a yazarsın; o byte bir bellek hücresi değil, bir pine bağlı bir **register**. Bir düğmenin basılıp basılmadığını anlamak için de başka bir adresi okursun; o adresteki değer, düğmeye basıldığı anda programdan habersiz değişir.

Böyle bir adresi bekleyen bir döngü:

```c
void wait_plain(void) {
    while (!ready) {
    }
}

void wait_volatile(void) {
    while (!ready_v) {
    }
}
```

```asm
wait_plain:
        ret

wait_volatile:
.LBB1_1:
        cmp     dword ptr [rip + ready_v], 0
        je      .LBB1_1
        ret
```

`wait_plain`'in bütün döngüsü **silindi**. Compiler'ın mantığı iki adımda: döngüde `ready`'yi kimse değiştirmiyor, öyleyse onu bir kez okumak yeter; o zaman döngü ya hiç dönmez ya da sonsuza kadar döner. C standardı, hiçbir şey yapmayan sonsuz bir döngünün olmadığını varsaymaya izin veriyor; demek ki döngü hiç dönmez. Ders 3.8'deki taşma kontrolünü silen akıl yürütmenin bir benzeri. `wait_volatile`'da ise her turda bellek yeniden okunuyor: düğmeye basıldığı an döngü biter.

Arduino'nun kütüphaneleri, donanım register'larının adlarını (`PORTB` gibi) tam bu yüzden `volatile` olarak tanımlar.

Aynı sorun, beklemek için yazılan boş döngülerde de çıkar:

```c
void delay(void) {
    for (int i = 0; i < 1000000; i++) {
    }
}
```

`-O2` ile bu fonksiyon tek bir `ret` oluyor: döngü hiçbir şey hesaplamıyor, silinebilir. Sayacı `volatile int i` yaparsan döngü, her adımda belleğe yazıp okuyarak bir milyon kez dönüyor. Ders 3.14'teki yuvarlama modu programında `one` ve `three`'yi `volatile` yapmamızın sebebi de buydu: compiler `1.0f / 3.0f`'ı derleme sırasında hesaplayıp sonucu koda gömmesin, bölme gerçekten o anki yuvarlama moduyla çalışsın.

### volatile ne değildir?

`volatile`, compiler'a "her erişimi yap" der; o kadar. Birden çok iş parçacığının (thread) aynı değişkeni kullandığı programlarda **yetmez**: erişimin bölünmeden yapılacağını (atomiklik) ya da farklı işlemci çekirdeklerinin yazmaları aynı sırayla göreceğini garanti etmez. Bunlar için C11'in `<stdatomic.h>`'teki atomik tipleri var; Faz 10'da göreceğiz. `volatile`'ın doğru kullanımları dar: donanım register'ları, sinyal işleyiciler (Faz 10) ve compiler'ın bir işlemi silmemesini istediğin ölçüm ve test kodları.

---

## Faz 3 bitti

Bu fazın başında Ders 3.1'de bir liste yapmıştık: Faz 2'de çarptığımız duvarlar. Hepsinin cevabını bulduk:

- **13! neden yanlış?** `int` 4 byte; 13! sığmıyor (3.1, 3.2). `long long` 20!'e kadar yetiyor; taşmayı önceden yakalamanın yolu `ckd_mul` (3.8).
- **`INT_MIN` neden bir fazla?** İkiler tümleyeni: sıfır pozitif tarafta yer kaplıyor (3.3).
- **Arduino'da aynı program neden bozuluyor?** Tiplerin boyutu platforma bağlı; `<stdint.h>` ile bilmek zorundayız (3.1, 3.2, 3.4).
- **Farklı tipler buluşunca ne oluyor?** Yükseltme, usual arithmetic conversions, işaretli–işaretsiz tuzakları ve dönüşümün üç kuralı (3.5–3.7).
- **Bir sayı bellekte nasıl duruyor?** Byte sırası (3.9), sabitlerin tipleri (3.10).
- **Vücut kitle indeksi neden 22?** Küsurat yoktu. Sabit noktalı sayılarla (3.11), sonra IEEE 754 ile (3.12–3.14) çözdük, ve dört yöntemi yan yana koyduk (3.15).
- **0,1 + 0,2 neden 0,3 değil?** 0,1 ikilikte sonsuz bir kesir; her işlem bir yuvarlama (3.12, 3.14).
- **`printf` ve `scanf`'in içinde ne var?** `itoa`, `strtol`, `print_hex`, `ftoa` ve `atof`'u sıfırdan yazdık; `strtol`'unkini birebir kopyaladık, `ftoa` ve `atof` için doğru sonucun ne kadar zor olduğunu gördük (3.16–3.20).

Ve tekrar tekrar aynı dersi aldık: **bitlerin anlamını bağlam belirler**, ve compiler, standardın sana söz vermediği her şeyi kendi lehine kullanır.

**Sıradaki faz:** Diziler, pointer, bellek ve string kütüphanesi sıfırdan. Bu fazda birçok kez "Faz 4'te göreceğiz" dedik: `&`'in ne olduğu, `char *`, array'lerin neden kopyalanmadığı, `'\0'` ile biten yazılar. Hepsi orada.

---

## Alıştırmalar

**1** – Bu ifadelerin değerlerini tahmin et, sonra dene: `(bool)0.1`, `(bool)-0.0`, `(bool)NAN`, `(uint8_t)(bool)512`, `(uint8_t)512`, `true + true`.

**2** – Ders 2.13'teki `io.h`'yi `enum` ile yeniden yaz: `READ_OK`, `READ_INVALID`, `READ_EOF` bir `enum ReadStatus`, `MALE` ve `FEMALE` bir `enum Sex` olsun. `struct ReadResult`'ın `status` alanının tipi ne olmalı? `main.c`'deki kodun değişmesi gerekiyor mu?

**3** – `typedef int32_t fixed_t;` yazdıktan sonra `fixed_t a = fx_from_int(2); fixed_t b = a + 2;` satırları uyarı verir mi? `-Wall -Wextra -Wconversion` ile dene. Bu, `typedef`'in neyi yapıp neyi yapmadığı hakkında ne söylüyor? Bu hatayı compiler'a yakalatmanın bir yolu var mı?

**4** – Hangileri derlenir? Derlenmeyenler için hatayı tahmin et.

```c
const int a = 5;
int b = a + 1;
a++;
const char text[] = "abc";
char c = text[0];
text[0] = 'x';
```

**5** – Bölüm 5'teki `delay` fonksiyonunu `-O0` ile derlediğinde döngü silinir mi? Bir programın `-O0` ile çalışıp `-O2` ile çalışmaması, hangi derslerde karşımıza çıktı? Ortak noktaları ne?

<details>
<summary>Cevaplar</summary>

**1** – `(bool)0.1` → **1**, `(bool)-0.0` → **0** (−0,0 sıfıra eşit), `(bool)NAN` → **1** (NaN sıfıra eşit değil; Ders 3.13'te NaN'ın `!=` ile her şeyden farklı olduğunu görmüştük), `(uint8_t)(bool)512` → **1**, `(uint8_t)512` → **0**, `true + true` → **2**. clang, `bool b = 0.5;` gibi sabit bir atamada `-Wliteral-conversion` ile uyarır: `implicit conversion from 'double' to 'bool' changes value from 0.5 to true`.

**2** –

```c
enum ReadStatus {
    READ_EOF = -1,
    READ_INVALID,
    READ_OK,
};

enum Sex {
    MALE = 1,
    FEMALE,
};

struct ReadResult {
    enum ReadStatus status;
    int value;
};
```

`MALE = 1` şart: kullanıcı menüde 1 ve 2 yazıyor, ve `ask(MALE, FEMALE)` bu sayılarla çalışıyor. `main.c`'nin değişmesi gerekmiyor: adlar ve değerler aynı, ve `enum` değerleri `int` olarak her yerde kullanılabiliyor. Kazandığımız: debugger'da adlar, ve `status` üzerinde bir `switch` yazarsan eksik durumlar için uyarı.

**3** – Hiçbir uyarı yok. `fixed_t` bir takma ad; compiler için `a + 2` sıradan bir `int32_t` toplaması. `typedef` **okuyucuya** bilgi veriyor, **compiler'a** değil. Compiler'a yakalatmanın C'deki yolu, değeri bir struct'ın içine koymak: `typedef struct { int32_t raw; } fixed_t;`. Artık `a + 2` derlenmez, çünkü bir struct'la toplama yapılamaz; her işlem `fx_add` gibi fonksiyonlardan geçmek zorunda. Bedeli, kodun uzaması.

**4** –

- `const int a = 5;` ✓
- `int b = a + 1;` ✓ (`a`'yı okumak serbest)
- `a++;` ✗: `cannot assign to variable 'a' with const-qualified type 'const int'`
- `const char text[] = "abc";` ✓
- `char c = text[0];` ✓
- `text[0] = 'x';` ✗: `cannot assign to variable 'text' with const-qualified type 'const char[4]'`

**5** – `-O0` ile silinmez: compiler hiçbir iyileştirme yapmaz ve döngü yazıldığı gibi bir milyon kez döner. Aynı farkı Ders 2.12'de (`x + 1 > x`), Ders 3.8'de (`add_overflows`'un `xor eax, eax`'e dönüşmesi), Ders 3.13'te (`-ffast-math` ile `isnan`) ve Ders 3.14'te (`-ffast-math` ile Kahan) gördük. Ortak nokta: kod, standardın **söz vermediği** bir şeye dayanıyordu (işaretli taşma, sonsuz boş döngü, NaN'ın olmaması, işlem sırası, değişkenin başka bir yerden değişmesi). `-O0` bu sözleri kullanmadığı için kod "çalışıyor gibi" görünür; `-O2` kullanır ve gerçek ortaya çıkar. Bir programı her zaman iyileştirmelerle, uyarılarla ve sanitizer'larla da test etmenin sebebi bu.

</details>

---

## Kaynaklar

- C standardı (ISO/IEC 9899:2018), §6.2.5 ve §6.3.1.2: `_Bool` ve dönüşüm kuralı; §6.7.2.2: `enum`; §6.7.8: `typedef`; §6.7.3: `const` ve `volatile`; §6.8.5¶6: sonlanacağı varsayılabilen döngüler. C23 (ISO/IEC 9899:2024): `bool` anahtar kelimesi, `constexpr`, tipi belirtilmiş `enum`'lar.
- Robert Seacord, *Effective C* (2. baskı), Bölüm 2 ve 3: tip niteleyicileri ve `enum`'lar.
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.3, §2.4, §6.7.

**Sıradaki ders:** Ders 4.1, diziler bellekte.
