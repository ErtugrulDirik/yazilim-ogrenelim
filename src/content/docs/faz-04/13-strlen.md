---
title: "4.13 strlen sıfırdan"
description: "Standart kütüphanenin ilk fonksiyonunu sıfırdan yazmak: indeksle ve pointer farkıyla iki strlen, standart sürümle 650 bini aşkın test, clang'in -O2'de döngümüzü tanıyıp strlen çağrısına çevirmesi, -fno-builtin, standart sürümün 15 kat hızlı olması ve döngü koşulunda strlen çağırmanın programı kareli zamana sürüklemesi."
---

Ders 4.12'de bir C stringinin uzunluğunun hiçbir yerde saklanmadığını söyledik: tek yol, `'\0'`'ı bulana kadar saymak. Bu sayma işini yapan fonksiyon `<string.h>`'teki `strlen`. Ders 3.4'ten beri adını anıyoruz; Ders 4.11 ve 4.12'de kara kutu olarak kullandık.

Bu dersle birlikte Faz 4'ün ikinci yarısı başlıyor: `<string.h>`'in fonksiyonlarını tek tek sıfırdan yazacağız. Her birinde aynı sırayı izleyeceğiz:

1. Standart imzayı birebir kopyala (Ders 4.8).
2. En basit doğru sürümü yaz.
3. Standart sürümle **aynı girdiler** üzerinde karşılaştır.
4. Hızını ölç ve aradaki farkı anla.

Ders 4.30'da hepsini bir kütüphanede, `libmystr`'de toplayacağız.

---

## 1. İmza

```c
size_t strlen(const char *s);
```

- **`const char *s`**: yazıyı okuyor, değiştirmiyor (Ders 4.8).
- **`size_t`**: bir uzunluk; Ders 3.4'teki kural. Negatif olamaz, ve 2³¹'den uzun yazıları da sayabilir.
- **`'\0'` sayılmıyor**: `strlen("kedi")` 4, `sizeof "kedi"` 5 (Ders 4.12).

