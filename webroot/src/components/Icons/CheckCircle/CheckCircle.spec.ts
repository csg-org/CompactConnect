//
//  CheckCircle.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/5/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import CheckCircle from '@components/Icons//CheckCircle/CheckCircle.vue';

describe('CheckCircle component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(CheckCircle);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(CheckCircle).exists()).to.equal(true);
    });
});
