---
title: "7.18 Yükleyici ve program başlangıcı"
description: "./prog yazınca ne olur: execve, çekirdeğin ELF segmentlerini belleğe eşlemesi, ld.so, ve _start. crt0'ın işi: yığındaki argc/argv/envp, __libc_start_main, constructor'lar, main, atexit, destructor'lar, exit. main'den dönmek ile _exit'in farkı. libc olmadan, sadece write ve exit sistem çağrılarıyla (syscall komutu, inline assembly) çalışan bir program."
gereksinimler: [gcc]
---

Şimdiye kadar her programın `main`'den başladığını varsaydık. Ama Ders 7.16'da `readelf -h prog` "Entry point 0x1060" diyordu, ve `main` `0x1154`'teydi. Yani işlemcinin çalıştırdığı ilk komut `main`'in değil. Bu ders `./prog` yazdığın andan `main`'in ilk satırına kadar olanları ve `main` döndükten sonra olanları anlatıyor; sonunda da bütün bu altyapıyı atıp, libc'siz, sadece çekirdekle konuşan bir program yazıyoruz.

Çıktılar x86-64 Linux'ta (Ubuntu 24.04, gcc 13).

---

## 1. `./prog`'dan `_start`'a

Kabuk `./prog` komutunu `fork` + **`execve`** sistem çağrısıyla çalıştırır. `execve`'den sonra çekirdek (işletim sistemi, Ders 7.28):

1. Dosyanın ilk baytlarına bakar: `7f 45 4c 46`, bir ELF.
2. Program başlıklarını (Ders 7.16'daki `LOAD` satırları) okur ve her segmenti, istenen izinlerle, sürecin sanal adres uzayına **eşler** (map). Dosyayı okumuyor bile: sadece "bu sanal sayfalar şu dosyanın şu kısmı" diye not alıyor; sayfalar ilk dokunulduğunda diskten gelecek (talep üzerine sayfalama, Ders 7.27). `.bss` için sıfır sayfalar ayrılır.
3. Bir yığın ayırır ve üstüne programın argümanlarını ve ortam değişkenlerini koyar.
4. Dosyada `INTERP` varsa (dinamik bağlanmış program), önce **`ld.so`**'yu yükler ve kontrolü ona verir. `ld.so` gerekli `.so`'ları yükler, GOT'u doldurur (Ders 7.17), sonra programın giriş noktasına atlar.
5. Statik programda doğrudan giriş noktasına atlar.

Giriş noktasındaki fonksiyonun adı geleneksel olarak **`_start`**. Bizim yazmadığımız, libc'nin getirdiği bir dosyada (`crt1.o`, "C runtime"; tarihsel adıyla `crt0`) tanımlı ve `gcc` onu her programa sessizce bağlıyor.

---

## 2. `_start`'ın içi

```
$ objdump -d once | sed -n '/<_start>:/,/^$/p'
00000000000010a0 <_start>:
    10a0:  endbr64
    10a4:  xor    %ebp,%ebp
    10a6:  mov    %rdx,%r9
    10a9:  pop    %rsi
    10aa:  mov    %rsp,%rdx
    10ad:  and    $0xfffffffffffffff0,%rsp
    10b1:  push   %rax
    10b2:  push   %rsp
    10b3:  xor    %r8d,%r8d
    10b6:  xor    %ecx,%ecx
    10b8:  lea    0x115(%rip),%rdi        # 11d4 <main>
    10bf:  call   *0x2f13(%rip)           # 3fd8 <__libc_start_main@GLIBC_2.34>
    10c5:  hlt
```

Ders 7.10 ve 7.11'deki bilgiyle satır satır okunabilir:

- `xor %ebp,%ebp`: çerçeve işaretçisini sıfırla. Hata ayıklayıcı çerçeve zincirini (Ders 7.11) gezerken `rbp = 0` görünce "en dış çerçeve bu" der.
- Çekirdek yığını şöyle bırakmıştı: `[rsp]` = `argc`, `[rsp+8]` = `argv[0]`, `argv[1]`, ..., `NULL`, sonra ortam değişkenleri, `NULL`. `pop %rsi` `argc`'yi alır (2. argüman), `mov %rsp,%rdx` artık `argv`'yi gösteren adresi alır (3. argüman).
- `%rdx`'te `ld.so`'nun bıraktığı bir sonlandırma fonksiyonu vardı; `%r9`'a taşınır (6. argüman).
- `and $-16,%rsp`: yığını 16 bayta hizala. Ders 7.10'daki ABI kuralı; çekirdek bunu garanti etmez, `_start` sağlar.
- `lea main, %rdi`: **`main`'in adresi** 1. argüman. `_start` `main`'i kendisi çağırmıyor, adresini başka bir fonksiyona veriyor.
- `call __libc_start_main`: asıl iş orada. Ve o fonksiyon **hiç dönmez**: `main` bitince `exit`'i çağırır. Dönerse `hlt` (ayrıcalıklı bir komut, kullanıcı modunda çalıştırılınca süreç çöker), "buraya hiç gelinmemeli" işareti.

---

## 3. `main`'den önce ve sonra

`__libc_start_main` sırasıyla: libc'nin kendi iç yapılarını kurar (stdio tamponları, iş parçacığı yerel depolama, ve Ders 7.14'teki yığın kanaryasının rastgele değeri), **constructor**'ları çalıştırır, `main(argc, argv, envp)`'yi çağırır, ve dönüş değeriyle **`exit`**'i çağırır. `exit` de `atexit` ile kaydedilen fonksiyonları ve **destructor**'ları çalıştırır, stdio tamponlarını boşaltır, sonunda çekirdeğe "bitti" der.

