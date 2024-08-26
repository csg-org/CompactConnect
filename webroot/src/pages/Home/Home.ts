//
//  Home.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { Component, Vue } from 'vue-facing-decorator';
import { Compact } from '@models/User/User.model';

@Component({
    name: 'HomePage',
    components: {}
})
export default class Home extends Vue {
    //
    // Data
    //
    defaultCompact = Compact.ASLP;

    //
    // Lifecycle
    //
    created() {
        this.goToCompact();
    }

    //
    // Computed
    //
    get storeCurrentCompact(): Compact | null {
        return this.$store.state.user.currentCompact;
    }

    //
    // Methods
    //
    goToCompact(compactId?: Compact) {
        let compact = compactId || this.storeCurrentCompact;

        if (!compact) {
            compact = this.setCurrentCompact();
        }

        this.$router.push({ name: 'Licensing', params: { compact }});
    }

    setCurrentCompact() {
        const compact = this.defaultCompact;

        this.$store.dispatch('user/setCurrentCompact', compact);

        return compact;
    }
}
