---
title: "4.4 Adres kavramı"
description: "& operatörü ve %p ile adresleri yazdırmak; adresi alınabilen ve alınamayan şeyler; yerel, global ve static değişkenlerin, fonksiyonların ve string sabitlerinin bellekte nerede durduğunu gösteren bir harita; stack'in aşağı doğru büyümesi, adreslerin her çalıştırmada değişmesi (ASLR) ve hizalama."
---

Ders 4.1'de `&scores[i]` ile array elemanlarının adreslerini yazdırdık ve "`&`'i Ders 4.4'te ayrıntılı göreceğiz" dedik. Aslında `&` ile çok daha önce tanışmıştık: Ders 2.13'te `scanf("%d", &value)`, Ders 3.8'de `__builtin_add_overflow(a, b, &sum)`, Ders 3.9'da `memcpy(bytes, &x, sizeof(x))`. Her seferinde "değişkenin yeri" demiştik. Bu derste o yerlere, yani **adreslere**, yakından bakıyoruz: neyin adresi alınabilir, adresler neye benzer, ve bir programın değişkenleri belleğin nerelerine dağılmış?

---

## 1. & operatörü

`&`, bir değişkenin önüne yazıldığında o değişkenin **adresini**, yani bellekteki ilk byte'ının numarasını verir:

```c
#include <stdio.h>

int main(void) {
    int local = 1;
    double ratio = 0.5;
    char letter = 'a';
    printf("local  %p\n", (void *)&local);
    printf("ratio  %p\n", (void *)&ratio);
    printf("letter %p\n", (void *)&letter);
    return 0;
}
```

```
local  0x16b886178
ratio  0x16b886170
letter 0x16b88616f
```

- `%p`, bir adresi yazdırır; adresler onaltılık (Ders 3.10) yazılır. Bilgisayarımızdaki `printf`, başına `0x` koyuyor.
- `(void *)`: `%p`, `void *` denen "herhangi bir şeyin adresi" tipini bekler. `&local`'ın tipi ise `int *`, "bir `int`'in adresi". Bu tipleri bir sonraki derste göreceğiz; şimdilik `%p` ile yazdırırken her adresi `(void *)`'e çevir.

Ders 3.18'deki `&` (bit bit VE) ile aynı işaret, ama hiçbir ilgisi yok. `a & b`'de iki tarafta değer var; `&local`'da sadece sağda. Compiler hangisi olduğunu bu farktan anlar.

### Adresin boyutu

Bir adresin kendisi de bir sayı, ve onun da bir boyutu var:

```c
printf("%zu %zu %zu\n", sizeof(&local), sizeof(&letter), sizeof(&ratio));
```

```
8 8 8
```

`char`'ın 1, `double`'ın 8 byte olmasına bakmadan, **hepsinin adresi 8 byte**. Bir adres, belleğin hangi byte'ı olduğunu söyleyen bir numara; o byte'ta ne olduğundan bağımsız. 8 byte = 64 bit, ve Ders 3.2'deki LP64 veri modelinin "P"si bu: **P**ointer 64 bit. 32 bitlik bir sistemde adresler 4 byte; Arduino'da 2.

Bir adresi bir tamsayı gibi kullanmak istersen Ders 3.4'teki `uintptr_t`'ye çevirebilirsin; Ders 4.3'te iki adres arasındaki uzaklığı bu yolla hesaplamıştık.

### Neyin adresi alınabilir?

Adresi olan şey, bellekte bir **yeri** olan şey. Bir değişkenin, bir array elemanının, bir struct alanının yeri var:

```c
&local
&scores[2]
&students[1].score
```

Bir hesabın sonucunun ya da bir sabitin ise yeri yok; işlemci onları register'larda tutup hemen kullanabilir:

```c
int *p = &(x + 1);
int *q = &5;
```

```
error: cannot take the address of an rvalue of type 'int'
error: cannot take the address of an rvalue of type 'int'
```

