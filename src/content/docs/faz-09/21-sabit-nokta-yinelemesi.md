---
title: "9.21 Sabit nokta yinelemesi"
description: "Veri akışı analizinin matematiksel çekirdeği: Ders 6.8'in kafesleri, monoton fonksiyonlar ve en küçük sabit noktaya ⊥'dan başlayıp yinelemeyle ulaşmak (Kleene), sonlu yükseklikli kafeste sonlanma; canlılık analizi bit kümeleri üzerinde geriye doğru denklemler olarak, tur tur ve worklist ile; Ders 9.19'un döngülü fonksiyonunda sonuçlar; düz kafeste iyimser sabit yayılımı ve döngü içinden gelen y = 2'nin ve z = 7'nin bulunması; 200 000 bloklu CFG'de gezinme sırasının etkisi: 6 tura karşı 29 tur, worklist ile 0.59 milyon blok hesabı, üçünde aynı sabit nokta."
---

Bu fazın son üç graf dersinde bir kalıp tekrar etti: Ders 9.16'nın Alıştırma 5'i (özyinelemeli fonksiyonlar için analiz), Ders 9.19'daki Cooper–Harvey–Kennedy (dominatörler) ve saf dominatör denklemleri. Hepsinde bir şeyi doğrudan hesaplayamadık: her düğümün cevabı komşularınınkine bağlıydı ve bağımlılıklar **döngüseldi**. Yaptığımız şey hep aynıydı: herkese bir başlangıç değeri ver, her düğümün cevabını komşularının **şu anki** cevaplarından yeniden hesapla, hiçbir şey değişmeyene kadar tekrarla. Bu dersin konusu bu işlemin kendisi: **sabit nokta yinelemesi** (fixed-point iteration). Neden bittiğini, neden doğru cevaba ulaştığını ve nasıl hızlı yapılacağını göreceğiz.

Derleyicilerde bu yöntemin adı **veri akışı analizi** (data-flow analysis): Faz 16'daki neredeyse her optimizasyon (ölü kod silme, sabit yayılımı, ortak alt ifade, yazmaç ayırma için canlılık) bir veri akışı problemi olarak ifade ediliyor ve aynı motorla çözülüyor.

---

## 1. Kuram

Ders 6.8'de **kafes** (lattice) tanımladık: her iki elemanın en küçük üst sınırı ($\sqcup$, birleşim) ve en büyük alt sınırı ($\sqcap$, buluşma) olan kısmi sıralı bir küme. En küçük eleman $\bot$, en büyük $\top$. Örnek: bir değişken kümesinin bütün altkümeleri, $\subseteq$ sırasıyla; birleşim $\cup$, $\bot = \emptyset$.

Bir $f$ fonksiyonu **monoton**: $x \sqsubseteq y \Rightarrow f(x) \sqsubseteq f(y)$. "Daha çok bilgi girerse daha çok bilgi çıkar."

**Teorem** (Kleene; sonlu yükseklikli kafesler için): $f$ monoton ise $\bot, f(\bot), f(f(\bot)), \dots$ dizisi **artan** bir zincir, ve kafes sonlu yükseklikliyse sonlu adımda durur. Durduğu nokta $f$'nin **en küçük** sabit noktası ($f(x) = x$ olan en küçük $x$).

**İspat**: $\bot \sqsubseteq f(\bot)$ (çünkü $\bot$ her şeyden küçük). Monotonluk: $f(\bot) \sqsubseteq f(f(\bot))$; tümevarımla zincir artan. Sonlu yükseklikli bir kafeste kesin artan bir zincir sonsuza kadar sürmez; bir noktada $f^{k+1}(\bot) = f^k(\bot)$, bir sabit nokta. En küçüklüğü: herhangi bir sabit nokta $p$ için $\bot \sqsubseteq p$, ve monotonlukla $f^i(\bot) \sqsubseteq f^i(p) = p$; yani bulunan nokta her sabit noktanın altında. $\blacksquare$

Bir CFG'de her bloğun bir değeri var ve bütün blokların değerlerinden oluşan vektör, bileşen bileşen sıralanan bir **çarpım kafesi**. Bütün blokların denklemlerini birlikte uygulamak tek bir büyük monoton fonksiyon $F$. Algoritma, $F$'yi $\bot$'dan başlayıp sabit noktaya kadar uygulamak. Teoremin iki önemli sonucu:

