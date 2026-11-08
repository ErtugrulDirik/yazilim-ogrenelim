---
title: "10.5 Mini kabuk (shell)"
description: "150 satırda çalışan bir kabuk: satırı belirteçlere bölmek, Komut yapısına ayrıştırmak; fork/exec döngüsü; cd'nin neden dışarıda yazılamayacağı; dup2 ile < > >> yönlendirmeleri; pipe ile iki komutu bağlamak ve strace ile kurulumu izlemek; kapatılmayan boru ucunun wc'yi sonsuza kadar bekletmesi; boru kapasitesi 65 536 bayt, SIGPIPE ve EPIPE; kabuğun neden yönlendirmeleri fork ile exec arasında yaptığı."
---

Ders 10.4'te `fork`, `exec` ve `wait`'i, Ders 10.2'de `dup2`'yi öğrendik. Kabuk bunların üzerine yazılmış, şaşırtıcı derecede küçük bir program. Bu derste 150 satırlık bir kabuk yazıyoruz: komut çalıştırıyor, `cd` ve `exit` yapıyor, `<`, `>`, `>>` yönlendirmelerini ve tek bir `|` borusunu destekliyor. Çok aşamalı boru hatlarını, tırnakları, değişkenleri, `&&` ve arka plan işlerini Ders 10.20'deki projeye bırakıyoruz.

