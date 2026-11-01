---
title: "7.1 Komut kümesi mimarisi (ISA)"
description: "ISA ile mikromimari arasındaki fark; donanım ile yazılım arasındaki sözleşme; CISC ve RISC felsefeleri; x86-64, ARM/AArch64 ve RISC-V'nin karşılaştırması; sabit ve değişken komut uzunluğu, register sayısı, bellek erişim modeli; aynı C fonksiyonunu üç mimariye derleyip assembly çıktılarını yan yana okumak; neden bu fazda RISC-V ve x86-64 seçildiği."
gereksinimler: [gcc]
gereksinimNotu: "clang zaten kurulu; bu fazda aynı kodu ikinci bir derleyiciyle karşılaştırmak için gcc'yi de kuruyoruz."
---

Faz 2'den beri C yazıyoruz; Faz 3'te `int`'in bitlerine, Faz 4'te belleğe, Faz 5'te tek tek bitlere indik. Ama hep bir kutu kapalı kaldı: C kodu çalıştığında işlemci **tam olarak ne yapıyor**? Ders 0'da işlemciyi mantık kapılarından kurulmuş bir makine olarak gördük; Ders 2.7'de stack frame'lerden, Ders 2.6'da LLDB'yle hata ayıklamaktan söz ettik ama hiç makine komutu okumadık.

Bu faz o kutuyu açıyor. Sonunda, bir C fonksiyonunun hangi makine komutlarına dönüştüğünü okuyabilecek ve basit fonksiyonları elle assembly'de yazabileceksin. Derleyicinin arka yüzü (Faz 16'dan itibaren kod üreteceğimiz yer) bu bilgi olmadan anlaşılamaz. İlk ders, konuşacağımız dilin kendisini tanımlıyor: **komut kümesi mimarisi**.

---

## 1. ISA: donanım ile yazılım arasındaki sözleşme

Bir işlemcinin **komut kümesi mimarisi** (Instruction Set Architecture, ISA), yazılımın donanımdan görebildiği her şeydir:

- Hangi **komutlar** var (`add`, `load`, `jump`, ...) ve bitlerle nasıl kodlanırlar
- Kaç tane **register** var, ne genişlikte
- Belleğe nasıl erişilir, adresler nasıl hesaplanır
- Komutlar hangi durum bitlerini (bayrakları) etkiler

ISA bir **sözleşme**. Derleyici (ya da elle assembly yazan insan) sözleşmenin bir tarafında; sözleşmeye uyan her makine kodunu üretebilir. İşlemci üreticisi öbür tarafında; sözleşmeye uyan her kodu doğru çalıştırmak zorunda. Bir sözleşme olduğu için 1978'de yazılmış x86 makine kodu bugünün işlemcisinde hâlâ çalışıyor, ve bir Linux dağıtımının derlenmiş ikili dosyaları milyonlarca farklı bilgisayarda çalışıyor.

**Mikromimari** (microarchitecture) ise sözleşmenin **nasıl** yerine getirildiği: kaç çevrimde çalışır, kaç komut aynı anda yürütülür, cache ne kadar büyük, boru hattı kaç aşamalı. Aynı ISA'yı uygulayan iki işlemci (örneğin bir Intel ve bir AMD x86-64 çipi, ya da aynı ailenin yavaş ve hızlı modelleri) tamamen farklı mikromimariye sahip olabilir; ikisi de aynı makine kodunu çalıştırır, farklı hızlarda. Bu fazın ilk yarısı (bu ders–7.18) çoğunlukla ISA'yı; ikinci yarısı (7.19–7.29) mikromimariyi konu alıyor.

Ayrım şuna benziyor: ISA, bir fonksiyonun **arayüzü** (ne alır, ne döndürür); mikromimari, **gövdesi** (bunu nasıl yapar). Ders 4.9'daki "arayüz ile uygulamanın ayrılması" fikri, donanım ölçeğinde.

---

## 2. İki felsefe: CISC ve RISC

1970'lerde bellek pahalı ve derleyiciler zayıftı; insanlar sık sık elle assembly yazıyordu. O dönemin tasarımı **CISC** (Complex Instruction Set Computer): tek bir komut karmaşık işler yapsın, program kısa olsun. Bir komut hem bellekten okuyup hem hesap yapıp hem geri yazabilir; komutlar farklı uzunluklarda olur. **x86** bunun en yaygın örneği.

