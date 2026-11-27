//
//  ApplicationStatusCard.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/10/2026.
//

import {
    Component,
    Vue,
    Prop,
    toNative
} from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import CheckCircleIcon from '@components/Icons/CheckCircle/CheckCircle.vue';
import AlertTriangleIcon from '@components/Icons/AlertTriangle/AlertTriangle.vue';
import CloseXIcon from '@components/Icons/CloseX/CloseX.vue';
import { Application, ApplicationStatus, ApplicantSectionStatus } from '@models/Application/Application.model';

export enum StatusStepState {
    COMPLETE = 'complete',
    CURRENT = 'current',
    ATTENTION = 'attention',
    APPROVED = 'approved',
    REJECTED = 'rejected',
    UPCOMING = 'upcoming',
}

export interface StatusStep {
    number: number;
    label: string;
    state: StatusStepState;
    isCurrent: boolean;
}

@Component({
    name: 'ApplicationStatusCard',
    components: {
        InputButton,
        CheckCircleIcon,
        AlertTriangleIcon,
        CloseXIcon,
    },
})
class ApplicationStatusCard extends Vue {
    @Prop({ required: true }) application!: Application;

    //
    // Computed
    //
    get stepStates(): typeof StatusStepState {
        return StatusStepState;
    }

    get title(): string {
        return this.$t('application.applicationTitle', { type: this.application?.typeDisplay() || '' });
    }

    get isFeeWaived(): boolean {
        return this.application?.isFeeWaived() || false;
    }

    get isStarted(): boolean {
        return this.application?.isStarted() || false;
    }

    get isInReview(): boolean {
        return this.application?.isInReview() || false;
    }

    get isNeedsAttention(): boolean {
        return this.application?.isNeedsAttention() || false;
    }

    get isApproved(): boolean {
        return this.application?.isApproved() || false;
    }

    get isRejected(): boolean {
        return this.application?.isRejected() || false;
    }

    get isDeactivated(): boolean {
        return this.application?.isDeactivated() || false;
    }

    get isRejectedOrDeactivated(): boolean {
        return this.isRejected || this.isDeactivated;
    }

    get currentStepIndex(): number {
        let stepIndex = 0;

        if (this.isInReview || this.isNeedsAttention) {
            stepIndex = 2;
        } else if (this.isApproved || this.isRejectedOrDeactivated) {
            stepIndex = 3;
        }

        return stepIndex;
    }

    get currentStepState(): StatusStepState {
        let stepState = StatusStepState.CURRENT;

        if (this.isNeedsAttention) {
            stepState = StatusStepState.ATTENTION;
        } else if (this.isApproved) {
            stepState = StatusStepState.APPROVED;
        } else if (this.isRejectedOrDeactivated) {
            stepState = StatusStepState.REJECTED;
        }

        return stepState;
    }

    get reviewStepLabel(): string {
        const status = (this.isNeedsAttention)
            ? ApplicantSectionStatus.NEEDS_ATTENTION
            : ApplicationStatus.STAFF_REVIEW;

        return this.application?.getStatusDisplay(status) || '';
    }

    get decisionStepLabel(): string {
        let label = this.$t('application.decision');

        if (this.isApproved || this.isRejectedOrDeactivated) {
            label = this.application?.applicationStatusDisplay() || '';
        }

        return label;
    }

    get steps(): Array<StatusStep> {
        const labels = [
            this.application?.getStatusDisplay(ApplicationStatus.STARTED) || '',
            this.application?.getStatusDisplay(ApplicationStatus.SUBMITTED) || '',
            this.reviewStepLabel,
            this.decisionStepLabel,
        ];

        return labels.map((label, index) => {
            const isCurrent = index === this.currentStepIndex;
            let state = StatusStepState.UPCOMING;

            if (index < this.currentStepIndex) {
                state = StatusStepState.COMPLETE;
            } else if (isCurrent) {
                state = this.currentStepState;
            }

            return {
                number: index + 1,
                label,
                state,
                isCurrent,
            };
        });
    }

    get summary(): string {
        let summary = '';

        if (this.isStarted) {
            summary = this.$t('application.sectionsComplete', {
                complete: this.application.completedSectionCount(),
                total: this.application.sectionCount(),
            });
        } else if (this.isInReview) {
            summary = this.$t('application.submittedInReview', { date: this.application.submittedDateDisplay() });
        } else if (this.isApproved) {
            summary = this.$t('application.approvedSummary');
        } else if (this.isRejected) {
            summary = this.$t('application.rejectedSummary');
        } else if (this.isDeactivated) {
            summary = this.$t('application.deactivatedSummary');
        }

        return summary;
    }

    get notes(): Array<string> {
        let notes: Array<string> = [];

        if (this.isNeedsAttention || this.isRejectedOrDeactivated) {
            notes = this.application.applicantNotes();
        }

        return notes;
    }

    get notesTitle(): string {
        return (this.isNeedsAttention)
            ? this.$t('application.issueWithApplication')
            : this.$t('application.reviewerNotes');
    }

    get isUpdateAvailable(): boolean {
        return this.isStarted || this.isNeedsAttention;
    }

    get updateButtonLabel(): string {
        return (this.isNeedsAttention)
            ? this.$t('application.updateApplication')
            : this.$t('application.continueApplication');
    }

    //
    // Methods
    //
    updateApplication(): void {
        this.$router.push({
            name: 'ApplicationChecklist',
            params: {
                compact: this.$store.state.user.currentCompact?.type,
                applicationId: this.application?.id,
            },
        });
    }
}

export default toNative(ApplicationStatusCard);

// export default ApplicationStatusCard;
