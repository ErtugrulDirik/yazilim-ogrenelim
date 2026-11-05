---
title: "7.25 Cache organizasyonu"
description: "Bir önbelleğin içi: satır (blok), geçerli biti ve tag; doğrudan eşlemeli, küme-ilişkili ve tam ilişkili önbellekler; bir adresin tag / index / offset alanlarına bölünmesi ve bit genişliklerinin hesabı; yer değiştirme politikası (LRU); zorunlu, kapasite ve çakışma ıskaları (üç C); yazma politikaları (write-through, write-back, write-allocate); 4 KB'lık bir önbelleği C'de simüle edip iki dizinin 4 KB arayla çakışmasının doğrudan eşlemeli önbellekte isabeti %0'a düşürmesini, 2 yollu önbellekte %99.4'e çıkarmasını görmek."
---

Ders 7.24'te önbelleklerin **ne kadar** hızlı olduğunu ölçtük ve yerelliğin neden işe yaradığını gördük. Bu ders önbelleğin **nasıl** çalıştığını anlatıyor: bir adres geldiğinde donanım, verinin önbellekte olup olmadığını tek döngüde nasıl anlıyor? Cevap, Ders 5.2'deki maskeleme ve kaydırmanın donanımdaki en önemli uygulamalarından biri: adresin bitlerini üç parçaya bölmek.

---

## 1. Satır, tag, geçerli biti

Önbellek veriyi tek tek bayt olarak değil, **satır** (line, blok) olarak tutar: 64 bayt (ya da Apple M serisinde 128 bayt), adresi 64'ün katı olan hizalı bir bellek parçası (Ders 5.7'deki hizalama). Her satırın yanında iki küçük bilgi daha durur:

- **Geçerli** (valid) biti: bu yuvada gerçekten veri var mı? (Açılışta hepsi 0.)
- **Tag**: bu yuvadaki satır, belleğin **hangi** parçasından geldi?

Bir erişimde donanım soruyor: "aradığım adresin satırı bu yuvada mı?" Bunu da yuvanın tag'ini adresin tag'iyle karşılaştırarak anlıyor. Peki hangi yuvaya bakacak?

---

## 2. Doğrudan eşlemeli önbellek

En basit cevap: her bellek satırının gidebileceği **tek** bir yuva olsun. Önbellekte $S$ yuva varsa, satır numarası $m$ olan bellek parçası $m \bmod S$ numaralı yuvaya gider. $S$ ikinin kuvveti olduğu için mod alma sadece **alt bitleri almak** (Ders 5.7).

Bir adres böylece üç alana ayrılır:

```
 adres:   |        tag         |   index   |  offset  |
           ust bitler           yuva no.    satir ici bayt
```

- **Offset**: satırın içindeki bayt. Satır $B$ bayt ise $\log_2 B$ bit.
- **Index**: hangi yuva (küme). $S$ yuva varsa $\log_2 S$ bit.
- **Tag**: geri kalan üst bitler. Aynı yuvaya düşebilecek bütün satırları birbirinden ayırır.

Örnek: 4 KB önbellek, 64 baytlık satır. $4096 / 64 = 64$ yuva. Offset $\log_2 64 = 6$ bit, index $\log_2 64 = 6$ bit, tag geri kalan.

`0x12345` adresi:

```
0x12345 = 0001 0010 | 0011 01 | 00 0101
          tag 0x12    index 13  offset 5
```

Okuma şöyle olur: index ile yuva 13 seçilir (bir mux, Ders 7.19), yuvanın tag'i `0x12` ile karşılaştırılır (bir eşitlik devresi), geçerli bit de 1 ise **isabet** ve offset 5'teki bayt döndürülür. Değilse **ıska**: satır alt seviyeden getirilip yuvaya yazılır (eskisinin yerine) ve tag güncellenir.

Doğrudan eşlemenin zayıflığı: `0x13345` adresi de index 13'e düşer (tag `0x13`). Bu iki adres arasında gidip gelen bir program her seferinde öbürünü atar; önbelleğin geri kalan 63 yuvası boş olsa bile. Bölüm 6'daki deney bunu gösterecek.

---

## 3. Küme-ilişkili önbellek

