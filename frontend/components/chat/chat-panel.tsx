"use client"

import { useState } from "react"
import { MessageCircle } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ChatMessages } from "./chat-messages"
import { ChatInput } from "./chat-input"
import { useChat } from "@/hooks/use-chat"

const SUGGESTED_PROMPTS = [
  "What pods are currently failing?",
  "Show me high CPU deployments",
  "Any recent warning events?",
  "What's the cluster resource usage?",
]

export function ChatPanel() {
  const [open, setOpen] = useState(false)
  const { messages, isStreaming, sendMessage, newChat } = useChat()

  return (
    <>
      <div className="fixed bottom-6 right-6 z-50">
        <Button
          variant="default"
          size="icon-lg"
          className="relative rounded-full shadow-lg"
          onClick={() => setOpen(true)}
          aria-label="Open AI Chat"
        >
          <MessageCircle className="size-5" />
          <Badge className="absolute -right-1.5 -top-1.5 h-4 px-1 text-[10px]">
            AI
          </Badge>
        </Button>
      </div>

      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent
          side="right"
          className="flex w-[420px] flex-col gap-0 p-0 sm:max-w-[420px]"
          showCloseButton={true}
        >
          <SheetHeader className="flex flex-row items-center justify-between border-b border-border px-4 pb-3 pt-4">
            <SheetTitle className="flex items-center gap-2">
              <MessageCircle className="size-4 text-primary" />
              AI Assistant
            </SheetTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={newChat}
              disabled={isStreaming}
              className="text-xs text-muted-foreground"
            >
              New Chat
            </Button>
          </SheetHeader>

          <ChatMessages
            messages={messages}
            isStreaming={isStreaming}
            suggestedPrompts={SUGGESTED_PROMPTS}
            onPromptClick={sendMessage}
          />

          <ChatInput onSend={sendMessage} disabled={isStreaming} />
        </SheetContent>
      </Sheet>
    </>
  )
}