- **Sonlanma**: kafesin yüksekliği $h$ ve blok sayısı $n$ ise, her blok değeri en fazla $h$ kez değişebilir; toplam en fazla $nh$ değişiklik.
- **Sıradan bağımsızlık**: blokları hangi sırayla (hatta tek tek, istediğin sırayla) güncellersen güncelle, monoton olduğu sürece **aynı** en küçük sabit noktaya ulaşırsın. Sıra sadece **hızı** etkiliyor. (Ders 9.19'un Alıştırma 5'inin cevabı.)

---

## 2. Canlılık analizi

Bir değişken bir program noktasında **canlı**: o noktadan sonra, yeniden yazılmadan önce okunacak bir yol var. Ders 9.20'deki girişim grafının hammaddesi, ve ölü kod silmenin (canlı olmayan bir değişkene yapılan atama gereksiz) temeli. Her blok için:

- $\text{KULLAN}(b)$: blokta, önce tanımlanmadan **okunan** değişkenler.
- $\text{TANIM}(b)$: blokta yazılan değişkenler.

Denklemler **geriye doğru** (bilgi, kullanımdan tanıma, akışın tersine yayılıyor):

$$
\text{ÇIKIŞ}(b) = \bigcup_{s \in \text{ardıl}(b)} \text{GİRİŞ}(s), \qquad \text{GİRİŞ}(b) = \text{KULLAN}(b) \cup \big(\text{ÇIKIŞ}(b) \setminus \text{TANIM}(b)\big).
$$

Kafes: değişken kümeleri, $\subseteq$, $\bot = \emptyset$; 64 değişkene kadar tek bir `uint64_t` (Ders 5.20). İkinci denklem $\text{ÇIKIŞ}$'ta monoton ($\cup$ ve sabit bir kümeyle fark monoton), dolayısıyla Bölüm 1'in teoremi geçerli.

