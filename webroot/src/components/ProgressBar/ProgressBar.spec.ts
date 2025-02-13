//
//  ProgressBar.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 2/3/2025.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import ProgressBar from '@components/ProgressBar/ProgressBar.vue';

describe('ProgressBar component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(ProgressBar);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(ProgressBar).exists()).to.equal(true);
    });
});
