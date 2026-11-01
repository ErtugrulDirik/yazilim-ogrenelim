---
title: "7.12 Diziler, struct'lar ve pointer'lar assembly'de"
description: "Faz 4'teki bellek kavramlarının assembly karşılığı: pointer dereferansı tek bir load; dizi indekslemenin base + i × eleman_boyutu olması ve x86-64'ün ölçekli adreslemesiyle RISC-V'nin ayrı çarpmasının farkı; struct üyesine sabit ofsetle erişim; hizalama ve dolgunun (Faz 4.26) ofsetlerde ve sizeof'ta görünmesi; iki boyutlu dizilerin satır öncelikli indekslenmesi; ofsetlerin ABI ile belirlenmesi."
gereksinimler: [gcc]
---

Faz 4'te belleği, pointer'ları, dizileri ve struct'ları soyut olarak kurduk: bir pointer bir adres (Ders 4.4), `a[i]` aslında `*(a + i)` (Ders 4.6), bir struct üyesi sabit bir ofsette (Ders 4.25), hizalama dolgu ekler (Ders 4.26). Bu ders o soyutlamaların **altını** gösteriyor: her biri birkaç makine komutu, ve ofsetler tam Faz 4'te hesapladığımız sayılar. Bu, C'nin bellek modeliyle makinenin bellek erişimi arasındaki son köprü; Faz 15'te kod üretirken bu ofsetleri biz hesaplayacağız.

---

## 1. Pointer dereferansı tek load

Ders 4.5'te `*p` "p'nin gösterdiği yerdeki değer" demekti. Assembly'de tek bir bellek okuması:

```c
int get(int *p) { return *p; }
```

```
get:  movl  (%rdi), %eax      # eax = *p  (p = rdi)
      retq
```

`(%rdi)`, Ders 7.7'deki en basit adresleme: register'ın gösterdiği adresteki değer. RISC-V'de `lw a0, 0(a0)` (Ders 7.4). Pointer, Faz 4'te söylediğimiz gibi, sadece bir adres tutan register; `*` onu okuyan komut.

---

## 2. Dizi indeksleme

Ders 4.6'da `a[i]` = `*(a + i)`, ve `a + i`'nin eleman boyutuna göre ölçeklendiğini (pointer aritmetiği) görmüştük. Assembly'de:

```c
int arr_elem(int *a, long i) { return a[i]; }
```

**x86-64:**
```
arr_elem:  movl  (%rdi,%rsi,4), %eax    # eax = *(a + i*4)
           retq
```

**RISC-V:**
```
arr_elem:  slli  a1, a1, 2              # a1 = i * 4  (sola 2 kaydir, Ders 5.1)
           add   a0, a0, a1             # a0 = a + i*4
           lw    a0, 0(a0)              # a0 = *(a + i*4)
           ret
```

İkisi de `a + i*4` adresini hesaplayıp okuyor (`int` = 4 byte, bu yüzden ölçek 4). Fark Ders 7.1'in ta kendisi: x86-64 ölçekli adreslemeyle (`(%rdi,%rsi,4)`) hepsini tek `movl`'de yapıyor; RISC-V önce çarpıp (kaydırma) sonra topluyor, üç komut. Faz 4.6'daki "`a + i` eleman boyutuyla ölçeklenir" kuralı, burada ölçek çarpanı (4) ya da kaydırma miktarı (2) olarak somut.

