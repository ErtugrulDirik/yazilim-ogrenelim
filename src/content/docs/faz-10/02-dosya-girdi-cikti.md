---
title: "10.2 Dosya G/Ç"
description: "Unix'in dört temel çağrısı open, read, write, close ve dosya tanımlayıcısı; kısmi okuma ve yazma, EINTR ve tam_yaz döngüsü; read'in 0 döndürmesi ve dosya sonu; tampon boyutunun etkisi (16 MB'de 1 baytlık tamponla 33.5 milyon çağrı ve 7.5 s, 64 KB ile 7 ms); çekirdeğin üç katmanlı yapısı: dosya tanımlayıcı tablosu, açık dosya kaydı ve inode; dup ile paylaşılan konum, en küçük boş numara kuralı; lseek ve seyrek dosyalar; O_APPEND'in neden atomik olduğu ve lseek + write ile veri kaybı deneyi."
---

Ders 10.1'de `strace` çıktısındaki en sık çağrılar `openat`, `read`, `write`, `close`'du. Unix'in en büyük fikri bu dört çağrının **her şey** için çalışması: diskteki dosya, terminal, boru, soket, `/dev/null`. Bu ders o arayüzü ve arkasındaki çekirdek yapısını anlatıyor. Bir derleyici için bu doğrudan iş: kaynak dosyasını okumak, nesne dosyasını yazmak, hata mesajını stderr'e basmak.

---

## 1. Dört çağrı

```c
#include <fcntl.h>
#include <unistd.h>

int     open(const char *yol, int bayraklar, ... /* mode_t izinler */);
ssize_t read(int fd, void *tampon, size_t n);
ssize_t write(int fd, const void *tampon, size_t n);
int     close(int fd);
```

`open` bir **dosya tanımlayıcısı** (file descriptor, fd) döndürüyor: küçük bir tamsayı. Bundan sonra dosyadan yolla değil, bu numarayla söz ediliyor. Her süreç üç açık tanımlayıcıyla başlıyor (`STDIN_FILENO` 0, `STDOUT_FILENO` 1, `STDERR_FILENO` 2; Ders 10.1'deki `strace`'te ilk `open` bu yüzden 3 döndürmüştü).

Bayraklar:

| Bayrak | Anlam |
| --- | --- |
| `O_RDONLY`, `O_WRONLY`, `O_RDWR` | Erişim kipi (tam olarak biri) |
| `O_CREAT` | Yoksa oluştur (izinler üçüncü argüman) |
| `O_TRUNC` | Varsa boyutunu 0 yap |
| `O_APPEND` | Her yazma dosyanın sonuna |
| `O_EXCL` | `O_CREAT` ile: dosya zaten varsa hata (kilit dosyaları için) |
| `O_CLOEXEC` | `exec` sırasında otomatik kapat (Ders 10.4) |

Üçüncü argüman yeni dosyanın izinleri (`0644`: sahibi okur-yazar, diğerleri okur; Ders 10.15). `umask`'taki bitler bundan çıkarılır. Sekizlik yazılması şart: `644` yazmak tamamen başka bir izin demek (Ders 3.10).

Bütün bu çağrılar hatada `-1` döndürür ve `errno`'yu ayarlar; `perror` bunu okunur hale getirir. Kural basit: **her dönüş değerini kontrol et.**

### read ve write'ın sözleşmesi

`read(fd, buf, n)` **en fazla** $n$ bayt okur ve kaç bayt okuduğunu döndürür:

- `> 0`: okunan bayt sayısı. **$n$'den az olabilir**: dosyada o kadar kalmamıştır ya da kaynak bir terminal, boru veya sokettir ve o an elde olan kadarını veriyordur.
- `0`: **dosya sonu**. Ayrı bir "EOF karakteri" yok; dosya sonu bu dönüş değerinin kendisi.
- `-1`: hata. `errno == EINTR` ise çağrı bir sinyalle kesilmiş demektir (Ders 10.6) ve yeniden denemek gerekir.

`write` de **kısmi** yazabilir: disk dolunca, boru tamponu dolunca, soketlerde. Normal dosyalarda nadir, ama "nadir" doğru kod için yeterli değil. Bu yüzden her ciddi programda şu döngü var:

