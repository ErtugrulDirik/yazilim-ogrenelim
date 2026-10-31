---
title: "6.2 Yüklemler mantığı"
description: "Yüklem ve evren, ∀ (her) ve ∃ (bazı) niceleyicileri, sonlu evrende ∀'nın erken çıkan döngü, ∃'nin tanık arayan döngü olması, niceleyicilerin olumsuzlanması (¬∀ ≡ ∃¬), boş evrende boş yere doğruluk, iç içe niceleyicilerde sıranın önemi, ve program koşullarını (sıralı dizi, ön koşul, son koşul) niceleyicilerle yazıp assert ile denetleme."
---

Ders 6.1'de "x > 3" cümlesinin önerme olmadığını söyledik: `x`'e bağlı. Ama matematikte ve programlamada cümlelerin çoğu böyle. "Dizinin her elemanı pozitif", "bu sayının 1'den ve kendisinden başka böleni yok", "her girdi için fonksiyon sonlanır". Bu cümleleri yazabilmek için önermeler mantığına iki şey ekliyoruz: **değişkenler** ve **niceleyiciler**.

---

## 1. Yüklem

**Yüklem** (predicate), değişken içeren ve değişkenlere değer verilince önermeye dönüşen bir ifade:

$$
P(x) : x > 3
$$

$P(5)$ doğru, $P(2)$ yanlış. $P$ tek başına ne doğru ne yanlış; bir **fonksiyon** gibi, girdisini bekliyor. C'de tam olarak bu:

```c
bool P(int x) { return x > 3; }
```

Yüklemler birden çok değişken alabilir: $Q(x, y) : x + y = 4$. $Q(1, 3)$ doğru, $Q(2, 3)$ yanlış.

Değişkenin hangi değerleri alabileceği önemli. Bu kümeye **evren** (domain of discourse) diyoruz. "$x^2 = 2$ olan bir $x$ var" cümlesi tamsayılar evreninde yanlış, gerçel sayılar evreninde doğru. Bir niceleyici yazdığında evreni de söylemelisin; C'de evren çoğunlukla bir dizi ya da bir aralık.

---

## 2. İki niceleyici

| Simge | Okunuşu | Anlamı |
| --- | --- | --- |
| $\forall x\, P(x)$ | her $x$ için $P(x)$ | evrendeki **bütün** değerler için doğru |
| $\exists x\, P(x)$ | bir $x$ vardır ki $P(x)$ | evrende **en az bir** değer için doğru |

Evren sonluysa, $\{a_1, \dots, a_n\}$, niceleyiciler önermeler mantığının uzun yazılışı:

$$
\forall x\, P(x) \equiv P(a_1) \land P(a_2) \land \dots \land P(a_n)
$$

$$
\exists x\, P(x) \equiv P(a_1) \lor P(a_2) \lor \dots \lor P(a_n)
$$

Bu da bize kodu veriyor. $\forall$, `&&` zinciri; ilk yanlışta durabilirsin. $\exists$, `||` zinciri; ilk doğruda durabilirsin. Ders 2.3'teki kısa devre değerlendirmesinin döngü hali:

```c
typedef bool (*pred_fn)(int x);

// forall i in [0, n): p(a[i])
static bool forall(const int *a, int n, pred_fn p) {
    for (int i = 0; i < n; i++) {
        if (!p(a[i])) return false;   // karsi ornek bulundu
    }
    return true;                      // karsi ornek yok (n == 0 ise de)
}

// exists i in [0, n): p(a[i])
static bool exists(const int *a, int n, pred_fn p) {
    for (int i = 0; i < n; i++) {
        if (p(a[i])) return true;     // tanik bulundu
    }
    return false;
}
```

`forall`'ın `false` döndürdüğü elemana **karşı örnek** (counterexample), `exists`'in `true` döndürdüğü elemana **tanık** (witness) diyoruz. Bu iki kelime kanıtlarda da aynı anlamla kullanılacak.

```c
int a[] = {4, 8, 15, 16, 23, 42};
forall(a, 6, is_positive)   // 1
forall(a, 6, is_even)       // 0   (karsi ornek: 15)
exists(a, 6, is_even)       // 1   (tanik: 4)
```

