//
//  PageFooter.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 5/4/2020.
//

import { Vue, Component, toNative } from 'vue-facing-decorator';
import moment from 'moment';

@Component({
    name: 'PageFooter',
    components: {}
})
class PageFooter extends Vue {
    //
    // Computed
    //
    get copyrightYear(): string {
        return moment().format('YYYY');
    }
}

export default toNative(PageFooter);

// export { PageFooter };
