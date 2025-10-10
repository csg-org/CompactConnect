//
//  statsigapi.d.ts
//  CompactConnect
//
//  Created by InspiringApps on 9/17/2025.
//

import { StatsigClient } from '@statsig/js-client';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $features: StatsigClient,
        $analytics: StatsigClient,
    }
}
