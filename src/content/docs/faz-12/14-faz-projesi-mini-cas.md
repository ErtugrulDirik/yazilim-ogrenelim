---
title: "12.14 Faz projesi: mini CAS"
description: "Fazın bütün parçalarını tek bir komut satırı cebir sistemine bağlamak: kesin sayılar (2^200, (2/3)^-4, 1000!), Miller–Rabin ile asallık (2^127 - 1 ve 2^521 - 1), tanımlar (f := x^3 - 2x + 1), kural tabanlı sadeleştirme, Q[x] kanonik formuyla genişletme, polinom bölmesi ve EBOB, sembolik türev ve kesin değer; iç içe komutlar ve ifadenin içindeki komutların yaz-ayrıştır döngüsü sayesinde metinle yer değiştirmesi; oturumun SymPy ile doğrulanması; kural tabanlı sadeleştirmenin sınırlarını gösteren iki örnek ve 1900 satırlık sistemin katman haritası."
---

On üç derste parçaları tek tek yazdık: büyük tamsayılar, modüler aritmetik, kesirler, polinomlar, polinom EBOB'u, FFT, sonlu cisimler, ifade ağacı, sadeleştirme ve türev. Faz projesi onları **tek bir programda** bir araya getiriyor: bir satır yaz, sonucu kesin olarak al. Amaç Mathematica'yı yeniden yazmak değil. Her katmanın bir üsttekine nasıl hizmet ettiğini ve nerede yetersiz kaldığını görmek.

---

## 1. Katmanlar

```
  cas.c        komutlar, tanimlar, satir okuma                233 satir
  ---------------------------------------------------------------------
  turev.c      sembolik turev (12.13)                          46
  sadele.c     yeniden yazma, katlama, Q[x] kanonik form (12.12) 194
  ifade.c      agac, ayristirma, yazdirma (12.11)              250
  ---------------------------------------------------------------------
  poli*.c      Q[x]: carpma, bolme, EBOB (12.7, 12.8)          218
  rat.c        kesirler (12.6)                                  91
  bn_mod.c, bn_mont.c, bn_asal.c  us alma, EBOB, Miller-Rabin (12.5)  305
  bn_*.c       limb dizileri, Karatsuba, Algoritma D (12.2-12.4)  360
  ---------------------------------------------------------------------
                                          baslik dosyalari dahil 1894 satir
```

Her katman yalnız altındakini kullanıyor. `ifade.c` sayıları `rat` olarak tutuyor ve sabit katlama doğrudan kesin. `sadele.c` bir polinomu tanıyınca onu `poli`'ye çeviriyor ve kanonik formu oradan alıyor. `rat` her işlemden sonra `bn_ebob` çağırıyor. En üstteki bir `genislet((x + 1)^10)` komutu, en alttaki limb toplamasına kadar iniyor.

Bu fazda yazmadığımız ama yazabileceğimiz iki katman: 12.9'daki FFT, `bn_carp`'ın büyük sayılar için seçebileceği bir yol olarak (Alıştırma 2). 12.10'daki $GF(p)[x]$, polinom EBOB'unu modüler yapmak için (Ders 12.8, Alıştırma 5).

---

## 2. Komutlar

| komut | ne yapar | hangi katman |
| --- | --- | --- |
| ifade | sadeleştirir, kesin hesaplar | `sadele`, `rat`, `bn` |
| `ad := ifade` | tanımlar; sonraki satırlarda yerine konur | `cas` |
| `turev(f, x)` | türev alır ve sadeleştirir | `turev`, `sadele` |
| `genislet(f)` | $\mathbb{Q}[x]$ kanonik formu | `poli` |
| `bol(f, g)` | bölüm ve kalan | `poli_bol` |
| `ebob(f, g)` | monik EBOB | `poli_bol` |
| `deger(f, x, a)` | $x$ yerine $a$ koyar, kesin hesaplar | `cas`, `sadele` |
| `fakt(n)` | $n!$ | `bn` |
| `asal(n)` | Miller–Rabin, 40 tur | `bn_asal`, `bn_mont` |
| `sure` | her satırın süresini göster/gizle | `olcum.h` |

