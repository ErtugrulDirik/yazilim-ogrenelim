---
title: "9.15 Topolojik sıralama"
description: "Bağımlılıkları olan işleri, her iş bağımlı olduğu işlerden sonra gelecek şekilde dizmek: yönlü döngüsüz graflar (DAG) ve tek bir döngünün sıralamayı imkânsız kılması; Kahn algoritması (giriş derecesi sıfır olanları kuyrukla çıkar) ve DFS bitiş sırasının tersi, ikisinin de O(n + m) olduğu ve doğruluk ispatları; küçük bir Makefile'ın derleme sırası, döngüsel bir #include'da Kahn'ın takılıp kalan düğümleri göstermesi ve DFS'in geri kenarı bulması; 1 milyon düğüm, 10 milyon kenarlı bir DAG'da iki yöntemin de doğrulanmış sonucu; paralel derleme seviyeleri."
---

`make` bir programı derlerken her `.o` dosyasını kendi `.c` ve `.h` dosyalarından **sonra**, programı bütün `.o`'lardan sonra üretmek zorunda. Bir paket yöneticisi bir paketi bağımlılıklarından sonra kuruyor; bir derleyici modülleri, içe aktardıkları modüllerden sonra derliyor; bir elektronik tablo bir hücreyi, formülünün başvurduğu hücrelerden sonra hesaplıyor. Hepsi aynı problem: bir **bağımlılık grafının** düğümlerini, her kenar $u \to v$ için $u$ $v$'den **önce** gelecek şekilde dizmek. Bu dizilişe **topolojik sıra** denir.

Böyle bir sıra ancak graf **döngüsüz** ise var: $a \to b \to c \to a$ döngüsünde $a$, $c$'den hem önce hem sonra gelmeli. Yönlü döngüsüz graflara **DAG** (directed acyclic graph) denir. Ders 9.14'te DFS ile döngü tespit etmeyi gördük; bu ders aynı gezinmenin döngü yoksa bir topolojik sıra da verdiğini gösteriyor, ve bir de ondan bağımsız ikinci bir algoritma yazıyor.

---

## 1. Kod

