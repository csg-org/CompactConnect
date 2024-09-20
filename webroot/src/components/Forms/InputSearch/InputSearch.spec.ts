//
//  InputSearch.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/11/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputSearch from '@components/Forms/InputSearch/InputSearch.vue';

describe('InputSearch component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputSearch);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputSearch).exists()).to.equal(true);
    });
});
