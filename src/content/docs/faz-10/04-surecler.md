---
title: "10.4 Süreçler"
description: "Süreç nedir; fork'un bir kez çağrılıp iki kez dönmesi; aynı sanal adreste farklı değerler; döngüde fork ve süreç ağacı çizimi; exec ailesi, exec'in neyi koruyup neyi değiştirdiği, O_CLOEXEC; wait, waitpid ve çıkış durumunu çözmek; kendi system() fonksiyonumuz; zombi ve yetim süreçler, /proc/PID/stat ile Z durumunu görmek; copy-on-write ölçümü: 128 MB'lık süreçte fork 0.6 ms, ardından yazma 32 768 sayfa hatası ve 26 ms."
---

Ders 10.1'de `strace -f` çıktısında kabuğun `clone`, `execve` ve `wait4` çağırdığını gördük. Unix'te yeni bir program başlatmanın yolu bu üç adım: **kendini kopyala**, **kopyayı başka bir programa dönüştür**, **bitmesini bekle**. Tek bir "programı başlat" çağrısı yerine ikiye bölünmüş olması ilk bakışta tuhaf; ama Ders 10.5'te göreceğimiz gibi kabukların yönlendirme ve boruları bu iki adımın **arasına** yerleşiyor. `cc` de bu yolla çalışıyor: sürücü program, önişlemciyi, derleyiciyi, assembler'ı ve bağlayıcıyı (Ders 7.17) birer alt süreç olarak başlatıyor.

---

## 1. fork: bir çağrı, iki dönüş

**Süreç** (process), çalışmakta olan bir programın çekirdekteki temsili: bir adres alanı, register'lar, açık dosyalar, bir PID. `fork()`, çağıran sürecin neredeyse birebir kopyası olan **yeni bir süreç** oluşturur. Yeni süreç, tıpkı eskisi gibi `fork`'un dönüş noktasından devam eder. Yani `fork` bir kez çağrılır ve **iki kez döner**: ebeveynde çocuğun PID'si, çocukta `0`.

```c
/* fork: bir cagri, iki donus; bellek kopyalanir */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void) {
    int x = 10;
    setbuf(stdout, NULL);
    printf("fork oncesi: pid=%d\n", getpid());
    pid_t p = fork();
    if (p < 0) { perror("fork"); return 1; }
    if (p == 0) {
        x += 1;
        printf("cocuk  : fork -> %d, pid=%d, ppid=%d, x=%d, &x=%p\n", p, getpid(), getppid(), x, (void *)&x);
        return 0;
    }
    wait(NULL);
    printf("ebeveyn: fork -> %d, pid=%d, x=%d, &x=%p\n", p, getpid(), x, (void *)&x);
    return 0;
}
```

```
$ cc -O2 catal1.c -o catal1 && ./catal1
fork oncesi: pid=11
cocuk  : fork -> 0, pid=12, ppid=11, x=11, &x=0xffffe4772f8c
ebeveyn: fork -> 12, pid=11, x=10, &x=0xffffe4772f8c
```

`&x` iki süreçte de **aynı** adres, ama değerler farklı: 11 ve 10. Çelişki yok: bu adresler **sanal** (Ders 7.27). Her sürecin kendi sayfa tablosu var; aynı sanal adres farklı fiziksel sayfalara çevriliyor. (`setbuf(stdout, NULL)` tamponu kapatıyor; yoksa Ders 10.3'teki "fork tamponu kopyalar" sorununa düşerdik.)

Çocuk neyi miras alıyor? Belleğin kopyası, register'lar, **açık dosya tanımlayıcıları** (Ders 10.2'deki açık dosya kayıtlarını paylaşarak, yani dosya konumu ortak), sinyal ayarları, çalışma dizini, ortam değişkenleri. Farklı olanlar: PID, PPID, bekleyen sinyaller ve zamanlayıcılar, dosya kilitleri.

Sıra garantisi **yok**. `fork`'tan sonra hangisinin önce çalışacağını zamanlayıcı seçer (Ders 10.14). Yukarıda sırayı `wait` belirledi.

### Süreç ağacı

Bir döngüde `fork` çağırmak ilk sınav sorusudur:

```c
/* Dongude fork: surec agaci. Her surec bir satir yazar */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void) {
    setbuf(stdout, NULL);
    for (int i = 0; i < 3; i++) fork();
    printf("pid=%d ppid=%d\n", getpid(), getppid());
    while (wait(NULL) > 0) { }
    return 0;
}
```

