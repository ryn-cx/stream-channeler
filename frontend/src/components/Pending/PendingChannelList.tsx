// TODO: Validate
import { LayoutGrid, Plus, Table as TableIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ButtonGroup } from "@/components/ui/button-group"
import { Skeleton } from "@/components/ui/skeleton"

// TODO: Validate
const PendingChannelList = () => (
  <div className="flex flex-col gap-6">
    <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
      <h1 className="text-2xl font-bold tracking-tight">Channels</h1>
      <div className="flex flex-wrap items-center gap-2">
        <ButtonGroup>
          <Button variant="default" disabled className="opacity-50">
            <LayoutGrid />
            Browse
          </Button>
          <Button variant="outline" disabled className="opacity-50">
            <TableIcon />
            Table
          </Button>
        </ButtonGroup>
        <Button disabled className="opacity-50">
          <Plus />
          New Channel
        </Button>
      </div>
    </div>

    {/* Channel row skeletons */}
    {Array.from({ length: 4 }).map((_, rowIndex) => (
      <div key={rowIndex} className="flex flex-col gap-2">
        <div className="flex items-center gap-3 px-[4%]">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-16" />
        </div>
        <div className="flex gap-2 px-[4%]">
          {Array.from({ length: 5 }).map((_, cardIndex) => (
            <Skeleton
              key={cardIndex}
              className="flex-shrink-0 w-[280px] md:w-[340px] lg:w-[400px] aspect-video rounded-sm"
            />
          ))}
        </div>
      </div>
    ))}
  </div>
)

export default PendingChannelList
