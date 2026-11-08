---
title: "10.3 Tamponlu G/Ç sıfırdan"
description: "stdio'nun FILE* fikrini sıfırdan yazmak: tg kütüphanesi (tampon, tam / satır / tamponsuz kipler, tg_yaz, tg_getc, tg_satir, tg_bosalt); bayt bayt 8 MB yazmak: write ile 2078 ms ve 8.4 milyon çağrı, tamponla 68 ms ve 2048 çağrı, hızlı yolla 7.5 ms; stdout'un terminalde satır tamponlu, boruda tam tamponlu olması ve çıktının sırasının değişmesi; abort edince tampondaki satırın kaybolması; fork'un tamponu kopyalayıp satırı iki kez yazdırması; fflush'un çekirdeğe, fsync'in diske götürmesi."
---

Ders 10.2'de küçük tamponun felaket olduğunu gördük: 1 baytlık `read`/`write` 1000 kat yavaştı. Ama programlar veriyi çoğu zaman tek bayt ya da tek satır üretir; derleyicinin assembly çıktısı, `printf`'lerden oluşan bir log, bir `getc` döngüsü. Çözüm, küçük işleri **kullanıcı alanında** bir tamponda toplayıp çekirdeğe büyük parçalar halinde götürmek. C'nin `FILE*`'ı tam olarak bu. Bu derste onu sıfırdan yazıyoruz; Ders 10.20'deki kabuk projesinde bu kütüphaneyi kullanacağız.

---

## 1. Tasarım

Bir akış için gereken durum küçük:

- altındaki **dosya tanımlayıcısı**,
- bir **tampon** ve içindeki doluluğu gösteren indeksler,
- **kip**: ne zaman boşaltılacağı,
- hata ve dosya sonu bayrakları.

Yazma akışında `[0, son)` çekirdeğe henüz gitmemiş baytlar. Okuma akışında `[bas, son)` çekirdekten alınmış ama programa henüz verilmemiş baytlar.

```
yazma:  tampon [ x x x x x . . . . ]        okuma:  tampon [ . . x x x x . . ]
                 0         ↑son  kap                         bas↑     ↑son
                 └ bekleyen ┘                                 └verilmemis┘
```

Üç tamponlama kipi var, C standardının adlarıyla:

| Kip | Boşaltma zamanı | Tipik kullanım |
| --- | --- | --- |
| Tam tamponlu (`_IOFBF`) | Tampon dolunca | Dosyalar, borular |
| Satır tamponlu (`_IOLBF`) | Tampon dolunca **ya da `\n` gelince** | Terminale giden stdout |
| Tamponsuz (`_IONBF`) | Hemen | stderr |

```c
/* tg: kucuk bir tamponlu G/C kutuphanesi (stdio'nun FILE* fikrinin sifirdan yazimi) */
#ifndef TG_H
#define TG_H
#include <stddef.h>

typedef enum { TG_TAM, TG_SATIR, TG_YOK } TgMod;    /* tam tamponlu, satir tamponlu, tamponsuz */

typedef struct {
    int fd;
    int yazma;            /* 1: yazma akisi, 0: okuma akisi */
    TgMod mod;
    char *tampon;
    size_t kap;           /* tamponun boyutu */
    size_t bas, son;      /* okuma: [bas, son) henuz verilmemis baytlar; yazma: [0, son) bekleyen baytlar */
    int hata, eof;
    long cagri;           /* yapilan read/write sistem cagrisi sayisi (olcum icin) */
} TG;

TG    *tg_fdden(int fd, const char *kip, TgMod mod);
TG    *tg_ac(const char *yol, const char *kip);      /* "r", "w", "a" */
size_t tg_yaz(TG *f, const void *p, size_t n);
int    tg_putc(TG *f, int c);
int    tg_getc(TG *f);
size_t tg_oku(TG *f, void *p, size_t n);
char  *tg_satir(TG *f, char *s, size_t n);           /* fgets gibi */
int    tg_bosalt(TG *f);                              /* fflush gibi */
int    tg_kapat(TG *f);
#endif
```

