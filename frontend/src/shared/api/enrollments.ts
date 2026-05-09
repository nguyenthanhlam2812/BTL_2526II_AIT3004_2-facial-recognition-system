import { api } from "./client";
import type { EnrollmentCreateResponse, EnrollmentStatusResponse } from "@/shared/types/api";

export async function createEnrollment(
  employeeId: number,
  files: File[],
): Promise<EnrollmentCreateResponse> {
  const fd = new FormData();
  files.forEach((f) => fd.append("files", f));
  const { data } = await api.post<EnrollmentCreateResponse>(
    `/employees/${employeeId}/enrollments`,
    fd,
  );
  return data;
}

export async function getEnrollmentJob(jobId: string): Promise<EnrollmentStatusResponse> {
  const { data } = await api.get<EnrollmentStatusResponse>(`/enrollments/${jobId}`);
  return data;
}
