---
title: "10.16 Dinamik kütüphaneler"
description: "Paylaşılan kütüphane oluşturmak: -fPIC -shared, libhesap.so; yükleyicinin arama sırası, LD_LIBRARY_PATH, RPATH ve $ORIGIN; ldd, readelf -d, nm -D; dlopen/dlsym ile eklenti sistemi ve -rdynamic; LD_PRELOAD ile malloc saymak; konumdan bağımsız kod: GOT ve PLT, arm64'te R_AARCH64_ADR_GOT_PAGE, -fno-pic ile bağlama hatası; tembel bağlama, LD_DEBUG=bindings; RELRO."
---

Ders 7.17'de statik bağlamayı, Ders 7.18'de yükleyiciyi gördük. Ders 10.1'deki `strace`'te her programın libc'yi `mmap` ettiğini okuduk. Bu ders o mekanizmanın geliştirici tarafı: kendi `.so` dosyalarımızı üretmek, programı çalıştırırken yüklemek ve **eklenti sistemleri** kurmak. Derleyici projelerinin çoğu bu yolla genişliyor: `clang -fplugin`, LLVM geçişleri, tarayıcı eklentileri, Python'un C modülleri.

---

## 1. Kütüphane oluşturmak

```c
/* hesap.h */
#ifndef HESAP_H
#define HESAP_H
int topla(int a, int b);
int sayac_artir(void);
extern int hesap_surum;
#endif
```

```c
/* hesap.c */
#include "hesap.h"
#include <stdio.h>
int hesap_surum = 2;
static int gizli_sayac = 0;
int topla(int a, int b) { return a + b; }
int sayac_artir(void) { return ++gizli_sayac; }
__attribute__((constructor)) static void yuklendi(void) { printf("[libhesap yuklendi]\n"); }
__attribute__((destructor)) static void bosaltildi(void) { printf("[libhesap bosaltildi]\n"); }
```

```c
/* ana.c */
#include "hesap.h"
#include <stdio.h>
int main(void) {
    printf("topla(30, 12) = %d, surum = %d\n", topla(30, 12), hesap_surum);
    sayac_artir();
    printf("sayac = %d\n", sayac_artir());
    return 0;
}
```

```
$ cc -fPIC -shared -Wall hesap.c -o libhesap.so
$ cc ana.c -L. -lhesap -o ana
$ ./ana
./ana: error while loading shared libraries: libhesap.so: cannot open shared object file: No such file or directory
$ echo $?
127
$ LD_LIBRARY_PATH=. ./ana
[libhesap yuklendi]
topla(30, 12) = 42, surum = 2
sayac = 2
[libhesap bosaltildi]
```

- `-shared`: yürütülebilir yerine paylaşılan nesne üret. `-fPIC`: konumdan bağımsız kod (Bölüm 4).
- `-L.`, bağlayıcıya derleme **anında** nereye bakacağını söylüyor. Çalışma zamanı ise başka bir konu: bağlayıcı yalnızca "libhesap.so gerekli" notunu bırakıyor, yerini değil. 127 kodu, yükleyicinin kütüphaneyi bulamaması.

Yükleyici (`ld-linux`) sırayla şuralara bakıyor: `LD_LIBRARY_PATH`, programa gömülü `RUNPATH`, `/etc/ld.so.cache` ve sistem dizinleri (`/lib`, `/usr/lib`). Programla birlikte taşınacak bir kütüphane için en temiz yol **`$ORIGIN`**: "yürütülebilir dosyanın kendi dizini".

```
$ cc ana.c -L. -lhesap -Wl,-rpath,'$ORIGIN' -o ana2
$ ./ana2
[libhesap yuklendi]
topla(30, 12) = 42, surum = 2
sayac = 2
[libhesap bosaltildi]
$ ldd ana2
	linux-vdso.so.1 (0x0000ffffb3ec7000)
	libhesap.so => /tmp/w/./libhesap.so (0x0000ffffb3e30000)
	libc.so.6 => /lib/aarch64-linux-gnu/libc.so.6 (0x0000ffffb3c70000)
	/lib/ld-linux-aarch64.so.1 (0x0000ffffb3e8a000)
$ readelf -d ana2 | grep -E "NEEDED|RUNPATH"
 0x0000000000000001 (NEEDED)             Shared library: [libhesap.so]
 0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]
 0x000000000000001d (RUNPATH)            Library runpath: [$ORIGIN]
$ nm -D libhesap.so | grep -v " [wU] "
0000000000020020 D hesap_surum
0000000000000688 T sayac_artir
0000000000000668 T topla
```

