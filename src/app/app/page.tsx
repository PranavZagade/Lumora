import { Suspense } from "react";
import { AppContent } from "@/components/app/app-content";

function AppLoadingFallback() {
  return (
    <div className="h-screen flex bg-background-secondary items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 border-2 border-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

export default function AppPage() {
  return (
    <Suspense fallback={<AppLoadingFallback />}>
      <AppContent />
    </Suspense>
  );
}
