// Sitenin adresiyle ilgili her şey buradan okunur. GitHub kullanıcı adını ya da
// depo adını değiştirirsen sadece bu iki satırı değiştirmen yeterli.
export const GITHUB_KULLANICI = 'ErtugrulDirik';
export const DEPO = 'yazilim-ogrenelim';

export const BASE = `/${DEPO}`;
export const SITE = `https://${GITHUB_KULLANICI.toLowerCase()}.github.io`;
export const SITE_URL = `${SITE}${BASE}`;
export const DEPO_URL = `https://github.com/${GITHUB_KULLANICI}/${DEPO}`;

// Ders metinlerinde kullanılabilen yer tutucular; derleme sırasında gerçek değerle değişir.
export const YER_TUTUCULAR = {
	'%SITE_URL%': SITE_URL,
	'%DEPO_URL%': DEPO_URL,
};
