"use client"

import { cn } from "@/lib/utils"

interface ApprovalBadgeProps {
  count: number
  pulse?: boolean
}

export function ApprovalBadge({ count, pulse }: ApprovalBadgeProps) {
  if (count === 0) return null

  return (
    <span
      className={cn(
        "ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-destructive px-1.5 text-[10px] font-bold text-white",
        pulse && "animate-pulse"
      )}
    >
      {count > 99 ? "99+" : count}
    </span>
  )
}
