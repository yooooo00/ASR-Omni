# ASR Omni

Offline Windows voice input prototype using `Qwen3-ASR-0.6B` with CPU inference.

The source code can be published on GitHub. The model weights and local Python
environment are intentionally not committed; the setup script downloads them on
the target machine.

## What Gets Published

Commit these files:

- `asr_omni/`
- `tests/`
- `scripts/`
- `requirements.txt`
- `glossary.tsv`
- `settings.example.json`
- `run_qwen3_asr_prototype.ps1`
- `README.md`
- `LICENSE`

Do not commit these local artifacts:

- `.conda/`
- `.conda-qwen3-asr/`
- `models/`
- `vendor/`
- `settings.json`

`Qwen3-ASR-0.6B` is distributed separately by Qwen under its own license. This
project downloads it from ModelScope during setup.

## Setup On Another Windows PC

Prerequisites:

- Windows 10/11
- Miniconda or Anaconda available as `conda`
- Network access for the first model download

Then run:

```powershell
git clone <your-github-repo-url>
cd ASR-Omni
.\scripts\setup_windows.ps1
```

The model is downloaded to:

```text
models\Qwen3-ASR-0.6B
```

## Updating An Existing Checkout

If this project already exists on another PC:

```powershell
cd ASR-Omni
git pull --ff-only
.\scripts\setup_windows.ps1
```

The existing model directory and local Python environment are reused when
possible. Local `settings.json` is ignored by Git and will not be overwritten.

## Quick Checks

List microphone devices:

```powershell
.\run_qwen3_asr_prototype.ps1 --list-devices
```

Run an offline ASR smoke test without microphone or hotkey:

```powershell
.\run_qwen3_asr_prototype.ps1 --test-audio .\samples\test_zh.wav
```

If you do not have the sample audio, pass any local wav file instead.

## Run Voice Input

```powershell
.\run_qwen3_asr_prototype.ps1
```

Default hotkeys are `ctrl+h` and `alt+h`. Press either one once to start
recording and once again to stop. A small always-on-top control window is also
shown by default; click its button to toggle recording with the mouse. After
the app detects silence, the completed segment is automatically pasted into the
current cursor location. Recording stays active after each automatic paste
until you press one of the hotkeys or click the control button again.

## Manual Hotkey Configuration

For a local per-machine hotkey, copy the example settings file:

```powershell
Copy-Item .\settings.example.json .\settings.json
```

Then edit `settings.json`:

```json
{
  "hotkeys": ["ctrl+h", "alt+h"],
  "control_window": true,
  "preview": false,
  "clipboard_history": false
}
```

Examples:

```json
{ "hotkeys": ["alt+h"] }
{ "hotkeys": ["ctrl+h", "alt+h"] }
{ "hotkeys": ["ctrl+alt+h", "shift+h"] }
```

The old single-hotkey form still works:

```json
{ "hotkey": "alt+h" }
```

`settings.json` is ignored by Git, so pulling a newer version from GitHub will
not overwrite your local hotkey. A command-line `--hotkey` argument still has
priority over `settings.json`; pass it more than once to register multiple
hotkeys.

Useful options:

```powershell
.\run_qwen3_asr_prototype.ps1 --hotkey "ctrl+alt+h" --language Chinese --no-paste
.\run_qwen3_asr_prototype.ps1 --hotkey "ctrl+h" --hotkey "alt+h"
.\run_qwen3_asr_prototype.ps1 --no-control-window
.\run_qwen3_asr_prototype.ps1 --input-device 1
.\run_qwen3_asr_prototype.ps1 --silence-threshold 0.02 --silence-seconds 2.0 --max-segment-seconds 30
.\run_qwen3_asr_prototype.ps1 --preview --preview-interval-seconds 2.0 --min-preview-seconds 1.0
.\run_qwen3_asr_prototype.ps1 --clipboard-history
.\run_qwen3_asr_prototype.ps1 --language auto --context "Mostly Chinese dictation with some English technical terms; preserve English words as English."
```

`--no-paste` is useful when testing recognition without touching the active window.

By default the launcher uses `--language auto` so Qwen can detect mixed Chinese
and English instead of forcing all output as Chinese. It also passes a short
mixed-language context prompt unless you provide your own `--context`.

## Clipboard History

By default transcript paste uses the Windows clipboard plus `Ctrl+V`, but marks
the temporary clipboard content so Windows should not add it to Win+V clipboard
history or cloud clipboard sync. The app also restores the previous text
clipboard content with the same no-history marker after paste.

If you want the old behavior, allow clipboard history explicitly:

```powershell
.\run_qwen3_asr_prototype.ps1 --clipboard-history
```

Or in `settings.json`:

```json
{
  "clipboard_history": true
}
```

## Runtime Switches

Preview is disabled by default because it runs extra ASR passes while you are
still speaking. On memory-constrained machines this can cause high RAM pressure.
Enable it only when you need terminal preview text:

```powershell
.\run_qwen3_asr_prototype.ps1 --preview
```

Disable preview explicitly:

```powershell
.\run_qwen3_asr_prototype.ps1 --no-preview
```

Useful memory and latency controls:

```powershell
.\run_qwen3_asr_prototype.ps1 --max-segment-seconds 12
.\run_qwen3_asr_prototype.ps1 --torch-threads 4
.\run_qwen3_asr_prototype.ps1 --max-new-tokens 64
```

Switch summary:

- `--control-window` / `--no-control-window`: show or hide the always-on-top mouse toggle. Default: shown.
- `--preview` / `--no-preview`: enable or disable periodic preview recognition. Default: disabled.
- `--clipboard-history` / `--no-clipboard-history`: allow or suppress Win+V clipboard history entries. Default: suppressed on Windows.
- `--preview-interval-seconds`: preview cadence when preview is enabled. Larger values reduce CPU/RAM pressure.
- `--min-preview-seconds`: minimum buffered speech before a preview is attempted.
- `--silence-seconds`: silence duration before committing a segment to the active text field.
- `--max-segment-seconds`: hard upper bound for one segment. Smaller values reduce peak memory per ASR call.
- `--torch-threads`: CPU threads used by PyTorch. Lower values reduce system contention.
- `--max-new-tokens`: maximum generated output tokens. Lower values reduce generation work.
- `--monitor-interval`: resource monitor print interval.

The same options can be put in `settings.json`, for example:

```json
{
  "hotkeys": ["ctrl+h", "alt+h"],
  "control_window": true,
  "preview": false,
  "clipboard_history": false,
  "max_segment_seconds": 12,
  "torch_threads": 4,
  "max_new_tokens": 64
}
```

## Glossary Post-Processing

Final text and preview text are corrected with a glossary before display or
insertion. The default editable glossary is:

```text
glossary.tsv
```

Each line is:

```text
source<TAB>target
```

The initial entry is:

```text
cloud code	claude code
```

You can pass another glossary file:

```powershell
.\run_qwen3_asr_prototype.ps1 --glossary-file .\my-glossary.tsv
```

## Open Source Notes

The application source is MIT licensed. Third-party packages and the Qwen model
keep their own licenses. The repository does not redistribute model weights.
