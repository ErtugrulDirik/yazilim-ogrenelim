---
title: "4.17 strchr, strrchr, strstr sıfırdan"
description: "Yazıda aramak: strchr'ün ilk, strrchr'ün son eşleşmeyi bulması, c == '\\0' için sonlandırıcıyı döndürme ayrıntısı, const char * alıp char * döndüren imzanın Ders 4.8'deki ikilemi ve C23 çözümü, strchr ile bir satırı parçalama, naif strstr'in O(n×m) en kötü durumu ölçülerek ve neden tekrarlı metinlerde patladığı, KMP'ye köprü."
---

Ders 4.12'deki `read_int`'te `strchr(line, '\n')` kullandık; Ders 4.8'de `strchr`'ün `const` ikilemine değindik ve "Ders 4.17'de bu kararı biz de vereceğiz" dedik. Şimdi yazıda **arama** yapan üç fonksiyonu yazıyoruz: bir karakteri baştan (`strchr`) ve sondan (`strrchr`), ve bir alt diziyi (`strstr`).

`strchr` ile `strrchr` kolay. `strstr` ise "bir yazının içinde başka bir yazıyı bulmak" probleminin naif çözümü; bu problemin neden hızlı bir algoritma (Faz 9'daki KMP) hak ettiğini de burada göreceğiz.

---

## 1. strchr

```c
char *strchr(const char *s, int c);
```

- `s`'de `c`'nin **ilk** geçtiği yeri gösteren pointer; yoksa `NULL`.
- `c` bir `int`, ama bir `char`'a dönüştürülerek aranıyor (tıpkı Ders 3.16'daki `getchar`'ın `int` döndürmesi gibi tarihî bir sebep).
- Bir ayrıntı: `c == '\0'` ise, sonlandırıcının yeri bulunuyor — yani yazının sonundaki `'\0'`'ı gösteren pointer dönüyor.

```c
char *strchr_mine(const char *s, int c) {
    char target = (char)c;
    while (*s != '\0') {
        if (*s == target) {
            return (char *)s;
        }
        s++;
    }
    if (target == '\0') {
        return (char *)s;
    }
    return NULL;
}
```

Döngü yazı boyunca ilerliyor; eşleşme bulursa adresi döndürüyor. Döngü `'\0'`'da bitiyor, onu karşılaştırmadan — bu yüzden `c == '\0'` durumunu ayrıca ele alıyoruz: döngü bittiğinde `s` zaten `'\0'`'ı gösteriyor, onu döndürüyoruz. Bu küçük kural kullanışlı: `strchr(s, '\0')`, Ders 4.15'teki gibi yazının sonunu veriyor.

### Ders 4.8'deki ikilem, karar anı

`strchr`, `const char *` alıp `char *` döndürüyor: aldığından `const`'u **düşürüyor**. Ders 4.8'de bunun tehlikesini konuşmuştuk. `return (char *)s;` satırındaki cast, const'u atan tam o hamle.

Neden böyle? Ders 4.8'deki iki seçenek: ya `int *`/`const int *` için iki ayrı fonksiyon (C++'ın yolu), ya da `const` alıp `const` olmayan döndürmek. C, ikinci yolu seçti, çünkü iki ayrı fonksiyon C'de mümkün değil (aynı isimli iki fonksiyon olamaz). Sonuç: `strchr`, `const` bir yazıda bulduğun şeye yazmana compiler'ın izin vermesi demek. Bu makinede:

```c
const char message[] = "merhaba";
char *p = strchr(message, 'h');
*p = 'H';   // message const; undefined behavior
```

derlenir ama Ders 4.8'deki `const` globaldeki gibi davranır (burada yerel, çökmeyebilir ama tanımsız). Sorumluluk tamamen çağıranda.

C23 bu ikilemi Ders 4.8'de anlattığımız gibi çözdü: `_Generic` (Ders 3.10) ile, `const char *` verince `const char *`, `char *` verince `char *` dönen bir `strchr`. Kendi sürümümüzü yazarken bu seçeneğimiz var; ama standart imzayla uyumlu kalmak için klasik `char *` döndüren biçimi tutuyoruz ve adını `strchr_mine` koyuyoruz (Ders 4.13'teki kural: standart adları kullanmıyoruz).

