---
title: "9.16 Güçlü bağlı bileşenler"
description: "Yönlü bir grafta karşılıklı olarak birbirine ulaşabilen düğüm grupları: güçlü bağlı bileşen tanımı, bileşenlerin bir DAG oluşturması (yoğunlaştırma); Tarjan algoritması: tek DFS, keşif ve 'düşük bağlantı' değerleri, bileşen yığını, açık yığınla; Kosaraju algoritması: önce bitiş sırası, sonra ters grafta gezinme; bir derleyicinin çağrı grafında doğrudan ve karşılıklı özyinelemeyi bulmak; 1 milyon düğümde ortalama derece 1'in üstünde dev bir bileşenin ortaya çıkışı ve iki algoritmanın aynı bölümü 0.08 s civarında bulması."
---

Ders 9.14 yönlü bir grafta döngü olup olmadığını söylüyordu, Ders 9.15 döngü yoksa bir sıralama veriyordu. Ama gerçek graflar çoğu zaman döngülü, ve asıl soru döngülerin **nerede** olduğu. Bir derleyicinin **çağrı grafında** (fonksiyon $f$, fonksiyon $g$'yi çağırıyorsa $f \to g$) hangi fonksiyonlar özyinelemeli? Sadece kendini çağıranlar değil, birbirini çağıran gruplar da: Faz 15'te yazacağımız ayrıştırıcıda `ifade` → `terim` → `carpan` → (parantezli alt ifade için) `ifade`. Bu tür bir grubu bilmek önemli: grubun içindeki fonksiyonlar **satır içi açılamaz** (inline sonsuz büyür), yığın kullanımları önceden sınırlanamaz, ve bazı analizler (Faz 16'daki fonksiyonlar arası analiz) grubu tek bir birim olarak, bir sabit noktaya kadar yinelenerek işlemek zorunda (Ders 9.21).

---

## 1. Tanım

Yönlü bir grafta $u$ ile $v$ **güçlü bağlı**: $u$'dan $v$'ye **ve** $v$'den $u$'ya yol var. Bu bir denklik bağıntısı (Ders 6.6: yansıyan, simetrik, geçişli), ve denklik sınıflarına **güçlü bağlı bileşenler** (GBB; SCC, strongly connected components) denir. Her düğüm tam olarak bir bileşende; döngüsüz bir düğüm kendi başına tek elemanlı bir bileşen.

Her bileşeni tek bir düğüme **büzersek** (yoğunlaştırma, condensation), çıkan graf **döngüsüz**: iki bileşen arasında iki yönlü de yol olsaydı onlar aynı bileşen olurdu. Yani her yönlü graf, "içinde döngüler olan düğüm gruplarının bir DAG'ı". Bu, bir yönlü grafın en önemli yapısal tanımı; Ders 9.15'in topolojik sıralaması bu DAG üzerinde her zaman çalışıyor.

Saf yöntem: her düğümden bir BFS ileri, bir BFS geri; $O(n(n + m))$. İki klasik algoritma bunu $O(n + m)$'ye indiriyor.

---

## 2. Kod

```c
/* Guclu bagli bilesenler: Tarjan (tek DFS, lowlink) ve Kosaraju (iki DFS, ters graf). Ikisi de acik yiginla. */
#include <stdio.h>
#include "graf.h"

/* TARJAN. dusuk[u]: u'nun DFS alt agacindan (en fazla bir geri/capraz kenarla) ulasilan, HALA YIGINDA olan en kucuk kesif no.
   dusuk[u] == kesif[u] ise u bir bilesenin koku: yigindaki u ve ustundekiler bir bilesen. */
static int tarjan(const Graf *g, int *bilesen) {
    int n = g->n, zaman = 0, sayi = 0;
    int *kesif = calloc(n, sizeof(int)), *dusuk = malloc(n * sizeof(int)), *yigin_ici = calloc(n, sizeof(int));
    int *S = malloc(n * sizeof(int)), sp = 0;                       /* bilesen yigini */
    int *cagri = malloc(n * sizeof(int)), *yer = malloc(n * sizeof(int)), cp = 0;   /* DFS cagri yigini (Ders 8.6) */
    for (int s = 0; s < n; s++) {
        if (kesif[s]) continue;
        cagri[cp++] = s; kesif[s] = dusuk[s] = ++zaman; yer[s] = g->ofset[s]; S[sp++] = s; yigin_ici[s] = 1;
        while (cp) {
            int u = cagri[cp - 1];
            if (yer[u] < g->ofset[u + 1]) {
                int v = g->hedef[yer[u]++];
                if (!kesif[v]) { kesif[v] = dusuk[v] = ++zaman; yer[v] = g->ofset[v]; S[sp++] = v; yigin_ici[v] = 1; cagri[cp++] = v; }
                else if (yigin_ici[v] && kesif[v] < dusuk[u]) dusuk[u] = kesif[v];
            } else {
                cp--;
                if (cp && dusuk[u] < dusuk[cagri[cp - 1]]) dusuk[cagri[cp - 1]] = dusuk[u];   /* ozyinelemeden donus */
                if (dusuk[u] == kesif[u]) {                                                  /* bilesen koku */
                    int w;
                    do { w = S[--sp]; yigin_ici[w] = 0; bilesen[w] = sayi; } while (w != u);
                    sayi++;
                }
            }
        }
    }
    free(kesif); free(dusuk); free(yigin_ici); free(S); free(cagri); free(yer);
    return sayi;
}

/* KOSARAJU. 1) DFS ile bitis sirasi. 2) Ters grafta, bitisi en buyukten baslayarak DFS: her agac bir bilesen. */
static int kosaraju(const Graf *g, int *bilesen) {
    int n = g->n, *sira = malloc(n * sizeof(int)), k = 0;
    int *renk = calloc(n, sizeof(int)), *yig = malloc(n * sizeof(int)), *yer = malloc(n * sizeof(int)), tp;
    for (int s = 0; s < n; s++) {                       /* 1. gecis: Ders 9.15'in DFS'i gibi bitis sirasi */
        if (renk[s]) continue;
        tp = 0; yig[tp++] = s; renk[s] = 1; yer[s] = g->ofset[s];
        while (tp) { int u = yig[tp - 1];
            if (yer[u] < g->ofset[u + 1]) { int v = g->hedef[yer[u]++]; if (!renk[v]) { renk[v] = 1; yer[v] = g->ofset[v]; yig[tp++] = v; } }
            else { sira[k++] = u; tp--; } }
    }
    Kenar *ters = malloc((g->m ? g->m : 1) * sizeof *ters); int t = 0;    /* ters graf (Ders 8.19, Alistirma 3) */
    for (int u = 0; u < n; u++) for (int i = g->ofset[u]; i < g->ofset[u + 1]; i++) ters[t++] = (Kenar){ g->hedef[i], u };
    Graf T = graf_kur(n, ters, g->m); free(ters);
    for (int v = 0; v < n; v++) bilesen[v] = -1;
    int sayi = 0;
    for (int j = n - 1; j >= 0; j--) {                  /* 2. gecis: bitis sirasinin tersi */
        int s = sira[j]; if (bilesen[s] >= 0) continue;
        tp = 0; yig[tp++] = s; bilesen[s] = sayi;
        while (tp) { int u = yig[--tp];
            for (int i = T.ofset[u]; i < T.ofset[u + 1]; i++) { int v = T.hedef[i]; if (bilesen[v] < 0) { bilesen[v] = sayi; yig[tp++] = v; } } }
        sayi++;
    }
    graf_birak(&T); free(sira); free(renk); free(yig); free(yer);
    return sayi;
}

#ifndef KUTUPHANE
/* Bir programin cagri grafi: f -> g, "f, g'yi cagiriyor" */
static const char *ad[] = { "main", "ayristir", "ifade", "terim", "carpan", "hata", "yaz", "tablo_bul", "hash", "sirala", "birlestir" };
enum { MAIN, AYRISTIR, IFADE, TERIM, CARPAN, HATA, YAZ, TABLO_BUL, HASH, SIRALA, BIRLESTIR, N };
int main(void) {
    Kenar k[] = {
        { MAIN, AYRISTIR }, { MAIN, YAZ }, { MAIN, SIRALA },
        { AYRISTIR, IFADE }, { IFADE, TERIM }, { TERIM, CARPAN }, { CARPAN, IFADE },   /* ozyinelemeli inis: ( ifade ) */
        { CARPAN, TABLO_BUL }, { CARPAN, HATA }, { IFADE, HATA }, { HATA, YAZ },
        { TABLO_BUL, HASH }, { SIRALA, SIRALA }, { SIRALA, BIRLESTIR } };       /* sirala kendini cagiriyor */
    Graf g = graf_kur(N, k, sizeof k / sizeof k[0]);
    int b1[N], b2[N];
    int s1 = tarjan(&g, b1), s2 = kosaraju(&g, b2);
    printf("Tarjan %d bilesen, Kosaraju %d bilesen\n", s1, s2);
    int oz[N] = { 0 }; for (int u = 0; u < N; u++) for (int i = g.ofset[u]; i < g.ofset[u + 1]; i++) if (g.hedef[i] == u) oz[u] = 1;
    for (int c = 0; c < s1; c++) {
        int boy = 0, ilk = -1; for (int v = 0; v < N; v++) if (b1[v] == c) { boy++; if (ilk < 0) ilk = v; }
        printf("  bilesen %d:", c); for (int v = 0; v < N; v++) if (b1[v] == c) printf(" %s", ad[v]);
        if (boy > 1) printf("   <- karsilikli ozyineleme");
        else if (oz[ilk]) printf("   <- dogrudan ozyineleme");
        printf("\n");
    }
    graf_birak(&g);
}
#endif
```

### Tarjan

Robert Tarjan (1972) bileşenleri **tek** bir DFS'te buluyor. Gözlem: bir bileşenin düğümleri, DFS ağacında **bitişik** bir alt ağaç oluşturuyor; bu alt ağacın en üstteki düğümüne bileşenin **kökü** diyelim. DFS keşfettiği her düğümü ayrı bir **bileşen yığınına** itiyor. Bir kök bittiğinde, yığında onun üstünde duran bütün düğümler onun bileşeni: hepsini çıkar.

Kökü tanımak için her düğümün bir **düşük bağlantı** (low-link) değeri: $\text{düşük}(u)$, $u$'nun DFS alt ağacından, en fazla **bir** geri ya da çapraz kenar kullanarak ulaşılabilen ve **hâlâ bileşen yığınında** olan düğümlerin en küçük keşif numarası. Hesaplanışı:

- Başta $\text{düşük}(u) = \text{keşif}(u)$.
- $u \to v$ kenarı $v$'yi keşfediyorsa (ağaç kenarı), $v$ bittikten sonra $\text{düşük}(u) = \min(\text{düşük}(u), \text{düşük}(v))$: kodda "özyinelemeden dönüş" satırı.
- $v$ zaten keşfedilmiş ve hâlâ yığındaysa (aynı, henüz kapanmamış bir bileşende), $\text{düşük}(u) = \min(\text{düşük}(u), \text{keşif}(v))$.
- $v$ keşfedilmiş ama yığında değilse, $v$'nin bileşeni zaten kapandı: o kenar başka bir bileşene gidiyor, yok say.

$u$ bittiğinde $\text{düşük}(u) = \text{keşif}(u)$ ise, $u$'nun alt ağacından $u$'nun üstüne (daha eski, hâlâ açık bir düğüme) dönen hiçbir yol yok: $u$ bir kök.

Açık yığınla yazıldı (Ders 8.6, 9.14): `cagri` DFS'in çağrı yığını, `S` bileşen yığını. İki ayrı yığın, ve ikisini karıştırmamak Tarjan'ın en çok hata yapılan yeri.

### Kosaraju

Kosaraju'nun (1978, ve bağımsız olarak Sharir 1981) algoritması daha kolay anlaşılıyor:

1. Bir DFS ile bütün düğümlerin **bitiş sırasını** çıkar (Ders 9.15'teki gibi).
2. Grafın **tersini** kur (bütün kenarlar ters yönde; Ders 8.19, Alıştırma 3).
3. Ters grafta, düğümleri **bitiş zamanı büyükten küçüğe** sırayla dene; beyaz kalan her birinden bir gezinme başlat. Her gezinmenin ulaştığı düğümler bir bileşen.

Neden doğru? Bitişi en büyük düğüm, yoğunlaştırma DAG'ının bir **kaynak** bileşeninde (ona gelen kenar yok). Ters grafta o bileşenden çıkan kenar yok; oradan başlayan gezinme bileşenin dışına çıkamıyor ve tam onu buluyor. Sonraki en büyük bitişli düğüm, kalan DAG'ın bir kaynağında; ters grafta oradan çıkan kenarlar sadece zaten bulunmuş bileşenlere gidiyor ve onlar atlanıyor. (CLRS Lemma 22.14.)

Kosaraju'da iki gezinme ve ters graf için ek bellek; Tarjan tek gezinme. İkisi de $O(n + m)$.

---

## 3. Çağrı grafında özyineleme

Küçük bir derleyicinin fonksiyonları:

```
main      -> ayristir, yaz, sirala
ayristir  -> ifade
ifade     -> terim, hata
terim     -> carpan
carpan    -> ifade (parantezli alt ifade), tablo_bul, hata
hata      -> yaz
tablo_bul -> hash
sirala    -> sirala (kendini), birlestir
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined gbb.c -o gbb && ./gbb
Tarjan 9 bilesen, Kosaraju 9 bilesen
  bilesen 0: hash
  bilesen 1: tablo_bul
  bilesen 2: yaz
  bilesen 3: hata
  bilesen 4: ifade terim carpan   <- karsilikli ozyineleme
  bilesen 5: ayristir
  bilesen 6: birlestir
  bilesen 7: sirala   <- dogrudan ozyineleme
  bilesen 8: main
```

- `ifade`, `terim`, `carpan` tek bileşen: **karşılıklı özyineleme**. Özyinelemeli inişli ayrıştırıcıların (Faz 15) tipik yapısı.
- `sirala` tek başına ama öz döngüsü var: **doğrudan özyineleme**. (Tek elemanlı bir bileşen, ancak öz döngüsü varsa özyinelemeli.)
- Diğerleri özyinelemesiz: bunların yığın kullanımı derleme anında, çağrı grafının en uzun yolundan hesaplanabilir (gömülü sistemlerde yığın taşmasını önceden önlemenin yolu; Ders 9.15, Alıştırma 3'teki kritik yol).

Tarjan'ın bileşen numaraları da bilgi taşıyor: bileşenler, yoğunlaştırma DAG'ının **ters topolojik sırasıyla** (yapraklar önce) bulunuyor: `hash` 0, `main` 8. Bir derleyici fonksiyonlar arası bir analizi tam bu sırayla yapar: bir fonksiyonu işlerken çağırdığı her fonksiyon (kendi bileşeni dışında) zaten işlenmiş olur. LLVM'in `CallGraphSCCPass`'i bu sırayı kullanıyor.

---

## 4. Ölçüm

1 milyon düğümlü rastgele yönlü graflar; ortalama çıkış derecesi 0.5'ten 2'ye. İki algoritmanın verdiği bölümlerin **aynı** olduğu (birinin her bileşeni ötekinde tek bir bileşene karşılık geliyor, ve tersi) kontrol ediliyor:

```
$ cc -std=c11 -O2 -Wall buyuk.c -o buyuk && ./buyuk
derece 0.5: 1000000 bilesen (en buyugu 1 dugum)  Tarjan 0.019 s  Kosaraju 0.023 s  ayni bolum: evet
derece 1.0: 999871 bilesen (en buyugu 68 dugum)  Tarjan 0.038 s  Kosaraju 0.042 s  ayni bolum: evet
derece 1.5: 661327 bilesen (en buyugu 338674 dugum)  Tarjan 0.058 s  Kosaraju 0.067 s  ayni bolum: evet
derece 2.0: 364045 bilesen (en buyugu 635953 dugum)  Tarjan 0.076 s  Kosaraju 0.089 s  ayni bolum: evet
```

(Sanitizer'lı derleme temiz.)

- İki algoritma her durumda aynı bölümü buluyor; Tarjan %15–20 hızlı (tek gezinme, ters graf yok).
- Ortalama derece 1'in altında neredeyse hiç döngü yok: bütün düğümler tek başına. Derece 1'i geçince bir **faz geçişi**: derece 1.5'te düğümlerin üçte biri tek bir **dev bileşende**, 2'de üçte ikisi. Ders 8.18'deki süzülme eşiğinin ve rastgele graflardaki dev bileşenin (Erdős–Rényi) yönlü grafta karşılığı. Web grafı da böyle: 2000'lerin başındaki ölçümlerde sayfaların dörtte biri, birbirinden karşılıklı ulaşılabilen tek bir "çekirdekte" çıkmıştı (Broder ve ark., 2000).

---

## Alıştırmalar

**1** – Çağrı grafının **yoğunlaştırma** DAG'ını kur: her bileşen bir düğüm, bileşenler arası kenarlar (tekrarlarsız). Bölüm 3'teki örnekte kaç düğüm ve kaç kenar çıkar? Tarjan'ın numaralandırmasıyla bu DAG'ın bir topolojik sırasını doğrudan nasıl elde edersin?

**2** – Tarjan'ı elle izle: `0→1, 1→2, 2→0, 2→3, 3→4, 4→3`. Her düğümün keşif ve son düşük değeri ne, hangi düğümler kök, bileşenler hangi sırayla çıkıyor?

**3** – Kosaraju'nun 3. adımında düğümleri bitiş zamanı **küçükten büyüğe** sırayla denesek ne olur? Bölüm 3'teki çağrı grafında bir karşı örnek göster.

**4** – **2-SAT**: her biri iki değişkenden oluşan "veya" koşulları, $(x_1 \lor \lnot x_2) \land (\lnot x_1 \lor x_3) \land \dots$. Her koşul $(a \lor b)$ iki çıkarım veriyor: $\lnot a \Rightarrow b$, $\lnot b \Rightarrow a$. Bu çıkarım grafında bir değişken ve değili aynı GBB'deyse formül neden sağlanamaz? Sağlanabiliyorsa bir atamayı nasıl bulursun? (Genel SAT, Ders 9.22'de NP-tam; 2-SAT doğrusal.)

**5** – Özyinelemeli bir bileşendeki fonksiyonlar için derleyici bir analiz yapacak (örneğin "bu fonksiyon global değişken yazıyor mu?"). Bileşenin içinde bağımlılıklar döngüsel; doğru cevabı nasıl bulursun? (İpucu: Ders 9.21'deki sabit nokta yinelemesi.)

<details>
<summary>Cevaplar</summary>

**1** – 9 bileşen, 9 düğüm. Kenarlar (bileşenler arası, tekrarlarsız): `main→ayristir`, `main→yaz`, `main→sirala`, `ayristir→{ifade,terim,carpan}`, `{...}→hata`, `{...}→tablo_bul`, `hata→yaz`, `tablo_bul→hash`, `sirala→birlestir`: 9 kenar (`carpan→hata` ve `ifade→hata` tek kenara iniyor; `sirala→sirala` öz döngüsü bileşenin içinde kaldı). Tarjan bir bileşeni, ondan ulaşılan bütün bileşenler kapandıktan **sonra** kapatıyor; dolayısıyla bileşen numarası yüksek olan, düşük olandan önce gelmeli: numaraları **büyükten küçüğe** dizmek bir topolojik sıra (`main` 8, `sirala` 7, ..., `hash` 0). Ayrıca sıralama gerekmiyor.

**2** – DFS 0'dan: keşif(0)=1, keşif(1)=2, keşif(2)=3; `2→0`: 0 yığında, düşük(2)=1. `2→3`: keşif(3)=4, keşif(4)=5; `4→3`: 3 yığında, düşük(4)=4. 4 biterken düşük(4)=4 ≠ keşif(4)=5; 3'e dönüş: düşük(3)=min(4, 4)=4. 3 biterken düşük(3)=4 = keşif(3): **kök**, yığından 4 ve 3 çıkıyor: bileşen {3, 4}. 2'ye dönüş: düşük(2)=min(1, 4)=1. 2 biterken düşük=1 ≠ 3; 1'e dönüş: düşük(1)=1; 0'a: düşük(0)=1. 0 biterken düşük(0)=1 = keşif(0): kök, yığından 2, 1, 0: bileşen {0, 1, 2}. Sıra: önce {3, 4} (yaprak bileşen), sonra {0, 1, 2}.

**3** – Bitişi en küçük düğüm genelde bir **yaprak** bileşende (çıkışı olmayan) değil, bir DFS dalının sonundadır; ters grafta ondan başlayan gezinme, ona **gelen** bütün bileşenlere yayılır. Örnekte bitişi en küçük düğümlerden biri `hash` (çağrı zincirinin dibi); ters grafta `hash`'ten `tablo_bul`'a, oradan `carpan`'a, oradan `terim`, `ifade`, `ayristir`, `main`'e ulaşılıyor. Hepsi tek bir "bileşen" olarak çıkar: yanlış. Büyükten küçüğe sıra, gezinmeyi her zaman henüz bulunmamış bileşenlerin bir **kaynağından** başlatıyor ve ters grafta kaynaktan çıkış yok; tersi sıra bu garantiyi bozuyor.

**4** – Bir değişken $x$ ve $\lnot x$ aynı GBB'deyse, $x \Rightarrow \dots \Rightarrow \lnot x$ ve $\lnot x \Rightarrow \dots \Rightarrow x$ çıkarım zincirleri var: $x$ doğruysa yanlış olmalı, yanlışsa doğru olmalı; çelişki. Hiçbir değişken için böyle değilse formül sağlanabilir (Aspvall, Plass ve Tarjan, 1979). Atama: yoğunlaştırma DAG'ının **ters topolojik sırasıyla** (Tarjan'ın bulduğu sıra!) bileşenleri gez; bir değişken için, $x$'in bileşeni $\lnot x$'inkinden **önce** (Tarjan numarası daha küçük) bulunduysa $x$ = doğru, değilse yanlış. $O(n + m)$. 2-SAT, derleyicilerde bazı yazmaç atama ve komut planlama kısıtlarının özel durumlarında çıkıyor.

**5** – Bileşenin içindeki fonksiyonların cevapları birbirine bağlı: `ifade` global yazıyor mu? `terim` yazıyorsa evet; `terim`, `carpan`'a bağlı; `carpan`, `ifade`'ye... Çözüm: hepsine iyimser bir başlangıç değeri ver ("yazmıyor"), sonra her fonksiyonun cevabını kendi gövdesinden ve çağırdıklarının **şu anki** cevaplarından tekrar hesapla; bir şey değiştikçe tekrarla. Cevaplar sadece "yazmıyor"dan "yazıyor"a değişebildiği için (monoton), bu en fazla bileşen boyutu kadar turda durur: bir **sabit nokta**. Bileşenler arası ise yineleme gerekmiyor: Tarjan'ın sırasıyla, her bileşen işlenirken çağırdığı bileşenler zaten bitmiş. Ders 9.21 bunun genel kuramı (kafes üzerinde monoton fonksiyonlar, Ders 6.8).

</details>

---

## Kaynaklar

- Robert Tarjan, "Depth-First Search and Linear Graph Algorithms", *SIAM Journal on Computing* 1(2), 1972.
- Micha Sharir, "A Strong-Connectivity Algorithm and Its Applications in Data Flow Analysis", *Computers & Mathematics with Applications* 7(1), 1981.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 22.5: güçlü bağlı bileşenler (Kosaraju).
- Bengt Aspvall, Michael Plass ve Robert Tarjan, "A Linear-Time Algorithm for Testing the Truth of Certain Quantified Boolean Formulas", *Information Processing Letters* 8(3), 1979: 2-SAT.
- Andrei Broder ve ark., "Graph Structure in the Web", *Computer Networks* 33, 2000.

**Sıradaki ders:** En kısa yol. Dijkstra, Bellman–Ford ve Floyd–Warshall.
