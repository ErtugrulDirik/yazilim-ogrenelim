---
title: "7.15 Derleyici optimizasyon seviyeleri"
description: "-O0, -O1, -O2, -O3, -Os seviyelerinin anlamı; -O0'ın neden hata ayıklama için, -O2'nin üretim için olduğu; sabit katlama (3²+4² → 25), ölü kod eleme, register'da tutma, döngü değişkeni analiziyle bir döngünün kapalı forma (Gauss) çevrilmesi, -O3'te vektörleştirme; optimizasyonun sonucu değiştirmemesi gerektiği ve işaretli taşma/UB'nin (Faz 3) buna nasıl karıştığı; optimizasyonun hata ayıklamayı neden zorlaştırdığı."
gereksinimler: [gcc]
---

Bu faz boyunca derleyici çıktılarına bakarken çoğunlukla `-O1` ya da `-O2` kullandık, ve bazen şaşırtıcı şeyler gördük: Ders 7.11'de bütün bir fonksiyonun kaybolması, Ders 7.9'da bir döngünün kapalı formüle dönüşmesi. Bunlar **optimizasyon**: derleyicinin, aynı sonucu veren ama daha hızlı/küçük kod üretme çabası. Bu ders optimizasyon seviyelerini sistemli tanıtıyor ve Faz 16'da yazacağımız optimizasyon geçişlerinin (sabit katlama, ölü kod eleme, döngü dönüşümleri) ilk örneklerini gösteriyor.

---

## 1. Seviyeler

| Bayrak | Anlamı |
| --- | --- |
| `-O0` | Optimizasyon yok (varsayılan). Her C ifadesi birebir, her değişken bellekte. Hızlı derler, yavaş çalışır, **hata ayıklanabilir**. |
| `-O1` | Temel optimizasyonlar. Sabit katlama, ölü kod eleme, basit register tahsisi. |
| `-O2` | Daha agresif. Döngü optimizasyonları, inline, çoğu üretim kodunun seçimi. |
| `-O3` | En agresif. Vektörleştirme (SIMD), agresif inline; bazen kod şişer. |
| `-Os` | Boyut için optimize (hız yerine küçük kod; cache ve gömülü için). |

Temel kural: **geliştirme/hata ayıklama `-O0 -g`, üretim `-O2`.** `-O3` her zaman `-O2`'den hızlı değil (kod şişmesi cache'i, Ders 7.24, bozabilir); ölçmeden (Faz 11) seçilmez.

---

## 2. Sabit katlama ve ölü kod

En temel optimizasyon: derleme zamanında bilinen hesapları **önceden yap**.

```c
int sabit(void) { int a = 3, b = 4; return a*a + b*b; }
```

**-O0:**
```
sabit:  pushq  %rbp
        movq   %rsp, %rbp
        movl   $3, -4(%rbp)        # a = 3
        movl   $4, -8(%rbp)        # b = 4
        movl   -4(%rbp), %eax
        imull  -4(%rbp), %eax      # a*a
        movl   -8(%rbp), %ecx
        imull  -8(%rbp), %ecx      # b*b
        addl   %ecx, %eax          # a*a + b*b
        popq   %rbp
        retq
```

**-O1 (ve üstü):**
```
sabit:  movl   $25, %eax          # = 3*3 + 4*4, derleme zamaninda hesaplandi
        retq
```

`-O0` her adımı tek tek, belleğe yazıp okuyarak yapıyor (11 komut). `-O1` ise `a` ve `b`'nin sabit olduğunu görüp **bütün ifadeyi 25'e katladı** (**sabit katlama**, constant folding) ve kullanılmayan `a`, `b` değişkenlerini tamamen **eledi** (**ölü kod eleme**, dead code elimination). Fonksiyon tek komuta indi. İkisi de aynı sonucu (25) veriyor — optimizasyonun **değişmez** kuralı: davranış aynı, hız farklı.

Bunlar Faz 6.23'te derleyicinin halka yasalarıyla yaptığı dönüşümlerin (örneğin `x*9 → x+(x<<3)`) kardeşi; Faz 16'da bir "sabit katlama geçişi" (constant folding pass) yazacağız.

