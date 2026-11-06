---
title: "9.12 Dinamik programlama 2"
description: "Üç klasik DP problemi ve tasarım yöntemi (alt problemi tanımla, bağıntıyı yaz, doldurma sırasını bul, geri izle): 0/1 sırt çantası, değer/ağırlık oranlı açgözlünün 200'e karşı 220 vermesi ve kaba kuvvetle doğrulama, O(nW)'nin neden 'sözde polinom' olduğu; düzenleme (Levenshtein) uzaklığı, işlem dizisinin geri izlenmesi ve derleyicinin 'bunu mu demek istediniz' önerisi; matris zinciri çarpımı, aralık DP'si ve beş matriste en iyi sıranın soldan sağa sıradan 266 kat az çarpım yapması."
---

Ders 9.11'de dinamik programlamanın iki koşulunu (optimal alt yapı, örtüşen alt problemler) ve iki biçimini gördük. Bu ders tekniği üç klasik problemle pekiştiriyor; her birinin alt problem yapısı farklı. Hepsinde aynı dört adımı izleyeceğiz:

1. **Alt problemi tanımla**: tablonun bir hücresi neyi temsil ediyor? Bu, DP'nin en zor ve en yaratıcı adımı.
2. **Bağıntıyı yaz**: bir hücre, daha küçük hücrelerden nasıl hesaplanıyor? Doğruluğu genelde "son karar ne oldu?" sorusuyla gösteriliyor.
3. **Doldurma sırasını bul**: her hücre, ihtiyaç duyduğu hücrelerden sonra doldurulmalı.
4. **Geri izle**: tablo sadece optimal **değeri** veriyor; optimal **çözümün kendisi** için hangi seçimlerin yapıldığı tablodan geriye doğru okunuyor.

---

## 1. 0/1 sırt çantası

Kapasitesi $W$ kilo olan bir sırt çantası ve $n$ eşya; $i$. eşyanın ağırlığı $w_i$, değeri $v_i$. Her eşya ya alınır ya alınmaz (bölünemez; Ders 9.10'un Alıştırma 2'sindeki kesirli sürümden farkı). Toplam değeri en büyük, kapasiteyi aşmayan altkümeyi seç.

**Alt problem**: $T(i, w)$ = ilk $i$ eşyayla, kapasite $w$ iken alınabilecek en büyük değer.

**Bağıntı**, $i$. eşya hakkındaki son karara göre: alınmazsa $T(i-1, w)$; alınırsa (sığıyorsa) $v_i + T(i-1, w - w_i)$. İkisinin büyüğü.

$$
T(i, w) = \max\big(T(i-1, w),\; v_i + T(i-1, w - w_i)\big), \qquad T(0, w) = 0.
$$

**Sıra**: satır $i$, sadece satır $i-1$'e bakıyor: satır satır.

