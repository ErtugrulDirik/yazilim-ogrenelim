---
title: "8.6 Özyineleme ve yığın ilişkisi"
description: "Her özyinelemeli çağrının çağrı yığınına bir çerçeve koyduğunu adreslerle görmek (Apple M2'de çerçeve başına 80 bayt), 8 MB yığının 174 bin derinlikte bitmesi ve ASan'ın stack-overflow raporu; özyinelemeli fonksiyonu açık yığınla döngüye çevirmenin genel tarifi (parametreler + dönüş noktası = çerçeve), Hanoi kuleleri ve büyük bir alanda çöken flood fill'in açık yığınlı sürümü; kuyruk çağrısı, clang'in -O2'de özyinelemeyi döngüye hatta kapalı formüle çevirmesi ve buna neden güvenilmemesi gerektiği."
---

Ders 2.8'de özyinelemeyi bir fonksiyonun kendini çağırması olarak tanıttık. Ders 7.11'de her çağrının yığında bir **çerçeve** açtığını assembly düzeyinde gördük: dönüş adresi, kaydedilen register'lar, yerel değişkenler. Ders 8.4'te de kendi yığınımızı yazdık. Bu ders bu üçünü birleştiriyor: özyineleme, aslında derleyicinin senin yerine yönettiği bir yığın. Bu yığının sınırını görecek, sonra aynı işi kendi yığınımızla yapacağız. Ağaçlar (8.7–8.11) ve graf aramaları (Faz 9) baştan sona özyinelemeli, bu yüzden bu dönüşümü bilmek o derslerde iş görecek.

---

## 1. Çağrı yığınını gözle görmek

Her çağrıda yerel bir değişkenin adresini yazdıralım:

```c
/* Her ozyineleme cagrisi yigina yeni bir cerceve koyar: yerel degiskenin adresine bakalim */
#include <stdio.h>
#include <stdint.h>

static char *onceki;

static long topla(long n) {
    char yerel;                                   /* bu cercevede bir bayt */
    if (onceki) printf("  n=%ld  &yerel=%p  fark=%td bayt\n", n, (void *)&yerel, onceki - &yerel);
    else        printf("  n=%ld  &yerel=%p\n", n, (void *)&yerel);
    onceki = &yerel;
    if (n == 0) return 0;
    return n + topla(n - 1);
}

int main(void) {
    printf("topla(4) = %ld\n", topla(4));
    return 0;
}
```

```
$ cc -std=c11 -O0 -Wall derinlik.c -o derinlik && ./derinlik
  n=4  &yerel=0x16f2020ef
  n=3  &yerel=0x16f20209f  fark=80 bayt
  n=2  &yerel=0x16f20204f  fark=80 bayt
  n=1  &yerel=0x16f201fff  fark=80 bayt
  n=0  &yerel=0x16f201faf  fark=80 bayt
topla(4) = 10
```

Her çağrıda adres 80 bayt **azalıyor**: yığın aşağı doğru büyüyor (Ders 4.21) ve her `topla` çağrısı 80 baytlık bir çerçeve kaplıyor. Beş çağrı aynı anda yaşıyor: `topla(0)` dönmeden `topla(1)`'in toplaması yapılamaz, çünkü `n + topla(n - 1)` ifadesindeki `n` hâlâ gerekli. Her çerçevede saklanan şey tam da bu: **dönünce işin geri kalanını yapmak için gereken bilgi.**

```
yüksek adres
  ┌──────────────┐
  │ main         │
  ├──────────────┤
  │ topla(4)  n=4│  dönünce: 4 + sonuç
  ├──────────────┤
  │ topla(3)  n=3│  dönünce: 3 + sonuç
  ├──────────────┤
  │ ...          │
  ├──────────────┤
  │ topla(0)     │  ← sp
  └──────────────┘
düşük adres
```

---

## 2. Yığın biter

Bu yığının boyutu sabit ve küçük. macOS ve çoğu Linux dağıtımında ana iş parçacığı için varsayılan 8 MB:

```
$ ulimit -s
8176
```

