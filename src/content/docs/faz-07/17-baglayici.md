---
title: "7.17 Bağlayıcı (linker)"
description: "Bağlayıcının iki işi: sembol çözümleme (her U'yu bir tanımla eşlemek; tanımsız ve çoklu tanım hataları) ve relocation (boş bırakılan adresleri doldurmak; R_X86_64_PC32 ve PLT32'nin elle hesaplanması). Statik kütüphane (.a) ve sıra kuralı; paylaşımlı kütüphane (.so), dinamik bağlama, ld.so; PLT ve GOT ile dış fonksiyon çağrısı, tembel (lazy) ve hemen (BIND_NOW) bağlama; statik ve dinamik programın boyut karşılaştırması."
gereksinimler: [gcc]
---

Ders 7.16'da iki nesne dosyasına baktık: `util.o` `kare` ve `sayac`'ı **tanımlıyordu**, `ana.o` onları **kullanıyordu** (`U`), ve `ana.o`'nun makine kodunda adreslerin yerinde `00 00 00 00` boşlukları vardı. Bu boşlukları dolduran ve dosyaları tek bir programa çeviren araç **bağlayıcı** (linker, Linux'ta `ld`). `gcc util.o ana.o -o prog` dediğinde gcc arka planda `ld`'yi çağırır.

Bağlayıcının iki temel işi var:

1. **Sembol çözümleme** (symbol resolution): her kullanılan ismi tam bir tanımla eşle.
2. **Yeniden konumlandırma** (relocation): bölümleri birleştirip adres ver, sonra boşlukları gerçek adreslerle doldur.

Çıktılar Ders 7.16'daki gibi x86-64 Linux'ta (Ubuntu 24.04, gcc 13); `ana.c` ve `util.c` o dersteki dosyalar, ikisi de `-O1` ile derlendi.

---

## 1. Sembol çözümleme

Bağlayıcı her `.o` dosyasının sembol tablosunu okur, iki liste tutar: tanımlananlar ve tanımsızlar. Sonunda her tanımsızın tam **bir** tanımı olmalı. İki tipik hata, iki kuralın ihlali:

**Tanım yok:**

```
$ gcc ana.o -o x
/usr/bin/ld: ana.o: in function `main':
ana.c:(.text+0xa): undefined reference to `sayac'
/usr/bin/ld: ana.c:(.text+0xf): undefined reference to `kare'
collect2: error: ld returned 1 exit status
```

Hata mesajı derleyiciden değil, **bağlayıcıdan** (`ld`, `collect2`). `ana.c` derlenirken `kare`'nin prototipi vardı, derleyici memnundu; tanımın olmadığı ancak bağlarken anlaşıldı. `.text+0xa` ve `.text+0xf` de Bölüm 2'deki boşlukların yerleri.

**Birden fazla tanım:**

```c
/* dup.c */
int kare(int x) { return x; }
```

```
$ gcc util.o dup.o ana.o -o x
/usr/bin/ld: dup.o: in function `kare':
dup.c:(.text+0x0): multiple definition of `kare'; util.o:util.c:(.text+0x0): first defined here
```

Program genelinde global bir isim tek bir tanıma sahip olmalı (C'nin "tek tanım kuralı"). İki dosyada da bir yardımcı fonksiyona ihtiyacın varsa ya `static` yapacaksın (her dosyanın kendi yerel kopyası, Ders 7.16'daki küçük harf) ya da bir dosyada tanımlayıp başlık dosyasında bildireceksin (Ders 2.11).

---

## 2. Relocation: boşlukları doldurmak

`ana.o`'nun kodu ve relocation tablosu (`objdump -dr` her boşluğun altına ne konacağını yazar):

```
0000000000000000 <main>:
   0:   f3 0f 1e fa             endbr64
   4:   48 83 ec 08             sub    $0x8,%rsp
   8:   8b 3d 00 00 00 00       mov    0x0(%rip),%edi
                        a: R_X86_64_PC32        sayac-0x4
   e:   e8 00 00 00 00          call   13 <main+0x13>
                        f: R_X86_64_PLT32       kare-0x4
  13:   89 c2                   mov    %eax,%edx
  15:   48 8d 35 00 00 00 00    lea    0x0(%rip),%rsi
                        18: R_X86_64_PC32       .LC0-0x4
  ...
  26:   e8 00 00 00 00          call   2b <main+0x2b>
                        27: R_X86_64_PLT32      __printf_chk-0x4
