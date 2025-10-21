<!--
    InputLabel.vue
    CompactConnect

    Created by InspiringApps on 10/21/2025.
-->

<template>
    <label
        v-if="!formInput.shouldHideLabel"
        :for="labelFor"
        class="label-container"
    >
        <div>
            {{ formInput.label }}
            <span v-if="isRequired" class="required-indicator">*</span>
        </div>
        <div v-if="formInput.labelInfo" class="label-info-container" v-click-outside="hideInfoBlock">
            <div
                class="info-toggle"
                role="button"
                @click.stop.prevent="toggleInfoBlock"
                @keyup.enter="toggleInfoBlock"
                :aria-label="`${$t('common.toggleInfoFor')} ${formInput.label}`"
                :aria-describedby="(shouldShowInfoBlock) ? `label-info-block-${formInput.id}` : undefined"
                :aria-expanded="shouldShowInfoBlock"
                tabindex="0"
            >
                <InfoIcon class="info-icon"/>
            </div>
            <Transition name="fade" :mode="elementTransitionMode">
                <div v-if="shouldShowInfoBlock" class="collapsible-info-wrapper">
                    <div class="block-connector" />
                    <div
                        :id="`label-info-block-${formInput.id}`"
                        class="label-info-block"
                        v-html="formInput.labelInfo"
                    />
                </div>
            </Transition>
        </div>
        <div
            v-if="formInput.labelSubtext"
            v-html="formInput.labelSubtext"
            class="input-label-subtext"
        ></div>
    </label>
</template>

<script lang="ts" src="./InputLabel.ts"></script>
<style scoped lang="less" src="./InputLabel.less"></style>
