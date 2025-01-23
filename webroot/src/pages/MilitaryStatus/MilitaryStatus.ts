//
//  MilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, mixins } from 'vue-facing-decorator';
import { reactive } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import ListContainer from '@components/Lists/ListContainer/ListContainer.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
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
    get userStore(): any {
        return this.$store.state.user;
    }

    get user(): LicenseeUser {
        return this.userStore?.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore?.currentCompact || null;
    }

    get currentCompactType(): string | null {
        return this.currentCompact?.type || null;
    }

    get licensee(): Licensee | null {
        return this.user?.licensee || null;
    }

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

    get militaryDocumentHeader(): any {
        return { name: this.$t('military.fileName'), date: this.$t('military.dateUploaded') };
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
        return this.$matches.phone.only ? this.$t('common.yes') : this.$t('military.yesEnd');
    }

    get sortOptions(): Array<any> {
        // Sorting not API supported
        return [];
    }

    get affiliations(): Array<any> {
        let affiliations: any = [];

        if (this.licensee && this.licensee?.militaryAffiliations) {
            affiliations = (this.licensee.militaryAffiliations)
                .map((militaryAffiliation: MilitaryAffiliation) => {
                    const affiliationDisplay = { name: '', date: '' };

                    if (militaryAffiliation.fileNames && (militaryAffiliation.fileNames as Array<string>).length) {
                        affiliationDisplay.name = militaryAffiliation.fileNames[0] || '';
                        affiliationDisplay.date = militaryAffiliation.dateOfUploadDisplay();
                    }

                    return affiliationDisplay;
                });
        }

        return affiliations;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            submitEnd: new FormInput({
                isSubmitInput: true,
                id: 'submit-end',
            }),
        });
    }

    sortingChange() {
        // Sorting not API supported
        return false;
    }

    paginationChange() {
        // Pagination not API supported
        return false;
    }

    editInfo() {
        if (this.currentCompactType) {
            this.$router.push({
                name: 'MilitaryStatusUpdate',
                params: { compact: this.currentCompactType }
            });
        }
    }

    async confirmEndMilitaryAffiliation() {
        this.closeEndAffilifationModal();
        await this.$store.dispatch('user/endMilitaryAffiliationRequest');
        await this.$store.dispatch('user/getLicenseeAccountRequest');
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
        this.$nextTick(() => {
            const buttonComponent = this.$refs.noBackButton as any;
            const button = buttonComponent.$refs.button as HTMLElement;

            button.focus();
        });
    }

    closeEndAffilifationModal() {
        this.shouldShowEndAffiliationModal = false;
        this.$store.dispatch('setModalIsOpen', false);
    }

    focusTrap(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('no-back-button');
        const lastTabIndex = document.getElementById(this.formData.submitEnd.id);

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
