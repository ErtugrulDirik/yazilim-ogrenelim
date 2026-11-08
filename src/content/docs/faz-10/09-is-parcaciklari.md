---
title: "10.9 İş parçacıkları"
description: "İş parçacığı: aynı adres alanını paylaşan yürütme akışları; pthread_create ve join; PID aynı, TID farklı; döngü değişkeninin adresini vermenin hatası; clone3 bayraklarını strace ile okumak; oluşturma maliyeti 47 µs, fork 117 µs; 400 milyon elemanlı paralel toplamda hızlanma ve 3.3 kat tavanı; _Thread_local ve errno'nun iş parçacığı başına olması."
---

Ders 10.4'teki süreçler birbirinden yalıtılmıştı: paylaşmak için boru ya da `mmap` gerekiyordu. **İş parçacığı** (thread) ise aynı adres alanında çalışan ikinci bir yürütme akışı: kendi register'ları ve yığını var, ama global değişkenleri, heap'i ve dosya tanımlayıcılarını kardeşleriyle paylaşıyor. Paralel derleme, derleyicinin paralel optimizasyon geçişleri, her modern sunucu bunun üzerine kurulu. Ve paylaşım, Ders 10.10–10.13'ün konusu olan bütün sorunların kaynağı.

Derleme: `cc -pthread`. (Modern glibc'de pthread libc'nin içinde, ama bayrak hâlâ doğru tanım ve bağlama için önerilir.)

---

## 1. Oluşturmak ve beklemek

```c
int pthread_create(pthread_t *t, const pthread_attr_t *ozellik, void *(*f)(void *), void *arg);
int pthread_join(pthread_t t, void **donus);
```

`pthread_create` yeni bir akış başlatıp `f(arg)`'ı çalıştırıyor. `pthread_join` bitmesini bekliyor (süreçlerdeki `wait`'in karşılığı) ve `f`'in dönüş değerini alıyor. Bu fonksiyonlar hatada `-1` değil **hata kodunu doğrudan** döndürüyor; `errno` kullanmıyorlar.

```c
/* Is parcaciklari ayni adres alaninda: global ve yigin adresleri */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/syscall.h>
#include <unistd.h>

static int global = 0;

typedef struct { int no; int sonuc; } Is;

static void *calis(void *arg) {
    Is *is = arg;
    int yerel = is->no * 10;
    global += 1;
    is->sonuc = yerel + 1;
    printf("is %d: pid=%d, tid=%ld, &yerel=%p, &global=%p\n", is->no, getpid(), (long)syscall(SYS_gettid), (void *)&yerel, (void *)&global);
    return is;
}

int main(void) {
    setbuf(stdout, NULL);
    pthread_t t[3]; Is isler[3];
    printf("main: pid=%d, tid=%ld\n", getpid(), (long)syscall(SYS_gettid));
    for (int i = 0; i < 3; i++) {
        isler[i] = (Is){ i, 0 };
        pthread_create(&t[i], NULL, calis, &isler[i]);
        pthread_join(t[i], NULL);
    }
    for (int i = 0; i < 3; i++) printf("is %d sonucu %d\n", i, isler[i].sonuc);
    printf("global = %d\n", global);
    return 0;
}
```

```
$ cc -O2 -Wall -pthread ilk.c -o ilk && ./ilk
main: pid=23, tid=23
is 0: pid=23, tid=24, &yerel=0xffff91a0e8bc, &global=0xaaaae74b0064
is 1: pid=23, tid=25, &yerel=0xffff91a0e8bc, &global=0xaaaae74b0064
is 2: pid=23, tid=26, &yerel=0xffff91a0e8bc, &global=0xaaaae74b0064
is 0 sonucu 1
is 1 sonucu 11
is 2 sonucu 21
global = 3
```

