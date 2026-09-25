//
//  LicenseActionsModal.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/23/2026.
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
import { dateFormatPatterns } from '@/app.config';
import { getEncumberConfigLicense, getEncumberConfigPrivilege } from '@utils/compactConfig';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputTextarea from '@components/Forms/InputTextarea/InputTextarea.vue';
import InputDate from '@components/Forms/InputDate/InputDate.vue';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import InputSelectMultiple from '@components/Forms/InputSelectMultiple/InputSelectMultiple.vue';
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
import { Investigation } from '@/models/Investigation/Investigation.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import Joi from 'joi';
import moment from 'moment';

let licenseActionsModalInstanceCount = 0;

@Component({
    name: 'LicenseActionsModal',
    components: {
        MockPopulate,
        InputTextarea,
        InputDate,
        InputSelect,
        InputSelectMultiple,
        InputCheckbox,
        InputButton,
        InputSubmit,
        Modal,
        CheckCircleIcon,
    }
})
class LicenseActionsModal extends mixins(MixinForm) {
    @Prop({ required: true }) license!: License;
    @Prop({ required: true }) licensee!: Licensee;
    @Prop({ default: 'license' }) type?: 'license' | 'privilege';

    //
    // Data
    //
    instanceId = 0;
    isLicenseActionMenuDisplayed = false;
    isDeactivateLicenseModalDisplayed = false;
    isEncumberLicenseModalDisplayed = false;
    isEncumberLicenseModalSuccess = false;
    isUnencumberLicenseModalDisplayed = false;
    isUnencumberLicenseModalSuccess = false;
    isAddInvestigationModalDisplayed = false;
    isAddInvestigationModalSuccess = false;
    isEndInvestigationModalDisplayed = false;
    isEndInvestigationModalConfirm = false;
    isEndInvestigationModalSuccess = false;
    encumbranceInputs: Array<FormInput> = [];
    selectedEncumbrances: Array<AdverseAction> = [];
    investigationInputs: Array<FormInput> = [];
    selectedInvestigation: Investigation | null = null;
    modalErrorMessage = '';

    //
    // Lifecycle
    //
    created(): void {
        licenseActionsModalInstanceCount += 1;
        this.instanceId = licenseActionsModalInstanceCount;
    }

    //
    // Computed
    //
    get isPrivilege(): boolean {
        return this.type === 'privilege';
    }

    get i18nNoun(): 'License' | 'Privilege' {
        return this.isPrivilege ? 'Privilege' : 'License';
    }

    get storeNoun(): 'License' | 'Privilege' {
        return this.i18nNoun;
    }

    get idPrefix(): string {
        const raw = this.license?.id || `license-actions-${this.instanceId}`;

        return String(raw).replace(/\s+/g, '-');
    }

    get ids(): Record<string, string> {
        const { idPrefix } = this;

        return {
            notes: `notes-${idPrefix}`,
            submit: `submit-modal-continue-${idPrefix}`,
            disciplineAction: `discipline-action-${idPrefix}`,
            npdbCategories: `npdb-categories-${idPrefix}`,
            encumberStart: `encumber-start-${idPrefix}`,
            deactivateCancel: `deactivate-modal-cancel-button-${idPrefix}`,
            encumberCancel: `encumber-modal-cancel-button-${idPrefix}`,
            unencumberCancel: `unencumber-modal-cancel-button-${idPrefix}`,
            addInvestigationCancel: `add-investigation-modal-cancel-button-${idPrefix}`,
            endInvestigationCancel: `end-investigation-modal-cancel-button-${idPrefix}`,
            endInvestigationNoEncumbrance: `end-investigation-modal-no-encumbrance-${idPrefix}`,
        };
    }

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

    get shouldShowMenu(): boolean {
        return (this.isPrivilege)
            ? this.isCurrentUserLicenseAdmin
            : this.isCurrentUserLicenseStateAdmin;
    }

    get shouldShowDeactivateMenuItem(): boolean {
        return this.isPrivilege && this.isCurrentUserCompactAdmin;
    }

    get shouldShowDisciplineMenuItems(): boolean {
        return this.isCurrentUserLicenseStateAdmin;
    }

    get licenseeId(): string {
        return this.license?.licenseeId || '';
    }

    get licenseeName(): string {
        return this.licensee?.nameDisplay() || '';
    }

    get licenseNumber(): string {
        return this.license?.licenseNumber || '';
    }

