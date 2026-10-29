---
title: "4.19 ctype.h sıfırdan"
description: "Karakter sınıflandırma: isdigit, isupper, islower, isalpha, isalnum, isspace aralık kontrolleriyle; ASCII'de büyük ve küçük harfi sadece 5. bitin (0x20) ayırması, toupper ve tolower'ın bu bitle, tablo tabanlı sürüm ve her karakter için bir byte'lık bayrak; ctype fonksiyonlarının int alıp unsigned char beklemesi ve işaretli char'la gelen negatif argümanın undefined behavior olması."
---

Ders 4.11 ve 4.16'daki karşılaştırıcılarda büyük harfi küçülten bir `lower` yardımcısı yazdık ve "Ders 4.19'da `tolower` ile yapacağız" dedik. Ders 3.17'de rakam kontrolü, Ders 4.12'de `read_int`'te boşluk kontrolü yaptık. Bu işlerin hepsi `<ctype.h>`'te: karakterleri **sınıflandıran** (`isdigit`, `isalpha`, …) ve **dönüştüren** (`toupper`, `tolower`) küçük fonksiyonlar.

Hepsi tek satırlık aralık kontrolleri; asıl ilginç olan ikisi: büyük–küçük harf dönüşümünün tek bir bitle yapılabilmesi, ve bu fonksiyonların `int` alıp `unsigned char` beklemesinin Ders 3.2'deki `char` işaretliliğiyle bağlantısı.

---

## 1. Sınıflandırma: aralık kontrolleri

ASCII (Faz 0) sıralı olduğu için (Ders 3.16: `'0'`–`'9'` art arda, harfler art arda), çoğu kontrol bir aralık sorusu:

```c
int isdigit_mine(int c) {
    return c >= '0' && c <= '9';
}

int isupper_mine(int c) {
    return c >= 'A' && c <= 'Z';
}

int islower_mine(int c) {
    return c >= 'a' && c <= 'z';
}

int isalpha_mine(int c) {
    return isupper_mine(c) || islower_mine(c);
}

int isalnum_mine(int c) {
    return isalpha_mine(c) || isdigit_mine(c);
}

int isspace_mine(int c) {
    return c == ' ' || c == '\t' || c == '\n' || c == '\r' || c == '\v' || c == '\f';
}
```

- `isdigit`, Ders 3.17'deki `c >= '0' && c <= '9'` kontrolünün aynısı. Standart sadece rakamların art arda olmasını garanti ediyor (Ders 3.17'deki not), harflerin değil; ama ASCII'de harfler de art arda, ve bu seri ASCII varsayıyor.
- `isalpha`, `isalnum` daha küçük kontrollerden kuruluyor.
- `isspace`, altı "boşluk" karakteri: boşluk, tab, yeni satır, satır başı, dikey tab, sayfa ileri. Ders 4.12'deki `is_blank`'in tam hali.

