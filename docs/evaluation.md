# Evaluacija

Evaluacija je odvojena na dva sloja: formalnu logiku i LLM prevod korisničke izjave u strukturirani upit. Slojevi su mjereni odvojeno da bi se jasno razlikovalo da li eventualna greška dolazi iz razumijevanja izjave ili iz formalne obrade pravila i senzorskih očitavanja.

**Dva skupa:**

- **glavni** — 15 podržanih izjava (`eval_cases.jsonl`)
- **stress** — 20 izjava: 9 složenijih, ali podržanih izjava, 11 koje treba odbiti (`eval_stress_cases.jsonl`)

**Dvije evaluacije:**

- **logika** — presuda iz očekivanog upita i očitavanja senzora, bez LLM-a, na glavnom skupu
- **prevod** — izjava u strukturirani upit, u tri konfiguracije: `local` (Qwen3.5-9B, L40S), `local-thinking` (isti model, thinking uključen) i `openai` (gpt-5.6-luna)

Slojevi se mjere odvojeno jer greške nisu iste prirode: prevod može pogriješiti u razumijevanju izjave, dok greška u logičkom sloju može doći iz pravila, groundinga ili same implementacije. Da se mjeri samo krajnji izlaz, ne bi se znalo koji sloj je pogriješio.

## 1. LLM prevod u upit

| | local | openai | local-thinking |
|---|---|---|---|
| glavni skup, tačan upit | 15/15 | 15/15 | 15/15 |
| stress, složeniji validni | 9/9 | 9/9 | 9/9 |
| stress, odbijeni | 11/11 | 11/11 | 11/11 |
| latencija, glavni skup | 0.63 s | 1.09 s | 15.54 s |
| latencija, stress | 0.49 s | 1.39 s | **34.54 s** |

Nijedna greška: 0 nevalidnih JSON odgovora, 0 izmišljenih ciljeva, 0 pogrešno prihvaćenih izjava, 0 ponovnih pokušaja.

Sve tri konfiguracije imaju istu tačnost, pa razliku pravi uglavnom latencija: lokalni model bez thinkinga je najbrži, OpenAI je do tri puta sporiji, a thinking 25 do 70 puta, zavisno od skupa. Pošto LLM ovdje samo popunjava fiksnu JSON šemu, thinking režim nije donio bolju tačnost, ali je značajno povećao latenciju.

## 2. Uticaj `unsupported` moda

Mod za izjave van domena uveden je naknadno. Tabela poredi isti podskup od 8 stress slučajeva koje je trebalo odbiti, sa tim modom i bez njega.

| | bez `unsupported` moda | sa `unsupported` modom |
|---|---|---|
| odbijeno | **0/8** | **8/8** |
| pogrešno prihvaćeno | 8 | 0 |

Bez posebnog izlaza za izjave van domena, model nije imao način da kaže da upit nije podržan. Zato je svih 8 takvih slučajeva pogrešno mapirao na neki od postojećih ciljeva, uključujući i pokušaje prompt injectiona. Dodavanje `unsupported` moda omogućilo je da se takve izjave eksplicitno odbiju.

Sa `unsupported` modom `local-thinking` daje isti rezultat, 8/8 uz 33.37 s. Bez njega je pet slučajeva završilo timeoutom, pa je odgovoreno samo na tri, i sva tri su pogrešno prihvaćena.

## 3. Logika

Glavni skup, bez LLM-a.

| | |
|---|---|
| tačne presude | 15/15 |
| prosječno vrijeme | 158 ms |
| najduže vrijeme | 615 ms |

Presude: 5 MORA VAŽITI, 4 NE MORA VAŽITI, 3 SMIJE, 3 NE SMIJE.

Presude su determinističke: ista očitavanja i isti upit uvijek daju isti rezultat, pa ponovljeni run mijenja samo vrijeme. Najsporiji su odbijeni zahtjevi (do 615 ms), jer traženje konfliktnih pravila ponavlja provjeru konzistentnosti.

## Napomene

Skupovi su mali i ručno pisani, pa 15/15 i 20/20 znače da nema očiglednih grešaka, a ne da ih nema uopšte. Testirano je 6 od 12 mogućih ciljeva, a retry/self-refinement mehanizam se nijednom nije aktivirao.

## Fajlovi sa rezultatima

| tabela | fajl u `experiments/results/` |
|---|---|
| prevod, glavni | `translation_20260912_080317.csv` |
| prevod, stress | `translation_stress_20260911_180440.csv`, `…180655.csv`, `…184823.csv` |
| `unsupported` mod | `translation_stress_20260911_152445.csv` (prije), `…180440.csv`, `…184823.csv` (poslije) |
| logika | `logic_20260911_182804.csv` |
