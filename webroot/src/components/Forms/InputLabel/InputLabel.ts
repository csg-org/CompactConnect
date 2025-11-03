//
//  InputLabel.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/21/2025.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import { FormInput } from '@models/FormInput/FormInput.model';
import InfoIcon from '@components/Icons/InfoCircle/InfoCircle.vue';

@Component({
    name: 'InputLabel',
    components: {
        InfoIcon,
    },
})
class InputLabel extends Vue {
    @Prop({ required: true, default: new FormInput() }) formInput!: FormInput;
    @Prop({ default: '' }) customFor!: string;
    @Prop({ default: false }) isRequired!: boolean;

    //
    // Data
    //
    shouldShowInfoBlock = false;

    //
    // Computed
    //
    get labelFor(): string {
        const { formInput, customFor } = this;

        return customFor || formInput.id || '';
    }

    get elementTransitionMode(): string {
        // Test utils have a bug with transition modes; this only includes the mode in non-test contexts.
        return (this.$envConfig.isTest) ? '' : 'out-in';
    }

    //
    // Methods
    //
    toggleInfoBlock(): void {
        this.shouldShowInfoBlock = !this.shouldShowInfoBlock;
    }

    hideInfoBlock(): void {
        this.shouldShowInfoBlock = false;
    }
}

export default toNative(InputLabel);

// export default InputLabel;
