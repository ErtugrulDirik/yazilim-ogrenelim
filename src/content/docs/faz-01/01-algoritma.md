---
title: "1.1 Algoritma ve problem çözme"
description: "Algoritmanın beş özelliği, problemi girdi ve çıktı olarak tanımlama, sözde kod ve Pólya'nın dört adımı."
---

Bu derste de kod yazmıyoruz; kağıt ve kalem yeterli. Beş bölüm var:

1. Algoritma nedir?
2. Bir algoritmanın beş özelliği
3. Problemi tanımlamak: girdi, çıktı, koşul
4. Sözde kod
5. Problem çözmenin dört adımı

Her bölümün sonunda alıştırmalar var. Cevaplar kapalı kutularda; önce kendin çöz.

---

## 1. Algoritma nedir?

**Algoritma**, bir problemi çözmek için izlenen, sonlu sayıda ve açıkça tanımlanmış adımlar dizisidir.

Kelime, 9. yüzyılda Bağdat'ta yaşamış matematikçi **el-Harezmî**'nin adından gelir. Onun hint rakamlarıyla hesap yapmayı anlatan kitabı Latinceye *Algoritmi de numero Indorum* ("Harezmî, hint sayıları üzerine") adıyla çevrildi; "algoritma" kelimesi bu başlıktaki *Algoritmi*'den türedi.

**Yemek tarifi bir algoritma mı?** İlk bakışta öyle görünür: malzemeler var, adımlar var, sonunda bir yemek çıkıyor. Ama tarifte şu tür cümleler olur:

- "Tuzunu kararınca ekle."
- "Kıvamını alana kadar karıştır."

"Kararınca" ne kadardır? "Kıvam" ne zaman alınmış sayılır? İki farklı kişi bu adımları farklı uygular ve farklı sonuç alır. Bilgisayar ise "kararınca"yı anlamaz; ona her adımı tek bir anlama gelecek şekilde söylemek zorundayız. Algoritmayı tariften ayıran şey budur.

**Bilgisayar sadece algoritma çalıştırır.** Faz 0'da bilgisayarın bir talimat listesini, yani programı izlediğini gördük. Program, bir algoritmanın bilgisayarın anlayacağı dille yazılmış halidir. Önce algoritmayı kağıtta doğru kurarız, sonra onu bir programlama diline çeviririz. Bu fazın tamamı birinci adım üzerine.

### Alıştırma

**1.1** Aşağıdakilerden hangileri bir bilgisayarın uygulayabileceği kadar açık bir talimattır?

- a) "Sayıyı 2 ile çarp."
- b) "Odayı biraz toparla."
- c) "Listedeki en küçük sayıyı bul."
- d) "Güzel bir şiir seç."

<details>
<summary>Cevap</summary>

**a** ve **c** açıktır: herkes aynı girdiyle aynı sonucu bulur. **b** ("biraz" ne kadar?) ve **d** ("güzel" kime göre?) kişiden kişiye değişir; bilgisayar bunları uygulayamaz.

</details>

---

## 2. Bir algoritmanın beş özelliği

Donald Knuth, *The Art of Computer Programming* kitabının ilk bölümünde bir algoritmanın taşıması gereken beş özelliği sayar:

| Özellik | Anlamı | Bozulursa ne olur? |
| --- | --- | --- |
| **Sonluluk** | Sonlu sayıda adımdan sonra mutlaka biter. | Algoritma sonsuza kadar çalışır, cevap hiç gelmez. |
| **Kesinlik** | Her adım tek bir anlama gelir. | Aynı girdiyle farklı kişiler farklı şeyler yapar. |
| **Girdi** | Sıfır ya da daha fazla girdi alır. | — (girdisiz algoritma da olabilir) |
| **Çıktı** | En az bir çıktı üretir. | Algoritma çalışır ama kimse sonucu göremez. |
| **Etkinlik** | Her adım, kağıt kalemle sonlu sürede ve tam olarak yapılabilecek kadar basittir. | Adım "yapılabilir" görünür ama gerçekte yapılamaz. |

Üç örnekle açalım.

**Sonluluk.** Şu talimatlara bak:

```
1. x ← 1
2. x ← x + 1
3. 2. adıma git
```

Her adım kesin, her adım yapılabilir. Ama hiçbir zaman durmaz. Bu bir algoritma değildir.

