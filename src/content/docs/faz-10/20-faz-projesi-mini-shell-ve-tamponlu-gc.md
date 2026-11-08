---
title: "10.20 Faz projesi: mini shell ve tamponlu G/Ç"
description: "Faz 10'un bütün parçaları tek programda: boru hatları, < > >> 2> 2>&1 yönlendirmeleri, tek ve çift tırnak, $AD, ${AD}, $? genişletmesi, ; && || ve arka plan işleri, Ctrl+C için süreç grupları ve tcsetpgrp, Ders 10.3'teki tg kütüphanesiyle G/Ç; stdin'i komutlarla paylaşınca tamponun neden tehlikeli olduğu; bash ile fark testi ve bu testin yakaladığı $? genişletme hatası; 35 satırlık senaryo, 9 birim testi, sözde terminalde Ctrl+C testi ve sanitizer."
---

Bu proje fazın neredeyse her dersini bir araya getiriyor. Ders 10.5'teki 150 satırlık kabuğu gerçek bir araca çeviriyoruz: istediğin uzunlukta boru hattı, tırnaklar, değişkenler, koşullu çalıştırma, arka plan işleri, düzgün `Ctrl+C`. G/Ç için de Ders 10.3'te yazdığımız `tg` kütüphanesini kullanıyoruz. Ders 9.24'teki proje gibi, işin büyük kısmı algoritma değil, **kenar durumlar**.

| Özellik | Ders |
| --- | --- |
| `fork`, `exec`, `wait`, çıkış kodları | 10.4 |
| `pipe`, `dup2`, kullanılmayan uçları kapatmak | 10.2, 10.5 |
| `O_CLOEXEC`, `F_DUPFD_CLOEXEC` | 10.4 |
| Tamponlu G/Ç, `fork` öncesi boşaltma | 10.3 |
| `SIGINT`'i kabukta yok sayıp çocukta geri açmak | 10.6 |
| Süreç grupları ve ön plan terminali | 10.6 |
| Zombi toplamak | 10.4, 10.6 |

```
proje/
├── tg.h, tg.c     Ders 10.3'teki tamponlu G/Ç
├── kabuk.c        belirteçler, ayrıştırıcı, yürütücü
├── Makefile
├── senaryo.txt    bash ile karşılaştırılan komutlar
├── test.sh        fark testi + birim testleri
└── etkilesim.py   sözde terminalde Ctrl+C testi
```

`tg.h` ve `tg.c`, Ders 10.3'teki halleriyle aynı; hiçbir değişiklik gerekmedi.

---

## 1. Kabuk dilinin yapısı

Ders 10.5'te satırı boşluklardan bölmüştük. Gerçek dil için üç katman gerekiyor ve bu, Faz 15'te yazacağımız derleyici ön ucunun küçük bir kopyası:

1. **Belirteçlere ayırma (lexer)**: `echo "a b" > x` → `KELIME(echo) KELIME(a b) CIKTI KELIME(x)`. Tırnaklar ve `$` burada çözülüyor.
2. **Ayrıştırma (parser)**: belirteçlerden yapı kurmak.
3. **Yürütme**: yapıyı `fork`/`exec` çağrılarına çevirmek.

Dilin dilbilgisi:

```
satir    := hat ( (';' | '&' | '&&' | '||') hat )* [';' | '&']
hat      := komut ( '|' komut )*
komut    := ( KELIME | yonlendirme )+
yonlendirme := '<' KELIME | '>' KELIME | '>>' KELIME | '2>' KELIME | '2>&1'
```

Kabukta yönlendirmeler **soldan sağa** uygulanır; bu yüzden `Yon` dizisinde sıralarıyla tutuluyor (Ders 10.5'in Alıştırma 5'i).

---

## 2. Tam kod

