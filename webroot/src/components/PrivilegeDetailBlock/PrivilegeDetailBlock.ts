//
//  PrivilegeDetailBlock.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/19/2025.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import PrivilegeHistory from '@components/PrivilegeHistory/PrivilegeHistory.vue';
import { License, LicenseStatus } from '@models/License/License.model';

@Component({
    name: 'PrivilegeDetailBlock',
    components: {
        PrivilegeHistory
    }
})
class PrivilegeDetailBlock extends Vue {
    // PROPS
    @Prop({ required: true }) privilege!: License;

    //
    // Computed
    //
    get status(): string {
        return this.isActive ? this.$t('licensing.statusOptions.active') : this.$t('licensing.statusOptions.inactive');
    }

    get statusDisplay(): string {
        return `${this.status} (${this.isDeactivated ? this.$t('licensing.deactivated') : this.expiryLabel}${this.expiresContent})`.trim();
    }

    get isActive(): boolean {
        return this.privilege?.status === LicenseStatus.ACTIVE;
    }

    get isDeactivated(): boolean {
        return Boolean(this.privilege?.isDeactivated());
    }

    get isExpired(): boolean {
        return Boolean(this.privilege?.isExpired());
    }

    get expiryLabel(): string {
        return this.isExpired ? this.$t('licensing.expired') : this.$t('licensing.expires');
    }

    get issuedTitle(): string {
        return this.$t('licensing.issued');
    }

    get issuedContent(): string {
        return this.privilege?.issueDateDisplay() || '';
    }

    get expiresContent(): string {
        return this.isDeactivated ? '' : `: ${this.privilege?.expireDateDisplay() || ''}`;
    }

    get disciplineTitle(): string {
        return this.$t('licensing.disciplineStatus');
    }

    get disciplineContent(): string {
        return this.$t('licensing.noDiscipline');
    }

    get privilegeId(): string {
        return this.privilege?.privilegeId || '';
    }
}

export default toNative(PrivilegeDetailBlock);

// export default PrivilegeDetailBlock;
