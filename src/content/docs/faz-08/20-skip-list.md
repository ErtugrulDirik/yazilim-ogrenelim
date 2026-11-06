---
title: "8.20 Skip list ve rastgele yapılar"
description: "Dengeyi kurallarla değil yazı-turayla sağlamak: üst üste bağlı listelerden oluşan skip list, yazı-tura ile seviye seçimi ve bunun bit hilesiyle tek satırda yapılışı, arama, ekleme ve silme; beklenen seviye sayısı, düğüm başına beklenen pointer ve geriye doğru analizle arama maliyeti (1/p)·log₁/ₚ n; 1 milyon anahtarda ölçüm: arama başına 38–40 karşılaştırma, sıralı girdinin hiçbir şeyi bozmaması, 10 tohumda %8'lik bir aralıkta kalan sonuçlar; p = 1/4 ile 1.33 pointer; kırmızı-siyah ağaçla süre karşılaştırması ve skip list'in nerede kullanıldığı."
---

Ders 8.8'deki ikili arama ağacı, anahtarlar **rastgele** sırayla gelirse iyi davranıyordu (ortalama derinlik $2 \ln n$), ama gelen sırayı biz seçemiyorduk. Ders 8.9–8.10, en kötü sıraya karşı bile dengeyi koruyan kurallar ve dönmeler ekledi; kod uzadı ve hataya açık hale geldi. Üçüncü bir yol var: rastgeleliği **girdiden** almak yerine **kendimiz** üretmek. Yapı, girdinin sırasından bağımsız olarak, kendi attığı yazı-turalara göre şekil alıyor. Kötü bir girdi yok; sadece kötü şans var, ve onun olasılığı ihmal edilebilir. **Skip list** (William Pugh, 1990) bu fikrin en sade uygulaması: AVL'nin ya da kırmızı-siyahın dörtte biri uzunluğunda kod, ve aynı beklenen $O(\log n)$.

---

## 1. Fikir: bağlı listeye ekspres hatlar

Sıralı bir bağlı listede arama $O(n)$: baştan tek tek ilerlemek gerekiyor. Her iki düğümden birini bir **üst** listeye de koyarsak, üst listede ilerleyerek yarısını atlayabiliriz; doğru aralığı bulunca alta inip bir iki adım daha. Üst listenin de yarısını bir üste koyarsak... Bir şehrin metro sistemi gibi: her durakta duran tren, sadece büyük duraklarda duran ekspres, sadece birkaç merkez durakta duran süper ekspres.

```
 seviye 3: bas ─────────────────────────► 40 ──────────────────────────► nil
 seviye 2: bas ──────────► 20 ──────────► 40 ──────────► 60 ──────────► nil
 seviye 1: bas ──► 10 ──► 20 ──► 30 ──► 40 ──► 50 ──► 60 ──► 70 ──► nil
```

Düzenli yapılırsa (tam her ikinci düğüm bir üstte) arama $O(\log n)$, ama ekleme ve silme bu düzeni bozar: bir düğüm eklemek, üstteki bütün seviyelerin yeniden dizilmesini gerektirir. Pugh'un fikri: düzeni zorlamaktan vazgeç. Her yeni düğüm için **yazı-tura at**: tura gelirse bir üst seviyeye de katıl, tekrar at; yazı gelince dur. Ortalamada düğümlerin yarısı seviye 2'de, dörtte biri seviye 3'te: düzenli yapının istatistiksel hali. Ve bir düğüm eklemek, başka hiçbir düğümün seviyesini değiştirmiyor.

---

## 2. Kod

```c
/* Skip list (Pugh, 1990): seviyeli bagli listeler. Her dugum p olasilikla bir ust seviyeye de katilir. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define MAKS_SEVIYE 32

typedef struct SDugum {
    int anahtar;
    int seviye;                         /* kac seviyede var (1..MAKS_SEVIYE) */
    struct SDugum *ileri[];             /* esnek dizi: ileri[0] en alt seviye, tam liste */
} SDugum;

typedef struct {
    SDugum *bas;                        /* gozcu: butun seviyelerde, anahtari anlamsiz */
    int seviye;                         /* su an kullanilan en yuksek seviye */
    long karsilastirma;                 /* istatistik */
    uint64_t rs;                        /* rastgele sayi durumu */
} SkipList;

static uint64_t rastgele(SkipList *s) { s->rs ^= s->rs << 13; s->rs ^= s->rs >> 7; s->rs ^= s->rs << 17; return s->rs; }
```

