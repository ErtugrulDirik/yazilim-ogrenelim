---
title: "7.10 System V AMD64 çağrı kuralı"
description: "System V AMD64 ABI: ilk altı tamsayı argümanı rdi, rsi, rdx, rcx, r8, r9'da; dönüş rax'te; altıdan fazla argümanın yığına konması; call ve ret'in dönüş adresini yığına itmesi; 16-byte yığın hizalaması ve call öncesi push ile sağlanması; caller/callee-saved register bölüşümü; red zone (rsp altı 128 byte) ve yaprak fonksiyonların onu kullanması; RISC-V ABI ile karşılaştırma."
gereksinimler: [gcc]
---

Ders 7.6'da RISC-V'nin çağrı kuralını (ABI) kurduk: argümanlar `a0`–`a7`'de, dönüş adresi `ra`'da, yığın `sp` ile. x86-64'ün de bir ABI'si var: **System V AMD64** (Linux, macOS, BSD'nin kullandığı; Windows'un farklı bir ABI'si var). Aynı fikirler, farklı register'lar ve birkaç x86'ya özgü incelik. Bu ABI'yi bilmek, assembly'den C fonksiyonu çağırmak (Ders 7.13), hata ayıklarken yığını okumak (Ders 7.11) ve Faz 15'te kod üretmek için gerekli.

---

## 1. Argümanlar ve dönüş

İlk altı tamsayı/pointer argümanı sırayla şu register'larda:

| Argüman | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- |
| Register | `rdi` | `rsi` | `rdx` | `rcx` | `r8` | `r9` |

Dönüş değeri `rax`'te (128-bit ise `rax`:`rdx`). Kayan nokta argümanları ayrı register'larda (`xmm0`–`xmm7`, Ders 7.29). Bir çağrı:

```c
long caller(long x) { return 1 + callee(x, x + 1, x + 2); }
```

```
caller: pushq  %rax                 # yigini 16'ya hizala (asagida)
        leaq   1(%rdi), %rsi        # arg2 = x + 1   (rdi zaten x = arg1)
        leaq   2(%rdi), %rdx        # arg3 = x + 2
        callq  callee@PLT           # cagir (donus adresini yigina it)
        incq   %rax                 # sonuc (rax) + 1
        popq   %rcx                 # yigini geri al
        retq
```

`x` zaten `rdi`'de (caller'ın 1. argümanı), ve aynı zamanda callee'nin 1. argümanı olacağı için yerinde kalıyor. `x+1` → `rsi` (arg2), `x+2` → `rdx` (arg3), sonra `call`. Dönüşte sonuç `rax`'te, üstüne 1 ekleniyor. RISC-V'deki `a0`–`a2`'nin x86-64 karşılığı `rdi`, `rsi`, `rdx`.

Altıdan fazla argüman **yığına** konur:

```c
long seven_args(long a, long b, long c, long d, long e, long f, long g) { return a + g; }
```

```
seven_args: movq  %rdi, %rax        # a (1. arg, rdi'de)
            addq  8(%rsp), %rax     # g (7. arg, yiginda)
            retq
```

İlk altısı register'da, yedincisi (`g`) yığında, `8(%rsp)`'de. Neden 8? Çünkü `call` dönüş adresini yığına itti (8 byte); argüman onun hemen üstünde. Register'lar hızlı olduğu için ilk altı argüman onlarda; fazlası, nadiren olduğu için, yavaş yığında.

---

## 2. call ve ret

RISC-V'de `jal` dönüş adresini bir **register'a** (`ra`) yazıyordu (Ders 7.6). x86-64'te `call` onu **yığına iter**:

- **`call hedef`**: `rsp -= 8`, dönüş adresini `(rsp)`'ye yaz, `hedef`'e atla.
- **`ret`**: `(rsp)`'deki adrese atla, `rsp += 8`.

Fark felsefi: RISC (RISC-V) dönüş adresini register'da tutar (hızlı, ama yaprak olmayan fonksiyon yine de yığına saklamak zorunda); CISC (x86-64) doğrudan yığına koyar (bir register harcamaz, ama her çağrı bir bellek yazması). İkisi de aynı işi yapar; Ders 7.1'deki tasarım felsefesi farkının bir yüzü daha.

Dönüş adresinin yığında, yerel değişkenlerin hemen yanında durması, Ders 7.14'teki tampon taşması saldırısının neden mümkün olduğunun çekirdeği: bir diziyi taşıran veri, dönüş adresinin üstüne yazabilir.

---

## 3. 16-byte hizalama

System V ABI bir kural koyar: bir `call` komutu çalıştığı anda `rsp` **16'nın katı** olmalı (bazı komutların, özellikle SSE'nin, Ders 7.29, hizalı bellek istemesi için). `call` dönüş adresini itince `rsp` 16'nın katından 8 çıkar; bu yüzden bir fonksiyon içinde `call` yapmadan önce yığının toplamda 16'ya hizalanması gerekir.

