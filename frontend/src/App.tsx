import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "@/routes/LoginPage";
import AdminLayout from "@/routes/admin/AdminLayout";
import EmployeesPage from "@/routes/admin/EmployeesPage";
import EmployeeFormPage from "@/routes/admin/EmployeeFormPage";
import EnrollPage from "@/routes/admin/EnrollPage";
import AttendancePage from "@/routes/admin/AttendancePage";

// Route /kiosk sẽ thêm ở tuần 5

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route path="/admin" element={<AdminLayout />}>
        <Route index element={<Navigate to="employees" replace />} />

        {/* Employees */}
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/new" element={<EmployeeFormPage />} />
        <Route path="employees/:id/edit" element={<EmployeeFormPage />} />
        <Route path="employees/:id/enroll" element={<EnrollPage />} />

        {/* Attendance */}
        <Route path="attendance" element={<AttendancePage />} />
      </Route>

      <Route path="/" element={<Navigate to="/admin/employees" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
