---
title: "2.14 Uyarılar ve undefined behavior"
description: "Compiler uyarılarını okumak ve -Werror ile hataya çevirmek; undefined behavior nedir, neden 'her şey olabilir' demektir; UndefinedBehaviorSanitizer ve AddressSanitizer ile görünmeyen hataları yakalamak."
---

Bu fazda birkaç kez aynı cümleyle karşılaştık: "sonuç belirsizdir." 13!'in overflow olması (Ders 2.8), asal testindeki `d * d` (Ders 2.10), `INT_MIN`'in negatifi (Ders 2.11), array'in dışına taşmak (Ders 2.4), değer verilmemiş bir değişkeni okumak (Ders 2.3)… Bu derste bu durumların adını koyacağız: **undefined behavior** (tanımsız davranış). C'nin en tehlikeli kavramı.

Ama önce, compiler'ın bizi bu tür hatalara karşı nasıl uyardığına bakalım.

---

## 1. Uyarılar

Compiler iki tür mesaj verir:

- **Hata** (error): Kod C'nin kurallarına uymuyor; program **üretilemez**. Noktalı virgülü unutmak gibi.
- **Uyarı** (warning): Kod kurallara uyuyor, program üretilebilir; ama compiler "bu muhtemelen senin istediğin şey değil" diyor.

Uyarılar, compiler'ın senin yerine yaptığı bir kod incelemesidir. Dört klasik hata içeren şu programa bak:

```c
#include <stdio.h>

int sign(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    }
}

int main(void) {
    int unused = 5;
    int total;
    int n = 3;
    if (n = 5) {
        printf("beş\n");
    }
    for (int i = 0; i < n; i++) {
        total += i;
    }
    printf("%d %d\n", total, sign(0));
    return 0;
}
```

`-Wall -Wextra` ile derleyelim (Ders 2.2'de `tasks.json`'a koyduğumuz ayarlar):

```
warn.c:9:1: warning: non-void function does not return a value in all control paths [-Wreturn-type]
warn.c:15:11: warning: using the result of an assignment as a condition without parentheses [-Wparentheses]
warn.c:12:9: warning: unused variable 'unused' [-Wunused-variable]
warn.c:19:9: warning: variable 'total' is uninitialized when used here [-Wuninitialized]
4 warnings generated.
```

Her biri gerçek bir hata:

| Uyarı | Ne diyor? | Hata ne? |
| --- | --- | --- |
| `-Wreturn-type` | "`int` döndüren fonksiyon her yolda bir değer döndürmüyor." | `sign(0)` için hiçbir `return` çalışmıyor; dönen değer belirsiz. |
| `-Wparentheses` | "Koşul olarak bir atamanın sonucunu kullanıyorsun." | `n == 5` yazmak isterken `n = 5` yazılmış: `n` 5 oldu ve koşul hep doğru (Ders 2.3). |
| `-Wunused-variable` | "`unused` hiç kullanılmamış." | Zararsız görünür, ama çoğu zaman bir şeyin unutulduğunu gösterir. |
| `-Wuninitialized` | "`total` değer verilmeden kullanılıyor." | `total`'ın başlangıç değeri belirsiz; toplam da belirsiz. |

Dördü de program **derlendiği** halde ortaya çıktı. Uyarıları okumasaydın, bu programın neden tuhaf sonuçlar verdiğini saatlerce arayabilirdin.

**Kural:** Uyarıyla derlenen kodu bitmiş sayma. Her uyarı ya düzeltilir ya da neden zararsız olduğu açıkça bilinir.

### -Werror

Uyarılar bir süre sonra görmezden gelinmeye başlar. Ekran uyarıyla dolu bir projede yeni bir uyarı fark edilmez. Bunu önlemenin yolu, uyarıları **hataya** çevirmek:

```sh
clang -std=c17 -Wall -Wextra -Werror warn.c -o warn
```

`-Werror` ile aynı dört mesaj artık `error:` diye başlıyor ve program **üretilmiyor**. Uyarıyı düzeltmeden devam edemezsin.

Ders 2.15'teki faz projesinin `Makefile`'ında `-Werror` kullanacağız. İstersen `.vscode/tasks.json`'daki derleme komutuna da `-Wall -Wextra`'nın yanına `-Werror` ekleyebilirsin.

---

## 2. Undefined behavior nedir?

C standardı, bazı durumlar için "program ne yapmalı?" sorusuna **cevap vermez**. Bu durumlara **undefined behavior** denir. Standart, böyle bir durumda programın **herhangi bir şey** yapabileceğini söyler: doğru sonuç vermek, yanlış sonuç vermek, çökmek, hiçbir şey olmamış gibi devam etmek… Hepsi "kurallara uygun" sayılır.

