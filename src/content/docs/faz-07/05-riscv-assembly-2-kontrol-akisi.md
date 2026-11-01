---
title: "7.5 RISC-V assembly 2: kontrol akışı"
description: "Koşullu dallanma komutları (beq, bne, blt, bge ve işaretsiz halleri); bgt, ble gibi sözde dalların blt/bge'ye çevrilmesi; if, if/else ve çok dallı kararın assembly karşılığı; while ve for döngülerinin dallanmayla kurulması; j ve jal; B biçiminin immediate kodlaması ve dalın PC'ye göreli olması; her yapıyı Faz 1'deki akış diyagramıyla eşleştirmek."
gereksinimler: [rars]
---

Ders 7.4'te düz bir döngü yazdık ama kararın (`if`) ve döngünün nasıl kurulduğunu hızlıca geçtik. Bu ders kontrol akışını tam kuruyor: C'deki her `if`, `else`, `while`, `for`, assembly'de birkaç **dallanma** komutuna dönüşür. Faz 1'de akış diyagramı çizip (Ders 1.2) okların geri dönüşünü döngü, dalını karar olarak görmüştük; assembly tam olarak o diyagramın metin hali. Bu eşleştirmeyi görünce, bir derleyicinin C'yi assembly'ye nasıl çevirdiğinin ilk yarısını anlamış olacaksın.

---

## 1. Koşullu dallanma

RISC-V'de karar, iki register'ı karşılaştırıp sonuca göre bir etikete atlayan **dal** (branch) komutlarıyla verilir:

| Komut | Atlar eğer | C karşılığı |
| --- | --- | --- |
| `beq a, b, L` | a == b | `if (a == b) goto L;` |
| `bne a, b, L` | a != b | `if (a != b) goto L;` |
| `blt a, b, L` | a < b (işaretli) | `if (a < b) goto L;` |
| `bge a, b, L` | a >= b (işaretli) | `if (a >= b) goto L;` |
| `bltu a, b, L` | a < b (işaretsiz) | — |
| `bgeu a, b, L` | a >= b (işaretsiz) | — |

Faz 3'ün dersi burada donanıma yansıyor: **işaretli ve işaretsiz karşılaştırma farklı komutlar**. `blt` ikiye tümleyen olarak karşılaştırır (−1 < 0), `bltu` bit deseni olarak (0xFFFFFFFF > 0). Ders 3.6'daki işaretli-işaretsiz karşılaştırma tuzağı, assembly'de "yanlış dal komutunu seçmek" olarak görünür; derleyici tipe bakıp doğru olanı seçer.

Dikkat: RISC-V'de doğrudan "küçük mü" (`<`) sorusunu register'a koyan komut yok (`slt` var ama sonuç verir, dallanmaz); karşılaştır-ve-dallan tek komutta. Ayrıca `bgt` (büyüktür), `ble` (küçük eşit) gibi komutlar **sözde**: assembler bunları işlenenleri takas ederek `blt`/`bge`'ye çevirir (`bgt a, b, L` = `blt b, a, L`). Altı gerçek dal komutu, bütün karşılaştırmaları karşılıyor.

---

## 2. if ve if/else

**`if` (else yok):** koşul **yanlışsa** gövdeyi atla. C'deki koşulu **tersine çevirip** dallanıyoruz:

```c
if (a < b)
    a = a + 1;
// devam
```

```
        bge     t0, t1, devam    # !(a < b) ise govdeyi atla
        addi    t0, t0, 1        # a = a + 1
devam:
        ...
```

"`a < b` ise artır" demek yerine "`a >= b` ise **atla**" diyoruz. Derleyici neredeyse her `if`'i böyle ters koşulla çevirir: gövdeye girmek yerine, girmemek için dallanmak daha az komut (gövde sıradan akışla, araya dal koymadan, çalışır).

**`if/else`:** iki gövde, biri atlanmalı.

```c
if (a < b) x = 1;
else       x = 2;
```

