---
title: "9.9 String eşleme"
description: "Bir metinde bir deseni aramak: Ders 4.17'deki naif strstr ve O(nm) en kötü durumu; KMP'nin önek-sonek tablosu ve metinde hiç geri gitmeyen O(n + m) taraması, ababaca örneği ve amortize analiz; Boyer–Moore'un sadeleşmiş hali Horspool, sağdan karşılaştırma ve kötü karakter kayması, uzun desende karakter başına 0.08 karşılaştırma; Rabin–Karp'ın kayan hash'i; 25 MB'lık sözlük metninde ve aaaa…ab gibi kötü girdilerde beş yöntem (libc strstr dahil) ölçülerek; her algoritmanın kendi kötü girdisi."
---

Ders 4.17'de `strstr`'i sıfırdan yazdık ve kötü bir girdiyle karşılaştık: `"aaaa...a"` metninde `"aaa...ab"` deseni, her konumda neredeyse tam eşleşip son karakterde bozuluyor ve $n \times m$ karşılaştırma yapılıyordu. Orada sözü bu derse bırakmıştık: "zaten okuduğumuz karakterleri unutmadan devam edebilirdik." **String eşleme**, metin düzenleyicilerdeki "bul"dan `grep`'e, virüs tarayıcılardan DNA dizilimi analizine kadar her yerde. Bu ders üç klasik algoritmayı yazıyor, her biri naif aramanın israfını farklı bir şekilde ortadan kaldırıyor: KMP **zaten okunanı** hatırlayarak, Boyer–Moore **okunmayanı** atlayarak, Rabin–Karp bütün pencereyi **tek bir sayıyla** karşılaştırarak.

Gösterim: metin $t$, uzunluğu $n$; desen $p$, uzunluğu $m$. Bütün fonksiyonlar desenin metinde geçtiği (çakışanlar dahil) bütün yerleri sayıyor, ki sonuçları karşılaştırabilelim.

---

## 1. Kod

```c
/* String esleme: naif, KMP, Boyer-Moore-Horspool, Rabin-Karp. Hepsi butun (cakisan) eslesmeleri sayar. */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long kars;                                     /* karakter karsilastirmasi */

/* NAIF (Ders 4.17'nin strstr_mine'i, butun eslesmeleri sayan hali): O(nm) en kotu */
static long naif(const char *t, size_t n, const char *p, size_t m) {
    long say = 0;
    for (size_t i = 0; i + m <= n; i++) {
        size_t j = 0;
        while (j < m && (kars++, t[i + j] == p[j])) j++;
        if (j == m) say++;
    }
    return say;
}

/* KMP: pi[j] = p[0..j]'nin hem oneki hem soneki olan en uzun ozel parcasinin uzunlugu */
static void kmp_tablo(const char *p, size_t m, size_t *pi) {
    pi[0] = 0;
    for (size_t j = 1, k = 0; j < m; j++) {
        while (k > 0 && p[j] != p[k]) k = pi[k - 1];  /* uyusmazlik: bir sonraki daha kisa sinira dus */
        if (p[j] == p[k]) k++;
        pi[j] = k;
    }
}
static long kmp(const char *t, size_t n, const char *p, size_t m) {
    size_t *pi = malloc(m * sizeof *pi); kmp_tablo(p, m, pi);
    long say = 0;
    for (size_t i = 0, k = 0; i < n; i++) {           /* metinde HIC geri gidilmiyor */
        while (k > 0 && (kars++, t[i] != p[k])) k = pi[k - 1];
        if (k == 0) kars++;
        if (t[i] == p[k]) k++;
        if (k == m) { say++; k = pi[k - 1]; }        /* eslesme: cakisan bir sonrakine devam */
    }
    free(pi);
    return say;
}

/* HORSPOOL (Boyer-Moore'un sadelesmis hali): sagdan sola karsilastir; kayma, pencerenin son karakterine gore */
static long horspool(const char *t, size_t n, const char *p, size_t m) {
    size_t kayma[256];
    for (int c = 0; c < 256; c++) kayma[c] = m;
    for (size_t j = 0; j + 1 < m; j++) kayma[(unsigned char)p[j]] = m - 1 - j;
    long say = 0;
    for (size_t i = 0; i + m <= n; i += kayma[(unsigned char)t[i + m - 1]]) {
        size_t j = m;
        while (j > 0 && (kars++, t[i + j - 1] == p[j - 1])) j--;
        if (j == 0) say++;
    }
    return say;
}

/* RABIN-KARP: kayan hash (mod 2^64). Hash esitse karakterleri dogrula. */
static long rabin_karp(const char *t, size_t n, const char *p, size_t m) {
    const uint64_t B = 1000003;
    uint64_t hp = 0, ht = 0, Bm = 1;
    for (size_t j = 0; j < m; j++) { hp = hp * B + (unsigned char)p[j]; ht = ht * B + (unsigned char)t[j]; Bm *= B; }
    long say = 0;
    for (size_t i = 0; i + m <= n; i++) {
        if (ht == hp && memcmp(t + i, p, m) == 0) { kars += (long)m; say++; }
        if (i + m < n) ht = ht * B + (unsigned char)t[i + m] - Bm * (unsigned char)t[i];   /* kaydir: O(1) */
    }
    return say;
}

static long libc(const char *t, size_t n, const char *p, size_t m) {
    (void)n; (void)m; long say = 0;
    for (const char *s = t; (s = strstr(s, p)); s++) say++;
    return say;
}
```

