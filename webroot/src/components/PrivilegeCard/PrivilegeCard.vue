<!--
    PrivilegeCard.vue
    CompactConnect

    Created by InspiringApps on 10/8/2024.
-->

<template>
    <div class="privilege-card-container">
        <div class="privilege-title-row" :class="{ 'has-actions': isCurrentUserPrivilegeAdmin }">
            <div class="privilege-title-section">
                <div class="privilege-title">{{stateContent}}</div>
                <div class="license-type-abbrev">{{privilegeTypeAbbrev}}</div>
            </div>
            <div class="privilege-status" :class="{ 'italics': !isActive, 'bold': isActive }">
                {{statusDisplay}}
            </div>
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
                            class="privilege-menu-item"
                            :class="{ 'disabled': !isActive, 'danger': isActive }"
                            role="button"
                            @click="toggleDeactivatePrivilegeModal"
                            @keyup.enter="toggleDeactivatePrivilegeModal"
                            tabindex="0"
                        >
                            {{ (isActive) ? $t('licensing.deactivate') : $t('licensing.deactivated') }}
                        </li>
                    </ul>
                </transition>
            </div>
        </div>
        <div class="privilege-info-grid">
            <div class="info-item-container">
                <div class="info-item-title">{{issuedTitle}}</div>
                <div class="info-item">{{issuedContent}}</div>
            </div>
           <div class="info-item-container">
                <div class="info-item-title">{{expiresTitle}}</div>
                <div class="info-item" :class="{ 'error': isPastExiprationDate }">{{expiresContent}}</div>
            </div>
            <div class="info-item-container">
                <div class="info-item-title">{{$t('licensing.privilegeNumSymbol')}}</div>
                <div class="info-item" >{{privilegeId}}</div>
            </div>
            <div class="info-item-container discipline-item">
                <div class="info-item-title">{{disciplineTitle}}</div>
                <div class="info-item">{{disciplineContent}}</div>
            </div>
        </div>
        <InputButton
            :label="viewDetails"
            :aria-label="viewDetails"
            class="view-details-button"
            :isTransparent="true"
            @click="goToPrivilegeDetailsPage"
        />
        <TransitionGroup>
            <Modal
                v-if="isDeactivatePrivilegeModalDisplayed"
                class="deactivate-privilege-modal"
                :title="stateContent"
                :showActions="false"
                @keydown.tab="focusTrapDeactivatePrivilegeModal($event)"
                @keyup.esc="closeDeactivatePrivilegeModal"
            >
                <template v-slot:content>
                    <div class="modal-content deactivate-modal-content">
                        {{ $t('licensing.confirmPrivilegeDeactivate') }}
                        <form @submit.prevent="submitDeactivatePrivilege">
                            <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="deactivate-modal-cancel-button"
                                    class="cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeDeactivatePrivilegeModal"
                                />
                                <InputSubmit
                                    class="submit-button continue-button"
                                    :formInput="formData.submitModalContinue"
                                    :label="(isFormLoading) ? $t('common.loading') : $t('common.continue')"
                                    :isEnabled="!isFormLoading"
                                />
                            </div>
                        </form>
                    </div>
                </template>
            </Modal>
        </TransitionGroup>
    </div>
</template>

<script lang="ts" src="./PrivilegeCard.ts"></script>
<style scoped lang="less" src="./PrivilegeCard.less"></style>
