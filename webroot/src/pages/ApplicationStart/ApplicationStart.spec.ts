//
//  ApplicationStart.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import sinon from 'sinon';
import { mountFull, mountShallow } from '@tests/helpers/setup';
import ApplicationStart from '@pages/ApplicationStart/ApplicationStart.vue';
import { CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import { Application, ApplicationType } from '@models/Application/Application.model';
import store from '@store/index';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';

use(chaiMatchPattern);

const setPsypactCompact = async (): Promise<void> => {
    await store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: CompactType.PSYPACT }));
};

const mountPage = async (mountFn = mountFull) => {
    const wrapper = await mountFn(ApplicationStart);

    await nextTick();
    await flushPromises();

    return wrapper;
};

describe('ApplicationStart page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(ApplicationStart);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ApplicationStart).exists()).to.equal(true);
    });
    it('should fetch the application config and compact states when states are not loaded', async () => {
        const dispatchSpy = sinon.spy(store, 'dispatch');

        await mountPage(mountShallow);

        expect(dispatchSpy.calledWith('user/getApplicationConfigRequest')).to.equal(true);
        expect(dispatchSpy.calledWith('user/getCompactStatesRequest')).to.equal(true);
    });
    it('should only fetch the application config when compact states are already loaded', async () => {
        await setPsypactCompact();

        const dispatchSpy = sinon.spy(store, 'dispatch');
        const wrapper = await mountPage(mountShallow);
        const component = wrapper.vm;

        expect(dispatchSpy.calledWith('user/getApplicationConfigRequest', { compact: CompactType.PSYPACT }))
            .to.equal(true);
        expect(dispatchSpy.calledWith('user/getCompactStatesRequest')).to.equal(false);
        expect(component.applicationConfig?.feeForType(ApplicationType.APIT)).to.equal(100);
        expect(component.applicationConfig?.feeForType(ApplicationType.TAP)).to.equal(50);
    });
    it('should render the page sections with no types preselected by default', async () => {
        const wrapper = await mountPage();
        const component = wrapper.vm;

        expect(wrapper.find('.application-start-title').text()).to.equal('Apply for a PSYPACT authorization');
        expect(wrapper.findAll('.application-start-card').length).to.equal(2);
        expect(component.selectedTypes).to.matchPattern([]);
        expect(wrapper.find('label[for="type-apit"]').text())
            .to.equal('APIT (Authority to Practice Interjurisdictional Telepsychology)');
        expect(wrapper.find('label[for="type-tap"]').text()).to.equal('TAP (Temporary Authorization to Practice)');
        expect(wrapper.find('.requirement-item.license').exists()).to.equal(true);
        expect(wrapper.find('.requirement-item.degree').exists()).to.equal(true);
        expect(wrapper.find('.requirement-item.epassport').exists()).to.equal(false);
        expect(wrapper.find('.requirement-item.ipc').exists()).to.equal(false);
        expect(wrapper.find('.requirement-item.fee').exists()).to.equal(true);
        expect(wrapper.find('.requirement-item.time').exists()).to.equal(true);
        expect(wrapper.find('#submit-start-application').attributes('value')).to.equal('Start application');
    });
    it('should preselect application types from the route query', async () => {
        const wrapper = await mountPage(mountShallow);
        const component = wrapper.vm;

        await component.$router.push({
            name: 'ApplicationStart',
            params: { compact: CompactType.PSYPACT },
            query: { types: 'tap,not-a-type' },
        });
        component.initFormInputs();

        expect(component.preselectedTypes).to.matchPattern([ApplicationType.TAP]);
        expect(component.formData.apit.value).to.equal(false);
        expect(component.formData.tap.value).to.equal(true);

        await component.$router.push({
            name: 'ApplicationStart',
            params: { compact: CompactType.PSYPACT },
            query: { types: 'apit,tap' },
        });
        component.initFormInputs();

        expect(component.selectedTypes).to.matchPattern([ApplicationType.APIT, ApplicationType.TAP]);
    });
    it('should show the E.Passport and IPC sections based on the selected types', async () => {
        const wrapper = await mountPage();
        const component = wrapper.vm;

        component.formData.apit.value = true;
        await nextTick();

        expect(wrapper.find('.requirement-item.epassport').exists()).to.equal(true);
        expect(wrapper.find('.requirement-item.ipc').exists()).to.equal(false);
        expect(wrapper.find('.requirement-item.epassport .external-link').attributes('target')).to.equal('_blank');
        expect(wrapper.find('.requirement-item.epassport .external-link').attributes('href'))
            .to.equal('https://example.com');

        component.formData.apit.value = false;
        component.formData.tap.value = true;
        await nextTick();

        expect(wrapper.find('.requirement-item.epassport').exists()).to.equal(false);
        expect(wrapper.find('.requirement-item.ipc').exists()).to.equal(true);
        expect(wrapper.find('.requirement-item.ipc .external-link').attributes('target')).to.equal('_blank');
    });
    it('should add the fees for the selected types', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage();
        const component = wrapper.vm;

        expect(component.totalFee).to.equal(0);

        component.formData.apit.value = true;
        await nextTick();

        expect(component.totalFee).to.equal(100);

        component.formData.apit.value = false;
        component.formData.tap.value = true;
        await nextTick();

        expect(component.totalFee).to.equal(50);

        component.formData.apit.value = true;
        await nextTick();

        expect(component.totalFee).to.equal(150);
        expect(component.totalFeeDisplay).to.equal('$150.00');
        expect(wrapper.find('.requirement-item.fee').text()).to.contain('$150.00');
    });
    it('should show the fee as unavailable and block submission when the application config is missing', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage();
        const component = wrapper.vm;
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');

        await store.dispatch('user/getApplicationConfigSuccess', null);
        await nextTick();

        expect(component.isFeeUnavailable).to.equal(false);
        expect(wrapper.find('.requirement-item.fee').text()).to.contain('$0.00');

        component.formData.apit.value = true;
        component.formData.licenseState.value = 'co';
        await nextTick();

        expect(component.isFeeUnavailable).to.equal(true);
        expect(wrapper.find('.fee-unavailable').attributes('role')).to.equal('alert');
        expect(wrapper.find('.requirement-item.fee').text()).to.not.contain('$');
        expect(wrapper.find('#submit-start-application').attributes('disabled')).to.not.equal(undefined);

        await component.handleSubmit();

        expect(dispatchSpy.calledWith('user/createApplicationRequestLicensee')).to.equal(false);
    });
    it('should list all states with non-participating states disabled', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage(mountShallow);
        const component = wrapper.vm;
        const { valueOptions } = component.formData.licenseState;
        const coloradoOption = valueOptions.find((option) => option.value === 'co');
        const floridaOption = valueOptions.find((option) => option.value === 'fl');
        const guamOption = valueOptions.find((option) => option.value === 'gu');

        expect(valueOptions.length).to.equal(component.stateOptions.length);
        expect(valueOptions[0].isDisabled).to.equal(true);
        expect(coloradoOption).to.matchPattern({ value: 'co', name: 'Colorado', isDisabled: false });
        expect(floridaOption).to.matchPattern({ value: 'fl', name: 'Florida (Not participating)', isDisabled: true });
        expect(guamOption.isDisabled).to.equal(true);
    });
    it('should require at least one application type and a license state on submit', async () => {
        const wrapper = await mountPage();
        const component = wrapper.vm;
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');

        await component.handleSubmit();
        await nextTick();

        expect(component.isFormValid).to.equal(false);
        expect(component.formData.tap.errorMessage).to.equal('Select APIT, TAP, or both');
        expect(wrapper.find('.type-error').text()).to.equal('Select APIT, TAP, or both');
        expect(component.formData.licenseState.errorMessage).to.not.equal('');
        expect(dispatchSpy.calledWith('user/createApplicationRequestLicensee')).to.equal(false);
    });
    it('should clear the application type error once a type is selected', async () => {
        const wrapper = await mountPage(mountShallow);
        const component = wrapper.vm;

        await component.handleSubmit();

        expect(component.formData.tap.errorMessage).to.equal('Select APIT, TAP, or both');

        component.formData.apit.value = true;
        component.validateTypeSelection();

        expect(component.formData.tap.errorMessage).to.equal('');
        expect(component.formData.tap.isValid).to.equal(true);
    });
    it('should create the application with the selected types and license state', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage();
        const component = wrapper.vm;
        const dispatchSpy = sinon.spy(component.$store, 'dispatch');
        const replaceStub = sinon.stub(component.$router, 'replace').resolves();

        component.formData.apit.value = true;
        component.formData.tap.value = true;
        component.formData.licenseState.value = 'co';
        await nextTick();

        const submitRequest = component.handleSubmit();

        await nextTick();

        expect(component.isFormLoading).to.equal(true);
        expect(component.submitLabel).to.equal('Creating application...');
        expect(wrapper.find('#submit-start-application').attributes('disabled')).to.not.equal(undefined);

        await submitRequest;
        await nextTick();

        expect(dispatchSpy.calledWith('user/createApplicationRequestLicensee', {
            data: {
                types: [ApplicationType.APIT, ApplicationType.TAP],
                licenseJurisdiction: 'co',
            },
        })).to.equal(true);
        expect(replaceStub.calledOnce).to.equal(true);
        expect(replaceStub.firstCall.args[0].name).to.equal('ApplicationChecklist');
        expect(replaceStub.firstCall.args[0].params.compact).to.equal(CompactType.PSYPACT);
        expect(replaceStub.firstCall.args[0].params.applicationId).to.match(/^[0-9a-f-]{36}$/);
        expect(component.isFormLoading).to.equal(false);
        expect(component.submitLabel).to.equal('Start application');
        expect(component.formData.submit.errorMessage).to.equal('');
    });
    it('should not redirect to the checklist if the page unmounts while creation is pending', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage(mountShallow);
        const component = wrapper.vm;
        const replaceStub = sinon.stub(component.$router, 'replace').resolves();
        let resolveCreate;

        sinon.stub(component.$store, 'dispatch').returns(new Promise((resolve) => {
            resolveCreate = resolve;
        }));
        component.formData.apit.value = true;
        component.formData.licenseState.value = 'co';
        await nextTick();

        const submitRequest = component.handleSubmit();

        wrapper.unmount();
        resolveCreate(new Application({ id: 'created-application' }));
        await submitRequest;

        expect(component.isPageActive).to.equal(false);
        expect(replaceStub.notCalled).to.equal(true);
    });
    it('should mock populate the form with both types and the first participating state', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage(mountShallow);
        const component = wrapper.vm;
        const scrollSpy = sinon.spy();
        const getElementStub = sinon.stub(document, 'getElementById').returns({
            scrollIntoView: scrollSpy,
        } as unknown as HTMLElement);

        await component.mockPopulate();

        expect(component.selectedTypes).to.matchPattern([ApplicationType.APIT, ApplicationType.TAP]);
        expect(component.formData.licenseState.value).to.equal('al');
        expect(component.isFormValid).to.equal(true);
        expect(getElementStub.calledWith('submit-start-application')).to.equal(true);
        expect(scrollSpy.calledOnceWith({ behavior: 'smooth', block: 'center' })).to.equal(true);
    });
    it('should show a create error above the button and re-enable it', async () => {
        await setPsypactCompact();

        const wrapper = await mountPage();
        const component = wrapper.vm;

        const dispatchStub = sinon.stub(component.$store, 'dispatch').callThrough();

        dispatchStub
            .withArgs('user/createApplicationRequestLicensee')
            .callsFake(() => Promise.reject(new Error('Server error')));
        component.formData.tap.value = true;
        component.formData.licenseState.value = 'co';
        await nextTick();
        await component.handleSubmit();
        await nextTick();

        expect(component.isFormLoading).to.equal(false);
        expect(component.formData.submit.errorMessage).to.equal('Server error');
        expect(wrapper.find('.input-submit-container .error').text()).to.equal('Server error');
        expect(wrapper.find('#submit-start-application').attributes('disabled')).to.equal(undefined);
        expect(wrapper.find('#submit-start-application').attributes('value')).to.equal('Start application');
    });
});
