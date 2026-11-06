---
title: "9.20 Graf renklendirme"
description: "Komşu iki düğüme aynı renk vermeden en az renkle boyamak: kromatik sayı ve NP-tamlık; açgözlü renklendirme, sıranın önemi ve 2 renkli bir taç grafında 8 renk kullanan kötü sıra; büyük dereceli önce ve DSatur sıraları; 300 rastgele grafta geri izlemeyle bulunan kesin sayıya göre karşılaştırma (doğal sıra 187 grafta fazla renk, DSatur 18); yazmaç ataması: canlılık aralıklarından girişim grafı, Chaitin–Briggs sadeleştirme ve seçme, 3 yazmaçta taşımasız, 2 yazmaçta iki değişkenin belleğe taşınması."
---

Bir derleyici, programın değişkenlerini işlemcinin sınırlı sayıdaki **yazmaçlarına** (register) yerleştirmek zorunda: RISC-V'de 31, x86-64'te 16 genel amaçlı yazmaç (Ders 7.4, 7.7). Aynı anda canlı (değeri daha sonra kullanılacak) iki değişken aynı yazmacı paylaşamaz. Değişkenleri düğüm, "aynı anda canlı" ilişkisini kenar yaparsan, problem bir **graf renklendirme** problemine dönüşüyor: komşu iki düğüme aynı rengi (yazmacı) verme, en fazla $k$ renk kullan. Bu ders renklendirmenin kendisini, neden zor olduğunu ve derleyicilerin kullandığı yaklaşımı (Chaitin, 1981) yazıyor. Faz 16'daki yazmaç ayırıcının iskeleti bu.

---

## 1. Problem

Yönsüz bir grafın **$k$-renklendirmesi**: her düğüme $\{0, \dots, k-1\}$'den bir renk, kenarın iki ucu farklı renkte. Bunu mümkün kılan en küçük $k$, grafın **kromatik sayısı** $\chi(G)$. Bir haritanın ülkelerini (komşu ülkeler farklı renk), bir sınav takvimini (ortak öğrencisi olan iki sınav aynı saatte olamaz) ya da frekans atamasını (yakın vericiler farklı frekans) planlamak aynı problem.

- $\chi \le 2$ mi? Graf iki parçalı mı demek; BFS ile doğrusal (Ders 9.14, Alıştırma 5).
- $\chi \le 3$ mü? **NP-tam** (Karp, 1972; Ders 9.22). Bilinen hiçbir algoritma bunu her graf için polinom zamanda cevaplamıyor, ve büyük ihtimalle yok.
- $\chi$'yi yaklaşık bulmak bile zor: $n^{1-\epsilon}$ çarpanından iyi bir yaklaşım NP-zor (Zuckerman, 2007).

Pratikte iki yol: küçük graflarda tam arama (geri izleme), büyüklerde iyi **sezgisel** yöntemler (Ders 9.23).

---

## 2. Kod

