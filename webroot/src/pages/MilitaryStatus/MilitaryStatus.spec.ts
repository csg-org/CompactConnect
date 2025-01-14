//
//  MilitaryStatus.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MilitaryStatus from '@pages/MilitaryStatus/MilitaryStatus.vue';

describe('MilitaryStatus page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(MilitaryStatus);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MilitaryStatus).exists()).to.equal(true);
    });
});
