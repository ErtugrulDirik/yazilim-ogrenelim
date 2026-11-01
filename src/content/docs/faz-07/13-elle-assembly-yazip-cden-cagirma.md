---
title: "7.13 Elle assembly yazıp C'den çağırma"
description: "Assembly'de bir fonksiyon yazıp C'den çağırmak; .globl ile sembolü dışa açmak ve çağrı kuralına (ABI) uymak; GAS (AT&T) ile NASM (Intel) sözdizimlerinin aynı işi yapması; ayrı assemble edip C ile linklemek; inline assembly, çıktı/girdi işlenenleri ve kısıtlar (constraints); ne zaman elle assembly yazmanın anlamlı olduğu ve riskleri; .note.GNU-stack notu."
gereksinimler: [gcc, nasm]
gereksinimNotu: "NASM'ı (Intel sözdizimli assembler) bu derste kullanıyoruz; GAS zaten gcc ile gelir."
---

Şimdiye kadar derleyicinin ürettiği assembly'yi **okuduk**. Bu ders tersini yapıyor: assembly'yi elle **yazıp** C programından çağırıyoruz. Bunu yapabilmek, Ders 7.10'daki çağrı kuralının (ABI) neden bir sözleşme olduğunu somut gösteriyor — C ve assembly, kim derlerse derlesin, aynı kurala uyduğu için birbirini çağırabiliyor. Ayrıca Faz 11'de (SIMD) ve gömülü/çekirdek kodunda bazen elle assembly gerekiyor; temelini burada atıyoruz.

---

## 1. Bir sembol dışa açmak

C'den çağrılabilecek bir assembly fonksiyonu iki şey gerektirir: (1) bir **global sembol** (fonksiyonun adı, linker'ın görebilmesi için), (2) **çağrı kuralına uymak** (argümanları doğru register'dan al, sonucu doğru register'a koy).

GAS (AT&T) sözdiziminde `long kare(long x)`:

```
        .text
        .globl  kare            # sembolu disa ac (C'den gorunur)
kare:                           # long kare(long x)
        movq    %rdi, %rax      # rax = x   (1. arg rdi, System V, Ders 7.10)
        imulq   %rdi, %rax      # rax = x * x
        ret                     # sonuc rax'te
        .section .note.GNU-stack,"",@progbits
```

`.globl kare`, `kare` etiketini linker'ın görebileceği bir sembole çevirir (olmazsa C'den bulunamaz, "undefined reference"). Gövde ABI'ye uyuyor: `x` `rdi`'den geldi (Ders 7.10), sonuç `rax`'e kondu. Fonksiyon bu sözleşmeye uyduğu sürece C onu sıradan bir C fonksiyonu gibi çağırabilir — içinin assembly olduğunu bilmesine gerek yok.

Son satırdaki `.note.GNU-stack`: modern linker'lar, yığının çalıştırılabilir (executable) olup olmadığını bu nottan anlar. Elle yazılmış bir `.s` dosyasında bu not yoksa linker "çalıştırılabilir yığın" varsayıp uyarır (güvenlik riski, Ders 7.14'teki saldırılarla ilgili). Boş `@progbits` notu "yığın çalıştırılamaz" der; derleyicinin ürettiği dosyalarda otomatik var, elle yazarken eklemek gerekir.

---

## 2. GAS ve NASM: aynı iş, iki sözdizimi

Ders 7.7'de AT&T ve Intel sözdizimlerinden söz ettik. İki ayrı **assembler** de var: **GAS** (GNU assembler, gcc'yle gelir, varsayılan AT&T) ve **NASM** (Netwide Assembler, Intel sözdizimi). Aynı `kup(x) = x³` fonksiyonunu NASM ile:

```
        global  kup             ; NASM: sembolu disa ac
        section .text
kup:                            ; long kup(long x)
        mov     rax, rdi        ; rax = x        (Intel: hedef SOLDA)
        imul    rax, rdi        ; rax = x*x
        imul    rax, rdi        ; rax = x*x*x
        ret
        section .note.GNU-stack noalloc noexec nowrite progbits
```

Intel sözdizimi farkları (Ders 7.7): hedef **solda** (`mov rax, rdi` = `rax = rdi`), register'larda `%` yok, sabitlerde `$` yok. Aynı makine kodunu üretir; sadece insan yazımı farklı. NASM gömülü/işletim sistemi dünyasında yaygın; GAS, gcc araç zincirinin parçası.

---

## 3. Ayrı assemble, sonra link

