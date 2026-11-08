---
title: "10.14 Zamanlayıcı"
description: "Çekirdeğin kime işlemci vereceği sorusu: dönüş süresi ve yanıt süresi; FCFS, SJF ve Round-Robin simülatörü ve Gantt çizimleri; kuantum seçiminde ödünleşim; bağlam değiştirme maliyeti: boru ping-pong ile 645 ns, farklı çekirdekte 27.6 µs; önbellek etkisi; nice değerleri ve ağırlıklar: 75/25, 90/10, 98/2 ölçümü; Linux CFS ve EEVDF, 3.6 ms'lik gözlenen zaman dilimi; gönüllü ve zorla bağlam değişimi."
---

Ders 10.1'de "işlemci sanallaştırılıyor" demiştik: her süreç kendi işlemcisi varmış gibi çalışıyor. Bunu yapan parça **zamanlayıcı** (scheduler): hazırda bekleyen bir sürü iş varken, işlemciyi kime ve ne kadar süreyle vereceğine karar veriyor. Ders 7.28'deki zamanlayıcı kesmesi ona kontrolü geri getiren mekanizma. Bir derleyici yazarı için bu konu `make -j` ölçeklemesini, paralel optimizasyon geçişlerinin davranışını ve Ders 10.12'deki spinlock felaketini açıklıyor.

---

## 1. Ölçütler ve üç klasik algoritma

İki ana ölçüt birbiriyle çekişiyor:

$$
T_{\text{dönüş}} = T_{\text{bitiş}} - T_{\text{geliş}}, \qquad T_{\text{yanıt}} = T_{\text{ilk çalışma}} - T_{\text{geliş}}.
$$

Toplu işler için dönüş süresi önemli; etkileşimli programlar için (editör, terminal) yanıt süresi. Üç algoritma:

- **FCFS** (ilk gelen ilk): gelene sırayla işlemci. Uzun bir iş arkasındakileri bekletir.
- **SJF** (en kısa iş önce): gelenlerin en kısasını seç. Ortalama dönüş süresi kesintisiz algoritmalar arasında en iyi; ama süreyi önceden bilmek gerekir.
- **Round-Robin** (RR): sabit bir **kuantum** süresince çalıştır, sıranın sonuna at. Yanıt süresi iyi.

```c
/* Zamanlayici simulatoru: FCFS, SJF, Round-Robin */
#include <stdio.h>
#include <string.h>
typedef struct { const char *ad; int gelis, sure; int kalan, ilk, bitis; } Is;
enum { N = 5 };
static const Is ORNEK[N] = {
    { "A", 0, 3 }, { "B", 2, 6 }, { "C", 4, 4 }, { "D", 6, 5 }, { "E", 8, 2 },
};
static void rapor(const char *ad, Is *a, int deg) {
    double don = 0, yan = 0;
    for (int i = 0; i < N; i++) { don += a[i].bitis - a[i].gelis; yan += a[i].ilk - a[i].gelis; }
    printf("%-14s ort. donus %5.2f  ort. yanit %5.2f  baglam degisimi %d\n", ad, don / N, yan / N, deg);
}
static void sifirla(Is *a) { memcpy(a, ORNEK, sizeof ORNEK); for (int i = 0; i < N; i++) { a[i].kalan = a[i].sure; a[i].ilk = -1; } }
static void cizgi(const char *ad, const char *c) { printf("%-14s %s\n", ad, c); }

static void kesintisiz(const char *ad, int sjf) {
    Is a[N]; sifirla(a); char c[128] = ""; int t = 0, biten = 0, deg = -1;
    while (biten < N) {
        int s = -1;
        for (int i = 0; i < N; i++) if (a[i].kalan && a[i].gelis <= t && (s < 0 || (sjf && a[i].sure < a[s].sure))) s = i;
        if (s < 0) { strcat(c, "."); t++; continue; }
        a[s].ilk = t; deg++;
        for (int k = 0; k < a[s].sure; k++) strcat(c, a[s].ad);
        t += a[s].sure; a[s].kalan = 0; a[s].bitis = t; biten++;
    }
    cizgi(ad, c); rapor(ad, a, deg);
}
static void rr(const char *ad, int q) {
    Is a[N]; sifirla(a); char c[128] = ""; int t = 0, biten = 0, deg = -1, kuyruk[256], b = 0, s = 0, eklendi = 0, onceki = -1;
    while (biten < N) {
        while (eklendi < N && a[eklendi].gelis <= t) kuyruk[s++] = eklendi++;
        if (b == s) { strcat(c, "."); t++; continue; }
        int i = kuyruk[b++];
        if (a[i].ilk < 0) a[i].ilk = t;
        if (i != onceki) deg++;
        onceki = i;
        int d = a[i].kalan < q ? a[i].kalan : q;
        for (int k = 0; k < d; k++) strcat(c, a[i].ad);
        t += d; a[i].kalan -= d;
        while (eklendi < N && a[eklendi].gelis <= t) kuyruk[s++] = eklendi++;
        if (a[i].kalan) kuyruk[s++] = i; else { a[i].bitis = t; biten++; }
    }
    cizgi(ad, c); rapor(ad, a, deg);
}
int main(void) {
    kesintisiz("FCFS", 0);
    kesintisiz("SJF", 1);
    rr("RR q=1", 1);
    rr("RR q=4", 4);
    return 0;
}
```