```c
/* kabuk: boru hatti, yonlendirme, tirnak, degisken, ; && || & ve is denetimi */
#include "tg.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <termios.h>
#include <unistd.h>

enum { EN_ARG = 128, EN_KOMUT = 32, EN_YON = 8, EN_BELIRTEC = 1024, SATIR = 4096, HAVUZ = 65536 };

/* ---- belirtecler ---- */
typedef enum { K_KELIME, K_BORU, K_VE, K_VEYA, K_NOKTALI, K_ARKA, K_GIRDI, K_CIKTI, K_EKLE, K_HATA, K_HATA_CIKTI, K_SON } Tur;
typedef struct { Tur tur; char *metin; } Belirtec;

typedef struct { Tur tur; char *dosya; } Yon;             /* soldan saga uygulanir */
typedef struct { char *argv[EN_ARG]; int argc; Yon yon[EN_YON]; int yonsay; } Komut;
typedef struct { Komut k[EN_KOMUT]; int n; int arka; } Hat;

static TG *cikti, *hatalar;
static int son_durum = 0, etkilesimli = 0;
static pid_t kabuk_grubu;
static char havuz[HAVUZ];
static size_t havuz_son;

static void yaz(TG *f, const char *s) { tg_yaz(f, s, strlen(s)); }
static void hata(const char *a, const char *b) { yaz(hatalar, "kabuk: "); yaz(hatalar, a); if (b) { yaz(hatalar, ": "); yaz(hatalar, b); } yaz(hatalar, "\n"); }

/* havuzdaki gecerli kelimeye bir bayt ekle */
static int ekle(char c) { if (havuz_son + 1 >= HAVUZ) return -1; havuz[havuz_son++] = c; return 0; }

static int ekle_s(const char *s) { for (; *s; s++) if (ekle(*s) < 0) return -1; return 0; }

/* *ps '$' uzerinde; degiskeni havuza genislet */
static int genislet(const char **ps) {
    const char *s = *ps + 1;
    if (*s == '?') { char t[16]; snprintf(t, sizeof t, "%d", son_durum); *ps = s + 1; return ekle_s(t); }
    if (*s == '$') { char t[16]; snprintf(t, sizeof t, "%d", (int)getpid()); *ps = s + 1; return ekle_s(t); }
    int parantez = *s == '{';
    if (parantez) s++;
    const char *b = s;
    while (*s == '_' || (*s >= 'a' && *s <= 'z') || (*s >= 'A' && *s <= 'Z') || (s > b && *s >= '0' && *s <= '9')) s++;
    if (s == b) { *ps = s; return ekle('$'); }           /* tek basina $ */
    char ad[128]; size_t n = (size_t)(s - b);
    if (n >= sizeof ad) return -1;
    memcpy(ad, b, n); ad[n] = 0;
    if (parantez) { if (*s != '}') return -1; s++; }
    const char *d = getenv(ad);
    *ps = s;
    return d ? ekle_s(d) : 0;
}

/* *ps'den bir hat kadar belirtec okur: ayirici (; & && ||) dahil, orada durur.
   Genisletme burada oldugu icin bir hat ancak calisacagi anda okunmali. */
static int bol(const char **ps, Belirtec *b) {
    const char *s = *ps;
    int n = 0; havuz_son = 0;
    for (;;) {
        while (*s == ' ' || *s == '\t' || *s == '\n') s++;
        if (!*s || *s == '#') { s += strlen(s); break; }
        if (n == EN_BELIRTEC - 1) { hata("cok fazla belirtec", NULL); return -1; }
        Belirtec *t = &b[n++]; t->metin = NULL;
        if (s[0] == '|' && s[1] == '|') { t->tur = K_VEYA; s += 2; break; }
        if (s[0] == '&' && s[1] == '&') { t->tur = K_VE; s += 2; break; }
        if (*s == '|') { t->tur = K_BORU; s++; continue; }
        if (*s == '&') { t->tur = K_ARKA; s++; break; }
        if (*s == ';') { t->tur = K_NOKTALI; s++; break; }
        if (*s == '<') { t->tur = K_GIRDI; s++; continue; }
        if (s[0] == '>' && s[1] == '>') { t->tur = K_EKLE; s += 2; continue; }
        if (*s == '>') { t->tur = K_CIKTI; s++; continue; }
        if (!strncmp(s, "2>&1", 4)) { t->tur = K_HATA_CIKTI; s += 4; continue; }
        if (s[0] == '2' && s[1] == '>') { t->tur = K_HATA; s += 2; continue; }

        t->tur = K_KELIME; t->metin = havuz + havuz_son;
        int tirnak = 0;
        size_t bas = havuz_son;
        while (*s && !strchr(" \t\n|&;<>", *s)) {
            if (*s == '\'') {
                tirnak = 1; s++;
                while (*s && *s != '\'') if (ekle(*s++) < 0) goto tasti;
                if (!*s) { hata("kapanmamis tirnak", "'"); return -1; }
                s++;
            } else if (*s == '"') {
                tirnak = 1; s++;
                while (*s && *s != '"') {
                    if (*s == '\\' && s[1] && strchr("\"\\$", s[1])) { if (ekle(s[1]) < 0) goto tasti; s += 2; }
                    else if (*s == '$') { if (genislet(&s) < 0) goto tasti; }
                    else if (ekle(*s++) < 0) goto tasti;
                }
                if (!*s) { hata("kapanmamis tirnak", "\""); return -1; }
                s++;
            } else if (*s == '\\' && s[1]) { if (ekle(s[1]) < 0) goto tasti; s += 2; }
            else if (*s == '$') { if (genislet(&s) < 0) goto tasti; }
            else if (ekle(*s++) < 0) goto tasti;
        }
        if (ekle(0) < 0) goto tasti;
        if (!tirnak && havuz_son - 1 == bas) { n--; havuz_son = bas; }  /* bos genisleme: kelime yok */
    }
    b[n].tur = K_SON; b[n].metin = NULL;
    *ps = s;
    return n;
tasti:
    hata("satir cok uzun", NULL);
    return -1;
}

/* ---- ayristirici ---- */
static int yon_mu(Tur t) { return t == K_GIRDI || t == K_CIKTI || t == K_EKLE || t == K_HATA || t == K_HATA_CIKTI; }

static int komut_ayristir(const Belirtec *b, int *pi, Komut *k) {
    int i = *pi;
    memset(k, 0, sizeof *k);
    while (b[i].tur == K_KELIME || yon_mu(b[i].tur)) {
        if (b[i].tur == K_KELIME) {
            if (k->argc == EN_ARG - 1) { hata("cok fazla arguman", NULL); return -1; }
            k->argv[k->argc++] = b[i++].metin;
            continue;
        }
        if (k->yonsay == EN_YON) { hata("cok fazla yonlendirme", NULL); return -1; }
        Yon *y = &k->yon[k->yonsay++]; y->tur = b[i].tur; y->dosya = NULL; i++;
        if (y->tur != K_HATA_CIKTI) {
            if (b[i].tur != K_KELIME) { hata("sozdizimi", "yonlendirmeden sonra dosya adi bekleniyor"); return -1; }
            y->dosya = b[i++].metin;
        }
    }
    k->argv[k->argc] = NULL;
    if (k->argc == 0) { hata("sozdizimi", "bos komut"); return -1; }
    *pi = i;
    return 0;
}

/* tek hatti ayristirir; *sonraki: bu hattan sonraki baglac */
static int ayristir(const Belirtec *b, Hat *h, Tur *sonraki) {
    int i = 0;
    h->n = 0; h->arka = 0; *sonraki = K_NOKTALI;
    for (;;) {
        if (h->n == EN_KOMUT) { hata("boru hatti cok uzun", NULL); return -1; }
        if (komut_ayristir(b, &i, &h->k[h->n++]) < 0) return -1;
        if (b[i].tur != K_BORU) break;
        i++;
    }
    switch (b[i].tur) {
        case K_SON: case K_NOKTALI: break;
        case K_ARKA: h->arka = 1; break;
        case K_VE:   *sonraki = K_VE; break;
        case K_VEYA: *sonraki = K_VEYA; break;
        default: hata("sozdizimi", "beklenmeyen belirtec"); return -1;
    }
    return 0;
}

/* ---- yurutme ---- */
static void yonlendir(const Komut *k) {
    for (int i = 0; i < k->yonsay; i++) {
        const Yon *y = &k->yon[i];
        if (y->tur == K_HATA_CIKTI) { dup2(1, 2); continue; }
        int bayrak = y->tur == K_GIRDI ? O_RDONLY : y->tur == K_EKLE ? O_WRONLY | O_CREAT | O_APPEND : O_WRONLY | O_CREAT | O_TRUNC;
        int fd = open(y->dosya, bayrak, 0644);
        if (fd < 0) { fprintf(stderr, "kabuk: %s: %s\n", y->dosya, strerror(errno)); _exit(1); }
        dup2(fd, y->tur == K_GIRDI ? 0 : y->tur == K_HATA ? 2 : 1);
        close(fd);
    }
}

static void varsayilan_sinyaller(void) {
    int s[] = { SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU, SIGPIPE };
    for (size_t i = 0; i < sizeof s / sizeof *s; i++) signal(s[i], SIG_DFL);
}

static int durum_kodu(int d) { return WIFEXITED(d) ? WEXITSTATUS(d) : 128 + WTERMSIG(d); }

static int hat_calistir(const Hat *h) {
    pid_t pid[EN_KOMUT], grup = 0; int onceki = -1;
    tg_bosalt(cikti);                                     /* fork tamponu kopyalamasin: Ders 10.3 */
    for (int i = 0; i < h->n; i++) {
        int b[2] = { -1, -1 };
        if (i < h->n - 1 && pipe(b) < 0) { hata("pipe", strerror(errno)); return 1; }
        pid_t p = fork();
        if (p < 0) { hata("fork", strerror(errno)); return 1; }
        if (p == 0) {
            if (etkilesimli) setpgid(0, grup);
            varsayilan_sinyaller();
            if (onceki >= 0) { dup2(onceki, 0); close(onceki); }
            if (b[1] >= 0) { dup2(b[1], 1); close(b[0]); close(b[1]); }
            yonlendir(&h->k[i]);
            execvp(h->k[i].argv[0], h->k[i].argv);
            int e = errno;
            fprintf(stderr, "kabuk: %s: %s\n", h->k[i].argv[0], strerror(e));
            _exit(e == ENOENT ? 127 : 126);
        }
        if (etkilesimli) { if (!grup) grup = p; setpgid(p, grup); }
        pid[i] = p;
        if (onceki >= 0) close(onceki);
        if (b[1] >= 0) close(b[1]);
        onceki = b[0];
    }
    if (h->arka) {
        char t[32]; snprintf(t, sizeof t, "[%d]\n", (int)pid[h->n - 1]);
        if (etkilesimli) { yaz(cikti, t); tg_bosalt(cikti); }
        return 0;
    }
    if (etkilesimli) tcsetpgrp(0, grup);
    int son = 0;
    for (int i = 0; i < h->n; i++) {
        int d;
        while (waitpid(pid[i], &d, 0) < 0) if (errno != EINTR) { d = 0; break; }
        if (i == h->n - 1) son = durum_kodu(d);
    }
    if (etkilesimli) tcsetpgrp(0, kabuk_grubu);
    return son;
}

/* yerlesik komut ise 1 dondurur, *sonuc'u ayarlar; exit icin -1 */
static int yerlesik(const Komut *k, int *sonuc) {
    if (!strcmp(k->argv[0], "exit")) { *sonuc = k->argc > 1 ? atoi(k->argv[1]) : son_durum; return -1; }
    if (!strcmp(k->argv[0], "cd")) {
        const char *h = k->argc > 1 ? k->argv[1] : getenv("HOME");
        if (!h || chdir(h) < 0) { hata(h ? h : "cd", h ? strerror(errno) : "HOME yok"); *sonuc = 1; } else *sonuc = 0;
        return 1;
    }
    if (!strcmp(k->argv[0], "export")) {
        for (int i = 1; i < k->argc; i++) {
            char *e = strchr(k->argv[i], '=');
            if (e) { *e = 0; setenv(k->argv[i], e + 1, 1); *e = '='; }
        }
        *sonuc = 0;
        return 1;
    }
    return 0;
}

static void arka_plani_topla(void) {
    int d; pid_t p;
    while ((p = waitpid(-1, &d, WNOHANG)) > 0)
        if (etkilesimli) { char t[64]; snprintf(t, sizeof t, "[%d] bitti (%d)\n", (int)p, durum_kodu(d)); yaz(cikti, t); tg_bosalt(cikti); }
}

/* bir satiri isler; kabuk cikmali ise 1 */
static int satir_isle(const char *s, int *cikis) {
    static Belirtec b[EN_BELIRTEC];
    static Hat h;
    Tur baglac = K_NOKTALI;
    for (;;) {
        int bn = bol(&s, b);
        if (bn < 0) { son_durum = 2; return 0; }
        if (bn == 0) {
            if (baglac != K_NOKTALI) { hata("sozdizimi", "baglactan sonra komut yok"); son_durum = 2; }
            return 0;
        }
        Tur sonraki;
        if (ayristir(b, &h, &sonraki) < 0) { son_durum = 2; return 0; }
        int atla = (baglac == K_VE && son_durum != 0) || (baglac == K_VEYA && son_durum == 0);
        baglac = sonraki;
        if (atla) continue;
        int r;
        if (h.n == 1 && !h.arka) {
            int y = yerlesik(&h.k[0], &r);
            if (y == -1) { *cikis = r; return 1; }
            if (y == 1) { son_durum = r; continue; }
        }
        son_durum = hat_calistir(&h);
    }
}

int main(int argc, char **argv) {
    cikti = tg_fdden(1, "w", TG_SATIR);
    hatalar = tg_fdden(2, "w", TG_YOK);
    TG *g;
    if (argc > 1) {
        int fd = open(argv[1], O_RDONLY);
        if (fd < 0) { hata(argv[1], strerror(errno)); return 127; }
        int yuksek = fcntl(fd, F_DUPFD_CLOEXEC, 10);       /* cocuklara sizmasin */
        close(fd);
        g = tg_fdden(yuksek, "r", TG_TAM);
    } else {
        g = tg_fdden(0, "r", TG_TAM);
        /* stdin'i cocuklarla paylasiyoruz: fazla okursak onlarin girdisini calariz */
        const char *t = getenv("KABUK_TAMPON");
        g->kap = t ? (size_t)atoi(t) : 1;
        etkilesimli = isatty(0);
    }
    if (etkilesimli) {
        int s[] = { SIGINT, SIGQUIT, SIGTSTP, SIGTTIN, SIGTTOU };
        for (size_t i = 0; i < sizeof s / sizeof *s; i++) signal(s[i], SIG_IGN);
        kabuk_grubu = getpid();
        setpgid(0, kabuk_grubu);
        tcsetpgrp(0, kabuk_grubu);
    }
    char satir[SATIR]; int cikis = 0;
    for (;;) {
        arka_plani_topla();
        if (etkilesimli) { yaz(cikti, "kabuk$ "); tg_bosalt(cikti); }
        if (!tg_satir(g, satir, sizeof satir)) { cikis = son_durum; break; }
        if (satir_isle(satir, &cikis)) break;
    }
    tg_kapat(g); tg_kapat(hatalar); tg_kapat(cikti);
    return cikis;
}
```

