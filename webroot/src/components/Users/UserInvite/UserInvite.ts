//
//  UserInvite.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/11/2024.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
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

enum Permission {
    NONE = 'none',
    READ = 'read',
    WRITE = 'write',
    ADMIN = 'admin',
}

interface PermissionObject {
    isRead?: boolean;
    isWrite?: boolean;
    isAdmin?: boolean;
}

@Component({
    name: 'UserInvite',
    components: {
        Card,
        MockPopulate,
        InputText,
        InputSelect,
        InputButton,
        InputSubmit,
        LoadingSpinner,
    },
    emits: [ 'cancel', 'saved' ],
})
class UserInvite extends mixins(MixinForm) {
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

    get userCompactOptions(): Array<PermissionOption> {
        const { currentCompact } = this;
        const compactOptions: Array<PermissionOption> = [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
        ];

        if (currentCompact && currentCompact.type) {
            compactOptions.push({
                value: currentCompact.type,
                name: currentCompact.abbrev(),
            });
        }

        return compactOptions;
    }

    get userPermissionOptionsCompact(): Array<PermissionOption> {
        return [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
            { value: Permission.READ, name: this.$t('account.accessLevel.read') },
            { value: Permission.ADMIN, name: this.$t('account.accessLevel.admin') },
        ];
    }

    get currentUserStatePermissions(): Array<StatePermission> {
        const statePermissions = this.currentUserCompactPermission?.states || [];

        return statePermissions;
    }

    get userPermissionOptionsState(): Array<PermissionOption> {
        return [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
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

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
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
                value: this.currentCompact?.type,
                isDisabled: true,
            }),
            compactPermission: new FormInput({
                id: 'compact-permission',
                name: 'compact-permission',
                label: computed(() => this.$t('account.permission')),
                placeholder: computed(() => this.$t('account.permission')),
                valueOptions: this.userPermissionOptionsCompact,
                value: Permission.NONE,
                isDisabled: !this.isCurrentUserCompactAdmin,
            }),
            email: new FormInput({
                id: 'email',
                name: 'email',
                label: computed(() => this.$t('common.emailAddress')),
                placeholder: computed(() => this.$t('common.emailAddress')),
                validation: Joi.string().required().email({ tlds: false }).messages(this.joiMessages.string),
            }),
            firstName: new FormInput({
                id: 'first-name',
                name: 'first-name',
                label: computed(() => this.$t('common.firstName')),
                placeholder: computed(() => this.$t('common.firstName')),
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            lastName: new FormInput({
                id: 'last-name',
                name: 'last-name',
                label: computed(() => this.$t('common.lastName')),
                placeholder: computed(() => this.$t('common.lastName')),
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
                shouldHideMargin: true,
            }),
        });

        this.watchFormInputs(); // Important if you want automated form validation
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

                // If state has already been selected then show it in the options list as disabled
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
            } else if (compactPermission.isRead) {
                permission = Permission.READ;
            }
        }

        return permission;
    }

    setCompactPermission(permission: Permission): PermissionObject {
        const response: PermissionObject = {};

        switch (permission) {
        case Permission.NONE:
            response.isRead = false;
            response.isAdmin = false;
            break;
        case Permission.READ:
            response.isRead = true;
            response.isAdmin = false;
            break;
        case Permission.ADMIN:
            response.isRead = true;
            response.isAdmin = true;
            break;
        default:
            break;
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
            }
        }

        return permission;
    }

    setStatePermission(permission: Permission): PermissionObject {
        const response: PermissionObject = {};

        switch (permission) {
        case Permission.NONE:
            response.isWrite = false;
            response.isAdmin = false;
            break;
        case Permission.WRITE:
            response.isWrite = true;
            response.isAdmin = false;
            break;
        case Permission.ADMIN:
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
            const serverData = StaffUserSerializer.toServer({
                permissions: [formData.compactData],
                attributes: formData.userData,
            });

            await this.$store.dispatch(`users/createUserRequest`, {
                compact: this.currentCompact?.type,
                data: serverData,
            }).catch((err) => {
                this.setError(err.message);
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
            }

            this.$emit('saved');
            this.endFormLoading();
        }
    }

    prepFormData(): any {
        const { formValues } = this;
        const userData = {
            email: formValues.email,
            firstName: formValues.firstName,
            lastName: formValues.lastName,
        };
        const compactData = {
            compact: formValues.compact,
            ...this.setCompactPermission(formValues.compactPermission),
            states: [] as Array<object>,
        };
        const stateKeys = Object.keys(formValues).filter((key) => key.startsWith('state-option'));

        stateKeys.forEach((stateKey) => {
            const keyNum = stateKey.split('-').pop();
            const stateAbbrev = formValues[`state-option-${keyNum}`];
            const statePermission = formValues[`state-permission-${keyNum}`];

            compactData.states.push({
                abbrev: stateAbbrev,
                ...this.setStatePermission(statePermission),
            });
        });

        return { userData, compactData };
    }

    mockPopulate(): void {
        this.formData.email.value = `test@example.com`;
        this.formData.firstName.value = `Test`;
        this.formData.lastName.value = `User`;
    }
}

export default toNative(UserInvite);

// export default UserInvite;
