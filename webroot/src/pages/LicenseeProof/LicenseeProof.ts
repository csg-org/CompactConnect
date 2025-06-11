//
//  LicenseeProof.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/2/2025.
//

import { Component, Vue, Watch } from 'vue-facing-decorator';
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import PrivilegesIcon from '@components/Icons/LicenseeUser/LicenseeUser.vue';
import UserIcon from '@components/Icons/User/User.vue';
import { Compact } from '@models/Compact/Compact.model';
import { License, LicenseStatus } from '@models/License/License.model';
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
        return this.licensee.privileges?.filter((privilege: License) =>
            privilege.status === LicenseStatus.ACTIVE)
            .sort((a: License, b: License) => {
                const dateA = moment(a.issueDate);
                const dateB = moment(b.issueDate);

                return dateB.valueOf() - dateA.valueOf(); // Most recent first
            }) || [];
    }

    get publicProfileUrl(): string {
        let url = '';
        const { domain } = this.$envConfig;
        const licenseeId = this.licensee.id;
        const compactType = this.currentCompactType;

        if (licenseeId && compactType) {
            url = `${domain}/Search/${compactType}/${licenseeId}`;
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
                // Get the primary color from CSS custom properties
                const primaryColor = getComputedStyle(document.documentElement)
                    .getPropertyValue('--primary-color').trim();

                this.qrCodeDataUrl = await QRCode.toDataURL(this.publicProfileUrl, {
                    width: 150,
                    margin: 1,
                    color: {
                        dark: primaryColor || '#2459a9', // Fallback to hardcoded value
                        light: '#ffffff'
                    }
                });
            } catch (error) {
                console.error('Error generating QR code:', error);
                this.qrCodeDataUrl = '';
            }
        }
    }

    // Watch for changes to publicProfileUrl
    @Watch('publicProfileUrl') async onPublicProfileUrlChanged() {
        await this.generateQRCode();
    }
}
