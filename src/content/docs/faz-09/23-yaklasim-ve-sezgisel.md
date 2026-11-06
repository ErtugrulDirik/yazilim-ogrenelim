---
title: "9.23 Yaklaşım ve sezgisel yöntemler"
description: "NP-zor bir problemle karşılaşınca ne yapılır: gezgin satıcı problemi üzerinde garantili yaklaşım (MST'yi önek sırayla gezip üçgen eşitsizliğiyle 2 × OPT sınırı), açgözlü kurucu sezgisel (en yakın komşu), yerel arama (2-opt) ve yerel minimumlardan kaçmak için benzetimli tavlama; 12 şehirde Held–Karp DP ile bulunan kesin optimuma göre oranlar (2-opt ortalama %1.5–2 fazla, tavlama 20 örneğin hepsinde optimum), 2000 şehirde MST alt sınırına göre; tavlama sıcaklığının etkisi; derleyicilerin satır içi açma, döngü açma ve planlamada sezgisel kararları."
---

Ders 9.22'nin sonucu kötümserdi: birçok önemli problemin en kötü durumda verimli bir kesin çözümü büyük ihtimalle yok. Ama pratikte bu problemler her gün çözülüyor: kargo şirketleri rotalarını planlıyor, çip tasarımcıları milyarlarca transistörü yerleştiriyor, derleyiciler yazmaç ayırıyor. Hile, ya **optimum yerine ona yakın** bir cevaba razı olmak, ya da **garantiden vazgeçip** genelde iyi çalışan bir yöntem kullanmak. Bu ders iki yolu da tek bir klasik problem üzerinde ölçüyor: **gezgin satıcı problemi** (TSP): $n$ şehri her birini bir kez ziyaret edip başlangıca dönen **en kısa** tur.

İki tür yöntem var:

- **Yaklaşım algoritması** (approximation algorithm): polinom zamanlı ve sonucu optimumun en fazla $\rho$ katı olduğu **ispatlanmış**. $\rho$ yaklaşım oranı.
- **Sezgisel yöntem** (heuristic): hızlı ve pratikte iyi, ama hiçbir garantisi yok.

---

## 1. Kod

