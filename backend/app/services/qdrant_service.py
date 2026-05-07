from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.app.config import get_settings


class VectorStoreError(Exception):
    pass


@dataclass(slots=True)
class FaceSearchResult:
    employee_id: int | None
    score: float
    payload: dict[str, object]
    point_id: str | int | None


def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    return QdrantClient(url=settings.qdrant_url)


def ensure_collection_exists() -> str:
    settings = get_settings()
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection_employee_faces

    try:
        client.get_collection(collection_name)
        return collection_name
    except UnexpectedResponse:
        pass
    except Exception as exc:
        raise VectorStoreError("Cannot access Qdrant collection.") from exc

    try:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=512, distance=Distance.COSINE),
        )
    except Exception as exc:
        raise VectorStoreError("Cannot create Qdrant collection.") from exc

    return collection_name


def upsert_face_embedding(
    *,
    employee_id: int,
    enrollment_id: int,
    enrollment_image_id: int,
    object_key: str,
    embedding: list[float],
) -> str:
    client = get_qdrant_client()
    collection_name = ensure_collection_exists()
    point_id = str(uuid4())

    try:
        client.upsert(
            collection_name=collection_name,
            wait=True,
            points=[
                PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "employee_id": employee_id,
                        "enrollment_id": enrollment_id,
                        "enrollment_image_id": enrollment_image_id,
                        "object_key": object_key,
                    },
                )
            ],
        )
    except Exception as exc:
        raise VectorStoreError("Cannot upsert embedding to Qdrant.") from exc

    return point_id


def search_face_embedding(
    *,
    embedding: list[float],
    limit: int = 1,
) -> FaceSearchResult | None:
    client = get_qdrant_client()
    collection_name = ensure_collection_exists()

    try:
        points = client.search(
            collection_name=collection_name,
            query_vector=embedding,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
    except Exception as exc:
        raise VectorStoreError("Cannot search embedding in Qdrant.") from exc

    if not points:
        return None

    point = points[0]
    payload = dict(point.payload or {})
    employee_id_raw = payload.get("employee_id")
    employee_id = int(employee_id_raw) if employee_id_raw is not None else None

    return FaceSearchResult(
        employee_id=employee_id,
        score=float(point.score),
        payload=payload,
        point_id=point.id,
    )
