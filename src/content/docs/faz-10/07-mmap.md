---
title: "10.7 mmap"
description: "mmap: adres alanına yeni bir bölge eklemek; 257 MB'lik dosyada satır saymak: read 4 KB 62 ms, read 1 MB 54 ms, mmap 49 ms ve 16'şar sayfalık fault-around sayesinde 65 bin yerine 4115 sayfa hatası; MAP_PRIVATE ve MAP_SHARED, süreçler arası paylaşım; anonim eşlemenin tembelliği: 1 GB sanal, 1 MB fiziksel; MADV_DONTNEED ile belleği geri vermek, PROT_NONE ile 1 TB rezervasyon; Ders 4.29'daki ilk-yeten allocator'ı mmap ile beslemek, büyük blokları ayrı eşlemek ve glibc ile karşılaştırma."
---

Ders 10.1'deki `strace`'te libc `read` ile okunmamıştı: `mmap(..., PROT_READ|PROT_EXEC, ..., 3, 0)` ile **eşlenmişti**. `malloc`'un büyük blokları, paylaşılan kütüphaneler, JIT derleyicilerin kod belleği, modern derleyicilerin kaynak dosyalarını okuması hep bu çağrıyla. `mmap`, Ders 7.27'deki sanal bellek mekanizmasının programcıya açılan kapısı.

---

## 1. Çağrı

```c
#include <sys/mman.h>
void *mmap(void *adres, size_t uzunluk, int izin, int bayraklar, int fd, off_t konum);
int   munmap(void *adres, size_t uzunluk);
int   mprotect(void *adres, size_t uzunluk, int izin);
```

`mmap`, sürecin adres alanına yeni bir **bölge** ekliyor ve başlangıç adresini döndürüyor (hata: `MAP_FAILED`, `NULL` değil). Boyut sayfa katlarına yuvarlanıyor.

| Parametre | Değerler |
| --- | --- |
| `izin` | `PROT_READ`, `PROT_WRITE`, `PROT_EXEC`, `PROT_NONE` |
| Paylaşım | `MAP_SHARED` (yazılanlar dosyaya / diğer süreçlere gider), `MAP_PRIVATE` (copy-on-write, sadece bende) |
| Kaynak | Dosya (`fd`, `konum`) ya da `MAP_ANONYMOUS` (`fd = -1`; sıfırlanmış bellek) |

Dört kombinasyon, dört tanıdık kullanım:

| | `MAP_PRIVATE` | `MAP_SHARED` |
| --- | --- | --- |
| **Dosya** | Programın kod ve veri bölümleri, kütüphaneler | Dosyayı bellek gibi düzenlemek, veritabanları |
| **Anonim** | `malloc`, iş parçacığı yığınları | `fork` edilen süreçler arası paylaşım |

---

## 2. Dosya eşlemek

Eşlenmiş bir dosya, bir `char` dizisi gibi okunur. Çekirdek okunan sayfa henüz bellekte değilse sayfa hatasıyla diskten getiriyor (Ders 7.27); araya `read` girmiyor, kullanıcı alanına kopya çıkmıyor.

