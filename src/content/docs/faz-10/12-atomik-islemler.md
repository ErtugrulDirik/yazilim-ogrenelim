---
title: "10.12 Atomik işlemler"
description: "C11 stdatomic.h: atomik tipler, fetch_add, compare-and-swap; dört iş parçacığında sayaç karşılaştırması (relaxed 7.8 ns, seq_cst 16.4 ns, CAS 46.8 ns, mutex 43 ns); arm64'te outline atomics ve LSE komutları ldadd, casal; kendi spinlock'umuz: TAS ve TTAS, 8 iş parçacığında spin'in mutex'e kaybetmesi; Treiber kilitsiz yığını ve 8 milyon eleman; ABA problemi."
---

Ders 10.10'da kilit, sayacı doğru yaptı ama 80 kat yavaşlattı. Oysa kilidin kendisi de bir yerden başlıyor: bir bayrağı "bir iş parçacığı değiştirebilecek şekilde" güncelleyen bir **donanım** komutuna. Bu ders o katmana iniyor: `stdatomic.h`. Derleyicilerin referans sayıları, eşzamanlı çalışma zamanları ve `shared_ptr` (Faz 13) bu araçlarla yazılıyor.

---

## 1. stdatomic.h

`_Atomic` nitelikli (ya da `atomic_int`, `atomic_long`) bir değişkene yapılan işlemler **bölünmez**: başka bir iş parçacığı "yarım" görmez ve veri yarışı oluşmaz.

```c
#include <stdatomic.h>
atomic_long a = 0;

atomic_fetch_add(&a, 1);                    /* a += 1, onceki degeri dondurur */
atomic_store(&a, 5);
long v = atomic_load(&a);
long e = 5;
_Bool ok = atomic_compare_exchange_strong(&a, &e, 7);
```

Bir de bellek sıralamalı `_explicit` sürümleri var (Ders 10.13).

**Compare-and-swap** (CAS), bütün kilitsiz algoritmaların temeli: "`a` hâlâ `e`'ye eşitse `y` yap, atomik olarak; değilse `e`'ye `a`'nın güncel değerini koy." `_weak` sürümü nadiren sebepsiz başarısız olabilir ama döngülerde daha hızlıdır (arm64 gibi LL/SC mimarilerinde).

### Maliyet

```c
/* Atomik sayac: her yontemin 4 is parcacigi altindaki bedeli */
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
enum { N = 5000000, T = 4 };
static atomic_long a; static volatile long v; static pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
static void *f_kilitsiz(void *x) { (void)x; for (long i = 0; i < N; i++) v++; return NULL; }
static void *f_relaxed(void *x) { (void)x; for (long i = 0; i < N; i++) atomic_fetch_add_explicit(&a, 1, memory_order_relaxed); return NULL; }
static void *f_seq(void *x) { (void)x; for (long i = 0; i < N; i++) atomic_fetch_add(&a, 1); return NULL; }
static void *f_cas(void *x) { (void)x; for (long i = 0; i < N; i++) { long e = atomic_load_explicit(&a, memory_order_relaxed); while (!atomic_compare_exchange_weak(&a, &e, e + 1)) { } } return NULL; }
static void *f_mutex(void *x) { (void)x; for (long i = 0; i < N; i++) { pthread_mutex_lock(&m); v++; pthread_mutex_unlock(&m); } return NULL; }
static void dene(const char *ad, void *(*f)(void *), int ta) {
    pthread_t t[T]; a = 0; v = 0; double t0 = simdi();
    for (int i = 0; i < ta; i++) pthread_create(&t[i], NULL, f, NULL);
    for (int i = 0; i < ta; i++) pthread_join(t[i], NULL);
    printf("%-22s %d is: sonuc %9ld, %6.1f ms, artis basina %6.1f ns\n", ad, ta, f == f_mutex || f == f_kilitsiz ? (long)v : (long)a, (simdi() - t0) * 1e3, (simdi() - t0) * 1e9 / (N * ta));
}
int main(void) {
    int ts[] = { 1, 4 };
    for (int k = 0; k < 2; k++) {
        dene("volatile (yanlis)", f_kilitsiz, ts[k]); dene("fetch_add relaxed", f_relaxed, ts[k]);
        dene("fetch_add seq_cst", f_seq, ts[k]); dene("CAS dongusu", f_cas, ts[k]); dene("mutex", f_mutex, ts[k]);
    }
    return 0;
}
```

