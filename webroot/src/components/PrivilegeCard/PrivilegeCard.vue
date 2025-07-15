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
                    </ul>
                </transition>
            </div>
        </div>
        <div class="privilege-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{ $t('licensing.issued') }}</div>
                <div class="info-item">{{issuedContent}}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item" :class="{ 'error': isExpired }">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{$t('licensing.privilegeNumSymbol')}}</div>
                <div class="info-item" >{{privilegeId}}</div>
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
                            <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
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
                            <div class="form-row input-container static-input">
                                <div class="input-label static-label">{{ $t('licensing.practitionerName') }}</div>
                                <div class="static-value">{{ licenseeName }}</div>
                            </div>
                            <div class="form-row input-container static-input">
                                <div class="input-label static-label">{{ $t('common.state') }}</div>
                                <div class="static-value">{{ stateContent }}</div>
                            </div>
                            <div class="form-row input-container static-input">
                                <div class="input-label static-label">{{ $t('licensing.privilegeId') }}</div>
                                <div class="static-value">{{ privilegeId }}</div>
                            </div>
                            <div class="form-row input-container static-input">
                                <div class="input-label static-label">{{ $t('licensing.privilegeType') }}</div>
                                <div class="static-value">{{ privilegeTypeAbbrev }}</div>
                            </div>
                            <div class="form-row">
                                <InputSelect :formInput="formData.encumberModalNpdbCategory" />
                            </div>
                            <div class="form-row">
                                <InputDate
                                    :formInput="formData.encumberModalStartDate"
                                    :yearRange="[new Date().getFullYear() - 5, new Date().getFullYear() + 5]"
                                    :preventMinMaxNavigation="true"
                                    :textInput="{ format: 'MM/dd/yyyy', openMenu: false }"
                                    :startDate="new Date()"
                                />
                            </div>
                            </div>
                            <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
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
                    <div v-else class="modal-content encumber-modal-content modal-content-success">
                        <div class="icon-container"><CheckCircleIcon /></div>
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
                                    :class="{ 'selected': isEncumbranceSelected(adverseAction) }"
                                    @click="clickUnencumberItem(adverseAction, $event)"
                                    @keyup.space="clickUnencumberItem(adverseAction, $event)"
                                >
                                    <InputCheckbox
                                        :formInput="formData[`adverse-action-data-${adverseAction.id}`]"
                                        class="unencumber-checkbox-input"
                                    />
                                    <div class="encumbrance-start-date">
                                        {{ adverseAction.startDateDisplay() }}
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
                            <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
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
                    <div v-else class="modal-content unencumber-modal-content modal-content-success">
                        <div class="icon-container"><CheckCircleIcon /></div>
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
        </TransitionGroup>
    </div>
</template>

<script lang="ts" src="./PrivilegeCard.ts"></script>
<style scoped lang="less" src="./PrivilegeCard.less"></style>
