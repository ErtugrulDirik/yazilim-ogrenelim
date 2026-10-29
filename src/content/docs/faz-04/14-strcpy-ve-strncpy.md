---
title: "4.14 strcpy ve strncpy sıfırdan"
description: "Bir yazıyı kopyalamak: strcpy'nin iki sürümü ve K&R'ın while ((*d++ = *s++)) deyimi, hedefin boyutunu bilmemenin yol açtığı tampon taşması, taşmanın komşu veriyi bozması, modern derleyicinin savunmaları (fortify, stack koruyucusu), strncpy'nin '\\0' bırakmama ve boşuna dolgu tuzakları, ve kesilmeyi dürüstçe bildiren strlcpy."
---

Ders 3.19'da `strcpy`'yi bir kez kullandık ve "Ders 4.14'te kendimiz yazacağız" dedik. Ders 3.16'daki `itoa`'da da bir yazının, ayrılan yerin bir byte ötesine taştığını AddressSanitizer ile görmüştük.

`strcpy`, yazmak için C'nin en basit fonksiyonlarından biri. Ama aynı zamanda, güvenli olmayan C kodunun ders kitabı örneği. İkisinin sebebi aynı: **hedefin ne kadar büyük olduğunu bilmiyor.** Bu dersin asıl konusu kopyalamanın kendisi değil; hedefin boyutunu bilmemenin neden tehlikeli olduğu ve bunu önlemenin yolları.

---

## 1. strcpy

```c
char *strcpy(char *restrict dest, const char *restrict src);
```

- `src`'deki yazıyı, `'\0'` dahil, `dest`'in gösterdiği yere kopyalıyor.
- `src` sadece okunuyor (`const`), `dest`'e yazılıyor (Ders 4.8).
- `dest`'i döndürüyor.
- `restrict`: "bu iki pointer'ın gösterdiği bölgeler çakışmıyor" sözü. Ders 4.7'deki aliasing'in tersi; ayrıntısını Ders 4.18'de göreceğiz. Şimdilik: `dest` ile `src` üst üste binerse sonuç undefined behavior.

İmzanın **hiçbir yerinde** `dest`'in boyutu yok. Ders 4.1'e göre `dest` bir pointer; fonksiyonun, arkasında kaç byte olduğunu öğrenmesinin yolu yok. Yeterli yer olduğundan emin olmak tamamen çağıranın işi: en az `strlen(src) + 1` byte.

### İndeksle

```c
#include <stddef.h>

char *strcpy_index(char *dest, const char *src) {
    size_t i = 0;
    while (src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';
    return dest;
}
```

Döngü `'\0'`'ı kopyalamıyor; onu ayrıca yazıyoruz (Ders 3.16'daki `itoa`'nın sonundaki satırla aynı). `src[i]` `'\0'` olunca döngü bitiyor, `dest[i] = '\0'` sonlandırıyor.

### Pointer deyimiyle

K&R §5.5'teki ünlü sürüm:

```c
char *strcpy_pointer(char *dest, const char *src) {
    char *d = dest;
    while ((*d++ = *src++) != '\0') {
    }
    return dest;
}
```

