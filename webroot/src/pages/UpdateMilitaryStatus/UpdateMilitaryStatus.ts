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
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'UpdateMilitaryStatus',
    components: {
        InputSubmit,
        InputRadioGroup,
        InputButton
    }
})
export default class MilitaryStatus extends mixins(MixinForm) {
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
        return [];
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            status: new FormInput({
                id: 'status',
                name: 'status',
                shouldHideLabel: true,
                label: computed(() => this.$t('military.affiliationType')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.statusOptions.map((option) => ({ ...option })),
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
        console.log('submit', this.formData);
    }
}
