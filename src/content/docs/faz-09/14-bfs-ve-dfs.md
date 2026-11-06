---
title: "9.14 BFS ve DFS"
description: "Bir grafı gezmenin iki temel yolu, Ders 8.19'un CSR gösterimi üzerinde: kuyrukla genişlik öncelikli arama ve kenar sayısı olarak en kısa uzaklıklar; açık yığınla derinlik öncelikli arama, beyaz-gri-siyah renkler, keşif ve bitiş zamanları, parantez yapısı; yönlü bir grafta her kenarın ağaç, geri, ileri ya da çapraz kenar olarak sınıflandırılması ve geri kenarın döngü demek olması; 1 milyon düğümlü bir yolda ders kitabı özyinelemeli DFS'in çökmesi, 1 milyon düğüm ve 10 milyon kenarda BFS 0.06 s ve DFS 0.29 s."
---

Ders 8.5'te labirentte en kısa yolu BFS ile bulduk, Ders 8.6'da aynı iskeletin yığınla derinlik öncelikli bir gezinmeye döndüğünü gördük, Ders 8.19'da grafları CSR olarak sakladık. Bu ders bu parçaları genel, yönlü graflar için birleştiriyor ve DFS'in gezinmenin ötesinde verdiği **yapısal bilgiyi** çıkarıyor: keşif ve bitiş zamanları ve kenar sınıfları. Sonraki üç dersin (topolojik sıralama, güçlü bağlı bileşenler, dominator ağacı) hepsi bu bilgiye dayanıyor. Bir derleyicide en sık sorulan graf sorusu da burada: **bu grafta döngü var mı?** (Bir dosya kendini dolaylı olarak `#include` ediyor mu, bir fonksiyon kendini dolaylı olarak çağırıyor mu, bir döngü gövdesine geri dönen bir atlama var mı.)

---

## 1. Ortak dosya

Faz 9'un graf dersleri boyunca kullanacağımız CSR (Ders 8.19'dakinin aynısı, tek başlık dosyasında):

```c
/* graf.h: Ders 8.19'daki CSR, yonlu graf. Faz 9 graf derslerinin ortak dosyasi. */
#ifndef GRAF_H
#define GRAF_H
#include <stdlib.h>
#include <string.h>

typedef struct { int u, v; } Kenar;
typedef struct { int n, m; int *ofset, *hedef; } Graf;      /* u'nun komsulari hedef[ofset[u] .. ofset[u+1]) */

static Graf graf_kur(int n, const Kenar *k, int m) {
    Graf g = { n, m, calloc(n + 1, sizeof(int)), malloc((m ? m : 1) * sizeof(int)) };
    for (int i = 0; i < m; i++) g.ofset[k[i].u + 1]++;
    for (int u = 0; u < n; u++) g.ofset[u + 1] += g.ofset[u];
    int *yaz = malloc((n ? n : 1) * sizeof(int)); memcpy(yaz, g.ofset, n * sizeof(int));
    for (int i = 0; i < m; i++) g.hedef[yaz[k[i].u]++] = k[i].v;
    free(yaz);
    return g;
}
static void graf_birak(Graf *g) { free(g->ofset); free(g->hedef); }
#endif
```

---

## 2. Kod

