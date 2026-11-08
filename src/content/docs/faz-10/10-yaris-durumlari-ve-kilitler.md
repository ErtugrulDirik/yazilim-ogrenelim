---
title: "10.10 Yarış durumları ve kilitler"
description: "Sayaç yarışı deneyi: 4 iş parçacığı × 5 milyon artış, kilitsiz 20 milyon yerine 5 milyon ve yüzde 75 kayıp; x++'nın üç adımı; kritik bölge ve karşılıklı dışlama; pthread_mutex ile doğru sonuç ve 80 kat maliyet; ThreadSanitizer ile veri yarışını satırıyla bulmak; kilitlenme: ABBA senaryosu, dört koşul ve kilit sıralaması; kritik bölgenin uzunluğu ve kilitlerin ölçeklenmemesi; futex nedir."
---

Ders 10.2'de iki süreç aynı dosyanın sonuna yazınca satırlar kaybolmuştu. Ders 10.7'nin son alıştırmasında paylaşılan bir sayacın doğru çıkmayacağını söyledik. Bu derste bunu ölçüyoruz, nedenini açıklıyoruz ve ilk çözümü kuruyoruz: **kilit**.

---

## 1. Deney

```c
/* Sayac yarisi: kilitsiz, mutex'li */
#include <pthread.h>
#include <stdio.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
enum { T = 4, N = 5000000 };
static volatile long sayac = 0;
static pthread_mutex_t kilit = PTHREAD_MUTEX_INITIALIZER;
static void *kilitsiz(void *a) { (void)a; for (long i = 0; i < N; i++) sayac++; return NULL; }
static void *kilitli(void *a)  { (void)a; for (long i = 0; i < N; i++) { pthread_mutex_lock(&kilit); sayac++; pthread_mutex_unlock(&kilit); } return NULL; }
static void dene(const char *ad, void *(*f)(void *)) {
    for (int r = 0; r < 3; r++) {
        pthread_t t[T]; sayac = 0; double t0 = simdi();
        for (int i = 0; i < T; i++) pthread_create(&t[i], NULL, f, NULL);
        for (int i = 0; i < T; i++) pthread_join(t[i], NULL);
        printf("%-9s sayac = %9ld (beklenen %d, kayip %%%5.2f) %8.1f ms\n", ad, sayac, T * N, 100.0 * (T * N - sayac) / (T * N), (simdi() - t0) * 1e3);
    }
}
int main(void) { dene("kilitsiz", kilitsiz); dene("mutex", kilitli); return 0; }
```

```
$ cc -O2 -Wall -pthread yaris.c -o yaris && ./yaris
kilitsiz  sayac =   5007217 (beklenen 20000000, kayip %74.96)     10.0 ms
kilitsiz  sayac =   5200129 (beklenen 20000000, kayip %74.00)      9.9 ms
kilitsiz  sayac =   5000000 (beklenen 20000000, kayip %75.00)      9.9 ms
mutex     sayac =  20000000 (beklenen 20000000, kayip % 0.00)    798.8 ms
mutex     sayac =  20000000 (beklenen 20000000, kayip % 0.00)    799.6 ms
mutex     sayac =  20000000 (beklenen 20000000, kayip % 0.00)    798.3 ms
```

Kilitsiz sürüm 20 milyonun dörtte birini buluyor. `volatile` işe yaramadı: `volatile` derleyiciye "bu değişkeni gerçekten oku ve yaz" der (Ders 10.6), iki iş parçacığı arasında hiçbir **sıra** garantisi vermez.

---

## 2. Neden: x++ üç adım

C'de tek işlem gibi görünen `sayac++` makinede üç adım:

```
ldr x9, [sayac]     ; oku
add x9, x9, #1      ; artır
str x9, [sayac]     ; yaz
```

İki iş parçacığı aralarına girerse:

| Adım | A | B | `sayac` (bellek) |
| --- | --- | --- | --- |
| 1 | `ldr` → 5 | | 5 |
| 2 | | `ldr` → 5 | 5 |
| 3 | `add` → 6 | | 5 |
| 4 | | `add` → 6 | 5 |
| 5 | `str` 6 | | 6 |
| 6 | | `str` 6 | 6 |

İki artış oldu, sayaç bir arttı. Üstelik yukarıdaki ölçümde kayıp neredeyse tam %75, yani neredeyse her güncelleme birbirini eziyor: iş parçacıkları aynı anda koşarken her biri bir süre kendi register'ındaki değeri artırıp büyük bir değeri sayacın üzerine yazıyor; sonuçta "en son yazan kazanır" ve geri kalanların işi siliniyor.

