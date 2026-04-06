import type { Provider } from '@/types/provider'

export function useCsv() {
  function exportProviders(providers: Provider[]) {
    const headers = ['nombre', 'descripcion', 'email', 'telefono', 'website', 'ciudad', 'pais', 'categorias', 'tags']
    const rows = providers.map((p) => [
      p.name,
      p.description.replace(/"/g, '""'),
      p.contact_email ?? '',
      p.contact_phone ?? '',
      p.website ?? '',
      p.city ?? '',
      p.country ?? '',
      p.categories.map((c) => c.category.name).join('; '),
      p.tags.map((t) => t.tag.name).join('; '),
    ])

    const csv = [headers, ...rows].map((row) => row.map((v) => `"${v}"`).join(',')).join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `proveedores_${new Date().toISOString().slice(0, 10)}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  function parseCsvLine(line: string): string[] {
    const values: string[] = []
    let current = ''
    let inQuotes = false

    for (let i = 0; i < line.length; i++) {
      const char = line[i]!
      if (inQuotes) {
        if (char === '"' && line[i + 1] === '"') {
          current += '"'
          i++ // skip escaped quote
        } else if (char === '"') {
          inQuotes = false
        } else {
          current += char
        }
      } else {
        if (char === '"') {
          inQuotes = true
        } else if (char === ',') {
          values.push(current.trim())
          current = ''
        } else {
          current += char
        }
      }
    }
    values.push(current.trim())
    return values
  }

  function parseImportCsv(file: File): Promise<Array<Record<string, string>>> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => {
        const text = e.target?.result as string
        const lines = text.split('\n').filter((l) => l.trim())
        if (lines.length < 2) return reject(new Error('CSV vacio o sin datos'))

        const headers = parseCsvLine(lines[0]!).map((h) => h.toLowerCase())
        const rows = lines.slice(1).map((line) => {
          const values = parseCsvLine(line)
          const obj: Record<string, string> = {}
          headers.forEach((h, i) => {
            obj[h] = values[i] ?? ''
          })
          return obj
        })
        resolve(rows)
      }
      reader.onerror = () => reject(new Error('Error al leer el archivo'))
      reader.readAsText(file)
    })
  }

  return { exportProviders, parseImportCsv }
}
