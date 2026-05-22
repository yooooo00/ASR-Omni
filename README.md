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
- `run_qwen3_asr_prototype.ps1`
- `README.md`
- `LICENSE`

Do not commit these local artifacts:

- `.conda/`
- `.conda-qwen3-asr/`
- `models/`
- `vendor/`

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

## Quick Checks

List microphone devices:

```powershell
.\run_qwen3_asr_prototype.ps1 --list-devices
```

Run an offline ASR smoke test without microphone or hotkey:

```powershell
.\run_qwen3_asr_prototype.ps1 --test-audio .\samples\test_zh.wav --language Chinese
```

If you do not have the sample audio, pass any local wav file instead.

## Run Voice Input

```powershell
.\run_qwen3_asr_prototype.ps1 --language Chinese
```

Default hotkey is `alt+h`. Press it once to start recording and once again to stop.
Recognized segments are pasted into the current cursor location.

Useful options:

```powershell
.\run_qwen3_asr_prototype.ps1 --hotkey "ctrl+alt+h" --language Chinese --no-paste
.\run_qwen3_asr_prototype.ps1 --input-device 1 --language Chinese
.\run_qwen3_asr_prototype.ps1 --silence-threshold 0.02 --silence-seconds 0.7
```

`--no-paste` is useful when testing recognition without touching the active window.

## Open Source Notes

The application source is MIT licensed. Third-party packages and the Qwen model
keep their own licenses. The repository does not redistribute model weights.
