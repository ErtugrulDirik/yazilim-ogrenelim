---
title: "8.4 Yığın (stack)"
description: "Son giren ilk çıkar (LIFO): it, çek, tepe; aynı opak arayüzün dinamik dizi ve bağlı liste ile iki uygulaması ve 10 milyon işlemde 4 kat hız farkı; çağrı yığını, geri al (undo) ve tarayıcı geçmişi; açan parantezlerin konumlarını yığında tutarak (), [], {} eşleşmesini denetleyen ve hatanın yerini gösteren program; postfix (ters Leh) gösterimi ve yığınla ifade hesaplama, işlenen sırası ve hata durumları; infix'ten postfix'e Dijkstra'nın shunting-yard algoritması."
---

Ders 8.2 ve 8.3'te listeler, her yerden eklenip silinebilen esnek yapılardı. Bu ders tersini yapıyor: bir yapının **neye izin vermediği** onu güçlü kılıyor. **Yığın** (stack), sadece **bir uçtan** eklenip çıkarılabilen bir dizi: en son konan, ilk alınan. Bir tabak yığını gibi; alttaki tabağa ulaşmak için üsttekileri almak zorundasın.

Bu kısıt neden faydalı? Çünkü bilgisayar biliminde "en son başlayan iş ilk bitmeli" kuralına uyan problemler her yerde: iç içe parantezler, iç içe fonksiyon çağrıları (Ders 7.6, 7.11'deki çağrı yığını, adı buradan), iç içe ifadeler. Bu derste yığını Ders 8.1'deki ADT tarzında yazıp iki klasik problemi çözeceğiz: parantez denetimi ve ifade hesaplama. İkisi de Faz 15'teki derleyici ön yüzünün (ayrıştırıcının) küçük habercileri.

---

## 1. Arayüz

Yığının üç temel işlemi:

- **it** (push): tepeye bir eleman koy.
- **çek** (pop): tepedeki elemanı al ve çıkar.
- **tepe** (peek/top): tepedeki elemana çıkarmadan bak.

Kural: **LIFO** (last in, first out). `it(1), it(2), it(3)` ardından üç `çek` 3, 2, 1 verir.

```c
/* yigin.h: long tutan yigin ADT'si (Ders 8.1 tarzi opak tip) */
#ifndef YIGIN_H
#define YIGIN_H

#include <stdbool.h>
#include <stddef.h>

typedef struct Yigin Yigin;

Yigin *yigin_olustur(void);
void   yigin_yok_et(Yigin *y);
bool   yigin_it(Yigin *y, long x);       /* push; bellek yetmezse false */
bool   yigin_cek(Yigin *y, long *x);     /* pop;  bossa false, *x'e dokunmaz */
bool   yigin_tepe(const Yigin *y, long *x);
bool   yigin_bos_mu(const Yigin *y);
size_t yigin_boyut(const Yigin *y);

#endif
```

Boş bir yığından çekmek bir hata durumu (stack underflow). Bu arayüzde `yigin_cek` `bool` döndürüyor ve değeri bir çıkış parametresine (`long *x`) yazıyor; böylece "boş" durumu, yığında gerçekten bulunabilecek herhangi bir değerle (−1 gibi) karışmıyor. Elemanlar `long`: parantez denetleyicide **konum**, hesaplayıcıda **sayı** ve dönüştürücüde **karakter** tutacağız.

---

## 2. İki uygulama

**Dinamik dizi ile** (Ders 4.24): tepe dizinin sonu. `it` sona ekler, `çek` sondan alır; ikisi de amortize $O(1)$.

```c
/* yigin_dizi.c: dinamik dizi ile (Ders 4.24). Tepe = dizinin sonu. */
#include "yigin.h"
#include <stdlib.h>

struct Yigin { long *veri; size_t adet, kapasite; };

Yigin *yigin_olustur(void) { return calloc(1, sizeof(Yigin)); }

void yigin_yok_et(Yigin *y) { if (y) { free(y->veri); free(y); } }

bool yigin_it(Yigin *y, long x) {
    if (y->adet == y->kapasite) {
        size_t yeni = y->kapasite ? 2 * y->kapasite : 16;
        long *p = realloc(y->veri, yeni * sizeof *p);
        if (!p) return false;
        y->veri = p; y->kapasite = yeni;
    }
    y->veri[y->adet++] = x;
    return true;
}

bool yigin_cek(Yigin *y, long *x) {
    if (y->adet == 0) return false;
    *x = y->veri[--y->adet];
    return true;
}

bool yigin_tepe(const Yigin *y, long *x) {
    if (y->adet == 0) return false;
    *x = y->veri[y->adet - 1];
    return true;
}

bool   yigin_bos_mu(const Yigin *y) { return y->adet == 0; }
size_t yigin_boyut(const Yigin *y)  { return y->adet; }
```

**Bağlı liste ile** (Ders 8.2): tepe listenin başı. `it` başa ekleme, `çek` baştan silme; ikisi de kesin $O(1)$. Tek yönlü listenin $O(1)$ olan iki işlemi tam da yığının istedikleri, ve listenin zayıf olduğu her şeyi (sona erişim, ortaya erişim) yığın zaten yasaklıyor.

```c
/* yigin_liste.c: tek yonlu liste ile (Ders 8.2). Tepe = listenin basi. */
#include "yigin.h"
#include <stdlib.h>

typedef struct Dugum { long deger; struct Dugum *sonraki; } Dugum;
struct Yigin { Dugum *tepe; size_t adet; };

Yigin *yigin_olustur(void) { return calloc(1, sizeof(Yigin)); }

void yigin_yok_et(Yigin *y) {
    if (!y) return;
    while (y->tepe) { Dugum *s = y->tepe->sonraki; free(y->tepe); y->tepe = s; }
    free(y);
}

bool yigin_it(Yigin *y, long x) {               /* basa ekleme: O(1) */
    Dugum *d = malloc(sizeof *d);
    if (!d) return false;
    d->deger = x; d->sonraki = y->tepe;
    y->tepe = d; y->adet++;
    return true;
}

bool yigin_cek(Yigin *y, long *x) {             /* bastan silme: O(1) */
    if (!y->tepe) return false;
    Dugum *d = y->tepe;
    *x = d->deger;
    y->tepe = d->sonraki; y->adet--;
    free(d);
    return true;
}

bool yigin_tepe(const Yigin *y, long *x) {
    if (!y->tepe) return false;
    *x = y->tepe->deger;
    return true;
}

bool   yigin_bos_mu(const Yigin *y) { return y->tepe == NULL; }
size_t yigin_boyut(const Yigin *y)  { return y->adet; }
```

İkisi de aynı `yigin.h`'yi uyguluyor; bütün kullanıcı programları iki uygulamayla da aynı çıktıyı verdi (çıktıların özetleri birebir aynı, ASan ve UBSan temiz). Hız farkı:

```c
for (int tur = 0; tur < 10; tur++) {
    for (long i = 0; i < 1000000; i++) yigin_it(y, i);
    while (yigin_cek(y, &x)) toplam += x;
}
```

```
$ cc -std=c11 -O2 hiz.c yigin_dizi.c -o hiz_dizi && ./hiz_dizi
10 x (1M it + 1M cek): toplam=4999995000000  0.054 s
$ cc -std=c11 -O2 hiz.c yigin_liste.c -o hiz_liste && ./hiz_liste
10 x (1M it + 1M cek): toplam=4999995000000  0.234 s
```

Kağıt üzerinde liste daha iyi (amortize değil kesin $O(1)$), ölçümde dizi **4 kat** hızlı (Apple M2). Liste her `it`'te bir `malloc`, her `çek`'te bir `free` yapıyor; dizi kapasite bir kez oturduktan sonra hiç bellek ayırmıyor ve elemanlar yan yana (Ders 7.24). Ders 8.2'deki "çoğu zaman dizi" sonucunun bir örneği daha. Liste sürümünün tek avantajı: en kötü durumda bile hiçbir `it` uzun sürmüyor (dizi büyürken bir `realloc` milyonlarca elemanı kopyalayabilir); gerçek zamanlı sistemlerde bu önemli olabilir.

### Yığın her yerde

- **Çağrı yığını** (Ders 7.6, 7.11): her fonksiyon çağrısı bir çerçeve iter, her `ret` bir çerçeve çeker. Özyineleme bu sayede çalışıyor; Ders 8.6'da özyinelemeli bir fonksiyonu kendi yığınımızla döngüye çevireceğiz.
- **Geri al** (undo): her düzenleme bir yığına itilir, Ctrl+Z en sonuncuyu çeker. "Yinele" (redo) ikinci bir yığın.
- **Tarayıcıdaki geri düğmesi**: ziyaret edilen sayfaların yığını.
- **Yığın makineleri** (Ders 7.2): JVM, WebAssembly, Python'un bayt kodu yorumlayıcısı ve Ders 7.29'daki x87 hesaplarını bir işlenen yığınında yapar. Bölüm 4'teki hesaplayıcı tam olarak böyle bir makine.

---

## 3. Parantez denetleyici

Bir kod parçasında `()`, `[]`, `{}` doğru eşleşiyor ve doğru iç içe mi? `f(a[i])` doğru, `f(a[i)]` yanlış. Gözlem: bir kapanan parantez, **en son açılmış ve henüz kapanmamış** parantezle eşleşmeli. "En son açılan" demek yığının tepesi demek.

Algoritma: soldan sağa oku. Açan görünce yığına it. Kapanan görünce yığından çek ve türlerinin uyduğunu kontrol et. Sonda yığın boş olmalı. Hatayı **göstermek** için yığına karakterin kendisini değil **konumunu** itiyoruz.

```c
/* Parantez denetleyici: (), [], {} dogru eslesip ic ice mi? */
#include <stdio.h>
#include "yigin.h"

/* Dogruysa -1, degilse hatanin konumu (0'dan) */
static long denetle(const char *s) {
    Yigin *y = yigin_olustur();
    long sonuc = -1;
    for (long i = 0; s[i]; i++) {
        char c = s[i];
        if (c == '(' || c == '[' || c == '{') {
            yigin_it(y, i);                         /* acanin KONUMUNU sakla */
        } else if (c == ')' || c == ']' || c == '}') {
            long j;
            char beklenen = c == ')' ? '(' : c == ']' ? '[' : '{';
            if (!yigin_cek(y, &j) || s[j] != beklenen) { sonuc = i; break; }   /* fazla ya da yanlis kapanan */
        }
    }
    long j;
    if (sonuc == -1 && yigin_cek(y, &j)) sonuc = j;  /* kapanmamis acan kaldi */
    yigin_yok_et(y);
    return sonuc;
}

int main(void) {
    const char *ornekler[] = {
        "a[i] = f(b[j], {1, 2});",
        "if (x > (y + 1) { }",
        "dizi[(i + 1]",
        "return (a + b));",
        "{ [ ( ) ] ( ) }",
    };
    for (int k = 0; k < 5; k++) {
        long h = denetle(ornekler[k]);
        printf("%-26s ", ornekler[k]);
        if (h < 0) printf("dogru\n");
        else printf("HATA, konum %ld ('%c')\n", h, ornekler[k][h]);
    }
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra parantez.c yigin_dizi.c -o parantez && ./parantez
a[i] = f(b[j], {1, 2});    dogru
if (x > (y + 1) { }        HATA, konum 3 ('(')
dizi[(i + 1]               HATA, konum 11 (']')
return (a + b));           HATA, konum 14 (')')
{ [ ( ) ] ( ) }            dogru
```

Üç hata türü, üç farklı yer:

- **Kapanmamış açan** (`if (x > (y + 1) { }`): sona gelindiğinde yığında bir açan kalmış. İçteki `(` 8. konumda açılıp 14'te kapandı; dıştaki 3. konumdaki `(` hiç kapanmadı. Raporlanan, yığında kalan konum: 3.
- **Yanlış türde kapanan** (`dizi[(i + 1]`): `]` geldiğinde tepede `(` var.
- **Fazla kapanan** (`return (a + b));`): ikinci `)` geldiğinde yığın boş.

Her karakter bir kez işleniyor, her işlem $O(1)$: $O(n)$ zaman, en kötü $O(n)$ yığın (bütün karakterler açansa). Derleyicilerin "expected ')'" hatası, bu algoritmanın çok daha genel bir halinden (Faz 15'teki ayrıştırıcı) geliyor. (Bu sürüm string ve yorum içindeki parantezleri de sayıyor: `printf(")")` hatalı görünür. Gerçek bir denetleyici önce metni sözcüklere ayırır, Faz 15'teki lexer.)

---

## 4. Postfix ifadeler

Alışık olduğumuz yazım **infix** (araya ek): işleç işlenenlerin arasında, `3 + 4`. Sorunu: `3 + 4 * 2` ne demek? Öncelik kuralları (çarpma önce) ve parantezler gerekiyor.

Polonyalı mantıkçı Jan Łukasiewicz'in 1920'lerde önerdiği **postfix** (sona ek, "ters Leh gösterimi", RPN) yazımda işleç işlenenlerinden **sonra** gelir:

| Infix | Postfix |
| --- | --- |
| `3 + 4` | `3 4 +` |
| `(3 + 4) * 2` | `3 4 + 2 *` |
| `3 + 4 * 2` | `3 4 2 * +` |
| `5 + (1 + 2) * 4 - 3` | `5 1 2 + 4 * + 3 -` |

Postfix'te **parantez yok ve öncelik kuralı yok**; sıra her şeyi belirliyor. Ve bir yığınla hesaplamak çok basit: sayı görünce it; işleç görünce iki sayı çek, işlemi yap, sonucu it. Sonda yığında tek bir sayı kalmalı.

`5 1 2 + 4 * + 3 -` için yığının hali:

| Okunan | İşlem | Yığın (tepe sağda) |
| --- | --- | --- |
| `5` | it | `5` |
| `1` | it | `5 1` |
| `2` | it | `5 1 2` |
| `+` | 1 + 2 | `5 3` |
| `4` | it | `5 3 4` |
| `*` | 3 · 4 | `5 12` |
| `+` | 5 + 12 | `17` |
| `3` | it | `17 3` |
| `-` | 17 − 3 | `14` |

```c
/* Postfix (ters Leh) ifade hesaplayici: "3 4 + 2 *" = (3 + 4) * 2 */
#include <stdio.h>
#include <stdlib.h>
#include <ctype.h>
#include "yigin.h"

/* Basariliysa 0 ve *sonuc; hatada hata mesaji */
static const char *hesapla(const char *s, long *sonuc) {
    Yigin *y = yigin_olustur();
    const char *hata = NULL;
    while (*s && !hata) {
        if (isspace((unsigned char)*s)) { s++; continue; }
        if (isdigit((unsigned char)*s)) {
            char *son;
            long x = strtol(s, &son, 10);          /* Ders 3.17 */
            yigin_it(y, x);
            s = son;
            continue;
        }
        long b, a;                                  /* dikkat: once sagdaki (b) cekilir */
        if (!yigin_cek(y, &b) || !yigin_cek(y, &a)) { hata = "eksik islenen"; break; }
        switch (*s) {
        case '+': yigin_it(y, a + b); break;
        case '-': yigin_it(y, a - b); break;
        case '*': yigin_it(y, a * b); break;
        case '/': if (b == 0) hata = "sifira bolme"; else yigin_it(y, a / b); break;
        default:  hata = "bilinmeyen karakter";
        }
        s++;
    }
    if (!hata) {
        if (yigin_boyut(y) != 1) hata = "fazla islenen";
        else yigin_cek(y, sonuc);
    }
    yigin_yok_et(y);
    return hata;
}

int main(void) {
    const char *ifadeler[] = {
        "3 4 + 2 *",              /* (3 + 4) * 2          */
        "3 4 2 * +",              /* 3 + 4 * 2            */
        "5 1 2 + 4 * + 3 -",      /* 5 + (1 + 2) * 4 - 3  */
        "10 2 8 * + 3 -",         /* 10 + 2 * 8 - 3       */
        "2 3 4",                  /* operator eksik       */
        "1 +",                    /* islenen eksik        */
        "4 0 /",
    };
    for (int k = 0; k < 7; k++) {
        long r;
        const char *h = hesapla(ifadeler[k], &r);
        if (h) printf("%-22s -> hata: %s\n", ifadeler[k], h);
        else   printf("%-22s -> %ld\n", ifadeler[k], r);
    }
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra postfix.c yigin_dizi.c -o postfix && ./postfix
3 4 + 2 *              -> 14
3 4 2 * +              -> 11
5 1 2 + 4 * + 3 -      -> 14
10 2 8 * + 3 -         -> 23
2 3 4                  -> hata: fazla islenen
1 +                    -> hata: eksik islenen
4 0 /                  -> hata: sifira bolme
```

İnce bir nokta: **çekme sırası**. `10 3 -` için yığında `10 3` var (tepe 3). İlk çekilen sağ işlenen (`b = 3`), ikinci çekilen sol işlenen (`a = 10`), sonuç `a - b = 7`. Toplama ve çarpmada sıra fark etmez (değişme özelliği, Ders 6.21), çıkarma ve bölmede eder. Bu sırayı karıştırmak, yığın tabanlı hesaplayıcıların en klasik hatası.

Hata durumları da yığının durumundan okunuyor: işleç geldiğinde iki sayı yoksa "eksik işlenen", sonda birden fazla sayı varsa "fazla işlenen". Sıfıra bölme ayrıca kontrol ediliyor (Ders 7.28: x86'da SIGFPE). Bu programda taşma kontrolü yok; `a * b` taşabilir (Ders 3.8, 5.6).

HP'nin bilimsel hesap makineleri onlarca yıl RPN kullandı: parantez tuşu yok, her ara sonuç ekranda (yığında) görünüyor. PostScript ve Forth dilleri doğrudan postfix. Ve derleyiciler: bir ifadeyi postfix sırasında yazmak, onu bir yığın makinesi için **koda çevirmek** demek; Faz 15–16'da bir ifade ağacını (Ders 8.7) postorder gezerek tam bunu yapacağız.

---

## Alıştırmalar

**1** – **Shunting-yard** (Dijkstra, 1961): infix bir ifadeyi postfix'e çeviren algoritma. Sayıları doğrudan çıktıya yaz; işleçleri bir yığında beklet: yeni bir işleç geldiğinde, yığının tepesindeki işleç ondan **önce** yapılmalıysa (önceliği büyük ya da eşit, sol birleşmeli işleçler için) önce onu çıktıya aktar. `(` yığına girer, `)` gelince `(`'ya kadar her şey çıktıya aktarılır. Tek haneli sayılar ve `+ - * /` için yaz. `8 - 3 - 2` neden `8 3 - 2 -` vermeli, `8 3 2 - -` değil?

**2** – **Min yığını**: `it`, `çek` ve `en_kucuk` işlemlerinin üçü de $O(1)$ olsun. İpucu: ikinci bir yığın. `5, 3, 7, 2, 8` itip sonra dört kez çekerken her adımda `en_kucuk` ne döner?

**3** – Bir string'in parantezleri **sadece** `()` ise, yığın olmadan, tek bir tamsayı sayaçla denetlenebilir. Nasıl? Üç tür parantezde neden sayaçlar yetmiyor? (`([)]`'i düşün.)

**4** – Postfix hesaplayıcıda `yigin_cek(y, &b)` ve `yigin_cek(y, &a)`'nın sırasını değiştirirsen `10 3 -`, `8 2 /` ve `3 4 +` ne verir?

**5** – Ders 7.11'deki çağrı yığını ile bu dersteki yığın ADT'si arasındaki benzerlik ve farklar neler? Çağrı yığınında "boş yığından çekme" ve "taşma" neye karşılık gelir?

<details>
<summary>Cevaplar</summary>

**1** –

```c
static int oncelik(char op) { return (op == '*' || op == '/') ? 2 : (op == '+' || op == '-') ? 1 : 0; }

static void cevir(const char *s, char *cikti) {
    Yigin *ops = yigin_olustur(); long t; int k = 0;
    for (; *s; s++) {
        char c = *s;
        if (isspace((unsigned char)c)) continue;
        if (isdigit((unsigned char)c)) { cikti[k++] = c; cikti[k++] = ' '; }
        else if (c == '(') yigin_it(ops, c);
        else if (c == ')') { while (yigin_cek(ops, &t) && t != '(') { cikti[k++] = (char)t; cikti[k++] = ' '; } }
        else {
            while (yigin_tepe(ops, &t) && t != '(' && oncelik((char)t) >= oncelik(c)) {
                yigin_cek(ops, &t); cikti[k++] = (char)t; cikti[k++] = ' ';
            }
            yigin_it(ops, c);
        }
    }
    while (yigin_cek(ops, &t)) { cikti[k++] = (char)t; cikti[k++] = ' '; }
    cikti[k ? k - 1 : 0] = 0;      /* sondaki boslugu sil */
    yigin_yok_et(ops);
}
```

```
(3 + 4) * 2            -> 3 4 + 2 *
3 + 4 * 2              -> 3 4 2 * +
5 + (1 + 2) * 4 - 3    -> 5 1 2 + 4 * + 3 -
8 - 3 - 2              -> 8 3 - 2 -
2 * (3 + 4) * 5        -> 2 3 4 + * 5 *
```

Çıktıları Bölüm 4'teki hesaplayıcıya verirsen infix ifadenin değerini bulursun: ikisi birlikte tam bir ifade hesaplayıcı. `8 - 3 - 2`: çıkarma **sol birleşmeli**, yani $(8 - 3) - 2 = 3$. İkinci `-` geldiğinde tepedeki `-` ile önceliği **eşit**; `>=` sayesinde önce o çıktıya aktarılıyor: `8 3 - 2 -` = 3. `>` kullansaydık `8 3 2 - -` = $8 - (3 - 2) = 7$ çıkardı: sağ birleşmeli bir işlecin (üs alma, `^`) davranışı. Algoritmanın tek satırındaki `>=`/`>` seçimi birleşmeliliği belirliyor.

**2** – Asıl yığının yanında ikinci bir yığın, her seviyede **o ana kadarki** minimumu tutar: `it(x)` ikinciye `min(x, ikincinin tepesi)` iter, `çek` ikisinden de çeker, `en_kucuk` ikincinin tepesine bakar. Hepsi $O(1)$.

```
it 5 -> min 5
it 3 -> min 3
it 7 -> min 3
it 2 -> min 2
it 8 -> min 2
cek    -> min 2
cek    -> min 3
cek    -> min 3
cek    -> min 5
```

Püf noktası: yığın sadece tepeden değiştiği için, her seviyenin minimumu **altındaki** elemanlara bağlı ve o elemanlar çekilene kadar değişmiyor. Aynı fikir bir kuyruk için çalışmaz (iki uçtan değişiyor; Ders 8.5'in bir alıştırması).

**3** – Sayaç: `(`'da artır, `)`'da azalt; hiçbir zaman negatife düşmemeli ve sonda 0 olmalı. Tek tür parantezde "en son açılan" hakkında bilinmesi gereken tek şey **kaç tane** açık olduğu. Üç türde her biri için ayrı sayaç tutsan `([)]`'de sayaçlar hep geçerli (her biri 1'e çıkıp 0'a iniyor) ama ifade yanlış: `)` geldiğinde en son açılan `[`. Sayaçlar türleri sayıyor ama **sırayı** unutuyor; sırayı hatırlamak yığının işi. (Faz 14'te bunun biçimsel hali var: iki dil de sonlu otomatla tanınamaz, çünkü iç içe derinlik sınırsız; tek tür parantez bir sayaçla yetinen bir makineyle, çok türlüsü ancak bir yığınlı otomatla tanınır.)

**4** – Ters sırada `a` önce (tepe) çekilir: `a = 3, b = 10`, `10 3 -` → $3 - 10 = -7$; `8 2 /` → $2 / 8 = 0$ (tamsayı bölmesi); `3 4 +` → 7 (değişmeli işlem, doğru görünüyor). Toplama ve çarpmayla yapılan testler bu hatayı yakalamaz; test kümesinde değişmeli olmayan işlemler mutlaka olmalı.

**5** – Benzerlik: ikisi de LIFO; `call` bir çerçeve iter (dönüş adresi, kaydedilen register'lar, yerel değişkenler), `ret` çeker. En son çağrılan fonksiyon ilk döner, tıpkı en son açılan parantezin ilk kapanması gibi. Farklar: çağrı yığınının elemanları farklı boyutlarda (her çerçeve kendi boyunda), donanım ve ABI tarafından yönetiliyor (`sp` register'ı, Ders 7.10), ve büyüklüğü sabit (tipik 8 MB). "Boş yığından çekme": `_start`'ın `ret` yapması (Ders 7.18, Alıştırma 1): yığında dönüş adresi yok, çöküş. **Taşma** (stack overflow): çok derin özyineleme (Ders 8.2, Alıştırma 1) yığının sonundaki koruma sayfasına çarpar, sayfa hatası, SIGSEGV. Bizim dinamik dizi yığınımız ise heap'te büyüyebiliyor; Ders 8.6'da derin özyinelemeyi bu yüzden ona taşıyacağız.

</details>

---

## Kaynaklar

- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 4.2–4.4: yığın ADT'si, postfix hesaplama, infix'ten postfix'e.
- Edsger Dijkstra, "Algol 60 translation" (Mathematisch Centrum raporu, 1961): shunting-yard algoritmasının ilk yayını.
- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 2.2.1: yığınlar, kuyruklar ve deque'ler.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 10.1.

**Sıradaki ders:** Kuyruk ve deque. Halka tampon (ring buffer), 2'nin kuvveti boyutla mod yerine maske.
