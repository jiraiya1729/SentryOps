"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import { Plus, Star, LayoutDashboard } from "lucide-react"
import { getDashboards, createDashboard } from "@/lib/api/dashboards"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Skeleton } from "@/components/ui/skeleton"
import type { Dashboard } from "@/lib/types/api"

export default function DashboardsPage() {
  const router = useRouter()
  const [dashboards, setDashboards] = useState<Dashboard[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [newDescription, setNewDescription] = useState("")
  const [creating, setCreating] = useState(false)

  async function fetchDashboards() {
    try {
      const res = await getDashboards()
      setDashboards(res.dashboards)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDashboards() }, [])

  async function handleCreate() {
    if (!newName.trim()) return
    setCreating(true)
    try {
      await createDashboard(newName.trim(), newDescription.trim() || undefined)
      setCreateOpen(false)
      setNewName("")
      setNewDescription("")
      await fetchDashboards()
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold tracking-tight">Dashboards</h1>
          <p className="text-sm text-muted-foreground">Custom observability dashboards</p>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Create Dashboard
        </Button>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 rounded-xl" />
          ))}
        </div>
      ) : dashboards.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <LayoutDashboard className="h-10 w-10 text-muted-foreground/40" />
          <p className="text-sm font-medium">No dashboards yet</p>
          <p className="text-xs text-muted-foreground">Create your first dashboard to get started</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {dashboards.map((d) => (
            <div
              key={d.id}
              onClick={() => router.push(`/cluster/dashboards/${d.id}`)}
              className="cursor-pointer"
            >
              <Card className="hover:ring-2 hover:ring-ring/50 transition-all h-full">
                <CardHeader className="pb-2">
                  <div className="flex items-center gap-1.5">
                    <CardTitle className="text-sm font-medium">{d.name}</CardTitle>
                    {d.is_default && (
                      <Star className="h-3.5 w-3.5 text-yellow-400 fill-yellow-400 shrink-0" />
                    )}
                  </div>
                  <CardDescription className="text-xs line-clamp-2">
                    {d.description || "No description"}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <Badge variant="outline" className="text-xs">
                    {d.panels?.length ?? 0} panels
                  </Badge>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogTitle>New Dashboard</DialogTitle>
          <div className="space-y-4 pt-2">
            <div className="space-y-1.5">
              <label className="text-xs font-medium">Name *</label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Dashboard"
                className="h-8 text-sm"
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-medium">Description (optional)</label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Describe this dashboard…"
                className="h-8 text-sm"
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" size="sm" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleCreate} disabled={!newName.trim() || creating}>
                {creating ? "Creating…" : "Create"}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}
