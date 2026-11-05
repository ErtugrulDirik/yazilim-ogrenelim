---
title: "7.30 Faz projesi: RISC-V emülatörü"
description: "Fazın bütün parçalarını birleştiren proje: C ile ~200 satırlık bir RV32I emülatörü (bellek, 32 register, PC, getir–çöz–yürüt döngüsü, I/S/B/U/J immediate'ları, 37 komut, write ve exit sistem çağrıları); RISC-V çapraz derleyicisiyle libc'siz bir C programını derleyip (kendi _start'ımız, ecall ile sistem çağrıları, çarpma ve bölme olmadan sayı yazdırma) düz ikili dosyaya çevirmek ve emülatörde çalıştırmak; M uzantısını eklemek."
gereksinimler: [gcc]
gereksinimNotu: "Misafir programı derlemek için bir RISC-V çapraz derleyicisi gerekiyor: Ubuntu/Debian'da `sudo apt install gcc-riscv64-linux-gnu binutils-riscv64-linux-gnu`. Emülatörün kendisi her C derleyicisiyle (macOS'ta clang dahil) derlenir."
---

Bu fazın 29 dersi bir işlemcinin her katmanını tek tek açtı: Ders 7.2'de oyuncak bir CPU, 7.3'te komut kodlaması, 7.4–7.6'da RISC-V assembly, 7.16–7.18'de nesne dosyası, bağlayıcı ve `_start`, 7.19'da veri yolu, 7.28'de sistem çağrısı trap'i. Faz projesi bunları tek bir programda birleştiriyor: gerçek bir komut kümesinin, RV32I'nın, tamamını çalıştıran bir **emülatör**. Ve onu oyuncak programlarla değil, **gerçek bir C derleyicisinin** ürettiği makine koduyla deneyeceğiz. Emülatör çalıştığında, gcc'nin RISC-V için ürettiği bir programı, RISC-V işlemcisi olmayan bir makinede (Mac, x86 PC) kendi yazdığın 200 satırlık C ile çalıştırmış olacaksın.

Bu, Faz 15–20'deki derleyici çalışmalarının da bir hazırlığı: kendi derleyicimiz RISC-V kodu ürettiğinde, onu çalıştıracak (ve hata ayıklayacak) bir makinemiz olacak.

---

## 1. Plan

```
 misafir.c  --riscv64-linux-gnu-gcc-->  misafir.elf  --objcopy-->  misafir.bin  --rv32emu-->  cikti
 baslat.s       (-march=rv32i)             (ELF, Ders 7.16)            (duz bayt)    (bu ders)
```

İki parça yazacağız:

1. **Emülatör** (`rv32emu.c`): 64 KB bellek, 32 register, PC. Bir dosyayı belleğin 0 adresine yükler, 0'dan çalıştırmaya başlar, `ecall`'da `write` ve `exit` sistem çağrılarını sunar. Ev sahibi (host) makinede yerel olarak derlenir.
2. **Misafir program** (`misafir.c` + `baslat.s`): RISC-V için derlenir. libc yok (Ders 7.18), ekrana yazmak için kendi `ecall`'unu yapıyor.

