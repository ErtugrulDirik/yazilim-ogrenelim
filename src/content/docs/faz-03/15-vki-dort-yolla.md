---
title: "3.15 VKİ dört yolla"
description: "Vücut kitle indeksini int, 100 ile ölçeklenmiş int, Q16.16 sabit noktalı sayı ve double ile hesaplamak; altı kişi için sonuçların ve hataların karşılaştırması, x86-64 ve ARM64 assembly'si, kayan nokta birimi olmayan Arduino'da ne değiştiği ve hangi yöntemin ne zaman seçileceği."
---

Vücut kitle indeksi Ders 0.1'den beri bizimle. Her fazda biraz daha iyi hesapladık:

| Ders | Yöntem | 70 kg, 175 cm |
| --- | --- | --- |
| 2.3 | `int` | 22 |
| 2.13 | 100 ile ölçeklenmiş `int` | 22,85 |
| 3.11 | Q16.16 sabit noktalı | 22,8571 |
| 3.12–3.14 | `double` | ? |

Bu derste dört yöntemi aynı dosyaya koyup yan yana koşturacağız: hangisi ne kadar doğru, compiler her birinden nasıl bir makine kodu çıkarıyor, ve küçük bir işlemcide ne değişiyor?

---

## 1. Dört fonksiyon

Dört fonksiyonun da girdisi aynı: kilo (kg) ve boy (cm), ikisi de `int`. Ders 2.13'teki gibi kullanıcıdan tamsayı okuduğumuzu düşünüyoruz.

```c
#include <stdint.h>

#define FX_ONE 65536

int bmi_int(int weight_kg, int height_cm) {
    return weight_kg * 10000 / (height_cm * height_cm);
}

int bmi_x100(int weight_kg, int height_cm) {
    return weight_kg * 1000000 / (height_cm * height_cm);
}

int32_t fx_from_int(int n) {
    return n * FX_ONE;
}

int32_t fx_from_ratio(int num, int den) {
    return (int32_t)((int64_t)num * FX_ONE / den);
}

int32_t fx_mul(int32_t a, int32_t b) {
    return (int32_t)((int64_t)a * b / FX_ONE);
}

int32_t fx_div(int32_t a, int32_t b) {
    return (int32_t)((int64_t)a * FX_ONE / b);
}

int32_t bmi_fx(int weight_kg, int height_cm) {
    int32_t height = fx_from_ratio(height_cm, 100);
    return fx_div(fx_from_int(weight_kg), fx_mul(height, height));
}

double bmi_double(int weight_kg, int height_cm) {
    double height = height_cm / 100.0;
    return weight_kg / (height * height);
}
```

- `bmi_int`: Ders 2.3'teki satırın aynısı.
- `bmi_x100`: Ders 2.13'teki `bmi_x100`. Sonuç 100 ile çarpılmış.
- `bmi_fx`: Ders 3.11'deki fonksiyonlarla. Sonuç Q16.16.
- `bmi_double`: `height_cm / 100.0` ifadesinde bir taraf `double` olduğu için `height_cm` de `double`'a çevriliyor (Ders 3.12, Bölüm 7). Aynı şey `weight_kg / (…)`'da da oluyor. Fonksiyonda tek bir cast yok; dönüşümlerin hepsi örtük.

`bmi_double` en kısa ve en okunaklı olanı. Formül, Ders 0.1'de kağıda yazdığımız haliyle duruyor: kilo / boy². Ölçekler, `int64_t` ara sonuçlar, "önce çarp sonra böl" kararları yok.

---

## 2. Sonuçlar

Altı kişi için dört fonksiyonu çağırıp sonuçları yazdırdık. `bmi_x100` için Ders 2.13'teki `print_fixed2`'yi, `bmi_fx` için Ders 3.11'deki `fx_print`'i, `bmi_double` için `%.17g`'yi kullandık. "Gerçek değer" sütununu kesirli sayılarla tam hesaplayan ayrı bir programla bulduk.