```
$ ./agac
pid=16 ppid=1
pid=18 ppid=16
pid=20 ppid=16
pid=21 ppid=18
pid=17 ppid=16
pid=22 ppid=17
pid=19 ppid=17
pid=23 ppid=19
```

Her turda **o an var olan bütün süreçler** çatallanıyor: 1 → 2 → 4 → 8; $2^3$ süreç. PPID sütunundan ağacı kuralım:

```
16 ─┬─ 17 (i=0) ─┬─ 19 (i=1) ─── 23 (i=2)
    │            └─ 22 (i=2)
    ├─ 18 (i=1) ─── 21 (i=2)
    └─ 20 (i=2)
```

Kök üç çocuk doğuruyor (her turda bir); $i = 0$'da doğan çocuk kalan iki turu yaşıyor, iki çocuk doğuruyor; $i = 2$'de doğanın kalan turu yok. Bu bir **binom ağacı** ($B_3$). Satır sırası her çalıştırmada değişebilir, sayı hep 8.

Sistemdeki bütün süreçler tek bir ağaç: kökünde PID 1 (`init`/`systemd`). `pstree -p` çizer:

```
$ (sleep 0.3 & sleep 0.3 & sh -c "sleep 0.3" & pstree -p $$; wait)
bash(1)---bash(59)-+-pstree(63)
                   |-sh(62)---sleep(64)
                   |-sleep(60)
                   `-sleep(61)
