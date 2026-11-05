---
title: "7.28 Kesmeler ve istisnalar"
description: "İşlemcinin normal akışını kesen olaylar: senkron istisnalar (fault, trap, abort) ve asenkron kesmeler (zamanlayıcı, aygıt); kullanıcı ve çekirdek modu, ayrıcalıklı komutlar; trap'in donanımda adım adım işleyişi (RISC-V mcause/mepc/mtvec, x86-64 IDT); işletim sisteminin istisnaları sinyallere çevirmesi; x86-64 Linux ve arm64 macOS'ta aynı C programıyla NULL okuma, sıfıra bölme, geçersiz komut, zamanlayıcı ve sistem çağrısının karşılaştırılması; RISC-V'de sıfıra bölmenin neden istisna olmadığı."
gereksinimler: [rars]
---

Bu fazın son birkaç dersinde aynı kavram sürekli karşımıza çıktı ama hep "ileride" dedik: Ders 7.18'deki `syscall` komutu "çekirdek moduna geç"; Ders 7.27'deki sayfa hatası "kontrol işletim sistemine geçer"; Ders 7.23'teki ROB "kesin istisnalar için" sıralı tamamlıyordu; Ders 7.14'teki taşma bir `Segmentation fault` ile bitiyordu. Bu ders hepsinin ortak mekanizmasını anlatıyor: işlemcinin, o an çalıştırdığı programı bırakıp **işletim sistemindeki** bir koda atlaması. Faz 10'daki işletim sistemi programlamasının donanım temeli bu.

---

## 1. Kullanıcı modu ve çekirdek modu

İşlemci en az iki **ayrıcalık seviyesinde** çalışabilir:

- **Kullanıcı modu** (user mode): sıradan programlar. Sadece kendi adres uzayına (Ders 7.27) erişebilir; bazı komutları çalıştıramaz.
- **Çekirdek modu** (kernel / supervisor mode): işletim sistemi. Her şeye erişebilir.

Sadece çekirdek modunda çalışabilen **ayrıcalıklı komutlar** var: sayfa tablosu kökünü değiştirmek (RISC-V'de `satp` yazmak, x86-64'te `mov` ile `cr3`), kesmeleri kapatmak (`cli`), işlemciyi durdurmak (`hlt`, Ders 7.18'de `_start`'ın sonundaki), G/Ç aygıtlarıyla doğrudan konuşmak. Kullanıcı modunda bunlardan birini çalıştırmak bir istisna üretir. Yalıtım (Ders 7.27) bu sayede gerçek: bir program sayfa tablosunu değiştiremiyorsa kendi adres uzayından çıkamaz.

RISC-V üç seviye tanımlar: **U** (user), **S** (supervisor, işletim sistemi), **M** (machine, en ayrıcalıklı; açılış yazılımı). x86-64'te "halkalar" (ring 0 çekirdek, ring 3 kullanıcı). arm64'te istisna seviyeleri (EL0 kullanıcı, EL1 çekirdek, EL2 hipervizör).

Peki kullanıcı modundaki bir program çekirdek moduna nasıl geçer? Kendi başına geçemez; ancak bir **trap** ile, ve çekirdeğin önceden belirlediği **tek bir giriş noktasına**.

---

## 2. Olayların sınıflandırılması

Normal akışı kesen olaylar iki eksende ayrılır: komutun kendisinden mi kaynaklanıyor (senkron), yoksa dışarıdan mı geliyor (asenkron)?

| Tür | Kaynak | Örnek | Sonra |
| --- | --- | --- | --- |
| **Kesme** (interrupt) | Asenkron, dış aygıt | Zamanlayıcı, klavye, ağ kartı, disk "iş bitti" | Kesilen komuttan **sonraki** komuttan devam |
| **Trap** (tuzak) | Senkron, **bilerek** | `syscall`, `ecall`, kesme noktası (`int3`, `ebreak`) | Trap komutundan **sonraki** komuttan devam |
| **Fault** (hata) | Senkron, kurtarılabilir olabilir | Sayfa hatası, geçersiz komut, sıfıra bölme | Hatalı komutu **yeniden** çalıştır ya da süreci sonlandır |
| **Abort** | Senkron, kurtarılamaz | Donanım bellek hatası (ECC) | Sonlandır |

