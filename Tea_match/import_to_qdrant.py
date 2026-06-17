from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from tea_match.config import MEMORY_DIR, PROJECT_ROOT
from tea_match.qdrant_store import COLLECTION_DEFINITIONS, get_qdrant_client, get_qdrant_settings


MULTI_VALUE_RE = re.compile(r"[|、，,+]+")
DEFAULT_MODEL = "BAAI/bge-small-zh-v1.5"


class EmbeddingModel:
    def __init__(self, model_name: str, batch_size: int = 64):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. Run `pip install sentence-transformers` first."
            ) from exc

        self.model_name = model_name
        self.batch_size = batch_size
        self.model = SentenceTransformer(model_name)
        probe = self.encode(["dimension probe"])
        self.vector_size = len(probe[0]) if probe else 0
        if self.vector_size <= 0:
            raise RuntimeError(f"Failed to infer embedding size from model: {model_name}")

    def encode(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=len(texts) > 128,
        )
        return [list(map(float, row)) for row in embeddings]


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def split_values(value: str | None) -> list[str]:
    text = str(value or "").strip()
    if not text:
        return []
    parts = [item.strip() for item in MULTI_VALUE_RE.split(text) if item.strip()]
    seen: set[str] = set()
    ordered: list[str] = []
    for item in parts:
        if item not in seen:
            ordered.append(item)
            seen.add(item)
    return ordered


def make_point_id(collection_key: str, unique_text: str) -> str:
    digest = hashlib.md5(unique_text.encode("utf-8")).hexdigest()
    return f"{collection_key}:{digest}"


def infer_category(term: str) -> str:
    text = str(term or "")
    if any(keyword in text for keyword in ["体质", "阴虚", "阳虚", "气虚", "湿热", "痰湿", "血瘀", "气郁"]):
        return "constitution"
    if any(keyword in text for keyword in ["肝", "心", "脾", "肺", "肾"]):
        return "organ"
    if any(keyword in text for keyword in ["高血压", "高血脂", "高血糖", "糖尿病", "鼻炎", "结节", "囊肿", "炎", "病"]):
        return "western_disease"
    return "symptom"


def append_record(records: list[dict[str, Any]], seen: set[tuple[Any, ...]], key: tuple[Any, ...], text: str, payload: dict[str, Any]) -> None:
    if key in seen:
        return
    seen.add(key)
    records.append({"id": make_point_id(payload["collection_key"], "|".join(map(str, key))), "text": text, "payload": payload})


