---
title: "10.6 Sinyaller"
description: "Sinyal: çekirdeğin bir sürece gönderdiği asenkron bildirim; varsayılan eylemler ve 128+n çıkış kodları; sigaction ile işleyici, volatile sig_atomic_t bayrağı; EINTR ve SA_RESTART; SIGSEGV'yi yakalamak, si_addr, sigsetjmp/siglongjmp ve yığın taşması için sigaltstack; async-signal-safe kavramı ve işleyicide malloc ile üç denemede üç kilitlenme; maskeleme, standart sinyallerin birleşmesi (5 gönderildi, 1 çalıştı) ve gerçek zamanlı sinyallerin kuyruklanması; SIGCHLD ile çocuk toplama döngüsü; işleyicinin aynı yığında çalışması ve rt_sigreturn."
---

Ders 7.28'de bir `NULL` okumanın donanım istisnasına, çekirdeğin de onu `SIGSEGV`'ye çevirdiğini gördük. Ders 10.3'te `abort` çıkış kodu 134 üretti, Ders 10.5'te `yes` bir `SIGPIPE` ile öldü, kabuk `Ctrl+C` ile kendisi de gitti. Sinyal, çekirdeğin bir sürece "bir şey oldu" demesinin yolu: **asenkron bir bildirim**. Programın herhangi iki komutu arasında gelebilir ve bu, onu C'deki en tehlikeli özelliklerden biri yapıyor.

---

## 1. Sinyal nedir

Sinyal, bir numaradan ibaret (ek bilgi taşıyabilir ama taşımak zorunda değil). Kaynakları:

- **Donanım istisnası**: geçersiz bellek (`SIGSEGV`, `SIGBUS`), sıfıra bölme (`SIGFPE`), geçersiz komut (`SIGILL`).
- **Terminal**: `Ctrl+C` → `SIGINT`, `Ctrl+\` → `SIGQUIT`, `Ctrl+Z` → `SIGTSTP`.
- **Başka bir süreç**: `kill(pid, sinyal)` (adına rağmen öldürmek zorunda değil).
- **Çekirdeğin olayları**: çocuk bitti (`SIGCHLD`), okuyansız boruya yazma (`SIGPIPE`), zamanlayıcı (`SIGALRM`, `SIGPROF`).

Her sinyalin bir **varsayılan eylemi** var:

| Sinyal | No (Linux) | Varsayılan | Tipik neden |
| --- | --- | --- | --- |
| `SIGINT` | 2 | Bitir | `Ctrl+C` |
| `SIGQUIT` | 3 | Bitir + core | `Ctrl+\` |
| `SIGILL` | 4 | Bitir + core | Geçersiz komut |
| `SIGABRT` | 6 | Bitir + core | `abort()` |
| `SIGFPE` | 8 | Bitir + core | Sıfıra tamsayı bölme (x86) |
| `SIGKILL` | 9 | Bitir (**yakalanamaz**) | `kill -9` |
| `SIGSEGV` | 11 | Bitir + core | Geçersiz bellek erişimi |
| `SIGPIPE` | 13 | Bitir | Okuyansız boruya yazma |
| `SIGALRM` | 14 | Bitir | `alarm` |
| `SIGTERM` | 15 | Bitir | `kill` (kibar sonlandırma) |
| `SIGCHLD` | 17 | Yok say | Çocuk durdu ya da bitti |
| `SIGSTOP` | 19 | Durdur (**yakalanamaz**) | `kill -STOP` |

Numaralar mimariye göre değişebilir (bu tablo x86 ve arm64 Linux için). Kabukta sinyalle ölen sürecin `$?` değeri **128 + n**:

```
$ sh -c 'kill -TERM $$'; echo $?
143
$ sh -c 'kill -KILL $$'; echo $?
137
```

`137` (128 + 9) log'larda sıkça görülür: genellikle çekirdeğin bellek yetmeyince süreci öldürmesi (OOM killer) demek. Bir program `SIGKILL` ve `SIGSTOP` dışındaki her sinyal için üç şey seçebilir: varsayılan eylem, **yok say**, **kendi işleyicisini** çalıştır.

---

## 2. İşleyici yazmak

Eski `signal()` çağrısının davranışı sistemden sisteme değişiyor; doğrusu `sigaction`:

```c
/* Sinyal isleyici: bayrak koy, is ana akista yapilsin */
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static volatile sig_atomic_t kesildi = 0;
static void isleyici(int s) { (void)s; kesildi = 1; }

