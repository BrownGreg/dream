"""Mesure de latence des API : N appels par fournisseur sur le corpus fixe.

Usage :
    python benchmark/run_latency.py --mock              # sans clé, valide la chaîne
    python benchmark/run_latency.py --live -n 10        # fournisseurs dont la clé est présente
    python benchmark/run_latency.py --live --list-models
    python benchmark/run_latency.py --local -n 10       # faster-whisper, sans clé ni transfert

Sorties (jamais éditées à la main) :
    benchmark/results/latency_<mode>_<horodatage>.csv   une ligne par appel
    benchmark/results/summary_<mode>_<horodatage>.csv   p50/p95/p99, erreurs, retries
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import os
import statistics
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import httpx
from catalog import load_catalog
from dotenv import load_dotenv
from providers.base import BenchItem, BenchProvider, CallResult
from providers.mistral import MistralLLM, MistralSTT, MistralTTS, list_models
from providers.mock import MockProvider

HERE = Path(__file__).resolve().parent
CORPUS = HERE / "corpus"
RESULTS = HERE / "results"
TTS_CHARS = 400  # aligné sur l'hypothèse H6


def load_items(category: str) -> list[BenchItem]:
    """Construit les entrées du corpus pour une catégorie."""
    refs = sorted((CORPUS / "references").glob("*.txt"))
    if category == "STT":
        items = []
        for ref in refs:
            audio = CORPUS / "audio" / f"{ref.stem}.mp3"
            if audio.exists():
                items.append(BenchItem(ref.stem, ref.read_text("utf-8").strip(), str(audio)))
        return items
    if category == "T2I":
        with (CORPUS / "prompts.toml").open("rb") as fh:
            return [BenchItem(p["id"], p["text"]) for p in tomllib.load(fh)["prompt"]]
    texts = [BenchItem(r.stem, r.read_text("utf-8").strip()) for r in refs]
    if category == "TTS":
        return [BenchItem(t.item_id, t.text[:TTS_CHARS]) for t in texts]
    return texts


def live_providers() -> list[BenchProvider]:
    """Adapters réels disponibles selon les clés présentes dans l'environnement."""
    providers: list[BenchProvider] = []
    if os.environ.get("MISTRAL_API_KEY"):
        providers += [
            MistralSTT("mistral_voxtral_mini_3"),
            MistralSTT("mistral_voxtral_small_3"),
            MistralLLM(),
            MistralTTS(),
        ]
    return providers


def percentile(values: list[float], q: float) -> float:
    """Percentile par interpolation linéaire (q entre 0 et 100)."""
    if not values:
        return float("nan")
    if len(values) == 1:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[int(q) - 1]


def summarize(results: list[CallResult]) -> list[dict[str, object]]:
    """Agrège les appels par fournisseur."""
    rows: list[dict[str, object]] = []
    for key in sorted({r.provider for r in results}):
        rs = [r for r in results if r.provider == key]
        ok = [r for r in rs if r.ok]
        totals = [r.total_s for r in ok]
        ttfbs = [r.ttfb_s for r in ok]
        rows.append(
            {
                "provider": key,
                "category": rs[0].category,
                "mode": rs[0].mode,
                "calls": len(rs),
                "errors": len(rs) - len(ok),
                "error_rate": round((len(rs) - len(ok)) / len(rs), 4),
                "retries": sum(r.retries for r in rs),
                "p50_total_s": round(percentile(totals, 50), 3),
                "p95_total_s": round(percentile(totals, 95), 3),
                "p99_total_s": round(percentile(totals, 99), 3),
                "p50_ttfb_s": round(percentile(ttfbs, 50), 3),
                "p95_ttfb_s": round(percentile(ttfbs, 95), 3),
                "mean_billed_audio_s": round(
                    statistics.fmean([r.billed_audio_s for r in ok]) if ok else 0.0, 2
                ),
                "mean_prompt_tokens": round(
                    statistics.fmean([r.prompt_tokens for r in ok]) if ok else 0.0, 1
                ),
                "mean_completion_tokens": round(
                    statistics.fmean([r.completion_tokens for r in ok]) if ok else 0.0, 1
                ),
            }
        )
    return rows


async def campaign(providers: list[BenchProvider], n: int) -> list[CallResult]:
    """Exécute N appels séquentiels par fournisseur (pas de concurrence : latence nette)."""
    results: list[CallResult] = []
    timeout = httpx.Timeout(120.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        for provider in providers:
            items = load_items(provider.category)
            if not items:
                print(f"  {provider.key}: corpus vide pour {provider.category}, ignoré")
                continue
            for i in range(n):
                result = await provider.run(client, items[i % len(items)])
                results.append(result)
            done = [r for r in results if r.provider == provider.key]
            print(f"  {provider.key}: {sum(r.ok for r in done)}/{len(done)} OK")
    return results


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    """Écrit des lignes homogènes en CSV UTF-8."""
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    """Point d'entrée CLI."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true", help="adapters simulés, aucune clé requise")
    mode.add_argument("--live", action="store_true", help="appels réels (clés dans .env)")
    mode.add_argument("--local", action="store_true", help="faster-whisper sur cette machine")
    parser.add_argument("-n", type=int, default=10, help="appels par fournisseur (10 à 30)")
    parser.add_argument("--only", nargs="*", default=None, help="clés de catalogue à mesurer")
    parser.add_argument("--list-models", action="store_true", help="liste les modèles Mistral")
    args = parser.parse_args()
    load_dotenv(HERE.parent / ".env")

    if args.list_models:

        async def _list() -> list[str]:
            async with httpx.AsyncClient(timeout=30) as client:
                return await list_models(client)

        print("\n".join(asyncio.run(_list())))
        return 0

    if args.mock:
        _, catalog = load_catalog()
        providers: list[BenchProvider] = [
            MockProvider(p.key, p.category)
            for p in catalog
            if p.category in {"STT", "LLM", "TTS", "T2I"}
        ]
    elif args.local:
        from providers.local_whisper import LocalWhisper

        whisper = LocalWhisper()
        print(f"Modèle chargé en {whisper.load_s:.1f} s ({whisper.hardware})")
        providers = [whisper]
    else:
        providers = live_providers()
        if not providers:
            print("Aucune clé API trouvée dans .env : utilisez --mock.", file=sys.stderr)
            return 2
    if args.only:
        providers = [p for p in providers if p.key in args.only]

    label = "mock" if args.mock else ("local" if args.local else "live")
    print(f"Campagne {label} : {len(providers)} fournisseurs × {args.n} appels")
    results = asyncio.run(campaign(providers, args.n))
    if not results:
        print("Aucun résultat.", file=sys.stderr)
        return 1
    RESULTS.mkdir(exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    raw_path = RESULTS / f"latency_{label}_{stamp}.csv"
    sum_path = RESULTS / f"summary_{label}_{stamp}.csv"
    write_csv(raw_path, [r.row() for r in results])
    summary = summarize(results)
    write_csv(sum_path, summary)
    for row in summary:
        print(
            f"  {row['provider']:28} p50={row['p50_total_s']}s p95={row['p95_total_s']}s "
            f"ttfb50={row['p50_ttfb_s']}s err={row['error_rate']:.0%} retries={row['retries']}"
        )
    print(f"→ {raw_path}\n→ {sum_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
