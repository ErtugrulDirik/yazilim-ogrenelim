---
title: "8.7 İkili ağaç"
description: "Kök, çocuk, yaprak, yükseklik; C'de ikili ağaç düğümü ve yana yatık çizim; dört gezinme (önek, içek, sonek, seviye sırası) aynı ağaç üzerinde ve her birinin ne işe yaradığı; içek gezinmeyi açık yığınla yazıp adım adım ilerleyen bir yineleyiciye çevirme; postfix ifadeden yığınla ifade ağacı kurma, sonek gezinmeyle hesaplama, içek ile tam parantezli ve önek ile Lisp gösterimi: derleyicilerin AST'sine ilk bakış."
---

Şimdiye kadarki yapıların hepsi doğrusaldı: her elemanın en fazla bir "sonraki"si vardı. Ağaçta bir düğümün birden fazla çocuğu olabilir. Bu küçük değişiklik çok şeyi mümkün kılıyor: hiyerarşiler (dosya sistemi, HTML), $O(\log n)$'de arama (Ders 8.8–8.11) ve programların kendisi. Bir derleyici kaynak kodu okuduğunda ilk ürettiği şey bir ağaç: **soyut sözdizimi ağacı** (AST). Bu ders ikili ağacın temel işlemlerini yazıyor ve dersin sonunda küçük bir AST kuruyor.

---

## 1. Terimler

Ders 6.30'da ağacı "döngüsü olmayan bağlantılı graf" diye tanımladık. Veri yapısı olarak ağaç **köklü**: bir düğüm kök seçilmiş ve kenarlar yukarıdan aşağı yönlü.

```
          A            A: kök (root)
        /   \          B, C: A'nın çocukları (children); A onların ebeveyni (parent)
       B     C         D, G, F: yaprak (leaf), çocuğu yok
      / \     \        B'nin alt ağacı (subtree): B, D, E, G
     D   E     F       G'nin derinliği (depth): kökten uzaklığı = 3
        /              ağacın yüksekliği (height): en derin yaprağın derinliği = 3
       G
```

**İkili ağaç** (binary tree): her düğümün en fazla iki çocuğu var ve bunlar **sol** ve **sağ** diye ayrılıyor. Ayrım önemli: sadece sol çocuğu olan bir düğüm ile sadece sağ çocuğu olan düğüm farklı ağaçlar. Yukarıda C'nin sadece sağ çocuğu var.

Tanımın en kullanışlı hali özyinelemeli: bir ikili ağaç ya **boştur**, ya da bir kök ve iki ikili ağaçtan (sol ve sağ alt ağaç) oluşur. Ağaç üzerindeki neredeyse her fonksiyon bu tanımı birebir izler: "boşsa şunu döndür, değilse kökle bir şey yap ve iki alt ağaçta kendini çağır." Ağaç hakkında bir şey ispatlamanın yolu da aynı: Ders 6.4'teki güçlü tümevarımı alt ağaçlara uygulamak ("iki alt ağaç için doğruysa bütün ağaç için de doğru"); buna **yapısal tümevarım** denir.

---

## 2. C'de düğüm ve ilk fonksiyonlar

```c
/* Ikili agac: dugum, dort gezinme, yukseklik, yana yatik cizim */
#include <stdio.h>
#include <stdlib.h>

typedef struct Dugum {
    char deger;
    struct Dugum *sol, *sag;
} Dugum;

static Dugum *d(char deger, Dugum *sol, Dugum *sag) {
    Dugum *n = malloc(sizeof *n);
    n->deger = deger; n->sol = sol; n->sag = sag;
    return n;
}
```

Boş ağaç `NULL`. Ders 8.2'deki liste düğümünün iki pointer'lı hali; çift yönlü listeden farkı, iki pointer'ın da **aşağı** bakması.

Yükseklik ve boyut, tanımın doğrudan çevirisi:

```c
static int yukseklik(const Dugum *n) {      /* bos agac: -1, tek dugum: 0 */
    if (!n) return -1;
    int a = yukseklik(n->sol), b = yukseklik(n->sag);
    return 1 + (a > b ? a : b);
}

static int boyut(const Dugum *n) { return n ? 1 + boyut(n->sol) + boyut(n->sag) : 0; }

static void serbest(Dugum *n) { if (!n) return; serbest(n->sol); serbest(n->sag); free(n); }
```

