# AI-Powered Restaurant Recommendation System

This repo follows the phase-wise architecture in `docs/phase-wise-architecture.md`.

## Run (Phase 1–2 CLI)

### Prereqs
- Python 3.10+

#### Windows note (fix for “Python was not found”)
If PowerShell says **“Python was not found; run without arguments to install from the Microsoft Store …”**:
- Install Python 3.10+ (from `python.org`) and make sure **“Add python.exe to PATH”** is checked.
- Disable the Microsoft Store alias:
  - Settings → Apps → Advanced app settings → App execution aliases
  - Turn off `python.exe` and `python3.exe`

### Install deps (recommended)

```bash
python -m pip install -e .
```

### Run (Windows PowerShell helper)

```powershell
.\scripts\run.ps1 ingest
.\scripts\run.ps1 recommend --location Bangalore --budget-max-inr 1500 --cuisines "Italian,Chinese" --min-rating 3.5
```

### Run (no install)

```bash
python -m restaurant_rec ingest
python -m restaurant_rec recommend --location Bangalore --budget-max-inr 1500 --cuisines "Italian,Chinese" --min-rating 3.5
```
