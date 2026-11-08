---
title: "10.15 Dosya sistemleri"
description: "Disk blokları üzerinde dosya soyutlaması: inode, veri blokları, dizinler; stat'ı sıfırdan yazıp okumak; sert ve sembolik bağlar, silme ile bağ sayısı; açık bir dosyanın silinmesi; dizin ağacı gezme ve du ile karşılaştırma; atomik güncelleme: O_TRUNC ile 484 binde 480 bin eksik okuma, rename ile sıfır; journal fikri ve fsync."
---

Ders 10.2'de `open`/`read`/`write` ile "dosya" dediğimiz şeyi kullandık, ama dosyanın diskte nasıl durduğunu söylemedik. Disk yalnızca numaralı bloklardan oluşan dev bir dizi; ad, dizin, boyut gibi şeylerin hepsi **dosya sistemi** dediğimiz veri yapısının ürünü. Faz 8'de veri yapılarını bellekte kurduk; bu, kalıcı depoda kurulmuş olanı. Derleyici açısından: `make`'in hangi dosyanın değiştiğini `mtime` ile anlaması, `#include` aramalarının `stat`'lerden oluşması, `ccache`'in sert bağlar kullanabilmesi hep buradan geliyor.

---

## 1. Diskteki düzen

Tipik bir Unix dosya sistemi (ext2 ailesinin basitleştirilmiş hali) diski şu bölgelere ayırır:

```
┌────────┬──────────────┬──────────────┬───────────────┬──────────────────────┐
│ süper  │ inode bit    │ veri bit     │ inode         │ veri blokları        │
│ blok   │ haritası     │ haritası     │ tablosu       │                      │
└────────┴──────────────┴──────────────┴───────────────┴──────────────────────┘
```

**inode** (index node) bir dosyanın kimlik kartı: tipi, izinleri, sahibi, boyutu, zamanları, bağ sayısı, verinin **hangi bloklarda** olduğu. inode'da **dosyanın adı yok.** İsimler dizinlerde.

Verinin yerini tutmanın klasik yolu çok seviyeli işaretçiler: 12 doğrudan blok, sonra bir dolaylı, bir çift dolaylı, bir üç dolaylı blok:

$$
\text{en büyük boyut} = (12 + k + k^2 + k^3) \cdot B, \qquad k = B / 4.
$$

