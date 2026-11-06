---
title: "9.18 Minimum yayılan ağaç"
description: "Bağlı, ağırlıklı, yönsüz bir grafın bütün düğümlerini en az toplam ağırlıkla bağlayan ağaç: kesme özelliği ve onunla ispatlanan iki açgözlü algoritma; Kruskal (kenarları sırala, döngü kapatmayanları Ders 8.18'in union-find'ıyla al) ve Prim (ağacı heap'le bir düğümden büyüt); CLRS örneğinde toplam 37; 3000 küçük rastgele grafta bütün yayılan ağaçları deneyen kaba kuvvetle doğrulama; 1 milyon düğüm ve 5 milyon kenarda Kruskal 0.46 s, Prim 1.40 s; kümeleme ve en kısa yol ağacıyla farkı."
---

Bir şehrin bütün mahallelerini elektrik ya da fiber hattıyla birbirine bağlamak istiyorsun; her mahalle çifti arasındaki hattın bir maliyeti var. Her mahalle, dolaylı olarak da olsa, diğer hepsine bağlı olmalı ve toplam maliyet en az olmalı. Gereksiz bir hat (bir döngü kapatan) hiçbir zaman işe yaramaz; dolayısıyla çözüm bir **ağaç**: bütün düğümleri kapsayan, döngüsüz bir alt graf. Toplam ağırlığı en küçük olanına **minimum yayılan ağaç** (MST, minimum spanning tree) denir. Devre tasarımı, ağ topolojisi, kümeleme (Alıştırma 3), görüntü bölütleme ve Ders 9.23'teki gezgin satıcı yaklaşımı bu problemi kullanıyor.

Ders 8.18'de union-find'ın Kruskal algoritmasının çekirdeği olduğunu söylemiştik (Alıştırma 3). Bu derste algoritmanın kendisini ve ikinci klasik yöntemi yazıyoruz; ikisi de açgözlü (Ders 9.10), ve ikisinin doğruluğu da tek bir özelliğe dayanıyor.

---

## 1. Kesme özelliği

Grafın düğümlerini herhangi iki gruba ayır (bir **kesme**, cut). İki grubu birbirine bağlayan kenarlar arasında ağırlığı en küçük olan, **bir** MST'nin içindedir.

**İspat** (değiştirme argümanı, Ders 9.10): $e = \{u, v\}$ bu en hafif kesme kenarı olsun ve $T$ onu içermeyen bir MST. $T$'ye $e$'yi eklemek bir döngü yaratıyor (ağaçta $u$ ile $v$ zaten bağlı). Bu döngü kesmeyi bir yönde geçip geri döndüğü için kesmeyi geçen başka bir kenar $f$ daha içeriyor. $T - f + e$ yine bir yayılan ağaç (döngüdeki bir kenarı çıkarmak bağlılığı bozmuyor) ve ağırlığı $w(T) - w(f) + w(e) \le w(T)$, çünkü $e$ en hafif kesme kenarıydı. Yani $e$'yi içeren bir MST var. $\blacksquare$

Bütün MST algoritmaları bir kenar kümesi $A$ biriktiriyor ve her adımda, $A$'yı bir MST'nin alt kümesi olarak tutan **güvenli** bir kenar ekliyor. Kesme özelliği hangi kenarın güvenli olduğunu söylüyor: $A$'ya saygı duyan (hiçbir $A$ kenarını kesmeyen) herhangi bir kesmenin en hafif kenarı. İki algoritma, kesmeyi farklı seçiyor.

---

## 2. Kod

