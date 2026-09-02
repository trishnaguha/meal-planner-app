"use client";

import { useState } from "react";
import { FileText, ChevronRight } from "lucide-react";
import FileDropZone from "./FileDropZone";
import StatusIndicator from "./StatusIndicator";
import { useMealHistory } from "@/hooks/useMealHistory";
import { UploadResponse } from "@/lib/types";

interface Props {
  onUploadComplete: (response: UploadResponse) => void;
  existingMealCount?: number;
}

export default function MealHistoryPanel({ onUploadComplete, existingMealCount = 0 }: Props) {
  const [pasteText, setPasteText] = useState("");
  const {
    uploadFile,
    uploadText,
    isUploading,
    uploadedFiles,
    totalMealsIndexed,
    error,
  } = useMealHistory();

  const handleFileSelect = async (file: File) => {
    const result = await uploadFile(file);
    if (result) onUploadComplete(result);
  };

  const handleSubmit = async () => {
    if (!pasteText.trim()) return;
    const result = await uploadText(pasteText);
    if (result) {
      setPasteText("");
      onUploadComplete(result);
    }
  };

  return (
    <div className="glass rounded-2xl p-5 animate-fade-in-up">
      <h2
        className="text-base font-semibold mb-4 flex items-center gap-2"
        style={{ color: "var(--text-primary)" }}
      >
        <span
          className="w-1.5 h-5 rounded-full"
          style={{
            background: "linear-gradient(180deg, var(--accent), var(--accent-end))",
          }}
        />
        Meal History
      </h2>

      <FileDropZone onFileSelect={handleFileSelect} disabled={isUploading} />

      <div className="mt-4">
        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder="Or paste your meal notes here..."
          rows={4}
          disabled={isUploading}
          className="glass-input w-full px-3 py-2.5 rounded-xl text-sm resize-none"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={isUploading || !pasteText.trim()}
        className="btn-accent mt-3 w-full px-4 py-2.5 rounded-xl text-sm flex items-center justify-center gap-2"
      >
        {isUploading ? (
          "Analysing..."
        ) : (
          <>
            Upload & Analyse
            <ChevronRight className="w-4 h-4" />
          </>
        )}
      </button>

      <StatusIndicator
        status={isUploading ? "loading" : error ? "error" : "idle"}
        message={isUploading ? "Processing meal notes..." : error || undefined}
      />

      {(uploadedFiles.length > 0 || existingMealCount > 0) && (
        <div
          className="mt-4 pt-4"
          style={{ borderTop: "1px solid var(--glass-border)" }}
        >
          <h3
            className="text-xs font-medium uppercase tracking-wider mb-2"
            style={{ color: "var(--text-tertiary)" }}
          >
            {uploadedFiles.length > 0 ? "Uploaded History" : "Saved History"}
          </h3>
          {uploadedFiles.length > 0 && (
            <ul className="space-y-1.5">
              {uploadedFiles.map((file, i) => (
                <li
                  key={i}
                  className="flex items-center gap-2 text-sm"
                  style={{ color: "var(--text-secondary)" }}
                >
                  <FileText className="w-3.5 h-3.5" style={{ color: "var(--accent)" }} />
                  <span className="truncate">{file.name}</span>
                </li>
              ))}
            </ul>
          )}
          <div
            className="mt-3 flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg"
            style={{
              background: "var(--accent-glow)",
              color: "var(--accent)",
            }}
          >
            <span className="font-semibold">{totalMealsIndexed || existingMealCount}</span>
            <span>meals indexed</span>
          </div>
        </div>
      )}
    </div>
  );
}