1980'lerde ölçümler şunu gösterdi: derleyiciler karmaşık komutların çoğunu zaten kullanmıyordu, ve basit komutları hızlandırmak daha kolaydı. **RISC** (Reduced Instruction Set Computer) felsefesi doğdu: az sayıda, basit, sabit uzunlukta komut; bellek erişimi sadece ayrı `load`/`store` komutlarıyla (geri kalan her şey register'larda). **ARM**, **MIPS**, **RISC-V** bu ailede.

| | CISC (x86-64) | RISC (AArch64, RISC-V) |
| --- | --- | --- |
| Komut uzunluğu | değişken (1–15 byte) | sabit (4 byte; RISC-V'de 2 ya da 4) |
| Bellek erişimi | birçok komut belleğe erişebilir | sadece `load`/`store` |
| Komut sayısı | çok (binlerce, uzantılarla) | az (temel RISC-V: ~50) |
| Register sayısı | 16 genel amaçlı | 31 (AArch64), 32 (RISC-V) |
| Kodlamayı çözmek | zor (önce uzunluğu bulmalısın) | kolay (hep aynı yerde) |

Bugün ayrım bulanıklaştı: modern x86-64 işlemcileri içeride CISC komutlarını küçük RISC benzeri "mikro-işlemlere" (µops) çeviriyor (Ders 7.23). Ama ISA düzeyinde, yani **okuyacağımız assembly** düzeyinde, fark hâlâ belirgin.

---

## 3. Üç ISA

Bu fazda üç mimariyi göreceğiz, her biri bir sebep için:

- **RISC-V**: 2010'da Berkeley'de, bir ders aracı ve açık standart olarak tasarlandı. Sade, düzenli, telif ücreti yok. Derleyici öğretmek için ideal; assembly'yi onunla öğreneceğiz (7.3–7.6). Bugün gömülü sistemlerden sunuculara yayılıyor.
- **x86-64**: masaüstü ve sunucu dünyasının baskın mimarisi (Intel ve AMD). Yaygınlığı yüzünden okumayı bilmek şart; godbolt'ta ve gerçek programlarda sürekli karşına çıkacak (7.7–7.11). İşaretli/işaretsiz farkının, taşmanın (Faz 3) donanımdaki karşılığını burada göreceğiz.
- **AArch64** (64-bit ARM): telefonların ve Apple Silicon Mac'lerin mimarisi. Ayrı bir bölüm ayırmıyoruz ama senin makinen muhtemelen bu, ve karşılaştırmalarda çıkacak.

Faz 2'den beri **clang** kullandık. Bu fazda yanına **gcc**'yi kuruyoruz (bu dersin gereksinim kutusuna bak). İki derleyici aynı C kodundan çoğu zaman farklı ama eşdeğer assembly üretir; ikisini karşılaştırmak, hangi seçimlerin **dilin** gereği, hangilerinin derleyicinin **tercihi** olduğunu ayırt etmeyi öğretir.

Bir not: bu bölümlerin çoğu, herhangi bir makinede çalışan **çapraz derleme** (cross-compilation) ile yapılabiliyor; `clang --target=...` ile ARM işlemcili bir Mac'te bile x86-64 ya da RISC-V assembly üretebilirsin. Çalıştırmak için ise bir simülatör (RISC-V'de RARS, 7.4) ya da öykünücü (QEMU) gerekir; onları ait oldukları derslerde kuracağız.

---

## 4. Aynı fonksiyon, üç dil

Soyut konuşmayı bırakıp bir örneğe bakalım. Ders 4.2'deki dizi toplamı:

```c
long sum(const long *a, long n) {
    long s = 0;
    for (long i = 0; i < n; i++) s += a[i];
    return s;
}
```

Bunu üç mimariye derleyelim. Komutu şimdilik ezberlemene gerek yok; amaç **biçimleri** karşılaştırmak. (Çapraz derleme: `clang --target=<mimari> -O1 -c sum.c`, sonra `llvm-objdump -d`.)

**x86-64:**

