---
title: "4.25 struct"
description: "İlgili verileri bir araya toplamak: struct tanımı, iç içe struct'lar, . ile üye erişimi, bir pointer üzerinden p->x (yani (*p).x), struct'ı fonksiyona değer ile vermenin kopya çıkarması ve bunun ölçülen maliyeti, pointer ile vermenin kopyadan kaçınması ve const kullanımı, struct atamasının alan alan kopya olması, struct döndürmek ve belirtilmiş başlatıcılar."
---

Ders 2.4'te `struct`'la tanıştık: ilgili değerleri tek bir "kutuda" toplamak, `struct Point player = {1, 1}` gibi. Ders 4.1'de bir `struct Student`'ın bellekte nasıl durduğunu, Ders 4.4'te neden 17 değil 20 byte olduğunu (dolgu) gördük. Ders 4.11'de `qsort`'un karşılaştırıcısında `x->score` yazdık ve "Ders 4.25'te ayrıntısıyla göreceğiz" dedik. Şimdi o ders: struct'ları fonksiyonlara vermek, `.` ile `->` farkı, ve değer ile pointer arasındaki seçim.

---

## 1. Tanım ve iç içe struct'lar

```c
struct Point {
    double x;
    double y;
};

struct Rect {
    struct Point top_left;
    struct Point bottom_right;
    const char *label;
};
```

Bir `struct`, farklı tiplerdeki değerleri (üyeleri) tek bir tip altında topluyor. Array'den farkı: array aynı tipten çok eleman, struct farklı tiplerden isimli üyeler. Bir struct, başka bir struct'ı üye olarak tutabiliyor (`Rect`'in içinde iki `Point`), ve bir pointer da (`label`).

```c
struct Point p = {1.0, 2.0};
printf("sizeof Point = %zu\n", sizeof(struct Point));   // 16
struct Rect box = { {0, 0}, {4, 3}, "kutu" };
printf("sizeof Rect = %zu\n", sizeof(struct Rect));     // 40
```

`sizeof(struct Point)` = 16: iki `double`, her biri 8 byte. `sizeof(struct Rect)` = 40: iki `Point` (32) + bir pointer (8). Üyeler bellekte, Ders 4.1'deki array gibi, sırayla ve ardışık duruyor (aralarda dolgu olabilir; Ders 4.26). İç içe başlatmada `{ {0,0}, {4,3}, "kutu" }` — her iç `{}` bir `Point`.

---

## 2. Üyeye erişim: `.` ve `->`

Elinde bir struct **değeri** varsa, üyeye nokta ile erişiyorsun (Ders 2.4):

```c
box.label           // Rect'in label'i
box.top_left.x      // icindeki Point'in x'i
```

Elinde struct'ı gösteren bir **pointer** varsa, önce dereference edip (Ders 4.5) sonra üyeye bakman gerekir: `(*p).x`. Ama bu o kadar sık ki, C'nin bir kısayolu var: `p->x`.

```c
struct Node n = {7};
struct Node *p = &n;
printf("%d %d %d\n", n.value, (*p).value, p->value);
```

```
7 7 7
```

`p->value`, `(*p).value`'nun **tam olarak** aynısı: "p'nin gösterdiği struct'ın `value` üyesi". Parantezler olmadan `*p.value` yazmak yanlış olurdu, çünkü `.` `*`'tan önce bağlanır (`*(p.value)` diye okunur); `->` bu karışıklığı ortadan kaldırıyor. Ders 4.11'deki `x->score`, Ders 4.24'teki `v->count` hep buydu.

Kural basit: **nokta değer için, ok pointer için.** `s.x` ya da `ptr->x`.

---

## 3. Fonksiyona vermek: değer mi, pointer mi?

Ders 2.3'teki temel kural: bir fonksiyon, kendisine verilen değerin **kopyasıyla** çalışır. Struct'lar için de geçerli — ve burada bir seçim doğuruyor.

### Değer ile: kopya çıkar

```c
double area(struct Rect r) {
    double w = r.bottom_right.x - r.top_left.x;
    double h = r.bottom_right.y - r.top_left.y;
    return w * h;
}
```

`area(box)` çağrıldığında, `box`'ın **tamamı** (40 byte) `r`'ye kopyalanıyor. Fonksiyon içinde `r`'yi değiştirmek `box`'ı etkilemez. Küçük struct'lar için bu ucuz ve temiz: `area` `box`'ı yanlışlıkla bozamaz.

Array'lerin aksine (Ders 4.1: array fonksiyona verilince kopyalanmaz, pointer'a dönüşür), struct'lar fonksiyona verilince **kopyalanır**. C'de struct, bir bütün olarak taşınan bir değer; array ise öyle değil. Bu, dilin en önemli tutarsızlıklarından biri: bir array'i kopyalamak için bir struct'ın içine koymak eski bir numaradır (Ders 4.1'deki `struct`'a sarılı array).

