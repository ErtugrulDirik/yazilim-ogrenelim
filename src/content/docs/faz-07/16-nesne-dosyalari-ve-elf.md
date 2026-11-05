---
title: "7.16 Nesne dosyaları ve ELF"
description: "Derleyicinin ürettiği .o dosyasının içi: ELF başlığı, bölümler (.text, .data, .bss, .rodata), sembol tablosu, yerel ve global semboller, tanımsız (U) semboller; readelf, objdump ve nm ile bir nesne dosyasını okumak; bağlanmış bir programda bölümlerin segmentlere (program başlıkları) dönüşmesi; strip."
gereksinimler: [gcc]
---

Bu faz boyunca `clang -c` ile `.o` dosyaları ürettik (Ders 7.13'te assembly ile C'yi birleştirirken), ama içine hiç bakmadık. Ders 2.11'de çok dosyalı bir programı ayrı ayrı derleyip bağlamıştık ("ön işleme → derleme → assembly → bağlama"); bu ders o hattın ortasındaki ürünü, **nesne dosyasını** (object file) açıyor. Linux'ta bu dosyaların biçimi **ELF** (Executable and Linkable Format): hem `.o`, hem çalıştırılabilir program, hem paylaşımlı kütüphane (`.so`) aynı biçimi kullanır. Sıradaki iki ders (bağlayıcı ve yükleyici) tamamen bu dosyanın üstüne kurulu.

Bu dersteki çıktılar x86-64 Linux'ta (Ubuntu 24.04, gcc 13) alındı. macOS'ta biçim farklı (Mach-O) ama kavramlar aynı; komutları Linux ortamında çalıştır.

---

## 1. Deney programı

İki dosya: biri değişken ve fonksiyon **tanımlıyor**, öteki onları **kullanıyor**.

```c
/* util.c */
int sayac = 5;                  /* ilk değerli global  -> .data   */
int bos_dizi[100];              /* ilk değersiz global -> .bss    */
static int gizli = 7;           /* static: dosyaya özel (yerel)   */
const char mesaj[] = "merhaba"; /* salt okunur         -> .rodata */

int kare(int x) { return x * x + gizli; }
```

```c
/* ana.c */
#include <stdio.h>
extern int sayac;
int kare(int x);
int main(void) {
    printf("%d\n", kare(sayac));
    return 0;
}
```

```
$ gcc -O0 -c util.c -o util.o
$ gcc -O1 -c ana.c  -o ana.o
$ gcc util.o ana.o -o prog
$ ./prog
32
```

`kare(5) = 25 + 7 = 32`. Şimdi `util.o`'nun içine bakalım.

---

## 2. ELF başlığı

Her ELF dosyası 64 baytlık bir başlıkla başlar. İlk dört bayt "sihirli sayı": `7f 45 4c 46`, yani `0x7f 'E' 'L' 'F'`.

```
$ readelf -h util.o
ELF Header:
  Magic:   7f 45 4c 46 02 01 01 00 00 00 00 00 00 00 00 00
  Class:                             ELF64
  Data:                              2's complement, little endian
  Type:                              REL (Relocatable file)
  Machine:                           Advanced Micro Devices X86-64
  Entry point address:               0x0
  Number of program headers:         0
  Number of section headers:         14
```

Önemli alanlar:

- **Class ELF64, little endian**: 64 bit, baytlar Ders 3.9'daki küçük-sonlu sırayla.
- **Type REL**: *yeniden konumlandırılabilir* (relocatable) dosya. Henüz son adresleri yok; bağlayıcı yerleştirecek. Bağlanmış programda bu `EXEC` ya da `DYN` olur.
- **Entry point 0x0, program header 0**: `.o` çalıştırılamaz; giriş noktası ve yükleme bilgisi yok.

---

## 3. Bölümler (sections)

Nesne dosyası, içeriği türüne göre **bölümlere** ayırır:

```
$ readelf -S -W util.o
  [Nr] Name              Type            Address          Off    Size   ES Flg
  [ 1] .text             PROGBITS        0000000000000000 000040 00001d 00  AX
  [ 2] .rela.text        RELA            0000000000000000 000210 000018 18   I
  [ 3] .data             PROGBITS        0000000000000000 000060 000008 00  WA
  [ 4] .bss              NOBITS          0000000000000000 000080 000190 00  WA
  [ 5] .rodata           PROGBITS        0000000000000000 000080 000008 00   A
  ...
  [11] .symtab           SYMTAB          0000000000000000 000110 0000d8 18
  [12] .strtab           STRTAB          0000000000000000 0001e8 000028 00
```

