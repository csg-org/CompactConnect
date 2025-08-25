//
//  AlertTriangle.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/24/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import AlertTriangle from '@components/Icons/AlertTriangle/AlertTriangle.vue';

describe('AlertTriangle component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(AlertTriangle);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(AlertTriangle).exists()).to.equal(true);
    });
});
