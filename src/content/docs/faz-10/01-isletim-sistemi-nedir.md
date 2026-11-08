---
title: "10.1 İşletim sistemi nedir"
description: "İşletim sisteminin üç işi: sanallaştırma (CPU → süreç, bellek → adres alanı, disk → dosya), koruma ve kaynak yönetimi; çekirdek ile kullanıcı alanı; aynı satırı printf, write, syscall() ve ham svc/syscall komutuyla yazdırmak; strace ile bir merhaba programının yaptığı 33 sistem çağrısını tek tek okumak, strace -c ve -f; bir sistem çağrısının maliyeti (fonksiyon çağrısı 0.9 ns, getppid 121 ns) ve vDSO'nun clock_gettime'ı neden strace'te görünmez yaptığı; /proc ile çekirdeğin bir süreç hakkında bildiklerine bakmak."
---

Faz 7'de bir programın makinede neye dönüştüğünü gördük: komutlar, register'lar, yığın çerçeveleri, ELF dosyaları. Ama bir yeri hep "çekirdeğe bırakıyoruz" diye geçtik. Ders 7.18'de `printf`'in sonunda bir `syscall` komutu vardı; Ders 7.27'de sayfa hatası "kontrol işletim sistemine geçer" diye bitiyordu; Ders 7.28'de `SIGSEGV`'yi işletim sistemi üretiyordu. Faz 10 o tarafa geçiyor: programın üzerinde çalıştığı yazılım katmanı ve onunla nasıl konuşulduğu.

Bir derleyici yazarı için bunun iki nedeni var. Birincisi, derleyicinin ürettiği her program bu ortamda çalışıyor: `main`'e nasıl gelindiği, `malloc`'un belleği nereden aldığı, `printf`'in neden bazen hiçbir şey yazmadığı hep işletim sisteminin kuralları. İkincisi, derleyicinin **kendisi** de bir program: dosya okuyor, alt süreç başlatıyor (`cc`, bağlayıcıyı ayrı bir süreç olarak çağırır), paralel derliyor, JIT derleyiciler çalışırken bellek ayırıp içine kod yazıyor. Bu fazın sonunda bunların hepsini kendimiz yazmış olacağız.

Bu fazdaki çıktılar **arm64 Linux**'ta alındı (Ubuntu 24.04, clang 18, Apple M2 üzerinde sanal makine; [Kurulum → Linux ortamı](/kurulum/linux/) sayfasındaki macOS kurulumunun aynısı). Windows'ta WSL kullananlar x86-64 Linux'ta: kodlar aynı çalışıyor, mimariye bağlı farkları (sistem çağrısı numaraları, makine kodu) yeri geldikçe ikisi için de veriyoruz.

---

## 1. İşletim sisteminin üç işi

Donanımın kendisi kaba: bir (ya da birkaç) işlemci, bir büyük bayt dizisi olarak bellek, blok blok okunup yazılan bir disk, bir ağ kartı. Üzerinde aynı anda bir tarayıcı, bir editör, bir derleyici ve yüzlerce arka plan programı çalışıyor ve hiçbiri diğerlerinin varlığından haberdar değil. Bunu mümkün kılan işletim sisteminin üç işi (Arpaci-Dusseau'nun *Three Easy Pieces*'teki bölümlemesi):

1. **Sanallaştırma.** Her programa makinenin tamamı kendisininmiş gibi görünen bir **soyutlama** veriliyor:
   - İşlemci → **süreç** (process). Her program kendi işlemcisi varmış gibi çalışıyor; çekirdek gerçek çekirdekleri saniyede yüzlerce kez programlar arasında paylaştırıyor (Ders 10.14).
   - Bellek → **adres alanı**. Her süreç `0x0`'dan başlayan kendi sanal belleğini görüyor; sayfa tabloları onu fiziksel belleğe çeviriyor (Ders 7.27).
   - Disk → **dosya**. Bloklar, sektörler, sürücü ayrıntıları yerine adı olan, büyüyebilen bayt dizileri (Ders 10.2, 10.15).
