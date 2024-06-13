//
//  ExampleLoadingSpinner.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/5/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleLoadingSpinner from '@components/StyleGuide/ExampleLoadingSpinner/ExampleLoadingSpinner.vue';

describe('ExampleLoadingSpinner component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleLoadingSpinner);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleLoadingSpinner).exists()).to.equal(true);
    });
});