**Etkinlik.** "π sayısını 2 ile çarp ve sonucu yaz" talimatı kesin görünür: ne yapılacağı belli. Ama π'nin basamakları sonsuzdur; bu çarpmayı tam olarak, sonlu sürede yapamazsın. Faz 0'da 0,1'in ikilikte sonsuz olduğunu görmüştük; bilgisayarın bu tür sayılarla neden dikkatli çalışmak zorunda olduğunun kökü burada.

**Girdi sıfır olabilir.** "1. 5 yaz. 2. Dur." hiç girdi almaz, ama sonlu, kesin, yapılabilir ve bir çıktısı var. Geçerli bir algoritmadır. Çıktı ise en az bir tane olmak zorundadır: sonucunu kimseye vermeyen bir algoritma, hiçbir problemi çözmüş olmaz.

### Alıştırmalar

Aşağıdaki talimat listelerinin her biri Knuth'un beş özelliğinden hangisini bozuyor? Bozmuyorsa "geçerli" de.

**2.1**
```
1. Bir sayı oku.
2. Sayıyı 2 ile çarp.
3. Dur.
```

**2.2**
```
1. Bir sayı oku.
2. Sayıya yeterince büyük bir sayı ekle.
3. Sonucu yaz.
```

**2.3**
```
1. n ← 10
2. n sıfır olduğu sürece n'den 1 çıkar.
3. n'yi yaz.
```

**2.4**
```
1. n ← 10
2. n sıfırdan farklı olduğu sürece n'ye 1 ekle.
3. n'yi yaz.
```

**2.5**
```
1. 1/3'ü ondalık olarak, bütün basamaklarıyla yaz.
```

<details>
<summary>Cevaplar</summary>

**2.1** **Çıktı** yok. Sayı çarpılıyor ama sonuç hiçbir yere yazılmıyor.

**2.2** **Kesinlik** bozuk. "Yeterince büyük" hangi sayı? Her okuyan başka bir sayı seçer.

**2.3** **Geçerli.** n = 10 olduğu için "n sıfır olduğu sürece" koşulu en baştan yanlıştır; 2. adım hiç çalışmaz, 3. adım 10 yazar ve algoritma biter. Garip görünse de beş özelliğin hepsini taşır.

**2.4** **Sonluluk** bozuk. n 10'dan başlayıp hep artar, hiçbir zaman 0 olmaz; algoritma bitmez. (Faz 0'daki 8 bit taşmasını hatırlarsan, gerçek bir bilgisayarda bu sayı bir gün "dönüp" 0'a gelebilir. Bunu Faz 3'te göreceğiz.)

**2.5** **Sonluluk** ve **etkinlik** bozuk. 1/3 = 0,333…; basamaklar sonsuza kadar sürer, iş hiç bitmez.

</details>

---

## 3. Problemi tanımlamak: girdi, çıktı, koşul

Bir problemi çözmeye başlamadan önce **ne çözdüğünü** tam olarak yazmalısın. Bunun için üç soru sorulur:

- **Girdi:** Elimde ne var? Hangi değerler, hangi türde?
- **Çıktı:** Sonunda ne üretmem gerekiyor?
- **Koşul:** Girdiler hangi sınırlar içinde? Çıktı ile girdi arasındaki ilişki ne?

**Örnek: vücut kitle indeksi.**

- **Girdi:** kilo (kg cinsinden, sıfırdan büyük) ve boy (metre cinsinden, sıfırdan büyük).
- **Çıktı:** vücut kitle indeksi değeri ve bu değerin hangi gruba girdiği.
- **Koşul:** vücut kitle indeksi = kilo / boy². Gruplar: 18,5'in altı zayıf; 18,5 ve üstü ama 25'in altı normal; 25 ve üstü ama 30'un altı fazla kilolu; 30 ve üstü obez. (Sınırları böyle yazmak kesinliğin gereğidir: "18,5 ile 25 arası" deseydik, tam 25 olan biri hangi grupta olurdu?)

Koşul kısmındaki "sıfırdan büyük" ifadesi süs değildir. Boy 0 girilirse sıfıra bölme olur ve hesap anlamsızlaşır. Problemi tanımlarken bu sınırları yazmazsan, algoritmayı kurarken de unutursun.

**Örnek: en büyük sayı.**

- **Girdi:** n tane tamsayı: a₁, a₂, …, aₙ. Koşul: n ≥ 1.
- **Çıktı:** bu sayıların en büyüğü.

n ≥ 1 koşulu neden var? Çünkü hiç sayı yoksa "en büyüğü" diye bir şey de yoktur. Boş liste, problemin tanımında baştan dışarıda bırakılmış olur.