Bu, **yarış durumu** (race condition): sonuç, olayların zamanlamasına bağlı. C11'de iki iş parçacığının aynı nesneye, en az biri yazarak ve senkronizasyon olmadan erişmesi **veri yarışı** (data race) ve **tanımsız davranış**: sadece "sayı yanlış çıkar" değil, derleyici de bu olmadığını varsayarak kodu dönüştürür (Ders 10.13).

---

## 3. Kritik bölge ve mutex

**Kritik bölge**, paylaşılan veriye dokunan ve aynı anda yalnızca bir iş parçacığının çalıştırması gereken kod parçası. **Mutex** (mutual exclusion, karşılıklı dışlama) bunu sağlar:

```c
pthread_mutex_t m = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_lock(&m);     /* serbestse al, degilse bekle */
/* kritik bolge */
pthread_mutex_unlock(&m);   /* birak, bekleyen varsa biri alir */
```

Sözleşme:

- Mutex **veriyi değil, kodu** kilitler: aynı veriye dokunan **her yer** aynı kilidi almalı. Bir yerde unutmak bütün korumayı boşa çıkarır.
- Kilidi alan bırakır; başkasının bıraktırması tanımsız.
- Aynı iş parçacığı aynı kilidi iki kez alırsa kendini bekler (normal mutex); `PTHREAD_MUTEX_RECURSIVE` bunu izin verir ama genellikle tasarım sorununun işaretidir.

Yukarıdaki tablo bedelini gösteriyor: 10 ms → 800 ms, **80 kat**. Çekişmeli (contended) durumda iş parçacıkları kilit için sürekli bekliyor. Kilit almak için yapılan işi Ders 10.12'de açacağız. Linux'ta kilit **futex** üstüne kurulu: boştaysa tamamen kullanıcı alanında tek bir atomik işlem (sistem çağrısı yok); doluysa `futex(FUTEX_WAIT)` ile çekirdekte uyuyor. Ders 10.9'daki `strace`'te `futex` çağrılarını görmüştük: `join`'in de altındaki mekanizma bu.

Ayrıca kilit yalnızca çakışmayı önlemez, **görünürlüğü** de sağlar: A'nın kilit içinde yazdığını, B kilidi aldıktan sonra görmek garantili (Ders 10.13).

---

## 4. Yarışları bulmak: ThreadSanitizer

Yarışlar test sırasında görünmeyebilir: zamanlama değişince kaybolurlar. `-fsanitize=thread` (TSan) her bellek erişimini izleyip "önce-olur" (happens-before) ilişkisi kurulmamış çakışan erişimleri raporluyor.

```c
/* Veri yarisi: ThreadSanitizer ile yakalamak */
#include <pthread.h>
#include <stdio.h>
static int sayac = 0;
static void *calis(void *a) { (void)a; for (int i = 0; i < 1000; i++) sayac++; return NULL; }
int main(void) {
    pthread_t a, b;
    pthread_create(&a, NULL, calis, NULL);
    pthread_create(&b, NULL, calis, NULL);
    pthread_join(a, NULL); pthread_join(b, NULL);
    printf("%d\n", sayac);
    return 0;
}
```

```
$ cc -g -O1 -fsanitize=thread -pthread iz.c -o iz && ./iz
==================
WARNING: ThreadSanitizer: data race (pid=11)
  Write of size 4 at 0xaaaada7d34a0 by thread T2:
    #0 calis /tmp/w/iz.c:5:76 (iz+0xf1c28) ...

  Previous write of size 4 at 0xaaaada7d34a0 by thread T1:
    #0 calis /tmp/w/iz.c:5:76 (iz+0xf1c28) ...

  Location is global 'sayac' of size 4 at 0xaaaada7d34a0 (iz+0x15734a0)

  Thread T2 (tid=15, running) created by main thread at:
    #0 pthread_create <null> (iz+0x68d38) ...
    #1 main /tmp/w/iz.c:9:5 (iz+0xf1b98) ...
...
SUMMARY: ThreadSanitizer: data race /tmp/w/iz.c:5:76 in calis
==================
ThreadSanitizer: reported 1 warnings
2000
```

Dikkat: program bu çalıştırmada **doğru sonuç** (2000) verdi; 1000 turluk bir döngü bir çekirdek süresi içinde bitti. TSan yine de yarışı buldu: değişkeni, satır ve sütunu, iki erişimi ve iş parçacıklarının nereden doğduğunu. `-g` satır bilgisi için gerekli. Çok iş parçacıklı her C kodu en az bir kez TSan altında test edilmeli (bedeli 5–15 kat yavaşlama, 5–10 kat bellek). `-fsanitize=address` ile aynı anda kullanılamaz.

---

## 5. Kilitlenme

İki kilit olunca yeni bir arıza mümkün:

```c
/* Kilitlenme: iki is parcacigi iki kilidi ters sirada alir */
#include <pthread.h>
#include <stdio.h>
#include <unistd.h>
static pthread_mutex_t A = PTHREAD_MUTEX_INITIALIZER, B = PTHREAD_MUTEX_INITIALIZER;
static int ters = 1;
static long say = 0;
static void *bir(void *x) { (void)x; for (int i = 0; i < 2000000; i++) { pthread_mutex_lock(&A); pthread_mutex_lock(&B); say++; pthread_mutex_unlock(&B); pthread_mutex_unlock(&A); } return NULL; }
static void *iki(void *x) {
    (void)x;
    for (int i = 0; i < 2000000; i++) {
        pthread_mutex_t *ilk = ters ? &B : &A, *son = ters ? &A : &B;
        pthread_mutex_lock(ilk); pthread_mutex_lock(son); say++; pthread_mutex_unlock(son); pthread_mutex_unlock(ilk);
    }
    return NULL;
}
int main(int argc, char **argv) {
    (void)argv; ters = argc == 1;
    pthread_t a, b;
    pthread_create(&a, NULL, bir, NULL); pthread_create(&b, NULL, iki, NULL);
    pthread_join(a, NULL); pthread_join(b, NULL);
    printf("bitti: %ld\n", say);
    return 0;
}
```

```
$ timeout 10 ./kilitlenme; echo $?
124
$ ./kilitlenme ayni-sira; echo $?
bitti: 4000000
0
```

A önce `A`'yı aldı ve `B`'yi bekliyor; B önce `B`'yi aldı ve `A`'yı bekliyor: hiçbiri ilerleyemez. Kilitlenmenin dört gerekli koşulu (Coffman, 1971): karşılıklı dışlama, tutup bekleme, zorla geri alınamama, dairesel bekleme. Pratikte kırılan son koşul: **kilitleri her yerde aynı global sırada al**. Sıralama adrese göre yapılabilir: `if (a > b) swap`. Tek kod farkıyla program tamamen düzeldi. Bir diğer çözüm `pthread_mutex_trylock`: başarısızsa aldıklarını bırakıp baştan dene.

TSan kilit sırası çevrimlerini de raporlar: kilitlenme o çalıştırmada gerçekten olmasa bile "bu iki kilit iki yerde ters sırada alınmış" der.

---

## 6. Kilitler ölçeklenmez

Kritik bölge sürüyorken bekleyen bütün iş parçacıkları boş duruyor. Amdahl yasasındaki (Ders 10.9) "seri kısım" tam olarak bu.

```c
/* Kritik bolge uzunlugu ve is parcacigi sayisi: kilit olceklenmez */
#include <pthread.h>
#include <stdio.h>
#include <time.h>
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }
static pthread_mutex_t k = PTHREAD_MUTEX_INITIALIZER;
static volatile long s;
enum { TOPLAM = 8000000 };
static int isci;
static inline void is_yap(int n) { for (volatile int i = 0; i < n; i++) { } }
static int ic, dis;
static void *calis(void *a) { (void)a; for (long i = 0; i < TOPLAM / isci; i++) { pthread_mutex_lock(&k); is_yap(ic); s++; pthread_mutex_unlock(&k); is_yap(dis); } return NULL; }
int main(void) {
    int oz[][2] = { { 0, 0 }, { 0, 100 }, { 50, 50 } };
    const char *ad[] = { "yalniz kritik bolge", "ic 0, dis 100", "ic 50, dis 50" };
    for (int z = 0; z < 3; z++) {
        ic = oz[z][0]; dis = oz[z][1];
        printf("%s\n", ad[z]);
        for (int T = 1; T <= 8; T *= 2) {
            isci = T; pthread_t t[8]; double t0 = simdi();
            for (int i = 0; i < T; i++) pthread_create(&t[i], NULL, calis, NULL);
            for (int i = 0; i < T; i++) pthread_join(t[i], NULL);
            printf("  %d is parcacigi: %7.1f ms\n", T, (simdi() - t0) * 1e3);
        }
    }
    return 0;
}
```

```
$ ./yuk
yalniz kritik bolge
  1 is parcacigi:    55.7 ms
  2 is parcacigi:   242.3 ms
  4 is parcacigi:   315.4 ms
  8 is parcacigi:   349.0 ms
ic 0, dis 100
  1 is parcacigi:   322.9 ms
  2 is parcacigi:   351.1 ms
  4 is parcacigi:   498.1 ms
  8 is parcacigi:   822.9 ms
ic 50, dis 50
  1 is parcacigi:   607.7 ms
  2 is parcacigi:   963.1 ms
  4 is parcacigi:   883.0 ms
  8 is parcacigi:  1816.4 ms
```

Toplam iş sabit, daha çok iş parçacığı **yavaşlatıyor**: 1'den 8'e kritik bölgede 6 kat, dışarıda 100 boş tur olsa bile 2.5 kat. Hiçbir ek çekirdek yardımcı olmadı; çünkü kilit el değiştirirken önbellek satırı çekirdekler arasında gidip geliyor (Ders 7.25) ve uyandırmanın maliyeti ödeniyor. "Dış iş" arttıkça çekişme azalıyor, ama bu ölçekte kazanç görünmüyor.