Bu fazda karşılaştığımız undefined behavior'lar:

| Durum | Nerede gördük? |
| --- | --- |
| İşaretli tamsayı overflow'u (`int`'in sınırını aşmak) | 13! (2.8), `d * d` (2.10), `-INT_MIN` (2.11) |
| Array'in dışını okumak ya da yazmak | Labirentte kenarı açmak (2.4) |
| Değer verilmemiş bir değişkeni okumak | `total` (yukarıda), `int sayi;` (2.3) |
| Sıfıra bölmek | `average(10, 0)` (aşağıda) |
| Değer döndürmesi gereken fonksiyonun döndürmemesi | `sign(0)` (yukarıda) |

C neden böyle bir şeye izin veriyor? Çünkü C, Ders 2.1'de gördüğümüz gibi, makineye çok yakın ve çok hızlı olmak için tasarlandı. Her toplamadan sonra overflow kontrolü, her array erişiminde sınır kontrolü yapmak programı yavaşlatır. C bu kontrolleri **programcıya** bırakır ve karşılığında şunu varsayar: **doğru bir programda undefined behavior hiç olmaz.**

---

## 3. "Her şey olabilir" ne demek?

Bunu bir kuralın soyut uyarısı olarak düşünme. Compiler, "undefined behavior hiç olmaz" varsayımını **gerçekten kullanır**. Şu fonksiyona bak:

```c
#include <stdio.h>
#include <limits.h>

int next_is_bigger(int x) {
    return x + 1 > x;
}

int main(void) {
    printf("%d\n", next_is_bigger(5));
    printf("%d\n", next_is_bigger(INT_MAX));
    return 0;
}
```

`next_is_bigger(INT_MAX)` ne döndürür? `INT_MAX + 1` overflow olur. Programı iki farklı ayarla derleyip çalıştırdık:

```sh
clang -std=c17 -O0 opt.c -o o0 && ./o0
```

```
1
0
```

```sh
clang -std=c17 -O2 opt.c -o o2 && ./o2
```

```
1
1
```

