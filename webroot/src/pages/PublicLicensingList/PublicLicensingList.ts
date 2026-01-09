//
//  PublicLicensingList.ts
//  CompactConnect
//
//  Created by InspiringApps on 3/5/2025.
//

import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import LicenseeList from '@components/Licensee/LicenseeListLegacy/LicenseeListLegacy.vue';

@Component({
    name: 'LicensingListPublic',
    components: {
        Section,
        LicenseeList,
    }
})
export default class LicensingListPublic extends Vue {
}
