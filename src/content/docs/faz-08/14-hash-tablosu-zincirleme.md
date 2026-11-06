---
title: "8.14 Hash tablosu: zincirleme"
description: "Kova dizisi ve her kovada çakışan anahtarların bağlı listesi; string'den long'a opak bir sözlük: FNV-1a, saklanan hash ile ucuz karşılaştırma, esnek dizi üyesiyle tek bloklu girdi, pointer'a pointer ile arama/ekleme/silme; yük faktörü α ve başarılı aramada 1 + α/2, başarısızda α beklenen maliyet; α sınırını aşınca ikiye katlayıp yeniden dağıtma ve girdi başına 1.05 taşıma; 1 milyon anahtarda yük faktörü 0.5'ten 8'e çıkınca arama 62 ns'den 138 ns'ye; sözlükteki 235 976 kelimede anagram sınıfları."
---

Ders 8.13'teki hash fonksiyonu anahtarı bir kova numarasına çeviriyordu; farklı anahtarların aynı kovaya düşmesi (çakışma) kaçınılmazdı. Bir hash tablosu, çakışmaları nasıl çözdüğüyle tanımlanır. İki ana yol var. Bu dersteki **zincirleme** (separate chaining): her kova bir bağlı liste, aynı kovaya düşen bütün anahtarlar o listede. Ders 8.15'teki **açık adresleme**: her şey tek bir dizide, çakışan anahtar başka bir boş yuva arıyor.

Zincirleme hem en eski hem en basit yöntem: kovalar Ders 8.2'deki tek yönlü listenin başları. Çoğu ders kitabının, Java'nın `HashMap`'inin ve C++'ın `std::unordered_map`'inin yöntemi.

---

## 1. Arayüz

String anahtarlardan `long` değerlere bir **sözlük** (map, dictionary). Ders 8.1'deki gibi opak:

```c
/* tablo.h: string -> long sozluk, zincirlemeli hash tablosu */
#ifndef TABLO_H
#define TABLO_H
#include <stdbool.h>
#include <stddef.h>

typedef struct Tablo Tablo;

Tablo *tablo_olustur(void);
void   tablo_yok_et(Tablo *t);
bool   tablo_koy(Tablo *t, const char *anahtar, long deger);    /* varsa gunceller */
long  *tablo_bul(Tablo *t, const char *anahtar);                /* yoksa NULL */
bool   tablo_sil(Tablo *t, const char *anahtar);
size_t tablo_boyut(const Tablo *t);
void   tablo_istatistik(const Tablo *t);
/* butun girdileri gez */
void   tablo_her(const Tablo *t, void (*f)(const char *anahtar, long deger, void *ek), void *ek);
#endif
```

`tablo_bul` değerin kendisini değil **adresini** döndürüyor: hem "yok" (`NULL`) ile "değeri 0" ayrımı yapılabiliyor, hem de bulunan değer yerinde güncellenebiliyor (`(*v)++`). Adres, bir sonraki `tablo_koy` ya da `tablo_sil` çağrısına kadar geçerli. `tablo_her`, Ders 8.1'in Alıştırma 3'ündeki geri çağırma kalıbı; `ek` pointer'ı çağıranın kendi durumunu fonksiyona taşıyor (Ders 4.11).

Kullanım, bir sayaç:

```c
int main(void) {
    Tablo *t = tablo_olustur();
    const char *meyve[] = { "elma", "armut", "kiraz", "erik", "incir", "elma", "erik", "elma" };
    for (int i = 0; i < 8; i++) {
        long *v = tablo_bul(t, meyve[i]);
        tablo_koy(t, meyve[i], v ? *v + 1 : 1);
    }
    const char *sor[] = { "elma", "erik", "kiraz", "muz" };
    for (int i = 0; i < 4; i++) { long *v = tablo_bul(t, sor[i]); printf("%-6s %ld\n", sor[i], v ? *v : 0); }
    tablo_sil(t, "erik");
    printf("erik silindi: %s, boyut %zu\n", tablo_bul(t, "erik") ? "hala var" : "yok", tablo_boyut(t));
    tablo_istatistik(t);
    tablo_yok_et(t);
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined deneme.c tablo.c -o deneme && ./deneme
elma   3
erik   2
kiraz  1
muz    0
erik silindi: yok, boyut 4
  4 girdi, 8 kova, yuk 0.50, bos kova %62.5, en uzun zincir 2, basarili arama ort. 1.25 girdi, tasinan/girdi 0.00
```

