"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { UploadResponse } from "@/lib/types";

interface UploadedFile {
  name: string;
  mealsIndexed: number;
}

export function useMealHistory() {
  const [isUploading, setIsUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [totalMealsIndexed, setTotalMealsIndexed] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = async (file: File): Promise<UploadResponse | null> => {
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await api.uploadMeals(formData);
      setUploadedFiles((prev) => [
        ...prev,
        { name: file.name, mealsIndexed: response.meals_indexed },
      ]);
      setTotalMealsIndexed((prev) => prev + response.meals_indexed);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  const uploadText = async (text: string): Promise<UploadResponse | null> => {
    setIsUploading(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("text", text);
      const response = await api.uploadMeals(formData);
      setUploadedFiles((prev) => [
        ...prev,
        { name: "Pasted text", mealsIndexed: response.meals_indexed },
      ]);
      setTotalMealsIndexed((prev) => prev + response.meals_indexed);
      return response;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      return null;
    } finally {
      setIsUploading(false);
    }
  };

  return { uploadFile, uploadText, isUploading, uploadedFiles, totalMealsIndexed, error };
}
