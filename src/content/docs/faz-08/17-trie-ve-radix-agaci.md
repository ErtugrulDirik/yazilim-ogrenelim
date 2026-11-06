---
title: "8.17 Trie ve radix ağacı"
description: "Anahtarları karakter karakter dallanan bir ağaçta saklamak: trie düğümü, ekleme, arama, önek sayısı ve alfabetik otomatik tamamlama; 210 773 kelimelik sözlükte 697 bin düğüm ve 150 MB, çocuk pointer'larının %3.8'i dolu; tek çocuklu zincirleri tek kenarda birleştiren radix ağacı, kenar bölme ve 10 MB; arama süresi karşılaştırması (hash 47 ns, trie 125 ns, radix 300 ns) ve trie'nin asıl gücü olan önek sorguları; C anahtar kelimelerini tanımada trie 1.6 ns, hash 4.4 ns, doğrusal strcmp 70 ns; en uzun önek eşleme."
---

Ders 8.14'teki hash tablosu bir string'i tek bir sayıya çevirip doğrudan yerine gidiyordu. Hızlı, ama string'in **yapısını** tamamen kaybediyordu: `"algoritma"` ile `"algoritmik"`'in ortak bir öneki olduğunu bilmiyor. "`algo` ile başlayan bütün kelimeler" ya da "bu metnin başındaki en uzun anahtar kelime" gibi sorular bir hash tablosunda bütün tabloyu taramayı gerektirir. **Trie** (Edward Fredkin, 1960; "re**trie**val"dan, "tray" okunur) anahtarları karakter karakter dallanan bir ağaçta saklıyor: her düğüm bir **önek**, ve ortak öneki olan anahtarlar o öneki paylaşıyor. Otomatik tamamlama, yazım denetimi, IP yönlendirme tabloları ve lexer'lar bu yapıyı kullanıyor.

---

## 1. Trie

```
 "to", "tea", "ten", "test", "team" kelimeleri:

            (kök)
             │ t
            ( )
          e /   \ o
         ( )     (●)   to
       a / | \ n
      (●)  s   (●)     tea, ten
       │ m  \ t
      (●)   (●)        team, test
```

Kökten bir düğüme giden yoldaki harfler o düğümün temsil ettiği önek. `●` o önekte biten bir kelime olduğunu gösteriyor ("t", "te" kelime değil, ama "to" kelime). Arama kelimenin harflerini sırayla izliyor: $O(L)$, $L$ kelimenin uzunluğu. Kaç kelime saklandığından **bağımsız**.

En basit gösterim: her düğümde alfabedeki her harf için bir çocuk pointer'ı. Sadece küçük harfli İngilizce kelimeler için 26:

```c
/* Trie: her dugum bir onek; cocuklar harfe gore dogrudan dizi indeksi. Sadece 'a'..'z'. */
#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ALFABE 26

typedef struct TDugum {
    struct TDugum *cocuk[ALFABE];
    bool son;                       /* bu onekte biten bir kelime var mi */
    int altta;                      /* bu onekle baslayan kelime sayisi */
} TDugum;

static long dugum_sayisi;

static TDugum *yeni(void) { dugum_sayisi++; return calloc(1, sizeof(TDugum)); }

/* Sadece kucuk harfli kelimeler; digerlerini reddet */
static bool gecerli(const char *s) { for (; *s; s++) if (*s < 'a' || *s > 'z') return false; return true; }

bool trie_ekle(TDugum *kok, const char *s) {
    if (!gecerli(s)) return false;
    TDugum *n = kok;
    for (const char *p = s; *p; p++) {                 /* once var mi bak: altta sayaci dogru kalsin */
        n = n->cocuk[*p - 'a'];
        if (!n) break;
    }
    if (n && n->son) return false;
    n = kok;
    n->altta++;
    for (; *s; s++) {
        TDugum **c = &n->cocuk[*s - 'a'];
        if (!*c) *c = yeni();
        n = *c;
        n->altta++;
    }
    n->son = true;
    return true;
}
```

