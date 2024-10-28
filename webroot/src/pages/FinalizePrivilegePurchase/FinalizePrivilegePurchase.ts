//
//  FinalizePrivilegePurchase.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//

import { Component, mixins, Vue } from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputText from '@components/Forms/InputText/InputText.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
// import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';

@Component({
    name: 'FinalizePrivilegePurchase',
    components: {
        InputText,
        InputSelect,
        InputCheckbox,
        InputSubmit,
        InputButton
    }
})
export default class FinalizePrivilegePurchase extends mixins(MixinForm) {
    //
    // Data
    //
    created() {
        this.initFormInputs();
    }

    //
    // Lifecycle
    //

    //
    // Computed
    //

    //
    // Methods
    //
    handleSubmit() {
        console.log('submitted');
    }

    initFormInputs() {
        this.formData = reactive({
            compact: new FormInput({
                id: 'compact',
                name: 'compact',
                label: computed(() => this.$t('common.compact')),
                shouldHideLabel: true,
                shouldHideMargin: true,
                placeholder: computed(() => this.$t('common.compact')),
                value: this.currentCompact?.type,
                valueOptions: this.compactOptions,
            }),
        });
    }
}
