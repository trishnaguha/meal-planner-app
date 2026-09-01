"use client";

import { useState } from "react";
import { Copy, Check, ShoppingCart } from "lucide-react";
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
        const items = g.items
          .map((item) => `  - ${item.name} (${item.quantity})`)
          .join("\n");
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
      className={`glass rounded-2xl p-5 animate-fade-in-up delay-200 transition-opacity duration-300 ${
        isTentative ? "opacity-60" : "opacity-100"
      }`}
    >
      <div className="flex items-center justify-between mb-4">
        <h2
          className="text-base font-semibold flex items-center gap-2"
          style={{ color: "var(--text-primary)" }}
        >
          <span
            className="w-1.5 h-5 rounded-full"
            style={{
              background:
                "linear-gradient(180deg, var(--accent), var(--accent-end))",
            }}
          />
          Shopping List
          {isTentative && (
            <span
              className="text-[10px] font-normal uppercase tracking-wider ml-1 px-2 py-0.5 rounded-full"
              style={{
                color: "var(--text-tertiary)",
                background: "var(--glass-bg)",
                border: "1px solid var(--glass-border)",
              }}
            >
              tentative
            </span>
          )}
        </h2>
        <button
          onClick={copyToClipboard}
          disabled={isTentative}
          className="btn-glass flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" style={{ color: "var(--success)" }} />
              <span style={{ color: "var(--success)" }}>Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy
            </>
          )}
        </button>
      </div>

      {groceryList.length === 0 ? (
        <div className="text-center py-10">
          <ShoppingCart
            className="w-10 h-10 mx-auto mb-3"
            style={{ color: "var(--text-tertiary)" }}
          />
          <p className="text-sm" style={{ color: "var(--text-tertiary)" }}>
            Your shopping list will appear here
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
          {grouped.map(({ category, items }, index) => (
            <GroceryCategory
              key={category}
              category={category}
              items={items}
              index={index}
            />
          ))}
        </div>
      )}
    </div>
  );
}
