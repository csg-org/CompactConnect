//
//  Card.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/19/2024.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';

@Component({
    name: 'Card',
})
class Card extends Vue {
    @Prop({ default: false }) allowOverflow!: boolean;
}

export default toNative(Card);

// export default Card;