```c
/* write butun baytlari yazmayabilir: kalan kismi tekrar dene */
static int tam_yaz(int fd, const char *p, size_t n) {
    while (n > 0) {
        ssize_t w = write(fd, p, n);
        if (w < 0) { if (errno == EINTR) continue; return -1; }
        p += w; n -= (size_t)w;
    }
    return 0;
}
```

---

## 2. cp'yi sıfırdan yazmak

```c
/* kopya: kaynak dosyayi hedefe, verilen tampon boyutuyla read/write kullanarak kopyalar */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

/* ... tam_yaz yukaridaki gibi ... */

int main(int argc, char **argv) {
    if (argc != 4) { fprintf(stderr, "kullanim: %s kaynak hedef tampon_boyutu\n", argv[0]); return 2; }
    size_t boy = strtoul(argv[3], NULL, 10);
    int g = open(argv[1], O_RDONLY);
    if (g < 0) { perror(argv[1]); return 1; }
    int c = open(argv[2], O_WRONLY | O_CREAT | O_TRUNC, 0644);
    if (c < 0) { perror(argv[2]); return 1; }
    char *tampon = malloc(boy);
    long cagri = 0;
    for (;;) {
        ssize_t r = read(g, tampon, boy); cagri++;
        if (r == 0) break;                          /* dosya sonu */
        if (r < 0) { if (errno == EINTR) continue; perror("read"); return 1; }
        if (tam_yaz(c, tampon, (size_t)r) < 0) { perror("write"); return 1; }
        cagri++;
    }
    if (close(g) < 0 || close(c) < 0) { perror("close"); return 1; }
    fprintf(stderr, "tampon %6zu bayt: %ld cagri\n", boy, cagri);
    free(tampon);
    return 0;
}
```

`close`'un dönüş değerine bile bakıyoruz: bazı dosya sistemlerinde (NFS gibi) yazma hatası ancak `close` anında bildirilir. Dosyayı açamayınca da doğru mesaj çıkıyor:

```
$ ./kopya yok.txt x 10
yok.txt: No such file or directory
```

Şimdi 16 MB'lık bir dosyayı farklı tampon boyutlarıyla kopyalayalım:

```
$ head -c 16777216 /dev/urandom > girdi.bin
$ for b in 1 16 256 4096 65536 1048576; do time ./kopya girdi.bin cikti.bin $b; done
tampon      1 bayt: 33554433 cagri
  7.555 s gercek, 1.287 s kullanici, 6.268 s sistem
tampon     16 bayt: 2097153 cagri
  0.483 s gercek, 0.085 s kullanici, 0.397 s sistem
tampon    256 bayt: 131073 cagri
  0.037 s gercek, 0.005 s kullanici, 0.029 s sistem
tampon   4096 bayt: 8193 cagri
  0.009 s gercek, 0.000 s kullanici, 0.007 s sistem
tampon  65536 bayt: 513 cagri
  0.007 s gercek, 0.000 s kullanici, 0.006 s sistem
tampon 1048576 bayt: 33 cagri
  0.007 s gercek, 0.000 s kullanici, 0.006 s sistem
```

Aynı iş, aynı veri: 1 baytlık tamponla 7.5 saniye, 64 KB'lık tamponla 7 milisaniye, **1000 kat** fark. Tablo iki rejim gösteriyor:

- Küçük tamponlarda süre **çağrı sayısıyla orantılı**: tamponu 16 kat büyütmek süreyi yaklaşık 16 kat azaltıyor. Çağrı başına ~225 ns; maliyetin neredeyse tamamı sistem zamanı. Bayt kopyalamak değil, çekirdeğe girip çıkmak pahalı (Ders 10.1).
- Büyük tamponlarda süre **sabitleniyor**: artık çağrı maliyeti önemsiz, kalan süre çekirdeğin 16 MB'yi gerçekten kopyalamasının maliyeti (saniyede ~2.4 GB). 4 KB'den sonrası neredeyse kazanç getirmiyor; `cat`'in 128 KB'lık tamponu (Ders 10.1'in Alıştırma 1'i) bu yüzden yeterince büyük.