| Bölüm | İçerik | Bayraklar |
| --- | --- | --- |
| `.text` | Makine kodu (`kare`) | A (bellekte yer al), X (çalıştırılabilir) |
| `.data` | İlk değerli globaller (`sayac`, `gizli`) | W (yazılabilir) |
| `.bss` | İlk değersiz (sıfır) globaller (`bos_dizi`) | W, ama **NOBITS** |
| `.rodata` | Salt okunur veri (`mesaj`, string sabitleri) | Sadece A |
| `.rela.text` | `.text`'teki doldurulacak adreslerin listesi (Bölüm 5) | I (bilgi), belleğe yüklenmez |
| `.symtab`, `.strtab` | Sembol tablosu ve isimleri | Belleğe yüklenmez |

`.data` 8 bayt: `sayac` ve `gizli`, ikişer `int`. En ilginci `.bss`: boyutu `0x190 = 400` bayt (`100 * sizeof(int)`), ama türü **NOBITS** — dosyada hiç yer kaplamıyor (`.data` ile `.rodata`'nın dosya ofsetinin ikisinin de `0x80` olmasına dikkat: aradaki `.bss` dosyada sıfır bayt). 400 sıfırı dosyaya yazmak israf; ELF sadece "400 bayt sıfır gerek" diyor, yükleyici belleği ayırıp sıfırlıyor. Bu yüzden bir milyon elemanlı sıfır dizi programı büyütmez, `= {1}` ile ilk değer verirsen büyütür (Alıştırma 2).

Bölümlerin ayrılmasının sebebi **izinler**: kod çalıştırılabilir ama yazılamaz, veri yazılabilir ama çalıştırılamaz (Ders 7.14'teki NX), sabitler ikisi de değil. Aynı izinli şeyleri bir araya toplamak, işletim sisteminin sayfa sayfa (Ders 7.27) izin vermesini mümkün kılıyor.

---

## 4. Sembol tablosu ve `nm`

Bağlayıcının asıl ihtiyacı **semboller**: "bu dosya hangi isimleri tanımlıyor, hangilerini başkasından bekliyor?"

```
$ nm util.o
0000000000000000 B bos_dizi
0000000000000004 d gizli
0000000000000000 T kare
0000000000000000 R mesaj
0000000000000000 D sayac

$ nm ana.o
0000000000000000 r .LC0
                 U __printf_chk
                 U kare
0000000000000000 T main
                 U sayac
```

Harfler bölümü ve görünürlüğü söylüyor:

| Harf | Anlamı |
| --- | --- |
| `T` / `t` | `.text`'te (kod) |
| `D` / `d` | `.data`'da |
| `B` / `b` | `.bss`'te |
| `R` / `r` | `.rodata`'da |
| `U` | **Tanımsız** (undefined): bu dosya kullanıyor ama tanımlamıyor |

**Büyük harf global, küçük harf yerel.** `gizli` `static` olduğu için `d`: sadece `util.c` içinde görünür, başka dosya ona `extern` ile erişemez. Ders 2.7 ve 2.11'de öğrendiğin "`static` global = dosyaya özel" kuralının makinedeki karşılığı bu küçük harf.

`ana.o`'daki `U`'lar bağlayıcıya bir yapılacaklar listesi: `kare` ve `sayac`'ı `util.o`'da, `__printf_chk`'yi libc'de bulacak. (`printf` neden `__printf_chk` oldu? Ubuntu gcc'si varsayılan olarak `-D_FORTIFY_SOURCE` açık; Ders 7.14'teki güvenli sürümlere yönlendiriyor.) `.LC0` derleyicinin `"%d\n"` stringine verdiği iç isim.

Adreslerin hepsi `0`: her sembolün değeri, **kendi bölümünün başından** uzaklığı. `gizli`'nin `4` olması `.data`'da `sayac`'tan sonra gelmesinden. Son adresler bağlamada belirlenecek.

`readelf -s` aynı tabloyu daha ayrıntılı verir (boyut, tür, bağlanma):

```
   Num:    Value          Size Type    Bind   Vis      Ndx Name
     3: 0000000000000000    11 FUNC    GLOBAL DEFAULT    1 kare
     4: 0000000000000000     8 OBJECT  GLOBAL DEFAULT    4 mesaj
     5: 0000000000000000   400 OBJECT  GLOBAL DEFAULT    3 bos_dizi
     6: 0000000000000000     4 OBJECT  GLOBAL DEFAULT    2 sayac
```

(Bu tablo `-O1` ile derlenmiş `util.o`'dan; `Ndx` sütunu bölüm numarası, `Size` sembolün bayt cinsinden boyutu: `mesaj` 8 = "merhaba" + `\0`.)

---

## 5. `objdump`: kod ve boşluklar

```
$ objdump -d util.o
0000000000000000 <kare>:
   0:   f3 0f 1e fa             endbr64
   4:   55                      push   %rbp
   5:   48 89 e5                mov    %rsp,%rbp
   8:   89 7d fc                mov    %edi,-0x4(%rbp)
   b:   8b 45 fc                mov    -0x4(%rbp),%eax
   e:   0f af c0                imul   %eax,%eax
  11:   89 c2                   mov    %eax,%edx
  13:   8b 05 00 00 00 00       mov    0x0(%rip),%eax
  19:   01 d0                   add    %edx,%eax
  1b:   5d                      pop    %rbp
  1c:   c3                      ret
```

`0x13`'teki komut `gizli`'yi okuyor ama adres alanı **`00 00 00 00`**. Derleyici `gizli`'nin programda nereye düşeceğini bilmiyor, bir boşluk bırakıyor. Bu boşlukların listesine **relocation** (yeniden konumlandırma) denir ve bir sonraki dersin konusu. Şimdilik: `.o` dosyası "neredeyse makine kodu", eksik adresleri olan bir şablon.

---

## 6. Bağlanmış program: bölümlerden segmentlere

Bağladıktan sonra her şeyin gerçek adresi var:

```
$ nm prog | grep -E ' (kare|sayac|main|bos_dizi|mesaj)$'
0000000000004040 B bos_dizi
0000000000001149 T kare
0000000000001154 T main
0000000000002008 R mesaj
0000000000004010 D sayac
```

Ve dosyada artık **program başlıkları** (program headers) var: yükleyiciye "bu dosyanın şu parçasını belleğin şuraya, şu izinlerle koy" diyen tablo.

```
$ readelf -l -W prog
Elf file type is DYN (Position-Independent Executable file)
Entry point 0x1060
  Type           Offset   VirtAddr           FileSiz  MemSiz   Flg Align
  INTERP         0x000318 0x0000000000000318 0x00001c 0x00001c R   0x1
      [Requesting program interpreter: /lib64/ld-linux-x86-64.so.2]
  LOAD           0x000000 0x0000000000000000 0x000648 0x000648 R   0x1000
  LOAD           0x001000 0x0000000000001000 0x0001a9 0x0001a9 R E 0x1000
  LOAD           0x002000 0x0000000000002000 0x000114 0x000114 R   0x1000
  LOAD           0x002db8 0x0000000000003db8 0x000260 0x000418 RW  0x1000
  GNU_STACK      0x000000 0x0000000000000000 0x000000 0x000000 RW  0x10

 Section to Segment mapping:
   03     .init .plt .plt.got .plt.sec .text .fini
   04     .rodata .eh_frame_hdr .eh_frame
   05     .init_array .fini_array .dynamic .got .data .bss
```

İki farklı bakış var ve bu ayrım ELF'in özü:

- **Bölümler** (sections) bağlayıcı içindir: ince taneli, isimli (`.text`, `.data`, ...).
- **Segmentler** (segments, `LOAD` satırları) yükleyici içindir: aynı izinli bölümler tek segmentte toplanır. Kod segmenti `R E` (oku, çalıştır), veri segmenti `RW`.

Son `LOAD` segmentine bak: `FileSiz 0x260` ama `MemSiz 0x418`. Aradaki fark `.bss`: dosyada yok, bellekte var, yükleyici sıfırla dolduruyor. `GNU_STACK RW` (E yok), Ders 7.14'te gördüğümüz çalıştırılamaz yığın.

Tür `DYN` ve adresler küçük (`0x1149`) çünkü Ubuntu varsayılan olarak **PIE** (konumdan bağımsız çalıştırılabilir) üretir: program her çalıştırmada rastgele bir taban adrese yüklenir (ASLR, Ders 7.14) ve bu adresler o tabana göre.

---

## 7. `strip`: sembolleri atmak

Sembol tablosu çalışmak için gerekmez, sadece insanlar ve araçlar için:

```
$ strip -o prog_s prog
$ ls -l prog prog_s
-rwxr-xr-x 1 root root 16160 prog
-rwxr-xr-x 1 root root 14480 prog_s
$ nm prog_s
nm: prog_s: no symbols
```

`prog_s` aynen çalışır ama hata ayıklayıcı artık fonksiyon isimlerini gösteremez. Dağıtılan programlar genellikle strip'lenir; hata ayıklama bilgisi (`-g`, DWARF, ayrı `.debug_*` bölümleri) ayrı dosyada saklanır.

---

## Alıştırmalar

**1** – `util.c`'yi `-O1` ile derleyip `nm` çalıştır. `gizli` listede var mı? Yoksa neden? (İpucu: `-O1` `kare`'yi nasıl derledi, Ders 7.15.)

**2** – `int buyuk[1000000];` ve `int buyuk2[1000000] = {1};` tanımlayan iki ayrı dosya derle. `.o` dosyalarının boyutlarını ve `size` çıktısını karşılaştır. Hangisi 4 MB büyüdü, neden?

**3** – `nm ana.o`'da `main`'in harfi `T`. `main`'i `static int main(void)` yaparsan ne olur? Önce harfi tahmin et, sonra bağlamayı dene.

**4** – `readelf -l prog`'daki kod segmenti neden `R E` de `RWE` değil? Bir program kendi kodunu değiştirmek isteseydi (JIT derleyiciler gibi) ne yapması gerekirdi?

**5** – `const char mesaj[]` yerine `char *mesaj = "merhaba";` yazsan `nm` ve `readelf -S` nasıl değişir? `mesaj` hangi bölüme, `"merhaba"` hangi bölüme düşer?

<details>
<summary>Cevaplar</summary>

**1** – Yok. `-O1`'de derleyici `gizli`'nin `static` olduğunu ve dosyanın hiçbir yerinde değiştirilmediğini görür; değeri her zaman 7. Bu yüzden `kare`'yi `imul %edi,%edi; lea 0x7(%rdi),%eax` olarak derler (sabit katlama, Ders 7.15) ve değişkeni tamamen siler. Dışarıdan erişilemeyen (`static`) bir değişken için bunu güvenle yapabilir; global `sayac` için yapamaz, çünkü başka bir dosya onu değiştirebilir.

**2** – `buyuk` (ilk değersiz) `.bss`'e düşer, NOBITS: `.o` dosyası küçük kalır, `size` sadece `bss` sütununda 4000000 gösterir. `buyuk2 = {1}` ise `.data`'ya düşer: bir eleman sıfır değil, bütün dizi dosyaya yazılmak zorunda, `.o` yaklaşık 4 MB büyür. Kural: sıfır olan şey dosyada yer kaplamaz.

**3** – Harf `t` olur (yerel). Bağlama `undefined reference to 'main'` hatasıyla başarısız olur: libc'nin başlangıç kodu (`_start` → `__libc_start_main`, Ders 7.18) global bir `main` arıyor, yerel sembol başka dosyadan görünmüyor.

**4** – Yazma + çalıştırma aynı anda tehlikeli: Ders 7.14'teki gibi bir taşma, kodun üstüne yazıp onu çalıştırabilirdi (W^X, "yazılabilir ya da çalıştırılabilir, ikisi birden değil" ilkesi). JIT derleyiciler `mmap` ile önce yazılabilir bir sayfa ayırır, kodu yazar, sonra `mprotect` ile sayfayı `R X` yapar (ya da aynı fiziksel sayfayı iki farklı izinli sanal adrese eşler, Ders 7.27).

**5** – Artık iki ayrı nesne var: `mesaj` bir **işaretçi** (8 bayt), yazılabilir ilk değerli bir global (`nm`: `D mesaj`); `"merhaba"` stringinin kendisi ise `.rodata`'da isimsiz bir sabit. İşaretçinin içindeki adres derleme anında bilinmediği için bir relocation çıkar: `R_X86_64_64 .rodata + 0`, "buraya `.rodata`'nın gerçek adresini yaz". Ubuntu gcc'sinde (PIE) işaretçi düz `.data` yerine `.data.rel.local` adlı bir bölüme düşer: yükleme anında düzeltilmesi gereken veri ayrı tutulur. `const char mesaj[]` ise doğrudan 8 baytlık bir dizi, tek nesne, `.rodata`'da, relocation yok.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 7.1–7.5: nesne dosyaları, ELF, semboller.
- John R. Levine, *Linkers and Loaders* (1999), Bölüm 3: nesne dosyası biçimleri.
- System V ABI, "ELF Object File Format" belgesi; `man 5 elf`.
- `man readelf`, `man objdump`, `man nm`.

**Sıradaki ders:** Bağlayıcı (linker). Sembol çözümleme, relocation, statik ve dinamik bağlama, PLT/GOT.
