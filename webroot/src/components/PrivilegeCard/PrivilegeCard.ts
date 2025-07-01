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
import {
    reactive,
    computed,
    ComputedRef,
    nextTick
} from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputTextarea from '@components/Forms/InputTextarea/InputTextarea.vue';
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import MockPopulate from '@components/Forms/MockPopulate/MockPopulate.vue';
import Modal from '@components/Modal/Modal.vue';
import { dateDisplay } from '@models/_formatters/date';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { Compact } from '@models/Compact/Compact.model';
import { State } from '@/models/State/State.model';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';
import { AdverseAction } from '@/models/AdverseAction/AdverseAction.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';
import moment from 'moment';

@Component({
    name: 'PrivilegeCard',
    components: {
        MockPopulate,
        InputTextarea,
        InputDate,
        InputSelect,
        InputCheckbox,
        InputButton,
        InputSubmit,
        Modal,
        CheckCircleIcon,
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
    isEncumberPrivilegeModalDisplayed = false;
    isEncumberPrivilegeModalSuccess = false;
    isUnencumberPrivilegeModalDisplayed = false;
    isUnencumberPrivilegeModalSuccess = false;
    encumbranceInputs: Array<FormInput> = [];
    selectedEncumbrances: Array<AdverseAction> = [];
    modalErrorMessage = '';

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

    get licenseeName(): string {
        return this.licensee?.nameDisplay() || '';
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

    get stateAbbrev(): string {
        return this.state?.abbrev || '';
    }

    get stateContent(): string {
        return this.state?.name() || '';
    }

    get issuedContent(): string {
        return this.privilege?.issueDateDisplay() || '';
    }

    get isExpired(): boolean {
        return Boolean(this.privilege?.isExpired());
    }

    get expiresTitle(): string {
        return (this.isExpired) ? this.$t('licensing.expired') : this.$t('licensing.expires');
    }

    get expiresContent(): string {
        return (this.privilege?.isDeactivated()) ? this.$t('licensing.deactivated') : this.privilege?.expireDateDisplay() || '';
    }

    get isEncumbered(): boolean {
        return this.privilege?.isEncumbered() || false;
    }

    get disciplineContent(): string {
        return (this.isEncumbered) ? this.$t('licensing.encumbered') : this.$t('licensing.noDiscipline');
    }

    get adverseActions(): Array<AdverseAction> {
        return this.privilege?.adverseActions || [];
    }

    get npdbCategoryOptions(): Array<{ value: string, name: string | ComputedRef<string> }> {
        const options = this.$tm('licensing.npdbTypes').map((npdbType) => ({
            value: npdbType.key,
            name: npdbType.name,
        }));

        options.unshift({
            value: '',
            name: computed(() => this.$t('common.selectOption')),
        });

        return options;
    }

    get isUnencumberSubmitEnabled(): boolean {
        return Boolean(this.isFormValid && !this.isFormLoading && this.selectedEncumbrances.length);
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    //
    // Methods
    //
    initFormInputs(): void {
        if (this.isDeactivatePrivilegeModalDisplayed) {
            this.initFormInputsDeactivatePrivilege();
        } else if (this.isEncumberPrivilegeModalDisplayed) {
            this.initFormInputsEncumberPrivilege();
        } else if (this.isUnencumberPrivilegeModalDisplayed) {
            this.initFormInputsUnencumberPrivilege();
        }
    }

    initFormInputsDeactivatePrivilege(): void {
        this.formData = reactive({
            deactivateModalNotes: new FormInput({
                id: 'notes',
                name: 'notes',
                label: computed(() => this.$t('licensing.deactivateNotesTitle')),
                placeholder: computed(() => this.$t('licensing.deactivateNotesPlaceholder')),
                validation: Joi.string().required().max(256).messages(this.joiMessages.string),
                enforceMax: true,
            }),
            deactivateModalContinue: new FormInput({
                isSubmitInput: true,
                id: 'submit-modal-continue',
            }),
        });
        this.watchFormInputs();
    }

    initFormInputsEncumberPrivilege(): void {
        this.formData = reactive({
            encumberModalNpdbCategory: new FormInput({
                id: 'npdb-category',
                name: 'npdb-category',
                label: computed(() => this.$t('licensing.npdbCategoryLabel')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.npdbCategoryOptions,
            }),
            encumberModalStartDate: new FormInput({
                id: 'encumber-start',
                name: 'encumber-start',
                label: computed(() => this.$t('licensing.encumberStartDate')),
                placeholder: computed(() => 'MM/DD/YYYY'),
                validation: Joi.string().required().messages(this.joiMessages.string),
            }),
            encumberModalContinue: new FormInput({
                isSubmitInput: true,
                id: 'submit-modal-continue',
            }),
        });
        this.watchFormInputs();
    }

    initFormInputsUnencumberPrivilege(): void {
        this.formData = reactive({
            unencumberModalContinue: new FormInput({
                isSubmitInput: true,
                id: 'submit-modal-continue',
            }),
        });

        this.adverseActions.forEach((adverseAction: AdverseAction) => {
            const adverseActionId = adverseAction.id;
            const adverseActionInput = new FormInput({
                id: `adverse-action-data-${adverseActionId}`,
                name: `adverse-action-data-${adverseActionId}`,
                label: adverseAction.npdbTypeName(),
            });

            this.formData[`adverse-action-data-${adverseActionId}`] = adverseActionInput;
            this.encumbranceInputs.push(adverseActionInput);
        });
    }

    resetForm(): void {
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;
        this.modalErrorMessage = '';
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
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

    togglePrivilegeActionMenu(): void {
        this.isPrivilegeActionMenuDisplayed = !this.isPrivilegeActionMenuDisplayed;
    }

    closePrivilegeActionMenu(): void {
        this.isPrivilegeActionMenuDisplayed = false;
    }

    // =======================================================
    //                      DEACTIVATE
    // =======================================================
    async toggleDeactivatePrivilegeModal(): Promise<void> {
        if (this.isActive) {
            this.resetForm();
            this.isDeactivatePrivilegeModalDisplayed = !this.isDeactivatePrivilegeModalDisplayed;

            if (this.isDeactivatePrivilegeModalDisplayed) {
                this.initFormInputs();
                await nextTick();
                document.getElementById(this.formData.deactivateModalNotes.id)?.focus();
            }
        }
    }

    closeDeactivatePrivilegeModal(event?: Event): void {
        event?.preventDefault();
        this.isDeactivatePrivilegeModalDisplayed = false;
    }

    focusTrapDeactivatePrivilegeModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('notes');
        const lastTabIndex = (this.isFormValid && !this.isFormLoading)
            ? document.getElementById(this.formData.deactivateModalContinue.id)
            : document.getElementById('deactivate-modal-cancel-button');

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
                notes: this.formData.deactivateModalNotes.value,
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

    // =======================================================
    //                       ENCUMBER
    // =======================================================
    async toggleEncumberPrivilegeModal(): Promise<void> {
        this.resetForm();
        this.isEncumberPrivilegeModalDisplayed = !this.isEncumberPrivilegeModalDisplayed;

        if (this.isEncumberPrivilegeModalDisplayed) {
            this.initFormInputs();
            await nextTick();
            document.getElementById(this.formData.encumberModalNpdbCategory.id)?.focus();
        }
    }

    closeEncumberPrivilegeModal(event?: Event): void {
        event?.preventDefault();
        this.isEncumberPrivilegeModalDisplayed = false;
        this.isEncumberPrivilegeModalSuccess = false;
    }

    focusTrapEncumberPrivilegeModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('npdb-category')
            || document.getElementById('encumber-modal-cancel-button');
        const lastTabIndex = (this.isFormValid && !this.isFormLoading && !this.isEncumberPrivilegeModalSuccess)
            ? document.getElementById(this.formData.encumberModalContinue.id)
            : document.getElementById('encumber-modal-cancel-button');

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

    async submitEncumberPrivilege(): Promise<void> {
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

            await this.$store.dispatch(`users/encumberPrivilegeRequest`, {
                compact: compactType,
                licenseeId,
                privilegeState: stateAbbrev,
                licenseType: privilegeTypeAbbrev.toLowerCase(),
                npdbCategory: this.formData.encumberModalNpdbCategory.value,
                startDate: this.formData.encumberModalStartDate.value,
            }).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.isEncumberPrivilegeModalSuccess = true;
                await nextTick();
                document.getElementById('encumber-modal-cancel-button')?.focus();
            }

            this.endFormLoading();
        }
    }

    // =======================================================
    //                      UN-ENCUMBER
    // =======================================================
    clickUnencumberItem(adverseAction: AdverseAction, event?: PointerEvent | KeyboardEvent): void {
        const { srcElement, type } = event || {};
        const adverseActionId = adverseAction?.id;
        const nodeType = (srcElement as Element)?.nodeName;

        // Handle wrapped checkbox input so that the wrapper events act the same as the nested checkbox input
        if (nodeType === 'INPUT') {
            if (type === 'keyup') {
                event?.preventDefault();
            }
            event?.stopPropagation();
        } else if (nodeType === 'LABEL') {
            event?.preventDefault();
        }

        if (adverseActionId) {
            const formInput = this.formData[`adverse-action-data-${adverseActionId}`];
            const existingValue = Boolean(formInput?.value);

            if (formInput) {
                formInput.value = !existingValue;

                if (formInput.value) {
                    this.addUnencumberFormData(adverseAction);
                } else {
                    this.removeUnencumberFormData(adverseActionId);
                }
            }
        }
    }

    async addUnencumberFormData(adverseAction: AdverseAction): Promise<void> {
        const adverseActionId = adverseAction.id;

        if (adverseActionId) {
            const adverseActionEndDateInput = new FormInput({
                id: `adverse-action-${adverseActionId}`,
                name: `adverse-action-${adverseActionId}`,
                label: computed(() => this.$t('licensing.confirmPrivilegeUnencumberEndDate')),
                validation: Joi.string().required().messages(this.joiMessages.string),
            });

            this.formData[`adverse-action-end-date-${adverseActionId}`] = adverseActionEndDateInput;
            if (!this.selectedEncumbrances.find((selectedAction) => selectedAction.id === adverseActionId)) {
                this.selectedEncumbrances.push(adverseAction);
            }
            if (adverseAction.endDate) {
                await nextTick();
                this.formData[`adverse-action-end-date-${adverseActionId}`].value = adverseAction.endDate;
                adverseActionEndDateInput.validate();
            }
            this.watchFormInputs();
            this.validateAll();
        }
    }

    removeUnencumberFormData(adverseActionId: string): void {
        delete this.formData[`adverse-action-end-date-${adverseActionId}`];
        this.selectedEncumbrances = this.selectedEncumbrances.filter((adverseAction: AdverseAction) =>
            (adverseAction.id || '') !== adverseActionId);
        this.watchFormInputs();
        this.validateAll();
    }

    getFirstEnabledFormInputId(): string {
        const { formData } = this;
        const firstEnabledFormInput: string = Object.keys(formData)
            .filter((key) => key !== 'unencumberModalContinue')
            .find((key) => !formData[key].isDisabled) || '';
        const firstEnabledInputId = formData[firstEnabledFormInput]?.id || 'unencumber-modal-cancel-button';

        return firstEnabledInputId;
    }

    async toggleUnencumberPrivilegeModal(): Promise<void> {
        this.resetForm();
        this.isUnencumberPrivilegeModalDisplayed = !this.isUnencumberPrivilegeModalDisplayed;

        if (this.isUnencumberPrivilegeModalDisplayed) {
            this.initFormInputs();
            await nextTick();
            const firstEnabledInputId = this.getFirstEnabledFormInputId();
            const firstTabIndex = document.getElementById(firstEnabledInputId);

            firstTabIndex?.focus();
        }
    }

    closeUnencumberPrivilegeModal(event?: Event): void {
        event?.preventDefault();
        this.selectedEncumbrances = [];
        this.isUnencumberPrivilegeModalDisplayed = false;
        this.isUnencumberPrivilegeModalSuccess = false;
    }

    focusTrapUnencumberPrivilegeModal(event: KeyboardEvent): void {
        const { isUnencumberSubmitEnabled } = this;
        const firstEnabledInputId = this.getFirstEnabledFormInputId();
        const firstTabIndex = document.getElementById(firstEnabledInputId);
        const lastTabIndex = (isUnencumberSubmitEnabled)
            ? document.getElementById('submit-modal-continue')
            : document.getElementById('unencumber-modal-cancel-button');

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

    async submitUnencumberPrivilege(): Promise<void> {
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
            const errorMessages: Array<string> = [];

            await Promise.all(this.selectedEncumbrances.map(async (adverseAction: AdverseAction) => {
                const adverseActionId = adverseAction.id;

                await this.$store.dispatch(`users/unencumberPrivilegeRequest`, {
                    compact: compactType,
                    licenseeId,
                    privilegeState: stateAbbrev,
                    licenseType: privilegeTypeAbbrev.toLowerCase(),
                    encumbranceId: adverseActionId,
                    endDate: this.formData[`adverse-action-end-date-${adverseActionId}`].value,
                }).catch((err) => {
                    errorMessages.push(err?.message || this.$t('common.error'));
                });
            }));

            if (errorMessages.length) {
                this.modalErrorMessage = errorMessages.join('; ');
                this.isFormError = true;
            }

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.isUnencumberPrivilegeModalSuccess = true;
                await nextTick();
                document.getElementById('unencumber-modal-cancel-button')?.focus();
            }

            this.endFormLoading();
        }
    }

    async focusTrapTeleportedDatepicker(formInput: FormInput, isOpen: boolean): Promise<void> {
        if (isOpen) {
            await nextTick();
            document.getElementById(`dp-menu-${formInput.id}`)?.focus();
        } else {
            document.getElementById(`dp-input-icon-open-${formInput.id}`)?.focus();
        }
    }

    isEncumbranceSelected(adverseAction: AdverseAction): boolean {
        return this.selectedEncumbrances.some((selected: AdverseAction) => selected.id === adverseAction.id);
    }

    dateDisplayFormat(unformattedDate: string): string {
        return dateDisplay(unformattedDate);
    }

    async mockPopulate(): Promise<void> {
        if (this.isDeactivatePrivilegeModalDisplayed) {
            this.formData.deactivateModalNotes.value = `Sample note`;
            this.validateAll({ asTouched: true });
        } else if (this.isEncumberPrivilegeModalDisplayed) {
            this.formData.encumberModalNpdbCategory.value = this.npdbCategoryOptions[1]?.value;
            this.formData.encumberModalStartDate.value = moment().format('YYYY-MM-DD');
            this.validateAll({ asTouched: true });
        } else if (this.isUnencumberPrivilegeModalDisplayed) {
            this.selectedEncumbrances.forEach((selected) => {
                this.clickUnencumberItem(selected);
            });
            await Promise.all(this.adverseActions.map(async (adverseAction) => {
                this.clickUnencumberItem(adverseAction);
                await nextTick();
                this.formData[`adverse-action-end-date-${adverseAction.id}`].value = moment().format('YYYY-MM-DD');
            }));
            this.validateAll({ asTouched: true });
        }
    }
}

export default toNative(PrivilegeCard);

// export default PrivilegeCard;
