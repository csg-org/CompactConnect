//
//  Application.model.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/29/2026.
//

import chaiMatchPattern from 'chai-match-pattern';
import { use, expect } from 'chai';
import { serverDateFormat, serverDatetimeFormat, displayDateFormat } from '@/app.config';
import {
    Application,
    ApplicationType,
    ApplicationStatus,
    ApplicantSectionStatus,
    ReviewSectionStatus,
    ReviewerType,
    ApplicationLicenseStatus,
    ApplicationSerializer
} from '@models/Application/Application.model';
import i18n from '@/i18n';
import moment from 'moment';

use(chaiMatchPattern);

describe('Application model', () => {
    before(() => {
        const { tm: $tm, t: $t } = i18n.global;

        (window as any).Vue = {
            config: {
                globalProperties: {
                    $tm,
                    $t,
                }
            }
        };
        i18n.global.locale.value = 'en';
    });
    it('should create an Application model with expected defaults', () => {
        const application = new Application();

        // Test field values
        expect(application).to.be.an.instanceof(Application);
        expect(application.id).to.equal(null);
        expect(application.created).to.equal(null);
        expect(application.submitted).to.equal(null);
        expect(application.completed).to.equal(null);
        expect(application.types).to.matchPattern([]);
        expect(application.isRenewal).to.equal(false);
        expect(application.status).to.equal(ApplicationStatus.STARTED);
        expect(application.reviews).to.matchPattern([]);
        expect(application.attestations).to.matchPattern([]);
        expect(application.paymentCompensated).to.matchPattern([]);
        expect(application.personalInformation).to.matchPattern({
            applicantStatus: ApplicantSectionStatus.INCOMPLETE,
            reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
            reviews: [],
            firstName: null,
            middleName: null,
            lastName: null,
            suffix: null,
            phone: null,
            altPhone: null,
            dob: null,
            ssnLastFour: null,
            npi: null,
            gender: null,
            professionalName: null,
            citizenship: null,
            placeOfBirth: null,
            languages: [],
            mailingAddress1: null,
            mailingAddress2: null,
            mailingCity: null,
            mailingState: null,
            mailingZip: null,
        });
        expect(application.licenseHistory).to.matchPattern({
            applicantStatus: ApplicantSectionStatus.INCOMPLETE,
            reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
            reviews: [],
            ePassport: {
                mobilityNumber: null,
                issueDate: null,
            },
            ipc: {
                mobilityNumber: null,
                issueDate: null,
            },
            licenses: [],
        });
        expect(application.education).to.matchPattern({
            applicantStatus: ApplicantSectionStatus.INCOMPLETE,
            reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
            reviews: [],
            nameAtTime: null,
            institution: null,
            city: null,
            state: null,
            degreeType: null,
            program: null,
            department: null,
            conferredDate: null,
            isCompleted: false,
            accreditingBody: null,
            accreditingYear: null,
            isAccreditedByAuthority: false,
            isProgramEquivalent: false,
            accreditingContact: null,
            hasResidence: false,
            transcripts: [],
        });
        expect(application.conductHistory).to.matchPattern({
            applicantStatus: ApplicantSectionStatus.INCOMPLETE,
            reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
            reviews: [],
            attestations: [],
            convictions: [],
            notes: null,
            documents: [],
        });
        expect(application.homeState).to.matchPattern({
            applicantStatus: ApplicantSectionStatus.INCOMPLETE,
            reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
            reviews: [],
            applicationTypes: [],
        });
        expect(application.acknowledgements).to.matchPattern({
            applicantStatus: ApplicantSectionStatus.INCOMPLETE,
            reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
            reviews: [],
            attestations: [],
            signatureName: null,
        });

        // Test methods
        expect(application.createdDateDisplay()).to.equal('');
        expect(application.submittedDateDisplay()).to.equal('');
        expect(application.completedDateDisplay()).to.equal('');
        expect(application.typeDisplay()).to.equal('');
        expect(application.getStatusDisplay('')).to.equal('Unknown');
        expect(application.applicationStatusDisplay()).to.equal('Started');
        expect(application.areAllSectionsCompleteForApplicant()).to.equal(false);
    });
    it('should create an Application model with specific values', () => {
        const review = {
            assignedDate: 'test-assignedDate',
            reviewer: {
                id: 'test-reviewer-id',
                firstName: 'test-reviewer-firstName',
                lastName: 'test-reviewer-lastName',
            },
            reviewerType: ReviewerType.FIRST_REVIEWER,
            reviewerStatus: ReviewSectionStatus.APPROVED,
            reviewDate: 'test-reviewDate',
            notesForApplicant: 'test-notesForApplicant',
            notesForReviewers: 'test-notesForReviewers',
        };
        const attestation = {
            attestationId: 'test-attestationId',
            version: '1',
        };
        const file = {
            filename: 'test-filename',
            sizeBytes: 1,
            downloadUri: 'test-downloadUri',
        };
        const data = {
            id: 'test-id',
            created: 'test-created',
            submitted: 'test-submitted',
            completed: 'test-completed',
            types: [ApplicationType.APIT, ApplicationType.TAP],
            isRenewal: true,
            status: ApplicationStatus.AWAITING_APPLICANT,
            reviews: [review],
            attestations: [attestation],
            paymentCompensated: [ApplicationType.APIT],
            personalInformation: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                firstName: 'test-firstName',
                middleName: 'test-middleName',
                lastName: 'test-lastName',
                suffix: 'test-suffix',
                phone: 'test-phone',
                altPhone: 'test-altPhone',
                dob: 'test-dob',
                ssnLastFour: 'test-ssnLastFour',
                npi: 'test-npi',
                gender: 'test-gender',
                professionalName: 'test-professionalName',
                citizenship: 'test-citizenship',
                placeOfBirth: 'test-placeOfBirth',
                languages: ['test-language'],
                mailingAddress1: 'test-mailingAddress1',
                mailingAddress2: 'test-mailingAddress2',
                mailingCity: 'test-mailingCity',
                mailingState: 'test-mailingState',
                mailingZip: 'test-mailingZip',
            },
            licenseHistory: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                ePassport: {
                    mobilityNumber: 'test-ePassport-mobilityNumber',
                    issueDate: 'test-ePassport-issueDate',
                },
                ipc: {
                    mobilityNumber: 'test-ipc-mobilityNumber',
                    issueDate: 'test-ipc-issueDate',
                },
                licenses: [{
                    state: 'test-state',
                    issueDate: 'test-issueDate',
                    licenseNumber: 'test-licenseNumber',
                    status: ApplicationLicenseStatus.ACTIVE,
                }],
            },
            education: {
                applicantStatus: ApplicantSectionStatus.NEEDS_ATTENTION,
                reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
                reviews: [review],
                nameAtTime: 'test-nameAtTime',
                institution: 'test-institution',
                city: 'test-city',
                state: 'test-state',
                degreeType: 'test-degreeType',
                program: 'test-program',
                department: 'test-department',
                conferredDate: 'test-conferredDate',
                isCompleted: true,
                accreditingBody: 'test-accreditingBody',
                accreditingYear: 'test-accreditingYear',
                isAccreditedByAuthority: true,
                isProgramEquivalent: true,
                accreditingContact: {
                    name: 'test-name',
                    email: 'test-email',
                    city: 'test-city',
                    state: 'test-state',
                    zip: 'test-zip',
                    phone: 'test-phone',
                    attestations: [attestation],
                },
                hasResidence: true,
                transcripts: [file],
            },
            conductHistory: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                attestations: [attestation],
                convictions: [{
                    charge: 'test-charge',
                    location: 'test-location',
                    date: 'test-date',
                    type: 'test-type',
                }],
                notes: 'test-notes',
                documents: [file],
            },
            homeState: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                applicationTypes: [{
                    applicationType: ApplicationType.APIT,
                    state: 'test-state',
                    startDate: 'test-startDate',
                    isActiveMilitary: true,
                    militaryDocuments: [file],
                    attestations: [attestation],
                }],
            },
            acknowledgements: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                attestations: [attestation],
                signatureName: 'test-signatureName',
            },
        };
        const application = new Application(data);

        // Test field values
        expect(application).to.be.an.instanceof(Application);
        expect(application.id).to.equal(data.id);
        expect(application.created).to.equal(data.created);
        expect(application.submitted).to.equal(data.submitted);
        expect(application.completed).to.equal(data.completed);
        expect(application.types).to.matchPattern(data.types);
        expect(application.isRenewal).to.equal(data.isRenewal);
        expect(application.status).to.equal(data.status);
        expect(application.reviews).to.matchPattern(data.reviews);
        expect(application.attestations).to.matchPattern(data.attestations);
        expect(application.paymentCompensated).to.matchPattern(data.paymentCompensated);
        expect(application.personalInformation).to.matchPattern(data.personalInformation);
        expect(application.licenseHistory).to.matchPattern(data.licenseHistory);
        expect(application.education).to.matchPattern(data.education);
        expect(application.conductHistory).to.matchPattern(data.conductHistory);
        expect(application.homeState).to.matchPattern(data.homeState);
        expect(application.acknowledgements).to.matchPattern(data.acknowledgements);

        // Test methods
        expect(application.createdDateDisplay()).to.equal('Invalid date');
        expect(application.submittedDateDisplay()).to.equal('Invalid date');
        expect(application.completedDateDisplay()).to.equal('Invalid date');
        expect(application.typeDisplay()).to.equal('APIT + TAP');
        expect(application.getStatusDisplay(ApplicantSectionStatus.NEEDS_ATTENTION)).to.equal('Needs attention');
        expect(application.applicationStatusDisplay()).to.equal('Awaiting applicant');
        expect(application.areAllSectionsCompleteForApplicant()).to.equal(false);
    });
    it('should create an Application model with specific values through serializer', () => {
        const review = {
            assignedDate: moment().subtract(3, 'days').format(serverDatetimeFormat),
            reviewer: {
                id: 'test-reviewer-id',
                firstName: 'test-reviewer-firstName',
                lastName: 'test-reviewer-lastName',
            },
            reviewerType: ReviewerType.FIRST_REVIEWER,
            reviewerStatus: ReviewSectionStatus.APPROVED,
            reviewDate: moment().subtract(1, 'day').format(serverDatetimeFormat),
            notesForApplicant: 'test-notesForApplicant',
            notesForReviewers: 'test-notesForReviewers',
        };
        const attestation = {
            attestationId: 'test-attestationId',
            version: '1',
        };
        const file = {
            filename: 'test-filename.pdf',
            sizeBytes: 1000,
            downloadUri: 'https://example.com/test-filename.pdf',
        };
        const data = {
            id: 'test-id',
            created: moment().subtract(2, 'weeks').format(serverDatetimeFormat),
            submitted: moment().subtract(1, 'week').format(serverDatetimeFormat),
            completed: moment().subtract(1, 'day').format(serverDatetimeFormat),
            types: [ApplicationType.APIT, ApplicationType.TAP],
            isRenewal: true,
            status: ApplicationStatus.APPROVED,
            reviews: [review],
            attestations: [attestation],
            paymentCompensated: [ApplicationType.APIT],
            personalInformation: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                firstName: 'test-firstName',
                middleName: 'test-middleName',
                lastName: 'test-lastName',
                suffix: 'test-suffix',
                phone: '+12223334444',
                altPhone: '+13334445555',
                dob: moment().subtract(50, 'years').format(serverDateFormat),
                ssnLastFour: '1111',
                npi: '1111111111',
                gender: 'test-gender',
                professionalName: 'test-professionalName',
                citizenship: 'us',
                placeOfBirth: 'test-placeOfBirth',
                languages: ['en', 'es'],
                mailingAddress1: 'test-mailingAddress1',
                mailingAddress2: 'test-mailingAddress2',
                mailingCity: 'test-mailingCity',
                mailingState: 'co',
                mailingZip: '11111',
            },
            licenseHistory: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                ePassport: {
                    mobilityNumber: '1111111',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                },
                ipc: {
                    mobilityNumber: '2222222',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                },
                licenses: [{
                    state: 'co',
                    issueDate: moment().subtract(6, 'months').format(serverDateFormat),
                    licenseNumber: '1111111111',
                    status: ApplicationLicenseStatus.ACTIVE,
                }],
            },
            education: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                nameAtTime: 'test-nameAtTime',
                institution: 'test-institution',
                city: 'test-city',
                state: 'co',
                degreeType: 'phd',
                program: 'test-program',
                department: 'test-department',
                conferredDate: moment().subtract(7, 'months').format(serverDateFormat),
                isCompleted: true,
                accreditingBody: 'test-accreditingBody',
                accreditingYear: moment().subtract(7, 'months').format('YYYY'),
                isAccreditedByAuthority: true,
                isProgramEquivalent: true,
                accreditingContact: {
                    name: 'test-name',
                    email: 'test@example.com',
                    city: 'test-city',
                    state: 'co',
                    zip: '11111',
                    phone: '+12223334444',
                    attestations: [attestation],
                },
                hasResidence: true,
                transcripts: [file],
            },
            conductHistory: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                attestations: [attestation],
                convictions: [{
                    charge: 'test-charge',
                    location: 'test-location',
                    date: moment().subtract(30, 'years').format(serverDateFormat),
                    type: 'test-type',
                }],
                notes: 'test-notes',
                documents: [file],
            },
            homeState: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                applicationTypes: [{
                    applicationType: ApplicationType.APIT,
                    state: 'co',
                    startDate: moment().subtract(6, 'months').format(serverDateFormat),
                    isActiveMilitary: true,
                    militaryDocuments: [file],
                    attestations: [attestation],
                }],
            },
            acknowledgements: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                reviewStatus: ReviewSectionStatus.APPROVED,
                reviews: [review],
                attestations: [attestation],
                signatureName: 'test-signatureName',
            },
        };
        const application = ApplicationSerializer.fromServer(data);

        // Test field values
        expect(application).to.be.an.instanceof(Application);
        expect(application.id).to.equal(data.id);
        expect(application.created).to.equal(data.created);
        expect(application.submitted).to.equal(data.submitted);
        expect(application.completed).to.equal(data.completed);
        expect(application.types).to.matchPattern(data.types);
        expect(application.isRenewal).to.equal(data.isRenewal);
        expect(application.status).to.equal(data.status);
        expect(application.reviews).to.matchPattern(data.reviews);
        expect(application.attestations).to.matchPattern(data.attestations);
        expect(application.paymentCompensated).to.matchPattern(data.paymentCompensated);
        expect(application.personalInformation).to.matchPattern(data.personalInformation);
        expect(application.licenseHistory).to.matchPattern(data.licenseHistory);
        expect(application.education).to.matchPattern(data.education);
        expect(application.conductHistory).to.matchPattern(data.conductHistory);
        expect(application.homeState).to.matchPattern(data.homeState);
        expect(application.acknowledgements).to.matchPattern(data.acknowledgements);

        // Test methods
        expect(application.createdDateDisplay()).to.equal(
            moment(data.created, serverDatetimeFormat).format(displayDateFormat)
        );
        expect(application.submittedDateDisplay()).to.equal(
            moment(data.submitted, serverDatetimeFormat).format(displayDateFormat)
        );
        expect(application.completedDateDisplay()).to.equal(
            moment(data.completed, serverDatetimeFormat).format(displayDateFormat)
        );
        expect(application.typeDisplay()).to.equal('APIT + TAP');
        expect(application.getStatusDisplay(ReviewSectionStatus.PENDING)).to.equal('Pending');
        expect(application.applicationStatusDisplay()).to.equal('Approved');
        expect(application.areAllSectionsCompleteForApplicant()).to.equal(true);
    });
    it('should create an Application model with section defaults through serializer when server values are missing', () => {
        const application = ApplicationSerializer.fromServer({});
        const defaultApplication = new Application();

        // Test field values
        expect(application).to.be.an.instanceof(Application);
        expect(application.types).to.matchPattern([]);
        expect(application.isRenewal).to.equal(false);
        expect(application.status).to.equal(ApplicationStatus.STARTED);
        expect(application.reviews).to.matchPattern([]);
        expect(application.attestations).to.matchPattern([]);
        expect(application.paymentCompensated).to.matchPattern([]);
        expect(application.personalInformation).to.matchPattern(defaultApplication.personalInformation);
        expect(application.licenseHistory).to.matchPattern(defaultApplication.licenseHistory);
        expect(application.education).to.matchPattern(defaultApplication.education);
        expect(application.conductHistory).to.matchPattern(defaultApplication.conductHistory);
        expect(application.homeState).to.matchPattern(defaultApplication.homeState);
        expect(application.acknowledgements).to.matchPattern(defaultApplication.acknowledgements);
    });
    it('should create an Application model with partial sections merged over section defaults', () => {
        const application = new Application({
            education: {
                applicantStatus: ApplicantSectionStatus.COMPLETE,
                institution: 'test-institution',
            },
        });

        // Test field values
        expect(application.education?.applicantStatus).to.equal(ApplicantSectionStatus.COMPLETE);
        expect(application.education?.institution).to.equal('test-institution');
        expect(application.education?.reviewStatus).to.equal(ReviewSectionStatus.AWAITING_APPLICANT);
        expect(application.education?.transcripts).to.matchPattern([]);
        expect(application.education?.accreditingContact).to.equal(null);
    });
    it('should create Application models that do not share section defaults', () => {
        const application1 = new Application();
        const application2 = new Application();

        // Test field values
        expect(application1.education).to.not.equal(application2.education);
        expect(application1.education?.transcripts).to.not.equal(application2.education?.transcripts);
    });
    it('should create an Application model with an unknown type display fallback', () => {
        const application = new Application({
            types: ['test-type' as ApplicationType],
        });

        // Test methods
        expect(application.typeDisplay()).to.equal('UKWN');
    });
    it('should serialize an Application for transmission to server', () => {
        const application = new Application({
            id: 'test-id',
        });
        const transmit = ApplicationSerializer.toServer(application);

        expect(transmit.id).to.equal(application.id);
    });
});
