---
title: "6.30 Graf teorisi temelleri"
description: "Graf, düğüm, kenar; yönlü ve yönsüz graflar; komşuluk matrisi, komşuluk listesi ve satır başına bitmask temsilleri; derece ve el sıkışma önsavı; yol, döngü, bağlılık; ağaçlar ve n − 1 kenar teoremi; DAG'ler ve topolojik sıralamayla bağı; graf renklendirme, kromatik sayı ve iki parçalı graflar; açgözlü renklendirme ve düğüm sırasının etkisi (taç grafı), geri izlemeli kesin çözüm; register tahsisinin bir girişim grafını renklendirmek olduğu ve küçük bir program için register atayan C kodu."
---

Bu fazda graflara defalarca rastladık ama adlarını koymadık. Ders 6.6'da bağıntıları oklarla çizdik; Ders 6.7'de bağımlılıkları topolojik olarak sıraladık; Ders 6.8'de bir programın bloklarını ve aralarındaki geçişleri bir sabit nokta ile gezdik; Ders 6.21'de Cayley tabloları, Ders 6.25'te matrisler gördük. Hepsinin ortak dili **graf**: nesneler ve aralarındaki bağlantılar.

Derleyici bir graf makinesi: kontrol akış grafı, çağrı grafı, bağımlılık grafı, dominator ağacı, SSA'daki def-use zincirleri, ve bu dersin sonundaki **girişim grafı**. Faz 8'de grafları veri yapısı olarak, Faz 9'da üzerlerindeki algoritmaları (en kısa yol, akış, eşleme) ayrıntılı göreceğiz. Bu ders kelime dağarcığını ve birkaç temel teoremi kuruyor, ve fazı derleyicinin en meşhur graf problemiyle kapatıyor.

---

## 1. Tanımlar

Bir **graf** $G = (V, E)$: bir **düğüm** (vertex) kümesi $V$ ve bir **kenar** (edge) kümesi $E$.

- **Yönsüz** graf: her kenar bir sırasız çift $\{u, v\}$. Arkadaşlık, yol ağı, "aynı anda canlı" ilişkisi.
- **Yönlü** graf: her kenar bir sıralı çift $(u, v)$, $u \to v$. Ders 6.6'daki bağıntıların ta kendisi: $V$ üzerinde bir bağıntı = yönlü bir graf.

Terimler:

- $u$ ile $v$ **komşu**: aralarında kenar var.
- **Derece** $\deg(v)$: $v$'ye değen kenar sayısı. Yönlü graflarda **giriş** ve **çıkış** derecesi.
- **Yol**: $v_0, v_1, \dots, v_k$, ardışık düğümler komşu. **Basit yol**: hiçbir düğüm tekrar etmiyor.
- **Döngü** (cycle): başı ve sonu aynı olan, en az bir kenarlı bir yol.
- **Bağlı** (yönsüz): her iki düğüm arasında bir yol var. Değilse graf **bileşenlere** ayrılıyor; "aynı bileşende olmak" bir denklik bağıntısı (Ders 6.6) ve bileşenler onun sınıfları.

Ders 6.6'nın geçişli kapanışı, yönlü grafta **erişilebilirlik**: $u$'dan $v$'ye bir yol var mı. Ders 6.8'deki sabit nokta yinelemesi tam olarak bunu hesaplıyordu.

---

## 2. Temsil

Üç yol, Ders 6.6'da ilk ikisini görmüştük:

| Temsil | Bellek | "$u$-$v$ kenarı var mı?" | "$v$'nin komşuları" |
| --- | --- | --- | --- |
| Komşuluk matrisi | $\Theta(\lvert V \rvert^2)$ | $O(1)$ | $\Theta(\lvert V \rvert)$ |
| Komşuluk listesi | $\Theta(\lvert V \rvert + \lvert E \rvert)$ | $O(\deg v)$ | $O(\deg v)$ |
| Satır başına bitmask | $\lvert V \rvert^2$ bit | $O(1)$ | 64'lük gruplarla `ctz` |

Gerçek graflar çoğunlukla **seyrek** ($|E| \ll |V|^2$): bir programın kontrol akış grafında her blok ortalama birkaç bloğa gidiyor. Seyrek graflar için liste; küçük ve yoğun graflar için bitmask. Bu dersin örnekleri küçük, Ders 6.5'teki gibi bitmask kullanıyoruz:

```c
#define MAXV 32
typedef struct { int n; uint32_t adj[MAXV]; } graph;   // adj[v]: v'nin komsulari (bitmask)

static void add_edge(graph *g, int u, int v) {          // yonsuz
    g->adj[u] |= 1u << v;
    g->adj[v] |= 1u << u;
}
```