```c
/* 0/1 sirt cantasi: en iyi[i][w] = ilk i esyayla, kapasite w'de en buyuk deger */
#include <stdio.h>
#include <stdlib.h>

typedef struct { const char *ad; int agirlik, deger; } Esya;

static int canta(const Esya *e, int n, int W, int *secildi) {
    int *T = calloc((size_t)(n + 1) * (W + 1), sizeof *T);
    #define T(i, w) T[(size_t)(i) * (W + 1) + (w)]
    for (int i = 1; i <= n; i++)
        for (int w = 0; w <= W; w++) {
            T(i, w) = T(i - 1, w);                                   /* i. esyayi alma */
            if (e[i - 1].agirlik <= w && T(i - 1, w - e[i - 1].agirlik) + e[i - 1].deger > T(i, w))
                T(i, w) = T(i - 1, w - e[i - 1].agirlik) + e[i - 1].deger;   /* al */
        }
    int en = T(n, W);
    for (int i = n, w = W; i > 0; i--) {                            /* geri izle: deger degistiyse alinmis */
        secildi[i - 1] = T(i, w) != T(i - 1, w);
        if (secildi[i - 1]) w -= e[i - 1].agirlik;
    }
    free(T);
    return en;
}

int main(void) {
    Esya e[] = { {"cadir", 5, 60}, {"uyku tulumu", 3, 50}, {"ocak", 4, 70}, {"kamera", 2, 30},
                 {"kitap", 1, 10}, {"durbun", 3, 40}, {"yemek", 6, 90} };
    int n = 7, W = 14, s[7];
    int en = canta(e, n, W, s), top_a = 0;
    printf("kapasite %d: en buyuk deger %d\n  secilen:", W, en);
    for (int i = 0; i < n; i++) if (s[i]) { printf(" %s(%d kg, %d)", e[i].ad, e[i].agirlik, e[i].deger); top_a += e[i].agirlik; }
    printf("  toplam %d kg\n", top_a);
    /* acgozlu (deger/agirlik oranina gore) */
    int sira[7] = { 0, 1, 2, 3, 4, 5, 6 };
    for (int i = 0; i < n; i++) for (int j = i + 1; j < n; j++)
        if (e[sira[j]].deger * e[sira[i]].agirlik > e[sira[i]].deger * e[sira[j]].agirlik) { int t = sira[i]; sira[i] = sira[j]; sira[j] = t; }
    int kalan = W, deger = 0; printf("  acgozlu (oran):");
    for (int k = 0; k < n; k++) { const Esya *x = &e[sira[k]]; if (x->agirlik <= kalan) { kalan -= x->agirlik; deger += x->deger; printf(" %s", x->ad); } }
    printf("  -> deger %d\n", deger);
    /* kaba kuvvet dogrulamasi */
    int kk = 0; for (int m = 0; m < (1 << n); m++) { int a = 0, d = 0; for (int i = 0; i < n; i++) if (m >> i & 1) { a += e[i].agirlik; d += e[i].deger; } if (a <= W && d > kk) kk = d; }
    printf("  kaba kuvvet (2^%d altkume): %d\n", n, kk);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined canta.c -o canta && ./canta
kapasite 14: en buyuk deger 220
  secilen: uyku tulumu(3 kg, 50) ocak(4 kg, 70) kitap(1 kg, 10) yemek(6 kg, 90)  toplam 14 kg
  acgozlu (oran): ocak uyku tulumu kamera durbun kitap  -> deger 200
  kaba kuvvet (2^7 altkume): 220
```

DP 220 buluyor; bütün $2^7 = 128$ altkümeyi deneyen kaba kuvvet de 220. Ders 9.10'daki değer/ağırlık oranına göre açgözlü kural ise 200'de kalıyor: oranı yüksek küçük eşyaları (ocak 17.5, uyku tulumu 16.7, kamera 15, ...) doldurup en değerli büyük eşyaya (yemek, 6 kg, 90) yer bırakmıyor. Kesirli sürümde doğru olan açgözlülük, bölünmezlik yüzünden yanılıyor.

**Geri izleme**: $T(i, w) \ne T(i-1, w)$ ise $i$. eşya alınmış (almadan aynı değere ulaşılamıyordu); kapasiteyi azaltıp devam. Değer değişmediyse alınmamış.

### Sözde polinom

Maliyet $O(nW)$: $n$ ve $W$'de polinom. Ama $W$ bir **sayı**, girdinin uzunluğu değil: $W = 10^{18}$ girdide sadece 60 bit tutuyor, tablo ise $10^{18}$ sütun. Girdi uzunluğuna göre bu üstel. Böyle algoritmalara **sözde polinom** (pseudo-polynomial) deniyor. 0/1 sırt çantası NP-zor (Ders 9.22); ağırlıklar küçük tamsayılarken DP pratik, büyükken değil.

---

## 2. Düzenleme uzaklığı

Ders 9.11'deki LCS sadece silme ve eklemeye izin veriyordu (Alıştırma 3). **Düzenleme uzaklığı** (edit distance, Levenshtein, 1965) bir string'i diğerine çeviren en az **ekle**, **sil** ve **değiştir** işlemi sayısı.

**Alt problem**: $D(i, j)$ = $x[0..i)$'yi $y[0..j)$'ye çevirmenin en az maliyeti.

