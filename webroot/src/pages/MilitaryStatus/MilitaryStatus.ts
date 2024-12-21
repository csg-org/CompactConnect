//
//  MilitaryStatus.ts
//  CompactConnect
//
//  Created by InspiringApps on 12/20/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import InputButton from '@components/Forms/InputButton/InputButton.vue';

@Component({
    name: 'MilitaryStatus',
    components: {
        InputButton
    }
})
export default class MilitaryStatus extends Vue {
    //
    // Data
    //

    //
    // Lifecycle
    //

    //
    // Computed
    //

    //
    // Methods
    //
    goBack() {
        console.log('go back');
    }
}
