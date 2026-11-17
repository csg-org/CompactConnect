//
//  ApplicationStatusCard.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/10/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import sinon from 'sinon';
import { mountShallow } from '@tests/helpers/setup';
import store from '@store/index';
import { CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import ApplicationStatusCard from '@components/ApplicationStatusCard/ApplicationStatusCard.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import { serverDatetimeFormat } from '@/app.config';
import {
    Application,
    ApplicationType,
    ApplicationStatus,
    ApplicantSectionStatus
} from '@models/Application/Application.model';
import moment from 'moment';

use(chaiMatchPattern);

describe('ApplicationStatusCard component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ApplicationStatusCard).exists()).to.equal(true);
    });
    it('should display a started application', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT],
                    status: ApplicationStatus.STARTED,
                    personalInformation: {
                        applicantStatus: ApplicantSectionStatus.COMPLETE,
                    },
                    licenseHistory: {
                        applicantStatus: ApplicantSectionStatus.COMPLETE,
                    },
                }),
            },
        });
        const component = wrapper.vm;
        const { stepStates } = component;

        expect(component.title).to.equal('Your APIT application');
        expect(component.summary).to.equal('2 of 6 sections complete');
        expect(component.steps).to.matchPattern([
            {
                number: 1,
                label: 'Started',
                state: stepStates.CURRENT,
                isCurrent: true,
            },
            {
                number: 2,
                label: 'Submitted',
                state: stepStates.UPCOMING,
                isCurrent: false,
            },
            {
                number: 3,
                label: 'Staff review',
                state: stepStates.UPCOMING,
                isCurrent: false,
            },
            {
                number: 4,
                label: 'Decision',
                state: stepStates.UPCOMING,
                isCurrent: false,
            },
        ]);
        expect(component.notes).to.matchPattern([]);
        expect(component.updateButtonLabel).to.equal('Continue application');
        expect(wrapper.findComponent(InputButton).exists()).to.equal(true);
        expect(wrapper.find('.application-status-card-container').classes()).to.matchPattern([
            'application-status-card-container',
        ]);
    });
    it('should display an in review application', async () => {
        const application = new Application({
            types: [ApplicationType.TAP],
            submitted: moment().subtract(1, 'week').format(serverDatetimeFormat),
            status: ApplicationStatus.STAFF_REVIEW,
        });
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application,
            },
        });
        const component = wrapper.vm;
        const { stepStates } = component;

        expect(component.title).to.equal('Your TAP application');
        expect(component.summary).to.equal(`Your application was submitted on ${application.submittedDateDisplay()}. It is now in review and you will be notified of a final decision.`);
        expect(component.steps).to.matchPattern([
            {
                number: 1,
                label: 'Started',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 2,
                label: 'Submitted',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 3,
                label: 'Staff review',
                state: stepStates.CURRENT,
                isCurrent: true,
            },
            {
                number: 4,
                label: 'Decision',
                state: stepStates.UPCOMING,
                isCurrent: false,
            },
        ]);
        expect(component.notes).to.matchPattern([]);
        expect(wrapper.findComponent(InputButton).exists()).to.equal(false);
    });
    it('should display a needs attention application', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT],
                    status: ApplicationStatus.AWAITING_APPLICANT,
                    conductHistory: {
                        applicantStatus: ApplicantSectionStatus.NEEDS_ATTENTION,
                        reviews: [{ notesForApplicant: 'test-notesForApplicant' }],
                    },
                }),
            },
        });
        const component = wrapper.vm;
        const { stepStates } = component;

        expect(component.summary).to.equal('');
        expect(component.steps).to.matchPattern([
            {
                number: 1,
                label: 'Started',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 2,
                label: 'Submitted',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 3,
                label: 'Needs attention',
                state: stepStates.ATTENTION,
                isCurrent: true,
            },
            {
                number: 4,
                label: 'Decision',
                state: stepStates.UPCOMING,
                isCurrent: false,
            },
        ]);
        expect(component.notesTitle).to.equal('Issue with your application');
        expect(component.notes).to.matchPattern(['test-notesForApplicant']);
        expect(component.updateButtonLabel).to.equal('Update application');
        expect(wrapper.findComponent(InputButton).exists()).to.equal(true);
        expect(wrapper.find('.application-status-card-container').classes()).to.matchPattern([
            'application-status-card-container',
            'needs-attention',
        ]);
    });
    it('should display an approved application', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT],
                    status: ApplicationStatus.APPROVED,
                }),
            },
        });
        const component = wrapper.vm;
        const { stepStates } = component;

        expect(component.summary).to.equal('Your application was approved.');
        expect(component.steps).to.matchPattern([
            {
                number: 1,
                label: 'Started',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 2,
                label: 'Submitted',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 3,
                label: 'Staff review',
                state: stepStates.COMPLETE,
                isCurrent: false,
            },
            {
                number: 4,
                label: 'Approved',
                state: stepStates.APPROVED,
                isCurrent: true,
            },
        ]);
        expect(component.notes).to.matchPattern([]);
        expect(wrapper.findComponent(InputButton).exists()).to.equal(false);
    });
    it('should display a rejected application', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT],
                    status: ApplicationStatus.REJECTED,
                    reviews: [{ notesForApplicant: 'test-notesForApplicant' }],
                }),
            },
        });
        const component = wrapper.vm;
        const { stepStates } = component;

        expect(component.summary).to.equal('Your application was rejected.');
        expect(component.steps[3]).to.matchPattern({
            number: 4,
            label: 'Rejected',
            state: stepStates.REJECTED,
            isCurrent: true,
        });
        expect(component.notesTitle).to.equal('Reviewer notes');
        expect(component.notes).to.matchPattern(['test-notesForApplicant']);
        expect(wrapper.findComponent(InputButton).exists()).to.equal(false);
        expect(wrapper.find('.application-status-card-container').classes()).to.matchPattern([
            'application-status-card-container',
            'rejected',
        ]);
    });
    it('should display a deactivated application', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT],
                    status: ApplicationStatus.DEACTIVATED,
                }),
            },
        });
        const component = wrapper.vm;
        const { stepStates } = component;

        expect(component.summary).to.equal('Your application was deactivated.');
        expect(component.steps[3]).to.matchPattern({
            number: 4,
            label: 'Deactivated',
            state: stepStates.REJECTED,
            isCurrent: true,
        });
        expect(wrapper.findComponent(InputButton).exists()).to.equal(false);
        expect(wrapper.find('.application-status-card-container').classes()).to.matchPattern([
            'application-status-card-container',
            'rejected',
        ]);
    });
    it('should display the fee waived label when all application types are payment compensated', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT],
                    paymentCompensated: [ApplicationType.APIT],
                }),
            },
        });

        expect(wrapper.find('.fee-waived-pill').exists()).to.equal(true);
    });
    it('should not display the fee waived label when some application types are not payment compensated', async () => {
        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({
                    types: [ApplicationType.APIT, ApplicationType.TAP],
                    paymentCompensated: [ApplicationType.APIT],
                }),
            },
        });

        expect(wrapper.find('.fee-waived-pill').exists()).to.equal(false);
    });
    it('should navigate to the application checklist when updating the application', async () => {
        await store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: CompactType.PSYPACT }));

        const wrapper = await mountShallow(ApplicationStatusCard, {
            props: {
                application: new Application({ id: 'test-application-id' }),
            },
        });
        const component = wrapper.vm;
        const pushStub = sinon.stub(component.$router, 'push').resolves();

        component.updateApplication();

        expect(pushStub.calledOnce).to.equal(true);
        expect(pushStub.firstCall.args[0]).to.matchPattern({
            name: 'ApplicationChecklist',
            params: {
                compact: CompactType.PSYPACT,
                applicationId: 'test-application-id',
            },
        });
    });
});
