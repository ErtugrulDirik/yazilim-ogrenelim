---
title: "7.23 Sırasız yürütme (out-of-order)"
description: "Sıralı boru hattının sınırı ve komut düzeyi paralellik (ILP); superscalar: döngü başına birden çok komut; gerçek bağımlılık (RAW) ile isim bağımlılıkları (WAR, WAW); register yeniden adlandırma; rezervasyon istasyonları ve yeniden sıralama tamponu (ROB) ile sırasız yürütüp sıralı tamamlama; Apple M2 üzerinde bağımlılık zinciri deneyleri: aynı sayıda toplama, 1, 4 ve 8 akümülatörle 8 kata varan hız farkı."
---

Ders 7.21'de derleyicinin komutları yeniden sıralayarak boru hattı beklemelerini yok ettiğini gördük, ve "büyük çekirdekler bunu donanımda yapar" demiştik. Bu ders o donanımı anlatıyor. Bugünkü masaüstü, dizüstü ve telefon çekirdeklerinin hepsi (Apple M serisi, Intel Core, AMD Zen, büyük ARM Cortex çekirdekleri) **sırasız** (out-of-order, OoO) çalışır: programdaki sırayı değil, verinin hazır olma sırasını izler. Sonunda bunun pratik bir sonucunu ölçeceğiz: aynı toplamayı farklı yazmak, kodu 8 kat hızlandırabiliyor.

---

## 1. Sıralı boru hattının sınırı

```
lw   x1, 0(x10)      # onbellekte yoksa 100+ dongu (Ders 7.24)
add  x2, x1, x3      # x1'i bekliyor
addi x4, x5, 1       # hicbir seyi beklemiyor!
addi x6, x7, 2       # bu da
```

Sıralı (in-order) bir boru hattında `add` beklerken arkasındaki her şey bekler; iki `addi`'nin hiçbir bağımlılığı olmasa bile. Derleyici bunu bazen önceden düzeltebilir (Ders 7.21), ama `lw`'nun kaç döngü süreceğini bilemez: veri önbellekte mi değil mi, çalışma anında belli olur.

Sırasız işlemcinin fikri: **komutları bir bekleme alanına koy; girdileri hazır olanı, programdaki sırasından bağımsız olarak çalıştır.** İki `addi` `lw` beklerken bitebilir.

---

## 2. Superscalar ve ILP

Aynı anda başka bir fikir: neden döngü başına **bir** komut? İki, dört, sekiz ALU koyup her döngüde birden çok komut başlatan işlemciye **superscalar** denir. Apple M2'nin büyük çekirdekleri döngüde 8 komut çözebiliyor ve 4 tamsayı ALU'su, 4 kayan nokta birimi var. Ölçü artık CPI değil, tersi: **IPC** (döngü başına komut).

Ama birden çok birim ancak birbirinden **bağımsız** komutlar varsa işe yarar. Bir programdaki aynı anda çalıştırılabilir komut miktarına **komut düzeyi paralellik** (ILP, instruction-level parallelism) denir. Bağımlılık zincirleri ILP'yi öldürür: her komut bir öncekini bekliyorsa 8 ALU'nun 7'si boştur.

---

## 3. Bağımlılıkların üç türü

```
1:  add  x1, x2, x3
2:  sub  x4, x1, x5      # RAW: 1'in yazdigi x1'i okuyor
3:  add  x1, x6, x7      # WAW: 1 ile ayni register'a yaziyor; WAR: 2'nin okudugu x1'e yaziyor
4:  mul  x8, x1, x9      # RAW: 3'un x1'ini okuyor
```

- **RAW** (read after write, *gerçek* bağımlılık): 2, 1'in **sonucuna** ihtiyaç duyuyor. Veri gerçekten akıyor; kaçınılmaz.
- **WAR** (write after read): 3, 2 okumadan önce `x1`'i yazarsa 2 yanlış değeri okur.
- **WAW** (write after write): 3, 1'den önce yazarsa, sonradan gelen 1'in yazması `x1`'in son değerini bozar.

WAR ve WAW **isim** bağımlılıkları: aralarında hiçbir veri akmıyor, sorun sadece ikisinin de `x1` **adını** kullanması. Programcı (ya da derleyici) 3 ve 4'te `x1` yerine kullanılmayan bir `x11` seçseydi bağımlılık olmazdı. Derleyici bunu yapamıyor çünkü ISA'da sadece 32 register var (Ders 7.4) ve tükeniyorlar.

