---
title: "9.13 Dinamik programlama 3: ağaç üzerinde"
description: "Alt problemlerin bir ağacın alt ağaçları olduğu DP: sonek gezinmeyle her düğümde çocukların cevaplarını birleştirmek; derleyicinin komut seçimi problemi: ara temsil ağacını makine komutu kalıplarıyla (li, add, addi, mul, slli, madd, ld, ofsetli ld) örtmek; her alt ağacın en ucuz örtüsünü aşağıdan yukarı DP ile bulmak ve x + a[i] * y için maliyet 6'ya karşı en büyük lokma yönteminin 8 ve 12'si; DP'nin doğruluğu, O(n × kalıp) maliyeti, ortak alt ifadelerde (DAG) neden çöktüğü; BURS'e hazırlık; ağaçta en büyük ağırlıklı bağımsız küme."
---

Ders 9.11–9.12'deki alt problemler bir dizinin **önekleri** ya da **aralıklarıydı**. Bu derste alt problemler bir ağacın **alt ağaçları**: her düğümün cevabı, çocuklarının cevaplarından kuruluyor. Doldurma sırası kendiliğinden belli: önce çocuklar, sonra düğüm; yani Ders 8.7'deki **sonek gezinme**. Ağaçta döngü olmadığı için alt problemler arasında hiç döngüsel bağımlılık yok, ve her düğüm bir kez işleniyor.

Dersin ana örneği bir derleyici problemi: **komut seçimi**. Ders 8.7'de bir ifadeyi ağaca çevirmiştik ve `hesapla`'nın `printf` yerine assembly yazan halinin bir derleyici olacağını söylemiştik. O derleyicinin her ağaç düğümü için bir komut üretmesi kolay ama israf: gerçek işlemciler tek bir komutla birden çok düğümün işini yapabiliyor. Hangi komutların seçileceğine karar vermek bir **örtme** problemi, ve ağaçlarda DP ile optimal olarak çözülüyor. Faz 16'daki kod üreticinin çekirdeği bu ders.

---

## 1. Problem

Derleyicinin ara temsili (IR) bir ifade ağacı. Düğüm türleri: bir yazmaçta duran değişken (`REG`), sabit (`CONST`), toplama (`ADD`), çarpma (`MUL`) ve bellekten okuma (`LOAD`). `x + a[i] * y` ifadesi, `a` 8 baytlık elemanların dizisiyse:

```
            ADD
           /    \
        REG x    MUL
                /    \
            LOAD      REG y
              |
             ADD
            /    \
        REG a     MUL
                 /    \
             REG i    CONST 8
```