```
$ ./sim
FCFS           AAABBBBBBCCCCDDDDDEE
FCFS           ort. donus  8.60  ort. yanit  4.60  baglam degisimi 4
SJF            AAABBBBBBEECCCCDDDDD
SJF            ort. donus  7.60  ort. yanit  3.60  baglam degisimi 4
RR q=1         AABABCBDCBEDCBEDCBDD
RR q=1         ort. donus 10.80  ort. yanit  0.80  baglam degisimi 17
RR q=4         AAABBBBCCCCDDDDBBEED
RR q=4         ort. donus 10.00  ort. yanit  3.60  baglam degisimi 6
```

Her satırın üstündeki şerit bir **Gantt çizimi**: her karakter bir zaman birimi. Tablodan okunan ödünleşim:

- SJF ortalama dönüşte en iyi (7.60). Kısa olan E, uzun D'nin önüne geçti.
- RR q=1'de yanıt süresi çok iyi (0.80), ama dönüş kötü: işler hep yarım bırakılıyor, 17 bağlam değişimi.
- Kuantum büyüyünce RR, FCFS'e yaklaşıyor. Küçüldükçe bağlam değiştirmenin kendi maliyeti sorun oluyor.

Pratikte iş süreleri bilinmiyor ve süreçlerin çoğu sırayla işlemci kullanıp G/Ç bekliyor. Klasik çözüm **çok düzeyli geri beslemeli kuyruk** (MLFQ): işlemciyi kısa kullanıp hemen G/Ç bekleyeni (etkileşimli) ödüllendir, sürekli işlemci yiyeni aşağı indir. Zamanlayıcı, süreye dair bilgiyi **gözlemden** çıkarıyor.

---

## 2. Bağlam değiştirme ne kadar pahalı

Bağlam değiştirme: çalışan sürecin register'larını kaydetmek, başkasınınkini yüklemek; süreç değişiyorsa sayfa tablosunu değiştirmek, TLB'nin bir bölümünü ve önbellekleri soğutmak. Ölçmek için iki süreç bir bayt ping-pong yapıyor: her yazma diğerini uyandırıyor, her okuma beklemeye geçiriyor.

```c
/* Baglam degistirme maliyeti: iki surec bir boru uzerinden bayt ping-pong */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static void cekirdek(int c) { cpu_set_t s; CPU_ZERO(&s); CPU_SET(c, &s); sched_setaffinity(0, sizeof s, &s); }
enum { N = 500000 };
static double olc(int c0, int c1) {
    int a[2], b[2]; pipe(a); pipe(b); char x = 0;
    pid_t p = fork();
    if (p == 0) { cekirdek(c1); for (int i = 0; i < N; i++) { read(a[0], &x, 1); write(b[1], &x, 1); } _exit(0); }
    cekirdek(c0);
    double t0 = simdi();
    for (int i = 0; i < N; i++) { write(a[1], &x, 1); read(b[0], &x, 1); }
    double t = simdi() - t0;
    wait(NULL); close(a[0]); close(a[1]); close(b[0]); close(b[1]);
    return t / N * 1e9;
}
int main(void) {
    int a[2]; pipe(a); char x = 0;
    cekirdek(0);
    double t0 = simdi();
    for (int i = 0; i < N; i++) { write(a[1], &x, 1); read(a[0], &x, 1); write(a[1], &x, 1); read(a[0], &x, 1); }
    double taban = (simdi() - t0) / N * 1e9;
    double ayni = olc(0, 0), farkli = olc(0, 1);
    printf("taban (4 cagri, baglam degisimi yok): %7.0f ns\n", taban);
    printf("ayni cekirdek ping-pong             : %7.0f ns\n", ayni);
    printf("farkli cekirdek ping-pong           : %7.0f ns\n", farkli);
    printf("bir baglam degisimi yaklasik        : %7.0f ns\n", (ayni - taban) / 2);
    struct rusage r; getrusage(RUSAGE_CHILDREN, &r);
    printf("cocuklarin gonullu degisimi %ld, zorla degisimi %ld\n", r.ru_nvcsw, r.ru_nivcsw);
    return 0;
}
```