```c
/* cas.c: mini bilgisayar cebir sistemi. Her satir bir ifade, bir tanim (ad := ifade) ya da bir komut.
   Komutlar ic ice kullanilabilir: turev(turev(f, x), x)
     turev(f, x)   genislet(f)   ebob(f, g)   deger(f, x, a)   fakt(n)      -> ifade dondurur
     bol(f, g)     asal(n)                                                  -> yalniz en distan
     sure          olcumu ac/kapa */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include <unistd.h>
#include "olcum.h"
#include "bn_mod.h"
#include "sadele.h"
#include "turev.h"

#define TANIM_EN 64
static char tanim_ad[TANIM_EN][8];
static ifade *tanim[TANIM_EN];
static int tanim_n;
static char hata_m[160];

/* e'deki her 'ad' degiskeninin yerine d'nin bir kopyasini koy */
static ifade *yerine(const ifade *e, const char *ad, const ifade *d) {
    if (e->t == DEG && !strcmp(e->ad, ad)) return i_kopya(d);
    ifade *k = i_kopya(e);
    if (e->a) { i_sil(k->a); k->a = yerine(e->a, ad, d); }
    if (e->b) { i_sil(k->b); k->b = yerine(e->b, ad, d); }
    return k;
}

static const char *ilk_degisken(const ifade *e) {  /* polinom komutlari icin: ifadedeki ilk degisken */
    if (e->t == DEG) return e->ad;
    const char *a = e->a ? ilk_degisken(e->a) : 0;
    return a ? a : e->b ? ilk_degisken(e->b) : 0;
}

static void yaz(const ifade *e) { char *s = i_yaz(e); printf("  %s\n", s); free(s); }

/* "a, b, c": ust duzeydeki virgullerden bol (yerinde) */
static int argumanlar(char *s, char **arg, int en) {
    int n = 0, derin = 0;
    arg[n++] = s;
    for (char *p = s; *p; p++) {
        if (*p == '(') derin++;
        else if (*p == ')') derin--;
        else if (*p == ',' && derin == 0) { *p = 0; if (n < en) arg[n++] = p + 1; }
    }
    return n;
}

/* s = "komut(govde)" ve kapanan parantez en sonda mi */
static const char *komutlar[] = { "turev", "genislet", "ebob", "deger", "fakt", "bol", "asal", 0 };
static int komut_mu(const char *s, char *ad, char **govde) {
    size_t n = strspn(s, "abcdefghijklmnopqrstuvwxyz");
    int k = -1;
    for (int i = 0; komutlar[i]; i++) if (strlen(komutlar[i]) == n && !strncmp(s, komutlar[i], n)) k = i;
    if (k < 0 || s[n] != '(') return 0;
    int derin = 0; const char *p = s + n;
    for (; *p; p++) { if (*p == '(') derin++; if (*p == ')' && --derin == 0) break; }
    const char *son = p;
    if (!*p) return 0;
    for (p++; isspace((unsigned char)*p); p++) {}
    if (*p) return 0;                                 /* turev(f, x) + 1: komut degil, ifade */
    strcpy(ad, komutlar[k]);
    size_t u = son - (s + n + 1);
    *govde = malloc(u + 1); memcpy(*govde, s + n + 1, u); (*govde)[u] = 0;
    return 1;
}

static ifade *hesapla(const char *s);

static int poli_al(poli *p, const ifade *e, const char *x) {
    if (ifade_poli(p, e, x)) { snprintf(hata_m, sizeof hata_m, "bu ifade %s'e gore bir polinom degil", x); return -1; }
    return 0;
}

static int dogal(bn *x, const ifade *e) {          /* e, sadelesince negatif olmayan bir tamsayi mi */
    ifade *d = sadelestir(e);
    int ok = d->t == SAYI && !d->r.p.isaret && d->r.q.n == 1 && d->r.q.d[0] == 1;
    if (ok) bn_kopyala(x, &d->r.p); else snprintf(hata_m, sizeof hata_m, "bir dogal sayi bekleniyordu");
    i_sil(d);
    return ok;
}

/* ifade donduren komutlar; en_dis: bol ve asal yalniz en distan cagrilabilir, sonucu kendisi yazar */
static ifade *komut(const char *ad, char *govde, int en_dis) {
    char *arg[4];
    int n = argumanlar(govde, arg, 4);
    ifade *e[3] = { 0 }, *sonuc = 0;
    for (int i = 0; i < n && i < 3; i++) if (!(e[i] = hesapla(arg[i]))) goto bitir;
    if (!strcmp(ad, "turev") && n == 2 && e[1]->t == DEG) {
        ifade *d = i_turev(e[0], e[1]->ad); sonuc = sadelestir(d); i_sil(d);
    } else if (!strcmp(ad, "deger") && n == 3 && e[1]->t == DEG) {
        ifade *y = yerine(e[0], e[1]->ad, e[2]); sonuc = sadelestir(y); i_sil(y);
    } else if (!strcmp(ad, "genislet") && n == 1) {
        const char *x = ilk_degisken(e[0]); if (!x) x = "x";
        poli p; poli_baslat(&p);
        if (!poli_al(&p, e[0], x)) sonuc = poli_ifade(&p, x);
        poli_sil(&p);
    } else if ((!strcmp(ad, "ebob") || !strcmp(ad, "bol")) && n == 2 && (en_dis || ad[0] == 'e')) {
        const char *x = ilk_degisken(e[0]); if (!x) x = ilk_degisken(e[1]); if (!x) x = "x";
        poli a, b, q, r; poli_baslat(&a); poli_baslat(&b); poli_baslat(&q); poli_baslat(&r);
        if (!poli_al(&a, e[0], x) && !poli_al(&b, e[1], x)) {
            if (ad[0] == 'e') { poli_ebob(&q, &a, &b); sonuc = poli_ifade(&q, x); }
            else if (b.n == 0) snprintf(hata_m, sizeof hata_m, "sifir polinoma bolme");
            else {
                poli_bol(&q, &r, &a, &b);
                ifade *k1 = poli_ifade(&q, x), *k2 = poli_ifade(&r, x);
                char *s1 = i_yaz(k1), *s2 = i_yaz(k2);
                printf("  bolum: %s\n  kalan: %s\n", s1, s2);
                free(s1); free(s2); i_sil(k1);
                sonuc = k2;                           /* yazildi; cagiran yazmasin diye isaretlenecek */
            }
        }
        poli_sil(&a); poli_sil(&b); poli_sil(&q); poli_sil(&r);
    } else if ((!strcmp(ad, "fakt") || (!strcmp(ad, "asal") && en_dis)) && n == 1) {
        bn x; bn_baslat(&x);
        if (dogal(&x, e[0])) {
            if (ad[0] == 'f') {
                if (x.n > 1 || (x.n && x.d[0] > 100000)) snprintf(hata_m, sizeof hata_m, "en fazla 100000");
                else {
                    uint32_t k = x.n ? x.d[0] : 0;
                    rat f; rat_baslat(&f); rat_tam(&f, 1);
                    bn t; bn_baslat(&t);
                    for (uint32_t i = 2; i <= k; i++) { bn_u64(&t, i); bn_carp(&f.p, &f.p, &t); }
                    sonuc = i_rat(&f); rat_sil(&f); bn_sil(&t);
                }
            } else {
                uint64_t s = 1;
                int a = x.n == 0 || (x.n == 1 && x.d[0] < 4) ? x.n && x.d[0] >= 2 : (x.d[0] & 1) && bn_asal_mi(&x, 40, &s);
                printf("  %s\n", a ? "asal (Miller-Rabin, 40 tur)" : "asal degil");
                sonuc = i_sayi(a);
            }
        }
        bn_sil(&x);
    } else if (!hata_m[0]) snprintf(hata_m, sizeof hata_m, "%s: yanlis arguman (ya da yalniz en distan kullanilabilir)", ad);
bitir:
    for (int i = 0; i < 3; i++) i_sil(e[i]);
    return sonuc;
}

static int yazildi;                                    /* bol ve asal sonucu kendisi yazdi */
static int komuttu;                                    /* en distaki ifade bir komuttu: sonucu zaten sade */

/* ifadenin icindeki komutlari (fakt(20)/fakt(18)) sonuclarinin metniyle degistir. Guvenli, cunku
   i_yaz ile i_ayristir birbirinin tersi (Ders 12.11) */
static char *komutlari_ac(const char *s) {
    char *m = strdup(s);
    for (;;) {
        char *p = m, *bas = 0;
        for (; *p; p++) {                              /* bir komut adinin basi: oncesinde harf/rakam yok */
            if (p > m && isalnum((unsigned char)p[-1])) continue;
            for (int i = 0; komutlar[i]; i++) {
                size_t n = strlen(komutlar[i]);
                if (!strncmp(p, komutlar[i], n) && p[n] == '(') { bas = p; break; }
            }
            if (bas) break;
        }
        if (!bas) return m;
        size_t n = strspn(bas, "abcdefghijklmnopqrstuvwxyz");
        int derin = 0; char *q = bas + n;
        for (; *q; q++) { if (*q == '(') derin++; if (*q == ')' && --derin == 0) break; }
        if (!*q) return m;                             /* kapanmayan parantez: ayristirici hatayi soylesin */
        char ad[16]; snprintf(ad, sizeof ad, "%.*s", (int)n, bas);
        size_t u = q - (bas + n + 1);
        char *govde = malloc(u + 1); memcpy(govde, bas + n + 1, u); govde[u] = 0;
        ifade *e = komut(ad, govde, 0);
        free(govde);
        if (!e) { free(m); return 0; }
        char *y = i_yaz(e); i_sil(e);
        size_t boy = strlen(m) + strlen(y) + 3;
        char *yeni = malloc(boy);
        snprintf(yeni, boy, "%.*s(%s)%s", (int)(bas - m), m, y, q + 1);
        free(y); free(m); m = yeni;
    }
}

/* metin -> ifade: tumu bir komutsa calistir; degilse icindeki komutlari ac, ayristir, tanimlari yerine koy */
static ifade *hesapla_(const char *s, int en_dis) {
    while (isspace((unsigned char)*s)) s++;
    char ad[16], *govde;
    if (komut_mu(s, ad, &govde)) {
        ifade *e = komut(ad, govde, en_dis);
        free(govde);
        if (en_dis) { komuttu = 1; if (!strcmp(ad, "bol") || !strcmp(ad, "asal")) yazildi = 1; }
        return e;
    }
    char *m = komutlari_ac(s), h[128];
    if (!m) return 0;
    ifade *e = i_ayristir(m, h, sizeof h);
    free(m);
    if (!e) { snprintf(hata_m, sizeof hata_m, "%s", h); return 0; }
    for (int i = tanim_n; i-- > 0;) { ifade *y = yerine(e, tanim_ad[i], tanim[i]); i_sil(e); e = y; }
    return e;
}
static ifade *hesapla(const char *s) { return hesapla_(s, 0); }

int main(void) {
    char satir[4096];
    int sure = 0;
    while (printf("> "), fflush(stdout), fgets(satir, sizeof satir, stdin)) {
        satir[strcspn(satir, "\n")] = 0;
        if (!isatty(0)) printf("%s\n", satir);       /* dosyadan okurken girdiyi de goster */
        char *s = satir;
        while (isspace((unsigned char)*s)) s++;
        if (!*s || *s == '#') continue;
        if (!strcmp(s, "sure")) { sure = !sure; printf("  sure olcumu %s\n", sure ? "acik" : "kapali"); continue; }
        double t0 = simdi();
        hata_m[0] = 0; yazildi = 0; komuttu = 0;
        char *tn = strstr(s, ":="), isim[8] = "";
        if (tn) {                                     /* tanim: f := x^2 + 1 */
            size_t k = 0;
            for (char *p = s; p < tn && k < 7; p++) if (!isspace((unsigned char)*p)) isim[k++] = *p;
            isim[k] = 0;
            s = tn + 2;
        }
        ifade *e = hesapla_(s, !tn), *d = !e ? 0 : komuttu ? i_kopya(e) : sadelestir(e);
        if (!d) printf("  hata: %s\n", hata_m[0] ? hata_m : "?");
        else if (tn) {
            int i = 0; while (i < tanim_n && strcmp(tanim_ad[i], isim)) i++;
            if (i == TANIM_EN) printf("  hata: cok fazla tanim\n");
            else { if (i == tanim_n) tanim_n++; else i_sil(tanim[i]); tanim[i] = i_kopya(d); strcpy(tanim_ad[i], isim); yaz(d); }
        } else if (!yazildi) {
            char *y = i_yaz(d); size_t u = strlen(y);
            if (u <= 120) printf("  %s\n", y); else printf("  %.50s...%s  (%zu karakter)\n", y, y + u - 20, u);
            free(y);
        }
        i_sil(e); i_sil(d);
        if (sure) printf("  (%.3f ms)\n", (simdi() - t0) * 1e3);
    }
    printf("\n");
    return 0;
}
```