Derece, `__builtin_popcount(g->adj[v])` (Ders 5.8).

---

## 3. İlk teoremler

**Önsav (el sıkışma).** Yönsüz bir grafta $\sum_{v} \deg(v) = 2|E|$.

**Kanıt.** Her kenar $\{u, v\}$ iki dereceye katkı veriyor: $u$'nunkine ve $v$'ninkine. Ders 6.14'teki **çift sayma**: kenar–uç çiftlerini önce kenarlara göre ($2|E|$), sonra düğümlere göre ($\sum \deg$) say. $\blacksquare$

**Sonuç.** Tek dereceli düğümlerin sayısı çifttir. (Toplam çift; çift dereceliler çift katkı veriyor, tek derecelilerin toplamı da çift olmalı.) Bir partide herkesin tokalaştığı kişi sayısının tek olduğu grup, çift sayıda kişiden oluşuyor.

Programla kontrol (bölüm 5'teki graf):

```
kenar 6, derece toplami 12
```

### Ağaçlar

Bağlı ve döngüsüz yönsüz bir grafa **ağaç** denir. Ders 6.16'daki parse ağaçları, Ders 6.4'teki asal ayrıştırma ağacı, Ders 6.13'teki özyineleme ağacı, dosya sistemleri.

**Teorem.** $n$ düğümlü bir ağacın tam olarak $n - 1$ kenarı var.

**Kanıt** (tümevarım, Ders 6.4). $n = 1$: kenar yok. ✓ $n \ge 2$: en az iki **yaprak** (derecesi 1 olan düğüm) var: en uzun basit yolun iki ucu (yaprak olmasalardı ya yol uzardı ya döngü oluşurdu). Bir yaprağı ve kenarını sil: geriye $n - 1$ düğümlü bir ağaç kalıyor (hâlâ bağlı ve döngüsüz), hipoteze göre $n - 2$ kenarlı. Silinen kenarla $n - 1$. $\blacksquare$

Sonuç: bir ağaç, $n$ düğümü bağlı tutan **en az** kenarlı yapı. Bir kenar silersen bağlılık bozuluyor; bir kenar eklersen döngü oluşuyor. Ağaçların her iki düğümü arasında **tek** bir basit yol var; dosya sistemindeki "yol" (path) kelimesinin kökeni.

### DAG'ler

Yönlü ve **döngüsüz** graf: DAG (directed acyclic graph). Ders 6.7'deki teorem: bir yönlü grafın topolojik sıralaması var $\iff$ DAG. Bağımlılık grafları (make, Ders 2.11), bir ifadenin ortak alt ifadelerini paylaşan hali (Faz 16'da göreceğimiz değer numaralandırma), bir devre şeması: hepsi DAG. Kahn algoritmasının "hazır düğüm kalmadı" çıkışı, grafta bir döngü olduğunun kanıtıydı.

---

## 4. Renklendirme

Bir grafın düğümlerine renk ata ki **komşu** düğümler farklı renkte olsun. Bunu yapan en az renk sayısına **kromatik sayı** $\chi(G)$ denir.

- $\chi = 1$: hiç kenar yok.
- $\chi \le 2$: grafın **iki parçalı** (bipartite) olması; düğümler iki gruba ayrılıyor ve her kenar gruplar arasında. **Teorem**: bir graf iki parçalıdır $\iff$ tek uzunlukta döngüsü yoktur. Kontrol etmesi kolay (bir BFS/DFS ile, Faz 9).
- $\chi = n$: $n$ düğümün hepsi birbirine bağlı (tam graf $K_n$).
- **Dört renk teoremi** (1976): düzlemde kesişmeden çizilebilen her graf 4 renkle boyanabilir. Kanıtı bilgisayar yardımıyla yapılan ilk büyük teorem; Ders 6.3'teki "kanıt" kavramını tartışmaya açtı.

Genel olarak $\chi(G) \le k$ mi sorusu, $k \ge 3$ için **NP-tam**: Ders 6.1'deki SAT ile aynı zorluk sınıfında; bilinen hiçbir algoritma her grafta hızlı değil. Küçük graflar için geri izleme (Ders 6.7'deki bütün topolojik sıralamaları gezmenin akrabası) kesin cevabı veriyor:

