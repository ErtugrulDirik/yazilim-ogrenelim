---
title: "9.24 Faz projesi: Huffman sıkıştırıcı ve diff"
description: "Faz 9'un iki algoritmasından iki gerçek komut satırı aracı: kanonik Huffman kodlarıyla dosya sıkıştıran ve açan huff (sadece kod uzunluklarını saklayan başlık, bit akışı, kod uzunluğu sınırı, bozuk dosyaların reddi), ve Myers'ın O((N + M)D) algoritmasıyla satır farkı bulup birleşik (unified) çıktı üreten fark; satır interning'i, kenar durumları (boş dosya, tek sembol, satır sonu olmayan son satır); patch ile uygulayıp 400 rastgele dosya çiftinde doğrulama ve LCS ile minimal değişiklik kontrolü; 236 bin satırlık sözlükte sistem diff -u ile bayt bayt aynı çıktı; gzip ile karşılaştırma ve tamamen farklı dosyalarda 3.6 GB bellekle ortaya çıkan sınır."
---

Faz 9 boyunca her algoritmayı ayrı bir derste, kendi küçük programıyla ölçtük. Bu proje ikisini, Ders 9.10'daki Huffman kodlamasını ve Ders 9.11'deki diff'i, gerçek araçlara çeviriyor: herhangi bir dosya üzerinde çalışan, hatalı girdiyi reddeden, testleri olan ve sistemdeki karşılıklarıyla (`gzip`, `diff`, `patch`) karşılaştırılabilen iki komut satırı programı. Bir algoritmayı bir araca dönüştürmenin işi büyük ölçüde **kenar durumlar** ve **dosya biçimi**; algoritmanın kendisi kodun küçük bir kısmı.

```
proje/
├── huff.c         Huffman sıkıştırıcı / açıcı
├── fark.c         Myers diff, birleşik çıktı
├── Makefile
├── test.sh        huff gidiş-dönüş testleri + test_fark.py
└── test_fark.py   rastgele dosya çiftleriyle fark testi
```

---

## 1. huff

Ders 9.10'daki program bir dosyayı **bellekte** kodlayıp geri çözüyordu. Bir sıkıştırıcının ek olarak çözen tarafa **kodları** da iletmesi gerekiyor. Ağacı pointer'larıyla yazmak yerine Ders 9.10'un Alıştırma 5'indeki **kanonik Huffman** yöntemi: sadece her sembolün **kod uzunluğu** saklanıyor; kodlar uzunluklardan, iki tarafta da aynı kuralla yeniden üretiliyor. Kural: sembolleri uzunluğa, eşitlikte sembol değerine göre sırala; ilk koda 0 ver; her sonraki kod bir öncekinin bir fazlası, uzunluk arttıkça sola kaydırılarak uzatılıyor. Bu, DEFLATE'in (gzip, zip, PNG) yöntemi.

Dosya biçimi:

| Bayt | İçerik |
| --- | --- |
| 0–3 | `HUF1` (sihirli sayı: yanlış dosyayı tanımak için) |
| 4–11 | Orijinal boyut, 64 bit, little endian (Ders 3.9) |
| 12–267 | 256 kod uzunluğu, sembol başına 1 bayt (0: kullanılmıyor) |
| 268– | Bit akışı, her baytta en anlamlı bit önce; son bayt sıfırla doldurulmuş |