Bölüm 1'deki `caller`'da `pushq %rax` tam bunu yapıyor: `rax`'i saklamak için değil, `rsp`'yi 8 azaltıp (bir `push` = `sub $8` + yazma) `call` anında 16 hizasını tutturmak için. Fonksiyon girişinde (caller'a `call` ile girildiği için) `rsp` 16-hizasından 8 eksikti; bir `push` daha 16'ya tamamladı. Dönüşte `popq %rcx` (rcx önemsiz, sadece `rsp`'yi geri almak için) dengeliyor.

Yerel değişkeni çok olan fonksiyonlar `subq $N, %rsp` ile yer açar, `N`'i 16 hizasını koruyacak şekilde seçer. Bu hizayı bozmak (yanlış `N`) programı çoğu zaman çalıştırır ama SSE komutlarında ya da bazı kütüphane çağrılarında çökertir — bulması zor bir hata.

---

## 4. Korunan register'lar

RISC-V'deki gibi (Ders 7.6) bölüşüm var:

- **Callee-saved** (çağrılan korur): `rbx`, `rbp`, `r12`–`r15`, ve `rsp`. Çağrılan bunları kullanacaksa prolog'da saklar, epilog'da geri koyar.
- **Caller-saved** (çağrılan ezebilir): `rax`, `rcx`, `rdx`, `rsi`, `rdi`, `r8`–`r11`. Çağıran, çağrı sonrası lazımsa önce saklar.

RISC-V'nin `s0`–`s11`'i (callee-saved) ile `t0`–`t6`'sının (caller-saved) karşılığı. Mantık aynı (Ders 7.6): bir çağrıyı "aşan" değerler callee-saved register'a, geçiciler caller-saved'e. Derleyicinin register tahsisi (Ders 6.30) bu kararı veriyor.

---

## 5. Red zone

x86-64'e özgü bir kolaylık: `rsp`'nin **altındaki 128 byte** "red zone" (kırmızı bölge), ve bir fonksiyon bu bölgeyi `rsp`'yi hiç değiştirmeden geçici alan olarak kullanabilir — **yaprak fonksiyonsa** (başka fonksiyon çağırmıyorsa).

```c
int leaf(int x) {
    int tmp[4];
    tmp[0]=x; tmp[1]=x*2; tmp[2]=x*3; tmp[3]=x*4;
    return tmp[0] + tmp[3];
}
```

```
leaf:   movl  %edi, -24(%rsp)       # tmp[0] = x
        ...
        movl  %edi, -12(%rsp)       # tmp[3] = x*4
        movl  -12(%rsp), %eax
        addl  -24(%rsp), %eax       # tmp[0] + tmp[3]
        retq
```

`rsp`'ye hiç dokunmadı — `subq`/`addq` ile yığın çerçevesi açmadı. `tmp` dizisi doğrudan `-24(%rsp)`'de, yani red zone'da. Neden güvenli? Bir sinyal işleyici (interrupt handler, Ders 7.28) ya da başka bir şey `rsp`'nin altına yazmayacağına söz veriyor; yaprak fonksiyon `call` yapmadığı için (ki `call` `rsp`'nin altına yazar) bu bölge dokunulmadan kalıyor. Prolog/epilog'u (ve iki komutu) atlamak küçük ama gerçek bir hızlanma.

Yaprak **olmayan** bir fonksiyon red zone'u kullanamaz: yaptığı `call` dönüş adresini `rsp`'nin oraya yazar ve red zone'daki veriyi ezer. O zaman normal `subq %rsp` ile çerçeve açar. RISC-V'de red zone yok; orada yaprak fonksiyonlar da yığına yazacaksa `sp`'yi ayarlar (Ders 7.6).

---

## 6. İki ABI yan yana

| | RISC-V | System V AMD64 |
| --- | --- | --- |
| Argüman 1–... | `a0`–`a7` (8 register) | `rdi, rsi, rdx, rcx, r8, r9` (6), sonrası yığın |
| Dönüş | `a0` (, `a1`) | `rax` (, `rdx`) |
| Dönüş adresi | `ra` register | yığında (`call` iter) |
| Callee-saved | `s0`–`s11`, `sp` | `rbx, rbp, r12`–`r15`, `rsp` |
| Yığın hizası | 16 byte | 16 byte |
| Red zone | yok | 128 byte (yaprak) |

Aynı problemin iki çözümü. Bir ABI "doğru" değil, bir **anlaşma**; aynı ISA için bile farklı ABI'ler olabilir (Windows x64 ABI, System V'den farklı: argümanlar `rcx, rdx, r8, r9`). Bu yüzden Linux'ta derlenmiş bir `.o` dosyası Windows'ta linklenemiyor: aynı x86-64 makine kodu, farklı çağrı sözleşmesi. ABI, ISA'nın üstüne kurulan ikinci bir sözleşme katmanı (Ders 7.1).

---

## Alıştırmalar

**1** – `long f(long a, long b) { return a - b; }` çağrısında `g(f(10, 3))` için argümanlar hangi register'lara konur? `f`'nin sonucu nereden alınıp `g`'ye nasıl geçer?

**2** – Bölüm 1'deki `caller`, `pushq %rax` yerine `subq $8, %rsp` de yazabilirdi; ikisi de `rsp`'yi 8 azaltır. Derleyici neden `push` seçmiş olabilir? (İpucu: komut uzunluğu, Ders 7.1.)

**3** – Bir fonksiyon dört `long` yerel değişken kullanıyor ve bir `call` yapıyor. Prolog'da `rsp`'den kaç byte çıkarmalı ki hem dört değişkene yer olsun hem de `call` anında 16-hizası korunsun? (Giriş anında `rsp` 16-hizasından 8 eksik olduğunu unutma.)

**4** – `seven_args`'ın sekizinci argümanı olsaydı (`h`), `8(%rsp)` yerine hangi ofsette olurdu? Dokuzuncu? Yığında argümanlar hangi sırayla dizili?

**5** – Red zone'u yaprak olmayan bir fonksiyon neden kullanamaz? Bir yaprak fonksiyon red zone'da `tmp[40]` (160 byte) kullanmak isterse ne olur? (Red zone 128 byte; aşınca ne gerekir?)

<details>
<summary>Cevaplar</summary>

**1** – `f(10, 3)`: `rdi = 10`, `rsi = 3`, `call f`. `f` sonucu `rax`'e koyar (`10 - 3 = 7`). `g(...)` için bu sonuç `g`'nin 1. argümanı olmalı: `movq %rax, %rdi`, sonra `call g`. `rax`'ten `rdi`'ye bir taşıma; dönüş register'ından argüman register'ına. (Derleyici bazen `f`'yi çağırmadan önce düzenleyip doğrudan optimize edebilir, ama kavram bu.)

**2** – `pushq %rax` **tek baytlık** bir komut (`0x50`); `subq $8, %rsp` dört byte. İkisi de `rsp`'yi 8 azaltır, ama `push` daha kısa. Kod boyutu küçük olunca cache'e daha çok sığar (Ders 7.24); derleyiciler 8-byte hizalama ayarı için sık sık `push`/`pop` (önemsiz bir register'la) kullanır. İçeri yazılan değer (`rax`) umursanmıyor; sadece `rsp`'yi kaydırmak için.

**3** – Dört `long` = 32 byte. Giriş anında `rsp` 16k+8 (call yüzünden). 16-hizası için toplam çıkarmanın `rsp`'yi 16'nın katına getirmesi gerekir: 8 (hizayı tamamla) + 32 (değişkenler) = 40, ama 40 16'nın katı değil; 16-hizasını korumak için çıkarma 16k+8 olmalı → 40 uygun (16·2 + 8 = 40, `rsp` 16k+8 − 40 = 16(k−3), 16'nın katı). Yani `subq $40, %rsp`. (Pratikte derleyici 32 veri + 8 hizalama = 40 ya da bir sonraki 16 katı olacak şekilde seçer.)

**4** – `call` dönüş adresi `0(%rsp)`'de (8 byte). 7. argüman `8(%rsp)`, 8. `16(%rsp)`, 9. `24(%rsp)`. Argümanlar yığında **soldan sağa** artan adreste: 7. en düşük, sonrakiler yukarı. Çağıran bunları `call`'dan önce (ters sırada push ederek ya da doğrudan yazarak) yerleştirir.

**5** – Yaprak olmayan fonksiyon `call` yapar; `call` dönüş adresini `rsp`'nin hemen altına (red zone'un içine) yazar ve oradaki veriyi ezer. Bu yüzden red zone sadece `call` yapmayan (yaprak) fonksiyonlar için güvenli. `tmp[40]` = 160 byte > 128 byte red zone: aşıyor; o zaman fonksiyon normal çerçeve açmak zorunda (`subq $N, %rsp`), red zone'a güvenemez. Red zone sadece **küçük** yerel veriler için bir kısayol; büyük diziler yine yığın çerçevesi gerektirir.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.7: prosedürler, yığın çerçeveleri, argüman geçişi.
- Michael Matz vd., *System V Application Binary Interface, AMD64 Architecture Processor Supplement* (ücretsiz): ABI'nin resmi tanımı; register rolleri, hizalama, red zone.
- Ders 7.6 (RISC-V fonksiyonlar): aynı kavramların RISC-V hali; iki ABI'yi karşılaştırmak için.

**Sıradaki ders:** Yığın çerçevesi. Yerel değişkenler, `rbp` kullanımı ve atlanması, LLDB ile yığını byte byte inceleme.

