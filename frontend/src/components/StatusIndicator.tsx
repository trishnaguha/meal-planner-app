import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface Props {
  status: "loading" | "success" | "error" | "idle";
  message?: string;
}

export default function StatusIndicator({ status, message }: Props) {
  if (status === "idle") return null;

  const icons = {
    loading: <Loader2 className="w-4 h-4 animate-spin text-blue-500" />,
    success: <CheckCircle2 className="w-4 h-4 text-emerald-500" />,
    error: <AlertCircle className="w-4 h-4 text-red-500" />,
  };

  const colors = {
    loading: "text-blue-600 dark:text-blue-400",
    success: "text-emerald-600 dark:text-emerald-400",
    error: "text-red-600 dark:text-red-400",
  };

  return (
    <div className={`flex items-center gap-2 text-sm ${colors[status]}`}>
      {icons[status]}
      {message && <span>{message}</span>}
    </div>
  );
}