```c
/* Graf renklendirme: acgozlu (farkli siralarla), DSatur, kucuk graflarda kesin (geri izleme); Chaitin sadelestirmesi */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAKS 4096
typedef struct { int n; uint64_t *bit; int W; } YGraf;             /* yonsuz, bit matrisi (Ders 8.19) */
static YGraf yg(int n) { YGraf g = { n, NULL, (n + 63) / 64 }; g.bit = calloc((size_t)n * g.W, 8); return g; }
static void kenar(YGraf *g, int u, int v) { if (u == v) return; g->bit[(size_t)u * g->W + v / 64] |= 1ull << (v % 64); g->bit[(size_t)v * g->W + u / 64] |= 1ull << (u % 64); }
static int komsu(const YGraf *g, int u, int v) { return g->bit[(size_t)u * g->W + v / 64] >> (v % 64) & 1; }
static int derece(const YGraf *g, int u) { int d = 0; for (int w = 0; w < g->W; w++) d += __builtin_popcountll(g->bit[(size_t)u * g->W + w]); return d; }

/* ACGOZLU: verilen sirayla, her dugume komsularinin kullanmadigi en kucuk renk */
static int acgozlu(const YGraf *g, const int *sira, int *renk) {
    int en = 0; char kullanilan[MAKS];
    for (int v = 0; v < g->n; v++) renk[v] = -1;
    for (int i = 0; i < g->n; i++) {
        int v = sira[i]; memset(kullanilan, 0, en + 1);
        for (int u = 0; u < g->n; u++) if (renk[u] >= 0 && komsu(g, u, v)) kullanilan[renk[u]] = 1;
        int c = 0; while (kullanilan[c]) c++;
        renk[v] = c; if (c + 1 > en) en = c + 1;
    }
    return en;
}

/* DSATUR (Brelaz 1979): her adimda komsularinda EN COK FARKLI renk olan (doygunlugu en yuksek) dugumu renklendir */
static int dsatur(const YGraf *g, int *renk) {
    int n = g->n, en = 0;
    for (int v = 0; v < n; v++) renk[v] = -1;
    for (int adim = 0; adim < n; adim++) {
        int sec = -1, sec_doy = -1, sec_der = -1;
        for (int v = 0; v < n; v++) { if (renk[v] >= 0) continue;
            char gor[MAKS] = { 0 }; int doy = 0;
            for (int u = 0; u < n; u++) if (renk[u] >= 0 && komsu(g, u, v) && !gor[renk[u]]) { gor[renk[u]] = 1; doy++; }
            int dr = derece(g, v);
            if (doy > sec_doy || (doy == sec_doy && dr > sec_der)) { sec = v; sec_doy = doy; sec_der = dr; } }
        char kul[MAKS] = { 0 }; for (int u = 0; u < n; u++) if (renk[u] >= 0 && komsu(g, u, sec)) kul[renk[u]] = 1;
        int c = 0; while (kul[c]) c++; renk[sec] = c; if (c + 1 > en) en = c + 1;
    }
    return en;
}

/* KESIN: k renkle boyanabilir mi? Geri izleme (kucuk n icin) */
static int dene(const YGraf *g, int *renk, int v, int k) {
    if (v == g->n) return 1;
    for (int c = 0; c < k; c++) {
        int ok = 1; for (int u = 0; u < v; u++) if (renk[u] == c && komsu(g, u, v)) { ok = 0; break; }
        if (ok) { renk[v] = c; if (dene(g, renk, v + 1, k)) return 1; }
    }
    return 0;
}
static int kromatik(const YGraf *g) { int *r = malloc(g->n * sizeof *r), k = 1; while (!dene(g, r, 0, k)) k++; free(r); return k; }

static int gecerli(const YGraf *g, const int *renk) {
    for (int u = 0; u < g->n; u++) for (int v = u + 1; v < g->n; v++) if (komsu(g, u, v) && renk[u] == renk[v]) return 0;
    return 1;
}

#ifndef KUTUPHANE
static uint64_t xs = 88172645463325252ull;
static uint64_t rnd(void) { xs ^= xs << 13; xs ^= xs >> 7; xs ^= xs << 17; return xs; }
static int *der_global; static const YGraf *gg;
static int der_kars(const void *a, const void *b) { return der_global[*(const int *)b] - der_global[*(const int *)a]; }

int main(void) {
    /* 1) Kotu siralama: "taç" grafi (iki parcali, u_i -- v_j  i != j). 2 renk yeter, ama u0 v0 u1 v1 ... sirasi n renk kullanir. */
    int k = 8; YGraf t = yg(2 * k);
    for (int i = 0; i < k; i++) for (int j = 0; j < k; j++) if (i != j) kenar(&t, i, k + j);
    int s1[16], s2[16], renk[16];
    for (int i = 0; i < k; i++) { s1[2 * i] = i; s1[2 * i + 1] = k + i; s2[i] = i; s2[k + i] = k + i; }
    printf("tac grafi (16 dugum): sira u0 v0 u1 v1 ...: %d renk; sira u0..u7 v0..v7: %d renk; kesin: %d\n",
           acgozlu(&t, s1, renk), acgozlu(&t, s2, renk), kromatik(&t));
    /* 2) Rastgele kucuk graflar: siralar ve DSatur, kesin sonuca gore */
    int fazla[3] = { 0 }, top[4] = { 0 }; int T = 300;
    for (int r = 0; r < T; r++) {
        int n = 14; YGraf g = yg(n);
        for (int u = 0; u < n; u++) for (int v = u + 1; v < n; v++) if (rnd() % 2) kenar(&g, u, v);
        int sira[14], der[14]; for (int v = 0; v < n; v++) { sira[v] = v; der[v] = derece(&g, v); }
        der_global = der; gg = &g;
        int a = acgozlu(&g, sira, renk);                                   /* dogal sira */
        qsort(sira, n, sizeof *sira, der_kars); int b = acgozlu(&g, sira, renk);   /* buyuk dereceli once */
        int c = dsatur(&g, renk); if (!gecerli(&g, renk)) puts("GECERSIZ");
        int x = kromatik(&g);
        top[0] += a; top[1] += b; top[2] += c; top[3] += x;
        fazla[0] += a > x; fazla[1] += b > x; fazla[2] += c > x;
        free(g.bit);
    }
    printf("%d rastgele graf (14 dugum, p=0.5), ortalama renk: dogal %.2f, derece %.2f, DSatur %.2f, kesin %.2f\n",
           T, top[0] / (double)T, top[1] / (double)T, top[2] / (double)T, top[3] / (double)T);
    printf("  kesinden fazla renk kullandigi graf sayisi: dogal %d, derece %d, DSatur %d\n", fazla[0], fazla[1], fazla[2]);
    free(t.bit);
}
#endif
```

