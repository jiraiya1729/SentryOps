"use client"

import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MobileNav } from "./mobile-nav"
import { useState } from "react"

interface HeaderProps {
  databaseConnected?: boolean
}

export function Header({ databaseConnected = false }: HeaderProps) {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 flex items-center h-14 border-b border-border bg-background px-4 md:px-6">
      <Button
        variant="ghost"
        size="icon"
        className="md:hidden mr-2"
        onClick={() => setMobileOpen(true)}
      >
        <Menu className="h-5 w-5" />
      </Button>

      <div className="flex items-center gap-2 md:hidden">
        <div className="flex items-center justify-center w-6 h-6 rounded-md bg-primary">
          <span className="text-[10px] font-bold text-white">S</span>
        </div>
        <span className="text-sm font-semibold">SentryOps</span>
      </div>

      <div className="flex-1" />

      <div className="flex items-center gap-2">
        <div className="hidden sm:flex items-center gap-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-success" />
            <span>K8s</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className={`w-2 h-2 rounded-full ${databaseConnected ? "bg-success" : "bg-muted-foreground"}`} />
            <span>DB</span>
          </div>
        </div>
      </div>

      <MobileNav open={mobileOpen} onOpenChange={setMobileOpen} />
    </header>
  )
}
