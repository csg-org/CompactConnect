//
//  Search.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/11/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Search from '@components/Icons/Search/Search.vue';

describe('Search component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(Search);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(Search).exists()).to.equal(true);
    });
});
