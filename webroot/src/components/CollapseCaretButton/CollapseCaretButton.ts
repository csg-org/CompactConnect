//
//  CollapseCaretButton.ts
//  CompactConnect
//
//  Created by InspiringApps on 11/3/2024.
//

import { Component, Vue, toNative } from 'vue-facing-decorator';

@Component({
    name: 'CollapseCaretButton',
})
class CollapseCaretButton extends Vue {
    //
    // Data
    //
    isUp = true;

    //
    // Methods
    //
    toggleCollapse() {
        this.$emit('toggleCollapse');
        this.isUp = !this.isUp;
    }
}

export default toNative(CollapseCaretButton);

// export default CollapseCaretButton;
