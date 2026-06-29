import { useMutationState } from "@tanstack/react-query"
import { createFileRoute, redirect } from "@tanstack/react-router"

import type { UserCreate } from "@/client"
import { UsersService } from "@/client"
import AddUser from "@/components/Admin/AddUser"
import { columns } from "@/components/Admin/columns"
import type { UserTableData } from "@/components/Admin/types"
import { ServerClientTable } from "@/components/Common/DataTable"
import { PageHeader } from "@/components/Common/PageHeader"
import PendingUsers from "@/components/Pending/PendingUsers"
import useAuth from "@/hooks/useAuth"

export const Route = createFileRoute("/_layout/admin")({
  component: Admin,
  beforeLoad: async () => {
    const user = await UsersService.readUserMe()
    if (!user.is_superuser) {
      throw redirect({
        to: "/",
      })
    }
  },
  head: () => ({
    meta: [
      {
        title: "Admin - FastAPI Template",
      },
    ],
  }),
})

function UsersTable() {
  const { user: currentUser } = useAuth()

  const pendingUsers = useMutationState({
    filters: { mutationKey: ["users", "create"], status: "pending" },
    select: (mutation): UserTableData => {
      const variables = mutation.state.variables as UserCreate
      return {
        id: `pending-${mutation.mutationId}`,
        email: variables.email,
        full_name: variables.full_name ?? null,
        is_superuser: variables.is_superuser ?? false,
        is_active: variables.is_active ?? false,
        pending: true,
        isCurrentUser: false,
      }
    },
  })

  return (
    <ServerClientTable<UserTableData>
      columns={columns}
      queryKey={["users"]}
      fetchTable={async ({ offset, limit, sortOptions, filterOptions }) => {
        const result = await UsersService.readUsers({
          offset,
          limit,
          sortOptions: JSON.stringify(sortOptions),
          filterOptions: JSON.stringify(filterOptions),
        })
        return {
          data: result.data.map((user) => ({
            ...user,
            isCurrentUser: currentUser?.id === user.id,
          })),
          total_count: result.total_count,
          filtered_count: result.filtered_count,
          is_server_side: result.is_server_side,
        }
      }}
      storageKey="users-table"
      pendingRows={pendingUsers}
      rowClassName={(row) => (row.pending ? "opacity-50" : undefined)}
      loadingFallback={<PendingUsers />}
    />
  )
}

function Admin() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Users"
        description="Manage user accounts and permissions"
      >
        <AddUser />
      </PageHeader>
      <UsersTable />
    </div>
  )
}
