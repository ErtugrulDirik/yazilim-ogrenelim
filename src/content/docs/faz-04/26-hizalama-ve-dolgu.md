---
title: "4.26 Hizalama ve dolgu"
description: "Bir struct'ın neden üyelerinin toplamından büyük olabildiği: her tipin hizalama gereksinimi, derleyicinin üyeleri doğru ofsetlere koymak için araya dolgu byte'ları eklemesi, offsetof ve alignof ile bunu görmek, üye sırasını büyükten küçüğe dizerek boyutu küçültmek (32'den 16'ya), Ders 4.1'deki struct Student'ın 20 byte olmasının sebebi, sondaki dolgu, packed'in bedeli ve malloc'un hizalama garantisi."
---

Ders 4.1'de bir `struct Student`'ın (bir `int` numara, bir `char` şube, üç `int` not) 17 byte etmesi gerekirken 20 byte olduğunu gördük; Ders 4.4'te `&` ile adreslerin hep 4'ün ya da 8'in katında başladığını fark ettik; Ders 4.25'te `struct Rect`'in `sizeof`'unu üyelerin toplamıyla doğruladık. Üçünün de altında tek bir kavram var: **hizalama** (alignment). Bu derste neden bazı struct'ların "fazladan" yer kapladığını ve üye sırasını değiştirerek bunu nasıl düzelteceğimizi görüyoruz.

---

## 1. Hizalama: her tipin bir kuralı var

