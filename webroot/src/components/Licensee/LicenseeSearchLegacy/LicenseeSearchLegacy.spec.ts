//
//  LicenseeSearchLegacy.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/12/2024.
//

import { nextTick } from 'vue';
import chaiMatchPattern from 'chai-match-pattern';
import chai from 'chai';
import { mountShallow, mountFull } from '@tests/helpers/setup';
import LicenseeSearch from '@components/Licensee/LicenseeSearchLegacy/LicenseeSearchLegacy.vue';
import { Compact, CompactType } from '@models/Compact/Compact.model';
import { AppModes } from '@/app.config';
import store from '@store/index';

chai.use(chaiMatchPattern);

const { expect } = chai;
const populateSearchFields = (formData) => {
    formData.firstName.value = 'Test';
    formData.lastName.value = 'User';
    formData.state.value = 'co';
    formData.licenseNumber.value = 'ABC123';
    formData.licenseType.value = 'licensed clinical social worker';
    formData.cuid.value = 'SWC-9999-9';
};

describe('LicenseeSearch component', async () => {
    afterEach(async () => {
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('user/setCurrentCompact', null);
    });

    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeSearch);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeSearch).exists()).to.equal(true);
    });
    it('should successfully validate CUID values', async () => {
        const wrapper = await mountShallow(LicenseeSearch);
        const cuidInput = wrapper.vm.formData.cuid;
        const formatError = wrapper.vm.$t('inputErrors.invalidCuidFormat');
        const testCases = [
            { value: '', isValid: true, errorMessage: '' },
            { value: 'SWC-9999-9', isValid: true, errorMessage: '' },
            { value: 'swc-0000-1', isValid: true, errorMessage: '' },
            { value: 'SwC-8879-1510662364862837507201851701209841388880384284903247330', isValid: true, errorMessage: '' },
            { value: 'SWC', isValid: false, errorMessage: formatError },
            { value: 'SWC-9999', isValid: false, errorMessage: formatError },
            { value: 'SWC-999-99', isValid: false, errorMessage: formatError },
            { value: 'SWC-99999-99', isValid: false, errorMessage: formatError },
            { value: 'SWC-9999-0', isValid: false, errorMessage: formatError },
            { value: 'SWC-9999-09', isValid: false, errorMessage: formatError },
            { value: 'ABC-9999-99', isValid: false, errorMessage: formatError },
            { value: ' SWC-9999-99', isValid: false, errorMessage: formatError },
            { value: 'SWC-9999-99 ', isValid: false, errorMessage: formatError },
        ];

        testCases.forEach((testCase) => {
            cuidInput.value = testCase.value;
            cuidInput.isTouched = true;
            cuidInput.validate();

            expect(cuidInput.isValid, `isValid for "${testCase.value}"`).to.equal(testCase.isValid);
            expect(cuidInput.errorMessage, `errorMessage for "${testCase.value}"`).to.equal(testCase.errorMessage);
        });
    });
    it('should successfully not display a CUID error when invalid and untouched', async () => {
        const wrapper = await mountShallow(LicenseeSearch);
        const cuidInput = wrapper.vm.formData.cuid;

        cuidInput.value = 'not-a-cuid';
        cuidInput.isTouched = false;
        cuidInput.validate();

        expect(cuidInput.isValid).to.equal(false);
        expect(cuidInput.errorMessage).to.equal('');
    });
    it('should successfully clear the CUID error when the value is corrected', async () => {
        const wrapper = await mountShallow(LicenseeSearch);
        const cuidInput = wrapper.vm.formData.cuid;
        const formatError = wrapper.vm.$t('inputErrors.invalidCuidFormat');

        cuidInput.value = 'not-a-cuid';
        cuidInput.isTouched = true;
        cuidInput.validate();

        expect(cuidInput.isValid).to.equal(false);
        expect(cuidInput.errorMessage).to.equal(formatError);

        cuidInput.value = 'SWC-9999-9';
        cuidInput.validate();

        expect(cuidInput.isValid).to.equal(true);
        expect(cuidInput.errorMessage).to.equal('');
    });
    it('should successfully display the CUID format error after blur', async () => {
        await store.dispatch('setAppMode', AppModes.SOCIAL_WORK);

        const wrapper = await mountFull(LicenseeSearch);
        const input = wrapper.find('#cuid');

        expect(input.exists()).to.equal(true);

        await input.setValue('not-a-cuid');
        await input.trigger('blur');
        await nextTick();

        const error = wrapper.find('#cuid-error');

        expect(error.exists()).to.equal(true);
        expect(error.text()).to.equal(wrapper.vm.$t('inputErrors.invalidCuidFormat'));
    });
    it('should successfully emit searchParams for JCC staff search', async () => {
        await store.dispatch('setAppMode', AppModes.JCC);

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        populateSearchFields(formData);
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: undefined,
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
        });
    });
    it('should successfully emit searchParams for JCC public search', async () => {
        await store.dispatch('setAppMode', AppModes.JCC);
        await store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.ASLP }));

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                isPublicSearch: true,
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        populateSearchFields(formData);
        formData.compact.value = CompactType.ASLP;
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: CompactType.ASLP,
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
        });
    });
    it('should successfully emit searchParams for cosmetology staff search', async () => {
        await store.dispatch('setAppMode', AppModes.COSMETOLOGY);

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        populateSearchFields(formData);
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: undefined,
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
            licenseNumber: 'ABC123',
        });
    });
    it('should successfully emit searchParams for cosmetology public search', async () => {
        await store.dispatch('setAppMode', AppModes.COSMETOLOGY);
        await store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.COSMETOLOGY }));

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                isPublicSearch: true,
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        populateSearchFields(formData);
        formData.compact.value = CompactType.COSMETOLOGY;
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: CompactType.COSMETOLOGY,
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
            licenseNumber: 'ABC123',
        });
    });
    it('should successfully emit searchParams for social work staff search', async () => {
        await store.dispatch('setAppMode', AppModes.SOCIAL_WORK);

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        populateSearchFields(formData);
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: undefined,
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
            licenseNumber: 'ABC123',
            licenseType: 'licensed clinical social worker',
            cuid: 'SWC-9999-9',
        });
    });
    it('should successfully emit searchParams for social work public search', async () => {
        await store.dispatch('setAppMode', AppModes.SOCIAL_WORK);
        await store.dispatch('user/setCurrentCompact', new Compact({ type: CompactType.SOCIAL_WORK }));

        let emittedSearchParams;
        const wrapper = await mountShallow(LicenseeSearch, {
            props: {
                isPublicSearch: true,
                onSearchParams: (searchParams) => {
                    emittedSearchParams = searchParams;
                },
            },
        });
        const { formData } = wrapper.vm;

        populateSearchFields(formData);
        formData.compact.value = CompactType.SOCIAL_WORK;
        await wrapper.vm.handleSubmit();

        expect(emittedSearchParams).to.matchPattern({
            compact: CompactType.SOCIAL_WORK,
            firstName: 'Test',
            lastName: 'User',
            state: 'co',
            licenseNumber: 'ABC123',
            licenseType: 'licensed clinical social worker',
            cuid: 'SWC-9999-9',
        });
    });
});
