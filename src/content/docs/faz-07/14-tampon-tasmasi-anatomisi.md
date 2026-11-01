---
title: "7.14 Tampon taşması saldırısının anatomisi"
description: "Yığında bir tamponun taşmasının dönüş adresini nasıl bozduğu; sınır kontrolsüz strcpy'nin tehlikesi ve korumasız bir programın çökmesi (savunma odaklı, silah değil); üç savunma: stack canary'nin taşmayı yakalaması ve assembly'si, NX ile yığının çalıştırılamaz olması, ASLR ile adreslerin rastgeleleştirilmesi; FORTIFY_SOURCE; ve asıl çözümün sınır kontrollü kod (Faz 4.14) olması."
gereksinimler: [gcc]
---

Ders 7.11'de yığın çerçevesinin yerleşimini gördük: yerel değişkenler ve dönüş adresi aynı çerçevede, yan yana. Ders 4.13–4.14'te sınır kontrolsüz string fonksiyonlarının (`strcpy`, `gets`) tehlikeli olduğunu söylemiştik. Bu ders ikisini birleştiriyor: bir dizinin sınırını aşan veri, **dönüş adresinin üzerine yazabilir** ve programın akışını bozabilir. Bu, bilgisayar güvenliğinin en eski ve en önemli hata sınıfı.

Bu ders **savunma odaklı ve eğitseldir**: saldırının nasıl çalıştığını, neden mümkün olduğunu ve nasıl **engellendiğini** anlamak için. Amaç, güvenli kod yazabilmek ve modern sistemlerin kendini nasıl koruduğunu bilmek. İşleyen bir saldırı yükü (exploit) yazmıyoruz; çöküşü ve savunmaların onu nasıl durdurduğunu gösteriyoruz.

---

## 1. Tehlikeli kod

Ders 4.14'teki uyarıyı hatırla: `strcpy` kopyaladığı stringin uzunluğuna bakmaz, hedefin sığıp sığmadığını kontrol etmez. Yığında küçük bir tamponla:

```c
void selamla(const char *girdi) {
    char ad[16];              // 16 baytlik tampon, YIGINDA
    strcpy(ad, girdi);        // sinir kontrolu YOK
    printf("Merhaba, %s\n", ad);
}
```

