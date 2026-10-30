---
title: "5.17 Uzay doldurma eğrileri"
description: "İki boyutlu bir koordinatı tek bir sayıya çevirmenin bitlerle yolları: Morton (Z-order) kodu, x ve y'nin bitlerini araya serpiştirerek (bit yayma, Ders 5.11/5.12), encode/decode; Hilbert eğrisinin ardışık noktalarının her zaman komşu olması (Morton'da olmayan özellik); ve iki boyutlu komşuların 1D indekste ne kadar yakın kaldığını ölçerek satır-öncelikli düzenle karşılaştırmak (cache dostu veri düzeni)."
---

İki boyutlu bir koordinatı (örneğin bir resimdeki piksel, bir haritadaki nokta) tek bir sayıya nasıl çeviririz? Ders 4.3'teki satır-öncelikli düzen (`i*COLS + j`) bir yoldu. Bu derste bitlerle kurulan iki alternatif görüyoruz: **Morton kodu** (Z-order) ve **Hilbert eğrisi**. İkisi de bir **uzay doldurma eğrisi** — 2B uzayı tek bir çizgi gibi gezen bir sıralama — ve ikisi de 2B komşuları 1B'de yakın tutarak **önbellek dostu** veri düzenleri sağlıyor. Bu, Ders 5.11'deki bit yayma ve Ders 5.12'deki expand'in güzel bir uygulaması.

İşaretsiz (`unsigned`) koordinatlarla.

---

## 1. Morton kodu: bitleri serpiştir

**Morton kodu** (ya da **Z-order**), `x` ve `y` koordinatlarının bitlerini **araya serpiştirir** (interleave): sonuç `y₀x₀y₁x₁y₂x₂…` gibi, bir `x` biti bir `y` biti. 16-bitlik iki koordinattan 32-bitlik bir Morton kodu:

```c
uint32_t morton_encode(uint16_t x, uint16_t y) {
    uint32_t X = x, Y = y;
    X = (X | (X << 8)) & 0x00FF00FF;    // bitleri aralara yay (Ders 5.11)
    X = (X | (X << 4)) & 0x0F0F0F0F;
    X = (X | (X << 2)) & 0x33333333;
    X = (X | (X << 1)) & 0x55555555;    // X artik tek konumlarda
    Y = (Y | (Y << 8)) & 0x00FF00FF;
    Y = (Y | (Y << 4)) & 0x0F0F0F0F;
    Y = (Y | (Y << 2)) & 0x33333333;
    Y = (Y | (Y << 1)) & 0x55555555;
    return X | (Y << 1);                // X cift konumlar, Y tek konumlar
}
```

Her koordinatın bitlerini, aralarına birer boşluk bırakacak şekilde **yayıyoruz** (Ders 5.11'deki shuffle, Ders 5.12'deki expand kalıbı): `X`'in bitleri çift konumlara (`0x55555555` maskesi), `Y`'ninkiler tek konumlara. Sonra OR'layıp iç içe geçiriyoruz. Yayma, Ders 5.11'deki kelebek deseninin aynısı — her adım bitleri iki katı aralığa açıyor.

4×4 bir ızgarada Morton kodları:

```
      x=0  x=1  x=2  x=3
y=0:   0    1    4    5
y=1:   2    3    6    7
y=2:   8    9   12   13
y=3:  10   11   14   15
```

Sıralamayı (0,1,2,3,4,…) takip edersen bir **Z** deseni çıkar — adı buradan. Çözmek (decode) tersine, bitleri ayırmak:

```c
void morton_decode(uint32_t m, uint16_t *x, uint16_t *y) {
    uint32_t X = m & 0x55555555, Y = (m >> 1) & 0x55555555;
    X = (X | (X >> 1)) & 0x33333333;    // bitleri geri topla
    X = (X | (X >> 2)) & 0x0F0F0F0F;
    X = (X | (X >> 4)) & 0x00FF00FF;
    X = (X | (X >> 8)) & 0x0000FFFF;
    // Y icin ayni...
    *x = (uint16_t)X; *y = (uint16_t)Y;
}
```

256×256 ızgarada bütün noktalarda encode-decode round-trip'ini doğruladık: sıfır hata. (x86'da bu serpiştirme tek komut: `pdep` ile `0x55555555` maskesine expand — Ders 5.12. Donanım varsa Morton encode iki `pdep` + bir OR.)

---

## 2. Hilbert eğrisi: ardışık noktalar hep komşu

Morton'ın bir zayıflığı var: Z deseninde **sıçramalar** olur. `3 → 4` geçişinde (ızgarada `(1,1) → (0,2)`) iki nokta uzaktır — Z'nin köşesinden atlar. **Hilbert eğrisi** bunu düzeltir: ardışık indeksli noktalar **her zaman** ızgarada komşudur (yatay ya da dikey bir adım). 4×4 Hilbert:

```
      x=0  x=1  x=2  x=3
y=0:   0    1   14   15
y=1:   3    2   13   12
y=2:   4    7    8   11
y=3:   5    6    9   10
```

