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
  Shield,
} from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { NavItem } from "./nav-item"

const navigation = [
  { href: "/cluster", label: "Overview", icon: LayoutDashboard },
  { href: "/cluster/pods", label: "Pods", icon: Box },
  { href: "/cluster/deployments", label: "Deployments", icon: Layers },
  { href: "/cluster/nodes", label: "Nodes", icon: Server },
  { href: "/cluster/namespaces", label: "Namespaces", icon: Network },
  { href: "/cluster/metrics", label: "Metrics", icon: BarChart3 },
  { href: "/cluster/logs", label: "Logs", icon: FileText },
  { href: "/cluster/events", label: "Events", icon: Bell },
  { href: "/cluster/guardian", label: "Guardian", icon: Shield },
]

interface MobileNavProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function MobileNav({ open, onOpenChange }: MobileNavProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="left" className="w-64 bg-sidebar border-sidebar-border p-0">
        <SheetHeader className="px-4 h-14 flex justify-center border-b border-sidebar-border">
          <SheetTitle className="flex items-center gap-2">
            <div className="flex items-center justify-center w-7 h-7 rounded-md bg-primary">
              <span className="text-xs font-bold text-white">S</span>
            </div>
            <span className="text-sm font-semibold text-white">SentryOps</span>
          </SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-1 p-3">
          {navigation.map((item) => (
            <NavItem key={item.href} {...item} />
          ))}
        </nav>
      </SheetContent>
    </Sheet>
  )
}