Bunların hepsini görebiliriz:

```c
#include <stdio.h>
#include <stdlib.h>

__attribute__((constructor)) static void once(void) { puts("1) constructor: main'den once"); }
static void sonra(void) { puts("4) atexit: main dondukten sonra"); }
__attribute__((destructor)) static void yikici(void) { puts("5) destructor: en son"); }

int main(int argc, char **argv, char **envp) {
    atexit(sonra);
    printf("2) main: argc=%d argv[0]=%s\n", argc, argv[0]);
    int n = 0; while (envp[n]) n++;
    printf("3) ortam degiskeni sayisi > 0: %s\n", n > 0 ? "evet" : "hayir");
    return 0;
}
```

```
$ gcc -O1 once.c -o once && ./once
1) constructor: main'den once
2) main: argc=1 argv[0]=./once
3) ortam degiskeni sayisi > 0: evet
4) atexit: main dondukten sonra
5) destructor: en son
```

`main`'in üçüncü parametresi `envp`, `_start`'ın yığından aldığı ortam değişkenleri dizisi (standart C değil ama Linux ve macOS'ta çalışır). Constructor'ların adresleri ELF'te `.init_array` bölümünde bir dizi olarak durur (Ders 7.16'daki segment listesinde görmüştük); `__libc_start_main` diziyi gezip her birini çağırır. C++'ta global nesnelerin kurucuları (Faz 13) tam bu mekanizmayla çalışır.

### `exit` ile `_exit`

`main`'den `return 0` demek `exit(0)` demektir: temizlik yapılır. Doğrudan sistem çağrısı olan `_exit` ise temizliği atlar:

```c
#include <stdio.h>
#include <unistd.h>
int main(void) { printf("tamponda bekliyor"); _exit(0); }
```

```
$ ./flush
$ 
```

Hiçbir şey yazılmadı. `printf` metni stdio'nun bellekteki tamponuna koydu (satır sonu yok, boşaltılmadı); tamponu boşaltacak olan `exit`'ti, `_exit` çekirdeğe doğrudan "süreci bitir" dedi ve tampon süreçle birlikte yok oldu. Kütüphane fonksiyonu (`exit`, `printf`) ile sistem çağrısı (`_exit`, `write`) arasındaki sınır burada görünür hale geliyor.

---

## 4. Sistem çağrısı: çekirdeğe kapı

