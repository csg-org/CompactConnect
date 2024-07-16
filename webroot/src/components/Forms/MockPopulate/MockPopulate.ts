//
//  MockPopulate.ts
//  CompactConnect
//
//  Created by InspiringApps on 6/20/2024.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';

@Component({
    name: 'MockPopulate',
    emits: [ 'selected' ],
})
class MockPopulate extends Vue {
    @Prop({ default: false }) isEnabled?: boolean;

    //
    // Methods
    //
    clicked(): void {
        this.$emit('selected');
    }
}

export default toNative(MockPopulate);

// export default MockPopulate;