**Bağıntı**, son karakterler üzerindeki son işleme göre:

$$
D(i, j) = \min \begin{cases} D(i-1, j) + 1 & x_{i-1}\text{'i sil} \\ D(i, j-1) + 1 & y_{j-1}\text{'i ekle} \\ D(i-1, j-1) + [x_{i-1} \ne y_{j-1}] & \text{değiştir (aynıysa bedava)} \end{cases}
$$

Kenarlar: $D(i, 0) = i$ (hepsini sil), $D(0, j) = j$ (hepsini ekle). LCS'nin tablosuyla aynı biçim ve aynı sıra.

```c
/* Duzenleme (Levenshtein) uzakligi: ekle, sil, degistir; islem dizisini geri izle */
#include <stdio.h>
#include <string.h>

static int min3(int a, int b, int c) { return a < b ? (a < c ? a : c) : (b < c ? b : c); }

static int uzaklik(const char *x, const char *y, int yaz) {
    int n = (int)strlen(x), m = (int)strlen(y);
    static int D[64][64];
    for (int i = 0; i <= n; i++) D[i][0] = i;                       /* x[0..i)'yi bos stringe: i silme */
    for (int j = 0; j <= m; j++) D[0][j] = j;                       /* bostan y[0..j)'ye: j ekleme */
    for (int i = 1; i <= n; i++)
        for (int j = 1; j <= m; j++)
            D[i][j] = min3(D[i - 1][j] + 1,                          /* x[i-1]'i sil */
                           D[i][j - 1] + 1,                          /* y[j-1]'i ekle */
                           D[i - 1][j - 1] + (x[i - 1] != y[j - 1])); /* degistir (ya da ayniysa bedava) */
    if (yaz) {                                                       /* geri izle, islemleri sondan basa topla */
        char adim[128][48]; int k = 0, i = n, j = m;
        while (i > 0 || j > 0) {
            if (i > 0 && j > 0 && D[i][j] == D[i - 1][j - 1] + (x[i - 1] != y[j - 1])) {
                if (x[i - 1] != y[j - 1]) snprintf(adim[k++], 48, "degistir %c -> %c", x[i - 1], y[j - 1]);
                i--; j--;
            } else if (i > 0 && D[i][j] == D[i - 1][j] + 1) { snprintf(adim[k++], 48, "sil %c", x[i - 1]); i--; }
            else { snprintf(adim[k++], 48, "ekle %c", y[j - 1]); j--; }
        }
        printf("  %s -> %s: %d islem:", x, y, D[n][m]);
        for (int t = k - 1; t >= 0; t--) printf(" [%s]", adim[t]);
        printf("\n");
    }
    return D[n][m];
}

int main(void) {
    uzaklik("kitten", "sitting", 1);
    uzaklik("algoritma", "logaritma", 1);
    uzaklik("printf", "pritnf", 1);
    const char *sozluk[] = { "while", "for", "return", "struct", "switch", "static", "sizeof", "typedef", "printf", "include" };
    const char *yazim[] = { "retrun", "swich", "pirntf", "incldue", "whiel" };
    for (int k = 0; k < 5; k++) {
        int en = 99; const char *oneri = NULL;
        for (int s = 0; s < 10; s++) { int d = uzaklik(yazim[k], sozluk[s], 0); if (d < en) { en = d; oneri = sozluk[s]; } }
        printf("  '%s' -> bunu mu demek istediniz: '%s' (uzaklik %d)\n", yazim[k], oneri, en);
    }
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined duzenleme.c -o duzenleme && ./duzenleme
  kitten -> sitting: 3 islem: [degistir k -> s] [degistir e -> i] [ekle g]
  algoritma -> logaritma: 3 islem: [degistir a -> l] [degistir l -> o] [degistir o -> a]
  printf -> pritnf: 2 islem: [degistir n -> t] [degistir t -> n]
  'retrun' -> bunu mu demek istediniz: 'return' (uzaklik 2)
  'swich' -> bunu mu demek istediniz: 'switch' (uzaklik 1)
  'pirntf' -> bunu mu demek istediniz: 'printf' (uzaklik 2)
  'incldue' -> bunu mu demek istediniz: 'include' (uzaklik 2)
  'whiel' -> bunu mu demek istediniz: 'while' (uzaklik 2)
```