- **PID aynı, TID farklı.** Linux'ta çekirdeğin zamanladığı birim TID'dir; bir "süreç" aslında aynı PID'i paylaşan bir **iş parçacığı grubu**. `/proc/PID/task/` altında her TID için bir dizin var.
- `&global` aynı: tek bir değişken. `global` 3 oldu.
- `&yerel` burada üçünde de aynı çünkü iş parçacıkları sırayla çalıştı ve kütüphane biten iş parçacığının yığınını yeniden kullandı. Aynı anda çalışsalardı farklı adreslerde olurlardı.

Sonuç, argüman yapısına yazılarak döndürüldü: yığındaki bir değişkenin adresini döndürmek (bir fonksiyondan olduğu gibi; Ders 4.23) bu durumda da hatalı.

### Çekirdek açısından

```
$ strace -f -e trace=clone3,mmap,mprotect,futex,exit ./tls
mmap(NULL, 8454144, PROT_NONE, MAP_PRIVATE|MAP_ANONYMOUS|MAP_STACK, -1, 0) = 0xffff99e00000
mprotect(0xffff99e10000, 8388608, PROT_READ|PROT_WRITE) = 0
clone3({flags=CLONE_VM|CLONE_FS|CLONE_FILES|CLONE_SIGHAND|CLONE_THREAD|CLONE_SYSVSEM|CLONE_SETTLS|CLONE_PARENT_SETTID|CLONE_CHILD_CLEARTID, ..., stack=0xffff99e00000, stack_size=0x80ea40, tls=0xffff9a60f8c0}...) = 40102
[pid 40101] futex(0xffff9a60f250, FUTEX_WAIT_BITSET|FUTEX_CLOCK_REALTIME, 40102, NULL, FUTEX_BITSET_MATCH_ANY <unfinished ...>
[pid 40102] exit(0)                     = ?
```

Bütün derslerin birleştiği yer:

- `mmap(... PROT_NONE)` + `mprotect(... READ|WRITE)`: 8 MB'lik **yığın** ayırıyor; altında bırakılan `PROT_NONE` bölge **koruma sayfası** (Ders 10.7).
- `clone3`: `fork`'la aynı çağrı ailesi, tek fark **bayraklar**. `CLONE_VM` adres alanını, `CLONE_FILES` dosya tablosunu, `CLONE_SIGHAND` sinyal işleyicilerini paylaştırıyor; `CLONE_THREAD` aynı PID grubuna koyuyor; `CLONE_SETTLS` iş parçacığı yerel depolamayı kuruyor.
- `futex`: `pthread_join` çekirdekte uyuyor, çocuk bitince uyandırılıyor.

Çekirdekte süreç ve iş parçacığı için ayrı yapılar yok: ikisi de bir `task_struct`; ne kadar paylaşacaklarını bayraklar belirliyor.

---

## 2. Klasik tuzak

```c
/* Klasik hata: dongu degiskeninin adresini vermek */
#include <pthread.h>
#include <stdio.h>
#include <stdint.h>
static void *yanlis(void *a) { return (void *)(intptr_t)*(int *)a; }
static void *dogru(void *a) { return a; }
int main(void) {
    for (int tur = 0; tur < 2; tur++) {
        pthread_t t[8]; void *d;
        printf("%s: ", tur == 0 ? "yanlis (&i)" : "dogru (deger)");
        for (int i = 0; i < 8; i++) pthread_create(&t[i], NULL, tur == 0 ? yanlis : dogru, tur == 0 ? (void *)&i : (void *)(intptr_t)i);
        for (int i = 0; i < 8; i++) { pthread_join(t[i], &d); printf("%ld ", (long)(intptr_t)d); }
        printf("\n");
    }
    return 0;
}
```

```
$ ./tuzak
yanlis (&i): 1 2 3 5 7 7 7 7 
dogru (deger): 0 1 2 3 4 5 6 7 
$ ./tuzak
yanlis (&i): 4 3 5 6 7 7 7 7 
dogru (deger): 0 1 2 3 4 5 6 7 
```

