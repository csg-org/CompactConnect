//
//  SelectPrivileges.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { Component, Watch, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import { displayDateFormat } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import Modal from '@components/Modal/Modal.vue';
import SelectedStatePurchaseInformation from '@components/SelectedStatePurchaseInformation/SelectedStatePurchaseInformation.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License, LicenseStatus } from '@/models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@/models/State/State.model';
import moment from 'moment';

@Component({
    name: 'SelectPrivileges',
    components: {
        InputCheckbox,
        InputSubmit,
        InputButton,
        Modal,
        SelectedStatePurchaseInformation
    }
})
export default class SelectPrivileges extends mixins(MixinForm) {
    //
    // Data
    //
    jurisprudencePendingConfirmation = '';

    //
    // Lifecycle
    //
    async created() {
        await this.$store.dispatch('user/getPrivilegePurchaseInformationRequest');

        if (this.alreadyObtainedPrivilegeStates?.length) {
            this.initFormInputs();
        }
    }

    //
    // Computed
    //
    get purchaseDataList(): Array<PrivilegePurchaseOption> {
        return this.currentCompact?.privilegePurchaseOptions || [];
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

    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser | null {
        return this.userStore.model;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get userFullName(): string {
        let name = '';

        if (this.user) {
            name = this.user.getFullName();
        }

        return name;
    }

    get isPhone() {
        return this.$matches.phone.only;
    }

    get privilegeList(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get alreadyObtainedPrivilegeStates(): Array<string> {
        const licenseList = this.licenseList.concat(this.privilegeList);
        const stateList: Array<string> = [];

        licenseList.forEach((license) => {
            if (license?.issueState?.abbrev) {
                stateList.push(license?.issueState?.abbrev);
            }
        });

        return stateList;
    }

    get disabledPrivilegeStateChoices(): Array<string> {
        const licenseList = this.licenseList.concat(this.privilegeList);

        const stateList: Array<string> = [];

        licenseList.forEach((license) => {
            if (
                license?.issueState?.abbrev
                && license?.expireDate === this.activeLicense?.expireDate
                && license.statusState === LicenseStatus.ACTIVE
            ) {
                stateList.push(license?.issueState?.abbrev);
            }
        });

        return stateList;
    }

    get backText(): string {
        return this.$t('common.back');
    }

    get cancelText(): string {
        return this.$t('common.cancel');
    }

    get stateCheckList(): Array<FormInput> {
        return this.formData.stateCheckList;
    }

    get isAtLeastOnePrivilegeChosen(): boolean {
        return this.formData.stateCheckList?.filter((formInput) =>
            (formInput.value === true)).length > 0;
    }

    get submitLabel(): string {
        let label = this.$t('common.next');

        if (this.isFormLoading) {
            label = this.$t('common.loading');
        }

        return label;
    }

    get isDesktop(): boolean {
        return this.$matches.desktop.min;
    }

    get isMobile(): boolean {
        return !this.isDesktop;
    }

    get statesSelected(): Array <string> {
        return this.formData.stateCheckList?.filter((formInput) =>
            (formInput.value === true)).map((input) => input.id);
    }

    get selectedStatePurchaseDataList(): Array<PrivilegePurchaseOption> {
        return this.purchaseDataList.filter((option) => {
            let includes = false;

            const stateAbbrev = option?.jurisdiction?.abbrev;

            if (stateAbbrev) {
                includes = this.statesSelected?.includes(stateAbbrev);
            }

            return includes;
        });
    }

    // get selectedStatePurchaseDataDisplayList(): Array<object> {
    //     return this.selectedStatePurchaseDataList.map((option) => {
    //         let feeDisplay = '';
    //         let militaryDiscountAmountDisplay = '';

    //         if (option?.fee) {
    //             feeDisplay = option?.fee?.toFixed(2);
    //         }

    //         if (option?.militaryDiscountAmount) {
    //             militaryDiscountAmountDisplay = option?.militaryDiscountAmount?.toFixed(2);
    //         }

    //         return {
    //             ...option,
    //             feeDisplay,
    //             militaryDiscountAmountDisplay
    //         };
    //     });
    // }

    get selectedStatesWithJurisprudenceRequired(): Array<string> {
        const selectedStatesWithJurisprudenceRequired: Array<string> = [];
        const privPurchaseStatesRequiringJurisprudence = this.selectedStatePurchaseDataList
            .filter((state) => state.isJurisprudenceRequired);

        privPurchaseStatesRequiringJurisprudence.forEach((state) => {
            if (state?.jurisdiction?.abbrev) {
                selectedStatesWithJurisprudenceRequired.push(state.jurisdiction.abbrev);
            }
        });

        return selectedStatesWithJurisprudenceRequired;
    }

    // get expirationDateText(): string {
    //     return this.$t('licensing.expirationDate');
    // }

    // get jurisdictionFeeText(): string {
    //     return this.$t('licensing.jurisdictionFee');
    // }

    // get commissionFeeText(): string {
    //     return this.$t('licensing.commissionFee');
    // }

    // get subtotalText(): string {
    //     return this.$t('common.subtotal');
    // }

    get jurisprudenceExplanationText(): string {
        return this.$t('licensing.jurisprudenceExplanationText');
    }

    // get militaryDiscountText(): string {
    //     return this.$t('licensing.militaryDiscountText');
    // }

    get jurisprudenceModalTitle(): string {
        return this.$t('licensing.jurisprudenceConfirmation');
    }

    get jurisprudenceModalContent(): string {
        return this.$t('licensing.jurisprudenceUnderstandParagraph');
    }

    get iUnderstandText(): string {
        return this.$t('licensing.iUnderstand');
    }

    get activeLicense(): License | null {
        return this.licenseList?.find((license) => license.statusState === LicenseStatus.ACTIVE) || null;
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

    get subTotalListDisplay(): Array<string> {
        return this.selectedStatePurchaseDataList?.map((purchaseInfo) => {
            const militaryDiscount = purchaseInfo.isMilitaryDiscountActive && purchaseInfo.militaryDiscountAmount
                ? purchaseInfo.militaryDiscountAmount : 0;

            const total = ((purchaseInfo?.fee || 0) + (this.currentCompactCommissionFee || 0) - (militaryDiscount));

            return total.toFixed(2);
        });
    }

    get selectPrivilegesTitleText(): string {
        return this.$t('licensing.selectPrivileges');
    }

    get shouldShowJurisprudenceModal(): boolean {
        return !!this.jurisprudencePendingConfirmation;
    }

    get areAllJurisprudenceConfirmed(): boolean {
        let allConfirmed = true;

        if (this.formData?.jurisprudenceConfirmations) {
            const jurisprudenceConfirmations = Object.keys(this.formData.jurisprudenceConfirmations);

            jurisprudenceConfirmations.forEach((state) => {
                if (!this.formData.jurisprudenceConfirmations[state].value) {
                    allConfirmed = false;
                }
            });
        }

        return allConfirmed;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            stateCheckList: [],
            jurisprudenceConfirmations: {},
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        };

        this.purchaseDataList?.forEach((purchaseOption) => {
            const { jurisdiction = new State() } = purchaseOption;

            if (jurisdiction) {
                const { abbrev } = jurisdiction;

                if (abbrev) {
                    initFormData.stateCheckList.push(new FormInput({
                        id: abbrev,
                        name: `${abbrev}-check`,
                        label: jurisdiction.name(),
                        value: false,
                        isDisabled: true
                    }));
                }
            }
        });

        this.formData = reactive(initFormData);
    }

    handleSubmit() {
        // This function is just a stub as it is the boundary to the next feature to be developed
        if (this.isAtLeastOnePrivilegeChosen && this.areAllJurisprudenceConfirmed) {
            this.startFormLoading();
            console.log(this.formData);
            this.endFormLoading();
        }
    }

    handleJurisprudenceClicked(privilegePurchaseInformation) {
        const stateAbbrev = privilegePurchaseInformation.jurisdiction.abbrev;
        const newValue = this.formData.jurisprudenceConfirmations[stateAbbrev].value;

        if (newValue === true) {
            if (stateAbbrev) {
                this.jurisprudencePendingConfirmation = stateAbbrev;
                this.formData.jurisprudenceConfirmations[stateAbbrev].value = false;
            }
        }
    }

    handleCancelClicked() {
        if (this.currentCompact?.type) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompact?.type }
            });
        }
    }

    handleBackClicked() {
        if (this.currentCompact?.type) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompact?.type }
            });
        }
    }

    deselectState(state) {
        const stateAbbrev = state?.jurisdiction?.abbrev;

        this.formData.stateCheckList.find((checkBox) => (checkBox.id === stateAbbrev)).value = false;
        delete this.formData.jurisprudenceConfirmations[stateAbbrev];
    }

    submitUnderstanding() {
        const { jurisprudencePendingConfirmation } = this;

        if (jurisprudencePendingConfirmation) {
            this.formData.jurisprudenceConfirmations[jurisprudencePendingConfirmation].value = true;
            this.$store.dispatch('setModalIsOpen', false);
            this.jurisprudencePendingConfirmation = '';
        }
    }

    closeAndInvalidateCheckbox() {
        const { jurisprudencePendingConfirmation } = this;

        if (jurisprudencePendingConfirmation) {
            this.formData.jurisprudenceConfirmations[jurisprudencePendingConfirmation].value = false;
            this.$store.dispatch('setModalIsOpen', false);
            this.jurisprudencePendingConfirmation = '';
        }
    }

    toggleStateSelected(stateFormInput) {
        const newStateFormInputValue = !stateFormInput.value;
        const stateAbbrev = stateFormInput.id;

        stateFormInput.value = newStateFormInputValue;

        if (newStateFormInputValue) {
            if (stateAbbrev && this.selectedStatesWithJurisprudenceRequired.includes(stateAbbrev)) {
                this.formData.jurisprudenceConfirmations[stateAbbrev] = new FormInput({
                    id: `${stateAbbrev}-jurisprudence`,
                    name: `${stateAbbrev}-jurisprudence`,
                    label: this.jurisprudenceExplanationText,
                    value: false
                });
            }
        } else {
            delete this.formData.jurisprudenceConfirmations[stateAbbrev];
        }
    }

    checkIfStateSelectIsDisabled(state): boolean {
        return this.disabledPrivilegeStateChoices.includes(state.id);
    }

    @Watch('alreadyObtainedPrivilegeStates.length') reInitForm() {
        this.initFormInputs();
    }
}
