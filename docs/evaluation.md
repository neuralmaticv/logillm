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
| sistemski prompt, prevod | ~704 tokena | 546 tokena |
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
| latencija, medijan | 0.34 s | 0.82 s |
| latencija, p95 | 0.43 s | 1.22 s |

Stress skup, **pet ponovljenih pokretanja**:

| | local | openai |
|---|---|---|
| složeniji validni | **100%** (9/9, svih 5 puta) | **100%** (9/9, svih 5 puta) |
| odbijeni | 90.9% (10/11, svih 5 puta) | **100%** (11/11, svih 5 puta) |
| latencija, medijan | 0.27 s | 0.83 s |
| latencija, p95 | 0.42 s | 1.39 s |
| latencija, max | 0.49 s | 1.96 s |

Percentili su računati na objedinjenih 100 mjerenja po konfiguraciji (5 pokretanja × 20 slučajeva).

### Potrošnja tokena

Vrijednosti dolaze iz `usage` polja u odgovoru servera. Navedena je medijana, a u zagradi raspon po slučajevima.

| poziv | prompt | izlaz | ukupno |
|---|---|---|---|
| prevod, `local` (n=15) | 546 (544–550) | 8 (6–12) | **553** (551–562) |
| prevod, `openai` (n=15) | 519 (516–520) | 10 (8–63) | **529** (526–580) |
| objašnjenje, `local` (n=10) | 269 (235–312) | 35 (20–56) | **305** (260–354) |

Kompaktni format smanjuje broj izlaznih tokena jer model više ne generiše JSON, nego kratku liniju oblika `claim rizik_sudara`. U prvoj iteraciji JSON izlaz je tipično bio oko 20 tokena, dok je u drugoj iteraciji izlaz prevoda smanjen na 8 tokena za lokalni model i 10 tokena za OpenAI profil.

Veći dio ukupne potrošnje dolazi iz prompta, ali latenciju posebno povećava duži izlaz jer se odgovor generiše token po token. Zato je za ovaj zadatak korisno držati izlaz što kraćim. Kada se uračunaju i prevod i objašnjenje, jedan prolazak kroz pipeline na `local` profilu troši **oko 820 tokena**.

### Stabilnost prevoda

Pet pokretanja istog stress skupa:

| | local | openai |
|---|---|---|
| temperatura | 0.0 | 1.0 (model ne dopušta 0) |
| rezultat kroz 5 pokretanja | **identičan** | **identičan** |

Za `openai` profil nije bilo moguće forsirati `temperature=0`, pa je korištena podrazumijevana vrijednost modela. U finalnoj verziji prompta oba profila su ipak kroz pet pokretanja davala isti rezultat.

### Dorada prompta i granica evaluacionog skupa

Nakon prelaska na kompaktni format prompt je dodatno dorađivan prema slučajevima koji su padali na stress skupu.

| izmjena prompta | posljedica |
| --- | --- |
| prelazak na jednu liniju | `openai` počinje da pada na `valid_approaching_fast` |
| preformulisano pravilo o opisu vozačeve situacije | popravlja `valid_approaching_fast`, kvari `reject_icy_road` |
| dodato **"These are exact concepts, not loose synonyms"** | popravlja `reject_icy_road` kod `openai`, ne i kod `local` |

Rezultat kroz pet pokretanja stress skupa, prije i poslije dorade:

| | validni | odbijeni | padovi |
| --- | --- | --- | --- |
| `local`, prije | 45/45 (100%) | 55/55 (100%) | nema |
| `openai`, prije | 40/45 (88.9%) | 53/55 (96.4%) | `valid_approaching_fast` 5/5, `reject_icy_road` 2/5 |
| `local`, poslije | 45/45 (100%) | 50/55 (90.9%) | `reject_icy_road` 5/5 |
| `openai`, poslije | 45/45 (100%) | 55/55 (100%) | nema |

Ukupan broj grešaka se smanjio sa 7 na 5, ali se greška promijenila između profila: izmjena koja je pomogla `openai` profilu pogoršala je rezultat kod `local` profila. To pokazuje da prompt nije neutralna komponenta sistema, nego dio koji može različito djelovati na različite modele.

Treba imati u vidu da su ove izmjene rađene prema istom stress skupu na kojem se rezultat mjeri. Zato finalni brojevi mogu biti optimistični: skup je djelimično postao skup za podešavanje prompta, a ne potpuno nezavisna provjera. Dalje dotjerivanje prompta je zato zaustavljeno, jer bi dodatne izmjene mogle samo bolje uklopiti instrukcije u postojećih 20 slučajeva, bez dokaza da pomažu na novim izjavama.

### Preostali slučaj: `reject_icy_road`

`reject_icy_road` (**"Je li zaleđen put?"**) je izjava van domena, jer led nije dio baze znanja. `local` ju je u svih pet pokretanja povezao sa `losi_uslovi` i prihvatio nepodržan upit, dok ju je `openai` svih pet puta odbio.

Slučaj je zadržan jer pokazuje ograničenje LLM prevoda: model može pogrešno povezati korisnički izraz sa postojećim ciljem iz zatvorenog rječnika. To ne znači da može izmisliti novu činjenicu ili promijeniti logička pravila, ali može dovesti do odgovora na pogrešno mapiran upit. U ovom slučaju prihvatanje nepodržanog pitanja je nepovoljnije od odbijanja podržanog, jer sistem odgovara na nešto što ne modeluje pouzdano.

## Zaključak i ograničenja

Iz rezultata se može zaključiti da trenutna implementacija ispravno radi na pokrivenim evaluacionim slučajevima. Logički sloj je deterministički, a razlike između LLM konfiguracija najviše se vide u latenciji, potrošnji tokena i stabilnosti prevoda.

Treba imati u vidu dva ograničenja. Skupovi su mali i ručno pisani, pa visoka tačnost ne znači opštu pouzdanost sistema, nego samo da u pokrivenim slučajevima nisu uočene očigledne greške. Uz to je prompt za prevod doteran prema padovima na tom istom stress skupu, pa prijavljena tačnost prevoda mjeri uklapanje u poznate slučajeve prije nego generalizaciju. Nezavisna procjena tražila bi skup izjava koji nije korišten tokom dorade prompta.

## Fajlovi sa rezultatima

| tabela | fajl u `experiments/results/` |
|---|---|
| logika | `logic_20260911_182804.csv` |
| iteracija 1, prevod, glavni | `translation_20260912_080317.csv` |
| iteracija 1, prevod, stress | `translation_stress_20260911_180440.csv`, `…180655.csv`, `…184823.csv` |
| iteracija 1, `unsupported` mod | `translation_stress_20260911_152445.csv` (prije), `…180440.csv`, `…184823.csv` (poslije) |
| iteracija 2, prevod, glavni | `translation_20260912_153316.csv` |
| iteracija 2, prevod, stress ×5, prije dorade prompta | `translation_stress_20260912_134020.csv`, `…134120.csv`, `…135240.csv`, `…135309.csv`, `…135344.csv` |
| iteracija 2, prevod, stress ×5, poslije dorade prompta | `translation_stress_20260912_152422.csv`, `…152542.csv`, `…152611.csv`, `…152637.csv`, `…152706.csv` |
