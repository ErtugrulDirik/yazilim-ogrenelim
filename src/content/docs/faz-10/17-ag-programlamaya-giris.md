---
title: "10.17 Ağ programlamaya giriş"
description: "Soket: dosya tanımlayıcısı gibi davranan ağ ucu; socket, bind, listen, accept, connect; 127.0.0.1 üzerinde yankı sunucusu ve istemci; her bağlantıya bir süreç ve poll ile tek süreçli olay döngüsü, yük altında karşılaştırma; TCP'nin bir bayt akışı olması: üç write tek read ile geldi; Nagle ve gecikmeli ACK: yaz-yaz-oku kalıbında tur başına 42 ms, TCP_NODELAY ile 0.05 ms; bayt sırası, SIGPIPE, kısmi okuma."
---

Ders 10.2'de "her şey bir dosya" dedik; Ders 10.5'te bir boru iki süreci aynı makinede bağladı. **Soket** aynı fikri ağa taşıyor: bir ucu başka bir makinede olabilen, `read`/`write` ile kullanılan bir dosya tanımlayıcısı. Derleyici açısından: dağıtık derleme (`distcc`), dil sunucuları (LSP), JIT kod önbellekleri hep bu arayüzle konuşuyor.

Bu ders TCP/IP'nin ayrıntılarına girmiyor; sadece programcının gördüğü arayüz ve onun tuzakları.

---

## 1. Sunucu ve istemci

TCP'de iki rol var. **Sunucu**, bir adres ve portu dinler; **istemci** ona bağlanır. Bağlantı kurulunca iki yönlü bir bayt borusu oluşur.

```
sunucu                                  istemci
socket()                                socket()
bind(adres, port)
listen()
accept()  ◀───── 3'lü el sıkışma ─────  connect(adres, port)
read() / write()  ◀───── baytlar ─────▶ write() / read()
close()                                 close()
```

```c
/* Yanki sunucusu: her baglantiya bir surec */
#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

static void cocuk_topla(int s) { (void)s; int k = errno; while (waitpid(-1, NULL, WNOHANG) > 0) { } errno = k; }

static int tam_yaz(int fd, const char *p, size_t n) {
    while (n > 0) {
        ssize_t w = write(fd, p, n);
        if (w < 0) { if (errno == EINTR) continue; return -1; }
        p += w; n -= (size_t)w;
    }
    return 0;
}

static void yanitla(int c) {
    char b[4096]; ssize_t r;
    while ((r = read(c, b, sizeof b)) > 0) if (tam_yaz(c, b, (size_t)r) < 0) break;
}

int main(int argc, char **argv) {
    int port = argc > 1 ? atoi(argv[1]) : 9000;
    signal(SIGPIPE, SIG_IGN);
    struct sigaction sa; memset(&sa, 0, sizeof sa); sa.sa_handler = cocuk_topla; sa.sa_flags = SA_RESTART; sigaction(SIGCHLD, &sa, NULL);

    int s = socket(AF_INET, SOCK_STREAM, 0);
    if (s < 0) { perror("socket"); return 1; }
    int bir = 1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &bir, sizeof bir);
    struct sockaddr_in a; memset(&a, 0, sizeof a);
    a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(s, (struct sockaddr *)&a, sizeof a) < 0) { perror("bind"); return 1; }
    if (listen(s, 128) < 0) { perror("listen"); return 1; }
    fprintf(stderr, "dinliyorum: 127.0.0.1:%d\n", port);
    for (;;) {
        struct sockaddr_in k; socklen_t kl = sizeof k;
        int c = accept(s, (struct sockaddr *)&k, &kl);
        if (c < 0) { if (errno == EINTR) continue; perror("accept"); return 1; }
        pid_t p = fork();
        if (p == 0) { close(s); yanitla(c); close(c); _exit(0); }
        close(c);
    }
}
```

