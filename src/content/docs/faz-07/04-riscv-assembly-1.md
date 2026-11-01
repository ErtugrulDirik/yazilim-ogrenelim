---
title: "7.4 RISC-V assembly 1"
description: "RARS simülatörünü kurmak; bir assembly dosyasının yapısı (.text, .data, etiketler); register'lar ve ABI adları; li, mv, add, addi, lw, sw komutları; la ile adres yükleme; ecall ile sistem çağrıları (PrintInt, Exit); bir diziyi toplayan ilk tam programı yazıp çalıştırmak; sözde komutların gerçek komutlara açılması."
gereksinimler: [rars]
---

Ders 7.3'te komutların bitlere nasıl kodlandığını gördük. Artık komutları elle yazıp **çalıştırmaya** başlıyoruz. Bunun için bir simülatör kullanacağız: gerçek bir RISC-V çipi almadan, programları yazıp adım adım izleyebileceğimiz bir ortam. Bu ve sonraki iki ders (7.5, 7.6) RISC-V assembly'nin temel komutlarını öğretiyor; sonunda C'de yazdığın her kontrol yapısını ve fonksiyonu assembly'de yazabileceksin.

---

## 1. RARS

**RARS** (RISC-V Assembler and Runtime Simulator), MARS'ın (klasik MIPS simülatörü) RISC-V halidir. Bir assembly dosyası yazarsın, RARS onu assemble edip çalıştırır; register'ları, belleği ve her komutun etkisini pencerede gösterir. Java ile yazılmış, tek bir `.jar` dosyası.

Kurulum (bu dersin gereksinim kutusuna bak):

1. **Java** kur (JDK ya da JRE 8+). Çoğu sistemde `java -version` ile kontrol et.
2. RARS'ı [github.com/TheThirdOne/rars](https://github.com/TheThirdOne/rars) sürümler sayfasından indir (`rars1_6.jar` gibi).
3. Çalıştır: `java -jar rars1_6.jar` (grafik arayüz açılır) ya da komut satırında `java -jar rars1_6.jar <dosya.s>`.

Grafik arayüzde: dosyayı aç, **Assemble** (F3), **Run** (F5) ya da **Step** (F7) ile adım adım. Sağdaki panelde register'ların değeri canlı değişir; assembly öğrenirken en değerli görünüm bu. Bu derste programların sadece metnini ve çıktısını göstereceğiz; sen RARS'ta açıp **adım adım izleyerek** her register'ın nasıl değiştiğini görmelisin — assembly'yi gerçekten anlamanın tek yolu bu.

RARS varsayılan olarak **RV32** (32-bitlik) bir makineyi öykünür: register'lar 32 bit, bir `word` 4 byte, bellek işlemleri `lw`/`sw` (load/store word). Ders 7.1'deki derleyici çıktısı 64-bitlik RV64 içindi (orada `ld`/`sd`, 8 byte); bu derslerde RARS'ın RV32'siyle çalışacağız, yani diziler `.word` (4 byte) ve adresler 4'er ilerleyecek. (RARS'ı `rv64` seçeneğiyle 64-bit de yapabilirsin ama gerek yok.)

---

## 2. Bir assembly dosyasının yapısı

```
        .data
dizi:   .word   3, 1, 4, 1, 5, 9, 2, 6
n:      .word   8

        .text
main:
        ...komutlar...
```