İki tasarım kararı:

- **Komutlar ayrıştırıcıda değil.** `turev(f, x)`'in ikinci argümanı bir değişken, `bol` iki sonuç döndürüyor, `asal` bir metin. Bunları ifade ağacına eklemek (yeni düğüm türleri) mümkün ama sadeleştiriciyi ve türevi karmaşıklaştırırdı. Bunun yerine `cas.c`, bir satırın tamamen bir komut olup olmadığına bakıyor. İfadenin **içindeki** komutları ise (`fakt(20)/fakt(18)`) önce çalıştırıp sonucun **metniyle** değiştiriyor: `(2432902008176640000)/(6402373705728000)`. Bu ancak `i_yaz` ve `i_ayristir` birbirinin tersi olduğu için güvenli. Ders 12.11'de bunu 100000 ağaçla sınamış, Ders 12.13'te eksi kesirlerdeki bir istisnayı düzeltmiştik.
- **Komut sonuçları yeniden sadeleştirilmiyor.** İlk sürüm her sonucu `sadelestir`'den geçiriyordu ve `genislet(f*g)`, `x^2 + 2*x + (x^5 - 3*x^3) - 1` çıkıyordu. Sadeleştiricinin sıralaması (Ders 12.12) polinomun terim sırasını bozuyordu. Kanonik form zaten "sade": üzerine bir sezgisel uygulamak onu kötüleştirir.

