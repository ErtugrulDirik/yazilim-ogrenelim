---
title: "7.20 Boru hattı (pipelining)"
description: "Çamaşırhane benzetmesiyle boru hattı fikri; tek döngülü veri yolunu IF, ID, EX, MEM, WB aşamalarına bölmek ve aralarına boru hattı register'ları koymak; zaman diyagramı; gecikme (latency) ile verim (throughput) farkı; k aşamalı boru hattında n komutun k + n − 1 döngü sürmesi ve hızlanmanın k'ya yaklaşması; aşamaların dengesizliği ve register yükünün hızlanmayı sınırlaması."
---

Ders 7.19'un sonunda tek döngülü işlemcinin sorununu gördük: saat periyodu en yavaş komuta (`lw`, 800 ps) göre ayarlanıyor, ve her komut o 800 ps boyunca veri yolunun **tamamını** tutuyor. Oysa `lw` komut belleğinden çıktıktan sonra komut belleği boşta; ALU'dan çıktıktan sonra ALU boşta. Bu ders, o boşta kalan birimleri bir sonraki komuta vererek işlemciyi neredeyse beş kat hızlandıran fikri anlatıyor: **boru hattı** (pipeline). Bugün telefondaki çekirdekten sunucu işlemcisine kadar her işlemci boru hatlı.

---

## 1. Çamaşırhane

Dört torba çamaşırın her biri dört adımdan geçiyor: yıkama (30 dk), kurutma (30 dk), katlama (30 dk), dolaba koyma (30 dk).

**Sırayla:** bir torba bitmeden ötekine başlama. 4 torba × 2 saat = **8 saat**.

**Boru hattı:** ilk torba yıkamadan kurutmaya geçince ikinci torbayı makineye at.

```
saat:     0:00  0:30  1:00  1:30  2:00  2:30  3:00  3:30
torba A   yika  kurut katla dolap
torba B         yika  kurut katla dolap
torba C               yika  kurut katla dolap
torba D                     yika  kurut katla dolap
```

Toplam **3.5 saat**. İki önemli gözlem:

- **Tek bir torbanın süresi değişmedi**: hâlâ 2 saat. Boru hattı bir işi hızlandırmaz.
- **Birim zamanda biten iş arttı**: ısınma bittikten sonra her 30 dakikada bir torba çıkıyor, 2 saatte bir değil.

Bu iki ölçünün adı var ve bütün performans konuşmalarının temeli (Faz 11):

- **Gecikme** (latency): tek bir işin başlangıcından bitişine geçen süre.
- **Verim** (throughput): birim zamanda tamamlanan iş sayısı.

Boru hattı **verimi** artırır, gecikmeyi değil (hatta biraz kötüleştirir, Bölüm 4).

---

## 2. Beş aşamalı RISC-V boru hattı

Ders 7.19'daki veri yolunun beş adımı doğal aşamalar:

| Aşama | Ne yapar | Birim |
| --- | --- | --- |
| **IF** (Instruction Fetch) | Komutu getir, PC += 4 | Komut belleği |
| **ID** (Instruction Decode) | Çöz, register'ları oku, immediate üret | Register dosyası, kontrol |
| **EX** (Execute) | ALU işlemi, dal hedefi hesabı | ALU |
| **MEM** (Memory) | `lw`/`sw` için bellek | Veri belleği |
| **WB** (Write Back) | Sonucu register'a yaz | Register dosyası |

Aşamaların arasına **boru hattı register'ları** konur (`IF/ID`, `ID/EX`, `EX/MEM`, `MEM/WB`): her saat kenarında her aşama ürettiğini bir sonraki aşamanın register'ına bırakır ve yeni bir girdi alır. Bu register'lar bir komutun "yanında taşıdığı çanta": `rd` numarası, kontrol sinyalleri (Ders 7.19'daki RegWrite, MemToReg...), ara sonuçlar. WB aşamasındaki komut, register dosyasına hangi `rd`'yi yazacağını kendi çantasından okur; o sırada ID'de olan başka bir komutun `rd`'sinden değil.

Böylece her döngüde beş farklı komut beş farklı aşamada olur. Saat periyodu artık en yavaş **aşamaya** göre: Ders 7.19'daki değerlerle 200 ps, yani 5 GHz (tek döngülü tasarımın 800 ps'lik, 1.25 GHz'lik saatine karşı).

---

## 3. Zaman diyagramı

Birbirine bağımlı olmayan beş komutu boru hattından geçiren küçük bir program:

```c
/* 5 asamali boru hatti: bagimsiz komutlar icin zaman diyagrami */
#include <stdio.h>

int main(void) {
    const char *komut[] = { "addi x1,x0,1", "addi x2,x0,2", "addi x3,x0,3",
                            "addi x4,x0,4", "addi x5,x0,5" };
    const char *asama[] = { "IF", "ID", "EX", "MEM", "WB" };
    int n = 5, k = 5;
    int toplam = k + n - 1;

    printf("%-14s", "");
    for (int t = 1; t <= toplam; t++) printf("%4d", t);
    printf("\n");
    for (int i = 0; i < n; i++) {
        printf("%-14s", komut[i]);
        for (int t = 1; t <= toplam; t++) {
            int s = t - 1 - i;                       /* komut i, t. dongude hangi asamada? */
            printf("%4s", (s >= 0 && s < k) ? asama[s] : ".");
        }
        printf("\n");
    }
    printf("\nboru hatti: %d dongu (k + n - 1), boru hatsiz: %d dongu (k * n)\n", toplam, k * n);

    /* hizlanma: n buyudukce k'ya yaklasir */
    long ns[] = { 1, 5, 100, 1000000 };
    for (int j = 0; j < 4; j++) {
        double h = (double)(k * ns[j]) / (k + ns[j] - 1);
        printf("n=%-8ld  hizlanma = %.3f\n", ns[j], h);
    }
    return 0;
}
```

```
$ cc -O1 -Wall boru.c -o boru && ./boru
                 1   2   3   4   5   6   7   8   9
addi x1,x0,1    IF  ID  EX MEM  WB   .   .   .   .
addi x2,x0,2     .  IF  ID  EX MEM  WB   .   .   .
addi x3,x0,3     .   .  IF  ID  EX MEM  WB   .   .
addi x4,x0,4     .   .   .  IF  ID  EX MEM  WB   .
addi x5,x0,5     .   .   .   .  IF  ID  EX MEM  WB

boru hatti: 9 dongu (k + n - 1), boru hatsiz: 25 dongu (k * n)
n=1         hizlanma = 1.000
n=5         hizlanma = 2.778
n=100       hizlanma = 4.808
n=1000000   hizlanma = 5.000
```

Diyagramı **sütun** sütun oku: 5. döngüde beş komut aynı anda işlemcide, her biri farklı bir aşamada. Bu boru hattının ta kendisi. **Satır** satır okursan her komut hâlâ beş döngü sürüyor (gecikme değişmedi).

---

## 4. Hızlanmanın formülü ve sınırları

$k$ aşamalı bir boru hattında $n$ komut:

- İlk komut $k$ döngüde biter (boru hattının **dolması**).
- Sonraki her komut bir döngü sonra biter.
- Toplam: $k + n - 1$ döngü. Boru hattı olmadan (her komut $k$ kısa döngü): $k \cdot n$.

$$
\text{hızlanma} = \frac{k \cdot n}{k + n - 1} \xrightarrow{\;n \to \infty\;} k
$$

Tablo bunu gösteriyor: tek komut için hızlanma yok (1.0), 5 komut için 2.78, milyon komut için 5.0. Gerçek programlar milyarlarca komut çalıştırır, yani dolma maliyeti ihmal edilebilir; ideal boru hattında **CPI = 1** ama döngü $k$ kat kısa.

Peki o zaman neden 5 değil 50 aşama? Üç sınır var:

1. **Aşamalar eşit değil.** Saat en yavaş aşamaya göre. Ders 7.19'daki değerlerle register okuma/yazma 100 ps, diğerleri 200 ps; döngü 200 ps olmak zorunda ve ID/WB'de yarı zaman boşa gidiyor. 800 ps'lik tek döngüye karşı gerçek hızlanma $800 / 200 = 4$, 5 değil.
2. **Boru hattı register'larının maliyeti.** Her register'ın kendi gecikmesi var (~20–50 ps). Aşamalar kısaldıkça bu sabit yük orantısal olarak büyür; 50 ps'lik aşamaya 30 ps register eklemek döngüyü %60 uzatır. Bu yüzden gecikme biraz **kötüleşir**: tek bir `lw` 800 ps yerine $5 \times 200 = 1000$ ps (ve register yüküyle daha fazla) sürer.
3. **Tehlikeler** (hazards). Diyagramdaki komutlar bilerek bağımsız seçildi. `add x3,x1,x2` hemen `lw x1,...`'den sonra gelirse, `x1` henüz yazılmamışken okunmak istenir. Boru hattı ya beklemek (stall) ya da sonucu kısa yoldan iletmek zorunda. Bir sonraki dersin konusu, ve derin boru hatlarının asıl düşmanı: aşama sayısı arttıkça bir tehlikenin cezası da artar.