### strchr ile bir satırı parçalamak

`strchr`'ün en yaygın kullanımı, bir yazıyı ayraçlardan bölmek:

```c
char text[] = "a=1;b=2;c=3";
char *p = text;
char *semi;
while ((semi = strchr(p, ';')) != NULL) {
    *semi = '\0';
    printf("[%s] ", p);
    p = semi + 1;
}
printf("[%s]\n", p);
```

```
[a=1] [b=2] [c=3]
```

Her `;`'yi bulup yerine `'\0'` yazıyoruz; böylece `p`, o ana kadarki parçayı gösteren bir yazı oluyor (Ders 4.12: `'\0'` yazıyı orada bitirir). `text`'in değiştirilebilir bir array olması şart — bu yüzden `const char *` değil. Bu kalıbı Ders 4.20'de `strtok`'u yazarken genişleteceğiz.

---

## 2. strrchr: sondan arama

```c
char *strrchr(const char *s, int c);
```

Baştaki `r`, "reverse". `c`'nin **son** geçtiği yeri buluyor. Baştan sona gezip, her eşleşmede "en son gördüğüm yer"i güncellemek yeterli:

```c
char *strrchr_mine(const char *s, int c) {
    char target = (char)c;
    const char *last = NULL;
    while (1) {
        if (*s == target) {
            last = s;
        }
        if (*s == '\0') {
            break;
        }
        s++;
    }
    return (char *)last;
}
```

Döngü `'\0'`'ı da kontrol ediyor (önce eşleşmeye bakıp sonra `'\0'` ise çıkıyor), çünkü `strchr` gibi `strrchr` da `c == '\0'` sorulduğunda sonlandırıcının yerini döndürüyor. `last` başta `NULL`; hiç eşleşme olmazsa `NULL` dönüyor.

En yaygın kullanımı dosya yollarında: `strrchr(path, '/')`, son `/`'ten sonrasının dosya adı olduğunu söyler; `strrchr(name, '.')` son noktayı bulup uzantıyı ayırır.

---

## 3. strstr: naif alt dizi arama

```c
char *strstr(const char *haystack, const char *needle);
```

`haystack` (saman yığını) içinde `needle`'ın (iğne) **ilk** geçtiği yeri buluyor. Naif fikir: her konumda, iğnenin oradan itibaren eşleşip eşleşmediğini dene.

```c
char *strstr_mine(const char *haystack, const char *needle) {
    if (*needle == '\0') {
        return (char *)haystack;
    }
    for (const char *h = haystack; *h != '\0'; h++) {
        const char *hp = h;
        const char *np = needle;
        while (*np != '\0' && *hp == *np) {
            hp++;
            np++;
        }
        if (*np == '\0') {
            return (char *)h;
        }
    }
    return (char *)NULL;
}
```

- **Boş iğne** her yazının başında "bulunur"; standart böyle diyor, `haystack`'i döndürüyoruz.
- Dış döngü her başlangıç konumunu (`h`) deniyor.
- İç döngü, `h`'den itibaren iğneyi karşılaştırıyor. İğne biterse (`*np == '\0'`) tamamı eşleşti, `h`'yi döndürüyoruz.
- İç döngü iğne bitmeden durursa, bir sonraki `h`'ye geçiyoruz.

2 milyon rastgele girdide (küçük alfabeyle, eşleşmelerin sık olması için) standart `strstr`, `strchr`, `strrchr` ile karşılaştırdık: sıfır fark.

### En kötü durum: $O(n \times m)$

Naif aramanın bir zayıf noktası var. İğne her konumda **neredeyse** eşleşip son anda bozulursa, iç döngü her seferinde baştan sona çalışıyor. Klasik kötü örnek: saman `"aaaa...a"` ($n$ tane `a`), iğne `"aaa...ab"` ($m-1$ tane `a` ve bir `b`). İğne hiçbir yerde yok, ama her konumda ilk $m-1$ karakter eşleşip sonuncuda bozuluyor.

İç döngünün toplam karşılaştırma sayısını ölçtük ($m = 100$ sabit, $n$ değişken):

