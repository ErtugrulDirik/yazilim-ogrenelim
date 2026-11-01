---
title: "7.8 x86-64 aritmetik ve bayraklar"
description: "x86-64 aritmetik komutları (add, sub, inc, imul, neg); durum bayrakları CF, ZF, SF, OF ve her birinin ne yakaladığı; CF'nin işaretsiz taşmayı, OF'nin işaretli taşmayı yakalaması ve Faz 3'teki carry/overflow farkının donanımdaki tam karşılığı; cmp ve test komutlarının çıkarma/and yapıp sonucu atması, sadece bayrak ayarlaması; jcc ve setcc'nin bayrakları okuması; işaretli ve işaretsiz karşılaştırmanın farklı dallar (jl vs jb) üretmesi."
gereksinimler: [gcc]
---

Ders 7.5'te RISC-V'de karşılaştır-ve-dallan tek komuttu (`blt`). x86-64 (ve ARM) bunu **iki aşamaya** böler: bir komut hesabı yapıp **bayraklar** (durum bitleri) ayarlar, sonraki komut bayraklara bakıp dallanır. Bu ders o bayrakları açıyor, ve Faz 3'teki en ince ayrımlardan birinin — işaretsiz "elde" (carry) ile işaretli "taşma" (overflow) farkının (Ders 3.8) — donanımda iki ayrı bit olarak nasıl durduğunu gösteriyor.

---

## 1. Aritmetik komutlar

| Komut | İşlem |
| --- | --- |
| `addq %rsi, %rdi` | `rdi += rsi` |
| `subq %rsi, %rdi` | `rdi -= rsi` |
| `incq %rdi` | `rdi++` |
| `negq %rdi` | `rdi = -rdi` (ikiye tümleyen, Ders 6.18) |
| `imulq %rsi, %rdi` | `rdi *= rsi` (işaretli) |
| `andq`, `orq`, `xorq`, `shlq`, `shrq`, `sarq` | bit işlemleri (Ders 5) |

Çoğu, hedefi hem kaynak hem varış olarak kullanıyor (`rdi = rdi + rsi`); RISC-V'nin üç-register biçiminin (`add rd, rs1, rs2`) tersine, x86-64 iki-register (hedef ezilir). Bu CISC'in iki-işlenenli geleneği.

`shrq` (mantıksal, soldan 0) ve `sarq` (aritmetik, soldan işaret biti) ayrımı Ders 5.1'deki işaretsiz/işaretli sağa kaydırma; derleyici tipe göre birini seçer. `imul` işaretli çarpma; işaretsiz için `mul`.

---

## 2. Dört bayrak

Her aritmetik/mantık komutu, sonuç hakkında **durum bayraklarını** (`RFLAGS` register'ındaki bitler) ayarlar. Dördü önemli:

| Bayrak | Adı | 1 olur eğer |
| --- | --- | --- |
| **ZF** | Zero | sonuç sıfır |
| **SF** | Sign | sonucun en yüksek biti 1 (işaretli yorumda negatif) |
| **CF** | Carry | **işaretsiz** taşma: en üst bitten elde çıktı ya da ödünç alındı |
| **OF** | Overflow | **işaretli** taşma: ikiye tümleyen sonucu temsil edilemez |

ZF ve SF açık: sonuca bakıp belirlenirler. Asıl incelik CF ile OF arasında, ve bu Faz 3'ün kalbindeki ayrım.

---

## 3. CF ile OF: Faz 3'ün donanımdaki hali

Ders 3.8'de şunu görmüştük: aynı toplama bit deseni, işaretsiz yorumda "elde taştı mı?", işaretli yorumda "ikiye tümleyen taştı mı?" diye **iki farklı** soruya yol açar, ve cevaplar farklı olabilir. İşlemci her toplamada **ikisini de** hesaplar: CF işaretsiz cevabı, OF işaretli cevabı tutar. 8-bitlik toplamalarla çalışma zamanında görelim (`setc`/`seto` ile bayrakları okuyarak):

```
  a   b | res | CF OF
200 100 |  44 |  1  0
100  50 | 150 |  0  1
255   1 |   0 |  1  0
127   1 | 128 |  0  1
```

Her satırı Faz 3 gözüyle oku:

- **200 + 100**: işaretsiz $300 > 255$, elde taştı → **CF = 1**. Ama ikiye tümleyen yorumda $200 = -56$, $-56 + 100 = 44$, aralıkta ($-128..127$) → **OF = 0**. İşaretsiz taştı, işaretli taşmadı.
- **100 + 50**: işaretsiz $150 \le 255$, elde yok → **CF = 0**. İşaretli $100 + 50 = 150 > 127$, aralık dışı → **OF = 1**. Tam tersi.
- **255 + 1**: işaretsiz $256$ sarar → CF = 1. İşaretli $-1 + 1 = 0$ → OF = 0.
- **127 + 1**: işaretsiz $128 \le 255$ → CF = 0. İşaretli $127 + 1$ taşar (en büyük pozitif + 1 = en küçük negatif) → OF = 1.

CF ve OF **bağımsız**: dört kombinasyonun hepsi mümkün. İşlemci hangisinin "doğru" taşma olduğunu bilmez — bu, sayıyı `int` mi `unsigned` mı saydığına bağlı, ve o bilgi sadece **derleyicide** (tip sisteminde) var. Donanım ikisini birden üretir, derleyici hangisine bakacağını seçer. Ders 3.8'deki "taşmayı önceden test et" ve UBSan'ın yakaladığı işaretli taşma, altta bu OF bitine dayanıyor.

---

## 4. cmp ve test: hesapla, at, sadece bayrak bırak

Karşılaştırma için x86-64 iki özel komut kullanır:

- **`cmp b, a`**: `a - b` hesaplar, **sonucu atar**, sadece bayrakları ayarlar. ("a, b'ye göre nasıl?")
- **`test b, a`**: `a & b` hesaplar, sonucu atar, bayrakları ayarlar. (Genellikle `test a, a` ile "a sıfır mı?", ya da `test maske, a` ile "şu bitler var mı?")

Neden sonucu atan komutlar? Çünkü çoğu karşılaştırmada farkın ya da AND'in **değeri** gerekmiyor, sadece **ilişkisi** gerekiyor: eşit mi, küçük mü, sıfır mı. `cmp`/`test` register harcamadan bu ilişkiyi bayraklara yazıyor. `a == b` için: `cmp b, a` sonra ZF'ye bak (fark sıfırsa eşit).

`test a, a` ile "sıfır mı" testi, `cmp $0, a`'dan kısa (ve AND'in sonucu da sıfırsa ZF=1). Derleyici "a sıfır mı" için hep `test`, "şu bit kümesi var mı" için `test maske` üretir — Ders 5.2'deki bayrak testinin (`flags & MASK`) assembly hali.