(Tablo 64 × 64 sabit, kısa kelimeler için; geri izleme işlemleri sondan başa topluyor ve ters sırada yazdırıyor.)

Son beş satır, bir derleyicinin tanımsız bir isim gördüğünde yaptığı şey: clang `use of undeclared identifier 'pirntf'; did you mean 'printf'?` derken sembol tablosundaki (Ders 8.16) isimler arasında düzenleme uzaklığı en küçük olanı arıyor (ve uzaklık ismin uzunluğuna göre makul bir sınırın altındaysa öneriyor). Yazım denetleyicileri, DNA dizilimi hizalama (değiştirme maliyetleri harf çiftine göre değişen ağırlıklı sürümüyle) ve "yaklaşık" arama aynı tabloyu kullanıyor.

Bir gözlem: `printf -> pritnf` iki değiştirme gerektiriyor, ama insan gözü bunu **bir** hata görüyor: iki komşu harfin yer değiştirmesi. Yer değiştirmeyi de bir işlem sayan sürüm (Damerau–Levenshtein) bağıntıya dördüncü bir dal ekliyor (Alıştırma 2).

---

## 3. Matris zinciri çarpımı

$p \times q$ boyutlu bir matrisi $q \times r$ boyutlu bir matrisle çarpmak $pqr$ skaler çarpım (Ders 6.25). Matris çarpımı birleşmeli: $(AB)C = A(BC)$, sonuç aynı. Ama **maliyet** aynı değil. $A_1$: $10 \times 100$, $A_2$: $100 \times 5$, $A_3$: $5 \times 50$ ise:

- $(A_1 A_2) A_3$: $10 \cdot 100 \cdot 5 + 10 \cdot 5 \cdot 50 = 7\,500$.
- $A_1 (A_2 A_3)$: $100 \cdot 5 \cdot 50 + 10 \cdot 100 \cdot 50 = 75\,000$.

On kat fark. $n$ matrisin olası parantezleme sayısı Catalan sayısı (Ders 8.8, Alıştırma 4), üstel; hepsini denemek mümkün değil.