Her dosyayı ayrı ayrı nesne dosyasına (`.o`) çevirip C ile linkliyoruz — Ders 2.11'deki çok dosyalı derlemenin aynısı, bir dosya C değil assembly:

```sh
gcc  -c asmfun.s    -o asmfun_gas.o      # GAS -> .o
nasm -f elf64 asmfun.asm -o asmfun_nasm.o # NASM -> .o
gcc  main.c asmfun_gas.o asmfun_nasm.o -o prog
```

C tarafı sadece bir **bildirim** (prototype) görüyor:

```c
#include <stdio.h>
long kare(long x);      // assembly'de (GAS)
long kup(long x);       // assembly'de (NASM)
int main(void) {
    printf("kare(7) = %ld, kup(4) = %ld\n", kare(7), kup(4));
    return 0;
}
```

```
kare(7) = 49, kup(4) = 64
```

C derleyicisi `kare` ve `kup`'un içini görmüyor, sadece "`long` alıp `long` döndüren bir fonksiyon" olduğunu biliyor. `call kare` üretiyor; linker bunu assembly'deki `kare:` etiketine bağlıyor (Ders 7.17'deki sembol çözümleme). Sözleşme (ABI) sayesinde her şey oturuyor: C argümanı `rdi`'ye koyar, assembly oradan alır; assembly sonucu `rax`'e koyar, C oradan alır. İki taraf birbirinin içini hiç görmeden anlaşıyor.

---

## 4. Inline assembly

Ayrı dosya yerine, assembly'yi doğrudan C'nin içine gömmek: **inline assembly**. Bu derste (ve Faz 6'da bayrakları okurken) kullandığımız `__asm__`. Bir karesini ve bir farkı inline hesaplayalım:

```c
long x = 9, kare;
__asm__ ("imulq %[v], %[v]"      // v = v * v
         : [v]"=r"(kare)         // CIKTI: bir register'a, sonra kare'ye
         : "0"(x));              // GIRDI: ayni register (0 = ilk ciktiyla ayni)
```

```
inline: kare=81 fark=7
```

Biçim: `__asm__ ("komutlar" : çıktılar : girdiler : bozulanlar)`. **Kısıtlar** (constraints) derleyiciye her işleneni nereye koyacağını söyler:

- `"=r"(kare)`: çıktı (`=`) bir register'a (`r`) konur, sonra `kare`'ye yazılır.
- `"0"(x)`: girdi, 0 numaralı çıktıyla **aynı** register'da (imul hedefi hem girdi hem çıktı).
- `%[v]`: adlandırılmış işlenen (okunaklılık için).

Dördüncü alan (bozulanlar, clobbers) derleyiciye assembly'nin hangi register/belleği ezdiğini söyler (Ders 6'da bayrakları okurken `"cc"` ile bayrakların bozulduğunu belirtmiştik). Yanlış kısıt = derleyici yanlış register varsayar = sessiz hatalar; inline assembly güçlü ama hataya açık.

Inline assembly ne zaman? Bir C karşılığı olmayan tek bir özel komut gerektiğinde (özel CPU komutları, atomik işlemler, Ders 7.29'daki SIMD'in bazı halleri). Genel kod için **kaçınılır**: derleyicinin optimizasyonunu (Ders 7.15) engeller, taşınabilir değildir (her ISA farklı), ve yanlış yazmak kolaydır.

---

## 5. Ne zaman ve neden (ve neden olmasın)

Elle assembly yazmanın meşru sebepleri azdır ama gerçektir:

- **Derleyicinin erişemediği komutlar**: özel donanım komutları, SIMD'in el ayarı (Faz 11), kriptografik komutlar (Ders 6.24'teki `pclmulqdq`).
- **İşletim sistemi / çekirdek**: bağlam değiştirme, kesme işleyiciler (Ders 7.28), `_start` (Ders 7.18) — C'nin ifade edemediği şeyler.
- **Son damla performans**: çok nadir; derleyici neredeyse her zaman insandan iyi assembly üretir.

