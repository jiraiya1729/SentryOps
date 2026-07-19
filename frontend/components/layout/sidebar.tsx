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
  Activity,
  GitCompare,
  Waypoints,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"
import { NavItem } from "./nav-item"
import { GuardianNavItem } from "@/components/guardian/guardian-nav-item"
import { useSidebar } from "@/hooks/use-sidebar"
import { cn } from "@/lib/utils"

const OVERVIEW = [
  { href: "/cluster", label: "Overview", icon: LayoutDashboard },
]

const RESOURCES = [
  { href: "/cluster/pods", label: "Pods", icon: Box },
  { href: "/cluster/nodes", label: "Nodes", icon: Server },
  { href: "/cluster/namespaces", label: "Namespaces", icon: Network },
  { href: "/cluster/deployments", label: "Deployments", icon: Layers },
]

const OBSERVABILITY = [
  { href: "/cluster/logs", label: "Logs", icon: FileText },
  { href: "/cluster/metrics", label: "Metrics", icon: BarChart3 },
  { href: "/cluster/events", label: "Events", icon: Activity },
  { href: "/cluster/traces", label: "Traces", icon: Waypoints },
  { href: "/cluster/changes", label: "Changes", icon: GitCompare },
]

const INTELLIGENCE = [
  { href: "/cluster/alerts", label: "Alerts", icon: Bell },
  { href: "/cluster/dashboards", label: "Dashboards", icon: LayoutDashboard },
]

function SectionLabel({
  label,
  collapsed,
}: {
  label: string
  collapsed: boolean
}) {
  if (collapsed) return <div className="my-1 border-t border-sidebar-border/40" />
  return (
    <p className="mt-3 mb-1 px-3 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground/50">
      {label}
    </p>
  )
}

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

      <nav className="flex-1 flex flex-col p-3 overflow-y-auto">
        <SectionLabel label="Overview" collapsed={collapsed} />
        {OVERVIEW.map((item) => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}

        <SectionLabel label="Resources" collapsed={collapsed} />
        {RESOURCES.map((item) => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}

        <SectionLabel label="Observability" collapsed={collapsed} />
        {OBSERVABILITY.map((item) => (
          <NavItem key={item.href} {...item} collapsed={collapsed} />
        ))}

        <SectionLabel label="Intelligence" collapsed={collapsed} />
        <GuardianNavItem collapsed={collapsed} />
        {INTELLIGENCE.map((item) => (
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
