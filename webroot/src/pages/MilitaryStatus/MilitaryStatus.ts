//
//  MilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import MilitaryDocumentRow from '@components/MilitaryDocumentRow/MilitaryDocumentRow.vue';
import Modal from '@components/Modal/Modal.vue';
import { Compact } from '@models/Compact/Compact.model';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { LicenseeUser } from '@/models/LicenseeUser/LicenseeUser.model';
import { Licensee } from '@/models/Licensee/Licensee.model';
import { MilitaryAffiliation } from '@/models/MilitaryAffiliation/MilitaryAffiliation.model';

@Component({
    name: 'MilitaryStatus',
    components: {
        InputButton,
        InputSubmit,
        ListContainer,
        MilitaryDocumentRow,
        Modal
    }
})
export default class MilitaryStatus extends mixins(MixinForm) {
    //
    // Data
    //
    shouldShowEndAffiliationModal = false;

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get statusTitleText(): string {
        return this.$t('licensing.status').toUpperCase();
    }

    get status(): string {
        let militaryStatus = '';

        if (this.licensee) {
            militaryStatus = this.licensee.isMilitary() ? this.$t('licensing.statusOptions.active') : this.$t('licensing.statusOptions.inactive');
        }

        return militaryStatus;
    }

    get affiliationTypeTitle(): string {
        return this.$t('military.affiliationType').toUpperCase();
    }

    get affiliationType(): string {
        let militaryStatus = '';

        if (this.licensee) {
            const activeAffiliation = this.licensee.aciveMilitaryAffiliation() as any;
            const isMilitary = this.licensee.isMilitary();

            if (isMilitary && activeAffiliation?.affiliationType === 'militaryMember') {
                militaryStatus = this.$tm('military.affiliationTypes.militaryMember');
            } else if (isMilitary && activeAffiliation?.affiliationType === 'militaryMemberSpouse') {
                militaryStatus = this.$tm('military.affiliationTypes.militaryMemberSpouse');
            } else {
                militaryStatus = this.$tm('military.affiliationTypes.none');
            }
        }

        return militaryStatus;
    }

    get previouslyUploadedTitle(): string {
        return this.$t('military.previouslyUploadedDocuments').toUpperCase();
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser {
        return this.userStore?.model;
    }

    get militaryDocumentHeader(): any {
        return { name: 'File name', date: 'Date uploaded' };
    }

    get endAffiliationModalTitle(): string {
        return this.$t('military.endAffiliationModalTitle');
    }

    get endAffiliationModalContent(): string {
        return this.$t('military.endAffiliationModalContent');
    }

    get backText(): string {
        return this.$t('military.noGoBack');
    }

    get yesEndText(): string {
        return this.$t('military.yesEnd');
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

    get affiliations(): Array<any> {
        let affiliations: any = [];

        if (this.licensee && this.licensee?.militaryAffiliations) {
            affiliations = (this.licensee.militaryAffiliations as Array<MilitaryAffiliation>).map((f) => {
                if (f.fileNames) {
                    return { name: f.fileNames[0] || null, date: f.dateOfUploadDisplay() };
                }

                return { name: '' || null, date: '' };
            });
        }

        return affiliations;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-end',
            }),
        };

        this.formData = reactive(initFormData);
    }

    goBack() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'LicenseeDashboard',
                params: { compact: this.currentCompactType }
            });
        }
    }

    startEndAffiliationFlow() {
        this.shouldShowEndAffiliationModal = true;
    }

    closeEndAffilifationModal() {
        this.shouldShowEndAffiliationModal = false;
        this.$store.dispatch('setModalIsOpen', false);
    }

    async confirmEndMilitaryAffiliation() {
        await this.$store.dispatch('user/endMilitaryAffiliationRequest');
        this.closeEndAffilifationModal();
        await this.$store.dispatch('user/getLicenseeAccountRequest');
    }

    async sortingChange() {
        console.log('sort changed');
    }

    async paginationChange() {
        console.log('page changed');
    }

    editInfo() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'UpdateMilitaryStatus',
                params: { compact: this.currentCompactType }
            });
        }
    }
}