def build_symptom_alias_records(rag_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()

    for row in read_csv_rows(rag_dir / "symptom_alias_dictionary.csv"):
        alias = str(row.get("alias") or "").strip()
        canonical = str(row.get("canonical") or "").strip()
        if not alias or not canonical:
            continue
        source = str(row.get("source") or "symptom_alias_dictionary").strip() or "symptom_alias_dictionary"
        confidence = float(row.get("confidence") or 1.0)
        category = infer_category(canonical)
        payload = {
            "collection_key": "symptom_aliases",
            "canonical_term": canonical,
            "alias": alias,
            "category": category,
            "step_hint": 1 if category == "symptom" else 0,
            "source": source,
            "confidence": confidence,
        }
        text = f"alias: {alias}\ncanonical_term: {canonical}\ncategory: {category}\nsource: {source}"
        append_record(records, seen, (alias, canonical, source), text, payload)

    for row in read_csv_rows(rag_dir / "western_disease_alias.csv"):
        alias = str(row.get("symptom") or "").strip()
        if not alias:
            continue
        canonical = alias
        payload = {
            "collection_key": "symptom_aliases",
            "canonical_term": canonical,
            "alias": alias,
            "category": str(row.get("category") or "western_disease").strip() or "western_disease",
            "step_hint": 1,
            "source": "western_disease_alias",
            "confidence": 0.95,
        }
        text = f"alias: {alias}\ncanonical_term: {canonical}\ncategory: western_disease\nsource: western_disease_alias"
        append_record(records, seen, (alias, canonical, "western_disease_alias"), text, payload)

    for row in read_csv_rows(rag_dir / "step2_oral_aliases.csv"):
        canonical = str(row.get("condition") or "").strip()
        aliases = split_values(row.get("aliases"))
        note = str(row.get("notes") or "").strip()
        if not canonical:
            continue
        for alias in aliases:
            payload = {
                "collection_key": "symptom_aliases",
                "canonical_term": canonical,
                "alias": alias,
                "category": infer_category(canonical),
                "step_hint": 2,
                "source": "step2_oral_aliases",
                "confidence": 0.9,
            }
            text = f"alias: {alias}\ncanonical_term: {canonical}\ncategory: {payload['category']}\nsource: step2_oral_aliases\nnotes: {note}"
            append_record(records, seen, (alias, canonical, "step2_oral_aliases"), text, payload)

    return records


def build_tea_knowledge_records(rag_dir: Path) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "functions": set(),
        "applicable_symptoms": set(),
        "applicable_constitutions": set(),
        "applicable_organs": set(),
        "priority": 9,
        "source": set(),
    })

    for row in read_csv_rows(rag_dir / "tea_symptom_index.csv"):
        tea_name = str(row.get("tea_name") or "").strip()
        if not tea_name:
            continue
        grouped[tea_name]["priority"] = min(grouped[tea_name]["priority"], 1)
        grouped[tea_name]["source"].add("tea_symptom_index")
        symptom = str(row.get("symptom") or "").strip()
        raw_symptom = str(row.get("raw_symptom") or "").strip()
        if symptom:
            grouped[tea_name]["applicable_symptoms"].add(symptom)
        if raw_symptom:
            grouped[tea_name]["functions"].update(split_values(raw_symptom))

    for row in read_csv_rows(rag_dir / "step2_combo_rules.csv"):
        for tea_name in split_values(row.get("recommended_teas")):
            grouped[tea_name]["priority"] = min(grouped[tea_name]["priority"], 2)
            grouped[tea_name]["source"].add("step2_combo_rules")
            grouped[tea_name]["applicable_symptoms"].update(split_values(row.get("primary_conditions")))
            grouped[tea_name]["applicable_symptoms"].update(split_values(row.get("trigger_condition")))
            grouped[tea_name]["functions"].update(split_values(row.get("raw_rule")))

    for row in read_csv_rows(rag_dir / "step3_constitution_fallback.csv"):
        tea_name = str(row.get("tea_name") or "").strip()
        constitution = str(row.get("fallback_condition") or "").strip()
        if tea_name:
            grouped[tea_name]["priority"] = min(grouped[tea_name]["priority"], 3)
            grouped[tea_name]["source"].add("step3_constitution_fallback")
            if constitution:
                grouped[tea_name]["applicable_constitutions"].add(constitution)

    for row in read_csv_rows(rag_dir / "step4_organ_fallback.csv"):
        tea_name = str(row.get("tea_name") or "").strip()
        organ = str(row.get("fallback_condition") or "").strip()
        if tea_name:
            grouped[tea_name]["priority"] = min(grouped[tea_name]["priority"], 4)
            grouped[tea_name]["source"].add("step4_organ_fallback")
            if organ:
                grouped[tea_name]["applicable_organs"].add(organ)

    records: list[dict[str, Any]] = []
    for tea_name, info in grouped.items():
        functions = sorted(info["functions"])
        symptoms = sorted(info["applicable_symptoms"])
        constitutions = sorted(info["applicable_constitutions"])
        organs = sorted(info["applicable_organs"])
        source = sorted(info["source"])
        payload = {
            "collection_key": "tea_knowledge",
            "tea_name": tea_name,
            "functions": functions,
            "applicable_symptoms": symptoms,
            "applicable_constitutions": constitutions,
            "applicable_organs": organs,
            "source": ",".join(source),
            "priority": int(info["priority"]),
        }
        text = (
            f"tea_name: {tea_name}\n"
            f"functions: {'、'.join(functions)}\n"
            f"applicable_symptoms: {'、'.join(symptoms)}\n"
            f"applicable_constitutions: {'、'.join(constitutions)}\n"
            f"applicable_organs: {'、'.join(organs)}"
        )
        records.append({
            "id": make_point_id("tea_knowledge", tea_name),
            "text": text,
            "payload": payload,
        })
    return records


