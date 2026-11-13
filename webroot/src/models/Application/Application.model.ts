//
//  Application.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/29/2026.
//

/* eslint-disable max-classes-per-file */
import { deleteUndefinedProperties } from '@models/_helpers';
import { dateDisplay } from '@models/_formatters/date';
import { StatsigClient } from '@statsig/js-client';

export enum ApplicationType {
    APIT = 'apit',
    TAP = 'tap',
}

export enum ApplicationStatus {
    STARTED = 'started',
    SUBMITTED = 'submitted',
    STAFF_REVIEW = 'staff-review',
    FIRST_REVIEW = 'first-review',
    SECOND_REVIEW = 'second-review',
    FINAL_REVIEW = 'final-review',
    COMMITTEE_REVIEW = 'committee-review',
    AWAITING_APPLICANT = 'awaiting-applicant',
    APPROVED = 'approved',
    REJECTED = 'rejected',
    DEACTIVATED = 'deactivated',
}

export enum ApplicantSectionStatus {
    INCOMPLETE = 'incomplete',
    COMPLETE = 'complete',
    NEEDS_ATTENTION = 'needs-attention',
    CONFIRM_DETAILS = 'confirm-details',
}

export enum ReviewSectionStatus {
    PENDING = 'pending',
    AWAITING_APPLICANT = 'awaiting-applicant',
    APPROVED = 'approved',
    REJECTED = 'rejected',
}

export enum ReviewerType {
    FIRST_REVIEWER = 'first-reviewer',
    SECOND_REVIEWER = 'second-reviewer',
    FINAL_REVIEWER = 'final-reviewer',
}

export interface ApplicationReview {
    assignedDate?: string | null;
    reviewer?: {
        id?: string | null,
        firstName?: string | null;
        lastName?: string | null;
    };
    reviewerType?: ReviewerType;
    reviewerStatus?: ApplicationStatus | ReviewSectionStatus;
    reviewDate?: string | null;
    notesForApplicant?: string | null;
    notesForReviewers?: string | null;
}

export interface ApplicationAttestation {
    attestationId?: string | null;
    version?: string | number | null;
}

export enum ApplicationLicenseStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
}

export interface ApplicationLicense {
    state?: string | null;
    issueDate?: string | null;
    licenseNumber?: string | null;
    status?: ApplicationLicenseStatus;
}

export interface ApplicationFile {
    filename?: string | null;
    sizeBytes?: number | null;
    downloadUri?: string | null;
}

export interface ApplicationAccreditingContact {
    name?: string | null,
    email?: string | null,
    city?: string | null,
    state?: string | null,
    zip?: string | null,
    phone?: string | null,
    attestations?: Array<ApplicationAttestation>;
}

export interface ApplicationConductConviction {
    charge?: string | null;
    location?: string | null;
    date?: string | null;
    type?: string | null;
}

export interface ApplicationHomeState {
    applicationType?: ApplicationType;
    state?: string | null;
    startDate?: string | null;
    isActiveMilitary?: boolean;
    militaryDocuments?: Array<ApplicationFile>;
    attestations?: Array<ApplicationAttestation>;
}

