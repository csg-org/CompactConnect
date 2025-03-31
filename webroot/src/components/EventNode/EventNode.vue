<!--
    EventNode.vue
    CompactConnect

    Created by InspiringApps on 3/21/2025.
-->

<template>
    <div class="event-node-container">
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

<script lang="ts" src="./EventNode.ts"></script>
<style scoped lang="less" src="./EventNode.less"></style>