(Kilobayt cinsinden; macOS 8 MB'den biraz azını gösteriyor.) Basit bir özyinelemeli toplam ne kadar derine inebilir?

```c
/* Ozyineleme ne kadar derine inebilir? */
#include <stdio.h>
#include <stdlib.h>

static long topla(long n) {
    if (n == 0) return 0;
    return n + topla(n - 1);
}

int main(int argc, char **argv) {
    long n = argc > 1 ? atol(argv[1]) : 1000;
    printf("topla(%ld) = %ld\n", n, topla(n));
    return 0;
}
```

```
$ cc -std=c11 -O0 tasma.c -o tasma0
$ ./tasma0 100000; echo "cikis kodu $?"
topla(100000) = 5000050000
cikis kodu 0
$ ./tasma0 200000; echo "cikis kodu $?"
cikis kodu 139
```

Çıkış kodu 139 = 128 + 11, yani SIGSEGV (Ders 7.28). İkili aramayla sınırı bulunca yaklaşık **174 200** çıkıyor. 8 MB / 174 200 ≈ 48 bayt: bu sürümde yerel `char` ve `printf` olmadığı için çerçeve 80 değil 48 bayt. Çökme yeri yığının sonundaki **koruma sayfası** (guard page): işletim sistemi yığının altına erişime kapalı bir sayfa koyuyor, ona dokunan program sayfa hatasıyla ölüyor (Ders 7.27).

ASan bunu adıyla söylüyor:

```
$ cc -std=c11 -O0 -g -fsanitize=address tasma.c -o tasma_asan && ./tasma_asan 1000000
AddressSanitizer:DEADLYSIGNAL
=================================================================
==18476==ERROR: AddressSanitizer: stack-overflow on address 0x00016f5a3ff0 (pc 0x0001000608b4 bp 0x00016f5a4020 sp 0x00016f5a3fd0 T0)
    #0 0x0001000608b4 in topla tasma.c:5
    #1 0x0001000608e4 in topla tasma.c:7
    #2 0x0001000608e4 in topla tasma.c:7
    ...
```

174 bin az bir sayı değil, ama girdinin boyutuna bağlı bir özyineleme derinliği her zaman bir risk. 1 milyon düğümlü bir listeyi özyinelemeyle gezmek, dengesiz bir ağaçta (Ders 8.8) yükseklik kadar inmek, ya da bir resimde büyük bir alanı boyamak bu sınırı kolayca aşar. Ve hata bir istisna değil, programın ölümü: C'de yığın taşmasından kurtulmanın taşınabilir bir yolu yok.

---

## 3. Genel tarif: çerçeveyi kendin tut

Derleyicinin çağrı yığınına koyduğu şeyin aynısını kendi dizimize (ya da Ders 8.4'teki yığına) koyarsak özyinelemeye gerek kalmaz. Bir çerçevede iki şey var:

1. **Parametreler ve yerel değişkenler**: o çağrının durumu.
2. **Dönüş adresi**: çağrı bitince fonksiyonun **hangi noktadan** devam edeceği.

İkincisi kritik. Bir fonksiyon kendini birden fazla yerden çağırıyorsa, her dönüşte farklı bir yerden devam eder. Bunu bir tamsayıyla, bir "adım" alanıyla kodlarız ve döngünün içinde `switch` ile o noktaya atlarız. Bu, işlemcinin dönüş adresiyle yaptığı şeyin elle yapılmış hali.

### Örnek: Hanoi kuleleri

$n$ diski A'dan C'ye taşımak için: üstteki $n-1$ diski B'ye taşı, en büyüğünü C'ye koy, $n-1$ diski B'den C'ye taşı. İki özyinelemeli çağrı, yani iki dönüş noktası:

```c
/* Hanoi kuleleri: ozyinelemeli ve acik yiginla ayni cikti */
#include <stdio.h>
#include <string.h>

static void hanoi(int n, char a, char b, char c) {   /* n diski a'dan c'ye, b yardimci */
    if (n == 0) return;
    hanoi(n - 1, a, c, b);                            /* donus noktasi 1 */
    printf("  %d: %c -> %c\n", n, a, c);
    hanoi(n - 1, b, a, c);                            /* donus noktasi 2 */
}

/* Cerceve: parametreler + "kaldigim yer". Derleyicinin yigina koydugu sey bunun aynisi. */
typedef struct { int n; char a, b, c; int adim; } Cerceve;

static void hanoi_yigin(int n, char a, char b, char c) {
    Cerceve yigin[64];
    int tepe = 0;
    yigin[tepe++] = (Cerceve){ n, a, b, c, 0 };
    while (tepe > 0) {
        Cerceve *f = &yigin[tepe - 1];
        if (f->n == 0) { tepe--; continue; }          /* return */
        switch (f->adim++) {
        case 0:                                        /* ilk cagri */
            yigin[tepe++] = (Cerceve){ f->n - 1, f->a, f->c, f->b, 0 };
            break;
        case 1:                                        /* donus noktasi 1 */
            printf("  %d: %c -> %c\n", f->n, f->a, f->c);
            yigin[tepe++] = (Cerceve){ f->n - 1, f->b, f->a, f->c, 0 };
            break;
        default:                                       /* donus noktasi 2: bitti */
            tepe--;
        }
    }
}

int main(void) {
    printf("ozyinelemeli:\n"); hanoi(3, 'A', 'B', 'C');
    printf("acik yigin:\n");   hanoi_yigin(3, 'A', 'B', 'C');
    return 0;
}
```

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined hanoi.c -o hanoi && ./hanoi
ozyinelemeli:
  1: A -> C
  2: A -> B
  1: C -> B
  3: A -> C
  1: B -> A
  2: B -> C
  1: A -> C
acik yigin:
  1: A -> C
  2: A -> B
  1: C -> B
  3: A -> C
  1: B -> A
  2: B -> C
  1: A -> C
```

Satır satır aynı. Döngünün her turu yığının tepesindeki çerçeveye bakıyor ve onun `adim`'ına göre davranıyor:

| Özyinelemeli kod | Açık yığın |
| --- | --- |
| Fonksiyon çağrısı | Yeni çerçeveyi it, `adim = 0` |
| `return` | Çerçeveyi çek |
| Çağrıdan sonraki satıra dönmek | Üstteki çerçeve çekilince alttakinin `adim`'ı sıradaki noktayı gösteriyor |
| Yerel değişkenler | Çerçeve struct'ının alanları |

Bir ince nokta: `f` pointer'ı, `yigin[tepe++] = ...` yazıldıktan sonra kullanılmıyor. Dizi yerine büyüyen bir yığın (`realloc`) kullanılsaydı yeni çerçeveyi itmek eski çerçevenin adresini geçersiz kılabilirdi (Ders 4.24'teki tuzak).

### Daha kolayı: dönüşten sonra iş yoksa

Hanoi'de çağrılar arasında iş var (`printf`), bu yüzden dönüş noktası gerekti. Çoğu gezinme algoritmasında çağrıdan sonra yapılacak bir şey yok: "bu hücreyi işle, komşuları ziyaret et" o kadar. O zaman çerçeveye dönüş noktası koymaya gerek yok; ziyaret edilecek şeyleri yığına itmek yetiyor.

**Flood fill** (resim programlarındaki boya kovası): bir hücreden başla, aynı renkteki bütün komşulara yayıl.

```c
/* Flood fill: ozyinelemeli ve acik yiginla. Buyuk bir alanda ozyinelemeli surum cokuyor. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int G, Y;              /* genislik, yukseklik */
static char *izgara;          /* '.' bos, '#' duvar, 'o' boyandi */
#define H(s, g) izgara[(long)(s) * G + (g)]

static long boya_ozy(int s, int g) {
    if (s < 0 || s >= Y || g < 0 || g >= G || H(s, g) != '.') return 0;
    H(s, g) = 'o';
    return 1 + boya_ozy(s - 1, g) + boya_ozy(s + 1, g) + boya_ozy(s, g - 1) + boya_ozy(s, g + 1);
}

static long boya_yigin(int s0, int g0) {
    long kap = 1024, tepe = 0, sayi = 0;
    long *yigin = malloc(kap * sizeof *yigin);
    yigin[tepe++] = (long)s0 * G + g0;
    while (tepe > 0) {
        long k = yigin[--tepe];
        int s = (int)(k / G), g = (int)(k % G);
        if (s < 0 || s >= Y || g < 0 || g >= G || H(s, g) != '.') continue;
        H(s, g) = 'o';
        sayi++;
        if (tepe + 4 > kap) { kap *= 2; yigin = realloc(yigin, kap * sizeof *yigin); }
        long kom[4][2] = { { s - 1, g }, { s + 1, g }, { s, g - 1 }, { s, g + 1 } };
        for (int i = 0; i < 4; i++)                     /* sinir disi komsuyu hic itme */
            if (kom[i][0] >= 0 && kom[i][0] < Y && kom[i][1] >= 0 && kom[i][1] < G)
                yigin[tepe++] = kom[i][0] * G + kom[i][1];
    }
    free(yigin);
    return sayi;
}

int main(int argc, char **argv) {
    G = Y = argc > 2 ? atoi(argv[2]) : 8;
    izgara = malloc((long)G * Y);
    memset(izgara, '.', (long)G * Y);
    for (int s = 0; s < Y - 1; s++) H(s, G / 2) = '#';   /* ortada bir duvar, altta bosluk */
    long n = argv[1][0] == 'o' ? boya_ozy(0, 0) : boya_yigin(0, 0);
    printf("%s %dx%d: %ld hucre boyandi\n", argv[1][0] == 'o' ? "ozyinelemeli" : "acik yigin", G, Y, n);
    if (G <= 8) for (int s = 0; s < Y; s++) printf("  %.*s\n", G, &H(s, 0));
    free(izgara);
    return 0;
}
```

(Sınır dışı komşuları itmemek gerekiyor: `(-1) * G + g` gibi bir kod geri açılırken başka bir geçerli hücreye denk gelebilir. Özyinelemeli sürümde bu sorun yok, çünkü `s` ve `g` ayrı parametreler.)

```
$ cc -std=c11 -O2 -Wall -Wextra boya.c -o boya
$ ./boya o 8
ozyinelemeli 8x8: 57 hucre boyandi
  oooo#ooo
  oooo#ooo
  oooo#ooo
  oooo#ooo
  oooo#ooo
  oooo#ooo
  oooo#ooo
  oooooooo
$ ./boya y 8 | head -1
acik yigin 8x8: 57 hucre boyandi
$ ./boya o 250
ozyinelemeli 250x250: 62251 hucre boyandi
$ ./boya o 300; echo "cikis $?"
cikis 139
$ ./boya y 2000
acik yigin 2000x2000: 3998001 hucre boyandi
```

Özyinelemeli sürüm 300 × 300'lük bir alanda (90 bin hücre) çöküyor: boyama "hep yukarı, sonra hep aşağı" diye yılan gibi kıvrılan tek bir yol çiziyor ve derinlik neredeyse hücre sayısı kadar oluyor. Açık yığınlı sürüm 4 milyon hücreyi sorunsuz boyuyor, çünkü yığını `malloc`'tan (heap) geliyor ve gerektiğinde büyüyor. Heap'in sınırı megabaytlar değil, gigabaytlar.

Açık yığın bir de **ziyaret sırasını** değiştiriyor: komşular ters sırada çıkıyor (en son itilen ilk). Boyamada sıra önemli değil, ama Hanoi'de olsaydı çıktı bozulurdu. Sıra önemliyse komşuları **ters sırada** itmek gerekir.

Yığını kuyrukla değiştirirsen aynı kod Ders 8.5'teki BFS'e dönüşür. Gezinme algoritmalarının hepsi aynı iskelet: "bekleyenler kümesinden birini al, işle, komşularını ekle". Bekleyenleri hangi yapıda tuttuğun, algoritmanın kimliğini belirliyor (Faz 9'da bunun üçüncü hali olarak öncelik kuyruğunu, yani Dijkstra'yı göreceğiz).

---

## 4. Kuyruk çağrısı ve derleyici

Bir çağrı fonksiyonun **son işi** ise (dönüşten sonra yapılacak bir şey yoksa) ona **kuyruk çağrısı** (tail call) denir. O durumda çağıranın çerçevesine dönüşte ihtiyaç yok; derleyici yeni çerçeve açmak yerine eskisini yeniden kullanıp `bl` (call) yerine `b` (jump) yapabilir. Özyineleme döngüye dönüşür.

```c
typedef struct Dugum { int deger; struct Dugum *sonraki; } Dugum;
long uzunluk(const Dugum *d) { return d ? 1 + uzunluk(d->sonraki) : 0; }
long uzunluk_k(const Dugum *d, long biriken) { return d ? uzunluk_k(d->sonraki, biriken + 1) : biriken; }
```

`uzunluk`'ta özyinelemeli çağrı son iş değil (dönünce `1 +` yapılacak); `uzunluk_k`'da son iş. Sonucu biriktiren bir parametre ekleyerek fonksiyonu kuyruk özyinelemeli hale getirdik. clang `-O2` ne üretiyor?

```
$ cc -std=c11 -O2 -S kuyruk.c -o -
_uzunluk:
	mov	x8, #0
	cbz	x0, LBB0_2
LBB0_1:
	ldr	x0, [x0, #8]
	add	x8, x8, #1
	cbnz	x0, LBB0_1
LBB0_2:
	mov	x0, x8
	ret
_uzunluk_k:
	cbz	x0, LBB1_2
LBB1_1:
	ldr	x0, [x0, #8]
	add	x1, x1, #1
	cbnz	x0, LBB1_1
LBB1_2:
	mov	x0, x1
	ret
```

İkisi de **döngü**, `bl` yok. `uzunluk_k`'da beklendiği gibi; ama clang `uzunluk`'u da dönüştürdü: `1 + ...` toplamanın birleşmeli olduğunu bilip biriktiriciyi kendisi ekledi. Daha da ileri gidebiliyor. Bölüm 2'deki `tasma.c` `-O2` ile:

```
$ cc -std=c11 -O2 tasma.c -o tasma2 && ./tasma2 100000000
topla(100000000) = 5000000050000000
```

100 milyon derinlik, çökmüyor. Assembly'de ne döngü ne çağrı var; `madd`, `umulh`, `extr`: clang $\sum_{i=1}^{n} i$ özyinelemesini tanıyıp $n(n+1)/2$ kapalı formülüne çevirmiş (Ders 6.10). Ölçüm yaparken buna dikkat (Ders 7.15).

Ama buna **güvenme**:

- C standardı kuyruk çağrısı eleme **garantisi vermez**. `-O0`'da hiçbiri olmaz; hata ayıklama derlemen çöker, sürüm derlemen çalışır. En kötü hata türü.
- Dönüşüm kırılgan: fonksiyonda bir yerel değişkenin adresini alırsan (`&yerel`), bir `free` ya da bir `printf` eklersen, ya da iki ayrı özyinelemeli çağrı olursa (Hanoi, flood fill, ağaç gezinmesi) derleyici çerçeveyi atamaz.
- clang, `__attribute__((musttail))` ile bir `return` ifadesinin kuyruk çağrısı olarak derlenmesini **zorunlu** kılabiliyor (olamıyorsa derleme hatası). Taşınabilir değil, ama "güvenmek" yerine "istemek" için var.

Scheme gibi bazı diller kuyruk çağrısı elemeyi dil kuralı yapar; orada döngü yazmak yerine kuyruk özyinelemesi yazılır. C'de kural tersi: **derinliği girdiye bağlı olan özyinelemeyi açık yığına çevir**, derinliği $O(\log n)$ ile sınırlı olanı (dengeli ağaçlar, Ders 8.9; birleştirmeli sıralama, Ders 9.4) rahatça özyinelemeli yaz. $\log_2(10^9) \approx 30$ çerçeve kimseyi korkutmaz.

---

## 5. Hangisi ne zaman

| | Özyineleme | Açık yığın |
| --- | --- | --- |
| Okunabilirlik | Çoğu zaman çok daha iyi; tanımı doğrudan yansıtır | Durum makinesi; özellikle çok dönüş noktası varsa zor okunur |
| Derinlik sınırı | Çağrı yığını (8 MB) | Heap (gigabaytlar) |
| Taşma | Programın ölümü | `malloc` hatası; yakalanabilir |
| Çerçeve boyutu | Derleyici belirler (kaydedilen register'lar dahil) | Sadece gereken alanlar |
| Hız | Çağrı + dönüş + register kaydetme | Dizi erişimi; genelde biraz daha hızlı |
| Durdurup devam ettirme | Yok | Yığın bir veri; saklanabilir, kopyalanabilir |

Son satır göründüğünden önemli: açık yığın bir veri yapısı olduğu için gezinmeyi yarıda bırakıp sonra devam ettirebilirsin. Ağaç **yineleyicileri** (iterator, "bir sonraki elemanı ver") tam bunu yapar (Ders 8.7, Alıştırma). Python'un üreteçleri ve Faz 10'daki eşyordamlar (coroutine) bu fikri dile taşıyor.

---

## Alıştırmalar

**1** – Fibonacci'nin saf özyinelemeli tanımı `fib(n) = fib(n-1) + fib(n-2)`. Bir sayaçla `fib(10)`, `fib(20)`, `fib(30)` için toplam çağrı sayısını ve aynı anda yaşayan en fazla çerçeve sayısını (en büyük derinlik) ölç. Çağrı sayısı neden bu kadar büyük ama derinlik neden küçük?

**2** – Hanoi'nin açık yığınlı sürümüne en büyük `tepe` değerini ölçen bir sayaç ekle. $n = 3$ ve $n = 20$ için ne çıkıyor? `Cerceve yigin[64]` hangi $n$'e kadar yeter?

**3** – İkili aramayı (Ders 4.2) özyinelemeli yaz: `ara(a, lo, hi, x)`. Bu bir kuyruk özyinelemesi mi? Elle döngüye çevir. Açık yığına neden gerek yok?

**4** – `boya_yigin`'deki yığının en fazla kaç eleman tuttuğunu 2000 × 2000 için tahmin et, sonra ölç. Komşuları yığına **itmeden önce** kontrol eden (boyanmışsa ya da duvarsa hiç itmeyen) bir sürüm bu sayıyı nasıl değiştirir?

**5** – Bir fonksiyon `-O2`'de çalışıp `-O0`'da yığın taşmasıyla çöküyor. Bu bir derleyici hatası mı? Ne yapmalısın?

<details>
<summary>Cevaplar</summary>

**1** –

```c
static long cagri, derin, en_derin;
static long fib(int n) { cagri++; if (++derin > en_derin) en_derin = derin;
  long r = n < 2 ? n : fib(n - 1) + fib(n - 2); derin--; return r; }
```

```
fib(10)=55  cagri=177  en derin=10
fib(20)=6765  cagri=21891  en derin=20
fib(30)=832040  cagri=2692537  en derin=30
```

Çağrı sayısı $C(n) = 1 + C(n-1) + C(n-2)$, $C(0) = C(1) = 1$; çözümü $C(n) = 2F_{n+1} - 1$ (Ders 6.11): $2 \cdot 1\,346\,269 - 1 = 2\,692\,537$. Üstel büyüyor ($\varphi^n$), çünkü aynı alt problemler defalarca çözülüyor (`fib(28)` iki kez, `fib(27)` üç kez...). Ama derinlik sadece $n$: herhangi bir anda yığında sadece kökten şu anki çağrıya giden **yol** var, bütün ağaç değil. Özyineleme ağacının **boyutu** zamanı, **yüksekliği** belleği belirliyor. Zaman sorunu yığınla değil, memoization ile çözülür (Ders 9.11).

**2** – `if (tepe > en_tepe) en_tepe = tepe;` her itmeden sonra: $n = 3$ için 4, $n = 20$ için 21. Genel olarak $n + 1$: her seviye için bir çerçeve, artı `n = 0` çerçevesi. 64'lük dizi $n = 63$'e kadar yeter; o noktada hamle sayısı $2^{63} - 1$ olduğu için zaten bitmeyecek. Derinliği $O(n)$, zamanı $O(2^n)$ olan bir algoritmada yığın asla sorun değil.

**3** –

```c
static long ara(const int *a, long lo, long hi, int x) {      /* [lo, hi) */
    if (lo >= hi) return -1;
    long orta = lo + (hi - lo) / 2;
    if (a[orta] == x) return orta;
    return a[orta] < x ? ara(a, orta + 1, hi, x) : ara(a, lo, orta, x);
}
```

Her iki özyinelemeli çağrı da `return`'ün doğrudan değeri: kuyruk özyinelemesi. Döngüye çevirmek için parametreleri güncelleyip başa dönmek yeter: `while (lo < hi) { ...; if (a[orta] < x) lo = orta + 1; else hi = orta; }`. Açık yığın gerekmiyor çünkü dönüşte yapılacak iş yok: bir sonraki çağrı başlayınca öncekinin durumu bir daha hiç okunmuyor, üzerine yazılabilir. Kuyruk çağrısı eleme, derleyicinin bu gözlemi otomatik yapması. (Derinlik zaten $\log_2 n$; özyinelemeli hali de güvenli.)

**4** – Her boyanan hücre 4 komşuya kadar itiyor ama sadece bir eleman çekiyor; boyanmış komşular da itiliyor, sonra çekilince atlanıyor. Yani yığın hücre sayısından **büyük** olabilir. Her itmeden sonra `if (tepe > en) en = tepe;` ile ölçüm (2000 × 2000, 3 998 001 hücre):

| Sürüm | En büyük yığın |
| --- | --- |
| Bölümdeki: her komşuyu it | 9 981 012 |
| Sadece boş (`'.'`) komşuları it | 3 992 005 |
| İtme anında işaretle (`H(...) = 'o'` itmeden önce) | 1 996 002 |

İlk sürüm hücre sayısının 2.5 katı eleman tutuyor (80 MB). Önce kontrol etmek bunu 2.5 kat azaltıyor ama bir hücre, henüz çekilip boyanmadan farklı komşular tarafından birkaç kez itilebiliyor. Üçüncü sürümde her hücre yığına **en fazla bir kez** giriyor: BFS'te `uzaklik`'ı ilk görüldüğü anda doldurduğumuz gibi (Ders 8.5). Yığın yine yarım milyon değil iki milyon, çünkü açık bir alanda derinlik öncelikli gezinme yılan gibi kıvrılıp her satırın yarısını bekleyen olarak bırakıyor; ama artık hücre sayısıyla sınırlı.

**5** – Derleyici hatası değil. Programın davranışı yığın boyutuna bağlı, ve C standardı ne yığın boyutundan ne kuyruk çağrısı elemeden bahseder; iki derleme de standarda uygun. `-O2` derlemesi sadece şanslı. Yapılacak şey, derinliği girdiye bağlı olan özyinelemeyi açık yığına (ya da kuyruk özyinelemesiyse elle döngüye) çevirmek. `ulimit -s` ile yığını büyütmek ya da `-O2`'ye güvenmek sorunu sadece ertelemek.

</details>

---

## Kaynaklar

- Harold Abelson ve Gerald Sussman, *Structure and Interpretation of Computer Programs* (2. baskı), Bölüm 1.2.1: doğrusal özyineleme ve yineleme; kuyruk özyinelemeli süreçler.
- Robert Sedgewick, *Algorithms in C* (3. baskı), Bölüm 5.1 ve 5.8: özyineleme, özyinelemenin açık yığınla kaldırılması.
- Donald Knuth, "Structured Programming with go to Statements", *Computing Surveys* 6(4), 1974: özyinelemenin sistematik kaldırılması örnekleri.
- Clang belgeleri, "Attributes in Clang": `musttail`.

**Sıradaki ders:** İkili ağaç. Gezinmeler (pre/in/post/level order), ifade ağacı ve AST'ye ilk bakış.
