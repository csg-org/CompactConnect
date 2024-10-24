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
        InputButton
    }
})
export default class SelectPrivileges extends mixins(MixinForm) {
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

    get privilegeList(): Array<License> {
        return this.licensee?.privileges || [];
    }

    get licenseList(): Array<License> {
        return this.licensee?.licenses || [];
    }

    get alreadyObtainedPrivilegeStates(): Array<string | null> {
        return this.licenseList.concat(this.privilegeList).map((license) => license?.issueState?.abbrev || null);
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

    get expirationDateText(): string {
        return this.$t('licensing.expirationDate');
    }

    get jurisdictionFeeText(): string {
        return this.$t('licensing.jurisdictionFee');
    }

    get commissionFeeText(): string {
        return this.$t('licensing.commissionFee');
    }

    get subtotalText(): string {
        return this.$t('common.subtotal');
    }

    get jurisprudenceExplanationText(): string {
        return this.$t('licensing.jurisprudenceExplanationText');
    }

    get militaryDiscountText(): string {
        return this.$t('licensing.militaryDiscountText');
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

    get subTotalList(): Array<number> {
        return this.selectedStatePurchaseDataList?.map((purchaseInfo) => {
            const militaryDiscount = purchaseInfo.isMilitaryDiscountActive && purchaseInfo.militaryDiscountAmount
                ? purchaseInfo.militaryDiscountAmount : 0;

            return ((purchaseInfo?.fee || 0) + (this.currentCompactCommissionFee || 0) - (militaryDiscount));
        });
    }

    get jurisprudenceInputs(): Array<FormInput> {
        const jurisprudenceInputs: any = {};

        this.selectedStatePurchaseDataList.forEach((purchaseItem) => {
            if (purchaseItem.isJurisprudenceRequired) {
                const { jurisdiction = new State() } = purchaseItem;

                if (jurisdiction) {
                    const { abbrev } = jurisdiction;

                    if (typeof abbrev === 'string' && abbrev) {
                        jurisprudenceInputs[abbrev] = new FormInput({
                            id: `${abbrev}-jurisprudence`,
                            name: `${abbrev}-jurisprudence`,
                            label: `${this.jurisprudenceExplanationText}`,
                            value: false
                        });
                    }
                }
            }
        });

        return jurisprudenceInputs;
    }

    get selectPrivilegesTitleText(): string {
        return 'Select Privileges';
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

                if (typeof abbrev === 'string' && abbrev) {
                    const shouldDisable = this.alreadyObtainedPrivilegeStates.includes(abbrev);

                    initFormData.stateCheckList.push(new FormInput({
                        id: `${abbrev}`,
                        name: `${abbrev}-check`,
                        label: `${jurisdiction.name()}`,
                        value: false,
                        isDisabled: shouldDisable
                    }));
                }
            }
        });

        this.formData = reactive(initFormData);
    }

    handleSubmit() {
        if (this.isAtLeastOnePrivilegeChosen) {
            this.startFormLoading();
            console.log(this.formData);
            this.endFormLoading();
        }
    }

    handleStateClicked(e) {
        /* eslint no-underscore-dangle: 0 */
        const newValue = e.target._modelValue;
        const stateAbbrev = e.target.id;

        if (newValue === true) {
            if (typeof stateAbbrev === 'string' && stateAbbrev) {
                this.formData.jurisprudenceConfirmations[stateAbbrev] = new FormInput({
                    id: `${stateAbbrev}-jurisprudence`,
                    name: `${stateAbbrev}-jurisprudence`,
                    label: `${this.jurisprudenceExplanationText}`,
                    value: false
                });
            }
        } else {
            delete this.formData.jurisprudenceConfirmations[stateAbbrev];
        }
    }

    handleJurisprudenceClicked() {
        console.log('Open Jurisprudence modal');
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
        this.formData.stateCheckList.find((checkBox) => (checkBox.id === state?.jurisdiction?.abbrev)).value = false;
    }

    @Watch('alreadyObtainedPrivilegeStates.length') reInitForm() {
        this.initFormInputs();
    }
}
