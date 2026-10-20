#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title Process Podcast Audio
# @raycast.mode fullOutput

# Optional parameters:
# @raycast.packageName Audio Tools
# @raycast.description Choose audio files and export loudness-matched podcast MP3s locally.
# @raycast.author David Sutrin

set -euo pipefail
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:${PATH:-}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROCESSOR="$SCRIPT_DIR/../scripts/process_podcast_audio.py"
[[ -f "$SCRIPT_DIR/process_podcast_audio.py" ]] && PROCESSOR="$SCRIPT_DIR/process_podcast_audio.py"

if [[ ! -f "$PROCESSOR" ]]; then
  echo "Missing processor: $PROCESSOR"
  echo "Keep the repository's raycast and scripts folders together."
  exit 1
fi
for dependency in python3 ffmpeg ffprobe; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing dependency: $dependency"
    echo "Install Python 3 and FFmpeg before running this command."
    exit 1
  fi
done

# Dialogs avoid relying on Finder's selection or automation permission.
# The first line is the destination; subsequent lines are selected inputs.
selection="$(osascript <<'APPLESCRIPT'
try
    set pickedFiles to choose file with prompt "Choose finished audio mixes to process" with multiple selections allowed
    set destinationFolder to choose folder with prompt "Choose where podcast exports should be saved"
    set outputPath to POSIX path of destinationFolder
    if outputPath contains linefeed then error "Paths containing line breaks are not supported."
    set selectedPaths to outputPath
    repeat with pickedFile in pickedFiles
        set inputPath to POSIX path of pickedFile
        if inputPath contains linefeed then error "Paths containing line breaks are not supported."
        set selectedPaths to selectedPaths & linefeed & inputPath
    end repeat
    return selectedPaths
on error errorMessage number errorNumber
    if errorNumber is -128 then return ""
    error errorMessage number errorNumber
end try
APPLESCRIPT
)"

if [[ -z "$selection" ]]; then
  echo "Cancelled. No files processed."
  exit 0
fi

destination="${selection%%$'\n'*}"
inputs=()
while IFS= read -r input; do
  [[ -n "$input" ]] && inputs+=("$input")
done <<< "${selection#*$'\n'}"

echo "Podcast export: 44.1 kHz stereo MP3, 128 kbps, target -16 LUFS."
echo "Destination: $destination"
echo "Full episodes take several minutes. Keep this command running."
echo
status=0
python3 "$PROCESSOR" "${inputs[@]}" --output "$destination" || status=$?
if [[ "$status" -eq 0 ]]; then
  message="Audio processing complete. All files passed numerical QC."
else
  message="Processing ended with errors. Review the command output and reports."
fi
# Notification delivery depends on macOS permissions. A separate completion
# dialog provides the Finder action; Script Commands cannot add notification buttons.
osascript - "$destination" "$message" <<'APPLESCRIPT' || true
on run argv
    set destinationPath to item 1 of argv
    set resultMessage to item 2 of argv
    display notification resultMessage with title "Process Podcast Audio"
    set answer to display dialog resultMessage buttons {"Done", "Reveal in Finder"} default button "Done" with title "Process Podcast Audio" giving up after 60
    if not gave up of answer and button returned of answer is "Reveal in Finder" then
        do shell script "/usr/bin/open " & quoted form of destinationPath
    end if
end run
APPLESCRIPT
exit "$status"