| Kilo | Boy | `int` | `x100` | Q16.16 | `double` | Gerçek değer |
| --- | --- | --- | --- | --- | --- | --- |
| 70 | 175 | 22 | 22,85 | 22,8571 | 22,857142857142858 | 22,857142857142857… |
| 70 | 182 | 21 | 21,13 | 21,1329 | 21,132713440405748 | 21,132713440405748… |
| 300 | 100 | 300 | 300,00 | 300,0000 | 300 | 300 |
| 20 | 250 | 3 | 3,20 | **3,1999** | 3,2000000000000002 | 3,2 |
| 85 | 190 | 23 | 23,54 | 23,5458 | 23,545706371191137 | 23,545706371191135… |
| 54 | 163 | 20 | 20,32 | **20,3247** | 20,324438255109339 | 20,324438255109337… |

Her sütunu ayrı ayrı okuyalım.

**`int`.** Küsuratı tamamen atıyor. 20 kg ve 250 cm için 3,2 yerine 3; %6 hata. Gruplara ayırmak için bile yetersiz: 24,99 ile 24,01 aynı sonucu veriyor.

**`x100`.** İki ondalık basamak, ve gösterdiği her basamak doğru. Ama **kesiyor**, yuvarlamıyor: 22,857 → 22,85 (doğrusu 22,86), 23,5457 → 23,54 (doğrusu 23,55). 1. alıştırmada düzelteceksin.

**Q16.16.** Dört ondalık basamak gösteriyor, ama dördüncü basamak her zaman doğru değil. 54 kg, 163 cm için 20,3247; doğrusu 20,3244. Ders 3.11'de 182 cm için gördüğümüz sorun:

- 1,63 × 65.536 = 106.823,68 → 106.823'e kesildi. Bağıl hata yaklaşık 6 × 10⁻⁶.
- `fx_mul(height, height)` ikinci bir kesme yaptı: 174.122,6 yerine 174.120. Bağıl hata artık 1,5 × 10⁻⁵.
- Bölme bu bağıl hatayı sonuca taşıdı: 20,32 × 1,5 × 10⁻⁵ ≈ 0,0003.

Her kesme küçük; ama bağıl hatalar çarpmada ve bölmede **toplanır**. 20 kg, 250 cm için çıkan 3,1999'un sebebi ise farklı; 4. alıştırmada.

**`double`.** On beş–on altı basamağın hepsi doğru. Sadece en son basamakta, beklendiği gibi, yuvarlama farkları var: 3,2 `double`'da 3,2000000000000002 (Ders 3.12'deki 0,1 gibi, 3,2 de ikilikte sonsuz bir kesir). 70 kg ve 175 cm için gerçek değer ...857, `double` ...858: en yakın `double` bu.

Sonucu kullanıcıya gösterirken bu kadar basamağa gerek yok. `printf("%.2f", bmi_double(70, 175))` **22,86** yazar: `printf` **yuvarlar**. `x100`'ün kaçırdığı yuvarlama bedavaya geldi.

---

## 3. Makine kodu

Dört fonksiyonu Ders 3.5'teki gibi [godbolt.org](https://godbolt.org)'a koyalım: **x86-64 clang**, **`-O2`**. Aynı kodu **armv8-a clang** (ARM64) ile de derleyelim.

### int ve x100

```asm
bmi_int:
        imul    eax, edi, 10000
        imul    esi, esi
        cdq
        idiv    esi
        ret

bmi_x100:
        imul    eax, edi, 1000000
        imul    esi, esi
        cdq
        idiv    esi
        ret
```

İki fonksiyon, sabit dışında **birebir aynı**. Ölçeklemenin makine için bir bedeli yok.

- `imul eax, edi, 10000`: kilo × 10.000.
- `imul esi, esi`: boy × boy.
- `cdq`: `eax`'in işaretini `edx`'e genişletir. x86'nın `idiv` komutu 64 bitlik bir sayıyı (`edx:eax`) böler; 32 bitlik bölünen önce işaretle 64 bite genişletilmeli. Ders 3.5'teki `movsx`'in bir benzeri.
- `idiv esi`: işaretli bölme. Bölüm `eax`'te kalır; fonksiyonun dönüş değeri de `eax`.