İşlemci belleği tek tek byte değil, **bloklar** halinde okuyor (Ders 4.4'te bunu sezmiştik). Verimli okuma için her tipin bir **hizalama gereksinimi** var: o tipten bir değer, adresi hizalamanın katı olan bir yerde durmalı. C11'in `alignof`'u (`<stdalign.h>`) bunu söylüyor:

```c
printf("alignof: char=%zu int=%zu double=%zu\n",
       alignof(char), alignof(int), alignof(double));
```

```
alignof: char=1 int=4 double=8
```

- `char` (1): her adreste durabilir.
- `int` (4): adresi 4'ün katı olmalı.
- `double` (8): adresi 8'in katı olmalı.

Bir tipin hizalaması genelde boyutuna eşit. Ders 4.4'te `&x`'lerin 4'ün/8'in katında çıkmasının sebebi buydu: derleyici her değişkeni tipinin gerektirdiği hizaya koyuyor. Bazı eski mimarilerde hizasız erişim doğrudan çöker; ARM ve x86'da çalışır ama yavaştır. Derleyici bu yüzden hizayı **garanti** etmek zorunda.

---

## 2. Dolgu: struct neden üyelerinin toplamından büyük

Bir struct'ın üyeleri bellekte sırayla dizilir (Ders 4.1), ve her üye kendi hizasına uymak zorundadır. Üyeler buna kendiliğinden uymazsa, derleyici aralarına **dolgu** (padding) byte'ları ekler. Kötü sıralanmış bir struct:

```c
struct Bad {
    char a;      // 1 byte
    int b;       // 4 byte
    char c;      // 1 byte
    double d;    // 8 byte
    char e;      // 1 byte
};
```

Üyeler 1+4+1+8+1 = 16 byte eder. Ama:

```c
printf("Bad: sizeof=%zu\n", sizeof(struct Bad));
printf("  a:%zu b:%zu c:%zu d:%zu e:%zu\n",
       offsetof(struct Bad, a), offsetof(struct Bad, b), ...);
```

```
Bad:  sizeof=32
  a:0 b:4 c:8 d:16 e:24
```

**32 byte** — yarısı dolgu. `offsetof` (`<stddef.h>`; bir üyenin struct içindeki byte ofseti) her üyenin nerede durduğunu söylüyor:

```
ofset:  0    1  2  3   4   5  6  7   8    9 ...15   16          24    25...31
        a   [dolgu]    b b b b   c   [dolgu]        d d d d d d d d   e  [dolgu]
```

- `a` ofset 0.
- `b` (`int`, hiza 4) 1'de başlayamaz; derleyici 1–3'ü **dolgu** yapıp `b`'yi 4'e koyar.
- `c` ofset 8.
- `d` (`double`, hiza 8) 9'da başlayamaz; 9–15 dolgu, `d` 16'da.
- `e` ofset 24.
- Sonra `e`'den sonra 25–31 arası 7 byte daha dolgu — birazdan (Bölüm 4) sebebini göreceğiz.

Her dolgu, bir sonraki üyeyi hizasına taşımak için. Ders 4.1'deki `struct Student`'ın 20 byte olması da tam buydu:

```c
struct Student { int number; char group; int notes[3]; };
// sizeof=20, offset: number:0 group:4 notes:8
```

`group` ofset 4'te (1 byte), ama `notes` bir `int` array'i (hiza 4), 5'te başlayamaz; derleyici 5–7'yi dolgu yapıp `notes`'u 8'e koyar. 4 + 1 + **3 dolgu** + 12 = 20. Ders 4.1'deki "aradaki 3 byte" işte bu üç dolgu byte'ı.

---

## 3. Üye sırası boyutu değiştirir

`struct Bad`'in dolgusu, üyelerin **sırasından** kaynaklanıyor: küçük ve büyük üyeler dönüşümlü. Aynı üyeleri **büyükten küçüğe** dizersek:

```c
struct Good {
    double d;    // 8
    int b;       // 4
    char a;      // 1
    char c;      // 1
    char e;      // 1
};
```

```
Good: sizeof=16
  d:0 b:8 a:12 c:13 e:14
```

**16 byte** — yarısı! Aynı veri, yarı yer. Yerleşim:

```
ofset:  0 1 2 3 4 5 6 7   8 9 10 11   12  13  14   15
        d d d d d d d d    b  b  b  b   a   c   e  [dolgu]
```

`d` 0'da (hiza 8, tamam), `b` 8'de (hiza 4, tamam), üç `char` 12-13-14'te ardışık. Hiç ara dolgu yok; sadece sonda 1 byte. **Kural**: üyeleri hizalaması (genelde boyutu) büyükten küçüğe sırala, dolgu en aza iner. Çok sayıda struct tutan programlarda (Ders 4.24'teki diziler, Faz 8'deki veri yapıları) bu, belleği ve önbellek kullanımını yarıya indirebilir.

Not: `offsetof` ve `sizeof` ile dolguyu doğrudan ölçtüğümüz için, bir struct'ın düzenini tahmin etmek yerine **gözleyebiliyoruz**. Önemli bir struct'ı tanımladıktan sonra `sizeof`'una bakmak iyi bir alışkanlık.

---

## 4. Sondaki dolgu ve struct'ın hizalaması

`struct Bad`'de `e` ofset 24'teydi ama boyut 32; `e`'den sonra 7 byte dolgu var. Neden? Bir struct'ın **kendi** hizalaması, **en büyük hizalı üyesinin** hizasıdır:

```c
printf("alignof Bad=%zu Good=%zu\n", alignof(struct Bad), alignof(struct Good));
```

```
alignof Bad=8 Good=8
```

İkisinin de hizası 8, çünkü ikisinde de bir `double` var. Bir struct'ın boyutu, hizasının **katı** olmak zorunda — çünkü struct'lardan bir **array** yapıldığında (Ders 4.1), her eleman doğru hizada başlamalı. `struct Bad`'in son üyesi 24'te bitiyor (25'e kadar), ama 25 ne 8'in katı; derleyici boyutu bir sonraki 8 katına (32) yuvarlıyor. Böylece `struct Bad arr[2]`'de `arr[1]` yine 8 hizalı bir adreste başlar. `struct Student` de 17'den 20'ye değil, 4'ün katı olan 20'ye yuvarlanmıştı (hizası 4, en büyük üyesi `int`).

### packed: dolguyu kaldırmak (ve bedeli)

Dolgudan tamamen kurtulmak mümkün: `__attribute__((packed))` (standart değil, ama clang ve gcc'de var).

```c
struct __attribute__((packed)) Packed { char a; int b; char c; double d; char e; };
// sizeof = 15  (1+4+1+8+1, hic dolgu yok)
```

15 byte — üyelerin tam toplamı. Ama bedeli var: `Packed` içindeki `b` artık hizasız bir adreste (ofset 1) durabilir. Hizasız bir `int`'i okumak bazı mimarilerde yavaş, bazılarında doğrudan çökme; ARM'da derleyici bunu bilip hizasız erişim için fazladan kod üretir. `packed` sadece gerçekten gerektiğinde kullanılır: bir ikili dosya formatını ya da ağ paketini byte byte eşlemek gibi (Ders 3.9'daki endianness ile birlikte). Sıradan struct'larda **asla**; dolgu bir israf değil, hızın bedeli.

---

## 5. malloc ve hizalama

Ders 4.22'de `malloc`'un verdiği belleğe her tipi koyabildiğimizi (int, double, struct) söylemiştik. Bu nasıl güvenli? Çünkü `malloc`, **en katı hizalama** gereksinimini karşılayan bir adres döndürmeyi garanti ediyor:

```c
for (int i = 0; i < 4; i++) {
    void *p = malloc(1);
    printf("malloc(1) %% 16 = %zu\n", (size_t)p % 16);
}
```

```
malloc(1) % 16 = 0
malloc(1) % 16 = 0
...
```

1 byte istesen bile, dönen adres 16'nın katı. `malloc` ne için kullanacağını bilmediği için (Ders 4.9'daki `void *`), en büyük temel tipin (`max_align_t`, genelde 16) hizasına uyacak bir adres veriyor. Böylece `int *a = malloc(...)` de `double *d = malloc(...)` de `struct Big *s = malloc(...)` de her zaman hizalı.

Kendi hizanı istersen, C11'in `alignas`'ı (`<stdalign.h>`):

```c
alignas(16) char buf[32];   // buf'un adresi 16'nin kati
```

Bir diziyi SIMD komutları (Faz 11) ya da belirli bir donanım için hizalamak gerektiğinde kullanılır. Ders 4.28'de kendi arena allocator'ımızı yazarken, verdiğimiz her bloğu bu kurala uyacak şekilde hizalamak zorunda kalacağız — hizalamanın neden önemli olduğunu orada kendi elimizle göreceğiz.

---

## Alıştırmalar

**1** – `struct { char a; char b; short c; int d; };`'nin `sizeof`'unu ve her üyenin `offsetof`'unu elle tahmin et (`short` hizası 2), sonra ölçerek doğrula. Hiç dolgu var mı?

**2** – `struct Bad`'in üyelerini (1 `double`, 1 `int`, 3 `char`) 16 byte'a sığdıran **başka** bir sıralama bul (Bölüm 3'tekinden farklı). Kaç farklı 16-byte sıralama var? Hangi kural yeterli?

**3** – `struct Mixed { char a; double b; char c; };`'nin boyutu kaç? `offsetof` ile dolgunun nerede olduğunu bul. Üyeleri yeniden sıralayarak en küçük boyutu elde et — kaç byte kazandın?

**4** – Ders 4.1'deki `struct Student`'ı (`int number; char group; int notes[3];`) 20 byte yerine daha küçük yapacak şekilde yeniden sırala. Kaç byte olur? `group`'u nereye koydun ve neden?

**5** – `struct __attribute__((packed)) Header { uint8_t version; uint32_t length; uint16_t flags; };` bir ağ paketi başlığı. `sizeof` kaç, `packed` olmadan kaç olurdu? `length` üyesini okurken (ofset 1, hizasız) neden `packed` gerekli, ama neden sıradan kodda tehlikeli? (Ders 3.9'daki endianness'ı da düşün.)

<details>
<summary>Cevaplar</summary>

**1** – `a` (char) ofset 0, `b` (char) ofset 1, `c` (short, hiza 2) ofset 2 (zaten 2'nin katı, dolgu yok), `d` (int, hiza 4) ofset 4. Toplam 8 byte, **hiç dolgu yok**: üyeler küçükten büyüğe diziliyken ve boyutları birbirinin katıyken her üye kendiliğinden hizaya denk geliyor. `sizeof` = 8, hizası 4 (en büyük üye `int`), 8 zaten 4'ün katı, sonda da dolgu yok.

**2** – Yeterli kural: `double` (hiza 8) en başta ya da 8 hizalı bir ofsette, sonra `int`, sonra üç `char`. 16 byte veren sıralamalar: `double, int, char, char, char` (Bölüm 3) ve `int, char, char, char, double`? — hayır, bu sonuncuda `double` 7'de başlayamaz, dolgu girer ve 16'yı aşar. Aslında 16 byte için `double`'ın 0 ya da 8 ofsetinde olması gerekir; `double` başta, geri kalan 8 byte'a `int`(4)+3 char(3)+1 dolgu rahat sığar — `int` ve üç char'ın kendi aralarındaki sırası fark etmez (hepsi küçük). Yani `double` önce, sonra `int` ve üç `char` herhangi sırada: birkaç geçerli sıralama. Genel kural: **en büyük hizalı üyeyi öne al**, gerisi küçükse serbest.

**3** – `struct Mixed { char a; double b; char c; }`: `a` ofset 0, `b` (double, hiza 8) ofset 8 (1–7 dolgu), `c` ofset 16, sonra struct hizası 8 olduğu için 17→24'e yuvarlanır. **sizeof = 24**. Dolgu: 7 byte (`a`'dan sonra) + 7 byte (sonda) = 14 byte dolgu, 10 byte veri! Yeniden sıralama `{ double b; char a; char c; }`: `b` 0, `a` 8, `c` 9, sonda 10→16 yuvarlama = **16 byte**. 24'ten 16'ya, 8 byte kazanç.

**4** – `struct Student { int number; int notes[3]; char group; }`: `number` 0–3, `notes` 4–15 (int array, 4 hizalı, dolgu yok), `group` 16, sonda struct hizası 4 olduğu için 17→20 yuvarlama... hâlâ 20. `group`'u `int`'lerin arasına değil sonuna koymak ara dolguyu kaldırdı (eski halde `group` 4'teydi ve `notes` için 3 dolgu gerekiyordu), ama sondaki yuvarlama yüzünden yine 20. Bu struct'ta `int`'ler zaten çoğunlukta; `char group` nereye konsa sondaki yuvarlama 20'yi dayatıyor. 17 byte veri, en küçük mümkün 20 (4'ün katı). Ders: bazen sıralama sondaki yuvarlama yüzünden boyutu değiştiremez — ama ara dolguyu kaldırmak yine de düzen açısından iyi.

**5** – `packed` ile `sizeof(Header)` = 1 + 4 + 2 = **7**. `packed` olmadan: `version` 0, `length` (hiza 4) 4'te (1–3 dolgu), `flags` 8'de, sonda 10→12 yuvarlama = **12 byte**. Bir ağ paketi başlığı tam 7 byte olmalı (karşı taraf da öyle bekliyor); dolgu eklenirse byte'lar kayar ve paket yanlış okunur, bu yüzden `packed` **gerekli**. Ama `length` artık ofset 1'de, hizasız: onu `header.length` diye okumak hizasız bir `int` erişimi, bazı mimarilerde yavaş/çökme — derleyici `packed` sayesinde bunu bilip güvenli (ama yavaş) kod üretir. Sıradan kodda tehlikeli, çünkü hizasız erişimin maliyeti gizli. Üstelik ağdan gelen byte'lar büyük-endian olabilir (Ders 3.9), `length`'i okurken endianness dönüşümü de gerekir. İkili formatlar `packed` + endianness dönüşümü + dikkatli okuma ister; Faz 18'de bunu bir DSL'e kodlayacağız.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §3.9.3: hizalama ve dolgu.
- C standardı (ISO/IEC 9899:2018), §6.2.8 (nesnelerin hizalaması), §6.7.2.1¶17 (struct üyelerinin sırası ve dolgu), §7.19 (`offsetof`), §6.2.8 ve `<stdalign.h>` (`alignof`, `alignas`).
- Eric Raymond, "The Lost Art of Structure Packing": üye sıralaması ve dolgu azaltma rehberi.
- Peter van der Linden, *Expert C Programming*, Bölüm 8: hizalama kuralları.

**Sıradaki ders:** `union` ve bit alanları. Tip punning, bir float'ın bitlerine union ile bakmak ve bitfield'lerin taşınabilirlik sorunları.
