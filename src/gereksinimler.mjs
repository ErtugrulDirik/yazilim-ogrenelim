// Kurulum gereksinimleri. Hem derslerin başındaki gereksinim kutusu hem /kurulum/ sayfası buradan okur.
// - sayfa: kurulumun anlatıldığı sayfa (null ise sayfa henüz yazılmadı)
// - windows: 'yerel' → Windows'ta doğrudan kurulur; 'wsl' → Windows'ta WSL gerekir
export const GEREKSINIMLER = {
	editor: {
		ad: 'Kod editörü',
		ozet: 'VS Code (önerilen) ya da CLion',
		sayfa: '/kurulum/editor/',
		windows: 'yerel',
	},
	llvm: {
		ad: 'clang ve LLDB',
		ozet: 'LLVM projesinin compiler ve debugger’ı, bir de make',
		sayfa: '/kurulum/llvm/',
		windows: 'yerel',
	},
	linux: {
		ad: 'Linux ortamı',
		ozet: 'Linux’ta hazırsın; Windows’ta WSL, macOS’ta Linux sanal makinesi',
		sayfa: '/kurulum/linux/',
		windows: 'wsl',
	},
	lean: { ad: 'Lean 4', ozet: 'Kanıt yardımcısı', sayfa: null, windows: 'yerel' },
	z3: { ad: 'Z3', ozet: 'SMT çözücü', sayfa: null, windows: 'yerel' },
	latex: { ad: 'LaTeX', ozet: 'Makale yazımı', sayfa: null, windows: 'yerel' },
};

// Her fazın gereksinimleri. Boş liste: kağıt ve kalem yeterli.
// Tek bir dersin ek gereksinimi varsa dersin kendi frontmatter'ına yazılır:
//   gereksinimler: [linux]
//   gereksinimNotu: "Neden gerektiğini anlatan bir cümle."
//   windowsNotu: "Windows'ta farklı olan bir şey varsa."
const TEMEL = ['editor', 'llvm'];
export const FAZ_GEREKSINIMLERI = {
	0: [],
	1: [],
	2: TEMEL,
	3: TEMEL,
	4: TEMEL,
	5: TEMEL,
	6: TEMEL,
	7: [...TEMEL, 'linux'],
	8: TEMEL,
	9: TEMEL,
	10: [...TEMEL, 'linux'],
	11: [...TEMEL, 'linux'],
	12: TEMEL,
	13: TEMEL,
	14: TEMEL,
	15: TEMEL,
	16: TEMEL,
	17: [...TEMEL, 'lean'],
	18: TEMEL,
	19: [...TEMEL, 'z3'],
	20: TEMEL,
	21: TEMEL,
	22: ['latex', 'lean'],
};

// Bir fazın ya da tek bir dersin bütün gereksinimleri (tekrarsız, faz sırası korunur).
export function gereksinimListesi(faz, dersEk = []) {
	return [...new Set([...(FAZ_GEREKSINIMLERI[faz] ?? []), ...dersEk])];
}
