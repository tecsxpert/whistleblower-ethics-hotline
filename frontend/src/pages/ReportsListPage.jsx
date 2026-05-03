import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import Layout from '../components/Layout';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';

export default function ReportsListPage() {
  const [reports, setReports]           = useState([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState('');
  const [page, setPage]                 = useState(0);
  const [totalPages, setTotalPages]     = useState(0);
  const [search, setSearch]             = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo]     = useState('');
  const searchTimer = useRef(null);
  const navigate = useNavigate();

  useEffect(() => { fetchReports(); }, [page, statusFilter]);

  const fetchReports = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({ page, size: 10 });
      if (search)       params.append('q', search);
      if (statusFilter) params.append('status', statusFilter);
      if (dateFrom) params.append('dateFrom', dateFrom);
      if (dateTo)   params.append('dateTo', dateTo);
      const res = await api.get(`/api/reports?${params}`);
      setReports(res.data.content || []);
      setTotalPages(res.data.totalPages || 0);
    } catch {
      setError('Failed to load reports.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearch = (val) => {
    setSearch(val);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => { setPage(0); fetchReports(); }, 400);
  };

  return (
    <Layout>
      <div className="p-6">
        {/* Header */}
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold text-gray-800">Ethics Reports</h1>
          <div className="flex gap-2">
            <button
              onClick={() => window.open('http://localhost:8080/api/reports/export', '_blank')}
              className="border border-primary text-primary px-4 py-2 rounded-lg hover:bg-blue-50 text-sm transition"
            >
              📥 Export CSV
            </button>
            <button
              onClick={() => navigate('/reports/new')}
              className="bg-primary text-white px-4 py-2 rounded-lg hover:bg-blue-800 text-sm transition"
            >
              + New Report
            </button>
          </div>
        </div>

        {/* Search + Filter */}
        <div className="flex gap-3 mb-4">
          <input
            value={search}
            onChange={e => handleSearch(e.target.value)}
            placeholder="Search reports..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          />
          <select
            value={statusFilter}
            onChange={e => { setStatusFilter(e.target.value); setPage(0); }}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
          >
            <option value="">All Statuses</option>
            <option value="SUBMITTED">Submitted</option>
            <option value="UNDER_REVIEW">Under Review</option>
            <option value="RESOLVED">Resolved</option>
            <option value="CLOSED">Closed</option>
          </select>
          <input
  type="date"
  value={dateFrom}
  onChange={e => { setDateFrom(e.target.value); setPage(0); }}
  className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
/>
<input
  type="date"
  value={dateTo}
  onChange={e => { setDateTo(e.target.value); setPage(0); }}
  className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary"
/>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex justify-center items-center h-48">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-xl">No reports found</p>
            <p className="mt-2 text-sm">Create the first report using the button above</p>
          </div>
        ) : (
          <>
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {['ID','Title','Category','Severity','Status','Date','Actions'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-sm font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {reports.map(r => (
                    <tr key={r.id} className="hover:bg-gray-50 transition">
                      <td className="px-4 py-3 text-sm text-gray-500">#{r.id}</td>
                      <td className="px-4 py-3">
                        <span
                          className="font-medium text-primary cursor-pointer hover:underline"
                          onClick={() => navigate(`/reports/${r.id}`)}
                        >
                          {r.title}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{r.category}</td>
                      <td className="px-4 py-3"><SeverityBadge severity={r.severity} /></td>
                      <td className="px-4 py-3"><StatusBadge status={r.status} /></td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {new Date(r.createdAt).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3 flex gap-3">
                        <button onClick={() => navigate(`/reports/${r.id}`)}
                          className="text-primary hover:underline text-sm">View</button>
                        <button onClick={() => navigate(`/reports/${r.id}/edit`)}
                          className="text-gray-500 hover:underline text-sm">Edit</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex justify-center gap-2 mt-4">
              <button onClick={() => setPage(p => Math.max(0, p-1))} disabled={page === 0}
                className="px-4 py-2 rounded border disabled:opacity-40 hover:bg-gray-100 text-sm">
                ← Previous
              </button>
              <span className="px-4 py-2 text-sm text-gray-600">
                Page {page + 1} of {totalPages || 1}
              </span>
              <button onClick={() => setPage(p => Math.min(totalPages-1, p+1))}
                disabled={page >= totalPages - 1}
                className="px-4 py-2 rounded border disabled:opacity-40 hover:bg-gray-100 text-sm">
                Next →
              </button>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
}