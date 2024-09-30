//
//  UserList.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/4/2024.
//

import { Component, Vue } from 'vue-facing-decorator';
import Section from '@components/Section/Section.vue';
import UserList from '@components/Users/UserList/UserList.vue';

@Component({
    name: 'UsersList',
    components: {
        Section,
        UserList,
    }
})
export default class UsersList extends Vue {
}