---

## 3. Register'da tutma ve döngü dönüşümü

`-O0`'ın en pahalı alışkanlığı: her değişkeni her kullanımda bellekten okuyup belleğe yazmak (Ders 7.11'deki `-4(%rbp)` erişimleri). `-O1`+ değişkenleri mümkün olduğunca **register'da** tutar (Ders 6.30'daki register tahsisi), bellek erişimini en aza indirir. Ders 7.1'deki `sum` döngüsünün neden bu kadar sıkı olduğunu (toplam `rax`'te, hiç belleğe yazmadan) bu açıklıyor.

Daha çarpıcısı, **döngü değişkeni analizi** (induction variable / scalar evolution). Bir toplam döngüsü:

```c
long topla_n(long n) { long s = 0; for (long i = 1; i <= n; i++) s += i; return s; }
```

`-O0`'da bu gerçek bir döngü (iki dal). `-O2`'de:

```
topla_n: testq  %rdi, %rdi
         jle    .sifir
         leaq   -1(%rdi), %rax
         leaq   -2(%rdi), %rcx
         mulq   %rcx                # (n-1)(n-2)
         shldq  $63, %rax, %rdx     # / 2
         leaq   (%rdx,%rdi,2), %rax
         decq   %rax
         retq
```

**Döngü yok!** Derleyici, döngünün $1 + 2 + \dots + n = \frac{n(n+1)}{2}$ hesapladığını (Ders 6.4, 6.10'daki Gauss formülü) **anladı** ve bütün döngüyü birkaç çarpma/kaydırma ile değiştirdi. $n = 10^9$ için döngü bir milyar tur dönerdi; bu kod sabit sürede. Çalıştırıp doğrulayalım:

```
O0: 25 5050
O2: 25 5050
```

İki seviye de aynı ($\text{topla\_n}(100) = 5050$, Gauss). Derleyici Faz 6'daki matematiği biliyor ve uyguluyor; bu, Faz 16'daki "döngü optimizasyonları"nın en gösterişli örneği. (Her döngü böyle kapatılamaz; sadece derleyicinin kapalı formülünü tanıdığı desenler. Dizi toplamı, elemanlar bilinmediği için kapatılamaz — bir sonraki bölüm.)

---

## 4. -O3 ve vektörleştirme

Kapalı forma çevrilemeyen bir döngü — dizi toplamı, elemanlar çalışma zamanında belli:

```c
long arrsum(const long *a, long n) { long s=0; for (long i=0;i<n;i++) s+=a[i]; return s; }
```

`-O1`'de sıradan bir döngü (Ders 7.1). `-O3`'te:

```
arrsum: ...
        movdqu (%rdi,%rax,8), %xmm2    # 2 long'u BIRDEN oku (128 bit)
        paddq  %xmm2, %xmm1            # 2 toplami paralel yap
        movdqu 16(%rdi,%rax,8), %xmm2  # sonraki 2
        paddq  %xmm2, %xmm0
        addq   $4, %rax                # 4 eleman ilerle
        ...
```

`-O3`, döngüyü **vektörleştirdi**: `xmm` register'larıyla (128 bit, Ders 7.29) her turda iki (hatta dört) elemanı **paralel** topluyor. Bir turda bir eleman yerine dört; döngü dört kat az dönüyor. Bu, Faz 11'in (SIMD) konusu; burada sadece `-O3`'ün ne kadar ileri gidebildiğini görüyoruz. Vektörleştirme her döngüde mümkün değil (bağımlılıklar, Ders 6.28'deki döngü dönüşümleri izin vermeli) ve kodu büyütür; bu yüzden `-O2` değil `-O3`.

---

## 5. Optimizasyon ve undefined behavior

Optimizasyonun tek kuralı: **gözlemlenebilir davranışı değiştirmemek**. Ama "davranış" ne? C standardının tanımladığı davranış. Tanımsız davranış (UB, Ders 2.12) içeren bir program için standart hiçbir şey garanti etmez, ve derleyici UB'nin **hiç olmadığını varsayarak** optimize eder.

