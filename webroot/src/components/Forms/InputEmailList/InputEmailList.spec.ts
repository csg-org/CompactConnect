//
//  InputEmailList.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/13/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InputEmailList from '@components/Forms/InputEmailList/InputEmailList.vue';

describe('InputEmailList component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InputEmailList);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InputEmailList).exists()).to.equal(true);
    });
});
