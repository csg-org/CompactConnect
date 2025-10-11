//
//  ExpirationExplanationIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/15/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExpirationExplanationIcon from '@components/Icons/ExpirationExplanationIcon/ExpirationExplanationIcon.vue';

describe('ExpirationExplanationIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExpirationExplanationIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExpirationExplanationIcon).exists()).to.equal(true);
    });
});