```c
/* Sabit nokta yinelemesi: canlilik analizi (geriye dogru, bit kumeleri) iki yolla: tur tur ve worklist */
#include <stdint.h>
#include <stdio.h>
#include "graf.h"

/* Her blok: KULLAN = blokta, once tanimlanmadan okunan degiskenler; TANIM = blokta yazilanlar.
   CANLI_CIKIS(b) = birlesim, ardillar s: CANLI_GIRIS(s)
   CANLI_GIRIS(b) = KULLAN(b) U (CANLI_CIKIS(b) - TANIM(b))           -- monoton: daha cok canli -> daha cok canli */
typedef uint64_t Kume;                                       /* en fazla 64 degisken */

static long islem;                                           /* istatistik: kac kez bir blogun denklemi hesaplandi */

static int tur_tur(const Graf *g, const Kume *kul, const Kume *tan, Kume *giris, Kume *cikis) {
    int tur = 0, degisti = 1;
    for (int b = 0; b < g->n; b++) giris[b] = cikis[b] = 0;   /* en kucuk eleman: "hicbir sey canli degil" */
    while (degisti) {
        degisti = 0; tur++;
        for (int b = g->n - 1; b >= 0; b--) {                 /* geriye dogru analiz: sondan basa gezmek daha hizli yakinsar */
            Kume c = 0;
            for (int i = g->ofset[b]; i < g->ofset[b + 1]; i++) c |= giris[g->hedef[i]];
            Kume y = kul[b] | (c & ~tan[b]); islem++;
            if (y != giris[b] || c != cikis[b]) { giris[b] = y; cikis[b] = c; degisti = 1; }
        }
    }
    return tur;
}

/* WORKLIST: sadece bir girdisi degisen bloklari yeniden hesapla. Geriye analizde bir blok degisince ONCULLERI etkilenir. */
static void worklist(const Graf *g, const Graf *ters, const Kume *kul, const Kume *tan, Kume *giris, Kume *cikis) {
    int n = g->n, *kuyruk = malloc(n * sizeof(int)), bas = 0, adet = 0; char *icinde = calloc(n, 1);
    for (int b = 0; b < n; b++) { giris[b] = cikis[b] = 0; kuyruk[adet++] = n - 1 - b; icinde[n - 1 - b] = 1; }
    while (adet) {
        int b = kuyruk[bas]; bas = (bas + 1) % n; adet--; icinde[b] = 0;     /* halka tampon (Ders 8.5) */
        Kume c = 0;
        for (int i = g->ofset[b]; i < g->ofset[b + 1]; i++) c |= giris[g->hedef[i]];
        Kume y = kul[b] | (c & ~tan[b]); islem++;
        cikis[b] = c;
        if (y != giris[b]) {
            giris[b] = y;
            for (int i = ters->ofset[b]; i < ters->ofset[b + 1]; i++) { int p = ters->hedef[i];
                if (!icinde[p]) { icinde[p] = 1; kuyruk[(bas + adet) % n] = p; adet++; } }
        }
    }
    free(kuyruk); free(icinde);
}

static Graf ters_kur(const Graf *g) {
    Kenar *k = malloc((g->m ? g->m : 1) * sizeof *k); int t = 0;
    for (int u = 0; u < g->n; u++) for (int i = g->ofset[u]; i < g->ofset[u + 1]; i++) k[t++] = (Kenar){ g->hedef[i], u };
    Graf r = graf_kur(g->n, k, g->m); free(k); return r;
}

#ifndef KUTUPHANE
/* Ders 9.19'un fonksiyonu: int f(int n) { int s = 0; for (int i = 0; i < n; i++) { if (i % 2) s += i; else s -= 1; } return s; } */
enum { N_, S_, I_ };                                         /* degiskenler: n, s, i */
static const char *dad = "nsi";
static const char *bad[] = { "giris", "kosul", "govde", "tek", "cift", "artir", "donus" };
static void yaz(Kume k) { printf("{"); int ilk = 1; for (int v = 0; v < 3; v++) if (k >> v & 1) { printf(ilk ? "%c" : ",%c", dad[v]); ilk = 0; } printf("}"); }
int main(void) {
    Kenar k[] = { {0,1}, {1,2}, {1,6}, {2,3}, {2,4}, {3,5}, {4,5}, {5,1} };
    Graf g = graf_kur(7, k, 8), r = ters_kur(&g);
    #define B(x) (1ull << (x))
    Kume kul[7] = { 0, B(I_) | B(N_), B(I_), B(S_) | B(I_), B(S_), B(I_), B(S_) };          /* giris: s=0,i=0 (n parametre) */
    Kume tan[7] = { B(S_) | B(I_), 0, 0, B(S_), B(S_), B(I_), 0 };
    Kume gi[7], ci[7];
    islem = 0; int t = tur_tur(&g, kul, tan, gi, ci);
    printf("tur tur: %d tur, %ld blok hesabi\n", t, islem);
    for (int b = 0; b < 7; b++) { printf("  %-6s giris ", bad[b]); yaz(gi[b]); printf("  cikis "); yaz(ci[b]); printf("\n"); }
    Kume gw[7], cw[7]; islem = 0; worklist(&g, &r, kul, tan, gw, cw);
    int ayni = 1; for (int b = 0; b < 7; b++) ayni &= gw[b] == gi[b] && cw[b] == ci[b];
    printf("worklist: %ld blok hesabi, sonuc ayni: %s\n", islem, ayni ? "evet" : "HAYIR");
    graf_birak(&g); graf_birak(&r);
}
#endif
```

İki strateji:

- **Tur tur** (round-robin): her turda bütün blokları sırayla güncelle; bir turda hiçbir şey değişmezse dur. Geriye doğru bir analiz için blokları **sondan başa** gezmek, bilginin bir turda uzun mesafeler yayılmasını sağlıyor.
- **Worklist**: sadece bir girdisi değişmiş blokları yeniden hesapla. Başta bütün bloklar listede. Bir bloğun $\text{GİRİŞ}$'i değişince, onu kullanan bloklar (geriye analizde **öncülleri**) listeye ekleniyor (zaten değilse). Liste boşalınca sabit nokta. Liste, Ders 8.5'in halka tamponu.

