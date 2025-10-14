//
//  LicenseeProof.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/2/2025.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import PrivilegesIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import ExpirationExplanationIcon from '@components/Icons/ExpirationExplanationIcon/ExpirationExplanationIcon.vue';
import UserIcon from '@components/Icons/User/User.vue';
import { Compact } from '@models/Compact/Compact.model';
import { License, LicenseStatus, LicenseType } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { State } from '@models/State/State.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import moment from 'moment';
import QRCode from 'qrcode';

@Component({
    name: 'LicenseeProof',
    components: {
        UserIcon,
        LicenseHomeIcon,
        PrivilegesIcon,
        ExpirationExplanationIcon
    }
})
export default class LicenseeProof extends Vue {
    //
    // Data
    //
    qrCodeDataUrl = '';

    //
    // Lifecycle
    //
    async mounted() {
        await this.generateQRCode();
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get currentDateDisplay(): string {
        return moment().format('MMM D, YYYY');
    }

    get licensee(): Licensee {
        return this.user?.licensee || new Licensee();
    }

    get homeJurisdiction(): State | null {
        return this.licensee?.homeJurisdiction || null;
    }

    get homeJurisdictionName(): string {
        return this.homeJurisdiction?.name() || '';
    }

    get userFullName(): string {
        return this.user?.getFullName() || '';
    }

    get licenseeLicenses(): Array<License> {
        return this.licensee.activeHomeJurisdictionLicenses() || [];
    }

    get licenseePrivileges(): Array<License> {
        const sortedPrivileges = (this.licensee.privileges ?? [])
            .filter((privilege: License) =>
                privilege.status === LicenseStatus.ACTIVE)
            .sort((a: License, b: License) => {
                const stateA = a.issueState?.name() ?? '';
                const stateB = b.issueState?.name() ?? '';
                let sort = 0;

                // Primary sort — by state name
                if (stateA < stateB) {
                    sort = -1;
                } else if (stateA > stateB) {
                    sort = 1;
                }

                // Secondary sort — by license type (custom order: OT, OTA, AUD, SLP)
                if (sort === 0) {
                    const typeA = a.licenseType ?? '';
                    const typeB = b.licenseType ?? '';
                    const typeOrder: Record<string, number> = {
                        [LicenseType.OCCUPATIONAL_THERAPIST]: 1,
                        [LicenseType.OCCUPATIONAL_THERAPY_ASSISTANT]: 2,
                        [LicenseType.AUDIOLOGIST]: 3,
                        [LicenseType.SPEECH_LANGUAGE_PATHOLOGIST]: 4,
                    };

                    // Unordered types sort after all custom ordered types
                    const customOrderCount = Object.keys(typeOrder).length;
                    const orderA = typeOrder[typeA] ?? customOrderCount + 1;
                    const orderB = typeOrder[typeB] ?? customOrderCount + 1;

                    sort = orderA - orderB;
                }

                return sort;
            });

        return sortedPrivileges;
    }

    get publicProfileUrl(): string {
        let url = '';
        const { domain } = this.$envConfig || {};
        const licenseeId = this.licensee.id;
        const compactType = this.currentCompactType;

        if (licenseeId && compactType) {
            try {
                const { href } = this.$router.resolve({
                    name: 'LicenseeDetailPublic',
                    params: {
                        compact: compactType,
                        licenseeId
                    }
                });

                url = new URL(href, domain).toString();
            } catch {
                url = '';
            }
        }

        return url;
    }

    //
    // Methods
    //
    printHandler(): void {
        window.print();
    }

    async generateQRCode(): Promise<void> {
        if (this.publicProfileUrl) {
            try {
                // Get the primary color from CSS custom properties with fallback
                const primaryColor = getComputedStyle(document.documentElement)
                    .getPropertyValue('--primary-color').trim() || '#2459a9';

                this.qrCodeDataUrl = await QRCode.toDataURL(this.publicProfileUrl, {
                    width: 150,
                    margin: 1,
                    color: {
                        dark: primaryColor,
                        light: '#ffffff'
                    }
                });
            } catch (error) {
                this.qrCodeDataUrl = '';
            }
        }
    }

    @Watch('publicProfileUrl') async onPublicProfileUrlChange(): Promise<void> {
        await this.generateQRCode();
    }
}
