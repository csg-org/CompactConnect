//
//  UserRow.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import {
    Component,
    mixins,
    Prop,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, nextTick } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import RightCaretIcon from '@components/Icons/RightCaretIcon/RightCaretIcon.vue';
import UserRowEdit from '@components/Users/UserRowEdit/UserRowEdit.vue';
import InputButton from '@components/Forms/InputButton/InputButton.vue';
import InputSubmit from '@components/Forms/InputSubmit/InputSubmit.vue';
import Modal from '@components/Modal/Modal.vue';
import { FormInput } from '@/models/FormInput/FormInput.model';
import { SortDirection } from '@store/sorting/sorting.state';

@Component({
    name: 'UserRow',
    components: {
        RightCaretIcon,
        UserRowEdit,
        InputButton,
        InputSubmit,
        Modal,
    },
})
class UserRow extends mixins(MixinForm) {
    @Prop({ required: true }) protected listId!: string;
    @Prop({ required: true }) item!: any;
    @Prop({ default: false }) isHeaderRow?: boolean;
    @Prop({ default: [] }) sortOptions?: Array<any>;
    @Prop({ default: () => null }) sortChange?: (selectedSortOption?: string, ascending?: boolean) => any;

    //
    // Data
    //
    lastSortSelectOption = '';
    lastSortSelectDirection = '';
    isRowExpanded = false;
    isRowActionMenuDisplayed = false;
    isEditUserModalDisplayed = false;
    isReinviteUserModalDisplayed = false;
    isDeactivateUserModalDisplayed = false;
    isReinviteSent = false;
    isDeactivated = false;
    modalErrorMessage = '';

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get currentCompactType() {
        return this.userStore.currentCompact?.type;
    }

    get sortingStore() {
        return this.$store.state.sorting;
    }

    get sortingStoreOption(): string {
        return this.sortingStore.sortingMap[this.listId]?.option;
    }

    get sortingStoreDirection(): SortDirection {
        return this.sortingStore.sortingMap[this.listId]?.direction;
    }

    get sortOptionNames(): Array<string> {
        const names: Array<string> = [];

        this.sortOptions?.forEach((option) => {
            if (option.value) {
                names.push(option.value);
            }
        });

        return names;
    }

    get isAccountStatusPending(): boolean {
        return this.item?.accountStatus === 'pending';
    }

    get isAccountStatusEmphasis(): boolean {
        return this.isAccountStatusPending;
    }

    get shouldAllowResendInvite(): boolean {
        return this.isAccountStatusPending;
    }

    get accountFullName(): string {
        return this.item?.getFullName() || '';
    }