```
$ ./ping
taban (4 cagri, baglam degisimi yok):     699 ns
ayni cekirdek ping-pong             :    1988 ns
farkli cekirdek ping-pong           :   27649 ns
bir baglam degisimi yaklasik        :     645 ns
cocuklarin gonullu degisimi 884007, zorla degisimi 115916
```

Aynı çekirdekte bir tur iki bağlam değişimi içeriyor: yaklaşık 645 ns. Doğrudan maliyet düşük görünüyor; ama **dolaylı** maliyet (soğuk önbellek ve TLB) ölçümde yok, çünkü programlar neredeyse hiç bellek kullanmıyor. Gerçek bir iş yükünde bir değişim mikrosaniyelerce önbellek ıskası demek olabilir (Ders 7.24).

**Farklı çekirdekler** 14 kat daha yavaş: uyandırma, karşı çekirdeğe bir kesme (IPI) göndermek demek; sanal makinelerde bu özellikle pahalı. Sezgiye aykırı sonuç: paralelleştirmek bir ping-pong kalıbını yavaşlatabilir. Çekirdek de bu yüzden uyandırılan süreci uyandıranın yakınına koymaya çalışıyor (`wake affine`).

Son satırdaki iki sayaç önemli bir ayrımı gösteriyor: **gönüllü** bağlam değişimi (süreç kendisi engellendi) ve **zorla** (zamanlayıcı kesti). `getrusage`, `/proc/PID/status` ve `pidstat -w` bu sayıları verir.

---

## 3. Linux'ta adalet: CFS ve EEVDF

Linux 2.6.23'ten 6.5'e kadar **CFS** (Completely Fair Scheduler) kullandı; 6.6 ile **EEVDF** (Earliest Eligible Virtual Deadline First) geldi. Fikir ortak: her iş parçacığı için bir **sanal zaman** (`vruntime`) tutulur; işlemcide az kalanlar önce çalışır, kırmızı-siyah ağaç (Ders 8.10) hangisinin en önde olduğunu $O(\log n)$ ile bulur. Ağırlık olarak **nice** değeri (-20...+19) kullanılır:

$$
\text{ağırlık}(n) \approx \frac{1024}{1.25^{\,n}}, \qquad \text{pay}_i = \frac{\text{ağırlık}_i}{\sum_j \text{ağırlık}_j}.
$$

Her nice adımı yaklaşık %25 ağırlık farkı demek. Çekirdekteki tablo: nice 0 = 1024, 5 = 335, 10 = 110, 19 = 15. Ölçelim:

```c
/* nice degeri ve islemci payi: ayni cekirdekte yarisan surecler */
#define _GNU_SOURCE
#include <sched.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static volatile sig_atomic_t dur;
static void h(int s) { (void)s; dur = 1; }
static void dene(const int *n, int k, double sn) {
    long *say = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    pid_t p[8];
    for (int i = 0; i < k; i++) {
        p[i] = fork();
        if (p[i] == 0) {
            cpu_set_t s; CPU_ZERO(&s); CPU_SET(2, &s); sched_setaffinity(0, sizeof s, &s);
            setpriority(PRIO_PROCESS, 0, n[i]);
            signal(SIGTERM, h);
            long c = 0; while (!dur) c++;
            say[i] = c; _exit(0);
        }
    }
    usleep((useconds_t)(sn * 1e6));
    for (int i = 0; i < k; i++) kill(p[i], SIGTERM);
    for (int i = 0; i < k; i++) wait(NULL);
    long top = 0; for (int i = 0; i < k; i++) top += say[i];
    for (int i = 0; i < k; i++) printf("  nice %3d: pay %%%5.1f\n", n[i], 100.0 * say[i] / top);
}
int main(void) {
    int a[] = { 0, 0 }, b[] = { 0, 5 }, c[] = { 0, 10 }, d[] = { 0, 19 };
    puts("esit"); dene(a, 2, 1.0);
    puts("0 ve 5"); dene(b, 2, 1.0);
    puts("0 ve 10"); dene(c, 2, 1.0);
    puts("0 ve 19"); dene(d, 2, 1.0);
    return 0;
}
```