### Pointer ile: kopyadan kaçın, ya da değiştir

```c
void move_by(struct Rect *r, double dx, double dy) {
    r->top_left.x += dx;
    r->top_left.y += dy;
    r->bottom_right.x += dx;
    r->bottom_right.y += dy;
}
```

`move_by(&box, 10, 10)` — `box`'ın **adresini** veriyoruz (Ders 4.7'deki çıkış parametresi). Fonksiyon `box`'ın kendisini değiştiriyor, kopyasını değil. Değiştirmek istiyorsan pointer **zorunlu**.

Değiştirmesen bile, **büyük** struct'larda pointer kopyadan kaçınmak için tercih edilir. 512 byte'lık bir struct'ı 50 milyon kez bir fonksiyona verelim:

```
sizeof Big = 512
deger ile:   0.0721 s
pointer ile: 0.0450 s
```

Değer ile her çağrı 512 byte kopyalıyor; pointer ile sadece 8 byte'lık bir adres. Fark ~%60. Büyük struct'ları okumak için bile `const` pointer kullanmak bu yüzden yaygın:

```c
struct Point midpoint(const struct Rect *r) {
    struct Point m;
    m.x = (r->top_left.x + r->bottom_right.x) / 2;
    m.y = (r->top_left.y + r->bottom_right.y) / 2;
    return m;
}
```

`const struct Rect *r` (Ders 4.8): "bu struct'ı okuyacağım, kopyalamadan, ama değiştirmeyeceğim". Hem kopya maliyeti yok, hem imza fonksiyonun struct'ı bozmayacağını söylüyor. Standart kütüphane ve çoğu C API'si büyük struct'ları hep `const T *` olarak alır.

| | değer (`struct Rect r`) | pointer (`struct Rect *r`) |
| --- | --- | --- |
| kopya | tam kopya | sadece adres (8 byte) |
| çağıranı değiştirir mi? | hayır | evet (`const` değilse) |
| ne zaman | küçük, değiştirmeyeceğin struct'lar | büyük struct'lar, ya da değiştireceğin |
| üye erişimi | `r.x` | `r->x` |

Pratik kural: değiştireceksen pointer (zorunlu); değiştirmeyeceksen, struct küçükse (birkaç alan) değer de olur, büyükse `const` pointer.

---

## 4. struct ataması ve döndürme

### Atama: alan alan kopya

```c
struct Rect copy = box;      // tum alanlar kopyalanir
copy.label = "kopya";
printf("box.label=%s copy.label=%s\n", box.label, copy.label);
```

```
box.label=kutu copy.label=kopya
```

Ders 4.1'de "array'ler `b = a` ile kopyalanamaz" demiştik; struct'lar **kopyalanır**. `copy = box`, `box`'ın bütün üyelerini `copy`'ye kopyalıyor (Ders 4.18'deki `memcpy` gibi, ama derleyici yapıyor). İkisi ayrı; `copy.label`'ı değiştirmek `box`'ı etkilemiyor.