```c
#include "tg.h"
#include <errno.h>
#include <fcntl.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define TG_KAP 4096

TG *tg_fdden(int fd, const char *kip, TgMod mod) {
    TG *f = calloc(1, sizeof *f);
    if (!f) return NULL;
    f->fd = fd; f->yazma = kip[0] != 'r'; f->mod = mod; f->kap = TG_KAP;
    f->tampon = malloc(f->kap);
    if (!f->tampon) { free(f); return NULL; }
    return f;
}

TG *tg_ac(const char *yol, const char *kip) {
    int bayrak = kip[0] == 'r' ? O_RDONLY
               : kip[0] == 'w' ? O_WRONLY | O_CREAT | O_TRUNC
               :                 O_WRONLY | O_CREAT | O_APPEND;
    int fd = open(yol, bayrak, 0644);
    if (fd < 0) return NULL;
    return tg_fdden(fd, kip, TG_TAM);
}

/* n baytin tamamini yaz; kismi write ve EINTR'yi halleder */
static int ham_yaz(TG *f, const char *p, size_t n) {
    while (n > 0) {
        ssize_t w = write(f->fd, p, n);
        f->cagri++;
        if (w < 0) { if (errno == EINTR) continue; f->hata = 1; return -1; }
        p += w; n -= (size_t)w;
    }
    return 0;
}

int tg_bosalt(TG *f) {
    if (!f->yazma || f->son == 0) return f->hata ? -1 : 0;
    int r = ham_yaz(f, f->tampon, f->son);
    f->son = 0;
    return r;
}

size_t tg_yaz(TG *f, const void *vp, size_t n) {
    const char *p = vp;
    if (f->mod == TG_YOK) return ham_yaz(f, p, n) == 0 ? n : 0;
    if (n > f->kap - f->son) {                 /* sigmiyor: once bekleyenleri bosalt */
        if (tg_bosalt(f) < 0) return 0;
        if (n >= f->kap) return ham_yaz(f, p, n) == 0 ? n : 0;   /* buyuk blok: tamponu atla */
    }
    memcpy(f->tampon + f->son, p, n);
    f->son += n;
    if (f->mod == TG_SATIR && memchr(p, '\n', n) && tg_bosalt(f) < 0) return 0;
    return n;
}

int tg_putc(TG *f, int c) {
    char b = (char)c;
    return tg_yaz(f, &b, 1) == 1 ? (unsigned char)c : -1;
}

/* tamponu dosyadan doldur; 1: veri var, 0: dosya sonu ya da hata */
static int doldur(TG *f) {
    for (;;) {
        ssize_t r = read(f->fd, f->tampon, f->kap);
        f->cagri++;
        if (r < 0) { if (errno == EINTR) continue; f->hata = 1; return 0; }
        if (r == 0) { f->eof = 1; return 0; }
        f->bas = 0; f->son = (size_t)r;
        return 1;
    }
}

int tg_getc(TG *f) {
    if (f->bas == f->son && !doldur(f)) return -1;
    return (unsigned char)f->tampon[f->bas++];
}

size_t tg_oku(TG *f, void *vp, size_t n) {
    char *p = vp; size_t top = 0;
    while (top < n) {
        if (f->bas == f->son && !doldur(f)) break;
        size_t k = f->son - f->bas;
        if (k > n - top) k = n - top;
        memcpy(p + top, f->tampon + f->bas, k);
        f->bas += k; top += k;
    }
    return top;
}

char *tg_satir(TG *f, char *s, size_t n) {
    size_t i = 0;
    while (i + 1 < n) {
        int c = tg_getc(f);
        if (c < 0) break;
        s[i++] = (char)c;
        if (c == '\n') break;
    }
    if (i == 0) return NULL;
    s[i] = 0;
    return s;
}

int tg_kapat(TG *f) {
    int r = tg_bosalt(f);
    if (close(f->fd) < 0) r = -1;
    free(f->tampon); free(f);
    return r;
}
```

Ayrıntılar:

- `tg_yaz`'da **büyük blok** yolu: tamponun kapasitesinden büyük bir veri, önce tampona kopyalanıp sonra yazılmak yerine doğrudan `write` ile gidiyor. Gereksiz bir `memcpy` kurtuluyor. Ama sıra korunmalı: önce bekleyenler boşaltılıyor.
- `tg_kapat` önce tamponu boşaltıyor. `close` çağrısı bunu **yapmaz**: çekirdek kullanıcı alanındaki tamponumuzdan habersiz.
- Dönüş değerleri stdio'daki gibi: `tg_getc`, bayt için 0–255, dosya sonu için -1; bu yüzden `int` (`char` olsaydı 0xFF baytı ile EOF karışırdı; `getchar`'ın da `int` döndürmesinin nedeni bu).

Test: satır satır yazıp okumak, üç kipte çağrı saymak (AddressSanitizer ile temiz):

```c
/* tg testi: satir satir okuyup numaralayarak yaz; tamponlama kiplerinde sistem cagrisi sayisi */
#include "tg.h"
#include <stdio.h>
#include <string.h>
int main(void) {
    TG *g = tg_ac("girdi.txt", "w");
    for (int i = 1; i <= 1000; i++) { char s[32]; int n = snprintf(s, sizeof s, "satir %d\n", i); tg_yaz(g, s, (size_t)n); }
    printf("yazma: %ld write cagrisi (kapatmadan once)\n", g->cagri);
    tg_kapat(g);
    TG *o = tg_ac("girdi.txt", "r");
    char s[64]; int say = 0; size_t top = 0;
    while (tg_satir(o, s, sizeof s)) { say++; top += strlen(s); }
    printf("okuma: %d satir, %zu bayt, %ld read cagrisi\n", say, top, o->cagri);
    tg_kapat(o);
    const TgMod modlar[] = { TG_TAM, TG_SATIR, TG_YOK };
    const char *adlar[] = { "tam", "satir", "yok" };
    for (int m = 0; m < 3; m++) {
        TG *c = tg_ac("c.txt", "w"); c->mod = modlar[m];
        for (int i = 1; i <= 1000; i++) { char t[32]; int n = snprintf(t, sizeof t, "satir %d\n", i); for (int k = 0; k < n; k++) tg_putc(c, t[k]); }
        tg_bosalt(c);
        printf("kip %-5s: %5ld write\n", adlar[m], c->cagri);
        tg_kapat(c);
    }
    return 0;
}
```

```
$ cc -g -O1 tg.c dene.c -o dene -fsanitize=address,undefined && ./dene
yazma: 2 write cagrisi (kapatmadan once)
okuma: 1000 satir, 9893 bayt, 4 read cagrisi
kip tam  :     3 write
kip satir:  1000 write
kip yok  :  9893 write
```

9893 bayt: tam tamponlu kipte $\lceil 9893 / 4096 \rceil = 3$ yazma; satır kipinde satır başına bir; tamponsuz kipte bayt başına bir. Okumada 3 dolum artı dosya sonunu öğrenen 4. `read`.

---

## 2. Ne kazandırıyor?

```c
/* 8 MB'yi bayt bayt yazmak: tamponsuz write, kendi tamponumuz, stdio */
#include "tg.h"
#include <fcntl.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>

enum { N = 8 * 1024 * 1024 };
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

int main(void) {
    double t0 = simdi();
    int fd = open("c1.bin", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    for (long i = 0; i < N; i++) { char c = (char)i; write(fd, &c, 1); }
    close(fd);
    double t1 = simdi();
    TG *g = tg_ac("c2.bin", "w");
    for (long i = 0; i < N; i++) tg_putc(g, (char)i);
    long cagri = g->cagri + 1;       /* son bosaltma */
    tg_kapat(g);
    double t2 = simdi();
    FILE *s = fopen("c3.bin", "w");
    for (long i = 0; i < N; i++) putc((char)i, s);
    fclose(s);
    double t3 = simdi();
    printf("write, bayt basina : %8.1f ms  (%d sistem cagrisi)\n", (t1 - t0) * 1e3, N);
    printf("tg_putc (4 KB)     : %8.1f ms  (%ld sistem cagrisi)\n", (t2 - t1) * 1e3, cagri);
    printf("stdio putc         : %8.1f ms\n", (t3 - t2) * 1e3);
    return 0;
}
```