---

## 3. Boş evren

`n = 0` olunca ne oluyor?

```
bos dizi, hepsi pozitif mi: 1
bos dizi, pozitif var mi:   0
```

Boş evrende $\forall$ her zaman **doğru**, $\exists$ her zaman **yanlış**. İlki şaşırtıcı gelebilir ama Ders 6.1'deki "boş yere doğruluk": "boş dizinin her elemanı pozitif" cümlesini çürütmek için pozitif olmayan bir eleman göstermen gerekir; yok. Cebirsel olarak da tutarlı: boş bir `&&` zincirinin değeri `&&`'nin etkisiz elemanı (1), boş bir `||` zincirininki `||`'nin etkisiz elemanı (0). Tıpkı boş toplamın 0, boş çarpımın 1 olması gibi (Ders 6.10).

Kodda bu doğal olarak çıkıyor: `forall`'daki döngü hiç dönmüyor ve `true` dönüyor. Bu davranış doğru ve istenen; "boş dizi sıralı mı?" sorusunun cevabı evet olmalı.

---

## 4. Niceleyicileri olumsuzlamak

"Her öğrenci sınavı geçti" cümlesinin değili ne? "Hiçbir öğrenci geçmedi" **değil**; "**en az bir** öğrenci geçmedi".

$$
\neg \forall x\, P(x) \equiv \exists x\, \neg P(x)
$$

$$
\neg \exists x\, P(x) \equiv \forall x\, \neg P(x)
$$

Bunlar De Morgan yasalarının niceleyici hali: $\neg(P(a_1) \land \dots \land P(a_n)) \equiv \neg P(a_1) \lor \dots \lor \neg P(a_n)$. Kural mekanik: **$\neg$'yi niceleyicinin içinden geçir, niceleyici $\forall \leftrightarrow \exists$ değişsin.**

İç içe niceleyicilerde aynı kuralı adım adım uygularsın:

$$
\neg \forall x\, \exists y\, P(x, y) \equiv \exists x\, \neg \exists y\, P(x, y) \equiv \exists x\, \forall y\, \neg P(x, y)
$$

Kodda da aynı ilişki: `!forall(a, n, p)` ile "`!p` için `exists`" aynı sonucu verir. Bir fonksiyonu yazıp diğerini ondan türetebilirsin.

---

## 5. Sıra önemli

İki niceleyici yan yana geldiğinde sıraları değiştirilirse anlam değişebilir. Evren $\{0, 1, 2, 3, 4\}$ ve $R(x, y) : x + y = 4$ olsun.

- $\forall x\, \exists y\, R(x, y)$: "her $x$ için, ona uyan bir $y$ var." Doğru: $y = 4 - x$. Her $x$ **kendi** $y$'sini seçebiliyor.
- $\exists y\, \forall x\, R(x, y)$: "öyle **tek bir** $y$ var ki bütün $x$'lere uyuyor." Yanlış: $y = 0$ sadece $x = 4$'e uyuyor.

Kodda bu iki iç içe döngü, ama hangisinin dışta olduğu değişiyor:

```c
#define N 5   // evren: {0, 1, 2, 3, 4}

static bool R(int x, int y) { return x + y == 4; }

// forall x exists y: R(x, y)
static bool forall_exists(void) {
    for (int x = 0; x < N; x++) {
        bool found = false;
        for (int y = 0; y < N; y++) {
            if (R(x, y)) { found = true; break; }
        }
        if (!found) return false;   // bu x icin y yok
    }
    return true;
}

// exists y forall x: R(x, y)
static bool exists_forall(void) {
    for (int y = 0; y < N; y++) {
        bool all = true;
        for (int x = 0; x < N; x++) {
            if (!R(x, y)) { all = false; break; }
        }
        if (all) return true;       // butun x'lere uyan tek bir y
    }
    return false;
}
```

```
forall x exists y: 1
exists y forall x: 0
```