```c
/* 256 MB dosyadaki satir sonlarini saymak: read ile, mmap ile */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static long hata(void) { struct rusage r; getrusage(RUSAGE_SELF, &r); return r.ru_minflt; }

static long read_ile(const char *yol, size_t boy) {
    int fd = open(yol, O_RDONLY); char *t = malloc(boy); long say = 0; ssize_t r;
    while ((r = read(fd, t, boy)) > 0) for (ssize_t i = 0; i < r; i++) say += t[i] == '\n';
    close(fd); free(t); return say;
}
static long mmap_ile(const char *yol) {
    int fd = open(yol, O_RDONLY); struct stat s; fstat(fd, &s);
    char *p = mmap(NULL, (size_t)s.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    close(fd);                                  /* esleme fd'den bagimsiz yasar */
    long say = 0;
    for (off_t i = 0; i < s.st_size; i++) say += p[i] == '\n';
    munmap(p, (size_t)s.st_size); return say;
}
int main(int argc, char **argv) {
    (void)argc;
    for (int r = 0; r < 2; r++) {
        double t0 = simdi(); long h0 = hata(); long a = read_ile(argv[1], 4096);
        double t1 = simdi(); long h1 = hata(); long b = read_ile(argv[1], 1 << 20);
        double t2 = simdi(); long h2 = hata(); long c = mmap_ile(argv[1]);
        double t3 = simdi(); long h3 = hata();
        printf("read 4 KB : %6.1f ms %6ld hata, %ld satir\n", (t1 - t0) * 1e3, h1 - h0, a);
        printf("read 1 MB : %6.1f ms %6ld hata, %ld satir\n", (t2 - t1) * 1e3, h2 - h1, b);
        printf("mmap      : %6.1f ms %6ld hata, %ld satir\n", (t3 - t2) * 1e3, h3 - h2, c);
    }
    return 0;
}
```

```
$ ls -l b.txt
-rw-r--r-- 1 root root 269628480 Nov  8 16:06 b.txt
$ ./say b.txt
read 4 KB :   62.0 ms      4 hata, 6600000 satir
read 1 MB :   54.2 ms    257 hata, 6600000 satir
mmap      :   49.0 ms   4115 hata, 6600000 satir
read 4 KB :   62.0 ms      1 hata, 6600000 satir
read 1 MB :   54.1 ms    255 hata, 6600000 satir
mmap      :   49.0 ms   4115 hata, 6600000 satir
```

Dosya sayfa önbelleğindeyken (disk devrede değil) `mmap` kazanıyor ama **sınırlı**: %21 ve %10. `mmap` sihirli değil: bu programda sürenin çoğu satır sayma döngüsünde, `read`'in ek maliyeti (kopya) yalnızca küçük bir payı. `read` ile sayfa başına bir kopya var; `mmap` ile kopya yok ama sayfa hatası var.

Sayfa hatası sayısı ilginç: dosya $269\,628\,480 / 4096 \approx 65\,827$ sayfa, oysa sadece 4115 hata oldu. Oran: tam **16**. Linux'un **fault-around** özelliği, sayfa önbelleğinde hazır duran 16 komşu sayfayı tek hatada eşliyor. (`read 1 MB`'deki ~256 hata ise tamponun ilk dokunuşu: 1 MB / 4 KB.)

`mmap` ne zaman gerçekten iyi?

- **Rastgele erişim**: dosyanın içinde atlaya atlaya gezmek. `read` ile her atlayış bir `lseek` + `read`; `mmap` ile sadece pointer aritmetiği. Veritabanları, ELF dosyaları, derleyicinin önceden derlenmiş başlıkları (PCH).
- **Paylaşım**: aynı dosyayı eşleyen süreçler fiziksel sayfaları paylaşıyor. Binlerce sürecin aynı libc'yi kullanması RAM'i tek kopya kadar yiyor.
- **Dosya-veri yapısı**: dosyadaki bir yapıya ayrıştırma yapmadan doğrudan pointer'la bakmak.

Bedeli: G/Ç hatası `read`'de `-1` iken `mmap`'te **sinyal** (`SIGBUS`): dosya başka biri tarafından küçültülürse. Boş dosya eşlenemez (`EINVAL`), kod bunu kontrol etmeli. `read` satır satır akışlar için çok iyi; boru ve soketlerde zaten `mmap` çalışmaz.

### Paylaşım deneyi

