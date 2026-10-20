<div align="center">

# Process Podcast Audio

**A local-first finishing pass for podcast delivery.**

Match loudness. Check the encoded file. Keep your originals.

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square)](#requirements) [![FFmpeg](https://img.shields.io/badge/Audio-FFmpeg-487D43?style=flat-square)](#delivery-settings) [![MIT license](https://img.shields.io/badge/License-MIT-656565?style=flat-square)](LICENSE)

[Quick start](#quick-start) · [Raycast](#raycast-on-macos) · [Agent skill](#agent-skill) · [Changelog](CHANGELOG.md)

</div>

---

Prepare finished mixes for distribution with measured loudness normalization,
consistent MP3 exports and per-file quality checks. Run it from Terminal,
Raycast or a compatible coding agent. No accounts, uploads or API keys.

> [!IMPORTANT]
> A delivery tool, not automatic mastering. Finish your edit and mix first,
> keep the lossless master, and listen to the export before publishing.

## At a glance

- Accepts individual files, multiple files, or folders recursively.
- Reads WAV, AIFF, FLAC, MP3, M4A, AAC and OGG.
- Shows stage progress, elapsed time and estimated stage time remaining.
- Produces lowercase kebab-case filenames and optional CSV/JSON reports.
- Preserves originals and refuses to overwrite existing outputs.

## Delivery settings

| Setting | Default |
| :--- | :--- |
| Format | MP3 · 44.1 kHz · stereo · 128 kbps CBR |
| Integrated loudness | −16 LUFS target · ±1 LU acceptance |
| Processing headroom | Starts at −2 dBTP |
| Encoded true peak | Must be ≤−1 dBTP |
| Verification | Full-file loudness, peaks, format and duration |
| Metadata | Source tags, artwork and chapters removed |

**Measure → Normalize & encode → Verify → Save**

Only exports that pass the numerical checks are saved as deliverables.

## Quick start

### Requirements

- macOS or Linux
- Python 3.9 or newer, Bash
- FFmpeg with `loudnorm` and `libmp3lame`, plus FFprobe

No third-party Python packages, accounts or API keys are required.

On macOS with Homebrew:

```bash
brew install python ffmpeg
```

<details>
<summary>Ubuntu / Debian installation</summary>

```bash
sudo apt-get update
sudo apt-get install python3 ffmpeg
```

</details>

### Install

```bash
git clone https://github.com/chairs44/process-podcast-audio.git
cd process-podcast-audio
chmod +x process-podcast-audio.sh raycast/process-podcast-audio.sh
```

### Process a finished mix

```bash
./process-podcast-audio.sh --output "./podcast-exports" "./finished-mix.wav"
```

<details>
<summary>More examples: multiple files and folders</summary>

Process several files:

```bash
./process-podcast-audio.sh --output "./podcast-exports" "./episode-one.wav" "./episode-two.wav"
```

Process a folder recursively:

```bash
./process-podcast-audio.sh --output "./podcast-exports" "./finished-mixes"
```

</details>

Choose an output directory outside input folders. Existing outputs are never
overwritten. Output files with colliding kebab-case names are refused.

## Options

```text
--output DIR   Required destination folder
--no-report    Disable CSV and JSON reports, not audio QC
-h, --help     Show help
```

## Quality-control report

Each run creates a unique `report-*` directory with `qc.csv` and `qc.json`.
Reports include per-file status, loudness, peaks and normalization mode.
JSON also contains source hashes, input measurements and warnings.

- `passed`: encoded audio meets the loudness, true-peak, format and duration checks.
- `failed`: no deliverable is published for that input; the report explains why.

Exit status is zero only when every input passes. Successful outputs remain
available if other files fail. A full episode takes several minutes because it
is measured, rendered and measured again.

FFmpeg uses linear gain where feasible, otherwise dynamic normalization/limiting.
The tool does not force a narrow loudness range. Failed encoded checks trigger
up to two further renders with more peak headroom, always from the original.

## Raycast on macOS

1. Clone the repository and keep its folders together.
2. In Raycast, search **Add Script Directory** and select the `raycast` folder.
3. Run **Process Podcast Audio**, choose one or more audio files, then choose the destination.

No Finder selection is required. Cancel either dialog to stop without processing.
Keep the command running until it finishes. Folder batches and `--no-report`
are available through the command-line interface.

Progress is printed approximately every ten seconds for measuring, encoding and
verification, with elapsed time and an estimated time remaining for that stage.
Estimates exclude later stages and retries; they are not a guaranteed finish time.
Raycast uses successive text lines rather than an in-place graphical progress bar.
At completion, a macOS notification is requested and a separate dialog offers
**Reveal in Finder**. Notification delivery depends on system permissions.
The dialog dismisses itself after 60 seconds.

<details>
<summary>Example progress output (illustrative)</summary>

```text
File 1/3: episode-one.wav
  2/3 Encoding (attempt 1) [############........] 60% | elapsed 2m 00s | ~1m 20s remaining
```

The percentage and estimate apply to the current stage, not the whole batch.

</details>

## Scope

This is a delivery utility, not a complete mastering system. It does not perform
speaker balancing, EQ, restoration, silence trimming or creative compression.
Integrated loudness cannot guarantee consistent dialogue within a mix.

Use a lossless premaster where possible. Re-encoding MP3/AAC creates another lossy
generation. Mono becomes dual mono; multichannel or multiple-audio-stream inputs
are rejected. Silent or shorter-than-three-second files require manual review.

Listen to the full export, especially loud transitions, quiet speech and endings.
Numerical QC does not certify sound quality or repair existing clipping.
Add approved episode metadata/artwork separately before publishing.

Normalization may turn an already loud mix down. Passing QC means the file
meets the stated delivery checks, not that it sounds clearer or better than the
original. Waveform height alone is not a measure of perceived loudness.
Compare references at matched playback loudness before making tonal or dynamics
decisions. Dynamic normalization can change the level over time; check the
reported mode and audition the result.

### Known limitations and next steps

- If another process creates the destination file during processing, the final
  save refuses to overwrite it. That input is reported as failed and its temporary
  candidate is removed, even if audio QC passed. Use a separate output folder
  for each concurrent run. Retaining a validated candidate after a late filename
  collision is a planned improvement, not implemented behavior.
- A more transparent fixed-gain-first delivery path with only necessary peak
  control is under consideration. The current version still uses FFmpeg's
  conditional linear/dynamic `loudnorm` behavior and the same acceptance limits.
- Music/SFX preparation, reference-matched mastering, transcription, chapters
  and a standalone app are not implemented. Raw assets should not automatically
  receive the complete-episode loudness target.

The defaults follow [Apple Podcasts audio recommendations](https://podcasters.apple.com/support/893-audio-requirements),
not a universal rule for all destinations. See [FFmpeg loudnorm documentation](https://ffmpeg.org/ffmpeg-filters.html#loudnorm)
for the normalization behavior.

## Privacy

Processing is local. The tool does not upload recordings or use telemetry.
Source metadata and artwork are excluded from exports. This does not anonymize
the audio itself. Console output and reports contain filenames/local paths;
JSON includes hashes. Review them before sharing. No recordings or private
production reports are included in this repository.

## Agent skill

Install the included workflow for compatible coding agents:

```bash
npx skills add chairs44/process-podcast-audio --skill process-podcast-audio
```

The [skill](SKILL.md) defines delivery settings, source-preservation guardrails
and the QC workflow. The command-line tool works independently.

## Development

```bash
python3 -m unittest discover -s tests -v
bash -n process-podcast-audio.sh
bash -n raycast/process-podcast-audio.sh
```

Tests generate temporary audio rather than bundling recordings. The canonical
implementation lives in `scripts/`, shared by Terminal, Raycast and the skill.
macOS is locally tested; Linux uses the same CLI but is not claimed as fully verified.

| File | Purpose |
| :--- | :--- |
| [`scripts/process_podcast_audio.py`](scripts/process_podcast_audio.py) | Shared processing engine |
| [`process-podcast-audio.sh`](process-podcast-audio.sh) | Terminal entrypoint |
| [`raycast/`](raycast/) | macOS Script Command |
| [`SKILL.md`](SKILL.md) | Agent instructions |
| [`tests/`](tests/) | Tests using temporary synthetic audio |

---

Built by [David Sutrin](https://www.davidsutrin.xyz) · [MIT license](LICENSE)

Also available: [Process Web Audio](https://github.com/chairs44/process-web-audio),
for browser-ready audio delivery.