---

## 2. Uygulama

```
 kova[]
  ┌───┐
0 │ / │
  ├───┤     ┌──────────────┐   ┌──────────────┐
1 │ ●─┼────►│ "elma"   3   │──►│ "kiraz"  1   │──► /
  ├───┤     └──────────────┘   └──────────────┘
2 │ / │
  ├───┤     ┌──────────────┐
3 │ ●─┼────►│ "armut"  1   │──► /
  ├───┤     └──────────────┘
  ...
```

```c
/* tablo.c: zincirleme. Kova = tek yonlu listenin basi (Ders 8.2). Kova sayisi 2'nin kuvveti. */
#include "tablo.h"
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct Girdi {
    struct Girdi *sonraki;
    uint32_t hash;                 /* saklanan hash: buyutmede ve karsilastirmada yeniden hesaplanmaz */
    long deger;
    char anahtar[];                /* esnek dizi uyesi (C99): anahtar girdiyle ayni blokta */
} Girdi;

struct Tablo {
    Girdi **kova;
    size_t kova_sayisi;            /* 2^k */
    size_t adet;
    long tasinan;                  /* istatistik: buyutmelerde tasinan girdi sayisi */
};

#ifndef MAKS_YUK
#define MAKS_YUK 1.0               /* yuk faktoru bunu gecince ikiye katla */
#endif

static uint32_t fnv1a(const char *s) {
    uint32_t h = 2166136261u;
    while (*s) { h ^= (unsigned char)*s++; h *= 16777619u; }
    return h;
}
```

Üç tasarım kararı:

- **Esnek dizi üyesi** (flexible array member, C99): struct'ın **son** alanı boyutu yazılmamış bir dizi olabilir (`char anahtar[]`). `sizeof(Girdi)` bu alanı saymıyor; struct için ayırdığın belleğe ne kadar eklersen dizi o kadar uzun. Burada tek bir `malloc` ile `sizeof *g + strlen + 1` bayt ayrılıyor ve anahtar girdinin sonuna yapışık duruyor. Anahtar için ayrı bir `strdup` olsaydı, her karşılaştırma bir pointer takibi ve büyük ihtimalle bir cache kaçırması daha demek olurdu (Ders 8.2'deki ölçüm). Tablo, çağıranın string'ini **kopyalıyor**: çağıran kendi tamponunu (`satir[128]` gibi) sonra değiştirebilir.
- **Saklanan hash**: her girdi kendi tam 32 bitlik hash'ini tutuyor. Zincirde ararken önce hash'ler karşılaştırılıyor (bir tamsayı karşılaştırması) ve `strcmp` sadece hash'ler eşitse çalışıyor. Aynı kovadaki farklı anahtarların tam hash'leri neredeyse her zaman farklı. Büyütmede de hash yeniden hesaplanmıyor.
- **Kova sayısı 2'nin kuvveti**: kova `h & (kova_sayisi - 1)`, bölme yok (Ders 8.5). Ders 8.13'ün uyarısı geçerli: bu ancak hash fonksiyonu alt bitleri iyi karıştırıyorsa güvenli. FNV-1a stringlerde bunu sağlıyor.

Bütün işlemler aynı yardımcıyı kullanıyor: anahtarın zincirdeki yerini, Ders 8.2'deki gibi, **o girdiyi gösteren pointer'ın adresi** olarak döndürmek.