```
$ cc -O2 -Wall -Wextra tg.c hiz.c -o hiz && ./hiz
write, bayt basina :   2077.9 ms  (8388608 sistem cagrisi)
tg_putc (4 KB)     :     67.7 ms  (2048 sistem cagrisi)
stdio putc         :     18.5 ms
```

(`cagri` satırı, son boşaltmayı da saydığımız için 2048: 8 MB tam 2048 tampon; son tampon `tg_kapat`'ta gidiyor.)

Sistem çağrısı sayısı 4096'da bir azaldı ve süre 30 kat düştü. stdio'nun `putc`'si bizimkinden 3.6 kat hızlı: çünkü `putc`, "tamponda yer var mı" kontrolünün ardından doğrudan bir baytı yazıyor; bizim `tg_putc` ise her bayt için `tg_yaz`'ı, oradan da `memcpy`'yi çağırıyor. Bu fark bayt başına ~6 ns. Alıştırma 2'de hızlı yolu ekleyip aradaki farkı kapatacağız, hatta stdio'yu geçeceğiz (stdio'nun kendi bedeli **kilit**: `putc` iş parçacığı güvenli; Ders 10.10).

---

## 3. stdout'un iki yüzü

C standardı stdout için şunu söylüyor: etkileşimli bir aygıta gitmiyorsa tam tamponlu olmalı. glibc'nin uygulaması: ilk yazmada `fstat` ve `ioctl(TCGETS)` ile "bu terminal mi?" diye soruyor (Ders 10.1'deki `strace`'te gördük). Terminalse satır tamponlu, değilse tam tamponlu. stderr her zaman tamponsuz.

Sonucu görmek için `printf` ile `write`'ı karıştıralım:

```c
/* stdout'un tamponlama kipi ve sira: terminalde ve boruda farkli */
#include <stdio.h>
#include <unistd.h>
int main(void) {
    printf("1: printf\n");
    write(1, "2: write\n", 9);
    printf("3: printf\n");
    fprintf(stderr, "4: stderr\n");
    write(1, "5: write\n", 9);
    return 0;
}
```

```
$ ./modlar                    # terminalde
1: printf
2: write
3: printf
4: stderr
5: write
$ ./modlar > o.txt 2>&1; cat o.txt
2: write
4: stderr
5: write
1: printf
3: printf
```

Aynı program, farklı sıra. Dosyaya yazarken `printf`'ler tamponda bekledi ve `return` sonrası `exit` onları **en sonda** tek `write` ile götürdü:

```
$ strace -e trace=write ./modlar 2>&1 >/dev/null
write(1, "2: write\n", 9)               = 9
write(2, "4: stderr\n", 10)             = 10
write(1, "5: write\n", 9)               = 9
write(1, "1: printf\n3: printf\n", 20)  = 20
```

Ders 10.2'deki `fdtablo` çıktısında `perror` satırının en üste çıkmasının nedeni de buydu. Pratik sonuçlar:

- Bir akışta `printf` ile `write`'ı karıştırma; karıştırmak zorundaysan `write`'tan önce `fflush(stdout)`.
- "Ekrana yazdırıp hata ayıklıyorum" yöntemi, çıktı yönlendirilince sırayı yalan söyler. Bu yüzden tanılamalar **stderr**'e gider.
- `grep` gibi araçların bir boruda çıktıyı geciktirmesi, `tail -f x | grep y | ...` zincirinin "takılı" görünmesi bu yüzden; `stdbuf -oL` ya da `grep --line-buffered` çözüm.

### Tamponda bekleyen veri kaybolabilir

```c
/* Tampondaki veri program cokunce kaybolur */
#include <stdio.h>
#include <stdlib.h>
int main(void) {
    printf("bu satir tamponda bekliyor\n");
    abort();
}
```

```
$ ./cokme                     # terminalde
bu satir tamponda bekliyor
Aborted
$ ./cokme | cat               # boruya
$ echo ${PIPESTATUS[0]}
134
```

Boruya yazarken satır **hiç çıkmadı**: `abort` süreci öldürdü, kullanıcı alanındaki tampon da süreçle birlikte yok oldu. "Program çöktü ama son logda hiçbir şey yok" durumunun klasik nedeni. Bu, Ders 10.1'in Alıştırma 3'ündeki `exit` sistem çağrısı farkıyla aynı olay: tamponu boşaltan şey libc'nin `exit`'i, çekirdek değil. (134 = 128 + 6: SIGABRT; Ders 10.6.)

