---
title: "9.17 En kısa yol"
description: "Ağırlıklı graflarda en kısa yollar ve ortak işlem olan gevşetme: Dijkstra (negatif olmayan ağırlıklar, heap ile O((n + m) log n), açgözlü değişmez ve ispatı), Bellman–Ford (negatif ağırlıklar, n − 1 tur ve negatif döngü tespiti), Floyd–Warshall (bütün çiftler, O(n³) üçlü döngü); CLRS örneklerinde sonuçlar ve negatif kenarda Dijkstra'nın t için 2 yerine 6 bulması; 1 milyon düğümde Dijkstra ile Bellman–Ford'un aynı uzaklıkları vermesi, rastgele grafta Bellman–Ford'un sadece 18 turda bitmesi ve kötü sıralı bir yolda 20 000 tur sürmesi; Floyd–Warshall ile 500 kez Dijkstra'nın karşılaştırması."
---

Ders 9.14'teki BFS en kısa yolu **kenar sayısı** olarak buluyordu. Gerçek graflarda kenarların **ağırlıkları** var: bir yol ağında kilometreler, bir ağda gecikmeler, bir derleyicinin kod seçiminde maliyetler (Ders 9.13), bir finans grafında döviz kurlarının logaritmaları. En kısa yol, ağırlıklarının toplamı en küçük yol. Bu ders üç klasik algoritmayı yazıyor; her biri farklı bir varsayım altında en iyisi.

---

## 1. Gevşetme

Üç algoritmanın da çekirdeği aynı işlem. $d[v]$, $s$'den $v$'ye şu ana kadar bilinen en kısa yolun uzunluğu (başta $\infty$, $d[s] = 0$). Bir $u \to v$ kenarını, ağırlığı $w$, **gevşetmek** (relax):

```
eğer d[u] + w < d[v] ise:  d[v] = d[u] + w;  ebeveyn[v] = u
```

"$u$ üzerinden gitmek $v$ için şimdiye kadarkinden kısa mı?" $d[v]$ her zaman gerçek bir yolun uzunluğu (bir üst sınır) ve hiç artmıyor. Algoritmalar arasındaki tek fark, kenarları **hangi sırayla** ve **kaç kez** gevşettikleri. `ebeveyn` dizisi, Ders 9.14'teki gibi, en kısa yolları bir ağaç olarak tutuyor.

---

## 2. Kod