```c
/* Anahtarin bulundugu (ya da eklenecegi) yeri gosteren pointer'in adresi (Ders 8.2) */
static Girdi **yer(const Tablo *t, const char *anahtar, uint32_t h) {
    Girdi **p = &t->kova[h & (t->kova_sayisi - 1)];
    while (*p && !((*p)->hash == h && strcmp((*p)->anahtar, anahtar) == 0))   /* once hash'i karsilastir: ucuz */
        p = &(*p)->sonraki;
    return p;
}
```

Anahtar varsa `*p` onun girdisi; yoksa `*p == NULL` ve `p` zincirin sonundaki `NULL` pointer'ın adresi, yani yeni girdinin bağlanacağı yer. Bulmak, eklemek ve silmek üç satıra iniyor:

```c
long *tablo_bul(Tablo *t, const char *anahtar) {
    Girdi *g = *yer(t, anahtar, fnv1a(anahtar));
    return g ? &g->deger : NULL;
}

bool tablo_sil(Tablo *t, const char *anahtar) {
    Girdi **p = yer(t, anahtar, fnv1a(anahtar));
    if (!*p) return false;
    Girdi *g = *p;
    *p = g->sonraki;
    free(g);
    t->adet--;
    return true;
}
```

Zincirlemede silme kolay: girdiyi listeden söküp atmak. Ders 8.15'te açık adreslemede bunun ne kadar zorlaştığını göreceğiz.

---

## 3. Yük faktörü