2000'lerin başında Intel Pentium 4 (Prescott) 31 aşamaya kadar çıktı; yüksek saat hızına ulaştı ama dal tahmini hatalarının (Ders 7.22) cezası o kadar büyüdü ki sonraki tasarımlar 14–20 aşamaya geri döndü. Aşama sayısı bir denge, "daha çok daha iyi" değil.

---

## Alıştırmalar

**1** – Bölüm 3'teki diyagramda 7. döngüde hangi komutlar hangi aşamada? 10 komut olsaydı son komut hangi döngüde biterdi?

**2** – Aşama gecikmeleri IF 250 ps, ID 150 ps, EX 200 ps, MEM 300 ps, WB 100 ps olsun. (a) Tek döngülü işlemcide saat periyodu? (b) Boru hatlı işlemcide? (c) Çok sayıda komut için hızlanma?

**3** – Soru 2'de MEM aşamasını ikiye bölüp (MEM1, MEM2: 150'şer ps) 6 aşamalı bir boru hattı yapsak döngü ne olur, hızlanma ne olur? Hangi aşama yeni darboğaz?

**4** – Boru hattı register'ı başına 20 ps yük eklenirse Soru 2(b)'deki döngü kaç ps olur? Tek bir komutun gecikmesi kaç ps olur, tek döngülü tasarımla karşılaştır.

**5** – Bir çamaşırhanede yıkama 30 dk, kurutma 60 dk, katlama 30 dk. Boru hattında saatte kaç torba çıkar? İkinci bir kurutma makinesi almak ne değiştirir? Bu, işlemcilerde neye karşılık gelir?

<details>
<summary>Cevaplar</summary>

**1** – 7. döngü: `addi x3` WB, `addi x4` MEM, `addi x5` EX (x1 ve x2 bitti). Genel kural: komut $i$ (0'dan) $t$. döngüde $t - 1 - i$. aşamada. 10 komutla son komut $k + n - 1 = 5 + 10 - 1 = 14$. döngüde biter.

**2** – (a) Tek döngü: tüm aşamaların toplamı, $250 + 150 + 200 + 300 + 100 = 1000$ ps. (b) Boru hattı: en yavaş aşama, MEM, **300 ps**. (c) Hızlanma $1000 / 300 \approx 3.33$. Dengesizlik (MEM 300, WB 100) ideal 5'ten çok kaybettiriyor.

**3** – MEM 150 + 150; yeni en yavaş aşama IF (250 ps). Döngü 250 ps, hızlanma $1000 / 250 = 4$. Darboğaz artık IF. Gerçek tasarımlarda en yavaş aşamayı bölmek tam olarak böyle yapılır (önbellek erişimini iki aşamaya yaymak); her bölmede darboğaz başka bir aşamaya kayar.

**4** – Döngü $300 + 20 = 320$ ps. Tek komutun gecikmesi $5 \times 320 = 1600$ ps; tek döngülü tasarımda 1000 ps (register yükü yok). Gecikme %60 kötüleşti, ama verim her 320 ps'de bir komut, tek döngülüde her 1000 ps'de bir: hızlanma $1000 / 320 \approx 3.1$.

**5** – Boru hattı en yavaş aşamanın hızında akar: her 60 dakikada bir torba, saatte **1 torba**. Yıkama ve katlama 30 dakika bekliyor. İkinci kurutma makinesiyle iki torba aynı anda kurur, ortalamada her 30 dakikada bir torba çıkar: saatte 2. İşlemcide bu, yavaş bir birimden **birden fazla** koymak: modern işlemcilerde birden çok ALU ve bellek portu var, ve her döngüde birden fazla komut başlatılıyor (superscalar, Ders 7.23).

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design: RISC-V Edition* (2. baskı), Bölüm 4.5–4.6: boru hattına genel bakış (çamaşırhane benzetmesi oradan), boru hatlı veri yolu.
- John Hennessy & David Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Ek C: boru hattı temelleri.
- Sarah Harris & David Harris, *Digital Design and Computer Architecture: RISC-V Edition*, Bölüm 7.5.

**Sıradaki ders:** Boru hattı tehlikeleri. Veri, kontrol, yapısal tehlike; forwarding, stall — komut zamanlamanın (scheduling) neden gerektiği.
