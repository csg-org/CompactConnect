//
//  ExampleRow.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleRow from '@components/StyleGuide/ExampleRow/ExampleRow.vue';

describe('ExampleRow component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleRow, {
            props: {
                item: {},
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleRow).exists()).to.equal(true);
    });
});
