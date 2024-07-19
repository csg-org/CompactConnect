//
//  LicenseeRow.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 7/3/2024.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import LicenseeRow from '@components/Licensee/LicenseeRow/LicenseeRow.vue';
import { Licensee } from '@models/Licensee/Licensee.model';

describe('LicenseeRow component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(LicenseeRow, {
            props: {
                listId: 'test',
                item: new Licensee(),
            },
        });

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(LicenseeRow).exists()).to.equal(true);
    });
});
