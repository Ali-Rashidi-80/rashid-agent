"use client";

import { useTranslations } from "next-intl";
import { Check, Eye, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface DiffActionsProps {
  onPreview: () => Promise<boolean>;
  onApply: () => Promise<boolean>;
  isLoading: boolean;
  hasEdits: boolean;
  canApply?: boolean;
}

export function DiffActions({
  onPreview,
  onApply,
  isLoading,
  hasEdits,
  canApply = false,
}: DiffActionsProps) {
  const t = useTranslations("diff");

  if (!hasEdits) {
    return null;
  }

  return (
    <div className="flex items-center gap-2 border-t border-border px-4 py-3">
      <button
        type="button"
        disabled={isLoading}
        onClick={async () => {
          const ok = await onPreview();
          if (ok) {
            toast.success(t("previewDone"));
          } else {
            toast.error(t("previewFailed"));
          }
        }}
        className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-xs font-medium hover:bg-muted disabled:opacity-50"
      >
        {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Eye className="h-3.5 w-3.5" />}
        {t("preview")}
      </button>
      <button
        type="button"
        disabled={isLoading || !canApply}
        onClick={async () => {
          const ok = await onApply();
          if (ok) {
            toast.success(t("applyDone"));
          } else {
            toast.error(t("applyFailed"));
          }
        }}
        className="inline-flex items-center gap-2 rounded-lg bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground disabled:opacity-50"
      >
        {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
        {t("apply")}
      </button>
    </div>
  );
}
