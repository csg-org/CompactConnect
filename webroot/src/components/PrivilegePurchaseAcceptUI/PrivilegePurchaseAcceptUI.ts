//
//  PrivilegePurchaseAcceptUI.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/29/2025.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
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
    //
    // Data
    //
    isLoadingInit = true;
    acceptUiScript: HTMLElement | null = null;
    acceptUiPaymentDetails: AcceptUiResponse = {};
    errorMessage = '';

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
        return this.$envConfig.acceptUiLoginId || '';
    }

    get clientKey(): string {
        return this.$envConfig.acceptUiClientKey || '';
    }

    //
    // Methods
    //
    initPaymentDetailsUi(): void {
        const componentContainer = document.getElementById('finalize-privilege-purchase-container');
        const script = document.createElement('script');

        // AcceptUI library expects handler function to be on the window object
        (window as any).handlePaymentDetailsResponse = this.handlePaymentDetailsResponse;

        // Load the AcceptUI library
        this.acceptUiScript = script;
        script.src = 'https://jstest.authorize.net/v3/AcceptUI.js';
        script.charset = 'utf-8';
        componentContainer?.appendChild(script);
        script.onload = () => {
            this.isLoadingInit = false;
            console.log('script loaded');
            console.log('');
        };
    }

    unloadPaymentDetailsUi(): void {
        (window as any).handlePaymentDetailsResponse = undefined;
    }

    adjustFramePosition(): void {
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
            this.errorMessage = this.$t('payment.confirmCardDetailsError');
            this.$emit('error', acceptUiPaymentDetails);
        } else {
            acceptUiPaymentDetails.expiry = moment().add(14, 'minutes');
            this.$emit('success', acceptUiPaymentDetails);
        }
    }
}

export default toNative(PrivilegePurchaseAcceptUI);

// export default PrivilegePurchaseAcceptUI;
