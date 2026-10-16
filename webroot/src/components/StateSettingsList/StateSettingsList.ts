//
//  StateSettingsList.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2025.
//

import {
    Component,
    mixins,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import { AuthTypes } from '@utils/auth';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputEmailList from '@components/Forms/InputEmailList/InputEmailList.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import Modal from '@components/Modal/Modal.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';
import { State } from '@/models/State/State.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

interface StateConfigRowPermission {
    state?: State;
    isLiveForCompact?: boolean;
    isCompactAdmin?: boolean;
    isStateAdmin?: boolean;
}

@Component({
    name: 'StateSettingsList',
    components: {
        LoadingSpinner,
        Modal,
        InputButton,
        InputSubmit,
        InputEmailList,
        MockPopulate,
    },
})
class StateSettingsList extends mixins(MixinForm) {
    //
    // Data
    //
    isLoading = false;
    loadingErrorMessage = '';
    initialCompactConfig: any = {};
    compactConfigStates: Array<{
        abbrev: string,
        isLive: boolean,
        jurisdictionAdverseActionsNotificationEmails: Array<string>
    }> = [];
    compactAllStates: Array<{abbrev: string}> = []; // eslint-disable-line lines-between-class-members
    isStateLiveModalDisplayed = false;
    selectedState: State | null = null;
    modalErrorMessage = '';

    //
    // Lifecycle
    //
    created(): void {
        this.init();
    }

    //
    // Computed
    //
    get globalStore() {
        return this.$store.state;
    }

    get authType(): string {
        return this.globalStore.authType;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get compactType(): CompactType | null {
        return this.currentCompact?.type || null;
    }

    get compactStates(): Array<State> {
        return this.currentCompact?.memberStates || [];
    }

    get isCompactSeparatingPrivilegeEnabled(): boolean {
        return this.$isAppModeCosmetology;
    }

    get user() {
        return this.userStore.model;
    }

    get isLoggedInAsStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get staffPermission(): CompactPermission | null {
        const currentPermissions = this.user?.permissions;
        const compactPermission = currentPermissions?.find((currentPermission) =>
            currentPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get isCompactAdmin(): boolean {
        return this.isLoggedInAsStaff && Boolean(this.staffPermission?.isAdmin);
    }

    get statePermissionsAdmin(): Array<StatePermission> {
        return this.staffPermission?.states?.filter((statePermission) => statePermission.isAdmin) || [];
    }

    get isStateAdminAny(): boolean {
        return this.isLoggedInAsStaff
            && (this.statePermissionsAdmin.length > 0 || this.isCompactSeparatingPrivilegeEnabled);
    }

    get isStateAdminMultiple(): boolean {
        return this.isLoggedInAsStaff
            && (this.statePermissionsAdmin.length > 1 || this.isCompactSeparatingPrivilegeEnabled);
    }

    get isStateAdminExactlyOne(): boolean {
        return this.isLoggedInAsStaff
            && this.statePermissionsAdmin.length === 1 && !this.isCompactSeparatingPrivilegeEnabled;
    }

    get stateConfigRowPermissions(): Array<StateConfigRowPermission> {
        const userCompactAdminStates = this.compactConfigStates;
        const userPermissionAdminStates = this.statePermissionsAdmin;
        let rowPermissions: Array<StateConfigRowPermission> = [];

        // State row permissions are based on 2 different permission lists that we merge here

        //
        // Compact-level admin states
        //
        userCompactAdminStates.forEach((compactAdminState) => {
            rowPermissions.push({
                state: new State({ abbrev: compactAdminState.abbrev }),
                isLiveForCompact: compactAdminState.isLive,
                isCompactAdmin: true,
                isStateAdmin: false,
            });
        });

        // Some compacts allow compact admins to see all states so they can separately enable states as privilege-live.
        if (this.isCompactSeparatingPrivilegeEnabled) {
            this.compactStates.forEach((compactState) => {
                const existing = userCompactAdminStates.find((userCompactAdminState) =>
                    compactState.abbrev === userCompactAdminState.abbrev);

                if (!existing) {
                    rowPermissions.push({
                        state: new State({ abbrev: compactState.abbrev }),
                        isLiveForCompact: false,
                        isCompactAdmin: true,
                        isStateAdmin: false,
                    });
                }
            });
        }

        //
        // State-level admin states
        //
        userPermissionAdminStates.forEach((permissionAdminState) => {
            const existing = rowPermissions.find((existingState) =>
                existingState.state?.abbrev === permissionAdminState.state.abbrev);

            if (existing) {
                existing.isStateAdmin = true;
            } else {
                rowPermissions.push({
                    state: new State({ abbrev: permissionAdminState.state.abbrev }),
                    isLiveForCompact: false,
                    isCompactAdmin: this.isCompactSeparatingPrivilegeEnabled,
                    isStateAdmin: true,
                });
            }
        });

        // Sort the results for clarity
        rowPermissions = rowPermissions.sort((a, b) => {
            const stateNameA = a.state?.name() || '';
            const stateNameB = b.state?.name() || '';
            let sort = 0;

            if (stateNameA > stateNameB) {
                sort = 1;
            } else if (stateNameA < stateNameB) {
                sort = -1;
            }

            return sort;
        });

        return rowPermissions;
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    init(): void {
        this.initCompactConfig();
    }

    async initCompactConfig(): Promise<void> {
        if (this.compactType && this.isCompactAdmin) {
            this.isLoading = true;

            const compact = this.compactType || '';
            const compactConfig: any = await dataApi.getCompactConfig(compact).catch((err) => {
                this.loadingErrorMessage = err?.message || this.$t('serverErrors.networkError');
            });

            this.initialCompactConfig = compactConfig;

            if (Array.isArray(compactConfig?.configuredStates)) {
                this.compactConfigStates = [];
                compactConfig.configuredStates.forEach((serverState) => {
                    this.compactConfigStates.push({
                        abbrev: serverState.postalAbbreviation || '',
                        isLive: serverState.isLive || false,
                        jurisdictionAdverseActionsNotificationEmails:
                            serverState.jurisdictionAdverseActionsNotificationEmails || [],
                    });
                });
            }

            this.isLoading = false;
        }
    }

    initFormInputs(): void {
        if (this.isStateLiveModalDisplayed) {
            this.initFormInputsStateLive();
        }
    }

    initFormInputsStateLive(): void {
        const minAdverseActionEmails = (this.isCompactSeparatingPrivilegeEnabled) ? 1 : 0;

        this.formData = reactive({
            adverseActionNotificationEmails: new FormInput({
                id: 'adverse-action-notification-emails-state',
                name: 'adverse-action-notification-emails-state',
                label: computed(() => this.$t('compact.adverseActionsNotificationEmails')),
                labelSubtext: computed(() => this.$t('compact.adverseActionsNotificationEmailsSubtext')),
                placeholder: computed(() => this.$t('compact.addEmails')),
                validation: Joi.array().min(minAdverseActionEmails).messages(this.joiMessages.array),
                value: this.getStateConfig().jurisdictionAdverseActionsNotificationEmails || [],
            }),
            stateLiveModalContinue: new FormInput({
                isSubmitInput: true,
                id: 'submit-modal-continue',
            }),
        });
        this.watchFormInputs();
    }

    resetForm(): void {
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;
        this.selectedState = null;
        this.modalErrorMessage = '';
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }

    routeToStateConfig(abbrev: string, isRouteReplace = false): void {
        if (this.currentCompact?.type) {
            const routeConfig = {
                name: 'StateSettings',
                params: {
                    compact: this.currentCompact?.type,
                    state: abbrev,
                },
            };

            if (isRouteReplace) {
                this.$router.replace(routeConfig);
            } else {
                this.$router.push(routeConfig);
            }
        }
    }

    async toggleStateLiveModal(state: State): Promise<void> {
        this.resetForm();
        this.selectedState = state;
        this.isStateLiveModalDisplayed = !this.isStateLiveModalDisplayed;

        if (this.isStateLiveModalDisplayed) {
            this.initFormInputs();
            await nextTick();
            document.getElementById('confirm-modal-cancel-button')?.focus();
        }
    }

    closeStateLiveModal(event?: Event): void {
        event?.preventDefault();
        this.isStateLiveModalDisplayed = false;
    }

    focusTrapStateLiveModal(event: KeyboardEvent): void {
        let firstTabIndex = document.getElementById('confirm-modal-submit-button');
        const lastTabIndex = document.getElementById('confirm-modal-cancel-button');

        if (this.isCompactSeparatingPrivilegeEnabled && this.isStateConfigAdverseActionEmailMissing()) {
            firstTabIndex = document.getElementById('adverse-action-notification-emails-state');
        }

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    getStateConfig() {
        const stateAbbrev = this.selectedState?.abbrev;
        const stateConfig = this.compactConfigStates.find((compactConfigState) =>
            compactConfigState.abbrev === stateAbbrev) || {
            abbrev: '',
            isLive: false,
            jurisdictionAdverseActionsNotificationEmails: [],
        };

        return stateConfig;
    }

    getStateConfigIsLive(): boolean {
        return this.getStateConfig().isLive;
    }

    getStateConfigAdverseActionEmails(): Array<string> {
        return this.getStateConfig().jurisdictionAdverseActionsNotificationEmails || [];
    }

    isStateConfigAdverseActionEmailMissing(): boolean {
        return this.getStateConfigAdverseActionEmails().length === 0;
    }

    getStateRowPermission() {
        const stateAbbrev = this.selectedState?.abbrev;
        const stateRowPermission = this.stateConfigRowPermissions.find((stateConfigRowPermission) =>
            stateConfigRowPermission?.state?.abbrev === stateAbbrev);

        return stateRowPermission;
    }

    getSelectedStateName(): string {
        return this.selectedState?.name() || '';
    }

    getStateLiveModalSubmitLabel(): string {
        const stateRow = this.getStateRowPermission();
        let modalSubmitLabel = this.$t('compact.confirmSaveStateYes');

        if (this.isCompactSeparatingPrivilegeEnabled && !stateRow?.isLiveForCompact) {
            modalSubmitLabel = this.$t('compact.confirmSaveStateWithPrivilegesYes');
        }

        return modalSubmitLabel;
    }

    async submitStateLive(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid && this.compactType) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { compactType, selectedState } = this;
            const selectedStateAbbrev = selectedState?.abbrev || '';
            const payload = {
                ...this.initialCompactConfig,
                configuredStates: (this.initialCompactConfig?.configuredStates || []) // Deep clone the configuredStates
                    .map((configuredState) => ({ ...configuredState })),
            };
            let isStateConfigured = false;

            // For enabling a state, the server requires the entire compact config, minus a couple props
            payload.compactName = undefined;
            payload.compactAbbr = undefined;

            // Update the selected state to live / enabled
            payload.configuredStates?.forEach((configuredState) => {
                if (configuredState.postalAbbreviation === selectedStateAbbrev) {
                    configuredState.isLive = true;

                    // If the compact is able to separately enable states as privilege-live, some additional props need updating.
                    if (this.isCompactSeparatingPrivilegeEnabled && this.isStateConfigAdverseActionEmailMissing()) {
                        configuredState.jurisdictionAdverseActionsNotificationEmails = // eslint-disable-line operator-linebreak
                            this.formData.adverseActionNotificationEmails.value;
                    }

                    isStateConfigured = true;
                }
            });

            // If the compact is able to separately enable states as privilege-live AND the state isn't already part of the server-side config
            if (!isStateConfigured) {
                payload.configuredStates.push({
                    postalAbbreviation: selectedStateAbbrev,
                    isLive: true,
                    jurisdictionAdverseActionsNotificationEmails: this.formData.adverseActionNotificationEmails.value,
                });
                isStateConfigured = true;
            }

            // Call the server API to update
            await dataApi.updateCompactConfig(compactType, payload).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            // Handle success
            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.initCompactConfig();
                await nextTick();
                this.closeStateLiveModal();
            }

            this.endFormLoading();
        }
    }

    async mockPopulate(): Promise<void> {
        if (this.isCompactSeparatingPrivilegeEnabled) {
            this.populateFormInput(this.formData.adverseActionNotificationEmails, ['adverse@example.com']);
        }
    }

    //
    // Watch
    //
    @Watch('currentCompact') currentCompactUpdate() {
        this.initCompactConfig();
    }

    @Watch('user') userUpdate() {
        this.initCompactConfig();
    }
}

export default toNative(StateSettingsList);

// export default StateSettingsList;
