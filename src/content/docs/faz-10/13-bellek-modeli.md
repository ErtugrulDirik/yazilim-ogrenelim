---
title: "10.13 Bellek modeli"
description: "Yazdığın sıra çalışan sıra değil: derleyici yeniden sıralaması (a = 1 silindi, while (!hazir) kayboldu) ve işlemci yeniden sıralaması; C11 bellek sıraları relaxed, acquire, release, acq_rel, seq_cst; happens-before; mesaj geçirme kalıbı ve üretilen stlr/ldar komutları; arm64'te litmus testleri: SB relaxed 5 milyonda 2 milyon, ldapr ile yüzde 98.7, seq_cst ile sıfır; x86-TSO ile karşılaştırma."
---

Ders 10.10'da yarışların **tanımsız davranış** olduğunu söyledik; Ders 10.12'de atomik işlemlere `_explicit` bir parametre gördük. Bu derste neden her iki kuralın da var olduğunu görüyoruz. Tek cümleyle: **yazdığın sıra çalışan sıra değil.** Tek iş parçacığında bunu fark etmezsin, çünkü derleyici ve işlemci sonucu değiştirmeyecek şekilde yeniden sıralıyor. İkinci bir iş parçacığı, ara durumları görebiliyor.

Bu konu, bir derleyici yazarının tam da **kendi yaptığı işin** kuralı: Faz 16'daki hangi optimizasyonun geçerli olduğu buradaki modele bağlı.

---

## 1. Derleyici yeniden sıralar

```c
int a, b;
void yaz(void) { a = 1; b = 1; a = 2; }
int oku_iki(int *p) { int x = *p; int y = *p; return x + y; }
extern int hazir, veri;
int bekle(void) { while (!hazir) { } return veri; }
```

```
$ cc -O2 -S sira.c -o -
yaz:
	adrp	x8, b
	mov	w9, #1
	adrp	x10, a
	mov	w11, #2
	str	w9, [x8, :lo12:b]
	str	w11, [x10, :lo12:a]
	ret
oku_iki:
	ldr	w8, [x0]
	lsl	w0, w8, #1
	ret
bekle:
	adrp	x8, :got:veri
	ldr	x8, [x8, :got_lo12:veri]
	ldr	w0, [x8]
	ret
```

- `yaz`: `a = 1` **silindi**. Başka kimse görmüyorsa zaten boşa.
- `oku_iki`: iki okuma **tek okuma** oldu.
- `bekle`: `while (!hazir)` döngüsü **tamamen kayboldu**. Derleyici hiç başka iş parçacığı olmadığını varsaydı; döngü de yan etkisiz. C11 "ilerleme" kurallarıyla, koşulun sonlanacağını varsayabilir; yani doğrudan `veri`'yi okuyor.

Bu dönüşümlerin hepsi tek iş parçacığı için geçerli. İşte veri yarışını tanımsız yapmanın sebebi: "veri yarışı yok" varsayımı optimizasyonu mümkün kılıyor. `volatile` ise yalnız derleyici tarafını durdurur, çekirdekler arasında hiçbir garanti vermez.

---

## 2. İşlemci de yeniden sıralar

Derleyici sıraya dokunmasa bile, modern işlemciler (Ders 7.23) kaydı **depo tamponuna** (store buffer) atıp yoluna devam ediyor; okumalar yazmaları geçebiliyor. Hangi yeniden sıralamalara izin verildiği mimarinin **bellek modeli**:

| Yer değiştirebilen çift (önce → sonra) | x86-64 (TSO) | arm64 (zayıf) |
| --- | --- | --- |
| Okuma → Okuma | Hayır | **Evet** |
| Okuma → Yazma | Hayır | **Evet** |
| Yazma → Yazma | Hayır | **Evet** |
| Yazma → Okuma | **Evet** (depo tamponu) | **Evet** |

x86 "kibar" olduğu için çoğu kilitsiz hata x86'da görünmez ve kod arm'a taşınınca ortaya çıkar. C11 ise bu farkları kapatıp **taşınabilir** bir model tanımlar.

### Litmus testleri

Bir bellek modelini test etmenin yolu küçük "litmus" programları. İki klasik:

**MP (mesaj geçirme)**. A: `x = 1; y = 1;`. B: `r1 = y; r2 = x;`. Soru: `r1 == 1 && r2 == 0` görülür mü? Yani bayrağı gördü ama veri eski mi?

**SB (store buffering)**. A: `x = 1; r1 = y;`. B: `y = 1; r2 = x;`. Soru: `r1 == 0 && r2 == 0` görülür mü? Sezgisel olarak imkânsız (biri önce yazmış olmalı).

