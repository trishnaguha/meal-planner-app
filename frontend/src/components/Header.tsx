import ThemeToggle from "./ThemeToggle";
import { UtensilsCrossed } from "lucide-react";

export default function Header() {
  return (
    <header
      className="sticky top-0 z-50 glass-static"
      style={{ background: "var(--header-bg)" }}
    >
      <div className="max-w-7xl mx-auto flex items-center justify-between px-4 sm:px-6 py-3" style={{ paddingTop: "max(0.75rem, env(safe-area-inset-top))" }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, var(--accent), var(--accent-end))",
            }}
          >
            <UtensilsCrossed className="w-4 h-4 text-white" />
          </div>
          <h1
            className="text-lg font-semibold tracking-tight"
            style={{ color: "var(--text-primary)" }}
          >
            Meal Planner
          </h1>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}
