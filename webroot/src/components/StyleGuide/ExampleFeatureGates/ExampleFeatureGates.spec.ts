//
//  ExampleFeatureGates.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/25/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleFeatureGates from '@components/StyleGuide/ExampleFeatureGates/ExampleFeatureGates.vue';

describe('ExampleFeatureGates component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleFeatureGates);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleFeatureGates).exists()).to.equal(true);
    });
});
