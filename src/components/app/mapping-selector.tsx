"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
// Simple select using native HTML select for now
import { Check } from "lucide-react";

interface MappingSelectorProps {
  missingConcepts: string[];
  availableColumns: string[];
  onSave: (mappings: Record<string, string>) => Promise<void>;
  onCancel?: () => void;
}

export function MappingSelector({
  missingConcepts,
  availableColumns,
  onSave,
  onCancel,
}: MappingSelectorProps) {
  const [selectedMappings, setSelectedMappings] = useState<
    Record<string, string>
  >({});
  const [isSaving, setIsSaving] = useState(false);

  const handleSelect = (concept: string, column: string) => {
    setSelectedMappings((prev) => ({
      ...prev,
      [concept]: column,
    }));
  };

  const handleSave = async () => {
    // Check if all concepts are mapped
    const allMapped = missingConcepts.every(
      (concept) => selectedMappings[concept]
    );

    if (!allMapped) {
      return; // Don't save if not all mapped
    }

    setIsSaving(true);
    try {
      await onSave(selectedMappings);
    } finally {
      setIsSaving(false);
    }
  };

  const allMapped = missingConcepts.every(
    (concept) => selectedMappings[concept]
  );

  return (
    <div className="space-y-4 p-4 bg-secondary/50 rounded-lg border border-border">
      <div className="space-y-2">
        <p className="text-sm font-medium text-foreground">
          Map concepts to columns
        </p>
        <p className="text-xs text-muted-foreground">
          Select which column represents each concept:
        </p>
      </div>

      <div className="space-y-3">
        {missingConcepts.map((concept) => (
          <div key={concept} className="flex items-center gap-3">
            <label className="text-sm font-medium min-w-[100px] capitalize">
              {concept}:
            </label>
            <select
              value={selectedMappings[concept] || ""}
              onChange={(e) => handleSelect(concept, e.target.value)}
              className="flex-1 px-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
            >
              <option value="">Select column...</option>
              {availableColumns.map((col) => (
                <option key={col} value={col}>
                  {col}
                </option>
              ))}
            </select>
            {selectedMappings[concept] && (
              <Check className="w-4 h-4 text-green-600" />
            )}
          </div>
        ))}
      </div>

      <div className="flex gap-2 justify-end pt-2">
        {onCancel && (
          <Button variant="ghost" onClick={onCancel} disabled={isSaving}>
            Cancel
          </Button>
        )}
        <Button
          onClick={handleSave}
          disabled={!allMapped || isSaving}
          variant="gradient"
        >
          {isSaving ? "Saving..." : "Save Mappings"}
        </Button>
      </div>
    </div>
  );
}