Ders 9.19'un döngülü fonksiyonu (`int f(int n) { int s = 0; for (int i = 0; i < n; i++) { if (i % 2) s += i; else s -= 1; } return s; }`), değişkenler `n`, `s`, `i`:

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined sabit.c -o sabit && ./sabit
tur tur: 3 tur, 21 blok hesabi
  giris  giris {n}  cikis {n,s,i}
  kosul  giris {n,s,i}  cikis {n,s,i}
  govde  giris {n,s,i}  cikis {n,s,i}
  tek    giris {n,s,i}  cikis {n,s,i}
  cift   giris {n,s,i}  cikis {n,s,i}
  artir  giris {n,s,i}  cikis {n,s,i}
  donus  giris {s}  cikis {}
worklist: 12 blok hesabi, sonuc ayni: evet
```

- `n`, `s`, `i` döngünün her yerinde canlı (döngü her an devam edebilir ve üçünü de okuyabilir).
- `giris`'in girişinde sadece `n` (parametre): `s` ve `i` orada yazılıyor ve önceki değerleri hiç okunmuyor.
- `donus`'un girişinde sadece `s`.
- Tur tur 3 turda (son tur sadece "değişiklik yok" doğrulaması), worklist 12 blok hesabında aynı sonuca ulaşıyor.

---

## 3. Başka bir kafes: sabit yayılımı

Bit kümeleri dışında bir kafes: her değişken için

```
             ⊤   (henüz bilinmiyor)
      ... -1  0  1  2 ...   (bilinen sabit)
             ⊥   (sabit değil)
```

Bir "düz" kafes, yüksekliği 2. İki yoldan gelen bilginin **buluşması**: biri $\top$ ise diğeri; ikisi aynı sabitse o sabit; farklıysa ⊥. Bu analiz **ileriye doğru** (atamalar akış yönünde yayılıyor) ve **iyimser**: başta her şey $\top$, "kanıt gelene kadar her şey sabit olabilir". (Burada sıra yönü canlılığınkinin tersi: kafes "yukarıdan aşağı" iniyor; teoremin aynası, en büyük sabit nokta.)

```c
/* Sabit yayilimi: duz kafes  UST (henuz bilinmiyor) > her sabit > ALT (sabit degil). Ileriye dogru, worklist. */
#include <stdio.h>
#include <string.h>

typedef struct { int tur; long d; } Deger;                  /* tur: 0 = UST, 1 = sabit d, 2 = ALT */
enum { UST, SABIT, ALT };
static Deger bulus(Deger a, Deger b) {                        /* iki yoldan gelen bilgiyi birlestir (kafeste en buyuk alt sinir) */
    if (a.tur == UST) return b;
    if (b.tur == UST) return a;
    if (a.tur == SABIT && b.tur == SABIT && a.d == b.d) return a;
    return (Deger){ ALT, 0 };
}
/* Komut: hedef = sol + sag; terim: degisken (0..V-1) ya da sabit (V + deger) */
enum { X, K, I, Y, Z, V };
static const char *vad = "xkiyz";
typedef struct { int hedef, sol, sag; } Atama;
#define SB(c) (V + (c))
typedef struct { Atama a[3]; int n; int ardil[2], na; } Blok;
static Blok blok[] = {
    /* 0 giris */ { { { X, SB(1), SB(0) }, { K, SB(5), SB(0) }, { I, SB(0), SB(0) } }, 3, { 1 }, 1 },
    /* 1 kosul */ { { { 0 } }, 0, { 2, 3 }, 2 },                                  /* i < k ? govde : cikis */
    /* 2 govde */ { { { Y, X, SB(1) }, { I, I, SB(1) } }, 2, { 1 }, 1 },          /* y = x + 1; i = i + 1 */
    /* 3 cikis */ { { { Z, Y, K } }, 1, { 0 }, 0 },                               /* z = y + k */
};
enum { NB = 4 };
static Deger terim(const Deger *d, int t) { return t >= V ? (Deger){ SABIT, t - V } : d[t]; }
static void aktar(const Blok *b, const Deger *giris, Deger *cikis) {          /* monoton: girdi alcalirsa cikti da alcalir */
    memcpy(cikis, giris, V * sizeof *cikis);
    for (int i = 0; i < b->n; i++) {
        Deger p = terim(cikis, b->a[i].sol), q = terim(cikis, b->a[i].sag), r;
        if (p.tur == ALT || q.tur == ALT) r = (Deger){ ALT, 0 };
        else if (p.tur == UST || q.tur == UST) r = (Deger){ UST, 0 };
        else r = (Deger){ SABIT, p.d + q.d };
        cikis[b->a[i].hedef] = r;
    }
}
static void yaz(const Deger *d) { for (int v = 0; v < V; v++) { printf(" %c=", vad[v]); if (d[v].tur == UST) printf("?"); else if (d[v].tur == SABIT) printf("%ld", d[v].d); else printf("X"); } }

