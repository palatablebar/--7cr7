import { computed, ref } from 'vue'
import type { PartitionSpec } from '../types/table'

/** Partition selection + compute state for the plan preview page. */
export function usePlanDraft() {
  const selected = ref<string[]>([])
  const computing = ref(false)
  const error = ref('')

  const selectedPartitions = computed(() => selected.value)

  function toggle(partition: PartitionSpec) {
    const exists = selected.value.includes(partition.partition_value)
    if (exists) {
      selected.value = selected.value.filter((value) => value !== partition.partition_value)
    } else {
      selected.value = [...selected.value, partition.partition_value]
    }
  }

  function selectDefaults(partitions: PartitionSpec[]) {
    // default: the two oldest fragmented partitions, hot/newest last in the list
    const candidates = partitions.filter((item) => item.small_file_count > 0)
    selected.value = candidates
      .slice()
      .sort((a, b) => a.partition_value.localeCompare(b.partition_value))
      .slice(0, 2)
      .map((item) => item.partition_value)
  }

  function reset() {
    selected.value = []
    error.value = ''
  }

  return { selected, selectedPartitions, computing, error, toggle, selectDefaults, reset }
}
