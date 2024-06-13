//
//  CompactToggle.mixin.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/21/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    Vue,
    Prop
} from 'vue-facing-decorator';

@Component({
    name: 'MixinCompactToggle',
})
class MixinCompactToggle extends Vue {
    @Prop({ required: true }) protected listId!: string;
    @Prop({ default: false }) private includeCompactToggle!: boolean;

    //
    // Data
    //
    isCompact = false;

    //
    // Methods
    //
    compactToggle(isCompact) {
        this.isCompact = isCompact;
    }
}

// export default toNative(MixinCompactToggle);

export default MixinCompactToggle;
