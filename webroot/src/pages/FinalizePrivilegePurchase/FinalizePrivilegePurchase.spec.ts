//
//  FinalizePrivilegePurchase.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/28/2024.
//
import { nextTick } from 'vue';
import { expect } from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import FinalizePrivilegePurchase from '@pages/FinalizePrivilegePurchase/FinalizePrivilegePurchase.vue';
import InputCreditCard from '@components/Forms/InputCreditCard/InputCreditCard.vue';

describe('FinalizePrivilegePurchase page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(FinalizePrivilegePurchase);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(FinalizePrivilegePurchase).exists()).to.equal(true);
    });
    it('should not allow letters or symbols', async () => {
        const wrapper = await mountFull(FinalizePrivilegePurchase);

        const inputCreditCard = wrapper.findComponent(InputCreditCard);
        const ccInput = inputCreditCard.find('input');

        ccInput.element.value = '123a+';
        ccInput.trigger('input');

        await nextTick();
        expect(ccInput.element.value).to.equal('123');
    });
    it('should format the numbers correctly', async () => {
        const wrapper = await mountFull(FinalizePrivilegePurchase);

        const inputCreditCard = wrapper.findComponent(InputCreditCard);
        const ccInput = inputCreditCard.find('input');

        // First space applied
        ccInput.element.value = '12345';
        ccInput.trigger('input');

        await nextTick();
        expect(ccInput.element.value).to.equal('1234 5');

        // Second space applied
        ccInput.element.value = '123456789';
        ccInput.trigger('input');

        await nextTick();
        expect(ccInput.element.value).to.equal('1234 5678 9');

        // Third space applied
        ccInput.element.value = '1234567890123';
        ccInput.trigger('input');

        await nextTick();
        expect(ccInput.element.value).to.equal('1234 5678 9012 3');

        // delete works
        ccInput.element.value = '12345678901';
        ccInput.trigger('input');

        await nextTick();
        expect(ccInput.element.value).to.equal('1234 5678 901');
    });
});