Eleman boyutu değişince ölçek değişir: `long a[]` (8 byte) → ölçek 8 (`(%rdi,%rsi,8)`, Ders 7.1'deki `sum`), `char a[]` (1 byte) → ölçek 1.

---

## 3. Struct üyesine ofsetle erişim

Ders 4.25'te struct üyelerinin bellekte ardışık, her birinin sabit bir ofsette olduğunu gördük. Assembly'de üye erişimi, o ofsetle bir load:

```c
struct Nokta { int32_t x; int32_t y; };
int get_x(struct Nokta *p) { return p->x; }
int get_y(struct Nokta *p) { return p->y; }
```

```
get_x:  movl  (%rdi), %eax       # x: ofset 0
        retq
get_y:  movl  4(%rdi), %eax      # y: ofset 4
        retq
```

`x` ofset 0 (struct'ın başı), `y` ofset 4 (`x`'in 4 byte'ı sonra). `p->y`, "`p` + 4 adresindeki değer" — Ders 7.7'deki disp alanı. Üye adları derleme zamanında ofsetlere çevriliyor; makine kodunda `x`, `y` diye bir şey yok, sadece `0` ve `4`.

---

## 4. Hizalama ve dolgu ofsetlerde

Ders 4.26'daki hizalama kuralları (padding) tam burada ortaya çıkıyor. Dengesiz bir struct:

```c
struct Kayit { char c; int32_t n; char *ad; };
int kayit_n(struct Kayit *k) { return k->n; }
```

```
kayit_n:  movl  4(%rdi), %eax     # n: ofset 4, ofset 1 DEGIL!
          retq
```

`n`, `c`'den (ofset 0) hemen sonra ofset **1**'de değil, ofset **4**'te. Neden? `int32_t` 4-byte hizalı olmalı (Ders 4.26); derleyici `c`'den sonra **3 byte dolgu** koyuyor ki `n` 4'ün katı bir ofsette başlasın. `char *ad` (8 byte, 8 hizalı) ofset 8'de. Çalışma zamanında `offsetof` ile doğrulayalım:

```
c:0 n:4 ad:8 boyut:16
```

`sizeof(struct Kayit)` = 16: c(1) + dolgu(3) + n(4) + ad(8). Faz 4.26'da elle hesapladığımız dolgu, assembly'deki `4(%rdi)` ofsetinde ve `sizeof`'ta somut. Üyeleri boyuta göre sıralasaydık (`ad`, `n`, `c`) dolgu azalırdı (Ders 4.26'daki alıştırma) — ve o zaman `kayit_n` farklı bir ofset kullanırdı.

Önemli nokta: bu ofsetler **ABI** tarafından belirlenir (Ders 7.10), ISA tarafından değil. RISC-V'de de `n` ofset 4'te (`lw a0, 4(a0)`), çünkü aynı hizalama kuralları. Bu yüzden aynı struct, aynı ABI ailesinde farklı derleyicilerle aynı yerleşime sahip — yoksa bir derleyicinin yazdığı struct'ı diğeri okuyamazdı.

---

## 5. İki boyutlu diziler

Ders 4.3'te `int m[R][C]`'nin satır öncelikli (row-major) yerleştiğini, `m[r][c]`'nin `m + r*C + c` ofsetinde olduğunu görmüştük. Assembly'de iki ölçekleme:

```c
int get2d(int (*m)[8], long r, long c) { return m[r][c]; }   // C = 8
```

`m[r][c]` = `*(m + r*8 + c)` (eleman `int`, satır 8 eleman). Adres `m + (r*8 + c)*4` byte. x86-64 bunu `r*8`'i bir kaydırma + ölçekli adreslemeyle, RISC-V birkaç komutla kurar (Ders 7.7'nin 4. alıştırmasındaki gibi). `r*8` kısmı `C` sabit olduğu için derleme zamanında bir kaydırmaya (×8 = `<<3`) çevriliyor; `C` değişken olsaydı bir çarpma gerekirdi.

Bu, Ders 4.3'teki "satır öncelikli yerleşim" ve Ders 6.25'teki matris döngü sırasının neden cache'i etkilediğinin (Ders 7.24) altyapısı: `m[r][c]` ile `m[r][c+1]` bellekte yan yana (4 byte arayla), `m[r][c]` ile `m[r+1][c]` ise `C*4` byte uzakta.

---

## Alıştırmalar

**1** – `char buf[]`, `short s[]`, `double d[]` dizilerinde `x[i]`'nin x86-64 ölçekli adreslemesi ne olur? (Her birinin eleman boyutunu düşün.) Ölçek çarpanı sadece 1, 2, 4, 8 olabiliyor; 16 byte'lık bir eleman (`struct { double a, b; }`) için ne yapılır?

**2** – `struct S { int32_t a; char b; int32_t c; };`'nin her üyesinin ofsetini ve `sizeof`'unu elle hesapla (Ders 4.26), sonra `offsetof`/`sizeof` ile doğrula. `b`'den sonra dolgu var mı? Sonda dolgu var mı?

**3** – `arr_elem`'i `const int *a` yerine `int *a` yaparsan assembly değişir mi? Ya okuma yerine yazma (`a[i] = 5`) olsaydı hangi komut? (İpucu: `mov` yönü, Ders 7.7.)

