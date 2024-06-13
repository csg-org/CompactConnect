//
//  StyleGuide.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/28/2021.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { Component, Vue } from 'vue-facing-decorator';
import ExampleList from '@components/StyleGuide/ExampleList/ExampleList.vue';
import ExampleLanguageSelector from '@components/StyleGuide/ExampleLanguageSelector/ExampleLanguageSelector.vue';
import ExampleForm from '@components/StyleGuide/ExampleForm/ExampleForm.vue';
import ExampleModal from '@components/StyleGuide/ExampleModal/ExampleModal.vue';
import ExampleLoadingSpinner from '@components/StyleGuide/ExampleLoadingSpinner/ExampleLoadingSpinner.vue';
import ExampleMobileLinks from '@components/StyleGuide/ExampleMobileLinks/ExampleMobileLinks.vue';

@Component({
    components: {
        ExampleList,
        ExampleLanguageSelector,
        ExampleForm,
        ExampleModal,
        ExampleLoadingSpinner,
        ExampleMobileLinks,
    }
})
export default class StyleGuide extends Vue {
}
