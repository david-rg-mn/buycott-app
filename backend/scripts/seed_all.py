import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from init_db import main as init_db
from seed_ontology import main as seed_ontology
from seed_businesses import main as seed_businesses


def main() -> None:
    init_db()
    seed_ontology()
    seed_businesses()


if __name__ == "__main__":
    main()
