//
//  CompactSelector.ts
//  CompactConnect
//
//  Created by InspiringApps on 10/2/2024.
//

import { AppModes, compacts as compactsConfig } from '@/app.config';
import {
    Component,
    mixins,
    Prop,
    Watch,
    toNative
} from 'vue-facing-decorator';
import { reactive, computed, ComputedRef } from 'vue';
import { RouteRecordName } from 'vue-router';
import MixinForm from '@components/Forms/_mixins/form.mixin';
import InputSelect from '@components/Forms/InputSelect/InputSelect.vue';
import { FormInput } from '@models/FormInput/FormInput.model';
import { Compact, CompactSerializer, CompactType } from '@models/Compact/Compact.model';
import { StaffUser, CompactPermission } from '@models/StaffUser/StaffUser.model';

interface CompactOption {
    value: string | number;
    name: string | ComputedRef<string>;
}

@Component({
    name: 'CompactSelector',
    components: {
        InputSelect
    }
})
class CompactSelector extends mixins(MixinForm) {
    @Prop({ default: false }) isPermissionBased?: boolean;
    @Prop({ default: false }) hideIfNotMultiple?: boolean;

    //
    // Lifecycle
    //
    created() {
        this.init();
    }

    //
    // Computed
    //
    get userStore() {
        return this.$store.state.user;
    }

    get user(): StaffUser | null {
        return this.userStore.model;
    }

    get currentCompact(): Compact | null {
        return this.userStore.currentCompact;
    }

    get userPermissions(): Array<CompactPermission> {
        return this.user?.permissions || [];
    }

    get allCompacts(): Array<Compact> {
        const compactTypes = Object.keys(compactsConfig) as Array<CompactType>;
        const compacts = compactTypes.map((compactType) => new Compact({ type: compactType }));

        return compacts;
    }

    get compactOptions(): Array<CompactOption> {
        const options: Array<CompactOption> = [];

        if (this.isPermissionBased) {
            this.userPermissions.forEach((permission: CompactPermission) => {
                const { compact } = permission;

                options.push({ value: (compact.type as unknown as string), name: compact.name() });
            });
        } else {
            this.allCompacts.forEach((compact) => {
                options.push({ value: (compact.type as unknown as string), name: compact.name() });
            });
        }

        return options;
    }

    get shouldDisplay(): boolean {
        const { compactOptions, hideIfNotMultiple } = this;
        const optionsLength = compactOptions.length;

        return !(optionsLength === 1 && hideIfNotMultiple);
    }

    get routeCompactType(): CompactType | null {
        return (this.$route.params.compact as CompactType) || null;
    }

    //
    // Methods
    //
    init(): void {
        const {
            isPermissionBased,
            user,
            currentCompact,
            initFormInputs,
        } = this;

        if (isPermissionBased) {
            if (user && currentCompact) {
                initFormInputs();
            }
        } else if (currentCompact) {
            initFormInputs();
        }
    }

    initFormInputs(): void {
        this.formData = reactive({
            compact: new FormInput({
                id: 'compact-global',
                name: 'compact-global',
                label: computed(() => this.$t('common.compact')),
                shouldHideLabel: true,
                shouldHideMargin: true,
                placeholder: computed(() => this.$t('common.compact')),
                value: this.currentCompact?.type,
                valueOptions: this.compactOptions,
            }),
        });
    }

    async handleCompactSelect(): Promise<void> {
        const selectedCompactType = this.formData.compact.value;

        // If the current route is not matching the newly selected compact, then redirect
        if (this.routeCompactType && this.routeCompactType !== selectedCompactType) {
            await this.$router.push({
                name: (this.$route.name as RouteRecordName),
                params: { compact: selectedCompactType }
            });
            await this.$router.go(0); // This is the easiest way to force vue-router to reload components, which suits this compact-switch case
        } else {
            // Refresh the compact type on the store
            await this.$store.dispatch('user/setCurrentCompact', CompactSerializer.fromServer({ type: selectedCompactType }));
            if (selectedCompactType === CompactType.COSMETOLOGY) {
                this.$store.dispatch('setAppMode', AppModes.COSMETOLOGY);
            } else {
                this.$store.dispatch('setAppMode', AppModes.JCC);
            }
        }
    }

    //
    // Watchers
    //
    @Watch('currentCompact') storeCompactChange() {
        this.init();
    }

    @Watch('user') storeUserChange() {
        this.init();
    }
}

export default toNative(CompactSelector);

// export default CompactSelector;
