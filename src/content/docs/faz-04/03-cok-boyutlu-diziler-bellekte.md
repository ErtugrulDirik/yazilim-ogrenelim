---
title: "4.3 Çok boyutlu diziler bellekte"
description: "İki boyutlu bir array'in bellekte satır satır, art arda durması (satır öncelikli düzen), eleman adresinin formülü, fonksiyona verirken sütun sayısının neden şart olduğu, tek boyutlu bir array'de tablo tutmak, matris toplama ve çarpma, ve döngülerin sırasının hıza etkisi."
---

Ders 2.4'teki labirent oyununun haritası `int map[7][11]` idi: 7 satır, 11 sütun, bir ızgara. Ders 4.1'de bellekteki her şeyin tek bir sıra halinde dizildiğini gördük: her byte'ın bir adresi var, ve adresler tek bir sayı. Peki **iki boyutlu** bir şey **tek boyutlu** bir belleğe nasıl sığıyor? Ders 4.1'in 2. alıştırmasında bir tahmin yapmıştın; bu derste cevabını görüyoruz.

---

## 1. Satır satır

3 satırlı, 4 sütunlu bir array'in her elemanının, ilk elemandan kaç byte uzakta olduğunu yazdıralım:

```c
#include <stdio.h>
#include <stdint.h>

#define ROWS 3
#define COLS 4

int main(void) {
    int m[ROWS][COLS] = {
        {1, 2, 3, 4},
        {5, 6, 7, 8},
        {9, 10, 11, 12},
    };
    uintptr_t base = (uintptr_t)&m[0][0];
    for (int i = 0; i < ROWS; i++) {
        for (int j = 0; j < COLS; j++) {
            printf("%3d ", (int)((uintptr_t)&m[i][j] - base));
        }
        printf("\n");
    }
    return 0;
}
```

Adresleri doğrudan yazdırmak yerine aralarındaki farkı yazdırıyoruz. Bunun için adresi Ders 3.4'teki `uintptr_t`'ye çevirdik: "bir adresi tamsayı olarak tutabilecek kadar büyük" tip. İki tamsayının farkı byte cinsinden uzaklık.

```
  0   4   8  12
 16  20  24  28
 32  36  40  44
```

Uzaklıklar 0'dan 44'e, 4'er 4'er, **hiç boşluksuz** artıyor. İlk satırın dört elemanı, hemen arkasından ikinci satırın dört elemanı, sonra üçüncü satır. Bellekte bir tablo yok; satırları uç uca eklenmiş tek bir uzun array var:

```
uzaklık:  0   4   8  12  16  20  24  28  32  36  40  44
değer:    1   2   3   4   5   6   7   8   9  10  11  12
          └─── m[0] ───┘ └─── m[1] ───┘ └─── m[2] ────┘
```

Bu düzene **satır öncelikli** (row-major) düzen denir. C, C++, Python'un NumPy'ı ve çoğu dil böyle yapar. Fortran, MATLAB ve R ise tersini, **sütun öncelikli** (column-major) düzeni kullanır: önce ilk sütunun elemanları, sonra ikinci sütunun. İki dil arasında matris alıp verirken bu fark sık bir hata kaynağı.

### Adres formülü

Ders 4.1'deki formülün iki boyutlu hali: `m[i][j]`'ye gelmek için önce `i` tane **bütün satırı** atlıyoruz, sonra o satırın içinde `j` eleman.

$$
\text{adres}(m[i][j]) = \text{adres}(m[0][0]) + (i \times \text{COLS} + j) \times \text{sizeof}(\text{eleman})
$$

`m[2][1]`: (2 × 4 + 1) × 4 = 36. Tablo da 36 diyor.

Formülde `ROWS` yok, `COLS` var. Satır sayısı, bir elemanın adresini hesaplamak için gerekmiyor; sütun sayısı ise **şart**: bir satırın kaç byte olduğunu o söylüyor. Bölüm 3'te bunun bir sonucunu göreceğiz.

`sizeof` da bu yapıyı gösteriyor:

| İfade | `sizeof` | |
| --- | --- | --- |
| `m` | 48 | 3 × 4 × 4: bütün array |
| `m[0]` | 16 | bir satır: 4 `int` |
| `m[0][0]` | 4 | bir `int` |

`m[0]`, kendi başına 4 elemanlı bir array. İki boyutlu bir array, aslında **array'lerden oluşan bir array**: `m`, her elemanı `int[4]` olan 3 elemanlı bir array. `m[i][j]` de "önce `m`'nin `i`. elemanını (bir satır) seç, sonra onun `j`. elemanını" demek.

### Ders 4.1'in 2. alıştırması

Labirent haritası `map[7][11]`. `map[0][10]`, ilk satırın son elemanı, uzaklık (0 × 11 + 10) × 4 = 40. Hemen arkasındaki `int`, uzaklık 44: (1 × 11 + 0) × 4. Yani **`map[1][0]`**, ikinci satırın ilk elemanı.

