---
title: "8.15 Hash tablosu: açık adresleme"
description: "Bütün girdileri tek bir dizide tutmak ve çakışan anahtar için sırayla başka yuva aramak (sondalama); doğrusal sondalama ve birincil kümelenme, üçgen sayılarla karesel sondalama, Robin Hood hashing; Knuth'un sonda formülleriyle birebir uyuşan ölçümler ve yük 0.9'da en uzun zincirin 1025'ten 54'e inmesi; silmede neden mezar taşı gerektiği, mezarların birikip aramayı 4.6 kat yavaşlatması ve Robin Hood'un geri kaydırmalı silmesi; Apple M2'de bağımsız sorgularda zincirlemeyle başa baş, birbirine bağımlı sorgularda 3 kat hızlı."
---

Ders 8.14'teki zincirlemeli tabloda her girdi ayrı bir `malloc` bloğuydu ve bir arama en az iki farklı yere bakıyordu: kova dizisine ve girdinin kendisine. **Açık adresleme** (open addressing) pointer'ları tamamen kaldırıyor: girdilerin kendisi doğrudan dizide duruyor. Bir anahtarın ideal yuvası doluysa, belirli bir kurala göre **başka** yuvalara bakılıyor (sondalama, probing) ve ilk boş yuvaya yerleşiyor. Bu fikir bugünün en hızlı hash tablolarının (Google'ın Swiss Table'ı, Rust'ın `HashMap`'i, Python'un `dict`'i) temelinde. Ama bedelsiz değil: tablo dolmaya yaklaştıkça çöküyor ve silme işlemi zincirlemedeki kadar basit değil.

---

## 1. Yuva ve sondalama dizisi

```c
/* Acik adresleme: dogrusal, karesel ve Robin Hood sondalama; mezar tasli silme */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

typedef enum { BOS, DOLU, MEZAR } Durum;
typedef enum { DOGRUSAL, KARESEL, ROBIN } Yontem;

typedef struct { uint32_t anahtar; uint32_t deger; Durum durum; } Yuva;

typedef struct {
    Yuva *y;
    size_t kap;                 /* 2^k */
    size_t adet, mezar;
    Yontem yontem;
    long sonda;                 /* istatistik: bakilan yuva sayisi */
    long yeniden;               /* istatistik: mezar temizligi sayisi */
} Acik;

static uint32_t karistir(uint32_t h) {     /* fmix32 (Ders 8.13): alt bitler de iyi karisik */
    h ^= h >> 16; h *= 0x85ebca6bu; h ^= h >> 13; h *= 0xc2b2ae35u; h ^= h >> 16;
    return h;
}
```

Bu derste anahtarlar 32 bitlik tamsayı; üç yöntemi tek bir kodda karşılaştırabilmek için `yontem` alanı var. Her yuvanın üç durumu olabiliyor; üçüncüsünün (`MEZAR`) neden gerektiğini Bölüm 4'te göreceğiz.

Bir anahtarın **sondalama dizisi**, bakılacak yuvaların sırası: $h(k), h(k) + s_1, h(k) + s_2, \dots$ (modülo kapasite). Arama bu diziyi izliyor; anahtarı bulursa döner, **boş** bir yuvaya rastlarsa durur (anahtar eklenmiş olsaydı ilk boş yere konurdu, yani o boş yuvadan önce olurdu).

```c
/* i. denemenin yuvasi. Karesel: ucgen sayilar 0,1,3,6,10,... 2^k kapasitede butun yuvalari dolasir. */
static size_t yuva(const Acik *t, uint32_t h, size_t i) {
    size_t m = t->kap - 1;
    return t->yontem == KARESEL ? (h + i * (i + 1) / 2) & m : (h + i) & m;
}
```

**Doğrusal sondalama** (linear probing): $s_i = i$, yani bir sonraki yuva, sonra bir sonraki. En basit ve cache için en iyi yöntem: bakılan yuvalar bellekte yan yana, büyük ihtimalle aynı cache satırında (12 baytlık yuvalardan bir satıra 5 tane sığıyor). Sorunu **birincil kümelenme** (primary clustering): dolu yuvaların bir bloğu, ona düşen her anahtarı bloğun sonuna ekliyor ve blok büyüyor; büyüyen blok daha çok anahtar yakalıyor. Bloklar birleşince durum hızla kötüleşiyor.

