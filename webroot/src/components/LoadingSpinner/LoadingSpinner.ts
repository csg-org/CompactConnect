//
//  LoadingSpinner.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/28/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';

@Component
class LoadingSpinner extends Vue {
    @Prop({ default: false }) private noBgColor?: boolean;
}

export default toNative(LoadingSpinner);

// export { LoadingSpinner };