```c
/* Topolojik siralama iki yolla: Kahn (giris derecesi + kuyruk) ve DFS (bitis sirasinin tersi) */
#include <stdio.h>
#include "graf.h"

/* KAHN: giris derecesi 0 olanlar hazir; birini cikar, kenarlarini sil, yeni 0'lari kuyruga ekle */
static int kahn(const Graf *g, int *sira) {          /* doner: siralanan dugum sayisi (< n ise dongu var) */
    int n = g->n, *der = calloc(n, sizeof *der), bas = 0, son = 0;
    for (int i = 0; i < g->m; i++) der[g->hedef[i]]++;
    for (int v = 0; v < n; v++) if (der[v] == 0) sira[son++] = v;   /* sira dizisi ayni zamanda kuyruk */
    while (bas < son) {
        int u = sira[bas++];
        for (int i = g->ofset[u]; i < g->ofset[u + 1]; i++)
            if (--der[g->hedef[i]] == 0) sira[son++] = g->hedef[i];
    }
    free(der);
    return son;
}

/* DFS: bir dugum, ondan ulasilan her sey bittikten sonra biter. Bitis sirasinin TERSI topolojik sira. */
static int dfs_topo(const Graf *g, int *sira, int *dongu_u, int *dongu_v) {
    int n = g->n, *renk = calloc(n, sizeof *renk), *yigin = malloc(n * sizeof *yigin), *yer = malloc(n * sizeof *yer);
    int k = n, tepe = 0;                              /* sira'yi sondan basa dolduruyoruz */
    *dongu_u = -1;
    for (int s = 0; s < n; s++) {
        if (renk[s]) continue;
        yigin[tepe++] = s; renk[s] = 1; yer[s] = g->ofset[s];
        while (tepe) {
            int u = yigin[tepe - 1];
            if (yer[u] < g->ofset[u + 1]) {
                int v = g->hedef[yer[u]++];
                if (renk[v] == 0) { renk[v] = 1; yer[v] = g->ofset[v]; yigin[tepe++] = v; }
                else if (renk[v] == 1 && *dongu_u < 0) { *dongu_u = u; *dongu_v = v; }   /* geri kenar (Ders 9.14) */
            } else { renk[u] = 2; sira[--k] = u; tepe--; }
        }
    }
    free(renk); free(yigin); free(yer);
    return *dongu_u < 0;
}

#ifndef KUTUPHANE
/* Kucuk bir Makefile: hedef: bagimliliklar */
static const char *ad[] = { "program", "main.o", "liste.o", "tablo.o", "main.c", "liste.c", "tablo.c", "liste.h", "tablo.h", "ortak.h" };
enum { PROGRAM, MAIN_O, LISTE_O, TABLO_O, MAIN_C, LISTE_C, TABLO_C, LISTE_H, TABLO_H, ORTAK_H, N };

int main(void) {
    /* kenar u -> v: "u, v'den once hazir olmali" (v, u'ya bagimli) */
    Kenar k[] = {
        { MAIN_O, PROGRAM }, { LISTE_O, PROGRAM }, { TABLO_O, PROGRAM },
        { MAIN_C, MAIN_O }, { LISTE_H, MAIN_O }, { TABLO_H, MAIN_O },
        { LISTE_C, LISTE_O }, { LISTE_H, LISTE_O },
        { TABLO_C, TABLO_O }, { TABLO_H, TABLO_O },
        { ORTAK_H, LISTE_H }, { ORTAK_H, TABLO_H } };
    Graf g = graf_kur(N, k, 12);
    int s[N], du, dv;
    int c = kahn(&g, s);
    printf("Kahn (%d/%d):", c, N); for (int i = 0; i < c; i++) printf(" %s", ad[s[i]]); printf("\n");
    dfs_topo(&g, s, &du, &dv);
    printf("DFS       :"); for (int i = 0; i < N; i++) printf(" %s", ad[s[i]]); printf("\n");
    graf_birak(&g);

    /* dongu: ortak.h, liste.h'yi include ediyor (liste.h zaten ortak.h'yi ediyordu) */
    Kenar k2[13]; memcpy(k2, k, sizeof k); k2[12] = (Kenar){ LISTE_H, ORTAK_H };
    g = graf_kur(N, k2, 13);
    c = kahn(&g, s);
    printf("dongulu: Kahn %d/%d dugum siralayabildi; kalanlar:", c, N);
    int sirada[N] = { 0 }; for (int i = 0; i < c; i++) sirada[s[i]] = 1;
    for (int v = 0; v < N; v++) if (!sirada[v]) printf(" %s", ad[v]); printf("\n");
    if (!dfs_topo(&g, s, &du, &dv)) printf("dongulu: DFS geri kenar buldu: %s -> %s\n", ad[du], ad[dv]);
    graf_birak(&g);
}
#endif
```