**Aynı kod, iki farklı sonuç.** `-O0` ile derlenen program toplamayı gerçekten yaptı; sonuç negatif bir sayıya "döndü" ve fonksiyon 0 döndürdü. `-O2` (compiler'dan kodu hızlandırmasını isteyen ayar) ile derlenen program ise hiç toplama yapmadı. Compiler şöyle düşündü: "`x + 1`, overflow olmadığı sürece her zaman `x`'ten büyüktür. Overflow undefined behavior'dır ve doğru bir programda olmaz. O halde bu fonksiyon her zaman 1 döndürür." Ve fonksiyonu `return 1;`'e indirdi.

Compiler'ın mantığı kendi içinde kusursuz; hatalı olan bizim programımız. İşte undefined behavior'ı bu kadar tehlikeli yapan şey bu:

- Program **bazen** doğru çalışır, bazen çalışmaz.
- Testte çalışan kod, farklı bir ayarla ya da farklı bir compiler'la derlendiğinde bozulabilir.
- Hata, hatayı **yapan** satırda değil, compiler'ın vardığı sonucun etkilediği bambaşka bir yerde ortaya çıkabilir.

---

## 4. Sanitizer'lar: görünmeyeni görmek

Undefined behavior çoğu zaman **sessizdir**. Ders 2.4'teki array örneğini, döngü sınırını yanlış yazarak bozalım:

```c
#include <stdio.h>

#define SIZE 5

int main(void) {
    int scores[SIZE] = {70, 85, 60, 90, 75};
    int total = 0;
    for (int i = 0; i <= SIZE; i++) {
        total += scores[i];
    }
    printf("Toplam: %d\n", total);
    return 0;
}
```

`<=` yüzünden döngü `scores[5]`'i de okuyor; böyle bir eleman yok. Doğru toplam 380. Program ne diyor?

```
Toplam: 381
```

Hiçbir hata, hiçbir uyarı. Sadece yanlış bir sayı. `scores[5]`'in yerinde bellekte ne varsa (bu sefer 1) toplama eklendi. Bu hatayı ancak sonucu elle kontrol edersen fark edersin; çoğu zaman etmezsin.

clang'in bu tür hataları **program çalışırken** yakalayan araçları var: **sanitizer**'lar. Derlerken bir bayrak eklemek yeterli.

### AddressSanitizer

`-fsanitize=address`, bellekle ilgili hataları yakalar: array'in dışına taşmak, artık yaşamayan bir değişkene erişmek gibi.

```sh
clang -std=c17 -g -fsanitize=address oob.c -o oob
./oob
```

```
==24839==ERROR: AddressSanitizer: stack-buffer-overflow on address 0x00016d4da0b4
READ of size 4 at 0x00016d4da0b4 thread T0
    #0 0x00010292495c in main oob.c:9

  This frame has 1 object(s):
    [32, 52) 'scores' (line 6) <== Memory access at offset 52 overflows this variable
SUMMARY: AddressSanitizer: stack-buffer-overflow oob.c:9 in main
```

(Çıktıyı kısalttık.) Raporu okuyalım:

- **`stack-buffer-overflow`:** Stack'teki bir array'in sınırı aşıldı. (Yerel değişkenlerin stack'te durduğunu Ders 2.7'de görmüştük.)
- **`READ of size 4`:** 4 byte'lık, yani bir `int`'lik bir **okuma** yapıldı.
- **`main oob.c:9`:** Hatanın tam yeri: 9. satır, `total += scores[i];`.
- **`'scores' (line 6) <== ... overflows this variable`:** Aşılan array `scores`, 6. satırda tanımlanmış.

Sessiz bir yanlış sonuç, satır numarası ve değişken adıyla birlikte gelen bir rapora dönüştü. Program da hata anında durduruldu; yanlış sonuç hiç yazılmadı.

### UndefinedBehaviorSanitizer

`-fsanitize=undefined`, overflow ve sıfıra bölme gibi hataları yakalar. Bu araçla Ders 2.10 ve 2.11'de zaten tanıştın. Bir örnek daha:

```c
#include <stdio.h>

int average(int total, int count) {
    return total / count;
}

int main(void) {
    printf("%d\n", average(10, 0));
    return 0;
}
```

```
div0.c:4:18: runtime error: division by zero
```

### Sanitizer'ları ne zaman kullanmalı?

İkisi birlikte de kullanılabilir: `-fsanitize=undefined,address`. Sanitizer'lı bir program daha yavaş çalışır ve daha çok bellek kullanır; bu yüzden kullanıcıya verilen son sürümde kapatılırlar. Ama **geliştirirken** açık olmaları, hataları daha doğdukları anda yakalamak demektir.

Bunu alışkanlık haline getirmek için `.vscode/tasks.json`'daki derleme komutuna şu bayrağı ekleyebilirsin:

```
-fsanitize=undefined,address
```

LLDB de sanitizer'larla birlikte çalışır: bir sanitizer hata bulduğunda, LLDB programı tam o satırda durdurur ve değişkenlere bakabilirsin.

**Önemli bir sınır:** Sanitizer'lar sadece programın **gerçekten çalıştırılan** yollarındaki hataları yakalar. Hiç denemediğin bir girdi, hiç çalışmayan bir `if` dalı, sanitizer için görünmezdir. Ders 1.3'ten beri tekrarladığımız şey burada da geçerli: edge case'leri ayrıca dene. Ders 2.10'daki gibi binlerce girdiyle test etmek ile sanitizer'lar birlikte kullanıldığında çok güçlüdür.

---

## 5. Özet

| Araç | Ne zaman? | Neyi yakalar? |
| --- | --- | --- |
| `-Wall -Wextra` | Her zaman | Derleme sırasında şüpheli kodu |
| `-Werror` | Her zaman | Uyarıların görmezden gelinmesini |
| `-fsanitize=address` | Geliştirirken | Array dışına taşma ve diğer bellek hataları |
| `-fsanitize=undefined` | Geliştirirken | Overflow, sıfıra bölme ve diğer undefined behavior'lar |

İşaretsiz (`unsigned`) sayılarda overflow undefined behavior değildir; tanımlı bir şekilde başa sarar. Bunu ve `int`'in sınırlarının nereden geldiğini Faz 3'te göreceğiz.

---

## Alıştırmalar

**1. Uyarıları temizle.** Bölüm 1'deki programı, `-Wall -Wextra -Werror` ile hatasız derlenecek şekilde düzelt. Program "beş" yazmasın, 0 ile 2 arasındaki sayıların toplamını (3) ve `sign(0)`'ı (0) yazsın.

**2. Undefined behavior mı?** Aşağıdakilerin hangileri undefined behavior? (`int` değişkenler; `a` 5 elemanlı bir array.)

- a) `INT_MAX - 1 + 1`
- b) `INT_MAX + 1 - 1`
- c) `a[4] = 0;`
- d) `a[5] = 0;`
- e) `7 / 2`
- f) `7 / (2 - 2)`