2. **Koruma.** Bir süreç diğerinin belleğini okuyamamalı, diski doğrudan yazamamalı, işlemciyi sonsuza kadar elinde tutamamalı. Bunun donanım temeli Ders 7.28'deki **kullanıcı modu / çekirdek modu** ayrımı: ayrıcalıklı komutlar (sayfa tablosunu değiştirmek, kesmeleri kapatmak, aygıt register'larına yazmak) sadece çekirdek modunda çalışıyor.
3. **Kaynak yönetimi.** Sınırlı olan her şeyi (işlemci zamanı, bellek, dosya tanımlayıcıları, ağ bant genişliği) adil ve verimli paylaştırmak, işi biten süreçten geri almak.

Bu üç işi yapan, çekirdek modunda çalışan yazılıma **çekirdek** (kernel) diyoruz. "İşletim sistemi" bazen sadece çekirdeği, bazen çekirdekle birlikte gelen kütüphaneleri ve araçları (libc, kabuk, `ls`) kapsıyor. Bu fazda ikisini ayırıyoruz: **çekirdek** + **kullanıcı alanı** (user space). Bizim programlarımız, libc ve kabuk kullanıcı alanında.

---

## 2. Çekirdeğe kapı: sistem çağrısı

Kullanıcı modundaki bir program çekirdekten bir şey istemek için **sistem çağrısı** (system call, syscall) yapar: argümanları belirli register'lara koyar ve işlemciyi çekirdek moduna geçiren özel komutu çalıştırır (Ders 7.18, 7.28). Komut ve kural mimariye göre değişiyor:

| | x86-64 Linux | arm64 Linux |
| --- | --- | --- |
| Komut | `syscall` | `svc #0` |
| Çağrı numarası | `rax` | `x8` |
| Argümanlar | `rdi, rsi, rdx, r10, r8, r9` | `x0`–`x5` |
| Dönüş | `rax` | `x0` |
| `write`'ın numarası | 1 | 64 |
| `exit`'in numarası | 60 | 93 |

Hata durumunda çekirdek `-errno` döndürür (örneğin `-9` = `-EBADF`). Libc'deki sarmalayıcı fonksiyon (`write`, `read`, ...) bunu `-1`'e çevirip hatayı `errno` değişkenine koyar: C'de alıştığımız kural.

Aynı satırı dört katmanda yazdıralım:

```c
/* Ayni "merhaba"yi dort katmanda yazdirmak: stdio, libc sarmalayicisi, syscall(), ham komut */
#include <stdio.h>
#include <sys/syscall.h>
#include <unistd.h>

static long ham_write(long fd, const void *buf, long n) {
#if defined(__x86_64__)
    long r;
    __asm__ volatile ("syscall" : "=a"(r) : "a"(1L), "D"(fd), "S"(buf), "d"(n) : "rcx", "r11", "memory");
    return r;
#elif defined(__aarch64__)
    register long x8 __asm__("x8") = 64;          /* arm64 Linux: write = 64 */
    register long x0 __asm__("x0") = fd;
    register long x1 __asm__("x1") = (long)buf;
    register long x2 __asm__("x2") = n;
    __asm__ volatile ("svc #0" : "+r"(x0) : "r"(x8), "r"(x1), "r"(x2) : "memory");
    return x0;
#endif
}

int main(void) {
    printf("1: stdio (printf)\n");
    fflush(stdout);
    write(1, "2: libc sarmalayicisi (write)\n", 30);
    syscall(SYS_write, 1, "3: syscall(SYS_write, ...)\n", 27);
    long r = ham_write(1, "4: ham komut (svc / syscall)\n", 29);
    printf("ham_write donus degeri: %ld, SYS_write = %d\n", r, SYS_write);
    long hata = ham_write(99, "x", 1);
    printf("gecersiz fd ile: %ld (-EBADF)\n", hata);
    return 0;
}
```

