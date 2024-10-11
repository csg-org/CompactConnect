//
//  Home.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import {
    Component,
    Vue,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { Compact } from '@models/Compact/Compact.model';
import { AuthTypes } from '@/app.config';

@Component({
    name: 'HomePage',
    components: {}
})
class Home extends Vue {
    //
    // Lifecycle
    //
    created() {
        this.goToCompactHome();
    }

    //
    // Computed
    //
    get currentCompact(): Compact | null {
        return this.$store.state.user.currentCompact;
    }

    //
    // Methods
    //
    goToCompactHome() {
        const { currentCompact } = this;

        if (currentCompact) {
            const compactType = currentCompact.type;
            const authType = this.$store.getters['user/highestPermissionAuthType']();

            if (authType === AuthTypes.STAFF) {
                this.$router.push({ name: 'Licensing', params: { compact: compactType }});
            } else if (authType === AuthTypes.LICENSEE) {
                this.$router.push({ name: 'LicenseeDashboard', params: { compact: compactType }});
            }
        }
    }

    //
    // Watchers
    //
    @Watch('currentCompact') compactUpdated() {
        this.goToCompactHome();
    }
}

export default toNative(Home);

// export { Home };
