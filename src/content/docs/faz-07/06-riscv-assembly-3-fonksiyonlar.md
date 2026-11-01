---
title: "7.6 RISC-V assembly 3: fonksiyonlar"
description: "Çağrı kuralı (calling convention) neden bir sözleşme; jal ve jalr; ra ile dönüş; a0–a7 argüman ve dönüş register'ları; caller-saved (t, a) ve callee-saved (s, sp) ayrımı; yığın (stack) ve sp; prolog ve epilog; yaprak fonksiyon ile özyinelemeli faktöriyelin yığın çerçevesini elle kurmak."
gereksinimler: [rars]
---

Ders 7.5'te kararı ve döngüyü kurduk. Geriye bir büyük yapı kaldı: **fonksiyon çağrısı**. Faz 2.7'de bir fonksiyonun stack'te kendi frame'ini açtığını, Ders 2.8'de özyinelemenin bu frame'leri üst üste yığdığını görmüştük — ama hep soyut. Bu ders o frame'leri **elle kuruyor**: `jal` ile atla, `ra` ile dön, `sp` ile yığında yer aç. Faz 7.11'de aynı yığını byte byte inceleyeceğiz; Faz 15'te kendi dilimizin derleyicisi bu çerçeveleri üretecek.

---

## 1. Çağrı kuralı: bir sözleşme

Bir fonksiyon çağrısı iki tarafı birbirine bağlar: **çağıran** (caller) ve **çağrılan** (callee). İkisi farklı zamanda, belki farklı kişilerce yazılmış; aralarında anlaşma olmalı:

- Argümanlar nereye konulur? Dönüş değeri nereden alınır?
- Çağrı sırasında hangi register'lar korunur, hangileri ezilebilir?
- Dönüş adresi nerede tutulur?

Bu anlaşmaya **çağrı kuralı** (calling convention) ya da **ABI** (Application Binary Interface) denir. Ders 7.1'deki ISA bir sözleşmeydi (yazılım–donanım); ABI de bir sözleşme ama **fonksiyonlar arası**. Aynı ABI'ye uyan kod, kim derlerse derlesin birbirini çağırabilir: C'den yazılmış libc, assembly'den yazdığın fonksiyonu çağırabilir (Ders 7.13). RISC-V'nin standart ABI'si register'lara roller verir:

| Register | ABI adı | Rol | Çağrıda korunur mu |
| --- | --- | --- | --- |
| x1 | `ra` | dönüş adresi | hayır (caller-saved) |
| x2 | `sp` | yığın işaretçisi | **evet** (callee-saved) |
| x8–x9, x18–x27 | `s0`–`s11` | korunan | **evet** (callee-saved) |
| x10–x17 | `a0`–`a7` | argüman / dönüş | hayır (caller-saved) |
| x5–x7, x28–x31 | `t0`–`t6` | geçici | hayır (caller-saved) |

İlk sekiz argüman `a0`–`a7`'de, dönüş değeri `a0`'da (büyükse `a0`+`a1`). Daha fazla argüman yığına konur (Ders 7.10).

---

## 2. jal ve jalr: atla ve dön

Ders 7.5'te `jal`'i "atla" olarak gördük. Asıl işi fonksiyon çağırmak:

```
jal  ra, fact      # ra = buradan sonraki komutun adresi; sonra fact'e atla
```

`jal` iki şey yapar: (1) kendisinden **sonraki** komutun adresini `ra`'ya yazar (dönüş adresi), (2) hedefe atlar. Fonksiyon bitince geri dönmek için:

```
jr   ra            # ra'nin gosterdigi adrese atla  (= jalr x0, ra, 0)
```

`jr ra` bir sözde komut; gerçeği `jalr x0, ra, 0` (jump and link register): `ra`'ya atla, dönüş adresini `x0`'a — yani hiçbir yere (Ders 7.3). `jalr`, `jal`'in register'dan atlayan hali; `jal` sabit bir etikete (±1 MB), `jalr` register'daki herhangi bir adrese atlar (fonksiyon pointer'ları, Ders 4.11; uzak çağrılar).

**Yaprak fonksiyon** (leaf: başka fonksiyon çağırmayan) en basit hali:

```
# kare(a0) = a0 * a0
kare:
        mul     a0, a0, a0     # sonuc a0'da
        jr      ra             # don
```

