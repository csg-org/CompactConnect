//
//  CompactToggle.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/10/2020.
//

import { Component, Vue, Prop } from 'vue-facing-decorator';

@Component({
    emits: ['toggleCompact'],
})
export default class CompactToggle extends Vue {
    @Prop({ required: true }) private compactId!: string;
    @Prop({ required: true, default: false }) private isCompact!: boolean;

    //
    // Data
    //
    compactStore: any = {};

    //
    // Lifecycle
    //
    created() {
        this.compactStore = this.$store.state.compact;

        const { compactId, isCompact } = this;
        const compact = this.compactStore.compactMap[compactId];

        if (!compact) {
            this.$store.dispatch('compact/updateCompactMode', { compactId, isCompact });
        } else {
            this.toggleMode(compact.isCompact);
        }
    }

    //
    // Methods
    //
    toggleMode(isCompact) {
        const { compactId } = this;

        this.$store.dispatch('compact/updateCompactMode', { compactId, isCompact });
        this.$emit('toggleCompact', isCompact);
    }
}