    get accountEmail(): string {
        return this.item?.email || '';
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            submitModalContinue: new FormInput({
                isSubmitInput: true,
                id: 'submit-modal-continue',
            }),
        });
    }

    isSortOptionEnabled(optionName: string): boolean {
        return Boolean(this.isHeaderRow && this.sortOptionNames.includes(optionName));
    }

    isSortOptionSelected(optionName: string): boolean {
        return Boolean(this.isHeaderRow && this.sortingStoreOption === optionName);
    }

    sortOptionDirection(optionName: string): SortDirection {
        const isOptionSelected = this.isSortOptionSelected(optionName);
        let optionDirection = SortDirection.asc;

        if (isOptionSelected) {
            optionDirection = this.sortingStoreDirection;
        }

        return optionDirection;
    }

    isSortOptionAscending(optionName: string): boolean {
        return Boolean(this.sortOptionDirection(optionName) === SortDirection.asc);
    }

    isSortOptionDescending(optionName: string): boolean {
        return Boolean(this.sortOptionDirection(optionName) === SortDirection.desc);
    }

    async handleSortSelect(optionName: string): Promise<void> {
        await this.handleSortChangeDirection(optionName);
        await this.handleSortChangeOption(optionName);

        if (this.sortChange) {
            this.sortChange(this.sortingStoreOption, this.sortingStoreDirection === SortDirection.asc);
        }
    }

    async handleSortChangeOption(optionName: string, isExternal = false): Promise<void> {
        const sortingId = this.listId;

        if (optionName !== this.sortingStoreOption) {
            if (isExternal) {
                if (this.lastSortSelectOption !== this.sortingStoreOption) {
                    this.lastSortSelectOption = this.sortingStoreOption;
                }
            } else {
                const newOption = optionName;

                this.lastSortSelectOption = optionName;
                await this.$store.dispatch('sorting/updateSortOption', { sortingId, newOption });
            }
        }
    }

    async handleSortChangeDirection(optionName: string, isExternal = false): Promise<void> {
        const sortingId = this.listId;

        if (isExternal) {
            // If the sort direction changed externally, just sync our local state
            if (this.lastSortSelectDirection !== this.sortingStoreDirection) {
                this.lastSortSelectDirection = this.sortingStoreDirection;
            }
        } else if (optionName === this.sortingStoreOption) {
            // If the sort option is remaining the same, just toggle the direction
            const newDirection = (this.sortingStoreDirection === SortDirection.asc)
                ? SortDirection.desc
                : SortDirection.asc;

            await this.$store.dispatch('sorting/updateSortDirection', { sortingId, newDirection });
        } else if (optionName !== this.sortingStoreOption) {
            // If the sort option is changing, default to asc direction
            const newDirection = SortDirection.asc;

            await this.$store.dispatch('sorting/updateSortDirection', { sortingId, newDirection });
        }
    }

    expandRowToggle(): void {
        this.isRowExpanded = !this.isRowExpanded;
    }

    toggleRowActionMenu(): void {
        this.isRowActionMenuDisplayed = !this.isRowActionMenuDisplayed;
    }

    closeRowActionMenu(): void {
        this.isRowActionMenuDisplayed = false;
    }

    toggleEditUserModal(): void {
        this.isEditUserModalDisplayed = !this.isEditUserModalDisplayed;
    }

    closeEditUserModal(): void {
        this.isEditUserModalDisplayed = false;
    }

    async toggleReinviteUserModal(): Promise<void> {
        if (!this.isReinviteSent) {
            this.resetForm();
            this.isReinviteUserModalDisplayed = !this.isReinviteUserModalDisplayed;
            await nextTick();
            document.getElementById('reinvite-modal-cancel-button')?.focus();
        }
    }

    closeReinviteUserModal(): void {
        this.isReinviteUserModalDisplayed = false;
    }

    focusTrapReinviteUserModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('reinvite-modal-cancel-button');
        const lastTabIndex = document.getElementById(this.formData.submitModalContinue.id);

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitReinviteUser(): Promise<void> {
        this.startFormLoading();
        this.modalErrorMessage = '';

        await this.$store.dispatch(`users/reinviteUserRequest`, {
            compact: this.currentCompactType,
            userId: this.item.id,
        }).catch((err) => {
            this.modalErrorMessage = err?.message || this.$t('common.error');
            this.isFormError = true;
        });

        if (!this.isFormError) {
            this.isFormSuccessful = true;
            this.isReinviteSent = true;
            this.closeReinviteUserModal();
        }

        this.endFormLoading();
    }

    async toggleDeactivateUserModal(): Promise<void> {
        if (!this.isDeactivated) {
            this.resetForm();
            this.isDeactivateUserModalDisplayed = !this.isDeactivateUserModalDisplayed;
            await nextTick();
            document.getElementById('deactivate-modal-cancel-button')?.focus();
        }
    }

    closeDeactivateUserModal(): void {
        this.isDeactivateUserModalDisplayed = false;
    }

    focusTrapDeactivateUserModal(event: KeyboardEvent): void {
        const firstTabIndex = document.getElementById('deactivate-modal-cancel-button');
        const lastTabIndex = document.getElementById(this.formData.submitModalContinue.id);

        if (event.shiftKey) {
            // shift + tab to last input
            if (document.activeElement === firstTabIndex) {
                lastTabIndex?.focus();
                event.preventDefault();
            }
        } else if (document.activeElement === lastTabIndex) {
            // Tab to first input
            firstTabIndex?.focus();
            event.preventDefault();
        }
    }

    async submitDeactivateUser(): Promise<void> {
        this.startFormLoading();
        this.modalErrorMessage = '';

        await this.$store.dispatch(`users/deleteUserRequest`, {
            compact: this.currentCompactType,
            userId: this.item.id,
        }).catch((err) => {
            this.modalErrorMessage = err?.message || this.$t('common.error');
            this.isFormError = true;
        });

        if (!this.isFormError) {
            this.isFormSuccessful = true;
            this.isDeactivated = true;
            this.closeDeactivateUserModal();
        }

        this.endFormLoading();
    }

    resetForm(): void {
        this.isFormLoading = false;
        this.isFormSuccessful = false;
        this.isFormError = false;
        this.modalErrorMessage = '';
        this.updateFormSubmitSuccess('');
        this.updateFormSubmitError('');
    }

    //
    // Watchers
    //
    @Watch('sortingStoreOption') sortStoreOptionUpdate() {
        this.handleSortChangeOption(this.sortingStoreOption, true);
    }

    @Watch('sortingStoreDirection') sortStoreDirectionUpdate() {
        this.handleSortChangeDirection(this.sortingStoreOption, true);
    }
}

export default toNative(UserRow);

// export default UserRow;
