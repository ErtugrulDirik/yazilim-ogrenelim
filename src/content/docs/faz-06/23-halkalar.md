---
title: "6.23 Halkalar"
description: "Toplama ve çarpmanın birlikte yaşadığı yapı: halka aksiyomları ve dağılma; değişmeli halka, birimli halka; örnekler (Z, Z/nZ, polinom halkası, matrisler); 0·a = 0 ve (−a)b = −(ab) kanıtları; birimler ve sıfır bölenler, Z/12 ve Z/256'da sayılmaları; tamlık bölgesi; bilgisayar tamsayılarının Z/2ⁿZ halkası olduğunu bütün 8 bitlik üçlülerde doğrulayan program; derleyicinin halka yasalarıyla yaptığı dönüşümler (x·9 → x + (x≪3), dağılma, −x), işaretli taşmanın tanımsızlığından yararlanması ve kayan noktanın neden halka olmadığı."
---

Ders 6.21'de bir işlemli yapıları (gruplar) inceledik. Ama tamsayılarda, mod $n$'de ve bilgisayarda **iki** işlem var ve birbirleriyle konuşuyorlar: $a(b + c) = ab + ac$. Toplama ve çarpmanın birlikte uyduğu kurallara **halka** denir. Bu ders, Faz 3'ten beri kullandığımız tamsayı aritmetiğinin tam cebirsel adını veriyor ve derleyicinin optimizasyonlarının hangi yasalara dayandığını gösteriyor. Faz 12'deki polinom aritmetiği ve Faz 16'daki cebirsel sadeleştirmeler de bu yapının üzerinde.

---

## 1. Tanım

$(R, +, \cdot)$ şu aksiyomları sağlıyorsa bir **halka**dır:

1. $(R, +)$ değişmeli bir grup (Ders 6.21): birleşme, birim **0**, ters $-a$, değişme.
2. $\cdot$ birleşmeli: $(ab)c = a(bc)$.
3. **Dağılma** (iki yönden): $a(b + c) = ab + ac$ ve $(a + b)c = ac + bc$.

Ek özellikler:

- $ab = ba$ ise **değişmeli halka**.
- Çarpma için bir birim **1** varsa ($1 \cdot a = a \cdot 1 = a$) **birimli halka**. (Bu derste bütün halkalar birimli.)

Dikkat: çarpma için **ters istemiyoruz**. Halkada bölme olmayabilir; çarpma sadece bir monoid (Ders 6.21). Dağılma, iki işlemi birbirine bağlayan tek aksiyom; onsuz sadece iki ayrı yapı olurdu.

---

## 2. Örnekler

| Halka | Değişmeli mi | Not |
| --- | --- | --- |
| $\mathbb{Z}$ | evet | prototip |
| $\mathbb{Q}$, $\mathbb{R}$ | evet | sıfır dışında bölme de var: **cisim** (Ders 6.24) |
| $\mathbb{Z}/n\mathbb{Z}$ | evet | Ders 6.18 |
| `uint32_t` ile `+`, `*` | evet | $\mathbb{Z}/2^{32}\mathbb{Z}$ |
| $\mathbb{Z}[x]$, katsayıları tamsayı polinomlar | evet | Ders 6.16'daki `poly_mul` |
| $n \times n$ tamsayı matrisleri | **hayır** ($n \ge 2$) | Ders 6.25 |
| Bit desenleri, `^` ve `&` | evet | $\mathbb{Z}/2$'nin vektörleri; her $a$ için $a \cdot a = a$ (Boole halkası) |
| `double`, `+`, `*` | **hayır** | ne toplama birleşmeli ne dağılma tutuyor |

