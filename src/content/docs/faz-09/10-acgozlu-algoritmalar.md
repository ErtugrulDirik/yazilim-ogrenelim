---
title: "9.10 Açgözlü algoritmalar"
description: "Her adımda o an en iyi görüneni seçip geri dönmemek: aktivite seçiminde 'en erken biten' kuralı, değiştirme argümanıyla optimallik ispatı ve 20 000 rastgele örnekte kaba kuvvetle doğrulama; aynı problemde 'en kısa' ve 'en erken başlayan' kurallarının yanılması; madeni parada açgözlülüğün Türk kuruşunda doğru, {1, 3, 4}'te yanlış olması; Huffman kodlaması: en düşük iki frekansı birleştiren açgözlü ağaç, önek-serbest kodlar, entropiye 0.034 bit yakınlık; sözlük dosyasını %54.5'e sıkıştırıp bellekte geri açmak."
---

Bazı problemler adım adım çözülebiliyor ve her adımda yapılacak doğru seçim **o anki** duruma bakılarak anlaşılabiliyor: geleceği düşünmeye, seçenekleri karşılaştırmaya, geri dönmeye gerek yok. Böyle bir strateji **açgözlü** (greedy) bir algoritma. Kod genelde kısa ve hızlı. Zor olan, açgözlülüğün **doğru** olduğunu göstermek; çünkü çoğu problemde değil. Bu ders üç örnekle açgözlü stratejinin hem çalıştığı hem yanıldığı yerleri gösteriyor ve doğruluğunu ispatlamanın standart yöntemini kuruyor. Dersin sonunda Faz 9 projesinin (Ders 9.24) çekirdeğini yazacağız: Huffman kodlaması.

---

## 1. Aktivite seçimi

Bir salonu kullanmak isteyen $n$ etkinlik var, her biri $[b_i, s_i)$ zaman aralığında. Çakışan iki etkinlik aynı anda yapılamaz. En fazla sayıda etkinliği seçmek istiyoruz.

Akla gelen açgözlü kurallar: en kısa süreni seç; en erken başlayanı seç; en az çakışanı seç; **en erken biteni** seç. Sonuncusu doğru, öbürleri değil.

```c
/* Aktivite secimi: en erken BITENI sec. 20 000 rastgele kucuk ornekte kaba kuvvetle karsilastir. */
#include <stdio.h>
#include <stdlib.h>

typedef struct { int bas, son; } Aktivite;            /* [bas, son) */

static int son_kars(const void *x, const void *y) { const Aktivite *a = x, *b = y; return (a->son > b->son) - (a->son < b->son); }

static int acgozlu(Aktivite *a, int n, int *secilen) {
    qsort(a, n, sizeof *a, son_kars);                 /* bitis zamanina gore sirala */
    int k = 0, son = -1;
    for (int i = 0; i < n; i++)
        if (a[i].bas >= son) { secilen[k++] = i; son = a[i].son; }   /* oncekiyle cakismiyorsa al */
    return k;
}

static int kaba_kuvvet(const Aktivite *a, int n) {    /* butun 2^n altkume: en buyuk cakismasiz */
    int en = 0;
    for (int m = 0; m < (1 << n); m++) {
        int ok = 1, say = 0;
        for (int i = 0; i < n && ok; i++) if (m >> i & 1) { say++;
            for (int j = i + 1; j < n; j++) if ((m >> j & 1) && a[i].bas < a[j].son && a[j].bas < a[i].son) { ok = 0; break; } }
        if (ok && say > en) en = say;
    }
    return en;
}

/* Yanlis acgozlu kurallar: en kisa sure, en erken baslayan */
static int kural(Aktivite *a, int n, int (*kars)(const void *, const void *)) {
    Aktivite b[16]; for (int i = 0; i < n; i++) b[i] = a[i];
    qsort(b, n, sizeof *b, kars);
    int k = 0; int secili[16];
    for (int i = 0; i < n; i++) { int ok = 1; for (int j = 0; j < k; j++) if (b[i].bas < b[secili[j]].son && b[secili[j]].bas < b[i].son) ok = 0; if (ok) secili[k++] = i; }
    return k;
}
static int sure_kars(const void *x, const void *y) { const Aktivite *a = x, *b = y; int p = a->son - a->bas, q = b->son - b->bas; return (p > q) - (p < q); }
static int bas_kars(const void *x, const void *y) { const Aktivite *a = x, *b = y; return (a->bas > b->bas) - (a->bas < b->bas); }

int main(void) {
    Aktivite a[] = { {1,4}, {3,5}, {0,6}, {5,7}, {3,9}, {5,9}, {6,10}, {8,11}, {8,12}, {2,14}, {12,16} };
    int n = 11, s[11];
    int k = acgozlu(a, n, s);
    printf("CLRS ornegi: %d aktivite:", k); for (int i = 0; i < k; i++) printf(" [%d,%d)", a[s[i]].bas, a[s[i]].son); printf("\n");
    srand(9); int hata = 0, kisa_kotu = 0, erken_kotu = 0;
    for (int t = 0; t < 20000; t++) {
        int m = 1 + rand() % 12; Aktivite b[16];
        for (int i = 0; i < m; i++) { b[i].bas = rand() % 20; b[i].son = b[i].bas + 1 + rand() % 8; }
        int opt = kaba_kuvvet(b, m);
        if (kural(b, m, sure_kars) < opt) kisa_kotu++;
        if (kural(b, m, bas_kars) < opt) erken_kotu++;
        int sec[16]; if (acgozlu(b, m, sec) != opt) hata++;
    }
    printf("20000 rastgele ornek: en erken biten %d kez optimal degil; en kisa %d kez, en erken baslayan %d kez\n", hata, kisa_kotu, erken_kotu);
}
```

