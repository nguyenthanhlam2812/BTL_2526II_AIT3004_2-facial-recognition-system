"""Camera-captured files compatibility tests.

Prove that files produced by canvas.toBlob() in the EnrollCameraCapture
component (image/jpeg, .jpg filename) pass through the enrollment pipeline
identically to regular file uploads.
"""

from __future__ import annotations

from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import UploadFile

from backend.app.services.enrollment_service import (
    build_prepared_files,
    build_safe_filename,
    is_image_file,
    validate_enrollment_files,
)


def _make_upload_file(
    filename: str,
    content: bytes = b"\x89PNG\r\n\x1a\n",
    content_type: str = "image/jpeg",
) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers={"content-type": content_type},
    )


# ──────────────────────────────────────────────────────────────────
# is_image_file – camera content types
# ──────────────────────────────────────────────────────────────────


class TestIsImageFile:
    def test_jpeg_content_type_accepted(self):
        assert is_image_file(_make_upload_file("camera_capture_1.jpg", content_type="image/jpeg"))

    def test_png_content_type_accepted(self):
        assert is_image_file(_make_upload_file("camera_capture_1.png", content_type="image/png"))

    def test_webp_content_type_accepted(self):
        assert is_image_file(_make_upload_file("camera_capture_1.webp", content_type="image/webp"))

    def test_jpg_extension_accepted_without_content_type(self):
        assert is_image_file(_make_upload_file("shot.jpg", content_type="application/octet-stream"))

    def test_jpeg_extension_accepted(self):
        assert is_image_file(_make_upload_file("shot.jpeg", content_type="application/octet-stream"))

    def test_bmp_extension_accepted(self):
        assert is_image_file(_make_upload_file("shot.bmp", content_type="application/octet-stream"))

    def test_non_image_rejected(self):
        assert not is_image_file(_make_upload_file("data.csv", content_type="text/csv"))


# ──────────────────────────────────────────────────────────────────
# validate_enrollment_files – camera-style inputs
# ──────────────────────────────────────────────────────────────────


class TestValidateEnrollmentFiles:
    def test_single_camera_capture_file_passes(self):
        files = [_make_upload_file("camera_capture_1.jpg")]
        validate_enrollment_files(files)  # No exception

    def test_multiple_camera_capture_files_pass(self):
        files = [_make_upload_file(f"camera_capture_{i}.jpg") for i in range(1, 4)]
        validate_enrollment_files(files)  # No exception

    def test_mixed_camera_and_upload_files_pass(self):
        files = [
            _make_upload_file("camera_capture_1.jpg", content_type="image/jpeg"),
            _make_upload_file("portrait.png", content_type="image/png"),
        ]
        validate_enrollment_files(files)  # No exception

    def test_max_five_camera_files_pass(self):
        files = [_make_upload_file(f"camera_capture_{i}.jpg") for i in range(1, 6)]
        validate_enrollment_files(files)

    def test_six_camera_files_rejected(self):
        files = [_make_upload_file(f"camera_capture_{i}.jpg") for i in range(1, 7)]
        with pytest.raises(Exception, match="Maximum 5"):
            validate_enrollment_files(files)


# ──────────────────────────────────────────────────────────────────
# build_prepared_files – object keys from camera filenames
# ──────────────────────────────────────────────────────────────────


class TestBuildPreparedFiles:
    def test_camera_file_produces_correct_object_key(self):
        content = b"fake-jpeg-bytes"
        files = [_make_upload_file("camera_capture_1.jpg", content=content)]
        prepared = build_prepared_files(files, "job_abc123")

        assert len(prepared) == 1
        item = prepared[0]
        assert item["object_key"] == "enrollments/job_abc123/01_camera_capture_1.jpg"
        assert item["content_type"] == "image/jpeg"
        assert item["content"] == content
        assert item["original_name"] == "camera_capture_1.jpg"
        assert item["sort_order"] == 1

    def test_multiple_camera_files_are_sequentially_numbered(self):
        files = [_make_upload_file(f"camera_capture_{i}.jpg") for i in range(1, 4)]
        prepared = build_prepared_files(files, "job_xyz999")

        assert len(prepared) == 3
        assert prepared[0]["object_key"] == "enrollments/job_xyz999/01_camera_capture_1.jpg"
        assert prepared[1]["object_key"] == "enrollments/job_xyz999/02_camera_capture_2.jpg"
        assert prepared[2]["object_key"] == "enrollments/job_xyz999/03_camera_capture_3.jpg"


# ──────────────────────────────────────────────────────────────────
# build_safe_filename – camera naming safety
# ──────────────────────────────────────────────────────────────────


class TestBuildSafeFilename:
    def test_camera_capture_filename_passes_through(self):
        assert build_safe_filename("camera_capture_1.jpg", 1) == "camera_capture_1.jpg"

    def test_unicode_filename_is_sanitized(self):
        result = build_safe_filename("ảnh_chụp_từ_camera.jpg", 1)
        assert ".jpg" in result
        # Vietnamese diacritics should be replaced with underscores
        assert "ả" not in result

    def test_empty_filename_gets_fallback(self):
        assert build_safe_filename("", 3) == "image_3.jpg"