Çözüm: her index bir yuvaya değil, $W$ yuvalık bir **kümeye** (set) işaret etsin. Bir satır kümesindeki $W$ yuvadan **herhangi birine** konabilir. Buna **$W$ yollu küme-ilişkili** ($W$-way set associative) önbellek denir.

Aynı 4 KB, 64 baytlık satır, 2 yollu: 64 yuva, 32 küme. Offset 6 bit, index $\log_2 32 = 5$ bit, tag bir bit uzar. Okumada index ile küme seçilir, kümedeki iki yuvanın tag'i **aynı anda** (iki karşılaştırıcı, paralel) adresin tag'iyle karşılaştırılır.

Uç durumlar:

| Yapı | Yol sayısı | Küme sayısı | Not |
| --- | --- | --- | --- |
| Doğrudan eşlemeli | 1 | yuva sayısı | En basit, en hızlı, en çok çakışma |
| $W$ yollu | $W$ | yuva / $W$ | Gerçek L1'ler 4–12 yollu |
| Tam ilişkili | yuva sayısı | 1 | Index yok; her yuvanın tag'i karşılaştırılır. TLB gibi küçük yapılarda (Ders 7.27) |

Yol sayısını artırmak çakışmaları azaltır ama her erişimde daha çok karşılaştırıcı çalışır: daha çok enerji ve biraz daha uzun gecikme. Tasarımcılar bunu dengeliyor: M2'nin büyük çekirdeklerindeki 128 KB'lık L1 veri önbelleği (boyutu `sysctl hw.perflevel0.l1dcachesize` ile Ders 7.24'te gördük) mikromimari ölçümlerine göre 8 yollu.

### Yer değiştirme politikası

Iska olunca kümedeki yuvalardan biri boşaltılmalı. Hangisi? En yaygın cevap **LRU** (least recently used): en uzun süredir kullanılmayanı at. Zamansal yerelliğin doğrudan uygulaması: yakın zamanda kullanılan yine kullanılacak. 2 yolda LRU tek bir bitle tutulur; 8 yolda tam LRU pahalı olduğu için donanım yaklaşık sürümler kullanır (ağaç tabanlı sözde-LRU).

---

## 4. Genel formül

Kapasite $C$, satır boyutu $B$, yol sayısı $W$, adres $A$ bit:

$$
\text{küme sayısı } S = \frac{C}{B \cdot W}, \qquad
\text{offset} = \log_2 B, \qquad
\text{index} = \log_2 S, \qquad
\text{tag} = A - \text{index} - \text{offset}
$$

Örnek: tipik bir x86-64 L1 veri önbelleği, 32 KB, 64 bayt satır, 8 yollu, 48 bitlik sanal adres. $S = 32768 / (64 \cdot 8) = 64$ küme. Offset 6, index 6, tag $48 - 12 = 36$ bit.

İlginç bir rastlantı değil: offset + index = 12 bit = 4 KB, yani **sayfa** boyutu (Ders 7.27). Index bitlerinin hepsi sayfa içi ofsette kalınca önbellek, adres çevirisi bitmeden **index ile küme seçmeye** başlayabilir; tag karşılaştırması çeviri bittikten sonra yapılır. Bu yüzden x86 L1'leri yıllarca "32 KB, 8 yol" olarak kaldı: kapasiteyi artırmak için yol sayısını artırmak gerekiyordu. M2'nin 16 KB'lık sayfaları (Ders 7.27'deki ölçüm) 128 KB / 8 yol = 16 KB'lık bir L1'e izin veriyor.

---

## 5. Iskaların üç türü ve yazma

