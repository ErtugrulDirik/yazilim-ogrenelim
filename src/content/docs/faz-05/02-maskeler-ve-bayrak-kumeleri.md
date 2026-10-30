---
title: "5.2 Maskeler ve bayrak kümeleri"
description: "Bir sayının tek tek bitlerini yönetmek: bir biti set (| mask), clear (& ~mask), toggle (^ mask) ve test etme ((x >> n) & 1); çok bitli maskeler ve bit alanı çıkarma; tek bir sayıda düzinelerce evet/hayır bayrağı tutmak; | ile birleştirilen, tek test ile 'hepsi var mı' sorulan bir izin sistemi örneği ve Unix dosya izinleriyle bağlantısı."
---

Ders 3.21'de `enum` ve `const` ile bayrakları tanımıştık; Ders 4.27'de bit alanlarıyla bir struct'ı bite kadar paketledik ve "taşınabilir veri için elle maskeleme daha güvenli" demiştik. Bu derste o elle maskelemeyi öğreniyoruz: bir sayının **tek tek bitlerini** set etmek, temizlemek, çevirmek ve test etmek. Dört temel işlem, ve onlarla kurulan **bayrak kümeleri** — tek bir sayıda düzinelerce evet/hayır bilgisini tutmanın yolu.

---

## 1. Dört temel işlem

`n`. biti (0'dan başlayarak) hedef alan dört işlem. Hepsinin çekirdeği `1u << n`: sadece `n`. biti 1 olan bir **maske** (Ders 5.1'deki `1u`, işaretsiz; `1 << n` tehlikeli).