$n$ anahtar ve $m$ kova varsa **yük faktörü** $\alpha = n/m$: kova başına ortalama girdi sayısı. Hash fonksiyonu anahtarları kovalara rastgele dağıtıyormuş gibi davranıyorsa (Ders 8.13'ün ölçtüğü şey):

- **Başarısız arama** (anahtar yok): kovanın bütün zincirini gezmek gerekiyor. Beklenen zincir uzunluğu $\alpha$.
- **Başarılı arama**: aranan anahtar zincirde bir yerde. Ondan **önce** eklenip aynı kovaya düşen anahtarlar zincirde ondan önce (yeni girdiler sona ekleniyor). $i$. eklenen anahtardan sonra $n - i$ anahtar daha eklendi ve her biri $1/m$ olasılıkla aynı kovaya düştü. Ortalama:

$$
\frac{1}{n} \sum_{i=1}^{n} \left(1 + \frac{n - i}{m}\right) = 1 + \frac{n - 1}{2m} \approx 1 + \frac{\alpha}{2}.
$$

İkisi de $n$'ye değil sadece $\alpha$'ya bağlı. $\alpha$ sabit tutulursa her işlem $O(1)$ **beklenen** zamanda: 1 milyon ya da 1 milyar anahtar, fark etmiyor. "Beklenen" kelimesi önemli: en kötü durumda (bütün anahtarlar tek kovada) $O(n)$, ve Ders 8.13'teki hash taşkını tam bunu üretiyor. Dengeli ağaçların $O(\log n)$'i ise bir **garanti**.

### Büyütme

$\alpha$'yı sabit tutmak için kova dizisi büyümeli. Ders 4.24'teki dinamik dizinin stratejisi: $\alpha$ bir sınırı geçince kova sayısını **ikiye katla** ve bütün girdileri yeni kovalarına dağıt (rehash). Girdiler zincirlerden söküp yeni zincirlere takılıyor; `malloc` ya da `free` yok, ve hash saklı olduğu için hiçbir string yeniden okunmuyor.

```c
static bool buyut(Tablo *t) {
    size_t yeni_sayi = 2 * t->kova_sayisi;
    Girdi **yeni = calloc(yeni_sayi, sizeof *yeni);
    if (!yeni) return false;
    for (size_t i = 0; i < t->kova_sayisi; i++)
        for (Girdi *g = t->kova[i], *s; g; g = s) {
            s = g->sonraki;
            Girdi **k = &yeni[g->hash & (yeni_sayi - 1)];    /* hash saklandigi icin strlen/fnv yok */
            g->sonraki = *k; *k = g;                          /* yeni kovanin basina */
            t->tasinan++;
        }
    free(t->kova);
    t->kova = yeni;
    t->kova_sayisi = yeni_sayi;
    return true;
}

bool tablo_koy(Tablo *t, const char *anahtar, long deger) {
    uint32_t h = fnv1a(anahtar);
    Girdi **p = yer(t, anahtar, h);
    if (*p) { (*p)->deger = deger; return true; }             /* guncelle */
    if ((double)(t->adet + 1) > MAKS_YUK * t->kova_sayisi) {
        if (!buyut(t)) return false;
        p = yer(t, anahtar, h);                                /* kovalar degisti: yeri yeniden bul */
    }
    size_t uz = strlen(anahtar) + 1;
    Girdi *g = malloc(sizeof *g + uz);
    if (!g) return false;
    memcpy(g->anahtar, anahtar, uz);
    g->hash = h; g->deger = deger; g->sonraki = NULL;
    *p = g;                                                    /* zincirin sonuna */
    t->adet++;
    return true;
}
```

`buyut`'tan sonra `p` **geçersiz**: eski kova dizisinin içini gösteriyordu ve o dizi `free` edildi. Yeri yeniden bulmak şart; unutmak, ASan'ın hemen yakaladığı bir kullanım-sonrası-serbest hatası (Ders 4.23).

Kova sayısını ikiye katlayınca bir kovadaki her girdi ya aynı numaralı kovaya ya da `i + eski_sayi` numaralı kovaya gidiyor (hash'in bir biti daha devreye giriyor). Bazı uygulamalar bunu kullanıp zinciri sırayla ikiye bölüyor.

### Ölçüm

1 milyon anahtar (`"anahtar0"` ... `"anahtar999999"`), önceden üretilip bellekte sıralı duruyor ki ölçülen şey tablo olsun. Bulunanlar karışık sırayla, bulunmayanlar (`"yok0"`...) ayrıca aranıyor. `MAKS_YUK` derlemede değişiyor. Her yapılandırma üç kez çalıştırılıp en iyi süre alındı (süreler çalıştırmadan çalıştırmaya %10–20 oynuyor):

```
$ for y in 0.5 1.0 2.0 4.0 8.0; do cc -std=c11 -O2 -Wall -DMAKS_YUK=$y olcum.c tablo.c -o olcum && ./olcum; done
```

| `MAKS_YUK` | Gerçek $\alpha$ | Boş kova | En uzun zincir | Başarılı arama (girdi) | $1 + \alpha/2$ | Ekle | Bul | Bulma (yok) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0.5 | 0.48 | %61.9 | 6 | 1.23 | 1.24 | 60 ns | 62 ns | 16 ns |
| 1.0 | 0.95 | %38.1 | 8 | 1.46 | 1.48 | 56 ns | 65 ns | 18 ns |
| 2.0 | 1.91 | %14.2 | 10 | 1.93 | 1.96 | 55 ns | 61 ns | 23 ns |
| 4.0 | 3.81 | %2.2 | 15 | 2.90 | 2.91 | 63 ns | 82 ns | 35 ns |
| 8.0 | 7.63 | %0.1 | 26 | 4.91 | 4.82 | 80 ns | 138 ns | 57 ns |

(Bütün yapılandırmalarda istatistik satırı `tasinan/girdi 1.05` diyor; sanitizer'lı derleme temiz.)

- Ölçülen zincir maliyeti formülle neredeyse aynı: FNV-1a bu anahtarlarda rastgele gibi davranıyor.
- $\alpha \le 2$'de süre neredeyse sabit. Bir aramanın maliyetine baskın olan, zincir uzunluğu değil **cache kaçırmaları**: kova dizisinde bir okuma, girdinin kendisinde bir okuma. $\alpha$ büyüdükçe girdi başına bir kaçırma daha ekleniyor: $\alpha = 8$'de arama 2.2 kat yavaş.
- Bulunmayan anahtarlar çok daha hızlı: saklanan hash farklı olduğu için `strcmp` hiç çalışmıyor ve girdiler cache'e gelse bile anahtar baytlarına bakılmıyor.
- `MAKS_YUK = 1` (Java'nın 0.75'i, C++'ın 1.0'ı) makul bir varsayılan. Bellek açısından: `Girdi` başlığı 24 bayt + anahtar; kova pointer'ı girdi başına $8/\alpha$ bayt. $\alpha = 0.5$ kovalar için 16 bayt harcıyor, $\alpha = 8$ sadece 1 bayt.

Büyütmenin amortize maliyeti: tablo 8 kovadan başlayıp ikiye katlanarak $2^{20}$'ye geldi; taşınan girdi sayısı $8 + 16 + \dots + 2^{19} \approx 2^{20} = 1\,048\,576$, yani girdi başına 1.05 taşıma (Alıştırma 2). Ders 4.24'teki geometrik toplam: her girdi ortalamada $O(1)$ kez taşınıyor.

---

## 4. Uygulama: anagram sınıfları

İki kelime, harfleri aynıysa birbirinin **anagramı** (`listen`, `silent`). Bir kelimenin harflerini sıralarsak (`eilnst`) bütün anagramlarının ortak bir **imzası** oluyor. İmzayı anahtar yapan bir sayaç, sözlükteki bütün anagram sınıflarını tek geçişte buluyor:

```c
/* Anagram siniflari: harfleri siralanmis kelime = anahtar */
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "tablo.h"

static void imza(const char *k, char *out) {           /* "Listen" -> "eilnst" */
    int say[26] = { 0 }, j = 0;
    for (; *k; k++) if (isalpha((unsigned char)*k)) say[tolower((unsigned char)*k) - 'a']++;
    for (int c = 0; c < 26; c++) while (say[c]--) out[j++] = (char)('a' + c);
    out[j] = 0;
}

typedef struct { long en; char imza[64]; long sinif; } Enb;
static void en_buyuk(const char *a, long d, void *ek) {
    Enb *e = ek;
    if (d >= 2) e->sinif++;
    if (d > e->en) { e->en = d; strcpy(e->imza, a); }
}

int main(void) {
    FILE *f = fopen("/usr/share/dict/words", "r");
    if (!f) { perror("words"); return 1; }
    Tablo *t = tablo_olustur();
    char satir[128], im[128];
    long kelime = 0;
    while (fgets(satir, sizeof satir, f)) {
        satir[strcspn(satir, "\n")] = 0;
        imza(satir, im);
        long *v = tablo_bul(t, im);
        if (v) (*v)++; else tablo_koy(t, im, 1);
        kelime++;
    }
    Enb e = { 0 };
    tablo_her(t, en_buyuk, &e);
    printf("%ld kelime, %zu farkli imza, %ld anagram sinifi (2+ kelime)\n", kelime, tablo_boyut(t), e.sinif);
    printf("en buyuk sinif: \"%s\", %ld kelime:", e.imza, e.en);
    rewind(f);
    while (fgets(satir, sizeof satir, f)) {
        satir[strcspn(satir, "\n")] = 0;
        imza(satir, im);
        if (strcmp(im, e.imza) == 0) printf(" %s", satir);
    }
    printf("\n");
    tablo_istatistik(t);
    fclose(f);
    tablo_yok_et(t);
}
```

İmza, sıralama yerine harf sayma ile çıkarılıyor: 26 elemanlık bir sayaç dizisi, Ders 9.7'deki sayma sıralamasının (counting sort) küçük hali. $O(\text{uzunluk})$.

```
$ cc -std=c11 -O2 -Wall -Wextra -fsanitize=address,undefined anagram.c tablo.c -o anagram && ./anagram
235976 kelime, 215906 farkli imza, 15305 anagram sinifi (2+ kelime)
en buyuk sinif: "agnor", 11 kelime: angor argon goran grano groan nagor Orang orang organ rogan Ronga
  215906 girdi, 262144 kova, yuk 0.82, bos kova %44.0, en uzun zincir 9, basarili arama ort. 1.41 girdi, tasinan/girdi 1.21
```

(Sözlük büyük ölçüde nadir ve eski kelimelerden oluşuyor; `Orang` ve `orang` büyük/küçük harf farkıyla iki ayrı giriş.) 236 bin kelimeyi işlemek sanitizer'lı derlemede bile yarım saniyenin altında. Aynı işi bir dengeli ağaçla yapmak da mümkün, ve en büyük sınıfı bulduktan sonra imzaları **sıralı** gezmek isteseydik gerekli olurdu. Hash tablosunun gezinme sırası kovaların sırası, yani pratikte rastgele (Alıştırma 5).

---

## Alıştırmalar

**1** – Bölüm 3'teki başarılı arama formülünü, yeni girdiler zincirin **başına** eklenseydi yeniden türet. Sonuç değişir mi? Hangi durumda başa eklemek daha iyi olur?

**2** – Tablo 8 kovadan başlıyor ve $\alpha > 1$ olunca ikiye katlanıyor. 1 000 000 eklemede toplam kaç girdi taşınır? `tasinan/girdi = 1.05`'i hesapla. Anagram programında neden 1.21 çıktı?

**3** – `tablo_sil` hiç küçülmüyor. 1 milyon anahtar ekleyip 999 990'ını silersen ne olur? Küçültme ekle: $\alpha$ hangi değerin altına düşünce kova sayısını yarıya indirmelisin? $\alpha < 1/2$'de küçültmek neden kötü bir fikir?

**4** – Bir zincirde aranan anahtar bulununca onu zincirin **başına** taşımak (move-to-front) ne zaman faydalı? Bu, `tablo_bul`'un imzasındaki `const` eksikliğini nasıl açıklıyor?

**5** – `tablo_her` girdileri hangi sırayla veriyor? Aynı anahtarları farklı bir sırayla eklersen bu sıra değişir mi? Bir tablo büyüdüğünde? Python 3.7'den beri sözlükler **ekleme sırasını** koruyor; bunu zincirlemeli bir tabloda nasıl sağlarsın?

<details>
<summary>Cevaplar</summary>

**1** – Başa eklemede, $i$. anahtardan **sonra** eklenip aynı kovaya düşenler onun önünde. Onların sayısının beklentisi $(n - i)/m$, yani formül **aynı**: $1 + (n-1)/(2m)$. Değişen, kimin ucuz kimin pahalı olduğu: başa eklemede **yeni** anahtarlar hızlı bulunuyor, sona eklemede eskiler. Yeni eklenenlere daha sık erişilen iş yüklerinde (önbellekler, son kullanılan değişkenler) başa eklemek daha iyi. Ayrıca başa eklemek zincirin sonuna yürümeyi gerektirmiyor; ama bizim `tablo_koy` zaten varlık kontrolü için zinciri yürüyor, o yüzden sona eklemek bedava.

**2** – Büyütmeler 8 → 16 → ... → $2^{20}$. Her büyütmede o anki girdi sayısı (eski kova sayısı kadar, çünkü $\alpha$ tam 1'i geçtiğinde büyüyor) taşınıyor: $8 + 16 + \dots + 2^{19} = 2^{20} - 8 = 1\,048\,568$. Girdi başına $1\,048\,568 / 10^6 = 1.05$. Taşıma oranı, $n$'nin bir sonraki 2'nin kuvvetine ne kadar yakın olduğuna bağlı: $n$ bir büyütmeden hemen sonraysa oran 2'ye yaklaşır, hemen öncesindeyse 1'e. Anagram programında 215 906 imza, son büyütme $2^{17} = 131\,072$'de oldu: $2^{18} - 8 = 262\,136$ taşıma, $262\,136 / 215\,906 = 1.21$. Her durumda 2'den az: amortize $O(1)$.

**3** – Kova dizisi $2^{20}$ pointer, 8 MB, olarak kalıyor; 10 girdi için. `tablo_her` 1 milyon kovayı geziyor. Küçültme: $\alpha < 1/4$ olunca yarıya indir. Neden $1/2$ değil? $\alpha = 1$'de büyüyüp $\alpha = 1/2$'de küçülen bir tabloda, büyütmeden hemen sonra $\alpha = 1/2$; bir silme küçültmeyi, bir ekleme tekrar büyütmeyi tetikler. Sınırda gidip gelen bir iş yükü her işlemde $O(n)$ öder. $1/4$ ile büyütme ve küçültme arasında 4 katlık bir boşluk var: bir yeniden boyutlandırmadan sonra bir sonrakine kadar en az $n/2$ işlem gerekiyor, bu da amortize $O(1)$'i koruyor (Ders 4.24'teki aynı tuzak ve çözümü).

**4** – Erişimler eşit dağılmıyorsa: bazı anahtarlar çok sık aranıyorsa onlar zincirin başına yerleşir ve neredeyse her zaman ilk karşılaştırmada bulunur. $\alpha \le 1$'de zincirler zaten kısa, kazanç küçük; yük faktörü yüksek ya da hash zayıfsa önemli. Ama bulmak artık yapıyı **değiştiriyor**: `tablo_bul(const Tablo *t, ...)` yazamazsın. Ayrıca okuyan iki iş parçacığı artık aynı anda yazıyor demek; kilitsiz okuma imkânı kayboluyor (Faz 10). Bizim `tablo_bul`'un `const` olmaması, döndürdüğü `long *`'ın değeri değiştirmeye izin vermesinden kaynaklanıyor; ayrı bir `const long *tablo_bak(const Tablo *, ...)` eklemek iyi bir tasarım olurdu.

**5** – Kova sırasıyla, her kovada zincir sırasıyla: yani hash değerlerinin alt bitlerine göre. Farklı ekleme sırası sadece aynı kovadaki girdilerin sırasını değiştirir. Büyütme ise sırayı tamamen karıştırır (girdiler yeni kovalara dağılır ve kova başına eklendikleri için zincir sırası ters döner). Bu yüzden hash tablosunun gezinme sırasına **asla** güvenilmemeli; Ders 8.13'teki rastgele tohumlu hash'lerle sıra çalıştırmadan çalıştırmaya bile değişir. Ekleme sırasını korumak için girdileri ayrıca ekleme sırasıyla bir listede tutmak yeterli: her girdiye Ders 8.3'teki gibi bir çift yönlü liste düğümü ekle (silme $O(1)$ kalsın diye), gezinmeyi o listeden yap. Python'un yöntemi daha da kompakt: girdiler ekleme sırasıyla yoğun bir dizide, hash tablosu ise sadece o dizideki **indeksleri** tutuyor.

</details>

---

## Kaynaklar

- Thomas Cormen ve ark., *Introduction to Algorithms* (CLRS, 3. baskı), Bölüm 11.2: zincirlemeli hash tabloları ve Teorem 11.1–11.2 (beklenen arama maliyeti).
- Donald Knuth, *The Art of Computer Programming*, Cilt 3, Bölüm 6.4: ayrı zincirleme ve analizi.
- Brian Kernighan ve Rob Pike, *The Practice of Programming*, Bölüm 2.9: C'de zincirlemeli hash tablosu.
- Raymond Hettinger, "Modern Python Dictionaries: A confluence of a dozen great ideas", PyCon 2017: kompakt, sıra koruyan sözlük.

**Sıradaki ders:** Hash tablosu: açık adresleme. Doğrusal ve karesel sondalama, Robin Hood hashing ve silmede mezar taşları.
