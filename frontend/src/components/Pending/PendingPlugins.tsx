import { Columns, Plus } from "lucide-react"
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

const PendingPlugins = () => (
  <div className="flex flex-col gap-4">
    <div className="flex items-center justify-between">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Plugins</h1>
        <p className="text-muted-foreground">Manage your plugins</p>
      </div>
      <div className="flex gap-2">
        <Button disabled className="opacity-50 mt-2 mb-4">
          <Plus />
          Add Plugin
        </Button>
        <Button disabled className="opacity-50 mt-2 mb-4">
          <Columns />
          Columns
        </Button>
      </div>
    </div>
    <Table className="table-fixed w-full">
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          {["Name", "Key"].map((label) => (
            <TableHead key={label} className="overflow-hidden py-2">
              <div>{label}</div>
              <Skeleton className="h-8 w-full mt-2 rounded-md" />
            </TableHead>
          ))}
          <TableHead>
            <span className="sr-only">Actions</span>
          </TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: 5 }).map((_, index) => (
          <TableRow key={index}>
            <TableCell>
              <Skeleton className="h-4" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-4" />
            </TableCell>
            <TableCell>
              <div className="flex justify-end">
                <Skeleton className="size-8 rounded-md" />
              </div>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  </div>
)

export default PendingPlugins