Riskleri büyük: elle yazılan assembly taşınabilir değil (x86-64 kodu ARM'da çalışmaz, Ders 7.1), bakımı zor, ve ABI'ye ya da kısıtlara uymazsan **sessizce** bozulur (yanlış register, bozulan callee-saved register, hizalama ihlali). Modern kuralı: **önce C yaz, ölç (Faz 11), gerçekten gerekiyorsa ve sadece darboğazda assembly'ye in.** Bu fazın amacı assembly **yazmak** değil, onu **okuyup anlamak** — derleyici ne üretiyor, neden, ve doğru mu.

---

## Alıştırmalar

**1** – `long topla3(long a, long b, long c)` fonksiyonunu GAS ile yaz (`a + b + c`). Argümanlar hangi register'larda (Ders 7.10)? C'den çağırıp doğrula.

**2** – Aynı `topla3`'ü NASM ile yaz. İki sözdizimi arasındaki farkları (hedef yönü, `%`/`$`) satır satır göster. İkisi de aynı sonucu mu veriyor?

**3** – `.globl kare` satırını sil ve linklemeyi dene. Hangi hatayı alıyorsun, hangi aşamada (assemble mi link mi)? (Ders 2.11'deki "undefined reference".)

**4** – Inline assembly ile `x`'i 3 ile çarpan bir ifade yaz (`lea` kullanarak, Ders 7.7: `leaq (%rax,%rax,2), %rax`). Kısıtları doğru yaz; derleyici çıktısını `-S` ile kontrol et.

**5** – `kare` fonksiyonunu ABI'yi **ihlal edecek** şekilde yaz: sonucu `rax` yerine `rbx`'e koy. C'den çağırınca ne olur, ve neden? (Ders 7.10: `rbx` callee-saved, dönüş değeri değil.) Bu, "sözleşmeye uymazsan sessizce bozulur" dersini gösteriyor.

<details>
<summary>Cevaplar</summary>

**1** –

```
        .globl  topla3
topla3: leaq    (%rdi,%rsi), %rax     # rax = a + b
        addq    %rdx, %rax            # rax = a + b + c
        ret
        .section .note.GNU-stack,"",@progbits
```

`a` = `rdi`, `b` = `rsi`, `c` = `rdx` (ilk üç argüman, Ders 7.10). `leaq (%rdi,%rsi), %rax` ile `a+b` (Ders 7.7'deki lea), sonra `+c`. Sonuç `rax`. `topla3(1,2,3)` → 6.

**2** –

```
        global  topla3
topla3: lea     rax, [rdi + rsi]     ; rax = a + b   (hedef solda)
        add     rax, rdx             ; rax += c
        ret
```

Farklar: `lea rax, [rdi+rsi]` (Intel: hedef sol, bellek `[]` ile) vs GAS `leaq (%rdi,%rsi), %rax` (hedef sağ, `()` ve `%`); `add rax, rdx` vs `addq %rdx, %rax`. Aynı makine kodu, aynı sonuç (6).

**3** – `.globl` silinince assemble başarılı (assembler `kare:`'yi yerel sembol yapar) ama **link** aşamasında `undefined reference to 'kare'` hatası: linker, `main.o`'daki `call kare`'yi bağlayacak global bir `kare` sembolü bulamıyor (Ders 2.11, 7.17). Hata linker'dan gelir, derleyiciden değil; sembol dışa açılmadığı için görünmez.

**4** –

```c
long x = 7, r;
__asm__ ("leaq (%[v],%[v],2), %[o]" : [o]"=r"(r) : [v]"r"(x));
// r = x + x*2 = 3x = 21
```

`-S` ile bakınca `leaq (%reg,%reg,2), %reg` görünür. `"=r"` çıktı register'ı, `"r"` girdi register'ı; `lea` girdiyi ezmediği için ayrı register'lar olabilir (imul örneğindeki `"0"` kısıtı burada gerekmez).

**5** – `kare` sonucu `rbx`'e koyarsa: C `call kare`'den sonra sonucu `rax`'ten okur (ABI, Ders 7.10), ama `kare` oraya bir şey koymadı → `rax`'te çöp, **yanlış sonuç**. Dahası `rbx` callee-saved; `kare` onu kaydetmeden ezdi, yani çağıranın `rbx`'teki değeri de bozuldu → başka yerlerde gizli hatalar. Program çöker ya da rastgele yanlış çalışır, hiçbir uyarı olmadan. İşte ABI'nin "sözleşme" olmasının anlamı: iki taraf da harfiyen uymazsa, derleyici hiçbir hata vermez ama program sessizce bozulur. Assembly yazmanın en büyük riski bu.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.8.3 ve ekler: assembly ile C'yi birleştirmek.
- GCC belgeleri, "Extended Asm" (gcc.gnu.org): inline assembly, işlenenler, kısıtlar, clobbers.
- NASM belgeleri (nasm.us/doc): Intel sözdizimi ve ELF çıktısı.
- Ders 2.11 (çok dosyalı program ve Make): ayrı derleme ve linkleme.

**Sıradaki ders:** Tampon taşması saldırısının anatomisi. Dönüş adresinin üzerine yazılması, stack canary, NX, ASLR — savunma odaklı.