Yığına hiç dokunmadı, çünkü `ra`'yı ezmedi (içeride `jal` yok) ve geçici register'lar yetti. Çağıran:

```
        li      a0, 7
        jal     ra, kare       # a0 = 49
```

---

## 3. Korunan ve korunmayan register'lar

Çağrı kuralının en ince noktası. Bir fonksiyon çağırdığında, çağrılan fonksiyon bazı register'ları değiştirebilir. Hangileri?

- **Caller-saved** (`t0`–`t6`, `a0`–`a7`, `ra`): çağrılan bunları ezebilir. Çağıran, çağrı sonrası bir değere ihtiyaç duyuyorsa **çağrıdan önce** kendisi saklamalı.
- **Callee-saved** (`s0`–`s11`, `sp`): çağrılan bunları kullanacaksa, **önce saklayıp dönerken geri koymalı**. Çağıran, çağrı sonrası bu register'ların değişmediğine güvenebilir.

Bu bölüşme bir denge: her register'ı her çağrıda saklamak israf olurdu. Değeri çağrıdan sonra lazım olmayanları `t`'ye koy (saklama derdi yok), uzun ömürlüleri `s`'ye koy (bir kez başta saklanır). Derleyicinin register tahsisi (Ders 6.30) tam bu kararı veriyor: bir değer bir çağrıyı "aşıyorsa" (çağrıdan önce ve sonra canlıysa) callee-saved bir register tercih edilir.

`ra`'nın caller-saved olması kritik: bir fonksiyon başka bir fonksiyon çağırırsa, `jal` `ra`'yı ezer. Bu yüzden çağırmadan önce `ra`'yı saklaması gerekir — birazdan göreceğimiz özyinelemenin kalbi.

---

## 4. Yığın: sp, prolog, epilog

**Yığın** (stack), fonksiyonların geçici yer açtığı bellek bölgesi (Ders 2.7, Faz 4.21). `sp` (stack pointer) yığının tepesini gösterir. RISC-V'de yığın **aşağı** büyür: yer açmak `sp`'yi azaltmak.

Bir fonksiyonun başında yer açıp saklaması gerekenleri saklamasına **prolog**, sonunda geri yükleyip yeri kapatmasına **epilog** denir:

```
fonksiyon:
        addi    sp, sp, -16    # PROLOG: 16 bayt yer ac (asagi buyu)
        sw      ra, 12(sp)     #   ra'yi sakla
        sw      s0, 8(sp)      #   s0'i sakla (kullanacaksak)
        ...                    # govde
        lw      s0, 8(sp)      # EPILOG: s0'i geri al
        lw      ra, 12(sp)     #   ra'yi geri al
        addi    sp, sp, 16     #   yeri kapat
        jr      ra
```

Prolog ve epilog simetrik: ne açtıysan kapat, ne sakladıysan geri al, `sp`'yi dönerken başladığı yere getir. Bu simetri bozulursa (`sp` yanlış değerle dönerse, ya da `ra` geri yüklenmezse) program çağırana yanlış yere döner — assembly'de en sık yapılan hata, ve Faz 7.14'teki yığın taşması saldırısının da dayandığı mekanizma.

---

## 5. Özyinelemeli faktöriyel

Hepsini bir araya koyalım. `fact(n) = n * fact(n-1)`, Ders 2.8'deki özyinelemeli fonksiyonun assembly hali. Özyineleme neden yığın gerektiriyor? Çünkü `fact`, `fact`'i çağırıyor; iç çağrı `ra`'yı ve `a0`'ı (n) ezer. Her seviye kendi `ra` ve `n`'ini yığında saklamalı.

```
# Ozyinelemeli faktoriyel: fact(n) = n * fact(n-1), fact(1) = 1
        .text
main:
        li      a0, 5          # fact(5)
        jal     ra, fact
        li      a7, 1          # PrintInt (sonuc a0'da)
        ecall
        li      a7, 10
        ecall

# fact(a0) -> a0
fact:
        addi    sp, sp, -8     # PROLOG: cerceve ac (iki word)
        sw      ra, 4(sp)      #   donus adresini sakla
        sw      a0, 0(sp)      #   n'i sakla (ic cagri a0'i ezecek)

        li      t0, 1
        bge     t0, a0, taban  # n <= 1 ise taban durumu

        addi    a0, a0, -1     # a0 = n - 1
        jal     ra, fact       # fact(n-1) -> a0   (ra ve a0 ezildi)
        lw      t1, 0(sp)      # n'i yigindan geri al
        mul     a0, a0, t1     # a0 = fact(n-1) * n
        j       geridon
taban:
        li      a0, 1          # fact(1) = 1
geridon:
        lw      ra, 4(sp)      # EPILOG: donus adresini geri al
        addi    sp, sp, 8      #   cerceveyi kapat
        jr      ra
```