```
$ cc -O2 ham.c -o ham && ./ham
1: stdio (printf)
2: libc sarmalayicisi (write)
3: syscall(SYS_write, ...)
4: ham komut (svc / syscall)
ham_write donus degeri: 29, SYS_write = 64
gecersiz fd ile: -9 (-EBADF)
```

Dört satır da sonunda **aynı** şeye dönüşüyor: çekirdeğe "1 numaralı dosya tanımlayıcısına şu baytları yaz" isteği. Katmanlar şunu ekliyor:

- `syscall()`: numarayı ve argümanları register'lara koyan genel bir libc fonksiyonu. Libc'nin sarmalayıcı yazmadığı yeni çağrılar için kullanılır.
- `write()`: o çağrı için hazır sarmalayıcı; `-errno`'yu `errno`'ya çevirir.
- `printf()`: biçimlendirme ve **tamponlama**. `fflush` olmadan 1. satır, 2. satırdan **sonra** çıkabilirdi: stdio onu bir tamponda bekletiyor (Ders 10.3).

Ham çağrı `-9` döndürdü, `-1` değil; çünkü arada `errno`'ya çeviren bir libc yok.

---

## 3. strace: bir programın çekirdekle konuşmasını dinlemek

`strace`, bir programın yaptığı **her** sistem çağrısını argümanları ve dönüş değeriyle yazdırır. Arkasında `ptrace` sistem çağrısı var: izleyen süreç, izlenen süreç her çekirdeğe girdiğinde ve çıktığında durdurulup haber alıyor (hata ayıklayıcıların kullandığı mekanizma; Ders 10.19). Kurulum: `sudo apt install strace`.

En basit program:

```c
#include <stdio.h>
int main(void) {
    printf("merhaba\n");
    return 0;
}
```

```
$ cc -O2 merhaba.c -o merhaba && strace ./merhaba
execve("./merhaba", ["./merhaba"], 0xfffff4ecdd70 /* 6 vars */) = 0
brk(NULL)                               = 0xaaaab9604000
mmap(NULL, 8192, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_ANONYMOUS, -1, 0) = 0xffff8dc4f000
faccessat(AT_FDCWD, "/etc/ld.so.preload", R_OK) = -1 ENOENT (No such file or directory)
openat(AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC) = 3
fstat(3, {st_mode=S_IFREG|0644, st_size=11171, ...}) = 0
mmap(NULL, 11171, PROT_READ, MAP_PRIVATE, 3, 0) = 0xffff8dc4c000
close(3)                                = 0
openat(AT_FDCWD, "/lib/aarch64-linux-gnu/libc.so.6", O_RDONLY|O_CLOEXEC) = 3
read(3, "\177ELF\2\1\1\3\0\0\0\0\0\0\0\0\3\0\267\0\1\0\0\0\360\206\2\0\0\0\0\0"..., 832) = 832
fstat(3, {st_mode=S_IFREG|0755, st_size=1722920, ...}) = 0
mmap(NULL, 1892240, PROT_NONE, MAP_PRIVATE|MAP_ANONYMOUS|MAP_DENYWRITE, -1, 0) = 0xffff8da48000
mmap(0xffff8da50000, 1826704, PROT_READ|PROT_EXEC, MAP_PRIVATE|MAP_FIXED|MAP_DENYWRITE, 3, 0) = 0xffff8da50000
munmap(0xffff8da48000, 32768)           = 0
munmap(0xffff8dc0e000, 32656)           = 0
mprotect(0xffff8dbea000, 77824, PROT_NONE) = 0
mmap(0xffff8dbfd000, 20480, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_FIXED|MAP_DENYWRITE, 3, 0x19d000) = 0xffff8dbfd000
mmap(0xffff8dc02000, 49040, PROT_READ|PROT_WRITE, MAP_PRIVATE|MAP_FIXED|MAP_ANONYMOUS, -1, 0) = 0xffff8dc02000
close(3)                                = 0
set_tid_address(0xffff8dc4ff90)         = 17
set_robust_list(0xffff8dc4ffa0, 24)     = 0
rseq(0xffff8dc505e0, 0x20, 0, 0xd428bc00) = 0
mprotect(0xffff8dbfd000, 12288, PROT_READ) = 0
mprotect(0xaaaab627f000, 4096, PROT_READ) = 0
mprotect(0xffff8dc54000, 8192, PROT_READ) = 0
prlimit64(0, RLIMIT_STACK, NULL, {rlim_cur=8192*1024, rlim_max=RLIM64_INFINITY}) = 0
munmap(0xffff8dc4c000, 11171)           = 0
fstat(1, {st_mode=S_IFIFO|0600, st_size=0, ...}) = 0
getrandom("\x37\xc7\xc2\xaf\x9b\x0d\x28\x01", 8, GRND_NONBLOCK) = 8
brk(NULL)                               = 0xaaaab9604000
brk(0xaaaab9625000)                     = 0xaaaab9625000
write(1, "merhaba\n", 8merhaba
)                = 8
exit_group(0)                           = ?
+++ exited with 0 +++
```