(`graf.h`, Ders 9.14'teki CSR.)

### Kahn algoritması

Arthur Kahn (1962): **giriş derecesi** sıfır olan bir düğüm (hiçbir şeye bağımlı olmayan) her zaman listenin başına konabilir. Onu çıkar ve kenarlarını grafdan sil; bu, bazı başka düğümlerin giriş derecesini sıfıra indirebilir. Tekrarla.

Değişmez: `sira[0..bas)`'taki her düğüm, bütün öncülleri kendisinden önce gelecek şekilde yerleşmiş; ve bir düğüm kuyruğa tam olarak bütün öncülleri çıkarıldığında giriyor (`--der[...] == 0`). Grafta döngü varsa döngüdeki düğümlerin hiçbirinin giriş derecesi sıfıra inmiyor (her biri döngüdeki bir öncülü bekliyor) ve kuyruk onlar sıralanmadan boşalıyor. Dönen sayı $n$'den küçükse döngü var; sıralanamayan düğümler, döngüdekiler ve onlara (dolaylı olarak) bağımlı olanlar.

`sira` dizisi aynı zamanda kuyruk: çıkarılan düğümler zaten sırayla dizinin başında. $O(n + m)$.

### DFS ile

Ders 9.14'ün DFS'i bir düğümü, ondan **ulaşılabilen her şey** bittikten sonra bitiriyor (siyah). Bir DAG'da $u \to v$ kenarı varsa: $v$ beyazsa $u$'nun torunu olur ve $u$'dan önce biter; $v$ siyahsa zaten bitmiştir; $v$ gri olamaz, çünkü bu bir geri kenar, yani döngü olurdu. Her durumda $\text{bitiş}(v) < \text{bitiş}(u)$. O halde düğümleri **bitiş zamanlarının tersine** dizmek, her kenarı ileri doğru yöneltiyor: topolojik sıra. Kod düğümleri bittikleri anda `sira`'nın **sonundan** başa doğru yazıyor. Gri bir düğüme kenar (geri kenar) görülürse döngü raporlanıyor.

---

## 2. Bir Makefile

```
program: main.o liste.o tablo.o
main.o:  main.c liste.h tablo.h
liste.o: liste.c liste.h
tablo.o: tablo.c tablo.h
liste.h: ortak.h        (liste.h, ortak.h'yi #include ediyor)
tablo.h: ortak.h
```

Kenar $u \to v$, "$u$, $v$'den önce hazır olmalı" demek ($v$, $u$'ya bağımlı).

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined topo.c -o topo && ./topo
Kahn (10/10): main.c liste.c tablo.c ortak.h liste.h tablo.h liste.o main.o tablo.o program
DFS       : ortak.h tablo.h liste.h tablo.c liste.c main.c tablo.o liste.o main.o program
dongulu: Kahn 3/10 dugum siralayabildi; kalanlar: program main.o liste.o tablo.o liste.h tablo.h ortak.h
dongulu: DFS geri kenar buldu: ortak.h -> liste.h
```

İki algoritma iki **farklı** ama ikisi de geçerli sıra veriyor: bir DAG'ın genelde birçok topolojik sırası var. Kahn kaynak dosyalarıyla başlıyor (hiçbir şeye bağımlı değiller), DFS ise önce bir dalı sonuna kadar götürüyor.

Sonra `ortak.h`'nin `liste.h`'yi include ettiğini ekledik: `liste.h → ortak.h → liste.h`, bir **döngüsel include**. Kahn sadece üç kaynak dosyasını sıralayabildi; geri kalan yedi düğüm (döngüdeki iki başlık ve onlara bağımlı her şey) giriş derecesi sıfıra hiç inmeden kaldı. DFS döngüyü bir geri kenar olarak buldu; Ders 9.14'ün Alıştırma 3'ündeki gibi `ebeveyn` zinciriyle döngünün tamamı yazdırılabilirdi. GNU Make'in `Circular liste.h <- ortak.h dependency dropped.` uyarısı tam olarak bu. (C başlıklarında döngüsel include'u `#ifndef` koruyucuları "çözüyor", ama sadece dosyanın ikinci kez açılmasını engelleyerek; tanımların sırası yine bozuk olabiliyor.)

---

## 3. Büyük bir DAG

1 milyon düğüm ve 10 milyon kenarlı rastgele bir DAG (düğümler gizli bir rastgele permütasyona göre sıralanıp sadece "ileri" kenarlar konuyor ki döngü olmasın). Her iki sıra için **doğrulama**: her kenarın kaynağı, hedefinden önce mi? Sonra bir $a \to b \to c$ yolu bulunup $c \to a$ kenarı ekleniyor: kesin bir döngü.

```c
int main(void) {
    int n = 1000000; long m = 10000000;
    /* DAG: gizli rastgele bir permutasyona gore sadece "ileri" kenarlar */
    int *p = malloc(n * sizeof *p); for (int i = 0; i < n; i++) p[i] = i;
    uint64_t x = 88172645463325252ull;
    #define R() (x ^= x << 13, x ^= x >> 7, x ^= x << 17, x)
    for (int i = n - 1; i > 0; i--) { int j = (int)(R() % (uint64_t)(i + 1)), t = p[i]; p[i] = p[j]; p[j] = t; }
    Kenar *k = malloc(m * sizeof *k);
    for (long i = 0; i < m; i++) { int a = (int)(R() % (uint64_t)n), b = (int)(R() % (uint64_t)n); if (a == b) b = (b + 1) % n; if (a > b) { int t = a; a = b; b = t; } k[i] = (Kenar){ p[a], p[b] }; }
    Graf g = graf_kur(n, k, (int)m);
    int *s = malloc(n * sizeof *s), du, dv;
    double t0 = simdi(); int c = kahn(&g, s); double t1 = simdi();
    printf("Kahn: %d/%d dugum, %.3f s, gecerli: %s\n", c, n, t1 - t0, c == n && gecerli(&g, s) ? "evet" : "HAYIR");
    t0 = simdi(); int ok = dfs_topo(&g, s, &du, &dv); t1 = simdi();
    printf("DFS : dongu %s, %.3f s, gecerli: %s\n", ok ? "yok" : "VAR", t1 - t0, ok && gecerli(&g, s) ? "evet" : "HAYIR");
    /* a -> b -> c yolu bul, c -> a ekle: kesin bir dongu */
    long i = 0;
    while (g.ofset[k[i].v] == g.ofset[k[i].v + 1]) i++;     /* ucunun cikis kenari olan bir a -> b */
    int a = k[i].u, b = k[i].v, cc = g.hedef[g.ofset[b]];
    k = realloc(k, (m + 1) * sizeof *k); k[m] = (Kenar){ cc, a };
    graf_birak(&g); g = graf_kur(n, k, (int)m + 1);
    c = kahn(&g, s); ok = dfs_topo(&g, s, &du, &dv);
    printf("%d -> %d -> %d -> %d dongusu eklendi: Kahn %d/%d dugum siraladi, DFS %s (geri kenar %d -> %d)\n", a, b, cc, a, c, n, ok ? "dongu bulamadi" : "dongu buldu", du, dv);
}
```

```
$ cc -std=c11 -O2 -Wall -Wextra buyuk.c -o buyuk && ./buyuk
Kahn: 1000000/1000000 dugum, 0.071 s, gecerli: evet
DFS : dongu yok, 0.097 s, gecerli: evet
450792 -> 555274 -> 885382 -> 450792 dongusu eklendi: Kahn 535305/1000000 dugum siraladi, DFS dongu buldu (geri kenar 555274 -> 885382)
```

(Sanitizer'lı derleme temiz.) İki algoritma da 70–100 ms'de geçerli bir sıra veriyor. Tek bir döngü, Kahn'ın düğümlerin neredeyse yarısını sıralayamamasına yetti: döngüye dolaylı olarak bağımlı her şey takıldı. DFS döngünün kenarlarından birini geri kenar olarak buldu; hangisi olduğu, gezinmenin döngüye hangi düğümden girdiğine bağlı.

| | Kahn | DFS |
| --- | --- | --- |
| Zaman, bellek | $O(n + m)$, giriş derecesi dizisi + kuyruk | $O(n + m)$, renkler + yığın |
| Döngü olunca | Sıralanamayan düğümler kalıyor (hangileri takıldı) | Bir geri kenar (döngünün kendisi) |
| Sıra seçimi | Kuyruk yerine öncelik kuyruğu: istenen sıra (Alıştırma 4) | Gezinme sırasına bağlı |
| Paralellik | Doğal: aynı anda hazır olanlar bir "seviye" (Alıştırma 2) | Yok |
| Artımlı | Kolay: tamamlanan işin kenarlarını sil | Zor |

Gerçek derleme sistemleri (Make, Ninja, Bazel) Kahn'ın bir varyantını çalıştırıyor: hazır olan işlerin kuyruğu, ve bir iş bitince ona bağımlı işlerin sayaçlarını azaltmak. `make -j8`, kuyrukta aynı anda en fazla sekiz işi çalıştırıyor.

---

## Alıştırmalar

**1** – Bölüm 2'deki Makefile grafının kaç farklı topolojik sırası var? (Sayması zor olabilir; en azından neden birden çok olduğunu ve hangi koşulda **tek** olacağını açıkla.)

**2** – `make -j` ile sınırsız sayıda iş aynı anda çalışabilseydi, Bölüm 2'deki proje en az kaç **turda** derlenirdi? Kahn'ı seviye seviye çalıştırarak bul. Bu sayı grafın hangi özelliği?

**3** – Her işin bir süresi var (derleme süresi gibi). Sınırsız paralellikte bütün projenin en erken bitiş zamanı, grafın en uzun (ağırlıklı) yolu: **kritik yol**. Topolojik sırayla bir DP olarak nasıl hesaplarsın? Genel graflarda en uzun yol NP-zor; DAG'da neden kolay?

**4** – Birden fazla geçerli sıra varken, sözlük sırasına göre **en küçük** topolojik sırayı istiyorsun (her adımda hazır olanların en küçük numaralısı). Kahn'ı nasıl değiştirirsin? Maliyet ne olur?

**5** – **Artımlı derleme**: Bölüm 2'deki projede sadece `tablo.h` değişti. Hangi dosyalar yeniden derlenmeli? Bunu grafta hangi işlemle bulursun, ve yeniden derleme sırası ne olmalı?

<details>
<summary>Cevaplar</summary>

**1** – Kaynaklar (`main.c`, `liste.c`, `tablo.c`, `ortak.h`) birbirinden bağımsız, istenen sırada gelebilir; `liste.h` ve `tablo.h` de birbirinden bağımsız; `.o`'lar da. Bu bağımsızlıklar yüzünden çok sayıda sıra var: tam olarak **2880** (bütün düğüm altkümeleri üzerinde "bu altküme sıralandıysa sıradaki düğüm hangisi olabilir" DP'siyle sayıldı; genel durumda bir DAG'ın topolojik sıralarını saymak #P-tam bir problem). Topolojik sıra **tek** ancak ve ancak sıradaki her ardışık iki düğüm arasında doğrudan bir kenar varsa: yani DAG bütün düğümlerden geçen bir yol (Hamilton yolu) içeriyorsa. Kahn'da bu, kuyrukta her an **tek** bir düğüm bulunması demek.

**2** – Seviye 0 (giriş derecesi 0): `main.c`, `liste.c`, `tablo.c`, `ortak.h`. Seviye 1: `liste.h`, `tablo.h` (sadece `ortak.h`'yi bekliyorlardı). Seviye 2: `main.o`, `liste.o`, `tablo.o`. Seviye 3: `program`. **4 tur**. Kahn'ı seviye seviye çalıştırmak: o anki kuyruğun tamamını bir tur olarak işle, onların kenarlarını sil, yeni sıfırlar bir sonraki tur. Tur sayısı grafın **en uzun yolunun** (kenar sayısı olarak) uzunluğu + 1: `ortak.h → liste.h → main.o → program`. Hiçbir paralellik bu zincirden kısa süremez.

**3** – Düğümleri topolojik sırayla gez; her $v$ için $\text{erken}(v) = s_v + \max_{u \to v} \text{erken}(u)$ ($s_v$ işin süresi; öncülü yoksa sadece $s_v$). Topolojik sıra, her düğüm işlenirken bütün öncüllerinin hesaplanmış olmasını garanti ediyor: DP'nin doğru doldurma sırası (Ders 9.12'nin üçüncü adımı) tam olarak topolojik sıra. Cevap en büyük $\text{erken}$; geri izleme kritik yolu veriyor. Genel graflarda en uzun **basit** yol NP-zor (Hamilton yolu problemini içeriyor), çünkü döngülerde bir düğümün yeniden ziyaret edilmemesini takip etmek gerekiyor; DAG'da döngü yok, her yol kendiliğinden basit. Proje yönetimindeki CPM/PERT yöntemleri bu hesap.

**4** – Kahn'ın kuyruğu yerine bir **min-heap** (Ders 8.12): her adımda hazır olanların en küçüğünü çek. Her düğüm bir kez eklenip bir kez çekiliyor: $O(m + n \log n)$. Sonuç sözlük sırasına göre en küçük topolojik sıra, çünkü her adımda mümkün olan en küçük düğüm seçiliyor ve bir düğümü erken seçmek sonraki seçenekleri hiç daraltmıyor (açgözlü seçim güvenli). Derleyicilerde, aynı girdiden her seferinde **aynı** çıktıyı üretmek (deterministik derleme) için böyle sabit bir sıra kuralı gerekiyor.

**5** – Değişen düğümden **ulaşılabilen** her düğüm etkileniyor: `tablo.h`'den BFS/DFS (Ders 9.14): `main.o`, `tablo.o`, `program`. `liste.o` ve `liste.h` etkilenmiyor. Yeniden derleme sırası, bu alt kümenin (orijinal topolojik sıraya göre) sırası: `main.o` ve `tablo.o` (paralel), sonra `program`. Make bunu dosya değişiklik zamanlarıyla yapıyor: bir hedef, bağımlılıklarından herhangi biri ondan yeniyse yeniden yapılıyor, ve hedefler topolojik sırayla kontrol edildiği için değişiklik dalga gibi yayılıyor.

</details>

---

## Kaynaklar

- Arthur Kahn, "Topological sorting of large networks", *Communications of the ACM* 5(11), 1962.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 22.4: DFS ile topolojik sıralama; Bölüm 24.2: DAG'da en kısa (ve en uzun) yollar.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 2.2.3: topolojik sıralama algoritması.
- Stuart Feldman, "Make — A Program for Maintaining Computer Programs", *Software: Practice and Experience* 9(4), 1979.
- Evan Martin, "Ninja: a small build system with a focus on speed", 2012; GNU Make kılavuzu, "Parallel Execution".

**Sıradaki ders:** Güçlü bağlı bileşenler. Tarjan ve Kosaraju algoritmaları, çağrı grafında özyineleme tespiti.
