---
title: "4.20 strtok sıfırdan"
description: "Bir yazıyı ayraçlardan parçalara ayırmak: strtok'un ilk çağrıda yazıyı, sonraki çağrılarda NULL alması, ayraçların yerine '\\0' yazıp parçaları yerinde döndürmesi, bu halin iki büyük sorunu — gizli static durum yüzünden girdiyi değiştirmesi ve iki ayrıştırma iç içe olduğunda birbirini bozması (yeniden girilemezlik), ve durumu çağırana taşıyan strtok_r."
---

Ders 4.17'de `strchr` ile bir yazıyı ayraçlardan bölmüştük: her ayracı bulup yerine `'\0'` yaz, parçaları gez. `strtok` bu işi bir fonksiyona koyuyor: bir yazıyı, verilen ayraç karakterlerinden **parçalara** (token) ayırıyor. Ama `strtok`, standart kütüphanenin en çok eleştirilen fonksiyonu; Ders 4.7'de `static` bir tamponun tuzağını anlatırken "Ders 4.20'deki `strtok` bu tasarımın sorunlarını gösterecek" demiştik. İşte o ders.

Önce çalıştıracağız, sonra iki ciddi tasarım hatasını göreceğiz, sonra hatasız halini (`strtok_r`) yazacağız.

---

## 1. strtok nasıl kullanılıyor

```c
char *strtok(char *restrict str, const char *restrict delim);
```

Garip bir çağrı biçimi var: **ilk** çağrıda yazıyı veriyorsun, **sonraki** çağrılarda `NULL`. Her çağrı bir sonraki parçayı döndürüyor, parça kalmayınca `NULL`:

```c
char text[] = "  bir,iki;;uc  dort,";
char *token = strtok(text, " ,;");
while (token != NULL) {
    printf("[%s] ", token);
    token = strtok(NULL, " ,;");
}
```

```
[bir] [iki] [uc] [dort]
```

- `delim`, ayraç **kümesi**: buradaki her karakter bir ayraç. `" ,;"` demek "boşluk, virgül veya noktalı virgül".
- Art arda gelen ayraçlar (`;;`, `  `) tek bir ayırıcı gibi: boş parça üretilmiyor.
- Baştaki ve sondaki ayraçlar atlanıyor.
- İlk çağrı `text`'i, sonrakiler `NULL` alıyor: "aynı yazıda devam et".

`NULL` ile devam edebilmesi için, `strtok`'un yazının **neresinde kaldığını** bir yerde hatırlaması gerekiyor. İşte bütün sorun orada.

---

## 2. Kendi strtok'umuz

Önce durumu nerede sakladığını açıkça görelim. Ayraç kümesinde bir karakter var mı diye bakan bir yardımcı, sonra asıl fonksiyon:

```c
#include <string.h>

static int in_set(char c, const char *set) {
    while (*set != '\0') {
        if (*set == c) {
            return 1;
        }
        set++;
    }
    return 0;
}

static char *saved;   // GIZLI DURUM: kaldigimiz yer

char *strtok_mine(char *str, const char *delim) {
    char *start = (str != NULL) ? str : saved;

    // 1. Bastaki ayraclari atla
    while (*start != '\0' && in_set(*start, delim)) {
        start++;
    }
    if (*start == '\0') {
        saved = start;
        return NULL;   // parca kalmadi
    }

    // 2. Parcanin sonunu bul
    char *end = start;
    while (*end != '\0' && !in_set(*end, delim)) {
        end++;
    }

    // 3. Ayracin yerine '\0' yaz, kaldigimiz yeri sakla
    if (*end != '\0') {
        *end = '\0';
        saved = end + 1;
    } else {
        saved = end;
    }
    return start;
}
```

- `str != NULL` ise baştan başla; `NULL` ise `saved`'dan (geçen çağrının bıraktığı yer) devam et.
- Baştaki ayraçları atla, parçanın sonunu bul.
- Ayracı `'\0'` ile değiştir: böylece `start`, Ders 4.17'deki gibi kendi başına bir yazı oluyor. `saved`'ı bir sonrasına kaydır.

