---
title: "10.19 Hata ayıklama araçları derinlemesine"
description: "LLDB'yi otomatikleştirmek: koşullu kesme noktası, komut dosyası ve toplu çalışma; Python betiğiyle bağlı listeyi gezen özel 'liste' komutu; core dump almak, ulimit ve core_pattern, lldb -c ile ölmüş programı incelemek; valgrind memcheck ile aynı hatayı bulmak; valgrind --tool=callgrind ile komut sayarak profil, 1 490 000 çağrının tam sayımı ve arm64'te çağrı grafiği uyarısı; ptrace'in arka planı."
---

Fazlar boyunca LLDB'yi el ile kullandık: kesme noktası koy, adımla, değişkene bak. Bu ders hata ayıklamayı **otomatikleştiriyor** ve program çoktan öldükten sonra bile yapılabilir hale getiriyor. Bir derleyici yazarı kaçınılmaz olarak derleyicinin kendisini çökerten bir girdi ile ya da ürettiği hatalı kodla uğraşır; orada elle adımlamak yetmez.

Bütün bu araçların altında Ders 10.1'de `strace`'in üzerine kurulu olduğunu söylediğimiz **ptrace** var: bir süreç diğerini durdurup belleğini ve register'larını okuyabiliyor. Kesme noktası, hedef adresteki komutu tuzak komutuyla değiştirmek demek (x86-64'te `int3`, arm64'te `brk`); oraya gelince işlemci istisna üretiyor (Ders 7.28), çekirdek süreci durdurup hata ayıklayıcıya haber veriyor.

