---
title: "11.16 Veri düzeni: AoS ve SoA"
description: "Aynı parçacıklar üç bellek düzeninde: struct dizisi (AoS), dizi struct'ı (SoA) ve 8'li bloklar (AoSoA); derleyicinin AoS'u vektörleştirmeyi yararsız bulması; önbellekte konum güncellemesinde 2.7 kat, tek alan okumada 1.8 kat fark; 134 MB'ta tek alan için AoS 0.57, SoA 0.11 ns ve AoSoA'nın beklenmedik biçimde AoS kadar yavaş kalması; dokunulan önbellek satırı başına bant genişliği hesabı; sıcak ve soğuk alanları ayırmak."
---

Ders 7.26'da AoS ve SoA'yı önbellek açısından tanıttık: tek alan okuyan bir döngüde AoS, getirdiği verinin çoğunu boşa harcıyor. Bu derste aynı soruyu SIMD açısından ve ölçerek soruyoruz. SIMD, şeritlerin **bellekte yan yana** gelmesini istiyor; veri düzeni bunu ya veriyor ya vermiyor.

---

## 1. Üç düzen

```
AoS    x y z vx vy vz m q | x y z vx vy vz m q | ...       (32 byte / parcacik)
SoA    x x x x x ... | y y y y y ... | vx vx vx ...
AoSoA  [x*8 y*8 z*8 vx*8 vy*8 vz*8 m*8 q*8] [x*8 ...] ...  (256 byte / 8 parcacik)
```

AoSoA (*array of structures of arrays*) ikisinin karışımı: blok içinde SoA, bloklar AoS. ISPC derleyicisinin ve oyun motorlarının sevdiği düzen: SIMD için şeritler yan yana, bir parçacığın verisi ise birbirine yakın.