Ama bir program veriyi her zaman büyük bloklar halinde üretmez: derleyici satır satır, bayt bayt çıktı üretir. Küçük yazmaları büyük bloklara **toplayan** katman Ders 10.3'ün konusu.

---

## 3. Bir dosya tanımlayıcısının arkasında ne var

Bir fd sadece bir sayı; arkasında çekirdekte üç katman var:

```
süreç A                     sistem geneli                 sistem geneli
fd tablosu                  açık dosya tablosu            inode tablosu
┌───┬──────┐               ┌─────────────────────┐       ┌──────────────┐
│ 3 │  ●───┼──────────┬──▶ │ konum: 3            │       │ boyut, izin, │
│ 4 │  ●───┼─────┐    │    │ bayraklar: O_RDONLY │──┬──▶ │ veri blokları│
│ 5 │  ●───┼─────│────┘    └─────────────────────┘  │    │ (veri.txt)   │
└───┴──────┘     │         ┌─────────────────────┐  │    └──────────────┘
                 └───────▶ │ konum: 0            │──┘
                           │ bayraklar: O_RDONLY │
                           └─────────────────────┘
```

1. **Dosya tanımlayıcı tablosu** (süreç başına): numara → açık dosya kaydı.
2. **Açık dosya kaydı** (open file description): **dosyadaki konum** (offset), durum bayrakları, inode'a pointer. Her `open` yeni bir kayıt oluşturuyor.
3. **inode** (Ders 10.15): dosyanın kendisi: boyut, izinler, verinin yeri.

Kritik nokta: **konum, fd'de değil açık dosya kaydında**. `dup(fd)` aynı kayda işaret eden yeni bir numara döndürüyor, yani iki numara konumu **paylaşıyor**. İki ayrı `open` ise iki ayrı kayıt, iki ayrı konum:

```c
/* Dosya tanimlayicilari: en kucuk bos numara, dup, iki ayri open ve paylasilan konum */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void goster(const char *ad, int fd) {
    char yol[64], hedef[256];
    snprintf(yol, sizeof yol, "/proc/self/fd/%d", fd);
    ssize_t n = readlink(yol, hedef, sizeof hedef - 1);
    hedef[n < 0 ? 0 : n] = 0;
    printf("%-10s fd=%d -> %-22s konum=%ld\n", ad, fd, hedef, (long)lseek(fd, 0, SEEK_CUR));
}

int main(void) {
    int f = open("veri.txt", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    write(f, "0123456789", 10);
    close(f);

    int a = open("veri.txt", O_RDONLY);      /* 3: en kucuk bos numara */
    int b = open("veri.txt", O_RDONLY);      /* 4: ayri bir acik dosya kaydi */
    int c = dup(a);                           /* 5: a ile AYNI kaydi gosterir */
    char x[4] = { 0 };
    read(a, x, 3);
    printf("a'dan okunan: \"%s\"\n", x);
    goster("a", a); goster("b", b); goster("c=dup(a)", c);

    read(c, x, 3);
    printf("c'den okunan: \"%s\"  (a'nin kaldigi yerden)\n", x);
    read(b, x, 3);
    printf("b'den okunan: \"%s\"  (kendi konumundan)\n", x);

    close(0);                                 /* stdin'i kapat */
    int d = open("veri.txt", O_RDONLY);
    printf("stdin kapandiktan sonra open -> %d\n", d);

    int e = open("yok/boyle/bir/dosya", O_RDONLY);
    perror("yok/boyle/bir/dosya");
    printf("open donusu: %d\n", e);
    return 0;
}
```

```
$ ./fdtablo
yok/boyle/bir/dosya: No such file or directory
a'dan okunan: "012"
a          fd=3 -> /tmp/w/veri.txt        konum=3
b          fd=4 -> /tmp/w/veri.txt        konum=0
c=dup(a)   fd=5 -> /tmp/w/veri.txt        konum=3
c'den okunan: "345"  (a'nin kaldigi yerden)
b'den okunan: "012"  (kendi konumundan)
stdin kapandiktan sonra open -> 0
open donusu: -1
```

