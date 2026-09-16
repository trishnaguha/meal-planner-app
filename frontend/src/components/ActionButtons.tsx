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
        className={`flex-1 flex items-center justify-center gap-2 px-4 py-3 min-h-[44px] rounded-xl text-sm transition-all duration-200 ${
          approved ? "btn-success" : "btn-accent"
        }`}
      >
        <Check className="w-4 h-4" />
        {approved ? "Approved" : "Approve Plan"}
      </button>
      <button
        onClick={onSwap}
        disabled={disabled || approved}
        className="flex-1 btn-glass flex items-center justify-center gap-2 px-4 py-3 min-h-[44px] rounded-xl text-sm"
      >
        <RefreshCw
          className="w-4 h-4 transition-transform duration-300 group-hover:rotate-180"
        />
        Swap Plan
      </button>
    </div>
  );
}
