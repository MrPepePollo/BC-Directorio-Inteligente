<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, useId } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'

interface SelectOption {
  label: string
  value: string
  description?: string
}

interface Props {
  modelValue?: string
  options: SelectOption[]
  placeholder?: string
  label?: string
  disabled?: boolean
  fullWidth?: boolean
  align?: 'left' | 'right'
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: '',
  placeholder: 'Selecciona una opcion',
  label: undefined,
  disabled: false,
  fullWidth: true,
  align: 'left',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [value: string]
}>()

const rootRef = ref<HTMLElement | null>(null)
const triggerRef = ref<HTMLButtonElement | null>(null)
const optionRefs = ref<(HTMLButtonElement | null)[]>([])
const isOpen = ref(false)
const highlightedIndex = ref(0)
const listboxId = useId()

const selectedIndex = computed(() =>
  Math.max(
    0,
    props.options.findIndex((option) => option.value === props.modelValue),
  ),
)

const selectedOption = computed(
  () => props.options.find((option) => option.value === props.modelValue) ?? null,
)

function setOptionRef(element: HTMLButtonElement | null, index: number) {
  optionRefs.value[index] = element
}

function focusHighlighted() {
  nextTick(() => {
    optionRefs.value[highlightedIndex.value]?.focus()
  })
}

function openMenu(preferredIndex = selectedIndex.value) {
  if (props.disabled) return
  highlightedIndex.value = Math.max(0, preferredIndex)
  isOpen.value = true
  focusHighlighted()
}

function closeMenu(focusTrigger = false) {
  isOpen.value = false
  if (focusTrigger) {
    nextTick(() => {
      triggerRef.value?.focus()
    })
  }
}

function toggleMenu() {
  if (isOpen.value) {
    closeMenu()
    return
  }
  openMenu()
}

function selectOption(option: SelectOption) {
  emit('update:modelValue', option.value)
  emit('change', option.value)
  closeMenu(true)
}

function moveHighlight(step: number) {
  const total = props.options.length
  if (!total) return
  highlightedIndex.value = (highlightedIndex.value + step + total) % total
  focusHighlighted()
}

function onTriggerKeydown(event: KeyboardEvent) {
  if (props.disabled) return

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    openMenu(selectedIndex.value)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    openMenu(selectedIndex.value)
    return
  }

  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    toggleMenu()
  }
}

function onListKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveHighlight(1)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveHighlight(-1)
    return
  }

  if (event.key === 'Home') {
    event.preventDefault()
    highlightedIndex.value = 0
    focusHighlighted()
    return
  }

  if (event.key === 'End') {
    event.preventDefault()
    highlightedIndex.value = props.options.length - 1
    focusHighlighted()
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()
    closeMenu(true)
    return
  }

  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    const option = props.options[highlightedIndex.value]
    if (option) selectOption(option)
  }
}

function onClickOutside(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Node)) return
  if (!rootRef.value?.contains(target)) {
    closeMenu()
  }
}

onMounted(() => {
  document.addEventListener('mousedown', onClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('mousedown', onClickOutside)
})
</script>

<template>
  <div ref="rootRef" :class="['relative', fullWidth ? 'w-full' : 'w-auto']">
    <label v-if="label" class="mb-1.5 block text-xs font-semibold uppercase tracking-[0.08em] text-text-muted">
      {{ label }}
    </label>

    <button
      :id="`${listboxId}-trigger`"
      ref="triggerRef"
      type="button"
      :disabled="disabled"
      :aria-expanded="isOpen"
      :aria-controls="listboxId"
      aria-haspopup="listbox"
      @click="toggleMenu"
      @keydown="onTriggerKeydown"
      :class="[
        'field-shell field-shell--compact px-4 text-left',
        'disabled:cursor-not-allowed disabled:opacity-50',
        fullWidth ? 'w-full' : 'min-w-[13rem]',
      ]"
    >
      <span class="min-w-0 flex-1">
        <span
          :class="[
            'block truncate text-sm font-semibold',
            selectedOption ? 'text-text-primary' : 'text-text-muted',
          ]"
        >
          {{ selectedOption?.label ?? placeholder }}
        </span>
        <span v-if="selectedOption?.description" class="mt-0.5 block truncate text-xs text-text-muted">
          {{ selectedOption.description }}
        </span>
      </span>
      <ChevronDown
        :class="[
          'h-4 w-4 shrink-0 text-text-muted transition-transform duration-200',
          isOpen ? 'rotate-180 text-text-primary' : '',
        ]"
      />
    </button>

    <div
      v-if="isOpen"
      :class="[
        'floating-menu absolute top-[calc(100%+0.6rem)] z-40 max-h-72 overflow-y-auto rounded-[1.15rem] p-2',
        fullWidth ? 'w-full' : 'min-w-[15rem]',
        align === 'right' ? 'right-0' : 'left-0',
      ]"
      :id="listboxId"
      role="listbox"
      :aria-labelledby="`${listboxId}-trigger`"
      @keydown="onListKeydown"
    >
      <button
        v-for="(option, index) in options"
        :key="option.value || `empty-${index}`"
        :ref="(element) => setOptionRef(element as HTMLButtonElement | null, index)"
        type="button"
        role="option"
        :aria-selected="option.value === modelValue"
        @click="selectOption(option)"
        @mouseenter="highlightedIndex = index"
        :class="[
          'flex w-full items-start gap-3 rounded-[0.95rem] px-3 py-2.5 text-left transition-colors duration-150',
          option.value === modelValue
            ? 'bg-primary-100 text-text-primary dark:bg-primary-900/60'
            : highlightedIndex === index
              ? 'bg-surface-hover text-text-primary'
              : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary',
        ]"
      >
        <span
          :class="[
            'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full border',
            option.value === modelValue
              ? 'border-primary-400 bg-primary-500 text-white'
              : 'border-border bg-surface text-transparent',
          ]"
        >
          <Check class="h-3 w-3" />
        </span>
        <span class="min-w-0 flex-1">
          <span class="block truncate text-sm font-semibold">
            {{ option.label }}
          </span>
          <span v-if="option.description" class="mt-0.5 block text-xs text-text-muted">
            {{ option.description }}
          </span>
        </span>
      </button>
    </div>
  </div>
</template>
