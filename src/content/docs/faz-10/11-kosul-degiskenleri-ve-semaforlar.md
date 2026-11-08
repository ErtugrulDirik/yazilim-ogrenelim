---
title: "10.11 Koşul değişkenleri ve semaforlar"
description: "Bir koşulu beklemenin doğru yolu: boşta döngü 1 s işlemci, koşul değişkeni sıfır; pthread_cond_wait'in atomik bırak-ve-uyu sözleşmesi; sınırlı kuyruk ile üretici–tüketici: 3 üretici, 3 tüketici, 6 milyon öğe, toplam doğrulaması; neden if değil while (483 hatalı uyanma); signal ve broadcast; semafor ve iki sayaçla aynı kuyruk; koşul değişkeni ile semaforun karşılaştırılması."
---

Kilit, "aynı anda bir kişi" sorusunu çözüyor. Çoğu zaman bir de "**bir şey olana kadar bekle**" sorusu var: kuyrukta iş olana kadar, kuyrukta yer açılana kadar, bir ayar yüklenene kadar. İş parçacığı havuzları, `make -j`, her sunucunun ana döngüsü bunun üzerine kurulu. Bu derste koşul değişkenlerini ve semaforları kullanıp klasik **üretici–tüketici** problemini çözüyoruz.

---

## 1. Boşta beklemek kötü

Kilitsiz, en doğal yol: bir bayrağa bakan döngü.

```c
/* Bosta bekleme ile kosul degiskeni: islemci zamani */
#include <pthread.h>
#include <stdio.h>
#include <sys/resource.h>
#include <time.h>
#include <unistd.h>
static volatile int hazir = 0;
static pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t c = PTHREAD_COND_INITIALIZER;
static int bayrak = 0;
static void *dongulu(void *a) { (void)a; while (!hazir) { } return NULL; }
static void *kosullu(void *a) { (void)a; pthread_mutex_lock(&m); while (!bayrak) pthread_cond_wait(&c, &m); pthread_mutex_unlock(&m); return NULL; }
static double cpu(void) { struct rusage r; getrusage(RUSAGE_SELF, &r); return r.ru_utime.tv_sec + r.ru_utime.tv_usec * 1e-6 + r.ru_stime.tv_sec + r.ru_stime.tv_usec * 1e-6; }
int main(void) {
    pthread_t t; double c0 = cpu();
    pthread_create(&t, NULL, dongulu, NULL); sleep(1); hazir = 1; pthread_join(t, NULL);
    double c1 = cpu();
    pthread_create(&t, NULL, kosullu, NULL); sleep(1);
    pthread_mutex_lock(&m); bayrak = 1; pthread_cond_signal(&c); pthread_mutex_unlock(&m); pthread_join(t, NULL);
    double c2 = cpu();
    printf("1 saniye bosta dongu   : %.3f s islemci\n", c1 - c0);
    printf("1 saniye kosul degiskeni: %.3f s islemci\n", c2 - c1);
    return 0;
}
```

```
$ ./bekle
1 saniye bosta dongu   : 1.005 s islemci
1 saniye kosul degiskeni: 0.000 s islemci
```

