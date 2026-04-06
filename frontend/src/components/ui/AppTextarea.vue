<script setup lang="ts">
interface Props {
  modelValue?: string
  label?: string
  placeholder?: string
  rows?: number
  error?: string
  required?: boolean
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  modelValue: '',
  rows: 4,
  required: false,
  disabled: false,
})

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <div class="flex flex-col gap-1.5">
    <label v-if="label" class="text-sm font-medium text-text-secondary">
      {{ label }}
      <span v-if="required" class="text-danger">*</span>
    </label>
    <textarea
      :value="modelValue"
      :placeholder="placeholder"
      :rows="rows"
      :required="required"
      :disabled="disabled"
      @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      :class="[
        'w-full px-3 py-2 text-sm rounded-md border bg-surface text-text-primary resize-y',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        'placeholder:text-text-muted transition-colors duration-150',
        'focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent',
        error ? 'border-danger' : 'border-border',
      ]"
    />
    <p v-if="error" class="text-xs text-danger">{{ error }}</p>
  </div>
</template>