ARM64'te aynı şey: iki `mul`, bir `sdiv` (signed divide). `bmi_x100`'de bir komut fazla: 1.000.000 tek komuta sığmadığı için iki parçada (`mov` ve `movk`) yükleniyor.

### double

```asm
bmi_double:
        cvtsi2sd        xmm1, esi
        divsd   xmm1, qword ptr [rip + .LCPI7_0]
        cvtsi2sd        xmm0, edi
        mulsd   xmm1, xmm1
        divsd   xmm0, xmm1
        ret
```

- `xmm0`, `xmm1`: kayan nokta sayılar için ayrı **register**'lar. İşlemcinin içinde, tamsayılardan ayrı bir kayan nokta birimi var.
- `cvtsi2sd`: **c**on**v**er**t** **s**igned **i**nteger **to** **s**calar **d**ouble. Ders 3.12'deki örtük `int` → `double` dönüşümü tek bir komut.
- `divsd`, `mulsd`: `double` bölme ve çarpma. `.LCPI7_0` bellekte duran 100,0 sabiti.

Altı komut; tamsayı versiyonundan sadece bir fazla. Masaüstü bir işlemcide kayan nokta, tamsayı kadar **birinci sınıf** bir vatandaş.

Bir ayrıntı: compiler `height_cm / 100.0`'ı `height_cm * 0.01`'e çevirmedi, oysa çarpma bölmeden daha hızlı. Çünkü 0,01 `double`'da tam değil (Ders 3.12); çarpmak her zaman aynı sonucu vermez. IEEE 754'ün "her işlem tam hesaplanıp yuvarlanır" sözü, compiler'ın sonucu değiştirebilecek hiçbir dönüşüm yapmamasını gerektiriyor. `-ffast-math` ile derleyince `divsd` gerçekten `mulsd`'ye dönüşüyor (Ders 3.14'te bu ayarın ne kadar şeyi değiştirdiğini görmüştük).

### Q16.16

```asm
bmi_fx:
        movsxd  rcx, esi
        shl     rcx, 16
        movabs  rdx, -6640827866535438581
        mov     rax, rcx
        imul    rdx
        add     rdx, rcx
        mov     rax, rdx
        shr     rax, 63
        shr     rdx, 6
        add     edx, eax
        shl     edi, 16
        movsxd  rcx, edx
        movsxd  rax, edi
        shl     rax, 16
        imul    rcx, rcx
        shr     rcx, 16
        movsxd  rsi, ecx
        mov     rdx, rax
        or      rdx, rsi
        shr     rdx, 32
        je      .LBB6_1
        cqo
        idiv    rsi
        ret
.LBB6_1:
        xor     edx, edx
        div     ecx
        ret
```

Uzun, ama okunabilir. Ders 3.11'deki dört fonksiyon `bmi_fx`'in içine yerleştirilmiş (**inline**); ayrı çağrılar kalmamış. Üç ilginç şey:

- **65.536 ile çarpma ve bölme, `shl` ve `shr` oldu.** `shl rcx, 16`, bitleri 16 basamak sola kaydırmak: 2¹⁶ ile çarpmak. Ondalıkta bir sayıyı 1000 ile çarpmak için sağına üç sıfır yazmak gibi. Bit kaydırmayı Faz 5'te göreceğiz; Ders 3.11'de ölçeği 2'nin kuvveti seçmemizin ödülü bu.
- **100'e bölme hiç yok.** Yerine `movabs rdx, -6640827866535438581` ile dev bir sabit yüklenip çarpılıyor. Compiler, sabit bir sayıya bölmeyi, özenle seçilmiş bir "sihirli sayı" ile çarpma ve kaydırmaya çeviriyor; çünkü bölme komutu çarpmadan çok daha yavaş. Bu dönüşüm her tamsayı için **tam olarak** aynı sonucu verir (`double`'daki 0,01'in aksine). Nasıl çalıştığını Faz 7'de göreceğiz.
- **İki yol var.** `or rdx, rsi; shr rdx, 32; je` satırları, 64 bitlik bölmenin iki tarafı da aslında 32 bite sığıyor mu diye bakıyor; sığıyorsa daha hızlı olan 32 bitlik `div`'i kullanıyor. Compiler, bizim yerimize bir hız kontrolü eklemiş.

ARM64'te `bmi_fx` 17 komut ve tek bir `sdiv`: ARM'ın 64 bitlik bölme komutu yeterince hızlı olduğu için iki yola gerek görülmemiş.

### Özet

| Fonksiyon | x86-64 komut | ARM64 komut | Bölme komutu |
| --- | --- | --- | --- |
| `bmi_int` | 5 | 5 | 1 tamsayı |
| `bmi_x100` | 5 | 6 | 1 tamsayı |
| `bmi_fx` | 27 | 17 | 1 tamsayı (64 bit) |
| `bmi_double` | 6 | 8 | 2 kayan nokta |

(`ret` dahil, iki yollu x86 `bmi_fx`'in iki yolu birlikte.) Sabit noktalı sayılar, kayan nokta birimi olan bir işlemcide hem **daha uzun** hem **daha az doğru**. Peki neden hâlâ kullanılıyor?

---

## 4. Arduino'da

Ders 3.1'den beri örnek verdiğimiz Arduino Uno'nun işlemcisinde (AVR) kayan nokta birimi **yok**. Hatta bölme komutu da yok: işlemci sadece 8 bitlik sayıları çarpabiliyor. Aynı dosyayı clang ile Arduino için derleyip (`--target=avr -mmcu=atmega328p -O2`) her fonksiyonun hangi kütüphane fonksiyonlarını çağırdığına baktık:

| Fonksiyon | Çağrılan yardımcı fonksiyonlar |
| --- | --- |
| `bmi_int` | `__divmodhi4` (16 bit bölme) |
| `bmi_x100` | `__mulsi3`, `__divmodsi4` (32 bit çarpma ve bölme) |
| `bmi_fx` | `__muldi3`, `__divmodsi4`, `__divdi3` (64 bit çarpma ve bölme) |
| `bmi_double` | `__floatsisf` ×2, `__divsf3` ×2, `__mulsf3` |

Donanımın yapamadığı her işlem, compiler'ın programa eklediği bir **yazılım** fonksiyonuyla yapılıyor. Kayan nokta için olanların adlarındaki `sf`, "single float" demek: Ders 3.12'de gördüğümüz gibi Arduino'da `double` 4 byte, yani aslında bir `float`. `__divsf3`, IEEE 754 bölmesini 8 bitlik komutlarla adım adım yapan, yüzlerce komutluk bir fonksiyon.

İki sonuç var:

- **Hassasiyet.** Arduino'daki `bmi_double` aslında `float` ile hesaplıyor. Bilgisayarımızda aynı fonksiyonu `float` ile yazıp çalıştırdık: 70 kg, 175 cm için **22,8571434**. Yedi basamak doğru, sonrası değil (2. alıştırma).
- **Hız ve boyut.** Kayan nokta fonksiyonları, 32 KB'lık program belleği olan bir kartta yer kaplıyor ve her çağrıda yüzlerce komut çalışıyor. Sabit noktalı sayılar bu tür işlemcilerde hâlâ yaygın: `__divdi3` de bir yazılım fonksiyonu, ama tamsayı fonksiyonları daha basit ve öngörülebilir.

Doom'un 1993'te Q16.16 kullanması da aynı sebepten: o yılların ev bilgisayarlarının çoğunda kayan nokta birimi ya yoktu ya da çok yavaştı.

---

## 5. Hangisi ne zaman?

| Yöntem | Hassasiyet | Aralık | Ne zaman? |
| --- | --- | --- | --- |
| `int` | Sadece tamsayı | ±2,1 milyar | Sayılan şeyler: adet, indeks, puan |
| Ondalık ölçekli `int` | Sabit sayıda ondalık basamak, **tam** | Ölçek kadar daralır | **Para** (kuruş), sabit ondalıklı ölçümler |
| Q biçimi (Q16.16) | Sabit sayıda ikilik basamak | Çok dar | Kayan nokta birimi olmayan işlemciler, ses işleme, her platformda bit bit aynı sonuç gereken yerler |
| `double` | ~15–16 anlamlı basamak, bağıl | 10³⁰⁸ | Ölçümler, bilim, mühendislik, istatistik; masaüstünde varsayılan seçim |
| `float` | ~7 anlamlı basamak, bağıl | 10³⁸ | Bellek ya da hız gerektiğinde: grafik, oyun, makine öğrenmesi |

Vücut kitle indeksi bir ölçüm: kilo ve boy zaten tam değil (tartının hassasiyeti, boyun milimetresi). Doğru seçim `double`, ve sonucu `%.2f` ile göstermek. Sağlık hesaplayıcısını bugün yeniden yazsaydık `bmi_double`'ı kullanırdık. Kalori hesabındaki katsayılar (1,2, 1,375, 1,55…) için de aynısı geçerli.

Ama aynı uygulama bir **ödeme** alsaydı, tutarlar kuruş cinsinden bir tamsayıda dururdu. Ders 3.14'teki 2. alıştırmayı hatırla: `float`, 131.072 TL'nin üzerinde kuruşları ayırt edemiyor. `double` bu sınırı trilyonlara taşıyor, ama 0,1 TL'yi bile tam tutamıyor.

---

## Alıştırmalar

**1** – `bmi_x100`'ü kesmek yerine **yuvarlayacak** şekilde değiştir: 70 kg ve 175 cm için 22,86 versin. (İpucu: Ders 3.11'deki 2. alıştırma.) Altı kişinin sonuçları ne oluyor?

**2** – `bmi_double`'ın `float` halini (`bmi_float`) yaz: `100.0f` ve `float` değişkenlerle. Altı kişi için `%.9g` ile yazdır. `double` sonuçlarıyla kaç basamakta uyuşuyor? Bu sonuçlar Arduino'da ne anlama geliyor?

**3** – godbolt'ta `bmi_double`'ı **`-O2 -ffast-math`** ile derle. Ne değişti? Bu değişiklik altı kişiden herhangi birinin `%.2f` ile gösterilen sonucunu değiştirir mi? Değiştirmezse, neden yine de önemli olabilir?

**4** – Q16.16, 20 kg ve 250 cm için 3,1999 verdi. 2,5 Q16.16'da tam saklanır (2,5 = 5/2), `height_squared` = 6,25 de tam. Hata nereden geliyor? `fx_print`'i yuvarlayacak şekilde değiştirirsen ne yazar?

**5** – Arduino'da `int` 2 byte (Ders 3.1). Bu dersteki dört fonksiyondan hangileri Arduino'da 70 kg, 175 cm için **yanlış** sonuç verir? (Ders 3.1'deki 4. alıştırmayı ve Ders 3.10'daki sabitlerin tip kurallarını hatırla.)

<details>
<summary>Cevaplar</summary>

**1** –

```c
int bmi_x100_rounded(int weight_kg, int height_cm) {
    int height_squared = height_cm * height_cm;
    return (weight_kg * 1000000 + height_squared / 2) / height_squared;
}
```

Bölmeden önce bölenin yarısını eklemek, pozitif sayılarda en yakına yuvarlar. Sonuçlar: **22,86**, 21,13, 300,00, 3,20, **23,55**, 20,32. Değişenler, kesilen kısmın yarıdan büyük olduğu iki satır. Overflow kontrolü: 300.000.000 + 31.250 (250² / 2) hâlâ `INT_MAX`'ın çok altında.

**2** –

```c
float bmi_float(int weight_kg, int height_cm) {
    float height = height_cm / 100.0f;
    return weight_kg / (height * height);
}
```

| Kilo | Boy | `float` | `double` |
| --- | --- | --- | --- |
| 70 | 175 | 22,8571434 | 22,857142857142858 |
| 70 | 182 | 21,1327133 | 21,132713440405748 |
| 300 | 100 | 300 | 300 |
| 20 | 250 | 3,20000005 | 3,2000000000000002 |
| 85 | 190 | 23,5457077 | 23,545706371191137 |
| 54 | 163 | 20,3244381 | 20,324438255109339 |

Yaklaşık 7 anlamlı basamakta uyuşuyor; Ders 3.12'deki `FLT_DIG` ile tutarlı. `%.4f` ile yazdırınca altısı da `double` ile aynı. Arduino'da `double` = `float` olduğu için, Arduino'daki `bmi_double` tam olarak bu sütunu üretir. Vücut kitle indeksi için fazlasıyla yeterli.

**3** – `divsd xmm1, [100,0]` satırı `mulsd xmm1, [0,01]` oldu. Altı kişinin `%.2f` sonuçlarını değiştirmez: fark en fazla son basamakta, 10⁻¹⁵ civarında. Ama artık programın sonucu, compiler'ın hangi dönüşümleri yaptığına bağlı; başka bir compiler, başka bir sürüm ya da başka bir ayar farklı son basamaklar üretebilir. Testlerde sonuçları bit bit karşılaştıran ya da iki makinenin aynı sonucu bulmasını bekleyen bir program (örneğin ağ üzerinden oynanan bir oyun) için bu kabul edilemez.

**4** – Hata son bölmede: 20 / 6,25 = 3,2, ve 3,2 ikilikte sonsuz bir kesir. 3,2 × 65.536 = 209.715,2 → **209.715**'e kesiliyor; bu 3,19999695… demek. `fx_print` de küsuratı 4 basamağa **keserek** çeviriyor: 0,19999695 → 1999. İki kesme üst üste binince 3,1999. `fx_print`'te dört basamağa çevirirken yuvarlarsan (`(frac * 10000 + 32768) / 65536`, ve 10.000'e ulaşırsa tam kısma taşıyarak) **3,2000** yazar.

**5** –

- `bmi_int`: `weight_kg * 10000` iki `int`'in çarpımı; 10.000 2 byte'a sığdığı için `int`. 700.000 sığmaz: **yanlış** (Ders 3.1).
- `bmi_x100`: 1.000.000 2 byte'a sığmadığı için `long` (Ders 3.10); çarpma 32 bitle yapılıyor ve 70.000.000 sığıyor. Ama payda `height_cm * height_cm` = 30.625, 32.767'nin kıl payı altında; 175 cm için **doğru**, 182 cm'den itibaren yanlış.
- `bmi_fx`: `fx_from_int`'teki `n * FX_ONE`: 65.536 2 byte'a sığmadığı için `long`, çarpma 32 bit; 70 × 65.536 sığıyor. Diğer ara sonuçlar zaten `int64_t`. **Doğru.**
- `bmi_double`: `height_cm / 100.0` kayan noktayla; `int` taşması yok. **Doğru**, `float` hassasiyetinde.

Arduino için yazılan kodda, hangi sabitin hangi tipte olduğunu bilmek bu yüzden bu kadar önemli.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.3.6–2.3.7: sabitle çarpmayı ve 2'nin kuvvetine bölmeyi kaydırmaya çevirmek; §3.11: kayan nokta kodu.
- Torbjörn Granlund & Peter Montgomery, "Division by Invariant Integers using Multiplication", *PLDI*, 1994.
- [Compiler Explorer](https://godbolt.org).
- [GCC belgesi: AVR kayan nokta ve `double`'ın boyutu](https://gcc.gnu.org/wiki/avr-gcc).

**Sıradaki ders:** Dönüşüm sıfırdan 1: `itoa`. `printf("%d")`'nin içinde ne oluyor? Bir tamsayıyı herhangi bir tabanda yazıya çevirmek.
