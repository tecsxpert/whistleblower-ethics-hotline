import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import Layout from '../components/Layout';
import StatusBadge from '../components/StatusBadge';
import SeverityBadge from '../components/SeverityBadge';
import FileUpload from '../components/FileUpload';

function AiCard({ title, content, color, icon }) {
  return (
    <div className={`rounded-xl border ${color} p-5 mb-4`}>
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xl">{icon}</span>
        <h3 className="font-semibold text-gray-800">{title}</h3>
      </div>
      <p className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">{content}</p>
    </div>
  );
}

function AiButton({ label, onClick, disabled, color }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`${color} px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-50 mr-2 mb-2`}
    >
      {label}
    </button>
  );
}

export default function ReportDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [report, setReport]       = useState(null);
  const [loading, setLoading]     = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiStep, setAiStep]       = useState('');

  useEffect(() => {
    api.get(`/api/reports/${id}`)
      .then(r => setReport(r.data))
      .finally(() => setLoading(false));
  }, [id]);

  const triggerAI = async (type) => {
    setAiLoading(true);
    setAiStep(
      type === 'describe'  ? 'Generating AI description...' :
      type === 'recommend' ? 'Getting AI recommendations...' :
      'Generating full AI report...'
    );
    try {
      await api.post(`/api/reports/${id}/ai/${type}`);
      const r = await api.get(`/api/reports/${id}`);
      setReport(r.data);
    } catch {
      setAiStep('AI service unavailable. Please try again.');
    } finally {
      setAiLoading(false);
      setAiStep('');
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Soft delete this report?')) return;
    await api.delete(`/api/reports/${id}`);
    navigate('/reports');
  };

  if (loading) return (
    <Layout>
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    </Layout>
  );

  if (!report) return (
    <Layout>
      <div className="p-6 text-red-500">Report not found.</div>
    </Layout>
  );

  return (
    <Layout>
      <div className="p-6 max-w-4xl mx-auto">

        {/* Top bar */}
        <div className="flex justify-between items-center mb-6">
          <button onClick={() => navigate('/reports')}
            className="text-primary hover:underline text-sm">
            ← Back to Reports
          </button>
          <div className="flex gap-2">
            <button onClick={() => navigate(`/reports/${id}/edit`)}
              className="border border-gray-300 px-4 py-2 rounded-lg text-sm hover:bg-gray-50">
              ✏️ Edit
            </button>
            <button onClick={handleDelete}
              className="border border-red-300 text-red-600 px-4 py-2 rounded-lg text-sm hover:bg-red-50">
              🗑️ Delete
            </button>
          </div>
        </div>

        {/* Report Info */}
        <div className="bg-white rounded-xl shadow p-6 mb-4">
          <div className="flex justify-between items-start mb-4">
            <h1 className="text-xl font-bold text-gray-800 flex-1 mr-4">{report.title}</h1>
            <div className="flex gap-2 shrink-0">
              <SeverityBadge severity={report.severity} />
              <StatusBadge status={report.status} />
            </div>
          </div>
          <p className="text-gray-600 mb-6 leading-relaxed">{report.description}</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-400 text-xs">Category</p>
              <p className="font-medium mt-1">{report.category}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs">Department</p>
              <p className="font-medium mt-1">{report.department || '—'}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs">Incident Date</p>
              <p className="font-medium mt-1">{report.incidentDate || '—'}</p>
            </div>
            <div>
              <p className="text-gray-400 text-xs">Submitted</p>
              <p className="font-medium mt-1">{new Date(report.createdAt).toLocaleDateString()}</p>
            </div>
          </div>
        </div>

        {/* AI Panel */}
        <div className="bg-white rounded-xl shadow p-6 mb-4">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-2xl">🤖</span>
            <h2 className="text-lg font-semibold text-gray-800">AI Analysis</h2>
            {report.aiProcessed && (
              <span className="bg-green-100 text-green-700 text-xs px-2 py-1 rounded-full">
                ✓ AI Processed
              </span>
            )}
            {report.aiFallback && (
              <span className="bg-yellow-100 text-yellow-700 text-xs px-2 py-1 rounded-full">
                ⚠ Fallback Mode
              </span>
            )}
          </div>

          {/* AI Loading Spinner */}
          {aiLoading && (
            <div className="flex items-center gap-3 bg-blue-50 rounded-lg p-4 mb-4">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary shrink-0"></div>
              <div>
                <p className="text-sm font-medium text-blue-800">{aiStep}</p>
                <p className="text-xs text-blue-600 mt-1">This may take a few seconds...</p>
              </div>
            </div>
          )}

          {/* AI Description */}
          {report.aiDescription ? (
            <AiCard
              title="AI Description"
              content={report.aiDescription}
              color="border-blue-200 bg-blue-50"
              icon="📝"
            />
          ) : (
            <AiButton
              label="📝 Generate AI Description"
              onClick={() => triggerAI('describe')}
              disabled={aiLoading}
              color="bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100"
            />
          )}

          {/* AI Recommendations */}
          {report.aiRecommendations ? (
            <AiCard
              title="AI Recommendations"
              content={report.aiRecommendations}
              color="border-green-200 bg-green-50"
              icon="💡"
            />
          ) : (
            <AiButton
              label="💡 Get AI Recommendations"
              onClick={() => triggerAI('recommend')}
              disabled={aiLoading}
              color="bg-green-50 text-green-700 border border-green-200 hover:bg-green-100"
            />
          )}

          {/* AI Full Report */}
          {report.aiReport ? (
            <AiCard
              title="AI Full Report"
              content={report.aiReport}
              color="border-purple-200 bg-purple-50"
              icon="📊"
            />
          ) : (
            <AiButton
              label="📊 Generate Full AI Report"
              onClick={() => triggerAI('report')}
              disabled={aiLoading}
              color="bg-purple-50 text-purple-700 border border-purple-200 hover:bg-purple-100"
            />
          )}

          {/* Regenerate button */}
          {(report.aiDescription || report.aiRecommendations || report.aiReport) && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <button
                onClick={() => triggerAI('describe')}
                disabled={aiLoading}
                className="text-gray-500 hover:text-gray-700 text-xs hover:underline"
              >
                🔄 Regenerate AI Analysis
              </button>
            </div>
          )}
        </div>

        {/* File Upload Section */}
        <div className="bg-white rounded-xl shadow p-6 mt-4">
          <h2 className="text-lg font-semibold text-gray-800 mb-4">📎 Supporting Documents</h2>
          <FileUpload reportId={id} onSuccess={() => console.log('uploaded')} />
        </div>

      </div>
    </Layout>
  );
}