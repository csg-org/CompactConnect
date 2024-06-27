//
//  Blueprint.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on MM/DD/YYYY.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import Blueprint from '@pages/SubPath/Blueprint/Blueprint.vue';

describe('Blueprint page', () => {
    it('should mount the page component', () => {
        const wrapper = mountShallow(Blueprint);
        const component = wrapper.find(Blueprint);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.find(Blueprint).exists()).to.equal(true);
        expect(component.is(Blueprint)).to.equal(true);
    });
});