```c
/* huff: Huffman sikistirici (Ders 9.10). Kanonik kodlar: dosyaya sadece kod uzunluklari yaziliyor.
   Bicim: "HUF1" | orijinal boyut (8 bayt, little endian) | 256 kod uzunlugu (1'er bayt) | bit akisi (MSB once)
   Kullanim: huff -c girdi cikti   |   huff -d girdi cikti */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define EN_UZUN 32                                       /* kod uzunlugu siniri (64 bitlik koda rahatca sigar) */

static unsigned char *dosya_oku(const char *yol, size_t *n) {
    FILE *f = fopen(yol, "rb"); if (!f) { perror(yol); exit(1); }
    size_t kap = 1 << 16, k = 0; unsigned char *b = malloc(kap); size_t r;
    while ((r = fread(b + k, 1, kap - k, f)) > 0) { k += r; if (k == kap) b = realloc(b, kap *= 2); }
    fclose(f); *n = k; return b;
}

/* ---- kod uzunluklari: Ders 9.10'un heap'li Huffman agaci ---- */
typedef struct { uint64_t f; int sol, sag; } Dugum;
static void uzunluklar(const uint64_t *frek, unsigned char *uz) {
    Dugum d[511]; int h[256], hn = 0, n = 0;
    memset(uz, 0, 256);
    #define KUCUK(a, b) (d[a].f < d[b].f || (d[a].f == d[b].f && a < b))     /* esitlikte numara: deterministik */
    for (int c = 0; c < 256; c++) if (frek[c]) {
        d[n] = (Dugum){ frek[c], -1 - c, 0 };                            /* yaprak: sol = -1 - sembol */
        int i = hn++; while (i > 0 && KUCUK(n, h[(i - 1) / 2])) { h[i] = h[(i - 1) / 2]; i = (i - 1) / 2; } h[i] = n++; }
    if (n == 0) return;
    if (n == 1) { uz[-1 - d[0].sol] = 1; return; }                       /* tek sembol: 1 bitlik kod */
    while (hn > 1) {
        int ab[2];
        for (int k = 0; k < 2; k++) { ab[k] = h[0]; int son = h[--hn], i = 0;
            for (;;) { int c = 2 * i + 1; if (c >= hn) break; if (c + 1 < hn && KUCUK(h[c + 1], h[c])) c++; if (!KUCUK(h[c], son)) break; h[i] = h[c]; i = c; }
            if (hn) h[i] = son; }
        d[n] = (Dugum){ d[ab[0]].f + d[ab[1]].f, ab[0], ab[1] };
        int i = hn++; while (i > 0 && KUCUK(n, h[(i - 1) / 2])) { h[i] = h[(i - 1) / 2]; i = (i - 1) / 2; } h[i] = n++;
    }
    int yig[512], der[512], tp = 0; yig[tp] = h[0]; der[tp++] = 0;     /* agacta gezin, derinlik = kod uzunlugu */
    while (tp) { int v = yig[--tp], dr = der[tp];
        if (d[v].sol < 0) uz[-1 - d[v].sol] = (unsigned char)dr;
        else { yig[tp] = d[v].sol; der[tp++] = dr + 1; yig[tp] = d[v].sag; der[tp++] = dr + 1; } }
}

/* ---- kanonik kodlar (Ders 9.10 Al. 5): uzunluga, sonra sembole gore sirala; ardisik numaralar ver ---- */
static void kanonik(const unsigned char *uz, uint64_t *kod) {
    int say[EN_UZUN + 2] = { 0 }; uint64_t sonraki[EN_UZUN + 2] = { 0 }, c = 0;
    for (int s = 0; s < 256; s++) say[uz[s]]++;
    say[0] = 0;
    for (int L = 1; L <= EN_UZUN + 1; L++) { c = (c + (uint64_t)say[L - 1]) << 1; sonraki[L] = c; }
    for (int s = 0; s < 256; s++) if (uz[s]) kod[s] = sonraki[uz[s]]++;
}

static int sikistir(const char *gy, const char *cy) {
    size_t n; unsigned char *v = dosya_oku(gy, &n);
    uint64_t frek[256] = { 0 }; for (size_t i = 0; i < n; i++) frek[v[i]]++;
    unsigned char uz[256]; uzunluklar(frek, uz);
    for (int s = 0; s < 256; s++) if (uz[s] > EN_UZUN) {                 /* cok carpik dagilim: frekanslari sikistirip tekrar */
        for (int k = 0; k < 256; k++) if (frek[k]) frek[k] = (frek[k] >> 4) | 1;
        uzunluklar(frek, uz); s = -1; }
    uint64_t kod[256]; kanonik(uz, kod);
    FILE *f = fopen(cy, "wb"); if (!f) { perror(cy); return 1; }
    fwrite("HUF1", 1, 4, f);
    for (int i = 0; i < 8; i++) fputc((int)((uint64_t)n >> (8 * i) & 0xff), f);
    fwrite(uz, 1, 256, f);
    unsigned acc = 0; int nb = 0;                                         /* bit biriktirici */
    for (size_t i = 0; i < n; i++) {
        int L = uz[v[i]]; uint64_t k = kod[v[i]];
        for (int b = L - 1; b >= 0; b--) { acc = (acc << 1) | (unsigned)(k >> b & 1); if (++nb == 8) { fputc((int)acc, f); acc = 0; nb = 0; } }
    }
    if (nb) fputc((int)(acc << (8 - nb)), f);                             /* son bayti sifirla doldur */
    fclose(f); free(v); return 0;
}

static int ac(const char *gy, const char *cy) {
    size_t n; unsigned char *v = dosya_oku(gy, &n);
    if (n < 268 || memcmp(v, "HUF1", 4)) { fprintf(stderr, "%s: HUF1 dosyasi degil\n", gy); return 1; }
    uint64_t boy = 0; for (int i = 0; i < 8; i++) boy |= (uint64_t)v[4 + i] << (8 * i);
    const unsigned char *uz = v + 12;
    /* kanonik cozme tablolari: her uzunluk icin ilk kod ve o uzunluktaki semboller (sirali) */
    int say[EN_UZUN + 2] = { 0 }, ilk_indeks[EN_UZUN + 2], sembol[256], k = 0; uint64_t ilk_kod[EN_UZUN + 2], c = 0;
    for (int s = 0; s < 256; s++) if (uz[s] > EN_UZUN) { fprintf(stderr, "bozuk uzunluk\n"); return 1; } else say[uz[s]]++;
    say[0] = 0;
    for (int L = 1; L <= EN_UZUN; L++) { c = (c + (uint64_t)say[L - 1]) << 1; ilk_kod[L] = c; ilk_indeks[L] = k; for (int s = 0; s < 256; s++) if (uz[s] == L) sembol[k++] = s; }
    FILE *f = fopen(cy, "wb"); if (!f) { perror(cy); return 1; }
    size_t bit = 0, toplam_bit = (n - 268) * 8;
    for (uint64_t i = 0; i < boy; i++) {
        uint64_t kd = 0; int L = 0;
        for (;;) {
            if (bit >= toplam_bit) { fprintf(stderr, "beklenmedik dosya sonu\n"); fclose(f); return 1; }
            kd = (kd << 1) | (uint64_t)(v[268 + bit / 8] >> (7 - bit % 8) & 1); bit++; L++;
            if (L > EN_UZUN) { fprintf(stderr, "bozuk veri\n"); fclose(f); return 1; }
            if (say[L] && kd - ilk_kod[L] < (uint64_t)say[L]) { fputc(sembol[ilk_indeks[L] + (int)(kd - ilk_kod[L])], f); break; }
        }
    }
    fclose(f); free(v); return 0;
}

int main(int argc, char **argv) {
    if (argc == 4 && !strcmp(argv[1], "-c")) return sikistir(argv[2], argv[3]);
    if (argc == 4 && !strcmp(argv[1], "-d")) return ac(argv[2], argv[3]);
    fprintf(stderr, "kullanim: %s -c|-d girdi cikti\n", argv[0]); return 2;
}
```