**rvalue**, atamanın sadece **sağında** (right) durabilen bir değer demek: `x + 1 = 3` yazamazsın. Atamanın solunda durabilen, yani bellekte bir yeri olan şeylere de **lvalue** denir. `&` sadece lvalue'lara uygulanabilir.

### Array'in adresi

Ders 4.1'de array'in adının ilk elemanının adresine dönüştüğünü gördük. Peki `&scores`?

```c
printf("%p %p %p\n", (void *)scores, (void *)&scores[0], (void *)&scores);
```

```
0x16da76160 0x16da76160 0x16da76160
```

Üçü de **aynı** sayı: array, ilk elemanının olduğu yerde başlıyor. Ama tipleri farklı. Ders 4.1'de LLDB'ye `p &scores` deseydik `(int (*)[5]) 0x…` görürdük: "5 elemanlı bir `int` array'inin adresi". `&scores[0]`'ın tipi ise `int *`, "bir `int`'in adresi". Aynı yeri gösteren iki farklı tip; Ders 4.6'da bu farkın neden önemli olduğunu göreceğiz.

---

## 2. Bir bellek haritası

Bir programdaki farklı türden şeylerin adreslerini yan yana koyalım: fonksiyonlar, bir string sabiti, global ve static değişkenler (Ders 2.7), `main`'in ve başka bir fonksiyonun yerel değişkenleri.

```c
#include <stdio.h>

int global_counter = 42;
int global_zero;
const int global_limit = 100;

void show(int parameter) {
    int inner = 7;
    printf("parameter (show)     %p\n", (void *)&parameter);
    printf("inner (show)         %p\n", (void *)&inner);
}

int main(void) {
    static int calls = 0;
    int local = 1;
    printf("main (fonksiyon)     %p\n", (void *)main);
    printf("show (fonksiyon)     %p\n", (void *)show);
    printf("\"merhaba\" (sabit)    %p\n", (void *)"merhaba");
    printf("global_limit         %p\n", (void *)&global_limit);
    printf("global_counter       %p\n", (void *)&global_counter);
    printf("calls (static)       %p\n", (void *)&calls);
    printf("global_zero          %p\n", (void *)&global_zero);
    printf("local                %p\n", (void *)&local);
    show(local);
    return 0;
}
```

- `main` ve `show`, `&` olmadan: bir fonksiyonun adı da, array'inki gibi, adresine dönüşüyor. Fonksiyonlar da bellekte duruyor; makine komutları olarak. Bu adreslerle neler yapılabildiğini Ders 4.11'de göreceğiz.
- `"merhaba"`: çift tırnaklı bir yazı, Ders 3.16'dan beri bildiğimiz gibi sonunda `'\0'` olan bir `char` array'i. O da bir yerde duruyor.

Sonuçları adrese göre küçükten büyüğe sıralayalım (bilgisayarımızda, `-O0` ile):

