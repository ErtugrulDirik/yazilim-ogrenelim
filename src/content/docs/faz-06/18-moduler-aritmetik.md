---
title: "6.18 Modüler aritmetik"
description: "Mod n denkliği ve denklik sınıfları; Z/nZ ve toplama ile çarpmanın iyi tanımlı olduğunun kanıtı; işlemi her adımda mod almak; 9'a bölünebilme kuralı; hızlı üs alma ile powmod ve __int128 ile taşmasız mulmod; bilgisayar tamsayılarının Z/2ⁿZ olduğu, ikiye tümleyenin −x ≡ 2ⁿ − x olması ve işaretli/işaretsiz toplamanın aynı devre olduğunu 8 bitte bütün çiftler için doğrulayan C programı; mod 2ⁿ'de bölme ve sıralamanın neden bozulduğu."
---

Ders 6.6'da "mod $n$ denk" bağıntısının bir denklik bağıntısı olduğunu kanıtladık ve sınıflarını yazdık: mod 3'te $\{0, 3, 6, \dots\}$, $\{1, 4, 7, \dots\}$, $\{2, 5, 8, \dots\}$. O zaman "bilgisayarın `uint32_t` aritmetiği $\mathbb{Z}/2^{32}\mathbb{Z}$" demiştik. Bu derste bu cümleyi kanıtlıyoruz ve Faz 3'teki ikiye tümleyenin neden bu kadar iyi çalıştığını, artık bir mühendislik hilesi olarak değil, bir matematik teoremi olarak görüyoruz.

---

## 1. Denklik

$$
a \equiv b \pmod{n} \iff n \mid a - b
$$

"$a$ ile $b$, $n$'e bölündüğünde aynı kalanı verir." Saat aritmetiği: 23:00'ten 5 saat sonra 04:00, çünkü $23 + 5 = 28 \equiv 4 \pmod{24}$.

$a$'nın denklik sınıfı $[a]_n = \{\dots, a - 2n, a - n, a, a + n, a + 2n, \dots\}$. Her sınıfın $\{0, 1, \dots, n-1\}$ içinde tam bir temsilcisi var: bölme algoritmasının kalanı (Ders 6.17). Sınıfların kümesi:

$$
\mathbb{Z}/n\mathbb{Z} = \{[0], [1], \dots, [n-1]\}
$$

$n$ elemanlı bir küme. Elemanları **sayı değil, sonsuz kümeler**; ama her birini kalanıyla adlandırıyoruz.

---

## 2. İşlemler iyi tanımlı

$\mathbb{Z}/n\mathbb{Z}$'de toplama ve çarpmayı temsilciler üzerinden tanımlamak istiyoruz:

$$
[a] + [b] = [a + b], \qquad [a] \cdot [b] = [a \cdot b].
$$

Ama bir sorun var: bir sınıfın sonsuz temsilcisi var. $[2] = [7]$ (mod 5). $[2] + [1]$'i 2 ile mi 7 ile mi hesaplayacağız? Sonuç seçime bağlıysa tanım anlamsız. Bağlı olmadığını göstermemiz gerekiyor.

**Teorem.** $a \equiv a'$ ve $b \equiv b' \pmod n$ ise

$$
a + b \equiv a' + b' \quad\text{ve}\quad ab \equiv a'b' \pmod{n}.
$$

**Kanıt.** $a' = a + kn$, $b' = b + ln$. Toplam: $a' + b' = a + b + (k + l)n$. ✓ Çarpım: $a'b' = ab + (al + bk + kln)n$. ✓ $\blacksquare$

Bu teorem, modüler aritmetiğin bütün **pratik** gücünün kaynağı: hesabın **her adımında** mod alabilirsin, sonuç değişmez. Ara değerler hiçbir zaman $n^2$'yi aşmıyor.

**Örnek.** $3^{200}$'ün son üç basamağı? $3^{200}$ yaklaşık 96 basamaklı; ama sadece mod 1000 lazım ve her çarpmadan sonra mod alabiliriz. (Birazdan programla: cevap 001.)

**Örnek: 9'a bölünebilme.** $10 \equiv 1 \pmod 9$, dolayısıyla her $k$ için $10^k \equiv 1^k = 1$. Bir sayı $d_k \cdots d_1 d_0$ ise

$$
\sum d_i 10^i \equiv \sum d_i \pmod 9.
$$

Sayı ile basamak toplamı mod 9'da aynı. İlkokuldaki "basamaklar toplamı 9'a bölünüyorsa sayı da bölünür" kuralı bu teoremin bir satırlık sonucu. Aynı yolla $10 \equiv -1 \pmod{11}$ sana 11 kuralını veriyor (basamakları dönüşümlü işaretle topla).

