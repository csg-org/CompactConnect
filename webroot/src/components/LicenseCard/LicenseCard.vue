<!--
    LicenseCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="license-card-container" :class="{ 'active': isActive }">
        <div class="license-heading-row">
            <div class="state-title">
                <div v-if="shouldIncludeLogo" class="license-icon-container">
                    <LicenseHomeIcon v-if="isHomeState && isActive" class="icon-license active" />
                    <LicenseIcon v-else class="icon-license" :class="{ 'active': isActive }" />
                </div>
                {{stateContent}}
            </div>
            <div class="license-status" :class="{ 'active': isActive }">{{statusDisplay}}</div>
            <div v-if="isCurrentUserLicenseStateAdmin" class="license-actions">
                <div
                    class="license-actions-menu-toggle"
                    :class="{ 'active': isActive }"
                    role="button"
                    :aria-label="$t('licensing.licenseActions')"
                    @click="toggleLicenseActionMenu"
                    @keyup.enter="toggleLicenseActionMenu"
                    tabindex="0"
                >
                    <span class="dot" /><span class="dot" /><span class="dot" />
                </div>
                <transition name="fade" mode="out-in">
                    <ul
                        v-if="isLicenseActionMenuDisplayed"
                        class="license-menu"
                        v-click-outside="closeLicenseActionMenu"
                    >
                        <li
                            v-if="isCurrentUserLicenseStateAdmin"
                            class="license-menu-item danger"
                            role="button"
                            @click="toggleEncumberLicenseModal"
                            @keyup.enter="toggleEncumberLicenseModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.encumber') }}
                        </li>
                        <li
                            v-if="isCurrentUserLicenseStateAdmin && isEncumbered"
                            class="license-menu-item"
                            role="button"
                            @click="toggleUnencumberLicenseModal"
                            @keyup.enter="toggleUnencumberLicenseModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.unencumber') }}
                        </li>
                        <li
                            v-if="isCurrentUserLicenseStateAdmin"
                            class="license-menu-item new-section"
                            role="button"
                            @click="toggleAddInvestigationModal"
                            @keyup.enter="toggleAddInvestigationModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.addInvestigation') }}
                        </li>
                        <li
                            v-if="isCurrentUserLicenseStateAdmin && isUnderInvestigation"
                            class="license-menu-item"
                            role="button"
                            @click="toggleEndInvestigationModal"
                            @keyup.enter="toggleEndInvestigationModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.endInvestigation') }}
                        </li>
                    </ul>
                </transition>
            </div>
        </div>
        <div class="license-heading-row">
            <div class="license-type-abbrev">{{licenseTypeAbbrev}}</div>
            <div class="license-status-description" ref="statusDescription">{{statusDescriptionDisplay}}</div>
        </div>
        <div class="license-info-grid">
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{$t('licensing.licenseNumSymbol')}}</div>
                <div class="info-item rr-block">{{licenseNumber}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{ $t('licensing.disciplineStatus') }}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <div v-if="isCompactEligible" class="license-eligibility-container">
            <div class="eligibility-icon-container eligible">
                <CheckCircleIcon class="eligibility-icon" />
            </div>
            {{ $t('licensing.compactEligible') }}
        </div>
        <div v-else class="license-eligibility-container" :class="{ 'inactive': !isActive }">
            <div class="eligibility-icon-container not-eligible">
                <CloseXIcon class="eligibility-icon" />
            </div>
            {{ $t('licensing.notCompactEligible') }}
        </div>
        <TransitionGroup>
            <Modal
                v-if="isEncumberLicenseModalDisplayed"
                modalId="encumber-license-modal"
                class="license-edit-modal encumber-license-modal"
                :title="!isEncumberLicenseModalSuccess ? $t('licensing.confirmLicenseEncumberTitle') : ' '"
                :showActions="false"
                @keydown.tab="focusTrapEncumberLicenseModal($event)"
                @keyup.esc="closeEncumberLicenseModal"
            >
                <template v-slot:content>
                    <div v-if="!isEncumberLicenseModalSuccess" class="modal-content encumber-modal-content">
                        {{ $t('licensing.confirmLicenseEncumberSubtext') }}
                        <form
                            class="license-edit-form encumber-license-form"
                            @submit.prevent="submitEncumberLicense"
                        >
                            <div class="encumber-license-form-input-container">
                            <MockPopulate
                                v-if="isMockPopulateEnabled"
                                :isEnabled="isMockPopulateEnabled"
                                @selected="mockPopulate"
                            />
                            <div class="form-row static-container">
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.practitionerName') }}</div>
                                    <div class="static-value">{{ licenseeName }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('common.state') }}</div>
                                    <div class="static-value">{{ stateContent }}</div>
                                </div>
                            </div>
                            <div class="form-row static-container">
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.licenseNumber') }}</div>
                                    <div class="static-value rr-block">{{ licenseNumber }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.licenseType') }}</div>
                                    <div class="static-value">{{ licenseTypeAbbrev }}</div>
                                </div>
                            </div>
                            <div class="form-row">
                                <InputSelect :formInput="formData.encumberModalDisciplineAction" />
                            </div>
                            <div v-if="$features.checkGate(featureGates.ENCUMBER_MULTI_CATEGORY)" class="form-row">
                                <InputSelectMultiple :formInput="formData.encumberModalNpdbCategories" />
                            </div>
                            <div v-else class="form-row">
                                <InputSelect :formInput="formData.encumberModalNpdbCategory" />
                            </div>
                            <div class="form-row">
                                <InputDate
                                    :formInput="formData.encumberModalStartDate"
                                    :yearRange="[new Date().getFullYear() - 5, new Date().getFullYear() + 5]"
                                    :preventMinMaxNavigation="true"
                                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                                    :startDate="new Date()"
                                    position="right"
                                    :teleport="true"
                                    @open="((formInput) => focusTrapTeleportedDatepicker(formInput, true))"
                                    @close="((formInput) => focusTrapTeleportedDatepicker(formInput, false))"
                                    @keyup.esc.stop
                                />
                            </div>
                            </div>
                            <div
                                v-if="modalErrorMessage"
                                class="modal-error"
                                aria-live="assertive"
                                role="alert"
                            >{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="encumber-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeEncumberLicenseModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.encumberModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('licensing.confirmLicenseEncumberSubmit')"
                                    :isWarning="true"
                                    :isEnabled="isFormValid && !isFormLoading"
                                />
                            </div>
                        </form>
                    </div>
                    <div v-else
                        class="modal-content encumber-modal-content modal-content-success"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <div class="icon-container"><CheckCircleIcon aria-hidden="true" /></div>
                        <h1 class="modal-title">{{ $t('licensing.confirmLicenseEncumberSuccess') }}</h1>
                        <div class="success-container">
                            <div class="input-label static-label">{{ licenseeName }}</div>
                            <div class="static-value">{{ stateContent }}</div>
                            <div class="static-value">{{ licenseNumber }}</div>
                        </div>
                        <InputButton
                            id="encumber-modal-cancel-button"
                            class="encumber-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeEncumberLicenseModal"
                        />
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isUnencumberLicenseModalDisplayed"
                modalId="unencumber-license-modal"
                class="license-edit-modal unencumber-license-modal"
                :title="!isUnencumberLicenseModalSuccess ? $t('licensing.confirmLicenseUnencumberTitle') : ' '"
                :showActions="false"
                @keydown.tab="focusTrapUnencumberLicenseModal($event)"
                @keyup.esc="closeUnencumberLicenseModal"
            >
                <template v-slot:content>
                    <div v-if="!isUnencumberLicenseModalSuccess" class="modal-content unencumber-modal-content">
                        <form
                            class="license-edit-form unencumber-license-form"
                            @submit.prevent="submitUnencumberLicense"
                        >
                            <div class="unencumber-license-form-input-container">
                            <MockPopulate
                                v-if="isMockPopulateEnabled"
                                :isEnabled="isMockPopulateEnabled"
                                @selected="mockPopulate"
                            />
                            <div
                                v-for="(adverseAction, index) in adverseActions"
                                :key="adverseAction.id || index"
                                class="form-row unencumber-row"
                            >
                                <div
                                    class="unencumber-select"
                                    :class="{
                                        'selected': isEncumbranceSelected(adverseAction),
                                        'inactive': adverseAction.hasEndDate(),
                                    }"
                                    @click="!adverseAction.hasEndDate()
                                        && clickUnencumberItem(adverseAction, $event)"
                                    @keyup.space="!adverseAction.hasEndDate()
                                        && clickUnencumberItem(adverseAction, $event)"
                                >
                                    <InputCheckbox
                                        v-if="!adverseAction.hasEndDate()"
                                        :formInput="formData[`adverse-action-data-${adverseAction.id}`]"
                                        class="unencumber-checkbox-input"
                                    />
                                    <div v-else class="inactive-category">
                                        {{ formData[`adverse-action-data-${adverseAction.id}`].label }}
                                    </div>
                                    <div class="encumbrance-dates">
                                        <span>{{ adverseAction.startDateDisplay() }}</span>
                                        <span v-if="adverseAction.endDateDisplay()">
                                            - {{ adverseAction.endDateDisplay() }}
                                        </span>
                                    </div>
                                </div>
                                <InputDate
                                    v-if="formData[`adverse-action-end-date-${adverseAction.id}`]"
                                    :formInput="formData[`adverse-action-end-date-${adverseAction.id}`]"
                                    :yearRange="[new Date().getFullYear() - 5, new Date().getFullYear() + 5]"
                                    :preventMinMaxNavigation="false"
                                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                                    :startDate="new Date()"
                                    position="right"
                                    :teleport="true"
                                    @open="((formInput) => focusTrapTeleportedDatepicker(formInput, true))"
                                    @close="((formInput) => focusTrapTeleportedDatepicker(formInput, false))"
                                    @keyup.esc.stop
                                    class="encumbrance-end-date"
                                />
                            </div>
                            </div>
                            <div
                                v-if="modalErrorMessage"
                                class="modal-error"
                                aria-live="assertive"
                                role="alert"
                            >{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="unencumber-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeUnencumberLicenseModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.unencumberModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('licensing.confirmLicenseUnencumberSubmit')"
                                    :isWarning="true"
                                    :isEnabled="isFormValid && !isFormLoading && selectedEncumbrances.length"
                                />
                            </div>
                        </form>
                    </div>
                    <div v-else
                        class="modal-content unencumber-modal-content modal-content-success"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <div class="icon-container"><CheckCircleIcon aria-hidden="true" /></div>
                        <h1 class="modal-title">{{ $t('licensing.confirmLicenseUnencumberSuccess') }}</h1>
                        <div class="success-container">
                            <div
                                v-for="(selected) in selectedEncumbrances"
                                :key="selected.id"
                                class="removed-encumbrance"
                            >
                                <div class="input-label static-label">{{ selected.npdbTypeName() }}</div>
                                <div class="static-value">
                                    {{ $t('licensing.confirmLicenseUnencumberSuccessEndDate') }}:
                                    {{ dateDisplayFormat(formData[`adverse-action-end-date-${selected.id}`].value) }}
                                </div>
                            </div>
                        </div>
                        <InputButton
                            id="unencumber-modal-cancel-button"
                            class="unencumber-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeUnencumberLicenseModal"
                        />
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isAddInvestigationModalDisplayed"
                modalId="add-investigation-license-modal"
                class="license-edit-modal add-investigation-license-modal"
                :title="!isAddInvestigationModalSuccess ? $t('licensing.confirmLicenseInvestigationStartTitle') : ' '"
                :showActions="false"
                @keydown.tab="focusTrapAddInvestigationModal($event)"
                @keyup.esc="closeAddInvestigationModal"
            >
                <template v-slot:content>
                    <div
                        v-if="!isAddInvestigationModalSuccess"
                        class="modal-content add-investigation-modal-content"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        {{ $t('licensing.confirmLicenseInvestigationStartSubtext') }}
                        <form class="license-edit-form" @submit.prevent="submitAddInvestigation">
                            <div class="add-investigation-form-input-container">
                            <div class="form-row static-container">
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.practitionerName') }}</div>
                                    <div class="static-value">{{ licenseeName }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('common.state') }}</div>
                                    <div class="static-value">{{ stateContent }}</div>
                                </div>
                            </div>
                            <div class="form-row static-container">
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.licenseNumber') }}</div>
                                    <div class="static-value rr-block">{{ licenseNumber }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.licenseType') }}</div>
                                    <div class="static-value">{{ licenseTypeAbbrev }}</div>
                                </div>
                            </div>
                            </div>
                            <div
                                v-if="modalErrorMessage"
                                class="modal-error"
                                aria-live="assertive"
                                role="alert"
                            >{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="add-investigation-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeAddInvestigationModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.addInvestigationModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('licensing.confirmLicenseInvestigationStartSubmit')"
                                    :isWarning="true"
                                    :isEnabled="!isFormLoading"
                                />
                            </div>
                        </form>
                    </div>
                    <div v-else
                        class="modal-content add-investigation-modal-content modal-content-success"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <form class="add-investigation-success-form" @submit.prevent="closeAddInvestigationModal">
                            <div class="icon-container"><CheckCircleIcon aria-hidden="true" /></div>
                            <h1 class="modal-title">{{ $t('licensing.confirmLicenseInvestigationStartSuccess') }}</h1>
                            <div class="success-container">
                                <div class="input-label static-label">{{ licenseeName }}</div>
                                <div class="static-value">{{ licenseNumber }}</div>
                            </div>
                            <InputSubmit
                                :formInput="formData.addInvestigationModalContinue"
                                class="add-investigation-modal-cancel-button"
                                :label="$t('common.close')"
                            />
                        </form>
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isEndInvestigationModalDisplayed"
                modalId="end-investigation-license-modal"
                class="license-edit-modal end-investigation-license-modal"
                :title="endInvestigationModalTitle"
                :showActions="false"
                @keydown.tab="focusTrapEndInvestigationModal($event)"
                @keyup.esc="closeEndInvestigationModal"
            >
                <template v-slot:content>
                    <div
                        v-if="!isEndInvestigationModalConfirm && !isEndInvestigationModalSuccess"
                        class="modal-content end-investigation-modal-content"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <form
                            id="end-investigation-modal-form"
                            class="license-edit-form end-investigation-license-form"
                            @submit.prevent="continueToEndInvestigationConfirm"
                        >
                            <div class="end-investigation-license-form-input-container">
                            <MockPopulate
                                v-if="isMockPopulateEnabled"
                                :isEnabled="isMockPopulateEnabled"
                                @selected="mockPopulate"
                            />
                            <div
                                v-for="(investigation, index) in investigations"
                                :key="investigation.id || index"
                                class="form-row end-investigation-row"
                            >
                                <div
                                    class="end-investigation-select"
                                    :class="{
                                        'selected': isInvestigationSelected(investigation),
                                        'inactive': investigation.hasEndDate(),
                                    }"
                                    @click="!investigation.hasEndDate()
                                        && clickEndInvestigationItem(investigation, $event)"
                                    @keyup.space="!investigation.hasEndDate()
                                        && clickEndInvestigationItem(investigation, $event)"
                                >
                                    <InputCheckbox
                                        v-if="!investigation.hasEndDate()"
                                        :formInput="formData[`end-investigation-data-${investigation.id}`]"
                                        class="end-investigation-checkbox-input"
                                    />
                                    <div v-else class="inactive-category">
                                        {{ formData[`end-investigation-data-${investigation.id}`].label }}
                                    </div>
                                    <div class="investigation-dates">
                                        <span v-if="investigation.hasEndDate()">
                                            {{ $t('licensing.investigationEndedOn', {
                                                date: investigation.endDateDisplay()
                                            }) }}
                                        </span>
                                    </div>
                                </div>
                            </div>
                            </div>
                            <div
                                v-if="modalErrorMessage"
                                class="modal-error"
                                aria-live="assertive"
                                role="alert"
                            >{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="end-investigation-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeEndInvestigationModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.endInvestigationModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('common.continue')"
                                    :isEnabled="isFormValid && !isFormLoading && selectedInvestigation"
                                />
                            </div>
                        </form>
                    </div>
                    <div
                        v-else-if="isEndInvestigationModalConfirm && !isEndInvestigationModalSuccess"
                        class="modal-content end-investigation-modal-content"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <p class="info-block">
                            {{ $t('licensing.confirmLicenseInvestigationEndSubtext1', {
                                date: selectedInvestigation.startDateDisplay()
                            }) }}
                        </p>
                        <p class="info-block">
                            {{ $t('licensing.confirmLicenseInvestigationEndSubtext2') }}
                        </p>
                        <div class="action-button-row">
                            <InputButton
                                id="end-investigation-modal-cancel-button"
                                class="action-button end-investigation-modal-cancel-button"
                                :label="$t('common.cancel')"
                                :isTransparent="true"
                                :onClick="closeEndInvestigationModal"
                                :isEnabled="!isFormLoading"
                            />
                            <InputButton
                                id="end-investigation-modal-no-encumbrance"
                                class="action-button end-investigation-modal-no-encumbrance"
                                :label="$t('licensing.confirmLicenseInvestigationEndSubmitWithoutEncumber')"
                                :onClick="submitEndInvestigationWithoutEncumbrance"
                                :isEnabled="!isFormLoading"
                            />
                            <InputButton
                                id="submit-modal-continue"
                                class="action-button end-investigation-modal-with-encumbrance"
                                :label="$t('licensing.confirmLicenseInvestigationEndSubmitWithEncumber')"
                                :isWarning="true"
                                :onClick="submitEndInvestigationWithEncumbrance"
                                :isEnabled="!isFormLoading"
                            />
                        </div>
                    </div>
                    <div v-else
                        class="modal-content end-investigation-modal-content modal-content-success"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <div class="icon-container"><CheckCircleIcon aria-hidden="true" /></div>
                        <h1 class="modal-title">{{ $t('licensing.confirmLicenseInvestigationEndSuccess') }}</h1>
                        <div class="success-container">
                            <div class="input-label static-label">{{ licenseeName }}</div>
                            <div class="static-value">{{ licenseNumber }}</div>
                        </div>
                        <InputButton
                            id="end-investigation-modal-cancel-button"
                            class="end-investigation-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeEndInvestigationModal"
                        />
                    </div>
                </template>
            </Modal>
        </TransitionGroup>
    </div>
</template>

<script lang="ts" src="./LicenseCard.ts"></script>
<style scoped lang="less" src="./LicenseCard.less"></style>