```
$ cc -O2 -Wall -pthread sayac.c -o sayac && ./sayac
volatile (yanlis)      1 is: sonuc   5000000,    1.7 ms, artis basina    0.3 ns
fetch_add relaxed      1 is: sonuc   5000000,    9.5 ms, artis basina    1.9 ns
fetch_add seq_cst      1 is: sonuc   5000000,   20.1 ms, artis basina    4.0 ns
CAS dongusu            1 is: sonuc   5000000,   19.7 ms, artis basina    3.9 ns
mutex                  1 is: sonuc   5000000,   34.2 ms, artis basina    6.8 ns
volatile (yanlis)      4 is: sonuc   5038376,   10.0 ms, artis basina    0.5 ns
fetch_add relaxed      4 is: sonuc  20000000,  156.7 ms, artis basina    7.8 ns
fetch_add seq_cst      4 is: sonuc  20000000,  327.5 ms, artis basina   16.4 ns
CAS dongusu            4 is: sonuc  20000000,  935.2 ms, artis basina   46.8 ns
mutex                  4 is: sonuc  20000000,  859.8 ms, artis basina   43.0 ns
```

Okunması gereken üç nokta:

- Atomik işlemler bile **çekişmesiz** de normal `++`'dan pahalı (0.3 → 1.9 ns), çünkü işlemciye "bu satırı kendime özel al" dedirtiyor.
- **Çekişme fiyatı belirliyor**: 4 iş parçacığında relaxed 1.9 → 7.8 ns. Önbellek satırı çekirdekler arasında sürekli taşınıyor (Ders 7.25).
- **CAS döngüsü çekişmede mutex kadar kötü.** Bir yeniden deneme, diğerlerinin kazandığı anlamına geliyor. Bu yüzden `fetch_add` doğrudan varsa CAS döngüsü yazılmaz. Kilitsiz olmak hızlı olmak demek değil.

### Makinede neye dönüşüyor

```c
#include <stdatomic.h>
atomic_long a;
long artir(void) { return atomic_fetch_add_explicit(&a, 1, memory_order_relaxed); }
long dene_cas(long e, long y) { atomic_compare_exchange_strong(&a, &e, y); return e; }
```

```
$ cc -O2 -c topla.c && objdump -d topla.o        # varsayilan arm64
0000000000000000 <artir>:
   ...
  10:	52800020 	mov	w0, #0x1
  14:	94000000 	bl	0 <__aarch64_ldadd8_relax>
   ...
$ cc -O2 -march=armv8.1-a -c topla.c -o t2.o && objdump -d t2.o
0000000000000000 <artir>:
   0:	52800028 	mov	w8, #0x1
   4:	90000009 	adrp	x9, 0 <artir>
   8:	91000129 	add	x9, x9, #0x0
   c:	f8280120 	ldadd	x8, x0, [x9]
  10:	d65f03c0 	ret
0000000000000014 <dene_cas>:
  14:	90000008 	adrp	x8, 0 <artir>
  18:	91000108 	add	x8, x8, #0x0
  1c:	c8e0fd01 	casal	x0, x1, [x8]
  20:	d65f03c0 	ret
```

Temel arm64 (ARMv8.0) komut kümesinde bileşik atomik yok: yalnızca `ldxr`/`stxr` çifti (LL/SC, yük-bağla/koşullu sakla) var, yani derleyici bir yardımcı fonksiyon çağırıyor; bu yardımcı (`outline atomics`), çalışırken donanıma bakıp ARMv8.1'in **LSE** komutunu (`ldadd`, `casal`) ya da eski LL/SC döngüsünü seçiyor. x86-64'te karşılığı `lock xadd` ve `lock cmpxchg`; `lock` öneki ve tek komut. Bu, Ders 7.23'teki sırasız yürütme tarafında da bir sıralama noktası oluşturuyor (Ders 10.13).

---

## 2. Kendi kilidimiz

