//
//  CompactSettings.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/5/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import PaymentProcessorConfig from '@components/PaymentProcessorConfig/PaymentProcessorConfig.vue';

@Component({
    name: 'CompactSettings',
    components: {
        Section,
        PaymentProcessorConfig,
    }
})
export default class CompactSettings extends Vue {
}