```c
/* En kisa yollar: Dijkstra (negatif olmayan agirliklar, heap), Bellman-Ford (negatif agirlik, negatif dongu tespiti),
   Floyd-Warshall (butun ciftler). Agirlikli CSR. */
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int u, v; long w; } AKenar;
typedef struct { int n, m; int *ofset, *hedef; long *agirlik; } AGraf;

static AGraf agraf_kur(int n, const AKenar *k, int m) {      /* Ders 8.19'un CSR'si, bir agirlik dizisiyle */
    AGraf g = { n, m, calloc(n + 1, sizeof(int)), malloc((m ? m : 1) * sizeof(int)), malloc((m ? m : 1) * sizeof(long)) };
    for (int i = 0; i < m; i++) g.ofset[k[i].u + 1]++;
    for (int u = 0; u < n; u++) g.ofset[u + 1] += g.ofset[u];
    int *yaz = malloc(n * sizeof(int)); memcpy(yaz, g.ofset, n * sizeof(int));
    for (int i = 0; i < m; i++) { int j = yaz[k[i].u]++; g.hedef[j] = k[i].v; g.agirlik[j] = k[i].w; }
    free(yaz); return g;
}
static void agraf_birak(AGraf *g) { free(g->ofset); free(g->hedef); free(g->agirlik); }

#define SONSUZ (LONG_MAX / 4)

/* DIJKSTRA: (uzaklik, dugum) ciftlerinin min-heap'i (Ders 8.12). Azaltma yerine yeni kayit ekle, eskiyi cekince atla. */
typedef struct { long d; int v; } HK;
static long gevseme;                                           /* istatistik */
static void dijkstra(const AGraf *g, int s, long *uzak, int *ebeveyn) {
    HK *h = malloc((g->m + 1) * sizeof *h); int hn = 0;
    char *kesin = calloc(g->n, 1);                             /* cekilen dugumun uzakligi KESIN: bir daha islenmez */
    for (int v = 0; v < g->n; v++) { uzak[v] = SONSUZ; ebeveyn[v] = -1; }
    uzak[s] = 0; h[hn++] = (HK){ 0, s };
    while (hn) {
        HK k = h[0], son = h[--hn]; int i = 0;                 /* en kucugu cek */
        for (;;) { int c = 2 * i + 1; if (c >= hn) break; if (c + 1 < hn && h[c + 1].d < h[c].d) c++; if (h[c].d >= son.d) break; h[i] = h[c]; i = c; }
        if (hn) h[i] = son;
        if (kesin[k.v]) continue;                              /* eski kayit: dugum daha kisa bir yolla zaten islendi */
        int u = k.v; kesin[u] = 1;
        for (int j = g->ofset[u]; j < g->ofset[u + 1]; j++) {
            int v = g->hedef[j]; long nd = uzak[u] + g->agirlik[j];
            if (!kesin[v] && nd < uzak[v]) {                   /* GEVSETME: u uzerinden daha kisa */
                uzak[v] = nd; ebeveyn[v] = u; gevseme++;
                int c = hn++; while (c > 0 && h[(c - 1) / 2].d > nd) { h[c] = h[(c - 1) / 2]; c = (c - 1) / 2; } h[c] = (HK){ nd, v };
            }
        }
    }
    free(h); free(kesin);
}

/* BELLMAN-FORD: butun kenarlari n-1 tur gevset. n. turda hala gevseyen varsa: negatif dongu. */
static int bf_tur;                                             /* istatistik: kac tur surdu */
static int bellman_ford(const AGraf *g, int s, long *uzak, int *ebeveyn) {
    for (int v = 0; v < g->n; v++) { uzak[v] = SONSUZ; ebeveyn[v] = -1; }
    uzak[s] = 0;
    for (int tur = 0; tur < g->n; tur++) {
        int degisti = 0; bf_tur = tur + 1;
        for (int u = 0; u < g->n; u++) {
            if (uzak[u] == SONSUZ) continue;
            for (int j = g->ofset[u]; j < g->ofset[u + 1]; j++) {
                int v = g->hedef[j];
                if (uzak[u] + g->agirlik[j] < uzak[v]) { uzak[v] = uzak[u] + g->agirlik[j]; ebeveyn[v] = u; degisti = 1; }
            }
        }
        if (!degisti) return 1;                                /* erken bitis: dengeye ulasti */
        if (tur == g->n - 1) return 0;                         /* n. turda degisiklik: negatif dongu */
    }
    return 1;
}

/* FLOYD-WARSHALL: D[i][j], ara dugumleri {0..k} ile sinirli en kisa yol; k'yi birer birer buyut. O(n^3). */
static void floyd(long *D, int n) {
    for (int k = 0; k < n; k++)
        for (int i = 0; i < n; i++) {
            long dik = D[(size_t)i * n + k]; if (dik == SONSUZ) continue;
            for (int j = 0; j < n; j++) { long y = dik + D[(size_t)k * n + j]; if (y < D[(size_t)i * n + j]) D[(size_t)i * n + j] = y; }
        }
}

#ifndef KUTUPHANE
static void yaz(const char *ad, const char *isim, const long *u, int n) {
    printf("  %-14s", ad); for (int v = 0; v < n; v++) { if (u[v] >= SONSUZ / 2) printf(" %c:-", isim[v]); else printf(" %c:%ld", isim[v], u[v]); } printf("\n");
}
int main(void) {
    const char *isim = "stxyz";
    enum { S, T, X, Y, Z };
    AKenar k1[] = { {S,T,10}, {S,Y,5}, {T,X,1}, {T,Y,2}, {X,Z,4}, {Y,T,3}, {Y,X,9}, {Y,Z,2}, {Z,S,7}, {Z,X,6} };   /* CLRS 24.6 */
    AGraf g = agraf_kur(5, k1, 10); long u[5]; int e[5];
    printf("negatif olmayan agirliklar:\n");
    dijkstra(&g, S, u, e); yaz("Dijkstra", isim, u, 5);
    bellman_ford(&g, S, u, e); yaz("Bellman-Ford", isim, u, 5);
    printf("  s -> x yolu (ters): x"); for (int v = X; e[v] >= 0; v = e[v]) printf(" <- %c", isim[e[v]]); printf("\n");
    long D[25]; for (int i = 0; i < 25; i++) D[i] = i % 6 ? SONSUZ : 0;      /* kosegen 0, gerisi sonsuz */
    for (int i = 0; i < 10; i++) D[k1[i].u * 5 + k1[i].v] = k1[i].w;
    floyd(D, 5);
    printf("  Floyd-Warshall, butun ciftler:\n");
    for (int i = 0; i < 5; i++) { printf("    %c:", isim[i]); for (int j = 0; j < 5; j++) printf(" %3ld", D[i * 5 + j]); printf("\n"); }
    agraf_birak(&g);

    AKenar k2[] = { {S,T,6}, {S,Y,7}, {T,X,5}, {T,Y,8}, {T,Z,-4}, {X,T,-2}, {Y,X,-3}, {Y,Z,9}, {Z,S,2}, {Z,X,7} };   /* CLRS 24.4 */
    g = agraf_kur(5, k2, 10);
    printf("negatif agirliklar:\n");
    dijkstra(&g, S, u, e); yaz("Dijkstra", isim, u, 5);
    int ok = bellman_ford(&g, S, u, e); yaz("Bellman-Ford", isim, u, 5); printf("  negatif dongu: %s\n", ok ? "yok" : "VAR");
    agraf_birak(&g);
    k2[5].w = -9;                                              /* x -> t'yi -9 yap: t -> x -> t dongusu 5 - 9 = -4 */
    g = agraf_kur(5, k2, 10);
    ok = bellman_ford(&g, S, u, e); printf("x -> t = -9 iken: negatif dongu %s\n", ok ? "yok" : "VAR");
    agraf_birak(&g);
}
#endif
```

