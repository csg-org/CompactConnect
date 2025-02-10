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
}

export default toNative(ProgressBar);

// export default ProgressBar;
