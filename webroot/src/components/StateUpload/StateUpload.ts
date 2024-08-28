//
//  StateUpload.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/18/2024.
//

import {
    Component,
    mixins,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import { uploadTypes } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Card from '@components/Card/Card.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputFile from '@components/Forms/InputFile/InputFile.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CheckCircle from '@components/Icons/CheckCircle/CheckCircle.vue';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';
import { CompactType } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';
import { dataApi } from '@network/data.api';
import Joi from 'joi';

@Component({
    name: 'StateUpload',
    components: {
        Card,
        MockPopulate,
        InputSelect,
        InputFile,
        InputSubmit,
        CheckCircle,
        LoadingSpinner,
    },
})
class StateUpload extends mixins(MixinForm) {
    //
    // Data
    //
    isInitializing = false;

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

    get compactType(): CompactType | null {
        return this.userStore.currentCompact?.type;
    }

    get stateOptions(): Array<any> {
        const { currentCompact } = this.userStore;
        const compactMemberStates = (currentCompact?.memberStates || []).map((state) => ({
            value: state.abbrev, name: state.name()
        }));
        const defaultSelectOption: any = { value: '' };

        if (!compactMemberStates.length) {
            defaultSelectOption.name = '';
        } else {
            defaultSelectOption.name = computed(() => this.$t('common.selectOption'));
        }

        compactMemberStates.unshift(defaultSelectOption);

        return compactMemberStates;
    }

    get isStateSelectEnabled(): boolean {
        return Boolean(this.stateOptions.length);
    }

    get submitLabel(): string {
        let label = this.$t('common.submit');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            state: new FormInput({
                id: 'state',
                name: 'state',
                label: computed(() => this.$t('common.state')),
                placeholder: computed(() => this.$t('common.state')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.stateOptions,
                isDisabled: !this.isStateSelectEnabled,
            }),
            files: new FormInput({
                id: 'file',
                name: 'file',
                label: computed(() => this.$t('common.uploadDocument')),
                placeholder: computed(() => this.$t('common.uploadDocument')),
                value: [],
                validation: Joi.array().min(1).messages(this.joiMessages.files),
                fileConfig: {
                    accepts: [uploadTypes.CSV.mime],
                    allowMultiple: false,
                    maxSizeMbPer: 100,
                    maxSizeMbAll: 100,
                    hint: computed(() => this.$t('stateUpload.uploadHint'))
                },
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    updateStateInput(): void {
        const stateInput = this.formData.state;

        stateInput.valueOptions = this.stateOptions;
        stateInput.isDisabled = !this.isStateSelectEnabled;
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const compact = this.compactType || '';
            const { state, files } = this.formValues;
            const uploadConfig = await this.fetchUploadConfig(compact, state);

            if (!this.isFormError) {
                await this.uploadFile(uploadConfig, files[0]);
            }

            if (!this.isFormError) {
                this.isFormSuccessful = true;
            }

            this.endFormLoading();
        }
    }

    async fetchUploadConfig(compact: string, state: string): Promise<any> {
        const uploadConfig = await dataApi.getStateUploadRequestConfig(compact, state).catch((err) => {
            this.setError(err.message);
        });

        return uploadConfig;
    }

    async uploadFile(uploadConfig: any, file: File): Promise<any> {
        const upload = await dataApi.stateUploadRequest(uploadConfig, file).catch((err) => {
            this.setError(err.message);
        });

        return upload;
    }

    async mockPopulate(): Promise<void> {
        this.populateFormInput(this.formData.state, this.stateOptions[1].value);
        this.populateFormInput(this.formData.files, new File([`a,b,c`], `test-file.csv`, { type: `text/csv` }));
    }

    //
    // Watchers
    //
    @Watch('compactType') updateCompactStates(): void {
        this.updateStateInput();
    }
}

export default toNative(StateUpload);

// export default StateUpload;