Emülatör, ELF ayrıştırmak yerine **düz ikili** (flat binary) yükleyecek: `objcopy -O binary` ELF'teki `.text` ve `.rodata` bölümlerini adresleriyle, başlıksız, tek bir bayt dizisine döküyor. `.bss`'i dökmüyor; emülatörün belleği zaten sıfır başladığı için gerek yok (Ders 7.16'daki NOBITS).

---

## 2. Emülatör

Ders 7.19'daki veri yolu simülasyonundan farkı: orada her komut aynı satırlardan geçiyordu ve sadece 6 komut vardı. Burada amaç donanımı modellemek değil, ISA'yı **doğru ve tam** çalıştırmak; o yüzden yapı Ders 7.2'deki gibi bir `switch`. RV32I'nın bütün kullanıcı modu komutları (`fence` boş, `ecall` sistem çağrısı; `ebreak` ve CSR komutları desteklenmiyor):

```c
/* rv32emu: kucuk bir RV32I emulatoru. Duz (flat) ikili dosyayi 0 adresine yukler. */
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#define BELLEK (64 * 1024)

static uint8_t mem[BELLEK];
static uint32_t x[32], pc;
static long komut_sayisi;

static void hata(const char *m) {
    fprintf(stderr, "emulator hatasi: %s (pc=0x%08x)\n", m, pc);
    exit(2);
}

/* --- bellek erisimi (little endian) --- */
static uint32_t oku(uint32_t a, int n) {
    if (a + n > BELLEK) hata("bellek disi okuma");
    uint32_t v = 0;
    for (int i = 0; i < n; i++) v |= (uint32_t)mem[a + i] << (8 * i);
    return v;
}
static void yaz(uint32_t a, uint32_t v, int n) {
    if (a + n > BELLEK) hata("bellek disi yazma");
    for (int i = 0; i < n; i++) mem[a + i] = (uint8_t)(v >> (8 * i));
}

/* --- immediate'lar (Ders 7.3'teki formatlar) --- */
static int32_t imm_i(uint32_t k) { return (int32_t)k >> 20; }
static int32_t imm_s(uint32_t k) { return ((int32_t)(k & 0xfe000000) >> 20) | ((k >> 7) & 0x1f); }
static int32_t imm_b(uint32_t k) {
    return ((int32_t)(k & 0x80000000) >> 19) | ((k & 0x80) << 4)
         | ((k >> 20) & 0x7e0) | ((k >> 7) & 0x1e);
}
static int32_t imm_u(uint32_t k) { return (int32_t)(k & 0xfffff000); }
static int32_t imm_j(uint32_t k) {
    return ((int32_t)(k & 0x80000000) >> 11) | (k & 0xff000)
         | ((k >> 9) & 0x800) | ((k >> 20) & 0x7fe);
}

/* --- sistem cagrilari: Linux numaralari (64 write, 93 exit) --- */
static int ecall(void) {
    uint32_t no = x[17], a0 = x[10], a1 = x[11], a2 = x[12];   /* a7, a0, a1, a2 */
    switch (no) {
    case 64:                                                    /* write(fd, buf, n) */
        if (a1 + a2 > BELLEK) hata("write: tampon bellek disi");
        fwrite(&mem[a1], 1, a2, a0 == 2 ? stderr : stdout);
        x[10] = a2;
        return 0;
    case 93:                                                    /* exit(kod) */
        return 1;
    }
    hata("bilinmeyen sistem cagrisi");
    return 1;
}

/* Bir komut: getir, coz, yurut. Program bittiyse 1 dondurur. */
static int adim(void) {
    uint32_t k = oku(pc, 4);
    uint32_t op = k & 0x7f, rd = (k >> 7) & 31, f3 = (k >> 12) & 7,
             rs1 = (k >> 15) & 31, rs2 = (k >> 20) & 31, f7 = k >> 25;
    uint32_t a = x[rs1], b = x[rs2], sonraki = pc + 4, sonuc = 0;
    int rd_yaz = 1;
    komut_sayisi++;

    switch (op) {
    case 0x37: sonuc = imm_u(k); break;                         /* lui   */
    case 0x17: sonuc = pc + imm_u(k); break;                    /* auipc */
    case 0x6f: sonuc = pc + 4; sonraki = pc + imm_j(k); break;  /* jal   */
    case 0x67: sonuc = pc + 4; sonraki = (a + imm_i(k)) & ~1u; break; /* jalr */
    case 0x63: {                                                /* dallanmalar */
        int al;
        switch (f3) {
        case 0: al = a == b; break;                             /* beq  */
        case 1: al = a != b; break;                             /* bne  */
        case 4: al = (int32_t)a <  (int32_t)b; break;           /* blt  */
        case 5: al = (int32_t)a >= (int32_t)b; break;           /* bge  */
        case 6: al = a <  b; break;                             /* bltu */
        case 7: al = a >= b; break;                             /* bgeu */
        default: hata("gecersiz dal"); al = 0;
        }
        if (al) sonraki = pc + imm_b(k);
        rd_yaz = 0;
        break;
    }
    case 0x03: {                                                /* yuklemeler */
        uint32_t adr = a + imm_i(k);
        switch (f3) {
        case 0: sonuc = (int32_t)(int8_t)oku(adr, 1); break;    /* lb  */
        case 1: sonuc = (int32_t)(int16_t)oku(adr, 2); break;   /* lh  */
        case 2: sonuc = oku(adr, 4); break;                     /* lw  */
        case 4: sonuc = oku(adr, 1); break;                     /* lbu */
        case 5: sonuc = oku(adr, 2); break;                     /* lhu */
        default: hata("gecersiz yukleme");
        }
        break;
    }
    case 0x23: {                                                /* saklamalar */
        uint32_t adr = a + imm_s(k);
        if (f3 > 2) hata("gecersiz saklama");
        yaz(adr, b, 1 << f3);                                   /* sb, sh, sw */
        rd_yaz = 0;
        break;
    }
    case 0x13: {                                                /* immediate aritmetik */
        int32_t im = imm_i(k);
        uint32_t sh = rs2;                                      /* kaydirma miktari */
        switch (f3) {
        case 0: sonuc = a + im; break;                          /* addi  */
        case 2: sonuc = (int32_t)a < im; break;                 /* slti  */
        case 3: sonuc = a < (uint32_t)im; break;                /* sltiu */
        case 4: sonuc = a ^ im; break;                          /* xori  */
        case 6: sonuc = a | im; break;                          /* ori   */
        case 7: sonuc = a & im; break;                          /* andi  */
        case 1: sonuc = a << sh; break;                         /* slli  */
        case 5: sonuc = (f7 & 0x20) ? (uint32_t)((int32_t)a >> sh) : a >> sh; break; /* srai/srli */
        }
        break;
    }
    case 0x33: {                                                /* register aritmetik */
        if (f7 & ~0x20u) hata("M uzantisi yok (RV32I)");
        switch (f3) {
        case 0: sonuc = (f7 & 0x20) ? a - b : a + b; break;     /* sub/add */
        case 1: sonuc = a << (b & 31); break;                   /* sll  */
        case 2: sonuc = (int32_t)a < (int32_t)b; break;         /* slt  */
        case 3: sonuc = a < b; break;                           /* sltu */
        case 4: sonuc = a ^ b; break;                           /* xor  */
        case 5: sonuc = (f7 & 0x20) ? (uint32_t)((int32_t)a >> (b & 31)) : a >> (b & 31); break;
        case 6: sonuc = a | b; break;                           /* or   */
        case 7: sonuc = a & b; break;                           /* and  */
        }
        break;
    }
    case 0x0f: rd_yaz = 0; break;                               /* fence: tek cekirdekte bos */
    case 0x73:                                                  /* ecall */
        if (k != 0x00000073) hata("ebreak/csr desteklenmiyor");
        rd_yaz = 0;
        if (ecall()) return 1;
        break;
    default:
        hata("gecersiz komut");
    }
    if (rd_yaz && rd != 0) x[rd] = sonuc;                       /* x0 hep 0 kalir */
    pc = sonraki;
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) { fprintf(stderr, "kullanim: %s program.bin\n", argv[0]); return 1; }
    FILE *f = fopen(argv[1], "rb");
    if (!f) { perror(argv[1]); return 1; }
    size_t n = fread(mem, 1, BELLEK, f);
    fclose(f);
    fprintf(stderr, "[%zu bayt yuklendi]\n", n);

    pc = 0;
    while (!adim())
        if (komut_sayisi > 100000000) hata("komut siniri asildi");
    fflush(stdout);
    fprintf(stderr, "[program %ld komutta bitti, cikis kodu %u]\n", komut_sayisi, x[10]);
    return (int)x[10];
}
```

Ders 7.3'ten tanıdık noktalar:

- **Immediate'lar.** Beş format, beş fonksiyon. `(int32_t)k >> 20` aritmetik sağa kaydırma: en üst bit (işaret) çoğaltılıyor, işaret genişletme bedava (Ders 5.1). B ve J formatlarındaki dağınık bitler (Ders 7.3'teki "neden bu kadar karışık?" sorusu) donanımda sadece tel; yazılımda maske ve kaydırma.
- **x0.** `if (rd_yaz && rd != 0)`: x0'a yazma sessizce yok sayılıyor. Hiç yazılmadığı için `x[0]` hep 0.
- **İşaretli ve işaretsiz.** `blt` / `bltu`, `slt` / `sltu`, `srai` / `srli`, `lb` / `lbu`: aynı bitler, iki yorum (Ders 3.3). C'de bu ayrımı tip dönüşümleriyle (`(int32_t)a`) yapıyoruz.
- **Kaydırma miktarı** `b & 31`: RISC-V register'la kaydırmada sadece alt 5 biti kullanır. C'de 32 veya daha fazla kaydırmak UB olduğu için (Ders 2.12) maske şart, sadece "RISC-V öyle istiyor" diye değil.
- **`jalr`'da `& ~1u`**: hedef adresin en alt biti sıfırlanıyor (belirtimin kuralı).
- **Sistem çağrıları.** Numaralar Linux'unkiler (64 = `write`, 93 = `exit`; Ders 7.28): aynı misafir program gerçek bir RISC-V Linux'ta da çalışabilir. Emülatör, Ders 7.28'deki çekirdek trap işleyicisinin rolünü oynuyor: `a7`'ye bakıp işi ev sahibi işletim sistemine (`fwrite`) devrediyor.
- **Bellek sınırı** kontrolü her erişimde: misafir programın hatası emülatörü çökertmesin, Ders 7.27'deki sayfa hatasının küçük bir karşılığı.

