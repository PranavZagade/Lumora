"use client";

import { useState, useRef, useEffect, KeyboardEvent } from "react";
import { Send, Paperclip } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload?: () => void;
  disabled?: boolean;
  placeholder?: string;
  showUpload?: boolean;
}

export function ChatInput({
  onSend,
  onFileUpload,
  disabled = false,
  placeholder = "Ask a question about your data...",
  showUpload = false,
}: ChatInputProps) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [value]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (trimmed && !disabled) {
      onSend(trimmed);
      setValue("");
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="glass rounded-2xl p-2 shadow-soft">
      <div className="flex items-end gap-2">
        {showUpload && (
          <TooltipProvider delayDuration={0}>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onFileUpload}
                  className="text-muted-foreground hover:text-foreground shrink-0 mb-0.5"
                >
                  <Paperclip className="w-5 h-5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Upload a file</TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
        
        <Textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            "flex-1 min-h-[44px] max-h-[200px] resize-none border-0 bg-transparent",
            "focus-visible:ring-0 focus-visible:ring-offset-0",
            "placeholder:text-muted-foreground/60 text-foreground",
            "py-3 px-2"
          )}
        />
        
        <Button
          onClick={handleSubmit}
          disabled={disabled || !value.trim()}
          variant="gradient"
          size="icon"
          className={cn(
            "shrink-0 mb-0.5 transition-all duration-200",
            !value.trim() && "opacity-50"
          )}
        >
          <Send className="w-4 h-4" />
        </Button>
      </div>
    </div>
  );
}



