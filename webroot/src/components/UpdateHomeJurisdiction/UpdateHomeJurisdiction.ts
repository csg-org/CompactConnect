//
//  UpdateHomeJurisdiction.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/1/2025.
//

import {
    Component,
    mixins,
    toNative,
    Watch
} from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import { stateList } from '@/app.config';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import Modal from '@components/Modal/Modal.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import Joi from 'joi';
import { LicenseeUser } from '@models/LicenseeUser/LicenseeUser.model';
import { State } from '@models/State/State.model';
import { User } from '@models/User/User.model';
import { StaffUser } from '@models/StaffUser/StaffUser.model';
import MixinForm from '@components/Forms/_mixins/form.mixin';

interface SelectOption {
    value: string | number;
    name: string | ComputedRef<string>;
    isDisabled?: boolean;
}

@Component({
    name: 'UpdateHomeJurisdiction',
    components: {
        InputSelect,
        InputButton,
        InputSubmit,
        CheckCircleIcon,
        Modal,
    }
})
class UpdateHomeJurisdiction extends mixins(MixinForm) {
    isModalVisible = false;
    isSuccess = false;
    isError = false;
    errorMessage = '';
    formData: any = {};

    get userStore() {
        return this.$store.state.user;
    }

    get user(): User | LicenseeUser | StaffUser {
        return this.userStore.model || new User();
    }

    get homeJurisdictionName(): string {
        const licensee = this.userStore.model?.licensee;

        return licensee?.homeJurisdiction?.name() || '';
    }

    get homeJurisdictionOptions(): Array<SelectOption> {
        const options = [{ value: '', name: `- ${this.$t('common.select')} -`, isDisabled: true }];

        stateList?.forEach((state) => {
            const stateObject = new State({ abbrev: state });
            const value = stateObject?.abbrev?.toLowerCase();
            const name = stateObject?.name();

            if (name && value) {
                options.push({ value, name, isDisabled: false });
            }
        });
        return options;
    }

    created() {
        this.initHomeJurisdictionForm();
    }

    initHomeJurisdictionForm(): void {
        this.formData = reactive({
            newHomeJurisdiction: new FormInput({
                id: 'new-home-jurisdiction',
                name: 'new-home-jurisdiction',
                label: computed(() => this.$t('homeJurisdictionChange.newHomeJurisdictionLabel')),
                valueOptions: this.homeJurisdictionOptions,
                validation: Joi.string().required().messages(this.joiMessages.string),
                value: ''
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-home-jurisdiction',
            })
        });
    }

    handleSubmit(): void {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.openModal();
        }
    }

    openModal(): void {
        this.isModalVisible = true;
        this.isSuccess = false;
        this.isError = false;
        this.errorMessage = '';
    }

    closeModal(): void {
        this.isModalVisible = false;
        this.isSuccess = false;
        this.isError = false;
        this.errorMessage = '';
        this.formData.newHomeJurisdiction.value = '';
    }

    async submitHomeJurisdictionChange(): Promise<void> {
        this.formData.newHomeJurisdiction.validate({ asTouched: true });

        if (this.formData.newHomeJurisdiction.isValid) {
            this.isFormLoading = true;
            this.isError = false;
            this.errorMessage = '';
            const newHomeJurisdiction = this.formData.newHomeJurisdiction.value;
            const jurisdictionUpdateData = {
                jurisdiction: newHomeJurisdiction
            };

            await this.$store.dispatch('user/updateHomeJurisdictionRequest', jurisdictionUpdateData).then(() => {
                this.isSuccess = true;
            }).catch((err: any) => {
                this.isError = true;
                this.errorMessage = err?.message || this.$t('common.tryAgain');
            });

            this.isFormLoading = false;
        }
    }

    @Watch('userStore.model') onUserChanged() {
        if (this.formData?.newHomeJurisdiction) {
            this.formData.newHomeJurisdiction.value = '';
        }
    }
}

export default toNative(UpdateHomeJurisdiction);
