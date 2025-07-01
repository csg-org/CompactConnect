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
        Modal,
    }
})
class UpdateHomeJurisdiction extends mixins(MixinForm) {
    isHomeStateModalVisible = false;
    isHomeStateSuccess = false;
    isHomeStateError = false;
    homeStateErrorMessage = '';
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

    get homeStateOptions(): Array<SelectOption> {
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
        this.initHomeStateForm();
    }

    initHomeStateForm(): void {
        this.formData = reactive({
            newHomeState: new FormInput({
                id: 'new-home-state',
                name: 'new-home-state',
                label: computed(() => this.$t('homeStateChange.newHomeStateLabel')),
                valueOptions: this.homeStateOptions,
                validation: Joi.string().required().messages(this.joiMessages.string),
                value: ''
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit-home-state',
            })
        });
    }

    handleSubmit(): void {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.openHomeStateModal();
        }
    }

    openHomeStateModal(): void {
        this.isHomeStateModalVisible = true;
        this.isHomeStateSuccess = false;
        this.isHomeStateError = false;
        this.homeStateErrorMessage = '';
    }

    closeHomeStateModal(): void {
        this.isHomeStateModalVisible = false;
        this.isHomeStateSuccess = false;
        this.isHomeStateError = false;
        this.homeStateErrorMessage = '';
        this.formData.newHomeState.value = '';
    }

    async submitHomeStateChange(): Promise<void> {
        this.formData.newHomeState.validate({ asTouched: true });

        if (this.formData.newHomeState.isValid) {
            this.isFormLoading = true;
            this.isHomeStateError = false;
            this.homeStateErrorMessage = '';
            const newHomeState = this.formData.newHomeState.value;

            await this.$store.dispatch('user/updateHomeJurisdictionRequest', {
                data: { jurisdiction: newHomeState }
            }).then(() => {
                this.isHomeStateSuccess = true;
            }).catch((err: any) => {
                this.isHomeStateError = true;
                this.homeStateErrorMessage = err?.message || this.$t('common.somethingWentWrong');
            });

            this.isFormLoading = false;
        }
    }

    @Watch('userStore.model') onUserChanged() {
        if (this.formData?.newHomeState) {
            this.formData.newHomeState.value = '';
        }
    }
}

export default toNative(UpdateHomeJurisdiction);
