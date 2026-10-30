---
title: "5.14 Sabite bölme"
description: "Bölme yavaş olduğu için derleyicinin sabit bir bölenle bölmeyi çarpmaya çevirmesi: x/3'ün x * 0xAAAAAAAB >> 33'e dönüşmesi, sihirli sayının (2^(32+s)/d yukarı yuvarlanmış) nereden geldiği, godbolt'ta derleyici çıktısının bununla birebir uyuşması, her d için sihirli sayı ve kaydırmayı bulup tüm 32-bit aralıkta doğrulayan bir program, ve 7 gibi 'zor' bölenlerin neden ek düzeltme gerektirdiği."
---

Ders 5.13'te bölmenin 32 adımlık, yavaş bir işlem; çarpmanın ise hızlı olduğunu gördük. Bu derste derleyicinin güzel bir numarasını çözüyoruz: **sabit** bir sayıya bölmeyi (örneğin `x / 3`) bir **çarpmaya** çevirmek. Çalışırken bölünen değişse de bölen sabitse, derleyici o pahalı bölmeyi bir çarpma ve bir kaydırmaya indiriyor. Nasıl yaptığını, "sihirli sayı"nın nereden geldiğini ve onu bulan programı yazacağız. İşaretsiz (`unsigned`) sayılarla.

---

## 1. Bölme neden çarpmaya dönüşür

`x / 3`, matematiksel olarak `x × (1/3)`. `1/3` bir tamsayı değil, ama `1/3 ≈ M / 2^k` biçiminde bir **kesir yaklaşımı** bulabiliriz: `M`, `2^k / 3`'e yakın bir tamsayı. O zaman:

$$\frac{x}{3} \approx \frac{x \times M}{2^k} = (x \times M) \gg k$$

Çarpma hızlı, kaydırma bedava; bölmeden kurtulduk. İş, `M`'yi (sihirli sayı) ve `k`'yı (kaydırma) öyle seçmekte ki sonuç **her** `x` için tam `x / 3`'e eşit olsun (yaklaşık değil, birebir).

`x / 3` için ölçtüğümüz değerler: `M = 0xAAAAAAAB`, kaydırma `33` (yani `k = 32 + 1`). Bütün 32-bit aralıkta (4 milyar değer) doğruladık: sıfır hata.

---

## 2. Derleyici zaten yapıyor

`x / 3u` yazıp `-O2` ile derlersek (bu makine, ARM):

```
_div3:
	mov	w8, #43691          ; 0xaaab
	movk	w8, #43690, lsl #16 ; ust yari 0xaaaa -> w8 = 0xAAAAAAAB
	umull	x8, w0, w8          ; x * M (64-bit sonuc)
	lsr	x0, x8, #33          ; >> 33
	ret
```

Hiç `div` komutu yok. Derleyici `M = 0xAAAAAAAB`'i yükledi, `x` ile çarptı (`umull`, Ders 5.13'teki geniş çarpma), ve `>> 33` yaptı. Bulduğumuz `M` ve kaydırmayla **birebir** aynı. `x / 7`, `x / 10`, `x / 100` — hepsi böyle çarpmaya dönüşür. Ders 3.15'te 65536'ya bölmenin kaydırmaya dönüştüğünü görmüştük; bu, 2'nin kuvveti **olmayan** sabitler için genel hali.

Bir koşul: bölen **derleme sırasında** sabit olmalı. `x / y` (ikisi de değişken) gerçek bir bölme komutu olur; `x / 3` (sabit) çarpmaya döner. Bu yüzden mümkünse sabit bölenler kullanmak (ya da bir döngüde değişmeyen böleni dışarı almak) performans kazandırır.

---

## 3. Sihirli sayı nereden geliyor

`M`, `2^k / d`'nin **yukarı yuvarlanmış** hali. `x / 3` için `k = 33` deneyelim: `2^33 / 3 = 2863311530.67`, yukarı yuvarlayınca `2863311531 = 0xAAAAAAAB`. İşte sihirli sayı.

Neden yukarı yuvarlama ve neden tam bu `k`? Yukarı yuvarlama, `M / 2^k`'nın `1/d`'den biraz **büyük** olmasını sağlar; bu, tamsayı bölmesinin aşağı yuvarlamasıyla birleşince doğru sonucu verir. `k` ise yeterince büyük olmalı ki yuvarlama hatası, `x`'in bütün değerleri için sonucu bozmasın — ama `M`'nin 32 bite sığacağı kadar küçük. Her `d` için en küçük geçerli `k`'yı deneyerek buluruz. Bu formülün tam türetimi ve neden işe yaradığının ispatı Hacker's Delight §10'da; sezgisi: "`1/d`'ye yukarıdan yakın bir kesir, yeterli hassasiyetle".

---

## 4. Sihirli sayıyı bulan program

