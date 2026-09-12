# Evaluacija

- [Dvije iteracije](#dvije-iteracije)
- [Metodologija](#metodologija)
- [Logički sloj](#logički-sloj)
- [Iteracija 1 - JSON format](#iteracija-1---json-format)
- [Iteracija 2 - kompaktni format](#iteracija-2---kompaktni-format)
- [Zaključak i ograničenja](#zaključak-i-ograničenja)
- [Fajlovi sa rezultatima](#fajlovi-sa-rezultatima)

## Dvije iteracije

Mjerenja su rađena u dvije iteracije, jer je strukturirani izlaz LLM-a u međuvremenu promijenjen. Skupovi slučajeva su isti, ali format odgovora i promptovi nisu.

| | iteracija 1 | iteracija 2 |
|---|---|---|
| format izlaza | `{"mode": "claim", "target": "rizik_sudara"}` | `claim rizik_sudara` |
| sistemski prompt, prevod | ~704 tokena | 513 tokena |
| konfiguracije | `local`, `local-thinking`, `openai` | `local`, `openai` |
| ponavljanja | 1 po konfiguraciji | 5 za stress skup |
| potrošnja tokena | procijenjena | izmjerena iz `usage` |

## Metodologija

Evaluacija je odvojena na dva sloja: formalnu logiku i LLM prevod korisničke izjave u strukturirani upit. Slojevi su mjereni odvojeno da bi se jasno razlikovalo da li eventualna greška dolazi iz razumijevanja izjave ili iz formalne obrade pravila i senzorskih očitavanja.

**Dva skupa:**

- **glavni** - 15 podržanih izjava (`eval_cases.jsonl`)
- **stress** - 20 izjava: 9 složenijih podržanih izjava i 11 izjava koje treba odbiti (`eval_stress_cases.jsonl`)

**Dvije evaluacije:**

- **logika** - presuda iz očekivanog upita i očitavanja senzora, bez LLM-a, na glavnom skupu
- **prevod** - korisnička izjava u strukturirani upit, u konfiguracijama `local` (Qwen3.5-9B, L40S), `local-thinking` (isti model, thinking uključen) i `openai` (gpt-5.6-luna)

Slojevi se mjere odvojeno jer greške nisu iste prirode. LLM može pogriješiti u razumijevanju izjave, dok greška u logičkom sloju može doći iz pravila, groundinga ili implementacije. Kada bi se mjerio samo krajnji izlaz, ne bi bilo jasno gdje je greška nastala.

LLM prevod vraća jedan od tri moda: `claim`, `request` ili `unsupported`.

- `claim` označava pitanje o tome da li neki zaključak važi, npr. da li postoji rizik sudara.
- `request` označava zahtjev ili pitanje dozvole, npr. uključivanje tempomata.
- `unsupported` označava izjavu koju sistem ne zna bezbjedno mapirati na postojeće ciljeve.

Upiti sa modovima `claim` i `request` šalju se u logički sloj. Upiti označeni kao `unsupported` se odbacuju.

## Logički sloj

Glavni skup:

| metrika | rezultat |
| --- | --- |
| tačne presude | 15/15 |
| prosječno vrijeme | 158 ms |
| najduže vrijeme | 615 ms |

Najsporiji su odbijeni zahtjevi (do 615 ms), jer traženje konfliktnih pravila ponavlja provjeru konzistentnosti.

## Iteracija 1 - JSON format

Model je vraćao JSON objekat `{"mode": ..., "target": ..., "speed_kmh": ...}`. Jedno pokretanje po konfiguraciji.

| | local | openai | local-thinking |
|---|---|---|---|
| glavni skup, tačan upit | 15/15 | 15/15 | 15/15 |
| stress, složeniji validni | 9/9 | 9/9 | 9/9 |
| stress, odbijeni | 11/11 | 11/11 | 11/11 |
| latencija, glavni skup | 0.63 s | 1.09 s | 15.54 s |
| latencija, stress | 0.49 s | 1.39 s | **34.54 s** |

U ovoj iteraciji nije zabilježena nijedna greška: 0 odgovora u pogrešnom formatu, 0 izmišljenih ciljeva, 0 pogrešno prihvaćenih izjava i 0 ponovnih pokušaja.

Sve tri konfiguracije imaju istu tačnost, pa razliku pravi uglavnom latencija: lokalni model bez thinkinga je najbrži, OpenAI je do tri puta sporiji, a thinking 25 do 70 puta, zavisno od skupa. Pošto LLM ovdje samo popunjava fiksnu šemu, thinking režim nije donio bolju tačnost, ali je značajno povećao latenciju.

## Iteracija 2 - kompaktni format

Strukturirani izlaz je prebačen s JSON objekta na jednu liniju:

```
prije:   {"mode": "claim", "target": "rizik_sudara"}
poslije: claim rizik_sudara
```

Uz to su oba sistemska prompta skraćena, a `local-thinking` je izostavljen jer je u prvoj iteraciji pokazao istu tačnost uz 25 do 70 puta veću latenciju.

### Tačnost

Glavni skup, jedno pokretanje:

| | local | openai |
|---|---|---|
| tačan upit | **15/15** | **15/15** |
| latencija, medijan | 0.32 s | 0.96 s |
| latencija, p95 | 0.43 s | 2.26 s |

Stress skup, **pet ponovljenih pokretanja**:

| | local | openai |
|---|---|---|
| složeniji validni | **100%** (9/9, svih 5 puta) | 88.9% (8/9) |
| odbijeni | **100%** (11/11, svih 5 puta) | 90.9–100% |
| latencija, medijan | 0.21 s | 0.85 s |
| latencija, p95 | 0.41 s | 1.47 s |
| latencija, max | 0.51 s | 2.14 s |

Percentili su računati na objedinjenih 100 mjerenja po konfiguraciji (5 pokretanja × 20 slučajeva).

### Potrošnja tokena

Vrijednosti dolaze iz `usage` polja u odgovoru servera. Navedena je medijana, a u zagradi raspon po slučajevima.

| poziv | prompt | izlaz | ukupno |
|---|---|---|---|
| prevod, `local` (n=15) | 513 (511–517) | 8 (6–12) | **520** (518–529) |
| prevod, `openai` (n=15) | 487 (484–488) | 10 (8–12) | **496** (494–500) |

Kompaktni format smanjuje broj izlaznih tokena jer model više ne generiše JSON, nego kratku liniju oblika `claim rizik_sudara`. U prvoj iteraciji JSON izlaz je tipično bio oko 20 tokena, dok je u drugoj iteraciji izlaz prevoda smanjen na 8 tokena za lokalni model i 10 tokena za OpenAI profil.

Veći dio ukupne potrošnje dolazi iz prompta, ali latenciju posebno povećava duži izlaz jer se odgovor generiše token po token. Zato je za ovaj zadatak korisno držati izlaz što kraćim. Kada se uračunaju i prevod i objašnjenje, jedan prolazak kroz pipeline na `local` profilu troši **oko 820 tokena**.

### Determinizam prevoda

Pet pokretanja istog stress skupa:

| | local | openai |
|---|---|---|
| temperatura | 0.0 | 1.0 (model ne dopušta 0) |
| rezultat kroz 5 pokretanja | **identičan** | varirao |

Za `openai` profil nije bilo moguće forsirati `temperature=0`, pa je korištena podrazumijevana vrijednost modela. Zbog toga se rezultat kroz više pokretanja razlikovao.

| slučaj | neuspješna pokretanja | priroda |
| --- | --- | --- |
| `valid_approaching_fast` | 5/5 | dvosmislen prompt |
| `reject_icy_road` | 2/5 | varijansa temperature |

`valid_approaching_fast` je pokazao da je korišćeni prompt bio dvosmislen za izjave koje istovremeno opisuju stanje na putu i postavljaju pitanje. Naknadno je prompt dodatno preciziran.

`reject_icy_road` je izjava van domena jer led nije dio baze znanja. U dva od pet pokretanja model ju je pogrešno povezao sa `losi_uslovi` i prihvatio nepodržan upit.

## Zaključak i ograničenja

Iz rezultata se može zaključiti da trenutna implementacija ispravno radi na pokrivenim evaluacionim slučajevima. Logički sloj je deterministički, a razlike između LLM konfiguracija najviše se vide u latenciji, potrošnji tokena i stabilnosti prevoda.

Treba imati u vidu da su skupovi mali i ručno pisani, pa visoka tačnost ne znači opštu pouzdanost sistema, nego samo da u pokrivenim slučajevima nisu uočene očigledne greške.



## Fajlovi sa rezultatima

| tabela | fajl u `experiments/results/` |
|---|---|
| logika | `logic_20260911_182804.csv` |
| iteracija 1, prevod, glavni | `translation_20260912_080317.csv` |
| iteracija 1, prevod, stress | `translation_stress_20260911_180440.csv`, `…180655.csv`, `…184823.csv` |
| iteracija 1, `unsupported` mod | `translation_stress_20260911_152445.csv` (prije), `…180440.csv`, `…184823.csv` (poslije) |
| iteracija 2, prevod, glavni | `translation_20260912_140539.csv` |
| iteracija 2, prevod, stress ×5 | `translation_stress_20260912_134020.csv`, `…134120.csv`, `…135240.csv`, `…135309.csv`, `…135344.csv` |