```

Her relocation kaydı üç şey söyler: **nerede** (ofset, örneğin `0xa`), **hangi sembol** (`sayac`), **nasıl hesapla** (tür, `R_X86_64_PC32`). PC32 "PC'ye göreli 32 bit": yazılacak değer = `sembol + ek − konum`. Ek (`addend`) `-4`, çünkü x86'da `%rip` göreli adresleme bir sonraki komutun adresinden ölçülür ve boşluk komutun son 4 baytı (Ders 7.7).

Bağlandıktan sonra:

```
0000000000001154 <main>:
    1154:  endbr64
    1158:  sub    $0x8,%rsp
    115c:  8b 3d ae 2e 00 00    mov    0x2eae(%rip),%edi    # 4010 <sayac>
    1162:  e8 e2 ff ff ff       call   1149 <kare>
    ...
    117a:  call   1050 <__printf_chk@plt>
```

Elle doğrulayalım. Bağlayıcı `.text`'i `0x1000`'lerden, `.data`'yı `0x4000`'lerden başlattı; `main` `0x1154`'te, `kare` `0x1149`'da, `sayac` `0x4010`'da.

- `mov` komutu `0x115c`'te başlıyor, boşluk `0x115c + 2 = 0x115e`'de. Değer = `0x4010 + (−4) − 0x115e = 0x2eae`. Baytlar `ae 2e 00 00` (küçük-sonlu). ✓
- `call` `0x1162`'de, boşluk `0x1163`'te. Değer = `0x1149 − 4 − 0x1163 = −0x1e`, 32 bit ikiye tümleyende `0xffffffe2`, baytlar `e2 ff ff ff`. ✓ İşlemci çalışırken `0x1167 + (−0x1e) = 0x1149`'a atlar.

Bağlayıcının yaptığı tam olarak bu aritmetik, her relocation için bir kez. PC'ye göreli adresleme sayesinde kod hangi adrese yüklenirse yüklensin (PIE, ASLR) bu sayılar değişmiyor: `main` ile `kare` arasındaki mesafe sabit.

---

## 3. Statik kütüphane: `.a`

Statik kütüphane, `.o` dosyalarının bir **arşivi**, başka bir şey değil:

```
$ ar rcs libutil.a util.o
$ ar t libutil.a
util.o
$ gcc ana.o libutil.a -o ok && ./ok
32
```

Bağlayıcı bir arşivi tararken sadece **o ana kadar tanımsız kalan** bir sembolü tanımlayan üyeleri alır. Bu yüzden sıra önemli:

```
$ gcc libutil.a ana.o -o bad
ana.c:(.text+0xa): undefined reference to `sayac'
/usr/bin/ld: ana.c:(.text+0xf): undefined reference to `kare'
```

Arşiv önce görüldüğünde henüz hiçbir tanımsız sembol yoktu, bağlayıcı `util.o`'yu almadı ve geçti; sonra `ana.o` gelip `kare`'yi istediğinde geri dönmedi. Kural: **kütüphaneler, onları kullanan dosyalardan sonra** (`gcc main.o -lm`, `gcc -lm main.o` değil). Bu, "ihtiyaç olunca al" mantığının bedava olmayan tarafı; ama faydası büyük: libc yüzlerce `.o` içerir, programın sadece kullandıklarını alır.

---

## 4. Paylaşımlı kütüphane ve dinamik bağlama

Statik bağlamada kütüphane kodu programın **içine kopyalanır**. Bütün libc'yi statik bağlarsak:

```
$ gcc -static util.o ana.o -o prog_static && ./prog_static
32
$ ls -l prog prog_static
-rwxr-xr-x 1 root root  16128 prog
-rwxr-xr-x 1 root root 785480 prog_static
```

16 KB'a karşı 767 KB. `prog_static`'te `printf`'in ve çağırdığı her şeyin kopyası var (`nm prog_static` 861 fonksiyon listeliyor). Her program libc'nin kendi kopyasını taşısa disk ve RAM israf olur, libc'deki bir güvenlik açığı da her programın yeniden bağlanmasını gerektirir.

**Paylaşımlı kütüphane** (`.so`, shared object) bunu çözer: kod tek bir dosyada durur, program sadece "bana `libc.so.6` lazım" diye not alır, bağlama **çalışma anına** kalır.

```
$ gcc -O1 -fPIC -shared util.c -o libutil.so
$ gcc -O1 ana.c -L. -lutil -o prog_dyn
$ ./prog_dyn
./prog_dyn: error while loading shared libraries: libutil.so: cannot open shared object file: No such file or directory
$ LD_LIBRARY_PATH=. ./prog_dyn
32
```

İlk çalıştırma başarısız: bağlama zamanında `-L.` ile kütüphaneyi bulduk, ama çalışma anında onu bulup yükleyecek olan başka bir program, **dinamik bağlayıcı** `ld.so` (`/lib64/ld-linux-x86-64.so.2`, Ders 7.16'daki `INTERP` satırı). O sadece sistem dizinlerine ve `LD_LIBRARY_PATH`'e bakar. `ldd` bu aramayı önceden gösterir:

```
$ ldd prog_dyn | grep util
	libutil.so => not found
