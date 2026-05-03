const SEV_COLORS = {
  LOW: 'bg-green-100 text-green-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  HIGH: 'bg-orange-100 text-orange-800',
  CRITICAL: 'bg-red-100 text-red-800',
};

export default function SeverityBadge({ severity }) {
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${SEV_COLORS[severity] || 'bg-gray-100'}`}>
      {severity}
    </span>
  );
}