```c
/* Yanki istemcisi: argumanlari gonderir, gelen yaniti yazar */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
int main(int argc, char **argv) {
    if (argc < 3) { fprintf(stderr, "kullanim: %s port mesaj\n", argv[0]); return 2; }
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a; memset(&a, 0, sizeof a);
    a.sin_family = AF_INET; a.sin_port = htons((uint16_t)atoi(argv[1]));
    inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    if (connect(s, (struct sockaddr *)&a, sizeof a) < 0) { perror("connect"); return 1; }
    size_t n = strlen(argv[2]);
    write(s, argv[2], n);
    shutdown(s, SHUT_WR);                       /* "gonderecegim bitti": sunucu EOF gorur */
    char b[256]; ssize_t r;
    while ((r = read(s, b, sizeof b)) > 0) fwrite(b, 1, (size_t)r, stdout);
    putchar('\n');
    close(s);
    return 0;
}
```

```
$ ./sunucu 9000 &
dinliyorum: 127.0.0.1:9000
$ ./istemci 9000 "merhaba tcp"
merhaba tcp
$ strace -e trace=write,read,shutdown,close ./istemci 9002 selam
write(3, "selam", 5)                    = 5
shutdown(3, SHUT_WR)                    = 0
read(3, "selam", 256)                   = 5
read(3, "", 256)                        = 0
close(3)                                = 0
```

Bu kodun her parçası tanıdık:

- **Çok baytlı sayılar için `htons`/`htonl`.** Ağ bayt sırası big-endian; arm64 ve x86 little-endian (Ders 3.9). Port numarasını çevirmeyi unutursan 9000 yerine 10275'e bağlanırsın.
- `SO_REUSEADDR`: yeni başlayan sunucunun, bir önceki kapatılan bağlantıların `TIME_WAIT` durumuna takılmadan aynı porta bağlanmasını sağlıyor. Olmazsa yeniden başlatmada `Address already in use` alırsın.
- `accept` **yeni** bir soket döndürüyor; dinleyen soket dinlemeye devam ediyor. `fork` ile çocukta `close(s)`, ebeveynde `close(c)`: Ders 10.5'teki "kullanmadığın ucu kapat" kuralının aynısı.
- `SIGPIPE`'ı yok saymak **şart**: karşı taraf kapanınca `write` yoksa süreci öldürür (Ders 10.5). `send(..., MSG_NOSIGNAL)` başka bir yol.
- `SIGCHLD` ile çocuk toplama: Ders 10.6'daki döngü.
- `shutdown(s, SHUT_WR)`: yazma yönünü kapatıyor ama okumayı sürdürüyor; karşı taraf `read` ile 0 alıyor. Sadece `close` iki yönü de kapatırdı.

`read`/`write` soketlerde tam da Ders 10.2'deki kısmi davranışı gösteriyor; `tam_yaz` burada şart.

---

## 2. Ölçeklemek: süreç mi, olay döngüsü mü

Her bağlantıya bir süreç, en sade tasarım. Binlerce bağlantı olunca bellek ve bağlam değişimi (Ders 10.14) pahalılaşır. Alternatif: **tek süreçte** bütün soketleri izlemek. `poll`, bir tanımlayıcı listesinden "hangisi hazır?" diye soruyor.

```c
/* Yanki sunucusu: tek surec, poll ile olay dongusu */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>
enum { EN_COK = 1024 };
int main(int argc, char **argv) {
    int port = argc > 1 ? atoi(argv[1]) : 9001;
    signal(SIGPIPE, SIG_IGN);
    int s = socket(AF_INET, SOCK_STREAM, 0);
    int bir = 1; setsockopt(s, SOL_SOCKET, SO_REUSEADDR, &bir, sizeof bir);
    struct sockaddr_in a; memset(&a, 0, sizeof a);
    a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port); a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    if (bind(s, (struct sockaddr *)&a, sizeof a) < 0 || listen(s, 128) < 0) { perror("bind/listen"); return 1; }
    fcntl(s, F_SETFL, O_NONBLOCK);
    struct pollfd p[EN_COK]; int n = 1;
    p[0].fd = s; p[0].events = POLLIN;
    for (;;) {
        if (poll(p, (nfds_t)n, -1) < 0) { if (errno == EINTR) continue; perror("poll"); return 1; }
        for (int i = n - 1; i >= 1; i--) {
            if (!(p[i].revents & (POLLIN | POLLHUP | POLLERR))) continue;
            char b[4096];
            ssize_t r = read(p[i].fd, b, sizeof b);
            if (r > 0) { if (write(p[i].fd, b, (size_t)r) == r) continue; }
            else if (r < 0 && errno == EAGAIN) continue;
            close(p[i].fd); p[i] = p[--n];
        }
        if (p[0].revents & POLLIN) {
            int c;
            while ((c = accept(s, NULL, NULL)) >= 0) {
                if (n == EN_COK) { close(c); continue; }
                fcntl(c, F_SETFL, O_NONBLOCK);
                p[n].fd = c; p[n].events = POLLIN; p[n].revents = 0; n++;
            }
        }
    }
}
```