`test-and-set`: "bayrağı 1 yap, eski değerini söyle". Eski 0'sa kilidi aldık.

```c
/* Spinlock: test-and-set ve test-and-test-and-set */
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
enum { N = 2000000 };
typedef struct { atomic_flag f; } TAS;
static TAS tas = { ATOMIC_FLAG_INIT };
static void tas_al(TAS *k) { while (atomic_flag_test_and_set_explicit(&k->f, memory_order_acquire)) { } }
static void tas_birak(TAS *k) { atomic_flag_clear_explicit(&k->f, memory_order_release); }
static atomic_int tt;
static void ttas_al(void) { for (;;) { if (!atomic_exchange_explicit(&tt, 1, memory_order_acquire)) return; while (atomic_load_explicit(&tt, memory_order_relaxed)) { } } }
static void ttas_birak(void) { atomic_store_explicit(&tt, 0, memory_order_release); }
static pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
static long s;
static void *a1(void *x) { (void)x; for (long i = 0; i < N; i++) { tas_al(&tas); s++; tas_birak(&tas); } return NULL; }
static void *a2(void *x) { (void)x; for (long i = 0; i < N; i++) { ttas_al(); s++; ttas_birak(); } return NULL; }
static void *a3(void *x) { (void)x; for (long i = 0; i < N; i++) { pthread_mutex_lock(&m); s++; pthread_mutex_unlock(&m); } return NULL; }
static void dene(const char *ad, void *(*f)(void *), int T) {
    pthread_t t[8]; s = 0; double t0 = simdi();
    for (int i = 0; i < T; i++) pthread_create(&t[i], NULL, f, NULL);
    for (int i = 0; i < T; i++) pthread_join(t[i], NULL);
    printf("%-8s %d is: %8.1f ms (sonuc %s)\n", ad, T, (simdi() - t0) * 1e3, s == (long)N * T ? "dogru" : "YANLIS");
}
int main(void) { int ts[] = { 1, 2, 4, 8 }; for (int k = 0; k < 4; k++) { dene("TAS", a1, ts[k]); dene("TTAS", a2, ts[k]); dene("mutex", a3, ts[k]); } return 0; }
```

```
$ ./kilit
TAS      1 is:      9.4 ms (sonuc dogru)
TTAS     1 is:      9.1 ms (sonuc dogru)
mutex    1 is:     13.8 ms (sonuc dogru)
TAS      2 is:    133.1 ms (sonuc dogru)
TTAS     2 is:     76.9 ms (sonuc dogru)
mutex    2 is:    239.2 ms (sonuc dogru)
TAS      4 is:    478.1 ms (sonuc dogru)
TTAS     4 is:    229.4 ms (sonuc dogru)
mutex    4 is:    315.9 ms (sonuc dogru)
TAS      8 is:   3697.1 ms (sonuc dogru)
TTAS     8 is:   1682.8 ms (sonuc dogru)
mutex    8 is:    884.8 ms (sonuc dogru)
```

- **TAS** bekleme döngüsünde sürekli **yazıyor**: her deneme önbellek satırını sahipleniyor, diğer çekirdeklerin kopyalarını geçersiz kılıyor.
- **TTAS** (test-and-test-and-set) döngüsünde **sadece okuyor**; okumalar paylaşımlı önbellekten geliyor, satır dolaşmıyor. Kilit boşalınca yazmayı deniyor. İki kat civarı hızlanıyor.
- 8 iş parçacığında (yani çekirdek sayısında) **mutex kazanıyor**: uyuyanlar işlemciyi boşaltıyor, spin'cilerse kilit sahibi çekirdekten atılırsa ve onlar çekirdeklerde dönüyorlarsa zamanı boşa harcıyor. `pthread_mutex` çok kısa spin + `futex` birleşimi.

Sonuç: Spinlock çok kısa kritik bölgeler için, ve iş parçacığı sayısı çekirdek sayısının altındayken, mantıklı. Genel amaçlı kilit olarak kendi spinlock'unu yazmak hemen hemen hep kötü fikir.

---

## 3. Kilitsiz yığın

CAS ile kilitsiz veri yapıları yazılabilir. En küçük örnek **Treiber yığını** (1986):