`*d++ = *src++` tek satırda üç iş yapıyor (Ders 4.6'daki `*p++`):

1. `*src`'yi oku, `*d`'ye yaz.
2. İkisini de bir ilerlet.
3. **Atamanın değeri**, yazılan karakter. `while`, bu değeri `'\0'` ile karşılaştırıyor.

`'\0'` de kopyalanıyor (atama yapılıyor, sonra döngü bitiyor). C kodunda en çok bu biçimiyle karşılaşırsın; ama okunması güç, ve `strcpy_index`'le aynı işi yapıyor. Dıştaki parantez (`(*d++ = *src++)`) şart: atamanın değerini karşılaştırdığımızı hem compiler'a hem okuyucuya söylüyor; onsuz clang `-Wparentheses` ile "bunu karşılaştırma değil atama mı demek istedin?" diye uyarır.

İki sürümü de `<string.h>`'teki `strcpy`'yle 184 binden fazla girdide (her uzunlukta, rastgele içerikli yazılar) karşılaştırdık; `-fsanitize=address,undefined` ile tek bir fark ya da sınır dışı erişim çıkmadı. Doğru kullanıldığında ikisi de çalışıyor. Sorun "doğru kullanıldığında"da.

---

## 2. Boyutu bilmemenin bedeli

Bir programın, kullanıcının adını alıp sakladığını düşünelim:

```c
#include <stdio.h>
#include <string.h>

struct User {
    char name[8];
    int is_admin;
};

int main(int argc, char **argv) {
    if (argc != 2) {
        printf("kullanim: %s isim\n", argv[0]);
        return 1;
    }
    struct User user = {"", 0};
    strcpy(user.name, argv[1]);
    printf("name = %s, is_admin = %d (0x%x)\n",
           user.name, user.is_admin, (unsigned)user.is_admin);
    return 0;
}
```

`name` 8 byte, ve hemen arkasında `is_admin` duruyor (Ders 4.4'teki struct yerleşimi). İsim 8 byte'a sığdığı sürece sorun yok:

```
$ ./admin Ali
name = Ali, is_admin = 0 (0x0)
```

Ama 8 byte'tan uzun bir isim verilirse, `strcpy` durmuyor — `'\0'`'a kadar yazmaya devam ediyor, ve `name`'in sınırını aşıp **`is_admin`'in byte'larına** yazıyor:

```
$ ./admin Deniz123X
name = Deniz123X, is_admin = 88 (0x58)
```

`is_admin` 0'dı; şimdi 88 (`'X'`'in ASCII değeri). Program hiç niyet etmediği halde `is_admin`'i sıfırdan farklı bir değere getirdi. Bu, **tampon taşması** (buffer overflow). Verinin bir parçasına yazarken, hemen yanındaki başka bir veriyi kazara bozduk.

Fark edilmesi güç olan nokta: `strcpy`'nin kodunda hata yok, `struct User`'ın tanımında hata yok. Hata, 8 byte'lık bir alana 8 byte'tan uzun bir şey kopyalanabileceğini **kimsenin kontrol etmemesinde**. Girdi program dışından (burada komut satırından) geldiği için, programı yazan kişinin "en fazla 7 harf gelir" varsayımı girdiyi veren tarafından bozulabiliyor. Güvenlik açıklarının çoğu tam olarak bu kalıpta: bir yerde yapılmış sessiz bir boyut varsayımı.

Taşma yerel bir array'de olduğunda sonuç daha ağır olabilir: Ders 4.4'teki stack'te, `greet`'in `char buffer[16]`'sının arkasında fonksiyonun **geri dönüş adresi** (Ders 4.7'deki, fonksiyon bitince nereye döneceği bilgisi) duruyor. Yeterince uzun bir girdi onu da ezer; program geri dönerken geçersiz bir adrese gitmeye çalışıp çöker. LLDB ile baktığımızda çöken adres, girdideki `'A'` byte'larının kendisi oluyor (`0x4141414141414141`): programın akışı, dışarıdan gelen veriyle bozulmuş durumda. Buna "stack smashing" (yığını parçalamak) denir, ve kötü niyetli bir girdinin programı istenmeyen bir yere yönlendirmesinin klasik yoludur.

---

## 3. Derleyici neden çoğu zaman engelliyor

Yukarıdaki `Deniz123X` çıktısını görmek için programı aslında bir savunmayı **kapatarak** derledik. macOS'ta `clang`, normalde iki koruma ekliyor:

**Fortify (`_FORTIFY_SOURCE`).** Optimizasyonla (`-O1` ve üstü) derlerken clang, hedefin boyutunu derleme sırasında bildiği `strcpy` çağrılarını, boyut kontrol eden bir sürümle değiştiriyor. Önişlemci çıktısında (Ders 2.11) `strcpy` yerine şunu görüyoruz:

```
__builtin___strcpy_chk(user.name, argv[1], __builtin_object_size(user.name, ...))
```

`__builtin_object_size`, `user.name`'in 8 byte olduğunu derleme sırasında hesaplıyor; `_chk` sürümü çalışırken bunu aşan bir kopyada programı hemen durduruyor:

