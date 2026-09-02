import { GroceryItem } from "@/lib/types";

interface Props {
  category: string;
  items: GroceryItem[];
  index: number;
}

const CATEGORY_CONFIG: Record<
  string,
  { label: string; accent: string; glow: string }
> = {
  produce: {
    label: "Produce",
    accent: "#22c55e",
    glow: "rgba(34, 197, 94, 0.08)",
  },
  protein: {
    label: "Protein",
    accent: "#ef4444",
    glow: "rgba(239, 68, 68, 0.08)",
  },
  dairy: {
    label: "Dairy",
    accent: "#3b82f6",
    glow: "rgba(59, 130, 246, 0.08)",
  },
  grains_pantry: {
    label: "Grains & Pantry",
    accent: "#f59e0b",
    glow: "rgba(245, 158, 11, 0.08)",
  },
  spices: {
    label: "Spices",
    accent: "#a855f7",
    glow: "rgba(168, 85, 247, 0.08)",
  },
};

export default function GroceryCategory({ category, items, index }: Props) {
  const config = CATEGORY_CONFIG[category] || {
    label: category.charAt(0).toUpperCase() + category.slice(1),
    accent: "var(--text-tertiary)",
    glow: "var(--glass-bg)",
  };

  return (
    <div
      className="rounded-xl p-3.5 transition-all duration-300 animate-fade-in-up"
      style={{
        background: config.glow,
        border: `1px solid ${config.accent}20`,
        animationDelay: `${index * 80}ms`,
      }}
    >
      <h3 className="text-xs font-semibold uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: config.accent }}
        />
        <span style={{ color: config.accent }}>{config.label}</span>
      </h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li
            key={i}
            className="text-sm leading-relaxed"
            style={{ color: "var(--text-secondary)" }}
          >
            {item.name}{" "}
            <span style={{ color: "var(--text-tertiary)" }}>
              {item.quantity}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