```c
/* Kilitsiz (Treiber) yigini; dugumler geri kullanilmaz, bu yuzden ABA yok */
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
enum { T = 4, N = 2000000 };
typedef struct Dugum { long v; struct Dugum *sonraki; } Dugum;
static _Atomic(Dugum *) tepe;
static atomic_long yeniden;
static void it(Dugum *d) {
    Dugum *e = atomic_load_explicit(&tepe, memory_order_relaxed);
    do { d->sonraki = e; } while (!atomic_compare_exchange_weak_explicit(&tepe, &e, d, memory_order_release, memory_order_relaxed) && (atomic_fetch_add_explicit(&yeniden, 1, memory_order_relaxed), 1));
}
static Dugum *cek(void) {
    Dugum *e = atomic_load_explicit(&tepe, memory_order_acquire);
    while (e && !atomic_compare_exchange_weak_explicit(&tepe, &e, e->sonraki, memory_order_acquire, memory_order_acquire)) { }
    return e;
}
static Dugum *havuz;
static void *itici(void *a) { long id = (long)a; for (long i = 0; i < N; i++) { Dugum *d = &havuz[id * N + i]; d->v = id * N + i; it(d); } return NULL; }
int main(void) {
    havuz = malloc(sizeof(Dugum) * T * N);
    pthread_t t[T];
    for (long i = 0; i < T; i++) pthread_create(&t[i], NULL, itici, (void *)i);
    for (int i = 0; i < T; i++) pthread_join(t[i], NULL);
    long say = 0; unsigned char *g = calloc(T * N, 1); int hata = 0;
    for (Dugum *d; (d = cek()); say++) { if (g[d->v]) hata++; g[d->v] = 1; }
    printf("%d eleman itildi, %ld cekildi, tekrar %d, CAS yeniden deneme %ld\n", T * N, say, hata, atomic_load(&yeniden));
    return 0;
}
```

```
$ ./yigin
8000000 eleman itildi, 8000000 cekildi, tekrar 0, CAS yeniden deneme 8173073
```

Hiçbir eleman kaybolmadı, hiçbiri iki kez çıkmadı. Yeniden deneme sayısı toplam itme kadar: ortalama her eleman için bir kere başkasına yenildik. Bu, kilitsiz (lock-free) tanımının özü: birisi yeniliyorsa, başkası **kazanmıştır**; sistem bir bütün olarak ilerliyor.

### ABA

Bu kod yalnızca itiyor; boşaltma tek iş parçacıklı ve düğümler yeniden kullanılmıyor. `cek` birden çok iş parçacığından çağrılsaydı ve düğümler geri dönüştürülseydi şu olabilirdi:

1. A `tepe` = `X` görüyor, `X->sonraki` = `Y` okuyor. CAS'tan önce askıya alınıyor.
2. B: `X`'i çekip siliyor, `Y`'yi çekip siliyor. `malloc` aynı adresi veriyor: yeni düğüm yine `X` adresinde, itiyor.
3. A uyanıyor: "`tepe` hâlâ `X`" (A → B → A): CAS başarılı, `tepe = Y`. `Y` çoktan serbest bırakılmış!

CAS "değişmedi" diye kontrol eder, oysa **değişip eski haline dönmüş**. Çözümler: işaretçinin yanına bir sürüm sayacı (çift genişlikte CAS), tehlike işaretçileri (hazard pointers), RCU, ya da düğümleri hiç yeniden kullanmamak (yukarıdaki gibi). `free` ile geri vermek de ayrı bir sorun: başkası hâlâ okuyor olabilir. **Kilitsiz kodun asıl zorluğu bellek geri kazanımı.** Bu yüzden kilitsiz veri yapısı yazmak uzman işidir; ölçmeden yazılmaz.

---

## Alıştırmalar

**1** – Ders 10.10'daki sayacı `atomic_long` yaparak düzelt. `sayac++` yazmak atomik midir? `sayac = sayac + 1` peki?

**2** – Bir `atomic_int` üzerinde "en büyüğü güncelle" (`atomic_max`) fonksiyonunu CAS ile yaz. Karşılaştıracağın değer zaten büyükse döngüden nasıl çıkarsın?

