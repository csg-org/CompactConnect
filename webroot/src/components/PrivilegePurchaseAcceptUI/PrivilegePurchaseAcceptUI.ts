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
        (window as any).handlePaymentDetailsResponse = undefined;
    }

    handleClicked(): void {
        this.resetMessages();
        this.adjustFramePosition();
    }

    resetMessages(): void {
        this.errorMessage = '';
        this.successMessage = '';
    }

    adjustFramePosition(): void {
        // The AcceptUI.js widget will sometimes pop up partially or fully off-screen if the
        // launching page's <body> height is significantly taller than the viewport.
        // This is a simple adjustment to start the pop up near our content.
        const acceptUiContainer = document.getElementById('AcceptUIContainer');

        if (acceptUiContainer) {
            acceptUiContainer.style.top = '300px';
        }
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
