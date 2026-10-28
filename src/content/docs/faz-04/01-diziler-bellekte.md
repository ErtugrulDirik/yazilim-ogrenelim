---
title: "4.1 Diziler bellekte"
description: "Ders 2.4'teki array'lerin bellekteki gerçek hali: elemanların adresleri, ardışık yerleşim ve adres formülü, LLDB ile belleği okumak, array'i fonksiyona verince neden kopyalanmadığı ve sizeof hilesinin neden çalışmadığı, sınır dışına yazmanın komşu değişkeni bozması ve AddressSanitizer."
---

Faz 2 ve 3 boyunca array'ler hakkında üç şeyi "Faz 4'te göreceğiz" diye bekletmiştik:

- Ders 2.4: Array'i fonksiyona verince **neden kopyalanmıyor**? Fonksiyon nasıl oluyor da asıl array'i değiştirebiliyor?
- Ders 3.1: `sizeof(scores) / sizeof(scores[0])` hilesi, fonksiyona verilen array'de neden **çalışmıyor**?
- Ders 2.4: Array'in dışına yazınca **tam olarak** ne oluyor?

Üçünün de cevabı, array'in bellekte nasıl durduğunda. Faz 4'e oradan başlıyoruz.

---

## 1. Her kutunun bir adresi var

Faz 0'da belleği numaralandırılmış kutulardan oluşan bir raf olarak düşünmüştük: her kutu bir byte, ve her byte'ın bir **numarası** var. Bu numaraya **adres** denir. Ders 3.9'da `memcpy(bytes, &x, sizeof(x))` yazarken `&x`'in "`x`'in bellekteki yeri" olduğunu söylemiştik; o yer, `x`'in ilk byte'ının adresi.

Bir array'in elemanlarının adreslerini yazdıralım:

```c
#include <stdio.h>

#define SIZE 5

int main(void) {
    int scores[SIZE] = {70, 85, 60, 90, 75};
    for (int i = 0; i < SIZE; i++) {
        printf("&scores[%d] = %p\n", i, (void *)&scores[i]);
    }
    return 0;
}
```

```
&scores[0] = 0x16f456160
&scores[1] = 0x16f456164
&scores[2] = 0x16f456168
&scores[3] = 0x16f45616c
&scores[4] = 0x16f456170
```

Bu satırdaki üç yeni parçayı şimdilik kısaca tanıyalım; hepsini Ders 4.4'te ayrıntılı göreceğiz:

- `&scores[i]`: "`scores[i]`'nin adresi".
- `%p`: bir adresi yazdırma biçimi. Adresler onaltılık (Ders 3.10) yazılır.
- `(void *)`: `%p`'nin beklediği tipe çeviren bir cast. Şimdilik kuralın bir parçası olarak kabul et.