```c
/* BFS (uzakliklar) ve DFS (kesif/bitis zamanlari, kenar siniflandirmasi). DFS acik yiginla: derin graflarda tasmaz. */
#include <stdio.h>
#include "graf.h"

/* BFS: Ders 8.5'in kuyrugu. uzak[v] = s'den v'ye en az kenar sayisi (-1: ulasilamaz) */
static void bfs(const Graf *g, int s, int *uzak, int *ebeveyn) {
    int *q = malloc(g->n * sizeof *q), bas = 0, son = 0;
    for (int v = 0; v < g->n; v++) { uzak[v] = -1; ebeveyn[v] = -1; }
    uzak[s] = 0; q[son++] = s;
    while (bas < son) {
        int u = q[bas++];
        for (int i = g->ofset[u]; i < g->ofset[u + 1]; i++) {
            int v = g->hedef[i];
            if (uzak[v] < 0) { uzak[v] = uzak[u] + 1; ebeveyn[v] = u; q[son++] = v; }
        }
    }
    free(q);
}

/* DFS renkleri: BEYAZ = gorulmedi, GRI = yiginda (alt agaci bitmedi), SIYAH = bitti */
enum { BEYAZ, GRI, SIYAH };
typedef struct { int *renk, *kesif, *bitis, *ebeveyn; int zaman; long agac, geri, ileri, capraz; int yaz; } DFS;

static void dfs_ziyaret(const Graf *g, int s, DFS *d) {
    int *yigin = malloc(g->n * sizeof *yigin), *sira = malloc(g->n * sizeof *sira), tepe = 0;
    /* sira[u]: u'nun komsu listesinde bir sonraki bakilacak kenar (Ders 8.6: cerceve = dugum + kaldigi yer) */
    yigin[tepe++] = s; d->renk[s] = GRI; d->kesif[s] = ++d->zaman; sira[s] = g->ofset[s];
    while (tepe > 0) {
        int u = yigin[tepe - 1];
        if (sira[u] < g->ofset[u + 1]) {
            int v = g->hedef[sira[u]++];
            const char *tur;
            if (d->renk[v] == BEYAZ) {                         /* agac kenari: v'yi kesfet */
                tur = "agac"; d->agac++;
                d->ebeveyn[v] = u; d->renk[v] = GRI; d->kesif[v] = ++d->zaman; sira[v] = g->ofset[v];
                yigin[tepe++] = v;
            } else if (d->renk[v] == GRI) { tur = "geri"; d->geri++; }        /* yigindaki bir ataya: DONGU */
            else if (d->kesif[u] < d->kesif[v]) { tur = "ileri"; d->ileri++; } /* bitmis bir torune */
            else { tur = "capraz"; d->capraz++; }                              /* bitmis, ata/torun olmayan */
            if (d->yaz) printf("    %d -> %d  %s\n", u, v, tur);
        } else {                                               /* butun komsular bitti: u'yu kapat */
            d->renk[u] = SIYAH; d->bitis[u] = ++d->zaman; tepe--;
        }
    }
    free(yigin); free(sira);
}

static void dfs(const Graf *g, DFS *d) {
    int n = g->n;
    d->renk = calloc(n, sizeof(int)); d->kesif = calloc(n, sizeof(int)); d->bitis = calloc(n, sizeof(int));
    d->ebeveyn = malloc(n * sizeof(int)); for (int v = 0; v < n; v++) d->ebeveyn[v] = -1;
    d->zaman = 0; d->agac = d->geri = d->ileri = d->capraz = 0;
    for (int s = 0; s < n; s++) if (d->renk[s] == BEYAZ) dfs_ziyaret(g, s, d);   /* her bilesen */
}
static void dfs_birak(DFS *d) { free(d->renk); free(d->kesif); free(d->bitis); free(d->ebeveyn); }

#ifndef KUTUPHANE
int main(void) {
    /*  0 -> 1, 0 -> 3, 1 -> 4, 2 -> 4, 2 -> 5, 3 -> 1, 4 -> 3, 5 -> 5, 0 -> 4   (CLRS 22.4 + bir ileri kenar) */
    Kenar k[] = { {0,1}, {0,3}, {0,4}, {1,4}, {2,4}, {2,5}, {3,1}, {4,3}, {5,5} };
    Graf g = graf_kur(6, k, 9);
    int uzak[6], eb[6];
    bfs(&g, 0, uzak, eb);
    printf("BFS 0'dan uzakliklar:"); for (int v = 0; v < 6; v++) printf(" %d:%d", v, uzak[v]); printf("\n");
    DFS d = { .yaz = 1 };
    printf("DFS kenarlari:\n"); dfs(&g, &d);
    printf("kesif/bitis:"); for (int v = 0; v < 6; v++) printf(" %d:%d/%d", v, d.kesif[v], d.bitis[v]); printf("\n");
    printf("agac %ld, geri %ld, ileri %ld, capraz %ld  -> %s\n", d.agac, d.geri, d.ileri, d.capraz, d.geri ? "DONGU VAR" : "dongu yok");
    dfs_birak(&d); graf_birak(&g);
}
#endif
```

