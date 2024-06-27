//
//  ShowPasswordEye.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ShowPasswordEye from '@components/Icons/ShowPasswordEye/ShowPasswordEye.vue';

describe('ShowPasswordEye component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ShowPasswordEye);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ShowPasswordEye).exists()).to.equal(true);
    });
});