| İşlem | Formül | Nasıl çalışır |
| --- | --- | --- |
| **set** (1 yap) | `x \| (1u << n)` | `n`. bit 1 olur, diğerleri `\|` ile değişmez |
| **clear** (0 yap) | `x & ~(1u << n)` | `n`. bit 0 olur, diğerleri `&` ile değişmez |
| **toggle** (çevir) | `x ^ (1u << n)` | `n`. bit tersine döner (Ders 5.1'deki XOR) |
| **test** (oku) | `(x >> n) & 1u` | `n`. biti en sağa getir, gerisini maskele |

Her birini bir makroya koyabiliriz (Ders 2.11; argümanları parantezle):

```c
#define SET(x, n)    ((x) | (1u << (n)))
#define CLEAR(x, n)  ((x) & ~(1u << (n)))
#define TOGGLE(x, n) ((x) ^ (1u << (n)))
#define TEST(x, n)   (((x) >> (n)) & 1u)
```

```c
uint32_t x = 0;
x = SET(x, 0);      // 0b0001 = 1
x = SET(x, 3);      // 0b1001 = 9
x = TOGGLE(x, 1);   // 0b1011 = 11
x = CLEAR(x, 0);    // 0b1010 = 10
TEST(x, 3)          // 1
TEST(x, 2)          // 0
```

Neden bu formüller işe yarıyor:

- **set**: `|` ile 1'lenen bitler kesin 1 olur; 0'la OR'lanan bit değişmez. Maske sadece `n`. bitte 1 olduğu için yalnız o bit set edilir, gerisi korunur.
- **clear**: `~(1u << n)`, sadece `n`. biti 0, gerisi 1 olan maske. `&` ile 1'le AND'lenen bit değişmez, 0'la AND'lenen kesin 0 olur. Yani yalnız `n`. bit temizlenir.
- **toggle**: `^` ile 1'le XOR'lanan bit ters döner, 0'la XOR'lanan değişmez (Ders 5.1).
- **test**: `n`. biti en sağa kaydırıp `& 1u` ile sadece o biti bırakır. Sonuç 0 ya da 1.

`CLEAR`'daki iki operatör (`~` ve `&`) Ders 5.1'deki önceliği hatırlatıyor: `~(1u << n)`, önce kaydır sonra tümle. `TEST`'teki `& 1u` da sonucu tek bite indirmenin standart yolu.

---

## 2. Çok bitli maskeler

Tek bit yerine bir **grup** biti aynı anda hedefleyebiliriz. En sık işlem, bir sayının alt `k` bitini seçmek:

```c
uint32_t lower4 = (1u << 4) - 1;   // 0b1111 = 0xF
```

`1u << 4` = `0b10000`; bir eksiği `0b1111`, yani alt 4 bitin hepsi 1. Genel olarak `(1u << k) - 1`, alt `k` biti 1 olan maske — Ders 3.18'de bir float'ın kesirini ayırırken kullandığımız kalıbın ta kendisi.

```c
uint32_t v = 0xABCD;
v & lower4          // 0xD   (alt 4 bit)
(v >> 4) & lower4   // 0xC   (bit 4-7: once kaydir, sonra maskele)
```

Bir **bit alanını çıkarmak** (bit `p`'den başlayan `k` bit): `(v >> p) & ((1u << k) - 1)`. Önce istenen alanı en sağa kaydır, sonra `k` bitlik maskeyle kes. Ders 4.27'de bit alanlarının (bitfield) taşınabilir olmadığını söylemiştik; bu formül aynı işi, bitlerin yerini **sen** belirleyerek yapıyor — her makinede aynı.

---

## 3. Bayrak kümeleri: tek sayıda çok bilgi

Asıl güç burada. Bir programda düzinelerce evet/hayır ayarı olabilir: bir pencere görünür mü, düzenlenebilir mi, kenarlıklı mı… Her biri için ayrı bir `bool` yerine, hepsini **tek bir sayının bitlerinde** tutabiliriz. Her bayrak bir bit:

```c
enum {
    PERM_READ    = 1u << 0,   // 1
    PERM_WRITE   = 1u << 1,   // 2
    PERM_EXECUTE = 1u << 2,   // 4
    PERM_DELETE  = 1u << 3,   // 8
};
```

Her sabit 2'nin bir kuvveti, yani tam bir bit (Ders 3.21'deki `enum`). Bir bayrak **kümesi** kurmak, onları `|` ile birleştirmek:

```c
uint32_t user = PERM_READ | PERM_WRITE;   // 0b0011: okuma + yazma
```

Tek bir `uint32_t`'de 32 bağımsız bayrak sığar. İşlemler, Bölüm 1'deki dördünün maske halleri:

```c
user |= PERM_EXECUTE;    // ekle:    0b0111
user &= ~PERM_WRITE;     // kaldir:  0b0101
```

Test iki türlü. **Tek bir bayrak var mı?** `(user & FLAG) != 0`:

```c
(user & PERM_READ)   != 0   // 1: okuyabilir
(user & PERM_DELETE) != 0   // 0: silemez
```

(Ders 5.1'deki öncelik tuzağı: `& `mutlaka parantez içinde.) **Birden fazla bayrağın hepsi var mı?** Maskeleri birleştirip sonucun maskeye eşit olmasına bak:

```c
uint32_t need = PERM_READ | PERM_EXECUTE;
(user & need) == need    // 1: hem r hem x var
```

`user & need`, `need`'deki bitlerden `user`'da da olanları verir; bu `need`'e eşitse, `need`'in **bütün** bitleri `user`'da var demektir. "Herhangi biri var mı?" için ise `(user & need) != 0`. İki satır arasındaki fark, "hepsi" ile "herhangi biri" ayrımı.

Bir izin dizisini yazdıralım:

```c
void print_perms(uint32_t p) {
    putchar((p & PERM_READ)    ? 'r' : '-');
    putchar((p & PERM_WRITE)   ? 'w' : '-');
    putchar((p & PERM_EXECUTE) ? 'x' : '-');
    putchar((p & PERM_DELETE)  ? 'd' : '-');
    putchar('\n');
}
```

```
rw--      (READ | WRITE)
rwx-      (EXECUTE eklendi)
r-x-      (WRITE kaldirildi)
```

---

## 4. Gerçek dünya: Unix dosya izinleri

Bu kalıp her yerde. Unix dosya izinleri (`rwxr-xr-x`) tam olarak böyle çalışıyor: 9 bit, üç gruba (sahip, grup, diğerleri) ayrılmış, her grupta read-write-execute. `chmod 755` komutundaki `755` bu bitlerin **sekizlik** (octal) yazılışı — her sekizlik basamak tam 3 bit (Ders 3.10):

```c
printf("%o\n", 0755);              // 755
(0755 >> 6) & 7                    // 7 = rwx (sahip: ust 3 bit)
(0755 >> 3) & 7                    // 5 = r-x (grup)
0755 & 7                           // 5 = r-x (digerleri)
```

C'de `0` ile başlayan sayı **sekizlik** (Ders 3.10); `0755` = 7×64 + 5×8 + 5 = 493. Sekizlik kullanmanın sebebi, her basamağın tam bir rwx grubuna denk gelmesi — izinleri okumayı kolaylaştırıyor. `(x >> 6) & 7`, Bölüm 2'deki bit alanı çıkarma: sahip grubunu (üst 3 bit) al.

Aynı bayrak-kümesi kalıbı işletim sistemi çağrılarında (`open`'ın `O_RDONLY | O_CREAT` bayrakları, Faz 10), grafik kütüphanelerinde, ağ protokollerinde — kısaca "bir sürü aç/kapa ayarı" olan her yerde karşına çıkacak. Bir `uint32_t` 32 bayrak, bir `uint64_t` 64 bayrak tutar; daha fazlası için Ders 5.20'deki bitset.

---

## Alıştırmalar

**1** – `SET`, `CLEAR`, `TOGGLE`, `TEST` makrolarını kullanarak `0`'dan başlayıp sırasıyla: bit 5'i set et, bit 2'yi set et, bit 5'i toggle et, bit 7'yi test et. Her adımda değeri ikilik yaz. Son değer kaç?

**2** – `n`. bitin değerini (0 ya da 1) verilen `v`'ye **ayarlayan** `set_bit_to(uint32_t x, int n, int v)` yaz — `v` 1 ise set, 0 ise clear, ama dalsız (if'siz). (İpucu: önce biti temizle, sonra `v << n` ile OR'la.)

**3** – Bir sayının `[p, p+k)` bit aralığını, başka bir `value`'nun alt `k` bitiyle **değiştiren** `replace_bits(uint32_t x, int p, int k, uint32_t value)` yaz. (İpucu: o aralığı temizle, `value`'yu `p` kadar kaydırıp OR'la.)

**4** – İzin sisteminde "sadece okuma" (`PERM_READ`, başka hiçbir şey yok) olup olmadığını test eden bir ifade yaz. `(user & PERM_READ) != 0` neden yetmez? `user == PERM_READ` doğru mu?

**5** – `chmod` değerini çözümle: `0644` hangi izinleri verir (sahip, grup, diğerleri için rwx)? `0755` ile farkı ne? Bir `uint32_t mode`'dan, sahibin yazma izni olup olmadığını test eden ifadeyi yaz (ipucu: sahip bitleri 6-8, yazma bit 7).

<details>
<summary>Cevaplar</summary>

**1** – Başlangıç `0b00000000`. `SET(.,5)` → `0b00100000` (32). `SET(.,2)` → `0b00100100` (36). `TOGGLE(.,5)` → `0b00000100` (4, bit 5 geri kapandı). `TEST(.,7)` → 0 (bit 7 hiç set edilmedi). Son değer **4**.

**2** –

```c
uint32_t set_bit_to(uint32_t x, int n, int v) {
    x &= ~(1u << n);              // once temizle
    x |= (uint32_t)(v & 1) << n;  // sonra v'nin bitini koy
    return x;
}
```

`v & 1`, `v`'nin sadece alt bitini alır (0 ya da 1 garantisi); `<< n` ile yerine taşıyıp OR'lar. Önce temizlemek şart: yoksa `v=0` iken OR hiçbir şey yapmaz, eski 1 kalırdı. If yok — dalsız (Ders 5.5'e köprü).

**3** –

```c
uint32_t replace_bits(uint32_t x, int p, int k, uint32_t value) {
    uint32_t mask = ((1u << k) - 1) << p;   // [p, p+k) araligi 1
    x &= ~mask;                             // araligi temizle
    x |= (value << p) & mask;               // value'yu yerlestir, tasmayi kes
    return x;
}
```

`(1u << k) - 1` alt `k` bit (Bölüm 2), `<< p` ile aralığa taşınır. `~mask` ile aralık temizlenir, `value << p` ile yeni değer konur; `& mask`, `value`'nun `k` bitten taşan kısmını keser (güvenlik). `k = 32` için `1u << 32` UB olur (Ders 5.1); gerçek kodda bu uç durum ayrıca ele alınır.

**4** – "Sadece okuma" için `(user & PERM_READ) != 0` **yetmez**: bu sadece "okuma biti var mı" der, başka bitler de olabilir (`rwx` de bu testi geçer). "Sadece okuma" = "okuma var **ve** başka hiçbir şey yok". `user == PERM_READ` **doğru**: `user` tam olarak `PERM_READ` (yani `0b0001`) ise, başka hiçbir bit set değil demektir. Bir bayrağın "en az var mı" (`& != 0`) ile "tam olarak bu mu" (`==`) soruları farklı.

**5** – `0644`: sahip 6 = `rw-` (read+write, execute yok), grup 4 = `r--`, diğerleri 4 = `r--`. Yani "sahip okuyup yazabilir, herkes okuyabilir" — sıradan bir veri dosyası. `0755`: sahip 7 = `rwx`, grup/diğerleri 5 = `r-x` — çalıştırılabilir dosya ya da dizin (herkes girebilir/çalıştırabilir, sadece sahip değiştirebilir). Fark: `0755` herkese execute (+x) ve sahibe +x verir, `0644` hiç execute vermez. Sahibin yazma izni: sahip yazma biti, octal 6-8 bitlerinin ortası = bit 7. `(mode >> 7) & 1` ya da `(mode & 0200) != 0` (`0200` = sahip yazma maskesi).

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.9: bit operatörleriyle maskeler.
- Sean Anderson, "Bit Twiddling Hacks": bit set/clear/toggle kalıpları.
- `chmod(1)` ve `open(2)` man sayfaları: gerçek bayrak kümeleri.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.1: bit düzeyinde işlemler ve maskeler.

**Sıradaki ders:** En sağdaki bitler. `x & (x-1)`, `x & -x` ve `x | (x+1)` formülleri ve ispatları.
