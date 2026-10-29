---
title: "4.30 Faz projesi: libmystr"
description: "Faz 4'ün bitiş projesi: bu fazda tek tek yazdığımız string fonksiyonlarını bir kütüphanede toplamak. mystr.h ve mystr.c, standart sürümle karşılaştıran bir test programı, ar ile statik kütüphane (libmystr.a) oluşturmak, -L ve -l ile bağlamak ve her şeyi derleyen, test eden, sanitizer'la çalıştıran bir Makefile."
windowsNotu: "WSL içinde çalış; ar ve statik kütüphaneler orada aynı şekilde çalışır."
---

Faz 4'ün sonuna geldin. Pointer'ları, belleği ve `<string.h>`'in neredeyse tamamını sıfırdan yazdın. Bu projede hepsini bir araya getiriyoruz: Ders 4.13–4.19'da tek tek yazdığımız string fonksiyonlarını **kendi kütüphanemizde** toplayacak, bir test programıyla doğrulayacak, ve `ar` ile gerçek bir **statik kütüphane** (`libmystr.a`) haline getireceğiz.

Yeni bir algoritma yok; fonksiyonları zaten yazdın. Bu ders, onları **paketlemekle** ilgili: çok dosyalı bir proje (Ders 2.11), bir kütüphane, ve her şeyi derleyip test eden bir `Makefile`. Gerçek bir C kütüphanesinin nasıl dağıtıldığını göreceksin.

:::tip[Önce kendin yaz]
Bu bir proje dersi. Gereksinimleri okuduktan sonra **kendi çözümünü yaz**: fonksiyonları bu fazdan topla, kendi testini ve Makefile'ını kur. Bizim çözümümüz aşağıda, kapalı kutularda. Takıldığın yerde sadece ilgili parçaya bak.
:::

---

## 1. Gereksinimler

Bir statik kütüphane projesi:

- **`mystr.h`**: kütüphanenin **arayüzü** (Ders 2.11). Fonksiyon bildirimleri, bir include koruyucusu (`#ifndef`).
- **`mystr.c`**: fonksiyonların **gerçeklemesi**. Ders 4.13–4.19'dan en az şunlar: `my_strlen`, `my_strcpy`, `my_strlcpy`, `my_strcat`, `my_strcmp`, `my_strchr`, `my_strstr`, ve Ders 4.22'den `my_strdup`.
- **`test_mystr.c`**: her fonksiyonu, mümkünse `<string.h>`'teki standart sürümle (Ders 4.13'ten beri yaptığımız gibi) karşılaştıran bir test programı. Kenar durumları (boş yazı, bulunamama, kesme, yüksek bitli byte) içermeli.
- **`libmystr.a`**: `ar` ile oluşturulan statik kütüphane.
- **`Makefile`**: kütüphaneyi derler, testi kütüphaneye **bağlar**, ve bir `check` hedefiyle çalıştırır. `-Wall -Wextra -Werror` ile hiç uyarı vermemeli, sanitizer'larla (Ders 2.12, 4.22) hiç hata raporlamamalı.

**Adlandırma:** Ders 4.13'teki kural — fonksiyonlara standart adları (`strlen`) **vermiyoruz**; `my_` öneki kullanıyoruz ki standart kütüphaneyle çakışmasın ve test programında ikisini yan yana çağırabilelim.

---

## 2. Statik kütüphane nedir?

Şimdiye kadar çok dosyalı programlarda (Ders 2.11) `.o` dosyalarını doğrudan bağlıyorduk: `clang main.o health.o -o program`. Bir **statik kütüphane**, birden çok `.o` dosyasını tek bir arşivde toplayan bir dosya (`.a` uzantılı). `ar` (archiver) ile oluşturulur — aslında `tar` gibi bir arşivleyici, ama derleyicinin anladığı biçimde.

```
ar rcs libmystr.a mystr.o
```

- `r`: dosyaları arşive ekle (varsa değiştir).
- `c`: arşiv yoksa oluştur, uyarı verme.
- `s`: bir **sembol dizini** yaz (içindeki fonksiyonların listesi, bağlayıcının hızlı bulması için).

Sonra bir programı bu kütüphaneye bağlarken, `.o` yerine kütüphaneyi veriyoruz:

```
clang test_mystr.c -L. -lmystr -o test
```

