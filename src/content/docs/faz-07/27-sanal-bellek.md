---
title: "7.27 Sanal bellek"
description: "Her sürece kendi adres uzayı: sanal ve fiziksel adres, sayfa ve çerçeve; sayfa tablosu girdisi (PTE) ve izin bitleri; tek seviyeli tablonun neden çok büyük olduğu ve çok seviyeli tablolar; RISC-V Sv32'de iki seviyeli adres çevirisini adım adım yapan bir C simülasyonu; TLB ve neden işe yaradığı; sayfa hatası, talep üzerine sayfalama ve macOS'ta (16 KB sayfa) mmap ile sayfa hatalarını saymak."
---

Ders 7.16'da program başlıkları "bu segmenti `0x1000` adresine yükle" diyordu; Ders 7.18'de çekirdeğin segmentleri belleğe **eşlediğini** söyledik. Ama aynı anda çalışan iki program da `0x1000`'i istiyorsa? Ve Ders 7.24'te 256 MB'lık bir dizi için ölçülen gecikmenin bir kısmını "TLB" diye bir şeye bağladık. Bu dersin konusu, bütün bunların altındaki mekanizma: **sanal bellek**. İşlemcinin her yükleme ve saklamada, programın gördüğü adresi gerçek RAM adresine çevirmesi.

---

## 1. Neden sanal bellek?

Programlar **sanal adreslerle** çalışır. İşlemcinin içindeki **MMU** (memory management unit) her erişimde sanal adresi **fiziksel adrese** (RAM'deki gerçek konum) çevirir. Çeviriyi işletim sistemi kurar, donanım uygular. Bu tek dolaylılık katmanı aynı anda dört sorunu çözer:

1. **Yalıtım:** her süreç kendi adres uzayını görür. Bir süreç ötekinin belleğine bir adres yazarak erişemez; o adres onun çeviri tablosunda yoktur. Bir programın çökmesi diğerlerini etkilemez.
2. **Basitlik:** her program `0x400000`'dan başlayabilir (Ders 7.18), bağlayıcı sabit adresler kullanabilir; programlar RAM'in neresine düştüklerini bilmek zorunda değil.
3. **Koruma:** her sayfanın izinleri var (oku/yaz/çalıştır). Ders 7.14'teki NX, Ders 7.17'deki RELRO, Ders 7.16'daki `R E` kod segmenti hep buradan.
4. **RAM'den büyük bellek:** kullanılmayan sayfalar diske çıkarılabilir; adres uzayı (64 bitte 256 TB) fiziksel RAM'den çok büyük olabilir. Paylaşımlı kütüphaneler (Ders 7.17) her süreçte aynı fiziksel sayfalara eşlenir.

---

## 2. Sayfalar ve sayfa tablosu

Çeviriyi bayt bayt yapmak imkânsız; bellek **sayfa** (page) denen sabit boyutlu parçalara bölünür. x86-64 ve RISC-V'de tipik sayfa 4 KB, Apple M serisinde 16 KB (Bölüm 6'da ölçüyoruz). Fiziksel bellekteki karşılığına **çerçeve** (frame) denir.

