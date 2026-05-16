import { publicApi } from "./client";
import type { AttendanceActionType, AttendanceFrameResponse } from "@/shared/types/api";

export async function postAttendanceFrame(
  imageBlob: Blob,
  actionType: AttendanceActionType,
  capturedAt?: string,
  cameraId?: string,
  recordUnmatched = true,
): Promise<AttendanceFrameResponse> {
  const fd = new FormData();
  fd.append("image", imageBlob, "frame.jpg");
  fd.append("action_type", actionType);
  fd.append("record_unmatched", String(recordUnmatched));
  if (capturedAt) fd.append("captured_at", capturedAt);
  if (cameraId) fd.append("camera_id", cameraId);
  const { data } = await publicApi.post<AttendanceFrameResponse>("/attendance/frame", fd);
  return data;
}