`static char *saved`, Ders 2.11 ve 4.4'teki `static`: fonksiyon çağrıları arasında yaşayan, veri bölgesinde duran bir değişken. `strtok`'un "kaldığı yeri hatırlaması" bu. Standart `strtok` ile 20'yi aşkın farklı girdide (baştaki/sondaki/art arda ayraçlar) karşılaştırdık; aynı parçaları üretiyor.

---

## 3. İki büyük sorun

### Sorun 1: girdiyi değiştiriyor

`strtok`, ayraçların yerine `'\0'` yazıyor — yani sana verilen yazıyı **kalıcı olarak bozuyor**. Döngüden sonra `text`, `"bir\0iki\0\0uc  dort\0"` halinde; orijinal `"  bir,iki;;uc  dort,"` gitti. Bu yüzden:

- `strtok`'a bir **string sabiti** veremezsin: `strtok("a,b,c", ",")` salt okunur belleğe yazmaya çalışır ve çöker (Ders 4.12). Değiştirilebilir bir array gerekiyor.
- Orijinal yazıya sonra ihtiyacın varsa, önce bir kopyasını almalısın (Ders 4.14).

### Sorun 2: yeniden girilemez (not reentrant)

Asıl ciddi sorun bu. Gizli durum **tek bir global** (`saved`). Yani aynı anda **iki ayrı** ayrıştırma yapılamıyor. Bir yazıyı parçalara ayırırken, her parçayı da kendi içinde ayırmayı deneyelim — `ad=Ece;sehir=Izmir` gibi bir veriyi önce `;`'den, sonra her parçayı `=`'den:

```c
char data[] = "ad=Ece;sehir=Izmir;dil=C";
char *pair = strtok(data, ";");
while (pair != NULL) {
    char key_value[64];
    strcpy(key_value, pair);
    char *key = strtok(key_value, "=");   // IC ICE strtok
    char *val = strtok(NULL, "=");
    printf("key=[%s] val=[%s]\n", key, val);
    pair = strtok(NULL, ";");             // dis dongu
}
```

```
key=[ad] val=[Ece]
```

Sadece **bir** çift yazdırıldı, sonra döngü bitti. İçteki `strtok(key_value, "=")`, `saved`'ı `key_value`'yu gösterecek şekilde **ezdi**. Dıştaki döngünün `strtok(NULL, ";")` çağrısı `data`'dan devam edeceğini sanıyordu, ama `saved` artık `key_value`'nun (zaten tükenmiş) içini gösteriyor; `NULL` dönüyor ve dış döngü erkenden bitiyor. İki ayrıştırma **aynı** gizli değişkeni paylaştığı için birbirini bozdu.

Aynı sorun çok iş parçacıklı (multithreaded) programlarda daha da kötü: iki iş parçacığı aynı anda `strtok` çağırırsa `saved`'ı birbirinin altından çekerler. Bir fonksiyonun, kesilip yeniden çağrıldığında (ya da iç içe çağrıldığında) doğru çalışması özelliğine **yeniden girilebilirlik** (reentrancy) denir; `strtok` bundan yoksun, çünkü durumu global bir yerde saklıyor. Ders 4.7'deki `static char buffer[12]` tuzağının aynısı: paylaşılan gizli durum.

---

## 4. strtok_r: durumu çağırana vermek

Çözüm, Ders 4.10'un ana fikri: gizli global durumu **çağıranın verdiği bir değişkene** taşımak. `strtok_r` (POSIX; `r` "reentrant") fazladan bir parametre alıyor:

```c
char *strtok_r(char *str, const char *delim, char **saveptr);
```

`saveptr` bir `char **` (Ders 4.10): "kaldığım yeri senin değişkenine yazayım, bir sonraki çağrıda oradan okuyayım". Global `saved` yerine bu. Kodumuz neredeyse aynı, sadece `saved`'ı `*saveptr` yapıyoruz:

```c
char *strtok_r_mine(char *str, const char *delim, char **saveptr) {
    char *start = (str != NULL) ? str : *saveptr;

    while (*start != '\0' && in_set(*start, delim)) {
        start++;
    }
    if (*start == '\0') {
        *saveptr = start;
        return NULL;
    }

    char *end = start;
    while (*end != '\0' && !in_set(*end, delim)) {
        end++;
    }
    if (*end != '\0') {
        *end = '\0';
        *saveptr = end + 1;
    } else {
        *saveptr = end;
    }
    return start;
}
```