$\exists y\, \forall x$ her zaman $\forall x\, \exists y$'yi gerektirir (bütün $x$'lere uyan bir $y$ varsa, her $x$ o $y$'yi seçebilir), ama tersi gerekmez. Matematikteki pek çok tanımın inceliği tam bu sırada saklı; Ders 6.12'deki büyük-O tanımı "$\exists c\, \exists n_0\, \forall n \ge n_0$" diye başlıyor ve sırayı karıştırmak tanımı bozuyor.

---

## 6. Program koşullarını mantıkla yazmak

Niceleyiciler, bir programın **ne yapması gerektiğini** kesin biçimde yazmanın dili. "Dizi sıralı" cümlesi:

$$
\text{sıralı}(a, n) \equiv \forall i\, (0 \le i < n - 1 \to a_i \le a_{i+1})
$$

Ve bu tanım doğrudan koda dönüşüyor:

```c
static bool is_sorted(const int *a, int n) {
    // forall i in [0, n-1): a[i] <= a[i+1]
    for (int i = 0; i + 1 < n; i++) {
        if (a[i] > a[i + 1]) return false;
    }
    return true;
}
```

`i + 1 < n` yazdık, `i < n - 1` değil: ikisi matematikte aynı ama `n` işaretsiz bir tip olsaydı (`size_t`), `n = 0` iken `n - 1` dev bir sayıya sarardı (Ders 3.6). Mantıksal tanım ile kod arasında böyle küçük farklar olabiliyor; tanımı yazmak bu farkları fark etmeyi kolaylaştırıyor.

Bir fonksiyonun sözleşmesi iki yüklemle yazılır:

- **Ön koşul** (precondition): fonksiyon çağrılmadan önce çağıranın sağlaması gereken şey.
- **Son koşul** (postcondition): fonksiyon döndüğünde fonksiyonun garanti ettiği şey.

Ders 2.10'daki ikili arama örneği:

- Ön koşul: $\text{sıralı}(a, n)$
- Son koşul: dönüş değeri $r \ne -1$ ise $a_r = \text{key}$; $r = -1$ ise $\forall i\, (0 \le i < n \to a_i \ne \text{key})$

Son koşulun ikinci yarısı bir $\forall$; "bulamadım" demek, "hiçbir yerde yok" demek. Bu koşulları `assert` ile çalışma zamanında denetleyebiliriz:

```c
#include <assert.h>

int binary_search(const int *a, int n, int key) {
    assert(is_sorted(a, n));            // on kosul
    int lo = 0, hi = n - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] == key) return mid;
        if (a[mid] < key) lo = mid + 1;
        else hi = mid - 1;
    }
    return -1;
}
```

`assert` koşul yanlışsa programı durdurur ve hangi satırda olduğunu söyler; `-DNDEBUG` ile derleyince tamamen kaybolur. Burada bir bedel var: `is_sorted` $n$ adım, ikili arama $\log n$ adım. Ön koşulu denetlemek fonksiyonun kendisinden pahalı. Bu yüzden böyle denetimler geliştirme sırasında açık, son sürümde kapalı tutulur.

`assert` bir koşulun **bu çalıştırmada** doğru olduğunu gösterir; **her** çalıştırmada doğru olduğunu göstermez. "Her girdi için" demek bir $\forall$, ve sonsuz (ya da çok büyük) bir evrende $\forall$'ı tek tek denetleyemeyiz. Bunun için **kanıt** gerekiyor; bir sonraki dersin konusu.

---

## Alıştırmalar

**1** – Şu cümleleri niceleyicilerle yaz (evren tamsayılar): (a) "Her sayının bir ardılı vardır." (b) "En büyük tamsayı yoktur." (c) "$n$ asaldır." ($n > 1$ ve $1$, $n$ dışında böleni yok.)

**2** – Şunları olumsuzla ve $\neg$'yi en içe it: (a) $\forall x\, (x > 0 \to x^2 > 0)$ (b) $\exists x\, \forall y\, (x \le y)$