- `-L.`: kütüphaneleri **bu dizinde** de ara.
- `-lmystr`: `libmystr.a` adlı kütüphaneye bağla. (`-l` önekine `lib`, soneke `.a` ekler; bu yüzden isim `libmystr.a` olmak zorunda.)

Bağlayıcı, `test_mystr.c`'nin kullandığı `my_strlen`, `my_strcmp` gibi sembolleri kütüphanede bulup programa **kopyalar**. "Statik" olması bu: kullanılan fonksiyonların kodu programın kendi içine gömülür; program çalışırken kütüphane dosyasına ihtiyaç kalmaz. (Ders 4.21'de `libc.so.6`'yı görmüştük — o bir **paylaşımlı** kütüphane, kodu program içine gömülmez, çalışırken yüklenir. Statik ve paylaşımlı kütüphanelerin farkını Faz 10'da göreceğiz; `.a` statik olandır.)

`libc`'nin kendisi de böyle bir kütüphane; `strlen` çağırdığında aslında `libc`'ye bağlanıyorsun. `libmystr.a` ile, kendi `libc`'nin minyatür bir halini yapmış oluyorsun.

---

## 3. Tasarım

| Dosya | Görevi |
| --- | --- |
| `mystr.h` | Arayüz: bildirimler, include koruyucusu |
| `mystr.c` | Gerçekleme: Ders 4.13–4.19 ve 4.22'deki fonksiyonlar |
| `test_mystr.c` | Testler: standart sürümle karşılaştırma |
| `Makefile` | Derleme, kütüphane, test, sanitizer |

Test programında küçük bir yardımcı makro işi kolaylaştırıyor:

```c
#define CHECK(cond) do { \
    if (cond) { \
        passed++; \
    } else { \
        failed++; \
        printf("  BASARISIZ (%s:%d): %s\n", __FILE__, __LINE__, #cond); \
    } \
} while (0)
```

`do { ... } while (0)` Ders 4.9'daki makro kalıbı. `#cond`, makro argümanını **yazıya** çeviren önişlemci operatörü (stringizing): `CHECK(my_strlen("") == 0)` başarısız olursa, ekrana koşulun kendisini (`my_strlen("") == 0`) ve `__FILE__`/`__LINE__` ile satır numarasını yazar. Kendi küçük test çatını kurmanın en kısa yolu.

---

## 4. Bizim çözümümüz

<details>
<summary>mystr.h</summary>

```c
#ifndef MYSTR_H
#define MYSTR_H

#include <stddef.h>

size_t my_strlen(const char *s);
char  *my_strcpy(char *dest, const char *src);
size_t my_strlcpy(char *dest, const char *src, size_t size);
char  *my_strcat(char *dest, const char *src);
int    my_strcmp(const char *a, const char *b);
char  *my_strchr(const char *s, int c);
char  *my_strstr(const char *haystack, const char *needle);
char  *my_strdup(const char *s);

#endif
```

`#ifndef MYSTR_H` include koruyucusu (Ders 2.11): başlık iki kez include edilse bile bir kez işlenir. `size_t` için `<stddef.h>` (Ders 3.4).

</details>

<details>
<summary>mystr.c</summary>

```c
#include "mystr.h"
#include <stdlib.h>

size_t my_strlen(const char *s) {
    const char *p = s;
    while (*p != '\0') {
        p++;
    }
    return (size_t)(p - s);
}

char *my_strcpy(char *dest, const char *src) {
    char *d = dest;
    while ((*d++ = *src++) != '\0') {
    }
    return dest;
}

size_t my_strlcpy(char *dest, const char *src, size_t size) {
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

char *my_strcat(char *dest, const char *src) {
    char *d = dest;
    while (*d != '\0') {
        d++;
    }
    while ((*d++ = *src++) != '\0') {
    }
    return dest;
}

int my_strcmp(const char *a, const char *b) {
    const unsigned char *x = (const unsigned char *)a;
    const unsigned char *y = (const unsigned char *)b;
    while (*x != '\0' && *x == *y) {
        x++;
        y++;
    }
    return (int)*x - (int)*y;
}

char *my_strchr(const char *s, int c) {
    char target = (char)c;
    while (*s != '\0') {
        if (*s == target) {
            return (char *)s;
        }
        s++;
    }
    return (target == '\0') ? (char *)s : NULL;
}

char *my_strstr(const char *haystack, const char *needle) {
    if (*needle == '\0') {
        return (char *)haystack;
    }
    for (const char *h = haystack; *h != '\0'; h++) {
        const char *hp = h;
        const char *np = needle;
        while (*np != '\0' && *hp == *np) {
            hp++;
            np++;
        }
        if (*np == '\0') {
            return (char *)h;
        }
    }
    return NULL;
}

char *my_strdup(const char *s) {
    size_t n = my_strlen(s) + 1;
    char *copy = malloc(n);
    if (copy == NULL) {
        return NULL;
    }
    my_strcpy(copy, s);
    return copy;
}
```

