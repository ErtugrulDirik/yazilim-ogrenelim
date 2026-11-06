---
title: "8.19 Graf gösterimleri"
description: "Bir grafı bellekte tutmanın üç yolu ve aynı küçük graf üzerinde üçü: satırları 64 bitlik sözcüklere hizalı bit matrisi, düğüm başına bağlı liste ve iki diziden oluşan CSR (sayma ve önek toplamıyla iki geçişte kurulum); 1 milyon düğüm ve 10 milyon kenarlı seyrek grafta BFS: bağlı liste 0.68 s ve 168 MB, CSR 0.054 s ve 44 MB, matris 125 GB; yoğun grafta (4096 düğüm, %50) matris 2.1 MB ve bit paralel BFS 0.1 ms; hangi gösterimin ne zaman seçileceği ve yoğunluk eşiği."
---

Ders 6.30'da grafı matematiksel bir nesne olarak tanımladık: düğümler ve kenarlar. Ders 8.5'teki labirent BFS'i ve Ders 8.18'deki süzülme ızgarası da birer graftı, ama yapıları o kadar düzenliydi ki (her hücrenin dört komşusu) grafı hiç saklamadık: komşuları aritmetikle hesapladık. Genel bir grafta (bir yol ağı, bir sosyal ağ, bir derleyicinin kontrol akış grafı, bir derleme sistemindeki dosya bağımlılıkları) komşuluklar keyfi ve bir yerde saklanmalı. Faz 9'daki bütün graf algoritmaları bu derste seçilen gösterim üzerinde çalışacak. Seçim, algoritmanın kendisi kadar performansı belirliyor.

---

## 1. Örnek graf

Beş düğümlü, yönlü bir graf:

```
     0 ──► 1
     │ ▲   │
     ▼  ╲  ▼
     2 ◄──┘           kenarlar: 0→1, 0→2, 1→2, 2→0, 2→3, 3→3, 4→3
     │
     ▼
     3 ◄── 4
     ↺
```

(`3→3` bir **öz döngü**.) Yönsüz bir grafta her kenar iki yönlü iki kenar olarak saklanır. Düğümler $0, \dots, n-1$; $m$ kenar sayısı. Ağırlıklı graflarda (Dijkstra, Faz 9) her kenarın bir de ağırlığı var; aşağıdaki her gösterime bir dizi daha eklemek yeterli.

Bir graf gösteriminden istenen işlemler:

| İşlem | Kullanıldığı yer |
| --- | --- |
| `u → v` kenarı var mı? | Yoğun graf algoritmaları, Floyd–Warshall |
| `u`'nun komşularını gez | BFS, DFS, Dijkstra: neredeyse her şey |
| Kenar ekle / sil | Dinamik graflar |
| Bellek | Büyük graflar |

---

## 2. Üç gösterim

```c
/* Uc graf gosterimi: komsuluk matrisi (bit), komsuluk listesi (bagli), CSR (iki dizi) */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int u, v; } Kenar;
```

Üçü de aynı girdiden kuruluyor: bir **kenar listesi** (`Kenar` dizisi). Bu da bir gösterim, en basiti; dosyalarda grafların saklandığı biçim genelde bu.

### Komşuluk matrisi

