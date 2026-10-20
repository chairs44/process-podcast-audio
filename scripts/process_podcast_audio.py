#!/usr/bin/env python3
"""Local podcast delivery export. Python 3.9+, ffmpeg and ffprobe required."""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
import unicodedata

EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".mp3", ".m4a", ".aac", ".ogg"}


def run(args, duration=None, stage=None):
    if duration is not None:
        return run_progress(args, duration, stage)
    p = subprocess.run(args, capture_output=True, text=True)
    if p.returncode:
        raise ValueError(p.stderr[-2500:])
    return p.stdout, p.stderr


def clock_text(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60}m {seconds % 60:02d}s"


def run_progress(args, duration, stage):
    """Read FFmpeg progress separately from its measurement/error log."""
    started = time.monotonic()
    last_print = -10
    position = 0.0
    print(f"  {stage} | 0% | estimating stage time...", flush=True)
    with tempfile.TemporaryFile(mode="w+t") as log:
        command = [args[0], "-nostats", "-progress", "pipe:1", *args[1:]]
        with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=log, text=True) as p:
            try:
                for line in p.stdout:
                    key, _, value = line.strip().partition("=")
                    if key == "out_time_us":
                        try:
                            position = max(position, float(value) / 1_000_000)
                        except ValueError:
                            pass
                    if key != "progress":
                        continue
                    elapsed = time.monotonic() - started
                    if elapsed - last_print < 10:
                        continue
                    fraction = min(0.99, max(0, position / duration))
                    percent = int(fraction * 100)
                    filled = percent // 5
                    eta = (f"~{clock_text(elapsed * (1 - fraction) / fraction)} remaining"
                           if fraction > 0.01 and elapsed >= 3 else "estimating")
                    print(f"  {stage} [{'#' * filled}{'.' * (20 - filled)}] "
                          f"{percent}% | elapsed {clock_text(elapsed)} | {eta}", flush=True)
                    last_print = elapsed
                code = p.wait()
            except BaseException:
                p.terminate()
                try:
                    p.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    p.kill()
                    p.wait()
                raise
        log.seek(0)
        stderr = log.read()
    if code:
        raise ValueError(stderr[-2500:])
    print(f"  {stage} | 100% | elapsed {clock_text(time.monotonic() - started)}", flush=True)
    return "", stderr


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_streams",
                           "-show_format", "-of", "json", str(path)])[0])


def audio(info):
    streams = [s for s in info["streams"] if s["codec_type"] == "audio"]
    if len(streams) != 1 or streams[0]["channels"] not in (1, 2):
        raise ValueError("Requires exactly one mono or stereo audio stream.")
    return streams[0]


def measure(path, duration=None, stage=None):
    # Duplicate mono explicitly so measurement matches the stereo deliverable.
    prefix = "aformat=channel_layouts=stereo,"
    _, log = run(["ffmpeg", "-hide_banner", "-nostdin", "-v", "info", "-i", str(path),
                  "-map", "0:a:0", "-af", prefix + "loudnorm=I=-16:TP=-2:LRA=50:print_format=json",
                  "-f", "null", "-"], duration, stage)
    matches = re.findall(r'\{\s*"input_i".*?\}', log, re.S)
    if not matches:
        raise ValueError("Missing loudness measurement.")
    result = json.loads(matches[-1])
    for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
        if not math.isfinite(float(result[key])):
            raise ValueError("Silence or unmeasurable loudness; export refused.")
    return result


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def slug(name):
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "audio"


