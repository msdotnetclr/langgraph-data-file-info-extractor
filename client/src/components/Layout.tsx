import { useState } from 'react';
import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard', icon: '📊' },
  { to: '/domains', label: 'Domains', icon: '🌐' },
  { to: '/sessions', label: 'Sessions', icon: '⚡' },
  { to: '/outputs', label: 'Outputs', icon: '📦' },
];

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="min-h-screen bg-gray-50 flex">
      <aside className={`bg-white border-r border-gray-200 flex flex-col transition-all duration-300 ${collapsed ? 'w-12' : 'w-56'}`}>
        <div className={`p-4 border-b border-gray-100 flex items-center ${collapsed ? 'justify-center' : 'justify-between'}`}>
          {!collapsed && (
            <div>
              <h1 className="text-lg font-bold text-gray-800">Data Assistant</h1>
              <p className="text-xs text-gray-400 mt-0.5">Source Data Spec Extractor</p>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="text-gray-400 hover:text-gray-600 transition-colors flex-shrink-0"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
              {collapsed ? (
                <path d="M 5,3 L 10,8 L 5,13" />
              ) : (
                <path d="M 10,3 L 5,8 L 10,13" />
              )}
            </svg>
          </button>
        </div>
        <nav className="flex-1 p-2 space-y-0.5">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) =>
                `block px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                  collapsed ? 'text-center' : ''
                } ${
                  isActive
                    ? 'bg-blue-50 text-blue-700'
                    : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                }`
              }
            >
              <span className="inline-block align-middle">{item.icon}</span>
              {!collapsed && <span className="ml-2">{item.label}</span>}
            </NavLink>
          ))}
        </nav>
        {!collapsed && (
          <div className="p-3 border-t border-gray-100 text-xs text-gray-400">
            LangGraph + FastAPI
          </div>
        )}
      </aside>
      <main className="flex-1 p-6 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
