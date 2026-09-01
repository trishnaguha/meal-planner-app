"use client";

import { useCallback } from "react";
import { useDropzone } from "react-dropzone";
import { Upload } from "lucide-react";

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
      className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors
        ${isDragActive ? "border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20" : "border-gray-300 dark:border-gray-600 hover:border-emerald-400"}
        ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
    >
      <input {...getInputProps()} />
      <Upload className="w-8 h-8 mx-auto mb-2 text-gray-400" />
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {isDragActive
          ? "Drop file here..."
          : "Drop files here or click to upload"}
      </p>
      <p className="text-xs text-gray-400 mt-1">.txt .csv .json .pdf</p>
    </div>
  );
}