    get privilegeId(): string {
        return this.license?.privilegeId || '';
    }

    get licenseTypeAbbrev(): string {
        return this.license?.licenseTypeAbbreviation() || '';
    }

    get licenseScope(): string {
        return this.license?.licenseScope || '';
    }

    get isActive(): boolean {
        return this.license?.status === LicenseStatus.ACTIVE;
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

    get isEncumbered(): boolean {
        return this.license?.isEncumbered() || false;
    }

    get isUnderInvestigation(): boolean {
        return this.license?.isUnderInvestigation() || false;
    }

    get adverseActions(): Array<AdverseAction> {
        return this.license?.adverseActions || [];
    }

    get investigations(): Array<Investigation> {
        return this.license?.investigations || [];
    }

    get encumberConfig() {
        return (this.isPrivilege)
            ? getEncumberConfigPrivilege(this.$appMode)
            : getEncumberConfigLicense(this.$appMode);
    }

    get encumberDisciplineOptions(): Array<{ value: string, name: string | ComputedRef<string> }> {
        const includeList: Array<string> = this.encumberConfig.disciplineTypes;
        const options = this.$tm('licensing.disciplineTypes').map((disciplineType) => ({
            value: disciplineType.key,
            name: disciplineType.name,
        })).filter((option) => includeList.includes(option.value) || option.value === '');

        options.unshift({
            value: '',
            name: computed(() => this.$t('common.selectOption')),
        });

        return options;
    }

    get npdbCategoryOptions(): Array<{ value: string, name: string | ComputedRef<string> }> {
        const includeList: Array<string> = this.encumberConfig.npdbTypes;
        const options = this.$tm('licensing.npdbTypes').map((npdbType) => ({
            value: npdbType.key,
            name: npdbType.name,
        })).filter((option) => includeList.includes(option.value) || option.value === '');

        if (!this.shouldAllowNpdbMultiSelect) {
            options.unshift({ value: '', name: computed(() => this.$t('common.selectOption')) });
        }

        return options;
    }

    get shouldAllowNpdbMultiSelect(): boolean {
        return !this.$isAppModeCosmetology;
    }

    get endInvestigationModalTitle(): string {
        let modalTitle = this.$t(`licensing.confirm${this.i18nNoun}InvestigationEndSelectTitle`);

        if (this.isEndInvestigationModalSuccess) {
            modalTitle = ' ';
        } else if (this.isEndInvestigationModalConfirm) {
            modalTitle = this.$t(`licensing.confirm${this.i18nNoun}InvestigationEndTitle`);
        }

        return modalTitle;
    }

    get isUnencumberSubmitEnabled(): boolean {
        return Boolean(this.isFormValid && !this.isFormLoading && this.selectedEncumbrances.length);
    }

    get isEndInvestigationSubmitEnabled(): boolean {
        return Boolean(this.isFormValid && !this.isFormLoading && this.selectedInvestigation);
    }

    get isMockPopulateEnabled(): boolean {
        return Boolean(this.$envConfig.isDevelopment);
    }

    get menuAriaLabel(): string {
        return this.$t(`licensing.${this.isPrivilege ? 'privilegeActions' : 'licenseActions'}`);
    }

    get baseRequestPayload(): Record<string, unknown> {
        const payload: Record<string, unknown> = {
            compact: this.currentCompactType,
            licenseeId: this.licenseeId,
            licenseType: this.licenseTypeAbbrev.toLowerCase(),
        };

        if (this.isPrivilege) {
            payload.privilegeState = this.stateAbbrev;
        } else {
            payload.licenseState = this.stateAbbrev;
            payload.licenseScope = this.licenseScope;
        }

        return payload;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        if (this.isDeactivateLicenseModalDisplayed) {
            this.initFormInputsDeactivateLicense();
        } else if (this.isEncumberLicenseModalDisplayed) {
            this.initFormInputsEncumberLicense();
        } else if (this.isUnencumberLicenseModalDisplayed) {
            this.initFormInputsUnencumberLicense();
        } else if (this.isAddInvestigationModalDisplayed) {
            this.initFormInputsAddInvestigation();
        } else if (this.isEndInvestigationModalDisplayed) {
            this.initFormInputsEndInvestigation();
        }
    }

    initFormInputsDeactivateLicense(): void {
        this.formData = reactive({
            deactivateModalNotes: new FormInput({
                id: this.ids.notes,
                name: 'notes',
                label: computed(() => this.$t('licensing.deactivateNotesTitle')),
                placeholder: computed(() => this.$t('licensing.deactivateNotesPlaceholder')),
                validation: Joi.string().required().max(256).messages(this.joiMessages.string),
                enforceMax: true,
            }),
            deactivateModalContinue: new FormInput({
                isSubmitInput: true,
                id: this.ids.submit,
            }),
        });
        this.watchFormInputs();
    }

    initFormInputsEncumberLicense(): void {
        this.formData = reactive({
            encumberModalDisciplineAction: new FormInput({
                id: this.ids.disciplineAction,
                name: 'discipline-action',
                label: computed(() => this.$t('licensing.encumberAction')),
                validation: Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.encumberDisciplineOptions,
            }),
            encumberModalNpdbCategories: new FormInput({
                id: this.ids.npdbCategories,
                name: 'npdb-categories',
                label: (this.shouldAllowNpdbMultiSelect)
                    ? computed(() => this.$t('licensing.npdbCategoryLabel'))
                    : computed(() => this.$t('licensing.encumberBasisLabel')),
                validation: (this.shouldAllowNpdbMultiSelect)
                    ? Joi.array().min(1).messages(this.joiMessages.array)
                    : Joi.string().required().messages(this.joiMessages.string),
                valueOptions: this.npdbCategoryOptions,
                value: (this.shouldAllowNpdbMultiSelect)
                    ? []
                    : '',
            }),
            encumberModalStartDate: new FormInput({
                id: this.ids.encumberStart,
                name: 'encumber-start',
                label: computed(() => this.$t('licensing.encumberStartDate')),
                placeholder: computed(() => 'MM/DD/YYYY'),
                validation: Joi.string()
                    .required()
                    .pattern(dateFormatPatterns.MM_DD_YYYY)
                    .messages(this.joiMessages.dateWithFormat('MM/DD/YYYY')),
            }),
            encumberModalContinue: new FormInput({
                isSubmitInput: true,
                id: this.ids.submit,
            }),
        });
        this.watchFormInputs();
    }

    initFormInputsUnencumberLicense(): void {
        this.formData = reactive({
            unencumberModalContinue: new FormInput({
                isSubmitInput: true,
                id: this.ids.submit,
            }),
        });

        this.adverseActions.forEach((adverseAction: AdverseAction) => {
            const adverseActionId = adverseAction.id;
            const adverseActionInput = new FormInput({
                id: `adverse-action-data-${adverseActionId}`,
                name: `adverse-action-data-${adverseActionId}`,
                label: adverseAction.encumbranceTypeName(),
                isDisabled: Boolean(adverseAction.endDate),
            });

            this.formData[`adverse-action-data-${adverseActionId}`] = adverseActionInput;
            this.encumbranceInputs.push(adverseActionInput);
        });
    }

    initFormInputsAddInvestigation(): void {
        this.formData = reactive({
            addInvestigationModalContinue: new FormInput({
                isSubmitInput: true,
                id: this.ids.submit,
            }),
        });
        this.watchFormInputs();
    }

    initFormInputsEndInvestigation(): void {
        this.formData = reactive({
            endInvestigationModalContinue: new FormInput({
                isSubmitInput: true,
                id: this.ids.submit,
            }),
        });

        this.investigations.forEach((investigation: Investigation) => {
            const investigationId = investigation.id;
            const investigationInput = new FormInput({
                id: `end-investigation-data-${investigationId}`,
                name: `end-investigation-data-${investigationId}`,
                label: this.$t('licensing.investigationStartedOn', { date: investigation.startDateDisplay() }),
                isDisabled: Boolean(investigation.endDate),
            });

            this.formData[`end-investigation-data-${investigationId}`] = investigationInput;
            this.investigationInputs.push(investigationInput);
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

    // =======================================================
    //                      DEACTIVATE
    // =======================================================
    async toggleDeactivateLicenseModal(): Promise<void> {
        this.closeLicenseActionMenu();

        if (this.isActive) {
            this.resetForm();
            this.isDeactivateLicenseModalDisplayed = !this.isDeactivateLicenseModalDisplayed;

            if (this.isDeactivateLicenseModalDisplayed) {
                this.initFormInputs();
            }
        }
    }

    closeDeactivateLicenseModal(event?: Event): void {
        event?.preventDefault();
        this.isDeactivateLicenseModalDisplayed = false;
    }

    focusTrapDeactivateLicenseModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById(this.ids.notes);
        const lastTabIndex = (this.isFormValid && !this.isFormLoading)
            ? document.getElementById(this.formData.deactivateModalContinue.id)
            : document.getElementById(this.ids.deactivateCancel);

        if (event.shiftKey) {
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitDeactivateLicense(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { currentCompactType: compactType, licenseeId } = this;

            await this.$store.dispatch('users/deletePrivilegeRequest', {
                ...this.baseRequestPayload,
                notes: this.formData.deactivateModalNotes.value,
            }).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.closeDeactivateLicenseModal();
            }

            this.endFormLoading();
        }
    }

    // =======================================================
    //                       ENCUMBER
    // =======================================================
    openEncumberFromMenu(): void {
        this.closeLicenseActionMenu();
        this.selectedInvestigation = null;
        this.openEncumberModal();
    }

    async openEncumberModal(): Promise<void> {
        this.resetForm();
        this.isEncumberLicenseModalDisplayed = true;
        this.initFormInputs();
    }

    closeEncumberLicenseModal(event?: Event): void {
        event?.preventDefault();
        this.isEncumberLicenseModalDisplayed = false;
        this.isEncumberLicenseModalSuccess = false;
        this.selectedInvestigation = null;
    }

    focusTrapEncumberLicenseModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById(this.ids.disciplineAction)
            || document.getElementById(this.ids.encumberCancel);
        const lastTabIndex = (this.isFormValid && !this.isFormLoading && !this.isEncumberLicenseModalSuccess)
            ? document.getElementById(this.formData.encumberModalContinue.id)
            : document.getElementById(this.ids.encumberCancel);

        if (event.shiftKey) {
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitEncumberLicense(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { currentCompactType: compactType, licenseeId, formData } = this;
            const encumbrance = {
                encumbranceType: formData.encumberModalDisciplineAction.value,
                npdbCategories: (Array.isArray(formData.encumberModalNpdbCategories.value))
                    ? formData.encumberModalNpdbCategories.value
                    : [formData.encumberModalNpdbCategories.value],
                startDate: formData.encumberModalStartDate.value,
            };

            if (this.selectedInvestigation) {
                const investigationId = this.selectedInvestigation?.id;
                const investigationPayload: Record<string, unknown> = {
                    ...this.baseRequestPayload,
                    investigationId,
                    encumbrance: (this.isPrivilege)
                        ? encumbrance
                        : { ...encumbrance, licenseScope: this.licenseScope },
                };

                await this.$store.dispatch(`users/updateInvestigation${this.storeNoun}Request`, investigationPayload)
                    .catch((err) => {
                        this.modalErrorMessage = err?.message || this.$t('common.error');
                        this.isFormError = true;
                    });
            } else {
                await this.$store.dispatch(`users/encumber${this.storeNoun}Request`, {
                    ...this.baseRequestPayload,
                    ...encumbrance,
                }).catch((err) => {
                    this.modalErrorMessage = err?.message || this.$t('common.error');
                    this.isFormError = true;
                });
            }

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.isEncumberLicenseModalSuccess = true;
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
                label: computed(() => this.$t(`licensing.confirm${this.i18nNoun}UnencumberEndDate`)),
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

    getFirstEnabledUnencumberFormInputId(): string {
        const { formData } = this;
        const firstEnabledFormInput: string = Object.keys(formData)
            .filter((key) => key !== 'unencumberModalContinue')
            .find((key) => !formData[key].isDisabled) || '';
        const firstEnabledInputId = formData[firstEnabledFormInput]?.id || this.ids.unencumberCancel;

        return firstEnabledInputId;
    }

    async openUnencumberLicenseModal(): Promise<void> {
        this.closeLicenseActionMenu();
        this.resetForm();
        this.isUnencumberLicenseModalDisplayed = true;
        this.initFormInputs();
    }

    closeUnencumberLicenseModal(event?: Event): void {
        event?.preventDefault();
        this.selectedEncumbrances = [];
        this.isUnencumberLicenseModalDisplayed = false;
        this.isUnencumberLicenseModalSuccess = false;
    }

    focusTrapUnencumberLicenseModal(event: KeyboardEvent): void {
        const { isUnencumberSubmitEnabled } = this;
        const firstEnabledInputId = this.getFirstEnabledUnencumberFormInputId();
        const firstTabIndex = document.getElementById(firstEnabledInputId);
        const lastTabIndex = (isUnencumberSubmitEnabled)
            ? document.getElementById(this.ids.submit)
            : document.getElementById(this.ids.unencumberCancel);

        if (event.shiftKey) {
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitUnencumberLicense(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { currentCompactType: compactType, licenseeId } = this;
            const errorMessages: Array<string> = [];

            await Promise.all(this.selectedEncumbrances.map(async (adverseAction: AdverseAction) => {
                const adverseActionId = adverseAction.id;

                await this.$store.dispatch(`users/unencumber${this.storeNoun}Request`, {
                    ...this.baseRequestPayload,
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
            }

            this.endFormLoading();
        }
    }

    // =======================================================
    //                    ADD INVESTIGATION
    // =======================================================
    async openAddInvestigationModal(): Promise<void> {
        this.closeLicenseActionMenu();
        this.resetForm();
        this.isAddInvestigationModalDisplayed = true;
        this.initFormInputs();
    }

    closeAddInvestigationModal(event?: Event): void {
        event?.preventDefault();
        this.isAddInvestigationModalDisplayed = false;
        this.isAddInvestigationModalSuccess = false;
    }

    focusTrapAddInvestigationModal(event: KeyboardEvent): void {
        const { isAddInvestigationModalSuccess } = this;
        const firstTabIndex = (isAddInvestigationModalSuccess)
            ? document.getElementById(this.ids.submit)
            : document.getElementById(this.ids.addInvestigationCancel);
        let lastTabIndex = document.getElementById(this.ids.submit);

        if (!this.isAddInvestigationModalSuccess && (!this.isFormValid || this.isFormLoading)) {
            lastTabIndex = document.getElementById(this.ids.addInvestigationCancel);
        }

        if (event.shiftKey) {
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitAddInvestigation(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { currentCompactType: compactType, licenseeId } = this;

            await this.$store.dispatch(`users/createInvestigation${this.storeNoun}Request`, this.baseRequestPayload)
                .catch((err) => {
                    this.modalErrorMessage = err?.message || this.$t('common.error');
                    this.isFormError = true;
                });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.isAddInvestigationModalSuccess = true;
            }

            this.endFormLoading();
        }
    }

    // =======================================================
    //                    END INVESTIGATION
    // =======================================================
    clickEndInvestigationItem(investigation: Investigation, event?: PointerEvent | KeyboardEvent): void {
        const { srcElement, type } = event || {};
        const investigationId = investigation?.id;
        const nodeType = (srcElement as Element)?.nodeName;

        if (nodeType === 'INPUT') {
            if (type === 'keyup') {
                event?.preventDefault();
            }
            event?.stopPropagation();
        } else if (nodeType === 'LABEL') {
            event?.preventDefault();
        }

        if (investigationId) {
            const formInput = this.formData[`end-investigation-data-${investigationId}`];
            const existingValue = Boolean(formInput?.value);

            if (formInput) {
                formInput.value = !existingValue;

                if (formInput.value) {
                    this.addEndInvestigationFormData(investigation);
                } else {
                    this.removeEndInvestigationFormData();
                }
            }
        }
    }

    async addEndInvestigationFormData(investigation: Investigation): Promise<void> {
        if (investigation) {
            this.selectedInvestigation = investigation;
            this.investigationInputs.forEach((input: FormInput) => {
                if (input.id !== `end-investigation-data-${investigation.id}`) {
                    input.value = '';
                }
            });

            this.watchFormInputs();
            this.validateAll();
        }
    }

    removeEndInvestigationFormData(): void {
        this.selectedInvestigation = null;
        this.watchFormInputs();
        this.validateAll();
    }

    getFirstEnabledEndInvestigationFormInputId(): string {
        const { formData } = this;
        const firstEnabledFormInput: string = Object.keys(formData)
            .filter((key) => key !== 'endInvestigationModalContinue')
            .find((key) => !formData[key].isDisabled) || '';
        const firstEnabledInputId = formData[firstEnabledFormInput]?.id || this.ids.endInvestigationCancel;

        return firstEnabledInputId;
    }

    async openEndInvestigationModal(): Promise<void> {
        this.closeLicenseActionMenu();
        this.resetForm();
        this.isEndInvestigationModalDisplayed = true;
        this.initFormInputs();
    }

    closeEndInvestigationModal(event?: Event, keepSelectedInvestigation = false): void {
        event?.preventDefault();

        if (!keepSelectedInvestigation) {
            this.selectedInvestigation = null;
        }

        this.isEndInvestigationModalDisplayed = false;
        this.isEndInvestigationModalConfirm = false;
        this.isEndInvestigationModalSuccess = false;
    }

    focusTrapEndInvestigationModal(event: KeyboardEvent): void {
        const {
            isEndInvestigationModalConfirm,
            isEndInvestigationModalSuccess,
            isEndInvestigationSubmitEnabled
        } = this;
        const firstEnabledInputId = (isEndInvestigationModalConfirm || isEndInvestigationModalSuccess)
            ? this.ids.endInvestigationCancel
            : this.getFirstEnabledEndInvestigationFormInputId();
        const firstTabIndex = document.getElementById(firstEnabledInputId);
        const lastTabIndex = (isEndInvestigationSubmitEnabled && !isEndInvestigationModalSuccess)
            ? document.getElementById(this.ids.submit)
            : document.getElementById(this.ids.endInvestigationCancel);

        if (event.shiftKey) {
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    continueToEndInvestigationConfirm(): void {
        this.isEndInvestigationModalConfirm = true;
    }

    submitEndInvestigationWithEncumbrance(): void {
        this.closeEndInvestigationModal(undefined, true);
        this.openEncumberModal();
    }

    async submitEndInvestigationWithoutEncumbrance(): Promise<void> {
        this.validateAll({ asTouched: true });

        if (this.isFormValid) {
            this.startFormLoading();
            this.modalErrorMessage = '';

            const { currentCompactType: compactType, licenseeId } = this;
            const investigationId = this.selectedInvestigation?.id;

            await this.$store.dispatch(`users/updateInvestigation${this.storeNoun}Request`, {
                ...this.baseRequestPayload,
                investigationId,
            }).catch((err) => {
                this.modalErrorMessage = err?.message || this.$t('common.error');
                this.isFormError = true;
            });

            if (!this.isFormError) {
                this.isFormSuccessful = true;
                await this.$store.dispatch('license/getLicenseeRequest', { compact: compactType, licenseeId });
                this.isEndInvestigationModalConfirm = false;
                this.isEndInvestigationModalSuccess = true;
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

    isInvestigationSelected(investigation: Investigation): boolean {
        return this.selectedInvestigation?.id === investigation.id;
    }

    dateDisplayFormat(unformattedDate: string): string {
        return dateDisplay(unformattedDate);
    }

    async mockPopulate(): Promise<void> {
        if (this.isDeactivateLicenseModalDisplayed) {
            this.formData.deactivateModalNotes.value = `Sample note`;
            await nextTick();
            this.validateAll({ asTouched: true });
        } else if (this.isEncumberLicenseModalDisplayed) {
            this.formData.encumberModalDisciplineAction.value = this.encumberDisciplineOptions[1]?.value;
            this.formData.encumberModalNpdbCategories.value = (this.shouldAllowNpdbMultiSelect)
                ? [this.npdbCategoryOptions[1]?.value]
                : this.npdbCategoryOptions[1]?.value;
            this.formData.encumberModalStartDate.value = moment().format('YYYY-MM-DD');
            await nextTick();
            this.validateAll({ asTouched: true });
        } else if (this.isUnencumberLicenseModalDisplayed) {
            this.selectedEncumbrances.forEach((selected) => {
                this.clickUnencumberItem(selected);
            });
            await Promise.all(this.adverseActions
                .filter((adverseAction) => !adverseAction.hasEndDate())
                .map(async (adverseAction) => {
                    this.clickUnencumberItem(adverseAction);
                    await nextTick();
                    this.formData[`adverse-action-end-date-${adverseAction.id}`].value = moment().format('YYYY-MM-DD');
                }));
            await nextTick();
            this.validateAll({ asTouched: true });
        } else if (this.isEndInvestigationModalDisplayed) {
            await Promise.all(this.investigations
                .filter((investigation) => !investigation.hasEndDate())
                .map(async (investigation) => {
                    this.clickEndInvestigationItem(investigation);
                    await nextTick();
                }));
            await nextTick();
            this.validateAll({ asTouched: true });
        }
    }
}

export default toNative(LicenseActionsModal);