**3. Labirent.** Ders 2.4'teki labirent oyununda (Alıştırma 9.5) kenardaki bir duvarı kaldırıp oyuncuyu dışarı çıkarmayı iki şekilde dene:

- **Sağ kenar:** `map[1][10]`'u 0 yap, oyuncuyu `{1, 9}`'dan başlat ve iki kez sağa git.
- **Alt kenar:** son satırdaki `map[6][1]`'i 0 yap, oyuncuyu `{5, 1}`'den başlat ve iki kez aşağı git.

Her birini önce `-fsanitize=address`, sonra `-fsanitize=undefined` ile derleyip çalıştır. Hangi sanitizer hangi hatayı yakalıyor?

<details>
<summary>Cevaplar</summary>

**1.**
```c
#include <stdio.h>

int sign(int x) {
    if (x > 0) {
        return 1;
    } else if (x < 0) {
        return -1;
    }
    return 0;
}

int main(void) {
    int total = 0;
    int n = 3;
    if (n == 5) {
        printf("beş\n");
    }
    for (int i = 0; i < n; i++) {
        total += i;
    }
    printf("%d %d\n", total, sign(0));
    return 0;
}
```
`sign`'a eksik `return 0;` eklendi, `=` yerine `==` yazıldı, kullanılmayan değişken silindi, `total`'a başlangıç değeri verildi. Çıktı: `3 0`.

**2.**

- a) **Değil.** Soldan sağa: `INT_MAX - 1` sığar, `+ 1` ile `INT_MAX` olur.
- b) **Undefined behavior.** `INT_MAX + 1` daha ilk adımda overflow olur. Matematikte a ile aynı ifade; bilgisayarda değil. İşlem sırası önemli.
- c) **Değil.** 5 elemanlı array'in son elemanı `a[4]`.
- d) **Undefined behavior.** `a[5]` array'in dışında.
- e) **Değil.** Tamsayı bölmesi, sonuç 3.
- f) **Undefined behavior.** Sıfıra bölme.

**3.** Denedik; sonuç şaşırtıcı:

| Açıklık | AddressSanitizer | UndefinedBehaviorSanitizer |
| --- | --- | --- |
| Sağ kenar | Hiçbir şey demiyor; oyuncu "Duvar!" mesajıyla geri itiliyor | `runtime error: index 11 out of bounds for type 'int[11]'` |
| Alt kenar | `stack-buffer-overflow ... in is_wall`, `'map' ... overflows this variable` | Hiçbir şey demiyor |

Neden? 2 boyutlu bir array'in satırları bellekte **arka arkaya** durur. `map[1][11]`, satırın sonunu bir aşınca bir sonraki satırın ilk kutusuna, yani `map[2][0]`'ın yerine denk gelir. Bu hâlâ `map`'in belleğinin içi. AddressSanitizer belleğe bakar ve orada bir sorun görmez; oyuncu, bir sonraki satırın duvarına çarpmış gibi sessizce geri itilir. UndefinedBehaviorSanitizer ise bir satırın 11 elemanlı olduğunu bilir ve 11 numaralı indeksi yakalar.

Alt kenarda tersi olur. 7. satır, `map`'in belleğinin tamamen dışındadır ve AddressSanitizer bunu yakalar. UndefinedBehaviorSanitizer ise `is_wall`'a parametre olarak gelen array'in **kaç satırlık** olduğunu bilemez (Ders 2.4'te sadece sütun sayısını yazmak zorunda olduğumuzu hatırla) ve satır indeksini denetleyemez.

Ders: iki sanitizer farklı şeylere bakar ve birbirinin kör noktalarını kapatır. Geliştirirken ikisini **birlikte** kullan: `-fsanitize=undefined,address`.

</details>

---

## Kaynaklar

- John Regehr, [*A Guide to Undefined Behavior in C and C++*](https://blog.regehr.org/archives/213) (2010): undefined behavior'ın compiler'ları nasıl etkilediğine dair klasik yazı dizisi.
- Chris Lattner, [*What Every C Programmer Should Know About Undefined Behavior*](https://blog.llvm.org/2011/05/what-every-c-programmer-should-know.html) (2011): clang'i yazan ekibin gözünden.
- [Clang belgeleri: AddressSanitizer](https://clang.llvm.org/docs/AddressSanitizer.html) ve [UndefinedBehaviorSanitizer](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html).

**Sıradaki ders:** Faz projesi. Bu fazda öğrendiğin her şeyle, menülü bir sağlık hesaplayıcı yazacaksın.