İki satırlık bir program için 33 çağrı. Okuyalım; hepsi önceki derslerden tanıdık:

- `execve`: kabuğun bu programı başlatma isteği; çekirdek ELF'i yükleyip dinamik bağlayıcıyı (`ld-linux`) başlatıyor (Ders 7.18). Çıktıdaki ilk satır aslında yeni programın değil, onu başlatan çağrının dönüşü.
- `openat("/etc/ld.so.cache")`, `openat(".../libc.so.6")`, `read(3, "\177ELF...")`: dinamik bağlayıcı libc'yi arıyor, açıyor, ELF başlığını okuyor (Ders 7.16, 7.17). Dönen `3`, yeni açılan dosyanın **dosya tanımlayıcısı** (Ders 10.2): 0, 1, 2 zaten stdin, stdout, stderr.
- `mmap(..., PROT_READ|PROT_EXEC, ..., 3, 0)`: libc'nin kod bölümü belleğe **eşleniyor**, okunmuyor (Ders 10.7). `mprotect(..., PROT_READ)`: bağlama bitince bazı bölgeler salt okunur yapılıyor (RELRO; Ders 10.16).
- `set_tid_address`, `set_robust_list`, `rseq`: iş parçacığı altyapısının kurulumu (Ders 10.9).
- `fstat(1, {st_mode=S_IFIFO...})`: stdio, stdout'un ne olduğuna bakıyor. Burada bir boru (çıktı `strace`'e gidiyor); terminal olsaydı `S_IFCHR`. Bu cevap stdout'un **satır tamponlu mu, tam tamponlu mu** olacağını belirliyor (Ders 10.3).
- `brk`: `malloc`'un yığın (heap) bölgesini büyütmesi; stdio tamponu için bellek (Ders 4.22, 10.7).
- `write(1, "merhaba\n", 8)`: programın asıl işi. Tek satır.
- `exit_group(0)`: `return 0` → `exit` → bütün iş parçacıklarını bitir. Dönüş değeri `?`, çünkü dönmüyor.

Programın "asıl" işi tek bir `write`; geri kalan 32 çağrı programın çalışabilir hale gelmesi. Bu oran tipik: kısa ömürlü programların (derleyicinin her `.c` dosyası için başlattığı `cc1` gibi) başlangıç maliyeti önemli olabilir. Statik bağlanmış bir programda (`-static`) dinamik bağlayıcı kısmı tamamen kayboluyor (Alıştırma 2).

### strace'in kullanışlı seçenekleri

`-c`: tek tek yazdırmak yerine **özet** tablo:

