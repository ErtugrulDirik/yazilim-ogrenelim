---
title: "4.23 Bellek hataları"
description: "Dinamik bellekle gelen dört klasik hata: sallanan pointer ve use-after-free, double free, heap üzerinde sınır dışı erişim ve bir fonksiyonun yerel değişkeninin adresini döndürmesi (stack-use-after-return). Her birini AddressSanitizer'la üretip raporunu satır satır okumak: üç yığın izi (nerede kullanıldı, nerede serbest bırakıldı, nerede ayrıldı) ve gölge byte'lar."
---

Ders 4.22'de `malloc` ve `free`'yi öğrendik, sızıntıyı valgrind'le yakaladık. Sızıntı hataların en zararsızı: program yine doğru çalışır. Bu derste dinamik belleğin **tehlikeli** hatalarını topluyoruz — programı bozan, çökerten ya da güvenlik açığı yaratanları. Hepsi Ders 4.7'deki sallanan pointer fikrinin birer çeşidi.

Araç yine Ders 3.16'dan beri kullandığımız **AddressSanitizer** (`-fsanitize=address`). Bu derste asıl öğrendiğimiz, ASan'ın çıktısını **okumak**: her rapor, hatanın nerede olduğunu üç ayrı yığın iziyle anlatıyor.

Örnekleri `-O0` ile derliyoruz. ASan `-O1` ile daha hızlı çalışır ve çoğu projede öyle kullanılır; ama optimizasyon, sonucu kullanılmayan "ölü" bir hatayı (bir double free, kullanılmayan bir sınır dışı yazma) silebilir ve ASan onu göremez. Hatayı güvenilir görmek için `-O0`.

---

## 1. Use-after-free

Serbest bırakılmış belleği kullanmak. `free`'den sonra pointer hâlâ eski adresi tutuyor (sallanan pointer; Ders 4.7), ama o bellek artık senin değil:

```c
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    int *a = malloc(4 * sizeof(int));
    for (int i = 0; i < 4; i++) {
        a[i] = i + 1;
    }
    free(a);
    printf("%d\n", a[2]);   // use-after-free
    return 0;
}
```

ASan olmadan bu program çoğu zaman "3" yazıp sorunsuz biter — ve işte tehlike bu: bellek henüz başka bir şeye verilmediği için eski değer orada **duruyor gibi** görünür. Ama `free`'den sonra `malloc` o bölgeyi başka bir isteğe verebilir; o an `a[2]`, artık başka bir değişkenin verisini okur ya da bozar. Hata, ortaya çıkması aylar sürebilen, yeniden üretilmesi zor bir tür.

`-fsanitize=address` ile:

```
==30146==ERROR: AddressSanitizer: heap-use-after-free on address 0x6020000000d8 ...
READ of size 4 at 0x6020000000d8 thread T0
    #0 ... in main uaf.c:7           <- HATA BURADA: a[2]'yi okudun
    ...

0x6020000000d8 is located 8 bytes inside of 16-byte region [0x6020000000d0,0x6020000000e0)
freed by thread T0 here:
    #0 ... in free
    #1 ... in main uaf.c:6           <- BURADA serbest biraktin
    ...

previously allocated by thread T0 here:
    #0 ... in malloc
    #1 ... in main uaf.c:4           <- BURADA ayirdin
```

ASan raporunun kalbi bu **üç yığın izi**:

1. **Hatanın kendisi** (`heap-use-after-free ... READ of size 4 ... uaf.c:7`): 7. satırda, 4 byte'lık bir okuma yaptın, serbest bırakılmış bellekte.
2. **`freed by ... here`** (`uaf.c:6`): bu bellek 6. satırda `free` edildi.
3. **`previously allocated by ... here`** (`uaf.c:4`): ve 4. satırda ayrılmıştı.

Üçü birlikte hatanın tam hikâyesi: *bu bellek 4'te doğdu, 6'da öldü, 7'de hortladı.* Her izin Ders 2.6'daki LLDB `bt` ve Ders 4.22'deki valgrind yığını gibi okunur. "16-byte region" ayrılan bloğun boyutu (4 × `sizeof(int)`), "8 bytes inside" ise okuduğun yerin bloğun 8. byte'ı (yani `a[2]`) olması.