`NEEDED` listesi, `RUNPATH` ve `nm -D`'nin dışa açık sembolleri: ELF başlığına kazınmış (Ders 7.16). `gizli_sayac` listede yok, `static` olduğu için; `-fvisibility=hidden` ile diğer semboller de varsayılan olarak gizlenebilir ve yalnızca `__attribute__((visibility("default")))` olanlar dışa çıkar. Kütüphanelerin API'sini küçük tutmanın ve hızlanmanın yolu bu.

`constructor` fonksiyonları `main`'den önce çalışıyor (Ders 7.18'deki `.init_array`); C++ global nesneleri de böyle. Konvansiyonel sürümleme için kütüphanenin `SONAME`'i (`libhesap.so.2`) ve sembolik bağlar (Ders 10.15) kullanılıyor.

---

## 2. dlopen: çalışırken yüklemek

`dlopen`, kütüphaneyi program **çalışırken** açar; `dlsym` adıyla sembol arar. Bu mekanizma bir **eklenti sistemini** üç küçük parçayla kurar: bir arayüz, derlenmiş `.so`'lar, onları tarayan bir ana program.

```c
/* eklenti.h: her eklenti bu yapiyi "eklenti_tanim" adiyla disa acar */
#ifndef EKLENTI_H
#define EKLENTI_H
typedef struct {
    const char *ad;
    void (*donustur)(char *s);
} Eklenti;
void ana_log(const char *mesaj);          /* ana programin eklentilere sundugu fonksiyon */
#endif
```

```c
/* eklentiler/buyuk.c */
#include "../eklenti.h"
#include <ctype.h>
static void donustur(char *s) { for (; *s; s++) *s = (char)toupper((unsigned char)*s); ana_log("buyuk calisti"); }
const Eklenti eklenti_tanim = { "buyuk", donustur };
```

```c
/* eklentiler/ters.c */
#include "../eklenti.h"
#include <string.h>
static void donustur(char *s) { for (size_t i = 0, j = strlen(s); i + 1 < j; i++, j--) { char t = s[i]; s[i] = s[j - 1]; s[j - 1] = t; } }
const Eklenti eklenti_tanim = { "ters", donustur };
```

```c
/* Eklenti sistemi: dizindeki .so dosyalarini dlopen ile yukle */
#include "eklenti.h"
#include <dirent.h>
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

void ana_log(const char *mesaj) { printf("  [ana program] %s\n", mesaj); }

int main(int argc, char **argv) {
    const char *dizin = argc > 1 ? argv[1] : "./eklentiler";
    char metin[64] = "merhaba dunya";
    DIR *d = opendir(dizin);
    if (!d) { perror(dizin); return 1; }
    struct dirent *e;
    while ((e = readdir(d))) {
        size_t n = strlen(e->d_name);
        if (n < 4 || strcmp(e->d_name + n - 3, ".so")) continue;
        char yol[512]; snprintf(yol, sizeof yol, "%s/%s", dizin, e->d_name);
        void *h = dlopen(yol, RTLD_NOW | RTLD_LOCAL);
        if (!h) { fprintf(stderr, "dlopen: %s\n", dlerror()); continue; }
        const Eklenti *ek = dlsym(h, "eklenti_tanim");
        if (!ek) { fprintf(stderr, "dlsym: %s\n", dlerror()); dlclose(h); continue; }
        ek->donustur(metin);
        printf("%-6s -> %s\n", ek->ad, metin);
        dlclose(h);
    }
    closedir(d);
    return 0;
}
```

```
$ for f in buyuk ters; do cc -fPIC -shared -Wall eklentiler/$f.c -o eklentiler/$f.so; done
$ cc -Wall -rdynamic kabukbas.c -o kabukbas -ldl && ./kabukbas
  [ana program] buyuk calisti
buyuk  -> MERHABA DUNYA
ters   -> AYNUD ABAHREM
$ cc -Wall kabukbas.c -o kb2 -ldl && ./kb2
dlopen: ./eklentiler/buyuk.so: undefined symbol: ana_log
ters   -> aynud abahrem
```