```c
/* Gezgin satici (duzlemde noktalar): en yakin komsu, MST ile 2-yaklasim, 2-opt yerel arama, benzetimli tavlama,
   kucuk n icin kesin cozum (Held-Karp DP, O(2^n n^2)) */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int n; static double *X, *Y;
static double uz(int a, int b) { double dx = X[a] - X[b], dy = Y[a] - Y[b]; return sqrt(dx * dx + dy * dy); }
static double tur_uzunlugu(const int *t) { double s = 0; for (int i = 0; i < n; i++) s += uz(t[i], t[(i + 1) % n]); return s; }

/* EN YAKIN KOMSU: hep en yakin ziyaret edilmemis sehre git (acgozlu) */
static void en_yakin(int *t) {
    char *gor = calloc(n, 1); t[0] = 0; gor[0] = 1;
    for (int i = 1; i < n; i++) { int en = -1; for (int v = 0; v < n; v++) if (!gor[v] && (en < 0 || uz(t[i - 1], v) < uz(t[i - 1], en))) en = v; t[i] = en; gor[en] = 1; }
    free(gor);
}

/* MST 2-YAKLASIM: Prim ile MST (O(n^2), yogun graf: Ders 9.18 Al. 4), sonra MST'yi onek sirayla gez, tekrarlari atla.
   Ucgen esitsizligi varsa: tur <= 2 * MST <= 2 * OPT */
static double mst_agirlik;
static void mst_tur(int *t) {
    double *en = malloc(n * sizeof *en); int *eb = malloc(n * sizeof *eb); char *ag = calloc(n, 1);
    for (int v = 0; v < n; v++) { en[v] = INFINITY; eb[v] = -1; } en[0] = 0; mst_agirlik = 0;
    int *cocuk_bas = malloc(n * sizeof(int)), *kardes = malloc(n * sizeof(int)); for (int v = 0; v < n; v++) cocuk_bas[v] = -1;
    for (int k = 0; k < n; k++) {
        int u = -1; for (int v = 0; v < n; v++) if (!ag[v] && (u < 0 || en[v] < en[u])) u = v;
        ag[u] = 1; mst_agirlik += en[u];
        if (eb[u] >= 0) { kardes[u] = cocuk_bas[eb[u]]; cocuk_bas[eb[u]] = u; }
        for (int v = 0; v < n; v++) if (!ag[v] && uz(u, v) < en[v]) { en[v] = uz(u, v); eb[v] = u; }
    }
    int *yig = malloc(n * sizeof(int)), tp = 0, k = 0; yig[tp++] = 0;          /* onek gezinme, acik yiginla */
    while (tp) { int u = yig[--tp]; t[k++] = u; for (int c = cocuk_bas[u]; c >= 0; c = kardes[c]) yig[tp++] = c; }
    free(en); free(eb); free(ag); free(cocuk_bas); free(kardes); free(yig);
}

/* 2-OPT: iki kenari (a,b) ve (c,d), (a,c) ve (b,d) ile degistirmek turu kisaltiyorsa aradaki parcayi ters cevir; iyilesme kalmayana kadar */
static int iki_opt(int *t) {
    int iyilesme = 1, adim = 0;
    while (iyilesme) { iyilesme = 0;
        for (int i = 0; i < n - 1; i++) for (int j = i + 2; j < n; j++) {
            int a = t[i], b = t[i + 1], c = t[j], d = t[(j + 1) % n];
            if (a == d) continue;
            if (uz(a, c) + uz(b, d) < uz(a, b) + uz(c, d) - 1e-12) {
                for (int p = i + 1, q = j; p < q; p++, q--) { int x = t[p]; t[p] = t[q]; t[q] = x; }
                iyilesme = 1; adim++; }
        } }
    return adim;
}

/* BENZETIMLI TAVLAMA: rastgele bir 2-opt hamlesi; kotulestirse bile exp(-fark/T) olasilikla kabul et; T yavasca dusur */
static uint64_t xs = 88172645463325252ull;
static double rnd01(void) { xs ^= xs << 13; xs ^= xs >> 7; xs ^= xs << 17; return (xs >> 11) * 0x1p-53; }
static void tavla(int *t, long adim, double T0) {
    double T = T0, sogu = pow(1e-4, 1.0 / adim);                /* T0'dan T0*1e-4'e geometrik */
    int *en_iyi = malloc(n * sizeof *en_iyi); memcpy(en_iyi, t, n * sizeof *t); double en_l = tur_uzunlugu(t), l = en_l;
    for (long s = 0; s < adim; s++, T *= sogu) {
        int i = (int)(rnd01() * n), j = (int)(rnd01() * n); if (i > j) { int x = i; i = j; j = x; } if (j - i < 2 || (i == 0 && j == n - 1)) continue;
        int a = t[i], b = t[i + 1], c = t[j], d = t[(j + 1) % n];
        double fark = uz(a, c) + uz(b, d) - uz(a, b) - uz(c, d);
        if (fark < 0 || rnd01() < exp(-fark / T)) {
            for (int p = i + 1, q = j; p < q; p++, q--) { int x = t[p]; t[p] = t[q]; t[q] = x; }
            l += fark; if (l < en_l) { en_l = l; memcpy(en_iyi, t, n * sizeof *t); } }
    }
    memcpy(t, en_iyi, n * sizeof *t); free(en_iyi);
}

/* HELD-KARP: D[S][v] = 0'dan baslayip S kumesini gezip v'de biten en kisa yol. Kucuk n icin kesin. */
static double held_karp(void) {
    int M = 1 << n; double *D = malloc((size_t)M * n * sizeof *D);
    for (size_t i = 0; i < (size_t)M * n; i++) D[i] = INFINITY;
    D[1 * n + 0] = 0;
    for (int S = 1; S < M; S += 2)                               /* 0 her zaman kumede */
        for (int v = 0; v < n; v++) { double d = D[(size_t)S * n + v]; if (!(S >> v & 1) || d == INFINITY) continue;
            for (int w = 0; w < n; w++) if (!(S >> w & 1)) { double y = d + uz(v, w); size_t k = (size_t)(S | 1 << w) * n + w; if (y < D[k]) D[k] = y; } }
    double en = INFINITY; for (int v = 1; v < n; v++) { double y = D[(size_t)(M - 1) * n + v] + uz(v, 0); if (y < en) en = y; }
    free(D); return en;
}

static void noktalar(int k, uint64_t tohum) { n = k; xs = tohum; free(X); free(Y); X = malloc(n * sizeof *X); Y = malloc(n * sizeof *Y); for (int i = 0; i < n; i++) { X[i] = rnd01(); Y[i] = rnd01(); } }

int main(void) {
    int *t = malloc(4096 * sizeof *t);
    printf("kucuk ornekler (n=12), 20 rastgele nokta kumesi, kesin optimuma orani (ortalama / en kotu):\n");
    double top[5] = { 0 }, enk[5] = { 0 };
    for (int r = 0; r < 20; r++) {
        noktalar(12, 1000 + r); double opt = held_karp(), o[5];
        en_yakin(t); o[0] = tur_uzunlugu(t) / opt;
        mst_tur(t); o[1] = tur_uzunlugu(t) / opt;
        iki_opt(t); o[2] = tur_uzunlugu(t) / opt;                      /* MST turu + 2-opt */
        en_yakin(t); iki_opt(t); o[3] = tur_uzunlugu(t) / opt;
        en_yakin(t); tavla(t, 200000, 0.1); o[4] = tur_uzunlugu(t) / opt;
        for (int k = 0; k < 5; k++) { top[k] += o[k]; if (o[k] > enk[k]) enk[k] = o[k]; }
        if (o[1] > 2.0 + 1e-9) puts("2-YAKLASIM IHLALI");
    }
    const char *ad[] = { "en yakin komsu", "MST turu", "MST + 2-opt", "en yakin + 2-opt", "tavlama" };
    for (int k = 0; k < 5; k++) printf("  %-17s %.3f / %.3f\n", ad[k], top[k] / 20, enk[k]);
    printf("buyuk ornek (n=2000), MST alt sinirina orani (MST <= OPT):\n");
    noktalar(2000, 77);
    en_yakin(t); double l1 = tur_uzunlugu(t); mst_tur(t); double mst = mst_agirlik, l2 = tur_uzunlugu(t);
    int a = iki_opt(t); double l3 = tur_uzunlugu(t);
    en_yakin(t); int b = iki_opt(t); double l4 = tur_uzunlugu(t);
    printf("  en yakin komsu    %.3f\n  MST turu          %.3f\n  MST + 2-opt       %.3f (%d hamle)\n  en yakin + 2-opt  %.3f (%d hamle)\n", l1 / mst, l2 / mst, l3 / mst, a, l4 / mst, b);
    en_yakin(t); iki_opt(t); tavla(t, 20000000, 0.005); iki_opt(t); double l5 = tur_uzunlugu(t);
    printf("  en yakin + 2-opt + tavlama + 2-opt  %.3f\n", l5 / mst);
    free(t); free(X); free(Y);
}
```