Hedef işlemcinin komutları (RISC-V'ye benzer, Ders 7.4; artı ARM'ın `madd`'i) her biri ağacın küçük bir **kalıbını** (tile) örtüyor ve bir maliyeti var:

| Kalıp | Örttüğü ağaç parçası | Komut | Maliyet |
| --- | --- | --- | --- |
| `li` | `CONST k` | `li r, k` | 1 |
| `add` | `ADD(r1, r2)` | `add r, r1, r2` | 1 |
| `addi` | `ADD(r1, CONST k)` | `addi r, r1, k` | 1 |
| `mul` | `MUL(r1, r2)` | `mul r, r1, r2` | 3 |
| `slli` | `MUL(r1, CONST 2^s)` | `slli r, r1, s` | 1 |
| `madd` | `ADD(r1, MUL(r2, r3))` | `madd r, r2, r3, r1` | 3 |
| `ld` | `LOAD(r1)` | `ld r, 0(r1)` | 1 |
| `ld+ofset` | `LOAD(ADD(r1, CONST k))` | `ld r, k(r1)` | 1 |

(Maliyetler gecikme gibi düşünülebilir: çarpma toplamadan pahalı; Ders 7.23.) Kalıbın içindeki `r1`, `r2`, `r3` **delikler**: o alt ağaçların değeri önce bir yazmaca hesaplanmış olmalı. Örtme, ağacın her düğümünü tam olarak bir kalıbın örttüğü ve kalıpların deliklerde birleştiği bir parçalama. Bir örtünün maliyeti, kalıplarının maliyetlerinin toplamı. Amaç: en ucuz örtü.

---

## 2. DP

Bir düğümün en ucuz örtüsünü düşün. Kökte **bir** kalıp var. O kalıp seçilince, geri kalan iş, deliklerdeki alt ağaçları örtmek; ve bu alt ağaçlar **birbirinden bağımsız** (ağaçta paylaşılan düğüm yok). Her deliğin en ucuz örtüsü, onun kendi alt problemi. Optimal alt yapı:

$$
\text{maliyet}(n) = \min_{\text{kökte eşleşen kalıp } p} \Big( c(p) + \sum_{h \in \text{delikler}(p)} \text{maliyet}(h) \Big).
$$

Delikler her zaman $n$'nin **torunları** (kalıp en az kökü örtüyor), dolayısıyla sonek gezinmeyle onlar önceden hesaplanmış. Algoritma her düğümde her kalıbı deniyor: $O(n \cdot |\text{kalıplar}|)$, doğrusal.

```c
/* Agac ortme ile komut secimi: her alt agac icin en ucuz "kalip ortusu"nu asagidan yukari DP ile bul.
   Karsilastirma: en buyuk lokma (maximal munch), yukaridan asagi acgozlu. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef enum { REG, CONST, ADD, MUL, LOAD } Op;
typedef struct Dugum {
    Op op; const char *ad; long sabit;            /* REG: ad, CONST: sabit */
    struct Dugum *sol, *sag;
    int maliyet, kalip;                            /* DP sonucu: bu alt agacin en ucuz ortusu ve kokteki kalip */
    int yazmac;                                    /* kod uretimi: sonucun yazmac numarasi */
} Dugum;

static Dugum *d(Op op, Dugum *l, Dugum *r) { Dugum *n = calloc(1, sizeof *n); n->op = op; n->sol = l; n->sag = r; return n; }
static Dugum *reg(const char *ad) { Dugum *n = d(REG, NULL, NULL); n->ad = ad; return n; }
static Dugum *sbt(long k) { Dugum *n = d(CONST, NULL, NULL); n->sabit = k; return n; }

/* KALIPLAR. Her biri: kokte eslesiyor mu, eslesirse "delikleri" (yazmacta olmasi gereken alt agaclar) ve maliyet. */
typedef struct { const char *ad; int maliyet; int (*esles)(Dugum *n, Dugum **delik); } Kalip;

static int k_reg(Dugum *n, Dugum **h)  { (void)h; return n->op == REG ? 0 : -1; }                     /* zaten yazmacta */
static int k_li(Dugum *n, Dugum **h)   { (void)h; return n->op == CONST ? 0 : -1; }                   /* li  r, k */
static int k_add(Dugum *n, Dugum **h)  { if (n->op != ADD) return -1; h[0] = n->sol; h[1] = n->sag; return 2; }   /* add */
static int k_addi(Dugum *n, Dugum **h) { if (n->op != ADD || n->sag->op != CONST) return -1; h[0] = n->sol; return 1; } /* addi r, r, k */
static int k_mul(Dugum *n, Dugum **h)  { if (n->op != MUL) return -1; h[0] = n->sol; h[1] = n->sag; return 2; }   /* mul */
static int k_slli(Dugum *n, Dugum **h) {                                                              /* slli: 2'nin kuvvetiyle carpim */
    if (n->op != MUL || n->sag->op != CONST || n->sag->sabit <= 0 || (n->sag->sabit & (n->sag->sabit - 1))) return -1;
    h[0] = n->sol; return 1; }
static int k_madd(Dugum *n, Dugum **h) {                                                              /* madd: a + b*c tek komut */
    if (n->op != ADD || n->sag->op != MUL) return -1; h[0] = n->sol; h[1] = n->sag->sol; h[2] = n->sag->sag; return 3; }
static int k_ld(Dugum *n, Dugum **h)   { if (n->op != LOAD) return -1; h[0] = n->sol; return 1; }      /* ld r, 0(r) */
static int k_ldo(Dugum *n, Dugum **h) {                                                               /* ld r, k(r): adres toplamasi bedava */
    if (n->op != LOAD || n->sol->op != ADD || n->sol->sag->op != CONST) return -1; h[0] = n->sol->sol; return 1; }

static Kalip kaliplar[] = {
    { "reg", 0, k_reg }, { "li", 1, k_li }, { "add", 1, k_add }, { "addi", 1, k_addi }, { "mul", 3, k_mul },
    { "slli", 1, k_slli }, { "madd", 3, k_madd }, { "ld", 1, k_ld }, { "ld+ofset", 1, k_ldo } };
enum { KALIP_SAYISI = sizeof kaliplar / sizeof kaliplar[0] };

/* DP: maliyet(n) = min over eslesen kalip p ( p.maliyet + sum maliyet(delik) ). Sonek gezinme: once cocuklar. */
static void etiketle(Dugum *n) {
    if (!n) return;
    etiketle(n->sol); etiketle(n->sag);
    n->maliyet = 1 << 30;
    for (int k = 0; k < KALIP_SAYISI; k++) {
        Dugum *h[3]; int dn = kaliplar[k].esles(n, h);
        if (dn < 0) continue;
        int m = kaliplar[k].maliyet;
        for (int i = 0; i < dn; i++) m += h[i]->maliyet;     /* deliklerin alt agaclari zaten etiketlendi */
        if (m < n->maliyet) { n->maliyet = m; n->kalip = k; }
    }
}

/* EN BUYUK LOKMA: kokte eslesen kaliplar arasinda EN COK dugum ortenini sec (maliyete bakmadan), deliklere in. */
static int ortulen(int k) {                                 /* kalip k kac IR dugumunu ortuyor */
    switch (k) { case 3: case 5: case 6: return 2; case 8: return 3; default: return 1; }
}
static int lokma(Dugum *n) {
    int en = -1, en_boy = 0;
    for (int k = 0; k < KALIP_SAYISI; k++) { Dugum *h[3]; if (kaliplar[k].esles(n, h) < 0) continue;
        int b = ortulen(k); if (b > en_boy) { en_boy = b; en = k; } }
    n->kalip = en;
    Dugum *h[3]; int dn = kaliplar[en].esles(n, h), m = kaliplar[en].maliyet;
    for (int i = 0; i < dn; i++) m += lokma(h[i]);
    return n->maliyet = m;
}

/* Kod uretimi: secilen kaliplari sonek sirayla yaz */
static int sonraki_yazmac;
static void uret(Dugum *n) {
    Dugum *h[3]; int k = n->kalip, dn = kaliplar[k].esles(n, h);
    for (int i = 0; i < dn; i++) uret(h[i]);
    if (k == 0) { n->yazmac = -1; return; }
    n->yazmac = sonraki_yazmac++;
    #define Y(x) ((x)->yazmac < 0 ? (x)->ad : (snprintf(buf[bi], 8, "t%d", (x)->yazmac), buf[bi++]))
    char buf[4][8]; int bi = 0;
    switch (k) {
    case 1: printf("    li   t%d, %ld\n", n->yazmac, n->sabit); break;
    case 2: { const char *a = Y(h[0]), *b = Y(h[1]); printf("    add  t%d, %s, %s\n", n->yazmac, a, b); break; }
    case 3: printf("    addi t%d, %s, %ld\n", n->yazmac, Y(h[0]), n->sag->sabit); break;
    case 4: { const char *a = Y(h[0]), *b = Y(h[1]); printf("    mul  t%d, %s, %s\n", n->yazmac, a, b); break; }
    case 5: { int s = 0; for (long v = n->sag->sabit; v > 1; v >>= 1) s++; printf("    slli t%d, %s, %d\n", n->yazmac, Y(h[0]), s); break; }
    case 6: { const char *a = Y(h[0]), *b = Y(h[1]), *c = Y(h[2]); printf("    madd t%d, %s, %s, %s   # %s + %s*%s\n", n->yazmac, b, c, a, a, b, c); break; }
    case 7: printf("    ld   t%d, 0(%s)\n", n->yazmac, Y(h[0])); break;
    case 8: printf("    ld   t%d, %ld(%s)\n", n->yazmac, n->sol->sag->sabit, Y(h[0])); break;
    }
}

static Dugum *ornek(void) {      /* x + a[i] * y,  a[i] = LOAD(a + i*8)   (8 baytlik elemanlar) */
    return d(ADD, reg("x"), d(MUL, d(LOAD, d(ADD, reg("a"), d(MUL, reg("i"), sbt(8))), NULL), reg("y")));
}
static Dugum *ornek2(void) {     /* p->alan + 1, p->alan = LOAD(p + 16) */
    return d(ADD, d(LOAD, d(ADD, reg("p"), sbt(16)), NULL), sbt(1));
}

int main(void) {
    for (int t = 0; t < 2; t++) {
        for (int madd3 = 1; madd3 >= 0; madd3--) {
            kaliplar[6].maliyet = madd3 ? 3 : 5;
            Dugum *r = t ? ornek2() : ornek();
            printf("%s, madd maliyeti %d\n", t ? "p->alan + 1" : "x + a[i] * y", kaliplar[6].maliyet);
            etiketle(r); printf("  DP (en ucuz ortu): maliyet %d\n", r->maliyet); sonraki_yazmac = 1; uret(r);
            lokma(r);    printf("  en buyuk lokma:    maliyet %d\n", r->maliyet); sonraki_yazmac = 1; uret(r);
            if (t) break;
        }
    }
}
```

Üç fonksiyon:

- **`etiketle`**: DP. Sonek gezinme; her düğümde eşleşen her kalıp için maliyet hesaplanıyor, en ucuzu `kalip` alanına yazılıyor.
- **`lokma`**: karşılaştırma için **en büyük lokma** (maximal munch): kökte, maliyete bakmadan **en çok düğüm örten** kalıbı seç, sonra deliklere in. Yukarıdan aşağı açgözlü bir yöntem; birçok basit derleyicinin ve elle yazılmış kod üreticilerin seçimi.
- **`uret`**: seçilen kalıpları sonek sırayla komuta çeviriyor; her kalıp bir geçici yazmaç (`t1`, `t2`, ...) üretiyor. Yazmaç ayırma (bu geçicilerin gerçek yazmaçlara yerleştirilmesi) ayrı bir problem: Ders 9.20.

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined secici.c -o secici && ./secici
x + a[i] * y, madd maliyeti 3
  DP (en ucuz ortu): maliyet 6
    slli t1, i, 3
    add  t2, a, t1
    ld   t3, 0(t2)
    madd t4, t3, y, x   # x + t3*y
  en buyuk lokma:    maliyet 8
    li   t1, 8
    madd t2, i, t1, a   # a + i*t1
    ld   t3, 0(t2)
    madd t4, t3, y, x   # x + t3*y
x + a[i] * y, madd maliyeti 5
  DP (en ucuz ortu): maliyet 7
    slli t1, i, 3
    add  t2, a, t1
    ld   t3, 0(t2)
    mul  t4, t3, y
    add  t5, x, t4
  en buyuk lokma:    maliyet 12
    li   t1, 8
    madd t2, i, t1, a   # a + i*t1
    ld   t3, 0(t2)
    madd t4, t3, y, x   # x + t3*y
p->alan + 1, madd maliyeti 3
  DP (en ucuz ortu): maliyet 2
    ld   t1, 16(p)
    addi t2, t1, 1
  en buyuk lokma:    maliyet 2
    ld   t1, 16(p)
    addi t2, t1, 1
```

`madd` maliyeti 3 iken (ilk blok):

- **DP**: `i * 8`'i `slli` ile (kaydırma, 1), adresi `add` ile, yüklemeyi `ld` ile, ve dış `x + t3 * y`'yi tek bir `madd` ile: maliyet 6.
- **En büyük lokma**: adres hesabında `a + i * 8`'i de `madd` ile örtüyor (iki düğüm örttüğü için `add`'den "daha büyük lokma"), bu yüzden 8 bir yazmaca yüklenmek zorunda (`li`) ve pahalı çarpma kullanılıyor: maliyet 8.

`madd`'in maliyeti 5 olsaydı (bazı işlemcilerde çarp-topla ayrı bir çarpma ve toplamadan yavaş): DP ikisini de bırakıp `mul` + `add` seçiyor (maliyet 7); en büyük lokma kalıp boyutundan başka bir şeye bakmadığı için aynı kodu üretiyor ve maliyet 12'ye çıkıyor.

Üçüncü örnekte (`p->alan + 1`, bir struct alanını okuyup artırmak) iki yöntem de aynı: `ld 16(p)` adres toplamasını yüklemenin içine katıyor, `addi` sabiti toplamanın içine.

### Doğruluk ve sınırlar

DP'nin optimal olduğunun ispatı yukarıdaki bağıntı: her örtünün kökünde bir kalıp var; kalıp sabitlenince en iyi örtü, deliklerin en iyi örtülerinin birleşimi (bağımsız alt ağaçlar; birinin örtüsü öbürünü etkilemiyor). Değiştirme argümanı (Ders 9.10) burada "herhangi bir optimal örtüde bir deliğin örtüsünü onun DP örtüsüyle değiştir, maliyet artmaz" diyor.

Sınırlar:

- **Ağaç olmalı.** Gerçek kodda alt ifadeler **paylaşılıyor**: `a[i] + a[i]` hesaplanırken `a[i]` iki kez değil bir kez hesaplanmalı. IR o zaman bir ağaç değil bir **DAG** (yönlü döngüsüz graf). DAG'larda paylaşılan bir düğümün iki ebeveyni farklı kalıplar isteyebilir, alt problemler bağımsızlığını kaybediyor, ve optimal örtme NP-zor (Ders 9.22; Bruno ve Sethi, 1976). Derleyiciler DAG'ı paylaşılan düğümlerde ağaçlara bölüp her ağacı ayrı DP ile örtüyor.
- **Maliyet modeli.** "Maliyet" tek bir sayı; gerçek işlemcide süre, komutların birbirini nasıl beklediğine (Ders 7.21–7.23), yazmaç baskısına ve cache'e bağlı. DP verilen modelde optimal; model gerçeği ne kadar yansıtıyorsa o kadar iyi.

### BURS'e doğru

Bu kodda kalıp eşleme elle yazılmış fonksiyonlar. Gerçek kod üreticilerde kalıplar bir **dilbilgisi** olarak yazılıyor (`reg: ADD(reg, MUL(reg, reg))  maliyet 3  "madd ..."`) ve eşleştirici bu dilbilgisinden **otomatik olarak** üretiliyor. **BURS** (bottom-up rewrite system; Pelegrí-Llopart ve Graham, 1988) daha da ileri gidip DP'nin işini derleyici **derlenirken** yapıyor: olası bütün "durumları" (bir alt ağacın her kalıp hedefi için maliyet vektörünü) önceden bir tabloya döküp, çalışma anında her düğümde sadece bir tablo bakışı yapıyor. lcc'nin `lburg`'ü, Go derleyicisinin ve LLVM'in (TableGen kalıplarından üretilen `ISelMatcher`'ı) komut seçicileri bu ailenin üyeleri. Faz 16'da ve Faz 18'deki kod üretici üreteçlerinde (Ders 18.15) bu fikre döneceğiz.

---

## 3. Ağaçta DP: genel kalıp

Komut seçimi tek örnek değil. Ağaç DP'sinin genel kalıbı: her düğüm için birkaç **durum** tanımla, her durumun değerini çocukların durumlarından hesapla. Klasik örnek: **ağaçta en büyük ağırlıklı bağımsız küme**: düğümlerin ağırlıkları var; hiçbir ebeveyn-çocuk çifti birlikte seçilemez; toplam ağırlığı en büyük kümeyi seç. (Bir şirketin hiyerarşisinde, kimsenin doğrudan amiriyle birlikte davet edilmediği en "eğlenceli" parti; CLRS Problem 15-6.)

Her düğüm için iki durum: $\text{al}(v)$, $v$ seçiliyken alt ağacının en iyisi; $\text{alma}(v)$, $v$ seçili değilken.

$$
\text{al}(v) = w_v + \sum_{c} \text{alma}(c), \qquad \text{alma}(v) = \sum_{c} \max(\text{al}(c), \text{alma}(c)).
$$

```c
/* Agacta en buyuk agirlikli bagimsiz kume (komsu iki dugum birlikte secilemez): her dugumde iki deger */
#include <stdio.h>
#include <stdlib.h>
#define N 18
static int ebeveyn[N], agirlik[N], n;
static long al[N], alma[N];       /* al[v]: v secili, v'nin alt agacinin en iyisi; alma[v]: v secili degil */
int main(void) {
    srand(8); long hata = 0;
    for (int t = 0; t < 2000; t++) {
        n = 2 + rand() % (N - 1);
        for (int v = 0; v < n; v++) { agirlik[v] = 1 + rand() % 20; ebeveyn[v] = v ? rand() % v : -1; }   /* v'nin ebeveyni ondan kucuk: 0 kok */
        for (int v = 0; v < n; v++) { al[v] = agirlik[v]; alma[v] = 0; }
        for (int v = n - 1; v > 0; v--) {          /* cocuklar ebeveynden sonra numaralandigi icin tersten = sonek sira */
            int e = ebeveyn[v];
            al[e] += alma[v];                       /* e secildiyse v secilemez */
            alma[e] += al[v] > alma[v] ? al[v] : alma[v];   /* e secilmediyse v icin en iyisi */
        }
        long dp = al[0] > alma[0] ? al[0] : alma[0], kk = 0;
        for (int m = 0; m < (1 << n); m++) {        /* kaba kuvvet */
            int ok = 1; long top = 0;
            for (int v = 0; v < n && ok; v++) if (m >> v & 1) { top += agirlik[v]; if (v && (m >> ebeveyn[v] & 1)) ok = 0; }
            if (ok && top > kk) kk = top;
        }
        if (dp != kk) hata++;
    }
    printf("2000 rastgele agac (en fazla %d dugum): DP ile kaba kuvvet %ld kez farkli\n", N, hata);
}
```

Ağaç bir ebeveyn dizisiyle tutuluyor, ve her düğümün ebeveyni kendisinden küçük numaralı; bu yüzden düğümleri **ters** sırada gezmek, her düğümü bütün çocuklarından sonra işlemek demek: sonek sıra, özyinelemesiz.

```
$ cc -std=c11 -O2 -Wall -Wextra bagimsiz.c -o bagimsiz && ./bagimsiz
2000 rastgele agac (en fazla 18 dugum): DP ile kaba kuvvet 0 kez farkli
```

2000 rastgele ağaçta, bütün $2^n$ altkümeyi deneyen kaba kuvvetle aynı sonuç. DP $O(n)$, kaba kuvvet $O(2^n \cdot n)$. Aynı problem **genel graflarda** NP-zor (Ders 9.22); ağaç yapısı onu doğrusal yapıyor. Bu, ağaç DP'sinin en önemli dersi: genel graflarda zor olan birçok problem (bağımsız küme, köşe örtüsü, renklendirme) ağaçlarda, ve "ağaca benzeyen" graflarda (küçük ağaç genişliği), dinamik programlamayla verimli çözülüyor.

---

## Alıştırmalar

**1** – Bölüm 1'deki tabloya x86'nın ölçekli indeksli adreslemesini (Ders 7.7) ekle: `ldx r, (r1, r2, s)` = `LOAD(ADD(r1, MUL(r2, CONST 2^s)))`, maliyet 1. `x + a[i] * y` için DP ne seçer ve maliyet kaç olur (`madd` 3 iken)? En büyük lokma?

**2** – `x * 2 + 1` ifadesinin ağacını çiz. DP hangi kalıpları seçer, maliyet kaç? Bir de `CONST 7 * x` (sabit **solda**): `slli` neden eşleşmez, ve bunu nasıl düzeltirsin (birden fazla yol var)?

**3** – `(a + b) * (a + b)` ifadesinde `a + b` bir kez hesaplanmalı. IR'yi bir DAG olarak çiz. Ağaç DP'sini paylaşılan düğüm iki kez sayılmayacak şekilde nasıl uygularsın, ve neden optimal olmayabilir?

**4** – En büyük ağırlıklı bağımsız küme DP'sinden, seçilen **düğümleri** de geri izleyerek bul. Hangi bilgiyi saklaman gerekir?

**5** – Bir ağaçta **köşe örtüsü**: her kenarın en az bir ucunu içeren en küçük düğüm kümesi. DP durumlarını ve bağıntıyı yaz. Bağımsız kümeyle ilişkisi ne?

<details>
<summary>Cevaplar</summary>

**1** – `a[i]`'nin bütün adres hesabı (`ADD(a, MUL(i, 8))`) ve yükleme tek bir `ldx t1, (a, i, 3)` ile örtülüyor: maliyet 1, delikler `a` ve `i` (zaten yazmaçta, 0). Sonra dış `x + t1 * y` için `madd`: 3. Toplam **4**; önceki en iyi 6 idi. En büyük lokma kökte `madd`'i (2 düğüm) seçer, sonra `LOAD`'da `ldx`'i (4 düğüm; `ld+ofset` eşleşmiyor çünkü adresin sağ çocuğu sabit değil): bu sefer o da 4 bulur. Zengin adresleme modları, karmaşık komut kümelerinde (CISC) komut seçiminin ağırlıklı olarak "adres hesabını yüklemenin içine katmak" olmasının sebebi.

**2** – `ADD(MUL(REG x, CONST 2), CONST 1)`. Kökte `addi` (sağ çocuk sabit, deliği `MUL(x, 2)`) ya da `add` (iki delik; `CONST 1` için `li`) ya da `madd` (`ADD(r, MUL(r, r))` biçimi değil, çünkü `MUL` solda; eşleşmez). `MUL(x, 2)` için `slli` (1) ya da `mul` + `li` (4). DP: `slli t1, x, 1; addi t2, t1, 1`, maliyet 2. `MUL(CONST 7, REG x)`'te `slli`'nin kalıbı sabiti **sağda** arıyor; 7 zaten 2'nin kuvveti değil ama `MUL(CONST 8, x)` de eşleşmezdi. Düzeltmeler: (a) değişmeli işlemler için kalıbın iki yönlü halini de ekle (`MUL(CONST, r)`); (b) IR'yi kod seçiminden önce **normalleştir**: değişmeli işlemlerde sabiti hep sağa koy (derleyicilerin "kanonikleştirme" geçişi; Faz 16). 7 için ise `slli` + `sub` (`x * 8 - x`) bir kalıp olarak eklenebilir: Ders 5.14'teki sabitle çarpma.

**3** – DAG: `MUL`'un iki çocuğu da **aynı** `ADD(a, b)` düğümü. Yöntem: paylaşılan düğümü bir **ağaç kökü** gibi ayrı örtüp sonucunu bir yazmaçta tut; onu kullanan her yer o düğümü bir `REG` yaprağı gibi görür. `ADD(a, b)` → `add t1, a, b` (1); `MUL(t1, t1)` → `mul t2, t1, t1` (3): maliyet 4. Optimal olmayabilir, çünkü paylaşılan düğümün **içinin** bir ebeveynin kalıbına katılması bazen daha ucuz olur: bir ebeveyn adres hesabını yüklemenin içine katabilirdi (`ld k(r)`), öteki ise değeri bir yazmaçta istiyor. Ya iki kez hesaplamak ya da katmaktan vazgeçmek gerekiyor; en iyi karar genel DAG'larda NP-zor.

**4** – Her düğümde iki değer zaten var. Kökten başla: $\text{al}(0) \ge \text{alma}(0)$ ise kökü seç. Bir düğüm seçildiyse bütün çocukları **seçilmez** durumda; bir düğüm seçilmediyse her çocuk için $\text{al}(c) \ge \text{alma}(c)$ ise çocuğu seç. Bu, ebeveynden çocuklara inen (önek) bir gezinme; her düğümün "seçildi mi" kararı ebeveyninin kararına ve kendi iki değerine bağlı. Ekstra bilgi gerekmiyor; iki değer yeterli (Ders 9.12'deki sırt çantası geri izlemesi gibi, karar tablodan yeniden çıkarılıyor). Ebeveyn dizisinde, düğümleri **artan** sırada gezmek bu önek sırayı veriyor.

**5** – $\text{iç}(v)$: $v$ örtüde, alt ağacının en küçük örtüsü; $\text{dış}(v)$: $v$ örtüde değil. $\text{iç}(v) = 1 + \sum_c \min(\text{iç}(c), \text{dış}(c))$; $\text{dış}(v) = \sum_c \text{iç}(c)$ ($v$ yoksa her $(v, c)$ kenarını örtmek için her çocuk örtüde olmalı). Cevap $\min(\text{iç}(\text{kök}), \text{dış}(\text{kök}))$. İlişki: bir küme köşe örtüsüdür ancak ve ancak tümleyeni bağımsız kümedir (bir kenarın iki ucu da tümleyendeyse, örtü o kenarı örtmüyor). Dolayısıyla en küçük köşe örtüsü = $n$ − en büyük bağımsız küme (birim ağırlıklarla). Bu ilişki her graf için geçerli; genel graflarda ikisi de NP-zor, ağaçlarda ikisi de doğrusal.

</details>

---

## Kaynaklar

- Andrew Appel, *Modern Compiler Implementation in C*, Bölüm 9: komut seçimi, en büyük lokma ve dinamik programlama ile optimal örtme.
- Alfred Aho, Mahadevan Ganapathi ve Steven Tjiang, "Code Generation Using Tree Matching and Dynamic Programming", *ACM TOPLAS* 11(4), 1989.
- Eduardo Pelegrí-Llopart ve Susan Graham, "Optimal Code Generation for Expression Trees: An Application of BURS Theory", *POPL* 1988.
- Christopher Fraser, David Hanson ve Todd Proebsting, "Engineering a Simple, Efficient Code-Generator Generator", *ACM LOPLAS* 1(3), 1992: `iburg`.
- John Bruno ve Ravi Sethi, "Code Generation for a One-Register Machine", *Journal of the ACM* 23(3), 1976: DAG'larda kod üretiminin NP-tamlığı.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Problem 15-6: şirket partisi planlaması.

**Sıradaki ders:** BFS ve DFS. Gezinme, DFS ağacı ve kenar sınıflandırması (ileri, geri, çapraz); döngü tespitinin temeli.
