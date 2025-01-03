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
import { Compact } from '@models/Compact/Compact.model';
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
    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
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
}
