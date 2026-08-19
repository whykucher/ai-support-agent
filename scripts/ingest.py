"""Re-index the knowledge folder.

    python -m scripts.ingest              # index everything in knowledge/
    python -m scripts.ingest --no-embed   # keyword index only (no API calls)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db, rag  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Index the knowledge base")
    parser.add_argument("--no-embed", action="store_true",
                        help="skip embeddings, keyword search only")
    parser.add_argument("--dir", default=None, help="folder to index")
    args = parser.parse_args()

    db.init()
    target = Path(args.dir) if args.dir else config.KNOWLEDGE_DIR
    if not target.exists():
        print(f"! {target} does not exist")
        return 1

    result = rag.ingest_directory(target, embed=not args.no_embed)
    if not result:
        print(f"! no .md or .txt files found in {target}")
        return 1

    for name, count in result.items():
        print(f"  {name}: {count} chunks")
    stats = db.chunk_stats()
    print(f"\nindexed {stats['n']} chunks from {stats['sources']} file(s); "
          f"{stats['vectorised']} have embeddings "
          f"(provider={config.LLM_PROVIDER})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