int main(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_handler = isleyici;
    sigemptyset(&sa.sa_mask);
    sigaction(SIGINT, &sa, NULL);

    pid_t ana = getpid();
    if (fork() == 0) { usleep(200000); kill(ana, SIGINT); _exit(0); }

    long tur = 0;
    while (!kesildi) tur++;
    wait(NULL);
    printf("SIGINT geldi, duzgun cikiyorum (%ld tur dondu)\n", tur);
    return 0;
}
```

```
$ ./sayac
SIGINT geldi, duzgun cikiyorum (647549541 tur dondu)
```

Bu kalıp sinyal işlemenin altın kuralı: **işleyici sadece bir bayrak koysun, asıl iş ana akışta yapılsın.** Bayrağın tipi iki koşulu karşılamalı:

- `volatile`: yoksa derleyici `while (!kesildi)` döngüsünde değişkenin değişmediğini görüp `-O2`'de onu tek okumaya indirir (Ders 7.15) ve döngü sonsuz olur. İşleyici, derleyicinin göremediği bir akış.
- `sig_atomic_t`: okuma ve yazmanın sinyal tarafından yarıda kesilemeyeceğini garanti eden tip.

Sinyal geldiğinde çekirdek ne yapıyor? Sürecin register'larını **kullanıcı yığınına** bir çerçeve olarak kaydediyor, program sayacını işleyiciye ayarlıyor, dönüş adresini `rt_sigreturn` çağıran küçük bir parçaya yönlendiriyor. İşleyici bitince `rt_sigreturn` ile çekirdek kaydedilmiş register'ları geri yüklüyor ve kesilen komuttan devam ediliyor:

```
$ strace -e trace=tgkill,rt_sigreturn,write ./cerceve
tgkill(112, 112, SIGUSR1)               = 0
--- SIGUSR1 {si_signo=SIGUSR1, si_code=SI_TKILL, si_pid=112, si_uid=0} ---
write(1, "isleyici yerel degiskeni, main'i"..., 58) = 58
rt_sigreturn({mask=[]})                 = 0
```

İşleyici **aynı yığında**, kesilen kodun hemen altında çalışıyor; `raise(SIGUSR1)` çağıran küçük bir programda (`cerceve`) `main`'in yerel değişkeniyle işleyicininki arasında arm64 Linux'ta 4992 bayt ölçüldü: kaydedilmiş register'lar (SIMD dahil) ve bağlam bilgisi. Yığın doluyken gelen sinyalin neden sorun olduğunu birazdan göreceğiz.

### EINTR ve SA_RESTART

Program yavaş bir sistem çağrısında beklerken (`read`, `wait`, `accept`) sinyal gelirse çağrı yarıda kalır: işleyici çalışır, sonra çağrı `-1` / `EINTR` ile döner (Ders 10.2'deki döngülerin nedeni). `SA_RESTART` bayrağı çekirdekten çağrıyı kendiliğinden yeniden başlatmasını ister:

```c
/* Bloklu bir read sinyalle kesilirse: EINTR ve SA_RESTART */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static void isleyici(int s) { (void)s; write(2, "  [sinyal]\n", 11); }
static void dene(int bayrak, const char *ad) {
    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_handler = isleyici; sa.sa_flags = bayrak;
    sigaction(SIGALRM, &sa, NULL);
    int b[2]; pipe(b);
    pid_t p = fork();
    if (p == 0) { close(b[0]); usleep(400000); write(b[1], "veri", 4); _exit(0); }
    close(b[1]);
    alarm(0); ualarm(100000, 0);
    char t[16];
    ssize_t r = read(b[0], t, sizeof t);
    printf("%-12s read -> %zd (%s)\n", ad, r, r < 0 ? strerror(errno) : "veri geldi");
    fflush(stdout);
    close(b[0]);
}
int main(void) { dene(0, "bayraksiz"); usleep(500000); dene(SA_RESTART, "SA_RESTART"); return 0; }
```

```
$ ./kesinti
  [sinyal]