Ayrıntılar:

- **Ağaç**, Ders 9.10'daki heap'li Huffman; eşit frekanslarda düğüm numarasına bakan karşılaştırma (`KUCUK`), aynı dosyanın her seferinde **aynı** çıktıyı vermesini sağlıyor (deterministik çıktı; Ders 9.15'in Alıştırma 4'ü).
- **Kod uzunluğu sınırı**: çok çarpık frekanslarda (Fibonacci benzeri; Ders 9.10, Alıştırma 3) kodlar 32 biti aşabilir. O zaman frekanslar 16'ya bölünüp (sıfır olmasın diye `| 1`) ağaç yeniden kuruluyor: optimal değil ama sınırlı. Gerçek biçimler daha düşük sınır (DEFLATE'te 15) ve optimal "package-merge" algoritması kullanıyor.
- **Çözme**, bit bit: o ana kadar okunan bitler $L$ uzunluğundaki kodların aralığına (`ilk_kod[L]`'den itibaren `say[L]` tane) düşüyorsa bir sembol bulunmuş. Kanonik kodların bu aralık yapısı, ağacı hiç kurmadan çözmeyi mümkün kılıyor.
- **Bozuk girdi**: sihirli sayı, uzunlukların sınırı ve bit akışının erken bitmesi kontrol ediliyor; hiçbiri dizi dışı bir okumaya yol açmıyor (sanitizer'lı testte bir kesik dosya bilerek açılıyor).

---

## 2. fark

Ders 9.11'deki diff, $O(NM)$ bir LCS tablosu kuruyordu: 236 bin satırlık iki dosya için 55 milyar hücre. Gerçek `diff` ve `git diff`, Eugene Myers'ın (1986) algoritmasını kullanıyor, ve fikri Ders 9.11'in tablosunu bir **graf** olarak düşünmek: $(x, y)$ noktaları, sağa adım bir satır silme, aşağı adım bir satır ekleme, ve $A_x = B_y$ ise **köşegen** adım bedava. En az değişiklikli düzenleme, $(0,0)$'dan $(N, M)$'ye en az sağa ve aşağı adımlı yol: Ders 9.14'teki BFS'in bir hali, ama köşegen adımların bedava olduğu.

Myers'ın gözlemi: $d$ değişiklikle ulaşılabilen noktalar sadece $k = x - y \in [-d, d]$ köşegenlerinde, ve her köşegende sadece **en uzağa** ulaşan nokta önemli. $V[k]$, $d$ değişiklikle $k$ köşegeninde ulaşılan en büyük $x$; $d$'den $d+1$'e geçmek her köşegen için bir adım (sağa ya da aşağı) artı gidebildiği kadar köşegen ("yılan", snake). Toplam $O((N + M) D)$; $D$, değişiklik sayısı. Dosyalar az farklıysa neredeyse doğrusal.

```c
/* fark: satir tabanli diff, Myers'in O((N+M)D) algoritmasi; birlesik (unified) cikti, 3 satir baglam.
   Kullanim: fark eski yeni   (cikis kodu: 0 ayni, 1 farkli, 2 hata) */
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { char **s; size_t *uz; int n; } Satirlar;

static Satirlar oku(const char *yol) {
    FILE *f = fopen(yol, "r"); if (!f) { perror(yol); exit(2); }
    Satirlar d = { NULL, NULL, 0 }; int kap = 0; char *b = NULL; size_t bk = 0; ssize_t r;
    while ((r = getline(&b, &bk, f)) >= 0) {
        if (d.n == kap) { kap = kap ? 2 * kap : 1024; d.s = realloc(d.s, kap * sizeof *d.s); d.uz = realloc(d.uz, kap * sizeof *d.uz); }
        d.s[d.n] = malloc(r + 1); memcpy(d.s[d.n], b, r + 1); d.uz[d.n++] = (size_t)r;
    }
    free(b); fclose(f); return d;
}

/* Her satira bir kimlik numarasi: esit satirlar = esit numaralar (Ders 8.14 / 8.16'nin interning'i). Sonra sadece tamsayi karsilastirmasi. */
static int *kimlik_ver(Satirlar *a, Satirlar *b) {
    int toplam = a->n + b->n, kap = 1; while (kap < 2 * toplam + 2) kap <<= 1;
    int *tablo = malloc(kap * sizeof *tablo), *id = malloc((toplam ? toplam : 1) * sizeof *id), sonraki = 0;
    for (int i = 0; i < kap; i++) tablo[i] = -1;
    for (int k = 0; k < toplam; k++) {
        const char *s = k < a->n ? a->s[k] : b->s[k - a->n]; size_t u = k < a->n ? a->uz[k] : b->uz[k - a->n];
        uint64_t h = 1469598103934665603ull; for (size_t i = 0; i < u; i++) { h ^= (unsigned char)s[i]; h *= 1099511628211ull; }
        size_t j = (size_t)(h ^ (h >> 29)) & (kap - 1);
        for (;;) {                                                   /* dogrusal sondalama (Ders 8.15); tablo[j]: bir temsilci satir */
            if (tablo[j] < 0) { tablo[j] = k; id[k] = sonraki++; break; }
            int t = tablo[j]; const char *ts = t < a->n ? a->s[t] : b->s[t - a->n]; size_t tu = t < a->n ? a->uz[t] : b->uz[t - a->n];
            if (tu == u && memcmp(ts, s, u) == 0) { id[k] = id[t]; break; }
            j = (j + 1) & (kap - 1);
        }
    }
    free(tablo); return id;
}

/* MYERS: d. adimda, her kosegen k = x - y icin V[k] = ulasilabilen en uzak x. Her d icin V'nin kopyasi saklanir (geri izleme). */
enum { AYNI, SIL, EKLE };
static int myers(const int *A, int N, const int *B, int M, unsigned char **ops_, int *n_ops, int *D_) {
    int MAX = N + M, ofs = MAX + 1;
    int *V = calloc(2 * MAX + 3, sizeof *V);
    int **iz = malloc((MAX + 1) * sizeof *iz); int D = -1;
    for (int d = 0; d <= MAX; d++) {
        iz[d] = malloc((2 * d + 1) * sizeof(int));                   /* sadece [-d, d] araligi: toplam O(D^2) bellek */
        for (int k = -d; k <= d; k += 2) {
            int x;
            if (k == -d || (k != d && V[ofs + k - 1] < V[ofs + k + 1])) x = V[ofs + k + 1];   /* asagi: ekleme */
            else x = V[ofs + k - 1] + 1;                                                     /* saga: silme */
            int y = x - k;
            while (x < N && y < M && A[x] == B[y]) { x++; y++; }                           /* kosegen: ayni satirlar, bedava */
            V[ofs + k] = x;
            if (x >= N && y >= M) { D = d; break; }
        }
        for (int k = -d; k <= d; k++) iz[d][k + d] = V[ofs + k];
        if (D >= 0) break;
    }
    /* geri izle: (N, M)'den (0, 0)'a */
    unsigned char *ops = malloc(N + M + 1); int no = 0, x = N, y = M;
    for (int d = D; d > 0; d--) {
        int k = x - y; const int *Vp = iz[d - 1];                    /* Vp[k + (d-1)]: onceki adim */
        int asagi = (k == -d || (k != d && Vp[k - 1 + d - 1] < Vp[k + 1 + d - 1]));
        int pk = asagi ? k + 1 : k - 1, px = Vp[pk + d - 1], py = px - pk;
        while (x > px + (asagi ? 0 : 1) && y > py + (asagi ? 1 : 0)) { ops[no++] = AYNI; x--; y--; }
        if (asagi) { ops[no++] = EKLE; y--; } else { ops[no++] = SIL; x--; }
    }
    while (x > 0 && y > 0) { ops[no++] = AYNI; x--; y--; }
    for (int i = 0; i < no / 2; i++) { unsigned char t = ops[i]; ops[i] = ops[no - 1 - i]; ops[no - 1 - i] = t; }   /* ters cevir */
    for (int d = 0; d <= D; d++) free(iz[d]);
    free(iz); free(V);
    *ops_ = ops; *n_ops = no; *D_ = D;
    return D;
}

static void aralik(int bas, int adet) {                              /* diff -u'nun "bas,adet" yazimi */
    if (adet == 0) printf("%d,0", bas); else if (adet == 1) printf("%d", bas + 1); else printf("%d,%d", bas + 1, adet);
}
static void satir_yaz(char on, const char *s, size_t u) {
    putchar(on); fwrite(s, 1, u, stdout);
    if (u == 0 || s[u - 1] != '\n') printf("\n\\ No newline at end of file\n");
}

int main(int argc, char **argv) {
    if (argc != 3) { fprintf(stderr, "kullanim: %s eski yeni\n", argv[0]); return 2; }
    Satirlar a = oku(argv[1]), b = oku(argv[2]);
    int *id = kimlik_ver(&a, &b), no, D;
    unsigned char *ops;
    myers(id, a.n, id + a.n, b.n, &ops, &no, &D);
    if (D == 0) return 0;
    printf("--- %s\n+++ %s\n", argv[1], argv[2]);
    const int C = 3;                                                 /* baglam satiri */
    int i = 0, ax = 0, by = 0;                                       /* ops'ta konum, eski ve yeni satir sayaclari */
    while (i < no) {
        while (i < no && ops[i] == AYNI) { i++; ax++; by++; }       /* bir sonraki degisikligi bul */
        if (i == no) break;
        int bas = i, bas_x = ax, bas_y = by, son = i, sx = ax, sy = by;
        int j = i, jx = ax, jy = by;
        for (;;) {                                                   /* degisiklik bloklarini, aralarinda <= 2C ayni satir varsa birlestir */
            while (j < no && ops[j] != AYNI) { if (ops[j] == SIL) jx++; else jy++; j++; }
            son = j; sx = jx; sy = jy;
            int k = j, kx = jx, ky = jy; while (k < no && ops[k] == AYNI && k - j < 2 * C + 1) { k++; kx++; ky++; }
            if (k < no && ops[k] != AYNI && k - j <= 2 * C) { j = k; jx = kx; jy = ky; } else break;
        }
        int on = bas_x < C ? bas_x : C;                              /* onceki baglam */
        int sonra = 0; { int k = son; while (k < no && ops[k] == AYNI && sonra < C) { k++; sonra++; } }
        int ex = bas_x - on, ey = bas_y - on;
        printf("@@ -"); aralik(ex, (sx - bas_x) + on + sonra); printf(" +"); aralik(ey, (sy - bas_y) + on + sonra); printf(" @@\n");
        for (int t = 0; t < on; t++) satir_yaz(' ', a.s[ex + t], a.uz[ex + t]);
        int x = bas_x, y = bas_y;
        for (int t = bas; t < son; t++) {
            if (ops[t] == AYNI) { satir_yaz(' ', a.s[x], a.uz[x]); x++; y++; }
            else if (ops[t] == SIL) { satir_yaz('-', a.s[x], a.uz[x]); x++; }
            else { satir_yaz('+', b.s[y], b.uz[y]); y++; }
        }
        for (int t = 0; t < sonra; t++) satir_yaz(' ', a.s[x + t], a.uz[x + t]);
        i = son; ax = sx; by = sy;
    }
    fflush(stdout);
    fprintf(stderr, "%d degisiklik (silme + ekleme)\n", D);
    return 1;
}
```

Ayrıntılar:

- **Satır kimlikleri**: satırlar her karşılaştırmada `strcmp`'lenmek yerine bir kez hash'lenip (Ders 8.13'ün FNV-1a'sı, Ders 8.15'in doğrusal sondalaması) **eşit satırlar eşit tamsayılar** olacak şekilde numaralanıyor (Ders 8.16'nın interning fikri). Myers'ın iç döngüsü sadece tamsayı karşılaştırıyor.
- **Geri izleme**: her $d$ için $V$'nin $[-d, d]$ dilimi saklanıyor (toplam $O(D^2)$ bellek), sonra $(N, M)$'den geriye her adımda hangi köşegenden gelindiği bulunuyor.
- **Birleşik çıktı**: değişiklik blokları, aralarında en fazla 6 aynı satır varsa tek bir **hunk**'ta birleştiriliyor, her hunk'ın önünde ve arkasında 3 satır bağlam; `@@ -eski,adet +yeni,adet @@` başlıkları `diff -u`'nun kurallarıyla (adet 1 ise yazılmıyor, 0 ise başlangıç bir önceki satır). Son satırda satır sonu yoksa `\ No newline at end of file`.
- Eşitlikte önce **silme**: `diff -u` gibi, değiştirilen bir satırın eski hali yenisinden önce.

---

## 3. Derleme ve testler

```make
CC     = cc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -O2
SAN    = -std=c11 -Wall -Wextra -O1 -g -fsanitize=address,undefined

all: huff fark

huff: huff.c
	$(CC) $(CFLAGS) huff.c -o huff
fark: fark.c
	$(CC) $(CFLAGS) fark.c -o fark

test: huff.c fark.c test.sh test_fark.py
	$(CC) $(SAN) huff.c -o huff
	$(CC) $(SAN) fark.c -o fark
	sh test.sh

clean:
	rm -f huff fark ta tb tc t.patch *.huf *.cikti bos tek

.PHONY: all test clean
```

```sh
#!/bin/sh
# huff: sikistir + ac, orijinalle karsilastir. fark: rastgele dosya ciftleri (test_fark.py).
set -e
: > bos; printf 'aaaaaaaaaa' > tek
for f in bos tek huff.c fark.c /usr/share/dict/words /bin/ls; do
    ./huff -c "$f" t.huf
    ./huff -d t.huf t.cikti
    if cmp -s "$f" t.cikti; then
        echo "huff: $f  $(wc -c < "$f" | tr -d ' ') -> $(wc -c < t.huf | tr -d ' ') bayt, geri acilan ayni"
    else
        echo "huff: $f  HATA"; exit 1
    fi
done
head -c 300 t.huf > kesik.huf
if ./huff -d kesik.huf t.cikti 2>/dev/null; then echo "huff: kesik dosyayi kabul etti: HATA"; exit 1; else echo "huff: kesik dosya reddedildi"; fi
python3 -I test_fark.py 7
```

```python
# Rastgele dosya ciftleri: fark'in ciktisini patch ile eskiye uygula, yeniyle karsilastir;
# degisiklik sayisini LCS ile hesaplanan en kucuk sayiyla karsilastir.
import random, subprocess, sys
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
def lcs(a, b):
    n, m = len(a), len(b); L = [[0]*(m+1) for _ in range(n+1)]
    for i in range(n-1, -1, -1):
        for j in range(m-1, -1, -1):
            L[i][j] = L[i+1][j+1]+1 if a[i] == b[j] else max(L[i+1][j], L[i][j+1])
    return L[0][0]
hata = 0; T = 400
for t in range(T):
    n = random.randint(0, 40); alf = random.randint(1, 6)
    a = [chr(97 + random.randrange(alf)) + "\n" for _ in range(n)]
    b = list(a)
    for _ in range(random.randint(0, 8)):
        r = random.random()
        if r < 0.4 and b: del b[random.randrange(len(b))]
        elif r < 0.8: b.insert(random.randint(0, len(b)), chr(97 + random.randrange(alf)) + "\n")
        elif b: b[random.randrange(len(b))] = "x\n"
    if random.random() < 0.2 and b: b[-1] = b[-1].rstrip("\n")          # son satirda satir sonu yok
    open("ta", "w").write("".join(a)); open("tb", "w").write("".join(b))
    p = subprocess.run(["./fark", "ta", "tb"], capture_output=True, text=True)
    D = int(p.stderr.split()[0]) if p.returncode == 1 else 0
    if D != len(a) + len(b) - 2 * lcs(a, b): hata += 1; print("D yanlis", t)
    open("tc", "w").write("".join(a))
    if p.returncode == 1:
        open("t.patch", "w").write(p.stdout)
        q = subprocess.run(["patch", "-s", "tc", "t.patch"], capture_output=True, text=True)
        if q.returncode != 0: hata += 1; print("patch basarisiz", t, q.stdout, q.stderr); break
    if open("tc").read() != open("tb").read(): hata += 1; print("sonuc farkli", t); break
print(f"{T} rastgele dosya cifti: {hata} hata (patch ile uygulama + en kucuk degisiklik sayisi)")
```

`test_fark.py`'nin her turu: küçük bir alfabeyle rastgele bir dosya, ona rastgele silme/ekleme/değiştirme uygulanmış ikinci bir dosya (bazen son satırı satır sonusuz). İki kontrol:

1. **Doğruluk**: `fark`'ın çıktısı sistemdeki `patch` ile eski dosyaya uygulanıyor; sonuç yeni dosyayla aynı olmalı. Bu, çıktının hem içerik hem biçim olarak doğru olduğunu, bağımsız bir programla test ediyor.
2. **En küçüklük**: `fark`'ın raporladığı değişiklik sayısı, Ders 9.11'in LCS tablosuyla (Python'da, ayrıca) hesaplanan $N + M - 2 \cdot \text{LCS}$'ye eşit olmalı (Ders 9.11, Alıştırma 3). Myers en kısa yolu buluyor; bulmasaydı bu kontrol yakalardı.

`make test` iki aracı sanitizer'larla derleyip (bu yüzden ikili dosyaların üzerine yazıyor; normal derleme için `make clean all`) bütün testleri çalıştırıyor:

```
$ make test
cc -std=c11 -Wall -Wextra -O1 -g -fsanitize=address,undefined huff.c -o huff
cc -std=c11 -Wall -Wextra -O1 -g -fsanitize=address,undefined fark.c -o fark
sh test.sh
huff: bos  0 -> 268 bayt, geri acilan ayni
huff: tek  10 -> 270 bayt, geri acilan ayni
huff: huff.c  5912 -> 3894 bayt, geri acilan ayni
huff: fark.c  6927 -> 4345 bayt, geri acilan ayni
huff: /usr/share/dict/words  2493885 -> 1359801 bayt, geri acilan ayni
huff: /bin/ls  154208 -> 62976 bayt, geri acilan ayni
huff: kesik dosya reddedildi
400 rastgele dosya cifti: 0 hata (patch ile uygulama + en kucuk degisiklik sayisi)
```

Sözlük dosyası 1 359 801 bayta iniyor: Ders 9.10'da bellekte hesapladığımız 1 359 533 bayt + 268 baytlık başlık, bayt bayt. Boş dosya sadece başlık; on tane `a` 1 bitlik kodla 2 bayt.

Bir de kod uzunluğu sınırının tetiklendiği yapay bir dosya: 36 sembol, frekansları Fibonacci sayıları (39 milyon bayt). Ham Huffman ağacı 35 bit derinliğe iniyor; sınırlama sonrası en uzun kod 17 bit, dosya 39 088 168 bayttan 12 792 038 bayta iniyor ve geri açılınca aynı. Tamamen rastgele 1 MB'lık bir dosya ise 1 048 576 bayttan 1 048 844'e **büyüyor**: her bayt eşit olasılıklı, entropi 8 bit (Ders 9.10), ve sıkıştırılacak bir şey yok; başlık kadar kayıp.

---

## 4. Karşılaştırma

**huff ve gzip** (`gzip -9`):

| Dosya | Orijinal | huff | gzip -9 |
| --- | --- | --- | --- |
| `/usr/share/dict/words` | 2 493 885 | 1 359 801 (%54.5) | 754 295 (%30.2) |
| `/bin/ls` | 154 208 | 62 976 (%40.8) | 33 659 (%21.8) |

gzip yaklaşık iki kat daha iyi sıkıştırıyor. Fark algoritmada değil **modelde**: Huffman her baytı bağımsız sayıyor (sıfırıncı mertebe model, Ders 9.10'daki entropi sınırı), gzip'in DEFLATE'i önce **LZ77** ile tekrar eden dizileri ("ion\n", "ness\n") önceki geçişlerine geri referanslarla değiştiriyor, sonra o referansları ve kalan baytları Huffman ile kodluyor. Huffman, hemen her sıkıştırıcının son aşaması; tek başına değil. Hız: huff sözlüğü 0.04 s'de sıkıştırıp 0.07 s'de açıyor (bit bit çözme; tablo tabanlı çözme birkaç kat hızlandırır, Alıştırma 2).

**fark ve diff**: 236 bin satırlık sözlük dosyasında rastgele 5, 50 ve 500 satır değiştirildi (her değişiklik bir silme + bir ekleme, $D$ = 10, 100, 1000):

```
D=10: 10 degisiklik (silme + ekleme), sure real 0.05
   sistem diff: real 0.04, satir sayisi fark=      47 diff=      47
   patch: ayni
D=100: 100 degisiklik (silme + ekleme), sure real 0.04
   sistem diff: real 0.05, satir sayisi fark=     452 diff=     452
   patch: ayni
D=1000: 1000 degisiklik (silme + ekleme), sure real 0.04
   sistem diff: real 0.07, satir sayisi fark=    4479 diff=    4479
   patch: ayni
```

Ve çıktılar, ilk iki başlık satırı (dosya adları ve tarihler) dışında, sistemdeki `diff -u`'nunkiyle **bayt bayt aynı**:

```
D=10: sistem diff -u ile bayt bayt ayni (baslik haric)
D=100: sistem diff -u ile bayt bayt ayni (baslik haric)
D=1000: sistem diff -u ile bayt bayt ayni (baslik haric)
```

Süre 40–50 ms, sistem `diff` ile aynı mertebede; çoğu dosyayı okumak ve satırları hash'lemek. Ders 9.11'in $O(NM)$ tablosu burada 220 GB olurdu.

### Sınır

İki dosya **tamamen** farklıysa (20 000 satıra karşı tamamen başka 20 000 satır, $D = 40\,000$):

```
40000 degisiklik (silme + ekleme)
        2.65 real         1.70 user         0.77 sys
          3649716224  maximum resident set size
```

2.7 s ve **3.6 GB** bellek: saklanan $V$ dilimlerinin toplamı $(D+1)^2$ tamsayı. Sistem `diff` aynı dosyaları 0.11 s'de karşılaştırıyor. Myers'ın makalesindeki **doğrusal bellekli** sürüm (en kısa yolun ortasındaki "orta yılanı" iki yönden arayıp problemi ikiye bölmek; Ders 9.11, Alıştırma 1'deki Hirschberg fikri) bu belleği $O(N + M)$'ye indiriyor; gerçek diff araçları ayrıca $D$ çok büyüdüğünde arama maliyetini sınırlayan sezgisel kesmeler kullanıyor (Alıştırma 4).

---

## 5. Faz 9'a dönüp bakış

| Teknik | Dersler | Bu projede |
| --- | --- | --- |
| Döngü değişmezi, ölçüm | 9.1 | Testler: bağımsız doğrulama (patch, LCS) |
| Arama, sıralama | 9.2–9.8 | Kanonik kodlar için sembolleri sıralamak |
| String eşleme | 9.9 | — (satırlar hash'le eşleştiriliyor) |
| Açgözlü | 9.10 | Huffman ağacı |
| Dinamik programlama | 9.11–9.13 | LCS (test kontrolü), Myers'ın köşegen DP'si |
| Graf algoritmaları | 9.14–9.21 | Myers: düzenleme grafında BFS benzeri arama |
| NP-zorluk, sezgisel | 9.22–9.23 | Kod uzunluğu sınırlamada yaklaşık çözüm |

Fazın tekrar eden dersi, Faz 8'inkinin tamamlayıcısı. Faz 8'de veri yapısının **bellek düzeni** performansı belirliyordu; Faz 9'da çoğu zaman **doğru algoritma** belirledi: $O(NM)$'den $O((N+M)D)$'ye geçmek, aynı makinede 220 GB'lık bir tabloyu 40 milisaniyelik bir işe çevirdi. Ama her ölçümde de iki şey görüldü. Birincisi, asimptotik analizin sabitleri ve varsayımları (rastgele grafta Bellman–Ford'un 18 tur sürmesi, Ders 9.17; hızlı sıralamanın tekrarlı anahtarlarda çökmesi, Ders 9.5) gerçekte çok önemli. İkincisi, en iyi algoritmanın bile bir **en kötü durumu** var (Myers'ın 3.6 GB'ı), ve bir aracı gerçek hale getiren şey o durumu bilmek ve ele almak.

---

## Alıştırmalar

**1** – huff'ın başlığı 256 bayt kod uzunluğu saklıyor. Kod uzunlukları en fazla 32 olduğu için her biri 5 bitte saklanabilir; çoğu dosyada kullanılmayan sembollerin uzunluğu 0 ve arka arkaya geliyor. Başlığı küçültmenin iki yolunu öner. DEFLATE bunu nasıl yapıyor?

**2** – Çözme, her bit için bir döngü turu. **Tablo tabanlı** çözme: sonraki $k = 10$ biti tek seferde oku, $2^{10}$ girdilik bir tablodan "bu bitlerle başlayan kodun sembolü ve uzunluğu"nu bul. Uzunluğu 10'dan büyük kodlar için ne yaparsın? Tahminen ne kadar hızlanır?

**3** – fark, satır sonu karakterlerini satırın parçası sayıyor: `"a\n"` ile `"a"` farklı satırlar. `diff -w` (boşlukları yok say) ve `diff -i` (büyük/küçük harf) seçeneklerini nasıl eklersin? Değişiklik sadece hangi fonksiyonda olur?

**4** – fark'ın bellek sınırını önlemenin en basit yolu: $D$ bir eşiği (örneğin 10 000) aşarsa aramayı bırakıp "dosyalar çok farklı" demek ya da kalan kısmı tek bir büyük hunk olarak yazmak. Bu, çıktının **minimal** olma garantisini nasıl etkiler? Doğruluğunu (patch ile uygulanabilirliğini) korur mu?

**5** – `git diff --patience` ve `--histogram` seçenekleri, Myers'tan farklı (minimal olmayabilen) ama "insan için daha okunaklı" fark üretiyor: önce her iki dosyada da **tam bir kez** geçen satırları eşleştir, aradaki bölgeleri özyinelemeyle işle. Neden daha okunaklı olabilir? Ders 9.11'in Alıştırma 2'sindeki en uzun artan alt dizi bu yöntemin neresinde?

<details>
<summary>Cevaplar</summary>

**1** – (a) Her uzunluğu 5 bitte paketle: 256 × 5 = 160 bayt. (b) Sadece kullanılan sembolleri yaz: sembol sayısı, sonra her biri için (sembol, uzunluk) çiftleri; sözlük dosyasında 54 sembol × 2 bayt = 108 bayt. (c) Uzunluk dizisini **koşu uzunluğu** (run-length) ile kodla: "şu kadar sıfır", "şu değer şu kadar tekrar". DEFLATE (RFC 1951) üçüncüsünü yapıyor ve bir adım daha atıyor: kod uzunlukları dizisinin kendisi, 19 sembollü ayrı bir Huffman koduyla (0–15 uzunlukları ve tekrar kodları 16, 17, 18) sıkıştırılıyor; o küçük kodun uzunlukları da 3'er bitle yazılıyor. Küçük dosyalarda başlık toplam boyutun önemli bir kısmı, bu yüzden bu tür sıkıştırma önemli.

**2** – $k$ bit "göz at" (peek); `tablo[bitler]` = (sembol, uzunluk); uzunluk kadar bit tüket. Kanonik kodlarla tablo, her kod için $2^{k - L}$ girdi doldurularak (kodun arkasına gelebilecek her bit kombinasyonu) kuruluyor. $L > k$ kodlar için tabloya "uzun kod" işareti koy ve o durumda bit bit çözmeye ya da ikinci seviye bir tabloya geç; uzun kodlar seyrek olduğu için (en seyrek semboller) bu yavaş yol nadiren çalışıyor. Bit bit çözme sembol başına ortalama 4–5 döngü turu ve her turda tahmin edilemeyen bir dal; tablo tek bir bellek erişimi. zlib'in `inflate`'i bu yöntemle; hızlanma tipik olarak 3–5 kat.

**3** – Sadece `kimlik_ver` değişiyor: hash'lenmeden ve karşılaştırılmadan önce satır **normalleştiriliyor** (`-w` için boşluklar atlanıyor, `-i` için her karakter küçük harfe çevrilerek hash'leniyor ve karşılaştırılıyor). Myers ve çıktı kodu kimlik numaralarına bakıyor; normalleştirilmiş eşit satırlar aynı numarayı alınca onları "aynı" sayar. Ama çıktıda satırın **orijinal** hali yazılmalı (`a.s[x]` ve `b.s[y]` zaten orijinal); ve iki dosyanın "aynı" sayılan satırları farklı göründüğünde, birleşik çıktıdaki bağlam satırı eski dosyadan yazılıyor (`diff -w`'nin de davranışı).

**4** – Minimalliği kaybediyor: eşikten sonrası için bütün kalan satırlar silinip eklenmiş sayılıyor, gerçek fark çok daha küçük olabilir. Doğruluğu koruyor, çünkü "bütün eski kalanı sil, bütün yeni kalanı ekle" her zaman geçerli bir düzenleme; patch onu uygulayıp yeni dosyayı üretir. Daha iyi bir kesme GNU diff'in yaptığı: $D$ büyüyünce köşegenlerin her birinde "yeterince ilerlemiş" en iyi noktayı seçip oradan devam etmek (aramanın derinliğini sınırlamak); sonuç neredeyse minimal ve maliyet sınırlı. Bu, Ders 9.23'ün "garantiyi biraz bırakıp hız kazan" fikrinin bir örneği.

**5** – Myers en az değişiklik sayısını buluyor ama eşleşen satırları seçerken (eşit uzunlukta birçok LCS varken) sık geçen, anlamsız satırları (`}`, boş satır) eşleştirebiliyor ve bir fonksiyonun gövdesi yerine iki fonksiyonun kapanış parantezlerini hizalayıp okunması zor bir fark üretebiliyor. Patience: her iki dosyada **tam bir kez** geçen satırlar büyük ihtimalle anlamlı ve gerçekten karşılık geliyor (bir fonksiyon imzası gibi); önce onları eşleştirip "çapa" yap, sonra aradaki bölgeleri ayrı ayrı (ve özyinelemeyle) farkla. Çapaları seçmek: eşsiz satırların iki dosyadaki konumları $(i, j)$ çiftleri; $i$ sırasına dizildiğinde $j$'nin **en uzun artan alt dizisi**, birbiriyle çaprazlanmayan en büyük çapa kümesi. Bunu $O(n \log n)$'de bulan sabır sıralaması, algoritmaya adını veriyor (Bram Cohen, 2006).

</details>

---

## Kaynaklar

- Eugene Myers, "An O(ND) Difference Algorithm and Its Variations", *Algorithmica* 1(2), 1986.
- L. Peter Deutsch, RFC 1951, "DEFLATE Compressed Data Format Specification version 1.3", 1996.
- Mark Adler ve Jean-loup Gailly, *zlib* kaynak kodu, `inflate.c` ve `inftrees.c`: tablo tabanlı Huffman çözme.
- James Hunt ve M. Douglas McIlroy, "An Algorithm for Differential File Comparison", Bell Labs CSTR 41, 1976.
- GNU diffutils, `analyze.c`: Myers algoritması ve maliyet sınırlayan sezgiseller.
- Bram Cohen, "Patience Diff Advantages", 2010 (blog yazısı); Git belgeleri, `git diff --patience`.

**Sıradaki ders:** Faz 10'a geçiyoruz: işletim sistemi nedir. Çekirdek, sistem çağrısı, ve bir programın yaptığı çağrıları izlemek.
