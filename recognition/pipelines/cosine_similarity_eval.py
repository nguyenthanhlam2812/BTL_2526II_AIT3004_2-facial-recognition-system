from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from statistics import mean, median
from typing import Any

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from recognition.pipelines.face_detect_embed import collect_images, create_face_app, select_primary_face


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate cosine similarity on enrolled and unknown demo images."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/demo"),
        help="Root directory containing enrolled/ and unknown/ demo images.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/poc/cosine_similarity.json"),
        help="Path to the JSON output file.",
    )
    parser.add_argument(
        "--model-name",
        default="buffalo_l",
        help="InsightFace model pack name.",
    )
    parser.add_argument(
        "--model-root",
        type=Path,
        default=None,
        help="Optional root directory for local InsightFace model weights.",
    )
    parser.add_argument(
        "--det-size",
        type=int,
        default=640,
        help="Detection input size. Default is 640.",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["CPUExecutionProvider"],
        help="ONNX Runtime providers. Default is CPUExecutionProvider.",
    )
    return parser


def summarize_scores(scores: list[float]) -> dict[str, float] | None:
    if not scores:
        return None

    return {
        "count": len(scores),
        "min": round(min(scores), 6),
        "max": round(max(scores), 6),
        "mean": round(mean(scores), 6),
        "median": round(median(scores), 6),
    }


def compute_cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    return float(np.dot(left, right))


def normalize_embedding(embedding: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(embedding))
    if norm == 0.0:
        raise ValueError("Embedding norm is zero.")
    return embedding / norm


def extract_embedding_record(app: Any, image_path: Path, input_root: Path, identity: str, split: str) -> dict[str, Any]:
    image = cv2.imread(str(image_path))
    relative_path = str(image_path.relative_to(input_root))

    if image is None:
        return {
            "status": "read_error",
            "split": split,
            "identity": identity,
            "image_path": str(image_path),
            "relative_path": relative_path,
            "error": "OpenCV could not read the image.",
        }

    faces = app.get(image)
    if not faces:
        return {
            "status": "no_face_detected",
            "split": split,
            "identity": identity,
            "image_path": str(image_path),
            "relative_path": relative_path,
            "faces_detected": 0,
        }

    primary_index, primary_face = select_primary_face(faces)
    embedding = getattr(primary_face, "embedding", None)
    if embedding is None:
        return {
            "status": "embedding_missing",
            "split": split,
            "identity": identity,
            "image_path": str(image_path),
            "relative_path": relative_path,
            "faces_detected": len(faces),
            "primary_face_index": primary_index,
        }

    normalized = normalize_embedding(np.asarray(embedding, dtype=float))
    return {
        "status": "ok" if len(faces) == 1 else "multiple_faces_detected",
        "split": split,
        "identity": identity,
        "image_path": str(image_path),
        "relative_path": relative_path,
        "faces_detected": len(faces),
        "primary_face_index": primary_index,
        "det_score": round(float(getattr(primary_face, "det_score", 0.0)), 6),
        "embedding_dim": int(normalized.shape[0]),
        "embedding": normalized,
    }


def collect_dataset_records(app: Any, input_root: Path) -> list[dict[str, Any]]:
    enrolled_root = input_root / "enrolled"
    unknown_root = input_root / "unknown"
    records: list[dict[str, Any]] = []

    if enrolled_root.exists():
        for identity_dir in sorted(path for path in enrolled_root.iterdir() if path.is_dir()):
            for image_path in collect_images(identity_dir):
                records.append(
                    extract_embedding_record(
                        app=app,
                        image_path=image_path,
                        input_root=input_root,
                        identity=identity_dir.name,
                        split="enrolled",
                    )
                )

    if unknown_root.exists():
        for image_path in collect_images(unknown_root):
            records.append(
                extract_embedding_record(
                    app=app,
                    image_path=image_path,
                    input_root=input_root,
                    identity="unknown",
                    split="unknown",
                )
            )

    return records


def build_pair_record(left: dict[str, Any], right: dict[str, Any], pair_type: str, label: str) -> dict[str, Any]:
    score = compute_cosine_similarity(left["embedding"], right["embedding"])
    return {
        "pair_type": pair_type,
        "label": label,
        "score": round(score, 6),
        "left": {
            "identity": left["identity"],
            "relative_path": left["relative_path"],
            "split": left["split"],
        },
        "right": {
            "identity": right["identity"],
            "relative_path": right["relative_path"],
            "split": right["split"],
        },
    }


