---
title: "7.7 x86-64 register'ları ve adresleme"
description: "x86-64'ün 16 genel amaçlı register'ı; rax/eax/ax/al iç içe geçişi ve 32-bit yazmanın üst yarıyı sıfırlaması; AT&T sözdizimi; adresleme modu formülü disp(base, index, scale); mov ile bellek erişimi; lea'nın bellek okumadan adres aritmetiği yapması ve çarpma/çokterimli için kullanımı; işaret ve sıfır genişleten taşımalar (movzbl, movsbl); 32-bit sabit yüklemenin tek komutta olması."
gereksinimler: [gcc]
---

Ders 7.1'de x86-64'ün CISC olduğunu, `addq (%rdi,%rcx,8), %rax` gibi bir komutun tek başına adres hesaplayıp bellek okuyup toplayabildiğini gördük. Şimdi bu mimariyi doğrudan öğreniyoruz. x86-64, masaüstü ve sunucuların mimarisi; godbolt'ta, `objdump` çıktısında, hata ayıklarken sürekli karşına çıkacak. RISC-V'den sonra onu okumak, iki farklı felsefeyi (Ders 7.1) somut görmek demek.

Bu bölüm (7.7–7.11) x86-64'ü RISC-V kadar derinlemesine kurmuyor; amaç **okuyabilmek** ve temel farkları görmek. Senin makinen muhtemelen ARM ya da x86-64; bu derslerin kodunu bir Linux ortamında (Ders 7 gereksinimleri) `gcc`/`clang` ile derleyip `objdump` ile inceleyebilirsin.

---

## 1. On altı register ve iç içe geçmiş adları

x86-64'ün 16 genel amaçlı register'ı var, her biri 64 bit: `rax`, `rbx`, `rcx`, `rdx`, `rsi`, `rdi`, `rbp`, `rsp`, ve `r8`–`r15`. RISC-V'nin 32'sine karşı 16; CISC geleneğinin izi (Ders 7.1).

Her register'ın **alt parçalarına** da ayrı adlarla erişilebiliyor — tarihsel bir miras (8086'nın 16 bitlik `ax`'i, 80386'nın 32 bitlik `eax`'i, x86-64'ün 64 bitlik `rax`'i üst üste bindi):

```
 63                              31              15       7      0
[================ rax ================================================]
                                 [============ eax =================]
                                                 [==== ax =========]
                                                 [= ah =][= al ====]
```

| 64 bit | 32 bit | 16 bit | 8 bit (düşük) |
| --- | --- | --- | --- |
| `rax` | `eax` | `ax` | `al` |
| `rdi` | `edi` | `di` | `dil` |
| `r8` | `r8d` | `r8w` | `r8b` |

Ders 3.2'deki "aynı sayının farklı genişlikleri" fikri, burada tek register'da fiziksel olarak iç içe. `al`'e yazmak `rax`'ın en düşük baytını değiştirir, gerisine dokunmaz.