Hatta `strtok_mine`'ı artık bunun üzerine kurabiliriz — global `saved` sadece "durum nerede" sorusunun tek, paylaşılan cevabı:

```c
static char *saved;

char *strtok_mine(char *str, const char *delim) {
    return strtok_r_mine(str, delim, &saved);
}
```

Şimdi iç içe ayrıştırma, her biri **kendi** `saveptr`'siyle çalışıyor:

```c
char *outer;
char *pair = strtok_r(data, ";", &outer);
while (pair != NULL) {
    char *inner;
    char *key = strtok_r(pair, "=", &inner);
    char *val = strtok_r(NULL, "=", &inner);
    printf("key=[%s] val=[%s]\n", key, val);
    pair = strtok_r(NULL, ";", &outer);
}
```

```
key=[ad] val=[Ece]
key=[sehir] val=[Izmir]
key=[dil] val=[C]
```

Üç çift de doğru. Dış döngünün durumu `outer`'da, iç döngününki `inner`'da; birbirlerine dokunmuyorlar. `strtok_r` artık `strcpy` ile kopyalamaya da gerek bırakmadı (iç ayrıştırma `pair`'in kendisi üzerinde, ama dış durumu bozmadan).

**Kural:** yeni kodda `strtok` yerine `strtok_r` kullan (Windows'ta adı `strtok_s`). Hâlâ girdiyi değiştiriyor, ama en azından yeniden girilebilir. Girdiyi hiç değiştirmemek istiyorsan, Ders 4.17'deki `strchr`/`strcspn` kalıbıyla, kopyalamadan, parçaların başını ve uzunluğunu döndüren kendi fonksiyonunu yazarsın (5. alıştırma).

---

## Alıştırmalar

**1** – `strtok_mine(NULL, delim)`'i, ondan önce hiç `strtok_mine(str, ...)` çağrılmadan çalıştırırsan ne olur? `saved` başlangıçta ne? (İpucu: `static` bir pointer; Ders 4.4'teki bss bölgesi.) Bu bir hata mı, yoksa tanımlı mı?

**2** – `strtok`, art arda ayraçları (`;;`) neden atlıyor da boş parça üretmiyor? `"a,,b"`'yi `,`'den ayırınca `strtok` kaç parça verir? CSV dosyalarında boş alanlar (`a,,b` → üç alan, ortası boş) anlamlıysa, `strtok` neden yanlış araç?

**3** – Bölüm 3'teki iç içe `strtok` örneğinde, sadece **bir** çift değil **hiç** çıktı olmaması için girdiyi nasıl değiştirirdin? (İpucu: ilk parçanın içinde ayraç olmayan bir durum.)

**4** – `strtok_r_mine`'da `str != NULL` ise `*saveptr`'ye hiç bakılmıyor. İlk çağrıda `saveptr`'nin gösterdiği değişken başlatılmamış (çöp) olabilir mi? Neden sorun değil? İkinci çağrıda (`NULL` ile) niye önemli hale geliyor?

**5** – Girdiyi **değiştirmeyen** bir ayrıştırıcı yaz: `const char *next_token(const char **saveptr, const char *delim, size_t *len)`. Parçayı yerinde `'\0'` ile kesmek yerine, başını döndürüp uzunluğunu `*len`'e yazsın. `const char *` aldığı için ne kazandın, ne kaybettin?

<details>
<summary>Cevaplar</summary>

**1** – `static char *saved;` başta `NULL`'dur: `static` ve global değişkenler, Ders 4.4'teki bss bölgesinde, sıfırla başlatılır (bir pointer için `NULL`). Yani ilk çağrı `strtok_mine(NULL, delim)` olursa, `start = saved = NULL` ve `*start` bir NULL dereference (Ders 4.5): çökme. Bu bir **kullanım hatası**, ama standart `strtok`'ta da bu durum undefined behavior; ilk çağrı her zaman yazıyı vermelidir. Kendi sürümümüz de bunu kontrol etmiyor (standartla uyumlu kalmak için).

**2** – `strtok`, parça sonunu bulduktan sonra bir sonraki çağrıda **baştaki ayraçları atlayarak** başlıyor (Bölüm 2, adım 1). `;;` görünce ikisini de atlar, arada boş parça bırakmaz. `"a,,b"`'yi `,`'den ayırınca `strtok` **iki** parça verir: `"a"` ve `"b"`; ortadaki boş alan yok olur. CSV için bu yanlış: `a,,b` üç alandır (ikincisi boş) ve `strtok` ikinci alanı sessizce yutar. CSV ayrıştırmak için her ayracın tam bir alan sınırı sayıldığı (art arda ayraçların boş alan ürettiği) bir mantık gerekir; `strtok`'un "art arda ayraçları birleştirme" davranışı buna uymaz. (Ayrıca CSV'de tırnak içinde ayraç olabilir; `strtok` onu da bilmez.)

