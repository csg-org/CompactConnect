//
//  MilitaryStatusUpdate.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputFile from '@components/Forms/InputFile/InputFile.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'MilitaryStatusUpdate',
    components: {
        InputSubmit,
        InputRadioGroup,
        InputFile,
        InputButton
    }
})
export default class MilitaryStatusUpdate extends mixins(MixinForm) {
    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get attestationTitleText(): any {
        return `${this.$t('licensing.attestation')}*`;
    }

    get statusOptions(): any {
        return this.$tm('styleGuide.statusOptions');
    }

    get affiliationTypeOptions(): any {
        return this.$tm('military.affiliationAttestationOptions');
    }

    get documentProofLabel(): any {
        return this.$t('military.documentProofLabel');
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            affiliationType: new FormInput({
                id: 'affiliation-type',
                name: 'affiliation-type',
                shouldHideLabel: true,
                label: computed(() => this.$t('military.affiliationType')),
                validation: Joi.string().required().messages({ ...this.joiMessages.string }),
                valueOptions: this.affiliationTypeOptions.map((option) => ({ ...option })),
            }),
            document: new FormInput({
                id: 'document',
                name: 'document',
                label: computed(() => this.$t('military.documentProofLabel')),
                placeholder: computed(() => this.$t('military.documentProofLabel')),
                value: [],
                shouldHideLabel: true,
                validation: Joi.array().min(1).max(1).messages(this.joiMessages.files),
                fileConfig: {
                    accepts: [`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `image/png`, `image/jpeg`],
                    allowMultiple: false,
                    maxSizeMbPer: 9,
                    maxSizeMbAll: 9,
                },
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });

        this.watchFormInputs();
    }

    goBack() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'MilitaryStatus',
                params: { compact: this.currentCompactType }
            });
        }
    }

    async handleSubmit() {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            let uploadResponse;

            const documentUploadData = this.transformFormDataToUploadIntent(this.formData);

            if (!this.isFormError) {
                uploadResponse = await this.$store.dispatch('user/uploadMilitaryAffiliationRequest', documentUploadData);
            }

            if (!this.isFormError) {
                this.isFormSuccessful = true;
            }

            this.endFormLoading();

            if (uploadResponse?.status === 204) {
                this.resetForm(true);
            } else {
                const parser = new DOMParser();
                const xmlData = parser.parseFromString(uploadResponse?.response?.data || '', 'text/xml');

                const xmlErrorMessage = xmlData.getElementsByTagName('Message')[0]?.innerHTML || '';

                this.resetForm(false, xmlErrorMessage);
            }
        }
    }

    resetForm(isSuccessful, xmlErrorMessage = '') {
        this.formData.document.value.length = 0;
        this.formData.affiliationType.value = null;
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;

        if (isSuccessful) {
            this.$nextTick(() => {
                this.updateFormSubmitSuccess(this.$t('military.successLongProcess'));
            });
        } else {
            this.$nextTick(() => {
                this.updateFormSubmitError(xmlErrorMessage || this.$t('military.submitFail'));
                this.$store.dispatch('user/getLicenseeAccountRequest');
            });
        }
    }

    transformFormDataToUploadIntent(formData) {
        const affiliationType = formData.affiliationType.value;
        const document = formData.document.value[0];
        const fileNames = [ document.name ];

        return { affiliationType, fileNames, document };
    }
}
