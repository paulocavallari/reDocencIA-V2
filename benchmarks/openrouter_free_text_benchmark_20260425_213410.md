# OpenRouter Free Text Models Benchmark

Ranking por menor latência total (mediana).

| # | Model | Success Rate | Median (ms) | P95 (ms) |
|---|---|---:|---:|---:|
| 1 | liquid/lfm-2.5-1.2b-thinking:free | 100% | 3114.39 | 3738.81 |
| 2 | liquid/lfm-2.5-1.2b-instruct:free | 100% | 3225.71 | 3459.59 |
| 3 | inclusionai/ling-2.6-flash:free | 100% | 7832.83 | 11278.71 |
| 4 | nvidia/nemotron-3-nano-30b-a3b:free | 100% | 9979.90 | 10017.33 |
| 5 | inclusionai/ling-2.6-1t:free | 100% | 20223.97 | 20726.28 |
| 6 | openai/gpt-oss-20b:free | 100% | 37492.21 | 39717.32 |
| 7 | nvidia/nemotron-nano-9b-v2:free | 100% | 37629.21 | 61984.62 |
| 8 | openai/gpt-oss-120b:free | 100% | 75621.70 | 78080.31 |
| 9 | z-ai/glm-4.5-air:free | 100% | 98182.21 | 121176.69 |
| 10 | tencent/hy3-preview:free | 67% | 100892.91 | 140466.60 |

## Notas
- Escopo: modelos gratuitos com id `:free` e modalidade `text->text`.
- Configuração: `max_tokens=5000` por tentativa.
- Se um modelo falhar em todas as tentativas, mediana/p95 ficam vazios.