```c
/* duzen.c: ayni parcaciklar, uc bellek duzeni */
#include <stdio.h>
#include <stdlib.h>
#include "olcum.h"

/* AoS: struct dizisi, 32 byte */
typedef struct { float x, y, z, vx, vy, vz, kutle, yuk; } Parcacik;

/* SoA: dizi struct'i */
typedef struct { float *x, *y, *z, *vx, *vy, *vz, *kutle, *yuk; } Parcaciklar;

/* AoSoA: 8'li bloklar, her blok kendi icinde SoA */
typedef struct { float x[8], y[8], z[8], vx[8], vy[8], vz[8], kutle[8], yuk[8]; } Blok;

__attribute__((noinline)) void ilerlet_aos(Parcacik *restrict p, long n, float dt) {
    for (long i = 0; i < n; i++) {
        p[i].x += p[i].vx * dt; p[i].y += p[i].vy * dt; p[i].z += p[i].vz * dt;
    }
}
__attribute__((noinline)) void ilerlet_soa(Parcaciklar s, long n, float dt) {
    float *restrict x = s.x, *restrict y = s.y, *restrict z = s.z;
    const float *restrict vx = s.vx, *restrict vy = s.vy, *restrict vz = s.vz;
    for (long i = 0; i < n; i++) { x[i] += vx[i] * dt; y[i] += vy[i] * dt; z[i] += vz[i] * dt; }
}
__attribute__((noinline)) void ilerlet_aosoa(Blok *restrict b, long n, float dt) {
    for (long k = 0; k < n / 8; k++)
        for (int j = 0; j < 8; j++) {
            b[k].x[j] += b[k].vx[j] * dt; b[k].y[j] += b[k].vy[j] * dt; b[k].z[j] += b[k].vz[j] * dt;
        }
}

/* yalnizca bir alan: toplam kutle */
__attribute__((noinline)) float kutle_aos(const Parcacik *p, long n) {
    float s = 0; for (long i = 0; i < n; i++) s += p[i].kutle; return s;
}
__attribute__((noinline)) float kutle_soa(const float *m, long n) {
    float s = 0; for (long i = 0; i < n; i++) s += m[i]; return s;
}
__attribute__((noinline)) float kutle_aosoa(const Blok *b, long n) {
    float s = 0;
    for (long k = 0; k < n / 8; k++) for (int j = 0; j < 8; j++) s += b[k].kutle[j];
    return s;
}

static long tur_icin(long n) { long t = 200000000 / n; return t < 3 ? 3 : t; }

int main(void) {
    long ns[] = { 4096, 4 * 1024 * 1024 };
    for (int u = 0; u < 2; u++) {
        long n = ns[u], tur = tur_icin(n);
        Parcacik *p = aligned_alloc(64, sizeof(Parcacik) * n);
        Blok *b = aligned_alloc(64, sizeof(Blok) * (n / 8));
        Parcaciklar s; float **alan[] = { &s.x, &s.y, &s.z, &s.vx, &s.vy, &s.vz, &s.kutle, &s.yuk };
        for (int f = 0; f < 8; f++) *alan[f] = aligned_alloc(64, 4 * n);
        for (long i = 0; i < n; i++) {
            float v[8] = { (float)i, 1, 2, 0.5f, 0.25f, 0.125f, 1.0f + (float)(i % 3), 0 };
            p[i] = (Parcacik){ v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7] };
            for (int f = 0; f < 8; f++) (*alan[f])[i] = v[f];
            float *bl = (float *)&b[i / 8]; for (int f = 0; f < 8; f++) bl[f * 8 + i % 8] = v[f];
        }
        KORU(p); KORU(b); KORU(s.x);
        double e[6] = { 1e9, 1e9, 1e9, 1e9, 1e9, 1e9 };
        volatile float r = 0;
        for (int q = 0; q < 5; q++)
            for (int k = 0; k < 6; k++) {
                double b0 = simdi();
                for (long j = 0; j < tur; j++) {
                    switch (k) {
                    case 0: ilerlet_aos(p, n, 1e-3f); break;
                    case 1: ilerlet_soa(s, n, 1e-3f); break;
                    case 2: ilerlet_aosoa(b, n, 1e-3f); break;
                    case 3: r = kutle_aos(p, n); break;
                    case 4: r = kutle_soa(s.kutle, n); break;
                    case 5: r = kutle_aosoa(b, n); break;
                    }
                    BELLEK();
                }
                double t = simdi() - b0; if (t < e[k]) e[k] = t;
            }
        printf("n=%ld (AoS %.1f MB)\n", n, sizeof(Parcacik) * n / 1e6);
        const char *ad[] = { "ilerlet AoS", "ilerlet SoA", "ilerlet AoSoA", "kutle AoS", "kutle SoA", "kutle AoSoA" };
        for (int k = 0; k < 6; k++) printf("  %-14s %.3f ns/parcacik\n", ad[k], e[k] * 1e9 / (tur * (double)n));
        (void)r;
    }
    return 0;
}
```

---

## 2. Derleyici ne diyor?

```
$ clang -O3 -ffast-math -Rpass=loop-vectorize -Rpass-missed=loop-vectorize -c duzen.c
duzen.c:16:5: remark: the cost-model indicates that vectorization is not beneficial
duzen.c:23:5: remark: vectorized loop (vectorization width: 4, interleaved count: 1)
duzen.c:26:5: remark: the cost-model indicates that vectorization is not beneficial
duzen.c:34:18: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
duzen.c:37:18: remark: vectorized loop (vectorization width: 4, interleaved count: 2)
duzen.c:41:5: remark: the cost-model indicates that vectorization is not beneficial
```

- `ilerlet_aos` (16): döngü vektörleşmedi. Elemanlar 32 byte arayla; aynı alanı dört parçacıktan toplamak için karıştırma gerekiyordu (Ders 11.10) ve maliyet modeli değmeyeceğine karar verdi. Bunun yerine SLP vektörleştiricisi bir parçacığın içindeki `x` ve `y`'yi yan yana işliyor: `ldr d2, [x0]` (iki float) ve `fmla v2.2s` (iki şerit).
- `ilerlet_soa` (23): sorunsuz.
- `ilerlet_aosoa` (26): iç döngü (8 elemanlık) tamamen açılıp SLP ile işleniyor, dış döngü için "yararsız" raporu.
- `kutle_aos` (34) ve `kutle_soa` (37) vektörleşti: AoS'ta 8'li adımlı erişim için derleyici yükleme yapıp karıştırıyor.

