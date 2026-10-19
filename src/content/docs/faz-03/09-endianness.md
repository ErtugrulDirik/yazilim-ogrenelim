---
title: "3.9 Endianness"
description: "Çok byte'lık bir sayının byte'ları bellekte hangi sırayla durur? Little ve big endian, bir uint32_t'yi byte byte okumak, hangi işlemcinin hangisini kullandığı, dosya formatlarında ve ağda byte sırası, makineden bağımsız okuyup yazan fonksiyonlar, htonl ve ntohl."
---

Bir `uint32_t` 4 byte yer kaplar (Ders 3.4). Peki o 4 byte, bellekte **hangi sırayla** durur?

Soru tuhaf görünebilir; bir sayının "doğal" bir sırası var gibi. 1.234 yazarken en büyük basamaktan başlarız. Ama bilgisayar için böyle bir zorunluluk yok, ve bugün kullandığın bilgisayarın cevabı büyük ihtimalle senin beklediğinin **tersi**.

---

## 1. Bir sayının byte'ları

Önce sayının kendisine bakalım. Ondalık bir sayıyı basamaklarına ayırırken 10'a böleriz (Ders 2.8). Bir sayıyı **byte'larına** ayırmak da aynı fikir, sadece taban 10 değil 256: her byte 0 ile 255 arasında bir "basamak".

Bu ders boyunca kullanacağımız sayı: **16.909.060**. Neden bu sayı?

16.909.060 = **1** × 256³ + **2** × 256² + **3** × 256 + **4**

Yani 256 tabanında "1 2 3 4". (Ders 3.10'da bu sayıyı çok daha okunaklı bir şekilde, `0x01020304` diye yazmayı öğreneceğiz.) Byte'larını bölme ve kalanla bulabiliriz:

| Byte | Hesap | Değer | Basamak değeri |
| --- | --- | --- | --- |
| En anlamlı | `x / 16777216 % 256` | 1 | 256³ = 16.777.216 |
| | `x / 65536 % 256` | 2 | 256² = 65.536 |
| | `x / 256 % 256` | 3 | 256 |
| En anlamsız | `x % 256` | 4 | 1 |

Ondalıktaki "en büyük basamak" ve "birler basamağı" gibi, bunlara **en anlamlı byte** (most significant byte, MSB) ve **en anlamsız byte** (least significant byte, LSB) denir. En anlamlı byte'taki bir değişiklik sayıyı 16 milyon değiştirir; en anlamsızdaki sadece 1.

Bu hesaplar **değerle** yapılıyor; sayının bellekte nasıl durduğundan bağımsız. Her bilgisayarda "1 2 3 4" verirler.

---

## 2. Bellekte bakmak

Şimdi aynı sayının bellekte gerçekten nasıl durduğuna bakalım. Bunun için sayının 4 byte'ını, olduğu gibi, 4 elemanlı bir `uint8_t` array'ine **kopyalayacağız**:

```c
#include <stdio.h>
#include <stdint.h>
#include <string.h>

int main(void) {
    uint32_t x = 16909060;
    uint8_t bytes[4];
    memcpy(bytes, &x, sizeof(x));

    printf("Değerden:  %d %d %d %d\n",
           x / 16777216 % 256, x / 65536 % 256, x / 256 % 256, x % 256);
    printf("Bellekten: %d %d %d %d\n", bytes[0], bytes[1], bytes[2], bytes[3]);
    return 0;
}
```

`memcpy(hedef, kaynak, kaç_byte)`, `<string.h>`'teki bir fonksiyon: kaynaktaki byte'ları hiç yorumlamadan hedefe kopyalar. `&x` yine Ders 2.13'teki `scanf`'te gördüğümüz `&`: burada "`x`'in bellekteki yeri" anlamında. Şimdilik ikisini de kara kutu olarak kullanıyoruz; Faz 4'te pointer'ları öğrenince `memcpy`'yi kendimiz yazacağız.

Bilgisayarımızda (Apple Silicon) çıktı:

```
Değerden:  1 2 3 4
Bellekten: 4 3 2 1
```

Byte'lar bellekte **ters** sırada duruyor: belleğin ilk byte'ında en anlamsız byte (4), son byte'ında en anlamlı byte (1) var.

İki düzen var ve ikisinin de adı var:

| Düzen | Bellekteki ilk byte | 16.909.060 bellekte |
| --- | --- | --- |
| **Little endian** | En anlamsız byte | `4 3 2 1` |
| **Big endian** | En anlamlı byte | `1 2 3 4` |

"Little endian": sayının **küçük ucu** başta. "Big endian": **büyük ucu** başta. Big endian, kâğıda yazdığımız sıraya benziyor; little endian ise tersi.

İsimler, Jonathan Swift'in *Gulliver'in Gezileri*'nden geliyor: Lilliput'ta haşlanmış yumurtayı küçük ucundan kıranlarla (little-endians) büyük ucundan kıranlar (big-endians) arasında savaşlar çıkar. Danny Cohen 1980'de yazdığı bir yazıda bu iki düzen arasındaki tartışmanın da aynı kadar anlamsız olduğunu söylemek için bu isimleri kullandı. İkisinin de birbirine bir üstünlüğü yok; önemli olan herkesin aynı düzende anlaşması.

### Değer ve bellek, iki ayrı şey

Bu dersin en önemli fikri: Bölüm 1'deki **değerle** yapılan hesaplar (bölme, kalan, ileride Faz 5'teki bit kaydırma) endianness'tan **etkilenmez**. `x % 256` her makinede en anlamsız byte'ı verir. Endianness sadece byte'lara **bellek üzerinden** baktığında ortaya çıkar: `memcpy` ile kopyaladığında, bir dosyaya ya da ağa ham byte'lar olarak yazdığında, Faz 4'te bir pointer ile byte byte okuduğunda.

