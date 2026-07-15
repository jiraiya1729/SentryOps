"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { Shield } from "lucide-react"
import { cn } from "@/lib/utils"
import { ApprovalBadge } from "./approval-badge"
import { useApprovalCount } from "@/hooks/use-approval-count"

interface GuardianNavItemProps {
  collapsed?: boolean
}

export function GuardianNavItem({ collapsed }: GuardianNavItemProps) {
  const pathname = usePathname()
  const { count, hasNew, clearNew } = useApprovalCount()
  const isActive =
    pathname === "/cluster/guardian" ||
    pathname.startsWith("/cluster/guardian/")

  return (
    <Link
      href="/cluster/guardian"
      onClick={clearNew}
      className={cn(
        "relative flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
        "hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
        isActive ? "bg-sidebar-accent text-white" : "text-muted-foreground"
      )}
    >
      <Shield className="h-4 w-4 shrink-0" />
      {!collapsed && (
        <>
          <span>Guardian</span>
          <ApprovalBadge count={count} pulse={hasNew} />
        </>
      )}
      {collapsed && count > 0 && (
        <span
          className={cn(
            "absolute -right-0.5 -top-0.5 flex h-3.5 min-w-3.5 items-center justify-center rounded-full bg-destructive px-0.5 text-[8px] font-bold text-white",
            hasNew && "animate-pulse"
          )}
        >
          {count > 9 ? "9+" : count}
        </span>
      )}
    </Link>
  )
}
