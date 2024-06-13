//
//  envConfig.d.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//  Copyright © 2024. InspiringApps. All rights reserved.
//

import { EnvConfig } from './envConfig.plugin';

declare module '@vue/runtime-core' {
    interface ComponentCustomProperties {
        $envConfig: EnvConfig
    }
}
