---
title: "0.1 Yol haritası"
---

<!-- Yol haritası görselini PNG olarak dışa aktarıp src/assets/yol-haritasi.png
     adıyla kaydettikten sonra alttaki satırın başındaki ve sonundaki yorum
     işaretlerini kaldır.
![Yol haritası](../../../assets/yol-haritasi.png)
-->

Bu seri tek bir bitten başlar ve kendi programlama dilimizi, o dilden kod üreten araçları ve en sonunda bu araçları üreten araçları yazmakla biter. Yol 23 faza ve beş durağa ayrılmıştır.

## Beş durak

| Durak | Fazlar | Konu | Çıkışta ne yapabilirsin? |
| --- | --- | --- | --- |
| 1. Temeller | 0–2 | Bit ve sayı sistemleri, algoritma ve akış diyagramı, sadece `int` ile C | Kağıtta düşünüp C'de yazabilirsin. |
| 2. Makinenin dili | 3–5 | Veri tipleri, bellek ve pointer, bit manipülasyonu | Standart kütüphaneyi sıfırdan yazabilirsin. |
| 3. Matematik ve makine | 6–7 | Ayrık matematik ve soyut cebir, mimari ve assembly | C kodunun makinede neye dönüştüğünü okuyabilirsin. |
| 4. Sistem ve performans | 8–13 | Veri yapıları, algoritmalar, işletim sistemi, SIMD, cebirsel hesaplama, C++ | Hızlı ve sağlam sistem yazılımı yazabilirsin. |
| 5. Dil ve üretici | 14–22 | Hesaplama kuramı, dil işleme, semantik, DSL, matematik tabanlı kod üreticileri, üretici üreten üreticiler, araştırma | Kod üreten kodu yazabilirsin. |

## Ortak ip: VKİ programı

Seri boyunca aynı küçük program büyüyecek: vücut kitle endeksi (VKİ = kilo / boy²).

- **Faz 1:** Kağıtta akış diyagramı olarak.
- **Faz 2:** Sadece `int` iln sonuç 22 çıkae. 70 kg ve 175 cm içir, oysa gerçek değer 22,86'dır. Neden? Bunu orada göreceğiz.
- **Faz 3:** Doğru veri tipleriyle. Hassasiyet geri gelir.
- **Faz 18:** Kendi yazdığımız küçük bir dilden, birimleri denetlenerek otomatik üretilmiş C kodu olarak.

## Neler gerekli?

- **Faz 0 ve Faz 1:** Sadece kağıt ve kalem.
- **Faz 2'den itibaren:** Linux (Windows'ta WSL), `gcc`, `gdb` ve tarayıcıda [Compiler Explorer](https://godbolt.org). Kurulum Ders 2.1'de anlatılıyor.

Başlangıç için üç kitap önerilir:

- Charles Petzold, *Code: The Hidden Language of Computer Hardware and Software*
- Brian Kernighan & Dennis Ritchie, *The C Programming Language*
- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective*

## Bu seri nasıl takip edilir?

- Her alıştırmada okumayı bırak, önce kendin çöz. Cevaplar kapalı kutularda.
- Ayrı bir defter tut. Elle yazmak, okumaktan çok daha kalıcıdır.
- Düzenli ilerle. Haftada birkaç ders, ayda bir kez yapılan uzun bir çalışmadan iyidir.
- Takıldığın yerde soru sor: [soru sorma yerinin linki: GitHub Discussions, Discord vb.]

Bir sonraki derste en temel soruyla başlıyoruz: bilgisayar nedir ve neden sadece sayıları bilir?
