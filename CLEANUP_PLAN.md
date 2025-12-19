# Project Cleanup Plan

The root directory is currently cluttered with 60+ items. This plan proposes organizing them into a cleaner structure.

## 1. New Directory Structure

We will create/use these folders:
- `scripts/debug/`: For all `debug_*.py` scripts.
- `tests/`: For all `test_*.py` scripts (currently in root).
- `data/raw/`: For raw input files (Excel, Parquet, PDFs, CSV folders).
- `docs/setup/`: For setup guides (`GPU_SETUP.md`, `FIX_TORCH_DLL.md`, etc.).
- `legacy/`: For old backups and demos (`RNN_Demo`, `backup_pre_migration`).

## 2. Moves

### 📂 Scripts & Tests
| File | Destination |
|------|-------------|
| `debug_*.py` | `scripts/debug/` |
| `test_*.py` | `tests/` |
| `download_bge.py` | `scripts/` |
| `diagnose_gpu.ps1`, `install_gpu.ps1` | `scripts/windows/` |
| `suppress_warnings.py` | `backend/utils/` (or `scripts/`) |

### 📄 Documentation
| File | Destination |
|------|-------------|
| `GPU_SETUP.md`, `FIX_TORCH_DLL.md` | `docs/setup/` |
| `BRANDED_FOODS_GUIDE.md`, `DATASET_STATUS.md` | `docs/data/` |
| `GITHUB_PAGES_DEPLOYMENT.md` | `docs/dev/` |
| `NUTRI_DOCUMENTARY_DETAILED.md`, `info.md` | `docs/archive/` |

### 💾 Data
| File | Destination |
|------|-------------|
| `composition-data.xlsx` | `data/raw/` |
| `FartDB.parquet` | `data/raw/` |
| `herbal-pdrsmall.pdf` | `data/pdfs/` |
| `FoodData Central – *` | `data/raw/` |
| `DSSTox/`, `FoodDB/` | `data/raw/` |
| `processed/` | `data/processed/` |

### 🗑️ Legacy / Backups
| File | Destination |
|------|-------------|
| `RNN_Demo/` | `legacy/` |
| `backup_pre_migration/` | `legacy/` |
| `requirements-nutri.txt`, `requirements-rag.txt` | `legacy/` (if `requirements.txt` is master) |

## 3. Root Keepers
These will remain in the root:
- `api.py` (Entry point)
- `config.py` (Configuration)
- `llm.py` (Core module - consider moving to `backend/`)
- `rag_engine.py` (Core module - consider moving to `backend/`)
- `README.md`
- `DEVELOPMENT.md`
- `requirements.txt`
- `mkdocs.yml`
- `.gitignore`
- `start_server.sh` / `start_server.bat`

## 4. Action Plan
1.  Create necessary directories.
2.  Move files group by group.
3.  **Crucial**: Update imports in `api.py` and other scripts if we move core python files (`llm.py`, `rag_engine.py`). *For now, I recommend keeping core python files in root or moving them to `backend/` carefully.*
4.  Update `config.py` paths if data moves to `data/raw/`.

Shall we proceed with this cleanup?
