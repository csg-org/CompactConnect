//
//  PageContainer.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageContainer from '@components/Page/PageContainer/PageContainer.vue';
import PageFooter from '@components/Page/PageFooter/PageFooter.vue';
import PageHeader from '@components/Page/PageHeader/PageHeader.vue';

describe('PageContainer component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageContainer);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageContainer).exists()).to.equal(true);
    });
    it('should have the page footer or header if route is not deny-listed', async () => {
        const wrapper = await mountShallow(PageContainer);

        expect(wrapper.findComponent(PageFooter).exists()).to.equal(true);
        expect(wrapper.findComponent(PageHeader).exists()).to.equal(true);
    });
    it('should not have the page footer or header if route is deny-listed', async () => {
        const wrapper = await mountShallow(PageContainer, {
            computed: {
                includePageHeader: {
                    get() {
                        return false;
                    }
                },
                includePageFooter: {
                    get() {
                        return false;
                    }
                },
            }
        });

        expect(wrapper.findComponent(PageFooter).exists()).to.equal(false);
        expect(wrapper.findComponent(PageHeader).exists()).to.equal(false);
    });
});