```
$ ./iyilik
esit
  nice   0: pay % 49.9
  nice   0: pay % 50.1
0 ve 5
  nice   0: pay % 75.1
  nice   5: pay % 24.9
0 ve 10
  nice   0: pay % 90.1
  nice  10: pay %  9.9
0 ve 19
  nice   0: pay % 98.0
  nice  19: pay %  2.0
```

Teori: $1024 / (1024 + 335) = 75.3\%$, $1024 / 1134 = 90.3\%$, $1024 / 1039 = 98.6\%$. Bir saniyelik testlerde ölçümler bunlara oldukça yakın. (Sayaç, her turda `dur` bayrağını kontrol eden bir döngü; yani "yapılan iş", işlemci zamanının iyi bir yaklaşığı.)

### Gözlenen zaman dilimi

```c
/* Zaman dilimi: kac kez zorla kesildik */
#define _GNU_SOURCE
#include <sched.h>
#include <stdio.h>
#include <sys/resource.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
int main(void) {
    cpu_set_t s; CPU_ZERO(&s); CPU_SET(3, &s); sched_setaffinity(0, sizeof s, &s);
    for (int k = 1; k <= 3; k++) {
        for (int i = 0; i < k; i++) if (fork() == 0) {
            double t0 = simdi(); volatile long c = 0; struct rusage r0, r1;
            getrusage(RUSAGE_SELF, &r0);
            while (simdi() - t0 < 1.0) c++;
            getrusage(RUSAGE_SELF, &r1);
            double cpu = (r1.ru_utime.tv_sec - r0.ru_utime.tv_sec) + (r1.ru_utime.tv_usec - r0.ru_utime.tv_usec) * 1e-6 + (r1.ru_stime.tv_sec - r0.ru_stime.tv_sec) + (r1.ru_stime.tv_usec - r0.ru_stime.tv_usec) * 1e-6;
            long zorla = r1.ru_nivcsw - r0.ru_nivcsw;
            printf("%d surec: islemci %.2f s, zorla degisim %ld, ort. dilim %.1f ms\n", k, cpu, zorla, zorla ? cpu * 1e3 / zorla : 0.0);
            fflush(stdout);
            _exit(0);
        }
        while (wait(NULL) > 0) { }
    }
    return 0;
}
```

```
$ ./dilim
1 surec: islemci 1.00 s, zorla degisim 6, ort. dilim 166.7 ms
2 surec: islemci 0.50 s, zorla degisim 137, ort. dilim 3.6 ms
2 surec: islemci 0.50 s, zorla degisim 138, ort. dilim 3.7 ms
3 surec: islemci 0.33 s, zorla degisim 95, ort. dilim 3.5 ms
3 surec: islemci 0.33 s, zorla degisim 100, ort. dilim 3.3 ms
3 surec: islemci 0.34 s, zorla degisim 93, ort. dilim 3.6 ms
```

Tek çekirdeğe bağlı iki ve üç süreç: işlemci adil bölünmüş (0.50, 0.33), dilim yaklaşık 3.5 ms. Yani bir CPU'yu paylaşan iş parçacıkları her saniye yüzlerce kez yer değiştiriyor; kilit tutan iş parçacığının dilimi bitip kesilmesi Ders 10.12'de spinlock'un neden mutex'e kaybettiğinin açıklaması.