Adreslerin kendisi büyük, anlamsız sayılar; programı her çalıştırışında da farklı çıkıyor (ikinci çalıştırmada `&scores[0]` `0x16d3d2160` oldu; sebebini Ders 4.4'te göreceğiz). Önemli olan aralarındaki **fark**:

| Eleman | Adres (son iki onaltılık basamak) | Bir öncekinden farkı |
| --- | --- | --- |
| `scores[0]` | `…60` | |
| `scores[1]` | `…64` | 4 |
| `scores[2]` | `…68` | 4 |
| `scores[3]` | `…6c` | 4 |
| `scores[4]` | `…70` | 4 |

Her eleman bir öncekinden tam **4 byte** sonra: `sizeof(int)` (Ders 3.1). Arada boşluk yok. Ders 2.4'teki "yan yana kutular" benzetmesi bir benzetme değilmiş: array, bellekte **art arda** duran elemanlar. 5 eleman × 4 byte = 20 byte, ve `sizeof(scores)` gerçekten 20.

Farklı tiplerle aynı deney:

| Array | Tipin boyutu | Ardışık adresler |
| --- | --- | --- |
| `char letters[4]` | 1 | `…0c`, `…0d`, `…0e`, `…0f` |
| `int scores[5]` | 4 | `…60`, `…64`, `…68`, … |
| `double prices[3]` | 8 | `…40`, `…48`, `…50` |
| `struct Student st[2]` | 20 | `…18`, `…2c` |

(`struct Student`, Ders 2.4'teki numara, şube ve üç notluk struct. `0x2c − 0x18` = 44 − 24 = 20, `sizeof(struct Student)`. Bir `int` ve bir `char` ve üç `int` toplamı 17 byte ediyor; aradaki 3 byte'ın nereden geldiğini Ders 4.26'da göreceğiz.)

Kural her tipte aynı:

$$
\text{adres}(a[i]) = \text{adres}(a[0]) + i \times \text{sizeof}(\text{eleman})
$$

Bu formül, array'in neden bu kadar hızlı olduğunu da açıklıyor: `scores[3]`'e ulaşmak için baştan saymaya gerek yok; işlemci tek bir çarpma ve toplamayla adresi hesaplayıp oraya gidiyor. Ders 3.5'teki godbolt çıktısında gördüğümüz `[rdi + 1]` tam olarak bu hesaptı. İndeksin 0'dan başlamasının sebebi de bu: ilk elemanın array'in başından uzaklığı **sıfır** eleman.

---

## 2. Belleğe LLDB ile bakmak

Ders 2.6'da LLDB'nin belleği doğrudan okuyabildiğini, ama bunu Faz 4'e bıraktığımızı söylemiştik. Şu programı `-g` ile derleyip `printf` satırında duralım:

```c
#include <stdio.h>

int main(void) {
    int scores[5] = {70, 85, 60, 90, 75};
    scores[2] = 65;
    printf("%d\n", scores[2]);
    return 0;
}
```

```
(lldb) memory read --size 4 --format d --count 5 &scores
0x16fdfdf40: 70
0x16fdfdf44: 85
0x16fdfdf48: 65
0x16fdfdf4c: 90
0x16fdfdf50: 75
```

`memory read`, verilen adresten başlayarak belleği okur. `--size 4` "4'er byte'lık birimler", `--format d` "onluk tamsayı olarak göster", `--count 5` "beş tane". Array'in beş elemanı, art arda dört byte'lık adreslerde.

Aynı belleği byte byte, onaltılık okuyalım:

```
(lldb) memory read --size 1 --format x --count 20 &scores
0x16fdfdf40: 0x46 0x00 0x00 0x00 0x55 0x00 0x00 0x00
0x16fdfdf48: 0x41 0x00 0x00 0x00 0x5a 0x00 0x00 0x00
0x16fdfdf50: 0x4b 0x00 0x00 0x00
```

`0x46` = 70, `0x55` = 85, `0x41` = 65… Her `int`'in dört byte'ı, Ders 3.9'daki **little endian** sırayla: en anlamsız byte başta. Bellek, Ders 3.18'deki hex dump'ın aynısı; bu sefer programa hiç kod eklemeden.

Bir de array'in **bittiği yerden** sonrasına bakalım:

```
(lldb) memory read --size 4 --format d --count 8 &scores
0x16fdfdf40: 70
0x16fdfdf44: 85
0x16fdfdf48: 65
0x16fdfdf4c: 90
0x16fdfdf50: 75
0x16fdfdf54: 1
0x16fdfdf58: -1860042696
0x16fdfdf5c: -1512679759
```

Son üç satır `scores`'a ait değil. Orada **başka şeyler** var; bellek, array'in sonunda bitmiyor. LLDB'ye "8 tane oku" dedik ve okudu: bellek, array'in kaç elemanlı olduğunu bilmiyor. Bölüm 4'te bu gerçeğin sonuçlarını göreceğiz.

---

## 3. Array'i fonksiyona vermek

Ders 2.4'teki `sum` fonksiyonuna bir satır ekleyip, fonksiyonun içinde array'in adresine ve boyutuna bakalım:

```c
#include <stdio.h>

#define SIZE 5

int sum(int numbers[], int size) {
    printf("sum içinde: numbers = %p, sizeof(numbers) = %zu\n",
           (void *)numbers, sizeof(numbers));
    int total = 0;
    for (int i = 0; i < size; i++) {
        total += numbers[i];
    }
    return total;
}

int main(void) {
    int scores[SIZE] = {70, 85, 60, 90, 75};
    printf("main içinde: scores = %p, sizeof(scores) = %zu\n",
           (void *)scores, sizeof(scores));
    printf("toplam %d\n", sum(scores, SIZE));
    return 0;
}
```

clang daha derlerken bir şeyden şüpheleniyor:

```
warning: sizeof on array function parameter will return size of 'int *' instead of 'int[]' [-Wsizeof-array-argument]
```

Çalıştıralım:

```
main içinde: scores = 0x16f456160, sizeof(scores) = 20
sum içinde: numbers = 0x16f456160, sizeof(numbers) = 8
toplam 380
```

İki şey çıktı:

**Adres aynı.** `main`'deki `scores` ile `sum`'daki `numbers` **aynı adreste** başlıyor. `sum`, bir kopya üzerinde değil, `main`'in array'inin kendisi üzerinde çalışıyor. Ders 2.4'teki `double_all`'ın asıl array'i değiştirebilmesinin sebebi bu.

**Boyut 8.** `sum`'ın içinde `numbers` 20 byte değil, **8 byte**. 8, Ders 3.2'deki tablonun son sütunu: bu bilgisayarda bir **adresin** boyutu. `sum`'a bir array verilmedi; array'in **ilk elemanının adresi** verildi.

C'nin kuralı şu: bir array'in adı, neredeyse her ifadede **ilk elemanının adresine** dönüşür. `sum(scores, SIZE)` yazınca aslında `sum(&scores[0], SIZE)` yazmış oluyoruz. `printf`'e `scores` verince adres yazdırması da bu yüzden. Bu dönüşüme İngilizcede *array decay* (array'in "bozulması") denir. Sadece iki istisna var: `sizeof(scores)` ve `&scores`; ikisinde de array, array olarak kalır.

Fonksiyonun parametresindeki `int numbers[]` da bir array değil; compiler onu "bir `int`'in adresi" olarak okur. Ders 4.5'te göreceğimiz gösterimle `int *numbers`. Ders 3.21'deki uyarıda `char text[]`'in `char *` diye görünmesinin sebebi buydu. Ve ilk elemanın adresinden, array'in kaç elemanlı olduğunu çıkarmanın hiçbir yolu yok: Ders 3.1'deki `sizeof` hilesinin fonksiyonun içinde çalışmaması, ve Ders 2.4'ten beri boyutu her zaman ayrı bir parametreyle vermemiz bu yüzden.

### Neden böyle?

C, 1970'lerde, belleğin ve işlemcinin çok kıt olduğu bir dünyada tasarlandı. Bir array'i fonksiyona her verişte kopyalamak, büyük array'lerde hem zaman hem bellek demek. Ders 2.1'deki C++ örneğini hatırla: bir fonksiyon çağrısında 10 milyon elemanlık bir vektörü yanlışlıkla kopyalamak. C bunu varsayılan olarak hiç yapmıyor; sadece 8 byte'lık bir adres veriyor.

Bir array'i gerçekten kopyalamak istersen, onu bir struct'ın içine koymak yetiyor. Struct'lar (Ders 2.3) **kopyalanır**:

```c
struct Scores {
    int values[5];
};

void double_all(struct Scores s) {
    for (int i = 0; i < 5; i++) {
        s.values[i] = s.values[i] * 2;
    }
}
```

`main`'deki `s.values[0]` 1 ise, `double_all(s)`'den sonra hâlâ 1. Fonksiyonun içindeki `s.values`'un adresi de farklı çıkıyor: kopyanın adresi. Ama array'in kendisiyle bu olmuyor; iki array'i atamayla bile kopyalayamazsın:

```c
int a[3] = {1, 2, 3};
int b[3];
b = a;
```

```
error: array type 'int[3]' is not assignable
```

Array'leri kopyalamak için ya bir döngü ya da Ders 3.9'daki `memcpy` gerekiyor (`memcpy`'yi Ders 4.18'de kendimiz yazacağız).

---

## 4. Sınırın dışına çıkmak

Ders 2.4'te "C array'in sınırını kontrol etmez" demiştik. Bölüm 2'de LLDB'nin array'in ötesini sorgusuz okuduğunu gördük. Bir program aynısını yaparsa ne olur?

```c
#include <stdio.h>

void fill(int numbers[], int count, int value) {
    for (int i = 0; i < count; i++) {
        numbers[i] = value;
    }
}

int main(void) {
    int first[4] = {1, 1, 1, 1};
    int second[4] = {2, 2, 2, 2};
    printf("first:  %p\nsecond: %p\n", (void *)first, (void *)second);
    fill(second, 6, 9);
    printf("first:  %d %d %d %d\n", first[0], first[1], first[2], first[3]);
    printf("second: %d %d %d %d\n", second[0], second[1], second[2], second[3]);
    return 0;
}
```

`fill`'e 4 elemanlık bir array'e **6** eleman yazmasını söyledik. `-O0` ile:

```
first:  0x16b372160
second: 0x16b372150
first:  9 9 1 1
second: 9 9 9 9
```

`second`'a hiç dokunmadığımız `first`'in ilk iki elemanı **9 oldu**. Adreslere bak: `second` `…150`'de başlıyor, 4 × 4 = 16 byte sonra, yani tam `…160`'ta `first` başlıyor. `second[4]` ve `second[5]` diye yazdığımız yerler, aslında `first[0]` ve `first[1]`.

```
adres:   …150  …154  …158  …15c  …160  …164  …168  …16c
         └──────── second ───────┘└──────── first ────────┘
indeks:  [0]   [1]   [2]   [3]   [4]?  [5]?
```

İşlemcinin bakış açısından burada bir hata yok: `numbers[i]`'yi Bölüm 1'deki formülle hesapladı ve oraya yazdı. Hangi adresin hangi değişkene ait olduğunu bilen tek şey compiler'dı, ve o da kontrol etmiyor.

Bu çıktı **garanti değil**. `first` ve `second`'ın bellekteki sırası, aralarındaki boşluk, hatta ikisinin bellekte olup olmadığı compiler'ın kararı. Aynı programı `-O2` ile derleyince:

```
first:  0x16f32a1d0
second: 0x16f32a1c0
zsh: segmentation fault  ./ob
```

Adresler yazıldı, ama sonuçlar hiç gelmedi. Ders 2.12'deki undefined behavior: compiler, `fill`'in 6 eleman yazacağını ve bunun doğru bir programda olamayacağını gördü, ve döngüyü **hiç bitmeyen** bir yazma döngüsüne çevirdi. Program bellekte, işletim sisteminin izin vermediği bir yere ulaşana kadar yazdı ve işletim sistemi onu durdurdu: **segmentation fault** (bellek bölümü hatası).

İki sonuç da kötü, ama ilki daha tehlikeli: program **çalışmaya devam etti** ve başka bir değişkeni sessizce bozdu. Bir array'in sınırının dışına yazabilen bir program, ona doğru girdiyi veren birinin bellekte istediği şeyi değiştirmesine izin verebilir. Ders 3.16'daki tampon taşması bunun bir haliydi; 1988'deki Morris solucanından bugüne, en çok istismar edilen güvenlik açıkları bu türden. Okumak da güvenli değil: 2014'teki Heartbleed açığı, bir sunucunun bir array'in sınırının ötesini **okuyup** karşı tarafa göndermesiydi; şifreler ve özel anahtarlar dahil.

### AddressSanitizer

Ders 2.12'deki `-fsanitize=address` tam olarak bu hatayı yakalamak için:

```
==1225==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x00016d3920b0 ...
WRITE of size 4 at 0x00016d3920b0 thread T0
    #0 0x000102a6c858 in fill ob.c:5
    #1 0x000102a6ca20 in main ob.c:13
...
  This frame has 2 object(s):
    [32, 48) 'first' (line 10)
    [64, 80) 'second' (line 11) <== Memory access at offset 80 overflows this variable
```

Raporu okuyalım:

- `stack-buffer-overflow`: stack'teki (Ders 2.7) bir array'in sınırı aşıldı.
- `WRITE of size 4`: 4 byte'lık bir yazma, yani bir `int`.
- `in fill ob.c:5`: hatayı yapan satır, `numbers[i] = value;`. Altındaki satır onu çağıran yer.
- `[64, 80) 'second'`: `second`, `main`'in frame'inde 64 ile 80 arasındaki byte'larda duruyor; erişim 80'de, yani tam sonunda.

ASan bunu nasıl biliyor? Her değişkenin etrafına, programın normalde kullanmadığı "yasak" byte'lar koyuyor ve her bellek erişiminden önce o adresin yasak olup olmadığına bakıyor. Raporda gördüğün `[32, 48)` ile `[64, 80)` arasındaki boşluk o yasak bölge. Bedeli, programın birkaç kat yavaşlaması; bu yüzden sadece testlerde kullanılıyor.

---

## Alıştırmalar

**1** – `short values[6]` array'inin ilk elemanının adresi `0x1000` ise `&values[4]` ne? `long long big[10]` için `&big[7]`? (Ders 3.2'deki boyutlar.) Programla kontrol et; adresler farklı çıkacak ama farklar aynı olmalı.

