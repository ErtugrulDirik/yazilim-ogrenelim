---
title: "4.24 Dinamik dizi"
description: "Çalışırken büyüyen bir dizi: data/count/capacity üçlüsü, dolunca kapasiteyi ikiye katlayıp realloc ile taşımak, neden birer birer büyütmenin O(n²) olduğu, ikiye katlamanın toplam kopyalamayı ~n'de tutması ve amortize edilmiş O(1) ekleme, geometrik serinin ispatı, ve ikiye katlama ile 1,5 kat büyümenin bellek-hız dengesi."
---

Ders 2.4'ten beri array'lerin boyutu sabitti; Ders 4.22'de `malloc` ve `realloc` ile çalışırken bellek istemeyi öğrendik. Şimdi ikisini birleştiriyoruz: **büyüyen bir dizi**. Kaç eleman geleceğini baştan bilmeden, eleman ekledikçe kendiliğinden büyüyen bir yapı. Python'un `list`'i, C++'ın `vector`'ü, Go'nun `slice`'ı hep bu; adı "dinamik dizi" ya da "büyüyen dizi" (dynamic/growable array).

Yapı basit, ama içinde güzel bir fikir var: diziyi **her eklemede değil**, dolunca ve **ikiye katlayarak** büyütmek. Bu seçimin neden $O(n)$ değil amortize edilmiş $O(1)$ verdiğini göreceğiz.

---

## 1. Üç alan: data, count, capacity

Bir dinamik dizi üç şey tutuyor:

```c
typedef struct {
    int *data;        // heap'teki blok (Ders 4.22)
    size_t count;     // su an kac eleman var
    size_t capacity;  // kac elemanlik yer ayrildi
} Vector;
```

