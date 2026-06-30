// TODO: Validate
interface ActionsMenuProps {
  children: React.ReactNode
}

export const ActionsMenu = ({ children }: ActionsMenuProps) => {
  return <div className="flex items-center justify-end gap-1">{children}</div>
}
