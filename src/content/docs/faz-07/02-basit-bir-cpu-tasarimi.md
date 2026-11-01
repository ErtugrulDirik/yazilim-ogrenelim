---
title: "7.2 Basit bir CPU tasarımı"
description: "Mantık kapısından işlemciye: NAND'dan AND/OR/NOT, yarım ve tam toplayıcı, çok bitli toplayıcı; multiplexer ve ALU; register ve saat; bellek; fetch–decode–execute döngüsü; Nand2Tetris'in Hack makinesi; her şeyi tek bir arayüzün arkasına koyan oyuncak bir işlemciyi C'de yazıp bir programı çalıştırmak."
---

Ders 7.1'de ISA'yı donanım ile yazılım arasındaki sözleşme olarak tanımladık, ve bir C döngüsünün makine komutlarına dönüştüğünü gördük. Ama bir makine komutu **çalıştığında** fiziksel olarak ne oluyor? Ders 0.2'de işlemcinin mantık kapılarından kurulduğunu söylemiştik. Bu ders o kapılardan işlemciye giden yolu, hızlı hızlı, baştan sona yürüyor; amaç her katmanı tasarlamak değil (bu başlı başına bir ders dizisi, Nand2Tetris), bir makine komutunun altında ne olduğunu **görmek**.

Sonunda, bütün bu donanımın yaptığı işi tek bir C döngüsü olarak yazacağız: **fetch–decode–execute**. Bu döngü, Faz 7'nin sonunda (Ders 7.30) yazacağımız RISC-V öykünücüsünün de, her yorumlayıcının (Faz 15) da kalbi.

---

## 1. Her şey NAND'dan

Ders 6.1'in alıştırmasında NAND'ın tek başına bütün mantığı ifade etmeye yettiğini kanıtlamıştık: $\neg p = \text{NAND}(p, p)$, ve $\text{AND}$, $\text{OR}$ bundan türüyor (De Morgan). Donanımda da öyle: bir NAND kapısı iki transistörle yapılabiliyor, ve her şey ondan kuruluyor.

```
NOT(a)    = NAND(a, a)
AND(a, b) = NOT(NAND(a, b))
OR(a, b)  = NAND(NOT(a), NOT(b))        (De Morgan)
XOR(a, b) = ...  (birkac NAND)
```

Bunlar Ders 5.1'deki `&`, `|`, `~`, `^` operatörlerinin **tek bit** halleri. `uint32_t` üzerindeki bir `&`, aslında yan yana dizilmiş 32 AND kapısı; hepsi aynı anda çalışıyor. Faz 5'te "32 bit paralel" dediğimiz şey, donanımda gerçekten 32 ayrı kapı.

---

## 2. Toplayıcı

İki biti toplamak: $0+0=0$, $0+1=1$, $1+0=1$, $1+1=10$ (sonuç 0, elde 1). Bu, Ders 5.4'teki özdeşlik: toplamın elde'siz kısmı XOR, elde ise AND.

```
yarim toplayici (half adder):
    toplam = a XOR b
    elde   = a AND b
```

Üç biti (iki sayı biti + alttan gelen elde) toplayan **tam toplayıcı** (full adder) iki yarım toplayıcıdan kuruluyor. $n$ tam toplayıcıyı, her birinin eldesini bir sonrakine vererek yan yana dizersen $n$ bitlik bir toplayıcı olur: Ders 3.8'deki `uint32_t` toplaması, 32 tam toplayıcılık bir zincir. Eldenin en soldan "düşmesi" (taşma, Ders 3.8) tam da bu zincirin sonundan çıkan bit.

Çıkarma ayrı bir devre gerektirmiyor: Ders 6.18'de gördük ki $-b \equiv \sim b + 1 \pmod{2^n}$ (ikiye tümleyen). Toplayıcıya $b$ yerine $\sim b$ ver ve en alttaki eldeyi 1 yap: çıkarma çıkar. İşaretli ve işaretsiz toplama aynı devre (Ders 6.18); işlemcide tek bir toplama donanımı var.

---

## 3. Multiplexer ve ALU

Bir **multiplexer** (mux), bir seçici bite bakıp iki girişten birini çıktıya veren devre: `mux(a, b, s) = s ? b : a`. Ders 5.5'teki dalsız seçimin donanım hali, ve C'de:

```c
uint32_t mux(uint32_t a, uint32_t b, int s) {
    uint32_t mask = (uint32_t)-(uint32_t)(s & 1);   // s=1 -> 0xFFFFFFFF, s=0 -> 0
    return (a & ~mask) | (b & mask);
}
```