Bir derleyici yazarı için kabuk iki bakımdan önemli. Birincisi en küçük anlamlı **dil işleyicisi**: girdi metni, belirteçlere ayırma, ayrıştırma, yorumlama (Faz 15'in minyatürü). İkincisi `make` ve derleyici sürücüleri her işlerini bu şekilde alt süreçlerle yapıyor.

---

## 1. Ana döngü

Bir kabuğun iskeleti:

```
sonsuza kadar:
    istem yaz
    bir satır oku (EOF ise çık)
    satırı ayrıştır
    yerleşik komutsa kendin yap
    değilse fork; çocukta yönlendirmeleri kur ve exec; ebeveynde wait
```

### Belirteçlere ayırma

Basitlik için belirteçleri **boşluk** ayırıyor: `ls | wc` çalışıyor, `ls|wc` çalışmıyor (Alıştırma 1). Parçalama, satırın içindeki boşlukların yerine `\0` yazarak yerinde yapılıyor; `strtok`'un yöntemi (Ders 4.20).

```c
/* kabuk: fork/exec, < > >> yonlendirme, tek | borusu, cd ve exit */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define EN_COK 64

typedef struct {
    char *argv[EN_COK];
    int argc;
    char *girdi, *cikti;      /* < dosya, > dosya */
    int ekle;                 /* >> ise 1 */
} Komut;

/* satiri bosluklardan parcala; ozel karakterler ayri belirtec olur */
static int parcala(char *s, char **b) {
    int n = 0;
    while (*s) {
        while (*s == ' ' || *s == '\t' || *s == '\n') *s++ = 0;
        if (!*s) break;
        if (n == EN_COK - 1) return -1;
        b[n++] = s;
        while (*s && !strchr(" \t\n", *s)) s++;
    }
    b[n] = NULL;
    return n;
}

/* belirtecleri [bas, son) araligindan bir Komut'a cevir */
static int ayristir(char **b, int bas, int son, Komut *k) {
    memset(k, 0, sizeof *k);
    for (int i = bas; i < son; i++) {
        if (!strcmp(b[i], "<") || !strcmp(b[i], ">") || !strcmp(b[i], ">>")) {
            if (i + 1 >= son) { fprintf(stderr, "kabuk: '%s' sonrasi dosya adi yok\n", b[i]); return -1; }
            if (b[i][0] == '<') k->girdi = b[i + 1];
            else { k->cikti = b[i + 1]; k->ekle = b[i][1] == '>'; }
            i++;
        } else k->argv[k->argc++] = b[i];
    }
    k->argv[k->argc] = NULL;
    if (k->argc == 0) { fprintf(stderr, "kabuk: bos komut\n"); return -1; }
    return 0;
}
```

`ayristir`, `wc -l < girdi > cikti` gibi bir satırı, yönlendirmeleri ayıklayarak `Komut`'a çeviriyor: `argv = {"wc", "-l"}`, `girdi = "girdi"`, `cikti = "cikti"`. Yönlendirme satırın herhangi bir yerinde olabilir; `> c wc -l` de aynı komut. Program bu dosyaları **hiç görmüyor**: argüman listesinde yoklar.

---

## 2. Neden cd yerleşik?

`cd`'yi ayrı bir program olarak yazsak ne olurdu? `fork` olurdu, çocuk `chdir` yapardı, çocuk biterdi; **ebeveynin** çalışma dizini hiç değişmezdi. Çalışma dizini sürecin kendi özelliği ve başka bir süreç değiştiremiyor. Bu yüzden `cd`, `exit`, `export`, `umask` gibi kabuğun kendi durumunu değiştiren komutlar **yerleşik** (builtin) olmak zorunda.

```c
if (!strcmp(b[0], "exit")) return n > 1 ? atoi(b[1]) : son;
if (!strcmp(b[0], "cd")) {
    const char *hedef = n > 1 ? b[1] : getenv("HOME");
    if (chdir(hedef) < 0) { perror(hedef); son = 1; } else son = 0;
    continue;
}
```

---

## 3. Yönlendirme: fork ile exec arası

İşte iki adıma bölünmenin karşılığı. `fork`'tan sonra çocuk hâlâ **bizim kodumuzu** çalıştırıyor; `exec`'ten önce kendi dosya tanımlayıcılarını istediği gibi düzenleyebilir. Hedef program hiçbir şeyden habersiz: 0'dan okuyor, 1'e yazıyor.

```c
/* cocugun icinde cagrilir: yonlendirmeleri kur ve exec et; asla donmez */
static void cocuk(const Komut *k) {
    if (k->girdi) {
        int fd = open(k->girdi, O_RDONLY);
        if (fd < 0) { perror(k->girdi); _exit(1); }
        dup2(fd, 0); close(fd);
    }
    if (k->cikti) {
        int fd = open(k->cikti, O_WRONLY | O_CREAT | (k->ekle ? O_APPEND : O_TRUNC), 0644);
        if (fd < 0) { perror(k->cikti); _exit(1); }
        dup2(fd, 1); close(fd);
    }
    execvp(k->argv[0], k->argv);
    fprintf(stderr, "%s: %s\n", k->argv[0], strerror(errno));
    _exit(127);
}

static int bekle(pid_t p) {
    int d;
    while (waitpid(p, &d, 0) < 0) if (errno != EINTR) return 1;
    return WIFEXITED(d) ? WEXITSTATUS(d) : 128 + WTERMSIG(d);
}

static int tek(const Komut *k) {
    pid_t p = fork();
    if (p == 0) cocuk(k);
    return bekle(p);
}
```

`dup2(fd, 1); close(fd);` kalıbı: artık 1 numara dosyayı gösteriyor; `fd` numarası gereksiz, kapatıyoruz. Yönlendirme **çocukta** yapılıyor, kabuğun kendi stdout'una dokunulmuyor. `128 + sinyal` kabukların `$?` için kullandığı gelenek (Ders 10.3'teki 134).

Tasarımın gücü burada: `CreateProcess`-benzeri tek bir "programı başlat" çağrısı olsaydı, yönlendirme için özel bir parametreler listesi gerekirdi. `fork`/`exec` ayrımında ise "çocuğu hazırla" adımı **sıradan C kodu** ve sistem çağrılarının herhangi bir kombinasyonu olabiliyor.

---

## 4. Boru

`pipe(b)`, çekirdekte bir tampon oluşturur ve iki dosya tanımlayıcısı döndürür: `b[0]` okuma ucu, `b[1]` yazma ucu. Bir uca yazılan baytlar diğerinden okunur. `fork`, fd'leri miras bıraktırdığı için iki süreç bu tamponla konuşabilir. Bir boru hattı `a | b` kurmak:

```
         a'nın stdout (1)     ┌────────────┐      b'nin stdin (0)
  a ───────────────────────▶ │ çekirdek   │ ───────────────────────▶ b
          b[1]                │ tamponu    │          b[0]
                              └────────────┘
```

```c
static int boru_hatti(const Komut *sol, const Komut *sag) {
    int b[2];
    if (pipe(b) < 0) { perror("pipe"); return 1; }
    pid_t p1 = fork();
    if (p1 == 0) { dup2(b[1], 1); close(b[0]); close(b[1]); cocuk(sol); }
    pid_t p2 = fork();
    if (p2 == 0) { dup2(b[0], 0); close(b[0]); close(b[1]); cocuk(sag); }
    close(b[0]); close(b[1]);                 /* ebeveyn kapatmazsa sag taraf EOF goremez */
    bekle(p1);
    return bekle(p2);                         /* boru hattinin sonucu: son komut */
}
```

Ana döngüye `|` taraması ekleyince kabuk tamam:

```c
int main(void) {
    char satir[4096], *b[EN_COK];
    int son = 0, tty = isatty(0);
    for (;;) {
        if (tty) { printf("kabuk$ "); fflush(stdout); }
        if (!fgets(satir, sizeof satir, stdin)) break;
        int n = parcala(satir, b);
        if (n <= 0) continue;
        /* ... exit ve cd yukaridaki gibi ... */
        int bor = -1;
        for (int i = 0; i < n; i++) if (!strcmp(b[i], "|")) { bor = i; break; }
        Komut k1, k2;
        fflush(stdout);
        if (bor < 0) {
            if (ayristir(b, 0, n, &k1) == 0) son = tek(&k1);
        } else if (ayristir(b, 0, bor, &k1) == 0 && ayristir(b, bor + 1, n, &k2) == 0) {
            son = boru_hatti(&k1, &k2);
        }
    }
    return son;
}
```

`isatty` ile istem sadece etkileşimli çalışınca yazılıyor; bu sayede kabuğa dosyadan komut verilebilir. Test:

```
$ cat komutlar.txt
echo merhaba dunya
ls /etc/hostname /yok
echo $HOME
pwd
cd /usr
pwd
cd /tmp/w
echo bir > c.txt
echo iki >> c.txt
cat < c.txt
wc -l < c.txt > sayi.txt
cat sayi.txt
ls /usr/bin | wc -l
cat c.txt | tr a-z A-Z
boyle-komut-yok
cat < yok.txt
sort <
sh -c "exit
exit 5
$ ./kabuk < komutlar.txt; echo "cikis kodu: $?"
merhaba dunya
/etc/hostname
ls: cannot access '/yok': No such file or directory
$HOME
/tmp/w
/usr
bir
iki
2
435
BIR
IKI
boyle-komut-yok: No such file or directory
yok.txt: No such file or directory
kabuk: '<' sonrasi dosya adi yok
sh: 1: Syntax error: Unterminated quoted string
cikis kodu: 5
```

Eksikler de açıkça görünüyor: `$HOME` genişletilmedi, tırnaklar anlaşılmadı (`sh -c "exit` yarım geldi). Bunlar kabuğun **dil** tarafı; Ders 10.20'de ekleyeceğiz.

