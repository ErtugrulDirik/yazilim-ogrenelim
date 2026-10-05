---
title: "0.2 Bilgisayar nedir: bit, byte, sayı sistemleri"
---

Bu derste kod yazmıyoruz; kağıt ve kalem yeterli. Dört bölüm var:

1. Bilgisayar nedir?
2. Bit, byte, halfword, word ve ASCII
3. Sayı sistemleri
4. Bitlerle aritmetik ve mantık

Her bölümün sonunda alıştırmalar var. Cevaplar kapalı kutularda; önce kendin çöz.

---

## 1. Bilgisayar nedir?

**Hesap makinesi ile bilgisayarın farkı.** Hesap makinesi tek bir iş yapar. Bilgisayar ise kendisine verilen talimat listesine, yani programa göre her işi yapabilir. Fark *programlanabilirliktir*.

**Girdi → işlem → çıktı.** Klavye ve dosyalar girdidir; ekran ve dosyalar çıktıdır; aradaki her şey işlemdir. Örneğin VKİ hesabında girdi kilo ve boy, işlem formül, çıktı ise sayı ve kategoridir.

**İşlemci ve bellek.** Belleği, numaralandırılmış kutulardan oluşan uzun bir raf gibi düşün. Her kutunun bir adresi ve içinde bir sayısı vardır. İşlemci (CPU) kutudan sayı okur, onu işler ve sonucu bir kutuya geri yazar.

**Program da bellekte bir sayıdır.** John von Neumann 1945'te, talimatların da veri gibi aynı bellekte saklanabileceğini yazdı. Bugünkü bilgisayarların neredeyse hepsi bu fikre dayanır: program ayrı bir şey değil, bellekteki sayılardır.

**Her şey sayıdır; anlamı bağlam belirler.** Aynı sayı farklı yerlerde farklı anlamlara gelir:

| Bellekteki değer | Sayı olarak | Harf olarak (ASCII) | x86-64 komutu olarak |
| --- | --- | --- | --- |
| `0x41` | 65 | `A` | — |
| `0xC3` | 195 | — | `ret` (fonksiyondan dön) |

Komutların ayrıntısı Faz 7'de gelecek. Şimdilik akılda kalması gereken tek şey: bilgisayar için her şey sayıdır.

### Alıştırma

**1.1** Telefonunla bir fotoğraf çektin. Girdi ne, işlem ne, çıktı ne?

<details>
<summary>Cevap</summary>

Girdi: kameraya gelen ışık ve ekrana dokunman. İşlem: ışığın sayılara çevrilmesi, renk düzeltme ve sıkıştırma. Çıktı: ekrandaki görüntü ve bellekte kaydedilen dosya.

</details>

---

## 2. Bit, byte, halfword, word ve ASCII

**Neden iki durum?** İki durumu birbirinden ayırmak en güvenilir yoldur: evet/hayır, açık/kapalı. **Bit**, tek bir evet/hayır sorusunun cevabıdır: 0 ya da 1.

**n bit ile 2ⁿ durum.** 1 bit ile 2, 2 bit ile 4, 3 bit ile 8 farklı durum temsil edilir. Her yeni bit, durum sayısını ikiye katlar.

**Tahmin oyunu.** Biri 1 ile 1.000.000 arasında bir sayı tutsun ve sen sadece "büyük mü, küçük mü?" diye sor. Her soruda ihtimalleri yarıya indirirsen en fazla 20 soruda bulursun, çünkü 2²⁰ = 1.048.576, yani bir milyondan büyük. Soru sayısı ile bit sayısı aynı şeydir.

**Birimler:**

| Birim | Bit | Farklı değer sayısı | x86 adı | ARM / RISC-V adı |
| --- | --- | --- | --- | --- |
| Bit | 1 | 2 | — | — |
| Nibble | 4 | 16 | — | — |
| Byte | 8 | 256 | BYTE | byte |
| Halfword | 16 | 65.536 | WORD | halfword |
| Word | 32 | 4.294.967.296 | DWORD | word |
| Doubleword | 64 | yaklaşık 1,8 × 10¹⁹ | QWORD | doubleword |

**Word sabit bir boyut değildir.** Word, işlemcinin doğal çalışma boyutudur ve mimariye göre değişir. x86'da tarihsel nedenlerle WORD 16 bit kalmıştır; ARM ve RISC-V'de word 32 bittir.

**KB ile KiB farkı.** 1 KB = 1000 byte, 1 KiB = 1024 byte. Disk üreticileri KB, işletim sistemleri çoğu zaman KiB kullanır. "1 TB'lık disk neden yaklaşık 931 GB görünüyor?" sorusunun cevabı budur.

**Günlük hayattan örnekler:**

