from datetime import datetime
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "data" / "property_os.db"
if not source.exists():
    raise SystemExit("No database found yet. Start Property OS and create the workspace first.")
backup_dir = ROOT / "backups"
backup_dir.mkdir(exist_ok=True)
target = backup_dir / f"property_os_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
with sqlite3.connect(source) as src, sqlite3.connect(target) as dst:
    src.backup(dst)
print(f"Backup created: {target}")
