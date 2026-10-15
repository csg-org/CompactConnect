//
//  AppTypeSelector.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/22/2026.
//

import {
    Component,
    mixins,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import { AppModes } from '@/app.config';
import { clearStashIfIncompatibleWithAppMode } from '@utils/auth';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import { Compact, CompactType } from '@models/Compact/Compact.model';

@Component({
    name: 'AppTypeSelector',
    components: {
        InputSelect
    }
})
class AppTypeSelector extends mixins(MixinForm) {
    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
        clearStashIfIncompatibleWithAppMode(this.$appMode);
    }

    //
    // Computed
    //
    get appTypeOptions(): Array<{ value: string, name: string | ComputedRef }> {
        return [
            { value: 'compactconnect', name: computed(() => this.$t('common.appName')) },
            { value: 'psypact', name: 'PSYPACT' },
        ];
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            appType: new FormInput({
                id: 'app-type-global',
                name: 'app-type-global',
                label: computed(() => this.$t('common.appTypeLabel')),
                shouldHideLabel: true,
                value: (this.$isAppModePsyPact) ? 'psypact' : 'compactconnect',
                valueOptions: this.appTypeOptions,
            }),
        });
    }

    async handleAppTypeSelect(): Promise<void> {
        const { appType } = this.formData || {};
        const nextAppMode = (appType?.value === 'psypact') ? AppModes.PSYPACT : AppModes.JCC;

        if (nextAppMode === AppModes.PSYPACT) {
            await this.$store.dispatch('setAppMode', AppModes.PSYPACT);
            await this.$store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.PSYPACT }));
        } else {
            await this.$store.dispatch('setAppMode', AppModes.JCC);
            await this.$store.dispatch('user/setCurrentCompact', null);
        }

        clearStashIfIncompatibleWithAppMode(nextAppMode);
    }
}

export default toNative(AppTypeSelector);

export { AppTypeSelector };