```c
/* Litmus testleri: MP (mesaj gecirme) ve SB (depo tamponu) */
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>
enum { TUR = 5000000 };
#define SATIR _Alignas(256)              /* x ve y ayri onbellek satirlarinda */
static SATIR atomic_int x;
static SATIR atomic_int y;
static SATIR atomic_int gen;
static atomic_int sayac;
static SATIR int r1;
static SATIR int r2;
static memory_order mo_y, mo_o;          /* yazma, okuma */
static int test;                          /* 0: MP, 1: SB */

static void engel(void) {                 /* iki is parcacigi da gelene kadar bekle */
    int g = atomic_load_explicit(&gen, memory_order_acquire);
    if (atomic_fetch_add_explicit(&sayac, 1, memory_order_acq_rel) == 1) {
        atomic_store_explicit(&sayac, 0, memory_order_relaxed);
        atomic_store_explicit(&gen, g + 1, memory_order_release);
    } else while (atomic_load_explicit(&gen, memory_order_acquire) == g) { }
}
static inline void gecik(unsigned r) { for (volatile unsigned i = 0; i < (r & 15); i++) { } }
static long gozlem;
static volatile int cop;

static void *a(void *z) {
    (void)z; unsigned r = 1;
    for (int i = 0; i < TUR; i++) {
        atomic_store_explicit(&x, 0, memory_order_relaxed);
        atomic_store_explicit(&y, 0, memory_order_relaxed);
        engel();
        atomic_store_explicit(&y, 0, memory_order_relaxed);    /* y satiri bu cekirdekte kalsin */
        engel();
        r = r * 1103515245 + 12345; gecik(r >> 16);
        if (test == 0) { atomic_store_explicit(&x, 1, memory_order_relaxed); atomic_store_explicit(&y, 1, mo_y); }
        else { atomic_store_explicit(&x, 1, mo_y); r1 = atomic_load_explicit(&y, mo_o); }
        engel();
        if (test == 0 ? (r1 == 1 && r2 == 0) : (r1 == 0 && r2 == 0)) gozlem++;
    }
    return NULL;
}
static void *b(void *z) {
    (void)z; unsigned r = 7;
    for (int i = 0; i < TUR; i++) {
        engel();
        cop = atomic_load_explicit(&x, memory_order_relaxed);  /* x satiri paylasimli olsun: yazma gecikir */
        engel();
        r = r * 1103515245 + 12345; gecik(r >> 16);
        if (test == 0) { r1 = atomic_load_explicit(&y, mo_o); r2 = atomic_load_explicit(&x, memory_order_relaxed); }
        else { atomic_store_explicit(&y, 1, mo_y); r2 = atomic_load_explicit(&x, mo_o); }
        engel();
    }
    return NULL;
}
static void dene(int t, const char *ad, memory_order my, memory_order mo) {
    test = t; mo_y = my; mo_o = mo; gozlem = 0;
    pthread_t p, q;
    pthread_create(&p, NULL, a, NULL); pthread_create(&q, NULL, b, NULL);
    pthread_join(p, NULL); pthread_join(q, NULL);
    printf("%-3s %-16s sasirtici sonuc: %8ld / %d\n", t == 0 ? "MP" : "SB", ad, gozlem, TUR);
}
int main(void) {
    dene(0, "relaxed", memory_order_relaxed, memory_order_relaxed);
    dene(0, "release/acquire", memory_order_release, memory_order_acquire);
    dene(1, "relaxed", memory_order_relaxed, memory_order_relaxed);
    dene(1, "release/acquire", memory_order_release, memory_order_acquire);
    dene(1, "seq_cst", memory_order_seq_cst, memory_order_seq_cst);
    return 0;
}
```

```
$ cc -O2 -Wall -pthread litmus.c -o litmus && ./litmus
MP  relaxed          sasirtici sonuc:        0 / 5000000
MP  release/acquire  sasirtici sonuc:        0 / 5000000
SB  relaxed          sasirtici sonuc:  1262856 / 5000000
SB  release/acquire  sasirtici sonuc:        0 / 5000000
SB  seq_cst          sasirtici sonuc:        0 / 5000000
$ cc -O2 -march=armv8.3-a -pthread litmus.c -o l2 && ./l2
MP  relaxed          sasirtici sonuc:        0 / 5000000
MP  release/acquire  sasirtici sonuc:        0 / 5000000
SB  relaxed          sasirtici sonuc:   501719 / 5000000
SB  release/acquire  sasirtici sonuc:  4933793 / 5000000
SB  seq_cst          sasirtici sonuc:        0 / 5000000
```