Her düğüm kendi seviyesi kadar `ileri` pointer'ı taşıyor; Ders 8.14'teki esnek dizi üyesi sayesinde tek bir `malloc` ile, tam gereken boyutta. Baştaki gözcü düğüm (Ders 8.3) bütün seviyelerde var, bu yüzden "ilk düğümden önce ekle" diye bir özel durum yok. Rastgele sayılar, Ders 8.13'teki xorshift; yapıya bir **tohum** veriliyor.

### Seviye seçimi

Yazı-turaları tek tek atmak yerine tek bir 64 bitlik rastgele sayının bitlerini kullanıyoruz: her bit bağımsız bir yazı-tura. Seviye, sondaki ardışık 1 bitlerinin sayısı artı bir:

```c
/* Seviye: yazi-tura at, tura geldikce bir cik. P(seviye >= k) = 2^-(k-1). Bitlerle: sondaki 1'lerin sayisi + 1. */
static int rastgele_seviye(SkipList *s) {
    uint64_t r = rastgele(s);
    int k = 1;
    while ((r & 1) && k < MAKS_SEVIYE) { k++; r >>= 1; }
    return k;
}
```

(Daha da kısası: `1 + __builtin_ctzll(~r)`, Ders 5.9.) `MAKS_SEVIYE = 32` sınırı $2^{32}$ düğüme kadar yeterli; ötesinde seviye 32'nin üstüne çıkma olasılığı ihmal edilebilir ama düzen bozulmuyor, sadece üst seviyeler kalabalıklaşıyor.

### Arama

En üst seviyeden başla. Bir sonraki düğüm aranandan küçükse sağa git; değilse bir seviye in. En alt seviyede durduğun yerin sağındaki düğüm, aranan anahtar ya da ondan büyük ilk anahtar:

```c
/* En ust seviyeden basla: sagdaki x'ten kucukse saga git, degilse bir seviye in. */
bool skip_ara(SkipList *s, int x) {
    SDugum *n = s->bas;
    for (int i = s->seviye - 1; i >= 0; i--)
        while (n->ileri[i] && (s->karsilastirma++, n->ileri[i]->anahtar < x)) n = n->ileri[i];
    n = n->ileri[0];
    return n && n->anahtar == x;
}
```

(`(s->karsilastirma++, ...)` virgül işleci: önce sayacı artır, sonra karşılaştırmanın değerini kullan; sadece ölçüm için.)

### Ekleme ve silme

Ekleme, aramanın iniş yolunu kaydediyor: her seviyede, yeni düğümün **önüne** gelecek düğüm. Sonra yeni düğüm, kendi seviyesine kadar her seviyede, Ders 8.2'deki gibi listeye bağlanıyor:

```c
bool skip_ekle(SkipList *s, int x) {
    SDugum *once[MAKS_SEVIYE], *n = s->bas;            /* her seviyede, yeni dugumden onceki dugum */
    for (int i = s->seviye - 1; i >= 0; i--) {
        while (n->ileri[i] && n->ileri[i]->anahtar < x) n = n->ileri[i];
        once[i] = n;
    }
    if (n->ileri[0] && n->ileri[0]->anahtar == x) return false;
    int k = rastgele_seviye(s);
    if (k > s->seviye) { for (int i = s->seviye; i < k; i++) once[i] = s->bas; s->seviye = k; }
    SDugum *y = dugum(x, k);
    for (int i = 0; i < k; i++) { y->ileri[i] = once[i]->ileri[i]; once[i]->ileri[i] = y; }   /* her seviyede listeye ekle (Ders 8.2) */
    return true;
}

bool skip_sil(SkipList *s, int x) {
    SDugum *once[MAKS_SEVIYE], *n = s->bas;
    for (int i = s->seviye - 1; i >= 0; i--) {
        while (n->ileri[i] && n->ileri[i]->anahtar < x) n = n->ileri[i];
        once[i] = n;
    }
    n = n->ileri[0];
    if (!n || n->anahtar != x) return false;
    for (int i = 0; i < n->seviye; i++) once[i]->ileri[i] = n->ileri[i];
    free(n);
    while (s->seviye > 1 && !s->bas->ileri[s->seviye - 1]) s->seviye--;
    return true;
}
```

