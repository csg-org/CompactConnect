//
//  ExampleList.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExampleList from '@components/StyleGuide/ExampleList/ExampleList.vue';

describe('ExampleList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExampleList, {
            propsData: {
                listId: 'test',
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExampleList).exists()).to.equal(true);
    });
});