def process(source, destination):
    if destination.exists() or source.resolve() == destination.resolve():
        raise FileExistsError(f"Refusing to overwrite: {destination}")
    before_hash = digest(source)
    info = probe(source)
    source_stream = audio(info)
    duration = float(info["format"]["duration"])
    if duration < 3:
        raise ValueError("Files shorter than 3 seconds require manual loudness review.")
    print("  Measuring complete source...", flush=True)
    measured = measure(source, duration, "1/3 Measuring")
    history = []
    with tempfile.TemporaryDirectory(prefix=".podcast-", dir=destination.parent) as temp:
        candidate = Path(temp) / "candidate.mp3"
        for attempt in range(3):
            print(f"  Rendering and verifying MP3, attempt {attempt + 1}...", flush=True)
            ceiling = -2.0 - attempt
            filt = (
                "aformat=channel_layouts=stereo,"
                f"loudnorm=I=-16:TP={ceiling}:LRA=50:linear=true:"
                f"measured_I={measured['input_i']}:measured_TP={measured['input_tp']}:"
                f"measured_LRA={measured['input_lra']}:"
                f"measured_thresh={measured['input_thresh']}:"
                f"offset={measured['target_offset']}:print_format=json"
            )
            # Always render from the source, never from a previous MP3 attempt.
            _, log = run(["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(source),
                          "-map", "0:a:0", "-map_metadata", "-1", "-map_chapters", "-1",
                          "-af", filt, "-ar", "44100", "-ac", "2",
                          "-c:a", "libmp3lame", "-b:a", "128k",
                          "-id3v2_version", "3", str(candidate)],
                         duration, f"2/3 Encoding (attempt {attempt + 1})")
            render = json.loads(re.findall(r'\{\s*"input_i".*?\}', log, re.S)[-1])
            final = measure(candidate, duration, f"3/3 Verifying (attempt {attempt + 1})")
            output_info = probe(candidate)
            stream = audio(output_info)
            valid_format = (stream["codec_name"] == "mp3"
                            and int(stream["sample_rate"]) == 44100
                            and stream["channels"] == 2
                            and int(stream["bit_rate"]) == 128000)
            if not valid_format or abs(float(output_info["format"]["duration"]) - duration) > 0.15:
                raise ValueError("Format or duration validation failed.")
            history.append({"ceiling": ceiling, "mode": render["normalization_type"],
                            "lufs": float(final["input_i"]), "true_peak": float(final["input_tp"])})
            if abs(float(final["input_i"]) + 16) <= 1 and float(final["input_tp"]) <= -1:
                if digest(source) != before_hash:
                    raise ValueError("Source changed during processing; export refused.")
                # Atomic no-clobber publication on the same filesystem.
                os.link(candidate, destination)
                warnings = []
                if source_stream["codec_name"] in ("mp3", "aac", "vorbis", "opus"):
                    warnings.append("Lossy input: this is another lossy generation; prefer a WAV premaster.")
                if float(measured["input_tp"]) >= 0:
                    warnings.append("Source reaches/exceeds 0 dBTP; this tool cannot repair existing distortion.")
                if render["normalization_type"] == "dynamic":
                    warnings.append("Dynamic normalization was required; listen for changed dynamics.")
                return {"source": str(source), "output": str(destination), "status": "passed",
                        "source_sha256": before_hash, "input": measured, "output_measurement": final,
                        "attempts": history, "duration_seconds": duration,
                        "warnings": warnings,
                        "listening": "Not performed; numerical QC only."}
        raise ValueError("Encoded audio failed loudness/peak QC; no output published. " + str(history))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("inputs", nargs="+", type=Path, help="Files or folders (folders scanned recursively)")
    parser.add_argument("--output", required=True, type=Path, help="New export folder, outside input folders")
    parser.add_argument("--no-report", action="store_true", help="Disable JSON and CSV reports")
    args = parser.parse_args()
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            parser.error(f"{tool} missing. Install FFmpeg first (macOS: brew install ffmpeg).")
    output = args.output.expanduser().resolve()
    sources = set()
    for item in args.inputs:
        item = item.expanduser().resolve()
        if not item.exists():
            parser.error(f"Missing input: {item}")
        if item.is_dir():
            if output == item or item in output.parents:
                parser.error("Output must be outside input folders to prevent reprocessing.")
            sources.update(p.resolve() for p in item.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)
        else:
            sources.add(item)
    if not sources:
        parser.error("No audio files found.")
    targets = [output / (slug(p.stem) + ".mp3") for p in sorted(sources)]
    if len(set(targets)) != len(targets):
        parser.error("Input names collide after kebab-case conversion. Run separately.")
    if any(p.exists() for p in targets):
        parser.error("Output already exists. Choose a different destination; files are never overwritten.")
    output.mkdir(parents=True, exist_ok=True)
    records = []
    started = time.monotonic()
    for index, (source, target) in enumerate(zip(sorted(sources), targets), 1):
        print(f"File {index}/{len(sources)}: {source.name}", flush=True)
        try:
            record = process(source, target)
            last = record["attempts"][-1]
            print(f"PASS: {last['lufs']} LUFS, {last['true_peak']} dBTP ({last['mode']})", flush=True)
        except (ValueError, OSError) as exc:
            record = {"source": str(source), "status": "failed", "error": str(exc)}
            print(f"FAIL: {exc}", flush=True)
        records.append(record)
    if not args.no_report:
        # Unique report directory keeps previous batch reports intact.
        report_dir = Path(tempfile.mkdtemp(prefix="report-", dir=output))
        (report_dir / "qc.json").write_text(json.dumps(records, indent=2) + "\n")
        with (report_dir / "qc.csv").open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["source", "status", "output", "LUFS", "dBTP", "mode", "error"])
            for r in records:
                last = r.get("attempts", [{}])[-1]
                writer.writerow([r["source"], r["status"], r.get("output"), last.get("lufs"),
                                 last.get("true_peak"), last.get("mode"), r.get("error")])
        print(f"Reports: {report_dir}", flush=True)
    passed = sum(r["status"] == "passed" for r in records)
    print(f"Finished: {passed} passed, {len(records) - passed} failed. "
          f"Total elapsed: {clock_text(time.monotonic() - started)}", flush=True)
    return 0 if passed == len(records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
