//
//  InputRange.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2024.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    mixins,
    Prop,
    toNative
} from 'vue-facing-decorator';
import MixinInput from '@components/Forms/_mixins/input.mixin';

@Component({
    name: 'InputRange',
})
class InputRange extends mixins(MixinInput) {
    @Prop({ default: false }) showValueLabel?: boolean;
    @Prop({ default: false }) showTickMarks?: boolean;
    @Prop({ default: false }) showTickLabels?: boolean;
    @Prop({ default: 1 }) tickInterval?: number;

    //
    // Lifecycle
    //
    mounted() {
        this.updateBarProgress();
    }

    //
    // Computed
    //
    get rangeSteps(): Array<number> {
        const { min, max, stepInterval } = this.formInput.rangeConfig;
        const steps: Array<number> = [];

        for (let i = min; i <= max; i += stepInterval) {
            steps.push(i);
        }

        return steps;
    }

    get tickSteps(): Array<number> {
        const { min, max } = this.formInput.rangeConfig;
        const { showTickMarks, tickInterval } = this;
        const steps: Array<number> = [];

        if (showTickMarks && tickInterval) {
            this.rangeSteps.forEach((rangeStep) => {
                if (rangeStep === min || rangeStep === max || rangeStep % tickInterval === 0) {
                    steps.push(rangeStep);
                }
            });
        }

        return steps;
    }

    get formattedValue(): string {
        const { value, rangeConfig } = this.formInput || {};
        let formatted = (value.toString) ? value.toString() : '';

        if (rangeConfig.displayFormatter) {
            formatted = rangeConfig.displayFormatter(value);
        }

        return formatted;
    }

    //
    // Methods
    //
    input() {
        this.updateBarProgress();
    }

    updateBarProgress() {
        const { value, rangeConfig } = this.formInput || {};
        const { max = 0 } = rangeConfig || {};
        const progress = (Number(value) / max) * 100;
        const { rangeElement } = this.$refs;

        if (rangeElement) {
            (rangeElement as any).style.background = `linear-gradient(to right, #1C7CB0 ${progress}%, #c8c8c8 ${progress}%)`;
        }
    }
}

export default toNative(InputRange);

// export { InputRange };
