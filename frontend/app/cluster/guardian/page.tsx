import { ApprovalPanel } from "@/components/guardian/approval-panel"

export default function GuardianPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Guardian</h1>
        <p className="text-sm text-muted-foreground">
          Review and approve AI-proposed remediations
        </p>
      </div>
      <ApprovalPanel />
    </div>
  )
}
