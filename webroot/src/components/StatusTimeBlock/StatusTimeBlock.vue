<!--
    StatusTimeBlock.vue
    CompactConnect

    Created by InspiringApps on 3/21/2025.
-->

<template>
    <div
        class="status-time-block-container"
        role="status"
        :aria-label="$t('licensing.statusBlockLabel', { status })"
        :class="{
            'inactive': isDeactivating,
            'active': isActivating,
            'start-of-block': isStartOfVisualBlock,
            'end-of-block': isEndOfVisualBlock,
        }"
    >
        <div
            :class="{
                'inactive': isDeactivating,
                'active': isActivating,
                'start-of-block': isStartOfVisualBlock,
                'end-of-block': isEndOfVisualBlock,
                'last-event': isLastEvent
            }"
            class="status-time-block-color"
        >
            <span v-if="isStartOfVisualBlock">{{status}}</span>
        </div>
    </div>
</template>

<script lang="ts" src="./StatusTimeBlock.ts"></script>
<style scoped lang="less" src="./StatusTimeBlock.less"></style>
