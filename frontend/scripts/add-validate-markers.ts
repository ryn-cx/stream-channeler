// TODO: Validate
import { readFileSync, writeFileSync } from "node:fs"
import { relative, resolve } from "node:path"
import { Glob } from "bun"
import ts from "typescript"

const MARKER = "// TODO: Validate"
const EXEMPT_PATTERNS = [
  /(^|[\\/])client[\\/]/,
  /routeTree\.gen\.ts$/,
  /(^|[\\/])node_modules[\\/]/,
]

// TODO: Validate
const isExempt = (path: string): boolean =>
  EXEMPT_PATTERNS.some((pattern) => pattern.test(path))

// TODO: Validate
const scriptKindFor = (path: string): ts.ScriptKind => {
  if (path.endsWith(".tsx")) return ts.ScriptKind.TSX
  if (path.endsWith(".jsx")) return ts.ScriptKind.JSX
  if (path.endsWith(".js") || path.endsWith(".mjs")) return ts.ScriptKind.JS
  return ts.ScriptKind.TS
}

// TODO: Validate
const isFunctionLike = (node: ts.Node): boolean =>
  ts.isArrowFunction(node) ||
  ts.isFunctionExpression(node) ||
  ts.isClassExpression(node)

// TODO: Validate
const isMarkable = (node: ts.Node): boolean => {
  if (
    ts.isFunctionDeclaration(node) ||
    ts.isClassDeclaration(node) ||
    ts.isMethodDeclaration(node) ||
    ts.isConstructorDeclaration(node) ||
    ts.isGetAccessorDeclaration(node) ||
    ts.isSetAccessorDeclaration(node)
  ) {
    return true
  }
  if (ts.isVariableStatement(node)) {
    return node.declarationList.declarations.some(
      (declaration) =>
        declaration.initializer !== undefined &&
        isFunctionLike(declaration.initializer),
    )
  }
  return false
}

// TODO: Validate
const collectInsertLines = (sourceFile: ts.SourceFile): Set<number> => {
  const insertLines = new Set<number>()
  const visit = (node: ts.Node): void => {
    if (isMarkable(node)) {
      const start = node.getStart(sourceFile, true)
      insertLines.add(sourceFile.getLineAndCharacterOfPosition(start).line)
    }
    ts.forEachChild(node, visit)
  }
  ts.forEachChild(sourceFile, visit)
  return insertLines
}

// TODO: Validate
const processFile = (path: string): boolean => {
  const source = readFileSync(path, "utf8")
  const sourceFile = ts.createSourceFile(
    path,
    source,
    ts.ScriptTarget.Latest,
    true,
    scriptKindFor(path),
  )

  const insertLines = collectInsertLines(sourceFile)
  insertLines.add(0)

  const lines = source.split("\n")
  let changed = false
  for (const index of [...insertLines].sort((left, right) => right - left)) {
    const neighborIndex = index === 0 ? 0 : index - 1
    if (lines[neighborIndex]?.trim() === MARKER) continue
    const target = lines[index] ?? ""
    const indent = target.slice(0, target.length - target.trimStart().length)
    const carriageReturn = target.endsWith("\r") ? "\r" : ""
    lines.splice(index, 0, `${indent}${MARKER}${carriageReturn}`)
    changed = true
  }

  if (changed) writeFileSync(path, lines.join("\n"), "utf8")
  return changed
}

// TODO: Validate
const main = (): void => {
  const roots = process.argv.slice(2)
  const glob = new Glob("**/*.{ts,tsx,js,jsx,mjs}")
  let changedCount = 0
  let totalCount = 0
  for (const root of roots.length > 0 ? roots : ["src"]) {
    for (const match of glob.scanSync({ cwd: root, absolute: true })) {
      const path = resolve(match)
      if (isExempt(relative(process.cwd(), path))) continue
      totalCount += 1
      if (processFile(path)) {
        changedCount += 1
        console.log(`updated ${relative(process.cwd(), path)}`)
      }
    }
  }
  console.log(`${changedCount} of ${totalCount} files updated`)
}

main()