Her iş parçacığı **aynı** `i`'nin adresini aldı; yeni iş parçacığı onu okuyana kadar `main` çoktan arttırmış oluyor. Üstelik her çalıştırmada başka sonuç. İş parçacığına ya değerin kendisi (yukarıdaki gibi pointer'a sığdırılmış) ya da yaşayacağı bilinen ayrı bir nesnenin adresi verilmeli.

---

## 3. Ne kadar ucuz?

```c
/* Olusturma maliyeti: fonksiyon cagrisi, is parcacigi, surec */
#include <pthread.h>
#include <stdio.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static void *bos(void *a) { return a; }
int main(void) {
    enum { N = 20000 };
    double t0 = simdi();
    for (int i = 0; i < N; i++) { pthread_t t; pthread_create(&t, NULL, bos, NULL); pthread_join(t, NULL); }
    double t1 = simdi();
    for (int i = 0; i < N; i++) { pid_t p = fork(); if (p == 0) _exit(0); waitpid(p, NULL, 0); }
    double t2 = simdi();
    printf("pthread_create+join : %6.1f us\n", (t1 - t0) / N * 1e6);
    printf("fork+waitpid        : %6.1f us\n", (t2 - t1) / N * 1e6);
    return 0;
}
```

```
$ ./maliyet
pthread_create+join :   46.8 us
fork+waitpid        :  117.2 us
```

İş parçacığı ucuz ama bedava değil: Ders 10.1'deki bir sistem çağrısının ~400 katı. Kısa ömürlü işler için bu yüzden önceden açılıp tekrar tekrar kullanılan bir **iş parçacığı havuzu** kurulur (Ders 10.11 sonrası Alıştırma).

### Paralel hızlanma

```c
/* Paralel toplam: is parcacigi sayisina gore hizlanma */
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
enum { N = 400000000 };
static uint32_t *a;
typedef struct { long bas, son; uint64_t top; } Dilim;
static void *topla(void *v) {
    Dilim *d = v; uint64_t s = 0;
    for (long i = d->bas; i < d->son; i++) { uint64_t x = a[i]; x = (x * x) ^ (x >> 3); s += x; }
    d->top = s;
    return NULL;
}
int main(void) {
    a = malloc(N * sizeof *a);
    for (long i = 0; i < N; i++) a[i] = (uint32_t)(i * 2654435761u);
    double bir = 0;
    int ts[] = { 1, 2, 4, 8, 16 };
    for (int k = 0; k < 5; k++) {
        int T = ts[k]; pthread_t t[16]; Dilim d[16];
        double t0 = simdi();
        for (int i = 0; i < T; i++) { d[i] = (Dilim){ (long)N * i / T, (long)N * (i + 1) / T, 0 }; pthread_create(&t[i], NULL, topla, &d[i]); }
        uint64_t top = 0;
        for (int i = 0; i < T; i++) { pthread_join(t[i], NULL); top += d[i].top; }
        double s = simdi() - t0;
        if (T == 1) bir = s;
        printf("%2d is parcacigi: %7.1f ms, hizlanma %4.2f  (toplam %llx)\n", T, s * 1e3, bir / s, (unsigned long long)top);
    }
    return 0;
}
```

```
$ nproc
8
$ ./paralel
 1 is parcacigi:    85.6 ms, hizlanma 1.00  (toplam 6c1e3f683af1400)
 2 is parcacigi:    39.4 ms, hizlanma 2.17  (toplam 6c1e3f683af1400)
 4 is parcacigi:    27.4 ms, hizlanma 3.12  (toplam 6c1e3f683af1400)
 8 is parcacigi:    27.7 ms, hizlanma 3.09  (toplam 6c1e3f683af1400)
16 is parcacigi:    26.0 ms, hizlanma 3.29  (toplam 6c1e3f683af1400)
```

