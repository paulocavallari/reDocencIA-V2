from __future__ import annotations

import argparse
import json
import os
import sys
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

MODELS_URL = "https://openrouter.ai/api/v1/models"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@dataclass
class AttemptResult:
    attempt: int
    elapsed_ms: float
    status_code: int
    ok: bool
    error: str | None
    completion_tokens: int | None


@dataclass
class ModelBenchmark:
    model_id: str
    context_length: int | None
    max_completion_tokens: int | None
    attempts: list[AttemptResult]

    @property
    def success_attempts(self) -> list[AttemptResult]:
        return [a for a in self.attempts if a.ok]

    @property
    def success_rate(self) -> float:
        if not self.attempts:
            return 0.0
        return len(self.success_attempts) / len(self.attempts)

    @property
    def median_ms(self) -> float | None:
        values = [a.elapsed_ms for a in self.success_attempts]
        if not values:
            return None
        return statistics.median(values)

    @property
    def p95_ms(self) -> float | None:
        values = sorted(a.elapsed_ms for a in self.success_attempts)
        if not values:
            return None
        if len(values) == 1:
            return values[0]
        index = int(round(0.95 * (len(values) - 1)))
        return values[index]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Benchmark OpenRouter free text/chat models (:free with text->text modality) "
            "using fixed 5000 max output tokens by default."
        )
    )
    parser.add_argument("--api-key", type=str, default=None, help="OpenRouter API key (fallback: OPENROUTER_API_KEY env)")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per model (default: 3)")
    parser.add_argument("--max-models", type=int, default=0, help="Cap number of models tested (0 = all)")
    parser.add_argument("--max-output-tokens", type=int, default=5000, help="max_tokens sent to API (default: 5000)")
    parser.add_argument("--timeout-seconds", type=float, default=120.0, help="HTTP timeout per request")
    parser.add_argument("--pause-ms", type=int, default=250, help="Pause between attempts in milliseconds")
    parser.add_argument("--output-dir", type=str, default="benchmarks", help="Output directory for reports")
    parser.add_argument(
        "--skip-db-lookup",
        action="store_true",
        help="Do not try reading openrouter_api_key from Setting table when env/key arg is missing",
    )
    return parser.parse_args()


def read_api_key_from_db() -> str | None:
    try:
        from app.database import SessionLocal
        from app.models import Setting
    except Exception:
        return None

    db = SessionLocal()
    try:
        setting = db.query(Setting).filter(Setting.key == "openrouter_api_key").first()
        return setting.value if setting and setting.value else None
    except Exception:
        return None
    finally:
        db.close()


def get_api_key(args: argparse.Namespace) -> str:
    api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key and not args.skip_db_lookup:
        api_key = read_api_key_from_db()

    if not api_key:
        raise SystemExit(
            "Missing OpenRouter API key. Use --api-key, set OPENROUTER_API_KEY, or keep DB lookup enabled."
        )
    return api_key


def is_free_text_model(model: dict[str, Any]) -> bool:
    model_id = str(model.get("id", ""))
    if not model_id.endswith(":free"):
        return False

    architecture = model.get("architecture") or {}
    modality = str(architecture.get("modality", ""))

    # User scope: free text/chat only (exclude multimodal and specialty models).
    if modality != "text->text":
        return False

    pricing = model.get("pricing") or {}
    if str(pricing.get("prompt", "")) != "0" or str(pricing.get("completion", "")) != "0":
        return False

    return True


def extract_candidates(models_payload: dict[str, Any], max_models: int, required_output_tokens: int) -> list[dict[str, Any]]:
    models = models_payload.get("data") or []
    candidates: list[dict[str, Any]] = []

    for model in models:
        if not isinstance(model, dict) or not is_free_text_model(model):
            continue

        top_provider = model.get("top_provider") or {}
        provider_max = top_provider.get("max_completion_tokens") if isinstance(top_provider, dict) else None
        if isinstance(provider_max, int) and provider_max < required_output_tokens:
            continue

        candidates.append(model)

    candidates.sort(key=lambda m: str(m.get("id", "")))

    if max_models and max_models > 0:
        return candidates[:max_models]
    return candidates


