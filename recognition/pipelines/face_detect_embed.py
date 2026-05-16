from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from insightface.app import FaceAnalysis


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PoC detect + embedding using InsightFace and OpenCV."
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to a single image or a directory of images.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/poc/results.json"),
        help="Path to the JSON output file.",
    )
    parser.add_argument(
        "--annotated-dir",
        type=Path,
        default=None,
        help="Optional directory for saving annotated preview images.",
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
    parser.add_argument(
        "--omit-embedding",
        action="store_true",
        help="Do not include the full embedding vector in JSON output.",
    )
    return parser


def collect_images(input_path: Path) -> list[Path]:
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if input_path.is_file():
        if input_path.suffix.lower() not in IMAGE_EXTENSIONS:
            raise ValueError(f"Unsupported image file: {input_path}")
        return [input_path]

    images = sorted(
        path for path in input_path.rglob("*") if path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if not images:
        raise ValueError(f"No supported images found under: {input_path}")
    return images


def create_face_app(model_name: str, model_root: Path | None, det_size: int, providers: list[str]) -> FaceAnalysis:
    kwargs: dict[str, Any] = {"name": model_name, "providers": providers}
    if model_root is not None:
        kwargs["root"] = str(model_root)

    try:
        app = FaceAnalysis(**kwargs)
        app.prepare(ctx_id=-1, det_size=(det_size, det_size))
    except Exception as exc:
        raise RuntimeError(
            "Failed to initialize InsightFace. Install dependencies and make sure model weights are available. "
            "On first run, InsightFace may need to download weights."
        ) from exc
    return app


def bbox_area(face: Any) -> float:
    bbox = np.asarray(face.bbox, dtype=float)
    return max(0.0, float((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])))


def select_primary_face(faces: list[Any]) -> tuple[int, Any]:
    return max(enumerate(faces), key=lambda item: bbox_area(item[1]))


def round_floats(values: np.ndarray, digits: int = 6) -> list[float]:
    return [round(float(value), digits) for value in values.tolist()]


def serialize_face(face: Any, include_embedding: bool) -> dict[str, Any]:
    bbox = np.asarray(face.bbox, dtype=float)
    kps = getattr(face, "kps", None)
    embedding = getattr(face, "embedding", None)

    payload: dict[str, Any] = {
        "bbox": round_floats(bbox, digits=2),
        "det_score": round(float(getattr(face, "det_score", 0.0)), 6),
        "area": round(bbox_area(face), 2),
    }

    if kps is not None:
        payload["kps"] = [
            [round(float(point[0]), 2), round(float(point[1]), 2)]
            for point in np.asarray(kps, dtype=float)
        ]

    if embedding is not None:
        embedding_array = np.asarray(embedding, dtype=float)
        payload["embedding_dim"] = int(embedding_array.shape[0])
        payload["embedding_norm"] = round(float(np.linalg.norm(embedding_array)), 6)
        if include_embedding:
            payload["embedding"] = round_floats(embedding_array)

    return payload


def annotate_image(image: np.ndarray, faces: list[Any], primary_index: int) -> np.ndarray:
    canvas = image.copy()
    for index, face in enumerate(faces):
        bbox = np.asarray(face.bbox, dtype=int)
        x1, y1, x2, y2 = bbox.tolist()
        is_primary = index == primary_index
        color = (0, 200, 0) if is_primary else (0, 165, 255)
        label = f"face_{index} score={float(getattr(face, 'det_score', 0.0)):.3f}"
        if is_primary:
            label += " primary"

        cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            canvas,
            label,
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            color,
            2,
            cv2.LINE_AA,
        )
    return canvas


def build_annotated_path(source_path: Path, input_root: Path, annotated_dir: Path) -> Path:
    if input_root.is_file():
        return annotated_dir / source_path.name
    return annotated_dir / source_path.relative_to(input_root)


def process_image(
    app: FaceAnalysis,
    image_path: Path,
    input_root: Path,
    annotated_dir: Path | None,
    include_embedding: bool,
) -> dict[str, Any]:
    image = cv2.imread(str(image_path))
    relative_path = image_path.name if input_root.is_file() else str(image_path.relative_to(input_root))

    if image is None:
        return {
            "image_path": str(image_path),
            "relative_path": relative_path,
            "status": "read_error",
            "error": "OpenCV could not read the image.",
        }

    faces = app.get(image)
    result: dict[str, Any] = {
        "image_path": str(image_path),
        "relative_path": relative_path,
        "image_size": {"width": int(image.shape[1]), "height": int(image.shape[0])},
        "faces_detected": len(faces),
    }

    if not faces:
        result["status"] = "no_face_detected"
        return result

    primary_index, primary_face = select_primary_face(faces)
    result["status"] = "ok" if len(faces) == 1 else "multiple_faces_detected"
    result["primary_face_index"] = primary_index
    result["primary_face"] = serialize_face(primary_face, include_embedding=include_embedding)
    result["all_faces"] = [
        serialize_face(face, include_embedding=False)
        for face in faces
    ]

    if annotated_dir is not None:
        annotated_path = build_annotated_path(image_path, input_root, annotated_dir)
        annotated_path.parent.mkdir(parents=True, exist_ok=True)
        annotated = annotate_image(image, faces, primary_index)
        cv2.imwrite(str(annotated_path), annotated)
        result["annotated_image"] = str(annotated_path)

    return result


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    counter = Counter(item["status"] for item in items)
    return {
        "total_images": len(items),
        "ok": counter.get("ok", 0),
        "multiple_faces_detected": counter.get("multiple_faces_detected", 0),
        "no_face_detected": counter.get("no_face_detected", 0),
        "read_error": counter.get("read_error", 0),
    }


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    images = collect_images(args.input)
    app = create_face_app(
        model_name=args.model_name,
        model_root=args.model_root,
        det_size=args.det_size,
        providers=args.providers,
    )

    items = [
        process_image(
            app=app,
            image_path=image_path,
            input_root=args.input,
            annotated_dir=args.annotated_dir,
            include_embedding=not args.omit_embedding,
        )
        for image_path in images
    ]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "config": {
            "model_name": args.model_name,
            "model_root": str(args.model_root) if args.model_root else None,
            "det_size": args.det_size,
            "providers": args.providers,
            "include_embedding": not args.omit_embedding,
        },
        "summary": build_summary(items),
        "items": items,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"Processed {len(images)} image(s).")
    print(f"Results written to: {args.output}")
    if args.annotated_dir is not None:
        print(f"Annotated images written to: {args.annotated_dir}")


if __name__ == "__main__":
    main()