Boşta döngü (busy wait, spin) bir çekirdeği yüzde yüz meşgul ediyor; pil ve başka iş parçacıklarından çalıyor. (Ayrıca `volatile` burada da doğru senkronizasyon değil; `hazir`'ı doğru yazmak Ders 10.12.) Koşul değişkeni ise iş parçacığını **çekirdekte uyutuyor**.

---

## 2. Koşul değişkeni

Koşul değişkeni (`pthread_cond_t`) bir veri tutmaz: "üzerinde uyuyanların kuyruğu"dur. Koşulun kendisi (kuyruk boş mu?) sizin paylaşılan verinizde ve bir mutex ile korunuyor.

```c
pthread_mutex_lock(&m);
while (!kosul)                       /* her zaman while */
    pthread_cond_wait(&c, &m);       /* m'yi birak, uyu; uyaninca m'yi yeniden al */
/* kosul dogru ve m elimizde */
pthread_mutex_unlock(&m);
```

Uyandıran taraf:

```c
pthread_mutex_lock(&m);
kosul = 1;
pthread_cond_signal(&c);             /* bir bekleyeni uyandir */
pthread_mutex_unlock(&m);
```

`pthread_cond_wait`'in sihri, **mutex'i bırakıp uyumanın tek bir atomik adım** olması. İki ayrı adım olsaydı (bırak, uyu) arada uyandırma sinyali gelip kaybolabilirdi ("lost wakeup"): tam Ders 10.6'daki `pause` yarışı, `sigsuspend`'in çözdüğü şey.

### Sınırlı kuyruk

Üretici elemanları koyar, tüketici alır; kuyruk sınırlı: dolunca üretici, boşken tüketici bekler. Boyut sınırı **geri basınç** sağlar (Ders 10.5'teki boru gibi). İki koşul var, iki koşul değişkeni:

```c
/* Uretici-tuketici: sinirli kuyruk, mutex ve iki kosul degiskeni */
#include <pthread.h>
#include <stdio.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
enum { KAP = 64, URETICI = 3, TUKETICI = 3, HER = 2000000 };

typedef struct {
    long v[KAP];
    int bas, son, say;
    pthread_mutex_t m;
    pthread_cond_t dolu_degil, bos_degil;
} Kuyruk;

static Kuyruk q = { .m = PTHREAD_MUTEX_INITIALIZER, .dolu_degil = PTHREAD_COND_INITIALIZER, .bos_degil = PTHREAD_COND_INITIALIZER };
static long bekleme_u, bekleme_t;

static void koy(Kuyruk *k, long x) {
    pthread_mutex_lock(&k->m);
    while (k->say == KAP) { bekleme_u++; pthread_cond_wait(&k->dolu_degil, &k->m); }
    k->v[k->son] = x; k->son = (k->son + 1) % KAP; k->say++;
    pthread_cond_signal(&k->bos_degil);
    pthread_mutex_unlock(&k->m);
}
static long al(Kuyruk *k) {
    pthread_mutex_lock(&k->m);
    while (k->say == 0) { bekleme_t++; pthread_cond_wait(&k->bos_degil, &k->m); }
    long x = k->v[k->bas]; k->bas = (k->bas + 1) % KAP; k->say--;
    pthread_cond_signal(&k->dolu_degil);
    pthread_mutex_unlock(&k->m);
    return x;
}
static void *uretici(void *a) { long id = (long)a; for (long i = 1; i <= HER; i++) koy(&q, id * 10000000 + i); return NULL; }
static void *tuketici(void *a) { long *t = a; for (long i = 0; i < HER; i++) *t += al(&q) % 10000000; return NULL; }
int main(void) {
    pthread_t u[URETICI], t[TUKETICI]; long top[TUKETICI] = { 0 };
    double t0 = simdi();
    for (long i = 0; i < TUKETICI; i++) pthread_create(&t[i], NULL, tuketici, &top[i]);
    for (long i = 0; i < URETICI; i++) pthread_create(&u[i], NULL, uretici, (void *)(i + 1));
    for (int i = 0; i < URETICI; i++) pthread_join(u[i], NULL);
    for (int i = 0; i < TUKETICI; i++) pthread_join(t[i], NULL);
    long s = 0; for (int i = 0; i < TUKETICI; i++) s += top[i];
    long bek = (long)URETICI * (long)HER * ((long)HER + 1) / 2;
    printf("toplam %ld, beklenen %ld: %s\n", s, bek, s == bek ? "DOGRU" : "YANLIS");
    printf("%.0f ms, oge basina %.0f ns; bekleme: uretici %ld, tuketici %ld\n", (simdi() - t0) * 1e3, (simdi() - t0) / (URETICI * (double)HER) * 1e9, bekleme_u, bekleme_t);
    return 0;
}
```

```
$ cc -O2 -Wall -pthread kuyruk.c -o kuyruk && ./kuyruk
toplam 6000003000000, beklenen 6000003000000: DOGRU
3025 ms, oge basina 504 ns; bekleme: uretici 112978, tuketici 114284
```

Altı milyon öğe; her biri yalnız bir kez alındı (toplam tam denk). 113 bin bekleme: iş parçacıkları nadiren gerçekten uyudu. Öğe başına 504 ns, çoğu çekişme: Ders 10.10'da gördüğümüz, kilidin tek bir kuyruk başına olmasının bedeli.

### Neden while?

Uyanmış bir iş parçacığı koşulun **hâlâ doğru olduğunu** varsayamaz. Üç sebep:

1. **Başkası kaptı.** A uyandırıldı ama kilidi almadan B kuyruğu boşalttı.
2. **Sahte uyanma** (spurious wakeup): POSIX, nedensiz dönüşe izin veriyor.
3. Sinyal başka bir koşul için gelmiş olabilir.

```c
/* while yerine if: uyanan is parcacigi kosulu yeniden kontrol etmezse */
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
static pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t c = PTHREAD_COND_INITIALIZER;
static int say = 0, hatali = 0;
static void *tuketici(void *a) {
    (void)a;
    for (long i = 0; i < 1000000; i++) {
        pthread_mutex_lock(&m);
        if (say == 0) pthread_cond_wait(&c, &m);         /* HATA: while olmaliydi */
        if (say == 0) hatali++;
        else say--;
        pthread_mutex_unlock(&m);
    }
    return NULL;
}
static volatile int bitti = 0;
static void *uretici(void *a) {
    (void)a;
    while (!bitti) { pthread_mutex_lock(&m); say++; pthread_cond_signal(&c); pthread_mutex_unlock(&m); }
    return NULL;
}
int main(void) {
    pthread_t t[3], u;
    pthread_create(&u, NULL, uretici, NULL);
    for (int i = 0; i < 3; i++) pthread_create(&t[i], NULL, tuketici, NULL);
    for (int i = 0; i < 3; i++) pthread_join(t[i], NULL);
    bitti = 1; pthread_join(u, NULL);
    printf("uyandiginda kuyrugu bos bulan tuketici: %d kez\n", hatali);
    return 0;
}
```

```
$ ./if_hata
uyandiginda kuyrugu bos bulan tuketici: 483 kez
```

483 kez bir tüketici `say == 0` iken "elde bir eleman varmış" gibi devam etmeye kalktı. Gerçek bir kuyrukta bu boş elemanı okumak ya da `say`'ı eksiye düşürmek demek. `while` kural, istisnasız.

### signal mi broadcast mi?

`pthread_cond_signal` en az bir bekleyeni, `pthread_cond_broadcast` hepsini uyandırır. Tüm bekleyenler aynı işi yapıyor ve her olay **bir** iş açıyorsa `signal` doğru ve verimli. Bekleyenlerin koşulları farklıysa ya da bir olay birden çok iş açıyorsa (`dur` komutu, kuyruk kapatıldı) `broadcast` gerekir; aksi takdirde birisi sonsuza kadar uyur.

---

## 3. Semafor

**Semafor** (Dijkstra, 1965), bir sayaç ve iki atomik işlem:

- `sem_wait` (P): sayaç > 0 ise azalt; 0 ise artana kadar uyu.
- `sem_post` (V): sayacı artır, bekleyen varsa birini uyandır.

Sayaç 1 olursa kilit gibi davranır; ama kilidin aksine **başka bir iş parçacığı post edebilir**. Kuyruğu iki sayaçla ifade etmek doğal:

```c
/* Ayni kuyruk semaforlarla: bos yer ve dolu yer sayaclari */
#include <pthread.h>
#include <semaphore.h>
#include <stdio.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
enum { KAP = 64, URETICI = 3, TUKETICI = 3, HER = 2000000 };
static long v[KAP]; static int bas, son;
static sem_t bos_yer, dolu_yer;
static pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
static void koy(long x) { sem_wait(&bos_yer); pthread_mutex_lock(&m); v[son] = x; son = (son + 1) % KAP; pthread_mutex_unlock(&m); sem_post(&dolu_yer); }
static long al(void) { sem_wait(&dolu_yer); pthread_mutex_lock(&m); long x = v[bas]; bas = (bas + 1) % KAP; pthread_mutex_unlock(&m); sem_post(&bos_yer); return x; }
static void *uretici(void *a) { long id = (long)a; for (long i = 1; i <= HER; i++) koy(id * 10000000 + i); return NULL; }
static void *tuketici(void *a) { long *t = a; for (long i = 0; i < HER; i++) *t += al() % 10000000; return NULL; }
int main(void) {
    sem_init(&bos_yer, 0, KAP); sem_init(&dolu_yer, 0, 0);
    pthread_t u[URETICI], t[TUKETICI]; long top[TUKETICI] = { 0 };
    double t0 = simdi();
    for (long i = 0; i < TUKETICI; i++) pthread_create(&t[i], NULL, tuketici, &top[i]);
    for (long i = 0; i < URETICI; i++) pthread_create(&u[i], NULL, uretici, (void *)(i + 1));
    for (int i = 0; i < URETICI; i++) pthread_join(u[i], NULL);
    for (int i = 0; i < TUKETICI; i++) pthread_join(t[i], NULL);
    long s = 0; for (int i = 0; i < TUKETICI; i++) s += top[i];
    long bek = (long)URETICI * (long)HER * ((long)HER + 1) / 2;
    printf("toplam %s, %.0f ms\n", s == bek ? "DOGRU" : "YANLIS", (simdi() - t0) * 1e3);
    return 0;
}
```

```
$ ./sem
toplam DOGRU, 2443 ms
```

Kod kısaldı; `say` değişkeni yok, çünkü sayaçlar onu tutuyor. Sıra önemli: `sem_wait(bos_yer)` kilit **alınmadan önce** olmalı. Tersi kilitlenmedir: kilidi tutarken kuyruk doluysa, tüketici kilidi alamadan `post` yapamaz.

| | Koşul değişkeni + mutex | Semafor |
| --- | --- | --- |
| Durum | Sizin verinizde | Sayaçta |
| `post` ile `wait` sırası | `signal` bekleyen yoksa **kaybolur** | Sayaç **hatırlar** |
| Karmaşık koşul | Her koşul ifade edilebilir | Sayaç olarak ifade edilemiyorsa zor |
| Sinyal işleyiciden | Güvenli değil | `sem_post` async-signal-safe |

Son satır pratik: Ders 10.6'daki "işleyiciden ana döngüye haber ver" sorununu `sem_post` çözer (`write` ile self-pipe'ın alternatifi).

---

## Alıştırmalar

**1** – `kuyruk.c`'deki `pthread_cond_signal` çağrılarını `pthread_mutex_unlock`'tan sonraya al. Program doğru çalışır mı? Fark ne olabilir?

**2** – Kuyruğa "kapandı" durumunu ekle: `kuyruk_kapat()` çağrılınca üreticiler hata alsın, tüketiciler kalan elemanları bitirip çıksın. Neden `broadcast` gerekiyor?

**3** – Boyut 1 olan semaforla mutex yaz. Mutex'ten farkı ne? Başka bir iş parçacığı bırakabilir mi, bunun yararı/zararı ne?

**4** – 8 iş parçacıklı bir **iş parçacığı havuzu** yaz: `havuz_ekle(f, arg)` işleri kuyruğa atıyor, `havuz_bekle()` bütün işlerin bitmesini bekliyor. Kaç koşul değişkeni gerekiyor?

**5** – Okuyan–yazan kilidi (`pthread_rwlock_t`) ne zaman tek mutex'ten iyidir? Çok okuyuculu bir hash tablosunda neden yine de kazanç düşebilir?

<details>
<summary>Cevaplar</summary>

**1** – Doğru çalışır: `signal` kilidin içinde olmak zorunda değil. Kilit dışında olunca uyandırılan iş parçacığı kilidi hemen alabilir (kilit içindeyse uyanıp hemen kilit için uyuyabilirdi; Linux'ta "wait morphing" bu kaybı azaltıyor). Tutarlılık için içeride yapmak da yaygın. Kilidin dışındayken `signal` yapmak, ancak `signal`'den önce mutex altında koşul değişmişse güvenlidir.

**2** – Yapıya `kapali` bayrağı. `koy`: `while (say == KAP && !kapali)` bekle; `kapali` ise hata dön. `al`: `while (say == 0 && !kapali)` bekle; `say == 0` ise (kapalı ve boş) "bitti" dön. `kuyruk_kapat` bayrağı kilit altında set edip **iki** koşul değişkenine `broadcast` yapar; çünkü bekleyen herkes uyanıp durumu görmeli, `signal` sadece birini uyandırırdı.

**3** – `sem_init(&s, 0, 1); sem_wait(&s); ...; sem_post(&s);`. Farkları: sahipliği yok, başka bir iş parçacığı `post` yapabilir. Bu, "bir olay" sinyali olarak işe yarıyor (boyut 0'dan başlatılmış semafor), ama kilit olarak kullanıldığında hatalı bir `post` korumayı sessizce kırar. Ayrıca mutex kilitlenme tespiti ve öncelik mirası (priority inheritance) gibi özellikler sunabilir.

**4** – İki koşul: "kuyrukta iş var" (işçiler için) ve "bütün işler bitti" (bekleyen için). Sayaç: bekleyen + çalışan iş sayısı. İşçi işi bitirip sayacı azaltır; sayaç 0 olursa ikinci koşulu `broadcast` eder. Kapatma için Alıştırma 2'deki bayrak. Bu yapı, `make -j`'nin iş sunucusu ile `clang`'in iş parçacığı havuzlarının basit hali.

**5** – Okuma çok, yazma nadirse ve kritik bölge yeterince uzunsa iyidir: okuyucular paralel. Kritik bölge çok kısaysa (hash arama: birkaç önbellek erişimi) rwlock'un kendi sayacı her okumada atomik olarak değişiyor; bu önbellek satırı çekirdekler arasında sürekli gidip geliyor ve kazanç kaybolur. Çözüm: paylaştırılmış sayaçlar, RCU (Linux çekirdeği) ya da okuyucular için kilitsiz yöntemler.

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 30–31: koşul değişkenleri, semaforlar.
- Edsger Dijkstra, "Cooperating Sequential Processes", 1965: semaforlar.
- C. A. R. Hoare, "Monitors: An Operating System Structuring Concept", *CACM*, 1974.
- Butler Lampson ve David Redell, "Experience with Processes and Monitors in Mesa", *CACM*, 1980: neden `while` (Mesa semantiği).
- `man 3 pthread_cond_wait`, `man 7 sem_overview`.

**Sıradaki ders:** Atomik işlemler. C11 `stdatomic.h`, compare-and-swap, kilitsiz sayaç.
