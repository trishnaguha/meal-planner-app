"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export function usePreferences() {
  const [preference, setPreference] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getPreferences()
      .then((data) => {
        setPreference(data.preference || "");
        setIsLoaded(true);
      })
      .catch(() => {
        setIsLoaded(true);
      });
  }, []);

  const savePreference = async (newPreference: string) => {
    setIsSaving(true);
    setError(null);
    try {
      await api.savePreferences(newPreference);
      setPreference(newPreference);
      return true;
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to save preference"
      );
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  return {
    preference,
    isSaving,
    isLoaded,
    error,
    savePreference,
  };
}