Ders 3.7'deki dönüşümler de değerle çalışır. `(uint8_t)x`, endianness ne olursa olsun en anlamsız byte'ı, yani 4'ü verir.

---

## 3. Hangi işlemci hangisi?

Aynı küçük fonksiyonu clang ile farklı işlemciler için derleyip, belleğin ilk byte'ı olarak ne döndürdüğüne baktık:

```c
int first_byte(void) {
    uint32_t x = 16909060;
    uint8_t bytes[4];
    memcpy(bytes, &x, sizeof(x));
    return bytes[0];
}
```

| İşlemci | Nerede? | İlk byte | Düzen |
| --- | --- | --- | --- |
| x86-64 | Çoğu masaüstü ve dizüstü, sunucular | 4 | Little |
| ARM64 | Telefonlar, Apple Silicon, Raspberry Pi | 4 | Little |
| RISC-V | Gömülü sistemler, yeni çıkan kartlar | 4 | Little |
| PowerPC 64 (little) | IBM sunucuları, yeni Linux sürümleri | 4 | Little |
| PowerPC 64 (big) | IBM sunucuları, eski sürümler | 1 | **Big** |
| IBM Z (s390x) | Bankaların ana bilgisayarları | 1 | **Big** |

Compiler, sabit bir sayının byte'larını derleme sırasında hesapladı; her hedefte fonksiyon tek bir sayı döndürüyor (x86'da `mov eax, 4`, s390x'te `lghi %r2, 1`).

Bugün yazdığın kodun çalışacağı makinelerin neredeyse hepsi little endian. ARM ve PowerPC aslında iki düzeni de destekler (**bi-endian**), ama ARM'ı kullanan neredeyse bütün sistemler little endian modunu seçer. Peki big endian'ı neden öğreniyoruz? Çünkü byte'lar makinenin dışına çıktığında hâlâ her yerde karşımıza çıkıyor.

---

