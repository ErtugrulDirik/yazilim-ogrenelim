---
title: "9.11 Dinamik programlama 1"
description: "Aynı alt problemi tekrar tekrar çözmemek: Fibonacci'de saf özyinelemenin 331 milyon çağrısına karşı memoization ile 179 çağrı ve tablo ile tek döngü; dinamik programlamanın iki koşulu (optimal alt yapı, örtüşen alt problemler) ve iki biçimi (yukarıdan aşağı, aşağıdan yukarı); en uzun ortak alt dizi (LCS): özyinelemeli tanım, (n+1)×(m+1) tablo, ABCBDAB/BDCABA örneği ve geri izleme; 16 000 karakterde 0.5 s ama 1 GB tablo; satırların LCS'siyle çalışan, diff -u gibi çıktı veren küçük bir diff."
---

Ders 8.6'nın Alıştırma 1'inde saf özyinelemeli Fibonacci'nin çağrı sayısını ölçmüştük: `fib(30)` için 2.7 milyon çağrı, çünkü aynı alt problemler (`fib(28)`, `fib(27)`, ...) defalarca çözülüyordu. Orada "zaman sorunu yığınla değil, memoization ile çözülür" demiştik. Bu ders o çözümü genelleştiriyor: **dinamik programlama** (DP). Fikir basit: bir alt problemin cevabını ilk hesapladığında **sakla**, bir daha sorulduğunda hesaplama, hatırla. Etkisi dramatik: üstelden polinoma. Ders 9.10'da açgözlülüğün yanıldığı madeni para problemini bu teknikle çözmüştük; bu ve sonraki iki ders tekniğin kendisini kuruyor.

---

## 1. Fibonacci üç yolla

```c
/* Fibonacci uc yolla: saf ozyineleme, memoization (yukaridan asagi), tablo (asagidan yukari) */
#include <stdint.h>
#include <stdio.h>
#include <time.h>

static long cagri;
static uint64_t fib_saf(int n) { cagri++; return n < 2 ? (uint64_t)n : fib_saf(n - 1) + fib_saf(n - 2); }

static uint64_t not_[100]; static int biliniyor[100];
static uint64_t fib_memo(int n) {                         /* ayni alt problemi ikinci kez cozme: sonucu sakla */
    cagri++;
    if (n < 2) return (uint64_t)n;
    if (biliniyor[n]) return not_[n];
    biliniyor[n] = 1;
    return not_[n] = fib_memo(n - 1) + fib_memo(n - 2);
}

static uint64_t fib_tablo(int n) {                        /* kucukten buyuge: her deger bir kez, O(1) bellek */
    uint64_t a = 0, b = 1;
    for (int i = 0; i < n; i++) { uint64_t t = a + b; a = b; b = t; }
    return a;
}

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

int main(void) {
    for (int n = 30; n <= 40; n += 5) {
        cagri = 0; double t0 = simdi(); uint64_t s = fib_saf(n); double t = simdi() - t0;
        printf("saf   fib(%d) = %llu  %10ld cagri  %.3f s\n", n, (unsigned long long)s, cagri, t);
    }
    cagri = 0; uint64_t m = fib_memo(90);
    printf("memo  fib(90) = %llu  %ld cagri\n", (unsigned long long)m, cagri);
    printf("tablo fib(90) = %llu\n", (unsigned long long)fib_tablo(90));
    printf("tablo fib(93) = %llu (uint64_t'ye sigan son)\n", (unsigned long long)fib_tablo(93));
}
```

```
$ cc -std=c11 -O2 -Wall -Wextra fib.c -o fib && ./fib
saf   fib(30) = 832040     2692537 cagri  0.006 s
saf   fib(35) = 9227465    29860703 cagri  0.062 s
saf   fib(40) = 102334155   331160281 cagri  0.676 s
memo  fib(90) = 2880067194370816120  179 cagri
tablo fib(90) = 2880067194370816120
tablo fib(93) = 12200160415121876738 (uint64_t'ye sigan son)
```

