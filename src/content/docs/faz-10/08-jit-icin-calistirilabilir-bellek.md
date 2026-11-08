---
title: "10.8 JIT için çalıştırılabilir bellek"
description: "JIT derleyicinin en küçük hali: makine kodunu mmap ile alınan belleğe yazmak, mprotect ile çalıştırılabilir yapmak ve fonksiyon işaretçisiyle çağırmak; x86-64 ve arm64 için el ile kodlanmış baytlar; W^X politikası ve iki SIGSEGV deneyi; arm64'te komut önbelleğini temizlemek; sonek ifadeleri makine koduna çeviren küçük bir derleyici, üretilen kodun objdump ile okunması; yorumlayıcı 11.5 ns, JIT 5.4 ns, clang -O2 1.15 ns."
---

Ders 10.7'de `mmap` ile bellek almayı ve `mprotect` ile izinlerini değiştirmeyi gördük. Faz 7'de de makine kodunun sadece baytlar olduğunu öğrendik (Ders 7.3). İkisini birleştirince şu mümkün: program **çalışırken** yeni makine kodu üretip kendi kendine çağırabilir. V8, HotSpot, LuaJIT ve LLVM'in ORC JIT'i bunu yapar. Bu derste işin çekirdeğini yazıyoruz: 40 satırda bir fonksiyon "üretmek", sonra küçük bir ifade derleyicisi. Faz 18–20'deki kod üreticilerinin en basit, en doğrudan hali bu.

---

## 1. Bayt yaz, çalıştır, çağır

Bir fonksiyon, işlemcinin komut olarak yorumladığı bayt dizisi. Dolayısıyla makine kodu üretmek için **bir diziye bayt yazmak** yetiyor:

| Fonksiyon | x86-64 (System V) | arm64 |
| --- | --- | --- |
| `int f(void) { return 42; }` | `b8 2a 00 00 00` `mov eax, 42`<br/>`c3` `ret` | `52800540` `mov w0, #42`<br/>`d65f03c0` `ret` |
| `int g(int a, int b) { return a + b; }` | `8d 04 37` `lea eax, [rdi+rsi]`<br/>`c3` `ret` | `0b010000` `add w0, w0, w1`<br/>`d65f03c0` `ret` |

Kodlamayı Ders 7.3 ve 7.7'de görmüştük; çağrı kuralı Ders 7.10 (x86-64'te ilk iki `int` argüman `edi`, `esi`; arm64'te `w0`, `w1`; dönüş `eax` ve `w0`).

```c
/* En basit JIT: makine kodunu bellege yaz, calistirilabilir yap, cagir */
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>

#if defined(__x86_64__)
static const unsigned char kirk_iki[] = { 0xb8, 0x2a, 0x00, 0x00, 0x00,   /* mov eax, 42 */
                                          0xc3 };                          /* ret */
static const unsigned char topla[]    = { 0x8d, 0x04, 0x37,               /* lea eax, [rdi+rsi] */
                                          0xc3 };                          /* ret */
#elif defined(__aarch64__)
static const uint32_t kirk_iki[] = { 0x52800540,    /* mov w0, #42 */
                                     0xd65f03c0 };  /* ret */
static const uint32_t topla[]    = { 0x0b010000,    /* add w0, w0, w1 */
                                     0xd65f03c0 };  /* ret */
#endif

static void *uret(const void *kod, size_t n) {
    void *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) { perror("mmap"); return NULL; }
    memcpy(p, kod, n);
    if (mprotect(p, 4096, PROT_READ | PROT_EXEC) < 0) { perror("mprotect"); return NULL; }
    __builtin___clear_cache((char *)p, (char *)p + n);     /* arm64'te sart, x86'da bos */
    return p;
}

int main(void) {
    int (*f)(void) = (int (*)(void))uret(kirk_iki, sizeof kirk_iki);
    int (*g)(int, int) = (int (*)(int, int))uret(topla, sizeof topla);
    printf("f() = %d\n", f());
    printf("g(30, 12) = %d\n", g(30, 12));
    return 0;
}
```

Aynı kaynak iki mimaride de çalıştı:

```
$ uname -m; ./jit1        # arm64 Linux
aarch64
f() = 42
g(30, 12) = 42
$ uname -m; ./jit1        # x86-64 Linux
x86_64
f() = 42
g(30, 12) = 42
```