```
987654321987654321 mod 9 = 0, basamak toplami 90 mod 9 = 0
```

Ders 2.5'teki "sayıyı ters çevirme" ve palindrom alıştırmalarının hepsi basamaklarla çalışıyordu; mod 9 ve mod 11 o sayıların hızlı bir sağlamasını veriyor ("dokuz çıkarma" yöntemiyle hesap kontrolü yüzyıllarca kullanıldı).

---

## 3. Hızlı modüler üs

Ders 2.9'daki hızlı üs alma ($e$'nin bitlerine bakarak karele ve çarp), her adımda mod alınca **modüler üs** oluyor. Ders 6.13'e göre $\Theta(\log e)$ çarpma:

```c
static uint64_t mulmod(uint64_t a, uint64_t b, uint64_t m) {
    return (uint64_t)((unsigned __int128)a * b % m);
}

static uint64_t powmod(uint64_t a, uint64_t e, uint64_t m) {
    uint64_t r = 1 % m;
    a %= m;
    while (e) {
        if (e & 1) r = mulmod(r, a, m);
        a = mulmod(a, a, m);
        e >>= 1;
    }
    return r;
}
```

İki ayrıntı:

- `mulmod`: $a, b < m < 2^{64}$ olsa bile $ab$, 128 bite kadar çıkabiliyor. `unsigned __int128` (clang ve gcc'nin uzantısı; standart C değil) çarpımı tam tutuyor, sonra mod alıyoruz. Ders 5.13'teki geniş çarpmanın ta kendisi: işlemci $64 \times 64 \to 128$ bitlik çarpımı tek komutla yapıyor.
- `1 % m`: $m = 1$ ise her şey $\equiv 0$; `r = 1` yazsaydık `powmod(a, 0, 1)` yanlışlıkla 1 döndürürdü.

```
3^200 mod 1000 = 1
2^64 mod (10^9+7) = 582344008
7^(10^18) mod (2^61-1) = 80730455784664051
```

Üçüncü satır $10^{18}$ üssü 60 civarı adımda hesaplıyor. $3^{200} \equiv 1 \pmod{1000}$ tesadüf değil; Ders 6.20'deki Euler teoremi bunu açıklayacak ($\varphi(1000) = 400$ ve $3^{400} \equiv 1$; burada 200 bile yetiyor).

---

## 4. Bilgisayar tamsayıları $\mathbb{Z}/2^n\mathbb{Z}$'dir

C standardı `unsigned` aritmetiği için açıkça şunu söylüyor: sonuç $2^n$ ile mod alınarak hesaplanır (Ders 3.8). Yani `uint8_t` toplama ve çarpma **tam olarak** $\mathbb{Z}/256\mathbb{Z}$'nin işlemleri. Taşma bir hata değil; tanım bu.

Şimdi Ders 3.3'teki ikiye tümleyene bakalım. $-x$'i $\sim x + 1$ olarak temsil ediyorduk. Neden?

$$
\sim x = (2^n - 1) - x \quad(\text{her biti ters çevirmek, } 11\dots1\text{'den çıkarmak})
$$

$$
\sim x + 1 = 2^n - x \equiv -x \pmod{2^n}.
$$

İkiye tümleyen, $-x$'in mod $2^n$'deki **olağan temsilcisi**: $[-x]$ sınıfının $\{0, \dots, 2^n - 1\}$ içindeki elemanı. Örneğin 8 bitte $-1 \equiv 255$, $-128 \equiv 128$.

Bu sayede işaretli ve işaretsiz sayılar **aynı denklik sınıflarını** kullanıyor; sadece sınıfların **adlandırılması** farklı:

| bit deseni | `uint8_t` olarak | `int8_t` olarak | sınıf |
| --- | --- | --- | --- |
| `00000001` | 1 | 1 | $[1]$ |
| `01111111` | 127 | 127 | $[127]$ |
| `10000000` | 128 | −128 | $[128] = [-128]$ |
| `11111111` | 255 | −1 | $[255] = [-1]$ |

İşaretsiz temsilciler $\{0, \dots, 255\}$, işaretliler $\{-128, \dots, 127\}$. Bölüm 2'deki teoreme göre toplama ve çarpma **hangi temsilciyi seçtiğinden bağımsız**. Demek ki işaretli ve işaretsiz toplama aynı bit desenini vermeli. Bunu 8 bitte bütün $256 \times 256$ çift için doğrulayalım:

```c
int ok = 1;
for (int a = -128; a < 128; a++)
    for (int b = -128; b < 128; b++) {
        uint8_t ua = (uint8_t)a, ub = (uint8_t)b;
        uint8_t s = (uint8_t)(ua + ub), p = (uint8_t)(ua * ub);
        if (s != (uint8_t)((a + b) & 0xFF) || p != (uint8_t)((a * b) & 0xFF)) ok = 0;
        if ((uint8_t)(-ua) != (uint8_t)(~ua + 1)) ok = 0;
    }
```

```
8 bit toplama/carpma mod 256 ile ayni: 1
(uint8_t)-1 = 255, (uint8_t)-128 = 128
```

$a + b$'yi gerçek tamsayılarla (işaretli, `int`) hesaplayıp bit desenini aldık; $u_a + u_b$'yi işaretsiz 8 bitle. 65536 çiftin hepsinde aynı. Bu yüzden işlemcide **tek** bir toplama devresi ve tek bir `add` komutu var; işaretli mi işaretsiz mi olduğunu bilmiyor ve bilmesi gerekmiyor. Fark sadece bayraklarda (taşma OF mi, elde CF mi; Ders 7.8) ve karşılaştırmada.

Bu, ikiye tümleyenin bütün rakip temsillere (işaret-büyüklük, birlere tümleyen) karşı kazanmasının sebebi: **matematiğin halka yapısını** koruyan tek temsil o. Ders 6.23'te bu yapıya **halka** adını vereceğiz ve derleyicinin bunu nasıl sömürdüğünü göreceğiz.

### Ne bozuluyor?

Modüler aritmetik toplamayı ve çarpmayı koruyor, ama tamsayıların her özelliğini değil:

- **Sıralama**: $\mathbb{Z}/n\mathbb{Z}$'de "küçüktür" anlamlı değil. $255 > 0$ ama $255 + 1 = 0$. Ders 3.6'daki işaretli-işaretsiz karşılaştırma tuzağı, aynı sınıfın iki farklı temsilcisini ($-1$ ve $255$) sıralamaya çalışmaktan geliyor. Toplama sınıflara saygı duyuyor, `<` duymuyor.
- **Bölme**: mod 256'da $2 \cdot 1 = 2$, ama $2 \cdot 129 = 258 \equiv 2$ de doğru. $2x \equiv 2$ denkleminin iki çözümü var (1 ve 129); "2'yi 2'ye bölmek" tek bir sonuç vermiyor. Mod $n$'de bölme her zaman tanımlı değil; ne zaman tanımlı olduğunu ve nasıl yapıldığını Ders 6.19 anlatacak. Ders 6.9'da 5 ile çarpmanın tersini bulmuştuk; 2 ya da 6 ile çarpmanın tersi **yok** (çift sayılarla çarpma birebir değildi).

C'nin `/` operatörü bu yüzden modüler bölme değil; tamsayı bölmesi, ve `unsigned` için bile mod $2^n$ yapısına uymuyor: `(uint8_t)(200 + 100) / 2` ile `(200 / 2 + 100 / 2)` farklı.

İşaretli tipler için bir uyarı: C standardı işaretli taşmayı **tanımsız** bırakıyor (Ders 2.12, 3.8). Donanım mod $2^n$ hesaplasa bile derleyici `int` toplamasının taşmadığını **varsayıp** optimize edebiliyor. Bu derste gördüğümüz güzel yapıya güvenmek istiyorsan `unsigned` kullan.

---

## Alıştırmalar

**1** – Mod 7'de $3^{100}$'ü elle hesapla. (İpucu: $3^6 \equiv 1$; $100 = 6 \cdot 16 + 4$.) Sonra `powmod` ile doğrula.

**2** – Haftanın günlerini 0 (Pazartesi) ile 6 arasında numarala. Bugün Cuma ise 1000 gün sonra hangi gün? $-1000$ gün önce? C'de `%` kullanırken negatif durumda nasıl doğru sonuç alırsın? (Ders 6.17'deki `mod`.)

**3** – 11'e bölünebilme kuralını kanıtla ve bir C fonksiyonu olarak yaz: `bool div11(const char *digits)`. Sayıyı tamsayıya çevirmeden, basamak dizgisinden (yüzlerce basamaklı sayılar için de çalışsın).

**4** – `mulmod`'u `__int128` olmadan yaz: $b$'nin bitlerine bakarak toplama ile çarpma (Ders 5.13'teki kaydır-ve-topla çarpması), her adımda mod al. $m < 2^{63}$ ise ara toplamalar neden taşmıyor? `__int128`'li sürümden kaç kat yavaş?

**5** – `uint32_t` için `x * 0xAAAAAAABu` işleminin, $x$ 3'e **tam bölündüğünde** $x / 3$'ü verdiğini göster. (İpucu: $3 \cdot \text{0xAAAAAAAB} \equiv 1 \pmod{2^{32}}$.) 3'e bölünmeyen $x$'te ne çıkıyor? Ders 5.14'teki sihirli sayıyla (aynı sabit, ama `>> 33` ile) farkı ne?

<details>
<summary>Cevaplar</summary>

**1** – $3^1 = 3$, $3^2 = 9 \equiv 2$, $3^3 \equiv 6$, $3^4 \equiv 18 \equiv 4$, $3^5 \equiv 12 \equiv 5$, $3^6 \equiv 15 \equiv 1$. $3^{100} = (3^6)^{16} \cdot 3^4 \equiv 1 \cdot 4 = 4$. `powmod(3, 100, 7) == 4`. $3^6 \equiv 1$ olması da tesadüf değil: Ders 6.20'deki Fermat teoremi, $p = 7$ asal için $a^{6} \equiv 1$.

**2** – Cuma = 4. $1000 \bmod 7 = 6$, $(4 + 6) \bmod 7 = 3$: Perşembe. $-1000$: $4 - 1000 = -996$; C'de `-996 % 7 == -2`, düzeltmeyle $-2 + 7 = 5$: Cumartesi. Kontrol: $-1000 \equiv 1 \pmod 7$ (çünkü $1001 = 7 \cdot 143$), $4 + 1 = 5$. ✓

**3** – $10 \equiv -1 \pmod{11}$, $10^i \equiv (-1)^i$. Sayı $\equiv d_0 - d_1 + d_2 - \dots$

```c
bool div11(const char *digits) {
    int n = (int)strlen(digits), s = 0;
    for (int i = 0; i < n; i++) {
        int d = digits[n - 1 - i] - '0';       // sagdan i'inci basamak
        s += (i % 2 == 0) ? d : -d;
        s %= 11;                               // her adimda kucuk tut
    }
    return s == 0;                             // s, [-10, 10] araliginda; -0 da 0
}
```

`s %= 11` negatif kalabilir ama $s \equiv 0 \iff s = 0$ (aralıkta $\pm 11$ yok). Her adımda mod alarak keyfi uzunluktaki sayılarla çalışıyoruz; Bölüm 2'deki teoremin doğrudan uygulaması.

**4** –

```c
uint64_t mulmod_slow(uint64_t a, uint64_t b, uint64_t m) {   // m < 2^63
    uint64_t r = 0;
    a %= m;
    while (b) {
        if (b & 1) { r += a; if (r >= m) r -= m; }
        a += a; if (a >= m) a -= m;                        // a = 2a mod m
        b >>= 1;
    }
    return r;
}
```

$r, a < m < 2^{63}$ ise $r + a < 2^{64}$: toplama taşmıyor. `%` yerine tek çıkarma yetiyor çünkü toplam $2m$'den küçük. 64 tur toplama ve dal; `__int128` sürümü tek çarpma ve bir bölme (128 bitlik bölme yavaş bir kütüphane çağrısı olsa da). Ölçünce birkaç ile on kat arası fark çıkıyor. Bu, `powmod`'u bir `log` faktörü daha yavaşlatıyor. Faz 12'deki Montgomery çarpması bu bölmeyi de ortadan kaldıracak.

**5** – `3u * 0xAAAAAAABu` $= 0x200000001$, mod $2^{32}$'de 1: `0xAAAAAAAB`, 3'ün mod $2^{32}$ tersi. $x = 3q$ ise $x \cdot \text{0xAAAAAAAB} \equiv 3q \cdot 3^{-1} = q$. Tam bölünmeyen $x$'te sonuç $x \cdot 3^{-1}$ mod $2^{32}$, büyük ve anlamsız bir sayı (örneğin $x = 1$ için `0xAAAAAAAB`). Ders 5.14'teki yöntem farklı: `x * 0xAAAAAAAB` çarpımının **üst** bitlerini (`>> 33`) alıyor ve her $x$ için $\lfloor x/3 \rfloor$ veriyor; bu derstekinin **alt** 32 biti alıyor ve sadece tam bölmede çalışıyor. Aynı sabit, iki farklı matematik: biri $\frac{2^{33}}{3}$'e yakın bir sayı, öbürü mod $2^{32}$'de $\frac13$. Derleyiciler ikisini de kullanıyor (ikincisi, örneğin işaretçi farkını eleman boyutuna bölerken: `(p - q)` her zaman tam bölünüyor).

</details>

---

## Kaynaklar

- Kenneth Rosen, *Discrete Mathematics and Its Applications* (8. baskı), §4.1–4.2: bölünebilirlik ve modüler aritmetik.
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), §2.3: tamsayı aritmetiği, ikiye tümleyen toplamanın mod 2ʷ olması.
- Henry Warren, *Hacker's Delight* (2. baskı), §10-16: tam bölmenin modüler tersle yapılması.

**Sıradaki ders:** Genişletilmiş Öklid ve modüler ters. Bézout katsayıları, ve mod $n$'de "bölmenin" ne zaman ve nasıl yapıldığı.