Bit desenleri satırı ilginç: XOR toplama, AND çarpma. $a \,\&\, (b \oplus c) = (a \,\&\, b) \oplus (a \,\&\, c)$ her bit için doğru (tek bitte $\mathbb{Z}/2$'nin dağılması), dolayısıyla 32 bitte de. Ders 6.24'teki $GF(2)$ ve Ders 5.19'daki CRC bu halkada.

---

## 3. Aksiyomlardan ilk teoremler

Bunlar "apaçık" görünüyor ama aksiyomlarda yoklar; kanıtlanmaları gerekiyor. Ve kanıtlandıkları için **her** halkada, `uint32_t`'de de, polinomlarda da, matrislerde de geçerliler.

**Teorem.** Her $a$ için $0 \cdot a = 0$.

**Kanıt.** $0 \cdot a = (0 + 0) \cdot a = 0 \cdot a + 0 \cdot a$ (dağılma). İki taraftan $0 \cdot a$'nın toplama tersini çıkar: $0 = 0 \cdot a$. $\blacksquare$

Sıfırla çarpmanın sıfır verdiği bir **aksiyom değil**, dağılmanın sonucu. Dağılmayı bozan bir yapıda (kayan nokta, $0 \cdot \infty = \text{NaN}$; Ders 3.13) bu teorem de bozuluyor.

**Teorem.** $(-a) b = -(ab)$, ve $(-a)(-b) = ab$.

**Kanıt.** $ab + (-a)b = (a + (-a))b = 0 \cdot b = 0$; demek $(-a)b$, $ab$'nin toplama tersi. İkincisi: $(-a)(-b) = -(a(-b)) = -(-(ab)) = ab$. $\blacksquare$

"Eksi çarpı eksi artıdır" kuralının kanıtı: dağılmayı korumak istiyorsan başka seçeneğin yok.

---

## 4. Birimler ve sıfır bölenler

Çarpma tersi olmayabilir dedik. Bir halkada:

- $a$ bir **birim** (unit): $ab = 1$ olan bir $b$ var. (Bu "birim" kelimesi 1 ile karıştırılmasın: 1 bir birim, ama tek birim olmayabilir.)
- $a \ne 0$ bir **sıfır bölen**: $ab = 0$ olan bir $b \ne 0$ var.

$\mathbb{Z}$'de birimler sadece $\pm 1$, sıfır bölen yok. $\mathbb{Z}/n\mathbb{Z}$'de Ders 6.19'dan biliyoruz: $a$ birim $\iff$ $\text{EBOB}(a, n) = 1$. Geri kalanlar?

```c
for (unsigned a = 1; a < n; a++) {
    bool unit = false, zdiv = false;
    for (unsigned b = 1; b < n; b++) {
        if (a * b % n == 1) unit = true;
        if (a * b % n == 0) zdiv = true;
    }
    units += unit; zd += zdiv;
}
```

```
Z/12: 4 birim, 7 sifir bolen, 0 ikisi de degil (0 haric)
Z/256: 128 birim, 127 sifir bolen, 0 ikisi de degil (0 haric)
```

$\mathbb{Z}/n$'de sıfır olmayan her eleman ya birim ya sıfır bölen; ikisi birden değil. $d = \text{EBOB}(a, n) > 1$ ise $a \cdot \frac{n}{d} = \frac{a}{d} \cdot n \equiv 0$. Birimler $\varphi(n)$ tane (Ders 6.15): $\varphi(12) = 4$, $\varphi(256) = 128$.

`uint8_t`'de **her çift sayı** bir sıfır bölen: örneğin $16 \cdot 16 = 256 \equiv 0$. İki sıfır olmayan sayının çarpımı sıfır. Sıfır bölenler, mod $2^n$'de sadeleştirmenin neden yapılamadığını açıklıyor: $ab = ac$ ama $b \ne c$ olabilir ($2 \cdot 1 = 2 \cdot 129$ mod 256; Ders 6.18). Grup aksiyomlarından gelen sadeleştirme sadece birimler için çalışıyor.

Sıfır böleni olmayan değişmeli halkaya **tamlık bölgesi** (integral domain) denir: $\mathbb{Z}$, $\mathbb{Z}[x]$, ve $\mathbb{Z}/p$ ($p$ asal). Tamlık bölgesinde sadeleştirme serbest: $ab = ac$ ve $a \ne 0$ ise $a(b - c) = 0$, dolayısıyla $b = c$.

---

## 5. Bilgisayar tamsayıları bir halkadır

Ders 6.18'de `uint8_t` toplamasının ve çarpmasının mod 256 ile aynı olduğunu gördük. Halka aksiyomlarının hepsinin tuttuğunu doğrudan, **bütün** üçlüler için denetleyelim:

```c
bool ok = true;
for (unsigned a = 0; a < 256; a++)
    for (unsigned b = 0; b < 256; b++)
        for (unsigned c = 0; c < 256; c++) {
            uint8_t A = a, B = b, C = c;
            ok = ok && (uint8_t)((uint8_t)(A * B) * C) == (uint8_t)(A * (uint8_t)(B * C));   // carpma birlesme
            ok = ok && (uint8_t)(A * (uint8_t)(B + C)) == (uint8_t)((uint8_t)(A * B) + (uint8_t)(A * C)); // dagilma
        }
```

```
uint8_t: birlesme ve dagilma 2^24 uclude dogru: 1
```

16 milyon üçlü; Ders 6.3'ün dersine rağmen burada **kanıt** bu: evren sonlu ve hepsini denedik. (Her ara sonucu `uint8_t`'ye dönüştürmek şart; C'nin tamsayı yükseltmesi (Ders 3.5) yoksa hesabı `int`'te yapardı.)

