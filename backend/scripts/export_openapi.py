"""Write the OpenAPI schema to openapi/openapi.json without starting a server.

The frontend generates its TypeScript types from this file, and CI regenerates it to
detect when the committed schema and the code have drifted apart.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.main import create_app

OUTPUT = Path(__file__).resolve().parents[2] / "openapi" / "openapi.json"


def main() -> None:
    schema = create_app().openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
