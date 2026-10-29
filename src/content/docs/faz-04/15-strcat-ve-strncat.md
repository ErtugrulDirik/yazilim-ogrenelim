---
title: "4.15 strcat ve strncat sıfırdan"
description: "İki yazıyı birleştirmek: strcat'in önce sonu arayıp sonra kopyalaması, strncat'in strncpy'den farklı olarak her zaman sonlandırması, bir yazıyı parça parça kurarken her strcat'in baştan sonu araması yüzünden işin kareli zamana çıkması (Shlemiel the painter), kuyruk pointer'ıyla doğrusal çözüm ve kesilmeyi bildiren strlcat."
---

Ders 4.14'te bir yazıyı kopyaladık. Bu derste iki yazıyı **birleştiriyoruz** (concatenation): `src`'yi `dest`'in **sonuna** ekleyeceğiz. Fonksiyonun kendisi `strcpy`'nin küçük bir varyasyonu; asıl ders, bu fonksiyonu bir döngü içinde kullanmanın gizli maliyeti. Ders 4.13'teki "döngü koşulunda `strlen`" tuzağının çok daha sinsi bir akrabası.

---

## 1. strcat

```c
char *strcat(char *restrict dest, const char *restrict src);
```

`dest`, zaten `'\0'` ile biten bir yazı olmalı. `strcat`, önce `dest`'in sonundaki `'\0'`'ı buluyor, sonra `src`'yi oradan itibaren kopyalıyor (`'\0'` dahil). İki parçalı:

```c
char *strcat_mine(char *dest, const char *src) {
    char *d = dest;
    while (*d != '\0') {
        d++;
    }
    while ((*d++ = *src++) != '\0') {
    }
    return dest;
}
```

İlk döngü `d`'yi `dest`'in `'\0'`'ına kadar ilerletiyor — yani `strlen(dest)` kadar adım. İkinci döngü Ders 4.14'teki `strcpy_pointer`'ın aynısı. `strcat`, `strlen(dest) + strlen(src)` byte dokunuyor; ve `strcpy` gibi, **`dest`'in boyutunu bilmiyor**: `dest`'te hem mevcut yazıya hem eklenene hem de `'\0'`'a yetecek yer olması çağıranın sorumluluğu.

`<string.h>`'teki `strcat` ile 200 binden fazla girdide (her uzunlukta önek + her uzunlukta ek) karşılaştırdık; `-fsanitize=address,undefined` ile tek fark çıkmadı.

---

## 2. strncat: strncpy'nin aksine düzgün

```c
char *strncat(char *restrict dest, const char *restrict src, size_t n);
```

`strncat`, `src`'den en fazla `n` byte ekliyor. Ama Ders 4.14'teki `strncpy`'nin iki tuzağı **burada yok**:

```c
char *strncat_mine(char *dest, const char *src, size_t n) {
    char *d = dest;
    while (*d != '\0') {
        d++;
    }
    size_t i = 0;
    while (i < n && src[i] != '\0') {
        d[i] = src[i];
        i++;
    }
    d[i] = '\0';
    return dest;
}
```

- **Her zaman sonlandırıyor**: ikinci döngüden sonra `d[i] = '\0'` koşulsuz çalışıyor. `strncpy` bunu yapmıyordu.
- **Kalanı doldurmuyor**: tam `min(n, strlen(src))` byte ekleyip duruyor.

Yani `strncat`'teki `n`, `strncpy`'dekinden farklı anlama geliyor: "`src`'den en fazla kaç byte **ekle**" (sonlandırıcı hariç). İsimleri benzeyen iki fonksiyonun `n`'i bambaşka iş yapıyor — C standart kütüphanesinin tutarsızlıklarından biri. Yine de `strncat`'in de tehlikeli bir yanı var: `n`'i `dest`'in kalan boşluğuna göre doğru hesaplamak çağırana kalıyor (`sizeof dest - strlen(dest) - 1`), ve bu hesabı yanlış yapmak yine taşma demek.

