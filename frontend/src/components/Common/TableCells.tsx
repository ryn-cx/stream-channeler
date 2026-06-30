// TODO: Validate
interface CellProps {
  value: string | null | undefined
}

export function TruncatedCell({ value }: CellProps) {
  return (
    <span className="text-muted-foreground text-sm truncate max-w-48 block">
      {value ?? "-"}
    </span>
  )
}

export function DateCell({ value }: CellProps) {
  return (
    <span className="text-muted-foreground text-sm">
      {value ? new Date(value).toLocaleString() : "-"}
    </span>
  )
}