Terimler mimariden mimariye değişir (RISC-V hepsine "trap" der, senkron olanlara "exception", asenkron olanlara "interrupt"), ama ayrım aynı. En önemli fark **nereden devam edileceği**: sayfa hatası, çekirdek sayfayı getirdikten sonra **aynı** `lw`'yu yeniden çalıştırmalı (Ders 7.27'deki talep üzerine sayfalama); bir sistem çağrısı ise bittikten sonra bir **sonraki** komuttan devam etmeli.

---

## 3. Bir trap'in adım adım işleyişi

RISC-V'de (M modu için; S modu aynı, `m` yerine `s` önekli register'larla) bir trap olduğunda donanım tek bir döngüde şunları yapar:

1. Trap'e sebep olan komutun adresini `mepc`'ye (exception PC) kaydeder.
2. Sebebi `mcause`'a yazar: en üst bit 1 ise kesme, 0 ise istisna; geri kalanı kod. Örneğin 2 = geçersiz komut, 8 = U modundan `ecall`, 13 = yükleme sayfa hatası, 15 = saklama sayfa hatası.
3. Hatalı adres gibi ek bilgiyi `mtval`'e yazar.
4. Önceki ayrıcalık seviyesini kaydeder ve M moduna geçer; kesmeleri kapatır.
5. PC'yi `mtvec` register'ındaki adrese ayarlar: işletim sisteminin **trap işleyicisi** (trap handler).

İşleyici (yazılım, işletim sistemi) bütün register'ları yığına kaydeder (Ders 7.11'deki çerçevenin büyük hali), `mcause`'a bakıp ne olduğunu anlar, gerekeni yapar, register'ları geri yükler ve **`mret`** komutunu çalıştırır: ayrıcalık seviyesini geri alır ve `mepc`'ye atlar. Sistem çağrısında işleyici dönmeden önce `mepc`'yi 4 artırır (`ecall`'u tekrar çalıştırmamak için); sayfa hatasında artırmaz (aynı komut tekrar denensin).

x86-64'te aynı iş **IDT** (interrupt descriptor table) ile yapılır: 256 girdilik bir tablo, her istisna/kesme numarası için bir işleyici adresi (0 = sıfıra bölme, 6 = geçersiz komut, 13 = genel koruma, 14 = sayfa hatası; hatalı adres `cr2`'ye yazılır). `syscall` komutu ise daha hızlı, özel bir yol kullanır (`MSR_LSTAR` register'ındaki adrese atlar; Ders 7.18'deki `rcx`/`r11` bozulmasının sebebi, dönüş adresinin ve bayrakların oraya kaydedilmesi).

### RARS'ta trap: `ecall`

Ders 7.4'ten beri kullandığımız `ecall` bir trap'tir. RARS'ta işletim sistemi olmadığı için simülatörün kendisi trap işleyicisi gibi davranıyor ve `a7`'deki servis numarasına bakıyor:

```asm
# RARS: ecall bir trap; a7 = servis numarasi
    .text
main:
    li   a7, 1          # PrintInt
    li   a0, 42
    ecall
    li   a7, 10         # Exit
    ecall
```

```
$ java -jar rars.jar nc ecall.s
42
```

Gerçek bir RISC-V Linux sisteminde aynı `ecall` U modundan S moduna bir trap üretir (`scause` = 8), çekirdeğin işleyicisi `a7`'ye bakar (Linux numaraları: 64 = `write`, 93 = `exit`; Ders 7.30'daki emülatör bunları kullanacak).

---

## 4. İstisnalardan sinyallere

İşletim sistemi bir istisnayı kendisi çözemezse (bir sayfa gerçekten geçersizse, bir komut gerçekten geçersizse) süreci kurtaramaz; ona bir **sinyal** (Unix) gönderir. Süreç sinyali yakalamadıysa varsayılan davranış sonlandırmadır, ve kabuk bunu `Segmentation fault` olarak raporlar (çıkış kodu 128 + sinyal numarası: SIGSEGV = 11 → 139, Ders 7.14 ve 7.18).