`f` dediğimiz şey derleyicinin hiç görmediği bir bellek bölgesi. Fonksiyon işaretçisine çevirmek (Ders 4.11) yeterli: `f()` sadece o adrese bir `call`/`blr` üretiyor. Bu dönüşüm C standardına göre tanımsız (veri işaretçisi ile fonksiyon işaretçisi arası), ama POSIX `dlsym` (Ders 10.16) için de buna güveniyor ve bütün gerçek platformlarda çalışıyor.

---

## 2. W^X: yaz ya da çalıştır, ikisi birden değil

`PROT_READ|PROT_WRITE|PROT_EXEC` tek çağrıda istenebilir, ama yapılmamalı. Hem yazılabilir hem çalıştırılabilir bir bölge, bir bellek açığı bulan saldırganın kendi kodunu yerleştirip çalıştırması için hazır bir sahne (Ders 7.14). Modern politika **W^X** (write xor execute): bir sayfa aynı anda ikisi birden olamaz. Üret, sonra izni değiştir; yukarıda yaptığımız bu.

```c
/* W^X: yazilabilir bellegi calistirmak, calistirilabilir bellege yazmak */
#include <setjmp.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
static sigjmp_buf d;
static void h(int s, siginfo_t *b, void *c) { (void)s; (void)c; printf("  SIGSEGV, adres %p, si_code %d\n", b->si_addr, b->si_code); siglongjmp(d, 1); }
#if defined(__x86_64__)
static const unsigned char kod[] = { 0xb8, 0x2a, 0, 0, 0, 0xc3 };
#else
static const uint32_t kod[] = { 0x52800540, 0xd65f03c0 };
#endif
int main(void) {
    setbuf(stdout, NULL);
    struct sigaction sa; memset(&sa, 0, sizeof sa); sa.sa_sigaction = h; sa.sa_flags = SA_SIGINFO; sigaction(SIGSEGV, &sa, NULL);
    char *p = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    memcpy(p, kod, sizeof kod);
    printf("PROT_READ|PROT_WRITE bellegi cagir:\n");
    if (sigsetjmp(d, 1) == 0) printf("  sonuc %d\n", ((int (*)(void))p)());
    mprotect(p, 4096, PROT_READ | PROT_EXEC);
    __builtin___clear_cache(p, p + sizeof kod);
    printf("PROT_READ|PROT_EXEC bellegi cagir:\n");
    if (sigsetjmp(d, 1) == 0) printf("  sonuc %d\n", ((int (*)(void))p)());
    printf("PROT_READ|PROT_EXEC bellege yaz:\n");
    if (sigsetjmp(d, 1) == 0) { p[0] = 0; printf("  yazdi\n"); }
    return 0;
}
```

```
$ ./wx
PROT_READ|PROT_WRITE bellegi cagir:
  SIGSEGV, adres 0xffff91bf2000, si_code 2
PROT_READ|PROT_EXEC bellegi cagir:
  sonuc 42
PROT_READ|PROT_EXEC bellege yaz:
  SIGSEGV, adres 0xffff91bf2000, si_code 2
```

`si_code 2` Ders 10.6'daki `SEGV_ACCERR`: sayfa var, izin yok. Bu donanımın sayfa tablosundaki **NX** (x86-64) ya da **XN/UXN** (arm64) biti (Ders 7.27). Buradaki sinyal işleyici kısa olduğu için `printf` çağırmayı göze aldık; Ders 10.6'daki kural normalde `write` der.

Gerçek JIT'lerde çift eşleme (aynı fiziksel sayfayı bir yerde RW, başka yerde RX eşlemek; Linux'ta `memfd_create` + iki `mmap`) ya da `mprotect` geçişleri kullanılıyor. `mprotect` pahalı: TLB temizliği gerektiriyor ve iş parçacıkları arasında tüm çekirdeklere yayılıyor. V8 bu yüzden kodu büyük parçalar halinde üretip topluca açıyor.

:::caution[macOS]
Apple Silicon'da JIT için `mmap`'e `MAP_JIT` bayrağı, yazma/çalıştırma geçişi için `pthread_jit_write_protect_np()`, imzalı uygulamalarda da bir yetki gerekiyor. Bu yüzden derse Linux'ta devam ediyoruz; ama kavram aynı.
:::

