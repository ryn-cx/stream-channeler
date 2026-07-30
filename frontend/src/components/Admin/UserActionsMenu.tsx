import type { UserPublic } from "@/client"
import useAuth from "@/hooks/useAuth"
import DeleteUser from "./DeleteUser"
import EditUser from "./EditUser"

interface UserActionsMenuProps {
  user: UserPublic
}

export const UserActionsMenu = ({ user }: UserActionsMenuProps) => {
  const { user: currentUser } = useAuth()

  if (user.id === currentUser?.id) {
    return null
  }

  return (
    <div className="flex items-center justify-end gap-1">
      <EditUser user={user} />
      <DeleteUser id={user.id} />
    </div>
  )
}