def build_rule_chunk_records(rag_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in read_csv_rows(rag_dir / "tea_symptom_index.csv"):
        symptom = str(row.get("symptom") or "").strip()
        tea_name = str(row.get("tea_name") or "").strip()
        source_row = int(row.get("source_row") or 0)
        if not symptom or not tea_name:
            continue
        rule_id = f"step1::{source_row}::{symptom}::{tea_name}"
        payload = {
            "collection_key": "rule_chunks",
            "rule_id": rule_id,
            "step": 1,
            "rule_type": "direct",
            "condition_text": symptom,
            "trigger_terms": [symptom],
            "recommended_teas": [tea_name],
            "priority": 1,
            "source_excel_row": source_row,
        }
        text = f"step: 1\ncondition: {symptom}\nrecommended_teas: {tea_name}\nraw_symptom: {row.get('raw_symptom', '')}"
        records.append({"id": make_point_id("rule_chunks", rule_id), "text": text, "payload": payload})

    for row in read_csv_rows(rag_dir / "step2_combo_rules.csv"):
        rule_id = str(row.get("rule_id") or "").strip()
        if not rule_id:
            continue
        primary = str(row.get("primary_conditions") or "").strip()
        trigger = str(row.get("trigger_condition") or "").strip()
        recommended_teas = split_values(row.get("recommended_teas"))
        condition_text = primary if not trigger else f"{primary} + {trigger}"
        trigger_terms = split_values(primary) + split_values(trigger)
        payload = {
            "collection_key": "rule_chunks",
            "rule_id": rule_id,
            "step": 2,
            "rule_type": str(row.get("rule_type") or "combination").strip() or "combination",
            "condition_text": condition_text,
            "trigger_terms": trigger_terms,
            "recommended_teas": recommended_teas,
            "priority": int(row.get("priority") or 2),
            "source_excel_row": int(rule_id.split("::")[1].split(".")[0]) if "::" in rule_id else 0,
        }
        text = f"step: 2\ncondition: {condition_text}\nrecommended_teas: {'、'.join(recommended_teas)}\nraw_rule: {row.get('raw_rule', '')}"
        records.append({"id": make_point_id("rule_chunks", rule_id), "text": text, "payload": payload})

    for row in read_csv_rows(rag_dir / "step3_constitution_fallback.csv"):
        condition = str(row.get("fallback_condition") or "").strip()
        tea_name = str(row.get("tea_name") or "").strip()
        source_row = int(row.get("source_row") or 0)
        if not condition or not tea_name:
            continue
        rule_id = f"step3::{source_row}::{condition}::{tea_name}"
        payload = {
            "collection_key": "rule_chunks",
            "rule_id": rule_id,
            "step": 3,
            "rule_type": "constitution_fallback",
            "condition_text": condition,
            "trigger_terms": [condition],
            "recommended_teas": [tea_name],
            "priority": int(row.get("priority") or 3),
            "source_excel_row": source_row,
        }
        text = f"step: 3\ncondition: {condition}\nrecommended_teas: {tea_name}\napplies_when: {row.get('applies_when', '')}"
        records.append({"id": make_point_id("rule_chunks", rule_id), "text": text, "payload": payload})

    for row in read_csv_rows(rag_dir / "step4_organ_fallback.csv"):
        condition = str(row.get("fallback_condition") or "").strip()
        tea_name = str(row.get("tea_name") or "").strip()
        source_row = int(row.get("source_row") or 0)
        if not condition or not tea_name:
            continue
        rule_id = f"step4::{source_row}::{condition}::{tea_name}"
        payload = {
            "collection_key": "rule_chunks",
            "rule_id": rule_id,
            "step": 4,
            "rule_type": "organ_fallback",
            "condition_text": condition,
            "trigger_terms": [condition],
            "recommended_teas": [tea_name],
            "priority": int(row.get("priority") or 4),
            "source_excel_row": source_row,
        }
        text = f"step: 4\ncondition: {condition}\nrecommended_teas: {tea_name}\napplies_when: {row.get('applies_when', '')}"
        records.append({"id": make_point_id("rule_chunks", rule_id), "text": text, "payload": payload})

    return records


def build_case_memory_records(memory_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row in read_jsonl_rows(memory_dir / "recommendation_events.jsonl"):
        user_id = str(row.get("user_id") or "").strip()
        event_id = str(row.get("event_id") or "").strip()
        query_text = str(row.get("query") or "").strip()
        if not event_id or not query_text:
            continue
        recommended_teas = [str(item.get("name") or "").strip() for item in (row.get("top_recommendations") or []) if str(item.get("name") or "").strip()]
        normalized_terms = [str(item).strip() for item in ((row.get("semantic_normalization") or {}).get("canonical_terms") or []) if str(item).strip()]
        selected_buttons = [str(item).strip() for item in (row.get("selected_symptoms") or []) if str(item).strip()]
        payload = {
            "collection_key": "case_memory",
            "user_id": user_id,
            "query_text": query_text,
            "selected_buttons": selected_buttons,
            "normalized_terms": normalized_terms,
            "recommended_teas": recommended_teas,
            "feedback": "",
            "feedback_text": "",
            "created_at": str(row.get("created_at") or "").strip(),
            "session_id": event_id,
        }
        text = (
            f"query_text: {query_text}\n"
            f"normalized_terms: {'、'.join(normalized_terms)}\n"
            f"selected_buttons: {'、'.join(selected_buttons)}\n"
            f"recommended_teas: {'、'.join(recommended_teas)}"
        )
        records.append({"id": make_point_id("case_memory", event_id), "text": text, "payload": payload})

    for row in read_jsonl_rows(memory_dir / "feedback_events.jsonl"):
        event_id = str(row.get("event_id") or "").strip()
        tea_name = str(row.get("tea_name") or "").strip()
        if not event_id or not tea_name:
            continue
        feedback_text = " ".join(
            part for part in [
                str(row.get("notes") or "").strip(),
                str(row.get("adverse_reaction") or "").strip(),
            ]
            if part
        )
        payload = {
            "collection_key": "case_memory",
            "user_id": str(row.get("user_id") or "").strip(),
            "query_text": "",
            "selected_buttons": [],
            "normalized_terms": [],
            "recommended_teas": [tea_name],
            "feedback": str(row.get("effect") or "").strip(),
            "feedback_text": feedback_text,
            "created_at": str(row.get("created_at") or "").strip(),
            "session_id": event_id,
        }
        text = f"tea_name: {tea_name}\nfeedback: {payload['feedback']}\nfeedback_text: {feedback_text}"
        records.append({"id": make_point_id("case_memory", event_id), "text": text, "payload": payload})

    return records


def collection_exists(client: Any, collection_name: str) -> bool:
    try:
        return bool(client.collection_exists(collection_name))
    except Exception:
        response = client.get_collections()
        return any(item.name == collection_name for item in getattr(response, "collections", []))


def ensure_collection(client: Any, collection_name: str, vector_size: int, recreate: bool) -> None:
    from qdrant_client.models import Distance, VectorParams

    if recreate and collection_exists(client, collection_name):
        client.delete_collection(collection_name)

    if collection_exists(client, collection_name):
        return

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )


def upsert_records(client: Any, collection_name: str, records: list[dict[str, Any]], embedder: EmbeddingModel, batch_size: int, dry_run: bool) -> int:
    from qdrant_client.models import PointStruct

    if not records:
        return 0
    if dry_run:
        return len(records)

    count = 0
    for start in range(0, len(records), batch_size):
        batch = records[start : start + batch_size]
        vectors = embedder.encode([item["text"] for item in batch])
        points = [
            PointStruct(id=item["id"], vector=vector, payload={k: v for k, v in item["payload"].items() if k != "collection_key"})
            for item, vector in zip(batch, vectors, strict=False)
        ]
        client.upsert(collection_name=collection_name, wait=True, points=points)
        count += len(points)
    return count


def build_records_map(rag_dir: Path, include_memory: bool) -> dict[str, list[dict[str, Any]]]:
    records_map = {
        "symptom_aliases": build_symptom_alias_records(rag_dir),
        "tea_knowledge": build_tea_knowledge_records(rag_dir),
        "rule_chunks": build_rule_chunk_records(rag_dir),
        "case_memory": [],
    }
    if include_memory:
        records_map["case_memory"] = build_case_memory_records(MEMORY_DIR)
    return records_map


def main() -> None:
    parser = argparse.ArgumentParser(description="Import tea matching knowledge into Qdrant collections.")
    parser.add_argument("--rag-dir", type=Path, default=PROJECT_ROOT / "rag_output")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Sentence-transformers model name or local path.")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--collections", nargs="*", choices=list(COLLECTION_DEFINITIONS.keys()), default=list(COLLECTION_DEFINITIONS.keys()))
    parser.add_argument("--include-memory", action="store_true", help="Also import local recommendation/feedback history into case_memory.")
    parser.add_argument("--recreate", action="store_true", help="Delete and recreate target collections before import.")
    parser.add_argument("--dry-run", action="store_true", help="Show how many records would be imported without writing to Qdrant.")
    args = parser.parse_args()

    settings = get_qdrant_settings()
    records_map = build_records_map(args.rag_dir, include_memory=args.include_memory)
    embedder = EmbeddingModel(args.model, batch_size=args.batch_size)

    client = None if args.dry_run else get_qdrant_client()
    summary: dict[str, Any] = {
        "qdrant": settings.to_dict(),
        "model": args.model,
        "embedding_dim": embedder.vector_size,
        "collections": {},
        "dry_run": args.dry_run,
    }

    for key in args.collections:
        definition = COLLECTION_DEFINITIONS[key]
        collection_name = settings.collection_name(definition.name)
        records = records_map.get(key, [])
        if client is not None:
            ensure_collection(client, collection_name, embedder.vector_size, recreate=args.recreate)
        imported = upsert_records(client, collection_name, records, embedder, args.batch_size, args.dry_run)
        summary["collections"][key] = {
            "collection_name": collection_name,
            "configured_vector_size": definition.vector_size,
            "actual_vector_size": embedder.vector_size,
            "record_count": len(records),
            "imported_count": imported,
        }

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
