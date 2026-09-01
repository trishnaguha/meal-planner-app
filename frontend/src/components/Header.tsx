import ThemeToggle from "./ThemeToggle";
import { UtensilsCrossed } from "lucide-react";

export default function Header() {
  return (
    <header className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">
      <div className="flex items-center gap-3">
        <UtensilsCrossed className="w-6 h-6 text-emerald-600" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">
          Meal Planner
        </h1>
      </div>
      <ThemeToggle />
    </header>
  );
}
