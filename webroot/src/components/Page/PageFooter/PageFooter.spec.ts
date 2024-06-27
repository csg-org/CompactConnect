//
//  PageFooter.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageFooter from '@components/Page/PageFooter/PageFooter.vue';
import moment from 'moment';

describe('PageFooter component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageFooter);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageFooter).exists()).to.equal(true);
    });
    it('should display the copyright year', async () => {
        const wrapper = await mountShallow(PageFooter);
        const copyright = wrapper.find('.copyright');
        const copyrightYear = moment().format('YYYY');

        expect(copyright.exists()).to.equal(true);
        expect(copyright.text()).to.contain(copyrightYear);
    });
});