```

---

## 2. exec: kopyayı başka bir programa dönüştürmek

`execve(yol, argv, envp)`, çağıran sürecin programını **değiştirir**: kod, veri, stack ve heap atılır; yeni ELF yüklenir (Ders 7.18); yürütme yeni programın başından başlar. **Yeni süreç oluşturmaz**: PID aynı kalır. Başarılı olursa asla dönmez; `exec`'ten sonraki satıra gelindiyse hata var demektir.

Libc'de aileyi oluşturan sarmalayıcılar harflerle adlandırılıyor: `l` (argümanlar liste), `v` (argümanlar dizi), `p` (`PATH`'te ara), `e` (ortamı açıkça ver). `execvp` kabukların kullandığı: `PATH`'teki dizinleri sırayla deniyor (`/usr/local/sbin/ls`, `/usr/local/bin/ls`, ...), `ENOENT` alınca sıradakine geçiyor. Argüman listesinin kuralı: `argv[0]` geleneksel olarak programın adı, dizi `NULL` ile bitiyor.

**Korunanlar** PID, PPID, çalışma dizini ve **açık dosya tanımlayıcıları**. Bunun bir tuzağı var ve bir ilaç: `O_CLOEXEC` ile açılan dosya `exec` sırasında kapanır.

```c
/* exec ne korur: PID, acik dosyalar (O_CLOEXEC olmayanlar); ne degisir: kod, veri, yigin */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv) {
    if (argc == 2 && !strcmp(argv[1], "ikinci")) {
        printf("exec sonrasi : pid=%d\n", getpid());
        for (int fd = 3; fd <= 4; fd++) {
            int r = write(fd, "x", 1);
            printf("  fd %d: %s\n", fd, r == 1 ? "hala acik" : "kapali");
        }
        return 0;
    }
    int a = open("/tmp/a.txt", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    int b = open("/tmp/b.txt", O_WRONLY | O_CREAT | O_TRUNC | O_CLOEXEC, 0644);
    printf("exec oncesi  : pid=%d, a=%d, b=%d\n", getpid(), a, b);
    fflush(stdout);
    execl("/proc/self/exe", argv[0], "ikinci", (char *)NULL);
    perror("execl");
    return 1;
}
```

```
$ ./kalan
exec oncesi  : pid=35, a=3, b=4
exec sonrasi : pid=35
  fd 3: hala acik
  fd 4: kapali
```

Aynı PID, tamamen yeni program; ama 3 numara yaşıyor. `> cikti.txt` yönlendirmesinin bir `exec`'i geçip programa ulaşmasını sağlayan şey bu. `O_CLOEXEC` ise özel dosyaların (bir kütüphanenin iç dosyası, bir veritabanı soketi) çalıştırılan programa sızmasını önler; `exec` yapma ihtimali olan her programda varsayılan olmalı. `exec`'ten önce `fflush` gerekli: tampon, adres alanıyla birlikte atılıyor.

---

## 3. wait: çocuğu beklemek

`waitpid(pid, &durum, secenekler)` belirtilen çocuk bitene kadar bloklar ve onun bitiş durumunu verir. `pid = -1` herhangi bir çocuk; `WNOHANG` seçeneği beklemeden hemen dönmesini sağlar. `wait(&d)`, `waitpid(-1, &d, 0)` kısaltmasıdır. Durum tek bir `int`'e paketli, makrolarla açılıyor:

| Makro | Anlam |
| --- | --- |
| `WIFEXITED(d)` | Normal bitti (`exit` ya da `main`'den dönüş) |
| `WEXITSTATUS(d)` | Çıkış kodu (alt 8 bit) |
| `WIFSIGNALED(d)` | Bir sinyalle öldürüldü |
| `WTERMSIG(d)` | Hangi sinyal (Ders 10.6) |

Hepsini birleştirip kendi `system`'imizi yazalım:

```c
/* kendi system()'imiz: fork + execvp + waitpid; cikis nedenini cozer */
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static int calistir(char *const argv[]) {
    pid_t p = fork();
    if (p < 0) { perror("fork"); return -1; }
    if (p == 0) {
        execvp(argv[0], argv);               /* basarili olursa buraya hic donmez */
        fprintf(stderr, "%s: %s\n", argv[0], strerror(errno));
        _exit(127);
    }
    int d;
    while (waitpid(p, &d, 0) < 0) if (errno != EINTR) return -1;
    if (WIFEXITED(d))   printf("  -> pid %d normal bitti, kod %d\n", p, WEXITSTATUS(d));
    if (WIFSIGNALED(d)) printf("  -> pid %d sinyalle oldu: %d (%s)\n", p, WTERMSIG(d), strsignal(WTERMSIG(d)));
    return d;
}

int main(void) {
    setbuf(stdout, NULL);
    char *a[] = { "echo", "merhaba", "dunya", NULL };       calistir(a);
    char *b[] = { "sh", "-c", "exit 3", NULL };             calistir(b);
    char *c[] = { "boyle-bir-komut-yok", NULL };            calistir(c);
    char *d[] = { "sh", "-c", "kill -SEGV $$", NULL };      calistir(d);
    return 0;
}
```

```
$ ./bencim
merhaba dunya
  -> pid 28 normal bitti, kod 0
  -> pid 29 normal bitti, kod 3
boyle-bir-komut-yok: No such file or directory
  -> pid 30 normal bitti, kod 127
  -> pid 31 sinyalle oldu: 11 (Segmentation fault)
```

İki ayrıntı. `exec` başarısız olunca çocukta **`_exit`** kullanıyoruz, `exit` değil: `exit` stdio tamponlarını boşaltır ve `atexit` işleyicilerini çalıştırır; bunlar ebeveynden kopyalanmış olduğu için aynı çıktı iki kez yazılabilir. 127 kodu, kabukların "komut bulunamadı" için kullandığı gelenek. Gerçek `system(3)` farklı olarak komutu `sh -c` ile çalıştırıyor ve bekleme sırasında `SIGINT` ile `SIGQUIT`'i yok sayıyor (Ders 10.6).

### Zombi ve yetim

Bir çocuk bittiğinde çekirdek onun belleğini geri alıyor ama **çıkış durumunu** ebeveyn `wait` yapana kadar saklamak zorunda. Bu aradaki hal **zombi**: süreç tablosunda kayıt var, başka bir şey yok. Tersi: ebeveyn önce biterse çocuk **yetim** kalır ve PID 1'in (ya da bir "subreaper"ın) çocuğu olur; PID 1 onu sonunda `wait` eder.

```c
/* Zombi ve yetim surecler: /proc/PID/stat'in durum alani */
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
static char durum(pid_t p) {
    char y[64], ad[64]; char d = '?'; int pp;
    snprintf(y, sizeof y, "/proc/%d/stat", p);
    FILE *f = fopen(y, "r");
    if (!f) return '-';
    if (fscanf(f, "%*d %63s %c %d", ad, &d, &pp) != 3) d = '?';
    fclose(f);
    return d;
}
int main(void) {
    setbuf(stdout, NULL);
    pid_t p = fork();
    if (p == 0) _exit(7);
    usleep(100000);
    printf("cocuk bitti, wait yok : durum %c\n", durum(p));
    int d; waitpid(p, &d, 0);
    printf("wait sonrasi          : durum %c, kod %d\n", durum(p), WEXITSTATUS(d));

    p = fork();
    if (p == 0) {
        if (fork() != 0) _exit(0);           /* ara ebeveyn olur */
        pid_t once = getppid();
        usleep(100000);
        printf("torun: ebeveyn %d idi, simdi %d\n", once, getppid());
        _exit(0);
    }
    waitpid(p, NULL, 0);
    usleep(200000);
    return 0;
}
```

```
$ ./zombi
cocuk bitti, wait yok : durum Z
wait sonrasi          : durum -, kod 7
torun: ebeveyn 41 idi, simdi 1
```

`Z` durumu zombi; `wait` sonrası `/proc/PID` tamamen yok oluyor. Bir sunucu çocuklarını hiç beklemezse zombiler birikir ve süreç tablosunu doldurur: uzun ömürlü her programın çocuklarını toplaması gerekiyor (`SIGCHLD` işleyicisi ya da `WNOHANG` döngüsü; Ders 10.6, 10.20). İkinci kısım, eski "çift fork" hilesi: arka plana atılan bir süreci hemen PID 1'e devretmek, böylece bekleme derdi kalmıyor.

---

## 4. Copy-on-write

`fork` bütün belleği kopyalıyorsa, 10 GB'lık bir derleyicinin bir alt süreç başlatması 10 GB kopyalamak demek olurdu. Üstelik çocuk hemen `exec` yapıp o kopyayı atacak. Çekirdek bu yüzden kopyalamıyor: iki sürecin sayfa tabloları **aynı fiziksel sayfaları** gösteriyor ve sayfalar iki tarafta da **salt okunur** işaretleniyor. Biri yazmaya kalkınca sayfa hatası oluşuyor (Ders 7.27), çekirdek **o sayfanın** kopyasını çıkarıp yazmaya izin veriyor: **copy-on-write** (COW).

```c
/* Copy-on-write: fork bellegi kopyalamaz; ilk yazma sayfa basina bir hata ve bir kopya */
#define _DEFAULT_SOURCE
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static long hata(void) { struct rusage r; getrusage(RUSAGE_SELF, &r); return r.ru_minflt; }

int main(void) {
    setbuf(stdout, NULL);
    long sayfa = sysconf(_SC_PAGESIZE);
    size_t boylar[] = { 1 << 20, 16 << 20, 128 << 20 };
    printf("   bellek |    fork |     yazma | yazmadaki sayfa hatasi\n");
    for (int i = 0; i < 3; i++) {
        size_t n = boylar[i];
        char *a = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
        madvise(a, n, MADV_NOHUGEPAGE);              /* karsilastirma temiz olsun: 4 KB sayfalar */
        memset(a, 1, n);
        double t0 = simdi();
        pid_t p = fork();
        if (p == 0) {
            double t1 = simdi();
            long h1 = hata();
            for (size_t k = 0; k < n; k += sayfa) a[k] = 2;
            double t2 = simdi();
            printf("%6zu MB | %5.0f us | %7.0f us | %ld\n", n >> 20, (t1 - t0) * 1e6, (t2 - t1) * 1e6, hata() - h1);
            _exit(0);
        }
        wait(NULL);
        printf("          ebeveynin ilk bayti hala %d\n", a[0]);
        munmap(a, n);
    }
    return 0;
}
```

```
$ ./cow
   bellek |    fork |     yazma | yazmadaki sayfa hatasi
     1 MB |    85 us |     241 us | 257
          ebeveynin ilk bayti hala 1
    16 MB |   118 us |    3512 us | 4097
          ebeveynin ilk bayti hala 1
   128 MB |   570 us |   25909 us | 32769
          ebeveynin ilk bayti hala 1
```

- Sayfa hatası sayısı **sayfa sayısıyla bire bir**: $128 \text{ MB} / 4 \text{ KB} = 32\,768$. (Bazı çalıştırmalarda sayaç 1 fazla çıkıyor: döngü dışında dokunulan başka bir sayfa.) Her yazma bir COW kopyası; sayfa başına ~0.8 µs.
- `fork` süresi bellekle **çok daha yavaş** büyüyor: 128 kat bellek, 7 kat süre. `fork`'un yaptığı sayfaları değil **sayfa tablolarını** kopyalamak. Yine de süreç çok büyürse `fork` hissedilir hale gelir; 128 MB'lık yazmanın tamamı ise `fork`'un 45 katı.
- Ebeveynin değeri korundu.

COW sayesinde `fork` + `exec` ucuz: çocuk hemen `exec` yaparsa neredeyse hiçbir sayfa kopyalanmaz. Yine de büyük süreçler için Linux'ta `vfork` ve `posix_spawn` var; `clang` gibi büyük programlar alt süreçleri bu yolla başlatıyor.

---

## Alıştırmalar

**1** – Bölüm 1'deki döngüyü `for (i = 0; i < n; i++) if (fork() == 0) break;` yapınca kaç süreç oluşur, ağacın şekli nasıl olur? `if (fork() != 0) break;` yapınca?

**2** – `fork() && fork();` satırı kaç süreç oluşturur? `||` ile? (İpucu: `&&` ve `||` kısa devre yapar; hangi sürecin hangi `fork`'u çalıştırdığını yaz.)

**3** – `calistir` fonksiyonunda çocuk `exit(127)` yapsaydı ve ebeveyn `printf("merhaba")` ile tamponda veri bırakmış olsaydı ne olurdu?

**4** – Bölüm 4'teki tabloya bakarak 4 GB'lık bir süreçte, `fork`'tan sonra çocuk 1000 sayfaya yazıp `exec` yaparsa ne kadar sayfa kopyalanır? Çocuk hiç `exec` yapmayıp bütün sayfalara yazarsa bellek kullanımı ne olur? Redis'in `BGSAVE`'i (kalıcılık için `fork`) neden bu durumla ilgilenir?

**5** – Ebeveyn, çocuklarını sırayla başlatıp `n` çocuğun hepsinin bitmesini bekliyor. Çocuklardan biri sonsuza kadar sürüyor, diğerleri bitmiş. Ebeveyn `waitpid(cocuk[i], ...)` ile sırayla bekliyorsa zombi kalır mı? `waitpid(-1, ...)` ile bekleseydi?

<details>
<summary>Cevaplar</summary>

**1** – `if (fork() == 0) break;`: çocuk döngüden çıkıyor, ebeveyn devam ediyor; toplam $n + 1$ süreç, ağaç bir **yıldız** (kökün $n$ çocuğu). `if (fork() != 0) break;`: ebeveyn çıkıyor, çocuk devam ediyor; yine $n + 1$ süreç, ama ağaç bir **zincir** (her süreç bir çocuk doğuruyor).

**2** – `fork() && fork();`: ilk `fork` ebeveynde sıfırdan farklı döner, ikinci `fork` çalışır; ilk çocukta 0 döner, kısa devre: ikinci `fork` çalışmaz. Toplam 3 süreç. `fork() || fork();`: ebeveynde ilk `fork` sıfırdan farklı: kısa devre, ikinci çalışmaz. Çocukta ilk 0: ikincisi çalışır. Toplam yine 3 süreç; farkı ikinci `fork`'u çocuğun yapması.

**3** – Çocuk `exit` ile tamponu boşaltır: `merhaba` çocuktan **bir kez** yazılır, ebeveyn de kendi kopyasını `exit`'te yazar; çıktıda iki kez görünür. `_exit` tamponları dokunmadan bırakır, sorun çıkmaz.

**4** – Yalnızca dokunulan 1000 sayfa (yaklaşık 4 MB) kopyalanır; geri kalan her şey paylaşımlı kalır. Çocuk bütün sayfalara yazarsa toplam bellek 8 GB'a çıkar: COW işi ertelemişti, ama yok etmedi. Redis'te `fork` edilen çocuk anlık görüntüyü diske yazarken, ebeveyn yazmaya devam ediyor; yazılan her sayfa kopyalanıyor. Yazma yükü yüksekse bellek kullanımı en kötü durumda iki katına çıkar, bu yüzden Redis belgeleri `overcommit` ve sayfa boyutu ayarlarına dikkat çekiyor; büyük sayfalar (THP) tek baytlık yazmayı 2 MB kopyalamaya çevirdiği için bu senaryoda zararlı.

**5** – Sırayla beklerken ebeveyn, sonsuz süren çocukta takılı kalır; o çocuktan sonrakiler bitmişse hepsi **zombi** olarak bekler. `waitpid(-1, ...)` bitenleri bittikçe topladığı için zombi birikmez; takılan çocuk sonuna kadar süren tek kayıt olur.

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 4–5: süreç soyutlaması ve süreç API'si.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 24–28: süreç oluşturma, sonlandırma, izleme, program yürütme.
- W. Richard Stevens ve Stephen Rago, *Advanced Programming in the UNIX Environment* (3. baskı), Bölüm 8.
- Andrew Baumann ve ark., "A fork() in the road", *HotOS 2019*: `fork`'un modern sistemlerdeki bedellerinin eleştirisi.
- `man 2 fork`, `man 2 execve`, `man 2 waitpid`, `man 3 posix_spawn`.

**Sıradaki ders:** Mini kabuk (shell). Komut ayrıştırma, `fork`/`exec`, yönlendirme ve boru.
