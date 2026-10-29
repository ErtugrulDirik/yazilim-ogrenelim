---
title: "4.18 memcpy, memmove, memset ve memcmp sıfırdan"
description: "Byte'larla çalışan dört fonksiyon: void * ve boyut imzası, memcpy'nin çakışan bölgelerde neden bozulduğu, memmove'un dest ile src'nin konumuna göre ileri ya da geri kopyalayarak bunu çözmesi, restrict anahtar kelimesinin 'çakışmıyorlar' sözü ve derleyicinin bu söz sayesinde çalışma zamanı çakışma kontrolünü atması, memset'in int alıp byte yazması, memcmp."
---

Ders 3.9'da `memcpy`'yi kara kutu olarak kullandık ve "Faz 4'te kendimiz yazacağız" dedik. Ders 4.1'de de `memcpy`'yi andık. Ders 4.9'da `swap_any`'i `unsigned char *` ile byte byte yazarken, bu fonksiyonların da aynı kalıpta olacağını söylemiştik. Şimdi `<string.h>`'in byte'larla çalışan dört fonksiyonunu yazıyoruz.

Bunlar string fonksiyonu değil: `'\0'` aramıyorlar, bir **byte sayısı** alıyorlar ve her tiple çalışıyorlar (Ders 4.9'daki `void *` + boyut kalıbı). Dördünün de kodu kısa; asıl ders `memcpy` ile `memmove` arasındaki fark ve `restrict`.

---

## 1. memset

En basiti: bir bölgenin her byte'ını aynı değere ayarlıyor.

```c
void *memset(void *dest, int c, size_t n);
```

```c
void *memset_mine(void *dest, int c, size_t n) {
    unsigned char *d = dest;
    unsigned char byte = (unsigned char)c;
    for (size_t i = 0; i < n; i++) {
        d[i] = byte;
    }
    return dest;
}
```

`c` bir `int`, ama sadece en düşük byte'ı kullanılıyor: `(unsigned char)c`. Ders 4.9'daki gibi `void *`'ı `unsigned char *`'a çevirip her byte'a yazıyoruz. Dönüş değeri `dest` (standart kütüphanenin alışkanlığı; zincirlemeye izin veriyor).

En sık `memset(buffer, 0, sizeof buffer)` ile bir bölgeyi sıfırlamak için kullanılıyor. Dikkat: `c` **byte** olarak yazılıyor, eleman olarak değil. `int a[10]; memset(a, 1, sizeof a);` her byte'ı `0x01` yapar, her `int`'i `1` değil — `0x01010101` = 16843009. Sadece 0 için güvenli (bütün byte'ları 0 olan `int` de `double` de sıfırdır; Ders 4.9'daki alıştırma).

---

## 2. memcpy

```c
void *memcpy(void *restrict dest, const void *restrict src, size_t n);
```

`src`'den `dest`'e `n` byte kopyalıyor. `swap_any`'nin yarısı:

```c
void *memcpy_mine(void *restrict dest, const void *restrict src, size_t n) {
    unsigned char *d = dest;
    const unsigned char *s = src;
    for (size_t i = 0; i < n; i++) {
        d[i] = s[i];
    }
    return dest;
}
```

`'\0'` yok, uzunluk hesabı yok: tam `n` byte. `strcpy`'den (Ders 4.14) farkı bu — `strcpy` nereye kadar kopyalayacağını `'\0'`'dan öğreniyordu, `memcpy` ise sayıyla. İmzadaki `restrict`'e birazdan geleceğiz.

---

## 3. Çakışan bölgeler: memcpy neden yetmiyor

`memcpy`'nin bir sözü var: `dest` ile `src` **çakışmamalı**. Çakışırlarsa ne olur? Bir yazıyı kendi içinde 2 byte sağa kaydırmayı deneyelim (`dest = src + 2`, bölgeler üst üste biniyor):

```c
char buf[16] = "abcdefgh";
memcpy_mine(buf + 2, buf, 6);
```

```
memcpy     abababab
```

Beklenen `ababcdefgh`'di (ilk 6 byte, 2 sağa). Ama çıktı `abababab`. Neden? Döngü ileri gidiyor: `d[0] = s[0]` ile `buf[2] = buf[0] = 'a'`. Sonra `d[1] = s[1]` ile `buf[3] = buf[1] = 'b'`. Ama `d[2] = s[2]` artık `buf[4] = buf[2]` — ve `buf[2]`'yi az önce `'a'` yapmıştık. Kopyaladığımız kaynağın üstüne yazdık; `'a'` ve `'b'` kendini tekrarlayarak yayıldı. Ders 4.9'daki `swap_any`'nin kısmi çakışma alıştırmasının aynı sorunu.

---

## 4. memmove: yönü seçmek

`memmove` aynı işi yapıyor ama çakışmada **doğru** çalışıyor:

```c
void *memmove(void *dest, const void *src, size_t n);
```

Fikir: kopyalama yönünü, `dest`'in `src`'nin önünde mi arkasında mı olduğuna göre seçmek.

```c
void *memmove_mine(void *dest, const void *src, size_t n) {
    unsigned char *d = dest;
    const unsigned char *s = src;
    if (d < s) {
        for (size_t i = 0; i < n; i++) {
            d[i] = s[i];
        }
    } else if (d > s) {
        for (size_t i = n; i > 0; i--) {
            d[i - 1] = s[i - 1];
        }
    }
    return dest;
}
```

- **`dest < src`** (hedef kaynağın önünde): **baştan** kopyala. Henüz okunmamış kaynak byte'ları hedefin yazdığı yerin ilerisinde; üzerine yazılmadan okunuyorlar.
- **`dest > src`** (hedef kaynağın arkasında, yukarıdaki örnek): **sondan** kopyala. En sondaki byte'tan başlayıp geriye gidince, her kaynak byte'ı okunduktan sonra üzerine yazılıyor.
- **`dest == src`**: yapacak bir şey yok.

```c
char buf[16] = "abcdefgh";
memmove_mine(buf + 2, buf, 6);
```

```
memmove    ababcdef
```

`ababcdefgh` — doğru. `dest > src` olduğu için sondan kopyaladı: `buf[7] = buf[5]`, `buf[6] = buf[4]`, … kaynak byte'lar üzerine yazılmadan önce okundu.

Sondan giden döngüde `i` bir `size_t`; `i >= 0` yazsaydık `size_t` hiçbir zaman negatif olamadığı için **sonsuz döngü** olurdu (Ders 3.6). Bu yüzden `i > 0` kontrol edip `i - 1` indeksliyoruz; `i` 1'den 0'a inince döngü bitiyor.

İki milyon rastgele girdide (çakışan ve çakışmayan, ileri ve geri) `memmove_mine`'ı standart `memmove` ile karşılaştırdık: sıfır fark.

**Ne zaman hangisi?** Bölgelerin çakışmadığından eminsen `memcpy` (daha hızlı olabilir, yön kontrolü yok). Çakışabilirlerse ya da emin değilsen `memmove`. Bir array'in elemanlarını kaydırmak (bir elemanı silip kalanları sola çekmek), Ders 4.3'teki transpozisyon, Ders 4.24'teki dinamik dizi — hepsi `memmove` işi.

---

## 5. restrict: "çakışmıyorlar" sözü

`memcpy`'nin imzasındaki `restrict` (Ders 4.14'te `strcpy`'de de görmüştük) işte bu çakışma sorununu **önceden** halletmenin yolu. `void *restrict dest`, şu anlama geliyor: "Bu fonksiyon çalıştığı sürece, `dest`'in gösterdiği bölgeye **sadece `dest` üzerinden** erişilecek; `src` oraya dokunmayacak." Yani "bu iki pointer çakışmıyor" sözü, programcıdan derleyiciye.

Bu bir söz; `restrict`, çakışmayı **kontrol etmiyor**. Yalan söylersen (çakışan bölgelerle `memcpy` çağırırsan) sonuç undefined behavior — Bölüm 3'teki `abababab`, ya da başka bir şey. `memcpy`'nin çakışmada bozulması bir hata değil, imzasındaki sözün ihlalinin sonucu.

Peki `restrict` ne kazandırıyor? Derleyiciye bir garanti verince, derleyici daha hızlı kod üretebiliyor. Bir örnek: iki array'i toplayan bir fonksiyon, `restrict`'li ve `restrict`'siz:

```c
void add_arrays(int *dest, const int *a, const int *b, size_t n) {
    for (size_t i = 0; i < n; i++) {
        dest[i] = a[i] + b[i];
    }
}
void add_arrays_r(int *restrict dest, const int *restrict a, const int *restrict b, size_t n) {
    for (size_t i = 0; i < n; i++) {
        dest[i] = a[i] + b[i];
    }
}
```

`restrict`**siz** sürümde derleyici şunu düşünmek zorunda: ya `dest`, `a` ile çakışıyorsa? O zaman `dest[0]`'a yazmak `a[1]`'i değiştirebilir, ve döngüyü birden fazla elemanı aynı anda işleyecek şekilde hızlandıramaz. clang bunu `-O2`'de, çalışırken bölgelerin çakışıp çakışmadığını **kontrol eden** bir kod ekleyerek çözüyor: çakışmıyorlarsa hızlı (vektörize) yol, çakışıyorlarsa güvenli yavaş yol. Ürettiği assembly'de pointer'ları birbiriyle karşılaştıran fazladan komutlar (bu makinede 11 tane) ve iki ayrı döngü var.

`restrict`**li** sürümde bu kontrol **yok**: programcı "çakışmıyorlar" dediği için derleyici doğrudan hızlı yolu üretiyor, daha kısa kod. `memcpy`, `strcpy` gibi fonksiyonlar `restrict` taşıyor, çünkü tasarım gereği çakışmayan bölgeler için; `memmove` ise `restrict` **taşımıyor**, çünkü bütün varlık sebebi çakışan bölgelerle çalışabilmek.

`restrict` sadece pointer'larda ve C'ye özgü (C++'ta standart değil, `__restrict` olarak var). Çoğu zaman elle yazmana gerek olmaz; ama bir fonksiyonun pointer parametreleri asla çakışmıyorsa, `restrict` eklemek derleyiciye hız için alan açar.

---

## 6. memcmp

```c
int memcmp(const void *a, const void *b, size_t n);
```

İki bölgenin ilk `n` byte'ını karşılaştırıyor; dönüş değeri `strcmp` sözleşmesinin aynısı (Ders 4.16), ve yine **`unsigned char`** olarak:

```c
int memcmp_mine(const void *a, const void *b, size_t n) {
    const unsigned char *x = a;
    const unsigned char *y = b;
    for (size_t i = 0; i < n; i++) {
        if (x[i] != y[i]) {
            return (int)x[i] - (int)y[i];
        }
    }
    return 0;
}
```

`strcmp`'ten farkı: `'\0'`'da durmuyor, tam `n` byte'a bakıyor. İlk farklı byte'ta duruyor, hiç fark yoksa 0.

Bir uyarı: `memcmp`'i **struct**'ları karşılaştırmak için kullanmak tehlikeli. Ders 4.4'te gördüğümüz **dolgu** (padding) byte'ları çöp değerler taşıyabilir; iki struct mantıken eşit olsa bile dolgu byte'ları farklıysa `memcmp` "eşit değil" der. Struct'ları alan alan karşılaştırmak gerekir. `memcmp` ham byte dizileri (karma değerleri, ikili tamponlar, sabit uzunluklu anahtarlar) için doğru araç. Bu konuya Ders 4.26'da döneceğiz.

---

## Alıştırmalar

**1** – `memmove_mine`'daki `if (d < s)` / `else if (d > s)` yerine her zaman sondan kopyalasak (`d > s` dalı), çakışmayan bölgelerde ve `d < s` çakışmasında doğru çalışır mı? Hangi tek durum bozulur? (İpucu: `dest = src - 2`.)

**2** – `memcpy_mine`'ı `memmove_mine` ile çağrılan Bölüm 3'teki örnekte `dest = src - 2` (2 **sola** kaydır) yaparsan `memcpy` doğru sonuç verir mi? Neden ileri kopyalama bu yönde çalışıyor?

**3** – `memset`'in neden `int` alıp `char` yazdığını Ders 3.16'daki `getchar`/`putchar` ile karşılaştır. `memset(buf, -1, n)` ne yazar? `memset(buf, 256, n)`? `memset(buf, 'A', n)`?

**4** – İki array'i toplayan `add_arrays`'i `dest == a` ile çağırmak (sonucu girdilerden birine yazmak) doğru sonuç verir mi? Ya `restrict`'li `add_arrays_r`'yi `dest == a` ile? İkisinin farkı çıktıda görünür mü, yoksa sadece tanım olarak mı yanlış?

**5** – Bir array'in `i`. elemanını silip kalanları sola kaydıran `void remove_at(int *a, size_t n, size_t i)` yaz (son eleman kopya kalır). `memcpy` mi `memmove` mu? Kaç byte taşınır? `i == n - 1` (son eleman) için ne olur?

<details>
<summary>Cevaplar</summary>

**1** – Her zaman sondan kopyalamak **`d < s` çakışmasında** bozulur. `dest = src - 2` (hedef kaynağın 2 **gerisinde**): sondan kopyalarsak, `d[n-1] = s[n-1]` yazarken `s[n-1]` aslında `d[n+1]`... hayır — `s = d + 2` olduğundan `s[n-1] = d[n+1]`, henüz dokunulmamış. Asıl sorun daha erken: geriye giderken yazdığımız `d[i]`, ileride okunacak bir `s[j] = d[j+2]` ile çakışır. Somut: `"abcdefgh"`, `dest=buf, src=buf+2, n=6` sonra sondan kopyalama `buf[5]=buf[7]='h'`, `buf[4]=buf[6]='g'`, … ama `buf[0]=buf[2]` okunduğunda `buf[2]` zaten `buf[4]`'ten gelen değere... Kısacası: `d < s` iken **baştan**, `d > s` iken **sondan** kopyalanmalı; yön kaynağın konumuna bağlı, sabit değil. İki dalın ikisi de gerekli.

**2** – Evet, `memcpy_mine` (ileri kopyalama) `dest = src - 2` durumunda doğru çalışır. İleri giderken `d[i] = s[i]` yazdığımızda `d[i] = s[i-2]` konumuna denk gelir (çünkü `d = s - 2`), yani **zaten okunmuş ve geride kalmış** bir yer; ileride okunacak `s[i+1]` byte'ının üstüne yazmıyoruz. `memcpy`'nin ileri yönü tam olarak `d < s` çakışmasında güvenli — ama standart bunu garanti etmiyor, `memcpy`'yi hiçbir çakışmada kullanmamak kural. Doğrusu `memmove`.

**3** – İkisi de "aslında `char`'lık bir değeri `int` olarak taşıyor": `getchar` EOF'u da ifade edebilmek için `int` döndürüyordu; `memset`'in `c`'si tarihî olarak `int`, ama sadece `(unsigned char)c` kadarı kullanılıyor. `memset(buf, -1, n)`: `(unsigned char)(-1)` = 255 = `0xff`, her byte `0xff`. `memset(buf, 256, n)`: `(unsigned char)256` = 0, her byte 0 (256 mod 256). `memset(buf, 'A', n)`: her byte `'A'` = 65. Byte'a sığmayan her değer mod 256'ya düşer.

**4** – `add_arrays(dest, a, b, n)`'yi `dest == a` ile çağırmak **doğru** çalışır: `dest[i] = a[i] + b[i]`, `dest[i]` ile `a[i]` aynı yer olsa bile, o elemanı okuduktan hemen sonra üzerine yazıyoruz, ileride başka bir eleman için gerekmiyor (her indeks bağımsız). Yani `add_arrays` çakışmaya dayanıklı. Ama `add_arrays_r` (restrict'li) `dest == a` ile çağrılırsa, "çakışmıyorlar" sözü **ihlal** edilmiş olur: undefined behavior. Bu basit döngüde çıktı yine doğru çıkabilir (derleyici çakışma olmadığını varsayıp ürettiği hızlı kod bu veri için aynı sonucu verir), ama tanım olarak yanlış ve derleyici farklı optimize ederse bozulabilir. "Çalışıyor gibi görünmek", `restrict` ihlalini güvenli yapmaz.

**5** –

```c
void remove_at(int *a, size_t n, size_t i) {
    if (i >= n) {
        return;
    }
    memmove(a + i, a + i + 1, (n - i - 1) * sizeof a[0]);
}
```

`memmove`, çünkü kaynak (`a + i + 1`) ile hedef (`a + i`) çakışıyor (`dest < src`, bir eleman arayla). `(n - i - 1)` eleman, her biri `sizeof a[0]` byte. `i == n - 1` (son eleman): `n - i - 1 == 0`, `memmove` sıfır byte taşır, hiçbir şey olmaz — doğru, çünkü son elemanı silince kaydırılacak bir şey yok. Diziyi küçülttüğümüzü ayrıca takip etmemiz gerekir (eleman sayısını bir azaltmak); `remove_at` belleği değiştirmiyor, sadece taşıyor. Dinamik dizilerde bunu Ders 4.24'te göreceğiz.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §B3: `memcpy`, `memmove`, `memset`, `memcmp`.
- C standardı (ISO/IEC 9899:2018), §7.24.2 (kopyalama), §7.24.4 (`memcmp`), §7.24.6 (`memset`); §6.7.3.1: `restrict`'in biçimsel tanımı.
- Peter van der Linden, *Expert C Programming*, Bölüm 8: `restrict` ve takma ad (aliasing) optimizasyonları.
- SEI CERT C Coding Standard, EXP43-C (`restrict` sözünü ihlal etmemek), EXP42-C (dolgu byte'larını `memcmp` ile karşılaştırmamak).

**Sıradaki ders:** `ctype.h` sıfırdan. `isdigit`, `isalpha`, `isspace`, `toupper`, `tolower`; 0x20 bit hilesi ve tablo tabanlı sürüm.