---

## 3. Shlemiel the painter

Asıl ders burada. Diyelim bir yazıyı parça parça kuruyoruz: bir kelimeyi defalarca ekleyerek uzun bir metin oluşturacağız.

```c
void join_strcat(int count) {
    buffer[0] = '\0';
    for (int i = 0; i < count; i++) {
        strcat(buffer, "merhaba ");
    }
}
```

Masum görünüyor. Ama her `strcat` çağrısı, Bölüm 1'deki ilk döngüyle `buffer`'ın sonunu **baştan arıyor**. İlk çağrıda buffer boş, arama kısa. Ama bininci çağrıda buffer zaten 8000 karakter; `strcat` eklemeden önce o 8000 karakteri baştan sona geziyor. `count` kelime eklerken, aramalar $0 + 8 + 16 + \dots$ diye büyüyor; toplam $O(\text{count}^2)$.

Ölçelim — aynı metni bir de **kuyruk pointer'ı** tutarak kuralım, yani sonu her seferinde aramak yerine nerede kaldığımızı hatırlayalım:

```c
void join_tail(int count) {
    char *end = buffer;
    *end = '\0';
    for (int i = 0; i < count; i++) {
        const char *word = "merhaba ";
        while (*word != '\0') {
            *end++ = *word++;
        }
    }
    *end = '\0';
}
```

```
n =  10000  strcat 0.0222 s  tail 0.000028 s  (uzunluk 80000 / 80000)
n =  20000  strcat 0.0456 s  tail 0.000005 s  (uzunluk 160000 / 160000)
n =  40000  strcat 0.1203 s  tail 0.000009 s  (uzunluk 320000 / 320000)
n =  80000  strcat 0.4640 s  tail 0.000018 s  (uzunluk 640000 / 640000)
```

İki fonksiyon da aynı 640 bin karakterlik metni üretiyor. Ama `count` iki katına çıkınca `join_strcat` **dört kat** yavaşlıyor (0,022 → 0,046 → 0,12 → 0,46): $O(n^2)$'nin imzası (Ders 4.2). `join_tail` ise düz: hep $O(n)$, ve 80 bin kelime için `strcat` sürümünden yaklaşık 25 bin kat hızlı.

Bu kalıbın bir adı var: **Shlemiel the painter** problemi. Joel Spolsky'nin anlattığı fıkradaki Shlemiel, bir yol boyunca şerit çiziyor. İlk gün 300 metre boyuyor, herkes şaşırıyor. Ertesi gün 150, sonraki gün 30. Patron soruyor: "Neden gittikçe yavaşlıyorsun?" Shlemiel: "Boya kovası hep başlangıç noktasında; her seferinde oraya kadar geri yürümem gerekiyor." Her `strcat` çağrısı, boyaya geri yürüyen Shlemiel: eklemeye başlamak için her seferinde yazının başına dönüp sonu arıyor.

Compiler bunu `-O2`'de bile düzeltmedi: `buffer`'a yazıldığı için her çağrıda `strlen`'i yeniden hesaplamak zorunda (Ders 4.13'teki `upper_slow`'un aynı sebebi). Kurtuluş kodun kendisinde: **nerede kaldığını hatırla.** Bir yazıyı parça parça kuruyorsan, her parçadan sonra sonu yeniden aramak yerine sonu gösteren bir pointer taşı.

Ders 4.14'ten hatırla: `strcat`'in hiçbir sürümü `dest`'in boyutunu bilmiyor. Shlemiel sürümü hem yavaş **hem de** taşmaya açık.

---

## 4. strlcat: hem güvenli hem dürüst

Ders 4.14'teki `strlcpy`'nin eklemeli hali. `dest`'in **toplam** boyutunu alıyor, asla taşmıyor, her zaman sonlandırıyor, ve kesilme olsaydı oluşacak **toplam uzunluğu** döndürüyor:

```c
size_t strlcat(char *dest, const char *src, size_t size);
```

```c
size_t strlcat_mine(char *dest, const char *src, size_t size) {
    size_t dlen = 0;
    while (dlen < size && dest[dlen] != '\0') {
        dlen++;
    }
    if (dlen == size) {
        size_t slen = 0;
        while (src[slen] != '\0') {
            slen++;
        }
        return size + slen;
    }
    size_t i = 0;
    while (src[i] != '\0' && dlen + i < size - 1) {
        dest[dlen + i] = src[i];
        i++;
    }
    dest[dlen + i] = '\0';
    while (src[i] != '\0') {
        i++;
    }
    return dlen + i;
}
```

İlk döngü `dest`'in uzunluğunu ama en fazla `size`'a kadar buluyor — bu sınır önemli: `dest`'in ilk `size` byte'ı içinde `'\0'` yoksa (bozuk bir tampon), `dlen == size` olur ve fonksiyon, `dest`'e hiç dokunmadan `size + strlen(src)` döndürüp pes ediyor; sonsuza kadar okumaya çalışmıyor. Bu, `<bsd/string.h>` ve macOS'taki `strlcat`'in davranışıyla birebir (200 binden fazla girdide, bozuk önekler dahil, doğruladık).

`strlcat` de kuyruğu kendi içinde arıyor; yani onu da bir döngüde çağırırsan Shlemiel geri gelir. Fark şu: `strlcat` **taşmayacak**, ama hâlâ **yavaş** olabilir. Güvenlik ile performans ayrı sorunlar; `strlcat` birincisini çözüyor, ikincisini değil. Uzun bir yazıyı çok parçadan kuruyorsan doğru araç, her parçada sonu arayan hiçbir fonksiyon değil, Bölüm 3'teki kuyruk pointer'ı.

| | sonlandırır mı? | taşar mı? | kesilmeyi bildirir mi? | döngüde Shlemiel? |
| --- | --- | --- | --- | --- |
| `strcat` | evet | evet (kontrol yok) | hayır | evet |
| `strncat` | evet | sınırı yanlışsa | hayır | evet |
| `strlcat` | evet | hayır | evet (dönüş değeri) | evet (ama güvenli) |

---

## Alıştırmalar

**1** – `strcat_mine`'ın ilk döngüsü yerine Ders 4.13'teki `strlen`'i, ikinci kısmı yerine Ders 4.14'teki `strcpy`'yi kullanarak `strcat`'i iki satırda yaz: `strcpy(dest + my_strlen(dest), src); return dest;`. Çalışır mı? Bu sürüm, elle yazılandan daha mı yavaş?

**2** – `join_strcat`'in neden $O(n^2)$ olduğunu, aramaların toplamının $8 \times (0 + 1 + \dots + (n-1))$ olduğunu göstererek açıkla. $n = 80000$ için bu kaç karakter okuması eder? `join_tail` kaç eder?

**3** – Bölüm 3'teki `join_tail`'i güvenli yap: `buffer`'ın boyutunu bir parametre olarak al ve taşacaksan dur. Dönüş değeri ne olmalı? (Ders 4.14'teki `strlcpy`'nin dönüş değerini düşün.)

**4** – `strncat_mine(dest, src, 0)` ne yapar? `dest`'i değiştirir mi? Peki `strncpy`'nin `n = 0` hali (Ders 4.14)?

**5** – `strlcat_mine`'da `size` kadar okuyan ilk döngü yerine `strlen(dest)` yazsaydık ne değişirdi? Bozuk (sonlandırılmamış) bir `dest` için iki sürüm nasıl davranır?

<details>
<summary>Cevaplar</summary>

**1** –

```c
char *strcat_short(char *dest, const char *src) {
    strcpy(dest + my_strlen(dest), src);
    return dest;
}
```

