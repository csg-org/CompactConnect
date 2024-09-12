//
//  LicenseeSearch.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/12/2024.
//

import {
    Component,
    mixins,
    // Prop,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { CompactType } from '@models/Compact/Compact.model';
import { FormInput } from '@models/FormInput/FormInput.model';
// import Joi from 'joi';

@Component({
    name: 'LicenseeSearch',
    components: {
        InputText,
        InputSelect,
        InputSubmit,
    },
    emits: [ 'searchParams' ],
})
class LicenseeSearch extends mixins(MixinForm) {
    // @Prop({ required: true }) protected compactType!: CompactType;

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

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            ssn: new FormInput({
                id: 'ssn',
                name: 'ssn',
                label: computed(() => this.$t('licensing.ssn')),
                placeholder: '000-00-0000',
                // validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            state: new FormInput({
                id: 'state',
                name: 'state',
                label: computed(() => this.$t('common.state')),
                // validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.stateOptions,
            }),
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    async handleSubmit(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();

            const { ssn, state } = this.formValues;

            this.$emit('searchParams', { ssn, state });

            this.endFormLoading();
        }
    }
}

export default toNative(LicenseeSearch);

// export default LicenseeSearch;
