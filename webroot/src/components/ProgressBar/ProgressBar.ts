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
    @Prop({ required: true }) progressPercent?: boolean;

    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //

    //
    // Methods
    //
}

export default toNative(ProgressBar);

// export default ProgressBar;
