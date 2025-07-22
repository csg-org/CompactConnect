//
//  SelectedStatePurchaseInformation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/12/2024.
//

import {
    Component,
    mixins,
    toNative,
    Prop
} from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import { displayDateFormat } from '@/app.config';
import CollapseCaretButton from '@components/CollapseCaretButton/CollapseCaretButton.vue';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { PrivilegeAttestation } from '@models/PrivilegeAttestation/PrivilegeAttestation.model';
import moment from 'moment';

@Component({
    name: 'SelectedStatePurchaseInformation',
    components: {
        InputCheckbox,
        InputButton,
        Modal,
        CollapseCaretButton,
        InputSubmit
    },
    emits: ['exOutState']
})
class SelectedStatePurchaseInformation extends mixins(MixinForm) {
    // PROPS
    @Prop({ required: true }) selectedStatePurchaseData?: PrivilegePurchaseOption;
    @Prop({ default: new FormInput({ value: false }) }) jurisprudenceCheckInput?: FormInput;
    @Prop({ default: new FormInput({ value: false }) }) scopeOfPracticeCheckInput?: FormInput;
    @Prop({ required: true }) scopeAttestation?: PrivilegeAttestation;
    @Prop({ required: true }) jurisprudenceAttestation?: PrivilegeAttestation;

    //
    // Lifecycle
    //
    async created() {
        this.initFormInputs();
    }

    //
    // Data
    //
    isJurisprudencePending = false;
    isScopeOfPracticePending = false;
    isPriceCollapsed = false;

    //
    // Computed
    //
    get selectedLicense(): License | null {
        return this.$store.getters['user/getLicenseSelected']();
    }

