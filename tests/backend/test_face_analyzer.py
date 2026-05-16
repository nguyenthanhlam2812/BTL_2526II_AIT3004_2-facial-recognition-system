from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from backend.app.services import face_analyzer


class FakeFace:
    def __init__(
        self,
        *,
        bbox: list[float],
        det_score: float = 0.9,
        embedding: list[float] | None = None,
    ) -> None:
        self.bbox = bbox
        self.det_score = det_score
        self.embedding = embedding or [0.1] * 512


class FakeFaceApp:
    def __init__(self, faces: list[FakeFace]) -> None:
        self._faces = faces

    def get(self, image: np.ndarray) -> list[FakeFace]:
        return self._faces


def configure_analyzer(monkeypatch, faces: list[FakeFace]) -> None:
    monkeypatch.setattr(
        face_analyzer.cv2,
        "imdecode",
        lambda image_array, flags: np.zeros((100, 100, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(face_analyzer, "get_face_app", lambda: FakeFaceApp(faces))
    monkeypatch.setattr(
        face_analyzer,
        "get_settings",
        lambda: SimpleNamespace(
            face_min_det_score=0.5,
            face_min_area_ratio=0.015,
            face_secondary_area_ratio=0.35,
        ),
    )


def test_analyze_image_bytes_returns_success_for_one_valid_face(monkeypatch):
    configure_analyzer(
        monkeypatch,
        [FakeFace(bbox=[10, 10, 60, 60])],
    )

    result = face_analyzer.analyze_image_bytes(b"image")

    assert result["status"] == "success"
    assert result["faces_detected"] == 1
    assert result["embedding_dim"] == 512


def test_analyze_image_bytes_returns_multiple_faces_for_two_large_faces(monkeypatch):
    configure_analyzer(
        monkeypatch,
        [
            FakeFace(bbox=[10, 10, 60, 60]),
            FakeFace(bbox=[30, 30, 80, 80]),
        ],
    )

    result = face_analyzer.analyze_image_bytes(b"image")

    assert result["status"] == "failed"
    assert result["faces_detected"] == 2
    assert result["error_message"] == "Multiple faces detected."


def test_analyze_image_bytes_ignores_small_or_low_score_secondary_faces(monkeypatch):
    configure_analyzer(
        monkeypatch,
        [
            FakeFace(bbox=[10, 10, 60, 60]),
            FakeFace(bbox=[1, 1, 8, 8]),
            FakeFace(bbox=[20, 20, 80, 80], det_score=0.2),
        ],
    )

    result = face_analyzer.analyze_image_bytes(b"image")

    assert result["status"] == "success"
    assert result["faces_detected"] == 1


def test_analyze_image_bytes_returns_no_face_when_no_valid_face_remains(monkeypatch):
    configure_analyzer(
        monkeypatch,
        [
            FakeFace(bbox=[1, 1, 6, 6]),
            FakeFace(bbox=[20, 20, 80, 80], det_score=0.2),
        ],
    )

    result = face_analyzer.analyze_image_bytes(b"image")

    assert result["status"] == "failed"
    assert result["faces_detected"] == 0
    assert result["error_message"] == "No face detected."