```
120
```

$5! = 120$. İşleyiş: `fact(5)` yığına kendi `ra` ve `n=5`'ini koyar, `fact(4)`'ü çağırır; o da `n=4`'ü koyar, `fact(3)`'ü çağırır... Beş çerçeve üst üste yığılır (Ders 2.8'deki "stack'te iniş"). `fact(1)` taban durumunda 1 döndürür; sonra çerçeveler teker teker kapanır, her biri saklanmış `n`'iyle çarpar (Ders 2.8'deki "çıkış"): $1 \cdot 2 \cdot 3 \cdot 4 \cdot 5$.

Üç kritik nokta:

- **`ra` saklanmazsa**: ilk `jal ra, fact` `ra`'yı `fact`'in içine ayarlar; iç çağrı onu ezer. Saklamazsak `fact(5)` `main`'e değil kendi içine döner — sonsuz döngü ya da çöküş.
- **`n` saklanmazsa**: iç çağrı `a0`'ı ezer (dönüşte sonucu koyar); çarpmak için gereken `n`'i kaybederiz. Bu yüzden çağrıdan önce yığına koyup sonra geri alıyoruz. (Alternatif: `n`'i bir `s` register'ında tutmak — ama o zaman `s`'yi saklamak gerekir, aynı maliyet.)
- **Yığın derinliği**: `fact(5)` beş çerçeve açar. `fact(100000)` yüz bin çerçeve — yığın taşar (stack overflow, Ders 4.21). Ders 2.8'deki "özyinelemenin derinlik sınırı", fiziksel olarak `sp`'nin yığının sonuna çarpması.

Ders 2.8'de özyinelemeyi döngüye çevirmeyi görmüştük; derleyici bunu bazen otomatik yapar (**kuyruk çağrısı optimizasyonu**), ama faktöriyel buna uygun değil (çağrıdan sonra çarpma var). Ders 7.15'te optimizasyon seviyelerinde değineceğiz.

---

## Alıştırmalar

**1** – `kare` yaprak fonksiyonu (Bölüm 2) neden yığına dokunmuyor ama `fact` dokunuyor? Bir fonksiyonun ne zaman prolog/epilog'a ihtiyacı olduğunu bir cümleyle söyle.

**2** – İki argümanlı bir `topla(a, b)` fonksiyonu yaz (`a0 + a1 → a0`). `main`'den `topla(3, 4)` çağır, 7 yazdır. Yaprak mı? Yığın gerekir mi?

**3** – `fact`'te `n`'i yığın yerine `s0` register'ında tutan bir sürüm yaz. Artık `s0`'ı saklaman gerekecek (callee-saved). Komut sayısı azaldı mı arttı mı? İki yaklaşımın maliyetini karşılaştır.

**4** – İki özyinelemeli çağrı yapan Fibonacci'yi (Ders 2.8) assembly'de yaz: `fib(n) = fib(n-1) + fib(n-2)`. İlk çağrının sonucunu ikinci çağrı sırasında nerede saklarsın? (İpucu: `a0` iki çağrı arasında ezilir; yığına ya da bir `s` register'ına.) `fib(10) = 55`'i doğrula.

**5** – `main`, `fact`'i çağırmadan önce `ra`'yı saklamıyor ama `fact` saklıyor. `main` neden `ra`'yı saklamak zorunda değil? (İpucu: `main`'in çağıranı kim, ve `main` nereye "dönüyor"?) Gerçek bir programda `main`'in de bir çağıranı var; ne yapar?

<details>
<summary>Cevaplar</summary>

**1** – `kare` başka fonksiyon çağırmıyor (`jal` yok), bu yüzden `ra` ezilmiyor; ve işini birkaç `t`/`a` register'ında bitiriyor, callee-saved register kullanmıyor. `fact` ise kendini çağırıyor (`ra` ezilir) ve `n`'i çağrı boyunca korumalı. Kural: **başka fonksiyon çağıran** ya da **callee-saved register kullanan** ya da **yerel değişken için yığında yer gereken** bir fonksiyon prolog/epilog'a ihtiyaç duyar; saf yaprak fonksiyonlar çoğu zaman duymaz.

**2** –

```
main:   li      a0, 3
        li      a1, 4
        jal     ra, topla
        li      a7, 1
        ecall
        li      a7, 10
        ecall
topla:  add     a0, a0, a1
        jr      ra
```

7 yazar. Yaprak fonksiyon; `ra` ezilmiyor, callee-saved kullanılmıyor, yerel değişken yok → yığına gerek yok. (RARS varsayılan olarak ilk komuttan başlar, bu yüzden `main`'i dosyanın başına koyduk.)

**3** –

```
fact:   addi    sp, sp, -8
        sw      ra, 4(sp)
        sw      s0, 0(sp)      # callee-saved: once sakla
        mv      s0, a0         # n'i s0'da tut
        li      t0, 1
        bge     t0, s0, taban
        addi    a0, s0, -1
        jal     ra, fact
        mul     a0, a0, s0     # fact(n-1) * n
        j       geridon
taban:  li      a0, 1
geridon:lw      s0, 0(sp)
        lw      ra, 4(sp)
        addi    sp, sp, 8
        jr      ra
```

Komut sayısı neredeyse aynı: yığına `n` yerine `s0` sakladık, ama `s0`'ı da saklamak gerekti (prolog/epilog'da bir `sw`/`lw` daha). İki yaklaşım aynı maliyete çıkıyor çünkü `n` çağrıyı aşan bir değer: nereye koyarsan koy, bir kez saklanmalı. Değeri **birden çok** çağrı boyunca kullanan fonksiyonlarda `s` register'ı kazanır (bir kez saklanır, çok kez okunur).

**4** –

```
fib:    addi    sp, sp, -12
        sw      ra, 8(sp)
        sw      s0, 4(sp)      # n
        sw      s1, 0(sp)      # fib(n-1) sonucu
        li      t0, 2
        blt     a0, t0, taban  # n < 2 ise fib(n) = n
        mv      s0, a0
        addi    a0, s0, -1
        jal     ra, fib        # fib(n-1)
        mv      s1, a0         # sonucu sakla (ikinci cagri a0'i ezecek)
        addi    a0, s0, -2
        jal     ra, fib        # fib(n-2)
        add     a0, a0, s1     # fib(n-1) + fib(n-2)
        j       geridon
taban:  # a0 zaten n (0 ya da 1)
geridon:lw      s1, 0(sp)
        lw      s0, 4(sp)
        lw      ra, 8(sp)
        addi    sp, sp, 12
        jr      ra
```

`fib(10) = 55`. İlk çağrının sonucunu (`fib(n-1)`) `s1`'e sakladık çünkü ikinci `jal` `a0`'ı ezecek; `s1` callee-saved olduğu için ikinci çağrıdan sağ çıkar (o çağrı da `s1`'i kullanırsa saklar). `n`'i `s0`'da tuttuk, iki çağrı arasında lazım. Ders 2.8'deki üstel çağrı ağacı burada yığında canlanıyor.

**5** – `main` de bir fonksiyon ve `ra`'sı var, ama bu oyuncak programda `main` `ra` ile dönmek yerine `ecall` (Exit) ile programı bitiriyor; dönüş adresine ihtiyacı yok. Gerçek bir programda `main`'i C çalışma zamanı (`_start`/`crt0`, Ders 7.18) çağırır ve `main` `ra` ile oraya döner; o zaman `main` de başka fonksiyon çağırıyorsa `ra`'yı saklamak zorundadır. Burada `main` kendini "en üst" sayıp `ra`'yı umursamıyor — ama `main` içinde `jal fact`'ten **sonra** `ra`'ya ihtiyaç duysaydı (örneğin iki kez `fact` çağırıp arada `ra`'yı kullansaydı) onu da saklamak gerekirdi.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design, RISC-V Edition* (2. baskı), Bölüm 2.8: fonksiyon çağırma, yığın, özyineleme.
- "RISC-V Calling Convention" (riscv.org, psABI belgesi): register rolleri, argüman geçişi, yığın hizalaması.
- Ders 2.7 (fonksiyonlar ve kapsam) ve 2.8 (özyineleme): bu dersin C'deki önceli.

**Sıradaki ders:** x86-64 register'ları ve adresleme. `rax`–`r15`, alt register'lar, adresleme modları ve `lea`.