Sanal adres iki parçaya ayrılır (Ders 7.25'teki tag/index/offset ile aynı fikir):

```
 sanal adres:   |  sanal sayfa numarasi (VPN)  |  sayfa ici ofset  |
                                                  12 bit (4 KB)
```

Ofset çeviride **değişmez**; sadece VPN, bir **fiziksel sayfa numarasına** (PPN) çevrilir. Çeviri bilgisi **sayfa tablosunda** durur: her VPN için bir **sayfa tablosu girdisi** (PTE):

```
 PTE:  |  PPN  | ... | X | W | R | V |
                       |   |   |   +-- gecerli (bu sayfa esli mi?)
                       |   |   +------ okunabilir
                       |   +---------- yazilabilir
                       +-------------- calistirilabilir
```

(RISC-V'de ayrıca U: kullanıcı modunda erişilebilir mi, A: erişildi mi, D: yazıldı mı (kirli) bitleri var. A ve D işletim sisteminin "hangi sayfayı diske çıkarayım?" kararını verirken kullandığı bilgiler; Ders 7.25'teki LRU ve kirli bitin sayfa ölçeğindeki karşılığı.)

### Tek seviyeli tablo çok büyük

32 bitlik adres, 4 KB sayfa: VPN 20 bit, $2^{20} \approx 10^6$ PTE, her biri 4 bayt: **4 MB** tablo, her süreç için. Oysa tipik bir süreç adres uzayının küçük bir kısmını kullanır (kod en altta, yığın en üstte, arası boş). 64 bitte tek seviyeli tablo hesaplanamayacak kadar büyük.

Çözüm: **çok seviyeli** tablo, bir ağaç. RISC-V Sv32'de VPN ikiye bölünür:

```
 31            22 21            12 11             0
|    VPN[1]     |    VPN[0]      |     ofset      |
    10 bit          10 bit           12 bit
```

- `satp` register'ı kök tablonun fiziksel adresini tutar (her süreç değişiminde işletim sistemi bunu değiştirir: adres uzayı değişimi tek bir register yazmak).
- Kök tablonun `VPN[1]`. girdisi, ikinci seviye bir tabloyu gösterir.
- O tablonun `VPN[0]`. girdisi asıl PTE: PPN ve izinler.

Kullanılmayan 4 MB'lık bölgelerin ikinci seviye tablosu **hiç yoktur**: kökte o girdi geçersizdir. Kod + veri + yığın kullanan bir süreç için tablo: 1 kök + 2 alt tablo = 12 KB, 4 MB yerine.

64 bitlik sistemler aynı ağacı derinleştirir: RISC-V Sv39 3 seviye, x86-64 ve Sv48 4 seviye, en yenileri 5 seviye. Her seviye 9 bit (512 girdi × 8 bayt = bir 4 KB sayfa).

---

## 3. Simülasyon: adres çevirisi adım adım

MMU'nun yaptığını C'de yapalım. 4 MB'lık bir "fiziksel bellek" dizisi, içinde Sv32 sayfa tabloları; işletim sisteminin rolünü `esle` fonksiyonu, MMU'nun rolünü `cevir` fonksiyonu oynuyor. Bir de 4 girdilik küçük bir TLB (Bölüm 4).

```c
/* Sv32 (RV32) sanal bellek: iki seviyeli sayfa tablosu yuruyusu + kucuk TLB */
#include <stdio.h>
#include <stdint.h>

#define SAYFA 4096
#define V 0x1                                /* PTE bitleri: gecerli, okuma, yazma, calistirma */
#define R 0x2
#define W 0x4
#define X 0x8

static uint32_t fiziksel[1024 * 1024];       /* 4 MB "RAM", 32 bitlik kelimeler */
static uint32_t sonraki_ppn = 1;             /* bos fiziksel sayfa sayaci */

static uint32_t *pte_adresi(uint32_t ppn, uint32_t idx) { return &fiziksel[ppn * 1024 + idx]; }

static uint32_t kok_ppn;

/* va -> pa eslemesi kur (isletim sistemi isi) */
static void esle(uint32_t va, uint32_t pa, uint32_t izin) {
    uint32_t vpn1 = va >> 22, vpn0 = (va >> 12) & 0x3ff;
    uint32_t *p1 = pte_adresi(kok_ppn, vpn1);
    if (!(*p1 & V)) *p1 = (sonraki_ppn++ << 10) | V;          /* yaprak degil: R/W/X yok */
    uint32_t *p0 = pte_adresi(*p1 >> 10, vpn0);
    *p0 = ((pa >> 12) << 10) | izin | V;
}

typedef struct { int gecerli; uint32_t vpn, ppn; } TLBSatir;
static TLBSatir tlb[4];
static int tlb_sira, tlb_isabet, tlb_iska, bellek_okuma;

/* Donanimin (MMU) yaptigi: va -> pa, ya da sayfa hatasi (-1) */
static int64_t cevir(uint32_t va, int ayrinti) {
    uint32_t vpn = va >> 12, off = va & 0xfff;
    for (int i = 0; i < 4; i++)
        if (tlb[i].gecerli && tlb[i].vpn == vpn) {
            tlb_isabet++;
            if (ayrinti) printf("  0x%08x: TLB isabet -> pa 0x%08x\n", va, (tlb[i].ppn << 12) | off);
            return (tlb[i].ppn << 12) | off;
        }
    tlb_iska++;
    uint32_t vpn1 = va >> 22, vpn0 = (va >> 12) & 0x3ff;
    uint32_t pte1 = *pte_adresi(kok_ppn, vpn1); bellek_okuma++;
    if (ayrinti) printf("  0x%08x: vpn1=%u vpn0=%u off=0x%03x | PTE1=0x%08x", va, vpn1, vpn0, off, pte1);
    if (!(pte1 & V)) { if (ayrinti) printf(" -> SAYFA HATASI (seviye 1)\n"); return -1; }
    uint32_t pte0 = *pte_adresi(pte1 >> 10, vpn0); bellek_okuma++;
    if (ayrinti) printf(" PTE0=0x%08x", pte0);
    if (!(pte0 & V)) { if (ayrinti) printf(" -> SAYFA HATASI (seviye 0)\n"); return -1; }
    uint32_t ppn = pte0 >> 10;
    tlb[tlb_sira] = (TLBSatir){ 1, vpn, ppn }; tlb_sira = (tlb_sira + 1) % 4;   /* FIFO */
    if (ayrinti) printf(" -> pa 0x%08x\n", (ppn << 12) | off);
    return (ppn << 12) | off;
}

int main(void) {
    kok_ppn = sonraki_ppn++;
    esle(0x00010000, 0x00200000, R | X);      /* kod  */
    esle(0x00011000, 0x00201000, R | W);      /* veri */
    esle(0x7ffff000, 0x003ff000, R | W);      /* yigin */

    printf("Adres cevirisi (TLB bos):\n");
    cevir(0x00010abc, 1);
    cevir(0x00011004, 1);
    cevir(0x7ffffff0, 1);
    cevir(0x00010ac0, 1);                     /* ayni sayfa: TLB'den */
    cevir(0x00012000, 1);                     /* eslenmemis: seviye 0 bos */
    cevir(0x40000000, 1);                     /* eslenmemis: seviye 1 bos */

    /* Bir sayfa icinde 1024 kelime okuyan dongu */
    for (int i = 0; i < 4; i++) tlb[i].gecerli = 0;       /* TLB temizle (ornegin baglam degisimi) */
    tlb_isabet = tlb_iska = bellek_okuma = 0;
    for (uint32_t i = 0; i < 1024; i++) cevir(0x00011000 + 4 * i, 0);
    printf("\nayni sayfada 1024 erisim: TLB isabet %d, iska %d, tablo icin bellek okumasi %d\n",
           tlb_isabet, tlb_iska, bellek_okuma);
    return 0;
}
```

Üç sayfa eşliyoruz: kod (`0x00010000` → `0x00200000`, R+X), veri (`0x00011000` → `0x00201000`, R+W), yığın (`0x7ffff000` → `0x003ff000`, R+W). `sonraki_ppn` basit bir fiziksel sayfa ayırıcı: 1 kök tablo, 2 ve 3 ikinci seviye tablolar.

```
$ cc -O1 -Wall sv32.c -o sv32 && ./sv32
Adres cevirisi (TLB bos):
  0x00010abc: vpn1=0 vpn0=16 off=0xabc | PTE1=0x00000801 PTE0=0x0008000b -> pa 0x00200abc
  0x00011004: vpn1=0 vpn0=17 off=0x004 | PTE1=0x00000801 PTE0=0x00080407 -> pa 0x00201004
  0x7ffffff0: vpn1=511 vpn0=1023 off=0xff0 | PTE1=0x00000c01 PTE0=0x000ffc07 -> pa 0x003ffff0
  0x00010ac0: TLB isabet -> pa 0x00200ac0
  0x00012000: vpn1=0 vpn0=18 off=0x000 | PTE1=0x00000801 PTE0=0x00000000 -> SAYFA HATASI (seviye 0)
  0x40000000: vpn1=256 vpn0=0 off=0x000 | PTE1=0x00000000 -> SAYFA HATASI (seviye 1)

ayni sayfada 1024 erisim: TLB isabet 1023, iska 1, tablo icin bellek okumasi 2
```

İlk satırı elle doğrulayalım:

- `0x00010abc` = `0000000000 0000010000 101010111100`: `VPN[1]` = 0, `VPN[0]` = 16 (`0x10`), ofset `0xabc`.
- Kök tablonun 0. girdisi `0x801`: alt 10 bit `0x001` (sadece V; R/W/X yok, yani "yaprak değil, bir sonraki tabloya bak"), PPN = `0x801 >> 10` = **2**. İkinci seviye tablo fiziksel sayfa 2'de.
- O tablonun 16. girdisi `0x0008000b`: alt bitler `0xb` = `1011` = X, R, V (W yok: kod sayfası yazılamaz). PPN = `0x8000b >> 10` = `0x200`.
- Fiziksel adres = `0x200 << 12 | 0xabc` = `0x00200abc`. ✓

Veri sayfasının PTE'si `0x...07` = W, R, V (X yok: NX). Yığın sayfası `VPN[1]` = 511 ile kök tablonun son bölgesine düşüyor ve kendi ikinci seviye tablosunu (PPN 3) kullanıyor.

**Sayfa hataları** iki farklı seviyede: `0x00012000` için ikinci seviye tablo var ama 18. girdi boş; `0x40000000` için kökteki 256. girdi boş, ikinci seviye tablo hiç ayrılmamış. Gerçek donanımda ikisi de bir **sayfa hatası istisnası** (page fault) üretir ve kontrol işletim sistemine geçer (Ders 7.28).

---

## 4. TLB: çeviri önbelleği

Bu şemanın bir bedeli var: Sv32'de her yükleme **iki ek bellek okuması** (iki seviye PTE) gerektiriyor; x86-64'te dört. Her `lw` beş bellek erişimine dönüşseydi işlemci beş kat yavaşlardı.

Çözüm yine önbellek: **TLB** (translation lookaside buffer), son çevirileri (VPN → PPN + izinler) tutan küçük, genelde tam ilişkili (Ders 7.25) bir yapı. 32–64 girdilik L1 TLB ve 1000–3000 girdilik L2 TLB tipik. TLB isabetinde çeviri sıfır ek maliyetli (L1 önbellek erişimiyle paralel, Ders 7.25 Bölüm 4'teki index hilesi sayesinde).

Simülasyonun son satırı neden işe yaradığını gösteriyor: bir sayfadaki 1024 kelimeye erişim, **tek** bir TLB ıskası (ve iki tablo okuması), sonra 1023 isabet. Sayfalar büyük (4 KB), programlar yerel (Ders 7.24): TLB isabet oranı tipik olarak %99'un üstünde.

**TLB erimi** (reach) = girdi sayısı × sayfa boyutu. 64 girdi × 4 KB = 256 KB. Ders 7.24'teki 256 MB'lık rastgele kovalama bunun çok ötesinde: her erişim muhtemelen bir TLB ıskası ve bir sayfa tablosu yürüyüşü, 100 ns'nin bir kısmı buradan. Çare **büyük sayfalar** (huge pages): x86-64'te 2 MB ve 1 GB'lık sayfalar, ağacın bir ya da iki seviyesini atlayan yaprak PTE'ler. Aynı 64 girdi 2 MB'lık sayfalarla 128 MB örter. Apple'ın 16 KB'lık sayfası da kısmen bu yüzden: aynı TLB 4 kat fazla bellek örter.

Süreç değiştiğinde TLB'deki çeviriler geçersiz (başka bir adres uzayına ait). Ya TLB temizlenir (simülasyondaki "bağlam değişimi" satırı), ya da her girdiye bir adres uzayı kimliği (ASID) eklenir ve temizlemeye gerek kalmaz.

---

## 5. Sayfa hatası ve talep üzerine sayfalama

Sayfa hatası her zaman bir hata değil. İşletim sistemleri onu bilerek kullanır:

- **Talep üzerine sayfalama** (demand paging): `mmap` ya da `malloc` büyük bir bölge istediğinde çekirdek hiçbir fiziksel sayfa ayırmaz, sadece "bu adres aralığı geçerli" diye not alır. Bir sayfaya ilk dokunulduğunda sayfa hatası olur, çekirdek o anda bir çerçeve ayırıp sıfırlar, PTE'yi doldurur ve komutu **yeniden çalıştırır**. Program hiçbir şey fark etmez (Ders 7.23'teki kesin istisnaların neden şart olduğu burada).
- **Diskten yükleme:** Ders 7.18'de çekirdeğin program dosyasını okumadan eşlediğini söyledik; kod sayfaları ilk çalıştırıldıklarında diskten gelir.
- **Yazınca kopyala** (copy-on-write): `fork` ebeveyn ve çocuğu aynı fiziksel sayfalara salt okunur eşler; biri yazınca sayfa hatası, çekirdek o sayfayı kopyalar (Faz 10).
- **Takas** (swap): RAM dolunca az kullanılan sayfalar diske yazılır, PTE geçersiz yapılır; tekrar erişilince geri okunur. Ders 7.24'teki tabloya göre bir disk erişimi milyonlarca döngü: takasa düşen bir sistem neden "dondu" sanılır, buradan.

Bir sayfa hatasının diske gitmeden çözülenine **minor** (küçük), diske gidenine **major** (büyük) hata denir. Talep üzerine sayfalamayı gerçek bir sistemde görelim:

```c
/* Gercek isletim sisteminde sayfalar: sayfa boyutu ve talep uzerine sayfalama */
#include <stdio.h>
#include <unistd.h>
#include <sys/mman.h>
#include <sys/resource.h>

static long hatalar(void) {
    struct rusage r;
    getrusage(RUSAGE_SELF, &r);
    return r.ru_minflt;                     /* "minor" sayfa hatasi: diske gitmeden cozulen */
}

int main(void) {
    long sayfa = sysconf(_SC_PAGESIZE);
    printf("sayfa boyutu: %ld bayt\n", sayfa);

    size_t boyut = 64UL * 1024 * 1024;     /* 64 MB ayir */
    long h0 = hatalar();
    char *p = mmap(NULL, boyut, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    long h1 = hatalar();
    printf("mmap 64 MB sonrasi sayfa hatasi: %ld (henuz hic dokunulmadi)\n", h1 - h0);

    for (size_t i = 0; i < boyut; i += sayfa) p[i] = 1;   /* her sayfaya bir kez dokun */
    long h2 = hatalar();
    printf("her sayfaya dokununca: %ld hata (beklenen ~%zu = 64 MB / sayfa)\n",
           h2 - h1, boyut / sayfa);

    for (size_t i = 0; i < boyut; i += sayfa) p[i] = 2;   /* ikinci kez: artik esli */
    printf("ikinci tur: %ld hata\n", hatalar() - h2);
    munmap(p, boyut);
    return 0;
}
```

macOS, Apple M2:

```
$ cc -O1 -Wall sayfa.c -o sayfa && ./sayfa
sayfa boyutu: 16384 bayt
mmap 64 MB sonrasi sayfa hatasi: 0 (henuz hic dokunulmadi)
her sayfaya dokununca: 4096 hata (beklenen ~4096 = 64 MB / sayfa)
ikinci tur: 0 hata
```

- Sayfa **16 KB**: Apple Silicon'da 4 KB değil.
- `mmap` 64 MB "ayırdı" ama **sıfır** sayfa hatası: hiçbir fiziksel bellek henüz verilmedi.
- Her sayfaya bir bayt yazmak tam **4096** hata üretti: $64 \text{ MB} / 16 \text{ KB} = 4096$. Her biri çekirdeğe bir yolculuk, bir sıfırlanmış çerçeve, bir PTE.
- İkinci turda sıfır: sayfalar artık eşli, çeviri tablolarda ve TLB'de.

---

## Alıştırmalar

**1** – Sv32'de `0x12345678` sanal adresinin `VPN[1]`, `VPN[0]` ve ofsetini hesapla.

**2** – 48 bitlik sanal adresler, 4 KB sayfa, 8 baytlık PTE ile tek seviyeli bir sayfa tablosu kaç bayt olurdu? 4 seviyeli tabloda, kod (bir sayfa), veri (bir sayfa) ve yığın (bir sayfa) kullanan, bunlar adres uzayının birbirinden uzak üç yerinde olan bir süreç için en az kaç sayfa tablosu sayfası gerekir?

**3** – Simülatöre izin kontrolü ekle: `cevir`'e bir `yazma` parametresi ver ve PTE'de W biti yoksa "koruma hatası" döndür. Kod sayfasına (`0x00010abc`) yazmayı dene.

**4** – L1 TLB'si 64 girdili bir işlemcide, 4 KB ve 2 MB sayfalarla TLB erimi ne olur? Ders 7.24'teki 64 MB'lık rastgele kovalamada hangisinde TLB ıskası daha az olur?

**5** – Bölüm 5'teki programı x86-64 Linux'ta çalıştırınca sayfa boyutu 4096 çıktı ama "her sayfaya dokununca" satırı 16 384 değil **543** hata gösterdi. Bunun olası açıklaması ne? (İpucu: Linux'un "şeffaf büyük sayfalar" (transparent huge pages, THP) özelliği.)

<details>
<summary>Cevaplar</summary>

**1** – `0x12345678 >> 22` = **72** (`0x48`); `(0x12345678 >> 12) & 0x3ff` = **837** (`0x345`); ofset `0x678`. Kontrol: $72 \cdot 2^{22} + 837 \cdot 2^{12} + 0x678 = 0x12000000 + 0x345000 + 0x678$ = `0x12345678`. ✓

**2** – Tek seviye: VPN $48 - 12 = 36$ bit, $2^{36}$ PTE × 8 bayt = $2^{39}$ bayt = **512 GB**, süreç başına. İmkânsız. 4 seviyede (her seviye 9 bit): kök tablo 1 sayfa. Üç bölge birbirinden uzaksa (farklı kök girdileri) her birinin kendi 3., 2. ve 1. seviye tabloları gerekir: $1 + 3 \times 3 = 10$ sayfa = 40 KB. Bölgeler yakınsa üst seviye tabloları paylaşırlar ve sayı azalır (en az $1 + 1 + 1 + 1 = 4$, hepsi aynı 2 MB'lık bölgedeyse).

**3** – `cevir`'de PTE0 okunduktan sonra: `if (yazma && !(pte0 & W)) { printf(" -> KORUMA HATASI\n"); return -1; }`. `0x00010abc`'nin PTE'si `0x8000b` (X, R, V), W yok: yazma reddedilir. Gerçek donanımda bu da bir sayfa hatası istisnasıdır (RISC-V'de "store page fault"); işletim sistemi PTE'ye bakar, sayfa gerçekten salt okunursa sürece SIGSEGV gönderir (Ders 7.28). Yazınca kopyala (Bölüm 5) aynı mekanizmayı kullanır, tek farkla: işletim sistemi "bu sayfa aslında yazılabilir olmalı, paylaşıldığı için salt okunur" bilgisini tutar ve kopyalayıp devam eder.

**4** – 4 KB: $64 \times 4 \text{ KB} = 256$ KB. 2 MB: $64 \times 2 \text{ MB} = 128$ MB. 64 MB'lık rastgele kovalamada 4 KB sayfalarla TLB erimi dizinin 1/256'sı, neredeyse her erişim bir TLB ıskası; 2 MB sayfalarla bütün dizi TLB'ye sığar (32 sayfa), TLB ıskası neredeyse yok. Büyük sayfalar, büyük ve rastgele erişilen veri yapıları (veritabanları, sanal makineler) için önemli bir optimizasyon.

**5** – THP açıkken çekirdek, 2 MB hizalı ve 2 MB boyutlu anonim bölgelere ilk dokunuşta 4 KB'lık bir sayfa yerine doğrudan bir **2 MB'lık büyük sayfa** verebilir: tek bir sayfa hatası 512 küçük sayfanın yerini tutar. 64 MB = 32 büyük sayfa; ölçülen 543, bölgenin bir kısmının büyük sayfalarla, hizalanmamış uçlarının ve geri kalanının küçük sayfalarla eşlendiğini düşündürüyor. (Ayrıca bu ölçüm emüle edilen bir x86-64 ortamında alındı, emülatörün kendi bellek davranışı da sayıya karışmış olabilir.) Ders: sayfa boyutu `sysconf`'un söylediği tek bir sayı değil; işletim sistemi duruma göre daha büyüklerini kullanabilir.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 9: sanal bellek, çok seviyeli sayfa tabloları, TLB, `mmap`.
- RISC-V Privileged Architecture Specification, Bölüm "Supervisor-Level ISA": Sv32, Sv39, Sv48 sayfa tablosu biçimleri (bu dersteki PTE bitleri oradan).
- Remzi & Andrea Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Bölüm 18–23 (ücretsiz, ostep.org): sayfalama, TLB, çok seviyeli tablolar, takas.
- `man 2 mmap`, `man 2 getrusage`.

**Sıradaki ders:** Kesmeler ve istisnalar. Trap, interrupt, fault; kullanıcı ve çekirdek modu.