Bir uyarı: bu **sığ** (shallow) bir kopya. `label` bir pointer olduğu için, kopyada da **aynı** yazıyı gösterir (Ders 4.10'daki gibi iki pointer tek yazı); yazının kendisi kopyalanmaz. Struct bir `malloc`'lu pointer tutuyorsa (Ders 4.22), `copy = box` iki struct'ı aynı bloğa bağlar — ikisini de `free` etmek double free olur (Ders 4.23). Derin kopya gerekirse elle yapılır.

### Döndürme

`midpoint`, bir `struct Point` **döndürüyor**. Ders 4.7'deki "yerel değişkenin adresini döndürme" kuralı burada **geçerli değil**: adresini değil, **değerini** döndürüyoruz. `m` kopyalanarak çağırana gidiyor (Ders 4.7'deki `return` değeri gibi), `m`'nin kendisi yok olsa da kopyası güvende. Küçük struct'ları döndürmek temiz ve yaygın; Ders 2.13 ve 3.17'deki `struct ReadResult`, `struct ParseResult` hep böyleydi — birden fazla değeri tek `return`'de taşımanın yolu.

---

## 5. Belirtilmiş başlatıcılar

Bir struct'ı başlatırken üyeleri **adıyla** verebilirsin (C99'dan beri):

```c
struct Point q = {.y = 5};        // x belirtilmedi -> 0
struct Rect r = {
    .label = "kutu",
    .bottom_right = {4, 3},
    .top_left = {0, 0},
};
```

```
q = (0, 5)
```

Avantajları:

- **Sıra önemsiz**: `.label`'ı önce yazabilirsin.
- **Belirtilmeyen üyeler sıfırlanır**: `q.x`, `.x` verilmediği için 0 (Ders 4.4'teki sıfır başlatma).
- **Okunabilir**: hangi değerin hangi üyeye gittiği açık; `{0, 0, 4, 3, "kutu"}` gibi sırasıyla yazmaktan çok daha az hataya açık, özellikle struct büyüdükçe.

`struct Point q = {0}` ise bütün üyeleri sıfırlar — bir struct'ı sıfırlamanın en kısa yolu (Ders 4.18'deki `memset(&q, 0, sizeof q)` yerine).

---

## Alıştırmalar

**1** – `struct Rect`'in `sizeof`'u neden 40? Üyeleri topla (2 × `Point` + pointer) ve Ders 4.1'deki ardışık yerleşimle doğrula. `label`'ı `struct`'ın başına alsan boyut değişir mi? (Dolgu; Ders 4.26'da tam cevap.)

**2** – `move_by`'ı değer alan bir sürüme çevir (`struct Rect move_by(struct Rect r, ...)`), taşınmış **yeni** bir `Rect` döndürsün. Çağrı nasıl değişir? Hangi sürüm orijinali korur, hangisi değiştirir? İkisinin de yeri var mı?

**3** – `p->x` ile `(*p).x`'in aynı olduğunu, bir `struct Point *p` için ikisini de yazdırarak göster. `*p.x` neden derlenmez? (`.`'nın `*`'tan önce bağlanması.)

**4** – Bir `struct Rect` içinde `char *label` yerine `char label[16]` olsaydı, `copy = box` atamasında `label` nasıl kopyalanırdı — Bölüm 4'teki sığ kopya sorunu kalır mıydı? İki durumu (`char *` vs `char[16]`) Ders 4.10'daki `list` vs `grid` farkıyla ilişkilendir.

**5** – `struct Rect`'i heap'te ayıran `struct Rect *rect_new(struct Point tl, struct Point br, const char *label)` yaz (Ders 4.22). `label`'ı nasıl saklarsın — pointer'ı olduğu gibi mi, yoksa `strdup` (Ders 4.22) ile kopyalayarak mı? İkisinin sahiplik (ownership; Ders 4.22) açısından farkı ne?

<details>
<summary>Cevaplar</summary>

**1** – `struct Rect` = iki `struct Point` (her biri 16: iki `double`) + bir `const char *` (8) = 32 + 8 = 40. Bu struct'ta dolgu yok, çünkü hepsi 8 byte hizalı tiplerden (double ve pointer) oluşuyor; üyeler `0, 8, 16, 24, 32` ofsetlerinde ardışık. `label`'ı başa alsan (`const char *label; struct Point tl; struct Point br;`) boyut yine 40: tüm üyeler zaten 8'in katı, sıra değişse de dolgu gerekmez. Dolgunun boyutu değiştirdiği durumları (farklı boyutlu üyeler karışınca) Ders 4.26'da göreceğiz.

**2** –

