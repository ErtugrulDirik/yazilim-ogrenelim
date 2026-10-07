// Ana sayfadaki büyük butonlar (hero) Markdown'dan geçmediği için bağlantılarına
// base yolunu burada ekliyoruz: link: /icindekiler/ → /yazilim-ogrenelim/icindekiler/
import { defineRouteMiddleware } from '@astrojs/starlight/route-data';
import { BASE } from '../site.mjs';

export const onRequest = defineRouteMiddleware((context) => {
	const hero = context.locals.starlightRoute.entry.data.hero;
	for (const eylem of hero?.actions ?? []) {
		if (eylem.link.startsWith('/') && !eylem.link.startsWith('//') && !eylem.link.startsWith(BASE + '/')) {
			eylem.link = BASE + eylem.link;
		}
	}
});