Graf, Ders 8.19'daki bit matrisi (yönsüz: iki yönde set ediliyor).

- **`acgozlu`**: düğümleri verilen sırayla gez, her birine komşularının kullanmadığı **en küçük** rengi ver. $\Delta$ en büyük derece ise en fazla $\Delta + 1$ renk (bir düğümün en fazla $\Delta$ komşusu var, $\Delta + 1$ renkten biri mutlaka boş). Ama kaç renk kullanacağı tamamen **sıraya** bağlı.
- **`dsatur`** (Brélaz, 1979): sıra baştan sabit değil; her adımda, komşularında **en çok farklı renk** bulunan (en "doymuş", seçenekleri en kısıtlı) düğüm renklendiriliyor. Kısıtlı olanı önce ele almak, açgözlü sezgisellerin klasik bir ilkesi.
- **`kromatik`**: kesin cevap; $k = 1, 2, \dots$ için geri izlemeyle (düğümleri sırayla dene, her birine geçerli bir renk ver, takılırsan geri dön) $k$-renklendirme ara. Üstel; 14 düğümde anında, 50 düğümde dakikalar.

```
$ cc -std=c11 -O2 -Wall -Wextra renk.c -o renk && ./renk
tac grafi (16 dugum): sira u0 v0 u1 v1 ...: 8 renk; sira u0..u7 v0..v7: 2 renk; kesin: 2
300 rastgele graf (14 dugum, p=0.5), ortalama renk: dogal 5.50, derece 5.05, DSatur 4.78, kesin 4.72
  kesinden fazla renk kullandigi graf sayisi: dogal 187, derece 93, DSatur 18
```

(Sanitizer'lı derleme temiz; DSatur'un ürettiği her renklendirme geçerlilik için kontrol ediliyor.)

**Sıranın gücü**: "taç grafı" ($u_i$ ile $v_j$ arasında, $i \ne j$ olduğu her çift için kenar; iki parçalı, $\chi = 2$). `u0 v0 u1 v1 ...` sırasıyla açgözlü her çifte yeni bir renk vermek zorunda kalıyor: **8 renk**. `u0..u7` önce gelince 2 renk. Açgözlü renklendirme en kötü sırada keyfi derecede kötü olabiliyor; ama her graf için **optimal** sonucu veren bir sıra da var (Alıştırma 3).

**Rastgele graflarda** (14 düğüm, her kenar %50): doğal sıra 300 grafın 187'sinde optimumdan fazla renk kullanıyor, büyük dereceli önce sırası 93'ünde, DSatur sadece 18'inde; ortalama renk sayısı DSatur'da kesin değerden sadece 0.06 fazla.

---

## 3. Yazmaç ataması