```
$ strace -c ./merhaba > /dev/null
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
  0.00    0.000000           0         1         1 ioctl
  0.00    0.000000           0         1         1 faccessat
  0.00    0.000000           0         2           openat
  0.00    0.000000           0         2           close
  0.00    0.000000           0         1           read
  0.00    0.000000           0         1           write
  0.00    0.000000           0         3           fstat
  0.00    0.000000           0         1           set_tid_address
  0.00    0.000000           0         1           set_robust_list
  0.00    0.000000           0         3           brk
  0.00    0.000000           0         3           munmap
  0.00    0.000000           0         1           execve
  0.00    0.000000           0         6           mmap
  0.00    0.000000           0         4           mprotect
  0.00    0.000000           0         1           prlimit64
  0.00    0.000000           0         1           getrandom
  0.00    0.000000           0         1           rseq
------ ----------- ----------- --------- --------- ----------------
100.00    0.000000           0        33         2 total
```

Bu sefer stdout `/dev/null` olduğu için fazladan bir `ioctl` var: stdio "bu bir terminal mi?" diye soruyor (`isatty`), cevap hayır (`ENOTTY`). Daha büyük bir programda `-c` asıl işi gösteriyor; `ls -l /usr/bin`:

```
$ strace -c ls -l /usr/bin > /dev/null
% time     seconds  usecs/call     calls    errors syscall
------ ----------- ----------- --------- --------- ----------------
 55.93    0.007041          16       436           statx
 21.88    0.002754           6       436       436 lgetxattr
 17.20    0.002165           6       350           listxattr
  4.27    0.000537           6        86           readlinkat
  0.17    0.000021           3         7           write
...
```

Dizindeki 436 dosyanın her biri için bir `statx` (dosya bilgisi; Ders 10.15) ve genişletilmiş öznitelik sorguları. `ls -l`'nin süresinin neredeyse tamamı bu; çıktının kendisi sadece 7 `write`.

Diğer seçenekler:

- `-e trace=write,openat`: sadece seçilen çağrılar. `-e trace=file`, `-e trace=process`, `-e trace=network` gibi gruplar da var.
- `-f`: `fork` ile oluşan **alt süreçleri** de izle (Ders 10.4). Kabuğun bir boru hattını nasıl kurduğunu görmek için:

```
$ strace -f -e trace=execve,clone,wait4 sh -c "ls / | wc -l"
execve("/usr/bin/sh", ["sh", "-c", "ls / | wc -l"], 0xffffd066df38 /* 6 vars */) = 0
clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, child_tidptr=0xffffa9e80ff0) = 16
strace: Process 16 attached
[pid    15] clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD ...) = 17
[pid    16] execve("/usr/bin/ls", ["ls", "/"], 0xaaaad1a406e0 /* 6 vars */) = 0
[pid    15] wait4(-1,  <unfinished ...>
[pid    17] execve("/usr/bin/wc", ["wc", "-l"], 0xaaaad1a406e0 /* 6 vars */) = 0
```

Kabuk (pid 15) iki kez kendini kopyalıyor (`clone`, `fork`'un Linux'taki genel hali), kopyalardan biri `ls`'ye, diğeri `wc`'ye dönüşüyor (`execve`), kabuk ikisini bekliyor (`wait4`). Ders 10.4 ve 10.5'te bu üç çağrıyla kendi kabuğumuzu yazacağız.

- `-T`: her çağrının süresi; `-tt`: zaman damgası; `-p PID`: çalışmakta olan bir sürece bağlan.

:::tip[strace bir hata ayıklama aracı]
"Program dosyayı bulamıyor", "neden takılı kalıyor", "hangi yapılandırma dosyasını okuyor" sorularının çoğu kaynak koda bakmadan `strace` ile cevaplanır: `ENOENT` dönen `openat`'ler hangi yolların denendiğini, son çağrının `read` ya da `futex` olması neyi beklediğini söyler. macOS'taki karşılığı `dtruss` (SIP nedeniyle kısıtlı); Linux'ta `ltrace` de kütüphane çağrılarını aynı şekilde izler.
:::

---

