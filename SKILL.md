---
name: process-podcast-audio
description: Prepare finished podcast mixes for MP3 distribution using local FFmpeg loudness normalization and encoded-file QC. Use for final episode delivery, batch podcast exports or loudness matching, not raw dialogue restoration or web sound effects.
---

# Process Podcast Audio

Create delivery derivatives without altering originals. Resolve script paths relative to this skill directory.

## Delivery standard

- Stereo MP3, 44.1 kHz, 128 kbps CBR.
- Target −16 LUFS integrated, acceptance ±1 LU; decoded MP3 true peak ≤−1 dBTP.
- Begin at −2 dBTP processing headroom. At most three renders, each from the source.
- Measure full files before and after encoding. Report whether normalization was linear or dynamic.

## Workflow

1. Confirm Python 3.9+, FFmpeg with libmp3lame/loudnorm, and ffprobe are installed.
2. Resolve input files or folders and an explicit output directory outside input folders.
3. Run `python3 scripts/process_podcast_audio.py --output OUTPUT INPUT...`.
4. Read the generated `report-*/qc.json` and CSV, then report passed/failed counts and output paths. Do not claim listening approval from numerical checks.

## Guardrails

- Prefer completed lossless mixes. Lossy input incurs another lossy generation.
- Never overwrite, move or rename originals. Existing outputs and kebab-case name collisions are refused.
- Mono is duplicated to stereo before measurement. More than two channels or multiple audio streams are refused.
- Failed QC candidates are not retained as deliverables. Successful files from a partial batch remain.
- Do not force a narrow loudness range, add EQ/denoise or process raw dialogue as if it were a finished episode.
- Source metadata, artwork and chapters are stripped for privacy. Add approved episode metadata separately.
- Reports contain local paths and hashes. Keep them private unless explicitly approved for sharing.
- Leave reports enabled unless the user requests `--no-report`. Never disable encoded audio checks.
- Require listening review for dynamics, distortion and transitions; normalization cannot repair existing clipping.