### Dijkstra

Edsger Dijkstra (1959): ağırlıklar **negatif değilse**, uzaklığı kesinleşmemiş düğümler arasında $d$'si en küçük olanın uzaklığı **kesindir**. Onu kesinleştir, kenarlarını gevşet, tekrarla. "En küçük $d$'li düğüm" sorusu bir öncelik kuyruğu: Ders 8.12'nin heap'i. Ders 8.12'nin 5. bölümünde sözünü ettiğimiz `azalt` işlemi yerine burada daha basit bir yol seçildi: bir düğümün uzaklığı azalınca heap'e **yeni** bir kayıt ekleniyor, eski kayıt çekildiğinde düğüm zaten kesinleşmiş olduğu için atlanıyor ("tembel silme").

**Değişmez**: kesinleşmiş her düğümün $d$'si gerçek en kısa uzaklık. **İspat**: $u$, kesinleşecek bir sonraki düğüm olsun ve diyelim $d[u]$ yanlış: daha kısa bir yol $P$ var. $P$, $s$'den (kesin) başlıyor ve bir noktada kesin olmayan bir düğüme geçiyor; bu ilk kesin-olmayan düğüm $y$ olsun, öncülü $x$ kesin. $x$ kesinleşirken $x \to y$ gevşetildi, yani $d[y] \le$ ($P$'nin $y$'ye kadarki uzunluğu). Ağırlıklar negatif değil, yani $P$'nin $y$'den sonraki kısmı negatif değil: $d[y] \le |P| < d[u]$. Ama $u$, kesin olmayanlar arasında en küçük $d$'liydi: çelişki. (CLRS Teorem 24.6.) Bu bir açgözlü algoritma (Ders 9.10), ve açgözlü seçimin doğruluğu tam olarak "ağırlıklar negatif değil" varsayımına dayanıyor.