```c
/* MAP_SHARED, MAP_PRIVATE ve surecler arasi paylasim */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
static void hazirla(void) { int f = open("d.txt", O_WRONLY | O_CREAT | O_TRUNC, 0644); write(f, "merhaba dunya\n", 14); close(f); }
static void goster(const char *e) { char t[32] = { 0 }; int f = open("d.txt", O_RDONLY); read(f, t, 14); close(f); printf("%-34s dosya: %s", e, t); }
int main(void) {
    hazirla();
    int f = open("d.txt", O_RDWR);
    char *p = mmap(NULL, 14, PROT_READ | PROT_WRITE, MAP_PRIVATE, f, 0);
    memcpy(p, "MERHABA", 7);
    printf("bellekte: %.14s", p);
    goster("MAP_PRIVATE yazdiktan sonra");
    munmap(p, 14);
    p = mmap(NULL, 14, PROT_READ | PROT_WRITE, MAP_SHARED, f, 0);
    memcpy(p, "SELAM  ", 7);
    goster("MAP_SHARED yazdiktan sonra");
    munmap(p, 14); close(f);

    int *s = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    int *o = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (fork() == 0) { *s = 42; *o = 42; _exit(0); }
    wait(NULL);
    printf("cocuk yazdi: paylasilan=%d, ozel=%d\n", *s, *o);
    return 0;
}
```

```
$ ./paylas
bellekte: MERHABA dunya
MAP_PRIVATE yazdiktan sonra        dosya: merhaba dunya
MAP_SHARED yazdiktan sonra         dosya: SELAM   dunya
cocuk yazdi: paylasilan=42, ozel=0
```

`MAP_SHARED`'e yazmak için `write` gerekmedi: bellekteki değişiklik dosyaya yansıdı, `read` hemen gördü (ikisi de aynı sayfa önbelleğine bakıyor). Diske ne zaman ulaşacağı `msync` çağrısıyla kontrol ediliyor (`fsync`'in eşleme karşılığı). Anonim `MAP_SHARED` ise `fork` edilen süreçler arasındaki en basit paylaşılan bellek; Ders 10.12'de atomik sayaçları böyle süreçler arasında da kullanabileceğiz.

---

## 3. Anonim eşleme ve tembellik

`mmap` çağrısı fiziksel bellek ayırmıyor: sadece "bu aralık geçerli" diye bir kayıt oluşturuyor. Fiziksel sayfa, ilk dokunuşta sayfa hatasıyla geliyor (Ders 7.27).

```c
/* Anonim esleme tembeldir: VmRSS sadece dokunulan sayfalar kadar artar */
#define _GNU_SOURCE
#include <signal.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
static void bellek(const char *e) {
    FILE *f = fopen("/proc/self/status", "r"); char s[128]; long vsz = 0, rss = 0;
    while (fgets(s, sizeof s, f)) { sscanf(s, "VmSize: %ld", &vsz); sscanf(s, "VmRSS: %ld", &rss); }
    fclose(f);
    printf("%-30s sanal %10ld KB, fiziksel %8ld KB\n", e, vsz, rss);
}
int main(void) {
    bellek("baslangic");
    size_t n = 1UL << 30;
    char *p = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    bellek("1 GB mmap sonrasi");
    madvise(p, n, MADV_NOHUGEPAGE);
    memset(p, 1, 100UL << 20);
    bellek("100 MB dokunulunca");
    madvise(p, 100UL << 20, MADV_DONTNEED);
    bellek("MADV_DONTNEED sonrasi");
    printf("geri alinan sayfa okununca: %d\n", p[0]);
    munmap(p, n);
    bellek("munmap sonrasi");
    size_t tb = 1UL << 40;
    char *q = mmap(NULL, tb, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0);
    printf("1 TB rezervasyon: %s\n", q == MAP_FAILED ? "basarisiz" : "tamam");
    if (q != MAP_FAILED) {
        bellek("1 TB rezerve edilince");
        mprotect(q, 1UL << 20, PROT_READ | PROT_WRITE);
        q[0] = 1;
        bellek("ilk MB acilip dokunulunca");
    }
    return 0;
}
```

