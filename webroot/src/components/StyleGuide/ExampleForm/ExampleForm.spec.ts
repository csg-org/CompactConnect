//
//  ExampleForm.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/3/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleForm from '@components/StyleGuide/ExampleForm/ExampleForm.vue';

describe('ExampleForm component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleForm);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleForm).exists()).to.equal(true);
    });
});