- Bir renk 8 bit kırmızı, 8 bit yeşil ve 8 bit mavi ile, toplam 24 bitle saklanır: 2²⁴ = 16.777.216 farklı renk.
- Bir IPv4 adresi 32 bittir; en fazla 2³² = 4.294.967.296 adres olabilir. IPv6'ya geçilmesinin nedeni budur.

**Harfler de sayıdır: ASCII.** ASCII, 128 karakteri 7 bitlik sayılarla eşleyen bir tablodur:

| Karakter | Sayı |
| --- | --- |
| boşluk | 32 |
| `0` | 48 |
| `A` | 65 |
| `a` | 97 |

`a` ile `A` arasındaki fark tam 32'dir ve 32, ikilikte tek bir bittir. Bunu Bölüm 4'te kullanacağız.

### Alıştırmalar

**2.1** 1 ile 1000 arasında tutulan bir sayı en fazla kaç soruda bulunur?

**2.2** 16 bit ile kaç farklı değer temsil edilebilir?

**2.3** "Hi" kelimesi bellekte hangi iki sayı olarak durur?

<details>
<summary>Cevaplar</summary>

**2.1** 10 soru, çünkü 2¹⁰ = 1024 ≥ 1000.

**2.2** 2¹⁶ = 65.536.

**2.3** `H` = 72, `i` = 105.

</details>

---

## 3. Sayı sistemleri

**Basamak değeri.** Onluk sistemi zaten biliyorsun:

2026 = 2·10³ + 0·10² + 2·10¹ + 6·10⁰

Genel kural: bir sayı, her basamağın tabanın kuvvetiyle çarpılıp toplanmasıdır. Taban 10 yerine 2 olursa ikilik sistemi elde ederiz.

**İkilikten onluğa.** 1101₂ = 1·8 + 1·4 + 0·2 + 1·1 = **13**

**Onluktan ikiliğe: bölme–kalan yöntemi.** Sayıyı sürekli 2'ye böl ve kalanları yaz:

| Adım | Bölünen | ÷ 2 | Kalan |
| --- | --- | --- | --- |
| 1 | 13 | 6 | 1 |
| 2 | 6 | 3 | 0 |
| 3 | 3 | 1 | 1 |
| 4 | 1 | 0 | 1 |

Kalanları **aşağıdan yukarı** oku: **1101₂**. Bu tabloya *iz sürme tablosu* denir; Faz 1'de çok kullanacağız.

**Onaltılık (hex) sistem.** 16 basamak vardır: 0–9 ve A–F (A = 10, …, F = 15). 4 bit tam olarak 1 hex basamağa denk gelir; bu yüzden ikilikten hex'e çevirmek sadece 4'erli gruplamaktır:

156 = 128 + 16 + 8 + 4 = 1001 1100₂ = **0x9C**

**Sekizlik sistem.** 3 bit 1 sekizlik basamağa denk gelir:

010 011 100₂ = **234₈** (kontrol: 2·64 + 3·8 + 4 = 156)

Sekizlik sistemi bugün en çok Linux dosya izinlerinde görürsün (`chmod 755`).

**Hex her yerde.** Web renk kodu `#FF8800`: kırmızı `FF` = 255, yeşil `88` = 136, mavi `00` = 0. Bellek adresleri de hex yazılır.

**Kesirli sayılar: çarpma yöntemi.** Kesirli kısmı sürekli 2 ile çarp, tam kısımları **yukarıdan aşağı** oku:

- 0,625 × 2 = 1,25 → **1**
- 0,25 × 2 = 0,5 → **0**
- 0,5 × 2 = 1,0 → **1**

Sonuç: **0,101₂**. Kontrol: 1/2 + 0/4 + 1/8 = 0,625.

**0,1 ikilikte sonsuzdur.**

0,1 → 0,2 (**0**) → 0,4 (**0**) → 0,8 (**0**) → 1,6 (**1**) → 1,2 (**1**) → 0,4 (**0**) → …

0,4'e geri döndük; bundan sonra aynı adımlar sonsuza kadar tekrar eder: 0,0001100110011…₂. Bu yüzden bilgisayar 0,1'i tam olarak saklayamaz. Bunun sonuçlarını Faz 3'te göreceğiz.

### Alıştırmalar

**3.1** 25'i ikiliğe çevir.

**3.2** 100'ü ikiliğe, sonra hex'e çevir.

**3.3** 10110110₂ kaçtır? Hex karşılığı nedir?

**3.4** 0x1F kaçtır?

**3.5** 777₈ kaçtır?

**3.6** 0,75'i ikiliğe çevir.

<details>
<summary>Cevaplar</summary>

**3.1** 11001₂

**3.2** 1100100₂ = 0x64

**3.3** 182 = 0xB6

**3.4** 31

**3.5** 7·64 + 7·8 + 7 = 511

