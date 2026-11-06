---
title: "9.22 NP-tamlık"
description: "Kolayca doğrulanabilen ama bulunması zor görünen cevaplar: karar problemleri, P ve NP sınıfları, sertifika ile doğrulama; polinom zamanlı indirgeme ve NP-tamlık, Cook–Levin teoremi ve SAT; küçük bir DPLL SAT çözücü (birim yayılım, dallanma, geri izleme), 3-renklendirmeden SAT'a indirgemeyle Petersen grafının boyanması ve K4'ün boyanamadığının gösterilmesi; rastgele 3-SAT'ta tümce/değişken oranı 4.26 civarında faz geçişi ve üstel büyüme; derleyicilerdeki NP-zor problemler ve derleyicilerin onlarla nasıl yaşadığı."
---

Faz 9 boyunca polinom zamanlı algoritmalar yazdık: $O(n \log n)$ sıralama, $O(n + m)$ graf gezinmeleri, $O(n^3)$ Floyd–Warshall. Ama birkaç yerde duvara çarptık: 0/1 sırt çantası (Ders 9.12), DAG'larda optimal komut seçimi (Ders 9.13), graf renklendirme ve yazmaç ayırma (Ders 9.20). Bunlar için bilinen her algoritma, en kötü durumda **üstel** zaman alıyor. Ve bunun tesadüf olmadığına dair güçlü bir kanıt var: bu problemlerin hepsi **NP-tam**, yani biri polinom zamanda çözülürse hepsi çözülür; ve 50 yıldır kimse birini bile çözemedi. Bu ders bu iddianın ne demek olduğunu, NP-tam problemlerin "ana dili" SAT'ı ve bir derleyicinin bu problemlerle nasıl yaşadığını anlatıyor.

---

## 1. P ve NP

Kuram **karar problemleriyle** çalışıyor: cevabı evet ya da hayır. "Bu grafın kromatik sayısı ne?" yerine "Bu graf 3 renkle boyanabilir mi?" Optimizasyon sürümü karar sürümünden en fazla polinom bir faktörle (ikili aramayla; Ders 9.2) zor.

- **P**: girdinin uzunluğunda polinom zamanda **çözülebilen** karar problemleri. Sıralama, en kısa yol, iki parçalılık, 2-SAT (Ders 9.16).
- **NP**: cevabı "evet" olan her girdi için, polinom uzunlukta bir **sertifika** (tanık) olan ve bu sertifikanın polinom zamanda **doğrulanabildiği** problemler. "3 renkle boyanabilir mi?": sertifika bir renklendirme; doğrulamak her kenara bakmak, $O(m)$. "Bu formül sağlanabilir mi?": sertifika bir atama; doğrulamak her tümceye bakmak.

Her P problemi NP'de (sertifikaya bakmadan kendin çöz). **P = NP mi?**, yani doğrulaması kolay her problemin çözümü de kolay mı? Bilgisayar biliminin en önemli açık sorusu. Neredeyse herkes P ≠ NP olduğuna inanıyor, ama kanıt yok.

(NP, "nondeterministic polynomial" demek: her adımda doğru seçimi "tahmin eden" bir makinenin polinom zamanda çözebileceği problemler. Sertifika tanımı buna denk ve daha kullanışlı.)

## 2. İndirgeme ve NP-tamlık

$A$ problemi $B$'ye **polinom zamanda indirgenir** ($A \le_p B$): $A$'nın her girdisini, polinom zamanda $B$'nin bir girdisine çeviren ve cevabı koruyan bir dönüşüm var. O zaman $B$'yi çözen bir algoritma $A$'yı da çözer; $B$ en az $A$ kadar zor.

Bir problem **NP-tam**: NP'de, ve NP'deki **her** problem ona indirgenebiliyor. NP'nin "en zor" problemleri. Biri P'de ise, indirgemeler yoluyla bütün NP P'de olur.

**Cook–Levin teoremi** (1971): **SAT** (bir mantık formülünün, Ders 6.1, değişkenlerine onu doğru yapan bir atama var mı?) NP-tam. İspat fikri: NP'deki bir problemin doğrulayıcısı bir programdır; o programın bir girdi ve sertifika üzerindeki polinom uzunluktaki çalışması, her adımdaki her bit için bir değişkenle bir formül olarak yazılabilir. Formül sağlanabilir ⟺ doğrulayıcıyı kabul ettiren bir sertifika var.

