//
//  Modal.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/22/2020.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import { nextTick } from 'vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'Modal',
    components: {
        InputButton,
    },
    emits: ['close-modal'],
})
class Modal extends Vue {
    @Prop({ default: '' }) private title?: string;
    @Prop({ default: false }) private closeOnBackgroundClick?: boolean;
    @Prop({ default: false }) private hasCloseIcon?: boolean;
    @Prop({ default: false }) private isErrorModal?: boolean;
    @Prop({ default: true }) private showActions?: boolean;
    @Prop({ default: [] }) private customActions?: Array<{ label: string; emitEventName: string; closeAfter: boolean }>
    @Prop({ default: '' }) private modalId?: string;

    globalStore: any = {};

    //
    // Lifecycle
    //
    created() {
        this.globalStore = this.$store.state;
    }

    async mounted() {
        this.$store.dispatch('setModalIsOpen', true);

        await nextTick();
        await this.initializeModalAccessibility();
    }

    beforeUnmount() {
        this.$store.dispatch('setModalIsOpen', false);
    }

    //
    // Computed
    //
    get displayTitle(): string {
        if (this.title) {
            return this.title.trim();
        }

        return (this.isErrorModal) ? 'Error:' : 'Info:';
    }

    get isLogoutOnly(): boolean {
        return this.globalStore.isModalLogoutOnly;
    }

    get titleId(): string {
        const baseId = this.modalId || 'modal';

        return `${baseId}-title`;
    }

    get contentId(): string {
        const baseId = this.modalId || 'modal';

        return `${baseId}-content`;
    }

    //
    // Methods
    //
    async initializeModalAccessibility() {
        const root = this.$el as HTMLElement | null;
        const modalContainer = root?.querySelector('.modal-container[role="dialog"]') as HTMLElement | null;
        const modalContent = this.$refs.modalContent as (HTMLElement | undefined);

        // Focus dialog container first for title announcement (even if content not yet rendered)
        if (modalContainer) {
            modalContainer.setAttribute('tabindex', '-1');
            modalContainer.focus({ preventScroll: true });
        }

        await nextTick();

        // Optionally move focus to content for reading/keyboard nav if present
        if (modalContent && document.contains(modalContent)) {
            modalContent.focus({ preventScroll: true });
        }
    }

    closeModal() {
        this.$emit('close-modal');
        this.$store.dispatch('setModalIsOpen', false);
    }

    logout() {
        this.$store.dispatch('user/logoutRequest');
        this.closeModal();
    }
}

export default toNative(Modal);

// export { Modal };