```make
CC      = cc
CFLAGS  = -O2 -g -Wall -Wextra -std=c11 -D_POSIX_C_SOURCE=200809L

kabuk: kabuk.o tg.o
	$(CC) $(CFLAGS) -o $@ $^

%.o: %.c tg.h
	$(CC) $(CFLAGS) -c $<

test: kabuk
	./test.sh

temizle:
	rm -f kabuk *.o

.PHONY: test temizle
```

---

## 3. Tasarım kararları

**Her hat çalışacağı anda ayrıştırılıyor.** İlk sürümde `bol` bütün satırı bir kerede belirteçlere ayırıyordu. `false; echo $?` satırı `0` yazdı, oysa `bash` `1` yazıyor: `$?` satır okunurken, yani `false` **çalışmadan önce** genişlemişti. Bu hatayı Bölüm 5'teki fark testi yakaladı. Düzeltme: `bol` yalnızca bir hattı okuyup duruyor; bir sonraki hat önceki bittikten sonra ayrıştırılıyor. Bedeli, satırın ilerisindeki sözdizimi hatasının geç fark edilmesi (`bash` satırı önce baştan sona ayrıştırır). `$?` doğru olduktan sonra bu küçük bir fark.

**Tampon ve stdin.** Betik dosyası verilince (`./kabuk betik`) komutları 4 KB'lık tamponla okuyoruz; dosyanın tanımlayıcısını 10'un üstüne taşıyıp `F_DUPFD_CLOEXEC` ile işaretliyoruz, çocuklara sızmasın. Ama komutlar **stdin**'den geliyorsa, çocuklar da aynı stdin'i miras alıyor. Fazladan okursak onların girdisini çalarız. `g->kap = 1` tampon kapasitesini 1 bayta indiriyor (bash'in de boruda yaptığı gibi). `KABUK_TAMPON` ortam değişkeniyle bunu bozup etkisini görelim:

```
$ printf "sh -c 'read x; echo aldim: \$x'\nbu satir sh icin\necho sonra\n" | ./kabuk
aldim: bu satir sh icin
sonra
$ printf "sh -c 'read x; echo aldim: \$x'\nbu satir sh icin\necho sonra\n" | KABUK_TAMPON=4096 ./kabuk
aldim:
kabuk: bu: No such file or directory
sonra
```

4 KB'lık tamponla kabuk üç satırı da tek `read`'de yuttu; `sh` boş boru buldu, ikinci satır komut sanılıp çalıştırıldı. Ders 10.3'te tamponu kazanç olarak yazmıştık; burada aynı tampon bir hata kaynağı.

**`fork` öncesi boşaltma.** `hat_calistir`'in ilk satırı `tg_bosalt(cikti)`: Ders 10.3'teki "fork tamponu kopyalar" hatası.

**Boru uçları.** Her döngü turunda ebeveyn, artık gerekmeyen uçları kapatıyor (`onceki` ve `b[1]`). Çocukta `dup2` sonrası da aynı. Bir fd unutulsa boru hattı Ders 10.5'teki gibi asılı kalır. Sızıntı olmadığının kanıtı:

```
$ ./kabuk f.txt          # icinde: ls -l /proc/self/fd
total 0
lrwx------ 1 root root 64 Nov  8 16:35 0 -> /dev/null
l-wx------ 1 root root 64 Nov  8 16:35 1 -> pipe:[391124]
l-wx------ 1 root root 64 Nov  8 16:35 2 -> pipe:[391125]
lr-x------ 1 root root 64 Nov  8 16:35 3 -> /proc/154/fd
```

0, 1, 2 ve `ls`'nin kendi okuduğu dizin. Betiğin tanımlayıcısı (`O_CLOEXEC`) yok.

**Yerleşikler sadece tek başına.** `cd` bir boru hattının içinde olursa alt süreçte çalışır ve etkisi kaybolur. `bash` da aynısını yapar (`cd / | cat` kabuğun dizinini değiştirmez).

**Hata kodları.** Komut bulunamazsa 127, çalıştırılamazsa 126, sinyalle ölürse `128 + sinyal`, sözdizimi hatası 2. Bu sayılar POSIX'in kabuk tanımından.

---

## 4. Ctrl+C neden bu kadar uzun

`Ctrl+C`'ye basınca terminal sürücüsü **ön plandaki süreç grubunun tamamına** `SIGINT` gönderiyor. Ders 10.5'teki kabuk çocuğuyla aynı gruptaydı, bu yüzden kendisi de ölüyordu. Doğru düzen:

1. Kabuk kendi grubunu kuruyor ve etkileşim sinyallerini **yok sayıyor** (`SIG_IGN`).
2. Her boru hattı kendi **süreç grubu** (`setpgid`). Grup kimliği, ilk çocuğun PID'si.
3. `setpgid` hem ebeveynde hem çocukta çağrılıyor: hangisinin önce çalışacağı belli değil (Ders 10.4), iki taraf da garanti altına alıyor.
4. `tcsetpgrp` ile bu grup terminalde ön plana geçiyor; hat bitince kabuk geri alıyor.
5. Çocuk `exec`'ten önce sinyalleri `SIG_DFL` yapıyor: `SIG_IGN` `exec`'ten geçer, işleyiciler geçmez (Ders 10.6, Alıştırma 5).

`SIGTTOU`'nun yok sayılması da gerekli: arka plandaki bir süreç grubu `tcsetpgrp` çağırırsa çekirdek ona `SIGTTOU` gönderir ve kabuk durur. Bunu `etkilesimli` değişkeniyle koşullu yapıyoruz; betik çalıştırırken terminal yok, gruplar da gereksiz.

---

## 5. Test

Bir kabuğun doğruluğunu ölçmenin en iyi yolu Ders 9.24'teki gibi: gerçek olanla karşılaştırmak. `senaryo.txt`'yi hem bizimkiyle hem `bash` ile çalıştırıp çıktıları `diff`'liyoruz.

```bash
echo merhaba dunya
echo 'tek  tirnak $HOME' "cift  tirnak"
echo "bosluk" "" son
export AD=ali SOYAD="veli can"
echo $AD "$SOYAD" ${AD}
echo a\ b \$AD "\$AD" "a\"b"
false; echo $?
true && echo ve-dogru
false && echo ve-yanlis
false || echo veya-yanlis
true || echo veya-dogru
false && echo x || echo y
echo bir; echo iki; echo uc
echo cikti > d1.txt; cat d1.txt
echo ek >> d1.txt; cat < d1.txt
wc -l < d1.txt > d2.txt; cat d2.txt
ls /yok-boyle 2> d3.txt; cat d3.txt | wc -l
ls /yok-boyle > d4.txt 2>&1; cat d4.txt | wc -l
ls /yok-boyle 2>&1 > d5.txt | wc -l; cat d5.txt | wc -l
seq 1 100000 | grep 7 | sed s/7/X/ | sort -r | head -n 3
seq 1 5 | tr -d '\n'; echo
yes | head -n 2
cd /usr; pwd
cd /; pwd
cd /tmp/w; pwd
sh -c 'exit 7'; echo $?
sh -c 'kill -TERM $$'; echo $?
echo "degisken yok: [$BOSUNA]"
echo $BOSUNA son
# yorum satiri
echo yorum # sondaki
ls -l /proc/self/fd | wc -l
```

```bash
#!/bin/bash
# Kabugun ciktisini ayni betikteki bash davranisiyla karsilastirir
set -u
./kabuk senaryo.txt > kabuk.out 2>/dev/null; k=$?
bash senaryo.txt > bash.out 2>/dev/null; b=$?
if diff kabuk.out bash.out > fark.txt && [ $k = $b ]; then echo "FARK TESTI: gecti ($(wc -l < kabuk.out) satir)"; else echo "FARK TESTI: KALDI (cikis $k / $b)"; cat fark.txt; fi

gec=0; kal=0
dene() { # ad, beklenen, gercek
    if [ "$2" == "$3" ]; then gec=$((gec+1)); else kal=$((kal+1)); echo "KALDI: $1: beklenen [$2], gelen [$3]"; fi
}
dene "exit kodu" 3 "$(printf 'exit 3\n' | ./kabuk; echo $?)"
dene "son durum" 1 "$(printf 'false\n' | ./kabuk; echo $?)"
dene "bulunamadi" 127 "$(printf 'yok-boyle-komut\n' | ./kabuk 2>/dev/null; echo $?)"
dene "kapanmamis tirnak" 2 "$(printf "echo 'a\n" | ./kabuk 2>/dev/null; echo $?)"
dene "bos komut" 2 "$(printf '| wc\n' | ./kabuk 2>/dev/null; echo $?)"
dene "stdin paylasimi" "aldim: bu satir sh icin
sonra" "$(printf "sh -c 'read x; echo aldim: \$x'\nbu satir sh icin\necho sonra\n" | ./kabuk 2>/dev/null)"
dene "arka plan" "x
y" "$(printf 'sh -c "sleep 0.2; echo y" &\necho x\nsleep 0.5\n' | ./kabuk)"
dene "uzun boru" 500 "$(printf 'seq 1 1000 | cat | cat | cat | cat | cat | cat | cat | head -n 500 | wc -l\n' | ./kabuk)"
python3 etkilesim.py; [ $? = 0 ] && gec=$((gec+1)) || { kal=$((kal+1)); echo "KALDI: etkilesim"; }
echo "birim: $gec gecti, $kal kaldi"
[ $kal = 0 ]
```

Sözde terminal testi, Python'un `pty` modülüyle gerçek bir terminal oturumu kuruyor ve gerçekten `Ctrl+C` karakterini (`\x03`) gönderiyor:

```python
#!/usr/bin/env python3
# Terminal uzerinden kabuk: Ctrl+C sadece on plandaki komutu oldurmeli
import os, pty, select, sys, time

pid, fd = pty.fork()
if pid == 0:
    os.execv("./kabuk", ["./kabuk"])

def oku(sure):
    bitis, b = time.time() + sure, b""
    while time.time() < bitis:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            try: b += os.read(fd, 4096)
            except OSError: break
    return b.decode(errors="replace")

oku(0.3)
os.write(fd, b"sleep 30\n"); oku(0.5)
t0 = time.time()
os.write(fd, b"\x03"); oku(0.5)
os.write(fd, b"echo hayatta $?\n"); c = oku(0.5)
os.write(fd, b"exit 0\n"); oku(0.3)
_, d = os.waitpid(pid, 0)
print("Ctrl+C sonrasi cikti:", repr(c.split("\r\n")[1:2]))
sys.exit(0 if "hayatta 130" in c and os.WEXITSTATUS(d) == 0 else 1)
```

```
$ make test
./test.sh
FARK TESTI: gecti (35 satir)
Ctrl+C sonrasi cikti: ['hayatta 130']
birim: 9 gecti, 0 kaldi
```

İlk çalıştırmada fark testi `$?` hatasını ve `${AD}` eksikliğini böyle bulmuştu:

```
6c6
< 0
---
> 1
30,31c30,31
< 0
< 0
---
> 7
> 143
```

Sözde terminal testinin çıktısı (`hayatta 130`) ise tam istediğimiz davranışı doğruluyor: `sleep 30`, `Ctrl+C` ile öldü, kabuk hayatta kaldı ve `$?` = 128 + 2 = 130 oldu. AddressSanitizer ve UBSan ile aynı senaryoda çıktı birebir aynı ve hiçbir hata yok:

```
$ cc -g -O1 -fsanitize=address,undefined -D_POSIX_C_SOURCE=200809L tg.c kabuk.c -o k_a
$ ./k_a senaryo.txt > a.out 2> a.err; diff a.out kabuk.out && echo cikti-ayni
cikti-ayni
```

---

## 6. Sınırlar

Proje 300 satır. Gerçek bir kabuktan eksikler, kabukların neden 100 000 satır olduğunu da gösteriyor:

- `$(komut)` ve `` `komut` `` komut yerine koyma (hem ayrıştırıcıyı hem yürütücüyü özyinelemeli yapar).
- Kelime bölme ve `*.c` genişletme (`$X` bir değişkense burada tek kelime kalıyor; `bash` boşluklardan böler).
- Değişken atama sözdizimi (`X=5`): biz sadece `export` destekliyoruz.
- Akış kontrolü: `if`, `while`, `for`, fonksiyonlar. Bunlar için gerçek bir AST gerekiyor (Faz 15).
- Durdurulmuş işler için `jobs`, `fg`, `bg` (`Ctrl+Z`).
- Geçmiş ve satır düzenleme (`readline`).

---

## Alıştırmalar

**1** – `wait` yerleşik komutunu ekle: arka plan işlerini bekle. `arka_plani_topla`'nın bitmiş bir süreci önceden toplamış olmasına dikkat et.

**2** – Değişken atamasını ekle: bütün satır `AD=deger` ise kabukta sakla (`setenv` ile dışa aktarmadan bir sözlükte; Ders 8.14). `$AD` önce bu sözlüğe baksın.

**3** – `$(komut)` ekle: bir boru oluşturup komutu çalıştır, çıktısını kelime olarak ekle. Sonundaki satır sonlarını sil. Neden `bol`'un içinden `hat_calistir` çağırmak artık yanlış olabilir (tek bir `havuz` var)?

**4** – Basit bir `cd -`, `~` genişletme ve `PS1` istemi ekle.

**5** – Bu kabuğun içinde gerçek bir `make -j4` derlemesi çalıştır. `Ctrl+C` ne yapar? `strace -f` ile `make`'in süreç grubu kullanımını incele.

**6** – Ders 10.17'deki yöntemlerle kabuğu bir TCP portu üzerinden servis et. Neden bu fikir tehlikeli? Ders 10.15'teki izinler ve Ders 10.16'daki `LD_PRELOAD` ile bir saldırı senaryosu yaz.

<details>
<summary>Cevaplar</summary>

**1** – Yerleşik `wait`: `while (waitpid(-1, &d, 0) > 0)` döngüsü ile bütün çocukları topla; `ECHILD` görünce bitti. Tek bir PID bekleniyorsa ve `arka_plani_topla` onu daha önce topladıysa `waitpid` `ECHILD` döner: kabuk biten işlerin durumlarını kendi tablosunda saklamalı.

**2** – `komut_ayristir`'dan önce: hattın tek kelimesi varsa ve `=` içeriyorsa ve `=`'den önceki kısım geçerli bir adsa, sözlüğe kaydet. `genislet`, sözlükte bulamazsa `getenv`'e başvursun. `export X` önce sözlükten değeri alıp `setenv` yapsın.

**3** – `genislet` içinde `$(` görünce eşleşen `)`'i bul (tırnak farkında), iç metni ayrı bir `fork` çocuğunda `satir_isle` ile çalıştır, stdout'unu boruya bağla, oku, sondaki `\n`'leri at, sonucu `ekle_s`. `havuz` ve `Belirtec` dizileri statik: iç çalışma dış ayrıştırmanın verisini ezer. `fork` çocuğu içinde çalıştırmak bu sorunu çözüyor (çünkü bellek kopya), ama tembel: bir kabuğun her `$(...)`'de `fork` yapmasının nedeni budur. Daha temiz çözüm durumu bir `Ayristirici` yapısına almak.

**4** – `cd -`: önceki dizini (`OLDPWD`) tut, değişiklik başına güncelle. `~`: `bol`'da kelime başındaysa ve tırnak içinde değilse `$HOME` ile değiştir. `PS1`: `getenv("PS1")`, yoksa `"kabuk$ "`.

**5** – `Ctrl+C`, `make`'in ve bütün alt derleyicilerin aynı süreç grubunda olduğu için hepsine gider, hepsi durur. `make` jobserver'ı boru üzerinde çalışır (Ders 10.14 Alıştırma 5). `strace -f -e trace=setpgid,kill` ile izleyebilirsin.

**6** – Kimlik doğrulaması olmayan bir kabuk, portu bulan herkese o kullanıcının yetkilerini verir: dosyaları okur, `LD_PRELOAD` ile sonraki programlara kod enjekte eder, SSH anahtarı ekler. Bu, üretimde yapılmaması gereken, tam da "uzaktan kod çalıştırma" dediğimiz şey. Ders 7.14'teki saldırının hedefi genellikle tam olarak bu yeteneği elde etmek. Deneyecekseniz yalnızca `127.0.0.1` üzerinde ve yalnızca kendi makinenizde.

</details>

---

## Kaynaklar

- *POSIX.1-2017*, "Shell Command Language" bölümü: belirteçleme, genişletme ve yürütme kuralları.
- Chet Ramey, "The Bourne-Again Shell", *The Architecture of Open Source Applications*, 2011: gerçek bir kabuğun yapısı.
- GNU C Library kılavuzu, "Implementing a Job Control Shell": süreç grupları ve terminal denetimi.
- Russ Cox, Frans Kaashoek ve Robert Morris, xv6 `sh.c`: birkaç yüz satırda kabuk.
- Michael Kerrisk, *The Linux Programming Interface*, Bölüm 34: süreç grupları, oturumlar ve iş denetimi.

**Sıradaki faz:** Performans, cache ve SIMD. Bu fazda öğrendiğimiz `perf`, iş parçacıkları ve bellek bilgisi, programları donanımın sınırına kadar hızlandırmak için kullanılacak.