```
n =  10000  karsilastirma =       995149  (n*m = 1000000)  0.00116 s
n =  20000  karsilastirma =      1995149  (n*m = 2000000)  0.00230 s
n =  40000  karsilastirma =      3995149  (n*m = 4000000)  0.00414 s
n =  80000  karsilastirma =      7995149  (n*m = 8000000)  0.00896 s
```

Karşılaştırma sayısı $n \times m$ ile orantılı: $n$ iki katına çıkınca iş de iki katına. Yani bu algoritma $O(n \times m)$. İğne 100 karakter, saman 80 bin karakter olunca 8 milyon karşılaştırma — sadece "yok" diyebilmek için. İğne uzadıkça daha da kötü.

Çoğu gerçek metinde (bir kelimeyi bir paragrafta aramak gibi) bu kadar kötü değil: ilk karakter çoğu konumda hemen uyuşmaz, iç döngü bir adımda biter, pratikte $O(n)$'e yakın. Ama girdi düşman kontrolündeyse (bir web sunucusuna arama sorgusu gelmesi gibi), bu en kötü durum bir hizmet reddi (DoS) sorununa dönüşebilir.

### KMP'ye köprü

Naif aramanın israfı şu: `"aaab"` iğnesi `"aaaa..."`da 4. karakterde bozulduğunda, zaten okuduğumuz üç `a`'yı **unutup** bir sonraki konumdan baştan başlıyoruz. Oysa o üç `a`'yı okuduğumuzda, iğnenin de `"aaa"` ile başladığını biliyorduk; bu bilgiyi kullanıp samanı **geri sarmadan** devam edebilirdik.

Knuth–Morris–Pratt (KMP) algoritması tam bunu yapıyor: iğneyi önceden işleyip, bir uyuşmazlıkta samanı geri almadan iğnenin neresinden devam edileceğini söyleyen bir tablo çıkarıyor. Sonuç $O(n + m)$: samanın her karakterine en fazla bir kez bakılıyor. KMP'yi, Boyer–Moore ve Rabin–Karp ile birlikte Faz 9'da (Ders 9.9) yazıp bu naif `strstr`'i yeniden ele alacağız. Gerçek `strstr` sürümleri de genelde bu akıllı algoritmaların bir karışımını kullanıyor.

---

## Alıştırmalar

**1** – `strchr_mine(s, '\0')` ne döndürür? `strchr_mine("", 'a')` ve `strchr_mine("", '\0')`? Üçünü de kodun üzerinden izle.

**2** – `strrchr_mine`'ı `strlen` ile, yazının **sonundan başa** giderek yaz. Hangi sürüm daha az karakter okur? (İpucu: ikisi de yazıyı bir kez geziyor, ama biri `strlen` için fazladan.)

**3** – `count_occurrences(const char *s, const char *needle)`: `needle`'ın `s`'de **çakışmayan** kaç kez geçtiğini say. `strstr_mine`'ı kullan. `"aaaa"` içinde `"aa"` kaç kez geçer — 2 mi 3 mü? Cevabın "çakışmayan" tanımına nasıl bağlı?

**4** – Naif `strstr_mine`, iğne saman kadar uzunken ($m = n$) ve hiç eşleşmezken kaç karşılaştırma yapar? Ya iğne samandan **uzunsa** ($m > n$)? İç döngünün ilk `*hp` okuması nerede durur?

**5** – Bir dosya adından uzantıyı döndüren `const char *extension(const char *name)` yaz: `strrchr`'le son `.`'yı bul. `"foto.jpg"` → `"jpg"`, `"arsiv.tar.gz"` → `"gz"`, `"README"` → `""` (ya da `NULL`), `".gitignore"` → ? Nokta yazının başındaysa ne yapmalı?

<details>
<summary>Cevaplar</summary>

**1** – `strchr_mine(s, '\0')`: döngü yazının sonuna kadar gider, `'\0'`'ı karşılaştırmadan çıkar, `target == '\0'` olduğu için döngü sonrası `s`'yi (sonlandırıcının adresini) döndürür. `strchr_mine("", 'a')`: döngü hiç dönmez (`*s` zaten `'\0'`), `target` `'\0'` değil, `NULL`. `strchr_mine("", '\0')`: döngü dönmez, `target == '\0'`, boş yazının `'\0'`'ını (yani yazının başını) döndürür.

**2** –