bayraksiz    read -> -1 (Interrupted system call)
  [sinyal]
SA_RESTART   read -> 4 (veri geldi)
```

`SA_RESTART` çoğu zaman istediğimiz şey. Ama "bir komutun süresi dolsun" gibi durumlarda tersine, kesilmeyi **isteriz**.

---

## 3. SIGSEGV'yi yakalamak

`SA_SIGINFO` ile işleyici ek bilgi alır: hatalı adres (`si_addr`) ve neden (`si_code`). `sigsetjmp`/`siglongjmp` ile işleyiciden hataya neden olan kodun dışına atlanabilir.

```c
/* SIGSEGV'yi yakalamak: hatali adres, kurtarma, yigin tasmasi icin alternatif yigin */
#define _GNU_SOURCE
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static sigjmp_buf donus;
static volatile void *son_adres;

static void isleyici(int s, siginfo_t *bilgi, void *baglam) {
    (void)s; (void)baglam;
    son_adres = bilgi->si_addr;
    siglongjmp(donus, bilgi->si_code);
}

static int dokun(volatile char *p) {
    int k = sigsetjmp(donus, 1);
    if (k == 0) { char c = *p; (void)c; return 0; }
    return k;
}

static long derin(long n) { volatile char dolgu[1024]; dolgu[0] = (char)n; return derin(n + 1) + dolgu[0]; }

int main(void) {
    static char yedek[64 * 1024];
    stack_t ss = { .ss_sp = yedek, .ss_size = sizeof yedek, .ss_flags = 0 };
    sigaltstack(&ss, NULL);

    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = isleyici;
    sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
    sigaction(SIGSEGV, &sa, NULL);

    int k = dokun((char *)0x10);
    printf("0x10 okuma: si_code=%d (%s), adres=%p\n", k, k == SEGV_MAPERR ? "SEGV_MAPERR" : "SEGV_ACCERR", (void *)son_adres);
    k = dokun((char *)main);
    printf("main'i okuma: si_code=%d (basarili)\n", k);

    if (sigsetjmp(donus, 1) == 0) { *(volatile char *)main = 0; }
    printf("main'e yazma: adres=%p, main=%p\n", (void *)son_adres, (void *)main);

    if (sigsetjmp(donus, 1) == 0) derin(0);
    int yerel;
    printf("yigin tasti ama sag kaldik: hatali adres=%p, &yerel=%p\n", (void *)son_adres, (void *)&yerel);
    return 0;
}
```

```
$ ./segv
0x10 okuma: si_code=1 (SEGV_MAPERR), adres=0x10
main'i okuma: si_code=0 (basarili)
main'e yazma: adres=0xaaaab9db08d8, main=0xaaaab9db08d8
yigin tasti ama sag kaldik: hatali adres=0xffffc80d6ffc, &yerel=0xffffc88d5fdc
```

`SEGV_MAPERR` (1): o adreste hiç sayfa yok. `SEGV_ACCERR` (2): sayfa var, izin yok. `0x10` bir `NULL` işaretçinin alanına erişimin tipik adresi (`p->alan`).

Son satır önemli. Yığın dolunca bir sonraki itme hata veriyor, ama çekirdek işleyici çerçevesini **aynı dolu yığına** koyamaz: program sessizce ölürdü. `sigaltstack` ayrı bir yığın tanımlıyor, `SA_ONSTACK` işleyicinin orada çalışmasını sağlıyor. Hatalı adres ile `&yerel` arasındaki fark 8 MB'lık yığın sınırı.

Bu mekanizma gerçek sistemlerde kullanılıyor: JVM'ler `NULL` kontrolünü kod üretmek yerine `SIGSEGV`'ye bırakır; Boehm GC gibi çöp toplayıcılar `mprotect` ile korudukları sayfalara yazmayı yakalayıp hangi sayfaların değiştiğini izler (Ders 10.7). Ama `SIGSEGV`'den sonra sıradan bir programı devam ettirmek çok riskli: hata anında veri yapıları yarım kalmış olabilir. Çoğu programın doğru tepkisi kayıt düşüp çıkmak.

---

## 4. Async-signal-safe

İşleyici programın **herhangi bir yerinde** çalışabilir. Düşünelim: ana akış `malloc`'un içinde, kilidi almış, serbest listeyi güncelliyor; sinyal geliyor, işleyici `malloc` çağırıyor. Aynı kilidi alamaz; kendisi bırakana kadar bekliyor, ama bırakacak olan kod kendisinin altında askıda. **Kilitlenme** (deadlock).

```c
/* isleyicide malloc: async-signal-safe olmamanin bedeli */
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

