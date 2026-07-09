"use client"

import { useState, type KeyboardEvent } from "react"
import { Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface ChatInputProps {
  onSend: (message: string) => void
  disabled: boolean
}

export function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [value, setValue] = useState("")

  function submit() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue("")
  }

  function handleKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="flex items-center gap-2 border-t border-border bg-background px-4 py-3">
      <Input
        value={value}
        onChange={e => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about your cluster..."
        disabled={disabled}
        className="flex-1 text-sm"
        autoComplete="off"
      />
      <Button
        size="icon"
        onClick={submit}
        disabled={disabled || !value.trim()}
        aria-label="Send"
      >
        <Send className="size-4" />
      </Button>
    </div>
  )
}