```
$ clang -O2 admin.c -o admin
$ ./admin Deniz123X
exit=133          # program durduruldu, is_admin'e yazılmadan
```

**Stack koruyucusu (stack protector).** Derleyici, yerel array'i olan fonksiyonların dönüş adresinin önüne rastgele bir "bekçi değeri" (canary) koyuyor; fonksiyon dönerken bu değer değişmişse bir taşma olmuş demektir ve program durduruluyor. Linux'ta mesajı açıkça görüyoruz:

```
$ ./smash AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
*** stack smashing detected ***: terminated
Aborted
```

Bu savunmalar değerli, ama **garanti değil**: fortify sadece boyutu derleme sırasında bilinen çağrıları kapsıyor (boyut çalışırken belirlenirse koruyamaz), stack koruyucusu da sadece dönüş adresini koruyor, Bölüm 2'deki `is_admin` gibi komşu veriyi değil. Doğru yaklaşım savunmalara güvenmek değil, **taşmayı baştan imkânsız kılan** fonksiyonları kullanmak. `strcpy`'nin yerini tutacak iki aday var.

---

## 4. strncpy: niyeti iyi, tuzakları çok

`strncpy`, en fazla `n` byte yazarak taşmayı sınırlamayı amaçlıyor:

```c
char *strncpy(char *restrict dest, const char *restrict src, size_t n);
```

```c
char *strncpy_mine(char *dest, const char *src, size_t n) {
    size_t i = 0;
    while (i < n && src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }
    while (i < n) {
        dest[i] = '\0';
        i++;
    }
    return dest;
}
```

İki döngü, iki tuzak:

**Tuzak 1: `'\0'` koymayabilir.** `src`, `n` byte'tan uzunsa, ilk döngü tam `n` byte kopyalayıp durur ve **sonlandırıcı yazılmaz**. Sonuç artık bir string değil (Ders 4.12):

```c
char word[8];
strncpy(word, "kelebekler", sizeof word);
printf("%s\n", word);
```

```
kelebeklX
```

`word`'de `"kelebekl"` var ama `'\0'` yok; `printf` arkasındaki çöp byte'ı da (`X`) yazdırıp orada rastladığı ilk `'\0'`'da durdu. Tam olarak Ders 4.12'deki `letters` hatası, bu sefer "güvenli" sandığımız fonksiyonun yüzünden. AddressSanitizer bunu sınır dışı okuma olarak yakalıyor. "`strncpy`'den sonra her zaman `dest[n-1] = '\0'` yaz" kuralı gerekiyor — fonksiyonun kendisinin yapması gerekeni elle tamamlamak.

**Tuzak 2: kalanı sıfırla doldurur.** `src`, `n`'den kısaysa ikinci döngü, `dest`'in geri kalan **bütün** byte'larını `'\0'` ile dolduruyor:

```c
char a[8];
strncpy(a, "kedi", sizeof a);   // k e d i \0 \0 \0 \0
```

`"kedi"` için 5 byte yeterdi; `strncpy` 8 byte'ın hepsine yazdı. Küçük tamponlarda fark etmez, ama büyük bir tampona kısa bir yazı kopyalarken boşuna iş: bir megabaytlık tampona `"kedi"` kopyalamak, bütün bir megabaytı sıfırlıyor. Ölçtük: aynı işi 1000 kez yaptığımızda `strncpy` ile 11 milisaniye, kesme yapan `strlcpy` ile 0,02 milisaniye.

`strncpy` aslında string'ler için tasarlanmamış: eski Unix'te, sonu `'\0'` olmayan **sabit uzunluklu** alanlar (örneğin dosya adları) içindi. String kısaltmak için kullanmak onu yanlış kullanmak.

---

## 5. strlcpy: dürüst olanı

OpenBSD'nin eklediği `strlcpy`, `strncpy`'nin iki tuzağını da düzeltiyor:

```c
size_t strlcpy(char *dest, const char *src, size_t size);
```