`serbest`'te sıra önemli: önce çocuklar, sonra düğümün kendisi. Önce `free(n)` deyip sonra `n->sol`'a erişmek, Ders 8.2'deki kullanım-sonrası-serbest hatası.

Boş ağacın yüksekliğini $-1$ almak bir tercih, ama tutarlı bir tercih: tek düğümlü ağacın yüksekliği $1 + \max(-1, -1) = 0$ çıkıyor ve formül özel durum istemiyor.

### Ağacı çizmek

Terminalde ağaç çizmenin en kolay yolu onu **yana yatırmak**: sağ alt ağaç üstte, kök solda, her seviye dört boşluk içeride.

```c
/* Yana yatik cizim: sag alt agac ustte, kok solda. Basini sola cevirip oku. */
static void ciz(const Dugum *n, int girinti) {
    if (!n) return;
    ciz(n->sag, girinti + 4);
    printf("%*s%c\n", girinti, "", n->deger);
    ciz(n->sol, girinti + 4);
}
```

`%*s` genişliği argümandan alıyor: `girinti` kadar boşluk. Hata ayıklarken bu fonksiyon her ağaç dersinde işimize yarayacak.

---

## 3. Dört gezinme

Bir ağacın bütün düğümlerini ziyaret etmenin birden fazla doğal sırası var. Özyinelemeli üçü, kök ile alt ağaçların sırasında ayrılıyor:

```c
static void onek(const Dugum *n)  { if (!n) return; printf(" %c", n->deger); onek(n->sol); onek(n->sag); }
static void icek(const Dugum *n)  { if (!n) return; icek(n->sol); printf(" %c", n->deger); icek(n->sag); }
static void sonek(const Dugum *n) { if (!n) return; sonek(n->sol); sonek(n->sag); printf(" %c", n->deger); }
```

| Gezinme | Sıra | Ne zaman |
| --- | --- | --- |
| **Önek** (preorder) | kök, sol, sağ | Ağacı kopyalamak, dışa yazmak (kök önce gelmeli ki okuyan yeniden kurabilsin) |
| **İçek** (inorder) | sol, kök, sağ | İkili arama ağacında elemanları **sıralı** vermek (Ders 8.8), ifadeyi infix yazmak |
| **Sonek** (postorder) | sol, sağ, kök | Çocukların sonucu gerektiğinde: serbest bırakmak, yükseklik, ifade hesaplamak |
| **Seviye sırası** (level order) | yukarıdan aşağı, soldan sağa | Kökten uzaklığa göre işlem, en sığ yaprağı bulmak |

Dördüncüsü özyinelemeli değil: Ders 8.5'teki BFS'in ağaç hali. Ağaçta döngü olmadığı için "ziyaret edildi mi" kontrolüne bile gerek yok:

```c
/* Seviye sirasi: kuyruk (Ders 8.5). Burada basit bir dizi-kuyruk yeterli. */
static void seviye(const Dugum *kok) {
    const Dugum *kuyruk[64]; int bas = 0, son = 0;
    if (kok) kuyruk[son++] = kok;
    while (bas < son) {
        const Dugum *n = kuyruk[bas++];
        printf(" %c", n->deger);
        if (n->sol) kuyruk[son++] = n->sol;
        if (n->sag) kuyruk[son++] = n->sag;
    }
}
```

