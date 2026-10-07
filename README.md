# 0'dan Yazılım Öğreniyorum

Temelden derinliğe: sıfırdan, hazır fonksiyon kullanmadan, sağlam temellerle yazılım.

**Siteyi oku:** https://[KULLANICI-ADIN].github.io/yazilim-ogrenelim/

Bu depo serinin kaynağıdır. Dersler `src/content/docs/` klasöründe Markdown olarak durur; site bu dosyalardan [Starlight](https://starlight.astro.build) ile otomatik üretilir.

## Depo yapısı

```
astro.config.mjs            Site ayarları
src/fazlar.mjs              Faz başlıkları ve duraklar
src/content/docs/index.mdx  Ana sayfa (Bu seri hakkında)
src/content/docs/icindekiler.mdx  Kendiliğinden dolan içindekiler ağacı
src/content/docs/faz-NN/    Her fazın dersleri
src/assets/                 Görseller
src/styles/ozel.css         Alıştırma kutularının görünümü
DERS-SABLONU.md             Yeni ders için başlangıç şablonu
.github/workflows/          Otomatik yayın ayarı
```

Faz 2'den itibaren her fazın C kodları `kod/faz-NN/` klasörlerinde yer alacak.

## Yeni ders eklemek

1. `DERS-SABLONU.md` dosyasını `src/content/docs/faz-NN/MM-ders-adi.md` olarak kopyala (ör. `faz-01/01-algoritma.md`).
2. En üstteki `title` satırına dersin adını yaz (ör. `"1.1 Algoritma ve problem çözme"`).
3. İstersen `description` satırına bir cümlelik özet yaz; İçindekiler ağacında dersin altında görünür.
4. GitHub'a gönder. Menü ve İçindekiler kendiliğinden güncellenir; yeni bir fazın ilk dersiyse faz da belirir.

## Bilgisayarında önizleme

1. [Node.js](https://nodejs.org) 22 veya üstünü kur.
2. Depo klasöründe bir kez `npm install`, sonra `npm run dev` çalıştır.
3. Terminaldeki adresi (http://localhost:4321/yazilim-ogrenelim/) aç. Dosyaları kaydettikçe sayfa kendiliğinden yenilenir.

## Katkı

Bir hata, yazım yanlışı ya da anlaşılmayan bir yer gördüysen her sayfanın altındaki "Sayfayı düzenle" bağlantısından değişiklik önerebilir ya da bir "issue" açabilirsin.

## Lisans

[Lisans seçimini buraya yaz. Öneri: ders metinleri için CC BY-SA 4.0, kodlar için MIT.]