---

## 3. Ölçüm

```
$ clang -O3 -ffast-math duzen.c -o d && ./d
n=4096 (AoS 0.1 MB)
  ilerlet AoS    0.454 ns/parcacik
  ilerlet SoA    0.169 ns/parcacik
  ilerlet AoSoA  0.172 ns/parcacik
  kutle AoS      0.171 ns/parcacik
  kutle SoA      0.095 ns/parcacik
  kutle AoSoA    0.104 ns/parcacik
n=4194304 (AoS 134.2 MB)
  ilerlet AoS    0.929 ns/parcacik
  ilerlet SoA    0.699 ns/parcacik
  ilerlet AoSoA  0.868 ns/parcacik
  kutle AoS      0.570 ns/parcacik
  kutle SoA      0.109 ns/parcacik
  kutle AoSoA    0.639 ns/parcacik
```

**Önbellekte** (4096 parçacık, 128 KB): fark tamamen hesaptan. SoA ve AoSoA eşit, AoS konum güncellemesinde **2.7 kat** yavaş: SIMD'in tam kullanılamamasının bedeli.

**Bellekte** (4 milyon parçacık): fark bellek trafiğinden.

- `ilerlet`: AoS 32 byte okuyup 32 byte yazıyor (her satır kirli); SoA 6 dizi × 4 = 24 byte okuyor, 12 byte yazıyor. Bayt oranı 64/36 = 1.8; ölçülen 1.33. Fark kısmen, iki düzenin de bellek sınırına tam dayanmamasından.
- `kutle`: SoA **5.2 kat** hızlı. Bayt hesabı (Ders 7.26'nın Alıştırma 4'ü) 8 kat öngörüyordu.

Beklemediğim sonuç `kutle AoSoA`: SoA kadar hızlı olmasını değilse de AoS'un yarısı olmasını bekliyordum. Ölçüm AoS'tan bile yavaş.

---

## 4. Satır sayısı yetmez

Dokunulan **önbellek satırlarını** (128 byte) sayıp hızı satır başına hesaplayalım:

| Düzen | Satır başına kullanılan | Dokunulan bellek | Süre | Satır bant genişliği |
| --- | --- | --- | --- | --- |
| AoS | 4 parçacık × 4 byte | 134 MB | 2.39 ms | 56 GB/s |
| SoA | 32 × 4 byte (hepsi) | 16.8 MB | 0.46 ms | 37 GB/s |
| AoSoA | 8 × 4 byte | 67 MB | 2.68 ms | 25 GB/s |

AoS her satırı **ardışık** okuyor ve donanım önyükleyicisi bunu en verimli biçimde yapıyor: 56 GB/s, bu makinede ölçtüğümüz en yüksek tek çekirdek okuma hızına yakın (Ders 11.18). AoSoA ise her 256 byte'lık blokta tek bir satıra dokunup ötekini atlıyor; bu desen satır başına çok daha pahalı. Kesin nedeni (önyükleyicinin atlamalı desende daha az ileriyi getirmesi mi, DRAM sayfa verimi mi) donanım sayacı olmadan ayırt edemiyorum.