Ayrımın kalbi `count` ile `capacity` arasındaki fark (Ders 4.14'teki `strlen` ile tampon boyutu ayrımının aynısı):

- **`count`**: dizide kaç eleman olduğu.
- **`capacity`**: kaç elemana yetecek bellek ayrıldığı.

`capacity >= count` her zaman. Aradaki boşluk, yeniden `realloc` çağırmadan eklenebilecek eleman sayısı. Fikir: biraz **fazla** yer ayır, böylece her ekleme bir `realloc` gerektirmesin.

```c
void vec_init(Vector *v) {
    v->data = NULL;
    v->count = 0;
    v->capacity = 0;
}
```

Başta hiç bellek yok; `NULL`'dan başlıyoruz, çünkü `realloc(NULL, ...)` `malloc` gibi davranıyor (Ders 4.22).

---

## 2. Ekleme: dolunca ikiye katla

```c
int vec_push(Vector *v, int value) {
    if (v->count == v->capacity) {
        size_t new_cap = (v->capacity == 0) ? 1 : v->capacity * 2;
        int *new_data = realloc(v->data, new_cap * sizeof(int));
        if (new_data == NULL) {
            return 0;   // basarisiz; eski data korundu (Ders 4.22)
        }
        v->data = new_data;
        v->capacity = new_cap;
    }
    v->data[v->count++] = value;
    return 1;
}
```

Ekleme iki durumda:

- **Yer varsa** (`count < capacity`): sadece yaz, `count`'u artır. Tek bir işlem — hızlı yol, çoğu çağrı bu.
- **Doluysa** (`count == capacity`): önce kapasiteyi **ikiye katla**, `realloc` ile bloğu büyüt (Ders 4.22'de gördüğümüz gibi taşınabilir), sonra yaz. İlk eklemede kapasite 0'dan 1'e.

`realloc`'u Ders 4.22'deki kurala uyarak ara bir değişkenle (`new_data`) çağırıyoruz: başarısız olursa eski `data` korunuyor, sızıntı olmuyor. Ekleyip serbest bırakırken Ders 4.23'teki alışkanlık:

```c
void vec_free(Vector *v) {
    free(v->data);
    v->data = NULL;
    v->count = 0;
    v->capacity = 0;
}
```

Kapasitenin eklendikçe nasıl büyüdüğünü izleyelim:

```
count=1 -> capacity=1
count=2 -> capacity=2
count=3 -> capacity=4
count=5 -> capacity=8
count=9 -> capacity=16
...
count=524289 -> capacity=1048576
```

Her büyüme bir öncekinin iki katı: 1, 2, 4, 8, 16, …, 2²⁰. Bir milyon eleman eklemek sadece **20 kez** `realloc` çağırdı. Sonunda `capacity=1048576`, `count=1000000`: 48.576 elemanlık boş yer var — ikiye katlamanın bedeli bu, en fazla iki katı belleğe kadar.

---

## 3. Neden ikiye katlama? Birer birer büyütmenin tuzağı

"Neden her eklemede tam bir eleman kadar büyütmüyoruz, boşa yer ayırmıyoruz?" Deneyelim: her `push`'ta `realloc(data, (count+1) * sizeof(int))`.

Sorun, Ders 4.15'teki Shlemiel'in bir başka yüzü. `realloc` bloğu büyütürken, yeni yere taşımak zorunda kalırsa mevcut `count` elemanın **hepsini** kopyalıyor (Ders 4.22). Her eklemede büyütürsen, her ekleme potansiyel olarak o ana kadarki her şeyi kopyalar: $0 + 1 + 2 + \dots + (n-1) = \frac{n(n-1)}{2}$, yani $O(n^2)$ kopyalama.

İki yaklaşımı ölçtük (kopyalama sayısı = taşınmada kopyalanabilecek eleman toplamı):

```
n=20000  ikiye-katla: 0.00006s kopya~32767      birer-birer: 0.00142s kopya~199990000
n=40000  ikiye-katla: 0.00006s kopya~65535      birer-birer: 0.00316s kopya~799980000
n=80000  ikiye-katla: 0.00012s kopya~131071     birer-birer: 0.00507s kopya~3199960000
```

- **İkiye katlama**: kopyalama $n$ ile orantılı (131071 ≈ 2 × 80000). $n$ iki katına çıkınca kopyalama da iki katına. $O(n)$ toplam.
- **Birer birer**: kopyalama $\frac{n^2}{2}$ ile orantılı (3,2 milyar ≈ 80000² / 2). $n$ iki katına çıkınca kopyalama **dört** katına. $O(n^2)$ toplam, ve süre de buna yakın (80 binde ~50 kat yavaş).

Birer birer büyütme, bir milyon eleman için yarım **trilyon** kopyalamaya çıkar; ikiye katlama bir milyonda kalır.

---

## 4. Amortize edilmiş O(1)

İkiye katlamada tek bir `push`'un maliyeti **değişken**: çoğu çağrı $O(1)$ (sadece yaz), ama ara sıra bir çağrı $O(n)$ (bütün diziyi kopyala). Yine de, $n$ eklemenin **toplam** maliyetini $n$'e bölünce sabit bir sayı çıkıyor. Buna **amortize edilmiş** (amortized) maliyet denir: tek tek pahalı olabilen işlemlerin ortalamaya yayılmış maliyeti.

İspat, bir geometrik seri. $n$ eleman eklerken kopyalamalar yalnızca büyüme anlarında olur, ve o anlarda kapasite $1, 2, 4, \dots$ idi. Toplam kopyalama:

$$1 + 2 + 4 + \dots + \frac{n}{2} = n - 1 < n$$

Geometrik serinin toplamı, son terimin **iki katından az**. Yani $n$ eleman eklerken toplam kopyalama $n$'den az; ekleme başına **ortalama birden az** kopyalama. Ölçümdeki `oran=1.05` tam bu: bir milyon eklemede eleman başına ortalama 1,05 kopyalama.

$$\text{amortize edilmiş maliyet} = \frac{\text{toplam iş}}{\text{işlem sayısı}} = \frac{O(n)}{n} = O(1)$$

Kilit nokta, kapasiteyi **çarpımsal** (× 2) büyütmek. Sabit bir miktar eklemek (birer birer, ya da her seferinde +100) her zaman $O(n^2)$ verir; sadece çarpımsal büyüme geometrik seriyi ve $O(1)$ amortismanı sağlar. Bir pahalı kopyalamanın maliyeti, ondan önceki o kadar ucuz eklemeye "yayılıyor". (Bu analizin biçimsel adı **toplu/muhasebe yöntemi**dir; Faz 8'de veri yapıları bağlamında tekrar göreceğiz.)

---

## 5. Büyüme çarpanı: 2 mi, 1,5 mi?

Çarpan 2 olmak zorunda değil; 1'den büyük herhangi bir sabit $O(1)$ amortismanı verir. Seçim bir **denge**:

- **× 2**: daha az `realloc` (daha az kopyalama), ama en fazla iki katı bellek israfı. En yaygın, en basit.
- **× 1,5**: daha sık büyüme (biraz daha çok kopyalama), ama daha az israf. Ayrıca ince bir avantajı var: ikiye katlamada yeni blok, serbest kalan eski blokların toplamından her zaman büyüktür, bu yüzden `malloc` onları tekrar kullanamaz; 1,5 kat ise bir süre sonra boşalan bloklara sığabilir, belleği daha iyi kullanabilir. (Bazı C++ `vector` uygulamaları bu yüzden 1,5 kullanır; diğerleri 2.)

İkisi de aynı $O(1)$ amortismanı veriyor; fark sabit katsayıda ve bellek kullanımında. Bu seride basitlik için 2 kullanıyoruz.

Bir uyarı (Ders 4.22'den): `new_cap * sizeof(int)` çarpımı çok büyük bir dizide taşabilir. Üretim kodunda bu çarpım kontrol edilir (ya da `calloc`'un yaptığı gibi; Ders 4.22). Ayrıca `capacity * 2` de teorik olarak `size_t`'yi taşırabilir, ama bunun için dizinin belleğin yarısını doldurması gerekir.

---

## Alıştırmalar

**1** – `vec_push`'ta ilk kapasiteyi 1 yerine 8 yapsan ne değişir? Küçük diziler için avantajı ne, dezavantajı ne? Çoğu gerçek uygulama neden 0'dan ilk eklemede küçük bir sabite (4, 8, 16) atlar?

**2** – `int vec_get(const Vector *v, size_t i, int *out)` ve `int vec_set(Vector *v, size_t i, int value)` yaz: `i >= count` ise 0 (başarısız) dönsün. Neden `capacity` değil `count` ile kontrol ediyorsun? `i`, `count` ile `capacity` arasındaysa orada ne var?

**3** – `vec_pop(Vector *v, int *out)`: son elemanı çıkar. `count`'u azaltmak yeterli mi, yoksa `realloc` ile küçültmeli mi? Dizi çok küçülürse (count, capacity'nin dörtte birine inerse) kapasiteyi yarıya indiren bir kural ekle — neden yarıya inince değil de dörtte bire inince küçültüyoruz (ipucu: sürekli ekle-çıkar yapılırsa ne olur)?

**4** – Bölüm 4'teki geometrik seri toplamının ($1 + 2 + \dots + n/2 = n - 1$) neden "son terimin iki katından az" olduğunu göster. Büyüme çarpanı 2 yerine 3 olsaydı, toplam kopyalama eleman başına ortalama kaç olurdu? (İpucu: $1 + 3 + 9 + \dots$)

**5** – `Vector`'ü `int` yerine **herhangi bir tip** tutacak şekilde genelleştir (Ders 4.9'daki `void *` fikri): `void *data`, `size_t elem_size`, ve `vec_push(Vector *v, const void *value)` içinde `memcpy` (Ders 4.18). Eleman adresini nasıl hesaplarsın? (Ders 4.1'deki adres formülü.)

<details>
<summary>Cevaplar</summary>

**1** – İlk kapasiteyi 8 yapmak, 8 elemana kadar hiç `realloc` yapmaz: küçük diziler için daha az ayırma, biraz daha hızlı. Dezavantajı: sadece 1-2 eleman tutacak çok sayıda küçük dizi varsa, her biri 8 elemanlık yer tutar — israf. 0'dan 1'e başlamak hiç israf etmez ama ilk birkaç eklemede sık `realloc` yapar. Çoğu uygulama ortayı seçer: ilk eklemede doğrudan 4, 8 ya da 16'ya atlar, çünkü "bir dizi oluşturuldu ama hiç kullanılmadı" durumunda bellek harcamaz (hâlâ `NULL`), ama kullanılmaya başlandığında ilk büyümeleri atlar. Denge, beklenen kullanım örüntüsüne bağlı.

**2** –

```c
int vec_get(const Vector *v, size_t i, int *out) {
    if (i >= v->count) {
        return 0;
    }
    *out = v->data[i];
    return 1;
}
int vec_set(Vector *v, size_t i, int value) {
    if (i >= v->count) {
        return 0;
    }
    v->data[i] = value;
    return 1;
}
```

`count` ile kontrol, çünkü **geçerli eleman** sayısı o. `count` ile `capacity` arasındaki indekslerde ayrılmış ama **başlatılmamış** bellek var (Ders 4.22'deki `malloc`'un çöp değerleri); orayı okumak çöp verir, yazmak ise `count`'u güncellemeden eklediğin için diziyi tutarsız bırakır. Kullanıcı sadece `[0, count)` aralığını görmeli.

**3** –

```c
int vec_pop(Vector *v, int *out) {
    if (v->count == 0) {
        return 0;
    }
    *out = v->data[--v->count];
    if (v->capacity > 4 && v->count <= v->capacity / 4) {
        size_t nc = v->capacity / 2;
        int *nd = realloc(v->data, nc * sizeof(int));
        if (nd != NULL) {
            v->data = nd;
            v->capacity = nc;
        }
    }
    return 1;
}
```

`count`'u azaltmak yeterli (eleman artık "yok"); `realloc` ile küçültmek zorunlu değil, sadece belleği geri vermek için. Küçültme eşiği neden ¼? Eğer kapasite tam dolunca büyütüp, bir eleman çıkınca hemen (½'de) küçültseydik, kapasite sınırında sürekli ekle-çıkar yapan bir kullanım her seferinde büyüt-küçült-büyüt-küçült yapar, her biri $O(n)$ kopyalama — amortisman bozulur. ¼'te küçültüp ½'ye inince, büyütme ve küçültme eşikleri arasında bir "tampon" kalır; art arda ekle-çıkar bu tampon içinde $O(1)$ kalır. Bu da bir amortisman argümanı.

**4** – $1 + 2 + 4 + \dots + 2^k$ toplamı $2^{k+1} - 1$, yani son terim $2^k$'nın iki katından (yani $2^{k+1}$'den) bir eksik — "iki katından az". (İkili tabanda: `111...1` = `1000...0` − 1.) Çarpan 3 olsaydı: $1 + 3 + 9 + \dots + 3^k = \frac{3^{k+1}-1}{2}$. Son terim $3^k = n$ civarıysa toplam $\approx \frac{3n}{2}$, eleman başına ortalama $\frac{3}{2} = 1{,}5$ kopyalama (çarpan 2'de bu ~1'di). Çarpan büyüdükçe kopyalama başına ortalama artıyor ama hep sabit kalıyor (çarpan $r$ için $\frac{r}{r-1}$); $O(1)$ bozulmuyor, sadece sabit değişiyor. Daha büyük çarpan = daha az `realloc` ama daha çok israf.

