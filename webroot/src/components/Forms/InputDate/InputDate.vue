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
            :text-input="isTextInput"
            :autocomplete="isAutoComplete"
            :disabled="isDisabled"
            :inline="isInline"
            :auto-apply="isAutoApply"
            :clearable="isClearable"
            :no-today="!isTodayHighlighted"
            :multi-calendars="multiCalendar"
            :range="enableRangePicker"
            :min-date="minDate"
            :max-date="maxDate"
            :prevent-min-max-navigation="(minDate || maxDate) ? preventMinMaxNavigation : false"
            :allowed-dates="allowedDates"
            :disabledDates="disabledDates"
            :year-range="yearRange"
            :enable-time-picker="enableTimePicker"
            :enable-seconds="enableSeconds"
            :min-time="minTime"
            :max-time="maxTime"
            :is-24="isTime24"
            @closed="blur(formInput)"
            @update:model-value="input(formInput)"
            :loading="isLoading"
            :locale="$i18n.locale"
        />
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