    get selectedLicenseTypeAbbrev(): string {
        return this.selectedLicense?.licenseTypeAbbreviation().toLowerCase() || '';
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get selectedLicenseExpirationDate(): string {
        let date = '';

        if (this.selectedLicense) {
            const { expireDate } = this.selectedLicense;

            if (expireDate) {
                date = moment(expireDate).format(displayDateFormat);
            }
        }

        return date;
    }

    get jurisprudenceInputRef(): HTMLElement | null {
        return document.getElementById((this.jurisprudenceCheckInput?.id || ''));
    }

    get scopeOfPracticeInputRef(): HTMLElement | null {
        return document.getElementById((this.scopeOfPracticeCheckInput?.id || ''));
    }

    get expirationDateText(): string {
        return this.$t('licensing.expirationDate');
    }

    get commissionFeeText(): string {
        return this.$t('licensing.adminFee');
    }

    get subtotalText(): string {
        return this.$t('common.subtotal');
    }

    get militaryDiscountText(): string {
        return this.$t('military.militaryDiscountText');
    }

    get jurisprudenceModalTitle(): string {
        return this.$t('licensing.jurisprudenceConfirmation');
    }

    get jurisprudenceModalContent(): string {
        return this.jurisprudenceAttestation?.textDisplay() || '';
    }

    get scopeModalContent(): string {
        return this.scopeAttestation?.textDisplay() || '';
    }

    get iUnderstandText(): string {
        return this.$t('licensing.iUnderstand');
    }

    get licenseTypeFees(): any {
        return this.selectedStatePurchaseData?.fees?.[this.selectedLicenseTypeAbbrev];
    }

    get basePurchasePrice(): number {
        return this.licenseTypeFees?.baseRate || 0;
    }

    get militaryPurchasePrice(): number {
        return this.licenseTypeFees?.militaryRate || 0;
    }

    get hasMilitaryRate(): boolean {
        return this.licenseTypeFees?.militaryRate || this.licenseTypeFees?.militaryRate === 0;
    }

    get baseFeeDisplay(): string {
        return this.basePurchasePrice.toFixed(2);
    }

    get militaryFeeDisplay(): string {
        return this.militaryPurchasePrice.toFixed(2) || '';
    }

    get feeDisplay(): string {
        return this.shouldUseMilitaryRate ? this.militaryFeeDisplay : this.baseFeeDisplay;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactCommissionFee(): number {
        return this.currentCompact?.fees?.compactCommissionFee || 0;
    }

    get currentCompactCommissionFeeDisplay(): string {
        return this.currentCompactCommissionFee.toFixed(2);
    }

    get shouldUseMilitaryRate(): boolean {
        return Boolean(this.hasMilitaryRate && this.licensee?.isMilitaryStatusActive());
    }

    get jurisdictionFeeText(): string {
        return this.shouldUseMilitaryRate ? this.$t('licensing.jurisdictionFeeMilitary') : this.$t('licensing.jurisdictionFee');
    }

    get subTotal(): string {
        const effectiveRate = this.shouldUseMilitaryRate
            ? this.militaryPurchasePrice
            : this.basePurchasePrice;

        const total = (
            (effectiveRate)
            + (this.currentCompactCommissionFee)
        );

        return total.toFixed(2);
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get isPhone(): boolean {
        return !this.$matches.tablet.min;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            submitJurisprudenceUnderstanding: new FormInput({
                id: 'submit-jurisprudence-understanding',
                isSubmitInput: true,
            }),
            submitScopeUnderstanding: new FormInput({
                id: 'submit-scope-understanding',
                isSubmitInput: true,
            }),
        });
    }

    handleJurisprudenceClicked(): void {
        const newValue = this.jurisprudenceCheckInput?.value;

        if (newValue) {
            if (this.jurisprudenceCheckInput) {
                this.isJurisprudencePending = true;
                this.setJurisprudenceInputValue(false);

                this.$nextTick(() => {
                    const buttonComponent = this.$refs.backButton as any;
                    const button = buttonComponent.$refs.button as HTMLElement;

                    button.focus();
                });
            }
        }
    }

    handleScopeOfPracticeClicked(): void {
        const newValue = this.scopeOfPracticeCheckInput?.value;

        if (newValue) {
            if (this.scopeOfPracticeCheckInput) {
                this.isScopeOfPracticePending = true;
                this.setScopeInputValue(false);

                this.$nextTick(() => {
                    const buttonComponent = this.$refs.backButton as any;
                    const button = buttonComponent.$refs.button as HTMLElement;

                    button.focus();
                });
            }
        }
    }

    deselectState(): void {
        const stateAbbrev = this.selectedStatePurchaseData?.jurisdiction?.abbrev;

        this.$emit('exOutState', stateAbbrev);
    }

    submitJurisprudenceUnderstanding(): void {
        const { isJurisprudencePending, jurisprudenceCheckInput } = this;

        if (isJurisprudencePending && jurisprudenceCheckInput) {
            this.setJurisprudenceInputValue(true);
            this.$store.dispatch('setModalIsOpen', false);
            this.jurisprudenceInputRef?.focus();
            this.isJurisprudencePending = false;
        }
    }

    submitScopeUnderstanding(): void {
        const { isScopeOfPracticePending, scopeOfPracticeCheckInput } = this;

        if (isScopeOfPracticePending && scopeOfPracticeCheckInput) {
            this.setScopeInputValue(true);
            this.$store.dispatch('setModalIsOpen', false);
            this.scopeOfPracticeInputRef?.focus();
            this.isScopeOfPracticePending = false;
        }
    }

    closeAndInvalidateJurisprudenceCheckbox(): void {
        const { isJurisprudencePending, jurisprudenceCheckInput } = this;

        if (isJurisprudencePending && jurisprudenceCheckInput) {
            this.setJurisprudenceInputValue(false);
            this.$store.dispatch('setModalIsOpen', false);
            this.jurisprudenceInputRef?.focus();
            this.isJurisprudencePending = false;
        }
    }

    closeAndInvalidateScopeCheckbox(): void {
        const { isScopeOfPracticePending, scopeOfPracticeCheckInput } = this;

        if (isScopeOfPracticePending && scopeOfPracticeCheckInput) {
            this.setScopeInputValue(false);
            this.$store.dispatch('setModalIsOpen', false);
            this.scopeOfPracticeInputRef?.focus();
            this.isScopeOfPracticePending = false;
        }
    }

    setJurisprudenceInputValue(newValue): void {
        if (this.jurisprudenceCheckInput) {
            (this.jurisprudenceCheckInput.value as any) = newValue; // any use required here because of outstanding ts bug regarding union type inference
            this.jurisprudenceCheckInput.validate();
        }
    }

    setScopeInputValue(newValue): void {
        if (this.scopeOfPracticeCheckInput) {
            (this.scopeOfPracticeCheckInput.value as any) = newValue; // any use required here because of outstanding ts bug regarding union type inference
            this.scopeOfPracticeCheckInput.validate();
        }
    }

    togglePriceCollapsed(): void {
        this.isPriceCollapsed = !this.isPriceCollapsed;
    }

    focusTrapJurisprudence(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('modal-back-button');
        const lastTabIndex = document.getElementById(this.formData.submitJurisprudenceUnderstanding.id);

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

    focusTrapScope(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('modal-back-button');
        const lastTabIndex = document.getElementById(this.formData.submitScopeUnderstanding.id);

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

export default toNative(SelectedStatePurchaseInformation);

// export default SelectedStatePurchaseInformation;