$n \times n$ bir tablo, `A[u][v] = 1` ancak ve ancak `u → v` kenarı varsa. Her hücre bir **bit** (Ders 5.20'deki bitset); her satır 64 bitlik sözcüklerin bir dizisi ve sözcük sınırında başlıyor:

```c
/* 1) Matris: her satir W = ceil(n/64) sozcuk (satirlar sozcuk sinirinda baslar). kenar_var O(1), komsulari gezmek O(n). */
typedef struct { int n, W; uint64_t *bit; } Matris;
static Matris matris_kur(int n, const Kenar *k, int m) {
    int W = (n + 63) / 64;
    Matris g = { n, W, calloc((size_t)n * W, 8) };
    for (int i = 0; i < m; i++) g.bit[(size_t)k[i].u * W + k[i].v / 64] |= 1ull << (k[i].v % 64);
    return g;
}
static int matris_var(const Matris *g, int u, int v) { return (g->bit[(size_t)u * g->W + v / 64] >> (v % 64)) & 1; }
```

Kenar sorgusu $O(1)$: tek bir bit okuma. Ama bellek $n^2$ bit, kenar sayısından **bağımsız**, ve bir düğümün komşularını gezmek $O(n)$: komşusu iki tane olsa bile bütün satırı taramak gerekiyor. (`(size_t)` dönüşümü önemli: `u * W` `int`'te taşabilir; Ders 3.8.)

### Komşuluk listesi

Her düğüm için komşularının bir listesi. Klasik hali Ders 8.2'deki bağlı liste:

```c
/* 2) Komsuluk listesi: her dugum icin bagli liste (Ders 8.2). Kenar basina bir malloc. */
typedef struct KDugum { int hedef; struct KDugum *sonraki; } KDugum;
typedef struct { int n; KDugum **bas; } Liste;
static Liste liste_kur(int n, const Kenar *k, int m) {
    Liste g = { n, calloc(n, sizeof(KDugum *)) };
    for (int i = 0; i < m; i++) {
        KDugum *d = malloc(sizeof *d);
        d->hedef = k[i].v; d->sonraki = g.bas[k[i].u]; g.bas[k[i].u] = d;     /* basa ekle */
    }
    return g;
}
```

Bellek $O(n + m)$, komşuları gezmek $O(\text{derece})$, kenar eklemek $O(1)$. Kenar sorgusu $O(\text{derece})$. Ders kitaplarının (CLRS, Sedgewick) standart gösterimi.

### CSR

**CSR** (compressed sparse row, sıkıştırılmış seyrek satır) bağlı listedeki bütün düğümleri tek bir diziye diziyor: önce 0'ın bütün komşuları, sonra 1'inkiler, ... İkinci bir dizi, her düğümün komşularının nerede **başladığını** tutuyor:

```c
/* 3) CSR (compressed sparse row): u'nun komsulari hedef[ofset[u] .. ofset[u+1]) araliginda, yan yana. */
typedef struct { int n, m; int *ofset, *hedef; } CSR;
static CSR csr_kur(int n, const Kenar *k, int m) {
    CSR g = { n, m, calloc(n + 1, sizeof(int)), malloc(m * sizeof(int)) };
    for (int i = 0; i < m; i++) g.ofset[k[i].u + 1]++;                 /* 1. gecis: derece say */
    for (int u = 0; u < n; u++) g.ofset[u + 1] += g.ofset[u];          /* onek toplami: baslangiclar */
    int *yaz = malloc(n * sizeof(int));
    memcpy(yaz, g.ofset, n * sizeof(int));
    for (int i = 0; i < m; i++) g.hedef[yaz[k[i].u]++] = k[i].v;       /* 2. gecis: yerlestir */
    free(yaz);
    return g;
}
```

Kurulum, Ders 9.7'deki **sayma sıralamasının** ta kendisi: kenarları kaynak düğüme göre sıralıyoruz. Önce her düğümün derecesi sayılıyor, sonra önek toplamı (`ofset[u+1] += ofset[u]`, Ders 6.10'daki kısmi toplamlar) her düğümün bölgesinin başlangıcını veriyor, sonra her kenar kendi bölgesindeki sıradaki boş yere yazılıyor. $O(n + m)$, iki geçiş, ve kenar başına `malloc` yok. (Hata kontrolleri kısalık için yok.)

`u`'nun derecesi `ofset[u+1] - ofset[u]`: $O(1)$. `ofset`'in $n + 1$ elemanlı olması bu formülü son düğüm için de geçerli kılıyor.

### Örnek graf, üç gösterimde

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined graf.c -o graf && ./graf
matris:
  0: 0 1 1 0 0
  1: 0 0 1 0 0
  2: 1 0 0 1 0
  3: 0 0 0 1 0
  4: 0 0 0 1 0
liste:
  0: -> 2 -> 1
  1: -> 2
  2: -> 3 -> 0
  3: -> 3
  4: -> 3
CSR:
  ofset: 0 2 3 5 6 7
  hedef: 1 2 2 0 3 3 3
  komsular(2): 0 3
```

Bağlı listede komşular **ters** sırada (başa ekleme); CSR'de kenar listesindeki sırada (sayma sıralaması kararlı). `komsular(2)`: `hedef[ofset[2] .. ofset[3])` = `hedef[3..5)` = `0 3`.

---

## 3. Ölçüm

Aynı grafın üç gösteriminde düğüm 0'dan BFS (Ders 8.5; kuyruk düz bir dizi). İki graf: **seyrek** (1 milyon düğüm, 10 milyon rastgele yönlü kenar, ortalama derece 10) ve **yoğun** (4096 düğüm, her kenar %50 olasılıkla, 8.4 milyon kenar).

```c
static long bfs_csr(const CSR *g) {
    memset(uzak, -1, g->n * sizeof(int)); int bas = 0, son = 0; long kenar = 0;
    uzak[0] = 0; kuyruk[son++] = 0;
    while (bas < son) { int u = kuyruk[bas++];
        for (int i = g->ofset[u]; i < g->ofset[u + 1]; i++) { int v = g->hedef[i]; kenar++; if (uzak[v] < 0) { uzak[v] = uzak[u] + 1; kuyruk[son++] = v; } } }
    return kenar;
}
```

(Bağlı liste ve matris sürümleri aynı iskeletle, sadece iç döngü farklı.)

```
$ cc -std=c11 -O2 -Wall olcum.c -o olcum && ./olcum
seyrek: n=1000000 m=10000000
  liste : kur 0.131 s  BFS 0.689 s  (9999644 kenar)  bellek ~168 MB (+malloc basliklari)
  CSR   : kur 0.058 s  BFS 0.054 s  (9999644 kenar)  bellek  44 MB
  matris: 125 GB olurdu
yogun : n=4096 m=8387820
  liste : kur 0.101 s  BFS 0.014 s  (8387820 kenar)  bellek ~134 MB (+malloc basliklari)
  CSR   : kur 0.035 s  BFS 0.003 s  (8387820 kenar)  bellek  34 MB
  matris:                BFS 0.052 s  (8387820 kenar)  bellek  2.1 MB
  matris, bit paralel:   BFS 0.0001 s  (4095 yeni dugum)
```

(Sanitizer'lı derleme de temiz bitiyor. "kenar" sütunu BFS'in gezdiği kenar sayısı; seyrek grafta 0'dan ulaşılamayan birkaç düğümün kenarları gezilmiyor.)

**Seyrek graf**:

- **CSR bağlı listeden 13 kat hızlı** ve 4 kat az bellek kullanıyor. Bağlı listede her kenar ayrı bir 16 baytlık `malloc` bloğu (artı başlık), ve bir düğümün komşuları bellekte dağınık: kenarlar rastgele sırayla eklendiği için `u`'nun ardışık iki komşu düğümü, aralarında milyonlarca başka ayırma olan iki farklı yerde. Her komşu bir cache kaçırması. CSR'de bir düğümün komşuları **yan yana**: Ders 8.2'deki "dizi mi liste mi" ölçümünün aynısı.
- Matris imkânsız: $10^{12}$ bit.

**Yoğun graf**:

- Matris **2.1 MB**, CSR'nin 16'da biri: her kenar 32 bit yerine 1 bit. Yarısı dolu bir matriste "kenar yok" bilgisi de "kenar var" kadar değerli.
- Ama matrisi bit bit taramak CSR'den yavaş (0.052 s): her bit için bir kaydırma ve maske.
- **Bit paralel BFS** ise 0.1 ms, CSR'den 30 kat hızlı. Fikir: bir satırın 64 bitlik sözcüğünü, "henüz görülmemiş düğümler" bitset'iyle **AND**'le. Sonuç, bu sözcükteki yeni komşuların kümesi; tek komutta 64 düğüm. Sonra bu kümenin bitlerini Ders 5.9'daki `ctz` ile tek tek çıkar:

```c
/* Bit paralel: satirin 64'luk sozcuklerini "henuz gorulmemis" maskesiyle AND'le, sadece yeni komsulari ctz ile cikar */
static long bfs_matris_bit(const Matris *g) {
    int W = g->W; uint64_t *gorulmemis = malloc(W * 8);
    for (int w = 0; w < W; w++) gorulmemis[w] = ~0ull;
    memset(uzak, -1, g->n * sizeof(int)); int bas = 0, son = 0; long yeni = 0;
    uzak[0] = 0; kuyruk[son++] = 0; gorulmemis[0] &= ~1ull;
    while (bas < son) { int u = kuyruk[bas++]; const uint64_t *satir = g->bit + (size_t)u * W;
        for (int w = 0; w < W; w++) {
            uint64_t x = satir[w] & gorulmemis[w];
            gorulmemis[w] &= ~x;
            while (x) { int v = w * 64 + __builtin_ctzll(x); x &= x - 1; uzak[v] = uzak[u] + 1; kuyruk[son++] = v; yeni++; }
        } }
    free(gorulmemis);
    return yeni;
}
```

Daha önce görülmüş komşulara hiç bakılmıyor; kenarlar tek tek **sayılmıyor** bile (çıktıda "4095 yeni düğüm"). Her düğüm için iş $O(n/64)$, toplam $O(n^2/64)$: 4096 düğümde 262 bin sözcük işlemi. Ders 5.20'deki bitboard'ların graf algoritmasına uygulanışı; satırları 64 bitlik sınırlara hizalamamızın sebebi de bu.

---

## 4. Hangisi ne zaman

| | Matris (bit) | Bağlı liste | CSR |
| --- | --- | --- | --- |
| Bellek | $n^2/8$ bayt | $\approx 8n + 16m$ + başlıklar | $4(n+1) + 4m$ |
| `u → v` var mı | $O(1)$ | $O(\deg u)$ | $O(\deg u)$, sıralıysa $O(\log \deg u)$ |
| Komşuları gez | $O(n)$, bit paralel $O(n/64)$ | $O(\deg u)$, dağınık | $O(\deg u)$, ardışık |
| Kenar ekle | $O(1)$ | $O(1)$ | $O(m)$: yeniden kur |
| Kenar sil | $O(1)$ | $O(\deg u)$ | $O(m)$ |

- **CSR**, kurulduktan sonra değişmeyen graflar için varsayılan seçim: yol ağları, web grafı, seyrek matrisler (Faz 11'deki bilimsel hesaplamada aynı format **seyrek matris-vektör çarpımı** için kullanılıyor; adı da oradan). Graf kütüphaneleri (Boost.Graph'ın `compressed_sparse_row_graph`'ı, GAP Benchmark Suite) bu formatta çalışıyor.
- **Dinamik graflar** için düğüm başına bir **dinamik dizi** (Ders 4.24): CSR'nin yerelliğinin çoğunu koruyup $O(1)$ amortize ekleme veriyor. Bağlı liste neredeyse hiçbir zaman en iyi seçim değil.
- **Matris**, yoğun ve küçük graflar için: $n$ birkaç bin, kenar oranı birkaç yüzdenin üstünde. Ayrıca Floyd–Warshall gibi bütün düğüm çiftleri üzerinde çalışan algoritmalar (Faz 9) ve geçişli kapanış (Ders 6.6'daki Warshall'ın bitlerle yazılışı) için doğal.
- **Kenar listesi**, Kruskal (Ders 8.18, Alıştırma 3) gibi kenarları sıralayıp sırayla işleyen algoritmalar için yeterli.

Derleyicide: bir fonksiyonun **kontrol akış grafı** (temel bloklar ve aralarındaki atlamalar) küçük, seyrek ve optimizasyon sırasında değişiyor; genelde her blokta ardıl ve öncül listeleri (dinamik dizi) tutuluyor. Kayıt ayırmadaki (register allocation) **girişim grafı** (interference graph; aynı anda canlı olan değişkenler) ise bazen yoğun ve hem kenar sorgusu hem komşu gezinmesi istiyor: LLVM'in eski kayıt ayırıcısı ve Chaitin–Briggs ayırıcıları hem bit matrisi hem komşuluk listesi tutuyordu (Faz 16).

---

## Alıştırmalar

**1** – Örnek grafı **yönsüz** kabul et (her kenar iki yönde). CSR'nin `ofset` ve `hedef` dizileri ne olur? `3→3` öz döngüsü nasıl saklanmalı?

**2** – CSR'de `u → v` kenar sorgusunu hızlandırmak için ne yapılabilir? Kurulumdan sonra her düğümün komşu listesini sırala; sorgu kaç adım sürer? Bu sıralamayı $O(n + m)$'de yapmanın bir yolu var mı?

**3** – Bir yönlü grafın **tersini** (bütün kenarları ters çevrilmiş grafı) CSR'den CSR'ye $O(n + m)$'de kur. Ters graf ne zaman gerekiyor?

**4** – Seyrek grafta bağlı liste BFS'i CSR'den 13 kat yavaştı. Bağlı listenin düğümlerini, `malloc` yerine kenarları **kaynak düğüme göre sıralı** bir sırayla ayrılan büyük bir diziden versek ne olur? Bu yapı CSR'den ne kadar farklı?

**5** – Bit matrisi ile CSR'nin bellek formüllerini karşılaştır. Kenar yoğunluğu $p = m / n^2$ hangi değerin üstündeyse matris daha az yer kaplar? Ölçümdeki yoğun graf ($p = 0.5$) ve seyrek graf ($p = 10^{-5}$) için kontrol et.

<details>
<summary>Cevaplar</summary>

**1** – Yönsüz grafta her `{u, v}` kenarı `u → v` ve `v → u` olarak iki kez saklanıyor. Yönlü grafın `0→2` ve `2→0` kenarları yönsüzde aynı kenar; tekilleştirince kenarlar {0,1}, {0,2}, {1,2}, {2,3}, {3,3}, {3,4}. Komşuluklar: 0: {1, 2}, 1: {0, 2}, 2: {0, 1, 3}, 3: {2, 3, 4}, 4: {3}. `ofset = 0 2 4 7 10 11`, `hedef = 1 2 | 0 2 | 0 1 3 | 2 3 4 | 3`. Öz döngü bir kez saklanmalı (iki yönü aynı kenar); iki kez saklanırsa düğümün derecesi 2 artar, ki bu bazı tanımlarda (öz döngü dereceye 2 katkı yapar) doğru, bazı algoritmalarda (BFS) zararsız, bazılarında (Euler yolu sayma) önemli. Kenar listesinden yönsüz CSR kurarken her kenar için iki yönlü kayıt üretip `u == v` durumunu ayrıca ele almak gerekiyor.

**2** – Sıralı komşu listesinde ikili arama: $O(\log \deg u)$ (Ders 4.2). Ortalama derecesi 10 olan bir grafta 3–4 adım, ve hepsi aynı bir iki cache satırında. Sıralamayı $O(n + m)$'de yapmak için kenar listesini önce **hedefe** göre sayma sıralamasıyla sırala, sonra kaynağa göre (CSR kurulumu): ikinci sıralama kararlı olduğu için her düğümün komşuları hedef sırasıyla gelir. İki geçişli radix sıralama (Ders 9.7). Alternatif olarak her listeyi ayrı ayrı `qsort` etmek $O(m \log d)$.

**3** – Ters grafta `v`'nin komşuları, orijinal grafta `v`'ye **gelen** kenarların kaynakları. CSR kurulumunun aynısı: önce her düğümün **giriş derecesini** say (`for` her `u`, her `v` in komşular(u): `ters_ofset[v+1]++`), önek toplamı al, sonra her `u → v` için `ters_hedef[yaz[v]++] = u`. İki geçiş, $O(n + m)$. Gerekiyor: Kosaraju'nun güçlü bağlı bileşen algoritması (Faz 9) grafı ve tersini geziyor; derleyicide bir temel bloğun **öncülleri** (hangi bloklardan buraya atlanıyor) dominator ağacı hesabı ve veri akışı analizinde gerekiyor (Faz 16); "bu dosyayı kim içeriyor" sorusu bağımlılık grafının tersi.

**4** – Düğümler kaynak sırasıyla ayrılırsa `u`'nun komşu düğümleri dizide yan yana oluyor, ve `sonraki` pointer'ları hep bir sonraki elemanı gösteriyor. Bu, CSR'nin her hedefe 8 baytlık bir `sonraki` pointer'ı eklenmiş hali: yerellik CSR'ninki gibi, bellek iki-üç kat fazla, ve gezinme her adımda bir pointer okuduğu için (bağımlı yükleme) CSR'nin ardışık indeksinden biraz yavaş. Ama bu sıralı ayırmayı yapabilmek için kenarların önceden bilinmesi gerekiyor; o zaman da CSR'yi kurmak daha basit. Bağlı listenin tek avantajı olan $O(1)$ ekleme, sıralı ayırmayla kayboluyor. Ders 8.21'deki arena allocator bu yaklaşımın daha genel hali: düğümler sırayla ayrılınca yerellik kendiliğinden geliyor.

**5** – Matris $n^2/8$ bayt, CSR yaklaşık $4n + 4m$ bayt. Matris daha küçük: $n^2/8 < 4m + 4n$, büyük $n$ için $m > n^2/32$, yani $p > 1/32 \approx \%3$. Yoğun graf ($p = 0.5$): matris 2.1 MB, CSR 34 MB, matris 16 kat küçük ($0.5 \cdot 32 = 16$). Seyrek graf ($p = 10^{-5}$): matris 125 GB, CSR 44 MB, CSR 2800 kat küçük. Gerçek dünyadaki büyük graflar (yol ağları, sosyal ağlar, web) neredeyse her zaman çok seyrek: düğüm sayısı arttıkça ortalama derece aşağı yukarı sabit kalıyor, yani $p \approx d/n$ sıfıra gidiyor.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 22.1: grafların gösterimi.
- Robert Sedgewick, *Algorithms in C, Part 5: Graph Algorithms* (3. baskı), Bölüm 17.
- Scott Beamer, Krste Asanović ve David Patterson, "The GAP Benchmark Suite", 2015: CSR tabanlı graf kıyaslama programları.
- Yousef Saad, *Iterative Methods for Sparse Linear Systems* (2. baskı), Bölüm 3.4: CSR ve diğer seyrek matris formatları.
- Preston Briggs, Keith Cooper ve Linda Torczon, "Improvements to Graph Coloring Register Allocation", *ACM TOPLAS* 16(3), 1994: girişim grafının bit matrisi ve komşuluk listesi ile birlikte tutulması.

**Sıradaki ders:** Skip list ve rastgele yapılar. Beklenen karmaşıklık analizi.
