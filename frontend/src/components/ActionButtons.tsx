import { Check, RefreshCw } from "lucide-react";

interface Props {
  onApprove: () => void;
  onSwap: () => void;
  disabled?: boolean;
  approved?: boolean;
}

export default function ActionButtons({
  onApprove,
  onSwap,
  disabled,
  approved,
}: Props) {
  return (
    <div className="flex gap-3">
      <button
        onClick={onApprove}
        disabled={disabled || approved}
        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <Check className="w-4 h-4" />
        {approved ? "Approved" : "Approve"}
      </button>
      <button
        onClick={onSwap}
        disabled={disabled || approved}
        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        <RefreshCw className="w-4 h-4" />
        Swap Meal Plan
      </button>
    </div>
  );
}
