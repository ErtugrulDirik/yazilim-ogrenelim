---
title: "11.15 Otomatik vektörleştirme"
description: "Derleyicinin SIMD'i kendisi üretmesi ve bunu nasıl raporladığı: clang'in -Rpass=loop-vectorize ve gcc'nin -fopt-info-vec çıktısı, on bir döngünün ikisinde birden incelenmesi; float toplamının 'vektörleşti' dense de sıralı fadd zinciri olarak kalması ve -ffast-math ile 9 kat hızlanma; sqrtf'nin errno yüzünden 19 kat yavaş kalması; erken çıkış, histogram ve kayıtlı bağımlılığın neden vektörleşmediği; clang ile gcc'nin koşullu atamada zıt kararlar vermesi; sinf için glibc libmvec ile 4.8 kat ve clang 18'in -fveclib=libmvec'te bağlanmayan isim üretmesi."
---

Ders 11.7–11.14 boyunca SIMD'i elle yazdık. Gerçek kodun çoğu ise elle yazılmaz: derleyicinin **vektörleştiricisi** döngüleri kendisi SIMD'e çevirir. Bu derste iki soruyu soruyoruz: derleyici neyi vektörleştiriyor ve vektörleştiremediğinde bunu bize nasıl söylüyor?

Bütün ölçümler M2 üzerinde, `clang 18` ve `gcc 13`, arm64 Linux.

---

## 1. Derleyiciyi konuşturmak

```
clang -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize
gcc   -O3 -fopt-info-vec-optimized -fopt-info-vec-missed
```

Clang'de `-Rpass` başarılı dönüşümleri, `-Rpass-missed` başarısızları, `-Rpass-analysis` başarısızlığın nedenini raporlar. Gcc'de `-fopt-info-vec-all` her şeyi döker (çok uzun). İkisinde de vektörleştirici `-O2`'de açık (clang ve gcc 12+), `-O3` daha istekli.

Deney dosyası on bir döngü:

```c
/* dongu.c: vektorlestirici her donguye ne diyor? */
#include <math.h>

void topla(float *d, const float *a, const float *b, int n) {
    for (int i = 0; i < n; i++) d[i] = a[i] + b[i];
}

int itoplam(const int *a, int n) {
    int s = 0;
    for (int i = 0; i < n; i++) s += a[i];
    return s;
}

float ftoplam(const float *a, int n) {
    float s = 0;
    for (int i = 0; i < n; i++) s += a[i];
    return s;
}

void onceki(float *a, const float *b, int n) {
    for (int i = 1; i < n; i++) a[i] = a[i - 1] + b[i];
}

int bul(const int *a, int n, int x) {
    for (int i = 0; i < n; i++)
        if (a[i] == x) return i;
    return -1;
}

void kosullu(float *b, const float *a, int n) {
    for (int i = 0; i < n; i++)
        if (a[i] > 0) b[i] = a[i];
}

void secim(float *b, const float *a, int n) {
    for (int i = 0; i < n; i++) b[i] = a[i] > 0 ? a[i] : b[i];
}

void adim2(float *d, const float *a, int n) {
    for (int i = 0; i < n; i++) d[i] = a[2 * i] + a[2 * i + 1];
}

void histogram(int *h, const unsigned char *a, int n) {
    for (int i = 0; i < n; i++) h[a[i]]++;
}

void karekok(float *d, const float *a, int n) {
    for (int i = 0; i < n; i++) d[i] = sqrtf(a[i]);
}

void sinus(float *d, const float *a, int n) {
    for (int i = 0; i < n; i++) d[i] = sinf(a[i]);
}
```

---

## 2. Ne dediler

```
$ clang -O3 -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -Rpass-analysis=loop-vectorize -c dongu.c
dongu.c:5:5: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
dongu.c:10:5: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
dongu.c:16:5: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
dongu.c:21:38: remark: loop not vectorized: unsafe dependent memory operations in loop. Use #pragma clang loop distribute(enable) to allow loop distribution to attempt to isolate the offending operations into a separate loop
dongu.c:25:5: remark: loop not vectorized: could not determine number of loop iterations
dongu.c:31:5: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
dongu.c:36:5: remark: the cost-model indicates that vectorization is not beneficial
dongu.c:40:5: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
dongu.c:44:33: remark: loop not vectorized: cannot identify array bounds
dongu.c:48:40: remark: loop not vectorized: library call cannot be vectorized. Try compiling with -fno-math-errno, -ffast-math, or similar flags
dongu.c:52:40: remark: loop not vectorized: library call cannot be vectorized. Try compiling with -fno-math-errno, -ffast-math, or similar flags

$ gcc -O3 -fopt-info-vec-optimized -fopt-info-vec-missed -c dongu.c
dongu.c:5:23: optimized: loop vectorized using 16 byte vectors
dongu.c:10:23: optimized: loop vectorized using 16 byte vectors
dongu.c:16:23: missed: couldn't vectorize loop
dongu.c:21:23: missed: couldn't vectorize loop
dongu.c:26:14: missed: couldn't vectorize loop
dongu.c:31:23: missed: couldn't vectorize loop
dongu.c:36:23: optimized: loop vectorized using 16 byte vectors
dongu.c:40:23: optimized: loop vectorized using 16 byte vectors
dongu.c:44:23: missed: couldn't vectorize loop
dongu.c:48:23: missed: couldn't vectorize loop
dongu.c:52:23: missed: couldn't vectorize loop
```

