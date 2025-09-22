//
//  Sorting.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/2/2020.
//

import {
    Component,
    Prop,
    mixins,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed } from 'vue';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputRadioGroup from '@components/Forms/InputRadioGroup/InputRadioGroup.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import { SortDirection } from '@store/sorting/sorting.state';

@Component({
    name: 'Sorting',
    components: {
        InputRadioGroup
    }
})
class Sorting extends mixins(MixinForm) {
    @Prop({ required: true }) listId!: string;
    @Prop({ required: true }) sortOptions!: Array<{ value: string; name: string }>;
    @Prop({ required: true }) sortChange!: (selectedSortOption: string, ascending: boolean) => any;
    @Prop({ required: true }) sortingId!: string;

    //
    // Data
    //
    isCollapsed = true;

    //
    // Lifecycle
    //
    created() {
        this.initFormInputs();
    }

    //
    // Computed
    //
    get sortingStore() {
        return this.$store.state.sorting;
    }

    get sortingStoreOption(): any {
        return this.sortingStore.sortingMap[this.listId]?.option;
    }

    get sortingStoreDirection(): SortDirection {
        return this.sortingStore.sortingMap[this.listId]?.direction;
    }

    get isPhone(): boolean {
        return this.$matches.phone.only;
    }

    //
    // Methods
    //
    initFormInputs(): void {
        this.formData = reactive({
            sortOptions: new FormInput({
                id: 'sort-option',
                name: 'sort-option',
                label: computed(() => this.$t('sorting.sortBy')),
                value: this.sortingStore.sortingMap[this.listId]?.option,
                valueOptions: this.sortOptions,
            }),
            sortDirection: new FormInput({
                id: 'sort-direction',
                name: 'sort-direction',
                label: computed(() => this.$t('sorting.order')),
                value: this.sortingStore.sortingMap[this.listId]?.direction,
                valueOptions: [
                    { value: SortDirection.asc, name: computed(() => this.$t('sorting.asc')) },
                    { value: SortDirection.desc, name: computed(() => this.$t('sorting.desc')) },
                ],
            }),
        });
    }

    toggleSort() {
        this.isCollapsed = !this.isCollapsed;
    }

    async sortOptionChange(formInput: FormInput, isExternal = false) {
        const { sortingId } = this;
        const { sortOptions, sortDirection } = this.formData;

        if (sortOptions.value !== this.sortingStoreOption) {
            if (isExternal) {
                sortOptions.value = this.sortingStoreOption;
            } else {
                const newOption = formInput.value;

                await this.$store.dispatch('sorting/updateSortOption', { sortingId, newOption });
            }

            if (typeof this.sortChange === 'function') {
                this.sortChange(sortOptions.value, Boolean(sortDirection.value === SortDirection.asc));
            }
        }
    }

    async sortDirectionChange(formInput: FormInput, isExternal = false) {
        const { sortingId } = this;
        const { sortOptions, sortDirection } = this.formData;

        if (sortDirection.value !== this.sortingStoreDirection) {
            if (isExternal) {
                sortDirection.value = this.sortingStoreDirection;
            } else {
                const newDirection = formInput.value;

                await this.$store.dispatch('sorting/updateSortDirection', { sortingId, newDirection });
            }

            if (typeof this.sortChange === 'function') {
                this.sortChange(sortOptions.value, Boolean(sortDirection.value === SortDirection.asc));
            }
        }
    }

    //
    // Watchers
    //
    @Watch('sortingStoreOption') sortStoreOptionUpdate() {
        this.sortOptionChange(this.formData.sortOptions, true);
    }

    @Watch('sortingStoreDirection') sortStoreDirectionUpdate() {
        this.sortDirectionChange(this.formData.sortDirection, true);
    }
}

export default toNative(Sorting);

// export { Sorting };
