---
title: "8.22 Kalıcı (persistent) yapılar"
description: "Değiştirildiğinde eski sürümü de koruyan veri yapıları: alanları const olan değişmez bir bağlı liste, yeni sürümlerin eski kuyrukları paylaşması ve ortadaki bir değişikliğin sadece önündeki hücreleri kopyalaması; yol kopyalama ile kalıcı ikili arama ağacı, eklemede sadece kökten yaprağa yolun kopyalanması; 1 milyon eklemenin 1 milyon sürümünü saklamak 26.4 düğüm/ekleme ve 633 MB (her sürümü tam kopyalamak terabaytlar); belleği arenayla yönetmek; geri alma, sürüm geçmişi, iş parçacıkları arasında kilitsiz paylaşım ve derleyicide kapsamlar."
---

Bu fazdaki her yapı **yerinde** değişiyordu: Ders 8.9'daki AVL'ye bir anahtar eklemek eski ağacı yok edip yenisine dönüştürüyordu. Eski hali bir daha görmek mümkün değildi. Çoğu zaman istenen de bu. Ama bazen eski hal de gerekiyor: bir metin düzenleyicinin geri alma geçmişi, bir veritabanının "dün saat 3'teki" görüntüsü, git'in her commit'i, bir derleyicinin bir kapsamdan çıkınca geri dönmesi gereken sembol tablosu (Ders 8.16), birden çok iş parçacığının aynı veriyi kilitsiz okuması.

Saf çözüm her değişiklikten önce yapının tamamını kopyalamak: $O(n)$ zaman ve bellek, her değişiklikte. **Kalıcı** (persistent) yapılar bunu çok daha ucuza yapıyor: değişen kısmı kopyalayıp değişmeyen kısmı eski sürümle **paylaşarak**. Fikrin temeli tek bir kural: **hiçbir düğüm, yaratıldıktan sonra değişmiyor.**

---

## 1. Değişmez liste

Ders 8.2'deki tek yönlü listede başa ekleme, yeni bir düğüm yaratıp onu eski başa bağlıyordu. Eski baş hiç değişmiyordu. O halde başa ekleme zaten kalıcı: eski listeyi tutan biri onu aynen görmeye devam ediyor.

```c
/* Degismez liste: bir dugum yaratildiktan sonra hic degismiyor; yeni surumler eski kuyruklari paylasiyor. */
#include <stdio.h>
#include <string.h>
#include "arena.h"

typedef struct Hucre { const int bas; const struct Hucre *const kuyruk; } Hucre;   /* const: derleyici degisikligi reddeder */

static Arena A;
static const Hucre *cons(int x, const Hucre *k) {
    Hucre *h = ARENA_YENI(&A, Hucre);
    Hucre ilk = { x, k };                      /* const alanli struct: atamayla degil, kopyayla doldur */
    memcpy(h, &ilk, sizeof ilk);
    return h;
}
```

