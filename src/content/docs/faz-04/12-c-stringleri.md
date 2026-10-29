---
title: "4.12 C stringleri"
description: "C'de string diye ayrı bir tip yok: '\\0' ile biten bir char array'i. Null sonlandırıcıyı unutunca printf'in komşu değişkeni okuması, char s[] ile char *s = \"...\" farkı, string sabitlerinin salt okunur bölgede durması ve onlara yazınca bus error, -Wwrite-strings, UTF-8'de bir harfin birden fazla byte olması ve scanf yerine fgets ile satır okuyan bir read_int."
---

Ders 3.16'dan beri `char text[]` ile yazılar kurup `printf("%s", text)` ile yazdırıyoruz, ve "yazının sonunda bir `'\0'` var" diyoruz. Ders 4.10'da `argv`'deki yazıların adreslerini, Ders 4.11'de `strcmp`'ü gördük. Ama bir C stringinin ne olduğunu tam olarak tanımlamadık.

Tanım kısa: **C'de string diye bir tip yok.** Bir string, sonunda `'\0'` (değeri 0 olan karakter) bulunan bir `char` dizisi. Hepsi bu. Uzunluğu hiçbir yerde saklanmıyor; yazının nerede bittiğini öğrenmenin tek yolu `'\0'`'ı aramak. C'deki string hatalarının neredeyse hepsi bu tek kararın sonucu.

---

## 1. Null sonlandırıcı

```c
#include <stdio.h>

int main(void) {
    char word[] = "kedi";
    printf("sizeof word = %zu\n", sizeof word);
    for (size_t i = 0; i < sizeof word; i++) {
        printf("word[%zu] = %3d '%c'\n", i, word[i], word[i]);
    }
    char same[5] = {'k', 'e', 'd', 'i', '\0'};
    printf("%s %s\n", word, same);
    word[2] = '\0';
    printf("%s, sizeof = %zu\n", word, sizeof word);
    return 0;
}
```

```
sizeof word = 5
word[0] = 107 'k'
word[1] = 101 'e'
word[2] = 100 'd'
word[3] = 105 'i'
word[4] =   0 ' '
kedi kedi
ke, sizeof = 5
```

- 4 harflik bir yazı **5 byte**: compiler, çift tırnaklı yazının sonuna `'\0'`'ı kendisi ekliyor (Ders 3.16).
- `"kedi"` yazmakla, `{'k', 'e', 'd', 'i', '\0'}` yazmak aynı şey. Çift tırnak bir kısaltma.
- `word[2] = '\0'` yazınca yazı `"ke"` oldu, ama array hâlâ 5 byte. Bir string'in **uzunluğu** (ilk `'\0'`'a kadar) ile içinde durduğu array'in **boyutu** iki ayrı şey. `printf`, `%s`'yi gördüğünde verilen adresten başlayıp `'\0'`'a kadar yazdırıyor; array'in boyutunu bilmiyor bile.

Bu son nokta önemli: Ders 4.1'e göre `printf`'e verilen `word`, bir **adres**. `printf` elinde sadece bir `char *` ile duruyor. Nerede duracağını söyleyen tek şey `'\0'`.

### `'\0'`'ı unutunca

```c
#include <stdio.h>

int main(void) {
    char name[8] = "Deniz";
    char letters[4] = {'k', 'e', 'd', 'i'};
    printf("letters = %s\n", letters);
    printf("name    = %p\nletters = %p\n", (void *)name, (void *)letters);
    return 0;
}
```

`letters` dört harf, ama `'\0'` yok. `-O0`:

```
letters = kedi
name    = 0x16b3ba170
letters = 0x16b3ba168
```

Doğru görünüyor; ama şans eseri. `letters` 4 byte, `name` 8 byte sonra başlıyor; arada kalan 4 byte'tan ilki o anda 0'dı. `-O2`:

```
letters = kediDeniz
name    = 0x16b586160
letters = 0x16b58615c
```

Bu sefer `name`, `letters`'ın **hemen arkasında** (`0x...15c` + 4 = `0x...160`). `printf`, `letters`'ın sonunda durmadı; `name`'in byte'larını da yazdırdı ve `name`'in `'\0'`'ında durdu. Ders 4.1'deki sınır dışı okuma, bu sefer bir kütüphane fonksiyonunun içinde. AddressSanitizer ile:

```
==25014==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x00016d6460a4 ...
READ of size 6 at 0x00016d6460a4 thread T0
    #0 0x000102e9300c in printf_common(void*, char const*, char*)+0x898 ...
    #1 0x000102e93e08 in printf+0x5c ...
  This frame has 2 object(s):
    [32, 40) 'name' (line 4)
    [64, 68) 'letters' (line 5) <== Memory access at offset 68 overflows this variable
```

`printf`, 4 byte'lık `letters`'tan 6 byte okumaya çalıştı.

Compiler bu hatayı başka bir yazılışta yakalayabiliyor:

```c
char t[3] = "abc";
```

```
warning: initializer-string for character array is too long, array size is 3 but initializer has size 4 (including the null terminating character); did you mean to use the 'nonstring' attribute? [-Wunterminated-string-initialization]
```

Sadece bir uyarı, çünkü C standardı buna izin veriyor: array tam yazının uzunluğundaysa, `'\0'` sessizce atılıyor. (C++'ta aynı satır bir **hata**.) Bazen bilerek yapılır: sabit uzunluklu alanlar için, sonunda `'\0'` olmayan karakter dizileri. Ama sonuç artık bir **string değil**, ve `%s` ile yazdırmak `letters`'taki hatanın aynısı.

---

## 2. `char s[]` ile `char *s`

Ders 4.6 ve 4.10'da bu farkı ileriye bırakmıştık. İki satır, aynı görünüyor:

```c
char array[] = "kedi";
char *pointer = "kedi";
```

```c
#include <stdio.h>

int main(void) {
    char array[] = "kedi";
    char *pointer = "kedi";
    char *other = "kedi";

    printf("sizeof array = %zu, sizeof pointer = %zu\n", sizeof array, sizeof pointer);
    printf("array   = %p\n", (void *)array);
    printf("pointer = %p\n", (void *)pointer);
    printf("other   = %p\n", (void *)other);
    printf("&pointer = %p\n", (void *)&pointer);

    array[0] = 'K';
    printf("%s\n", array);
    pointer[0] = 'K';
    printf("%s\n", pointer);
    return 0;
}
```

```
sizeof array = 5, sizeof pointer = 8
array   = 0x16d4fa124
pointer = 0x102904598
other   = 0x102904598
&pointer = 0x16d4fa118
Kedi
zsh: bus error  ./d
```

**`char array[] = "kedi"`**, stack'te 5 byte'lık bir **array** açıyor ve `"kedi\0"`'ı içine **kopyalıyor**. Array'in kendisi `main`'in; içini istediğin gibi değiştirebilirsin. `array[0] = 'K'` çalıştı.

**`char *pointer = "kedi"`**, stack'te 8 byte'lık bir **pointer** açıyor (`&pointer` stack'te) ve ona bir adres koyuyor. Hangi adres? `0x102904598`, Ders 4.4'teki haritanın en altında: programın **kodunun yanındaki salt okunur bölge**. `"kedi\0"` oraya, programın dosyasının içine, derleme sırasında yazıldı. `pointer` sadece onu gösteriyor.

Bunu programın dosyasında doğrudan görebiliriz. macOS'ta `otool -s __TEXT __cstring d`, programın string sabitlerini tutan bölümünü gösteriyor:

```
Contents of (__TEXT,__cstring) section
0000000100000598	6964656b 7a697300 ...
```

`6b 65 64 69 00` (little-endian 4 byte'lık gruplar halinde; Ders 3.9) = `k e d i \0`, `0x598` ofsetinde. Program çalışırken adres `0x102904598`; son 3 hane aynı. Ders 4.4'teki ASLR: işletim sistemi programı her seferinde farklı bir yere taşıyor, ama içerideki yerleşimi bozmuyor.

**`pointer[0] = 'K'` programı çöktürdü.** O bölge, Ders 4.8'deki `const` global gibi yazmaya kapalı; bus error aynı sebepten. C standardı açısından: **bir string sabitini değiştirmek undefined behavior.** `-O2`'de de sonuç aynı.

**`other` ile `pointer` aynı adres.** Compiler aynı string sabitini iki kez yazmak yerine tek bir kopyasını tuttu ve iki pointer'a da onun adresini verdi. Değiştirilemeyecekleri için paylaşmak güvenli; bu da string sabitlerini değiştirmenin neden yasak olduğunu açıklıyor: `pointer[0] = 'K'` çalışsaydı, `other` da `"Kedi"` olurdu.

| | `char array[] = "kedi";` | `char *pointer = "kedi";` |
| --- | --- | --- |
| Ne açılıyor? | 5 byte'lık array | 8 byte'lık pointer |
| `"kedi"` nerede? | array'in içinde (kopya) | salt okunur bölgede |
| `sizeof` | 5 | 8 |
| Harfleri değiştirmek | serbest | undefined behavior (çöker) |
| Başka bir yazıyı göstermek | yasak (`array = ...`; Ders 4.1) | serbest (`pointer = "kopek"`) |
| Ömrü | tanımlandığı fonksiyon kadar | programın tamamı |

Son satır Ders 4.7'deki sallanan pointer'la bağlantılı: bir fonksiyonun **kendi array'ini** döndürmesi hata, ama bir **string sabitinin** adresini döndürmesi güvenli; sabit programın sonuna kadar yaşıyor.

```c
const char *day_name(int day) {
    const char *names[7] = {"Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma", "Cumartesi", "Pazar"};
    return names[day];
}
```

`names` array'i yerel ve fonksiyon bitince yok oluyor; ama döndürdüğümüz şey array'in **elemanı**, bir sabitin adresi. Sorun yok.

### Neden `const char *` yazmalıyız?

String sabitleri değiştirilemiyorsa, compiler neden `char *pointer = "kedi"` satırında uyarmadı? Tarihî bir sebep: `const` C'ye 1989'da eklendi, ama o tarihe kadar yazılmış milyonlarca satır `char *s = "..."` içeriyordu. Bu kodları bozmamak için, C'de bir string sabitinin tipi **`char [5]`**, `const char [5]` değil. Değiştirilemeyen ama tipi bunu söylemeyen bir nesne; Ders 4.8'deki `strchr` ikileminin bir başka hali. (C++'ta tip `const char [5]`, ve `char *p = "kedi"` bir hata.)

clang'e C++ gibi davranmasını söyleyebilirsin:

```
$ clang -Wall -Wextra -Wwrite-strings -c d.c
warning: initializing 'char *' with an expression of type 'const char[5]' discards qualifiers [-Wincompatible-pointer-types-discards-qualifiers]
```

`-Wwrite-strings`, string sabitlerinin tipini `const char []` yapıyor; artık Ders 4.8'deki "discards qualifiers" uyarısı çıkıyor. Kural: **bir string sabitini gösteren pointer'ı her zaman `const char *` olarak tanımla.** Bu seride bundan sonra hep böyle yazacağız.

### Yan yana yazılan sabitler

Bir detay: aralarında sadece boşluk olan iki string sabiti, compiler tarafından **birleştiriliyor**:

```c
const char *joined = "bir " "iki " "uc";
printf("%s\n", joined);
```

```
bir iki uc
```

Uzun bir yazıyı satırlara bölmenin yolu bu; `+` gibi bir operatör yok, ve olmasına gerek de yok, çünkü birleştirme derleme sırasında oluyor.

---

## 3. Bir harf, bir byte değil

Türkçe yazıları da `char` array'lerinde tutuyoruz. Ama bir harf her zaman bir byte mı?

```c
const char *words[3] = {"kedi", "çiçek", "ğ"};
for (int i = 0; i < 3; i++) {
    printf("%-8s strlen = %zu, byte: ", words[i], strlen(words[i]));
    const unsigned char *p = (const unsigned char *)words[i];
    while (*p != '\0') {
        printf("%02x ", *p);
        p++;
    }
    printf("\n");
}
```

```
kedi     strlen = 4, byte: 6b 65 64 69
çiçek  strlen = 7, byte: c3 a7 69 c3 a7 65 6b
ğ       strlen = 2, byte: c4 9f
```

`"çiçek"` 5 harf, ama **7 byte**. ASCII (Faz 0) sadece 128 karakter tanımlıyor; `ç`, `ğ`, `ş` onların arasında değil. Bu dosya, ve bugün neredeyse her metin, **UTF-8** ile kodlanıyor: ASCII karakterleri yine tek byte, diğerleri 2 ila 4 byte. `ç` = `c3 a7`, `ğ` = `c4 9f`.

Sonuçları:

- `strlen` (Ders 4.13'te yazacağız) **byte** sayıyor, harf değil. Türkçe bir yazının harf sayısı başka bir hesap gerektiriyor (2. alıştırma).
- `printf`'in `%-8s`'si "en az 8 karakter genişliğinde yaz" demek; ama o da byte sayıyor. `çiçek`'ten sonra 1 boşluk kaldı (7 byte + 1), hizalama kaydı. Ekranda 5 harf, `printf`'in gözünde 7.
- `word[0]` bir **byte**. `"çiçek"[0]` `ç` değil, onun ilk yarısı (`0xc3`).
- Byte'ları `unsigned char *` ile okuduk; `char` bu makinede işaretli olduğu için `0xc3`, `char` olarak −61 (Ders 3.2). Ders 4.16'da bu ayrıntı `strcmp`'ün doğru çalışması için önemli olacak.

Bu fazda yazdığımız string fonksiyonları byte'larla çalışacak; UTF-8'in ayrıntısı bu fazın konusu değil.

---

## 4. Satır okumak: `scanf`'in yerine `fgets`

Ders 3.17'de "satırı bir array'e okuyup çevirmek, string'leri gördükten sonra bütün `scanf` kullanımlarımızın yerini alacak" demiştik. Ders 2.13'teki `read_int`'i hatırla: `scanf("%9d", ...)` ile okuyor, sonra satırın geri kalanını karakter karakter atlıyordu. `%9d` hilesi de 9 basamaktan uzun sayıları reddediyordu.

`<stdio.h>`'teki `fgets`, bir satırı olduğu gibi bir array'e okuyor:

```c
char *fgets(char *buffer, int size, FILE *stream);
```

- En fazla `size - 1` karakter okuyup sonuna `'\0'` koyuyor; tampon asla taşmıyor.
- Satır sonundaki `'\n'`'ı da tampona yazıyor (yer varsa).
- Hiçbir şey okuyamazsa (girişin sonu; Ders 2.13'teki EOF) `NULL` döndürüyor.
- `stream`, nereden okunacağı: klavye için `stdin`. (Dosyalar Faz 10'da.)

Satır elimizde bir string olunca, Ders 3.17'deki `strtol` ve Ders 4.10'daki `end` kontrolü işi bitiriyor:

```c
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <errno.h>
#include <limits.h>

#define READ_OK 1
#define READ_INVALID 0
#define READ_EOF -1

struct ReadResult {
    int status;
    int value;
};

bool is_blank(char c) {
    return c == ' ' || c == '\t' || c == '\n';
}

struct ReadResult read_int(void) {
    struct ReadResult result = {READ_INVALID, 0};
    char line[64];
    if (fgets(line, sizeof line, stdin) == NULL) {
        result.status = READ_EOF;
        return result;
    }
    if (strchr(line, '\n') == NULL && !feof(stdin)) {
        int c = getchar();
        while (c != '\n' && c != EOF) {
            c = getchar();
        }
        return result;
    }
    char *end;
    errno = 0;
    long value = strtol(line, &end, 10);
    if (end == line || errno == ERANGE || value > INT_MAX || value < INT_MIN) {
        return result;
    }
    while (is_blank(*end)) {
        end++;
    }
    if (*end != '\0') {
        return result;
    }
    result.status = READ_OK;
    result.value = (int)value;
    return result;
}
```

Satır satır:

- **`fgets(line, sizeof line, stdin)`**: `sizeof line` burada 64, çünkü `line` bu fonksiyonun kendi array'i (Ders 4.1).
- **Satır tampona sığmadıysa**: tamponda `'\n'` yoksa, ya satır 63 karakterden uzundu ya da giriş `'\n'` olmadan bitti. `strchr(line, '\n')`, yazıda `'\n'`'ı arayıp bulamazsa `NULL` döndürüyor (Ders 4.17'de yazacağız); `feof(stdin)` girişin bitip bitmediğini söylüyor. Uzun satırsa geri kalanını Ders 2.13'teki gibi atlayıp geçersiz sayıyoruz; aksi halde bir sonraki `read_int`, aynı satırın devamını okurdu.
- **`strtol`**: baştaki boşlukları kendisi atlıyor (Ders 3.17). `end == line` ise hiç rakam yok.
- **`int`'e sığıyor mu**: `strtol` bir `long` döndürüyor; Ders 3.17'deki `parse_int` gibi aralığı kendimiz kontrol ediyoruz. `%9d` hilesine artık gerek yok.
- **Sayıdan sonra**: sadece boşluk ve `'\n'` kalmalı. `175abc` burada reddediliyor.

```c
int main(void) {
    while (true) {
        printf("sayi: ");
        struct ReadResult r = read_int();
        if (r.status == READ_EOF) {
            printf("\n");
            break;
        }
        if (r.status == READ_INVALID) {
            printf("gecersiz\n");
        } else {
            printf("okundu: %d\n", r.value);
        }
    }
    return 0;
}
```

Girişi bir dosyadan verir gibi, `printf ... | ./r` ile (Ders 2.13) on satır verelim: `42`, `  -17  `, `175abc`, `2000000000`, `3000000000`, boş satır, `abc`, yüz tane `1`, ve sonunda `'\n'` olmayan `7`:

```
sayi: okundu: 42
sayi: okundu: -17
sayi: gecersiz
sayi: okundu: 2000000000
sayi: gecersiz
sayi: gecersiz
sayi: gecersiz
sayi: gecersiz
sayi: okundu: 7
sayi:
```

Ders 2.13'teki sürümün reddettiği `2000000000` artık okunuyor; `3000000000` `int`'e sığmadığı için reddediliyor. 100 karakterlik satır taşma yapmadı, bir sonraki satırı da bozmadı. AddressSanitizer ve UBSan ile derlendi; hiçbir uyarı yok. Bundan sonra klavyeden bir şey okuyacağımız her yerde bu kalıbı kullanacağız: **önce satırı oku, sonra çözümle.**

`scanf("%s", buffer)` ise ne kadar uzun bir kelime gelirse gelsin `buffer`'a yazmaya devam eder; tamponun boyutunu bilmez. Ders 4.14'te bunun neden bir güvenlik açığı olduğunu göreceğiz.

---

## Alıştırmalar

**1** – Her tanım için `sizeof` değerini ve içeriğin değiştirilip değiştirilemeyeceğini söyle:

```c
char a[] = "";
char b[10] = "abc";
char c[] = {'a', 'b', 'c'};
const char *d = "abc";
char e[] = "ab\0cd";
```

`e`'yi `%s` ile yazdırınca ne çıkar?

**2** – UTF-8'de bir harfin **ilk** byte'ı `0xxxxxxx` ya da `11xxxxxx` biçiminde; devam byte'ları ise hep `10xxxxxx`. Bu kuralla bir yazıdaki harf sayısını bulan `size_t utf8_length(const char *s)` yaz. `"çiçek"` için 5 dönmeli. (İpucu: `(byte & 0xC0) != 0x80`; Ders 3.18'deki `&`.)

**3** – Bölüm 2'deki `day_name`, `day` 0–6 dışında olunca ne yapar? Bunu düzelt. Peki `names`'i `const char *names[7]` yerine `char names[7][10]` yapıp `return names[day];` yazsaydık?

**4** – Bölüm 4'teki `read_int`, `line` 64 yerine 4 byte olsaydı `1234` girişinde ne yapardı? Ya `123`? Bir tampon boyutu seçerken neyi düşünmelisin?

**5** – Bir yazının içindeki bütün küçük ASCII harfleri büyüğe çeviren `void to_upper(char *s)` yaz. Şu iki çağrıdan hangisi doğru, hangisi undefined behavior? `char x[] = "merhaba"; to_upper(x);` ve `to_upper("merhaba");`. `-Wwrite-strings` hangisini yakalar?

<details>
<summary>Cevaplar</summary>

**1** –

| Tanım | `sizeof` | Değiştirilebilir mi? |
| --- | --- | --- |
| `char a[] = "";` | 1 (sadece `'\0'`) | evet |
| `char b[10] = "abc";` | 10 (geri kalan 6 byte da `'\0'`) | evet |
| `char c[] = {'a', 'b', 'c'};` | 3; `'\0'` **yok**, string değil | evet |
| `const char *d = "abc";` | 8 (pointer) | hayır |
| `char e[] = "ab\0cd";` | 6 (`a b \0 c d \0`) | evet |

`e` yazdırılınca `ab` çıkar: `printf` ilk `'\0'`'da duruyor. `cd` array'de duruyor ama hiçbir string fonksiyonu onu görmüyor. Bir string'in içinde `'\0'` olamaz; olursa string orada biter.

**2** –

```c
size_t utf8_length(const char *s) {
    size_t count = 0;
    for (const unsigned char *p = (const unsigned char *)s; *p != '\0'; p++) {
        if ((*p & 0xC0) != 0x80) {
            count++;
        }
    }
    return count;
}
```

`0xC0` = `11000000`: byte'ın en üstteki iki biti. `10` ile başlayan byte'lar (`0x80`–`0xBF`) devam byte'ları; onları saymıyoruz. `"çiçek"` → `c3 a7 69 c3 a7 65 6b`: `a7` iki kez devam byte'ı, 7 − 2 = 5. Bu fonksiyon yazının geçerli UTF-8 olduğunu kontrol etmiyor; sadece sayıyor.

**3** – Kontrol yoksa `names[day]`, Ders 4.1'deki gibi array'in dışından bir değer okur ve onu bir adres diye döndürür; çağıran onu yazdırmaya kalkınca program büyük ihtimalle çöker. Düzeltme: `if (day < 0 || day > 6) { return NULL; }` (ya da `"?"`). `char names[7][10]` yapsaydık, isimler **yerel bir array'in içine** kopyalanırdı ve `names[day]` o array'in bir satırının adresi olurdu: fonksiyon bitince yok olan bir yeri gösteren sallanan pointer (Ders 4.7). clang bunu da `-Wreturn-stack-address` ile yakalar.

**4** – 4 byte'lık tampona `fgets` en fazla 3 karakter okur. `1234\n` için tamponda `123` olur, `'\n'` yok; satırın geri kalanı atlanır ve sonuç **geçersiz**. `123\n` için de `123` okunur ve `'\n'` sığmaz; `read_int` bunu da uzun satır sanıp, bir sonraki satırı (`'\n'`'ı arayarak) **yutar**: aslında `'\n'` hemen orada olduğu için sadece onu tüketir, ama `123` yine geçersiz sayılır. Yani tampon, beklenen en uzun geçerli satırı **ve** `'\n'` ile `'\0'`'ı alacak kadar büyük olmalı. Bir `int` en fazla 11 karakter (`-2147483648`); etrafındaki boşluklara da yer bırakmak için 64 rahat bir seçim.

**5** –

```c
void to_upper(char *s) {
    while (*s != '\0') {
        if (*s >= 'a' && *s <= 'z') {
            *s = *s - ('a' - 'A');
        }
        s++;
    }
}
```

`to_upper(x)` doğru: `x` bir array, içi `main`'in. `to_upper("merhaba")` undefined behavior: string sabitine yazıyor, Bölüm 2'deki gibi bus error ile çöker. `-Wwrite-strings` ile `"merhaba"`'nın tipi `const char [8]` olur, ve `char *` parametreye verilmesi "discards qualifiers" uyarısı verir: hata derleme sırasında yakalanır.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §1.9 (karakter array'leri), §5.5 (karakter pointer'ları ve fonksiyonlar), §B1.4 (`fgets`).
- C standardı (ISO/IEC 9899:2018), §6.4.5: string sabitleri, birleştirilmeleri ve değiştirilmelerinin undefined behavior olması; §6.7.9¶14: `char t[3] = "abc"`'nin geçerli olması; §7.21.7.2: `fgets`.
- Peter van der Linden, *Expert C Programming*, Bölüm 4: "The Shocking Truth: C Arrays and Pointers Are NOT the Same!"
- RFC 3629, *UTF-8, a transformation format of ISO 10646*.
- SEI CERT C Coding Standard, STR30-C (string sabitlerini değiştirmemek), STR32-C (null sonlandırılmamış diziyi string fonksiyonlarına vermemek).

**Sıradaki ders:** `strlen` sıfırdan. Önce indeksle, sonra pointer farkıyla; ve standart kütüphanedekiyle hız karşılaştırması.
