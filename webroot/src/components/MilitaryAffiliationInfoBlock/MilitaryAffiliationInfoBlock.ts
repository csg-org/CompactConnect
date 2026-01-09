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
import { reactive, computed } from 'vue';
import { AuthTypes, MilitaryAuditStatusTypes } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputTextarea from '@components/Forms/InputTextarea/InputTextarea.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CheckIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import AlertIcon from '@components/Icons/AlertTriangle/AlertTriangle.vue';
import ClockIcon from '@components/Icons/ClockStatus/ClockStatus.vue';
import MilitaryDocumentRow from '@components/MilitaryDocumentRow/MilitaryDocumentRow.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { MilitaryAffiliation } from '@/models/MilitaryAffiliation/MilitaryAffiliation.model';
import Joi from 'joi';

@Component({
    name: 'MilitaryAffiliationInfoBlock',
    components: {
        ListContainer,
        InputButton,
        InputTextarea,
        InputSubmit,
        CheckIcon,
        AlertIcon,
        ClockIcon,
        MilitaryDocumentRow,
        Modal
    }
})
class MilitaryAffiliationInfoBlock extends mixins(MixinForm) {
    @Prop({ required: true }) licensee?: Licensee;
    @Prop({ default: false }) shouldShowEditButtons?: boolean;

    //
    // Data
    //
    shouldShowMilitaryAuditApproveModal = false;
    shouldShowMilitaryAuditDeclineModal = false;
    shouldShowEndAffiliationModal = false;
    modalErrorMessage = '';

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

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
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

    get licenseeId(): string | null {
        return this.licensee?.id || null;
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

    get affiliations(): Array<MilitaryAffiliation> {
        return this.licensee?.militaryAffiliations || [];
    }

    get affiliationType(): string {
        let affiliation = '';

        if (this.licensee) {
            const activeAffiliation = this.licensee.activeMilitaryAffiliation() as any;
            const isMilitary = this.licensee.isMilitaryStatusActive();

            if (isMilitary && activeAffiliation?.affiliationType === 'militaryMember') {
                affiliation = this.$tm('military.affiliationTypes.militaryMember');
            } else if (isMilitary && activeAffiliation?.affiliationType === 'militaryMemberSpouse') {
                affiliation = this.$tm('military.affiliationTypes.militaryMemberSpouse');
            } else {
                affiliation = this.$tm('military.affiliationTypes.none');
            }
        }

        return affiliation;
    }

    get auditStatusTypes(): typeof MilitaryAuditStatusTypes {
        return MilitaryAuditStatusTypes;
    }

    get auditStatus(): string {
        return this.licensee?.militaryStatus || '';
    }

    get auditStatusName(): string {
        return this.licensee?.militaryAuditStatusName() || '';
    }

    get isAuditStatusApproved(): boolean {
        return this.auditStatus === MilitaryAuditStatusTypes.APPROVED;
    }

    get isAuditStatusDeclined(): boolean {
        return this.auditStatus === MilitaryAuditStatusTypes.DECLINED;
    }

    get isAuditStatusPending(): boolean {
        return this.auditStatus === MilitaryAuditStatusTypes.TENTATIVE;
    }

    get isAuditReady(): boolean {
        return Boolean(this.currentCompactType && this.licenseeId);
    }

    get auditStatusNote(): string {
        return this.licensee?.militaryStatusNote || '';
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

    get sortOptions(): Array<any> {
        return []; // Sorting not API supported
    }

    //
    // Methods
    //
    initFormInputs(): void {
        if (this.shouldShowMilitaryAuditApproveModal) {
            this.initFormInputsAuditApprove();
        } else if (this.shouldShowMilitaryAuditDeclineModal) {
            this.initFormInputsAuditDecline();
        } else if (this.shouldShowEndAffiliationModal) {
            this.initFormInputsEndAffiliation();
        }
    }

    // =======================================================
    //                      AUDIT STATUS
    // =======================================================
    initFormInputsAuditApprove(): void {
        this.formData = reactive({
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-approve',
            }),
        });
    }

    initFormInputsAuditDecline(): void {
        this.formData = reactive({
            auditDeclineNotes: new FormInput({
                id: 'decline-notes',
                name: 'decline-notes',
                label: computed(() => this.$t('military.auditDeclineConfirmNotesLabel')),
                placeholder: computed(() => this.$t('military.auditDeclineConfirmNotesPlaceholder')),
                validation: Joi.string().max(256).allow('', null).messages(this.joiMessages.string),
                enforceMax: true,
            }),
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-decline',
            }),
        });
    }

    toggleMilitaryAuditApproveModal(): void {
        this.shouldShowMilitaryAuditApproveModal = !this.shouldShowMilitaryAuditApproveModal;
        this.isFormError = false;
        this.modalErrorMessage = '';
        this.initFormInputs();
    }

    focusTrapAuditApprove(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('audit-approve-cancel-button');
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

    toggleMilitaryAuditDeclineModal(): void {
        this.shouldShowMilitaryAuditDeclineModal = !this.shouldShowMilitaryAuditDeclineModal;
        this.isFormError = false;
        this.modalErrorMessage = '';
        this.initFormInputs();
    }

    focusTrapAuditDecline(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById(this.formData.auditDeclineNotes.id);
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

    async auditSubmit(auditAction: MilitaryAuditStatusTypes): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { currentCompactType, licenseeId, formData } = this;
            const payload: { militaryStatus: MilitaryAuditStatusTypes, militaryStatusNote?: string } = {
                militaryStatus: auditAction,
            };

            if (formData.auditDeclineNotes?.value) {
                payload.militaryStatusNote = formData.auditDeclineNotes.value;
            }

            await this.$store.dispatch('users/updateMilitaryAuditRequest', {
                compact: currentCompactType,
                licenseeId,
                data: payload,
            }).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', {
                    compact: currentCompactType,
                    licenseeId
                }).catch(() => {
                    // Continue
                });
                this.shouldShowMilitaryAuditApproveModal = false;
                this.shouldShowMilitaryAuditDeclineModal = false;
            }

            this.endFormLoading();
        }
    }

    // =======================================================
    //                      END AFFILIATION
    // =======================================================
    initFormInputsEndAffiliation(): void {
        this.formData = reactive({
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-end',
            }),
        });
    }

    startEndAffiliationFlow(): void {
        this.shouldShowEndAffiliationModal = true;
        this.isFormError = false;
        this.modalErrorMessage = '';
        this.initFormInputs();
    }

    focusTrapEndAffiliation(event: KeyboardEvent): void {
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

    focusOnModalCancelButton(): void {
        const buttonComponent = this.$refs.noBackButton as InstanceType<typeof InputButton>;
        const button = buttonComponent?.$refs.button as HTMLElement;

        button?.focus();
    }

    async confirmEndMilitaryAffiliation(): Promise<void> {
        this.closeEndAffiliationModal();
        await this.$store.dispatch('user/endMilitaryAffiliationRequest');
        await this.$store.dispatch('user/getLicenseeAccountRequest');
    }

    closeEndAffiliationModal(): void {
        this.shouldShowEndAffiliationModal = false;
        this.$store.dispatch('setModalIsOpen', false);
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
}

export default toNative(MilitaryAffiliationInfoBlock);

// export default MilitaryAffiliationInfoBlock;
