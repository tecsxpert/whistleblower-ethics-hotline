import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import api from '../services/api';
import Layout from '../components/Layout';

const COLORS = ['#1B4F8A','#10B981','#F59E0B','#EF4444','#8B5CF6','#EC4899'];

export default function AnalyticsPage() {
  const [stats, setStats]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [period, setPeriod]   = useState('all');

  useEffect(() => {
    fetchStats();
  }, [period]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/reports/stats?period=${period}`);
      setStats(res.data);
    } catch {
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  const statusData = [
    { name: 'Submitted',    value: stats?.submitted   || 0 },
    { name: 'Under Review', value: stats?.underReview || 0 },
    { name: 'Resolved',     value: stats?.resolved    || 0 },
    { name: 'Closed',       value: stats?.closed      || 0 },
  ];

  const categoryData = stats?.byCategory
    ? Object.entries(stats.byCategory).map(([name, value]) => ({ name, value }))
    : [];

  const severityData = [
    { name: 'Low',      value: stats?.low      || 0 },
    { name: 'Medium',   value: stats?.medium   || 0 },
    { name: 'High',     value: stats?.high     || 0 },
    { name: 'Critical', value: stats?.critical || 0 },
  ];

  return (
    <Layout>
      <div className="p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-2xl font-bold text-gray-800">Analytics</h1>

          {/* Period Selector */}
          <div className="flex gap-2">
            {[
              { value: 'week',  label: 'This Week' },
              { value: 'month', label: 'This Month' },
              { value: 'year',  label: 'This Year' },
              { value: 'all',   label: 'All Time' },
            ].map(p => (
              <button
                key={p.value}
                onClick={() => setPeriod(p.value)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
                  period === p.value
                    ? 'bg-primary text-white'
                    : 'bg-white border border-gray-300 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* KPI Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Total', value: stats?.total, color: 'border-blue-500', icon: '📋' },
            { label: 'Critical', value: stats?.critical, color: 'border-red-500', icon: '🚨' },
            { label: 'Resolved', value: stats?.resolved, color: 'border-green-500', icon: '✅' },
            { label: 'Pending', value: (stats?.submitted || 0) + (stats?.underReview || 0), color: 'border-yellow-500', icon: '⏳' },
          ].map(card => (
            <div key={card.label} className={`bg-white rounded-xl shadow p-4 border-l-4 ${card.color}`}>
              <p className="text-xs text-gray-500">{card.label}</p>
              <p className="text-2xl font-bold text-gray-800 mt-1">{card.value ?? '—'}</p>
              <span className="text-lg">{card.icon}</span>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="flex justify-center items-center h-48">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

            {/* Status Pie */}
            <div className="bg-white rounded-xl shadow p-6">
              <h2 className="font-semibold text-gray-700 mb-4">Reports by Status</h2>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie data={statusData} dataKey="value" nameKey="name"
                    cx="50%" cy="50%" outerRadius={90} label>
                    {statusData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Category Bar */}
            <div className="bg-white rounded-xl shadow p-6">
              <h2 className="font-semibold text-gray-700 mb-4">Reports by Category</h2>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={categoryData}>
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#1B4F8A" radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Severity Bar */}
            <div className="bg-white rounded-xl shadow p-6">
              <h2 className="font-semibold text-gray-700 mb-4">Reports by Severity</h2>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={severityData}>
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" radius={[4,4,0,0]}>
                    {severityData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

          </div>
        )}
      </div>
    </Layout>
  );
}