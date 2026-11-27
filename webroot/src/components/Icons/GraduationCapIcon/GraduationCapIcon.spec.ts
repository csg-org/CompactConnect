//
//  GraduationCapIcon.spec.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/17/2026.
//

import { expect } from 'chai';
import { mountShallow } from '@tests/helpers/setup';
import GraduationCapIcon from '@components/Icons/GraduationCapIcon/GraduationCapIcon.vue';

describe('GraduationCapIcon component', async () => {
    it('should mount the component', async () => {
        const wrapper = await mountShallow(GraduationCapIcon);

        expect(wrapper.exists()).to.equal(true);
        expect(wrapper.findComponent(GraduationCapIcon).exists()).to.equal(true);
    });
});
