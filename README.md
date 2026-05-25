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
recording and once again to stop. While you speak, the app prints preview lines
in the terminal. After it detects silence, the completed segment is
automatically pasted into the current cursor location. Recording stays active
after each automatic paste until you press one of the hotkeys again.

## Manual Hotkey Configuration

For a local per-machine hotkey, copy the example settings file:

```powershell
Copy-Item .\settings.example.json .\settings.json
```

Then edit `settings.json`:

```json
{
  "hotkeys": ["ctrl+h", "alt+h"]
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
.\run_qwen3_asr_prototype.ps1 --input-device 1
.\run_qwen3_asr_prototype.ps1 --silence-threshold 0.02 --silence-seconds 2.0 --max-segment-seconds 30
.\run_qwen3_asr_prototype.ps1 --preview-interval-seconds 0.8 --min-preview-seconds 1.0
.\run_qwen3_asr_prototype.ps1 --language auto --context "Mostly Chinese dictation with some English technical terms; preserve English words as English."
```

`--no-paste` is useful when testing recognition without touching the active window.

By default the launcher uses `--language auto` so Qwen can detect mixed Chinese
and English instead of forcing all output as Chinese. It also passes a short
mixed-language context prompt unless you provide your own `--context`.

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
