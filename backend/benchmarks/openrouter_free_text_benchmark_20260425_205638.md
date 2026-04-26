# OpenRouter Free Text Models Benchmark

Ranking por menor latência total (mediana).

| # | Model | Success Rate | Median (ms) | P95 (ms) |
|---|---|---:|---:|---:|
| 1 | cognitivecomputations/dolphin-mistral-24b-venice-edition:free | 0% | - | - |
| 2 | google/gemma-3n-e2b-it:free | 0% | - | - |
| 3 | google/gemma-3n-e4b-it:free | 0% | - | - |

## Notas
- Escopo: modelos gratuitos com id `:free` e modalidade `text->text`.
- Configuração: `max_tokens=5000` por tentativa.
- Se um modelo falhar em todas as tentativas, mediana/p95 ficam vazios.