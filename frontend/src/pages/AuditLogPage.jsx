import { useState, useEffect } from 'react';
import api from '../services/api';
import Layout from '../components/Layout';

export default function AuditLogPage() {
  const [logs, setLogs]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage]       = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    fetchLogs();
  }, [page]);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/audit-logs?page=${page}&size=15`);
      setLogs(res.data.content || []);
      setTotalPages(res.data.totalPages || 0);
    } catch {
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const getActionColor = (action) => {
    switch(action) {
      case 'CREATE': return 'bg-green-100 text-green-700';
      case 'UPDATE': return 'bg-blue-100 text-blue-700';
      case 'DELETE': return 'bg-red-100 text-red-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  return (
    <Layout>
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Audit Log</h1>

        {loading ? (
          <div className="flex justify-center items-center h-48">
            <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
          </div>
        ) : logs.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-xl">No audit logs yet</p>
            <p className="text-sm mt-2">Logs will appear when reports are created, updated or deleted</p>
          </div>
        ) : (
          <>
            <div className="bg-white rounded-xl shadow overflow-hidden">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    {['Time','Action','Entity','Performed By','IP Address'].map(h => (
                      <th key={h} className="px-4 py-3 text-left text-sm font-semibold text-gray-600">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {logs.map(log => (
                    <tr key={log.id} className="hover:bg-gray-50 transition">
                      <td className="px-4 py-3 text-xs text-gray-500">
                        {new Date(log.createdAt).toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getActionColor(log.action)}`}>
                          {log.action}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {log.entityType} #{log.entityId}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {log.performedBy || '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {log.ipAddress || '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            <div className="flex justify-center gap-2 mt-4">
              <button onClick={() => setPage(p => Math.max(0, p-1))}
                disabled={page === 0}
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