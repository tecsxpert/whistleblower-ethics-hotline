import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';
import api from '../services/api';
import Layout from '../components/Layout';

function KpiCard({ label, value, color, icon }) {
  return (
    <div className={`bg-white rounded-xl shadow p-6 border-l-4 ${color}`}>
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm text-gray-500">{label}</p>
          <p className="text-3xl font-bold text-gray-800 mt-1">{value ?? '—'}</p>
        </div>
        <span className="text-2xl">{icon}</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    Promise.all([
      api.get('/api/reports/stats').catch(() => ({ data: {} })),
      api.get('/api/reports?page=0&size=5').catch(() => ({ data: { content: [] } })),
    ]).then(([statsRes, reportsRes]) => {
      setStats(statsRes.data);
      setRecent(reportsRes.data.content || []);
    }).finally(() => setLoading(false));
  }, []);

  const chartData = stats?.byCategory
    ? Object.entries(stats.byCategory).map(([name, value]) => ({ name, value }))
    : [];

  if (loading) return (
    <Layout>
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    </Layout>
  );

  return (
    <Layout>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Dashboard</h1>

        {/* 4 KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <KpiCard label="Total Reports"  value={stats?.total}       color="border-blue-500"   icon="📋" />
          <KpiCard label="Under Review"   value={stats?.underReview} color="border-yellow-500" icon="🔍" />
          <KpiCard label="Resolved"       value={stats?.resolved}    color="border-green-500"  icon="✅" />
          <KpiCard label="Critical"       value={stats?.critical}    color="border-red-500"    icon="🚨" />
        </div>

        {/* Chart */}
        {chartData.length > 0 && (
          <div className="bg-white rounded-xl shadow p-6 mb-6">
            <h2 className="font-semibold text-gray-700 mb-4">Reports by Category</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={chartData}>
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="value" fill="#1B4F8A" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Recent Reports */}
        <div className="bg-white rounded-xl shadow">
          <div className="p-4 border-b flex justify-between items-center">
            <h2 className="font-semibold text-gray-700">Recent Reports</h2>
            <button
              onClick={() => navigate('/reports')}
              className="text-primary text-sm hover:underline"
            >
              View all →
            </button>
          </div>
          {recent.length === 0 ? (
            <p className="text-center py-8 text-gray-400">No reports yet</p>
          ) : (
            <div className="divide-y">
              {recent.map(r => (
                <div
                  key={r.id}
                  className="px-4 py-3 flex justify-between items-center hover:bg-gray-50 cursor-pointer transition"
                  onClick={() => navigate(`/reports/${r.id}`)}
                >
                  <div>
                    <p className="font-medium text-sm text-gray-800">{r.title}</p>
                    <p className="text-xs text-gray-400">
                      {r.category} · {new Date(r.createdAt).toLocaleDateString()}
                    </p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded-full ${
                    r.status === 'SUBMITTED'    ? 'bg-blue-100 text-blue-700' :
                    r.status === 'UNDER_REVIEW' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {r.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}