Bu, `m[0][4]` gibi bir şey yazınca sonucun genellikle `m[1][0]` çıkacağı anlamına geliyor:

```c
printf("%d\n", m[0][4]);
```

```
5
```

clang uyarıyor:

```
warning: array index 4 is past the end of the array (that has type 'int[4]') [-Warray-bounds]
```

`-fsanitize=undefined` de çalışırken yakalıyor: `runtime error: index 4 out of bounds for type 'int[4]'`. Bellekte orada gerçekten `m[1][0]` duruyor; ama standart için `m[0]` 4 elemanlı bir array, ve `m[0][4]` onun sınırının dışı. Ders 4.1'deki gibi undefined behavior. Bir sonraki satıra geçmek istiyorsan `m[1][0]` yaz.

---

## 2. Tek boyutlu bir array'de tablo tutmak

Formülü kendimiz uygularsak, iki boyutlu bir tabloyu **tek boyutlu** bir array'de tutabiliriz:

```c
#define ROWS 3
#define COLS 4

int grid[ROWS * COLS];

int get(const int g[], int i, int j) {
    return g[i * COLS + j];
}
```

`grid[i * COLS + j]`, bellekte tam olarak `m[i][j]` ile aynı yere denk geliyor; compiler'ın iki boyutlu array için yaptığı hesabı biz yapıyoruz. Neden böyle bir şey yapalım?

- **Bütün elemanları tek döngüyle gezmek.** Toplam, en büyük, sıfırlama gibi konumdan bağımsız işler için `for (int k = 0; k < ROWS * COLS; k++)` yeter. Ders 4.2'deki bütün fonksiyonlar, hiç değişmeden çalışır.
- **Boyutu program çalışırken belli olan tablolar.** Bir resmin genişliği ve yüksekliği dosyadan okunuyorsa, `int image[height][width]` yazabilmek için ikisini derlerken bilmen gerekir. Ders 4.22'de belleği program çalışırken ayırmayı öğrendiğimizde, tabloları hep böyle, tek boyutlu bir blok ve `i * width + j` formülüyle tutacağız. Resim dosyaları, ekran kartının belleği ve NumPy da tam olarak böyle çalışır.

---

## 3. Fonksiyona vermek

Ders 4.1'de bir array'i fonksiyona verince sadece ilk elemanın adresinin gittiğini gördük. İki boyutlu bir array için de aynısı: `m`'nin "ilk elemanı" ilk **satır**, ve fonksiyona o satırın adresi gidiyor. Fonksiyonun `m[i][j]`'yi hesaplayabilmesi için bir satırın ne kadar uzun olduğunu bilmesi gerekiyor:

```c
void mat_print(const int m[][COLS]) {
    for (int i = 0; i < ROWS; i++) {
        for (int j = 0; j < COLS; j++) {
            printf("%4d", m[i][j]);
        }
        printf("\n");
    }
}
```

İlk köşeli parantez boş kalabilir (satır sayısı formülde yok), ikincisi kalamaz:

```c
void f(int m[][]);
```

```
error: array has incomplete element type 'int[]'
```

Sütun sayısı **parametrenin tipinin bir parçası**. 3 sütunlu bir matris bekleyen bir fonksiyona 4 sütunluyu verirsen bu bir uyarı değil, hata:

```
error: incompatible pointer types passing 'int[3][4]' to parameter of type 'int (*)[3]' [-Wincompatible-pointer-types]
```

`int (*)[3]`, "3 elemanlı bir `int` array'inin adresi" demek; okumayı Ders 4.5'ten sonra öğreneceğiz. Bu kısıt, Bölüm 2'deki tek boyutlu yöntemin bir avantajı daha: `int g[]` alan bir fonksiyon her boyuttaki tabloyla çalışır, yeter ki boyutları da parametre olarak ver. (C99'da sütun sayısını bir parametre yapmanın bir yolu da var, `void f(int rows, int cols, int m[rows][cols])`, ama standart onu C11'de isteğe bağlı bir özellik yaptı.)

---

## 4. Matrisler

Bir matris, sayılardan oluşan bir tablo; iki boyutlu array'lerin en önemli kullanım alanı. Grafikteki döndürme ve büyütme, fizikteki denklem sistemleri, makine öğrenmesindeki sinir ağları, hepsi matris işlemleri. Faz 6'da matematiğine ayrıntılı bakacağız; şimdilik iki işlemi yazalım. Kare matrislerle, `N` × `N`:

```c
#define N 3
```

### Toplama

Aynı yerdeki elemanları topla:

```c
void mat_add(const int a[][N], const int b[][N], int result[][N]) {
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            result[i][j] = a[i][j] + b[i][j];
        }
    }
}
```