Ve en önemlisi, imzanın **söylemediği** şey: `s` geçerli, `'\0'` ile biten bir yazıyı göstermeli. `strlen(NULL)` ya da sonunda `'\0'` olmayan bir array (Ders 4.12'deki `letters`) undefined behavior. Standart sürüm de bunları kontrol etmiyor; kontrol etmenin bir yolu da yok, çünkü bir pointer'ın "geçerli bir yazıyı" gösterip göstermediği pointer'a bakarak anlaşılmıyor.

Kendi fonksiyonlarımıza standart adları **vermeyeceğiz**: `strlen` adlı bir fonksiyon yazmak, standart kütüphanedekiyle çakışır ve undefined behavior. Bu derste `strlen_index` ve `strlen_pointer` diyoruz; Ders 4.30'da kütüphaneye `my_` önekiyle koyacağız.

---

## 2. İki sürüm

### İndeksle

Ders 4.2'deki gibi bir sayaçla:

```c
#include <stddef.h>

size_t strlen_index(const char *s) {
    size_t n = 0;
    while (s[n] != '\0') {
        n++;
    }
    return n;
}
```

Döngü değişmezi (Ders 4.2): her adımın başında `s[0]`'dan `s[n-1]`'e kadar hiçbiri `'\0'` değil. Döngü `s[n] == '\0'` olunca bitiyor; o anda `n`, `'\0'`'dan önceki karakter sayısı. Boş yazıda (`""`) döngü hiç dönmüyor, 0 dönüyor.

### Pointer farkıyla

Ders 4.6'daki `*p++` deyimi ve pointer farkı:

```c
size_t strlen_pointer(const char *s) {
    const char *p = s;
    while (*p != '\0') {
        p++;
    }
    return (size_t)(p - s);
}
```

`p` yazı boyunca ilerliyor ve `'\0'`'ın üstünde duruyor. İki pointer'ın farkı (`ptrdiff_t`; Ders 4.6) aradaki eleman sayısı. Fark burada hiçbir zaman negatif olamayacağı için `size_t`'ye çevirmek güvenli; cast'i, bir işaretli değeri işaretsize bilerek çevirdiğimizi göstermek için yazdık (Ders 3.7).

K&R §5.4 bu sürümü verir ve C kodunda en çok bu biçimiyle karşılaşırsın. Ama birazdan göreceğimiz gibi, ikisi arasında bir hız farkı yok.

---

## 3. Standart sürümle karşılaştırmak

İki fonksiyonu 0'dan 4096'ya kadar her uzunlukta, rastgele içerikli yazılarda deneyelim. İçerik 1–255 arası rastgele byte'lar (0 olamaz; o zaman yazı erken biterdi). Bir de **başlangıç adresi** değişsin: Faz 5'te göreceğimiz hızlı sürümler, yazının 8'in katı bir adreste başlayıp başlamamasına göre farklı davranacak, testler o durumları da kapsamalı.

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

size_t strlen_index(const char *s);
size_t strlen_pointer(const char *s);

int main(void) {
    static char buf[4097];
    long tests = 0;
    long fails = 0;
    srand(7);
    for (int len = 0; len <= 4096; len++) {
        for (int rep = 0; rep < 20; rep++) {
            for (int i = 0; i < len; i++) {
                buf[i] = (char)(1 + rand() % 255);
            }
            buf[len] = '\0';
            for (int off = 0; off <= len && off < 8; off++) {
                size_t want = strlen(buf + off);
                if (strlen_index(buf + off) != want || strlen_pointer(buf + off) != want) {
                    fails++;
                }
                tests++;
            }
        }
    }
    printf("%ld test, %ld hata\n", tests, fails);
    return 0;
}
```

Fonksiyonları ayrı bir dosyaya (`mylen.c`) koyup AddressSanitizer ve UBSan ile derliyoruz (`-fno-builtin`'in ne olduğunu birazdan göreceğiz):

```
$ clang -O2 -Wall -Wextra -std=c17 -fsanitize=address,undefined -fno-builtin test.c mylen.c -o test
$ ./test
654960 test, 0 hata
```

650 bini aşkın karşılaştırma, hiçbir fark, hiçbir sınır dışı okuma. (`static char buf[4097]`: `static` bu array'i stack'ten veri bölgesine taşıyor; Ders 4.4. 4 KB stack için sorun değil, ama alışkanlık olarak büyük array'leri stack'e koymuyoruz.)

---

## 4. Compiler döngümüzü tanıyor

`mylen.c`'yi `-O2` ile derleyip üretilen assembly'ye (Ders 4.6'daki gibi) bakalım:

```
$ clang -O2 -S -o - mylen.c
_strlen_index:
	b	_strlen
_strlen_pointer:
	b	_strlen
```

Döngü yok. İki fonksiyonun da tek komutu `b _strlen`: "standart kütüphanedeki `strlen`'e atla." clang, yazdığımız döngünün **ne yaptığını tanıdı** ("ilk sıfır byte'ı bulup indeksini döndürüyor") ve onu bildiği daha hızlı bir fonksiyonla değiştirdi. Bu optimizasyona **idiom recognition** (kalıp tanıma) denir; aynı şey `memset` ve `memcpy` gibi döngüler için de yapılıyor.

Kendi sürümümüzü ölçmek istiyorsak, compiler'a bunu yapmamasını söylememiz gerekiyor. `-fno-builtin`, "standart kütüphane fonksiyonlarını özel olarak tanıma" demek:

```
$ clang -O2 -fno-builtin -S -o - mylen.c
_strlen_pointer:
	mov	x8, #0
LBB1_1:
	ldrb	w9, [x0, x8]
	add	x8, x8, #1
	cbnz	w9, LBB1_1
	sub	x0, x8, #1
	ret
```

Döngü geri geldi: bir byte oku (`ldrb`), sayacı artır (`add`), sıfır değilse başa dön (`cbnz`). `strlen_pointer` için compiler'ın ürettiği kod, bir **indeks** kullanıyor (`[x0, x8]`: `s + x8` adresinden oku); `strlen_index`'inkiyle neredeyse aynı. Ders 4.6'da da görmüştük: indeks ile pointer arasındaki seçim okunabilirlik meselesi, hız değil.

---

## 5. Ne kadar hızlı?

100 milyon `'a'`'lık (100 MB) bir yazının uzunluğunu her fonksiyonla 10 kez ölçelim. Zamanı ölçmek için `<time.h>`'teki `clock_gettime`'ı kullanan küçük bir yardımcı:

```c
#include <stdio.h>
#include <string.h>
#include <time.h>

#define N 100000000

size_t strlen_index(const char *s);
size_t strlen_pointer(const char *s);

char text[N + 1];

double seconds(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec / 1e9;
}

__attribute__((noinline))
void measure(const char *name, size_t (*length)(const char *)) {
    double start = seconds();
    size_t total = 0;
    for (int r = 0; r < 10; r++) {
        total += length(text);
    }
    double elapsed = seconds() - start;
    printf("%-15s %zu  %.3f s  %5.2f GB/s\n", name, total / 10, elapsed, 10.0 * N / elapsed / 1e9);
}

int main(void) {
    memset(text, 'a', N);
    measure("strlen_index", strlen_index);
    measure("strlen_pointer", strlen_pointer);
    measure("strlen (libc)", strlen);
    return 0;
}
```

`measure`, Ders 4.11'deki gibi ölçülecek fonksiyonu bir **fonksiyon pointer'ı** olarak alıyor. `__attribute__((noinline))` clang'e özel bir işaret: "bu fonksiyonu çağrıldığı yere yerleştirme". İlk denemede bu satır yoktu, ve standart `strlen` için **542 GB/s** gibi imkânsız bir sonuç çıktı: clang, `measure`'ı `main`'in içine yerleştirince `strlen(text)`'in 10 kez aynı sonucu vereceğini anlamış ve onu bir kez çağırmıştı. Ölçüm yaparken compiler'ın ölçtüğün işi silmediğinden emin olmak, ölçümün kendisi kadar önemli.

`CLOCK_MONOTONIC`, geriye hiç gitmeyen bir saat (bilgisayarın saati ayarlansa bile). `tv_sec` saniyeyi, `tv_nsec` nanosaniyeyi tutuyor.

Bilgisayarımızda (Apple M2):

| Derleme | `strlen_index` | `strlen_pointer` | `strlen` (libc) |
| --- | --- | --- | --- |
| `-O0` | 1,67 GB/s | 1,74 GB/s | 53,8 GB/s |
| `-O2`, `mylen.c` `-fno-builtin` ile | 3,4 GB/s | 3,5 GB/s | 53,7 GB/s |
| `-O2` | 28,6 GB/s | 42,6 GB/s | 47,9 GB/s |

Okuması:

- **`-O0`'dan `-O2`'ye** kendi döngümüz iki kat hızlandı: `-O0`'da sayaç her adımda belleğe yazılıp okunuyordu (Ders 2.6'daki debug derlemesi), `-O2`'de bir register'da duruyor.
- **`-O2 -fno-builtin`**, kendi döngümüzün gerçek hızı: saniyede yaklaşık 3,5 milyar byte. M2 saniyede 3,5 milyar civarında döngü dönüyor; yani **her döngü turunda bir byte**.
- **Standart `strlen` 15 kat hızlı.** Her turda bir byte yerine bir seferde 16 byte'a bakıyor. Bunu nasıl yaptığını Faz 5'te (Ders 5.10, "word-at-a-time") bit hileleriyle, Faz 11'de SIMD komutlarıyla göreceğiz.
- **Son satırda üç sütun da aslında aynı fonksiyon**: Bölüm 4'teki `b _strlen`. Aradaki farklar ölçüm gürültüsü (ilk ölçülen fonksiyon, işlemcinin ve belleğin "ısınması" sırasında çalışıyor).

### Standart sürüm nasıl yazının dışını okumuyor?

16 byte'lık parçalarla okuyan bir fonksiyon, `'\0'` bir parçanın ortasındaysa, yazının **arkasındaki** byte'ları da okumuş oluyor. Ders 4.12'deki `letters` örneğinde bunun bir hata olduğunu söyledik; AddressSanitizer bizim kodumuzda bunu yakalardı. Standart `strlen` neden çökmüyor?

Kısa cevap: parçaları **hizalı** adreslerden, yani 16'nın katı adreslerden okuyor, ve işletim sistemi belleği 4 KB'lık (ya da bu makinede 16 KB'lık) **sayfalarla** yönetiyor. 16'nın katında başlayan 16 byte'lık bir parça asla iki sayfanın arasına düşmüyor; yazının son byte'ı geçerli bir sayfadaysa, aynı parçadaki diğer byte'lar da o sayfada. Okumak çökmüyor, ve fazladan okunan byte'lar sonuca karışmıyor. Bu, C standardının **sana** izin vermediği ama standart kütüphanenin, makineyi bildiği için yapabildiği bir şey. Ders 4.21'de sayfaları, Faz 5'te bu tekniği ayrıntısıyla göreceğiz.

---

## 6. Gizli maliyet: döngü koşulunda strlen

`strlen` her çağrıldığında yazıyı **baştan sona** okuyor; $O(n)$ bir işlem (Ders 4.2). Bunu unutmak, C'nin en yaygın performans hatalarından birine yol açıyor:

```c
void upper_slow(char *s) {
    for (size_t i = 0; i < strlen(s); i++) {
        if (s[i] >= 'a' && s[i] <= 'z') {
            s[i] = s[i] - ('a' - 'A');
        }
    }
}

void upper_fast(char *s) {
    size_t n = strlen(s);
    for (size_t i = 0; i < n; i++) {
        if (s[i] >= 'a' && s[i] <= 'z') {
            s[i] = s[i] - ('a' - 'A');
        }
    }
}
```

Tek fark, `strlen(s)`'nin döngü koşulunda mı yoksa döngüden önce mi çağrıldığı. `-O2` ile:

```
n =   10000  slow 0.0040 s  fast 0.000016 s
n =  100000  slow 0.2119 s  fast 0.000047 s
n = 1000000  slow 18.2728 s  fast 0.000341 s
```

Bir milyon karakterlik bir yazıyı büyük harfe çevirmek **18 saniye** ile **0,3 milisaniye** arasında: 50 bin kat. Yazı 10 kat uzayınca `upper_slow` yaklaşık 85 kat yavaşladı; `upper_fast` 10 kat civarında.

`upper_slow`, `i`'nin her değeri için `strlen`'i çağırıyor; her çağrı $n$ byte okuyor. Toplam $n \times n = n^2$ byte. Ders 4.2'deki dille: $O(n)$ olması gereken bir döngü $O(n^2)$ oldu.

Compiler bunu neden düzeltmedi? Çünkü döngü `s[i]`'ye **yazıyor**. Bir harfi değiştirmek, compiler'ın gözünde yazının uzunluğunu değiştirebilir (bir harfin yerine `'\0'` yazılsaydı?). Her turda `strlen`'i yeniden çağırmak zorunda. Biz `'a'`–`'z'` arasındaki bir harfin `'\0'` olmayacağını biliyoruz; compiler bunu çıkaramıyor.

Kural: **bir döngü bir yazının uzunluğuna ihtiyaç duyuyorsa, uzunluğu bir kez hesapla**; ya da hiç hesaplama, `'\0'`'a kadar ilerle (`for (char *p = s; *p != '\0'; p++)`). Ders 4.15'te aynı hatanın `strcat` ile çok daha sinsi bir halini göreceğiz.

### `size_t` çıkarması

Ders 3.6'dan hatırlatma: `strlen` bir `size_t` döndürüyor. İki yazıdan hangisinin uzun olduğunu `strlen(a) - strlen(b) > 0` ile sormak, uzunluklar eşit olmadıkça **her zaman** doğru verir; çünkü `3 - 5` bir `size_t`'de 2⁶⁴ − 2. Doğrusu `strlen(a) > strlen(b)`.

---

## Alıştırmalar

**1** – `strlen_pointer`'ı `while (*p++ != '\0')` ile, döngü gövdesi boş olacak şekilde yeniden yaz. Dönüş değeri ne olmalı? Bölüm 3'teki testlerle doğrula.

**2** – `size_t strnlen(const char *s, size_t maxlen)` POSIX'te var: en fazla `maxlen` byte'a bakıyor; o sürede `'\0'` bulamazsa `maxlen` döndürüyor. Yaz. Ders 4.12'deki `letters` (`'\0'`'sız 4 byte'lık array) için `strnlen(letters, sizeof letters)` güvenli mi?

**3** – Ders 4.12'deki `read_int`'te `strchr(line, '\n') == NULL` kontrolü vardı. Aynı kontrolü `strlen` ile, `line`'ın son karakterine bakarak yaz. `fgets` hiç karakter okumadan `'\0'` döndüremeyeceğine göre `strlen(line) - 1` güvenli mi?

**4** – Bölüm 6'daki `upper_slow`'u, büyük harfe çevirme satırını kaldırıp sadece küçük harfleri **sayan** bir fonksiyona dönüştür (yazıya hiç yazmasın). `-O2` ile ölç. Hâlâ yavaş mı? Neden?

**5** – Bölüm 5'teki `measure`'dan `__attribute__((noinline))`'ı kaldırıp `-O2` ile ölç. Hangi satır değişti? Kendi fonksiyonlarımızın (`-fno-builtin` ile ayrı derlenmiş) sonuçları neden değişmedi?

<details>
<summary>Cevaplar</summary>

**1** –

```c
size_t strlen_post(const char *s) {
    const char *p = s;
    while (*p++ != '\0') {
    }
    return (size_t)(p - s - 1);
}
```

`*p++`, `*p`'yi okuyup **sonra** `p`'yi artırıyor (Ders 4.6). `'\0'` okunduğunda da artırma yapılıyor; döngü bittiğinde `p`, `'\0'`'ın **bir sonrasını** gösteriyor. Bu yüzden `- 1`. Bu bir sonrası adres, Ders 4.6'daki kurala göre geçerli (array'in bir sonrası). Boş bir `while` gövdesi `{}` ile yazılmalı; `while (...);` da çalışır ama bir sonraki satırın döngüye ait olduğu yanılgısına davetiye çıkarır.

**2** –

```c
size_t strnlen_mine(const char *s, size_t maxlen) {
    size_t n = 0;
    while (n < maxlen && s[n] != '\0') {
        n++;
    }
    return n;
}
```

`n < maxlen` kontrolü **önce** yapılıyor; `&&`'nin kısa devresi (Ders 3.17) sayesinde `s[maxlen]` hiç okunmuyor. `strnlen(letters, 4)` güvenli ve 4 döndürüyor: dört byte'a bakıp `'\0'` bulamadı. Sonuç "yazı en az 4 karakter" demek; `letters`'ı `%s` ile yazdırmak hâlâ güvenli değil.

**3** –

```c
size_t length = strlen(line);
if (line[length - 1] != '\n' && !feof(stdin)) {
```

`fgets`, `NULL` döndürmediyse en az bir karakter okumuş demek; `length` en az 1, `length - 1` güvenli. `fgets`'in dönüş değerini kontrol etmeden bu satırı yazmak, boş bir tamponda `0 - 1` = 2⁶⁴ − 1 indeksiyle okuma demek. (Bir uç durum: giriş bir `'\0'` byte'ı içeriyorsa `strlen` onu yazının sonu sanar ve `length` 0 olabilir. Klavyeden pek gelmez, ama bir dosyadan gelebilir.)

**4** –

```c
size_t count_lower(const char *s) {
    size_t count = 0;
    for (size_t i = 0; i < strlen(s); i++) {
        if (s[i] >= 'a' && s[i] <= 'z') {
            count++;
        }
    }
    return count;
}
```

Bu sefer yavaş **değil**: bir milyon karakter için `fast` sürümle aynı mertebede. Döngü yazıya yazmadığı ve `s` `const char *` olduğu için, compiler `strlen(s)`'nin her turda aynı sonucu vereceğini kanıtlayabiliyor ve çağrıyı döngünün dışına taşıyor (loop-invariant code motion). Ama bu bir **optimizasyon**: `-O0`'da yine kareli zaman. Kodun hızlı olması için compiler'ın akıllı olmasına güvenmek yerine, uzunluğu bir kez hesaplamak daha sağlam.

**5** – Standart `strlen`'in satırı imkânsız bir hıza çıkar (bizim ölçümümüzde 460–540 GB/s): `measure` `main`'e yerleştirilince clang `length`'in `strlen` olduğunu görüyor, `text`'in 10 çağrı arasında değişmediğini biliyor ve `strlen(text)`'i bir kez hesaplıyor. Kendi fonksiyonlarımız ayrı bir dosyada ve `-fno-builtin` ile derlendiği için clang onların ne yaptığını bilmiyor; her çağrının bir yan etkisi olabileceğini varsayıp 10 kez çağırıyor. (`-fno-builtin` olmadan derlenseydi `mylen.c`, Bölüm 4'e göre `strlen`'e atlardı; ama `main`'i derlerken clang bunu da bilemezdi, çünkü iki dosya ayrı ayrı derleniyor.)

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.4: `strlen`'in pointer farkıyla yazılması.
- C standardı (ISO/IEC 9899:2018), §7.24.6.3: `strlen`; §7.1.3: standart kütüphane adlarının ayrılmış olması.
- POSIX.1-2017, `strnlen`.
- Jon Bentley, *Programming Pearls* (2. baskı), Bölüm 8 ve Ek 3: maliyet modelleri ve döngü içindeki gizli çağrılar.

**Sıradaki ders:** `strcpy` ve `strncpy` sıfırdan. Tampon taşmasının neden bir güvenlik açığı olduğu, `strncpy`'nin `'\0'` bırakmama tuzağı ve `strlcpy`.