### fork tamponu kopyalar

```c
/* fork tamponu da kopyalar */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void) {
    printf("once\n");
    if (fork() == 0) { printf("cocuk\n"); return 0; }
    wait(NULL);
    printf("ebeveyn\n");
    return 0;
}
```

```
$ ./catal                     # terminalde
once
cocuk
ebeveyn
$ ./catal | cat               # boruya
once
cocuk
once
ebeveyn
```

Boruya yazarken `once` **iki kez** çıktı. `fork` belleğin kopyasını çıkarıyor (Ders 10.4) ve bu, tamponda bekleyen `"once\n"`'i de kapsıyor. İki süreç sonunda kendi kopyasını boşaltıyor. Kabuğumuzu yazarken `fork`'tan önce `fflush` yapmamızın nedeni bu.

---

## 4. Veri nerede duruyor?

`printf`'ten diske kadar veri birkaç tampondan geçiyor:

```
printf ──▶ stdio tamponu ──fflush/write──▶ çekirdek sayfa önbelleği ──fsync──▶ disk denetleyicisi ──▶ kalıcı ortam
          (kullanıcı alanı)                (çekirdek)                          (aygıtın önbelleği)
```

- `fflush` veriyi **çekirdeğe** götürür. Program çökse bile artık veri güvende, başka süreçler de görür. Elektrik kesilirse kaybolabilir.
- Çekirdek veriyi **sayfa önbelleğinde** (page cache) tutuyor ve birkaç saniye içinde arka planda diske yazıyor. Yazmaların hızlı görünmesinin nedeni bu: Ders 10.2'deki 16 MB'lık kopya diske hiç değmemiş olabilir.
- `fsync(fd)` çekirdekten veriyi **kalıcı ortama** götürmesini ve o bitene kadar beklemesini istiyor. Veritabanlarının ve dikkatli editörlerin kullandığı şey bu ve pahalı (milisaniyeler).

Bir dosyayı güvenli güncellemenin standart yolu: geçici dosyaya yaz, `fflush`, `fsync`, sonra `rename` ile hedefin üzerine koy. `rename` atomik: dosyayı okuyan biri ya eskisini ya yenisini görür, yarım yazılmışını asla (Ders 10.15).

---

## Alıştırmalar

**1** – `tg.c`'de hem okuma hem yazma yapan bir akış yok. Neden stdio'da `"r+"` ile açılmış akışta okuma ile yazma arasında `fflush` ya da `fseek` çağırmak zorunlu? Tamponun durumunu düşünerek açıkla.

**2** – `tg_putc` yavaş. Başlık dosyasında `static inline` bir hızlı yol ekle: kip `TG_TAM` ve tamponda yer varsa baytı doğrudan yaz, yoksa yavaş yola git. 8 MB'lik testi tekrarla; stdio ile karşılaştır. Neden hızlı yol satır tamponlu kipte aynı şekilde çalışmıyor?

**3** – `tg_printf(TG *f, const char *bicim, ...)` yaz. `vsnprintf` ile önce yerel bir tampona yazıp `tg_yaz`'a ver. Çıktı yerel tampona sığmazsa ne yapmalısın? (`vsnprintf`'in dönüş değerine bak.)

**4** – Program şu sırayla çalışıyor: `printf("A"); write(1, "B", 1); fflush(stdout); write(1, "C", 1); printf("D\n");`. stdout terminalken ve dosyayken çıktı ne olur?

**5** – 1 milyon satır yazan bir program satır başına bir `fflush` yapıyor. Hangi amaçla yapılmış olabilir, bedeli ne (Ders 10.2'deki 225 ns'lik maliyetle)? Aynı garantiyi daha ucuza almanın bir yolu var mı?

<details>
<summary>Cevaplar</summary>