```c
/* Minimum yayilan agac: Kruskal (kenarlari sirala + union-find, Ders 8.18) ve Prim (heap, Dijkstra'ya benzer) */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int u, v; long w; } Kenar;                    /* yonsuz */

/* ---- Kruskal ---- */
static int *eb; static unsigned char *rk;
static int bul(int x) { while (eb[x] != x) { eb[x] = eb[eb[x]]; x = eb[x]; } return x; }   /* yol yarilama (8.18 Al. 2) */
static int birlestir(int a, int b) {
    a = bul(a); b = bul(b); if (a == b) return 0;
    if (rk[a] < rk[b]) { int t = a; a = b; b = t; }
    eb[b] = a; if (rk[a] == rk[b]) rk[a]++; return 1;
}
static int w_kars(const void *x, const void *y) { long a = ((const Kenar *)x)->w, b = ((const Kenar *)y)->w; return (a > b) - (a < b); }

static long kruskal(int n, Kenar *k, int m, Kenar *secilen, int *sayi) {
    qsort(k, m, sizeof *k, w_kars);                             /* en hafiften agira */
    eb = malloc(n * sizeof *eb); rk = calloc(n, 1); for (int i = 0; i < n; i++) eb[i] = i;
    long top = 0; int s = 0;
    for (int i = 0; i < m && s < n - 1; i++)
        if (birlestir(k[i].u, k[i].v)) { secilen[s++] = k[i]; top += k[i].w; }   /* dongu kapatmiyorsa al */
    free(eb); free(rk); *sayi = s;
    return top;
}

/* ---- Prim: CSR (her yonsuz kenar iki kez), heap'te (agirlik, dugum, ebeveyn) ---- */
typedef struct { long w; int v, e; } HK;
static long prim(int n, const Kenar *k, int m, int *sayi) {
    int *of = calloc(n + 1, sizeof *of), *hd = malloc(2 * m * sizeof *hd); long *ag = malloc(2 * m * sizeof *ag);
    for (int i = 0; i < m; i++) { of[k[i].u + 1]++; of[k[i].v + 1]++; }
    for (int u = 0; u < n; u++) of[u + 1] += of[u];
    int *yz = malloc(n * sizeof *yz); memcpy(yz, of, n * sizeof *yz);
    for (int i = 0; i < m; i++) { int a = yz[k[i].u]++; hd[a] = k[i].v; ag[a] = k[i].w; a = yz[k[i].v]++; hd[a] = k[i].u; ag[a] = k[i].w; }
    char *agacta = calloc(n, 1); HK *h = malloc((2 * m + 1) * sizeof *h); int hn = 0;
    long top = 0; int s = 0;
    for (int kok = 0; kok < n; kok++) {                         /* bagli olmayan graf: her bilesen icin (orman) */
        if (agacta[kok]) continue;
        h[hn++] = (HK){ 0, kok, -1 };
        while (hn) {
            HK x = h[0], son = h[--hn]; int i = 0;
            for (;;) { int c = 2 * i + 1; if (c >= hn) break; if (c + 1 < hn && h[c + 1].w < h[c].w) c++; if (h[c].w >= son.w) break; h[i] = h[c]; i = c; }
            if (hn) h[i] = son;
            if (agacta[x.v]) continue;
            agacta[x.v] = 1; if (x.e >= 0) { top += x.w; s++; }
            for (int j = of[x.v]; j < of[x.v + 1]; j++)          /* agacin disina giden kenarlar aday */
                if (!agacta[hd[j]]) { int c = hn++; while (c > 0 && h[(c - 1) / 2].w > ag[j]) { h[c] = h[(c - 1) / 2]; c = (c - 1) / 2; } h[c] = (HK){ ag[j], hd[j], x.v }; }
        }
    }
    free(of); free(hd); free(ag); free(yz); free(agacta); free(h); *sayi = s;
    return top;
}

#ifndef KUTUPHANE
int main(void) {
    const char *ad = "abcdefghi";                                /* CLRS Sekil 23.1 */
    Kenar k[] = { {0,1,4}, {0,7,8}, {1,2,8}, {1,7,11}, {2,3,7}, {2,8,2}, {2,5,4}, {3,4,9}, {3,5,14}, {4,5,10}, {5,6,2}, {6,7,1}, {6,8,6}, {7,8,7} };
    int m = 14, n = 9, s1, s2; Kenar sec[8], kopya[14];
    memcpy(kopya, k, sizeof k);
    long t1 = kruskal(n, kopya, m, sec, &s1), t2 = prim(n, k, m, &s2);
    printf("Kruskal: %d kenar, toplam %ld:", s1, t1); for (int i = 0; i < s1; i++) printf(" %c-%c(%ld)", ad[sec[i].u], ad[sec[i].v], sec[i].w); printf("\n");
    printf("Prim   : %d kenar, toplam %ld\n", s2, t2);
}
#endif
```