```c
// k renk yeterli mi? geri izleme
static bool try_color(const graph *g, int v, int k, int *color) {
    if (v == g->n) return true;
    for (int c = 0; c < k; c++) {
        bool ok = true;
        for (int u = 0; u < v && ok; u++)
            if (((g->adj[v] >> u) & 1) && color[u] == c) ok = false;
        if (ok) { color[v] = c; if (try_color(g, v + 1, k, color)) return true; }
    }
    return false;
}

static int chromatic(const graph *g) {
    int color[MAXV];
    for (int k = 1; ; k++) if (try_color(g, 0, k, color)) return k;
}
```

Büyük graflar için **açgözlü** (greedy) renklendirme: düğümleri bir sırayla gez, her birine komşularının kullanmadığı en küçük rengi ver. Komşuların renklerini bir bitmask'te topla; ilk boş renk, maskenin tersindeki en sağdaki 1 (Ders 5.9'daki `ctz`):

```c
// en kucuk renk: komsularin kullanmadigi ilk renk. order: dugum sirasi
static int greedy_color(const graph *g, const int *order, int *color) {
    int used = 0;
    for (int i = 0; i < g->n; i++) color[i] = -1;
    for (int k = 0; k < g->n; k++) {
        int v = order[k];
        uint32_t taken = 0;
        for (int u = 0; u < g->n; u++)
            if (((g->adj[v] >> u) & 1) && color[u] >= 0) taken |= 1u << color[u];
        int c = __builtin_ctz(~taken);                    // ilk bos renk (Ders 5.9)
        color[v] = c;
        if (c + 1 > used) used = c + 1;
    }
    return used;
}
```

Açgözlü en fazla $\max \deg + 1$ renk kullanıyor (her düğümün en fazla $\max\deg$ komşusu, biri mutlaka boş). Ama sonuç **sıraya** bağlı. **Taç grafı**: iki grup $\{0, 1, 2, 3\}$ ve $\{4, 5, 6, 7\}$, $i$ ile $4 + j$ arasında $i \ne j$ iken kenar. İki parçalı, $\chi = 2$.

```
tac grafi: iyi sira 2 renk, kotu sira 4 renk, kromatik 2
```

Önce bir grubu sonra öbürünü gezersen 2 renk. $0, 4, 1, 5, 2, 6, 3, 7$ sırasıyla dönüşümlü gezersen her yeni çift yeni bir renk istiyor: 4 renk. $2n$ düğümlü taçta kötü sıra $n$ renk kullanıyor; açgözlü, optimumdan **keyfi** kötü olabilir. Pratikte iyi sıralar seçmek (en yüksek dereceliler önce, ya da aşağıdaki Chaitin yöntemi) çoğu grafta optimuma yakın sonuç veriyor.

---

## 5. Register tahsisi

Bir işlemcinin az sayıda register'ı var (RISC-V'de 32, x86-64'te 16 genel amaçlı; Faz 7). Bir programın ise yüzlerce değişkeni ve geçici değeri. Derleyici her değeri bir register'a koymak istiyor; ama **aynı anda canlı** (ikisi de daha sonra okunacak) iki değer aynı register'ı paylaşamaz.

**Girişim grafı** (interference graph): her değişken bir düğüm; aynı anda canlı olan iki değişken arasında bir kenar. Register tahsisi = bu grafı $k$ renkle (register sayısı) boyamak. Chaitin'in 1981'deki fikri; bugün de gcc ve LLVM'in tahsis algoritmalarının temeli.

Küçük bir program:

```c
a = 1;
b = 2;
c = a + b;
d = a * 2;     // a'nin son kullanimi
e = c + d;     // c ve d'nin son kullanimi
f = b + e;     // b ve e'nin son kullanimi
return f;
```

Her atamada, o anda canlı olan (daha sonra okunacak) değişkenleri yaz; atanan değişken onların hepsiyle çakışıyor:

| Atama | O anda canlı olanlar | Eklenen kenarlar |
| --- | --- | --- |
| `b = 2` | a | a–b |
| `c = a + b` | a, b | c–a, c–b |
| `d = a * 2` | b, c (a burada ölüyor) | d–b, d–c |
| `e = c + d` | b (c, d burada ölüyor) | e–b |
| `f = b + e` | (b, e burada ölüyor) | yok |

Bu "canlılık" bilgisini elle çıkardık; Ders 16.5'te Ders 6.8'deki sabit nokta çerçevesiyle otomatik hesaplayacağız (canlılık analizi, geri yönlü bir veri akışı problemi).

```c
graph g = { 6, {0} };
add_edge(&g, 0, 1);              // a, b
add_edge(&g, 0, 2); add_edge(&g, 1, 2);   // c tanimlanirken a, b canli
add_edge(&g, 1, 3); add_edge(&g, 2, 3);   // d tanimlanirken b, c canli (a son kullanim)
add_edge(&g, 1, 4);              // e tanimlanirken b canli
```