Hepsi bu fazdan: `my_strlen` (Ders 4.13), `my_strcpy`/`my_strlcpy` (4.14), `my_strcat` (4.15), `my_strcmp` (4.16), `my_strchr`/`my_strstr` (4.17), `my_strdup` (4.22). `my_strdup` içeride kendi `my_strlen` ve `my_strcpy`'sini çağırıyor — kütüphane kendi parçalarını kullanıyor.

</details>

<details>
<summary>test_mystr.c</summary>

```c
#include "mystr.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int passed = 0;
static int failed = 0;

#define CHECK(cond) do { \
    if (cond) { \
        passed++; \
    } else { \
        failed++; \
        printf("  BASARISIZ (%s:%d): %s\n", __FILE__, __LINE__, #cond); \
    } \
} while (0)

int main(void) {
    char buf[64];

    CHECK(my_strlen("") == strlen(""));
    CHECK(my_strlen("merhaba") == strlen("merhaba"));

    my_strcpy(buf, "deneme");
    CHECK(strcmp(buf, "deneme") == 0);

    char small[4];
    size_t r = my_strlcpy(small, "uzunca", sizeof small);
    CHECK(r == 6);                          // kaynagin tam uzunlugu
    CHECK(strcmp(small, "uzu") == 0);       // kesildi ama sonlandi

    my_strcpy(buf, "ab");
    my_strcat(buf, "cd");
    CHECK(strcmp(buf, "abcd") == 0);

    CHECK((my_strcmp("a", "b") < 0) == (strcmp("a", "b") < 0));
    CHECK(my_strcmp("ayni", "ayni") == 0);
    CHECK(my_strcmp("\xc3z", "bz") > 0);    // unsigned char (Ders 4.16)

    CHECK(my_strchr("merhaba", 'h') == strchr("merhaba", 'h'));
    CHECK(my_strchr("merhaba", 'z') == NULL);

    CHECK(my_strstr("abcabc", "cab") == strstr("abcabc", "cab"));
    CHECK(my_strstr("abc", "xyz") == NULL);

    char *d = my_strdup("kopya");
    CHECK(d != NULL && strcmp(d, "kopya") == 0);
    free(d);

    printf("%d gecti, %d basarisiz\n", passed, failed);
    return failed == 0 ? 0 : 1;
}
```

Her test, kendi fonksiyonumuzu ya standart sürümle ya da bilinen bir sonuçla karşılaştırıyor. `main`'in dönüş değeri test sonucunu kabuğa bildiriyor (Ders 4.10): hepsi geçerse 0, biri bile başarısızsa 1 — böylece `make` ve CI sistemleri (Faz 10) başarısızlığı anlar.

</details>

<details>
<summary>Makefile</summary>

```makefile
CC = clang
CFLAGS = -Wall -Wextra -Werror -std=c17
AR = ar

libmystr.a: mystr.o
	$(AR) rcs $@ $^

mystr.o: mystr.c mystr.h
	$(CC) $(CFLAGS) -c mystr.c -o $@

test: test_mystr.c libmystr.a mystr.h
	$(CC) $(CFLAGS) test_mystr.c -L. -lmystr -o test

check: test
	./test

check-asan: test_mystr.c mystr.c mystr.h
	$(CC) $(CFLAGS) -fsanitize=address,undefined -g test_mystr.c mystr.c -o test_asan
	./test_asan

clean:
	rm -f mystr.o libmystr.a test test_asan

.PHONY: check check-asan clean
```

Ders 2.11'deki `Makefile`'ın üstüne iki yeni fikir:

- **`libmystr.a: mystr.o`** kuralı `ar` ile kütüphaneyi kuruyor. `$@` hedef (`libmystr.a`), `$^` bağımlılıklar (`mystr.o`) — Ders 2.11'deki otomatik değişkenler.
- **`test`** kuralı kütüphaneye `-L. -lmystr` ile bağlanıyor. `make` bağımlılık zincirini (Ders 2.11) kendisi çözüyor: `test`, `libmystr.a`'ya bağlı, o da `mystr.o`'ya, o da `mystr.c`'ye — biri değişince gerekli adımlar yeniden çalışıyor.
- **`check-asan`** ayrı bir hedef: sanitizer'larla (Ders 2.12, 4.22) kütüphaneyi değil kaynağı doğrudan derleyip test ediyor. Sanitizer, kütüphanenin içindeki bellek hatalarını da yakalamalı.

</details>

---

## 5. Çalıştırmak ve test etmek

```
$ make check
clang -Wall -Wextra -Werror -std=c17 -c mystr.c -o mystr.o
ar rcs libmystr.a mystr.o
clang -Wall -Wextra -Werror -std=c17 test_mystr.c -L. -lmystr -o test
./test
14 gecti, 0 basarisiz
```

Kütüphanenin içine `ar t` ile bakabilirsin (hangi `.o` dosyaları var), `nm` ile hangi fonksiyonları dışa açtığını görebilirsin:

```
$ ar t libmystr.a
__.SYMDEF SORTED
mystr.o

$ nm libmystr.a | grep my_str
0000000000000178 T _my_strcat
0000000000000288 T _my_strchr
00000000000001ec T _my_strcmp
0000000000000048 T _my_strcpy
000000000000041c T _my_strdup
0000000000000098 T _my_strlcpy
0000000000000000 T _my_strlen
0000000000000320 T _my_strstr
```

`T`, fonksiyonun kütüphane tarafından **dışa açıldığını** (text bölgesinde, Ders 4.21) gösteriyor. Bu, Ders 4.21'deki `/proc/self/maps`'te `libc.so.6`'nın yaptığının aynısı, statik hali. Son olarak sanitizer'larla:

```
$ make check-asan
...
14 gecti, 0 basarisiz
```

AddressSanitizer ve UBSan hiçbir hata bulmadı: kütüphanenin içinde sınır dışı erişim, use-after-free ya da undefined behavior yok.

---

## Faz 4 bitti

Bu fazda, Faz 2 ve 3'te "Faz 4'te göreceğiz" diye bıraktığımız her şeyi yazdık: `&`'in ne olduğu (Ders 4.4), `char *` (4.12), array'lerin neden kopyalanmadığı (4.1), `'\0'` ile biten yazılar (4.12). Ve çok daha fazlası:

- **Pointer'lar**: tanım, aritmetik, fonksiyonlara aktarım, `const`, `void *`, pointer'a pointer, fonksiyon pointer'ı (4.5–4.11).
- **`<string.h>`'in neredeyse tamamı** sıfırdan, her biri standart sürümle test edilmiş (4.13–4.20).
- **Bellek**: programın bellek düzeni, `malloc`/`free`, bellek hataları, dinamik dizi (4.21–4.24).
- **Veri yapıları**: struct, hizalama, union ve bit alanları (4.25–4.27).
- **Kendi allocator'larımız**: arena ve serbest liste (4.28–4.29).
- **Kendi kütüphanemiz**, `ar` ile paketlenmiş (4.30).

Artık C'nin belleği nasıl gördüğünü biliyorsun: her değerin bir adresi var, her pointer bir adres tutuyor, ve belleğin ömrünü sen yönetiyorsun. Bu, C'nin hem gücü hem tehlikesi; bu fazdaki araçlar (sanitizer, valgrind, `const` doğruluğu) tehlikeyi yönetmek için.

Bir sonraki faz **bit manipülasyonu**: Ders 3.18'de tanıştığımız `<<`, `>>`, `&`, `|` operatörlerini derinleştirip, bir sayının bitlerini saymaktan Ders 4.13'teki `strlen`'i "word-at-a-time" tekniğiyle (Ders 5.10) hızlandırmaya kadar gideceğiz.

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), Bölüm 5–6 ve §8.7: bu fazın çekirdek kaynağı.
- `ar(1)` ve `nm(1)` man sayfaları: statik kütüphane oluşturma ve inceleme.
- GNU Make kılavuzu: kütüphane kuralları ve bağımlılık yönetimi.
- Peter van der Linden, *Expert C Programming*, Bölüm 5: bağlama (linking) ve kütüphaneler.

**Sıradaki faz:** Bit manipülasyonu. Bitlerle sayma, maskeleme, bit numaraları, ve Faz 4'teki `strlen`'i bitlerle hızlandırmak.
