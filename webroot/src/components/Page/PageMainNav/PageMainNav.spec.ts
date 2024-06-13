//
//  PageMainNav.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 11/20/2020.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import PageMainNav from '@components/Page/PageMainNav/PageMainNav.vue';

describe('PageMainNav component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(PageMainNav);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(PageMainNav).exists()).to.equal(true);
    });
    it('should have the expected links', async () => {
        const mainNavLinks = [
            {
                to: '/Home',
                label: 'Router link',
                isEnabled: true,
                isExternal: false,
            },
            {
                to: '/some/external/link',
                label: 'External link',
                isEnabled: true,
                isExternal: true,
            },
            {
                to: '/Disabled',
                label: 'Disabled link',
                isEnabled: false,
                isExternal: false,
            },
        ].filter((link) => link.isEnabled);
        const wrapper = await mountShallow(PageMainNav, {
            computed: {
                mainLinks: {
                    get() {
                        return mainNavLinks;
                    }
                },
                isDesktop: {
                    get() {
                        return true;
                    }
                },
                isMainNavVisible: {
                    get() {
                        return true;
                    }
                },
            },
        });
        const links = wrapper.findAll('a');

        expect(links.length).to.equal(2);

        expect(links[0].text()).to.equal('Router link');
        expect(links[0].attributes().href).to.equal('/Home');
        expect(links[0].attributes().target).to.be.undefined;
        expect(links[0].attributes().rel).to.be.undefined;

        expect(links[1].text()).to.equal('External link');
        expect(links[1].attributes().href).to.equal('/some/external/link');
        expect(links[1].attributes().target).to.equal('_blank');
        expect(links[1].attributes().rel).to.equal('noopener noreferrer');
    });
});
