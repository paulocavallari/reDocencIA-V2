# OpenRouter Free Text Models Benchmark

Ranking por menor latência total (mediana).

| # | Model | Success Rate | Median (ms) | P95 (ms) |
|---|---|---:|---:|---:|
| 1 | inclusionai/ling-2.6-flash:free | 100% | 8842.13 | 8842.13 |
| 2 | inclusionai/ling-2.6-1t:free | 100% | 18176.51 | 18176.51 |
| 3 | cognitivecomputations/dolphin-mistral-24b-venice-edition:free | 0% | - | - |

## Notas
- Escopo: modelos gratuitos com id `:free` e modalidade `text->text`.
- Configuração: `max_tokens=5000` por tentativa.
- Se um modelo falhar em todas as tentativas, mediana/p95 ficam vazios.