(`perror`'ın satırı en üstte, çünkü stderr'e yazıyor ve `printf` çıktısı burada boruya gidip tamponda bekliyor; Ders 10.3.)

İki kural, Ders 10.5'teki kabuğun temeli:

- `open` ve `dup` **en küçük boş numarayı** döndürür. Yukarıda `close(0)` sonrası `open` 0 döndürdü: artık standart girdi o dosya. Kabukların `< dosya` yönlendirmesi bunun üzerine kurulu.
- `dup2(eski, yeni)`, `yeni` numarasını kapatıp `eski`'nin kaydına yönlendirir. `> cikti.txt` yönlendirmesi kabukta tam olarak `fd = open(...); dup2(fd, 1); close(fd);`.

Programın kendisi hiçbir şey bilmiyor: 1 numaraya yazıyor, 1 numaranın arkasında ne olduğu kabuğun kararı. Unix'teki programların boru hatlarıyla birleştirilebilmesi bu tek dolaylılık katmanından geliyor.

`/proc/self/fd/N`, Ders 10.1'de söylediğimiz gibi her numara için dosyanın yolunu gösteren bir sembolik bağlantı.

---

## 4. lseek ve seyrek dosyalar

`lseek(fd, uzaklik, nereden)` konumu değiştirir (`SEEK_SET`, `SEEK_CUR`, `SEEK_END`) ve yeni konumu döndürür; `lseek(fd, 0, SEEK_CUR)` "şu an neredeyim", `lseek(fd, 0, SEEK_END)` "dosya ne kadar büyük" demenin kısa yolu. Boru ve terminalde çalışmaz (`ESPIPE`): akışlarda geri dönülecek bir yer yok. `pread`/`pwrite` ise konumu değiştirmeden belirtilen yerden okuyup yazar.

Dosya sonunun **ötesine** atlayıp yazmak serbest:

```c
/* Dosya sonunun otesine lseek: seyrek (sparse) dosya */
#include <fcntl.h>
#include <stdio.h>
#include <sys/stat.h>
#include <unistd.h>
int main(void) {
    int fd = open("seyrek.bin", O_WRONLY | O_CREAT | O_TRUNC, 0644);
    write(fd, "bas", 3);
    lseek(fd, 1L << 30, SEEK_SET);          /* 1 GB ileri atla */
    write(fd, "son", 3);
    close(fd);
    struct stat s; stat("seyrek.bin", &s);
    printf("boyut: %lld bayt, diskte: %lld bayt\n", (long long)s.st_size, (long long)s.st_blocks * 512);
    fd = open("seyrek.bin", O_RDONLY);
    char b[4] = { 0 };
    pread(fd, b, 3, 1000);
    printf("1000. bayttaki 3 bayt: %02x %02x %02x\n", b[0], b[1], b[2]);
    return 0;
}
```

```
$ ./delik
boyut: 1073741827 bayt, diskte: 8192 bayt
1000. bayttaki 3 bayt: 00 00 00
$ ls -ls seyrek.bin
8 -rw-r--r-- 1 root root 1073741827 Nov  8 11:24 seyrek.bin
```

