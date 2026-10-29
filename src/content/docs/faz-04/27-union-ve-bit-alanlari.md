---
title: "4.27 union ve bit alanları"
description: "union: bütün üyeler aynı bellek, boyutu en büyük üye kadar; bir float'ın bitlerine union ile bakmak (tip punning) ve bunun C'de tanımlı, C++'ta olmaması; işaret/üs/kesiri çıkarıp Ders 3.12'yi doğrulamak; etiketli birleşim (tagged union) ile tek tipte farklı değerler tutmak; bit alanları ile bir struct'ı bite kadar paketlemek, taşma uyarısı ve bit sırasının taşınabilirlik sorunu."
---

Ders 4.25 ve 4.26'da struct'ları, üyelerin **yan yana** durduğu yapıları gördük. `union` bunun tersi: bütün üyeler **aynı** bellek yerini paylaşıyor. Ders 4.5'te bir sayının byte'larına `unsigned char *` ile bakmıştık; Ders 3.12'de bir `float`'ın bitlerini merak etmiştik ve "Ders 4.27'de union'larla döneceğiz" demiştik. Bu derste union ile bir değerin **iki farklı tip gibi** okunmasını (tip punning), ve bit alanlarıyla bir struct'ı bit düzeyinde paketlemeyi işliyoruz.

---

## 1. union: paylaşılan bellek

```c
union FloatBits {
    float f;
    uint32_t bits;
};
```

`struct`'ta üyeler ardışık; `union`'da **üst üste**. `f` ve `bits` aynı 4 byte'ı gösteriyor. Boyutu en büyük üye kadar (ikisi de 4):

```c
union FloatBits fb;
fb.f = 3.14f;
printf("sizeof union = %zu\n", sizeof(union FloatBits));   // 4
printf("f = %g, bits = 0x%08x\n", fb.f, fb.bits);
```

```
sizeof union = 4
f = 3.14, bits = 0x4048f5c3
```

`fb.f`'e yazdık, `fb.bits`'ten okuduk: aynı 4 byte'ı bir kez `float`, bir kez `uint32_t` olarak gördük. Bu, bir değerin ham bitlerine bakmanın yolu — **tip punning**. Tersi de çalışıyor:

```c
fb.bits = 0x40490fdb;
printf("bits = 0x%08x -> f = %g\n", fb.bits, fb.f);
```

```
bits = 0x40490fdb -> f = 3.14159
```

Bir `uint32_t` yazıp onu `float` olarak okuduk: `0x40490fdb` bit deseni, π'ye yakın bir `float`.

Aynı anda bir union'ın **sadece bir** üyesi "anlamlı"; `fb.f`'e yazınca `fb.bits` o yazının bitlerini gösterir, tersi de. İkisini aynı anda bağımsız değer olarak kullanamazsın — tek bir bellek var.

### C'de tanımlı, C++'ta değil

Ders 4.5'te bir `float`'ı `int *` ile okumanın **strict aliasing** ihlali (undefined behavior) olduğunu söylemiştik. union ile tip punning, C'de bu kuralın **istisnası**: C standardı, bir union üyesine yazıp başka bir üyesinden okumaya açıkça izin veriyor (§6.5.2.3, "son yazılandan farklı bir üyeyi okumak"). Yani union, byte'lara bakmanın Ders 4.5'teki `unsigned char *`'a ek, tanımlı bir yolu.

Önemli bir uyarı: bu **C'ye özgü**. C++'ta union ile tip punning teknik olarak undefined behavior; orada `std::bit_cast` ya da `memcpy` (Ders 3.9'da kullandığımız yol) gerekir. `memcpy` yöntemi her iki dilde de tanımlı olduğu için en taşınabilir seçenek; union, C kodunda yaygın ve okunaklı bir alternatif.

### Ders 3.12'yi doğrulamak

Artık bir `float`'ın işaret, üs ve kesir alanlarını (Ders 3.12) doğrudan çıkarabiliriz. `-2.5f` için:

```c
fb.f = -2.5f;
uint32_t b = fb.bits;
printf("-2.5f: isaret=%u us=%u kesir=0x%06x\n",
       b >> 31, (b >> 23) & 0xFF, b & 0x7FFFFF);
```

```
-2.5f: isaret=1 us=128 kesir=0x200000
```

Ders 3.18'deki kaydırma ve maskeleme ile 32 biti üçe ayırdık (Ders 3.12'deki `1 + 8 + 23` düzeni):

