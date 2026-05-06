import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import Layout from '../components/Layout';

const CATEGORIES = ['FRAUD','HARASSMENT','SAFETY','BRIBERY','DISCRIMINATION','OTHER'];
const SEVERITIES  = ['LOW','MEDIUM','HIGH','CRITICAL'];
const STATUSES    = ['SUBMITTED','UNDER_REVIEW','RESOLVED','CLOSED'];

export default function EditReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [form, setForm]     = useState(null);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});

  useEffect(() => {
    api.get(`/api/reports/${id}`).then(r => setForm(r.data));
  }, [id]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm(f => ({ ...f, [name]: value }));
  };

  const handleSave = async () => {
    if (!form.title.trim()) { setErrors({ title: 'Title is required' }); return; }
    setSaving(true);
    try {
      await api.put(`/api/reports/${id}`, form);
      navigate(`/reports/${id}`);
    } catch (err) {
      setErrors({ global: err.response?.data?.message || 'Failed to save' });
    } finally {
      setSaving(false);
    }
  };

  if (!form) return (
    <Layout>
      <div className="flex justify-center items-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    </Layout>
  );

  const inputClass = `w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary`;

  return (
    <Layout>
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Edit Report #{id}</h1>

        {errors.global && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
            {errors.global}
          </div>
        )}

        <div className="bg-white rounded-xl shadow p-6 space-y-4">

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title *</label>
            <input name="title" value={form.title || ''} onChange={handleChange} className={inputClass} />
            {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description *</label>
            <textarea name="description" value={form.description || ''} onChange={handleChange}
              rows={5} className={inputClass} />
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select name="category" value={form.category || ''} onChange={handleChange} className={inputClass}>
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
              <select name="severity" value={form.severity || ''} onChange={handleChange} className={inputClass}>
                {SEVERITIES.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <select name="status" value={form.status || ''} onChange={handleChange} className={inputClass}>
                {STATUSES.map(s => <option key={s}>{s.replace('_', ' ')}</option>)}
              </select>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Resolution Notes</label>
            <textarea name="resolutionNotes" value={form.resolutionNotes || ''} onChange={handleChange}
              rows={3} className={inputClass} placeholder="Add any resolution notes..." />
          </div>

          <div className="flex gap-3 pt-2">
            <button onClick={handleSave} disabled={saving}
              className="bg-primary text-white px-6 py-2 rounded-lg hover:bg-blue-800 transition disabled:opacity-50 text-sm">
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button onClick={() => navigate(`/reports/${id}`)}
              className="border border-gray-300 px-6 py-2 rounded-lg hover:bg-gray-50 text-sm">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}