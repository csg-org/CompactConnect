<!--
    SelectPrivileges.vue
    CompactConnect

    Created by InspiringApps on 10/15/2024.
-->

<template>
    <div class="select-privileges-container">
        <form class="privilege-form" @submit.prevent="handleSubmit">
            <div class="select-privileges-core-container">
                <div class="select-privileges-title">
                    {{selectPrivilegesTitleText}}
                </div>
                <div class="lists-container">
                    <ul class="state-select-list">
                        <li
                            v-for="state in stateCheckList"
                            :key="state.label"
                            class="state-unit"
                        >
                            <div v-if="checkIfStateSelectIsDisabled(state)" class="state-select-unit">
                                <div class="disabled-state-overlay" />
                                <InputCheckbox
                                    :formInput="state"
                                />
                            </div>
                            <div
                                v-else
                                class="state-select-unit"
                            >
                                <div
                                    @click.prevent="toggleStateSelected(state)"
                                    @keyup.enter="toggleStateSelected(state)"
                                    tabindex="0"
                                    class="enabled-state-overlay"
                                />
                                <InputCheckbox
                                    :formInput="state"
                                />
                            </div>
                            <SelectedStatePurchaseInformation
                                v-if="isPhone && findStatePurchaseInformation(state)"
                                class="selected-state-block"
                                :selectedStatePurchaseData="findStatePurchaseInformation(state)"
                                :jurisprudenceCheckInput="formData.jurisprudenceConfirmations[state.id]"
                                @exOutState="deselectState"
                            />
                        </li>
                    </ul>
                    <ul v-if="!isPhone" class="selected-state-list">
                        <SelectedStatePurchaseInformation
                            v-for="(state) in selectedStatePurchaseDataList"
                            :key="state.jurisdiction.abbrev"
                            class="selected-state-block"
                            :selectedStatePurchaseData="state"
                            :jurisprudenceCheckInput="formData.jurisprudenceConfirmations[state.jurisdiction.abbrev]"
                            @exOutState="deselectState"
                        />
                    </ul>
                </div>
            </div>
            <div class="button-row">
                <InputButton
                    :label="cancelText"
                    :isTextLike="true"
                    aria-label="close modal"
                    class="icon icon-close-modal"
                    @click="handleCancelClicked"
                />
                <div class="right-cell">
                    <InputButton
                        :label="backText"
                        aria-label="close modal"
                        class="back-button"
                        @click="handleBackClicked"
                    />
                    <InputSubmit
                        :formInput="formData.submit"
                        :label="submitLabel"
                        :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen && areAllJurisprudenceConfirmed"
                    />
                </div>
            </div>
        </form>
    </div>
</template>

<script lang="ts" src="./SelectPrivileges.ts"></script>
<style scoped lang="less" src="./SelectPrivileges.less"></style>