### Komut önbelleği

x86-64 komut ve veri önbelleklerini donanımda tutarlı tutuyor; bir adrese yazıp sonra oradan yürütmek çalışır. arm64 **tutmuyor**: yeni yazılan kod veri önbelleğinde kalmış, komut önbelleğinde eski bayt olabilir. Bu yüzden `__builtin___clear_cache` çağrısı şart: arm64'te `dc cvau` (veri önbelleğini temizle) ve `ic ivau` (komut önbelleğini geçersiz kıl) dizisine dönüşüyor, x86-64'te ise hiçbir şey üretmiyor. Bir JIT'i sadece x86'da test edip arm'a taşımak yıllardır klasik hata kaynağı: çoğu zaman çalışır, ara sıra çöker.

---

## 3. Küçük bir derleyici

Şimdi kod üreticisi yazalım. Dil: tek değişkenli **sonek (postfix) ifadeler**: `x x * 3 x * + 7 -`, yani $x^2 + 3x - 7$. Bir yığın makinesinin (Ders 8.4) tam karşılığı. Çeviri tek geçiş: her işlem için birkaç sabit komut yaz.

| Bayt kodu | x86-64 | arm64 |
| --- | --- | --- |
| Sayı yükle | `mov eax, v; push rax` | `movz w9, lo; movk w9, hi; str x9, [sp, #-16]!` |
| `x` yükle | `push rdi` | `str x0, [sp, #-16]!` |
| İkili işlem | `pop rcx; pop rax; add/sub/imul; push rax` | `ldr x10, [sp], #16; ldr x9, [sp], #16; add/sub/mul; str x9, [sp, #-16]!` |
| Bitiş | `pop rax; ret` | `ldr x0, [sp], #16; ret` |

arm64'te `sp` 16 bayta hizalı olmak zorunda (Ders 7.10 ile aynı mantık, ama burada her erişimde donanım denetliyor); bu yüzden 8 baytlık değerler için 16 bayt ayırıyoruz.

