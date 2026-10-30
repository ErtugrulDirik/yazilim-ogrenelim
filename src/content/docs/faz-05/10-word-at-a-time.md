---
title: "5.10 Word-at-a-time"
description: "Bir string'i byte byte değil, 8 byte'lık word'ler halinde işlemek: bir word'de sıfır byte olup olmadığını tek bir (v - ONES) & ~v & HIGHS ifadesiyle bulma formülü ve neden çalıştığı, Faz 4'teki strlen'i word word okuyarak 8 kat hızlandırma, hizaya gelme zorunluluğu, ve bu tekniğin string'in mantıksal sonunu kasıtlı aşmasının neden Ders 4.13'teki 'libc nasıl taşmıyor' sorusunun cevabı olduğu."
---

Ders 4.13'te kendi `strlen`'imizi byte byte yazmış, standart sürümün 15 kat hızlı olduğunu görmüş ve "Faz 5'te word word okuyarak hızlandıracağız" demiştik. Ayrıca "standart `strlen` nasıl yazının dışını okumadan 16 byte'lık parçalarla çalışıyor?" diye sormuş, cevabı buraya bırakmıştık. Bu ders ikisini de yanıtlıyor.

Fikir: bir string'i karakter karakter (byte byte) taramak yerine, **8 byte'ı aynı anda** (bir 64-bit word olarak) okuyup içinde `'\0'` olup olmadığını bit işlemleriyle anlamak. Doğru yapılırsa 8 kat hız; ama kasıtlı olarak yazının sonunu aştığı için tehlikeli — ve o tehlike, Ders 4.13'teki sorunun ta kendisi.

---

## 1. Bir word'de sıfır byte var mı?

Elimizde 8 byte'lık bir word var; içindeki herhangi bir byte 0 mı? Her byte'ı tek tek kontrol etmek (`& 0xFF`, kaydır, tekrar) işi yavaşlatır — amacımız tam bundan kaçınmak. Warren'ın (*Hacker's Delight*) formülü, hepsini **tek bir ifadede** yapıyor:

```c
#define ONES  0x0101010101010101ull   // her byte'in en dusuk biti
#define HIGHS 0x8080808080808080ull   // her byte'in en yuksek biti

int has_zero_byte(uint64_t v) {
    return ((v - ONES) & ~v & HIGHS) != 0;
}
```

```
has_zero(0x0102030405060708) = 0   (hic sifir byte yok)
has_zero(0x0102030400060708) = 1   (ortada bir 00 var)
```