| Adres | Ne? | Bölge |
| --- | --- | --- |
| `0x1045785e8` | `show` fonksiyonu | **kod** (text) |
| `0x104578644` | `main` fonksiyonu | **kod** (text) |
| `0x104578820` | `global_limit` (`const`) | salt okunur veri |
| `0x1045788a1` | `"merhaba"` | salt okunur veri |
| `0x104580000` | `global_counter` (ilk değeri 42) | **veri** (data) |
| `0x104580004` | `calls` (`static`) | **veri** (data) |
| `0x104580008` | `global_zero` (ilk değeri yok) | **sıfırlanmış veri** (bss) |
| … | | (dev bir boşluk) |
| `0x16b886118` | `inner` (`show`'un yereli) | **stack** |
| `0x16b88611c` | `parameter` (`show`'un parametresi) | **stack** |
| `0x16b886178` | `local` (`main`'in yereli) | **stack** |

Çizersek:

```
yüksek adresler
  ┌──────────────────────────┐
  │ stack                    │  main'in frame'i: local         0x16b886178
  │   ↓ aşağı doğru büyür    │  show'un frame'i: parameter     0x16b88611c
  │                          │                   inner         0x16b886118
  ├──────────────────────────┤
  │                          │
  │    (kullanılmayan alan)  │
  │                          │
  ├──────────────────────────┤
  │ bss                      │  global_zero                    0x104580008
  │ data                     │  global_counter, calls          0x104580000
  │ salt okunur veri         │  "merhaba", global_limit        0x104578820
  │ kod                      │  main, show                     0x1045785e8
  └──────────────────────────┘
düşük adresler
```

Haritadan okunanlar:

**Kod en altta, onun hemen üstünde sabitler.** Fonksiyonların makine komutları ve değişmeyecek veriler (string sabitleri, `const` globaller) yan yana; işletim sistemi bu bölgeyi **salt okunur** olarak işaretler. Bir string sabitini değiştirmeye çalışmanın programı neden çökerttiğini Ders 4.12'de göreceğiz.

**Global ve static değişkenler aynı bölgede.** Ders 2.7'de `static` yerel değişkenin "stack'teki frame'de değil, global değişkenlerle aynı yerde" durduğunu söylemiştik: `calls`, `global_counter`'ın hemen yanında. İlk değeri olmayan globaller (`global_zero`) ayrı bir bölgede, **bss**'te; program başlarken bu bölgenin tamamı sıfırlanır. C standardı, ilk değeri verilmeyen global ve `static` değişkenlerin 0 ile başlayacağını garanti eder; yerel değişkenler için böyle bir garanti yoktur (Ders 2.12). Bu garantinin bedeli işte bu bölge. Dosyada bu bölge için 0'lardan oluşan bir blok tutmaya gerek yok; sadece boyutu yazılır.

**Stack çok yukarıda, ve aşağı doğru büyüyor.** `main` `show`'u çağırınca `show`'un frame'i (Ders 2.7'deki call stack) `main`'inkinin **altına**, daha küçük adreslere kuruldu. Çoğu işlemcide stack böyle büyür. Ders 4.1'deki taşma örneğinde `second`'ın `first`'ten 16 byte aşağıda olması da bununla ilgili.

**Arada dev bir boşluk.** `0x104580008` ile `0x16b886118` arası yaklaşık 1,7 GB; programın kendisi ise birkaç on KB. Ders 4.22'de program çalışırken bellek istediğimizde (`malloc`) gelen bellek bu boşluğun bir yerinden, **heap** denen bölgeden gelecek. Bütün bölgelerin ayrıntısını Ders 4.21'de göreceğiz.

---

## 3. Adresler her çalıştırmada değişir

Aynı programı bir kez daha çalıştıralım:

```
main (fonksiyon)     0x104438644
show (fonksiyon)     0x1044385e8
"merhaba" (sabit)    0x1044388a1
...
local                0x16d37a178
```

Bütün adresler **değişti**. Ama dikkatli bak: son üç onaltılık basamak (`644`, `5e8`, `8a1`, `178`) aynı. Her bölge bütünüyle, rastgele seçilmiş başka bir yere kaydırılmış; bölgenin içindeki düzen aynı kalmış.

Buna **ASLR** (address space layout randomization, adres alanı düzeninin rastgeleleştirilmesi) denir. Bugünkü bütün işletim sistemleri bunu yapar, ve sebebi Ders 4.1'deki güvenlik açıkları: bir saldırgan, bir tampon taşmasıyla programın akışını değiştirmek istiyorsa, belleğin neresinde ne olduğunu bilmek zorunda. Adresler her çalıştırmada değişirse bu çok zorlaşıyor.

Bunun bizim için sonucu: **bir adres, sadece programın o çalıştırması için anlamlıdır.** Bir adresi bir dosyaya yazıp programı yeniden başlatınca geri okumak işe yaramaz; o adreste artık başka bir şey var.

---

## 4. Hizalama

Bölüm 1'deki adreslerin son basamaklarına bak: `local` `…178`, `ratio` `…170`, `letter` `…16f`. Bir şey dikkat çekiyor:

```c
printf("%zu %zu\n", (size_t)&local % 4, (size_t)&ratio % 8);
```

```
0 0
```

4 byte'lık `int`'in adresi 4'ün, 8 byte'lık `double`'ınki 8'in katı. `char`'ınki ise tek bir sayı. Bu bir tesadüf değil: compiler her tipi, kendi boyutunun katı olan bir adrese yerleştiriyor. Buna **hizalama** (alignment) denir.

Sebebi donanımda. İşlemci belleği tek tek byte'larla değil, 4 ya da 8 byte'lık parçalarla okur. 8'in katında başlayan bir `double` tek bir okumayla gelir; iki parçanın sınırına denk gelen bir `double` iki okuma gerektirir. Bazı işlemciler hizalanmamış erişimi yavaş yapar, bazıları hiç yapmaz ve programı durdurur.

Ders 4.1'deki `struct Student`'ın 17 değil 20 byte olması da bu yüzden: `char group`'tan sonraki `int` array'inin 4'ün katında başlaması için compiler araya 3 byte **dolgu** (padding) koyuyor. Bunu, ve struct alanlarının sırasının boyutu nasıl değiştirdiğini Ders 4.26'da göreceğiz.

---

## 5. scanf'e neden & veriyoruz?

Ders 2.13'ten beri her `scanf`'te değişkenin önüne `&` koyduk ve "şimdilik kuralın bir parçası olarak kabul et" dedik. Artık nedenini söyleyebiliriz.

Ders 2.3'te gördüğümüz gibi bir fonksiyon, kendisine verilen değerin **kopyasıyla** çalışır. `scanf("%d", value)` yazsaydık `scanf`'e `value`'nun içindeki sayının bir kopyası gidecekti. `scanf` o kopyayı değiştirse bile, `main`'deki `value`'ya dokunamazdı; kopyanın nereden geldiğini bilmiyor.

`&value` yazınca ise `scanf`'e `value`'nun **adresi** gidiyor. Adresin kendisi de kopyalanıyor, ama adresin kopyası da **aynı yeri** gösteriyor. `scanf`, okuduğu sayıyı o adrese yazınca, `main`'in değişkeni değişiyor. Ders 4.1'de array'lerin fonksiyona verildiğinde neden değiştirilebildiğini görmüştük: fonksiyona ilk elemanın adresi gidiyordu. `&value`, aynı şeyi tek bir değişken için yapıyor.

`__builtin_add_overflow(a, b, &sum)` ve `memcpy(bytes, &x, sizeof(x))` da aynı mantıkla çalışıyor. Bir fonksiyonun, kendisine adresi verilen bir değişkeni nasıl okuyup yazdığını görmek için adresleri **tutabilen** bir tipe ihtiyacımız var: **pointer**. Ders 4.5'in konusu bu; ve Ders 4.7'de `scanf` gibi bir değişkenin içine yazan fonksiyonları kendimiz yazacağız.

---

## Alıştırmalar

**1** – Bölüm 2'deki programı kendi bilgisayarında iki kez çalıştır. Hangi adresler değişiyor? Bir bölgenin içindeki iki şeyin (örneğin `main` ile `show`) arasındaki fark değişiyor mu?

**2** – Bir fonksiyonun içinde `int a; int b; int c;` tanımlayıp üçünün adresini yazdır. Hangisi en yüksek adreste? Aynı programı `-O2` ile derleyince adresler nasıl değişiyor? (İpucu: compiler bu sırayı garanti etmez.)

**3** – Ders 2.8'deki özyinelemeli faktöriyel fonksiyonuna (`factorial(n)`) parametresinin adresini yazdıran bir satır ekle ve `factorial(5)`'i çağır. Adresler arasındaki fark ne? Bu, Ders 2.7'deki call stack çizimi hakkında ne söylüyor?

**4** – Hangileri derlenir? Derlenmeyenler için sebep ne?

```c
int x = 5;
int scores[3] = {1, 2, 3};
struct Point { int x; int y; } p = {1, 2};

&x
&scores
&scores[1]
&(scores[1] + 1)
&p
&p.y
&10
&main
```

**5** – Bölüm 2'deki haritada `global_counter`, `0x104580000`'da, yani `0x1000`'in (4.096'nın) tam bir katında başlıyor. Neden olabilir? (İpucu: işletim sistemi belleği hangi büyüklükteki parçalarla yönetir? Ders 4.21'de cevabını göreceğiz; şimdilik tahmin et.)

<details>
<summary>Cevaplar</summary>

**1** – Her çalıştırmada bütün adresler değişir (ASLR), ama aynı bölgedeki iki şeyin farkı değişmez: `main` − `show` her zaman aynı (bizde `0x5c` = 92 byte, `show`'un makine kodunun boyutu kadar). Kod, veri ve stack bölgeleri birbirinden **bağımsız** kaydırılıyor; bu yüzden örneğin `local` ile `main` arasındaki fark çalıştırmadan çalıştırmaya değişir.

**2** – Bilgisayarımızda ilk tanımlanan (`a`) en yüksek adreste çıktı, `b` ve `c` 4'er byte aşağıda; `-O2` ile de aynı sıra. Ama bu bir garanti değil: başka bir compiler ya da ayar sırayı değiştirebilir; hatta adresini almasaydın değişkenler bellekte hiç yer kaplamayıp sadece register'larda yaşayabilirdi. `&a`'yı yazdırmak, compiler'ı `a`'ya bellekte bir yer vermeye zorluyor. Değişkenlerin bellekteki sırasına hiçbir zaman güvenme; Ders 4.1'deki "komşu değişken" de bu yüzden güvenilir değildi.

**3** – Her çağrının `n`'i farklı bir adreste, ve adresler her çağrıda bir sabit kadar **küçülüyor** (bizde `-O0` ile 48 byte; tam değeri compiler'ın frame düzenine bağlı). Ders 2.7'de her çağrının stack'e kendi frame'ini eklediğini çizmiştik; burada o frame'lerin gerçekten art arda, aşağı doğru dizildiğini görüyorsun. Ve her çağrının kendi `n`'i var: aynı ad, beş farklı değişken.

**4** –

- `&x` ✓
- `&scores` ✓ (tipi "3 elemanlı `int` array'inin adresi")
- `&scores[1]` ✓
- `&(scores[1] + 1)` ✗: bir toplamanın sonucu, rvalue
- `&p` ✓
- `&p.y` ✓ (`.`, `&`'den önce uygulanır: `&(p.y)`)
- `&10` ✗: sabit, rvalue
- `&main` ✓: bir fonksiyonun adresi; `main` yazmakla aynı değeri verir

**5** – İşletim sistemi belleği **sayfa** (page) denen sabit büyüklükteki parçalarla yönetir; birçok sistemde 4 KB (4.096 byte), Apple Silicon'da 16 KB. Kod sayfaları salt okunur ve çalıştırılabilir, veri sayfaları yazılabilir olarak işaretlenir; bir sayfanın tamamının izinleri aynı olmak zorunda. Bu yüzden yazılabilir veri bölgesi, salt okunur bölgeden sonraki **ilk sayfa sınırında** başlıyor. `0x104580000`, 16 KB'ın (`0x4000`) da tam bir katı.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.1: pointer'lar ve adresler.
- C standardı (ISO/IEC 9899:2018), §6.5.3.2: `&` ve `*` operatörleri; §6.3.2.1: lvalue'lar.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §7.9 ve §9.7: bir programın bellekteki bölgeleri; §3.9.3: hizalama; §3.10.4: ASLR.

**Sıradaki ders:** Pointer. Bir adresi bir değişkende tutmak, ve o adresteki değeri `*` ile okuyup yazmak.