```
        bge     t0, t1, else     # a >= b ise else'e
        li      t2, 1            # x = 1  (if govdesi)
        j       devam            # else'i atla
else:
        li      t2, 2            # x = 2  (else govdesi)
devam:
```

`if` gövdesinin sonundaki `j devam` kritik: yoksa akış `else` gövdesine de girerdi. Bu, Faz 1'deki akış diyagramının (Ders 1.2) tam karşılığı: karar baklavasından iki ok çıkar, ikisi de aşağıda birleşir, ama birleşmeden önce birinci kol ikinciyi atlamalı.

**Çok dallı karar** (işaret fonksiyonu, Ders 2.3'teki `switch`/if-else zinciri):

```
# x < 0 -> -1,  x == 0 -> 0,  x > 0 -> 1
main:
        li      t0, -42
        blt     t0, zero, neg    # x < 0 ?
        bgt     t0, zero, pos    # x > 0 ?
        li      a0, 0            # buraya geldiyse x == 0
        j       yaz
neg:    li      a0, -1
        j       yaz
pos:    li      a0, 1
yaz:    li      a7, 1
        ecall
        li      a7, 10
        ecall
```

```
-1
```

`t0 = -42` için ilk dal (`blt`, işaretli "küçük") `neg`'e atlıyor, `a0 = -1`. Sıralı denemeler bir if-else-if zinciri; her `j yaz`, bir sonraki kolu atlamak için.

---

## 3. Döngüler

**`while`:** koşulu başta dene, yanlışsa çık; gövdenin sonunda başa dön.

```c
while (i <= n) { ... i++; }
```

```
dongu:
        bgt     t2, t0, bitti    # i > n ise cik  (kosulun tersi)
        ...                      # govde
        addi    t2, t2, 1        # i++
        j       dongu            # basa don
bitti:
```

Faktöriyel, bu kalıpla:

```
# n! hesapla
main:
        li      t0, 5            # n
        li      t1, 1            # sonuc
        li      t2, 1            # i
dongu:
        bgt     t2, t0, bitti    # i > n ise cik
        mul     t1, t1, t2       # sonuc *= i
        addi    t2, t2, 1        # i++
        j       dongu
bitti:
        mv      a0, t1
        li      a7, 1
        ecall
        li      a7, 10
        ecall
```

```
120
```

$5! = 120$. (`mul`, RISC-V'nin M uzantısının komutu; RARS destekler. Çarpmanın kendisi olmasaydı Ders 5.13'teki kaydır-topla ile kurulurdu.) Yapı Ders 1.3'teki faktöriyel akış diyagramının, Ders 2.8'deki döngülü `fact`'in aynısı: başta koşul testi, gövdede çarpma, sonda sayaç artırma ve geri dönüş.

**`for`:** C'de `for (i = 0; i < n; i++)` aslında bir `while`'ın kısaltması (Ders 2.3); assembly'de de öyle çevrilir — başlatma döngüden önce, koşul başta, artırma sonda. Ders 7.4'teki dizi toplama programı bir `for` döngüsüydü.

**`do-while`** (gövde en az bir kez çalışır): koşul **sonda**. Bu aslında en basit biçim, tek dal:

```
dongu:
        ...                      # govde
        blt     t2, t0, dongu    # i < n ise tekrar
```

Derleyiciler bir `while`'ı bazen `do-while`'a çevirir (koşulun ilk turda doğru olduğunu biliyorsa), çünkü bir dal komutu daha az (Ders 7.15'teki optimizasyonlar).

---

## 4. j ve jal

`j L` (jump) koşulsuz atlama: her zaman `L`'ye git. Ama bu bir **sözde komut**; gerçek komut `jal` (jump and link):

```
jal  rd, L       # rd = sonraki komutun adresi (donus adresi); sonra L'ye atla
j    L     =     jal x0, L    # donus adresini x0'a (coplenir) yaz -> sadece atla
```

`jal`'in asıl işi fonksiyon çağırmak (Ders 7.6): atlarken dönüş adresini bir register'a saklar ki fonksiyon bitince geri dönebilsin. `j`'de dönüş adresine ihtiyaç yok, bu yüzden `x0`'a (her zaman sıfır, Ders 7.3) yazılır — yani atılır. `x0` hilesi bir kez daha ayrı bir komuttan kurtarıyor.

Dallar (`beq`, ...) yakın hedeflere (±4 KB, Bölüm 5), `jal` daha uzağa (±1 MB) atlar. Çok uzak hedefler için `jalr` (register'dan, Ders 7.6) ya da iki komut gerekir.

---

## 5. B biçimi ve PC-göreli dallanma

Dal komutları, hedefi **mutlak adres** olarak değil, **o anki komuttan ne kadar uzakta** olduğu olarak (PC-göreli) kodlar. `beq t0, t1, hedef`'te, `hedef` iki komut ileriyse immediate +8.

```
main:
        beq     t0, t1, hedef    # adres 0
        nop                      # adres 4
hedef:
        nop                      # adres 8
```

Bu `beq` `0x00628463` olarak kodlanıyor. B biçiminin (Ders 7.3) immediate'i beş parçaya dağılmış; çözünce ofset **+8** çıkıyor (0'dan 8'e). PC-göreli olmasının iki faydası var: (a) kod bellekte nereye yüklenirse yüklensin dallar doğru çalışır (**konumdan bağımsız kod**, Ders 7.17); (b) ofsetler küçük olduğu için az bit yeter. Bu yüzden B biçiminin immediate'i sadece 13 bit (±4 KB); daha uzak koşullu dal gerekirse derleyici yakına bir `beq` + uzağa bir `jal` kombinasyonu kurar.

Immediate'in neden parçalı olduğunu Ders 7.3'te açıklamıştık: her bit mümkün olduğunca sabit konumda dursun, donanımın işi kolay olsun. B biçimi bunun en uç örneği; okuması zor ama çözen devre küçük.

---

## Alıştırmalar

**1** – Şu C kodunu assembly'ye çevir: `if (a > 0 && b > 0) c = 1; else c = 0;`. İki koşulu nasıl birleştirirsin? (İpucu: `&&` kısa devre, Ders 2.3; ilki yanlışsa doğrudan `else`'e atla.)

**2** – Ders 7.4'teki dizi toplama döngüsünü, `do-while` biçimine (koşul sonda) çevir. Dizinin **en az bir** elemanı olduğunu varsayabilirsin. Kaç dal komutu azaldı?

**3** – `blt t0, t1, L` ile `bltu t0, t1, L` arasındaki farkı göster: `t0 = -1`, `t1 = 1` iken hangisi atlar, hangisi atlamaz? Bunu Ders 3.6'daki `int`/`unsigned` karşılaştırma tuzağıyla ilişkilendir.

**4** – Collatz dizisini (Ders 2.5) assembly'de yaz: `n` tekse `3n+1`, çiftse `n/2`; `n == 1` olana kadar adım say. `n` çift mi diye `andi t1, t0, 1` (en düşük bit, Ders 5.2) ile bak. `n = 27` için kaç adım? (Beklenen: 111.)

**5** – `beq t0, t1, hedef` komutu, `hedef` **geriye** 12 komut (−48 byte) olacak şekilde yazılırsa immediate ne olur? İşaret biti nerede? Negatif ofsetin ikiye tümleyen (Ders 3.3) olarak kodlandığını B biçiminde doğrula (bir geri dönüşlü döngü yazıp `objdump`/RARS ile bak).

<details>
<summary>Cevaplar</summary>

**1** – `&&` kısa devre: ilk koşul yanlışsa ikincisine bakma, doğrudan else.

```
        ble     t0, zero, else   # !(a > 0) ise else  (a <= 0)
        ble     t1, zero, else   # !(b > 0) ise else
        li      t2, 1            # ikisi de dogru: c = 1
        j       devam
else:
        li      t2, 0
devam:
```

Her iki koşul da kendi dalıyla else'e atlıyor; ikisi de geçilirse `c = 1`. Bu, kısa devrenin assembly hali: `a > 0` yanlışsa `b`'ye hiç bakılmıyor.

**2** –

```
dongu:
        lw      t4, 0(t0)
        add     t2, t2, t4
        addi    t0, t0, 4
        addi    t3, t3, 1
        blt     t3, t1, dongu    # i < n ise tekrar (kosul sonda)
```

While halinde gövdenin başında `beq ... bitti` ve sonunda `j dongu` vardı: iki dal. do-while'da tek dal (`blt`). Her turda bir dal komutu az; döngü $n$ kez döndüğü için $n$ komut tasarruf. Derleyicilerin `while`'ı `do-while`'a çevirme (loop rotation) optimizasyonunun kazancı bu.

**3** – `t0 = -1` bit deseni `0xFFFFFFFF`, `t1 = 1`. `blt` (işaretli): $-1 < 1$ doğru → **atlar**. `bltu` (işaretsiz): $\text{0xFFFFFFFF} = 4294967295 > 1$ → **atlamaz**. Aynı bitler, farklı yorum, zıt sonuç — Ders 3.6'daki tuzağın ta kendisi. C'de `int a = -1; unsigned b = 1; a < b` ifadesi `a`'yı `unsigned`'a çevirip `bltu` üretir ve "yanlış" (atlamaz) sonucunu verir; derleyici tipe göre `blt` mi `bltu` mu seçeceğine karar veriyor.

**4** –

```
main:   li      t0, 27           # n
        li      t1, 0            # adim sayaci
dongu:  li      t2, 1
        beq     t0, t2, bitti    # n == 1 ise cik
        andi    t2, t0, 1        # n'in en dusuk biti
        beq     t2, zero, cift   # bit 0 ise cift
        li      t3, 3            # tek: n = 3n + 1
        mul     t0, t0, t3
        addi    t0, t0, 1
        j       say
cift:   srli    t0, t0, 1        # cift: n = n / 2  (saga 1 kaydir, Ders 5.1)
say:    addi    t1, t1, 1
        j       dongu
bitti:  mv      a0, t1
        li      a7, 1
        ecall
        li      a7, 10
        ecall
```

27 için 111 adım. `andi t2, t0, 1` çift/tek testi (Ders 5.2'deki en düşük bit); `srli t0, t0, 1` ikiye bölme (işaretsiz sağa kaydırma = /2, Ders 5.1). Çiftse çarpma/toplama hiç yapılmıyor — tam da C'deki `if/else`'in iki kolu.

**5** – −48 byte ofset: immediate = −48. B biçiminin işaret biti (imm[12]) komutun 31. bitinde, ve −48'in ikiye tümleyen gösterimi 13 bitte `1 111111010000` (−48 = −64 + 16). En yüksek bit (işaret) 1 olduğu için 31. bit 1. Geriye dönüşlü döngülerde (örneğin faktöriyeldeki `j dongu`, ya da bir `bne ..., dongu`) ofset hep negatif; `objdump` bunu `beq t0, t1, 0x...` olarak çözerken RARS'ın Text segment penceresinde ham komutu görebilirsin. Negatif dal ofseti, Faz 1'deki akış diyagramının "geri dönen oku"nun (döngü) bit düzeyindeki hali.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design, RISC-V Edition* (2. baskı), Bölüm 2.7: kararlar ve dallanma; 2.9: akış denetimi.
- RISC-V International, *The RISC-V Instruction Set Manual, Volume I*: dal komutları ve B/J biçimlerinin immediate kodlaması.
- Ders 1.2 (akış diyagramı) ve 1.3 (iz sürme): bu dersteki yapıların kâğıt üstündeki halleri.

**Sıradaki ders:** RISC-V assembly 3: fonksiyonlar. Çağrı kuralı, `ra`, `sp`, caller/callee-saved register'lar, ve özyinelemeli faktöriyel.