(Clang çıktısında her başarısızlığın ardından gelen kısa "loop not vectorized" tekrarlarını, gcc'den de her satır için birden fazla gelen ayrıntılı nedenleri çıkardım.) "width 4" dört `float` şeridi, "interleaved count 2" döngünün ayrıca iki kat açılması demek (Ders 11.3).

Sonuçları tabloya dökelim, süreleriyle birlikte (ns/eleman, 4096 eleman):

| Döngü | clang -O3 | gcc -O3 | Neden |
| --- | --- | --- | --- |
| `topla` | evet | evet | Bağımsız elemanlar |
| `itoplam` | evet, 0.064 | evet, 0.136 | Tamsayı toplama birleşmeli |
| `ftoplam` | "evet", **0.834** | hayır, 0.851 | Float toplama birleşmeli değil |
| `onceki` | hayır | hayır | `a[i]`, `a[i-1]`'e bağlı |
| `bul` | hayır | hayır | Erken çıkış: tur sayısı bilinmiyor |
| `kosullu` | evet, 0.395 | hayır, 0.922 | Koşullu **yazma** |
| `secim` | hayır (maliyet), 0.645 | evet, **0.075** | Koşulsuz yazma |
| `adim2` | evet | evet | 2 adımlı erişim: `ld2` |
| `histogram` | hayır | hayır | `h[a[i]]` çakışabilir |
| `karekok` | hayır, 2.739 | hayır, 2.637 | `errno` |
| `sinus` | hayır | hayır | Kütüphane çağrısı |

Her satırı tek tek açalım.

---

## 3. "Vektörleşti" yeterli değil: float toplamı

Clang `ftoplam` için **vectorized loop** diyor, ama süre skaler gcc ile aynı. Üretilen döngü:

```
.LBB2_5:
	ldp	q1, q2, [x10, #-16]       ; 8 float vektor olarak okundu
	mov	s3, v1.s[1]
	fadd	s0, s0, s1                ; ama tek tek, sirayla toplaniyor
	mov	s4, v1.s[2]
	mov	s1, v1.s[3]
	fadd	s0, s0, s3
	...
	fadd	s0, s0, s1
	b.ne	.LBB2_5
```

Yüklemeler vektörlü, toplamlar sıralı: bu bir **sıralı indirgeme** (*ordered reduction*). Float toplama birleşmeli olmadığından (Ders 3.14, 11.11) derleyici toplama sırasını değiştiremez; tek `fadd` zinciri 3 çevrimlik gecikmeyle kilitli kalır: 0.834 ns × 3.5 ≈ 2.9 çevrim/eleman. Ders 11.1'in uyarısı burada da geçerli: **raporu değil süreyi ölç**.

Sırayı değiştirme izni:

```
$ clang -O3 -ffast-math ...        ftoplam 0.095 ns/eleman
$ gcc -O3 -ffast-math ...          ftoplam 0.202 ns/eleman
```

**9 kat**. `-ffast-math` yerine yalnız gereken iznin adı `-fassociative-math` (clang'de `-fno-signed-zeros` ve `-fno-trapping-math` ile birlikte). `-ffast-math` NaN ve sonsuz yok varsayımı gibi tehlikeli şeyleri de açar; bir kütüphanede bütün dosyaya değil, yalnız ilgili fonksiyona uygulanmalı ya da Ders 11.11'deki gibi elle birikimci yazılmalı.

Tamsayıda bu sorun yok: `itoplam` ilk denemede 0.064 ns.

---

## 4. errno: karekök 19 kat yavaş

C standardına göre `sqrtf(-1)` `errno`'ya `EDOM` yazabilir (`math_errhandling` `MATH_ERRNO` içeriyorsa; glibc'de içerir). Bir vektör karekök komutu `errno` yazamaz, bu yüzden derleyici skaler çağrıda kalıyor. Clang'in uyarısı çözümü de söylüyor:

```
clang -O3                   karekok 2.739 ns/eleman
clang -O3 -fno-math-errno   karekok 0.143 ns/eleman
```

**19 kat**. Bu bayrak `-ffast-math`'ten çok daha zararsız: yalnızca matematik fonksiyonlarının `errno` yazmayacağını varsayıyor (macOS'ta zaten varsayılan böyle).