$ LD_LIBRARY_PATH=. ldd prog_dyn | grep util
	libutil.so => ./libutil.so (0x00007fffff7b9000)
```

`-fPIC` (konumdan bağımsız kod) şart: aynı `.so` her süreçte farklı bir adrese yüklenir, kodu sabit adres içeremez.

---

## 5. PLT ve GOT: çağrı adresi çalışma anında

Sorun: `printf` libc'de ve libc'nin nereye yükleneceği (ASLR) çalışmadan bilinmiyor. Ama bağlayıcı `call` komutuna bir sayı yazmak zorunda. Çözüm iki küçük tablo:

- **GOT** (Global Offset Table): veri bölümünde, her dış sembol için 8 baytlık bir adres yuvası. Yazılabilir; `ld.so` doldurur.
- **PLT** (Procedure Linkage Table): kod bölümünde, her dış fonksiyon için küçük bir "atlama kapısı".

`main`'deki çağrı libc'ye değil, aynı programdaki PLT girişine gidiyor (adres sabit, PC32 ile çözülebilir):

```
    117a:  call   1050 <__printf_chk@plt>

0000000000001050 <__printf_chk@plt>:
    1050:  endbr64
    1054:  jmp    *0x2f76(%rip)        # 3fd0 <__printf_chk@GLIBC_2.3.4>
```

PLT girişi tek iş yapar: GOT'taki `0x3fd0` yuvasında hangi adres yazıyorsa oraya **dolaylı atlar** (`jmp *`, Ders 7.9'daki atlama tablosu gibi). Program yüklenirken `ld.so` relocation tablosundaki şu kaydı işler:

```
Relocation section '.rela.plt':
  Offset          Info           Type              Sym. Name + Addend
000000003fd0  000400000007 R_X86_64_JUMP_SLO   __printf_chk@GLIBC_2.3.4 + 0
```

"`0x3fd0`'a `__printf_chk`'nin gerçek adresini yaz." Kod sayfaları salt okunur kalıyor, değişen sadece veri sayfasındaki tek bir 8 baytlık yuva. Yüzlerce süreç aynı libc kod sayfalarını paylaşabiliyor, çünkü her sürecin kendine ait olan kısmı sadece GOT.

`ld.so`'nun yaptığını izleyebiliriz:

```
$ LD_DEBUG=bindings ./prog 2>&1 | grep printf
binding file ./prog [0] to /lib/x86_64-linux-gnu/libc.so.6 [0]: normal symbol `__printf_chk' [GLIBC_2.3.4]
```

### Tembel ve hemen bağlama

İki strateji var:

- **Hemen** (BIND_NOW): `ld.so` bütün GOT yuvalarını program başlamadan doldurur. Ubuntu'nun varsayılanı; `readelf -d prog`'da `FLAGS BIND_NOW` görünür. Doldurduktan sonra GOT salt okunur yapılabilir (`GNU_RELRO`, Ders 7.16'daki segment): bir saldırgan GOT'un üstüne yazıp çağrıyı saptıramaz.
- **Tembel** (lazy): yuva önce PLT'nin kendi içine işaret eder; ilk çağrıda `ld.so`'ya düşülür, adres çözülür, yuvaya yazılır, sonraki çağrılar doğrudan gider. Başlangıç hızlı, ama GOT yazılabilir kalmak zorunda.

Tembel modu zorlayıp başlangıç GOT'una bakalım:

```
$ gcc -Wl,-z,lazy util.o ana.o -o lazy
$ objdump -d lazy | sed -n '/<__printf_chk@plt>:/,/^$/p'
    1054:  jmp    *0x2fa6(%rip)        # 4000 <__printf_chk@GLIBC_2.3.4>
$ objdump -s -j .got.plt lazy
 3ff8 00000000 00000000 30100000 00000000
```

`0x4000`'deki yuva başlangıçta `0x1030` içeriyor: PLT'nin içinde, `push $0; jmp .plt` yapan ve `ld.so`'nun çözücüsüne giden kod. İlk `printf` çağrısı bu yolu izler ve yuvayı gerçek adresle değiştirir.

---

## Alıştırmalar

**1** – `ana.o`'daki `lea 0x0(%rip),%rsi` komutu (ofset `0x15`, relocation `0x18`'de, `.LC0-0x4`) bağlanmış programda `0x1169`'da `lea 0xea0(%rip),%rsi` olarak görünüyor. Hedef adresi hesapla. Bu adres hangi bölümde olmalı, ve `nm prog`'da `mesaj` `0x2008`'deyse sonuç mantıklı mı?

