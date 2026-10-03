// TODO: Validate
import { useMutation } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, Download, FileUp, Upload } from "lucide-react"
import { useRef, useState } from "react"
import { FilesService } from "@/client"
import { PageHeader } from "@/components/Common/PageHeader"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { LoadingButton } from "@/components/ui/loading-button"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"

export const Route = createFileRoute("/_layout/admin/manage-files")({
  component: AdminManageFiles,
  head: () => ({
    meta: [{ title: "Manage Files - Stream Channeler" }],
  }),
})

// TODO: Validate
function downloadJson(data: unknown, fileName: string) {
  const url = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
  )
  const link = document.createElement("a")
  link.href = url
  link.download = fileName
  link.click()
  URL.revokeObjectURL(url)
}

// TODO: Validate
function ExportManifestCard() {
  const { showSuccessToast, showErrorToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () => FilesService.getFileManifest(),
    onSuccess: (entries) => {
      downloadJson(entries, "stream-channeler-file-manifest.json")
      showSuccessToast(`Exported ${entries.length} files`)
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Export File List</CardTitle>
        <CardDescription>
          Download every file in this database as a JSON list of plugin keys and
          file keys.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <LoadingButton
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          className="w-fit"
        >
          <Download />
          Export File List
        </LoadingButton>
      </CardContent>
    </Card>
  )
}

// TODO: Validate
function DumpMissingFilesCard() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error("No file selected")
      return FilesService.dumpMissingFiles({ formData: { file: selectedFile } })
    },
    onSuccess: (files) => {
      downloadJson(files, "stream-channeler-missing-files.json")
      showSuccessToast(`Dumped ${files.length} missing files`)
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Dump Missing Files</CardTitle>
        <CardDescription>
          Upload a file list exported from another database to download every
          file this database holds that the list does not.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
        />
        <LoadingButton
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!selectedFile}
          className="w-fit"
        >
          <FileUp />
          Dump Missing Files
        </LoadingButton>
      </CardContent>
    </Card>
  )
}

// TODO: Validate
function ImportFilesCard() {
  const { showSuccessToast, showErrorToast } = useCustomToast()
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const mutation = useMutation({
    mutationFn: () => {
      if (!selectedFile) throw new Error("No file selected")
      return FilesService.importFiles({ formData: { file: selectedFile } })
    },
    onSuccess: (result) => {
      showSuccessToast(
        `Imported ${result.imported} files, skipped ${result.skipped} that already exist`,
      )
      setSelectedFile(null)
      if (fileInputRef.current) fileInputRef.current.value = ""
    },
    onError: handleError.bind(showErrorToast),
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle>Import Files</CardTitle>
        <CardDescription>
          Upload a missing file dump to add those files to this database. Files
          are matched to their plugin by key, so the plugin's id may differ
          between databases.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <input
          ref={fileInputRef}
          type="file"
          accept=".json,application/json"
          onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
          className="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-primary-foreground hover:file:bg-primary/90"
        />
        <LoadingButton
          onClick={() => mutation.mutate()}
          loading={mutation.isPending}
          disabled={!selectedFile}
          className="w-fit"
        >
          <Upload />
          Import Files
        </LoadingButton>
      </CardContent>
    </Card>
  )
}

// TODO: Validate
function AdminManageFiles() {
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
      <PageHeader
        title="Manage Files"
        description="Move files between Stream Channeler databases."
      />
      <div className="flex flex-col gap-4 px-[4%] pb-8">
        <ExportManifestCard />
        <DumpMissingFilesCard />
        <ImportFilesCard />
      </div>
    </div>
  )
}
