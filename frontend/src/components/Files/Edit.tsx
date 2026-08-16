// TODO: Validate
import { zodResolver } from "@hookform/resolvers/zod"
import { useQuery } from "@tanstack/react-query"
import { ChevronDown, ChevronRight, Pencil } from "lucide-react"
import { useEffect, useState } from "react"
import { useForm } from "react-hook-form"
import { z } from "zod"

import { FilesService, type FileUpdate } from "@/client"
import { FormModal } from "@/components/Common/FormModal"
import { FormTextArea } from "@/components/Common/FormTextArea"
import { FormTextField } from "@/components/Common/FormTextField"
import { TooltipIconButton } from "@/components/Common/TooltipIconButton"
import { useEditTableRow } from "@/components/Common/useEditTableRow"
import { Button } from "@/components/ui/button"
import { extraText, parseExtraText } from "@/lib/extra"
import { nullifyBlanks, optionalString, requiredKey } from "@/lib/formSchemas"
import type { FileTableData } from "./columns"

const formSchema = z.object({
  key: requiredKey,
  data_timestamp: z.string().min(1, "Data timestamp is required"),
  content: optionalString,
  update_at: optionalString,
  extra: optionalString,
})

type FormInput = z.input<typeof formSchema>
type FormOutput = z.output<typeof formSchema>

interface EditFileProps {
  file: FileTableData
}

// TODO: Validate
const EditFile = ({ file }: EditFileProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const [showContent, setShowContent] = useState(false)

  const form = useForm<FormInput, unknown, FormOutput>({
    resolver: zodResolver(formSchema),
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      key: file.key ?? "",
      data_timestamp: file.data_timestamp?.slice(0, 16) ?? "",
      content: "",
      update_at: file.update_at?.slice(0, 16) ?? "",
      extra: extraText(file.extra),
    },
  })

  // content is excluded from the files list response, so fetch the full file
  // when the modal opens to populate the content field.
  const { data: fullFile } = useQuery({
    queryKey: ["files", file.id],
    queryFn: () => FilesService.getFile({ fileId: file.id }),
    enabled: isOpen,
  })

  useEffect(() => {
    if (fullFile) {
      form.setValue("content", fullFile.content ?? "")
    }
  }, [fullFile, form])

  const mutation = useEditTableRow<FileUpdate>({
    mutationFn: (data) =>
      FilesService.updateFile({ fileId: file.id, requestBody: data }),
    rowId: file.id,
    successMessage: "File updated successfully",
    extraInvalidateKeys: [["files", file.id]],
  })

  // TODO: Validate
  const onSubmit = (data: FormOutput) => {
    setIsOpen(false)
    // Clear blanked fields (send null, not omit) so the PATCH actually clears
    // them. content is fetched lazily, so keep it omit-on-blank to avoid a slow
    // load wiping it.
    mutation.mutate({
      ...nullifyBlanks(data),
      content: data.content,
      extra: parseExtraText(data.extra ?? ""),
    })
  }

  return (
    <FormModal
      open={isOpen}
      onOpenChange={setIsOpen}
      trigger={
        <TooltipIconButton
          label="Edit File"
          icon={<Pencil />}
          onClick={() => setIsOpen(true)}
        />
      }
      title="Edit File"
      description="Update the file details below."
      form={form}
      onSubmit={onSubmit}
      isPending={mutation.isPending}
    >
      <FormTextField control={form.control} label="Key" type="text" />
      <FormTextField
        control={form.control}
        label="Data Timestamp"
        type="datetime-local"
        required
      />
      <FormTextField
        control={form.control}
        label="Update At"
        type="datetime-local"
        showNowButton
      />
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="w-fit px-2"
        onClick={() => setShowContent((previous) => !previous)}
      >
        {showContent ? <ChevronDown /> : <ChevronRight />}
        Content
      </Button>
      {showContent && (
        <FormTextArea
          control={form.control}
          label="Content"
          placeholder="File content..."
          rows={8}
        />
      )}
      <FormTextField control={form.control} label="Extra" type="text" />
    </FormModal>
  )
}

export default EditFile