int main(void) {
    Deger giris[NB][V], cikis[NB][V];
    for (int b = 0; b < NB; b++) for (int v = 0; v < V; v++) giris[b][v] = cikis[b][v] = (Deger){ UST, 0 };   /* iyimser baslangic */
    int kuyruk[64], bas = 0, son = 0, adim = 0; char icinde[NB] = { 0 };
    for (int b = 0; b < NB; b++) { kuyruk[son++] = b; icinde[b] = 1; }
    while (bas < son) {
        int b = kuyruk[bas++]; icinde[b] = 0; adim++;
        Deger g[V];
        for (int v = 0; v < V; v++) g[v] = (Deger){ UST, 0 };                 /* bulusun etkisiz elemani */
        for (int p = 0; p < NB; p++) for (int j = 0; j < blok[p].na; j++) if (blok[p].ardil[j] == b)
            for (int v = 0; v < V; v++) g[v] = bulus(g[v], cikis[p][v]);
        memcpy(giris[b], g, sizeof g);
        Deger c[V]; aktar(&blok[b], g, c);
        if (memcmp(c, cikis[b], sizeof c)) {
            memcpy(cikis[b], c, sizeof c);
            for (int j = 0; j < blok[b].na; j++) { int s = blok[b].ardil[j]; if (!icinde[s]) { icinde[s] = 1; kuyruk[son++] = s; } }
            printf("  adim %2d: blok %d cikisi:", adim, b); yaz(c); printf("\n");
        }
    }
    printf("sonuc (cikis blogunun cikisi):"); yaz(cikis[3]); printf("\n");
}
```

Program: `x = 1; k = 5; i = 0; while (i < k) { y = x + 1; i = i + 1; } z = y + k;`

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined sabityay.c -o sabityay && ./sabityay
  adim  1: blok 0 cikisi: x=1 k=5 i=0 y=? z=?
  adim  2: blok 1 cikisi: x=1 k=5 i=0 y=? z=?
  adim  3: blok 2 cikisi: x=1 k=5 i=1 y=2 z=?
  adim  4: blok 3 cikisi: x=1 k=5 i=0 y=? z=?
  adim  5: blok 1 cikisi: x=1 k=5 i=X y=2 z=?
  adim  6: blok 2 cikisi: x=1 k=5 i=X y=2 z=?
  adim  7: blok 3 cikisi: x=1 k=5 i=X y=2 z=7
sonuc (cikis blogunun cikisi): x=1 k=5 i=X y=2 z=7
```