Her `d` için `M` ve kaydırmayı bulup **tüm 32-bit aralıkta** doğrulayan program:

```c
#include <stdio.h>
#include <stdint.h>

int works(uint32_t d, uint64_t M, int s) {
    if (M >> 32) return 0;                    // M 32 bite sigmali
    for (uint64_t x = 0; x <= 0xFFFFFFFFull; x++) {
        uint32_t got = (uint32_t)(((uint64_t)(uint32_t)x * M) >> (32 + s));
        if (got != (uint32_t)x / d) return 0;
    }
    return 1;
}

int main(void) {
    uint32_t divs[] = {3, 5, 6, 7, 9, 10};
    for (int k = 0; k < 6; k++) {
        uint32_t d = divs[k];
        int found = 0;
        for (int s = 0; s < 32 && !found; s++) {
            uint64_t M = ((uint64_t)1 << (32 + s)) / d + 1;   // ceil(2^(32+s)/d)
            if (M >> 32) break;
            if (works(d, M, s)) {
                printf("d=%2u: M=0x%08llx s=%d\n", d, (unsigned long long)M, s);
                found = 1;
            }
        }
        if (!found) {
            printf("d=%2u: basit form YOK (duzeltme gerekli)\n", d);
        }
    }
    return 0;
}
```

```
d= 3: M=0xaaaaaaab s=1
d= 5: M=0xcccccccd s=2
d= 6: M=0xaaaaaaab s=2
d= 7: basit form YOK (duzeltme gerekli)
d= 9: M=0x38e38e39 s=1
d=10: M=0xcccccccd s=3
```

