import { AuthProvider } from './context/AuthProvider';
import { useAuth } from './context/AuthContext';
import { HealthDashboard } from './components/HealthDashboard';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';

const AppContent = () => {
  const { currentPage } = useAuth();

  return (
    <>
      {currentPage === 'login' && <LoginPage />}
      {currentPage === 'register' && <RegisterPage />}
      {currentPage === 'dashboard' && <HealthDashboard />}
    </>
  );
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;