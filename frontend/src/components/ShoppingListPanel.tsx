"use client";

import { useState } from "react";
import { Copy, Check } from "lucide-react";
import GroceryCategory from "./GroceryCategory";
import { GroceryItem, AppState } from "@/lib/types";

interface Props {
  groceryList: GroceryItem[];
  appState: AppState;
}

const CATEGORY_ORDER = ["produce", "protein", "dairy", "grains_pantry", "spices"];

export default function ShoppingListPanel({ groceryList, appState }: Props) {
  const [copied, setCopied] = useState(false);

  if (appState === "idle" || appState === "uploading" || appState === "ready") {
    return null;
  }

  const grouped = CATEGORY_ORDER.map((cat) => ({
    category: cat,
    items: groceryList.filter((item) => item.category === cat),
  })).filter((g) => g.items.length > 0);

  const uncategorized = groceryList.filter(
    (item) => !CATEGORY_ORDER.includes(item.category)
  );
  if (uncategorized.length > 0) {
    grouped.push({ category: "other", items: uncategorized });
  }

  const copyToClipboard = async () => {
    const text = grouped
      .map((g) => {
        const header = g.category.charAt(0).toUpperCase() + g.category.slice(1);
        const items = g.items.map((item) => `  - ${item.name} (${item.quantity})`).join("\n");
        return `${header}:\n${items}`;
      })
      .join("\n\n");

    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isTentative = appState !== "approved";

  return (
    <div
      className={`bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5 ${isTentative ? "opacity-75" : ""}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          Shopping List
          {isTentative && (
            <span className="ml-2 text-xs font-normal text-gray-400">(tentative)</span>
          )}
        </h2>
        <button
          onClick={copyToClipboard}
          disabled={isTentative}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white border border-gray-300 dark:border-gray-600 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" /> Copied
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" /> Copy List
            </>
          )}
        </button>
      </div>

      {groceryList.length === 0 ? (
        <p className="text-center text-gray-500 py-6 text-sm">
          Shopping list will appear here after plan is generated
        </p>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {grouped.map(({ category, items }) => (
            <GroceryCategory key={category} category={category} items={items} />
          ))}
        </div>
      )}
    </div>
  );
}
