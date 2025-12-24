"use client";

import Link from "next/link";
import { Upload, Play, Shield, Sparkles, Clock, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass">
        <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-brand-gradient flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <span className="text-lg font-semibold text-foreground">Lumora</span>
          </div>
          <Link href="/app">
            <Button variant="gradient" size="sm">
              Open App
            </Button>
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="pt-32 pb-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-secondary text-muted-foreground text-sm mb-8 animate-fade-in">
            <Clock className="w-4 h-4" />
            <span>Understand your data in under 60 seconds</span>
          </div>

          {/* Main Headline */}
          <h1 className="text-4xl sm:text-5xl md:text-6xl font-semibold text-foreground leading-tight tracking-tight mb-6 animate-fade-in-up">
            Upload a dataset.
            <br />
            <span className="text-brand-gradient">Understand what it means.</span>
          </h1>

          {/* Subheadline */}
          <p className="text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto mb-12 animate-fade-in-up" style={{ animationDelay: "0.1s" }}>
            Lumora analyzes your data and tells you what matters — 
            in plain English, not charts and dashboards.
          </p>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-16 animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
            <Link href="/app">
              <Button variant="gradient" size="xl" className="w-full sm:w-auto">
                <Upload className="w-5 h-5" />
                Upload Dataset
              </Button>
            </Link>
            <Link href="/app?sample=true">
              <Button variant="outline" size="xl" className="w-full sm:w-auto">
                <Play className="w-5 h-5" />
                Try with Sample Data
              </Button>
            </Link>
          </div>

          {/* Product Preview */}
          <div className="relative max-w-5xl mx-auto animate-fade-in-up" style={{ animationDelay: "0.3s" }}>
            <div className="relative rounded-2xl overflow-hidden shadow-soft-lg border border-border/50">
              {/* Mock Browser Chrome */}
              <div className="bg-secondary/50 px-4 py-3 flex items-center gap-2 border-b border-border/50">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-severity-high/20" />
                  <div className="w-3 h-3 rounded-full bg-severity-medium/20" />
                  <div className="w-3 h-3 rounded-full bg-severity-low/20" />
                </div>
                <div className="flex-1 mx-4">
                  <div className="max-w-md mx-auto bg-background rounded-md px-3 py-1.5 text-xs text-muted-foreground">
                    lumora.app
                  </div>
                </div>
              </div>
              
              {/* App Preview Content */}
              <div className="bg-background-secondary p-6 sm:p-8">
                <div className="flex gap-6">
                  {/* Sidebar Preview */}
                  <div className="hidden sm:block w-56 shrink-0">
                    <div className="glass rounded-xl p-4 space-y-3">
                      <div className="h-8 bg-brand-gradient/10 rounded-lg" />
                      <div className="h-6 bg-secondary rounded-lg w-3/4" />
                      <div className="h-6 bg-secondary rounded-lg w-2/3" />
                      <div className="h-6 bg-secondary rounded-lg w-4/5" />
                    </div>
                  </div>
                  
                  {/* Main Content Preview */}
                  <div className="flex-1 space-y-4">
                    {/* Insight Card Preview */}
                    <div className="bg-background rounded-xl p-5 shadow-soft">
                      <div className="flex items-start gap-3 mb-3">
                        <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                          <Sparkles className="w-4 h-4 text-primary" />
                        </div>
                        <div className="space-y-2 flex-1">
                          <div className="h-4 bg-foreground/10 rounded w-3/4" />
                          <div className="h-3 bg-muted rounded w-full" />
                          <div className="h-3 bg-muted rounded w-5/6" />
                        </div>
                      </div>
                    </div>
                    
                    {/* Second Card Preview */}
                    <div className="bg-background rounded-xl p-5 shadow-soft">
                      <div className="flex items-start gap-3">
                        <div className="w-8 h-8 rounded-lg bg-accent/10 flex items-center justify-center shrink-0">
                          <div className="w-4 h-4 rounded bg-accent/30" />
                        </div>
                        <div className="space-y-2 flex-1">
                          <div className="h-4 bg-foreground/10 rounded w-2/3" />
                          <div className="h-3 bg-muted rounded w-full" />
                          <div className="h-3 bg-muted rounded w-4/5" />
                        </div>
                      </div>
                    </div>
                    
                    {/* Chat Input Preview */}
                    <div className="glass rounded-xl p-3 flex items-center gap-3 mt-6">
                      <div className="flex-1 h-10 bg-background rounded-lg" />
                      <div className="w-10 h-10 rounded-lg bg-brand-gradient/80" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
            
            {/* Decorative gradient blur */}
            <div className="absolute -bottom-20 left-1/2 -translate-x-1/2 w-96 h-32 bg-brand-gradient opacity-10 blur-3xl rounded-full pointer-events-none" />
          </div>
        </div>
      </main>

      {/* Trust Section */}
      <section className="py-20 px-6 bg-background-secondary border-t border-border/50">
        <div className="max-w-4xl mx-auto">
          <div className="grid sm:grid-cols-3 gap-8">
            {/* Privacy First */}
            <div className="text-center sm:text-left">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-primary/10 mb-4">
                <Shield className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-base font-medium text-foreground mb-2">
                Privacy First
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Your data is processed temporarily and never stored permanently. 
                Raw data is deleted after your session.
              </p>
            </div>

            {/* No Hallucinations */}
            <div className="text-center sm:text-left">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-accent/10 mb-4">
                <Lock className="w-6 h-6 text-accent" />
              </div>
              <h3 className="text-base font-medium text-foreground mb-2">
                No Hallucinations
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                AI never touches your raw data. Every insight is computed deterministically
                and verified before you see it.
              </p>
            </div>

            {/* Instant Understanding */}
            <div className="text-center sm:text-left">
              <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-severity-low/10 mb-4">
                <Clock className="w-6 h-6 text-severity-low" />
              </div>
              <h3 className="text-base font-medium text-foreground mb-2">
                60 Seconds or Less
              </h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Upload your dataset and understand what matters — 
                without learning SQL, Python, or any tool.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-8 px-6 border-t border-border/50">
        <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div className="w-6 h-6 rounded-md bg-brand-gradient flex items-center justify-center">
              <Sparkles className="w-3 h-3 text-white" />
            </div>
            <span className="text-sm font-medium text-foreground">Lumora</span>
          </div>
          <p className="text-sm text-muted-foreground">
            Story-first data understanding.
          </p>
        </div>
      </footer>
    </div>
  );
}