Toplamların hepsi aynı. Dilimler ayrık olduğu için iş parçacıkları hiçbir şeyi **yazarak** paylaşmıyor; kilit gerekmiyor. Hızlanma ise bir tavana çarpıyor: 8 çekirdekli makinede 3.3 kat. Olası nedenler: M2'nin dört performans ve dört verimlilik çekirdeği olması, belleğin bant genişliği (400 milyon eleman, 1.6 GB tarıyoruz; Ders 7.24) ve 2 iş parçacığında 2.17'nin de gösterdiği gibi ölçüm dalgalanması (ilk turda sayfalar henüz ısınmamış). Bu yüzden "çekirdek sayısı kadar hızlanır" varsayımı güvenilmez.

Hızlanmanın teorik sınırı **Amdahl yasası**: programın $p$ kadarı paralelleştirilebiliyorsa $n$ çekirdekte hızlanma

$$
S(n) = \frac{1}{(1 - p) + p / n}
$$

$n \to \infty$ için $1/(1-p)$. %95'i paralel olan bir program sonsuz çekirdekle bile 20 kat hızlanabilir.

---

## 4. Ne paylaşılıyor, ne paylaşılmıyor

| Paylaşılan | İş parçacığına özel |
| --- | --- |
| Kod, global veriler, heap | Yığın |
| Dosya tanımlayıcıları, çalışma dizini | Register'lar, program sayacı |
| Sinyal işleyicileri | Sinyal maskesi |
| PID, kullanıcı kimlikleri | TID, `errno`, iş parçacığı yerel değişkenleri |

`_Thread_local` (C11) ile tanımlanan değişken her iş parçacığı için ayrı. `errno` da böyle, olmasaydı iki iş parçacığı birbirinin hatasını okurdu:

```c
/* Is parcacigi yerel depolama ve errno */
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>
static _Thread_local int yerel = 0;
static int ortak = 0;
static void *calis(void *a) {
    (void)a;
    yerel = 7; ortak = 7;
    close(-1);
    printf("is parcacigi: yerel=%d, &errno=%p, errno=%d\n", yerel, (void *)&errno, errno);
    return NULL;
}
int main(void) {
    pthread_t t;
    errno = 0;
    printf("main        : &errno=%p\n", (void *)&errno);
    pthread_create(&t, NULL, calis, NULL); pthread_join(t, NULL);
    printf("main        : yerel=%d, ortak=%d, errno=%d\n", yerel, ortak, errno);
    return 0;
}
```

```
$ ./tls
main        : &errno=0xffff852de650
is parcacigi: yerel=7, &errno=0xffff8500f8f0, errno=9
main        : yerel=0, ortak=7, errno=0
```

`errno` aslında bir makro: `*__errno_location()`, çağıran iş parçacığının kopyasını gösteriyor. Sinyallerde ise ayrı bir kural var: süreçteki **herhangi bir** iş parçacığına teslim edilir, sinyal maskesi iş parçacığı başına; sinyalleri tek bir iş parçacığına toplamak (`pthread_sigmask` + `sigwait`) çok iş parçacıklı programların yaygın yöntemi. `fork` ise sadece çağıran iş parçacığını kopyalar; kilitler o anki halleriyle kalır, bu yüzden çok iş parçacıklı programda `fork` sonrası sadece `exec` veya async-signal-safe çağrılar güvenli (Ders 10.6).

---

## Alıştırmalar

**1** – Paralel toplam için Amdahl yasasını kullan: 4 iş parçacığında ölçülen hızlanma 3.12. Bu sonuç için $p$ kaç olmalı? Aynı $p$ ile 16 çekirdekte beklenen hızlanmayı hesapla ve ölçümle karşılaştır.

**2** – Bir `int a[1000]` dizisinin elemanlarını iş parçacıkları **ayrı** indekslere yazıyorsa kilit gerekir mi? Peki `a[i] = a[i-1] + 1` yazıyorsa?

