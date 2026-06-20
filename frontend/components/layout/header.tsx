"use client"

import { Menu } from "lucide-react"
import { Button } from "@/components/ui/button"
import { MobileNav } from "./mobile-nav"
import { useState } from "react"

export function Header() {
  const [mobileOpen, setMobileOpen] = useState(false)

  return (
    <header className="sticky top-0 z-40 flex items-center h-14 border-b border-border bg-background/80 backdrop-blur-sm px-4 md:px-6">
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
        <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse" />
          <span>Connected</span>
        </div>
      </div>

      <MobileNav open={mobileOpen} onOpenChange={setMobileOpen} />
    </header>
  )
}