**5** –

```c
typedef struct {
    void *data;
    size_t count;
    size_t capacity;
    size_t elem_size;
} Vector;

int vec_push(Vector *v, const void *value) {
    if (v->count == v->capacity) {
        size_t nc = v->capacity ? v->capacity * 2 : 1;
        void *nd = realloc(v->data, nc * v->elem_size);
        if (nd == NULL) {
            return 0;
        }
        v->data = nd;
        v->capacity = nc;
    }
    unsigned char *slot = (unsigned char *)v->data + v->count * v->elem_size;
    memcpy(slot, value, v->elem_size);
    v->count++;
    return 1;
}
```

Eleman adresi, Ders 4.1'deki adres formülünün ta kendisi: `data + count * elem_size`. `void *` üzerinde aritmetik yapılamadığı için (Ders 4.9) önce `unsigned char *`'a çeviriyoruz; `unsigned char` 1 byte olduğu için `count * elem_size` tam byte ofseti verir. `memcpy` ile `elem_size` byte kopyalıyoruz — tipi bilmeden, Ders 4.9'daki `swap_any` gibi. `qsort`'un (Ders 4.11) ve bütün genel C koleksiyonlarının çalışma biçimi bu. Okuma da simetrik: `memcpy(out, slot, elem_size)`.

</details>

---

## Kaynaklar

- Thomas Cormen vd., *Introduction to Algorithms* (4. baskı), Bölüm 16: amortize analiz (toplu, muhasebe, potansiyel yöntemleri); tablo büyütme örneği.
- Jon Bentley, *Programming Pearls* (2. baskı), Bölüm 13–14: diziler ve büyüme.
- C standardı (ISO/IEC 9899:2018), §7.22.3.5: `realloc`.
- Andrei Alexandrescu, "std::vector growth factor" tartışmaları: 2 ile 1,5 arasındaki bellek-hız dengesi.

**Sıradaki ders:** `struct`. Tanım, `.` ve `->`, struct'ı fonksiyona değer ve pointer ile vermek.