---

## 4. Register yeniden adlandırma

Donanımın çözümü: programın gördüğü 32 **mimari** register'ın arkasında yüzlerce **fiziksel** register var (modern çekirdeklerde 200–400). Her komut bir hedef register'a yazacağı zaman, işlemci ona **yeni, boş bir fiziksel register** ayırır ve bir tabloda "`x1` şu an `p37` demek" diye not eder.

| Komut | Program | Yeniden adlandırma sonrası |
| --- | --- | --- |
| 1 | `add x1, x2, x3` | `add p37, p2, p3` (x1 → p37) |
| 2 | `sub x4, x1, x5` | `sub p38, p37, p5` (x4 → p38) |
| 3 | `add x1, x6, x7` | `add p39, p6, p7` (x1 → p39) |
| 4 | `mul x8, x1, x9` | `mul p40, p39, p9` (x8 → p40) |

Sağ sütunda WAR ve WAW yok oldu: 1 ve 3 farklı fiziksel register'lara yazıyor. Geriye sadece gerçek veri akışı kaldı: 1 → 2 ve 3 → 4, **iki bağımsız zincir**. 1 ile 3 aynı döngüde, 2 ile 4 bir sonraki döngüde çalışabilir.

Bu, Faz 16'da göreceğimiz SSA biçiminin (her değişkene bir kez atanır) donanımdaki karşılığı: ikisi de "isim" ile "değer"i ayırıyor.

---

## 5. Sırasız çekirdeğin yapısı

```
 sirali               sirasiz                        sirali
 -------------------  -----------------------------  ----------------
 Getir -> Coz ->      Rezervasyon   -> Yurutme      -> ROB -> Tamamla
          Yeniden     istasyonlari     birimleri       (program
          adlandir    (girdisini       (ALU, FP,        sirasiyla)
                      bekleyenler)     yukleme/saklama)
```

1. **Ön uç sıralı:** komutlar program sırasıyla getirilir (dal tahminiyle, Ders 7.22), çözülür ve yeniden adlandırılır.
2. **Rezervasyon istasyonları:** her komut girdilerini bekleyerek burada oturur. Bir sonuç üretildiğinde bütün istasyonlara duyurulur; girdileri tamamlanan komut boş bir yürütme birimine gönderilir. Burası **sırasız**.
3. **Yeniden sıralama tamponu (ROB, reorder buffer):** her komut, çözüldüğü sırayla ROB'a da bir kayıt olarak girer. Sırasız biten komutun sonucu henüz "resmi" değil. ROB'un başındaki komut bittiyse **tamamlanır** (commit/retire): sonucu mimari duruma geçer, kaydı silinir. Tamamlama **sıralı**.

Neden sonunda tekrar sıralı? **Kesin istisnalar** (precise exceptions) için. Bir `lw` sayfa hatası verirse (Ders 7.27, 7.28), işletim sistemi programı "o komuttan önceki her şey olmuş, sonraki hiçbir şey olmamış" halde görmeli; yoksa hatayı düzeltip programı kaldığı yerden devam ettiremez. Aynı mekanizma yanlış tahmin edilen dallar için de kullanılır: dalın arkasındaki komutlar ROB'da henüz tamamlanmamış duruyordur, dal yanlış çıkınca hepsi silinir ve hiçbiri mimari durumu değiştirmemiştir.

ROB'un boyutu, işlemcinin ne kadar **ileriye bakabildiğini** belirler: M2'nin büyük çekirdeklerinde 600 civarı komut. Önbellekte olmayan bir `lw` 100 döngü beklerken işlemci arkasındaki yüzlerce komutu çalıştırmaya devam edebilir, yeter ki onlar `lw`'nun sonucuna bağlı olmasın.

---

## 6. Deney: bağımlılık zinciri

İşlemcinin sırasız ve superscalar olduğunu doğrudan görebiliriz. 4096 `double`'ı (32 KB, L1 önbelleğe sığar; bellek değil işlemci ölçülüyor) üç şekilde toplayalım:

```c
/* Komut duzeyi paralellik (ILP): ayni toplama, farkli bagimlilik zinciri */
#include <stdio.h>
#include <time.h>

#define N 4096          /* 32 KB: L1 cache'e sigar, bellek degil CPU olculur */
#define TEKRAR 100000

static double simdi(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC, &t);
    return t.tv_sec + t.tv_nsec * 1e-9;
}

/* Tek akumulator: her toplama bir oncekini bekler (uzun bagimlilik zinciri) */
__attribute__((noinline)) static double topla1(const double *a) {
    double s = 0;
    for (int i = 0; i < N; i++) s += a[i];
    return s;
}

/* Dort akumulator: dort bagimsiz zincir, CPU bunlari ayni anda yurutebilir */
__attribute__((noinline)) static double topla4(const double *a) {
    double s0 = 0, s1 = 0, s2 = 0, s3 = 0;
    for (int i = 0; i < N; i += 4) {
        s0 += a[i]; s1 += a[i+1]; s2 += a[i+2]; s3 += a[i+3];
    }
    return (s0 + s1) + (s2 + s3);
}

/* Sekiz akumulator */
__attribute__((noinline)) static double topla8(const double *a) {
    double s[8] = {0};
    for (int i = 0; i < N; i += 8)
        for (int j = 0; j < 8; j++) s[j] += a[i+j];
    return ((s[0]+s[1])+(s[2]+s[3])) + ((s[4]+s[5])+(s[6]+s[7]));
}

static void olc(const char *ad, double (*f)(const double *), const double *a) {
    double t0 = simdi(), s = 0;
    for (int r = 0; r < TEKRAR; r++) {
        s += f(a);
        __asm__ volatile("" ::: "memory");  /* derleyici "ayni sonuc, bir kez hesaplarim" demesin */
    }
    double t = simdi() - t0;
    printf("%-14s toplam=%.0f  %.3f s  %.3f ns/toplama\n", ad, s, t, t * 1e9 / ((double)N * TEKRAR));
}

int main(void) {
    static double a[N];
    for (int i = 0; i < N; i++) a[i] = i % 7;
    olc("1 akumulator", topla1, a);
    olc("4 akumulator", topla4, a);
    olc("8 akumulator", topla8, a);
    return 0;
}
```

`-fno-vectorize -fno-slp-vectorize` ile derliyoruz: aksi halde clang `topla4` ve `topla8`'i SIMD komutlarına (Ders 7.29, Faz 11) çeviriyor ve iki etki karışıyor. Burada sadece skaler komutlarla ILP'yi görmek istiyoruz.

```
$ cc -O2 -fno-vectorize -fno-slp-vectorize ilp.c -o ilp && ./ilp
1 akumulator   toplam=1228500000  0.349 s  0.853 ns/toplama
4 akumulator   toplam=1228500000  0.087 s  0.212 ns/toplama
8 akumulator   toplam=1228500000  0.046 s  0.111 ns/toplama
```

(Apple M2; tekrarlarda 1 akümülatörlü sürüm 0.85–1.0 ns arası değişti, diğerleri kararlı.)

Üçü de tam olarak aynı sayıda toplama yapıyor ve aynı sonucu buluyor. Ama:

- **1 akümülatör: 0.85 ns.** Her `s += a[i]` bir önceki `s`'i bekliyor. M2'de kayan nokta toplamanın **gecikmesi** 3 döngü; ~3.5 GHz'de 3 döngü ≈ 0.86 ns. Ölçülen değer tam bu: işlemci her toplamayı bir öncekinin bitmesini bekleyerek yapıyor ve dört FP biriminden biri, o da üç döngüde bir çalışıyor.
- **4 akümülatör: 0.21 ns, 4 kat hızlı.** Dört bağımsız zincir; her 3 döngüde 4 toplama başlıyor. $0.86 / 4 \approx 0.21$.
- **8 akümülatör: 0.11 ns, 8 kat hızlı.** Sekiz zincir, 3 döngüde 8 toplama.

Sınır nerede? M2'de 4 FP birimi var, her biri her döngü yeni bir toplama başlatabilir (**verim** 1/döngü/birim), gecikme 3 döngü. Bütün birimleri sürekli dolu tutmak için uçuşta $4 \times 3 = 12$ bağımsız toplama gerekir (Little yasası: eşzamanlılık = verim × gecikme). 8 akümülatör bunun altında; 16 ile sınıra yaklaşılır (Alıştırma 2).