- **`.data`**: başlangıç verisi. `dizi:` bir **etiket** (label), bir bellek adresine isim verir; `.word 3, 1, ...` o adrese ardışık 32-bitlik tamsayılar koyar (Ders 4.1'deki dizi, bellekte). `n:` tek bir word.
- **`.text`**: çalıştırılabilir komutlar.
- **`main:`**: programın başladığı etiket.

Etiketler Faz 1'deki akış diyagramının ok hedefleri (Ders 1.2) ve C'deki `goto` etiketleri gibi; assembly'de dallanma hep etiketlere yapılır, assembler onları adrese çevirir (Ders 7.3).

---

## 3. İlk komutlar

| Komut | Anlamı | C karşılığı |
| --- | --- | --- |
| `li t0, 42` | t0 = 42 | `t0 = 42;` |
| `mv t0, t1` | t0 = t1 | `t0 = t1;` |
| `add t0, t1, t2` | t0 = t1 + t2 | `t0 = t1 + t2;` |
| `addi t0, t1, 5` | t0 = t1 + 5 | `t0 = t1 + 5;` |
| `sub t0, t1, t2` | t0 = t1 − t2 | `t0 = t1 - t2;` |
| `lw t0, 0(t1)` | t0 = bellek[t1 + 0] | `t0 = *(int*)t1;` |
| `sw t0, 0(t1)` | bellek[t1 + 0] = t0 | `*(int*)t1 = t0;` |
| `la t0, dizi` | t0 = dizi'nin adresi | `t0 = &dizi;` |

RISC'in load/store kuralı (Ders 7.1) burada kendini gösteriyor: belleğe **sadece** `lw`/`sw` erişiyor; `add` gibi bir komut doğrudan bellekle çalışamıyor. Önce `lw` ile register'a yükle, hesabı register'da yap, gerekirse `sw` ile geri yaz.

`lw t0, 0(t1)` biçimindeki `0(t1)`, Ders 4.5'teki pointer erişimi: `t1` bir adres, `0` ofset. Ofseti değiştirerek bir struct'ın üyelerine ya da bir dizinin elemanlarına erişilir (Ders 7.12). Bu, Ders 7.3'teki I biçiminin (`lw` bir I-tipi komut) immediate alanı.

**ABI adları.** Ders 7.3'te register'ların hem numarası (`x5`) hem rol adı (`t0`) olduğunu söylemiştik. Assembly'de rol adlarını kullanıyoruz çünkü okunaklı: `t0`–`t6` geçici değerler, `a0`–`a7` argüman ve dönüş, `zero` = `x0`. Ders 7.6'da bu rollerin fonksiyon çağrılarındaki anlamını göreceğiz; şimdilik `t` register'larını serbest çalışma alanı gibi kullanıyoruz.

---

## 4. Sistem çağrıları

Bir simülatörde (ve gerçek işletim sisteminde, Faz 10) ekrana yazmak, girdi almak gibi işler **sistem çağrısı** (syscall) ile yapılır: `a7`'ye hangi hizmeti istediğini yaz, argümanı `a0`'a koy, `ecall` komutunu çalıştır. RARS'ın bazı çağrıları:

| `a7` | Hizmet | Argüman |
| --- | --- | --- |
| 1 | PrintInt | `a0` = yazılacak tamsayı |
| 4 | PrintString | `a0` = string adresi |
| 5 | ReadInt | sonuç `a0`'da |
| 10 | Exit | — |

`ecall` (environment call), programın işletim sistemine/simülatöre "benim adıma şunu yap" demesi. Ders 7.18'de gerçek Linux'ta syscall'ları, Ders 7.28'de donanım tarafını (trap) göreceğiz.

---

## 5. İlk tam program: dizi toplamı

Ders 7.1'deki `sum`'ı, Ders 7.2'deki oyuncak makinede yazdığımız programı, şimdi gerçek RISC-V'de yazalım:

```
# Bir dizinin elemanlarini toplayip yazdirir.
        .data
dizi:   .word   3, 1, 4, 1, 5, 9, 2, 6     # 8 eleman
n:      .word   8

        .text
main:
        la      t0, dizi            # t0 = dizinin adresi
        lw      t1, n               # t1 = eleman sayisi (8)
        li      t2, 0               # t2 = toplam = 0
        li      t3, 0               # t3 = i = 0
dongu:
        beq     t3, t1, bitti       # i == n ise cik
        lw      t4, 0(t0)           # t4 = dizi[i]
        add     t2, t2, t4          # toplam += t4
        addi    t0, t0, 4           # adresi bir word (4 byte) ilerlet
        addi    t3, t3, 1           # i++
        j       dongu
bitti:
        mv      a0, t2              # yazdirilacak sayi
        li      a7, 1               # 1 = PrintInt
        ecall
        li      a7, 10              # 10 = Exit
        ecall
```

RARS ile çalıştırınca:

```
31
```

$3+1+4+1+5+9+2+6 = 31$. Programın iskeleti Ders 7.1'deki derleyici çıktısıyla aynı: adres ve sayaç kur, `beq` ile döngü koşulu, gövdede `lw`+`add`, sonra pointer'ı 4 ilerlet (bir `word` = 4 byte, Ders 4.1) ve `i`'yi artır, `j` ile başa dön.

İki yöntem farkı: Ders 7.1'deki derleyici, `i` sayacı yerine pointer'ı bitiş adresiyle karşılaştırıyordu (bir register tasarrufu). Burada hem `i`'yi hem adresi ayrı tuttuk, okunaklı olsun diye. İkisi de doğru; derleyici genellikle daha az register kullanan sürümü seçer (Ders 6.30'daki register tahsisi).

