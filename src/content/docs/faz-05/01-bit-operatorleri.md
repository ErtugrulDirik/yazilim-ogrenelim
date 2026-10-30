---
title: "5.1 Bit operatörleri"
description: "C'nin altı bit operatörü: & | ^ ~ << >>. Her birinin doğruluk tablosu, XOR'un tersinirliği ve XOR ile takas, ~ ile tümleyen, işaretsizde mantıksal ve işaretlide aritmetik sağa kaydırma farkı, kaydırmanın undefined behavior durumları (genişliğe eşit/aşan sayı, negatif sayı, işaret bitine sola kaydırma) ve & operatörünün == karşısındaki düşük önceliği."
---

Ders 3.18'de bitlere bakmak için dört operatörü (`<<`, `>>`, `&`, `|`) tanımış, bir sayıyı ikilik ve onaltılık tabanda yazdırmıştık ve "bütün ayrıntılarını Faz 5'te göreceğiz" demiştik. Bu faz boyunca bitlerle hesap yapacağız: saymak, maskelemek, dalsız kod yazmak, çarpmayı ve bölmeyi bitlerle kurmak. Önce aletleri tam tanıyoruz: C'nin **altı** bit operatörü ve her birinin kesin tanımı.

Bu fazda sayıları hep **bit desenleri** olarak düşüneceğiz. Çoğu zaman `unsigned` tiplerle çalışacağız, çünkü birazdan göreceğimiz gibi işaretli sayılarda bazı işlemler tanımsız; `unsigned` bit desenleri için en güvenli zemin.

---

## 1. Altı operatör

| Operatör | Adı | Ne yapar |
| --- | --- | --- |
| `&` | VE (AND) | iki bit de 1 ise 1 |
| `\|` | VEYA (OR) | en az biri 1 ise 1 |
| `^` | ÖZEL VEYA (XOR) | bitler **farklı** ise 1 |
| `~` | TÜMLEYEN (NOT) | her biti ters çevir (tekli) |
| `<<` | sola kaydır | bitleri sola it, sağdan 0 |
| `>>` | sağa kaydır | bitleri sağa it |

