"use client";

import { useState } from "react";
import { Settings, Save, ChevronDown, ChevronRight } from "lucide-react";
import { usePreferences } from "@/hooks/usePreferences";
import StatusIndicator from "./StatusIndicator";

export default function PreferencesPanel() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [localPreference, setLocalPreference] = useState("");
  const { preference, isSaving, isLoaded, error, savePreference } =
    usePreferences();

  const handleToggle = () => {
    if (!isExpanded && isLoaded) {
      setLocalPreference(preference);
    }
    setIsExpanded(!isExpanded);
  };

  const handleSave = async () => {
    const success = await savePreference(localPreference);
    if (success) {
      setIsExpanded(false);
    }
  };

  return (
    <div className="glass rounded-2xl p-5 animate-fade-in-up delay-100">
      <button
        onClick={handleToggle}
        className="w-full flex items-center gap-2 text-base font-semibold"
        style={{ color: "var(--text-primary)" }}
      >
        <span
          className="w-1.5 h-5 rounded-full"
          style={{
            background:
              "linear-gradient(180deg, var(--accent), var(--accent-end))",
          }}
        />
        <Settings className="w-4 h-4" />
        Dietary Preferences
        <span className="ml-auto">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </span>
      </button>

      {isExpanded && (
        <div className="mt-4 space-y-3 animate-fade-in-up">
          <textarea
            value={localPreference}
            onChange={(e) => setLocalPreference(e.target.value)}
            placeholder="e.g., vegetarian, gluten-free, low-carb, spicy..."
            rows={3}
            disabled={isSaving}
            className="glass-input w-full px-3 py-2.5 rounded-xl text-base sm:text-sm resize-none"
          />

          <button
            onClick={handleSave}
            disabled={isSaving || !localPreference.trim()}
            className="btn-success w-full px-4 py-3 min-h-[44px] rounded-xl text-sm flex items-center justify-center gap-2"
          >
            {isSaving ? (
              "Saving..."
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Preferences
              </>
            )}
          </button>

          <StatusIndicator
            status={isSaving ? "loading" : error ? "error" : "idle"}
            message={
              isSaving ? "Saving preferences..." : error || undefined
            }
          />
        </div>
      )}
    </div>
  );
}