### BFS

Ders 8.5'teki labirent aramasının genel graf hali. Kuyruk, düğümleri başlangıçtan **uzaklıklarına göre** sırayla veriyor: önce uzaklığı 0 olan, sonra bütün 1'ler, sonra bütün 2'ler. Bir düğüm ilk görüldüğünde ona verilen uzaklık, kenar sayısı olarak **en kısa** uzaklık. İspat (Ders 8.5'te "Faz 9'da" diye söz vermiştik): değişmez "kuyruktaki uzaklıklar sıralı ve en fazla iki farklı değer içeriyor ($d$ ve $d + 1$)"; bir düğüm $d + 1$ ile işaretlenmeden önce uzaklığı $\le d$ olan bütün düğümler işlenmiş, ve onların hiçbiri bu düğüme kenar vermiyordu (verseydi düğüm daha önce işaretlenirdi). `ebeveyn` dizisi, her düğüme ulaşan en kısa yolları bir ağaç olarak tutuyor: **BFS ağacı**.

Maliyet $O(n + m)$: her düğüm kuyruğa en fazla bir kez giriyor, her kenara bir kez bakılıyor.

### DFS

DFS bir düğümden gidebildiği kadar derine iniyor, çıkmaz sokakta bir geri dönüp başka bir dal deniyor. Ders 8.6'daki gibi açık yığınla yazıldı: yığında düğüm ve o düğümün komşu listesinde **kaldığı yer** (`sira[u]`), yani bir özyinelemeli çağrı çerçevesinin tam içeriği (parametre ve dönüş noktası). Her düğüme üç renkten biri:

- **Beyaz**: henüz görülmedi.
- **Gri**: keşfedildi ama alt ağacı bitmedi; şu an yığında.
- **Siyah**: kendisi ve ondan ulaşılan her şey bitti.

Bir düğüm griye döndüğünde `kesif` zamanını, siyaha döndüğünde `bitis` zamanını alıyor (tek bir sayaçtan). `dfs`, bütün düğümleri sırayla deniyor ve beyaz kalan her birinden yeni bir gezinme başlatıyor: her başlangıç bir **DFS ağacı**, hepsi birlikte **DFS ormanı**.