```c
/* Sonek ifade derleyicisi: "x x * 3 +" -> makine kodu; yorumlayici ile karsilastirma */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>

typedef enum { SAYI, X, TOPLA, CIKAR, CARP } Tur;
typedef struct { Tur tur; int deger; } Kod;

static int cevir(const char *s, Kod *k) {          /* metni bayt koduna cevir */
    char t[256]; snprintf(t, sizeof t, "%s", s);
    int n = 0;
    for (char *p = strtok(t, " "); p; p = strtok(NULL, " ")) {
        if (!strcmp(p, "x"))      k[n++] = (Kod){ X, 0 };
        else if (!strcmp(p, "+")) k[n++] = (Kod){ TOPLA, 0 };
        else if (!strcmp(p, "-")) k[n++] = (Kod){ CIKAR, 0 };
        else if (!strcmp(p, "*")) k[n++] = (Kod){ CARP, 0 };
        else                      k[n++] = (Kod){ SAYI, atoi(p) };
    }
    return n;
}

static int yorumla(const Kod *k, int n, int x) {
    int y[64], t = 0;
    for (int i = 0; i < n; i++) switch (k[i].tur) {
        case SAYI:  y[t++] = k[i].deger; break;
        case X:     y[t++] = x; break;
        case TOPLA: t--; y[t - 1] = (int)((unsigned)y[t - 1] + (unsigned)y[t]); break;
        case CIKAR: t--; y[t - 1] = (int)((unsigned)y[t - 1] - (unsigned)y[t]); break;
        case CARP:  t--; y[t - 1] = (int)((unsigned)y[t - 1] * (unsigned)y[t]); break;
    }
    return y[0];
}

static unsigned char *yaz;
#if defined(__x86_64__)
static void b(int c) { *yaz++ = (unsigned char)c; }
static void e_sayi(int v) { b(0xb8); memcpy(yaz, &v, 4); yaz += 4; b(0x50); }   /* mov eax, v; push rax */
static void e_x(void)     { b(0x57); }                                          /* push rdi */
static void e_ikili_bas(void) { b(0x59); b(0x58); }                             /* pop rcx; pop rax */
static void e_ikili_son(void) { b(0x50); }                                      /* push rax */
static void e_topla(void) { e_ikili_bas(); b(0x01); b(0xc8); e_ikili_son(); }   /* add eax, ecx */
static void e_cikar(void) { e_ikili_bas(); b(0x29); b(0xc8); e_ikili_son(); }   /* sub eax, ecx */
static void e_carp(void)  { e_ikili_bas(); b(0x0f); b(0xaf); b(0xc1); e_ikili_son(); } /* imul eax, ecx */
static void e_bitir(void) { b(0x58); b(0xc3); }                                 /* pop rax; ret */
#elif defined(__aarch64__)
static void k(uint32_t c) { memcpy(yaz, &c, 4); yaz += 4; }
static void it(int r)  { k(0xF81F0FE0u | (unsigned)r); }                        /* str xR, [sp, #-16]! */
static void al(int r)  { k(0xF84107E0u | (unsigned)r); }                        /* ldr xR, [sp], #16 */
static void e_sayi(int v) {
    k(0x52800009u | ((unsigned)(v & 0xffff) << 5));                             /* movz w9, #lo */
    k(0x72A00009u | ((unsigned)((v >> 16) & 0xffff) << 5));                     /* movk w9, #hi, lsl #16 */
    it(9);
}
static void e_x(void)     { it(0); }
static void e_topla(void) { al(10); al(9); k(0x0B0A0129u); it(9); }             /* add w9, w9, w10 */
static void e_cikar(void) { al(10); al(9); k(0x4B0A0129u); it(9); }             /* sub w9, w9, w10 */
static void e_carp(void)  { al(10); al(9); k(0x1B0A7D29u); it(9); }             /* mul w9, w9, w10 */
static void e_bitir(void) { al(0); k(0xD65F03C0u); }                            /* ldr x0, [sp], #16; ret */
#endif

typedef int (*Fn)(int);
static Fn derle(const Kod *kod, int n, size_t *boy) {
    unsigned char *bas = mmap(NULL, 4096, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    yaz = bas;
    for (int i = 0; i < n; i++) switch (kod[i].tur) {
        case SAYI:  e_sayi(kod[i].deger); break;
        case X:     e_x(); break;
        case TOPLA: e_topla(); break;
        case CIKAR: e_cikar(); break;
        case CARP:  e_carp(); break;
    }
    e_bitir();
    *boy = (size_t)(yaz - bas);
    mprotect(bas, 4096, PROT_READ | PROT_EXEC);
    __builtin___clear_cache((char *)bas, (char *)yaz);
    return (Fn)(void *)bas;
}

static double simdi(void) { struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + t.tv_nsec * 1e-9; }

__attribute__((noinline)) static int yerel(int x) { return (int)((unsigned)x * (unsigned)x + 3u * (unsigned)x - 7u); }

int main(int argc, char **argv) {
    const char *ifade = argc > 1 ? argv[1] : "x x * 3 x * + 7 -";
    Kod k[64]; int n = cevir(ifade, k);
    size_t boy; Fn f = derle(k, n, &boy);
    printf("ifade: %s  (%d islem, %zu bayt makine kodu)\n", ifade, n, boy);
    for (int x = 0; x <= 3; x++) printf("  x=%d: yorumlayici %d, JIT %d\n", x, yorumla(k, n, x), f(x));
    if (argc > 2) { FILE *d = fopen(argv[2], "wb"); fwrite((void *)f, 1, boy, d); fclose(d); }
    enum { N = 100000000 };
    volatile int s = 0;
    double t0 = simdi(); for (int i = 0; i < N; i++) s += yorumla(k, n, i);
    double t1 = simdi(); for (int i = 0; i < N; i++) s += f(i);
    double t2 = simdi(); for (int i = 0; i < N; i++) s += yerel(i);
    double t3 = simdi();
    printf("yorumlayici : %6.2f ns/cagri\n", (t1 - t0) / N * 1e9);
    printf("JIT         : %6.2f ns/cagri\n", (t2 - t1) / N * 1e9);
    printf("clang -O2   : %6.2f ns/cagri\n", (t3 - t2) / N * 1e9);
    return 0;
}
```