Bir problemin NP-tam olduğunu göstermek için artık bütün NP'yi indirgemek gerekmiyor: bilinen bir NP-tam problemi **ona** indirgemek yetiyor. Karp (1972) bu yolla 21 problemi NP-tam gösterdi: 3-SAT, köşe örtüsü, bağımsız küme (Ders 9.13'te ağaçta doğrusaldı), Hamilton döngüsü, 3-renklendirme, sırt çantası, ... Bugün binlercesi biliniyor.

---

## 3. SAT çözmek

NP-tam olması SAT'ın pratikte çözülemez olduğu anlamına gelmiyor: modern SAT çözücüler milyonlarca değişkenli endüstriyel formülleri dakikalar içinde çözüyor (donanım doğrulama, paket bağımlılığı çözümü, derleyici testleri). Hepsinin temeli **DPLL** (Davis, Putnam, Logemann, Loveland, 1962):

1. **Birim yayılım**: bir tümcede tek bir belirsiz literal kalmışsa ve diğerleri yanlışsa, o literal doğru olmak **zorunda**. Yap, tekrarla. (Bir tümcenin bütün literalleri yanlışsa: çelişki.)
2. Değişken kalmadıysa: sağlandı.
3. Bir değişken seç, önce doğru dene (özyineleme); olmazsa geri al ve yanlış dene. İkisi de olmazsa: bu daldan çözüm yok.

Formül **CNF** (conjunctive normal form; Ders 6.1): tümcelerin VE'si, her tümce literallerin VEYA'sı. Literal `+v` ya da `-v`.

