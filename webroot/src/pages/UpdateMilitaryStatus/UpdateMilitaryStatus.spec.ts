//
//  UpdateMilitaryStatus.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import UpdateMilitaryStatus from '@pages/UpdateMilitaryStatus/UpdateMilitaryStatus.vue';

describe('UpdateMilitaryStatus page', async () => {
    it('should mount the page component', async () => {
        const wrapper = await mountShallow(UpdateMilitaryStatus);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(UpdateMilitaryStatus).exists()).to.equal(true);
    });
});
