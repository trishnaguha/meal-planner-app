import { GroceryItem } from "@/lib/types";

interface Props {
  category: string;
  items: GroceryItem[];
}

const CATEGORY_LABELS: Record<string, string> = {
  produce: "Produce",
  protein: "Protein",
  dairy: "Dairy",
  grains_pantry: "Grains & Pantry",
  spices: "Spices",
};

const CATEGORY_COLORS: Record<string, string> = {
  produce: "bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800",
  protein: "bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800",
  dairy: "bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800",
  grains_pantry: "bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800",
  spices: "bg-purple-50 dark:bg-purple-900/20 border-purple-200 dark:border-purple-800",
};

export default function GroceryCategory({ category, items }: Props) {
  return (
    <div className={`rounded-lg border p-3 ${CATEGORY_COLORS[category] || "bg-gray-50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-700"}`}>
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
        {CATEGORY_LABELS[category] || category}
      </h3>
      <ul className="space-y-1">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-600 dark:text-gray-400">
            {item.name}{" "}
            <span className="text-gray-400 dark:text-gray-500">
              ({item.quantity})
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
