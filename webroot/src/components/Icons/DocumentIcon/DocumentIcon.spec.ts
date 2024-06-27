//
//  DocumentIcon.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 6/5/2020.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import DocumentIcon from '@components/Icons//DocumentIcon/DocumentIcon.vue';

describe('DocumentIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(DocumentIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(DocumentIcon).exists()).to.equal(true);
    });
});
