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
import { reactive, nextTick } from 'vue';
import { AuthTypes } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { CompactPermission, StatePermission } from '@models/StaffUser/StaffUser.model';
import { State } from '@/models/State/State.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';

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
    },
})
class StateSettingsList extends mixins(MixinForm) {
    //
    // Data
    //
    isLoading = false;
    loadingErrorMessage = '';
    initialCompactConfig: any = {};
    compactConfigStates: Array<{abbrev: string, isLive: boolean}> = [];
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
        return this.isLoggedInAsStaff && this.statePermissionsAdmin.length > 0;
    }

    get isStateAdminMultiple(): boolean {
        return this.isLoggedInAsStaff && this.statePermissionsAdmin.length > 1;
    }

    get isStateAdminExactlyOne(): boolean {
        return this.isLoggedInAsStaff && this.statePermissionsAdmin.length === 1;
    }

    get stateConfigRowPermissions(): Array<StateConfigRowPermission> {
        const userCompactAdminStates = this.compactConfigStates;
        const userPermissionAdminStates = this.statePermissionsAdmin;
        let rowPermissions: Array<StateConfigRowPermission> = [];

        // State row permissions are based on 2 different permission lists that we merge here

        // Compact-level admin states
        userCompactAdminStates.forEach((compactAdminState) => {
            rowPermissions.push({
                state: new State({ abbrev: compactAdminState.abbrev }),
                isLiveForCompact: compactAdminState.isLive,
                isCompactAdmin: true,
                isStateAdmin: false,
            });
        });

        // State-level admin states
        userPermissionAdminStates.forEach((permissionAdminState) => {
            const existing = rowPermissions.find((existingState) =>
                existingState.state?.abbrev === permissionAdminState.state.abbrev);

            if (existing) {
                existing.isStateAdmin = true;
            } else {
                rowPermissions.push({
                    state: new State({ abbrev: permissionAdminState.state.abbrev }),
                    isLiveForCompact: false,
                    isCompactAdmin: false,
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

            if (Array.isArray(compactConfig.configuredStates)) {
                this.compactConfigStates = [];
                compactConfig.configuredStates.forEach((serverState) => {
                    this.compactConfigStates.push({
                        abbrev: serverState.postalAbbreviation || '',
                        isLive: serverState.isLive || false,
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
        this.formData = reactive({
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
        const firstTabIndex = document.getElementById('confirm-modal-submit-button');
        const lastTabIndex = document.getElementById('confirm-modal-cancel-button');

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

    async submitStateLive(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid && this.compactType) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { compactType, selectedState } = this;
            const selectedStateAbbrev = selectedState?.abbrev || '';
            const payload = { ...this.initialCompactConfig };

            // For enabling a state, the server requires the entire compact config, minus a couple props
            delete payload.compactName;
            delete payload.compactAbbr;

            // Update the selected state to live / enabled
            payload.configuredStates?.forEach((configuredState) => {
                if (configuredState.postalAbbreviation === selectedStateAbbrev) {
                    configuredState.isLive = true;
                }
            });

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