Ders 6.23'te gördüğümüz örnek: `int x; x + 1 > x` ifadesini derleyici `-O1`+ ile `return 1`'e çevirir, çünkü işaretli taşma UB'dir ve derleyici "taşma olmaz" varsayar. `unsigned` için aynı kodu çeviremez (sarma tanımlı, Ders 3.8). Yani optimizasyon seviyesi arttıkça, UB içeren programlar **daha tehlikeli** davranabilir: `-O0`'da "çalışan" bir kod `-O2`'de beklenmedik sonuç verebilir — kod yanlış değil, UB içeriyor ve derleyici bunu sömürüyordu. Faz 3'teki UBSan ve "UB'den kaçın" dersinin pratik önemi burada: optimizasyon, gizli UB'yi ortaya çıkaran şey.

Bu yüzden optimizasyon bir "sihir" değil, standardın izin verdiği dönüşümlerin uygulanması. Doğru (UB'siz) bir program her seviyede aynı sonucu verir (Bölüm 2–3'teki `25`, `5050`); UB'li bir program vermeyebilir. Faz 16'da optimizasyon yazarken bu sınırı — "ne zaman bir dönüşüm güvenli?" — sürekli düşüneceğiz.

---

## 6. Optimizasyon ve hata ayıklama

`-O2` kod hızlı ama hata ayıklaması zor:

- Değişkenler register'da ya da hiç yok (Ders 7.11'deki `-O2` örneğinde `tmp` yok oldu); hata ayıklayıcı "optimized out" der.
- Satırlar yeniden sıralanır, birleşir; tek bir C satırında durmak anlamını yitirir.
- Fonksiyonlar inline olur; backtrace'te görünmeyebilir.

Bu yüzden:

- **Hata ayıklarken** `-O0 -g`: her değişken bellekte, her satır izlenebilir, backtrace güvenilir (Ders 7.11).
- **Ölçerken ve üretimde** `-O2` (ya da `-O2 -g`, hata ayıklama bilgisini tutup optimizasyonu da açarak — ortada bir denge).

Bir hatayı `-O0`'da bulamayıp sadece `-O2`'de görürsen, bu genellikle bir **UB işareti** (Bölüm 5): kod bir şeye güveniyor ki standart garanti etmiyor, ve optimizasyon onu ortaya çıkarıyor. O zaman çözüm optimizasyonu kapatmak değil, UB'yi bulup düzeltmek (sanitizer'larla, Ders 4.23).

---

## Alıştırmalar

**1** – `int f(void){int x=10; int y=x*2; int z=y+5; return z;}`'yi `-O0` ve `-O1` ile derle. `-O1` kaç komuta iniyor, ve neden? Hangi optimizasyonlar uygulandı (sabit katlama, ölü kod)?

**2** – Bir fonksiyonda hiç kullanılmayan pahalı bir hesap olsun: `int g(int a){int unused = a*a*a*a; return a+1;}`. `-O1`'de `unused` hesaplanıyor mu? Neden? Ya `unused` bir fonksiyon çağrısı olsaydı (`int unused = f(a);`), derleyici onu eleyebilir miydi?

**3** – `topla_n`'in kapalı forma çevrilmesi (Bölüm 3) her döngüde olur mu? `long carp_n(long n){long p=1; for(long i=1;i<=n;i++) p*=i; return p;}` (faktöriyel) için `-O2` döngüyü kapatabilir mi? Neden faktöriyel toplamadan farklı?

**4** – `int ub(int x){return x+1 > x;}`'i `-O0`, `-O1`, `-O2` ile derle. Her seviyede ne üretiyor? `unsigned ub2(unsigned x){return x+1 > x;}` ile karşılaştır (Ders 6.23). Hangisi UB içeriyor?

**5** – Bir kod `-O0`'da doğru çalışıp `-O2`'de yanlış sonuç veriyor. İlk şüphen ne olmalı, ve nasıl araştırırsın? (İpucu: `-fsanitize=undefined,address` ile derle, Ders 4.23; derleyicinin değil, kodun hatası olabilir.)

