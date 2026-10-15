//
//  PrivacyPolicy.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/30/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'PrivacyPolicy',
    components: {
        InputButton,
    }
})
export default class PrivacyPolicy extends Vue {
    //
    // Computed
    //
    get appName(): string {
        return (this.$isAppModePsyPact) ? this.$t('common.appNamePsyPact') : this.$t('common.appName');
    }

    //
    // Methods
    //
    goBack(): void {
        if (window.history.state.back !== null) {
            this.$router.go(-1);
        } else {
            this.$router.push({ name: 'DashboardPublic' });
        }
    }
}
