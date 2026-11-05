---
title: "7.19 Tek döngülü veri yolu (datapath)"
description: "RISC-V RV32I için tek döngülü bir işlemci: PC, komut belleği, register dosyası, immediate üretici, ALU, veri belleği ve onları bağlayan çoklayıcılar (mux). Kontrol biriminin opcode'dan ürettiği sinyaller (RegWrite, ALUSrc, MemRead, MemWrite, MemToReg, Branch), her komut türünün veri yolunda izlediği yol, ve bunları adım adım gösteren bir C simülasyonu. Saat periyodunu en yavaş komutun (lw) belirlemesi."
---

Ders 7.2'de basit bir CPU'yu C'de bir `switch` olarak yazdık: getir, çöz, yürüt. Ders 7.3'te RISC-V komutlarının bitlerini çözdük. Bu ders ikisini donanıma yaklaştırıyor: bir RISC-V işlemcisinin **veri yolunu** (datapath) — verinin aktığı kutuları ve telleri — ve o tellerin hangisinin açık olacağına karar veren **kontrol birimini** kuruyoruz. "Tek döngülü" (single-cycle) demek: her komut tam **bir saat döngüsünde** baştan sona biter. Bu en basit tasarım; sonraki iki ders (boru hattı) onu hızlandırmanın yolu.

Bu ders Patterson & Hennessy'nin *Computer Organization and Design RISC-V Edition* kitabının 4. bölümündeki tasarımı izliyor: `add`, `sub`, `addi`, `lw`, `sw`, `beq` destekleyen bir alt küme. Diğer komutlar aynı fikrin uzantısı.

---

## 1. Yapı taşları

Ders 7.2'deki gibi mantık kapılarından kurulan altı kutu:

| Birim | Ne yapar | Ders |
| --- | --- | --- |
| **PC** | Sıradaki komutun adresini tutan 32 bitlik register | 7.2 |
| **Komut belleği** | Adres girer, 32 bitlik komut çıkar | 7.3 |
| **Register dosyası** | 32 register; iki okuma portu (`rs1`, `rs2`), bir yazma portu (`rd`) | 7.4 |
| **Immediate üretici** | Komutun formatına göre (I/S/B) dağınık immediate bitlerini toplayıp 32 bite işaret genişletir | 7.3 |
| **ALU** | İki 32 bitlik girişte toplama/çıkarma/mantık; sonuç ve "sıfır mı?" çıkışı | 7.2 |
| **Veri belleği** | Adres + yazılacak veri girer; okunan veri çıkar | 7.4 |

Bir de **çoklayıcı** (multiplexer, mux): iki girişten birini bir seçme sinyaline göre çıkışa veren devre. C'deki `secim ? a : b` ifadesinin donanımı. Veri yolundaki bütün "karar"lar mux'larla verilir.

---

## 2. Veri yolunu birleştirmek

Her komutun yaptığına bakıp gereken bağlantıları ekleyelim:

```
 [PC] --> [Komut bellegi] --komut--+--> rs1, rs2 --> [Register dosyasi] --a--------------> [ALU] --sonuc--+
   ^                               |                                   --b--> (mux) -->   |            |
   |                               +--> [Imm uretici] --imm-----------------> ALUSrc      |sifir       |
   |                               |                                                      v            v
   |                               +--> opcode --> [Kontrol] --> sinyaller          [Branch AND]  [Veri bellegi]
   |                                                                                      |            |
   +-------- (mux PC) <---- PC+4 / PC+imm <-----------------------------------------------+            |
                                                                                                       |
            [Register dosyasi] <-- rd <-- (mux MemToReg) <-- ALU sonucu / bellekten okunan <-----------+
```

