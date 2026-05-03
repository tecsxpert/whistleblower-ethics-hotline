import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout({ children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className="w-64 bg-primary text-white flex flex-col">
        <div className="p-6 border-b border-blue-700">
          <h2 className="text-lg font-bold">🔒 Ethics Hotline</h2>
          <p className="text-blue-200 text-sm mt-1">Whistleblower Portal</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {[
            { to: '/', label: '📊 Dashboard' },
            { to: '/reports', label: '📋 Reports' },
            { to: '/analytics', label: '📈 Analytics' },
            { to: '/audit-log', label: '📜 Audit Log' },
          ].map(({ to, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `block px-4 py-2 rounded-lg text-sm transition ${
                  isActive
                    ? 'bg-blue-700 text-white'
                    : 'text-blue-100 hover:bg-blue-700'
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-4 border-t border-blue-700">
          <p className="text-blue-200 text-sm">{user?.username}</p>
          <button
            onClick={handleLogout}
            className="text-blue-200 hover:text-white text-sm mt-1"
          >
            Logout →
          </button>
        </div>
      </aside>
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}