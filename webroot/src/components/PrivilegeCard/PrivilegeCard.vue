<!--
    PrivilegeCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="privilege-card-container">
        <div class="privilege-title-row" :class="{
            'active': isActive,
            'has-actions': isCurrentUserPrivilegeAdmin
        }">
            <div class="privilege-title-section">
                <div class="privilege-title">{{stateContent}}</div>
                <div class="license-type-abbrev">{{privilegeTypeAbbrev}}</div>
            </div>
            <div class="privilege-status" :class="{ 'active': isActive }">{{statusDisplay}}</div>
            <div v-if="isCurrentUserPrivilegeAdmin" class="privilege-actions">
                <div
                    class="privilege-actions-menu-toggle"
                    role="button"
                    :aria-label="$t('licensing.privilegeActions')"
                    @click="togglePrivilegeActionMenu"
                    @keyup.enter="togglePrivilegeActionMenu"
                    tabindex="0"
                >
                    <span class="dot" /><span class="dot" /><span class="dot" />
                </div>
                <transition name="fade" mode="out-in">
                    <ul
                        v-if="isPrivilegeActionMenuDisplayed"
                        class="privilege-menu"
                        v-click-outside="closePrivilegeActionMenu"
                    >
                        <li
                            v-if="isCurrentUserCompactAdmin"
                            class="privilege-menu-item"
                            :class="{ 'disabled': !isActive, 'danger': isActive }"
                            role="button"
                            @click="toggleDeactivatePrivilegeModal"
                            @keyup.enter="toggleDeactivatePrivilegeModal"
                            tabindex="0"
                        >
                            {{ (isActive) ? $t('licensing.deactivate') : $t('licensing.deactivated') }}
                        </li>
                        <li
                            v-if="isCurrentUserPrivilegeStateAdmin"
                            class="privilege-menu-item danger"
                            role="button"
                            @click="toggleEncumberPrivilegeModal"
                            @keyup.enter="toggleEncumberPrivilegeModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.encumber') }}
                        </li>
                        <li
                            v-if="isCurrentUserPrivilegeStateAdmin && isEncumbered"
                            class="privilege-menu-item"
                            role="button"
                            @click="toggleUnencumberPrivilegeModal"
                            @keyup.enter="toggleUnencumberPrivilegeModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.unencumber') }}
                        </li>
                        <li
                            v-if="isCurrentUserPrivilegeStateAdmin"
                            class="privilege-menu-item new-section"
                            role="button"
                            @click="toggleAddInvestigationModal"
                            @keyup.enter="toggleAddInvestigationModal"
                            tabindex="0"
                        >
                            {{ $t('licensing.addInvestigation') }}
                        </li>
                        <li
                            v-if="isCurrentUserPrivilegeStateAdmin && isUnderInvestigation"
                            class="privilege-menu-item"
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
        <div class="privilege-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{ $t('licensing.activeFrom') }}</div>
                <div class="info-item">{{ (isActive) ? activeFromContent : $t('licensing.deactivated') }}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item" :class="{ 'error': isExpired }">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{$t('licensing.privilegeNumSymbol')}}</div>
                <div class="info-item rr-block">{{privilegeId}}</div>
            </div>
            <div class="info-item-container discipline-item">
                <div class="info-item-title">{{ $t('licensing.disciplineStatus') }}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <InputButton
            :label="$t('common.viewDetails')"
            :aria-label="$t('common.viewDetails')"
            class="view-details-button"
            :isTransparent="true"
            @click="goToPrivilegeDetailsPage"
        />
        <TransitionGroup>
            <Modal
                v-if="isDeactivatePrivilegeModalDisplayed"
                modalId="deactivate-privilege-modal"
                class="privilege-edit-modal deactivate-privilege-modal"
                :title="$t('licensing.confirmPrivilegeDeactivateTitle')"
                :showActions="false"
                @keydown.tab="focusTrapDeactivatePrivilegeModal($event)"
                @keyup.esc="closeDeactivatePrivilegeModal"
            >
                <template v-slot:content>
                    <div class="modal-content deactivate-modal-content">
                        {{ $t('licensing.confirmPrivilegeDeactivateSubtext') }}
                        <form class="privilege-edit-form" @submit.prevent="submitDeactivatePrivilege">
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
                                    id="deactivate-modal-cancel-button"
                                    class="action-button cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeDeactivatePrivilegeModal"
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
                v-if="isEncumberPrivilegeModalDisplayed"
                modalId="encumber-privilege-modal"
                class="privilege-edit-modal encumber-privilege-modal"
                :title="!isEncumberPrivilegeModalSuccess ? $t('licensing.confirmPrivilegeEncumberTitle') : ' '"
                :showActions="false"
                @keydown.tab="focusTrapEncumberPrivilegeModal($event)"
                @keyup.esc="closeEncumberPrivilegeModal"
            >
                <template v-slot:content>
                    <div v-if="!isEncumberPrivilegeModalSuccess" class="modal-content encumber-modal-content">
                        {{ $t('licensing.confirmPrivilegeEncumberSubtext') }}
                        <form
                            id="encumber-modal-form"
                            class="privilege-edit-form encumber-privilege-form"
                            @submit.prevent="submitEncumberPrivilege"
                        >
                            <div class="encumber-privilege-form-input-container">
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
                                    <div class="input-label static-label">{{ $t('licensing.privilegeId') }}</div>
                                    <div class="static-value">{{ privilegeId }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.privilegeType') }}</div>
                                    <div class="static-value">{{ privilegeTypeAbbrev }}</div>
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
                                    :onClick="closeEncumberPrivilegeModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.encumberModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('licensing.confirmPrivilegeEncumberSubmit')"
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
                        <h1 class="modal-title">{{ $t('licensing.confirmPrivilegeEncumberSuccess') }}</h1>
                        <div class="success-container">
                            <div class="input-label static-label">{{ licenseeName }}</div>
                            <div class="static-value">{{ privilegeId }}</div>
                        </div>
                        <InputButton
                            id="encumber-modal-cancel-button"
                            class="encumber-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeEncumberPrivilegeModal"
                        />
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isUnencumberPrivilegeModalDisplayed"
                modalId="unencumber-privilege-modal"
                class="privilege-edit-modal unencumber-privilege-modal"
                :title="!isUnencumberPrivilegeModalSuccess ? $t('licensing.confirmPrivilegeUnencumberTitle') : ' '"
                :showActions="false"
                @keydown.tab="focusTrapUnencumberPrivilegeModal($event)"
                @keyup.esc="closeUnencumberPrivilegeModal"
            >
                <template v-slot:content>
                    <div v-if="!isUnencumberPrivilegeModalSuccess" class="modal-content unencumber-modal-content">
                        <form
                            id="unencumber-modal-form"
                            class="privilege-edit-form unencumber-privilege-form"
                            @submit.prevent="submitUnencumberPrivilege"
                        >
                            <div class="unencumber-privilege-form-input-container">
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
                                    :onClick="closeUnencumberPrivilegeModal"
                                    :isEnabled="!isFormLoading"
                                />
                                <InputSubmit
                                    class="action-button submit-button continue-button"
                                    :formInput="formData.unencumberModalContinue"
                                    :label="(isFormLoading)
                                        ? $t('common.loading')
                                        : $t('licensing.confirmPrivilegeUnencumberSubmit')"
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
                        <h1 class="modal-title">{{ $t('licensing.confirmPrivilegeUnencumberSuccess') }}</h1>
                        <div class="success-container">
                            <div
                                v-for="(selected) in selectedEncumbrances"
                                :key="selected.id"
                                class="removed-encumbrance"
                            >
                                <div class="input-label static-label">{{ selected.npdbTypeName() }}</div>
                                <div class="static-value">
                                    {{ $t('licensing.confirmPrivilegeUnencumberSuccessEndDate') }}:
                                    {{ dateDisplayFormat(formData[`adverse-action-end-date-${selected.id}`].value) }}
                                </div>
                            </div>
                        </div>
                        <InputButton
                            id="unencumber-modal-cancel-button"
                            class="unencumber-modal-cancel-button"
                            :label="$t('common.close')"
                            :onClick="closeUnencumberPrivilegeModal"
                        />
                    </div>
                </template>
            </Modal>
            <Modal
                v-if="isAddInvestigationModalDisplayed"
                modalId="add-investigation-privilege-modal"
                class="privilege-edit-modal add-investigation-privilege-modal"
                :title="!isAddInvestigationModalSuccess ? $t('licensing.confirmPrivilegeInvestigationStartTitle') : ' '"
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
                        {{ $t('licensing.confirmPrivilegeInvestigationStartSubtext') }}
                        <form class="privilege-edit-form" @submit.prevent="submitAddInvestigation">
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
                                    <div class="input-label static-label">{{ $t('licensing.privilegeId') }}</div>
                                    <div class="static-value">{{ privilegeId }}</div>
                                </div>
                                <div class="static-input">
                                    <div class="input-label static-label">{{ $t('licensing.privilegeType') }}</div>
                                    <div class="static-value">{{ privilegeTypeAbbrev }}</div>
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
                                        : $t('licensing.confirmPrivilegeInvestigationStartSubmit')"
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
                            <h1 class="modal-title">{{ $t('licensing.confirmPrivilegeInvestigationStartSuccess') }}</h1>
                            <div class="success-container">
                                <div class="input-label static-label">{{ licenseeName }}</div>
                                <div class="static-value">{{ privilegeId }}</div>
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
                modalId="end-investigation-privilege-modal"
                class="privilege-edit-modal end-investigation-privilege-modal"
                :title="endInvestigationModalTitle"
                :showActions="false"
                @keydown.tab="focusTrapEndInvestigationModal($event)"
                @keyup.esc="closeEndInvestigationModal"
            >
                <template v-slot:content>
                    <div v-if="!isEndInvestigationModalConfirm && !isEndInvestigationModalSuccess"
                        class="modal-content end-investigation-modal-content"
                        tabindex="0"
                        aria-live="polite"
                        role="status"
                    >
                        <form
                            id="end-investigation-modal-form"
                            class="privilege-edit-form end-investigation-privilege-form"
                            @submit.prevent="continueToEndInvestigationConfirm"
                        >
                            <div class="end-investigation-privilege-form-input-container">
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
                            {{ $t('licensing.confirmPrivilegeInvestigationEndSubtext1', {
                                date: selectedInvestigation.startDateDisplay()
                            }) }}
                        </p>
                        <p class="info-block">
                            {{ $t('licensing.confirmPrivilegeInvestigationEndSubtext2') }}
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
                                :label="$t('licensing.confirmPrivilegeInvestigationEndSubmitWithoutEncumber')"
                                :onClick="submitEndInvestigationWithoutEncumbrance"
                                :isEnabled="!isFormLoading"
                            />
                            <InputButton
                                id="submit-modal-continue"
                                class="action-button end-investigation-modal-with-encumbrance"
                                :label="$t('licensing.confirmPrivilegeInvestigationEndSubmitWithEncumber')"
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
                        <h1 class="modal-title">{{ $t('licensing.confirmPrivilegeInvestigationEndSuccess') }}</h1>
                        <div class="success-container">
                            <div class="input-label static-label">{{ licenseeName }}</div>
                            <div class="static-value">{{ privilegeId }}</div>
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

<script lang="ts" src="./PrivilegeCard.ts"></script>
<style scoped lang="less" src="./PrivilegeCard.less"></style>
