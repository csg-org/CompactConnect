<!--
    PrivilegeEventNode.vue
    CompactConnect

    Created by InspiringApps on 3/21/2025.
-->

<template>
    <div
        class="event-node-container"
        role="listitem"
        :aria-label="$t('licensing.eventNodeLabel', { eventNameDisplay, eventDate })"
        :class="{
            'short': eventLengthBucket === 'short',
            'medium': eventLengthBucket === 'medium',
            'long': eventLengthBucket === 'long'
        }"
    >
        <div class="node"
            :class="{
                'inactive': isDeactivating,
                'active': isActivating
            }"
        />
        <div class="event-info">
            <div class="event-date">{{eventDate}}</div>
            <div class="event-type">{{eventNameDisplay}}</div>
            <div class="event-detail"></div>
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeEventNode.ts"></script>
<style scoped lang="less" src="./PrivilegeEventNode.less"></style>