---

## 2. Double free

Aynı bloğu iki kez serbest bırakmak:

```c
int *a = malloc(4 * sizeof(int));
free(a);
free(a);   // double free
```

```
==30118==ERROR: AddressSanitizer: attempting double-free on 0x6020000000d0 ...
    #0 ... in free
    #1 ... in main df.c:5            <- ikinci free
    ...
freed by thread T0 here:
    #0 ... in free
    #1 ... in main df.c:4            <- ilk free
```

İki yığın izi: ikinci `free`'nin yeri (satır 5) ve bloğun zaten nerede serbest bırakıldığı (satır 4). Double free neden tehlikeli? `free`, serbest blokları kendi iç listesinde tutuyor (Ders 4.29'da bu listeyi kendimiz yazacağız); aynı bloğu iki kez geri vermek bu listeyi bozabilir ve sonraki `malloc`'ların aynı belleği iki yere vermesine yol açabilir — bu da klasik bir güvenlik açığı türü.

En sık sebebi, bir bloğa iki pointer'ın (Ders 4.7'deki aliasing) işaret edip ikisinin de `free` edilmesi, ya da `realloc`'tan sonra eski pointer'ı `free` etmek (Ders 4.22). Savunma Ders 4.22'deki alışkanlık: `free(a); a = NULL;`. `free(NULL)`'ın **hiçbir etkisi yoktur** (güvenle çağrılabilir), bu yüzden ikinci `free(a)` artık `free(NULL)` olur ve zararsızdır.

---

## 3. Heap üzerinde sınır dışı

Ders 4.1'deki sınır dışı erişim, bu sefer stack'te değil heap'te:

```c
int *a = malloc(4 * sizeof(int));
a[4] = 99;   // 0..3 gecerli; a[4] bir fazlasi
```

```
==30126==ERROR: AddressSanitizer: heap-buffer-overflow on address 0x6020000000e0 ...
WRITE of size 4 at 0x6020000000e0 thread T0
    #0 ... in main ho.c:4            <- sinir disi yazma
    ...
0x6020000000e0 is located 0 bytes after 16-byte region [0x6020000000d0,0x6020000000e0)
allocated by thread T0 here:
    #0 ... in malloc
    #1 ... in main ho.c:3            <- blok burada ayrildi
```

"0 bytes after 16-byte region": yazdığın adres, 16 byte'lık bloğun hemen **bittiği** yer — yani bloğun bir byte ötesi. İki yığın izi: yazmanın yeri (satır 4) ve bloğun ayrıldığı yer (satır 3). Ders 3.16'daki `itoa`'da tamponun bir byte ötesine yazınca gördüğümüz hatanın aynısı.

Heap taşması, stack taşması (Ders 4.14) kadar tehlikeli: `malloc`'un blokların arasında tuttuğu yönetim bilgisini ezip sonraki `malloc`/`free`'leri bozabilir.

---

## 4. Yerel değişkenin adresini döndürmek

Ders 4.7'deki sallanan pointer'ın heap'siz hali: bir fonksiyon kendi yerel değişkeninin adresini döndürüyor.

```c
int *make(void) {
    int x = 42;
    return &x;      // x fonksiyon bitince yok olur
}
int main(void) {
    int *p = make();
    return *p;      // yok olmus bir seyin adresini okuyoruz
}
```

Önce compiler zaten uyarıyor (Ders 4.7):

```
warning: address of stack memory associated with local variable 'x' returned [-Wreturn-stack-address]
```

ASan ile, stack kullanımını da izleyecek seçenekle (`ASAN_OPTIONS=detect_stack_use_after_return=1`):

```
==30155==ERROR: AddressSanitizer: stack-use-after-return on address 0x000101db0020 ...
READ of size 4 at 0x000101db0020 thread T0
    #0 ... in main dang.c:3
```