`j dongu` ve `mv a0, t2` birer **sözde komut**: assembler bunları gerçek komutlara açıyor. `j dongu` → `jal x0, dongu` (atla, dönüş adresini `x0`'a — yani hiçbir yere — yaz, Ders 7.5); `mv a0, t2` → `addi a0, t2, 0` (Ders 7.3). RARS'ın bellek penceresinde (ya da `objdump`'ta) gerçek komutları görebilirsin. Sözde komutlar assembly'yi okunaklı yapar ama altta hep tanıdığımız temel komutlar var.

---

## Alıştırmalar

**1** – Yukarıdaki programı RARS'ta aç, **Step** (F7) ile adım adım çalıştır. Her adımda `t0`, `t2`, `t3` register'larının nasıl değiştiğini izle. `t0` neden her turda 4 artıyor, `t3` neden 1?

**2** – Programı, diziyi toplamak yerine **en büyük** elemanı bulup yazdıracak şekilde değiştir. (İpucu: `blt t2, t4, ...` — "t2 < t4 ise" — Ders 7.5'te göreceğiz ama deneyebilirsin; ya da `bge` ile.) 9 çıkmalı.

**3** – `lw t4, 0(t0)` yerine ofseti kullanarak pointer'ı ilerletmeden aynı işi yapmayı dene: döngüde `lw t4, 0(t0)`, `lw t5, 4(t0)` gibi. Bu neden sadece sabit boyutlu diziler için işe yarar, değişken `n` için neden işe yaramaz?

**4** – `li t0, 0x12345678` yaz ve RARS'ta assemble et. Bellek/kod penceresinde kaç gerçek komuta açıldığına bak. Neden bir komut yetmiyor? (İpucu: I biçiminin immediate'i 12 bit, Ders 7.3; 32 bitlik bir sabit için `lui` + `addi` gerekir, Ders 7.7'de.)

**5** – Programa, toplamı yazdırdıktan sonra bir de **ortalamayı** (toplam / n) yazdıran kod ekle. RISC-V'de bölme `div` komutu (Ders 7.4 kapsamı dışı ama RARS destekler): `div a0, t2, t1`. Tam sayı bölmesi olduğu için sonuç ne çıkar, ve bu Ders 3.7'deki tamsayı bölmesiyle nasıl ilişkili?

<details>
<summary>Cevaplar</summary>

**1** – `t0` dizinin adresini tutuyor ve her eleman 4 byte (bir `word`) olduğu için bir sonraki elemana geçmek adresi 4 artırmak demek (`addi t0, t0, 4`); Ders 4.6'daki pointer aritmetiğinin assembly hali, ama burada ölçekleme (×4) elle. `t3` eleman **sayacı** (`i`), 0'dan `n`'e birer birer, bu yüzden 1 artıyor. İkisi farklı birimde ilerliyor: biri byte adresi, öbürü eleman indeksi.

**2** – En büyüğü bulma:

```
        lw      t2, 0(t0)           # t2 = dizi[0], simdilik en buyuk
        li      t3, 1               # i = 1'den basla
dongu:
        beq     t3, t1, bitti
        slli    t4, t3, 2           # t4 = i * 4
        add     t5, t0, t4          # t5 = &dizi[i]
        lw      t5, 0(t5)           # t5 = dizi[i]
        bge     t2, t5, atla        # en buyuk >= dizi[i] ise degistirme
        mv      t2, t5              # yeni en buyuk
atla:
        addi    t3, t3, 1
        j       dongu
```

9 çıkar. `slli t4, t3, 2` (sola 2 kaydır = ×4, Ders 5.1) indeksi byte ofsetine çeviriyor — Ders 7.1'deki derleyicinin `slli a1, a1, 3` adımının aynısı (orada eleman 8 byte'tı).

**3** – Sabit ofsetlerle (`0(t0)`, `4(t0)`, `8(t0)`) her elemana ayrı komut yazmak, ancak eleman sayısı **derleme zamanında** biliniyorsa işe yarar: `n` elemanlı dizi için `n` ayrı `lw` komutu yazarsın. Değişken `n` için bu imkânsız (kaç `lw` yazacağını bilemezsin); döngü ve pointer ilerletme gerekir. Bu, Ders 4.1'deki "dizi boyutu çalışma zamanında belliyse döngü şart" ilkesinin assembly hali. (Derleyiciler küçük sabit boyutlu döngüleri bazen "açarak" (unroll, Ders 7.15) ofsetli koda çevirir.)

**4** – `li t0, 0x12345678` iki komuta açılır: `lui t0, 0x12345` (üst 20 biti yükle) ve `addi t0, t0, 0x678` (alt 12 biti ekle). I biçiminin immediate'i 12 bit olduğu için (Ders 7.3) tek komutla en fazla ±2048'lik bir sabit yüklenebilir; 32 bitlik bir sabit, 20 + 12 olarak iki komuta bölünür (Ders 7.7'deki `lui`). `li` bir sözde komut: assembler sabite göre bir ya da iki gerçek komut üretir.

**5** – `div a0, t2, t1` → $31 / 8 = 3$ (tamsayı bölmesi, kalan atılır). Ders 3.7'deki `/` operatörünün aynısı: C'de `31 / 8` de 3'tür, çünkü ikisi de aynı donanım bölme komutuna (ya da onun taklidine) dönüşür. Kesirli ortalama istiyorsan ya kalanı (`rem`) ayrı yazdırmalı ya da kayan noktaya geçmeli (Ders 7.29). Tamsayı bölmesi aşağı değil **sıfıra** yuvarlar (Ders 6.17); pozitif sayılarda ikisi aynı.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design, RISC-V Edition* (2. baskı), Bölüm 2.1–2.6: register'lar, aritmetik ve bellek komutları.
- RARS wiki (github.com/TheThirdOne/rars/wiki): sistem çağrıları listesi, assembler yönergeleri, kullanım.
- "RISC-V Assembly Programmer's Manual" (github.com/riscv-non-isa/riscv-asm-manual): sözde komutlar ve ABI adları.

**Sıradaki ders:** RISC-V assembly 2: kontrol akışı. `beq`, `bne`, `jal`; if/else ve döngülerin assembly karşılığı, akış diyagramıyla eşleştirme.
