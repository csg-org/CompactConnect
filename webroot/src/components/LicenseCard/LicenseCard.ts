//
//  LicenseCard.ts
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
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import LicenseIcon from '@components/Icons/LicenseIcon/LicenseIcon.vue';
import LicenseHomeIcon from '@components/Icons/LicenseHome/LicenseHome.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import CloseXIcon from '@components/Icons/CloseX/CloseX.vue';
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
    name: 'LicenseCard',
    components: {
        MockPopulate,
        InputDate,
        InputSelect,
        InputCheckbox,
        InputButton,
        InputSubmit,
        Modal,
        LicenseIcon,
        LicenseHomeIcon,
        CheckCircleIcon,
        CloseXIcon,
    }
})
class LicenseCard extends mixins(MixinForm) {
    @Prop({ required: true }) license!: License;
    @Prop({ required: true }) licensee!: Licensee;
    @Prop({ default: null }) homeState?: State | null;
    @Prop({ default: false }) shouldIncludeLogo?: boolean;

    //
    // Data
    //
    isLicenseActionMenuDisplayed = false;
    isDeactivateLicenseModalDisplayed = false;
    isEncumberLicenseModalDisplayed = false;
    isEncumberLicenseModalSuccess = false;
    isUnencumberLicenseModalDisplayed = false;
    isUnencumberLicenseModalSuccess = false;
    encumbranceInputs: Array<FormInput> = [];
    selectedEncumbrances: Array<AdverseAction> = [];
    modalErrorMessage = '';

    //
    // Lifecycle
    //
    mounted(): void {
        this.addStatusDescriptionExpansion();
    }