**Karesel sondalama** (quadratic probing): adımlar büyüyor ve aynı yerden başlayan anahtarlar hızla birbirinden uzaklaşıyor. Saf $i^2$ kapasite 2'nin kuvvetiyken bütün yuvaları ziyaret etmiyor (Alıştırma 2); **üçgen sayılar** $i(i+1)/2$ ise ediyor. Aynı ideal yuvadan başlayan anahtarlar yine aynı diziyi izliyor (ikincil kümelenme), ama komşu yuvalardan başlayanlar artık birbirini bloklamıyor.

---

## 2. Arama ve ekleme

```c
Acik *acik_olustur(size_t kap, Yontem yon) {
    Acik *t = malloc(sizeof *t);
    t->y = calloc(kap, sizeof *t->y);           /* calloc: hepsi BOS (0) */
    t->kap = kap; t->adet = t->mezar = 0; t->yontem = yon; t->sonda = 0; t->yeniden = 0;
    return t;
}

Yuva *acik_bul(Acik *t, uint32_t x) {
    uint32_t h = karistir(x);
    for (size_t i = 0; i < t->kap; i++) {
        Yuva *s = &t->y[yuva(t, h, i)];
        t->sonda++;
        if (s->durum == BOS) return NULL;                      /* bos yuva: anahtar burada olamaz */
        if (s->durum == DOLU && s->anahtar == x) return s;     /* MEZAR: atla, devam et */
        if (t->yontem == ROBIN && s->durum == DOLU && uzaklik(t, yuva(t, h, i), s->anahtar) < i)
            return NULL;                                       /* Robin Hood: daha "zengin" biri var, x olsa burada olurdu */
    }
    return NULL;
}
```

(`malloc` hata kontrolleri kısalık için yok.) Ekleme, aramanın izlediği yolu izleyip ilk `BOS` ya da `MEZAR` yuvaya yazıyor:

```c
bool acik_ekle(Acik *t, uint32_t x, uint32_t deger) {
    if (acik_bul(t, x)) return false;
    if (t->adet + t->mezar + 1 > t->kap * 9 / 10) {             /* bu derste buyutme yok */
        if (t->mezar == 0) return false;                         /* gercekten dolu */
        temizle(t);                                              /* mezarlari supur */
    }
    uint32_t h = karistir(x);
    Yuva yeni = { x, deger, DOLU };
    for (size_t i = 0; ; i++) {
        size_t k = yuva(t, h, i);
        Yuva *s = &t->y[k];
        if (s->durum != DOLU) {                                /* BOS ya da MEZAR: buraya koy */
            if (s->durum == MEZAR) t->mezar--;
            *s = yeni;
            t->adet++;
            return true;
        }
        if (t->yontem == ROBIN) {
            size_t onun = uzaklik(t, k, s->anahtar), benim = uzaklik(t, k, yeni.anahtar);
            if (onun < benim) { Yuva g = *s; *s = yeni; yeni = g; }   /* zenginden al: yer degistir, eskiyi tasimaya devam */
        }
    }
}
```

Açık adreslemede yük faktörü $\alpha = n/m$ her zaman 1'den küçük ve tablonun **asla** tamamen dolmaması gerekiyor: boş yuva kalmazsa başarısız bir arama sonsuza kadar döner. Bu derste kapasite sabit ve %90'da tablo "dolu" sayılıyor; gerçek bir uygulama orada Ders 8.14'teki gibi kapasiteyi ikiye katlayıp her şeyi yeniden ekler.

### Robin Hood

Doğrusal sondalamanın bir sorunu da **adaletsizlik**: bazı anahtarlar ideal yuvalarına konuyor, bazıları kümenin sonuna kadar itilip onlarca yuva öteye. Ortalama makul olsa bile en kötü arama çok uzun.

**Robin Hood hashing** (Pedro Celis, 1986) kuralı basit: her girdinin ideal yuvasından **uzaklığı** belli (`uzaklik`). Eklerken bir yuvada, eklenen anahtardan **daha az** uzaktaki ("daha zengin") bir girdiye rastlarsan, yerini ona değil yeni anahtara ver ve o eski girdiyi alıp yola devam et. Zenginden alıp fakire veriyorsun: uzaklıklar dengeleniyor.