// ========================================================
// =                       Interface                      =
// ========================================================
export interface InterfaceApplicationCreate {
    id?: string | null;
    created?: string | null;
    submitted?: string | null;
    completed?: string | null;
    types?: Array<ApplicationType>;
    isRenewal?: boolean;
    status?: ApplicationStatus;
    reviews?: Array<ApplicationReview>;
    attestations?: Array<ApplicationAttestation>;
    paymentCompensated?: Array<ApplicationType>;
    personalInformation?: {
        applicantStatus: ApplicantSectionStatus,
        reviewStatus?: ReviewSectionStatus;
        reviews?: Array<ApplicationReview>;
        firstName?: string | null;
        middleName?: string | null;
        lastName?: string | null;
        suffix?: string | null;
        phone?: string | null;
        altPhone?: string | null;
        dob?: string | null;
        ssnLastFour?: string | null;
        npi?: string | null;
        gender?: string | null;
        professionalName?: string | null;
        citizenship?: string | null;
        placeOfBirth?: string | null;
        languages?: Array<string>;
        mailingAddress1?: string | null;
        mailingAddress2?: string | null;
        mailingCity?: string | null;
        mailingState?: string | null;
        mailingZip?: string | null;
    };
    licenseHistory?: {
        applicantStatus: ApplicantSectionStatus,
        reviewStatus?: ReviewSectionStatus;
        reviews?: Array<ApplicationReview>;
        ePassport?: {
            mobilityNumber?: string | null,
            issueDate?: string | null,
        };
        ipc?: {
            mobilityNumber?: string | null,
            issueDate?: string | null,
        };
        licenses?: Array<ApplicationLicense>;
    };
    education?: {
        applicantStatus: ApplicantSectionStatus,
        reviewStatus?: ReviewSectionStatus;
        reviews?: Array<ApplicationReview>;
        nameAtTime?: string | null;
        institution?: string | null;
        city?: string | null;
        state?: string | null;
        degreeType?: string | null;
        program?: string | null;
        department?: string | null;
        conferredDate?: string | null;
        isCompleted?: boolean;
        accreditingBody?: string | null;
        accreditingYear?: string | null;
        isAccreditedByAuthority?: boolean;
        isProgramEquivalent?: boolean;
        accreditingContact?: ApplicationAccreditingContact | null;
        hasResidence?: boolean;
        transcripts?: Array<ApplicationFile>;
    };
    conductHistory?: {
        applicantStatus: ApplicantSectionStatus,
        reviewStatus?: ReviewSectionStatus;
        reviews?: Array<ApplicationReview>;
        attestations?: Array<ApplicationAttestation>;
        convictions?: Array<ApplicationConductConviction>;
        notes?: string | null;
        documents?: Array<ApplicationFile>;
    };
    homeState?: {
        applicantStatus: ApplicantSectionStatus,
        reviewStatus?: ReviewSectionStatus;
        reviews?: Array<ApplicationReview>;
        applicationTypes?: Array<ApplicationHomeState>;
    };
    acknowledgements?: {
        applicantStatus: ApplicantSectionStatus,
        reviewStatus?: ReviewSectionStatus;
        reviews?: Array<ApplicationReview>;
        attestations?: Array<ApplicationAttestation>;
        signatureName?: string | null;
    };
}

// ========================================================
// =                        Model                         =
// ========================================================
const APPLICATION_SECTION_KEYS = [
    'personalInformation',
    'licenseHistory',
    'education',
    'conductHistory',
    'homeState',
    'acknowledgements',
];

export class Application implements InterfaceApplicationCreate {
    public $tm?: any = () => [];
    public $features?: StatsigClient | null = null;
    public id? = null;
    public created? = null;
    public submitted? = null;
    public completed? = null;
    public types? = [];
    public isRenewal? = false;
    public status? = ApplicationStatus.STARTED;
    public reviews? = [];
    public attestations? = [];
    public paymentCompensated? = [];
    public personalInformation? = {
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
    };
    public licenseHistory? = { // eslint-disable-line lines-between-class-members
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
    };
    public education? = { // eslint-disable-line lines-between-class-members
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
    };
    public conductHistory? = { // eslint-disable-line lines-between-class-members
        applicantStatus: ApplicantSectionStatus.INCOMPLETE,
        reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
        reviews: [],
        attestations: [],
        convictions: [],
        notes: null,
        documents: [],
    };
    public homeState? = { // eslint-disable-line lines-between-class-members
        applicantStatus: ApplicantSectionStatus.INCOMPLETE,
        reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
        reviews: [],
        applicationTypes: [],
    };
    public acknowledgements? = { // eslint-disable-line lines-between-class-members
        applicantStatus: ApplicantSectionStatus.INCOMPLETE,
        reviewStatus: ReviewSectionStatus.AWAITING_APPLICANT,
        reviews: [],
        attestations: [],
        signatureName: null,
    };