## 4. Byte'lar makineden çıkınca

Byte'lar bellekte kaldığı sürece endianness'ı hiç düşünmezsin: aynı makine yazıp aynı makine okur. Sorun, byte'lar başka bir yere gittiğinde başlar: bir **dosyaya** ya da **ağ** üzerinden başka bir makineye.

Bir makinenin 16.909.060 sayısını `memcpy` ile ham byte'larına ayırıp gönderdiğini düşün. Little endian bir makine `4 3 2 1` gönderir. Big endian bir makine bu byte'ları kendi düzeniyle okursa:

4 × 256³ + 3 × 256² + 2 × 256 + 1 = **67.305.985**

Aynı 4 byte, iki makinede iki farklı sayı. Bu yüzden her dosya formatı ve her ağ protokolü, çok byte'lık sayıların hangi sırayla yazılacağını **açıkça** belirtir:

- **Big endian:** İnternetin temel protokolleri (IP, TCP, UDP), PNG ve JPEG resimleri, Java'nın `.class` dosyaları.
- **Little endian:** BMP resimleri, WAV ses dosyaları, ZIP arşivleri.

### Makineden bağımsız okumak ve yazmak

Doğru yol: byte'ları `memcpy` ile değil, Bölüm 1'deki gibi **değerle** üretmek ve okumak. O zaman kodun, üzerinde çalıştığı makinenin endianness'ından hiç etkilenmez.

```c
#include <stdio.h>
#include <stdint.h>

void write_be32(uint8_t out[], uint32_t x) {
    out[0] = (uint8_t)(x / 16777216);
    out[1] = (uint8_t)(x / 65536 % 256);
    out[2] = (uint8_t)(x / 256 % 256);
    out[3] = (uint8_t)(x % 256);
}

uint32_t read_be32(uint8_t in[]) {
    return (uint32_t)in[0] * 16777216 + (uint32_t)in[1] * 65536
         + (uint32_t)in[2] * 256 + in[3];
}

uint32_t read_le32(uint8_t in[]) {
    return (uint32_t)in[3] * 16777216 + (uint32_t)in[2] * 65536
         + (uint32_t)in[1] * 256 + in[0];
}

int main(void) {
    uint8_t packet[4];
    write_be32(packet, 16909060);
    printf("%d %d %d %d\n", packet[0], packet[1], packet[2], packet[3]);
    printf("%u\n", read_be32(packet));
    printf("%u\n", read_le32(packet));
    return 0;
}
```

```
1 2 3 4
16909060
67305985
```

- `write_be32`, sayıyı big endian düzende, en anlamlı byte başta olacak şekilde yazıyor. Bu kod her makinede `1 2 3 4` üretir.
- `read_be32`, byte'ları 256 tabanında bir sayı gibi soldan sağa okuyor. `read_le32` aynı işi sağdan sola yapıyor. Aynı byte'lara yanlış düzenle bakınca yine 67.305.985 çıkıyor.
- `read_be32`'deki cast'ler Ders 3.5'ten: `in[0]` bir `uint8_t`, cast olmasa `int`'e yükseltilirdi ve 255 × 16.777.216 `int`'e sığmazdı. `(uint32_t)` ile çarpma işaretsiz 32 bitle yapılıyor.
- `write_be32`'deki `(uint8_t)` cast'leri Ders 3.7'den: değerin 0–255 arasında olduğunu biliyoruz; cast bunu söylüyor ve `-Wconversion`'ı susturuyor.

Faz 5'te bit kaydırmayı öğrenince bu fonksiyonları çok daha kısa yazacağız (`x / 16777216` yerine `x >> 24`), ama fikir aynı kalacak.

### Ağ byte sırası: htonl ve ntohl

İnternet protokollerindeki big endian düzene **ağ byte sırası** (network byte order) denir; makinenin kendi düzenine de **makine byte sırası** (host byte order). POSIX sistemlerde (macOS, Linux) `<arpa/inet.h>` ikisi arasında çeviren hazır fonksiyonlar sunar:

| Fonksiyon | Okunuşu | Ne yapar? |
| --- | --- | --- |
| `htonl(x)` | **h**ost **to** **n**etwork, **l**ong (32 bit) | Makine sırasından ağ sırasına |
| `ntohl(x)` | **n**etwork **to** **h**ost, **l**ong | Ağ sırasından makine sırasına |
| `htons(x)`, `ntohs(x)` | **s**hort (16 bit) | Aynısı, 16 bitlik sayılar için |

(Buradaki "long" ve "short", C'nin tipleri değil; bu fonksiyonlar `long`'un her yerde 32 bit olduğu sanılan zamanlardan kalma isimler. Gerçekte `uint32_t` ve `uint16_t` ile çalışırlar.)

```c
#include <arpa/inet.h>

printf("%u\n", htonl(16909060));
printf("%u\n", ntohl(htonl(16909060)));
```

```
67305985
16909060
```

Little endian bilgisayarımızda `htonl` byte'ları ters çevirdi: sonucun bellekteki byte'ları artık `1 2 3 4`, ama değer olarak okununca 67.305.985. Big endian bir makinede `htonl` hiçbir şey yapmaz, çünkü makine sırası zaten ağ sırasıdır. Ağ programlamayı Faz 10'da göreceğiz. (Windows'ta bu fonksiyonlar `<winsock2.h>`'te.)

---

## 5. Makinenin düzenini öğrenmek

Bölüm 2'deki fikirle, çalışma sırasında:

```c
int is_little_endian(void) {
    uint32_t one = 1;
    uint8_t bytes[4];
    memcpy(bytes, &one, sizeof(one));
    return bytes[0] == 1;
}
```

1'in en anlamsız byte'ı 1, diğerleri 0. Bellekteki ilk byte 1 ise makine little endian.

Derleme sırasında ise clang ve GCC'nin tanımladığı bir makroyla, Ders 2.11'deki `#ifndef`'in kardeşi `#if` ile:

```c
#if __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__
    // little endian
#else
    // big endian
#endif
```

C23 standardı aynı bilgiyi `<stdbit.h>` başlığında `__STDC_ENDIAN_NATIVE__` adıyla standartlaştırdı, ama bu başlık henüz her sistemde yok (macOS'ta bulamadık).

Ama çoğu zaman bunlara ihtiyacın olmaz. Bölüm 4'teki gibi byte'ları değerle okuyup yazan kod, **hangi makinede çalıştığını bilmek zorunda değildir**. En iyi endianness kodu, endianness'ı hiç sormayan koddur.

---

## Alıştırmalar

**1** – 258 sayısını `uint16_t` olarak düşün. Byte'ları neler? Little endian ve big endian bir makinenin belleğinde hangi sırayla durur? Aynı sayı `uint32_t` olsaydı?

**2** – `write_le32(uint8_t out[], uint32_t x)` fonksiyonunu yaz. Sonra `write_le32` ile yazıp `read_le32` ile okuyarak 0, 255, 256, 16.909.060 ve 4.294.967.295 için aynı sayıyı geri aldığını kontrol et.

**3** – Bir BMP resim dosyasının başlığında, resmin genişliği, dosyanın başından 18 byte sonra başlayan 4 byte'ta (byte'ları 0'dan sayarsak 18, 19, 20 ve 21. byte'lar), little endian olarak yazılıdır. Bir dosyada bu dört byte sırasıyla `0 4 0 0`. Resim kaç piksel genişliğinde? Big endian sanıp okusaydın kaç bulurdun?

**4** – 16 bitlik bir sayının iki byte'ının yerini değiştiren `uint16_t swap16(uint16_t x)` fonksiyonunu yaz (`memcpy` kullanmadan, değerle). `swap16(258)` kaç verir? `swap16(swap16(x))` her zaman `x` mi?