**ALU** (Arithmetic Logic Unit, aritmetik–mantık birimi) bir avuç devreyi (toplayıcı, AND, OR, XOR, kaydırıcı) yan yana koyar, hepsini aynı anda çalıştırır, ve bir multiplexer ağıyla **hangi sonucun** çıkacağını seçer. "Komut `add` mı `sub` mı `and` mı?" sorusunun cevabı, mux'ların seçici bitleri. ALU ayrıca sonuç hakkında **bayraklar** üretir: sonuç sıfır mı, negatif mi, elde çıktı mı, taştı mı (Ders 7.8'de ayrıntılı).

ALU'nun hafızası yok: girişler değişince çıkış anında (kapı gecikmeleriyle) değişir. Böyle devrelere **birleşimsel** (combinational) denir. Hesabı saklamak için başka bir şey gerekiyor.

---

## 4. Register, saat ve bellek

Bir **flip-flop**, tek bir biti saklayan, geri besleme (bir çıkışın kendi girişine dönmesi) içeren bir devre. Ders 6.15'teki "sonlu durum sonunda tekrar eder" dediğimiz durum, fiziksel olarak flip-flop'larda duruyor. $n$ flip-flop yan yana bir **register**.

Bütün bunları bir **saat** (clock) düzenliyor: düzenli aralıklarla 0–1–0–1 giden bir sinyal. Her saat vuruşunda register'lar girişlerindeki değeri içeri alıp kilitler; vuruşlar arasında ALU ve mantık devreleri yeni değeri hesaplar. "3 GHz işlemci" demek, saat saniyede 3 milyar kez vuruyor demek. Ders 7.20'deki boru hattı, bir saat vuruşunda ne kadar iş sığdırılabileceğiyle ilgili.

**Bellek** (RAM), çok sayıda register'ın bir adresle seçilebilen hali: bir adres ver, o adresteki kelimeyi oku ya da yaz. Faz 4'teki bütün pointer'lar, bu adres–kelime mekanizmasına dönüşüyor.

---

## 5. Fetch–decode–execute

Elimizde ALU (hesap yapar), register'lar (değer tutar), bellek (program ve veri) var. Bunları bir araya getiren, işlemciyi "işlemci" yapan şey bir döngü:

1. **Fetch** (getir): program sayacının (`pc`) gösterdiği adresteki komutu bellekten oku.
2. **Decode** (çöz): komutun bitlerini parçalara ayır — hangi işlem, hangi register'lar.
3. **Execute** (yürüt): işlemi yap (ALU'yu çalıştır, belleğe eriş, ya da `pc`'yi değiştir).
4. `pc`'yi ilerlet, başa dön.