Akış her komut için aynı beş aşama (Ders 7.2'deki döngünün donanım hali):

1. **Getir** (IF): `PC` → komut belleği → 32 bitlik komut.
2. **Çöz** (ID): komut bitleri tellere ayrılır. `rs1`, `rs2` register dosyasından iki değer okutur; immediate üretici immediate'ı hazırlar; opcode kontrol birimine gider.
3. **Yürüt** (EX): ALU, `rs1` değeri ile **ya** `rs2` değerini **ya** immediate'ı (ALUSrc mux'ı) toplar ya da çıkarır.
4. **Bellek** (MEM): `lw` ise ALU sonucu adres olur ve bellekten okunur; `sw` ise o adrese `rs2` değeri yazılır.
5. **Geri yaz** (WB): register dosyasına **ya** ALU sonucu **ya** bellekten okunan değer (MemToReg mux'ı) yazılır.

Ve paralelde **sonraki PC**: normalde `PC + 4`; `beq` ise ve ALU sonucu sıfırsa (iki register eşit) `PC + imm`.

Tek döngülü tasarımda bu beş aşama ayrı zamanlar değil, **aynı saat döngüsü içinde** sinyalin devreden akması. Döngünün sonunda (saat kenarında) PC ve register dosyası/bellek güncellenir.

---

## 3. Kontrol birimi

Aynı veri yolu altı farklı komutu çalıştırıyor; fark sadece mux'ların ve yazma izinlerinin ayarı. Bu ayarları **sadece opcode'a** bakan bir devre üretir:

| Komut | opcode | RegWrite | ALUSrc | MemRead | MemWrite | MemToReg | Branch | ALU |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `add`/`sub` (R) | `0110011` | 1 | 0 (rs2) | 0 | 0 | 0 (ALU) | 0 | funct3/funct7'ye bak |
| `addi` (I) | `0010011` | 1 | 1 (imm) | 0 | 0 | 0 (ALU) | 0 | topla |
| `lw` (I) | `0000011` | 1 | 1 (imm) | 1 | 0 | 1 (bellek) | 0 | topla (adres) |
| `sw` (S) | `0100011` | 0 | 1 (imm) | 0 | 1 | x | 0 | topla (adres) |
| `beq` (B) | `1100011` | 0 | 0 (rs2) | 0 | 0 | x | 1 | çıkar (eşit mi?) |

`x` "önemsiz": `sw` ve `beq` register'a yazmadığı için MemToReg ne olursa olsun fark etmez. Bu, gerçek donanımda kapı tasarrufu demek: tasarımcı "x" olan yerlere devreyi en basit yapan değeri koyabilir (mantık tasarımında "don't care").

Tabloyu satır satır okumak her komutun **veri yolundaki yolunu** verir:

- `lw`: register → ALU (+imm) → bellek → register. **Beş birimin hepsinden** geçiyor; en uzun yol.
- `sw`: register → ALU (+imm) → bellek. Register'a yazmıyor.
- `add`: register → ALU → register. Belleğe uğramıyor.
- `beq`: register → ALU (çıkar) → "sıfır" sinyali → PC mux'ı.

`add` ve `sub` aynı opcode'u paylaşıyor; ALU'ya toplama mı çıkarma mı yapacağını `funct7`'nin 5. biti (`0x20`) söylüyor (Ders 7.3'teki `add` = `0x007302B3`, `sub` = `0x407302B3`; fark tam o bit). Gerçek tasarımlarda bu iki seviyeli yapılır: ana kontrol `ALUOp` üretir, küçük bir "ALU kontrol" devresi `ALUOp` + funct alanlarından son işlemi seçer.

---

## 4. Simülasyon

Veri yolunu C'de, her mux ve sinyal ayrı bir satır olacak şekilde yazalım. Ders 7.2'deki `switch`'ten farkı: burada komut türüne göre farklı kod **yok**; her komut aynı satırlardan geçiyor, sadece kontrol sinyalleri farklı.

