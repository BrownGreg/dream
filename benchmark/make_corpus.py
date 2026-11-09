"""Génère les fichiers audio du corpus à partir des textes de référence.

Corpus **synthétique uniquement** (aucun rêve réel, cf. CLAUDE.md). Moteur :
- `--engine mistral` : Voxtral TTS (voix française), si MISTRAL_API_KEY est défini ;
- `--engine espeak`  : espeak + ffmpeg en local (voix robotique, sans transfert).

Biais signalé : un audio produit par le TTS Mistral puis transcrit par le STT Mistral
peut favoriser ce fournisseur ; le manifeste trace le moteur utilisé.

Usage : python benchmark/make_corpus.py --engine espeak
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
REFS = HERE / "corpus" / "references"
AUDIO = HERE / "corpus" / "audio"


def with_espeak(text: str, out: Path) -> None:
    """Synthèse locale espeak → WAV → MP3 (ffmpeg)."""
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    ffmpeg = shutil.which("ffmpeg")
    if not espeak or not ffmpeg:
        raise RuntimeError("espeak et ffmpeg sont requis")
    wav = out.with_suffix(".wav")
    subprocess.run([espeak, "-v", "fr", "-s", "110", "-w", str(wav), text], check=True)  # noqa: S603
    subprocess.run(  # noqa: S603
        [ffmpeg, "-y", "-loglevel", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", str(out)],
        check=True,
    )
    wav.unlink()


def with_mistral(text: str, out: Path) -> None:
    """Synthèse Voxtral TTS (réponse JSON, audio base64 dans `audio_data`)."""
    response = httpx.post(
        "https://api.mistral.ai/v1/audio/speech",
        headers={"Authorization": f"Bearer {os.environ['MISTRAL_API_KEY']}"},
        json={
            "model": os.environ.get("MISTRAL_TTS_MODEL", "voxtral-mini-tts-3-0"),
            "input": text,
            "voice_id": os.environ.get("MISTRAL_TTS_VOICE", "voice_592"),
            "response_format": "mp3",
        },
        timeout=120,
    )
    response.raise_for_status()
    out.write_bytes(base64.b64decode(response.json()["audio_data"]))


def duration_s(path: Path) -> float:
    """Durée d'un fichier audio via ffprobe."""
    ffprobe = shutil.which("ffprobe") or "ffprobe"
    res = subprocess.run(  # noqa: S603
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return round(float(res.stdout.strip()), 2)


def main() -> None:
    """Génère l'audio de chaque texte de référence et écrit le manifeste."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", choices=["espeak", "mistral"], default="espeak")
    args = parser.parse_args()
    load_dotenv(HERE.parent / ".env")
    AUDIO.mkdir(parents=True, exist_ok=True)
    manifest = []
    for ref in sorted(REFS.glob("*.txt")):
        out = AUDIO / f"{ref.stem}.mp3"
        text = ref.read_text("utf-8").strip()
        (with_mistral if args.engine == "mistral" else with_espeak)(text, out)
        manifest.append({"id": ref.stem, "file": out.name, "duration_s": duration_s(out)})
        print(f"{out.name}: {manifest[-1]['duration_s']} s")
    (AUDIO / "manifest.json").write_text(
        json.dumps(
            {
                "engine": args.engine,
                "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
                "items": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