(`dugum(x, k)`, `k` pointer'lık bir düğüm ayırıyor; `malloc` hata kontrolü kısalık için yok.) Dönme yok, renk yok, yükseklik güncellemesi yok. Silme, eklemenin tam tersi. Dengeyi koruyan hiçbir kod yok, çünkü korunacak bir kural yok: her düğümün seviyesi eklendiği anda belirlendi ve bir daha değişmiyor.

```c
int main(void) {
    SkipList *s = skip_olustur(12345);
    int g[] = { 30, 10, 50, 20, 70, 40, 60, 80, 90, 25 };
    for (int i = 0; i < 10; i++) skip_ekle(s, g[i]);
    skip_ciz(s);
    printf("ara 40: %d, ara 45: %d\n", skip_ara(s, 40), skip_ara(s, 45));
    skip_sil(s, 50); skip_sil(s, 10);
    printf("50 ve 10 silindi:\n");
    skip_ciz(s);
    skip_yok_et(s);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined skip.c -o skip && ./skip
  seviye 4: bas------------------------------------- 90
  seviye 3: bas----------------- 40------------- 80- 90
  seviye 2: bas- 10--------- 30- 40- 50--------- 80- 90
  seviye 1: bas- 10- 20- 25- 30- 40- 50- 60- 70- 80- 90
ara 40: 1, ara 45: 0
50 ve 10 silindi:
  seviye 4: bas----------------------------- 90
  seviye 3: bas------------- 40--------- 80- 90
  seviye 2: bas--------- 30- 40--------- 80- 90
  seviye 1: bas- 20- 25- 30- 40- 60- 70- 80- 90
```

(`skip_ciz` her seviyede, o seviyede olmayan düğümlerin yerine çizgi koyuyor ki sütunlar hizalansın.) 10 düğümden 6'sı seviye 2'de, 3'ü seviye 3'te, 1'i seviye 4'te: yazı-turaların bu sefer biraz cömert düştüğü bir yapı. Kademeli düzen yok (`20` ve `25` seviye 1'de yan yana), ama arama yine üstten başlıyor: 70'i aramak için seviye 4'te 90'a bakıp inmek, seviye 3'te 40'a gidip 80'de inmek, seviye 2'de 40'tan 50'ye, seviye 1'de 50'den 60'a, 70.

Aynı rastgele işlemleri düz bir `bool` dizisiyle karşılaştıran test (2 milyon ekle/sil/ara, sonda en alt seviyenin sıralı olduğunun kontrolü) sanitizer'lı derlemede temiz:

```
0 hata, 2490 dugum (referans 2490)
```

---

## 3. Beklenen değerler

Bir düğümün bir üst seviyeye çıkma olasılığına $p$ diyelim (yukarıda $p = 1/2$).

**Düğüm başına pointer.** Seviye $k$'ya ulaşma olasılığı $p^{k-1}$; seviyesi bir geometrik dağılım (Ders 6.29). Beklenen seviye, yani beklenen pointer sayısı:

$$
E[\text{seviye}] = \sum_{k \ge 1} p^{k-1} = \frac{1}{1 - p}.
$$

$p = 1/2$'de 2 pointer: bir ikili ağaçla aynı. $p = 1/4$'te 1.33.

**Yükseklik.** $n$ düğümün herhangi birinin seviye $k$'yı aşma olasılığı en fazla $n \cdot p^k$ (birleşim sınırı). $k = \log_{1/p} n + c$ için bu $p^c$: yükseklik $\log_{1/p} n$'yi $c$ kadar aşma olasılığı üstel olarak küçülüyor. Yükseklik, yüksek olasılıkla $\log_{1/p} n + O(1)$.

**Arama maliyeti: geriye doğru analiz.** Arama yolunu **tersten** izle: bulunan düğümden, en alt seviyeden başla ve yukarı-sola doğru köke dön. Her adımda iki olasılık var: içinde bulunduğumuz düğümün bir üst seviyesi varsa (olasılık $p$) yukarı çık; yoksa (olasılık $1 - p$) sola git. Yazı-turalar bağımsız olduğu için, bir seviye yukarı çıkmak için beklenen adım sayısı $1/p$ (ilk "tura"ya kadar atış sayısı). Seviye $\log_{1/p} n$'ye ulaşmak:

$$
E[\text{arama}] \approx \frac{1}{p} \log_{1/p} n = \frac{1}{p \log_2(1/p)} \log_2 n.
$$

$p = 1/2$: $2 \log_2 n$. $p = 1/4$: $\frac{4}{2} \log_2 n = 2 \log_2 n$, aynı! Çarpan $\frac{1}{p \log_2(1/p)}$, $p = 1/e$'de en küçük ($e / \log_2 e \approx 1.88$); $1/2$ ile $1/4$ arası çok az fark yaratıyor, ama $1/4$ belleği üçte bir azaltıyor. Pugh'un önerisi bu yüzden $p = 1/4$.

Bütün bunlar **girdiden bağımsız**: hangi anahtarların hangi sırayla geldiği, hiçbir olasılığı etkilemiyor. Beklenti, yapının kendi yazı-turaları üzerinden.

---

## 4. Ölçüm

1 milyon anahtar, önce sıralı sonra karışık eklenip karışık sırayla aranıyor; karşılaştırma için Ders 8.10'daki kırmızı-siyah ağaç:

```
$ cc -std=c11 -O2 -Wall olcum.c ../rb/rb.c -o olcum -lm && ./olcum
sirali : seviye=21  dugum basina 2.00 pointer  arama basina 39.3 karsilastirma (2 log2 n = 39.9)
         skip list: ekle 87 ns  ara 255 ns     kirmizi-siyah: ekle 151 ns  ara 121 ns  (2000000)
         seviye dagilimi: 1:499434 2:249993 3:125495 4:62563 5:31195 6:15727 7:7750 8:3917 ...
karisik: seviye=21  dugum basina 2.00 pointer  arama basina 38.3 karsilastirma (2 log2 n = 39.9)
         skip list: ekle 310 ns  ara 374 ns     kirmizi-siyah: ekle 163 ns  ara 129 ns  (2000000)
10 tohum, 1M anahtar, arama basina karsilastirma: 37.3 37.2 38.3 38.4 39.2 37.4 38.3 39.3 37.8 40.0
```

- **Teori ve ölçüm**: düğüm başına tam 2.00 pointer; seviye dağılımı her seviyede yarıya iniyor (499 bin, 250 bin, 125 bin, ...); yükseklik 21 ($\log_2 10^6 \approx 20$); arama başına 38–39 karşılaştırma, $2 \log_2 n = 39.9$ tahmini.
- **Sıralı girdi hiçbir şeyi bozmuyor**: Ders 8.8'deki düz BST'yi listeye çeviren girdi, burada karışık girdiyle aynı karşılaştırma sayısını veriyor.
- **On farklı tohum**: 37.2 ile 40.0 arası, ortalamanın (38.3) en fazla %3 altında ve %4 üstünde. Rastgele yapının "şansı" pratikte hissedilmiyor.
- **Süre**: kırmızı-siyah ağaç aramada 2–3 kat hızlı. Skip list arama başına 2 log₂ n düğüme dokunuyor (ağaç yaklaşık $\log_2 n$'e), ve her düğüm ayrı, rastgele yerlerde duran bir `malloc` bloğu; her adım muhtemelen bir cache kaçırması. Sıralı eklemede skip list hızlı (87 ns), çünkü yeni düğümler hep sona ekleniyor ve iniş yolu cache'te; karışık eklemede 310 ns.

$p = 1/4$ ile aynı ölçüm (seviye seçiminde `(r & 3) == 3` ve `r >>= 2`):

```
sirali : seviye=11  dugum basina 1.33 pointer  arama basina 37.7 karsilastirma (2 log2 n = 39.9)
karisik: seviye=11  dugum basina 1.33 pointer  arama basina 41.5 karsilastirma (2 log2 n = 39.9)
10 tohum, 1M anahtar, arama basina karsilastirma: 39.4 38.3 38.1 38.0 38.7 36.0 36.9 36.7 36.2 37.0
```

Yarı yükseklik (11), üçte bir az pointer (1.33), aynı karşılaştırma sayısı: Bölüm 3'teki analizin dediği gibi.

### Neden kullanılıyor

Tek iş parçacıklı bir sözlük için skip list, kırmızı-siyah ağaçtan genelde daha yavaş. Ama:

- **Eş zamanlılık**: skip list'te bir ekleme, birbirinden bağımsız birkaç seviyede birer pointer değiştiriyor; ağaçtaki gibi bir alt ağacı yeniden düzenleyen bir dönme yok. Her seviyedeki ekleme ayrı ayrı, kilitsiz (atomik karşılaştır-ve-değiştir ile; Faz 10) yapılabiliyor. Java'nın `ConcurrentSkipListMap`'i bu yüzden var; kilitsiz bir kırmızı-siyah ağaç çok daha zor.
- **Basitlik**: kod yarım sayfa ve yanlış yapılacak bir dönme yok. Redis'in sıralı kümeleri (`ZSET`), LevelDB ve RocksDB'nin bellek içi tablosu (memtable) skip list.
- **Aralık sorguları**: en alt seviye sıralı bir bağlı liste; bir aralığın başını bulup oradan yürümek doğal (Ders 8.11'deki B+ ağacının yaprak listesi gibi).

---

## 5. Diğer rastgele yapılar

Aynı fikir başka yapılarda da var: deterministik bir dengeyi beklenen bir dengeyle değiştir.

- **Treap** (Seidel ve Aragon, 1989): her anahtara rastgele bir **öncelik** ver; ağaç anahtarlara göre BST, önceliklere göre heap (Ders 8.12). Bu iki koşulu sağlayan ağaç tek ve tam olarak "anahtarları önceliğe göre sıralanmış sırayla eklemenin" BST'si: rastgele sırayla kurulmuş bir BST (Ders 8.8, beklenen derinlik $2 \ln n$), girdinin sırası ne olursa olsun. Dengeyi dönmelerle koruyor ama kuralı tek.
- **Rastgele pivotlu hızlı sıralama** (Ders 9.5): en kötü girdi diye bir şey yok, sadece kötü şans.
- **Rastgele tohumlu hash** (Ders 8.13): saldırganın çakışma üretmesini engellemek için.
- **Bloom filtresi** (Faz 9 ya da 12): bir kümeye üyeliği yanlış pozitif olasılığıyla, çok az bellekle cevaplayan bit dizisi.

Hepsinde ortak tuzak: rastgelelik ancak saldırgan onu **tahmin edemiyorsa** koruma sağlıyor. Bu dersteki gibi sabit bir tohumla başlayan bir skip list, tohumu bilen biri için deterministik bir yapı (Alıştırma 5).

---

## Alıştırmalar

**1** – $p = 1/2$ ve $p = 1/4$ için beklenen arama maliyetinin aynı olduğunu gördük. $p = 1/8$ ve $p = 1/16$ için $\frac{1}{p \log_2(1/p)}$ çarpanını ve düğüm başına beklenen pointer'ı hesapla. Hangisini seçerdin?

**2** – 1 milyon düğümde yüksekliğin 30'u aşma olasılığı için bir üst sınır ver ($p = 1/2$). Ölçülen 21 bununla uyumlu mu?

**3** – Skip list'te "sıralamada $i$. eleman" sorgusunu $O(\log n)$ beklenen zamanda yapmak istiyorsun. Her `ileri[k]` pointer'ının yanına neyi saklarsan yeter? Ekleme ve silmede bu bilgi nasıl güncellenir? (Redis'in `ZRANK` komutu bunu yapıyor.)

**4** – Treap'te bir anahtar eklemek: BST gibi yaprağa ekle, sonra önceliği ebeveyninden büyükse (max-heap) dönmelerle yukarı çıkar. Neden dönme kullanmak zorundayız; Ders 8.12'deki heap'in "yer değiştir" yöntemi burada neden işe yaramaz?

**5** – Bu dersteki skip list, sabit bir tohumla (`skip_olustur(12345)`) başlıyor. Kodun ve tohumun açık olduğu bir sunucuda bir saldırgan ne yapabilir? Nasıl önlersin?

<details>
<summary>Cevaplar</summary>

**1** – $p = 1/8$: çarpan $\frac{8}{3} \approx 2.67$, pointer $\frac{1}{1 - 1/8} \approx 1.14$. $p = 1/16$: çarpan $\frac{16}{4} = 4$, pointer $1.07$. $p$ küçüldükçe bellek $1$'e yaklaşıyor (neredeyse düz bir bağlı liste kadar) ama arama maliyeti hızla artıyor: her seviyede çok sayıda yatay adım. $1/2$ (çarpan 2, pointer 2) ile $1/4$ (çarpan 2, pointer 1.33) arasında $1/4$ açıkça daha iyi; $1/8$'de arama %33 pahalılaşıp bellek sadece %15 azalıyor. Pugh'un da önerisi $1/4$. Önemli bir istisna: düğümler büyükse (anahtar + değer yüzlerce bayt), pointer'ların bellek payı küçük ve $p = 1/2$ tercih edilebilir.

**2** – Bir düğümün seviyesinin 30'u aşma olasılığı $2^{-30}$. Birleşim sınırıyla, $10^6$ düğümden herhangi birinin aşma olasılığı en fazla $10^6 \cdot 2^{-30} = 10^6 / (1.07 \cdot 10^9) \approx 0.00093$, yani binde birden az. Ölçülen 21: $\log_2 10^6 \approx 19.9$'un biraz üstü, beklendiği gibi. (Yüksekliğin $\log_2 n + c$'yi aşma olasılığı $2^{-c}$ civarında: 21'i aşma olasılığı yaklaşık yarı, 25'i aşma olasılığı yaklaşık %3.)

**3** – Her `ileri[k]` pointer'ının yanına o pointer'ın **atladığı** düğüm sayısını (genişliğini, span) sakla: seviye 1'de hep 1, üst seviyelerde aradaki alt seviye düğümlerinin sayısı. $i$. elemanı bulmak için aramadaki iniş: her seviyede, toplam genişlik $i$'yi aşmadıkça sağa git. Eklemede yeni düğüm her seviyede `once[k]`'nın pointer'ını ikiye bölüyor: `once[k]`'nın genişliği, yeni düğüme kadar olan mesafe; yeni düğümün genişliği kalan. Mesafeyi bilmek için iniş sırasında her seviyede kaç düğüm atlandığı biriktiriliyor. Yeni düğümün seviyesinin üstündeki seviyelerde `once[k]`'nın genişliği sadece bir artıyor. Silme tersini yapıyor. Hepsi $O(\log n)$ beklenen. Bir dengeli ağaçta aynı işi her düğümde alt ağaç boyutu saklamak yapar (sıra istatistik ağacı, CLRS 14.1).

**4** – Heap'te elemanlar bir dizide ve yapının şekli sabit; sadece **değerleri** yer değiştirmek yeterli. Treap'te iki sıra aynı anda korunmalı: anahtarlar BST sırasında, öncelikler heap sırasında. Bir düğümün değerini ebeveyniyle takas etmek önceliği düzeltir ama anahtarları BST sırasından çıkarır (büyük anahtar sol alt ağaca düşer). Dönme, Ders 8.9'da gördüğümüz gibi içek sırayı (BST sırasını) koruyarak bir düğümü bir seviye yukarı çıkarıyor: tam istenen hamle. Beklenen dönme sayısı ekleme başına 2'den az (Seidel ve Aragon).

**5** – Tohum biliniyorsa her düğümün seviyesi önceden hesaplanabilir. Saldırgan, eklenecek anahtar sayısını ve sırasını kontrol edebiliyorsa, seviyeleri 1 çıkacak düğümleri (ya da en kötü şekli üretecek bir sırayı) seçip yapıyı neredeyse düz bir bağlı listeye çevirebilir: arama $O(n)$. Ders 8.13'teki hash taşkını saldırısının skip list hali. Önlem: tohumu program başlarken işletim sisteminin güvenli rastgele kaynağından almak (`getentropy` macOS ve Linux'ta, `/dev/urandom`), ve tahmin edilmesi zor bir üreteç kullanmak; xorshift'in çıktıları birkaç gözlemden sonra tahmin edilebiliyor. Kriptografik bir üreteç pahalıysa, en azından tohumu gizli ve süreç başına farklı tutmak.

</details>

---

## Kaynaklar

- William Pugh, "Skip Lists: A Probabilistic Alternative to Balanced Trees", *Communications of the ACM* 33(6), 1990.
- William Pugh, "A Skip List Cookbook", University of Maryland teknik rapor CS-TR-2286.1, 1990: genişlikli skip list ve diğer işlemler.
- Raimund Seidel ve Cecilia Aragon, "Randomized Search Trees", *Algorithmica* 16, 1996 (ilk hali *FOCS* 1989): treap.
- Rajeev Motwani ve Prabhakar Raghavan, *Randomized Algorithms*, Bölüm 8: skip list ve treap analizi.
- Redis kaynak kodu, `src/t_zset.c`: genişlikli skip list ile sıralı kümeler.

**Sıradaki ders:** Bellek havuzları ve arena ile veri yapıları. Faz 4'teki arena ile AST düğümü ayırma, tek seferde serbest bırakma.
