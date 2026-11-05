---
title: "7.21 Boru hattı tehlikeleri"
description: "Boru hattını durduran üç tehlike: yapısal (aynı birimi iki komut ister), veri (RAW: bir komut öncekinin sonucunu bekler) ve kontrol (dal sonucu bilinmeden sonraki komut getirilemez). Bekleme (stall/bubble), iletme (forwarding/bypassing), yükle-kullan (load-use) tehlikesinin neden forwarding ile bile bir döngü beklettiği; bunları sayan bir C simülatörü; yüklemeleri öne alarak tehlikeleri gideren komut zamanlama (instruction scheduling) ve derleyicinin bunu neden yaptığı."
---

Ders 7.20'deki zaman diyagramında beş komut hiç takılmadan aktı, ama hile yapmıştık: komutlar birbirinden bağımsızdı. Gerçek programlarda bir komut neredeyse her zaman bir öncekinin sonucunu kullanır. Bu ders, boru hattının ideal "her döngüde bir komut" akışını bozan durumları — **tehlikeleri** (hazards) — ve donanımın ve derleyicinin onlara karşı kullandığı üç silahı anlatıyor: beklemek, iletmek ve yeniden sıralamak.

---

## 1. Üç tür tehlike

| Tür | Sebep | Örnek |
| --- | --- | --- |
| **Yapısal** | İki komut aynı döngüde aynı donanım birimini istiyor | Tek bir bellek hem komut getirmeye (IF) hem `lw`'ya (MEM) hizmet ediyorsa |
| **Veri** | Bir komut, henüz yazılmamış bir sonucu okumak istiyor | `add x3,x1,x2` hemen `lw x1,0(x10)`'dan sonra |
| **Kontrol** | Dalın sonucu bilinmeden hangi komutun getirileceği bilinmiyor | `beq` EX'te karar verene kadar IF ne getirsin? |

**Yapısal tehlikeler** tasarımla çözülür: RISC-V boru hattında komut ve veri için **ayrı** bellekler (pratikte ayrı L1 önbellekleri, Ders 7.24) var; register dosyası döngünün ilk yarısında yazıp ikinci yarısında okuyacak şekilde yapılıyor, böylece WB ve ID aynı döngüde çakışmıyor. Bu dersin geri kalanı diğer ikisi hakkında.

---

## 2. Veri tehlikesi: RAW

En yaygın tür **RAW** (read after write, yazmadan sonra okuma): bir komut, önceki bir komutun **yazacağı** register'ı okuyor.

```
lw   x1, 0(x10)
add  x3, x1, x2      # x1'e ihtiyac var
```

`lw` `x1`'i ancak WB'de (5. döngü) yazıyor; `add` ise ID'de (3. döngü) okumak istiyor. Bir şey yapılmazsa eski `x1` değeri okunur ve program yanlış çalışır.

### Çözüm 1: Beklemek (stall)

Donanım bağımlılığı fark eder (ID aşamasındaki komutun `rs1`/`rs2`'si, ilerideki bir komutun `rd`'siyle aynı mı?) ve bağımlı komutu ID'de **bekletir**; arkasındakiler de IF'te bekler. Boş geçen aşamalara **kabarcık** (bubble) denir: boru hattında ilerleyen, hiçbir iş yapmayan bir `nop`. Bekleme doğruluğu garanti eder ama her kabarcık bir döngü kayıp.

### Çözüm 2: İletmek (forwarding)

Gözlem: `add x3,x1,x2`'nin sonucu aslında EX aşamasının **sonunda** hazır, WB'yi beklemeye gerek yok. Bir sonraki komutun EX'i ona tam o anda ihtiyaç duyuyor. Donanım ALU çıkışından ALU girişine **kısa bir yol** (bypass) ekler: `EX/MEM` register'ındaki değer, register dosyasındaki eski değer yerine ALU'ya verilir. ALU'nun girişlerine iki yeni mux eklenir; "iletme birimi" (forwarding unit) her döngüde `rd` ve `rs` numaralarını karşılaştırıp mux'ları ayarlar.

Forwarding ile ALU → ALU bağımlılıkları **sıfır** beklemeyle çözülür. Ama bir istisna var.

### Yükle-kullan tehlikesi

`lw`'nun sonucu EX'te değil, **MEM'in sonunda** hazır (bellekten okunuyor). Hemen arkasındaki komutun EX'i ise `lw`'nun MEM'iyle aynı döngüde. Veriyi zamanda geriye gönderemeyiz: forwarding'le bile **bir döngü** bekleme şart. Bu **load-use hazard**, ve tam da bu yüzden derleyici yüklemeleri kullanımlardan uzaklaştırmaya çalışıyor (Bölüm 4).

