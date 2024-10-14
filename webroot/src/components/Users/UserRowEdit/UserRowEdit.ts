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
import { reactive, /* , computed, */ ComputedRef } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import { Compact } from '@models/Compact/Compact.model';
import { User, CompactPermission } from '@models/User/User.model';
import { FormInput } from '@models/FormInput/FormInput.model';

interface PermissionOption {
    value: string | number;
    name: string | ComputedRef<string>;
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
            { value: 'none', name: this.$t('account.accessLevel.none') },
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
            { value: 'none', name: this.$t('account.accessLevel.none') },
            { value: 'read', name: this.$t('account.accessLevel.read') },
            { value: 'admin', name: this.$t('account.accessLevel.admin') },
        ];
    }

    get userPermissionOptionsState(): Array<PermissionOption> {
        return [
            { value: 'none', name: this.$t('account.accessLevel.none') },
            { value: 'write', name: this.$t('account.accessLevel.write') },
            { value: 'admin', name: this.$t('account.accessLevel.admin') },
        ];
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
                shouldHideMargin: true,
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    handleCancel(): void {
        this.$emit('cancel');
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            await new Promise((resolve) => setTimeout(() => resolve(true), 2000));

            // const compact = this.compactType || '';
            // const { state, files } = this.formValues;
            // const uploadConfig = await this.fetchUploadConfig(compact, state);
            //
            // if (!this.isFormError) {
            //     await this.uploadFile(uploadConfig, files[0]);
            // }
            //
            // if (!this.isFormError) {
            //     this.isFormSuccessful = true;
            // }

            this.$emit('saved');

            this.endFormLoading();
        }
    }
}

export default toNative(UserRowEdit);

// export default UserRowEdit;
