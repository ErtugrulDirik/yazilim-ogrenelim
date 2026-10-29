---
title: "4.22 Dinamik bellek"
description: "Çalışırken bellek istemek: malloc'un void * döndürmesi ve dönüşünü her zaman kontrol etmek, calloc'un sıfırlaması ve çarpma taşmasını yakalaması, realloc'un bloğu taşıyabilmesi ve p = realloc(p, ...) tuzağı, free ve sonrası NULL'a çekmek, bir strdup yazmak, bellek sızıntısı ve valgrind'in sızıntıyı satır numarasıyla göstermesi."
gereksinimler: [linux]
gereksinimNotu: "valgrind bölümü Linux'a özeldir; malloc/free kodu her yerde çalışır, macOS'ta sızıntı için leaks ya da AddressSanitizer kullanılır."
windowsNotu: "valgrind'i WSL içinde kur: sudo apt install valgrind."
---

Ders 2.4'ten beri array'lerin boyutunun derlemede belli olması gerektiğini söyledik; Ders 4.3'te "boyutu çalışırken belli olan tabloları Ders 4.22'de göreceğiz" dedik. Ders 4.7'de bir fonksiyonun kendi yerel değişkeninin adresini döndüremediğini (sallanan pointer), ama `malloc` ile ayrılmış belleğin fonksiyondan uzun yaşadığını söyledik. Ders 4.21'de heap bölgesini gördük. Şimdi o bölgeden bellek istiyoruz.

**Dinamik bellek**: miktarı program çalışırken belirlenen, istediğin kadar yaşayan bellek. Dört fonksiyon, hepsi `<stdlib.h>`'te: `malloc`, `calloc`, `realloc`, `free`.

---

## 1. malloc ve free

```c
void *malloc(size_t size);
void free(void *ptr);
```

`malloc`, `size` byte'lık bir blok ayırıp **başlangıç adresini** döndürüyor; `free` onu geri veriyor. `malloc`'un dönüş tipi `void *` (Ders 4.9): ne için kullanacağını bilmiyor, sadece byte veriyor.

```c
#include <stdio.h>
#include <stdlib.h>

int n = 5;
int *a = malloc(n * sizeof(int));
if (a == NULL) {
    fprintf(stderr, "bellek yok\n");
    return 1;
}
for (int i = 0; i < n; i++) {
    a[i] = i * i;
}
// ... kullan ...
free(a);
```

Üç kural, en baştan:

**1. Dönüşü her zaman kontrol et.** `malloc` başarısız olursa `NULL` döndürüyor (bellek tükenmişse). `NULL` dönen bir pointer'ı kullanmak Ders 4.5'teki NULL dereference: çökme. Her `malloc`'tan sonra `if (p == NULL)`.

**2. Boyutu `n * sizeof(int)` diye yaz.** Kaç eleman × her biri kaç byte. `sizeof(int)` yerine elle `4` yazmak, Windows'ta ya da başka bir tipte yanlış olur (Ders 3.2). `void *` sayesinde cast gerekmiyor: `int *a = malloc(...)` doğrudan çalışıyor (Ders 4.9; C++'ta cast gerekirdi).

**3. Ayırdığın her bloğu `free` et.** `malloc` ile `free` eşleşmeli. Etmezsen bellek **sızar** (Bölüm 5).

`malloc`'un verdiği bellek **başlatılmamış**: içinde çöp değerler var (Ders 4.5'teki başlatılmamış değişken gibi). İlk iş onu doldurmak. `malloc(0)`'ın ne döndürdüğü tanımlı değil (ya `NULL` ya da serbest bırakılabilir benzersiz bir pointer); bu uç duruma güvenme.

---

## 2. calloc: sıfırlanmış ve taşmaya karşı güvenli

```c
void *calloc(size_t count, size_t size);
```

`calloc`, `malloc`'tan iki farkla:

- Belleği **sıfırla** dolduruyor (Ders 4.9'daki `memset(…, 0, …)` gibi; bütün byte'lar 0).
- Boyutu **iki ayrı** parametre olarak alıyor: `count` eleman, her biri `size` byte.

```c
int *b = calloc(n, sizeof(int));   // n tane sifirlanmis int
```

İkinci fark güvenlik için önemli. `malloc(count * size)` yazarsan, `count * size` çarpımı Ders 3.8'deki gibi **taşabilir**: çok büyük bir `count` ile çarpım sarıp küçük bir sayı olur, `malloc` küçük bir blok verir, ama kod `count` eleman olduğunu sanıp taşar. `calloc` çarpmayı **kendi içinde** yapıyor ve taşmayı kontrol ediyor; taşarsa `NULL` döndürüyor. Bir boyut kullanıcı girdisinden geliyorsa (`calloc(kullanici_sayisi, sizeof ...)`), `calloc` bu yüzden `malloc(kullanici_sayisi * sizeof ...)`'dan güvenli.