Çalışır: `dest + my_strlen(dest)`, `dest`'in `'\0'`'ını gösteriyor (Ders 4.6'daki pointer aritmetiği); `strcpy` oradan itibaren `src`'yi yazıyor. Hızı aynı: `my_strlen` yine sonu bir kez arıyor, `strcpy` ekliyor. Tek bir çağrı için fark yok; ama bu sürümü de bir döngüde çağırırsan Shlemiel aynen geri gelir, çünkü `my_strlen` her çağrıda sonu baştan arıyor.

**2** – Her `strcat`'in ilk döngüsü, o ana kadar birikmiş yazının uzunluğu kadar adım atıyor. `i`. çağrıda yazı `8i` karakter (her kelime 8 byte). Toplam arama: $\sum_{i=0}^{n-1} 8i = 8 \cdot \frac{n(n-1)}{2} \approx 4n^2$. $n = 80000$ için $4 \times 80000^2 \approx 2{,}56 \times 10^{10}$: 25 milyar karakter okuması, sadece sonu bulmak için. `join_tail` ise her kelimede sadece o kelimeyi yazıyor: toplam $8n = 640000$. Oran ~40 bin; ölçtüğümüz hız farkıyla uyumlu.

**3** –

```c
size_t append(char *buffer, size_t size, char **end, const char *word) {
    size_t written = (size_t)(*end - buffer);
    while (*word != '\0') {
        if (written + 1 >= size) {
            **end = '\0';
            return written + my_strlen(word);
        }
        **end = *word;
        (*end)++;
        word++;
        written++;
    }
    **end = '\0';
    return written;
}
```

`end` bir `char **` (Ders 4.10): kuyruk pointer'ını çağıranın değişkeninde güncelliyoruz, böylece bir sonraki çağrı kaldığı yerden devam ediyor — hem hızlı hem güvenli. Dönüş değeri, `strlcpy` gibi, kesme olmasaydı oluşacak uzunluk; `>= size` ise taştı demektir. (Daha sade bir tasarım: sadece kuyruk pointer'ını döndürüp taşmayı ayrı kontrol etmek.)

**4** – `strncat_mine(dest, src, 0)`: ikinci döngü hiç dönmez (`i < 0` yanlış), ama `d[0] = '\0'` yine çalışır — yani `dest`'in zaten orada olan `'\0'`'ının üzerine aynı `'\0'`'ı yazar. `dest` **değişmez**. `strncpy(dest, src, 0)` ise hiçbir şey yapmaz, `dest`'e tek byte bile yazmaz (döngü koşulu `i < 0` baştan yanlış, dolgu döngüsü de). İkisi de güvenli ama farklı: `strncat` sonlandırmayı "garanti" ettiği için `dest[current_len]`'e dokunur, `strncpy` dokunmaz.

**5** – `strlen(dest)` kullansaydık, sonlandırılmış bir `dest` için sonuç aynı olurdu. Fark bozuk bir `dest`'te: `strlen`, ilk `size` byte'ta `'\0'` olmasa bile aramaya **devam eder**, tamponun dışına taşar ve undefined behavior / çökme üretir. `size` ile sınırlı döngü ise en fazla `size` byte okur, `dlen == size` görüp güvenle pes eder. `strlcat`'in `size` parametresini almasının bütün anlamı bu: kaynağa güvenmeden, tamponun sınırını aşmadan çalışmak.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §B3: `strcat`, `strncat`.
- C standardı (ISO/IEC 9899:2018), §7.24.3.1 (`strcat`), §7.24.3.2 (`strncat`).
- Todd C. Miller & Theo de Raadt, "strlcpy and strlcat" (USENIX 1999).
- Joel Spolsky, "Back to Basics" (2001): Shlemiel the painter algoritması.
- SEI CERT C Coding Standard, STR31-C: birleştirmede hedefin yeterli olduğundan emin olmak.

**Sıradaki ders:** `strcmp` ve `strncmp` sıfırdan. Dönüş değerinin sözleşmesi, ve neden karakterleri `unsigned char` olarak karşılaştırmak gerektiği.