- **SB relaxed**: "imkânsız" sonuç dört turda bir görüldü (başka bir çalıştırmada beş turda iki). Her iki iş parçacığının yazması da kendi depo tamponundayken öbürü okumuş.
- **SB release/acquire**, varsayılan derlemede sıfır, ama `-march=armv8.3-a` ile **turların %98.7'si**! Değişen tek şey: ARMv8.3'ün daha hafif `ldapr` komutu seçildi. Standart bu sonucu **baştan beri izin veriyordu**. Varsayılan derlemede kullanılan `ldar` komutu, standardın istediğinden güçlü olduğu için görülmemişti. Yani "testlerimde hiç görmedim" programın doğru olduğunu **kanıtlamaz**; başka bir derleyici bayrağıyla düşebilir.
- **seq_cst**: sıfır, her zaman. Standardın garantisi.
- **MP relaxed**: 5 milyon denemede sıfır, oysa arm64 mimarisi ve C11 buna izin veriyor. Bu test bu çekirdekte tetikleyemedi. Görmemiş olmak "güvenli" demek değil; kural yukarıdaki satırla aynı.

Gerçek x86 işlemcide MP hiç görülmez (TSO: yazma sırası korunur), SB görülür. Aynı programı sanal amd64 ortamında çalıştırmak bir anlam taşımaz, çünkü Apple Silicon üzerinde bir emülatör çevirisini ölçmüş oluruz.

---

## 3. C11 bellek sıraları

| Sıra | Garantisi |
| --- | --- |
| `memory_order_relaxed` | Yalnızca bu değişkene atomiklik. Başka hiçbir sıralama yok. |
| `memory_order_release` (yazma) | Bu yazmadan **önceki** okuma/yazmalar sonrasına geçemez. |
| `memory_order_acquire` (okuma) | Bu okumadan **sonraki** okuma/yazmalar öncesine geçemez. |
| `memory_order_acq_rel` | Oku-değiştir-yaz için ikisi birden. |
| `memory_order_seq_cst` | Acquire/release + bütün seq_cst işlemler için tek bir **toplam sıra**. Varsayılan. |

Temel kavram **önce-olur** (happens-before): A işlemi B'den önce oluyorsa, B A'nın etkilerini görür. Bir iş parçacığında komut sırası bunu kuruyor. Bir release, aynı değişkeni okuyan bir acquire ile **eşleşince** (synchronizes-with), iki iş parçacığı arasında da kuruluyor.

### Mesaj geçirme doğru nasıl yazılır

```c
#include <stdatomic.h>
atomic_int hazir; int veri;
void yayinla(int v) { veri = v; atomic_store_explicit(&hazir, 1, memory_order_release); }
int bekle(void) { while (!atomic_load_explicit(&hazir, memory_order_acquire)) { } return veri; }
void gevsek(int v) { veri = v; atomic_store_explicit(&hazir, 1, memory_order_relaxed); }
void tam(int v) { veri = v; atomic_store(&hazir, 1); }
```

```
$ cc -O2 -S sira_at.c -o -
yayinla:
	adrp	x8, veri
	mov	w9, #1
	str	w0, [x8, :lo12:veri]
	adrp	x8, hazir
	add	x8, x8, :lo12:hazir
	stlr	w9, [x8]
	ret
bekle:
	adrp	x8, hazir
	add	x8, x8, :lo12:hazir
.LBB1_1:
	ldar	w9, [x8]
	cbz	w9, .LBB1_1
	adrp	x8, veri
	ldr	w0, [x8, :lo12:veri]
	ret
gevsek:
	adrp	x8, veri
	adrp	x9, hazir
	mov	w10, #1
	str	w0, [x8, :lo12:veri]
	str	w10, [x9, :lo12:hazir]
	ret
tam:
	...
	stlr	w9, [x8]
	ret
```

`stlr` (store-release) ve `ldar` (load-acquire) tam olarak modelin istediği komutlar. `veri` kilit gibi korunuyor: `veri = v` release'in **öncesine** geçemez; acquire görüldüyse `veri` okuması onu görür. Ders 10.10'da bahsettiğimiz "kilit görünürlük de sağlar" sözünün mekanizması bu: `pthread_mutex_unlock` bir release, `lock` bir acquire.

`gevsek`'te ise düz `str`: işlemci iki yazmayı yer değiştirebilir, yani `hazir = 1`'i gören `veri`'yi eski görebilir. Düz `int veri` burada atomik olmasa da **sorun değil**: release/acquire önce-olur ilişkisi kurduğu için veri yarışı oluşmuyor.

`tam` (seq_cst) arm64'te `stlr` ile aynı komuta dönüşüyor; farkı okuma tarafında ve seq_cst işlemlerin kendi arasındaki sırada. x86-64'te ise `store` seq_cst `xchg`, relaxed ve release ise düz `mov`.

### Pratik kural