`M = ((1 << (32 + s)) / d) + 1`, tam Bölüm 3'teki "yukarı yuvarla" (`+ 1` yuvarlama). `works`, o `M` ve `s`'nin **her** `x` için doğru sonucu verdiğini 4 milyar değerle sınıyor — "ispatsız ama tam denenmiş" bir doğrulama (Ders 2.12'deki "test et" ilkesi, burada tüm uzayı kapsayacak kadar). `d = 3` için bulunan `M = 0xAAAAAAAB, s = 1` (kaydırma `32 + 1 = 33`), Bölüm 2'deki derleyici çıktısıyla **birebir** aynı. Derleyici de aynı aramayı (daha akıllıca, Hacker's Delight algoritmasıyla) derleme sırasında yapıyor.

---

## 5. "Zor" bölenler: 7 neden düzeltme istiyor

Program `d = 7` için "basit form yok" dedi. Neden? 7 için gereken `M`, basit `(x * M) >> k` formülünde 32 bite **sığmıyor** — yuvarlama hatasını telafi edecek `M`, 33 bite taşıyor. Bu "zor" bölenler için ek bir **düzeltme adımı** gerekir. Derleyicinin `x / 7` çıktısı bu yüzden birkaç komut daha uzun:

```c
// kavramsal: 7 icin duzeltmeli form
t = umulh(x, M);                    // x * M'nin yuksek yarisi (Ders 5.13)
q = (((x - t) >> 1) + t) >> 2;      // duzeltme ile
```

`umulh` (çarpımın yüksek yarısı; Ders 5.13) ve araya bir toplama-kaydırma giriyor. Hacker's Delight bu iki durumu (basit ve düzeltmeli) ayıran bir algoritma veriyor; derleyici her sabit bölen için hangisinin gerektiğini seçip uygun kodu üretiyor. Bölenlerin bazıları basit (3, 5, 9: `M` sığıyor), bazıları düzeltmeli (7, 11: taşıyor) — ikinin kuvvetleri ise en kolayı, sadece kaydırma (Ders 5.7).

Sonuç: bölme pahalı, ama **sabit** bölenle bölme neredeyse çarpma kadar ucuz, çünkü derleyici bu numarayı uyguluyor. Senin yapman gereken sadece böleni sabit tutmak; gerisini derleyici halleder. (İşaretli bölmede ek düzeltmeler var — negatif sayıda `/` sıfıra yuvarlar, Ders 5.7 — o yüzden işaretli sabit bölme biraz daha uzun kod üretir.)

---

## Alıştırmalar

**1** – `x / 4`'ün sihirli sayısı ne? (İpucu: 4 bir 2'nin kuvveti; Ders 5.7.) Derleyici bunu çarpmaya mı yoksa kaydırmaya mı çevirir, neden?

**2** – Bölüm 4'teki programda `d = 100` için `M` ve `s`'yi bul (programı çalıştır ya da elle `ceil(2^(32+s)/100)`'ü dene). `x / 100` (bir sayının yüzlük kısmını almak, Ders 3.11'deki sabit nokta) bu yüzden neden ucuz?

**3** – `M = 0xAAAAAAAB`, `s = 1` ile `x = 3`, `x = 6`, `x = 7` için `(x * M) >> 33`'ü hesapla (64-bit çarpma gerekir). Sonuçlar `3/3=1`, `6/3=2`, `7/3=2` mi?

**4** – Bölüm 4'teki `works`, 4 milyar değeri deniyor — birkaç saniye sürer. Bu bir **ispat** mı, yoksa sadece çok kapsamlı bir test mi? Tüm 32-bit `x`'i denemek, `M` ve `s`'nin doğruluğunu garanti eder mi, yoksa 64-bit `x` için de mi genellenir?

**5** – `x / 3` çarpmaya dönüşürken `x % 3` ne olur? (İpucu: `x % 3 == x - (x / 3) * 3`.) Derleyici `x % 3`'ü de bölmesiz hesaplayabilir mi? Bir sayının 3'e tam bölünüp bölünmediğini (`x % 3 == 0`) bölmesiz test eden bir yol var mı?

<details>
<summary>Cevaplar</summary>

**1** – `x / 4`'ün "sihirli sayısı" yok — 4 bir 2'nin kuvveti (`2²`), ve 2'nin kuvvetine bölme sadece bir **kaydırma**: `x / 4 == x >> 2` (Ders 5.7). Derleyici bunu çarpmaya değil, tek bir `lsr x, 2` komutuna çevirir — çarpmadan da ucuz. Sihirli sayı numarası sadece 2'nin kuvveti **olmayan** bölenler (3, 5, 7, …) için gerekir; 2'nin kuvvetleri zaten kaydırma.

**2** – `d = 100`: `ceil(2^(32+s)/100)` denendiğinde (program) bir `M, s` çifti bulur (örneğin `s` birkaç, `M` 32 bite sığan bir değer — `0x28F5C29` civarı bir aile). `x / 100` ucuz, çünkü bölme yerine bir çarpma + kaydırmaya dönüşür. Ders 3.11'de sabit noktalı sayılarda sürekli `/ 100` ve `% 100` yapıyorduk (kuruş/lira); bunların hepsi derleyici tarafından çarpmaya çevrildiği için, sabit noktalı aritmetik gerçek bölme yapmaz, hızlıdır.

**3** – `x = 3`: `3 * 0xAAAAAAAB = 0x2_00000001`, `>> 33` = `0x2_00000001 >> 33` = 1. `6/3`: `6 * 0xAAAAAAAB = 0x4_00000002`, `>> 33` = 2. `7/3`: `7 * 0xAAAAAAAB = 0x4_AAAAAAA5`, `>> 33`: `0x4AAAAAAA5 >> 33` = 2. Sonuçlar 1, 2, 2 — tam `3/3`, `6/3`, `7/3`. Yukarı yuvarlanmış `M` ve 33 kaydırma, tamsayı bölmesinin aşağı yuvarlamasını doğru taklit ediyor.

**4** – Bütün 2³² olası `uint32_t` `x` değerini denemek, **32-bit `x` için bir ispattır**: `x` yalnızca 2³² değer alabildiği için hepsini denemek, o aralıkta `M, s`'nin doğruluğunu kesin kanıtlar (tükenme/exhaustive proof). Ama **64-bit `x` için genellenmez**: 64-bit bölünenler için `M` ve kaydırma farklı olur, ve 2⁶⁴ değeri denemek imkânsız — orada Hacker's Delight'ın cebirsel ispatı gerekir. Küçük uzaylarda tükenmeli test bir ispat yerine geçer (Faz 19'daki SMT çözücüler de benzer bir fikir); büyük uzaylarda matematiksel ispat şart.

**5** – `x % 3 = x - (x / 3) * 3`. Derleyici `x / 3`'ü çarpmaya çevirdikten sonra, `% 3`'ü de **bölmesiz** hesaplar: sihirli çarpmayla `q = x/3` bul, sonra `x - q*3` (bir çarpma, bir çıkarma). Hiç bölme komutu yok. "3'e tam bölünür mü?" (`x % 3 == 0`) için daha hızlı bir yol da var: `x * 0xAAAAAAAB <= 0x55555555` gibi bir eşik testi (Granlund-Montgomery yöntemi) — tek çarpma ve bir karşılaştırma, bölme ya da mod olmadan. Derleyiciler `x % 3 == 0`'ı bazen bu biçime çevirir. Bölünebilirlik testi, modun kendisinden bile ucuz olabilir.

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §10: sabite bölme, sihirli sayı türetimi ve ispatı.
- Torbjörn Granlund & Peter Montgomery, "Division by Invariant Integers using Multiplication" (PLDI 1994): derleyicilerin kullandığı algoritma.
- Daniel Lemire, "Faster Remainders When the Divisor Is a Constant": bölünebilirlik ve mod hızlandırma.
- godbolt.org: `x / d` çıktısını farklı `d` ve derleyicilerle incelemek.

**Sıradaki ders:** Bit düzeyinde tamsayı fonksiyonları. Bit bit karekök, tamsayı log₂ ve log₁₀.