**Alt problem**: $m(i, j)$ = $A_i A_{i+1} \cdots A_j$ çarpımının en az maliyeti. (Ders 9.11'deki öneklerden farklı bir yapı: alt problemler **aralıklar**.)

**Bağıntı**, **son** çarpıma göre: zincir bir $k$ noktasında ikiye bölünüyor, $(A_i \cdots A_k)(A_{k+1} \cdots A_j)$; iki yarının en iyi maliyetleri artı son çarpımın maliyeti $p_{i-1} p_k p_j$. Bütün $k$'ların en küçüğü:

$$
m(i, j) = \min_{i \le k < j} \big( m(i, k) + m(k+1, j) + p_{i-1}\, p_k\, p_j \big), \qquad m(i, i) = 0.
$$

**Sıra**: bir aralık, kendisinden **kısa** aralıklara bakıyor. Satır satır değil, aralık **uzunluğuna** göre: önce uzunluğu 2 olanlar, sonra 3... Bu tür "aralık DP"si $O(n^3)$: $O(n^2)$ aralık, her biri $O(n)$ bölme noktası.

```c
/* Matris zinciri carpimi: A1 A2 ... An'yi hangi parantezleme ile carpmali? m[i][j] = A_i..A_j'nin en az skaler carpimi */
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long m[16][16]; static int s[16][16];

static long zincir(const int *p, int n) {             /* A_i boyutu p[i-1] x p[i], i = 1..n */
    for (int i = 1; i <= n; i++) m[i][i] = 0;
    for (int uz = 2; uz <= n; uz++)                    /* zincir uzunlugu: kisadan uzuna */
        for (int i = 1; i + uz - 1 <= n; i++) {
            int j = i + uz - 1; m[i][j] = -1;
            for (int k = i; k < j; k++) {              /* son carpim: (A_i..A_k)(A_k+1..A_j) */
                long q = m[i][k] + m[k + 1][j] + (long)p[i - 1] * p[k] * p[j];
                if (m[i][j] < 0 || q < m[i][j]) { m[i][j] = q; s[i][j] = k; }
            }
        }
    return m[1][n];
}
static void yaz(int i, int j) { if (i == j) { printf("A%d", i); return; } printf("("); yaz(i, s[i][j]); yaz(s[i][j] + 1, j); printf(")"); }

/* Gercek matrislerle: verilen parantezlemeyi uygula, sureyi olc */
typedef struct { int r, c; double *v; } Mat;
static Mat carp(Mat a, Mat b) {
    Mat c = { a.r, b.c, calloc((size_t)a.r * b.c, sizeof(double)) };
    for (int i = 0; i < a.r; i++) for (int k = 0; k < a.c; k++) { double x = a.v[(size_t)i * a.c + k];
        for (int j = 0; j < b.c; j++) c.v[(size_t)i * c.c + j] += x * b.v[(size_t)k * b.c + j]; }   /* ikj (Ders 7.26) */
    return c;
}
static Mat M[16];
static Mat uygula_en_iyi(int i, int j) {
    if (i == j) return M[i];
    Mat a = uygula_en_iyi(i, s[i][j]), b = uygula_en_iyi(s[i][j] + 1, j), c = carp(a, b);
    if (a.v != M[i].v) free(a.v); if (b.v != M[s[i][j] + 1].v) free(b.v);
    return c;
}
static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

int main(void) {
    int p1[] = { 10, 100, 5, 50 };                        /* CLRS: A1 10x100, A2 100x5, A3 5x50 */
    printf("%ld skaler carpim: ", zincir(p1, 3)); yaz(1, 3);
    printf("   (diger sira: A1(A2A3) = %d)\n", 100 * 5 * 50 + 10 * 100 * 50);
    int p[] = { 30, 35, 15, 5, 10, 20, 25 };              /* CLRS 15.2 ornegi, 6 matris */
    printf("%ld skaler carpim: ", zincir(p, 6)); yaz(1, 6); printf("\n");
    /* gercek: 5 matris, boyutlar buyuk */
    int q[] = { 2000, 10, 2000, 10, 2000, 10 };
    int n = 5; long en_iyi = zincir(q, n);
    printf("boyutlar 2000x10, 10x2000, 2000x10, 10x2000, 2000x10: en iyi %ld carpim: ", en_iyi); yaz(1, n); printf("\n");
    for (int i = 1; i <= n; i++) { M[i] = (Mat){ q[i - 1], q[i], malloc((size_t)q[i - 1] * q[i] * sizeof(double)) }; for (int t = 0; t < q[i - 1] * q[i]; t++) M[i].v[t] = (t % 7) * 0.5; }
    double t0 = simdi(); Mat r = uygula_en_iyi(1, n); double t1 = simdi();
    /* soldan saga: ((((A1A2)A3)A4)A5) */
    Mat x = carp(M[1], M[2]);
    for (int i = 3; i <= n; i++) { Mat y = carp(x, M[i]); free(x.v); x = y; }
    double t3 = simdi();
    long sol = 0; { long r0 = q[0]; for (int i = 1; i < n; i++) sol += r0 * q[i] * q[i + 1]; }
    printf("  en iyi sira %.4f s, soldan saga (%ld carpim) %.4f s, sonuclar ayni: %s\n", t1 - t0, sol, t3 - t1,
           r.v[0] == x.v[0] && r.v[(size_t)r.r * r.c - 1] == x.v[(size_t)x.r * x.c - 1] ? "evet" : "HAYIR");
    free(r.v); free(x.v); for (int i = 1; i <= n; i++) free(M[i].v);
}
```

`s[i][j]`, en iyi bölme noktasını saklıyor; `yaz` ondan parantezlemeyi geri kuruyor. `uygula_en_iyi` aynı parantezlemeyi gerçek matrislerle uyguluyor (çarpma Ders 7.26'nın cache dostu `ikj` sırasıyla).

```
$ cc -std=c11 -O2 -Wall -Wextra zincir.c -o zincir && ./zincir
7500 skaler carpim: ((A1A2)A3)   (diger sira: A1(A2A3) = 75000)
15125 skaler carpim: ((A1(A2A3))((A4A5)A6))
boyutlar 2000x10, 10x2000, 2000x10, 10x2000, 2000x10: en iyi 601000 carpim: (A1((A2A3)(A4A5)))
  en iyi sira 0.0003 s, soldan saga (160000000 carpim) 0.0494 s, sonuclar ayni: evet
```

(Sanitizer'lı derleme temiz.) İkinci satır CLRS'nin altı matrislik örneği, aynı cevap. Son satırda boyutlar "ince-geniş" sırayla değişiyor: soldan sağa çarpmak her adımda $2000 \times 2000$'lik ara matrisler üretiyor (160 milyon çarpım), en iyi sıra hep küçük matrisleri önce çarpıyor ($10 \times 10$'luk ara sonuçlar, 601 bin çarpım): **266 kat** az iş ve ölçülen süre 0.3 ms'ye karşı 49 ms. Sonuç aynı.

Derleyiciler ve sayısal kütüphaneler bunu gerçekten yapıyor: NumPy'nin `multi_dot`'u ve Eigen'in ifade şablonları (Ders 18.20) matris zincirlerini bu DP ile yeniden sıralıyor. Aynı "ilişkisel ifadeyi en ucuz sırayla değerlendir" sorusu veritabanlarının sorgu optimizasyonunda (hangi tabloları hangi sırayla birleştirmeli) da çıkıyor, ve orada da DP ile çözülüyor (System R, 1979).

---

## Alıştırmalar

**1** – Sırt çantası tablosunu tek bir satıra indir: $T[w]$, $w$'yi **büyükten küçüğe** gezerek. Neden küçükten büyüğe gezmek yanlış olur? Küçükten büyüğe gezilen sürüm hangi farklı problemi çözer?

**2** – Damerau–Levenshtein: iki **komşu** karakterin yer değiştirmesini tek bir işlem say. Bağıntıya hangi dal eklenir? `printf -> pritnf` uzaklığı kaç olur?

**3** – Düzenleme uzaklığı tablosunun sadece köşegene yakın bir bandını doldurmak: iki string arasındaki uzaklığın en fazla $k$ olduğu biliniyorsa (ya da sadece $k$'dan küçük olup olmadığı soruluyorsa), $|i - j| > k$ olan hücrelere neden hiç bakmaya gerek yok? Maliyet ne olur?

**4** – Matris zinciri problemini açgözlü bir kuralla çözmeye çalış: "her adımda, en ucuz komşu çarpımı yap". Bu kural Bölüm 3'teki 3 matrislik örnekte doğru çalışır mı? 4 matrislik bir karşı örnek bulabilir misin?

**5** – **Çubuk kesme**: $n$ cm'lik bir çubuk; $i$ cm'lik bir parçanın satış fiyatı $f_i$. Çubuğu parçalara bölerek toplam geliri en büyük yap. Alt problemi ve bağıntıyı yaz. $f = (1, 5, 8, 9, 10, 17, 17, 20)$, $n = 8$ için cevap ne?

<details>
<summary>Cevaplar</summary>

**1** – Tek satırda `T[w] = max(T[w], v_i + T[w - w_i])`. $w$ büyükten küçüğe giderse, `T[w - w_i]` henüz bu eşya için **güncellenmemiş**, yani bir önceki satırın değeri: tam istenen $T(i-1, w - w_i)$. Küçükten büyüğe giderse `T[w - w_i]` bu turda zaten güncellenmiş olabilir, yani $i$. eşyayı zaten içeren bir değer; eşya ikinci, üçüncü kez alınabilir. Bu, **sınırsız** sırt çantası problemini (her eşyadan istediğin kadar) çözer: Ders 9.10'daki madeni para problemi tam olarak bu, değeri "−1 para" saymakla.

**2** – Dördüncü dal: $i, j \ge 2$, $x_{i-1} = y_{j-2}$ ve $x_{i-2} = y_{j-1}$ ise $D(i, j) = \min(\dots, D(i-2, j-2) + 1)$. `printf -> pritnf`: `nt` ↔ `tn` tek bir yer değiştirme, uzaklık 1. (Bu, "en uygun dizi hizalama" sürümü; daha genel, aynı karakterleri birden çok kez düzenlemeye izin veren sürüm biraz daha karmaşık bir bağıntı gerektiriyor.)

**3** – $D(i, j) \ge |i - j|$: uzunluk farkı kadar ekleme ya da silme her durumda şart. $|i - j| > k$ olan bir hücrenin değeri zaten $k$'dan büyük; optimal yol oradan geçmiyorsa uzaklık $\le k$ olabilir, ama oradan geçen her yol $> k$ maliyetli. Dolayısıyla köşegenin iki yanında $k$ genişliğinde bir bant yeter: $O(k \cdot \min(n, m))$ zaman. Bandın dışı sonsuz kabul ediliyor. Yazım denetleyicilerinde $k = 2$ civarı; sözlükteki her kelimeyle $O(k \cdot \text{uzunluk})$ karşılaştırma. Ukkonen (1985) bunu $k$'yı bilmeden, $k$'yı 1, 2, 4, ... diye büyüterek $O(D \cdot n)$'e indirdi; Ders 9.11'de bahsedilen Myers'ın diff algoritmasıyla aynı fikir.

**4** – 3 matrislik örnekte en ucuz komşu çarpım $A_1 A_2$ (5000, $A_2 A_3$'ün 25 000'ine karşı); sonra 2500: toplam 7500, doğru. Karşı örnek: $A_1$: $10 \times 10$, $A_2$: $10 \times 1$, $A_3$: $1 \times 10$, $A_4$: $10 \times 100$ ($p = 10, 10, 1, 10, 100$). Komşu çarpım maliyetleri: $A_1A_2 = 100$, $A_2A_3 = 100$, $A_3A_4 = 1000$. Açgözlü $A_1A_2$'yi seçebilir ($10 \times 1$), sonra $(A_1A_2)A_3 = 100$ ($10 \times 10$), sonra $\cdot A_4 = 10\,000$: toplam 10 200. Optimal: $(A_1 A_2)(A_3 A_4)$: $100 + 1000 + 10 \cdot 1 \cdot 100 = 2\,100$. Açgözlü, büyük son çarpımın boyutlarını hiç düşünmüyor. (DP programına bu boyutları vererek kontrol edilebilir.)

**5** – $r(n)$ = $n$ cm'lik çubuğun en büyük geliri; ilk kesilen parçanın uzunluğu $i$'ye göre: $r(n) = \max_{1 \le i \le n} (f_i + r(n - i))$, $r(0) = 0$. $O(n^2)$. Verilen fiyatlarla: $r(1..8) = 1, 5, 8, 10, 13, 17, 18, 22$. $r(8) = 22$: $2 + 6$ cm ($5 + 17$). (CLRS 15.1'in örneği.) Bu, sınırsız sırt çantasının bir hali: her uzunluktaki parçadan istenildiği kadar.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 15.1 (çubuk kesme), 15.2 (matris zinciri), Problem 15-5 (düzenleme uzaklığı); Bölüm 16.2 (0/1 ve kesirli sırt çantası).
- Vladimir Levenshtein, "Binary codes capable of correcting deletions, insertions, and reversals", *Soviet Physics Doklady* 10(8), 1966.
- Robert Wagner ve Michael Fischer, "The String-to-String Correction Problem", *Journal of the ACM* 21(1), 1974.
- Patricia Selinger ve ark., "Access Path Selection in a Relational Database Management System", *SIGMOD* 1979: sorgu optimizasyonunda DP.
- Jon Kleinberg ve Éva Tardos, *Algorithm Design*, Bölüm 6: dinamik programlama.

**Sıradaki ders:** Dinamik programlama 3: ağaç üzerinde. Ağaç örtme ile optimal komut seçimi (BURS fikrine hazırlık).