İlkeler:

- Kritik bölgeyi **kısa tut**: pahalı işi (G/Ç, hesaplama) kilidin dışına çıkar.
- **İnce taneli** kilit: tek global kilit yerine yapı başına kilit (bir hash tablosunda kova başına, Alıştırma 3).
- Mümkünse **paylaşma**: iş parçacığı başına ayrı sayaç tutup sonunda topla. En ucuz senkronizasyon, gereksiz olanıdır.

---

## Alıştırmalar

**1** – Ders 10.2'deki `lseek` + `write` deneyini iş parçacıklarıyla yeniden yap ve bir mutex ile düzelt. `O_APPEND` çözümüne göre ne kaybettin?

**2** – Bir banka hesabı yapısında `transfer(a, b, miktar)` fonksiyonu iki hesabı kilitliyor. Kilitlenmeyi önlemek için adres sıralaması kullan. `a == b` durumunda ne yapmalısın?

**3** – 1024 kovalı bir hash tablosuna eş zamanlı ekleme yapan iki sürüm yaz: tek global kilit ve kova başına kilit. 8 iş parçacığıyla ölç. Kova başına kilit neden yine de mükemmel ölçeklenmez?

**4** – Bir mutex'i `free`'lenmiş bir yapının içinden kullanmak, ya da bir kilidi başka bir iş parçacığında bırakmak ne yapar? `PTHREAD_MUTEX_ERRORCHECK` bu tür hataların hangilerini yakalar?

**5** – Bir kritik bölgede `printf` yapmak neden iyi bir fikir değildir? Ders 10.3'teki stdio kilidi ile birleştirince hangi kilit sırası ortaya çıkıyor?

<details>
<summary>Cevaplar</summary>

**1** – `lseek` + `write` çiftini mutex ile sarmak aynı süreçte sonuç verir, boyut 64 000 bayt olur. Ama (a) sadece bu sürecin iş parçacıkları için geçerli: başka süreç hâlâ araya girebilir; (b) kilit tutulurken diske gidiliyor, bütün iş parçacıkları sırada; (c) kod uzuyor. `O_APPEND` ise atomikliği çekirdeğe yaptırıyor, süreçler arası da çalışıyor (Ders 10.2'deki kural).

**2** – `first = a < b ? a : b; second = a < b ? b : a;` ile sıralı al. `a == b` ise aynı kilidi iki kez alırdı (kendi kendini kilitleme): önce kontrol edip tek kilit al ya da işlem yapma.

**3** – Global kilitte 8 iş parçacığı bir kilit etrafında kuyruklanır, ölçeklenmez. Kova başına kilitte çakışma $1/1024$'e düşer, hızlanma önemli olur. Yine de: tabloyu büyütme (rehash) bütün kovaları kilitlemek gerektirir; bellek bant genişliği ve kilit değişkenlerinin aynı önbellek satırına düşmesi (yanlış paylaşım, Faz 11) sınır koyar; `malloc` da içeride kilitliyor.

**4** – `free`'lenmiş bellek üzerinde mutex: tanımsız davranış, Ders 4.23'teki kullanım-sonrası-serbest. Başka iş parçacığından bırakma: normal mutex'te tanımsız, `PTHREAD_MUTEX_ERRORCHECK` ile `EPERM` döner; aynı iş parçacığının iki kez almasını `EDEADLK` ile bildirir. Serbest bırakılmış bellek kullanımını yakalamaz (onun için ASan).

**5** – `printf` çıktıya gittiği için yavaş olabilir (terminal, boru dolu) ve kilit tutulurken herkes bekler. stdio'nun kendi kilidi var (Ders 10.3): `flockfile`. Kod iki yerde farklı sırada "benim kilit, stdio kilidi" alırsa ABBA kilitlenmesi mümkün. Basit kural: kilit içinde bilinmeyen bir kodu çağırma.

</details>

---

## Kaynaklar

- Remzi ve Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 28–29, 32: kilitler, eşzamanlı veri yapıları, yaygın hatalar.
- Edward Coffman, Melanie Elphick ve Arie Shoshani, "System Deadlocks", *ACM Computing Surveys*, 1971.
- Konstantin Serebryany ve Timur Iskhodzhanov, "ThreadSanitizer: data race detection in practice", *WBIA*, 2009.
- Ulrich Drepper, "Futexes Are Tricky", 2011: Linux futex'inin doğru kullanımı.
- `man 3 pthread_mutex_lock`, `man 2 futex`.

**Sıradaki ders:** Koşul değişkenleri ve semaforlar. Üretici–tüketici problemi.
