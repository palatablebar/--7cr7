import { computed, ref } from 'vue'
import type { DataFile, PartitionSpec } from '../types/table'

export interface FileFilterState {
  partition: string
  sizeBand: 'all' | 'small' | 'large'
  sort: 'size_desc' | 'size_asc' | 'rows_desc' | 'path_asc'
}

export function useTableFilters(partitions: () => PartitionSpec[], files: () => DataFile[]) {
  const state = ref<FileFilterState>({ partition: '', sizeBand: 'all', sort: 'size_desc' })

  const filteredFiles = computed(() => {
    let rows = files()
    if (state.value.partition) {
      rows = rows.filter((file) => file.partition_value === state.value.partition)
    }
    if (state.value.sizeBand === 'small') rows = rows.filter((file) => file.is_small)
    if (state.value.sizeBand === 'large') rows = rows.filter((file) => !file.is_small)
    const sorted = [...rows]
    switch (state.value.sort) {
      case 'size_asc':
        sorted.sort((a, b) => a.size_bytes - b.size_bytes)
        break
      case 'rows_desc':
        sorted.sort((a, b) => b.row_count - a.row_count)
        break
      case 'path_asc':
        sorted.sort((a, b) => a.path.localeCompare(b.path))
        break
      default:
        sorted.sort((a, b) => b.size_bytes - a.size_bytes)
    }
    return sorted
  })

  const partitionOptions = computed(() => partitions().map((item) => item.partition_value))
  const smallFileCount = computed(() => files().filter((file) => file.is_small).length)

  function reset() {
    state.value = { partition: '', sizeBand: 'all', sort: 'size_desc' }
  }

  return { state, filteredFiles, partitionOptions, smallFileCount, reset }
}
