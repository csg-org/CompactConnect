<!--
    InputEmailList.vue
    CompactConnect

    Created by InspiringApps on 5/13/2025.
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
            :for="formInput.id"
        >
            <div>
                {{ formInput.label }}
                <span v-if="isRequired" class="required-indicator">*</span>
            </div>
            <div
                v-if="formInput.labelSubtext"
                v-html="formInput.labelSubtext"
                class="input-label-subtext"
            >
            </div>
        </label>
        <div class="input-row">
            <input
                type="text"
                :id="formInput.id"
                :name="formInput.name"
                :placeholder="formInput.placeholder"
                ref="email"
                :autocomplete="formInput.autocomplete"
                :aria-label="formInput.label"
                @blur="blur(formInput)"
                @input="input(formInput)"
                class="email-input"
                :class="{ 'has-error': !!formInput.errorMessage }"
                :disabled="formInput.isDisabled"
            />
            <button
                class="btn-add-email"
                @click.stop.prevent="add(formInput)"
                :aria-label="$t('common.add')"
                tabindex="-1"
            ></button>
        </div>
        <span class="separator"></span>
        <span
            v-if="formInput.errorMessage && !formInput.shouldHideErrorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
        <ul class="email-tag-container">
            <li
                v-for="(email, index) in formInput.value"
                :key="index"
                class="email-tag"
            >
                <span class="email">{{ email }}</span>
                <CloseXIcon
                    class="remove-email"
                    role="button"
                    :aria-label="$t('common.remove')"
                    @click="remove(email)"
                    @keyup.enter="remove(email)"
                    tabindex="0"
                />
            </li>
        </ul>
    </div>
</template>

<script lang="ts" src="./InputEmailList.ts"></script>
<style scoped lang="less" src="./InputEmailList.less"></style>
