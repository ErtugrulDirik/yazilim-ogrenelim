---
title: "6.21 Gruplar"
description: "Soyut cebire giriş: ikili işlem ve kapalılık; grup aksiyomları (birleşme, birim, ters) ve değişmeli gruplar; örnekler ve karşı örnekler (Z, Z/nZ toplama, (Z/nZ)* çarpma, bit desenlerinde XOR, permütasyon grubu S₃); birimin ve tersin tekliği, (ab)⁻¹ = b⁻¹a⁻¹ ve sadeleştirme; Cayley tablosunun Latin karesi olması; sonlu bir işlem tablosunu okuyup grup aksiyomlarını denetleyen ve S₃'ün tablosunu üreten C programı; izomorfizm."
---

Bu fazda şimdiye kadar birbirine çok benzeyen yapılarla karşılaştık:

- Tamsayılarda toplama: $a + 0 = a$, her $a$'nın tersi $-a$.
- Mod $n$ toplama (Ders 6.18): aynı kurallar, ama sonlu.
- Mod $p$ çarpma (Ders 6.19): birim 1, her sıfır olmayan sınıfın tersi var.
- Bit desenlerinde XOR (Ders 5.1): birim 0, her desen kendi tersi.
- Birebir örten fonksiyonların bileşkesi (Ders 6.9): birim $\text{id}$, ters $f^{-1}$.

Beşinde de aynı üç kural geçerli ve Fermat teoreminin kanıtı (Ders 6.20) sadece bu kuralları kullandı. Matematikçilerin 19. yüzyılda yaptığı şey, bu ortak yapıya bir ad vermek ve teoremleri **bir kez**, bütün örnekler için birden kanıtlamaktı. Bu yapı **grup** ve bu fikir, soyut cebirin başlangıcı. Programcı için tanıdık bir hareket: beş benzer fonksiyonu bir arayüzün arkasına almak.

---

## 1. Tanım

