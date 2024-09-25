//
//  Home.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { Component, Vue } from 'vue-facing-decorator';
import { AuthTypes } from '@/app.config';
import { CompactType, Compact, CompactSerializer } from '@models/Compact/Compact.model';

@Component({
    name: 'HomePage',
    components: {}
})
export default class Home extends Vue {
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
    goToCompact(type?: CompactType) {
        let compactType = type || this.storeCurrentCompact?.type;

        if (!compactType) {
            this.setCurrentCompact();
            compactType = this.storeCurrentCompact?.type;
        }

        const authType = this.$store.getters['user/highestPermissionAuthType']();

        if (authType === AuthTypes.STAFF) {
            this.$router.push({ name: 'Licensing', params: { compact: compactType }});
        } else if (authType === AuthTypes.LICENSEE) {
            this.$router.push({ name: 'LicenseeDashboard', params: { compact: compactType }});
        }
    }

    setCurrentCompact() {
        const compact = CompactSerializer.fromServer({ type: CompactType.ASLP }); // Temp until server endpoints define this

        this.$store.dispatch('user/setCurrentCompact', compact);

        return compact;
    }
}