```c
/* Kucuk bir DPLL SAT cozucu: birim yayilim + dallanma + geri izleme. Literaller: +v / -v (v = 1..n). */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { int n, m; int *lit; int *bas; } CNF;            /* tumce c: lit[bas[c] .. bas[c+1]) */
static signed char *deger;                                       /* 0: atanmadi, +1 dogru, -1 yanlis */
static long dugum;                                               /* istatistik: dallanma sayisi */

static int lit_degeri(int l) { int d = deger[abs(l)]; return l > 0 ? d : -d; }   /* +1 dogru, -1 yanlis, 0 belirsiz */

/* Birim yayilim: tek belirsiz literali kalan ve dogru literali olmayan tumcelerde o literal dogru OLMALI.
   Iz yigini: geri izlemede geri almak icin. Celiski bulursa 0 doner. */
static int *iz, iz_n;
static int yay(const CNF *f) {
    int degisti = 1;
    while (degisti) {
        degisti = 0;
        for (int c = 0; c < f->m; c++) {
            int belirsiz = 0, son = 0, dogru = 0;
            for (int i = f->bas[c]; i < f->bas[c + 1]; i++) { int d = lit_degeri(f->lit[i]); if (d > 0) { dogru = 1; break; } if (d == 0) { belirsiz++; son = f->lit[i]; } }
            if (dogru) continue;
            if (belirsiz == 0) return 0;                          /* butun literaller yanlis: celiski */
            if (belirsiz == 1) { deger[abs(son)] = son > 0 ? 1 : -1; iz[iz_n++] = abs(son); degisti = 1; }
        }
    }
    return 1;
}
static int dpll(const CNF *f) {
    int isaret = iz_n;
    if (!yay(f)) { while (iz_n > isaret) deger[iz[--iz_n]] = 0; return 0; }
    int v = 0; for (int i = 1; i <= f->n; i++) if (!deger[i]) { v = i; break; }
    if (!v) return 1;                                             /* her sey atandi, celiski yok: SAGLANDI */
    dugum++;
    for (int dal = 1; dal >= -1; dal -= 2) {                      /* once dogru, sonra yanlis dene */
        deger[v] = (signed char)dal; iz[iz_n++] = v;
        if (dpll(f)) return 1;
        while (iz_n > isaret) deger[iz[--iz_n]] = 0;              /* geri al */
    }
    return 0;
}
static int coz(const CNF *f) {
    deger = calloc(f->n + 1, 1); iz = malloc((f->n + 1) * sizeof *iz); iz_n = 0; dugum = 0;
    return dpll(f);
}
static int dogrula(const CNF *f) {                               /* bulunan atama butun tumceleri sagliyor mu */
    for (int c = 0; c < f->m; c++) { int ok = 0; for (int i = f->bas[c]; i < f->bas[c + 1]; i++) if (lit_degeri(f->lit[i]) > 0) ok = 1; if (!ok) return 0; }
    return 1;
}

/* Tumce ekleme yardimcisi */
typedef struct { int *lit, *bas, n, m, kap_l, kap_c; } Yapici;
static void tumce(Yapici *y, const int *l, int k) {
    if (y->m + 2 > y->kap_c) { y->kap_c = 2 * y->kap_c + 16; y->bas = realloc(y->bas, y->kap_c * sizeof(int)); }
    if (y->bas[y->m] + k > y->kap_l) { y->kap_l = 2 * y->kap_l + 64; y->lit = realloc(y->lit, y->kap_l * sizeof(int)); }
    for (int i = 0; i < k; i++) y->lit[y->bas[y->m] + i] = l[i];
    y->bas[y->m + 1] = y->bas[y->m] + k; y->m++;
}
static Yapici yapici(int n) { Yapici y = { NULL, malloc(16 * sizeof(int)), n, 0, 0, 16 }; y.bas[0] = 0; return y; }
static CNF bitir(Yapici *y) { return (CNF){ y->n, y->m, y->lit, y->bas }; }

#ifndef KUTUPHANE
/* 3-RENKLENDIRME -> SAT: degisken x(v, c) = "v dugumu c renginde". Her dugum en az bir renk, en fazla bir renk; komsular farkli. */
static int X(int v, int c) { return 3 * v + c + 1; }
static CNF renk3(int n, const int (*k)[2], int m) {
    Yapici y = yapici(3 * n);
    for (int v = 0; v < n; v++) {
        int en_az[3] = { X(v,0), X(v,1), X(v,2) }; tumce(&y, en_az, 3);
        for (int a = 0; a < 3; a++) for (int b = a + 1; b < 3; b++) { int t[2] = { -X(v,a), -X(v,b) }; tumce(&y, t, 2); }
    }
    for (int i = 0; i < m; i++) for (int c = 0; c < 3; c++) { int t[2] = { -X(k[i][0], c), -X(k[i][1], c) }; tumce(&y, t, 2); }
    return bitir(&y);
}
int main(void) {
    /* Petersen grafi: 3 renkle boyanir. K4: boyanamaz. */
    int pet[15][2] = { {0,1},{1,2},{2,3},{3,4},{4,0},{0,5},{1,6},{2,7},{3,8},{4,9},{5,7},{7,9},{9,6},{6,8},{8,5} };
    CNF f = renk3(10, pet, 15);
    int s = coz(&f);
    printf("Petersen grafi (10 dugum, 15 kenar) -> %d degisken, %d tumce: %s, %ld dallanma, dogrulama %s\n  renkler:",
           f.n, f.m, s ? "SAGLANABILIR" : "SAGLANAMAZ", dugum, s && dogrula(&f) ? "gecti" : "-");
    for (int v = 0; v < 10; v++) for (int c = 0; c < 3; c++) if (deger[X(v, c)] > 0) printf(" %d=%d", v, c);
    printf("\n");
    int k4[6][2] = { {0,1},{0,2},{0,3},{1,2},{1,3},{2,3} };
    CNF g = renk3(4, k4, 6);
    printf("K4 (4 dugum, tam graf): %s, %ld dallanma\n", coz(&g) ? "SAGLANABILIR" : "SAGLANAMAZ", dugum);
}
#endif
```

