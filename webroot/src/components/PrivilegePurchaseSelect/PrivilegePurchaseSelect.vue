<!--
    PrivilegePurchaseSelect.vue
    CompactConnect

    Created by InspiringApps on 10/15/2024.
-->

<template>
    <div>
        <div class="select-privileges-container">
            <form class="privilege-form" @submit.prevent="handleSubmit">
                <div class="select-privileges-core-container">
                    <div class="title-row">
                        <h1 class="select-privileges-title">
                            {{selectPrivilegesTitleText}}
                        </h1>
                        <SelectedLicenseInfo class="license-info" />
                    </div>
                    <LoadingSpinner v-if="isLoading"></LoadingSpinner>
                    <div v-else>
                        <MockPopulate
                            :isEnabled="isMockPopulateEnabled"
                            @selected="mockPopulate"
                            class="mock-populate"
                        />
                        <div class="lists-container">
                            <ul class="state-select-list">
                                <li
                                    v-for="state in stateCheckList"
                                    :key="state.label"
                                    class="state-unit"
                                >
                                    <div v-if="isStateSelectDisabled(state)" class="state-select-unit">
                                        <div class="disabled-state-overlay" />
                                        <InputCheckbox
                                            :formInput="state"
                                        />
                                    </div>
                                    <div
                                        v-else
                                        class="state-select-unit"
                                        :class="{ selected: state.value }"
                                    >
                                        <div
                                            @click.prevent="toggleStateSelected(state)"
                                            @keyup.enter="toggleStateSelected(state)"
                                            @keyup.space="toggleStateSelected(state)"
                                            tabindex="0"
                                            class="enabled-state-overlay"
                                        />
                                        <InputCheckbox
                                            :formInput="state"
                                        />
                                    </div>
                                    <Transition name="fade">
                                        <SelectedStatePurchaseInformation
                                            v-if="isPhone && findStatePurchaseInformation(state)"
                                            class="selected-state-block"
                                            :selectedStatePurchaseData="findStatePurchaseInformation(state)"
                                            :jurisprudenceCheckInput="formData[`jurisprudence-${state.id}`]"
                                            :scopeOfPracticeCheckInput="formData[`scope-${state.id}`]"
                                            :scopeAttestation="scopeAttestation"
                                            :jurisprudenceAttestation="jurisprudenceAttestation"
                                            @exOutState="deselectState"
                                        />
                                    </Transition>
                                </li>
                            </ul>
                            <TransitionGroup tag="ul" name="list" v-if="!isPhone" class="selected-state-list">
                                <SelectedStatePurchaseInformation
                                    v-for="(state) in selectedStatePurchaseDataList"
                                    :key="state.jurisdiction.abbrev"
                                    class="selected-state-block"
                                    :selectedStatePurchaseData="state"
                                    :jurisprudenceCheckInput="formData[`jurisprudence-${state.jurisdiction.abbrev}`]"
                                    :scopeOfPracticeCheckInput="formData[`scope-${state.jurisdiction.abbrev}`]"
                                    :scopeAttestation="scopeAttestation"
                                    :jurisprudenceAttestation="jurisprudenceAttestation"
                                    @exOutState="deselectState"
                                />
                            </TransitionGroup>
                        </div>
                    </div>
                </div>
                <div id="button-row" class="button-row">
                    <div class="form-nav-buttons">
                        <InputSubmit
                            :formInput="formData.submit"
                            class="form-nav-button"
                            :label="submitLabel"
                            :isEnabled="!isFormLoading && isAtLeastOnePrivilegeChosen"
                        />
                        <InputButton
                            :label="backText"
                            :aria-label="backText"
                            class="form-nav-button back-button"
                            :isTransparent="true"
                            @click="handleBackClicked"
                        />
                    </div>
                    <div class="form-override-buttons">
                        <InputButton
                            :label="cancelText"
                            :isTextLike="true"
                            :aria-label="cancelText"
                            class="form-override-button icon icon-close-modal"
                            @click="handleCancelClicked"
                        />
                    </div>
                </div>
            </form>
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegePurchaseSelect.ts"></script>
<style scoped lang="less" src="./PrivilegePurchaseSelect.less"></style>