Maliyet: her kenar en fazla bir heap ekleme, her ekleme bir çekme: $O((n + m) \log n)$.

### Bellman–Ford

Bellman (1958) ve Ford (1956): bütün kenarları sırayla gevşet; bunu $n - 1$ kez tekrarla. Bir en kısa yol (negatif döngü yoksa) en fazla $n - 1$ kenarlı; $i$. turdan sonra en fazla $i$ kenarlı bütün en kısa yollar doğru bulunmuş oluyor (tümevarım). Ağırlıkların işaretine hiç bakılmıyor: **negatif ağırlıklar serbest**.

Bir tur hiç değişiklik yapmazsa uzaklıklar dengeye ulaşmıştır ve erken bitiliyor. $n$. turda hâlâ bir şey değişiyorsa, sonsuza kadar küçülebilen bir yol var: **negatif döngü**, ve "en kısa yol" tanımsız.

Maliyet: en kötü $O(nm)$.

### Floyd–Warshall

Bütün düğüm **çiftleri** arasındaki uzaklıklar (Floyd ve Warshall, 1962). Ders 6.6'daki Warshall'ın geçişli kapanış algoritmasının ağırlıklı hali, ve bir DP (Ders 9.11): $D_k[i][j]$, ara düğümleri $\{0, \dots, k\}$ ile sınırlı en kısa $i \to j$ yolu. $k$'yı eklemek ya yolu değiştirmiyor ya da yol $k$'dan geçiyor:

$$
D_k[i][j] = \min\big(D_{k-1}[i][j],\; D_{k-1}[i][k] + D_{k-1}[k][j]\big).
$$

Tek bir matris, yerinde güncellenerek (yerinde güncelleme $k$. satır ve sütunu değiştirmiyor); üç iç içe döngü, $O(n^3)$. Döngü sırası önemli: $k$ en dışta olmalı.

---

## 3. Küçük örnekler

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined enkisa.c -o enkisa && ./enkisa
negatif olmayan agirliklar:
  Dijkstra       s:0 t:8 x:9 y:5 z:7
  Bellman-Ford   s:0 t:8 x:9 y:5 z:7
  s -> x yolu (ters): x <- t <- y <- s
  Floyd-Warshall, butun ciftler:
    s:   0   8   9   5   7
    t:  11   0   1   2   4
    x:  11  19   0  16   4
    y:   9   3   4   0   2
    z:   7  15   6  12   0
negatif agirliklar:
  Dijkstra       s:0 t:6 x:4 y:7 z:2
  Bellman-Ford   s:0 t:2 x:4 y:7 z:-2
  negatif dongu: yok