static void *volatile cop;                     /* derleyici malloc/free ciftini silmesin */
static volatile long sayac = 0;
static volatile sig_atomic_t tehlikeli = 0;

static void isleyici(int s) {
    (void)s;
    if (tehlikeli) { void *p = malloc(5000); cop = p; free(p); }
    sayac++;
}

static void *uyuyan(void *a) { (void)a; sigset_t m; sigfillset(&m); pthread_sigmask(SIG_BLOCK, &m, NULL); for (;;) pause(); }

int main(int argc, char **argv) {
    tehlikeli = argc > 1;
    pthread_t t0;
    pthread_create(&t0, NULL, uyuyan, NULL);   /* glibc tek is parcacikli programda malloc kilidini atlar */
    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_handler = isleyici; sa.sa_flags = SA_RESTART;
    sigaction(SIGPROF, &sa, NULL);
    struct itimerval t = { { 0, 50 }, { 0, 50 } };
    setitimer(ITIMER_PROF, &t, NULL);
    for (long i = 0; i < 20000000; i++) { void *p = malloc(5000); cop = p; free(p); }
    printf("bitti, %ld sinyal islendi\n", sayac);
    return 0;
}
```

```
$ ./kilit; echo $?
bitti, 392 sinyal islendi
0
$ for i in 1 2 3; do timeout 10 ./kilit tehlikeli; echo $?; done
124
124
124
```

İşleyicide `malloc` olmayan sürüm 392 sinyali sorunsuz işleyip bitti; olan sürüm üç denemede üçünde 10 saniyeyi doldurup `timeout` tarafından öldürüldü (124). Programdaki gereksiz görünen iş parçacığı tesadüf değil: glibc, tek iş parçacıklı programlarda hızlanmak için `malloc` kilidini atlıyor. O durumda kilitlenme görmezdik; ama yarım güncellenmiş listeyi bozma riski aynen duruyor, yani hata daha sessiz olurdu.

Bir fonksiyonun işleyiciden güvenle çağrılabilmesi için **async-signal-safe** olması gerekiyor. POSIX'in listesi kısa: `write`, `read`, `open`, `close`, `_exit`, `kill`, `waitpid`, `sigaction`, `pipe`, `dup2`, `fork`, `execve`, `memcpy`, `strlen` ve birkaç onlarcası (`man 7 signal-safety`). **Yok olanlar**: `malloc`, `free`, `printf`, `fopen`, `exit`, pthread kilitleri. Ayrıca:

- `errno`'yu kaydet ve geri yükle: işleyici `write` çağırıp `errno`'yu bozarsa, kesilen kod yanlış hata görür (aşağıdaki `cocuk_topla` örneği).
- Global durumu sadece `volatile sig_atomic_t` veya kilitsiz atomik (Ders 10.12) ile paylaş.

### Karmaşık işleri ana akışa taşımak

İşleyicide bir şey yapmak gerçekten gerekliyse standart çözüm **self-pipe trick**: işleyici bir boruya tek bayt yazıyor (`write` güvenli), ana döngü `poll` ile hem işini hem borunun okuma ucunu bekliyor. Linux'ta `signalfd` sinyalleri doğrudan bir dosya tanımlayıcısından okunur hale getiriyor. Derleyici yazarı olarak bilmen gereken: temizlik kodunu (`atexit`) işleyiciden çağırma, bayrak koy.

---

## 5. Maskeleme ve birleşme

Bir sinyal **bloklanabilir**: `sigprocmask` ile maske değişir, gelen sinyal bekletilir, maske kaldırılınca teslim edilir. Kritik bölgeyi korumanın yolu bu. Ama bekleyen sinyaller için çekirdek sadece bir **bit** tutuyor: aynı sinyal beş kez geldiyse bir kez işlenir.

```c
/* Standart sinyaller kuyruklanmaz, gercek zamanli sinyaller kuyruklanir */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static volatile sig_atomic_t std_say = 0, rt_say = 0;
static void isleyici(int s) { if (s == SIGUSR1) std_say++; else rt_say++; }
int main(void) {
    struct sigaction sa; memset(&sa, 0, sizeof sa); sa.sa_handler = isleyici;
    sigaction(SIGUSR1, &sa, NULL); sigaction(SIGRTMIN, &sa, NULL);
    sigset_t m, eski; sigemptyset(&m); sigaddset(&m, SIGUSR1); sigaddset(&m, SIGRTMIN);
    sigprocmask(SIG_BLOCK, &m, &eski);
    for (int i = 0; i < 5; i++) { kill(getpid(), SIGUSR1); kill(getpid(), SIGRTMIN); }
    sigprocmask(SIG_SETMASK, &eski, NULL);
    printf("5 SIGUSR1 gonderildi, %d kez calisti\n", std_say);
    printf("5 SIGRTMIN gonderildi, %d kez calisti\n", rt_say);
    return 0;
}
```

```
$ ./birlesme
5 SIGUSR1 gonderildi, 1 kez calisti
5 SIGRTMIN gonderildi, 5 kez calisti
```

Bu yüzden sinyal bir **sayaç** gibi kullanılamaz; "en az bir kez oldu" demek. Çok çocuklu bir programda `SIGCHLD` işleyicisi tek bir `waitpid` yaparsa zombi kalır. Doğrusu, bekleyen her çocuğu toplayan bir döngü:

```c
/* SIGCHLD ile cocuklari toplamak: birlesme yuzunden waitpid dongusu sart */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
static volatile sig_atomic_t toplanan = 0, cagri = 0;
static void isleyici(int s) {
    (void)s;
    int kayit = errno;                        /* isleyici errno'yu bozmamali */
    cagri++;
    while (waitpid(-1, NULL, WNOHANG) > 0) toplanan++;
    errno = kayit;
}
int main(void) {
    struct sigaction sa; memset(&sa, 0, sizeof sa);
    sa.sa_handler = isleyici; sa.sa_flags = SA_RESTART;
    sigaction(SIGCHLD, &sa, NULL);
    for (int i = 0; i < 20; i++) if (fork() == 0) _exit(0);
    while (toplanan < 20) pause();
    printf("20 cocuk, isleyici %d kez calisti, %d toplandi\n", cagri, toplanan);
    return 0;
}
```

```
$ ./cocuk_topla
20 cocuk, isleyici 18 kez calisti, 20 toplandi
$ ./cocuk_topla
20 cocuk, isleyici 17 kez calisti, 20 toplandi
```

20 çocuk, 17–18 sinyal: birleşmeyi canlı gördük. Döngü sayesinde hepsi toplandı. (Bu programda ince bir **yarış** var: son sinyal, `toplanan < 20` kontrolü ile `pause` arasına düşerse `pause` sonsuza kadar uyur. Doğrusu `sigsuspend` ile; Alıştırma 3.)

---

## Alıştırmalar

**1** – `while (!kesildi) tur++;` örneğinde `volatile`'ı kaldırıp `-O2` ile derle. Çalıştır, assembly'sine bak (`-S`). Ne oluyor?

**2** – `SIGINT`'i yakalayıp "Çıkmak için bir kez daha basın" yazan ve ikinci sinyalde çıkan bir program yaz. Yazıyı işleyicide hangi fonksiyonla yazmalısın?

**3** – `cocuk_topla`'daki `pause` yarışını `sigprocmask` ve `sigsuspend` ile düzelt. `sigsuspend`'in `pause`'dan farkı nedir?

**4** – Yerleşik `timeout` komutunun basit halini yaz: `./zamanasimi 2 komut arg...`. Çocuğu başlat, 2 saniye geçerse `SIGTERM` gönder, çocuğun çıkış kodunu `timeout` gibi yansıt. Çocuk `SIGTERM`'i yok sayıyorsa ne yaparsın?

**5** – Ders 10.5'teki kabuk `Ctrl+C` ile ölüyordu. `sigaction` ile kabuğun kendisinde `SIGINT`'i yok say; ama `exec` edilen komut yine `Ctrl+C` ile ölebilsin. Yok sayılan sinyaller ve kurulmuş işleyiciler `exec`'ten sonra ne olur?

<details>
<summary>Cevaplar</summary>

**1** – `-O2` ile derleyici `kesildi`'nin döngüde değişmediğini kanıtlıyor (sinyal işleyicisini görmez), tek bir okuma yapıp ya hiç dönmüyor ya da sonsuza kadar dönüyor. Assembly'de koşullu dal sabite bağlı kendine atlayan bir döngüye iner. `SIGINT` gelir, bayrak güncellenir, ama döngü bir daha okumaz; program `kill -9` ile ölür. `tur` kullanılmıyorsa döngü gövdesi de kaybolur.

**2** – Sayaç kullan: `static volatile sig_atomic_t n; n++`. Yazı için `write(2, mesaj, uzunluk)`; `printf` güvenli değil. İkinci sinyalde `_exit(130)` (130 = 128 + 2). Ana döngüde bayrağa bakıp tertemiz çıkmak daha iyi.

**3** – `sigprocmask` ile `SIGCHLD`'yi blokla; `fork`'ları yap; döngü: `while (toplanan < 20) sigsuspend(&bos_maske);`. `sigsuspend` maskeyi **atomik olarak** değiştirip bekliyor: sinyal bloklu kaldığı sürece kontrol ile bekleme arasına düşemez; `sigsuspend` içinde teslim edilir. `pause`'da maske değişimi ile bekleme iki ayrı adım olurdu.

**4** – `SIGCHLD`'yi yakala ya da `alarm`/`sigtimedwait` kullan. En temiz yol: `SIGCHLD` ile `SIGALRM`'u bloklayıp `sigwaitinfo` ile beklemek; zamanlayıcı dolunca `kill(cocuk, SIGTERM)`, kısa bir süre (örneğin 1 s) daha bekleyip hâlâ yaşıyorsa `SIGKILL`. Çocuk normal bittiyse `WEXITSTATUS`'u, sinyalle öldüyse `128 + sinyal`'i, zaman aşımında 124 döndür. `SIGKILL` yakalanamaz; son çare budur.

**5** – Kabukta `sa.sa_handler = SIG_IGN; sigaction(SIGINT, &sa, NULL);`. `exec` sonrası **kurulmuş işleyiciler** varsayılana sıfırlanır (işleyicinin kodu artık yok); ama **yok sayılanlar yok sayılı kalır**. Bu yüzden çocukta `fork`'tan sonra, `exec`'ten önce `signal(SIGINT, SIG_DFL)` çağırmak gerek. Aksi takdirde çalıştırılan komutlar da `Ctrl+C`'ye bağışık olur. `nohup` bu mirası bilerek kullanıyor: `SIGHUP`'u yok sayıp `exec` ediyor.

</details>

---

## Kaynaklar

- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 20–22: sinyaller, işleyiciler, güvenli fonksiyonlar, sinyallerin kuyruklanması.
- W. Richard Stevens ve Stephen Rago, *Advanced Programming in the UNIX Environment* (3. baskı), Bölüm 10.
- `man 7 signal`, `man 7 signal-safety`, `man 2 sigaction`, `man 2 sigaltstack`.
- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 6: trap ve kesme akışı.
- Michal Zalewski, "Delivering Signals for Fun and Profit", 2001: işleyicilerdeki yarış durumlarının güvenlik açısından incelenmesi.

**Sıradaki ders:** mmap. Dosyayı belleğe eşleme, anonim eşleme, `malloc`'umuzu `mmap` ile beslemek.
