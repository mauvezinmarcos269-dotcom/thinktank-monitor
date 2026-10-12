'use client';

type ActiveFilterItem = {
  key: string;
  label: string;
  onClear: () => void;
};

type ActiveFilterSummaryProps = {
  items: ActiveFilterItem[];
  loading: boolean;
  onResetFilters: () => void;
};

export function ActiveFilterSummary({
  items,
  loading,
  onResetFilters,
}: ActiveFilterSummaryProps) {
  if (items.length === 0) {
    return null;
  }

  return (
    <div className="active-filter-summary" aria-label="当前筛选条件">
      <span>当前筛选</span>
      <div>
        {items.map((item) => (
          <button
            key={item.key}
            type="button"
            className="active-filter-chip"
            onClick={item.onClear}
            disabled={loading}
            title={`清除${item.label}`}
          >
            {item.label}
            <span aria-hidden="true">×</span>
          </button>
        ))}
      </div>
      <button type="button" onClick={onResetFilters} disabled={loading}>
        清空全部筛选
      </button>
    </div>
  );
}

export type { ActiveFilterItem };
