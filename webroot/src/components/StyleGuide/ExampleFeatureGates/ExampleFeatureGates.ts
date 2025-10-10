//
//  ExampleFeatureGates.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/25/2025.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import { FeatureGates } from '@/app.config';
import Section from '@components/Section/Section.vue';
import { User } from '@models/User/User.model';
import { dataApi } from '@network/data.api';

@Component({
    name: 'ExampleFeatureGates',
    components: {
        Section,
    },
})
class ExampleFeatureGates extends Vue {
    //
    // Data
    //
    isFeatureGateEnabledInStoreLayer = false;
    isFeatureGateEnabledInModelLayer = false;
    isFeatureGateEnabledInNetworkLayer = false;

    //
    // Lifecycle
    //
    async created(): Promise<void> {
        await this.setFeatureGateEnabledInStoreLayer();
        await this.setFeatureGateEnabledInModelLayer();
        await this.setFeatureGateEnabledInNetworkLayer();
    }

    //
    // Computed
    //
    get featureGates(): typeof FeatureGates {
        return FeatureGates;
    }

    //
    // Methods
    //
    async setFeatureGateEnabledInStoreLayer(): Promise<void> {
        const isEnabled = await this.$store.dispatch('styleguide/getFeatureGateExample');

        this.isFeatureGateEnabledInStoreLayer = isEnabled;
    }

    async setFeatureGateEnabledInModelLayer(): Promise<void> {
        const userModel = new User();

        this.isFeatureGateEnabledInModelLayer = userModel.$features?.checkGate(FeatureGates.EXAMPLE_FEATURE_1) || false;
    }

    async setFeatureGateEnabledInNetworkLayer(): Promise<void> {
        const isEnabled = await dataApi.getExampleFeatureGate();

        this.isFeatureGateEnabledInNetworkLayer = isEnabled;
    }
}

export default toNative(ExampleFeatureGates);

// export default ExampleFeatureGates;
