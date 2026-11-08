---
title: "10.18 Performans ölçümü"
description: "Ölçmeden optimize etmemek: time'ın real, user, sys sayıları ve üç iş yükünün imzası; clock_gettime'ın saatleri, çözünürlük ve okuma maliyeti; perf stat ile task-clock, bağlam değişimi, sayfa hatası ve sanal makinede desteklenmeyen donanım sayaçları; perf record ve report ile darboğaz avı: strlen'i döngü koşuluna yazan O(n²) kod, 1806 ms'den 2 ms'ye; örnekleme profilinin nasıl çalıştığı."
---

Faz boyunca birçok şeyi ölçtük. Bu ders ölçme araçlarının kendisini anlatıyor: bir programın neden yavaş olduğunu **tahmin etmeden** bulmak. Faz 11 (performans ve SIMD) tamamen bu araçlarla çalışacak; derleyici yazarı olarak da bir optimizasyonun ne kazandırdığı ancak böyle anlaşılır.

Temel kural: **sezgiye güvenme, ölç.** Yavaşlığın nerede olduğu hakkındaki tahminler çoğu zaman yanlış çıkar.

---

## 1. time: üç sayı

`time` komutu üç süre veriyor:

- **real** (duvar saati): başlangıçtan bitişe geçen gerçek süre.
- **user**: süreç kendi kodunda çalışırken harcanan işlemci süresi.
- **sys**: çekirdek sürecin adına çalışırken harcanan işlemci süresi.

```c
/* time'in uc sayisi: real, user, sys */
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc, char **argv) {
    if (argc < 2) return 2;
    if (!strcmp(argv[1], "islem")) { volatile long s = 0; for (long i = 0; i < 1500000000L; i++) s += i; }
    else if (!strcmp(argv[1], "cagri")) { int f = open("/dev/zero", O_RDONLY); char b; for (long i = 0; i < 3000000; i++) read(f, &b, 1); }
    else if (!strcmp(argv[1], "uyku")) sleep(1);
    return 0;
}
```

```
$ time ./zaman islem
real	0m2.228s
user	0m2.227s
sys	0m0.001s
$ time ./zaman cagri
real	0m0.429s
user	0m0.121s
sys	0m0.308s
$ time ./zaman uyku
real	0m1.006s
user	0m0.001s
sys	0m0.000s
```

Üç iş yükü, üç imza, ve bu imzaları okumak ilk teşhis:

| Durum | İmza | Anlamı |
| --- | --- | --- |
| Hesaplama | real ≈ user | CPU darboğazı; algoritma ve kod |
| Çok sistem çağrısı | sys büyük | Küçük G/Ç (Ders 10.2'deki tablo); tamponla |
| Bekleme | real ≫ user + sys | Disk, ağ, kilit, `sleep`: işlemci boşta |
| Paralel | user + sys > real | Birden çok çekirdek çalışıyor |

Ders 10.2'deki "1 baytlık tampon" durumunda `sys` değerinin neredeyse bütün zamanı alması tam olarak ikinci satır.

---

## 2. Program içinden ölçmek

Bütün faz boyunca kullandığımız `clock_gettime` birkaç **saat** sunuyor:

```c
/* Saatler: cozunurluk, okuma maliyeti, duvar saati ile islemci saati */
#include <stdio.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
static double oku(clockid_t c) { struct timespec t; clock_gettime(c, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void) {
    clockid_t s[] = { CLOCK_REALTIME, CLOCK_MONOTONIC, CLOCK_PROCESS_CPUTIME_ID, CLOCK_THREAD_CPUTIME_ID };
    const char *ad[] = { "CLOCK_REALTIME", "CLOCK_MONOTONIC", "CLOCK_PROCESS_CPUTIME_ID", "CLOCK_THREAD_CPUTIME_ID" };
    for (int i = 0; i < 4; i++) {
        struct timespec r; clock_getres(s[i], &r);
        double t0 = oku(CLOCK_MONOTONIC); for (int k = 0; k < 1000000; k++) oku(s[i]); double t1 = oku(CLOCK_MONOTONIC);
        double en_kucuk = 1e9, a = oku(s[i]);
        for (int k = 0; k < 100000; k++) { double b = oku(s[i]); if (b > a && b - a < en_kucuk) en_kucuk = b - a; a = b; }
        printf("%-26s cozunurluk %3ld ns, okuma %6.1f ns, gorulen en kucuk adim %5.0f ns\n", ad[i], r.tv_nsec, (t1 - t0) / 1e6 * 1e9, en_kucuk * 1e9);
    }
    double d0 = oku(CLOCK_MONOTONIC), c0 = oku(CLOCK_PROCESS_CPUTIME_ID);
    sleep(1);
    double d1 = oku(CLOCK_MONOTONIC), c1 = oku(CLOCK_PROCESS_CPUTIME_ID);
    printf("sleep(1): duvar %.3f s, islemci %.6f s\n", d1 - d0, c1 - c0);
    d0 = oku(CLOCK_MONOTONIC); c0 = oku(CLOCK_PROCESS_CPUTIME_ID);
    while (oku(CLOCK_MONOTONIC) - d0 < 1.0) { }
    c1 = oku(CLOCK_PROCESS_CPUTIME_ID);
    printf("dongu 1s: duvar %.3f s, islemci %.3f s\n", oku(CLOCK_MONOTONIC) - d0, c1 - c0);
    return 0;
}
```

```
$ ./saatler
CLOCK_REALTIME             cozunurluk 1000000 ns, okuma   16.3 ns, gorulen en kucuk adim   238 ns
CLOCK_MONOTONIC            cozunurluk 1000000 ns, okuma   15.9 ns, gorulen en kucuk adim    41 ns
CLOCK_PROCESS_CPUTIME_ID   cozunurluk   1 ns, okuma  176.0 ns, gorulen en kucuk adim    83 ns
CLOCK_THREAD_CPUTIME_ID    cozunurluk   1 ns, okuma  169.9 ns, gorulen en kucuk adim   125 ns
sleep(1): duvar 1.005 s, islemci 0.000069 s
dongu 1s: duvar 1.000 s, islemci 1.000 s
```

- `CLOCK_REALTIME` duvar saati: sistem saati ayarlanırsa **geri gidebilir**. Süre ölçmek için kullanma.
- `CLOCK_MONOTONIC` yalnızca ileri gider: süre ölçümü için doğru saat. 16 ns'lik okuma vDSO sayesinde (Ders 10.1).
- `*_CPUTIME_ID` işlemci zamanı: bekleme süresi dahil değil, ama çekirdeğe giriyor (10 kat pahalı).
- `clock_getres`'in bu sanal makinede verdiği 1 ms, pratikte görülen adımla ilgisiz: gerçek adım 41 ns. Bir fonksiyonun beyan ettiğine değil, **ölçtüğüne** güven.

Mikrosaniye altı için kısa işleri tekrarlamak gerek: Ders 9.1'deki ölçme tuzakları (derleyicinin işi silmesi, ısınma, en iyi süreyi almak) burada da geçerli.

---

## 3. Bir darboğaz bulmak

```c
/* Darbogaz avi: bir metindeki kelimeleri sayan yavas program */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { BOY = 400000 };
static char metin[BOY + 1];
__attribute__((noinline)) static void uret(void) {
    unsigned r = 1;
    for (int i = 0; i < BOY; i++) { r = r * 1103515245 + 12345; metin[i] = (r >> 16) % 6 == 0 ? ' ' : (char)('a' + (r >> 20) % 26); }
    metin[BOY] = 0;
}
__attribute__((noinline)) static long kucult(void) {
    long d = 0;
    for (size_t i = 0; i < strlen(metin); i++) { metin[i] = (char)tolower((unsigned char)metin[i]); d++; }
    return d;
}
__attribute__((noinline)) static long say(void) {
    long k = 0; int ic = 0;
    for (char *p = metin; *p; p++) { if (*p == ' ') ic = 0; else if (!ic) { ic = 1; k++; } }
    return k;
}
int main(void) { uret(); long d = kucult(); printf("%ld karakter, %ld kelime\n", d, say()); return 0; }
```

```
$ cc -O2 -g -fno-omit-frame-pointer yavas.c -o yavas
$ time ./yavas
400000 karakter, 55395 kelime

real	0m1.807s
user	0m1.806s
sys	0m0.000s
```

400 KB metin için 1.8 saniye şüpheli. `real ≈ user`: CPU darboğazı. Nereye gidiyor? `perf` ile bakalım.

Linux `perf` çekirdek kaynak ağacıyla gelen araçtır: `sudo apt install linux-tools-generic`. Sanal makine ve konteynerlerde üç şeye dikkat: paket `/usr/bin/perf` altında çekirdek sürümünü arayan bir sarmalayıcı kuruyor, çekirdek farklıysa aracı doğrudan `/usr/lib/linux-tools/*/perf` yolundan çağır; `/proc/sys/kernel/perf_event_paranoid` ayarı ya da konteyner izinleri erişimi kısıtlayabilir (Docker'da `--privileged`).

### perf stat

```
$ perf stat ./yavas
400000 karakter, 55395 kelime

 Performance counter stats for './yavas':

           1788.82 msec task-clock                       #    1.000 CPUs utilized
                 8      context-switches                 #    4.472 /sec
                 0      cpu-migrations                   #    0.000 /sec
               145      page-faults                      #   81.059 /sec
   <not supported>      cycles
   <not supported>      instructions
   <not supported>      branches
   <not supported>      branch-misses

       1.788974876 seconds time elapsed

       1.788927000 seconds user
       0.000000000 seconds sys
```

`task-clock`, bağlam değişimi ve sayfa hatası yazılım sayaçları: sanal makinede de çalışıyor. **Donanım sayaçları** (cycles, instructions, branch-misses, cache-misses) ise bu sanal makinede hipervizör tarafından sunulmuyor: `<not supported>`. Çıplak donanımda (ya da bunu destekleyen bir bulut örneğinde) `perf stat` çevrim başına komut (IPC) ve dal ıskası oranını gösterir; `perf stat -e cache-misses,...` Faz 11'de Ders 7.24 ve 7.26'nın ölçümünü sağlayacak. Bu makinede o rakamları üretemediğimiz için burada göstermiyoruz.

### perf record ve report

`perf record` programı periyodik olarak **örnekler**: zamanlayıcı kesmesi geldiğinde komut adresini ve (`-g` ile) çağrı yığınını kaydeder. Sık örneklenen fonksiyon, zamanın çoğunu harcayan fonksiyondur.

```
$ perf record -o p.data -e cpu-clock -F 2000 -g ./yavas
[ perf record: Woken up 1 times to write data ]
[ perf record: Captured and wrote 0.196 MB p.data (1802 samples) ]
$ perf report -i p.data --stdio --no-children --sort symbol
    99.83%  [.] __strlen_asimd
            |
            ---kucult
               main
               __libc_start_call_main
               __libc_start_main@@GLIBC_2.34
               _start
     0.06%  [.] say
     0.06%  [.] strlen@plt
     0.06%  [.] uret
```

Tek satır: zamanın **%99.83'ü** `strlen`'de, `kucult`'un içinden çağrılmış. Kodu okumaya artık gerek yok:

```c
for (size_t i = 0; i < strlen(metin); i++)
```

Döngü koşulu her turda `strlen` çağırıyor, `strlen` de her seferinde $n$ bayt tarıyor: $O(n^2)$. (Derleyici neden dışarı almadı? `metin` döngüde yazılıyor; `strlen` sonucunun değişmeyeceğini kanıtlayamıyor. Ders 4.13'te bu kalıba dikkat çekmiştik.) `-fno-omit-frame-pointer`, `-g` çağrı yığınlarının çalışması için gerekli.

Düzeltme: uzunluğu bir kez hesapla.

```
$ time ./hizli
400000 karakter, 55395 kelime

real	0m0.002s
user	0m0.002s
sys	0m0.000s
```

1806 ms → 2 ms. Tek satırla **900 kat**. Karmaşıklık değiştiği için hiçbir mikro-optimizasyon bu kadar kazandıramazdı.

### Profil okuma

- **Örnekleme profili** programı yavaşlatmıyor (kesme başına birkaç mikrosaniye), ama istatistiksel: az örnekli fonksiyonlardaki yüzde güvenilmez. 1000 Hz ile 1 saniye yaklaşık 1000 örnek; %1'lik kalem için $\pm 0.3$ puan belirsizlik. Çok kısa programlar için çoklu tekrar gerekli.
- Süre **satırla** ilişkilendirilirken, sırasız yürütme nedeniyle (Ders 7.23) örnek bir sonraki komuta kayabilir.
- `perf report` etkileşimlidir; `perf annotate` işlevin assembly'sini yüzdelerle gösterir. **Flame graph** (Brendan Gregg), çağrı yığınlarını görsel olarak özetler.
- Amdahl yasası (Ders 10.9) hangi işin önemli olduğunu söyler: programın %5'ini 10 kat hızlandırmak toplamı en fazla %4.5 azaltır. Önce en büyük satır.

---

## Alıştırmalar

**1** – `yavas.c`'yi derleyici bayrağı olmadan `-O0` ile derle ve `perf` çıktısını karşılaştır. Çağrılan `strlen` aynı olmasına rağmen neden `-O0` yine önemli ölçüde yavaş?

**2** – Ders 9.1'deki ikiye katlama yöntemiyle `yavas`'ın büyüme üstelini ölç: `BOY`'u 100k, 200k, 400k, 800k için çalıştır.

**3** – Ders 10.2'deki `kopya` programını 1 baytlık tamponla `perf record` ile çalıştır. Sembol listesinde ne görüyorsun? `-e cpu-clock` ve `sudo`'ya ne gerekiyor (çekirdek sembolleri)?

**4** – `sleep(1)` yapan bir program, `perf record` çıktısında neden neredeyse boş görünür? Hangi profil türü bu programı anlamaya yarar?

**5** – Çok iş parçacıklı bir programda `real` 1 s, `user` 3.5 s, `sys` 0.5 s. Bu size ne anlatıyor? Çekirdek sayısı 8 ise boşta kapasite ne kadar?

<details>
<summary>Cevaplar</summary>

**1** – `strlen` hâlâ baskın, ama `-O0`'da döngünün geri kalanı (`tolower` çağrısı, register yerine yığın okuma/yazma) ayrıca yavaş: `strlen` zaman içindeki ağırlığı biraz düşer. `-O0` üretim ölçümü değildir (Ders 7.15).

**2** – $T(2n) / T(n) \approx 4$, yani $b \approx 2$: $O(n^2)$. Düzeltilmiş `hizli`'da oran 2'ye yakın, $b \approx 1$. Ölçüm, profil görmeden önce de karmaşıklığı açıklıyor.

**3** – Örnekler büyük ölçüde çekirdek sembollerinde (`write`, `read`, sistem çağrısı giriş/çıkış kodu) toplanır, `kopya`'nın kendi kodu küçük bir yüzde. Çekirdek sembolleri için `perf_event_paranoid` düşük (`<= 1`) ya da root gerekir. `-e cpu-clock` donanım sayacı yoksa yazılım tabanlı örnekleme sağlar.

**4** – `perf record` işlemciyi kullanırken örnekler; uyuyan süreç örnek üretmez. Bekleme süresini anlamak için bir "off-CPU" analizi gerekir: `strace -T` (çağrı süreleri), `perf trace`, `bpftrace`, `offcputime` gibi araçlar. Ders 10.1'deki `strace` çıktıları bu yüzden yararlı.

**5** – 4 s toplam işlemci süresi 1 saniyeye sığmış: ortalama 4 çekirdek aktif. `sys / (user + sys) = %12.5`: dikkat çekici ama olağan bir sistem çağrısı payı. 8 çekirdekte kapasitenin yarısı boş; ya iş bölünmüyor ya da kilitlerde bekleniyor (Ders 10.10) ya da G/Ç var. `perf`, `pidstat -t` ile her iş parçacığını ayrı incele.

</details>

---

## Kaynaklar

- Brendan Gregg, *Systems Performance* (2. baskı), Addison-Wesley, 2020; flame graph yazıları (brendangregg.com).
- Linux çekirdeği, `tools/perf/Documentation/`: `perf stat`, `perf record`, `perf report`.
- Todd Mytkowicz ve ark., "Producing Wrong Data Without Doing Anything Obviously Wrong!", *ASPLOS 2009*: ölçüm yanlılığı.
- Emery Berger, "Performance Matters" (Coz nedensel profiler), *SOSP 2015*.
- `man 1 time`, `man 2 clock_gettime`, `man 1 perf-record`.

**Sıradaki ders:** Hata ayıklama araçları derinlemesine. LLDB betikleri, core dump analizi, `valgrind --tool=callgrind`.