Sıfırlama bedava değil (büyük bloklarda belleğe sıfır yazmak zaman alır), ama çoğu zaman zaten sıfırlayacağın belleği `calloc` ile almak hem kısa hem güvenli.

---

## 3. realloc: bloğu büyütmek

```c
void *realloc(void *ptr, size_t new_size);
```

Mevcut bir bloğu yeniden boyutlandırıyor; içindeki veriyi (eski ve yeni boyutun küçüğü kadarını) **koruyor**.

```c
int *c = realloc(a, 10 * sizeof(int));
if (c == NULL) {
    free(a);          // a hala gecerli
    return 1;
}
a = c;
```

`realloc` üç şey yapabilir: ya bloğu yerinde büyütür (arkada yer varsa), ya **yeni bir yere taşır** (eskisini kopyalayıp serbest bırakır), ya da `NULL` döndürür (başarısız). Bloğu büyüte büyüte ölçtüğümüzde, çoğu adımda **taşındığını** görüyoruz:

```
ilk    = 0x101541e40
tasindi cap=8:   0x101541e40 -> 0x101541e50
tasindi cap=16:  0x101541e50 -> 0x101541e70
...
tasindi cap=1024: 0x101543ac0 -> 0x9d1000000
```

Taşınma yüzünden iki kritik kural:

**Eski pointer'ı bir daha kullanma.** `realloc` taşıdıysa, eski adres artık serbest; oradan okumak use-after-free (Ders 4.23). Her zaman dönen yeni pointer'ı kullan.

**`p = realloc(p, ...)` yazma.** Bu çok yaygın bir tuzak: `realloc` `NULL` döndürürse, `p`'nin içindeki **eski geçerli adres** kaybolur ve o blok artık `free` edilemez — sızıntı. Doğrusu yukarıdaki gibi ara bir değişken (`c`) kullanıp, başarılıysa `a = c` yapmak. `realloc(NULL, size)` ise `malloc(size)` gibi davranıyor (ilk ayırma için kullanışlı), `realloc(p, 0)` ise tanımı tartışmalı — buna güvenme.

---

## 4. free sonrası ve bir strdup

`free`'den sonra pointer hâlâ eski (artık geçersiz) adresi tutuyor: **sallanan pointer** (Ders 4.7). Onu kullanmak use-after-free. Yaygın savunma, `free`'den hemen sonra `NULL`'a çekmek:

```c
free(a);
a = NULL;   // artik a'yi kazara kullanmak NULL dereference (hemen cokertir), sessiz bozulma degil
```

Ders 4.10'daki 2. alıştırmadaki `clear_and_null` kalıbı tam buydu.

Bunları birleştiren klasik bir fonksiyon: bir yazının **kopyasını** heap'te oluşturan `strdup` (POSIX'te var, C23'te standart). Ders 4.7'deki "fonksiyon kendi yazısını döndüremez" sorununun çözümü:

```c
#include <stdlib.h>
#include <string.h>

char *duplicate(const char *s) {
    size_t n = strlen(s) + 1;      // '\0' dahil
    char *copy = malloc(n);
    if (copy == NULL) {
        return NULL;
    }
    memcpy(copy, s, n);            // Ders 4.18
    return copy;
}
```

`copy` heap'te, fonksiyondan uzun yaşıyor; çağıran onu kullanıp işi bitince `free` ediyor. Yerel bir array döndürmek (Ders 4.7) çökerdi; `malloc`'lu kopya çözüm. Tek bedel: `free` sorumluluğu artık çağıranda. "Kim ayırdı, kim serbest bırakacak?" sorusu (ownership), dinamik bellekle yazılan her API'nin en önemli tasarım kararı.

---

## 5. Sızıntı ve valgrind

En sık dinamik bellek hatası: ayırıp `free` etmemek. Bu hata **sessiz** — program çalışır, doğru sonuç verir, ama kullanmadığı belleği geri vermez. Kısa çalışan programlarda zararsız (program bitince işletim sistemi hepsini geri alır); ama uzun çalışan bir programda (sunucu, oyun) sızıntı birike birike belleği tüketir.

```c
char *duplicate(const char *s) { /* yukaridaki */ }

int main(void) {
    for (int i = 0; i < 3; i++) {
        char *c = duplicate("merhaba");
        // free(c) UNUTULDU
    }
    char *keep = duplicate("kalici");
    return 0;   // keep de free edilmedi
}
```