```c
/* Bir anahtarin "ideal" yerinden uzakligi (Robin Hood icin; dogrusal sondalamada) */
static size_t uzaklik(const Acik *t, size_t konum, uint32_t anahtar) {
    return (konum - karistir(anahtar)) & (t->kap - 1);
}
```

(`konum - ideal` işaretsiz çıkarma, dizinin sonundan başa saran girdiler için de doğru; Ders 8.5'teki `(bas - 1) & (kap - 1)` hilesi.)

Bu kural aramaya da bir kısayol veriyor: aranan anahtar $i$ adım uzaklıktayken uzaklığı $i$'den **küçük** bir girdiye rastlarsak, aranan anahtar orada olamaz; olsaydı ekleme sırasında o yuvayı zaten alırdı. Arama boş yuvaya kadar gitmeden duruyor.

---

## 3. Ölçüm: kümelenme

$2^{20}$ yuvalık bir tabloyu rastgele anahtarlarla yük faktörüne kadar doldurup her eklenen anahtarı arıyoruz (bulunan), sonra 1 milyon rastgele anahtarı arıyoruz (büyük ihtimalle yok). Karşılaştırma için Knuth'un formülleri: doğrusal sondalamada bulunan için $\frac12\left(1 + \frac{1}{1-\alpha}\right)$, bulunmayan için $\frac12\left(1 + \frac{1}{(1-\alpha)^2}\right)$; karesel için Knuth'un ikincil kümelenme yaklaşımı.

```c
            if (yon == DOGRUSAL)
                printf("%-10s %4.2f  %8.2f %8.2f  %8.2f %8.2f  %9ld\n", ad[yon], a, bul, 0.5 * (1 + 1 / (1 - a)), yok, 0.5 * (1 + 1 / ((1 - a) * (1 - a))), en);
            else if (yon == KARESEL)
                printf("%-10s %4.2f  %8.2f %8.2f  %8.2f %8.2f  %9ld\n", ad[yon], a, bul, 1 - log(1 - a) - a / 2, yok, 1 / (1 - a) - a - log(1 - a), en);
```

```
$ cc -std=c11 -O2 -Wall olcum.c -o olcum -lm && ./olcum
            yuk   bulunan  (teori)       yok  (teori)    en uzun
dogrusal   0.50      1.50     1.50      2.50     2.50         33
dogrusal   0.70      2.17     2.17      6.05     6.06        100
dogrusal   0.80      3.00     3.00     12.94    13.00        260
dogrusal   0.90      5.47     5.50     50.25    50.50       1025
karesel    0.50      1.43     1.44      2.16     2.19         20
karesel    0.70      1.84     1.85      3.80     3.84         30
karesel    0.80      2.20     2.21      5.89     5.81         68
karesel    0.90      2.87     2.85     12.11    11.40        104
Robin Hood 0.50      1.50               1.75                  10
Robin Hood 0.70      2.17               2.52                  17
Robin Hood 0.80      3.00               3.40                  31
Robin Hood 0.90      5.47               5.92                  54
```

(Sayılar ortalama bakılan yuva; "en uzun", herhangi bir anahtarı bulmak için gereken en fazla yuva.)

- Doğrusal sondalamada ölçüm teoriyle **ikinci ondalığa kadar** aynı. Knuth bu formülleri 1963'te türetmişti; doğrusal sondalama, ortalama durum analizi yapılan ilk algoritmalardan biri.
- $\alpha$ arttıkça bulunmayan anahtar maliyeti $1/(1-\alpha)^2$ ile patlıyor: %80'de 13 yuva, %90'da 50. Birincil kümelenmenin bedeli bu. En uzun arama %90'da **1025** yuva.
- Karesel sondalama kümelenmeyi kırıyor: %90'da bulunmayan 12, en uzun 104.
- **Robin Hood'un ortalama** başarılı arama maliyeti doğrusal sondalamayla **tamamen aynı** (Alıştırma 4), ama en uzun arama 1025'ten **54**'e iniyor. Başarısız aramalar erken durduğu için 50'den 6'ya. Ortalama aynı, dağılım çok daha dar.

Pratik sonuç: doğrusal sondalamalı tablolar genelde $\alpha \le 0.5$–$0.7$'de tutulur; Robin Hood ve Swiss Table gibi tasarımlar $0.875$'e kadar çıkabilir.

---

## 4. Silme ve mezar taşları

Zincirlemede silme, girdiyi listeden sökmekti. Açık adreslemede girdinin yuvasını `BOS` yapmak **yanlış**:

```
 A ve B aynı ideal yuvaya (3) düşüyor; B, A doluyken eklendiği için 4'e kondu.

  yuva:   3     4     5
        [ A ] [ B ] [   ]

 A'yı silip yuvayı BOS yaparsak:
        [   ] [ B ] [   ]

 B'yi ara: 3'ten başla → BOS → "yok". Ama B tabloda!
```

Boş yuva, aramaya "buradan sonrasına bakma" diyor; ama B'nin sondalama dizisi o yuvadan **geçiyordu**. Çözüm, silinen yuvaya özel bir işaret koymak: **mezar taşı** (tombstone). Arama mezarı dolu gibi atlıyor, ekleme onu boş gibi kullanıyor.

```c
bool acik_sil(Acik *t, uint32_t x) {
    Yuva *s = acik_bul(t, x);
    if (!s) return false;
    if (t->yontem == ROBIN) {                                  /* geri kaydirma: mezar tasi yok */
        size_t k = (size_t)(s - t->y), m = t->kap - 1;
        for (;;) {
            size_t sonraki = (k + 1) & m;
            Yuva *n = &t->y[sonraki];
            if (n->durum != DOLU || uzaklik(t, sonraki, n->anahtar) == 0) break;
            t->y[k] = *n;                                       /* bir geri cek */
            k = sonraki;
        }
        t->y[k].durum = BOS;
    } else {
        s->durum = MEZAR;                                       /* BOS yapamayiz: arkasindaki zincir kopar */
        t->mezar++;
    }
    t->adet--;
    return true;
}
```

Mezarların sorunu **birikmeleri**. Başarısız aramalar mezarlarda durmadığı için, tablo hep aynı sayıda anahtar tutsa bile çok sayıda ekleme-silmeden sonra mezarlar boş yuvaların yerini alıyor ve aramalar uzuyor. Sonunda tabloyu aynı kapasitede baştan kurmak (bütün `DOLU` girdileri yeni bir diziye eklemek) gerekiyor:

```c
/* Ayni kapasitede yeniden kur: butun DOLU yuvalari yeni diziye ekle, mezarlar kaybolur. */
static void temizle(Acik *t) {
    Yuva *eski = t->y;
    t->y = calloc(t->kap, sizeof *t->y);
    t->adet = t->mezar = 0;
    for (size_t i = 0; i < t->kap; i++)
        if (eski[i].durum == DOLU) acik_ekle(t, eski[i].anahtar, eski[i].deger);
    free(eski);
    t->yeniden++;
}
```

**Robin Hood** bunu tamamen önlüyor. Doğrusal sondalamada silinen yuvadan sonraki girdiler, ideal yuvalarında olmadıkları sürece bir **geri** çekilebiliyor: hepsi ideal yuvalarına bir adım yaklaşıyor ve boşluk zincirin sonuna kayıyor. İdeal yuvasında olan (uzaklığı 0) ya da boş bir yuvaya gelince duruluyor. Sonuç, o anahtar hiç eklenmemiş gibi bir tablo.

Yük faktörünü 0.5'te sabit tutup sürekli rastgele bir anahtarı silip yerine yenisini ekleyelim ($2^{16}$ yuva):

```
$ cc -std=c11 -O2 -Wall mezar.c -o mezar && ./mezar
dogrusal + mezar tasi:
       0 sil+ekle sonra: mezar     0, basarisiz arama   2.49 yuva, temizlik 0
    5000 sil+ekle sonra: mezar  4461, basarisiz arama   3.10 yuva, temizlik 0
   10000 sil+ekle sonra: mezar  8312, basarisiz arama   3.77 yuva, temizlik 0
   15000 sil+ekle sonra: mezar 11555, basarisiz arama   4.47 yuva, temizlik 0
   20000 sil+ekle sonra: mezar 14302, basarisiz arama   5.18 yuva, temizlik 0
   25000 sil+ekle sonra: mezar 16714, basarisiz arama   6.03 yuva, temizlik 0
   30000 sil+ekle sonra: mezar 18811, basarisiz arama   6.99 yuva, temizlik 0
   50000 sil+ekle sonra: mezar 24714, basarisiz arama  11.61 yuva, temizlik 0
   75000 sil+ekle sonra: mezar 13055, basarisiz arama   4.82 yuva, temizlik 1
  100000 sil+ekle sonra: mezar 22973, basarisiz arama   9.65 yuva, temizlik 1
Robin Hood + geri kaydirma:
       0 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
    5000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   10000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   15000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   20000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   25000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   30000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   50000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
   75000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
  100000 sil+ekle sonra: mezar     0, basarisiz arama   1.75 yuva, temizlik 0
```

Anahtar sayısı hiç değişmedi (32 768), ama mezar taşlı tabloda başarısız arama 2.5 yuvadan 11.6'ya, **4.6 kat** çıktı: aramanın gördüğü "etkin" yük faktörü, anahtarlar + mezarlar, 0.5'ten 0.88'e. Temizlik onu sıfırlıyor ve birikme yeniden başlıyor. Robin Hood'da her şey sabit.

Üç yöntem, aynı rastgele işlemleri düz bir `bool` dizisiyle (referans) karşılaştıran bir testten (2 milyon ekle/sil/bul, temizliği de tetikleyecek kadar küçük bir tablo) sanitizer'lı derlemede hatasız geçiyor:

```
yontem 0: 0 hata, 1487 anahtar (referans 1487), 429 temizlik
yontem 1: 0 hata, 1487 anahtar (referans 1487), 511 temizlik
yontem 2: 0 hata, 1487 anahtar (referans 1487), 0 temizlik
```

---

## 5. Zincirlemeye karşı: süre

Yuva sayısı neden süreye tam yansımıyor? Ders 7.23'teki sırasız yürütmenin etkisi. Bunu görmek için yöntem dalı ve istatistik sayacı olmayan **yalın** bir doğrusal sondalama yazalım: yuva 8 bayt, anahtar 0 "boş" anlamına geliyor (0 anahtar olarak kullanılmıyor):

```c
typedef struct { uint32_t anahtar, deger; } Yuva;
...
    for (size_t i = 0; i < n; i++) { size_t k = karistir(q[i]) & m; while (y[k].anahtar != q[i]) k = (k + 1) & m; s += y[k].deger; }
```

Aynı anahtarlarla bir de zincirlemeli tablo (düğüm başına `malloc`, Ders 8.14'ün tamsayı hali), $2^{22}$ yuva/kova, sorgular karışık sırada:

```
$ cc -std=c11 -O2 -Wall yalin.c -o yalin && ./yalin 0.5 && ./yalin 0.8
yuk 0.5  yalin dogrusal  bulunan  11.2 ns  bulunmayan  33.8 ns
yuk 0.5  zincirleme      bulunan  16.8 ns  bulunmayan  16.1 ns  (1)
yuk 0.5  bagimli sorgu:  dogrusal  65.9 ns  zincirleme 176.9 ns  (0)
yuk 0.8  yalin dogrusal  bulunan  24.4 ns  bulunmayan  64.7 ns
yuk 0.8  zincirleme      bulunan  19.0 ns  bulunmayan  23.3 ns  (0)
yuk 0.8  bagimli sorgu:  dogrusal  66.8 ns  zincirleme 196.7 ns  (0)
```

İki farklı ölçüm var ve farklı şeyler söylüyorlar:

- **Bağımsız sorgular** (ilk iki satır): sorgular birbirinden bağımsız, işlemci aynı anda onlarca sorgunun bellek okumasını başlatabiliyor ve cache kaçırmalarının gecikmesi örtüşüyor. Ölçülen, gecikme değil **çıktı hızı** (throughput). Burada iki yöntem başa baş: düşük yükte doğrusal önde, yüksek yükte zincirleme. Bulunmayan anahtarlarda zincirleme açıkça hızlı, çünkü onun başarısız araması kısa bir zinciri gezmek, doğrusal sondalamanınki ise bir sonraki boş yuvaya kadar yürümek (yük 0.8'de 13 yuva).
- **Bağımlı sorgular** (üçüncü satırlar): her sorgunun anahtarı bir öncekinin sonucuna bağlı, örtüşme imkânsız. Bu, **gecikmeyi** ölçüyor: bir ağaçta yol takip etmek, bir derleyicinin sembol tablosunda bir ismin peşinden gitmek gibi gerçek iş yüklerinin durumu. Doğrusal sondalama tek bir bellek kaçırması (yaklaşık 60 ns, Ders 7.24), zincirleme en az iki: kova dizisi ve düğüm. Fark **3 kat**.

Bölüm 3'teki genel amaçlı (`yontem` dallı, istatistik sayaçlı, 12 baytlık yuvalı) kod bağımsız sorgularda bu yalın sürümden belirgin şekilde yavaş; Robin Hood'un aramada her yuva için `karistir` çağırması özellikle pahalı. Gerçek Robin Hood uygulamaları her yuvada uzaklığı (ya da hash'i) saklayarak bunu önlüyor, Ders 8.14'teki saklanan hash gibi.

| | Zincirleme (8.14) | Açık adresleme |
| --- | --- | --- |
| Bellek | Girdi başına `malloc` + pointer | Tek dizi; girdi başına ek yük yok, ama boş yuvalar |
| Yük faktörü | 1'in üstüne çıkabilir, yavaş bozulur | < 1 olmak zorunda; 1'e yaklaşınca çöker |
| Silme | Kolay | Mezar taşı ya da geri kaydırma |
| Kötü hash'e dayanıklılık | Uzun zincir | Kümelenme; çok daha kötü |
| Gecikme (bağımlı erişim) | 2+ kaçırma | Çoğunlukla 1 kaçırma |
| Girdilerin adresi | Sabit (pointer tutulabilir) | Büyütmede ve Robin Hood'da yer değiştiriyor |

Son satır C'de önemli: zincirlemeli bir tablonun döndürdüğü `long *` girdi silinmedikçe geçerli; açık adreslemede bir sonraki eklemede bile geçersiz olabilir.

---

## Alıştırmalar

**1** – Bölüm 4'teki örneği, mezar taşı ile tekrar et: A silindikten sonra B'yi ara, sonra yeni bir C anahtarı (ideal yuvası 3) ekle. C nereye konur? Konmadan önce neden B'nin olmadığından emin olmak gerekmiyor?

**2** – Kapasite 8 iken $i^2 \bmod 8$ ve $i(i+1)/2 \bmod 8$ dizilerini $i = 0, \dots, 7$ için yaz. Hangisi bütün yuvaları ziyaret ediyor? Saf karesel sondalamanın bu kusuru pratikte ne demek?

**3** – Doğrusal sondalamada $\alpha = 0.9$'da başarısız arama 50 yuva. $\alpha = 0.95$ ve $0.99$ için formülden hesapla. Tablolar neden genellikle $\alpha$ 0.5–0.875 aralığında büyütülüyor?

**4** – Ölçümde Robin Hood'un ortalama **başarılı** arama maliyeti doğrusal sondalamayla birebir aynı çıktı (1.50, 2.17, 3.00, 5.47). Neden? İpucu: bir anahtarı bulmanın maliyeti uzaklığı + 1; toplam uzaklık, girdilerin hangi sırayla yerleştiğine bağlı mı?

**5** – **Çift hashing** (double hashing): adım boyu $s_i = i \cdot h_2(k)$, $h_2$ ikinci bir hash fonksiyonu. Kapasite $2^r$ iken $h_2(k)$ neden **tek** sayı olmalı? Çift hashing birincil ve ikincil kümelenmeyi nasıl önlüyor, ve cache açısından bedeli ne?

<details>
<summary>Cevaplar</summary>

**1** – A silinince yuva 3 `MEZAR` oluyor: `[M] [B] [ ]`. B'yi ara: 3 mezar, atla; 4'te B, bulundu. C eklenirken ideal yuvası 3 bir mezar; ama önce `acik_bul(t, C)` çağrılıyor ve o, C'nin tabloda **olmadığını** boş yuvaya (5) kadar giderek doğruluyor. Ondan sonra ekleme ilk uygun yer olan mezara (3) yazıyor. Aramayı önce yapmak şart: C zaten 5'ten önceki bir yuvada olsaydı, mezara ikinci bir kopya yazılırdı. Eklemeden önceki bu arama mezarlarda **durmadığı** için doğru; mezarın "boş gibi kullanılması" sadece yazma yeri seçilirken.

**2** – $i^2 \bmod 8$: 0, 1, 4, 1, 0, 1, 4, 1. Sadece **3** farklı yuva (0, 1, 4 ofsetleri). $i(i+1)/2 \bmod 8$: 0, 1, 3, 6, 2, 7, 5, 4. **Hepsi**. Saf karesel sondalamada, ideal yuvası ve o iki yuva doluysa anahtar tabloda çok sayıda boş yuva varken bile **eklenemez**: ekleme sonsuz döngüye girer ya da başarısız olur. Bu yüzden saf $i^2$ ancak asal kapasiteyle ve $\alpha < 1/2$ garantisiyle kullanılabiliyor. Üçgen sayılar $2^r$ kapasitede bir permütasyon veriyor: $i(i+1)/2 \equiv j(j+1)/2 \pmod{2^r}$ ise $(i - j)(i + j + 1) \equiv 0 \pmod{2^{r+1}}$, ve $i - j$ ile $i + j + 1$'den biri tek olduğu için öteki $2^{r+1}$'e bölünmeli, ki $0 \le i, j < 2^r$ için bu sadece $i = j$'de mümkün (Ders 6.18).

**3** – $\frac12(1 + 1/(1 - \alpha)^2)$: $\alpha = 0.95$'te $\frac12(1 + 400) = 200.5$, $\alpha = 0.99$'da $\frac12(1 + 10\,000) = 5000.5$. Başarılı aramada da $0.99$'da 50.5. Her ek yüzde puanı maliyeti katlıyor. Tablonun yarısını boş tutmak bellek israfı gibi görünüyor, ama yuvalar küçükse (8 bayt) bu, zincirlemenin girdi başına `malloc` başlığı ve pointer maliyetinden genelde daha ucuz. Büyütme eşiği bellek ile hız arasında bir ayar: Swiss Table 7/8'de büyütüyor çünkü bir grup yuvanın kontrol baytlarını SIMD ile tek komutta tarayıp kümelenmenin maliyetini azaltıyor (Faz 11).

**4** – Doğrusal sondalamada hangi anahtarların hangi **yuva kümesini** kapladığı ekleme sırasından bağımsız: her durumda ideal yuvalar aynı ve her anahtar ilk boş yere itiliyor, yani dolu yuvaların kümesi aynı. Bir kümedeki girdilerin toplam uzaklığı, kümenin konumu ve içine düşen ideal yuvalarla belirleniyor; kimin hangi yuvada durduğu sadece bu toplamı farklı şekilde **paylaştırıyor**. Robin Hood paylaşımı değiştiriyor (zenginden fakire), toplamı değiştirmiyor; ortalama aynı kalıyor. Değişen, varyans: en uzun uzaklık. Başarısız aramalar ise erken durma kuralı sayesinde gerçekten kısalıyor; o kural ancak uzaklıklar dengeliyken anlamlı.

**5** – Sondalama dizisi $h_1(k) + i \cdot h_2(k) \bmod 2^r$, $i = 0, \dots, 2^r - 1$. Bunun bütün yuvaları ziyaret etmesi için $\gcd(h_2(k), 2^r) = 1$ olmalı (Ders 6.18); $2^r$ ile aralarında asal olmanın tek yolu tek olmak. Pratikte `h2 = (ikinci_hash(k) << 1) | 1` gibi. Aynı ideal yuvadan başlayan iki anahtarın farklı $h_2$'leri var, yani farklı yollar izliyorlar: hem birincil hem ikincil kümelenme yok, ve davranış "her anahtar rastgele bir permütasyon izliyor" idealine çok yakın. Bedeli: ardışık sondalar bellekte uzak, her biri büyük ihtimalle ayrı bir cache kaçırması. Doğrusal sondalamanın "bir sonraki yuva aynı cache satırında" avantajı kayboluyor. Modern donanımda bu yüzden genelde doğrusal sondalama (ya da onun gruplanmış hali Swiss Table) çift hashing'i yeniyor.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.4: açık adresleme, doğrusal sondalamanın analizi (Algoritma L) ve silme.
- Donald Knuth, "Notes on 'Open' Addressing", 1963 (yayımlanmamış not): doğrusal sondalamanın ilk analizi.
- Pedro Celis, "Robin Hood Hashing", doktora tezi, University of Waterloo, 1986.
- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 11.4.
- Matt Kulukundis, "Designing a Fast, Efficient, Cache-friendly Hash Table, Step by Step", CppCon 2017 (Abseil Swiss Table).

**Sıradaki ders:** Sembol tablosu. Derleyici için iç içe kapsamlı sembol tablosu ve string interning.