Ana program hiç yeniden derlenmedi; yalnızca o dizine yeni bir `.so` koymak yeni bir özellik ekliyor. Eklentinin ana programa geri çağrı yapabilmesi (`ana_log`) için ana programın kendi sembollerini dışa açması gerekiyor: `-rdynamic`. O olmadan, `ana_log`'a ihtiyaç duyan `buyuk` reddedildi; ihtiyaç duymayan `ters` çalıştı.

Tasarım notları. **ABI** kritik: ana programın ve eklentinin `struct` düzenleri aynı olmalı (`Eklenti`'nin başına bir `surum` alanı koymak yaygındır). `dlclose` sonrası eklentinin kodu bellekten kalkabilir: içeriden dışarı sızan her pointer sarkar. Eklenti ana programla aynı adres alanında: hatası bütün süreci düşürür. Yalıtım gerekiyorsa süreç + boru (Ders 10.5). LLVM'in `-load` ve `clang -fplugin` seçenekleri bu mekanizmanın aynısı.

---

## 3. LD_PRELOAD: başkasının programına girmek

Yükleyici `LD_PRELOAD`'daki kütüphaneleri **önce** yüklüyor, yani onların sembolleri kazanıyor. Hiçbir programı yeniden derlemeden bir fonksiyonu araya alabiliyoruz; `RTLD_NEXT` ise "sıradaki gerçeğini bul" diyor.

```c
/* LD_PRELOAD ile malloc'u araya almak */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stddef.h>
#include <unistd.h>
#include <stdio.h>
static void *(*gercek)(size_t);
static long say; static long long toplam;
void *malloc(size_t n) {
    if (!gercek) gercek = (void *(*)(size_t))dlsym(RTLD_NEXT, "malloc");
    say++; toplam += (long long)n;
    return gercek(n);
}
__attribute__((destructor)) static void bitir(void) {
    char b[96]; int k = snprintf(b, sizeof b, "[say_malloc] %ld malloc, toplam %lld bayt\n", say, toplam);
    write(2, b, (size_t)k);
}
```

```
$ cc -fPIC -shared say_malloc.c -o say_malloc.so -ldl
$ LD_PRELOAD=./say_malloc.so python3 -c pass
[say_malloc] 3167 malloc, toplam 1107768 bayt
```

Python'u hiç değiştirmedik. Bellek hata ayıklayıcılar, `jemalloc`/`tcmalloc` geçişleri (kod değişmeden `malloc` değiştirme) ve bazı `strace` benzeri araçlar bu yolu kullanıyor. Güvenlik için `setuid` programlarda `LD_PRELOAD` yok sayılıyor.

---

## 4. Konumdan bağımsız kod (PIC)

Paylaşılan kütüphane her süreçte **farklı bir adrese** yükleniyor (ASLR ve çakışmalar yüzünden). Kod bölümü adresleri içeriyorsa, bunları yüklemede düzeltmek gerekir; bu, kod sayfalarını kirletip süreçler arası paylaşımı (Ders 10.7) bozar. **PIC** çözümü: kod hiçbir mutlak adres içermesin. Mimarilerin PC-göreli adreslemesi (`adrp`, `rip` tabanlı) içerideki adresler için yeterli; dış semboller için bir tablo gerekiyor.

**GOT** (Global Offset Table): dış değişkenlerin adreslerini tutan, yazılabilir veri bölümündeki tablo. Kod **tablodan** adresi okur; sadece tablo düzeltilir.

```c
extern int dis_degisken;
extern int dis_fonk(int);
static int ic_degisken = 5;
int kullan(int x) { return dis_fonk(x) + dis_degisken + ic_degisken; }
```

```
$ cc -O2 -fPIC -c pic.c -o p1.o && objdump -dr p1.o
   8:	94000000 	bl	0 <dis_fonk>
			8: R_AARCH64_CALL26	dis_fonk
   c:	90000008 	adrp	x8, 0 <dis_degisken>
			c: R_AARCH64_ADR_GOT_PAGE	dis_degisken
  10:	f9400108 	ldr	x8, [x8]
			10: R_AARCH64_LD64_GOT_LO12_NC	dis_degisken
  14:	b9400108 	ldr	w8, [x8]
  18:	0b080008 	add	w8, w0, w8
  1c:	11001500 	add	w0, w8, #0x5
$ cc -O2 -fno-pic -fno-pie -c pic.c -o p2.o && objdump -dr p2.o
   8:	94000000 	bl	0 <dis_fonk>
			8: R_AARCH64_CALL26	dis_fonk
   c:	90000008 	adrp	x8, 0 <dis_degisken>
			c: R_AARCH64_ADR_PREL_PG_HI21	dis_degisken
  10:	b9400108 	ldr	w8, [x8]
			10: R_AARCH64_LDST32_ABS_LO12_NC	dis_degisken
  14:	0b080008 	add	w8, w0, w8
```

PIC sürümde **fazladan bir `ldr`** var: önce GOT'tan adresi, sonra değeri okuyoruz. `-fno-pic`te adres doğrudan koda bağlanıyor. PIC'in bedeli budur: dış değişken başına bir dolaylılık. `ic_degisken` (`static`) ise sabit 5'e katlandı; `static` olmayan iç semboller için `-fvisibility=hidden` ve `-Bsymbolic` benzer kazanç sağlıyor. `-fno-pic` ile `.so` yapmaya kalkınca bağlayıcı reddediyor:

```
$ cc -shared -fno-pic -fno-pie pic.c -o nopic.so
/usr/bin/ld: /tmp/pic-72f6a5.o: relocation R_AARCH64_ADR_PREL_PG_HI21 against symbol `dis_degisken' which may bind externally can not be used when making a shared object; recompile with -fPIC
```

**PLT** (Procedure Linkage Table) fonksiyonlar için. Kod, doğrudan fonksiyona değil `topla@plt` adlı küçük bir parçaya atlar; o da GOT'taki adresi yükleyip dallanır:

```
$ cc -O2 ana.c -L. -lhesap -Wl,-rpath,'$ORIGIN' -Wl,-z,lazy -o ana3
$ objdump -d --section=.plt ana3
00000000000006e0 <sayac_artir@plt>:
 6e0:	90000110 	adrp	x16, 20000 <__libc_start_main@GLIBC_2.34>
 6e4:	f9400a11 	ldr	x17, [x16, #16]
 6e8:	91004210 	add	x16, x16, #0x10
 6ec:	d61f0220 	br	x17
```

**Tembel bağlama**: başlangıçta GOT girişi çözümleyiciyi gösteriyor, ilk çağrı gerçek adresi bulup GOT'a yazıyor; sonrakiler doğrudan gidiyor. Hiç çağrılmayan fonksiyon için maliyet yok. Bağlayıcının ne yaptığı izlenebiliyor:

```
$ LD_DEBUG=bindings ./ana3 2>&1 | grep -E "topla|sayac_artir|hesap_surum"
        73:	binding file ./ana3 [0] to /tmp/w/libhesap.so [0]: normal symbol `hesap_surum'
        73:	binding file ./ana3 [0] to /tmp/w/libhesap.so [0]: normal symbol `topla'
        73:	binding file ./ana3 [0] to /tmp/w/libhesap.so [0]: normal symbol `sayac_artir'
```

Güvenlik tarafı: GOT yazılabilirse, bir bellek açığı buradaki adresleri değiştirip kontrolü ele geçirebilir (Ders 7.14). **RELRO** (`readelf -l` ile `GNU_RELRO` segmenti; Ders 10.1'deki `strace`'te `mprotect(..., PROT_READ)`) çözümü: yükleme bittikten sonra bölgeyi salt okunur yap. `-z now` ile tam RELRO: tüm semboller başlangıçta çözülür ve GOT da salt okunur olur. Bazı dağıtımların gcc'si bunu varsayılan yapıyor; burada kullandığımız clang 18'de varsayılan değil (`readelf -d`'de `NOW` bayrağı yok), o yüzden kendin eklemelisin.

---

## Alıştırmalar

**1** – `libhesap.so`'yu `hesap_surum` değişkenini 3 yapıp tekrar derle; `ana`'yı yeniden derlemeden çalıştır. Ne görüyorsun? Şimdi `topla`'nın imzasını `long topla(long, long, long)` yap. Neden derleyici hata vermez, ne olur?

**2** – Üçüncü bir eklenti yaz: tekrarlı boşlukları tek boşluğa indirsin. Arayüze `int surum;` alanı ekle ve ana programın uyumsuz eklentiyi reddetmesini sağla.

**3** – `dlclose` yaptıktan sonra eklentinin fonksiyonunu çağırmaya çalış. Ne olur? Çözüm için bir kural yaz.

**4** – `LD_PRELOAD` ile `open` çağrısını araya alıp açılan dosyaların listesini stderr'e yazan bir araç yaz. Variadic `open` için neye dikkat etmelisin? Neden `strace` kadar her şeyi göremezsin?

**5** – Bir kütüphane fonksiyon çağrısı PLT üzerinden gidiyor. Çok sık çağrılan bir fonksiyon için fazladan iki komut ne kadar maliyetli? `-fno-plt` ne yapıyor? `-fno-semantic-interposition` hangi optimizasyona izin veriyor?

<details>
<summary>Cevaplar</summary>

**1** – `surum = 3` yeniden derlemesiz görünür: `ana`, değeri kütüphanenin verisinden okuyor (paylaşımlı kütüphanelerin avantajı). `topla`'nın imzasını değiştirmek ise **ABI kırılması**: C bağlayıcısı fonksiyon adından başka bir şey bilmiyor (Ders 7.16); `ana` iki argüman hazırlayıp çağırıyor, kütüphane üç `long` okuyor: üçüncü register'daki rastgele değer kullanılıyor. Sonuç tanımsız ve sessiz. SONAME sürümü bu nedenle var. C++'taki isim bezemesi (Faz 13) bu sorunu kısmen yakalar.

**2** – Tekrarlı boşluk: yazma/okuma iki işaretçisiyle yerinde sıkıştır. Ana program: `if (ek->surum != EKLENTI_SURUM) { fprintf(stderr, "uyumsuz eklenti %s\n", yol); dlclose(h); continue; }`. Alanı yapının **başına** koy; böylece eski sürüm eklentiler de hatasız okunabiliyor.

**3** – Kapatıldıktan sonra kod eşlemesi kaldırılmış olabilir (başka kullanıcı yoksa): `SIGSEGV`. Kural: `dlclose` sonrası o kütüphaneden alınmış hiçbir pointer (fonksiyon, veri, statik string) kullanılamaz. Çoğu büyük program bu yüzden eklentileri hiç kapatmaz.

**4** – `#include <stdarg.h>`; `int open(const char *yol, int bayrak, ...) { mode_t m = 0; if (bayrak & (O_CREAT | O_TMPFILE)) { va_list a; va_start(a, bayrak); m = va_arg(a, mode_t); va_end(a); } ... gercek(yol, bayrak, m); }`. `dlsym(RTLD_NEXT, "open")` ile gerçeğini al. Görülemeyenler: libc'nin içinden yapılan çağrılar (`fopen` gibi iç sembol kullananlar), doğrudan `syscall` kullananlar, statik bağlı programlar. `strace` çekirdek seviyesinde olduğundan bunların hepsini görür.

**5** – İki ek komut (`adrp`/`ldr`) artı dolaylı dal; 1 ns'nin altında ama dal tahmincisi kaçırdığında daha fazla. Sıklıkla önemsiz, çok sıcak kod yollarında önemli. `-fno-plt`: PLT'yi atlayıp çağrı noktasında GOT üzerinden dolaylı çağırır (RELRO ve hızlı başlangıçla iyi çalışır). `-fno-semantic-interposition`: derleyiciye "bu sembolü `LD_PRELOAD` değiştiremez" der; kütüphane içi çağrıları satır içine alabilir. Bu tek bayrak Python'u ölçülebilir derecede hızlandırmıştı.

</details>

---

## Kaynaklar

- John Levine, *Linkers and Loaders*, Morgan Kaufmann, 2000.
- Ulrich Drepper, "How To Write Shared Libraries", 2011: GOT, PLT, sembol görünürlüğü, performans.
- Ian Lance Taylor, "Linkers" yazı dizisi, 2007: bağlayıcıların çalışma biçimi.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 41–42: paylaşılan kütüphaneler ve `dlopen`.
- `man 8 ld.so`, `man 3 dlopen`, `man 7 rtld-audit`.

**Sıradaki ders:** Ağ programlamaya giriş. Soket, basit TCP sunucu ve istemci.
