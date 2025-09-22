<!--
    PrivilegeEventNode.vue
    CompactConnect

    Created by InspiringApps on 3/21/2025.
-->

<template>
    <div
        class="event-node-container"
        :class="eventLengthBucket"
        :aria-label="$t('licensing.eventNodeLabel', { eventNameDisplay, eventDate })"
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
            <div class="event-detail" v-if="uploadOnDisplay">{{uploadOnDisplay}}</div>
            <div class="event-detail">{{detailDisplay}}</div>
        </div>
    </div>
</template>

<script lang="ts" src="./PrivilegeEventNode.ts"></script>
<style scoped lang="less" src="./PrivilegeEventNode.less"></style>
