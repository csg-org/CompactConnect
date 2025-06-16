//
//  MilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import MilitaryAffiliationInfoBlock from '@components/MilitaryAffiliationInfoBlock/MilitaryAffiliationInfoBlock.vue';
import { Compact } from '@models/Compact/Compact.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { Licensee } from '@/models/Licensee/Licensee.model';

@Component({
    name: 'MilitaryStatus',
    components: {
        InputButton,
        MilitaryAffiliationInfoBlock,
    }
})
export default class MilitaryStatus extends mixins(MixinForm) {
    //
    // Data
    //
    shouldShowEndAffiliationModal = false;

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser {
        return this.userStore?.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get statusTitleText(): string {
        return this.$t('licensing.status').toUpperCase();
    }

    goBack() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'Account'
            });
        }
    }
}