def build_similarity_pairs(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    usable_records = [record for record in records if record["status"] in {"ok", "multiple_faces_detected"}]
    enrolled_by_identity: dict[str, list[dict[str, Any]]] = defaultdict(list)
    unknown_records: list[dict[str, Any]] = []

    for record in usable_records:
        if record["split"] == "enrolled":
            enrolled_by_identity[record["identity"]].append(record)
        else:
            unknown_records.append(record)

    pairs: list[dict[str, Any]] = []

    for identity_records in enrolled_by_identity.values():
        for left, right in combinations(identity_records, 2):
            pairs.append(build_pair_record(left, right, pair_type="positive_same_identity", label="positive"))

    enrolled_identities = sorted(enrolled_by_identity)
    for index, left_identity in enumerate(enrolled_identities):
        for right_identity in enrolled_identities[index + 1 :]:
            for left in enrolled_by_identity[left_identity]:
                for right in enrolled_by_identity[right_identity]:
                    pairs.append(build_pair_record(left, right, pair_type="negative_cross_identity", label="negative"))

    for unknown in unknown_records:
        for identity_records in enrolled_by_identity.values():
            for enrolled in identity_records:
                pairs.append(build_pair_record(unknown, enrolled, pair_type="negative_unknown_vs_enrolled", label="negative"))

    return pairs


def evaluate_threshold(pairs: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    tp = fp = tn = fn = 0
    for pair in pairs:
        predicted_positive = pair["score"] >= threshold
        actual_positive = pair["label"] == "positive"
        if predicted_positive and actual_positive:
            tp += 1
        elif predicted_positive and not actual_positive:
            fp += 1
        elif not predicted_positive and not actual_positive:
            tn += 1
        else:
            fn += 1

    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return {
        "threshold": round(float(threshold), 6),
        "accuracy": round(float(accuracy), 6),
        "precision": round(float(precision), 6),
        "recall": round(float(recall), 6),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
    }


def find_best_threshold(pairs: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not pairs:
        return None

    scores = sorted({pair["score"] for pair in pairs})
    candidates = sorted(set(scores + [score - 1e-6 for score in scores] + [score + 1e-6 for score in scores]))
    best_result: dict[str, Any] | None = None

    for threshold in candidates:
        result = evaluate_threshold(pairs, threshold)

        if best_result is None:
            best_result = result
            continue

        if result["accuracy"] > best_result["accuracy"]:
            best_result = result
            continue

        if result["accuracy"] == best_result["accuracy"] and result["precision"] > best_result["precision"]:
            best_result = result

    return best_result


def build_summary(records: list[dict[str, Any]], pairs: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts: dict[str, int] = defaultdict(int)
    for record in records:
        status_counts[record["status"]] += 1

    positive_scores = [pair["score"] for pair in pairs if pair["label"] == "positive"]
    negative_scores = [pair["score"] for pair in pairs if pair["label"] == "negative"]

    summary: dict[str, Any] = {
        "images_total": len(records),
        "status_counts": dict(sorted(status_counts.items())),
        "pairs_total": len(pairs),
        "positive_pairs": len(positive_scores),
        "negative_pairs": len(negative_scores),
        "positive_score_summary": summarize_scores(positive_scores),
        "negative_score_summary": summarize_scores(negative_scores),
        "best_accuracy_threshold": find_best_threshold(pairs),
    }

    if positive_scores and negative_scores:
        min_positive = min(positive_scores)
        max_negative = max(negative_scores)
        separation_gap = min_positive - max_negative
        summary["separation_gap"] = round(separation_gap, 6)
        if separation_gap > 0:
            midpoint_threshold = (min_positive + max_negative) / 2.0
            summary["recommended_threshold"] = {
                **evaluate_threshold(pairs, midpoint_threshold),
                "strategy": "midpoint_between_max_negative_and_min_positive",
            }
        else:
            summary["recommended_threshold"] = {
                **summary["best_accuracy_threshold"],
                "strategy": "best_accuracy_on_current_pairs",
            }
    else:
        summary["recommended_threshold"] = (
            {
                **summary["best_accuracy_threshold"],
                "strategy": "best_accuracy_on_current_pairs",
            }
            if summary["best_accuracy_threshold"] is not None
            else None
        )

    return summary


def serialize_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    serialized: list[dict[str, Any]] = []
    for record in records:
        item = {key: value for key, value in record.items() if key != "embedding"}
        serialized.append(item)
    return serialized


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    app = create_face_app(
        model_name=args.model_name,
        model_root=args.model_root,
        det_size=args.det_size,
        providers=args.providers,
    )

    records = collect_dataset_records(app=app, input_root=args.input)
    pairs = build_similarity_pairs(records)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "config": {
            "model_name": args.model_name,
            "model_root": str(args.model_root) if args.model_root else None,
            "det_size": args.det_size,
            "providers": args.providers,
        },
        "summary": build_summary(records, pairs),
        "records": serialize_records(records),
        "pairs": pairs,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Processed {len(records)} image(s).")
    print(f"Generated {len(pairs)} similarity pair(s).")
    print(f"Results written to: {args.output}")


if __name__ == "__main__":
    main()