(Sabit boyutlu dizi, yedi düğümlük örnek için yeterli; gerçek kodda Ders 8.5'teki deque.)

```c
int main(void) {
    /*        A
            /   \
           B     C
          / \     \
         D   E     F
            /
           G                      */
    Dugum *kok = d('A', d('B', d('D', NULL, NULL), d('E', d('G', NULL, NULL), NULL)),
                        d('C', NULL, d('F', NULL, NULL)));
    printf("onek  (pre)  :"); onek(kok);   printf("\n");
    printf("icek  (in)   :"); icek(kok);   printf("\n");
    printf("sonek (post) :"); sonek(kok);  printf("\n");
    printf("seviye       :"); seviye(kok); printf("\n");
    printf("boyut=%d yukseklik=%d\n", boyut(kok), yukseklik(kok));
    ciz(kok, 0);
    serbest(kok);
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined agac.c -o agac && ./agac
onek  (pre)  : A B D E G C F
icek  (in)   : D B G E A C F
sonek (post) : D G E B F C A
seviye       : A B C D E F G
boyut=7 yukseklik=3
        F
    C
A
        E
            G
    B
        D
```

Elle kontrol etmenin bir yolu: ağacın etrafında, kökün solundan başlayıp saat yönünün tersine bir çizgi çek. Her düğümün yanından üç kez geçersin: solundan (inerken), altından (sol alt ağaçtan dönerken), sağından (çıkarken). Önek ilk geçişte, içek ikincide, sonek üçüncüde yazar.

Bütün gezinmeler $O(n)$: her düğüm bir kez ziyaret ediliyor. Özyinelemeli olanların ek belleği ağacın yüksekliği kadar çerçeve (Ders 8.6); seviye sırasınınki en kalabalık seviye kadar kuyruk.

---

## 4. Açık yığınla içek gezinme: yineleyici

Ders 8.6'nın tarifi: özyinelemeyi açık yığına çevir. İçek gezinmede dönüş noktası var (sol alt ağaç bitince kökü yazıp sağa geç), ama yapısı basit: **bir düğümden en sola kadar inen yolu yığına it.** Tepedeki düğüm, henüz yazılmamış en küçük düğüm. Onu çekip yazınca sıradaki, sağ alt ağacının en solundaki düğüm.

Bunu tek bir döngü yerine "bir sonrakini ver" fonksiyonu olarak yazarsak elimize bir **yineleyici** (iterator) geçiyor: gezinmeyi istediğin yerde durdurup devam ettirebilirsin.

```c
/* Icek gezinme acik yiginla (Ders 8.6): yineleyici olarak */
typedef struct { const Dugum *yigin[64]; int tepe; } Yineleyici;

static void sola_in(Yineleyici *it, const Dugum *n) {   /* n'den en sola kadar yolu it */
    for (; n; n = n->sol) it->yigin[it->tepe++] = n;
}
static void baslat(Yineleyici *it, const Dugum *kok) { it->tepe = 0; sola_in(it, kok); }
static const Dugum *sonraki(Yineleyici *it) {
    if (it->tepe == 0) return NULL;
    const Dugum *n = it->yigin[--it->tepe];
    sola_in(it, n->sag);                               /* sag alt agacin en kucugu siradaki */
    return n;
}
```

```c
    Yineleyici it; baslat(&it, kok);
    printf("icek (yineleyici):");
    for (const Dugum *n; (n = sonraki(&it)); ) printf(" %c", n->deger);
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined yineleyici.c -o yin && ./yin
icek (yineleyici): D B G E A C F
```

Yığında hiçbir zaman yükseklik + 1'den fazla düğüm yok. Her düğüm bir kez itilip bir kez çekildiği için bütün gezinme $O(n)$; tek bir `sonraki` çağrısı en kötü $O(h)$ ama amortize $O(1)$ (Ders 8.5, Alıştırma 2 ile aynı argüman). C++'ın `std::map` yineleyicisi aynı işi ebeveyn pointer'larıyla, yığınsız yapar (Ders 8.10).

---

## 5. İfade ağacı: AST'ye ilk bakış

Ders 8.4'te `5 1 2 + 4 * + 3 -` gibi postfix ifadeleri bir yığınla **hesapladık**. Aynı algoritma, yığına sayı yerine **ağaç** iterse ne olur? Sayı gelince tek düğümlü bir ağaç it; işlem gelince iki ağaç çek, onları çocuk yapan yeni bir düğüm kur, onu it. Sonunda yığında tek bir ağaç kalır: ifadenin yapısı.

```c
/* Ifade agaci: postfix'ten kur (yiginla), hesapla (sonek), yazdir (icek ve onek) */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum { SAYI, ISLEM } Tur;

typedef struct Ifade {
    Tur tur;
    long sayi;               /* tur == SAYI */
    char op;                 /* tur == ISLEM: + - * / */
    struct Ifade *sol, *sag;
} Ifade;

static Ifade *yeni_sayi(long x) {
    Ifade *e = calloc(1, sizeof *e); e->tur = SAYI; e->sayi = x; return e;
}
static Ifade *yeni_islem(char op, Ifade *sol, Ifade *sag) {
    Ifade *e = calloc(1, sizeof *e); e->tur = ISLEM; e->op = op; e->sol = sol; e->sag = sag; return e;
}

/* Ders 8.4'teki postfix hesaplayicinin aynisi; ama yigina sayi degil AGAC itiyoruz. */
static Ifade *postfixten_kur(const char *s) {
    Ifade *yigin[64]; int tepe = 0;
    while (*s) {
        if (isspace((unsigned char)*s)) { s++; continue; }
        if (isdigit((unsigned char)*s)) {
            char *son; long x = strtol(s, &son, 10); s = son;
            yigin[tepe++] = yeni_sayi(x);
        } else {
            if (tepe < 2) return NULL;                 /* (hata yonetimi kisa tutuldu) */
            Ifade *sag = yigin[--tepe], *sol = yigin[--tepe];
            yigin[tepe++] = yeni_islem(*s++, sol, sag);
        }
    }
    return tepe == 1 ? yigin[0] : NULL;
}
```

Düğümün iki türü var: yaprak (sayı) ve iç düğüm (işlem). `Tur` alanı hangisi olduğunu söylüyor; Ders 4.27'deki etiketli birliğin (tagged union) basit hali. Gerçek bir derleyicide türler onlarca (değişken, fonksiyon çağrısı, atama, `if`, `while`...) ve alanlar bir `union` içinde.

Ağacı kurduktan sonra üç gezinmenin üçü de anlamlı bir şey yapıyor:

```c
static long hesapla(const Ifade *e) {             /* sonek sira: once cocuklar */
    if (e->tur == SAYI) return e->sayi;
    long a = hesapla(e->sol), b = hesapla(e->sag);
    switch (e->op) {
    case '+': return a + b;
    case '-': return a - b;
    case '*': return a * b;
    default:  return a / b;
    }
}

static void infix(const Ifade *e) {                /* icek sira, tam parantezli */
    if (e->tur == SAYI) { printf("%ld", e->sayi); return; }
    printf("("); infix(e->sol); printf(" %c ", e->op); infix(e->sag); printf(")");
}

static void lisp(const Ifade *e) {                 /* onek sira */
    if (e->tur == SAYI) { printf("%ld", e->sayi); return; }
    printf("(%c ", e->op); lisp(e->sol); printf(" "); lisp(e->sag); printf(")");
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined ifade.c -o ifade && ./ifade
postfix: 2 3 4 * +            infix: (2 + (3 * 4))   lisp: (+ 2 (* 3 4))   = 14
postfix: 2 3 + 4 *            infix: ((2 + 3) * 4)   lisp: (* (+ 2 3) 4)   = 20
postfix: 8 3 - 2 -            infix: ((8 - 3) - 2)   lisp: (- (- 8 3) 2)   = 3
postfix: 5 1 2 + 4 * + 3 -    infix: ((5 + ((1 + 2) * 4)) - 3)   lisp: (- (+ 5 (* (+ 1 2) 4)) 3)   = 14
      3
  -
              4
          *
                  2
              +
                  1
      +
          5
```

Son ifadenin ağacı (yana yatık): kök `-`; sol alt ağacı `5 + (1 + 2) * 4`, sağı `3`.

Bu üç gösterim **aynı ağacın** üç gezinmesi:

- **Postfix** (sonek): girdi olarak verdiğimiz şey. Ağacı sonek sırayla yazınca geri elde ediliyor.
- **Infix** (içek): insanların yazdığı şey. Ama ağaçta saklı olan yapıyı göstermek için parantez gerekiyor; ağacın kendisinde parantez yok, yapı ağacın **şekli**.
- **Önek**: Lisp'in sözdizimi. Lisp programları doğrudan kendi AST'lerinin yazılmış hali.

Bir derleyicinin ilk yarısının işi, programcının yazdığı metni (infix, öncelikler, parantezler) bu ağaca çevirmek. Faz 15'te bunu yapan ayrıştırıcıyı (parser) yazacağız. Ağaç kurulduktan sonra parantezler, boşluklar, öncelik kuralları kayboluyor; geriye sadece **yapı** kalıyor. Bu yüzden "soyut" sözdizimi ağacı. Sonraki her aşama bu ağaç üzerinde çalışır: tip denetimi bir gezinme, sabit katlama (Faz 16; `2 + 3` yerine `5` yazmak) bir sonek gezinme, kod üretimi bir sonek gezinme. `hesapla` aslında küçük bir **yorumlayıcı** (interpreter); `printf` yerine assembly komutları yazan bir sonek gezinme ise küçük bir **derleyici**.

---

## Alıştırmalar

**1** – Bir ağacın önek gezinmesi `A B D E G C F`, içek gezinmesi `D B G E A C F`. Ağacı çiz (sadece bu iki diziden). Önek dizisinin ilk elemanı neden kök, ve içek dizisi ağacı nasıl ikiye bölüyor? Bunu yapan özyinelemeli `kur(onek, icek, n)` fonksiyonunu yaz ve sonek gezinmeyi yazdırarak kontrol et.

**2** – `infix` her işlemi paranteze alıyor. Sadece **gereken** parantezleri koyan bir sürüm yaz: `*` ve `/`, `+` ve `-`'den önce gelir, ve hepsi soldan birleşir. `5 1 2 + 4 * + 3 -`, `8 3 - 2 -`, `8 3 2 - -` ve `1 2 3 + +` için ne yazdırmalı?

**3** – Yüksekliği $h$ olan bir ikili ağaçta en fazla kaç düğüm olabilir? Tümevarımla ispatla. Buradan $n$ düğümlü bir ikili ağacın yüksekliği için bir **alt** sınır çıkar.

**4** – Bir ağacın **aynasını** (her düğümün sol ve sağ çocuğunu değiştirerek) yerinde alan fonksiyonu yaz. Bölüm 3'teki ağacın aynasının içek gezinmesi ne?

**5** – Önek gezinmeyi açık yığınla yaz. Hangi çocuğu önce itmelisin?

<details>
<summary>Cevaplar</summary>

**1** – Önek kökü **önce** yazdığı için ilk eleman kök: `A`. İçekte `A`'nın solundakiler (`D B G E`) sol alt ağaç, sağındakiler (`C F`) sağ alt ağaç. Sol alt ağaçta 4 düğüm olduğu için önek dizisinde `A`'dan sonraki 4 eleman (`B D E G`) sol alt ağacın öneki, kalan (`C F`) sağınki. Aynı işlem her alt ağaçta tekrarlanıyor:

```c
static Dugum *kur(const char *on, const char *ic, int n) {
    if (n == 0) return NULL;
    int k = (int)(strchr(ic, on[0]) - ic);          /* kok icekte nerede */
    return d(on[0], kur(on + 1, ic, k), kur(on + 1 + k, ic + k + 1, n - k - 1));
}
```

```
sonek: D G E B F C A
```

Bölüm 3'teki ağacın ta kendisi. Değerler farklı olmalı (aynı harf iki kez geçerse `strchr` yanlış yeri bulur). Sadece önek ve sonekten kurmak genelde **mümkün değil**: tek çocuklu bir düğümün çocuğunun sol mu sağ mı olduğu ikisinden de anlaşılmıyor.

**2** – Bir alt ifadenin paranteze ihtiyacı, kendi önceliğinin ebeveyninin önceliğinden düşük olmasından ya da eşit öncelikle **sağ** çocuk olmasından (soldan birleşme) kaynaklanıyor:

```c
static int onc(char op) { return op == '+' || op == '-' ? 1 : 2; }
static void yaz(const Ifade *e, int ust, int sagda) {
    if (e->tur == SAYI) { printf("%ld", e->sayi); return; }
    int p = onc(e->op);
    int par = p < ust || (p == ust && sagda);     /* sagdaki esit oncelik: 8 - (3 - 2) */
    if (par) printf("(");
    yaz(e->sol, p, 0); printf(" %c ", e->op); yaz(e->sag, p, 1);
    if (par) printf(")");
}
```

```
5 1 2 + 4 * + 3 -    -> 5 + (1 + 2) * 4 - 3
8 3 - 2 -            -> 8 - 3 - 2
8 3 2 - -            -> 8 - (3 - 2)
2 3 4 * +            -> 2 + 3 * 4
2 3 + 4 *            -> (2 + 3) * 4
1 2 3 + +            -> 1 + (2 + 3)
```

Son satırda parantez matematiksel olarak gereksiz, çünkü toplama birleşmeli. Ama kural onu bilmiyor ve bu bilinçli: C'de `1 + (2 + 3)` ile `(1 + 2) + 3` her zaman aynı değil (işaretli taşma, Ders 3.8; `double`'da yuvarlama, Ders 3.14). Ağacın yapısını değiştirmeyen tek güvenli yazım, ağacın yapısını koruyan yazım. Faz 18'deki kod üreticiler (C kodu yazan programlar) bu fonksiyonun bir benzerini kullanır.

