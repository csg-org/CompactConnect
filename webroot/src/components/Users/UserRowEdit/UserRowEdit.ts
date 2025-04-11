//
//  UserRowEdit.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/14/2024.
//

import {
    Component,
    mixins,
    Prop,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import { Permission } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import {
    StaffUser,
    StaffUserSerializer,
    CompactPermission,
    StatePermission
} from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

interface PermissionOption {
    value: string | number;
    name: string | ComputedRef<string>;
    isDisabled?: boolean;
}

interface PermissionObject {
    isReadPrivate?: boolean;
    isReadSsn?: boolean;
    isWrite?: boolean;
    isAdmin?: boolean;
}

@Component({
    name: 'UserRowEdit',
    components: {
        Card,
        InputSelect,
        InputButton,
        InputSubmit,
        LoadingSpinner,
    },
    emits: [ 'cancel', 'saved' ],
})
class UserRowEdit extends mixins(MixinForm) {
    @Prop({ required: true }) user!: StaffUser;

    //
    // Data
    //
    permissionStateInputs: Array<FormInput> = [];

    //
    // Lifecycle
    //
    created() {
        this.shouldValuesIncludeDisabled = true;
        this.initFormInputs();
    }

    mounted() {
        document.getElementById('cancel-edit-user')?.focus();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get currentUser(): StaffUser {
        return this.userStore.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get currentUserCompactPermission(): CompactPermission | null {
        const currentPermissions = this.currentUser?.permissions;
        const compactPermission = currentPermissions?.find((currentPermission: CompactPermission) =>
            currentPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get rowUserCompactPermission(): CompactPermission | null {
        const userPermissions = this.user.permissions;
        const compactPermission = userPermissions?.find((userPermission: CompactPermission) =>
            userPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get isCurrentUserCompactAdmin(): boolean {
        return this.getCompactPermission(this.currentUserCompactPermission) === Permission.ADMIN;
    }

    get isCurrentUserStateAdminAny(): boolean {
        const { currentUserCompactPermission } = this;
        const statePermissions = currentUserCompactPermission?.states || [];
        const isStateAdminAny = statePermissions.some((statePermission) => statePermission.isAdmin);

        return isStateAdminAny;
    }

    get isAnyTypeOfAdmin(): boolean {
        return this.isCurrentUserCompactAdmin || this.isCurrentUserStateAdminAny;
    }

    get userCompact(): Compact | null {
        return this.rowUserCompactPermission?.compact || null;
    }

    get userCompactOptions(): Array<PermissionOption> {
        const { userCompact } = this;
        const compactOptions: Array<PermissionOption> = [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
        ];

        if (userCompact && userCompact.type) {
            compactOptions.push({
                value: userCompact.type,
                name: userCompact.abbrev(),
            });
        }

        return compactOptions;
    }

    get userPermissionOptionsCompact(): Array<PermissionOption> {
        return [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
            { value: Permission.READ_PRIVATE, name: this.$t('account.accessLevel.readPrivate') },
            { value: Permission.READ_SSN, name: this.$t('account.accessLevel.readSsn') },
            { value: Permission.ADMIN, name: this.$t('account.accessLevel.admin') },
        ];
    }

    get currentUserStatePermissions(): Array<StatePermission> {
        const statePermissions = this.currentUserCompactPermission?.states || [];

        return statePermissions;
    }

    get userStatePermissions(): Array<StatePermission> {
        return this.rowUserCompactPermission?.states || [];
    }

    get userPermissionOptionsState(): Array<PermissionOption> {
        return [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
            { value: Permission.READ_PRIVATE, name: this.$t('account.accessLevel.readPrivate') },
            { value: Permission.READ_SSN, name: this.$t('account.accessLevel.readSsn') },
            { value: Permission.WRITE, name: this.$t('account.accessLevel.write') },
            { value: Permission.ADMIN, name: this.$t('account.accessLevel.admin') },
        ];
    }

    get userOptionsState(): Array<PermissionOption> {
        const { currentCompact } = this;
        let options = currentCompact?.memberStates?.map((memberState: State) => ({
            value: (memberState.abbrev as unknown as string)?.toLowerCase() || '',
            name: memberState.name(),
        })) || [];

        if (!this.isCurrentUserCompactAdmin) {
            options = options.filter((option) =>
                this.currentUserStatePermissions.some((statePermission) => {
                    const stateAbbrev = statePermission.state?.abbrev || '';
                    const isStateAdmin = statePermission.isAdmin;

                    return stateAbbrev === option.value && isStateAdmin;
                }));
        }

        options.unshift({ value: '', name: this.$t('common.select') });

        return options;
    }

    get shouldShowAddStateButton(): boolean {
        let shouldShow = false;

        if (this.isCurrentUserCompactAdmin || this.isCurrentUserStateAdminAny) {
            const availableStatesNum = this.userOptionsState.length - 1;
            const assignedStatesNum = Object.keys(this.formData)
                .filter((formKey) => formKey.startsWith('state-option')).length;

            // If there are available states that haven't been assigned, the button should be shown
            if (availableStatesNum > assignedStatesNum) {
                shouldShow = true;
            }
        }

        return shouldShow;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            compact: new FormInput({
                id: 'compact',
                name: 'compact',
                label: computed(() => this.$t('account.affiliation')),
                placeholder: computed(() => this.$t('account.affiliation')),
                valueOptions: this.userCompactOptions,
                value: this.userCompact?.type,
                isDisabled: true,
            }),
            compactPermission: new FormInput({
                id: 'compact-permission',
                name: 'compact-permission',
                label: computed(() => this.$t('account.permission')),
                placeholder: computed(() => this.$t('account.permission')),
                valueOptions: this.userPermissionOptionsCompact,
                value: this.getCompactPermission(this.rowUserCompactPermission),
                isDisabled: !this.isCurrentUserCompactAdmin,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
                shouldHideMargin: true,
            }),
        });

        this.addStateFormInputs();
        this.watchFormInputs(); // Important if you want automated form validation
    }

    focusTrap(event: KeyboardEvent): void {
        const { formData } = this;
        const firstEnabledFormInput: string = Object.keys(formData)
            .filter((key) => key !== 'submit')
            .find((key) => !formData[key].isDisabled) || '';
        const firstEnabledInputId = formData[firstEnabledFormInput]?.id || 'cancel-edit-user';
        const firstTabIndex = document.getElementById(firstEnabledInputId);
        const lastTabIndex = document.getElementById('submit');

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

    addStateFormInputs(): void {
        this.userStatePermissions.forEach((statePermission) => {
            this.addStateFormInput(statePermission);
        });
    }

    addStateFormInput(statePermission?: StatePermission): void {
        const { state } = statePermission || {};
        const stateAbbrev = state?.abbrev || '';
        const stateOptions = this.filterStateOptions();
        const isStateInOptions = stateOptions.some((stateOption) => stateOption.value === stateAbbrev);
        const index = this.permissionStateInputs.length;

        if (isStateInOptions) {
            const stateInput = new FormInput({
                id: `state-option-${index}`,
                name: `state-option-${index}`,
                label: computed(() => this.$t('account.state')),
                placeholder: computed(() => this.$t('account.state')),
                validation: (!statePermission) ? Joi.string().required().messages(this.joiMessages.string) : null,
                valueOptions: stateOptions,
                value: state?.abbrev || '',
                isDisabled: Boolean(statePermission),
            });
            const permissionInput = new FormInput({
                id: `state-permission-${index}`,
                name: `state-permission-${index}`,
                label: computed(() => this.$t('account.permission')),
                placeholder: computed(() => this.$t('account.permission')),
                validation: (!statePermission) ? Joi.string().required().messages(this.joiMessages.string) : null,
                valueOptions: this.userPermissionOptionsState,
                value: (statePermission) ? this.getStatePermission(statePermission) : Permission.NONE,
            });

            this.formData[`state-option-${index}`] = stateInput;
            this.formData[`state-permission-${index}`] = permissionInput;

            this.permissionStateInputs.push(permissionInput);
        }
    }

    filterStateOptions(): Array<PermissionOption> {
        return this.userOptionsState.map((optionState) => {
            const option = { ...optionState };

            this.permissionStateInputs.forEach((permissionInput) => {
                const stateInputId = permissionInput.id.split('-').pop();
                const stateInput = this.formData[`state-option-${stateInputId}`];

                // If there are available states that haven't been assigned, the button should be shown
                if (stateInput.value && stateInput.value === optionState.value) {
                    option.isDisabled = true;
                }
            });

            return option;
        });
    }

    lockInStateOptions(): void {
        const { formData } = this;

        Object.keys(this.formData).forEach((key) => {
            if (key.startsWith('state-option')) {
                formData[key].isDisabled = true;
            }
        });
    }

    createNewStatePermission(): void {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.lockInStateOptions();
            this.addStateFormInput();
        }
    }

    getCompactPermission(compactPermission: CompactPermission | null): Permission {
        let permission = Permission.NONE;

        if (compactPermission) {
            if (compactPermission.isAdmin) {
                permission = Permission.ADMIN;
            } else if (compactPermission.isReadSsn) {
                permission = Permission.READ_SSN;
            } else if (compactPermission.isReadPrivate) {
                permission = Permission.READ_PRIVATE;
            }
        }

        return permission;
    }

    setCompactPermission(permission: Permission): PermissionObject {
        const response: PermissionObject = {};

        if (this.isCurrentUserCompactAdmin) {
            switch (permission) {
            case Permission.NONE:
                response.isReadPrivate = false;
                response.isReadSsn = false;
                response.isAdmin = false;
                break;
            case Permission.READ_PRIVATE:
                response.isReadPrivate = true;
                response.isReadSsn = false;
                response.isAdmin = false;
                break;
            case Permission.READ_SSN:
                response.isReadPrivate = true;
                response.isReadSsn = true;
                response.isAdmin = false;
                break;
            case Permission.ADMIN:
                response.isReadPrivate = true;
                response.isReadSsn = true;
                response.isAdmin = true;
                break;
            default:
                break;
            }
        }

        return response;
    }

    getStatePermission(statePermission: StatePermission | null): Permission {
        let permission = Permission.NONE;

        if (statePermission) {
            if (statePermission.isAdmin) {
                permission = Permission.ADMIN;
            } else if (statePermission.isWrite) {
                permission = Permission.WRITE;
            } else if (statePermission.isReadSsn) {
                permission = Permission.READ_SSN;
            } else if (statePermission.isReadPrivate) {
                permission = Permission.READ_PRIVATE;
            }
        }

        return permission;
    }

    setStatePermission(permission: Permission): PermissionObject {
        const response: PermissionObject = {};

        switch (permission) {
        case Permission.NONE:
            response.isReadPrivate = false;
            response.isReadSsn = false;
            response.isWrite = false;
            response.isAdmin = false;
            break;
        case Permission.READ_PRIVATE:
            response.isReadPrivate = true;
            response.isReadSsn = false;
            response.isWrite = false;
            response.isAdmin = false;
            break;
        case Permission.READ_SSN:
            response.isReadPrivate = true;
            response.isReadSsn = true;
            response.isWrite = false;
            response.isAdmin = false;
            break;
        case Permission.WRITE:
            response.isReadPrivate = true;
            response.isReadSsn = true;
            response.isWrite = true;
            response.isAdmin = false;
            break;
        case Permission.ADMIN:
            response.isReadPrivate = true;
            response.isReadSsn = true;
            response.isWrite = true;
            response.isAdmin = true;
            break;
        default:
            break;
        }

        return response;
    }

    handleCancel(): void {
        this.$emit('cancel');
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const formData = this.prepFormData();
            const serverData = StaffUserSerializer.toServer({ permissions: [formData] });

            await this.$store.dispatch(`users/updateUserRequest`, {
                compact: this.userCompact?.type,
                userId: this.user.id,
                data: serverData,
            }).catch((err) => {
                this.setError(err.message);
            });

            if (this.user.id === this.currentUser.id) {
                await this.$store.dispatch(`user/getStaffAccountRequest`);
            }

            if (!this.isFormError) {
                this.isFormSuccessful = true;
            }

            this.$emit('saved');
            this.endFormLoading();
        }
    }

    prepFormData(): object {
        const { formValues } = this;
        const compactData = {
            compact: formValues.compact,
            ...this.setCompactPermission(formValues.compactPermission),
            states: [] as Array<object>,
        };
        const stateKeys = Object.keys(formValues).filter((key) => key.startsWith('state-option'));

        // Server endpoints may not be idempotent so the frontend needs to handle statefulness;
        // e.g. if the user's server permisson is already false, we may get a server error if we try to send false again.
        const existingCompactPermission = this.getCompactPermission(this.rowUserCompactPermission);

        if (existingCompactPermission !== Permission.READ_PRIVATE && !compactData.isReadPrivate) {
            delete compactData.isReadPrivate;
        }
        if (existingCompactPermission !== Permission.ADMIN && !compactData.isAdmin) {
            delete compactData.isAdmin;
        }
        // End: Handle compact statefulness

        stateKeys.forEach((stateKey) => {
            const keyNum = stateKey.split('-').pop();
            const stateAbbrev = formValues[`state-option-${keyNum}`];
            const statePermission = formValues[`state-permission-${keyNum}`];
            const stateData = {
                abbrev: stateAbbrev,
                ...this.setStatePermission(statePermission),
            };

            // Server endpoints may not be idempotent so the frontend needs to handle statefulness;
            // e.g. if the user's server permisson is already false, we may get a server error if we try to send false again.
            const existingStatePermission = this.getStatePermission(this.userStatePermissions.find((permission) =>
                permission.state?.abbrev === stateAbbrev) || null);

            if (existingStatePermission !== Permission.READ_PRIVATE && !stateData.isReadPrivate) {
                delete stateData.isReadPrivate;
            }
            if (existingStatePermission !== Permission.WRITE && !stateData.isWrite) {
                delete stateData.isWrite;
            }
            if (existingStatePermission !== Permission.ADMIN && !stateData.isAdmin) {
                delete stateData.isAdmin;
            }
            // End: Handle state statefulness

            compactData.states.push(stateData);
        });

        return compactData;
    }
}

export default toNative(UserRowEdit);

// export default UserRowEdit;
