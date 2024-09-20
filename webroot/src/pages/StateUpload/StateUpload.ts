//
//  StateUpload.ts
//  CompactConnect
//
//  Created by InspiringApps on 8/19/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import StateUpload from '@components/StateUpload/StateUpload.vue';

@Component({
    name: 'StateUploadPage',
    components: {
        Section,
        StateUpload,
    }
})
export default class StateUploadPage extends Vue {
}