**2** – Ders 2.4'teki labirent haritası `int map[7][11]`'dı. `map[0][10]`'un hemen arkasındaki `int` hangisi? Bir tahmin yap; Ders 4.3'te doğru cevabı göreceğiz. (İpucu: `sizeof(map)` 308.)

**3** – Şu fonksiyon ne yazdırır? clang ne diyor?

```c
void show_count(int numbers[]) {
    printf("%zu\n", sizeof(numbers) / sizeof(numbers[0]));
}
```

`main`'de `int values[10]` ile çağırıyoruz.

**4** – Bölüm 4'teki programda `fill(second, 6, 9)` yerine `fill(first, 6, 9)` yazsaydık ne olurdu? Önce tahmin et, sonra `-O0` ile ve `-fsanitize=address` ile dene.

**5** – Bir array'in elemanlarını, sınırı aşmadan tersine yazdıran bir döngü:

```c
for (unsigned int i = SIZE - 1; i >= 0; i--) {
    printf("%d ", scores[i]);
}
```

Bu döngü neden sınırın dışına çıkar? (Ders 3.6.) ASan ne diyor? İki farklı düzeltme yaz.

<details>
<summary>Cevaplar</summary>

**1** – `short` 2 byte: `0x1000 + 4 × 2` = **`0x1008`**. `long long` 8 byte: `big` `0x1000`'de başlasaydı `0x1000 + 7 × 8` = 0x1000 + 56 = **`0x1038`** (56 = 0x38). Programda `&values[4]` ile `&values[0]`'ın farkı 8, `&big[7]` ile `&big[0]`'ınki 56 çıkmalı.

