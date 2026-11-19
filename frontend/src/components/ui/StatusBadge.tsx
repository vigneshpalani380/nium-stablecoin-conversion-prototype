const VARIANTS: Record<string, { cls: string; label: string; icon: string }> = {
  COMPLETED: { cls: 'badge-success', label: 'Completed', icon: '✓' },
  RESERVED: { cls: 'badge-warning', label: 'Processing', icon: '…' },
  FAILED: { cls: 'badge-error', label: 'Failed — funds released', icon: '✕' },
  REVIEW_REQUIRED: { cls: 'badge-warning', label: 'Under review', icon: '!' },
  OPEN: { cls: 'badge-neutral', label: 'Open', icon: '○' },
  EXPIRED: { cls: 'badge-error', label: 'Expired', icon: '✕' },
}

/** Status is always conveyed by text (and an icon), never by colour alone. */
export function StatusBadge({ status }: { status: string }) {
  const v = VARIANTS[status] ?? { cls: 'badge-neutral', label: status, icon: '' }
  return (
    <span className={`badge ${v.cls}`}>
      <span aria-hidden="true">{v.icon}</span>
      {v.label}
    </span>
  )
}