İşlemci bunları sırasız yürütmeyle **kendiliğinden** buluyor: `topla4`'ün döngüsü tek bir akış olarak geliyor, yeniden adlandırma ve rezervasyon istasyonları dört zincirin birbirini beklemediğini çalışma anında keşfediyor.

Neden derleyici `topla1`'i kendisi 4 akümülatöre çevirmiyor? Çünkü kayan nokta toplama **birleşmeli değil** (Ders 3.14): $(a+b)+c$ ile $a+(b+c)$ son bitlerde farklı olabilir. Toplamayı yeniden gruplamak sonucu değiştirebileceği için derleyici izin almadan yapamaz. `-ffast-math` (ya da sadece `-fassociative-math`) bu izni verir. Tamsayılarda toplama birleşmeli olduğu için derleyici bunu serbestçe yapar.

### Tamsayı zinciri: superscalar'ı görmek

Bir de doğrudan tamsayı komutlarıyla (arm64 inline assembly; derleyici dokunamasın diye):

```c
/* zincir: 4 toplama, her biri oncekini bekler */
__asm__ volatile("add %0, %0, #1\n add %0, %0, #1\n add %0, %0, #1\n add %0, %0, #1" : "+r"(a));
/* bagimsiz: 4 toplama, 4 farkli register */
__asm__ volatile("add %0, %0, #1\n add %1, %1, #1\n add %2, %2, #1\n add %3, %3, #1"
                 : "+r"(b), "+r"(c), "+r"(d), "+r"(e));
```

Her biri bir milyar kez:

```
zincir: 1.184 ns/tur  bagimsiz: 0.382 ns/tur
```

Tamsayı toplamanın gecikmesi 1 döngü: zincirde tur başına 4 döngü ≈ 1.14 ns, ölçülen 1.18. Bağımsız sürümde tur ~1.3 döngü sürüyor; turda 4 toplama artı döngü sayacı, karşılaştırma ve dal (7 komut) var. Yani işlemci **döngü başına 5'ten fazla komut** tamamlıyor. Superscalar'ı ve sırasız yürütmeyi tek satırda görmek bu.

---

## Alıştırmalar

**1** – Şu kodda yeniden adlandırma sonrası hangi bağımlılıklar kalır? Sınırsız birimli bir işlemci bunu en az kaç "adımda" (her adımda bağımsız komutlar aynı anda) çalıştırabilir?

```
add x1, x2, x3
add x4, x1, x1
add x1, x5, x6
add x7, x1, x4
```

**2** – Deneyi 2 ve 16 akümülatörle tekrarla. Bölüm 6'daki gecikme/verim modeline göre ne beklersin? (Ölçülen değerler cevaplarda.)