**3.6** 0,75 × 2 = 1,5 → 1; 0,5 × 2 = 1,0 → 1. Sonuç: 0,11₂

</details>

---

## 4. Bitlerle aritmetik ve mantık

**İkilik toplama tablosu:**

| İşlem | Sonuç | Elde |
| --- | --- | --- |
| 0 + 0 | 0 | 0 |
| 0 + 1 | 1 | 0 |
| 1 + 1 | 0 | 1 |
| 1 + 1 + 1 | 1 | 1 |

Bu, onluktaki "9 + 1 = 10, elde var" ile aynı mantıktır.

**Elde zinciri.** 91 + 46 işlemini 8 bit ile yapalım:

```
  elde:  1111110
         01011011   (91)
       + 00101110   (46)
       ----------
         10001001   (137)
```

Elde, sağdan sola bit bit ilerler. Bu örnekte arka arkaya altı bit boyunca elde taşınıyor.

**Çıkarma ve ödünç.** 1010 (10) − 0011 (3) = 0111 (7). 0'dan 1 çıkarılamadığında soldaki bitten ödünç alınır, tıpkı onluk sistemde olduğu gibi.

**Sabit genişlik ve taşma.** Bilgisayar sınırsız sayıda bit tutmaz. 8 bit ile:

```
   11111111   (255)
 + 00000001   (1)
 ----------
 1 00000000   → 9. bit sığmaz, sonuç 0
```

Arabanın kilometre sayacını düşün: 999999'dan sonra 000000'a döner. Aynı şekilde 8 bitte 200 + 100, 300 değil 44 eder (300 − 256). Negatif sayılar ve taşmanın ayrıntıları Faz 3'te.

**Mantık işlemleri.**

| A | B | A VE B | A VEYA B | A XOR B |
| --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 |
| 0 | 1 | 0 | 1 | 1 |
| 1 | 0 | 0 | 1 | 1 |
| 1 | 1 | 1 | 1 | 0 |

DEĞİL ise biti tersine çevirir: DEĞİL 0 = 1, DEĞİL 1 = 0.

**Bit bit uygulama.** a = 11001010 (0xCA), b = 10100110 (0xA6) için:

| İşlem | Sonuç | Hex |
| --- | --- | --- |
| a VE b | 10000010 | 0x82 |
| a VEYA b | 11101110 | 0xEE |
| a XOR b | 01101100 | 0x6C |
| DEĞİL a | 00110101 | 0x35 |

**De Morgan kuralları.**

- DEĞİL (A VE B) = (DEĞİL A) VEYA (DEĞİL B)
- DEĞİL (A VEYA B) = (DEĞİL A) VE (DEĞİL B)

Dört satırlık bir doğruluk tablosu yazarak ikisini de kendin kontrol et.

**İki küçük uygulama.**

- **Büyük harfi küçük harfe çevirmek:** `A` (01000001) VEYA 00100000 = 01100001 = `a`. Bölüm 2'deki "32 farkı" burada tek bir bit olarak karşımıza çıkıyor.
- **XOR ile gizlemek:** `A` (65) XOR 42 = 107 (`k`). `k` (107) XOR 42 = 65 (`A`). Aynı anahtarla iki kez XOR yapmak başa döndürür. Bu şifrelemenin en basit fikridir ama gerçek bir güvenlik sağlamaz.

### Alıştırmalar

**4.1** 00110101 + 00011110 = ? Onluk karşılıklarıyla kontrol et.

**4.2** 8 bitte 250 + 10 işleminin sonucu ne olur?

**4.3** 0x0F VE 0x3C, 0x0F VEYA 0x3C ve 0x0F XOR 0x3C işlemlerinin sonuçları nedir?

**4.4** `z` harfini büyük harfe çevirmek için hangi bit kapatılmalıdır? Sonuç ne olur?

<details>
<summary>Cevaplar</summary>

**4.1** 01010011₂ = 83 (53 + 30)

**4.2** 260 sekiz bite sığmaz; sonuç 260 − 256 = 4 (00000100) olur ve elde dışarı taşar.

**4.3** VE: 0x0C, VEYA: 0x3F, XOR: 0x33

**4.4** `z` = 122 = 01111010. Değeri 32 olan bit kapatılır: 01011010 = 90 = `Z`.

</details>

---

## Kaynaklar

- Charles Petzold, *Code* (2. baskı), Bölüm 7–12: sayı sistemleri, ikilik ve onaltılık sistem, ASCII.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §1.1 ve §2.1.
- Donald Knuth, *The Art of Computer Programming*, Cilt 2, §4.1: konumsal sayı sistemlerinin tarihi ve matematiği (meraklısı için).

**Sıradaki faz:** Kağıt üzerinde düşünmeyi, yani algoritma ve akış diyagramını öğreneceğiz.
