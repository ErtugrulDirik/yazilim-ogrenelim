---
title: "4.16 strcmp ve strncmp sıfırdan"
description: "İki yazıyı karşılaştırmak: negatif/sıfır/pozitif dönüş sözleşmesi, == 0 kontrolü, ilk farklı karakterde durmak, karakterleri char yerine unsigned char olarak karşılaştırmak zorunluluğu (işaretli char'la UTF-8 ve yüksek bitli byte'larda yanlış sıralama), 3 milyon rastgele girdide standart sürümle karşılaştırma, ve en fazla n karakter bakan strncmp."
---

Ders 4.11'de `strcmp`'ü `qsort`'un karşılaştırıcısı olarak kullandık; Ders 4.12'de `read_int`'te `strchr`'le birlikte andık. Ders 4.11'de karşılaştırıcıları `unsigned char` ile yazarken "sebebini Ders 4.16'da göreceğiz" demiştik. Şimdi o ders.

`strcmp`, iki yazının **sözlük sırasını** söylüyor. Yazmak kolay görünüyor; ama tek bir satırda, C'nin en çok gözden kaçan tuzaklarından biri saklı: karakterlerin işaretli mi işaretsiz mi karşılaştırıldığı.

---

## 1. Dönüş değeri sözleşmesi

```c
int strcmp(const char *a, const char *b);
```

`strcmp` bir `bool` değil, bir `int` döndürüyor, ve değeri Ders 4.11'deki `qsort` karşılaştırıcısının sözleşmesinin aynısı:

- `a`, `b`'den **önce** geliyorsa (sözlükte): **negatif**.
- İkisi **eşitse**: **0**.
- `a`, `b`'den **sonra** geliyorsa: **pozitif**.

Buradaki en sık hata, `strcmp`'ü bir `bool` sanmak. "`a` ile `b` eşit mi?" sorusunun cevabı `strcmp(a, b)` **değil**, `strcmp(a, b) == 0`. Eşitlikte 0, yani "yanlış" değeri döndüğü için:

```c
if (strcmp(user_input, "evet")) {
    // BU, girdi "evet" DEĞİLSE çalışır!
}
```

Doğrusu `if (strcmp(user_input, "evet") == 0)`. Bu ters mantık o kadar yaygın bir hata ki, bazı projeler `strcmp` yerine `streq(a, b)` diye bir yardımcı tanımlıyor.

Dönüş değerinin **büyüklüğü** anlamlı değil, sadece işareti. Standart "negatif/pozitif" diyor; bir sürüm −1, başka bir sürüm −159 döndürebilir, ikisi de doğru. Bu yüzden `strcmp`'ün sonucunu her zaman `< 0`, `== 0`, `> 0` ile kullan; `== -1` yazma.

---

## 2. İlk versiyonu — ve içindeki hata

İki yazıyı baştan karşılaştır, ilk farklı karakterde dur:

```c
int strcmp_signed(const char *a, const char *b) {
    while (*a != '\0' && *a == *b) {
        a++;
        b++;
    }
    return (int)*a - (int)*b;
}
```

Döngü, karakterler eşit olduğu sürece ilerliyor. İki durumda duruyor:

- **İlk fark bulundu** (`*a != *b`): o iki karakterin farkını döndürüyoruz. `*a < *b` ise negatif.
- **`a`'nın sonuna gelindi** (`*a == '\0'`): `*b` hâlâ bir karakterse, `a` daha kısa ve `b`'nin öneki, yani `a` önce gelir; `0 - *b` negatif. İkisi de `'\0'` ise eşit, `0 - 0 = 0`.

`"elma"` ile `"elmas"` için ilk dördü eşit, sonra `a`'da `'\0'`, `b`'de `'s'`: `0 - 115 = -115`, doğru. Çoğu girdide çalışıyor. Ama bir hata var, ve ancak bir ucu yüksek değerli bir byte içeren yazılarda ortaya çıkıyor.

---

## 3. char işaretli olunca sıralama bozuluyor

Ders 3.2'den: bu makinede (çoğu makinede olduğu gibi) `char` **işaretli**. Yani değeri 127'den büyük bir byte, bir `char` olarak **negatif**. Ders 4.12'den: UTF-8'de Türkçe harfler (`ç` = `0xc3 0xa7`, `ğ` = `0xc4 0x9f`) tam da bu aralıktaki byte'larla başlıyor.

`"\xc3z"` (UTF-8 `ç` ile başlayan bir yazı) ile `"bz"`'yi karşılaştıralım:

```c
const char *big = "\xc3z";
const char *small = "bz";
```

```
libc:   97
signed: -159
mine:   97
```

Standart `strcmp` **pozitif** diyor: `0xc3` = 195, `'b'` = 98; 195 > 98, yani `ç...` `b...`'den sonra gelir. Doğru. Ama `strcmp_signed` **negatif** veriyor:

```c
(int)*a - (int)*b
```