```
sum:
    xorl   %eax, %eax              # s = 0 (donus degeri eax/rax'te)
    testq  %rsi, %rsi              # n == 0 mi?
    jle    .son                    # n <= 0 ise donguye girme
    xorl   %ecx, %ecx              # i = 0
.dongu:
    addq   (%rdi,%rcx,8), %rax     # s += a[i]  -- TEK komutta: adres hesabi + bellek okuma + toplama
    incq   %rcx                    # i++
    cmpq   %rcx, %rsi              # i, n'yi gecti mi?
    jne    .dongu
.son:
    retq
```

**AArch64:**

```
sum:
    cmp    x1, #0x1                # n < 1 mi?
    b.lt   .sifir
    mov    x8, xzr                 # s = 0
.dongu:
    ldr    x9, [x0], #0x8          # x9 = *a; sonra a += 8  (ayri LOAD komutu)
    subs   x1, x1, #0x1            # n--  (ve bayraklari ayarla)
    add    x8, x9, x8              # s += x9
    b.ne   .dongu                  # n != 0 ise devam
    mov    x0, x8                  # donus degerini x0'a
    ret
.sifir:
    mov    x8, xzr
    mov    x0, x8
    ret
```

**RISC-V (rv64):**

```
sum:
    li     a2, 0                   # s = 0
    blez   a1, .son                # n <= 0 ise atla
    slli   a1, a1, 3               # n = n * 8  (eleman boyutu)
    add    a1, a0, a1              # a1 = dizinin sonu (a + 8n)
.dongu:
    ld     a3, 0(a0)               # a3 = *a      (ayri LOAD komutu)
    addi   a0, a0, 8               # a += 8
    add    a2, a3, a2              # s += a3
    bne    a0, a1, .dongu          # a != son ise devam
    mv     a0, a2                  # donus degeri a0'a
    ret
```

Üç çıktı aynı işi yapıyor ama felsefe farkı gözle görülür:

- **x86-64'te** `addq (%rdi,%rcx,8), %rax` tek bir komut: `%rdi + %rcx*8` adresini hesaplıyor, oradaki değeri okuyor ve `%rax`'a ekliyor. CISC'in "bir komut çok iş" anlayışı. Bu yüzden döngü gövdesi daha az komut.
- **RISC'lerde** aynı iş iki komut: önce `ld` ile bellekten register'a yükle, sonra `add` ile topla. "Bellek erişimi ayrı, hesap ayrı" kuralı. RISC-V bir adım daha ileri gidip bellekte adres yürütmek yerine pointer'ı doğrudan ilerletiyor (`addi a0, a0, 8`).
- **Adresleme**: x86-64'ün `(%rdi,%rcx,8)` biçimi (taban + indeks × ölçek) tek komutta adres hesaplıyor; buna "ölçekli indeksli adresleme" denir (Ders 7.7). RISC-V'de böyle bir şey yok; çarpmayı (`slli`, 8 = $2^3$ ile sola kaydırma, Ders 5.1) ayrı yapmak gerekiyor.

Kod boyutları da farkı gösteriyor: x86-64 fonksiyonu 29 byte (değişken uzunluklu, kompakt), AArch64 48 byte (her komut tam 4 byte), RISC-V 40 byte. Aynı program, farklı uzunlukta makine kodu.