Neden çalışıyor, tek bir byte üzerinden düşünelim (formül 8 byte'ı paralel, SWAR tarzı, Ders 5.8 yapıyor):

- **`v - ONES`**: her byte'tan 1 çıkarır. Bir byte 0 ise, çıkarma ödünç alır (Ders 5.3) ve o byte `0xFF` olur — en yüksek biti 1. Byte sıfırdan farklıysa, en yüksek biti genelde 1 olmaz.
- **`& ~v`**: `~v`, byte 0 iken en yüksek biti 1 (çünkü `v`'de 0'dı). Bu, "byte gerçekten 0'dı" durumunu, "byte zaten 0x80+ idi" durumundan ayırır: sadece **başlangıçta** en yüksek biti 0 olan byte'lar geçer.
- **`& HIGHS`**: sadece her byte'ın en yüksek bitine bak. Sonuç sıfırdan farklıysa, en az bir byte 0 demektir.

Üç işlem, bir word'deki 8 byte'ı aynı anda sınar. (Küçük bir yanlış-pozitif payı var — `0x01`–`0x80` arası bazı byte'lar için — ama sıfır byte her zaman yakalanır; onay için o word byte byte kontrol edilir.)

---

## 2. Word word strlen

Formülü `strlen`'e takıyoruz: word word tara, bir word'de sıfır byte bulununca o word'ün içinde byte byte dur.

```c
size_t strlen_word(const char *s) {
    const char *p = s;
    // 1. Hizaya gel (byte byte)
    while ((uintptr_t)p & 7) {
        if (*p == '\0') return (size_t)(p - s);
        p++;
    }
    // 2. Word word tara
    const uint64_t *w = (const uint64_t *)p;
    while (!has_zero_byte(*w)) {
        w++;
    }
    // 3. Sifir byte bu word'de; byte byte bul
    p = (const char *)w;
    while (*p != '\0') {
        p++;
    }
    return (size_t)(p - s);
}
```

Üç aşama:

1. **Hizaya gel**: `s` 8'in katı bir adreste başlamayabilir. `(uintptr_t)p & 7` (Ders 5.7'deki hizalama testi) 0 olana kadar byte byte ilerle. Bu arada `'\0'` bulursak zaten bittik. Hizalama **neden şart**, birazdan.
2. **Word word tara**: artık `p` 8 hizalı; onu `uint64_t *` olarak oku (Ders 4.5'teki pointer tipi), her word'de 8 byte'ı bir anda sına. Sıfır byte yoksa bir sonraki word'e atla — her adımda 8 byte ilerliyoruz.
3. **Son word'de byte byte**: sıfır byte'ın hangi word'de olduğunu bulduk; o word'ün içinde tam yerini byte byte (ya da Ders 5.9'daki `ntz` ile) buluyoruz.

Doğru çalışıyor (kısa ve uzun yazılarda standart `strlen` ile aynı). Hızı?

```
byte:  0.049 s   20 GB/s
word:  0.006 s  155 GB/s      <- 8 kat hizli
libc:  0.021 s   48 GB/s
```

Byte byte sürüm (Ders 4.13) saniyede 20 GB; word word sürüm **155 GB** — tam 8 kat, çünkü her döngü turunda 8 byte işliyor. Ders 4.13'te byte byte sürümümüzün libc'den 15 kat yavaş olduğunu görmüştük; word-at-a-time o farkı kapatıp geçti bile. (Faz 11'de SIMD ile 16-32 byte'ı bir anda işleyip daha da hızlandıracağız.)

---

## 3. Hizalama neden şart — ve Ders 4.13'ün cevabı

Aşama 1'deki hizalama sadece hız için değil, **güvenlik** için. İşte Ders 4.13'te sorduğumuz sorunun cevabı.

Word word okurken, string'in son byte'ı bir word'ün ortasındaysa, o word'ün **kalan byte'larını da okuyoruz** — yani yazının mantıksal sonunu (`'\0'`'dan sonrasını) kasıtlı aşıyoruz. Ders 4.1 ve 4.12'de bunun bir **sınır dışı okuma** olduğunu söylemiştik. Peki neden çökmüyor?

Çünkü word'ler **hizalı** okunuyor. İşletim sistemi belleği sayfalarla (Ders 4.21; 4 KB ya da 16 KB) yönetir, ve sayfa boyutu 8'in katı. 8 hizalı bir adresten okunan 8 byte, **asla iki sayfanın arasına düşmez**: hepsi aynı sayfada. Yani yazının son byte'ı geçerli bir sayfadaysa, aynı word'deki fazladan byte'lar da o sayfada — okumak çökmez. Fazladan okunan byte'lar sonuca karışmaz (sıfır byte'ı bulduğumuzda duruyoruz). Hizalama, "sayfa sınırını aşma" garantisini veriyor.

**Ama bu, C standardına göre hâlâ undefined behavior** (bir array'in sonunu aşmak). AddressSanitizer bu kodu derleyip çalıştırırsak **yakalar**:

```
ERROR: AddressSanitizer: global-buffer-overflow
READ of size 8 ... '.str' is ascii string '' ... of size 1
```

ASan, "bu 8 byte'lık okuma 1 byte'lık bir string'i aşıyor" diyor — ve teknik olarak haklı. Word-at-a-time, standardın **sana** vermediği, ama donanımı ve işletim sistemini bilen kütüphane yazarının (hizalama + sayfa garantisiyle) alabildiği bir risk. Bu yüzden gerçek `strlen`:

- Genellikle **el yazması assembly** ya da özel derleyici işaretleriyle yazılır (ASan'ın "bu fonksiyon bilerek böyle" diye tanıdığı).
- Senin sıradan C ile yazdığın word-at-a-time, ASan'la test edilen bir programda hata verir.

Ders 4.13'teki "libc nasıl taşmadan 16 byte okuyor?" sorusunun tam cevabı bu: **taşıyor, ama hizalı okuyarak sayfa sınırını aşmadığı için çökmüyor, ve bunu C standardının dışında, makineyi bilerek yapıyor.** Sen kendi kodunda bu numarayı kullanacaksan, hizalamayı garantilemen ve ASan'ın neden şikâyet ettiğini bilmen gerekir.

---

## 4. Aynı fikir başka yerlerde

Word-at-a-time sadece `strlen` için değil. Bir word'de belirli bir byte'ı aramak (`memchr`), iki bloğu karşılaştırmak (`memcmp`), boşluk aramak — hepsi aynı kalıpla hızlandırılır: 8 byte'ı bir word olarak oku, bit işlemleriyle sına. Formülün çeşitleri:

- **Belirli bir byte `c` var mı?**: önce `v ^= c * ONES` (her byte'tan `c` çıkar, aranan byte 0 olur), sonra sıfır byte formülü.
- **Hangi byte sıfır?**: `has_zero_byte`'ın ürettiği maskeye `ntz` (Ders 5.9) uygulayıp byte konumunu doğrudan bulmak (byte byte dönmeden).

Bu teknikler, Ders 4.18'de yazdığımız `mem*` fonksiyonlarının gerçek, hızlı sürümlerinin temeli. Faz 11'de aynı fikri SIMD komutlarıyla (`pcmpeqb` + `pmovmskb`) 16-32 byte'a taşıyacağız; word-at-a-time, SIMD'in register'la yapılan ilk hali.

---

## Alıştırmalar

**1** – `has_zero_byte`'ı `0x4100000042000000` (içinde iki sıfır byte var) ve `0x4142434445464748` (hiç yok) için izle. `v - ONES`, `~v` ve `HIGHS` adımlarını 64 bitlik olarak değil, kavramsal olarak (hangi byte'lar 0) açıkla.

**2** – `strlen_word`'ün 1. aşamasını (hizaya gelme) kaldırırsan ne olur? Hizasız bir adresten `uint64_t` okumak bu makinede çöker mi, yavaşlar mı (Ders 4.26)? Neden ASan olmadan "çalışıyor gibi" görünebilir?

**3** – Belirli bir byte `c`'yi arayan `has_byte(uint64_t v, uint8_t c)` yaz: `v`'yi `c * ONES` ile XOR'layıp `has_zero_byte`'a ver. Neden XOR aranan byte'ı 0'a çeviriyor (Ders 5.1)? Bu, `memchr`'ın word-at-a-time hali.

**4** – Word-at-a-time `strlen`'i ASan ile derleyip bir `malloc`'lu, sonu 8'e kadar sıfırla doldurulmuş tamponda çalıştır. ASan hâlâ şikâyet eder mi? Tamponu `strlen(s) + 1`'e göre değil de 8'in katına yuvarlayıp ayırmak (Ders 5.7) neden ASan'ı susturur ama yine de standart dışıdır?

**5** – 3. aşamada byte byte aramak yerine, `has_zero_byte`'ın ürettiği maskeden sıfır byte'ın konumunu `__builtin_ctz` (Ders 5.9) ile doğrudan bulan bir sürüm düşün. Little-endian'da (Ders 3.9) en düşük adresli byte, word'ün en düşük byte'ı mı? Bu neden `ntz`'yi doğru byte'a çevirmeyi endianness'a bağımlı yapar?

<details>
<summary>Cevaplar</summary>

**1** – `0x4100000042000000`: byte'lar (yüksekten düşüğe) `41 00 00 00 42 00 00 00` — birkaç sıfır byte var. `v - ONES`: sıfır olan byte'lar ödünç alıp `0xFF` olur (en yüksek bit 1); `~v`: sıfır byte'ların her biti 1, en yüksek bit 1; `& HIGHS`: sıfır byte'ların en yüksek bitleri sağ kalır → sonuç sıfırdan farklı, "sıfır byte var". `0x4142434445464748`: bütün byte'lar sıfırdan farklı (`41`-`48`); hiçbiri `v - ONES`'ta en yüksek biti 1 yapacak şekilde taşmaz, `& HIGHS` sonrası 0 → "sıfır byte yok". Formül, "bir byte 0 ise çıkarma onu 0xFF yapar" gözlemini 8 byte için paralel uyguluyor.

**2** – Hizaya gelme kaldırılırsa, `s` hizasız bir adreste başlarsa `(const uint64_t *)p`'den okuma **hizasız** olur. ARM ve x86'da bu **çökmez ama yavaşlar** (Ders 4.26: donanım hizasız erişimi destekler, fazladan iş yaparak); bazı eski/gömülü mimarilerde çökerdi. ASan olmadan "çalışıyor gibi" görünür çünkü sonuç doğru çıkar (sadece yavaş), ve çöken bir mimaride test edilmedikçe fark edilmez. Hizalama hem taşınabilirlik (çökmeyen) hem hız (sayfa sınırını aşmayan, Bölüm 3) için.

**3** –

```c
int has_byte(uint64_t v, uint8_t c) {
    uint64_t x = v ^ (c * ONES);   // her byte'tan c "cikar"
    return ((x - ONES) & ~x & HIGHS) != 0;
}
```

`c * ONES`, her byte'ı `c` yapar (`ONES = 0x0101...`, `c` ile çarpınca her byte `c`). `v ^ (c * ONES)`: `v`'nin `c`'ye eşit olan byte'ları 0 olur (`c ^ c = 0`; Ders 5.1), diğerleri sıfırdan farklı. Sonra sıfır byte formülü, "0 olan byte var mı" = "`c`'ye eşit byte var mı" sorusuna döner. Bu, `memchr`'ın word-at-a-time çekirdeği: XOR ile aranan byte'ı sıfıra çevir, sıfır byte bul.

**4** – ASan büyük ihtimalle **yine şikâyet eder**: `malloc(strlen(s) + 1)` sadece yazı + `'\0'` kadar yer ayırır, word okuma onu aşar. Tamponu 8'in katına yuvarlayıp ayırmak (`malloc(align_up(len + 1, 8))`) ASan'ı **susturur**, çünkü artık okunan word'ün bütün byte'ları ayrılmış bloğun içinde — ASan "bu byte ayrılmış mı" diye bakar, hepsi ayrılmış görünür. Ama **yine standart dışı**: C standardına göre string `'\0'`'da biter, ondan sonrasını okumak (ayrılmış olsa bile mantıken string'in dışı) tanımsız; sen sadece ASan'ı tatmin ettin, standardı değil. "Çalışıyor ve ASan temiz" ile "standarda uygun" aynı şey değil.

**5** – Little-endian'da (Ders 3.9) bir word'ün en **düşük adresli** byte'ı, sayının en **düşük değerli** (en sağdaki) byte'ıdır. `has_zero_byte` maskesinde en düşük değerli byte'taki işaret biti, en düşük adresteki (string'de en önce gelen) byte'a karşılık gelir; `__builtin_ctz` (en sağdaki 1'in konumu) o maskede en düşük set biti bulur, `/ 8` ile byte konumuna çevrilir — ve bu, little-endian'da string'deki **ilk** sıfır byte'ı doğru verir. Big-endian'da ise en düşük adresli byte en **yüksek** değerli byte olur, bu yüzden `ctz` değil `clz` (Ders 5.9) gerekir, ve maske bitleri ters eşlenir. Yani "maskedeki bit konumu → string'deki byte konumu" dönüşümü endianness'a bağlı; taşınabilir word-at-a-time kodu bunu ayrıca ele almak zorunda.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §6.1: "Find First 0-Byte" ve word-at-a-time teknikleri.
- glibc `strlen` kaynağı (sysdeps): gerçek word-at-a-time ve SIMD uygulamaları.
- Ders 4.13 (strlen sıfırdan): byte byte sürüm ve "libc nasıl taşmıyor" sorusu.
- Mike Pall, "Word-at-a-time string operations": tekniğin ayrıntılı anlatımı.

**Sıradaki ders:** Bitleri yeniden düzenleme. Bit reverse, perfect shuffle ve 8×8 bit matrisi transpozu.