    constructor(data?: InterfaceApplicationCreate) {
        const cleanDataObject: any = deleteUndefinedProperties(data);
        const global = window as any;
        const { $tm, $features } = global.Vue?.config?.globalProperties || {};

        this.$tm = $tm;
        this.$features = $features;

        // Partial sections are merged over the section defaults rather than replacing them
        APPLICATION_SECTION_KEYS.forEach((sectionKey) => {
            if (cleanDataObject[sectionKey]) {
                cleanDataObject[sectionKey] = {
                    ...(this as any)[sectionKey],
                    ...deleteUndefinedProperties(cleanDataObject[sectionKey]),
                };
            }
        });

        Object.assign(this, cleanDataObject);
    }

    // Helper methods
    public createdDateDisplay(): string {
        return dateDisplay(this.created);
    }

    public submittedDateDisplay(): string {
        return dateDisplay(this.submitted);
    }

    public completedDateDisplay(): string {
        return dateDisplay(this.completed);
    }

    public typeDisplay(): string {
        const applicationTypes = this.$tm('application.applicationTypes') || [];
        const unknownType = applicationTypes.find((translate) => translate.key === 'unknown')?.abbrev || '';
        const displayTypes = this.types?.map((type) =>
            applicationTypes.find((translate) => translate.key === type)?.abbrev || unknownType) || [];
        const display = displayTypes.join(' + ');

        return display;
    }

    public getStatusDisplay(status: string): string {
        const applicationStatusTypes = this.$tm('application.applicationStatusTypes') || [];
        const unknownStatusDisplay = applicationStatusTypes.find((translate) => translate.key === 'unknown')?.name || '';
        const statusDisplay = applicationStatusTypes.find((translate) =>
            translate.key === status)?.name || unknownStatusDisplay;

        return statusDisplay;
    }

    public applicationStatusDisplay(): string {
        return this.getStatusDisplay(this.status || '');
    }

    public areAllSectionsCompleteForApplicant(): boolean {
        const sectionStatuses = [
            this.personalInformation?.applicantStatus,
            this.licenseHistory?.applicantStatus,
            this.education?.applicantStatus,
            this.conductHistory?.applicantStatus,
            this.homeState?.applicantStatus,
            this.acknowledgements?.applicantStatus,
        ];

        return sectionStatuses.every((status) => status === ApplicantSectionStatus.COMPLETE);
    }
}

// ========================================================
// =                      Serializer                      =
// ========================================================
export class ApplicationAttestationsSerializer {
    static fromServer(serverAttestations: any): Array<ApplicationAttestation> {
        const attestations: Array<ApplicationAttestation> = [];

        if (Array.isArray(serverAttestations)) {
            serverAttestations.forEach((json) => {
                const attestation: ApplicationAttestation = {
                    attestationId: json.attestationId,
                    version: json.version,
                };

                attestations.push(attestation);
            });
        }

        return attestations;
    }
}

export class ApplicationReviewsSerializer {
    static fromServer(serverReviews: any): Array<ApplicationReview> {
        const reviews: Array<ApplicationReview> = [];

        if (Array.isArray(serverReviews)) {
            serverReviews.forEach((json) => {
                const review: ApplicationReview = {
                    assignedDate: json.assignedDate,
                    reviewer: (json.reviewer) ? {
                        id: json.reviewer?.id,
                        firstName: json.reviewer?.firstName,
                        lastName: json.reviewer?.lastName,
                    } : undefined,
                    reviewerType: json.reviewerType,
                    reviewerStatus: json.reviewerStatus,
                    reviewDate: json.reviewDate,
                    notesForApplicant: json.notesForApplicant,
                    notesForReviewers: json.notesForReviewers,
                };

                reviews.push(review);
            });
        }

        return reviews;
    }
}