Sonuç ayrı bir array'e yazılıyor; Ders 4.1'e göre `result`, çağıranın array'inin kendisi.

### Çarpma

Matris çarpımı elemanları tek tek çarpmak **değil**. Sonucun `i`. satırının `j`. elemanı, `a`'nın `i`. **satırı** ile `b`'nin `j`. **sütununun** elemanlarının karşılıklı çarpımlarının toplamı:

$$
c_{ij} = \sum_{k=0}^{N-1} a_{ik} \, b_{kj}
$$

```c
void mat_mul(const int a[][N], const int b[][N], int result[][N]) {
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            int sum = 0;
            for (int k = 0; k < N; k++) {
                sum += a[i][k] * b[k][j];
            }
            result[i][j] = sum;
        }
    }
}
```

Üç iç içe döngü: her (`i`, `j`) için `k` boyunca bir toplam. Bir örnek:

```
    a           b
 1  2  0     2  0  1
 0  1  3     1  3  0
 4  0  1     0  1  2
```

`c[0][0]`'ı elle hesaplayalım; `a`'nın 0. satırı ile `b`'nin 0. sütunu:

| `k` | `a[0][k]` | `b[k][0]` | Çarpım | `sum` |
| --- | --- | --- | --- | --- |
| 0 | 1 | 2 | 2 | 2 |
| 1 | 2 | 1 | 2 | 4 |
| 2 | 0 | 0 | 0 | **4** |

Programın yazdığı `a × b` ve `b × a`:

```
  a × b          b × a
 4  6  1        6  4  1
 1  6  6        1  5  9
 8  1  6        8  1  5
```

**İki sonuç farklı.** Sayılarda 2 × 3 = 3 × 2, ama matrislerde `a × b` ile `b × a` genellikle eşit değil. Grafikte bunun anlamı: önce döndürüp sonra kaydırmak, önce kaydırıp sonra döndürmekle aynı yere varmaz.

Köşegeni 1, gerisi 0 olan matris, **birim matris**, sayılardaki 1 gibi: `a × I = a`. Programla denedik; sonuç `a`'nın kendisi.

Bir uyarı: `mat_mul(a, b, a)` gibi sonucu girdilerden birinin üzerine yazmak **yanlış** sonuç verir; `result[0][0]`'a yazınca, `a[0][0]` sonraki elemanları hesaplarken hâlâ gerekiyor. Sonuç her zaman ayrı bir array'e yazılmalı.

### Döngülerin sırası

`mat_mul`'daki üç döngünün sırasını değiştirmek matematiksel sonucu değiştirmez: hepsi aynı toplamları hesaplıyor. `k` döngüsünü ortaya alalım (`i`, `k`, `j` sırası), ve bunu `double`'larla, 1024 × 1024'lük matrislerle `-O2` ile ölçelim:

```c
for (int i = 0; i < N; i++) {
    for (int k = 0; k < N; k++) {
        double x = a[i][k];
        for (int j = 0; j < N; j++) {
            c[i][j] += x * b[k][j];
        }
    }
}
```

(`c` önceden sıfırlanmış olmalı.) Bilgisayarımızda:

| Döngü sırası | Süre |
| --- | --- |
| `i`, `j`, `k` (yukarıdaki `mat_mul`) | 1,25 saniye |
| `i`, `k`, `j` | **0,16 saniye** |

Aynı işlem, aynı sonuç, **yaklaşık 8 kat** hız farkı. Sebep, Bölüm 1'deki satır öncelikli düzen. En içteki döngüye bak:

- `i, j, k` sırasında en içteki döngü `b[k][j]`'yi `k` boyunca, yani **sütun sütun aşağı** okuyor. Her adımda bellekte bir satır, 1024 × 8 = 8 KB atlıyor.
- `i, k, j` sırasında en içteki döngü `b[k][j]` ve `c[i][j]`'yi `j` boyunca, yani bellekte **art arda** okuyor.

İşlemci belleği byte byte değil, 64 byte'lık bloklar halinde getirir ve yakın zamanda kullandığı blokları **cache** denen küçük, çok hızlı bir bellekte tutar. Art arda okunan veri, bir kez getirilen bloğun tamamını kullanıyor; 8 KB atlayarak okunan veri ise her eleman için yeni bir blok getiriyor. Ayrıca art arda erişim, compiler'ın birden çok elemanı aynı anda işleyen komutlar (SIMD) kullanmasına izin veriyor. İkisini de Faz 11'de ayrıntılı göreceğiz. Şimdilik kural: **iki boyutlu bir array'i gezerken en içteki döngü son indeksi değiştirsin.**

---

## Alıştırmalar

**1** – `double t[5][8]` array'inde `t[3][6]`, `t[0][0]`'dan kaç byte uzakta? Tablonun toplam boyutu ne? `t[2]`'nin `sizeof`'u?

