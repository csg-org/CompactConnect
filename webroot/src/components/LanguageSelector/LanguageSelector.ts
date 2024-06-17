//
//  LanguageSelector.ts
//  InspiringApps modules.
//
//  Created by InspiringApps on 5/8/2024.
//

import { Component, mixins, toNative } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import { languagesEnabled } from '@/app.config';
import Joi from 'joi';

@Component({
    name: 'LanguageSelector',
    components: {
        InputSelect
    }
})
class LanguageSelector extends mixins(MixinForm) {
    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get currentLanguage() {
        return this.$i18n.locale;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            language: new FormInput({
                id: 'language',
                name: 'language',
                label: computed(() => this.$t('common.language')),
                placeholder: computed(() => this.$t('common.language')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                value: this.currentLanguage,
                valueOptions: languagesEnabled,
            }),
        });
        this.watchFormInputs(); // Important if you want automated form validation
    }

    handleLanguageSelect(): void {
        this.$i18n.locale = this.formData.language.value;
    }
}

export default toNative(LanguageSelector);

// export { LanguageSelector };