```
acgozlu: 3 register: a=r0 b=r1 c=r2 d=r0 e=r0 f=r0
kromatik sayi: 3
```

Altı değişken, üç register. `d`, `a`'nın register'ını (`r0`) alıyor, çünkü `a` `d` tanımlanırken ölüyor; `e` ve `f` de aynı register'ı yeniden kullanıyor. Kromatik sayı 3 (a, b, c birbirine bağlı bir üçgen; üçünün de farklı register'a ihtiyacı var), açgözlü optimumu buldu.

Register'lar yetmezse ($\chi > k$) bazı değişkenler belleğe (yığına) **taşınıyor** (spill): her kullanımdan önce yükle, her atamadan sonra sakla (Ders 7.11'de assembly'de göreceğiz). Hangi değişkenin taşınacağı, en çok kullanılan değişkenleri register'da tutmaya çalışan bir maliyet hesabı. Chaitin'in yöntemi: derecesi $k$'dan küçük bir düğüm varsa, o **her zaman** boyanabilir (komşuları en fazla $k-1$ renk kullanır); onu grafa en son eklenmek üzere çıkar, kalan grafla devam et. Bu, açgözlüye **iyi bir sıra** seçmenin yolu ve taç grafındaki tuzağa düşmüyor.

---

## Alıştırmalar

**1** – 5 düğümlü ve her düğümün derecesi 3 olan bir graf var mı? (El sıkışma önsavı.) 6 düğümlüsü?

**2** – $n$ düğümlü bir yönsüz grafta en fazla kaç kenar olabilir? Kaç farklı yönsüz graf var (düğümler etiketli)? Bunu Ders 6.14 ve 6.5 ile ilişkilendir.

**3** – Bir grafın iki parçalı olup olmadığını kontrol eden bir fonksiyon yaz: bir düğümü 0 ile boya, komşularını 1, onların komşularını 0, ... Çelişki olursa iki parçalı değil. Taç grafında ve 5 düğümlü bir döngüde dene.

**4** – Bölüm 5'teki programa bir satır ekle: `g = a + f;` ve `a`'nın son kullanımını buraya kaydır. Girişim grafını yeniden kur. Kaç register gerekiyor? 2 register'lı bir makinede hangi değişkeni taşırdın?

**5** – Chaitin'in sadeleştirme adımını yaz: derecesi $< k$ olan bir düğümü bul, bir yığına it ve grafdan çıkar (komşularının derecelerini azalt); tekrarla. Graf boşalınca yığından çıkararak açgözlü boya. Taç grafında $k = 2$ ile dene. Hiçbir düğümün derecesi $< k$ değilse ne yaparsın?

<details>
<summary>Cevaplar</summary>

**1** – 5 düğüm, hepsi derece 3: toplam 15, tek. El sıkışmaya göre toplam $2|E|$, çift olmalı: **yok**. 6 düğümlüsü var: toplam 18, 9 kenar; örneğin $K_{3,3}$ (iki üçlü grup, gruplar arası bütün kenarlar) ya da bir altıgen artı üç köşegen.

**2** – En fazla $\binom{n}{2}$ kenar ($K_n$). Her olası kenar var ya da yok: $2^{\binom{n}{2}}$ graf. $n$ düğümlü graflar, $\binom{n}{2}$ elemanlı kenar kümesinin alt kümeleri (Ders 6.5). $n = 5$'te $2^{10} = 1024$; $n = 10$'da $2^{45}$. Bütün grafları denemek çok küçük $n$'ler dışında imkânsız.

**3** –

```c
static bool bipartite(const graph *g) {
    int side[MAXV];
    for (int v = 0; v < g->n; v++) side[v] = -1;
    for (int s = 0; s < g->n; s++) {
        if (side[s] >= 0) continue;
        side[s] = 0;
        int stack[MAXV], top = 0; stack[top++] = s;
        while (top) {
            int v = stack[--top];
            for (int u = 0; u < g->n; u++) {
                if (!((g->adj[v] >> u) & 1)) continue;
                if (side[u] < 0) { side[u] = 1 - side[v]; stack[top++] = u; }
                else if (side[u] == side[v]) return false;   // tek dongu
            }
        }
    }
    return true;
}
```

Taç grafı: evet. 5'li döngü: hayır (tek uzunluklu döngü; $\chi = 3$). Dış döngü, bağlı olmayan graflarda her bileşeni ayrı başlatıyor. Her düğüm yığına en fazla bir kez giriyor (ilk boyandığında), dolayısıyla yığın `MAXV`'yi aşmıyor.