```
$ cc -std=c11 -O2 -Wall -Wextra -fsanitize=address,undefined aktivite.c -o aktivite && ./aktivite
CLRS ornegi: 4 aktivite: [1,4) [5,7) [8,11) [12,16)
20000 rastgele ornek: en erken biten 0 kez optimal degil; en kisa 615 kez, en erken baslayan 4966 kez
```

20 000 rastgele küçük örnekte (en fazla 12 etkinlik, bütün $2^{12}$ altkümeyi deneyen kaba kuvvetle karşılaştırarak): "en erken biten" her seferinde optimal, "en kısa" 615 kez, "en erken başlayan" yaklaşık her dört örnekten birinde yanılıyor. Yanılan bir kural için tek bir karşı örnek yeter; "en erken başlayan" için: $[0, 10)$, $[1, 2)$, $[3, 4)$. Kural uzun etkinliği seçip ikisini kaybediyor.

### İspat: değiştirme argümanı

Test, kuralın doğru olduğunu **göstermiyor**, sadece kolayca bulunacak bir karşı örnek olmadığını söylüyor. İspat:

**İddia**: en erken biten etkinlik $e$, bir optimal çözümün içindedir.

**İspat**: $O$ herhangi bir optimal çözüm, ve $O$'daki en erken biten etkinlik $f$ olsun. $f = e$ ise bitti. Değilse, $e$ bütün etkinliklerin en erken biteni olduğu için $s_e \le s_f$. $O$'dan $f$'i çıkarıp yerine $e$'yi koy: $O' = O \setminus \{f\} \cup \{e\}$. $O$'daki diğer bütün etkinlikler $f$ bittikten sonra başlıyor ($f$, $O$'nun en erken biteniydi ve $O$ çakışmasızdı), dolayısıyla $e$ bittikten **sonra** da başlıyorlar ($s_e \le s_f$). $O'$ çakışmasız ve $|O'| = |O|$: o da optimal, ve $e$'yi içeriyor. $\blacksquare$

İlk seçim güvenli. Geriye, $e$ ile çakışmayan etkinliklerden oluşan **daha küçük aynı türden bir problem** kalıyor (optimal alt yapı), ve aynı argüman tümevarımla her adımda uygulanıyor.

Bu iki parça, açgözlülüğün doğruluğunun standart ispatı:

1. **Açgözlü seçim özelliği**: açgözlü seçimi içeren bir optimal çözüm var. Genelde **değiştirme argümanıyla** (exchange argument) gösteriliyor: herhangi bir optimal çözümü, değerini kötüleştirmeden açgözlü seçimi içerecek şekilde değiştir.
2. **Optimal alt yapı**: seçimden sonra kalan problemin optimal çözümü, seçimle birleşince bütün problemin optimal çözümünü veriyor.

Maliyet: sıralama $O(n \log n)$, tarama $O(n)$.

---

## 2. Madeni para

Para üstü vermek: $x$ kuruşu en az sayıda madeni parayla oluştur. Açgözlü kural: en büyük madeni parayı sığdığı kadar kullan, sonra bir küçüğü...

```c
/* Para ustu: acgozlu (en buyuk madeni para) ne zaman optimal? Dinamik programlamayla karsilastir (Ders 9.12) */
#include <stdio.h>
static int acgozlu(const int *m, int k, int x) { int say = 0; for (int i = k - 1; i >= 0; i--) { say += x / m[i]; x %= m[i]; } return x ? -1 : say; }
static int dp(const int *m, int k, int x) { int en[1001]; en[0] = 0;
    for (int v = 1; v <= x; v++) { en[v] = 1 << 20; for (int i = 0; i < k; i++) if (m[i] <= v && en[v - m[i]] + 1 < en[v]) en[v] = en[v - m[i]] + 1; }
    return en[x]; }
int main(void) {
    int tl[] = { 1, 5, 10, 25, 50, 100 }, tuhaf[] = { 1, 3, 4 };
    int kotu = 0; for (int x = 1; x <= 1000; x++) if (acgozlu(tl, 6, x) != dp(tl, 6, x)) kotu++;
    printf("{1,5,10,25,50,100} kurus: 1..1000 icinde acgozlu %d kez optimal degil\n", kotu);
    kotu = 0; int ilk = 0; for (int x = 1; x <= 1000; x++) if (acgozlu(tuhaf, 3, x) != dp(tuhaf, 3, x)) { if (!ilk) ilk = x; kotu++; }
    printf("{1,3,4}: %d kez optimal degil; ilk ornek x=%d: acgozlu %d, optimal %d\n", kotu, ilk, acgozlu(tuhaf, 3, ilk), dp(tuhaf, 3, ilk));
}
```

```
$ cc -std=c11 -O2 -Wall para.c -o para && ./para
{1,5,10,25,50,100} kurus: 1..1000 icinde acgozlu 0 kez optimal degil
{1,3,4}: 249 kez optimal degil; ilk ornek x=6: acgozlu 3, optimal 2
```

Türk kuruşlarıyla (1, 5, 10, 25, 50 kuruş ve 1 TL) açgözlü kural 1'den 1000 kuruşa kadar her tutarda optimal; ama $\{1, 3, 4\}$ madeni paralarıyla 6 kuruş için açgözlü $4 + 1 + 1$ (3 para) veriyor, optimal $3 + 3$ (2 para). Karşılaştırma için kullanılan `dp`, bütün alt tutarların cevabını tabloya yazan dinamik programlama: Ders 9.11–9.12'nin konusu, ve açgözlülüğün yanıldığı problemlerin genel çözümü.

Açgözlülüğün hangi madeni para sistemlerinde doğru olduğu ("kanonik" sistemler) şaşırtıcı derecede ince bir soru; bir sistemin kanonik olup olmadığını polinom zamanda test etmek mümkün (Pearson, 2005), ama basit bir kural yok. Gerçek ülkelerin para sistemleri neredeyse hep kanonik; tarihi bir istisna, İngiltere'nin 1971 öncesi sistemi (1, 3, 6, 12, 24, 30 peni; 48 peni için açgözlü $30 + 12 + 6$, optimal $24 + 24$).

---

## 3. Huffman kodlaması

Bir dosyadaki her bayt 8 bitle saklanıyor. Ama bir metin dosyasında `e` harfi `q`'dan 64 kat sık geçiyor; sık karakterlere kısa, seyrek karakterlere uzun kodlar verirsek toplam bit sayısı azalır. Mors alfabesindeki `E` = `·`, `Q` = `−−·−` fikri.

Değişken uzunluklu kodların bir tehlikesi var: `a` = `0`, `b` = `01` ise `01` bir `b` mi, yoksa `a` ve ardından başka bir şey mi? Çözüm **önek-serbest** (prefix-free) kod: hiçbir kod başka bir kodun öneki değil. O zaman bit dizisi soldan sağa tek anlamlı olarak çözülebiliyor. Önek-serbest bir kod bir **ikili ağaç** olarak düşünülebilir: semboller yapraklarda, kod kökten yaprağa giden yol (sol 0, sağ 1). Ders 8.17'deki trie'nin ikili hali; yapraklarda durulduğu için hiçbir kod öbürünün öneki olamıyor.

Problem: frekansları $f_c$ verilen semboller için, toplam bit sayısı $\sum_c f_c \cdot \text{derinlik}(c)$'yi en aza indiren ikili ağacı bul.

**Huffman'ın açgözlü algoritması** (David Huffman, 1952, bir ders ödevi olarak): her sembolü tek düğümlü bir ağaç yap. En düşük frekanslı **iki** ağacı alıp onları çocuk yapan yeni bir ağaçta birleştir (frekansı ikisinin toplamı). Tek ağaç kalana kadar tekrarla. "En küçük iki" sorusu her adımda bir öncelik kuyruğu: Ders 8.12'nin heap'i. $k$ farklı sembol için $O(k \log k)$.

```c
/* Huffman kodlamasi: frekanslardan agac (min-heap ile, Ders 8.12), kodlar, bellekte kodla-coz, boyut ve entropi */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint64_t frekans; int sol, sag; int sembol; } Dugum;   /* yaprak: sol = sag = -1 */
static Dugum d[511];                                  /* en fazla 256 yaprak + 255 ic dugum */
static int heap[256], hn;

static int kucuk(int a, int b) { return d[a].frekans < d[b].frekans; }
static void heap_ekle(int x) {
    int i = hn++;
    while (i > 0 && kucuk(x, heap[(i - 1) / 2])) { heap[i] = heap[(i - 1) / 2]; i = (i - 1) / 2; }
    heap[i] = x;
}
static int heap_cek(void) {
    int kok = heap[0], son = heap[--hn], i = 0;
    for (;;) { int c = 2 * i + 1; if (c >= hn) break; if (c + 1 < hn && kucuk(heap[c + 1], heap[c])) c++;
        if (!kucuk(heap[c], son)) break; heap[i] = heap[c]; i = c; }
    if (hn) heap[i] = son;
    return kok;
}

/* ACGOZLU ADIM: en kucuk iki frekansli agaci birlestir; tek agac kalana kadar */
static int agac_kur(const uint64_t *frek) {
    int n = 0; hn = 0;
    for (int c = 0; c < 256; c++) if (frek[c]) { d[n] = (Dugum){ frek[c], -1, -1, c }; heap_ekle(n++); }
    if (n == 1) { d[n] = (Dugum){ d[0].frekans, 0, -1, -1 }; return n; }   /* tek sembol: yine 1 bitlik kod */
    while (hn > 1) {
        int a = heap_cek(), b = heap_cek();
        d[n] = (Dugum){ d[a].frekans + d[b].frekans, a, b, -1 };
        heap_ekle(n++);
    }
    return heap_cek();
}

static uint64_t kod[256]; static int uzunluk[256];
static void kodlari_cikar(int v, uint64_t k, int u) {    /* soldan 0, sagdan 1 */
    if (v < 0) return;
    if (d[v].sol < 0 && d[v].sag < 0) { kod[d[v].sembol] = k; uzunluk[d[v].sembol] = u ? u : 1; return; }
    kodlari_cikar(d[v].sol, k << 1, u + 1);
    kodlari_cikar(d[v].sag, (k << 1) | 1, u + 1);
}

static void dene(const char *yol) {
    FILE *f = fopen(yol, "rb"); if (!f) { perror(yol); return; }
    fseek(f, 0, SEEK_END); size_t n = (size_t)ftell(f); rewind(f);
    unsigned char *v = malloc(n); if (fread(v, 1, n, f) != n) { fclose(f); return; } fclose(f);
    uint64_t frek[256] = { 0 }; for (size_t i = 0; i < n; i++) frek[v[i]]++;
    int kok = agac_kur(frek);
    memset(uzunluk, 0, sizeof uzunluk); kodlari_cikar(kok, 0, 0);
    double H = 0; uint64_t bit = 0; int farkli = 0, en_uzun = 0;
    for (int c = 0; c < 256; c++) if (frek[c]) { double p = (double)frek[c] / n; H -= p * log2(p); bit += frek[c] * uzunluk[c]; farkli++; if (uzunluk[c] > en_uzun) en_uzun = uzunluk[c]; }
    /* kodla */
    unsigned char *cikti = calloc(bit / 8 + 2, 1); uint64_t yaz = 0;
    for (size_t i = 0; i < n; i++) for (int b = uzunluk[v[i]] - 1; b >= 0; b--) { if (kod[v[i]] >> b & 1) cikti[yaz >> 3] |= (unsigned char)(0x80 >> (yaz & 7)); yaz++; }
    /* coz: agacta yuru */
    unsigned char *geri = malloc(n); uint64_t oku = 0;
    for (size_t i = 0; i < n; i++) {
        int x = kok;
        while (d[x].sol >= 0 || d[x].sag >= 0) { int b = cikti[oku >> 3] >> (7 - (oku & 7)) & 1; oku++; x = b ? d[x].sag : d[x].sol; }
        geri[i] = (unsigned char)d[x].sembol;
    }
    printf("%s: %zu bayt, %d farkli bayt, en uzun kod %d bit\n", yol, n, farkli, en_uzun);
    printf("  entropi %.3f bit/bayt, Huffman %.3f bit/bayt -> %llu bayt (%%%.1f), geri cozulen ayni mi: %s\n",
           H, (double)bit / n, (unsigned long long)((bit + 7) / 8), 100.0 * (bit + 7) / 8 / n, memcmp(v, geri, n) == 0 ? "evet" : "HAYIR");
    if (strstr(yol, "words")) for (const char *s = "e\nzq"; *s; s++) {
        unsigned char c = (unsigned char)*s; printf("  '%s' frekans %llu, kod ", c == '\n' ? "\\n" : (char[2]){ (char)c, 0 }, (unsigned long long)frek[c]);
        for (int b = uzunluk[c] - 1; b >= 0; b--) putchar('0' + (int)(kod[c] >> b & 1)); printf(" (%d bit)\n", uzunluk[c]);
    }
    free(v); free(cikti); free(geri);
}

int main(int argc, char **argv) { for (int i = 1; i < argc; i++) dene(argv[i]); }
```

**Neden doğru?** Açgözlü seçim özelliği yine bir değiştirme argümanıyla: optimal bir ağaçta en derin seviyede kardeş iki yaprak var. En düşük frekanslı iki sembol $x$, $y$ bu iki yaprakta değilse, onları oradaki sembollerle **yer değiştirmek** toplamı artıramıyor (düşük frekanslıyı daha derine, yüksek frekanslıyı daha sığa almak). Yani $x$ ve $y$'nin derin kardeşler olduğu bir optimal ağaç var; onları tek bir "$x + y$" sembolüne birleştirince problem bir sembol küçülüyor ve optimal alt yapı tümevarımı bitiriyor. (CLRS Lemma 16.2–16.3.)

### Ölçüm

Program her dosyayı okuyor, frekanslardan ağacı kuruyor, dosyayı bellekte bit bit **kodluyor**, sonra ağaçta yürüyerek **geri çözüyor** ve orijinalle karşılaştırıyor. Üç dosya: sözlük (Ders 8.13), programın kendi kaynağı ve bir ikili dosya (`/bin/ls`):

```
$ cc -std=c11 -O2 -Wall -Wextra huffman.c -o huffman -lm && ./huffman /usr/share/dict/words huffman.c /bin/ls
/usr/share/dict/words: 2493885 bayt, 54 farkli bayt, en uzun kod 16 bit
  entropi 4.327 bit/bayt, Huffman 4.361 bit/bayt -> 1359533 bayt (%54.5), geri cozulen ayni mi: evet
  'e' frekans 234497, kod 000 (3 bit)
  '\n' frekans 235976, kod 001 (3 bit)
  'z' frekans 8232, kod 01101001 (8 bit)
  'q' frekans 3657, kod 011010001 (9 bit)
huffman.c: 3976 bayt, 81 farkli bayt, en uzun kod 12 bit
  entropi 4.962 bit/bayt, Huffman 4.987 bit/bayt -> 2479 bayt (%62.4), geri cozulen ayni mi: evet
/bin/ls: 154208 bayt, 256 farkli bayt, en uzun kod 13 bit
  entropi 3.134 bit/bayt, Huffman 3.253 bit/bayt -> 62708 bayt (%40.7), geri cozulen ayni mi: evet
```

(Sanitizer'lı derleme temiz.) Sözlük dosyası %54.5'e iniyor: en sık iki bayt (`\n` ve `e`) 3 bitle, `q` 9 bitle kodlanıyor. Sözlükte sadece 54 farklı bayt var; 8 bit yerine ortalama 4.36.

**Entropi** (Claude Shannon, 1948): bir kaynağın her sembol için gereken en az ortalama bit sayısı, $H = -\sum_c p_c \log_2 p_c$, sembollerin birbirinden bağımsız olduğu modelde. Hiçbir önek-serbest kod $H$'nin altına inemez, ve Huffman kodunun ortalama uzunluğu $L$ her zaman $H \le L < H + 1$ aralığında. Burada $L - H$ sadece 0.03–0.12 bit. Huffman, sembol başına tam sayıda bit kullanmak zorunda olan kodlar arasında **optimal**. Daha iyisi ancak modeli değiştirerek mümkün: sembol başına kesirli bit (aritmetik kodlama), ya da bağımsızlık varsayımını bırakıp tekrar eden dizileri kullanmak (LZ77; gzip'in ilk aşaması, ikinci aşaması Huffman).

`/bin/ls` bir ikili dosya olduğu halde %40.7'ye iniyor: makine kodunda çok sayıda sıfır bayt ve tekrar eden komut kalıpları var. Faz 9 projesinde (Ders 9.24) bu programı, ağacı da dosyaya yazan ve gerçekten sıkıştırılmış bir dosya üreten bir araca çevireceğiz.

---

## Alıştırmalar

**1** – **Ağırlıklı aktivite seçimi**: her etkinliğin bir değeri var ve amaç toplam **değeri** en büyük çakışmasız kümeyi seçmek. "En erken biten" kuralı burada neden yanılır? Küçük bir karşı örnek ver. Bu problem nasıl çözülür?

**2** – **Kesirli sırt çantası**: kapasitesi $W$ olan bir çantaya ağırlıkları $w_i$, değerleri $v_i$ olan malzemeler koyuyorsun ve bir malzemenin **bir kısmını** alabilirsin. Açgözlü kural "değer/ağırlık oranı en yüksek olandan başla" optimal. Değiştirme argümanıyla göster. Malzemeler bölünemezse (0/1 sırt çantası) aynı kural neden yanılır?

**3** – Frekansları Fibonacci sayıları olan 10 sembol için ($1, 1, 2, 3, 5, 8, 13, 21, 34, 55$) Huffman ağacı nasıl görünür? En uzun kod kaç bit? Sözlükte en uzun kodun 16 bit çıkmasıyla ilgisi ne?

**4** – Huffman kodunun her zaman **tam** bir ikili ağaç (her iç düğümün tam iki çocuğu var) olduğunu göster. Önek-serbest ama tam olmayan bir kod neden asla optimal değildir?

**5** – Kodu çözen tarafın da ağaca ihtiyacı var; sıkıştırılmış dosyaya ağacı da yazmak gerekiyor. **Kanonik Huffman kodu**: sadece her sembolün **kod uzunluğunu** sakla, ve kodları uzunluklardan belirli bir kuralla yeniden üret. Kural ne olabilir? Bu, 256 sembollük bir alfabede ağacı saklamanın maliyetini kaç bayta indirir?

<details>
<summary>Cevaplar</summary>

**1** – Örnek: $[0, 10)$ değer 100, $[1, 2)$ değer 1, $[3, 4)$ değer 1. "En erken biten" ikisini seçip toplam 2 değer alıyor; optimal $[0, 10)$ tek başına, 100. Değiştirme argümanı çöküyor: en erken biteni optimal çözümdekiyle değiştirmek **sayıyı** korur ama **değeri** korumaz. Çözüm dinamik programlama (Ders 9.12): etkinlikleri bitiş zamanına göre sırala; $\text{opt}(i) = \max(\text{opt}(i-1),\; v_i + \text{opt}(p(i)))$, $p(i)$, $i$ ile çakışmayan son etkinlik (ikili aramayla bulunur). $O(n \log n)$.

**2** – Değiştirme: optimal bir çözüm oranı en yüksek $i$ malzemesinden alabileceğinin hepsini almıyorsa ve oranı daha düşük bir $j$'den bir miktar alıyorsa, $j$'den $\epsilon$ ağırlık çıkarıp yerine $i$'den $\epsilon$ ağırlık koymak değeri $\epsilon(v_i/w_i - v_j/w_j) \ge 0$ kadar artırıyor; çözümü kötüleştirmeden açgözlü seçimi içerecek hale getirdik. Bölünemezse: kapasite 50; malzemeler (ağırlık, değer): (10, 60), (20, 100), (30, 120); oranlar 6, 5, 4. Açgözlü önce 10'u, sonra 20'yi alıyor (toplam 30, değer 160), 30'luk sığmıyor. Optimal 20 + 30 = 50 ağırlık, değer 220. Kesirli sürümde açgözlü 10 + 20 + 30'un 2/3'ü, değer 240. 0/1 sırt çantası Ders 9.12'nin konusu ve NP-zor (Ders 9.22).

**3** – Fibonacci frekanslarında her adımda en küçük iki ağacın toplamı, bir sonraki en küçük frekansa eşit ya da ondan küçük oluyor ($F_1 + F_2 = F_3$, $F_1 + F_2 + F_3 = F_5 - 1 < F_4$...); her birleştirme şimdiye kadar birleşmiş bütün ağacı bir sonraki sembolle eşleştiriyor. Ağaç tamamen dengesiz bir **zincir**: en sık sembol 1 bit, en seyrek iki sembol 9 bit ($n - 1$). Genel olarak en uzun kod $n - 1$ bite kadar çıkabiliyor, ve bunun için frekansların Fibonacci gibi çok hızlı büyümesi gerekiyor. Sözlükteki 16 bitlik kod, dosyada çok az geçen birkaç bayt yüzünden: örneğin `-` sadece 2 kez geçiyor, büyük `Q` 77 kez; frekanslar 235 binden birkaç taneye kadar inince ağaç o yapraklara doğru uzuyor. Gerçek formatlar (DEFLATE: 15 bit, JPEG: 16 bit) en uzun kodu sınırlıyor; sınırı aşan durumlarda Huffman yerine uzunluk sınırlı optimal kodu bulan "package-merge" algoritması kullanılıyor.

**4** – Huffman her birleştirmede tam iki çocuklu bir düğüm yaratıyor; yapraklar dışındaki bütün düğümler böyle doğuyor. Tam olmayan bir kodda tek çocuklu bir iç düğüm var; o düğümü kaldırıp çocuğunu yerine çıkarmak, o alt ağaçtaki her kodu 1 bit kısaltıyor ve önek-serbestliği bozmuyor. Toplam uzunluk kesin azalıyor (alt ağaçta en az bir sembol varsa): tam olmayan kod optimal olamaz. Bu yüzden Kraft eşitsizliği (Ders 9.6, Alıştırma 3) Huffman kodları için eşitlikle sağlanıyor: $\sum 2^{-\ell_c} = 1$.

**5** – Kural: sembolleri önce kod uzunluğuna, eşitlikte sembol değerine göre sırala. İlk sembole uzunluğu kadar sıfırdan oluşan kodu ver; her sonraki sembolün kodu, bir öncekinin kodu + 1, ve uzunluk arttıysa sağa sıfır ekleyerek (sola kaydırarak) uzat. Bu, aynı uzunluklarla geçerli bir önek-serbest kod üretiyor ve her uzunluk dizisi için tek. Saklanan şey 256 sembolün uzunlukları: 4 bitle 15'e kadar uzunluk, 128 bayt; ya da sadece kullanılan sembollerin listesi ve uzunlukları. Bir ağacı pointer'larıyla saklamaktan çok daha küçük, ve çözücü kodları bir tablo olarak hızla yeniden kurabiliyor. DEFLATE (gzip, PNG, zip) ve JPEG kanonik Huffman kullanıyor; Ders 9.24'teki sıkıştırıcı da kullanacak.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 16: açgözlü algoritmalar, aktivite seçimi ve Huffman kodları.
- David Huffman, "A Method for the Construction of Minimum-Redundancy Codes", *Proceedings of the IRE* 40(9), 1952.
- Claude Shannon, "A Mathematical Theory of Communication", *Bell System Technical Journal* 27, 1948.
- Jon Kleinberg ve Éva Tardos, *Algorithm Design*, Bölüm 4: açgözlü algoritmalar ve değiştirme argümanları.
- David Pearson, "A polynomial-time algorithm for the change-making problem", *Operations Research Letters* 33(3), 2005.
- L. Peter Deutsch, RFC 1951, "DEFLATE Compressed Data Format Specification", 1996: kanonik Huffman kodları.

**Sıradaki ders:** Dinamik programlama 1. Memoization, Fibonacci ve en uzun ortak alt dizi (diff aracının temeli).
