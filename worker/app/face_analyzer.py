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


def analyze_image_bytes(image_bytes: bytes) -> dict[str, object]:
    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        return {
            "status": "failed",
            "faces_detected": 0,
            "error_message": "Cannot decode image.",
        }

    faces = get_face_app().get(image)
    faces_detected = len(faces)

    if faces_detected == 0:
        return {
            "status": "failed",
            "faces_detected": 0,
            "error_message": "No face detected.",
        }

    if faces_detected > 1:
        return {
            "status": "failed",
            "faces_detected": faces_detected,
            "error_message": "Multiple faces detected.",
        }

    return {
        "status": "success",
        "faces_detected": 1,
        "error_message": None,
    }
