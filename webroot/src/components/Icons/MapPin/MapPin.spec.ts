//
//  MapPin.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/2/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MapPin from '@components/Icons/MapPin/MapPin.vue';

describe('MapPin component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(MapPin);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MapPin).exists()).to.equal(true);
    });
});
