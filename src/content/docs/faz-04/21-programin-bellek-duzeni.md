---
title: "4.21 Programın bellek düzeni"
description: "Bir programın belleği beş bölge: text (kod), rodata, data (sıfırdan farklı başlatılan globaller), bss (sıfır başlatılanlar), heap (malloc) ve stack. size komutuyla bölümlerin boyutu, Linux'ta /proc/self/maps ile çalışan bir sürecin gerçek bellek haritası ve her bölgenin okuma/yazma/çalıştırma izinleri, heap'in yukarı stack'in aşağı büyümesi ve ASLR."
gereksinimler: [linux]
gereksinimNotu: "Bu dersin /proc/self/maps bölümü Linux'a özeldir; size komutu ve adres ölçümleri her yerde çalışır."
windowsNotu: "WSL içinde çalıştır; Windows'ta /proc dosya sistemi yoktur."
---

Ders 4.4'te adreslere bakarak bir bellek haritası çizmiştik: kod en altta, üstünde sabitler, sonra globaller, en üstte stack. Ders 4.12'de string sabitlerinin salt okunur bölgede, Ders 4.8'de `const` globallerin yazılamaz bir sayfada durduğunu gördük. Ders 4.22'de `malloc`'u öğrenmeden önce, bütün bu bölgeleri bir araya getiriyoruz: bir programın belleği **kaç bölgeye** ayrılmış, hangisi ne tutuyor, ve bunu nasıl **gözleyebiliriz**.

Bu derste iki araç var: her yerde çalışan `size` komutu, ve Linux'un çalışan bir programın belleğini bize açan `/proc/self/maps` dosyası.

---

## 1. Beş bölge

Bir C programının belleği, çalışırken şu bölgelere ayrılıyor:

| Bölge | Ne tutuyor | İzinler | Ne zaman belirleniyor |
| --- | --- | --- | --- |
| **text** | makine komutları (fonksiyonlar) | oku + **çalıştır** | derlemede |
| **rodata** | değişmez veri: string sabitleri, `const` globaller | **sadece oku** | derlemede |
| **data** | sıfırdan **farklı** başlatılan globaller ve `static`'ler | oku + yaz | derlemede |
| **bss** | **sıfır** başlatılan (ya da başlatılmayan) globaller | oku + yaz | derlemede (yer), çalışmada (sıfırlama) |
| **heap** | `malloc` ile çalışırken ayrılan bellek (Ders 4.22) | oku + yaz | **çalışmada** |
| **stack** | yerel değişkenler, fonksiyon çağrıları (Ders 4.7) | oku + yaz | **çalışmada** |

İlk dördü programın **dosyasında** tanımlı (derleyici belirliyor), son ikisi program çalışırken büyüyüp küçülüyor. Hepsini tek bir programla yazdıralım:

```c
#include <stdio.h>
#include <stdlib.h>

int global_init = 42;              // data
int global_zero;                   // bss
int global_big[100000];            // bss
const char *message = "merhaba";   // pointer data'da, yazi rodata'da
const int read_only = 7;           // rodata

void func(void) { }

int main(void) {
    int local = 1;                 // stack
    static int once = 5;           // data
    int *heap = malloc(sizeof(int));  // heap (pointer'in kendisi stack'te)

    printf("%-20s %p\n", "func (text)",        (void *)func);
    printf("%-20s %p\n", "read_only (rodata)", (void *)&read_only);
    printf("%-20s %p\n", "message yazi",       (void *)message);
    printf("%-20s %p\n", "global_init (data)", (void *)&global_init);
    printf("%-20s %p\n", "once (data)",        (void *)&once);
    printf("%-20s %p\n", "global_zero (bss)",  (void *)&global_zero);
    printf("%-20s %p\n", "global_big (bss)",   (void *)global_big);
    printf("%-20s %p\n", "heap",               (void *)heap);
    printf("%-20s %p\n", "local (stack)",      (void *)&local);
    printf("%-20s %p\n", "heap_ptr (stack)",   (void *)&heap);
    free(heap);
    return 0;
}
```

Linux'ta (bu derste komutları WSL / sanal makinedeki Linux'ta çalıştırıyoruz):

```
func (text)          0xaaaac9c40818
read_only (rodata)   0xaaaac9c40a48
message yazi         0xaaaac9c40998
global_init (data)   0xaaaac9c60048
once (data)          0xaaaac9c60058
global_zero (bss)    0xaaaac9c60060
global_big (bss)     0xaaaac9c60064
heap                 0xaaaacee5b2a0
local (stack)        0xffffec0111f8
heap_ptr (stack)     0xffffec0111f0
```