Boyutu 1 GB olan dosya diskte 8 KB yer tutuyor: aradaki hiç yazılmamış "delik" için blok ayrılmıyor, okununca sıfır veriliyor (`calloc`'un sıfır sayfa hilesinin dosya karşılığı; Ders 7.27). Sanal makine disk imajları ve core dump'lar (Ders 10.19) bundan yararlanır.

---

## 5. Atomiklik: O_APPEND neden var

Log dosyasına iki süreç aynı anda ekleme yapıyor. Doğal görünen yol "sona git, sonra yaz":

```c
/* O_APPEND olmadan ve O_APPEND ile iki surecin ayni dosyaya yazmasi */
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

static void yazdir(const char *yol, int ek, char harf) {
    int fd = open(yol, O_WRONLY | O_CREAT | ek, 0644);
    char satir[17]; memset(satir, harf, 15); satir[15] = '\n'; satir[16] = 0;
    for (int i = 0; i < 2000; i++) {
        if (!ek) lseek(fd, 0, SEEK_END);       /* "sona git, sonra yaz": iki ayri adim */
        write(fd, satir, 16);
    }
    close(fd);
}

static void dene(const char *yol, int ek) {
    unlink(yol);
    if (fork() == 0) { yazdir(yol, ek, 'A'); _exit(0); }
    if (fork() == 0) { yazdir(yol, ek, 'B'); _exit(0); }
    wait(NULL); wait(NULL);
    int fd = open(yol, O_RDONLY);
    off_t boy = lseek(fd, 0, SEEK_END);
    printf("%-22s dosya boyutu %6ld bayt (beklenen %d)\n", ek ? "O_APPEND ile" : "lseek + write ile", (long)boy, 2 * 2000 * 16);
    close(fd);
}

int main(void) {
    dene("ekle1.txt", 0);
    dene("ekle2.txt", O_APPEND);
    return 0;
}
```

```
$ ./ekle
lseek + write ile      dosya boyutu  49424 bayt (beklenen 64000)
O_APPEND ile           dosya boyutu  64000 bayt (beklenen 64000)
$ ./ekle
lseek + write ile      dosya boyutu  32368 bayt (beklenen 64000)
O_APPEND ile           dosya boyutu  64000 bayt (beklenen 64000)
```

İkinci çalıştırmada satırların **neredeyse yarısı kayboldu** ve sonuç her seferinde farklı. Neden: A süreci `lseek` ile konumu öğreniyor; çekirdek tam o anda B'yi çalıştırıyor, B aynı konuma yazıyor; A geri dönünce kendi (artık eski) konumuna yazıp B'nin satırını **üstüne yazıyor**. "Kontrol et, sonra yap" kalıbının klasik kusuru: iki adım arasına başkası girebiliyor. Bu ilk **yarış durumu**muz; Ders 10.10 konunun tamamı.

`O_APPEND`'de "sona git ve yaz" çekirdeğin içinde **tek bir atomik işlem**. Araya kimse giremiyor. Bunun için fazladan bir şey yazmıyoruz; doğru bayrağı seçmek yetiyor. Kural: birden fazla adımın birlikte olması gerekiyorsa, çekirdeğin bunu tek adımda yapan bir yolu var mı diye bak (`O_APPEND`, `O_CREAT|O_EXCL`, `pread`, `rename`).

---

## Alıştırmalar

**1** – Kendi `wc -c`'ni yaz: argüman olarak verilen dosyadaki bayt sayısını sadece `open`, `read`, `close` ile bulsun; dosya adı verilmezse stdin'den okusun. Bu program `lseek(fd, 0, SEEK_END)` kullansaydı `cat dosya | ./sayac` durumunda ne olurdu?

**2** – Bölüm 2'deki tablodan yola çıkarak çağrı başına maliyeti ve kopyalama hızını hesapla. 1 GB'lik dosyayı 4 KB tamponla kopyalamak yaklaşık kaç sistem çağrısı gerektirir? Süre en çok neye gider?

**3** – `read`'in kısmi dönebildiğini kendin gör: bir program yaz, stdin'den `read(0, buf, 1000)` yapıp dönen sayıyı yazdırsın (döngüde, 0 dönene kadar). Önce terminalde iki satır yazıp `Ctrl+D` ile, sonra `(echo a; sleep 1; echo b) | ./prog` ile çalıştır. `read` kaç bayt döndürüyor, neden 1000 değil?

**4** – `fd = open("x", O_WRONLY|O_CREAT, 0644); dup2(fd, 1); printf("merhaba\n");` kodunda `merhaba` nereye gider? `close(fd)` eklemek gerekir mi, eklemezsek ne olur? `dup2(fd, 1)` öncesinde `fflush(stdout)` neden iyi bir fikir?

**5** – Bir dosyanın en sonundaki $k$ satırı yazdıran `tail` yaz. Dosyanın tamamını okumadan, `lseek` ve geriye doğru bloklarla nasıl yaparsın? stdin bir boruysa bu yöntem neden çalışmaz, o zaman ne yaparsın?

<details>
<summary>Cevaplar</summary>

**1** – Döngü: `while ((r = read(fd, buf, sizeof buf)) > 0) top += r;`; `r < 0` ise `EINTR` dışında hata. Dosya adı yoksa `fd = 0`. `lseek` sürümü normal dosyada çok daha hızlı olurdu (içeriği hiç okumaz), ama boruda `lseek` `-1` / `ESPIPE` döndürür; yani program boruda bozulur. Gerçek `wc` önce `fstat` ile normal dosya mı diye bakıyor, öyleyse `st_size`'ı kullanıyor, değilse okuyor.

**2** – 1 baytlık satır: $7.555 / 33\,554\,433 \approx 225$ ns çağrı başına (bir `read` ya da `write`, küçük bir kopyalamayla birlikte). Kopyalama hızı: 16 MB / 7 ms $\approx$ 2.4 GB/s. 1 GB ve 4 KB için: $2^{30} / 2^{12} = 262\,144$ blok, her blok bir `read` bir `write`, toplam 524 288 çağrı (+1 son `read`). Çağrı maliyeti: $524\,288 \times 225$ ns $\approx 0.12$ s; kopyalama: $1 / 2.4 \approx 0.42$ s. Süre büyük ölçüde baytların kendisine gidiyor, geçişler artık baskın değil.

**3** – Terminalde `read`, **satır** bazında döner: terminal sürücüsü (kanonik mod) girdiyi satır satır teslim ediyor, yani bir satırın bayt sayısı (Enter dahil) dönüyor. `Ctrl+D` boş bir satırda dosya sonu demek, `read` 0 döndürür. Boruda ilk `read` `"a\n"` (2 bayt) döndürür, bir saniye sonra `"b\n"` (2 bayt), sonra borunun yazan tarafı kapanınca 0. `read`, verinin **geldiği kadarını** verir; 1000 bayt birikmesini beklemez. Bu yüzden soket ve boru kodu hep döngü içinde yazılır.

**4** – `merhaba`, x dosyasına gider: `dup2` 1 numarayı x'in kaydına yönlendirdi, `printf`'in `write(1, ...)`'ı oraya yazıyor. `close(fd)` temizlik için gerekir: aynı kaydı gösteren fazladan bir numara kalır, boruda bu sorun olur (okuyan taraf EOF görmez; Ders 10.5). `fflush(stdout)` önemli çünkü stdio tamponunda `dup2`'den önce kalan baytlar varsa, onlar da yeni hedefe gider; yönlendirmeden önceki çıktı yanlış yere düşer.

**5** – Dosya boyutunu `lseek(fd, 0, SEEK_END)` ile al; sondan başlayarak blok blok (`pread` ile, örneğin 4 KB) geriye oku ve `\n` say; $k+1$. satır başını bulunca oradan sona kadar yaz. Boru geri sarılamaz (`ESPIPE`), bu yüzden akış için tek yol, son $k$ satırı **dairesel tampon** içinde (Ders 8.5) tutarak baştan sona okumak: $O(\text{toplam boyut})$ zaman, $O(\text{son } k \text{ satırın boyutu})$ bellek. Gerçek `tail` tam olarak böyle iki yol izliyor.

</details>

---

## Kaynaklar

- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 4–5: dosya G/Ç, atomiklik, fd ile açık dosya ilişkisi, seyrek dosyalar.
- W. Richard Stevens ve Stephen Rago, *Advanced Programming in the UNIX Environment* (3. baskı), Bölüm 3: tampon boyutunun etkisi tablosunun klasik hali.
- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 39: dosyalar ve dizinler.
- `man 2 open`, `man 2 read`, `man 2 write`, `man 2 dup`, `man 2 lseek`.
- Dennis Ritchie ve Ken Thompson, "The UNIX Time-Sharing System", *Communications of the ACM*, 1974: tek tip dosya arayüzünün ilk anlatımı.

**Sıradaki ders:** Tamponlu G/Ç sıfırdan. `FILE*` benzeri tamponlu yazıcı yazmak, `fflush` neden var.
