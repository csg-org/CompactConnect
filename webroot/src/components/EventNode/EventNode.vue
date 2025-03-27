<!--
    EventNode.vue
    CompactConnect

    Created by InspiringApps on 3/21/2025.
-->

<template>
    <div class="event-node-container">
        <div class="node" />
        <div class="event-info">
            <div class="event-date">{{eventDate}}</div>
            <div class="event-type">{{eventType}}</div>
            <div class="event-detail"></div>
        </div>
        <!-- <StatusTimeBlock class="time-block" /> -->
    </div>
</template>

<script lang="ts" src="./EventNode.ts"></script>
<style scoped lang="less" src="./EventNode.less"></style>
