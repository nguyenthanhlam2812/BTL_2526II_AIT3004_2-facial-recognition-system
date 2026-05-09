from __future__ import annotations

from functools import lru_cache

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from backend.app.config import get_settings


@lru_cache
def get_face_app() -> FaceAnalysis:
    settings = get_settings()
    app = FaceAnalysis(
        name=settings.insightface_model_name,
        providers=["CPUExecutionProvider"],
    )
    app.prepare(ctx_id=-1, det_size=(640, 640))
    return app


def _bbox_area(face: object) -> float:
    bbox = np.asarray(getattr(face, "bbox", [0, 0, 0, 0]), dtype=float)
    return max(0.0, float((bbox[2] - bbox[0]) * (bbox[3] - bbox[1])))


def _valid_faces(faces: list[object], image: np.ndarray) -> list[object]:
    settings = get_settings()
    image_area = float(image.shape[0] * image.shape[1])
    if image_area <= 0:
        return []

    valid: list[object] = []
    for face in faces:
        det_score = float(getattr(face, "det_score", 0.0))
        area_ratio = _bbox_area(face) / image_area
        if det_score >= settings.face_min_det_score and area_ratio >= settings.face_min_area_ratio:
            valid.append(face)

    return sorted(valid, key=_bbox_area, reverse=True)


def analyze_image_bytes(image_bytes: bytes) -> dict[str, object]:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        return {
            "status": "failed",
            "faces_detected": 0,
            "error_message": "Cannot decode image.",
        }

    faces = _valid_faces(get_face_app().get(image), image)
    faces_detected = len(faces)

    if faces_detected == 0:
        return {
            "status": "failed",
            "faces_detected": 0,
            "error_message": "No face detected.",
        }

    primary_face = faces[0]
    settings = get_settings()
    blocking_secondary_faces = [
        face
        for face in faces[1:]
        if _bbox_area(face) >= _bbox_area(primary_face) * settings.face_secondary_area_ratio
    ]

    if blocking_secondary_faces:
        return {
            "status": "failed",
            "faces_detected": faces_detected,
            "error_message": "Multiple faces detected.",
        }

    embedding = np.asarray(primary_face.embedding, dtype=float)

    return {
        "status": "success",
        "faces_detected": 1,
        "error_message": None,
        "embedding": embedding.tolist(),
        "embedding_dim": int(embedding.shape[0]),
    }