`girdi` 16 bayttan kısaysa sorun yok. Ama 40 baytlık bir `girdi` gelirse, `strcpy` `ad`'ın 16 baytını doldurur ve **devam eder** — çerçevede `ad`'ın üstündeki baytların (kaydedilen register'lar, ve en önemlisi **dönüş adresi**, Ders 7.11) üzerine yazar. Ders 7.11'deki çerçeve şemasını hatırla: yerel değişkenler düşük adreste, dönüş adresi yüksek adreste; yığın aşağı büyür ama `strcpy` **yukarı** doğru yazar, tam dönüş adresine doğru.

---

## 2. Korumasız program çöker

Bütün savunmaları kapatıp (`-fno-stack-protector`) uzun bir girdi verelim:

```
=== canary KAPALI, uzun girdi:
Segmentation fault  (cikis: 139)
```

Program **çöktü** (segfault, Ders 4.23). Neden? `strcpy` dönüş adresinin üzerine `AAAA...` (`0x41414141...`) yazdı. `selamla` bitip `ret` çalıştığında (Ders 7.10), dönüş adresi olarak `0x4141414141414141`'i okudu ve oraya atlamaya çalıştı — geçersiz bir adres, işlemci erişemedi, işletim sistemi programı öldürdü.

Bir saldırgan `AAAA` yerine **anlamlı** bir adres yazabilseydi, programın akışını kendi seçtiği bir yere yönlendirebilirdi — klasik "stack smashing" saldırısı (Aleph One'ın 1996'daki ünlü yazısı). Eskiden saldırgan, kötü niyetli makine kodunu da tampona yazıp dönüş adresini oraya yönlendirirdi. Modern savunmalar tam bunu zorlaştırmak için var.

---

## 3. Savunma 1: Stack canary

Fikir: fonksiyonun girişinde, yerel değişkenlerle dönüş adresi **arasına** gizli, rastgele bir değer ("kanarya", madendeki kanaryadan) koy. Fonksiyon dönmeden önce bu değerin değişip değişmediğini kontrol et. Bir tampon taşması dönüş adresine ulaşmak için **önce kanaryayı** ezmek zorunda; kanarya değişmişse taşma olmuş demektir, program güvenle durdurulur.

Derleyici (gcc, varsayılan açık) bunu otomatik ekliyor. `selamla`'nın assembly'si:

```
selamla:
        subq    $32, %rsp
        movq    %fs:40, %rax      # gizli kanarya degerini al (thread-local)
        ...                       # (yigina, donus adresinin hemen altina koy)
        call    strcpy
        ...
        subq    %fs:40, %rax      # yigindaki kanarya ile orijinali karsilastir
        jne     .basarisiz        # degismisse -> __stack_chk_fail
        addq    $32, %rsp
        ret
.basarisiz:
        call    __stack_chk_fail@PLT   # "stack smashing detected", programi oldur
```

`%fs:40`, her iş parçacığına özel (thread-local, Ders 7.27) rastgele bir değer; program her çalıştığında farklı, saldırganın tahmin edemeyeceği. Fonksiyon başında yığına konur, sonunda kontrol edilir. Aynı uzun girdiyi savunma **açıkken** verelim:

```
=== canary acik, uzun girdi (tasma):
*** stack smashing detected ***: terminated  (cikis: 134)
```

Çökme yerine kontrollü bir durdurma. Kanarya taşmayı yakaladı, dönüş adresine ulaşmadan programı sonlandırdı. Saldırgan dönüş adresini kontrol edemiyor çünkü araya girmek için bilemediği kanaryayı doğru yazması gerekirdi.

Kanaryanın maliyeti: her fonksiyon girişinde/çıkışında birkaç komut. Küçük ama var; bu yüzden derleyici sadece **yığında dizi/tampon olan** fonksiyonlara ekler (risk oradaysa). `-fstack-protector-strong` daha geniş, `-fno-stack-protector` kapatır (asla üretim kodunda).

---

## 4. Savunma 2: NX (çalıştırılamaz yığın)

Eski saldırılar kötü kodu tampona yazıp oraya atlardı. **NX** (No-eXecute, DEP), yığını ve veri bölgelerini **çalıştırılamaz** işaretler: oraya yazılmış baytlar veri olarak okunur ama **kod olarak çalıştırılamaz**. Dönüş adresi tampona yönlense bile, oradaki baytlar çalışmaz.

ELF dosyasında bunu görebiliriz:

```
=== NX: yigin calistirilabilir mi?
GNU_STACK   ...  RW   0x10
```

`GNU_STACK` bölümü `RW` (okunur-yazılır) ama `X` (çalıştırılabilir) **değil**. Ders 7.13'te elle yazdığımız assembly'ye `.note.GNU-stack` notunu eklememizin sebebi buydu: not yoksa linker yığını çalıştırılabilir varsayar ve NX korumasını kaybederiz. İşlemci bu biti donanım düzeyinde zorlar (Ders 7.27'deki sayfa tabloları); çalıştırılamaz bir sayfadaki koda atlamak hata (fault, Ders 7.28) üretir.

NX'i aşmak için saldırganlar yeni kod enjekte etmek yerine **var olan** kod parçalarını zincirleme tekniklerine (ROP) yöneldi; bu da savunmalarla (sonraki) zorlaştırıldı. Güvenlik bir silahlanma yarışı; her savunma bir saldırı sınıfını kapatır.

---

## 5. Savunma 3: ASLR

**ASLR** (Address Space Layout Randomization), programın parçalarını (yığın, öbek, kütüphaneler) her çalıştırmada **rastgele** adreslere koyar. Saldırgan "dönüş adresini şu sabit adrese yönlendir" diyemez, çünkü o adres her seferinde farklı. Ders 7.11'de LLDB oturumunda gördüğümüz `0x16fdfdee0` gibi yığın adresleri her çalıştırmada değişiyor; ASLR bunu kasıtlı yapıyor.

ASLR, NX ile birlikte saldırıyı çok zorlaştırır: saldırgan ne kendi kodunu çalıştırabilir (NX), ne var olan kodun yerini bilir (ASLR). Üçü birlikte (canary + NX + ASLR) modern sistemlerin varsayılan savunması. Hiçbiri tek başına mükemmel değil, ama katmanlı savunma (defense in depth) saldırı maliyetini çok yükseltir.

---

## 6. Asıl çözüm: sınır kontrollü kod

Savunmalar önemli ama bir **ağ**; asıl çözüm açığı en baştan yazmamak. Ders 4.14'teki kural: sınır kontrolsüz fonksiyonları (`strcpy`, `strcat`, `gets`, `sprintf`) sınırlı halleriyle değiştir:

```c
void selamla(const char *girdi) {
    char ad[16];
    snprintf(ad, sizeof ad, "%s", girdi);   // en fazla 15 karakter + sonlandirici
    printf("Merhaba, %s\n", ad);
}
```

`snprintf` (ya da `strncpy`, dikkatli kullanıldığında) hedefin boyutunu bilir, taşmaz. Bölüm 1'deki assembly'de gördüğün `__strcpy_chk` ve `__printf_chk` da bunun otomatik hali: **FORTIFY_SOURCE** (gcc/glibc), derleme zamanında hedef boyutu bilinen `strcpy`/`printf` çağrılarını, çalışma zamanında sınır kontrolü yapan güvenli sürümleriyle değiştirir. `-D_FORTIFY_SOURCE=2 -O2` ile açılır.

Daha derin çözüm, dili değiştirmek: Rust gibi diller sınır kontrolünü dil düzeyinde zorlar, bu hata sınıfını büyük ölçüde ortadan kaldırır. C'de ise disiplin ve araçlar (ASan, Ders 4.23; FORTIFY; statik analiz) şart. Ama anlamak için önce mekanizmayı bilmek gerekiyordu: taşma neden dönüş adresine ulaşır, ve savunmalar onu nasıl durdurur. Bu bilgi olmadan ne güvenli kod yazılır ne de bir güvenlik açığı anlaşılır.

---

## Alıştırmalar

**1** – Ders 7.11'deki çerçeve şemasını kullanarak, 16 baytlık `ad` tamponunu taşıran verinin sırayla hangi şeyleri (kaydedilen register'lar, dönüş adresi) ezdiğini çiz. `strcpy` hangi yönde yazıyor, yığın hangi yönde büyüyor?

**2** – Kendi makinende `bof.c`'yi `-fno-stack-protector` ile derleyip uzun bir argümanla çalıştır (eğitim amaçlı, kendi makinende). Hangi sinyalle çöküyor (segfault / SIGABRT)? Sonra savunmaları açık (varsayılan) derleyip aynı girdiyi ver; fark ne?

**3** – Stack canary assembly'sinde `movq %fs:40, %rax` (başta) ve `subq %fs:40, %rax; jne` (sonda) ne yapıyor? Kanarya değeri neden `%fs:40`'ta (rastgele, thread-local) tutuluyor da kodun içinde sabit bir sayı değil? (Tahmin edilebilirlik.)

**4** – NX, ASLR ve canary'den **her biri** hangi saldırı adımını engelliyor? Bir tabloda eşleştir: (a) tampona kod yazıp çalıştırmak, (b) dönüş adresini sabit bilinen bir adrese yönlendirmek, (c) dönüş adresine hiç ulaşmak.

**5** – `snprintf(ad, sizeof ad, "%s", girdi)` neden taşmaz? `strncpy(ad, girdi, sizeof ad)` ise bir tuzak içeriyor (Ders 4.14): ne? (İpucu: `strncpy` tam dolu bir tamponu sonlandırmaz.) Hangisi daha güvenli?

<details>
<summary>Cevaplar</summary>

**1** – Yığın aşağı (düşük adrese) büyür, ama `strcpy` `ad`'ın başından **yukarı** (yüksek adrese) doğru yazar. Çerçevede (Ders 7.11) `ad` düşük adreste; yukarı doğru sırayla: `ad`'ın 16 baytı, (varsa) kanarya, kaydedilen `rbp`, **dönüş adresi**. 16 baytı aşan veri önce kanaryayı, sonra kaydedilen rbp'yi, sonra dönüş adresini ezer. `strcpy`'nin yazma yönü ile yığının büyüme yönünün ters olması, taşmanın neden "yukarıdaki" dönüş adresine ulaştığını açıklar.

**2** – `-fno-stack-protector` ile uzun girdi: **segfault** (SIGSEGV, exit 139) — dönüş adresi bozulur, `ret` geçersiz adrese atlar. Savunmalar açıkken: **SIGABRT** (exit 134), "stack smashing detected" — kanarya taşmayı yakalar, kontrollü durur. Fark: korumasızda akış bozulur (saldırgana açık kapı), korumalıda taşma anında güvenle durdurulur.

**3** – Başta `movq %fs:40, %rax`: thread-local depodaki (Ders 7.27) gizli kanarya değerini alıp yığına (dönüş adresinin altına) koyar. Sonda `subq %fs:40, %rax; jne`: yığındaki değeri orijinalle karşılaştırır; farklıysa (`jne`) taşma olmuş, `__stack_chk_fail`'e gider. Değer `%fs:40`'ta rastgele ve her çalıştırmada farklı; kodun içinde sabit olsaydı saldırgan onu okuyup taşırken aynısını yazabilir, kontrolü atlatabilirdi. Rastgelelik tahmin edilemezliği sağlıyor.

**4** – (a) tampona kod yazıp çalıştırmak → **NX** engeller (yığın çalıştırılamaz). (b) dönüş adresini sabit bilinen adrese yönlendirmek → **ASLR** engeller (adresler rastgele, bilinmez). (c) dönüş adresine hiç ulaşmak → **canary** engeller (araya girdiğini yakalar). Üçü farklı adımları kapatıyor; bu yüzden birlikte kullanılırlar (katmanlı savunma). Birini aşan bir saldırı diğerine takılır.

**5** – `snprintf(ad, sizeof ad, ...)` ikinci argümanı hedef boyutu (16); en fazla 15 karakter yazıp mutlaka `\0` ile sonlandırır, taşmaz. `strncpy(ad, girdi, 16)` tuzağı: `girdi` tam 16+ karakterse `strncpy` 16 baytı doldurur ama **sonlandırıcı `\0` koymaz** (Ders 4.14); sonraki `printf("%s", ad)` sonlandırıcı arayıp tamponun dışına taşar (okuma taşması). `snprintf` daha güvenli (hep sonlandırır); `strncpy` kullanılacaksa `ad[15] = '\0'` elle eklenmeli. İki fonksiyon da "n" içeriyor ama güvenlik garantileri farklı — sınır kontrolü yeterli değil, doğru sonlandırma da gerek.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.10.3–3.10.4: tampon taşması, stack canary, NX, ASLR.
- Ders 4.13–4.14 (string fonksiyonları), 4.23 (bellek hataları ve ASan): bu dersin C'deki önceli.
- OWASP ve CWE-121 (Stack-based Buffer Overflow): savunma rehberleri.
- Matt Miller (Microsoft), "Trends in the exploitation of memory safety issues": savunmaların etkisi ve bellek güvenliğinin önemi üzerine veri.

**Sıradaki ders:** Derleyici optimizasyon seviyeleri. `-O0`, `-O1`, `-O2`, `-O3` çıktısının karşılaştırılması; sabit katlama ve döngü dönüşümlerine ilk bakış.
