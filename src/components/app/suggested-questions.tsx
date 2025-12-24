"use client";

import { useState } from "react";
import { MessageSquare, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SuggestedQuestion } from "@/lib/api";

interface SuggestedQuestionsProps {
  questions: SuggestedQuestion[];
  onSelect: (question: SuggestedQuestion) => void;
}

// Priority: time > category > quality > numeric
const TYPE_ORDER: Array<SuggestedQuestion["type"]> = [
  "time",
  "category",
  "quality",
  "numeric",
];

const TYPE_LABELS: Record<SuggestedQuestion["type"], string> = {
  time: "Time-based questions",
  category: "Category comparisons",
  quality: "Data quality & coverage",
  numeric: "Numeric distribution",
};

export function SuggestedQuestions({
  questions,
  onSelect,
}: SuggestedQuestionsProps) {
  const [showAll, setShowAll] = useState(false);

  if (questions.length === 0) return null;

  // Rank by type priority, then by type/name/id for stability.
  const sorted = [...questions].sort((a, b) => {
    const pa = TYPE_ORDER.indexOf(a.type);
    const pb = TYPE_ORDER.indexOf(b.type);
    if (pa !== pb) return pa - pb;
    if (a.type !== b.type) return a.type.localeCompare(b.type);
    if (a.column !== b.column) return a.column.localeCompare(b.column);
    return a.id.localeCompare(b.id);
  });

  const visible = showAll ? sorted : sorted.slice(0, 4);

  // Group by type
  const byType: Record<string, SuggestedQuestion[]> = {};
  for (const q of visible) {
    if (!byType[q.type]) byType[q.type] = [];
    byType[q.type].push(q);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <MessageSquare className="w-4 h-4 text-muted-foreground" />
        <h3 className="text-sm font-medium text-muted-foreground">
          Suggested questions
        </h3>
      </div>

      <div className="space-y-4">
        {TYPE_ORDER.map((type) => {
          const items = byType[type] || [];
          if (items.length === 0) return null;
          return (
            <div key={type} className="space-y-2">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                {TYPE_LABELS[type]}
              </p>
              <div className="grid sm:grid-cols-2 gap-2">
                {items.map((q) => (
                  <button
                    key={q.id}
                    onClick={() => onSelect(q)}
                    className={cn(
                      "group flex items-center gap-3 p-3 rounded-xl text-left",
                      "bg-secondary/50 hover:bg-secondary transition-all duration-150",
                      "border border-transparent hover:border-border/50"
                    )}
                  >
                    <span className="flex-1 text-sm text-foreground">
                      {q.text}
                    </span>
                    <ChevronRight className="w-4 h-4 text-muted-foreground/50 group-hover:text-muted-foreground group-hover:translate-x-0.5 transition-all shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {sorted.length > 4 && (
        <div className="pt-1">
          <button
            onClick={() => setShowAll((prev) => !prev)}
            className={cn(
              "inline-flex items-center gap-2 px-3 py-1.5 rounded-full",
              "text-xs font-medium text-primary bg-primary/5 border border-primary/10",
              "hover:bg-primary/10 transition-colors"
            )}
          >
            {showAll ? "Show fewer questions" : "Show more questions"}
            <span className="text-[10px] text-muted-foreground">
              {showAll ? "" : `${sorted.length - 4} more`}
            </span>
          </button>
        </div>
      )}
    </div>
  );
}


