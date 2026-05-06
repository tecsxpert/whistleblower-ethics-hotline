import { useState } from 'react';
import api from '../services/api';

export default function FileUpload({ reportId, onSuccess }) {
  const [file, setFile]         = useState(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError]       = useState('');
  const [success, setSuccess]   = useState('');

  const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'application/pdf', 'text/plain'];
  const MAX_SIZE = 5 * 1024 * 1024; // 5MB

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    setError('');
    setSuccess('');

    if (!selected) return;

    if (!ALLOWED_TYPES.includes(selected.type)) {
      setError('Only JPG, PNG, PDF and TXT files are allowed');
      return;
    }

    if (selected.size > MAX_SIZE) {
      setError('File size must be less than 5MB');
      return;
    }

    setFile(selected);
  };

  const handleUpload = async () => {
    if (!file) { setError('Please select a file first'); return; }
    setUploading(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      await api.post(`/api/reports/${reportId}/upload`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setSuccess('File uploaded successfully!');
      setFile(null);
      if (onSuccess) onSuccess();
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="border-2 border-dashed border-gray-300 rounded-xl p-6 text-center">
      <div className="text-3xl mb-2">📎</div>
      <p className="text-sm text-gray-600 mb-4">
        Upload supporting documents (JPG, PNG, PDF, TXT — max 5MB)
      </p>

      <input
        type="file"
        onChange={handleFileChange}
        accept=".jpg,.jpeg,.png,.pdf,.txt"
        className="hidden"
        id="file-input"
      />

      <label
        htmlFor="file-input"
        className="cursor-pointer bg-gray-50 border border-gray-300 text-gray-700 px-4 py-2 rounded-lg text-sm hover:bg-gray-100 transition"
      >
        Choose File
      </label>

      {file && (
        <div className="mt-3 bg-blue-50 rounded-lg p-3 text-left">
          <p className="text-sm text-blue-800 font-medium">📄 {file.name}</p>
          <p className="text-xs text-blue-600">{(file.size / 1024).toFixed(1)} KB</p>
        </div>
      )}

      {error && (
        <div className="mt-3 bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded text-sm">
          {error}
        </div>
      )}

      {success && (
        <div className="mt-3 bg-green-50 border border-green-200 text-green-700 px-3 py-2 rounded text-sm">
          {success}
        </div>
      )}

      {file && !error && (
        <button
          onClick={handleUpload}
          disabled={uploading}
          className="mt-3 bg-primary text-white px-6 py-2 rounded-lg text-sm hover:bg-blue-800 transition disabled:opacity-50"
        >
          {uploading ? 'Uploading...' : 'Upload File'}
        </button>
      )}
    </div>
  );
}