Düz (dallanmasız) bir kod parçası, her satırda bir değişken tanımlanıyor:

```c
a = oku();  b = oku();  c = a + b;  d = a * 2;  e = c - b;
f = d + e;  g = c * f;  h = g + e;  x = h + f;   /* x sonuc */
```

Her değişkenin **canlılık aralığı**: tanımlandığı satırdan son kullanıldığı satıra kadar. İki aralık çakışıyorsa değişkenler aynı anda canlı ve aynı yazmacı paylaşamaz: **girişim grafında** (interference graph) bir kenar. (Bir değişken bir satırda son kez kullanılıp aynı satırda başkası tanımlanıyorsa, ikisi aynı yazmacı kullanabilir: `d = a * 2` için `a` ve `d` çakışmıyor.)

**Chaitin'in sadeleştirmesi** (1981, IBM): derecesi $k$'dan **küçük** bir düğüm her zaman renklendirilebilir, komşuları ne renk alırsa alsın (en fazla $k - 1$ komşu, $k$ renk). O halde onu grafdan çıkar ve bir yığına it; bu, komşularının derecelerini azaltıyor ve yeni düğümleri "kolay" hale getiriyor. Graf boşalana kadar tekrarla. Sonra yığından ters sırayla çek ve her düğüme ilk boş rengi ver; çıkarıldığında $k$'dan az komşusu olduğu için her zaman bir renk var.

Derecesi $< k$ düğüm kalmazsa bir **taşıma** (spill) adayı seçilir: o değişken yazmaç yerine bellekte (yığında, Ders 7.11) tutulacak. Briggs'in iyileştirmesi (1994): adayı yine yığına it (`[c?]`), çünkü seçme aşamasında komşularından bazıları aynı rengi almış olabilir ve aday yine de renklenebilir; ancak gerçekten renk kalmazsa taşı.

```c
/* Yazmac atama icin Chaitin-Briggs: canlilik araliklari -> girisim grafi -> sadelestir / sec / tasir */
#define KUTUPHANE
#include "renk.c"

/* Duz bir kod parcasi: her satir bir degisken tanimliyor, bazilarini kullaniyor */
typedef struct { const char *tanim; const char *kullan[3]; } Komut;
static const Komut kod[] = {
    { "a", { NULL } },             /* a = oku()     */
    { "b", { NULL } },             /* b = oku()     */
    { "c", { "a", "b" } },         /* c = a + b     */
    { "d", { "a" } },              /* d = a * 2     */
    { "e", { "c", "b" } },         /* e = c - b     */
    { "f", { "d", "e" } },         /* f = d + e     */
    { "g", { "c", "f" } },         /* g = c * f     */
    { "h", { "g", "e" } },         /* h = g + e     */
    { "x", { "h", "f" } },         /* x = h + f  -> sonuc */
};
enum { K = 9 };
static const char *degisken[] = { "a", "b", "c", "d", "e", "f", "g", "h", "x" };
static int no(const char *s) { for (int i = 0; i < K; i++) if (!strcmp(degisken[i], s)) return i; return -1; }

static void ata(const YGraf *g, int k) {
    int n = g->n, *yigin = malloc(n * sizeof *yigin), tp = 0, *der = malloc(n * sizeof *der);
    char *cikti = calloc(n, 1), *aday = calloc(n, 1);
    for (int v = 0; v < n; v++) der[v] = derece(g, v);
    printf("k = %d yazmac:\n  sadelestir:", k);
    for (int adim = 0; adim < n; adim++) {
        int sec = -1;
        for (int v = 0; v < n; v++) if (!cikti[v] && der[v] < k) { sec = v; break; }   /* derecesi < k: kesin renklenir */
        if (sec < 0) {                                                                 /* takildi: tasima adayi sec (en yuksek derece) */
            for (int v = 0; v < n; v++) if (!cikti[v] && (sec < 0 || der[v] > der[sec])) sec = v;
            aday[sec] = 1; printf(" [%s?]", degisken[sec]);
        } else printf(" %s", degisken[sec]);
        cikti[sec] = 1; yigin[tp++] = sec;
        for (int u = 0; u < n; u++) if (!cikti[u] && komsu(g, u, sec)) der[u]--;
    }
    int *renk = malloc(n * sizeof *renk); for (int v = 0; v < n; v++) renk[v] = -1;
    printf("\n  sec:");
    while (tp) {                                                                     /* yigindan cek, ilk bos rengi ver */
        int v = yigin[--tp]; char kul[64] = { 0 };
        for (int u = 0; u < n; u++) if (renk[u] >= 0 && komsu(g, u, v)) kul[renk[u]] = 1;
        int c = 0; while (c < k && kul[c]) c++;
        if (c < k) { renk[v] = c; printf(" %s=r%d", degisken[v], c); }
        else printf(" %s=TASI(bellege)", degisken[v]);                               /* gercek tasima */
    }
    printf("\n");
    free(yigin); free(der); free(cikti); free(aday); free(renk);
}

int main(void) {
    int bas[K], son[K];                                       /* canlilik araligi: tanimdan son kullanima */
    for (int i = 0; i < K; i++) { bas[i] = son[i] = -1; }
    for (int s = 0; s < K; s++) { int t = no(kod[s].tanim); bas[t] = son[t] = s;
        for (int j = 0; j < 3 && kod[s].kullan[j]; j++) son[no(kod[s].kullan[j])] = s; }
    son[no("x")] = K;                                         /* sonuc fonksiyondan donuyor: sona kadar canli */
    YGraf g = yg(K);
    printf("canlilik araliklari:");
    for (int i = 0; i < K; i++) printf(" %s[%d,%d]", degisken[i], bas[i], son[i]);
    printf("\ngirisim kenarlari:");
    for (int i = 0; i < K; i++) for (int j = i + 1; j < K; j++)
        if (bas[i] < son[j] && bas[j] < son[i]) { kenar(&g, i, j); printf(" %s-%s", degisken[i], degisken[j]); }   /* araliklar cakisiyor */
    printf("\nkesin renk sayisi: %d\n", kromatik(&g));
    ata(&g, 3); ata(&g, 2);
    free(g.bit);
}
```

