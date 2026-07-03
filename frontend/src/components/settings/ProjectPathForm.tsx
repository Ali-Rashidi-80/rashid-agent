"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { toast } from "sonner";
import { fetchProjectPath, saveProjectPath } from "@/lib/session-api";

export function ProjectPathForm() {
  const t = useTranslations("settings");
  const [path, setPath] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchProjectPath().then((value) => {
      if (!cancelled) {
        setPath(value ?? "");
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const onSave = useCallback(async () => {
    if (!path.trim()) {
      return;
    }
    setSaving(true);
    try {
      const saved = await saveProjectPath(path.trim());
      setPath(saved);
      toast.success(t("projectPathSaved"));
    } catch (err) {
      toast.error((err as Error).message);
    } finally {
      setSaving(false);
    }
  }, [path, t]);

  return (
    <div className="space-y-3">
      <label className="block text-sm font-medium" htmlFor="project-path">
        {t("projectPath")}
      </label>
      <input
        id="project-path"
        type="text"
        value={path}
        disabled={loading}
        onChange={(event) => setPath(event.target.value)}
        placeholder={t("projectPathPlaceholder")}
        className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm"
        dir="ltr"
      />
      <button
        type="button"
        onClick={onSave}
        disabled={saving || loading || !path.trim()}
        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
      >
        {saving ? t("saving") : t("saveProjectPath")}
      </button>
    </div>
  );
}
