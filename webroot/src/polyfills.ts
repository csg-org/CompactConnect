//
//  polyfills.ts
//  InspiringApps modules
//
//  Created by InspiringApps on 4/12/20.
//

import fromEntries from 'object.fromentries';
import { TextEncoder } from 'text-encoding-shim';

// Object.fromEntries
if (!Object.fromEntries) {
    fromEntries.shim();
}

// window.TextEncoder
if (typeof window.TextEncoder === 'undefined') {
    (window as any).TextEncoder = TextEncoder;
}