```c
char *strrchr_from_end(const char *s, int c) {
    char target = (char)c;
    const char *p = s + my_strlen(s);   // '\0'u gosteriyor
    while (p >= s) {
        if (*p == target) {
            return (char *)p;
        }
        p--;
    }
    return NULL;
}
```

`p`, `'\0'`'dan başlıyor (bu yüzden `c == '\0'` de doğru çalışır) ve başa doğru iniyor. İlk sürüm (baştan, `last`'ı güncelleyerek) daha az karakter okur: yazıyı bir kez geziyor. Bu sürüm `strlen` için bir kez daha geziyor; toplam iki geçiş. İlk sürüm tercih edilir. (Küçük tuzak: `p >= s` karşılaştırması, `p` `s`'nin bir gerisine inerse pointer aritmetiği kurallarına göre tanımsız olabilir; `while (p-- > s)` benzeri bir yazım daha güvenlidir.)

**3** –

```c
int count_occurrences(const char *s, const char *needle) {
    int count = 0;
    size_t nlen = my_strlen(needle);
    if (nlen == 0) {
        return 0;
    }
    const char *p = s;
    char *found;
    while ((found = strstr_mine(p, needle)) != NULL) {
        count++;
        p = found + nlen;
    }
    return count;
}
```

`"aaaa"` içinde `"aa"`: bu "çakışmayan" sürüm **2** bulur (0–1 ve 2–3). `p = found + nlen` ile bulunan eşleşmenin **sonundan** devam ettiğimiz için çakışma olmuyor. Çakışmaya izin verseydik (`p = found + 1`) **3** bulurdu (0–1, 1–2, 2–3). Hangisinin doğru olduğu soruna bağlı; "kaç tane ayrık `aa` var" ile "kaç konumda `aa` başlıyor" farklı sorular.

**4** – $m = n$ ve eşleşme yoksa: dış döngü `h = haystack`'te başlar, iç döngü en fazla $n$ karakter karşılaştırıp bir yerde bozulur; `h` ilerledikçe kalan saman kısalır, bir noktadan sonra iğne artık sığmaz ve iç döngü hemen biter. En kötü durum yine $O(n \times m) = O(n^2)$ mertebesinde. İğne samandan **uzunsa** ($m > n$): her `h` için iç döngü en geç samanın `'\0'`'ında durur (`*hp == '\0'`, iğnede o konumda `'\0'` olmadığı için `*hp == *np` yanlış). İğne hiçbir zaman bitemeyeceği için `NULL` döner; `*hp` okuması samanın `'\0'`'ını geçmez, sınır dışına çıkmaz.

**5** –

```c
const char *extension(const char *name) {
    const char *dot = strrchr_mine(name, '.');
    if (dot == NULL || dot == name) {
        return "";
    }
    return dot + 1;
}
```

`"foto.jpg"` → `"jpg"`, `"arsiv.tar.gz"` → `"gz"` (son nokta), `"README"` → `""` (nokta yok). `".gitignore"` → `dot == name` (nokta en başta), `""` döndürüyoruz: baştaki nokta bir uzantı ayracı değil, gizli dosya işareti (Unix geleneği). `dot == name` kontrolü tam bunun için. `dot + 1`, son noktadan sonrasını gösteriyor; nokta yazının son karakteriyse (`"dosya."`) `dot + 1` boş yazıyı (`'\0'`) gösterir, bu da makul.

</details>

---

## Kaynaklar

- Brian Kernighan & Dennis Ritchie, *The C Programming Language* (2. baskı), §B3: `strchr`, `strrchr`, `strstr`.
- C standardı (ISO/IEC 9899:2018), §7.24.5: arama fonksiyonları. C23 (ISO/IEC 9899:2024), §7.26.5.2: niteleyici koruyan `strchr`.
- Donald Knuth, James Morris & Vaughan Pratt, "Fast Pattern Matching in Strings" (SIAM J. Comput. 1977): KMP.
- Thomas Cormen vd., *Introduction to Algorithms* (4. baskı), Bölüm 32: string eşleme algoritmaları ve naif yöntemin analizi.

**Sıradaki ders:** `memcpy`, `memmove`, `memset` ve `memcmp` sıfırdan. Çakışan bölgeler, `memmove`'un yön seçimi ve `restrict` anahtar kelimesi.