| Donanım olayı | Sinyal |
| --- | --- |
| Geçersiz adrese erişim (sayfa hatası, koruma hatası) | SIGSEGV (11) |
| Hizalanmamış erişim (bazı mimarilerde), eşlenmiş ama erişilemeyen dosya | SIGBUS (7 ya da 10) |
| Sıfıra bölme (x86-64), kayan nokta istisnası (açıksa) | SIGFPE (8) |
| Geçersiz komut | SIGILL (4) |
| Kesme noktası komutu | SIGTRAP (5) |
| Zamanlayıcı (`alarm`, `setitimer`) | SIGALRM (14) |

Bir program bu sinyalleri yakalayabilir. Aşağıdaki program beş olayı tetikleyip her birinin kullanıcı alanından nasıl göründüğünü yazdırıyor. Hatalı komutu "atlamak" için `sigsetjmp`/`siglongjmp` kullanıyoruz: sinyal işleyicisi, önceden kaydedilmiş bir noktaya uzun bir atlama yapıyor. (Bu bir gösteri tekniği. Gerçek programlarda SIGSEGV'den sonra devam etmek neredeyse hiçbir zaman doğru değil; programın durumu artık güvenilir değil. Ayrıca işleyicide `printf` çağırmak teknik olarak güvenli değil, sadece "async-signal-safe" fonksiyonlar çağrılmalı; burada kısalık için kullanıyoruz.)

```c
/* Istisnalar kullanici alanindan nasil gorunur: CPU trap -> cekirdek -> sinyal */
#include <stdio.h>
#include <signal.h>
#include <setjmp.h>
#include <string.h>
#include <unistd.h>

static sigjmp_buf geri;
static volatile sig_atomic_t tik;

static void yakala(int sig, siginfo_t *bilgi, void *baglam) {
    (void)baglam;
    printf("  -> sinyal %d (%s), hatali adres %p\n", sig, strsignal(sig), bilgi->si_addr);
    siglongjmp(geri, 1);                  /* hatali komutu atla, deneye devam et */
}

static void zamanlayici(int sig) { (void)sig; tik++; }

int main(void) {
    setvbuf(stdout, NULL, _IONBF, 0);     /* tamponsuz: cikti sirasi karismasin */
    struct sigaction sa;
    memset(&sa, 0, sizeof sa);
    sa.sa_sigaction = yakala;
    sa.sa_flags = SA_SIGINFO | SA_NODEFER;
    sigaction(SIGSEGV, &sa, NULL);
    sigaction(SIGBUS, &sa, NULL);
    sigaction(SIGFPE, &sa, NULL);
    sigaction(SIGILL, &sa, NULL);
    sigaction(SIGTRAP, &sa, NULL);

    puts("1) NULL isaretciden okuma (sayfa hatasi, fault):");
    if (!sigsetjmp(geri, 1)) { volatile int *p = NULL; printf("%d\n", *p); }

    puts("2) Tamsayi sifira bolme:");
    if (!sigsetjmp(geri, 1)) {
        volatile int a = 7, b = 0;
        printf("  7 / 0 = %d (istisna olmadi!)\n", a / b);
    }

    puts("3) Gecersiz komut (__builtin_trap):");
    if (!sigsetjmp(geri, 1)) { __builtin_trap(); }

    puts("4) Zamanlayici kesmesi benzeri (SIGALRM, her 10 ms):");
    signal(SIGALRM, zamanlayici);
    ualarm(10000, 10000);
    volatile long say = 0;
    while (tik < 5) say++;               /* dongu "habersizce" 5 kez kesildi */
    ualarm(0, 0);
    printf("  5 kesme geldi, aralarda dongu %ld tur dondu\n", say);

    puts("5) Sistem cagrisi (bilerek yapilan trap): write()");
    long n = write(1, "  merhaba, cekirdek\n", 20);
    printf("  write %ld bayt yazdi\n", n);
    return 0;
}
```

Aynı kaynak kod, iki farklı makine:

```
=== x86-64 Linux (gcc 13)
1) NULL isaretciden okuma (sayfa hatasi, fault):
  -> sinyal 11 (Segmentation fault), hatali adres (nil)
2) Tamsayi sifira bolme:
  -> sinyal 8 (Floating point exception), hatali adres 0x55555555541f
3) Gecersiz komut (__builtin_trap):
  -> sinyal 4 (Illegal instruction), hatali adres 0x555555555541
4) Zamanlayici kesmesi benzeri (SIGALRM, her 10 ms):
  5 kesme geldi, aralarda dongu 99143919 tur dondu
5) Sistem cagrisi (bilerek yapilan trap): write()
  merhaba, cekirdek
  write 20 bayt yazdi

=== arm64 macOS (Apple M2, clang)
1) NULL isaretciden okuma (sayfa hatasi, fault):
  -> sinyal 11 (Segmentation fault: 11), hatali adres 0x0
2) Tamsayi sifira bolme:
  7 / 0 = 0 (istisna olmadi!)
3) Gecersiz komut (__builtin_trap):
  -> sinyal 5 (Trace/BPT trap: 5), hatali adres 0x102f546f8
4) Zamanlayici kesmesi benzeri (SIGALRM, her 10 ms):
  5 kesme geldi, aralarda dongu 83030755 tur dondu
5) Sistem cagrisi (bilerek yapilan trap): write()
  merhaba, cekirdek
  write 20 bayt yazdi
```

Satır satır:

1. **NULL okuma:** ikisinde de SIGSEGV, hatalı adres 0. Adres 0'ı içeren sayfa hiçbir süreçte eşlenmez (tam bu tür hataları yakalamak için); MMU sayfa hatası verir, çekirdek "bu adres geçerli bir bölgede değil" der ve sinyal gönderir. `si_addr`, x86-64'te `cr2`'den, RISC-V'de `stval`'den gelen değer.
2. **Sıfıra bölme:** iki mimari **farklı**. x86-64'ün `idiv` komutu sıfıra bölmede donanım istisnası (#DE, vektör 0) üretir; Linux bunu SIGFPE'ye çevirir (adı "kayan nokta" ama tamsayı bölmesi için de kullanılıyor, tarihî bir isim). `si_addr` = `0x...41f`, `objdump`'ta `141f: idiv %ecx`: tam o komut (PIE tabanı `0x555555554000`). arm64'ün `sdiv` komutu ise sıfıra bölmede istisna üretmez, **0 döndürür**. RISC-V de istisna üretmez (Alıştırma 1). C açısından ikisi de doğru: sıfıra bölme UB (Ders 2.12), standart hiçbir sonuç garanti etmiyor.
3. **Geçersiz komut:** `__builtin_trap()` x86-64'te `ud2` ("tanımsız komut", bilerek geçersiz; `objdump`'ta `1541: ud2`, hatalı adres tam o), arm64'te `brk #0x1` (kesme noktası komutu) üretiyor. Bu yüzden sinyaller farklı: SIGILL ve SIGTRAP.
4. **Zamanlayıcı:** `ualarm` çekirdekten her 10 ms'de bir sinyal ister. Çekirdek bunu donanım zamanlayıcı kesmesiyle sağlıyor: zamanlayıcı yongası işlemciyi kesiyor, çekirdek sürecin süresini kontrol edip sinyal gönderiyor. `while` döngüsünün kendisinde hiçbir şey yok; dışarıdan 5 kez kesildi ve her seferinde kaldığı yerden devam etti, ~20 milyon tur arayla. Aynı mekanizma, çekirdeğin süreçler arasında geçiş yapmasının (zaman paylaşımlı çoklu görev, Faz 10) temeli: zamanlayıcı kesmesi gelince çekirdek "bu sürecin süresi doldu" deyip başka bir sürece geçebilir.
5. **Sistem çağrısı:** bilerek yapılan bir trap. Hata değil; `write` sonucu (20 bayt) normal şekilde döndü. Ders 7.18'de `syscall` komutuyla elle yaptığımızın libc sarmalayıcısı.