$B = 4$ KB için $k = 1024$: yaklaşık 4 TB. Çoğu dosya küçük olduğundan ilk 12 işaretçi çoğu dosya için yetiyor (Ders 8.11'deki B-ağacının mantığıyla aynı "ucuz sık durum" tasarımı). ext4 ve modern sistemler, ardışık bloklar için `(başlangıç, uzunluk)` ikilileri (**extent**) kullanıyor; XFS ve btrfs de B-ağaçlarına dayanıyor.

**Dizin**, içeriği `(ad, inode numarası)` çiftlerinin listesi olan özel bir dosya. `/usr/bin/cc`'yi açmak: kök inode'unu oku, içinde `usr`'yi bul, onun inode'unu oku, `bin`'i bul, ... Her bileşen için en az bir disk erişimi. Bu yüzden çekirdek **dentry önbelleği** (dizin girişleri) ve **inode önbelleği** tutuyor.

---

## 2. stat

`stat(yol, &s)` inode'daki bilgileri verir; `lstat` sembolik bağı izlemez, `fstat` açık bir tanımlayıcı üzerinden çalışır. Ders 10.1'deki `ls -l`'nin her dosya için yaptığı çağrı bu.

```c
/* stat: inode'un soyledikleri */
#include <stdio.h>
#include <sys/stat.h>
#include <sys/sysmacros.h>
#include <time.h>
static char tur(mode_t m) {
    return S_ISREG(m) ? '-' : S_ISDIR(m) ? 'd' : S_ISLNK(m) ? 'l' : S_ISCHR(m) ? 'c' : S_ISBLK(m) ? 'b' : S_ISFIFO(m) ? 'p' : S_ISSOCK(m) ? 's' : '?';
}
int main(int argc, char **argv) {
    for (int i = 1; i < argc; i++) {
        struct stat s;
        if (lstat(argv[i], &s) < 0) { perror(argv[i]); continue; }
        char z[32]; strftime(z, sizeof z, "%Y-%m-%d %H:%M:%S", localtime(&s.st_mtime));
        char izin[10]; const char *h = "rwxrwxrwx";
        for (int b = 0; b < 9; b++) izin[b] = (s.st_mode >> (8 - b)) & 1 ? h[b] : '-';
        izin[9] = 0;
        printf("%-14s %c%s inode=%-9lu bag=%lu boyut=%-8lld blok=%-5lld aygit=%u:%u %s\n", argv[i], tur(s.st_mode), izin, (unsigned long)s.st_ino, (unsigned long)s.st_nlink, (long long)s.st_size, (long long)s.st_blocks, major(s.st_dev), minor(s.st_dev), z);
    }
    return 0;
}
```

```
$ echo icerik > a.txt; ln a.txt b.txt; ln -s a.txt c.txt; ln -s yok.txt d.txt; mkdir klasor; mkdir klasor/alt
$ ./bilgi a.txt b.txt c.txt d.txt klasor klasor/alt /dev/null /
a.txt          -rw-r--r-- inode=260437    bag=2 boyut=7        blok=8     aygit=0:64 2026-11-08 16:27:24
b.txt          -rw-r--r-- inode=260437    bag=2 boyut=7        blok=8     aygit=0:64 2026-11-08 16:27:24
c.txt          lrwxrwxrwx inode=260438    bag=1 boyut=5        blok=0     aygit=0:64 2026-11-08 16:27:24
d.txt          lrwxrwxrwx inode=260439    bag=1 boyut=7        blok=0     aygit=0:64 2026-11-08 16:27:24
klasor         drwxr-xr-x inode=260440    bag=3 boyut=4096     blok=8     aygit=0:64 2026-11-08 16:27:24
klasor/alt     drwxr-xr-x inode=260442    bag=2 boyut=4096     blok=8     aygit=0:64 2026-11-08 16:27:24
/dev/null      crw-rw-rw- inode=61        bag=1 boyut=0        blok=0     aygit=0:81 2026-11-08 16:27:24
/              drwxr-xr-x inode=260411    bag=1 boyut=4096     blok=8     aygit=0:64 2026-11-08 16:27:24
```

Bu tabloda okunacak çok şey var:

- `a.txt` ve `b.txt`'nin **inode'ları aynı**, bağ sayısı 2: tek dosya, iki isim.
- `blok=8`: `st_blocks` 512 baytlık birim. 7 baytlık dosya 4 KB bir blok tutuyor (Ders 10.2'deki seyrek dosyanın tersi: küçük dosyanın da asgari yeri var).
- `c.txt` boyutu 5: sembolik bağın içeriği hedef yolunun kendisi (`a.txt`). `blok=0`: kısa olduğu için doğrudan inode'da saklanıyor.
- `klasor` bağ sayısı 3: kendi `.`, üst dizindeki adı ve `alt/..`. Her alt dizin bir bağ ekliyor. Kök dizinde bağ sayısının 1 olması buradaki overlay dosya sisteminin bir özelliği (ext4'te tipik olarak çok daha fazla).
- `/dev/null`: tür `c` (karakter aygıtı), boyutu 0: "dosya" arayüzüyle bir sürücü.

### Bağ türleri

| | Sert bağ (`ln`) | Sembolik bağ (`ln -s`) |
| --- | --- | --- |
| Ne | Aynı inode'a yeni bir **dizin girdisi** | Yol metnini içeren ayrı bir dosya |
| Kendi inode'u | Hayır | Evet |
| Başka dosya sistemine | Hayır (inode numarası yereldir) | Evet |
| Dizinlere | Hayır (döngü riski) | Evet |
| Hedef silinince | Hayatta, bağ sayısı düşer | **Sarkan** bağ |

Silmek, Unix'te "dosyayı yok etmek" değil, bir isim silmek:

```
$ rm a.txt
$ ./bilgi b.txt
b.txt          -rw-r--r-- inode=260437    bag=1 boyut=7        blok=8     aygit=0:64 ...
$ cat c.txt
cat: c.txt: No such file or directory
$ cat b.txt
icerik
```

Bağ sayısı 1'e indi, veri duruyor. Sembolik bağ ise sarktı: isim üzerinden çözümlenir. Bloklar ancak bağ sayısı **ve** açık tanımlayıcı sayısı sıfır olunca serbest kalıyor:

```c
/* Acik bir dosyayi silmek: isim gider, inode kalir */
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>
int main(void) {
    int f = open("gecici.txt", O_RDWR | O_CREAT | O_TRUNC, 0644);
    write(f, "hala buradayim\n", 15);
    unlink("gecici.txt");
    struct stat s; fstat(f, &s);
    printf("unlink sonrasi bag sayisi: %lu, dosya var mi: %s\n", (unsigned long)s.st_nlink, access("gecici.txt", F_OK) == 0 ? "evet" : "hayir");
    char t[32] = { 0 }, y[64], h[128] = { 0 };
    pread(f, t, 15, 0);
    printf("fd'den okunan: %s", t);
    snprintf(y, sizeof y, "/proc/self/fd/%d", f);
    readlink(y, h, sizeof h - 1);
    printf("/proc/self/fd: %s\n", h);
    close(f);
    return 0;
}
```

```
$ ./silinmis
unlink sonrasi bag sayisi: 0, dosya var mi: hayir
fd'den okunan: hala buradayim
/proc/self/fd: /tmp/w/gecici.txt (deleted)
```

İki pratik sonuç. `open` + hemen `unlink`, program ölünce otomatik yok olan bir geçici dosya demek (derleyicilerin ara dosyalarında kullanışlı). Ve "diskim dolu ama dosyayı sildim" sorununun olağan sebebi: sildiğin log dosyası hâlâ bir program tarafından açık; `lsof +L1` gösterir, `/proc/PID/fd` üzerinden kurtarılabilir.

---

## 3. Dizin gezmek

```c
/* du -a'nin basit hali: dizin agacini gez, boyutlari topla */
#include <dirent.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
static long dosya, dizin, bag;
static long long toplam;
static void gez(const char *yol) {
    DIR *d = opendir(yol);
    if (!d) { perror(yol); return; }
    struct dirent *e;
    while ((e = readdir(d))) {
        if (!strcmp(e->d_name, ".") || !strcmp(e->d_name, "..")) continue;
        char y[PATH_MAX];
        if (snprintf(y, sizeof y, "%s/%s", yol, e->d_name) >= (int)sizeof y) continue;
        struct stat s;
        if (lstat(y, &s) < 0) continue;
        if (S_ISLNK(s.st_mode)) { bag++; continue; }             /* sembolik baglari izleme: dongu olabilir */
        if (S_ISDIR(s.st_mode)) { dizin++; gez(y); }
        else if (S_ISREG(s.st_mode)) { dosya++; toplam += s.st_blocks * 512; }
    }
    closedir(d);
}
int main(int argc, char **argv) {
    gez(argc > 1 ? argv[1] : ".");
    printf("%ld dosya, %ld dizin, %ld sembolik bag, %.1f MB\n", dosya, dizin, bag, toplam / 1048576.0);
    return 0;
}
```

```
$ ./gez /usr/lib
3430 dosya, 461 dizin, 222 sembolik bag, 664.7 MB
$ du -sm /usr/lib
667	/usr/lib
```

Fark, `du`'nun dizinlerin kendi bloklarını da saymasından geliyor (461 dizin × 4 KB ≈ 1.8 MB). `.` ve `..`'yı atlamak **şart** (yoksa sonsuz özyineleme); sembolik bağları izlememek de öyle (bir bağ üst dizine işaret edebilir). `d_type` alanı kullanılsaydı `lstat`'siz de tip öğrenilebilirdi; dizin başına `stat` maliyetini düşüren bir optimizasyon. Faz 15'teki derleyici sürücüsünün `#include` araması da bu kalıp.

---

## 4. Tutarlılık: atomik güncelleme

Ders 10.3'te "önce geçici dosyaya yaz, sonra `rename`" dedik. Nedenini ölçelim: bir süreç dosyayı sürekli güncelliyor, bir diğeri okuyor.

```c
/* rename ile atomik guncelleme: okuyan hic yarim dosya gormez */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
enum { BOY = 65536, TUR = 3000 };
static void yaz_yerinde(char c) { char b[BOY]; memset(b, c, BOY); int f = open("h.dat", O_WRONLY | O_CREAT | O_TRUNC, 0644); write(f, b, BOY / 2); write(f, b + BOY / 2, BOY / 2); close(f); }
static void yaz_atomik(char c) { char b[BOY]; memset(b, c, BOY); int f = open("h.tmp", O_WRONLY | O_CREAT | O_TRUNC, 0644); write(f, b, BOY); close(f); rename("h.tmp", "h.dat"); }
static void dene(const char *ad, void (*y)(char)) {
    y('a');
    pid_t p = fork();
    if (p == 0) { for (int i = 0; i < TUR * 4; i++) y(i & 1 ? 'a' : 'b'); _exit(0); }
    long kisa = 0, karisik = 0, say = 0; char b[BOY + 1]; int st; 
    while (waitpid(p, &st, WNOHANG) == 0) {
        int f = open("h.dat", O_RDONLY); if (f < 0) continue;
        ssize_t n = read(f, b, sizeof b); close(f); say++;
        if (n != BOY) { kisa++; continue; }
        for (int i = 1; i < BOY; i++) if (b[i] != b[0]) { karisik++; break; }
    }
    printf("%-22s %ld okuma: eksik boy %ld, karisik icerik %ld\n", ad, say, kisa, karisik);
}
int main(void) { dene("yerinde (O_TRUNC)", yaz_yerinde); dene("gecici + rename", yaz_atomik); return 0; }
```

```
$ ./atomik
yerinde (O_TRUNC)      484622 okuma: eksik boy 480442, karisik icerik 1
gecici + rename        31493 okuma: eksik boy 0, karisik icerik 0
```

Yerinde güncellemede okuyanların **%99**'u kırpılmış dosya gördü, biri de iki sürümün karışımını. `rename` ile sıfır: aynı dosya sistemi içinde `rename` dizin girdisini atomik olarak değiştiriyor; okuyan ya tamamen eski ya tamamen yeni inode'u alıyor. Bu dosya sistemindeki ender gerçek atomik işlemlerden biri, ve (`mv` için `strace`'in gösterdiği `renameat2`) `make`, paket yöneticileri ve editörler bunu kullanıyor.

### Elektrik kesilirse

`rename` süreçler arası atomikliği sağladı, ama **elektrik kesintisini** değil: bir `rename` birden çok disk yapısını değiştiriyor (dizin girdisi, inode bağ sayısı, bit haritaları). Yarım kalırsa dosya sistemi tutarsız kalır. Üç çağa ait çözüm:

- `fsck`: açılışta bütün yapıları tarayıp tamir et. Terabaytlarda saatler sürer.
- **Journaling** (ext4, XFS, NTFS): değişikliği önce **kayıt** defterine yaz, sonra asıl yerine. Kesinti olursa defteri yeniden oynat.
- **Copy-on-write** (btrfs, ZFS, APFS): hiçbir bloğu yerinde değiştirme; yeni sürümü başka yere yaz, kökü atomik olarak değiştir. Ders 8.22'deki kalıcı veri yapılarının diskteki hali.

Uygulamanın sorumluluğu ise tamamen ayrı: güvenli güncelleme **dosyayı `fsync`, sonra `rename`, sonra içeren dizini `fsync`** gerektiriyor. Yoksa `rename` kalıcı olsa bile yeni dosyanın içeriği henüz diskte olmayabilir.

---

## Alıştırmalar

**1** – Blok boyutu 1 KB, işaretçi 4 bayt ve inode 12 doğrudan + 1 tek + 1 çift dolaylı işaretçi içeren bir dosya sisteminde en büyük dosya boyutu nedir? 300 KB'lık dosyayı okumak için kaç blok okuma gerekir?

**2** – Kendi `ls -li`'ni yaz: ad, inode, tür, izinler, boyut. `bilgi.c`'yi `opendir` ile birleştir, adları sırala (Ders 9.5 ya da `qsort`).

**3** – `gez.c`'nin sert bağları iki kez saymasını engelle: `(st_dev, st_ino)` çiftlerini bir hash kümesinde (Ders 8.14) tut. `du` ne yapıyor?

**4** – Bir programın güvenli "kaydet" fonksiyonunu yaz: `kaydet(yol, veri, n)`. Hangi çağrıları hangi sırada yapmalısın? Geçici dosyayı neden hedef ile aynı dizinde oluşturmalısın?

**5** – `make`, hedefin yeniden derlenip derlenmeyeceğini `mtime`'a göre belirler. Bu yöntemin hangi durumlarda yanılabileceğini yaz. Faz 16'da inşa edeceğimiz derleyici bu bilgiyi nasıl kullanabilir?

<details>
<summary>Cevaplar</summary>

**1** – $k = 1024 / 4 = 256$. En büyük: $(12 + 256 + 256^2) \cdot 1$ KB $= 65\,804$ KB ≈ 64 MB. 300 KB: 12 doğrudan blok (12 okuma), kalan 288 KB. Tek dolaylı 256 KB karşılar: 1 işaretçi bloğu + 256 veri = 257 okuma. Kalan 32 KB için çift dolaylı: 1 + 1 + 32 = 34. Toplam $12 + 257 + 34 = 303$ blok okuma (inode hariç).

**2** – Girişleri bir diziye al (`malloc` ile `ad` ve `struct stat`), `qsort(... strcmp ...)`, yaz. `lstat` için yol birleştirme (`snprintf`) gerekli ya da `dirfd` + `fstatat`; ikincisi yol sınırına takılmaz ve daha hızlı.

**3** – `(st_dev, st_ino)` anahtarıyla küme tut; `st_nlink > 1` olan dosyalar için kontrol et (bağ sayısı 1 olanlar zaten tektir). `du` tam olarak bunu yapıyor: bir sert bağı bir kez sayıyor.

**4** – (1) `yol.tmp.PID` adıyla `open(O_WRONLY|O_CREAT|O_EXCL)`, (2) `write` (döngüde), (3) `fsync(fd)`, (4) `close`, (5) `rename(tmp, yol)`, (6) içeren dizini `open(O_RDONLY|O_DIRECTORY)`, `fsync`, `close`. Aynı dizinde olmalı, çünkü `rename` farklı dosya sistemleri arasında çalışmaz (`EXDEV`) ve `/tmp` çoğu zaman ayrı bir dosya sistemi.

**5** – Yanılma durumları: saat geri kayarsa, `git checkout` eski bir dosyayı geri getirirse, zaman damgası çözünürlüğü kaba ise ve aynı saniye içinde iki değişiklik olursa, başlık dosyaları ya da derleyicinin kendisi değiştiğinde (bağımlılık yoksa), derleme seçeneği değişse bile dosya aynıysa. Ninja ve Bazel gibi araçlar içerik özeti (hash) ve komut satırını da karşılaştırır; bir derleyicinin "artımlı" kısmı benzer şekilde içerik özetlerine güvenmeli.

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 39–43: dosyalar, dizinler, dosya sistemi uygulaması, tutarlılık ve günlükleme.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 14–15, 18: dosya sistemleri, öznitelikler, dizinler ve bağlar.
- Marshall McKusick ve ark., "A Fast File System for UNIX", *ACM TOCS*, 1984.
- Thanumalayan Sankaranarayana Pillai ve ark., "All File Systems Are Not Created Equal", *OSDI 2014*: `fsync` ve `rename` tuzakları.
- `man 2 stat`, `man 2 rename`, `man 3 opendir`, `man 7 inode`.

**Sıradaki ders:** Dinamik kütüphaneler. `.so` oluşturma, `dlopen`/`dlsym` ile eklenti sistemi, PIC.
