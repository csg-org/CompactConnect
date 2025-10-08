//
//  PrivilegePurchaseAcceptUI.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/29/2025.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import { PaymentSdkConfig } from '@models/CompactFeeConfig/CompactFeeConfig.model';
import moment, { Moment } from 'moment';

export interface AcceptUiResponse {
    messages?: {
        message: Array<{ code: string, text: string }>,
        resultCode: string,
    },
    opaqueData?: {
        dataDescriptor: string,
        dataValue: string,
    },
    customerInformation?: {
        firstName?: string,
        lastName?: string,
    },
    encryptedCardData?: {
        cardNumber?: string,
        expDate?: string,
        bin?: string,
    },
    expiry?: Moment | null,
}

@Component({
    name: 'PrivilegePurchaseAcceptUI',
    emits: ['success', 'error'],
})
class PrivilegePurchaseAcceptUI extends Vue {
    @Prop({ required: true }) paymentSdkConfig!: PaymentSdkConfig | null;
    @Prop({ default: '' }) buttonLabel?: string;
    @Prop({ default: false }) includeButtonIcon?: boolean;
    @Prop({ default: true }) private isEnabled?: boolean;
    @Prop({ default: false }) private isWarning?: boolean;

    //
    // Data
    //
    isLoadingInit = true;
    acceptUiScript: HTMLElement | null = null;
    acceptUiContainer: HTMLElement | null = null;
    acceptUiContainerId = 'AcceptUIContainer';
    focusTrapElement: HTMLElement | null = null;
    acceptUiObserver: MutationObserver | null = null;
    acceptUiPaymentDetails: AcceptUiResponse = {};
    errorMessage = '';
    successMessage = '';

    //
    // Lifecycle
    //
    mounted() {
        this.initPaymentDetailsUi();
    }

    beforeUnmount(): void {
        this.unloadPaymentDetailsUi();
    }

    //
    // Computed
    //
    get loginId(): string {
        return this.paymentSdkConfig?.loginId || '';
    }

    get clientKey(): string {
        return this.paymentSdkConfig?.clientKey || '';
    }

    get isSandboxMode(): boolean {
        return this.paymentSdkConfig?.isSandboxMode || false;
    }

    get buttonLabelText(): string {
        return this.buttonLabel || this.$t('payment.enterPaymentDetails');
    }

    //
    // Methods
    //
    initPaymentDetailsUi(): void {
        const scriptSrc = (this.isSandboxMode)
            ? 'https://jstest.authorize.net/v3/AcceptUI.js'
            : 'https://js.authorize.net/v3/AcceptUI.js';
        const componentContainer = document.getElementById('finalize-privilege-purchase-container');
        const script = document.createElement('script');

        // AcceptUI library expects handler function to be on the window object
        (window as any).handlePaymentDetailsResponse = this.handlePaymentDetailsResponse;

        // Load the AcceptUI library
        this.acceptUiScript = script;
        script.src = scriptSrc;
        script.charset = 'utf-8';
        componentContainer?.appendChild(script);
        script.onload = () => {
            this.isLoadingInit = false;
        };
    }

    unloadPaymentDetailsUi(): void {
        this.removeFocusTrapHandling();
        this.removeAcceptUiElements();
        this.acceptUiScript?.remove();
        this.acceptUiScript = null;
        delete (window as any).handlePaymentDetailsResponse;
    }

    removeAcceptUiElements(): void {
        this.acceptUiContainer?.remove();
        this.acceptUiContainer = null;

        this.focusTrapElement?.remove();
        this.focusTrapElement = null;

        document.getElementById('AcceptUIBackground')?.remove();
    }

    removeFocusTrapHandling(): void {
        const {
            acceptUiContainer,
            focusTrapElement,
            focusTrap,
            acceptUiObserver
        } = this;

        if (acceptUiContainer) {
            acceptUiContainer.removeEventListener('keydown', focusTrap);
        }

        if (focusTrapElement) {
            focusTrapElement.removeEventListener('keydown', focusTrap);
            focusTrapElement.remove();
        }

        if (acceptUiObserver) {
            acceptUiObserver.disconnect();
        }
    }

    handleClicked(): void {
        this.resetMessages();
        this.improveInteractions();
    }