- `size`, hedefin **toplam** boyutu (byte sayısı, `strncpy`'deki gibi "kaç byte kopyala" değil).
- **Her zaman** `'\0'` ile sonlandırıyor (`size > 0` ise).
- Kalanı sıfırla **doldurmuyor**.
- **`strlen(src)`'yi döndürüyor**: kaynağın tam uzunluğu. Bu dönüş değeri `size`'dan büyük ya da eşitse, yazı **kesilmiş** demektir.

```c
size_t strlcpy_mine(char *dest, const char *src, size_t size) {
    size_t i = 0;
    if (size > 0) {
        while (i < size - 1 && src[i] != '\0') {
            dest[i] = src[i];
            i++;
        }
        dest[i] = '\0';
    }
    while (src[i] != '\0') {
        i++;
    }
    return i;
}
```

İlk döngü en fazla `size - 1` byte kopyalayıp mutlaka sonlandırıyor; ikinci döngü, kaynağın geri kalanını kopyalamadan sadece **sayıyor** ki doğru uzunluğu döndürebilsin.

```c
char c[8];
size_t r2 = strlcpy(c, "kelebekler", sizeof c);   // c = "kelebek"
if (r2 >= sizeof c) {
    printf("kesildi: %zu karakterin %zu tanesi sigdi\n", r2, sizeof c - 1);
}
```

```
kesildi: 10 karakterin 7 tanesi sigdi
```

Fark, dönüş değerinin **dürüstlüğü**: `strlcpy` "aslında 10 karakter vardı, 7'si sığdı" diyor, ve program buna bakıp kesilmeyi fark edebiliyor. `strncpy` sessizce kesiyor, hatta sonlandırmayı atlayabiliyor. Sessiz kesme de bir hata kaynağı (bir dosya adının yarısı başka bir dosyaya işaret edebilir), ama en azından taşma değil.

`strlcpy` C standardında yok; macOS, BSD'ler ve `<bsd/string.h>` ile Linux'ta var. C11'in `strcpy_s`'i benzer bir amaç güdüyor ama imzası ve yaygınlığı farklı. Ders 4.30'da `libmystr`'e kendi `strlcpy`'mizi koyacağız; projelerde taşmaya karşı en sade savunma bu.

| | sonlandırır mı? | kalanı doldurur mu? | kesilmeyi bildirir mi? |
| --- | --- | --- | --- |
| `strcpy` | evet | — | taşar (boyut kontrolü yok) |
| `strncpy` | **gerekmez** | evet (yavaş) | hayır |
| `strlcpy` | evet | hayır | evet (dönüş değeriyle) |

---

## Alıştırmalar

**1** – `strcpy_pointer`'daki dıştaki parantezi kaldır: `while (*d++ = *src++)`. clang ne diyor? Parantezi `while ((*d++ = *src++))` diye koymak yerine `!= '\0'` eklemek (`while ((*d++ = *src++) != '\0')`) niye daha açık?

**2** – `strcat` gibi davranan değil, `dest`'in sonuna `src`'yi **güvenli** ekleyen bir fonksiyon imzası tasarla: elinde yalnızca `dest`, `src` ve `dest`'in toplam boyutu var. Hangi bilgileri döndürmek istersin? (Bu, Ders 4.15'teki `strlcat`.)

**3** – Bölüm 2'deki `struct User`'ı taşmaya karşı güvenli hale getir: `strcpy` yerine `strlcpy` kullan ve isim 8 byte'a sığmazsa kullanıcıya haber ver. `is_admin` artık hiçbir isimle değişebilir mi?

**4** – `strncpy_mine`'ı, Bölüm 4'teki "her zaman sonlandır" kuralını içine alacak şekilde değiştir (`dest[n-1] = '\0'`). Bu artık `strncpy`'den farklı; hangi durumda `strlcpy`'den de farklı davranır?

**5** – `strlcpy_mine`'da `size == 0` çağrısı ne yapıyor, satır satır izle. `dest`'e hiç yazılmıyor, ama fonksiyon yine de bir sayı döndürüyor: hangi sayı, ve bu neden kullanışlı?

<details>
<summary>Cevaplar</summary>