## 4. Bir sistem çağrısı ne kadar sürer?

Kullanıcı modundan çekirdek moduna geçmek bir fonksiyon çağrısından çok daha pahalı: işlemci modu değişiyor, register'lar çekirdek yığınına kaydediliyor, çekirdek argümanları doğruluyor, dönüşte her şey geri yükleniyor. Spectre/Meltdown sonrası azaltmalar (sayfa tablosu değişimi, dal tahmincisi temizliği) bunu daha da artırdı. Ölçelim:

```c
/* Bir sistem cagrisinin maliyeti: siradan fonksiyon cagrisi, getppid, vDSO'lu clock_gettime */
#include <stdio.h>
#include <sys/syscall.h>
#include <time.h>
#include <unistd.h>

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

__attribute__((noinline)) static long bos_fonksiyon(long x) { __asm__ volatile(""); return x + 1; }

int main(void) {
    enum { N = 5000000 };
    volatile long s = 0;
    double t0 = simdi();
    for (long i = 0; i < N; i++) s += bos_fonksiyon(i);
    double t1 = simdi();
    for (long i = 0; i < N; i++) s += syscall(SYS_getppid);
    double t2 = simdi();
    struct timespec ts;
    for (long i = 0; i < N; i++) { clock_gettime(CLOCK_MONOTONIC, &ts); s += ts.tv_nsec; }
    double t3 = simdi();
    printf("fonksiyon cagrisi        : %6.2f ns\n", (t1 - t0) / N * 1e9);
    printf("getppid (sistem cagrisi) : %6.2f ns\n", (t2 - t1) / N * 1e9);
    printf("clock_gettime (vDSO)     : %6.2f ns\n", (t3 - t2) / N * 1e9);
    return 0;
}
```

```
$ cc -O2 maliyet.c -o maliyet && ./maliyet
fonksiyon cagrisi        :   0.94 ns
getppid (sistem cagrisi) : 120.68 ns
clock_gettime (vDSO)     :  16.73 ns
```

`getppid` neredeyse hiçbir iş yapmayan bir çağrı (çekirdekteki bir alanı okuyup döndürüyor); 121 ns'nin tamamı **geçiş maliyeti**, bir fonksiyon çağrısının ~130 katı. (Sanal makinede ölçüldü; çıplak donanımda daha ucuz, x86-64'te tipik olarak 50–150 ns. Oran yine iki büyüklük mertebesi.)

Bunun iki sonucu var:

1. **Küçük çağrıları birleştir.** Her baytı ayrı bir `write` ile yazmak, aynı baytları bir tamponda toplayıp tek `write` ile yazmaktan yüzlerce kat yavaş. stdio'nun varlık nedeni bu; Ders 10.3'te ölçüp kendimiz yazacağız.
2. **Bazı çağrılar hiç çekirdeğe girmiyor.** `clock_gettime` sadece 17 ns sürdü. Çünkü Linux, saati okumak gibi sık ve zararsız birkaç işlemi **vDSO** (virtual dynamic shared object) adlı, çekirdeğin her sürecin adres alanına eşlediği küçük bir kütüphaneyle kullanıcı modunda yapıyor. Çekirdek zaman bilgisini salt okunur bir sayfaya yazıyor, vDSO'daki kod onu okuyup donanım sayacıyla düzeltiyor.

Kanıtı `strace`'te:

```c
#include <stdio.h>
#include <time.h>
#include <unistd.h>
int main(void) {
    struct timespec t;
    for (int i = 0; i < 3; i++) clock_gettime(CLOCK_MONOTONIC, &t);
    getpid(); getpid(); getpid();
    printf("bitti\n");
    return 0;
}
```

```
$ strace -e trace=getpid,clock_gettime ./vdso
getpid()                                = 10
getpid()                                = 10
getpid()                                = 10
bitti
+++ exited with 0 +++
$ grep vdso /proc/self/maps
ffffb87c8000-ffffb87c9000 r-xp 00000000 00:00 0                          [vdso]
```

