// TODO: Validate
import { LayoutGrid, Table as TableIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Skeleton } from "@/components/ui/skeleton"

const PendingChannelDetails = () => (
  <div className="flex flex-col">
    {/* Hero skeleton */}
    <Skeleton className="w-full aspect-video" />

    {/* Toolbar */}
    <div className="flex flex-wrap items-center gap-2 px-[4%] py-4">
      <Skeleton className="h-8 w-48 mr-2" />
      <ButtonGroup>
        <Button variant="default" disabled className="opacity-50 my-4">
          <LayoutGrid />
          Cards
        </Button>
        <Button variant="outline" disabled className="opacity-50 my-4">
          <TableIcon />
          Table
        </Button>
      </ButtonGroup>
      <Skeleton className="h-10 w-28 my-4 rounded-md" />
      <Skeleton className="h-10 w-28 my-4 rounded-md" />
      <Skeleton className="h-10 w-28 my-4 rounded-md" />
    </div>

    {/* Card grid skeleton */}
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4 px-[4%]">
      {Array.from({ length: 12 }).map((_, index) => (
        <div key={index} className="flex flex-col gap-2">
          <Skeleton className="w-full aspect-video rounded-sm" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-3 w-1/2" />
        </div>
      ))}
    </div>
  </div>
)

export default PendingChannelDetails