```
$ ./tembel
baslangic                      sanal       2252 KB, fiziksel     1060 KB
1 GB mmap sonrasi              sanal    1050828 KB, fiziksel     1188 KB
100 MB dokunulunca             sanal    1050828 KB, fiziksel   103588 KB
MADV_DONTNEED sonrasi          sanal    1050828 KB, fiziksel     1272 KB
geri alinan sayfa okununca: 0
munmap sonrasi                 sanal       2252 KB, fiziksel     1272 KB
1 TB rezervasyon: tamam
1 TB rezerve edilince          sanal 1073744076 KB, fiziksel     1272 KB
ilk MB acilip dokunulunca      sanal 1073744076 KB, fiziksel     1272 KB
```

- 1 GB sanal alan neredeyse hiç fiziksel bellek tutmuyor.
- `memset` ile dokunulan 100 MB kadar fiziksel bellek arttı.
- `MADV_DONTNEED`, sayfaları çekirdeğe geri veriyor: eşleme duruyor, ama sonraki okuma yeni bir **sıfır** sayfa getiriyor.
- `PROT_NONE` ile 1 TB rezervasyon: adres alanı ayrılıyor, ama erişilemiyor; `mprotect` ile parça parça açılıyor (son satırda tek sayfaya dokunduk, 4 KB fark sayaçta görünmeyecek kadar küçük).

Son kalıp önemli. **JVM heap'i, Go çalışma zamanı ve tarayıcı motorları** dev bir adres aralığını `PROT_NONE` ile rezerve ediyor, gerekince büyütüyor. Böylece nesneler hiç taşınmıyor; "büyük bir dizim var ama fiziksel bellek kullandığım kadar" sağlanıyor. Bu, Ders 4.24'teki `realloc`'un kopyalama sorununa zarif bir alternatif ve Ders 8.21'deki arena fikrinin büyüyebilen hali.

:::note[Overcommit]
Linux, varsayılan olarak fizikselden fazla anonim bellek vermeye izin veriyor (overcommit). `malloc` başarılı dönse bile dokunulduğunda bellek olmayabilir; o zaman çekirdeğin **OOM killer**'ı bir süreci `SIGKILL` ile öldürür. Ders 10.6'daki 137 çıkış kodu çoğunlukla bu.
:::

---

## 4. Kendi malloc'umuzu mmap ile beslemek

Ders 4.29'da ilk-yeten serbest listesiyle bir allocator yazmıştık; bellek kaynağı 4096 baytlık sabit bir diziydi. Şimdi kaynağı gerçek hale getiriyoruz: belleği çekirdekten `mmap` ile istiyoruz.