**3** – Referans sayımlı bir nesne için `ref_al` ve `ref_birak` yaz. `birak` sayaç 0'a inince nesneyi serbest bıraksın. İki iş parçacığının aynı anda son iki referansı bırakması ne olur?

**4** – `sayac.c`'deki ölçümde iş parçacığı sayısını 1, 2, 4, 8 yap; relaxed `fetch_add` için tablo oluştur. Kazanç neden azalıyor? İş parçacığı başına sayaç kullansaydın ne olurdu?

**5** – Spinlock için `tas_al` döngüsünün içine `__builtin_arm_yield()` ya da x86'daki `pause` karşılığını ekle. İşlemciye neyi söylüyor? Çekirdek sayısının üzerindeki iş parçacığında spinlock'u bir de `sched_yield` ile dene.

<details>
<summary>Cevaplar</summary>

**1** – `_Atomic` bir değişken üzerinde `sayac++` atomiktir: C11 buna `atomic_fetch_add` semantiği verir (seq_cst). `sayac = sayac + 1` ise iki ayrı işlem: atomik okuma, sonra atomik yazma; arada başkası girebilir. Yarış devam eder (veri yarışı olmasa da mantık yarışı).

**2** – 

```c
void atomic_max(atomic_int *a, int v) {
    int e = atomic_load_explicit(a, memory_order_relaxed);
    while (e < v && !atomic_compare_exchange_weak_explicit(a, &e, v, memory_order_relaxed, memory_order_relaxed)) { }
}
```

Başarısız CAS, `e`'yi güncel değerle doldurur; `e >= v` olunca döngü koşulu biter. Boşa yazma yapılmaz.

**3** – `ref_al`: `atomic_fetch_add_explicit(&s, 1, relaxed)`. `ref_birak`: `if (atomic_fetch_sub_explicit(&s, 1, release) == 1) { atomic_thread_fence(acquire); free(p); }`. `fetch_sub` önceki değeri döndürdüğü için yalnızca **bir** iş parçacığı 1 görür: tam olarak o serbest bırakır. Boost ve Rust'un `Arc`'ı aynı sırayı kullanıyor (nedeni Ders 10.13'te).

**4** – Çekirdek sayısı arttıkça önbellek satırı trafiği artıyor, satır başına bir yazma. İş parçacığı başına sayaç (ayrı satırlarda, `_Alignas(64)`) ölçeklenir: her sayaç tek bir çekirdekte kalıyor, okuyan taraf hepsini toplar. Çekirdekteki `percpu` sayaçlarının yöntemi. Yanlış satırlara düşerse fayda kaybolur (Faz 11).

**5** – arm64'te `yield` ve x86-64'te `pause`, "bir döngüde bekliyorum" ipucu: işlemci boru hattını hafifletiyor, bazı sistemlerde SMT komşusuna kaynak bırakıyor. Çekirdek sayısının üstündeki iş parçacığıyla spinlock felaketi: kilit sahibi çalışmıyorken bekleyenler zaman dilimlerini yakıyor. `sched_yield` bunu biraz düzeltir ama çekirdeğe girmek pahalı; `futex` kullanan mutex'in hâlâ önde olmasının nedeni bu.

</details>

---

## Kaynaklar

- ISO/IEC 9899:2011 (C11), §7.17: `<stdatomic.h>`.
- Maurice Herlihy ve Nir Shavit, *The Art of Multiprocessor Programming* (2. baskı), Bölüm 7, 11: spinlock'lar ve kilitsiz yığın.
- R. Kent Treiber, "Systems Programming: Coping with Parallelism", IBM Research, 1986.
- Maged Michael, "Hazard Pointers: Safe Memory Reclamation for Lock-Free Objects", *IEEE TPDS*, 2004.
- Paul McKenney, *Is Parallel Programming Hard, And, If So, What Can You Do About It?*: önbellek davranışı ve bellek geri kazanımı.
- `man 7 futex`, `man 3 pthread_spin_lock`.

**Sıradaki ders:** Bellek modeli. Sıralama garantileri, derleyici ve CPU yeniden sıralaması.
