// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { Pencil } from "lucide-react"
import { useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { type TitlePublic, TitlesService, type TitleUpdate } from "@/client"
import { TitleInformationSummary } from "@/components/ChannelCommon/TitleInformationDialog"
import { FormModal } from "@/components/Common/FormModal"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import useAuth from "@/hooks/useAuth"
import { extraText, parseExtraText } from "@/lib/extra"
import { optionalString } from "@/lib/formSchemas"
import { ForceRelinkTitleButton } from "./ForceRelinkTitleButton"
import { ForceUpdateTitleButton } from "./ForceUpdateTitleButton"
import { LinkedTitleField } from "./LinkedTitleField"
import { LinkedTitleLinks } from "./LinkedTitleLinks"
import { MarkTitleAbsentButton } from "./MarkTitleAbsentButton"
import { TmdbTitleField } from "./TmdbTitleField"

const formSchema = z.object({
  extra: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditTitleProps {
  title: TitlePublic
  size?: React.ComponentProps<typeof TooltipIconButton>["size"]
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// TODO: Validate
const EditTitle = ({ title, size, open, onOpenChange }: EditTitleProps) => {
  const [isOpenHere, setIsOpenHere] = useState(false)
  const isOpen = open ?? isOpenHere
  const setIsOpen = onOpenChange ?? setIsOpenHere
  const { user } = useAuth()
  const isTmdbTitle = title.plugin_name === "TMDB"
  const fullName = `${title.plugin_name} - ${title.name}`

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      extra: extraText(title.extra),
    },
  })

  const mutation = useEditTableRow<TitleUpdate>({
    mutationFn: (data) =>
      TitlesService.updateTitle({ titleId: title.id, requestBody: data }),
    rowId: title.id,
    successMessage: "Title updated successfully",
    extraInvalidateKeys: [["titles", title.id]],
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    mutation.mutate({ extra: parseExtraText(data.extra ?? "") })
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        open === undefined ? (
          <TooltipIconButton
            label="Edit Title"
            icon={<Pencil />}
            size={size}
            onClick={() => setIsOpen(true)}
          />
        ) : null
      }
      title={fullName}
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
      size="3xl"
      footerStart={
        user?.is_superuser ? (
          <div className="flex gap-2">
            <ForceUpdateTitleButton titleId={title.id} />
            {!isTmdbTitle && <ForceRelinkTitleButton titleId={title.id} />}
          </div>
        ) : null
      }
    >
      <TitleInformationSummary titleId={title.id} enabled={isOpen} />
      {user?.is_superuser &&
        (isTmdbTitle ? (
          <div className="space-y-3">
            <LinkedTitleLinks titleId={title.id} enabled={isOpen} />
            <LinkedTitleField titleId={title.id} />
          </div>
        ) : (
          <div className="space-y-3">
            <TmdbTitleField
              titleId={title.id}
              tmdbTitleIds={title.tmdb_title_ids ?? []}
              enabled={isOpen}
            />
            <div className="space-y-2">
              <MarkTitleAbsentButton
                titleId={title.id}
                titleName={title.name}
              />
              <p className="text-sm text-muted-foreground">
                {title.tmdb_absent_at
                  ? "This title is already settled as one TMDB has no record of."
                  : "Drops every canonical title this stands for and settles it as one TMDB has no record of, so no later import links it again."}
              </p>
            </div>
          </div>
        ))}
    </FormModal>
  )
}

export default EditTitle