def build_prompt() -> str:
    # Fixed prompt to make latency comparison fair across models.
    return (
        "Você é um assistente pedagógico. Gere um plano de aula completo em português do Brasil, "
        "com introdução, desenvolvimento, conclusão e adaptações para educação especial. "
        "Use texto claro e aplicável."
    )


def parse_error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return response.text[:500]

    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message") or error.get("code")
        if message:
            return str(message)
    return json.dumps(payload)[:500]


def parse_completion_tokens(response: httpx.Response) -> int | None:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return None

    usage = payload.get("usage")
    if not isinstance(usage, dict):
        return None

    value = usage.get("completion_tokens")
    if isinstance(value, int):
        return value
    return None


def run_attempt(
    client: httpx.Client,
    *,
    api_key: str,
    model_id: str,
    max_output_tokens: int,
    attempt_number: int,
) -> AttemptResult:
    body = {
        "model": model_id,
        "temperature": 0.2,
        "max_tokens": max_output_tokens,
        "messages": [
            {"role": "system", "content": "Responda em português do Brasil."},
            {"role": "user", "content": build_prompt()},
        ],
    }

    started = time.perf_counter()
    try:
        response = client.post(
            CHAT_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://redocencia.app",
                "X-Title": "redocencia-benchmark",
            },
            json=body,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
    except httpx.TimeoutException:
        return AttemptResult(
            attempt=attempt_number,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            status_code=0,
            ok=False,
            error="timeout",
            completion_tokens=None,
        )
    except httpx.HTTPError as exc:
        return AttemptResult(
            attempt=attempt_number,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            status_code=0,
            ok=False,
            error=f"http-error: {exc}",
            completion_tokens=None,
        )

    if response.status_code >= 400:
        return AttemptResult(
            attempt=attempt_number,
            elapsed_ms=elapsed_ms,
            status_code=response.status_code,
            ok=False,
            error=parse_error_message(response),
            completion_tokens=None,
        )

    return AttemptResult(
        attempt=attempt_number,
        elapsed_ms=elapsed_ms,
        status_code=response.status_code,
        ok=True,
        error=None,
        completion_tokens=parse_completion_tokens(response),
    )


def benchmark_models(
    *,
    api_key: str,
    candidates: list[dict[str, Any]],
    attempts: int,
    max_output_tokens: int,
    timeout_seconds: float,
    pause_ms: int,
) -> list[ModelBenchmark]:
    results: list[ModelBenchmark] = []

    with httpx.Client(timeout=timeout_seconds) as client:
        for idx, model in enumerate(candidates, start=1):
            model_id = str(model.get("id", ""))
            provider = model.get("top_provider") or {}
            context_length = provider.get("context_length") if isinstance(provider, dict) else None
            max_completion = provider.get("max_completion_tokens") if isinstance(provider, dict) else None

            benchmark = ModelBenchmark(
                model_id=model_id,
                context_length=context_length if isinstance(context_length, int) else None,
                max_completion_tokens=max_completion if isinstance(max_completion, int) else None,
                attempts=[],
            )

            print(f"[{idx}/{len(candidates)}] Testing {model_id}")

            for attempt in range(1, attempts + 1):
                result = run_attempt(
                    client,
                    api_key=api_key,
                    model_id=model_id,
                    max_output_tokens=max_output_tokens,
                    attempt_number=attempt,
                )
                benchmark.attempts.append(result)
                state = "OK" if result.ok else f"FAIL ({result.status_code})"
                print(f"  attempt {attempt}: {state} - {result.elapsed_ms:.1f} ms")
                if pause_ms > 0:
                    time.sleep(pause_ms / 1000.0)

            results.append(benchmark)

    return results


def sort_ranked(results: list[ModelBenchmark]) -> list[ModelBenchmark]:
    def sort_key(item: ModelBenchmark) -> tuple[float, float, str]:
        median = item.median_ms if item.median_ms is not None else 10_000_000.0
        success_penalty = 1.0 - item.success_rate
        return (median, success_penalty, item.model_id)

    return sorted(results, key=sort_key)