    beforeUnmount(): void {
        this.removeStatusDescriptionExpansion();
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

    get isCurrentUserLicenseStateAdmin(): boolean {
        const { currentUserCompactPermission } = this;
        const statePermission = currentUserCompactPermission?.states?.find((permission) =>
            this.state?.abbrev === permission.state?.abbrev);
        const hasStatePermission = statePermission?.isAdmin || false;

        return hasStatePermission;
    }

    get isCurrentUserLicenseAdmin(): boolean {
        return this.isCurrentUserCompactAdmin || this.isCurrentUserLicenseStateAdmin;
    }

    get licenseeId(): string {
        return this.license?.licenseeId || '';
    }

    get licenseeNumber(): string {
        return this.license?.licenseNumber || '';
    }

    get licenseeName(): string {
        return this.licensee?.nameDisplay() || '';
    }

    get licenseNumber(): string {
        return this.license?.licenseNumber || '';
    }

    get licenseTypeAbbrev(): string {
        return this.license?.licenseTypeAbbreviation() || '';
    }

    get isActive(): boolean {
        return this.license?.status === LicenseStatus.ACTIVE;
    }

    get statusDisplay(): string {
        let licenseStatus = this.$t('licensing.statusOptions.inactive');

        if (this.isActive) {
            licenseStatus = this.$t('licensing.statusOptions.active');
        }

        return licenseStatus;
    }

    get statusDescriptionDisplay(): string {
        return this.license?.statusDescription || '';
    }

    get isCompactEligible(): boolean {
        return Boolean(this.license?.isCompactEligible());
    }

    get state(): State | null {
        return this.license?.issueState || null;
    }

    get stateAbbrev(): string {
        return this.state?.abbrev || '';
    }

    get stateContent(): string {
        return this.state?.name() || '';
    }

    get isHomeState(): boolean {
        return this.license?.issueState?.abbrev === this.homeState?.abbrev;
    }

    get issuedContent(): string {
        return this.license?.issueDateDisplay() || '';
    }

    get isExpired(): boolean {
        return Boolean(this.license?.isExpired());
    }

    get expiresTitle(): string {
        return (this.isExpired) ? this.$t('licensing.expired') : this.$t('licensing.expires');
    }

    get expiresContent(): string {
        return this.license?.expireDateDisplay() || '';
    }

    get isEncumbered(): boolean {
        return this.license?.isEncumbered() || false;
    }

    get disciplineContent(): string {
        return (this.isEncumbered) ? this.$t('licensing.encumbered') : this.$t('licensing.noDiscipline');
    }

    get adverseActions(): Array<AdverseAction> {
        return this.license?.adverseActions || [];
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
        if (this.isEncumberLicenseModalDisplayed) {
            this.initFormInputsEncumberLicense();
        } else if (this.isUnencumberLicenseModalDisplayed) {
            this.initFormInputsUnencumberLicense();
        }
    }

    initFormInputsEncumberLicense(): void {
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

    initFormInputsUnencumberLicense(): void {
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

    toggleLicenseActionMenu(): void {
        this.isLicenseActionMenuDisplayed = !this.isLicenseActionMenuDisplayed;
    }

    closeLicenseActionMenu(): void {
        this.isLicenseActionMenuDisplayed = false;
    }

    addStatusDescriptionExpansion(): void {
        const statusDescriptionElement = this.$refs.statusDescription as HTMLElement;

        if (statusDescriptionElement) {
            statusDescriptionElement.addEventListener('mouseenter', this.statusDescriptionExpansionEvent);
        }
    }

    removeStatusDescriptionExpansion(): void {
        const statusDescriptionElement = this.$refs.statusDescription as HTMLElement;

        if (statusDescriptionElement) {
            statusDescriptionElement.removeEventListener('mouseenter', this.statusDescriptionExpansionEvent);
        }
    }

    statusDescriptionExpansionEvent(event: Event): void {
        // Simple desktop hover for overflowed status descriptions; mvp while we test how states will use this field.
        const element = event.target as HTMLElement;

        if (!element.title && element.scrollWidth > element.clientWidth) {
            element.title = element.innerText;
        }
    }

    // =======================================================
    //                       ENCUMBER
    // =======================================================
    async toggleEncumberLicenseModal(): Promise<void> {
        this.resetForm();
        this.isEncumberLicenseModalDisplayed = !this.isEncumberLicenseModalDisplayed;

        if (this.isEncumberLicenseModalDisplayed) {
            this.initFormInputs();
            await nextTick();
            document.getElementById(this.formData.encumberModalNpdbCategory.id)?.focus();
        }
    }

    closeEncumberLicenseModal(event?: Event): void {
        event?.preventDefault();
        this.isEncumberLicenseModalDisplayed = false;
        this.isEncumberLicenseModalSuccess = false;
    }

    focusTrapEncumberLicenseModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('npdb-category')
            || document.getElementById('encumber-modal-cancel-button');
        const lastTabIndex = (this.isFormValid && !this.isFormLoading && !this.isEncumberLicenseModalSuccess)
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

    async submitEncumberLicense(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const {
                currentCompactType: compactType,
                licenseeId,
                stateAbbrev,
                licenseTypeAbbrev
            } = this;

            await this.$store.dispatch(`users/encumberLicenseRequest`, {
                compact: compactType,
                licenseeId,
                licenseState: stateAbbrev,
                licenseType: licenseTypeAbbrev.toLowerCase(),
                npdbCategory: this.formData.encumberModalNpdbCategory.value,
                startDate: this.formData.encumberModalStartDate.value,
            }).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.isEncumberLicenseModalSuccess = true;
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
                label: computed(() => this.$t('licensing.confirmLicenseUnencumberEndDate')),
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

    async toggleUnencumberLicenseModal(): Promise<void> {
        this.resetForm();
        this.isUnencumberLicenseModalDisplayed = !this.isUnencumberLicenseModalDisplayed;

        if (this.isUnencumberLicenseModalDisplayed) {
            this.initFormInputs();
            await nextTick();
            const firstEnabledInputId = this.getFirstEnabledFormInputId();
            const firstTabIndex = document.getElementById(firstEnabledInputId);

            firstTabIndex?.focus();
        }
    }

    closeUnencumberLicenseModal(event?: Event): void {
        event?.preventDefault();
        this.selectedEncumbrances = [];
        this.isUnencumberLicenseModalDisplayed = false;
        this.isUnencumberLicenseModalSuccess = false;
    }

    focusTrapUnencumberLicenseModal(event: KeyboardEvent): void {
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

    async submitUnencumberLicense(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const {
                currentCompactType: compactType,
                licenseeId,
                stateAbbrev,
                licenseTypeAbbrev
            } = this;
            const errorMessages: Array<string> = [];

            await Promise.all(this.selectedEncumbrances.map(async (adverseAction: AdverseAction) => {
                const adverseActionId = adverseAction.id;

                await this.$store.dispatch(`users/unencumberLicenseRequest`, {
                    compact: compactType,
                    licenseeId,
                    licenseState: stateAbbrev,
                    licenseType: licenseTypeAbbrev.toLowerCase(),
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
                this.isUnencumberLicenseModalSuccess = true;
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
        if (this.isDeactivateLicenseModalDisplayed) {
            this.formData.deactivateModalNotes.value = `Sample note`;
            this.validateAll({ asTouched: true });
        } else if (this.isEncumberLicenseModalDisplayed) {
            this.formData.encumberModalNpdbCategory.value = this.npdbCategoryOptions[1]?.value;
            this.formData.encumberModalStartDate.value = moment().format('YYYY-MM-DD');
            this.validateAll({ asTouched: true });
        } else if (this.isUnencumberLicenseModalDisplayed) {
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

export default toNative(LicenseCard);

// export default LicenseCard;