Gözle bulmak zor. Linux'ta **valgrind** tam bunun için: programı yavaşlatarak çalıştırır, her `malloc`/`free`'yi izler, bitişte serbest bırakılmamış blokları **nereden ayrıldıklarıyla** birlikte raporlar.

```
$ valgrind --leak-check=full ./leak
==10==   total heap usage: 4 allocs, 0 frees, 31 bytes allocated
==10== 7 bytes in 1 blocks are definitely lost in loss record 1 of 2
==10==    at 0x4885250: malloc
==10==    by 0x10883F: duplicate (leak.c:6)
==10==    by 0x1088BB: main (leak.c:16)
==10== 24 bytes in 3 blocks are definitely lost in loss record 2 of 2
==10==    at 0x4885250: malloc
==10==    by 0x10883F: duplicate (leak.c:6)
==10==    by 0x108897: main (leak.c:13)
==10==    definitely lost: 31 bytes in 4 blocks
```

Okuması:

- **4 allocs, 0 frees**: dört kez ayrıldı, hiç serbest bırakılmadı.
- **"definitely lost"**: bu bloklara erişebilecek hiçbir pointer kalmadı — kesin sızıntı. (valgrind "indirectly" ve "possibly lost" gibi başka kategoriler de ayırır.)
- **Çağrı yığını**: `malloc ← duplicate (leak.c:6) ← main (leak.c:13)`. Ders 4.7'deki çağrı yığınının (Ders 2.6'daki LLDB `bt`) aynısı. Sızıntının hangi satırda ayrılan blokta olduğunu doğrudan söylüyor: döngüdeki üç `c` (satır 13) ve `keep` (satır 16).

`free`'leri eklediğimizde valgrind `All heap blocks were freed -- no leaks are possible` ve `ERROR SUMMARY: 0 errors` der. Dinamik bellek kullanan her programı valgrind (ya da macOS'ta `leaks` / AddressSanitizer) ile çalıştırmak, Ders 2.12'deki `-Wall` kadar temel bir alışkanlık. valgrind sadece sızıntıyı değil, Ders 4.23'teki use-after-free ve sınır dışı erişimi de yakalıyor.

---

## Alıştırmalar

**1** – `malloc(n * sizeof(int))` yerine `malloc(sizeof(int) * n)` yazmak fark eder mi? Peki `n` bir `int` ve çok büyükse (örneğin kullanıcıdan gelen 2 milyar), `n * sizeof(int)` çarpımında ne olur? `calloc(n, sizeof(int))` bu durumda nasıl davranır?

**2** – `duplicate`'i `calloc` ile yaz. `'\0'` dahil kopyaladığın için sıfırlamanın bir faydası var mı? Hangi durumda `calloc` `malloc`'tan daha mantıklı olurdu (ipucu: kopyalamadan önce bir kısmını boş bırakmak)?

**3** – `p = realloc(p, new_size)` tuzağını bir programda göster: `realloc`'un `NULL` döndürdüğü durumu taklit et (çok büyük bir `new_size` iste) ve valgrind'in ne dediğine bak. Doğru sürümle (ara değişkenli) karşılaştır.

