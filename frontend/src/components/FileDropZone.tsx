"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileUp } from "lucide-react";

interface Props {
  onFileSelect: (file: File) => void;
  disabled?: boolean;
}

const ACCEPTED = {
  "text/plain": [".txt"],
  "text/csv": [".csv"],
  "application/json": [".json"],
  "application/pdf": [".pdf"],
};

export default function FileDropZone({ onFileSelect, disabled }: Props) {
  const onDrop = useCallback(
    (accepted: File[]) => {
      if (accepted.length > 0) onFileSelect(accepted[0]);
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: ACCEPTED,
    maxFiles: 1,
    disabled,
  });

  return (
    <div
      {...getRootProps()}
      className={`drop-zone rounded-xl p-5 text-center cursor-pointer transition-all duration-300 ${
        isDragActive ? "drop-zone-active" : ""
      } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} />
      <div
        className="w-10 h-10 rounded-full mx-auto mb-3 flex items-center justify-center transition-transform duration-300"
        style={{
          background: isDragActive ? "var(--accent-glow)" : "var(--glass-bg)",
          border: "1px solid var(--glass-border)",
          transform: isDragActive ? "scale(1.1)" : "scale(1)",
        }}
      >
        {isDragActive ? (
          <FileUp className="w-5 h-5" style={{ color: "var(--accent)" }} />
        ) : (
          <Upload className="w-5 h-5" style={{ color: "var(--text-tertiary)" }} />
        )}
      </div>
      <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
        {isDragActive ? "Drop to upload" : "Drop files here or click to browse"}
      </p>
      <p className="text-xs mt-1" style={{ color: "var(--text-tertiary)" }}>
        .txt .csv .json .pdf
      </p>
    </div>
  );
}
