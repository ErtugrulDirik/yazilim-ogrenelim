---
title: "6.22 Alt grup, devirli grup, Lagrange"
description: "Alt grup ve alt grup testi; bir elemanın mertebesi ve ürettiği devirli alt grup; devirli gruplar ve üreteçler (ilkel kök); yan kümeler ve Lagrange teoremi (alt grubun mertebesi grubun mertebesini böler); Lagrange'ın sonucu olarak Fermat ve Euler teoremleri; (Z/15)* ve mod 13 için mertebeleri hesaplayan C programı; RSA'nın kurulumu, neden çalıştığının kanıtı, ÇKT ile hızlı çözme, ve oyuncak RSA kodu; ayrık logaritma ve kriptografiye bağlantı."
---

Ders 6.20'de $3^{200} \equiv 1 \pmod{1000}$ çıktı, oysa Euler sadece $3^{400} \equiv 1$'i söylüyordu; "gerçek periyot Euler'in üssünün bir **böleni**" dedik ve kanıtı bu derse bıraktık. Ders 6.21'de grupları tanımladık. Şimdi grupların **içindeki** gruplara bakacağız ve sayı teorisinin bu fazdaki en büyük sonucunu çok kısa bir kanıtla elde edeceğiz: Lagrange teoremi. Fermat, Euler ve RSA onun birer satırlık sonuçları.

---

## 1. Alt grup

$(G, \ast)$ bir grup, $H \subseteq G$ olsun. $H$, aynı işlemle kendi başına bir grupsa $H$'ye $G$'nin **alt grubu** denir: $H \le G$.

- $(2\mathbb{Z}, +) \le (\mathbb{Z}, +)$: çift sayılar. Kapalı (çift + çift = çift), 0 içinde, tersler çift.
- $\{0, 3\} \le \mathbb{Z}/6\mathbb{Z}$: $3 + 3 = 0$.
- $\{1\}$ ve $G$ kendisi: her grubun **aşikâr** alt grupları.
- Tek sayılar $\mathbb{Z}$'nin alt grubu **değil**: $1 + 1 = 2$ tek değil; 0 da içinde değil.

**Alt grup testi.** $H$ boş değil ve her $a, b \in H$ için $a \ast b^{-1} \in H$ ise $H \le G$.

**Kanıt.** $a \in H$ al: $a \ast a^{-1} = e \in H$. Sonra $e \ast a^{-1} = a^{-1} \in H$. Sonra $a \ast (b^{-1})^{-1} = a \ast b \in H$. Birleşme $G$'den miras. $\blacksquare$

Sonlu gruplarda daha da basit: **kapalılık** yetiyor (Alıştırma 2).

---

## 2. Mertebe ve devirli alt grup

$a \in G$ için kuvvetlerine bak: $e, a, a^2, a^3, \dots$ $G$ sonluysa bu dizi bir yerde tekrar etmek zorunda (Ders 6.15, güvercin yuvası): $a^i = a^j$, $i < j$. Sadeleştirince $a^{j-i} = e$.

$a$'nın **mertebesi** (order) $\text{ord}(a)$: $a^k = e$ olan **en küçük** $k > 0$. $a$'nın kuvvetleri

$$
\langle a \rangle = \{e, a, a^2, \dots, a^{k-1}\}
$$

tam $k$ farklı eleman ve bir alt grup: $a^i \ast a^j = a^{(i+j) \bmod k}$, tersler $a^{-i} = a^{k-i}$. Buna $a$'nın ürettiği **devirli alt grup** denir. Yapısı $\mathbb{Z}/k\mathbb{Z}$ ile aynı (izomorf, Ders 6.21): $a^i \leftrightarrow i$.

Programla $(\mathbb{Z}/15\mathbb{Z})^*$'da her elemanın mertebesini ve kuvvetlerini hesaplayalım:

```c
// a'nin mod n mertebesi: a^k = 1 olan en kucuk k > 0
static unsigned order(uint64_t a, uint64_t n) {
    uint64_t x = a % n; unsigned k = 1;
    while (x != 1) { x = x * a % n; k++; }
    return k;
}
```

