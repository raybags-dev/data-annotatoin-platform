import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { api } from '../lib/api'
import StatCard from '../components/StatCard'

const COLORS = ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#3b82f6']

export default function Dashboard() {
  const { data, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: api.dashboard, refetchInterval: 10_000 })

  if (isLoading) return <div className="p-8 text-gray-500 animate-pulse">Loading dashboard…</div>
  if (!data) return null

  const labelData = Object.entries(data.label_distribution).map(([name, value]) => ({ name, value }))
  const statusData = Object.entries(data.dataset_status_distribution).map(([name, value]) => ({ name, value }))

  return (
    <div className="p-8 space-y-8">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Datasets" value={data.total_datasets} />
        <StatCard label="Records" value={data.total_records.toLocaleString()} />
        <StatCard label="Avg Confidence" value={data.confidence_stats.avg ? (data.confidence_stats.avg * 100).toFixed(1) + '%' : '—'} />
        <StatCard label="Annotation Coverage"
          value={data.total_records > 0
            ? Math.round(((data.annotation_status_distribution.approved ?? 0) / data.total_records) * 100) + '%'
            : '—'}
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {labelData.length > 0 && (
          <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
            <h2 className="font-semibold mb-4 text-sm uppercase tracking-wide text-gray-400">Label Distribution</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={labelData} margin={{ left: -20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {labelData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {statusData.length > 0 && (
          <div className="bg-gray-900 border border-white/10 rounded-xl p-5">
            <h2 className="font-semibold mb-4 text-sm uppercase tracking-wide text-gray-400">Dataset Status</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={statusData} margin={{ left: -20 }}>
                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <YAxis tick={{ fontSize: 11, fill: '#9ca3af' }} />
                <Tooltip contentStyle={{ background: '#111827', border: '1px solid rgba(255,255,255,0.1)' }} />
                <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {data.recent_datasets.length > 0 && (
        <div className="bg-gray-900 border border-white/10 rounded-xl overflow-hidden">
          <div className="px-5 py-3 border-b border-white/10">
            <h2 className="font-semibold text-sm uppercase tracking-wide text-gray-400">Recent Datasets</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="text-xs text-gray-500 uppercase">
              <tr>{['Name','Status','Rows','Created'].map(h => <th key={h} className="text-left px-5 py-2">{h}</th>)}</tr>
            </thead>
            <tbody>
              {data.recent_datasets.map(d => (
                <tr key={d._id} className="border-t border-white/5 hover:bg-white/5">
                  <td className="px-5 py-3"><Link to={`/datasets/${d._id}`} className="text-indigo-400 hover:underline">{d.name}</Link></td>
                  <td className="px-5 py-3"><span className="text-xs bg-white/10 px-2 py-0.5 rounded-full">{d.status}</span></td>
                  <td className="px-5 py-3 text-gray-400">{d.row_count.toLocaleString()}</td>
                  <td className="px-5 py-3 text-gray-400">{new Date(d.created_at).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
