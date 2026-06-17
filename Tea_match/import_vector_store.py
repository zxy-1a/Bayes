from __future__ import annotations

import argparse
import json
import pickle
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import normalize


def load_docs(path: Path) -> list[dict]:
    docs = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    if not docs:
        raise ValueError(f"No documents found in {path}")
    return docs


def doc_text(doc: dict) -> str:
    metadata = doc.get("metadata", {})
    fields = [
        doc.get("content", ""),
        metadata.get("tea_name", ""),
        metadata.get("symptom", ""),
        " ".join(metadata.get("symptom_terms", []) or []),
        metadata.get("constitution", ""),
        metadata.get("organ", ""),
    ]
    return "\n".join(str(x) for x in fields if x)


def build_tfidf_store(docs: list[dict], out_dir: Path) -> dict:
    texts = [doc_text(doc) for doc in docs]
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    matrix = normalize(matrix, norm="l2", copy=False)

    index = NearestNeighbors(metric="cosine", algorithm="brute")
    index.fit(matrix)

    with (out_dir / "vectorizer.pkl").open("wb") as f:
        pickle.dump(vectorizer, f)
    with (out_dir / "matrix.pkl").open("wb") as f:
        pickle.dump(matrix, f)
    with (out_dir / "index.pkl").open("wb") as f:
        pickle.dump(index, f)

    return {
        "backend": "tfidf_char",
        "embedding_dim": int(matrix.shape[1]),
        "note": "Local lexical vector index. Good for pipeline testing; use sentence-transformers/Qdrant for production semantic search.",
    }


def build_sentence_transformers_store(docs: list[dict], out_dir: Path, model_name: str) -> dict:
    from sentence_transformers import SentenceTransformer

    texts = [doc_text(doc) for doc in docs]
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        texts,
        batch_size=32,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    index = NearestNeighbors(metric="cosine", algorithm="brute")
    index.fit(embeddings)

    np.save(out_dir / "embeddings.npy", embeddings)
    with (out_dir / "index.pkl").open("wb") as f:
        pickle.dump(index, f)

    return {
        "backend": "sentence_transformers",
        "model": model_name,
        "embedding_dim": int(embeddings.shape[1]),
        "note": "Local dense vector index built from a sentence-transformers embedding model.",
    }


def write_docs(out_dir: Path, docs: list[dict]) -> None:
    with (out_dir / "docs.jsonl").open("w", encoding="utf-8") as f:
        for doc in docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a local vector store from tea RAG documents.")
    parser.add_argument("--input", type=Path, default=Path("rag_output/tea_rag_documents.jsonl"))
    parser.add_argument("--out-dir", type=Path, default=Path("vector_store/tea_rag"))
    parser.add_argument(
        "--backend",
        choices=["tfidf", "sentence-transformers"],
        default="tfidf",
        help="Use tfidf for an install-free local index, or sentence-transformers for dense semantic embeddings.",
    )
    parser.add_argument(
        "--model",
        default="BAAI/bge-small-zh-v1.5",
        help="sentence-transformers model name or local model path.",
    )
    args = parser.parse_args()

    docs = load_docs(args.input)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_docs(args.out_dir, docs)

    if args.backend == "tfidf":
        manifest = build_tfidf_store(docs, args.out_dir)
    else:
        manifest = build_sentence_transformers_store(docs, args.out_dir, args.model)

    manifest.update(
        {
            "source": str(args.input),
            "doc_count": len(docs),
            "store_dir": str(args.out_dir),
        }
    )
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