**Uç durumlar.** Sınırların hemen üstündeki ve altındaki girdilere **uç durum** denir: boş liste, tek elemanlı liste, sıfır, çok büyük sayı… Hataların çoğu buralarda saklanır. Problemi tanımlarken uç durumları da not et.

### Alıştırmalar

Aşağıdaki problemlerin girdisini, çıktısını ve koşulunu yaz. En az bir uç durum belirt.

**3.1** İki tamsayıdan büyük olanı bulmak.

**3.2** Bir yılın artık yıl olup olmadığını bulmak. (Kural: 4'e bölünen yıllar artık yıldır; ama 100'e bölünüp 400'e bölünmeyenler artık yıl değildir.)

**3.3** Bir sınıftaki öğrencilerin not ortalamasını bulmak.

<details>
<summary>Cevaplar</summary>

**3.1** Girdi: a ve b tamsayıları. Çıktı: a ile b'den büyük olanı. Koşul: çıktı a ≥ b ise a, değilse b. Uç durum: a = b. İkisi eşitse hangisini döndürdüğün fark etmez, ama tanımda bunu düşünmüş olmalısın.

**3.2** Girdi: yıl (pozitif tamsayı). Çıktı: "evet" ya da "hayır". Koşul: yıl 400'e bölünüyorsa evet; değilse ve 100'e bölünüyorsa hayır; değilse ve 4'e bölünüyorsa evet; hiçbiri değilse hayır. Uç durumlar: 1900 (4'e ve 100'e bölünür ama 400'e bölünmez → hayır), 2000 (400'e bölünür → evet).

**3.3** Girdi: n öğrencinin notları (her biri 0 ile 100 arasında). Çıktı: notların toplamının n'ye bölümü. Koşul: n ≥ 1. Uç durum: n = 0. Sınıfta hiç öğrenci yoksa sıfıra bölme olur; bu durumda ne yapılacağına önceden karar verilmelidir.

</details>

---

## 4. Sözde kod

Algoritmayı Türkçe cümlelerle yazmak hem uzun hem belirsizdir. Doğrudan bir programlama diliyle yazmak ise henüz erken. Arada bir yol var: **sözde kod**. Kurallı, kısa ve her adımı tek anlama gelen bir yazım.

Bu kitapta şu yazımı kullanacağız:

| Yazım | Anlamı | Örnek |
| --- | --- | --- |
| `x ← değer` | x'e değeri ver (**atama**) | `x ← 5` |
| `a ÷ b` | Tamsayı bölmesi; kalan atılır | 7 ÷ 2 = 3 |
| `a mod b` | Bölmeden kalan | 7 mod 2 = 1 |
| `=`, `≠`, `<`, `≤`, `>`, `≥` | Karşılaştırma; sonuç doğru ya da yanlıştır | `x = 0` |
| `EĞER koşul İSE … DEĞİLSE …` | Karar: koşula göre iki yoldan birini seç | |
| `koşul OLDUĞU SÜRECE: …` | Döngü: koşul doğru oldukça tekrarla, önce koşula bak | |
| `TEKRARLA … koşul OLANA KADAR` | Döngü: önce bir kez yap, sonra koşula bak | |
| `DÖNDÜR x` | x'i sonuç olarak ver ve bitir | |

Bir adımın hangi bloğa ait olduğunu **girinti** gösterir: bir EĞER ya da döngünün altındaki adımlar sağa kaydırılarak yazılır.

**Neden `=` değil de `←`?** `x ← x + 1` "x'in eski değerine 1 ekle, sonucu x'e koy" demektir. Matematikte `x = x + 1` ise yanlış bir ifadedir: hiçbir sayı kendisinin bir fazlasına eşit olamaz. Atama ile eşitliği karıştırmamak için iki ayrı işaret kullanıyoruz. Faz 2'de C'nin bu iki anlamı hangi işaretlerle yazdığını göreceğiz.

**Örnek: en büyük sayı.** Bölüm 3'te tanımladığımız problem:

```
ALGORİTMA EnBüyük
GİRDİ: a₁, a₂, …, aₙ  (n ≥ 1)
ÇIKTI: en büyük eleman

enb ← a₁
i ← 2
i ≤ n OLDUĞU SÜRECE:
    EĞER aᵢ > enb İSE
        enb ← aᵢ
    i ← i + 1
DÖNDÜR enb
```

Fikir basit: ilk sayıyı "şimdiye kadarki en büyük" kabul et, sonra kalan sayılara tek tek bak; daha büyüğünü görürsen onu aklında tut.

Girdi 4, 9, 2, 7 için adım adım:

| i | aᵢ | aᵢ > enb? | enb |
| --- | --- | --- | --- |
| — | — | — | 4 |
| 2 | 9 | evet | 9 |
| 3 | 2 | hayır | 9 |
| 4 | 7 | hayır | 9 |

i = 5 olunca `i ≤ n` yanlış olur, döngü biter ve 9 döndürülür. Bu tür tablolara Faz 0'da *iz sürme tablosu* demiştik; Ders 1.3'te bu konuyu derinleştireceğiz.

### Alıştırmalar

**4.1** Bir sayının çift mi tek mi olduğunu bulan sözde kodu yaz.

**4.2** İki sayıdan büyüğünü döndüren sözde kodu yaz (Alıştırma 3.1).

**4.3** Aşağıdaki sözde kod 5 girdisi için ne döndürür? Bu algoritma genel olarak ne hesaplıyor?

```
ALGORİTMA Gizem
GİRDİ: n  (n ≥ 1)

s ← 0
i ← 1
i ≤ n OLDUĞU SÜRECE:
    s ← s + i
    i ← i + 1
DÖNDÜR s
```

<details>
<summary>Cevaplar</summary>

**4.1**
```
ALGORİTMA ÇiftMi
GİRDİ: n  (tamsayı)
ÇIKTI: "çift" ya da "tek"

EĞER n mod 2 = 0 İSE
    DÖNDÜR "çift"
DEĞİLSE
    DÖNDÜR "tek"
```
Faz 0'dan bir bağlantı: n mod 2, n'nin ikilikteki en sağdaki bitidir. Çift sayıların son biti 0, tek sayılarınki 1'dir.

**4.2**
```
ALGORİTMA Büyük
GİRDİ: a, b
ÇIKTI: a ile b'den büyük olanı

EĞER a ≥ b İSE
    DÖNDÜR a
DEĞİLSE
    DÖNDÜR b
```

**4.3** 15 döndürür.

| i | s |
| --- | --- |
| — | 0 |
| 1 | 1 |
| 2 | 3 |
| 3 | 6 |
| 4 | 10 |
| 5 | 15 |

Algoritma 1'den n'e kadar olan sayıların toplamını hesaplar: 1 + 2 + … + n.

</details>

---

## 5. Problem çözmenin dört adımı

Macar matematikçi George Pólya, *How to Solve It* kitabında problem çözmeyi dört adıma ayırır:

1. **Problemi anla.** Girdi ne, çıktı ne, koşul ne? Birkaç örneği elle çöz.
2. **Plan yap.** Daha önce benzer bir problem gördün mü? Problemi daha küçük parçalara bölebilir misin?
3. **Planı uygula.** Algoritmayı adım adım yaz ve her adımı kontrol et.
4. **Geriye bak.** Sonuç doğru mu? Uç durumlarda çalışıyor mu? Bu yöntem başka bir problemde de işe yarar mı?

Çoğu kişi doğrudan 3. adıma atlar, 4. adımı da hiç yapmaz. Hataların büyük kısmı tam olarak bu iki boşluktan çıkar. Dört adımı bir örnek üzerinde tek tek uygulayalım.

**Problem: bir sayının kaç basamaklı olduğunu bulmak.**

**1. Anla.**

- Girdi: n, sıfır ya da pozitif bir tamsayı.
- Çıktı: n'nin onluk sistemde kaç basamaklı olduğu.
- Elle birkaç örnek: 7 → 1, 2026 → 4, 100 → 3.

**2. Plan yap.** Benzer bir şey gördük mü? Evet: Faz 0'da onluktan ikiliğe çevirirken sayıyı sürekli 2'ye böldük ve sayı 0 olana kadar devam ettik. Her bölme bir basamak üretiyordu. Aynı fikir burada da işler: sayıyı sürekli **10'a** bölersek, her bölme bir basamağı "yer". Kaç kez bölebildiğimizi sayarsak basamak sayısını buluruz.

**3. Uygula.**

```
ALGORİTMA BasamakSayısı
GİRDİ: n  (n ≥ 0)
ÇIKTI: n'nin basamak sayısı

sayaç ← 0
n > 0 OLDUĞU SÜRECE:
    n ← n ÷ 10
    sayaç ← sayaç + 1
DÖNDÜR sayaç
```

2026 ile deneyelim:

| Adım | n | sayaç |
| --- | --- | --- |
| başlangıç | 2026 | 0 |
| 1 | 202 | 1 |
| 2 | 20 | 2 |
| 3 | 2 | 3 |
| 4 | 0 | 4 |

n = 0 olunca döngü biter; sonuç 4. Doğru.

**4. Geriye bak.** Uç durumları dene. n = 7 → bir bölmede 0 olur → 1. Doğru. Peki **n = 0**?

`n > 0` koşulu en baştan yanlış olduğu için döngü hiç çalışmaz ve algoritma **0** döndürür. Ama 0 sayısı bir basamaklıdır! Algoritmada bir hata bulduk ve bunu ancak 4. adım sayesinde gördük.

Düzeltme: bölmeyi **önce bir kez yap**, sonra koşula bak. Sözde koddaki `TEKRARLA … OLANA KADAR` tam bunun için var:

```
sayaç ← 0
TEKRARLA
    n ← n ÷ 10
    sayaç ← sayaç + 1
n = 0 OLANA KADAR
DÖNDÜR sayaç
```

Şimdi n = 0 için: bir kez bölünür (0 ÷ 10 = 0), sayaç 1 olur, koşul sağlanır ve döngü biter. Sonuç 1. Diğer örnekler de eskisi gibi doğru çalışır.

**Geriye bakmanın ikinci yarısı: genelleme.** Bu yöntem başka nerede işe yarar? 10 yerine **2'ye** bölersek, sayının **ikilikte kaç bit** tuttuğunu buluruz. 13 için: 13 → 6 → 3 → 1 → 0, dört bölme, yani 4 bit. Gerçekten de 13 = 1101₂. Bir problemi çözmek, çoğu zaman başka problemlerin de anahtarını verir.

### Alıştırmalar

**5.1** Pólya'nın dört adımını kullanarak bir sayının ikilikteki gösteriminde kaç tane **1** olduğunu bulan algoritmayı yaz. Örnek: 13 = 1101₂ → üç tane 1. (İpucu: Faz 0'daki bölme–kalan yöntemini hatırla.)