```c
/* Tek dongulu RV32I veri yolu: her komut bir dongude, kontrol sinyalleriyle */
#include <stdio.h>
#include <stdint.h>

typedef struct {
    int RegWrite, ALUSrc, MemRead, MemWrite, MemToReg, Branch;
    const char *ALUOp;              /* "ADD", "SUB", "F3F7" (funct alanina bak) */
} Kontrol;

/* Kontrol birimi: SADECE opcode'a bakar */
static Kontrol kontrol(uint32_t opcode) {
    switch (opcode) {
    case 0x33: return (Kontrol){1,0,0,0,0,0,"F3F7"};  /* R: add/sub   */
    case 0x13: return (Kontrol){1,1,0,0,0,0,"ADD"};   /* I: addi      */
    case 0x03: return (Kontrol){1,1,1,0,1,0,"ADD"};   /* I: lw        */
    case 0x23: return (Kontrol){0,1,0,1,0,0,"ADD"};   /* S: sw        */
    case 0x63: return (Kontrol){0,0,0,0,0,1,"SUB"};   /* B: beq       */
    }
    return (Kontrol){0,0,0,0,0,0,"?"};
}

static int32_t imm_uret(uint32_t k) {          /* immediate uretici */
    uint32_t op = k & 0x7f;
    if (op == 0x13 || op == 0x03) return (int32_t)k >> 20;
    if (op == 0x23) return ((int32_t)(k & 0xfe000000) >> 20) | ((k >> 7) & 0x1f);
    if (op == 0x63) return ((int32_t)(k & 0x80000000) >> 19) | ((k & 0x80) << 4)
                         | ((k >> 20) & 0x7e0) | ((k >> 7) & 0x1e);
    return 0;
}

int main(void) {
    uint32_t imem[] = { 0x00800093, 0x00500113, 0x002081b3, 0x00302023,
                        0x00002203, 0x00418463, 0x06300293, 0x40220333 };
    const char *ad[] = { "addi x1,x0,8", "addi x2,x0,5", "add x3,x1,x2", "sw x3,0(x0)",
                         "lw x4,0(x0)",  "beq x3,x4,+8", "addi x5,x0,99", "sub x6,x4,x2" };
    int32_t x[32] = {0}, dmem[16] = {0};
    uint32_t pc = 0;
    int dongu = 0;

    printf("dongu  pc  komut           RW AS MR MW M2R Br ALU   sonuc\n");
    while (pc / 4 < 8) {
        uint32_t k = imem[pc / 4];                                /* 1. getir (fetch) */
        uint32_t op = k & 0x7f, rd = (k >> 7) & 31, f3 = (k >> 12) & 7,
                 rs1 = (k >> 15) & 31, rs2 = (k >> 20) & 31, f7 = k >> 25;
        Kontrol c = kontrol(op);                                  /* 2. coz (decode)  */
        int32_t a = x[rs1], b = x[rs2], imm = imm_uret(k);
        int32_t alu_b = c.ALUSrc ? imm : b;                        /* ALUSrc mux       */
        int sub = (c.ALUOp[0] == 'S') || (c.ALUOp[0] == 'F' && f3 == 0 && f7 == 0x20);
        int32_t alu = sub ? a - alu_b : a + alu_b;                 /* 3. yurut (ALU)   */
        int sifir = (alu == 0);
        int32_t okunan = c.MemRead ? dmem[alu / 4] : 0;            /* 4. bellek        */
        if (c.MemWrite) dmem[alu / 4] = b;
        int32_t yaz = c.MemToReg ? okunan : alu;                   /* MemToReg mux     */
        if (c.RegWrite && rd != 0) x[rd] = yaz;                    /* 5. geri yaz      */
        uint32_t sonraki = (c.Branch && sifir) ? pc + imm : pc + 4; /* PC mux          */

        printf("%4d  %3u  %-15s  %d  %d  %d  %d  %d   %d  %-5s ",
               ++dongu, pc, ad[pc/4], c.RegWrite, c.ALUSrc, c.MemRead, c.MemWrite,
               c.MemToReg, c.Branch, sub ? "SUB" : "ADD");
        if (c.RegWrite) printf("x%u=%d\n", rd, yaz);
        else if (c.MemWrite) printf("mem[%d]=%d\n", alu, b);
        else printf("sifir=%d -> pc=%u\n", sifir, sonraki);
        pc = sonraki;
    }
    printf("x5=%d (beq atladi mi? %s), x6=%d\n", x[5], x[5] ? "hayir" : "evet", x[6]);
    return 0;
}
```