export class ApplicationLicensesSerializer {
    static fromServer(serverLicenses: any): Array<ApplicationLicense> {
        const licenses: Array<ApplicationLicense> = [];

        if (Array.isArray(serverLicenses)) {
            serverLicenses.forEach((json) => {
                const license: ApplicationLicense = {
                    state: json.state,
                    issueDate: json.issueDate,
                    licenseNumber: json.licenseNumber,
                    status: json.status,
                };

                licenses.push(license);
            });
        }

        return licenses;
    }
}

export class ApplicationFilesSerializer {
    static fromServer(serverFiles: any): Array<ApplicationFile> {
        const files: Array<ApplicationFile> = [];

        if (Array.isArray(serverFiles)) {
            serverFiles.forEach((json) => {
                const file: ApplicationFile = {
                    filename: json.filename,
                    sizeBytes: json.sizeBytes,
                    downloadUri: json.downloadUri,
                };

                files.push(file);
            });
        }

        return files;
    }
}

export class ApplicationAccreditingContactSerializer {
    static fromServer(json: any): ApplicationAccreditingContact | null {
        let accreditingContact: ApplicationAccreditingContact | null = null;

        if (json) {
            accreditingContact = {
                name: json.name,
                email: json.email,
                city: json.city,
                state: json.state,
                zip: json.zip,
                phone: json.phone,
                attestations: ApplicationAttestationsSerializer.fromServer(json.attestations),
            };
        }

        return accreditingContact;
    }
}

export class ApplicationConductConvictionsSerializer {
    static fromServer(serverConductConvictions: any): Array<ApplicationConductConviction> {
        const conductConvictions: Array<ApplicationConductConviction> = [];

        if (Array.isArray(serverConductConvictions)) {
            serverConductConvictions.forEach((json) => {
                const conductConviction: ApplicationConductConviction = {
                    charge: json.charge,
                    location: json.location,
                    date: json.date,
                    type: json.type,
                };

                conductConvictions.push(conductConviction);
            });
        }

        return conductConvictions;
    }
}

export class ApplicationHomeStatesSerializer {
    static fromServer(serverHomeStates: any): Array<ApplicationHomeState> {
        const homeStates: Array<ApplicationHomeState> = [];

        if (Array.isArray(serverHomeStates)) {
            serverHomeStates.forEach((json) => {
                const homeState: ApplicationHomeState = {
                    applicationType: json.applicationType,
                    state: json.state,
                    startDate: json.startDate,
                    isActiveMilitary: json.isActiveMilitary || false,
                    militaryDocuments: ApplicationFilesSerializer.fromServer(json.militaryDocuments),
                    attestations: ApplicationAttestationsSerializer.fromServer(json.attestations),
                };

                homeStates.push(homeState);
            });
        }

        return homeStates;
    }
}

