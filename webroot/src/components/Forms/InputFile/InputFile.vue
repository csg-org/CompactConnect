<!--
    InputFile.vue
    inHere

    Created by InspiringApps on 7/8/2020.
-->

<template>
    <div
        ref="inputContainer"
        class="input-container"
        :class="{
            'form-row': formInput.isFormRow,
            'has-error': !!formInput.errorMessage,
            'is-drag-over': isDragOver,
        }"
        @dragenter.prevent="dragEnter"
    >
        <div
            class="drop-mask"
            :class="{ 'is-drag-over': isDragOver }"
            @dragenter.prevent
            @dragover.prevent
            @dragleave.prevent="dragLeave"
            @drop.prevent="drop"
        ></div>
        <div
            v-if="!formInput.shouldHideLabel"
            class="input-label"
        >
            {{ formInput.label }}
            <span v-if="isRequired" class="required-indicator">*</span>
        </div>
        <div v-if="formInput.fileConfig.hint" class="hint">
            {{ formInput.fileConfig.hint }}
        </div>
        <input
            type="file"
            ref="inputFiles"
            :id="formInput.id"
            :name="formInput.name"
            :placeholder="formInput.placeholder"
            :aria-label="formInput.label"
            :accept="formInput.fileConfig.accepts"
            :multiple="formInput.fileConfig.allowMultiple"
            @blur="blur(formInput)"
            @change="input(formInput)"
            class="input-file"
            :class="{ 'has-error': !!formInput.errorMessage }"
        />
        <div class="input-file-container">
            <label :for="formInput.id" class="add-files transparent">
                <UploadFileIcon class="icon-upload-file" />
                {{ selectLabel }}
            </label>
            <div v-if="selectedFiles.length" class="selected-files">
                <div
                    v-for="(file, index) in $refs.inputFiles.files"
                    :key="index"
                    class="selected-file"
                    :class="{ 'has-error': !!file.ia_errorMessage }"
                >
                    <div class="file-name">{{ file.name }}</div>
                    <div class="file-size">({{ formatBytes(file.size, 1) }})</div>
                </div>
            </div>
        </div>
        <span
            v-if="formInput.errorMessage"
            class="form-field-error"
        >
            {{ formInput.errorMessage }}
        </span>
    </div>
</template>

<script lang="ts" src="./InputFile.ts"></script>
<style scoped lang="less" src="./InputFile.less"></style>