---

## 3. Bir oturum

```
$ clang -O2 cas.c bn_temel.c bn_carp.c bn_bol.c bn_mod.c bn_mont.c bn_asal.c rat.c poli.c poli_bol.c \
        ifade.c sadele.c turev.c -o cas
$ ./cas < cas_ornek.txt
```

```text
> # sayilar: kesin
> 2^200
  1606938044258990275541962092341162602522202993782792835301376
> 1/3 + 1/6 - 1/2
  0
> (2/3)^-4
  81/16
> fakt(30)
  265252859812191058636308480000000
> fakt(1000)
  40238726007709377354370243392300398571937486421071...00000000000000000000  (2568 karakter)
> asal(2^127 - 1)
  asal (Miller-Rabin, 40 tur)
> asal(2^128 + 1)
  asal degil
> # sadelestirme
> x*1 + 0 + x + x
  3*x
> sin(x)^2 + cos(x)^2 + y - y
  1
> # tanimlar
> f := x^3 - 2*x + 1
  x^3 - 2*x + 1
> g := x^2 - 1
  x^2 - 1
> f*g
  (x^3 - 2*x + 1)*(x^2 - 1)
> genislet(f*g)
  x^5 - 3*x^3 + x^2 + 2*x - 1
> genislet((x + 1)^10)
  x^10 + 10*x^9 + 45*x^8 + 120*x^7 + 210*x^6 + 252*x^5 + 210*x^4 + 120*x^3 + 45*x^2 + 10*x + 1
> # polinom bolmesi ve EBOB
> bol(f, x - 1)
  bolum: x^2 + x - 1
  kalan: 0
> ebob(f, g)
  x - 1
> ebob(x^4 - 1, x^6 - 1)
  x^2 - 1
> ebob((x - 1)^3*(x + 2), 3*(x - 1)^2*(x + 2) + (x - 1)^3)
  x^2 - 2*x + 1
> # turev
> turev(f, x)
  3*x^2 - 2
> turev(x^2*sin(x), x)
  cos(x)*x^2 + 2*x*sin(x)
> turev(exp(x)/x, x)
  (x*exp(x) - exp(x))/x^2
> turev(turev(ln(x^2 + 1), x), x)
  (2*(x^2 + 1) - (2*x)^2)/(x^2 + 1)^2
> # kesin deger
> deger(f, x, 1/2)
  1/8
> deger(turev(f, x), x, 1/2)
  -5/4
> deger(x^2*exp(y), y, 0)
  x^2
> h := turev(x^4, x)
  4*x^3
> deger(h, x, 3)
  108
> fakt(20)/fakt(18)
  380
> turev(f, x) + 1 - 3*x^2
  3*x^2 - 1 - 3*x^2
> genislet((x + 1)^3) - x^3 - 1
  x^3 + 3*x + 3*x^2 + 1 - x^3 - 1
> genislet(turev(f, x) + 1 - 3*x^2)
  -1
> genislet(genislet((x + 1)^3) - x^3 - 1)
  3*x^2 + 3*x
> ebob(genislet((x-1)^5*(x+3)), turev(genislet((x-1)^5*(x+3)), x))
  x^4 - 4*x^3 + 6*x^2 - 4*x + 1
> sure
  sure olcumu acik
> fakt(10000)
  28462596809170545189064132121198688901480514017027...00000000000000000000  (35660 karakter)
  (100.849 ms)
> asal(2^521 - 1)
  asal (Miller-Rabin, 40 tur)
  (34.919 ms)
> sure
  sure olcumu kapali
> # hatalar
> sin(x
  hata: 6. karakterde ')' bekleniyordu
> ebob(sin(x), x)
  hata: bu ifade x'e gore bir polinom degil
> foo(x)
  hata: 4. karakterde bilinmeyen fonksiyon
> 
```

