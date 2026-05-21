import { Routes, Route, Navigate } from "react-router-dom";
import LoginPage from "@/routes/LoginPage";
import AdminLayout from "@/routes/admin/AdminLayout";
import DashboardPage from "@/routes/admin/DashboardPage";
import EmployeesPage from "@/routes/admin/EmployeesPage";
import EmployeeFormPage from "@/routes/admin/EmployeeFormPage";
import EnrollPage from "@/routes/admin/EnrollPage";
import AttendancePage from "@/routes/admin/AttendancePage";
import ReportsPage from "@/routes/admin/ReportsPage";
import AuditPage from "@/routes/admin/AuditPage";
import LookupsPage from "@/routes/admin/LookupsPage";
import SystemPage from "@/routes/admin/SystemPage";
import UsersPage from "@/routes/admin/UsersPage";
import KioskPage from "@/routes/kiosk/KioskPage";
import ErrorBoundary from "@/shared/ui/ErrorBoundary";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/admin"
        element={
          <ErrorBoundary>
            <AdminLayout />
          </ErrorBoundary>
        }
      >
        <Route index element={<Navigate to="dashboard" replace />} />

        {/* Dashboard */}
        <Route path="dashboard" element={<DashboardPage />} />

        {/* Employees */}
        <Route path="employees" element={<EmployeesPage />} />
        <Route path="employees/new" element={<EmployeeFormPage />} />
        <Route path="employees/:id/edit" element={<EmployeeFormPage />} />
        <Route path="employees/:id/enroll" element={<EnrollPage />} />

        {/* Lookups */}
        <Route path="lookups" element={<LookupsPage />} />

        {/* Attendance */}
        <Route path="attendance" element={<AttendancePage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="audit" element={<AuditPage />} />
        <Route path="users" element={<UsersPage />} />

        {/* System settings */}
        <Route path="system" element={<SystemPage />} />
      </Route>

      {/* Kiosk — standalone, không cần auth */}
      <Route
        path="/kiosk"
        element={
          <ErrorBoundary>
            <KioskPage />
          </ErrorBoundary>
        }
      />

      <Route path="/" element={<Navigate to="/admin/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
