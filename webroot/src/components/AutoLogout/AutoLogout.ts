//
//  AutoLogout.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/13/2025.
//

import {
    Component,
    mixins,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, nextTick } from 'vue';
import { autoLogoutConfig } from '@/app.config';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import Modal from '@components/Modal/Modal.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';

@Component({
    name: 'AutoLogout',
    components: {
        Modal,
        InputSubmit,
    },
})
class AutoLogout extends mixins(MixinForm) {
    //
    // Data
    //
    gracePeriodTimerId: number | null = null;
    gracePeriodExtendEnabled = true;
    eventsController: AbortController | null = null;
    eventDebounceMs = 1000;
    activityResetEventTypes = [
        'mousemove',
        'mousedown',
        'click',
        'keypress',
        'touchstart',
        'touchend',
        'touchmove',
        'onscroll',
        'wheel',
        'mousewheel',
    ];

    //
    // Lifecycle
    //
    async created() {
        if (this.userStore.isLoggedIn) {
            this.initFormInputs();
            this.startAutoLogoutInactivityTimer();
        }
    }

    async beforeUnmount() {
        this.removeAutoLogoutEvents();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            stayLoggedIn: new FormInput({
                isSubmitInput: true,
                id: 'auto-logout-cancel-button',
            }),
        });
    }

    startAutoLogoutInactivityTimer(): void {
        const { isLoggedIn, isAutoLogoutWarning } = this.userStore;
        const abortController = new AbortController();
        const eventHandler = (event) => {
            autoLogoutConfig.LOG(`event: ${event.type}`);
            this.$store.dispatch('user/startAutoLogoutInactivityTimer');
            this.startAutoLogoutInactivityTimer();
        };
        const debouncedEventHandler = this.debounce(eventHandler, this.eventDebounceMs);

        this.removeAutoLogoutEvents();

        if (isLoggedIn && !isAutoLogoutWarning) {
            this.$store.dispatch('user/startAutoLogoutInactivityTimer');
            this.eventsController = abortController;
            this.activityResetEventTypes.forEach((eventType) => {
                document.addEventListener(eventType, debouncedEventHandler, {
                    capture: false,
                    once: true,
                    passive: true,
                    signal: abortController.signal,
                });
            });
            autoLogoutConfig.LOG(`event listeners created`);
        }
    }

    startAutoLogoutGracePeriodTimer(): void {
        const { isLoggedIn, isAutoLogoutWarning } = this.userStore;

        if (isLoggedIn && isAutoLogoutWarning) {
            autoLogoutConfig.LOG(`grace period started`);
            this.gracePeriodTimerId = window.setTimeout(() => {
                autoLogoutConfig.LOG(`grace period logging out...`);
                this.gracePeriodExtendEnabled = false;
                this.$router.push({ name: 'Logout' });
            }, autoLogoutConfig.GRACE_PERIOD_MS);
        }
    }

    clearAutoLogoutGracePeriodTimer(): void {
        const { gracePeriodTimerId } = this;

        if (gracePeriodTimerId) {
            clearTimeout(gracePeriodTimerId);
            this.gracePeriodTimerId = null;
        }
    }

    debounce(callback, delayMs): () => void {
        let timeout;

        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => callback.apply(this, args), delayMs);
        };
    }

    staySignedIn(): void {
        this.clearAutoLogoutGracePeriodTimer();
        this.$store.dispatch('user/updateAutoLogoutWarning', false);
        this.startAutoLogoutInactivityTimer();
    }

    focusTrapAutoLogoutModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('auto-logout-cancel-button');
        const lastTabIndex = document.getElementById('auto-logout-cancel-button');

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

    removeAutoLogoutEvents(): void {
        const { eventsController } = this;

        if (eventsController) {
            eventsController.abort();
            this.eventsController = null;
            autoLogoutConfig.LOG(`event listeners removed`);
        }
    }

    //
    // Watchers
    //
    @Watch('userStore.isLoggedIn') async handleLoginUpdate() {
        if (!this.userStore.isLoggedIn) {
            this.removeAutoLogoutEvents();
        } else {
            this.startAutoLogoutInactivityTimer();
        }
    }

    @Watch('userStore.isAutoLogoutWarning') async handleAutoLogoutWarning() {
        if (this.userStore.isAutoLogoutWarning) {
            this.startAutoLogoutGracePeriodTimer();
            await nextTick();
            document.getElementById('auto-logout-cancel-button')?.focus();
        }
    }
}

export default toNative(AutoLogout);

// export default AutoLogout;