Küçük bir yük üreticisi (`K` iş parçacığı, her biri 8 baytlık `R` gidiş-dönüş yapıyor) iki sunucuyu da aynı anda vurduğumuzda:

```
$ ./yuk 9000 K R        # fork'lu sunucu
$ ./yuk 9001 K R        # poll'lu sunucu
   1 baglanti x 20000 tur: 0.72 s, 27780 gidis-donus/s    # fork
   1 baglanti x 20000 tur: 0.72 s, 27851 gidis-donus/s    # poll
  10 baglanti x 2000 tur: 0.10 s, 208117 gidis-donus/s    # fork
  10 baglanti x 2000 tur: 0.16 s, 124193 gidis-donus/s    # poll
 100 baglanti x 200 tur: 0.16 s, 122898 gidis-donus/s     # fork
 100 baglanti x 200 tur: 0.15 s, 131117 gidis-donus/s     # poll
```

Sonuç sezginin tersi gibi görünebilir: 10 bağlantıda fork'lu sunucu **önde**. Nedeni basit: fork'lu sunucu birden çok çekirdek kullanıyor, poll'lu sunucu tek iş parçacığı. 100 bağlantıda fark kapanıyor, çünkü artık bağlam değişimleri ve yük üreticisi de aynı 8 çekirdeği paylaşıyor. Olay döngüsünün asıl üstünlüğü **çok sayıda boşta bağlantıda**: 10 000 açık ama çoğu sessiz bağlantı için 10 000 süreç yerine tek süreç (C10K problemi). Üretimde `poll` yerine `epoll` (Linux) ya da `kqueue` (BSD) kullanılıyor, çünkü `poll` her çağrıda bütün listeyi tarıyor; birkaç iş parçacığı + `epoll` çok yaygın.

Buradaki olay döngüsünün önemli bir eksiği var: `write` kısmen gerçekleşirse kalan baytları saklamak ve `POLLOUT` beklemek gerekiyor; biz sadece bağlantıyı kapatıyoruz. Bu eksik, olay döngülerinin en karmaşık kısmı.

---

## 3. TCP bir bayt akışıdır

TCP mesaj sınırlarını **korumaz**. Üç `write` tek `read`'de birleşebilir, tek bir `write` birden çok `read`'e bölünebilir.

```c
/* TCP bir bayt akisidir: mesaj sinirlari korunmaz */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>
static int dinle(int *port) {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a; memset(&a, 0, sizeof a); a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    bind(s, (struct sockaddr *)&a, sizeof a); listen(s, 1);
    socklen_t l = sizeof a; getsockname(s, (struct sockaddr *)&a, &l); *port = ntohs(a.sin_port);
    return s;
}
static int baglan(int port) {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a; memset(&a, 0, sizeof a); a.sin_family = AF_INET; a.sin_port = htons((uint16_t)port); inet_pton(AF_INET, "127.0.0.1", &a.sin_addr);
    connect(s, (struct sockaddr *)&a, sizeof a);
    return s;
}
int main(void) {
    setbuf(stdout, NULL);
    int port, s = dinle(&port);
    pid_t p = fork();
    if (p == 0) {
        int c = baglan(port);
        write(c, "bir", 3); write(c, "iki", 3); write(c, "uc", 2);
        usleep(200000);
        static char buyuk[1 << 21];
        write(c, buyuk, sizeof buyuk);
        close(c); _exit(0);
    }
    int c = accept(s, NULL, NULL);
    usleep(100000);
    char b[256];
    ssize_t r = read(c, b, sizeof b);
    printf("uc ayri write, tek read: %zd bayt: \"%.*s\"\n", r, (int)r, b);
    static char t[1 << 21]; long say = 0, top = 0;
    while ((r = read(c, t, sizeof t)) > 0) { say++; top += r; }
    printf("2 MB'lik tek write: %ld bayt, %ld read ile geldi\n", top, say);
    wait(NULL);
    return 0;
}
```