**Parantez yapısı**: keşfi bir açılan, bitişi bir kapanan parantez olarak yaz; her düğümün aralığı $[\text{keşif}, \text{bitiş}]$. İki düğümün aralıkları ya iç içe (biri ötekinin DFS ağacındaki atası) ya da tamamen ayrık; asla kesişmiyor. Çünkü bir düğüm, yığından ancak kendisinden sonra itilen her şey çıktıktan sonra çıkıyor (Ders 8.4'teki parantez denetleyicisinin ta kendisi).

### Kenar sınıflandırması

DFS, $u \to v$ kenarına baktığı anda $v$'nin rengine göre kenarı dört sınıftan birine koyuyor:

| $v$'nin rengi | Sınıf | Anlamı |
| --- | --- | --- |
| Beyaz | **Ağaç** | $v$ ilk kez bu kenarla keşfedildi |
| Gri | **Geri** | $v$, $u$'nun bir atası (yığında): $v \to \dots \to u \to v$ bir **döngü** |
| Siyah, $\text{keşif}(u) < \text{keşif}(v)$ | **İleri** | $v$, $u$'nun zaten bitmiş bir torunu |
| Siyah, $\text{keşif}(u) > \text{keşif}(v)$ | **Çapraz** | $v$ ne ata ne torun; başka bir dalda ya da başka bir ağaçta |

**Teorem**: yönlü bir grafta döngü var ancak ve ancak DFS bir geri kenar buluyor. Geri kenar varsa döngü apaçık (ağaç yolu $v \to \dots \to u$ artı $u \to v$). Tersine, bir döngü varsa, döngüde ilk keşfedilen düğüm $v$ olsun; döngüdeki diğer her düğüm $v$ gri iken (beyaz yol teoremi: keşif anında $v$'den beyaz düğümlerle ulaşılabilen her şey $v$'nin torunu olur) keşfedilip biter, ve döngüde $v$'ye dönen kenar o anda gri bir $v$'yi görüyor: geri kenar.

Örnek graf (CLRS'nin Şekil 22.4'ü, bir ileri kenar, `0 → 4`, eklenmiş; altı düğüm, dokuz kenar): `0→1`, `0→3`, `0→4`, `1→4`, `2→4`, `2→5`, `3→1`, `4→3` ve öz döngü `5→5`.


```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined gezinme.c -o gezinme && ./gezinme
BFS 0'dan uzakliklar: 0:0 1:1 2:-1 3:1 4:1 5:-1
DFS kenarlari:
    0 -> 1  agac
    1 -> 4  agac
    4 -> 3  agac
    3 -> 1  geri
    0 -> 3  ileri
    0 -> 4  ileri
    2 -> 4  capraz
    2 -> 5  agac
    5 -> 5  geri
kesif/bitis: 0:1/8 1:2/7 2:9/12 3:4/5 4:3/6 5:10/11
agac 4, geri 2, ileri 2, capraz 1  -> DONGU VAR
```

- BFS: 2 ve 5'e 0'dan ulaşılamıyor (`-1`); 1, 3, 4 doğrudan komşu.
- DFS 0'dan başlayıp 0 → 1 → 4 → 3 yolunu iniyor. 3 → 1, gri bir düğüme: **geri** kenar, `1 → 4 → 3 → 1` döngüsü. 0 → 3 ve 0 → 4, 0'ın bitmiş torunlarına: **ileri**. İkinci ağaç 2'den başlıyor; 2 → 4, başka bir ağaçta bitmiş bir düğüme: **çapraz**. 5 → 5 öz döngü: **geri** (bir düğüm kendisinin atası).
- Zamanlar parantez yapısında: 0'ın aralığı $[1, 8]$, 1'inki $[2, 7]$ içinde, 4'ünki $[3, 6]$, 3'ünki $[4, 5]$; 2'nin $[9, 12]$'si hepsinden ayrık.

Yönsüz bir grafta sadece ağaç ve geri kenarlar var (Alıştırma 2).

---

## 3. Büyük graflar

```
$ cc -std=c11 -O2 -Wall buyuk.c -o buyuk && ./buyuk
acik yiginli DFS, 1000000 dugumluk yol: 0.015 s, en derin kesif 1000000
rastgele graf n=1000000 m=10000000: BFS 0.060 s (999955 ulasilabilir, en uzak 9 adim); DFS 0.287 s
  DFS kenarlari: agac 999954, geri 4762147, ileri 3996975, capraz 240924 (toplam 10000000)
$ ./buyuk o; echo "ozyinelemeli cikis $?"
ozyinelemeli cikis 139
```

(`buyuk.c`, `gezinme.c`'yi `KUTUPHANE` tanımlı olarak içerip `main`'ini dışarıda bırakıyor; aynı dosyada bir de ders kitabındaki gibi düz özyinelemeli bir `dfs_oz` var.)

- **Uzun bir yol** (0 → 1 → ... → 999 999): açık yığınlı DFS 15 ms'de bitiriyor; düz özyinelemeli DFS, `-O2`'de de `-O0`'da da, 1 milyon çerçeveyle 8 MB'lık yığını taşırıp çöküyor (Ders 8.6). Gerçek graflarda (bağımlılık zincirleri, uzun bağlı listeler, derin çağrı zincirleri) DFS derinliği düğüm sayısına yaklaşabiliyor; özyinelemeli DFS ancak derinliğin küçük olduğu biliniyorsa güvenli.
- **Rastgele graf** (ortalama derece 10): neredeyse bütün düğümler 0'dan ulaşılabilir ve en uzak düğüm sadece 9 adımda ("küçük dünya": her adımda erişilen düğüm sayısı kabaca 10 katına çıkıyor, $\log_{10} 10^6 = 6$ civarı adımdan sonra graf tükeniyor). BFS 60 ms, DFS 287 ms; DFS her kenar için rengi ve keşif zamanını okuyor ve sınıflandırıyor, ve yığın gezinmesi BFS'in ardışık kuyruğundan daha dağınık.
- Kenar sınıflarının toplamı tam olarak $m$: her kenara bir kez bakıldı. Ağaç kenarı sayısı $n$ eksi DFS ağacı sayısı.

---

## Alıştırmalar

**1** – Parantez teoremi: herhangi iki düğüm $u$, $v$ için $[\text{keşif}(u), \text{bitiş}(u)]$ ve $[\text{keşif}(v), \text{bitiş}(v)]$ aralıklarının ya iç içe ya ayrık olduğunu, ve iç içeyse içtekinin DFS ağacında dıştakinin torunu olduğunu göster. Bölüm 2'deki çıktıda kontrol et.

**2** – **Yönsüz** bir grafta (her kenar iki yönde saklanıyor) DFS neden hiç ileri ya da çapraz kenar üretmez? Yönsüz grafta döngü tespiti için "gri komşu" kuralı neden tek başına yanlış sonuç verir, ve nasıl düzeltilir?

**3** – Döngü tespitinde sadece "var" demek yerine döngünün **kendisini** yazdır. Geri kenar $u \to v$ bulunduğunda hangi bilgiyle döngüyü kurarsın?

**4** – BFS ile $s$'den $t$'ye en kısa yolu (düğüm listesi olarak) yazdır. Bütün kenarlar 0 ya da 1 ağırlıklıysa en kısa **ağırlıklı** yolu $O(n + m)$'de nasıl bulursun (ipucu: Ders 8.5'teki deque)?

