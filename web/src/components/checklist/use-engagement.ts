"use client";
import { useCallback, useEffect, useState } from "react";
import { getEngagement, uploadDocument } from "@/lib/api";
import type { Engagement } from "@/lib/checklist";

/** Loads the current engagement and applies optimistic status changes after uploads. */
export function useEngagement() {
  const [data, setData] = useState<Engagement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reload = useCallback(() => {
    setError(null);
    getEngagement()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    getEngagement()
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, []);

  const upload = useCallback(
    async (itemId: string, file: File, onProgress: (pct: number) => void) => {
      if (!data) return;
      await uploadDocument(data.id, itemId, file, onProgress);
      setData(
        (prev) =>
          prev && {
            ...prev,
            sections: prev.sections.map((s) => ({
              ...s,
              items: s.items.map((i) =>
                i.id === itemId
                  ? {
                      ...i,
                      status: "checking",
                      reason: undefined,
                      files: [
                        ...i.files,
                        {
                          id: crypto.randomUUID(),
                          name: file.name,
                          size: file.size,
                          uploadedAt: new Date().toISOString(),
                        },
                      ],
                    }
                  : i,
              ),
            })),
          },
      );
    },
    [data],
  );

  return { data, error, upload, reload };
}
