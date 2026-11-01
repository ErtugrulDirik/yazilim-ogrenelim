---
title: "7.3 Makine kodu ve kodlama"
description: "Assembly ile makine kodu arasındaki fark; RISC-V'nin 32 register'ı ve x0 kuralı; komutların 32 bite kodlanması; R, I, S, B, U, J biçimleri ve neden immediate alanların parçalı olduğu; bir komutu elle bit bit kodlamak ve assembler çıktısıyla karşılaştırmak; little-endian bellek yerleşimi; sıkıştırılmış (16-bit) komutlara kısa bakış."
gereksinimler: [rars]
gereksinimNotu: "RISC-V komutlarını yazıp çalıştırmak için; bir sonraki derste kuruyoruz. Bu derste assembler çıktısını okumak yeterli."
---

Ders 7.2'de oyuncak makinemizin komutlarını `enc(op, a, b, c)` ile 16 bite kodladık: her alan kendi bit konumunda. Gerçek işlemciler de tam olarak bunu yapıyor, sadece daha fazla alan ve daha fazla kuralla. Bu ders RISC-V'nin komut kodlamasını açıyor: `add x5, x6, x7` yazdığında bellekte duran 32 bit nereden geliyor?

Kodlamayı anlamak iki sebeple önemli. Birincisi, Faz 7'nin sonundaki öykünücü (Ders 7.30) ve her disassembler (`objdump`), bu bitleri çözmek zorunda. İkincisi, kodlamanın **biçimi** ISA tasarımının neden öyle olduğunu anlatıyor: RISC-V'nin register alanları neden hep aynı yerde, immediate'ler neden parçalanmış.

---

## 1. Assembly ile makine kodu

İki ayrı şey:

- **Makine kodu**: işlemcinin çalıştırdığı ham bitler. `add x5, x6, x7` için 32 bit: `0x007302B3`.
- **Assembly**: o bitlerin insan okuyabilir hali. `add x5, x6, x7` bir metin.

İkisi arasındaki çeviriyi **assembler** yapar (makine koduna), **disassembler** tersine (`objdump -d`). Çeviri neredeyse birebir: her assembly satırı genellikle bir makine komutu. (Neredeyse: **sözde komutlar** (pseudo-instructions) bir istisna, Ders 7.4.) Faz 2'den beri kullandığımız derleyici, C'yi önce assembly'ye, sonra assembler onu makine koduna çeviriyor; `clang -S` ilk adımda durur, `clang -c` ikincisine kadar gider.

Bu dersin örneklerini bir assembler'dan (RISC-V'ye çapraz derlenmiş clang) geçirip ham bitleri `objdump` ile okuyacağız, sonra aynı bitleri elle üreteceğiz.

---

## 2. RISC-V register'ları

RISC-V'nin (RV32I/RV64I temel kümesi) **32 tamsayı register'ı** var: `x0`–`x31`, her biri 32 bit (RV32) ya da 64 bit (RV64). Bir özellik: **`x0` her zaman sıfırdır.** Ona yazmak hiçbir şey yapmaz, okumak hep 0 verir.

Bu küçük hile çok işe yarıyor. Ayrı bir "sıfırla" komutu gerekmez (`add x5, x0, x0` → `x5 = 0`); ayrı bir "kopyala" komutu gerekmez (`add x5, x6, x0` → `x5 = x6`); ayrı bir "atla, sonucu atma" komutu gerekmez. Ders 7.2'deki oyuncak makinede yaşadığımız register sıkışmasının bir ucu burada çözülüyor: sabit 0'ı tutmak için register harcamıyoruz.

Register'ların ABI'de (Ders 7.6, 7.10) rol adları da var: `zero` (= x0), `ra` (dönüş adresi, x1), `sp` (yığın, x2), `a0`–`a7` (argümanlar, x10–x17), `t0`–`t6` (geçici), `s0`–`s11` (korunan). `objdump` çıktısında bu adları görürsün (`t0` = `x5`). Şimdilik sayıları kullanacağız; adları Ders 7.6'da ABI ile öğreneceğiz.

---

## 3. Altı komut biçimi