Ama bir sürpriz: **32-bitlik parçaya yazmak üst 32 biti sıfırlar.** Çalışma zamanında doğrulayalım (`rax`'ı tümü 1 yapıp alt parçalara yazarak):

```
eax'e 5 yazildiktan sonra rax = 0x0000000000000005
ax'e 5 yazildiktan sonra rax  = 0xFFFFFFFFFFFF0005
```

`eax`'e (32 bit) yazınca üst 32 bit sıfırlandı; `ax`'e (16 bit) yazınca üst kısım korundu. Bu, x86-64'ün kasıtlı bir kuralı: 32-bit işlemler üst yarıyı temizler. Pratik sonucu derleyici çıktısında görünür — `int` (32 bit) döndüren bir fonksiyon `eax` kullanır ve üst yarıyı umursamaz; bu yüzden Ders 7.1'deki `sum`'da `xorl %eax, %eax` (32-bit sıfırlama) tüm `rax`'ı sıfırlıyordu.

---

## 2. AT&T sözdizimi

x86 assembly'nin iki yazımı var: **Intel** ve **AT&T**. Unix dünyası (gcc, clang, `objdump`) varsayılan olarak AT&T kullanır; biz de onu kullanacağız (Ders 7.1'deki çıktılar da AT&T'ydi). Kuralları:

- **Hedef sağda**: `movq %rsi, %rdi` → `rdi = rsi` ("kaynaktan hedefe"). RISC-V ve Intel'in tersine.
- **Register'lar `%` ile**: `%rax`. Sabitler `$` ile: `$10`.
- **Komutlara boyut eki**: `q` (quad, 8 byte), `l` (long, 4 byte), `w` (word, 2), `b` (byte, 1). `movq` 64-bit, `movl` 32-bit taşır.
- **Bellek erişimi parantezle**: `(%rax)` → `rax`'ın gösterdiği adresteki değer.

Hedefin sağda olması ilk başta kafa karıştırır ama tutarlı. Intel sözdizimi (`mov rdi, rsi`, hedef solda) godbolt'ta bir düğmeyle açılır; ikisini de tanımak iyi.

---

## 3. Adresleme modları

CISC'in gücü burada. Bir bellek adresi tek bir komutta şu formülle hesaplanabilir:

$$
\text{adres} = \text{disp} + \text{base} + \text{index} \times \text{scale}
$$

AT&T yazımı: `disp(base, index, scale)`. `scale` 1, 2, 4 ya da 8 (eleman boyutları). Örnekler, `long a[]` üzerinde (C → x86-64, `-O1`):

```c
long elem(long *a, long i)  { return a[i]; }
long elem3(long *a, long i) { return a[i+3]; }
```

```
elem:   movq  (%rdi,%rsi,8), %rax     # a[i]:   rax = *(rdi + rsi*8)
        retq
elem3:  movq  24(%rdi,%rsi,8), %rax   # a[i+3]: rax = *(rdi + rsi*8 + 24)
        retq
```

`a` `rdi`'de, `i` `rsi`'de. `(%rdi,%rsi,8)` tam olarak Ders 4.6'daki pointer aritmetiği: `a + i`, eleman 8 byte olduğu için `i`'yi 8 ile ölçekle. `a[i+3]`'te `+3` eleman, `+24` byte (disp alanı) olarak ekleniyor. RISC-V'de (Ders 7.1) bu üç iş (çarp, topla, oku) üç komuttu; x86-64'te tek `movq`. Bu adresleme modu C'nin dizi ve struct erişimi için tam biçilmiş kaftan (Ders 7.12).

---

## 4. lea: bellek okumadan adres aritmetiği

`lea` (load effective address) adresleme modu formülünü hesaplar ama **belleğe hiç dokunmaz**: adresin kendisini register'a koyar. İsmi "adres yükle" ama asıl kullanımı bambaşka: ücretsiz bir aritmetik makinesi.

```c
long times9(long x)        { return x * 9; }
long poly(long x, long y)  { return 4*x + y + 10; }
```

```
times9: leaq  (%rdi,%rdi,8), %rax     # rax = rdi + rdi*8 = 9*rdi
        retq
poly:   leaq  (%rsi,%rdi,4), %rax     # rax = rsi + rdi*4 = y + 4*x
        addq  $10, %rax               # + 10
        retq
```

`times9` bir çarpma komutu (`imul`) kullanmıyor; `lea` ile $x + 8x = 9x$. Ders 5.14 ve 6.23'te derleyicinin `x * 9`'u `x + (x << 3)`'e çevirdiğini görmüştük; x86-64'te `lea` bunu tek komutta yapıyor, üstelik bir toplama ve bir ölçekli çarpmayı birleştirerek. `poly`'de `4*x + y` tek `lea` ile, `+10` ayrı. `lea` taban + indeks×{1,2,4,8} + sabit biçimindeki her ifadeyi tek komutta hesaplar; derleyiciler bunu adresler için değil, sıradan aritmetik için bolca kullanır.

Dikkat: `lea` bayrakları (Ders 7.8) etkilemez, oysa `add` etkiler. Bu bazen `lea`'nın `add` yerine seçilmesinin bir başka sebebi (araya giren bir karşılaştırmanın bayraklarını bozmamak).

---

## 5. Genişleten taşımalar

Dar bir değeri geniş bir register'a taşırken üst bitler ne olur? İki seçenek, Ders 3.5'teki iki genişletme:

- **Sıfır genişletme** (`movz...`): üstü 0 ile doldur. İşaretsiz değerler için.
- **İşaret genişletme** (`movs...`): üstü işaret bitiyle doldur. İşaretli değerler için.

```c
int lowbyte(int x) { return (unsigned char)x; }
```

```
lowbyte: movzbl %dil, %eax           # dil (x'in alt baytı) -> eax, sifir genislet
         retq
```

`movzbl` = move, zero-extend, byte → long: `dil`'deki (x'in en düşük baytı, `unsigned char`) baytı `eax`'a sıfır genişleterek taşır. `(unsigned char)x` bir baytı alıp sıfır genişlettiği için (Ders 3.7) tam karşılık bu. Eğer `(signed char)x` olsaydı derleyici `movsbl` (işaret genişleten) üretirdi. Faz 3'teki işaretli/işaretsiz dönüşüm farkı, assembly'de farklı komut: donanım hangi genişletmeyi yapacağını komuttan biliyor.

