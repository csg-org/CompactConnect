//
//  ExampleModal.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import Modal from '@components/Modal/Modal.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'ExampleModal',
    components: {
        Section,
        Modal,
        InputButton
    }
})
class ExampleModal extends Vue {
    //
    // Data
    //
    isModalVisible = false;
    isErrorModal = false;
    showCustomActions = false;
    modalContent = '';

    //
    // Computed
    //
    get defaultModalContent(): string {
        return this.$t('styleGuide.defaultModalContent');
    }

    //
    // Methods
    //
    openModal(): void {
        this.modalContent = this.modalContent || this.defaultModalContent;
        this.isModalVisible = true;
    }

    openErrorModal(): void {
        this.isErrorModal = true;
        this.modalContent = this.$t('styleGuide.errorModalContent');
        this.openModal();
    }

    openCustomActionsModal(): void {
        this.showCustomActions = true;
        this.modalContent = this.$t('styleGuide.customModalContent');
        this.openModal();
    }

    closeModal(): void {
        this.isModalVisible = false;
        this.isErrorModal = false;
        this.modalContent = '';
        this.showCustomActions = false;
    }
}

export default toNative(ExampleModal);

// export { ExampleModal };