`0→1→2→3→4→…`'ü takip et: her adım bir kare yana ya da aşağı, hiç sıçrama yok. Bunu ölçtük: 4×4'te ardışık Hilbert indekslerinin ızgara mesafesi **her zaman 1**. Hilbert'in kodu Morton'dan karmaşık, çünkü her ölçekte alt karelerin **döndürülmesi** gerekiyor (U şekilleri birbirine bağlanırken):

```c
uint32_t hilbert_xy2d(uint32_t n, uint32_t x, uint32_t y) {
    uint32_t d = 0;
    for (uint32_t s = n / 2; s > 0; s /= 2) {
        uint32_t rx = (x & s) > 0;
        uint32_t ry = (y & s) > 0;
        d += s * s * ((3 * rx) ^ ry);
        if (ry == 0) {                          // alt kareyi dondur
            if (rx == 1) { x = s - 1 - x; y = s - 1 - y; }
            uint32_t t = x; x = y; y = t;
        }
    }
    return d;
}
```

Her ölçekte, noktanın hangi çeyrekte olduğuna (`rx`, `ry`) göre bir indeks parçası ekleniyor (`(3*rx) ^ ry`, dört çeyreği 0-3'e Hilbert sırasıyla eşler), ve gerekiyorsa koordinatlar döndürülüyor (U şekillerini hizalamak için). Tersi (`d2xy`) de var; round-trip'i doğruladık, sıfır hata.

---

## 3. Neden önbellek dostu

Asıl fayda **veri düzeninde**. Ders 4.3'te satır-öncelikli bir matriste, aynı satırdaki komşuların bellekte bitişik, ama aynı sütundaki komşuların bir satır (büyük bir atlama) uzakta olduğunu görmüştük — bu yüzden döngü sırası önemliydi. Bir 2B verinin hem yatay hem dikey komşulara eriştiği durumlarda (görüntü işleme, fizik simülasyonu, oyun haritaları), satır-öncelikli düzen dikey erişimde önbelleği boşa harcar.

256×256 ızgarada, 2B komşuların 1B indekste ortalama ne kadar uzak olduğunu ölçtük:

```
yatay komsular:   row-major 1.00    morton 85.67
dikey komsular:   row-major 256.00  morton 171.33
```

- **Satır-öncelikli**: yatay komşular bitişik (mesafe 1, mükemmel), ama dikey komşular 256 uzakta (bir satır — berbat).
- **Morton**: yatay ~86, dikey ~171 — ikisi de 1 değil, ama **dengeli**, ve en kötü durum sınırlı. Hiçbir yön felaket değil.

Satır-öncelikli tek bir yönde (yatay) harika, diğerinde (dikey) felaket; Morton ikisini **dengeliyor**. Bir algoritma hem satır hem sütun komşularına erişiyorsa, Morton (ya da daha iyisi Hilbert, çünkü ardışık noktalar hep komşu) toplam önbellek ıskalamasını azaltır. Bu yüzden Morton/Hilbert düzeni, görüntü dokularında (GPU'lar doku belleğini Morton'a göre dizer), uzamsal veritabanı indekslerinde (R-tree alternatifleri), ve blok tabanlı matris algoritmalarında kullanılır.

Fikir, bu fazın teması: **bitleri yeniden düzenlemek (serpiştirmek) verinin fiziksel yerleşimini kontrol eder**, ve doğru yerleşim donanımın (önbelleğin) nasıl çalıştığına uyarsa büyük hız kazandırır. Morton kodu, Ders 5.11'deki shuffle ve Ders 5.12'deki expand'in, 2B uzayı önbelleğe sığdırmak için kullanılan hali.

---

## Alıştırmalar

**1** – `morton_encode(3, 5)`'i elle hesapla: `x = 3 = 011`, `y = 5 = 101`. Bitleri serpiştir (`y₂x₂y₁x₁y₀x₀`), sonucu ikilik ve ondalık yaz. `morton_decode` ile geri `(3, 5)` çıkar mı?

**2** – Morton 4×4 tablosunda `3 → 4` geçişi ızgarada hangi iki noktayı birleştiriyor, mesafe kaç? Hilbert 4×4'te aynı geçiş (`3 → 4`) kaç mesafe? Morton'ın "sıçrama" sorununu bu örnekle açıkla.

**3** – Morton encode'daki bit yayma (`X = (X | (X << 8)) & 0x00FF00FF; …`) Ders 5.11'deki shuffle ve Ders 5.12'deki expand ile nasıl ilişkili? `pdep(x, 0x55555555)` (Ders 5.12) ne üretir — Morton'ın `X` kısmıyla aynı mı?

**4** – 3 boyutlu Morton kodu: `x`, `y`, `z`'nin bitlerini üçerli serpiştirmek (`z₀y₀x₀z₁y₁x₁…`). 10-bitlik üç koordinattan 30-bitlik bir kod için maskeler ne olur (ipucu: her 3. bit, `0x49249249` gibi)? Bu neden 3B dokularda (voxel) kullanılır?

**5** – Bir 2B diziyi Morton düzeninde saklamak: `pixel[morton_encode(x, y)]`. Satır-öncelikli `pixel[y * width + x]` ile karşılaştır. Bir 3×3 bulanıklaştırma filtresi (her piksel + 8 komşusu) hangi düzende daha az önbellek ıskalaması yapar, neden? Hilbert daha mı iyi olurdu?

<details>
<summary>Cevaplar</summary>

**1** – `x = 011`, `y = 101`. Serpiştir (Morton: `X` çift konumlar, `Y` tek konumlar, yani `y₂x₂ y₁x₁ y₀x₀`): bit çiftleri (yüksekten): `(y₂=1,x₂=0)`, `(y₁=0,x₁=1)`, `(y₀=1,x₀=1)` → `10 01 11` = `100111` = 39. `morton_decode(39)`: çift konumlar (`x`) = bit 0,2,4 = `1,1,0` = `011` = 3; tek konumlar (`y`) = bit 1,3,5 = `1,0,1` = `101` = 5. Geri `(3, 5)`. Doğru.

**2** – Morton `3 → 4`: indeks 3 `(1,1)`, indeks 4 `(0,2)` (tabloya bak: `y=1,x=1`→3; `y=2,x=0`→4). Mesafe `|1-0| + |1-2| = 2`. Hilbert `3 → 4`: indeks 3 `(0,1)`, indeks 4 `(0,2)`; mesafe `0 + 1 = 1`. Morton'ın sıçraması: bir 2×2 bloğun sonundan bir sonraki bloğun başına geçerken Z'nin köşegeni atlanır (mesafe 2+); Hilbert, blokları döndürerek bağladığı için hep mesafe 1. Bu yüzden Hilbert daha iyi yerellik, ama hesaplaması daha pahalı.

**3** – Morton encode'daki yayma, Ders 5.11'deki shuffle'ın (bitleri aralama) yarısı: her koordinatın bitlerini birer boşluk bırakarak açar. Ders 5.12'deki `pdep(x, 0x55555555)` **tam olarak** Morton'ın `X` kısmını üretir: `x`'in bitlerini `0x55555555` maskesinin 1 olduğu (çift) konumlara dağıtır — yani `x₀` → bit 0, `x₁` → bit 2, …. Yani donanımda `morton_encode(x,y) = pdep(x, 0x55555555) | pdep(y, 0xAAAAAAAA)`, iki `pdep` komutu. Yazdığımız bit yayma, `pdep` olmayan makinelerde onun yerini tutan yazılım.

**4** – 3B Morton için her koordinatın bitleri **üçer** aralıkla yayılır: bir bit koy, iki boşluk bırak. Maske `0x49249249` (`...001001001`, her 3. bit 1). Yayma adımları da üçe göre: `X = (X | (X << 16)) & ...`, `(X << 8)`, `(X << 4)`, `(X << 2)` gibi, maskeler her adımda 3'erli grupları ayırır. 3B dokularda (voxel, tıbbi görüntüleme, fizik) kullanılır çünkü 3B'de bir noktanın 6 komşusu (±x, ±y, ±z) var; satır-öncelikli düzen bunlardan ikisini bitişik, dördünü çok uzak tutar, Morton altısını da dengeli yakın tutar — 3B önbellek yerelliği.

**5** – 3×3 bulanıklaştırma, her piksel için kendisi + 8 komşusuna (yatay, dikey, çapraz) erişir. Satır-öncelikli düzende yatay komşular bitişik ama dikey/çapraz komşular bir-iki satır (width kadar) uzakta — her piksel için 3 ayrı önbellek satırı (üç komşu satır) gerekir. Morton düzeninde 9 komşu 1B indekste **dengeli** yakın (Bölüm 3'teki ölçüm: hiçbiri çok uzak değil), bir ya da iki önbellek satırına sığabilir — daha az ıskalama. Hilbert **daha iyi** olurdu: ardışık noktalar hep komşu olduğu için 2B yerellik en yüksek; ama encode/decode maliyeti Morton'dan fazla, bu yüzden erişim deseni çok yoğunsa Hilbert, hesap maliyeti önemliyse Morton tercih edilir. Ölçmeden karar verilmez (Ders 2.12).

</details>

---

## Kaynaklar

- Henry Warren, *Hacker's Delight* (2. baskı), §14: Morton kodu ve bit serpiştirme.
- Guy Macdonald Morton, "A Computer Oriented Geodetic Data Base" (1966): Z-order'ın kökeni.
- David Hilbert, "Über die stetige Abbildung einer Linie auf ein Flächenstück" (1891): Hilbert eğrisi.
- Ders 5.11 (shuffle) ve Ders 5.12 (pext/pdep): Morton encode'un araçları.

**Sıradaki ders:** Float bit hileleri. Float'ı tamsayı gibi karşılaştırma, hızlı ters karekök (0x5f3759df) ve Newton adımı.
