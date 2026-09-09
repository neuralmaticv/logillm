# logillm - hibridni AI sistem: logika + LLM

Projekat iz predmeta *Uvod u vještačku inteligenciju*, Prirodno-matematički fakultet, UNIBL.

Sistem za procjenu prijetnje u ADAS domenu (pomoć vozaču). Odluku donosi **deterministički sloj iskazne logike**, a LLM služi samo za prevod između prirodnog jezika i formalnog zapisa.

## Preduslovi

### LLM sloj

- računar ili server sa NVIDIA GPU
- Docker + NVIDIA Container Toolkit
- pristup HuggingFace-u radi preuzimanja LLM modela

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

### Konfiguracija

Adresa servera se zadaje kroz environment varijable:

```bash
LOGILLM_LLM_URL=http://<ip-servera>:8111/v1
LOGILLM_LLM_MODEL=Qwen/Qwen3.5-9B
```
