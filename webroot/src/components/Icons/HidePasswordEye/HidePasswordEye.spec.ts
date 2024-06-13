//
//  HidePasswordEye.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/22/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import HidePasswordEye from '@components/Icons/HidePasswordEye/HidePasswordEye.vue';

describe('HidePasswordEye component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(HidePasswordEye);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(HidePasswordEye).exists()).to.equal(true);
    });
});