Alanlar `const` (Ders 3.21, 4.8): hücre yaratıldıktan sonra ona yazmaya çalışan kod **derlenmiyor**. Hücreyi ilk kez doldurmak için bile atama yapılamıyor, bu yüzden yerel bir kopya kurulup `memcpy` ile yerleştiriliyor. `cons` adı Lisp'ten: "construct", bir baş ve bir kuyruktan yeni bir liste kur. Bellek Ders 8.21'deki arenadan (neden, Bölüm 4'te).

Ortadaki bir konuma "eklemek" ise eski listeyi değiştiremeyeceği için o konumdan **önceki** hücreleri kopyalamak zorunda:

```c
/* Degistirmeden "ekleme": i. konuma x koy -> ilk i hucre kopyalanir, gerisi paylasilir */
static const Hucre *araya(const Hucre *l, int i, int x) {
    if (i == 0) return cons(x, l);
    return cons(l->bas, araya(l->kuyruk, i - 1, x));
}

int main(void) {
    arena_baslat(&A, 4096);
    const Hucre *v1 = cons(3, cons(2, cons(1, NULL)));
    const Hucre *v2 = cons(4, v1);
    const Hucre *v3 = cons(5, v1);
    const Hucre *v4 = araya(v1, 2, 9);
    yaz("v1", v1); yaz("v2", v2); yaz("v3", v3); yaz("v4", v4);
    printf("  v2->kuyruk == v1: %s, v3->kuyruk == v1: %s\n", v2->kuyruk == v1 ? "evet" : "hayir", v3->kuyruk == v1 ? "evet" : "hayir");
    printf("  v4 ile v1 son hucreyi paylasiyor mu: %s\n", v4->kuyruk->kuyruk->kuyruk == v1->kuyruk->kuyruk ? "evet" : "hayir");
    printf("  toplam %zu bayt = %zu hucre\n", A.toplam, A.toplam / sizeof(Hucre));
    arena_yok_et(&A);
}
```

(`yaz`, listeyi ve ilk hücrenin adresini yazdıran küçük bir yardımcı.)

```
$ cc -std=c11 -Wall -Wextra -fsanitize=address,undefined liste.c arena.c -o liste && ./liste
  v1 = [3 2 1]   ilk hucre 0x621000000138
  v2 = [4 3 2 1]   ilk hucre 0x621000000148
  v3 = [5 3 2 1]   ilk hucre 0x621000000158
  v4 = [3 2 9 1]   ilk hucre 0x621000000188
  v2->kuyruk == v1: evet, v3->kuyruk == v1: evet
  v4 ile v1 son hucreyi paylasiyor mu: evet
  toplam 128 bayt = 8 hucre
```

```
  v2 ─► [4]─┐
             ├─► [3]─►[2]─►[1]─► /      ◄── v1
  v3 ─► [5]─┘                 ▲
                              │
  v4 ─► [3]─►[2]─►[9]─────────┘
```

Dört liste, toplam 14 eleman, ama sadece 8 hücre. `v2` ve `v3` bütün `v1`'i paylaşıyor; `v4`, 9'un önündeki iki hücreyi (`3`, `2`) kopyaladı ve `1`'i paylaştı. `v1` hâlâ `[3 2 1]`: hiçbir işlem onu bozmadı. Değişikliğin maliyeti, değişen yere kadar olan **yol**.

Programa bir hücreyi değiştirmeye çalışan bir satır eklenirse (`v1->bas = 7;`, `-DHATA` ile açılan) derleyiciden geçmiyor:

```
liste.c:39:13: error: cannot assign to non-static data member 'bas' with const-qualified type 'const int'
```

---

## 2. Yol kopyalama: kalıcı ağaç

Aynı fikir ağaçlarda çok daha etkili, çünkü kökten bir düğüme giden yol kısa: dengeli ya da rastgele bir ağaçta $O(\log n)$. Bir anahtar eklemek için kökten eklenecek yere inen yoldaki düğümler kopyalanıyor; her kopya, değişmeyen tarafındaki alt ağacı **eski ağaçla paylaşıyor**. Bu teknik **yol kopyalama** (path copying).

```
 s4:          50                 s5 = s4 + 60:      50'                (' = yeni kopya)
            /    \                                /     \
          30      70           paylaşılan →     30       70'
            \                                     \      /
             40                                    40   60   ← yeni yaprak
```

`s5`'in kökü yeni bir 50, sağ çocuğu yeni bir 70, 70'in sol çocuğu yeni yaprak 60. Sol alt ağaç (30 ve 40) `s4` ile **aynı** düğümler. `s4`'ün kökü hâlâ eski 50'yi gösteriyor ve eski 50 hâlâ eski 70'i: `s4` değişmedi.

```c
/* Kalici ikili arama agaci: yol kopyalama. Ekleme kokten yapraga giden yolu kopyalar, gerisini paylasir. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "arena.h"

typedef struct KD { int anahtar; const struct KD *sol, *sag; } KD;

static Arena A;
static long kopya;                                   /* istatistik: yaratilan dugum */

static const KD *dugum(int x, const KD *sol, const KD *sag) {
    KD *d = ARENA_YENI(&A, KD);
    d->anahtar = x; d->sol = sol; d->sag = sag;
    kopya++;
    return d;
}

/* Eski agaci DEGISTIRMEDEN, x'i iceren yeni bir agacin kokunu dondur */
static const KD *ekle(const KD *n, int x) {
    if (!n) return dugum(x, NULL, NULL);
    if (x < n->anahtar) return dugum(n->anahtar, ekle(n->sol, x), n->sag);   /* sag alt agac PAYLASILIYOR */
    if (x > n->anahtar) return dugum(n->anahtar, n->sol, ekle(n->sag, x));   /* sol alt agac paylasiliyor */
    return n;                                        /* zaten var: ayni agac */
}

static bool var(const KD *n, int x) {
    while (n && n->anahtar != x) n = x < n->anahtar ? n->sol : n->sag;
    return n;
}
```

Ders 8.8'deki `bst_ekle` ile karşılaştır: orada pointer'a pointer ile bulunan yere yeni düğüm **asılıyordu** (bir düğümün `sol`'u değiştiriliyordu). Burada hiçbir mevcut düğüme yazılmıyor; her seviyede, bir çocuğu yeni olan bir kopya yaratılıyor. Ders 8.9'daki AVL'nin `n->sol = avl_ekle(n->sol, x)` kalıbına benziyor, ama `n`'yi değiştirmek yerine yeni bir `n` döndürüyor. Ağacı arayan `var`, düz BST aramasının aynısı; kalıcılık okumayı hiç etkilemiyor.

(Burada `KD`'nin alanları `const` değil, çünkü `dugum` onları doğrudan dolduruyor; ama dışarıya sadece `const KD *` veriliyor, ve kod hiçbir mevcut düğüme yazmıyor.)

```c
    const KD *s[6] = { NULL };
    int g[] = { 50, 30, 70, 40, 60 };
    for (int i = 0; i < 5; i++) { long o = kopya; s[i + 1] = ekle(s[i], g[i]); printf("s%d = s%d + %d (%ld yeni dugum):", i + 1, i, g[i], kopya - o); icek(s[i + 1]); printf("\n"); }
    printf("s5 ile s4 sol alt agaci paylasiyor mu: %s\n", s[5]->sol == s[4]->sol ? "evet" : "hayir");
    printf("eski surumler hala saglam: s2:"); icek(s[2]); printf("   s3:"); icek(s[3]); printf("\n");
```

```
$ cc -std=c11 -O2 -Wall -Wextra agac.c arena.c -o agac && ./agac
s1 = s0 + 50 (1 yeni dugum): 50
s2 = s1 + 30 (2 yeni dugum): 30 50
s3 = s2 + 70 (2 yeni dugum): 30 50 70
s4 = s3 + 40 (3 yeni dugum): 30 40 50 70
s5 = s4 + 60 (3 yeni dugum): 30 40 50 60 70
s5 ile s4 sol alt agaci paylasiyor mu: evet
eski surumler hala saglam: s2: 30 50   s3: 30 50 70
```

Her ekleme, yeni düğümün derinliği + 1 kadar düğüm yaratıyor: 40 derinlik 2'de, 3 düğüm. Beş sürümün hepsi aynı anda erişilebilir ve her biri kendi içeriğini görüyor.

### Ölçüm

1 milyon rastgele anahtarı sırayla ekleyip **her** eklemeden sonraki sürümü saklayalım: 1 milyon + 1 kök.

```c
    int n = 1000000;
    const KD **surum = malloc((n + 1) * sizeof *surum);
    int *a = malloc(n * sizeof *a);
    surum[0] = NULL;
    double t0 = simdi();
    for (int i = 0; i < n; i++) { a[i] = (int)(rnd() & 0x7fffffff); surum[i + 1] = ekle(surum[i], a[i]); }
    double t1 = simdi();
    ...
    for (int k = 0; k < 1000; k++) {                 /* her sorgu O(n) kontrol: 1000 tane yeterli */
        int v = (int)(rnd() % (n + 1)), i = (int)(rnd() % n);
        bool beklenen = false;
        for (int j = 0; j < v && !beklenen; j++) if (a[j] == a[i]) beklenen = true;
        if (var(surum[v], a[i]) != beklenen) hata++;
    }
```

Doğrulama: rastgele bir sürüm $v$ ve rastgele bir anahtar seçiliyor; $v$. sürüm, tam olarak ilk $v$ anahtarı içermeli.

```
1000000 surum: 26384721 dugum yaratildi (ekleme basina 26.4), 633 MB; tek bir degisken agac 1000000 dugum, 24 MB tutardi
ekleme basina 555 ns
1000 rastgele (surum, anahtar) sorgusu: 0 hata
```

(Sanitizer'lı derlemede de 0 hata.) Ekleme başına 26.4 düğüm: yeni anahtarın eklendiği derinlik + 1, ve rastgele bir BST'de bu derinlik $2 \ln n$ mertebesinde (Ders 8.8). 1 milyon sürümün **hepsini** saklamak 633 MB, tek bir değişken ağacın 26 katı. Her sürümü ayrı ayrı tam kopyalasaydık, ortalama 500 bin düğümlük 1 milyon ağaç: $5 \cdot 10^{11}$ düğüm, **12 TB**. Yol kopyalama 20 000 kat daha az bellekle aynı işi yapıyor.

Ekleme 555 ns, değişken bir BST'den yavaş: her seviyede bir `malloc` yerine arena ayırması da olsa, 26 düğüm yazmak gerekiyor.

Ağaç dengeli olmalı: dejenere bir ağaçta yol $O(n)$ ve her ekleme $O(n)$ düğüm kopyalar. Kalıcı bir AVL ya da kırmızı-siyah ağaç, yolu kopyalarken dönmeleri de kopyalar üzerinde yapıyor; dönmeler zaten yol üzerindeki düğümleri değiştirdiği için ek maliyet sabit.

---

## 3. Ne işe yarıyor

**Geri alma ve sürüm geçmişi.** Her değişiklikten sonra kökü bir diziye itmek, bütün geçmişi saklıyor. Geri almak, bir önceki köke dönmek: $O(1)$. Metin düzenleyicilerde metin bir kalıcı ağaç (rope) olarak tutulabiliyor; geri alma yığını sadece kökler.

**Kilitsiz paylaşım.** Bir iş parçacığı yapıyı okurken başka biri değiştiriyorsa, değişken bir yapıda kilit gerekir (Faz 10). Kalıcı bir yapıda okuyucu bir kökü alıp onu istediği kadar gezebilir; yazıcı yeni bir kök yaratıp atomik olarak yayımlıyor. Okuyucu eski sürümü görmeye devam ediyor, hiçbir düğüm altından değişmiyor. Clojure'un ve Scala'nın değişmez koleksiyonları, ve veritabanlarındaki çok sürümlü eşzamanlılık denetimi (MVCC) bu fikre dayanıyor.

**Derleyicide kapsamlar.** Ders 8.16'daki sembol tablosu, kapsam kapanınca sembolleri tek tek kovalarından söküyordu. Kalıcı bir sözlükle kapsam yönetimi önemsiz hale geliyor: kapsama girerken o anki kökü sakla, tanımlar yeni kökler üretsin, kapsamdan çıkarken saklanan köke dön (Alıştırma 3). Fonksiyonel dillerin derleyicileri (OCaml, Haskell) ortamları böyle tutuyor.

**Fonksiyonel programlama.** Haskell, Clojure, Erlang gibi dillerde veri yapıları varsayılan olarak değişmez; "değiştirme" her zaman yeni bir sürüm demek. Bu dillerin standart kütüphaneleri baştan sona kalıcı yapılardan oluşuyor. Ders 8.5'in Alıştırma 2'sindeki "iki yığınla kuyruk", sadece değişmez listeleri olan bu dillerde kuyruğun standart uygulaması (Okasaki).

**Git.** Bir git deposu, içeriğe göre adreslenen değişmez nesnelerden oluşan kalıcı bir ağaç: bir dosyayı değiştiren commit, o dosyadan köke kadar olan dizin nesnelerini yeniden yaratıyor ve geri kalan her şeyi önceki commit'le paylaşıyor. Yol kopyalamanın ta kendisi.

---

## 4. Bellek kimin?

Kalıcı yapıların C'deki asıl zorluğu: bir düğümü ne zaman `free` edebilirsin? Bir düğüm birçok sürüm tarafından paylaşılıyor olabilir; bir sürümü atmak, onun düğümlerinin hepsini atmak demek değil. Ders 8.7'deki `serbest` gibi bir özyinelemeli bırakma, başka sürümlerin hâlâ kullandığı düğümleri bırakır.

Üç yol var:

- **Arena** (bu dersteki): bütün sürümler aynı arenada ve hepsi birlikte ölüyor. Bir derleme oturumu, bir istek, bir oyun karesi gibi net bir ömür grubu varsa en basit ve en hızlısı (Ders 8.21).
- **Referans sayma**: her düğüm, onu gösteren pointer sayısını tutuyor; sayı 0'a düşünce düğüm bırakılıp çocuklarının sayıları azaltılıyor. Kalıcı yapılarda bu güvenli, çünkü yeni düğümler sadece **eski** düğümleri gösterebiliyor: bir düğüm yaratıldığında gösterdiği her şey zaten var ve düğüm sonra değişmiyor, yani bir düğümden kendisine geri dönen bir döngü oluşamaz. Döngüsüz bir yapıda referans sayma her şeyi doğru bırakıyor (Alıştırma 4).
- **Çöp toplama**: fonksiyonel dillerin seçimi. Faz 17'de.

---

## Alıştırmalar

**1** – İki değişmez listeyi uç uca eklemek (`a ++ b`): yeni liste nasıl kurulur, kaç hücre yaratılır, hangi liste paylaşılır? `b ++ a` ile maliyet farkı ne? Değişken bir listede, son hücrenin `kuyruk` pointer'ını değiştirerek bu $O(1)$ idi; kalıcı listede neden olamaz?

**2** – Kalıcı BST'den **silme**: Ders 8.8'deki üç durumu yol kopyalamayla nasıl yaparsın? İki çocuklu bir düğüm silinirken kaç yol kopyalanır?

**3** – Ders 8.16'daki sembol tablosunu kalıcı bir sözlükle (isim → sembol bilgisi) yeniden tasarla. `kapsam_ac`, `kapsam_kapat`, `sembol_tanimla` ve `sembol_bul` ne yapar? Gölgeleme ve "aynı kapsamda tekrar tanım" hatası nasıl yakalanır?

**4** – Kalıcı ağaçta referans sayma: her düğüme bir `int sayac` ekle. `ekle` yeni bir düğüm yaratıp eski çocuklardan birini paylaşınca hangi sayaçlar artar? Bir sürümü (bir kökü) bırakmak için `birak(kok)` fonksiyonunu tarif et. Yukarıdaki 1 milyon sürümün ilk 999 999'u bırakılırsa bellekte ne kalır?

**5** – Yol kopyalamanın bir alternatifi **şişman düğüm** (fat node): düğümler kopyalanmıyor; her düğüm her alanının bütün geçmiş değerlerini (sürüm numarasıyla birlikte) bir listede tutuyor. Bir sürümde arama nasıl yapılır? Bellek ve zaman açısından yol kopyalamayla karşılaştır.

<details>
<summary>Cevaplar</summary>

**1** – `a`'nın bütün hücreleri sırayla kopyalanıyor, son kopyanın kuyruğu `b`'yi gösteriyor: `ekle(a, b) = a ? cons(a->bas, ekle(a->kuyruk, b)) : b`. $|a|$ hücre yaratılıyor, `b` olduğu gibi **paylaşılıyor**. `b ++ a` ise $|b|$ hücre kopyalıyor: maliyet soldaki listenin uzunluğu. Değişken listede `a`'nın son hücresinin `kuyruk`'unu `b`'ye çevirmek $O(1)$ ama `a`'yı **değiştiriyor**: `a`'yı tutan herkes artık `a ++ b`'yi görüyor. Kalıcı listede bunu yapmak `a`'nın eski sürümünü yok etmek olurdu. Bu yüzden fonksiyonel dillerde listeye **başa** eklemek ucuz, **sona** eklemek pahalı; sona eklemenin sık olduğu yerde başka bir yapı (kalıcı vektör, sonlu parmak ağacı) kullanılıyor.

**2** – Yaprak ya da tek çocuk: silinecek düğüme kadar olan yol kopyalanıyor, silinen düğümün yerine (kopyalanmış ebeveynin ilgili alanına) `NULL` ya da tek çocuğu konuyor. Tek çocuklu durumda çocuk alt ağacı kopyalanmadan paylaşılıyor. İki çocuk: silinecek düğüm, anahtarı **ardılın** anahtarı olan yeni bir düğümle değiştiriliyor; bu yeni düğümün sağ alt ağacı, eski sağ alt ağaçtan ardılın silindiği sürüm (ardıla inen yol kopyalanıyor). Toplam kopyalanan: köke kadar olan yol + silinen düğümden ardıla inen yol, yani yine kökten ardıla tek bir yol: $O(h)$.

**3** – Kapsam bir **değer** oluyor: o anki kök. `kapsam_ac` o anki kökü bir yığına itiyor (ya da çağıranın yerel değişkeninde saklıyor). `sembol_tanimla(isim)` kökü `ekle(kok, isim → bilgi)` ile değiştiriyor; aynı isim dış kapsamda varsa yeni sürümde yenisiyle değişiyor (gölgeleme), eski sürüm etkilenmiyor. `kapsam_kapat` yığından kökü çekip geri yüklüyor: dış kapsamın sözlüğü tam olarak açılmadan önceki hali, ve bunun için hiçbir şey sökülmüyor; $O(1)$. `sembol_bul` düz bir arama. "Aynı kapsamda tekrar tanım"ı yakalamak için bilgiye tanımlandığı **kapsam seviyesi** yazılıyor (Ders 8.16'daki gibi); bulunan sembolün seviyesi şu anki seviyeyse hata. Bir avantaj daha: derleyicinin daha sonraki bir aşaması (örneğin bir hata mesajı) belirli bir noktadaki kapsamın tamamını görmek isterse, o noktadaki kökü saklamak yeterli.

**4** – `dugum(x, sol, sag)` yeni düğümü sayaç 1 ile yaratıyor (onu gösteren tek şey, döndürüldüğü yer) ve paylaştığı her çocuğun sayacını bir artırıyor. `ekle`, yol üzerindeki eski düğümü kopyalarken eski düğümün değişmeyen çocuğunu paylaşıyor: o çocuğun sayacı +1. `birak(n)`: `if (--n->sayac == 0) { birak(n->sol); birak(n->sag); free(n); }` (`NULL` kontrolüyle). İlk 999 999 sürüm bırakılınca sadece son sürümün düğümleri kalıyor: 1 milyon düğüm, 24 MB (artı sayaç alanları). Önceki sürümlere özgü olan, yani son sürüm tarafından paylaşılmayan bütün yol kopyaları bırakılmış oluyor. Döngü olmadığı için (her düğüm sadece kendisinden önce yaratılmış düğümleri gösterebilir) referans sayma hiçbir şeyi kaçırmıyor. Bedel: her paylaşımda bir sayaç güncellemesi ve her bırakmada bir özyineleme; ve iş parçacıkları arasında paylaşılıyorsa sayaçlar atomik olmalı (Faz 10).

**5** – Şişman düğümde her alanın `(sürüm, değer)` çiftlerinin listesi var. $v$. sürümde arama, her düğümde her alan için sürümü $\le v$ olan en son değeri bulmak: alan geçmişi sürüm sırasına göre sıralı olduğu için ikili arama, düğüm başına $O(\log m)$ ($m$ değişiklik sayısı), arama toplam $O(h \log m)$. Bellek değişiklik başına $O(1)$: sadece değişen alan için bir çift ekleniyor (yol kopyalamada $O(h)$ düğüm). Yani şişman düğüm bellekte kazanıyor, aramada kaybediyor; ve sadece **son** sürüm değiştirilebiliyor (kısmi kalıcılık). Driscoll, Sarnak, Sleator ve Tarjan (1989), iki yöntemi birleştirip (düğüme sınırlı sayıda ek alan koyup dolunca kopyalayarak) hem $O(1)$ amortize bellek hem $O(1)$ ek arama maliyeti veren bir yöntem gösterdiler.

</details>

---

## Kaynaklar

- James Driscoll, Neil Sarnak, Daniel Sleator ve Robert Tarjan, "Making Data Structures Persistent", *Journal of Computer and System Sciences* 38(1), 1989.
- Chris Okasaki, *Purely Functional Data Structures*, Cambridge University Press, 1998.
- Phil Bagwell, "Ideal Hash Trees", EPFL teknik rapor, 2001: Clojure ve Scala'nın kalıcı hash haritalarının temeli (HAMT).
- Scott Chacon ve Ben Straub, *Pro Git* (2. baskı), Bölüm 10.2: git nesneleri.
- Harold Abelson ve Gerald Sussman, *Structure and Interpretation of Computer Programs* (2. baskı), Bölüm 2.2: `cons` ve liste yapıları.

**Sıradaki ders:** Genel (generic) yapılar C'de. `void*` ile, makro ile ve intrusive yapı yaklaşımı; avantaj ve dezavantajları.
