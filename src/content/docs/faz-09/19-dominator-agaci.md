---
title: "9.19 Dominator ağacı"
description: "Kontrol akış grafında 'her yol bu bloktan geçer mi?' sorusu: dominatörler, anında dominatör ve dominatör ağacı; Cooper–Harvey–Kennedy'nin ters sonek sırada çalışan yinelemeli algoritması ve iki düğümün ortak dominatörünü ağaçta yukarı yürüyerek bulan kesiş fonksiyonu; doğrulama için bit kümeleriyle saf veri akışı denklemleri; tanımdan (bloğu silince erişilemezlik) 2000 rastgele CFG'de birebir kontrol; 1 milyon bloklu CFG'de 0.37 s ve 4 tur; geri kenarlar ve döngü başlıkları; SSA'nın φ düğümleri için dominans sınırları; Lengauer–Tarjan'a bakış."
---

Derleyici bir fonksiyonu **temel bloklara** ayırıyor: içinde dallanma olmayan, sadece başından girilip sonundan çıkılan komut dizileri. Bloklar arasındaki atlamalar bir yönlü graf oluşturuyor: **kontrol akış grafı** (CFG, control flow graph). Faz 16'daki optimizasyonların neredeyse hepsi bu graf üzerinde çalışıyor, ve en temel sorulardan biri: **giriş bloğundan bir B bloğuna giden her yol, A bloğundan geçer mi?** Cevap evetse "A, B'yi **domine eder**". Bu ilişki döngüleri bulmanın (Bölüm 4), kodu güvenli bir şekilde taşımanın ("bu hesabı döngünün dışına çıkarabilir miyim?") ve modern derleyicilerin ara temsili **SSA** formunu kurmanın (Bölüm 5) temeli.

---

## 1. Tanımlar

Giriş bloğu $g$ olan bir CFG'de:

- $d$, $v$'yi **domine eder** ($d \;\text{dom}\; v$): $g$'den $v$'ye **her** yol $d$'den geçiyor. Her blok kendisini domine eder; $g$ her şeyi domine eder.
- $d$, $v$'yi **kesin** domine eder: $d \;\text{dom}\; v$ ve $d \ne v$.
- $v$'nin **anında dominatörü** $\text{idom}(v)$: $v$'yi kesin domine edenlerin içinde $v$'ye **en yakın** olan; $v$'yi kesin domine eden diğer her blok $\text{idom}(v)$'yi de domine ediyor.

Her blok ($g$ hariç) tek bir anında dominatöre sahip, ve $v \to \text{idom}(v)$ kenarları bir ağaç oluşturuyor: kökü $g$ olan **dominatör ağacı**. $d$, $v$'yi domine ediyor ancak ve ancak $d$ ağaçta $v$'nin atasıysa. Bütün dominans bilgisi tek bir `idom` dizisinde.

Örnek fonksiyon:

```c
int f(int n) { int s = 0; for (int i = 0; i < n; i++) { if (i % 2) s += i; else s -= 1; } return s; }
```

