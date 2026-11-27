//
//  LocationPinIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LocationPinIcon from '@components/Icons/LocationPinIcon/LocationPinIcon.vue';

describe('LocationPinIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LocationPinIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LocationPinIcon).exists()).to.equal(true);
    });
});