x -> t = -9 iken: negatif dongu VAR
```

- **Negatif olmayan ağırlıklar** (CLRS Şekil 24.6): Dijkstra ve Bellman–Ford aynı uzaklıkları veriyor; $s \to x$ en kısa yolu $s \to y \to t \to x$ ($5 + 3 + 1 = 9$), doğrudan $s \to t$ (10) değil.
- **Negatif ağırlıklar** (CLRS Şekil 24.4; $t \to z = -4$, $x \to t = -2$, $y \to x = -3$): Bellman–Ford doğru ($t = 2$, yol $s \to y \to x \to t$, $7 - 3 - 2$). Dijkstra $t$'yi 6 olarak **kesinleştiriyor** (doğrudan $s \to t$), çünkü o an en küçük $d$ oydu; sonradan bulunan $s \to y \to x \to t$ yolu $-3$ ve $-2$'lik kenarlarla daha kısa, ama $t$ artık değişmiyor. $z$ de ondan yanlış hesaplanıyor. İspattaki "yolun geri kalanı negatif değil" adımı burada çöküyor.
- Floyd–Warshall'ın $s$ satırı Dijkstra'nın sonucuyla aynı; matris bütün çiftleri birden veriyor (örneğin $x$'ten $t$'ye 19: $x \to z \to s \to y \to t$, $4 + 7 + 5 + 3$).
- $x \to t$'yi $-9$ yapınca $t \to x \to t$ döngüsünün toplamı $5 - 9 = -4$: Bellman–Ford negatif döngüyü buluyor.

---

## 4. Ölçüm

Rastgele graflar (ağırlıklar 1–1000), iki algoritmanın sonuçları her düğüm için karşılaştırılıyor; Bellman–Ford'un kötü girdisi; ve bütün çiftler için Floyd–Warshall ile her düğümden bir Dijkstra:

```
$ cc -std=c11 -O2 -Wall olcum.c -o olcum && ./olcum
n= 100000 m= 500000: Dijkstra 0.013 s (144561 gevsetme), Bellman-Ford 0.015 s (15 tur), farkli uzaklik 0
n=1000000 m=5000000: Dijkstra 0.280 s (1445807 gevsetme), Bellman-Ford 0.183 s (18 tur), farkli uzaklik 0
yol, 20000 dugum: Dijkstra 0.0001 s, Bellman-Ford 0.314 s (20000 tur)
n=500 m=5000 butun ciftler: Floyd-Warshall 0.050 s, 500 kez Dijkstra 0.027 s, farkli 0
```

(Sanitizer'lı derleme temiz.)

- Üç algoritma her yerde aynı uzaklıkları buluyor.
- **Sürpriz**: 1 milyon düğümlü rastgele grafta Bellman–Ford Dijkstra'dan **hızlı**. Teori $O(nm)$ diyordu, ama erken bitiş sayesinde sadece 18 tur sürdü: rastgele bir grafın çapı küçük (Ders 9.14'te en uzak düğüm 9 adımdaydı) ve en kısa yollar az kenarlı. Her tur, CSR'yi baştan sona **ardışık** tarıyor (Ders 7.24); Dijkstra ise heap'te ve uzaklık dizisinde rastgele adreslere atlıyor. Gevşetme sayısı da az: 5 milyon kenarın sadece 1.4 milyonu bir uzaklığı iyileştirdi.
- **Kötü girdi**: bir yol, ama düğümler Bellman–Ford'un kenarları taradığı sıranın **tersine** dizilmiş. Her tur bilgiyi yol boyunca sadece bir adım ilerletebiliyor: tam $n$ tur, 0.31 s; Dijkstra 0.1 ms. Bellman–Ford'un en kötü durumu gerçek; ölçümde iyi çıkması girdinin şanslı olmasından. Pratik sürümler (SPFA; Bellman–Ford'u kuyrukla sadece değişen düğümlerden çalıştırmak) çoğu girdide çok hızlı ama en kötü durum yine $O(nm)$.
- **Bütün çiftler**: Floyd–Warshall $O(n^3) = 1.25 \cdot 10^8$ işlem, 500 Dijkstra $O(n \cdot m \log n)$; bu seyrek grafta Dijkstra iki kat hızlı. Floyd–Warshall yoğun graflarda ($m \approx n^2$), negatif kenarlarda (Dijkstra kullanılamazken) ve kodunun dört satır olmasıyla değerli.

| | Ağırlıklar | Tek kaynak / bütün çiftler | Zaman | Negatif döngü |
| --- | --- | --- | --- | --- |
| BFS (9.14) | Hepsi 1 | Tek kaynak | $O(n + m)$ | — |
| Dijkstra | $\ge 0$ | Tek kaynak | $O((n + m) \log n)$ | — |
| Bellman–Ford | Herhangi | Tek kaynak | $O(nm)$ | Tespit eder |
| DAG'da (9.15) | Herhangi | Tek kaynak | $O(n + m)$, topolojik sırayla tek tur | Döngü yok |
| Floyd–Warshall | Herhangi | Bütün çiftler | $O(n^3)$ | Tespit eder ($D[i][i] < 0$) |

---

## Alıştırmalar

**1** – Bölüm 3'teki negatif ağırlıklı örnekte Dijkstra'nın düğümleri hangi sırayla kesinleştirdiğini ve her adımda $d$ değerlerini izle. $t$ hangi anda 6 olarak kesinleşiyor, ve doğru yol ($s \to y \to x \to t$) o anda neden görülemiyor?

**2** – Bütün ağırlıklara aynı sabiti ekleyerek negatiflikten kurtulup Dijkstra kullanmak neden **yanlış**? Bir karşı örnek ver. (Doğru yöntem: Johnson'un yeniden ağırlıklandırması, Alıştırma 5.)

**3** – Bellman–Ford negatif döngü bulduğunda döngünün **kendisini** yazdır. $n$. turda gevşeyen bir $v$ düğümünden `ebeveyn` zincirini neden $n$ adım geri izlemek gerekiyor, sonra ne yapıyorsun?

**4** – **A\*** algoritması: Dijkstra'nın heap anahtarı $d[v]$ yerine $d[v] + h(v)$, $h(v)$ $v$'den hedefe kalan uzaklığın bir **tahmini**. Bir harita üzerinde $h$ olarak kuş uçuşu uzaklık neden işe yarıyor? $h$ hangi koşulu sağlamalı ki bulunan yol en kısa olsun?

**5** – **Johnson algoritması** (negatif kenarlı, seyrek, bütün çiftler): yeni bir $q$ düğümü ekle, her düğüme 0 ağırlıklı kenar; Bellman–Ford ile $h(v) = \text{uzak}(q, v)$ bul; her kenarı $w'(u, v) = w(u, v) + h(u) - h(v)$ ile yeniden ağırlıklandır. Neden $w' \ge 0$? Neden en kısa yollar değişmiyor? Toplam maliyet ne?

<details>
<summary>Cevaplar</summary>

**1** – Başta $d = (s{:}0, t{:}\infty, x{:}\infty, y{:}\infty, z{:}\infty)$. $s$ kesinleşiyor: $t = 6$, $y = 7$. En küçük $t$ (6): kesinleşiyor; $x = 6 + 5 = 11$, $y = \min(7, 14) = 7$, $z = 6 - 4 = 2$. En küçük $z$ (2): kesinleşiyor; $s$ kesin (atlanıyor), $x = \min(11, 9) = 9$. En küçük $y$ (7): $x = \min(9, 7 - 3) = 4$, $z$ kesin. En küçük $x$ (4): $t$ kesin olduğu için $x \to t$ ($4 - 2 = 2 < 6$) **gevşetilmiyor**. Son: $t = 6$, $z = 2$; doğrusu $t = 2$, $z = -2$. $t$, $y$ ve $x$ işlenmeden önce (2. adımda) kesinleşti, çünkü o anda en küçüktü; daha kısa yol sonradan, negatif kenarlarla bulundu ve iş işten geçmişti.

**2** – Sabit eklemek, **kenar sayısı** farklı yolları farklı miktarda uzatıyor: $k$ kenarlı bir yol $k \cdot c$ uzuyor. Örnek: $s \to a$ (−2), $a \to t$ (−2), ve $s \to t$ (−3). En kısa: $s \to a \to t$ (−4). Her kenara 3 ekle: $s \to a \to t$ = 1 + 1 = 2, $s \to t$ = 0. Artık doğrudan kenar daha kısa görünüyor: cevap yanlış. Johnson'un yeniden ağırlıklandırması bunu, her yolu **aynı** miktarda (sadece uç noktalara bağlı) değiştirerek önlüyor.

**3** – $n$. turda gevşeyen $v$, ya bir negatif döngünün üzerinde ya da bir negatif döngüden ulaşılabilen bir yolda. `ebeveyn` zincirini $n$ adım geri izlemek, zincirde mutlaka bir döngüye girmeyi garanti ediyor ($n$ adımda $n$ farklı düğüm görülemezse bir düğüm tekrar ediyor; güvercin yuvası, Ders 6.15); bu noktadaki düğüm $c$ kesinlikle döngünün üzerinde. Sonra $c$'den başlayıp $c$'ye geri dönene kadar `ebeveyn`'i izle: döngü (ters sırada). Döviz kurlarında bir **arbitraj** fırsatını bulmak bu: kenar ağırlıkları $-\log(\text{kur})$, ve çarpımı 1'den büyük bir döngü negatif toplamlı bir döngü.

**4** – $h(v)$, $v$'den hedefe gerçek uzaklığı **aşmamalı** (kabul edilebilir, admissible). Kuş uçuşu uzaklık, hiçbir yolun ondan kısa olamayacağı bir alt sınır: koşulu sağlıyor. A\*, hedefe doğru giden düğümleri önce işleyerek Dijkstra'nın her yöne eşit yayılmasını önlüyor ve çok daha az düğüm ziyaret ediyor. Ayrıca $h$ **tutarlıysa** ($h(u) \le w(u, v) + h(v)$ her kenar için; kuş uçuşu için üçgen eşitsizliği) bir düğüm kesinleşince bir daha açılmıyor, tam Dijkstra gibi. Aslında A\*, Dijkstra'nın Alıştırma 5'teki yeniden ağırlıklandırmayla ($w'(u,v) = w(u,v) - h(u) + h(v)$) çalıştırılmış hali. $h = 0$ ise Dijkstra'nın kendisi.

**5** – $h(v) = \text{uzak}(q, v)$ için üçgen eşitsizliği: $h(v) \le h(u) + w(u, v)$ (en kısa yol tanımı gereği), yani $w'(u, v) = w(u, v) + h(u) - h(v) \ge 0$. Bir $s \to t$ yolu boyunca $w'$'lerin toplamı **teleskoplaşıyor**: $\sum w' = \sum w + h(s) - h(t)$; her $s \to t$ yolu aynı $h(s) - h(t)$ kadar değişiyor, dolayısıyla en kısa yol aynı yol. Sonra her düğümden Dijkstra (artık $w' \ge 0$) ve sonuçları $-h(s) + h(t)$ ile geri düzelt. Maliyet: bir Bellman–Ford $O(nm)$ + $n$ Dijkstra $O(n (n + m) \log n)$; seyrek graflarda Floyd–Warshall'ın $O(n^3)$'ünden iyi. Bellman–Ford negatif döngü bulursa bütün çiftler için de "tanımsız" demek gerekiyor.

</details>

---

## Kaynaklar

- Edsger Dijkstra, "A Note on Two Problems in Connexion with Graphs", *Numerische Mathematik* 1, 1959.
- Richard Bellman, "On a Routing Problem", *Quarterly of Applied Mathematics* 16(1), 1958.
- Robert Floyd, "Algorithm 97: Shortest Path", *Communications of the ACM* 5(6), 1962.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 24 (tek kaynak) ve 25 (bütün çiftler, Johnson).
- Peter Hart, Nils Nilsson ve Bertram Raphael, "A Formal Basis for the Heuristic Determination of Minimum Cost Paths", *IEEE Transactions on Systems Science and Cybernetics* 4(2), 1968: A\*.

**Sıradaki ders:** Minimum yayılan ağaç. Kruskal (union-find ile) ve Prim.
