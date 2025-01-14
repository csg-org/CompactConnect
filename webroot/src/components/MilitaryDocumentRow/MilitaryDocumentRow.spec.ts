//
//  MilitaryDocumentRow.spec.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/30/2021.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import MilitaryDocumentRow from '@components/MilitaryDocumentRow/MilitaryDocumentRow.vue';

describe('MilitaryDocumentRow component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(MilitaryDocumentRow, {
            props: {
                item: {},
            }
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(MilitaryDocumentRow).exists()).to.equal(true);
    });
});