**1** – Parantezsiz `while (*d++ = *src++)` için clang uyarır: `using the result of an assignment as a condition without parentheses [-Wparentheses]`, ve "eşitlik mi (`==`) demek istedin?" diye sorar. Bu uyarı değerli, çünkü `while (x = y)` çoğu zaman `while (x == y)`'nin yazım hatasıdır. Dıştaki parantez "bilerek atama yapıyorum" demek. Ama `!= '\0'` eklemek daha da açık: karşılaştırmanın neye karşı yapıldığını (sonlandırıcı) gösteriyor; okuyucu "atamanın sonucu `'\0'` mı?" sorusunu doğrudan görüyor.

**2** –

```c
size_t strlcat_mine(char *dest, const char *src, size_t size);
```

`size`, `dest`'in **toplam** boyutu (mevcut yazı + eklenecek + `'\0'`). Dönüş değeri, kesme olmasaydı oluşacak toplam uzunluk (`strlen(dest) + strlen(src)`) olmalı; `>= size` ise ekleme kesilmiş demektir. `strlcpy`'nin mantığının aynısı, sadece `dest`'in mevcut sonundan başlıyor. Ders 4.15'te bunu yazarken "mevcut sonu bulmanın" tekrar tekrar `strlen` çağırmaya dönüşmesinin tehlikesine değineceğiz.

**3** –

```c
struct User user = {"", 0};
if (strlcpy(user.name, argv[1], sizeof user.name) >= sizeof user.name) {
    printf("isim cok uzun (en fazla %zu karakter)\n", sizeof user.name - 1);
    return 1;
}
```

Artık `name`'e en fazla 7 karakter + `'\0'` yazılıyor; `strlcpy` sınırı asla aşmıyor, dolayısıyla `is_admin`'e hiçbir isimle dokunulmuyor. Uzun isim bir hata olarak reddediliyor, sessizce kesilmiyor.

**4** –

```c
char *strncpy_safe(char *dest, const char *src, size_t n) {
    if (n == 0) {
        return dest;
    }
    size_t i = 0;
    while (i < n - 1 && src[i] != '\0') {
        dest[i] = src[i];
        i++;
    }
    dest[i] = '\0';
    return dest;
}
```

Artık en fazla `n - 1` byte kopyalayıp mutlaka sonlandırıyor; `strncpy`'nin 1. tuzağı yok. Ama hâlâ `strlcpy`'den farklı: `strlcpy` kaynağın **gerçek uzunluğunu** döndürüp kesilmeyi bildiriyor; bu sürüm `dest` döndürüyor, çağıran kesme olup olmadığını anlayamıyor. Dönüş değeri, `strncpy` ile `strlcpy` arasındaki asıl fark.

**5** – `size == 0` iken: `if (size > 0)` bloğu atlanıyor, yani `dest`'e **hiç yazılmıyor** (0 byte'lık bir tampona yazmak taşma olurdu; bu doğru). Sonra ikinci döngü `src`'yi baştan sona sayıyor ve `strlen(src)`'yi döndürüyor. Kullanışlı, çünkü `strlcpy(NULL, src, 0)` ile hiçbir şey kopyalamadan "bu yazı için kaç byte'lık tampon gerekir?" sorusunu sorabiliyorsun; dönen değer + 1 kadar yer ayırıp (Ders 4.22'deki `malloc`) sonra gerçekten kopyalayabilirsin.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.5: `strcpy` ve `*d++ = *s++` deyimi.
- C standardı (ISO/IEC 9899:2018), §7.24.2.3 (`strcpy`), §7.24.2.4 (`strncpy`); K.3.7.1.3 (`strcpy_s`).
- Todd C. Miller & Theo de Raadt, "strlcpy and strlcat — Consistent, Safe, String Copy and Concatenation" (USENIX 1999): `strlcpy`'nin tasarım gerekçesi.
- SEI CERT C Coding Standard, STR31-C (hedefte yeterli yer olduğundan emin olmak), STR32-C (string'leri sonlandırmak).
- Matt Bishop, *Computer Security: Art and Science*, tampon taşması bölümü: boyut varsayımlarının neden açık yarattığı.

**Sıradaki ders:** `strcat` ve `strncat` sıfırdan. Her eklemede sonu baştan aramanın maliyeti — "Shlemiel the painter" problemi.