**3** – Bir bağlı listeyi gezen `while (p) { s += p->deger; p = p->sonraki; }` döngüsü, sırasız yürütmeden ne kadar faydalanabilir? Bir diziyi gezen döngüden farkı ne? (İpucu: bir sonraki adres ne zaman belli oluyor? Ders 7.24'teki ölçüm tam bunu kullanıyor.)

**4** – ROB 600 komutluksa ve döngü başına 8 komut çözülüyorsa, önbellekte olmayan bir `lw` (300 döngü) beklerken ön uç kaç döngü sonra durmak zorunda kalır? Bu, bellek gecikmesini "gizleme" kapasitesi hakkında ne söyler?

**5** – `topla1`'i önce `-O2 -ffast-math -fno-vectorize -fno-slp-vectorize`, sonra sadece `-O2 -ffast-math` ile derle. Her seferinde `objdump -d` ile döngüye bak ve süreyi ölç. Derleyici ne yaptı?

<details>
<summary>Cevaplar</summary>

**1** – Yeniden adlandırma: `p1 = p2+p3`, `p4' = p1+p1`, `p1' = p5+p6`, `p7 = p1'+p4'`. RAW zincirleri: 1 → 2 → 4 ve 3 → 4. WAW (1 ve 3, ikisi de `x1`) ve WAR (2 okuyor, 3 yazıyor) yok oldu. Adımlar: 1. adımda 1 ve 3 (bağımsız), 2. adımda 2, 3. adımda 4. **3 adım**, sırayla çalıştırmanın 4 adımına karşı. Yeniden adlandırma olmasaydı 3, 2 okuyana kadar beklemek zorunda kalırdı.

**2** – Model: $k$ akümülatörle her 3 döngüde $k$ toplama, en fazla döngüde 4. 2 akümülatör: $0.86 / 2 \approx 0.43$ ns beklenir; ölçülen **0.442 ns**. 16 akümülatör: model sınıra çarpar (12'den fazla bağımsız zincir var, ama birimler döngüde 4 toplamayla sınırlı): $0.29 / 4 \approx 0.07$ ns; ölçülen **0.085 ns** (döngü sayacı, yükleme komutları ve sonda 16 toplamanın birleştirilmesi de yer kaplıyor). 8'den 16'ya kazanç artık küçük: darboğaz gecikmeden verime geçti.

**3** – Neredeyse hiç. `p = p->sonraki` bir yükleme, ve bir sonraki yüklemenin **adresi** bu yüklemenin **sonucu**: kesin bir RAW zinciri. Sırasız yürütme, zincirdeki her halkanın bitmesini beklemek zorunda; `s += p->deger` gibi yan işleri paralel yapabilir ama ana zincir tamamen seri. Dizide ise `a[i+1]`'in adresi `a[i]`'nin değerine bağlı değil; işlemci onlarca yüklemeyi aynı anda başlatabilir. Bağlı listelerin dizilerden çoğu zaman çok yavaş olmasının iki sebebinden biri bu (diğeri önbellek, Ders 7.26). Ders 7.24'teki "işaretçi kovalama" ölçümü bu özelliği bilerek kullanıyor: saf gecikmeyi ölçmek için.

**4** – ROB'un dolması $600 / 8 = 75$ döngü sürer. `lw` ROB'un başında 300 döngü beklerken kendisi tamamlanamaz, arkasındakiler de tamamlanamaz (tamamlama sıralı); 75 döngü sonra ROB dolar ve ön uç durur. Kalan ~225 döngü kayıp. Yani sırasız yürütme bir önbellek ıskasının ancak bir kısmını gizleyebilir; RAM erişimi (yüzlerce döngü) hâlâ pahalı. Bu yüzden bellek hiyerarşisi (Ders 7.24) ve önbellek dostu kod (Ders 7.26) ayrı bir konu.

**5** – Ölçümler (M2):

- `-ffast-math`, vektörleştirme **kapalı**: döngü değişmedi, hâlâ tek `fadd d0, d1, d0` zinciri, **0.92 ns**. İzin vardı ama clang'ın bu döngüde yeniden gruplamayı yapan kısmı vektörleştirici; o kapalı olunca kimse kullanmadı.
- `-ffast-math`, vektörleştirme **açık**: döngü dört ayrı vektör akümülatöre (`v0`–`v3`, her biri 2 `double`) dönüştü: `fadd.2d v0, v4, v0`, `fadd.2d v1, v5, v1`, ... ve sonda birleştirme. Yani **8 bağımsız toplama zinciri**, tam da elle yazdığımız `topla8`'in SIMD hali. Süre **0.17 ns**, 5 kattan fazla hızlı.
- Karşılaştırma: `-ffast-math` olmadan, vektörleştirme açıkken `topla1` yine 0.93 ns: derleyici `double` toplamayı kendi başına yeniden gruplamıyor.

Bedel: sonuç bitleri toplama sırasına bağlı olarak `-O2`'dekinden farklı olabilir. Bu örnekteki tamsayı değerli `double`'larda fark çıkmadı (toplam yine 1228500000); genel durumda çıkabilir (Ders 3.14). Bir de: derleyicinin "yapabileceği" ile "yaptığı" aynı şey değil; tahmin etme, üretilen koda bak.

</details>

---

## Kaynaklar

- John Hennessy & David Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Bölüm 3: ILP, Tomasulo algoritması, yeniden adlandırma, ROB.
- R. M. Tomasulo, "An Efficient Algorithm for Exploiting Multiple Arithmetic Units" (IBM Journal, 1967): rezervasyon istasyonlarının ilk hali (IBM 360/91).
- Agner Fog, *The microarchitecture of Intel, AMD and VIA CPUs* ve *Instruction tables* (agner.org/optimize): komut gecikme ve verim tabloları.
- Dougall Johnson, "Apple M1 Firestorm microarchitecture" (dougallj.github.io): Apple çekirdeklerinin ölçülmüş birim sayıları ve ROB boyutu.

**Sıradaki ders:** Bellek hiyerarşisi. Register–L1–L2–L3–RAM–disk gecikmeleri, yerellik ilkesi.
