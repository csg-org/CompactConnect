//
//  ApplicationChecklist.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import ProgressBar from '@components/ProgressBar/ProgressBar.vue';
import UserIcon from '@components/Icons/User/User.vue';
import RibbonIcon from '@components/Icons/RibbonIcon/RibbonIcon.vue';
import GraduationCapIcon from '@components/Icons/GraduationCapIcon/GraduationCapIcon.vue';
import ClipboardCheckIcon from '@components/Icons/ClipboardCheckIcon/ClipboardCheckIcon.vue';
import LocationPinIcon from '@components/Icons/LocationPinIcon/LocationPinIcon.vue';
import PencilIcon from '@components/Icons/PencilIcon/PencilIcon.vue';
import {
    Application,
    ApplicationSection,
    ApplicantSectionStatus
} from '@models/Application/Application.model';

export enum ChecklistStatusClass {
    INCOMPLETE = 'incomplete',
    COMPLETE = 'complete',
    ATTENTION = 'attention',
}

export interface ChecklistSection {
    key: ApplicationSection;
    name: string;
    description: string;
    icon: string;
    statusDisplay: string;
    statusClass: ChecklistStatusClass;
    isIncomplete: boolean;
    buttonLabel: string;
}

interface ApplicationSectionConfig {
    key?: string;
    name?: string;
    description?: string;
}

@Component({
    name: 'ApplicationChecklist',
    components: {
        InputButton,
        ProgressBar,
        UserIcon,
        RibbonIcon,
        GraduationCapIcon,
        ClipboardCheckIcon,
        LocationPinIcon,
        PencilIcon,
    }
})
class ApplicationChecklist extends Vue {
    //
    // Data
    //
    hasFetched = false;
    fetchedApplication: Application | null = null;

    //
    // Lifecycle
    //
    async created() {
        await this.fetchApplication();
    }

    //
    // Computed
    //
    get userStore(): any {
        return this.$store.state.user;
    }

    get compactType(): string {
        return this.userStore.currentCompact?.type || String(this.$route.params.compact || '');
    }

    get applicationId(): string {
        return String(this.$route.params.applicationId || '');
    }

    get storeApplication(): Application | null {
        const applications: Array<Application> = this.userStore.model?.licensee?.applications || [];

        return applications.find((application) => String(application.id) === this.applicationId) || null;
    }

    get application(): Application | null {
        return this.storeApplication || this.fetchedApplication;
    }

    get isLoadError(): boolean {
        return this.hasFetched && !this.application;
    }

    get isEditable(): boolean {
        return this.application?.isEditableByApplicant() || false;
    }

    get completedSectionCount(): number {
        return this.application?.completedSectionCount() || 0;
    }

    get sectionCount(): number {
        return this.application?.sectionCount() || 0;
    }

    get progressPercent(): number {
        return (this.sectionCount) ? Math.round((this.completedSectionCount / this.sectionCount) * 100) : 0;
    }

    get progressDisplay(): string {
        return this.$t('application.checklistProgress', {
            complete: this.completedSectionCount,
            total: this.sectionCount,
        });
    }

    get sectionConfigs(): Array<ApplicationSectionConfig> {
        return this.$tm('application.applicationSections') || [];
    }

    get sections(): Array<ChecklistSection> {
        const sections = this.application?.getSections() || [];

        return sections.map(({ key, applicantStatus }) => {
            const status = applicantStatus || ApplicantSectionStatus.INCOMPLETE;
            const config = this.sectionConfigs.find((sectionConfig) => sectionConfig.key === key);
            const isIncomplete = status === ApplicantSectionStatus.INCOMPLETE;

            return {
                key,
                name: config?.name || '',
                description: config?.description || '',
                icon: this.getSectionIcon(key),
                statusDisplay: this.application?.getStatusDisplay(status) || '',
                statusClass: this.getStatusClass(status),
                isIncomplete,
                buttonLabel: (isIncomplete) ? this.$t('application.startSection') : this.$t('common.edit'),
            };
        });
    }

    get isContinueEnabled(): boolean {
        return this.isEditable && (this.application?.areAllSectionsCompleteForApplicant() || false);
    }

    get continueLabel(): string {
        return (this.application?.isFeeWaived())
            ? this.$t('application.continueToSubmission')
            : this.$t('application.continueToPayment');
    }

    //
    // Methods
    //
    async fetchApplication(): Promise<void> {
        const application = await this.$store.dispatch('user/getApplicationRequestLicensee', {
            applicationId: this.applicationId,
        });

        this.fetchedApplication = application || null;
        this.hasFetched = true;
    }

    getSectionIcon(key: ApplicationSection): string {
        const sectionIcons = {
            [ApplicationSection.PERSONAL_INFORMATION]: 'UserIcon',
            [ApplicationSection.LICENSE_HISTORY]: 'RibbonIcon',
            [ApplicationSection.EDUCATION]: 'GraduationCapIcon',
            [ApplicationSection.CONDUCT_HISTORY]: 'ClipboardCheckIcon',
            [ApplicationSection.HOME_STATE]: 'LocationPinIcon',
            [ApplicationSection.ACKNOWLEDGEMENTS]: 'PencilIcon',
        };

        return sectionIcons[key];
    }

    getStatusClass(status: ApplicantSectionStatus): ChecklistStatusClass {
        let statusClass = ChecklistStatusClass.INCOMPLETE;

        if (status === ApplicantSectionStatus.COMPLETE) {
            statusClass = ChecklistStatusClass.COMPLETE;
        } else if (
            status === ApplicantSectionStatus.NEEDS_ATTENTION
            || status === ApplicantSectionStatus.CONFIRM_DETAILS
        ) {
            statusClass = ChecklistStatusClass.ATTENTION;
        }

        return statusClass;
    }

    openSection(section: ChecklistSection): void {
        console.log('open application section', this.applicationId, section.key);
    }

    continueApplication(): void {
        console.log('continue application', this.applicationId);
    }
}

export default toNative(ApplicationChecklist);

// export default ApplicationChecklist;