### Derleyici halka yasalarını kullanıyor

`unsigned` aritmetik bir halka olduğu için derleyici, her `unsigned` için sonucu değiştirmeyeceğinden **emin** olarak ifadeleri yeniden yazabiliyor. Ders 5.14'te godbolt'ta sabite bölmeyi görmüştük; birkaç halka dönüşümü daha (clang `-O2`, ARM64):

```c
unsigned mul9(unsigned x) { return x * 9; }
unsigned dist(unsigned a, unsigned b, unsigned c) { return a * b + a * c; }
unsigned neg(unsigned x) { return x * 0xFFFFFFFFu; }
```

```
_mul9:
	add	w0, w0, w0, lsl #3        ; x + (x << 3)
_dist:
	add	w8, w2, w1                ; b + c
	mul	w0, w8, w0                ; a * (b + c)
_neg:
	neg	w0, w0                    ; -x
```

- `x * 9` → `x + (x << 3)`: $9x = 8x + x$, dağılma; ve `<< 3`, $2^3$ ile çarpma. Çarpma yerine tek bir "kaydırılmış toplama" komutu.
- `a*b + a*c` → `a * (b + c)`: dağılmayı **ters yönde** kullanarak iki çarpmayı bire indirdi. Bu dönüşüm **sadece** halkada geçerli; `double`'da yapılamıyor.
- `x * 0xFFFFFFFF` → `-x`: $\text{0xFFFFFFFF} \equiv -1 \pmod{2^{32}}$ ve $(-1) \cdot x = -x$ (Bölüm 3'teki teorem).

Faz 16'daki **instcombine** benzeri geçişler, bu tür yüzlerce halka özdeşliğinin bir listesi. Faz 12'de bir sembolik sadeleştiricide aynı kuralları kendimiz yazacağız.

### İşaretli tipler: halkadan fazlası ve eksiği

```c
int always(int x) { return x + 1 > x; }
unsigned notalways(unsigned x) { return x + 1 > x; }
```

```
_always:
	mov	w0, #1                    ; her zaman 1
_notalways:
	cmn	w0, #1                    ; x == 0xFFFFFFFF mi?
	cset	w0, ne
```

`unsigned`'da $x + 1 > x$, $x = 2^{32} - 1$'de **yanlış** (sarıyor); derleyici dürüstçe kontrol ediyor. `int`'te ise derleyici fonksiyonu `return 1`'e çevirdi. Sebep: işaretli taşma **undefined behavior** (Ders 2.12, 3.8); derleyici taşmanın hiç olmadığını varsayabiliyor ve o zaman `int`, $\mathbb{Z}/2^{32}$ değil, $\mathbb{Z}$'nin bir parçası gibi davranıyor: $\mathbb{Z}$'de $x + 1 > x$ her zaman doğru.

Bu iki yönlü bir bıçak. Derleyiciye daha güçlü varsayımlar (sıralama, $x + 1 > x$, $2x / 2 = x$) veriyor; döngü sayaçlarının optimizasyonu büyük ölçüde buna dayanıyor. Ama taşan bir programda sonuç öngörülemez. `-fwrapv` bayrağı işaretli tamsayıları da $\mathbb{Z}/2^{32}$ halkası yapıyor ve bu optimizasyonları kapatıyor.

### Kayan nokta halka değil

```
0.1*(0.1+0.3) = 0.040000000000000008, 0.040000000000000001
```

Dağılma bozuk (her işlemden sonra yuvarlama, Ders 3.14). Toplama da birleşmeli değil (Ders 6.21). Bu yüzden derleyici `a*b + a*c`'yi `double` için `a*(b+c)`'ye **çeviremiyor**; `-ffast-math` bayrağı "kayan noktayı bir halka (hatta cisim) gibi düşün" izni veriyor ve sonuçları değiştirebiliyor. Sayısal kodda hangi bayrağın neyi feda ettiğini bilmek, hangi cebirsel yasayı feda ettiğini bilmek.

---

## Alıştırmalar

**1** – Halka aksiyomlarından kanıtla: (a) $a \cdot (b - c) = ab - ac$ (b) $(a + b)^2 = a^2 + ab + ba + b^2$; değişmeli halkada $a^2 + 2ab + b^2$. Matrislerde neden ilk biçimde kalıyor?

**2** – `uint8_t`'de $x^2 = x$ olan (**tek kuvvetli**) elemanları bul. Kaç tane? $\mathbb{Z}/12$'de? (İpucu: ÇKT ile $\mathbb{Z}/12 \cong \mathbb{Z}/4 \times \mathbb{Z}/3$.)

**3** – `uint32_t`'de $x^2 = 1$ olan kaç $x$ var? $\mathbb{Z}$'de iki tane ($\pm 1$). Programla say (bütün $2^{32}$ sayıyı dene, ya da mod $2^k$ için küçük $k$'larda dene ve deseni bul).

**4** – Şu dönüşümlerden hangilerini derleyici `unsigned` için yapabilir, hangilerini `int` için, hangilerini `double` için? (a) `x * 2 / 2` → `x` (b) `(x + y) - y` → `x` (c) `x * 0` → `0` (d) `x / 3 * 3 + x % 3` → `x` (e) `(a + b) + c` → `a + (b + c)`. godbolt ile kontrol et.

**5** – Bit desenlerinde XOR toplama, AND çarpma olan halkada (Boole halkası) her $a$ için $a + a = 0$ ve $a \cdot a = a$. Bu iki özellikten, halkanın değişmeli olması gerektiğini kanıtla. (İpucu: $(a + b)^2 = a + b$'yi aç.)

<details>
<summary>Cevaplar</summary>

**1** – (a) $a(b - c) = a(b + (-c)) = ab + a(-c) = ab + (-(ac)) = ab - ac$; ortadaki adım Bölüm 3'teki teoremin simetriği. (b) $(a + b)(a + b) = a(a + b) + b(a + b) = a^2 + ab + ba + b^2$; iki yönlü dağılmayı da kullandık. Değişmeliyse $ab + ba = 2ab$. Matrislerde $AB \ne BA$ olabildiği için $(A + B)^2 \ne A^2 + 2AB + B^2$; okul formülü bir **değişmeli** halka teoremi.

**2** – `uint8_t`'de: $x(x - 1) \equiv 0 \pmod{256}$; $x$ ile $x - 1$ ardışık, biri tek, dolayısıyla $2^8$ tamamen birini bölmeli: $x \in \{0, 1\}$. Sadece 2 tane. $\mathbb{Z}/12$'de: $\mathbb{Z}/4$'te tek kuvvetliler $\{0, 1\}$, $\mathbb{Z}/3$'te $\{0, 1\}$; ÇKT ile $2 \times 2 = 4$ tane: $0, 1, 4, 9$ ($4^2 = 16 \equiv 4$, $9^2 = 81 \equiv 9$). Modül birden çok asalın kuvvetiyse halka "parçalara ayrılıyor" ve tek kuvvetliler parçaları seçiyor.

**3** – Dört tane: $1$, $2^{32} - 1$ ($= -1$), $2^{31} - 1$, $2^{31} + 1$. Kontrol: $(2^{31} + 1)^2 = 2^{62} + 2^{32} + 1 \equiv 1$. Mod $2^k$, $k \ge 3$ için her zaman 4. $\mathbb{Z}/2^{32}$ tamlık bölgesi olmadığı için $(x - 1)(x + 1) = 0$ denkleminin "olağan" ikiden fazla çözümü var. Ders 6.20'deki Miller–Rabin tam bu özellikten yararlanıyordu: asal modda 1'in sadece iki karekökü var.

**4** – (a) `unsigned`: hayır ($x = 2^{31}$: $2x$ sarıyor, $0 / 2 = 0$); `int`: **evet** (taşma UB, derleyici varsayıyor); `double`: hayır; 2 ile çarpma tam ama çok büyük $x$'te $2x = \infty$ olur ve $\infty / 2 = \infty \ne x$, dolayısıyla derleyici bu dönüşümü yapmıyor. (b) `unsigned` ve `int`: evet (toplama grubunda $-y$ ters); `double`: hayır ($x = 1$, $y = 10^{20}$). (c) `unsigned`, `int`: evet; `double`: hayır ($x = \infty$ ya da NaN, ve $-0.0$). (d) `unsigned`, `int`: evet (C'de bölme ve kalan tanımı tam bunu garanti ediyor, Ders 6.17); `double` için `%` yok. (e) `unsigned`, `int`: evet; `double`: hayır, `-ffast-math` olmadan asla.

**5** – $(a + b)^2 = a + b$ (her eleman tek kuvvetli). Açınca $a^2 + ab + ba + b^2 = a + ab + ba + b$. Eşitleyince $ab + ba = 0$. $a + a = 0$ olduğu için her eleman kendi toplama tersi: $ab = -(ba) = ba$. $\blacksquare$ Ayrıca $1 + 1 = 0$: bu halkanın **karakteristiği** 2. Ders 6.24'te karakteristiği 2 olan cisimlerle (GF(2ⁿ)) çalışacağız; orada çıkarma ile toplama aynı işlem.

</details>

---

## Kaynaklar

- Charles Pinter, *A Book of Abstract Algebra* (2. baskı), Bölüm 17–19: halkalar, tamlık bölgeleri, birimler ve sıfır bölenler.
- Joseph Gallian, *Contemporary Abstract Algebra* (10. baskı), Bölüm 12–13.
- John Regehr, "A Guide to Undefined Behavior in C and C++" (blog, 2010): işaretli taşmanın optimizasyonlara etkisi.
- LLVM `InstCombine` kaynak kodu (`lib/Transforms/InstCombine`): halka yasalarına dayanan sadeleştirmelerin gerçek listesi.

**Sıradaki ders:** Cisimler ve sonlu cisimler. Sıfır dışındaki her elemanın tersinin olduğu halkalar, $GF(2^8)$, ve AES ile Reed–Solomon'un kullandığı çarpma.