**5** – Yönsüz bir graf **iki parçalı** mı (düğümler, her kenar iki grup arasında olacak şekilde iki gruba ayrılabilir mi)? BFS ile nasıl test edersin? Bir derleyicide iki parçalı graflar nerede ortaya çıkar?

<details>
<summary>Cevaplar</summary>

**1** – $\text{keşif}(u) < \text{keşif}(v)$ diyelim. $v$, $u$ gri iken keşfedildiyse, $v$ yığında $u$'nun üstünde; yığın LIFO olduğu için $v$, $u$'dan önce çıkar: $\text{bitiş}(v) < \text{bitiş}(u)$, aralıklar iç içe, ve $v$'ye giden ağaç kenarları zinciri $u$'dan başlıyor ($v$, $u$'nun torunu). $v$, $u$ siyahken keşfedildiyse $\text{bitiş}(u) < \text{keşif}(v)$: ayrık. Kesişme ($\text{keşif}(u) < \text{keşif}(v) < \text{bitiş}(u) < \text{bitiş}(v)$) yığın disiplini yüzünden imkânsız. Çıktıda: 0 $[1,8]$ ⊃ 1 $[2,7]$ ⊃ 4 $[3,6]$ ⊃ 3 $[4,5]$; 2 $[9,12]$ ⊃ 5 $[10,11]$; iki grup ayrık.

**2** – $\{u, v\}$ kenarı iki yönde de var. $v$ siyahsa ve $u$'dan sonra keşfedildiyse ($v$, $u$'nun torunu) ileri kenar olurdu; ama $v$ keşfedilip biterken $v \to u$ kenarına da bakılmıştı ve $u$ o anda griydi: bu kenar zaten bir geri kenar olarak, $v$ tarafından, görüldü. Çapraz kenar için $v$'nin $u$'dan önce bitmiş olması gerekiyor; ama $v$ bitmeden $v \to u$'ya bakılırdı ve $u$ o zaman beyaz olurdu, $u$ $v$'nin torunu olurdu: çelişki. Sorun: her ağaç kenarı $u \to v$'nin ters yönü $v \to u$, $u$ griyken görüldüğü için "geri kenar" sayılır ve her yönsüz graf döngülü görünür. Düzeltme: $v$'nin komşusu kendi DFS **ebeveyni** ise (ve o kenar aynı kenarsa) atla. (Çoklu kenarlar varsa, ebeveyne ikinci bir kenar gerçekten bir döngüdür; kenar kimliğiyle karşılaştırmak gerekir.)

