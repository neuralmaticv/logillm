# logillm - hibridni AI sistem: logika + LLM

Projekat iz predmeta *Uvod u vještačku inteligenciju*, Prirodno-matematički fakultet, UNIBL.

Sistem za procjenu prijetnje u ADAS domenu (pomoć vozaču / korisniku). Odluku donosi **deterministički sloj iskazne logike**, a LLM služi samo za prevod između prirodnog jezika i formalnog zapisa.

## Arhitektura

![Arhitektura sistema](docs/diagrams/logillm-arch.png)

Sistem prima dvije međusobno nezavisne vrste ulaza: očitavanja senzora i izjavu korisnika. Očitavanja opisuju trenutno stanje na putu, dok izjava određuje o čemu korisnik pita ili koju radnju zahtijeva.

**Baza znanja** objedinjuje pragove senzora, dozvoljene pojmove i formalna pravila ADAS domena. Tokom **grounding** koraka numerička očitavanja se, prema tim pragovima, pretvaraju u istinitosne vrijednosti logičkih činjenica. Time se podaci prevode u oblik koji formalni sloj može obraditi.

Izjava korisnika prolazi odvojenim putem. LLM je pretvara u strukturirani upit koji sadrži vrstu namjere, ciljni pojam i, kada je potrebno, brojčanu vrijednost iz korisničkog zahtjeva. Dobijeni upit se zatim validira: prihvataju se samo očekivana struktura, podržana vrsta namjere i unaprijed definisani pojmovi koje sistem može obraditi. Ako validacija odbije odgovor, LLM dobija nazad svoj odgovor i poruku o grešci, pa u sljedećem pokušaju može sam ispraviti izlaz (*self-refinement*, po uzoru na Logic-LM). Ako ni nakon tri pokušaja upit nije ispravan, sistem prijavljuje grešku.

**Logičko jezgro** povezuje validirani upit sa činjenicama dobijenim iz senzora i pravilima iz baze znanja. Ako korisnik postavlja pitanje, provjerava se da li traženi zaključak slijedi iz tih činjenica i pravila. Ako zahtijeva radnju, provjerava se da li je ona u skladu sa trenutnim stanjem i pravilima.

Uz odluku se čuva i formalni osnov, kao što su relevantni koraci izvođenja, neispunjeni uslovi ili konfliktna pravila. LLM taj već utvrđeni rezultat samo pretvara u kratko objašnjenje razumljivo korisniku.

## Primjer

Isti upit korisnika, dva različita očitavanja senzora. Prevod je u oba slučaja identičan; presudu mijenjaju senzori.

```text
korisnik: Postoji li opasnost od sudara?
prevod:   {"mode": "claim", "target": "rizik_sudara"}

  smanjena vidljivost, vozilo je blizu i brzo mu se približavamo
    presuda:     MORA VAŽITI
    osnov:       sa senzora: blizu, brzo_priblizavanje
    osnov:       ((blizu & brzo_priblizavanje) -> rizik_sudara)
    objašnjenje: Postoji opasnost od sudara jer je vozilo blizu i brzo mu se približavamo.

  dobra vidljivost, vozilo ostaje na sigurnoj udaljenosti
    presuda:     NE MORA VAŽITI
    osnov:       nije utvrđeno: rizik_sudara
    osnov:       jer nije ispunjeno: blizu, brzo_priblizavanje
    objašnjenje: Očitavanja ne ukazuju na opasnost od sudara jer vozilo ostaje na sigurnoj udaljenosti.
```

Šta se iz ovoga vidi:

- **Senzorska očitavanja određuju rezultat.** LLM prevodi isti upit na isti način, dok formalni sloj procjenjuje svaku situaciju zasebno.
- **Objašnjenje se zasniva isključivo na navedenom osnovu.** LLM dobija odluku i pravila koja su do nje dovela, bez mogućnosti da ih dopuni ili izmijeni.
- **Presuda je deterministička, za razliku od objašnjenja.** Ponovno pokretanje istog scenarija daje istu odluku, dok se tekst objašnjenja može razlikovati.

## Preduslovi

### Logički sloj