**5.2** Yazdığın algoritmayı 0 ve 255 için dene. Sonuçlar doğru mu?

**5.3** BasamakSayısı algoritmasının ilk halini düşün. n = 0 dışında yanlış sonuç verdiği başka bir girdi var mı?

<details>
<summary>Cevaplar</summary>

**5.1**

*Anla.* Girdi: n ≥ 0. Çıktı: n'nin ikilik gösterimindeki 1'lerin sayısı. Örnekler: 13 → 3, 8 = 1000₂ → 1.

*Plan.* Bölme–kalan yöntemi her adımda bir bit verir: n mod 2. Kalan 1 olan adımları sayarsak 1'lerin sayısını buluruz.

*Uygula.*
```
ALGORİTMA BirlerinSayısı
GİRDİ: n  (n ≥ 0)
ÇIKTI: n'nin ikilikteki 1'lerinin sayısı

birler ← 0
n > 0 OLDUĞU SÜRECE:
    EĞER n mod 2 = 1 İSE
        birler ← birler + 1
    n ← n ÷ 2
DÖNDÜR birler
```

13 için iz:

| n | n mod 2 | birler |
| --- | --- | --- |
| 13 | 1 | 1 |
| 6 | 0 | 1 |
| 3 | 1 | 2 |
| 1 | 1 | 3 |
| 0 | — | 3 |

**5.2** n = 0: döngü hiç çalışmaz, sonuç 0. Doğru, çünkü 0'da hiç 1 yoktur. Burada `OLDUĞU SÜRECE` döngüsü doğru seçimdir; BasamakSayısı'ndaki hata bu problemde ortaya çıkmaz. n = 255 = 11111111₂: sekiz bölmenin hepsinde kalan 1'dir, sonuç 8. Doğru.

**5.3** Hayır. n ≥ 1 olan her sayı için döngü en az bir kez çalışır ve doğru sonucu verir; hata yalnızca n = 0'da ortaya çıkar. Bu yüzden uç durumlar ayrıca denenmelidir: "çoğu örnekte çalışıyor" demek "doğru" demek değildir.

</details>

---

## Kaynaklar

- Donald Knuth, *The Art of Computer Programming*, Cilt 1 (3. baskı), §1.1: algoritmanın beş özelliği.
- George Pólya, *How to Solve It*: problem çözmenin dört adımı ve sezgisel yöntemler.

**Sıradaki ders:** Algoritmaları çizmeyi öğreneceğiz: akış diyagramı.