(Girdi dosyadan okunduğunda program her satırı ekrana da yazıyor: `isatty`, Ders 10.2'deki dosya tanımlayıcısının bir terminal olup olmadığını söylüyor. Etkileşimli kullanımda `./cas` çalıştırıp satırları kendin yazabilirsin.)

Satır satır neler oluyor:

- **`2^200`, `(2/3)^-4`, `1/3 + 1/6 - 1/2`**: sabit katlama, `rat` ile. Hiç yuvarlama yok.
- **`fakt(1000)`**: Ders 12.4'teki 2568 basamak. `fakt(10000)` 84 ms: 10000 tane küçük çarpma ve sonunda $O(n^2)$ onluk dönüşüm. Ders 12.4'te bunu nasıl hızlandıracağımızı gördük.
- **`asal(2^127 - 1)`**: Mersenne asalı $M_{127}$, Lucas'ın 1876'da elle kanıtladığı. `asal(2^128 + 1)`: Fermat sayısı $F_7$, bileşik. `asal(2^521 - 1)`, 1952'de SWAC bilgisayarının bulduğu ilk Mersenne asallarından biri: 15.6 ms. 40 turun her biri 521 bitlik bir Montgomery üs alması (Ders 12.5).
- **`sin(x)^2 + cos(x)^2 + y - y`** → `1`: üç kural (`A + B - A -> B`, sıralama, sıralı yazılmış `cos(A)^2 + sin(A)^2 -> 1`).
- **`ebob(f, g)`** → `x - 1`: $f(1) = 0$ ve $g(1) = 0$. `bol(f, x - 1)` bunu kalanın sıfır olmasıyla doğruluyor.
- **`ebob(p, p')`** ($p = (x - 1)^5 (x + 3)$) → $x^4 - 4x^3 + 6x^2 - 4x + 1 = (x - 1)^4$: Ders 12.8'deki "katlı kök türevde bir eksik katla kalır".
- **`turev(turev(ln(x^2 + 1), x), x)`**: iç içe komut. Sonuç $\frac{2(x^2 + 1) - (2x)^2}{(x^2 + 1)^2}$ doğru ama sadeleşmemiş. Pay $2 - 2x^2$.
- **`h := turev(x^4, x)`** ve **`deger(h, x, 3)`** → 108: tanımlar komut sonuçlarını da tutabiliyor.

SymPy ile bağımsız kontrol:

```
$ python3 -c "
from sympy import *; x = symbols('x')
print(isprime(2**127 - 1), isprime(2**128 + 1), isprime(2**521 - 1))
f = x**3 - 2*x + 1; print(expand(f*(x**2 - 1)), gcd(f, x**2 - 1))
p = expand((x - 1)**5*(x + 3)); print(factor(gcd(p, diff(p, x))))
print(simplify(diff(ln(x**2 + 1), x, 2) - (2*(x**2 + 1) - (2*x)**2)/(x**2 + 1)**2), diff(f, x).subs(x, Rational(1, 2)), f.subs(x, Rational(1, 2)))
print(simplify(diff(x**2*sin(x), x) - (cos(x)*x**2 + 2*x*sin(x))), simplify(diff(exp(x)/x, x) - (x*exp(x) - exp(x))/x**2))"
True False True
x**5 - 3*x**3 + x**2 + 2*x - 1 x - 1
(x - 1)**4
0 -5/4 1/8
0 0
```

---

## 4. Sınırlar

Oturumun iki satırı, bu sistemin nerede durduğunu açıkça gösteriyor:

```
> turev(f, x) + 1 - 3*x^2
  3*x^2 - 1 - 3*x^2
> genislet((x + 1)^3) - x^3 - 1
  x^3 + 3*x + 3*x^2 + 1 - x^3 - 1
```

İkisi de basit: ilki $-1$, ikincisi $3x^2 + 3x$. Kural tabanlı sadeleştirici göremiyor, çünkü birbirini götüren terimler ikili ağaçta **uzak**: $3x^2$ en solda, $-3x^2$ en sağda, aralarında başka düğümler var. `A + B - A -> B` kuralı yalnız komşu terimleri buluyor. Ders 12.12'nin Alıştırma 2'sinde gördüğümüz sorun.

Aynı ifadeler `genislet` ile doğru çıkıyor:

```
> genislet(turev(f, x) + 1 - 3*x^2)
  -1
> genislet(genislet((x + 1)^3) - x^3 - 1)
  3*x^2 + 3*x
```

Gerçek bir CAS'ın bu ikisini birleştirmesinin yolu, **n-li toplam ve çarpım düğümleri**: `Add(3*x^2, -1, -3*x^2)` bir terim listesi. Oluşturulurken terimler sıralanıp aynı "monomlar" (katsayı dışında aynı terimler) toplanıyor. Bu, polinom kanonik formunun polinom olmayan ifadelere genişletilmiş hali: $2\sin(x) + 3\sin(x) = 5\sin(x)$, `sin(x)`'i bir "değişken" sayarak. SymPy, Mathematica ve Maxima'nın çekirdekleri böyle. Bizim ikili ağacımız, derleyicinin AST'sine yakın kalsın diye seçildi (Ders 12.11).

Diğer bilinen eksikler:

- Polinom komutları tek değişkenli: `genislet((x + y)^2)` "polinom değil" diyor. Çok değişkenli polinomlar Ders 12.7'deki seyrek temsille (üs vektörleri) yazılabilir.
- Kesirli fonksiyonlar ($\frac{x^2 - 1}{x - 1} = x + 1$) için `ebob` ile pay ve paydayı sadeleştiren bir `sadelestir_kesir` yok (Alıştırma 1).
- Hata mesajları ayrıştırıcının iç durumunu yansıtıyor (Ders 12.11).
- Bellek: her işlem yeni ağaçlar kuruyor. Uzun oturumlarda sorun değil, büyük türevlerde (Ders 12.13) sorun.

---

## 5. Faz 12'nin özeti

| ders | parça | bir sonraki faza bağlantı |
| --- | --- | --- |
| 12.2–12.4 | limb dizileri, Karatsuba, Algoritma D | Faz 13: `BigInt` sınıfı ve operatör aşırı yükleme |
| 12.5 | Montgomery, Barrett, RSA | kriptografi kütüphaneleri, sabit zamanlı kod |
| 12.6 | kesirler, Bareiss | Faz 6.28: tamsayı lineer cebiri |
| 12.7–12.8 | polinomlar, PRS, katsayı şişmesi | Faz 19: karar prosedürleri |
| 12.9 | FFT, NTT | Faz 19: SPIRAL ve FFTW'nin kod üretimi |
| 12.10 | $GF(p)[x]$, Rabin, CRC | Faz 5.19'un teorisi; hata düzelten kodlar |
| 12.11 | ayrıştırıcı ve AST | Faz 15: derleyici ön yüzü |
| 12.12 | yeniden yazma, sonlanma, konfluens | Faz 16.10: yerel optimizasyonlar; Faz 19.2: terim yeniden yazma |
| 12.13 | sembolik türev | Faz 19.22: otomatik türev kodu |
| 12.14 | mini CAS | Faz 13.30: aynı CAS, C++'ta OOP ve Visitor ile |

Fazın bir cümlelik özeti: **kesinliğin bedeli büyüme**. Büyük sayılar büyüyor (12.4'teki 100000!), kesirler büyüyor (12.6'daki bölmesiz eleme), polinom kalanları büyüyor (12.8'deki 1.7 milyon basamak), türevler büyüyor (12.13'teki 1.7 milyon düğüm). Fazın her dersindeki asıl algoritma, bu büyümeyi kontrol altında tutmanın bir yolu: Karatsuba ve FFT, EBOB ile sadeleştirme, Bareiss ve alt-sonuçlar, modüler yöntemler, kanonik formlar.

---

## Alıştırmalar

**1** – `sadelestir_kesir(f / g)`: pay ve paydayı $\mathbb{Q}[x]$'e çevir, EBOB'a böl, sonucu geri yaz. `(x^2 - 1)/(x - 1)` → `x + 1`. Ders 12.12'deki `A / A -> 1` kuralı ile karşılaştır: hangi $x$ değerlerinde bu sadeleştirme "yanlış"?

**2** – `bn_carp`'a bir eşik ekle: iki sayı da 1000 limb'den büyükse Ders 12.9'daki `bn_carp_ntt`'yi çağır. `fakt(100000)`'i binary splitting ile yaz (Ders 12.9, Alıştırma 3) ve süreyi ölç.

**3** – `topla` düğümlerini n-li yap: `TOPLA` bir çocuk dizisi tutsun. Oluşturulurken iç içe toplamları düzleştir, terimleri `i_kars` ile sırala, aynı terimleri (sayı katsayısı dışında) birleştir. Bölüm 4'teki iki örnek ne oluyor? `ifade.c`'de hangi fonksiyonlar değişiyor?

**4** – Çok değişkenli `genislet`: Ders 12.7'deki `seyrek`'i üs vektörleriyle genişlet (`uint8_t us[4]`: $x, y, z, w$). `genislet((x + y + z)^5)` kaç terim? Formülle kontrol et.

**5** – Bir `coz(f, x)` komutu: $f$ derece 1 veya 2 ise kökleri kesin bulsun ($\sqrt{\ }$ gerekirse `sqrt(...)` düğümü olarak bıraksın). Derece 3 ve üstü için ne yapılabilir? (Rasyonel kök teoremi: $\pm$ sabit terimin bölenleri / baş katsayının bölenleri.)

<details>
<summary>Cevaplar</summary>

**1** – $\gcd(x^2 - 1, x - 1) = x - 1$, pay $(x^2 - 1)/(x - 1) = x + 1$, payda $1$. "Yanlış" olduğu yer $x = 1$: özgün ifade orada tanımsız, sadeleşmiş hali 2. Bu, `A / A -> 1` ile aynı türden bir tanım kümesi genişlemesi, ama EBOB ile sistematik: ortak çarpanın kökleri tam olarak sadeleştirmenin kaldırdığı tekil noktalar. SymPy'nin `cancel`'ı da aynı şeyi yapıyor.

**2** – Ders 12.9'daki kesişme 512–1024 limb arası. Binary splitting'in üst seviyelerinde sayılar on binlerce limb ve NTT orada Karatsuba'dan 5–10 kat hızlı. Ders 12.4'te 2.78 saniye süren 100000! hesabı, binary splitting + NTT ile yüz milisaniyeler mertebesine inmeli (onluk dönüşüm hâlâ $O(n^2)$ ve 3.5 saniye; onu da böl ve yönet ile hızlandırmak gerekiyor). Ölçüm senin.

**3** – `3*x^2 - 1 - 3*x^2`: düzleştirilmiş terimler $\{3x^2, -1, -3x^2\}$; aynı monom $x^2$ için katsayılar toplanıyor: $3 - 3 = 0$, terim düşüyor, sonuç $-1$. İkinci örnek $3x^2 + 3x$. Değişenler: `i_ikili` yerine bir `i_topla(dizi)`, `i_esit` ve `i_kars` (dizileri karşılaştırma), `yaz` (çocukları sırayla), `i_turev` (her terimin türevi), ve sadeleştiricinin desen eşleştirmesi: `A + 0` gibi desenler artık "dizide 0 var mı" sorusu. Bu son değişiklik en büyüğü. n-li düğümlerde desen eşleştirme ("AC-eşleştirme") NP-zor ve CAS'lar bunu özel durumlarla çözüyor.

**4** – $(x + y + z)^5$'in terim sayısı, toplamı 5 olan $(a, b, c)$ üçlülerinin sayısı: $\binom{5 + 2}{2} = 21$. Katsayılar multinom katsayıları $\frac{5!}{a!\,b!\,c!}$. Hepsinin toplamı $3^5 = 243$ ($x = y = z = 1$ koy).

**5** – Derece 1: $ax + b \Rightarrow x = -b/a$, `rat` ile kesin. Derece 2: $\Delta = b^2 - 4ac$. $\Delta$ tam kare bir kesirse ($\sqrt{p/q}$, $p$ ve $q$ tam kare) kökler rasyonel, değilse `sqrt(Δ)` düğümü kalıyor. Derece 3–4 için formüller var (Cardano, Ferrari) ama karmaşık. Derece 5 ve üstü için genel formül yok (Abel–Ruffini). Rasyonel kök teoremi bütün rasyonel kökleri sonlu bir aday kümesinden buluyor. Her bulunan kök `bol` ile çarpan olarak atılıyor. Kalan polinomun gerçek kökleri sayısal yöntemle (Ders 12.7 Alıştırma 2'deki Horner + Newton) yaklaşık bulunabilir.

</details>

---

## Kaynaklar

- Joel S. Cohen, *Computer Algebra and Symbolic Computation: Elementary Algorithms* ve *Mathematical Methods*, A K Peters, 2002–2003 (iki ciltlik bir CAS yapım kılavuzu).
- Joachim von zur Gathen ve Jürgen Gerhard, *Modern Computer Algebra* (3. baskı), Cambridge, 2013.
- Keith Geddes, Stephen Czapor, George Labahn, *Algorithms for Computer Algebra*, Kluwer, 1992.
- Aaron Meurer ve diğerleri, "SymPy: Symbolic Computing in Python", *PeerJ Computer Science*, 3:e103, 2017 (çekirdeğin tasarımı: n-li `Add`/`Mul`, otomatik sadeleştirme).
- Richard Fateman, "A Review of Mathematica", *Journal of Symbolic Computation*, 13(5), 1992 (CAS tasarım kararlarının eleştirel bir incelemesi).
- Maxima kaynak kodu ve belgeleri (maxima.sourceforge.io): Macsyma'nın 1960'lardan bugüne gelen Lisp çekirdeği.

**Sıradaki faz:** Faz 13, C++. Bu fazdaki büyük tamsayıyı operatör aşırı yüklemeli bir `BigInt` sınıfına, mini CAS'ı da OOP, Visitor ve akıllı pointer ile C++'a taşıyacağız.
