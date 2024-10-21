<!--
    SelectPrivileges.vue
    CompactConnect

    Created by InspiringApps on 10/15/2024.
-->

<template>
    <div class="select-privileges-container">
        <form @submit.prevent="handleSubmit">
            <div v-if="isMobile" class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    aria-label="close modal"
                    class="icon icon-close-modal"
                    @click="closeModal"
                />
                <InputButton
                    :label="backText"
                    aria-label="close modal"
                    class="icon icon-close-modal"
                    @click="closeModal"
                />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen"
                />
            </div>
            <div class="select-privileges-core-container">
                <div class="state-select-list">
                    <div v-for="state in stateCheckList" :key="state.label" class="state-select-unit">
                        <InputCheckbox :formInput="state" @change="handleStateClicked" />
                    </div>
                </div>
                <div class="selected-state-list">
                    <div
                        v-for="state in selectedStatePurchaseDataList"
                        :key="state.jurisdiction.abbrev"
                        class="selected-state-block"
                    >
                        <div class="state-title info-row">{{state.jurisdiction.name()}}</div>
                        <div class="info-row"><div class="info-row-label">{{expirationDateText}}</div></div>
                    </div>
                </div>
            </div>
            <div class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    aria-label="close modal"
                    class="icon icon-close-modal"
                    @click="closeModal"
                />
                <InputButton
                    :label="backText"
                    aria-label="close modal"
                    class="icon icon-close-modal"
                    @click="closeModal"
                />
                <InputSubmit
                    :formInput="formData.submit"
                    :label="submitLabel"
                    :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen"
                />
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./SelectPrivileges.ts"></script>
<style scoped lang="less" src="./SelectPrivileges.less"></style>