**4** – Üyeleri yeniden sıralayarak `struct Kayit`'in `sizeof`'unu 16'dan küçültebilir misin? Sırala, yeni ofsetleri `offsetof` ile doğrula, ve `kayit_n`'in assembly ofsetinin değiştiğini göster.

**5** – Bir `struct Nokta` (8 byte) **değer olarak** döndüren bir fonksiyon (`struct Nokta yap(int x, int y)`) assembly'de sonucu nerede döndürür? 8 byte `rax`'e sığar; ya struct 16 byte'tan büyük olsaydı (Ders 7.10)? Derleyip bak.

<details>
<summary>Cevaplar</summary>

**1** – `char` (1 byte): ölçek 1, `(%rdi,%rsi,1)` ya da sadece `(%rdi,%rsi)`. `short` (2): ölçek 2. `double` (8): ölçek 8. 16 byte'lık eleman: ölçek 16 yok (en fazla 8); derleyici indeksi önce 16 ile çarpar (bir kaydırma `<<4` ya da `lea`) sonra ölçeksiz adresler, ya da `lea`'yı iki kez kullanır. Ölçek alanının sınırı (1/2/4/8) C'nin temel tip boyutlarına göre seçilmiş; daha büyük elemanlar ayrı çarpma gerektirir.

**2** – `a` ofset 0 (int32, 4 byte). `b` ofset 4 (char, 1 byte). `c` int32, 4 hizalı olmalı → `b`'den sonra 3 byte dolgu, `c` ofset 8. `sizeof` = 12 (en büyük üye 4 hizalı, 8+4 = 12, zaten 4'ün katı, sonda ek dolgu yok). `offsetof`: a:0, b:4, c:8, boyut:12. `b`'den sonra 3 dolgu var; sonda yok.

**3** – `const int *a` ile `int *a` aynı assembly'yi üretir: `const` sadece derleme zamanı bir kısıt (Ders 4.8), makine kodunda okuma ikisinde de `movl (%rdi,%rsi,4), %eax`. Yazma `a[i] = 5` olsaydı yön ters: `movl $5, (%rdi,%rsi,4)` (kaynak $5, hedef bellek; Ders 7.7'de hedef sağda ama bellek hedefi burada). RISC-V'de `sw` (Ders 7.4).

**4** – `struct Kayit { char *ad; int32_t n; char c; };` (büyükten küçüğe): `ad` ofset 0 (8), `n` ofset 8 (4), `c` ofset 12 (1), sonra 3 byte sonda dolgu (struct 8 hizalı olmalı çünkü `ad` 8-byte) → `sizeof` = 16. Hmm, yine 16! En büyük üye `char*` 8-byte olduğu için struct 8'in katı olmalı; 8+4+1 = 13 → 16'ya yuvarlanır. Bu struct küçültülemez (pointer hizalaması baskın). `n`'in ofseti 8'e taştı; `kayit_n` artık `movl 8(%rdi)`. (Ders 4.26'nın dersi: her struct küçültülemez; hizalama taban kısıtı.)

**5** – 8 byte'lık `struct Nokta` `rax`'te döner (iki `int32` paketlenmiş, ya da `rax`:`rdx`). 16 byte'a kadar `rax`:`rdx` çiftinde. 16 byte'tan büyükse ABI farklı davranır: çağıran sonuç için yığında yer ayırır, adresini **gizli bir ilk argüman** olarak (`rdi`) geçirir, fonksiyon oraya yazar; dönüş değeri yerine "çağıranın verdiği buffer'a yaz" (Ders 7.10'daki argüman geçişinin bir uzantısı). Bu yüzden büyük struct'ları değer olarak döndürmek gizli bir kopya/pointer maliyeti taşır; Faz 4'te "büyük struct'ları pointer'la geçir" tavsiyesinin assembly sebebi.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.8 (diziler) ve 3.9 (struct'lar, hizalama).
- Ders 4.1–4.6 (diziler, pointer'lar), 4.25 (struct), 4.26 (hizalama ve dolgu): bu dersin C'deki önceli.
- Ders 7.7 (adresleme modları): ölçekli indekslemenin ayrıntısı.

**Sıradaki ders:** Elle assembly yazıp C'den çağırma. NASM/GAS ile fonksiyon yazmak, C'ye bağlamak, inline assembly.