(`calloc` hata kontrolü kısalık için yok.) Çocuk seçimi bir dizi indeksi: `cocuk[harf - 'a']`. Karşılaştırma yok, dallanma yok. `altta` sayacı, her önekin altında kaç kelime olduğunu tutuyor; ekleme yolundaki her düğümde bir artıyor. Bu yüzden ekleme önce kelimenin zaten var olup olmadığına bakıyor: varsa sayaçlar iki kez artmasın.

```c
static const TDugum *onek_dugumu(const TDugum *n, const char *s) {
    for (; n && *s; s++) n = (*s >= 'a' && *s <= 'z') ? n->cocuk[*s - 'a'] : NULL;
    return n;
}

bool trie_var(const TDugum *kok, const char *s) { const TDugum *n = onek_dugumu(kok, s); return n && n->son; }
int  trie_onek_sayisi(const TDugum *kok, const char *s) { const TDugum *n = onek_dugumu(kok, s); return n ? n->altta : 0; }
```

### Önek sorguları

Trie'nin asıl gücü: bir önekin düğümüne $O(L)$'de inip oradan aşağıdaki alt ağacı gezmek. Çocuklar harf sırasıyla dizildiği için önek gezinme (Ders 8.7) kelimeleri **alfabetik** sırayla veriyor; sıralama gerekmiyor.

```c
/* Onekle baslayan kelimeleri alfabetik sirayla en fazla 'kalan' tane yazdir (onek gezinme, Ders 8.7) */
static void listele(const TDugum *n, char *tampon, int uz, int *kalan) {
    if (*kalan <= 0) return;
    if (n->son) { tampon[uz] = 0; printf(" %s", tampon); (*kalan)--; }
    for (int c = 0; c < ALFABE; c++)
        if (n->cocuk[c]) { tampon[uz] = (char)('a' + c); listele(n->cocuk[c], tampon, uz + 1, kalan); }
}

void trie_tamamla(const TDugum *kok, const char *onek, int en_fazla) {
    const TDugum *n = onek_dugumu(kok, onek);
    printf("  %-8s (%5d kelime):", onek, n ? n->altta : 0);
    if (n) { char t[128]; strcpy(t, onek); listele(n, t, (int)strlen(onek), &en_fazla); }
    printf("\n");
}
```