Bir ayrıntı: x86-64'te gcc bu programı derlerken `a / b`'yi gerçekten `idiv` ile yaptı çünkü `volatile` değişkenler kullandık. `7 / 0` sabit olsaydı derleyici bunu derleme anında görür, ve UB olduğu için istediğini yapabilirdi (Ders 7.15).

---

## 5. Kesmeler ve aygıtlar

Asenkron kesmeler, işlemcinin dış dünyayla konuşma biçimi. Bir disk okuma işlemi milisaniyeler sürer (Ders 7.24); işlemci o sürede beklemek yerine başka işler yapar, disk işi bitince bir **kesme** gönderir. Alternatif, işlemcinin sürekli "bitti mi?" diye sorması (**yoklama**, polling), çok hızlı aygıtlar (yüksek hızlı ağ kartları) dışında israf.

Kesmeler sırasız bir işlemcide (Ders 7.23) bile **kesin** olmalı: kesme bir komut sınırında alınır, ROB'daki o noktadan sonraki komutlar iptal edilir, `mepc` ilk iptal edilen komutu gösterir. Kesme işleyicisi bitince oradan devam edilir; program hiçbir şey fark etmez (zamanlayıcı satırındaki döngü gibi).

İşletim sistemi kodunun kritik bölümleri (örneğin bir kesme işleyicisinin paylaşılan bir veriyi güncellediği yer) kesmeleri kısa bir süre **kapatır** (ayrıcalıklı komut). Kullanıcı programları bunu yapamaz; Faz 10'da onların aynı soruna (iş parçacıkları arasında paylaşılan veri) kilitlerle nasıl çözüm bulduğunu göreceğiz.

