import { getServices } from "@/lib/api/traces"
import { ServiceMapTable } from "@/components/traces/service-map-table"

export default async function ServicesPage() {
  const data = await getServices()

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Services</h1>
        <p className="text-sm text-muted-foreground">
          Request rates, error rates, and latency per service
        </p>
      </div>
      <ServiceMapTable services={data.services} />
    </div>
  )
}
