import type { UserPublic } from "@/client"

export type UserPublicWithPending = UserPublic & { pending?: boolean }
export type UsersPublicWithPending = {
  data: UserPublicWithPending[]
  count: number
}

export type UserTableData = UserPublicWithPending & {
  isCurrentUser: boolean
}
