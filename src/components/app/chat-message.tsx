"use client";

import { User, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ChatMessage as ChatMessageType } from "@/stores/session";
import { InsightCard } from "./insight-card";
import { VisualizationCard } from "./visualization-card";
import type { ChartSpec } from "./chart-renderer";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isSystem = message.role === "system";

  if (isSystem) {
    return (
      <div className="text-center py-4">
        <p className="text-sm text-muted-foreground">{message.content}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "flex gap-4 py-6",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0",
          isUser ? "bg-secondary" : "bg-brand-gradient"
        )}
      >
        {isUser ? (
          <User className="w-4 h-4 text-muted-foreground" />
        ) : (
          <Sparkles className="w-4 h-4 text-white" />
        )}
      </div>

      {/* Content */}
      <div
        className={cn(
          "flex-1 min-w-0 space-y-4",
          isUser ? "text-right" : "text-left"
        )}
      >
        <div
          className={cn(
            "inline-block rounded-2xl px-4 py-3 max-w-[85%]",
            isUser
              ? "bg-primary text-primary-foreground rounded-tr-md"
              : "bg-secondary text-foreground rounded-tl-md"
          )}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {message.content}
          </p>
        </div>

        {/* Insights attached to message */}
        {message.insights && message.insights.length > 0 && (
          <div className="space-y-3 text-left">
            {message.insights.map((insight, index) => (
              <InsightCard key={insight.id} insight={insight} index={index} />
            ))}
          </div>
        )}

        {/* Visualization card - renders below text answer */}
        {message.visualization && (
          <div className="text-left">
            <VisualizationCard spec={message.visualization as unknown as ChartSpec} />
          </div>
        )}

        {/* Timestamp */}
        <p className="text-2xs text-muted-foreground">
          {new Date(message.timestamp).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </p>
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex gap-4 py-6">
      <div className="w-8 h-8 rounded-lg bg-brand-gradient flex items-center justify-center shrink-0">
        <Sparkles className="w-4 h-4 text-white" />
      </div>
      <div className="flex items-center gap-1 py-3 px-4 bg-secondary rounded-2xl rounded-tl-md">
        <div className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-pulse-soft" />
        <div
          className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-pulse-soft"
          style={{ animationDelay: "0.2s" }}
        />
        <div
          className="w-2 h-2 bg-muted-foreground/40 rounded-full animate-pulse-soft"
          style={{ animationDelay: "0.4s" }}
        />
      </div>
    </div>
  );
}



