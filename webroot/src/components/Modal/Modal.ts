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

    globalStore: any = {};

    //
    // Lifecycle
    //
    created() {
        this.globalStore = this.$store.state;
    }

    mounted() {
        this.$store.dispatch('setModalIsOpen', true);
    }

    beforeUnmount() {
        this.$store.dispatch('setModalIsOpen', false);
    }

    //
    // Computed
    //
    get displayTitle(): string {
        if (this.title) {
            return this.title;
        }

        return (this.isErrorModal) ? 'Error:' : 'Info:';
    }

    get isLogoutOnly(): boolean {
        return this.globalStore.isModalLogoutOnly;
    }

    //
    // Methods
    //
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