```c
struct Rect move_by(struct Rect r, double dx, double dy) {
    r.top_left.x += dx;      r.top_left.y += dy;
    r.bottom_right.x += dx;  r.bottom_right.y += dy;
    return r;
}
```

Çağrı `box = move_by(box, 10, 10);` (sonucu geri atamak gerekir) ya da `struct Rect moved = move_by(box, 10, 10);` (orijinali korumak için). Değer alan sürüm orijinali **korur** (kopya üzerinde çalışıp yenisini döndürür); pointer alan sürüm (`move_by(&box, ...)`) orijinali **değiştirir**. İkisinin de yeri var: değişmez (immutable) bir tasarımda yeni değer döndürmek tercih edilir (zincirlenebilir, yan etkisiz), performans ya da yerinde değişiklik gerekirse pointer. Küçük struct'larda değer sürümü temiz; `Rect` 40 byte, kopya ucuz.

**3** –

```c
struct Point pt = {3, 4};
struct Point *p = &pt;
printf("%g %g\n", p->x, (*p).x);   // 3 3
```

İkisi de 3 yazar; `p->x` `(*p).x`'in kısaltması. `*p.x` derlenmez, çünkü `.` operatörü `*`'tan **önce** bağlanır: `*p.x`, `*(p.x)` diye okunur, ve `p` bir pointer olduğu için `p.x` (pointer'ın `x` üyesi) anlamsız — pointer'ın üyesi yok. Dereference'ı önce yaptırmak için `(*p).x` gerekir; `->` bunu tek adımda yapar.

**4** – `char label[16]` olsaydı, `copy = box` atamasında 16 byte'ın **tamamı** kopyalanırdı (array da struct'ın bir üyesi; struct kopyalanınca içindeki array de kopyalanır — Ders 4.1'deki "array'i struct'a sarınca kopyalanır" numarası). Sığ kopya sorunu **kalmaz**: iki struct'ın `label`'ı ayrı 16 byte, biri değişince diğeri etkilenmez. `char *` ise sadece pointer (8 byte) kopyalanır, gösterilen yazı paylaşılır — sığ. Bu tam Ders 4.10'daki fark: `char grid[][10]` (yazılar struct'ın içinde, kopyalanır) vs `char *list[]` (pointer'lar, gösterilenler paylaşılır). Array üye = veri içeride, pointer üye = veri dışarıda.

**5** –

```c
struct Rect *rect_new(struct Point tl, struct Point br, const char *label) {
    struct Rect *r = malloc(sizeof(struct Rect));
    if (r == NULL) {
        return NULL;
    }
    r->top_left = tl;
    r->bottom_right = br;
    r->label = strdup(label);   // kopya: struct kendi label'ina sahip
    if (r->label == NULL) {
        free(r);
        return NULL;
    }
    return r;
}
```

`label`'ı `strdup` ile **kopyalamak** daha güvenli: struct artık kendi yazısına sahip, çağıranın verdiği `label`'ın ömründen bağımsız. Pointer'ı olduğu gibi saklasaydık (`r->label = label`), çağıranın verdiği yazı bir yerel array ya da sonra `free` edilecek bir blok olsaydı, `r->label` sallanan pointer'a dönerdi (Ders 4.7, 4.23). `strdup` ile sahiplik netleşir: `rect_free` hem `r->label`'ı hem `r`'yi `free` eder. Maliyeti: her `Rect` bir ekstra ayırma, ve `rect_free`'nin iki `free` yapması gerekir. Sahiplik kuralı Ders 4.22'deki gibi: bir struct, içinde tuttuğu `malloc`'lu belleğin sahibiyse, onu temizlemekten de sorumludur.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), Bölüm 6: struct'lar, `->`, struct'ları fonksiyonlara vermek.
- C standardı (ISO/IEC 9899:2018), §6.7.2.1 (struct bildirimi), §6.5.2.3 (`.` ve `->`), §6.7.9 (belirtilmiş başlatıcılar).
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §3.9.1: struct'ların bellek düzeni.

**Sıradaki ders:** Hizalama ve dolgu. `offsetof`, `alignof`, ve üye sırasının struct boyutuna etkisi.