---

## 3. Simülasyon

Klasik örnek: `a = b + c; d = e − f;` (değişkenler bellekte, taban adres `x10`'da). Aşağıdaki simülatör, her komutun EX'e girebileceği en erken döngüyü bağımlılık kurallarından hesaplıyor:

- **Forwarding yok:** tüketicinin EX'i ≥ üreticinin EX'i + 3. Üretici EX + 2'de (WB) döngünün ilk yarısında yazar, tüketici aynı döngünün ikinci yarısında ID'de okuyabilir (Bölüm 1), ve bir sonraki döngüde EX'e girer.
- **Forwarding var, ALU üreticisi:** tüketicinin EX'i ≥ üreticinin EX'i + 1 (hemen arkasından, beklemesiz).
- **Forwarding var, `lw` üreticisi:** tüketicinin EX'i ≥ üreticinin EX'i + 2 (MEM'den iletme, bir bekleme).

```c
/* Boru hatti tehlikeleri: forwarding olmadan / olarak, ve komut zamanlama */
#include <stdio.h>

typedef struct { const char *ad; int rd, rs1, rs2, yukleme; } Komut;

/* Her komutun EX dongusunu hesapla, diyagrami bas, toplam donguyu dondur */
static int simule(const Komut *p, int n, int forwarding, int bas) {
    int IF[16], ID[16], EX[16];
    for (int i = 0; i < n; i++) {
        IF[i] = (i == 0) ? 1 : ID[i-1];
        ID[i] = (i == 0) ? 2 : (IF[i] + 1 > EX[i-1] ? IF[i] + 1 : EX[i-1]);
        int ex = ID[i] + 1;
        if (i > 0 && ex < EX[i-1] + 1) ex = EX[i-1] + 1;
        for (int j = 0; j < i; j++) {                     /* RAW bagimliligi ara */
            if (p[j].rd == 0) continue;
            if (p[j].rd != p[i].rs1 && p[j].rd != p[i].rs2) continue;
            int gerek;
            if (!forwarding)       gerek = EX[j] + 3;    /* WB'den sonra ID okuyabilir */
            else if (p[j].yukleme) gerek = EX[j] + 2;    /* MEM sonucu iletilir       */
            else                   gerek = EX[j] + 1;    /* EX sonucu iletilir        */
            if (ex < gerek) ex = gerek;
        }
        EX[i] = ex;
    }
    int son = EX[n-1] + 2;
    if (bas) {
        printf("%-16s", "");
        for (int t = 1; t <= son; t++) printf("%4d", t);
        printf("\n");
        for (int i = 0; i < n; i++) {
            printf("%-16s", p[i].ad);
            for (int t = 1; t <= son; t++) {
                const char *s = ".";
                if (t == IF[i]) s = "IF";
                else if (t > IF[i] && t < ID[i]) s = "**";      /* IF'te bekleme */
                else if (t == ID[i]) s = "ID";
                else if (t > ID[i] && t < EX[i]) s = "**";      /* ID'de bekleme */
                else if (t == EX[i]) s = "EX";
                else if (t == EX[i] + 1) s = "MEM";
                else if (t == EX[i] + 2) s = "WB";
                printf("%4s", s);
            }
            printf("\n");
        }
    }
    return son;
}

int main(void) {
    /* a = b + c; d = e - f;  (b,c,e,f bellekte; x10 taban) */
    Komut kod[] = {
        { "lw  x1,0(x10)",  1, 10, 0, 1 },
        { "lw  x2,4(x10)",  2, 10, 0, 1 },
        { "add x3,x1,x2",   3, 1,  2, 0 },
        { "sw  x3,12(x10)", 0, 3, 10, 0 },
        { "lw  x4,8(x10)",  4, 10, 0, 1 },
        { "lw  x5,16(x10)", 5, 10, 0, 1 },
        { "sub x6,x4,x5",   6, 4,  5, 0 },
        { "sw  x6,20(x10)", 0, 6, 10, 0 },
    };
    /* ayni is, yuklemeler one alinmis (zamanlanmis) */
    Komut zaman[] = {
        { "lw  x1,0(x10)",  1, 10, 0, 1 },
        { "lw  x2,4(x10)",  2, 10, 0, 1 },
        { "lw  x4,8(x10)",  4, 10, 0, 1 },
        { "add x3,x1,x2",   3, 1,  2, 0 },
        { "lw  x5,16(x10)", 5, 10, 0, 1 },
        { "sw  x3,12(x10)", 0, 3, 10, 0 },
        { "sub x6,x4,x5",   6, 4,  5, 0 },
        { "sw  x6,20(x10)", 0, 6, 10, 0 },
    };
    printf("--- forwarding YOK ---\n");
    int a = simule(kod, 8, 0, 1);
    printf("\n--- forwarding VAR ---\n");
    int b = simule(kod, 8, 1, 1);
    printf("\n--- forwarding VAR + yeniden siralanmis ---\n");
    int c = simule(zaman, 8, 1, 1);
    printf("\nideal (tehlikesiz): %d dongu\n", 5 + 8 - 1);
    printf("forwarding yok: %d, forwarding var: %d, + zamanlama: %d\n", a, b, c);
    return 0;
}
```

`sw` komutlarının `rd`'si 0: register'a yazmıyorlar, kimse onları beklemiyor. `**` bekleme döngüsü (kabarcık).

```
$ cc -O1 -Wall tehlike.c -o tehlike && ./tehlike
--- forwarding YOK ---
                   1   2   3   4   5   6   7   8   9  10  11  12  13  14  15  16  17  18  19  20
lw  x1,0(x10)     IF  ID  EX MEM  WB   .   .   .   .   .   .   .   .   .   .   .   .   .   .   .
lw  x2,4(x10)      .  IF  ID  EX MEM  WB   .   .   .   .   .   .   .   .   .   .   .   .   .   .
add x3,x1,x2       .   .  IF  ID  **  **  EX MEM  WB   .   .   .   .   .   .   .   .   .   .   .
sw  x3,12(x10)     .   .   .  IF  **  **  ID  **  **  EX MEM  WB   .   .   .   .   .   .   .   .
lw  x4,8(x10)      .   .   .   .   .   .  IF  **  **  ID  EX MEM  WB   .   .   .   .   .   .   .
lw  x5,16(x10)     .   .   .   .   .   .   .   .   .  IF  ID  EX MEM  WB   .   .   .   .   .   .
sub x6,x4,x5       .   .   .   .   .   .   .   .   .   .  IF  ID  **  **  EX MEM  WB   .   .   .
sw  x6,20(x10)     .   .   .   .   .   .   .   .   .   .   .  IF  **  **  ID  **  **  EX MEM  WB

--- forwarding VAR ---
                   1   2   3   4   5   6   7   8   9  10  11  12  13  14
lw  x1,0(x10)     IF  ID  EX MEM  WB   .   .   .   .   .   .   .   .   .
lw  x2,4(x10)      .  IF  ID  EX MEM  WB   .   .   .   .   .   .   .   .
add x3,x1,x2       .   .  IF  ID  **  EX MEM  WB   .   .   .   .   .   .
sw  x3,12(x10)     .   .   .  IF  **  ID  EX MEM  WB   .   .   .   .   .
lw  x4,8(x10)      .   .   .   .   .  IF  ID  EX MEM  WB   .   .   .   .
lw  x5,16(x10)     .   .   .   .   .   .  IF  ID  EX MEM  WB   .   .   .
sub x6,x4,x5       .   .   .   .   .   .   .  IF  ID  **  EX MEM  WB   .
sw  x6,20(x10)     .   .   .   .   .   .   .   .  IF  **  ID  EX MEM  WB

--- forwarding VAR + yeniden siralanmis ---
                   1   2   3   4   5   6   7   8   9  10  11  12
lw  x1,0(x10)     IF  ID  EX MEM  WB   .   .   .   .   .   .   .
lw  x2,4(x10)      .  IF  ID  EX MEM  WB   .   .   .   .   .   .
lw  x4,8(x10)      .   .  IF  ID  EX MEM  WB   .   .   .   .   .
add x3,x1,x2       .   .   .  IF  ID  EX MEM  WB   .   .   .   .
lw  x5,16(x10)     .   .   .   .  IF  ID  EX MEM  WB   .   .   .
sw  x3,12(x10)     .   .   .   .   .  IF  ID  EX MEM  WB   .   .
sub x6,x4,x5       .   .   .   .   .   .  IF  ID  EX MEM  WB   .
sw  x6,20(x10)     .   .   .   .   .   .   .  IF  ID  EX MEM  WB

ideal (tehlikesiz): 12 dongu
forwarding yok: 20, forwarding var: 14, + zamanlama: 12
```

Üç diyagramı okuyalım:

- **Forwarding yok (20 döngü):** her RAW bağımlılığı iki bekleme döngüsü ekliyor. `add`, `x2`'nin WB'sini (6. döngü) bekliyor; `sw`, `x3`'ün WB'sini (9. döngü). Dört bağımlılık × 2 = 8 kayıp döngü, $12 + 8 = 20$.
- **Forwarding var (14 döngü):** ALU → `sw` bağımlılıkları bedavaya döndü. Geriye iki **yükle-kullan** kaldı: `lw x2` → `add` ve `lw x5` → `sub`, her biri tam bir kabarcık. $12 + 2 = 14$.
- **Yeniden sıralanmış (12 döngü):** `lw x4`'ü `add`'den önceye, `lw x5`'i `sw x3`'ten önceye aldık. Artık hiçbir `lw`'nun hemen arkasında onun sonucunu kullanan bir komut yok. Program **aynı işi** yapıyor (hiçbir bağımlılığı bozmadık), ama ideal sürede: 12 döngü, CPI = 1.

Kazanç: forwarding yokken 20 → 12, **%40 daha hızlı**, aynı donanımda, sadece komut sırası değişerek.

---

## 4. Komut zamanlama: derleyicinin işi

Son diyagramdaki yeniden sıralamaya **komut zamanlama** (instruction scheduling) denir. Kuralları:

- Bir komut, bağımlı olduğu bir komutun **önüne** geçemez (RAW).
- Bir komut, bir register'ı okuyan bir komutun önüne geçip o register'a **yazamaz** (WAR, okumadan sonra yazma), ve aynı register'a yazan iki komutun sırası değişemez (WAW). Bunlar "isim" bağımlılıkları; Ders 7.23'te donanımın register yeniden adlandırmayla nasıl çözdüğünü göreceğiz.
- Bellek erişimleri: iki erişimin aynı adrese gidip gitmediği belli değilse sıraları korunur (aliasing; C'de `restrict` derleyiciye "çakışmaz" demenin yolu, Ders 7.29'daki SIMD örneğinde de kullanıyoruz).

Örneğimizde `lw x4,8(x10)`'u `sw x3,12(x10)`'un önüne almak güvenliydi, çünkü adresler farklı (`x10+8` ve `x10+12`, aynı taban). Derleyici bunu **kanıtlayabildiği** için yapabilir.

Derleyiciler bunu gerçekten yapar (`-O2` ile zamanlama geçişleri açık; Faz 16'da kendi zamanlayıcımızı yazacağız). Basit sıralı (in-order) çekirdeklerde (küçük ARM ve RISC-V çekirdekleri, gömülü işlemciler) bu büyük fark yaratır. Büyük sırasız (out-of-order) çekirdekler ise aynı yeniden sıralamayı **donanımda**, çalışma anında yapar (Ders 7.23); orada derleyicinin zamanlaması daha az kritik ama yine de yardımcı.

---

## 5. Kontrol tehlikesi

```
    beq  x1, x2, hedef
    add  x3, x4, x5      # dal alinirsa bu calismamali
    ...
hedef:
    sub  x6, x7, x8
```

`beq`'in sonucu (eşit mi?) EX'te belli oluyor. O ana kadar IF iki komut daha getirmiş olur: `beq`'ten sonraki iki komut. Dal alınırsa bunlar **yanlış komutlar**. Seçenekler:

1. **Beklemek:** dal her görüldüğünde EX bitene kadar getirmeyi durdur. Her dalda 2 döngü kayıp; programların ~%15–20'si dal komutu olduğu için CPI ~1.3–1.4'e çıkar.
2. **Kararı öne almak:** karşılaştırmayı ID aşamasına taşımak (eşitlik kontrolü ucuz bir XOR; tam bir çıkarma gerekmiyor). Ceza 1 döngüye iner.
3. **Tahmin etmek:** "dal alınmaz" diye varsayıp `PC+4`'ten getirmeye devam et; yanlış çıkarsa getirilen komutları **iptal et** (flush: onları `nop`'a çevir; henüz WB'ye ulaşmadıkları için hiçbir şeyi değiştirmediler). Doğru tahminde ceza sıfır.

Seçenek 3 bugünkü bütün işlemcilerin yaptığı şey, ama çok daha akıllı tahmincilerle: geçmiş davranışa bakıp "bu dal genelde alınır mı?" diye öğrenen devreler. Boru hattı derinleştikçe (Ders 7.20'deki 14–31 aşama) yanlış tahminin cezası 15–20 döngüye çıkıyor ve tahminin isabeti hayati oluyor. Bir sonraki ders tamamen bunun üstüne.

---

## Alıştırmalar

**1** – Şu dizide hangi bağımlılıklar var? Forwarding olan 5 aşamalı boru hattında kaç kabarcık oluşur?

```
lw   x1, 0(x10)
addi x1, x1, 1
sw   x1, 0(x10)
```

**2** – Bölüm 3'teki simülatörde `kod` dizisinin sonuna `add x7,x6,x3` ekle. Üç modda toplam döngü kaç olur? Önce tahmin et, sonra çalıştır.

**3** – C'de `int f(int *a, int *b) { *a = 1; return *b; }` fonksiyonunda derleyici `*b`'yi okumayı `*a = 1` yazmasının önüne alabilir mi? `int f(int *restrict a, int *restrict b)` olsa?

**4** – Programın %20'si dal komutu, dalların %60'ı alınıyor. Boru hattı "hep alınmaz" tahmini yapıyor ve yanlış tahminin cezası 2 döngü. Başka tehlike yoksa CPI ne olur? Ceza 15 döngü olsaydı (derin boru hattı)?

**5** – Bir yapısal tehlike örneği: komutlar ve veri **tek** bir bellekte olsaydı (ayrı önbellek yok), `lw` MEM aşamasındayken aynı döngüde IF ne yapardı? Ders 7.20'deki 5 bağımsız komutluk diyagramda kaç `lw` olursa kaç döngü kaybedilir?

<details>
<summary>Cevaplar</summary>

**1** – İki RAW: `lw x1` → `addi` (yükle-kullan) ve `addi x1` → `sw` (ALU → bellek). İlki forwarding'le bile **1 kabarcık**; ikincisi forwarding'le bedava. Toplam 1. Ayrıca `addi x1,x1,1` hem okuyup hem yazıyor; `lw x1` ile arasında WAW var ama sıralı boru hattında yazmalar sırayla olduğu için sorun yok.

**2** – `add x7,x6,x3` hem `sub`'ın sonucuna (`x6`) hem çok önceki `add`'in sonucuna (`x3`) bağlı. `x3` çoktan yazıldı, sorun değil; `x6`'yı yazan `sub` iki komut önce (`sw x6` arada). Forwarding yokken: `sub`'ın EX'i 15, `add x7` en erken EX ≥ 18 olmalı; `sw x6`'nın EX'i 18 olduğu için `add x7` EX'i 19: toplam **21** döngü. Forwarding varken: `sub` EX 11, `sw x6` EX 12, `add x7` EX 13 (ALU → ALU, bekleme yok): toplam **15**. Zamanlanmış: **13**. Her modda tam 1 döngü ekledi: yeni komut hiçbir bekleme yaratmadı (forwarding yokken bile, çünkü `sw` zaten aradaki bekleme süresini doldurdu).

**3** – Hayır: `a` ve `b` aynı adresi gösterebilir (`f(&x, &x)`); o durumda `*b` 1 olmalı, okumayı öne almak eski değeri döndürür. Derleyici aliasing'i dışlayamadığı için sırayı korur. `restrict` ile programcı "bu iki işaretçi çakışmaz" der, derleyici okumayı öne alabilir (ya da `*b`'yi yazmadan önce bir register'da tutabilir). `restrict`'e uymayan bir çağrı UB'dir (Ders 2.12).

**4** – Dalların %60'ı alınıyor, "hep alınmaz" tahmini %60 yanlış. CPI = $1 + 0.20 \times 0.60 \times 2 = 1.24$. 15 döngülük cezayla $1 + 0.20 \times 0.60 \times 15 = 2.8$: işlemci yarı hızından da yavaş. Derin boru hatlarında iyi bir dal tahmincisi olmadan hiçbir şey çalışmaz.

**5** – Tek bellek bir döngüde tek erişime hizmet eder: `lw`'nun MEM'i ile o döngünün IF'i çakışır, IF bir döngü bekler (yapısal tehlike, bir kabarcık). Her `lw` ve `sw` bir döngü kaybettirir: 5 komutun $m$ tanesi bellek komutuysa $9 + m$ döngü. Ayrı komut ve veri önbellekleri (Harvard tarzı L1, Ders 7.24) bu yüzden var.

</details>

---

## Kaynaklar

- David Patterson & John Hennessy, *Computer Organization and Design: RISC-V Edition* (2. baskı), Bölüm 4.7–4.9: veri tehlikeleri, forwarding, stall, kontrol tehlikeleri (`a = b + c; d = e − f` örneği oradan).
- John Hennessy & David Patterson, *Computer Architecture: A Quantitative Approach* (6. baskı), Ek C.2: boru hattı tehlikeleri.
- Steven Muchnick, *Advanced Compiler Design and Implementation* (1997), Bölüm 17: komut zamanlama.

**Sıradaki ders:** Dal tahmini. Statik ve dinamik tahmin, 2 bitlik sayaç, sıralı ve sırasız dizi üzerinde hız farkı deneyi.
