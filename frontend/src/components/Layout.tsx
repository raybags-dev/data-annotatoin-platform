import { Outlet, NavLink } from 'react-router-dom'

const nav = [
  { to: '/dashboard', label: '📊 Dashboard' },
  { to: '/datasets', label: '🗂 Datasets' },
  { to: '/datasets/upload', label: '⬆ Upload' },
]

export default function Layout() {
  return (
    <div className="flex min-h-screen">
      <aside className="w-56 bg-gray-900 border-r border-white/10 flex flex-col">
        <div className="px-5 py-4 border-b border-white/10">
          <h1 className="font-bold text-sm text-indigo-400 uppercase tracking-widest">Annotation</h1>
          <p className="text-xs text-gray-500 mt-0.5">Platform</p>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {nav.map(n => (
            <NavLink
              key={n.to}
              to={n.to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive ? 'bg-indigo-600/20 text-indigo-400' : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }`
              }
            >{n.label}</NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