İlk üçü bit bit, iki sayı arasında çalışıyor (Ders 0.2 ve 2'deki Boole işlemleri, ama bu sefer tek bir bit değil, 32 bitin hepsi aynı anda). `0xC` (`1100`) ve `0xA` (`1010`) üzerinde:

```c
unsigned a = 0xCu, b = 0xAu;   // 1100, 1010
a & b   // 1000 = 0x8   (ikisi de 1 olan tek bit)
a | b   // 1110 = 0xE
a ^ b   // 0110 = 0x6   (farkli olanlar)
~a      // ...11110011 = 0xFFFFFFF3 (butun bitler ters)
```

`&`, `|` ve `<<`, `>>`'yi Ders 3.18'de kullandık: `&` maskeleme (istediğin bitleri seç), `|` birleştirme, `<<`/`>>` 2'nin kuvvetleriyle çarpma/bölme. Bu derste `^` ve `~`'ı ekliyoruz ve altısının da ince noktalarını topluyoruz.

---

## 2. XOR: farkı bulan operatör

`^` (XOR), iki bit **farklıysa** 1, aynıysa 0 veriyor. Doğruluk tablosu küçük ama sonuçları zengin:

```
0 ^ 0 = 0    0 ^ 1 = 1    1 ^ 0 = 1    1 ^ 1 = 0
```

İki özelliği bu fazda sürekli işimize yarayacak:

**Kendisiyle XOR 0'dır, 0 ile XOR kendisidir.** `x ^ x = 0` ve `x ^ 0 = x`. Yani XOR **tersinir**: bir sayıyı aynı şeyle iki kez XOR'lamak onu geri getirir — `(x ^ k) ^ k = x`. Basit şifrelemeden (Faz'ların ilerisinde) hata düzeltmeye (Ders 5.19'daki parite) kadar her yerde bu.

**XOR ile geçici değişkensiz takas.** Tersinirliğin ünlü bir sonucu:

```c
int a = 7, b = 11;
a ^= b;   // a = 7^11
b ^= a;   // b = 11 ^ (7^11) = 7
a ^= b;   // a = (7^11) ^ 7 = 11
```

```
xor takas: a=11 b=7
```

Üçüncü bir değişken olmadan `a` ve `b` yer değiştirdi. (Ders 4.9'daki `swap_any`'nin zarif ama tuzaklı bir alternatifi: `a` ve `b` **aynı** değişkense sonuç 0 olur — Ders 4.7'deki aliasing. Modern derleyiciler sıradan takası zaten en iyi şekilde derlediği için bu numara artık hız için değil, XOR'un gücünü göstermek için kullanılıyor.)

`a ^= b`, Ders 2.3'teki `+=` gibi: `a = a ^ b`'nin kısası. Altı operatörün hepsinin atama hali var: `&=`, `|=`, `^=`, `<<=`, `>>=`.

---

## 3. ~ ve işaretsiz sayılar

`~x`, `x`'in her bitini ters çeviriyor. 32 bitlik işaretsiz bir sayıda `~0u` bütün bitlerin 1 olması:

```c
~0u        // 4294967295 = 0xFFFFFFFF (32 bitin hepsi 1)
~0u >> 1   // 2147483647 = 0x7FFFFFFF (en ust bit 0)
```

`~0u`, "bütün bitler 1" demenin taşınabilir yolu: tipin kaç bit olduğunu bilmene gerek yok. Bir maske kurarken sık kullanılır (Ders 4.28'deki `~(align - 1)` buydu).

İşaretli sayılarda `~` bir sürprizle gelir. Ders 3.3'teki ikiye tümleyene göre `~x == -x - 1`:

```c
~0  == -1       // isaretli: butun bitler 1, iki tumleyen -1
~5  == -6
```

Bu doğru ama işaretli sayılarla bit işlemi yaparken dikkatli olmak gerektiğinin ilk işareti. Kural: **bit desenleriyle çalışırken `unsigned` kullan.** İşaretli tipte `~`, `<<` ve `>>` tanımsız ya da şaşırtıcı davranabilir (birazdan).

---

## 4. Sağa kaydırma: aritmetik mi, mantıksal mı?

`>>` sağa kaydırırken soldan ne gelir? İki olasılık var ve C bunu **tipin işaretliliğine** göre seçiyor:

- **İşaretsiz** (`unsigned`): soldan hep **0** gelir. Buna **mantıksal** (logical) kaydırma denir.
- **İşaretli** (`int`) ve sayı **negatif**: soldan **işaret biti** (1) gelir. Buna **aritmetik** (arithmetic) kaydırma denir.

```c
int32_t neg = -8;              // 0xFFFFFFF8
uint32_t un = 0xFFFFFFF8u;     // ayni bit deseni, isaretsiz

neg >> 1   // -4   (aritmetik: isaret korunur)
un  >> 1   // 0x7FFFFFFC = 2147483644 (mantiksal: soldan 0)
```

Aynı bit deseni, farklı tip, farklı sonuç. Aritmetik kaydırma işareti koruyor: `-8 >> 1 = -4`, `-8 >> 2 = -2`, tıpkı 2'ye bölme gibi. Mantıksal kaydırma ise soldan 0 getirdiği için koca bir pozitif sayı veriyor.

Bir ince nokta: C standardı negatif bir sayının aritmetik mi mantıksal mı kaydırılacağını aslında **uygulamaya bırakıyor** (çoğu makine aritmetik yapar, bu makineler de öyle). Yani `-8 >> 1`'in `-4` olması garanti değil. Bir kez daha: **bit kaydırma için `unsigned` kullan**, davranış her zaman tanımlı ve taşınabilir olsun.

---

## 5. Kaydırmanın undefined behavior'ları

Kaydırmanın üç tehlikeli durumu var; üçü de Ders 2.12'deki undefined behavior, ve UBSan ile yakalanıyor:

```c
int x = 1;
x << 33    // genislik 32, sayi 33: UB
1 << 31    // isaretli 1'i isaret bitine kaydirmak: UB
x << -1    // negatif kaydirma sayisi: UB
```

```
runtime error: shift exponent 33 is too large for 32-bit type 'int'
runtime error: left shift of 1 by 31 places cannot be represented in type 'int'
runtime error: shift exponent -1 is negative
```

- **Genişliğe eşit ya da fazla kaydırmak**: 32 bitlik bir tipi 32 veya daha fazla kaydırmak tanımsız. "Hepsi dışarı çıkar, 0 kalır" diye düşünmek yanlış — standart bunu söylemiyor, bazı işlemciler sayıyı 32'ye göre mod alır (`x << 33` aslında `x << 1` olur). Sonuç makineye bağlı.
- **İşaretli bir 1'i işaret bitine sola kaydırmak**: `1 << 31` işaretli `int`'te taşma (işaret bitini 1 yapmak). `1u << 31` (işaretsiz) ise **tanımlı** ve `0x80000000`. Bir bit maskesi kurarken `1u << n` yaz, `1 << n` değil.
- **Negatif sayı kadar kaydırmak**: her zaman tanımsız.

clang bu üçünü sabit değerlerde `-Wshift-count-overflow` ve `-Wshift-count-negative` ile derleme sırasında da uyarıyor. Kural: kaydırma sayısı her zaman `[0, genişlik)` aralığında olmalı, ve sola kaydırırken işaretsiz tip kullan.

---

## 6. Öncelik tuzağı: & ile ==

Bit operatörlerinin C'deki **önceliği**, birçok dilden farklı ve şaşırtıcı: `&`, `|`, `^` operatörleri `==` ve `!=`'den **daha düşük** öncelikli. "Bit 0 sıfır mı?" diye sormak isteyelim:

```c
int x = 2;   // 0b10, bit 0 sifir
x & 1 == 0     // beklenen: (x & 1) == 0
```

```
x & 1 == 0   -> 0     // YANLIS
(x & 1) == 0 -> 1     // DOGRU
```

`x & 1 == 0`, aslında `x & (1 == 0)` diye okunuyor: önce `1 == 0` (yani 0) hesaplanıyor, sonra `x & 0` = 0. Niyetimiz `(x & 1) == 0` (yani 1) idi. Tek bir parantez farkı, ters sonuç.

Sebep tarihî: `&` ve `&&`, C'nin ilk sürümünde tek operatördü; `&`'in önceliği `==`'den düşük kaldı. clang bunu `-Wparentheses` ile uyarıyor:

```
warning: & has lower precedence than ==; == will be evaluated first [-Wparentheses]
```

Kural basit ve kesin: **bir bit işlemini bir karşılaştırmayla birlikte yazarken, bit işlemini parantezle.** `(x & MASK) == 0`, `(flags & FLAG) != 0`. Bu fazda bu parantezleri sürekli göreceksin; tuzak gerçek ve yaygın.

---

## Alıştırmalar

**1** – Şu ifadeleri 8 bitlik işaretsiz sayılarla (`unsigned char` gibi düşün) hesapla: `0x3C & 0x0F`, `0x3C | 0xC0`, `0x3C ^ 0xFF`, `~0x3C & 0xFF`. Sonuncusu `0x3C ^ 0xFF` ile neden aynı?

**2** – `x ^ y ^ x` ifadesini sadeleştir. Bir dizideki bir sayı dışında her sayı iki kez geçiyorsa, hepsini XOR'layarak tek geçen sayıyı bulan `int find_single(const int *a, int n)` yaz. Neden çalışıyor? (İpucu: `x ^ x = 0`, XOR sıra bağımsız.)

**3** – `-1 >> 1`'in bu makinede `-1` verdiğini doğrula, sonra `(unsigned)-1 >> 1`'i hesapla. İkisi neden farklı? Hangisi her makinede aynı sonucu garanti eder?

**4** – `1u << 31` ve `1 << 31`'i `-fsanitize=undefined` ile derleyip çalıştır. Hangisi hata veriyor, neden? Bir bitin 31. konumda olduğu bir maske istiyorsan hangisini yazmalısın?

**5** – `if (flags & FLAG == 0)` yazan bir kod neden neredeyse her zaman yanlış? `FLAG` bir bit maskesiyken (örneğin `4`), bu ifade aslında neyi hesaplıyor? Doğrusunu yaz.

<details>
<summary>Cevaplar</summary>

**1** – `0x3C` = `00111100`. `0x3C & 0x0F` = `00001100` = `0x0C` (alt 4 biti seç). `0x3C | 0xC0` = `11111100` = `0xFC` (üst 2 biti ekle). `0x3C ^ 0xFF` = `11000011` = `0xC3` (bütün bitleri ters). `~0x3C & 0xFF` = `11000011` = `0xC3`. Son ikisi aynı, çünkü bir şeyi `0xFF` (bütün bitler 1) ile XOR'lamak, o bitleri ters çevirmek demek — tam olarak `~`'ın yaptığı. `& 0xFF`, `~`'ın ürettiği üst 24 biti (hepsi 1) kesip 8 bitte tutuyor. Yani `x ^ 0xFF` == `~x & 0xFF`, 8 bit için.

**2** – `x ^ y ^ x` = `y`: XOR sıra bağımsız (`x^y^x = x^x^y = 0^y = y`).

```c
int find_single(const int *a, int n) {
    int result = 0;
    for (int i = 0; i < n; i++) {
        result ^= a[i];
    }
    return result;
}
```

Her sayı iki kez geçtiği için kendileriyle XOR'lanıp 0 olurlar (`x ^ x = 0`); tek geçen sayı `0 ^ tek = tek` olarak kalır. XOR'un hem sıra bağımsız olması hem de `x^x=0` özelliği sayesinde, ekstra bellek kullanmadan, tek geçişte. (`int` taşması yok: XOR aritmetik değil bit işlemi, taşmaz.)

**3** – `-1 >> 1` = `-1`: `-1` bütün bitleri 1, aritmetik kaydırma soldan yine 1 getirir, değişmez (`-1 / 2` tam sayıda `-1`'e değil 0'a yuvarlanırdı, ama kaydırma `-1` verir — negatif sayılarda `>>` ile `/` farkı, Ders 5.13'te). `(unsigned)-1 >> 1` = `0x7FFFFFFF` = 2147483647: işaretsiz, mantıksal kaydırma, soldan 0. Farklılar çünkü biri aritmetik (işaret korur) biri mantıksal. **İşaretsiz** sürüm her makinede aynı sonucu garanti eder; işaretli negatifte kaydırma uygulamaya bağlı.

**4** – `1 << 31` hata verir: `left shift of 1 by 31 places cannot be represented in type 'int'` — işaretli `int`'te 1'i 31. bite (işaret biti) kaydırmak temsil edilemez, undefined behavior. `1u << 31` tanımlı: işaretsizde taşma diye bir şey yok (mod 2³²), sonuç `0x80000000`. 31. bitte bir maske için **`1u << 31`** (ya da daha genel `1u << n`) yazmalısın; işaretli `1 << n` `n` 31'e yaklaşınca tehlikeli.

**5** – `flags & FLAG == 0`, öncelik yüzünden `flags & (FLAG == 0)` diye okunur. `FLAG` sıfırdan farklı bir maske olduğu için (`4`), `FLAG == 0` her zaman 0; ifade `flags & 0` = 0 olur — yani koşul `flags`'tan **bağımsız**, her zaman yanlış. Niyet "`FLAG` biti kapalı mı?" idi; doğrusu `(flags & FLAG) == 0`. Bu, Bölüm 6'daki tuzağın en sık görülen hali; `&`'i mutlaka parantezle.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §2.9: bit operatörleri.
- C standardı (ISO/IEC 9899:2018), §6.5.7 (kaydırma ve UB durumları), §6.5.10–6.5.12 (`&`, `^`, `|` ve öncelikleri).
- Henry Warren, *Hacker's Delight* (2. baskı), Bölüm 2: temel bit işlemleri.
- Sean Anderson, "Bit Twiddling Hacks": XOR takası ve temel hileler.

**Sıradaki ders:** Maskeler ve bayrak kümeleri. Bit set/clear/toggle/test ve bir izin sistemi örneği.