`stack-use-after-return`: `make`'in stack çerçevesi (Ders 4.7) fonksiyon dönünce geçersiz oldu, ama `p` hâlâ oradaki `x`'i gösteriyor. Çözüm Ders 4.22'deki `malloc`: değerin fonksiyondan uzun yaşaması gerekiyorsa, onu heap'te ayır ya da çağıranın verdiği bir yere (çıkış parametresi; Ders 4.7) yaz.

---

## 5. Dört hata, tek tablo

| Hata | Ne | ASan adı | Savunma |
| --- | --- | --- | --- |
| **use-after-free** | serbest belleği kullanmak | `heap-use-after-free` | `free` sonrası `NULL`'a çek |
| **double free** | iki kez `free` | `attempting double-free` | `free(p); p = NULL;` |
| **heap overflow** | bloğun dışına yazmak/okumak | `heap-buffer-overflow` | boyutu doğru hesapla |
| **dangling return** | yerelin adresini döndürmek | `stack-use-after-return` | `malloc` ya da çıkış parametresi |

Hepsinin ortak kökü: **bir pointer, artık geçerli olmayan bir belleği gösteriyor.** C, pointer'ın gösterdiği şeyin hâlâ yaşayıp yaşamadığını kendiliğinden bilmiyor; bu takip tamamen programcıda. ASan bu takibi çalışırken yapan bir araç: her bellek erişiminden önce o adresin "geçerli" olup olmadığını bir **gölge bellekte** (shadow memory) kontrol ediyor. Raporların sonundaki `fd` (freed), `fa` (sınır bölgesi/redzone) gibi gölge byte'lar bunun içi. ASan'la geliştirmek, Ders 2.12'deki `-Wall` ve Ders 4.22'deki valgrind kadar temel; testlerini her zaman `-fsanitize=address` ile çalıştır.

---

## Alıştırmalar

**1** – Bölüm 1'deki use-after-free'de `printf("%d\n", a[2])` yerine `a[2] = 7;` yazsan ASan ne der — `READ` mı `WRITE` mı? Rapordaki üç yığın izinden hangileri aynı kalır?

**2** – Bir bloğa iki pointer: `int *a = malloc(4); int *b = a; free(a); free(b);`. ASan bunu double free olarak yakalar mı? `a`'yı `free` ettikten sonra `a = NULL` yapmak `b`'yi korur mu? Bu neden aliasing'in (Ders 4.7) tehlikeli bir hali?

**3** – `free(NULL)` güvenli olduğuna göre, şu kalıp neden işe yarıyor: bir fonksiyonun başında `char *buf = NULL;`, ortasında bir yerde `buf = malloc(...)`, sonunda koşulsuz `free(buf);`. `malloc`'a hiç gelinmezse ne olur?

**4** – `make`'i (Bölüm 4) `static int x = 42;` ile yaz. Artık `&x`'i döndürmek güvenli mi? `-Wreturn-stack-address` uyarısı kalkar mı? `static`'in (Ders 4.4) burada ne değiştirdiğini açıkla. İki `make()` çağrısı aynı adresi mi döndürür?

**5** – Bir `int` array'ini heap'te ayıran, dolduran, kullanan ve `free` eden eksiksiz bir fonksiyon yaz — ama `realloc` ile iki katına çıkar ve **eski pointer'ı** kullanmaya devam et (Ders 4.22'deki taşınma hatası). ASan'ın bunu `heap-use-after-free` olarak yakalayıp yakalamadığını kontrol et. Neden bazen yakalamayabilir?

<details>
<summary>Cevaplar</summary>

**1** – `a[2] = 7;` için ASan `WRITE of size 4` der (okuma değil yazma). Üç yığın izinden **ikisi aynı kalır**: "freed by here" (hâlâ aynı `free` satırı) ve "previously allocated by here" (aynı `malloc`). Değişen sadece ilk iz: hata artık bir okuma değil yazma, ve satır numarası `a[2] = 7`'nin bulunduğu satır. use-after-free hem okumada hem yazmada hata; ASan ikisini de yakalar.