    resetMessages(): void {
        this.errorMessage = '';
        this.successMessage = '';
    }

    improveInteractions(): void {
        const acceptUiContainer = document.getElementById(this.acceptUiContainerId);
        const iframe = acceptUiContainer?.getElementsByTagName('iframe')[0];
        const trapper = document.createElement('div');

        this.removeFocusTrapHandling();

        if (acceptUiContainer) {
            // The AcceptUI.js widget will sometimes pop up partially or fully off-screen if the
            // launching page's <body> height is significantly taller than the viewport.
            // This is a simple adjustment to start the pop up near our content.
            acceptUiContainer.style.top = '300px';

            // Configure elements before / after the iframe to focus-trap the iframe
            this.acceptUiContainer = acceptUiContainer;
            trapper.id = 'iframe-trapper';
            trapper.classList.add('iframe-trapper');
            trapper.setAttribute('tabindex', '0');
            acceptUiContainer.parentNode?.insertBefore(trapper, acceptUiContainer.nextSibling);
            this.focusTrapElement = trapper;

            acceptUiContainer.addEventListener('keydown', this.focusTrap);
            trapper.addEventListener('keydown', this.focusTrap);

            // Attempt to detect the closing of the iframe
            this.detectIframeClose();

            // Attempt to focus the iframe container for better keyboard nav
            acceptUiContainer.setAttribute('tabindex', '0');
            window.setTimeout(() => { acceptUiContainer.focus(); }, 100);
        }

        if (iframe) {
            try {
                // Attempt to set the title attr on the iframe for better a11y
                iframe.setAttribute('title', this.$t('payment.enterPaymentDetails'));
            } catch (err) {
                // Continue
            }
        }
    }

    focusTrap(event: KeyboardEvent): void {
        const { target, key, shiftKey } = event;
        const targetElement = target as Element;
        const { acceptUiContainer, focusTrapElement } = this;
        const isIframeVisible = acceptUiContainer?.classList.contains('show');

        if (isIframeVisible && key === 'Tab') {
            // If tabbing on the trapper element, cycle focus back to the iframe container
            if (!shiftKey && targetElement?.id === 'iframe-trapper') {
                event.preventDefault();
                acceptUiContainer?.focus();
            } else if (shiftKey && targetElement?.id === this.acceptUiContainerId) {
                // If reverse tabbing on the iframe container, cycle focus back to the trapper element
                event.preventDefault();
                focusTrapElement?.focus();
            }
        }
    }

    detectIframeClose(): void {
        const observer = new MutationObserver((mutationsList) => {
            mutationsList.forEach((mutation) => {
                if (mutation.type === 'childList') {
                    mutation.removedNodes.forEach((removedNode) => {
                        if ((removedNode as HTMLElement).id === this.acceptUiContainerId) {
                            this.handleIframeClosed();
                        }
                    });
                }
            });
        });

        this.acceptUiObserver = observer;
        observer.observe(document.body, { childList: true, subtree: false });
    }

    handleIframeClosed(): void {
        this.removeFocusTrapHandling();
        document.getElementById('payment-init')?.focus();
    }

    handlePaymentDetailsResponse(response: any): void {
        const { acceptUiPaymentDetails } = this;

        acceptUiPaymentDetails.messages = response?.messages;
        acceptUiPaymentDetails.opaqueData = response?.opaqueData;
        acceptUiPaymentDetails.customerInformation = response?.customerInformation;
        acceptUiPaymentDetails.encryptedCardData = response?.encryptedCardData;

        if (response?.messages?.resultCode?.toLowerCase() !== 'ok') {
            const responseMessages = response?.messages?.message || [];

            if (Array.isArray(responseMessages)) {
                responseMessages.forEach((message) => {
                    console.warn(`Authorize.net SDK: ${message.code || ''} ${message.text || ''}`.trim());
                });
            }

            this.$emit('error', acceptUiPaymentDetails);
        } else {
            acceptUiPaymentDetails.expiry = moment().add(15, 'minutes');
            this.$emit('success', acceptUiPaymentDetails);
        }
    }
}

export default toNative(PrivilegePurchaseAcceptUI);

// export default PrivilegePurchaseAcceptUI;
