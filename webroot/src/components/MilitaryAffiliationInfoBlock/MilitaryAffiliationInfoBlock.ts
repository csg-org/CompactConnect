//
//  MilitaryAffiliationInfoBlock.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/28/2025.
//

import {
    Component,
    toNative,
    Prop,
    mixins
} from 'vue-facing-decorator';
import { reactive } from 'vue';
import { AuthTypes } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import MilitaryDocumentRow from '@components/MilitaryDocumentRow/MilitaryDocumentRow.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { MilitaryAffiliation } from '@/models/MilitaryAffiliation/MilitaryAffiliation.model';

@Component({
    name: 'MilitaryAffiliationInfoBlock',
    components: {
        ListContainer,
        MilitaryDocumentRow,
        InputButton,
        InputSubmit,
        Modal
    }
})
class MilitaryAffiliationInfoBlock extends mixins(MixinForm) {
    @Prop({ required: true }) licensee?: Licensee;
    @Prop({ default: 'aslp' }) currentCompactType?: string;
    @Prop({ default: false }) shouldShowEditButtons?: boolean;

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
    get globalStore() {
        return this.$store.state;
    }

    get authType(): string {
        return this.globalStore.authType;
    }

    get userStore() {
        return this.$store.state.user;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get isLoggedInAsLicensee(): boolean {
        return this.authType === AuthTypes.LICENSEE;
    }

    get isLoggedInAsStaff(): boolean {
        return this.authType === AuthTypes.STAFF;
    }

    get staffUser(): StaffUser | null {
        return (this.isLoggedInAsStaff) ? this.userStore.model : null;
    }

    get staffPermission(): CompactPermission | null {
        const currentPermissions = this.staffUser?.permissions;
        const compactPermission = currentPermissions?.find((currentPermission: CompactPermission) =>
            currentPermission.compact.type === this.currentCompact?.type) || null;

        return compactPermission;
    }

    get isCompactAdmin(): boolean {
        return this.isLoggedInAsStaff && Boolean(this.staffPermission?.isAdmin);
    }

    get status(): string {
        let militaryStatus = this.$t('licensing.statusOptions.inactive');

        if (this.isStatusActive) {
            militaryStatus = this.$t('licensing.statusOptions.active');
        } else if (this.isStatusInitializing) {
            militaryStatus = this.$t('licensing.statusOptions.initializing');
        }

        return militaryStatus;
    }

    get isStatusInitializing(): boolean {
        return this.licensee?.isMilitaryStatusInitializing() || false;
    }

    get isStatusActive(): boolean {
        return this.licensee?.isMilitaryStatusActive() || false;
    }

    get affiliationType(): string {
        let militaryStatus = '';

        if (this.licensee) {
            const activeAffiliation = this.licensee.activeMilitaryAffiliation() as any;
            const isMilitary = this.licensee.isMilitaryStatusActive();

            if (isMilitary && activeAffiliation?.affiliationType === 'militaryMember') {
                militaryStatus = this.$tm('military.affiliationTypes.militaryMember');
            } else if (isMilitary && activeAffiliation?.affiliationType === 'militaryMemberSpouse') {
                militaryStatus = this.$tm('military.affiliationTypes.militaryMemberSpouse');
            } else {
                militaryStatus = this.$tm('military.affiliationTypes.none');
            }
        }

        return militaryStatus;
    }

    get auditStatus(): string {
        return this.licensee?.militaryAuditStatusName() || '';
    }

    get militaryDocumentHeader(): object {
        return {
            firstFilenameDisplay: () => this.$t('military.fileName'),
            dateOfUploadDisplay: () => this.$t('military.dateUploaded'),
            firstDownloadLink: () => this.$t('common.downloadFile'),
        };
    }

    get yesEndText(): string {
        return (this.$matches.phone.only) ? this.$t('common.yes') : this.$t('military.yesEnd');
    }

    get shouldShowEndButton(): boolean {
        return this.isStatusActive || this.isStatusInitializing;
    }

    get affiliations(): Array<MilitaryAffiliation> {
        return this.licensee?.militaryAffiliations || [];
    }

    get sortOptions(): Array<any> {
        return []; // Sorting not API supported
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-end',
            }),
        });
    }

    sortingChange(): boolean {
        return false; // Sorting not API supported
    }

    paginationChange(): boolean {
        return false; // Pagination not API supported
    }

    editInfo(): void {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'MilitaryStatusUpdate',
                params: { compact: this.currentCompactType }
            });
        }
    }

    async auditApprove(): Promise<void> {
        console.log('todo: approve');
    }

    async auditDecline(): Promise<void> {
        console.log('todo: decline');
    }

    async confirmEndMilitaryAffiliation(): Promise<void> {
        this.closeEndAffiliationModal();
        await this.$store.dispatch('user/endMilitaryAffiliationRequest');
        await this.$store.dispatch('user/getLicenseeAccountRequest');
    }

    startEndAffiliationFlow(): void {
        this.shouldShowEndAffiliationModal = true;
    }

    focusOnModalCancelButton(): void {
        const buttonComponent = this.$refs.noBackButton as InstanceType<typeof InputButton>;
        const button = buttonComponent?.$refs.button as HTMLElement;

        button?.focus();
    }

    closeEndAffiliationModal(): void {
        this.shouldShowEndAffiliationModal = false;
        this.$store.dispatch('setModalIsOpen', false);
    }

    focusTrap(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('no-back-button');
        const lastTabIndex = document.getElementById(this.formData.submitEnd.id);

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }
}

export default toNative(MilitaryAffiliationInfoBlock);

// export default MilitaryAffiliationInfoBlock;
