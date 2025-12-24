"use client";

import { useState } from "react";
import {
  Plus,
  PanelLeftClose,
  PanelLeft,
  FileSpreadsheet,
  MoreHorizontal,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useSessionStore, Session } from "@/stores/session";
import { cn } from "@/lib/utils";

function SessionItem({
  session,
  isActive,
  onSelect,
}: {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
}) {
  const [showActions, setShowActions] = useState(false);

  return (
    <button
      onClick={onSelect}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      className={cn(
        "w-full group flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150",
        isActive
          ? "bg-brand-gradient text-white"
          : "hover:bg-secondary text-foreground"
      )}
    >
      <FileSpreadsheet
        className={cn(
          "w-4 h-4 shrink-0",
          isActive ? "text-white" : "text-muted-foreground"
        )}
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{session.name}</p>
        {session.dataset && (
          <p
            className={cn(
              "text-xs truncate",
              isActive ? "text-white/70" : "text-muted-foreground"
            )}
          >
            {session.dataset.name}
          </p>
        )}
      </div>
      {showActions && !isActive && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            // Delete action would go here
          }}
          className="p-1 rounded hover:bg-secondary-foreground/10"
        >
          <MoreHorizontal className="w-4 h-4 text-muted-foreground" />
        </button>
      )}
    </button>
  );
}

export function Sidebar() {
  const {
    sidebarOpen,
    toggleSidebar,
    sessions,
    currentSession,
    createSession,
    selectSession,
  } = useSessionStore();

  if (!sidebarOpen) {
    return (
      <div className="h-full p-3">
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleSidebar}
                className="text-muted-foreground hover:text-foreground"
              >
                <PanelLeft className="w-5 h-5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Open sidebar</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    );
  }

  return (
    <aside className="w-72 h-full glass border-r border-border/50 flex flex-col animate-slide-in-left">
      {/* Header */}
      <div className="p-4 flex items-center justify-between border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-gradient flex items-center justify-center">
            <FileSpreadsheet className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-semibold text-foreground">Lumora</span>
        </div>
        <TooltipProvider delayDuration={0}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={toggleSidebar}
                className="text-muted-foreground hover:text-foreground"
              >
                <PanelLeftClose className="w-4 h-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent side="right">Close sidebar</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>

      {/* New Analysis Button */}
      <div className="p-3">
        <Button
          onClick={() => createSession()}
          variant="outline"
          className="w-full justify-start gap-2"
        >
          <Plus className="w-4 h-4" />
          New Analysis
        </Button>
      </div>

      {/* Sessions List */}
      <ScrollArea className="flex-1 px-3">
        <div className="space-y-1 pb-4">
          {sessions.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-muted-foreground">
                No analyses yet
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Upload a dataset to get started
              </p>
            </div>
          ) : (
            <>
              <p className="text-xs font-medium text-muted-foreground px-3 py-2 uppercase tracking-wider">
                Recent
              </p>
              {sessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={currentSession?.id === session.id}
                  onSelect={() => selectSession(session.id)}
                />
              ))}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="p-4 border-t border-border/50">
        <p className="text-xs text-muted-foreground text-center">
          Your data is processed temporarily
          <br />
          and never stored permanently.
        </p>
      </div>
    </aside>
  );
}

