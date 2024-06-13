//
//  InputTextarea.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 7/21/2020.
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
    name: 'InputTextarea',
})
class InputTextarea extends mixins(MixinInput) {
    @Prop({ default: false }) private shouldResizeX?: boolean;
    @Prop({ default: false }) private shouldResizeY?: boolean;
    @Prop({ default: false }) private shouldResize?: boolean;
    @Prop({ default: false }) private shouldBorderMatchBgColor?: boolean;
}

export default toNative(InputTextarea);

// export { InputTextarea };