Şehirler birim karede rastgele noktalar, uzaklık Öklid uzaklığı. Beş yöntem:

- **En yakın komşu** (açgözlü kurucu): her adımda en yakın ziyaret edilmemiş şehre git. $O(n^2)$. Garantisi yok: en kötü durumda optimumun $\Theta(\log n)$ katı.
- **MST turu** (2-yaklaşım): Ders 9.18'deki MST'yi (yoğun graf olduğu için heap'siz $O(n^2)$ Prim; 9.18 Alıştırma 4) kur, onu Ders 8.7'deki **önek** sırasıyla gez, daha önce ziyaret edilen şehirleri atla.
- **2-opt** (yerel arama): turdan iki kenar $(a, b)$ ve $(c, d)$ seç; onları $(a, c)$ ve $(b, d)$ ile değiştirmek (aradaki parçayı ters çevirmek) turu kısaltıyorsa yap. Hiçbir 2-opt hamlesi iyileştirmeyene kadar tekrarla. Sonuç bir **yerel minimum**: tek bir hamleyle iyileştirilemeyen bir tur.
- **Benzetimli tavlama** (simulated annealing; Kirkpatrick, Gelatt ve Vecchi, 1983): rastgele bir 2-opt hamlesi dene; iyileştiriyorsa kabul et, **kötüleştiriyorsa bile** $e^{-\Delta / T}$ olasılıkla kabul et. "Sıcaklık" $T$ yavaş yavaş düşürülüyor: başta kötü hamleler sık kabul edilip yerel minimumlardan kaçılıyor, sonda algoritma bir minimuma "donuyor". Adını metallerin yavaşça soğutularak kusursuz kristale dönüşmesinden alıyor.
- **Held–Karp** (kesin): Ders 9.12 tarzı bir DP. $D[S][v]$, 0'dan başlayıp $S$ kümesindeki şehirlerin hepsini gezip $v$'de biten en kısa yol; kümeler bit maskesi. $O(2^n n^2)$ zaman, $O(2^n n)$ bellek: $n = 12$'de anında, $n = 30$'da imkânsız. Kaba kuvvetin $n!$'ünden çok iyi ama yine üstel; TSP için bilinen en iyi kesin en kötü durum sınırı bu.

### MST turunun 2-yaklaşım ispatı

Uzaklıklar **üçgen eşitsizliğini** sağlıyorsa (Öklid uzaklığı sağlıyor):

1. $w(\text{MST}) \le \text{OPT}$: optimal turdan bir kenar çıkarınca bir yayılan ağaç (bir yol) kalıyor, ve MST en hafif yayılan ağaç.
2. MST'yi her kenardan iki kez geçerek (bir kez inip bir kez çıkarak) gezen "tam yürüyüş" $2 \cdot w(\text{MST})$ uzunlukta.
3. Önek sırası bu yürüyüşten, daha önce görülen şehirleri **atlayarak** elde ediliyor. Atlamak, bir yolu doğrudan bir kenarla değiştirmek; üçgen eşitsizliğiyle uzunluğu artırmıyor.

Sonuç: $\text{tur} \le 2 \cdot w(\text{MST}) \le 2 \cdot \text{OPT}$. Christofides'in (1976) algoritması, MST'ye tek dereceli düğümler arasında bir minimum eşleme ekleyerek bu oranı 1.5'e indiriyor. Üçgen eşitsizliği olmayan genel TSP için ise, P ≠ NP ise, **hiçbir** sabit oranlı polinom yaklaşım yok.

---

## 2. Ölçüm

İki deney: 12 şehirli 20 rastgele örnekte Held–Karp ile kesin optimuma göre oranlar (ortalama ve en kötü); 2000 şehirde ise kesin optimum hesaplanamadığı için **MST ağırlığına** göre oranlar ($\text{MST} \le \text{OPT}$ olduğu için bu bir alt sınır).

```
$ cc -std=c11 -O2 -Wall -Wextra tsp.c -o tsp -lm && ./tsp
kucuk ornekler (n=12), 20 rastgele nokta kumesi, kesin optimuma orani (ortalama / en kotu):
  en yakin komsu    1.158 / 1.313
  MST turu          1.180 / 1.331
  MST + 2-opt       1.015 / 1.094
  en yakin + 2-opt  1.020 / 1.173
  tavlama           1.000 / 1.000
buyuk ornek (n=2000), MST alt sinirina orani (MST <= OPT):
  en yakin komsu    1.373
  MST turu          1.548
  MST + 2-opt       1.234 (905 hamle)
  en yakin + 2-opt  1.202 (539 hamle)
  en yakin + 2-opt + tavlama + 2-opt  1.191
```

(Sanitizer'lı derleme temiz; MST turu 20 örneğin hiçbirinde 2 sınırını aşmıyor.)

- **12 şehir**: en yakın komşu ve MST turu optimumun %16–18 üstünde (en kötü örnekte %31–33); MST'nin teorik sınırı 2 ama pratikte çok daha iyi. 2-opt ile bu %1.5–2'ye iniyor. Tavlama 20 örneğin **hepsinde** optimumu buldu (oran tam 1.000): küçük problemlerde kötü hamleleri kabul edip aramaya devam etmek, yerel minimumların hepsinden kaçmaya yetiyor.
- **2000 şehir**: oranlar MST'ye göre; optimum da MST'den büyük. Büyük $n$'de, rastgele düzlemde optimum tur uzunluğu yaklaşık $0.7124\sqrt{nA}$ (Beardwood–Halton–Hammersley sabiti), MST yaklaşık $0.633\sqrt{nA}$; yani $\text{OPT}/\text{MST} \approx 1.13$ civarı (kenar etkileri yüzünden 2000 şehirde biraz farklı). Buna göre 2-opt'un 1.20'si optimumun yaklaşık %6 üstünde; ve MST turu (1.55) en yakın komşudan (1.37) daha kötü, garantisi olmasına rağmen.
- **Tavlama 2000 şehirde** 20 milyon adımda sadece %1 iyileştirdi (1.202 → 1.191). Sıcaklık seçimi önemli: aynı adım sayısıyla başlangıç sıcaklığı $T_0 = 0.002$ ile 1.198, $0.005$ ile 1.191, $0.05$ ile 1.202 (hiç iyileşme yok; çok sıcak başlayıp iyi turu bozuyor ve soğumaya vakit kalmıyor). Rastgele seçilen iki kenar büyük bir turda neredeyse hiç birbirine yakın olmuyor ve hamlelerin çoğu boşa gidiyor; gerçek uygulamalar hamleleri her şehrin **yakın komşuları** arasından seçiyor (komşu listeleri), ve Lin–Kernighan gibi daha güçlü yerel aramalar kullanıyor. Bugünün en iyi TSP çözücüleri (LKH) milyonlarca şehirde optimumun binde birkaç içine iniyor.

Sezgisel yöntemlerin genel dersi bu ölçümlerde: **iyi bir başlangıç** (açgözlü kurucu) + **yerel arama** (2-opt) en iyi maliyet/fayda oranı; yerel minimumlardan kaçan meta-sezgiseller (tavlama, tabu arama, genetik algoritmalar) daha fazla zaman karşılığında biraz daha iyi sonuç veriyor, ve parametreleri **ayarlanmak** zorunda.

---

## 3. Derleyicide sezgisel kararlar

Bir derleyicinin verdiği kararların çoğu, kesin cevabı ya NP-zor ya da çalışma anına bağlı (hangi dalın sık alınacağı) olan sorular. Hepsi sezgisellerle, ve sayısal **eşiklerle** veriliyor:

| Karar | Sezgisel | Tipik eşik (yaklaşık) |
| --- | --- | --- |
| Satır içi açma (inlining) | Çağrılan fonksiyonun "maliyeti" (komut sayısı) bir eşiğin altındaysa aç | LLVM'de `-inline-threshold` varsayılanı 225 |
| Döngü açma (unrolling) | Gövde küçükse ve döngü sayısı biliniyorsa birkaç kat aç | Açılmış gövde boyutu sınırı |
| Komut planlama | Liste planlama: hazır komutlardan kritik yolu en uzun olanı önce (Ders 9.15'in kritik yolu) | — |
| Yazmaç ayırma | Chaitin–Briggs; taşıma için "maliyet / derece" en düşük olan (Ders 9.20) | Döngü derinliğine göre kullanım ağırlığı |
| Dal düzeni | Sık alınan dal ardışık gelsin; profil yoksa "geri dallar alınır" tahmini (Ders 7.22) | — |

Bu eşikler çoğunlukla bir kıyaslama paketi üzerinde ölçülerek ayarlanıyor ve bir programda iyi olan başka bir programda kötü olabiliyor. Profil güdümlü optimizasyon (PGO; programın gerçek bir çalışmasından sayaçlar toplayıp yeniden derlemek) ve son yıllarda makine öğrenmesiyle eğitilmiş sezgiseller (Google'ın MLGO'su LLVM'in satır içi açma ve yazmaç ayırma kararlarını öğrenilmiş bir modelle veriyor) bu ayarlamayı otomatikleştiriyor.

---

## Alıştırmalar

**1** – **Köşe örtüsü** (her kenarın en az bir ucunu içeren en küçük düğüm kümesi; Ders 9.13'te ağaçta doğrusaldı, genel graflarda NP-zor) için 2-yaklaşım: henüz örtülmemiş bir kenar seç, **iki** ucunu da örtüye ekle, o uçlara değen bütün kenarları sil; tekrarla. Neden $\le 2 \cdot \text{OPT}$? (İpucu: seçilen kenarlar bir eşleme oluşturuyor.)

**2** – 2-opt'un bir turu en fazla kaç kez iyileştirebileceğine dair bir üst sınır ver. 2000 şehirde 539 ve 905 hamle neden bu kadar az?

**3** – En yakın komşu sezgiselinin başlangıç şehrine bağlı olduğunu düşün. Bütün $n$ başlangıcı deneyip en iyisini almak maliyeti ne yapar? Bu, bir "çoklu başlangıç" (multi-start) yerel aramanın en basit hali; ne zaman işe yarar?

**4** – Benzetimli tavlamada $e^{-\Delta/T}$ kuralıyla: $T$ çok büyükken ve çok küçükken algoritma neye dönüşür? $\Delta = 0.01$'lik bir kötüleşmenin $T = 0.005$'te ve $T = 0.0005$'te kabul olasılığı ne?

**5** – Held–Karp $n = 12$ için kaç durum (alt problem) kullanır ve kaç işlem yapar? $n = 25$ için bellek ne olur? Bu, Ders 9.22'deki "üstel ama kaba kuvvetten çok iyi" ayrımına bir örnek: $n!$ ile $2^n n^2$'yi $n = 12$ ve $n = 25$ için karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – Algoritmanın seçtiği kenarlar ortak uç paylaşmıyor (bir kenar seçilince uçlarına değen her kenar siliniyor): bir **eşleme** $M$. Örtü boyutu $2|M|$. Herhangi bir köşe örtüsü, $M$'nin her kenarını örtmek için o kenarın en az bir ucunu içermeli, ve $M$'nin kenarlarının uçları ayrık: $\text{OPT} \ge |M|$. Yani $2|M| \le 2 \cdot \text{OPT}$. Bu oranın (sabit olarak) iyileştirilip iyileştirilemeyeceği hâlâ açık; "benzersiz oyunlar varsayımı" doğruysa 2'den iyisi NP-zor. Ders 9.20'deki girişim grafında "bir taşıma kümesi seç" problemi bununla yakından ilişkili.

**2** – Her iyileştirici hamle tur uzunluğunu kesin azaltıyor ve olası turlar sonlu ($(n-1)!/2$); yani sonlanıyor, ama sınır üstel ve gerçekten de 2-opt'un üstel sayıda hamle yaptığı yapay örnekler var. Rastgele düzlem örneklerinde ise hamle sayısı $O(n)$ civarı ve her hamle turu belirgin kısaltıyor: başlangıç turu (en yakın komşu ya da MST) zaten iyi, ve kalan "çaprazlamalar" sayılı. 2000 şehirde 539 hamle, şehir başına 0.27. Ama her tam tarama $O(n^2)$ çift deniyor; maliyetin çoğu hamle yapmak değil, iyileştirici hamleyi **aramak**. Komşu listeleri bunu $O(n k)$'ya indiriyor.

**3** – Maliyet $n$ katına çıkıyor: $O(n^3)$. En yakın komşunun sonucu başlangıca bağlı olduğu için (bir yerde "sıkışıp" son şehirlere uzun kenarlarla dönmek zorunda kalması, başlangıca göre değişiyor) en iyi başlangıç ortalamadan genelde birkaç yüzde iyi. Çoklu başlangıç, yerel arama ucuzken ve farklı başlangıçlar farklı yerel minimumlara götürüyorken işe yarıyor; ama bir yerel minimumdan kaçmanın daha akıllı yolları (tavlama, "pertürbasyon + yeniden yerel arama" yani iterated local search) genelde aynı bütçeyle daha iyi.

**4** – $T \to \infty$: $e^{-\Delta/T} \to 1$, her hamle kabul ediliyor: **rastgele yürüyüş**. $T \to 0$: kötüleştiren hamlelerin kabul olasılığı 0'a gidiyor: **saf yerel arama** (sadece iyileştirici hamleler, yani rastgele hamleli bir 2-opt). $\Delta = 0.01$: $T = 0.005$'te $e^{-2} \approx 0.135$; $T = 0.0005$'te $e^{-20} \approx 2 \cdot 10^{-9}$, pratikte hiç. Ölçümde $T_0 = 0.05$'in kötü olması: başta neredeyse her kötüleşme kabul edildi ve tur bozuldu; 20 milyon adımlık soğuma, iyi bir tura geri dönmeye yetmedi.

**5** – $n = 12$: durum sayısı $2^{12} \cdot 12 = 49\,152$; her durum 12 sonraki şehri deniyor: yaklaşık $5.9 \cdot 10^5$ işlem (aslında 0'ı içeren kümelerle yarısı). Kaba kuvvet $(n-1)!/2 = 19\,958\,400$ tur. $n = 25$: $2^{25} \cdot 25 \approx 8.4 \cdot 10^8$ durum, `double` ile 6.7 GB bellek ve $2 \cdot 10^{10}$ işlem: sınırda. Kaba kuvvet $24!/2 \approx 3 \cdot 10^{23}$: evrenin yaşından uzun. İkisi de üstel ama $2^n n^2$, $n!$'den $n = 25$'te $10^{13}$ kat küçük. NP-zor problemlerde bu tür "daha iyi üstel" algoritmalar (ve dal-sınır, kesme düzlemleri gibi pratikte çok daha iyi çalışan kesin yöntemler: Concorde 85 900 şehirli bir örneği kesin çözdü) önemli.

</details>

---

## Kaynaklar

- David Johnson ve Lyle McGeoch, "The Traveling Salesman Problem: A Case Study in Local Optimization", *Local Search in Combinatorial Optimization*, 1997.
- Scott Kirkpatrick, C. Daniel Gelatt ve Mario Vecchi, "Optimization by Simulated Annealing", *Science* 220(4598), 1983.
- Nicos Christofides, "Worst-Case Analysis of a New Heuristic for the Travelling Salesman Problem", Carnegie Mellon teknik rapor, 1976.
- Michael Held ve Richard Karp, "A Dynamic Programming Approach to Sequencing Problems", *Journal of SIAM* 10(1), 1962.
- David Applegate, Robert Bixby, Vašek Chvátal ve William Cook, *The Traveling Salesman Problem: A Computational Study*, Princeton, 2006.
- Mircea Trofin ve ark., "MLGO: a Machine Learning Guided Compiler Optimizations Framework", 2021.

**Sıradaki ders:** Faz projesi. Huffman sıkıştırıcı ve `diff` aracının C'de sıfırdan yazımı.