**3** – İlk parçanın içinde `=` olmayan bir girdi, örneğin `data[] = "tekbasina;ad=Ece"`. İlk `pair` = `"tekbasina"`; içteki `strtok(key_value, "=")` `key_value`'yu ezer, `key = "tekbasina"`, `val = NULL`. Dış `strtok(NULL, ";")` yine `key_value`'dan devam edip `NULL` döner. Sonuç: bir satır (`key=[tekbasina] val=[(null)]`) yazılır ve biter. "Hiç çıktı olmaması" için ilk `pair`'in kendisinin boş olması gerekir ki bu da `strtok` boş parça üretmediği için pratikte olmaz — asıl ders, iç içe `strtok`'un sonucunun girdiye göre **öngörülemez** biçimde bozulması. `strtok_r` her durumda doğru.

**4** – İlk çağrıda (`str != NULL`) `*saveptr`'ye hiç bakılmaz; sadece **yazılır** (fonksiyonun sonunda `*saveptr = ...`). Bu yüzden `saveptr`'nin gösterdiği değişken başlangıçta çöp olabilir, sorun değil — ilk çağrı onu kurar. İkinci çağrıda (`str == NULL`) `start = *saveptr` ile **okunur**; o an artık ilk çağrının yazdığı geçerli değeri taşıyor. Kural: aynı `saveptr`'yi ilk çağrıdan itibaren tutarlı kullan; ilk çağrıyı atlayıp `NULL` ile başlarsan çöp okursun.

**5** –

```c
const char *next_token(const char **saveptr, const char *delim, size_t *len) {
    const char *start = *saveptr;
    while (*start != '\0' && in_set(*start, delim)) {
        start++;
    }
    if (*start == '\0') {
        *saveptr = start;
        return NULL;
    }
    const char *end = start;
    while (*end != '\0' && !in_set(*end, delim)) {
        end++;
    }
    *len = (size_t)(end - start);
    *saveptr = (*end != '\0') ? end + 1 : end;
    return start;
}
```

Başlangıçta `*saveptr`'yi yazının başına koyarsın; her çağrı parçanın başını döndürür, uzunluğunu `*len`'e yazar. Kazanç: girdiyi **hiç değiştirmiyor** (`const char *` alıyor), string sabitleriyle de çalışır, orijinal yazı korunur, yeniden girilebilir. Kayıp: döndürülen parça `'\0'` ile bitmiyor — bir yazı değil, bir (başlangıç, uzunluk) çifti. Onu yazdırmak için `printf("%.*s", (int)len, token)` gibi uzunluk veren bir biçim ya da `strncpy` (Ders 4.14) gerekir. Modern ayrıştırıcılar (Ders 4.30'daki projede de) genelde bu "string view" yaklaşımını tercih eder: veriyi değiştirmeden, başına ve uzunluğuna bakmak.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §B3: `strtok`.
- C standardı (ISO/IEC 9899:2018), §7.24.5.8: `strtok` ve iç durumunun çağrılar arası korunması; Ek K.3.7.3.1: `strtok_s`.
- POSIX.1-2017, `strtok_r`: yeniden girilebilir sürüm.
- SEI CERT C Coding Standard, CON33-C ve STR06-C: `strtok`'un çok iş parçacıklı ve yeniden giriş sorunları.

**Sıradaki ders:** Programın bellek düzeni. text, data, bss, heap, stack bölgeleri; `size` komutu ve Linux'ta `/proc/self/maps`.