Komut sözcükleri RISC-V assembler'ından (`riscv64-linux-gnu-as -march=rv32i`) alındı; `beq x3,x4,atla` 8 bayt ileriye atlıyor ve `0x00418463` olarak kodlanıyor.

```
$ cc -O1 -Wall datapath.c -o datapath && ./datapath
dongu  pc  komut           RW AS MR MW M2R Br ALU   sonuc
   1    0  addi x1,x0,8     1  1  0  0  0   0  ADD   x1=8
   2    4  addi x2,x0,5     1  1  0  0  0   0  ADD   x2=5
   3    8  add x3,x1,x2     1  0  0  0  0   0  ADD   x3=13
   4   12  sw x3,0(x0)      0  1  0  1  0   0  ADD   mem[0]=13
   5   16  lw x4,0(x0)      1  1  1  0  1   0  ADD   x4=13
   6   20  beq x3,x4,+8     0  0  0  0  0   1  SUB   sifir=1 -> pc=28
   7   28  sub x6,x4,x2     1  0  0  0  0   0  SUB   x6=8
x5=0 (beq atladi mi? evet), x6=8
```

Sinyal sütunları Bölüm 3'teki tablonun aynısı. `beq`'te ALU `13 − 13 = 0` hesapladı, "sıfır" sinyali 1 oldu, `Branch AND sifir` PC mux'ını `pc + imm = 20 + 8 = 28`'e çevirdi ve `addi x5,x0,99` hiç çalışmadı. 8 komutluk programda 7 döngü: tek döngülü işlemcide **CPI** (komut başına döngü) her zaman tam 1.

---

## 5. Saat periyodu: en yavaş komutun cezası