**2** – `int cube[2][3][4]` üç boyutlu bir array. `sizeof(cube)`, `sizeof(cube[0])` ve `sizeof(cube[0][0])` ne? `cube[i][j][k]`'nin `cube[0][0][0]`'dan uzaklığının formülünü yaz. Bu formülde hangi boyut yok?

**3** – Bir `N × N` matrisin **devriğini** (transpose; satırlar sütun, sütunlar satır olur) `result`'a yazan `mat_transpose(const int a[][N], int result[][N])` yaz. Sonra aynı işi ikinci bir array kullanmadan, **yerinde** yapan `mat_transpose_in_place(int a[][N])` yaz. (İpucu: Ders 4.2'deki yerinde ters çevirmede olduğu gibi, her çifti bir kez değiştir. Hangi elemanlar çift oluşturuyor?)

**4** – Ders 2.4'teki labirent haritasını Bölüm 2'deki gibi tek boyutlu bir `int map[ROWS * COLS]` olarak tutsaydık, oyuncunun bir **sağdaki** ve bir **aşağıdaki** komşusunun indeksi ne olurdu? Oyuncu `index` numaralı karede. Sağdaki komşu için hangi durumda dikkat etmen gerekir?

**5** – Bölüm 4'teki `mat_mul`'u kullanarak bir matrisin karesini `mat_mul(a, a, r)` diye hesaplamak doğru mu? `mat_mul(a, a, a)`?

<details>
<summary>Cevaplar</summary>

**1** – (3 × 8 + 6) × 8 = 30 × 8 = **240 byte**. Toplam: 5 × 8 × 8 = **320**. `sizeof(t[2])` = 8 × 8 = **64**: bir satır.

**2** – `sizeof(cube)` = 2 × 3 × 4 × 4 = **96**, `sizeof(cube[0])` = 3 × 4 × 4 = **48** (bir 3 × 4 tablo), `sizeof(cube[0][0])` = 4 × 4 = **16** (bir satır). Uzaklık:

$$
(i \times 3 \times 4 + j \times 4 + k) \times \text{sizeof(int)}
$$

İlk boyut (2) formülde yok; fonksiyona verirken de `int cube[][3][4]` yazılır, ilk boyut dışındaki bütün boyutlar şart.

**3** –

```c
void mat_transpose(const int a[][N], int result[][N]) {
    for (int i = 0; i < N; i++) {
        for (int j = 0; j < N; j++) {
            result[j][i] = a[i][j];
        }
    }
}

void mat_transpose_in_place(int a[][N]) {
    for (int i = 0; i < N; i++) {
        for (int j = i + 1; j < N; j++) {
            int tmp = a[i][j];
            a[i][j] = a[j][i];
            a[j][i] = tmp;
        }
    }
}
```

`a[i][j]` ile `a[j][i]` bir çift; köşegenin (i = j) iki tarafında birbirinin aynası. `j`'yi `i + 1`'den başlatmak, her çifti **bir kez** değiştiriyor ve köşegene dokunmuyor. `j` 0'dan başlasaydı her çift iki kez değişir ve matris kendisine geri dönerdi.

**4** – Sağdaki komşu `index + 1`, aşağıdaki `index + COLS`. Sağdaki komşuya dikkat: oyuncu satırın **son** sütunundaysa (`index % COLS == COLS - 1`), `index + 1` bir sonraki satırın **ilk** karesi; Bölüm 1'deki `m[0][4]`'ün tek boyutlu hali. Bu sefer sınırın dışına çıkmıyoruz, ama oyuncu haritanın sağından çıkıp solundan girer. Ders 2.4'teki oyunda haritanın kenarları duvar olduğu için bu durum oluşmuyordu; duvar olmayan bir haritada kontrol şart.

**5** – `mat_mul(a, a, r)` **doğru**: girdiler sadece okunuyor, sonuç ayrı bir array'e yazılıyor; aynı array'in iki kez okunmasında sakınca yok. `mat_mul(a, a, a)` **yanlış**: `result[0][0]` yazılınca `a[0][0]` değişiyor, ve `result[0][1]`'i hesaplarken `a[0][0]`'ın **eski** değeri gerekiyor. Ders 4.7'de bu durumun adını ve Ders 4.18'de `memmove` ile nasıl ele alındığını göreceğiz.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.7: çok boyutlu array'ler.
- C standardı (ISO/IEC 9899:2018), §6.5.2.1¶3–4: çok boyutlu array'lere erişim ve satır öncelikli düzen.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §3.8.3: iç içe array'ler; §6.6: matris çarpımında döngü sırası ve cache.

**Sıradaki ders:** Adres kavramı. `&` operatörü, ve bir programın değişkenlerinin bellekte nerelere dağıldığını gösteren bir harita.