**4** – `a` artık `g = a + f`'ye kadar canlı: `d`, `e`, `f` tanımlanırken de canlı. Yeni kenarlar: a–d, a–e, a–f. a, b, c, d arasındaki altı kenarın (a–b, a–c, a–d, b–c, b–d, c–d) hepsi var: bu dört değişken bir $K_4$ oluşturuyor ve 4 register gerekiyor. 2 register'da: en uzun yaşayan ve en az kullanılanı taşı; burada `a` (tanımdan son kullanıma kadar her şeyle çakışıyor ama sadece iki kez okunuyor). `a`'yı taşıyınca kalan graf ($b, c, d, e, f$) yine bir $b, c, d$ üçgeni içeriyor; 2 register için bir değişken daha taşımak gerekiyor.

**5** –

```c
static bool chaitin(const graph *g0, int k, int *color) {
    graph g = *g0; uint32_t alive = (g.n == 32) ? ~0u : (1u << g.n) - 1;
    int stack[MAXV], top = 0;
    while (alive) {
        int pick = -1;
        for (int v = 0; v < g.n; v++)
            if (((alive >> v) & 1) && __builtin_popcount(g.adj[v] & alive) < k) { pick = v; break; }
        if (pick < 0) return false;            // her dugumun derecesi >= k: tasima adayi sec
        stack[top++] = pick; alive &= ~(1u << pick);
    }
    int order[MAXV]; for (int i = 0; i < top; i++) order[i] = stack[top - 1 - i];   // ters sira
    return greedy_color(g0, order, color) <= k;
}
```

Taç grafında her düğümün derecesi 3; $k = 2$ ile ilk adımda hiçbir düğüm $< 2$ değil ve yöntem duruyor, oysa graf 2 renkle boyanabiliyor. Chaitin'in sadeleştirmesi **yeterli** bir koşul, gerekli değil. Takılınca: bir düğümü "taşınabilir" diye işaretleyip yine de yığına it (Briggs'in iyimser renklendirmesi, 1994); boyama sırasında belki yine de renk bulunur, bulunmazsa o zaman gerçekten taşı. LLVM ve gcc'nin tahsis algoritmaları bu fikrin üzerine kurulu.

</details>

---

## Faz 6 bitti

Bu fazda derleyici mühendisliğinin dayandığı matematiği kurduk. Önce **dil**: önermeler, niceleyiciler ve kanıt teknikleri; tümevarımın döngü değişmezi olduğunu gördük. Sonra **yapılar**: kümeler, bağıntılar, sıralamalar ve kafesler; Knaster–Tarski ile veri akışı analizinin neden sonlandığını kanıtladık. **Sayma ve büyüme**: toplamlar, özyinelemeli bağıntılar, $O$/$\Theta$, Master teoremi, kombinatorik ve üreteç fonksiyonları; algoritmaların maliyetini hesaplamak artık bir cebir problemi. **Sayılar**: bölünebilirlik, modüler aritmetik, modüler ters, ÇKT, Fermat ve Miller–Rabin. **Cebir**: gruplar, Lagrange ve RSA, halkalar ve bilgisayar tamsayısının $\mathbb{Z}/2^n\mathbb{Z}$ olması, sonlu cisimler ve $GF(2^8)$. **Doğrusal cebir**: matrisler, eliminasyon, determinant, ve unimodüler döngü dönüşümleri. Son olarak **olasılık** ve **graflar**.

Her derste bir C programı, matematiğin makinede ne anlama geldiğini gösterdi: bazen birebir (mod $2^{32}$ halkası), bazen yaklaşık (kayan nokta, ne halka ne cisim), bazen de yanıltıcı (Binet formülü $n = 71$'de yanıldı, açgözlü renklendirme taçta iki kat renk kullandı).

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), Bölüm 10–11: graflar ve ağaçlar.
- Gregory Chaitin, "Register Allocation & Spilling via Graph Coloring", *SIGPLAN Notices* 17(6), 1982.
- Preston Briggs, Keith Cooper & Linda Torczon, "Improvements to Graph Coloring Register Allocation", *ACM TOPLAS* 16(3), 1994.
- Keith Cooper & Linda Torczon, *Engineering a Compiler* (3. baskı), Bölüm 13: register tahsisi.

**Sıradaki faz:** Bilgisayar mimarisi ve assembly. C kodunun makine komutlarına nasıl dönüştüğünü okumak ve yazmak; bu fazda kurduğumuz register tahsisinin, mod $2^n$ aritmetiğinin ve bayrakların donanımdaki karşılığı.