(Konteyner içinde `ptrace` izni gerekiyor: Docker'da `--cap-add=SYS_PTRACE --security-opt seccomp=unconfined`.)

---

## 1. Hedef

```c
/* Hata ayiklama hedefi: bagli liste ve tanimsiz davranis */
#include <stdio.h>
#include <stdlib.h>
typedef struct Dugum { int deger; struct Dugum *sonraki; } Dugum;
static Dugum *ekle(Dugum *b, int v) { Dugum *d = malloc(sizeof *d); d->deger = v; d->sonraki = b; return d; }
static int topla(const Dugum *b) { int s = 0; for (; b; b = b->sonraki) s += b->deger; return s; }
static Dugum *bozuk_sil(Dugum *b, int v) {
    if (b->deger == v) { Dugum *s = b->sonraki; free(b); return s; }
    Dugum *o = b;
    while (o->sonraki->deger != v) o = o->sonraki;      /* v yoksa NULL uzerinden okur */
    Dugum *s = o->sonraki; o->sonraki = s->sonraki; free(s);
    return b;
}
int main(int argc, char **argv) {
    Dugum *l = NULL;
    for (int i = 1; i <= 5; i++) l = ekle(l, i * i);
    printf("toplam %d\n", topla(l));
    l = bozuk_sil(l, 9);
    printf("9 silindi, toplam %d\n", topla(l));
    l = bozuk_sil(l, argc > 1 ? atoi(argv[1]) : 100);
    printf("toplam %d\n", topla(l));
    return 0;
}
```

```
$ cc -g -O0 liste.c -o liste && ./liste | cat
Segmentation fault
$ echo ${PIPESTATUS[0]}
139
```

(`139` = 128 + 11, Ders 10.6.) `printf` çıktıları görünmedi: stdout boruya gidiyordu ve tamponda bekleyen satırlar süreçle birlikte kayboldu (Ders 10.3).

---

## 2. LLDB'yi betiklemek

Kesme noktalarına **koşul** verilebilir ve komutlar bir dosyada toplanabilir. Bu, aynı hata ayıklama oturumunu tekrar tekrar çalıştırmak demek: `-b` toplu kipte `-s` dosyasını yürütüp çıkıyor.

```
# komutlar.lldb
command script import liste.py
breakpoint set -n bozuk_sil -c "v == 100"
run
frame variable v
liste b
continue
bt
frame select 0
frame variable o
register read pc
expression o->deger
quit
```

LLDB'nin Python arabirimi özel komutlar eklemeye izin veriyor. `liste b` komutu derleyicinin bilmediği bir şey: bağlı listeyi insan gibi gösteriyor.

```python
# LLDB betigi: bagli listeyi gezen komut.  Yukleme: command script import liste.py
import lldb

def liste_goster(debugger, komut, sonuc, ic):
    cerceve = debugger.GetSelectedTarget().GetProcess().GetSelectedThread().GetSelectedFrame()
    d = cerceve.EvaluateExpression(komut)
    if not d.IsValid() or d.GetError().Fail():
        print("hata:", d.GetError().GetCString(), file=sonuc)
        return
    n, parcalar = 0, []
    while d.GetValueAsUnsigned() != 0 and n < 100:
        deger = d.GetChildMemberWithName("deger").GetValueAsSigned()
        parcalar.append(str(deger))
        d = d.GetChildMemberWithName("sonraki")
        n += 1
    print(" -> ".join(parcalar) + f"  ({n} dugum)", file=sonuc)

def __lldb_init_module(debugger, ic):
    debugger.HandleCommand("command script add -f liste.liste_goster liste")
```

```
$ lldb -b -s komutlar.lldb -- ./liste
(lldb) breakpoint set -n bozuk_sil -c "v == 100"
Breakpoint 1: where = liste`bozuk_sil + 20 at liste.c:8:9, address = 0x0000000000000a18
(lldb) run
toplam 55
9 silindi, toplam 46
Process 58 stopped
* thread #1, name = 'liste', stop reason = breakpoint 1.1
    frame #0: 0x0000aaaaaaaa0a18 liste`bozuk_sil(b=0x0000aaaaaaac1320, v=100) at liste.c:8:9
(lldb) frame variable v
(int) v = 100
(lldb) liste b
25 -> 16 -> 4 -> 1  (4 dugum)
(lldb) continue
Process 58 stopped
* thread #1, name = 'liste', stop reason = signal SIGSEGV: address not mapped to object (fault address: 0x0)
    frame #0: 0x0000aaaaaaaa0a64 liste`bozuk_sil(b=0x0000aaaaaaac1320, v=100) at liste.c:10:24
-> 10  	    while (o->sonraki->deger != v) o = o->sonraki;      /* v yoksa NULL uzerinden okur */
    	                       ^
(lldb) bt
* thread #1, name = 'liste', stop reason = signal SIGSEGV: address not mapped to object (fault address: 0x0)
  * frame #0: 0x0000aaaaaaaa0a64 liste`bozuk_sil(b=0x0000aaaaaaac1320, v=100) at liste.c:10:24
    frame #1: 0x0000aaaaaaaa0940 liste`main(argc=1, argv=0x0000fffffffffd88) at liste.c:20:9
    ...
(lldb) frame variable o
(Dugum *) o = 0x0000aaaaaaac12a0
(lldb) register read pc
      pc = 0x0000aaaaaaaa0a64  liste`bozuk_sil + 96 at liste.c:10:24
(lldb) expression o->deger
(int) $1 = 1
```

Tek komutla hata tam olarak söylendi. Koşullu kesme noktası sayesinde `v == 9` çağrısı atlandı; `liste b` komutu 9'un gerçekten silindiğini gösterdi; `o->deger` = 1, listenin son düğümü: `o->sonraki` `NULL`, `NULL->deger` adres 0'ı okuyor, `fault address: 0x0`. Hatanın kaynağı `while` koşulu: `o->sonraki != NULL` kontrolü yok.

Kullanışlı diğer araçlar:

- **Gözlem noktası** (watchpoint): `watchpoint set variable x` "bu bellek değişince dur". Donanım kaydıyla (Ders 7.28) neredeyse maliyetsiz; bellek bozulması için en güçlü araç.
- `breakpoint command add 1`: kesme noktasında otomatik çalışan komutlar: yeniden derlemeden "log ekleme".
- `target stop-hook add`: her durmada çalışan komutlar.
- GDB eşdeğerleri: `break f if v == 100`, `python ...`, `watch x`. Kavramlar aynı.

---

## 3. Core dump: ölümün fotoğrafı

Bir program sahada, sen yokken çöktüğünde kesme noktası koyamazsın. **Core dump**, çekirdeğin çöküş anında sürecin belleğini ve register'larını bir dosyaya yazması. Üç koşul gerekiyor:

- Sinyalin varsayılan eylemi "bitir + core" olmalı (Ders 10.6'daki tablo).
- `ulimit -c unlimited`: boyut sınırı 0'dan farklı olmalı (varsayılan çoğunlukla 0).
- Dosya yolu `/proc/sys/kernel/core_pattern` ile belirleniyor. Dağıtımlarda çoğunlukla `apport` ya da `systemd-coredump`'a yönlendirilmiş.

```
$ ulimit -c unlimited
$ cat /proc/sys/kernel/core_pattern
core
$ echo /tmp/core.%e.%p | sudo tee /proc/sys/kernel/core_pattern
/tmp/core.%e.%p
$ ./liste
Segmentation fault (core dumped)
$ ls -l /tmp/core.*
-rw------- 1 root root 389120 Nov  8 16:33 /tmp/core.liste.68
```

`%e` program adı, `%p` PID. Dosya bir ELF (Ders 7.16, `readelf -l` ile bakabilirsin): Ders 10.2'deki seyrek dosya yöntemiyle yazılıyor. Okuması:

```
$ lldb -b -c /tmp/core.liste.68 ./liste -o bt -o "frame variable" -o "frame select 1" -o "frame variable l"
(lldb) bt
* thread #1, name = 'liste', stop reason = signal SIGSEGV: address not mapped to object
  * frame #0: 0x0000aaaac4d50a64 liste`bozuk_sil(b=0x0000aaaafa231320, v=100) at liste.c:10:24
    frame #1: 0x0000aaaac4d50940 liste`main(argc=1, argv=0x0000fffff24fc138) at liste.c:20:9
    ...
(lldb) frame variable
(Dugum *) b = 0x0000aaaafa231320
(int) v = 100
(Dugum *) o = 0x0000aaaafa2312a0
(Dugum *) s = 0x0000aaaafa2312e0
(lldb) frame select 1
frame #1: 0x0000aaaac4d50940 liste`main(argc=1, argv=0x0000fffff24fc138) at liste.c:20:9
-> 20  	    l = bozuk_sil(l, argc > 1 ? atoi(argv[1]) : 100);
(lldb) frame variable l
(Dugum *) l = 0x0000aaaafa231320
```

Program bitmiş olduğu halde aynı değişkenler, aynı yığın. ASLR yüzünden adresler önceki çalıştırmadan farklı (`0x0000aaaac4d50a64`), LLDB bunu hallediyor. Core dump'tan **adımlama yapamazsın**, sadece o anı inceleyebilirsin; ama derleyici yazan biri için müthiş bir araç: bir kullanıcı "derleyici çöktü" dediğinde core dosyası sorunu tek seferde gösterir. Büyük dağıtık sistemlerde (Google, Meta) core dump'lar merkezi olarak toplanıp otomatik sınıflandırılıyor.

`-g` ile derlemek sahadaki ikili dosyayı büyütür; sürümlenmiş bir derlemede hata ayıklama bilgisini ayrı dosyaya almak (`objcopy --only-keep-debug`) standart yöntem.

---

## 4. Valgrind

`valgrind`, programı komut komut bir sanal işlemcide **çalıştırıyor** ve her erişimi denetliyor. Ayrıca derlemeye gerek yok. Bedeli 10–50 kat yavaşlama.

### memcheck

```
$ valgrind -q ./liste
==88== Invalid read of size 4
==88==    at 0x108A64: bozuk_sil (liste.c:10)
==88==    by 0x10893F: main (liste.c:20)
==88==  Address 0x0 is not stack'd, malloc'd or (recently) free'd
==88==
==88== Process terminating with default action of signal 11 (SIGSEGV): dumping core
==88==  Access not within mapped region at address 0x0
==88==    at 0x108A64: bozuk_sil (liste.c:10)
==88==    by 0x10893F: main (liste.c:20)
```

`Address 0x0 is not stack'd, malloc'd or (recently) free'd`: tek cümlede tanı. Ders 4.23'teki hataları (sınır dışı erişim, kullanım-sonrası-serbest, ilklenmemiş değişken) yakalıyor. ASan (`-fsanitize=address`) çok daha hızlı ve yığın/global taşmalarını da buluyor; valgrind derleme gerektirmemesiyle ve ilklenmemiş bellek takibiyle öne çıkıyor. İkisini bir arada kullanmak: testlerde ASan, elinde kaynağı olmayan ikili dosyalarda valgrind.

### callgrind: komut sayan profil

`perf` zaman örnekliyor (Ders 10.18); `callgrind` ise **her komutu sayıyor**: tam, tekrarlanabilir sayılar veriyor (zaman değil komut sayısı).

```c
/* callgrind hedefi */
#include <stdio.h>
__attribute__((noinline)) static long kare(long x) { return x * x; }
__attribute__((noinline)) static long ic(long n) { long s = 0; for (long i = 0; i < n; i++) s += kare(i); return s; }
__attribute__((noinline)) static long dis(long n) { long s = 0; for (long i = 0; i < n; i++) s += ic(i % 100); return s; }
int main(void) { printf("%ld\n", dis(20000)); printf("%ld\n", ic(500000)); return 0; }
```

```
$ cc -g -O1 profil.c -o profil
$ valgrind --tool=callgrind --separate-recs=1 --callgrind-out-file=cg.out ./profil
==11== I   refs:      12,494,516
$ callgrind_annotate cg.out
12,494,516 (100.0%)  PROGRAM TOTALS
9,419,414 (75.39%)  profil.c:ic [/tmp/w/profil]
2,980,000 (23.85%)  profil.c:kare [/tmp/w/profil]
```

Kaynak satırına göre dökümü de var:

```
2,980,000 (23.85%)  __attribute__((noinline)) static long kare(long x) { return x * x; }
9,179,812 (73.47%)  __attribute__((noinline)) static long ic(long n) { long s = 0; for (long i = 0; i < n; i++) s += kare(i); return s; }
2,980,000 (23.85%)  => profil.c:kare (1,490,000x)
```

`kare`'nin **tam 1 490 000** kez çağrıldığını söylüyor. Kontrol edelim: `dis` 20 000 tur, her turda `i % 100` (ortalama 49.5) kez `kare`: $20\,000 \times 49.5 = 990\,000$; ardından `ic(500000)`: $500\,000$. Toplam $1\,490\,000$. Birebir. `kare` başına 2 komut ($2\,980\,000 / 1\,490\,000$): `mul` ve `ret`.

Sayılar **deterministik**: iki kez çalıştırınca aynı çıkıyor, bu yüzden "bu değişiklik kaç komut kazandırdı?" sorusunu gürültüsüz cevaplıyor. LLVM ve GCC geliştiricileri optimizasyonları tam da böyle karşılaştırıyor. Eksiği: komut sayısı süre değil; cache ıskasını (`--cache-sim=yes` ile modellenebilir) ve dal ıskasını doğrudan görmez.

:::caution[arm64'te çağrı grafiği]
Bu örnekte `--separate-recs=1` kullanmak zorunda kaldık. Valgrind 3.22 arm64'te bazı `bl`/`ret` dizilerini özyineleme sanıp `ic'2` gibi satırlar üretti ve **kapsayıcı** (inclusive) sayılar anlamsız çıktı (`%666524` gibi yüzdeler). Fonksiyonun kendi komut sayıları ve çağrı sayıları doğru (yukarıda elle doğruladık). x86-64'te bu sorunla genelde karşılaşılmıyor; kapsayıcı sayılara dayanacaksan sonucu bu şekilde bir kez elle doğrula.
:::

---

## Alıştırmalar

**1** – `liste.c`'deki hatayı düzelt: `v` listede yoksa bir şey yapma. Düzelttiğini `valgrind -q` ile doğrula. Listeyi hiç silmediğin için `--leak-check=full` ne der?

**2** – Bir `int a[10]` ve döngüde bir taşma olan program yaz. LLDB ile `a[10]`'un adresine **watchpoint** kur ve onu kimin bozduğunu bul.

**3** – LLDB betiğine `liste_say` komutunu ekle: listeyi gezip **döngü** varsa (Floyd'un tavşan-kaplumbağa algoritması, Ders 8.2) "döngü var" desin.

**4** – `core_pattern`'e `|/usr/local/bin/toplayici %e %p` yazılırsa ne olur? Core dosyası nereye gider? Bu mekanizmayı `systemd-coredump` nasıl kullanıyor?

**5** – Ders 9.5'teki hızlı sıralama ile Ders 9.4'teki birleştirmeli sıralamayı `callgrind` ile karşılaştır. Komut sayısı kazanan, gerçek sürede de kazanır mı? Neden olmayabilir?

<details>
<summary>Cevaplar</summary>

**1** – `while (o->sonraki && o->sonraki->deger != v)`, sonra `if (!o->sonraki) return b;`. `valgrind -q` çıktısı boş olmalı. `--leak-check=full`, programın bitişinde serbest bırakılmamış 4 düğümü `definitely lost`/`still reachable` olarak raporlar: `l` hâlâ bir global ya da yığın üzerinden ulaşılabiliyorsa "still reachable". İşlevin sonuna `while (l) { ... free }` eklemek temizler.

**2** – `watchpoint set expression -- &a[10]` (ya da `watchpoint set variable a[10]`). Çalıştır, durunca `bt` ve `frame variable i` ile yazan satırı gör. Donanım watchpoint'lerinin sınırlı sayıda olduğunu unutma (genellikle 4 adet).

**3** – İki SBValue işaretçisi: `yavas` her adımda bir, `hizli` iki `sonraki` ilerler; karşılaştırmada `GetValueAsUnsigned()` kullan; biri 0'a düşerse "döngü yok", ikisi eşitlenirse "döngü var".

**4** – `|` ile başlarsa çekirdek bir programı çalıştırıp core verisini onun stdin'ine boruyla yazar (Ders 10.5). `systemd-coredump` tam olarak bu yolla çağrılıp core dosyalarını sıkıştırıyor ve `/var/lib/systemd/coredump`'a koyuyor; `coredumpctl` ile incelenir. Bu program çekirdek tarafından root yetkisiyle çalıştırılıyor.

**5** – Komut sayısı kazananın gerçek sürede de kazanması gerekmez. Birleştirmeli sıralama daha az karşılaştırma yapabilir ama ek bellek ve daha çok önbellek ıskası nedeniyle daha yavaş olabilir; hızlı sıralama ise yerinde çalışır ve önbellek dostudur (Ders 9.5). Komut sayısı IPC'yi (çevrim başına komut) ve bellek hiyerarşisini görmez.

</details>

---

## Kaynaklar

- LLDB proje belgeleri: "Python Reference" ve "Scripting" (lldb.llvm.org).
- Valgrind kullanıcı kılavuzu: Memcheck ve Callgrind bölümleri (valgrind.org).
- Julian Seward ve Nicholas Nethercote, "Valgrind: A Framework for Heavyweight Dynamic Binary Instrumentation", *PLDI 2007*.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 22: core dump dosyaları.
- `man 5 core`, `man 2 ptrace`, `man 1 valgrind`.

**Sıradaki ders:** Faz projesi. Pipe ve yönlendirme destekli mini shell + kendi tamponlu G/Ç kütüphanemiz.