Ders 4.4'teki haritanın aynısı, bu sefer her bölgeden örnekle:

- **text, rodata** (`...c40...`): en düşük adresler, yan yana. Kod ve değişmez veri birlikte.
- **data, bss** (`...c60...`): hemen üstünde. `global_init` (data) ile `global_zero`/`global_big` (bss) ardışık; derleyici ikisini komşu koyuyor.
- **heap** (`...e5b...`): data'nın epey üstünde; `malloc`'un verdiği yer.
- **stack** (`0xffff...`): en üstte, bambaşka bir aralıkta. `local` ve `heap_ptr` (pointer'ın **kendisi**) burada; `heap`'in **gösterdiği** yer ise heap'te.

`message` ilginç: pointer'ın kendisi data'da (`...c60...` civarı değil ama — aslında `message` bir global pointer, data'da), gösterdiği `"merhaba"` yazısı rodata'da (`...c40998`). Ders 4.10'daki `list` örneğinin aynısı.

---

## 2. size: bölümlerin boyutu

`size` komutu, bir programın dosyasındaki bölümlerin boyutunu gösteriyor (derlemede belirlenen ilk dört bölge):

```
$ size layout
   text	   data	    bss	    dec	    hex	filename
   2335	    660	 400012	 403007	  6263f	layout
```

- **text** 2335 byte: kod + rodata.
- **data** 660 byte: sıfırdan farklı başlatılan globaller (`global_init`, `once`, `message` pointer'ı ve kütüphanenin kendi verileri).
- **bss** 400012 byte: `global_big` tek başına 100000 × 4 = 400000 byte, artı `global_zero` ve birkaç byte.

Buradan önemli bir fikir çıkıyor: **bss, programın dosyasında yer kaplamıyor.** `global_big` 400 KB, ama program dosyası 400 KB büyük değil; dosyada sadece "bu kadar sıfır byte'a ihtiyacım var" yazıyor, ve işletim sistemi program başlarken o bölgeyi sıfırla dolduruyor. Ders 4.4'te "globaller 0 başlar" derken aslında bu oluyordu. Bir milyon elemanlı bir global array'i sıfır tanımlamak programın dosyasını büyütmüyor; ama `= {1, 2, ...}` ile başlatsaydın data'ya geçer ve her değer dosyaya yazılırdı.

`size`, macOS'ta da var ama bölümleri farklı adlandırıyor (`__TEXT`, `__DATA`); `size -m` ayrıntısını veriyor. Temiz `text/data/bss` üçlüsü için Linux'un `size`'ı daha anlaşılır.

---

## 3. /proc/self/maps: çalışan sürecin haritası

`size` dosyaya bakıyor. Peki program **çalışırken** belleği gerçekte neye benziyor? Linux'ta her çalışan sürecin belleği, `/proc/<pid>/maps` adlı sanal bir dosyada görünür; bir programın kendi haritası `/proc/self/maps`'te. Program bunu sıradan bir dosya gibi okuyabilir (Ders 4.12'deki `fgets` ile):

```c
FILE *f = fopen("/proc/self/maps", "r");
char line[256];
while (fgets(line, sizeof line, f) != NULL) {
    fputs(line, stdout);
}
fclose(f);
```

Yukarıdaki programa eklediğimizde (çıktının program kısmı):

```
aaaab05c0000-aaaab05c1000 r-xp ... /tmp/maps      <- text + rodata
aaaab05df000-aaaab05e0000 r--p ... /tmp/maps      <- salt okunur
aaaab05e0000-aaaab05e1000 rw-p ... /tmp/maps      <- data + bss
aaaada34f000-aaaada370000 rw-p ... [heap]
ffff9a6e0000-...          r-xp ... libc.so.6       <- C kütüphanesi
...
ffffd9401000-ffffd9422000 rw-p ... [stack]
```

Her satır bir bellek bölgesi: adres aralığı, **izinler**, ve (varsa) hangi dosyadan geldiği. İzin sütunu (`r-xp` gibi) Ders 4.4 ve 4.8'deki iddiaları **doğruluyor**:

- **`r-xp`** (read + execute): text bölgesi. Okunabilir ve **çalıştırılabilir**, ama yazılamaz (`w` yok). Bir fonksiyonun adresi (`&func`) bu aralıkta. Kodu değiştirmeye çalışmak bu yüzden çöker.
- **`r--p`** (sadece read): rodata. `&read_only` ve `"merhaba"` burada. Ders 4.8'de `const` globali, Ders 4.12'de string sabitini değiştirince neden bus error aldığımız tam burada görünüyor: `w` izni yok.
- **`rw-p`** (read + write, execute yok): data ve bss. Globallere yazabiliyoruz ama bu bölge **çalıştırılamaz** — buraya veri olarak yazılmış bir şeyi kod gibi çalıştırmak engelleniyor (güvenlik için, Ders 4.14'teki stack smashing'e karşı bir savunma).
- **`[heap]`** ve **`[stack]`**: ikisi de `rw-p`. `malloc`'un verdiği adres `[heap]` aralığında, `local` ise `[stack]` aralığında.
- **`libc.so.6`**: C kütüphanesinin kendisi. `printf`, `malloc`, `strlen` gibi fonksiyonların kodu programımızın içinde değil; işletim sistemi onları ayrı bir dosyadan belleğe **paylaşımlı** yüklüyor (bu yüzden adresleri `0xffff...` aralığında, programımızdan uzakta). Ders 4.13'te standart `strlen`'in kodu işte bu bölgede.

Hiçbir bölgenin aynı anda hem `w` hem `x` taşımadığına dikkat: ya yazılabilir ya çalıştırılabilir, ikisi birden değil (W^X kuralı). Bu, veriyi koda çeviren saldırılara karşı modern bir savunma.

---

## 4. Heap yukarı, stack aşağı

Ders 4.4'te stack'in **aşağı** (azalan adreslere) büyüdüğünü görmüştük. Haritadaki iki büyüyen bölge zıt yönlerde:

- **heap**, data'nın üstünden başlayıp **yukarı** (artan adreslere) büyüyor. Ardışık küçük `malloc`'lar artan adresler verir.
- **stack**, en üstten başlayıp **aşağı** büyüyor. Her fonksiyon çağrısı (Ders 4.7) stack'i biraz aşağı itiyor.

İkisi birbirine doğru büyüyor ve aralarında dev bir boşluk var (Ders 4.4'teki ~1,7 GB'lık boşluk). Bu boşluk, ikisinin de büyüyebilmesi için; biri diğerinin alanına girerse program çöker (stack overflow ya da bellek tükenmesi).

Bir ayrıntı: çok büyük bir `malloc` (örneğin 1 MB) `[heap]`'ten değil, işletim sisteminden ayrı bir bölge (`mmap`) olarak gelebilir ve stack'e yakın yüksek adreslerde çıkar. Küçük ayırmalar heap'ten, büyükler ayrı bölgelerden; `malloc`'un bu kararını Ders 4.22'de göreceğiz.

### ASLR geri döndü

Ders 4.4'te adreslerin her çalıştırmada değiştiğini (ASLR) görmüştük. `/proc/self/maps`'i iki kez çalıştırırsak:

```
run 1:  read_only = 0xaaaad8610a78   stack = 0xffffe6f0c4d8
run 2:  read_only = 0xaaaab9100a78   stack = 0xfffffec0fd38
```

Bütün aralıklar kaydı, ama **düşük haneler** (`a78`) sabit: işletim sistemi bölgelerin **başlangıcını** rastgeleleştiriyor, içindeki yerleşimi değil (Ders 4.4). Bir saldırganın bir adresi önceden tahmin etmesini zorlaştıran bu, text, data, heap ve stack'in her birini bağımsız kaydırıyor. Bunu `/proc/self/maps` üzerinden doğrudan görebiliyoruz.

---

## Alıştırmalar

**1** – `global_big`'i `int global_big[100000] = {1};` diye (ilk elemanı 1) başlatırsan `size` çıktısında hangi bölüm büyür, bss mi data mı? Neden? Program dosyasının boyutuna ne olur?

**2** – Şu değişkenlerin her birini bir bölgeye yerleştir: `static const double e = 2.718;`, bir fonksiyonun içindeki `char buf[100];`, bir fonksiyonun içindeki `static int counter;`, `char *global_name = "Ece";`'deki hem `global_name` hem `"Ece"`.

**3** – Programına `const int sabit = 7;` ekleyip `int *p = (int *)&sabit; *p = 8;` yaz. `/proc/self/maps`'te `&sabit`'in hangi izinli bölgede olduğunu bul, sonra programı çalıştır. Ders 4.8'deki bus error ile `/proc/self/maps`'teki izin nasıl bağlanıyor?

**4** – `main` içinde çok büyük bir yerel array (`int huge[3000000];`) tanımlayıp bütün elemanlarına yaz, sonra çalıştır. Ne olur? Stack sınırını `ulimit -s` ile öğren. `int huge[2000000]` ile denersen neden çökmez? (Bu bir stack overflow.)

**5** – `/proc/self/maps`'i okuyan kodu bir fonksiyona koy ve onu `malloc(10 * 1024 * 1024)` (10 MB) çağrısından **önce** ve **sonra** çağır. İki çıktı arasında ne değişti: `[heap]` mı büyüdü, yoksa yeni bir bölge mi çıktı?

<details>
<summary>Cevaplar</summary>

**1** – **data** büyür, bss küçülür. Bir global array'in **herhangi** bir elemanı sıfırdan farklı başlatılırsa, array'in tamamı data'ya geçer (bss sadece tümü sıfır olanlar için). `{1}` yazınca ilk eleman 1, kalan 99999'u 0 — ama hepsi data'da, ve **program dosyasına yazılır**: dosya ~400 KB büyür. bss'in dosyada yer kaplamaması, tam da "hepsi sıfır" olmasından; bir tek sıfırdan farklı değer bu avantajı bozuyor. (Bu yüzden büyük sabit tabloları `const` ve gerçekten gerekliyse tanımlanır; gereksiz yere sıfırdan farklı başlatılan büyük globaller dosyayı şişirir.)

**2** –

- `static const double e = 2.718;` → **rodata** (`const` ve sıfırdan farklı; değişmez veri).
- `char buf[100];` (fonksiyon içi) → **stack** (yerel, otomatik).
- `static int counter;` (fonksiyon içi) → **bss** (`static`, sıfır başlatılıyor; fonksiyon içinde olması onu stack'e koymaz, Ders 4.4).
- `char *global_name = "Ece";` → `global_name` pointer'ı **data**'da (global, sıfırdan farklı başlatılmış bir adres), `"Ece"` yazısı **rodata**'da.

**3** – `&sabit`, `/proc/self/maps`'te `r--p` (ya da `r-xp`) izinli, yani `w` taşımayan bir bölgede. `*p = 8` o bölgeye yazmaya çalışır; işletim sistemi yazma izni olmayan bir sayfaya yazma girişimini yakalar ve süreci bir sinyalle (SIGBUS/SIGSEGV) durdurur — Ders 4.8'deki bus error tam bu. İzin sütunundaki eksik `w`, çökmenin **sebebinin** kendisi; `const`'un donanım düzeyindeki karşılığı o salt-okunur sayfa.

**4** – `int huge[3000000]` (12 MB) çalıştırılınca segmentation fault verir. `ulimit -s` bu sistemde 8192 KB, yani **8 MB**: stack bu sınırdan büyüyemez. 12 MB'lık array elemanlarına yazarken stack'in izinli bölgesinin dışına çıkılır ve çöker. `int huge[2000000]` = 8.000.000 byte ≈ 7812 KB; 8192 KB sınırının **altında** kaldığı için çökmez. Yani çökme array'in büyük olmasından değil, stack sınırını **aşmasından**; sınıra yakın ama altındaki bir array çalışır. Büyük veriler için stack değil heap (`malloc`, Ders 4.22) kullanılır; `[stack]` aralığı `/proc/self/maps`'te başta küçük görünür, çekirdek gerektikçe 8 MB'a kadar büyütür.

**5** – Genellikle **yeni bir bölge** çıkar, `[heap]` büyümez. Büyük ayırmalar (bu eşik glibc'de tipik olarak 128 KB) `malloc` tarafından `mmap` ile, işletim sisteminden ayrı bir bölge olarak alınır; `/proc/self/maps`'te stack'e yakın yüksek adreslerde, dosya adı olmayan yeni bir `rw-p` satırı belirir. Küçük ayırmalar ise `[heap]`'i yukarı doğru büyütür. `free` ettiğinde `mmap`'li bölge işletim sistemine geri verilir ve haritadan kaybolur; heap'ten gelen küçük ayırmalar ise genelde programda kalır (Ders 4.22).

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §7.9 ve Bölüm 9: bir sürecin sanal bellek düzeni.
- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §5.4 ve §8.7: bellek bölgeleri ve `malloc`.
- Linux `proc(5)` man sayfası: `/proc/<pid>/maps` sütunlarının anlamı.
- `size(1)` man sayfası: text, data, bss bölümleri.

**Sıradaki ders:** Dinamik bellek. `malloc`, `calloc`, `realloc`, `free`; bellek sızıntısı ve valgrind ile tespiti.
