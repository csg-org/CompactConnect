<!--
    ExampleFeatureGates.vue
    CompactConnect

    Created by InspiringApps on 9/25/2025.
-->

<template>
    <Section class="example-feature-gates-container">
        <h2>{{ $t('styleGuide.exampleFeatureGates') }}</h2>
        <div class="example-feature-gate">
            <div class="example-feature-gate-layer">{{ $t('styleGuide.exampleFeatureGateLayerComponent') }}:</div>
            <span class="example-feature-gate-name">{{ featureGates.EXAMPLE_FEATURE_1 }}:</span>
            <span
                v-if="$features.checkGate(featureGates.EXAMPLE_FEATURE_1)"
                class="example-feature-gate-status enabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOn') }}
            </span>
            <span
                v-else
                class="example-feature-gate-status disabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOff') }}
            </span>
        </div>
        <div class="example-feature-gate">
            <div class="example-feature-gate-layer">{{ $t('styleGuide.exampleFeatureGateLayerStore') }}:</div>
            <span class="example-feature-gate-name">{{ featureGates.EXAMPLE_FEATURE_1 }}:</span>
            <span
                v-if="isFeatureGateEnabledInStoreLayer"
                class="example-feature-gate-status enabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOn') }}
            </span>
            <span
                v-else
                class="example-feature-gate-status disabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOff') }}
            </span>
        </div>
        <div class="example-feature-gate">
            <div class="example-feature-gate-layer">{{ $t('styleGuide.exampleFeatureGateLayerModel') }}:</div>
            <span class="example-feature-gate-name">{{ featureGates.EXAMPLE_FEATURE_1 }}:</span>
            <span
                v-if="isFeatureGateEnabledInModelLayer"
                class="example-feature-gate-status enabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOn') }}
            </span>
            <span
                v-else
                class="example-feature-gate-status disabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOff') }}
            </span>
        </div>
        <div class="example-feature-gate">
            <div class="example-feature-gate-layer">{{ $t('styleGuide.exampleFeatureGateLayerNetwork') }}:</div>
            <span class="example-feature-gate-name">{{ featureGates.EXAMPLE_FEATURE_1 }}:</span>
            <span
                v-if="isFeatureGateEnabledInNetworkLayer"
                class="example-feature-gate-status enabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOn') }}
            </span>
            <span
                v-else
                class="example-feature-gate-status disabled"
            >
                {{ $t('styleGuide.exampleFeatureGateOff') }}
            </span>
        </div>
    </Section>
</template>

<script lang="ts" src="./ExampleFeatureGates.ts"></script>
<style scoped lang="less" src="./ExampleFeatureGates.less"></style>