**2** – Evet, ASan `attempting double-free` der: `a` ve `b` **aynı** bloğu gösteriyor (`b = a`), `free(a)` bloğu serbest bırakıyor, `free(b)` aynı bloğu ikinci kez. `a`'yı `free`'den sonra `NULL` yapmak `b`'yi **korumaz**: `b` hâlâ eski adresi tutuyor, `a = NULL` sadece `a`'yı değiştirir. Aliasing'in tehlikesi tam bu: bir bloğa kaç pointer işaret ettiğini dilin kendisi bilmiyor; "sahipliği" (kim `free` edecek) programcı tek bir pointer'da tutmalı, diğerleri sadece "ödünç" bakmalı ve asla `free` etmemeli.

**3** – `malloc`'a hiç gelinmezse `buf` başlangıçtaki `NULL` değerinde kalır ve sondaki `free(buf)` aslında `free(NULL)` olur — hiçbir etkisi olmayan, güvenli bir çağrı. Bu kalıp (başta `NULL`, sonda koşulsuz `free`) hata yollarını temizlerken çok kullanışlı: bir fonksiyonun ortasında bir şey ters giderse `goto cleanup` ile sona atlarsın, ve henüz ayrılmamış pointer'lar `NULL` olduğu için `free`'leri zararsızdır. `free(NULL)`'ın güvenli tanımlanmış olması bu deseni mümkün kılıyor.

**4** – `static int x = 42;` ile `&x`'i döndürmek **güvenli**: `static` yerel değişken, Ders 4.4'teki veri bölgesinde durur, fonksiyon bitince yok olmaz, program boyunca yaşar. `-Wreturn-stack-address` uyarısı **kalkar**: `x` artık stack'te değil, compiler bunu biliyor. `static`'in değiştirdiği, değişkenin **ömrü**: otomatik (her çağrıda yeni, çağrı bitince ölür) yerine statik (tek bir kopya, program boyunca). İki `make()` çağrısı **aynı** adresi döndürür — tek bir `x` var. Dezavantajı Ders 4.7'deki `static char buffer` tuzağı: iki çağrı aynı yeri paylaşır, biri diğerinin değerini ezebilir; yeniden girilemez (Ders 4.20).

**5** –

```c
void grow_bug(void) {
    int *a = malloc(4 * sizeof(int));
    for (int i = 0; i < 4; i++) a[i] = i;
    int *b = realloc(a, 1024 * sizeof(int));  // buyuk: tasinir
    // a'yi kullanmaya devam (HATA): a artik serbest
    a[0] = 99;
    free(b);
}
```

`realloc` bloğu taşıdıysa (Ders 4.22'de büyük boyutlarda taşındığını ölçmüştük), eski `a` artık serbest bir bölgeyi gösteriyor; `a[0] = 99` bir use-after-free. ASan bunu `heap-use-after-free` (WRITE) olarak yakalar — **eğer** `realloc` gerçekten taşıdıysa. `realloc` bloğu **yerinde** büyütebilirse (arkada yer varsa) `a` ile `b` aynı adres olur ve `a[0]` hata olmaz; hata ortaya çıkmaz. Bu yüzden use-after-free'ler sinsi: aynı kod bazen çöker bazen çalışır, `realloc`'un o anki kararına bağlı. Kural değişmez: `realloc`'tan sonra sadece yeni pointer'ı kullan.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §9.11: yaygın bellek hataları.
- AddressSanitizer: Konstantin Serebryany vd., "AddressSanitizer: A Fast Address Sanity Checker" (USENIX ATC 2012); gölge bellek tekniği.
- C standardı (ISO/IEC 9899:2018), §7.22.3: `free(NULL)`'ın etkisizliği; serbest bırakılmış bir pointer'ın değerinin undefined olması.
- SEI CERT C Coding Standard, MEM30-C (use-after-free), MEM31-C (double free), MEM35-C (yetersiz ayırma).

**Sıradaki ders:** Dinamik dizi. Kapasite ikiye katlama ve amortize edilmiş $O(1)$ ekleme.