**3** – En fazla $2^{h+1} - 1$. Güçlü tümevarım (Ders 6.4) yükseklik üzerinde: $h = 0$ için tek düğüm, $2^1 - 1 = 1$. Yüksekliği $h$ olan bir ağacın iki alt ağacının yüksekliği en fazla $h - 1$, dolayısıyla her birinde en fazla $2^h - 1$ düğüm var; toplam en fazla $1 + 2(2^h - 1) = 2^{h+1} - 1$. Tersinden: $n \le 2^{h+1} - 1$ ise $h \ge \log_2(n+1) - 1$, yani $h \ge \lfloor \log_2 n \rfloor$. Bir ikili ağaç ne kadar iyi düzenlenirse düzenlensin, $n$ düğümü $\log_2 n$'den daha az seviyeye sığdıramazsın. Ders 8.8–8.10'daki dengeli ağaçların bütün amacı bu alt sınıra yakın kalmak.

**4** –

```c
static void ayna(Dugum *n) { if (!n) return; Dugum *t = n->sol; n->sol = n->sag; n->sag = t; ayna(n->sol); ayna(n->sag); }
```

```
ayna icek: F C A E G B D
```

Orijinal içek gezinmenin tam tersi; çünkü aynada "sol, kök, sağ" orijinaldeki "sağ, kök, sol" oluyor. (Önek ve sonek için böyle basit bir ilişki yok.)

