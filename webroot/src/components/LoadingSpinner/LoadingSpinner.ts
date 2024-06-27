//
//  LoadingSpinner.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/28/2020.
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
