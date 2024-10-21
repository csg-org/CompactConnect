//
//  SelectPrivileges.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/15/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputCheckbox from '@components/Forms/InputCheckbox/InputCheckbox.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { License } from '@models/License/License.model';
import { Licensee } from '@models/Licensee/Licensee.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { PrivilegePurchaseOption } from '@models/PrivilegePurchaseOption/PrivilegePurchaseOption.model';
import { State } from '@/models/State/State.model';

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
    // Data
    //

    //
    // Lifecycle
    //
    async created() {
        await this.$store.dispatch('user/getPrivilegePurchaseInformationRequest');
        this.initFormInputs();
    }

    //
    // Computed
    //
    get unalteredPurchaseList(): Array<PrivilegePurchaseOption> {
        return this.currentCompact?.privilegePurchaseOptions || [];
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
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

    get alreadyObtainedPrivilegeStates(): Array<any> {
        return this.licenseList.concat(this.privilegeList).map((license) => license?.issueState?.abbrev);
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
        return true;
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

    get statesSelected(): Array <any> {
        return this.formData.stateCheckList?.filter((formInput) =>
            (formInput.value === true)).map((input) => input.id);
    }

    get selectedStatePurchaseDataList(): Array <any> {
        console.log('statesSelected', this.statesSelected);
        console.log('unalteredPurchaseList', this.unalteredPurchaseList);
        return this.unalteredPurchaseList.filter((option) =>
            (this.statesSelected?.includes(option?.jurisdiction?.abbrev)));
    }

    get expirationDateText(): string {
        return 'expirationDateText';
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            stateCheckList: [],
            submit: new FormInput({
                isSubmitInput: true,
                id: 'submit',
            }),
        };

        this.unalteredPurchaseList?.forEach((purchaseOption) => {
            const { jurisdiction = new State() } = purchaseOption;

            if (jurisdiction) {
                const { abbrev } = jurisdiction;

                if (typeof abbrev === 'string' && abbrev) {
                    initFormData.stateCheckList.push(new FormInput({
                        id: `${abbrev}`,
                        name: `${abbrev}-check`,
                        label: `${jurisdiction.name()}`,
                        value: false
                    }));
                }
            }
        });

        this.formData = reactive(initFormData);
    }

    handleSubmit() {
        if (this.isAtLeastOnePrivilegeChosen) {
            this.startFormLoading();

            console.log('Form data submitted', this.formData);
            this.endFormLoading();
        }
    }

    handleStateClicked() {
        // console.log('we handlin', eh.target._modelValue);
        // console.log('we handlin', eh.target._modelValue);
    }
}