**5** – Kökü çek ve yazdır, sonra önce **sağ**, sonra **sol** çocuğu it. Yığın son itileni ilk verdiği için sol alt ağaç önce işlenir:

```c
static void onek_yigin(const Dugum *kok) {
    const Dugum *y[64]; int t = 0; if (kok) y[t++] = kok;
    while (t) { const Dugum *n = y[--t]; printf(" %c", n->deger);
        if (n->sag) y[t++] = n->sag; if (n->sol) y[t++] = n->sol; }
}
```

```
onek yigin: A B D E G C F
```

Önek, açık yığına en kolay çevrilen gezinme: dönüş noktası yok, çünkü kök çocuklardan **önce** işleniyor ve sonra yapılacak iş kalmıyor (Ders 8.6, "dönüşten sonra iş yoksa"). Bu kodda yığını kuyrukla değiştirirsen (ve sol çocuğu önce eklersen) seviye sırası elde edersin.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 1, Bölüm 2.3.1: ikili ağaçlar ve gezinmeleri; yığınla içek gezinme algoritması (Algoritma T).
- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 5.4–5.7: ağaçlar, ağaç gezinmeleri, ifade ağaçları.
- Alfred Aho ve ark., *Compilers: Principles, Techniques, and Tools* (2. baskı), Bölüm 2.5 ve 5.3: sözdizimi ağaçları ve ağaç üzerinde çeviri.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 10.4 ve 12.1.

**Sıradaki ders:** İkili arama ağacı. Ekleme, silme, arama; en kötü durumda ağacın dejenere bir listeye dönmesi.
