"""Produce word timings for a verse, for karaoke playback in the viewer.

    python -m scripts.align_audio --audio track.mp3 --lyrics verse.txt -o timings.json

Alignment needs a forced aligner, and every option is heavy: WhisperX pulls in
torch, aeneas needs espeak and ffmpeg. Neither is a dependency of this project --
this script uses whichever is installed and explains the options when neither is.
Nothing else in the codebase imports them, so `make install` stays small.

The output is the JSON word-timing format `rhymemap.timing` reads. You can also write
that file by hand, or export Audacity labels, if you would rather not install an
aligner at all: the viewer only needs start and end times per word.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

INSTRUCTIONS = """
No forced aligner is available. Pick one:

  WhisperX (accurate, large download -- pulls in torch)
      pip install whisperx
      python -m scripts.align_audio --audio track.mp3 --lyrics verse.txt -o timings.json

  aeneas (lighter, needs system packages)
      apt-get install espeak ffmpeg && pip install aeneas

  By hand (no install at all)
      Open the audio in Audacity, add a label per word (Ctrl+B), then
      File > Export > Export Labels. Pass the .txt to --timings; the viewer
      reads Audacity label tracks directly.

The timing format is plain JSON, so anything that can emit one object per word
works:

  [{"word": "palms", "start": 0.51, "end": 0.78}, ...]
"""


def align_with_whisperx(audio: Path, lyrics: str, language: str) -> list[dict]:
    import whisperx

    device = "cpu"
    model = whisperx.load_model("base", device, compute_type="int8")
    result = model.transcribe(str(audio))
    aligner, metadata = whisperx.load_align_model(language_code=language, device=device)
    aligned = whisperx.align(result["segments"], aligner, metadata, str(audio), device)

    return [
        {"word": w["word"], "start": float(w["start"]), "end": float(w["end"])}
        for segment in aligned.get("segments", [])
        for w in segment.get("words", [])
        if w.get("start") is not None and w.get("end") is not None
    ]


def align_with_aeneas(audio: Path, lyrics_path: Path) -> list[dict]:
    from aeneas.executetask import ExecuteTask
    from aeneas.task import Task

    task = Task(config_string="task_language=eng|is_text_type=plain|os_task_file_format=json")
    task.audio_file_path_absolute = str(audio.resolve())
    task.text_file_path_absolute = str(lyrics_path.resolve())
    ExecuteTask(task).execute()

    return [
        {"word": fragment.text, "start": float(fragment.begin), "end": float(fragment.end)}
        for fragment in task.sync_map_leaves()
        if fragment.text and fragment.text.strip()
    ]


def available() -> list[str]:
    found = []
    for name in ("whisperx", "aeneas"):
        try:
            __import__(name)
            found.append(name)
        except Exception:
            pass
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--audio", type=Path, required=True, help="audio file to align against")
    parser.add_argument("--lyrics", type=Path, required=True, help="lyrics text file, one line per line")
    parser.add_argument("--output", "-o", type=Path, default=Path("timings.json"))
    parser.add_argument("--language", default="en")
    parser.add_argument("--backend", choices=("auto", "whisperx", "aeneas"), default="auto")
    args = parser.parse_args(argv)

    if not args.audio.exists():
        print(f"error: audio file not found: {args.audio}", file=sys.stderr)
        return 1
    if not args.lyrics.exists():
        print(f"error: lyrics file not found: {args.lyrics}", file=sys.stderr)
        return 1

    backends = available()
    chosen = args.backend if args.backend != "auto" else (backends[0] if backends else None)
    if chosen is None:
        print(INSTRUCTIONS)
        return 1
    if chosen not in backends:
        print(f"error: {chosen} is not installed.\n{INSTRUCTIONS}", file=sys.stderr)
        return 1

    print(f"aligning {args.audio.name} with {chosen} (this can take a while)")
    try:
        if chosen == "whisperx":
            timings = align_with_whisperx(args.audio, args.lyrics.read_text(encoding="utf-8"), args.language)
        else:
            timings = align_with_aeneas(args.audio, args.lyrics)
    except Exception as exc:
        print(f"error: alignment failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if not timings:
        print("error: the aligner produced no word timings", file=sys.stderr)
        return 1

    args.output.write_text(json.dumps(timings, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output} ({len(timings)} words, {timings[-1]['end']:.1f}s)")
    print(f"Use it with:  python -m rhymemap.webexport --timings {args.output} --audio {args.audio.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