**4** – Bir `int` array'ini okuyup iki katına çıkaran `int *doubled(const int *a, int n)` yaz: yeni bir blok ayır, her elemanı iki katıyla doldur, döndür. Çağıran ne yapmak zorunda? `a`'yı `free` etmeli mi? (İpucu: `a`'yı kim ayırdı?)

**5** – Bölüm 5'teki sızıntılı programa `free(c)`'yi ekle ama `free(keep)`'i ekleme. valgrind kaç blok "definitely lost" der, hangi satırı gösterir? Program `return 0`'dan sonra işletim sistemi belleği geri alacağına göre, `keep`'i serbest bırakmak neden yine de önemli?

<details>
<summary>Cevaplar</summary>

**1** – `malloc(n * sizeof(int))` ile `malloc(sizeof(int) * n)` aynı: çarpma değişmeli. Ama `n` bir `int` ve büyükse sorun var: `n * sizeof(int)` çarpımında `sizeof(int)` bir `size_t` (işaretsiz 64 bit) olduğu için `n` de `size_t`'ye yükseltilir (Ders 3.5) ve çarpım 64 bitte yapılır — 2 milyar × 4 = 8 milyar, 64 bitte taşmaz, `malloc` 8 GB ister ve büyük ihtimalle `NULL` döner. Yani bu makinede çarpım taşmaz, ama 32 bitlik bir sistemde `size_t` de 32 bit olsaydı taşardı. `calloc(n, sizeof(int))` her durumda çarpmayı kontrol eder: taşarsa `NULL`, sessizce küçük blok vermez. Boyut dışarıdan geliyorsa `calloc` daha güvenli.

**2** –

```c
char *duplicate(const char *s) {
    size_t n = strlen(s) + 1;
    char *copy = calloc(n, 1);
    if (copy == NULL) return NULL;
    memcpy(copy, s, n);
    return copy;
}
```

Burada sıfırlamanın faydası **yok**: zaten `n` byte'ın hepsini `memcpy` ile üzerine yazıyoruz, `calloc`'un sıfırladığı byte'lar boşa gidiyor. `malloc` daha doğru. `calloc` şu durumda mantıklı olurdu: bloğun bir kısmını kopyalayıp gerisini boş (sıfır) bırakacaksan — örneğin `n` byte ayırıp sadece ilk `k` byte'ı doldurup kalanının sıfır olmasını istiyorsan, `calloc` + kısmi `memcpy`, `malloc` + `memcpy` + `memset` üçlüsünden kısa.

**3** –

```c
int *p = malloc(10 * sizeof(int));
int *tmp = realloc(p, (size_t)-1);   // imkansiz boyut: NULL doner
if (tmp == NULL) {
    printf("realloc basarisiz; p hala gecerli: %p\n", (void *)p);
    free(p);                          // dogru: eski blok serbest
} else {
    p = tmp;
}
```

`p = realloc(p, (size_t)-1)` yazsaydık, `realloc` `NULL` döndürünce `p` `NULL` olur ve `malloc`'la ayrılan 40 byte'lık blok **erişilemez** kalır. valgrind bunu "40 bytes definitely lost" der. Ara değişkenli sürümde `p` korunur ve `free(p)` ile temizlenir; valgrind "no leaks". `(size_t)-1`, Ders 3.6'daki gibi işaretsizde en büyük değer, pratikte ayrılamaz.

**4** –

```c
int *doubled(const int *a, int n) {
    int *result = malloc((size_t)n * sizeof(int));
    if (result == NULL) {
        return NULL;
    }
    for (int i = 0; i < n; i++) {
        result[i] = a[i] * 2;
    }
    return result;
}
```

Çağıran, dönen pointer'ı kullanıp işi bitince `free` etmek zorunda — `doubled` `malloc` ile ayırdı, serbest bırakma sorumluluğu çağırana geçti. `a`'yı `free` **etmemeli**: `a`'yı `doubled` ayırmadı, çağıran kendisi (ya da başka biri) ayırdı; onu `doubled`'ın serbest bırakması, "kim ayırdıysa o serbest bırakır" kuralını bozar ve muhtemelen double-free'ye yol açar (Ders 4.23). Her blok için tek bir sahip olmalı.

**5** – valgrind **1 blok** "definitely lost" der: `keep` (7 byte), `duplicate` içindeki `malloc`'tan, `main`'deki `keep = duplicate(...)` satırından. Döngüdeki üç `c` artık `free(c)` ile temizlendiği için raporda yok. `return 0`'dan sonra işletim sistemi gerçekten bütün belleği geri alır, yani bu küçük program için `keep`'i sızdırmak pratikte zararsız. Ama yine de önemli, çünkü: (1) bu `duplicate` çağrısı uzun çalışan bir programın içinde olsaydı sızıntı birikirdi; (2) valgrind'in raporunu temiz tutmak, gerçek (zararlı) sızıntıları görebilmek için şart — "zararsız" sızıntılar raporu kirletip ciddilerini gizler; (3) bir kütüphane fonksiyonu yazıyorsan, onu kimin ne kadar çağıracağını bilemezsin. Alışkanlık: her `malloc`'un bir `free`'si olsun.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §7.8.5 ve §8.7: `malloc`, `free` ve bir uygulaması.
- C standardı (ISO/IEC 9899:2018), §7.22.3: `malloc`, `calloc`, `realloc`, `free`.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §9.9: dinamik bellek ayırma.
- valgrind kullanıcı kılavuzu, Memcheck bölümü: sızıntı kategorileri (definitely/indirectly/possibly lost).
- SEI CERT C Coding Standard, MEM31-C (her bloğu serbest bırakmak), MEM35-C (`calloc` ile çarpma taşmasından kaçınmak).

**Sıradaki ders:** Bellek hataları. Dangling pointer, double free, use-after-free; AddressSanitizer çıktısını okumak.