$G$ bir küme, $\ast$ da $G$ üzerinde bir **ikili işlem** olsun: her $a, b \in G$ için $a \ast b \in G$. (Sonucun $G$'de kalması **kapalılık**; bir işlemin $G \times G \to G$ bir fonksiyon olması demek, Ders 6.9.)

$(G, \ast)$ şu üç aksiyomu sağlıyorsa bir **grup**tur:

1. **Birleşme**: $(a \ast b) \ast c = a \ast (b \ast c)$
2. **Birim**: bir $e \in G$ vardır ki her $a$ için $e \ast a = a \ast e = a$
3. **Ters**: her $a$ için bir $a^{-1} \in G$ vardır ki $a \ast a^{-1} = a^{-1} \ast a = e$

Ayrıca her $a, b$ için $a \ast b = b \ast a$ ise grup **değişmeli** (abelian, Niels Abel'den) denir. Değişme bir aksiyom **değil**; birçok önemli grup değişmeli değil.

İşlemi çoğu zaman çarpma gibi yazıyoruz ($ab$, birim $1$, ters $a^{-1}$, $a^n = a \cdots a$); değişmeli gruplarda bazen toplama gibi ($a + b$, birim $0$, ters $-a$, $na$).

---

## 2. Örnekler ve karşı örnekler

| Yapı | Grup mu? | Neden |
| --- | --- | --- |
| $(\mathbb{Z}, +)$ | evet, değişmeli | birim 0, ters $-a$ |
| $(\mathbb{N}, +)$ | **hayır** | $3$'ün tersi ($-3$) $\mathbb{N}$'de yok |
| $(\mathbb{Z}, \cdot)$ | **hayır** | 2'nin tersi ($\frac12$) $\mathbb{Z}$'de yok |
| $(\mathbb{Q} \setminus \{0\}, \cdot)$ | evet, değişmeli | sıfırı çıkarmak şart |
| $(\mathbb{Z}/n\mathbb{Z}, +)$ | evet, değişmeli | Ders 6.18 |
| $(\mathbb{Z}/n\mathbb{Z}, \cdot)$ | **hayır** | 0'ın tersi yok |
| $((\mathbb{Z}/n\mathbb{Z})^*, \cdot)$ | evet, değişmeli | $n$ ile aralarında asal sınıflar; Ders 6.19, $\varphi(n)$ eleman |
| ($k$ bitlik desenler, XOR) | evet, değişmeli | birim 0, $a^{-1} = a$ |
| (`uint32_t`, `+`) | evet, değişmeli | $\mathbb{Z}/2^{32}\mathbb{Z}$ |
| (`int32_t`, `+`) | **C'de hayır** | taşma tanımsız; matematik olarak $\mathbb{Z}/2^{32}$, ama dil bunu söz vermiyor |
| (`double`, `+`) | **hayır** | birleşme yok: `(1e20 + -1e20) + 1 = 1`, `1e20 + (-1e20 + 1) = 0` |
| ($n$ elemanın permütasyonları, $\circ$) | evet, $n \ge 3$ için değişmeli **değil** | $S_n$, simetrik grup; $n!$ eleman |
| (string'ler, birleştirme) | **hayır** | birim `""` var, ama ters yok ("abc"yi geri alan string yok); bu bir **monoid** |

Son iki satırın dersi: kayan nokta toplaması **birleşmeli değil** (Ders 3.14). Derleyici `(a + b) + c`'yi `a + (b + c)`'ye çeviremiyor, sonuç değişebilir; bu yüzden `-ffast-math` olmadan kayan nokta döngüleri vektörleştirilemiyor (Faz 11). Tamsayı toplaması ise bir grup olduğu için derleyici toplama sırasını istediği gibi değiştirebiliyor. Cebirsel yapıyı bilmek, hangi optimizasyonun **geçerli** olduğunu bilmek.

---

## 3. İlk teoremler

Bu teoremler sadece aksiyomlardan çıkıyor; dolayısıyla yukarıdaki her grup için geçerli.

**Teorem.** Birim tektir.

**Kanıt.** $e$ ve $e'$ iki birim olsun. $e = e \ast e' = e'$ (ilk eşitlik $e'$'nin birim olmasından, ikincisi $e$'nin). $\blacksquare$

**Teorem.** Her elemanın tersi tektir.

**Kanıt.** $b$ ve $c$, $a$'nın iki tersi olsun. $b = b \ast e = b \ast (a \ast c) = (b \ast a) \ast c = e \ast c = c$. $\blacksquare$

Ortadaki adım birleşmeyi kullanıyor; birleşme olmasa teklik bozulabilir.

**Teorem (sadeleştirme).** $a \ast b = a \ast c$ ise $b = c$.

**Kanıt.** Soldan $a^{-1}$ ile çarp ve birleşmeyi kullan. $\blacksquare$

Ders 6.20'deki Fermat kanıtında "$a$ ile çarpma birebir" dedik; bu teoremin $(\mathbb{Z}/p\mathbb{Z})^*$'daki hali.

**Teorem.** $(a \ast b)^{-1} = b^{-1} \ast a^{-1}$.

**Kanıt.** $(a \ast b) \ast (b^{-1} \ast a^{-1}) = a \ast (b \ast b^{-1}) \ast a^{-1} = a \ast a^{-1} = e$; tersin tekliğiyle bitti. $\blacksquare$

Ders 6.9'daki çorap–ayakkabı kuralı. Değişmeli gruplarda sıra önemsiz; değişmeli olmayanlarda ters sıra **şart**.

---

## 4. Cayley tablosu

Sonlu bir grubun işlemini bir tabloyla tam olarak verebiliriz: $i$'inci satır, $j$'inci sütun $= a_i \ast a_j$. Arthur Cayley'den adını alıyor. Ders 6.9'daki sonlu fonksiyonları dizi olarak tuttuğumuz gibi, sonlu bir işlemi iki boyutlu bir dizi olarak tutuyoruz:

```c
#define MAXN 32

// sonlu bir ikili islem: tablo[i][j] = i * j, elemanlar 0..n-1
typedef struct { int n; int t[MAXN][MAXN]; const char *name[MAXN]; } table;
```

Aksiyomları Ders 6.2'deki gibi $\forall$ ve $\exists$ döngüleriyle denetliyoruz:

```c
// grup aksiyomlarini denetler; birim elemani *e'ye yazar
static bool is_group(const table *g, int *e, bool *abelian) {
    int n = g->n;
    for (int a = 0; a < n; a++)                         // birlesme
        for (int b = 0; b < n; b++)
            for (int c = 0; c < n; c++)
                if (g->t[g->t[a][b]][c] != g->t[a][g->t[b][c]]) return false;
    *e = -1;
    for (int c = 0; c < n && *e < 0; c++) {             // birim
        bool ok = true;
        for (int a = 0; a < n; a++) ok = ok && g->t[c][a] == a && g->t[a][c] == a;
        if (ok) *e = c;
    }
    if (*e < 0) return false;
    for (int a = 0; a < n; a++) {                       // ters
        bool found = false;
        for (int b = 0; b < n; b++) found = found || (g->t[a][b] == *e && g->t[b][a] == *e);
        if (!found) return false;
    }
    *abelian = true;
    for (int a = 0; a < n; a++)
        for (int b = 0; b < n; b++) *abelian = *abelian && g->t[a][b] == g->t[b][a];
    return true;
}
```

Birleşme denetimi $n^3$; kapalılık tablo temsilinde kendiliğinden (her hücre $0..n-1$'de). Tabloları doldurup deneyelim:

```c
for (int i = 0; i < 6; i++) for (int j = 0; j < 6; j++) g.t[i][j] = (i + j) % 6;   // Z/6, +
for (int i = 0; i < 6; i++) for (int j = 0; j < 6; j++) g.t[i][j] = (i * j) % 6;   // Z/6, *
// (Z/7)*: elemanlar 1..6, indeks 0..5
for (int i = 0; i < 6; i++) for (int j = 0; j < 6; j++) g.t[i][j] = ((i + 1) * (j + 1)) % 7 - 1;
for (int i = 0; i < 4; i++) for (int j = 0; j < 4; j++) g.t[i][j] = i ^ j;          // 2 bit, XOR
```

```
    |   1   2   3   4   5   6
----+------------------------
  1 |   1   2   3   4   5   6
  2 |   2   4   6   1   3   5
  3 |   3   6   2   5   1   4
  4 |   4   1   5   2   6   3
  5 |   5   3   1   6   4   2
  6 |   6   5   4   3   2   1
Z/6, +: grup, birim 0, degismeli
Z/6, *: grup DEGIL
(Z/7)*, *: grup, birim 1, degismeli
{0..3}, xor: grup, birim 0, degismeli
```

$(\mathbb{Z}/7\mathbb{Z})^*$ tablosunda bir desen: **her satırda ve her sütunda her eleman tam bir kez** geçiyor. Bu bir **Latin karesi** ve her grup tablosu öyle: $a$'nın satırında $b$ ve $c$ aynı sonucu verseydi sadeleştirme teoremiyle $b = c$ olurdu (satır birebir), ve sonlu bir kümede birebir = örten. Bir sudoku, $3 \times 3$ bloklarıyla birlikte bir Latin karesi.

Tablo simetrikse (köşegene göre ayna) grup değişmeli; $(\mathbb{Z}/7)^*$ öyle.

### Değişmeli olmayan bir grup: $S_3$

$\{0, 1, 2\}$'nin altı permütasyonu, bileşke işlemiyle. Her permütasyonu görüntülerinin dizgisiyle adlandıralım: `120`, $0 \mapsto 1$, $1 \mapsto 2$, $2 \mapsto 0$ demek.

```c
for (int x = 0; x < 3; x++) r[x] = perm[i][perm[j][x]];   // (i o j)(x) = i(j(x))
```

```
    | 012 021 102 120 201 210
----+------------------------
012 | 012 021 102 120 201 210
021 | 021 012 201 210 102 120
102 | 102 120 012 021 210 201
120 | 120 102 210 201 012 021
201 | 201 210 021 012 120 102
210 | 210 201 120 102 021 012
S3, bilesim: grup, birim 012, degismeli DEGIL
```

`021` ∘ `102` = `201`, ama `102` ∘ `021` = `120`. İki değiş-tokuşu farklı sırayla yapmak farklı sonuç veriyor. $S_3$, değişmeli olmayan en küçük grup. Bir Rubik küpünün hamleleri de değişmeli olmayan bir grup (yaklaşık $4.3 \cdot 10^{19}$ eleman) ve "önce sağ yüzü sonra üst yüzü çevir" ile tersi aynı şey değil.

Permütasyonlar programlamada her yerde: bir diziyi sıralamak bir permütasyon uygulamak, Ders 5.11'deki bit yeniden düzenlemeleri bitlerin permütasyonları, bir derleyicinin komut zamanlaması komutların bir permütasyonunu seçmek. Ve **her** sonlu grup, bir permütasyon grubunun içinde bir kopya olarak var (Cayley teoremi): her eleman, Cayley tablosundaki satırı olan permütasyonla temsil ediliyor.

---

## 5. İzomorfizm

İki grup bazen "aynı" görünüyor. Mod 4 toplaması $\{0, 1, 2, 3\}$ ile mod 5 çarpmasının $\{1, 2, 3, 4\}$'ü:

| $+_4$ | 0 | 1 | 2 | 3 |
| --- | --- | --- | --- | --- |
| **0** | 0 | 1 | 2 | 3 |
| **1** | 1 | 2 | 3 | 0 |
| **2** | 2 | 3 | 0 | 1 |
| **3** | 3 | 0 | 1 | 2 |

| $\cdot_5$ | 1 | 2 | 4 | 3 |
| --- | --- | --- | --- | --- |
| **1** | 1 | 2 | 4 | 3 |
| **2** | 2 | 4 | 3 | 1 |
| **4** | 4 | 3 | 1 | 2 |
| **3** | 3 | 1 | 2 | 4 |

İkinci tablonun elemanlarını $1, 2, 4, 3$ sırasıyla dizince ($2^0, 2^1, 2^2, 2^3$) iki tablo **aynı desene** sahip. $\phi(k) = 2^k \bmod 5$ eşlemesi birebir örten ve $\phi(a + b) = \phi(a) \cdot \phi(b)$: toplamayı çarpmaya taşıyor.

$\phi : G \to H$ birebir örten ve $\phi(a \ast b) = \phi(a) \star \phi(b)$ ise $G$ ile $H$ **izomorf**tur: aynı grup, farklı adlarla. Ders 6.20'deki Çin kalan teoremi bir izomorfizmdi ($\mathbb{Z}/15 \cong \mathbb{Z}/3 \times \mathbb{Z}/5$). Logaritma da: $\log(ab) = \log a + \log b$, pozitif gerçel sayıların çarpma grubunu gerçel sayıların toplama grubuna taşıyor; sürgülü hesap cetvelinin çalışma ilkesi.

Programcı için izomorfizm, **veri temsilini değiştirmek**: aynı yapıyı, işlemi ucuz olan bir temsilde hesapla, sonra geri çevir. Ders 6.24'te $GF(2^8)$'de çarpmayı bu yolla, log tablolarıyla, toplamaya çevireceğiz.

---

## Alıştırmalar

**1** – Şunlar grup mu? Değilse hangi aksiyom bozuluyor? (a) $(\{-1, 1\}, \cdot)$ (b) $(\mathbb{Z}, -)$ (çıkarma) (c) $(\mathbb{Z}/8\mathbb{Z}, \cdot)$'nin $\{1, 3, 5, 7\}$ alt kümesi (d) $(\mathbb{R}, \max)$ (e) 3 bitlik desenler, `&`

**2** – $(\mathbb{Z}/8\mathbb{Z})^* = \{1, 3, 5, 7\}$ ile 2 bitlik XOR grubunun izomorf olduğunu göster: Cayley tablolarını programla yazdır, bir eşleme bul. $(\mathbb{Z}/5\mathbb{Z})^*$ ile izomorf mu? (İpucu: her elemanın karesine bak.)

**3** – `is_group`'a bir tablonun Latin karesi olup olmadığını denetleyen bir fonksiyon ekle. Her Latin karesi bir grup tablosu mu? 3×3 bir Latin karesi bul ve birleşmeyi denetle; 5×5 için birleşmeli olmayan bir Latin karesi bulabilir misin?

**4** – $S_4$'ün (24 eleman) Cayley tablosunu üret. Kaç elemanın kendisiyle bileşkesi birim (yani $a^2 = e$)? Bu elemanlar hangi permütasyonlar?

**5** – Sabit bir $g$ için $L_g(x) = g \ast x$ fonksiyonunun $G$ üzerinde bir permütasyon olduğunu göster. $g \mapsto L_g$ eşlemesi neden $G$'den $S_{|G|}$'ye "işlemi koruyan" bir fonksiyon? (Cayley teoremi.)

<details>
<summary>Cevaplar</summary>

**1** – (a) Evet, değişmeli; birim 1, her eleman kendi tersi. $\mathbb{Z}/2$ ile izomorf ($-1 \leftrightarrow 1$, işaretin çarpımı paritenin toplamı). (b) Hayır: birleşme yok ($(5 - 3) - 1 = 1$, $5 - (3 - 1) = 3$), birim de yok ($0 - a \ne a$). (c) Evet: $3 \cdot 3 = 9 \equiv 1$, $5 \cdot 5 = 25 \equiv 1$, $7 \cdot 7 = 49 \equiv 1$, $3 \cdot 5 = 15 \equiv 7$; kapalı, her eleman kendi tersi. Bu $(\mathbb{Z}/8)^*$. (d) Hayır: birleşmeli, ama birim ($\max(e, a) = a$ her $a$ için) $-\infty$ olmalı ve $\mathbb{R}$'de yok; tersler de yok. (e) Hayır: birim 7 (`111`), ama `0 & x = 0`, 0'ın tersi yok. `&` ve `|` bir monoid; Ders 6.8'deki kafes işlemleri.

**2** – $(\mathbb{Z}/8)^*$'da her eleman kendi tersi; XOR'da da. Eşleme: $1 \to 00$, $3 \to 01$, $5 \to 10$, $7 \to 11$. Kontrol: $3 \cdot 5 = 7 \leftrightarrow 01 \oplus 10 = 11$. ✓ $(\mathbb{Z}/5)^*$ ile izomorf **değil**: orada $2^2 = 4 \ne 1$; $a^2 = e$ olan elemanların sayısı farklı (birinde 4, öbüründe 2: $1, 4$). İzomorfizm bu sayıyı korumak zorunda. İkisi de 4 elemanlı ama farklı gruplar: $\mathbb{Z}/2 \times \mathbb{Z}/2$ ve $\mathbb{Z}/4$.

**3** –

```c
static bool is_latin(const table *g) {
    for (int i = 0; i < g->n; i++) {
        unsigned row = 0, col = 0;
        for (int j = 0; j < g->n; j++) { row |= 1u << g->t[i][j]; col |= 1u << g->t[j][i]; }
        if (row != (1u << g->n) - 1 || col != (1u << g->n) - 1) return false;
    }
    return true;
}
```

Satırdaki değerlerin kümesini Ders 6.5'teki gibi bitmask'te topluyoruz; tam küme olmalı. Her Latin karesi grup değil. 3×3'te her Latin karesi (satır ve sütunları uygun sıraya koyunca) $\mathbb{Z}/3$, ama birim bulunmayabilir (örneğin $t[i][j] = (2i + 2j) \bmod 3$: Latin, değişmeli, ama birleşmeli değil; programla dene). 5×5'te $t[i][j] = (2i + 3j) \bmod 5$ gibi tablolar Latin ama birleşmeli değil. Latin karesi "sadeleştirme" demek; grup bunun yanında birleşme ve birim istiyor. (Birleşmesiz Latin karelerine **quasigroup** denir.)

**4** – $S_4$'te $a^2 = e$ olan 10 eleman var: birim (1), tek bir değiş-tokuş (transpozisyon, $\binom42 = 6$ tane: `1023` gibi) ve iki ayrık değiş-tokuş (3 tane: `1032`, `2301`, `3210`). Döngü yapısına göre sayma: $a^2 = e$ ancak her döngü 1 ya da 2 uzunluktaysa.

**5** – $L_g$ birebir: $gx = gy \Rightarrow x = y$ (sadeleştirme). Sonlu kümede birebir = örten, dolayısıyla bir permütasyon. Tersi $L_{g^{-1}}$. İşlemi korur: $L_{gh}(x) = (gh)x = g(hx) = L_g(L_h(x))$, yani $L_{gh} = L_g \circ L_h$ (birleşmeden). $g \ne h$ ise $L_g(e) = g \ne h = L_h(e)$, birebir. Demek $G$, $S_{|G|}$'nin içinde bir kopya olarak duruyor: Cayley teoremi. $L_g$, Cayley tablosunun $g$ satırı.

</details>

---

## Kaynaklar

- Charles Pinter, *A Book of Abstract Algebra* (2. baskı), Bölüm 2–5 ve 8: işlemler, grup aksiyomları, temel teoremler, permütasyon grupları. Bu fazın soyut cebir derslerinin ana kaynağı.
- Joseph Gallian, *Contemporary Abstract Algebra* (10. baskı), Bölüm 2 ve 5–6: gruplar, permütasyon grupları, izomorfizm.
- Arthur Cayley, "On the theory of groups, as depending on the symbolic equation θⁿ = 1" (1854): tablo gösterimi ve soyut grup kavramı.

**Sıradaki ders:** Alt grup, devirli grup, Lagrange. Bir elemanın mertebesi, Lagrange teoremi, ve RSA'nın neden çalıştığı.