```
$ ./sinir
uc ayri write, tek read: 8 bayt: "birikiuc"
2 MB'lik tek write: 2097152 bayt, 2 read ile geldi
```

`"bir"`, `"iki"`, `"uc"` tek bir `"birikiuc"` oldu. Uygulama kendi **çerçeveleme** protokolünü yapmak zorunda. Üç yaygın yol:

- **Sabit uzunluk**: her mesaj N bayt.
- **Ayraç**: satır sonu (`\n`), HTTP başlıkları, Redis protokolü.
- **Uzunluk öneki**: önce 4 baytlık boyut (ağ sırasıyla), sonra içerik. İkili protokollerin çoğu.

"Yazdığım her `write` bir mesajdır" varsayımı, testte (localhost, küçük mesaj) çalışan ama üretimde bozulan klasik bir hata.

---

## 4. Nagle ve gecikmeli ACK

TCP varsayılan olarak küçük paketleri biriktiriyor (**Nagle algoritması**): "gönderilmiş ama onaylanmamış bir veri varsa yeni küçük veriyi bekletiyor". Alıcı da onayları (ACK) kısa süre geciktiriyor. İkisi birleşince ünlü bir tuzak: iki küçük `write` ardından cevap beklemek.

```c
/* Nagle ve gecikmeli ACK: yaz-yaz-oku kalibi */
#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static void dene(int nodelay, int birlestir) {
    int s = socket(AF_INET, SOCK_STREAM, 0);
    struct sockaddr_in a; memset(&a, 0, sizeof a); a.sin_family = AF_INET; a.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    bind(s, (struct sockaddr *)&a, sizeof a); listen(s, 1);
    socklen_t l = sizeof a; getsockname(s, (struct sockaddr *)&a, &l);
    enum { R = 100 };
    pid_t p = fork();
    if (p == 0) {
        int c = accept(s, NULL, NULL); char b[8];
        for (int i = 0; i < R; i++) { size_t k = 0; while (k < 8) { ssize_t r = read(c, b + k, 8 - k); if (r <= 0) _exit(0); k += (size_t)r; } write(c, "y", 1); }
        _exit(0);
    }
    int c = socket(AF_INET, SOCK_STREAM, 0);
    connect(c, (struct sockaddr *)&a, sizeof a);
    int v = nodelay; setsockopt(c, IPPROTO_TCP, TCP_NODELAY, &v, sizeof v);
    double t0 = simdi(); char y;
    for (int i = 0; i < R; i++) {
        if (birlestir) write(c, "abcdefgh", 8);
        else { write(c, "abcd", 4); write(c, "efgh", 4); }
        read(c, &y, 1);
    }
    printf("%-30s %8.2f ms / tur\n", nodelay ? "TCP_NODELAY, iki write" : birlestir ? "Nagle acik, tek write" : "Nagle acik, iki write", (simdi() - t0) / R * 1e3);
    close(c); close(s); wait(NULL);
}
int main(void) { setbuf(stdout, NULL); dene(0, 0); dene(1, 0); dene(0, 1); return 0; }
```

```
$ ./nagle
Nagle acik, iki write             42.47 ms / tur
TCP_NODELAY, iki write             0.05 ms / tur
Nagle acik, tek write              0.04 ms / tur
```

