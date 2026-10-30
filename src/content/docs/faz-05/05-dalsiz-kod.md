---
title: "5.5 Dalsız (branchless) kod"
description: "if olmadan hesaplamak: x >> 31 ile işaret maskesi, (x ^ mask) - mask ile mutlak değer (ve INT_MIN tuzağı), (x>0)-(x<0) ile işaret, maske ile dalsız min/max ve koşullu atama. Dal tahmininin ne olduğu, yanlış tahminin maliyeti, ve modern derleyicinin basit koşulları zaten csel/cmov ile dalsız derlediği — el ile dalsız yazmanın ne zaman gerçekten gerektiği."
---

Şimdiye kadar `if` ile dallandık: koşul doğruysa şunu, değilse bunu yap. Bu derste aynı işi **dal olmadan**, sadece aritmetik ve bit işlemleriyle yapmayı öğreniyoruz. İki sebeple: biri, işlemcinin dalları nasıl ele aldığını (dal tahmini) ve dalsız kodun ne zaman daha hızlı olduğunu anlamak; diğeri, bu tekniklerin kendi başına zarif ve öğretici olması. Ama en önemli ders, modern derleyicinin bunların çoğunu **zaten senin için yaptığı** olacak.

İşaret maskeleri için işaretli sağa kaydırmanın aritmetik olmasına güveniyoruz (Ders 5.1); bu makinede öyle.

---

## 1. İşaret maskesi: her şeyin temeli

Dalsız kodun anahtarı tek bir numara: işaretli bir sayıyı 31 kaydırmak, **işaret bitini** 32 bite yayar.

```c
int32_t mask = x >> 31;
```

- `x` negatifse işaret biti 1, aritmetik kaydırma soldan hep 1 getirir: `mask = 0xFFFFFFFF` = bütün bitler 1 = `-1`.
- `x` pozitif ya da 0 ise işaret biti 0: `mask = 0`.

Yani `x >> 31`, "`x` negatif mi?" sorusunu bir **maskeye** çeviriyor: negatifse `-1` (tüm bitler 1), değilse `0`. Bir koşulu `if` yerine bir sayıya dönüştürmenin yolu bu. Bütün dalsız formüller bunun üzerine kurulu.

---

## 2. Mutlak değer

```c
int32_t abs_branchless(int32_t x) {
    int32_t mask = x >> 31;        // negatifse -1, degilse 0
    return (x ^ mask) - mask;
}
```

Nasıl çalışıyor, iki duruma bakarak:

