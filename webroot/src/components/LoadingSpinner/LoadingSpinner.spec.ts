//
//  LoadingSpinner.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/28/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LoadingSpinner from '@components/LoadingSpinner/LoadingSpinner.vue';

describe('LoadingSpinner component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LoadingSpinner);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LoadingSpinner).exists()).to.equal(true);
    });
    it('should have default mask no-bg-color class', async () => {
        const wrapper = await mountShallow(LoadingSpinner);
        const mask = wrapper.find('.loading-spinner-mask');

        expect(mask.classes()).not.to.contain('no-bg-color');
    });
    it('should have enabled mask no-bg-color class', async () => {
        const wrapper = await mountShallow(LoadingSpinner, {
            props: {
                noBgColor: true,
            }
        });
        const mask = wrapper.find('.loading-spinner-mask');

        expect(mask.classes()).to.contain('no-bg-color');
    });
});