- **işaret = 1**: negatif.
- **üs = 128**: eğimli (biased) üs; gerçek üs 128 − 127 = 1, yani 2¹ (Ders 3.12'deki bias).
- **kesir = 0x200000**: ikilik `0.01`, yani 0.25. Mantis `1.25`, değer `1.25 × 2¹ = 2.5`, işaretle `-2.5`. Ders 3.12'de kâğıt üstünde yaptığımız hesabın bitlerini burada gözle görüyoruz.

Ders 3.13'teki özel değerler de (sonsuz, NaN) union ile incelenebilir (3. alıştırma).

---

## 2. Etiketli birleşim: tek değişken, farklı tipler

union'ın asıl kullanımı tip punning değil, **aynı anda farklı tiplerden biri** olabilen bir değer tutmak: bir hücre ya `int`, ya `double`, ya yazı. union tek başına hangi üyenin geçerli olduğunu bilmediği için, yanına bir **etiket** (tag) koyarız — buna **etiketli birleşim** (tagged union) denir:

```c
enum Kind { INT_VAL, DOUBLE_VAL, STR_VAL };

struct Value {
    enum Kind kind;        // hangi uye gecerli?
    union {
        int i;
        double d;
        const char *s;
    } as;
};
```

`kind` hangi üyenin dolu olduğunu söylüyor; `as` değerin kendisi. Okurken her zaman önce `kind`'e bakılır:

```c
void print_value(struct Value v) {
    switch (v.kind) {
        case INT_VAL:    printf("int: %d\n", v.as.i); break;
        case DOUBLE_VAL: printf("double: %g\n", v.as.d); break;
        case STR_VAL:    printf("str: %s\n", v.as.s); break;
    }
}
```

```
sizeof Value = 16
int: 42
double: 3.14
str: merhaba
```

`sizeof(struct Value)` = 16: `enum` (4) + dolgu (4) + union (8, en büyük üye `double`/pointer). union sayesinde üç tipin **toplamı** (4+8+8=20) değil, en büyüğü kadar yer harcanıyor — üç değerden aynı anda sadece biri tutulduğu için.

Etiketli birleşim, bir programlama dilinin değerlerini (Faz 8'deki yorumlayıcı, Faz 15'teki derleyicinin AST düğümleri) temsil etmenin temel yolu. Yanlış üyeyi okumak (`kind` `INT_VAL` iken `v.as.d`) bir hata; disiplin tamamen `kind`'i her zaman kontrol etmekte. Modern diller (Rust'ın `enum`'u, C++'ın `variant`'ı) bu kontrolü dile gömer; C'de programcıya düşer.

---

## 3. Bit alanları: bite kadar paketlemek

Bazen bir değer için bir `int` (32 bit) fazla: bir bayrak 1 bit, bir seviye 4 bit yeter. **Bit alanları** (bit fields), bir struct üyesinin kaç **bit** kaplayacağını belirtmeyi sağlıyor:

```c
struct Flags {
    unsigned int is_active : 1;
    unsigned int is_admin  : 1;
    unsigned int level     : 4;
    unsigned int reserved  : 2;
};
```

`: 1`, "bu üye 1 bit" demek. Toplam 8 bit, ama hizalama (Ders 4.26) yüzünden:

```c
printf("sizeof Flags = %zu\n", sizeof(struct Flags));   // 4
struct Flags f = {.is_active = 1, .level = 9};
printf("active=%u admin=%u level=%u\n", f.is_active, f.is_admin, f.level);
```

```
sizeof Flags = 4
active=1 admin=0 level=9
```

Üyelere sıradan struct üyeleri gibi erişiliyor (`f.level`), ama her biri sadece belirtilen bit sayısını kaplıyor. Ders 3.18'de bir bayrak kümesini `|`, `&`, `<<` ile elle yönetmiştik; bit alanları aynı işi, derleyiciye yaptırarak, okunaklı bir sözdizimiyle yapıyor. Bir tarih üç alana sığabilir:

```c
struct Date {
    unsigned int day   : 5;   // 1-31  (5 bit, 0-31)
    unsigned int month : 4;   // 1-12  (4 bit, 0-15)
    unsigned int year  : 23;
};
// 5 + 4 + 23 = 32 bit = 4 byte
```

### Taşma: sığmayan değer kesiliyor

Bir alana sığmayan bir değer yazarsan, fazla bitler atılır:

```c
f.level = 20;   // level 4 bit: 0-15
```

```
warning: implicit truncation from 'int' to bit-field changes value from 20 to 4 [-Wbitfield-constant-conversion]
```

`f.level` 4 olur: `20 & 0xF = 4` (20'nin alt 4 biti). Derleyici sabit değerlerde bunu uyarıyor, ama çalışırken hesaplanan bir değer sığmazsa sessizce kesilir. Bir alana ne kadar değer koyabileceğini (0 ila 2ⁿ−1) bilmek senin işin.

---

## 4. Taşınabilirlik sorunu

Bit alanları kullanışlı ama **taşınabilir değil**. Standart, alanların bir byte içinde **hangi uçtan** (düşük bitten mi yüksek bitten mi) başlayacağını belirlemiyor — **uygulamaya bağlı**. İki 4-bitlik alanı bir byte'a koyup byte'a bakalım:

```c
union U {
    struct { unsigned int a : 4; unsigned int b : 4; } f;
    uint8_t byte;
};
union U u = {0};
u.f.a = 0xA;
u.f.b = 0x5;
printf("a=0xA b=0x5 -> byte=0x%02x\n", u.byte);
```

```
macOS:          byte=0x5a
Linux aarch64:  byte=0x5a
```

İki sistemimde de ilk alan (`a`) byte'ın **düşük** 4 bitine, `b` yüksek 4 bitine gitti (`0x5a` = `b`×16 + `a`). Ama ikisi de little-endian; **big-endian** bir sistemde derleyici ilk alanı yüksek bitlere koyabilir ve aynı kod `0xa5` üretebilir. Standart hangisini garanti etmediği için, bit alanlarının bellekteki düzenine **güvenemezsin**.

Sonuç: bit alanları, **kendi programın içinde** yer tasarrufu için güzel (bir `Flags`, bir `Date`). Ama bir **ağ paketini**, bir **dosya formatını** ya da bir **donanım yazmacını** bit alanlarıyla eşlemek tehlikeli — başka bir derleyici ya da mimari bitleri başka yere koyabilir. Bu tür ikili formatlar için Ders 3.18'deki elle maskeleme (`value >> shift & mask`) daha güvenli: bitlerin nerede olacağını sen belirlersin, derleyici değil. Ders 3.9'daki endianness de işin içine girer. Faz 18'de bir ikili format DSL'i yazarken bu kuralların üreticiye nasıl kodlandığını göreceğiz.

---

## Alıştırmalar

**1** – `union { float f; uint32_t bits; }` ile `1.0f`'in bitlerini yazdır. Ders 3.12'deki `0x3f800000`'ı mı veriyor? İşaret, üs ve kesiri çıkar: üs neden 127, kesir neden 0?

**2** – `union { double d; uint64_t bits; }` ile `0.1`'in bitlerini yazdır (Ders 3.14'teki hassasiyet sorunu). `uint64_t` ve `%016llx` kullan. Aynı union'a `uint32_t bits` koysan ne olurdu — `double` 8 byte, `uint32_t` 4 byte; union kaç byte olur, `bits` `double`'ın hangi yarısını gösterir?

**3** – `float` için sonsuzu (üs hepsi 1, kesir 0) ve bir NaN'ı (üs hepsi 1, kesir sıfırdan farklı) union ile **bitlerden kurup** yazdır (Ders 3.13). `fb.bits = 0x7F800000` ne verir? `0x7FC00000`? `0xFF800000`?

**4** – Bölüm 2'deki `struct Value`'ya bir `bool` üyesi ekle (`BOOL_VAL`). `sizeof` değişir mi? Neden union'a bir `bool` eklemek boyutu büyütmedi ama `enum`'a bir değer eklemek de büyütmedi? `print_value`'da `default` dalı neden iyi bir fikir?

**5** – Ders 3.18'deki bayrak yönetimini (`flags |= 1 << 2` gibi) bit alanlarıyla yeniden yaz: `is_active`, `is_admin`, `level` (4 bit). İki yaklaşımın (elle maskeleme vs bit alanı) avantaj ve dezavantajlarını karşılaştır. Hangisi bir dosyaya yazılacak veri için doğru?

<details>
<summary>Cevaplar</summary>

**1** – `1.0f` → `0x3f800000`, evet (Ders 3.12). İşaret = 0 (pozitif). Üs biti deseni = `0x7f` = 127; gerçek üs 127 − 127 = 0, yani 2⁰ = 1. Kesir = 0, çünkü mantis tam `1.0` (gizli bit 1, kesirli kısım yok): `1.0 × 2⁰ = 1.0`. 1.0, IEEE 754'te "en temiz" sayı: işaret 0, üs tam bias, kesir 0.

**2** – `0.1` → `0x3fb999999999999a` (Ders 3.14'teki "sonsuza giden" deseni, son hane `a` yuvarlama). `uint32_t bits` koysaydık union 8 byte kalırdı (en büyük üye `double`), ama `bits` sadece `double`'ın **ilk 4 byte'ını** gösterirdi — little-endian'da (Ders 3.9) düşük yarısı (`0x9999999a`). `double`'ın tamamını görmek için 8 byte'lık `uint64_t` gerekir; küçük bir union üyesi büyük olanın sadece bir parçasına bakar.

**3** –

```c
fb.bits = 0x7F800000; printf("%g\n", fb.f);   // inf
fb.bits = 0x7FC00000; printf("%g\n", fb.f);   // nan
fb.bits = 0xFF800000; printf("%g\n", fb.f);   // -inf
```

`0x7F800000`: işaret 0, üs hepsi 1 (0xFF), kesir 0 → **+sonsuz** (`inf`). `0x7FC00000`: üs hepsi 1, kesir sıfırdan farklı (en üst kesir biti 1) → **NaN** (`nan`). `0xFF800000`: işaret 1, üs hepsi 1, kesir 0 → **−sonsuz** (`-inf`). Ders 3.13'teki özel değerleri bitlerden kurmak union ile tek satır; `1.0f/0.0f` yazmadan doğrudan deseni veriyoruz.

**4** – `sizeof(struct Value)` **değişmez**, 16 kalır. `bool` union'a eklendi; union zaten en büyük üyesi (`double`/pointer, 8 byte) kadar, `bool` (1 byte) ondan küçük olduğu için union büyümez. `enum Kind`'a bir değer (`BOOL_VAL`) eklemek de `enum`'un boyutunu değiştirmez (hâlâ bir `int`, 4 byte). `default` dalı iyi bir fikir, çünkü `kind` beklenmedik bir değer taşırsa (bozuk veri, eksik `case`) program sessizce yanlış üyeyi okumak yerine açık bir şey yapar; ayrıca derleyici `-Wswitch` ile eksik `case`'leri uyarabilir — `default` eklemek bu uyarıyı kapatmadan hata durumunu yakalar.

**5** –

```c
// Bit alani:
struct Perms { unsigned int is_active:1; unsigned int is_admin:1; unsigned int level:4; };
struct Perms p = {.is_active=1, .level=9};

// Elle maskeleme (Ders 3.18):
uint8_t perms = 0;
perms |= 1 << 0;          // is_active
perms |= 9 << 2;          // level, bit 2-5
int active = perms & 1;
int level = (perms >> 2) & 0xF;
```

**Bit alanı** avantajı: okunaklı (`p.level = 9`), derleyici maskeyi/kaydırmayı yapar, taşmayı uyarır. Dezavantajı: bellekteki bit düzeni taşınabilir değil (Bölüm 4). **Elle maskeleme** avantajı: bitlerin tam yerini sen bilirsin, her mimaride aynı — taşınabilir. Dezavantajı: daha çok kod, hata yapmaya açık. Bir **dosyaya/ağa** yazılacak veri için **elle maskeleme** doğru: bitlerin düzeni veriyi okuyacak başka bir programla (belki başka bir dilde, başka bir makinede) uyuşmak zorunda, ve bunu sadece elle kontrol ederek garanti edebilirsin. Bit alanı sadece programın kendi içinde, geçici yer tasarrufu için.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §6.8 (union), §6.9 (bit alanları).
- C standardı (ISO/IEC 9899:2018), §6.7.2.1 (bit alanları ve düzenlerinin uygulamaya bağlı olması), §6.5.2.3¶3 ve dipnot 97 (union ile tip punning'in tanımlı olması).
- Peter van der Linden, *Expert C Programming*, Bölüm 6: union ve bit alanlarının tuzakları.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §3.9.2 (union).

**Sıradaki ders:** Kendi allocator'ımız 1. Bump/arena allocator ve hizalama yuvarlaması.