**2** – `map[1][0]`. 7 × 11 × 4 = 308 byte, yani 77 `int` art arda; iki boyutlu array'in satırları da yan yana duruyor. İlk satırın son elemanından sonra ikinci satırın ilk elemanı geliyor. Ders 4.3'te adres formülüyle göstereceğiz.

**3** – **2** yazar, 10 değil. `numbers` bir adres, 8 byte; `numbers[0]` bir `int`, 4 byte; 8 / 4 = 2. clang Bölüm 3'teki `-Wsizeof-array-argument` uyarısını verir. Boyutu her zaman ayrı bir parametre olarak ver.

**4** – `first` `…160`'ta, `second` ondan 16 byte **önce**. `first`'in arkasında `second` yok; arkasında başka bir şey var (Bölüm 2'deki LLDB çıktısındaki gibi). `-O0` ile sonuç tamamen o adreste ne olduğuna bağlı: program fark edilmeden devam edebilir, ya da `main`'in geri döneceği adres gibi önemli bir bilgiyi bozup sonunda çökebilir. ASan yine `stack-buffer-overflow` raporlar, bu sefer `'first'` için. Değişkenlerin stack'teki sırası compiler'a kalmış; bu yüzden "komşu değişken" hiçbir zaman güvenilir bir kavram değil.

**5** – `i` işaretsiz. `i` 0 iken `i--` yapınca 4.294.967.295 oluyor (Ders 3.3); `i >= 0` işaretsiz bir sayı için **her zaman** doğru, döngü hiç bitmiyor ve `scores[4294967295]`'e erişmeye çalışıyor: array'in 16 GB ötesi. ASan bu sefer `stack-buffer-overflow` değil, `SEGV on unknown address ... caused by a READ memory access` raporladı; adres o kadar uzak ki işletim sistemi daha ASan'ın kontrolüne gelmeden programı durdurdu. Şaşırtıcı biçimde clang `-Wall -Wextra` ile uyarı vermiyor; uyarıyı ayrıca açman gerekiyor: `-Wtautological-unsigned-zero-compare` ile `result of comparison of unsigned expression >= 0 is always true`. Düzeltmeler:

```c
for (int i = SIZE - 1; i >= 0; i--) {
    printf("%d ", scores[i]);
}
```

ya da işaretsiz kalarak, karşılaştırmayı azaltmadan önce yapmak:

```c
for (unsigned int i = SIZE; i > 0; i--) {
    printf("%d ", scores[i - 1]);
}
```

İkincisi, Ders 3.6'daki `size_t` ile çalışırken kullanılan yaygın kalıp.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.3: array'ler ve adresler.
- C standardı (ISO/IEC 9899:2018), §6.3.2.1¶3: array'in ilk elemanının adresine dönüşmesi ve istisnaları; §6.7.6.3¶7: array parametrelerin adres olarak okunması.
- Peter van der Linden, *Expert C Programming: Deep C Secrets* (1994), Bölüm 4 ve 9: array'ler ve pointer'lar ne zaman aynı, ne zaman değil.
- Konstantin Serebryany ve diğerleri, "AddressSanitizer: A Fast Address Sanity Checker", *USENIX ATC*, 2012.

**Sıradaki ders:** Dizi algoritmaları. Toplam, en büyük ve en küçük, ortalama ve yerinde ters çevirme; bu sefer kenar durumlarıyla ve tracing tablolarıyla.
