---
title: "5.19 CRC ve Hamming kodu"
description: "Hataları yakalamak ve düzeltmek: CRC-32'yi bir polinom bölmesi olarak (XOR'lu uzun bölme, Ders 5.13'ün GF(2) hali) bit bit ve 256'lık tabloyla hesaplamak, standart kontrol değeri 0xCBF43926 ile doğrulamak; ve Hamming(7,4) kodu — 4 veri bitine 3 parite biti ekleyip herhangi bir tek bit hatasının yerini sendromla bulup düzeltmek, tüm veri ve hata konumlarında sınanmış."
---

Ders 5.8'de parite ile tek bir hata biti **algılamayı** görmüştük. Bu derste iki adım ileri gidiyoruz: **CRC**, bir veri bloğundaki hataları yüksek güvenilirlikle yakalayan bir sağlama (checksum); ve **Hamming kodu**, bir hatayı sadece algılamakla kalmayıp **düzelten** bir kod. İkisi de bitlerle ve XOR'la çalışıyor — CRC bir polinom bölmesi (Ders 5.13'teki uzun bölmenin bir akrabası), Hamming ise akıllıca yerleştirilmiş parite bitleri (Ders 5.8).

---

## 1. CRC: polinom bölmesi olarak sağlama

Bir dosyayı indirdiğinde ya da bir ağ paketi geldiğinde, bozulmadığından nasıl emin oluruz? Veriye bir **sağlama değeri** (checksum) ekleyip, alıcının aynı hesabı yapıp karşılaştırmasıyla. Basit bir toplam zayıftır (birçok hatayı kaçırır); **CRC** (Cyclic Redundancy Check) çok daha güçlü, çünkü veriyi bir **polinom** gibi görüp sabit bir polinoma **bölüyor** ve kalanı sağlama olarak kullanıyor.

Bu bölme, Ders 5.13'teki uzun bölmenin **GF(2)** (iki elemanlı alan) halidir: çıkarma yerine XOR, elde/ödünç yok. CRC-32'nin bit bit hali:

```c
#define POLY 0xEDB88320u   // CRC-32 polinomu (ters bit sirali)

uint32_t crc32_bitwise(const void *data, size_t len) {
    const uint8_t *p = data;
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++) {
        crc ^= p[i];
        for (int b = 0; b < 8; b++) {
            crc = (crc & 1) ? (crc >> 1) ^ POLY : crc >> 1;
        }
    }
    return ~crc;
}
```

Her byte için 8 bit işleniyor: en düşük bit 1 ise polinomla XOR'la ve kaydır, değilse sadece kaydır — tam olarak Ders 5.13'teki "bölen sığıyorsa çıkar" kararının XOR hali (çıkarma = XOR). `0xEDB88320`, standart CRC-32 polinomunun bit-ters hali; `0xFFFFFFFF` başlangıç ve sondaki `~` (tümleyen), standart CRC-32'nin kuralları. Standart **kontrol değeri** ile doğruladık:

```
CRC-32("123456789") = 0xCBF43926
```

Bu, CRC-32'nin dünyaca bilinen test değeri — her doğru uygulama "123456789" için bunu üretir.

### Tablo ile hızlandırma

Bit bit sürüm her byte için 8 adım. Ders 4.11 ve 5.8'deki gibi, **önceden hesaplanmış bir tablo** ile byte başına tek adıma inilir:

```c
static uint32_t table[256];
void crc32_build_table(void) {
    for (uint32_t i = 0; i < 256; i++) {
        uint32_t c = i;
        for (int b = 0; b < 8; b++) c = (c & 1) ? (c >> 1) ^ POLY : c >> 1;
        table[i] = c;
    }
}
uint32_t crc32_table(const void *data, size_t len) {
    const uint8_t *p = data;
    uint32_t crc = 0xFFFFFFFFu;
    for (size_t i = 0; i < len; i++)
        crc = (crc >> 8) ^ table[(crc ^ p[i]) & 0xFF];
    return ~crc;
}
```

Tablo, her olası byte için "8 bitlik bölme adımının sonucunu" saklıyor; ana döngü byte başına bir tablo bakışı + bir XOR yapıyor (Ders 4.11'deki işlem tablosu fikri). Aynı `0xCBF43926`'yı üretiyor. Gerçek CRC kütüphaneleri 8'li ya da 16'lı tablolarla daha da hızlandırır; bazı işlemcilerde CRC için özel komut bile var (`crc32`, x86 SSE4.2).

CRC **hata düzeltmez**, sadece **algılar** — ama çok güçlü algılar: tek bit, çift bit, patlama (burst) hatalarını neredeyse kesin yakalar. ZIP, PNG, Ethernet, ve neredeyse her dosya formatı/protokol CRC kullanır. Tek bir bit değişince CRC tamamen değişir:

```
"merhaba" = 0x76DFF90D    "merhbba" = 0x74994754   (bir harf, bambaska CRC)
```

---

## 2. Hamming kodu: hatayı düzeltmek

CRC hatayı yakalar ama düzeltemez — bozuk veriyi yeniden istemek gerekir. **Hamming kodu** ise tek bir bit hatasını hem bulur hem **düzeltir**, veri yeniden gönderilmeden. Fikir: veriye, her biri farklı bir bit grubunun paritesini (Ders 5.8) tutan, akıllıca yerleştirilmiş **parite bitleri** eklemek.

**Hamming(7,4)**: 4 veri bitine 3 parite biti ekleyip 7 bit üretir. Parite bitleri 1, 2, 4 (2'nin kuvvetleri) konumlarında; veri bitleri 3, 5, 6, 7'de. Her parite biti, konum numarasının belirli bir bitini içeren konumları kontrol eder:

```c
uint8_t hamming_encode(uint8_t data) {   // data: 4 bit
    int d1 = (data>>0)&1, d2 = (data>>1)&1, d3 = (data>>2)&1, d4 = (data>>3)&1;
    int p1 = d1 ^ d2 ^ d4;      // konum 1,3,5,7'nin paritesi
    int p2 = d1 ^ d3 ^ d4;      // konum 2,3,6,7
    int p4 = d2 ^ d3 ^ d4;      // konum 4,5,6,7
    return (p1<<0)|(p2<<1)|(d1<<2)|(p4<<3)|(d2<<4)|(d3<<5)|(d4<<6);
}
```

Her parite biti, konum numarasının ikilik gösteriminde belirli bir biti 1 olan konumları XOR'luyor (Ders 5.8'deki parite): `p1` (konum 1 = `001`), son biti 1 olan konumları (1,3,5,7); `p2` (konum 2 = `010`), orta biti 1 olanları (2,3,6,7); `p4` (konum 4 = `100`), üst biti 1 olanları (4,5,6,7).

### Sendrom: hatanın yerini bulmak

Alıcı, aynı parite kontrollerini yapıp bir **sendrom** (syndrome) hesaplar. Sendrom, hatalı bitin **konum numarasını** doğrudan verir — bu Hamming'in dehası:

```c
int hamming_syndrome(uint8_t code) {
    int bit[8];
    for (int i=1;i<=7;i++) bit[i] = (code>>(i-1))&1;
    int s1 = bit[1]^bit[3]^bit[5]^bit[7];
    int s2 = bit[2]^bit[3]^bit[6]^bit[7];
    int s4 = bit[4]^bit[5]^bit[6]^bit[7];
    return s1 | (s2<<1) | (s4<<2);
}
uint8_t hamming_decode(uint8_t code, int *corrected) {
    int syn = hamming_syndrome(code);
    if (syn != 0) {
        code ^= (1u << (syn-1));   // hatali biti cevir: duzeltildi!
        *corrected = syn;
    } else {
        *corrected = 0;
    }
    int d1=(code>>2)&1, d2=(code>>4)&1, d3=(code>>5)&1, d4=(code>>6)&1;
    return d1|(d2<<1)|(d3<<2)|(d4<<3);
}
```

Sendrom 0 ise hata yok. Sıfırdan farklıysa, **değeri tam olarak hatalı bitin konumu**: o biti XOR ile çevir (Ders 5.1), hata düzeldi. Neden konumu veriyor: parite bitleri 2'nin kuvveti konumlarında olduğu için, hatalı bir konumun numarasının her biti, o biti kontrol eden parite kontrolünü bozar; sendromun bitleri birleşince konum numarası çıkar.

Bütün 16 veri değeri ve her 7 bit konumundaki tek-bit hataları için sınadık:

```
Hamming(7,4) tum veri + tek-bit hatalar: 0 hata
```

Her tek-bit hata doğru konumda bulunup düzeltildi. Örnek:

```
veri=0b1011 kod=0x55, bit4 bozuldu=0x5d, duzeltildi konum=4, cozuldu=0b1011
```

Veri `1011` kodlandı; dördüncü bit kasten bozuldu; alıcı sendromla konum 4'ü buldu, düzeltti, orijinal `1011`'i kurtardı — yeniden gönderime gerek yok.

Hamming kodu ECC bellekte (sunucu RAM'i, kozmik ışınların çevirdiği bitleri düzeltir), uydu iletişiminde, QR kodlarında (daha güçlü Reed-Solomon ile) kullanılır. Tek bit düzeltir, çift biti algılar (ek bir parite ile, Hamming(8,4)); daha fazlası için daha güçlü kodlar gerekir.

---

## 3. Algılama ile düzeltme arasındaki fark

| | parite (5.8) | CRC-32 | Hamming(7,4) |
| --- | --- | --- | --- |
| ek bit | 1 | 32 | 3 (4 veriye) |
| ne yapar | 1 bit **algılar** | çok bit **algılar** | 1 bit **düzeltir** |
| yeniden gönderim | gerekir | gerekir | **gerekmez** |
| maliyet | en ucuz | orta (tablo) | orta (fazladan bit) |

Temel ödünleşim: **düzeltmek, algılamaktan daha pahalı** (daha çok ek bit, daha çok hesap). Bir hata ne kadar bilgiyle yakalanırsa, o kadar güçlü düzeltilebilir — ama bedeli fazladan bit. CRC, "bozulduysa haber ver, yeniden iste" senaryosu için (disk, ağ); Hamming, "yeniden isteyemem, yerinde düzelt" senaryosu için (bellek, uzay). İkisi de Ders 5.8'deki paritenin ve XOR'un üzerine kurulu — bit hileleriyle güvenilirlik.

---

## Alıştırmalar

**1** – CRC bit bit döngüsündeki `(crc & 1) ? (crc >> 1) ^ POLY : crc >> 1`'i Ders 5.13'teki kaydır-çıkar bölmeyle karşılaştır. Çıkarma yerine neden XOR? GF(2)'de toplama ve çıkarma neden aynı şey (ikisi de XOR)?

**2** – `crc32_build_table`'ın ürettiği `table[0]`, `table[1]` ve `table[0xFF]` değerlerini hesapla (ya da programı çalıştır). `table[0]` neden 0? Tablo ana döngüyü 8 kat neden hızlandırıyor?

**3** – Hamming(7,4)'te veri `0b1101`'i kodla (`p1`, `p2`, `p4`'ü hesapla). Sonra 3. biti boz, sendromu hesapla, konumun 3 çıktığını ve düzeltmenin veriyi kurtardığını göster.

**4** – Hamming(7,4) **iki** bit birden bozulursa ne olur? Sendrom bir konum gösterir, ama yanlış bir konum — program bozuk olmayan bir biti "düzeltip" veriyi daha da bozar. Bu neden "tek hata düzeltir" ile sınırlı? Çift hatayı **algılamak** için (düzeltmeden) ne eklenir (ipucu: bir genel parite biti, Hamming(8,4))?

**5** – CRC ve Hamming'i birleştir: bir veri bloğuna hem Hamming (tek bit düzeltme) hem CRC (kalan hataları algılama) eklemek neden mantıklı? Hangi senaryoda sadece CRC, hangisinde sadece Hamming yeter? (Disk vs ECC bellek vs derin uzay sondası.)

<details>
<summary>Cevaplar</summary>

**1** – İkisi de "en düşük bit 1 ise bir işlem yap, sonra kaydır" — aynı uzun bölme iskeleti (Ders 5.13). Fark: Ders 5.13 gerçek sayılarda çalıştığı için **çıkarma** (ve ödünç) kullanıyordu; CRC **GF(2)**'de (iki elemanlı alan: 0, 1) çalışır, orada toplama ve çıkarma **aynıdır ve XOR'dur**. Neden: GF(2)'de `1 + 1 = 0` (mod 2), ve `1 - 1 = 0`, `0 - 1 = 1` (mod 2) — hepsi XOR'un tablosu. Elde/ödünç yok (bir bitten öteye taşmaz). Bu yüzden polinom bölmesi, sıradan bölmeden daha basit: sadece XOR ve kaydırma.

**2** – `table[0] = 0`: `c = 0` ile başlayıp 8 kez "en düşük bit 1 ise XOR" — ama `c` hep 0, hiç XOR olmaz, `0 >> 8` = 0. `table[1]`: `c = 1`, sekiz adım sonra `0xD202EF8D` civarı bir değer (polinomun bir fonksiyonu). `table[0xFF]`: `0xFF` için sekiz adım. Tablo 8 kat hızlandırır çünkü bit bit sürümün byte başına 8 adımını (8 kez kaydır+XOR), önceden hesaplayıp tek bir tablo bakışı + XOR'a indirir (Ders 4.11'deki işlem tablosu, Ders 5.8'deki tablo yaklaşımı). Hesabı çalışma anından derleme/başlangıç anına taşımak.

**3** – `0b1101`: `d1=1, d2=0, d3=1, d4=1`. `p1 = 1^0^1 = 0`, `p2 = 1^1^1 = 1`, `p4 = 0^1^1 = 0`. Kod (p1 p2 d1 p4 d2 d3 d4) = `0 1 1 0 0 1 1`. 3. biti (konum 3 = d1) bozarsan `d1` 0 olur. Sendrom: `s1 = bit1^bit3^bit5^bit7`, `s2 = ...`, `s4 = ...` hesaplanınca `011` = 3 çıkar (konum 3). O biti çevir → `d1` geri 1, veri `1101` kurtulur. Sendromun değeri doğrudan hatalı konumu veriyor.

**4** – İki bit bozulursa, Hamming(7,4)'ün sendromu yine sıfırdan farklı bir konum gösterir, ama **yanlış** bir konum (iki hatanın XOR'u bir üçüncü konumu işaret eder). Program o yanlış biti "düzeltir" ve artık **üç** bit yanlış olur — veri daha da bozulur, ve hata sessizce geçer. Bu yüzden Hamming(7,4) sadece **tek** hata düzeltir (SEC: single error correcting). Çift hatayı **algılamak** için (düzeltmeden) bir **genel parite biti** eklenir — bütün 7 bitin paritesi, 8. bit (Hamming(8,4), SECDED: single error correct, double error detect). İki hata olunca genel parite tutar ama sendrom sıfırdan farklıdır → "çift hata, düzeltemem" denir, veri yeniden istenir.

**5** – Hamming + CRC katmanlı: Hamming tek-bit hataları yerinde düzeltir (en sık hata), CRC ise Hamming'in düzeltemediği (çift+) hataları yakalar — düzeltilemeyeni en azından **algılar**, böylece bozuk veri sessizce kabul edilmez. **Sadece CRC**: disk ve ağ — hata olunca yeniden okumak/istemek ucuz, düzeltmeye gerek yok. **Sadece Hamming**: ECC bellek — her okumada yeniden "isteyemezsin", tek-bit hatalar (kozmik ışın) sık ve yerinde düzeltilmeli. **İkisi birden**: derin uzay sondası — yeniden gönderim saatler sürer (ışık hızı gecikmesi), hem mümkün olduğunca düzeltmek (güçlü kodlar) hem kalanı algılamak gerekir; orada Hamming'den çok daha güçlü Reed-Solomon/turbo kodlar + CRC kullanılır. Ödünleşim her zaman: düzeltme gücü vs ek bit ve hesap maliyeti.

</details>

---

## Kaynaklar

- Richard Hamming, "Error Detecting and Error Correcting Codes" (Bell System Technical Journal, 1950): Hamming kodunun kökeni.
- W. Wesley Peterson & D. T. Brown, "Cyclic Codes for Error Detection" (1961): CRC.
- Ross Williams, "A Painless Guide to CRC Error Detection Algorithms" (1993): CRC'nin ayrıntılı anlatımı.
- Henry Warren, *Hacker's Delight* (2. baskı), §14.3: CRC ve bit düzeyinde uygulaması.

**Sıradaki ders:** Faz projesi. Bitset kütüphanesi ve satranç tahtasında at hamlelerini bit işlemleriyle üreten bitboard.