`strace` ile boru kurulumunu izleyelim (`ls / | wc -l`; okunaklı olsun diye `execve`'lerin başarısız `PATH` denemeleri ayıklandı, araya giren `<unfinished ...>` satırları birleştirildi):

```
$ strace -f -e trace=pipe2,dup3,execve,close,clone ./kabuk < k2.txt
14    pipe2([3, 4], 0)                  = 0
14    clone(...SIGCHLD...)              = 15
14    clone(...SIGCHLD...)              = 16
15    dup3(4, 1, 0)                     = 1
15    close(3)                          = 0
15    close(4)                          = 0
16    dup3(3, 0, 0)                     = 0
16    close(3)                          = 0
16    close(4)                          = 0
14    close(3)                          = 0
14    close(4)                          = 0
15    execve("/usr/bin/ls", ["ls", "/"], ...) = 0
16    execve("/usr/bin/wc", ["wc", "-l"], ...) = 0
```

Kodun birebir izdüşümü. (arm64 Linux'ta ayrı bir `dup2` çağrısı yok; libc onu `dup3`'e çeviriyor. x86-64'te `dup2` görürsün.)

### Kapatılmayan boru ucu

Borudaki en yaygın hata. Okuyan taraf, borunun **bütün** yazma uçları kapanınca dosya sonunu görür. Bir süreçte unutulan tek bir `b[1]`, okuyanı sonsuza kadar bekletir:

```c
/* Boru ucunu kapatmayi unutmak: okuyan taraf EOF goremez */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
#include <signal.h>
int main(void) {
    int b[2]; pipe(b);
    pid_t p = fork();
    if (p == 0) {
        dup2(b[0], 0); close(b[0]);
        /* close(b[1]) UNUTULDU */
        execlp("wc", "wc", "-c", (char *)NULL);
        _exit(127);
    }
    close(b[0]);
    write(b[1], "merhaba\n", 8);
    close(b[1]);
    alarm(2);
    int d; waitpid(p, &d, 0);
    return 0;
}
```

```
$ time ./cikmaz
Alarm clock

real    0m2.007s
```

Ebeveyn yazma ucunu kapattı ve bekliyor; `wc` ise `exec`'ten sonra hâlâ `b[1]`'i açık tutuyor, yani **kendisinden** veri gelebilir diye sonsuza kadar `read`'de duruyor. Program, koyduğumuz 2 saniyelik `alarm` sayesinde öldü. Bu nedenle boru kodunun kuralı: her süreç, **kullanmadığı her ucu** kapatır. Boruların çoğu programda `O_CLOEXEC` ile açılmasının (`pipe2`) nedeni de bu.

### Geri basınç ve SIGPIPE

Boru tamponu sınırlı. Dolunca yazan bloklanır; **boşsa** okuyan bloklanır. Hızlı bir üretici, yavaş bir tüketiciye kendiliğinden uyar. Okuyanı kalmamış boruya yazmak ise özel bir durum:

```c
/* Boru tamponu kapasitesi ve okuyani kalmamis boruya yazmak */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(void) {
    int b[2]; pipe(b);
    printf("F_GETPIPE_SZ: %d\n", fcntl(b[1], F_GETPIPE_SZ));
    fcntl(b[1], F_SETFL, O_NONBLOCK);
    long top = 0; char c = 'x';
    while (write(b[1], &c, 1) == 1) top++;
    printf("tek baytlarla dolana kadar: %ld bayt, sonra: %s\n", top, strerror(errno));
    signal(SIGPIPE, SIG_IGN);
    int r[2]; pipe(r); close(r[0]);
    int w = write(r[1], "x", 1);
    printf("okuyansiz boruya write: %d, %s\n", w, strerror(errno));
    return 0;
}
```

```
$ ./kapasite
F_GETPIPE_SZ: 65536
tek baytlarla dolana kadar: 65536 bayt, sonra: Resource temporarily unavailable
okuyansiz boruya write: -1, Broken pipe
```

Linux'ta varsayılan kapasite 64 KB. Okuyanı olmayan boruya yazmak `SIGPIPE` sinyali üretir (varsayılan: süreci öldür), sinyal yok sayılıyorsa `write` `EPIPE` döndürür. `yes | head -1`'in hemen bitmesinin sebebi: `head` çıkınca `yes`'in sonraki `write`'ı `SIGPIPE` ile onu öldürüyor (Ders 10.6).

---

## Alıştırmalar

**1** – `parcala` fonksiyonunu `ls|wc` ve `cat<x>y` yazılışlarını da destekleyecek şekilde değiştir: `|`, `<` ve `>` karakterlerini boşluk gerekmeyen ayrı belirteçler yap. Yerinde (`\0` yazarak) yapabilir misin, yoksa ayrı bir tampon mu gerekiyor?

**2** – `cat < yok.txt | wc -c` gibi bir komutta `cat` çocukta hatayla çıkıyor. `wc`'nin çıktısı ne olur? Bu boru hattının `$?` değeri nedir? Bash'in `set -o pipefail` seçeneği neyi değiştirir?

**3** – Boru hattında `bekle(p1); return bekle(p2);` sırasıyla bekliyoruz. Sol komut sonsuz üretiyor (`yes`), sağ komut hemen bitiyorsa (`head -1`) bu sıra sorun yaratır mı?

**4** – `Ctrl+C` ile bu kabukta bir komutu kesmeye çalışınca kabuğun kendisi de ölüyor. Neden? Ders 10.6'yı okumadan önce tahmin et, `kill -l` ve `strace` ile dene.

**5** – `2>` yönlendirmesini ekle. Ardından `2>&1`'i ekle: `ls /yok > c.txt 2>&1` ile `ls /yok 2>&1 > c.txt` neden farklı sonuç veriyor? `dup2` çağrılarının sırasını yazarak açıkla.

<details>
<summary>Cevaplar</summary>

**1** – Yerinde yapılamaz: `ls|wc` içindeki `|`'nın üzerine `\0` yazarsak `|` belirteci yok olur ve ayırıcı bir karakterin yeri yok. Ayrı bir tampon gerek (girdi kadar ya da iki katı): her belirteci sonuna `\0` ekleyerek oraya kopyala; ya da belirteç için `{tür, başlangıç, uzunluk}` tutan bir yapı kullan. Faz 15'teki sözcük çözümleyicilerin yöntemi ikincisi.

**2** – `cat` çocukta `open` hatasıyla çıkıyor, çocuğun yazma ucu kapanıyor, `wc -c` hemen dosya sonunu görüyor ve `0` yazıyor. `$?` son komutun, yani `wc`'nin kodu: 0. Kabuk `cat`'in başarısızlığından haberdar olmuyor. `set -o pipefail` ile sonuç, hata veren en sağdaki komutun kodu olur (burada 1). CI betiklerinin hep `set -euo pipefail` ile başlamasının nedeni bu.

**3** – Sorun yaratmaz. `head -1` bitince boru okuma ucu kapanır, `yes` bir sonraki `write`'ta `SIGPIPE` ile ölür; `bekle(p1)` döner. Çünkü iki komut da eşzamanlı çalışıyor, sıralı bekleme sadece ebeveyni ilgilendiriyor. Sıralı bekleme ancak beklenen süreç hiçbir zaman bitmezse sorun olur.

**4** – `Ctrl+C`, terminalin ön plandaki **süreç grubunun tamamına** `SIGINT` gönderiyor. Bu kabuk çocuklarıyla aynı grupta ve sinyal işleyicisi yok; varsayılan davranışla kendisi de ölüyor. Gerçek kabuklar `SIGINT`'i yok sayar ve her iş için ayrı bir süreç grubu oluşturur (`setpgid`, `tcsetpgrp`); Ders 10.6 ve 10.20.

**5** – Soldan sağa işlenir. `> c.txt 2>&1`: `dup2(fd, 1)` sonra `dup2(1, 2)`: ikisi de dosyayı gösterir, stdout ve stderr dosyaya. `2>&1 > c.txt`: önce `dup2(1, 2)`, o an 1 numara **terminal**, yani 2 terminali gösteriyor; sonra `dup2(fd, 1)` sadece 1'i değiştiriyor. Hata mesajı terminalde kalıyor, sadece stdout dosyaya gidiyor.

</details>

---

## Kaynaklar

- Brian Kernighan ve Rob Pike, *The UNIX Programming Environment*, Prentice Hall, 1984: kabuk ve boru hatlarının kullanımı.
- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 5: süreç API'si ve kabuk örneği.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 44: borular ve FIFO'lar.
- Russ Cox, Frans Kaashoek ve Robert Morris, xv6 kaynak kodu, `sh.c`: birkaç yüz satırlık tam bir kabuk (`github.com/mit-pdos/xv6-public`).
- `man 2 pipe`, `man 7 pipe`, `man 2 dup`.

**Sıradaki ders:** Sinyaller. `SIGINT`, `SIGSEGV`, sinyal işleyici, async-signal-safe.