- **Saf**: $n$ 5 artınca çağrı sayısı 11 kat ($\varphi^5 \approx 11.1$): $\Theta(\varphi^n)$, üstel. `fib(90)` bu hızla yaklaşık 600 yıl sürerdi ($0.68 \text{ s} \times \varphi^{50}$).
- **Memoization** (yukarıdan aşağı): aynı özyinelemeli tanım, ama her `fib(k)` sonucu bir tabloya yazılıyor ve ikinci çağrıda oradan okunuyor. `fib(90)` için 179 çağrı: her $k$ için en fazla iki çağrı (biri hesaplayan, biri tablodan okuyan). $\Theta(n)$.
- **Tablo** (aşağıdan yukarı): alt problemleri küçükten büyüğe, sırayla çöz. Özyineleme yok; ve her adımda sadece son iki değer gerektiği için bellek $O(1)$.

($F_{93}$, `uint64_t`'ye sığan en büyük Fibonacci sayısı; $F_{94} > 2^{64}$. Ders 3.8.)

İkisi de aynı iki gözleme dayanıyor, ve bunlar dinamik programlamanın **koşulları**:

1. **Optimal alt yapı**: problemin çözümü, daha küçük **alt problemlerin** çözümlerinden kurulabiliyor. ($F_n = F_{n-1} + F_{n-2}$.)
2. **Örtüşen alt problemler**: farklı yollardan **aynı** alt problemlere ulaşılıyor; saf özyineleme onları tekrar tekrar çözüyor.

Birinci koşul böl-yönet için de geçerliydi (Ders 9.4). Fark ikincide: birleştirmeli sıralamanın alt problemleri (dizinin farklı yarıları) hiç örtüşmüyor, saklamanın faydası yok. Fibonacci'de ve aşağıdaki problemlerde alt problemler üst üste biniyor; sayıları **polinom**, ama saf özyineleme onları üstel sayıda kez ziyaret ediyor.

| | Yukarıdan aşağı (memoization) | Aşağıdan yukarı (tablo) |
| --- | --- | --- |
| Kod | Özyinelemeli tanımın kendisi + bir tablo | Alt problemleri doğru **sırayla** gezen döngüler |
| Hesaplanan alt problemler | Sadece gerçekten gerekenler | Hepsi |
| Yığın | Derinlik kadar (Ders 8.6'nın riski) | Yok |
| Bellek optimizasyonu | Zor | Kolay (sadece gereken satırları tut) |

---

## 2. En uzun ortak alt dizi

İki dizi $x$ ve $y$. Bir **alt dizi**, bazı elemanları silerek (sırayı bozmadan) elde edilen dizi: `ACE`, `ABCDE`'nin bir alt dizisi (ardışık olması gerekmiyor; ardışık olana alt **string** denir). **En uzun ortak alt dizi** (LCS, longest common subsequence): ikisinin de alt dizisi olan en uzun dizi. `ABCBDAB` ve `BDCABA` için uzunluğu 4 (örneğin `BCBA`).

LCS, iki şeyin "ne kadar benzediğinin" ölçüsü: iki DNA dizisi, bir dosyanın iki sürümü. `diff` aracı tam olarak iki dosyanın satırlarının LCS'sini bulup geri kalanları "silinen" ve "eklenen" olarak gösteriyor. Git, her `git diff`'te bunun bir varyantını çalıştırıyor.

### Özyinelemeli tanım

$L(i, j)$, $x[0..i)$ ile $y[0..j)$'nin LCS uzunluğu olsun. Son karakterlere bak:

- Biri boşsa: $L(i, 0) = L(0, j) = 0$.
- Son karakterler aynıysa ($x_{i-1} = y_{j-1}$): o karakter bir LCS'nin sonu olabilir; $L(i, j) = L(i-1, j-1) + 1$.
- Farklıysa: ikisinden en az biri LCS'nin sonu değil; birini at, daha iyisini seç: $L(i, j) = \max(L(i-1, j),\; L(i, j-1))$.

(İkinci durumun doğruluğu bir değiştirme argümanı: son karakterler eşitken, onları kullanmayan bir LCS her zaman onları kullanacak şekilde değiştirilebilir. CLRS Teorem 15.1.)

Saf özyineleme her adımda (karakterler farklıysa) iki dala ayrılıyor: üstel. Ama sadece $(n+1)(m+1)$ **farklı** $(i, j)$ çifti var. Tablo, onları satır satır, her hücrenin ihtiyaç duyduğu üç komşudan (sol, üst, sol üst) sonra dolduruyor.

```c
/* En uzun ortak alt dizi (LCS): saf ozyineleme, tablo, geri izleme; ve satir tabanli kucuk bir diff */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long cagri;
static int lcs_saf(const char *x, int i, const char *y, int j) {     /* x[i..), y[j..) */
    cagri++;
    if (!x[i] || !y[j]) return 0;
    if (x[i] == y[j]) return 1 + lcs_saf(x, i + 1, y, j + 1);
    int a = lcs_saf(x, i + 1, y, j), b = lcs_saf(x, i, y, j + 1);
    return a > b ? a : b;
}

/* L[i][j] = x[0..i) ile y[0..j)'nin LCS uzunlugu. (n+1) x (m+1) tablo, satir satir doldur. */
static int *lcs_tablo(const char *x, int n, const char *y, int m) {
    int *L = calloc((size_t)(n + 1) * (m + 1), sizeof *L);
    #define T(i, j) L[(size_t)(i) * (m + 1) + (j)]
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++)
            T(i, j) = x[i - 1] == y[j - 1] ? T(i - 1, j - 1) + 1
                    : T(i - 1, j) > T(i, j - 1) ? T(i - 1, j) : T(i, j - 1);
    return L;
}

/* Tablodan bir LCS'yi geri izle: sagdan sola */
static void geri_izle(const int *L, const char *x, int n, const char *y, int m, char *out) {
    int i = n, j = m, k = T(n, m);
    out[k] = 0;
    while (i > 0 && j > 0) {
        if (x[i - 1] == y[j - 1]) { out[--k] = x[i - 1]; i--; j--; }
        else if (T(i - 1, j) >= T(i, j - 1)) i--;
        else j--;
    }
}
```

(`T(i, j)` makrosu, iki boyutlu tabloyu tek boyutlu bir dizide tutuyor; Ders 4.3. `(size_t)` çarpımı taşmaya karşı.)

```
$ cc -std=c11 -O2 -Wall -Wextra lcs.c -o lcs && ./lcs
LCS(ABCBDAB, BDCABA) = 4: BCBA
tablo:
      B D C A B A
    0 0 0 0 0 0 0 
  A 0 0 0 0 1 1 1 
  B 0 1 1 1 1 2 2 
  C 0 1 1 2 2 2 2 
  B 0 1 1 2 2 3 3 
  D 0 1 2 2 2 3 3 
  A 0 1 2 2 3 3 4 
  B 0 1 2 2 3 4 4 
saf n=10: LCS=6  2062 cagri  0.0000 s
saf n=12: LCS=7  82924 cagri  0.0002 s
saf n=14: LCS=6  1028271 cagri  0.0023 s
saf n=16: LCS=9  1754665 cagri  0.0035 s
tablo n= 1000: LCS=658 (0.658 n)  0.001 s  tablo 4 MB
tablo n= 4000: LCS=2607 (0.652 n)  0.014 s  tablo 64 MB
tablo n=16000: LCS=10445 (0.653 n)  0.505 s  tablo 1024 MB
```

(Sanitizer'lı derleme temiz.)

**Geri izleme**: tablo sadece **uzunluğu** veriyor; LCS'nin kendisi için sağ alt köşeden geriye yürünüyor. Karakterler eşitse o karakter LCS'de, çapraz git; değilse, değeri büyük olan komşuya (üst ya da sol) git. Eşitlikte hangisinin seçildiği, birden çok LCS arasından hangisinin bulunacağını belirliyor (`BCBA`, `BDAB` ve `BCAB` de uzunluğu 4).

**Saf özyineleme** dört harfli rastgele dizilerde, 16 karakterde bile 1.75 milyon çağrı; çağrı sayısı girdiye göre çok oynuyor ama üstel büyüyor. **Tablo** $O(nm)$ zaman: 16 000 karakter, 256 milyon hücre, 0.5 s. Ama **bellek** de $O(nm)$: 1 GB. Sadece uzunluk isteniyorsa iki satır yetiyor (Alıştırma 1), ama geri izleme bütün tabloyu gerektiriyor; büyük girdilerde bu, DP'nin asıl darboğazı. (Rastgele dört harfli dizilerde LCS uzunluğu $n$'nin yaklaşık 0.654 katı: Chvátal–Sankoff sabiti.)

---

## 3. Küçük bir diff

Aynı algoritma, karakterler yerine **satırlarla**. İki satır eşitse `strcmp` sıfır döndürüyor. Bu sefer tablo **sonekler** üzerinden kuruluyor ($L(i, j)$: $a[i..)$ ile $b[j..)$), ki geri izleme baştan sona ilerleyip satırları doğru sırada yazdırabilsin:

```c
/* Satir tabanli diff: satirlarin LCS'si ortak kalanlar; gerisi silinen (-) ya da eklenen (+) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int satirlar(const char *yol, char ***cikti) {
    FILE *f = fopen(yol, "r"); if (!f) { perror(yol); exit(1); }
    int n = 0, kap = 16; char **s = malloc(kap * sizeof *s), b[1024];
    while (fgets(b, sizeof b, f)) { if (n == kap) s = realloc(s, (kap *= 2) * sizeof *s); s[n++] = strdup(b); }
    fclose(f); *cikti = s; return n;
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "kullanim: %s eski yeni\n", argv[0]); return 2; }
    char **a, **b; int n = satirlar(argv[1], &a), m = satirlar(argv[2], &b);
    /* L[i][j]: a[i..n) ile b[j..m)'nin LCS'si (SONEKLER: boylece bastan sona yazdirilabilir) */
    int *L = calloc((size_t)(n + 1) * (m + 1), sizeof *L);
    #define T(i, j) L[(size_t)(i) * (m + 1) + (j)]
    for (int i = n - 1; i >= 0; i--)
        for (int j = m - 1; j >= 0; j--)
            T(i, j) = strcmp(a[i], b[j]) == 0 ? T(i + 1, j + 1) + 1 : T(i + 1, j) > T(i, j + 1) ? T(i + 1, j) : T(i, j + 1);
    int i = 0, j = 0, ortak = 0, sil = 0, ekle = 0;
    while (i < n || j < m) {
        if (i < n && j < m && strcmp(a[i], b[j]) == 0) { printf("  %s", a[i]); i++; j++; ortak++; }
        else if (i < n && (j == m || T(i + 1, j) >= T(i, j + 1))) { printf("- %s", a[i]); i++; sil++; }   /* once silme (diff -u gibi) */
        else { printf("+ %s", b[j]); j++; ekle++; }
    }
    fflush(stdout);
    fprintf(stderr, "%d ortak, %d silinen, %d eklenen satir\n", ortak, sil, ekle);
    return sil || ekle;
}
```

İki küçük dosya, `eski.c`:

```c
int main(void) {
    int x = 1;
    int y = 2;
    printf("%d\n", x + y);
    return 0;
}
```

ve `yeni.c`:

```c
int main(void) {
    int x = 1;
    int z = 3;
    int y = 2;
    printf("%d\n", x + y + z);
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined fark.c -o fark && ./fark eski.c yeni.c
  int main(void) {
      int x = 1;
+     int z = 3;
      int y = 2;
-     printf("%d\n", x + y);
+     printf("%d\n", x + y + z);
      return 0;
  }
5 ortak, 1 silinen, 2 eklenen satir
```

Sistemdeki `diff -u` ile aynı değişiklikler, aynı sırayla:

```
$ diff -u eski.c yeni.c
@@ -1,6 +1,7 @@
 int main(void) {
     int x = 1;
+    int z = 3;
     int y = 2;
-    printf("%d\n", x + y);
+    printf("%d\n", x + y + z);
     return 0;
 }
```

(İlk iki başlık satırı, dosya adları ve tarihler, kısaltıldı.) Çıkış kodu da `diff` gibi: fark varsa 1, yoksa 0. Değiştirilen bir satır, bir silme ve bir ekleme olarak görünüyor; satırın **içindeki** farkı göstermek, aynı LCS'yi o iki satırın karakterlerine bir kez daha uygulamak demek.

Gerçek `diff` ve git, $O(nm)$ tablo yerine Eugene Myers'ın (1986) $O((n + m) D)$ algoritmasını kullanıyor: $D$, iki dosya arasındaki **değişiklik** sayısı. Dosyalar az farklıysa (her zamanki durum) neredeyse doğrusal, ve bellek $O(n + m)$. Faz 9 projesinde (Ders 9.24) `diff`'imizi büyük dosyalara dayanacak hale getireceğiz.

---

## Alıştırmalar

**1** – LCS **uzunluğunu** $O(\min(n, m))$ bellekle hesapla: tablonun sadece son iki satırını tut. Neden iki satır yetiyor? Bu yöntemle LCS'nin kendisi neden bulunamıyor?

**2** – Bir dizinin **en uzun artan alt dizisi** (LIS): `3 1 4 1 5 9 2 6` için ne? Bunu LCS ile nasıl çözersin (ipucu: dizinin sıralanmış hali)? Maliyeti ne? Daha hızlı bir yöntem var mı?

**3** – Sadece satır silme ve ekleme izin verilirse, bir dosyayı diğerine çeviren **en az** işlem sayısı $n + m - 2 \cdot \text{LCS}$. Neden? `eski.c` ve `yeni.c` için kontrol et.

**4** – LCS'yi memoization ile (özyinelemeli tanım + tablo) yaz. 16 000 karakterlik iki dizi için özyineleme derinliği ne olur, ve ne olur (Ders 8.6)? Aşağıdan yukarı tablo neden bu sorunu taşımıyor?

**5** – İki dizinin LCS'si yerine en uzun ortak **alt string**'i (ardışık) istiyorsun. DP bağıntısı nasıl değişir? `ABABC` ve `BABCA` için cevap ne?

<details>
<summary>Cevaplar</summary>

**1** – Satır $i$'nin her hücresi sadece satır $i$ ve satır $i - 1$'deki hücrelere bakıyor (sol, üst, sol üst). Önceki satırları tutmaya gerek yok: iki dizi (önceki ve şimdiki) ve her satırdan sonra yer değiştir. Kısa dizi sütunlara konursa bellek $2(\min(n, m) + 1)$ tamsayı. 16 000 karakterlik örnekte 1 GB yerine 128 KB. LCS'nin kendisini geri izlemek için ise, sağ alt köşeden başlayıp her hücrede hangi komşudan gelindiğini bilmek gerekiyor ve o satırlar silindi. Hirschberg (1975) bu sorunu böl-yönet ile çözüyor: orta satırda LCS'nin hangi sütundan geçtiğini, bir kez baştan bir kez sondan iki satırlık DP ile bul, sonra iki yarıyı özyinelemeyle çöz. $O(nm)$ zaman, $O(n + m)$ bellek.

**2** – LIS: `1 4 5 9` ya da `1 4 5 6` gibi, uzunluk 4. Dizinin sıralanmış ve tekrarları atılmış hali `1 2 3 4 5 6 9`; orijinal ile bunun LCS'si, orijinalin artan bir alt dizisi (sıralı dizinin alt dizisi olduğu için artan) ve en uzunu: LIS. $O(n^2)$. Daha hızlısı $O(n \log n)$: her uzunluk $k$ için, uzunluğu $k$ olan artan alt dizilerin **en küçük** son elemanını bir dizide tut (bu dizi sıralı kalıyor); her yeni eleman için onun yerini ikili aramayla (Ders 9.2) bul ve güncelle. "Sabır sıralaması" (patience sorting) adıyla da bilinir; Myers'ın diff algoritmasıyla yakın akraba.

**3** – Ortak alt dizideki satırlar yerinde kalıyor; `eski`'deki diğer $n - \text{LCS}$ satır silinmeli, `yeni`'deki diğer $m - \text{LCS}$ satır eklenmeli. Daha az işlem, daha uzun bir ortak alt dizi demek olurdu. `eski.c` 6, `yeni.c` 7 satır, LCS 5: $6 + 7 - 10 = 3$ işlem; çıktıda 1 silme + 2 ekleme. Değiştirme işlemi de (bir satırı tek adımda başkasıyla değiştirmek) izinli olsaydı problem **düzenleme uzaklığı** olurdu: Ders 9.12.

**4** – Memoization sürümünde `lcs(i, j)` çağrısı `lcs(i+1, j)` ya da `lcs(i, j+1)`'i çağırıyor; en uzun çağrı zinciri $(0, 0)$'dan $(n, m)$'ye bir yol, derinlik $n + m = 32\,000$. Çerçeve başına 48–80 bayt (Ders 8.6) ile 2–3 MB; 8 MB'lık yığına sığıyor ama $n = 100\,000$'de sığmaz ve program çöker. Tablo ayrıca $(n+1)(m+1)$ hücre ve hangilerinin hesaplandığı bilgisi. Aşağıdan yukarı tablo, aynı alt problemleri özyineleme olmadan, bağımlılıkları zaten hesaplanmış bir sırayla (satır satır) dolduruyor: yığın kullanımı sabit. Bu, Ders 8.6'daki "özyinelemeyi açık yapıya çevirme"nin DP'deki hali; burada açık yığın bile gerekmiyor, çünkü doğru gezinme sırası önceden biliniyor.

**5** – $S(i, j)$: $x[0..i)$ ile $y[0..j)$'nin **tam sonunda biten** en uzun ortak alt string'in uzunluğu. Son karakterler eşitse $S(i, j) = S(i-1, j-1) + 1$, değilse $S(i, j) = 0$ (ardışıklık bozuldu, sıfırdan başla). Cevap tablonun **en büyük** hücresi, köşesi değil. `ABABC` ve `BABCA`: `BABC`, uzunluk 4. LCS'deki $\max$ yerine 0 gelmesi küçük bir değişiklik ama problemi tamamen değiştiriyor; ve bu problem $O(n + m)$'de sonek ağaçlarıyla da çözülebiliyor (LCS için böyle bir hızlanma bilinmiyor: $O(nm)$'den belirgin biçimde hızlı bir LCS algoritması olmadığına dair koşullu alt sınırlar var).

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 15.1–15.4: dinamik programlamanın unsurları ve LCS.
- Richard Bellman, *Dynamic Programming*, Princeton University Press, 1957.
- James Hunt ve M. Douglas McIlroy, "An Algorithm for Differential File Comparison", Bell Labs CSTR 41, 1976: Unix `diff`'in ilk algoritması.
- Eugene Myers, "An O(ND) Difference Algorithm and Its Variations", *Algorithmica* 1(2), 1986.
- Dan Hirschberg, "A Linear Space Algorithm for Computing Maximal Common Subsequences", *Communications of the ACM* 18(6), 1975.

**Sıradaki ders:** Dinamik programlama 2. Sırt çantası, düzenleme uzaklığı ve matris zinciri çarpımı.
