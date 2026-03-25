import { Columns, RefreshCw, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const PendingWatches = () => (
  <div>
    <div className="flex items-center gap-4">
      <h1 className="text-2xl font-bold">Watches</h1>
      <Button disabled className="opacity-50 mt-2 mb-4">
        <RefreshCw />
        Sync Episode Watches
      </Button>
      <Button disabled className="opacity-50 mt-2 mb-4">
        <Upload />
        Import
      </Button>
      <Button disabled className="opacity-50 mt-2 mb-4">
        <Columns />
        Columns
      </Button>
    </div>
    <div className="flex flex-col gap-4">
      <Table className="table-fixed w-full">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="overflow-hidden py-2">Source</TableHead>
            <TableHead className="overflow-hidden py-2">Show</TableHead>
            <TableHead className="overflow-hidden py-2">Season</TableHead>
            <TableHead className="overflow-hidden py-2">Episode</TableHead>
            <TableHead className="overflow-hidden py-2">Watch Date</TableHead>
            <TableHead className="overflow-hidden py-2">Verified</TableHead>
            <TableHead>
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {Array.from({ length: 10 }).map((_, __) => (
            <TableRow key={"skeleton"}>
              <TableCell>
                <Skeleton className="h-4" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4" />
              </TableCell>
              <TableCell>
                <Skeleton className="h-4" />
              </TableCell>
              <TableCell>
                <div className="flex justify-end">
                  {/* These sizes don't match with the sizes on the actual button but it looks good */}
                  <Skeleton className="size-8 rounded-md" />
                  <Skeleton className="size-8 rounded-md" />
                  <Skeleton className="size-8 rounded-md" />
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  </div>
)

export default PendingWatches
