//
//  PrivilegeCard.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/8/2024.
//
import {
    Component,
    mixins,
    toNative,
    Prop
} from 'vue-facing-decorator';
import { reactive, computed, nextTick } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputTextarea from '@components/Forms/InputTextarea/InputTextarea.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import Modal from '@components/Modal/Modal.vue';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@/models/State/State.model';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';

@Component({
    name: 'PrivilegeCard',
    components: {
        InputTextarea,
        InputButton,
        InputSubmit,
        Modal,
    }
})
class PrivilegeCard extends mixins(MixinForm) {
    @Prop({ required: true }) privilege!: License;
    @Prop({ required: true }) licensee!: Licensee;
    @Prop({ default: false }) isPublicSearch!: boolean;

    //
    // Data
    //
    isPrivilegeActionMenuDisplayed = false;
    isDeactivatePrivilegeModalDisplayed = false;
    modalErrorMessage = '';

    //
    // Lifecycle
    //
    created(): void {
        this.initFormInputs();
    }

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

    get statusDisplay(): string {
        let licenseStatus = this.$t('licensing.statusOptions.inactive');

        if (this.isActive) {
            licenseStatus = this.$t('licensing.statusOptions.active');
        }

        return licenseStatus;
    }

    get isActive(): boolean {
        return this.privilege?.status === LicenseStatus.ACTIVE;
    }

    get stateTitle(): string {
        return this.$t('licensing.state');
    }

    get state(): State | null {
        return this.privilege?.issueState || null;
    }

    get stateAbbrev(): string {
        return this.state?.abbrev || '';
    }

    get stateContent(): string {
        return this.state?.name() || '';
    }

    get issuedTitle(): string {
        return this.$t('licensing.issued');
    }

    get issuedContent(): string {
        return this.privilege?.issueDateDisplay() || '';
    }

    get expiresTitle(): string {
        return this.isExpired ? this.$t('licensing.expired') : this.$t('licensing.expires');
    }

    get expiresContent(): string {
        return this.privilege?.isDeactivated() ? this.$t('licensing.deactivated') : this.privilege?.expireDateDisplay() || '';
    }

    get disciplineTitle(): string {
        return this.$t('licensing.disciplineStatus');
    }

    get disciplineContent(): string {
        return this.$t('licensing.noDiscipline');
    }

    get viewDetails(): string {
        return this.$t('common.viewDetails');
    }

    get isExpired(): boolean {
        return Boolean(this.privilege?.isExpired());
    }

    get privilegeId(): string {
        return this.privilege?.privilegeId || '';
    }

    get licenseeId(): string {
        return this.privilege?.licenseeId || '';
    }

    get privilegeTypeAbbrev(): string {
        return this.privilege?.licenseTypeAbbreviation() || '';
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            submitModalNotes: new FormInput({
                id: 'notes',
                name: 'notes',
                label: computed(() => this.$t('licensing.deactivateNotesTitle')),
                placeholder: computed(() => this.$t('licensing.deactivateNotesPlaceholder')),
                validation: Joi.string().required().max(256).messages(this.joiMessages.string),
                enforceMax: true,
            }),
            submitModalContinue: new FormInput({
                isSubmitInput: true,
                id: 'submit-modal-continue',
            }),
        });

        this.watchFormInputs(); // Important if you want automated form validation
    }

    togglePrivilegeActionMenu(): void {
        this.isPrivilegeActionMenuDisplayed = !this.isPrivilegeActionMenuDisplayed;
    }

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

    closePrivilegeActionMenu(): void {
        this.isPrivilegeActionMenuDisplayed = false;
    }

    async toggleDeactivatePrivilegeModal(): Promise<void> {
        if (this.isActive) {
            this.resetForm();
            this.isDeactivatePrivilegeModalDisplayed = !this.isDeactivatePrivilegeModalDisplayed;
            await nextTick();
            document.getElementById('deactivate-modal-cancel-button')?.focus();
        }
    }

    closeDeactivatePrivilegeModal(): void {
        this.isDeactivatePrivilegeModalDisplayed = false;
    }

    focusTrapDeactivatePrivilegeModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('deactivate-modal-cancel-button');
        const lastTabIndex = document.getElementById(this.formData.submitModalContinue.id);

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

    async submitDeactivatePrivilege(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const {
                currentCompactType: compactType,
                licenseeId,
                stateAbbrev,
                privilegeTypeAbbrev
            } = this;

            await this.$store.dispatch(`users/deletePrivilegeRequest`, {
                compact: compactType,
                licenseeId,
                privilegeState: stateAbbrev,
                licenseType: privilegeTypeAbbrev.toLowerCase(),
                notes: this.formData.submitModalNotes.value,
            }).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.closeDeactivatePrivilegeModal();
            }

            this.endFormLoading();
        }
    }

    resetForm(): void {
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;
        this.modalErrorMessage = '';
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }
}

export default toNative(PrivilegeCard);

// export default PrivilegeCard;