`sinf` daha zor: donanımda `sin` komutu yok, vektörlü bir **kütüphane** fonksiyonu gerek. glibc 2.38'den beri aarch64 için *libmvec* sağlıyor ve gcc bunu kullanıyor:

```
$ gcc -O3 -ffast-math -S dongu.c -o - | grep bl
	bl	_ZGVnN4v_sinf             ; 4 seritli sinf
	bl	sinf                      ; kalan elemanlar
gcc -O3              sinus 2.238 ns/eleman
gcc -O3 -ffast-math  sinus 0.463 ns/eleman
```

`_ZGVnN4v_sinf` vektör ABI'nin isimlendirmesi: `n` = NEON, `N` = maskesiz, `4` = şerit, `v` = vektör argümanı. 4.8 kat kazanç.

Clang 18'de ise `-ffast-math` döngüyü "vektörleştirdi" ama her şeritte skaler `sinf` çağırdı (2.107 ns, kazanç yok). `-fveclib=libmvec` ile denedim:

```
$ clang -O3 -ffast-math -fveclib=libmvec -c dongu.c && clang hiz.c dongu.o -lm
/usr/bin/ld: dongu.c:(.text+0x568): undefined reference to `_ZGVbN4v_sinf'
```

Clang 18 aarch64'te x86'ya ait ismi (`b` = SSE) üretti ve bağlama başarısız oldu. Bu sürümde clang ile aarch64'te libmvec kullanılamıyor; daha yeni bir clang'de durum değişmiş olabilir, kontrol etmedim.

---

## 5. Vektörleşmeyenler

**`onceki`**: `a[i] = a[i-1] + b[i]` bir *döngü taşıyan bağımlılık* (Ders 11.5'in Alıştırma 5'i). Her eleman bir öncekini bekliyor, paralellik yok. Bu aslında bir **önek toplamı** (prefix sum) ve bunun için ayrı SIMD algoritmaları var (şeritler içinde kaydırıp toplama, $\log_2 k$ adım), ama derleyici bunu kendiliğinden yapmıyor.

**`bul`**: `return i` döngünün tur sayısını belirsiz kılıyor ("could not determine number of loop iterations"). Vektörlü sürüm kolay: Ders 11.12'nin `cmpeq + movemask` kalıbı. Ama vektörlü sürüm dizinin bulunan elemandan sonraki kısmını da **okuyor**, bu okuma derleyicinin izinli olduğu bir şey değil (dizinin sonu bilinmiyor, Ders 11.12'deki sayfa argümanını derleyici kendiliğinden kurmuyor). Clang 18 ve gcc 13 bu döngüyü bırakıyor.

**`histogram`**: `h[a[i]]++` iki şeritte aynı `a[i]` değeri olabileceği için çakışıyor; dört şeridi aynı anda artırmak yanlış sonuç verir. AVX-512'de `vpconflictd` gibi çakışma tespiti komutları var. Pratik yol, birden fazla alt histogram tutup sonda toplamak.

---

## 6. Koşullu yazma: iki derleyici, zıt kararlar

```c
if (a[i] > 0) b[i] = a[i];              /* kosullu */
b[i] = a[i] > 0 ? a[i] : b[i];          /* secim  */
```

İkisi anlamca neredeyse aynı (fark: `secim` her `b[i]`'ye **yazıyor**; başka bir iş parçacığı `b`'yi okuyorsa bu fark önemli olabilir). Ölçümler:

| | clang | gcc |
| --- | --- | --- |
| `kosullu` | vektörlü, 0.395 | skaler, 0.922 |
| `secim` | maliyet modeli "yararsız", 0.645 | vektörlü, **0.075** |

Clang'in `kosullu` için ürettiği kod: vektörlü karşılaştırma, ardından her şerit için ayrı bir dal (`umov` + `tbnz` + `str`). NEON'da maskeli yazma komutu olmadığı için şerit şerit yazıyor. Gcc `secim`'de `bsl` ile seçip tüm vektörü yazıyor: **8 kat** daha hızlı. Clang'in maliyet modeli burada yanılmış görünüyor.

Ders: **Aynı kaynak, iki derleyici, 12 kata varan fark.** Kritik döngüde raporu oku, süreyi ölç; gerekirse döngüyü derleyicinin anlayacağı biçimde yaz (`secim` gibi koşulsuz atama) ya da elle intrinsic kullan.

Clang'e karar vermesine yardım edebilirsin:

```c
#pragma clang loop vectorize(enable) interleave_count(2)
for (int i = 0; i < n; i++) b[i] = a[i] > 0 ? a[i] : b[i];
```

`vectorize(enable)` maliyet modelini geçersiz kılar (doğruluk kontrollerini değil). Gcc'de karşılığı `#pragma GCC ivdep` (bağımlılık yok sözü) ve `#pragma omp simd` (`-fopenmp-simd` ile; ikisinde de çalışır).