---

## Alıştırmalar

**1** – RARS'ta `li t0, 7; li t1, 0; div a0, t0, t1` çalıştırıp `a0`'ı yazdır. Sonra `rem a0, t0, t1`. Ne çıkıyor? RISC-V belirtimi neden sıfıra bölmeyi bir istisna yapmıyor?

**2** – Ders 7.18'de `void _start(void) { }` programı SIGSEGV ile çökmüştü. Bölüm 3'teki adımlarla anlat: hangi komut, hangi istisna, `mtval` (ya da `cr2`) ne içerir, çekirdek ne yapar?

**3** – Bir sayfa hatası işleyicisinin, sayfayı diske bakarak çözdükten sonra `mepc`'yi neden artırmaması gerektiğini, artırsaydı ne olacağını açıkla.

**4** – Bir program saniyede 10⁶ sistem çağrısı yapıyor ve her biri kullanıcı → çekirdek → kullanıcı geçişi için ~100 ns harcıyor. Sadece geçişler için ne kadar zaman gider? Bunu azaltmak için ne yapılabilir? (İpucu: stdio tamponlaması, Ders 7.18.)

**5** – `trap.c`'deki zamanlayıcı bölümünde `volatile sig_atomic_t tik` yerine düz `int tik` kullansan `-O2` ile ne olabilir? Neden?

<details>
<summary>Cevaplar</summary>

**1** – RARS çıktısı:

```
-1
7
```

`div` sıfıra bölmede **−1** (bütün bitler 1) döndürür, `rem` bölüneni (7) döndürür. Bu değerler `x = (x / y) * y + x % y` eşitliğini koruyor: $(-1)(0) + 7 = 7$. Belirtimin gerekçesi: istisna, boru hattında (Ders 7.21) pahalı ve karmaşık bir yol açar, ve sıfıra bölmeyi kontrol etmek isteyen yazılım bunu tek bir dal komutuyla (`beqz t1, hata`) zaten yapabilir. Sıradan aritmetik komutlarının hiç istisna üretmemesi donanımı basitleştiriyor. arm64 de aynı yolu seçmiş (0 döndürüyor); x86 tarihî nedenlerle istisna üretiyor.

**2** – `_start`'ın sonundaki `ret`, yığının tepesindeki değeri (`argc` = 1) dönüş adresi olarak alıp `0x1`'e atlar. İşlemci bir sonraki komutu `0x1`'den getirmeye çalışır: adres çevirisinde (Ders 7.27) bu sayfa eşli değil, **komut getirme sayfa hatası** (RISC-V'de `mcause`/`scause` = 12, x86-64'te vektör 14). `mtval` / `cr2` = `0x1`, `mepc` = `0x1`. Çekirdek sürecin bellek haritasına bakar, `0x1`'i içeren geçerli bir bölge bulamaz ve sürece SIGSEGV gönderir. İşleyici yok, varsayılan davranış: sonlandır. Kabuk 128 + 11 = 139 raporlar.