**5** – Bir arkadaşın, kendi bilgisayarında `uint32_t` dizisini olduğu gibi (`memcpy` ile ham byte'larıyla) bir dosyaya yazıp tekrar okuyan bir program yazmış: "Her seferinde doğru çalışıyor, endianness diye bir sorunum yok." Haklı mı? Hangi durumda sorun çıkar?

<details>
<summary>Cevaplar</summary>

**1** – 258 = 1 × 256 + 2. En anlamlı byte 1, en anlamsız 2.

- `uint16_t`: little endian'da `2 1`, big endian'da `1 2`.
- `uint32_t`: 258 = 0 × 256³ + 0 × 256² + 1 × 256 + 2. Little endian'da `2 1 0 0`, big endian'da `0 0 1 2`.

**2** –

```c
void write_le32(uint8_t out[], uint32_t x) {
    out[0] = (uint8_t)(x % 256);
    out[1] = (uint8_t)(x / 256 % 256);
    out[2] = (uint8_t)(x / 65536 % 256);
    out[3] = (uint8_t)(x / 16777216);
}
```

`write_be32`'nin aynısı, sadece byte'lar ters sırada. Beş sayının hepsi geri gelmeli. 4.294.967.295'in dört byte'ı da 255.

**3** – `read_le32` ile: 0 + 4 × 256 + 0 + 0 = **1.024** piksel. Big endian sanıp okusaydın: 0 × 256³ + 4 × 256² + 0 + 0 = **262.144** piksel. Gerçek dosya okuyan programlarda bu tür bir hata, resmin bozuk görünmesine ya da program çok büyük bir bellek ayırmaya çalışırken çökmesine yol açar.

**4** –

```c
uint16_t swap16(uint16_t x) {
    return (uint16_t)(x % 256 * 256 + x / 256);
}
```

En anlamsız byte en anlamlı byte'ın yerine (× 256), en anlamlı byte da en anlamsızın yerine (/ 256) geçiyor. `swap16(258)` = 2 × 256 + 1 = **513**. Evet, iki kez yer değiştirmek her byte'ı yerine geri koyar; `swap16(swap16(x))` her zaman `x`'tir. (`x % 256 * 256` `int` ile hesaplanır ve en fazla 65.280 olur; sığar. Sonucu `uint16_t`'ye çevirmek de değeri değiştirmez, çünkü toplam en fazla 65.535.)

**5** – Kendi bilgisayarında haklı: aynı makine yazıp aynı makine okuduğu için byte sırası hep tutarlı. Sorun, dosya **başka bir makineye** gittiğinde çıkar: big endian bir makine (örneğin bir IBM Z sunucusu) o dosyayı okursa her sayıyı farklı okur. Dosya formatı bir byte sırası belirtmiyorsa, dosya sadece onu yazan türden makinelerde anlamlıdır. Doğrusu, formatın düzenini seçip (örneğin little endian) `write_le32` ve `read_le32` gibi değerle çalışan fonksiyonlar kullanmak. (`uint32_t`'nin her platformda 4 byte olması bu sorunun yarısını zaten çözüyor; Ders 3.4. `int` kullansaydı boyut da değişebilirdi.)

</details>

---

## Kaynaklar

- Danny Cohen, "On Holy Wars and a Plea for Peace", IEN 137, 1980: little endian ve big endian terimlerinin kaynağı.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.1.3: byte sırası ve bir nesnenin byte'larını yazdırmak.
- RFC 1700 ve RFC 791: ağ byte sırasının big endian olarak belirlenmesi.
- POSIX, `<arpa/inet.h>`: `htonl`, `htons`, `ntohl`, `ntohs`.

**Sıradaki ders:** Sayı sabitleri. `0x`, `0b` ve `U`, `L` ekleri; bir sabitin tipi nasıl belirlenir?
