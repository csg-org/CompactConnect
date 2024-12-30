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
    shouldShowEndAffilifationModal = false;

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
        return 'Active';
    }

    get affiliationTypeTitle(): string {
        return this.$t('military.affiliationType').toUpperCase();
    }

    get affiliationType(): string {
        return 'Active-duty military member';
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

    get militaryDocuments(): any {
        return [];
    }

    get militaryDocumentHeader(): any {
        return { name: 'File name', date: 'Date uploaded' };
    }

    //
    // Methods
    //
    initFormInputs(): void {
        const initFormData: any = {
            submitUnderstanding: new FormInput({
                isSubmitInput: true,
                id: 'submit-understanding',
            }),
        };

        this.formData = reactive(initFormData);
    }

    goBack() {
        console.log('go back');
    }

    startEndAffiliationFlow() {
        this.shouldShowEndAffilifationModal = true;
    }

    async sortingChange() {
        console.log('sort');
    }

    // Match pageChange() @Prop signature from /components/Lists/Pagination/Pagination.ts
    async paginationChange() {
        console.log('pag');
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