Üç `getpid` görünüyor; üç `clock_gettime` görünmüyor, çünkü çekirdeğe hiç girmediler. `/proc/self/maps`'te (Ders 4.21) `[vdso]` adlı tek sayfalık, çalıştırılabilir bölge de orada.

---

## 5. /proc: çekirdeğin bir süreç hakkında bildikleri

Çekirdek her süreç için bir **tablo kaydı** tutuyor (Linux'ta `struct task_struct`): numarası (PID), ebeveyni, durumu, adres alanı, açık dosyaları, sinyal ayarları, kullanıcı kimliği, zamanlama bilgisi. Linux bunları **dosya gibi** okunabilir yapıyor: `/proc/PID/` dizini (kendi sürecin için `/proc/self/`). Diskte yok, okununca çekirdek içeriği o an üretiyor.

```
$ ls /proc/self/
attr autogroup auxv cgroup clear_refs cmdline comm coredump_filter cpuset cwd environ exe fd fdinfo
gid_map io limits map_files maps mem mountinfo mounts ... stat statm status syscall task ...
$ head -8 /proc/self/status
Name:	cat
Umask:	0022
State:	R (running)
Tgid:	21
Ngid:	0
Pid:	21
PPid:	1
TracerPid:	0
```

(`/proc/self` okuyan programın kendisini gösterir, burada `cat` ya da `head`.) Bu fazda sık kullanacaklarımız:

| Dosya | İçerik | Ders |
| --- | --- | --- |
| `maps` | Adres alanındaki bölgeler ve izinleri | 4.21, 10.7 |
| `fd/` | Açık dosya tanımlayıcıları (her biri bir sembolik bağlantı) | 10.2 |
| `status` | Ad, durum, PID, PPID, bellek kullanımı, iş parçacığı sayısı | 10.4, 10.9 |
| `task/` | Her iş parçacığı için bir alt dizin | 10.9 |
| `exe`, `cwd`, `cmdline`, `environ` | Çalıştırılan dosya, çalışma dizini, argümanlar, ortam | 10.4 |

"Her şey bir dosya" Unix'in tasarım fikri: dosyalar, aygıtlar (`/dev/null`, terminal), borular, soketler ve hatta süreç bilgisi aynı `open`/`read`/`write`/`close` arayüzüyle kullanılıyor. Bir sonraki ders bu arayüzü anlatıyor.

---

## Alıştırmalar

**1** – `strace -e trace=openat,read,write cat /etc/hostname` çalıştır. `cat`, dosyayı kaç `read` ile okuyor? Son `read` neden `0` döndürüyor?

**2** – `merhaba.c`'yi `cc -O2 -static merhaba.c -o merhaba_s` ile derle ve `strace -c` ile çağrı sayısını karşılaştır. Hangi çağrılar kayboldu ve neden? `ls -l merhaba merhaba_s` ile boyutları da karşılaştır.

**3** – Ham `write` örneğindeki `ham_write`'ı kullanarak `exit` sistem çağrısını da yapan (x86-64'te 60, arm64'te 93) bir `ham_exit(int kod)` yaz. `main`'in sonunda `return 0` yerine `ham_exit(7)` çağırıp `echo $?` ile çıkış kodunu kontrol et. `printf` ile yazdığın ama `fflush` etmediğin bir satır varsa ne olur? Neden?

**4** – Bir program saniyede 10 milyon kez `getppid` benzeri ucuz bir sistem çağrısı yapıyor. Bölüm 4'teki ölçüme göre zamanın ne kadarı sadece mod geçişlerine gidiyor? Aynı program `clock_gettime`'ı saniyede 10 milyon kez çağırsa?

**5** – Bir program dosya açarken hata veriyor ama hangi dosyayı açamadığını söylemiyor. `strace` ile bunu nasıl bulursun? Hangi `-e` seçeneğini, çıktıda hangi hata kodunu ararsın?

<details>
<summary>Cevaplar</summary>

**1** – Küçük bir dosya için tipik olarak iki `read`: ilki dosyanın tamamını döndürüyor (`cat` 128 KB'lık bir tamponla okuyor), ikincisi `0` döndürüyor. `read`'in 0 döndürmesi **dosya sonu** (EOF) demek: "artık okunacak bayt yok" (Ders 10.2). `cat` döngüsünü bu sayede bitiriyor. Arada bir `write(1, ...)` çıktıyı yazıyor; `openat` ise libc ve locale dosyalarıyla birlikte `/etc/hostname`'i de gösteriyor.

**2** – Statik programda `ld.so.cache`'in ve `libc.so.6`'nın açılması, okunması, `mmap` ile eşlenmesi ve `mprotect`'lerin çoğu kayboluyor: libc zaten programın içinde, dinamik bağlayıcı hiç çalışmıyor (Ders 7.17). Toplam çağrı sayısı 33'ten 16'ya iniyor; `execve`, `brk`, `fstat`, `write`, `exit_group` ve iş parçacığı kurulumu gibi programın kendisine ait olanlar kalıyor. Bedeli boyut: dinamik program 70 536 bayt, statik program 640 144 bayt, çünkü kullanılan libc parçaları içine kopyalanıyor.

**3** – Çıkış kodu 7 görünür. Ama `printf` ile yazılıp `fflush` edilmemiş satır **kaybolur** (stdout bir dosyaya ya da boruya yönlendirilmişse kesin; terminalde satır tamponlu olduğu için `\n` ile bitiyorsa zaten yazılmıştır). Çünkü stdio'nun tamponunu boşaltan `exit` fonksiyonu (libc), `atexit` işleyicileri ve stdio temizliği yapıyor; ham `exit` sistem çağrısı ise süreci doğrudan bitiriyor ve tampondaki baytlar süreçle birlikte yok oluyor. Ders 7.18'deki `exit` / `_exit` farkının aynısı.

**4** – $10^7 \times 121$ ns $\approx 1.21$ s: bir saniyeye sığmıyor bile, program bu hızda çağrı yapamaz; yani tek çekirdekte bütün zaman geçişlere gider. `clock_gettime` (vDSO) ile $10^7 \times 17$ ns = 0.17 s, zamanın %17'si. Ders: çok sık yapılan bir işi sistem çağrısına bağlamak yerine sonucunu önbelleğe almak, işi gruplamak ya da vDSO gibi kullanıcı alanında kalan bir yol bulmak.

**5** – `strace -f -e trace=%file ./program` (ya da `-e trace=openat,open,stat`) ile dosya ile ilgili bütün çağrıları listele ve `= -1 ENOENT` (dosya yok) ya da `= -1 EACCES` (izin yok) ile biten satırlara bak: argümandaki yol, programın açamadığı dosya. `-f`, işi bir alt sürece yaptıran programlar için gerekli. Çıktı uzunsa `strace -o iz.txt ...` ile dosyaya yazıp `grep ENOENT iz.txt`.

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 2 (giriş) ve 6 (sınırlı doğrudan yürütme: sistem çağrısı ve trap). Çevrimiçi ücretsiz: ostep.org.
- Michael Kerrisk, *The Linux Programming Interface*, No Starch, 2010, Bölüm 2–3: temel kavramlar, sistem çağrıları, libc sarmalayıcıları ve hata işleme.
- `man 2 syscall`: mimariye göre sistem çağrısı kuralları tablosu (komut, numara ve argüman register'ları).
- `man 7 vdso` ve `man 1 strace`.
- Linux çekirdeği, `include/uapi/asm-generic/unistd.h` (arm64 numaraları) ve `arch/x86/entry/syscalls/syscall_64.tbl` (x86-64 numaraları).

**Sıradaki ders:** Dosya G/Ç. `open`, `read`, `write`, `close` ve dosya tanımlayıcısı.
