from __future__ import annotations

import argparse
import json
import pickle
import re
import sys
import io
from pathlib import Path

import numpy as np
from sklearn.preprocessing import normalize

# 修复 Windows 编码问题
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors='replace')


COMPLAINT_SPLIT_RE = re.compile(
    r"[，,、；;。\.\n\r]+|(?:同时)?(?:伴有|合并)|以及|还有|并且|且|和"
)

QUERY_EXPANSIONS = [
    (
        ("眼睛干燥", "眼睛干", "眼干", "干眼", "眼涩", "眼睛涩", "视疲劳", "眼疲劳"),
        "护肝明目 缓解眼疲劳 眼疲劳 明目",
    ),
]


def load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def split_complaints(query: str) -> list[str]:
    parts = [part.strip() for part in COMPLAINT_SPLIT_RE.split(query)]
    complaints = []
    seen = set()
    for part in parts:
        if not part or part in seen:
            continue
        seen.add(part)
        complaints.append(part)
    return complaints or [query.strip()]


def expand_query(query: str) -> str:
    expansions = []
    for triggers, expansion in QUERY_EXPANSIONS:
        if any(trigger in query for trigger in triggers):
            expansions.append(expansion)
    if not expansions:
        return query
    return " ".join([query, *expansions])


def recommendation_key(doc: dict) -> str:
    metadata = doc.get("metadata", {})
    tea_name = metadata.get("tea_name")
    if tea_name:
        return f"tea:{tea_name}"
    recommended_teas = metadata.get("recommended_teas")
    if isinstance(recommended_teas, list) and recommended_teas:
        return "teas:" + "、".join(str(tea) for tea in recommended_teas)
    return f"id:{doc.get('id')}"


def dedupe_results(results: list[tuple[float, dict]], top_k: int, min_score: float) -> list[tuple[float, dict]]:
    deduped = []
    seen = set()
    for score, doc in results:
        if score < min_score:
            continue
        key = recommendation_key(doc)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((score, doc))
        if len(deduped) >= top_k:
            break
    return deduped


def search_tfidf(store_dir: Path, query: str, top_k: int) -> list[tuple[float, dict]]:
    docs = load_jsonl(store_dir / "docs.jsonl")
    with (store_dir / "vectorizer.pkl").open("rb") as f:
        vectorizer = pickle.load(f)
    with (store_dir / "index.pkl").open("rb") as f:
        index = pickle.load(f)

    query_vector = vectorizer.transform([query])
    query_vector = normalize(query_vector, norm="l2", copy=False)
    distances, indices = index.kneighbors(query_vector, n_neighbors=min(top_k, len(docs)))
    return [(1 - float(distance), docs[int(i)]) for distance, i in zip(distances[0], indices[0])]


def search_sentence_transformers(store_dir: Path, query: str, top_k: int, model_name: str) -> list[tuple[float, dict]]:
    from sentence_transformers import SentenceTransformer

    docs = load_jsonl(store_dir / "docs.jsonl")
    embeddings = np.load(store_dir / "embeddings.npy")
    with (store_dir / "index.pkl").open("rb") as f:
        index = pickle.load(f)

    model = SentenceTransformer(model_name)
    query_embedding = model.encode([query], normalize_embeddings=True)
    query_embedding = np.asarray(query_embedding, dtype=np.float32)
    distances, indices = index.kneighbors(query_embedding, n_neighbors=min(top_k, len(docs)))
    return [(1 - float(distance), docs[int(i)]) for distance, i in zip(distances[0], indices[0])]


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the local tea RAG vector store.")
    parser.add_argument("query", help="Customer complaint or query text.")
    parser.add_argument("--store-dir", type=Path, default=Path("vector_store/tea_rag"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.15, help="Minimum score to print a result.")
    parser.add_argument(
        "--no-split",
        action="store_true",
        help="Search the full query as one complaint instead of splitting multiple complaints.",
    )
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--pretty", action="store_true", help="Output JSON format (ignored, for compatibility)")
    args = parser.parse_args()

    manifest = json.loads((args.store_dir / "manifest.json").read_text(encoding="utf-8"))
    complaints = [args.query.strip()] if args.no_split else split_complaints(args.query)

    for complaint_idx, complaint in enumerate(complaints, start=1):
        expanded_query = expand_query(complaint)
        fetch_k = max(args.top_k * 5, args.top_k)

        if manifest["backend"] == "tfidf_char":
            results = search_tfidf(args.store_dir, expanded_query, fetch_k)
        elif manifest["backend"] == "sentence_transformers":
            results = search_sentence_transformers(
                args.store_dir,
                expanded_query,
                fetch_k,
                manifest.get("model", args.model),
            )
        else:
            raise ValueError(f"Unsupported backend: {manifest['backend']}")

        results = dedupe_results(results, args.top_k, args.min_score)
        print(f"\n== 诉求 {complaint_idx}: {complaint} ==")
        if expanded_query != complaint:
            print(f"expanded_query={expanded_query}")
        if not results:
            print("未找到有效匹配。")
            continue

        for rank, (score, doc) in enumerate(results, start=1):
            metadata = doc.get("metadata", {})
            tea_display = metadata.get("tea_name") or "、".join(metadata.get("recommended_teas", []) or [])
            print(f"\n#{rank} score={score:.4f} id={doc.get('id')}")
            print(f"tea={tea_display} type={metadata.get('doc_type', '')}")
            print(doc.get("content", "")[:500])


if __name__ == "__main__":
    main()