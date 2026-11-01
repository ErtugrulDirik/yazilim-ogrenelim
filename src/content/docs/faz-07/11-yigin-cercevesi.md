---
title: "7.11 Yığın çerçevesi"
description: "Bir fonksiyonun yığın çerçevesi: yerel değişkenler, kaydedilen register'lar, dönüş adresi; çerçeve işaretçisi (rbp / arm64 fp) ile çerçeveyi gezmek ve çerçeve zinciri; rbp'li klasik prolog (push rbp; mov rsp, rbp) ve çerçeve işaretçisinin atlanması (frame pointer omission); optimizasyonun çerçeveyi tamamen yok edebilmesi; LLDB ile canlı bir programda yığını byte byte okumak ve yerel değişkenleri bellekte bulmak."
gereksinimler: [gcc]
---

Ders 7.6 ve 7.10'da fonksiyonların yığında yer açtığını (prolog/epilog) gördük. Ders 2.6'da LLDB ile hata ayıklamayı, Ders 2.7'de stack frame'leri soyut olarak öğrenmiştik. Bu ders ikisini birleştiriyor: bir fonksiyonun **yığın çerçevesinin** (stack frame) tam yerleşimini kuruyor, ve çalışan bir programda yığını **byte byte** okuyarak yerel değişkenlerin bellekte nerede durduğunu gösteriyor. Bu, hem Faz 7.14'teki saldırıları anlamak, hem Faz 10'da iş parçacıklarının (her birinin kendi yığını) nasıl çalıştığını görmek için temel.

---

## 1. Çerçevenin anatomisi

Bir fonksiyon çağrıldığında yığında şunlar birikir (adres yukarı, yığın aşağı büyür):

```
   yuksek adres
   +---------------------+
   | ...caller'in verisi |
   +---------------------+
   | argumanlar (6'dan   |   (varsa; Ders 7.10)
   |  fazlasi)           |
   +---------------------+
   | DONUS ADRESI        |   <- call bunu itti (Ders 7.10)
   +---------------------+
   | kaydedilen rbp      |   <- cercevenin "capasi" (varsa)
   +---------------------+ <- rbp buraya bakar
   | kaydedilen register |   (callee-saved, kullanildiysa)
   +---------------------+
   | yerel degiskenler   |
   +---------------------+ <- rsp buraya bakar
   dusuk adres
```

