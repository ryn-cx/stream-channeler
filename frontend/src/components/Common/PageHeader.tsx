// TODO: Validate
interface PageHeaderProps {
  title: string
  description?: string
  children?: React.ReactNode
}

// TODO: Validate
export function PageHeader({ title, description, children }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 px-[4%] pt-4 pb-2">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
        {description ? (
          <p className="text-muted-foreground">{description}</p>
        ) : null}
      </div>
      {children ? (
        <div className="flex flex-wrap items-center gap-2">{children}</div>
      ) : null}
    </div>
  )
}
