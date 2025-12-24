"use client";

import { Sparkles, TrendingUp, PieChart, MessageSquare } from "lucide-react";
import { UploadZone } from "./upload-zone";

interface WelcomeViewProps {
  onFileSelect: (file: File) => void;
  onSampleData: () => void;
  isUploading?: boolean;
}

export function WelcomeView({
  onFileSelect,
  onSampleData,
  isUploading = false,
}: WelcomeViewProps) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 sm:p-12">
      {/* Hero */}
      <div className="text-center mb-12 max-w-xl">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brand-gradient mb-6">
          <Sparkles className="w-7 h-7 text-white" />
        </div>
        <h1 className="text-2xl sm:text-3xl font-semibold text-foreground mb-3">
          What story does your data tell?
        </h1>
        <p className="text-muted-foreground">
          Upload a dataset and get clear, trustworthy insights in seconds — 
          no SQL, no Python, no dashboards.
        </p>
      </div>

      {/* Upload Zone */}
      <UploadZone
        onFileSelect={onFileSelect}
        onSampleData={onSampleData}
        isUploading={isUploading}
      />

      {/* What You'll Get */}
      <div className="mt-16 w-full max-w-3xl">
        <h2 className="text-sm font-medium text-muted-foreground text-center mb-6 uppercase tracking-wider">
          What you&apos;ll get
        </h2>
        <div className="grid sm:grid-cols-3 gap-6">
          <div className="flex flex-col items-center text-center p-4">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center mb-3">
              <TrendingUp className="w-5 h-5 text-primary" />
            </div>
            <h3 className="text-sm font-medium text-foreground mb-1">
              Key Insights
            </h3>
            <p className="text-xs text-muted-foreground">
              The most important patterns and trends in your data
            </p>
          </div>

          <div className="flex flex-col items-center text-center p-4">
            <div className="w-10 h-10 rounded-xl bg-accent/10 flex items-center justify-center mb-3">
              <PieChart className="w-5 h-5 text-accent" />
            </div>
            <h3 className="text-sm font-medium text-foreground mb-1">
              Data Summary
            </h3>
            <p className="text-xs text-muted-foreground">
              Column profiles, distributions, and data quality issues
            </p>
          </div>

          <div className="flex flex-col items-center text-center p-4">
            <div className="w-10 h-10 rounded-xl bg-severity-low/10 flex items-center justify-center mb-3">
              <MessageSquare className="w-5 h-5 text-severity-low" />
            </div>
            <h3 className="text-sm font-medium text-foreground mb-1">
              Ask Questions
            </h3>
            <p className="text-xs text-muted-foreground">
              Chat with your data using plain English
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