```
(Z/15)*: 8 eleman
   1: mertebe 1  <a> = {1}
   2: mertebe 4  <a> = {1, 2, 4, 8}
   4: mertebe 2  <a> = {1, 4}
   7: mertebe 4  <a> = {1, 7, 4, 13}
   8: mertebe 4  <a> = {1, 8, 4, 2}
  11: mertebe 2  <a> = {1, 11}
  13: mertebe 4  <a> = {1, 13, 4, 7}
  14: mertebe 2  <a> = {1, 14}
```

Grubun 8 elemanı var; mertebeler $1, 2, 4$. **Hepsi 8'i bölüyor.** Bir tesadüf değil.

(`order` sadece $\text{EBOB}(a, n) = 1$ için sonlanıyor; aksi halde $a$'nın kuvvetleri asla 1 olmaz ve döngü sonsuz. Ön koşul, Ders 6.2.)

### Devirli gruplar

Bir grup tek bir elemanın kuvvetlerinden oluşuyorsa, $G = \langle g \rangle$, **devirli**dir ve $g$ bir **üreteç**tir.

- $\mathbb{Z}/n\mathbb{Z}$ devirli, üreteç 1 (ve $n$ ile aralarında asal her eleman).
- $(\mathbb{Z}/15)^*$ devirli **değil**: 8 elemanlı ama hiçbir elemanın mertebesi 8 değil.
- $(\mathbb{Z}/p\mathbb{Z})^*$, $p$ asalken **her zaman** devirli (Gauss; kanıtı polinomlar gerektiriyor, Ders 6.24). Üreteçlerine **ilkel kök** denir.

```
mod 13 ureteclar: 2 6 7 11
```

$2$'nin kuvvetleri mod 13: $1, 2, 4, 8, 3, 6, 12, 11, 9, 5, 10, 7$, hepsi. Bir üreteç, $(\mathbb{Z}/p)^*$'ı Ders 6.21'deki gibi toplamaya çeviriyor: $2^i \cdot 2^j = 2^{i+j}$, yani çarpma, üslerin mod $p-1$ toplaması. Bu, Ders 6.24'teki log tablolarının temeli.

---

## 3. Lagrange teoremi

**Teorem (Lagrange).** $G$ sonlu bir grup ve $H \le G$ ise $|H|$, $|G|$'yi böler.

Kanıt için bir yapı: $a \in G$ için $H$'nin **sol yan kümesi** $aH = \{a \ast h \mid h \in H\}$.

$(\mathbb{Z}/15)^*$'da $H = \langle 4 \rangle = \{1, 4\}$:

| $a$ | $aH$ |
| --- | --- |
| 1 | $\{1, 4\}$ |
| 2 | $\{2, 8\}$ |
| 7 | $\{7, 13\}$ |
| 11 | $\{11, 14\}$ |

(ve $4H = \{4, 1\} = 1H$, $8H = \{8, 2\} = 2H$, ...) Dört yan küme, her biri 2 elemanlı, hiç kesişmiyorlar ve birleşimleri bütün grup. Ders 6.6'nın dilinde: bir **bölüntü**.

**Kanıt.** Üç adım.

1. *Her yan küme $|H|$ elemanlı.* $h \mapsto a \ast h$ birebir (sadeleştirme, Ders 6.21), dolayısıyla $|aH| = |H|$.
2. *İki yan küme ya aynı ya ayrık.* "$a \sim b \iff a^{-1} b \in H$" bir denklik bağıntısı (yansıyan: $e \in H$; simetrik: tersler $H$'de; geçişli: $H$ kapalı), ve sınıfları tam olarak yan kümeler. Ders 6.6'daki teoreme göre sınıflar bir bölüntü.
3. *Sayma.* $G$, her biri $|H|$ elemanlı, $k$ tane ayrık yan kümeye bölünüyor: $|G| = k \cdot |H|$. $\blacksquare$

Kanıtın ne kadar az şey kullandığına bak: sadeleştirme ve denklik sınıfları. Fazın başındaki bağıntılar dersi burada karşılığını veriyor.

**Sonuç 1.** Sonlu bir grupta her elemanın mertebesi grubun mertebesini böler. ($\langle a \rangle$ bir alt grup ve $|\langle a \rangle| = \text{ord}(a)$.)

**Sonuç 2.** Her $a$ için $a^{|G|} = e$. ($|G| = k \cdot \text{ord}(a)$, $a^{|G|} = (a^{\text{ord}(a)})^k = e^k = e$.)

**Sonuç 3 (Euler, yeniden).** $G = (\mathbb{Z}/n\mathbb{Z})^*$, $|G| = \varphi(n)$. Sonuç 2: $a^{\varphi(n)} \equiv 1$. Fermat, $n = p$ hali.

Ders 6.20'de Euler'i bir permütasyon hilesiyle kanıtlamıştık; şimdi bunun genel bir yapının özel hali olduğunu görüyoruz. Ve $3^{200} \equiv 1 \pmod{1000}$'in açıklaması: 3'ün mertebesi $\varphi(1000) = 400$'ün bir böleni, ve 200'ü de bölüyor (gerçekte mertebe 100).

**Sonuç 4.** Asal mertebeli her grup devirlidir. ($|G| = p$; $a \ne e$ için $\text{ord}(a) \mid p$ ve $\ne 1$, demek $p$; $\langle a \rangle = G$.)

---

## 4. RSA

RSA (Rivest, Shamir, Adleman, 1977), bu dersin teoremlerini bir kilide çeviriyor.

**Kurulum.**

1. İki büyük asal seç: $p$, $q$ (Ders 6.20'deki Miller–Rabin ile). $N = pq$.
2. $\varphi(N) = (p-1)(q-1)$ (Ders 6.15, çarpımsallık).
3. $\text{EBOB}(e, \varphi(N)) = 1$ olan bir $e$ seç (genellikle $65537$).
4. $d = e^{-1} \bmod \varphi(N)$ (Ders 6.19).

**Açık anahtar** $(N, e)$, herkese verilir. **Gizli anahtar** $d$ (ve $p$, $q$).

- Şifreleme: $c = m^e \bmod N$
- Çözme: $m = c^d \bmod N$

**Teorem.** Her $0 \le m < N$ için $(m^e)^d \equiv m \pmod N$.

**Kanıt.** $ed \equiv 1 \pmod{\varphi(N)}$, yani $ed = 1 + k(p-1)(q-1)$. Önce mod $p$'de bak. $p \nmid m$ ise Fermat: $m^{ed} = m \cdot (m^{p-1})^{k(q-1)} \equiv m \cdot 1 = m$. $p \mid m$ ise iki taraf da $\equiv 0$. Her durumda $m^{ed} \equiv m \pmod p$. Simetrik olarak mod $q$'da. $p$ ve $q$ farklı asallar; ÇKT'nin teklik kısmı (Ders 6.20): $m^{ed} \equiv m \pmod{pq}$. $\blacksquare$

Kanıt, $m$'nin $N$ ile aralarında asal olmadığı (nadir) durumları da kapsıyor; sadece Euler'e dayansaydık onları kaçırırdık.

**Neden güvenli?** $d$'yi bulmak için $\varphi(N)$ lazım, $\varphi(N)$ için $p$ ve $q$ lazım, yani $N$'yi çarpanlarına ayırmak. Çarpanlara ayırmanın (bugün bildiğimiz) hızlı bir algoritması yok: 2048 bitlik bir $N$ için en iyi yöntemler bile evrenin yaşından uzun sürüyor. Çarpmak kolay, geri almak zor; bu asimetri açık anahtarlı kriptografinin temeli.

### Oyuncak RSA

```c
uint64_t P = 61, Q = 53, N = P * Q, ph = (P - 1) * (Q - 1), e = 17;
uint64_t d = inv(e, ph);
uint64_t m = 65, c = powmod(m, e, N), back = powmod(c, d, N);
```

```
N=3233 phi=3120 e=17 d=2753: m=65 -> c=2790 -> 65
butun m < N icin geri donuyor: 1
```

`inv` Ders 6.19'daki modüler ters, `powmod` Ders 6.18'deki hızlı üs. Ve 3233 mesajın hepsi geri dönüyor; $p$ ya da $q$'nun katı olan 113 mesaj da (kanıtın ikinci durumu).

**ÇKT ile hızlı çözme.** $c^d \bmod N$ yerine iki küçük üs al: $m_p = c^{d \bmod (p-1)} \bmod p$ ve $m_q = c^{d \bmod (q-1)} \bmod q$ (Fermat ile üsleri küçülttük), sonra ÇKT ile birleştir:

```c
uint64_t mp = powmod(c, d % (P - 1), P), mq = powmod(c, d % (Q - 1), Q);
uint64_t h = mulmod(inv(Q, P), (mp + P - mq % P) % P, P);
printf("CRT ile: %llu\n", (unsigned long long)(mq + h * Q));   // 65
```

(Garner formülü: $m = m_q + q \cdot [q^{-1}(m_p - m_q) \bmod p]$.) Yarı boyutlu sayılarla iki üs: çarpma maliyeti dörtte bire, üs uzunluğu yarıya iniyor; toplamda yaklaşık 4 kat hız. Gerçek RSA kütüphaneleri böyle çözüyor.

Gerçek RSA'da sayılar 2048 bit ve bunları Faz 12'deki büyük tamsayılarla yazacağız. Ayrıca gerçek kullanımda "ders kitabı RSA" asla doğrudan kullanılmıyor: $m$ önce rastgele dolgu (padding, OAEP) ile genişletiliyor, yoksa aynı mesaj hep aynı şifreye gidiyor ve küçük mesajlar kolayca tahmin ediliyor. Kriptografiyi kendin yazma; bu ders onun **neden** çalıştığını anlamak için.

### Ayrık logaritma

Devirli grupların başka bir zor problemi: $g$ ve $h = g^x \bmod p$ verildiğinde $x$'i bul. **Ayrık logaritma.** İleri yön (`powmod`) $O(\log x)$, geri yön için bilinen en iyi genel algoritmalar $\sqrt{p}$ civarı (Alıştırma 5). Diffie–Hellman anahtar değişimi ve eliptik eğri kriptografisi bu zorluğa dayanıyor: iki taraf $g^a$ ve $g^b$'yi paylaşıyor, ikisi de $g^{ab}$'yi hesaplayabiliyor, dinleyen ise ayrık logaritmayı çözemediği için hesaplayamıyor.

---

## Alıştırmalar

**1** – $\mathbb{Z}/12\mathbb{Z}$'nin (toplama) bütün alt gruplarını listele. Her birinin mertebesi 12'yi bölüyor mu? 12'nin her böleni için bir alt grup var mı?

**2** – Sonlu bir grupta kapalı ve boş olmayan her alt kümenin alt grup olduğunu kanıtla. (İpucu: $a \in H$ ise $a$'nın kuvvetleri $H$'de; $a^{\text{ord}(a) - 1} = a^{-1}$.) Sonsuz gruplarda neden yetmez? ($\mathbb{N} \subseteq \mathbb{Z}$.)

**3** – Ders 6.20'deki 3. alıştırmayı Lagrange ile yeniden düşün: $(\mathbb{Z}/p)^*$'da $a^{-1} = a^{p-2}$ neden doğru? `uint32_t`'de tek bir $a$ için $a^{-1} = a^{2^{31} - 1}$ doğru mu? Daha küçük bir üs yeter mi? (İpucu: $(\mathbb{Z}/2^{32})^*$'ın en büyük mertebesi $2^{30}$.)

**4** – Oyuncak RSA'yı $p = 1000003$, $q = 1000033$ ile kur, $e = 65537$. Bir mesajı şifrele ve çöz. Sonra $N$'yi Ders 2.9'daki deneme bölmesiyle çarpanlarına ayırıp $d$'yi "çal". Ne kadar sürdü? $p$, $q$ 10 kat daha fazla basamaklı olsaydı ne olurdu?

**5** – Ayrık logaritmayı kaba kuvvetle ($g^0, g^1, \dots$) ve **bebek adım–dev adım** algoritmasıyla çöz: $m = \lceil\sqrt{p-1}\rceil$; $g^j$'leri ($j < m$) bir tabloya koy; $h \cdot (g^{-m})^i$'yi $i = 0, 1, \dots$ için hesapla ve tabloda ara. Eşleşme $x = im + j$ verir. $p = 1000003$, $g = 2$ için ikisini karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – $\mathbb{Z}/12$ devirli; her alt grubu da devirli ve 12'nin her $d$ böleni için **tam bir** alt grup var: $\langle 12/d \rangle$. $d = 1$: $\{0\}$; $d = 2$: $\langle 6 \rangle = \{0, 6\}$; $d = 3$: $\langle 4 \rangle = \{0, 4, 8\}$; $d = 4$: $\langle 3 \rangle$; $d = 6$: $\langle 2 \rangle$; $d = 12$: hepsi. Altı alt grup, 12'nin altı böleni; ve kapsama ilişkisi Ders 6.7'deki 12'nin bölenlerinin Hasse diyagramıyla aynı. Değişmeli olmayan gruplarda Lagrange'ın tersi doğru değil: $A_4$ (12 eleman) 6 elemanlı alt gruba sahip değil.

**2** – $a \in H$; kapalılıkla bütün kuvvetleri $H$'de. Sonlu olduğu için $\text{ord}(a) = k$ var; $e = a^k \in H$ ve $a^{-1} = a^{k-1} \in H$. Birleşme miras. $\blacksquare$ Sonsuz grupta kuvvetler hiç 1'e dönmeyebilir: $\mathbb{N}$ toplamaya kapalı ve 0'ı içeriyor ama tersleri yok.

**3** – $|(\mathbb{Z}/p)^*| = p - 1$, Sonuç 2: $a^{p-1} = 1$, dolayısıyla $a \cdot a^{p-2} = 1$. `uint32_t`'de $|(\mathbb{Z}/2^{32})^*| = 2^{31}$, $a^{2^{31}} = 1$, yani $a^{-1} = a^{2^{31} - 1}$ doğru. Ama her elemanın mertebesi $2^{30}$'u böldüğü için (bu grup devirli değil; $\mathbb{Z}/2 \times \mathbb{Z}/2^{30}$) $a^{-1} = a^{2^{30} - 1}$ de yetiyor. Yine de Ders 6.19'daki Newton yöntemi (4 adım) her ikisinden de hızlı (yaklaşık 60 kareleme).

**4** – $N \approx 10^{12}$; deneme bölmesi $\sqrt N \approx 10^6$ bölmede $p$'yi buluyor, milisaniyeler. Basamaklar 10 kat (12 → 120 basamak): $\sqrt N \approx 10^{60}$, deneme bölmesi umutsuz. Daha iyi algoritmalar (sayı cismi eleği) 120 basamağı günler içinde çarpanlarına ayırabiliyor; 617 basamakta (2048 bit) hâlâ imkânsız. Güvenlik, ayırma algoritmalarının ilerleme hızından bir adım önde kalacak kadar büyük sayılar seçmeye dayanıyor.

**5** – Kaba kuvvet $x$ adım, en kötü $p - 1 \approx 10^6$. Bebek adım–dev adım: $m = 1001$; $m$ elemanlı tablo (Faz 8'deki hash tablosu ya da sıralı dizi + ikili arama) ve en fazla $m$ dev adım: $O(\sqrt p)$ zaman ve bellek. $10^6$ yerine $\sim 2000$ işlem. Zaman–bellek takası: bellek harcayarak karekök hız. 256 bitlik eliptik eğrilerde $\sqrt{2^{256}} = 2^{128}$; bu yüzden hâlâ güvenli.

</details>

---

## Kaynaklar

- Charles Pinter, *A Book of Abstract Algebra* (2. baskı), Bölüm 5, 11 ve 13: alt gruplar, devirli gruplar, yan kümeler ve Lagrange teoremi.
- Joseph Gallian, *Contemporary Abstract Algebra* (10. baskı), Bölüm 4 ve 7.
- Ronald Rivest, Adi Shamir & Leonard Adleman, "A Method for Obtaining Digital Signatures and Public-Key Cryptosystems", *Communications of the ACM* 21(2), 1978.
- Dan Boneh & Victor Shoup, *A Graduate Course in Applied Cryptography* (ücretsiz): RSA'nın doğru kullanımı ve dolgu şemaları.

**Sıradaki ders:** Halkalar. Toplama ve çarpmanın birlikte yaşadığı yapı; bilgisayar tamsayısının $\mathbb{Z}/2^n\mathbb{Z}$ halkası olması ve derleyicinin bunu kullanması.
