//
//  UpdateMilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import InputFile from '@components/Forms/InputFile/InputFile.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'UpdateMilitaryStatus',
    components: {
        InputSubmit,
        InputRadioGroup,
        InputFile,
        InputButton
    }
})
export default class UpdateMilitaryStatus extends mixins(MixinForm) {
    //
    // Data
    //

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get userStore(): any {
        return this.$store.state.user;
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

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            affiliationType: new FormInput({
                id: 'affiliation-type',
                name: 'affiliation-type',
                shouldHideLabel: true,
                label: computed(() => this.$t('military.affiliationType')),
                validation: Joi.string().required(),
                valueOptions: this.affiliationTypeOptions.map((option) => ({ ...option })),
            }),
            document: new FormInput({
                id: 'document',
                name: 'document',
                label: computed(() => this.$t('military.documentProofLabel')),
                placeholder: computed(() => this.$t('military.documentProofLabel')),
                value: [],
                validation: Joi.array().min(1).max(1),
                fileConfig: {
                    accepts: [`application/pdf`, `application/vnd.openxmlformats-officedocument.wordprocessingml.document`, `image/png`, `image/jpeg`],
                    allowMultiple: false,
                    maxSizeMbPer: 100,
                    maxSizeMbAll: 100,
                },
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        };

        this.formData = reactive(initFormData);
    }

    goBack() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'MilitaryStatus',
                params: { compact: this.currentCompactType }
            });
        }
    }

    handleSubmit() {
        const documentUploadData = this.transformFormDataToUploadIntent(this.formData);

        console.log('documentUploadData', documentUploadData);

        this.$store.dispatch('user/uploadMilitaryAffiliationRequest', documentUploadData);
    }

    transformFormDataToUploadIntent(formData) {
        console.log('formData', formData);
        const affiliationType = formData.affiliationType.value;
        const fileNames = [ formData.document.value[0].name ];

        return { affiliationType, fileNames };
    }
}