export class ApplicationSerializer {
    static fromServer(json: any): Application {
        const applicationData = {
            id: json.id,
            created: json.created,
            submitted: json.submitted,
            completed: json.completed,
            types: json.types || [],
            isRenewal: json.isRenewal || false,
            status: json.status,
            reviews: ApplicationReviewsSerializer.fromServer(json.reviews),
            attestations: ApplicationAttestationsSerializer.fromServer(json.attestations),
            paymentCompensated: json.paymentCompensated || [],
            personalInformation: {
                applicantStatus: json.personalInformation?.applicantStatus,
                reviewStatus: json.personalInformation?.reviewStatus,
                reviews: ApplicationReviewsSerializer.fromServer(json.personalInformation?.reviews),
                firstName: json.personalInformation?.firstName,
                middleName: json.personalInformation?.middleName,
                lastName: json.personalInformation?.lastName,
                suffix: json.personalInformation?.suffix,
                phone: json.personalInformation?.phone,
                altPhone: json.personalInformation?.altPhone,
                dob: json.personalInformation?.dob,
                ssnLastFour: json.personalInformation?.ssnLastFour,
                npi: json.personalInformation?.npi,
                gender: json.personalInformation?.gender,
                professionalName: json.personalInformation?.professionalName,
                citizenship: json.personalInformation?.citizenship,
                placeOfBirth: json.personalInformation?.placeOfBirth,
                languages: json.personalInformation?.languages || [],
                mailingAddress1: json.personalInformation?.mailingAddress1,
                mailingAddress2: json.personalInformation?.mailingAddress2,
                mailingCity: json.personalInformation?.mailingCity,
                mailingState: json.personalInformation?.mailingState,
                mailingZip: json.personalInformation?.mailingZip,
            },
            licenseHistory: {
                applicantStatus: json.licenseHistory?.applicantStatus,
                reviewStatus: json.licenseHistory?.reviewStatus,
                reviews: ApplicationReviewsSerializer.fromServer(json.licenseHistory?.reviews),
                ePassport: {
                    mobilityNumber: json.licenseHistory?.ePassport?.mobilityNumber || null,
                    issueDate: json.licenseHistory?.ePassport?.issueDate || null,
                },
                ipc: {
                    mobilityNumber: json.licenseHistory?.ipc?.mobilityNumber || null,
                    issueDate: json.licenseHistory?.ipc?.issueDate || null,
                },
                licenses: ApplicationLicensesSerializer.fromServer(json.licenseHistory?.licenses),
            },
            education: {
                applicantStatus: json.education?.applicantStatus,
                reviewStatus: json.education?.reviewStatus,
                reviews: ApplicationReviewsSerializer.fromServer(json.education?.reviews),
                nameAtTime: json.education?.nameAtTime,
                institution: json.education?.institution,
                city: json.education?.city,
                state: json.education?.state,
                degreeType: json.education?.degreeType,
                program: json.education?.program,
                department: json.education?.department,
                conferredDate: json.education?.conferredDate,
                isCompleted: json.education?.isCompleted || false,
                accreditingBody: json.education?.accreditingBody,
                accreditingYear: json.education?.accreditingYear,
                isAccreditedByAuthority: json.education?.isAccreditedByAuthority || false,
                isProgramEquivalent: json.education?.isProgramEquivalent || false,
                accreditingContact: ApplicationAccreditingContactSerializer
                    .fromServer(json.education?.accreditingContact),
                hasResidence: json.education?.hasResidence || false,
                transcripts: ApplicationFilesSerializer.fromServer(json.education?.transcripts),
            },
            conductHistory: {
                applicantStatus: json.conductHistory?.applicantStatus,
                reviewStatus: json.conductHistory?.reviewStatus,
                reviews: ApplicationReviewsSerializer.fromServer(json.conductHistory?.reviews),
                attestations: ApplicationAttestationsSerializer.fromServer(json.conductHistory?.attestations),
                convictions: ApplicationConductConvictionsSerializer.fromServer(json.conductHistory?.convictions),
                notes: json.conductHistory?.notes,
                documents: ApplicationFilesSerializer.fromServer(json.conductHistory?.documents),
            },
            homeState: {
                applicantStatus: json.homeState?.applicantStatus,
                reviewStatus: json.homeState?.reviewStatus,
                reviews: ApplicationReviewsSerializer.fromServer(json.homeState?.reviews),
                applicationTypes: ApplicationHomeStatesSerializer.fromServer(json.homeState?.applicationTypes),
            },
            acknowledgements: {
                applicantStatus: json.acknowledgements?.applicantStatus,
                reviewStatus: json.acknowledgements?.reviewStatus,
                reviews: ApplicationReviewsSerializer.fromServer(json.acknowledgements?.reviews),
                attestations: ApplicationAttestationsSerializer.fromServer(json.acknowledgements?.attestations),
                signatureName: json.acknowledgements?.signatureName,
            },
        };

        return new Application(applicationData);
    }

    static toServer(applicationModel: Application): any {
        return {
            id: applicationModel.id,
        };
    }
}
