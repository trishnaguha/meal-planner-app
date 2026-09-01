"use client";

import { useState } from "react";
import { FileText } from "lucide-react";
import FileDropZone from "./FileDropZone";
import StatusIndicator from "./StatusIndicator";
import { useMealHistory } from "@/hooks/useMealHistory";
import { UploadResponse } from "@/lib/types";

interface Props {
  onUploadComplete: (response: UploadResponse) => void;
}

export default function MealHistoryPanel({ onUploadComplete }: Props) {
  const [pasteText, setPasteText] = useState("");
  const { uploadFile, uploadText, isUploading, uploadedFiles, totalMealsIndexed, error } =
    useMealHistory();

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
    <div className="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-200 dark:border-gray-700 p-5">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        Meal History Input
      </h2>

      <FileDropZone onFileSelect={handleFileSelect} disabled={isUploading} />

      <div className="mt-4">
        <textarea
          value={pasteText}
          onChange={(e) => setPasteText(e.target.value)}
          placeholder="Or paste your meal notes here..."
          rows={4}
          disabled={isUploading}
          className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white placeholder-gray-400 text-sm resize-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent disabled:opacity-50"
        />
      </div>

      <button
        onClick={handleSubmit}
        disabled={isUploading || !pasteText.trim()}
        className="mt-3 w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {isUploading ? "Analysing..." : "Upload & Analyse"}
      </button>

      <StatusIndicator
        status={isUploading ? "loading" : error ? "error" : "idle"}
        message={isUploading ? "Processing meal notes..." : error || undefined}
      />

      {uploadedFiles.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
          <h3 className="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">
            Uploaded History
          </h3>
          <ul className="space-y-1">
            {uploadedFiles.map((file, i) => (
              <li key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <FileText className="w-4 h-4 text-emerald-500" />
                {file.name}
              </li>
            ))}
          </ul>
          <p className="mt-2 text-xs text-gray-500">
            {totalMealsIndexed} meals indexed
          </p>
        </div>
      )}
    </div>
  );
}
