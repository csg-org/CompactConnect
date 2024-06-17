//
//  ExternalLinkIcon.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 1/23/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ExternalLinkIcon from '@components/Icons/ExternalLinkIcon/ExternalLinkIcon.vue';

describe('ExternalLinkIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ExternalLinkIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ExternalLinkIcon).exists()).to.equal(true);
    });
});
