// Faz başlıkları ve duraklar. Hem menü (astro.config.mjs) hem İçindekiler sayfası buradan okur.
// Bir faz, menüde ve İçindekiler ağacında ancak klasöründe en az bir ders olduğunda görünür.
export const FAZLAR = {
	0: 'Bilgisayarın temeli',
	1: 'Algoritma, akış diyagramı ve iz sürme',
	2: "C'ye giriş",
	3: 'Veri tipleri ve dönüşümler',
	4: 'Diziler, pointer, bellek ve string kütüphanesi',
	5: 'Bit manipülasyonu',
	6: 'Matematik temelleri ve soyut cebir',
	7: 'Bilgisayar mimarisi ve assembly',
	8: 'Veri yapıları',
	9: 'Algoritmalar',
	10: 'İşletim sistemi ve sistem programlama',
	11: 'Performans, cache ve SIMD',
	12: 'Cebirsel hesaplama',
	13: 'C++ ve nesne yönelimli programlama',
	14: 'Hesaplama kuramı ve biçimsel diller',
	15: 'Dil işleme',
	16: 'Ara temsil, SSA ve optimizasyon',
	17: 'Programlama dili semantiği ve tip kuramı',
	18: 'DSL tasarımı ve kod üretimi',
	19: 'Matematik tabanlı kod üreticileri',
	20: 'Üretici üreten üreticiler',
	21: 'Bitirme projeleri',
	22: 'Araştırma sınırı: bilgi üretmek',
};

export const DURAKLAR = [
	{ ad: 'Temeller', fazlar: [0, 2], ozet: 'Kağıtta düşünüp C’de yazabilirsin.' },
	{ ad: 'Makinenin dili', fazlar: [3, 5], ozet: 'Standart kütüphaneyi sıfırdan yazabilirsin.' },
	{ ad: 'Matematik ve makine', fazlar: [6, 7], ozet: 'Kodun makinede neye dönüştüğünü okuyabilirsin.' },
	{ ad: 'Sistem ve performans', fazlar: [8, 13], ozet: 'Hızlı ve sağlam sistem yazılımı yazabilirsin.' },
	{ ad: 'Dil ve üretici', fazlar: [14, 22], ozet: 'Kod üreten kodu yazabilirsin.' },
];
