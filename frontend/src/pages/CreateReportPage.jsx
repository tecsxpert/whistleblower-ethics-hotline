import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import Layout from '../components/Layout';

const CATEGORIES = ['FRAUD','HARASSMENT','SAFETY','BRIBERY','DISCRIMINATION','OTHER'];
const SEVERITIES  = ['LOW','MEDIUM','HIGH','CRITICAL'];

export default function CreateReportPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors]         = useState({});
  const [form, setForm] = useState({
    title: '', description: '', category: 'OTHER', severity: 'MEDIUM',
    isAnonymous: true, reporterName: '', reporterEmail: '',
    department: '', incidentDate: '', location: '',
  });

  const validate = () => {
    const e = {};
    if (!form.title.trim())       e.title = 'Title is required';
    if (form.title.length > 255)  e.title = 'Max 255 characters';
    if (!form.description.trim()) e.description = 'Description is required';
    if (!form.isAnonymous && !form.reporterName.trim())
      e.reporterName = 'Name required when not anonymous';
    if (!form.isAnonymous && form.reporterEmail && !/\S+@\S+\.\S+/.test(form.reporterEmail))
      e.reporterEmail = 'Invalid email';
    return e;
  };

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target;
    setForm(f => ({ ...f, [name]: type === 'checkbox' ? checked : value }));
    setErrors(er => ({ ...er, [name]: '' }));
  };

  const handleSubmit = async () => {
    const errs = validate();
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setSubmitting(true);
    try {
      const res = await api.post('/api/reports', form);
      navigate(`/reports/${res.data.id}`);
    } catch (err) {
      setErrors({ global: err.response?.data?.message || 'Failed to submit report' });
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass = (name) =>
    `w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary ${errors[name] ? 'border-red-400' : 'border-gray-300'}`;

  return (
    <Layout>
      <div className="p-6 max-w-2xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-800 mb-6">Submit New Report</h1>

        {errors.global && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4 text-sm">
            {errors.global}
          </div>
        )}

        <div className="bg-white rounded-xl shadow p-6 space-y-4">

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Title <span className="text-red-500">*</span></label>
            <input name="title" value={form.title} onChange={handleChange}
              className={inputClass('title')} placeholder="Brief summary of the incident" />
            {errors.title && <p className="text-red-500 text-xs mt-1">{errors.title}</p>}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description <span className="text-red-500">*</span></label>
            <textarea name="description" value={form.description} onChange={handleChange}
              rows={5} className={inputClass('description')}
              placeholder="Describe what happened in detail..." />
            {errors.description && <p className="text-red-500 text-xs mt-1">{errors.description}</p>}
          </div>

          {/* Category + Severity */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select name="category" value={form.category} onChange={handleChange} className={inputClass('category')}>
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Severity</label>
              <select name="severity" value={form.severity} onChange={handleChange} className={inputClass('severity')}>
                {SEVERITIES.map(s => <option key={s}>{s}</option>)}
              </select>
            </div>
          </div>

          {/* Department + Date */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Department</label>
              <input name="department" value={form.department} onChange={handleChange}
                className={inputClass('department')} placeholder="e.g. Finance, HR" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Incident Date</label>
              <input type="date" name="incidentDate" value={form.incidentDate} onChange={handleChange}
                className={inputClass('incidentDate')} />
            </div>
          </div>

          {/* Anonymous toggle */}
          <div className="flex items-center gap-2">
            <input type="checkbox" name="isAnonymous" id="anon"
              checked={form.isAnonymous} onChange={handleChange}
              className="w-4 h-4 accent-primary" />
            <label htmlFor="anon" className="text-sm text-gray-700">Submit anonymously</label>
          </div>

          {/* Reporter info */}
          {!form.isAnonymous && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Name <span className="text-red-500">*</span></label>
                <input name="reporterName" value={form.reporterName} onChange={handleChange}
                  className={inputClass('reporterName')} />
                {errors.reporterName && <p className="text-red-500 text-xs mt-1">{errors.reporterName}</p>}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Your Email</label>
                <input name="reporterEmail" value={form.reporterEmail} onChange={handleChange}
                  className={inputClass('reporterEmail')} />
                {errors.reporterEmail && <p className="text-red-500 text-xs mt-1">{errors.reporterEmail}</p>}
              </div>
            </div>
          )}

          {/* Buttons */}
          <div className="flex gap-3 pt-2">
            <button onClick={handleSubmit} disabled={submitting}
              className="bg-primary text-white px-6 py-2 rounded-lg hover:bg-blue-800 transition disabled:opacity-50 text-sm">
              {submitting ? 'Submitting...' : 'Submit Report'}
            </button>
            <button onClick={() => navigate('/reports')}
              className="border border-gray-300 px-6 py-2 rounded-lg hover:bg-gray-50 text-sm">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </Layout>
  );
}