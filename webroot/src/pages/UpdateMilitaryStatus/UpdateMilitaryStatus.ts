//
//  UpdateMilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';

@Component({
    name: 'UpdateMilitaryStatus',
    components: {
        InputSubmit,
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

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-end',
            }),
        };

        this.formData = reactive(initFormData);
    }

    goBack() {
        console.log('go back');
    }
}
