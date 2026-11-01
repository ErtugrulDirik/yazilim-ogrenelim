---
title: "7.9 x86-64 kontrol akışı"
description: "jmp (koşulsuz) ve jcc (koşullu) dallar; bir döngünün x86-64'teki hali ve Faz 7.1 ile karşılaştırması; cmov (conditional move) ile dalsız kod ve dal tahmini maliyetinden kaçınma; switch'in atlama tablosuna (jump table) dönüşmesi ve dolaylı atlama; godbolt'ta if/switch/döngü çıktısı okuma; aynı C kodunun clang ve gcc çıktılarını karşılaştırmak ve endbr64 gibi farkları açıklamak."
gereksinimler: [gcc]
---

Ders 7.8'de bayrakları ve `jcc`'yi tanıdık. Bu ders x86-64'te kontrol akışının tam resmini veriyor: döngüler, `switch`, ve x86-64'ün (RISC-V'de olmayan) bir numarası olan **koşullu taşıma** (`cmov`). Burada ilk kez iki derleyicinin (clang ve gcc) aynı koddan farklı ama eşdeğer çıktı ürettiğini de sistemli göreceğiz; bu, Faz 16'dan itibaren derleyici yazarken "doğru çıktı tek değil" dersinin başlangıcı.

godbolt.org bu dersin en iyi arkadaşı: C yaz, sağda canlı assembly çıktısını gör, derleyici ve optimizasyon seviyesini değiştir. Aşağıdaki çıktılar çapraz derlenmiş clang/gcc'den (`-O1`, AT&T) alındı.

---

## 1. jmp ve jcc

İki temel dal:

- **`jmp hedef`**: koşulsuz atla (RISC-V'deki `j`, Ders 7.5). Hedef bir etiket (PC-göreli) ya da bir register/bellek (`jmp *%rax`, dolaylı).
- **`jcc hedef`**: koşullu atla; `cc` bir koşul (`je`, `jne`, `jl`, `jb`, `jg`, ...). Bayraklara bakar (Ders 7.8), atlar ya da düşer.

Bir döngü (Ders 7.1'deki `sum`'ın aynısı):

```c
long loop(const long *a, long n) { long s = 0; for (long i = 0; i < n; i++) s += a[i]; return s; }
```

```
loop:   xorl  %eax, %eax            # s = 0
        testq %rsi, %rsi            # n <= 0 mi?
        jle   .son                  # evetse donguye girme
        xorl  %ecx, %ecx            # i = 0
.dongu: addq  (%rdi,%rcx,8), %rax   # s += a[i]
        incq  %rcx                  # i++
        cmpq  %rcx, %rsi            # i, n'yi gecti mi?
        jne   .dongu                # degilse tekrar
.son:   retq
```

İki dal: başta `jle` (döngüye hiç girmeme koşulu), sonda `jne` (geri dönüş). Bu, Ders 7.5'teki RISC-V döngüsüyle aynı iskelet; fark, `cmpq` + `jne`'nin RISC-V'de tek `bne` olması (Ders 7.8'deki iki-aşamalı karşılaştırma). Döngünün gövdesi tek komut (`addq ...`) çünkü CISC adresleme (Ders 7.7) okuma ve toplamayı birleştiriyor.

---

## 2. cmov: dalsız seçim

Ders 5.5'te dalsız kodu bitlerle kurmuştuk; Faz 6'da (Ders 6.21) bazı seçimlerin dalsız yapılabildiğini görmüştük. x86-64'te bunun için özel bir komut var: **`cmov`** (conditional move), bayrak doğruysa bir değeri kopyalar, yanlışsa hiçbir şey yapmaz — **dallanmadan**.

```c
int cmp_if(int a, int b) { if (a < b) return a; else return b; }
```

```
cmp_if: movl   %esi, %eax           # eax = b
        cmpl   %esi, %edi           # a, b karsilastir
        cmovll %edi, %eax           # a < b ise eax = a  (yoksa dokunma)
        retq
```

Hiç `jcc` yok! `eax`'i önce `b` yap, sonra "`a < b` ise `a` yap". Dallanma olmadığı için işlemci iki olasılıktan hangisinin olacağını **tahmin etmek** zorunda kalmıyor. Neden önemli? Bir sonraki bölüm.

### Dal tahmini maliyeti

Modern işlemciler komutları boru hattında (Ders 7.20) işliyor: bir dala geldiğinde, sonucu daha belli olmadan hangi yoldan devam edeceğini **tahmin ediyor** (Ders 7.22). Tahmin tutarsa hız kazanıyor; **tutmazsa** boru hattını boşaltıp baştan başlıyor, onlarca çevrim kaybediyor. Tahmin edilmesi zor dallarda (örneğin rastgele veriye bağlı dallar) bu ceza büyük.

`cmov` dalı tamamen ortadan kaldırır: iki değeri de hesapla, birini seç. Tahmin yok, ceza yok. Ama bedeli: iki yolu da hesaplamak gerekir ( `b`'yi önce yükledik, sonra belki `a`'yla değiştirdik). Yollar pahalıysa ya da biri yan etkili (bellek yazması, fonksiyon çağrısı) ise `cmov` kullanılamaz. Derleyici bir tahmin yapar: dal kolay tahmin ediliyorsa `jcc`, zor tahmin ediliyorsa ve yollar ucuzsa `cmov`. Ders 7.22'de rastgele ve sıralı veri üzerinde bu farkı **ölçeceğiz**.

Ders 5.5'teki bit hileleriyle elle kurduğumuz dalsız seçimler, `cmov` olmadan (ya da taşınabilir kod istendiğinde) hâlâ işe yarıyor; `cmov` donanımın bunu tek komutta yapması.

---

## 3. switch ve atlama tablosu

Çok dallı `switch` (Ders 2.3), değerler yoğun bir aralıktaysa (0, 1, 2, ...) bir **atlama tablosu**na (jump table) dönüşür: her durum için bir adres içeren dizi, ve tek bir **dolaylı atlama** ile doğrudan doğru duruma git — sıralı `if-else` denemeleri yapmadan.

```c
int classify(int x) {
    switch (x) {
        case 0: return 42;  case 1: return 17;  case 2: return 99;
        case 3: return 8;   case 4: return 63;  default: return -1;
    }
}
```

gcc (`-O1`):

```
classify:
        cmpl    $4, %edi            # x > 4 mu? (isaretsiz karsilastirma)
        ja      .default            # aralik disi -> default
        jmp     *.L4(,%rdi,8)       # DOLAYLI atlama: .L4[x] adresine git
        .section .rodata
.L4:    .quad   .L_case0            # x=0 icin adres
        .quad   .L_case1
        .quad   .L_case2
        .quad   .L_case3
        .quad   .L_case4
```

`jmp *.L4(,%rdi,8)`: `.L4` tablosunun `x`'inci (× 8 byte, çünkü adresler 64-bit) elemanını oku ve **o adrese atla**. `x` 0–4 ise tek adımda doğru koda, hiç karşılaştırma zinciri olmadan. `cmpl $4` + `ja` ise sınır kontrolü (`ja` işaretsiz "büyük", Ders 7.8; negatif `x` de büyük bir işaretsiz sayı olarak `default`'a düşer — Ders 3.6'nın bir kez daha işe yaradığı yer).

Atlama tablosu $O(1)$; sıralı `if-else` zinciri $O(\text{durum sayısı})$. Derleyici durumlar yoğunsa tablo, seyrekse (örneğin 0, 100, 10000) ikili arama ya da zincir üretir. Değerler küçük ve düzenliyse (bu dersin ilk taslağında olduğu gibi) bazen tabloyu bile atlayıp doğrudan bir aritmetik formül üretir — Faz 16'daki optimizasyonların habercisi.

---

## 4. clang ve gcc: aynı iş, farklı çıktı

Ders 7.1'de iki derleyici kuracağımızı söylemiştik. Aynı C kodunu ikisine verip çıktıları karşılaştırmak öğretici. `max(a, b)`:

```c
int max(int a, int b) { return a > b ? a : b; }
```

**clang (-O2):**
```
max:    movl    %esi, %eax
        cmpl    %esi, %edi
        cmovgl  %edi, %eax
        retq
```

**gcc (-O2):**
```
max:    endbr64
        cmpl    %edi, %esi
        movl    %edi, %eax
        cmovge  %esi, %eax
        ret
```

İkisi de `cmov` kullanıyor (dalsız), ama:

- Komut sırası ve register seçimi farklı. clang `cmovg` (a > b), gcc işlenenleri ters çevirip `cmovge` kullanmış. İkisi de doğru; farklı yollar aynı sonuca.
- gcc'nin başında **`endbr64`** var, clang'de yok (bu ayarlarda). Bu, güvenlik için bir komut: **CET** (Control-flow Enforcement Technology), dolaylı atlamaların (Bölüm 3'teki `jmp *`) sadece `endbr64` ile işaretlenmiş "meşru" hedeflere gitmesini zorlar; Ders 7.14'teki saldırıları zorlaştırır. Hangi derleyicinin hangi güvenlik özelliklerini varsayılan açtığı dağıtıma ve sürüme bağlı.

Bu farklar, ISA'nın (sözleşme) **ne**'yi belirlediğini ama **nasıl**'ı derleyiciye bıraktığını gösteriyor (Ders 7.1). İki çıktı da sözleşmeye uyuyor; hangisi daha hızlı, mikromimariye ve ölçüme bağlı (Faz 11). Derleyici yazmaya başladığımızda (Faz 16) bizim de bu "nasıl" kararlarını vereceğiz: aynı IR'dan birçok geçerli makine kodu üretilebilir, iyi olanı seçmek optimizasyon.

---

## Alıştırmalar

**1** – Bölüm 1'deki döngüde iki dal (`jle`, `jne`) var. Hangisi döngünün her turunda çalışıyor, hangisi sadece bir kez? Bu, Ders 7.5'teki `do-while`'a çevirme optimizasyonuyla nasıl ilişkili?

**2** – `int sel(int c, int a, int b) { return c ? a : b; }`'yi derle. `cmov` mu `jcc` mi üretiliyor? Şimdi `int sel2(int c, int *a, int *b) { return c ? *a : *b; }`'yi derle — bu neden `cmov` ile yapılamaz? (İpucu: `*a` ve `*b`'nin ikisini de okumak güvenli mi? Biri geçersiz pointer'sa?)

**3** – Bölüm 3'teki `switch`'i, durumları 0, 10, 20, 30 yapacak şekilde değiştir (seyrek). Derleyici hâlâ atlama tablosu mu üretiyor, yoksa karşılaştırma zinciri mi? Neden?

**4** – `max`'i hem clang hem gcc ile (godbolt'ta ya da yerel) derle. Çıktılardaki farkları listele: register seçimi, komut sırası, `endbr64`, `ret`/`retq`. Hangileri "anlamlı" fark, hangileri sadece yazım/stil?

**5** – Dal tahmininin zor olduğu bir döngü düşün: `for (i...) if (a[i] > threshold) count++;`, `a` rastgele. Derleyici `count++`'ı `cmov` ile mi `jcc` ile mi yapar? (`-O2` ile dene.) Ders 7.22'de bu kodun rastgele ve sıralı `a` için hız farkını ölçeceğiz; neden sıralı veri daha hızlı olur, tahmin et.

<details>
<summary>Cevaplar</summary>

**1** – `jle` (başta) sadece bir kez çalışır: döngüye hiç girilmeyecekse ($n \le 0$) atlar. `jne` (sonda) her turda çalışır: döngüyü devam ettiren dal. Ders 7.5'teki `do-while` çevirisi tam bunu kullanıyor: koşulu başa koyup her turda iki dal yerine, başta bir giriş-kontrolü (`jle`) + sonda bir devam dalı (`jne`) ile her tur **tek** dal. Derleyici `while`'ı böyle "döndürerek" (loop rotation) tur başına dal sayısını 2'den 1'e indiriyor.

**2** – `sel` `cmov` üretir (iki değer de register'da, okumak bedava ve güvenli): `testl %edi,%edi; cmovel %edx,%eax`. `sel2`'de dikkat çeken bir incelik var: `cmov` **değerleri** (`*a`, `*b`) seçseydi ikisini de okuması gerekirdi, ama `c` false iken `a` geçersiz bir pointer olabilir ve geçersiz adresten okumak çökertir. Clang bunu şöyle çözüyor: `cmoveq %rdx, %rsi` ile **pointer'ı** seçer (`a` mı `b` mi), sonra `movl (%rsi), %eax` ile sadece seçileni okur. Yani `cmov` yine kullanıldı — ama değere değil adrese. Değerleri `cmov`'lamak güvensiz olurdu; derleyici `cmov`'u güvenli kalacak yere (pointer seçimi) taşıdı. Dersi: `cmov`'un "iki yolu da değerlendir" doğası yan etkili/güvensiz **okumalarda** kullanılamaz, ama derleyici çoğu zaman onu güvenli bir noktaya kaydırmanın yolunu bulur; bulamazsa `jcc`'ye düşer.

**3** – 0, 10, 20, 30 seyrek sayılmaz (yoğun, sadece aralıklı); derleyici genellikle `x`'i önce kontrol edip (ya da `x/10` ile indeksleyip) yine tablo kurabilir. Ama 0, 100, 10000 gibi gerçekten seyrek değerlerde tablo $10001$ elemanlı olurdu (çoğu `default`); derleyici onun yerine karşılaştırma zinciri ya da ikili arama üretir. Karar, tablonun boyutu ile hızı arasındaki denge: yoğun → tablo ($O(1)$ ama bellek), seyrek → zincir (az bellek ama $O(n)$).

**4** – Anlamlı olmayan (stil) farklar: register seçimi (`%eax` vs başka), komut sırası, `retq` (clang) vs `ret` (gcc) — ikisi aynı komut, farklı yazım. Anlamlı fark: `endbr64`'ün varlığı bir **güvenlik** kararı (CET), kodun davranışını değil güvenlik özelliklerini değiştirir. İkisi de `cmov` seçmiş (aynı strateji), sadece `cmovg` vs `cmovge` (işlenenleri ters). Hepsi aynı matematiksel sonucu üretiyor; "doğru çıktı tek değil".

**5** – `-O2`'de derleyici bunu genellikle `cmov` ya da dalsız bir forma (`setg` + ekleme) çevirmeye çalışır, çünkü tam da bu desen (rastgele veriye bağlı dal) tahmin edilemez ve `jcc` pahalıdır. Sıralı veride dal tahmini kolaylaşır (uzun süre hep aynı yöne gider, Ders 7.22), bu yüzden `jcc`'li sürüm sıralı veride hızlı, rastgele veride yavaş olur; `cmov`'lu sürüm ise veri sırasından bağımsız sabit hızda. Ders 7.22'de bu farkı milisaniye cinsinden ölçeceğiz. Tahmin: sıralı dizi rastgele diziden birkaç kat hızlı (dal tahmini sayesinde), ama derleyici `cmov` seçtiyse ikisi de aynı.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.6: kontrol akışı, `cmov`, `switch` ve atlama tabloları.
- godbolt.org (Compiler Explorer): C'yi canlı derleyip clang/gcc/MSVC çıktılarını karşılaştırmak.
- Intel, *Control-flow Enforcement Technology Specification*: `endbr64` ve dolaylı dal koruması.

**Sıradaki ders:** System V AMD64 çağrı kuralı. Parametre register'ları, 16-byte yığın hizalaması, prolog/epilog, kırmızı bölge.
