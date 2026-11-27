//
//  ApplicationChecklist.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import sinon from 'sinon';
import { mountFull, mountShallow } from '@tests/helpers/setup';
import ApplicationChecklist from '@pages/ApplicationChecklist/ApplicationChecklist.vue';
import { CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import {
    Application,
    ApplicantSectionStatus,
    ApplicationSection
} from '@models/Application/Application.model';
import store from '@store/index';
import { nextTick } from 'vue';
import { flushPromises } from '@vue/test-utils';

use(chaiMatchPattern);

const mountChecklist = async (applicationId: string, mountFn = mountFull) => {
    const wrapper = await mountFn(ApplicationChecklist);
    const component = wrapper.vm;

    await flushPromises();
    await component.$router.push({
        name: 'ApplicationChecklist',
        params: { compact: CompactType.PSYPACT, applicationId },
    });
    await component.fetchApplication();
    await nextTick();

    return wrapper;
};

describe('ApplicationChecklist page', async () => {
    beforeEach(async () => {
        await store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: CompactType.PSYPACT }));
    });
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(ApplicationChecklist);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ApplicationChecklist).exists()).to.equal(true);
    });
    it('should fetch the application by ID from the route', async () => {
        const dispatchSpy = sinon.spy(store, 'dispatch');

        await mountChecklist('1', mountShallow);

        expect(dispatchSpy.calledWith('user/getApplicationRequestLicensee', { applicationId: '1' })).to.equal(true);
    });
    it('should display a started application with no completed sections', async () => {
        const wrapper = await mountChecklist('1');
        const component = wrapper.vm;

        expect(wrapper.find('.breadcrumb-link').text()).to.equal('Dashboard');
        expect(wrapper.find('.breadcrumb-current').text()).to.equal('/ Authorization application');
        expect(wrapper.find('.checklist-title').text()).to.equal('Application checklist');
        expect(component.progressPercent).to.equal(0);
        expect(wrapper.find('.progress-display').text()).to.equal('0 of 6 complete');
        expect(wrapper.findAll('.section-name').map((name) => name.text())).to.matchPattern([
            'Personal information',
            'Licensure history',
            'Education',
            'Conduct history',
            'Home state declaration',
            'Acknowledgements and signature',
        ]);
        expect(wrapper.find('.personalInformation .section-description').text())
            .to.equal('Name, contact, and demographic details');
        expect(wrapper.findAll('.status-pill').map((pill) => pill.text())).to.matchPattern([
            'Status: Incomplete',
            'Status: Incomplete',
            'Status: Incomplete',
            'Status: Incomplete',
            'Status: Incomplete',
            'Status: Incomplete',
        ]);
        expect(wrapper.findAll('.section-button input').map((button) => button.attributes('value')))
            .to.matchPattern(['Start', 'Start', 'Start', 'Start', 'Start', 'Start']);
        expect(wrapper.find('.section-button input').classes()).to.not.include('transparent');
        expect(wrapper.find('.section-button input').attributes('disabled')).to.equal(undefined);
        expect(wrapper.find('.continue-button input').attributes('value')).to.equal('Continue to payment');
        expect(wrapper.find('.continue-button input').attributes('disabled')).to.not.equal(undefined);
    });
    it('should enable continuing to submission when all sections are complete and the fee is waived', async () => {
        const wrapper = await mountChecklist('2');
        const component = wrapper.vm;

        expect(component.progressPercent).to.equal(100);
        expect(wrapper.find('.progress-display').text()).to.equal('6 of 6 complete');
        expect(wrapper.findAll('.status-pill.complete').length).to.equal(6);
        expect(wrapper.findAll('.section-button input').map((button) => button.attributes('value')))
            .to.matchPattern(['Edit', 'Edit', 'Edit', 'Edit', 'Edit', 'Edit']);
        expect(wrapper.find('.section-button input').classes()).to.include('transparent');
        expect(component.isContinueEnabled).to.equal(true);
        expect(wrapper.find('.continue-button input').attributes('value')).to.equal('Continue to submission');
        expect(wrapper.find('.continue-button input').attributes('disabled')).to.equal(undefined);
    });
    it('should display sections that need attention', async () => {
        const wrapper = await mountChecklist('4');
        const component = wrapper.vm;

        expect(component.progressPercent).to.equal(83);
        expect(wrapper.find('.progress-display').text()).to.equal('5 of 6 complete');
        expect(wrapper.find('.education .status-pill').text()).to.equal('Status: Needs attention');
        expect(wrapper.find('.education .status-pill').classes()).to.include('attention');
        expect(wrapper.find('.education .section-button input').attributes('value')).to.equal('Edit');
        expect(wrapper.find('.education .section-button input').attributes('disabled')).to.equal(undefined);
        expect(wrapper.find('.continue-button input').attributes('disabled')).to.not.equal(undefined);
    });
    it('should disable all actions when the application is not editable by the applicant', async () => {
        const wrapper = await mountChecklist('3');
        const component = wrapper.vm;

        expect(component.isEditable).to.equal(false);
        expect(component.isContinueEnabled).to.equal(false);
        expect(wrapper.findAll('.section-button input').every((button) =>
            button.attributes('disabled') !== undefined)).to.equal(true);
        expect(wrapper.find('.continue-button input').attributes('disabled')).to.not.equal(undefined);
    });
    it('should display a load error when the application cannot be found', async () => {
        const wrapper = await mountChecklist('not-a-real-application');
        const component = wrapper.vm;

        expect(component.isLoadError).to.equal(true);
        expect(wrapper.find('.checklist-load-error').attributes('role')).to.equal('alert');
        expect(wrapper.find('.load-error-message').text())
            .to.equal('We couldn\'t load this application. Please try again later.');
        expect(wrapper.find('.checklist-load-error .text-link').text()).to.equal('Back to dashboard');
        expect(wrapper.find('.checklist-card').exists()).to.equal(false);
        expect(wrapper.find('.checklist-footer').exists()).to.equal(false);
    });
    it('should reset and refetch when the application ID changes', async () => {
        const wrapper = await mountChecklist('2', mountShallow);
        const component = wrapper.vm;

        expect(component.application?.id).to.equal('2');

        await component.$router.push({
            name: 'ApplicationChecklist',
            params: { compact: CompactType.PSYPACT, applicationId: 'not-a-real-application' },
        });
        await nextTick();

        expect(component.hasFetched).to.equal(false);
        expect(component.fetchedApplication).to.equal(null);

        await component.fetchApplication();

        expect(component.fetchedApplication).to.equal(null);
        expect(component.application).to.equal(null);
        expect(component.isLoadError).to.equal(true);
    });
    it('should ignore a fetch result for an application ID that is no longer current', async () => {
        const wrapper = await mountChecklist('1', mountShallow);
        const component = wrapper.vm;
        let resolveStaleFetch;
        const dispatchStub = sinon.stub(component.$store, 'dispatch').returns(new Promise((resolve) => {
            resolveStaleFetch = resolve;
        }));
        const staleRequest = component.fetchApplication();

        dispatchStub.restore();
        await component.$router.push({
            name: 'ApplicationChecklist',
            params: { compact: CompactType.PSYPACT, applicationId: '2' },
        });
        await component.fetchApplication();
        resolveStaleFetch(new Application({ id: '1' }));
        await staleRequest;

        expect(component.applicationId).to.equal('2');
        expect(component.fetchedApplication?.id).to.equal('2');
    });
    it('should map applicant section statuses to status classes', async () => {
        const wrapper = await mountShallow(ApplicationChecklist);
        const component = wrapper.vm;

        expect(component.getStatusClass(ApplicantSectionStatus.INCOMPLETE)).to.equal('incomplete');
        expect(component.getStatusClass(ApplicantSectionStatus.COMPLETE)).to.equal('complete');
        expect(component.getStatusClass(ApplicantSectionStatus.NEEDS_ATTENTION)).to.equal('attention');
        expect(component.getStatusClass(ApplicantSectionStatus.CONFIRM_DETAILS)).to.equal('attention');
    });
    it('should log section and continue actions', async () => {
        const wrapper = await mountChecklist('2', mountShallow);
        const component = wrapper.vm;
        const logStub = sinon.stub(console, 'log');

        component.openSection(component.sections[2]);
        component.continueApplication();
        logStub.restore();

        expect(logStub.firstCall.args).to.matchPattern([
            'open application section',
            '2',
            ApplicationSection.EDUCATION,
        ]);
        expect(logStub.secondCall.args).to.matchPattern(['continue application', '2']);
    });
});