`*a`, `0xc3` byte'ı, bir `char` olarak **−61** (Ders 3.2: 195 − 256). `*b` ise `'b'` = 98. `−61 − 98 = −159`: negatif, yani "`ç...` önce gelir". **Yanlış.** İşaretli `char`, 128–255 arası byte'ları negatif sanıyor ve onları bütün ASCII harflerinden **önceye** koyuyor.

3 milyon rastgele yazı çiftini standart `strcmp`'le karşılaştırdık:

```
3000000 test
  strcmp_mine hata: 0
  strcmp_signed hata: 1495792
```

`strcmp_signed` neredeyse **yarısında** yanlış: yüksek bitli bir byte her karşılaştığında işaret bozuluyor.

### Doğrusu: unsigned char

C standardı `strcmp`'ün karşılaştırmayı **`unsigned char` olarak** yapmasını şart koşuyor (§7.24.4¶1). Yani her byte 0–255 arası, işaret oyunu yok:

```c
int strcmp_mine(const char *a, const char *b) {
    const unsigned char *x = (const unsigned char *)a;
    const unsigned char *y = (const unsigned char *)b;
    while (*x != '\0' && *x == *y) {
        x++;
        y++;
    }
    return (int)*x - (int)*y;
}
```

Tek fark, pointer'ları `const unsigned char *`'a çevirmek (Ders 4.5'teki tip punning değil; sadece aynı byte'lara işaretsiz bakmak). Artık `0xc3`, 195 olarak okunuyor; `195 - 98 = 97`, pozitif, doğru. 3 milyon testte sıfır hata.

`== 0` (eşitlik) sorusu için fark yok: eşit yazılarda iki sürüm de 0 döndürür. Fark sadece **sıralamada** (`qsort` ile sıralarken, Ders 4.11). Ama o fark, UTF-8 metinlerinde yarı yarıya yanlış bir sıralama demek. `unsigned char`, yazılabilmesi kolay ama unutulması da kolay bir satır; CERT'in STR37-C kuralı doğrudan bununla ilgili.

İki değeri de `int`'e çeviriyoruz: `unsigned char` çıkarmasında (`195 - 98`) Ders 3.5'teki tamsayı yükseltmesi ikisini zaten `int`'e çıkarır, ama cast'i açıkça yazmak niyeti belli ediyor ve çıkarmanın hiçbir zaman sarmayacağını (iki değer de 0–255) garanti ediyor.

---

## 4. strncmp

`strncmp`, en fazla `n` karakter karşılaştırıyor:

```c
int strncmp(const char *a, const char *b, size_t n);
```

```c
int strncmp_mine(const char *a, const char *b, size_t n) {
    const unsigned char *x = (const unsigned char *)a;
    const unsigned char *y = (const unsigned char *)b;
    while (n > 0 && *x != '\0' && *x == *y) {
        x++;
        y++;
        n--;
    }
    if (n == 0) {
        return 0;
    }
    return (int)*x - (int)*y;
}
```

Döngüye bir koşul daha eklendi: `n > 0`. `n` karakter karşılaştırıldıktan sonra duruyoruz ve **0 döndürüyoruz** — "ilk `n` karakter eşit". `n` koşulu `&&`'nin en başında, çünkü `n == 0` olunca `*x`'i hiç okumamalıyız (Ders 4.13'teki `strnlen`'deki kısa devre).

İki kullanımı yaygın:

- **Önek kontrolü**: `strncmp(path, "/usr/", 5) == 0`, "`path`, `/usr/` ile mi başlıyor?" — tüm yazıyı karşılaştırmadan.
- **Sabit uzunluklu alanlar**: sonu `'\0'` ile bitmesi garanti olmayan (Ders 4.12) karakter dizilerini, en fazla alan boyu kadar karşılaştırmak.

3 milyon rastgele çiftte `n`'i de rastgele seçerek standart `strncmp`'le karşılaştırdık: sıfır hata.

---

## Alıştırmalar

**1** – `if (strcmp(a, b))` ile `if (!strcmp(a, b))`'nin her biri ne zaman çalışır? İkisini Türkçeye çevir. Hangisi "eşitlerse"?

**2** – `strcmp_mine`'daki döngü koşulundan `*x != '\0'` kontrolünü çıkar: `while (*x == *y)`. İki **eşit** yazı için (`"abc"`, `"abc"`) ne olur? Neden sonsuz döngü değil de sınır dışı okuma? (İpucu: iki yazının `'\0'`'ları.)