`M uzantisi yok` hatasına dikkat: RV32I'da çarpma ve bölme **yok**. `funct7 = 0x01` olan R komutları (`mul`, `div`, ...) "M" (multiply) uzantısında. Alıştırma 2'de ekliyoruz.

---

## 3. Misafir program

Giriş noktası, Ders 7.18'deki `_start`'ın RISC-V sürümü:

```asm
# Misafir programin giris noktasi: yigini kur, main'i cagir, exit ile cik
    .section .text.baslat
    .globl _start
_start:
    li   sp, 0x10000          # yigin 64 KB bellegin en ustunden baslar
    call main
    li   a7, 93               # sistem cagrisi 93: exit(a0)
    ecall
```

Yığın 64 KB'lık belleğin tepesinden başlıyor ve aşağı büyüyecek (Ders 7.6). `main` dönünce `a0`'daki dönüş değeri `exit`'in argümanı oluyor.

Program, C ile:

```c
/* Emulatorde calisacak program. RV32I: carpma/bolme komutu yok, libc yok. */
static long sistem(long no, long a0, long a1, long a2) {
    register long r_a0 __asm__("a0") = a0;
    register long r_a1 __asm__("a1") = a1;
    register long r_a2 __asm__("a2") = a2;
    register long r_a7 __asm__("a7") = no;
    __asm__ volatile ("ecall" : "+r"(r_a0) : "r"(r_a1), "r"(r_a2), "r"(r_a7) : "memory");
    return r_a0;
}

static void yaz(const char *s) {
    int n = 0;
    while (s[n]) n++;
    sistem(64, 1, (long)s, n);            /* 64: write(fd, buf, n) */
}

/* Bolme olmadan ondalik yazdirma: 10'un kuvvetlerini cikararak */
static void sayi_yaz(unsigned x) {
    static const unsigned kuvvet[] = { 1000000000, 100000000, 10000000, 1000000,
                                       100000, 10000, 1000, 100, 10, 1 };
    char buf[12]; int k = 0, basladi = 0;
    for (int i = 0; i < 10; i++) {
        char rakam = '0';
        while (x >= kuvvet[i]) { x -= kuvvet[i]; rakam++; }
        if (rakam != '0' || basladi || i == 9) { buf[k++] = rakam; basladi = 1; }
    }
    buf[k] = 0;
    yaz(buf);
}

static int asal_mi(unsigned n) {          /* bolme yok: eleme (sieve) kullan */
    static unsigned char bilesik[100];
    static int hazir = 0;
    if (!hazir) {
        for (unsigned i = 2; i < 100; i++)
            if (!bilesik[i])
                for (unsigned j = i + i; j < 100; j += i) bilesik[j] = 1;
        hazir = 1;
    }
    return n >= 2 && !bilesik[n];
}

int main(void) {
    yaz("RV32I emulatorunden merhaba!\n");

    unsigned a = 0, b = 1;
    yaz("fib: ");
    for (int i = 0; i < 15; i++) { sayi_yaz(a); yaz(" "); unsigned t = a + b; a = b; b = t; }
    yaz("\n");

    unsigned adet = 0;
    for (unsigned n = 0; n < 100; n++) adet += asal_mi(n);
    yaz("100'den kucuk asal sayisi: "); sayi_yaz(adet); yaz("\n");
    return 7;                             /* cikis kodu: emulator bildirir */
}
```