**3** – `pthread_create`'e `attr` vererek yığın boyutunu 16 KB yap, iş parçacığında 32 KB'lik bir dizi kullan. Ne oluyor? Varsayılan yığın boyutunu nasıl öğrenirsin (`ulimit -s`, `pthread_attr_getstacksize`)?

**4** – Bir iş parçacığı `exit(0)` çağırırsa ne olur? `pthread_exit(0)` çağırırsa? `main`, `pthread_join` yapmadan `return 0` derse?

**5** – 1000 kısa iş için 1000 iş parçacığı açmak yerine 8 iş parçacıklı bir havuz kullanırsan maliyet kazancı ne olur (Bölüm 3'teki ölçümle)? Havuzun iş kuyruğu için ne gerekir? (Ders 10.11.)

<details>
<summary>Cevaplar</summary>

**1** – $3.12 = 1 / ((1-p) + p/4)$ → $(1-p) + p/4 = 0.3205$ → $1 - 0.75 p = 0.3205$ → $p \approx 0.906$. 16 çekirdekte: $1 / (0.094 + 0.906/16) = 1 / 0.1506 \approx 6.6$. Ölçülen 3.29, çok daha düşük. Yani sınır Amdahl değil, donanım (performans çekirdeği sayısı ve bellek): Amdahl'daki kalıcı $p$ varsayımı burada tutmuyor, çünkü darboğaz koddaki seri bölüm değil.

**2** – Ayrı indekslere yazmak: kilit gerekmez, her iş parçacığı kendi baytlarına dokunuyor (C11'in bellek modeli farklı nesnelere erişimi garanti ediyor; aynı önbellek satırına düşüyorlarsa "yanlış paylaşım" yavaşlatabilir, Faz 11). `a[i] = a[i-1] + 1`'de komşu indeks başka iş parçacığı tarafından yazılıyor: dilimlerin sınırlarında **veri yarışı**. Ya senkronizasyon, ya da bağımlılığı kuran bir bölümleme.

**3** – `pthread_attr_setstacksize(&a, 16384); pthread_create(&t, &a, f, NULL);` (en az `PTHREAD_STACK_MIN`). 32 KB yığın kullanımı koruma sayfasına çarpar: `SIGSEGV`. Hatanın arkasında ne olduğu `si_addr` ile (Ders 10.6) anlaşılabilir. Varsayılan: glibc `ulimit -s` değerini kullanır (genellikle 8 MB).

**4** – `exit(0)`: bütün süreç biter (`exit_group`), bütün iş parçacıklarıyla. `pthread_exit(0)`: sadece çağıran iş parçacığı biter. `main`'den `return 0` da `exit` çağırır: bütün iş parçacıkları ölür, bitirilmemiş işler kaybolur. Bu yüzden `main` `join` yapmadan dönmemeli ya da `pthread_exit` çağırmalı.

**5** – 1000 × 47 µs = 47 ms oluşturma maliyetinden, 8 × 47 µs ≈ 0.4 ms'ye iniyor. İş başına sürenin çok altında olduğu durumlarda bu büyük fark. Havuz için iş kuyruğu gerekiyor: boşken işçiler uyumalı, iş geldiğinde uyandırılmalı, dolunca üreticiler beklemeli: kilit ve koşul değişkenleri (Ders 10.11).

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 26–27: eşzamanlılık ve thread API'si.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 29–33: POSIX iş parçacıkları.
- David Butenhof, *Programming with POSIX Threads*, Addison-Wesley, 1997.
- Gene Amdahl, "Validity of the Single Processor Approach to Achieving Large Scale Computing Capabilities", *AFIPS*, 1967.
- `man 7 pthreads`, `man 2 clone3`, `man 3 pthread_create`.

**Sıradaki ders:** Yarış durumları ve kilitler. Mutex, kritik bölge, sayaç yarışı deneyi.
