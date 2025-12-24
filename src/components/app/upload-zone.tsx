"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { Upload, FileSpreadsheet, AlertCircle, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface UploadZoneProps {
  onFileSelect: (file: File) => void;
  onSampleData?: () => void;
  isUploading?: boolean;
}

export function UploadZone({
  onFileSelect,
  onSampleData,
  isUploading = false,
}: UploadZoneProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[], rejectedFiles: unknown[]) => {
      setError(null);

      if (rejectedFiles.length > 0) {
        setError("Please upload a CSV or Excel file.");
        return;
      }

      if (acceptedFiles.length > 0) {
        const file = acceptedFiles[0];
        
        // Validate file size (max 50MB)
        if (file.size > 50 * 1024 * 1024) {
          setError("File size must be under 50MB.");
          return;
        }
        
        onFileSelect(file);
      }
    },
    [onFileSelect]
  );

  const { getRootProps, getInputProps, isDragActive, isDragReject } =
    useDropzone({
      onDrop,
      accept: {
        "text/csv": [".csv"],
        "application/vnd.ms-excel": [".xls"],
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [
          ".xlsx",
        ],
      },
      maxFiles: 1,
      disabled: isUploading,
    });

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div
        {...getRootProps()}
        className={cn(
          "relative border-2 border-dashed rounded-2xl p-12 transition-all duration-200 cursor-pointer",
          "bg-background hover:bg-secondary/50",
          isDragActive && !isDragReject && "border-primary bg-primary/5",
          isDragReject && "border-destructive bg-destructive/5",
          isUploading && "pointer-events-none opacity-60",
          error && "border-destructive",
          !isDragActive && !error && "border-border hover:border-primary/50"
        )}
      >
        <input {...getInputProps()} />

        <div className="flex flex-col items-center text-center">
          {/* Icon */}
          <div
            className={cn(
              "w-16 h-16 rounded-2xl flex items-center justify-center mb-6 transition-colors",
              isDragActive && !isDragReject
                ? "bg-primary/10"
                : isDragReject
                ? "bg-destructive/10"
                : "bg-secondary"
            )}
          >
            {isUploading ? (
              <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            ) : isDragReject ? (
              <AlertCircle className="w-8 h-8 text-destructive" />
            ) : (
              <Upload
                className={cn(
                  "w-8 h-8",
                  isDragActive ? "text-primary" : "text-muted-foreground"
                )}
              />
            )}
          </div>

          {/* Text */}
          <h3 className="text-lg font-medium text-foreground mb-2">
            {isUploading
              ? "Uploading..."
              : isDragActive
              ? "Drop your file here"
              : "Upload your dataset"}
          </h3>
          <p className="text-sm text-muted-foreground mb-1">
            {isUploading
              ? "Please wait while we process your file"
              : "Drag and drop a CSV or Excel file, or click to browse"}
          </p>
          <p className="text-xs text-muted-foreground">
            Supports CSV, XLS, XLSX up to 50MB
          </p>

          {/* Error */}
          {error && (
            <div className="mt-4 flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="w-4 h-4" />
              {error}
            </div>
          )}
        </div>
      </div>

      {/* Sample Data Option */}
      {onSampleData && !isUploading && (
        <div className="mt-6 text-center">
          <p className="text-sm text-muted-foreground mb-3">
            Don&apos;t have a dataset handy?
          </p>
          <Button variant="outline" onClick={onSampleData} className="gap-2">
            <FileSpreadsheet className="w-4 h-4" />
            Try with Sample Data
          </Button>
        </div>
      )}

      {/* Privacy Note */}
      <div className="mt-8 flex items-center justify-center gap-2 text-xs text-muted-foreground">
        <CheckCircle2 className="w-4 h-4 text-severity-low" />
        <span>Your data is processed securely and never stored permanently</span>
      </div>
    </div>
  );
}