Tasarım (glibc'nin de uyguladığı iki yol):

- **Küçük bloklar** (< 128 KB): 1 MB'lik parçalardan, serbest listeyle. `mmap` pahalı, her ayırmada çağrılamaz.
- **Büyük bloklar** (≥ 128 KB): kendi eşlemesi; `free` edildiğinde `munmap` ile **gerçekten** çekirdeğe döner.

```c
#ifndef MM_H
#define MM_H
#include <stddef.h>
typedef struct { long mmap_cagri, munmap_cagri; } MmIstatistik;
extern MmIstatistik mm_ist;
void *mm_malloc(size_t n);
void  mm_free(void *p);
#endif
```

```c
/* mm: mmap ile beslenen ilk-yeten allocator (Ders 4.29'un buyumesi) */
#include "mm.h"
#include <stdint.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define HIZA    16
#define PARCA   (1UL << 20)              /* her seferinde 1 MB iste */
#define ESIK    (128UL * 1024)           /* bundan buyukleri dogrudan mmap */

typedef struct Blok {
    size_t boy;                          /* veri kisminin boyutu */
    struct Blok *sonraki, *onceki;       /* butun bloklarin listesi */
    int bos, buyuk;
} Blok;

#define BASLIK ((sizeof(Blok) + HIZA - 1) & ~(size_t)(HIZA - 1))
static Blok *bas, *son;
MmIstatistik mm_ist;

static size_t hizala(size_t n, size_t a) { return (n + a - 1) & ~(a - 1); }
static char *veri(Blok *b) { return (char *)b + BASLIK; }
static int komsu(const Blok *a, const Blok *b) { return (const char *)a + BASLIK + a->boy == (const char *)b; }

static void *iste(size_t n) {
    void *p = mmap(NULL, n, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) return NULL;
    mm_ist.mmap_cagri++;
    return p;
}

static Blok *parca_ekle(void) {
    Blok *b = iste(PARCA);
    if (!b) return NULL;
    b->boy = PARCA - BASLIK; b->bos = 1; b->buyuk = 0; b->sonraki = NULL; b->onceki = son;
    if (son) son->sonraki = b; else bas = b;
    son = b;
    return b;
}

static void bol(Blok *b, size_t n) {
    if (b->boy < n + BASLIK + HIZA) return;     /* kalan parca ise yaramaz */
    Blok *y = (Blok *)(veri(b) + n);
    y->boy = b->boy - n - BASLIK; y->bos = 1; y->buyuk = 0;
    y->sonraki = b->sonraki; y->onceki = b;
    if (y->sonraki) y->sonraki->onceki = y; else son = y;
    b->sonraki = y; b->boy = n;
}

static void birlestir(Blok *a) {                /* a ile hemen arkasindaki bos blok */
    Blok *b = a->sonraki;
    a->boy += BASLIK + b->boy;
    a->sonraki = b->sonraki;
    if (a->sonraki) a->sonraki->onceki = a; else son = a;
}

void *mm_malloc(size_t n) {
    if (n == 0) n = 1;
    n = hizala(n, HIZA);
    if (n >= ESIK) {                            /* buyuk blok: kendi eslemesi */
        size_t top = hizala(n + BASLIK, (size_t)sysconf(_SC_PAGESIZE));
        Blok *b = iste(top);
        if (!b) return NULL;
        b->boy = top - BASLIK; b->buyuk = 1; b->bos = 0;
        return veri(b);
    }
    for (int deneme = 0; deneme < 2; deneme++) {
        for (Blok *b = bas; b; b = b->sonraki)
            if (b->bos && b->boy >= n) { bol(b, n); b->bos = 0; return veri(b); }
        if (!parca_ekle()) return NULL;
    }
    return NULL;
}

void mm_free(void *p) {
    if (!p) return;
    Blok *b = (Blok *)((char *)p - BASLIK);
    if (b->buyuk) { munmap(b, b->boy + BASLIK); mm_ist.munmap_cagri++; return; }
    b->bos = 1;
    if (b->sonraki && b->sonraki->bos && komsu(b, b->sonraki)) birlestir(b);
    if (b->onceki && b->onceki->bos && komsu(b->onceki, b)) birlestir(b->onceki);
}
```

Dikkat edilecek nokta, `komsu` kontrolü: liste bütün parçaların bloklarını sırayla tutuyor, ama iki **farklı** `mmap` parçası bellekte bitişik olmayabilir. Listede ardışık olan iki bloğu birleştirmeden önce gerçekten adresçe bitişik olduklarını doğrulamak gerekiyor. Unutulursa aradaki eşlenmemiş bölgeyi blok sanıp `SIGSEGV` alırız.

Stres testi: rastgele ayır-bırak, her bloğu belirli bir bayt deseniyle doldur, serbest bırakmadan önce desenin bozulmadığını kontrol et:

```c
/* mm stres testi: rastgele ayir/birak, icerik bozulmamali */
#include "mm.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
enum { N = 2000, TUR = 400000 };
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static uint32_t rs = 12345;
static uint32_t rnd(void) { rs ^= rs << 13; rs ^= rs >> 17; rs ^= rs << 5; return rs; }
static size_t boy_sec(void) {
    uint32_t r = rnd() % 1000;
    return r < 900 ? rnd() % 256 + 1 : r < 995 ? rnd() % 8192 + 1 : rnd() % (512 * 1024) + 130 * 1024;
}
int main(void) {
    static unsigned char *p[N]; static size_t b[N]; static unsigned char d[N];
    double t0 = simdi();
    for (long t = 0; t < TUR; t++) {
        int i = (int)(rnd() % N);
        if (p[i]) {
            for (size_t k = 0; k < b[i]; k += 97) if (p[i][k] != d[i]) { printf("BOZULMA tur %ld\n", t); return 1; }
            mm_free(p[i]); p[i] = NULL;
        } else {
            b[i] = boy_sec(); p[i] = mm_malloc(b[i]); d[i] = (unsigned char)rnd();
            if ((uintptr_t)p[i] % 16) { printf("hizasiz\n"); return 1; }
            memset(p[i], d[i], b[i]);
        }
    }
    for (int i = 0; i < N; i++) if (p[i]) mm_free(p[i]);
    printf("mm: %d tur tamam, %.0f ms; mmap %ld, munmap %ld\n", TUR, (simdi() - t0) * 1e3, mm_ist.mmap_cagri, mm_ist.munmap_cagri);
    rs = 12345; memset(p, 0, sizeof p); t0 = simdi();
    for (long t = 0; t < TUR; t++) {
        int i = (int)(rnd() % N);
        if (p[i]) {
            for (size_t k = 0; k < b[i]; k += 97) if (p[i][k] != d[i]) { printf("BOZULMA\n"); return 1; }
            free(p[i]); p[i] = NULL;
        }
        else { b[i] = boy_sec(); p[i] = malloc(b[i]); d[i] = (unsigned char)rnd(); memset(p[i], d[i], b[i]); }
    }
    printf("glibc: %.0f ms\n", (simdi() - t0) * 1e3);
    return 0;
}
```

```
$ cc -O2 -Wall -Wextra mm.c mm_test.c -o mm_t && ./mm_t
mm: 400000 tur tamam, 240 ms; mmap 1016, munmap 1015
glibc: 32 ms
```

Doğru çalışıyor (400 000 turda bozulma ya da hizasızlık yok; `mmap` sayısının 1016 olması tek 1 MB parça ve 1015 büyük blok: serbest kalan alan hep yetti). Ama aynı iş yüküyle glibc'den **7.5 kat yavaş**. Nedeni belli: `mm_malloc` listeyi baştan tarıyor, $O(\text{blok sayısı})$; serbest blok bulmak için dolu blokları da geziyor. glibc'de boyut sınıfları (bin'ler) ve iş parçacığı önbelleği (tcache) var. Ders 4.29'daki tartışma burada ölçülmüş oldu; Alıştırma 3 bu farkı kapatmaya başlıyor.

---

## Alıştırmalar

**1** – `grep "b.txt\|heap\|stack" /proc/self/maps` benzeri bir çıktı için `say.c`'de `mmap`'ten sonra `/proc/self/maps`'i yazdır. Eşlenen dosyanın satırını bul; sütunları (adres aralığı, izinler, konum, aygıt, inode, yol) açıkla.

**2** – Boş bir dosyayı `mmap` ile eşlemeyi dene; ne oluyor? Dosya 100 bayt ama 4096 bayt eşlediysen 200. bayta erişince ne olur? 5000. bayta erişince?

**3** – `mm_malloc`'u hızlandır: tüm bloklar yerine yalnızca **boş** blokların ayrı bir çift bağlı listesini tut. Serbest blokların sayısı doluların çok altındaysa ne kazanırsın? Hangi $O$ değişti?

**4** – Yığın taşmasını yakalamak için bir **koruma sayfası** (guard page) yaz: `mmap` ile 16 KB al, en alttaki sayfayı `mprotect(..., PROT_NONE)` yap ve bu alanı özel bir fonksiyonun yığını gibi kullan (ya da doğrudan `alt - 1` adresine yaz). `pthread`'lerin (Ders 10.9) yığınlarında aynı mekanizma var mı?

**5** – İki süreç `MAP_SHARED|MAP_ANONYMOUS` bir `int` üzerinde 1 milyon kez `x++` yapıyor. Sonuç 2 milyon olur mu? Neden? (Ders 10.10 ve 10.12'nin önsözü.)

<details>
<summary>Cevaplar</summary>

**1** – Örnek satır: `ffff8a000000-ffff9a100000 r--p 00000000 fe:01 12345 /tmp/w/b.txt`. Sütunlar: sanal adres aralığı; izinler (`r` okuma, `-` yazma yok, `-` çalıştırma yok, `p` private/COW, `s` paylaşımlı); dosyadaki konum; aygıt (major:minor); inode numarası; yol. Anonim bölgelerde son iki sütun boş ya da `[heap]`, `[stack]`, `[vdso]`.

**2** – Boş dosya: `mmap` `EINVAL` ile başarısız olur (uzunluk 0). 100 baytlık dosya, 4096 bayt eşleme: ilk sayfa bellekte; 200. bayt **geçerli** ve 0 okunur, çünkü eşleme sayfa katlarında ve sayfanın dosya dışı kalan kısmı sıfırlanır (yazarsan dosyaya yansımaz). 5000. bayt ikinci sayfada ve o sayfanın dosyada karşılığı yok: `SIGBUS`. Dosya sonunun ötesi her zaman bu: `SIGSEGV` değil `SIGBUS`, çünkü adres eşlenmiş ama arkasında veri yok.

**3** – Bloğa `bos_sonraki` / `bos_onceki` pointer'ları (ya da yalnız boşken veri alanına gömülü, Ders 4.29'daki gibi) ekle. `mm_malloc` artık yalnız boş listeyi tarar: $O(\text{boş blok sayısı})$. Dolu blok sayısından bağımsız. Daha ileri: boyut sınıfları (segregated fit) ile $O(1)$'e yakın; glibc'nin yolu. Boş blok bir kez kaldırılıp eklenirken `free`'de komşularla birleştirme hâlâ $O(1)$, çünkü blok başlıklarında komşu bilgisi var.

**4** – Kurulum: `char *p = mmap(NULL, 16384, PROT_READ|PROT_WRITE, ...); mprotect(p, 4096, PROT_NONE);`. `p + 4096` ile `p + 16384` arası kullanılabilir; `p + 4095`'e yazmak `SIGSEGV` üretir (Ders 10.6). Evet: `pthread_create` her yeni iş parçacığı yığınının altına bir koruma sayfası koyuyor (`pthread_attr_setguardsize`, varsayılan 1 sayfa). Ana yığın ise çekirdeğin otomatik büyütme mekanizmasına tabi.

**5** – Olmaz. `x++` tek makine komutu gibi görünse de oku–artır–yaz adımlarından oluşuyor (arm64'te açıkça üç komut: `ldr`, `add`, `str`) ve iki süreç bu adımları araya sokarak birbirinin güncellemesini ezebilir. Sonuç 1 ile 2 milyon arasında bir değer olur. Çözüm: Ders 10.10'da kilit, Ders 10.12'de atomik `fetch_add`. Paylaşılan bellek, senkronizasyon getirmiyor; sadece aynı baytlara erişim veriyor.

</details>

---

## Kaynaklar

- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 49–50: bellek eşlemeleri, `mprotect`, `madvise`.
- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 13–14, 18–22: adres alanı, bellek API'si, sayfalama.
- Paul Wilson ve ark., "Dynamic Storage Allocation: A Survey and Critical Review", 1995: allocator tasarımının klasik incelemesi.
- Doug Lea, "A Memory Allocator" (dlmalloc notları): glibc'nin ptmalloc'unun atası; boyut sınıfları ve büyük bloklar için `mmap` eşiği.
- Andrew Crotty, Viktor Leis ve Andrew Pavlo, "Are You Sure You Want to Use MMAP in Your Database Management System?", *CIDR 2022*: `mmap`'in veritabanlarındaki sınırları.
- `man 2 mmap`, `man 2 madvise`, `man 5 proc`.

**Sıradaki ders:** JIT için çalıştırılabilir bellek. `mmap` + `PROT_EXEC` ile çalışma zamanında makine kodu üretip çağırmak.