**1** – Tek bir tampon ve bir dosya konumu var. Yazma sonrası tamponda çekirdeğe gitmemiş baytlar var; hemen okumaya geçilirse okuma, o baytların dosyadaki yerinden değil, çekirdeğin geride kalmış konumundan okur. Okuma sonrası ise tamponda programın henüz almadığı baytlar var ve çekirdekteki konum programın gördüğünden **ileride**; yazılan baytlar yanlış yere gider. `fflush`/`fseek` tamponu boşaltıp çekirdekteki konumla programın mantıksal konumunu hizalıyor; C standardı bu yüzden arada zorunlu kılıyor.

**2** – Hızlı yol:

```c
static inline void tg_hizli_putc(TG *f, char c) {
    if (f->mod == TG_TAM && f->son < f->kap) f->tampon[f->son++] = c;
    else tg_putc(f, c);
}
```

Üç tekrarda ölçülen: `tg_putc` 71 ms, hızlı yol 7.5 ms, stdio `putc` 19 ms. Hızlı yol stdio'yu 2.5 kat geçiyor, çünkü stdio her `putc`'de akışın kilidini alıyor (iş parçacığı güvenliği); kilitsiz sürümü `putc_unlocked`. Satır tamponlu kipte her baytın `\n` olup olmadığına da bakmak gerekiyor, bu yüzden ek bir koşul lazım: `c != '\n'`. Tamponda yer olması tek başına yetmiyor.

**3** – `char yerel[256]; va_start(ap, bicim); int n = vsnprintf(yerel, sizeof yerel, bicim, ap); va_end(ap);`. `n`, gerçekte gereken bayt sayısı (`\0` hariç). `n >= sizeof yerel` ise çıktı kesilmiştir: `malloc(n + 1)` ile yeterli bir tampon ayırıp `va_start` ile argümanları **yeniden başlatarak** `vsnprintf`'i tekrar çağır, `tg_yaz`, `free`. `va_list` bir kez tüketilince yeniden kullanılamaz; bu yüzden `va_start` tekrar (ya da `va_copy`) şart.

**4** – Terminalde de dosyada da `A` tamponda (satır sonu yok, satır tamponlu kipte de `\n` görülene kadar bekliyor). `write(1, "B")` hemen çıkar: **B**. `fflush` `A`'yı götürür: **BA**. `write` **C**: **BAC**. `printf("D\n")`: terminalde `\n` boşaltır; dosyada `exit` sırasında gider. Sonuç her ikisinde de `BACD\n`. Bu özel sıra, `fflush` sayesinde iki kipte aynı; `fflush` olmasaydı dosyada `BCAD` olurdu, terminalde de `BCAD` (`A` satır sonunu beklerdi).

**5** – Her satırın, program çökse bile, kaybolmamasını istiyordur (log dosyaları) ya da satırı bekleyen bir okuyucu vardır. Bedel: $10^6$ `write` $\times$ 225 ns $\approx$ 0.23 s; toplu yazmaya göre 1–2 büyüklük mertebesi yavaş. Ucuz alternatifler: (a) çökme durumunda tamponu boşaltan bir sinyal işleyicisi güvenilir değil (Ders 10.6: `fflush` async-signal-safe değil); (b) `mmap` ile dosyaya doğrudan yazmak: program çökse de sayfalar çekirdekte kalır (Ders 10.7); (c) her $N$ satırda ya da her 100 ms'de bir boşaltmak, kaybı sınırlayan ucuz bir uzlaşma. `setvbuf(stdout, NULL, _IOLBF, 0)` da aynı şeyi yapar ve aynı bedeli öder.

</details>

---

## Kaynaklar

- Brian Kernighan ve Dennis Ritchie, *The C Programming Language* (2. baskı), Bölüm 8.5: `fopen` ve `getc` uygulaması; kısa bir `FILE` tasarımı.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 13: dosya G/Ç'de tamponlama, stdio tamponu, çekirdek tamponu, `fsync`.
- W. Richard Stevens ve Stephen Rago, *Advanced Programming in the UNIX Environment* (3. baskı), Bölüm 5: standart G/Ç kütüphanesi.
- C11 standardı, §7.21.3: akışların tamponlama kuralları.
- `man 3 setvbuf`, `man 3 fflush`, `man 2 fsync`.

**Sıradaki ders:** Süreçler. `fork`, `exec`, `wait` ve süreç ağacı.