**3** – Sayfa hatası komutun **tamamlanamadığını** söylüyor: `lw` veriyi okuyamadı, hedef register'a hiçbir şey yazılmadı. Çekirdek sayfayı getirdikten sonra aynı `lw`'nun **tekrar** çalıştırılması gerekiyor ki bu sefer başarılı olsun. `mepc` artırılsaydı `lw` atlanır, hedef register'da eski (alakasız) değer kalır ve program sessizce yanlış veriyle devam ederdi. Sistem çağrısında ise tersi: `ecall` zaten "tamamlandı", tekrar çalıştırılırsa aynı çağrı iki kez yapılır.

**4** – $10^6 \times 100$ ns = **0.1 saniye** her saniyede: zamanın %10'u sadece mod geçişlerine gidiyor (çekirdeğin asıl işi hariç). Çare çağrı sayısını azaltmak: küçük `write`'ları kullanıcı alanında bir tamponda biriktirip tek büyük `write` yapmak. stdio'nun `printf` için yaptığı tam bu (Ders 7.18'deki tamponlama): 1000 kısa satır, tek bir sistem çağrısı. Linux'ta ayrıca sık kullanılan bazı çağrılar (`clock_gettime` gibi) **vDSO** ile hiç çekirdeğe girmeden kullanıcı alanında çalışıyor; Ders 7.22'deki ölçümlerimizde `clock_gettime` bu yüzden ucuzdu.

**5** – Derleyici, `while (tik < 5) say++;` döngüsünün içinde `tik`'i değiştiren hiçbir şey görmez (sinyal işleyicisi "görünmez" bir yerden değiştiriyor), bu yüzden `tik`'i bir kez okumakta serbest. Denedik (`static int tik`, `-O2`), iki derleyici iki farklı bozuk program üretti:

- **gcc 13 (x86-64):** `tik`'i bir kez karşılaştırıyor, sonra `10d1: jmp 10d1`: kendine atlayan bir komut. Kesmeler geliyor, işleyici bellekteki `tik`'i artırıyor, ama döngü belleğe bir daha bakmıyor. Program **sonsuza dek** dönüyor (`timeout 2` ile öldürüldü).
- **clang (arm64):** döngüyü **tamamen sildi**; program anında `bitti 0` yazdı. Derleyicinin akıl yürütmesi: döngünün içinde `tik` değişmiyor, yani `tik < 5` ya baştan yanlış (döngü hiç dönmez) ya da baştan doğru (döngü sonsuza dek, gözlemlenebilir hiçbir şey yapmadan döner). C11'e göre gözlemlenebilir etkisi olmayan bir döngünün sonlanacağını derleyici **varsayabilir**; ikinci durumu bu yüzden yok sayıp döngüyü sıfır turluk saydı ve `say = 0` ile devam etti.

İkisi de standarda uygun, ikisi de yanlış program. `volatile` "her erişimde belleğe git" der (Ders 3.21); `sig_atomic_t` de okuma ve yazmanın bölünmez olmasını garanti ediyor. Asenkron olaylarla paylaşılan veri derleyicinin optimizasyon varsayımlarını bozar; Faz 10'da iş parçacıklarıyla aynı soruna (ve `volatile`'ın orada yetmediğine) döneceğiz.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 8.1 (istisnalar) ve 8.5 (sinyaller).
- RISC-V Privileged Architecture Specification: `mcause`, `mepc`, `mtvec`, `mret` ve istisna kodları tablosu.
- Intel 64 and IA-32 Architectures Software Developer's Manual, Cilt 3A, Bölüm 6: kesme ve istisna işleme, IDT.
- Remzi & Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 6: "Limited Direct Execution" (trap, kullanıcı/çekirdek modu, zamanlayıcı kesmesi).
- `man 7 signal`, `man 2 sigaction`.

**Sıradaki ders:** Kayan nokta donanımı. x87'den SSE'ye geçiş, `xmm` register'ları, skaler float komutları (SIMD fazına köprü).