(`renk.c`'yi `KUTUPHANE` tanımlı olarak içeriyor; kullanılmayan fonksiyonları için `-Wno-unused-function`.)

```
$ cc -std=c11 -Wall -Wextra -Wno-unused-function -fsanitize=address,undefined chaitin.c -o chaitin && ./chaitin
canlilik araliklari: a[0,3] b[1,4] c[2,6] d[3,5] e[4,7] f[5,8] g[6,7] h[7,8] x[8,9]
girisim kenarlari: a-b a-c b-c b-d c-d c-e c-f d-e e-f e-g f-g f-h
kesin renk sayisi: 3
k = 3 yazmac:
  sadelestir: a b d c e f g h x
  sec: x=r0 h=r0 g=r0 f=r1 e=r2 c=r0 d=r1 b=r2 a=r1
k = 2 yazmac:
  sadelestir: h x [c?] a b d [e?] f g
  sec: g=r0 f=r1 e=TASI(bellege) d=r0 b=r1 a=r0 c=TASI(bellege) x=r0 h=r0
```

- **3 yazmaçla**: sadeleştirme hiç takılmıyor; dokuz değişken üç yazmaca sığıyor ve taşıma yok. Kesin kromatik sayı da 3 (en çok üç değişken aynı anda canlı: `c`, `d`, `e` gibi).
- **2 yazmaçla**: iki kez takılıyor ve en yüksek dereceli `c` ile `e` aday oluyor; seçme aşamasında ikisi de renk bulamıyor ve **belleğe taşınıyor**. Gerçek bir ayırıcı burada, taşınan değişkenler için `sw`/`ld` (sakla/yükle) komutları ekleyip canlılık aralıklarını kısaltır ve bütün işlemi baştan tekrarlar.

Düz kodda girişim grafı bir **aralık grafı** ve aralık graflarında renklendirme kolay: aralıkları başlangıç zamanına göre sırayla açgözlü boyamak optimal, ve kromatik sayı aynı anda canlı en fazla değişken sayısı (Alıştırma 1). Dallanmalı ve döngülü kodda girişim grafı keyfi olabiliyor (Chaitin, her grafın bir programın girişim grafı olarak ortaya çıkabileceğini gösterdi) ve problem NP-tam. Bu yüzden derleyiciler sezgisel yöntemlerle çalışıyor; SSA formundaki programlarda (Ders 9.19) ise girişim grafları **kordal** ve optimal renklendirme yine polinom zamanda (Hack, 2006). Bir de hızlı ama daha az iyi bir alternatif: **doğrusal tarama** (linear scan; Poletto ve Sarkar, 1999), JIT derleyicilerin tercihi.

---

## Alıştırmalar

**1** – Aralık graflarında, aralıkları **başlangıçlarına** göre sıralayıp açgözlü boyamanın, tam olarak "aynı anda açık en fazla aralık sayısı" kadar renk kullandığını göster. Bu, Bölüm 3'teki örnekte kaç? Neden bu sayı bir alt sınır?

**2** – Açgözlü renklendirmenin en fazla $\Delta + 1$ renk kullandığını gösterdik. Tam graf $K_n$ ve tek uzunluklu döngü bu sınıra ulaşıyor. Brooks teoremi, bunların **dışında** her bağlı grafın $\Delta$ renkle boyanabileceğini söylüyor. Bölüm 2'deki taç grafında $\Delta$ kaç, ve açgözlünün en kötü sırası bu sınıra göre ne kadar kötüydü?

**3** – Her graf için açgözlü renklendirmenin **optimal** sonuç verdiği bir sıra olduğunu göster. (İpucu: optimal bir renklendirmeyi al ve düğümleri renk sınıflarına göre sırala.) Bu, açgözlü renklendirmenin "doğru sırayı bulma" problemine indirgendiği anlamına geliyor; o problem neden kolay değil?

**4** – Bir sınav takvimi: 6 sınav, öğrenci listeleri çakışan çiftler `{M,F}`, `{M,K}`, `{F,K}`, `{K,T}`, `{T,E}`, `{E,B}`, `{B,K}`. En az kaç sınav saati gerekir? Kesin cevabı geri izlemeyle, ve DSatur'la bul.

**5** – Yazmaç ayırmada **birleştirme** (coalescing): `b = a` gibi bir kopya komutunda `a` ile `b` aynı yazmaca konursa komut silinebilir; girişim grafında iki düğümü tek düğüme birleştirmek. Bu neden tehlikeli olabilir (renklendirilebilirliği bozabilir)? Briggs'in "temkinli birleştirme" kuralı ne?

<details>
<summary>Cevaplar</summary>

**1** – Aralıkları başlangıca göre gezerken, bir aralık $I$ boyanırken onunla çakışan ve daha önce boyanmış aralıkların hepsi $I$'nin **başlangıç noktasını** içeriyor (daha önce başladılar ve $I$ başladığında hâlâ açıklar). O noktada açık olan aralık sayısı en fazla $\omega$ (aynı anda açık en fazla aralık sayısı), dolayısıyla $I$'nin en fazla $\omega - 1$ boyanmış komşusu var ve $\omega$ renkten biri boş. Toplam $\omega$ renk. Alt sınır: aynı noktayı içeren $\omega$ aralık birbirinin hepsiyle çakışıyor ($\omega$ düğümlü tam bir alt graf), ve onlar $\omega$'dan az renkle boyanamaz. Örnekte `b` $[1,4]$, `c` $[2,6]$ ve `d` $[3,5]$ aralıkları satır 3 ile 4 arasını, `c`, `d`, `e` $[4,7]$ satır 4 ile 5 arasını paylaşıyor; dört aralığın ortak noktası yok: $\omega = 3$, kesin sayı da 3.

**2** – Taç grafında her $u_i$, $i$ hariç bütün $v_j$'lere bağlı: derece $k - 1 = 7$, $\Delta = 7$. Açgözlü en fazla $\Delta + 1 = 8$ renk kullanabilir, ve en kötü sıra **tam olarak** bu sınıra ulaştı; ama $\chi = 2$. Yani $\Delta + 1$ sınırı ($\Delta$ ve Brooks da) bu grafta çok gevşek: kromatik sayı ile en büyük derece arasında çok büyük bir fark olabiliyor. İki parçalı graflarda $\chi = 2$ her zaman, derece ne olursa olsun.

**3** – Optimal bir $\chi$-renklendirmede düğümleri önce renk 0'dakiler, sonra renk 1'dekiler, ... diye sırala. İddia: açgözlü, optimal rengi $c$ olan her düğüme en fazla $c$ rengini verir. Tümevarım: bu düğüm işlenirken, daha önce işlenmiş komşularının optimal renkleri $c$'den **küçük** (aynı renk sınıfındakiler komşu değil, büyük renk sınıfları henüz işlenmedi), ve tümevarım hipoteziyle açgözlü onlara $c - 1$'den büyük renk vermedi. Yani $0..c$ arasında en fazla $c$ renk dolu, en az biri boş: açgözlünün rengi $\le c$. Toplam en fazla $\chi$ renk. Bu sıra var, ama onu bulmak optimal renklendirmeyi bilmeyi gerektiriyor; yani NP-zor problemi çözmüş olmak. Sıralama sezgiselleri (derece, DSatur, en küçük son) bu sıraya iyi bir tahminle yaklaşmaya çalışıyor.

**4** – Düğümler M, F, K, T, E, B. `M`, `F`, `K` bir üçgen: en az 3 renk. 3 yeter mi: `M`=0, `F`=1, `K`=2; `T` (`K`'ya komşu)=0; `E` (`T`'ye komşu)=1; `B` (`E` ve `K`'ya komşu)=0. Geçerli: **3 saat**. DSatur: en yüksek dereceli `K` (derece 4) ile başlıyor, sonra doygunluğa göre `M`, `F` (üçgeni kapatıyor, 3. renk), sonra kalanlar; o da 3 buluyor. Bu dersteki `kromatik` ve `dsatur` fonksiyonlarına bu 6 düğümlük grafı verince: `kesin 3, DSatur 3: M=1 F=2 K=0 T=1 E=0 B=1 gecerli=1`.

**5** – Birleştirilen düğümün komşuları, iki düğümün komşularının **birleşimi**; derecesi büyüyor ve daha önce $k$ renkle boyanabilen graf artık boyanamaz hale gelebiliyor (taşıma gerektirebiliyor). Kopyayı silmenin kazancı, bir değişkeni belleğe taşımanın bedelinden çok küçük. Briggs'in temkinli kuralı: $a$ ile $b$'yi ancak birleşik düğümün, derecesi $\ge k$ olan komşu sayısı $k$'dan **azsa** birleştir. O zaman sadeleştirme aşamasında birleşik düğüm, derecesi $< k$ olan komşuları çıkarıldıktan sonra kendisi de $< k$ dereceli olacak ve sadeleştirilebilecek: renklendirilebilirlik bozulmuyor. George'un kuralı ve "yinelemeli birleştirme" (George ve Appel, 1996) bu fikri daha da geliştiriyor.

</details>

---

## Kaynaklar

- Gregory Chaitin, Marc Auslander, Ashok Chandra, John Cocke, Martin Hopkins ve Peter Markstein, "Register Allocation via Coloring", *Computer Languages* 6(1), 1981.
- Preston Briggs, Keith Cooper ve Linda Torczon, "Improvements to Graph Coloring Register Allocation", *ACM TOPLAS* 16(3), 1994.
- Daniel Brélaz, "New Methods to Color the Vertices of a Graph", *Communications of the ACM* 22(4), 1979: DSatur.
- Richard Karp, "Reducibility Among Combinatorial Problems", *Complexity of Computer Computations*, 1972: 3-renklendirmenin NP-tamlığı.
- Massimiliano Poletto ve Vivek Sarkar, "Linear Scan Register Allocation", *ACM TOPLAS* 21(5), 1999.
- Sebastian Hack, Daniel Grund ve Gerhard Goos, "Register Allocation for Programs in SSA-Form", *CC* 2006.

**Sıradaki ders:** Sabit nokta yinelemesi. Worklist algoritması ve kafes üzerinde monoton fonksiyonun sabit noktasına yakınsama; veri akışı analizinin çekirdeği.
