// TODO: Validate
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import type { VisibilityState } from "@tanstack/react-table"
import { getCoreRowModel, useReactTable } from "@tanstack/react-table"
import { ArrowLeft } from "lucide-react"
import { type UserPublic, UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { columns } from "@/components/Admin/columns"
import type { UserTableData } from "@/components/Admin/types"
import { ColumnVisibilityButton } from "@/components/Common/ColumnVisibilityButton"
import { DataTable } from "@/components/Common/DataTable"
import { DataTableSkeleton } from "@/components/Common/DataTableSkeleton"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import useAuth from "@/hooks/useAuth"
import { usePersistedJsonState } from "@/hooks/usePersistedState"

export const Route = createFileRoute("/_layout/admin/users")({
  component: AdminUsers,
  head: () => ({
    meta: [
      {
        title: "Admin Users - Stream Channeler",
      },
    ],
  }),
})

// TODO: Validate
function getUsersQueryOptions() {
  return {
    queryFn: () => UsersService.readUsers(),
    queryKey: ["users"],
    refetchOnWindowFocus: false,
    placeholderData: (previousData: any) => previousData,
  }
}

// TODO: Validate
function UsersTableContent() {
  const { user: currentUser } = useAuth()
  const { data: users, isPlaceholderData } = useQuery(getUsersQueryOptions())
  const [columnVisibility, setColumnVisibility] =
    usePersistedJsonState<VisibilityState>("users-column-visibility", {})

  const tableData: UserTableData[] = (users?.data ?? []).map(
    (user: UserPublic) => ({
      ...user,
      isCurrentUser: currentUser?.id === user.id,
    }),
  )

  const table = useReactTable({
    data: tableData,
    columns,
    state: {
      columnVisibility,
    },
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
  })

  return (
    <div
      className={
        isPlaceholderData
          ? "opacity-60 transition-opacity duration-200"
          : undefined
      }
    >
      <PageHeader title="Users">
        <AddUser />
        <ColumnVisibilityButton table={table} />
      </PageHeader>
      <div className="px-[4%]">
        {!users ? (
          <DataTableSkeleton table={table} />
        ) : (
          <DataTable
            columns={columns}
            data={tableData}
            columnVisibility={columnVisibility}
            onColumnVisibilityChange={setColumnVisibility}
          />
        )}
      </div>
    </div>
  )
}

// TODO: Validate
function AdminUsers() {
  return (
    <div className="flex flex-col gap-6">
      <div className="px-[4%] pt-4">
        <Button variant="ghost" size="sm" asChild>
          <Link to="/admin">
            <ArrowLeft />
            Back to Admin
          </Link>
        </Button>
      </div>
      <UsersTableContent />
    </div>
  )
}