- **`x >= 0`**: `mask = 0`. `(x ^ 0) - 0 = x`. Değişmez.
- **`x < 0`**: `mask = -1` (tüm bitler 1). `x ^ -1 = ~x` (Ders 5.1), ve `~x - (-1) = ~x + 1 = -x` (Ders 5.3'teki iki tümleyen). Yani `-x`, mutlak değer.

```
x=-3 abs=3    x=-1 abs=1    x=0 abs=0    x=2 abs=2
```

Tek bir `if` yok; sadece bir kaydırma, bir XOR, bir çıkarma. 

**INT_MIN tuzağı.** `abs(INT_MIN)` matematiksel olarak 2147483648, ama bu bir `int32_t`'ye sığmaz (Ders 3.8). Formül `INT_MIN`'i geri verir (taşma); standart `abs` de bu durumda undefined behavior. Dalsız sürüm "sihirli" değil — aritmetiğin sınırlarına o da tabi.

---

## 3. İşaret fonksiyonu

Bir sayının işaretini (−1, 0, +1) dalsız vermek, Ders 3.21'deki `(x > 0) - (x < 0)` kalıbı:

```c
int sign(int32_t x) {
    return (x > 0) - (x < 0);
}
```

```
x=-3 sign=-1    x=0 sign=0    x=2 sign=1
```

`x > 0` ve `x < 0` karşılaştırmaları 0 ya da 1 veriyor (Ders 2.3); farkları üç durumu kapsıyor: pozitifte `1 - 0 = 1`, negatifte `0 - 1 = -1`, sıfırda `0 - 0 = 0`. Karşılaştırma operatörlerinin kendisi de bir tür dalsız koşul: sonucu doğrudan bir sayı.

---

## 4. min, max ve koşullu atama

Maske ile min/max, dalsız kodun klasik gösterisi:

```c
int32_t min_bl(int32_t a, int32_t b) {
    return b ^ ((a ^ b) & -(a < b));
}
```

`-(a < b)`: `a < b` ise `-1` (tüm bitler 1), değilse `0` — Bölüm 1'deki maske, bu sefer bir karşılaştırmadan. Sonra:

- **`a < b`**: maske `-1`, `(a ^ b) & -1 = a ^ b`, `b ^ (a ^ b) = a`. Küçük olan `a`.
- **`a >= b`**: maske `0`, `(a ^ b) & 0 = 0`, `b ^ 0 = b`. Küçük olan `b`.

```
min(7,3)=3  max(7,3)=7  min(-5,2)=-5
```

Genel kalıp **koşullu atama**: "koşul doğruysa `a`, değilse `b`" = `b ^ ((a ^ b) & -koşul)`. Bir `if`/`else`'i tek satır aritmetiğe indiriyor.

Ama dur — bunu gerçekten elle yazmalı mısın?

---

## 5. Derleyici zaten yapıyor

Yukarıdaki `min_bl` çirkin. Oysa sıradan haliyle yazarsak:

```c
int max_if(int a, int b) {
    return a > b ? a : b;
}
```

`-O2` ile derleyicinin ürettiği (bu makine, ARM):

```
_max_if:
	cmp	w0, w1
	csel	w0, w0, w1, gt
	ret
```

Üç komut, ve ortadaki `csel` (conditional select) **bir dal değil**: "koşula göre iki değerden birini seç", tek komutta, dallanmadan. x86'da buna `cmov` (conditional move) denir. Yani derleyici, `a > b ? a : b` üçlü ifadesini **zaten dalsız** derledi — bizim `min_bl`'deki XOR hilesini elle yazmamıza gerek yok.

Bu, dersin asıl mesajı: **modern derleyiciler basit koşulları kendiliğinden dalsız yapıyor.** `abs`, `min`, `max`, basit koşullu atamalar — hepsini sıradan `if`/üçlü ile yaz, derleyici `csel`/`cmov`'a çevirsin. Elle XOR hileleri yazmak kodu okunmaz yapar ve çoğu zaman daha hızlı bile değildir. Bu formülleri **anlamak** değerli (bir donanımın, bir derleyicinin ne yaptığını görmek için); elle **yazmak** nadiren gerekir.

---

## 6. Dal tahmini: neden bazen önemli

Peki dalsız kod ne zaman gerçekten kazandırır? İşlemcinin dalları nasıl ele aldığını bilmek gerekiyor.

Modern işlemciler komutları bir **boru hattında** (pipeline) işliyor: bir komut bitmeden sonrakine başlıyor, aynı anda düzinelerce komut yolda. Bir `if` gelince sorun doğar: işlemci koşulun sonucunu beklemeden hangi yoldan devam edeceğini bilemez. Beklemek yerine **tahmin** ediyor (branch prediction) ve tahmin ettiği yoldan komutları işlemeye devam ediyor. Tahmin **doğruysa** hiç kayıp yok. **Yanlışsa**, boru hattındaki yanlış yolun bütün komutlarını atıp doğru yoldan başlamak zorunda — bu makinelerde ~15-20 çevrim kayıp.

Tahmin ne zaman yanlış olur? Koşul **öngörülemez** olduğunda. Rastgele veride bir eşik kontrolü (`if (a[i] >= 128)`) yarı yarıya iki yöne gider; tahminci şaşırır. Sıralı veride ise uzun süre hep aynı yön; tahminci öğrenir. Ünlü deney — aynı döngüyü rastgele ve sıralı dizide çalıştırmak:

```c
for (int i = 0; i < n; i++) {
    if (a[i] >= 128) { /* bir is */ } else { /* baska is */ }
}
```

Bu makinede (Apple M2):

```
RASTGELE: 0.446 s
SIRALI:   0.410 s
```

Sıralı veri ~%10 hızlı — çünkü dal tahmini neredeyse hiç şaşmıyor. Ama fark **küçük**. Eski x86 işlemcilerde bu deney 6 kata varan farklar verirdi ("neden sıralı dizi daha hızlı" diye ünlü bir soru); modern işlemcilerin (özellikle Apple Silicon'ın) dal tahmincileri o kadar iyi ki fark çok küçüldü. Ve derleyici koşulu `csel`'e çevirebildiğinde fark **tamamen** kaybolur (dal yok, tahmin edilecek bir şey yok).

Sonuç: dalsız kod, **öngörülemez** bir dalın **sıkı bir iç döngüde** olduğu ve derleyicinin onu kendiliğinden kaldıramadığı durumlarda kazanır. Bunlar gerçek ama nadir; çoğu kodda okunabilir `if` yazıp derleyiciye güvenmek doğru. Ölçmeden dalsız "optimizasyonu" yapmak, genelde sadece kodu çirkinleştirir (Ders 2.12'deki "önce ölç" ilkesi).

---

## Alıştırmalar

**1** – `x >> 31` maskesini `x = 5` ve `x = -5` için hesapla (`int32_t`). Sonra `abs_branchless`'i ikisi için elle, adım adım (`x ^ mask`, sonra `- mask`) izle.

**2** – İki sayının aynı işarette olup olmadığını dalsız test et: `(x ^ y) >= 0` neden "aynı işaret" demek? (İpucu: işaret bitleri.) `0` hangi gruba düşer?

**3** – `max_if` gibi `min_if(a, b) { return a < b ? a : b; }`'i yaz, `-O2` ile derleyip assembly'de `csel` olup olmadığına bak (`clang -O2 -S`). Elle yazdığın `min_bl` ile üretilen kod aynı mı?

**4** – Dalsız "koşul doğruysa `x`'e `delta` ekle, değilse dokunma": `x += delta & -(cond)`. `cond` 0/1 iken bu neden çalışıyor? `cond` 2 olursa (0/1 değil) ne olur, ve neden `!!cond` ya da `cond != 0` ile korumalısın?

**5** – Bölüm 6'daki dal tahmini deneyini kendi makinende çalıştır (rastgele vs sıralı). Farkı ölç. Sonra `if`'i `sum += a[i] & -(a[i] >= 128)` ile dalsız yaz ve rastgele veride dalsız sürümün dallıdan hızlı olup olmadığına bak. Derleyici zaten `csel` ürettiyse fark olur mu?

<details>
<summary>Cevaplar</summary>

**1** – `x = 5`: işaret biti 0, `5 >> 31 = 0`. `abs`: `(5 ^ 0) - 0 = 5`. `x = -5`: işaret biti 1, `-5 >> 31 = -1` (aritmetik, tüm bitler 1). `abs`: `-5 ^ -1 = ~(-5) = 4`, `4 - (-1) = 5`. İki durumda da mutlak değer, dalsız.

**2** – `(x ^ y) >= 0` "aynı işaret" demek, çünkü XOR iki sayının **işaret bitlerini** karşılaştırır: ikisi de pozitif ya da ikisi de negatifse işaret bitleri aynı, XOR'da o bit 0 → sonuç pozitif (işaret biti 0, `>= 0`). İşaretler farklıysa işaret bitleri farklı, XOR'da 1 → sonuç negatif. `0` pozitif sayılır (işaret biti 0), yani `0` ile herhangi bir pozitif "aynı işaret" grubuna düşer, negatifle düşmez.

**3** – `min_if` de `csel` üretir:

```
cmp w0, w1
csel w0, w0, w1, lt
ret
```

`max_if`'in aynısı, sadece koşul `gt` yerine `lt`. Elle yazılan `min_bl`'in XOR hilesi muhtemelen daha fazla komut üretir (üç XOR/AND, bir negate); `csel` tek komutta aynı işi yapar. Yani üçlü ifade hem okunur hem derleyicinin ürettiği dalsız koddan daha kötü değil — elle hile yazmanın gereksizliğinin kanıtı.

**4** – `x += delta & -(cond)`: `cond` 1 ise `-(1) = -1` (tüm bitler 1), `delta & -1 = delta`, eklenir. `cond` 0 ise `-(0) = 0`, `delta & 0 = 0`, hiçbir şey eklenmez. `cond` 0/1 olduğu sürece doğru. Ama `cond = 2` olursa `-(2) = 0xFFFFFFFE` (tüm bitler 1 değil, bit 0 eksik), `delta & 0xFFFFFFFE` `delta`'nın bit 0'ını siler — yanlış. Bu yüzden koşulun kesin 0/1 olması gerekir; `a < b` gibi karşılaştırmalar zaten 0/1 verir, ama rastgele bir `int`'i koşul olarak kullanıyorsan `!!cond` ya da `(cond != 0)` ile 0/1'e indir.

**5** – Sonuç makineye bağlı; modern bir işlemcide rastgele/sıralı farkı küçük (bu makinede ~%10), eski bir x86'da büyük (birkaç kat) olabilir. Dalsız `sum += a[i] & -(a[i] >= 128)` rastgele veride dallıdan hızlı **olabilir** (tahmin şaşmasını ortadan kaldırır), ama derleyici dallı sürümü zaten `csel`/vektör koduna çevirdiyse ikisi aynı hıza gelir, elle dalsız yazmanın faydası olmaz. Asıl ders: önce ölç; derleyicinin ne ürettiğine (godbolt) bak; dalsızı sadece gerçekten öngörülemez, sıkı bir döngüde ve derleyici kaldıramıyorsa elle yaz.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §2.19 (dalsız min/max, abs, sign).
- Sean Anderson, "Bit Twiddling Hacks": branchless abs, sign, min/max.
- Agner Fog, "Optimizing software in C++" ve mikromimari kılavuzları: dal tahmini ve `cmov`/`csel`.
- Ulrich Drepper, "What Every Programmer Should Know About Memory": boru hattı ve dal maliyeti.

**Sıradaki ders:** Taşma algılama ve döndürme (rotate). Toplama/çarpmada taşmayı bit düzeyinde bulmak ve derleyicinin `rol` komutu üretmesi.
