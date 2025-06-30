<!--
    InputDate.vue
    <the-app-name>

    Created by InspiringApps on 6/7/2024.
-->

<template>
    <div
        class="input-container"
        :class="{
            'form-row': formInput.isFormRow,
            'no-margin': formInput.shouldHideMargin,
            'has-error': !!formInput.errorMessage
        }"
        @blur="onInputBlur"
    >
        <label
            v-if="!formInput.shouldHideLabel"
            :for="`dp-input-${formInput.id}`"
        >
            {{ formInput.label }}
            <span v-if="isRequired" class="required-indicator">*</span>
        </label>
        <!-- https://vue3datepicker.com/slots/components/ -->
        <VueDatePicker
            ref="datepicker"
            :uid="formInput.id"
            :name="formInput.name"
            :placeholder="formInput.placeholder"
            :model-type="modelFormat"
            v-model="formInput.value"
            :autocomplete="isAutoComplete"
            :text-input="textInput"
            :disabled="isDisabled"
            :inline="isInline"
            :position="position"
            :teleport="teleport"
            :auto-apply="isAutoApply"
            :clearable="isClearable"
            :no-today="!isTodayHighlighted"
            :multi-calendars="multiCalendar"
            :range="enableRangePicker"
            :min-date="minDate"
            :max-date="maxDate"
            :prevent-min-max-navigation="(minDate || maxDate) ? preventMinMaxNavigation : false"
            :start-date="startDate || formInput.value || null"
            :allowed-dates="allowedDates"
            :disabled-dates="disabledDates"
            :year-range="yearRange"
            :enable-time-picker="enableTimePicker"
            :enable-seconds="enableSeconds"
            :min-time="minTime"
            :max-time="maxTime"
            :is-24="isTime24"
            @focus="focus"
            @open="onOpen(formInput)"
            @closed="onClose(formInput)"
            @update:model-value="input(formInput)"
            :loading="isLoading"
            :locale="$i18n.locale"
        >
            <template
                v-if="textInput && !textInput.openMenu"
                #dp-input="{ onEnter, onTab, onKeypress, onPaste, openMenu }"
            >
                <div class="dp__input_wrap">
                    <input
                        :id="`dp-input-${formInput.id}`"
                        type="text"
                        v-model="localValue"
                        @input="onInput"
                        @keydown.enter.stop="onEnter"
                        @keyup.enter.stop
                        @keydown.tab="onTab"
                        @blur="onInputBlur"
                        @keypress="onKeypress"
                        @paste="onPaste"
                        @click.stop
                        @focus.stop
                        class="dp__input dp__input_icon_pad"
                        :placeholder="formInput.placeholder"
                        :disabled="isDisabled"
                        :aria-label="formInput.label"
                        :name="formInput.name"
                        :autocomplete="isAutoComplete"
                        maxlength="10"
                    />
                    <div>
                        <svg
                            xmlns="http://www.w3.org/2000/svg"
                            viewBox="0 0 32 32"
                            fill="currentColor"
                            :id="`dp-input-icon-open-${formInput.id}`"
                            class="dp__icon dp__input_icon dp__input_icons"
                            @click="openMenu"
                            @keydown.enter="openMenu"
                            @keydown.space.prevent="openMenu"
                            tabindex="0"
                            role="button"
                            aria-label="Open calendar"
                            :aria-disabled="isDisabled"
                        >
                            <path d="M29.333 8c0-2.208-1.792-4-4-4h-18.667c-2.208 0-4 1.792-4 4v18.667c0
                            2.208 1.792 4 4 4h18.667c2.208 0 4-1.792 4-4v-18.667zM26.667 8v18.667c0
                            0.736-0.597 1.333-1.333 1.333 0 0-18.667 0-18.667 0-0.736
                            0-1.333-0.597-1.333-1.333 0 0 0-18.667 0-18.667 0-0.736 0.597-1.333
                            1.333-1.333 0 0 18.667 0 18.667 0 0.736 0 1.333 0.597 1.333 1.333z"></path>
                            <path d="M20 2.667v5.333c0 0.736 0.597 1.333 1.333 1.333s1.333-0.597
                            1.333-1.333v-5.333c0-0.736-0.597-1.333-1.333-1.333s-1.333 0.597-1.333 1.333z"></path>
                            <path d="M9.333 2.667v5.333c0 0.736 0.597 1.333 1.333 1.333s1.333-0.597
                            1.333-1.333v-5.333c0-0.736-0.597-1.333-1.333-1.333s-1.333 0.597-1.333 1.333z"></path>
                            <path d="M4 14.667h24c0.736 0 1.333-0.597
                            1.333-1.333s-0.597-1.333-1.333-1.333h-24c-0.736 0-1.333 0.597-1.333
                            1.333s0.597 1.333 1.333 1.333z"></path>
                        </svg>
                    </div>
                </div>
            </template>
            <template #clear-icon="{}"></template>
        </VueDatePicker>
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputDate.ts"></script>
<style scoped lang="less" src="./InputDate.less"></style>
