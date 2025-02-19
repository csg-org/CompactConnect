//
//  LicenseIcon.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/16/2025.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';

@Component({
    name: 'LicenseIcon',
})
class LicenseIcon extends Vue {
   @Prop({ default: 'black' }) fill?: string;
}

export default toNative(LicenseIcon);

// export default LicenseIcon;