Iskaları sebeplerine göre ayırmak, neyin düzeltilebileceğini gösterir (Mark Hill'in "üç C"si):

- **Zorunlu** (compulsory): bir satıra ilk erişim. Hiçbir önbellek bunu önleyemez (önceden getirici dışında). Büyük satır boyutu azaltır.
- **Kapasite** (capacity): çalışma kümesi önbellekten büyük. Daha büyük önbellek ya da daha az veri (Ders 7.26'da bloklama).
- **Çakışma** (conflict): önbellekte yer var ama satırlar aynı kümeye düşüyor. Daha çok yol ya da veriyi farklı adreslere dizmek.

**Yazma** iki soru doğurur:

- İsabette: **write-through** (hem önbelleğe hem alt seviyeye hemen yaz; basit ama trafik çok) ya da **write-back** (sadece önbelleğe yaz, satırı "kirli" (dirty) olarak işaretle; satır atılırken alt seviyeye yaz). Modern önbellekler write-back.
- Iskada: **write-allocate** (önce satırı getir, sonra yaz) ya da **no-write-allocate** (doğrudan alt seviyeye yaz). Write-back ile genelde write-allocate birlikte kullanılır.

Çok çekirdekli sistemlerde bir sorun daha var: iki çekirdeğin önbelleğinde aynı satırın iki kopyası olursa ve biri yazarsa? **Tutarlılık protokolleri** (cache coherence, MESI) bunu çözüyor; Faz 10'daki çok iş parçacıklı programlamanın donanım tarafı.

---

## 6. Simülasyon

Bölüm 2–3'teki her şeyi küçük bir simülatörde birleştirelim: 4 KB kapasite, 64 baytlık satır, ayarlanabilir yol sayısı, LRU.

```c
/* Kume-iliskili cache simulatoru: tag/index/offset ve LRU ile isabet/iska */
#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define SATIR 64                 /* satir (blok) boyutu, bayt */
#define KAPASITE (4 * 1024)      /* toplam 4 KB */

typedef struct { int gecerli; uint64_t tag; long son_kullanim; } Yol;

typedef struct {
    int yol_sayisi, kume_sayisi, offset_bit, index_bit;
    Yol y[64][64];               /* [kume][yol] */
    long zaman, isabet, iska;
} Cache;

static int log2i(int x) { int b = 0; while ((1 << b) < x) b++; return b; }

static void kur(Cache *c, int yol) {
    memset(c, 0, sizeof *c);
    c->yol_sayisi = yol;
    c->kume_sayisi = KAPASITE / SATIR / yol;
    c->offset_bit = log2i(SATIR);
    c->index_bit = log2i(c->kume_sayisi);
}

static void eris(Cache *c, uint64_t adres) {
    uint64_t index = (adres >> c->offset_bit) & (c->kume_sayisi - 1);
    uint64_t tag = adres >> (c->offset_bit + c->index_bit);
    Yol *k = c->y[index];
    c->zaman++;
    for (int w = 0; w < c->yol_sayisi; w++)
        if (k[w].gecerli && k[w].tag == tag) { c->isabet++; k[w].son_kullanim = c->zaman; return; }
    c->iska++;
    int kurban = 0;                                   /* bos yol ya da en eski (LRU) */
    for (int w = 0; w < c->yol_sayisi; w++) {
        if (!k[w].gecerli) { kurban = w; break; }
        if (k[w].son_kullanim < k[kurban].son_kullanim) kurban = w;
    }
    k[kurban] = (Yol){ 1, tag, c->zaman };
}

int main(void) {
    /* 1) Adres parcalama: 4 KB, 64 B satir, dogrudan eslemeli */
    Cache c;
    kur(&c, 1);
    printf("dogrudan eslemeli: %d kume, offset %d bit, index %d bit, tag geri kalan\n",
           c.kume_sayisi, c.offset_bit, c.index_bit);
    uint64_t ornek[] = { 0x12345, 0x12385, 0x13345 };
    for (int i = 0; i < 3; i++) {
        uint64_t a = ornek[i];
        printf("  adres 0x%05llx -> tag 0x%llx, index %llu, offset %llu\n",
               (unsigned long long)a,
               (unsigned long long)(a >> (c.offset_bit + c.index_bit)),
               (unsigned long long)((a >> c.offset_bit) & (c.kume_sayisi - 1)),
               (unsigned long long)(a & (SATIR - 1)));
    }

    /* 2) Iki dizi tam 4 KB arayla: a[i] ve b[i] ayni kumeye duser */
    printf("\na[i] + b[i], b = a + 4096 (ayni index'ler), 512 int (2+2 KB), 10 tur:\n");
    int yollar[] = { 1, 2, 4, 64 };
    for (int j = 0; j < 4; j++) {
        kur(&c, yollar[j]);
        for (int tur = 0; tur < 10; tur++)
            for (uint64_t i = 0; i < 512; i++) {
                eris(&c, 0x10000 + 4 * i);           /* a[i] */
                eris(&c, 0x11000 + 4 * i);           /* b[i] */
            }
        printf("  %2d yollu: isabet %5ld  iska %5ld  isabet orani %.1f%%\n", yollar[j],
               c.isabet, c.iska, 100.0 * c.isabet / (c.isabet + c.iska));
    }

    /* 3) Satir boyutunun etkisi: sirali tarama, satir basina 1 iska */
    kur(&c, 1);
    for (uint64_t i = 0; i < 1024; i++) eris(&c, 0x20000 + 4 * i);
    printf("\nsirali 1024 int (4 KB) ilk tarama: iska %ld (= 4096/64), isabet %ld\n", c.iska, c.isabet);
    return 0;
}
```

```
$ cc -O1 -Wall cache.c -o cache && ./cache
dogrudan eslemeli: 64 kume, offset 6 bit, index 6 bit, tag geri kalan
  adres 0x12345 -> tag 0x12, index 13, offset 5
  adres 0x12385 -> tag 0x12, index 14, offset 5
  adres 0x13345 -> tag 0x13, index 13, offset 5

a[i] + b[i], b = a + 4096 (ayni index'ler), 512 int (2+2 KB), 10 tur:
   1 yollu: isabet     0  iska 10240  isabet orani 0.0%
   2 yollu: isabet 10176  iska    64  isabet orani 99.4%
   4 yollu: isabet 10176  iska    64  isabet orani 99.4%
  64 yollu: isabet 10176  iska    64  isabet orani 99.4%

sirali 1024 int (4 KB) ilk tarama: iska 64 (= 4096/64), isabet 960
```

Üç bölüm:

1. **Adres parçalama.** `0x12345` ve `0x12385` aynı tag'e ama komşu index'lere düşüyor (64 bayt arayla: bir sonraki satır). `0x12345` ve `0x13345` ise tam 4 KB arayla: **aynı index, farklı tag**. Bu ikisi doğrudan eşlemeli önbellekte aynı yuva için yarışacak.
2. **Çakışma.** İki dizi, toplam 4 KB, önbellek de 4 KB: kapasite yeterli. Ama `b` tam `a + 4096`'da, yani her `a[i]` ile `b[i]` aynı kümeye düşüyor. Doğrudan eşlemeli önbellekte `a[i]` okunur, `b[i]` onu atar, `a[i+1]` (aynı satır!) yine ıska, ve böyle: **10 240 erişimin hepsi ıska**, isabet %0. Önbellek hiç yokmuş gibi, hatta daha kötü (her erişim bir satır getiriyor). 2 yollu önbellekte her kümede iki yer var: `a`'nın satırı ve `b`'nin satırı yan yana oturuyor. Sadece **64 zorunlu ıska** kalıyor (her dizi 2 KB = 32 satır, iki dizi 64 satır; ilk turda bir kez), isabet %99.4. 4 ya da 64 yol (tam ilişkili) daha fazla bir şey kazandırmıyor; çakışma ıskası zaten yok oldu.
3. **Zorunlu ıskalar ve satır boyutu.** 4 KB'ı sırayla okumak 64 ıska veriyor, 1024 erişimin 1/16'sı: her 64 baytlık satırın ilk `int`'i ıska, sonraki 15'i isabet (Ders 7.24, Alıştırma 4).

Bölüm 2'deki deney yapay görünüyor ama gerçek hayatta çok olur: 2'nin kuvveti boyutlu diziler (örneğin 1024 × 1024'lük bir matrisin sütunları, her biri 4 KB'ın katı arayla) gerçek önbelleklerde de aynı kümelere yığılır. Ders 7.26'daki sütun sırası gezinme deneyinin yavaşlığının bir parçası bu; bazı programcıların dizi boyutunu bilerek 1024 yerine 1040 yapmasının (dolgu, padding) sebebi de.

---

## Alıştırmalar

**1** – 32 KB, 64 baytlık satırlı, 8 yollu bir önbellekte 48 bitlik `0x7ffd1234abcd` adresinin tag, index ve offset değerlerini hesapla.

**2** – 256 KB, 128 baytlık satırlı, 4 yollu bir önbellekte 32 bitlik adreslerle tag kaç bit? Toplam kaç tag bitini saklamak gerekir? (Geçerli ve kirli bitlerini de sayarsan toplam ek bit oranı ne?)

**3** – Simülatörde Bölüm 2'deki deneyi **üç** diziyle (`0x10000`, `0x11000`, `0x12000`, her biri 256 `int` = 1 KB) ve 1, 2, 4 yolla tekrarla. 2 yollu önbellek bu sefer neden işe yaramaz?

**4** – Bölüm 6'daki iki dizi deneyinde `b`'yi `a + 4096` yerine `a + 4096 + 64` adresine koysan doğrudan eşlemeli önbellekte ne olur?

**5** – Write-back önbellekte bir satırın "kirli" biti neden gerekli? Write-through önbellekte gerekir mi?

<details>
<summary>Cevaplar</summary>

**1** – Küme sayısı $32768 / (64 \cdot 8) = 64$. Offset 6 bit, index 6 bit, tag 36 bit. `0x...abcd`'nin alt 12 biti `0xbcd` = `1011 1100 1101`: offset = alt 6 bit `001101` = **13** (`0xd`); index = sonraki 6 bit `101111` = **47**; tag = adres >> 12 = **`0x7ffd1234a`**.

**2** – Küme sayısı $262144 / (128 \cdot 4) = 512$; offset 7 bit, index 9 bit, tag $32 - 16 = 16$ bit. Satır sayısı $262144 / 128 = 2048$, her biri 16 tag biti: $2048 \times 16 = 32\,768$ bit = 4 KB tag. Geçerli + kirli ile satır başına 18 bit: $2048 \times 18 = 36\,864$ bit = 4.5 KB; 256 KB veriye oranı ~%1.8. Önbelleğin "görünmez" maliyeti küçük ama sıfır değil.

**3** – Ölçüm: 1 yollu ve 2 yollu: **7680 erişimin hepsi ıska**; 4 yollu: 48 ıska (3 dizi × 16 satır, sadece zorunlu), gerisi isabet. Üç dizi aynı kümeye düşüyor; 2 yollu kümede iki yer var. LRU ile `a`, `b`, `c` sırayla gelince her yeni gelen, en eskiyi (bir sonra lazım olanı!) atıyor: döngüsel erişimde LRU'nun en kötü durumu. Kural: aynı kümeye düşen $k$ akış için en az $k$ yol gerekir.

**4** – Simülatörde `0x11000` yerine `0x11040` ile ölçüm: doğrudan eşlemeli önbellekte **isabet %93.9** (10 240 erişimde 622 ıska), %0'a karşı. `b`'nin her satırı artık bir yuva kaymış: `a[i]` index $m$'ye düşüyorsa `b[i]` index $m+1$'e. Aynı anda kullanılan `a[i]` ve `b[i]` artık hiç çakışmıyor. Kalan çakışma şu: `a`'nın bir **sonraki** satırı ($m+1$) ile `b`'nin **şu anki** satırı aynı yuvaya düşüyor; `a` satır sınırını geçtiği anda `b`'nin satırını atıyor, ve satır başına birkaç ıska oluşuyor (zorunlu 64'ün üstündeki ~558). Tek bir satırlık dolgu (padding) çakışmaların ~%95'ini yok etti; 2 yollu önbellekte ise sonuç yine 64 ıska.

**5** – Write-back'te önbellekteki satır alt seviyeden **farklı** olabilir (yazıldı ama henüz geri yazılmadı). Satır atılırken bunun bilinmesi gerekir: kirliyse alt seviyeye yazılmalı, temizse sessizce atılabilir (alt seviyede zaten aynısı var). Kirli bit olmasaydı her atılan satırı yazmak gerekirdi; okuma ağırlıklı programlarda gereksiz trafik. Write-through'da her yazma zaten anında alt seviyeye gidiyor, önbellek ve alt seviye hep aynı: kirli bite gerek yok.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design: RISC-V Edition* (2. baskı), Bölüm 5.3–5.4: önbellek temelleri, küme-ilişkililik, ıska türleri.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 6.4: önbellek organizasyonu, $S$, $E$, $B$ parametreleri.
- Mark Hill & Alan Jay Smith, "Evaluating Associativity in CPU Caches" (IEEE Transactions on Computers, 1989): üç C modeli.
- Ulrich Drepper, "What Every Programmer Should Know About Memory" (2007), Bölüm 3.

**Sıradaki ders:** Cache dostu kod. Matris gezinme sırası deneyi, blocking (tiling) ile matris çarpımı.