Sözlükteki (Ders 8.13'teki `/usr/share/dict/words`) bütün küçük harfli kelimelerle:

```c
int main(void) {
    FILE *f = fopen("/usr/share/dict/words", "r");
    if (!f) { perror("words"); return 1; }
    TDugum *kok = yeni();
    char satir[128]; long kelime = 0, harf = 0;
    while (fgets(satir, sizeof satir, f)) {
        satir[strcspn(satir, "\n")] = 0;
        if (trie_ekle(kok, satir)) { kelime++; harf += (long)strlen(satir); }
    }
    fclose(f);
    printf("%ld kelime, %ld harf, %ld dugum, dugum basina %zu bayt -> %.1f MB\n",
           kelime, harf, dugum_sayisi, sizeof(TDugum), dugum_sayisi * sizeof(TDugum) / 1e6);
    printf("cocuk pointer'larinin %%%.1f'i dolu\n", 100.0 * (dugum_sayisi - 1) / (dugum_sayisi * (double)ALFABE));
    const char *sor[] = { "tree", "trie", "algorithm", "algorithmic" };
    for (int i = 0; i < 4; i++) printf("  var mi \"%s\": %s\n", sor[i], trie_var(kok, sor[i]) ? "evet" : "hayir");
    trie_tamamla(kok, "algo", 8);
    trie_tamamla(kok, "tri", 8);
    trie_tamamla(kok, "qu", 8);
    trie_tamamla(kok, "zzz", 8);
    trie_serbest(kok);
}
```

```
$ cc -std=c11 -O2 -Wall -Wextra -fsanitize=address,undefined trie.c -o trie && ./trie
210773 kelime, 2039158 harf, 696835 dugum, dugum basina 216 bayt -> 150.5 MB
cocuk pointer'larinin %3.8'i dolu
  var mi "tree": evet
  var mi "trie": hayir
  var mi "algorithm": evet
  var mi "algorithmic": evet
  algo     (   31 kelime): algocyan algodoncillo algodonite algoesthesiometer algogenic algoid algolagnia algolagnic
  tri      ( 1196 kelime): tri triable triableness triace triacetamide triacetate triacetonamine triachenium
  qu       ( 1069 kelime): qua quab quabird quachil quack quackery quackhood quackish
  zzz      (    0 kelime):
```

(`trie` bu eski sözlükte yok.) Önek sayısı $O(L)$, ilk $k$ tamamlama $O(L + k \cdot \text{ortalama uzunluk})$ civarı. Aynı sorguyu bir hash tablosuyla yapmak 210 bin kelimenin hepsine bakmak demek.

Ama bellek felaket: **2 MB'lık** metin için **150 MB**. Düğüm sayısı (697 bin) harf sayısının üçte biri; ortak önekler paylaşılıyor ama kelimelerin sonları paylaşılmıyor. Asıl sorun düğüm boyutu: 26 pointer = 208 bayt, ve bunların sadece %3.8'i dolu. Çoğu düğümün tek bir çocuğu var: `algoesthesiometer`'in `algoe`'den sonraki 12 harfi 12 ayrı düğüm, her biri 25 boş pointer taşıyor.

---

## 2. Radix ağacı

Çözüm, tek çocuklu zincirleri **sıkıştırmak**: bir kenarın etiketi tek bir harf değil, bir **string** olsun. Dallanma olmayan her yol tek bir kenar. Bu yapıya **radix ağacı** (ya da sıkıştırılmış trie, PATRICIA ağacı; Donald Morrison, 1968) deniyor.

```
 aynı kelimeler, radix ağacı olarak:

          (kök)
            │ "t"
           ( )
      "e" /   \ "o"
        ( )   (●)  to
  "a" / | \ "n"
    (●)  "st" (●)
     │ "m" \
    (●)    (●)
```

İkinci değişiklik çocukları saklama biçimi: 26'lık dizi yerine, ilk harflerine göre sıralı bir **bağlı liste** (her düğümde "ilk çocuk" ve "kardeş" pointer'ları; herhangi sayıda çocuklu bir ağacı ikili ağaç düğümleriyle temsil etmenin klasik yolu, Knuth'un "sol çocuk, sağ kardeş" gösterimi).

```c
/* Radix agaci (sikistirilmis trie): tek cocuklu zincirler tek kenarda birlesir.
   Kenar etiketi bir string; cocuklar ilk harfe gore sirali tek yonlu liste (ilk cocuk / kardes). */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct RDugum {
    char *etiket;                   /* bu dugume gelen kenarin etiketi (kok icin "") */
    int uz;
    bool son;
    struct RDugum *ilk_cocuk, *kardes;
} RDugum;

static long rdugum_sayisi, etiket_bayt;

static RDugum *ryeni(const char *e, int uz) {
    RDugum *n = calloc(1, sizeof *n);
    n->etiket = malloc(uz + 1); memcpy(n->etiket, e, uz); n->etiket[uz] = 0; n->uz = uz;
    rdugum_sayisi++; etiket_bayt += uz + 1;
    return n;
}

static int ortak(const char *a, const char *b, int n) { int i = 0; while (i < n && a[i] && a[i] == b[i]) i++; return i; }
```

Ekleme, kelimenin kalanının ilk harfiyle başlayan kenarı arıyor. Böyle bir kenar yoksa kelimenin bütün kalanı tek bir yeni kenar oluyor. Varsa, kenar etiketiyle kelimenin ortak önekine bakılıyor; etiketin tamamı eşleşiyorsa o kenardan aşağı iniliyor, eşleşmiyorsa kenar ortak önekte **bölünüyor**:

```c
bool radix_ekle(RDugum *n, const char *s) {
    for (;;) {
        if (!*s) { bool yeni_mi = !n->son; n->son = true; return yeni_mi; }
        RDugum **p = &n->ilk_cocuk;                      /* ilk harfi s[0] olan cocugu ara (liste sirali) */
        while (*p && (*p)->etiket[0] < *s) p = &(*p)->kardes;
        RDugum *c = *p;
        if (!c || c->etiket[0] != *s) {                  /* boyle bir kenar yok: kalan her sey tek yeni kenar */
            RDugum *y = ryeni(s, (int)strlen(s));
            y->son = true; y->kardes = c; *p = y;
            return true;
        }
        int k = ortak(c->etiket, s, c->uz);
        if (k < c->uz) {                                 /* kenari bol: "test" kenarina "team" -> "te" + {"st","am"} */
            RDugum *ara = ryeni(c->etiket, k);
            ara->kardes = c->kardes;
            *p = ara;
            memmove(c->etiket, c->etiket + k, c->uz - k + 1);   /* c'nin etiketi kalan kisim */
            c->uz -= k;
            c->kardes = NULL;
            ara->ilk_cocuk = c;
            n = ara;
        } else n = c;
        s += k;
    }
}

bool radix_var(const RDugum *n, const char *s) {
    while (*s) {
        const RDugum *c = n->ilk_cocuk;
        while (c && c->etiket[0] < *s) c = c->kardes;
        if (!c || c->etiket[0] != *s || strncmp(c->etiket, s, c->uz) != 0) return false;
        s += c->uz;
        n = c;
    }
    return n->son;
}
```

(Pointer'a pointer, `p`, sıralı listeye ekleme ve listedeki düğümü değiştirme için; Ders 8.2. Ayrıca bir kenar sonlanmadan kelime biterse, örneğin ağaçta `"test"` varken `"te"` eklenirse, `ortak` 2 döndürüyor ve bölme bir ara düğüm açıp onu `son` yapıyor; bu durum döngünün bir sonraki turunda `!*s` dalında yakalanıyor.)

Bölümün başındaki örnek kelimeler `test, team, tea, ten, toast, to, t` sırasıyla eklenip ağaç girintili yazdırıldığında (`*`, `son` işareti):

```
$ cc -std=c11 -O2 -Wall -Wextra -fsanitize=address,undefined radix.c -o radix && ./radix
  t *
    e
      a *
        m *
      n *
      st *
    o *
      ast *
210773 kelime, 283659 dugum, dugum 32 bayt + etiketler 1113902 bayt -> 10.2 MB (malloc basliklari haric)
var mi: tree=1 trie=0 algorithmic=1
```

`test` eklenince tek bir `"test"` kenarı oluştu; `team` onu `"te"` + `"st"` diye böldü; `tea` de `"am"`'ı `"a"` + `"m"` diye. Sözlükte düğüm sayısı 697 binden **284 bine**, bellek 150 MB'tan **10 MB**'a indi (15 kat). Radix ağacında her iç düğümün (kök hariç) en az iki çocuğu var ya da bir kelime orada bitiyor; bu yüzden düğüm sayısı kelime sayısının en fazla iki katı (Alıştırma 4).

---

## 3. Ölçüm

Aynı 210 773 kelime trie'de, radix ağacında ve Ders 8.14'teki hash tablosunda; her kelime karışık sırayla aranıyor (sorgu stringleri bellekte sıralı, ki ölçülen yapı olsun; Ders 8.15). Dört çalıştırma:

```
$ cc -std=c11 -O2 -Wall olcum.c ../zincir/tablo.c -o olcum && ./olcum
sozluk (210773 kelime): trie 126 ns  radix 303 ns  hash 44 ns  (632319)
sozluk (210773 kelime): trie 129 ns  radix 306 ns  hash 50 ns  (632319)
sozluk (210773 kelime): trie 122 ns  radix 292 ns  hash 46 ns  (632319)
sozluk (210773 kelime): trie 121 ns  radix 293 ns  hash 47 ns  (632319)
```

**Tam eşleşme** aramasında hash tablosu açık ara önde. Ortalama kelime 9.7 harf; trie her harf için ayrı bir düğüme, yani ayrı bir cache satırına atlıyor (yaklaşık 10 bağımlı bellek erişimi). Radix ağacı daha az düğümden geçiyor ama her düğümde kardeş listesini doğrusal geziyor (kökün 26 çocuğu var) ve etiketler ayrı `malloc` blokları; daha yavaş. Hash tablosu kelimenin baytlarını bir kez okuyor (hash) ve bir iki bellek erişimiyle bitiriyor.

Bu, Ders 8.11'deki B-ağacı ölçümüyle aynı ders: asimptotik karmaşıklık ($O(L)$, ve $n$'den bağımsız) bellek erişim kalıbını gizliyor. Trie'yi hızlı yapan gerçek uygulamalar (ART, Adaptive Radix Tree; Leis ve ark., 2013) düğümleri çocuk sayısına göre 4, 16, 48 ya da 256 boyutlu dört tipe ayırıyor ve küçük düğümlerde SIMD ile arıyor.

Trie'yi seçmenin sebebi hız değil, **sorgular**:

| Sorgu | Hash tablosu | Dengeli BST (8.9) | Trie / radix |
| --- | --- | --- | --- |
| Tam eşleşme | $O(L)$ beklenen, en hızlı | $O(L \log n)$ | $O(L)$ |
| Önek ile başlayan hepsi | Bütün tablo | $O(L \log n + k)$ | $O(L + k)$ |
| Sıralı gezinme | Yok (sıralamak gerek) | Var | Var |
| En uzun önek eşleme | $L$ kez arama | Zor | $O(L)$, tek geçiş |
| Bellek | Anahtarlar + kovalar | Anahtarlar + pointer'lar | Ortak önekler paylaşılıyor, ama düğüm ek yükü büyük |

---

## 4. Anahtar kelime tanıma

Bir lexer okuduğu her ismin anahtar kelime (`int`, `while`, `return`) mi yoksa bir tanımlayıcı mı olduğunu bilmeli. C89'un 32 anahtar kelimesi için üç yol:

```c
static const char *anahtar_kelimeler[] = {   /* C89'un 32 anahtar kelimesi */
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double", "else", "enum",
    "extern", "float", "for", "goto", "if", "int", "long", "register", "return", "short", "signed",
    "sizeof", "static", "struct", "switch", "typedef", "union", "unsigned", "void", "volatile", "while" };

static int dogrusal(const char *s) { for (int i = 0; i < 32; i++) if (strcmp(s, anahtar_kelimeler[i]) == 0) return 1; return 0; }
```

Diğer ikisi aynı 32 kelimeyle kurulmuş küçük bir trie ve küçük bir hash tablosu. Girdi, Ders 8.14'teki `tablo.c`'nin bütün isim tokenları (559 token, 84'ü anahtar kelime), 1000 kez:

```
anahtar kelime (559 token, 84 anahtar kelime/tur): dogrusal strcmp 69.3 ns  trie 1.6 ns  hash 4.3 ns
```

(Dört çalıştırmada trie 1.6–1.7 ns, hash 4.3–4.4 ns, doğrusal 69–79 ns; ilk çalıştırmalardan birinde hash 17.5 ns ölçüldü, bu tür sıçramaları görmek için ölçümü tekrarlamak gerekiyor.)

Burada trie **kazanıyor**, iki sebeple. 32 kelimelik trie birkaç yüz düğüm, cache'e tamamen sığıyor; tam sözlükteki cache kaçırma sorunu yok. Daha önemlisi, tanımlayıcıların çoğu ilk bir iki harfte reddediliyor: `tablo`, `t`'den sonra `a` ile devam eden bir anahtar kelime olmadığı için ikinci harfte; `kova` ilk harfte (k ile başlayan anahtar kelime yok). Hash ise her tokenın bütün harflerini okuyor. Doğrusal `strcmp` her tanımlayıcı için 32 karşılaştırma.

Gerçek lexer'lar bu fikri bir adım daha ileri götürüyor. Anahtar kelime trie'si aslında bir **sonlu durum makinesi** (Ders 1.3): her düğüm bir durum, her harf bir geçiş. Bunu veri yapısı olarak gezmek yerine **kod olarak** üretmek mümkün: her durum bir `switch`. re2c ve flex gibi lexer üreteçleri tam olarak bunu yapıyor (Faz 14'te NFA'dan DFA'ya, Ders 18.14'te kendi lexer üretecimiz). Başka bir yaklaşım, GNU `gperf`'in **mükemmel hash** fonksiyonu: sabit bir kelime kümesi için çakışmasız bir hash bulmak, ki arama tek bir hash ve tek bir `strcmp` olsun.

---

## Alıştırmalar

**1** – Trie düğümünü 26 yerine 256 çocuklu yapsaydık (her bayt değeri için bir pointer, bütün stringleri kabul etmek için), sözlüğün trie'si ne kadar bellek tutardı? Bu sorunu çözmenin, radix sıkıştırma dışında iki yolunu öner.

**2** – **En uzun önek eşleme**: bir string'in, trie'deki kelimelerden hangisiyle **başladığını**, ve bunlardan en uzununu bul. Trie'yi bir kez gezen bir fonksiyon yaz. `algorithmically`, `treehouses`, `xyzzy`, `understandingly` için sözlükte sonuç ne? Bu işlem bir lexer'da ve bir IP yönlendiricisinde neye karşılık geliyor?

**3** – Trie'den kelime silme: `son` bayrağını kaldırmak yeterli mi? Gereksiz kalan düğümleri de silen bir algoritma tarif et. `altta` sayacı bunu nasıl kolaylaştırıyor?

**4** – $n$ kelimeli bir radix ağacının en fazla kaç düğümü olabilir? Neden? Sözlükteki 283 659 düğüm bu sınıra uyuyor mu?

**5** – Bölüm 4'teki anahtar kelime trie'sini bir **durum makinesi** olarak, her düğümü bir `switch` durumu olan C koduna nasıl çevirirsin? `do`, `double`, `default` kelimeleri için o kodun ilk birkaç satırını yaz.

<details>
<summary>Cevaplar</summary>

**1** – Düğüm $256 \times 8 + 8 = 2056$ bayt; $696\,835$ düğümle **1.43 GB**. İki yol: (a) Çocukları düğümün içinde **sıralı küçük bir dizi** olarak, gerçek çocuk sayısı kadar yerle saklamak: `{harf, pointer}` çiftleri, aramada doğrusal ya da ikili arama. Düğüm boyutu çocuk sayısıyla orantılı. ART'nin 4/16/48/256'lık düğüm tipleri bunun uyarlanabilir hali. (b) Her baytı iki 4 bitlik parçaya (nibble) bölüp 16 çocuklu bir trie kullanmak: derinlik iki katına çıkıyor ama düğüm 16 pointer. (c) Üçlü arama ağacı (ternary search tree, Bentley ve Sedgewick, 1997): her düğümde tek bir harf ve üç çocuk (küçük, eşit, büyük); trie ile BST'nin karışımı.

**2** –

```c
static int en_uzun_onek(const TDugum *n, const char *s) {
    int en = 0;
    for (int i = 0; n && s[i]; i++) {
        n = (s[i] >= 'a' && s[i] <= 'z') ? n->cocuk[s[i] - 'a'] : NULL;
        if (n && n->son) en = i + 1;
    }
    return en;
}
```

```
  algorithmically  -> "algorithmic"
  treehouses       -> "tree"
  xyzzy            -> "x"
  understandingly  -> "understandingly"
```

Trie'de yolu gidebildiğin kadar izle; yol boyunca gördüğün son `son` düğümü cevap. Tek geçiş, $O(L)$. Lexer'da bu **en uzun eşleşme kuralı** (maximal munch): `<=` girdisinde `<` değil `<=` tokeni, `intx` girdisinde `int` anahtar kelimesi değil `intx` tanımlayıcısı. IP yönlendirmede: bir paketin hedef adresinin bitleri, yönlendirme tablosundaki ön eklerden (`10.0.0.0/8`, `10.1.0.0/16`) en uzun eşleşenini bulmak için bit bit bir trie'de (radix ağacında) izleniyor; Linux çekirdeğinin yönlendirme tablosu (`fib_trie`) tam bu yapı.

**3** – Yetmez: `son` kaldırılınca kelime bulunamaz, ama artık hiçbir kelimeye ait olmayan düğümler bellekte kalır. Doğru silme: kelimenin yolundaki her düğümde `altta`'yı bir azalt; `altta`'sı 0'a düşen ilk düğümden itibaren alt ağacı tamamen serbest bırak ve onu gösteren pointer'ı `NULL` yap. `altta == 0`, "bu öneki kullanan başka kelime yok" demek; o düğümden aşağısı sadece silinen kelimeye aitti. Sayaç olmasaydı her düğümde 26 çocuğu kontrol ederek "bu düğüm boş mu" diye sormak ve bunu aşağıdan yukarı, özyinelemeyle yapmak gerekirdi.

**4** – En fazla $2n$ (kök dahil, $2n + 1$). Radix ağacında kök dışındaki her düğüm ya bir kelimenin bittiği yer ($n$ tane olabilir) ya da en az iki çocuklu bir dallanma noktası. Yaprakların hepsi kelime sonu, yani en fazla $n$ yaprak. En az iki çocuklu iç düğümlerin sayısı yaprak sayısından az (Ders 8.7'deki ikili ağaç argümanının genellemesi: her dallanma yaprak sayısını en az bir artırır). Toplam: $n$ kelime düğümü + en fazla $n - 1$ dallanma düğümü + kök. Sözlükte $283\,659 \le 2 \cdot 210\,773 + 1 = 421\,547$: uyuyor. Trie'de ise düğüm sayısı **harf** sayısıyla sınırlı (697 bin), kelime sayısıyla değil.

**5** – Her trie düğümü bir kod bloğu; bir sonraki harfe göre `switch`. Kelimenin bittiği düğümde `'\0'` geldiyse anahtar kelime:

```c
static int anahtar_mi(const char *s) {
    switch (s[0]) {
    case 'd':
        switch (s[1]) {
        case 'o':                                   /* "do" */
            if (s[2] == '\0') return 1;
            return strcmp(s + 2, "uble") == 0;      /* tek dalli kalan: radix kenari gibi */
        case 'e':
            return strcmp(s + 2, "fault") == 0;
        default: return 0;
        }
    /* case 'a': ..., case 'b': ... */
    default: return 0;
    }
}
```

Dallanmanın bittiği yerde (`"do"`'dan sonra tek devam `"uble"`) kalan harfler tek bir `strcmp` ile kontrol ediliyor: radix ağacının sıkıştırılmış kenarı. Derleyici `switch`'leri atlama tablolarına ya da ikili arama dallarına çeviriyor (Ders 7.9), ve veri yapısı tamamen ortadan kalkıyor: pointer yok, bellek erişimi yok, sadece kod. Elle yazmak zahmetli ve hataya açık; bu yüzden üreteçlerle üretiliyor (Ders 18.14).

</details>

---

## Kaynaklar

- Edward Fredkin, "Trie Memory", *Communications of the ACM* 3(9), 1960.
- Donald Morrison, "PATRICIA: Practical Algorithm To Retrieve Information Coded in Alphanumeric", *Journal of the ACM* 15(4), 1968.
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.3: dijital arama; trie ve Patricia.
- Viktor Leis, Alfons Kemper ve Thomas Neumann, "The Adaptive Radix Tree: ARTful Indexing for Main-Memory Databases", *ICDE* 2013.
- Jon Bentley ve Robert Sedgewick, "Fast Algorithms for Sorting and Searching Strings", *SODA* 1997: üçlü arama ağaçları.
- Douglas Schmidt, "GPERF: A Perfect Hash Function Generator", *C++ Report*, 1990.

**Sıradaki ders:** Union-find. Rank ve yol sıkıştırma, ters Ackermann karmaşıklığı.