**3** – `strcmp_mine`'ı `return`'de çıkarma yapmadan, `(*x < *y) - (*x > *y)` ... yani −1/0/1 döndürecek şekilde yaz (Ders 4.11'deki `a - b` tuzağından kaçınan biçim). Bu sürüm hâlâ `unsigned char` gerektirir mi?

**4** – `strncmp(a, b, 0)` her zaman 0 döndürür. Bu, iki yazının eşit olduğu anlamına mı gelir? `strncmp(a, b, strlen(a) + 1)` ile `strcmp(a, b)` aynı şey mi? (`a`'nın `b`'den uzun olduğu durumu düşün.)

**5** – `casecmp(a, b)`: Ders 4.11'deki gibi büyük-küçük harf farkını yok sayan bir karşılaştırma. `strcmp_mine`'ı temel al, her byte'ı karşılaştırmadan önce küçült. Neden yine `unsigned char` ile başlamak gerekiyor?

<details>
<summary>Cevaplar</summary>

**1** – `strcmp(a, b)` eşitlikte **0** (yanlış), farkta sıfırdan farklı (doğru) döndürür.

- `if (strcmp(a, b))` → "`a` ile `b` **farklıysa**". (0 yanlış sayıldığı için.)
- `if (!strcmp(a, b))` → "`a` ile `b` **eşitse**". `!0` doğru.

"Eşitlerse" olan ikincisi, `!`'li olan. Bu ters mantık (`!` eşitlik demek) `strcmp`'ün en kafa karıştıran yanı; `strcmp(a, b) == 0` yazmak her zaman daha okunur.

**2** – Sınır dışı okuma. İki yazı eşit olduğunda, `'\0'` karakterleri de birbirine eşittir (`0 == 0`); `*x == *y` koşulu `'\0'`'da da doğru kalır ve döngü **durmaz**, iki pointer da yazıların sonundan öteye geçer. Sonsuz döngü değil, çünkü ilerledikçe er geç iki tamponun arkasındaki byte'lar farklılaşır ya da erişilemez belleğe çarpılır; AddressSanitizer bunu sınır dışı okuma olarak yakalar. `*x != '\0'` kontrolü tam da bunu engelliyor: yazı bitince (farklı olsun olmasın) dur.

**3** –

```c
int strcmp_sign(const char *a, const char *b) {
    const unsigned char *x = (const unsigned char *)a;
    const unsigned char *y = (const unsigned char *)b;
    while (*x != '\0' && *x == *y) {
        x++;
        y++;
    }
    return (*x > *y) - (*x < *y);
}
```

Evet, hâlâ `unsigned char` gerekiyor: `(*x > *y)` karşılaştırması da işaretli `char`'la yanlış sonuç verir (`0xc3` negatif sanılır). Çıkarmadan kaçınmak taşmayı önler ama işaret sorununu çözmez; ikisi ayrı meseleler. Bu sürüm 195 > 98'i doğru değerlendirir ve 1 döndürür.

**4** – `strncmp(a, b, 0)`, hiçbir karakter karşılaştırmadan 0 döndürür — "ilk sıfır karakter eşit", ki her zaman doğru. Yazıların eşit olduğu anlamına **gelmez**; tamamen farklı iki yazı için de 0 döner. `strncmp(a, b, strlen(a) + 1)`, `strcmp(a, b)` ile aynı: `a`'nın `'\0'`'ı dahil karşılaştırılır, `'\0'`'da ya eşitlik (iki yazı da bitti → 0) ya da fark bulunur. `a`, `b`'den uzunsa fark zaten `strlen(a)`'dan önce çıkar. (`strlen(b) + 1` kullansaydık ve `a` uzun olsaydı, `b` bitmeden önce zaten ayrışırlardı; yine aynı sonuç.)

**5** –

```c
int casecmp(const char *a, const char *b) {
    const unsigned char *x = (const unsigned char *)a;
    const unsigned char *y = (const unsigned char *)b;
    while (*x != '\0' && lower(*x) == lower(*y)) {
        x++;
        y++;
    }
    return (int)lower(*x) - (int)lower(*y);
}
```

`lower`, Ders 4.11'deki gibi büyük harfi küçülten yardımcı (Ders 4.19'da `tolower`). `unsigned char` yine şart: `lower` ASCII dışı byte'lara dokunmayıp olduğu gibi döndürüyor, ve o byte'lar yine 128–255 arası; işaretli `char`'la karşılaştırılırsa Bölüm 3'teki sıralama hatası geri gelir. "Harfe duyarsız" olmak, "işarete duyarsız" olmak değil.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.5 ve §B3: `strcmp`.
- C standardı (ISO/IEC 9899:2018), §7.24.4: `strcmp`, `strncmp` ve karşılaştırmanın `unsigned char` olarak yapılması.
- SEI CERT C Coding Standard, STR37-C: karakter sınıflandırma ve karşılaştırmada argümanları `unsigned char` olarak vermek.
- Peter van der Linden, *Expert C Programming*, Bölüm 2: `char`'ın işaretliliğinin taşınabilirlik sorunları.

**Sıradaki ders:** `strchr`, `strrchr` ve `strstr` sıfırdan. Bir yazıda karakter ve alt dizi aramak, naif aramanın karmaşıklığı ve KMP'ye köprü.
