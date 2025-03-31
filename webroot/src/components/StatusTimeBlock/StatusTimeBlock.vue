<!--
    StatusTimeBlock.vue
    CompactConnect

    Created by InspiringApps on 3/21/2025.
-->

<template>
    <div
        class="status-time-block-container"
        :class="{
            'inactive': isDeactivating,
            'active': isActivating,
            'start': isStart,
            'end': isEnd,
        }"
    >
        <div
            :class="{
                'inactive': isDeactivating,
                'active': isActivating,
                'start': isStart,
                'end': isEnd,
                'last': isLast
            }"
            class="status-time-block-color"
        >
            <span v-if="isStart">{{status}}</span>
        </div>
    </div>
</template>

<script lang="ts" src="./StatusTimeBlock.ts"></script>
<style scoped lang="less" src="./StatusTimeBlock.less"></style>