- **Python 3.14** (razvijano na 3.14.0; verzija je zaključana u `.python-version`)
- **[uv](https://docs.astral.sh/uv/) 0.9+** — upravljanje okruženjem i zavisnostima

### LLM sloj

- računar ili server sa NVIDIA GPU
- Docker + NVIDIA Container Toolkit
- pristup HuggingFace-u radi preuzimanja LLM modela

## Instalacija

```bash
git clone https://github.com/neuralmaticv/logillm.git
cd logillm
uv sync
```

Komanda `uv sync` koristi verziju Pythona navedenu u `.python-version`, instalira zavisnosti i pravi virtuelno okruženje u direktorijumu `.venv` unutar projekta. Okruženje nije potrebno ručno aktivirati: naredbe projekta pokreću se sa `uv run`.

### Konfiguracija

Za pokretanje cijelog hibridnog sistema prvo kopirajte primjer konfiguracije:

```bash
cp .env.example .env
```

Podešavanja se čitaju iz `.env`, dok ih vrijednosti zadane kroz okruženje mogu privremeno nadjačati.

```bash
# LLM provider: local | openai
LOGILLM_LLM_PROVIDER=local

# lokalni vLLM server
LOGILLM_LOCAL_URL=http://<ip-servera>:8111/v1
LOGILLM_LOCAL_MODEL=Qwen/Qwen3.5-9B
LOGILLM_LOCAL_THINKING=0

# OpenAI
LOGILLM_OPENAI_URL=https://api.openai.com/v1
LOGILLM_OPENAI_MODEL=<naziv-modela>
OPENAI_API_KEY=<kljuc>
```

Za lokalni LLM potrebno je podesiti adresu vLLM servera i naziv modela. Za OpenAI potrebno je navesti ID/naziv modela i `OPENAI_API_KEY`.

`LOGILLM_LOCAL_THINKING=0` isključuje *thinking* režim LLM-a.

## Pokretanje

CLI je glavni entry point za pokretanje cijelog pipelinea nad jednom izjavom korisnika i jednim skupom senzorskih očitavanja:

```bash
uv run logillm "Postoji li opasnost od sudara?" \
  --udaljenost 12 \
  --relativna-brzina 6 \
  --vidljivost 30
```

Provider se podrazumijevano čita iz `.env`, a za pojedinačno pokretanje može se zadati argumentom `--provider local|openai`. Na primjer, za lokalni LLM:

```bash
uv run logillm "Uključi tempomat." \
  --udaljenost 60 \
  --relativna-brzina 0 \
  --vidljivost 500 \
  --provider local
```

Spisak svih argumenata:

```bash
uv run logillm --help
```

Zahtjev za postavljanje brzine tumači se kao podešavanje tempomata, a zahtjev za ubrzavanje ("Ubrzaj na 120 km/h.") kao posebna radnja. U oba slučaja LLM izdvaja traženu brzinu, dok formalni sloj odlučuje da li je ona dozvoljena u odnosu na ograničenje i trenutno stanje:

```bash
uv run logillm "Postavi brzinu na 100 km/h." \
  --udaljenost 60 \
  --relativna-brzina 0 \
  --vidljivost 500 \
  --ogranicenje-brzine 130
```

Postojeće demo skripte za unaprijed definisane primjere:

```bash
uv run demo_logic.py
uv run demo_llm.py local
```

Provjera koda:

```bash
uv run ruff check .
uv run ruff format .
```

## Evaluacija

```bash
uv run scripts/evaluate_logic.py
uv run scripts/evaluate_translation.py --config local --config local-thinking --config openai
uv run scripts/evaluate_translation.py --stress --config local --config local-thinking --config openai
```

Rezultati po slučaju upisuju se u `experiments/results/`, a analiza je dostupna u [docs/evaluation.md](docs/evaluation.md).

## LLM server

U ovoj fazi koristi se lokalni LLM model `Qwen/Qwen3.5-9B` ([HF repo](https://huggingface.co/Qwen/Qwen3.5-9B)), serviran preko `vLLM` instance sa OpenAI-kompatibilnim endpointom. Izbor konkretnog modela nije presudan, jer LLM ne donosi formalnu odluku, već prevodi ulaz i objašnjava rezultat logičkog modula.

Komanda korišćena za pokretanje servera:
```bash
docker run -d --rm --name vllm-test --gpus all --ipc host --network host \
  -e HF_HOME=/hf-cache-path/ \
  -v /hf-cache-path/:/hf-cache-path/ \
  --group-add <gid-for-gpu> \
  --entrypoint vllm \
  nvcr.io/nvidia/ai-dynamo/vllm-runtime:1.4.2 \
  serve Qwen/Qwen3.5-9B \
    --host 0.0.0.0 --port 8111 \
    --gpu-memory-utilization 0.50 \
    --max-model-len 16384 \
    --max-num-seqs 32
```

| Opcija | Značenje |
|---|---|
| `--ipc host` | dijeljena memorija hosta jer je Dockerova memorija premaala za PyTorch | 
| `-v ...` | keš modela ostaje na hostu, pa se ne preuzima ponovo |
| `--gpu-memory-utilization 0.50` | zauzima 50% ukupne GPU memorije |
| `--max-model-len 16384` | najveća dužina konteksta; po potrebi smanjiti |

## Reference

- Pan, Albalak, Wang i Wang. **Logic-LM: Empowering Large Language Models with Symbolic Solvers for Faithful Logical Reasoning**. [arXiv:2305.12295](https://arxiv.org/abs/2305.12295), 2023.
- Yang i Tam. **Exploring an LM to Generate Prolog Predicates from Mathematics Questions**. [arXiv:2309.03667](https://arxiv.org/abs/2309.03667), 2023.
- Yang, Chen i Tam. **Arithmetic Reasoning with LLM: Prolog Generation & Permutation**. [arXiv:2405.17893](https://arxiv.org/abs/2405.17893), 2024.
- Han, Chen, Gupta i Altintas. **Scene-Aware Conversational ADAS with Generative AI for Real-Time Driver Assistance**. [arXiv:2507.10500](https://arxiv.org/abs/2507.10500), 2025.
