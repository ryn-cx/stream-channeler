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
import { CanonicalizeTitleButton } from "./CanonicalizeTitleButton"
import { CanonicalTitleField } from "./CanonicalTitleField"
import { ForceUpdateTitleButton } from "./ForceUpdateTitleButton"
import { NonCanonicalTitleField } from "./NonCanonicalTitleField"
import { NonCanonicalTitleLinks } from "./NonCanonicalTitleLinks"
import {
  episodeGroupIdOf,
  TMDB_EPISODE_ORDER_PLUGIN,
  TmdbEpisodeOrderField,
  withEpisodeGroupId,
} from "./TmdbEpisodeOrderField"

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
  // Only TMDB's own rows carry an episode order, and only an admin sets one.
  const isTmdbTitle = title.plugin_name === TMDB_EPISODE_ORDER_PLUGIN
  const showsEpisodeOrder = Boolean(user?.is_superuser) && isTmdbTitle
  const [episodeGroupId, setEpisodeGroupId] = useState(() =>
    episodeGroupIdOf(title.extra),
  )

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
  const onEpisodeGroupChange = (groupId: string) => {
    setEpisodeGroupId(groupId)
    const extra = withEpisodeGroupId(
      parseExtraText(form.getValues("extra") ?? ""),
      groupId,
    )
    form.setValue("extra", extraText(extra), { shouldDirty: true })
  }

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
      title="Edit Title"
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
      size="3xl"
      footerStart={
        user?.is_superuser ? (
          <ForceUpdateTitleButton titleId={title.id} />
        ) : null
      }
    >
      <TitleInformationSummary titleId={title.id} enabled={isOpen} />
      {user?.is_superuser &&
        (isTmdbTitle ? (
          <div className="space-y-3">
            <NonCanonicalTitleLinks titleId={title.id} enabled={isOpen} />
            <NonCanonicalTitleField titleId={title.id} />
          </div>
        ) : (
          <div className="space-y-3">
            <CanonicalTitleField
              titleId={title.id}
              canonicalTitleIds={title.canonical_title_ids ?? []}
              enabled={isOpen}
            />
            <CanonicalizeTitleButton
              titleId={title.id}
              canonicalTitleIds={title.canonical_title_ids ?? []}
            />
          </div>
        ))}
      {showsEpisodeOrder && (
        <TmdbEpisodeOrderField
          titleId={title.id}
          value={episodeGroupId}
          onChange={onEpisodeGroupChange}
          enabled={isOpen}
        />
      )}
    </FormModal>
  )
}

export default EditTitle