---

## 7. Vektörleştiriciye yardım listesi

1. `restrict` ya da yerel kopya ile aliasing'i ortadan kaldır (Ders 11.5); yoksa çalışma zamanı kontrolü eklenir.
2. Float indirgemelerde ya sıra değiştirme izni ver ya da birikimcileri elle yaz.
3. `-fno-math-errno` (çoğu kod için zararsız).
4. Döngü sayacı için `int` yerine `long`/`size_t` kullanmak taşma analizini basitleştirebilir.
5. Koşullu yazma yerine koşulsuz seçim.
6. AoS yerine SoA (Ders 11.16).
7. Ve her zaman: rapor + süre.

---

## Alıştırmalar

**1** – `itoplam` gcc'de clang'in iki katı yavaş. İki derleyicinin ürettiği döngüyü karşılaştır; fark nereden gelebilir? (İpucu: "interleaved count".)

**2** – `bul`'u vektörleştirmenin güvenli yolunu tarif et. Hangi bilgi (dizinin boyutu dışında) gerekir?

**3** – `ftoplam`'da `-ffast-math` ile sonuç bu veride değişmedi (`-57`). Hangi girdide değişirdi?

**4** – `histogram`'ı dört ayrı alt histogramla yeniden yaz. Vektörleşir mi? Neden ya da neden değil?

**5** – `topla`'yı `restrict` olmadan derle ve `-Rpass-analysis` çıktısına bak. Ders 11.5'teki çalışma zamanı kontrolünü raporda görebiliyor musun?

<details>
<summary>Cevaplar</summary>

**1** – Clang `width 4, interleaved count 2` ile iki bağımsız vektör birikimci kullanıyor; gcc tek birikimci kullanıyorsa bağımlılık zinciri yarı hızda kalır (Ders 11.2). Doğrulamak için gcc'nin `-S` çıktısındaki iç döngüde kaç `add v...` olduğuna bak.

**2** – Okumanın izinli olduğunu kanıtlamak gerekir: ya `n`'e kadar hepsini okumak (önce bütün bloğu karşılaştırıp sonra ilk eşleşmeyi bulmak, `n` biliniyor), ya da Ders 11.12'deki gibi hizalı okumanın sayfa sınırını geçmediği bilgisi. İlki C'de güvenli: `n` sınırı içinde 4'erli bloklar, sonra `ctz`.

**3** – Büyüklükleri çok farklı değerlerin toplandığı veride, örneğin `1e8, 1, -1e8, 1, ...`. Sıralı toplamda küçük değerler büyüklerin içinde kaybolur; farklı sırada farklı kaybolur. Bu veride değerler küçük tamsayılar olduğundan bütün ara toplamlar tam ifade edilebiliyor ve sıra fark etmiyor.

**4** – `h0[a[i]]++; h1[a[i+1]]++; ...` yine dolaylı yazma; derleyici iki şeridin aynı yere yazmadığını bilemez, yine vektörleşmez. Ama skaler kod hızlanır: aynı değerin ardışık gelmesi durumundaki bellek bağımlılığı (Ders 11.1'deki store-to-load) dört ayrı tabloya dağılır.

**5** – Clang raporu yine "vectorized loop" der; `-Rpass-analysis` ayrıca bir not vermeyebilir. Kontrol assembly'de görünür: döngüden önce adres karşılaştırmaları ve iki ayrı döngü (Ders 11.5'teki `.LBB0_8`).

</details>

---

## Kaynaklar

- LLVM, "Auto-Vectorization in LLVM" (llvm.org/docs/Vectorizers.html) ve "Remarks" belgeleri.
- GCC, "Auto-vectorization in GCC" ve `-fopt-info` belgeleri.
- glibc 2.38 sürüm notları: aarch64 libmvec.
- Arm, *Vector Function ABI Specification for AArch64* (`_ZGV` isimlendirmesi).
- ISO/IEC 9899:2011, §7.12.1 (`math_errhandling`).

**Sıradaki ders:** Veri düzeni: AoS ve SoA. Struct dizisi ve dizi struct'ı, SIMD dostu düzen.