Bir kullanıcı programı ekrana doğrudan yazamaz, diske erişemez, belleği kendi başına alamaz: bunları sadece çekirdek yapabilir (Ders 7.28'deki kullanıcı/çekirdek modu). İstemek için **sistem çağrısı** yapılır. x86-64 Linux'ta kural:

| Register | İçerik |
| --- | --- |
| `rax` | Sistem çağrısı numarası (`write` = 1, `exit` = 60) |
| `rdi`, `rsi`, `rdx`, `r10`, `r8`, `r9` | Argümanlar (dördüncüsü `rcx` değil `r10`!) |
| `syscall` | Komut: çekirdek moduna geç |
| `rax` | Dönüş değeri (hata ise `-errno`) |
| `rcx`, `r11` | `syscall` tarafından bozulur (dönüş adresi ve bayraklar oraya kaydedilir) |

RISC-V'de karşılığı Ders 7.4'ten tanıdık: numara `a7`'de, argümanlar `a0`–`a5`'te, komut `ecall`. RARS'ın sistem çağrıları da bu yüzden aynı biçimdeydi.

`printf` en sonunda bir `write(1, tampon, n)` sistem çağrısı yapar; `exit` en sonunda `exit_group` çağrısı. Aradaki her şey (biçimlendirme, tamponlama, atexit) libc'nin kullanıcı modunda çalışan kodu.

---

## 5. libc olmadan bir program

Bütün altyapıyı atalım: `crt1.o` yok, libc yok, kendi `_start`'ımız var.

```c
/* libc yok: syscall'lari kendimiz yapiyoruz (x86-64 Linux) */
typedef unsigned long u64;

static long sys_write(int fd, const void *buf, u64 n) {
    long ret;
    __asm__ volatile ("syscall"
        : "=a"(ret)
        : "a"(1), "D"(fd), "S"(buf), "d"(n)   /* rax=1: write */
        : "rcx", "r11", "memory");
    return ret;
}

static void sys_exit(int code) {
    __asm__ volatile ("syscall" :: "a"(60), "D"(code));  /* rax=60: exit */
    __builtin_unreachable();
}

static u64 uzunluk(const char *s) { u64 n = 0; while (s[n]) n++; return n; }

void _start(void) {
    const char *m = "libc olmadan merhaba\n";
    long yazilan = sys_write(1, m, uzunluk(m));
    sys_exit(yazilan == 21 ? 0 : 1);
}
```

Inline assembly kısıtları (Ders 7.13): `"a"` = `rax`, `"D"` = `rdi`, `"S"` = `rsi`, `"d"` = `rdx`. Bozulanlar listesinde `rcx`, `r11` (syscall bozar) ve `memory` ("bu komut belleği okuyabilir", derleyici `buf`'ı yazmayı ertelemesin). `__builtin_unreachable` derleyiciye "exit dönmez" der.

```
$ gcc -O1 -static -nostdlib -fno-stack-protector -o nolibc nolibc.c
$ ./nolibc; echo cikis=$?
libc olmadan merhaba
cikis=0
$ ls -l nolibc
-rwxr-xr-x 1 root root 9232 nolibc
$ nm nolibc
0000000000403000 R __bss_start
0000000000403000 R _edata
0000000000403000 R _end
0000000000401000 T _start
```

Bayraklar: `-nostdlib` libc'yi ve `crt1.o`'yu bağlama; `-static` `ld.so` kullanma (`INTERP` yok, çekirdek doğrudan bizim `_start`'a atlar); `-fno-stack-protector` kanarya kodu ekleme (kanaryanın değerini libc kuruyordu, Bölüm 3). Sembol tablosunda `_start` dışında bir fonksiyon yok: `sys_write`, `uzunluk` ve `sys_exit` inline oldu. Statik libc'li `prog_static` 767 KB'tı (Ders 7.17), bu 9 KB ve çoğu ELF başlıkları ve hizalama boşluğu.

Bütün program:

```
0000000000401000 <_start>:
  401000:  endbr64
  401004:  mov    $0x0,%edx
  401009:  lea    0xff0(%rip),%rax        # 402000
  401010:  add    $0x1,%rdx
  401014:  cmpb   $0x0,(%rax,%rdx,1)
  401018:  jne    401010 <_start+0x10>     # uzunluk dongusu
  40101a:  mov    $0x1,%eax                # rax = 1 (write)
  40101f:  lea    0xfda(%rip),%rsi         # rsi = mesaj
  401026:  mov    %eax,%edi                # rdi = 1 (stdout)
  401028:  syscall
  40102a:  cmp    $0x15,%rax               # yazilan == 21 ?
  40102e:  setne  %dil
  401032:  movzbl %dil,%edi
  401036:  mov    $0x3c,%eax               # rax = 60 (exit)
  40103b:  syscall
```

16 komut, hepsini artık okuyabiliyorsun. Derleyici iki küçük akıllılık yapmış: string boş olmadığı için döngünün ilk kontrolünü atlamış (`s[0]` kesin sıfır değil), ve uzunluk zaten `rdx`'te biriktiği için onu doğrudan `write`'ın üçüncü argümanı olarak kullanmış. `rdi` = 1 için de `rax`'taki 1'i kopyalamış.

---

## Alıştırmalar

**1** – `void _start(void) { }` yazıp `-nostdlib -static` ile derle ve çalıştır. Ne olur ve çıkış kodu ne? Neden? (İpucu: `_start` bir fonksiyon gibi `ret` ile dönerse yığının tepesinde ne var?)

**2** – Bölüm 5'teki programı `argc`'yi çıkış kodu olarak döndürecek şekilde değiştir. C'de `_start`'ın parametresi yok; `argc`'yi nereden okursun? Küçük bir assembly `_start` yaz ve `./argc a b c; echo $?` ile dene.

**3** – `exit` ile `_exit` arasındaki farkı `printf("satir\n")` (satır sonlu) ile dene. Terminale yazarken ve `./flush | cat` ile bir boruya yazarken sonuç değişir mi? Neden?

**4** – Bir programın `main`'den önce çalışan kodu neden güvenlik açısından önemli olabilir? `LD_PRELOAD` ile bir `.so`'nun constructor'ı ne zaman çalışır?

**5** – `nolibc`'nin `readelf -l` çıktısında üç `LOAD` segmenti var ve adresler `0x400000`'dan başlıyor. Ders 7.16'daki PIE programın adresleri `0x0`'dan başlıyordu. Fark ne, ve `nolibc` ASLR'den yararlanır mı?

<details>
<summary>Cevaplar</summary>

**1** – `Segmentation fault`, çıkış kodu 139 (128 + 11, SIGSEGV). Çekirdek `_start`'ı `call` ile çağırmadı, atladı; yığının tepesinde bir dönüş adresi yok, `argc` var (1). `ret` bu sayıyı adres sanıp `0x1`'e atlar, orası eşlenmemiş bir sayfa, sayfa hatası (Ders 7.27, 7.28). `_start`'ın hiç dönmemesi, bir `exit` sistem çağrısıyla bitmesi gerekir; glibc'deki `hlt` de bunun için.

**2** – `_start` girişinde `[rsp]` = `argc` (Bölüm 2). C fonksiyonunun prologu `rsp`'yi değiştireceği için bunu assembly'de okumak en temizi:

```asm
    .globl _start
    .text
_start:
    movq  (%rsp), %rdi        # argc
    movq  $60, %rax           # exit(argc)
    syscall
    .section .note.GNU-stack,"",@progbits
```

`gcc -nostdlib -static argc.s -o argc && ./argc a b c; echo $?` → `4` (program adı + 3 argüman). Daha büyük bir program için `_start` `argc`'yi ve `argv` adresini (`rsp+8`) bir C fonksiyonuna argüman olarak verebilir; glibc'nin yaptığı da bu.

**3** – Terminalde stdout **satır tamponlu**: `\n` görünce boşaltılır, `_exit`'ten önce yazılmış olur. Boruya ya da dosyaya yazarken **tam tamponlu**: `\n` boşaltmaz, `_exit` tamponu kaybeder, `./flush | cat` hiçbir şey göstermez. Aynı program, çıktının nereye gittiğine göre farklı davranır; tamponlama libc'nin kararı, çekirdek sadece `write` çağrılarını görür.

**4** – Constructor'lar `main`'den, dolayısıyla programın kendi güvenlik kontrollerinden (argüman doğrulama gibi) önce çalışır. `LD_PRELOAD=./x.so prog` ile `ld.so` `x.so`'yu her şeyden önce yükler ve constructor'ını programın constructor'larından ve `main`'den önce çalıştırır; ayrıca `x.so`'daki fonksiyonlar libc'dekileri gölgeler (sembol çözümlemesinde önce bulunur, Ders 7.17). Hata ayıklama ve ölçüm araçları bunu kullanır. Bu yüzden `ld.so` setuid programlarda `LD_PRELOAD`'u ve `LD_LIBRARY_PATH`'i yok sayar: aksi halde sıradan bir kullanıcı ayrıcalıklı bir sürece kod enjekte edebilirdi.

**5** – `-static` ve `-nostdlib` ile gcc **PIE olmayan** bir `EXEC` dosyası üretti (`Type: EXEC`, giriş `0x401000`): adresler mutlak, program hep `0x400000`'a yüklenmek zorunda. PIE (`DYN`) programın adresleri ise 0'dan başlayan göreli değerler; çekirdek rastgele bir taban ekler. Yani `nolibc`'nin kodu ASLR'den yararlanmaz (yığını yine rastgele yere konur). `-static-pie` ile statik ve konumdan bağımsız program da üretilebilir, ama o zaman kendi relocation'larını düzelten bir başlangıç kodu gerekir; libc'nin `_start`'ı bunu yapıyordu.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 7.9 (yükleme) ve 8.4 (`execve`, süreç başlangıcı).
- Patrick Horgan, "Linux x86 Program Start Up, or How the heck do we get to main()?" (dbp-consulting.com).
- `man 2 execve`, `man 2 syscall` (her mimari için register tablosu), `man 3 exit`, `man 2 _exit`.
- Linux çekirdeği, `arch/x86/entry/syscalls/syscall_64.tbl`: x86-64 sistem çağrısı numaraları.

**Sıradaki ders:** Tek döngülü veri yolu (datapath). RISC-V tek döngülü işlemcinin kontrol ve veri yolları.