Çok çekirdekli sistemde her çekirdeğin kendi kuyruğu var ve çekirdek düzenli olarak yük dengeliyor. `sched_setaffinity` ile bir süreci bir çekirdeğe sabitlemek bu dengelemeyi devre dışı bırakıyor; ölçümlerde kararlılık (Ders 10.18) için kullanışlı, üretimde ise dikkatli olunmalı. `SCHED_FIFO` ve `SCHED_RR` gerçek zamanlı politikalar; ayrıcalık gerektirir ve normal işleri tamamen aç bırakabilir.

---

## Alıştırmalar

**1** – Aynı beş iş için simülatöre **kesintili SJF**'yi (SRTF: kalan süresi en kısa olan) ekle. Ortalama dönüş ne çıkıyor? Yanıt süresi?

**2** – RR'ye bağlam değiştirme maliyeti ekle: her değişim 0.1 birim. $q = 1$ ve $q = 4$ için toplam süreyi hesapla. Kuantum seçimi nasıl bir ödünleşim?

**3** – SJF'nin ne kadar aç bırakabileceğini göster: her zaman biriminde kısa işler geliyorsa uzun iş hiç çalışmaz. Bunu önleyen basit yöntem hangisi?

**4** – İki süreç için nice 0 ve nice 1 payını teorik olarak hesapla; `iyilik.c`'de doğrula. Nice 0'daki bir süreç üç tane nice 19 süreçle yarışırsa nice 0 ne kadar alır?

**5** – `make -j N`'de $N$'i çekirdek sayısından büyük seçince neden ek hızlanma olur (ya da olabilir)? `make -j` aşırı büyükse ne yavaşlar?

<details>
<summary>Cevaplar</summary>

**1** – Her zaman biriminde kalan süresi en kısa olanı seç. Gantt: `AAABCCCCEEBBBBBDDDDD`. t=3'te B başlıyor; t=4'te C gelince (kalan 4) B'nin kalanı 5 olduğu için C kesiyor; t=8'de E (kalan 2) çalışıyor; sonra B ve D. Dönüşler: A 3, B 13, C 4, D 14, E 2 → ortalama $36/5 = 7.20$, SJF'nin 7.60'ından iyi. Yanıt süreleri: A 0, B 1, C 0, D 9, E 0 → ortalama 2.00, SJF'nin 3.60'ından iyi. Kesme yeteneği kısa işlerin beklemesini azaltıyor; bedeli, uzun işlerin (D) daha da beklemesi.

**2** – 20 birimlik iş; q=1: 17 değişim, 21.7 birim. q=4: 6 değişim, 20.6 birim. Yük %8.5'ten %3'e iniyor; ama q büyüdükçe yanıt süresi kötüleşiyor. Kural: kuantum, tipik bir bağlam değişiminden en az bir iki büyüklük mertebesi büyük olmalı.

**3** – Yaşlandırma (aging): uzun bekleyen işin önceliğini artır. CFS/EEVDF'de bu kendiliğinden: az çalışanın sanal zamanı geride kalıyor ve sıra ona geliyor.

**4** – Ağırlıklar 1024 ve 820: $1024 / 1844 = 55.5\%$ ve $44.5\%$. Üç nice 19 (15'er ağırlık): $1024 / (1024 + 45) = 95.8\%$.

**5** – Derleme işleri G/Ç (disk) bekliyorsa, çekirdek boş kalıyor: birkaç fazla iş bu boşlukları doldurur. Aşırı `-j` değerinde ise bellek tükenir (her `cc1` yüzlerce MB; Ders 10.7'deki OOM killer) ve önbellek/TLB zarar görür; ayrıca bağlam değişimi artar. `make`'in jobserver'ı alt süreçler arası bir boruyla iş jetonlarını paylaştırıyor: Ders 10.5'teki boru + Ders 10.11'deki semafor fikrinin pratik hali.

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 7–10: zamanlama, MLFQ, adil paylaşım, çok işlemci.
- Ingo Molnar, CFS tasarım belgesi: `Documentation/scheduler/sched-design-CFS.rst` (Linux çekirdek kaynak ağacı).
- Ion Stoica ve Hussein Abdel-Wahab, "Earliest Eligible Virtual Deadline First", 1995: EEVDF'in kökeni.
- Peter Zijlstra, EEVDF yama serisi, Linux 6.6, 2023.
- `man 7 sched`, `man 2 sched_setaffinity`, `man 2 setpriority`.

**Sıradaki ders:** Dosya sistemleri. inode, dizin, bağlantı türleri, `stat`.
