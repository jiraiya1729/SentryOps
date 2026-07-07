"use client"

import {
  LayoutDashboard,
  Box,
  Layers,
  Server,
  Network,
  BarChart3,
  FileText,
  Bell,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { NavItem } from "./nav-item"
import { useSidebar } from "@/hooks/use-sidebar"
import { cn } from "@/lib/utils"

const navigation = [
  { href: "/cluster", label: "Overview", icon: LayoutDashboard },
  { href: "/cluster/pods", label: "Pods", icon: Box },
  { href: "/cluster/deployments", label: "Deployments", icon: Layers },
  { href: "/cluster/nodes", label: "Nodes", icon: Server },
  { href: "/cluster/namespaces", label: "Namespaces", icon: Network },
  { href: "/cluster/metrics", label: "Metrics", icon: BarChart3 },
  { href: "/cluster/logs", label: "Logs", icon: FileText },
  { href: "/cluster/events", label: "Events", icon: Bell },
]

export function Sidebar() {
  const { collapsed, toggle } = useSidebar()

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col border-r border-sidebar-border bg-sidebar h-screen sticky top-0 transition-all duration-200",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <div className="flex items-center gap-2 px-4 h-14 border-b border-sidebar-border">
        <div className="flex items-center justify-center w-7 h-7 rounded-md bg-primary">
          <span className="text-xs font-bold text-white">S</span>
        </div>
        {!collapsed && (
          <span className="text-sm font-semibold tracking-tight">
            SentryOps
          </span>
        )}
      </div>

      <nav className="flex-1 flex flex-col gap-1 p-3">
        {navigation.map((item) => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}
      </nav>

      <div className="p-3 border-t border-sidebar-border">
        <button
          onClick={toggle}
          className="flex items-center gap-3 rounded-md px-3 py-2 text-sm text-muted-foreground hover:text-white hover:bg-sidebar-accent w-full transition-colors"
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4 shrink-0" />
          ) : (
            <>
              <PanelLeftClose className="h-4 w-4 shrink-0" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}
