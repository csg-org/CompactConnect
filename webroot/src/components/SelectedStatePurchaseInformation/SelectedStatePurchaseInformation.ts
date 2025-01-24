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
import { License, LicenseStatus } from '@/models/License/License.model';
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
    get activeLicense(): License | null {
        return this.licenseList?.find((license) => license.statusState === LicenseStatus.ACTIVE) || null;
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
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

    get activeLicenseExpirationDate(): string {
        let date = '';

        if (this.activeLicense) {
            const { expireDate } = this.activeLicense;

            if (expireDate) {
                date = moment(expireDate).format(displayDateFormat);
            }
        }

        return date;
    }

    get expirationDateText(): string {
        return this.$t('licensing.expirationDate');
    }

    get commissionFeeText(): string {
        return this.$t('licensing.commissionFee');
    }

    get jurisdictionFeeText(): string {
        return this.$t('licensing.jurisdictionFee');
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
        return this.jurisprudenceAttestation?.text || '';
    }

    get scopeModalContent(): string {
        return this.scopeAttestation?.text || '';
    }

    get scopeModalContentDisplay(): string {
        return '';
    }

    get iUnderstandText(): string {
        return this.$t('licensing.iUnderstand');
    }

    get feeDisplay(): string {
        return this.selectedStatePurchaseData?.fee?.toFixed(2) || '';
    }

    get militaryDiscountAmountDisplay(): string {
        return this.selectedStatePurchaseData?.militaryDiscountAmount?.toFixed(2) || '';
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactCommissionFee(): number | null {
        return this.currentCompact?.compactCommissionFee || null;
    }

    get currentCompactCommissionFeeDisplay(): string {
        return this.currentCompactCommissionFee?.toFixed(2) || '0.00';
    }

    get isMilitaryDiscountActive(): boolean {
        return this.selectedStatePurchaseData?.isMilitaryDiscountActive || false;
    }

    get shouldApplyMilitaryDiscount(): boolean {
        return Boolean(this.isMilitaryDiscountActive && this.licensee?.isMilitary());
    }

    get subTotal(): string {
        const militaryDiscount = this.shouldApplyMilitaryDiscount
            && this.selectedStatePurchaseData?.militaryDiscountAmount
            ? this.selectedStatePurchaseData?.militaryDiscountAmount : 0;

        const total = ((this.selectedStatePurchaseData?.fee || 0)
            + (this.currentCompactCommissionFee || 0)
            - (militaryDiscount || 0));

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
        const initFormData: any = {
            submitJurisprudenceUnderstanding: new FormInput({
                isSubmitInput: true,
                id: 'submit-jurisprudence-understanding',
            }),
            submitScopeUnderstanding: new FormInput({
                isSubmitInput: true,
                id: 'submit-scope-understanding',
            }),
        };

        this.formData = reactive(initFormData);
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
            this.isJurisprudencePending = false;
        }
    }

    submitScopeUnderstanding(): void {
        const { isScopeOfPracticePending, scopeOfPracticeCheckInput } = this;

        if (isScopeOfPracticePending && scopeOfPracticeCheckInput) {
            this.setScopeInputValue(true);
            this.$store.dispatch('setModalIsOpen', false);
            this.isScopeOfPracticePending = false;
        }
    }

    closeAndInvalidateJurisprudenceCheckbox(): void {
        const { isJurisprudencePending, jurisprudenceCheckInput } = this;

        if (isJurisprudencePending && jurisprudenceCheckInput) {
            this.setJurisprudenceInputValue(false);
            this.$store.dispatch('setModalIsOpen', false);
            this.isJurisprudencePending = false;
        }
    }

    closeAndInvalidateScopeCheckbox(): void {
        const { isScopeOfPracticePending, scopeOfPracticeCheckInput } = this;

        if (isScopeOfPracticePending && scopeOfPracticeCheckInput) {
            this.setScopeInputValue(false);
            this.$store.dispatch('setModalIsOpen', false);
            this.isScopeOfPracticePending = false;
        }
    }

    setJurisprudenceInputValue(newValue): void {
        if (this.jurisprudenceCheckInput) {
            (this.jurisprudenceCheckInput.value as any) = newValue; // any use required here because of outstanding ts bug regarding union type inference
        }
    }

    setScopeInputValue(newValue): void {
        if (this.scopeOfPracticeCheckInput) {
            (this.scopeOfPracticeCheckInput.value as any) = newValue; // any use required here because of outstanding ts bug regarding union type inference
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