**3** – `forall` ve `exists`'ten yalnız birini kullanarak diğerini yaz. Bunun için yüklemin değilini veren bir fonksiyon gerekiyor; C'de bunu genel olarak yazmak neden zor? (İpucu: C'de fonksiyonlar çalışma zamanında üretilemez.)

**4** – "Dizideki bütün elemanlar farklıdır" koşulunu niceleyicilerle yaz ve `bool all_distinct(const int *a, int n)` olarak kodla. Kaç karşılaştırma yapıyor?

**5** – Ders 4.2'deki doğrusal aramanın (`find`) son koşulunu yaz. Fonksiyon ilk bulduğu indeksi döndürüyorsa, son koşula bunu da ekle.

<details>
<summary>Cevaplar</summary>

**1** – (a) $\forall n\, \exists m\, (m = n + 1)$. (b) $\neg \exists n\, \forall m\, (m \le n)$, ya da olumsuzlamayı içeri iterek $\forall n\, \exists m\, (m > n)$. (c) $n > 1 \land \forall d\, ((d > 0 \land d \mid n) \to (d = 1 \lor d = n))$. Burada $d \mid n$ "$d$, $n$'i böler" demek.

Dikkat: (a) gerçek matematikte doğru ama C'nin `int`'inde yanlış; `INT_MAX`'ın ardılı yok, `INT_MAX + 1` undefined behavior (Ders 3.8). Evren değişince doğruluk değişiyor.

**2** – (a) $\neg \forall x\, (x > 0 \to x^2 > 0) \equiv \exists x\, \neg(x > 0 \to x^2 > 0) \equiv \exists x\, (x > 0 \land x^2 \le 0)$. Son adımda $\neg(p \to q) \equiv p \land \neg q$ kullandık ($p \to q \equiv \neg p \lor q$ ve De Morgan). (b) $\neg \exists x\, \forall y\, (x \le y) \equiv \forall x\, \exists y\, (y < x)$: "her sayıdan küçük bir sayı var", yani en küçük eleman yok. Tamsayılarda doğru, doğal sayılarda yanlış (0 en küçük).

**3** – `exists(a, n, p)` = `!forall(a, n, not_p)`. Sorun `not_p`'yi yazmak: C'de "verilen `p`'nin tersini döndüren yeni bir fonksiyon" çalışma zamanında üretilemiyor; her yüklem için elle `not_is_even` gibi bir fonksiyon yazman gerekiyor. Pratik çözüm, `forall`'a bir `bool negate` parametresi eklemek ya da yüklemle birlikte bir bağlam pointer'ı (`void *ctx`, Ders 4.9) geçirmek. C++'taki lambda ifadeleri (Faz 13) bu sorunu dil düzeyinde çözüyor.

**4** – $\forall i\, \forall j\, ((0 \le i < j < n) \to a_i \ne a_j)$.

```c
bool all_distinct(const int *a, int n) {
    for (int i = 0; i < n; i++) {
        for (int j = i + 1; j < n; j++) {
            if (a[i] == a[j]) return false;   // karsi ornek: (i, j)
        }
    }
    return true;
}
```

İç içe iki $\forall$, iç içe iki döngü. En kötü durumda $\frac{n(n-1)}{2}$ karşılaştırma ($j > i$ koşulu her çifti bir kez saydırıyor; bu toplamı Ders 6.4'te kanıtlayacağız).

**5** – `r = find(a, n, key)` için:

- $r = -1 \to \forall i\, (0 \le i < n \to a_i \ne \text{key})$
- $r \ne -1 \to (0 \le r < n \land a_r = \text{key})$
- İlk bulunan: $r \ne -1 \to \forall i\, (0 \le i < r \to a_i \ne \text{key})$

Son madde "$r$'den önceki hiçbir yerde yok" diyor; bu, fonksiyonun **en küçük** uygun indeksi döndürdüğünü söylüyor.

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §1.4–1.5: yüklemler, niceleyiciler, iç içe niceleyiciler.
- Daniel Velleman, *How to Prove It* (3. baskı), Bölüm 2: niceleyici mantığı.
- David Gries, *The Science of Programming*: ön koşul ve son koşulla program yazma.

**Sıradaki ders:** Kanıt teknikleri. "Her $n$ için" bir şeyi denemeden nasıl bilebiliriz?
