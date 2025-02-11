//
//  ProgressBar.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/3/2025.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';

@Component({
    name: 'ProgressBar',
})
class ProgressBar extends Vue {
    @Prop({ default: 0 }) progressPercent?: number;

    //
    // Computed
    //

    get remainingPercent(): number {
        return 100 - (this.progressPercent || 0);
    }
}

export default toNative(ProgressBar);

// export default ProgressBar;