---

## 5. jcc ve setcc: bayrakları okumak

Bayraklar ayarlandıktan sonra, **koşullu** komutlar onları okur:

- **`jcc` (koşullu dal)**: `je` (ZF=1, eşit), `jne`, `jl` (işaretli küçük), `jb` (işaretsiz küçük), `jg`, `ja`...
- **`setcc`**: koşulu bir bayta (0/1) yazar (dallanmadan).
- **`cmovcc`** (koşullu taşıma): Ders 7.9.

Koşul adları iki aileye ayrılıyor, ve bu Ders 3.6'daki tuzağın donanımdaki hali:

| Anlam | İşaretli | İşaretsiz |
| --- | --- | --- |
| küçük | `jl` / `setl` (SF≠OF) | `jb` / `setb` (CF=1) |
| büyük | `jg` / `setg` | `ja` / `seta` |
| eşit | `je` (her ikisi de ZF) | `je` |

"less" (l) işaretli, "below" (b) işaretsiz. Aynı `cmp`, farklı `jcc`. C'de görelim:

```c
int s_less(int a, int b)           { return a < b; }
int u_less(unsigned a, unsigned b) { return a < b; }
```

```
s_less: cmpl %esi, %edi
        setl %al               # isaretli: SF != OF
        ...
u_less: cmpl %esi, %edi
        setb %al               # isaretsiz: CF
        ...
```

**Aynı** `cmpl` komutu; tek fark `setl` (işaretli) ve `setb` (işaretsiz). Ders 3.6'da `int a = -1; unsigned b = 1; a < b` ifadesinin "yanlış" verdiğini görmüştük; sebebi derleyicinin `a`'yı `unsigned`'a çevirip `setb`/`jb` üretmesi, ve `0xFFFFFFFF > 1` olması. Bayraklar düzeyinde: işaretli karşılaştırma OF ve SF'ye, işaretsiz CF'ye bakar; aynı bitler iki soruya iki cevap. Faz 3'ün bütün işaret dersi, bu iki `jcc` ailesinde özetleniyor.

`test` ve `je`/`jne` ile sıfır/bit testleri:

```c
int is_zero(int a)   { return a == 0; }
int both_bits(int a) { return (a & 0x6) != 0; }
```

```
is_zero:   testl %edi, %edi     # a & a, ZF = (a == 0)
           sete  %al
both_bits: testb $6, %dil       # a & 0x6, ZF = (yok)
           setne %al
```

`testl %edi, %edi` (a AND a) sonucu a'nın kendisi; sıfırsa ZF=1. `testb $6` (= `0b110`), 1. ve 2. bitlerden biri var mı diye bakıyor; `setne` (ZF=0, yani AND sıfır değil) sonucu veriyor. Ders 5.2'deki `(flags & MASK) != 0` deyiminin donanımı.

---

## Alıştırmalar

**1** – `cmp` neden sonucu atıyor? "a − b'nin değeri gerekmiyor ama ilişkisi gerekiyor" ne demek? `cmp` yerine `sub` kullansaydık ne kaybederdik?

**2** – Şu toplamalarda (8-bit) CF ve OF'yi elle tahmin et, sonra Bölüm 3'teki programla doğrula: (a) 128 + 128 (b) 64 + 64 (c) 200 + 200 (d) 50 + 50.