**3** – `ebeveyn` dizisi DFS ağacını tutuyor. Geri kenar $u \to v$ bulununca, $u$'dan başlayıp `ebeveyn` zincirini $v$'ye ulaşana kadar izle: $u, \text{ebeveyn}(u), \dots, v$; ters çevirince $v \to \dots \to u$, ve sonuna $u \to v$ eklenince döngü. $v$, $u$'nun atası olduğu (gri) için bu zincir mutlaka $v$'ye ulaşıyor. Derleyicilerin "döngüsel `#include`" ya da Make'in "Circular dependency dropped" hata mesajları bu zinciri yazdırıyor (Ders 9.15).

**4** – BFS'ten sonra `ebeveyn` zincirini $t$'den $s$'ye izle ve ters çevir; $t$'ye ulaşılamıyorsa (`uzak[t] < 0`) yol yok. 0-1 ağırlıklarda: kuyruk yerine **deque** (Ders 8.5). Ağırlığı 0 olan bir kenarla bulunan düğüm deque'nin **başına**, ağırlığı 1 olanla bulunan **sonuna** ekleniyor; bir düğüm daha kısa bir uzaklıkla yeniden bulunursa güncelleniyor. Deque her an en fazla iki farklı uzaklık tutuyor ve baştaki her zaman en küçüğü: Dijkstra'nın (Ders 9.17) öncelik kuyruğunu, iki değerli ağırlıklarda $O(1)$'lik bir deque'ye indirgemek.

**5** – BFS sırasında düğümleri iki renge boya: başlangıç 0, her yeni keşfedilen düğüm ebeveyninin tersi. Bir kenarın iki ucu da aynı renkteyse graf iki parçalı değil (tek uzunluklu bir döngü var); hiçbir kenar böyle değilse iki parçalı, ve renkler iki grubu veriyor. Her bileşen için ayrı başlat. Derleyicide: iki kayıtlı (register) bir makinede yazmaç ayırma ("2 renkle boyanabilir mi?"; Ders 9.20'de genel $k$ renk NP-zor, ama 2 renk BFS ile doğrusal); ve eşleme problemlerinde (komutları işlem birimlerine atamak) iki parçalı graflar.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 22.2 (BFS) ve 22.3 (DFS, parantez teoremi, beyaz yol teoremi, kenar sınıflandırması).
- Robert Tarjan, "Depth-First Search and Linear Graph Algorithms", *SIAM Journal on Computing* 1(2), 1972.
- Robert Sedgewick, *Algorithms in C, Part 5: Graph Algorithms* (3. baskı), Bölüm 18.
- Steven Skiena, *The Algorithm Design Manual* (2. baskı), Bölüm 5: graf gezinmesi.

**Sıradaki ders:** Topolojik sıralama. Kahn algoritması ve DFS ile; derleme bağımlılığı (make) örneği.