def serialize_results(
    ranked: list[ModelBenchmark],
    *,
    generated_at: str,
    attempts: int,
    max_output_tokens: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": generated_at,
        "attempts_per_model": attempts,
        "max_output_tokens": max_output_tokens,
        "models_tested": len(ranked),
        "ranking": [],
    }

    for pos, item in enumerate(ranked, start=1):
        payload["ranking"].append(
            {
                "position": pos,
                "model_id": item.model_id,
                "context_length": item.context_length,
                "max_completion_tokens": item.max_completion_tokens,
                "success_rate": round(item.success_rate, 4),
                "median_ms": round(item.median_ms, 2) if item.median_ms is not None else None,
                "p95_ms": round(item.p95_ms, 2) if item.p95_ms is not None else None,
                "attempts": [
                    {
                        "attempt": a.attempt,
                        "elapsed_ms": round(a.elapsed_ms, 2),
                        "status_code": a.status_code,
                        "ok": a.ok,
                        "error": a.error,
                        "completion_tokens": a.completion_tokens,
                    }
                    for a in item.attempts
                ],
            }
        )

    return payload


def render_markdown_summary(ranked: list[ModelBenchmark], *, max_rows: int = 10) -> str:
    lines = [
        "# OpenRouter Free Text Models Benchmark",
        "",
        "Ranking por menor latência total (mediana).",
        "",
        "| # | Model | Success Rate | Median (ms) | P95 (ms) |",
        "|---|---|---:|---:|---:|",
    ]

    for pos, item in enumerate(ranked[:max_rows], start=1):
        median = f"{item.median_ms:.2f}" if item.median_ms is not None else "-"
        p95 = f"{item.p95_ms:.2f}" if item.p95_ms is not None else "-"
        lines.append(f"| {pos} | {item.model_id} | {item.success_rate:.0%} | {median} | {p95} |")

    lines.append("")
    lines.append("## Notas")
    lines.append("- Escopo: modelos gratuitos com id `:free` e modalidade `text->text`.")
    lines.append("- Configuração: `max_tokens=5000` por tentativa.")
    lines.append("- Se um modelo falhar em todas as tentativas, mediana/p95 ficam vazios.")
    return "\n".join(lines)


def save_reports(output_dir: Path, *, json_payload: dict[str, Any], markdown_summary: str) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"openrouter_free_text_benchmark_{stamp}.json"
    md_path = output_dir / f"openrouter_free_text_benchmark_{stamp}.md"

    json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(markdown_summary, encoding="utf-8")
    return json_path, md_path


def main() -> None:
    args = parse_args()
    api_key = get_api_key(args)

    with httpx.Client(timeout=args.timeout_seconds) as client:
        response = client.get(MODELS_URL)
        response.raise_for_status()
        models_payload = response.json()

    candidates = extract_candidates(models_payload, args.max_models, args.max_output_tokens)
    if not candidates:
        raise SystemExit("No free text/chat candidates found with current filters.")

    print(f"Candidates selected: {len(candidates)}")

    results = benchmark_models(
        api_key=api_key,
        candidates=candidates,
        attempts=args.attempts,
        max_output_tokens=args.max_output_tokens,
        timeout_seconds=args.timeout_seconds,
        pause_ms=args.pause_ms,
    )

    ranked = sort_ranked(results)
    generated_at = datetime.now(timezone.utc).isoformat()

    json_payload = serialize_results(
        ranked,
        generated_at=generated_at,
        attempts=args.attempts,
        max_output_tokens=args.max_output_tokens,
    )
    markdown_summary = render_markdown_summary(ranked)

    output_dir = Path(args.output_dir)
    json_path, md_path = save_reports(output_dir, json_payload=json_payload, markdown_summary=markdown_summary)

    print("\nTop 10 (median ms):")
    for pos, item in enumerate(ranked[:10], start=1):
        median = f"{item.median_ms:.1f} ms" if item.median_ms is not None else "no-success"
        print(f"{pos:>2}. {item.model_id} -> {median} (success: {item.success_rate:.0%})")

    print(f"\nJSON report: {json_path}")
    print(f"Markdown summary: {md_path}")


if __name__ == "__main__":
    main()
