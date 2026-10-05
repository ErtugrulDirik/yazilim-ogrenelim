// @ts-check
import { readdirSync, existsSync } from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { unified } from '@astrojs/markdown-remark';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';

// ── Doldurman gereken tek yer ──────────────────────────────────────────────
const GITHUB_KULLANICI = 'KULLANICI-ADIN';
const DEPO = 'yazilim-ogrenelim';
// ───────────────────────────────────────────────────────────────────────────

const DEPO_URL = `https://github.com/${GITHUB_KULLANICI}/${DEPO}`;

// Faz başlıkları. Menüde bir faz, ancak klasöründe en az bir ders olduğunda görünür.
const FAZLAR = {
	0: 'Yol haritası ve bilgisayarın temeli',
	1: 'Algoritma, akış diyagramı ve iz sürme',
	2: "C'ye giriş: sadece int",
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
	15: 'Derleyici ön yüzü',
	16: 'Ara temsil, SSA ve optimizasyon',
	17: 'Programlama dili semantiği ve tip kuramı',
	18: 'DSL tasarımı ve kod üretimi',
	19: 'Matematik tabanlı kod üreticileri',
	20: 'Üretici üreten üreticiler',
	21: 'Bitirme projeleri',
	22: 'Araştırma sınırı: bilgi üretmek',
};

// src/content/docs/faz-NN klasörlerini tarar; içinde ders olan her faz menüye eklenir.
// Fazın içindeki dersler dosya adına göre (01-, 02-, ...) sıralanır ve kendiliğinden listelenir.
function fazMenusu() {
	const kok = new URL('./src/content/docs/', import.meta.url);
	if (!existsSync(kok)) return [];
	return readdirSync(kok, { withFileTypes: true })
		.filter((g) => g.isDirectory() && /^faz-\d{2}$/.test(g.name))
		.filter((g) =>
			readdirSync(new URL(`${g.name}/`, kok)).some((f) => /^[^_].*\.mdx?$/.test(f)),
		)
		.sort((a, b) => a.name.localeCompare(b.name))
		.map((g) => {
			const no = Number(g.name.slice(4));
			return {
				label: `Faz ${no} — ${FAZLAR[no] ?? ''}`.trim(),
				collapsed: no > 0,
				items: [{ autogenerate: { directory: g.name } }],
			};
		});
}

export default defineConfig({
	site: `https://${GITHUB_KULLANICI.toLowerCase()}.github.io`,
	base: `/${DEPO}`,
	markdown: {
		// Formüller için: $...$ satır içi, $$...$$ blok (KaTeX ile çizilir)
		processor: unified({ remarkPlugins: [remarkMath], rehypePlugins: [rehypeKatex] }),
	},
	integrations: [
		starlight({
			title: "0'dan Yazılım Öğreniyorum",
			description: 'Bitten kod üreten koda: sıfırdan, sağlam temellerle yazılım.',
			defaultLocale: 'root',
			locales: { root: { label: 'Türkçe', lang: 'tr' } },
			social: [{ icon: 'github', label: 'GitHub', href: DEPO_URL }],
			editLink: { baseUrl: `${DEPO_URL}/edit/main/` },
			lastUpdated: true,
			customCss: ['katex/dist/katex.min.css', './src/styles/ozel.css'],
			sidebar: [{ label: 'Bu seri hakkında', link: '/' }, ...fazMenusu()],
		}),
	],
});
