<!--
    LicenseActionsModal.vue
    CompactConnect

    Created by InspiringApps on 9/23/2026.
-->

<template>
    <div
        class="license-actions-modal"
        :class="{
            [`type-${type}`]: true,
            'license-actions': shouldShowMenu,
        }"
    >
        <template v-if="shouldShowMenu">
            <div
                class="license-actions-menu-toggle"
                :class="{ 'active': isActive && !isPrivilege }"
                role="button"
                :aria-label="menuAriaLabel"
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
                        v-if="shouldShowDeactivateMenuItem"
                        class="license-menu-item"
                        :class="{ 'disabled': !isActive, 'danger': isActive }"
                        role="button"
                        @click="toggleDeactivateLicenseModal"
                        @keyup.enter="toggleDeactivateLicenseModal"
                        tabindex="0"
                    >
                        {{ (isActive) ? $t('licensing.deactivate') : $t('licensing.deactivated') }}
                    </li>
                    <li
                        v-if="shouldShowDisciplineMenuItems"
                        class="license-menu-item danger"
                        role="button"
                        @click="openEncumberFromMenu"
                        @keyup.enter="openEncumberFromMenu"
                        tabindex="0"
                    >
                        {{ $t('licensing.encumber') }}
                    </li>
                    <li
                        v-if="shouldShowDisciplineMenuItems && isEncumbered"
                        class="license-menu-item"
                        role="button"
                        @click="openUnencumberLicenseModal"
                        @keyup.enter="openUnencumberLicenseModal"
                        tabindex="0"
                    >
                        {{ $t('licensing.unencumber') }}
                    </li>
                    <li
                        v-if="shouldShowDisciplineMenuItems"
                        class="license-menu-item new-section"
                        role="button"
                        @click="openAddInvestigationModal"
                        @keyup.enter="openAddInvestigationModal"
                        tabindex="0"
                    >
                        {{ $t('licensing.addInvestigation') }}
                    </li>
                    <li
                        v-if="shouldShowDisciplineMenuItems && isUnderInvestigation"
                        class="license-menu-item"
                        role="button"
                        @click="openEndInvestigationModal"
                        @keyup.enter="openEndInvestigationModal"
                        tabindex="0"
                    >
                        {{ $t('licensing.endInvestigation') }}
                    </li>
                </ul>
            </transition>
        </template>
        <TransitionGroup>
            <Modal
                v-if="isDeactivateLicenseModalDisplayed"
                :modalId="`deactivate-license-modal-${idPrefix}`"
                class="license-edit-modal deactivate-license-modal"
                :title="$t('licensing.confirmPrivilegeDeactivateTitle')"
                :showActions="false"
                @keydown.tab="focusTrapDeactivateLicenseModal($event)"
                @keyup.esc="closeDeactivateLicenseModal"
            >
                <template v-slot:content>
                    <div class="modal-content deactivate-modal-content">
                        {{ $t('licensing.confirmPrivilegeDeactivateSubtext') }}
                        <form class="license-edit-form" @submit.prevent="submitDeactivateLicense">
                            <MockPopulate
                                v-if="isMockPopulateEnabled"
                                :isEnabled="isMockPopulateEnabled"
                                @selected="mockPopulate"
                            />
                            <div class="form-row">
                                <InputTextarea
                                    class="deactivation-notes"
                                    :formInput="formData.deactivateModalNotes"
                                    :shouldResizeY="true"
                                />
                            </div>
                            <div
                                v-if="modalErrorMessage"
                                class="modal-error"
                                aria-live="assertive"
                                role="alert"
                            >{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    :id="ids.deactivateCancel"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeDeactivateLicenseModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.deactivateModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('licensing.confirmPrivilegeDeactivateSubmit')"
                                    :isWarning="true"
                                    :isEnabled="!isFormLoading"
                                />
                            </div>
                        </form>
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isEncumberLicenseModalDisplayed"
                :modalId="`encumber-license-modal-${idPrefix}`"
                class="license-edit-modal encumber-license-modal"
                :title="!isEncumberLicenseModalSuccess
                    ? $t(`licensing.confirm${i18nNoun}EncumberTitle`)
                    : ' '"
                :showActions="false"
                @keydown.tab="focusTrapEncumberLicenseModal($event)"
                @keyup.esc="closeEncumberLicenseModal"
            >
                <template v-slot:content>
                    <div v-if="!isEncumberLicenseModalSuccess" class="modal-content encumber-modal-content">
                        {{ $t(`licensing.confirm${i18nNoun}EncumberSubtext`) }}
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
                                <div v-if="!isPrivilege" class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.licenseNumber') }}</div>
                                    <div class="static-value rr-block">{{ licenseNumber }}</div>
                                </div>
                                <div v-else-if="$isAppGroupModePrivilegePurchase" class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.privilegeId') }}</div>
                                    <div class="static-value">{{ privilegeId }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">
                                        {{ isPrivilege
                                            ? $t('licensing.privilegeType')
                                            : $t('licensing.licenseType') }}
                                    </div>
                                    <div class="static-value">{{ licenseTypeAbbrev }}</div>
                                </div>
                            </div>
                            <div class="form-row">
                                <InputSelect :formInput="formData.encumberModalDisciplineAction" />
                            </div>
                            <div class="form-row">
                                <InputSelectMultiple
                                    v-if="shouldAllowNpdbMultiSelect"
                                    :formInput="formData.encumberModalNpdbCategories"
                                />
                                <InputSelect
                                    v-else
                                    :formInput="formData.encumberModalNpdbCategories"
                                />
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
                                    :id="ids.encumberCancel"
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
                                        : $t(`licensing.confirm${i18nNoun}EncumberSubmit`)"
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
                        <h1 class="modal-title">{{ $t(`licensing.confirm${i18nNoun}EncumberSuccess`) }}</h1>
                        <div class="success-container">
                            <div class="input-label static-label">{{ licenseeName }}</div>
                            <template v-if="!isPrivilege">
                                <div class="static-value">{{ stateContent }}</div>
                                <div class="static-value">{{ licenseNumber }}</div>
                            </template>
                            <div v-else-if="$isAppGroupModePrivilegePurchase" class="static-value">
                                {{ privilegeId }}
                            </div>
                        </div>
                        <InputButton
                            :id="ids.encumberCancel"
                            class="encumber-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeEncumberLicenseModal"
                        />
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isUnencumberLicenseModalDisplayed"
                :modalId="`unencumber-license-modal-${idPrefix}`"
                class="license-edit-modal unencumber-license-modal"
                :title="!isUnencumberLicenseModalSuccess
                    ? $t(`licensing.confirm${i18nNoun}UnencumberTitle`)
                    : ' '"
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
                                    :id="ids.unencumberCancel"
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
                                        : $t(`licensing.confirm${i18nNoun}UnencumberSubmit`)"
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
                        <h1 class="modal-title">{{ $t(`licensing.confirm${i18nNoun}UnencumberSuccess`) }}</h1>
                        <div class="success-container">
                            <div
                                v-for="(selected) in selectedEncumbrances"
                                :key="selected.id"
                                class="removed-encumbrance"
                            >
                                <div class="input-label static-label">{{ selected.encumbranceTypeName() }}</div>
                                <div class="static-value">
                                    {{ $t(`licensing.confirm${i18nNoun}UnencumberSuccessEndDate`) }}:
                                    {{ dateDisplayFormat(formData[`adverse-action-end-date-${selected.id}`].value) }}
                                </div>
                            </div>
                        </div>
                        <InputButton
                            :id="ids.unencumberCancel"
                            class="unencumber-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeUnencumberLicenseModal"
                        />
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isAddInvestigationModalDisplayed"
                :modalId="`add-investigation-license-modal-${idPrefix}`"
                class="license-edit-modal add-investigation-license-modal"
                :title="!isAddInvestigationModalSuccess
                    ? $t(`licensing.confirm${i18nNoun}InvestigationStartTitle`)
                    : ' '"
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
                        {{ $t(`licensing.confirm${i18nNoun}InvestigationStartSubtext`) }}
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
                                <div v-if="!isPrivilege" class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.licenseNumber') }}</div>
                                    <div class="static-value rr-block">{{ licenseNumber }}</div>
                                </div>
                                <div v-else-if="$isAppGroupModePrivilegePurchase" class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.privilegeId') }}</div>
                                    <div class="static-value">{{ privilegeId }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">
                                        {{ isPrivilege
                                            ? $t('licensing.privilegeType')
                                            : $t('licensing.licenseType') }}
                                    </div>
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
                                    :id="ids.addInvestigationCancel"
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
                                        : $t(`licensing.confirm${i18nNoun}InvestigationStartSubmit`)"
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
                            <h1 class="modal-title">
                                {{ $t(`licensing.confirm${i18nNoun}InvestigationStartSuccess`) }}
                            </h1>
                            <div class="success-container">
                                <div class="input-label static-label">{{ licenseeName }}</div>
                                <div v-if="!isPrivilege" class="static-value">{{ licenseNumber }}</div>
                                <div v-else-if="$isAppGroupModePrivilegePurchase" class="static-value">
                                    {{ privilegeId }}
                                </div>
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
                :modalId="`end-investigation-license-modal-${idPrefix}`"
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
                            :id="`end-investigation-modal-form-${idPrefix}`"
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
                                    :id="ids.endInvestigationCancel"
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
                            {{ $t(`licensing.confirm${i18nNoun}InvestigationEndSubtext1`, {
                                date: selectedInvestigation.startDateDisplay()
                            }) }}
                        </p>
                        <p class="info-block">
                            {{ $t(`licensing.confirm${i18nNoun}InvestigationEndSubtext2`) }}
                        </p>
                        <div class="action-button-row">
                            <InputButton
                                :id="ids.endInvestigationCancel"
                                class="action-button end-investigation-modal-cancel-button"
                                :label="$t('common.cancel')"
                                :isTransparent="true"
                                :onClick="closeEndInvestigationModal"
                                :isEnabled="!isFormLoading"
                            />
                            <InputButton
                                :id="ids.endInvestigationNoEncumbrance"
                                class="action-button end-investigation-modal-no-encumbrance"
                                :label="$t(`licensing.confirm${i18nNoun}InvestigationEndSubmitWithoutEncumber`)"
                                :onClick="submitEndInvestigationWithoutEncumbrance"
                                :isEnabled="!isFormLoading"
                            />
                            <InputButton
                                :id="ids.submit"
                                class="action-button end-investigation-modal-with-encumbrance"
                                :label="$t(`licensing.confirm${i18nNoun}InvestigationEndSubmitWithEncumber`)"
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
                        <h1 class="modal-title">
                            {{ $t(`licensing.confirm${i18nNoun}InvestigationEndSuccess`) }}
                        </h1>
                        <div class="success-container">
                            <div class="input-label static-label">{{ licenseeName }}</div>
                            <div v-if="!isPrivilege" class="static-value">{{ licenseNumber }}</div>
                            <div v-else-if="$isAppGroupModePrivilegePurchase" class="static-value">
                                {{ privilegeId }}
                            </div>
                        </div>
                        <InputButton
                            :id="ids.endInvestigationCancel"
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

<script lang="ts" src="./LicenseActionsModal.ts"></script>
<style scoped lang="less" src="./LicenseActionsModal.less"></style>
