//
//  AlertCircle.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 5/7/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AlertCircle from '@components/Icons/AlertCircle/AlertCircle.vue';

describe('AlertCircle component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AlertCircle);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AlertCircle).exists()).to.equal(true);
    });
});