Hack makinesi (Nand2Tetris'in sonunda kurulan işlemci) bunu en sade haliyle yapıyor. Biz de kendi oyuncak makinemizi kuralım; donanımın bütün katmanlarını (kapı, ALU, register) C'nin arkasına saklayıp sadece **sözleşmeyi** (ISA'yı) yazalım.

### Oyuncak bir ISA

4 register, 256 baytlık bellek, 16 bitlik komutlar. Her komut dört 4-bitlik alan: `[ op | a | b | c ]`.

```c
// Komut bicimi:  [ op:4 | a:4 | b:4 | c:4 ]
enum { LI, ADD, ADDI, LD, ST, BEQ, JMP, HALT };
//  LI   a, imm    r[a] = imm          (imm = b*16 + c, yani 0..255)
//  ADD  a, b, c   r[a] = r[b] + r[c]
//  ADDI a, imm    r[a] = r[a] + imm   (imm = c, yani 0..15)
//  LD   a, b      r[a] = mem[r[b]]
//  ST   a, b      mem[r[b]] = r[a]
//  BEQ  a, b, c   if r[a] == r[b] then pc = c
//  JMP  c         pc = c
//  HALT           dur

static uint16_t enc(int op, int a, int b, int c) {
    return (uint16_t)((op << 12) | (a << 8) | (b << 4) | c);
}
```

`enc` bir komutu bitlere **kodluyor** (Ders 5.2'deki bayrak kümeleri gibi: her alan kendi bit konumunda). Ders 7.3'te gerçek RISC-V komutlarının kodlamasını göreceğiz; fikir aynı.

### Çekirdek döngü

```c
int pc = 0; long steps = 0;
for (;;) {
    uint16_t ins = p[pc];                                              // FETCH
    int op = ins >> 12 & 0xF, a = ins >> 8 & 0xF, b = ins >> 4 & 0xF, c = ins & 0xF;  // DECODE
    pc++; steps++;
    if (op == HALT) break;
    switch (op) {                                                      // EXECUTE
        case LI:   reg[a] = (uint8_t)(b * 16 + c); break;
        case ADD:  reg[a] = (uint8_t)(reg[b] + reg[c]); break;
        case ADDI: reg[a] = (uint8_t)(reg[a] + c); break;
        case LD:   reg[a] = mem[reg[b]]; break;
        case ST:   mem[reg[b]] = reg[a]; break;
        case BEQ:  if (reg[a] == reg[b]) pc = c; break;
        case JMP:  pc = c; break;
    }
}
```

Üç satır, bütün donanımın yaptığı iş. **Fetch**: `p[pc]`. **Decode**: bitleri kaydırıp maskeleyerek alanları çıkar (Ders 5.2). **Execute**: `switch` ile doğru işlemi seç — bu `switch`, donanımdaki ALU multiplexer'ının yazılım hali. `pc++` komutu ilerletiyor; `BEQ` ve `JMP` ise `pc`'yi değiştirerek dallanma ve döngü yapıyor (Ders 1.2'deki akış diyagramının okları).

### Bir program çalıştırmak

Bellekteki üç sayıyı toplayalım — Ders 7.1'deki `sum`'ın oyuncak makine hali:

```c
uint8_t reg[4] = {0};
uint8_t mem[256] = {0};
mem[100] = 3; mem[101] = 4; mem[102] = 5;

uint16_t p[] = {
    enc(LI,   0, 0, 0),   // 0: r0 = 0        toplam
    enc(LI,   1, 6, 4),   // 1: r1 = 100      gezen adres (6*16+4)
    enc(LI,   2, 6, 7),   // 2: r2 = 103      bitis adresi
    enc(BEQ,  1, 2, 8),   // 3: dongu: if r1 == r2 goto 8 (END)
    enc(LD,   3, 1, 0),   // 4:   r3 = mem[r1]
    enc(ADD,  0, 0, 3),   // 5:   r0 += r3
    enc(ADDI, 1, 0, 1),   // 6:   r1 += 1
    enc(JMP,  0, 0, 3),   // 7:   goto 3
    enc(HALT, 0, 0, 0),   // 8: END
};
```

```
r0 = 12  (20 komut calisti)
```

Doğru toplam. 20 komut: 3 kurulum, döngünün 3 turu (her tur `BEQ`+`LD`+`ADD`+`ADDI`+`JMP` = 5 komut), bir de çıkıştaki `BEQ` ve `HALT`. Bu döngünün Ders 7.1'deki gerçek RISC-V `sum` fonksiyonuyla aynı iskelete sahip olduğuna dikkat et: sıfırla, gez, topla, karşılaştır, dallan.

Bir ince nokta: bu makineyi tasarlarken **register sıkışması** yaşadık. r0 toplam, r1 adres, r2 bitiş, r3 yüklenen değer — dört register tam doldu, "adım 1" için ayrı register kalmadı. Çözüm, `ADDI` komutunu eklemek oldu (sabiti komutun içine gömmek). Bu, Faz 6'daki (Ders 6.30) register tahsisi probleminin donanım tarafı: az register, çok değer. Gerçek ISA'lar bu yüzden sabitleri komuta gömen "immediate" komutlara (RISC-V'de `addi`, Ders 7.4) sahip.

Bu oyuncak makine gerçek bir işlemcinin soyut bir resmi. Eksikleri çok: gerçek fetch–decode–execute donanımda paralel ve boru hatlı (7.20), bellek cache'li (7.24), ve komutlar sırasız yürütülebiliyor (7.23). Ama sözleşme — getir, çöz, yürüt — hepsinde aynı.

---

## Alıştırmalar

**1** – `mux(a, b, s)`'in `s = 0` ve `s = 1` için doğru çalıştığını Ders 5.5'teki maske mantığıyla açıkla. Bir ALU'da neden multiplexer'a ihtiyaç var?

**2** – Oyuncak makinede `SUB a, b, c` (`r[a] = r[b] - r[c]`) komutunu ekle. Sonra Ders 6.18'deki gibi, `SUB` yerine `r[c]`'nin ikiye tümleyenini alıp `ADD` kullanan bir yol düşün. Hangisi donanımda daha az devre ister?

**3** – Bölüm 5'teki program 3 eleman için 20 komut çalıştırdı. $n$ eleman için kaç komut çalışır? Formülü yaz. "Kurulum" ile "döngü başına" maliyeti ayır (Ders 6.12'deki gibi).

**4** – Oyuncak makineye bir çarpma komutu **eklemeden**, `mem[100]`'ü `mem[101]` ile çarpıp sonucu `r0`'a koyan bir program yaz. (İpucu: tekrarlı toplama; Ders 5.13'teki kaydır-topla çarpmayı da deneyebilirsin ama kaydırma komutu yok, sadece toplama var.)

**5** – `BEQ` ve `JMP` olmasa, yani `pc` hep `pc++` ile ilerlese, bu makinede hangi programlar yazılamazdı? Döngü ve karar olmadan bir makine ne kadar güçlü olur? (Faz 14'teki hesaplama kuramının habercisi.)

<details>
<summary>Cevaplar</summary>

**1** – `s = 0`: `mask = 0`, sonuç `(a & ~0) | (b & 0) = a`. `s = 1`: `mask = 0xFFFFFFFF`, sonuç `(a & 0) | (b & mask) = b`. Ders 5.5'teki "maskeyle seç" deseni. ALU birçok işlemi (toplama, AND, OR, ...) **aynı anda** hesaplıyor; multiplexer, komutun istediği sonucu seçip gerisini atıyor. Donanımda "sadece gerekeni hesapla" diye bir şey yok; her şey hesaplanır, mux seçer.

**2** – `case SUB: reg[a] = (uint8_t)(reg[b] - reg[c]); break;`. İkiye tümleyen yolu: `reg[b] + (~reg[c] + 1)`. Donanımda **tek bir toplayıcı** yetiyor: çıkarma için girişi tersle (bir XOR katmanı) ve en alttaki eldeyi 1 yap. Ayrı bir çıkarıcı devre kurmaktan ucuz; gerçek ALU'lar hep böyle yapar (Ders 6.18, 6.23).

**3** – Kurulum 3 komut (`LI` × 3). Döngü her tur 5 komut ($n$ tur), artı çıkıştaki `BEQ` (1) ve `HALT` (1). Toplam $3 + 5n + 2 = 5n + 5$. $n = 3$: 20. ✓ $\Theta(n)$ (Ders 6.12); sabit terim kurulum ve bitiş, $n$'li terim döngü.

**4** – Çarpmayı tekrarlı toplamaya çevir: `mem[100]` kere `mem[101]`'i topla.

```c
uint16_t p[] = {
    enc(LI,  0, 0, 0),    // r0 = 0           sonuc
    enc(LI,  1, 6, 4),    // r1 = &mem[100]
    enc(LD,  1, 1, 0),    // r1 = mem[100]    sayac (kac kez toplanacak)
    enc(LI,  2, 6, 5),    // r2 = &mem[101]
    enc(LD,  2, 2, 0),    // r2 = mem[101]    eklenecek deger
    enc(LI,  3, 0, 0),    // r3 = 0           sabit sifir (karsilastirma icin)
    enc(BEQ, 1, 3, 10),   // dongu: if r1 == 0 goto END
    enc(ADD, 0, 0, 2),    //   r0 += r2
    enc(ADDI,1, 0, 15),   //   r1 += 15  -> r1 -= 1 YAPAMAYIZ (ADDI sadece ekler)
    enc(JMP, 0, 0, 6),    //   goto dongu
    enc(HALT,0, 0, 0),    // END
};
```

Burada bir sorun çıkıyor: `ADDI` sadece ekliyor, çıkarma yok; sayacı azaltamıyoruz. Bu yüzden ya `SUB` komutu (Alıştırma 2) ekleyip `r1`'i 1'er azaltmalı, ya da sayaç yerine `mem[101]`'in adresini her tur ilerletip `mem[100]` kez tekrar etmeli. En temizi `SUB` eklemek: `enc(LI, 3, 0, 1)` ile r3=1, sonra `SUB r1, r1, r3`. Bu alıştırma, bir ISA'nın eksik bir komutunun programı nasıl zorlaştırdığını gösteriyor — tam da gerçek ISA tasarımcılarının düşündüğü şey.

**5** – `BEQ`/`JMP` olmadan `pc` hep bir artar: program düz bir çizgi, hiç geri dönemez, hiç karar veremez. Yazılabilen her program, komut sayısı kadar adımda biter; döngü, değişken uzunlukta girdiyi işleme (örneğin "$n$ elemanı topla", $n$ değişkense) yazılamaz. Böyle bir makine, sabit boyutlu hesaplar dışında neredeyse işe yaramaz. Dallanma, bir makineyi "hesaplayabilen" bir makine yapan şey; Faz 14'te bunun kesin sınırını (Turing makineleri, durma problemi) göreceğiz. Döngüsüz diller gerçekten var ve kasten sınırlı tutuluyor (her zaman biten programlar).

</details>

---

## Kaynaklar

- Noam Nisan & Shimon Schocken, *The Elements of Computing Systems* (Nand2Tetris, 2. baskı), Bölüm 1–5: NAND'dan Hack CPU'suna adım adım. Bu dersin ana kaynağı; projeleri ücretsiz (nand2tetris.org).
- David Patterson & John Hennessy, *Computer Organization and Design, RISC-V Edition* (2. baskı), Ek A (mantık tasarımı) ve Bölüm 4: veri yolu ve denetim.
- Charles Petzold, *Code: The Hidden Language of Computer Hardware and Software* (2. baskı): röleden işlemciye, matematiksiz ve sezgisel.

**Sıradaki ders:** Makine kodu ve kodlama. RISC-V komut biçimleri (R, I, S, B, U, J) ve bir komutu elle bitlere kodlamak.