`iz` yığını, birim yayılım ve dallanmanın yaptığı atamaları kaydediyor ki geri izlemede tam olarak onlar geri alınsın (Ders 8.6'nın açık yığını, bir arama ağacında).

### İndirgeme: 3-renklendirme → SAT

Bölüm 2'deki indirgemelerden birini **kod olarak** yazalım. Bir grafın 3-renklendirilebilirliği: her düğüm $v$ ve renk $c$ için bir değişken $x_{v,c}$ ("$v$, $c$ renginde"), ve üç tür tümce:

- Her düğüm en az bir renkte: $(x_{v,0} \lor x_{v,1} \lor x_{v,2})$.
- Her düğüm en fazla bir renkte: her renk çifti için $(\lnot x_{v,a} \lor \lnot x_{v,b})$.
- Komşular farklı renkte: her kenar $\{u, v\}$ ve renk $c$ için $(\lnot x_{u,c} \lor \lnot x_{v,c})$.

$n$ düğüm, $m$ kenar: $3n$ değişken, $n + 3n + 3m$ tümce, polinom. Formül sağlanabilir ⟺ graf 3-renklendirilebilir, ve bir sağlayan atama doğrudan bir renklendirme.

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined sat.c -o sat && ./sat
Petersen grafi (10 dugum, 15 kenar) -> 30 degisken, 85 tumce: SAGLANABILIR, 6 dallanma, dogrulama gecti
  renkler: 0=0 1=1 2=0 3=1 4=2 5=1 6=0 7=2 8=2 9=1
K4 (4 dugum, tam graf): SAGLANAMAZ, 5 dallanma
```

Petersen grafı (10 düğüm, 15 kenar; $10 + 30 + 45 = 85$ tümce) 3 renkle boyanıyor; bulunan atama bütün tümceleri sağlıyor ve okunan renklendirme geçerli. Dört düğümlü tam graf $K_4$ boyanamıyor: çözücü bütün dalları tüketip "sağlanamaz" diyor. Bu, NP-tamlığın pratikteki yüzü: bir problemi SAT'a çevir, iyi bir SAT çözücüye ver. Bu bir algoritma tasarım yöntemi olarak çok güçlü; Faz 19'daki Z3 bunun genelleştirilmiş hali (SMT).

---

## 4. Zorluk nerede

NP-tam bir problemin **her** örneği zor değil: en kötü durum zor. Rastgele 3-SAT formüllerinde zorluğun nerede yoğunlaştığı iyi biliniyor: tümce sayısının değişken sayısına oranı $\alpha = m/n$.

```c
static CNF rastgele3(int n, int m) {
    Yapici y = yapici(n);
    for (int c = 0; c < m; c++) { int l[3];
        for (int j = 0; j < 3; j++) { int v; int tekrar; do { v = 1 + (int)(rnd() % (uint64_t)n); tekrar = 0; for (int t = 0; t < j; t++) if (abs(l[t]) == v) tekrar = 1; } while (tekrar);
            l[j] = rnd() & 1 ? v : -v; }
        tumce(&y, l, 3); }
    return bitir(&y);
}
```

```
$ cc -std=c11 -O2 -Wall -Wextra faz.c -o faz && ./faz
n=40, her oran icin 100 rastgele formul:
  m/n=2.0: %100 saglanabilir, ortanca dallanma     22
  m/n=2.5: %100 saglanabilir, ortanca dallanma     19
  m/n=3.0: %100 saglanabilir, ortanca dallanma     19
  m/n=3.5: %100 saglanabilir, ortanca dallanma     21
  m/n=4.0: % 80 saglanabilir, ortanca dallanma     64
  m/n=4.5: % 41 saglanabilir, ortanca dallanma     97
  m/n=5.0: %  8 saglanabilir, ortanca dallanma     96
  m/n=5.5: %  3 saglanabilir, ortanca dallanma     69
  m/n=6.0: %  0 saglanabilir, ortanca dallanma     55
  m/n=6.5: %  0 saglanabilir, ortanca dallanma     41
  m/n=7.0: %  0 saglanabilir, ortanca dallanma     33
m/n = 4.26, n buyudukce (ortanca, 30 formul):
  n= 20: ortanca       11 dallanma, ortalama sure 0.0000 s
  n= 30: ortanca       47 dallanma, ortalama sure 0.0002 s
  n= 40: ortanca      133 dallanma, ortalama sure 0.0008 s
  n= 50: ortanca      307 dallanma, ortalama sure 0.0020 s
  n= 60: ortanca      776 dallanma, ortalama sure 0.0070 s
  n= 70: ortanca     1435 dallanma, ortalama sure 0.0157 s
```

(Her "sağlanabilir" cevabı `dogrula` ile kontrol ediliyor.)

- **Az tümce** ($\alpha \le 3.5$): formül neredeyse her zaman sağlanabilir ve kolayca bulunuyor (20 civarı dallanma).
- **Çok tümce** ($\alpha \ge 6$): neredeyse hiçbir zaman sağlanamaz, ve çelişki birim yayılımla çabuk ortaya çıkıyor.
- **Arada**, $\alpha \approx 4.26$ civarında: yarı yarıya sağlanabilir ve **en zor** formüller burada (dallanma sayısı zirvede). Bu bir **faz geçişi** (Mitchell, Selman ve Levesque, 1992; Ders 8.18'deki süzülmenin mantık dünyasındaki karşılığı); $n$ büyüdükçe geçiş keskinleşiyor ve eşik deneysel olarak 4.267.
- Eşikte $n$ 10 artınca dallanma sayısı **2–4 kat** artıyor: üstel büyüme, kabaca $1.1^n$. 70 değişkende 16 ms; aynı hızla 300 değişkende yıllar. Modern çözücüler (CDCL: çelişkilerden tümce öğrenen, yeniden başlatan) aynı formüllerde çok daha iyi, ama eşik formülleri onlar için de en zor sınıf.

---

## 5. Derleyicide NP-zor problemler

| Problem | Ders | Derleyicinin yaklaşımı |
| --- | --- | --- |
| Yazmaç ayırma (genel girişim grafı renklendirme) | 9.20 | Chaitin–Briggs sezgiseli; SSA'da kordal graf, polinom |
| Komut planlama (kaynak kısıtlı) | 7.21–7.23 | Liste planlama (açgözlü, kritik yol öncelikli; Ders 9.15) |
| DAG'larda optimal komut seçimi | 9.13 | Ağaçlara böl, her ağaçta DP |
| Optimal kod (süperoptimizasyon) | — | Sadece çok kısa diziler için kapsamlı arama ya da SAT/SMT |
| Fonksiyon sıralama, kod yerleşimi | — | Sezgisel (sıcak yollar önce) |

Üç strateji tekrar ediyor: **özel durumu bul** (ağaçlar, SSA, aralık grafları gibi polinom çözülebilen alt sınıflar), **sezgisel kullan** (Ders 9.23; hızlı, genelde iyi, garantisiz), ve **küçük örnekleri tam çöz** (SAT, tam sayılı doğrusal programlama). Bir derleyici her gün NP-zor problemlerle karşılaşıyor ve neredeyse hiçbirini optimal çözmüyor; optimal ile "yeterince iyi" arasındaki fark genelde yüzde birkaç.

---

## Alıştırmalar

**1** – 3-renklendirmenin NP'de olduğunu, doğrulayıcıyı yazarak göster: girdi bir graf ve bir renklendirme, çıktı evet/hayır. Karmaşıklığı ne? "Bu graf 3 renkle **boyanamaz**" iddiası için kısa bir sertifika var mı? (Bu, co-NP sorusu.)

**2** – İndirgemenin yönü: $A \le_p B$ ve $B$ kolay ise $A$ kolay. Bir öğrenci "SAT'ı, ikili aramaya (kolay bir probleme) indirgedim; demek ki SAT kolay" diyor, ve indirgemesi "her değişken için iki olasılığı da dene" adımını içeriyor. Hata nerede?

**3** – 2-SAT, Ders 9.16'da doğrusal zamanda çözüldü; 3-SAT NP-tam. Bir 3-tümceyi ($a \lor b \lor c$) 2-tümcelere çevirmeye çalış. Neden polinom boyutta bir çeviri bulamazsın (ya da bulursan ne kanıtlamış olursun)?

**4** – Bölüm 3'teki indirgemeyi **$k$ renk** için genelleştir. Kaç değişken ve kaç tümce? Ders 9.20'deki 300 rastgele grafın kromatik sayılarını SAT çözücüyle bulmak için ne yapardın?

**5** – 0/1 sırt çantası NP-tam, ama Ders 9.12'de $O(nW)$'de çözdük. Bu bir çelişki mi? "Zayıf" ve "güçlü" NP-zorluk ne demek? Hangi Faz 9 problemi güçlü anlamda NP-zor?

<details>
<summary>Cevaplar</summary>

**1** – Doğrulayıcı: her düğümün renginin $\{0, 1, 2\}$'de olduğunu ve her kenarın iki ucunun farklı renkte olduğunu kontrol et. $O(n + m)$, polinom; sertifikanın boyutu $O(n)$. Dolayısıyla 3-renklendirme NP'de. "Boyanamaz" için kısa bir sertifika bilinmiyor: bir $K_4$ alt grafı bazen bir kanıt, ama boyanamayan her grafta $K_4$ yok (örneğin bazı Mycielski grafları). Genel olarak "hayır" cevaplarının kısa sertifikaları olan problemler co-NP sınıfında; NP = co-NP olup olmadığı da açık, ve büyük ihtimalle değil. SAT çözücüler "sağlanamaz" derken bir **çürütme ispatı** (resolution kanıtı) üretebiliyor, ama o kanıt üstel uzunlukta olabiliyor.

**2** – İndirgeme **polinom zamanlı** olmalı; "her değişken için iki olasılığı dene" $2^n$ olasılık üretiyor. O zaman dönüşüm üstel zaman alıyor ve sonuçta $B$'nin kolay olması $A$ hakkında bir şey söylemiyor. Ayrıca yön: $A$'yı kolay bir $B$'ye polinom zamanda indirgemek $A$'nın kolay olduğunu kanıtlar; zor bir problemin kolay olduğunu "kanıtlayan" bir argüman neredeyse her zaman indirgemenin maliyetini gözden kaçırıyor.

**3** – $(a \lor b \lor c)$ "en az biri doğru" demek; 2-tümcelerle sadece **ikili** ilişkiler (çıkarımlar, $\lnot a \Rightarrow b$) ifade edilebiliyor ve "üçünden en az biri" bir çıkarım grafıyla yazılamıyor. Yeni yardımcı değişkenler eklemek de işe yaramıyor (2-SAT'ın çıkarım grafındaki SCC yapısı ifade gücünü sınırlıyor). Polinom boyutta, cevabı koruyan bir 3-SAT → 2-SAT çevirisi bulmak, 3-SAT'ı polinom zamanda çözmek (2-SAT P'de) yani **P = NP**'yi kanıtlamak olurdu. Yani böyle bir çeviri büyük ihtimalle yok; ve varsa, onu bulan kişi bilgisayar biliminin en ünlü problemini çözmüş olur.

**4** – $kn$ değişken; $n$ "en az bir" tümcesi ($k$ literalli), $n \binom{k}{2}$ "en fazla bir" tümcesi, $km$ "komşular farklı" tümcesi. Toplam $n + n k(k-1)/2 + km$, polinom. Kromatik sayı: $k = 1, 2, 3, \dots$ için formülü kur ve çöz; ilk sağlanabilir $k$ cevap. Ya da ikili arama: $\chi \le \Delta + 1$ (Ders 9.20), aralığı yarıya bölerek. Ders 9.20'deki geri izleme bunun SAT'sız hali; büyük graflarda SAT çözücünün öğrenme ve yayılımı genelde çok daha hızlı. Simetri (renkler değiştirilebilir) yüzünden "renk sınıflarını sırala" gibi simetri kırıcı tümceler eklemek büyük hızlanma sağlıyor.

**5** – Çelişki değil. $O(nW)$, girdinin **uzunluğunda** polinom değil: $W$ girdide $\log_2 W$ bitle yazılıyor ve $W$ o uzunlukta **üstel** (Ders 9.12'nin "sözde polinom"u). Sayılar küçükken (birli tabanda yazılmış gibi) problem kolay: buna **zayıf** NP-zorluk denir. **Güçlü** NP-zor problemler, sayılar polinom büyüklükte olsa bile zor: 3-renklendirme (hiç sayı yok), gezgin satıcı, bağımsız küme. Faz 9'dan: Ders 9.20'deki renklendirme ve Ders 9.23'teki gezgin satıcı güçlü anlamda NP-zor; sırt çantası ve (Ders 9.10'daki) para üstü zayıf.

</details>

---

## Kaynaklar

- Stephen Cook, "The Complexity of Theorem-Proving Procedures", *STOC* 1971.
- Richard Karp, "Reducibility Among Combinatorial Problems", *Complexity of Computer Computations*, 1972.
- Michael Garey ve David Johnson, *Computers and Intractability: A Guide to the Theory of NP-Completeness*, W. H. Freeman, 1979.
- Martin Davis, George Logemann ve Donald Loveland, "A Machine Program for Theorem-Proving", *Communications of the ACM* 5(7), 1962: DPLL.
- David Mitchell, Bart Selman ve Hector Levesque, "Hard and Easy Distributions of SAT Problems", *AAAI* 1992.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 34: NP-tamlık.

**Sıradaki ders:** Yaklaşım ve sezgisel yöntemler. Yerel arama, benzetimli tavlama ve derleyicilerde sezgisel kararlar.