Her RV32 komutu **tam 32 bit** (Ders 7.1'deki sabit uzunluk). İçindeki alanların yerleşimi komut türüne göre değişir ama altı sabit **biçim** var. Her biçimin ortak derdi: `opcode`, `rd`, `rs1`, `rs2` ve `funct3`/`funct7` (işlemi daha ince belirleyen alanlar) ile **immediate** (komuta gömülü sabit) alanlarını 32 bite sığdırmak.

| Biçim | Ne için | Örnek |
| --- | --- | --- |
| **R** | register–register | `add`, `sub`, `and`, `sll` |
| **I** | register + sabit; load; `jalr` | `addi`, `lw`, `jalr` |
| **S** | store | `sw`, `sb` |
| **B** | koşullu dal | `beq`, `bne`, `blt` |
| **U** | üst 20 bit sabit | `lui`, `auipc` |
| **J** | atlama | `jal` |

**R biçimi** (register–register–register), bit konumları:

```
 31      25 24   20 19   15 14 12 11    7 6         0
[ funct7  ][ rs2  ][ rs1 ][f3 ][  rd   ][  opcode   ]
   7 bit     5       5     3     5          7
```

**I biçimi** (register + 12-bitlik işaretli sabit): `rs2` ve `funct7`'nin yeri 12 bitlik bir immediate'e dönüşüyor.

```
 31              20 19   15 14 12 11    7 6         0
[   imm[11:0]      ][ rs1 ][f3 ][  rd   ][  opcode   ]
     12 bit           5     3     5          7
```

Dikkat çeken şey: `opcode` (7 bit) hep en sağda, `rd` hep 7.–11. bitte, `rs1` hep 15.–19. bitte, `funct3` hep 12.–14. bitte. Bütün biçimlerde **aynı alan aynı yerde**. Bu, donanımın işini kolaylaştıran kasıtlı bir tasarım: decode aşaması (Ders 7.2), komutun türünü bilmeden bile register numaralarını doğru yerden çekebiliyor, çünkü yerleri hep aynı. CISC'te (x86-64, Ders 7.7) register alanları her komutta başka yerde; decode çok daha zor.

---

## 4. Immediate'ler neden parçalı

S, B, J biçimlerinde immediate alanı, komutun içinde **dağınık** parçalara bölünmüş. `beq`'nin (B biçimi) 13 bitlik dal mesafesi beş ayrı parçaya ayrılmış; mantıksız görünüyor ama bir sebebi var.

RISC-V'nin tasarım ilkesi: bir immediate'in **her biti**, hangi biçimde olursa olsun, **mümkün olduğunca aynı bit konumunda** dursun. Örneğin immediate'in en yüksek biti (işaret biti) her biçimde komutun 31. bitinde. Neden? Donanımda işaret genişletme (12 ya da 13 bitlik sayıyı 32/64 bite yaymak) ve immediate'i birleştirme devresi, bit konumları sabit olunca çok daha küçük oluyor. İnsan için okunması zor, donanım için ucuz; RISC-V insanların elle kodlamasına değil, makinenin hızlı çözmesine göre tasarlandı.

B ve J biçimlerinde ayrıca bir incelik: dal/atlama hedefleri hep **çift** adreste (komutlar 2 ya da 4 byte, Bölüm 7), dolayısıyla mesafenin en düşük biti her zaman 0; onu saklamaya gerek yok. Immediate'ler bu yüzden 2'nin katı olarak kodlanıyor (`beq` 13 bit ama alt bit hep 0, yani 12 bit yer tutuyor).

Bu derste en basit iki biçimi (R ve I) elle kodlayacağız; parçalı biçimleri (S, B, J) okumayı Ders 7.5'te dallanma ile birlikte göreceğiz.

---

## 5. Elle kodlama

`add x5, x6, x7`'yi bitlerine ayıralım. R biçimi, ve `add` için standart değerler: `opcode = 0x33` (0110011), `funct3 = 0x0`, `funct7 = 0x00`.

```
funct7 = 0000000   (7 bit)
rs2    = 00111     (x7 = 7)
rs1    = 00110     (x6 = 6)
funct3 = 000
rd     = 00101     (x5 = 5)
opcode = 0110011
```

Yan yana (31. bitten 0'a): `0000000 00111 00110 000 00101 0110011`. Dört bitlik gruplara böl: `0000 0000 0111 0011 0000 0010 1011 0011` = `0x007302B3`.

`sub` aynı biçim, sadece `funct7 = 0x20` (0100000): en yüksek bit farkı, çıkarmayı toplamadan ayırıyor. Sonuç `0x407302B3`.

`addi x5, x6, -20` (I biçimi): `opcode = 0x13`, `funct3 = 0x0`. Sabit $-20$, 12 bitlik ikiye tümleyen (Ders 3.3): $4096 - 20 = 4076 = \text{0xFEC}$. Yerine koy: `111111101100 00110 000 00101 0010011` = `0xFEC30293`.

Bunları C'de bir fonksiyonla üretelim — Ders 7.2'deki `enc`'in gerçek hali:

```c
// R tipi: funct7[31:25] rs2[24:20] rs1[19:15] funct3[14:12] rd[11:7] opcode[6:0]
static uint32_t r_type(int funct7, int rs2, int rs1, int funct3, int rd, int opcode) {
    return (uint32_t)funct7 << 25 | (uint32_t)rs2 << 20 | (uint32_t)rs1 << 15
         | (uint32_t)funct3 << 12 | (uint32_t)rd << 7 | (uint32_t)opcode;
}

// I tipi: imm[31:20] rs1[19:15] funct3[14:12] rd[11:7] opcode[6:0]
static uint32_t i_type(int imm12, int rs1, int funct3, int rd, int opcode) {
    uint32_t imm = (uint32_t)imm12 & 0xFFF;           // 12 bit, isaretli
    return imm << 20 | (uint32_t)rs1 << 15 | (uint32_t)funct3 << 12
         | (uint32_t)rd << 7 | (uint32_t)opcode;
}
```

Her alanı kendi konumuna kaydırıp (Ders 5.1) birleştiriyoruz (Ders 5.2'deki `|` ile bit paketleme). `imm12 & 0xFFF`, 12 bitten taşan işaret bitlerini kesiyor (negatif sayının üst bitleri 1'di). Deneyelim:

```c
uint32_t add  = r_type(0x00, 7, 6, 0x0, 5, 0x33);   // add  t0, t1, t2
uint32_t sub  = r_type(0x20, 7, 6, 0x0, 5, 0x33);   // sub  t0, t1, t2
uint32_t addi = i_type(-20,  6, 0x0, 5, 0x13);      // addi t0, t1, -20
uint32_t ori  = i_type(255,  6, 0x6, 5, 0x13);      // ori  t0, t1, 255
```

```
add  t0,t1,t2   = 0x007302B3   (assembler: 0x007302B3)
sub  t0,t1,t2   = 0x407302B3   (assembler: 0x407302B3)
addi t0,t1,-20  = 0xFEC30293   (assembler: 0xFEC30293)
ori  t0,t1,255  = 0x0FF36293   (assembler: 0x0FF36293)
```

Dört komut da, assembler'ın (çapraz derlenmiş clang + `objdump`) ürettiğiyle bit bit aynı. Elle kodlama ile makinenin kodlaması aynı şey; "makine kodu" dediğimiz bu bitler, hiçbir sihir içermiyor, sadece dikkatli yerleştirilmiş alanlar. (`t0` = `x5`, `t1` = `x6`, `t2` = `x7`; objdump register'ların ABI adlarını gösteriyor, Bölüm 2.)

---

## 6. Bellekte: little-endian

`0x007302B3` bellekte dört byte olarak durur. Hangi sırayla? Ders 3.9'daki endianness: RISC-V ve x86-64 **little-endian**, yani en düşük anlamlı byte önce. `0x007302B3` bellekte `B3 02 73 00` sırasıyla yatar.

Bu yüzden ham ikili dosyaya bakan bir araç baytları `B3 02 73 00` gösterir ama komutu `0x007302B3` olarak çözer; `objdump` bu çevirmeyi senin için yapıyor. Faz 7.30'daki öykünücü, bellekten 4 byte'ı little-endian okuyup 32 bitlik komutu kurmak zorunda — Ders 3.9'daki `print_hex`'in tersi.

---

## 7. Sıkıştırılmış komutlar

Ders 7.1'de RISC-V'nin komut boyutunun "2 ya da 4 byte" olduğunu söylemiştik. Temel komutlar 4 byte, ama **C uzantısı** (RVC) sık kullanılan komutların 16 bitlik kısa biçimlerini ekliyor: `c.add`, `c.li`, `c.lw`... Bir 16-bitlik komut, tam biçimine kodlanabilen sınırlı bir durumu temsil ediyor (örneğin sadece en çok kullanılan 8 register'ı, küçük sabitleri).

Neden? Kod boyutu. Programların yarıdan fazlası birkaç yaygın komuttan oluşuyor (Ders 7.1'deki `sum`'da `add`, `ld`, `addi`); onları yarı yere sığdırmak programı küçültüyor, bu da cache'e (Ders 7.24) daha çok kod sığması demek. Ders 7.1'de RISC-V `sum`'ı sıkıştırmayla 2 ve 4 baytlık komutların karışımıydı; `-march=rv64g` (sıkıştırmasız) ile derleyince hepsi 4 byte oldu. Bu derste ve 7.4–7.6'da sıkıştırmayı kapalı tutacağız (`objdump` daha okunaklı olsun diye); gerçek sistemlerde açık.

Değişken uzunluk burada da bir maliyet getiriyor: bir komutun 2 mi 4 byte mı olduğunu anlamak için ilk birkaç bitine bakmak gerekiyor (alt iki bit `11` değilse komut 16 bitlik). x86-64'ün tam uzunluk belirsizliği kadar kötü değil ama RISC'in "hep 4 byte" sadeliğinden bir sapma.

---

## Alıştırmalar

**1** – `and x10, x11, x12`'yi elle kodla. `and` için `opcode = 0x33`, `funct3 = 0x7`, `funct7 = 0x00`. `r_type` ile doğrula. (x10 = a0, x11 = a1, x12 = a2.)

**2** – `addi x0, x0, 0` komutu ne yapar? Sonucu hesapla. RISC-V'de bu komutun özel bir adı var (`nop`); neden işe yarasın? (İpucu: Ders 7.3'ün sonundaki hizalama, ve Ders 7.20'deki boru hattı.)

**3** – `i_type` fonksiyonu `imm12 & 0xFFF` yapıyor. Bu satır olmasaydı `addi x5, x6, -20` için ne çıkardı? Negatif immediate'ler neden sorun çıkarırdı? (Ders 3.3.)

**4** – RISC-V'de ayrı bir "register kopyala" (`mv x5, x6`) komutu yok. Hangi gerçek komut bunu yapıyor? `x0`'ın sıfır olması bunu nasıl mümkün kılıyor? (Ders 7.1'deki `sum` çıktısında `mv a0, a2` satırını gerçekte hangi komuta çevirdiğini `objdump` ile kontrol et.)

**5** – `0x00A52823`'ü çöz: hangi RISC-V komutu? (İpucu: `opcode = 0x23` S biçimidir, store. S biçimi: `imm[11:5]` [31:25], `rs2` [24:20], `rs1` [19:15], `funct3` [14:12], `imm[4:0]` [11:7], `opcode` [6:0]. `funct3 = 0x2` → `sw`.) Assembler'la doğrula.

<details>
<summary>Cevaplar</summary>

**1** – `r_type(0x00, 12, 11, 0x7, 10, 0x33)`. Bitler: `0000000 01100 01011 111 01010 0110011`. Nibble: `0000 0000 1100 0101 1111 0101 0011 0011` = `0x00C5F533`. Assembler: `and a0, a1, a2` = `0x00C5F533`. ✓

**2** – `x0 = x0 + 0`; `x0` zaten 0 ve ona yazmak etkisiz, yani **hiçbir şey yapmaz** (`nop`, no operation). Kodu `0x00000013`. İşe yarar: (a) hizalama — bir sonraki komutu belli bir adrese getirmek için boşluk doldurur (Ders 7.3'teki hizalı dal hedefleri); (b) boru hattında bir "kabarcık" (bubble) olarak zaman geciktirmek (Ders 7.21). Ders 7.1'deki x86-64 çıktısında gördüğümüz `nopl` da bunun x86 hali.

**3** – `-20`, `int` olarak 32 bitte `0xFFFFFFEC`. `& 0xFFF` olmadan `imm << 20` üst bitleri de kaydırıp `rs1`, `funct3`, `rd`, `opcode` alanlarının üstüne taşardı ve komut bozulurdu. `& 0xFFF`, sadece alttaki 12 biti (ikiye tümleyen gösterimdeki $-20$) tutuyor. Donanım bu 12 biti okurken işaret bitini (11. bit) 32/64 bite genişletip $-20$'yi geri elde ediyor (Ders 3.3, 3.5'teki işaret genişletme).

**4** – `mv x5, x6` aslında `addi x5, x6, 0` (ya da bazı assembler'larda `add x5, x6, x0`): `x6 + 0 = x6`. `x0`'ın sıfır olması, "topla ama bir şey ekleme" yoluyla kopyalamayı mümkün kılıyor; ayrı bir `mv` komutu ISA'da yok, bir **sözde komut** (Ders 7.4). Ders 7.1'deki `mv a0, a2`, objdump'ta aslında `addi a0, a2, 0` ya da sıkıştırılmış `c.mv`.

**5** – `0x00A52823` = `0000000 01010 01010 010 10000 0100011`. S biçimi: `imm[11:5] = 0000000`, `rs2 = 01010` (x10 = a0), `rs1 = 01010` (x10 = a0), `funct3 = 010` (sw), `imm[4:0] = 10000` (16), `opcode = 0100011`. Immediate = `0000000` ++ `10000` = 16. Yani `sw a0, 16(a0)`: a0'daki değeri, a0 + 16 adresine yaz. Assembler `sw a0, 0x10(a0)` ile doğrular.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design, RISC-V Edition* (2. baskı), Bölüm 2.5 ve 2.10: komut biçimleri ve kodlama.
- RISC-V International, *The RISC-V Instruction Set Manual, Volume I* (ücretsiz), Bölüm 2: RV32I temel komut biçimleri; her komutun tam kodlaması.
- "RISC-V Reference Card" (tek sayfa, çevrimiçi): bütün biçimler ve opcode'lar bir bakışta.

**Sıradaki ders:** RISC-V assembly 1. Register'lar, `add`, `addi`, `lw`, `sw`, ve ilk programı RARS simülatöründe çalıştırmak.
