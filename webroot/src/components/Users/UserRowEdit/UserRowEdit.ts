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
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@models/State/State.model';
import { User, CompactPermission, StatePermission } from '@models/User/User.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';

interface PermissionOption {
    value: string | number;
    name: string | ComputedRef<string>;
}

enum Permission {
    NONE = 'none',
    READ = 'read',
    WRITE = 'write',
    ADMIN = 'admin',
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
    @Prop({ required: true }) user!: User;

    //
    // Data
    //
    permissionStateInputs: Array<FormInput> = [];

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get userCompactPermission(): CompactPermission | null {
        const userPermissions = this.user.permissions;
        const compactPermission = userPermissions?.find((userPermission: CompactPermission) =>
            userPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get userCompact(): Compact | null {
        return this.userCompactPermission?.compact || null;
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
            { value: Permission.READ, name: this.$t('account.accessLevel.read') },
            { value: Permission.ADMIN, name: this.$t('account.accessLevel.admin') },
        ];
    }

    get userStatePermissions(): Array<StatePermission> {
        return this.userCompactPermission?.states || [];
    }

    get userPermissionOptionsState(): Array<PermissionOption> {
        return [
            { value: Permission.NONE, name: this.$t('account.accessLevel.none') },
            { value: Permission.WRITE, name: this.$t('account.accessLevel.write') },
            { value: Permission.ADMIN, name: this.$t('account.accessLevel.admin') },
        ];
    }

    get userOptionsState(): Array<PermissionOption> {
        const { userCompact } = this;
        const options = userCompact?.memberStates?.map((memberState: State) => ({
            value: (memberState.abbrev as unknown as string)?.toLowerCase() || '',
            name: memberState.name(),
        })) || [];

        options.unshift({ value: '', name: this.$t('common.select') });

        return options;
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
                value: this.getCompactPermission(this.userCompactPermission),
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

    addStateFormInputs(): void {
        this.userStatePermissions.forEach((statePermission) => {
            this.addStateFormInput(statePermission);
        });
    }

    addStateFormInput(statePermission?: StatePermission): void {
        const { state } = statePermission || {};
        const index = this.permissionStateInputs.length;
        const stateInput = new FormInput({
            id: `state-option-${index}`,
            name: `state-option-${index}`,
            label: computed(() => this.$t('account.state')),
            placeholder: computed(() => this.$t('account.state')),
            validation: (!statePermission) ? Joi.string().required().messages(this.joiMessages.string) : null,
            valueOptions: this.userOptionsState,
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

    createNewStatePermission(): void {
        this.addStateFormInput();
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

    handleCancel(): void {
        this.$emit('cancel');
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const formData = this.prepFormData();

            console.log(formData);

            await new Promise((resolve) => setTimeout(() => resolve(true), 2000));

            // if (!this.isFormError) {
            //     this.isFormSuccessful = true;
            // }

            this.$emit('saved');

            this.endFormLoading();
        }
    }

    prepFormData(): object {
        const { formValues } = this;
        const compactData = {
            [formValues.compact]: formValues.compactPermission,
        };
        const stateData = {};
        const stateKeys = Object.keys(formValues).filter((key) => key.startsWith('state-option'));

        stateKeys.forEach((stateKey) => {
            const keyNum = stateKey.split('-').pop();
            const stateAbbrev = formValues[`state-option-${keyNum}`];
            const statePermission = formValues[`state-permission-${keyNum}`];

            stateData[stateAbbrev] = statePermission;
        });

        const formData = {
            ...compactData,
            ...stateData,
        };

        return formData;
    }
}

export default toNative(UserRowEdit);

// export default UserRowEdit;