- `i`: girişten 0, döngü gövdesinden 1 geliyor; buluşma ⊥ (`X`): sabit değil.
- `y`: girişten $\top$ (henüz atanmamış; iyimser varsayım "atanınca sabit olabilir"), gövdeden 2: buluşma **2**. Çıkışta `y = 2` biliniyor, ve `z = y + k` = **7**. Bir derleyici `z = 7` yazabilir.
- Kötümser bir analiz (başta her şey ⊥) `y`'nin girişteki "bilinmeyen" değerini ⊥ sayar, `z`'yi bulamazdı. İyimser başlangıç daha fazla sabit buluyor, çünkü döngülerde "henüz bir şey bilmiyorum" ile "sabit değil" arasındaki farkı koruyor (Wegman ve Zadeck'in koşullu sabit yayılımının temeli).

---

## 4. Ölçüm: sıranın etkisi

200 000 bloklu bir CFG (düz akış artı rastgele dallar ve geri kenarlar), 64 değişken, rastgele seyrek KULLAN/TANIM kümeleri. Aynı canlılık problemi üç yolla:

```
$ cc -std=c11 -O2 -Wall -Wextra olcum.c -o olcum && ./olcum
n=200000 blok, m=299999 kenar, 64 degisken:
  tur tur, sondan basa :    6 tur,   1200000 blok hesabi, 0.006 s
  tur tur, bastan sona :   29 tur,   5800000 blok hesabi, 0.031 s
  worklist             :              589195 blok hesabi, 0.010 s
  ucu ayni sabit nokta: evet
```

(Sanitizer'lı derleme temiz.)

- Üç yöntem **aynı** sabit noktaya ulaşıyor: Bölüm 1'in sıradan bağımsızlık sonucu.
- Tur tur gezmenin **yönü** 5 kat fark yaratıyor: geriye doğru bir analizde blokları sondan başa gezmek, bilgiyi bir turda düz akış boyunca bütün CFG'ye yayıyor (6 tur); baştan sona gezmek her turda bilgiyi sadece birkaç adım taşıyor (29 tur). Genel kural: ileri analizlerde **ters sonek sıra** (RPO, Ders 9.19), geri analizlerde ters CFG'nin RPO'su.
- Worklist, iyi sıralı tur tur'dan bile daha az blok hesaplıyor (değişmeyen bloklara hiç dokunmuyor), ama liste bakımının maliyeti yüzünden süre aynı mertebede. Gerçek derleyiciler genelde ikisini birleştiriyor: RPO'ya göre öncelikli bir worklist.

---

## Alıştırmalar

**1** – Canlılık analizinde $n$ blok ve $v$ değişken varsa, worklist algoritmasının en fazla kaç blok hesabı yapacağı için bir üst sınır ver. (İpucu: her bloğun $\text{GİRİŞ}$'i en fazla kaç kez değişebilir, ve her değişiklik kaç bloğu listeye ekler?)

**2** – **Ulaşan tanımlar** (reaching definitions): bir program noktasına, arada üzerine yazılmadan ulaşabilen atama komutları. Bu ileri mi geri mi bir analiz? Denklemleri yaz. Kafes ne, $\bot$ ne?

**3** – Monoton olmayan bir "analiz" düşün: $f(x) = \lnot x$, kafes $\{0, 1\}$, $0 \sqsubseteq 1$. $\bot$'dan yineleme ne yapar? Bu, veri akışı denklemlerini yazarken neden monotonluğun kontrol edilmesi gerektiğini nasıl gösteriyor?

**4** – **Aralık analizi**: her değişken için bir $[a, b]$ aralığı (dizi sınır kontrollerini kaldırmak için). Bu kafesin yüksekliği sonsuz: `for (i = 0; ; i++)` döngüsünde yineleme ne yapar? Bunu sonlu adımda bitirmenin yolu olan **genişletme** (widening) operatörü ne yapıyor?

**5** – Ders 9.19'daki saf dominatör denklemleri (Dom kümeleri) hangi kafes üzerinde, hangi yönde ve hangi başlangıç değeriyle bir sabit nokta problemi? Neden başlangıç değeri "her şey" (⊤) ve neden bu durumda en **büyük** sabit nokta isteniyor?

<details>
<summary>Cevaplar</summary>

**1** – Her bloğun $\text{GİRİŞ}$'i sadece **büyüyebiliyor** (monoton yineleme $\bot$'dan başlıyor) ve en fazla $v$ eleman alabiliyor: en fazla $v$ kez değişir. Her değişiklik, bloğun öncüllerini listeye ekliyor. Toplam liste eklemesi en fazla $\sum_b v \cdot \text{öncül}(b) = v \cdot m$, artı başlangıçtaki $n$. Blok hesabı sayısı $O(n + vm)$; bit kümeleriyle her hesap $O(\text{derece} \cdot v/64)$. Ölçümde $v = 64$, $m = 300\,000$ için sınır 19 milyon, gerçek sayı 0.59 milyon: sınır en kötü durum için, gerçek CFG'lerde bilgi birkaç turda oturuyor.

**2** – İleri analiz: tanımlar akış yönünde ilerliyor. $\text{GİRİŞ}(b) = \bigcup_{p \in \text{öncül}(b)} \text{ÇIKIŞ}(p)$; $\text{ÇIKIŞ}(b) = \text{ÜRET}(b) \cup (\text{GİRİŞ}(b) \setminus \text{ÖLDÜR}(b))$. $\text{ÜRET}(b)$, $b$'deki atamalardan blok sonuna ulaşanlar; $\text{ÖLDÜR}(b)$, $b$'nin yazdığı değişkenlerin programdaki **diğer** bütün tanımları. Kafes: programdaki atama komutlarının altkümeleri, $\subseteq$, $\bot = \emptyset$. Canlılıkla aynı biçim, ters yön; aynı motor (yönü ve birleşim işlemini parametre olarak alan tek bir çözücü) ikisini de çözüyor. SSA (Ders 9.19) bu analizi çoğunlukla gereksiz kılıyor: her kullanımın tek bir tanımı var.

**3** – $\bot = 0$, $f(0) = 1$, $f(1) = 0$, $f(0) = 1$, ... Sonsuz salınım: hiçbir zaman durmuyor, ve sabit nokta yok ($\lnot x = x$ çözümsüz). Monoton olmayan bir fonksiyonda yinelemenin artan bir zincir oluşturması garantisi yok. Gerçek analizlerde monotonluk genellikle bir **yazım hatasıyla** bozuluyor: örneğin bir aktarım fonksiyonunda, girdi bir eleman kazanınca çıktının bir eleman kaybetmesi (bir kümeyi yanlışlıkla girdiye bağlı olarak çıkarmak). Belirtisi, analizin bazı programlarda hiç bitmemesi.

**4** – `i` için yineleme: $[0, 0]$, sonra $[0, 1]$, $[0, 2]$, ... Her tur aralığı bir genişletiyor ve sonsuza kadar sürüyor (kafesin yüksekliği sonsuz, $[0, 0] \sqsubset [0, 1] \sqsubset \dots$). **Genişletme** $\nabla$: bir sınır iki yineleme arasında büyüdüyse onu hemen $\pm\infty$'a atla: $[0, 0] \nabla [0, 1] = [0, +\infty]$. Bir sonraki tur değişmiyor: sabit nokta, ama kaba. Sonra bir **daraltma** (narrowing) geçişi, döngü koşulunu (`i < n`) kullanarak sınırı geri çekebiliyor. Cousot ve Cousot'nun **soyut yorumlama** (abstract interpretation, 1977) çerçevesi; Faz 17'deki program analizinin temeli.

**5** – Kafes: blok kümelerinin altkümeleri, ama sıra **ters** ($\supseteq$; daha küçük küme = daha fazla bilgi = "kafeste daha yukarıda" ya da tersi, bakış açısına göre). İleri analiz: $\text{Dom}(v) = \{v\} \cup \bigcap_p \text{Dom}(p)$, buluşma $\cap$. Başlangıç "her şey": sabit nokta yinelemesi buradan **aşağı** iniyor ve en büyük sabit noktaya (en büyük Dom kümeleri) ulaşıyor. Neden en büyük? Döngülerde, en küçük sabit nokta (örneğin her şeyi boş kümeyle başlatmak) "döngü başlığının dominatörü yok" gibi anlamsız bir cevaba sabitlenebilir; doğru dominatör ilişkisi, denklemleri sağlayan **en büyük** çözüm. Ders 9.21'deki teorem tersine çevrilmiş kafes için aynen geçerli; iyimser sabit yayılımı da aynı "üstten başla, aşağı in" yönünü kullanıyor.

</details>

---

## Kaynaklar

- Gary Kildall, "A Unified Approach to Global Program Optimization", *POPL* 1973: veri akışı analizinin kafes çerçevesi.
- Alfred Aho, Monica Lam, Ravi Sethi ve Jeffrey Ullman, *Compilers* (2. baskı), Bölüm 9.2–9.3: veri akışı analizi ve temelleri.
- Flemming Nielson, Hanne Riis Nielson ve Chris Hankin, *Principles of Program Analysis*, Springer, 1999.
- Mark Wegman ve F. Kenneth Zadeck, "Constant Propagation with Conditional Branches", *ACM TOPLAS* 13(2), 1991.
- Patrick Cousot ve Radhia Cousot, "Abstract Interpretation: A Unified Lattice Model for Static Analysis of Programs", *POPL* 1977.

**Sıradaki ders:** NP-tamlık. P, NP, indirgeme ve SAT; derleyicideki NP-zor problemler (yazmaç ayırma, komut planlama).
