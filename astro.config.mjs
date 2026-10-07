// @ts-check
import { readdirSync, existsSync } from 'node:fs';
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { unified } from '@astrojs/markdown-remark';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import { FAZLAR } from './src/fazlar.mjs';

// ── Doldurman gereken tek yer ──────────────────────────────────────────────
const GITHUB_KULLANICI = 'DirikTi';
const DEPO = 'yazilim-ogrenelim';
// ───────────────────────────────────────────────────────────────────────────

const DEPO_URL = `https://github.com/${GITHUB_KULLANICI}/${DEPO}`;


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
			description: 'Temelden derinliğe: sıfırdan, sağlam temellerle yazılım.',
			logo: { src: './src/assets/logo.svg' },
			favicon: '/favicon.svg',
			defaultLocale: 'root',
			locales: { root: { label: 'Türkçe', lang: 'tr' } },
			social: [{ icon: 'github', label: 'GitHub', href: DEPO_URL }],
			editLink: { baseUrl: `${DEPO_URL}/edit/main/` },
			lastUpdated: true,
			customCss: ['katex/dist/katex.min.css', './src/styles/ozel.css'],
			sidebar: [
				{ label: 'Bu seri hakkında', link: '/' },
				{ label: 'İçindekiler', link: '/icindekiler/' },
				...fazMenusu(),
			],
		}),
	],
});
