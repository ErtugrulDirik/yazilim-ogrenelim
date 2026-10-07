// Ders metinlerindeki bağlantıları sitenin adresine göre düzenler:
// 1) "/" ile başlayan bağlantıların başına base yolu ekler: /icindekiler/ → /yazilim-ogrenelim/icindekiler/
// 2) %SITE_URL% gibi yer tutucuları gerçek değerle değiştirir (kod blokları dahil).
import { BASE, YER_TUTUCULAR } from '../site.mjs';

function degistir(metin) {
	for (const [anahtar, deger] of Object.entries(YER_TUTUCULAR)) metin = metin.split(anahtar).join(deger);
	return metin;
}

function kokBaglantisi(url) {
	if (typeof url !== 'string' || !url.startsWith('/') || url.startsWith('//')) return url;
	if (url === BASE || url.startsWith(BASE + '/')) return url;
	return BASE + url;
}

function gez(dugum) {
	if (typeof dugum.value === 'string') dugum.value = degistir(dugum.value);
	if (dugum.type === 'link' || dugum.type === 'definition') dugum.url = kokBaglantisi(degistir(dugum.url));
	if (dugum.type === 'html') {
		dugum.value = dugum.value.replace(/href="(\/[^"]*)"/g, (_, u) => `href="${kokBaglantisi(u)}"`);
	}
	if (dugum.type === 'mdxJsxFlowElement' || dugum.type === 'mdxJsxTextElement') {
		for (const nitelik of dugum.attributes ?? []) {
			if (nitelik.name === 'href' && typeof nitelik.value === 'string') nitelik.value = kokBaglantisi(degistir(nitelik.value));
		}
	}
	for (const cocuk of dugum.children ?? []) gez(cocuk);
}

export default function siteBaglantilari() {
	return (agac) => gez(agac);
}
