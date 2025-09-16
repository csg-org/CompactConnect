//
//  ExpirationExplanationIcon.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/15/2025.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';

@Component({
    name: 'ExpirationExplanationIcon',
})
class ExpirationExplanationIcon extends Vue {
    //
    // Data
    //
    shouldShowExpirationExplanation = false;

    //
    // Methods
    //
    toggleExpirationExplanation() {
        this.shouldShowExpirationExplanation = !this.shouldShowExpirationExplanation;
    }
}

export default toNative(ExpirationExplanationIcon);

// export default ExpirationExplanationIcon;