Her fonksiyon çağrısı böyle bir çerçeve açar; iç içe çağrılar çerçeveleri üst üste yığar (Ders 2.8'deki özyineleme). Dönüş adresi her çerçevenin içinde, yerel değişkenlerin yakınında — Ders 7.14'ün konusu.

---

## 2. rbp: çerçeve işaretçisi

Klasik yaklaşımda `rbp` (base pointer / frame pointer) çerçevenin sabit bir noktasını işaretler. Prolog:

```
topla:  pushq   %rbp            # caller'in rbp'sini sakla
        movq    %rsp, %rbp      # rbp = bu cercevenin capasi
        subq    $64, %rsp       # yerel degiskenler icin yer
        ...
```

(gcc `-O0`.) `rbp` kurulduktan sonra sabit kalır; yerel değişkenler ona göre sabit ofsetlerde (`-40(%rbp)`, `-24(%rbp)`), argümanlar pozitif ofsetlerde (`16(%rbp)`). `rsp` fonksiyon içinde oynasa da (örneğin bir şey push edilse) `rbp` oynamaz, bu yüzden yerellere erişim hep aynı ofsetle.

Neden iki işaretçi? `rbp` çerçevenin **dibini**, `rsp` **tepesini** gösterir. `rbp` ayrıca bir **zincir** oluşturur: her çerçevenin sakladığı eski `rbp`, bir önceki çerçeveyi işaret eder. Bu zinciri izleyerek bir hata ayıklayıcı bütün çağrı yığınını (backtrace, Ders 2.6) geriye doğru okuyabilir. gcc'nin `-O0` çıktısında ayrıca `%fs:40`'tan gelen bir **stack canary** da var (Ders 7.14); şimdilik görmezden gel.

---

## 3. Çerçeve işaretçisinin atlanması

`rbp` bir kolaylık ama bir **maliyet**: bir register'ı (rbp) bu işe ayırmak, ve her çağrıda iki komut (`push`/`pop rbp`). Modern derleyiciler, optimizasyon açıkken `rbp`'yi **atlar** (frame pointer omission): yerel değişkenlere doğrudan `rsp`'ye göre ofsetle erişir, `rbp`'yi başka iş için serbest bırakır.

Aynı `topla`, gcc `-O1`:

```
topla:  leaq    (%rdi,%rdi), %rax    # 2 * a
        ret
```

Çerçeve tamamen **yok oldu**! Ne `rbp`, ne `subq %rsp`, ne yerel değişken. Sebep: `topla(a, b)` aslında `yerel + tmp[0] - tmp[1] = (a+b) + a - b = 2a` hesaplıyor; derleyici bunu anladı (Ders 5, 6.23'teki cebirsel sadeleştirme), bütün yerel değişkenleri eledi ve sonucu tek `lea` ile (Ders 7.7) üretti. Yerel değişkenler `yerel` ve `tmp` koda hiç girmedi.

Bu, optimizasyonun gücünü gösteriyor (Ders 7.15) ama hata ayıklamayı zorlaştırıyor: `-O2` ile derlenmiş bir programda "yerel değişken `tmp`" diye bir şey bellekte olmayabilir; register'da ya da hiç yok. Bu yüzden hata ayıklarken `-O0 -g` kullanılır (her değişken bellekte, her satır izlenebilir); `rbp` de atlanmaz, backtrace güvenilir olur. Üretim kodu `-O2`, hata ayıklama `-O0 -g`.

---

## 4. LLDB ile yığını okumak

Çerçeveyi canlı görelim. `topla(10, 3)`'ü `-O0 -g` ile (çerçeve korunsun diye) derleyip LLDB ile 5. satırda (yereller atandıktan sonra) duralım.

> LLDB senin makinende çalışır. Aşağıdaki oturum bir ARM64 Mac'te; register adları orada `fp` (çerçeve işaretçisi, x29) ve `sp`. x86-64'te bunlar `rbp` ve `rsp` olur ama **mantık birebir aynı**: çerçeve işaretçisi dipte, yığın işaretçisi tepede, yereller aralarında.

```
(lldb) breakpoint set --file fr_dbg.c --line 5
(lldb) run
   3   	    long yerel = a + b;
   4   	    long tmp[2] = { a, b };
-> 5   	    return yerel + tmp[0] - tmp[1];

(lldb) frame variable
(long) a = 10
(long) b = 3
(long) yerel = 13
(long[2]) tmp = ([0] = 10, [1] = 3)

(lldb) bt
  * frame #0: ... topla(a=10, b=3) at fr_dbg.c:5
    frame #1: ... main at fr_dbg.c:7
    frame #2: ... dyld`start + 6992

(lldb) register read fp sp
      fp = 0x000000016fdfdf20
      sp = 0x000000016fdfdee0

(lldb) memory read --size 8 --format x --count 8 $sp
0x16fdfdee0: 0x00000001eec9fa70 0x000000000000000a
0x16fdfdef0: 0x0000000000000003 0x000000000000000d
0x16fdfdf00: 0x0000000000000003 0x000000000000000a
0x16fdfdf10: 0x00000001ee9e8100 0x0000000000000000
```

Okuyalım:

- **`frame variable`**: yerel değişkenlerin değeri. `yerel = 13` ($10 + 3$), `tmp = {10, 3}`. Derleyici her değişkenin yığında hangi ofsette olduğunu hata ayıklama bilgisinde (`-g`) tutuyor; LLDB onu kullanıp byte'ları değere çeviriyor.
- **`bt`** (backtrace): çağrı zinciri. `topla`'yı `main` çağırmış, `main`'i `start`. Bu zincir, Bölüm 2'deki kaydedilmiş çerçeve işaretçileri (ya da hata ayıklama bilgisi) izlenerek kuruluyor — Ders 2.8'deki yığılmış çerçevelerin somut hali.
- **`fp - sp` = `0x40` = 64 byte**: bu çerçevenin boyutu (gcc `-O0` çıktısındaki `subq $64, %rsp` ile aynı — farklı mimari, aynı büyüklük tercihi).
- **`memory read`**: yığının ham baytları. `sp`'nin hemen üstünde (`0x16fdfdee8`) `0x0a` = 10, sonra `0x03` = 3 (yani `tmp[0]`, `tmp[1]`), sonra `0x0d` = 13 (`yerel`). Yerel değişkenler gerçekten orada, byte byte. `frame variable`'ın gösterdiği soyut değerler, bu ham baytların yorumu (Ders 3'teki "aynı bitler, bir yorum").

Bu, bir programın çalışırken belleğinin içine bakmak. Faz 4'te pointer'larla belleği soyut gezmiştik; burada gerçek adresleri (`0x16fdfdee0`) ve içlerindeki baytları görüyoruz. Ders 7.14'te bu baytların — özellikle dönüş adresinin — üzerine nasıl yazılabileceğini göreceğiz.

---

## Alıştırmalar

**1** – `rbp`'li çerçevede yerel değişkenler neden **negatif** ofsette (`-24(%rbp)`), argümanlar (6'dan fazlası) neden **pozitif** ofsette (`16(%rbp)`)? Çerçeve şemasını (Bölüm 1) kullanarak açıkla.

**2** – `topla`'yı `-O0` ve `-O2` ile derle ve karşılaştır. `-O2`'de yerel değişkenler nerede? Bir hata ayıklayıcıda `-O2` kodda `frame variable` yazsan ne görürsün (ya da neden "optimized out" der)?

**3** – LLDB oturumunda `fp` ve `sp` arasındaki fark 64 byte çıktı. `topla`'nın gerçekte sakladığı veri (iki argüman, `yerel`, `tmp[2]`) kaç byte? Fark neden daha büyük? (İpucu: hizalama, Ders 7.10; ve derleyici `-O0`'da cömert davranır.)

**4** – Kendi makinende `fr_dbg.c`'yi `-O0 -g` ile derle, LLDB (ya da GDB) ile `topla`'da dur, `frame variable` ve `memory read $sp` çalıştır. Yerel değişkenlerin baytlarını yığında bul. (x86-64'teysen `register read rbp rsp`; arm64'teysen `fp sp`.)

**5** – `bt` çağrı zincirini nasıl buluyor? İki yöntem var: (a) çerçeve işaretçisi zinciri (her çerçevenin sakladığı eski `rbp`/`fp`), (b) hata ayıklama bilgisindeki (`.eh_frame`/DWARF) tablolar. Çerçeve işaretçisi atlanmışsa (Bölüm 3) hangisi gerekir? Bu yüzden `-fno-omit-frame-pointer` bazen neden açılır? (İpucu: profilleyiciler, Faz 11.)

<details>
<summary>Cevaplar</summary>

**1** – `rbp`, dönüş adresinin ve kaydedilen eski `rbp`'nin **altını** işaret eder (çerçevenin dibi). Yerel değişkenler `rbp`'den **aşağıda** (yığın aşağı büyür) açılır → negatif ofset. Argümanlar (6'dan fazlası) çağıran tarafından `call`'dan önce yığına, yani dönüş adresinin **üstüne** konur → `rbp`'den yukarıda, pozitif ofset. `16(%rbp)`: +8 kaydedilen rbp, +8 dönüş adresi, sonra ilk yığın argümanı. Şema Bölüm 1'de.

**2** – `-O0`'da yereller yığında (`-24(%rbp)` gibi), her biri belleğe yazılıp okunuyor. `-O2`'de derleyici onları eler ya da register'da tutar; `topla` örneğinde hepsi yok oldu (`2*a`). Hata ayıklayıcıda `-O2` kodda `frame variable` çoğu değişken için **"optimized out"** (optimize edilip elendi) der, çünkü değişkenin bellekte bir yeri yok — bir register'da anlık yaşadı ya da hiç var olmadı. Bu yüzden hata ayıklarken `-O0 -g`.

**3** – Gerçek veri: iki argüman (2×8 = 16), `yerel` (8), `tmp[2]` (16) = 40 byte. Çerçeve 64 byte: fark 24 byte. Sebepler: 16-byte hizalama (Ders 7.10; çerçeve 16'nın katı olmalı), derleyicinin `-O0`'da argümanları yığına kopyalaması (register'da da duruyorlar ama `-O0` yine yığına yazar), ve rahat yerleşim. `-O0` hız için değil, basitlik ve hata ayıklanabilirlik için üretir; cömert çerçeve normal.

**4** – Makineye göre değişir; arm64'te yukarıdaki oturumla aynı desen. Yereller `$sp`'nin birkaç byte üstünde, `frame variable`'ın gösterdiği değerlerle eşleşen baytlar olarak görünür (10, 3, 13, ...). x86-64'te `rbp`'ye göre negatif ofsetlerde.

**5** – Çerçeve işaretçisi atlanmışsa (b) **hata ayıklama/çözülme bilgisi** (DWARF `.eh_frame`) gerekir: çerçeve işaretçisi zinciri olmadığı için her fonksiyonun `rsp`'yi ne kadar kaydırdığını ve dönüş adresinin nerede olduğunu bu tablolardan hesaplanır. `-fno-omit-frame-pointer`, `rbp` zincirini koruyarak hızlı ve basit backtrace sağlar; **profilleyiciler** (Faz 11'de `perf` gibi) çalışan bir programı sık sık durdurup yığını örneklerken `rbp` zincirini izlemek DWARF çözmekten çok daha hızlı olduğu için bu bayrak sıkça açılır. Hız (atlama) ile gözlemlenebilirlik (çerçeve işaretçisi) arasında bir denge.

</details>

---

## Kaynaklar

- Randal Bryant & David O'Hallaron, *Computer Systems: A Programmer's Perspective* (3. baskı), Bölüm 3.7 ve 3.10.3: yığın çerçeveleri, çerçeve işaretçisi, bellekte yerleşim.
- LLDB belgeleri (lldb.llvm.org): `frame variable`, `memory read`, `register read`, `bt`.
- Ders 2.6 (LLDB) ve 2.7 (fonksiyonlar ve kapsam): bu dersin önceli.

**Sıradaki ders:** Diziler, struct'lar ve pointer'lar assembly'de. İndeksleme, struct üyesine ofsetle erişim, Faz 4 ile bağlantı.
