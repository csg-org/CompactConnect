//
//  ExampleLanguageSelector.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/8/2024.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import LanguageSelector from '@components/LanguageSelector/LanguageSelector.vue';

@Component({
    name: 'ExampleLanguageSelector',
    components: {
        Section,
        LanguageSelector
    }
})
class ExampleLanguageSelector extends Vue {
}

export default toNative(ExampleLanguageSelector);

// export { ExampleLanguageSelector };