```
$ ./ifade "x x * 3 x * + 7 -" k.bin          # arm64
ifade: x x * 3 x * + 7 -  (9 islem, 108 bayt makine kodu)
  x=0: yorumlayici -7, JIT -7
  x=1: yorumlayici -3, JIT -3
  x=2: yorumlayici 3, JIT 3
  x=3: yorumlayici 11, JIT 11
yorumlayici :  11.47 ns/cagri
JIT         :   5.39 ns/cagri
clang -O2   :   1.15 ns/cagri
```

Program üretilen baytları dosyaya da yazıyor; böylece kendi kodumuzu `objdump`'a okutabiliyoruz:

```
$ objdump -D -b binary -m aarch64 k.bin
   0:	f81f0fe0 	str	x0, [sp, #-16]!
   4:	f81f0fe0 	str	x0, [sp, #-16]!
   8:	f84107ea 	ldr	x10, [sp], #16
   c:	f84107e9 	ldr	x9, [sp], #16
  10:	1b0a7d29 	mul	w9, w9, w10
  14:	f81f0fe9 	str	x9, [sp, #-16]!
  18:	52800069 	mov	w9, #0x3
  1c:	72a00009 	movk	w9, #0x0, lsl #16
  20:	f81f0fe9 	str	x9, [sp, #-16]!
  ...
  64:	f84107e0 	ldr	x0, [sp], #16
  68:	d65f03c0 	ret
```

x86-64'te aynı ifade 39 bayt:

```
$ objdump -D -b binary -m i386:x86-64 -M intel k.bin
   0:	57                   	push   rdi
   1:	57                   	push   rdi
   2:	59                   	pop    rcx
   3:	58                   	pop    rax
   4:	0f af c1             	imul   eax,ecx
   7:	50                   	push   rax
   8:	b8 03 00 00 00       	mov    eax,0x3
   d:	50                   	push   rax
   ...
  25:	58                   	pop    rax
  26:	c3                   	ret
```

Kod **berbat** ama doğru: art arda `push rdi; push rdi; pop rcx; pop rax` değerleri yığına koyup hemen geri alıyor. Yine de yorumlayıcının iki katından hızlı: `switch`'in dallanma ve bayt kodu tarama maliyeti kayboldu. Tablo üç seviyeyi gösteriyor:

| Yöntem | ns/çağrı | Neyi yapmıyor? |
| --- | --- | --- |
| Yorumlayıcı | 11.47 | Her işlem için `switch` dallanması |
| Şablon JIT | 5.39 | Dallanma yok; ama her değer bellekten geçiyor |
| `clang -O2` | 1.15 | Yığın yok: register'da, sabit katlama ve çarpma birleştirme |

Baseline JIT'ler (örneğin V8'in Sparkplug'ı) tam olarak ortadaki yöntem: üretimi çok hızlı, kalitesi ortalama. Üstteki optimizasyonlar (register ataması, Faz 16; sabit katlama) ise kalan 4.7 kat farkı kapatıyor; Alıştırma 3 ilk adım. (x86-64'te Rosetta emülasyonu altında ölçülen 22.9 / 4.4 / 1.9 ns anlamlı değil: emülatör kendi çevirisini yapıyor.)

---

## Alıştırmalar

**1** – `int h(int a) { return a * a; }` fonksiyonunu kendi mimarinde `clang -O2 -c` ile derle, `objdump -d` ile baytlarını oku ve Bölüm 1'deki gibi bir diziye yazıp çağır.

**2** – Sonek dile `/` ve `%` ekle (x86-64'te `idiv`, `cdq` gerekli; arm64'te `sdiv`). Sıfıra bölmede iki mimarinin farkını Ders 7.28'den hatırla: üretilen kod ne yapmalı?

**3** – Basit bir **gözetleme deliği (peephole) optimizasyonu**: üretim sırasında "son komut `push rax`, yeni komut `pop rax`" ise ikisini de yazma. Sadece x86-64 için yaz. 39 bayt kaça iniyor? `push rax; pop rcx` gibi benzer kalıplar için ne yapılabilir? Daha ileri: ilk birkaç yığın yerini register'a eşle.

**4** – JIT'in içinden bir C fonksiyonu çağır: `printf` adresini 64 bitlik sabit olarak yükle (`mov rax, imm64` / `movz`+3×`movk`) ve `call rax` / `blr x16` üret. x86-64'te yığın hizası (Ders 7.10) ve arm64'te `x30`'un (dönüş adresi) saklanması için ne yapmalısın?

