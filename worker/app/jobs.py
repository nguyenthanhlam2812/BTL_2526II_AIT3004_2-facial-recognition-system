from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)


def process_enrollment_job(payload: dict[str, Any]) -> dict[str, Any]:
    logger.info("Received enrollment job placeholder: %s", payload)
    return {
        "status": "pending",
        "message": "Worker scaffold đã sẵn sàng, logic xử lý enrollment sẽ được bổ sung ở bước tiếp theo.",
    }
