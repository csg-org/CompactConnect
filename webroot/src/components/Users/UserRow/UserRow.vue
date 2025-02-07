<!--
    UserRow.vue
    CompactConnect

    Created by InspiringApps on 9/4/2024.
-->

<template>
    <div
        class="user-row is-wrap"
        :class="{ 'is-header': isHeaderRow }"
        role="row"
    >
        <div class="cell-content main-content">
            <div
                v-if="$matches.desktop.min"
                class="cell expand-collapse"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <RightCaretIcon
                    v-if="!isHeaderRow"
                    class="action-arrow"
                    :class="{ 'active': isRowExpanded }"
                    @click="expandRowToggle()"
                    @keyup.enter="expandRowToggle()"
                    :tabindex="(isHeaderRow) ? -1 : 0"
                />
            </div>
            <div
                class="cell first-name"
                :class="{ 'is-sort-enabled': isSortOptionEnabled('firstName') }"
                @click="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
                @keyup.enter="isSortOptionEnabled('firstName') && handleSortSelect('firstName')"
                :tabindex="(isHeaderRow && isSortOptionEnabled('firstName')) ? 0 : -1"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <span v-if="$matches.phone.only" class="cell-title">{{ $t('common.firstName') }}:</span>
                {{ item.firstName }}
                <span v-if="isSortOptionEnabled('firstName')" class="sort-icon" :class="{
                    'is-selected': isSortOptionSelected('firstName'),
                    'asc': isSortOptionAscending('firstName'),
                    'desc': isSortOptionDescending('firstName'),
                }"></span>
            </div>
            <div
                class="cell last-name"
                :class="{ 'is-sort-enabled': isSortOptionEnabled('lastName') }"
                @click="isSortOptionEnabled('lastName') && handleSortSelect('lastName')"
                @keyup.enter="isSortOptionEnabled('lastName') && handleSortSelect('lastName')"
                :tabindex="(isHeaderRow && isSortOptionEnabled('lastName')) ? 0 : -1"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <span v-if="$matches.phone.only" class="cell-title">{{ $t('common.lastName') }}:</span>
                {{ item.lastName }}
                <span v-if="isSortOptionEnabled('lastName')" class="sort-icon" :class="{
                    'is-selected': isSortOptionSelected('lastName'),
                    'asc': isSortOptionAscending('lastName'),
                    'desc': isSortOptionDescending('lastName'),
                }"></span>
            </div>
            <div
                class="cell permissions"
                :class="{ 'is-sort-enabled': isSortOptionEnabled('permissions') }"
                @click="isSortOptionEnabled('permissions') && handleSortSelect('permissions')"
                @keyup.enter="isSortOptionEnabled('permissions') && handleSortSelect('permissions')"
                :tabindex="(isHeaderRow && isSortOptionEnabled('permissions')) ? 0 : -1"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.permissions') }}:</span>
                {{ item.permissionsShortDisplay(currentCompactType) }}
                <span v-if="isSortOptionEnabled('permissions')" class="sort-icon" :class="{
                    'is-selected': isSortOptionSelected('permissions'),
                    'asc': isSortOptionAscending('permissions'),
                    'desc': isSortOptionDescending('permissions'),
                }"></span>
            </div>
            <div
                class="cell affiliation"
                :class="{ 'is-sort-enabled': isSortOptionEnabled('affiliation') }"
                @click="isSortOptionEnabled('affiliation') && handleSortSelect('affiliation')"
                @keyup.enter="isSortOptionEnabled('affiliation') && handleSortSelect('affiliation')"
                :tabindex="(isHeaderRow && isSortOptionEnabled('affiliation')) ? 0 : -1"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.affiliation') }}:</span>
                {{ item.affiliationDisplay(currentCompactType) }}
                <span v-if="isSortOptionEnabled('affiliation')" class="sort-icon" :class="{
                    'is-selected': isSortOptionSelected('affiliation'),
                    'asc': isSortOptionAscending('affiliation'),
                    'desc': isSortOptionDescending('affiliation'),
                }"></span>
            </div>
            <div
                class="cell states"
                :class="{ 'is-sort-enabled': isSortOptionEnabled('states') }"
                @click="isSortOptionEnabled('states') && handleSortSelect('states')"
                @keyup.enter="isSortOptionEnabled('states') && handleSortSelect('states')"
                :tabindex="(isHeaderRow && isSortOptionEnabled('states')) ? 0 : -1"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.states') }}:</span>
                {{ item.statesDisplay(currentCompactType) }}
                <span v-if="isSortOptionEnabled('states')" class="sort-icon" :class="{
                    'is-selected': isSortOptionSelected('states'),
                    'asc': isSortOptionAscending('states'),
                    'desc': isSortOptionDescending('states'),
                }"></span>
            </div>
            <div
                class="cell account-status"
                :class="{
                    'is-sort-enabled': isSortOptionEnabled('accountStatus'),
                    'is-emphasis': isAccountStatusEmphasis
                }"
                @click="isSortOptionEnabled('accountStatus') && handleSortSelect('accountStatus')"
                @keyup.enter="isSortOptionEnabled('accountStatus') && handleSortSelect('accountStatus')"
                :tabindex="(isHeaderRow && isSortOptionEnabled('accountStatus')) ? 0 : -1"
                :role="(isHeaderRow) ? 'columnheader' : 'cell'"
            >
                <span v-if="$matches.phone.only" class="cell-title">{{ $t('account.accountStatus') }}:</span>
                <span class="account-status">{{ item.accountStatusDisplay() }}</span>
                <span v-if="isSortOptionEnabled('accountStatus')" class="sort-icon" :class="{
                    'is-selected': isSortOptionSelected('accountStatus'),
                    'asc': isSortOptionAscending('accountStatus'),
                    'desc': isSortOptionDescending('accountStatus'),
                }"></span>
            </div>
            <div class="cell row-actions" :role="(isHeaderRow) ? 'columnheader' : 'cell'">
                <div v-if="!isHeaderRow">
                    <div
                        class="row-menu-toggle"
                        role="button"
                        :aria-label="$t('account.userActions')"
                        @click="toggleRowActionMenu"
                        @keyup.enter="toggleRowActionMenu"
                        tabindex="0"
                    >
                        <span class="dot" /><span class="dot" /><span class="dot" />
                    </div>
                    <transition name="fade" mode="out-in">
                        <ul
                            v-if="isRowActionMenuDisplayed"
                            class="row-menu"
                            v-click-outside="closeRowActionMenu"
                        >
                            <li
                                v-if="!isDeactivated"
                                class="row-menu-item"
                                :class="{ 'disabled': isReinviteSent }"
                                role="button"
                                @click="toggleReinviteUserModal"
                                @keyup.enter="toggleReinviteUserModal"
                                tabindex="0"
                            >
                                {{ (isReinviteSent) ? $t('account.reinviteSent') : $t('account.resendInvite') }}
                            </li>
                            <li
                                v-if="!isDeactivated"
                                class="row-menu-item"
                                role="button"
                                @click="toggleEditUserModal"
                                @keyup.enter="toggleEditUserModal"
                                tabindex="0"
                            >
                                {{ $t('account.editPermissions') }}
                            </li>
                            <li
                                class="row-menu-item"
                                :class="{ 'disabled': isDeactivated, 'danger': !isDeactivated }"
                                role="button"
                                @click="toggleDeactivateUserModal"
                                @keyup.enter="toggleDeactivateUserModal"
                                tabindex="0"
                            >
                                {{ (isDeactivated) ? $t('account.deactivated') : $t('account.deactivate') }}
                            </li>
                        </ul>
                    </transition>
                </div>
            </div>
        </div>
        <div
            v-if="!isHeaderRow && $matches.desktop.min"
            class="cell-content expanded-content"
            :class="{ 'active': isRowExpanded }"
            :role="(isRowExpanded) ? 'row' : ''"
        >
            <div v-if="$matches.desktop.min" class="cell expand-collapse"></div>
            <div class="cell first-name"></div>
            <div class="cell last-name"></div>
            <div class="cell permissions" role="cell">
                <div class="permissions-label">Permission details</div>
                <ul class="permissions-full good-wrap">
                    <li
                        v-for="(permission, index) in item.permissionsFullDisplay(currentCompactType)"
                        :key="index"
                        class="permission-full"
                    >
                        {{ permission }}
                    </li>
                </ul>
            </div>
            <div class="cell affiliation"></div>
            <div class="cell states"></div>
            <div class="cell account-status"></div>
            <div class="cell row-actions"></div>
        </div>
        <TransitionGroup>
            <div v-if="isEditUserModalDisplayed">
                <div class="modal-mask"></div>
                <div class="edit-user-modal">
                    <UserRowEdit :user="item" @saved="closeEditUserModal" @cancel="closeEditUserModal" />
                </div>
            </div>
            <Modal
                v-else-if="isReinviteUserModalDisplayed"
                class="reinvite-user-modal"
                :title="$t('account.confirmUserReinviteTitle', { name: accountFullName })"
                :closeOnBackgroundClick="true"
                :showActions="false"
                @keydown.tab="focusTrapReinviteUserModal($event)"
                @keyup.esc="closeReinviteUserModal"
            >
                <template v-slot:content>
                    <div class="modal-content reinvite-modal-content">
                        {{ $t('account.confirmUserReinviteSubtext', { email: accountEmail }) }}
                        <form @submit.prevent="submitReinviteUser">
                            <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="reinvite-modal-cancel-button"
                                    class="cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeReinviteUserModal"
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
            <Modal
                v-else-if="isDeactivateUserModalDisplayed"
                class="deactivate-user-modal"
                :title="accountFullName"
                :closeOnBackgroundClick="true"
                :showActions="false"
                @keydown.tab="focusTrapDeactivateUserModal($event)"
                @keyup.esc="closeDeactivateUserModal"
            >
                <template v-slot:content>
                    <div class="modal-content deactivate-modal-content">
                        {{ $t('account.confirmUserDeactivate', { name: accountFullName }) }}
                        <form @submit.prevent="submitDeactivateUser">
                            <div v-if="modalErrorMessage" class="modal-error">{{ modalErrorMessage }}</div>
                            <div class="action-button-row">
                                <InputButton
                                    id="deactivate-modal-cancel-button"
                                    class="cancel-button"
                                    :label="$t('common.cancel')"
                                    :isTransparent="true"
                                    :onClick="closeDeactivateUserModal"
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

<script lang="ts" src="./UserRow.ts"></script>
<style scoped lang="less" src="./UserRow.less"></style>