**5** – Bir tarayıcı JIT'i, üretilen kodda bir bellek taşması olduğunda RWX sayfalar kullanıyorsa saldırgan ne kazanır? W^X neyi engeller, neyi engellemez?

<details>
<summary>Cevaplar</summary>

**1** – arm64: `1b007c00` (`mul w0, w0, w0`) + `d65f03c0`. x86-64 (`-O2`): `0f af ff` (`imul edi, edi`) + `89 f8` (`mov eax, edi`) + `c3`. Baytlar derleyici sürümüne göre biraz değişebilir; önemli olan okuduğunu diziye koymak. Uzunluğu `objdump`'tan oku, `sizeof` ile geçir.

**2** – x86-64: `pop rcx; pop rax; cdq; idiv ecx; push rax` (`cdq`: `eax`'in işaretini `edx`'e genişletir; bölüm `eax`, kalan `edx`, kalan için `push rdx`). arm64: `sdiv w9, w9, w10`; kalan için `msub`. Sıfıra bölme x86-64'te `#DE` istisnası ve `SIGFPE`; arm64'te sonuç 0, hiçbir hata yok. Bir dil tanımı için davranış aynı olmalı: `ecx`/`w10` sıfır mı diye açık kontrol üret ve dilin hatasına (ya da belirlenmiş bir değere) git. JVM ve JS JIT'leri böyle yapıyor.

**3** – Son yazılan bayt `0x50` ve yeni bayt `0x58` ise `yaz--` yapmak (arada etiket yoksa güvenli). Bu ifadede böyle tek çift var, en sondaki; 39 bayt 37'ye iniyor. Çok daha sık görülen kalıp `push rax; pop rcx` ve `push rdi; pop rcx`: bunlar `mov ecx, eax` (`89 c1`) ve `mov ecx, edi` (`89 f9`) olarak yazılabilir; boyut aynı kalır ama iki bellek erişimi kaybolur. Asıl kazanç, sanal yığının ilk derinliklerini `eax`, `ecx`, `edx` gibi register'lara eşlemek: bu durumda bellek erişimi tamamen kaybolur; bu, Faz 16'daki register atamasının ilkel hali.

**4** – Çağırma kuralını yerine getir: arm64'te fonksiyon başında `stp x29, x30, [sp, #-16]!`, sonunda `ldp x29, x30, [sp], #16` (çünkü `blr`, `x30`'u bozuyor). x86-64'te `call`'dan önce `rsp` 16 bayta hizalı olmalı; JIT fonksiyonuna girildiğinde `rsp % 16 == 8` ve sanal yığın kaç eleman içeriyorsa ona göre `sub rsp, 8` eklemek gerekir. Ayrıca çağıran-korumalı register'lar (`rdi` gibi; `x` burada) çağrı öncesi saklanmalı.

**5** – RWX sayfa, taşma ile kodun üstüne yazıp doğrudan çalıştırma imkânı verir: en kolay istismar yolu. W^X bunu engeller. Ama saldırganın **hazır kodu** kullanmasını (ROP, Ders 7.14) ya da JIT'in kendisini istediği kodu üretmeye yönlendirmesini (JIT spraying) engellemez. Gerçek tarayıcılar buna sabitleri körleme (constant blinding), arm64'te PAC/BTI gibi önlemler ekliyor.

</details>

---

## Kaynaklar

- John Aycock, "A Brief History of Just-In-Time", *ACM Computing Surveys*, 2003: JIT'lerin tarihçesi.
- Mike Pall, LuaJIT ve DynASM belgeleri: tek geçişli kod üretimi için çalışma zamanı assembler'ı.
- Arm, *Arm Architecture Reference Manual for A-profile*: A64 komut kodlaması, `DC`/`IC` önbellek bakım komutları.
- Intel, *Intel 64 and IA-32 Architectures Software Developer's Manual*, Cilt 2: komut kodlaması; Cilt 3: sayfa tablosu NX biti.
- Thomas Würthinger ve ark., GraalVM / "Practical Partial Evaluation for High-Performance Dynamic Language Runtimes", *PLDI 2017*: JIT'lerin üst sınırı için bir örnek.
- `man 2 mprotect`, `man 2 memfd_create`.

**Sıradaki ders:** İş parçacıkları. `pthread_create`, `join`, paylaşılan bellek.