Bu, Bölüm 1'deki "32-bit yazma üst yarıyı sıfırlar" kuralıyla birleşince neden `movzbl` (32-bite genişletir) kullanıldığını açıklar: `eax`'a yazmak zaten `rax`'ın üst 32 bitini sıfırlıyor, ayrıca `movzbq` yazmaya gerek yok. Derleyici bu kuralı bilip kısa komutu seçiyor.

---

## 6. Sabit yükleme

RISC-V'de 32-bitlik bir sabiti yüklemek iki komut gerektiriyordu (`lui` + `addi`, Ders 7.4), çünkü komut 32 bit ve içine 32-bitlik sabit sığmaz. x86-64'te komutlar **değişken uzunlukta** (Ders 7.1), dolayısıyla sabit komutun içine doğrudan gömülür:

```
movl  $0x12345678, %eax     # tek komut; sabit komutun 4 byte'ina gomulu
movabsq $0x123456789ABCDEF0, %rax   # 64-bit sabit; komut 10 byte
```

CISC'in değişken uzunluğu burada avantaj: büyük sabit = uzun komut, ama tek komut. RISC'in sabit uzunluğu burada dezavantaj: büyük sabit = birkaç komut. İkisinin de bir bedeli var (RISC-V'de daha fazla komut, x86-64'te komut uzunluğunu çözmek zor, Ders 7.1); tasarım tercihi.

---

## Alıştırmalar

**1** – `movq %rsi, %rdi` ne yapar? AT&T sözdiziminde hedef hangisi? Aynı işlem RISC-V'de hangi komut olurdu (Ders 7.4)?

**2** – `leaq (%rdi,%rdi,4), %rax` neyi hesaplar? Bunu `x * 5` olarak derlenen bir C fonksiyonuyla doğrula (`clang -O1 -S`). `x * 10` için derleyici ne üretir? (İpucu: `5x` sonra bir kaydırma ya da iki `lea`.)