Ders: **"daha az bayt" daha hızlı demek değil**; erişim deseni de önemli. AoSoA, bütün alanları birlikte kullanan işlerde (`ilerlet` AoS'tan iyi) ve önbellekte iyi; tek alanlık taramalarda SoA'nın yerini tutmuyor.

---

## 5. Pratik: sıcak ve soğuk alanlar

Çoğu gerçek struct'ta bazı alanlar her karede (sıcak), bazıları nadiren (soğuk) kullanılır:

```c
typedef struct { float x, y, z, vx, vy, vz; } Sicak;     /* her karede */
typedef struct { char ad[32]; int tur; double dogum; } Soguk;   /* nadiren */
Sicak  *sicak;   /* n tane */
Soguk  *soguk;   /* n tane, ayni indis */
```

Bu, tam SoA'ya geçmeden AoS'un kolaylığını koruyor ve sıcak döngülerin getirdiği veriyi küçültüyor. Veri odaklı tasarım (Mike Acton, CppCon 2014) bu fikrin genelleşmesi: veriyi nesneye göre değil **erişim desenine** göre düzenle.

Seçim tablosu:

| Erişim | Düzen |
| --- | --- |
| Tek bir alanı çok elemanda | SoA |
| Bütün alanları birlikte, sıralı | AoS ya da AoSoA |
| Bütün alanları, SIMD ile | AoSoA ya da SoA |
| Rastgele tek eleman, bütün alanlar | AoS (tek satır) |
| Karışık | Sıcak/soğuk ayrımı |

---

## Alıştırmalar

**1** – AoSoA'da blok boyutunu 8 yerine 32 yap (`kutle[32]` = 128 byte = bir satır). `kutle AoSoA` süresinin nasıl değişmesini beklersin? Ölç.

**2** – NEON'un `vld3q_f32` komutu `x y z x y z ...` dizisini üç register'a ayırıyor. `struct { float x, y, z; }` dizisine sabit bir yer değiştirme ekleyen döngüyü NEON ile yaz. 8 alanlı `Parcacik` için neden bu kadar kolay değil?

**3** – SoA'da `ilerlet`, 3 ayrı çıktı dizisine yazıyor. Bir satırın bir kısmına yazmak neden tamamını okumayı gerektirir? (Ders 7.25, *write-allocate*.)

**4** – Bir oyunda 10 000 varlığın konumu her karede güncelleniyor, adları yalnız ekranda tıklandığında okunuyor. Hangi düzeni seçersin?

**5** – SoA'nın dezavantajı: tek bir parçacığı silmek veya sıralamak. 8 diziyi aynı sırayla sıralamak için ne yapmak gerekir?

<details>
<summary>Cevaplar</summary>

**1** – Her blokta `kutle` tam bir satır olur, satırın tamamı kullanılır. Dokunulan bayt SoA ile aynı olur (16.8 MB) ama satırlar ardışık değil, 1 KB arayla. Beklenti: AoSoA-8'den hızlı, ama 4. bölümdeki sonuç yüzünden SoA'dan yavaş olabilir. Ölçmedim; ölçüm senin.

**2** – `float32x4x3_t p = vld3q_f32(a + 3 * i);` ile dört noktanın `x`, `y`, `z`'si üç register'a gelir; `p.val[0] = vaddq_f32(p.val[0], dx)` gibi üç toplama, sonra `vst3q_f32(a + 3 * i, p)`. Ayırma komutları en fazla 4 alanı (`vld4q`) destekliyor; 8 alanlı struct için ya iki `vld4q` sonucunu karıştırmak ya da kullanılmayan alanları da okumak gerekiyor. Derleyicinin "yararsız" kararı bu maliyetten.

**3** – Önbellek satır parçasını yazamaz; satırın tamamı önbellekte olmalı. Yazma ıskası olunca satır önce bellekten okunur (write-allocate), sonra değiştirilir, sonra geri yazılır. Yani her yazma bir okuma + bir yazma maliyeti taşıyor.

**4** – Sıcak/soğuk ayrımı: konum ve hız ayrı bir dizide (SoA ya da küçük AoS), ad ayrı bir dizide. 10 000 varlıkla sıcak veri 240 KB, çoğu önbellekte kalır.

**5** – Önce bir indis permütasyonu hesapla (bir `int` dizisini anahtara göre sırala), sonra her diziyi bu permütasyonla yeniden düzenle (8 geçiş). Silmede genelde "son elemanı silinenin yerine koy" yöntemi tercih edilir; 8 dizide de aynı indis.

</details>

---

## Kaynaklar

- Mike Acton, "Data-Oriented Design and C++", CppCon 2014.
- Intel, "Memory Layout Transformations" (AoS, SoA, AoSoA), Intel geliştirici makaleleri.
- Matt Pharr ve William R. Mark, "ispc: A SPMD Compiler for High-Performance CPU Programming", *InPar 2012*.
- Ulrich Drepper, *What Every Programmer Should Know About Memory*, 2007, Bölüm 6.

**Sıradaki ders:** Cache optimizasyonu derinlemesine. Prefetch, false sharing, cache line hizalama, tiling parametresi seçimi.
