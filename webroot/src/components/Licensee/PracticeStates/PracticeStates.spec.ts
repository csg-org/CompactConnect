//
//  PracticeStates.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/24/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PracticeStates from '@components/Licensee/PracticeStates/PracticeStates.vue';

describe('PracticeStates component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PracticeStates);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PracticeStates).exists()).to.equal(true);
    });
});