Her birini standart sürümle 128 ASCII değerinin hepsinde karşılaştırdık; sıfır fark. (Standart fonksiyonlar 0 ya da sıfırdan farklı bir değer döndürür; "sıfırdan farklı"nın illa 1 olması gerekmiyor, bu yüzden `!!` ile ikisini de 0/1'e indirip karşılaştırdık.)

---

## 2. 0x20 hilesi: büyük ve küçük harf

`toupper` ve `tolower` için akla ilk gelen, Ders 4.11'deki gibi sabit farkı (`'a' - 'A'` = 32) eklemek/çıkarmak. Ama ASCII tablosunda daha zarif bir şey var. Büyük ve küçük harflerin bit desenlerine bakalım:

```
A = 01000001 (0x41)   a = 01100001 (0x61)
Z = 01011010 (0x5a)   z = 01111010 (0x7a)
M = 01001101 (0x4d)   m = 01101101 (0x6d)
```

Her çiftte **tek bir bit** farklı: soldan üçüncü, yani 5. bit (değeri $2^5 = 32 = $ `0x20`). Büyük harflerde 0, küçüklerde 1. ASCII bunu bilerek böyle tasarlamış: harfin kendisini değiştirmeden büyük/küçük yapmak bir bit işlemi (Ders 3.18'deki `&`, `|`).

```c
int toupper_mine(int c) {
    if (islower_mine(c)) {
        return c & ~0x20;
    }
    return c;
}

int tolower_mine(int c) {
    if (isupper_mine(c)) {
        return c | 0x20;
    }
    return c;
}
```

- `c | 0x20` → 5. biti **1 yap** (küçült). `C` (`0x43`) → `c` (`0x63`).
- `c & ~0x20` → 5. biti **0 yap** (büyült). `~0x20`, 5. bit hariç bütün bitleri 1 olan maske (Ders 3.18); `&` ile o bit sıfırlanır, diğerleri korunur.

Önemli: dönüşümü **sadece harflere** uyguluyoruz. `tolower('5')` `'5'` olmalı, `'5' | 0x20` değil (o başka bir karakter çıkarırdı). Bu yüzden `if (isupper_mine(c))` kontrolü şart. Standart `toupper`/`tolower` de harf olmayan her şeyi olduğu gibi döndürür. 128 ASCII değerinde standart sürümle karşılaştırdık: sıfır fark.

Bu hile sadece ASCII harfleri için çalışıyor; Türkçe `İ`/`i`, `I`/`ı` ikilisi (Ders 4.12'deki UTF-8) bu desene uymaz, çok byte'lıdır ve dile bağlıdır. `<ctype.h>`, adının aksine, sadece tek byte'lık "C yerel ayarı"nı (C locale) bilir.

---

## 3. Tablo tabanlı sürüm

Aralık kontrolleri hızlı, ama her çağrıda birkaç karşılaştırma yapıyor. Gerçek kütüphaneler genelde başka bir yöntem kullanıyor: her olası byte (0–255) için, o byte'ın hangi sınıflara girdiğini bir **bayrak byte'ında** önceden hesaplayıp bir tabloda saklamak. Sınıflandırma, tek bir tablo okuması ve bir bit kontrolüne iner.

Her sınıf bir bit (Ders 3.18'deki bayraklar):

```c
#define CT_DIGIT 0x01u
#define CT_UPPER 0x02u
#define CT_LOWER 0x04u
#define CT_SPACE 0x08u

static unsigned char table[256];

void build_table(void) {
    for (int c = '0'; c <= '9'; c++) table[c] |= CT_DIGIT;
    for (int c = 'A'; c <= 'Z'; c++) table[c] |= CT_UPPER;
    for (int c = 'a'; c <= 'z'; c++) table[c] |= CT_LOWER;
    const char *sp = " \t\n\r\v\f";
    for (int i = 0; sp[i] != '\0'; i++) {
        table[(unsigned char)sp[i]] |= CT_SPACE;
    }
}
```

Her byte için tablo, o byte'ın sınıflarını bir arada tutuyor; örneğin `table['A']` = `CT_UPPER`. Sınıflandırma artık tek bir tablo bakışı:

```c
int isalpha_t(int c) {
    return (c >= 0 && c < 256) && (table[c] & (CT_UPPER | CT_LOWER));
}

int isalnum_t(int c) {
    return (c >= 0 && c < 256) && (table[c] & (CT_UPPER | CT_LOWER | CT_DIGIT));
}
```

`isalpha` artık "büyük **ya da** küçük mü?" sorusunu iki aralık kontrolüyle değil, bir tablo okuması ve bir bit maskesiyle cevaplıyor. `isalnum` aynı tabloya bir bit daha ekleyerek bakıyor; yeni bir aralık kontrolü yok. 128 ASCII değerinde standart sürümle karşılaştırdık: sıfır fark.

Tablo yaklaşımının avantajı: yeni bir sınıf eklemek (örneğin `isxdigit`, onaltılık rakam) sadece bir bit ve tabloyu kurarken bir döngü; sorgu kodu değişmiyor. Dezavantajı: 256 byte'lık bir tablo ve onu bir kez kurmak. Gerçek `<ctype.h>` sürümleri tabloyu derleme sırasında hazır gömüyor, `build_table`'a gerek kalmıyor. Ders 4.11'deki işlem tablosu gibi, "hesaplama yerine arama" fikri.

---

## 4. int neden, ve negatif argüman tuzağı

`<ctype.h>` fonksiyonlarının hepsi `char` değil **`int`** alıyor:

```c
int isdigit(int c);
int toupper(int c);
```

Sebep Ders 3.16'daki `getchar` ile aynı: bu fonksiyonlar `getchar`'ın döndürdüğü değerle doğrudan çalışabilsin diye. `getchar`, ya 0–255 arası bir byte ya da `EOF` (−1) döndürüyor; `int`, ikisini de taşıyabiliyor.

Buradan C'nin en sinsi tuzaklarından biri çıkıyor. Standart şunu söylüyor: `<ctype.h>` fonksiyonlarının argümanı ya **`unsigned char` olarak gösterilebilir bir değer** (0–255) ya da **`EOF`** olmalı. Başka bir değer vermek **undefined behavior**.

Peki nasıl başka bir değer veririz? Ders 3.2'den: bu makinede `char` **işaretli**. Ders 4.12'den: UTF-8'de `ç`, `ğ` gibi harfler 128–255 arası byte'larla yazılıyor, ve işaretli bir `char`'da bunlar **negatif**. Bir yazıyı gezip her `char`'ı doğrudan `isalpha`'ya verirsek:

```c
char s[] = "cafe\xc3";    // sonda 0xc3
for (int i = 0; s[i] != '\0'; i++) {
    char c = s[i];
    isalpha(c);           // c, 0xc3 için -61: UB
}
```

`0xc3` byte'ı, işaretli `char` olarak −61. `isalpha(-61)` undefined behavior: bu makinede sessizce 0 döndürüyor, glibc'nin tablo tabanlı sürümünde tablonun **dışını** (negatif indeks) okuyor. Doğrusu, Ders 4.16'daki gibi `unsigned char`'a çevirmek:

```c
isalpha((unsigned char)c);   // 0xc3 için 195: tanimli
```

Bölüm 3'teki tablo sürümümüz, `c >= 0 && c < 256` kontrolüyle kendini koruyor — ama standart `<ctype.h>` bu kontrolü yapmıyor (hız için), sorumluluğu çağırana bırakıyor. Kural: **bir `char`'ı `<ctype.h>` fonksiyonuna verirken her zaman `(unsigned char)` ile çevir.**

İlginç bir ayrıntı: aynı programı Linux ARM'de çalıştırınca sorun **hiç çıkmıyor**, çünkü orada `char` **işaretsiz** (Ders 3.2'deki platform farkı); `s[i]` doğrudan 195 oluyor. Yani bu hata, kodun çalıştığı makinenin `char` işaretliliğine göre bazen ortaya çıkıp bazen çıkmıyor — taşınabilirlik hatalarının en can sıkıcı türü. `(unsigned char)` cast'i her platformda doğru.

---

## Alıştırmalar

**1** – `isxdigit` (onaltılık rakam: `0`–`9`, `a`–`f`, `A`–`F`) ve `ispunct` (yazdırılabilir ama harf/rakam/boşluk olmayan) fonksiyonlarını aralık kontrolleriyle yaz. `ispunct`'u tanımlamak için hangi aralıkları bilmen gerekiyor? (ASCII tablosu: yazdırılabilir karakterler 32–126.)

**2** – `toupper_mine`'ı `0x20` hilesi yerine `c - ('a' - 'A')` ile yaz. İkisi ASCII harfleri için aynı sonucu verir mi? `0x20` sürümünün bir avantajı var mı (ipucu: hangisi daha hızlı, hangisi daha açık)?

**3** – `c ^ 0x20`, bir harfin büyük/küçük halini **ters çevirir** (`XOR`; Ders 3.18). `'A' ^ 0x20` = ?, `'a' ^ 0x20` = ? Bir yazının her harfinin büyük/küçüklüğünü ters çeviren `void swap_case(char *s)` yaz. Harf olmayanlara dokunmamalı.

**4** – Bölüm 3'teki tabloya `CT_PRINT` (yazdırılabilir, 32–126) biti ekle ve `isprint_t` yaz. Sonra `isgraph` (boşluk hariç yazdırılabilir) fonksiyonunu **yeni bir tablo biti eklemeden**, mevcut bitlerle nasıl yazarsın?

**5** – `atoi`'nin basit bir halini yaz (Ders 3.17), ama boşlukları atlarken `isspace((unsigned char)*p)`, rakamları okurken `isdigit((unsigned char)*p)` kullan. `(unsigned char)` cast'ini unutursan, hangi girdi bu makinede soruna yol açar? Linux ARM'de?

<details>
<summary>Cevaplar</summary>

**1** –

```c
int isxdigit_mine(int c) {
    return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
}

int isprint_mine(int c) {
    return c >= 32 && c <= 126;
}

int ispunct_mine(int c) {
    return isprint_mine(c) && c != ' ' && !isalnum_mine(c);
}
```

`ispunct`: yazdırılabilir (32–126) olup harf, rakam veya boşluk olmayan. Yani `!`, `@`, `{`, `,` gibi noktalama ve simgeler. Boşluğun (32) yazdırılabilir ama `ispunct` olmadığına dikkat: ayrıca dışlıyoruz.

**2** – ASCII harfleri için ikisi de aynı: `'a' - 'A'` = 32 = `0x20`, küçük harfte bu bit 1 olduğu için çıkarma onu 0 yapar, tam `c & ~0x20` gibi. Fark harf olmayan değerlerde çıkar (ama ikisini de `if (islower(c))` koruduğu için sorun olmaz). `0x20` sürümü teoride bir çıkarma yerine bir `AND`/`OR`; modern işlemcide hız farkı yok. Asıl avantajı **niyetin açıklığı**: `& ~0x20` "büyük/küçük bitini temizle" diyor, `- 32` ise "32 çıkar" — ilki ne yaptığını anlatıyor. İkisi de kabul edilir; gerçek kütüphaneler çoğunlukla tabloyla yapıyor.

**3** – `'A' ^ 0x20` = `'a'` (5. bit 0→1), `'a' ^ 0x20` = `'A'` (5. bit 1→0). `XOR` biti "çevirdiği" için büyüğü küçüğe, küçüğü büyüğe döndürür.

```c
void swap_case(char *s) {
    for (; *s != '\0'; s++) {
        if (isalpha_mine((unsigned char)*s)) {
            *s = (char)(*s ^ 0x20);
        }
    }
}
```

`isalpha` kontrolü şart: `'5' ^ 0x20` başka bir karakter verirdi. `"Merhaba"` → `"mERHABA"`.

**4** –

```c
#define CT_PRINT 0x10u
// build_table icinde:
for (int c = 32; c <= 126; c++) table[c] |= CT_PRINT;

int isprint_t(int c) {
    return (c >= 0 && c < 256) && (table[c] & CT_PRINT);
}
```

`isgraph` (boşluk hariç yazdırılabilir), yeni bir bit gerektirmiyor: "yazdırılabilir **ve** boşluk değil". Boşluk (32) `CT_SPACE` taşıdığı için:

```c
int isgraph_t(int c) {
    return (c >= 0 && c < 256) && (table[c] & CT_PRINT) && !(table[c] & CT_SPACE);
}
```

Daha temiz: boşluk zaten `CT_SPACE`'te olduğundan, tek dışladığımız karakter o. Bitleri birleştirerek yeni sınıflar türetmek, tablo yaklaşımının gücü.

**5** –

```c
int atoi_mine(const char *s) {
    const char *p = s;
    while (isspace((unsigned char)*p)) {
        p++;
    }
    int sign = 1;
    if (*p == '+' || *p == '-') {
        if (*p == '-') sign = -1;
        p++;
    }
    int value = 0;
    while (isdigit((unsigned char)*p)) {
        value = value * 10 + (*p - '0');
        p++;
    }
    return sign * value;
}
```

`(unsigned char)` olmadan, yazıda 128–255 arası bir byte olan her girdi (örneğin baştaki boşluklardan sonra bir `ç` gelen `"  çay"`) bu makinede `isspace(-61)` ya da `isdigit(-61)` çağırır: undefined behavior. Linux ARM'de `char` işaretsiz olduğu için aynı girdi sorunsuz çalışır (195 geçerli bir argüman). Hata, sadece işaretli `char` platformlarında ve sadece ASCII dışı byte içeren girdilerde ortaya çıkar — bu yüzden test edilmesi zor, cast'i her zaman yazmak gerekli. (`atoi` taşmayı da kontrol etmiyor; doğrusu Ders 3.17'deki `strtol`.)

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §B2: `<ctype.h>`.
- C standardı (ISO/IEC 9899:2018), §7.4: karakter sınıflandırma; §7.4¶1: argümanın `unsigned char` olarak gösterilebilir olması ya da `EOF` olması şartı.
- SEI CERT C Coding Standard, STR37-C: `<ctype.h>` fonksiyonlarına `unsigned char`'a çevrilmiş argüman vermek.
- Faz 0'daki ASCII tablosu: büyük ve küçük harflerin 0x20 ile ayrılması.

**Sıradaki ders:** `strtok` sıfırdan. Gizli durum (`static`), neden yeniden girilemez olduğu ve `strtok_r`.
