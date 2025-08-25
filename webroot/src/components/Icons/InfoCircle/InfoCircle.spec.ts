//
//  InfoCircle.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/18/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import InfoCircle from '@components/Icons/InfoCircle/InfoCircle.vue';

describe('InfoCircle component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(InfoCircle);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(InfoCircle).exists()).to.equal(true);
    });
});