**3** – `a == 0` için `test a, a` kullanmak, `cmp $0, a`'dan neden tercih edilir? (İpucu: komut uzunluğu, Ders 7.1; ve `test`'in ekstra bir register/sabit gerektirmemesi.)

**4** – C'de `unsigned x; if (x - 1 < x) ...` kodu neredeyse her zaman doğru mu yanlış mı? Hangi `jcc` üretilir, ve `x = 0` olduğunda ne olur? (Ders 3.6, 3.8; CF'yi düşün.) Derleyip `objdump` ile bak.

**5** – `jg` (işaretli büyük) `SF`, `OF`, `ZF`'nin hangi kombinasyonunu kontrol eder? Neden sadece `SF`'ye bakmak yetmez? (İpucu: Ders 3.8'deki taşma; `cmp` sırasında OF set olursa SF yanıltıcı olur. Örnek: `INT_MIN` ile bir pozitif sayıyı karşılaştır.)

<details>
<summary>Cevaplar</summary>

**1** – `cmp` sonucu atıyor çünkü karşılaştırmada çoğu zaman farkın **değeri** değil, **işareti/sıfırlığı** gerekiyor (eşit mi, küçük mü). Bu bilgi bayraklarda. `sub` kullansaydık fark bir register'a yazılır, o register'ı harcar ve (eğer `a`'nın eski değeri sonra lazımsa) onu ezerdi. `cmp` hiçbir register'ı değiştirmeden sadece bayrak bırakıyor; Ders 7.4'teki `lw t4, ...` sonrası `beq` gibi "hesapla ama değeri tutma" fikrinin aracı.

**2** – (a) 128+128: işaretsiz 256→0, CF=1; işaretli $-128 + -128 = -256$, aralık dışı, OF=1. (b) 64+64=128: işaretsiz 128, CF=0; işaretli $64+64=128>127$, OF=1. (c) 200+200=400→144: işaretsiz taşar CF=1; işaretli $-56 + -56 = -112$, aralıkta, OF=0. (d) 50+50=100: CF=0, OF=0 (ikisi de aralıkta). Programla doğrulanır.

**3** – `test %eax, %eax` bir register'ı kendisiyle AND'liyor, ekstra bir sabit (`$0`) kodlamaya gerek yok; komut daha kısa (immediate alanı yok). `cmp $0, %eax` bir immediate içerir, daha uzun. İkisi de aynı ZF'yi ayarlar (a AND a = a; a − 0 = a; sıfırsa ZF=1). Kod boyutu küçük olunca cache'e daha çok sığar (Ders 7.24); derleyiciler bu yüzden hep `test`'i seçer.

**4** – `x - 1 < x` işaretsizde neredeyse her zaman **doğru**, ama `x = 0` için **yanlış**: `0 - 1 = 0xFFFFFFFF` (sarar, Ders 3.8), ve `0xFFFFFFFF < 0` işaretsizde yanlış. Derleyici `unsigned` olduğu için `jb`/`setb` (CF) üretir. `x = 0`'da `x - 1` CF ile sarar; karşılaştırma `0xFFFFFFFF < 0` → yanlış. Bu, işaretsiz aritmetikte "bir çıkarınca küçülür" varsayımının `x = 0`'da çöktüğü klasik hata; döngü sınırlarında (`for (unsigned i = n; i >= 0; i--)` sonsuz döngü) sık görülür.

**5** – `jg`: `ZF = 0 && SF == OF`. Sadece SF'ye bakmak yetmez çünkü `cmp` sırasında işaretli taşma (OF=1) olursa sonucun işaret biti (SF) yanıltıcıdır: gerçek fark negatif olması gerekirken taşma yüzünden pozitif görünebilir. `SF == OF` koşulu bunu düzeltir — taşma olduysa SF'yi "ters" yorumlar. Örnek: `INT_MIN` ($-2^{31}$) ile 1'i karşılaştır: `INT_MIN - 1` taşar (OF=1), ham sonuç pozitif görünür (SF=0); SF≠OF olduğu için `jl` doğru şekilde "INT_MIN < 1" der. İşte bu yüzden işaretli karşılaştırma iki bite (SF ve OF) bakmak zorunda; Ders 3.8'deki taşmanın karşılaştırmayı neden bozabileceğinin donanım çözümü.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.5–3.6: aritmetik, bayraklar, `cmp`/`test`, koşullu dallar; işaretli/işaretsiz karşılaştırma.
- Intel, *Software Developer's Manual, Volume 1*, Bölüm 3.4.3: `RFLAGS` ve durum bayraklarının anlamı.
- Ders 3.8 (taşma): bu dersin donanımsız önceli; CF/OF farkının "neden" kısmı orada.

**Sıradaki ders:** x86-64 kontrol akışı. `jmp`, `jcc`, `cmov`; godbolt'ta if/switch/döngü çıktısı okumak; aynı kodun clang ve gcc çıktılarını karşılaştırmak.
