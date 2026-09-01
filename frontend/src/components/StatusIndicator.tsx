import { Loader2, CheckCircle2, AlertCircle } from "lucide-react";

interface Props {
  status: "loading" | "success" | "error" | "idle";
  message?: string;
}

export default function StatusIndicator({ status, message }: Props) {
  if (status === "idle") return null;

  const config = {
    loading: {
      icon: <Loader2 className="w-3.5 h-3.5 animate-spin" />,
      bg: "rgba(59, 130, 246, 0.1)",
      border: "rgba(59, 130, 246, 0.2)",
      color: "#60a5fa",
    },
    success: {
      icon: <CheckCircle2 className="w-3.5 h-3.5" />,
      bg: "rgba(52, 211, 153, 0.1)",
      border: "rgba(52, 211, 153, 0.2)",
      color: "#34d399",
    },
    error: {
      icon: <AlertCircle className="w-3.5 h-3.5" />,
      bg: "rgba(248, 113, 113, 0.1)",
      border: "rgba(248, 113, 113, 0.2)",
      color: "#f87171",
    },
  };

  const c = config[status];

  return (
    <div
      className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full mt-3 w-fit"
      style={{
        background: c.bg,
        border: `1px solid ${c.border}`,
        color: c.color,
      }}
    >
      {c.icon}
      {message && <span>{message}</span>}
    </div>
  );
}
