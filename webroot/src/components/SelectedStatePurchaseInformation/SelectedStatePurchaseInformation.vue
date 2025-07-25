<!--
    SelectedStatePurchaseInformation.vue
    CompactConnect

    Created by InspiringApps on 11/12/2024.
-->

<template>
    <li class="selected-state-purchase-info-container">
        <div class="info-row">
            <div class="state-title">{{selectedStatePurchaseData.jurisdiction.name()}}</div>
            <button
                v-if="!isPriceCollapsed"
                class="deselect-state"
                :aria-label="$t('licensing.deselectState')"
                @click="deselectState()"
                @keyup.enter="deselectState()"
            >X</button>
        </div>
        <div v-if="!isPriceCollapsed">
            <div class="info-row sub-row">
                <div class="info-row-label">{{ $t('licensing.expirationDate') }}</div>
                <div class="expire-date-value">{{selectedLicenseExpirationDate}}</div>
            </div>
            <div class="info-row sub-row">
                <div class="info-row-label">{{jurisdictionFeeText}}</div>
                <div class="fee-display-value">${{feeDisplay}}</div>
            </div>
            <div class="info-row sub-row">
                <div class="info-row-label">{{ $t('licensing.adminFee') }}</div>
                <div class="fee-display-value">${{currentCompactCommissionFeeDisplay}}</div>
            </div>
            <div class="info-row total-row">
                <div class="info-row-label">{{ $t('common.subtotal') }}</div>
                <div class="subtotal-value">${{subTotal}}</div>
            </div>
        </div>
        <div v-if="selectedStatePurchaseData.isJurisprudenceRequired" class="jurisprudence-check-box">
            <InputCheckbox
                :formInput="jurisprudenceCheckInput"
                @change="handleJurisprudenceClicked()"
            />
            <div
                v-if="selectedStatePurchaseData.jurisprudenceInfoUri"
                class="jurisprudence-info-link-container"
                :class="{ 'error': !!jurisprudenceCheckInput.errorMessage }"
            >
                <a
                    :href="selectedStatePurchaseData.jurisprudenceInfoUri"
                    class="jurisprudence-info-link"
                    target="_blank"
                    rel="noopener noreferrer"
                    :aria-label="$t('common.moreInfo')"
                    tabindex="0"
                >
                    {{ $t('common.moreInfo') }}
                </a>
            </div>
        </div>
        <div class="jurisprudence-check-box">
            <InputCheckbox
                :formInput="scopeOfPracticeCheckInput"
                @change="handleScopeOfPracticeClicked()"
            />
        </div>
        <div class="collapse-button-container">
            <CollapseCaretButton
                v-if="isPhone"
                @toggleCollapse="togglePriceCollapsed"
            />
        </div>
        <Modal
            v-if="isJurisprudencePending"
            class="attestation-modal"
            :closeOnBackgroundClick="true"
            :showActions="false"
            :title="$t('licensing.jurisprudenceConfirmation')"
            @close-modal="closeAndInvalidateJurisprudenceCheckbox"
            @keydown.tab="focusTrapJurisprudence($event)"
            @keyup.esc="closeAndInvalidateJurisprudenceCheckbox"
        >
            <template v-slot:content>
                <div class="attestation-modal-content">
                    <div v-html="jurisprudenceModalContent"/>
                    <form @submit.prevent="submitJurisprudenceUnderstanding">
                        <div class="action-button-row">
                            <InputButton
                                id="modal-back-button"
                                ref="backButton"
                                class="back-button"
                                :label="$t('common.back')"
                                :isTransparent="true"
                                :onClick="closeAndInvalidateJurisprudenceCheckbox"
                            />
                            <InputSubmit
                                class="understand-button"
                                :formInput="formData.submitJurisprudenceUnderstanding"
                                :label="$t('licensing.iUnderstand')"
                            />
                        </div>
                    </form>
                </div>
            </template>
        </Modal>
        <Modal
            v-if="isScopeOfPracticePending"
            class="attestation-modal"
            :closeOnBackgroundClick="true"
            :showActions="false"
            :title="$t('licensing.scopeAttestTitle')"
            @close-modal="closeAndInvalidateScopeCheckbox"
            @keydown.tab="focusTrapScope($event)"
            @keyup.esc="closeAndInvalidateScopeCheckbox"
        >
            <template v-slot:content>
                <div class="attestation-modal-content">
                    <div v-html="scopeModalContent"/>
                    <form @submit.prevent="submitScopeUnderstanding">
                        <div class="action-button-row">
                            <InputButton
                                id="modal-back-button"
                                ref="backButton"
                                class="back-button"
                                :label="$t('common.back')"
                                :isTransparent="true"
                                :onClick="closeAndInvalidateScopeCheckbox"
                            />
                            <InputSubmit
                                class="understand-button"
                                :formInput="formData.submitScopeUnderstanding"
                                :label="$t('licensing.iUnderstand')"
                            />
                        </div>
                    </form>
                </div>
            </template>
        </Modal>
    </li>
</template>

<script lang="ts" src="./SelectedStatePurchaseInformation.ts"></script>
<style scoped lang="less" src="./SelectedStatePurchaseInformation.less"></style>