Aynı makine, aynı veri: **850 kat** fark. İkinci küçük `write`, birincinin onayını bekliyor; karşı taraf ise onayı 40 ms geciktiriyor çünkü henüz cevap yazacak bir şeyi yok (8 baytı beklediğinden). En iyi çözüm tablonun son satırı: uygulamada **tek write** ile göndermek (Ders 10.3'teki tamponlama). `TCP_NODELAY` ise etkileşimli protokollerde gecikme kritikse açılıyor.

---

## Alıştırmalar

**1** – Yankı sunucusunu **iş parçacığı** başına bir bağlantı olacak şekilde değiştir (Ders 10.9). Süreç sürümüne göre neyi paylaşır, neyi kaybedersin?

**2** – Uzunluk önekli çerçeveleme yaz: `mesaj_gonder(fd, p, n)` ve `mesaj_al(fd, p, en_cok)`. Kısmi okuma ve bozuk uzunluk (örneğin çok büyük) durumlarını ele al.

**3** – Yankı sunucusu yerine en basit **HTTP/1.0** sunucusunu yaz: istek satırını oku, dosyayı bul, `HTTP/1.0 200 OK` ve `Content-Length` ile gönder; bulamazsan 404. Tarayıcı ve `curl` ile dene. `../` yol geçişine karşı ne yapmalısın?

**4** – Olay döngüsündeki kısmi `write` eksiğini düzelt: bağlantı başına bir çıkış tamponu, doluyken `POLLOUT` bekleme.

**5** – Sunucuyu çalıştır, bir istemci bağlıyken öldür, hemen yeniden başlat. `SO_REUSEADDR` kaldırılınca ne oluyor? `ss -tan` ile `TIME_WAIT` satırlarına bak.

<details>
<summary>Cevaplar</summary>

**1** – `pthread_create(&t, NULL, f, (void*)(intptr_t)c)`, `pthread_detach`. Oluşturma daha ucuz (Ders 10.9'da 47 µs / 117 µs), bellek ve önbellek paylaşılıyor. Kaybedilen: yalıtım: bir bağlantıdaki `SIGSEGV` tüm sunucuyu düşürür; paylaşılan veriye erişim için kilit gerekir (Ders 10.10). Çok kullanıcılı güvenlik (ayrı süreç + `setuid`) için süreç hâlâ avantajlı.

**2** – Gönderme: `uint32_t u = htonl(n); tam_yaz(fd, &u, 4); tam_yaz(fd, p, n);` (ya da tek tampona koyup tek `write` ile, Bölüm 4). Alma: `tam_oku(fd, &u, 4)` (döngüde, 0 dönerse bağlantı kapandı, kısmi başlık hata), `n = ntohl(u)`, `n > en_cok` ise protokol hatası (saldırgan 4 GB iddia edebilir), sonra `tam_oku(fd, p, n)`. Bellek ayırmadan önce sınırı kontrol etmek güvenlik açısından kritik.

**3** – `GET /yol HTTP/1.0\r\n` satırını `\r\n\r\n`'e kadar oku. Yolu `realpath` ile çözüp kök dizinin içinde kaldığını kontrol et, ya da `..` içeren yolu reddet. Dosya `open`, boyut `fstat`, başlıkları yaz, gövdeyi `sendfile` ile (kullanıcı alanına kopyalamadan) gönder. `Connection: close` ile HTTP/1.0 basit kalır.

**4** – Bağlantı yapısına `char *cik; size_t cik_n;`. `write` kısmi dönerse kalanı `cik`'e al, `events |= POLLOUT`; `POLLOUT` gelince kalan yazılır ve bitince bayrak kaldırılır. Çıkış tamponu kapasitesini aşınca okumayı durdur (geri basınç), yoksa yavaş istemci belleği tüketir.

**5** – Çoğu kez `bind: Address already in use`: bir önceki sürecin bağlantıları `TIME_WAIT` durumunda (aktif kapatma tarafı 2×MSL boyunca bekler ki geç gelen paketler yeni bağlantıya karışmasın). `SO_REUSEADDR`, aynı port üzerinde `TIME_WAIT` varken bağlanmaya izin verir, ama aktif dinleyen bir soket üzerine değil.

</details>

---

## Kaynaklar

- W. Richard Stevens, Bill Fenner ve Andrew Rudoff, *UNIX Network Programming*, Cilt 1 (3. baskı): soket API'sinin temel referansı.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 56–63: soketler, alternatif G/Ç modelleri, `poll`, `epoll`.
- John Nagle, "Congestion Control in IP/TCP Internetworks", RFC 896, 1984.
- Dan Kegel, "The C10K Problem" (kegel.com/c10k.html).
- `man 7 socket`, `man 7 tcp`, `man 2 poll`, `man 7 epoll`.

**Sıradaki ders:** Performans ölçümü. `time`, `clock_gettime`, `perf stat`, `perf record`.
