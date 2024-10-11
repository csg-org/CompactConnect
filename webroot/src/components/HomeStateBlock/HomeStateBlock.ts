//
//  HomeStateBlock.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/3/2024.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import { State } from '@models/State/State.model';

@Component({
    name: 'HomeStateBlock',
})
class HomeStateBlock extends Vue {
    @Prop({ required: true }) state!: State;

    //
    // Computed
    //
    get stateName(): string {
        return this.state.name();
    }

    get homeStateTitle(): string {
        return this.$t('licensing.homeState');
    }
}

export default toNative(HomeStateBlock);

// export default HomeStateBlock;