**3** – `al`, `ax`, `eax`, `rax` arasındaki ilişkiyi Ders 3.2'deki tip genişlikleriyle eşleştir. `movb $0xFF, %al` sonra `rax`'ı okursan (önce `rax = 0` ise) ne çıkar? Ya `movl $0xFF, %eax` ise? (Bölüm 1'deki kuralı kullan.)

**4** – Şu C fonksiyonunu x86-64'e derle ve çıktıyı oku: `long idx(long *m, long r, long c) { return m[r*8 + c]; }`. Adresleme modunun `r*8+c`'yi nasıl tek komutta hesapladığını açıkla. (İpucu: iki `lea`/`mov` mu, tek adresleme mi?)

**5** – `lea` ile `add` arasındaki farkı (Bölüm 4'ün sonu) bir örnekle göster: bir karşılaştırmanın (`cmp`) bayraklarını bozmadan bir toplama yapmak gerektiğinde derleyici neden `lea` seçer? Küçük bir C kodu (`if (a == b) c = a + d;`) derleyip bak.

<details>
<summary>Cevaplar</summary>

**1** – `rdi = rsi` (kaynak `%rsi` sağdan sola değil, AT&T'de **kaynak solda, hedef sağda**: `mov kaynak, hedef`). Hedef `%rdi`. RISC-V'de `mv rdi_karsiligi, rsi_karsiligi`, yani `addi rd, rs, 0` (Ders 7.3). İki mimaride de "kopyala" ayrı komut değil, `mov`/`addi` ile.

**2** – `rax = rdi + rdi*4 = 5*rdi`. `long f(long x){return x*5;}` → `leaq (%rdi,%rdi,4), %rax`. `x*10`: $10x = 2 \cdot 5x$, derleyici genellikle `leaq (%rdi,%rdi,4), %rax` sonra `addq %rax, %rax` (×2) üretir; ya da `leaq 0(,%rdi,8), ... ` + `lea` kombinasyonu. İki `lea` ya da `lea`+kaydırma; `imul` yerine, çünkü `lea` daha hızlı (Ders 7.8'deki gibi basit komut).

**3** – `al` = 8 bit (`char`/`int8_t`), `ax` = 16 (`short`), `eax` = 32 (`int`), `rax` = 64 (`long`); Ders 3.2'deki genişlikler. `rax=0` iken `movb $0xFF, %al`: sadece alt bayt değişir, `rax = 0x00000000000000FF`. `movl $0xFF, %eax`: 32-bit yazma, üst 32 bit **sıfırlanır** (zaten 0'dı), `rax = 0x00000000000000FF` — bu örnekte aynı, ama `rax` başta sıfır değilse `movb` üst 56 biti korur, `movl` üst 32 biti sıfırlar (Bölüm 1).

**4** – `idx`: `m` `rdi`, `r` `rsi`, `c` `rdx`. İndeks `r*8 + c`, ama erişilen `m[r*8+c]` bellekte `m + (r*8+c)*8` bayt. Clang şunu üretir: `shlq $6, %rsi` (r × 64, yani r×8 eleman × 8 bayt), `addq %rdi, %rsi` (`m` tabanını ekle), sonra `movq (%rsi,%rdx,8), %rax` (üstüne `c*8` ekleyip oku). `r*8` kısmı `shl $6` (6 bit sola = ×64, Ders 5.1) ile, `c` kısmı okuma komutunun ölçekli indeksiyle (`%rdx,8`) yapıldı — iki ayrı adım ama çarpma komutu (`imul`) hiç yok; hepsi kaydırma, toplama ve adresleme. Katsayılar 2'nin kuvveti olduğu için ölçek ve kaydırma yetti.

**5** – `if (a == b) c = a + d;`: `cmpq %rsi, %rdi` (a==b testi, bayrakları ayarlar), sonra koşullu olarak `a+d`. Toplamayı `addq` ile yapsaydık `cmp`'nin ayarladığı bayraklar bozulurdu — ama burada toplama `cmp`'den sonra, dalın içinde, sorun yok. Asıl fark **conditional move** (`cmov`, Ders 7.9) kullanıldığında ortaya çıkar: `cmp` ile `cmov` arasında bayrakları bozmadan bir adres/değer hesaplamak gerekirse `lea` seçilir, çünkü `add` bayrakları ezer, `lea` ezmez. Derleyici çıktısında `lea`'nın `add` yerine tercih edildiği yerlerin çoğu bu ya da "üç işlemi tek komutta birleştirme" (Bölüm 4) sebebiyle.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.1–3.4: x86-64 register'ları, veri taşıma, adresleme modları, `lea`.
- Intel, *64 and IA-32 Architectures Software Developer's Manual, Volume 2*: komut referansı (`MOV`, `LEA`, `MOVZX`/`MOVSX`).
- godbolt.org: C'yi x86-64'e canlı derleyip AT&T/Intel sözdizimi arasında geçiş yapmak.

**Sıradaki ders:** x86-64 aritmetik ve bayraklar. `add`, `sub`, `imul`, `cmp`, `test`; CF, ZF, SF, OF bayrakları ve Faz 3'teki carry/overflow farkının donanımdaki karşılığı.