İki kısıt programı şekillendirdi:

- **libc yok.** `printf` yok; `sistem` fonksiyonu Ders 7.18'deki inline assembly'nin RISC-V hali. `register long r_a0 __asm__("a0")` gcc'ye "bu değişkeni tam olarak `a0`'da tut" diyor.
- **Çarpma ve bölme yok.** Bir sayıyı ondalık yazdırmak normalde `x % 10` ve `x / 10` ister (Ders 3.16'daki `itoa`). RV32I'da bölme komutu olmadığı için gcc onları libgcc'deki `__udivsi3` çağrılarına çevirirdi ve biz libgcc bağlamıyoruz. `sayi_yaz` bölme yerine 10'un kuvvetlerini **çıkarıyor**: Ders 5.13'teki "bölme = tekrarlı çıkarma" fikrinin en basit hali. Asal sayılar da bölmesiz, Eratosthenes eleği ile (Ders 6.17) bulunuyor; elek sadece toplama kullanıyor (`j += i`).

Derleme (Linux, RISC-V çapraz derleyiciyle):

```
$ riscv64-linux-gnu-gcc -march=rv32i -mabi=ilp32 -O1 -ffreestanding -nostdlib \
      -fno-pic -fno-unwind-tables -fno-asynchronous-unwind-tables -static \
      -Wl,-Ttext=0 -Wl,--no-relax -Wl,--build-id=none -Wl,-e,_start \
      -o misafir.elf baslat.s misafir.c
$ riscv64-linux-gnu-objcopy -O binary misafir.elf misafir.bin
$ ls -l misafir.bin
-rwxr-xr-x 1 root root 792 misafir.bin
```

Bayrakların her biri bu fazda bir derse karşılık geliyor:

| Bayrak | Neden | Ders |
| --- | --- | --- |
| `-march=rv32i -mabi=ilp32` | 32 bit, sadece temel komutlar, `int`/`long`/işaretçi 32 bit | 7.1, 7.4 |
| `-ffreestanding -nostdlib` | libc yok, `crt1.o` yok, kendi `_start`'ımız | 7.18 |
| `-fno-pic`, `-static` | Mutlak adresler, dinamik bağlayıcı yok | 7.17 |
| `-Wl,-Ttext=0` | `.text`'i 0 adresine koy (emülatör oradan başlıyor) | 7.17 |
| `-Wl,--no-relax` | Bağlayıcı `gp` göreli adreslemeye çevirmesin (`gp`'yi kurmuyoruz) | 7.17 |
| `-Wl,-e,_start` | Giriş noktası | 7.16 |
| `-fno-*unwind-tables`, `--build-id=none` | Gereksiz `.eh_frame` ve not bölümleri ikili dosyaya girmesin | 7.16 |

`objdump -h misafir.elf` ile bölümler: `.text` `0x0`–`0x2ac`, `.rodata` `0x2ac`–`0x318` (stringler ve `kuvvet` tablosu), `.sbss` ve `.bss` `0x1000`'de (`hazir` ve 100 baytlık `bilesik`). Dosya 792 bayt: 0x318 = 792, `.text` + `.rodata`, başka hiçbir şey. gcc'nin ürettiği 171 komutta en sık kullanılanlar `addi` (36), `li` (24, aslında `addi`), `mv` (16, o da `addi`), `lui` (12), `jalr` (10); ve `mul`/`div` hiç yok.

---

## 4. Çalıştırma

```
$ cc -O2 -Wall -Wextra rv32emu.c -o rv32emu
$ ./rv32emu misafir.bin
[792 bayt yuklendi]
RV32I emulatorunden merhaba!
fib: 0 1 1 2 3 5 8 13 21 34 55 89 144 233 377 
100'den kucuk asal sayisi: 25
[program 5507 komutta bitti, cikis kodu 7]
$ echo $?
7
```

gcc'nin RISC-V için ürettiği 5507 komut, Apple M2 (ya da x86) üzerinde, 200 satırlık bir C programının içinde çalıştı. Fibonacci dizisi doğru, 100'den küçük 25 asal var (2, 3, 5, ..., 97), ve `main`'in döndürdüğü 7 `exit` sistem çağrısından emülatörün çıkış koduna kadar taşındı.

Emülatör geçersiz bir komutla karşılaşınca ne yapıyor? `mul x4, x2, x3` (`0x02310233`) içeren 4 baytlık bir dosya:

```
$ printf '\x33\x02\x31\x02' > mul.bin
$ ./rv32emu mul.bin
[4 bayt yuklendi]
emulator hatasi: M uzantisi yok (RV32I) (pc=0x00000000)
```

Ders 7.28'deki geçersiz komut istisnasının (SIGILL) emülatördeki karşılığı.

---

## 5. Bu emülatör ne değil?

Ders 7.19–7.27'de öğrendiğimiz şeylerin çoğu burada **yok**, ve bu bilinçli:

- **Boru hattı, önbellek, dal tahmini, sırasız yürütme yok.** Emülatör ISA'yı (Ders 7.1'deki sözleşme) taklit ediyor, mikromimariyi değil. Programın **sonucu** gerçek bir işlemcideki ile aynı; **süresi** hakkında hiçbir şey söylemiyor. Bunlar mimari olarak görünmez olduğu için (Ders 7.23'teki kesin istisnalar), doğru çalışan bir program için fark etmez.
- **Sanal bellek, ayrıcalık seviyeleri yok.** Tek bir düz adres uzayı. Bir işletim sistemi çalıştırmak için S modu, `satp` ve Sv32 (Ders 7.27), trap ve CSR'ler (Ders 7.28) gerekirdi. QEMU ve Spike gibi tam emülatörler bunları yapıyor ve Linux çalıştırabiliyor.
- **Hızlı değil.** Her komut bir `switch`. Gerçek emülatörler (QEMU) misafir kodu ev sahibinin makine koduna **çeviriyor** (dinamik ikili çeviri, JIT); Apple'ın Rosetta 2'si x86-64 kodunu arm64'e aynı yolla çeviriyor. Faz 19–20'de kod üretimine geldiğimizde bu fikre döneceğiz.

---

## Alıştırmalar

**1** – Emülatöre `-t` seçeneği ekle: her komutta komut sayacını, PC'yi, komut sözcüğünü, `sp` ve `a0`'ı `stderr`'e yazsın. İlk 7 satırı Ders 7.4'teki bilgiyle yorumla.

**2** – M uzantısını ekle (`funct7 = 0x01`: `mul`, `mulh`, `mulhsu`, `mulhu`, `div`, `divu`, `rem`, `remu`). Sıfıra bölme ve `INT32_MIN / -1` taşması için RISC-V belirtiminin istediği sonuçları kullan (Ders 7.28, Alıştırma 1). Sonra `sayi_yaz`'ı `%` ve `/` ile yazıp `-march=rv32im` ile derleyerek test et.

**3** – Misafir programa `12!`'yi hesaplayan bir döngü ekle, ama `-march=rv32i` ile (çarpma yok). Derleyici ne yapar? Bağlama neden başarısız olur, ve bunu çarpmayı kendin (toplama ve kaydırma ile, Ders 5.13) yazarak nasıl çözersin?

**4** – Emülatöre komut türü başına sayaç ekle (yükleme, saklama, dal, ALU, ...) ve misafir programın profilini çıkar. Ders 7.21'deki tehlike modelinde bu programın CPI'si için kaba bir tahmin yap.

**5** – `misafir.bin`'i emülatöre verirken bir baytını değiştir (örneğin `printf '\x00' | dd of=misafir.bin bs=1 seek=0 conv=notrunc`). Emülatör ne der? Gerçek bir işlemci ne yapardı?

<details>
<summary>Cevaplar</summary>

**1** – `adim`'in başına `if (iz) fprintf(stderr, "%6ld  pc=%08x  %08x  sp=%08x a0=%08x\n", komut_sayisi, pc, k, x[2], x[10]);` ve `main`'de `-t` argümanını yakalamak yeter. Çıktının başı:

```
     1  pc=00000000  00010137  sp=00000000 a0=00000000
     2  pc=00000004  00000097  sp=00010000 a0=00000000
     3  pc=00000008  100080e7  sp=00010000 a0=00000000
     4  pc=00000104  fe010113  sp=00010000 a0=00000000
     5  pc=00000108  00112e23  sp=0000ffe0 a0=00000000
     6  pc=0000010c  00812c23  sp=0000ffe0 a0=00000000
     7  pc=00000110  00912a23  sp=0000ffe0 a0=00000000
```

(Register değerleri komut **çalışmadan önceki** hali.) 1: `lui sp, 0x10` (`li sp, 0x10000`'in tek komutluk hali), 2. satırda `sp` = `0x10000`. 2–3: `call main` = `auipc ra, 0` + `jalr ra, 256(ra)`, PC `0x104`'e (`main`) atlıyor. 4: `addi sp, sp, -32`, `main`'in prologu (Ders 7.6), 5. satırda `sp` = `0xffe0`. 5–7: `sw ra, 28(sp)`, `sw s0, 24(sp)`, `sw s1, 20(sp)`: dönüş adresi ve kaydedilen register'lar yığına. Ders 7.6'da elle yazdığımız fonksiyon çerçevesinin derleyici versiyonu.

**2** – R tipi `case 0x33`'ün başına, `funct7 == 0x01` ise ayrı bir `switch (f3)`: `mul` = `a * b` (alt 32 bit, işaretli/işaretsiz aynı); `mulh` = `((int64_t)(int32_t)a * (int32_t)b) >> 32`; `mulhu` = `((uint64_t)a * b) >> 32`; `mulhsu` = `((int64_t)(int32_t)a * (uint64_t)b) >> 32`; `div`: `b == 0` ise `0xffffffff`, `a == INT32_MIN && b == -1` ise `a` (C'de bu UB, Ders 3.8; RISC-V'de taşıp `INT32_MIN` döner), değilse `(int32_t)a / (int32_t)b`; `divu`: `b == 0` ise `0xffffffff`; `rem`: `b == 0` ise `a`, taşma durumunda 0; `remu`: `b == 0` ise `a`. Test programı (`f *= i` ile `12!`, ve `%`/`/` kullanan `sayi_yaz`) `-march=rv32im` ile derlenince gcc `mul`, `divu`, `remu` üretti:

```
$ ./rv32emu_m m.bin
[416 bayt yuklendi]
12! = 479001600
-7 / 2 = -3, -7 % 2 = -1
[program 473 komutta bitti, cikis kodu 0]
$ ./rv32emu m.bin
[416 bayt yuklendi]
emulator hatasi: M uzantisi yok (RV32I) (pc=0x000000e8)
```

Bölmeli `sayi_yaz` program boyutunu 792 bayttan 416 bayta ve komut sayısını yarıdan fazla düşürdü. M uzantısı olmayan emülatör ilk `mul`'da (`0xe8`) duruyor. `-7 / 2 = -3`: C ve RISC-V sıfıra doğru keser (Ders 3.7).

**3** – gcc, `-march=rv32i`'de `f *= i`'yi bir libgcc fonksiyonu çağrısına çevirir (`__mulsi3`). `-nostdlib` ile libgcc bağlanmadığı için `undefined reference to '__mulsi3'` (Ders 7.17'deki tanımsız sembol). Çözüm ya `-lgcc` eklemek (libgcc'nin rv32i/ilp32 sürümü kurulu ise), ya da `__mulsi3`'ü kendin tanımlamak: Ders 5.13'teki kaydır-ve-topla çarpması, `unsigned __mulsi3(unsigned a, unsigned b) { unsigned r = 0; while (b) { if (b & 1) r += a; a <<= 1; b >>= 1; } return r; }`. Bağlayıcı ismi bulur ve çağrıyı ona bağlar. Derleyicinin "yapamadığı" işlemleri bir kütüphaneye devretmesi, Ders 7.29'daki `sqrt` örneğinin tamsayı karşılığı.

**4** – `adim`'de `op`'a göre bir sayaç dizisi artır. Bu tür bir programda ALU komutları (`addi`, `add`, `lui`, ...) baskın; yükleme/saklamalar ve dallar daha az. Ders 7.21'in modeliyle: forwarding'li 5 aşamalı boru hattında her yükle-kullan çifti 1 kabarcık, her yanlış tahmin edilen dal 1–2 döngü. Yüklemelerin örneğin %15'i, dalların %20'si ve dalların yarısının yanlış tahmin edildiğini varsayarsan CPI ≈ $1 + 0.15 \times 0.5 + 0.20 \times 0.5 \times 2 \approx 1.3$. Bu bir tahmin; gerçek değer için emülatöre Ders 7.21'deki bağımlılık kontrolünü eklemek gerekir (bu da başlı başına güzel bir proje: emülatörü bir boru hattı simülatörüne çevirmek).

**5** – İlk komut `lui sp, 0x10` (`0x00010137`); ilk baytı `0x37` → `0x00` yaparsan komut `0x00010100` olur, opcode `0x00`: hiçbir RV32I komutu değil. Emülatör `emulator hatasi: gecersiz komut (pc=0x00000000)` der ve 2 koduyla çıkar. Gerçek bir RISC-V işlemcisi geçersiz komut istisnası (`mcause` = 2, Ders 7.28) üretir, `mtval`'e komut sözcüğünü yazar ve trap işleyicisine atlar; Linux sürece SIGILL gönderir. RISC-V'nin bilerek seçtiği bir özellik: tamamen sıfır olan komut sözcüğü (`0x00000000`) geçersiz tanımlı, böylece sıfırlanmış belleğe atlayan bir program hemen yakalanır.

</details>

---

## Faz 7'nin sonu

Bu faz C ile makine arasındaki her katmanı açtı. Şimdi bir C satırının yolculuğunu baştan sona izleyebilirsin: derleyici onu komutlara çeviriyor (7.1–7.15), assembler bit kalıplarına kodluyor (7.3), bağlayıcı adresleri dolduruyor (7.16–7.17), yükleyici belleğe eşliyor (7.18, 7.27); işlemci her komutu boru hattından geçiriyor (7.19–7.21), dalları tahmin ediyor (7.22), sırasız yürütüyor (7.23), verisini önbellek hiyerarşisinden getiriyor (7.24–7.26), olağandışı her durumda işletim sistemine kapı açıyor (7.28). Ve bütün bunların sözleşmesi olan ISA'yı kendi emülatörünle çalıştırabiliyorsun.

Faz 8 bu temelin üstüne veri yapılarını kuruyor. Ders 7.24–7.26'yı akılda tutarak: bir bağlı liste ile bir dizinin aynı büyük-O'ya rağmen neden 100 kat farklı hızda olabileceğini artık biliyorsun.

---

## Kaynaklar

- RISC-V Unprivileged ISA Specification, Bölüm 2 (RV32I) ve Bölüm 7 ("M" uzantısı): bütün komutların kesin tanımları; bu emülatör doğrudan oradan yazıldı.
- David Patterson & Andrew Waterman, *The RISC-V Reader: An Open Architecture Atlas* (2017): komut kartı ve tasarım gerekçeleri.
- Fabrice Bellard, "QEMU, a Fast and Portable Dynamic Translator" (USENIX ATC 2005).
- Spike, RISC-V'nin resmî referans emülatörü (github.com/riscv-software-src/riscv-isa-sim).
- Ben Eater, "Build an 8-bit computer" ve Nand2Tetris (Ders 7.2): emülatörün altındaki donanımı fiziksel olarak kurmak isteyenler için.

**Sıradaki ders:** Faz 8'e geçiyoruz: soyut veri tipi (ADT). Arayüz ile uygulamanın ayrılması, opak pointer, C'de kapsülleme.
