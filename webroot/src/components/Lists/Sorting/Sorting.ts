//
//  Sorting.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/2/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import {
    Component,
    Prop,
    mixins,
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

    get isPhone() {
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

    async sortOptionChange(formInput: FormInput) {
        const { sortingId } = this;
        const { sortOptions, sortDirection } = this.formData;
        const newOption = formInput.value;

        await this.$store.dispatch('sorting/updateSortOption', { sortingId, newOption }); // Ideally, interested observers can just watch the store
        this.sortChange(sortOptions.value, Boolean(sortDirection.value === SortDirection.asc)); // ...but we'll also fire the change method property too for now
    }

    async sortDirectionChange(formInput: FormInput) {
        const { sortingId } = this;
        const { sortOptions, sortDirection } = this.formData;
        const newDirection = formInput.value;

        await this.$store.dispatch('sorting/updateSortDirection', { sortingId, newDirection }); // Ideally, interested observers can just watch the store
        this.sortChange(sortOptions.value, Boolean(sortDirection.value === SortDirection.asc)); // ...but we'll also fire the change method property too for now
    }
}

export default toNative(Sorting);

// export { Sorting };