Blokları: `giris` (`s = 0; i = 0`), `kosul` (`i < n`?), `govde` (`i % 2`?), `tek` (`s += i`), `cift` (`s -= 1`), `artir` (`i++`, `kosul`'a dön), `donus` (`return s`).

Kenarlar: `giris → kosul`, `kosul → govde` (döngüye gir), `kosul → donus` (döngüden çık), `govde → tek`, `govde → cift`, `tek → artir`, `cift → artir`, ve döngünün geri dönüşü `artir → kosul`.

---

## 2. Kod

```c
/* Dominator agaci: Cooper-Harvey-Kennedy (2001) ve kontrol icin saf kume yinelemesi. Dominans sinirlari (SSA icin). */
#include <stdint.h>
#include <stdio.h>
#include "graf.h"

/* Ters sonek sira (reverse postorder, RPO): girisden DFS; bir dugum, ardillarinin cogundan once gelir. */
static int rpo_hesapla(const Graf *g, int giris, int *rpo, int *sira_no) {
    int n = g->n, *renk = calloc(n, sizeof(int)), *yig = malloc(n * sizeof(int)), *yer = malloc(n * sizeof(int)), tp = 0, k = 0;
    int *son = malloc(n * sizeof(int));
    for (int v = 0; v < n; v++) sira_no[v] = -1;
    yig[tp++] = giris; renk[giris] = 1; yer[giris] = g->ofset[giris];
    while (tp) { int u = yig[tp - 1];
        if (yer[u] < g->ofset[u + 1]) { int v = g->hedef[yer[u]++]; if (!renk[v]) { renk[v] = 1; yer[v] = g->ofset[v]; yig[tp++] = v; } }
        else { son[k++] = u; tp--; } }
    for (int i = 0; i < k; i++) { rpo[i] = son[k - 1 - i]; sira_no[rpo[i]] = i; }   /* sonek sirasinin tersi */
    free(renk); free(yig); free(yer); free(son);
    return k;                                                   /* girisden ulasilabilen dugum sayisi */
}

/* CHK: idom[v] = v'nin aninda dominatoru. Iki dugumun ortak dominatoru: agacta yukari yuru, RPO numarasi kucuk olan once. */
static int kesis(const int *idom, const int *sira_no, int a, int b) {
    while (a != b) {
        while (sira_no[a] > sira_no[b]) a = idom[a];
        while (sira_no[b] > sira_no[a]) b = idom[b];
    }
    return a;
}
static int tur_sayisi;
static void chk(const Graf *g, const Graf *ters, int giris, int *idom) {
    int n = g->n, *rpo = malloc(n * sizeof(int)), *sira_no = malloc(n * sizeof(int));
    int k = rpo_hesapla(g, giris, rpo, sira_no);
    for (int v = 0; v < n; v++) idom[v] = -1;
    idom[giris] = giris;
    int degisti = 1; tur_sayisi = 0;
    while (degisti) {                                           /* sabit noktaya kadar (Ders 9.21); RPO'da genelde 2-3 tur */
        degisti = 0; tur_sayisi++;
        for (int i = 1; i < k; i++) {
            int b = rpo[i], yeni = -1;
            for (int j = ters->ofset[b]; j < ters->ofset[b + 1]; j++) {   /* islenmis ilk oncul, sonra digerleriyle kesis */
                int p = ters->hedef[j];
                if (idom[p] < 0) continue;
                yeni = yeni < 0 ? p : kesis(idom, sira_no, p, yeni);
            }
            if (idom[b] != yeni) { idom[b] = yeni; degisti = 1; }
        }
    }
    free(rpo); free(sira_no);
}

/* SAF: Dom(giris) = {giris}; Dom(v) = {v} U (kesisim, butun onculler p: Dom(p)). Bit kumeleriyle (Ders 5.20). */
static void saf(const Graf *g, const Graf *ters, int giris, int *idom) {
    int n = g->n, W = (n + 63) / 64;
    uint64_t *D = malloc((size_t)n * W * 8);
    for (int v = 0; v < n; v++) for (int w = 0; w < W; w++) D[(size_t)v * W + w] = v == giris ? 0 : ~0ull;
    D[(size_t)giris * W + giris / 64] |= 1ull << (giris % 64);
    int degisti = 1;
    while (degisti) { degisti = 0;
        for (int v = 0; v < n; v++) { if (v == giris) continue;
            for (int w = 0; w < W; w++) {
                uint64_t x = ~0ull;
                for (int j = ters->ofset[v]; j < ters->ofset[v + 1]; j++) x &= D[(size_t)ters->hedef[j] * W + w];
                if (w == v / 64) x |= 1ull << (v % 64);
                if (x != D[(size_t)v * W + w]) { D[(size_t)v * W + w] = x; degisti = 1; }
            } } }
    /* idom(v): Dom(v) - {v} icinde, digerlerinin hepsi tarafindan domine edilen (en derin) */
    for (int v = 0; v < n; v++) { idom[v] = v == giris ? giris : -1; if (v == giris) continue;
        int en = -1, en_boy = -1;
        for (int d = 0; d < n; d++) if (d != v && (D[(size_t)v * W + d / 64] >> (d % 64) & 1)) {
            int boy = 0; for (int w = 0; w < W; w++) boy += __builtin_popcountll(D[(size_t)d * W + w]);
            if (boy > en_boy) { en_boy = boy; en = d; } }       /* en buyuk dominator kumesi = en derin */
        idom[v] = en; }
    free(D);
}

static Graf ters_kur(const Graf *g) {
    Kenar *k = malloc((g->m ? g->m : 1) * sizeof *k); int t = 0;
    for (int u = 0; u < g->n; u++) for (int i = g->ofset[u]; i < g->ofset[u + 1]; i++) k[t++] = (Kenar){ g->hedef[i], u };
    Graf r = graf_kur(g->n, k, g->m); free(k); return r;
}

#ifndef KUTUPHANE
/* int f(int n) { int s = 0; for (int i = 0; i < n; i++) { if (i % 2) s += i; else s -= 1; } return s; } */
static const char *ad[] = { "giris", "kosul", "govde", "tek", "cift", "artir", "donus" };
enum { GIRIS, KOSUL, GOVDE, TEK, CIFT, ARTIR, DONUS, N };
int main(void) {
    Kenar k[] = { {GIRIS,KOSUL}, {KOSUL,GOVDE}, {KOSUL,DONUS}, {GOVDE,TEK}, {GOVDE,CIFT}, {TEK,ARTIR}, {CIFT,ARTIR}, {ARTIR,KOSUL} };
    Graf g = graf_kur(N, k, 8), r = ters_kur(&g);
    int i1[N], i2[N];
    chk(&g, &r, GIRIS, i1); saf(&g, &r, GIRIS, i2);
    printf("aninda dominator (CHK, %d tur):\n", tur_sayisi);
    for (int v = 1; v < N; v++) printf("  idom(%s) = %s%s\n", ad[v], ad[i1[v]], i1[v] == i2[v] ? "" : "  (SAF FARKLI!)");
    /* geri kenar u -> h, h u'yu domine ediyorsa: dogal dongu basligi h */
    for (int u = 0; u < N; u++) for (int i = g.ofset[u]; i < g.ofset[u + 1]; i++) { int h = g.hedef[i], x = u;
        while (x != h && x != GIRIS) x = i1[x];
        if (x == h) printf("  geri kenar %s -> %s: dongu basligi %s\n", ad[u], ad[h], ad[h]); }
    /* dominans siniri: DF(b) = b'nin domine ettigi bir oncule sahip ama b'nin kesin domine etmedigi dugumler */
    printf("dominans sinirlari:\n");
    for (int b = 0; b < N; b++) {
        if (r.ofset[b + 1] - r.ofset[b] < 2) continue;          /* birlesme noktalari (en az 2 oncul) */
        for (int j = r.ofset[b]; j < r.ofset[b + 1]; j++) { int x = r.hedef[j];
            while (x != i1[b]) { printf("  DF(%s) icinde %s\n", ad[x], ad[b]); x = i1[x]; } }
    }
    graf_birak(&g); graf_birak(&r);
}
#endif
```

### Cooper–Harvey–Kennedy

Keith Cooper, Timothy Harvey ve Ken Kennedy'nin (2001) "basit, hızlı" algoritması. Gözlem: bir bloğun dominatörleri, bütün **öncüllerinin** dominatörlerinin ortak kısmı artı kendisi. Ağaç gösteriminde "ortak dominatörler" iki düğümün ağaçtaki **en yakın ortak atası**. `kesis(a, b)`, bu atayı bulmak için iki göstergeyi `idom` zinciri boyunca yukarı yürütüyor: her adımda RPO numarası **büyük** olanı (ağaçta daha derinde olan) bir yukarı çıkarıyor, karşılaşana kadar.

Bloklar **ters sonek sırada** (reverse postorder, RPO: DFS bitiş sırasının tersi, Ders 9.15) işleniyor. Döngüsüz bir CFG'de bu bir topolojik sıra: her blok, bütün öncüllerinden sonra geliyor ve tek bir tur yetiyor. Döngülerde geri kenarların kaynakları henüz işlenmemiş olabilir; o öncüller ilk turda atlanıyor (`idom[p] < 0`) ve algoritma hiçbir `idom` değişmeyene kadar turları tekrarlıyor: bir **sabit nokta** yinelemesi (Ders 9.21). RPO'da tur sayısı, CFG'nin döngü iç içeliğiyle ilgili küçük bir sayı (pratikte 2–3).

### Saf yöntem

Doğrulama için tanımın doğrudan çevirisi: her blok için dominatörlerin **kümesi**, bit kümeleri (Ders 5.20) olarak:

$$
\text{Dom}(g) = \{g\}, \qquad \text{Dom}(v) = \{v\} \cup \bigcap_{p \in \text{öncül}(v)} \text{Dom}(p),
$$

başta $g$ dışında her küme "her şey", ve denklemler değişiklik kalmayana kadar yineleniyor. $O(n^2 / 64)$ bellek ve tur başına iş: küçük CFG'ler için.

---

## 3. Örnek ve doğrulama

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined dom.c -o dom && ./dom
aninda dominator (CHK, 2 tur):
  idom(kosul) = giris
  idom(govde) = kosul
  idom(tek) = govde
  idom(cift) = govde
  idom(artir) = govde
  idom(donus) = kosul
  geri kenar artir -> kosul: dongu basligi kosul
dominans sinirlari:
  DF(artir) icinde kosul
  DF(govde) icinde kosul
  DF(kosul) icinde kosul
  DF(tek) icinde artir
  DF(cift) icinde artir
```

Okuma:

- `donus`'un anında dominatörü `kosul`: döngüye hiç girilmese de, kaç kez dönülse de `return`'e her yol `kosul`'dan geçiyor.
- `artir`'ın anında dominatörü `govde`, `tek` ya da `cift` **değil**: `artir`'a ikisinden de gelinebiliyor, ve ikisinin ortak dominatörü `govde`.
- İki yöntem aynı ağacı veriyor ve CHK 2 turda bitiyor (ilk turda `kosul`, `artir` henüz işlenmemişken sadece `giris` üzerinden hesaplanıyor; ikinci turda hiçbir şey değişmediği görülüyor).

Sonra daha sert testler:

```
$ cc -std=c11 -O2 -Wall olcum.c -o olcum && ./olcum
2000 kucuk CFG, butun (d, v) ciftleri: tanimla 0 uyusmazlik
n=3000: CHK 0.0003 s (3 tur), saf kume 0.006 s, farkli idom 0
n=1000000 m=2999999: CHK 0.371 s (4 tur), dominator agacinin derinligi 8
```

(Sanitizer'lı derleme temiz.)

- **Tanıma karşı**: 2000 rastgele küçük CFG'de (girişten her bloğa ulaşılabilen bir ağaç artı rastgele kenarlar, geri kenarlar dahil), **her** $(d, v)$ çifti için "$d$ silinince girişten $v$'ye BFS ile ulaşılamıyor mu?" sorusunun cevabı, dominatör ağacındaki atalık ilişkisiyle karşılaştırıldı. Hiç fark yok. Bu, algoritmayı onun kendi denklemlerinden **bağımsız** bir tanımla sınamak (Ders 9.1).
- **Saf yönteme karşı**: 3000 blokta aynı ağaç; CHK 20 kat hızlı.
- **1 milyon blok**: 0.37 s, 4 tur. (Gerçek fonksiyonlar bundan çok küçük; ama derleyiciler bunu her fonksiyon için, birçok optimizasyon geçişinde yeniden hesaplıyor.)

CHK'nin en kötü durumu $O(n^2)$ civarı. **Lengauer–Tarjan** (1979) algoritması $O(m\, \alpha(n))$'de çalışıyor: DFS ağacında her düğümün "yarı dominatörünü" hesaplayıp onlardan anında dominatörleri türetiyor, yol sıkıştırmalı bir union-find (Ders 8.18) yapısıyla. Çok daha karmaşık; Cooper ve arkadaşlarının ölçümünde gerçek CFG boyutlarında CHK genelde daha hızlı çıktı. LLVM uzun yıllar Lengauer–Tarjan'ın bir varyantını kullandı (bugün Semi-NCA); GCC de.

---

## 4. Döngüler

Bir $u \to h$ kenarında $h$, $u$'yu **domine ediyorsa** buna (dominans anlamında) **geri kenar** denir, ve $h$ bir **doğal döngünün başlığı** (header). Döngü, $u$'dan geriye doğru $h$'den geçmeden ulaşılabilen bloklar artı $h$. Örnekte `artir -> kosul`: döngünün gövdesi `kosul, govde, tek, cift, artir`.

Bu tanım Ders 9.14'teki DFS geri kenarından daha güçlü: başlık döngüdeki **her** bloğu domine ediyor, yani döngüye girmenin tek yolu başlıktan geçmek. Bu sayede derleyici döngüden önce yeni bir blok (**ön başlık**, preheader) açıp döngüde değişmeyen hesapları oraya taşıyabiliyor (loop-invariant code motion; Faz 16). İki girişli döngüler (Alıştırma 3) bu yapıya uymuyor; derleyiciler onları ayrıca ele alıyor.

---

## 5. SSA'ya hazırlık: dominans sınırları

**SSA** (static single assignment): her değişkene programda **tek bir** yerde atama yapılan ara temsil. `s` hem `tek`'te hem `cift`'te değiştiğinde, ikisi `s1` ve `s2` oluyor; `artir`'da hangisinin geçerli olduğu, gelinen yola bağlı: oraya bir **φ fonksiyonu** konuyor, `s3 = φ(s1, s2)`. Soru: φ'ler **nereye** konmalı? Gereğinden fazla φ ara temsili şişirir, eksik φ programı bozar.

Cytron ve arkadaşlarının (1991) cevabı **dominans sınırı**: $\text{DF}(b)$, $b$'nin bir öncülünü domine ettiği ama kendisini kesin domine etmediği bloklar; yani $b$'nin "etki alanının bittiği" ilk birleşme noktaları. Bir değişken $b$'de atanıyorsa, $\text{DF}(b)$'deki her bloğa bir φ gerekiyor (ve oraya konan φ da bir atama sayılıp işlem yineleniyor).

Kodun son kısmı DF'yi CHK makalesindeki yöntemle hesaplıyor: en az iki öncüllü her $b$ bloğu için her öncülden `idom` zinciri boyunca $\text{idom}(b)$'ye kadar yürü; yoldaki her bloğun DF'sine $b$ girer. Örnekte:

- $\text{DF}(\texttt{tek}) = \text{DF}(\texttt{cift}) = \{\texttt{artir}\}$: `s` iki dalda atanıyor, `artir`'a φ.
- $\text{DF}(\texttt{artir}) = \text{DF}(\texttt{govde}) = \text{DF}(\texttt{kosul}) = \{\texttt{kosul}\}$: döngüde değişen `i` ve `s` için döngü başlığına φ (bir değer `giris`'ten, bir değer `artir`'dan geliyor).

Faz 16'da SSA'ya dönüşümü bu iki fonksiyonla, `idom` ve DF ile kuracağız.

---

## Alıştırmalar

**1** – `if (a) x = 1; else x = 2; y = x;` için CFG'yi çiz (dört blok: koşul, then, else, birleşme). Her bloğun anında dominatörü ne? Birleşme bloğunun dominans sınırı? φ nereye konmalı?

**2** – **Post-dominatörler**: $d$, $v$'yi post-domine eder: $v$'den **çıkışa** giden her yol $d$'den geçiyor. Bunu bu dersteki kodla nasıl hesaplarsın? Örnekteki fonksiyonda `artir`'ın anında post-dominatörü ne? (Derleyicide "kontrol bağımlılığı" bu ilişkiyle tanımlanıyor.)

**3** – İki girişli bir döngü: `giris → A`, `giris → B`, `A → B`, `B → A`, `A → çıkış`. `A` ile `B` arasındaki döngünün bir başlığı (döngüdeki her bloğu domine eden) var mı? DFS geri kenarı nerede? Böyle CFG'lere ne denir, C'de nasıl ortaya çıkar?

**4** – Bölüm 5'teki kurala göre, örnekte `i` değişkeni hangi bloklarda atanıyor ve φ'leri nereye konmalı? `s` için tam listeyi (φ'lerin kendisinin de yeni atamalar olduğunu hesaba katarak) çıkar.

**5** – CHK'yi RPO yerine rastgele bir blok sırasıyla çalıştırsan sonuç değişir mi? Tur sayısı?

<details>
<summary>Cevaplar</summary>

**1** – Bloklar: `K` (koşul), `T` (then), `E` (else), `B` (birleşme). Kenarlar `K→T`, `K→E`, `T→B`, `E→B`. idom(T) = idom(E) = K; idom(B) = K (B'ye hem T'den hem E'den gelinebiliyor, ortak atası K). Dominans sınırları: $\text{DF}(T) = \text{DF}(E) = \{B\}$ ($T$, $B$'nin öncülünü (kendisini) domine ediyor ama $B$'yi değil); $\text{DF}(B) = \text{DF}(K) = \emptyset$. `x` hem T'de hem E'de atanıyor: $B$'ye `x3 = φ(x1, x2)`, ve `y = x3`.

**2** – Ters CFG'de (bütün kenarlar ters) çıkış bloğunu giriş olarak verip aynı `chk`'yi çalıştır. Birden çok çıkış varsa (birden çok `return`) hepsine bağlanan sanal bir çıkış bloğu ekle. Örnekte çıkış `donus`; ters grafta `donus`'tan `kosul`'a, oradan `artir` ve `giris`'e... `artir`'dan çıkışa giden her yol `kosul`'dan geçiyor: ipdom(artir) = kosul. Kontrol bağımlılığı: $Y$, $X$'e kontrol bağımlı, eğer $X$'in bir dalı $Y$'yi her zaman çalıştırıyor ama öbür dalı çalıştırmayabiliyorsa; post-dominatör ağacının dominans sınırlarıyla tam olarak hesaplanıyor (Ferrante, Ottenstein ve Warren, 1987).

**3** – `A`'yı domine eden: giris'ten `A`'ya doğrudan bir yol var (`giris→A`), yani `B` `A`'yı domine etmiyor; simetrik olarak `A` `B`'yi domine etmiyor. Döngüdeki her bloğu domine eden döngü içi bir blok yok: **doğal döngü değil**. DFS bir geri kenar buluyor (ilk keşfedilen hangisiyse, örneğin giris→A→B→A'da `B→A`), ama dominans anlamında geri kenar yok. Bu tür CFG'lere **indirgenemez** (irreducible) denir. C'de döngünün ortasına bir `goto` ile girmek, ya da `switch`'in `case`'lerinin bir döngünün içine dağıtılması (Duff's device) üretiyor. Derleyiciler böyle döngüleri ya düğüm kopyalayarak (bir girişi çoğaltıp) indirgenebilir hale getiriyor ya da döngü optimizasyonlarını atlıyor.

**4** – `i`: `giris`'te (`i = 0`) ve `artir`'da (`i++`). $\text{DF}(\texttt{artir}) = \{\texttt{kosul}\}$: `kosul`'a φ; φ kendisi `kosul`'da bir atama, $\text{DF}(\texttt{kosul}) = \{\texttt{kosul}\}$, zaten var. $\text{DF}(\texttt{giris}) = \emptyset$. Sonuç: `i` için sadece `kosul`'da `i2 = φ(i1, i3)`. `s`: `giris`, `tek`, `cift`'te. $\text{DF}(\texttt{tek}) \cup \text{DF}(\texttt{cift}) = \{\texttt{artir}\}$: `artir`'a φ. O yeni bir atama: $\text{DF}(\texttt{artir}) = \{\texttt{kosul}\}$: `kosul`'a φ. O da: $\text{DF}(\texttt{kosul}) = \{\texttt{kosul}\}$, zaten var. Sonuç: `s` için `artir` ve `kosul`'da birer φ. Bu "yinelemeli dominans sınırı" hesabı, Cytron ve arkadaşlarının φ yerleştirme algoritmasının tamamı.

**5** – Sonuç değişmez: algoritma bir sabit noktaya yakınsıyor ve o sabit nokta (en büyük çözüm) sıradan bağımsız; Ders 9.21'deki kafes kuramının bir sonucu. Ama tur sayısı artabilir: RPO'da her blok, döngüsüz bağımlılıklarının hepsi zaten işlenmişken işleniyor; rastgele sırada bilgi bir turda sadece bir adım yayılabiliyor, ve en kötü durumda tur sayısı CFG'nin derinliği kadar olabilir. Ayrıca `kesis` iki göstergenin RPO numaralarını karşılaştırıyor; o numaralar hâlâ RPO'dan gelmeli (sadece işleme **sırası** değişebilir), yoksa yukarı yürüme yanlış sonuç verir.

</details>

---

## Kaynaklar

- Keith Cooper, Timothy Harvey ve Ken Kennedy, "A Simple, Fast Dominance Algorithm", *Software: Practice and Experience* 4, 2001.
- Thomas Lengauer ve Robert Tarjan, "A Fast Algorithm for Finding Dominators in a Flowgraph", *ACM TOPLAS* 1(1), 1979.
- Ron Cytron, Jeanne Ferrante, Barry Rosen, Mark Wegman ve Kenneth Zadeck, "Efficiently Computing Static Single Assignment Form and the Control Dependence Graph", *ACM TOPLAS* 13(4), 1991.
- Keith Cooper ve Linda Torczon, *Engineering a Compiler* (2. baskı), Bölüm 9.2–9.3: dominans ve SSA.
- Alfred Aho, Monica Lam, Ravi Sethi ve Jeffrey Ullman, *Compilers* (2. baskı), Bölüm 9.6: döngüler, dominatörler ve doğal döngüler.

**Sıradaki ders:** Graf renklendirme. Açgözlü renklendirme, NP-tamlık ve Chaitin yaklaşımına hazırlık.