1. Önce kilit kullan. Ölçüm kilidin darboğaz olduğunu göstermedikçe atomiklere inme.
2. Atomik kullanacaksan önce varsayılan **seq_cst** ile yaz.
3. `relaxed`'ı yalnızca başka hiçbir verinin korunmadığı işlerde kullan: basit sayaçlar, istatistikler.
4. `release`/`acquire` çiftleri "veri yayınlama" kalıbı için doğru araç.
5. Doğruluğunu kanıtlayamıyorsan `herd7`/`cppmem` gibi araçlarla ve TSan ile test et; yalnızca çalıştırıp bakmak yetmez.

---

## Alıştırmalar

**1** – `yaz` fonksiyonunda `a = 1` silinmesin isteseydin ne yapardın? Bu seçenek çok iş parçacıklı programda ne garanti eder, ne etmez?

**2** – Ders 10.12'deki `ref_birak`'ın neden `release` ile azaltıp sonra `acquire` fence yaptığını önce-olur ilişkisiyle açıkla.

**3** – Double-checked locking kalıbını (bir kez başlat, kilit tut, tekrar kontrol et) yanlış ve doğru (atomik) olarak yaz. Yanlış sürüm neden sadece arm'da değil, derleyicide de bozulabilir?

**4** – Dekker algoritmasının (iki bayrak ve bir sıra) çekirdeği SB litmus'udur. Normal değişkenlerle Dekker neden kırılır? Hangi bellek sırası gereklidir?

**5** – Yukarıdaki MP testini çok daha uzun süre çalıştırmak (milyarlarca tur) sonucu görebilir miydi? `herd7` gibi bir araç neyi farklı yapar?

<details>
<summary>Cevaplar</summary>

**1** – `a`'yı `volatile int` yapmak: derleyici her `volatile` erişimi ve sırasını korumak zorunda. Ama donanım üzerinde başka çekirdeklere bir sıralama garantisi vermez: bir ara değeri görmek ya da yazma sırası ne garantili ne de atomiktir. Paylaşılan iş parçacıkları için `_Atomic` gerekir.

**2** – Azaltma `release`: bu iş parçacığının nesneye yaptığı **son** erişimlerin, bir sonraki azaltmadan önce olmasını sağlıyor. Son referansı bırakan (değer 1 gören), başka iş parçacıklarının release'lerini görmek zorunda; bu yüzden `acquire` fence: `free` çağrısı öncekilerin bütün yazmalarından **sonra** olsun. Azaltmaların hepsi `acq_rel` de olabilirdi; bu yöntem hızlı yolda acquire maliyetinden kaçınıyor.

**3** – Yanlış: `if (!p) { lock; if (!p) { p = new; } unlock; } return p;` düz işaretçiyle. `p` görüldüğünde nesnenin içi henüz yazılmamış olabilir: derleyici `p = malloc; inicle(p)`'yi yer değiştirebilir, işlemci de. Doğrusu `atomic_load_explicit(&p, acquire)`, oluşturmada `store_explicit(&p, n, release)`. C11'in `call_once` fonksiyonu bunu hazır yapıyor.

**4** – Dekker: `flag[i] = 1; while (flag[j]) ...` yazma–okuma sırası gerektiriyor: tam olarak SB. Depo tamponu yüzünden iki iş parçacığı da karşı bayrağı 0 görüp kritik bölgeye girer. `seq_cst` yazma ve okumalar (ya da aralarına tam bir bellek bariyeri) gerekir. Aynı nedenle Peterson algoritması da modern işlemcilerde bariyersiz çalışmaz.

**5** – Daha uzun çalıştırmak bazı durumlarda gösterir (farklı cache durumları, kesmeler), ama garanti değil: bazı çekirdekler belirli yeniden sıralamaları hiç uygulamıyor olabilir. `herd7`, modelin **izin verdiği bütün** sonuçları matematiksel olarak sayıyor; donanımı çalıştırmıyor. Doğruluğun ölçütü modelin izin verdiği sonuçlar; bir donanımda gözlemlenenler değil.

</details>

---

## Kaynaklar

- ISO/IEC 9899:2011 (C11), §5.1.2.4: çok iş parçacıklı yürütme ve veri yarışları.
- Jeff Preshing, "An Introduction to Lock-Free Programming" ve "Acquire and Release Semantics" (preshing.com).
- Hans Boehm ve Sarita Adve, "Foundations of the C++ Concurrency Memory Model", *PLDI 2008*.
- Peter Sewell ve ark., "x86-TSO: A Rigorous and Usable Programmer's Model for x86 Multiprocessors", *CACM*, 2010.
- Jade Alglave, Luc Maranget ve Michael Tautschnig, "Herding Cats", *TOPLAS*, 2014: `herd7` ve litmus yöntemi.
- Paul McKenney, "Memory Barriers: a Hardware View for Software Hackers", 2010.
- Ulrich Drepper, "What Every Programmer Should Know About Memory", 2007.

**Sıradaki ders:** Zamanlayıcı. Round-robin, öncelik, bağlam değiştirme maliyeti.