CPI = 1 kulağa ideal geliyor, ama saat periyodu ne olacak? Döngü, sinyalin **en uzun yoldan** geçmesine yetecek kadar uzun olmalı. Örnek gecikmeler (P&H'nin örnek değerleri):

| Birim | Gecikme |
| --- | --- |
| Komut belleği | 200 ps |
| Register okuma | 100 ps |
| ALU | 200 ps |
| Veri belleği | 200 ps |
| Register yazma | 100 ps |

| Komut | Kullandığı birimler | Toplam |
| --- | --- | --- |
| `lw` | IM + Reg + ALU + DM + Reg | 800 ps |
| `sw` | IM + Reg + ALU + DM | 700 ps |
| `add` | IM + Reg + ALU + Reg | 600 ps |
| `beq` | IM + Reg + ALU | 500 ps |

Saat herkes için aynı olmak zorunda, yani periyot **800 ps** (1.25 GHz). `beq` 500 ps'de bitiyor ama 300 ps boşta bekliyor. Programdaki komutların çoğu `lw` olmasa bile herkes `lw`'nun hızında çalışıyor. Bu, tek döngülü tasarımın temel zayıflığı; Ders 7.20'deki boru hattı tam bunu çözüyor: döngüyü aşama başına 200 ps'ye indirip beş komutu aynı anda farklı aşamalarda tutarak.

---

## Alıştırmalar

**1** – `lw x4,0(x0)` için veri yolunda hangi mux hangi girişi seçiyor? ALUSrc, MemToReg ve PC mux'ının değerlerini ve nedenlerini yaz.

**2** – Simülasyona `or` komutunu (R tipi, funct3 = 6) eklemek için kontrol tablosunda bir şey değişir mi? Neyi değiştirmen gerekir?

**3** – `jal rd, imm` komutunu desteklemek için veri yoluna ne eklenmeli? (İpucu: `rd`'ye ne yazılıyor, PC'ye ne yazılıyor? Mevcut mux'lar yeterli mi?)

**4** – Kontrol tablosunda `sw` için MemToReg "x". Yanlışlıkla `sw` için RegWrite = 1 yapılsaydı ne olurdu? Simülasyonda dene: hangi register bozulur?

**5** – Bölüm 5'teki gecikmelerle 1 milyon komutluk bir programın %25'i `lw`, %10'u `sw`, %45'i R tipi, %20'si `beq` olsun. Tek döngülü işlemcide süre ne olur? Her komut kendi süresi kadar sürebilseydi (değişken uzunluklu saat) ne olurdu?

<details>
<summary>Cevaplar</summary>

**1** – ALUSrc = 1: ALU'nun ikinci girişi immediate (0), çünkü adres = `rs1 + imm`. MemToReg = 1: register'a ALU sonucu (adres) değil, bellekten okunan değer yazılır. PC mux'ı `PC + 4`: Branch = 0, sıfır sinyali ne olursa olsun dallanma yok. Bu yüzden `lw` beş birimin hepsini kullanıyor.

**2** – Ana kontrol tablosu değişmez: `or` de opcode `0110011`, aynı R satırı (RegWrite = 1, ALUSrc = 0, ...). Değişmesi gereken ALU kontrolü: funct3 = 6 olunca ALU'nun `a | b` yapması. Simülasyonda `sub` değişkeni yerine funct3'e bakan küçük bir `switch` (Ders 7.30'daki emülatörde olduğu gibi). İki seviyeli kontrolün faydası bu: yeni bir R komutu ana kontrolü değiştirmiyor.

**3** – `jal` iki şey yapar: `rd = PC + 4` ve `PC = PC + imm` (J formatı immediate'ı). Gerekenler: immediate üreticiye J formatı; register'a yazılacak değer için MemToReg mux'ına üçüncü giriş (`PC + 4`); PC mux'ında koşulsuz atlama (Branch'e ek bir Jump sinyali: `PC_sec = Jump OR (Branch AND sifir)`). Kontrol tablosuna `jal` satırı: RegWrite = 1, Jump = 1, MemWrite = 0. Mevcut iki girişli mux'lar yetmiyor, birinin üç girişli olması gerekiyor.

**4** – `sw x3,0(x0)` komutunun `rd` alanındaki bitler aslında immediate'ın alt 5 biti (S formatında `imm[4:0]` tam `rd`'nin yerinde, Ders 7.3). Burada imm = 0, yani `rd` = 0 ve x0'a yazma görmezden gelinir; şans eseri zarar yok. `sw x3,4(x0)` olsaydı `rd` = 4 olurdu ve x4'e ALU sonucu (adres, 4) yazılırdı: alakasız bir register sessizce bozulur. "x" yalnızca **okunmayan** sinyaller için serbest; yazma izinleri (RegWrite, MemWrite) her zaman doğru olmalı.

**5** – Tek döngülü: her komut 800 ps, 10⁶ × 800 ps = **800 µs**. Değişken saatle: ortalama = 0.25·800 + 0.10·700 + 0.45·600 + 0.20·500 = 200 + 70 + 270 + 100 = 640 ps, toplam **640 µs**, %20 daha hızlı. Ama değişken uzunluklu saat pratikte yapılamıyor (her komutun süresini önceden bilip saati ona göre ayarlamak); çözüm boru hattı.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design: RISC-V Edition* (2. baskı), Bölüm 4.1–4.4: veri yolu, kontrol birimi, tek döngülü uygulama (bu dersteki gecikme değerleri oradan).
- Sarah Harris & David Harris, *Digital Design and Computer Architecture: RISC-V Edition*, Bölüm 7.3: tek döngülü işlemci, SystemVerilog ile.
- RISC-V Unprivileged ISA Specification, Bölüm 2: RV32I komut formatları.

**Sıradaki ders:** Boru hattı (pipelining). 5 aşamalı boru hattı, verim (throughput) ve gecikme (latency).