### Kruskal

Joseph Kruskal (1956): kenarları ağırlığa göre **sırala**; sırayla bak; bir kenar şu ana kadar seçilenlerle bir **döngü** kapatmıyorsa (iki ucu farklı bileşenlerdeyse) al. Bu, kesme özelliğinin doğrudan uygulaması: kenar $\{u, v\}$ alınırken, $u$'nun bileşeni ile geri kalan her şey arasındaki kesmede, daha hafif bütün kenarlar zaten incelenmiş ve ya alınmış ya döngü kapattığı için reddedilmiş (yani kesmeyi geçmiyorlar). $\{u, v\}$ bu kesmenin en hafif kenarı: güvenli.

"İki uç aynı bileşende mi?" sorusu ve bileşenleri birleştirmek: tam Ders 8.18'in union-find'ı, rank ve yol yarılamayla (8.18'in Alıştırma 2'si). Maliyet sıralamanın: $O(m \log m)$; union-find işlemleri $O(m\, \alpha(n))$.

### Prim

Robert Prim (1957; Jarník 1930'da bulmuştu): bir düğümden başla; ağacın **içi** ile **dışı** arasındaki kesmenin en hafif kenarını ekle; ağaç tek tek düğüm ekleyerek büyüyor. Kesme özelliği her adımı doğrudan haklı çıkarıyor. "Ağaçtan dışarı giden en hafif kenar" bir öncelik kuyruğu; Ders 9.17'deki Dijkstra ile neredeyse aynı kod. Tek fark heap anahtarı: Dijkstra'da başlangıçtan **toplam** uzaklık ($d[u] + w$), Prim'de sadece **kenarın** ağırlığı ($w$). Tembel silmeyle $O(m \log m)$.

Graf bağlı değilse (aşağıdaki büyük örnekte birkaç düğüm hiç kenarsız), her bileşen için ayrı bir ağaç: yayılan **orman**. Kruskal bunu kendiliğinden yapıyor; Prim'de her ziyaret edilmemiş düğümden yeniden başlanıyor.

---

## 3. Doğrulama ve ölçüm

CLRS'nin Şekil 23.1'indeki 9 düğümlük graf:

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined mst.c -o mst && ./mst
Kruskal: 8 kenar, toplam 37: g-h(1) f-g(2) c-i(2) c-f(4) a-b(4) c-d(7) b-c(8) d-e(9)
Prim   : 8 kenar, toplam 37
```

Kruskal kenarları ağırlık sırasıyla alıyor; `a-h(8)`, `h-i(7)` gibi kenarlar reddedildi çünkü o anda iki uçları zaten bağlıydı. (`b-c(8)` yerine `a-h(8)` de seçilebilirdi: eşit ağırlıklarda MST tek değil, ama toplam ağırlık hep aynı.)

Sonra: 3000 küçük rastgele bağlı graf (en fazla 7 düğüm, 14 kenar), her birinde, $n - 1$ kenarlı bütün kenar altkümeleri denenip döngüsüz olanların en hafifi bulunuyor (kaba kuvvet); ve 1 milyon düğüm, 5 milyon rastgele kenar:

```
$ cc -std=c11 -O2 -Wall olcum.c -o olcum && ./olcum
3000 kucuk rastgele graf: Kruskal ve Prim, kaba kuvvetten 0 kez farkli
n=1000000 m=5000000: Kruskal 0.457 s (999951 kenar, toplam 120224209031), Prim 1.402 s (999951 kenar, toplam 120224209031)
```

(Sanitizer'lı derleme temiz.)

- İki algoritma her küçük grafta kaba kuvvetle, büyük grafta birbirleriyle aynı toplamı veriyor. 999 951 kenar, yani orman $10^6 - 999\,951 = 49$ ağaçtan oluşuyor: dev bir bileşen ve neredeyse hepsi hiç kenarı olmayan tek düğümler (ortalama derecesi 10 olan rastgele bir grafta bir düğümün kenarsız kalma olasılığı yaklaşık $e^{-10}$; beklenen sayı 45).
- **Kruskal 3 kat hızlı**: süresinin çoğu `qsort` (5 milyon kenar, Ders 9.4'teki gibi fonksiyon pointer'lı); union-find işlemleri neredeyse bedava (Ders 8.18'in işlem başına 0.9 adımı). Ağırlıklar tamsayı olduğu için Ders 9.7'deki radix sıralama bunu daha da hızlandırırdı. Prim ise 10 milyon girdilik bir heap'te rastgele erişim yapıyor.
- Yoğun graflarda ($m \approx n^2$) tablo tersine dönüyor: heap'siz, komşuluk matrisli $O(n^2)$ Prim en iyisi (Alıştırma 4).

---

## Alıştırmalar

**1** – Bütün kenar ağırlıkları **farklıysa** MST'nin tek olduğunu kesme özelliğiyle göster. Eşit ağırlıklar varken iki farklı MST'nin toplam ağırlığı neden aynı?

**2** – **Maksimum** yayılan ağaç nasıl bulunur? **Darboğaz** yayılan ağaç (en ağır kenarı en hafif olan yayılan ağaç) ile MST arasındaki ilişki ne? Her MST bir darboğaz ağacı mı?

**3** – **Tek bağlantılı kümeleme**: $n$ noktayı $k$ kümeye ayırmak istiyorsun, kümeler arası en küçük uzaklık en büyük olsun. Kruskal'ı $n - k$ kenar aldıktan sonra durdurmak neden bu soruyu cevaplar?

**4** – Yoğun bir grafta ($m = \Theta(n^2)$), komşuluk matrisiyle ve heap kullanmadan Prim'i $O(n^2)$'de nasıl yazarsın? Heap'li sürümün $O(m \log m)$'si ile karşılaştır.

**5** – Dijkstra'nın en kısa yol ağacı (Ders 9.17) ile MST aynı mı? Üç düğümlük bir karşı örnek ver.

<details>
<summary>Cevaplar</summary>

**1** – İki farklı MST $T_1 \ne T_2$ olsun ve $e$, ikisinden yalnızca birinde (diyelim $T_1$'de) bulunan kenarlar arasında en hafifi. $T_1$'den $e$'yi çıkarınca düğümler iki gruba ayrılıyor; bu bir kesme. $T_2$ bu kesmeyi geçen bir $f$ kenarı içeriyor, $f \ne e$ ($e \notin T_2$). $f \in T_2 \setminus T_1$ ise (öyle olmalı, yoksa $T_1$ kesmeyi iki kenarla geçerdi) seçime göre $w(e) < w(f)$ (farklı ağırlıklar ve $e$ farklı kenarların en hafifi). $T_2 - f + e$ daha hafif bir yayılan ağaç: $T_2$ MST değil, çelişki. Eşit ağırlıklarda farklı MST'ler var ama her MST'nin ağırlıklarının çoklu kümesi (sıralı kenar ağırlıkları listesi) aynı; bu da toplamı aynı yapıyor. Sezgisel olarak: Kruskal eşit ağırlıklı kenarları hangi sırayla incelerse incelesin, her ağırlık seviyesinde aynı **sayıda** kenar alıyor.

**2** – Maksimum yayılan ağaç: ağırlıkları $-w$ yap (ya da Kruskal'ı büyükten küçüğe sırala); kesme özelliği aynen geçerli. Her MST bir darboğaz yayılan ağacı: MST'nin en ağır kenarı $e$ olsun; $e$'yi çıkarınca oluşan kesmede $e$ en hafif kenar (kesme özelliği), yani başka hiçbir yayılan ağaç bu kesmeyi $e$'den hafif bir kenarla geçemez; dolayısıyla her yayılan ağacın en ağır kenarı en az $w(e)$. Tersi doğru değil: bir darboğaz ağacı MST olmayabilir (sadece en ağır kenarı umursuyor). Darboğaz problemi daha kolay: $O(m)$'de çözülebiliyor (Camerini).

**3** – Kruskal en hafif kenarları alıyor ve her kenar iki kümeyi birleştiriyor; $n - k$ kenardan sonra tam $k$ küme kalıyor. Bir sonraki kenar (Kruskal'ın alacağı) kümeler arası **en küçük** uzaklık. Başka herhangi bir $k$-kümelemede, Kruskal'ın aynı kümeye koyduğu iki noktanın farklı kümelerde olduğu bir çift var; o çifti bağlayan Kruskal yolu (hepsi bu eşikten hafif kenarlardan oluşuyor) iki küme arasında bir kenardan geçiyor, ve o kenar Kruskal'ın durduğu eşikten hafif. Yani o kümelemenin kümeler arası en küçük uzaklığı daha küçük: Kruskal'ınki optimal. (Kleinberg ve Tardos, Bölüm 4.7.) Bu, hiyerarşik kümelemenin "single-linkage" yöntemi.

**4** – Her ağaç dışı düğüm için `en_iyi[v]`: ağaçtan $v$'ye en hafif kenarın ağırlığı (başta $\infty$). Her adımda `en_iyi`'si en küçük ağaç dışı düğümü **doğrusal tarama** ile bul ($O(n)$), ağaca ekle, sonra onun matris satırını tarayıp diğer düğümlerin `en_iyi`'lerini güncelle ($O(n)$). $n$ adım: $O(n^2)$. Yoğun graflarda $m \log m = \Theta(n^2 \log n)$, yani heap'siz sürüm $\log n$ kat hızlı, ve iç döngüler ardışık dizi taramaları (cache dostu, SIMD'ye uygun). Ders 8.19'daki "yoğun graf için matris" kuralının algoritma tarafı.

**5** – Hayır. Üçgen: $a$–$b$ 2, $b$–$c$ 2, $a$–$c$ 3. MST: $a$–$b$ + $b$–$c$, toplam 4. $a$'dan Dijkstra: $c$'ye en kısa yol doğrudan 3 (üzerinden 4), dolayısıyla en kısa yol ağacı $a$–$b$ + $a$–$c$, toplam 5. En kısa yol ağacı **kökten** uzaklıkları küçültüyor, MST **toplam** ağırlığı; farklı amaçlar. Prim ile Dijkstra'nın kodu neredeyse aynı (Bölüm 2), ama tek bir terim (heap anahtarına $d[u]$'yu eklemek ya da eklememek) iki farklı problemi çözüyor.

</details>

---

## Kaynaklar

- Joseph Kruskal, "On the Shortest Spanning Subtree of a Graph and the Traveling Salesman Problem", *Proceedings of the AMS* 7(1), 1956.
- Robert Prim, "Shortest Connection Networks and Some Generalizations", *Bell System Technical Journal* 36(6), 1957.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 23: minimum yayılan ağaçlar, Teorem 23.1 (kesme özelliği).
- Jon Kleinberg ve Éva Tardos, *Algorithm Design*, Bölüm 4.5–4.7: MST ve kümeleme.
- Ronald Graham ve Pavol Hell, "On the History of the Minimum Spanning Tree Problem", *Annals of the History of Computing* 7(1), 1985: Borůvka (1926) ve Jarník (1930).

**Sıradaki ders:** Dominator ağacı. Cooper–Harvey–Kennedy algoritması ve Lengauer–Tarjan; SSA'ya hazırlık.
