//
//  SelectedStatePurchaseInformation.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/12/2024.
//

import {
    Component,
    Vue,
    toNative,
    Prop
} from 'vue-facing-decorator';
import { displayDateFormat } from '@/app.config';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
// import { State } from '@/models/State/State.model';
import moment from 'moment';

@Component({
    name: 'SelectedStatePurchaseInformation',
    components: {
        InputCheckbox,
        InputButton,
        Modal
    },
    emits: ['exOutState']
})
class SelectedStatePurchaseInformation extends Vue {
    // PROPS
    @Prop({ required: true }) selectedStatePurchaseData?: PrivilegePurchaseOption;
    @Prop({ default: new FormInput({ value: false }) }) jurisprudenceCheckInput?: FormInput | any;

    //
    // Data
    //
    isJurisprudencePending = false;

    //
    // Lifecycle
    //

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
        return this.$t('licensing.militaryDiscountText');
    }

    get jurisprudenceExplanationText(): string {
        return this.$t('licensing.jurisprudenceExplanationText');
    }

    get jurisprudenceModalTitle(): string {
        return this.$t('licensing.jurisprudenceConfirmation');
    }

    get jurisprudenceModalContent(): string {
        return this.$t('licensing.jurisprudenceUnderstandParagraph');
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

    get subTotal(): string {
        const militaryDiscount = this.isMilitaryDiscountActive
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

    //
    // Methods
    //
    handleJurisprudenceClicked() {
        const newValue = this.jurisprudenceCheckInput?.value;

        if (newValue === true) {
            if (this.jurisprudenceCheckInput) {
                this.isJurisprudencePending = true;
                this.jurisprudenceCheckInput.value = false;
            }
        }
    }

    deselectState() {
        const stateAbbrev = this.selectedStatePurchaseData?.jurisdiction?.abbrev;

        this.$emit('exOutState', stateAbbrev);
    }

    submitUnderstanding() {
        const { isJurisprudencePending, jurisprudenceCheckInput } = this;

        if (isJurisprudencePending && jurisprudenceCheckInput) {
            jurisprudenceCheckInput.value = true;
            this.$store.dispatch('setModalIsOpen', false);
            this.isJurisprudencePending = false;
        }
    }

    closeAndInvalidateCheckbox() {
        const { isJurisprudencePending, jurisprudenceCheckInput } = this;

        if (isJurisprudencePending && jurisprudenceCheckInput) {
            jurisprudenceCheckInput.value = false;
            this.$store.dispatch('setModalIsOpen', false);
            this.isJurisprudencePending = false;
        }
    }
}

export default toNative(SelectedStatePurchaseInformation);

// export default SelectedStatePurchaseInformation;