İkisi de "doğru". Hangisinin daha hızlı olduğu komut sayısına değil, mikromimariye bağlı (Faz 7'nin ikinci yarısı), ve ölçmeden söylenemez (Faz 11). Şimdilik önemli olan: **yüksek seviyeli bir döngü, her mimaride tanınabilir bir makine kodu desenine dönüşüyor**, ve bu deseni okumayı öğreneceğiz.

---

## Alıştırmalar

**1** – CISC ve RISC arasındaki en temel fark nedir? "Register sayısı" mı yoksa "bellek erişiminin ayrı load/store komutlarıyla yapılması" mı daha belirleyici? Nedenini açıkla.

**2** – ISA ile mikromimari ayrımını kendi cümlelerinle anlat. Şunlardan hangisi ISA'nın, hangisi mikromimarinin parçası? (a) `add` komutunun var olması (b) toplama işleminin 1 çevrimde bitmesi (c) 16 register olması (d) L1 cache'in 32 KB olması (e) `%rax`'ın 64 bit olması.

**3** – Bölüm 4'teki üç çıktıda, döngü gövdesindeki **bellek okuma** komutunu her mimaride bul. x86-64'te neden ayrı bir okuma komutu yok?

**4** – `sum`'u kendi makinende derle: `clang -O1 -S sum.c -o sum.s` ile yerel assembly'yi (muhtemelen AArch64 ya da x86-64) üret ve oku. Sonra `clang --target=riscv64-linux-gnu -O1 -S sum.c` ile RISC-V üret. İki çıktıyı karşılaştır. (gcc kuruluysa `gcc -O1 -S` ile aynısını dene; clang'inkinden farklı mı?)

**5** – Neden açık bir ISA (RISC-V) olması önemli? Bir şirketin sahip olduğu kapalı bir ISA (x86, ARM) ile açık bir ISA arasında, yeni bir işlemci üretmek isteyen biri için ne fark var?

<details>
<summary>Cevaplar</summary>

**1** – Daha belirleyici olan **bellek erişiminin ayrılması** (load/store mimarisi). Register sayısı bir derece meselesi (x86-64 de 16'ya çıktı), ama "sadece load/store belleğe erişir" kuralı RISC'in tüm tasarımını belirliyor: komutlar sabit uzunlukta olabiliyor (çünkü karmaşık bellek adresleme alanı gerekmiyor), boru hattı düzenli oluyor (Ders 7.20), her komut benzer sürede bitiyor. x86-64'teki `addq (%rdi,%rcx,8), %rax` gibi "oku-hesapla-yaz" bir komut RISC'te ilke olarak yasak.

**2** – ISA = yazılımın gördüğü sözleşme (hangi komutlar, kaç register, ne genişlikte); mikromimari = o sözleşmenin donanımda nasıl gerçeklendiği (hız, boru hattı, cache). (a) ISA. (b) mikromimari (aynı `add` bir çipte 1, başka çipte daha fazla çevrim alabilir). (c) ISA. (d) mikromimari. (e) ISA.

**3** – x86-64: `addq (%rdi,%rcx,8), %rax` — okuma, `add`'in içinde gizli. AArch64: `ldr x9, [x0], #0x8`. RISC-V: `ld a3, 0(a0)`. x86-64'te ayrı okuma yok çünkü CISC bir komutun hem belleğe erişip hem hesap yapmasına izin veriyor; derleyici bu "birleşik" komutu kullanarak döngüyü kısaltmış.

**4** – Yerel çıktı muhtemelen AArch64 (Apple Silicon / çoğu yeni makine) ya da x86-64. RISC-V çıktısı Bölüm 4'tekine benzer. clang ve gcc çıktıları genellikle farklı komut sırası, farklı register seçimi gösterir ama aynı işi yapar; bazen biri döngüyü "açar" (unroll) ya da vektörleştirir, öbürü etmez. Farklar derleyicinin tercihleri; ikisi de sözleşmeye (ISA) uyuyor.

**5** – Açık ISA'da (RISC-V) herkes telif ücreti ödemeden uyumlu işlemci tasarlayıp üretebilir; standart herkese açık. Kapalı ISA'da (x86: Intel/AMD; ARM: ARM Holdings) işlemci yapmak için lisans almak, ücret ödemek, bazen hiç izin alamamak söz konusu. Açıklık, küçük şirketlerin ve üniversitelerin kendi çiplerini yapabilmesi, ve bu fazın bir ders aracı olarak RISC-V'yi seçebilmesi demek — standardı okumak, kullanmak ve değiştirmek serbest.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design, RISC-V Edition* (2. baskı), Bölüm 1–2: ISA kavramı, RISC-V'ye giriş.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3'ün girişi: ISA ile makine kodu.
- John Hennessy & David Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Ek A: ISA tasarım ilkeleri, CISC ve RISC tarihi.
- RISC-V International, *The RISC-V Instruction Set Manual, Volume I: Unprivileged ISA* (ücretsiz): standardın kendisi.

**Sıradaki ders:** Basit bir CPU tasarımı. Mantık kapısından ALU'ya ve register'a, Nand2Tetris'in Hack makinesiyle fetch–decode–execute döngüsü.