`kars` karakter karşılaştırmalarını sayıyor (Rabin–Karp'ta sadece hash eşleşince yapılan doğrulama).

---

## 2. KMP

Naif arama bir uyuşmazlıkta metinde **geri** gidip bir sonraki konumdan baştan başlıyor. Knuth, Morris ve Pratt'ın (1977) gözlemi: o noktaya kadar eşleşen $j$ karakter, desenin ilk $j$ karakteriyle aynı; yani metnin o kısmını **zaten biliyoruz** ve bu bilgi sadece desene bağlı. Desen önceden işlenip şu soru her $j$ için cevaplanabilir: "desenin ilk $j$ karakteri eşleşti, sonra uyuşmazlık oldu; desenin kaçıncı karakterinden devam edebilirim?"

Cevap, **önek-sonek tablosu** $\pi$: $\pi[j]$, $p[0..j]$'nin hem **öneki** hem **soneki** olan en uzun (kendisinden kısa) parçanın uzunluğu.

```
 desen:   a  b  a  b  a  c  a
 j:       0  1  2  3  4  5  6
 π[j]:    0  0  1  2  3  0  1
```

($\pi[4] = 3$: `ababa`'nın hem başı hem sonu `aba`.) Programla:

```
0 0 1 2 3 0 1 
```

Metinde `ababa` eşleşip 6. karakterde (`c` yerine başka bir şey) uyuşmazlık olduğunu düşün. Naif arama bir sonraki konumdan baştan başlardı. KMP ise şunu biliyor: son okunan 5 karakter `ababa`, ve bunun sonu (`aba`) desenin başıyla aynı. Desen bu kadar kaydırılınca ilk 3 karakteri **zaten eşleşmiş** durumda; karşılaştırma desenin 3. karakterinden, metinde **aynı yerden** devam ediyor.

`kmp` fonksiyonunda `k` eşleşen karakter sayısı. Uyuşmazlıkta `k = pi[k - 1]` ile bir sonraki en uzun sınıra düşülüyor (birkaç kez gerekebilir), ve metindeki `i` **hiç geri gitmiyor**. Tam eşleşmede de `k = pi[m - 1]`: çakışan bir sonraki eşleşme aranıyor.

**Maliyet**: `i` $n$ kez ilerliyor. `k` her adımda en fazla 1 artıyor ve her `while` turunda en az 1 azalıyor; hiç negatif olmadığı için toplam azalma, toplam artıştan (en fazla $n$) fazla olamaz. Dolayısıyla `while` döngüsü bütün tarama boyunca toplam en fazla $n$ kez dönüyor: arama $O(n)$, tablo aynı argümanla $O(m)$, toplam $O(n + m)$, **en kötü durumda**. Ders 4.24 ve 8.14'teki amortize analizin bir örneği daha: tek bir adım uzun sürebiliyor ama toplam doğrusal.

$\pi$ tablosunu kurmak, desenin **kendi içinde** KMP araması yapmak; aynı kod.

---

## 3. Boyer–Moore ve Horspool

KMP her metin karakterine en az bir kez bakıyor. Boyer ve Moore (1977) bunun da gerekmediğini gösterdi: deseni metnin üzerine koy ve **sağdan sola** karşılaştır. Pencerenin son karakteri desende hiç yoksa, desen o karakterin üzerinden hiçbir konumda eşleşemez: deseni $m$ karakter birden kaydır. Uzun bir desende çoğu metin karakterine hiç bakılmıyor; algoritma desen uzadıkça **hızlanıyor**.

Tam Boyer–Moore iki kural kullanıyor (kötü karakter ve iyi sonek); **Horspool** (1980) sadece birini, en basit hali: pencerenin **son** karakteri $c$ ise, deseni, $c$'nin desendeki (son konum hariç) en sağdaki geçişi bu karakterin hizasına gelecek kadar kaydır. $c$ desende yoksa $m$ kaydır. `kayma` tablosu her bayt değeri için bu mesafeyi tutuyor (Ders 9.7'deki gibi bir değeri doğrudan indeks olarak kullanmak).

```
 metin:   ...  t  h  e     c  a  t  ...
 desen:        z  y  g  o  t  e
                            ^ pencerenin son karakteri 'a', desende yok: 6 kaydır
```

Ortalama durumda doğal dil metninde karşılaştırma sayısı yaklaşık $n/m$; en kötü durumda $O(nm)$ (Alıştırma 2). Tam Boyer–Moore'un iyi sonek kuralı en kötü durumu $O(n + m)$'ye indiriyor (Galil'in iyileştirmesiyle), ama kodu çok daha karmaşık. `grep` ve çoğu `memmem`/`strstr` uygulaması Boyer–Moore ailesinden bir algoritma kullanıyor.

---

## 4. Rabin–Karp

Rabin ve Karp (1987) başka bir yol seçti: desenin karakterlerini teker teker karşılaştırmak yerine, desenin ve metindeki her $m$ uzunluklu pencerenin **hash'ini** (Ders 8.13) karşılaştır. Hash'ler eşitse karakterleri doğrula (çakışma olabilir); değilse kesinlikle eşleşme yok.

Püf nokta, pencerenin hash'ini her konum için baştan hesaplamamak. Polinom hash $h(s) = s_0 B^{m-1} + s_1 B^{m-2} + \dots + s_{m-1}$ (Ders 8.13'teki K&R hash'inin genel hali), pencere bir sağa kayınca $O(1)$'de güncelleniyor: soldan çıkan karakterin katkısını ($s_0 B^{m-1}$) çıkar, $B$ ile çarp, sağdan giren karakteri ekle. **Kayan hash** (rolling hash). Bütün aritmetik modülo $2^{64}$, işaretsiz taşmayla (Ders 3.8).

Beklenen $O(n + m)$; en kötü durum, her pencerede hash çakışması olursa $O(nm)$. Asıl gücü tek bir desende değil: **birçok** deseni aynı anda aramak (aynı uzunluktaki $k$ desenin hash'lerini bir hash tablosuna koyup her pencerenin hash'ini orada aramak, $O(n + km)$), ve **iki boyutlu** desen arama. Bir dosyadaki tekrarlı blokları bulan araçlar (rsync, yedekleme sistemlerindeki içerik tanımlı parçalama) kayan hash kullanıyor.

---

## 5. Ölçüm

Üç senaryo. Sözlük dosyası (Ders 8.13) kelimeler boşlukla ayrılmış halde 10 kez arka arkaya (25 MB); önce kısa bir desen (`zygote`), sonra metinde olmayan 28 karakterlik bir desen; sonra Ders 4.17'deki kötü girdi:

```
$ cc -std=c11 -O2 -Wall -Wextra eslesme.c -o eslesme && ./eslesme
sozlukte "zygote" (n=24938850, m=6)
  naif             40 eslesme     0.0195 s    1.00 karsilastirma/karakter
  KMP              40 eslesme     0.0239 s    1.00 karsilastirma/karakter
  Horspool         40 eslesme     0.0181 s    0.21 karsilastirma/karakter
  Rabin-Karp       40 eslesme     0.0313 s    0.00 karsilastirma/karakter
  libc strstr      40 eslesme     0.0090 s
sozlukte uzun ve olmayan bir desen (n=24938850, m=28)
  naif              0 eslesme     0.0329 s    1.09 karsilastirma/karakter
  KMP               0 eslesme     0.0357 s    1.08 karsilastirma/karakter
  Horspool          0 eslesme     0.0065 s    0.08 karsilastirma/karakter
  Rabin-Karp        0 eslesme     0.0312 s    0.00 karsilastirma/karakter
  libc strstr       0 eslesme     0.0254 s
aaaa...a icinde aaa...ab (n=1000000, m=1000)
  naif              0 eslesme     0.3298 s  999.00 karsilastirma/karakter
  KMP               0 eslesme     0.0013 s    2.00 karsilastirma/karakter
  Horspool          0 eslesme     0.0009 s    1.00 karsilastirma/karakter
  Rabin-Karp        0 eslesme     0.0012 s    0.00 karsilastirma/karakter
  libc strstr       0 eslesme     0.0301 s
```

(Beş yöntem her senaryoda aynı sayıda eşleşme buluyor; sanitizer'lı derleme temiz.)

- **Doğal metinde naif arama iyi**: karakter başına 1.0–1.1 karşılaştırma, çünkü desenin ilk karakteri çoğu konumda hemen uyuşmuyor. KMP de 1 karşılaştırma yapıyor ve tablo bakımı yüzünden biraz yavaş. Ders 4.17'nin gözlemi: naif aramanın en kötü durumu gerçek metinde nadiren ortaya çıkıyor.
- **Horspool uzun desende 5 kat hızlı**: karakter başına 0.08 karşılaştırma, ortalama kayma $m$'ye yakın. Desen 6 karakterden 28'e uzayınca karşılaştırma oranı 0.21'den 0.08'e düştü: desen uzadıkça hızlanan algoritma.
- **Kötü girdide naif 330 ms**, öbürleri 1 ms civarında: KMP karakter başına tam 2 karşılaştırma (amortize sınırın kendisi), Horspool 1 (pencerenin son karakteri `a`, desenin sonu `b`: anında uyuşmazlık ve bir kayma).
- **libc `strstr`** kısa desende en hızlısı (SIMD ile ilk karakteri aynı anda birçok konumda arıyor; Faz 11), ve kötü girdide naif arama gibi patlamıyor (30 ms): macOS'un `strstr`'i en kötü durumu sınırlayan bir algoritma kullanıyor. Uzun desende Horspool'dan yavaş.

Her algoritmanın kendi **kötü girdisi** var. Naif arama ve Rabin–Karp (hash çakışmasıyla) için yukarıdaki; Horspool için deseni tersine çevirmek yetiyor (Alıştırma 2). Sadece KMP ve tam Boyer–Moore (Galil iyileştirmesiyle) en kötü durumda doğrusal. Dışarıdan gelen girdiyle arama yapan bir sunucuda bu fark önemli (Ders 8.13'teki hash taşkınının string eşleme hali).

---

## Alıştırmalar

**1** – `aabaaab` deseni için $\pi$ tablosunu elle hesapla. Metin `aabaaaabaaab` ise KMP hangi konumda eşleşme buluyor; `k` değeri metin boyunca nasıl değişiyor?

**2** – Horspool'u `aaaa...a` (1 milyon) metninde `baa...a` (`b` ve 999 `a`) deseniyle çalıştır. Kaç karşılaştırma yapar? Neden? Tam Boyer–Moore'un iyi sonek kuralı burada ne yapardı?

**3** – Rabin–Karp'ta hash modülo $2^{64}$. Bir saldırgan, farklı içerikli ama aynı hash'li çok sayıda pencere içeren bir metin üretebilir mi? Asal bir modül ve rastgele seçilmiş bir taban ne değiştirir?

**4** – $k$ tane desen aynı anda aranacak (bir virüs tarayıcının imza listesi gibi), desenlerin uzunlukları farklı. KMP'yi $k$ kez çalıştırmak $O(k(n + m))$. Aho–Corasick algoritması bunu $O(n + \sum m_i + \text{eşleşme sayısı})$'ye indiriyor. Ders 8.17'deki trie ile KMP'nin $\pi$ tablosu birleşince ne olur?

**5** – KMP'nin $\pi$ tablosu bir **sonlu durum makinesi** (Ders 1.3) olarak da düşünülebilir: durum $k$, eşleşen karakter sayısı. Bu makineyi her (durum, karakter) çifti için tam bir geçiş tablosu olarak yazarsan aramanın iç döngüsü ne olur? Bellek maliyeti ne? Bu, Faz 14'teki hangi yapıya karşılık geliyor?

<details>
<summary>Cevaplar</summary>

**1** – `a a b a a a b`: $\pi = 0, 1, 0, 1, 2, 2, 3$. ($\pi[5]$: `aabaaa`'nın sonu `aa` ve başı `aa`, ama `aab` sonu değil: 2. $\pi[6]$: `aabaaab`'nin sonu `aab`, başı `aab`: 3.) Metin `aabaaaabaaab` (12 karakter), 0 tabanlı: `i = 0..4`'te `k` 1, 2, 3, 4, 5'e çıkıyor (`aabaa` eşleşti). `i = 5`'te metin `a`, desenin 5. karakteri `a`: `k = 6`. `i = 6`'da metin `a`, desenin 6. karakteri `b`: uyuşmazlık, `k = \pi[5] = 2`; desenin 2. karakteri `b`, metin `a`: yine uyuşmazlık, `k = \pi[1] = 1`; desenin 1. karakteri `a`, eşleşti: `k = 2`. `i = 7` (`b`): `k = 3`; `i = 8, 9, 10` (`a a a`): `k` 4, 5, 6; `i = 11` (`b`): `k = 7 = m`, eşleşme, başlangıcı `11 - 7 + 1 = 5`. Metinde hiç geri gidilmedi.

**2** –

```
aaaa...a icinde baa...a (n=1000000, m=1000)
  naif              0 eslesme     0.0007 s    1.00 karsilastirma/karakter
  KMP               0 eslesme     0.0010 s    1.00 karsilastirma/karakter
  Horspool          0 eslesme     0.4070 s  999.00 karsilastirma/karakter
  Rabin-Karp        0 eslesme     0.0012 s    0.00 karsilastirma/karakter
  libc strstr       0 eslesme     0.0003 s
```

Horspool her pencerede sağdan sola 999 `a` eşleştirip sadece desenin ilk karakteri `b`'de uyuşmazlık buluyor; pencerenin son karakteri `a` ve `kayma['a'] = 1` (desenin sondan bir önceki karakteri de `a`): her seferinde 1 kaydırıyor. $n \times m$: naif aramanın kötü durumunun aynası. Naif arama ise burada en iyi durumunda: soldan karşılaştırdığı için `b` hemen uyuşmuyor. Tam Boyer–Moore'un iyi sonek kuralı, eşleşen 999 karakterlik `aaa...a` sonekinin desende başka bir yerde **aynı karakterle bitmeyen** bir şekilde geçip geçmediğine bakıyor; geçmediği için deseni $m$ kaydırabiliyor. Galil'in kuralıyla da daha önce eşleştiği bilinen karakterleri tekrar karşılaştırmıyor: $O(n + m)$.

**3** – Evet. Taban ve modül sabit ve biliniyorsa, polinom hash'i modülo $2^{64}$ olan iki farklı string bulmak kolay: Thue–Morse dizisi ($0, 01, 0110, 01101001, \dots$, her adımda bitlerin tersini ekleyerek) ve onun tersi (her bitin tümleyeni), uzunluk yeterince büyüyünce **herhangi** bir tek taban için modülo $2^{64}$ aynı hash'i veriyor; bu dersteki taban 1 000 003 ile, `a`/`b` harfleriyle yazılmış 1024 karakterlik Thue–Morse dizisi ve tersi aynı hash'e sahip (programla kontrol edildi; 512'de henüz farklı). Bu bloklarla saldırgan her pencerede çakışma üretebilir ve Rabin–Karp her konumda $m$ karakter doğrulayıp $O(nm)$'e düşer. Büyük bir **asal** modül (örneğin $2^{61} - 1$) ve program her çalıştığında **rastgele** seçilen bir taban, çakışma olasılığını iki pencere için $m / p$ civarına indiriyor ve saldırganın önceden çakışma hesaplamasını imkânsız kılıyor (Ders 8.13'teki gizli tohumlu hash'ler).

**4** – Bütün desenleri bir **trie**'ye koy (Ders 8.17). Her trie düğümü bir desenin bir önekini temsil ediyor. KMP'nin $\pi$'sinin genellemesi: her düğüm için bir **başarısızlık bağlantısı**, o düğümün temsil ettiği string'in, trie'de bulunan **en uzun özel soneki**ne. Metni tararken trie'de ilerle; ilerleyemeyince başarısızlık bağlantılarını izle (KMP'nin `k = pi[k-1]`'i gibi). Ayrıca her düğümde "buradan ulaşılan bir başarısızlık zincirinde biten desenler" listesi. Bu, Aho–Corasick otomatı (1975); `grep -F`'in çoklu desen modu, ClamAV ve Snort'un imza eşlemesi, ve Unix'in `fgrep`'i bu yapıyı kullanıyor.

**5** – `delta[k][c]`: $k$ karakter eşleşmişken metinden `c` gelirse yeni eşleşen karakter sayısı. Tablo $\pi$ ile şöyle kuruluyor: $p[k] = c$ ise $k + 1$, değilse $\delta[\pi[k-1]][c]$ (ve $k = 0$ için $0$). Arama döngüsü tek satıra iniyor: `k = delta[k][(unsigned char)t[i]]; if (k == m) eslesme;`. Dal yok, `while` yok: metin karakteri başına tam bir tablo okuması. Bellek $(m + 1) \times 256$ durum, 1000 karakterlik desende 256 000 giriş (1 MB). Bu, desenin **deterministik sonlu otomatı** (DFA): Faz 14'te düzenli ifadelerden üreteceğimiz DFA'ların en basit hali (tek bir sabit string). `grep`'in düzenli ifade motoru ve lexer üreticileri (Ders 18.14) aynı yapıyı genel ifadeler için kuruyor.

</details>

---

## Kaynaklar

- Donald Knuth, James Morris ve Vaughan Pratt, "Fast Pattern Matching in Strings", *SIAM Journal on Computing* 6(2), 1977.
- Robert Boyer ve J Strother Moore, "A Fast String Searching Algorithm", *Communications of the ACM* 20(10), 1977.
- R. Nigel Horspool, "Practical Fast Searching in Strings", *Software: Practice and Experience* 10(6), 1980.
- Richard Karp ve Michael Rabin, "Efficient Randomized Pattern-Matching Algorithms", *IBM Journal of Research and Development* 31(2), 1987.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 32: string eşleme.
- Alfred Aho ve Margaret Corasick, "Efficient String Matching: An Aid to Bibliographic Search", *Communications of the ACM* 18(6), 1975.

**Sıradaki ders:** Açgözlü algoritmalar. Aktivite seçimi, Huffman kodlaması ve C'de dosya sıkıştırma.