**2** – `gcc -lm main.o` neden bazen `undefined reference to 'sqrt'` verir de `gcc main.o -lm` vermez? (Bölüm 3; libm'nin statik bağlandığını varsay.)

**3** – İki dosyada da `int sayac;` (ilk değersiz) yazıp bağlarsan gcc 13 ne der? `int sayac = 1;` ve `int sayac = 2;` olsaydı? (İpucu: gcc 10'dan beri varsayılan `-fno-common`.)

**4** – `prog_dyn` libc'yi ve `libutil.so`'yu dinamik kullanıyor. `libutil.so`'yu `kare`'si `x*x + 100` dönecek şekilde yeniden derleyip `prog_dyn`'i **yeniden bağlamadan** çalıştırırsan ne çıkar? `prog_static` için ne olurdu?

**5** – Ubuntu neden varsayılan olarak BIND_NOW ve RELRO kullanıyor? Tembel bağlamanın güvenlik açısından zayıf yanı ne?

<details>
<summary>Cevaplar</summary>

**1** – Komut `0x1169`'da, uzunluğu 7 bayt, bir sonraki komut `0x1170`. Hedef = `0x1170 + 0xea0 = 0x2010`. `.LC0` (`"%d\n"`) bir string sabiti, `.rodata`'da olmalı; `.rodata` `0x2000`'lerde başlıyor (`mesaj` `0x2008`'de, 8 bayt, `0x200f`'te bitiyor). `0x2010` tam `mesaj`'dan sonra, yani `util.o`'nun `.rodata`'sından sonra `ana.o`'nun `.rodata`'sı geliyor. `objdump`'ın yorumu `# 2010 <mesaj+0x8>` de bunu söylüyor: en yakın sembol `mesaj`, onun 8 bayt ötesi.

**2** – Bağlayıcı soldan sağa tarar. `-lm` önce gelince henüz tanımsız sembol yoktur, `libm.a`'dan hiçbir üye alınmaz; sonra `main.o` `sqrt`'u istediğinde arşiv geride kaldı. `main.o -lm` sırasında ise `sqrt` zaten tanımsız listesindedir ve `libm.a`'daki üye alınır. (Paylaşımlı kütüphanelerde de Ubuntu `--as-needed` kullandığı için sıra yine önemli.)

**3** – `int sayac;` iki dosyada: gcc 10 öncesi bunları "ortak sembol" (common) sayıp birleştiriyordu; gcc 10+ `-fno-common` varsayılanıyla bunlar `.bss`'te iki ayrı tanım olur ve `multiple definition of 'sayac'` hatası verilir. İlk değerli `= 1` ve `= 2` her zaman hata (iki güçlü tanım). Doğru yol: bir dosyada `int sayac = 0;`, başlık dosyasında `extern int sayac;`.

**4** – `prog_dyn` yeni kütüphaneyi yükler ve `125` yazar (25 + 100): çağrı çalışma anında GOT üzerinden çözülüyor, program dosyası değişmedi. Bu dinamik bağlamanın gücü (kütüphane güncellemesi her programı düzeltir) ve tehlikesi (uyumsuz bir güncelleme her programı bozar; bu yüzden `libc.so.6`'daki gibi sürüm numaraları ve `GLIBC_2.3.4` gibi sembol sürümleri var). `prog_static` ise eski `kare`'nin kopyasını içerdiği için `32` yazmaya devam eder.

**5** – Tembel bağlamada GOT program boyunca yazılabilir kalmak zorunda (ilk çağrıda doldurulacak). Bir bellek hatası (Ders 7.14'teki gibi bir taşma ya da serbest bırakılmış belleğe yazma) saldırgana GOT'taki bir yuvaya yazma imkânı verirse, `printf` çağrısı başka bir adrese yönlenir. BIND_NOW ile her şey başta çözülür ve RELRO o sayfaları `mprotect` ile salt okunur yapar; bedeli biraz daha yavaş başlangıç. Savunma tarafı: hatayı sömürülemez kılmak, Ders 7.14'teki kanarya ve NX ile aynı aile.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 7.6–7.12: sembol çözümleme, relocation, paylaşımlı kütüphaneler, PLT/GOT.
- John R. Levine, *Linkers and Loaders* (1999), Bölüm 4–10.
- Ian Lance Taylor, "Linkers" yazı dizisi (20 bölüm, airs.com blog): `gold` bağlayıcısının yazarından.
- Ulrich Drepper, "How To Write Shared Libraries" (2011).
- `man ld`, `man ld.so` (`LD_DEBUG`, `LD_LIBRARY_PATH`).

**Sıradaki ders:** Yükleyici ve program başlangıcı. `_start`, `crt0`, `main`'den önce olanlar, libc olmadan program yazma (syscall ile).
