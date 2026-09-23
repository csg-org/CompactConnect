//
//  PrivilegeCard.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//
import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import LicenseActionsModal from '@components/LicenseActionsModal/LicenseActionsModal.vue';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@/models/State/State.model';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';

@Component({
    name: 'PrivilegeCard',
    components: {
        InputButton,
        LicenseActionsModal,
    }
})
class PrivilegeCard extends Vue {
    @Prop({ required: true }) privilege!: License;
    @Prop({ required: true }) licensee!: Licensee;
    @Prop({ default: false }) isPublicSearch!: boolean;

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get currentUser(): StaffUser {
        return this.userStore.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get currentUserCompactPermission(): CompactPermission | null {
        const currentPermissions = this.currentUser?.permissions;
        const compactPermission = currentPermissions?.find((currentPermission: CompactPermission) =>
            currentPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get isCurrentUserCompactAdmin(): boolean {
        return this.currentUserCompactPermission?.isAdmin || false;
    }

    get isCurrentUserPrivilegeStateAdmin(): boolean {
        const { currentUserCompactPermission } = this;
        const statePermission = currentUserCompactPermission?.states?.find((permission) =>
            this.state?.abbrev === permission.state?.abbrev);
        const hasStatePermission = statePermission?.isAdmin || false;

        return hasStatePermission;
    }

    get isCurrentUserPrivilegeAdmin(): boolean {
        return this.isCurrentUserCompactAdmin || this.isCurrentUserPrivilegeStateAdmin;
    }

    get privilegeId(): string {
        return this.privilege?.privilegeId || '';
    }

    get licenseeId(): string {
        return this.privilege?.licenseeId || '';
    }

    get privilegeTypeDisplay(): string {
        return this.privilege?.licenseTypeDisplay() || '';
    }

    get privilegeTypeAbbrev(): string {
        return this.privilege?.licenseTypeAbbreviation() || '';
    }

    get isActive(): boolean {
        return this.privilege?.status === LicenseStatus.ACTIVE;
    }

    get statusDisplay(): string {
        let licenseStatus = this.$t('licensing.statusOptions.inactive');

        if (this.isActive) {
            licenseStatus = this.$t('licensing.statusOptions.active');
        }

        return licenseStatus;
    }

    get state(): State | null {
        return this.privilege?.issueState || null;
    }

    get stateContent(): string {
        return this.state?.name() || '';
    }

    get activeFromContent(): string {
        return this.privilege?.activeFromDateDisplay() || '';
    }

    get isExpired(): boolean {
        return Boolean(this.privilege?.isExpired());
    }

    get expiresTitle(): string {
        return (this.isExpired) ? this.$t('licensing.expired') : this.$t('licensing.expires');
    }

    get expiresContent(): string {
        return this.privilege?.expireDateDisplay() || '';
    }

    get isEncumbered(): boolean {
        return this.privilege?.isEncumbered() || false;
    }

    get isUnderInvestigation(): boolean {
        return this.privilege?.isUnderInvestigation() || false;
    }

    get disciplineContent(): string {
        let content = this.$t('licensing.noDiscipline');

        if (this.isEncumbered) {
            content = this.$t('licensing.encumbered');
        } else if (this.isUnderInvestigation) {
            content = this.$t('licensing.underInvestigationStatus');
        }

        return content;
    }

    get shouldShowDiscipline(): boolean {
        return this.$isAppGroupModePrivilegePurchase // Privilege purchase compacts public & staff
            || this.$isAppModeSocialWork             // Social Work compact public & staff
            || this.$isAppModePsyPact                // PsyPact compact public & staff
            || this.isCurrentUserPrivilegeAdmin;     // Any compact if staff user is admin of that state
    }

    //
    // Methods
    //
    goToPrivilegeDetailsPage(): void {
        const routeName = this.isPublicSearch ? 'PrivilegeDetailPublic' : 'PrivilegeDetail';

        this.$router.push(
            {
                name: routeName,
                params: {
                    compact: this.currentCompactType,
                    privilegeId: this.privilege.id,
                    licenseeId: this.licenseeId
                }
            }
        );
    }
}

export default toNative(PrivilegeCard);