<details>
<summary>Cevaplar</summary>

**1** – `-O1` tek komuta iner: `movl $25, %eax`. `x=10` sabit → `y = 20` (sabit katlama) → `z = 25` (sabit katlama); `x`, `y`, `z` değişkenleri elenir (ölü kod eleme, çünkü sadece `z` döndürülüyor ve o da sabit). Zincirleme sabit katlama bütün fonksiyonu tek bir sabite indirdi.

**2** – `-O1`'de `unused = a*a*a*a` **hesaplanmaz**: sonucu hiçbir yerde kullanılmıyor (ölü kod), derleyici eler. Üç çarpma yok olur, sadece `a+1` kalır. Ama `unused = f(a)` olsaydı, derleyici `f`'in **yan etkisi** (ekran yazma, global değişken değiştirme) olup olmadığını bilemezse çağrıyı eleyemez — yan etki gözlemlenebilir davranıştır (Bölüm 5). `f` "saf" (pure, yan etkisiz) olduğu derleyiciye belliyse (aynı dosyada görüp inline edebilirse, ya da `__attribute__((pure))` ile) eleyebilir; yoksa güvenli tarafta kalıp çağrıyı tutar.

**3** – Hayır, her döngü kapatılamaz. Faktöriyel $\prod i = n!$'in kapalı bir **polinom** formülü yok (Ders 6.14'teki Stirling bir yaklaşım, tam değil); derleyicinin tanıyacağı bir kapalı form olmadığı için `carp_n` döngü olarak kalır. Toplama ($\sum i$) ise $\frac{n(n+1)}{2}$ polinomu, derleyicinin "döngü değişkeni analizi" bunu tanır. Fark: toplama doğrusal birikim (kapalı polinom var), çarpma değil. Derleyici sadece bildiği desenleri kapatır.

**4** – `ub` (işaretli): `-O0`'da gerçek `x+1 > x` karşılaştırması (`add`, `cmp`, `setg`); `-O1`/`-O2`'de `movl $1, %eax` (her zaman 1), çünkü işaretli taşma UB, derleyici "taşmaz → hep doğru" varsayar. `ub2` (işaretsiz): her seviyede gerçek karşılaştırma üretir (`x=UINT_MAX`'te sarar, yanlış olur, Ders 3.8), kısaltamaz. `ub` UB içeriyor (işaretli taşma); `ub2` içermiyor (işaretsiz sarma tanımlı). Optimizasyon, UB'nin davranışı nasıl değiştirdiğini gösteriyor.

**5** – İlk şüphe: **tanımsız davranış** (UB), kodun hatası — derleyicinin değil (Bölüm 5, 6). Optimizasyon çoğu zaman gizli bir UB'yi (işaretsiz/işaretli karıştırma, başlatılmamış değişken, sınır dışı erişim, aliasing ihlali) ortaya çıkarır. Araştırma: `-fsanitize=undefined,address` ile derleyip çalıştır (Ders 4.23); UBSan/ASan hatayı işaret eder. `-O0`'da "çalışması" bir tesadüf; `-O2`'de "bozulması" derleyicinin UB'yi sömürmesi. Çözüm optimizasyonu kapatmak değil (hatayı gizler), UB'yi bulup düzeltmek. (Nadir durumlarda gerçekten derleyici hatası olabilir, ama önce kendi kodundan şüphelen.)

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 5: optimizasyon, derleyici sınırları, ölçme.
- GCC belgeleri, "Options That Control Optimization" (`-O` seviyelerinin tam listesi).
- Chris Lattner, "What Every C Programmer Should Know About Undefined Behavior" (LLVM blog, 3 bölüm): UB ve optimizasyon ilişkisi.
- Ders 2.12 (UB), 3.8 (taşma), 4.23 (sanitizer'lar): bu dersin UB tarafının önceli.

**Sıradaki ders:** Nesne dosyaları ve ELF. Bölümler, sembol tablosu, `readelf`, `objdump`, `nm`.
