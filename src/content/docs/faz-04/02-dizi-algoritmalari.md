---
title: "4.2 Dizi algoritmaları"
description: "Array üzerinde temel algoritmalar, bu sefer kenar durumlarıyla: taşmayan toplam, boş array'de en büyük eleman, eşitlikler, kesirli ortalama, iki indeksle yerinde ters çevirme, üç ters çevirmeyle döndürme, sıralı mı kontrolü ve doğrusal arama; tracing tabloları ve döngü değişmezi."
---

Ders 2.4'te bir array'in toplamını, en büyüğünü ve tersini birkaç satırda bulmuştuk. O kodlar beş notluk bir array için çalışıyordu. Peki array **boşsa**? Bütün sayılar **negatifse**? Toplam `int`'e **sığmıyorsa**? İki eleman **eşitse** hangisi "en büyük"?

Bu derste aynı işleri, Faz 3'te öğrendiklerimizle, her girdi için doğru çalışacak şekilde yeniden yazacağız. Her fonksiyon array'i ve eleman sayısını alıyor (Ders 4.1'de neden ayrı olarak vermek zorunda olduğumuzu gördük), ve array'i değiştirmeyecekse parametresi `const` (Ders 3.21).

---

## 1. Toplam

```c
long long sum(const int a[], int n) {
    long long total = 0;
    for (int i = 0; i < n; i++) {
        total += a[i];
    }
    return total;
}
```

Ders 2.4'teki koddan tek farkı `total`'ın tipi. Üç tane `INT_MAX`'ı toplayalım: 6.442.450.941. `int` bir toplayıcıyla `-fsanitize=undefined` şunu diyor:

```
runtime error: signed integer overflow: 2147483647 + 2147483647 cannot be represented in type 'int'
```

`long long` (Ders 3.2) en az 64 bit; 32 bitlik `int`'lerden yaklaşık iki milyar tanesini taşmadan toplayabilir. Kural: bir toplamın tipi, toplanan elemanların tipinden **geniş** olmalı. Ders 3.14'teki `float` toplamaların `double` toplayıcıyla iyileşmesinin tamsayı hali.

`n` 0 ise döngü hiç dönmez ve sonuç 0; boş bir array'in toplamı matematikte de 0. Burada kenar durum kendiliğinden doğru çıkıyor.

---

## 2. En büyük eleman

Ders 2.4'teki kod `best = scores[0]` ile başlıyordu. Bu iki varsayım yapıyor: array'in en az bir elemanı var, ve bulduğumuz şey bir **değer**. Değer yerine **indeks** döndürmek daha kullanışlı (Ders 2.4'teki struct array'inde bunu yapmıştık), ve boş array için "yok" diyebilmemizi sağlıyor:

```c
int index_of_max(const int a[], int n) {
    if (n <= 0) {
        return -1;
    }
    int best = 0;
    for (int i = 1; i < n; i++) {
        if (a[i] > a[best]) {
            best = i;
        }
    }
    return best;
}
```

- Boş array'de −1: geçerli hiçbir indeks negatif olamaz, bu yüzden "bulunamadı" anlamına gelebilir. Ders 3.17'deki "rakam yok" durumu gibi, çağıranın bakması gereken bir sonuç. Ders 1.1'deki EnBüyük algoritması girdi için `n ≥ 1` şartı koyuyordu; burada o şartı fonksiyonun kendisi kontrol ediyor.
- `best`'in ilk değeri 0, yani ilk elemanın indeksi; EnBüyük'teki `enb ← a₁` gibi. "En büyük değer" için 0 sayısıyla başlamak cazip ama yanlış: `{-5, -2, -9}`'un en büyüğü 0 değil, −2.
- `>` kullanıyoruz, `>=` değil. İki eşit en büyük eleman varsa **ilkini** döndürüyoruz.

`{-5, -2, -9, -2}` için tracing:

| `i` | `a[i]` | `a[best]` | `a[i] > a[best]`? | `best` |
| --- | --- | --- | --- | --- |
| Başta | | | | 0 |
| 1 | −2 | −5 | evet | 1 |
| 2 | −9 | −2 | hayır | 1 |
| 3 | −2 | −2 | **hayır** (eşit) | 1 |

Sonuç 1. `>=` yazsaydık 3 olurdu, son −2.

### Döngü değişmezi

Bu fonksiyonun doğru olduğundan nasıl emin oluruz? Tablodaki her satırdan sonra doğru olan bir cümle var:

> Döngünün her turunun başında, `a[best]`, `a[0]` ile `a[i - 1]` arasındaki elemanların en büyüğüdür.

- **Başta** doğru: `i` = 1, ve `a[0]` tek başına kendi en büyüğü.
- **Her tur** doğruluğu korur: `a[i]`, o ana kadarki en büyükten büyükse yeni en büyük o olur; değilse eskisi kalır.
- **Döngü bitince** `i` = `n`, ve cümle "`a[best]`, bütün array'in en büyüğü" diyor.

Böyle bir cümleye **döngü değişmezi** (loop invariant) denir. Ders 1.3'teki tracing tablolarının arkasındaki fikir bu: tablonun her satırında doğru kalan bir şey bulursan, döngünün doğru olduğunu **kanıtlamış** olursun. Faz 9'da algoritmaların doğruluğunu bu yolla göstereceğiz.

En küçük eleman için tek fark `<`. 4. alıştırmada ikisini tek döngüde bulacaksın.

---

## 3. Ortalama

```c
double average(const int a[], int n) {
    return (double)sum(a, n) / n;
}
```

- `sum`'ın `long long` sonucu, bölmeden **önce** `double`'a çevriliyor. Ders 3.12'deki kural: bir taraf `double` olunca bölme de `double` ile yapılır. Cast olmasaydı tamsayı bölmesi yapılır ve küsurat atılırdı.
- `{-7, 0}`'ın ortalaması: tamsayı bölmesiyle −7 / 2 = **−3** (sıfıra doğru, Ders 3.11), `average` ile **−3,5**. Notların ortalaması için Ders 2.4'teki `total / SIZE` her zaman aşağıya, ama negatif sayılarda yukarıya yuvarlıyordu.
- Boş array: 0 / 0. Tamsayılarla bu undefined behavior olurdu (Ders 3.8). Burada `(double)0 / 0` = **NaN** (Ders 3.13); program çökmüyor, ama sonucu kullanan kodun `isnan` ile bakması gerekiyor. Ya da çağıran, boş array için `average`'ı hiç çağırmamalı.
- Kayan noktaya geçmeden önce toplamın `long long` olması önemli: Bölüm 1'deki üç `INT_MAX`'ın ortalaması `average` ile tam olarak **2147483647,0**.

---

## 4. Yerinde ters çevirme

Ders 2.4'te array'i "tersten yazdırmıştık". Array'in **kendisini** ters çevirmek için ikinci bir array gerekmiyor: iki uçtan başlayıp elemanların yerlerini değiştirerek ortada buluşmak yeter. Ders 3.16'daki `reverse`'ün `int` hali:

```c
void reverse(int a[], int n) {
    int i = 0;
    int j = n - 1;
    while (i < j) {
        int tmp = a[i];
        a[i] = a[j];
        a[j] = tmp;
        i++;
        j--;
    }
}
```

`a` burada `const` değil: fonksiyonun işi onu değiştirmek. Ders 4.1'e göre `main`'deki array'in kendisi değişiyor.

`{1, 2, 3, 4, 5}`:

| Adım | `i` | `j` | Yer değiştiren | Array |
| --- | --- | --- | --- | --- |
| Başta | 0 | 4 | | 1 2 3 4 5 |
| 1 | 0 → 1 | 4 → 3 | `a[0]` ↔ `a[4]` | 5 2 3 4 1 |
| 2 | 1 → 2 | 3 → 2 | `a[1]` ↔ `a[3]` | 5 4 3 2 1 |
| Bitti | 2 | 2 | | 5 4 3 2 1 |

Eleman sayısı tekken ortadaki eleman (`3`) yerinde kalıyor. Çiftken (`{1, …, 6}`) `i` ve `j` birbirini geçiyor: üç yer değiştirmeden sonra `i` = 3, `j` = 2. `n` 0 ise `j` = −1 ve döngü hiç dönmüyor; `n` 1 ise `i` = `j` = 0, yine dönmüyor. Kenar durumların hepsi `i < j` koşulunda.

**Bu bir yerinde (in-place) algoritma**: array'in kendisinden başka sadece iki indeks ve bir `tmp` kullanıyor, array ne kadar büyük olursa olsun. Ders 4.7'de üç satırlık yer değiştirmeyi bir `swap` fonksiyonuna taşıyacağız.

---

## 5. Döndürme

Bir array'i `k` adım sola **döndürmek**: ilk `k` eleman sona gider, gerisi başa kayar. `{1, 2, 3, 4, 5, 6, 7}`'yi 3 adım sola döndürünce `{4, 5, 6, 7, 1, 2, 3}`.

İlk akla gelen yol, bütün array'i bir adım kaydırmayı `k` kez tekrarlamak; `k` × `n` işlem. Ya da ikinci bir array'e kopyalamak; `n` elemanlık fazladan bellek. Jon Bentley'nin *Programming Pearls*'te anlattığı bir hile ikisinden de iyi: **üç ters çevirme**.

```c
void reverse_range(int a[], int from, int to) {
    while (from < to) {
        int tmp = a[from];
        a[from] = a[to];
        a[to] = tmp;
        from++;
        to--;
    }
}

void rotate_left(int a[], int n, int k) {
    if (n == 0) {
        return;
    }
    k = k % n;
    reverse_range(a, 0, k - 1);
    reverse_range(a, k, n - 1);
    reverse_range(a, 0, n - 1);
}
```

| Adım | Array |
| --- | --- |
| Başta (`k` = 3) | **1 2 3** 4 5 6 7 |
| İlk `k` elemanı ters çevir | **3 2 1** 4 5 6 7 |
| Kalanları ters çevir | 3 2 1 **7 6 5 4** |
| Hepsini ters çevir | **4 5 6 7 1 2 3** |

Neden çalışıyor? Array'i iki parça olarak düşün: A = `1 2 3`, B = `4 5 6 7`. İstediğimiz AB'den BA'ya geçmek. Bir parçanın tersini Aᴿ diye yazarsak, ilk iki adım AᴿBᴿ üretiyor; bütün bunun tersi de (AᴿBᴿ)ᴿ = BA. Bir cümlenin kelimelerini tersten yazıp sonra her kelimeyi kendi içinde düzeltmek gibi.

- `k = k % n`: 10 adım döndürmek, 7 elemanlı bir array'de 3 adım döndürmekle aynı. `k` 0 ise `reverse_range(a, 0, -1)` hiçbir şey yapmıyor, ve array değişmiyor.
- Her eleman en fazla iki kez yer değiştiriyor; fazladan bellek yok.

---

## 6. Sıralı mı, ve doğrusal arama

İki kısa fonksiyon daha; ikisi de array'i baştan sona bir kez geziyor ama **erken çıkabiliyor**:

```c
#include <stdbool.h>

bool is_sorted(const int a[], int n) {
    for (int i = 1; i < n; i++) {
        if (a[i - 1] > a[i]) {
            return false;
        }
    }
    return true;
}

int find(const int a[], int n, int value) {
    for (int i = 0; i < n; i++) {
        if (a[i] == value) {
            return i;
        }
    }
    return -1;
}
```

- `is_sorted`, yan yana her çifte bakıyor; sırayı bozan ilk çiftte `false`. `i` 1'den başladığı için `a[i - 1]` hiçbir zaman `a[-1]` olmuyor. Boş ve tek elemanlı array'ler sıralı sayılıyor: döngü dönmüyor ve `true` dönüyor. Matematiksel olarak da doğru: sırayı bozan bir çift yok.
- `find`, aranan değeri ilk gördüğü yerde indeksini döndürüyor; yoksa `index_of_max` gibi −1. Ders 2.10'daki ikili arama sadece **sıralı** array'lerde çalışıyordu; `find` her array'de çalışır ama en kötü durumda `n` elemanın hepsine bakar. Bu ikisinin farkını, algoritmaların hızını ölçmeyi öğrenince Faz 9'da göreceğiz.

---

## Özet

| Fonksiyon | Boş array'de | Dikkat edilen |
| --- | --- | --- |
| `sum` | 0 | Toplayıcı geniş bir tip |
| `index_of_max` | −1 | İlk değer `a[0]`, eşitlikte ilk indeks |
| `average` | NaN | Bölmeden önce `double`'a çevir |
| `reverse` | Değişmez | `i < j` koşulu tek ve çift sayıları ve boş array'i karşılıyor |
| `rotate_left` | Değişmez | `k % n` ve `n == 0` kontrolü |
| `is_sorted` | `true` | `a[i - 1]` için döngü 1'den başlıyor |
| `find` | −1 | Erken dönüş |

Bu fonksiyonları `-fsanitize=undefined,address` ile, boş, tek elemanlı, negatif, eşit ve `INT_MAX` içeren array'lerle denedik; rapor yok.

---

## Alıştırmalar

**1** – `{3, 8, 8, 1}` için `index_of_max`'ın tracing tablosunu çiz. Sonuç ne? `>` yerine `>=` olsaydı?

**2** – `rotate_left(a, 6, 2)`'nin üç adımını `{1, 2, 3, 4, 5, 6}` için yaz. Sonra `rotate_left`'i kullanarak bir array'i `k` adım **sağa** döndüren `rotate_right` yaz.

**3** – `sum`'ın döngü değişmezini yaz: döngünün her turunun başında `total` neye eşit? Döngü bitince bu cümle ne söylüyor?

**4** – En küçük ve en büyük elemanın indeksini **tek** döngüde bulan bir fonksiyon yaz. İki sonucu döndürmek için Ders 3.17'deki gibi bir struct kullan: `struct MinMax { int min_index; int max_index; };`. Boş array için ikisi de −1 olsun. (Ders 4.7'de iki sonucu struct'sız döndürmeyi göreceğiz.)

**5** – `{1, 2, 2, 3, 3, 3, 4}` gibi **sıralı** bir array'deki tekrarları, yerinde silen `int unique(int a[], int n)` yaz: array'in başına `{1, 2, 3, 4}` yazsın ve yeni eleman sayısını (4) döndürsün. Fazladan array kullanma. (İpucu: iki indeks; biri okumak, biri yazmak için.)

<details>
<summary>Cevaplar</summary>

**1** –

| `i` | `a[i]` | `a[best]` | `a[i] > a[best]`? | `best` |
| --- | --- | --- | --- | --- |
| Başta | | | | 0 |
| 1 | 8 | 3 | evet | 1 |
| 2 | 8 | 8 | hayır | 1 |
| 3 | 1 | 8 | hayır | 1 |

Sonuç **1**. `>=` ile 2. adımda `best` 2 olurdu: son 8'in indeksi.

**2** – `k` = 2:

| Adım | Array |
| --- | --- |
| Başta | **1 2** 3 4 5 6 |
| İlk 2 | **2 1** 3 4 5 6 |
| Kalan 4 | 2 1 **6 5 4 3** |
| Hepsi | **3 4 5 6 1 2** |

`k` adım sağa döndürmek, `n − k` adım sola döndürmekle aynı:

```c
void rotate_right(int a[], int n, int k) {
    if (n == 0) {
        return;
    }
    rotate_left(a, n, n - k % n);
}
```

`k % n` 0 ise `n − 0` = `n` adım sola döndürmek; `rotate_left`'in içindeki `k % n` bunu 0'a indiriyor.

**3** – "Döngünün her turunun başında `total`, `a[0]` ile `a[i − 1]` arasındaki elemanların toplamıdır." Başta `i` = 0 ve `total` = 0: hiç elemanın toplamı. Her tur `a[i]`'yi ekleyip `i`'yi artırarak cümleyi koruyor. Döngü bitince `i` = `n`: `total`, bütün elemanların toplamı.

**4** –

```c
struct MinMax {
    int min_index;
    int max_index;
};

struct MinMax min_max(const int a[], int n) {
    struct MinMax result = {-1, -1};
    if (n <= 0) {
        return result;
    }
    result.min_index = 0;
    result.max_index = 0;
    for (int i = 1; i < n; i++) {
        if (a[i] < a[result.min_index]) {
            result.min_index = i;
        }
        if (a[i] > a[result.max_index]) {
            result.max_index = i;
        }
    }
    return result;
}
```

İki ayrı döngünün yaptığı işi, array'i bir kez gezerek yapıyor.

**5** –

```c
int unique(int a[], int n) {
    if (n == 0) {
        return 0;
    }
    int write = 1;
    for (int read = 1; read < n; read++) {
        if (a[read] != a[write - 1]) {
            a[write] = a[read];
            write++;
        }
    }
    return write;
}
```

`write`, şimdiye kadar bulunan farklı eleman sayısı; `a[0]` ile `a[write - 1]` arası tekrarsız. Değişmez: "`a[0..write - 1]`, `a[0..read - 1]`'deki farklı değerlerin sıralı listesi." Yeni bir değer, en son yazılandan farklıysa yazılıyor; array sıralı olduğu için tekrarlar hep yan yana. `{1, 2, 2, 3, 3, 3, 4}` → `{1, 2, 3, 4, …}`, dönüş değeri **4**. Array'in geri kalanında eski değerler duruyor; çağıran sadece ilk 4 elemanı kullanmalı. C++'ın standart kütüphanesindeki `std::unique` da tam olarak böyle çalışır.

</details>

---

## Kaynaklar

- Jon Bentley, *Programming Pearls* (2. baskı), Sütun 2: döndürme ve üç ters çevirme hilesi; Sütun 4: döngü değişmezleri ile doğru program yazmak.
- Thomas Cormen ve diğerleri, *Introduction to Algorithms* (4. baskı), §2.1: döngü değişmezleri.
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §1.6: array'ler.

**Sıradaki ders:** Çok boyutlu diziler bellekte. Ders 2.4'teki labirent haritasının satırları bellekte nasıl diziliyor, ve matrisler nasıl çarpılır?
